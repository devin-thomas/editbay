#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
"""Measure (and optionally normalise) loudness the way platforms do: EBU R128 integrated LUFS, LRA, true peak.

Usage:
  loudness.py FILE [FILE ...] [--target -14] [--tp -1.0]          measure; exit 1 if outside target ±1 LU or TP over
  loudness.py FILE --normalize OUT --target -16 --tp -1.5          two-pass loudnorm (linear when it fits)
Targets (house defaults): -14 LUFS for reels/shorts/music-led pieces, -16 LUFS for narrated explainers;
true peak <= -1 dBTP measured on the DELIVERED file (AAC transcodes add ~0.3 dB: leave headroom, re-measure).
"""
import argparse, json, os, re, subprocess, sys


def measure(path):
    err = subprocess.run(["ffmpeg", "-nostdin", "-hide_banner", "-i", path, "-vn", "-af", "ebur128=peak=true",
                          "-f", "null", "-"], capture_output=True, text=True).stderr
    summary = err[err.rfind("Summary:"):]
    get = lambda pat: float(re.search(pat, summary).group(1)) if re.search(pat, summary) else None
    return {"file": path, "integrated_lufs": get(r"I:\s+(-?[\d.]+) LUFS"), "lra": get(r"LRA:\s+(-?[\d.]+) LU"),
            "true_peak_dbtp": get(r"Peak:\s+(-?[\d.]+) dBFS")}


def normalize(src, dst, target, tp, lra=11):
    first = subprocess.run(["ffmpeg", "-nostdin", "-hide_banner", "-i", src, "-vn", "-af",
                            f"loudnorm=I={target}:TP={tp}:LRA={lra}:print_format=json", "-f", "null", "-"],
                           capture_output=True, text=True).stderr
    m = json.loads(first[first.rfind("{"):first.rfind("}") + 1])
    af = (f"loudnorm=I={target}:TP={tp}:LRA={lra}:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
          f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    # 48 kHz out: loudnorm upsamples internally to 192 kHz and would otherwise keep that rate.
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", src, "-af", af, "-ar", "48000", "-c:v", "copy", dst],
                   check=True)
    res = measure(dst)
    # Linear loudnorm is a gain change, so a dense mix can still peak over the ceiling. Trim the excess (and a 0.1 dB
    # margin) as plain gain: integrated loudness drops by the same small amount and stays inside the window.
    if res["true_peak_dbtp"] is not None and res["true_peak_dbtp"] > tp:
        trim = res["true_peak_dbtp"] - tp + 0.1
        tmp = dst + ".trim" + os.path.splitext(dst)[1]
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", dst, "-af", f"volume=-{trim:.2f}dB", "-c:v", "copy", tmp],
                       check=True)
        os.replace(tmp, dst)
        res = measure(dst)
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+"); ap.add_argument("--target", type=float); ap.add_argument("--tp", type=float, default=-1.0)
    ap.add_argument("--normalize", metavar="OUT"); ap.add_argument("--json")
    a = ap.parse_args()
    if a.normalize:
        if a.target is None:
            sys.exit("--normalize needs --target")
        res = [normalize(a.files[0], a.normalize, a.target, a.tp)]
    else:
        res = [measure(f) for f in a.files]
    bad = 0
    for r in res:
        verdict = ""
        if a.target is not None and r["integrated_lufs"] is not None:
            off = r["integrated_lufs"] - a.target
            tp_bad = r["true_peak_dbtp"] is not None and r["true_peak_dbtp"] > a.tp
            ok = abs(off) <= 1.0 and not tp_bad; bad += not ok
            verdict = f"  {'OK' if ok else 'FAIL'} (target {a.target} ±1 LU, TP <= {a.tp})"
        print(f"{r['file']}: {r['integrated_lufs']} LUFS, LRA {r['lra']} LU, TP {r['true_peak_dbtp']} dBTP{verdict}")
    if a.json:
        json.dump(res, open(a.json, "w"), indent=1)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
