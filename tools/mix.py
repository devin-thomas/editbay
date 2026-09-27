#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy", "soundfile", "soxr"]
# ///
"""Mix voice, music, and timed SFX; duck the music under speech; hit a loudness target on the delivered mix.

Usage:
  mix.py --out sound/mix.wav --duration 45.0 [--voice narration/narration.wav] [--voice-offset 0.0]
         [--music sound/bed.wav --music-gain -6 --duck 14] [--sfx cues.json] [--target -16 --tp -1.5]
cues.json: [{"t": 1.20, "file": "sound/sfx/whoosh.wav", "gain_db": -8}, ...] (or beats.resolved.json: cues with an
"sfx" name are placed at their start using --sfx-dir).
Ducking: the music is pulled down by --duck dB wherever the voice is speaking (20 ms RMS detector, 60 ms attack,
350 ms release), so beds sit well under the voice at every sentence onset. Writes the mix (48 kHz stereo 24-bit),
OUT.stems/{voice,music,sfx}.wav (post-duck, pre-master), and OUT.loudness.json. Normalisation: two-pass loudnorm
to --target with a --tp ceiling; measure the DELIVERED file again after encoding (AAC adds up to ~0.3 dB of peak).
"""
import argparse, json, os, subprocess, tempfile

import numpy as np
import soundfile as sf
import soxr

SR = 48000
HERE = os.path.dirname(os.path.abspath(__file__))


def load(path):
    y, sr = sf.read(path, always_2d=True)
    if sr != SR:
        y = soxr.resample(y, sr, SR)
    if y.shape[1] == 1:
        y = np.repeat(y, 2, axis=1)
    return y[:, :2]


def place(buf, y, at, gain_db=0.0):
    i = int(round(at * SR))
    if i >= len(buf) or i + len(y) <= 0:
        return
    if i < 0:
        y, i = y[-i:], 0
    m = min(len(y), len(buf) - i)
    buf[i:i + m] += y[:m] * 10 ** (gain_db / 20)


def duck_curve(voice, depth_db, thr_db=-38, attack=0.06, release=0.35):
    mono = np.abs(voice).mean(axis=1)
    hop = int(0.02 * SR)
    frames = mono[: len(mono) // hop * hop].reshape(-1, hop)
    rms = 20 * np.log10(np.sqrt((frames ** 2).mean(axis=1)) + 1e-9)
    target = np.where(rms > thr_db, -depth_db, 0.0)
    g, out = 0.0, np.zeros_like(target)
    a_c, r_c = np.exp(-0.02 / attack), np.exp(-0.02 / release)
    for k, tv in enumerate(target):
        coef = a_c if tv < g else r_c
        g = coef * g + (1 - coef) * tv
        out[k] = g
    curve = np.repeat(10 ** (out / 20), hop)
    return np.concatenate([curve, np.full(len(mono) - len(curve), curve[-1] if len(curve) else 1.0)])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True); ap.add_argument("--duration", type=float, required=True)
    ap.add_argument("--voice"); ap.add_argument("--voice-offset", type=float, default=0.0); ap.add_argument("--voice-gain", type=float, default=0.0)
    ap.add_argument("--music"); ap.add_argument("--music-offset", type=float, default=0.0); ap.add_argument("--music-gain", type=float, default=-6.0)
    ap.add_argument("--duck", type=float, default=14.0, help="dB of music reduction under speech")
    ap.add_argument("--fade-out", type=float, default=0.6, help="music fade at the end (s)")
    ap.add_argument("--sfx"); ap.add_argument("--sfx-dir"); ap.add_argument("--sfx-gain", type=float, default=-8.0)
    ap.add_argument("--target", type=float, default=-16.0); ap.add_argument("--tp", type=float, default=-1.5)
    a = ap.parse_args()
    n = int(a.duration * SR)
    voice, music, sfx = (np.zeros((n, 2)) for _ in range(3))
    if a.voice:
        place(voice, load(a.voice), a.voice_offset, a.voice_gain)
    if a.music:
        place(music, load(a.music), a.music_offset, a.music_gain)
        if a.fade_out > 0:
            f = int(a.fade_out * SR); music[-f:] *= np.linspace(1, 0, f)[:, None]
        if a.voice and a.duck > 0:
            music *= duck_curve(voice, a.duck)[:, None]
    placed = []
    if a.sfx:
        cues = json.load(open(a.sfx))
        if isinstance(cues, dict):  # beats.resolved.json
            cues = [{"t": c["start"] + c.get("sfx_offset", -0.05), "file": os.path.join(a.sfx_dir, c["sfx"] + ".wav"),
                     "gain_db": c.get("sfx_gain", a.sfx_gain)} for c in cues["cues"] if c.get("sfx")]
        for c in cues:
            place(sfx, load(c["file"]), c["t"], c.get("gain_db", a.sfx_gain)); placed.append(c)
    os.makedirs(a.out + ".stems", exist_ok=True)
    for name, y in (("voice", voice), ("music", music), ("sfx", sfx)):
        sf.write(os.path.join(a.out + ".stems", f"{name}.wav"), y, SR, subtype="PCM_24")
    pre = voice + music + sfx
    tmp = os.path.join(tempfile.mkdtemp(), "pre.wav")
    sf.write(tmp, pre, SR, subtype="FLOAT")
    r = subprocess.run(["python3", os.path.join(HERE, "loudness.py"), tmp, "--normalize", a.out, "--target", str(a.target),
                        "--tp", str(a.tp), "--json", a.out + ".loudness.json"], capture_output=True, text=True)
    print(r.stdout.strip() or r.stderr.strip())
    # Integer PCM for delivery, same duration as asked (loudnorm can add a few samples).
    y, _ = sf.read(a.out, always_2d=True)
    y = y[:n] if len(y) >= n else np.vstack([y, np.zeros((n - len(y), y.shape[1]))])
    sf.write(a.out, y, SR, subtype="PCM_24")
    print(f"mixed {a.duration}s: voice={'yes' if a.voice else 'no'} music={'yes' if a.music else 'no'} "
          f"(duck {a.duck} dB) sfx={len(placed)} -> {a.out}")


if __name__ == "__main__":
    main()
