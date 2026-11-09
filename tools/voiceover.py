#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy", "soundfile", "soxr"]
# ///
"""Script to narration: one sentence per TTS call, joined with fixed gaps, with a timing manifest.

Pace is a generation setting, not a post-process: never time-stretch the result to fit. Re-write or re-generate.
Single-shot cloned voices read fast (171-215 wpm measured); one request per sentence, one seed per beat (paragraph),
joined with 0.4 s, gave 144 wpm with no stretching. A beat still fast after four seeds is a script problem.

Engines:
  remote        a voice defined in ~/.config/editbay/config.json under tts.voices.<name> that runs on another machine's
                GPU (e.g. a creator's cloned voice). Pass --voice-config <name>. Sentences needing generation are sent
                in one job to tts_worker_runner.py on that host (it takes the host's GPU lock), and the WAVs come back.
  qwen3-worker  a local Qwen3-TTS JSON-lines worker (request {"text","voice_id","output_path","seed","settings"} per
                stdin line, first stdout line announces readiness). Pass --python, --worker, --ckpt, --device.
  say           macOS `say` scratch voice for drafts and timing rehearsals (never for delivery).
  hyperframes   `npx hyperframes tts` (Kokoro-82M, local).

Script format: plain text or Markdown. Blank line = paragraph (longer gap). Lines starting with `#`, `>`, `<!--`,
table pipes, or `~~~` blocks are skipped (headings, notes, metadata, cue blocks). Lines beginning `On-screen:`,
`Pronunciation:`, or `Metadata:` are also skipped and copied to `script-metadata.md`. An optional `[B03]` prefix on a
paragraph tags its beat.

Usage:
  voiceover.py script.md --out narration/ --engine qwen3-worker --voice aiden --python P --worker W --ckpt C --device mps
  voiceover.py script.md --out narration/ --engine say --voice Samantha
  voiceover.py script.md --out narration/ --engine remote --voice-config creator-clone --story-slug STORY --producer-callsign CALLSIGN
  voiceover.py script.md --out narration/ --engine remote --voice-config creator-clone --dry-run --story-slug STORY --producer-callsign CALLSIGN
                [--glossary transcript/glossary.json]
Writes narration/narration.wav (48 kHz mono, 24-bit), narration/sentences/*.wav, narration/narration.json, and when
present narration/script-metadata.md for skipped production notes
({sentences:[{i, beat, text, start, end, file, seed}], gap, paragraph_gap, duration, engine, voice}).
Re-running reuses sentence WAVs whose text is unchanged; --redo 4,7 regenerates those with a new seed.
Remote jobs use the namespace STORY--PRODUCER (inferred from --out and EDITBAY_* when omitted); --dry-run prints it
without starting TTS.
TTS garbles sentences now and then: always check with voiceover_check.py before building on the timings.
"""
import argparse, json, os, re, shutil, subprocess, sys, tempfile

np = sf = soxr = None

SR = 48000


def safe_part(value, label):
    value = re.sub(r"[^A-Za-z0-9._-]+", "-", str(value).strip()).strip("-._")
    if not value:
        raise SystemExit(f"voiceover: {label} must contain at least one safe path character")
    return value


def run_identity(out_dir, story_slug=None, producer=None):
    """Return the story and producer names used to isolate a remote TTS job."""
    out_dir = os.path.abspath(out_dir)
    slug = story_slug or os.environ.get("EDITBAY_STORY_SLUG") or os.path.basename(os.path.dirname(out_dir))
    slug = safe_part(slug, "story slug")
    callsign = producer or os.environ.get("EDITBAY_PRODUCER_CALLSIGN") or f"PRODUCER-{slug}"
    return slug, safe_part(callsign, "producer callsign")


def remote_work_dir(cfg, story_slug, producer):
    return cfg["work_dir"].rstrip("/") + f"/{story_slug}--{producer}"


