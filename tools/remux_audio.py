#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
"""Put the mastered mix back into a render: the video stream is copied untouched, the audio is the mix, re-encoded once.

Why: HyperFrames 0.8.79 changes the level of the audio it renders, and not by a fixed rule (measured 2026-09-26: a
-14.3 LUFS mix came out at -16.1, a constant -1.79 dB with zero lag; one -16.0 mix stayed at -16.1, another came out
at -17.4 with its true peak barely moving). Master the mix with mix.py, then run this after every render, whatever
the target.

Usage:
  remux_audio.py RENDER.mp4 MIX.wav --out FINAL.mp4 [--target -14 --tp -1.0] [--bitrate 320k]
After encoding it measures the result; AAC can push true peak up by a few tenths of a dB, so if the delivered file is
over --tp it trims the excess (plus 0.1 dB) and encodes again. Exit 1 if the delivered file still misses the target.
"""
import argparse, json, os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))


def measure(path):
    out = os.path.join(tempfile.mkdtemp(), "m.json")
    subprocess.run(["python3", os.path.join(HERE, "loudness.py"), path, "--json", out], capture_output=True, text=True)
    return json.load(open(out))[0]


def encode(render, mix, out, bitrate, limit_db=None):
    af = ["-af", f"alimiter=limit={10 ** (limit_db / 20):.4f}:attack=1:release=30:level=disabled"] if limit_db is not None else []
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", render, "-i", mix, "-map", "0:v:0", "-map", "1:a:0",
                    "-c:v", "copy", *af, "-c:a", "aac", "-b:a", bitrate, "-ar", "48000", "-shortest", "-movflags", "+faststart", out],
                   check=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("render"); ap.add_argument("mix"); ap.add_argument("--out", required=True)
    ap.add_argument("--target", type=float); ap.add_argument("--tp", type=float, default=-1.0)
    ap.add_argument("--bitrate", default="320k")
    a = ap.parse_args()
    encode(a.render, a.mix, a.out, a.bitrate)
    m, limit = measure(a.out), None
    for _ in range(3):
        if m["true_peak_dbtp"] is None or m["true_peak_dbtp"] <= a.tp:
            break
        # AAC overshoots sharp transients (hot, near-square drum hits) far more than their level, and a whole-mix gain
        # trim can make it worse: a vlog mix at -2.1 dBTP encoded at 160k to -0.9 dBTP, then to +1.5 dBTP after a
        # 0.2 dB trim, and the old trim loop took the copy to -17.3 LUFS. Limit the transients instead (a limit 3 dB
        # under the ceiling gave -1.1 dBTP at -15.0 LUFS), 1 dB lower on each further pass.
        limit = a.tp - 3.0 if limit is None else limit - 1.0
        encode(a.render, a.mix, a.out, a.bitrate, limit)
        m = measure(a.out)
    if limit is not None:
        print(f"limited transients at {limit:.1f} dBFS for the AAC true peak")
    dur = lambda p, s: float(subprocess.run(["ffprobe", "-v", "error", "-select_streams", s, "-show_entries", "stream=duration",
                                             "-of", "csv=p=0", p], capture_output=True, text=True).stdout or 0)
    v, au = dur(a.out, "v:0"), dur(a.out, "a:0")
    ok = (a.target is None or abs(m["integrated_lufs"] - a.target) <= 1.0) and m["true_peak_dbtp"] <= a.tp and abs(v - au) <= 0.05
    print(f"{a.out}: {m['integrated_lufs']} LUFS, TP {m['true_peak_dbtp']} dBTP; video {v:.3f}s audio {au:.3f}s  {'OK' if ok else 'FAIL'}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
