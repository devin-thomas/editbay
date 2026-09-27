#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy", "soundfile", "scipy"]
# ///
"""Synthesise a small, deterministic SFX palette (no stock sounds, no paid API, same output every run).

Usage:
  sfx_synth.py --out sound/sfx [--seed 7] [--only whoosh,click] [--list]
Sounds: whoosh, whoosh-short, riser, impact, sub-drop, click, tick, pop, shimmer, glitch, type, ding, swell.
Each is 48 kHz 24-bit stereo WAV, peak -3 dBFS, with a short silent tail. Pick by ear: render a preview with
`sfx_synth.py --out /tmp/sfx --preview` (all sounds in a row, 0.5 s apart).
Motion and sound: an entrance gets a whoosh or a click, a lock-up gets an impact, a count or a tick-over gets a tick,
a reveal gets a shimmer. One hit per idea; a sound on every element is noise.
"""
import argparse, os

import numpy as np
import soundfile as sf
from scipy import signal

SR = 48000


def env(n, a, d, curve=3.0):
    """Attack (samples) then exponential-ish decay over the rest."""
    e = np.ones(n)
    a = max(1, min(a, n - 1))
    e[:a] = np.linspace(0, 1, a)
    e[a:] = np.power(np.linspace(1, 0, n - a), curve)
    return e * d


def bandnoise(n, rng, lo, hi):
    x = rng.standard_normal(n)
    sos = signal.butter(4, [max(lo, 20), min(hi, SR / 2 - 100)], btype="band", fs=SR, output="sos")
    return signal.sosfilt(sos, x)


