#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy"]
# ///
"""Plan a rough cut from a word-timed transcript: dead air, fillers, and retakes, snapped to frames.

Usage:
  cut_plan.py TRANSCRIPT.json --media SOURCE.mp4 --out cut/ [--max-gap 0.7 --keep-gap 0.3] [--fillers um,uh,erm]
              [--implicit-retakes suggest|apply|off] [--protect 12.0-15.5,...] [--selects selects.json]
  --selects: [{"in": 100.24, "out": 106.01, "label": "intro"}, {"gap": 3.0, "label": "insert"}, ...] source ranges
             (first word start, last word end) and gaps (a black, silent slot of exact frames for a clip placed later)
             in OUTPUT order. Each is snapped into silence like any cut, cleaned of dead air and fillers inside, and
             assembled in the listed order (a promo from a rambling take). The EDL is then "ordered": true.
TRANSCRIPT: reconcile/faster-whisper JSON (segments with words [start, end, word, prob]) on the SOURCE timeline.
Writes:
  cut/edl.json         {source, fps, duration, keep:[{in,out}], remove:[{in,out,reason,text}], stats}
  cut/KEEP-LIST.md     every removal with its words and reason, for a human (or agent) to veto before rendering
  cut/words.cut.json   HyperFrames word array retimed onto the cut timeline (captions/beats after the cut)
Rules:
  - dead air: a gap between words longer than --max-gap shrinks to --keep-gap (kept half on each side)
  - fillers: standalone um/uh/erm (pass --fillers to change; "like"/"you know" are never removed by default)
  - retakes: an explicit restart phrase ("let me start that again", "scratch that", ...) removes the abandoned
    sentence and the phrase when the speaker then restarts with the same opening words; implicit restarts
    (a sentence that restarts with the same 3+ opening words within 12 s) are suggested, not applied, by default
  - --protect ranges are never cut (a deliberate pause, a punchline beat)
Every cut point is moved into real silence (the audio envelope, not the word timestamps, which drift 100-300 ms)
and then onto a frame boundary; a short pre-roll keeps the next word's onset.
"""
import argparse, json, math, os, re, subprocess

import numpy as np

MARKERS = ["sorry let me start that again", "let me start that again", "let me start again", "let me try that again",
           "let me redo that", "let me say that again", "start over", "scratch that", "cut that", "take two",
           "one more time", "let me rephrase"]


def norm(w):
    return re.sub(r"[^a-z0-9']", "", w.lower())


def probe(path):
    d = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                   "stream=r_frame_rate:format=duration", "-of", "json", path],
                                  capture_output=True, text=True).stdout)
    n, dd = d["streams"][0]["r_frame_rate"].split("/")
    return float(d["format"]["duration"]), float(n) / float(dd)


