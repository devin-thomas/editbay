#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10,<3.14"
# dependencies = ["opencv-python-headless>=4.8,<5", "numpy"]  # 5.x dropped the bundled Haar cascades
# ///
"""Where is the face? Face boxes over time, a keep-clear zone for overlays, and a vertical (9:16) crop path.

Usage:
  faces.py VIDEO [--every 0.5] [--start S --end E] [--json faces.json] [--sheet faces.jpg]
Output JSON (all boxes are fractions of the frame, x0,y0,x1,y1):
  samples:     [{t, faces: [[x0,y0,x1,y1,score]]}]
  keep_clear:  union of the main face box over the whole range, padded 12% (overlays stay outside it)
  free_zones:  left / right / top / bottom strips that never touch keep_clear, for side cards and lower thirds
  crop_9x16:   [{t, x0}] smoothed left edge of a full-height 9:16 window centred on the face (for vertical cuts)
Detector: OpenCV's bundled frontal-face Haar cascade (no model download). It misses profiles and small faces;
look at --sheet before trusting a zone, and pass --pad to widen it.
"""
import argparse, json, os, subprocess, tempfile

import cv2
import numpy as np


def frames(video, every, start, end):
    tmp = tempfile.mkdtemp(prefix="faces_")
    cmd = ["ffmpeg", "-nostdin", "-v", "error", "-y"]
    if start:
        cmd += ["-ss", str(start)]
    if end:
        cmd += ["-to", str(end)]
    cmd += ["-i", video, "-vf", f"fps=1/{every},scale=960:-2", os.path.join(tmp, "f_%05d.jpg")]
    subprocess.run(cmd, check=True)
    for i, f in enumerate(sorted(os.listdir(tmp))):
        yield (start or 0) + i * every, cv2.imread(os.path.join(tmp, f))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video"); ap.add_argument("--every", type=float, default=0.5)
    ap.add_argument("--start", type=float); ap.add_argument("--end", type=float)
    ap.add_argument("--pad", type=float, default=0.12); ap.add_argument("--json"); ap.add_argument("--sheet")
    a = ap.parse_args()
    det = cv2.CascadeClassifier(os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml"))
    samples, main_boxes, last_img = [], [], None
    for t, img in frames(a.video, a.every, a.start, a.end):
        h, w = img.shape[:2]
        gray = cv2.equalizeHist(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY))
        found, _, weights = det.detectMultiScale3(gray, scaleFactor=1.1, minNeighbors=6, minSize=(w // 20, w // 20),
                                                  outputRejectLevels=True)
        faces = sorted(([x / w, y / h, (x + fw) / w, (y + fh) / h, float(s)] for (x, y, fw, fh), s in zip(found, weights)),
                       key=lambda b: -(b[2] - b[0]) * (b[3] - b[1]))
        samples.append({"t": round(t, 2), "faces": [[round(v, 4) for v in b] for b in faces]})
        if faces:
            main_boxes.append(faces[0][:4])
        last_img = img
    res = {"video": a.video, "every": a.every, "samples": samples, "detected_in": f"{len(main_boxes)}/{len(samples)}"}
    if main_boxes:
        b = np.array(main_boxes)
        # Median-filter outliers, then take the union of the rest.
        med = np.median(b, axis=0); dev = np.abs(b - med).sum(axis=1)
        keep = b[dev <= np.percentile(dev, 90)]
        x0, y0 = keep[:, 0].min(), keep[:, 1].min(); x1, y1 = keep[:, 2].max(), keep[:, 3].max()
        pw, ph = (x1 - x0) * a.pad, (y1 - y0) * a.pad
        kc = [float(max(0, x0 - pw)), float(max(0, y0 - ph)), float(min(1, x1 + pw)), float(min(1, y1 + ph))]
        res["keep_clear"] = [round(v, 4) for v in kc]
        res["free_zones"] = {"left": [0, 0, round(kc[0], 4), 1], "right": [round(kc[2], 4), 0, 1, 1],
                             "top": [0, 0, 1, round(kc[1], 4)], "bottom": [0, round(kc[3], 4), 1, 1]}
        # 9:16 window over a 16:9 frame is (9/16)^2 = 0.316 of the width; centre it on the face, smoothed.
        win = (9 / 16) * (9 / 16)
        centres, last = [], (med[0] + med[2]) / 2
        for s in samples:
            c = (s["faces"][0][0] + s["faces"][0][2]) / 2 if s["faces"] else last
            last = 0.8 * last + 0.2 * c; centres.append(last)
        res["crop_9x16"] = [{"t": s["t"], "x0": round(float(np.clip(c - win / 2, 0, 1 - win)), 4)}
                            for s, c in zip(samples, centres)]
    if a.sheet and last_img is not None and "keep_clear" in res:
        img = last_img.copy(); h, w = img.shape[:2]
        kc = res["keep_clear"]
        cv2.rectangle(img, (int(kc[0] * w), int(kc[1] * h)), (int(kc[2] * w), int(kc[3] * h)), (0, 0, 255), 3)
        for s in samples:
            for f in s["faces"][:1]:
                cv2.rectangle(img, (int(f[0] * w), int(f[1] * h)), (int(f[2] * w), int(f[3] * h)), (0, 255, 0), 1)
        cv2.putText(img, "red = keep clear, green = detections", (12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        cv2.imwrite(a.sheet, img)
    if a.json:
        json.dump(res, open(a.json, "w"), indent=1)
    print(f"faces detected in {res['detected_in']} samples; keep_clear {res.get('keep_clear')}")


if __name__ == "__main__":
    main()
