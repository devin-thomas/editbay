#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
"""Measure a reference video so a style can be written from numbers, not impressions.

Runs the editbay measurement tools on one reference and writes a report the agent reads before describing the style:
cut rhythm (shots, flashes, density over time, the acceleration curve by thirds), tempo and how tightly cuts sit on
the grid (after removing the constant detector lag), palette with colour roles, loudness, long holds, and the sheets
to read (a dense overview plus a strip at every cut).

Usage:
  reference_report.py REF.mp4 --out reference/NAME/ [--threshold 0.25] [--every 0.25]
Writes MEASUREMENTS.md, measurements.json, cuts.json, beats.json, palette.json, overview_NN.jpg, strips_NN.jpg.
The report measures; it does not interpret. Reading the sheets and writing the breakdown is the agent's job.
"""
import argparse, json, os, re, subprocess, statistics, sys

HERE = os.path.dirname(os.path.abspath(__file__))


def run(tool, *args, uv=True):
    cmd = (["uv", "run", "-q", os.path.join(HERE, tool)] if uv else ["python3", os.path.join(HERE, tool)]) + [str(a) for a in args]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode not in (0, 1):
        print(r.stdout + r.stderr, file=sys.stderr)
    return r.stdout


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ref"); ap.add_argument("--out", required=True)
    ap.add_argument("--threshold", type=float, default=0.25); ap.add_argument("--every", type=float)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    o = lambda f: os.path.join(a.out, f)
    probe = json.loads(subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", a.ref],
                                      capture_output=True, text=True).stdout)
    dur = float(probe["format"]["duration"])
    v = next(s for s in probe["streams"] if s["codec_type"] == "video")
    n, d = v["r_frame_rate"].split("/"); fps = float(n) / float(d)

    run("scene_cuts.py", a.ref, "--threshold", a.threshold, "--json", o("cuts.json"), uv=False)
    cuts = json.load(open(o("cuts.json")))
    wav = o("audio.wav")
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", a.ref, "-vn", "-ac", "1", "-ar", "44100", wav], check=True)
    run("beat_grid.py", "detect", wav, "--json", o("beats.json"))
    beats = json.load(open(o("beats.json")))
    align_txt = run("beat_grid.py", "align", "--cuts", o("cuts.json"), "--beats", o("beats.json"), "--tolerance-ms",
                    round(2000 / fps, 1), "--half", "--auto-offset")
    run("palette.py", a.ref, "--every", 0.5, "--colors", 8, "--json", o("palette.json"), "--swatch", o("palette.png"))
    lufs = run("loudness.py", a.ref, uv=False).strip().replace(a.ref, os.path.basename(a.ref))
    frz = subprocess.run(["ffmpeg", "-nostdin", "-hide_banner", "-i", a.ref, "-an", "-vf", "freezedetect=n=0.003:d=0.4", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    starts = [float(x) for x in re.findall(r"freeze_start:\s*([\d.]+)", frz)]
    ends = [float(x) for x in re.findall(r"freeze_end:\s*([\d.]+)", frz)] + [dur]
    holds = [(round(s, 2), round(e, 2)) for s, e in zip(starts, ends)]
    every = a.every or (0.25 if dur <= 20 else 0.5 if dur <= 60 else 2.0)
    sheets = run("contact_sheet.py", a.ref, "--every", every, "--width", 480, "--out", o("overview")).split()
    strips = run("contact_sheet.py", a.ref, "--cuts", o("cuts.json"), "--rows", 6, "--width", 320, "--out", o("strips")).split() \
        if cuts["cuts"] else []

    # Acceleration curve: share of cuts in each third, and median shot length per third.
    thirds = [(0, dur / 3), (dur / 3, 2 * dur / 3), (2 * dur / 3, dur)]
    ct = [c["t"] for c in cuts["cuts"]]
    per_third = [sum(1 for t in ct if s <= t < e) for s, e in thirds]
    edges = [0.0] + ct + [dur]
    shots = [(edges[i], edges[i + 1]) for i in range(len(edges) - 1)]
    longest = sorted(shots, key=lambda x: x[1] - x[0], reverse=True)[:6]
    resid = [float(l.split("residual")[1].split("ms")[0]) for l in align_txt.splitlines() if "residual" in l]
    summary = {
        "file": os.path.basename(a.ref), "duration": round(dur, 3), "fps": round(fps, 3),
        "size": f"{v['width']}x{v['height']}", "shots": len(shots), "cuts": len(ct),
        "flashes": sum(1 for c in cuts["cuts"] if c.get("kind") == "flash"),
        "median_shot": round(statistics.median([e - s for s, e in shots]), 3),
        "cuts_by_third": per_third, "longest_shots": [[round(s, 2), round(e, 2)] for s, e in longest],
        "tempo_detected": beats["tempo"], "seconds_per_beat": round(60 / beats["tempo"], 4) if beats["tempo"] else None,
        "cut_to_grid_residual_ms": {"median_abs": round(statistics.median([abs(r) for r in resid]), 1) if resid else None,
                                    "within_2_frames": f"{sum(1 for r in resid if abs(r) <= 2000 / fps)}/{len(resid)}"},
        "loudness": lufs, "holds": holds, "palette": json.load(open(o("palette.json")))["palette"],
        "sheets": [os.path.basename(s) for s in sheets], "strips": [os.path.basename(s) for s in strips]}
    json.dump(summary, open(o("measurements.json"), "w"), indent=1)
    md = [f"# Measurements: {summary['file']}", "",
          f"- {summary['size']} at {summary['fps']} fps, {summary['duration']} s",
          f"- {summary['shots']} shots, {summary['cuts']} cut events ({summary['flashes']} flashes), median shot {summary['median_shot']} s",
          f"- cuts by third: {per_third} (acceleration when the last third dominates)",
          f"- longest shots (chapters or holds): {summary['longest_shots']}",
          f"- tempo (detected): {beats['tempo']} BPM; detectors can halve or double, and lag true onsets by ~35 ms",
          f"- cuts vs half-beat grid after removing the constant offset: median |residual| "
          f"{summary['cut_to_grid_residual_ms']['median_abs']} ms, {summary['cut_to_grid_residual_ms']['within_2_frames']} within 2 frames",
          f"- loudness: {lufs}",
          f"- holds (static picture >= 0.4 s): {holds or 'none'}",
          "- palette: " + ", ".join(f"{p['hex']} {p['share'] * 100:.0f}% {p['role']}" for p in summary["palette"]), "",
          "## Cut timeline", "", "```", align_txt.strip(), "```", "",
          "## Read next", "", "Overview sheets: " + ", ".join(summary["sheets"]), "", "Cut strips: " + ", ".join(summary["strips"]), "",
          "Read them in one batch, then write the breakdown (see the reference-to-style skill)."]
    open(o("MEASUREMENTS.md"), "w").write("\n".join(md) + "\n")
    os.remove(wav)
    print("\n".join(md[:12]))


if __name__ == "__main__":
    main()
