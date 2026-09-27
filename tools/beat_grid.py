#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10,<3.14"
# dependencies = ["librosa>=0.10", "numpy", "soundfile"]
# ///
"""Beat grids: detect them in music, generate them for a planned tempo, and check that cuts land on them.

Subcommands:
  detect AUDIO [--json beats.json]
      Tempo, beat times, a downbeat guess, per-beat energy (RMS), and onset peaks. Works on a video's audio too.
  grid --bpm 128 --duration 15 [--offset 0.0] [--fps 60] [--json grid.json]
      A planned grid: beat and half-beat times, bar numbers, and each beat's frame index at the given fps.
  align --cuts cuts.json --beats beats.json [--tolerance-ms 17] [--half] [--auto-offset]
      For each cut, the distance to the nearest beat (or half-beat with --half). Exit code 1 if any cut misses.
      17 ms is one frame at 60 fps; use 34 ms for 30 fps delivery. Use --auto-offset when measuring someone
      else's delivered file: detected beats lag the true transients by a constant, so judge the residuals.

Detected tempo can be off by x2 or x0.5 (octave errors): sanity-check against the energy curve and by ear.
"""
import argparse, json, sys

import numpy as np


def detect(path, out):
    import librosa
    y, sr = librosa.load(path, sr=22050, mono=True)
    tempo, frames = librosa.beat.beat_track(y=y, sr=sr, units="frames")
    beats = librosa.frames_to_time(frames, sr=sr)
    rms = librosa.feature.rms(y=y)[0]
    rms_t = librosa.times_like(rms, sr=sr)
    energy = [float(np.mean(rms[(rms_t >= b) & (rms_t < (beats[i + 1] if i + 1 < len(beats) else b + 0.5))]) or 0)
              for i, b in enumerate(beats)]
    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    onsets = librosa.onset.onset_detect(onset_envelope=onset_env, sr=sr, units="time")
    # Downbeat guess: the beat phase (0-3) whose beats carry the most onset strength.
    strength = onset_env[np.minimum(frames, len(onset_env) - 1)]
    phase = int(np.argmax([strength[p::4].mean() if len(strength[p::4]) else 0 for p in range(4)]))
    peak = max(energy) or 1.0
    res = {"audio": path, "duration": round(len(y) / sr, 3), "tempo": round(float(np.atleast_1d(tempo)[0]), 2),
           "beats": [round(float(b), 3) for b in beats], "downbeat_phase": phase,
           "downbeats": [round(float(b), 3) for b in beats[phase::4]],
           "energy": [round(e / peak, 3) for e in energy], "onsets": [round(float(o), 3) for o in onsets]}
    if out:
        json.dump(res, open(out, "w"), indent=1)
    print(f"tempo {res['tempo']} BPM, {len(beats)} beats, first beat {res['beats'][0] if len(beats) else None}s, "
          f"downbeat phase {phase}, {len(onsets)} onsets")
    return res


def grid(bpm, duration, offset, fps, out):
    spb = 60.0 / bpm
    beats, t, i = [], offset, 0
    while t <= duration + 1e-9:
        beats.append({"i": i, "t": round(t, 4), "bar": i // 4 + 1, "beat": i % 4 + 1, "frame": round(t * fps)})
        t += spb; i += 1
    res = {"bpm": bpm, "seconds_per_beat": round(spb, 4), "fps": fps, "frames_per_beat": round(spb * fps, 3),
           "duration": duration, "beats": beats, "half_beats": [round(offset + (k + 0.5) * spb, 4) for k in range(len(beats))]}
    if out:
        json.dump(res, open(out, "w"), indent=1)
    print(f"{bpm} BPM = {spb * 1000:.1f} ms/beat = {spb * fps:.2f} frames/beat at {fps} fps; "
          f"{len(beats)} beats ({len(beats) / 4:.1f} bars) in {duration}s")
    return res


def align(cuts_path, beats_path, tol_ms, half, auto_offset=False):
    cuts = [c["t"] if isinstance(c, dict) else c for c in json.load(open(cuts_path))["cuts"]]
    b = json.load(open(beats_path))
    beats = [x["t"] if isinstance(x, dict) else x for x in b["beats"]]
    if half:
        beats = sorted(beats + [(p + q) / 2 for p, q in zip(beats, beats[1:])])
    beats = np.array(beats)
    deltas = [(c - beats[int(np.argmin(np.abs(beats - c)))]) * 1000 for c in cuts]
    # Measured beats of a delivered file carry a constant lag (onset-detector latency, AAC priming, A/V offset).
    # For a reference, what matters is whether cuts sit on the grid consistently: remove the median offset.
    offset = float(np.median(deltas)) if auto_offset and deltas else 0.0
    if auto_offset:
        print(f"global offset removed: {offset:+.1f} ms (median cut-to-beat delta)")
    misses = 0
    for c, d in zip(cuts, deltas):
        r = d - offset; ok = abs(r) <= tol_ms; misses += not ok
        print(f"cut {c:8.3f}s  {'half-' if half else ''}beat delta {d:+7.1f} ms  residual {r:+7.1f} ms  {'ok' if ok else 'MISS'}")
    print(f"{len(cuts) - misses}/{len(cuts)} cuts within ±{tol_ms} ms" + (" after offset" if auto_offset else ""))
    return misses


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("detect"); d.add_argument("audio"); d.add_argument("--json")
    g = sub.add_parser("grid"); g.add_argument("--bpm", type=float, required=True)
    g.add_argument("--duration", type=float, required=True); g.add_argument("--offset", type=float, default=0.0)
    g.add_argument("--fps", type=float, default=60); g.add_argument("--json")
    al = sub.add_parser("align"); al.add_argument("--cuts", required=True); al.add_argument("--beats", required=True)
    al.add_argument("--tolerance-ms", type=float, default=17); al.add_argument("--half", action="store_true")
    al.add_argument("--auto-offset", action="store_true", help="remove the median cut-to-beat offset (for references)")
    a = ap.parse_args()
    if a.cmd == "detect":
        detect(a.audio, a.json)
    elif a.cmd == "grid":
        grid(a.bpm, a.duration, a.offset, a.fps, a.json)
    else:
        sys.exit(1 if align(a.cuts, a.beats, a.tolerance_ms, a.half, a.auto_offset) else 0)


if __name__ == "__main__":
    main()
