#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy", "pillow>=10"]
# ///
"""Recover a logo's or character's straight-alpha RGBA from renders of the same art on flat backgrounds.

Modes:
  difference  (two or more renders, `--on` each) every render is C_i = a*F + (1-a)*B_i with the same F and a, so
              C_i - C_j = (1-a)(B_i - B_j). (1-a) is the least-squares fit over every pair and channel; F is the
              average of the de-premultiplied renders, (C_i - (1-a)B_i) / a. Exact up to the inputs' own noise.
  key         (one render, `--key IMG --color '#4dffff'`) a fallback. `--alpha hue` (default for a coloured key):
              alpha falls with the pixel's lean toward the key's hue, 1 - <C,k>/<K,k> with k = K - mean(K), which
              is the classic green keyer G - (R+B)/2 generalised to any colour; de-premultiplying against the key
              leaves no key hue in the edge, so it despills by construction. `--alpha distance` (automatic for a
              grey key, which has no hue): alpha ramps with the RGB distance from the key (0 below --soft, 1 above
              --hard), and edge pixels lose any lean toward the key's hue (despill). One background cannot tell a
              pale edge from a half-transparent one, and art that shares the key's hue (or, on a grey key, its
              lightness) turns transparent; render on two backgrounds whenever you can.

Usage:
  logo_matte.py OUT.png --on BG_A.png --on BG_B.png [--on BG_C.png] [--bg '#hex' ...] [--json report.json]
  logo_matte.py OUT.png --key IMG.png [--color '#4dffff'] [--alpha hue|distance] [--soft 0.04 --hard 0.25]
Each background colour is the median of the four corner patches (--corner, a fraction of the short side); pass
`--bg '#hex'` once per `--on`, in order (or `--color` for --key), when the art reaches the corners. Inputs must be
the same size and aligned: the same art and framing, e.g. an app's avatar exported on several brand colours, or one
Blender or browser frame rendered over two or more flat backgrounds.

Prints each background, the recomposite error per background and channel (mean and p99 in 0-255: the written RGBA
laid back over each input's background, against that input) and the alpha coverage. In difference mode that error is
the check: misaligned inputs, a background that is not flat, or art that changed between renders give a large p99.
In key mode it only shows clipping and a --color that misses the real background; it cannot detect a wrong alpha.

Exit 1 (nothing written) when fewer than two `--on` are given, sizes differ, two backgrounds are closer than
--min-bg-diff ("backgrounds must differ": the same render twice cannot separate art from background), the
difference-mode recomposite p99 of any channel exceeds --max-p99, or the alpha comes out empty.

Measured on the Demo Artist avatar (demo-artist-{aqua,white,lavender}.webp, 2000 px lossy WebP, 2026-09-29):
- Difference, three backgrounds: recomposite mean 0.07-0.08/255 per channel, p99 2.0/255 (the prototype's
  max-over-channels figure: mean 0.11, p99 ~3). Each pair alone: mean <= 0.09, p99 <= 2.0; alpha is identical
  to the prototype's. One render shifted 3 px gives p99 27, so --max-p99 12 fails misalignment and passes lossy art.
- Key, against the three-background result, composited over a dark plate (#140e28) and scored on the art's pixels:
  aqua key, hue alpha: mean 0.51/255, p99 7.5, alpha error 0.001, no holes. Distance alpha (0.04/0.25) on the same
  render: mean 1.00, p99 19.5, a visible aqua rim that despill can only turn grey, because the rim pixels reach
  alpha 1; wider ramps were worse (hard 0.5: p99 52). Lavender (a weak hue): hue p99 36, distance p99 48.
  White key (distance): alpha error 0.021 and 1.8% of opaque pixels keyed out, the art's own whites.
"""
import argparse, json, sys

import numpy as np
from PIL import Image

HUE_MIN = 0.04  # key chroma |K - mean(K)| below this (about 10/255) has no usable hue: use distance


def load(path):
    im = Image.open(path)
    if im.mode in ("RGBA", "LA", "PA") and np.asarray(im.getchannel("A")).min() < 255:
        sys.exit(f"{path}: has transparency already; flatten it onto its background first")
    return np.asarray(im.convert("RGB")).astype(np.float64) / 255