def envelope(path, hop=0.01):
    """10 ms RMS envelope in dBFS of the media's audio (mono 16 kHz)."""
    raw = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", path, "-vn", "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                         capture_output=True).stdout
    y = np.frombuffer(raw, dtype=np.float32)
    n = int(16000 * hop)
    frames = y[: len(y) // n * n].reshape(-1, n)
    return 20 * np.log10(np.sqrt((frames ** 2).mean(axis=1)) + 1e-9), hop


class Snapper:
    """Word timestamps from Whisper drift by 100-300 ms; the audio does not. Move each cut into real silence:
    a removal starts in the nearest silent frame and ends just before the next speech onset."""

    def __init__(self, env, hop, thr_db, window=0.35, preroll=0.04):
        self.env, self.hop, self.win, self.pre = env, hop, window, preroll
        self.silent = env < thr_db

    def _i(self, t):
        return int(min(max(t / self.hop, 0), len(self.env) - 1))

    def start(self, t):
        i, w = self._i(t), int(self.win / self.hop)
        cands = [j for j in range(max(i - w, 0), min(i + w, len(self.env))) if self.silent[j]]
        return min(cands, key=lambda j: (abs(j - i), j)) * self.hop if cands else t

    def end(self, t):
        i, w = self._i(t), int(self.win / self.hop)
        for j in range(max(i - w, 1), min(i + w, len(self.env))):
            if self.silent[j - 1] and not self.silent[j]:  # first speech onset in the window
                return max(j * self.hop - self.pre, 0)
        cands = [j for j in range(max(i - w, 0), min(i + w, len(self.env))) if self.silent[j]]
        return min(cands, key=lambda j: (abs(j - i), -j)) * self.hop if cands else t


    # Select edges need direction: a select must never lose its first or last word. Nearest-silence snapping can jump
    # forward past a soft first word, or back into the closure before a final consonant ("tourname|nt").
    def select_in(self, t, window=0.6, min_sil=0.08):
        """Cut before the speech that holds t: the onset after at least min_sil of silence. (time, clean)."""
        i, w, ms = self._i(t), int(window / self.hop), max(int(min_sil / self.hop), 1)
        if self.silent[i]:  # ASR start early: the word begins at the next onset
            k = next((m for m in range(i, min(i + w, len(self.env))) if not self.silent[m]), None)
            return (max(k * self.hop - self.pre, 0), True) if k is not None else (t, True)
        k = i
        while k > max(i - w, 0):
            if all(self.silent[max(k - ms, 0):k]) and k - ms >= 0:
                return max(k * self.hop - self.pre, 0), True
            k -= 1
        lo = max(i - w, 0)  # speech runs straight into this word: cut at the quietest moment before it, reported
        return float(lo + min(range(i - lo + 1), key=lambda m: self.env[lo + m])) * self.hop, False

    def select_out(self, t, window=0.6, min_sil=0.08):
        """Cut after the speech that holds t: the start of the first silence of at least min_sil. (time, clean)."""
        i, w, ms = self._i(t), int(window / self.hop), max(int(min_sil / self.hop), 1)
        for k in range(i, min(i + w, len(self.env) - ms)):
            if all(self.silent[k:k + ms]):
                return k * self.hop + self.pre, True
        hi = min(i + w, len(self.env) - 1)  # no pause after the last word: the quietest moment after it, reported
        return float(i + min(range(hi - i + 1), key=lambda m: self.env[i + m])) * self.hop, False


def load_words(path):
    d = json.load(open(path))
    if isinstance(d, list):
        return [{"s": w["start"], "e": w["end"], "w": w["text"].strip()} for w in d]
    out = []
    for s in d["segments"]:
        for w in s.get("words") or []:
            if w[2].strip():
                out.append({"s": w[0], "e": w[1], "w": w[2].strip()})
    return out


def sentence_starts(words):
    starts = [0]
    for i in range(1, len(words)):
        if re.search(r"[.!?]$", words[i - 1]["w"]) or words[i]["s"] - words[i - 1]["e"] > 1.0:
            starts.append(i)
    return starts


def find_retakes(words, implicit):
    toks = [norm(w["w"]) for w in words]
    starts = sentence_starts(words)
    found = []
    # Explicit markers: [abandoned sentence] + [marker] + [restart with the same opening words].
    # Longest marker first; a shorter marker inside an already matched one is the same retake.
    covered = set()
    for m in sorted(MARKERS, key=lambda x: -len(x.split())):
        mt = m.split()
        for i in range(len(toks) - len(mt) + 1):
            if toks[i:i + len(mt)] != mt or covered & set(range(i, i + len(mt))):
                continue
            covered |= set(range(i, i + len(mt)))
            j = i + len(mt)  # first word after the marker
            prev = [s for s in starts if s < i and words[i]["s"] - words[s]["s"] < 20]
            best = None
            for s in reversed(prev):
                k = 0
                while j + k < len(toks) and s + k < i and toks[s + k] == toks[j + k]:
                    k += 1
                if k >= 2:
                    best = s; break
            if best is None and prev:
                best = prev[-1]  # no matching restart: remove the sentence right before the marker
            if best is not None:
                found.append({"from": best, "to": j, "reason": f"retake: '{m}' then restart", "applied": True})
    if implicit != "off":
        for a in starts:
            for b in starts:
                if b <= a or words[b]["s"] - words[a]["s"] > 12:
                    continue
                k = 0
                while b + k < len(toks) and a + k < b and toks[a + k] == toks[b + k]:
                    k += 1
                if k >= 3 and not any(r["from"] <= a < r["to"] for r in found):
                    found.append({"from": a, "to": b, "reason": f"implicit retake: restarts with '{' '.join(toks[b:b + k])}'",
                                  "applied": implicit == "apply"})
    return found


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("transcript"); ap.add_argument("--media", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--max-gap", type=float, default=0.7); ap.add_argument("--keep-gap", type=float, default=0.3)
    ap.add_argument("--fillers", default="um,uh,erm,uhm,ah,hmm")
    ap.add_argument("--implicit-retakes", choices=["suggest", "apply", "off"], default="suggest")
    ap.add_argument("--pad", type=float, default=0.06, help="kept around each cut word edge (s)")
    ap.add_argument("--lead", type=float, default=0.2); ap.add_argument("--tail", type=float, default=0.5)
    ap.add_argument("--min-keep", type=float, default=0.25, help="keeps shorter than this merge into the removal")
    ap.add_argument("--protect", default="", help="comma list of start-end ranges that are never cut")
    ap.add_argument("--no-snap-silence", action="store_true", help="trust word timestamps as they are")
    ap.add_argument("--silence-db", type=float, default=-45.0, help="envelope level treated as silence (dBFS)")
    ap.add_argument("--selects", help="JSON list of {in, out, label} source ranges in output order (see above)")
    a = ap.parse_args()

    dur, fps = probe(a.media)
    words = load_words(a.transcript)
    fillers = {norm(f) for f in a.fillers.split(",") if f.strip()}
    protect = [tuple(float(x) for x in r.split("-")) for r in a.protect.split(",") if r.strip()]
    removals = []  # (in, out, reason, text, applied)

    if words:
        if words[0]["s"] - a.lead > 0.05:
            removals.append((0.0, words[0]["s"] - a.lead, "leading silence", "", True))
        if dur - (words[-1]["e"] + a.tail) > 0.05:
            removals.append((words[-1]["e"] + a.tail, dur, "trailing silence", "", True))
    for p, q in zip(words, words[1:]):
        gap = q["s"] - p["e"]
        if gap > a.max_gap:
            half = a.keep_gap / 2
            removals.append((p["e"] + half, q["s"] - half, f"dead air {gap:.2f}s", "", True))
    for i, w in enumerate(words):
        if norm(w["w"]) in fillers:
            s = words[i - 1]["e"] + a.pad if i else max(w["s"] - a.pad, 0)
            e = words[i + 1]["s"] - a.pad if i + 1 < len(words) else w["e"] + a.pad
            s, e = max(s, w["s"] - 0.25), min(e, w["e"] + 0.25)
            if e > s:
                removals.append((s, e, "filler", w["w"], True))
    for r in find_retakes(words, a.implicit_retakes):
        s = words[r["from"]]["s"] - a.pad
        e = words[r["to"]]["s"] - a.pad if r["to"] < len(words) else dur
        text = " ".join(w["w"] for w in words[r["from"]:r["to"]])
        removals.append((max(s, 0), e, r["reason"], text, r["applied"]))

    # Protect ranges, frame-snap, merge.
    def snap(t, up):
        f = math.ceil(t * fps - 1e-6) if up else math.floor(t * fps + 1e-6)
        return min(max(f / fps, 0.0), dur)

    snapper = None if a.no_snap_silence else Snapper(*envelope(a.media), a.silence_db)
    applied = []
    for s, e, why, text, ok in removals:
        if not ok:
            continue
        if snapper and why not in ("leading silence", "trailing silence"):
            s, e = snapper.start(s), snapper.end(e)
        for ps, pe in protect:
            if s < pe and e > ps:
                s, e = (s, ps) if s < ps else (pe, e) if e > pe else (0, 0)
        s, e = snap(s, up=True), snap(e, up=False)
        if e - s >= 1 / fps:
            applied.append([s, e, why, text])
    applied.sort()
    merged = []
    for r in applied:
        if merged and r[0] <= merged[-1][1] + 1e-6:
            merged[-1][1] = max(merged[-1][1], r[1])
            merged[-1][2] += " + " + r[2]
            merged[-1][3] = (merged[-1][3] + " " + r[3]).strip()
        else:
            merged.append(r)
    keep, t = [], 0.0
    for s, e, *_ in merged:
        if s - t > 0:
            keep.append([t, s])
        t = e
    if dur - t > 0:
        keep.append([t, dur])
    # Tiny keeps are worse than no keep: fold them into the removal around them.
    keep = [k for k in keep if k[1] - k[0] >= a.min_keep or k[0] == 0.0]
    # Selects: keep only what falls inside each select, in the selects' order. A select's in point is a cut that ends
    # before the first word (snapped to its onset), its out point a cut that starts after the last word (in silence).
    labels, sel_out = [""] * len(keep), []
    if a.selects:
        sel = json.load(open(a.selects)); sel = sel["selects"] if isinstance(sel, dict) else sel
        ordered = []
        for x in sel:
            if "gap" in x:  # a slot for an insert (a clip, a card): black and silence of an exact frame count
                n = max(round(float(x["gap"]) * fps), 1)
                ordered.append(("gap", n / fps, x.get("label", "gap")))
                sel_out.append({"gap": round(n / fps, 4), "label": x.get("label", "gap")})
                continue
            s0, e0, clean_in, clean_out = float(x["in"]) - a.pad, float(x["out"]) + a.pad, True, True
            if snapper:
                (s0, clean_in), (e0, clean_out) = snapper.select_in(float(x["in"])), snapper.select_out(float(x["out"]))
            s0, e0 = snap(s0, up=False), snap(e0, up=True)
            sel_out.append({"in": round(s0, 4), "out": round(e0, 4), "label": x.get("label", ""),
                            **({} if clean_in else {"hard_in": "no silence before the first word"}),
                            **({} if clean_out else {"hard_out": "no silence after the last word"})})
            for ks, ke in keep:
                lo, hi = max(ks, s0), min(ke, e0)
                if ordered and ordered[-1][0] != "gap" and ordered[-1][0] <= lo < ordered[-1][1]:  # continuation: no repeated frames
                    lo = ordered[-1][1]
                if hi - lo >= a.min_keep:
                    ordered.append((lo, hi, x.get("label", "")))
        keep, labels = [[lo, hi] for lo, hi, _ in ordered], [lab for _, _, lab in ordered]
    gap_of = lambda k: k[1] if k[0] == "gap" else None
    frames = lambda x: round(x * fps)
    kept = sum(frames(e) if s == "gap" else frames(e) - frames(s) for s, e in keep) / fps

    # Retime words onto the cut timeline.
    retimed, offset_list, acc = [], [], 0.0
    for s, e in keep:
        if s == "gap":
            acc += frames(e) / fps; continue
        offset_list.append((s, e, acc)); acc += (frames(e) - frames(s)) / fps
    for w in words:
        for s, e, base in offset_list:
            if w["s"] >= s - 1e-6 and w["e"] <= e + 1e-6:
                retimed.append({"text": w["w"], "start": round(w["s"] - s + base, 3), "end": round(w["e"] - s + base, 3)})
                break
    retimed.sort(key=lambda w: w["start"])  # selects can put later source words earlier on the cut timeline
    os.makedirs(a.out, exist_ok=True)
    suggestions = [{"in": round(words[r["from"]]["s"], 3), "out": round(words[r["to"]]["s"], 3) if r["to"] < len(words) else dur,
                    "reason": r["reason"], "text": " ".join(w["w"] for w in words[r["from"]:r["to"]])}
                   for r in find_retakes(words, a.implicit_retakes) if not r["applied"]]
    # Store the source relative to the EDL so plans can be committed and moved; cut_render resolves it back.
    edl = {"source": os.path.relpath(os.path.abspath(a.media), os.path.abspath(a.out)), "fps": fps, "duration": round(dur, 3),
           "keep": [({"gap": round(e, 4)} if s == "gap" else {"in": round(s, 4), "out": round(e, 4)}) | ({"label": lab} if lab else {})
                    for (s, e), lab in zip(keep, labels)],
           "ordered": bool(a.selects), "selects": sel_out,
           "remove": [{"in": round(s, 4), "out": round(e, 4), "reason": why, "text": text} for s, e, why, text in merged],
           "suggested": suggestions,
           "stats": {"source_s": round(dur, 2), "cut_s": round(kept, 2), "removed_s": round(dur - kept, 2),
                     "removals": len(merged), "keeps": len(keep)}}
    json.dump(edl, open(os.path.join(a.out, "edl.json"), "w"), indent=1)
    json.dump([dict(id=f"w{i}", **w) for i, w in enumerate(retimed)], open(os.path.join(a.out, "words.cut.json"), "w"))
    mm = lambda x: f"{int(x // 60)}:{x % 60:05.2f}"
    lines = [f"# Keep list: {os.path.basename(a.media)}", "",
             f"{edl['stats']['source_s']}s source -> {edl['stats']['cut_s']}s cut ({edl['stats']['removed_s']}s removed in "
             f"{len(merged)} places). Veto a removal by adding its range to --protect and re-running.", "",
             "| # | source in | source out | length | reason | words removed |", "|---|---|---|---|---|---|"]
    for n, (s, e, why, text) in enumerate(merged, 1):
        lines.append(f"| {n} | {mm(s)} | {mm(e)} | {e - s:.2f}s | {why} | {text or '(silence)'} |")
    if sel_out:
        lines += ["", "## Selects, in output order", "", "| # | label | source in | source out | words |", "|---|---|---|---|---|"]
        for n, x in enumerate(sel_out, 1):
            if "gap" in x:
                lines.append(f"| {n} | {x['label']} | gap | {x['gap']:.2f}s | (black and silence: the slot for an insert) |"); continue
            txt = " ".join(w["w"] for w in words if w["s"] >= x["in"] - 1e-6 and w["e"] <= x["out"] + 1e-6)
            warn = "; ".join(v for k, v in x.items() if k.startswith("hard_"))
            lines.append(f"| {n} | {x['label']} | {mm(x['in'])} | {mm(x['out'])} | {txt[:140]}{' **HARD CUT: ' + warn + '**' if warn else ''} |")
    if suggestions:
        lines += ["", "## Suggested, not applied (implicit retakes)", ""]
        lines += [f"- {mm(x['in'])}-{mm(x['out'])}: {x['reason']}: \"{x['text']}\"" for x in suggestions]
    open(os.path.join(a.out, "KEEP-LIST.md"), "w").write("\n".join(lines) + "\n")
    for x in sel_out:
        for k, v in x.items():
            if k.startswith("hard_"):
                print(f"warning: select '{x['label']}': {v} (a hard cut; choose a different word or let the join check judge)")
    print(f"{dur:.2f}s -> {kept:.2f}s; {len(merged)} removals, {len(keep)} keeps"
          + (f" from {len(sel_out)} ordered selects" if sel_out else "") + f", {len(suggestions)} suggestions; "
          f"{len(retimed)}/{len(words)} words kept")


if __name__ == "__main__":
    main()
