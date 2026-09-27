#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
"""Transcribe an audio file twice (Whisper large-v3 and turbo) on the configured GPU host and bring the results back.

Why: hand-written ssh/scp/PowerShell for this step went wrong in a Codex run (the file was copied under one name and
transcribed under another). This does the whole round trip in three remote calls with fixed names.

Usage:
  asr_remote.py audio.wav --out-dir transcript/ [--stem t] [--prompt-file vocab.txt] [--models large-v3,large-v3-turbo]
                [--job NAME] [--story-slug SLUG] [--producer-callsign CALLSIGN]
                [--config ~/.config/editbay/config.json] [--dry-run]
Writes OUT/STEM.v3.{json,srt,txt} and OUT/STEM.turbo.{json,srt,txt} (other models: OUT/STEM.<model>.*). large-v3 runs
sequentially with the prompt file (names and jargon); turbo runs batched without it, as transcript-reconcile expects.
The host comes from the config's gpu_host (ssh alias, shell pwsh|bash, work_root, python). The audio travels as
audio<ext> so the remote command never depends on local file names. Prints each pass's word count and wall time, and
exits 1 when the two passes differ by more than 5% in words (a dropped or invented stretch: find it before voting).
Measured on the RTX 4090: 19.4 min of speech, large-v3 in ~170 s and turbo in ~11 s; an 89 s narration in ~9 s + ~1.4 s.
"""
import argparse, json, os, re, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
STEM_OF = {"large-v3": "v3", "large-v3-turbo": "turbo"}


def safe_part(value, label):
    value = re.sub(r"[^A-Za-z0-9._-]+", "-", str(value).strip()).strip("-._")
    if not value:
        raise SystemExit(f"asr_remote: {label} must contain at least one safe path character")
    return value


def run_identity(out_dir, story_slug=None, producer=None):
    out_dir = os.path.abspath(out_dir)
    slug = story_slug or os.environ.get("EDITBAY_STORY_SLUG") or os.path.basename(os.path.dirname(out_dir))
    slug = safe_part(slug, "story slug")
    callsign = producer or os.environ.get("EDITBAY_PRODUCER_CALLSIGN") or f"PRODUCER-{slug}"
    return slug, safe_part(callsign, "producer callsign")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("audio"); ap.add_argument("--out-dir", required=True); ap.add_argument("--stem", default="t")
    ap.add_argument("--prompt-file"); ap.add_argument("--models", default="large-v3,large-v3-turbo")
    ap.add_argument("--job"); ap.add_argument("--config", default=os.path.expanduser("~/.config/editbay/config.json"))
    ap.add_argument("--story-slug", help="story slug for the remote work namespace (inferred from --out-dir when omitted)")
    ap.add_argument("--producer-callsign", help="producer callsign for the remote work namespace")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if not os.path.isfile(a.audio):
        sys.exit(f"asr_remote: no such audio file: {a.audio}")
    if a.prompt_file and not os.path.isfile(a.prompt_file):
        sys.exit(f"asr_remote: no such prompt file: {a.prompt_file}")
    g = json.load(open(a.config)).get("gpu_host") or sys.exit("asr_remote: the config has no gpu_host")
    host, pwsh, py = g["ssh"], g.get("shell", "pwsh") == "pwsh", g["python"]
    story_slug, producer = run_identity(a.out_dir, a.story_slug, a.producer_callsign)
    namespace = f"{story_slug}--{producer}"
    requested_job = safe_part(a.job, "job") if a.job else ""
    job = requested_job if requested_job and story_slug in requested_job and producer in requested_job else \
        f"{namespace}--{requested_job}" if requested_job else namespace
    rdir = f"{g['work_root'].rstrip('/')}/transcribe/{job}"
    ext = os.path.splitext(a.audio)[1] or ".wav"
    models = [m.strip() for m in a.models.split(",") if m.strip()]
    stems = {m: f"{a.stem}.{STEM_OF.get(m, m)}" for m in models}

    def pass_cmd(m):
        args = [f"audio{ext}", "--model", m]
        if m == "large-v3" and a.prompt_file:
            args += ["--prompt-file", "vocab.txt"]
        if m != "large-v3":
            args += ["--batched"]
        args += ["--out", stems[m]]
        return args

    if pwsh:
        mk = f"New-Item -ItemType Directory -Force -Path '{rdir}' | Out-Null; [Environment]::Exit(0)"
        runs = "; ".join(f"& '{py}' transcribe_faster_whisper.py {' '.join(pass_cmd(m))}; if ($LASTEXITCODE) {{ [Environment]::Exit($LASTEXITCODE) }}"
                         for m in models)
        run = f"Set-Location '{rdir}'; {runs}; [Environment]::Exit(0)"
    else:
        mk = f"mkdir -p '{rdir}'"
        run = f"cd '{rdir}' && " + " && ".join(f"'{py}' transcribe_faster_whisper.py {' '.join(pass_cmd(m))}" for m in models)
    if a.dry_run:
        print("ssh", host, mk); print("scp ->", f"{host}:{rdir}/audio{ext}"); print("ssh", host, run); return
    os.makedirs(a.out_dir, exist_ok=True)
    t0 = time.time()
    subprocess.run(["ssh", host, mk], check=True)
    import shutil, tempfile
    tmp = tempfile.mkdtemp()
    shutil.copy2(a.audio, os.path.join(tmp, f"audio{ext}"))
    send = [os.path.join(HERE, "transcribe_faster_whisper.py"), os.path.join(tmp, f"audio{ext}")]
    if a.prompt_file:
        shutil.copy2(a.prompt_file, os.path.join(tmp, "vocab.txt")); send.append(os.path.join(tmp, "vocab.txt"))
    subprocess.run(["scp", "-q", *send, f"{host}:{rdir}/"], check=True)
    r = subprocess.run(["ssh", host, run], capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"asr_remote: remote transcription failed (exit {r.returncode}) in {host}:{rdir}\n{(r.stdout + r.stderr)[-1500:]}")
    wanted = [f"{host}:{rdir}/{stems[m]}.{x}" for m in models for x in ("json", "srt", "txt")]
    subprocess.run(["scp", "-q", *wanted, a.out_dir.rstrip("/") + "/"], check=True)
    counts = {}
    for m in models:
        d = json.load(open(os.path.join(a.out_dir, stems[m] + ".json")))
        counts[m] = sum(len(s.get("words") or []) for s in d["segments"])
        print(f"{stems[m]}.json: {counts[m]} words, {d.get('seconds', '?')} s on {host}")
    print(f"round trip {time.time() - t0:.1f} s ({host}:{rdir})")
    if len(counts) >= 2:
        lo, hi = min(counts.values()), max(counts.values())
        gap = (hi - lo) / max(hi, 1)
        print(f"word counts differ by {gap:.1%}" + ("  OK" if gap <= 0.05 else "  CHECK: over 5%, find the dropped or invented stretch"))
        sys.exit(0 if gap <= 0.05 else 1)


if __name__ == "__main__":
    main()