def hex_rgb(s):
    s = s.strip().lstrip("#")
    if len(s) != 6:
        sys.exit(f"colour {s!r}: expected #rrggbb")
    return np.array([int(s[i:i + 2], 16) for i in (0, 2, 4)], dtype=np.float64) / 255


def corner_bg(img, frac):
    h, w = img.shape[:2]; k = max(4, int(min(h, w) * frac))
    px = np.concatenate([img[:k, :k], img[:k, -k:], img[-k:, :k], img[-k:, -k:]]).reshape(-1, 3)
    med = np.median(px, 0)
    return med, float(np.abs(px - med).max(-1).mean() * 255)


def to255(c):
    return "#" + "".join(f"{int(round(v * 255)):02x}" for v in c)


def recomposite(rgba8, imgs, bgs):
    f = rgba8[..., :3].astype(np.float64) / 255; a = rgba8[..., 3:].astype(np.float64) / 255
    rows = []
    for img, bg in zip(imgs, bgs):
        err = np.abs(f * a + (1 - a) * bg - img) * 255
        rows.append({"bg": to255(bg),
                     "mean": [round(float(err[..., c].mean()), 3) for c in range(3)],
                     "p99": [round(float(np.percentile(err[..., c], 99)), 2) for c in range(3)]})
    return rows


def unpremultiply(img, k, a):
    f = np.where(a[..., None] > 1e-3, k + (img - k) / np.maximum(a[..., None], 1e-3), 0)
    return np.clip(f, 0, 1)


def difference(imgs, bgs):
    num = np.zeros(imgs[0].shape[:2]); den = 0.0
    for i in range(len(imgs)):
        for j in range(i + 1, len(imgs)):
            db = bgs[i] - bgs[j]
            num += ((imgs[i] - imgs[j]) * db).sum(-1); den += float((db * db).sum())
    t = np.clip(num / den, 0, 1)                       # t = 1 - alpha, least squares over pairs and channels
    a = 1 - t
    f = sum(img - t[..., None] * bg for img, bg in zip(imgs, bgs)) / len(imgs)
    f = np.where(a[..., None] > 1e-3, f / np.maximum(a[..., None], 1e-3), 0)
    return np.clip(f, 0, 1), a


