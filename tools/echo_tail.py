#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10,<3.14"
# dependencies = ["librosa>=0.10", "numpy", "scipy", "soundfile"]
# ///
"""A music bed that ends on an event (an in-app pause, a hard cut): a plain fade into it, a fade after it, or an
echo throw.

Usage:
  echo_tail.py SONG --out music.wav --stop S (--bpm 124.987 | --map map.json) [--start 0] [--place 0] [--duration S]
               [--repeats 8] [--first 0.92] [--feedback 0.63] [--throw 0.5] [--reverb 0.55] [--gain 0]
               [--json echo.json]
  echo_tail.py SONG --out music.wav --stop S (--bpm B | --map map.json) --fade-bars N [--beats-per-bar 4] ...
  echo_tail.py SONG --out music.wav --stop S --fade-from F [--start 0] [--place 0] [--duration S] [--gain 0]
  --stop    song seconds where the music stops (echo) or starts fading (--fade-bars).
  --place   edit seconds where song time --start lands; the stop lands at place + stop - start (printed).
  --map     a track_map.py JSON; its period sets the echo spacing and bar length.

Echo mode: the dry song from --start to --stop at --place, with an 8 ms fade at the stop (no click). The last
--throw seconds before the stop go to an echo bus and repeat every beat: repeat k (1..--repeats) ends k beats after
the stop, at gain first x feedback^(k-1), low-passed at max(700, 5200 / (1 + 0.55 k)) Hz (each darker), high-passed
at 180 Hz, panned 35 % to alternating sides. The bus, plus 0.35 x the last 0.6 s of the dry song, feeds a synthetic
stereo reverb (decaying noise, RT60 2.6 s, 2.8 s long, low-passed at 3.8 kHz, fixed seed) mixed at --reverb.
Fade mode: the song runs past --stop for N bars under a raised-cosine fade to silence (the plain "fade after the
second sixteen").
Fade-into mode (--fade-from F): the song plays untouched to song second F, then a plain linear fade reaches zero at
--stop; nothing follows (no echo, no reverb, no tempo needed). This is the default ending for an artist's own song:
the Demo Artist owner rejected the echo throw ("an echo I didn't personally add to the song") and asked for "a normal
fade" on 2026-09-29. The trailer: --fade-from 30.04 (the end of "had to change my phone.") --stop 31.313 (the in-app
pause) --place 1.442: a 1.27 s fade, peaks -3.9 / -10.9 / -20.1 dBFS at T 31.5 / 32.0 / 32.4 after the mix, digital
zero from the pause on.
Writes 48 kHz stereo 24-bit WAV. Duration defaults to the end of the tail (last echo + reverb, or the fade end).
Levels are not normalised (leave loudness to the mix); --gain scales the song at load, samples over 0 dBFS are
counted and a --gain that clears them is suggested. A bed that starts mid-song (--start > 0) fades in over 8 ms.
--json: the stop, each repeat's window (`echoes`: start/end are the send's placement, not what you hear), and
`hits`: the audible hit of each repeat, hits[k-1] = stop - throw + tau + k x period (edit time), where tau is the
throw's strongest onset (spectral flux on the song, searched 30 ms after the throw starts to 10 ms before the stop).
Key lockup type to hits[1..3] (repeats 2-4), not to the windows.

Measured 2026-09-29 against the Demo Artist trailer's hand-built sound/music.wav ("Changed My Phone" remix,
--stop 31.313 --place 1.442 --duration 39.5 --bpm 124.987 --first 0.92 --feedback 0.63): bit-identical (sample max
difference 0.0; per-0.25 s RMS max difference 0.000 dB over the 143 non-silent windows of 158). Stop at T 32.755,
echoes end at T 33.235, 33.715 ... 36.595 (gains 0.92 -> 0.036). The MP3 decodes with inter-sample overs (peak
+0.81 dBFS at 48 kHz), so that file hard-clips 754 samples in the hook; --gain -1 clears them (peak -0.19 dBFS).
--fade-bars 2 from 30.776 s: -13 dBFS in the fade's first half second, -50 dBFS in its last, ending on digital zero.
Negative controls: --stop past the end of the song (or a fade running past it) exits 1 naming the song length.
Re-measured 2026-09-29 after a cold-read test: with --gain -1.5 the output equals the trailer's rebuilt
sound/music.wav sample for sample (0 of 1,896,000 frames differ; gain applied after the tail differed by 1 LSB in
10,843 samples), and --gain 0 equals the previous version exactly. Hits: on the DemoIdent ident bed (--start 12.033
--stop 15.41 --place 0.25, 140.018 BPM) tau = 0.340 s (the kick on beat 35.5) and hits 3.896, 4.324 ... 6.895 sit
within 3.9 ms of onsets measured on the written bed (8 of 8); on the trailer bed 7 of 8 within 5 ms (the 8th,
gain 0.036, is under the reverb). The trailer had keyed its type to stop + k beats, 0.31 s after these hits. Fade-in:
the DemoIdent bed stepped from 0 to 0.051 in one sample at T 0.25; now its largest step in the first 2 ms is 0.021.
"""
import argparse, json, math, sys

