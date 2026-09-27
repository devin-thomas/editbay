#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy", "soundfile", "scipy"]
# ///
"""Generate an original music bed at an exact tempo, with the beat grid it was built on.

Because the grid is known, cuts can land on beats with zero detection error. Deterministic (same seed, same file).

Usage:
  beat_bed.py --bpm 124 --sections intro:2,build:4,drop:4,outro:2 --out sound/bed [--style pulse|lofi|drive]
              [--key A --scale minor] [--seed 3] [--fps 60] [--end-hit]
  sections: name:bars pairs. Names that shape the arrangement: intro (pad + hat), build (adds kick, rising filter),
  groove (kit + bass, no arp: under a voice), drop (full kit + bass + arp), break (pad only), outro (kit falls away),
  hold (sustained chord for a lockup). --gaps 24 silences the half beat before beat 24 (a pre-drop gap).
Writes OUT.wav (48 kHz stereo, around -18 LUFS, leave loudness to the mix), OUT.stems/{drums,bass,pad,arp}.wav,
and OUT.grid.json ({bpm, seconds_per_beat, fps, duration, beats:[{i,t,bar,beat,frame,section}], sections, downbeats}).
It is a bed, not a song: steady, unobtrusive under a voice, punctuated where the sections change.
"""
import argparse, json, os

import numpy as np
import soundfile as sf
from scipy import signal

SR = 48000
NOTES = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5, "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}
SCALES = {"minor": [0, 2, 3, 5, 7, 8, 10], "major": [0, 2, 4, 5, 7, 9, 11], "dorian": [0, 2, 3, 5, 7, 9, 10]}
PROG = {"minor": [0, 5, 3, 6], "major": [0, 4, 5, 3], "dorian": [0, 3, 0, 6]}  # scale degrees, one chord per bar


def hz(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


def adsr(n, a=0.005, d=0.1, s=0.6, r=0.1):
    a, d, r = int(a * SR), int(d * SR), int(r * SR)
    e = np.full(n, s)
    e[:a] = np.linspace(0, 1, max(a, 1))[:len(e[:a])]
    e[a:a + d] = np.linspace(1, s, max(d, 1))[:len(e[a:a + d])]
    if r and n > r:
        e[-r:] *= np.linspace(1, 0, r)
    return e


def kick(n):
    t = np.arange(n) / SR
    f = 42 + 120 * np.exp(-t * 35)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 7)


def snare(n, rng):
    t = np.arange(n) / SR
    noise = signal.sosfilt(signal.butter(2, [900, 7000], "band", fs=SR, output="sos"), rng.standard_normal(n))
    return (noise * np.exp(-t * 18) + 0.4 * np.sin(2 * np.pi * 190 * t) * np.exp(-t * 25))


def hat(n, rng, open_=False):
    t = np.arange(n) / SR
    noise = signal.sosfilt(signal.butter(4, 7000, "high", fs=SR, output="sos"), rng.standard_normal(n))
    return noise * np.exp(-t * (12 if open_ else 60))


def saw(freq, n, detune=0.0):
    t = np.arange(n) / SR
    ph = (freq * (1 + detune)) * t
    return 2 * (ph - np.floor(ph + 0.5))


def lowpass(x, fc):
    return signal.sosfilt(signal.butter(2, min(fc, SR / 2 - 100), "low", fs=SR, output="sos"), x)