def sweep_filter(x, f0, f1, q=0.7):
    """Time-varying low-pass sweep done in blocks (cheap, smooth enough for SFX)."""
    out, blk = np.zeros_like(x), 512
    freqs = np.geomspace(f0, f1, len(x) // blk + 1)
    zi = None
    for k in range(0, len(x), blk):
        sos = signal.butter(2, min(freqs[k // blk], SR / 2 - 200), btype="low", fs=SR, output="sos")
        if zi is None:
            zi = signal.sosfilt_zi(sos) * 0
        out[k:k + blk], zi = signal.sosfilt(sos, x[k:k + blk], zi=zi)
    return out


def t_(dur):
    return np.arange(int(dur * SR)) / SR


def whoosh(rng, dur=0.7, up=True):
    n = int(dur * SR); x = rng.standard_normal(n)
    x = sweep_filter(x, 300 if up else 6000, 6000 if up else 300)
    shape = np.sin(np.pi * np.linspace(0, 1, n)) ** 2
    return x * shape


def riser(rng, dur=1.6):
    n = int(dur * SR); tt = t_(dur)
    noise = sweep_filter(rng.standard_normal(n), 200, 9000) * np.linspace(0, 1, n) ** 2
    tone = np.sin(2 * np.pi * np.cumsum(np.geomspace(180, 900, n)) / SR) * np.linspace(0, 0.5, n) ** 2
    return noise + tone


def impact(rng, dur=0.9):
    tt = t_(dur); n = len(tt)
    f = np.geomspace(58, 41, n)
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, int(0.004 * SR), 1.0, 2.2)
    harm = 0.35 * np.sin(2 * np.pi * np.cumsum(f * 2) / SR) * env(n, int(0.004 * SR), 1.0, 4)  # phone speakers
    click = bandnoise(n, rng, 1500, 8000) * env(n, 20, 0.6, 12)
    return sub + harm + click


def sub_drop(rng, dur=1.2):
    tt = t_(dur); n = len(tt); f = np.geomspace(90, 30, n)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, int(0.01 * SR), 1.0, 1.6)


def click(rng, dur=0.08):
    n = int(dur * SR); return bandnoise(n, rng, 2000, 12000) * env(n, 10, 1.0, 10)


def tick(rng, dur=0.05):
    tt = t_(dur); return np.sin(2 * np.pi * 2400 * tt) * env(len(tt), 5, 1.0, 6)


def pop(rng, dur=0.12):
    tt = t_(dur); n = len(tt); f = np.geomspace(900, 280, n)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 20, 1.0, 5)


def shimmer(rng, dur=1.0):
    tt = t_(dur); n = len(tt); x = np.zeros(n)
    for k, fr in enumerate(rng.uniform(2500, 7000, 7)):
        vib = 1 + 0.004 * np.sin(2 * np.pi * rng.uniform(4, 7) * tt)
        x += np.sin(2 * np.pi * np.cumsum(fr * vib) / SR + rng.uniform(0, 6)) / (k + 2)
    return x * env(n, int(0.05 * SR), 1.0, 2.5)


def glitch(rng, dur=0.35):
    n = int(dur * SR); x = np.zeros(n); pos = 0
    while pos < n:
        ln = int(rng.uniform(0.01, 0.05) * SR)
        f = rng.choice([220, 440, 880, 1760, 3520])
        seg = np.sign(np.sin(2 * np.pi * f * np.arange(min(ln, n - pos)) / SR)) * rng.uniform(0.2, 1)
        x[pos:pos + len(seg)] = np.round(seg * 4) / 4
        pos += len(seg) + int(rng.uniform(0, 0.02) * SR)
    return x * env(n, 5, 1.0, 1)


def type_(rng, dur=0.6):
    n = int(dur * SR); x = np.zeros(n)
    for t0 in np.sort(rng.uniform(0, dur - 0.05, 7)):
        i = int(t0 * SR); m = int(0.03 * SR)
        x[i:i + m] += bandnoise(m, rng, 1800, 9000) * env(m, 5, rng.uniform(0.5, 1), 8)
    return x


def ding(rng, dur=1.4):
    tt = t_(dur); n = len(tt)
    return sum(np.sin(2 * np.pi * f * tt) * a for f, a in ((1320, 1), (2640, .35), (3960, .15), (1980, .2))) * env(n, 30, 1, 3)


def swell(rng, dur=1.8):
    tt = t_(dur); n = len(tt)
    pad = sum(np.sin(2 * np.pi * f * tt + rng.uniform(0, 6)) for f in (220, 277.2, 329.6, 440))
    return pad * np.sin(np.pi * np.linspace(0, 1, n)) ** 1.5


SOUNDS = {"whoosh": lambda r: whoosh(r, 0.7, True), "whoosh-short": lambda r: whoosh(r, 0.35, False), "riser": riser,
          "impact": impact, "sub-drop": sub_drop, "click": click, "tick": tick, "pop": pop, "shimmer": shimmer,
          "glitch": glitch, "type": type_, "ding": ding, "swell": swell}


def finish(x, rng, width=0.15):
    x = np.concatenate([x, np.zeros(int(0.05 * SR))])
    peak = np.max(np.abs(x)) or 1
    x = x / peak * 10 ** (-3 / 20)
    d = int(rng.uniform(0.0002, 0.0006) * SR)  # tiny inter-channel delay for width
    left, right = x, np.concatenate([np.zeros(d), x[:-d]]) * (1 - width) + x * width
    return np.stack([left, right], axis=1)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True); ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--only"); ap.add_argument("--list", action="store_true"); ap.add_argument("--preview", action="store_true")
    a = ap.parse_args()
    if a.list:
        print("\n".join(SOUNDS)); return
    os.makedirs(a.out, exist_ok=True)
    names = [n for n in (a.only.split(",") if a.only else SOUNDS)]
    parts = []
    for k, name in enumerate(names):
        rng = np.random.default_rng(a.seed * 1000 + k)
        y = finish(SOUNDS[name](rng), rng)
        sf.write(os.path.join(a.out, f"{name}.wav"), y, SR, subtype="PCM_24")
        parts += [y, np.zeros((int(0.5 * SR), 2))]
        print(f"{name:13} {len(y) / SR:5.2f}s -> {os.path.join(a.out, name + '.wav')}")
    if a.preview:
        sf.write(os.path.join(a.out, "_preview.wav"), np.concatenate(parts), SR, subtype="PCM_24")


if __name__ == "__main__":
    main()
