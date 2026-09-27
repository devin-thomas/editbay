#!/usr/bin/env python3
"""Reconcile a word-timestamped transcript against second opinions, then fix names with a glossary.

Pipeline (every change is logged):
  1. Majority vote: where the secondary transcript AND a third source (platform captions, or the script for
     narration) propose the same replacement for a span of the primary, take it (catches hallucinations such
     as "Wait," after long pauses, and dropped phrases). A token pass then drops single words the primary has
     that neither other source has at all (pure insertions).
  2. Patches: time-anchored find/replace for context-dependent fixes ("Cloud" -> "Kling" at 06:39),
     each with a reason. Applied before the glossary so they see the raw words.
  3. Glossary: canonical spellings for names and jargon ("Cloud Code" -> "Claude Code"), longest first.
  4. Flags: spans where all three sources disagree, and words the primary model was unsure of.

Inputs are faster-whisper JSON (see transcribe_faster_whisper.py) and optionally YouTube-style VTT or a script.
Only the primary needs word timestamps; stdlib only.

Usage:
  reconcile.py --primary a.json [--secondary b.json] [--captions c.vtt | --script s.md] [--glossary g.json]
               [--patches p.json] [--chapters info.json] --out stem
Writes stem.json (segments + words), stem.words.json (HyperFrames word array), stem.srt, stem.vtt,
stem.md (readable, by chapter) and stem.corrections.md.
"""
import argparse, difflib, html, json, re

PUNCT_TAIL = re.compile(r"[.,!?;:…]+$")


def norm(tok):
    """Comparison key: lowercase, no punctuation except internal dots (5.5, kie.ai)."""
    return re.sub(r"[^a-z0-9.']", "", tok.lower().replace("-", "")).strip(".")


def fmt(t, sep=","):
    h, rem = divmod(max(t, 0), 3600); m, s = divmod(rem, 60)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d}{sep}{int(round((s % 1) * 1000)) % 1000:03d}"


def mmss(t):
    return f"{int(t // 60):02d}:{int(t % 60):02d}"


def parse_time(s):
    parts = [float(p) for p in str(s).split(":")]
    t = 0.0
    for p in parts:
        t = t * 60 + p
    return t


def load_whisper(path):
    """Flat word list [{s,e,w,p,seg}] plus segment metadata."""
    d = json.load(open(path, encoding="utf-8"))
    words, segs = [], []
    for i, s in enumerate(d["segments"]):
        segs.append({"start": s["start"], "end": s["end"]})
        for w in s.get("words") or []:
            if norm(w[2]):
                words.append({"s": w[0], "e": w[1], "w": w[2], "p": w[3], "seg": i})
    return words, segs


def load_vtt(path):
    """Words from captions. YouTube auto-captions repeat the previous line as plain text in every cue,
    so when a file has word-timed <c> tags only those lines are read; plain VTT is read line by line."""
    out, seen = [], set()
    raw = open(path, encoding="utf-8").read()
    word_timed = "<c>" in raw
    for block in raw.split("\n\n"):
        lines = block.strip().splitlines()
        if not lines or "-->" not in lines[0]:
            continue
        t0 = parse_time(lines[0].split(" --> ")[0])
        for line in lines[1:]:
            if word_timed and "<c>" not in line:
                continue
            if "<c>" in line:
                pieces = [(t0, re.split(r"<\d", line)[0])] + [
                    (parse_time(f"{a}:{b}:{c}"), w)
                    for a, b, c, w in re.findall(r"<(\d+):(\d+):([\d.]+)><c>([^<]*)</c>", line)]
            else:
                pieces = [(t0, line)]
            for t, chunk in pieces:
                for tok in html.unescape(re.sub(r"<[^>]+>", "", chunk)).split():
                    if norm(tok) and (round(t, 2), tok) not in seen:
                        seen.add((round(t, 2), tok))
                        out.append({"s": t, "e": t, "w": " " + tok, "p": 1.0, "seg": -1})
    return out


def load_script(path):
    """Words of the intended text (a script) with no timings: a third opinion for narration."""
    text = open(path, encoding="utf-8").read()
    text = re.sub(r"~~~.*?~~~|<!--.*?-->", "", text, flags=re.S)
    text = "\n".join(l for l in text.splitlines() if not l.strip().startswith(("#", ">")))
    text = re.sub(r"\[[A-Za-z]\w*\]", "", text)
    return [{"s": 0.0, "e": 0.0, "w": " " + tok, "p": 1.0, "seg": -1} for tok in text.split() if norm(tok)]