def place(buf, x, at):
    i = int(at * SR)
    if i >= len(buf):
        return
    m = min(len(x), len(buf) - i)
    buf[i:i + m] += x[:m]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bpm", type=float, required=True); ap.add_argument("--sections", required=True)
    ap.add_argument("--out", required=True); ap.add_argument("--style", choices=["pulse", "lofi", "drive"], default="pulse")
    ap.add_argument("--key", default="A"); ap.add_argument("--scale", choices=list(SCALES), default="minor")
    ap.add_argument("--seed", type=int, default=3); ap.add_argument("--fps", type=float, default=60)
    ap.add_argument("--end-hit", action="store_true", help="a final hit and ring-out after the last bar")
    ap.add_argument("--gaps", default="", help="beat indices preceded by half a beat of silence (pre-drop gaps)")
    a = ap.parse_args()
    rng = np.random.default_rng(a.seed)
    spb = 60.0 / a.bpm
    secs = [(s.split(":")[0], int(s.split(":")[1])) for s in a.sections.split(",")]
    bars = sum(b for _, b in secs)
    tail = 2.5 if a.end_hit else 0.5
    dur = bars * 4 * spb
    n = int((dur + tail) * SR)
    drums, bass, pad, arp = (np.zeros(n) for _ in range(4))
    root = 45 + NOTES[a.key.upper()]  # A2 = 45
    scale = SCALES[a.scale]
    degree_note = lambda deg, octave=0: root + 12 * octave + scale[deg % 7] + 12 * (deg // 7)
    swing = 0.08 if a.style == "lofi" else 0.0
    grid, bar_i = [], 0
    for name, nb in secs:
        for b in range(nb):
            bar_t = bar_i * 4 * spb
            chord_deg = PROG[a.scale][bar_i % 4]
            chord = [degree_note(chord_deg, 1), degree_note(chord_deg + 2, 1), degree_note(chord_deg + 4, 1)]
            progress = (b + 1) / nb
            full = name in ("drop",) or (name == "build" and a.style == "drive")
            groove = name == "groove"  # kit + bass, no arp: sits under a voice
            # Pad: every section except drop-only styles; filter opens through a build.
            if name != "outro" or b < nb - 1:
                pn = int(4 * spb * SR)
                chord_wave = sum(saw(hz(m), pn, d) for m in chord for d in (-0.003, 0.003)) / 6
                fc = 900 + (3200 * progress if name == "build" else 1800 if full else 1100)
                place(pad, lowpass(chord_wave, fc) * adsr(pn, 0.25, 0.4, 0.8, 0.4) * (0.5 if full else 0.7), bar_t)
            for k in range(4):
                t = bar_t + k * spb
                grid.append({"i": len(grid), "t": round(t, 4), "bar": bar_i + 1, "beat": k + 1,
                             "frame": round(t * a.fps), "section": name})
                if name in ("build", "drop", "groove", "outro") and not (name == "outro" and b == nb - 1 and k > 0):
                    if a.style != "lofi" or k in (0, 2):
                        place(drums, kick(int(0.45 * SR)) * 0.9, t)
                if name in ("drop", "groove") or (name == "build" and progress > 0.5) or (name == "outro" and b < nb - 1):
                    if k in (1, 3):
                        place(drums, snare(int(0.3 * SR), rng) * 0.35, t)
                if name != "break" and name != "hold":
                    for h in (0, 0.5):
                        off = h * spb + (swing * spb if h else 0)
                        place(drums, hat(int(0.12 * SR), rng, open_=(h and k == 3 and full)) * (0.12 if h else 0.08), t + off)
                if full or groove or (name == "build" and progress > 0.5):
                    bn = int(spb * 0.9 * SR)
                    note = degree_note(chord_deg) if k != 3 else degree_note(chord_deg + 4)
                    place(bass, lowpass(saw(hz(note), bn), 500) * adsr(bn, 0.004, 0.12, 0.5, 0.05) * 0.5, t)
                if full:
                    for s16 in range(2):
                        an = int(spb * 0.45 * SR)
                        note = chord[(k * 2 + s16) % 3] + 12
                        place(arp, lowpass(saw(hz(note), an), 2600) * adsr(an, 0.002, 0.08, 0.2, 0.05) * 0.18,
                              t + s16 * spb / 2)
            bar_i += 1
    if a.end_hit:
        place(drums, kick(int(1.2 * SR)) * 1.0, dur)
        hn = int(2.3 * SR); last = [degree_note(0, 1), degree_note(2, 1), degree_note(4, 1), degree_note(0, 2)]
        place(pad, lowpass(sum(saw(hz(m), hn, d) for m in last for d in (-0.003, 0.003)) / 8, 1800) * adsr(hn, 0.01, 0.3, 0.6, 1.5), dur)
        grid.append({"i": len(grid), "t": round(dur, 4), "bar": bars + 1, "beat": 1, "frame": round(dur * a.fps), "section": "end-hit"})
    for gb in [int(x) for x in a.gaps.split(",") if x.strip()]:
        g0, g1 = int((gb - 0.5) * spb * SR), int(gb * spb * SR)
        fade = int(0.004 * SR)
        for buf in (drums, bass, pad, arp):
            buf[g0:g1] = 0.0
            buf[max(g0 - fade, 0):g0] *= np.linspace(1, 0, g0 - max(g0 - fade, 0))
    stems = {"drums": drums, "bass": bass, "pad": pad, "arp": arp}
    mix = sum(stems.values())
    peak = np.max(np.abs(mix)) or 1
    g = 10 ** (-6 / 20) / peak
    os.makedirs(a.out + ".stems", exist_ok=True)
    width = int(0.0004 * SR)
    stereo = lambda x: np.stack([x, np.concatenate([np.zeros(width), x[:-width]])], axis=1)
    for k, v in stems.items():
        sf.write(os.path.join(a.out + ".stems", f"{k}.wav"), stereo(v * g), SR, subtype="PCM_24")
    sf.write(a.out + ".wav", stereo(mix * g), SR, subtype="PCM_24")
    downbeats = [b["t"] for b in grid if b["beat"] == 1]
    sec_starts, t0 = [], 0.0
    for name, nb in secs:
        sec_starts.append({"name": name, "start": round(t0, 4), "bars": nb}); t0 += nb * 4 * spb
    json.dump({"bpm": a.bpm, "seconds_per_beat": round(spb, 6), "fps": a.fps, "frames_per_beat": round(spb * a.fps, 4),
               "duration": round(dur + (tail if a.end_hit else 0), 4), "music_end": round(dur, 4), "beats": grid,
               "downbeats": downbeats, "sections": sec_starts, "style": a.style, "key": f"{a.key} {a.scale}", "seed": a.seed},
              open(a.out + ".grid.json", "w"), indent=1)
    print(f"{a.bpm} BPM, {bars} bars = {dur:.3f}s (+{tail}s tail), {len(grid)} beats; {spb * a.fps:.3f} frames/beat at "
          f"{a.fps} fps -> {a.out}.wav, {a.out}.grid.json")


if __name__ == "__main__":
    main()
