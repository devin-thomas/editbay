#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
"""Resolve a beat sheet into exact times and check it before anything is built.

A cue says what appears, where, and why, anchored to a spoken phrase ("when I say Fable 5.1") or a musical beat.
This turns anchors into seconds, checks the plan against the brand and the footage, and writes the artefacts the
build and the verifier use.

Usage:
  beats_check.py beats/beats.json [--out beats/] [--brand brands/x.json] [--open-loops beats/OPEN-LOOPS.json] [--strict]
beats.json:
  {"timeline": "cut", "words": "cut/words.cut.json", "grid": null, "fps": 60, "duration": 42.0,
   "faces": "media/talk.faces.json", "min_read": 2.5,
   "cues": [
     {"id": "C01", "anchor": "Fable 5.1", "occurrence": 1, "offset": -0.15, "hold": 2.5,
      "kind": "side-card", "zone": "left", "content": {"title": "Fable 5.1"}, "why": "he points left here"},
     {"id": "C02", "anchor": "best outputs ever", "until": "ever", "kind": "word-highlight", "zone": "bottom"},
     {"id": "C03", "beat": 16, "hold_beats": 4, "kind": "title", "zone": "center", "content": {"title": "..."}}
   ]}
  anchor: a phrase in the words (case/punctuation-insensitive); occurrence picks the Nth; offset shifts the start.
  until: end the cue at the end of this phrase (searched after the anchor) instead of a fixed hold.
  until_start: end the cue where this phrase starts (hold a scene until the next beat takes over; no empty gap).
  beat / hold_beats: music-led cues on grid.json beats (bar b, beat k -> index (b-1)*4 + k-1); half-beats like
  24.5 are interpolated on the grid.
  zone: left | right | top | bottom | center | full | pip-tl | pip-tr | pip-bl | pip-br.
  overlay_of: id of a cue this one deliberately layers on (a highlight over a rail): no shared-zone warning.
  text kinds (read time applies): title, side-card, lower-third, bullet, word-highlight, caption-slam, label.
  kind "sfx": a sound-only cue (its "sfx" names the sound); no element, no motion assertion.
Writes: beats.resolved.json, BEATS.md (table + per-zone timeline), <name>.motion.json (hyperframes check sidecar:
each cue appears by its start + 0.5 s, stays in frame, and keeps its order).
Exit 1 on errors (an anchor not found, a cue outside the piece); warnings are printed and listed in BEATS.md.
When OPEN-LOOPS.json is present, every question needs a payoff more than 2 seconds after its setup; an absent or
too-early payoff is an error.
"""
import argparse, difflib, json, os, re, sys

TEXT_KINDS = {"title", "side-card", "lower-third", "bullet", "word-highlight", "caption-slam", "label", "quote"}
ZONE_BOX = {"left": [0, 0, .38, 1], "right": [.62, 0, 1, 1], "top": [0, 0, 1, .22], "bottom": [0, .74, 1, 1],
            "center": [.25, .2, .75, .8], "full": [0, 0, 1, 1], "pip-tl": [0, 0, .3, .3], "pip-tr": [.7, 0, 1, .3],
            "pip-bl": [0, .7, .3, 1], "pip-br": [.7, .7, 1, 1]}


def norm(w):
    return re.sub(r"[^a-z0-9.']", "", w.lower().replace("-", "")).strip(".")


def load_words(path):
    d = json.load(open(path))
    if isinstance(d, list):
        return [(w["start"], w["end"], w["text"]) for w in d]
    return [(w[0], w[1], w[2].strip()) for s in d["segments"] for w in s.get("words") or []]


def find(words, phrase, occurrence=1, after=0.0):
    toks = [norm(t) for t in phrase.split() if norm(t)]
    keys = [norm(w[2]) for w in words]
    hits = [i for i in range(len(keys) - len(toks) + 1) if keys[i:i + len(toks)] == toks and words[i][0] >= after - 1e-6]
    if len(hits) >= occurrence:
        i = hits[occurrence - 1]
        return words[i][0], words[i + len(toks) - 1][1], None
    joined = [" ".join(keys[i:i + len(toks)]) for i in range(len(keys))]
    near = difflib.get_close_matches(" ".join(toks), joined, n=3, cutoff=0.5)
    return None, None, near


