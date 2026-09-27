#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10,<3.14"
# dependencies = ["opencv-python-headless>=4.8,<5", "numpy"]  # 5.x dropped the bundled Haar cascades
# ///
"""Prove the overlays never cover the speaker's face.

Modes:
  diff    (base footage plays unchanged under the overlays) compare the keep-clear box between the source and the
          render at each sample; a large difference inside the box means something was drawn over the face.
  detect  (the base is zoomed, punched-in, or reframed) run face detection on the render; a sample where the source
          shows a face but the render shows none means the face was covered or pushed out of frame.

Usage:
  face_clear.py --source SRC.mp4 --render OUT.mp4 --faces faces.json [--mode diff|detect] [--every 0.5]
                [--offset 0.0] [--skip 10.0-12.5,...] [--json face_clear.json]
--offset: render time = source time + offset (a render with a 1 s intro card uses --offset 1.0).
--skip: render-time ranges where covering the face is intentional (a full-screen takeover).
Exit 1 when any sample outside --skip fails.
"""
import argparse, json, os, subprocess, sys, tempfile

import cv2
import numpy as np


def frame(path, t, w=640):
    tmp = os.path.join(tempfile.mkdtemp(), "f.png")
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", path, "-frames:v", "1",
                    "-vf", f"scale={w}:-2", tmp], check=True)
    return cv2.imread(tmp)


def duration(path):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                                capture_output=True, text=True).stdout)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", required=True); ap.add_argument("--render", required=True)
    ap.add_argument("--faces", required=True); ap.add_argument("--mode", choices=["diff", "detect"], default="diff")
    ap.add_argument("--every", type=float, default=0.5); ap.add_argument("--offset", type=float, default=0.0)
    ap.add_argument("--skip", default=""); ap.add_argument("--threshold", type=float, default=14.0,
                    help="mean absolute difference (0-255) inside the box that counts as covered (diff mode)")
    ap.add_argument("--json")
    a = ap.parse_args()
    faces = json.load(open(a.faces))
    box = faces.get("keep_clear")
    if not box:
        sys.exit("faces.json has no keep_clear box (no face found in the source?)")
    skips = [tuple(float(x) for x in r.split("-")) for r in a.skip.split(",") if r.strip()]
    det = cv2.CascadeClassifier(os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml"))
    end = min(duration(a.source), duration(a.render) - a.offset)
    rows, fails, t = [], 0, 0.0
    while t < end - 0.05:
        rt = t + a.offset
        if any(s <= rt <= e for s, e in skips):
            t += a.every; continue
        src, ren = frame(a.source, t), frame(a.render, rt)
        h, w = src.shape[:2]
        if a.mode == "diff":
            ren = cv2.resize(ren, (w, h))
            x0, y0, x1, y1 = int(box[0] * w), int(box[1] * h), int(box[2] * w), int(box[3] * h)
            d = float(np.abs(src[y0:y1, x0:x1].astype(int) - ren[y0:y1, x0:x1].astype(int)).mean())
            ok = d <= a.threshold
            rows.append({"t_render": round(rt, 2), "diff": round(d, 1), "ok": ok})
        else:
            g = lambda im: cv2.equalizeHist(cv2.cvtColor(im, cv2.COLOR_BGR2GRAY))
            has = lambda im: len(det.detectMultiScale(g(im), 1.1, 6, minSize=(im.shape[1] // 20,) * 2)) > 0
            ok = (not has(src)) or has(ren)
            rows.append({"t_render": round(rt, 2), "source_face": has(src), "render_face": has(ren), "ok": ok})
        fails += not rows[-1]["ok"]
        t += a.every
    bad = [r for r in rows if not r["ok"]]
    for r in bad:
        print(f"COVERED near {r['t_render']:.2f}s " + (f"(diff {r['diff']})" if "diff" in r else "(face lost in render)"))
    print(f"{len(rows) - fails}/{len(rows)} samples keep the face clear ({a.mode} mode, keep_clear {box})")
    if a.json:
        json.dump({"mode": a.mode, "keep_clear": box, "samples": rows, "covered": bad}, open(a.json, "w"), indent=1)
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