def key(img, k, method, soft, hard):
    kc = k - k.mean()
    kh = kc / max(np.linalg.norm(kc), 1e-9)            # sums to zero: <C, kh> is C's lean toward the key's hue
    if method == "hue":
        a = 1 - np.clip((img * kh).sum(-1) / float((k * kh).sum()), 0, 1)
        return unpremultiply(img, k, a), a
    d = np.linalg.norm(img - k, axis=-1) / np.sqrt(3)  # 0 on the key, 1 at the far corner of the RGB cube
    a = np.clip((d - soft) / max(hard - soft, 1e-6), 0, 1)
    f = unpremultiply(img, k, a)
    if np.linalg.norm(kc) >= 1e-3:                     # despill the edge band; a grey key has no hue to spill
        lean = np.maximum((f * kh).sum(-1), 0)
        band = (a > 0) & (a < 1)
        f = np.where(band[..., None], np.clip(f - lean[..., None] * kh, 0, 1), f)
    return f, a


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("out")
    ap.add_argument("--on", action="append", default=[], help="a render on a flat background (repeat, 2+)")
    ap.add_argument("--bg", action="append", default=[], help="background colour for each --on, in order")
    ap.add_argument("--key", help="single render on a flat key colour (fallback)")
    ap.add_argument("--color", help="key colour, #rrggbb (default: corner median)")
    ap.add_argument("--alpha", choices=("hue", "distance"), help="key alpha (default: hue, distance for a grey key)")
    ap.add_argument("--soft", type=float, default=0.04, help="distance key: alpha 0 below this distance")
    ap.add_argument("--hard", type=float, default=0.25, help="distance key: alpha 1 above this distance")
    ap.add_argument("--corner", type=float, default=0.02, help="corner patch size, fraction of the short side")
    ap.add_argument("--snap", type=float, default=0.02, help="alpha below snap -> 0, above 1-snap -> 1")
    ap.add_argument("--min-bg-diff", type=float, default=8.0, help="smallest background difference, 0-255")
    ap.add_argument("--max-p99", type=float, default=12.0, help="difference mode: fail above this p99, 0-255")
    ap.add_argument("--json", help="write the measurements here")
    a = ap.parse_args()

    if a.key and a.on:
        sys.exit("use --on (two or more backgrounds) or --key (one), not both")
    if a.key:
        imgs = [load(a.key)]
        corner, _ = corner_bg(imgs[0], a.corner)
        bgs = [hex_rgb(a.color) if a.color else corner]
        mode = "key"
        method = a.alpha or ("hue" if np.linalg.norm(bgs[0] - bgs[0].mean()) >= HUE_MIN else "distance")
        if a.color and np.abs(corner - bgs[0]).max() * 255 > 1.5:
            print(f"note: the corners read {to255(corner)}, not {a.color}")
    else:
        if len(a.on) < 2:
            sys.exit("difference matting needs two or more --on renders (or use --key IMG --color '#hex')")
        imgs = [load(p) for p in a.on]
        if len({im.shape for im in imgs}) > 1:
            sys.exit("inputs differ in size: " + ", ".join(f"{p} {im.shape[1]}x{im.shape[0]}" for p, im in zip(a.on, imgs)))
        if a.bg and len(a.bg) != len(a.on):
            sys.exit("--bg must be given once per --on, in order")
        bgs = [hex_rgb(c) for c in a.bg] if a.bg else [corner_bg(im, a.corner)[0] for im in imgs]
        mode, method = "difference", "least-squares"
    srcs = [a.key] if mode == "key" else a.on
    for src, im, bg in zip(srcs, imgs, bgs):
        spread = corner_bg(im, a.corner)[1]
        print(f"background {to255(bg)}  corner spread {spread:.2f}/255  {src}")
        if spread > 6:
            print(f"  warning: the corners of {src} are not flat ({spread:.1f}/255); pass the colour if the art reaches them")
    if mode == "difference":
        for i in range(len(imgs)):
            for j in range(i + 1, len(imgs)):
                d = float(np.abs(bgs[i] - bgs[j]).max() * 255)
                if d < a.min_bg_diff:
                    sys.exit(f"backgrounds must differ: {a.on[i]} and {a.on[j]} are both {to255(bgs[i])} "
                             f"(max channel difference {d:.1f}/255 < --min-bg-diff {a.min_bg_diff})")
        f, alpha = difference(imgs, bgs)
    else:
        print(f"key alpha: {method}")
        f, alpha = key(imgs[0], bgs[0], method, a.soft, a.hard)

    alpha = np.where(alpha < a.snap, 0, np.where(alpha > 1 - a.snap, 1, alpha))
    f = np.where(alpha[..., None] > 0, f, 0)
    rgba8 = (np.dstack([f, alpha]) * 255 + 0.5).astype(np.uint8)
    rows = recomposite(rgba8, imgs, bgs)
    al = rgba8[..., 3]
    cover = {"opaque": round(float((al == 255).mean()), 4), "partial": round(float(((al > 0) & (al < 255)).mean()), 4),
             "clear": round(float((al == 0).mean()), 4), "over_half": round(float((al > 127).mean()), 4)}
    for r in rows:
        print(f"recomposite on {r['bg']}  mean R/G/B {r['mean'][0]:.2f} {r['mean'][1]:.2f} {r['mean'][2]:.2f}"
              f"  p99 {r['p99'][0]:.1f} {r['p99'][1]:.1f} {r['p99'][2]:.1f}  (0-255)")
    print(f"alpha coverage: opaque {cover['opaque']:.1%}  partial {cover['partial']:.1%}  clear {cover['clear']:.1%}"
          f"  (>50%: {cover['over_half']:.1%})")
    worst = max(max(r["p99"]) for r in rows)
    if a.json:
        with open(a.json, "w") as fh:
            json.dump({"mode": mode, "alpha": method, "inputs": srcs, "recomposite": rows, "coverage": cover,
                       "worst_p99": worst, "out": a.out}, fh, indent=1)
    if mode == "difference" and worst > a.max_p99:
        sys.exit(f"recomposite p99 {worst:.1f}/255 exceeds --max-p99 {a.max_p99}: the renders are misaligned, a "
                 "background is not flat, or the art changed between them; nothing written")
    if not al.any():
        sys.exit("alpha is empty: nothing separates from the background; nothing written")
    Image.fromarray(rgba8, "RGBA").save(a.out)
    print(f"wrote {a.out}  {rgba8.shape[1]}x{rgba8.shape[0]} straight alpha")


if __name__ == "__main__":
    main()