import numpy as np

SR = 48000
IR_SECONDS = 2.8


def load(path):
    import librosa
    y, _ = librosa.load(path, sr=SR, mono=False)
    y = np.atleast_2d(y)
    return np.repeat(y, 2, 0) if y.shape[0] == 1 else y[:2]


def reverb_ir():
    from scipy.signal import butter, sosfilt
    rng = np.random.default_rng(3)
    L = int(IR_SECONDS * SR)
    t = np.arange(L) / SR
    ir = rng.standard_normal((2, L)) * np.exp(-6.9 * t / 2.6)          # -60 dB at 2.6 s
    ir = sosfilt(butter(2, 3800, "low", fs=SR, output="sos"), ir, axis=1)
    return ir / (np.abs(ir).sum(1, keepdims=True) ** 0.5 * 30)


def throw_transient(y, n1, throw):
    """Seconds into the throw of its strongest onset: spectral flux (hop 128) on the song itself with 0.1 s of context
    before the throw (no edge artefact), searched from 30 ms in (the send's fade-in) to 10 ms before the stop."""
    import librosa
    hop, ctx = 128, int(0.1 * SR)
    a = max(0, n1 - int(throw * SR) - ctx)
    env = librosa.onset.onset_strength(y=y[:, a:n1].mean(0).astype(np.float32), sr=SR, hop_length=hop)
    t = a / SR + np.arange(len(env)) * hop / SR - (n1 / SR - throw)        # seconds into the throw
    ok = (t >= 0.03) & (t <= throw - 0.01)
    return float(t[ok][int(np.argmax(env[ok]))])