def spread(tokens, s, e, seg, p=1.0):
    """Give replacement tokens evenly spaced timestamps across [s, e]."""
    n = max(len(tokens), 1); step = (e - s) / n if e > s else 0.0
    return [{"s": round(s + i * step, 2), "e": round(s + (i + 1) * step, 2), "w": " " + t, "p": p, "seg": seg}
            for i, t in enumerate(tokens)]


def majority(A, B, C, log):
    """Replace spans of A where B and C independently agree on the same alternative."""
    key = lambda ws: [norm(w["w"]) for w in ws]
    ab = difflib.SequenceMatcher(a=key(A), b=key(B), autojunk=False).get_opcodes()
    ac = difflib.SequenceMatcher(a=key(A), b=key(C), autojunk=False).get_opcodes()
    c_alt = {(i1, i2): " ".join(key(C[j1:j2])) for op, i1, i2, j1, j2 in ac if op != "equal"}
    out, flags, i = [], [], 0
    for op, i1, i2, j1, j2 in ab:
        if op == "equal":
            continue
        b_alt = " ".join(key(B[j1:j2]))
        if c_alt.get((i1, i2)) == b_alt:
            out.extend(A[i:i1])
            seg = A[i1]["seg"] if i1 < len(A) else A[-1]["seg"]
            new = [dict(w, seg=seg) for w in B[j1:j2]]
            before = "".join(w["w"] for w in A[i1:i2]).strip() or "∅"
            after = "".join(w["w"] for w in new).strip() or "∅"
            t = A[i1]["s"] if i1 < len(A) else A[-1]["e"]
            log.append(("majority", t, before, after, "secondary + third source agree"))
            out.extend(new); i = i2
        else:
            t = A[i1]["s"] if i1 < len(A) else A[-1]["e"]
            flags.append((t, "".join(w["w"] for w in A[i1:i2]).strip(), "".join(w["w"] for w in B[j1:j2]).strip(),
                          c_alt.get((i1, i2))))
    out.extend(A[i:])
    return prune_insertions(out, B, C, log), flags


def prune_insertions(A, B, C, log, max_run=4):
    """Token pass for what span voting misses: a word in A that neither B nor C has at that spot is an insertion
    (Whisper's "Wait," after a pause). Runs longer than max_run are left for a human: that is drift, not noise.
    Precision over recall: an insertion that sits inside a block where the sources heard different words is left
    alone and listed under unresolved disagreements; fix it with a patch after checking the audio."""
    key = lambda ws: [norm(w["w"]) for w in ws]
    ka = key(A)

    def orphans(other):
        """True where A's word sits in a pure delete: the other source has nothing at all opposite it.
        A replace (the other source heard *something* else there) is a substitution, not an insertion."""
        orphan = [False] * len(A)
        for op, i1, i2, j1, j2 in difflib.SequenceMatcher(a=ka, b=key(other), autojunk=False).get_opcodes():
            if op == "delete":
                for k in range(i1, i2):
                    orphan[k] = True
        return orphan

    ob, oc = orphans(B), orphans(C)
    drop = [ob[k] and oc[k] for k in range(len(A))]
    k, out = 0, []
    while k < len(A):
        if drop[k]:
            j = k
            while j < len(A) and drop[j]:
                j += 1
            if j - k <= max_run:
                log.append(("majority", A[k]["s"], "".join(w["w"] for w in A[k:j]).strip(), "∅",
                            "insertion: neither the secondary nor the third source has it"))
                k = j; continue
            out.extend(A[k:j]); k = j; continue
        out.append(A[k]); k += 1
    return out


def replace_window(words, k, n, tokens, log, kind, why):
    old = words[k:k + n]
    tail = PUNCT_TAIL.search(old[-1]["w"].strip()) if old else None
    toks = list(tokens)
    if toks and tail and not PUNCT_TAIL.search(toks[-1]):
        toks[-1] += tail.group(0)
    new = spread(toks, old[0]["s"], old[-1]["e"], old[0]["seg"]) if toks else []
    log.append((kind, old[0]["s"], "".join(w["w"] for w in old).strip(), " ".join(toks) or "∅", why))
    words[k:k + n] = new
    return len(new)