def overlap(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def check_open_loops(path, duration):
    """Validate the small, explicit curiosity ledger before motion work starts."""
    if not path:
        return [], []
    data = json.load(open(path))
    loops = data if isinstance(data, list) else data.get("loops")
    if not isinstance(loops, list):
        return [f"open loops: {path} must be a list or an object with a 'loops' list"], []
    errors, rows = [], []
    for i, loop in enumerate(loops, 1):
        label = (loop.get("id") or f"loop {i}") if isinstance(loop, dict) else f"loop {i}"
        if not isinstance(loop, dict):
            errors.append(f"{label}: entry must be an object")
            continue
        question = str(loop.get("question") or "").strip()
        if not question:
            errors.append(f"{label}: question is required")
        try:
            setup = float(loop["setup_time"])
        except (KeyError, TypeError, ValueError):
            errors.append(f"{label}: setup_time must be numeric")
            continue
        if "payoff_time" not in loop or loop.get("payoff_time") is None:
            errors.append(f"{label}: payoff_time is required (an open loop cannot remain unpaid)")
            continue
        try:
            payoff = float(loop["payoff_time"])
        except (TypeError, ValueError):
            errors.append(f"{label}: payoff_time must be numeric")
            continue
        if setup < 0 or setup > duration:
            errors.append(f"{label}: setup_time {setup:g}s is outside the {duration:g}s piece")
        if payoff < 0 or payoff > duration:
            errors.append(f"{label}: payoff_time {payoff:g}s is outside the {duration:g}s piece")
        if payoff - setup <= 2.0:
            errors.append(f"{label}: payoff must be more than 2s after setup ({setup:g}s -> {payoff:g}s)")
        rows.append((label, question, setup, payoff))
    return errors, rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("beats"); ap.add_argument("--out"); ap.add_argument("--brand"); ap.add_argument("--open-loops")
    ap.add_argument("--strict", action="store_true")
    a = ap.parse_args()
    base = os.path.dirname(os.path.abspath(a.beats))
    out = a.out or base
    sheet = json.load(open(a.beats))
    rel = lambda p: p if os.path.isabs(p) else os.path.join(base, p)
    words = load_words(rel(sheet["words"])) if sheet.get("words") else []
    grid = json.load(open(rel(sheet["grid"]))) if sheet.get("grid") else None
    faces = json.load(open(rel(sheet["faces"]))) if sheet.get("faces") else None
    brand = json.load(open(a.brand)) if a.brand else {}
    min_read = sheet.get("min_read") or brand.get("motion", {}).get("min_read_hold_s", 2.0)
    dur, fps = sheet["duration"], sheet.get("fps", 60)
    errors, warnings, resolved = [], [], []
    loops_path = a.open_loops
    if loops_path is None:
        candidate = os.path.join(base, "OPEN-LOOPS.json")
        loops_path = candidate if os.path.exists(candidate) else None
    loop_errors, loop_rows = check_open_loops(loops_path, dur) if loops_path else ([], [])
    errors.extend(loop_errors)
    for c in sheet["cues"]:
        r = dict(c)
        if "beat" in c:
            if not grid:
                errors.append(f"{c['id']}: beat cue but no grid"); continue
            beats = [b["t"] if isinstance(b, dict) else b for b in grid["beats"]]
            bi, frac = int(c["beat"]), c["beat"] - int(c["beat"])  # half-beats (24.5) interpolate on the grid
            if bi >= len(beats):
                errors.append(f"{c['id']}: beat {c['beat']} beyond the grid ({len(beats)} beats)"); continue
            spb = grid.get("seconds_per_beat") or (beats[1] - beats[0])
            r["start"] = beats[bi] + frac * spb + c.get("offset", 0.0)
            r["end"] = r["start"] + c.get("hold_beats", 2) * spb
        elif "anchor" in c:
            s, e, near = find(words, c["anchor"], c.get("occurrence", 1))
            if s is None:
                errors.append(f"{c['id']}: anchor '{c['anchor']}' not found" + (f"; nearest: {near}" if near else ""))
                continue
            r["start"] = max(s + c.get("offset", 0.0), 0.0)
            if c.get("until_start"):
                us, _, near2 = find(words, c["until_start"], 1, after=s + 0.01)
                if us is None:
                    errors.append(f"{c['id']}: until_start '{c['until_start']}' not found after the anchor"); continue
                r["end"] = us + c.get("tail", -0.05)
            elif c.get("until"):
                _, ue, near2 = find(words, c["until"], 1, after=s)
                if ue is None:
                    errors.append(f"{c['id']}: until '{c['until']}' not found after the anchor"); continue
                r["end"] = ue + c.get("tail", 0.4)
            else:
                r["end"] = r["start"] + c.get("hold", min_read)
            r["anchor_time"] = round(s, 3)
        elif "at" in c:
            r["start"] = float(c["at"]); r["end"] = r["start"] + c.get("hold", min_read)
        else:
            errors.append(f"{c['id']}: needs anchor, beat, or at"); continue
        r["start"], r["end"] = round(round(r["start"] * fps) / fps, 4), round(round(r["end"] * fps) / fps, 4)
        if r["end"] > dur + 1e-6:
            (errors if r["start"] >= dur else warnings).append(f"{c['id']}: ends at {r['end']:.2f}s, after the piece ({dur}s)")
        if c.get("kind") in TEXT_KINDS and r["end"] - r["start"] < min_read - 1e-6 and not c.get("flash"):
            warnings.append(f"{c['id']}: text on screen {r['end'] - r['start']:.2f}s < read time {min_read}s "
                            f"(mark \"flash\": true if it is meant to be a flash)")
        zone = c.get("zone")
        if faces and faces.get("keep_clear") and zone and zone != "full" and not c.get("cover_face"):
            if overlap(ZONE_BOX.get(zone, [0, 0, 0, 0]), faces["keep_clear"]):
                warnings.append(f"{c['id']}: zone '{zone}' overlaps the face keep-clear box {faces['keep_clear']}; "
                                f"use a free zone or set cover_face with a reason")
        resolved.append(r)
    resolved.sort(key=lambda r: r["start"])
    for i, p in enumerate(resolved):
        for q in resolved[i + 1:]:
            if q["start"] >= p["end"]:
                break
            layered = p.get("overlay_of") == q["id"] or q.get("overlay_of") == p["id"]
            if p.get("zone") and p.get("zone") == q.get("zone") and p.get("zone") != "full" and not layered:
                warnings.append(f"{p['id']} and {q['id']} share zone '{p['zone']}' between {q['start']:.2f}s and "
                                f"{min(p['end'], q['end']):.2f}s")
    for r in resolved:
        live = [x for x in resolved if x.get("kind") in TEXT_KINDS and x["start"] <= r["start"] < x["end"]]
        if len(live) > 2:
            warnings.append(f"{r['start']:.2f}s: {len(live)} text elements on screen at once ({', '.join(x['id'] for x in live)})")
    os.makedirs(out, exist_ok=True)
    json.dump({**{k: v for k, v in sheet.items() if k != "cues"}, "cues": resolved}, open(os.path.join(out, "beats.resolved.json"), "w"), indent=1)
    name = os.path.splitext(os.path.basename(sheet.get("composition", "index.html")))[0]
    motion = {"duration": dur, "assertions": []}
    visual = [r for r in resolved if r.get("kind") != "sfx"]  # sound-only cues place audio, not pixels
    for r in visual:
        sel = r.get("selector", f"#{r['id']}")
        motion["assertions"].append({"kind": "appearsBy", "selector": sel, "bySec": round(r["start"] + 0.5, 3)})
        if r.get("zone") != "full":
            motion["assertions"].append({"kind": "staysInFrame", "selector": sel})
    for p, q in zip(visual, visual[1:]):
        if q["start"] - p["start"] >= 0.3:
            motion["assertions"].append({"kind": "before", "a": p.get("selector", f"#{p['id']}"), "b": q.get("selector", f"#{q['id']}")})
    json.dump(motion, open(os.path.join(out, f"{name}.motion.json"), "w"), indent=1)
    mm = lambda t: f"{int(t // 60)}:{t % 60:05.2f}"
    lines = [f"# Beat sheet ({sheet.get('timeline', '?')} timeline, {dur}s @ {fps} fps)", "",
             "| id | in | out | anchor / beat | kind | zone | content | why |", "|---|---|---|---|---|---|---|---|"]
    for r in resolved:
        what = r.get("anchor") or (f"beat {r['beat']}" if "beat" in r else f"at {r.get('at')}")
        content = "; ".join(f"{k}: {v}" for k, v in (r.get("content") or {}).items())
        lines.append(f"| {r['id']} | {mm(r['start'])} | {mm(r['end'])} | {what} | {r.get('kind', '')} | {r.get('zone', '')} | "
                     f"{content} | {r.get('why', '')} |")
    lines += ["", "## Zones over time (each char = 0.5 s)", "", "```"]
    zones = sorted({r.get("zone") for r in resolved if r.get("zone")})
    n = int(dur / 0.5) + 1
    for z in zones:
        row = ["."] * n
        for r in resolved:
            if r.get("zone") == z:
                for k in range(int(r["start"] / 0.5), min(int(r["end"] / 0.5) + 1, n)):
                    row[k] = r["id"][-1]
        lines.append(f"{z:>8} |" + "".join(row))
    lines += ["```", ""]
    if loops_path:
        lines += ["## Open loops", "", "| id | question | setup | payoff |", "|---|---|---:|---:|"]
        lines += [f"| {label} | {question.replace('|', '/')} | {setup:g}s | {payoff:g}s |"
                  for label, question, setup, payoff in loop_rows]
        lines += [f"\nSource: `{os.path.basename(loops_path)}`; payoff must be more than 2 seconds after setup.", ""]
    if errors or warnings:
        lines += ["## Findings", ""] + [f"- ERROR {e}" for e in errors] + [f"- warn {w}" for w in warnings]
    open(os.path.join(out, "BEATS.md"), "w").write("\n".join(lines) + "\n")
    for e in errors:
        print("ERROR", e)
    for w in warnings:
        print("warn ", w)
    print(f"{len(resolved)}/{len(sheet['cues'])} cues resolved; {len(errors)} errors, {len(warnings)} warnings; "
          f"wrote beats.resolved.json, BEATS.md, {name}.motion.json in {out}")
    sys.exit(1 if errors or (a.strict and warnings) else 0)


if __name__ == "__main__":
    main()