def add(dst, src, at):
    """Mix src into dst starting at sample `at`, clipped to dst."""
    n = max(0, min(src.shape[1], dst.shape[1] - at))
    if at < dst.shape[1] and n:
        dst[:, at:at + n] += src[:, :n]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("song")
    ap.add_argument("--out", required=True)
    ap.add_argument("--stop", type=float, required=True, help="song seconds: the stop (or the fade start)")
    ap.add_argument("--start", type=float, default=0.0, help="song seconds the bed starts from")
    ap.add_argument("--place", type=float, default=0.0, help="edit seconds where --start lands")
    ap.add_argument("--duration", type=float, help="output length (default: end of the tail)")
    tempo = ap.add_mutually_exclusive_group()
    tempo.add_argument("--bpm", type=float)
    tempo.add_argument("--map", help="track_map.py JSON (uses its period)")
    ap.add_argument("--repeats", type=int, default=8)
    ap.add_argument("--first", type=float, default=0.92, help="gain of the first repeat")
    ap.add_argument("--feedback", type=float, default=0.63, help="gain ratio between repeats")
    ap.add_argument("--throw", type=float, default=0.5, help="seconds before the stop that repeat")
    ap.add_argument("--reverb", type=float, default=0.55, help="reverb return level")
    ap.add_argument("--fade-bars", type=float, help="fade the song out over N bars after --stop instead")
    ap.add_argument("--fade-from", type=float, help="song seconds: plain linear fade from here to zero at --stop")
    ap.add_argument("--beats-per-bar", type=int, default=4)
    ap.add_argument("--gain", type=float, default=0.0, help="dB applied to the whole bed (headroom for hot masters)")
    ap.add_argument("--json", help="write the stop, echo times and settings here")
    a = ap.parse_args()

    if a.fade_from is not None and a.fade_bars:
        sys.exit("--fade-from and --fade-bars are different endings; pass one")
    if a.fade_from is None and not (a.bpm or a.map):
        sys.exit("--bpm or --map is required for the echo and --fade-bars endings")
    D = json.load(open(a.map))["period"] if a.map else (60.0 / a.bpm if a.bpm else None)
    y = load(a.song) * 10 ** (a.gain / 20)     # gain at load, as the trailer's bed was built (bit-exact at -1.5 dB)
    song_dur = y.shape[1] / SR
    fade_s = a.fade_bars * a.beats_per_bar * D if a.fade_bars else 0.0
    if a.stop > song_dur or a.stop + fade_s > song_dur:
        sys.exit(f"--stop {a.stop:g} s{f' + {a.fade_bars:g} bars of fade' if fade_s else ''} is past the end of the "
                 f"song ({song_dur:.3f} s)")
    if not 0 <= a.start < a.stop:
        sys.exit(f"need 0 <= --start ({a.start:g}) < --stop ({a.stop:g})")
    if a.fade_from is not None and not a.start <= a.fade_from < a.stop:
        sys.exit(f"--fade-from {a.fade_from:g} must be in [--start {a.start:g}, --stop {a.stop:g})")
    if not fade_s and a.fade_from is None and not 0 < a.throw <= a.stop - a.start:
        sys.exit(f"--throw {a.throw:g} s must be > 0 and fit between --start and --stop")

    stop_T = a.place + a.stop - a.start
    if a.duration:
        dur = a.duration
    elif fade_s:
        dur = stop_T + fade_s
    elif a.fade_from is not None:
        dur = stop_T
    else:
        dur = math.ceil((stop_T + a.repeats * D + IR_SECONDS) * 10) / 10
    if dur <= stop_T:
        sys.exit(f"--duration {dur:g} s ends before the stop at T {stop_T:.3f}")
    out = np.zeros((2, int(dur * SR)))
    at, n0, n1 = int(a.place * SR), int(a.start * SR), int(a.stop * SR)
    n = n1 - n0
    k8 = int(0.008 * SR)
    fade_in = np.linspace(0, 1, k8) if a.start > 0 else None     # a cut into the song mid-signal steps: no click
    mode = "fade" if fade_s else ("fade-into" if a.fade_from is not None else "echo")
    report = {"song": a.song, "out": a.out, "mode": mode, "period": D, "start": a.start,
              "place": a.place, "stop": {"song": a.stop, "edit": round(stop_T, 4)}, "duration": dur}

    if a.fade_from is not None:
        seg = y[:, n0:n1].copy()
        nfrom = int(a.fade_from * SR) - n0
        seg[:, nfrom:] *= np.linspace(1.0, 0.0, n - nfrom)                        # plain linear fade to zero
        if fade_in is not None:
            seg[:, :k8] *= fade_in
        add(out, seg, at)
        from_T = a.place + a.fade_from - a.start
        report["fade"] = {"from": {"song": a.fade_from, "edit": round(from_T, 4)}, "seconds": round(stop_T - from_T, 4),
                          "curve": "linear"}
        print(f"fade into the stop: T {from_T:.3f} -> {stop_T:.3f} (song {a.fade_from:g}-{a.stop:g} s, linear, "
              f"zero from the stop on); song placed at T {a.place:g}")
    elif fade_s:
        nf = int(fade_s * SR)
        seg = y[:, n0:n1 + nf].copy()
        seg[:, n:] *= 0.5 * (1 + np.cos(np.pi * np.arange(nf) / nf))
        if fade_in is not None:
            seg[:, :k8] *= fade_in
        add(out, seg, at)
        report["fade"] = {"bars": a.fade_bars, "seconds": round(fade_s, 4), "end": round(stop_T + fade_s, 4)}
        print(f"fade: T {stop_T:.3f} -> {stop_T + fade_s:.3f} ({a.fade_bars:g} bars of {a.beats_per_bar} at "
              f"{60 / D:.3f} BPM); song {a.start:g}-{a.stop + fade_s:.3f} s placed at T {a.place:g}")
    else:
        from scipy.signal import butter, fftconvolve, sosfilt
        dry = y[:, n0:n1].copy()
        dry[:, -k8:] *= np.linspace(1, 0, k8)                                  # clean stop, no click
        if fade_in is not None:
            dry[:, :k8] *= fade_in
        add(out, dry, at)
        send = y[:, n1 - int(a.throw * SR):n1].copy()
        ramp = int(0.03 * SR)
        send[:, :ramp] *= np.linspace(0, 1, ramp)
        send[:, -int(0.01 * SR):] *= np.linspace(1, 0, int(0.01 * SR))
        tau = throw_transient(y, n1, a.throw)
        bus = np.zeros_like(out)
        hp = butter(1, 180, "high", fs=SR, output="sos")
        echoes = []
        for k in range(1, a.repeats + 1):
            g = a.first * a.feedback ** (k - 1)
            lp_hz = max(700.0, 5200 / (1 + 0.55 * k))
            e = sosfilt(hp, sosfilt(butter(2, lp_hz, "low", fs=SR, output="sos"), send, axis=1), axis=1) * g
            pan = 0.35 if k % 2 else -0.35
            e[0] *= 1 - pan
            e[1] *= 1 + pan
            s0 = at + n - send.shape[1] + int(k * D * SR)
            add(bus, e, s0)
            echoes.append({"k": k, "start": round(s0 / SR, 4), "end": round((s0 + send.shape[1]) / SR, 4),
                           "gain": round(g, 4), "lowpass_hz": round(lp_hz), "pan": "R" if pan > 0 else "L"})
        last = np.zeros_like(out)
        t0 = max(0, at + n - int(0.6 * SR))
        last[:, t0:at + n] = out[:, t0:at + n]
        ir = reverb_ir()
        wet = np.stack([fftconvolve(bus[c] + 0.35 * last[c], ir[c])[:out.shape[1]] for c in range(2)])
        out += bus + a.reverb * wet
        report["echoes"] = echoes
        # The audible hit of each repeat: the throw's strongest transient, tau seconds into the throw. Echo k's
        # window starts at stop - throw + k beats, so hits[k-1] = stop - throw + tau + k x period (edit time).
        report["throwTransient"] = {"song": round(a.stop - a.throw + tau, 4), "edit": round(stop_T - a.throw + tau, 4)}
        report["hits"] = [round(e["start"] + tau, 4) for e in echoes]
        report["settings"] = {"repeats": a.repeats, "first": a.first, "feedback": a.feedback, "throw": a.throw,
                              "reverb": a.reverb}
        print(f"stop: song {a.stop:g} s -> T {stop_T:.3f} (placed at T {a.place:g}); throw song "
              f"{a.stop - a.throw:.3f}-{a.stop:g} s, one repeat per beat ({60 / D:.3f} BPM)")
        print("echoes end at T " + ", ".join(f"{e['end']:.3f}" for e in echoes)
              + f"; gains {echoes[0]['gain']} -> {echoes[-1]['gain']}")
        print(f"echo hits (the throw's transient at song {report['throwTransient']['song']:.3f} s, repeated) at T "
              + ", ".join(f"{h:.3f}" for h in report["hits"]))

    import soundfile as sf
    peak = float(np.abs(out).max())
    over = int((np.abs(out) > 1.0).any(0).sum())
    report.update(gain_db=a.gain, peak_dbfs=round(20 * math.log10(max(peak, 1e-9)), 2), clipped_samples=over)
    sf.write(a.out, out.T.astype(np.float32), SR, subtype="PCM_24")
    print(f"wrote {a.out}: {dur:g} s, 48 kHz stereo 24-bit, gain {a.gain:g} dB, peak {report['peak_dbfs']} dBFS")
    if over:
        print(f"warning: {over} samples over 0 dBFS clip in the 24-bit file (decoded MP3s often have inter-sample "
              f"overs); --gain {-math.ceil((report['peak_dbfs'] + 0.1) * 2) / 2:g} clears them")
    if a.json:
        json.dump(report, open(a.json, "w"), indent=1)


if __name__ == "__main__":
    main()