def apply_patches(words, patches, log):
    for p in patches:
        at, find = parse_time(p["at"]), [norm(t) for t in p["find"].split()]
        rep = p["replace"].split() if p["replace"] else []
        best = None
        for k in range(len(words) - len(find) + 1):
            if [norm(w["w"]) for w in words[k:k + len(find)]] == find:
                d = abs(words[k]["s"] - at)
                if d <= p.get("window", 15) and (best is None or d < best[1]):
                    best = (k, d)
        if best is None:
            log.append(("patch-miss", at, p["find"], p["replace"], "NOT FOUND near anchor: " + p.get("why", "")))
            continue
        replace_window(words, best[0], len(find), rep, log, "patch", p.get("why", ""))


def apply_glossary(words, glossary, log):
    rules = []
    for term in glossary.get("terms", []):
        for v in term["variants"]:
            rules.append(([norm(t) for t in v.split()], term["canonical"].split(), term.get("why", "")))
    rules.sort(key=lambda r: -len(r[0]))
    k = 0
    while k < len(words):
        for find, canon, why in rules:
            n = len(find)
            if [norm(w["w"]) for w in words[k:k + n]] == find:
                current = [w["w"].strip() for w in words[k:k + n]]
                if [PUNCT_TAIL.sub("", c) for c in current] != canon:
                    k += replace_window(words, k, n, canon, log, "glossary", why) - 1
                break
        k += 1


def merge_hyphenated_words(words, log):
    """Keep ASR timing while making split compounds one caption and beat token."""
    merged = []
    for word in words:
        token = word["w"].strip()
        if merged and token.startswith("-") and token != "-":
            previous = merged[-1]
            before = (previous["w"] + word["w"]).strip()
            previous["w"] = previous["w"].rstrip() + token
            previous["e"] = word["e"]
            log.append(("caption-normalize", previous["s"], before, previous["w"].strip(),
                        "joined ASR hyphen suffix; spoken audio unchanged"))
        else:
            merged.append(dict(word))
    return merged


def rebuild_segments(words, n_segs, segs):
    buckets = [[] for _ in range(n_segs)]
    for w in words:
        buckets[max(w["seg"], 0)].append(w)
    out, prev_end = [], "."
    for i, ws in enumerate(buckets):
        if not ws:
            continue
        text = re.sub(r"(\w) -(\w)", r"\1-\2", "".join(w["w"] for w in ws)).strip()
        # Removing an insertion ("Wait, so ...") can leave a sentence starting in lower case. Segments often start
        # mid-sentence, so capitalise a segment's first word only when the previous segment ended a sentence.
        text = re.sub(r"([.!?]\s+)([a-z])", lambda m: m.group(1) + m.group(2).upper(), text)
        if re.search(r"[.!?]$", prev_end) and text[:1].islower():
            text = text[0].upper() + text[1:]
        prev_end = text
        out.append({"start": round(min(ws[0]["s"], segs[i]["start"]), 2), "end": round(max(ws[-1]["e"], segs[i]["end"]), 2),
                    "text": text, "words": [[w["s"], w["e"], w["w"], w["p"]] for w in ws]})
    return out


