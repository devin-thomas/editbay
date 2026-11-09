#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
"""Did the TTS say the script? Compare each narration sentence with what ASR heard, aligned by words (not times).

TTS garbles a sentence now and then (a valid-sounding take of the wrong words). Catch it before anything is timed
against the narration.

Usage:
  voiceover_check.py narration/narration.json transcript.json [--max-wer 0.15] [--glossary glossary.json]
transcript.json: faster-whisper JSON (segments with words) of narration.wav, or a HyperFrames word array.
Prints per-sentence word and character error rates (a sentence passes if either is under its limit, so
"time stamp" vs "timestamp" is not a failure) and a ready `--redo` list for voiceover.py. Exit 1 on any failure.
"""
import argparse, json, re, sys


ONES = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split()
TENS = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()


def spoken_number(n):
    """0-99 as words: ASR writes "Step 2" for a spoken "Step two"; both sides compare as words."""
    if n < 20:
        return ONES[n]
    return TENS[n // 10] + ("" if n % 10 == 0 else ONES[n % 10])


SYMBOLS = {"%": " percent ", "&": " and "}


def tokens(text):
    """Split on spaces after spelling out symbols ASR emits as their own tokens: "50%" or "50 %" is "fifty percent".
    EditorialPipeline 2026-09-28: a correct "50 percent ... Images 2.0" failed at WER 0.25 because norm() stripped the heard
    "%" and ASR split "2.0" into "2" ".0" (words_of rejoins that). Now 8/8 pass on both ASR passes; a changed script
    still fails (negative control); earlier Muse and GoCardless runs still pass."""
    for k, v in SYMBOLS.items():
        text = text.replace(k, v)
    return text.split()


def norm(w):
    w = re.sub(r"[^a-z0-9']", "", w.lower().replace("-", ""))
    return spoken_number(int(w)) if w.isdigit() and int(w) < 100 else w


def words_of(path):
    d = json.load(open(path))
    raw = [(w["start"], w["end"], w["text"]) for w in d] if isinstance(d, list) else \
        [(w[0], w[1], w[2]) for s in d["segments"] for w in s.get("words") or []]
    out = []
    for a, b, text in raw:
        if out and re.fullmatch(r"\.\d+[.,!?]?", text.strip()):   # ASR splits "2.0" into "2" ".0": rejoin it
            pa, _, pt = out[-1]
            out[-1] = (pa, b, pt + text.strip())
            continue
        out += [(a, b, t) for t in tokens(text)]
    return out


def wer(ref, hyp):
    r, h = [norm(x) for x in ref if norm(x)], [norm(x) for x in hyp if norm(x)]
    d = list(range(len(h) + 1))
    for i in range(1, len(r) + 1):
        prev, d[0] = d[0], i
        for j in range(1, len(h) + 1):
            cur = min(d[j] + 1, d[j - 1] + 1, prev + (r[i - 1] != h[j - 1]))
            prev, d[j] = d[j], cur
    return d[len(h)] / max(len(r), 1)


def cer(ref, hyp):
    """Character error rate with spaces removed: "timestamp" and "time stamp" are the same speech."""
    r = "".join(norm(x) for x in ref); h = "".join(norm(x) for x in hyp)
    return wer(list(r), list(h)) if r else 0.0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("narration"); ap.add_argument("transcript"); ap.add_argument("--max-wer", type=float, default=0.15)
    ap.add_argument("--max-cer", type=float, default=0.08)
    ap.add_argument("--glossary", help="reconcile-style glossary: variants count as the canonical word")
    a = ap.parse_args()
    nar = json.load(open(a.narration)); words = words_of(a.transcript)
    alias = {}
    if a.glossary:
        for t in json.load(open(a.glossary)).get("terms", []):
            for v in t["variants"]:
                alias[norm(v.replace(" ", ""))] = norm(t["canonical"].replace(" ", ""))
    # Assign heard words to sentences by aligning the whole transcript to the whole script, not by time windows:
    # Whisper stamps sentence starts 0.2-0.3 s early (into the pause), so windows drop first words.
    import difflib
    ref_tok, owner = [], []
    for k, s in enumerate(nar["sentences"]):
        for w in tokens(s["text"]):
            if norm(w):
                ref_tok.append(alias.get(norm(w), norm(w))); owner.append(k)
    hyp_words = [w for (_, _, w) in words if norm(w)]
    hyp_tok = [alias.get(norm(w), norm(w)) for w in hyp_words]
    heard_by = [[] for _ in nar["sentences"]]
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(a=ref_tok, b=hyp_tok, autojunk=False).get_opcodes():
        if op == "delete":
            continue
        k = owner[min(i1, len(owner) - 1)] if op != "insert" or i1 < len(owner) else owner[-1]
        if op == "insert" and i1 > 0 and (i1 == len(owner) or owner[i1] != owner[i1 - 1]):
            k = owner[i1 - 1]  # words heard between two sentences belong to the one that just ended
        if op in ("equal", "replace") and i2 > i1 and len({owner[x] for x in range(i1, i2)}) > 1:
            # A replace spanning a sentence boundary ("timestamp. um" vs "time stamp."): give each heard word to the
            # script word whose letters cover the heard word's letter midpoint.
            edges, pos = [], 0
            for x in range(i1, i2):
                pos += max(len(ref_tok[x]), 1); edges.append((pos, owner[x]))
            scale = pos / max(sum(max(len(hyp_tok[y]), 1) for y in range(j1, j2)), 1)
            acc = 0
            for y in range(j1, j2):
                mid = (acc + max(len(hyp_tok[y]), 1) / 2) * scale; acc += max(len(hyp_tok[y]), 1)
                heard_by[next((o for e_, o in edges if mid <= e_), edges[-1][1])].append(hyp_words[y])
            continue
        heard_by[k].extend(hyp_words[j1:j2])
    bad = []
    for k, s in enumerate(nar["sentences"]):
        heard = heard_by[k]
        ref = tokens(s["text"])
        hyp = [alias.get(norm(w), w) for w in heard]
        refa = [alias.get(norm(w), w) for w in ref]
        e, c = wer(refa, hyp), cer(refa, hyp)
        ok = e <= a.max_wer or c <= a.max_cer
        if not ok:
            bad.append(s["i"])
        print(f"[{s['i']:03d}] WER {e:4.2f} CER {c:4.2f} {'ok  ' if ok else 'FAIL'} {s['text']}" + ("" if ok else f"\n       heard: {' '.join(heard)}"))
    if bad:
        print(f"\n{len(bad)} sentence(s) failed. Regenerate: voiceover.py ... --redo {','.join(map(str, bad))}")
        sys.exit(1)
    print(f"\nall {len(nar['sentences'])} sentences match the script (WER <= {a.max_wer})")


if __name__ == "__main__":
    main()
