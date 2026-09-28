#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
"""Assemble a delivery folder: the files, captions, chapters (only if valid), thumbnail candidates, a description draft,
and a manifest with hashes and measured loudness for every delivered file.

Usage:
  deliver.py --out deliver/ --slug five-step-edit-loop \
    --file master=renders/master-4k.mp4 --file review=renders/review.mp4 --file vertical=renders/vertical.mp4 \
    --words narration/words.words.json [--beats beats/beats.resolved.json --chapter-kinds step,chapter] \
    [--chapter "0:00 Intro"] [--thumb-from renders/review.mp4 --thumb-at 6.6,45.8,57.5] \
    [--asset designed-thumb=PATH] [--asset cover=PATH] [--asset-name cover=SLUG-cover.jpg]
    [--title "..."] [--summary "..."] [--disclosure "..."] [--credit "Music: ..."]
Captions: SRT and VTT from the verified word timings (7 words / 34 characters per line, breaks at pauses and sentence
ends). Hyphenated ASR tokens such as `one` + `-time` are joined before cue assembly, and overlong assembled lines fail.
Chapters follow YouTube's rules (first at 0:00, at least three, each at least 10 s); invalid chapter lists are reported,
not written. Thumbnails are frame candidates (A/B/C, no pick); designed assets are copied and measured as first-class files.
"""
import argparse, hashlib, json, os, re, shutil, subprocess, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))


def ts(t, sep=","):
    h, rem = divmod(max(t, 0), 3600); m, s = divmod(rem, 60)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d}{sep}{int(round((s % 1) * 1000)) % 1000:03d}"


def mmss(t):
    t = int(round(t)); return f"{t // 60}:{t % 60:02d}" if t < 3600 else f"{t // 3600}:{t % 3600 // 60:02d}:{t % 60:02d}"


def load_words(path):
    d = json.load(open(path))
    if isinstance(d, list):
        return [{"text": w["text"], "start": w["start"], "end": w["end"]} for w in d]
    return [{"text": w[2].strip(), "start": w[0], "end": w[1]} for s in d["segments"] for w in s["words"]]


def merge_hyphenated(words):
    """Join ASR's split `word` + `-suffix` tokens without changing their timing span."""
    merged = []
    for word in words:
        token = word["text"].strip()
        if merged and token.startswith("-") and token != "-":
            merged[-1]["text"] = merged[-1]["text"].rstrip() + token
            merged[-1]["end"] = word["end"]
        else:
            merged.append(dict(word))
    return merged


def line_text(line):
    return " ".join(w["text"] for w in line)


def caption_lines(words, max_words=7, max_chars=34, gap=0.35):
    words = merge_hyphenated(words)
    lines, cur = [], []
    for i, w in enumerate(words):
        if cur and (len(cur) >= max_words or len(line_text(cur + [w])) > max_chars):
            lines.append(cur)
            cur = []
        cur.append(w)
        nxt = words[i + 1] if i + 1 < len(words) else None
        text = line_text(cur)
        if (nxt is None or re.search(r"[.!?]$", w["text"])
                or (nxt and nxt["start"] - w["end"] > gap)):
            lines.append(cur); cur = []
    too_wide = [(i + 1, line_text(line), len(line_text(line))) for i, line in enumerate(lines) if len(line_text(line)) > max_chars]
    if too_wide:
        details = "; ".join(f"cue {i} is {n} chars" for i, _, n in too_wide)
        raise SystemExit(f"deliver: assembled caption line exceeds {max_chars} characters ({details})")
    return lines


