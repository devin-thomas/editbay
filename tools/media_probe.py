#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
"""Inventory media files: duration, geometry, frame rate, colour tags, audio, and warnings an edit would trip on.

Usage:
  media_probe.py PATH [PATH ...] [--json out.json] [--md out.md]
PATH may be a file or a folder (searched recursively for video/audio/image files).
Warnings flag things that silently break edits: variable frame rate, untagged colour (decodes as BT.601),
rotation metadata, odd dimensions, missing audio, very long files.
"""
import argparse, json, os, subprocess, sys
from fractions import Fraction

VIDEO = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v", ".mts", ".ts", ".flv"}
AUDIO = {".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg", ".opus"}
IMAGE = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".tif", ".tiff", ".bmp", ".svg"}


def ffprobe(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", path],
                       capture_output=True, text=True)
    return json.loads(r.stdout) if r.returncode == 0 and r.stdout else None


def rate(s):
    try:
        f = Fraction(s)
        return round(float(f), 3) if f else None
    except (ValueError, ZeroDivisionError, TypeError):
        return None


def probe(path):
    info = {"path": path, "bytes": os.path.getsize(path), "warnings": []}
    ext = os.path.splitext(path)[1].lower()
    d = ffprobe(path)
    if d is None:
        info["kind"] = "unreadable"; info["warnings"].append("ffprobe could not read this file")
        return info
    fmt = d.get("format", {})
    info["duration"] = round(float(fmt.get("duration", 0) or 0), 3)
    info["container"] = fmt.get("format_name")
    vs = [s for s in d["streams"] if s["codec_type"] == "video" and not s.get("disposition", {}).get("attached_pic")]
    aus = [s for s in d["streams"] if s["codec_type"] == "audio"]
    info["kind"] = "image" if ext in IMAGE else ("video" if vs else ("audio" if aus else "other"))
    if vs:
        v = vs[0]
        rot = 0
        for sd in v.get("side_data_list", []) or []:
            if "rotation" in sd:
                rot = int(sd["rotation"])
        rot = rot or int((v.get("tags") or {}).get("rotate", 0) or 0)
        info["video"] = {
            "codec": v.get("codec_name"), "width": v.get("width"), "height": v.get("height"),
            "fps": rate(v.get("avg_frame_rate")), "r_fps": rate(v.get("r_frame_rate")),
            "pix_fmt": v.get("pix_fmt"), "color_primaries": v.get("color_primaries"),
            "color_transfer": v.get("color_transfer"), "color_space": v.get("color_space"),
            "rotation": rot, "bit_rate": int(v["bit_rate"]) if v.get("bit_rate") else None,
            "frames": int(v["nb_frames"]) if v.get("nb_frames", "").isdigit() else None,
        }
        vi = info["video"]
        if info["kind"] == "video":
            if vi["fps"] and vi["r_fps"] and abs(vi["fps"] - vi["r_fps"]) > 0.05:
                info["warnings"].append(f"variable frame rate (avg {vi['fps']} vs nominal {vi['r_fps']}): conform to CFR before editing")
            if not vi["color_primaries"] or vi["color_primaries"] == "unknown":
                info["warnings"].append("untagged colour: decoders assume BT.601 for SD-sized and may shift HD colours; tag as bt709 when you re-encode")
            if not aus:
                info["warnings"].append("no audio stream")
            if info["duration"] > 1800:
                info["warnings"].append("longer than 30 min: work from proxies and transcripts, not frames")
        if rot:
            info["warnings"].append(f"rotation metadata {rot}°: frames extract unrotated unless the tool honours it")
        if (vi["width"] or 0) % 2 or (vi["height"] or 0) % 2:
            info["warnings"].append("odd dimensions: H.264 needs even width/height")
    if aus:
        a = aus[0]
        info["audio"] = {"codec": a.get("codec_name"), "channels": a.get("channels"),
                         "sample_rate": int(a["sample_rate"]) if a.get("sample_rate") else None,
                         "streams": len(aus)}
        if len(aus) > 1:
            info["warnings"].append(f"{len(aus)} audio streams: pick one explicitly (-map 0:a:N)")
    return info


def walk(paths):
    for p in paths:
        if os.path.isdir(p):
            for root, _, files in os.walk(p):
                for f in sorted(files):
                    if os.path.splitext(f)[1].lower() in VIDEO | AUDIO | IMAGE:
                        yield os.path.join(root, f)
        elif os.path.exists(p):
            yield p
        else:
            print(f"missing: {p}", file=sys.stderr)


def hms(t):
    t = int(round(t)); return f"{t // 3600}:{t % 3600 // 60:02d}:{t % 60:02d}"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="+"); ap.add_argument("--json"); ap.add_argument("--md")
    a = ap.parse_args()
    items = [probe(p) for p in walk(a.paths)]
    total = sum(i.get("duration", 0) for i in items if i["kind"] in ("video", "audio"))
    lines = [f"# Media inventory: {len(items)} files, {hms(total)} of audio/video, "
             f"{sum(i['bytes'] for i in items) / 1e9:.2f} GB", "",
             "| file | kind | duration | video | audio | warnings |", "|---|---|---|---|---|---|"]
    for i in items:
        v = i.get("video") or {}; au = i.get("audio") or {}
        vs = f"{v.get('width')}x{v.get('height')} {v.get('fps') or ''}fps {v.get('codec')}" if v else ""
        ass = f"{au.get('codec')} {au.get('channels')}ch {au.get('sample_rate')}" if au else ""
        lines.append(f"| {os.path.relpath(i['path'])} | {i['kind']} | {hms(i.get('duration', 0))} | {vs} | {ass} | "
                     f"{'; '.join(i['warnings'])} |")
    md = "\n".join(lines) + "\n"
    if a.json:
        json.dump(items, open(a.json, "w"), indent=1)
    if a.md:
        open(a.md, "w").write(md)
    if not a.json and not a.md:
        print(md)
    else:
        print(f"{len(items)} files, {hms(total)}; warnings on {sum(1 for i in items if i['warnings'])}")


if __name__ == "__main__":
    main()
