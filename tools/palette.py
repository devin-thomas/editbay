#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pillow>=10", "numpy"]
# ///
"""Extract a video's (or an image's) working palette: dominant colours with their share of the frame.

Usage:
  palette.py VIDEO_OR_IMAGE [--colors 8] [--every 1.0] [--start S --end E] [--json palette.json] [--swatch palette.png]
Samples frames, runs k-means in Lab-ish space (numpy only), and reports hex colours sorted by coverage, plus
which are near-black / near-white / accent (high chroma, low coverage): accents are what brands are made of.
"""
import argparse, json, os, subprocess, tempfile

import numpy as np
from PIL import Image, ImageDraw


def pixels(path, every, start, end):
    ext = os.path.splitext(path)[1].lower()
    if ext in (".png", ".jpg", ".jpeg", ".webp"):
        ims = [Image.open(path).convert("RGB")]
    else:
        tmp = tempfile.mkdtemp(prefix="pal_")
        cmd = ["ffmpeg", "-nostdin", "-v", "error", "-y"] + (["-ss", str(start)] if start else []) + \
              (["-to", str(end)] if end else []) + ["-i", path, "-vf", f"fps=1/{every},scale=160:-2", f"{tmp}/f_%05d.png"]
        subprocess.run(cmd, check=True)
        ims = [Image.open(os.path.join(tmp, f)).convert("RGB") for f in sorted(os.listdir(tmp))]
    return np.concatenate([np.asarray(im.resize((160, max(1, 160 * im.height // im.width)))).reshape(-1, 3) for im in ims])


def kmeans(x, k, iters=25, seed=0):
    rng = np.random.default_rng(seed)
    c = x[rng.choice(len(x), k, replace=False)].astype(float)
    for _ in range(iters):
        lab = np.argmin(((x[:, None, :] - c[None]) ** 2).sum(-1), axis=1)
        new = np.array([x[lab == i].mean(0) if np.any(lab == i) else c[i] for i in range(k)])
        if np.allclose(new, c, atol=0.5):
            break
        c = new
    return c, np.bincount(lab, minlength=k) / len(x)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src"); ap.add_argument("--colors", type=int, default=8); ap.add_argument("--every", type=float, default=1.0)
    ap.add_argument("--start", type=float); ap.add_argument("--end", type=float)
    ap.add_argument("--json"); ap.add_argument("--swatch")
    a = ap.parse_args()
    px = pixels(a.src, a.every, a.start, a.end)
    if len(px) > 200000:
        px = px[np.random.default_rng(1).choice(len(px), 200000, replace=False)]
    centres, share = kmeans(px.astype(float), a.colors)
    order = np.argsort(-share)
    out = []
    for i in order:
        r, g, b = (int(v) for v in centres[i])
        mx, mn = max(r, g, b), min(r, g, b); chroma = (mx - mn) / 255
        role = "near-black" if mx < 40 else "near-white" if mn > 215 else ("accent" if chroma > 0.35 and share[i] < 0.15 else
               "neutral" if chroma < 0.12 else "colour")
        out.append({"hex": f"#{r:02x}{g:02x}{b:02x}", "share": round(float(share[i]), 3), "role": role})
    for c in out:
        print(f"{c['hex']}  {c['share'] * 100:5.1f}%  {c['role']}")
    if a.json:
        json.dump({"source": a.src, "palette": out}, open(a.json, "w"), indent=1)
    if a.swatch:
        im = Image.new("RGB", (100 * len(out), 120), "white"); d = ImageDraw.Draw(im)
        for i, c in enumerate(out):
            d.rectangle([i * 100, 0, i * 100 + 99, 90], fill=c["hex"]); d.text((i * 100 + 6, 96), c["hex"], fill="black")
        im.save(a.swatch)


if __name__ == "__main__":
    main()