def write_md(segs, chapters, notes, path, title):
    notes = sorted(notes, key=lambda n: n[0])
    lines, para, para_start, ch_i, n_i = [f"# {title}", ""], [], None, 0, 0

    def flush():
        nonlocal para, para_start
        if para:
            lines.extend([f"**[{mmss(para_start)}]** " + " ".join(para), ""])
        para, para_start = [], None

    for s in segs:
        while ch_i < len(chapters) and s["start"] >= chapters[ch_i]["start_time"] - 0.5:
            flush(); lines.extend([f"## {mmss(chapters[ch_i]['start_time'])} {chapters[ch_i]['title']}", ""]); ch_i += 1
        while n_i < len(notes) and s["start"] >= notes[n_i][0]:
            flush(); lines.extend([f"*[{mmss(notes[n_i][0])}] {notes[n_i][1]}*", ""]); n_i += 1
        if para_start is None:
            para_start = s["start"]
        para.append(s["text"])
        if len(" ".join(para).split()) > 55 and re.search(r"[.!?]$", s["text"]):
            flush()
    flush()
    open(path, "w", encoding="utf-8").write("\n".join(lines))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--primary", required=True); ap.add_argument("--secondary"); ap.add_argument("--captions")
    ap.add_argument("--script", help="intended text (narration script) used as the third opinion instead of captions")
    ap.add_argument("--glossary"); ap.add_argument("--patches"); ap.add_argument("--chapters")
    ap.add_argument("--title", default="Transcript"); ap.add_argument("--out", required=True)
    ap.add_argument("--low", type=float, default=0.4, help="flag primary words below this probability")
    a = ap.parse_args()

    A, segs = load_whisper(a.primary)
    log, flags = [], []
    third = load_vtt(a.captions) if a.captions else (load_script(a.script) if a.script else None)
    if a.secondary and third:
        B, _ = load_whisper(a.secondary)
        A, flags = majority(A, B, third, log)
    patches = json.load(open(a.patches, encoding="utf-8")) if a.patches else {}
    apply_patches(A, patches.get("patches", []), log)
    if a.glossary:
        apply_glossary(A, json.load(open(a.glossary, encoding="utf-8")), log)
    A = merge_hyphenated_words(A, log)
    out = rebuild_segments(A, len(segs), segs)

    chapters = json.load(open(a.chapters, encoding="utf-8")).get("chapters") or [] if a.chapters else []
    notes = [(parse_time(n["at"]), n["note"]) for n in patches.get("notes", [])]
    json.dump({"source": a.primary, "segments": out}, open(a.out + ".json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    # HyperFrames caption input: a flat, normalized word array (`hyperframes transcribe <file>` imports it as-is).
    flat = [w for s in out for w in s["words"] if w[2].strip()]
    json.dump([{"id": f"w{i}", "text": w[2].strip(), "start": w[0], "end": w[1]} for i, w in enumerate(flat)],
              open(a.out + ".words.json", "w", encoding="utf-8"), ensure_ascii=False)
    with open(a.out + ".srt", "w", encoding="utf-8") as f:
        for i, s in enumerate(out, 1):
            f.write(f"{i}\n{fmt(s['start'])} --> {fmt(s['end'])}\n{s['text']}\n\n")
    with open(a.out + ".vtt", "w", encoding="utf-8") as f:
        f.write("WEBVTT\n\n" + "".join(f"{fmt(s['start'], '.')} --> {fmt(s['end'], '.')}\n{s['text']}\n\n" for s in out))
    write_md(out, chapters, notes, a.out + ".md", a.title)

    with open(a.out + ".corrections.md", "w", encoding="utf-8") as f:
        f.write(f"# Corrections log\n\n{len(log)} changes. Sources: primary `{a.primary}`, secondary `{a.secondary}`, "
                f"third `{a.captions or a.script}`.\n\n| at | kind | before | after | why |\n|---|---|---|---|---|\n")
        for kind, t, before, after, why in sorted(log, key=lambda r: r[1]):
            f.write(f"| {mmss(t)} | {kind} | {before} | {after} | {why} |\n")
        f.write("\n## Unresolved disagreements (primary vs secondary; third source shown when it differs too)\n\n")
        fixed_at = [r[1] for r in log if r[0] in ("patch", "glossary")]
        for t, pa, pb, pc in flags:
            if norm(pa.replace(" ", "")) != norm(pb.replace(" ", "")):
                done = " — addressed by a patch/glossary fix" if any(abs(t - x) < 2.5 for x in fixed_at) else ""
                f.write(f"- {mmss(t)}: primary `{pa or '∅'}` / secondary `{pb or '∅'}`"
                        + (f" / third `{pc}`" if pc is not None else "") + done + "\n")
        low = [w for s in out for w in s["words"] if w[3] < a.low]
        f.write(f"\n## Low-confidence primary words (< {a.low}): {len(low)}\n\n")
        f.write(", ".join(f"{mmss(w[0])} {w[2].strip()}({w[3]:.2f})" for w in low) + "\n")
    print(f"{len(out)} segments; {len(log)} changes ({sum(1 for r in log if r[0]=='majority')} majority, "
          f"{sum(1 for r in log if r[0]=='patch')} patch, {sum(1 for r in log if r[0]=='glossary')} glossary, "
          f"{sum(1 for r in log if r[0]=='caption-normalize')} caption-normalize, "
          f"{sum(1 for r in log if r[0]=='patch-miss')} patch misses); {len(flags)} unresolved spans")


if __name__ == "__main__":
    main()
