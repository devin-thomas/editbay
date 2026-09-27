#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pillow>=10"]
# ///
"""Labelled contact sheets and cut strips: the cheapest way for an agent (or a person) to *look* at a video.

One sheet beats N single-frame views: attaching an image re-prices the whole context, so batch checks.

Modes (pick one):
  --every S          one frame every S seconds (overview; 2 s for a 30 s piece, 5-10 s for long talks)
  --count N          N frames evenly spaced
  --at T,T,...       explicit timestamps (seconds or mm:ss / hh:mm:ss)
  --around T,T,...   a strip per timestamp: frames at -2f, -1f, 0, +1f, +2f (cut / transition checks)
  --cuts FILE.json   --around every cut in a scene_cuts.py JSON

Usage:
  contact_sheet.py VIDEO --every 5 --out sheets/overview
  contact_sheet.py render.mp4 --cuts cuts.json --out qa/cut-strips
Writes OUT_01.jpg, OUT_02.jpg, ... (rows x cols per sheet) and prints the paths.
"""
import argparse, json, os, subprocess, tempfile
from PIL import Image, ImageDraw, ImageFont


def parse_t(s):
    t = 0.0
    for p in str(s).strip().split(":"):
        t = t * 60 + float(p)
    return t


def label(t):
    m, s = divmod(t, 60)
    return f"{int(m)}:{s:05.2f}" if s % 1 else f"{int(m)}:{int(s):02d}"


def probe(video):
    """Duration of the VIDEO stream (containers often run a few frames longer than the picture) and fps."""
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=r_frame_rate,duration:format=duration", "-of", "json", video], capture_output=True, text=True)
    d = json.loads(out.stdout)
    num, den = d["streams"][0]["r_frame_rate"].split("/")
    dur = float(d["streams"][0].get("duration") or d["format"]["duration"])
    return dur, float(num) / float(den)


def grab(video, t, width, path, fps=30.0):
    # -ss before -i is frame-accurate in modern ffmpeg (decodes from the previous keyframe).
    # Near the end a seek can land past the last frame: step back a frame at a time.
    for k in range(4):
        tt = max(t - k / fps, 0)
        r = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", f"{tt:.4f}", "-i", video,
                            "-frames:v", "1", "-vf", f"scale={width}:-2:out_range=pc,format=yuvj420p", path],
                           capture_output=True, text=True)
        if r.returncode == 0 and os.path.exists(path) and os.path.getsize(path) > 0:
            return path
    raise RuntimeError(f"could not grab a frame near {t:.3f}s: {r.stderr.strip()[-300:]}")


def font(size):
    for f in ("/System/Library/Fonts/Menlo.ttc", "C:/Windows/Fonts/consola.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"):
        if os.path.exists(f):
            return ImageFont.truetype(f, size)
    return ImageFont.load_default()


def sheet(frames, cols, out, title=None):
    """frames: [(path, caption)]. Captions sit in a strip under each tile so they never cover the picture."""
    ims = [Image.open(p).convert("RGB") for p, _ in frames]
    w, h = ims[0].size
    f = font(max(14, w // 22))
    cap_h = f.size + 10
    rows = (len(ims) + cols - 1) // cols
    top = 36 if title else 0
    canvas = Image.new("RGB", (cols * (w + 4) + 4, rows * (h + cap_h + 4) + 4 + top), (255, 255, 255))
    d = ImageDraw.Draw(canvas)
    if title:
        d.text((8, 6), title, font=font(20), fill=(0, 0, 0))
    for i, (im, (_, cap)) in enumerate(zip(ims, frames)):
        x, y = 4 + (i % cols) * (w + 4), top + 4 + (i // cols) * (h + cap_h + 4)
        canvas.paste(im, (x, y))
        d.rectangle([x, y + h, x + w, y + h + cap_h], fill=(20, 20, 20))
        d.text((x + 6, y + h + 4), cap, font=f, fill=(255, 230, 0))
    canvas.save(out, quality=88)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video"); ap.add_argument("--out", required=True)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--every", type=float); g.add_argument("--count", type=int)
    g.add_argument("--at"); g.add_argument("--around"); g.add_argument("--cuts")
    ap.add_argument("--cols", type=int, default=4); ap.add_argument("--rows", type=int, default=4)
    ap.add_argument("--width", type=int, default=480, help="tile width in px")
    ap.add_argument("--start", type=float, default=0); ap.add_argument("--end", type=float)
    a = ap.parse_args()

    dur, fps = probe(a.video)
    end = min(a.end or dur, dur)
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="sheet_")
    groups = []  # list of (title, [(t, caption)])
    if a.every or a.count:
        ts = ([a.start + i * a.every for i in range(int((end - a.start) / a.every) + 1)] if a.every else
              [a.start + (end - a.start) * (i + 0.5) / a.count for i in range(a.count)])
        groups.append((None, [(min(t, end - 1 / fps), label(t)) for t in ts]))
    else:
        if a.cuts:
            centers = [c["t"] if isinstance(c, dict) else c for c in json.load(open(a.cuts))["cuts"]]
        else:
            centers = [parse_t(x) for x in (a.at or a.around).split(",") if x.strip()]
        if a.at:
            groups.append((None, [(t, label(t)) for t in centers]))
        else:  # strips of 5 frames around each timestamp, one strip per row
            a.cols = 5
            for t in centers:
                groups.append((None, [(t + k / fps, f"{label(t)} {k:+d}f") for k in (-2, -1, 0, 1, 2)]))
    per = a.cols * a.rows
    flat = [x for _, items in groups for x in items]
    outs = []
    for s in range(0, len(flat), per):
        chunk = flat[s:s + per]
        frames = [(grab(a.video, t, a.width, os.path.join(tmp, f"f{s + i:05d}.jpg"), fps), cap) for i, (t, cap) in enumerate(chunk)]
        outs.append(sheet(frames, a.cols, f"{a.out}_{s // per + 1:02d}.jpg",
                          title=f"{os.path.basename(a.video)}  {label(chunk[0][0])}–{label(chunk[-1][0])}"))
    print("\n".join(outs))


if __name__ == "__main__":
    main()