def validate_glossary(path):
    """Fail before TTS when a reconciliation glossary cannot support variant matching."""
    if not path:
        return
    try:
        data = json.load(open(path, encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"voiceover: could not read glossary {path}: {exc}") from exc
    terms = data.get("terms") if isinstance(data, dict) else None
    if not isinstance(terms, list):
        raise SystemExit("voiceover: glossary must contain a terms array")
    for index, term in enumerate(terms):
        if not isinstance(term, dict) or not isinstance(term.get("canonical"), str) or not term["canonical"].strip():
            raise SystemExit(f"voiceover: glossary term {index} needs a non-empty canonical string")
        why = term.get("why")
        if not isinstance(why, str) or not why.strip():
            raise SystemExit(f"voiceover: glossary term {index} needs a non-empty why string")
        variants = term.get("variants")
        if not isinstance(variants, list) or any(not isinstance(v, str) or not v.strip() for v in variants):
            raise SystemExit(f"voiceover: glossary term {index} needs a variants array of non-empty strings")


def parse_script(path):
    text = open(path, encoding="utf-8").read()
    metadata = []
    for match in re.finditer(r"~~~(?:metadata|production[- ]?note|pronunciation)\b(.*?)~~~", text, flags=re.I | re.S):
        metadata.extend(line.strip() for line in match.group(1).splitlines() if line.strip())
    text = re.sub(r"~~~.*?~~~", "", text, flags=re.S)
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    paras = []
    for block in re.split(r"\n\s*\n", text):
        lines = []
        for line in block.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith(("#", ">", "|", "- [", "```")):
                metadata.append(line)
                continue
            if line.casefold().startswith(("on-screen:", "pronunciation:", "metadata:", "production note:")):
                metadata.append(line)
                continue
            lines.append(line)
        if not lines:
            continue
        body = " ".join(lines)
        beat = None
        m = re.match(r"^\[([A-Za-z]\w*)\]\s*(.*)$", body)
        if m:
            beat, body = m.group(1), m.group(2)
        # Sentence split that keeps abbreviations like "e.g." and decimals like "5.5" intact.
        sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+(?=[A-Z\"'(])", body) if s.strip()]
        paras.append((beat, sents))
    return paras, metadata


class QwenWorker:
    def __init__(self, python, worker, ckpt, device):
        self.p = subprocess.Popen([python, worker, "--ckpt-dir", ckpt, "--device", device], stdin=subprocess.PIPE,
                                  stdout=subprocess.PIPE, text=True, bufsize=1)
        ready = json.loads(self.p.stdout.readline())
        if not ready.get("ready"):
            raise RuntimeError(f"worker not ready: {ready}")
        print(f"qwen3 worker ready on {ready.get('device')} ({ready.get('dtype')})", file=sys.stderr)

    def say(self, text, voice, out, seed):
        self.p.stdin.write(json.dumps({"text": text, "voice_id": voice, "output_path": out, "seed": seed,
                                       "settings": {"language": "English"}}) + "\n")
        self.p.stdin.flush()
        r = json.loads(self.p.stdout.readline())
        if not r.get("ok"):
            raise RuntimeError(f"TTS failed for {text!r}: {r}")
        return r

    def close(self):
        self.p.stdin.close(); self.p.wait(timeout=60)


def remote_generate(cfg, jobs, local_dir, story_slug, producer):
    """Generate [(sentence_no, text, seed)] on the voice's host in one job; copy the WAVs to local_dir/sNNN.wav."""
    import time as _t
    host, rdir = cfg["host"], remote_work_dir(cfg, story_slug, producer)
    here = os.path.dirname(os.path.abspath(__file__))
    voice_id = cfg.get("voice_id")
    job = {"worker": cfg["worker"], "lock": cfg["lock"], "out_dir": rdir,
           "items": [{"id": f"s{i:03d}", "text": t, "seed": sd,
                      "settings": {"language": cfg.get("language", "English")},
                      **({"voice_id": voice_id} if voice_id else {})}
                     for i, t, sd in jobs]}
    jf = os.path.join(tempfile.mkdtemp(), "job.json")
    json.dump(job, open(jf, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    pwsh = cfg.get("shell", "pwsh") == "pwsh"
    mk = (f"New-Item -ItemType Directory -Force -Path '{rdir}' | Out-Null; [Environment]::Exit(0)" if pwsh else f"mkdir -p '{rdir}'")
    subprocess.run(["ssh", host, mk], check=True)
    subprocess.run(["scp", "-q", jf, os.path.join(here, "tts_worker_runner.py"), f"{host}:{rdir}/"], check=True)
    run = (f"& '{cfg['runner_python']}' '{rdir}/tts_worker_runner.py' '{rdir}/job.json'; [Environment]::Exit($LASTEXITCODE)"
           if pwsh else f"'{cfg['runner_python']}' '{rdir}/tts_worker_runner.py' '{rdir}/job.json'")
    t0 = _t.time()
    r = subprocess.run(["ssh", host, run])
    print(f"remote job on {host}: exit {r.returncode} in {_t.time() - t0:.0f}s", file=sys.stderr)
    # One transfer for all files: each ssh/scp session can cost seconds of remote shell startup.
    subprocess.run(["scp", "-q", *[f"{host}:{rdir}/s{i:03d}.wav" for i, _, _ in jobs], local_dir + "/"], check=True)
    if r.returncode:
        raise SystemExit(f"remote TTS job failed (exit {r.returncode}); see {host}:{rdir}/worker.log and results.json")


def say_engine(text, voice, out):
    aiff = out + ".aiff"
    subprocess.run(["say", "-v", voice or "Samantha", "-o", aiff, text], check=True)
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", aiff, out], check=True)
    os.remove(aiff)


def hf_engine(text, voice, out):
    subprocess.run(["npx", "-y", "hyperframes", "tts", text, "--voice", voice or "af_heart", "--output", out], check=True)


def load(path):
    y, sr = sf.read(path, always_2d=True)
    y = y.mean(axis=1)
    if sr != SR:
        y = soxr.resample(y, sr, SR)
    # Keep the model's natural edges (they are part of its phrasing); only shorten edges longer than 0.25 s so a
    # stray long silence cannot stretch a gap. The joins then add --gap / --paragraph-gap on top.
    idx = np.where(np.abs(y) > 10 ** (-50 / 20))[0]
    if len(idx):
        keep = int(0.25 * SR)
        y = y[max(idx[0] - keep, 0): idx[-1] + keep]
    return y


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("script"); ap.add_argument("--out", required=True)
    ap.add_argument("--engine", choices=["remote", "qwen3-worker", "say", "hyperframes"], default="qwen3-worker")
    ap.add_argument("--voice-config", help="name under tts.voices in the editbay config (engine remote)")
    ap.add_argument("--config", default=os.path.expanduser("~/.config/editbay/config.json"))
    ap.add_argument("--glossary", help="reconcile-style glossary; validate its variants before TTS")
    ap.add_argument("--story-slug", help="story slug for the remote work namespace (inferred from --out when omitted)")
    ap.add_argument("--producer-callsign", help="producer callsign for the remote work namespace")
    ap.add_argument("--dry-run", action="store_true", help="print the remote namespace without starting TTS")
    ap.add_argument("--voice", default="aiden"); ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--python"); ap.add_argument("--worker"); ap.add_argument("--ckpt"); ap.add_argument("--device", default="mps")
    ap.add_argument("--gap", type=float, default=0.4, help="silence between sentences (s)")
    ap.add_argument("--paragraph-gap", type=float, default=0.8)
    ap.add_argument("--lead-in", type=float, default=0.3)
    ap.add_argument("--redo", default="", help="comma list of sentence numbers to regenerate with a new seed")
    a = ap.parse_args()
    validate_glossary(a.glossary)
    story_slug, producer = run_identity(a.out, a.story_slug, a.producer_callsign)
    if a.dry_run:
        if a.engine == "remote":
            if not a.voice_config:
                raise SystemExit("voiceover: --voice-config is required for --engine remote")
            cfg = json.load(open(a.config))["tts"]["voices"][a.voice_config]
            print(f"remote workdir: {remote_work_dir(cfg, story_slug, producer)}")
            print(f"namespace: {story_slug}--{producer}")
        else:
            print(f"dry-run: engine={a.engine} out={a.out}")
        return
    global np, sf, soxr
    import numpy as np
    import soundfile as sf
    import soxr
    redo = {int(x) for x in a.redo.split(",") if x.strip()}
    old = {}
    mpath = os.path.join(a.out, "narration.json")
    if os.path.exists(mpath):
        old = {m["i"]: m for m in json.load(open(mpath))["sentences"]}
    paras, metadata = parse_script(a.script)
    os.makedirs(os.path.join(a.out, "sentences"), exist_ok=True)
    if metadata:
        with open(os.path.join(a.out, "script-metadata.md"), "w", encoding="utf-8") as f:
            f.write("# Non-spoken production notes\n\n" + "\n".join(f"- {line}" for line in metadata) + "\n")
    if a.engine == "remote":
        if not a.voice_config:
            raise SystemExit("voiceover: --voice-config is required for --engine remote")
        vcfg = json.load(open(a.config))["tts"]["voices"][a.voice_config]
        a.voice = a.voice_config
        old0 = {}
        if os.path.exists(os.path.join(a.out, "narration.json")):
            old0 = {m["i"]: m for m in json.load(open(os.path.join(a.out, "narration.json")))["sentences"]}
        redo0 = {int(x) for x in a.redo.split(",") if x.strip()}
        jobs, n = [], 0
        for pi, (_, sents) in enumerate(paras):
            for s_ in sents:
                n += 1
                prev = old0.get(n, {})
                # One seed per beat (paragraph) keeps the voice consistent inside a beat; a redo re-seeds one sentence.
                seed = prev.get("seed", a.seed + 100 * pi) + (1000 if n in redo0 else 0)
                f = os.path.join(a.out, "sentences", f"s{n:03d}.wav")
                if not (os.path.exists(f) and prev.get("text") == s_ and n not in redo0):
                    jobs.append((n, s_, seed))
        if jobs:
            remote_generate(vcfg, jobs, os.path.join(a.out, "sentences"), story_slug, producer)
        remote_seeds = {i: sd for i, _, sd in jobs}
    worker = None  # started lazily: a fully cached rebuild never loads the model
    pieces, meta, t, i = [np.zeros(int(a.lead_in * SR))], [], a.lead_in, 0
    try:
        for pi, (beat, sents) in enumerate(paras):
            for si, s in enumerate(sents):
                i += 1
                f = os.path.join(a.out, "sentences", f"s{i:03d}.wav")
                prev = old.get(i, {})
                seed = prev.get("seed", a.seed) + (1000 if i in redo else 0)
                cached = os.path.exists(f) and prev.get("text") == s and i not in redo
                if a.engine == "remote":
                    seed = remote_seeds.get(i, prev.get("seed", a.seed + i))
                    cached = True  # generated (or reused) above, in one batch
                if cached:
                    pass
                elif worker is None and a.engine == "qwen3-worker":
                    worker = QwenWorker(a.python, a.worker, a.ckpt, a.device)
                if cached:
                    pass
                elif worker:
                    worker.say(s, a.voice, f, seed)
                elif a.engine == "say":
                    say_engine(s, a.voice, f)
                else:
                    hf_engine(s, a.voice, f)
                y = load(f)
                meta.append({"i": i, "beat": beat, "text": s, "start": round(t, 3), "end": round(t + len(y) / SR, 3),
                             "file": os.path.relpath(f, a.out), "seed": seed})
                pieces.append(y); t += len(y) / SR
                last = si == len(sents) - 1 and pi == len(paras) - 1
                gap = 0.0 if last else (a.paragraph_gap if si == len(sents) - 1 else a.gap)
                pieces.append(np.zeros(int(gap * SR))); t += gap
                print(f"[{i:03d}] {meta[-1]['start']:7.2f}-{meta[-1]['end']:7.2f}  {s}", file=sys.stderr)
    finally:
        if worker:
            worker.close()
    pieces.append(np.zeros(int(0.5 * SR)))
    audio = np.concatenate(pieces)
    peak = np.max(np.abs(audio)) or 1.0
    audio = audio / peak * 10 ** (-3 / 20)  # -3 dBFS peak; loudness is set in the mix, not here
    sf.write(os.path.join(a.out, "narration.wav"), audio, SR, subtype="PCM_24")
    words = sum(len(m["text"].split()) for m in meta)
    speech = sum(m["end"] - m["start"] for m in meta)
    manifest = {"engine": a.engine, "voice": a.voice, "seed": a.seed, "gap": a.gap, "paragraph_gap": a.paragraph_gap,
                "disclosure": (json.load(open(a.config))["tts"]["voices"][a.voice_config].get("disclosure")
                               if a.engine == "remote" else None),
                "duration": round(len(audio) / SR, 3), "words": words, "wpm_speech_only": round(words / speech * 60, 1) if speech else 0,
                "wpm_overall": round(words / (len(audio) / SR) * 60, 1), "sentences": meta}
    json.dump(manifest, open(os.path.join(a.out, "narration.json"), "w"), indent=1)
    print(f"{len(meta)} sentences, {manifest['duration']}s, {manifest['wpm_overall']} wpm overall "
          f"({manifest['wpm_speech_only']} while speaking) -> {os.path.join(a.out, 'narration.wav')}")


if __name__ == "__main__":
    main()
