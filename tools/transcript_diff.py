#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
"""Expected words vs heard words, with the audio as referee.

Use it to verify a cut (expected = cut_plan's words.cut.json), captions (expected = the caption word list), or a
narration (expected = the script). Missing or changed expected words are findings; extra words are
listed for a listen (see Usage).

Usage:
  transcript_diff.py EXPECTED HEARD [--json diff.json]
EXPECTED/HEARD: HyperFrames word arrays ([{text,start,end}]) or faster-whisper JSON (segments with words).
Exit 1 when an expected word is missing or changed. Insertions are listed for review, never failed: ASR invents
words over pauses and moves the next word's timestamps to make room, so the transcript cannot judge them.
"""
import argparse, difflib, json, re, sys


ONES = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split()
TENS = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()


def norm(w):
    """ASR writes "Step 2" for a spoken "Step two": compare numbers 0-99 as words."""
    w = re.sub(r"[^a-z0-9']", "", w.lower().replace("-", ""))
    if w.isdigit() and int(w) < 100:
        n = int(w)
        return ONES[n] if n < 20 else TENS[n // 10] + ("" if n % 10 == 0 else ONES[n % 10])
    return w


def words(path):
    d = json.load(open(path))
    if isinstance(d, list):
        return [(w["start"], w["end"], w["text"].strip()) for w in d if norm(w["text"])]
    return [(w[0], w[1], w[2].strip()) for s in d["segments"] for w in s.get("words") or [] if norm(w[2])]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("expected"); ap.add_argument("heard"); ap.add_argument("--json")
    a = ap.parse_args()
    E, H = words(a.expected), words(a.heard)
    ke = ["".join(norm(w[2]) for w in [x]) for x in E]; kh = [norm(w[2]) for w in H]
    findings, review = [], []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(a=ke, b=kh, autojunk=False).get_opcodes():
        if op == "equal":
            continue
        exp = " ".join(w[2] for w in E[i1:i2]); got = " ".join(w[2] for w in H[j1:j2])
        # "time stamp" vs "timestamp": same letters, different spacing, not a finding.
        if "".join(ke[i1:i2]) == "".join(kh[j1:j2]):
            continue
        t = E[i1][0] if i1 < len(E) else (H[j1][0] if j1 < len(H) else 0)
        if op == "insert":
            # ASR invents words over short pauses and then shifts the next word's timestamps to make room, so an
            # insertion cannot be judged from the transcript. List it for a listen; objective leftover checks live
            # in cut_render.py (every join must sit in silence).
            review.append({"t": round(H[j1][0], 2), "kind": "insertion", "heard": got})
            continue
        else:
            findings.append({"t": round(t, 2), "kind": "missing" if op == "delete" else "changed", "expected": exp, "heard": got})
    for f in findings:
        print(f"FINDING {f['t']:7.2f}s {f['kind']}: expected '{f.get('expected', '')}' heard '{f.get('heard', '')}'")
    for r in review:
        print(f"review  {r['t']:7.2f}s ASR heard an extra '{r['heard']}' (often invented over a pause: listen once)")
    print(f"{len(E)} expected words, {len(H)} heard; {len(findings)} findings, {len(review)} insertions to review")
    if a.json:
        json.dump({"findings": findings, "review": review}, open(a.json, "w"), indent=1)
    sys.exit(1 if findings else 0)


if __name__ == "__main__":
    main()