def probe(path):
    d = json.loads(subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", path],
                                  capture_output=True, text=True).stdout)
    v = next((s for s in d["streams"] if s["codec_type"] == "video"), {})
    a = next((s for s in d["streams"] if s["codec_type"] == "audio"), {})
    fr = v.get("r_frame_rate", "0/1").split("/")
    return {"duration": round(float(d["format"]["duration"]), 3), "video": f"{v.get('codec_name')} {v.get('width')}x{v.get('height')}"
            f" {round(float(fr[0]) / float(fr[1]), 3) if v else ''}fps", "audio": f"{a.get('codec_name')} {a.get('sample_rate')} Hz" if a else None}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True); ap.add_argument("--slug", required=True)
    ap.add_argument("--file", action="append", default=[], help="variant=path (master, review, vertical, ...)")
    ap.add_argument("--asset", action="append", default=[], help="designed asset variant=path (for example cover=cover.jpg)")
    ap.add_argument("--asset-name", action="append", default=[], metavar="VARIANT=FILENAME",
                    help="destination filename for a designed asset; otherwise its source basename is kept")
    ap.add_argument("--words"); ap.add_argument("--beats"); ap.add_argument("--chapter-kinds", default="step,chapter")
    ap.add_argument("--chapter", action="append", default=[], help='"0:00 Title" (overrides chapters from the beat sheet)')
    ap.add_argument("--thumb-from"); ap.add_argument("--thumb-at", default="")
    ap.add_argument("--title", default=""); ap.add_argument("--summary", default="")
    ap.add_argument("--disclosure", default=""); ap.add_argument("--credit", action="append", default=[])
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    delivered, notes = [], []
    asset_names = {}
    for spec in a.asset_name:
        if "=" not in spec:
            raise SystemExit("deliver: --asset-name must be VARIANT=FILENAME")
        variant, filename = spec.split("=", 1)
        if (not variant or not filename or os.path.basename(filename) != filename
                or filename in (".", "..")):
            raise SystemExit("deliver: --asset-name filename must be a plain destination basename")
        if variant in asset_names:
            raise SystemExit(f"deliver: duplicate --asset-name for variant {variant!r}")
        asset_names[variant] = filename
    for spec in a.file:
        variant, path = spec.split("=", 1)
        dst = os.path.join(a.out, f"{a.slug}-{variant}{os.path.splitext(path)[1]}")
        shutil.copy2(path, dst); delivered.append((variant, dst))
    for spec in a.asset:
        if "=" not in spec:
            raise SystemExit("deliver: --asset must be VARIANT=PATH")
        variant, path = spec.split("=", 1)
        if not variant or not path:
            raise SystemExit("deliver: --asset must include a variant and path")
        dst = os.path.join(a.out, asset_names.get(variant, os.path.basename(path)))
        shutil.copy2(path, dst)
        delivered.append((variant, dst))
    if a.words:
        lines = caption_lines(load_words(a.words))
        with open(os.path.join(a.out, f"{a.slug}.en.srt"), "w") as f:
            for i, l in enumerate(lines, 1):
                f.write(f"{i}\n{ts(l[0]['start'])} --> {ts(l[-1]['end'])}\n{' '.join(w['text'] for w in l)}\n\n")
        with open(os.path.join(a.out, f"{a.slug}.en.vtt"), "w") as f:
            f.write("WEBVTT\n\n" + "".join(f"{ts(l[0]['start'], '.')} --> {ts(l[-1]['end'], '.')}\n{' '.join(w['text'] for w in l)}\n\n"
                                         for l in lines))
        delivered += [("captions", os.path.join(a.out, f"{a.slug}.en.srt")), ("captions", os.path.join(a.out, f"{a.slug}.en.vtt"))]
    # Chapters
    chapters = []
    if a.chapter:
        for c in a.chapter:
            t, title = c.split(" ", 1)
            p = [float(x) for x in t.split(":")]
            chapters.append((p[0] * 60 + p[1] if len(p) == 2 else p[0] * 3600 + p[1] * 60 + p[2], title))
    elif a.beats:
        kinds = set(a.chapter_kinds.split(","))
        cues = [c for c in json.load(open(a.beats))["cues"] if c.get("kind") in kinds]
        chapters = [(c["start"], (c.get("content") or {}).get("title", c["id"])) for c in cues]
        if chapters and chapters[0][0] > 0.5:
            chapters.insert(0, (0.0, "Intro"))
    dur = max((probe(p)["duration"] for v, p in delivered if p.endswith(".mp4")), default=0)
    if chapters:
        chapters[0] = (0.0, chapters[0][1])
        lens = [(b[0] if b else dur) - a_[0] for a_, b in zip(chapters, chapters[1:] + [None])]
        problems = []
        if len(chapters) < 3:
            problems.append(f"only {len(chapters)} chapters (YouTube needs at least 3)")
        short = [f"'{c[1]}' {l:.1f}s" for c, l in zip(chapters, lens) if l < 10]
        if short:
            problems.append("chapters shorter than 10 s: " + ", ".join(short))
        if problems:
            notes.append("Chapters not written: " + "; ".join(problems) + ". Merge sections or skip chapters for this length.")
        else:
            open(os.path.join(a.out, "chapters.txt"), "w").write("\n".join(f"{mmss(t)} {title}" for t, title in chapters) + "\n")
            delivered.append(("chapters", os.path.join(a.out, "chapters.txt")))
    # Thumbnail candidates
    for k, t in enumerate([float(x) for x in a.thumb_at.split(",") if x.strip()]):
        dst = os.path.join(a.out, f"{a.slug}-thumb-{'ABCDEFG'[k]}.jpg")
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", str(t), "-i", a.thumb_from, "-frames:v", "1",
                        "-vf", "scale=1280:720:out_range=pc,format=yuvj420p", "-q:v", "2", dst], check=True)
        delivered.append((f"thumb-{'ABCDEFG'[k]}", dst))
    # Manifest with measured loudness
    manifest = []
    for variant, path in delivered:
        item = {"variant": variant, "file": os.path.basename(path), "bytes": os.path.getsize(path),
                "sha256": hashlib.sha256(open(path, "rb").read()).hexdigest()}
        if path.endswith((".mp4", ".mov", ".webm")):
            item.update(probe(path))
            # loudness.py's printed line and its JSON would race on stdout: give the JSON its own file.
            tmpj = os.path.join(tempfile.mkdtemp(), "lu.json")
            subprocess.run(["python3", os.path.join(HERE, "loudness.py"), path, "--json", tmpj], capture_output=True, text=True)
            try:
                lu = json.load(open(tmpj))[0]
                item["loudness"] = {"lufs": lu["integrated_lufs"], "true_peak_dbtp": lu["true_peak_dbtp"]}
            except (OSError, ValueError, KeyError, IndexError):
                item["loudness"] = None
        elif path.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
            media = json.loads(subprocess.run(
                ["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", path],
                capture_output=True, text=True, check=True).stdout)
            video = next((s for s in media["streams"] if s.get("codec_type") == "video"), {})
            item["dimensions"] = f"{video.get('width')}x{video.get('height')}"
            item["media"] = "image"
        manifest.append(item)
    json.dump(manifest, open(os.path.join(a.out, "manifest.json"), "w"), indent=1)
    lines = [f"# Delivery: {a.title or a.slug}", "", "## Files", "", "| variant | file | size | spec | loudness |", "|---|---|---|---|---|"]
    for m in manifest:
        lu = m.get("loudness") or {}
        spec = m.get("video") or m.get("dimensions", "")
        duration = m.get("duration", "")
        lines.append(f"| {m['variant']} | {m['file']} | {m['bytes'] / 1e6:.1f} MB | {spec} {duration} |"
                     f" {str(lu.get('lufs', '')) + ' LUFS / ' + str(lu.get('true_peak_dbtp', '')) + ' dBTP' if lu else ''} |")
    lines += ["", "SHA-256 for every file: manifest.json.", ""]
    if notes:
        lines += ["## Notes", ""] + [f"- {n}" for n in notes] + [""]
    desc = [a.summary] if a.summary else []
    if a.disclosure:
        desc += ["", a.disclosure]
    if a.credit:
        desc += [""] + a.credit
    lines += ["## Description draft", "", "```", a.title, "", *desc, "```", ""]
    open(os.path.join(a.out, "DELIVERY.md"), "w").write("\n".join(lines))
    print(f"delivered {len(manifest)} files to {a.out}" + (f"; notes: {len(notes)}" if notes else ""))
    for n in notes:
        print("note:", n)


if __name__ == "__main__":
    main()
