#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
"""Detect hard cuts and measure cut rhythm (the numbers behind "pacing").

Usage:
  scene_cuts.py VIDEO [--threshold 0.3] [--start S --end E] [--json cuts.json]
Output JSON: {"video", "fps", "cuts": [{"t", "score", "kind": cut|flash, "frames"}], "shots": [...], "stats", "density"}
- stats: shot count, mean/median/min/max shot length, cuts per minute.
- density: cuts per 2 s window, to see acceleration (a flurry reads as a spike).
Threshold: 0.25-0.35 for edited video; lower (0.15) catches soft cuts but also fast motion. Always eyeball
the result with contact_sheet.py --cuts before trusting it; dissolves and whip pans are not hard cuts.
"""
import argparse, json, re, statistics, subprocess


def fps_of(video):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate",
                        "-of", "csv=p=0", video], capture_output=True, text=True).stdout.strip()
    n, d = r.split("/"); return float(n) / float(d)


def detect(video, threshold, start=None, end=None):
    cmd = ["ffmpeg", "-nostdin", "-hide_banner"]
    if start:
        cmd += ["-ss", str(start)]
    if end:
        cmd += ["-to", str(end)]
    cmd += ["-i", video, "-an", "-vf", f"select='gt(scene,{threshold})',metadata=print", "-f", "null", "-"]
    err = subprocess.run(cmd, capture_output=True, text=True).stderr
    cuts, t = [], None
    for line in err.splitlines():
        m = re.search(r"pts_time:([\d.]+)", line)
        if m:
            t = float(m.group(1)) + (start or 0)
        m = re.search(r"lavfi\.scene_score=([\d.]+)", line)
        if m and t is not None:
            cuts.append({"t": round(t, 3), "score": round(float(m.group(1)), 3)}); t = None
    return cuts


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video"); ap.add_argument("--threshold", type=float, default=0.3)
    ap.add_argument("--start", type=float); ap.add_argument("--end", type=float); ap.add_argument("--json")
    ap.add_argument("--merge-frames", type=int, default=2,
                    help="cuts within N frames collapse into one event (flashes/strobes fire on every frame)")
    a = ap.parse_args()
    fps = fps_of(a.video)
    raw = detect(a.video, a.threshold, a.start, a.end)
    cuts = []
    for c in raw:
        if cuts and c["t"] - cuts[-1]["last"] <= a.merge_frames / fps + 1e-6:
            cuts[-1]["last"] = c["t"]; cuts[-1]["frames"] += 1; cuts[-1]["kind"] = "flash"
            cuts[-1]["score"] = max(cuts[-1]["score"], c["score"])
        else:
            cuts.append(dict(c, last=c["t"], frames=1, kind="cut"))
    lo = a.start or 0.0
    hi = a.end or float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                        a.video], capture_output=True, text=True).stdout)
    edges = [lo] + [c["t"] for c in cuts] + [hi]
    shots = [round(b - a_, 3) for a_, b in zip(edges, edges[1:]) if b > a_]
    span = hi - lo
    stats = {"shots": len(shots), "cuts_per_min": round(len(cuts) / span * 60, 1) if span else 0,
             "mean_shot": round(statistics.mean(shots), 3) if shots else 0,
             "median_shot": round(statistics.median(shots), 3) if shots else 0,
             "min_shot": min(shots) if shots else 0, "max_shot": max(shots) if shots else 0,
             "min_shot_frames": round(min(shots) * fps) if shots else 0}
    density = []
    w = 2.0; t = lo
    while t < hi:
        density.append({"t": round(t, 2), "cuts": sum(1 for c in cuts if t <= c["t"] < t + w)}); t += w
    out = {"video": a.video, "fps": round(fps, 3), "threshold": a.threshold, "range": [lo, round(hi, 3)],
           "cuts": cuts, "shots": shots, "stats": stats, "density": density}
    if a.json:
        json.dump(out, open(a.json, "w"), indent=1)
    print(json.dumps(stats))
    print("cuts:", " ".join(f"{c['t']:.2f}" + ("*" if c["kind"] == "flash" else "") for c in cuts), "(* = flash)")
    print("density/2s:", " ".join(str(d["cuts"]) for d in density))


if __name__ == "__main__":
    main()
