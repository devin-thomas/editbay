#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10,<3.14"
# dependencies = ["librosa>=0.10", "numpy", "soundfile", "scipy"]
# ///
"""Map a supplied track for a music-led edit: tempo grid, bars, sections, groove, lyric anchors, per-frame features.

Usage:
  track_map.py SONG --out map.json [--md MAP.md] [--window 0:45] [--stems DIR [--stems-start S] | --separate]
               [--words] [--fps 60] [--offset 0.0] [--duration S] [--beats-per-bar 4] [--downbeat BEAT_INDEX]
               [--bpm-hint BPM | --grid-from MAP.json] [--peaks 3000]
  --window START:END  song seconds to analyse (0:45 = the first 45 s; "30:" = 30 s to the end; default whole song).
  --offset S          edit time T = song time + S (the song starts S seconds into the edit). Per-frame data covers
                      T = 0 .. --duration (default: window end + offset) and is zero outside the window; the beat
                      grid continues to --duration.
  --stems DIR         reuse Demucs stems (drums/bass/vocals/other.wav) whose sample 0 is song time --stems-start
                      (default: the window start). Checked: the stems must sum back to the mix.
  --separate          run Demucs htdemucs on the window in a subprocess (mps on Apple silicon, else cpu) and cache
                      the stems in <dir of --out>/stems/htdemucs/<song>-<start>-<end>/; a second run reuses them.
  --words             faster-whisper small.en (int8, cpu) word times on the vocal stem, in a subprocess. They are
                      lyric ANCHORS for timing only; never put ASR words on screen as lyrics.
  --downbeat K        beat K (0-based, counted from the first beat in the window) is a downbeat.
  --bpm-hint BPM      search only around this tempo (no octave choice), for a track the prior gets wrong.
  --grid-from MAP     reuse an earlier map's grid (period, first beat, downbeat, beats per bar), its loudness
                      references and, when no stem option is given, its stems: the window then only slices features,
                      events, groove and wave. Map the song once (--window 0:60 or the whole song), then map each
                      edit window with --grid-from. A grid beat up to 20 ms before the window start opens it.

Tempo: a constant period and phase, grid-searched on the onset envelope (hop 128 at 44.1 kHz) around the librosa
estimate and its x2 and x0.5 octaves (+-5 %, period step 0.02 %, phase step 2 ms). Score = mean of the maximum onset
strength within +-10 ms of each grid beat. That score always favours the slower octave (it keeps the stronger half of
the beats: 0.91 at 62.5 BPM vs 0.68 at 125 on the test song), so the octave is chosen by score x librosa's tempo
prior (log-normal, 120 BPM, one-octave sigma). The winner is refined by weighted least squares on the envelope peak
nearest each beat (+-25 ms, the stronger half of the beats), because the +-10 ms score is flat in phase.
Confidence = best score / mean of the max-filtered envelope (what a random grid scores). Below 3.0 the tool prints
"no stable tempo" and exits 1. Measured 2026-09-29 (song: "Changed My Phone" remix, 320 kbps MP3):
  song 0:45                        conf 5.04 -> 124.997 BPM, period 0.480011 s, first beat 0.056 s, residual 12.6 ms
  song 0:15 (intro, no drums)      conf 6.45 -> 125.026 BPM
  song 0:30 / 10:45 / 30:90 / all  conf 5.62 / 4.91 / 4.61 / 5.05 -> 124.961 / 124.992 / 124.985 / 124.997 BPM
  song 0:8                         conf 12.4 -> 62.4 BPM: too few beats, the prior loses; use --bpm-hint
  pink noise 20 s (anoisesrc)      conf 1.66 (its slower octave 2.27) -> "no stable tempo", exit 1
  white noise 20 s                 conf 1.77 (2.21) -> exit 1
  The run's hand grid was 0.48005 s / 0.058 s: 0.04 ms per beat and 2 ms of phase from this fit.
Downbeat: what the arrangement does, voted by phase. (1) Section changes: per beat, the 2-bars-after vs 2-bars-before
level change of drums, bass and other (dB, floored 40 dB under each stem's loud beats and 45 dB under the mix's, so
separation bleed does not count); local peaks of at least 20 dB and half the largest vote their size. (2) The first
bass or drums entrance: the stem's first beat within 6 dB of its loud beats (stepped back up to 3 beats while it is
present), after 2 bars averaging 24 dB or more under them; it votes its rise. A stem loud at the window start has
none. Low-band (<150 Hz) energy is only the fallback when nothing votes, and the first vocal entrance is only
reported (phrases start on pickups: DemoIdent' first line starts on beat 3 of bar 6). When the cues disagree the tool
prints the per-phase votes, every cue, and the check to make; --downbeat settles it. Measured 2026-09-29:
  "Changed My Phone" 0:45 / 10:45 / 0:30 / 30:90 / whole song: right, unanimous (0:45: changes at beats 32, 64, 72
  and the bass entrance at 32; whole song: 11 changes, all phase 0; low-band energy by phase 0.85 / 1.00 / 0.49 /
  0.54 would pick beat 1: the 808 lands on beat 1 of odd bars and beat 2 of even bars).
  "DemoIdent" (140 BPM; owner: the bass enters on bar 9 = beat 32) 0:60: right, 86 % (phase 0: changes at 16, 32, 100
  and the bass entrance at 32; the change at 129 votes phase 1, where the bass comes back on beat 3 of bar 33).
  The previous one-bar windows voted the groove's bass gap (beats 46, 50, 78, 82, 130, 134: phase 2 316 dB vs
  phase 0 237 dB), no phase reached 2/3, and low-band energy picked beat 3 with no note. 10:60 right (83 %), 0:30
  right (unanimous), 20:60 right but weak (57 %, flagged: the window starts after the first bass entrance), whole
  song (317 s) right but weak (51 %, flagged: later bass returns land on beat 3). Weak picks print "weak".
Per bar: RMS (dBFS) of the mix and each stem; a stem is present when its bar RMS is within 20 dB of its own loud bars
(95th percentile) and above the mix's loud bars - 36 dB (hook drums -27 dB vs intro bleed -73 dB, mix -9 dB).
Sections are runs of bars with the same stems present, named intro (before drums and bass first play together),
hook (both present) and break (after a hook, without them); the names are guesses, the +/- changes are measured.
Test song, 0:45: intro bars 1-8 (vocals, other); hook bars 9-16 from 15.42 s (+drums, +bass); break bars 17-18 from
30.78 s (-drums, -bass); hook 2 bars 19-23; and the window's last bar, 24, partial (1.63 beats: drums, bass and
other really drop out at 44.22 s). A last bar holding at least 1 beat is mapped and flagged partial; its steps past
the window end read '-'. Groove: a 16-step string per bar and voice (X > 0.56 x ref, x > 0.25 x
ref, . none; ref = the voice's loud bars, so a silent bar reads as dots) from spectral flux: bass (bass stem
<100 Hz), kick (drums <120 Hz), clap (drums 150-2500 Hz), hat (drums >6 kHz). Test song: clap `........X.......`
(beat 3) in every hook bar; bass X on beat 1 of odd hook bars and beat 2 of even ones.
The loudness references (presence, groove, envelopes, bands) are the window's own unless --grid-from supplies them
(`refs` in the JSON). DemoIdent ident window 12.033:15.41 with --bpm-hint 140.018 alone refits to 139.655 BPM with
its first beat on 12.461 (beat 29), so --downbeat 0 marks the wrong beat; window 0:15.48 reads bar 9's bass as
`XxXXXxxxXXXXXXXX` (12 X: its one bass bar is its own reference). With --grid-from the 0:60 map it keeps 140.018 BPM,
bars 8-9 (9 partial, 3.88 beats), bass `X...X...Xxxxxxxx` as in the 0:60 map, and grid hits bass 1.964, 2.392,
2.821 and clap 2.821, 3.464 (T = song - 11.783). On "Changed My Phone" 0:45 every tempo, grid, feature, band, wave
and event value is unchanged from the previous version; only the partial bar 24 is new.
Negative controls: --grid-from with a missing file, broken JSON, a non-numeric period, an unstable map, or a JSON
that is not a track map exits 1 naming the problem; --grid-from with --bpm-hint exits 1.
Stem check: sum of stems vs mix, aligned -33.9 dB; the same stems 20 ms late +2.1 dB (warns above -10 dB).

JSON (the schema the HyperFrames audio kit of the Demo Artist trailer read; times are edit time unless named song):
fps, preroll (= offset), offset, songStop, period, beat0, bars (downbeat times), beats, features{mix,bass,drums,vox,
mel} (per-frame RMS envelopes, instant attack, 0.10-0.23 s release, 0-1.2), bands (per frame, 32 log bands
40 Hz-16 kHz as 0-99), events{bass,kick,clap,hat,mel (onset times), words ({t,e}), grid{bass,kick,clap,hat} (X steps
snapped to the grid)}, wave{start (the edit time where peaks[0] plays: window start + offset; equals offset only
when the window starts at song 0), dur, peaks[[min,max]...]}; plus tempo, downbeat (with votes and cues), beatOrigin
(song time of beat 0 for beat numbers), stems, refs, barMap (per-bar RMS, presence, groove; partial), sections,
words ({w,s,e} in song time). With --window 0:31.26 --offset 1.442 --duration 40 the
envelopes match that run's data/audio.json at correlation 1.0000 (max difference 0.024), bands match except the two
frames at the window edge, and grid claps sit within 2.4 ms of its hand-placed claps.
Without stems, bass/drums/vox/mel are proxies (mix <150 Hz, HPSS percussive, harmonic 300-3400 Hz, harmonic) and
sections are omitted. Subprocess versions that worked 2026-09-29: demucs 4.1.0 + torch 2.14 (24 s window on mps,
13 s wall); faster-whisper 1.2.1 (audio passed as an array: its PyAV 19 decoder rejects 'metadata_errors').
"""
import argparse, json, os, shutil, subprocess, sys, tempfile

import numpy as np

SR = 44100
HOP = 128
STEMS = ("drums", "bass", "vocals", "other")
MIN_CONFIDENCE = 3.0
PRESENT_REL_DB = 20.0   # a stem is present within this many dB of its own loud bars
PRESENT_MIX_DB = 36.0   # and above the mix's loud bars minus this (a stem that never plays stays absent)
CHANGE_MIN_DB = 20.0    # a section change: at least this, and half the window's largest
ENTER_LOUD_DB = 6.0     # an entrance: a beat within 6 dB of the stem's loud beats (95th percentile)
ENTER_QUIET_DB = 24.0   # after two bars averaging at least 24 dB under them (the mix-based floor can sit 29 dB under)
MIN_PARTIAL_BEATS = 1.0 # a window's last, incomplete bar is mapped (flagged partial) when it holds at least 1 beat
GRID_SNAP_S = 0.02      # --grid-from: a grid beat this close before the window start still opens the window
VOICES = {"bass": ("bass", 20, 100), "kick": ("drums", 20, 120), "clap": ("drums", 150, 2500),
          "hat": ("drums", 6000, 16000)}
# Runs in its own uv environment. The audio goes in as a 16 kHz array: faster-whisper 1.2.1's own decoder fails with
# PyAV 19 ("unexpected keyword argument 'metadata_errors'", 2026-09-29).
WHISPER = r"""
import json, sys, wave
import numpy as np
from faster_whisper import WhisperModel
with wave.open(sys.argv[1]) as f:
    audio = np.frombuffer(f.readframes(f.getnframes()), np.int16).astype(np.float32) / 32768
m = WhisperModel("small.en", device="cpu", compute_type="int8")
segs, _ = m.transcribe(audio, word_timestamps=True, vad_filter=False, beam_size=5)
words = [{"w": w.word.strip(), "s": round(w.start, 2), "e": round(w.end, 2)} for s in segs for w in (s.words or [])]
json.dump(words, open(sys.argv[2], "w"))
"""


def db(x):
    return float(20 * np.log10(max(float(x), 1e-9)))


def parse_window(text, song_dur):
    a, _, b = text.partition(":")
    start = float(a or 0)
    end = float(b) if b else song_dur
    end = min(end, song_dur)
    if not 0 <= start < end:
        sys.exit(f"--window {text}: need 0 <= start < end <= song length ({song_dur:.2f} s)")
    return start, end


# ---------------------------------------------------------------- tempo
def fit_tempo(y, bpm_hint=None):
    import librosa
    from scipy.ndimage import maximum_filter1d
    hs = HOP / SR
    oenv = librosa.onset.onset_strength(y=y, sr=SR, hop_length=HOP, aggregate=np.median)
    L = len(oenv) * hs
    rad = int(round(0.010 / hs))
    mx = maximum_filter1d(oenv, 2 * rad + 1, mode="constant")
    base = float(mx.mean()) or 1e-9
    est = bpm_hint or float(np.atleast_1d(librosa.feature.tempo(onset_envelope=oenv, sr=SR, hop_length=HOP))[0])

    def scores(T, phases):
        k = np.arange(int(L / T) + 1)
        bt = phases[:, None] + k[None, :] * T
        ok = bt < L - 0.011
        v = np.where(ok, mx[np.clip(np.round(bt / hs).astype(int), 0, len(mx) - 1)], 0)
        return v.sum(1) / np.maximum(ok.sum(1), 1)

    cands = []
    for m in ((1.0,) if bpm_hint else (0.5, 1.0, 2.0)):
        T0 = 60.0 / (est * m)
        best = (-1.0, T0, 0.0)
        for T in np.arange(T0 * 0.95, T0 * 1.05, T0 * 2e-4):
            ph = np.arange(0, T, 0.002)
            s = scores(T, ph)
            i = int(np.argmax(s))
            if s[i] > best[0]:
                best = (float(s[i]), float(T), float(ph[i]))
        bpm = 60.0 / best[1]
        prior = 1.0 if bpm_hint else float(np.exp(-0.5 * np.log2(bpm / 120.0) ** 2))
        cands.append({"bpm": round(bpm, 3), "score": round(best[0], 4), "confidence": round(best[0] / base, 2),
                      "prior": round(prior, 3), "period": best[1], "phase": best[2]})
    pick = max(cands, key=lambda c: c["score"] * c["prior"])
    T, ph = pick["period"], pick["phase"]
    # Least-squares refinement on the envelope peak nearest each beat (the stronger half of the beats).
    resid_ms = None
    for _ in range(2):
        k = np.arange(int((L - ph) / T))
        bt = ph + k * T
        lo = np.clip(np.round((bt - 0.025) / hs).astype(int), 0, len(oenv) - 1)
        w = int(round(0.05 / hs)) + 1
        idx = np.clip(lo[:, None] + np.arange(w)[None, :], 0, len(oenv) - 1)
        j = idx[np.arange(len(k)), np.argmax(oenv[idx], 1)]
        pt, pv = j * hs, oenv[j]
        keep = pv >= np.median(pv)
        if keep.sum() < 4:
            break
        sw = np.sqrt(pv[keep])
        A = np.stack([np.ones(keep.sum()), k[keep]], 1) * sw[:, None]
        (p0, p1), *_ = np.linalg.lstsq(A, pt[keep] * sw, rcond=None)
        if abs(p1 - T) > 0.005 * T:     # refinement should only nudge; keep the grid-search answer otherwise
            break
        T, ph = float(p1), float(p0) % float(p1)
        resid_ms = float(np.median(np.abs(pt[keep] - (p0 + p1 * k[keep]))) * 1000)
    for c in cands:
        c["period"] = round(c["period"], 6); c["phase"] = round(c["phase"], 4)
    return {"bpm": round(60.0 / T, 3), "period": round(T, 6), "phase": round(ph, 4),
            "confidence": pick["confidence"], "threshold": MIN_CONFIDENCE, "stable": pick["confidence"] >= MIN_CONFIDENCE,
            "librosa_bpm": round(est, 2), "octaves": cands, "fit_residual_ms": None if resid_ms is None else round(resid_ms, 1)}


# ---------------------------------------------------------------- stems
def load_mono(path, sr=SR):
    import librosa
    return librosa.load(path, sr=sr, mono=True)[0].astype(np.float32)


def window_slice(y, y_start, ws, we):
    """Samples of y (whose sample 0 is song time y_start) covering song time ws..we, zero-padded."""
    n = int(round((we - ws) * SR))
    out = np.zeros(n, np.float32)
    a = int(round((ws - y_start) * SR))
    src0, dst0 = max(a, 0), max(-a, 0)
    m = max(0, min(n - dst0, len(y) - src0))
    out[dst0:dst0 + m] = y[src0:src0 + m]
    return out


def separate(song, ws, we, cache, device):
    import librosa, soundfile as sf
    name = f"{os.path.splitext(os.path.basename(song))[0]}-{ws:g}-{we:g}"
    out = os.path.join(cache, "htdemucs", name)
    if all(os.path.exists(os.path.join(out, f"{s}.wav")) for s in STEMS):
        print(f"stems: cached {out}")
        return out
    if not shutil.which("uv"):
        sys.exit("--separate needs uv on PATH (it runs Demucs in its own environment)")
    os.makedirs(cache, exist_ok=True)
    src = os.path.join(cache, name + ".wav")
    y, _ = librosa.load(song, sr=SR, mono=False, offset=0.0)
    y = np.atleast_2d(y)
    sf.write(src, y[:, int(round(ws * SR)):int(round(we * SR))].T, SR, subtype="PCM_16")
    if device == "auto":
        device = "mps" if sys.platform == "darwin" and os.uname().machine == "arm64" else "cpu"
    cmd = ["uv", "run", "--python", "3.12", "--with", "demucs", "--with", "torch", "--with", "torchaudio",
           "--with", "soundfile", "python", "-m", "demucs", "-n", "htdemucs", "-d", device, "-o", cache, src]
    print("separating:", " ".join(cmd))
    subprocess.run(cmd, check=True)
    return out


def transcribe(vox, ws):
    import soundfile as sf
    if not shutil.which("uv"):
        sys.exit("--words needs uv on PATH (it runs faster-whisper in its own environment)")
    with tempfile.TemporaryDirectory() as d:
        wav, js = os.path.join(d, "vocals.wav"), os.path.join(d, "words.json")
        import librosa
        sf.write(wav, librosa.resample(vox, orig_sr=SR, target_sr=16000), 16000, subtype="PCM_16")
        subprocess.run(["uv", "run", "--python", "3.12", "--with", "faster-whisper", "python", "-c", WHISPER, wav, js],
                       check=True)
        words = json.load(open(js))
    return [{"w": w["w"], "s": round(w["s"] + ws, 3), "e": round(w["e"] + ws, 3)} for w in words]


# ---------------------------------------------------------------- measurements
def band_env(y, lo, hi, n_fft=1024, hop=HOP):
    import librosa
    S = np.abs(librosa.stft(y, n_fft=n_fft, hop_length=hop))
    f = librosa.fft_frequencies(sr=SR, n_fft=n_fft)
    return S[(f >= lo) & (f < hi)].sum(0)


def voice_flux(y, lo, hi, ws, downbeats, bar_len, ref=None):
    """Band-limited spectral flux, its song times, and a reference level: the 90th percentile of per-bar peaks
    (the voice's loud bars), so thresholds hold across songs and a bar where the voice is silent stays quiet.
    `ref` (from --grid-from) replaces the window's own: a one-bar window has no quiet bars to compare against."""
    e = band_env(y, lo, hi)
    t = ws + np.arange(len(e)) * HOP / SR
    flux = np.maximum(0, np.diff(e, prepend=e[0]))
    if ref is None:
        peaks = [flux[(t >= d) & (t < d + bar_len)].max() for d in downbeats if ((t >= d) & (t < d + bar_len)).any()]
        ref = (float(np.percentile(peaks, 90)) if peaks else float(flux.max())) + 1e-9
    return t, flux, ref


def onset_times(t, flux, ref, rel=0.25):
    import librosa
    pk = librosa.util.peak_pick(flux, pre_max=6, post_max=6, pre_avg=12, post_avg=12, delta=rel * ref, wait=18)
    return t[pk]


def first_entrance(r, loud, bpb, loud_db=None, quiet_db=None):
    """The stem's first loud beat in the window (within loud_db of its loud beats, the 95th percentile) counts as an
    entrance when the 2 bars before it average at least quiet_db under them and the stem stays present for the bar.
    A stem already loud at the window start has no entrance: a re-entry after a break can be syncopated (DemoIdent'
    bass comes back on beat 3 of bar 33), so only the first appearance votes. Returns (k, rise in dB) or None."""
    w, loud_db, quiet_db = 2 * bpb, loud_db or ENTER_LOUD_DB, quiet_db or ENTER_QUIET_DB
    k = next((i for i, x in enumerate(r) if x >= loud - loud_db), None)
    # Step back (under a bar) to where the stem became present: CMP's drums first peak on the clap (beat 3), 2 beats
    # after they enter at -12 dB.
    for _ in range(bpb - 1):
        if k and r[k - 1] >= loud - PRESENT_REL_DB:
            k -= 1
    if k is None or k < w:
        return None
    before = r[k - w:k].mean()
    if before <= loud - quiet_db and r[k:k + bpb].mean() >= loud - PRESENT_REL_DB:
        return k, float(r[k] - before)
    return None


def pick_downbeat(stem_y, beats, bpb, T, ws):
    """Bar phase from what the arrangement does: section changes and the first bass/drums entrance vote for their
    beat's phase. Low-band energy and the first vocal entrance are reported but do not vote (see the docstring)."""
    low = band_env(stem_y["bass"] + stem_y["drums"], 20, 150)
    lt = ws + np.arange(len(low)) * HOP / SR
    win = min(0.12, T / 2)
    per_beat = np.array([low[(lt >= b) & (lt < b + win)].mean() if ((lt >= b) & (lt < b + win)).any() else 0.0
                         for b in beats])
    lowband = [float(per_beat[p::bpb].mean()) if len(per_beat[p::bpb]) else 0.0 for p in range(bpb)]
    top = max(lowband) or 1.0
    lowband = [round(v / top, 2) for v in lowband]
    nb = len(beats)

    def beat_db(y):
        return np.array([db(np.sqrt(np.mean(y[int((b - ws) * SR):int((b - ws + T) * SR)] ** 2) + 1e-18)) for b in beats])
    mix_loud = np.percentile(beat_db(sum(stem_y.values())), 95)
    lev, loud = {}, {}
    for s in ("drums", "bass", "other", "vocals"):
        r = beat_db(stem_y[s])
        loud[s] = float(np.percentile(r, 95))
        # Floor: 40 dB under the stem's loud beats and 45 dB under the mix's, so separation bleed is not a change.
        lev[s] = np.maximum(r, max(loud[s] - 40, mix_loud - 45))
    # Section changes: 2 bars after vs 2 bars before (dB), summed over drums, bass and other. Two-bar windows hold a
    # whole cycle of a one- or two-bar groove, so a bass gap inside the groove cancels; one-bar windows voted it.
    w = 2 * bpb
    nov = np.zeros(nb)
    for s in ("drums", "bass", "other"):
        r = lev[s]
        for k in range(w, nb - w + 1):
            nov[k] += abs(r[k:k + w].mean() - r[k - w:k].mean())
    changes = [k for k in range(nb) if nov[k] > 0 and nov[k] >= max(0.5 * nov.max(), CHANGE_MIN_DB)
               and nov[k] == nov[max(0, k - bpb):k + bpb + 1].max()]
    votes = [0.0] * bpb
    cues = []
    for k in changes:
        votes[k % bpb] += float(nov[k])
        cues.append({"cue": "change", "beat": k, "phase": k % bpb, "db": round(float(nov[k]), 1)})
    # The first bass or drums entrance (the drop) votes with its rise in dB.
    ents = [(e[0], -e[1], s) for s in ("bass", "drums")
            if (e := first_entrance(lev[s], loud[s], bpb))]
    entrance = None
    if ents:
        k, neg_rise, s = min(ents)
        entrance = {"cue": f"{s} enters", "beat": k, "phase": k % bpb, "db": round(-neg_rise, 1)}
        votes[k % bpb] += -neg_rise
        cues.append(entrance)
    # Reported only: vocal phrases often start on a pickup (DemoIdent' first phrase starts on beat 3 of its bar).
    v = first_entrance(lev["vocals"], loud["vocals"], bpb, loud_db=10.0)   # a sung line sits further under its peaks
    vocals = {"beat": v[0], "phase": v[0] % bpb, "db": round(v[1], 1)} if v else None
    info = {"lowband_by_phase": lowband, "changes": [{"beat": c["beat"], "db": c["db"]} for c in cues if c["cue"] == "change"],
            "entrance": entrance, "vocals": vocals, "votes": [round(x, 1) for x in votes], "cues": cues}
    total = sum(votes)
    if total > 0:
        p = int(np.argmax(votes))
        info.update(beat=p, share=round(votes[p] / total, 2), unanimous=all(c["phase"] == p for c in cues),
                    source="; ".join(filter(None, [
                        "changes at beats " + ", ".join(str(c["beat"]) for c in cues if c["cue"] == "change") if changes else "",
                        f"{entrance['cue']} at beat {entrance['beat']}" if entrance else ""])))
    else:
        p = int(np.argmax(lowband))
        info.update(beat=p, share=None, unanimous=False,
                    source="low-band energy (no section change or entrance in the window: wrong on both test songs)")
    return info


def downbeat_report(down, bpb):
    """Lines to print when the cues do not all agree: per-phase votes, every cue, and the check to make."""
    p = down["beat"]
    L = [f"  votes by phase {down['votes']} (phase {p}: {down['share'] * 100:.0f} %)" if down.get("share") is not None
         else "  no voting cue in the window"]
    for c in down["cues"]:
        L.append(f"  {c['cue']} at beat {c['beat']} ({c['db']} dB) -> phase {c['phase']}"
                 + ("" if c["phase"] == p else "   <- disagrees"))
    lb = int(np.argmax(down["lowband_by_phase"]))
    L.append(f"  low-band energy (not voting) peaks on phase {lb}{'' if lb == p else '   <- disagrees'}")
    if down.get("vocals"):
        v = down["vocals"]
        L.append(f"  vocals first enter at beat {v['beat']} (phase {v['phase']}; not voting: phrases start on pickups)")
    if down.get("share") is not None and down["share"] < 2 / 3:
        L.append("  weak: the pick has under 2/3 of the votes")
    L.append("  check in MAP.md: the bar where bass or drums first enter must show their first X on step 0 of its groove "
             "string; a first X on step 4k means the downbeat is k beats later. --downbeat K settles it.")
    return L


def envelope(y, frames_song_t, ws, we, release_s, fps, win=0.025, ref=None):
    """Per-frame RMS (+-win) normalised to its 99th percentile (or `ref`), instant attack, one-pole release.
    Returns (values, the reference used)."""
    c = np.concatenate([[0.0], np.cumsum(y.astype(np.float64) ** 2)])
    out = np.zeros(len(frames_song_t))
    inside = (frames_song_t >= ws) & (frames_song_t <= we)
    s = frames_song_t[inside] - ws
    a = np.clip(((s - win) * SR).astype(int), 0, len(y))
    b = np.clip(((s + win) * SR).astype(int), 0, len(y))
    out[inside] = np.sqrt((c[b] - c[a]) / np.maximum(b - a, 1))
    if ref is None:
        ref = float(np.percentile(out[out > 0], 99)) if (out > 0).any() else 1.0
    out = np.clip(out / (ref or 1.0), 0, 1.2)
    rel = max(1.0, release_s * fps)
    sm, v = np.zeros_like(out), 0.0
    for i, x in enumerate(out):
        v = x if x > v else v + (x - v) / rel
        sm[i] = v
    return np.round(sm, 3).tolist(), ref


def groove(fluxes, T, downbeats, bpb, we):
    """16th-step strings per bar and voice (X > 0.56 x ref, x > 0.25 x ref, as the run's grid16 read), plus the
    strong steps' song times. Steps at or past the window end (a partial last bar) read '-'."""
    rows, hits = {}, {}
    for voice in VOICES:
        t, flux, ref = fluxes[voice]
        vals = []
        for d in downbeats:
            v = []
            for s in range(bpb * 4):
                c = d + s * T / 4
                m = (t >= c - 0.03) & (t < c + 0.04)
                v.append(None if c >= we else float(flux[m].max()) if m.any() else 0.0)
            vals.append(v)
        rows[voice] = ["".join("-" if v is None else "X" if v > 0.56 * ref else "x" if v > 0.25 * ref else "." for v in r)
                       for r in vals]
        hits[voice] = [round(d + s * T / 4, 4) for d, r in zip(downbeats, rows[voice]) for s, ch in enumerate(r) if ch == "X"]
    return rows, hits


def sections_from(bars):
    runs = []
    for b in bars:
        if runs and runs[-1]["stems"] == b["present"]:
            runs[-1]["bars"][1] = b["n"]; runs[-1]["end"] = b["end"]
        else:
            runs.append({"bars": [b["n"], b["n"]], "start": b["start"], "end": b["end"], "stems": b["present"]})
        if b.get("partial"):
            runs[-1]["partial"] = True    # ends in the window's incomplete last bar
    seen_full, count, prev = False, {}, None
    for r in runs:
        full = "drums" in r["stems"] and "bass" in r["stems"]
        name = "hook" if full else ("break" if seen_full else "intro")
        seen_full |= full
        count[name] = count.get(name, 0) + 1
        r["name"] = name if count[name] == 1 else f"{name} {count[name]}"
        if prev is None:
            r["change"] = ", ".join(r["stems"]) or "no stems"
        else:
            add = [f"+{s}" for s in r["stems"] if s not in prev]
            rem = [f"-{s}" for s in prev if s not in r["stems"]]
            r["change"] = ", ".join(add + rem)
        prev = r["stems"]
    return runs


def load_grid(path):
    """The grid of an earlier map (--grid-from): period, first beat and downbeat in song time, beats per bar,
    and the loudness references. Exits 1 with the reason when the file cannot serve as a grid."""
    hint = "map the song once first: track_map.py SONG --window 0:60 --out beats/map.json"
    try:
        g = json.load(open(path))
    except FileNotFoundError:
        sys.exit(f"--grid-from {path}: no such file ({hint})")
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        sys.exit(f"--grid-from {path}: not JSON ({e}); {hint}")
    if not isinstance(g, dict):
        sys.exit(f"--grid-from {path}: not a track_map.py map (a JSON object with period, beat0, downbeat)")
    if g.get("stable") is False:
        sys.exit(f"--grid-from {path}: that map found no stable tempo, so it has no grid")
    missing = [k for k in ("period", "beat0", "offset", "beatsPerBar", "downbeat") if k not in g]
    if g.get("tool") != "track_map" or missing:
        sys.exit(f"--grid-from {path}: not a track_map.py map" + (f" (missing {', '.join(missing)})" if missing else ""))
    try:
        T, b0, off, bpb = float(g["period"]), float(g["beat0"]), float(g["offset"]), int(g["beatsPerBar"])
        dphase = int(g["downbeat"]["beat"])
    except (TypeError, ValueError, KeyError) as e:
        sys.exit(f"--grid-from {path}: unreadable grid field ({e!r})")
    if not (0.15 < T < 2.0 and bpb > 0):
        sys.exit(f"--grid-from {path}: period {T} s / {bpb} beats per bar is not a tempo grid")
    b0_song = b0 - off     # the map's first beat in song time
    return {"path": path, "song": g.get("song"), "period": T, "beat0": b0_song, "beatsPerBar": bpb,
            "downbeat": b0_song + dphase * T, "tempo": g.get("tempo") or {}, "refs": g.get("refs"),
            "stems": g.get("stems") or {}, "window": g.get("window")}


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("song")
    ap.add_argument("--out", required=True, help="map JSON")
    ap.add_argument("--md", help="human-readable map (Markdown)")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--stems", help="folder with drums/bass/vocals/other.wav")
    g.add_argument("--separate", action="store_true", help="run Demucs htdemucs on the window (cached)")
    ap.add_argument("--stems-start", type=float, help="song time of the stems' sample 0 (default: window start)")
    ap.add_argument("--device", default="auto", help="Demucs device: auto, mps, cpu or cuda")
    ap.add_argument("--words", action="store_true", help="faster-whisper word anchors on the vocal stem")
    ap.add_argument("--fps", type=float, default=60)
    ap.add_argument("--offset", type=float, default=0.0, help="edit time = song time + offset")
    ap.add_argument("--duration", type=float, help="edit length for per-frame data (default: window end + offset)")
    ap.add_argument("--window", default="0:", help="START:END song seconds (default: whole song)")
    ap.add_argument("--beats-per-bar", type=int, default=4)
    ap.add_argument("--downbeat", type=int, help="beat index (0-based) that is a downbeat")
    ap.add_argument("--bpm-hint", type=float)
    ap.add_argument("--grid-from", help="reuse the tempo grid, downbeat and loudness references of an earlier map")
    ap.add_argument("--peaks", type=int, default=3000, help="waveform min/max pairs over the window")
    a = ap.parse_args()

    grid = load_grid(a.grid_from) if a.grid_from else None
    if grid and a.bpm_hint:
        sys.exit("--grid-from and --bpm-hint: pick one (the grid map already fixes the tempo)")
    import librosa
    mix_full = load_mono(a.song)
    song_dur = len(mix_full) / SR
    ws, we = parse_window(a.window, song_dur)
    mix = window_slice(mix_full, 0.0, ws, we)
    off, fps, bpb = a.offset, a.fps, a.beats_per_bar

    if grid:
        if grid["song"] and os.path.basename(grid["song"]) != os.path.basename(a.song):
            print(f"warning: --grid-from {a.grid_from} maps {os.path.basename(grid['song'])}, not "
                  f"{os.path.basename(a.song)}; the grid only fits the same recording")
        T, bpb = grid["period"], grid["beatsPerBar"]
        # first grid beat in the window; a beat up to GRID_SNAP_S before the start counts (a window typed as 12.033
        # for a downbeat at 12.0328 keeps that bar)
        beat0 = float(grid["beat0"] + np.ceil((ws - GRID_SNAP_S - grid["beat0"]) / T) * T)
        if beat0 >= we:
            sys.exit(f"--window {a.window}: no beat of the --grid-from grid falls inside it")
        tempo = {**grid["tempo"], "bpm": round(60.0 / T, 3), "period": T, "phase": round(beat0 - ws, 4),
                 "source": f"--grid-from {a.grid_from}", "grid_window": grid["window"]}
        print(f"tempo {tempo['bpm']} BPM, period {T} s, first beat {beat0:.3f} s (song): from {a.grid_from} "
              f"(window {grid['window']}), not refitted")
    else:
        tempo = fit_tempo(mix, a.bpm_hint)
        print(f"tempo {tempo['bpm']} BPM, period {tempo['period']} s, first beat {ws + tempo['phase']:.3f} s (song), "
              f"confidence {tempo['confidence']} (threshold {MIN_CONFIDENCE}), fit residual {tempo['fit_residual_ms']} ms")
        print("  octaves: " + "; ".join(f"{c['bpm']} BPM score {c['score']} conf {c['confidence']} prior {c['prior']}"
                                        for c in tempo["octaves"]))
        if not tempo["stable"]:
            json.dump({"song": a.song, "window": [ws, we], "tempo": tempo, "stable": False}, open(a.out, "w"), indent=1)
            print(f"no stable tempo: confidence {tempo['confidence']} < {MIN_CONFIDENCE}; nothing mapped ({a.out})")
            sys.exit(1)
        T, beat0 = tempo["period"], ws + tempo["phase"]
        if we - ws < 10:
            print(f"warning: a {we - ws:.1f} s window fits its tempo on {int((we - ws) / T)} beats and its first beat may "
                  f"not be the song's; map the song once and pass --grid-from (DemoIdent 3.4 s: 140.018 -> 139.655 BPM)")

    # Stems (window-aligned mono), or proxies from the mix. With --grid-from and no stem option, the grid map's
    # stems are reused when they cover this window (a Demucs run on a 3 s window is worse and slower).
    stem_dir, stems_start = (separate(a.song, ws, we, os.path.join(os.path.dirname(os.path.abspath(a.out)), "stems"),
                                      a.device) if a.separate else a.stems), a.stems_start
    if grid and not stem_dir and grid["stems"].get("dir") and not grid["stems"].get("proxies"):
        gs = grid["stems"]
        if os.path.exists(os.path.join(gs["dir"], "drums.wav")):
            stem_dir, stems_start = gs["dir"], gs.get("start", 0.0)
            print(f"stems: reusing the --grid-from map's stems ({stem_dir})")
        else:
            print(f"warning: the --grid-from map's stems ({gs['dir']}) are gone; pass --stems or --separate, or the "
                  f"groove is read from proxies against no matching references")
    if stem_dir:
        missing = [s for s in STEMS if not os.path.exists(os.path.join(stem_dir, f"{s}.wav"))]
        if missing:
            sys.exit(f"{stem_dir}: missing {', '.join(m + '.wav' for m in missing)}")
        s0 = ws if stems_start is None else stems_start
        stem_y = {s: window_slice(load_mono(os.path.join(stem_dir, f"{s}.wav")), s0, ws, we) for s in STEMS}
        resid = db(np.sqrt(np.mean((mix - sum(stem_y.values())) ** 2)) / (np.sqrt(np.mean(mix ** 2)) + 1e-12))
        stems_info = {"dir": os.path.abspath(stem_dir), "start": s0, "residual_db": round(resid, 1), "proxies": False}
        print(f"stems: {stem_dir} (sample 0 = song {s0:g} s); sum-vs-mix residual {resid:.1f} dB")
        if resid > -10:
            print("warning: the stems do not sum back to the mix; check --stems-start or the stem folder")
    else:
        from scipy.signal import butter, sosfilt
        harm, perc = librosa.effects.hpss(mix)
        stem_y = {"drums": perc, "bass": sosfilt(butter(4, 150, "low", fs=SR, output="sos"), mix).astype(np.float32),
                  "vocals": sosfilt(butter(2, [300, 3400], "band", fs=SR, output="sos"), harm).astype(np.float32),
                  "other": harm}
        stems_info = {"dir": None, "proxies": True,
                      "note": "no stems: bass = mix <150 Hz, drums = HPSS percussive, vox = harmonic 300-3400 Hz, "
                              "mel = harmonic; sections omitted"}
        print("stems: none (proxies from the mix; use --stems or --separate for sections)")

    # Beat grid and downbeat.
    nb = int(np.floor((we - beat0) / T)) + 1
    beats_song = beat0 + np.arange(nb) * T
    beats_song = beats_song[beats_song < we]
    if grid:
        # the window's first beat that is a downbeat of the grid map
        k0 = int(round((beats_song[0] - grid["downbeat"]) / T))
        down = {"beat": (-k0) % bpb, "source": f"--grid-from {a.grid_from} (downbeat at song {grid['downbeat']:.3f} s)",
                "lowband_by_phase": None, "unanimous": True}
    else:
        down = pick_downbeat(stem_y, beats_song, bpb, T, ws)
    guess = down["beat"]
    if a.downbeat is not None:
        down.update(beat=a.downbeat % bpb, source="--downbeat")
    dphase = down["beat"]
    downbeats = beats_song[dphase::bpb]
    print(f"downbeat: beat {dphase} ({down['source']})" + (f"; votes by phase {down['votes']}" if down.get("votes") else ""))
    if guess != dphase:
        print(f"  note: the automatic guess was beat {guess}")
    elif not down.get("unanimous"):
        print("  note: the downbeat cues do not all agree")
        print("\n".join(downbeat_report(down, bpb)))
    bar_len = bpb * T
    bar_no = (lambda d: int(round((d - grid["downbeat"]) / bar_len)) + 1) if grid else None

    # Per-bar RMS, presence, groove, sections. Complete bars, plus the last bar when the window ends inside it
    # (flagged partial; its steps past the window end read '-'). Loudness references (presence, groove, features,
    # bands) come from the --grid-from map when it has them, else from this window's complete bars.
    full = [d for d in downbeats if d + bar_len <= we + 1e-6]
    part = [d for d in downbeats if d + bar_len > we + 1e-6 and (we - d) / T >= MIN_PARTIAL_BEATS]
    mapped = full + part
    gref = grid["refs"] if grid and grid["refs"] and grid["refs"].get("proxies") == stems_info["proxies"] else None
    if grid and not gref:
        print("  note: the --grid-from map has no matching loudness references; groove and presence are read "
              "against this window's own loud bars")
    refs = {"proxies": stems_info["proxies"], "source": gref.get("source") if gref else f"window {ws:g}:{we:g}"}
    fluxes = {v: voice_flux(stem_y[stem], lo, hi, ws, full or mapped, bar_len, gref["groove"][v] if gref else None)
              for v, (stem, lo, hi) in {**VOICES, "mel": ("other", 200, 5000)}.items()}
    refs["groove"] = {v: fluxes[v][2] for v in fluxes}
    rms = {k: [] for k in ("mix",) + STEMS}
    for d in mapped:
        i0, i1 = max(0, int((d - ws) * SR)), min(len(mix), int((d - ws + bar_len) * SR))
        rms["mix"].append(db(np.sqrt(np.mean(mix[i0:i1] ** 2))))
        for s in STEMS:
            rms[s].append(db(np.sqrt(np.mean(stem_y[s][i0:i1] ** 2))))
    nfull = len(full) or len(mapped)
    if gref:
        refs["rms_db"] = gref["rms_db"]
    else:
        refs["rms_db"] = {k: round(float(np.percentile(rms[k][:nfull], 95)), 2) if mapped else 0.0 for k in rms}
    rows, hits = groove(fluxes, T, mapped, bpb, we)
    bars = []
    for i, d in enumerate(mapped):
        present = [s for s in STEMS if not stems_info["proxies"]
                   and rms[s][i] >= max(refs["rms_db"][s] - PRESENT_REL_DB, refs["rms_db"]["mix"] - PRESENT_MIX_DB)]
        b = {"n": bar_no(d) if bar_no else i + 1, "start": round(float(d), 4), "end": round(float(min(d + bar_len, we)), 4),
             "T": round(float(d + off), 4), "rms_db": {k: round(rms[k][i], 1) for k in rms},
             "present": present, "groove": {v: rows[v][i] for v in VOICES}}
        if d in part:
            b.update(partial=True, beats=round(float((we - d) / T), 2))
            print(f"  bar {b['n']} is partial: {b['beats']} of {bpb} beats before the window end (song {we:g} s)")
        bars.append(b)
    sections = [] if stems_info["proxies"] else sections_from(bars)
    for s in sections:
        print(f"  {s['name']}: bars {s['bars'][0]}-{s['bars'][1]}{' (last bar partial)' if s.get('partial') else ''} "
              f"({s['change']})  song {s['start']:.2f}-{s['end']:.2f} s  T {s['start'] + off:.2f}-{s['end'] + off:.2f}")

    words = transcribe(stem_y["vocals"], ws) if a.words else None
    if words is not None:
        print(f"words: {len(words)} anchors from the {'vocal stem' if not stems_info['proxies'] else 'vocal proxy'}")

    # Per-frame data in edit time.
    dur = a.duration if a.duration else we + off
    nF = int(round(dur * fps))
    song_t = np.arange(nF) / fps - off
    # Release times are the run's 9/6/12/14 frames at 60 fps, kept in seconds so other frame rates match.
    feats, refs["features"] = {}, {}
    for k, y, rel in (("mix", mix, 9), ("bass", stem_y["bass"], 9), ("drums", stem_y["drums"], 6),
                      ("vox", stem_y["vocals"], 12), ("mel", stem_y["other"], 14)):
        feats[k], refs["features"][k] = envelope(y, song_t, ws, we, rel / 60, fps, ref=gref["features"][k] if gref else None)
    S = np.abs(librosa.stft(mix, n_fft=4096, hop_length=512))
    freqs = librosa.fft_frequencies(sr=SR, n_fft=4096)
    edges = np.geomspace(40, 16000, 33)
    sel = [(freqs >= lo) & (freqs < hi) for lo, hi in zip(edges[:-1], edges[1:])]
    B = np.stack([S[m].mean(0) if m.any() else S[int(np.argmin(np.abs(freqs - lo)))] for m, lo in zip(sel, edges)])
    refs["bandsMax"] = gref["bandsMax"] if gref else float(np.max(B))
    Bn = np.clip((librosa.amplitude_to_db(B + 1e-9, ref=refs["bandsMax"]) + 60) / 60, 0, 1)
    bands = np.zeros((nF, 32))
    inside = (song_t >= ws) & (song_t <= we)
    bands[inside] = Bn[:, np.minimum(Bn.shape[1] - 1, ((song_t[inside] - ws) * SR / 512).astype(int))].T
    ev = {v: [round(float(t + off), 3) for t in onset_times(*fluxes[v]) if ws <= t <= we] for v in fluxes}
    ev["words"] = [{"t": round(w["s"] + off, 3), "e": round(w["e"] + off, 3)} for w in words] if words else []
    ev["grid"] = {v: [round(t + off, 4) for t in hits[v]] for v in VOICES}
    cuts = np.linspace(0, len(mix), min(a.peaks, len(mix)) + 1).astype(int)
    peaks = [[round(float(mix[i:j].min()), 3), round(float(mix[i:j].max()), 3)] for i, j in zip(cuts[:-1], cuts[1:])]

    # The grid continues past the window to the end of the edit (an echo tail or a lockup still sits on it).
    ks = [k for k in range(int((dur - off - beat0) / T) + 1) if 0 <= beat0 + k * T + off <= dur]
    beats_edit = [round(float(beat0 + k * T + off), 4) for k in ks]
    res = {"tool": "track_map", "song": a.song, "window": [ws, we], "fps": fps, "preroll": off, "offset": off,
           "songStop": we, "duration": dur, "bpm": tempo["bpm"], "period": T, "beat0": round(beat0 + off, 4),
           "beatsPerBar": bpb, "downbeat": down, "beatOrigin": round(grid["beat0"] if grid else beat0, 4),
           "bars": [b for k, b in zip(ks, beats_edit) if (k - dphase) % bpb == 0],
           "beats": beats_edit, "tempo": tempo, "stems": stems_info, "features": feats,
           "bands": (bands * 99).astype(int).tolist(), "events": ev,
           "wave": {"start": round(ws + off, 4), "dur": round(we - ws, 4), "peaks": peaks},
           "barMap": bars, "sections": sections, "words": words, "refs": refs,
           "wordsNote": "ASR word times on the vocal stem: timing anchors only, never on-screen lyrics" if words else None}
    json.dump(res, open(a.out, "w"), separators=(",", ":"))
    print(f"wrote {a.out}: {len(beats_edit)} beats, {len(res['bars'])} bars, {nF} frames at {fps:g} fps, "
          + ", ".join(f"{k} {len(v)}" for k, v in ev.items() if k != "grid"))
    if a.md:
        write_md(a.md, res, off)
        print(f"wrote {a.md}")


def write_md(path, r, off):
    t, d = r["tempo"], r["downbeat"]
    fit = (f"confidence {t.get('confidence')} (stable at >= {t.get('threshold')}), fit residual {t.get('fit_residual_ms')} ms"
           if "confidence" in t else "")
    L = [f"# Track map: {os.path.basename(r['song'])}", "",
         f"- Window: song {r['window'][0]:.3f}-{r['window'][1]:.3f} s; edit time T = song time + {off:g} s; "
         f"the waveform's peaks[0] plays at T {r['wave']['start']:.3f} (`wave.start`).",
         f"- Tempo: {t['bpm']} BPM (period {t['period']} s), first beat song {r['beat0'] - off:.3f} s (T {r['beat0']:.3f})"
         + (f"; from {t['source']}, not refitted" if t.get("source") else "") + (f"; {fit}" if fit else "") + ".",
         "- Octaves searched: " + "; ".join(f"{c['bpm']} BPM (score {c['score']}, prior {c['prior']})"
                                           for c in t.get("octaves", [])) + "." if t.get("octaves") else None,
         f"- Bars: {r['beatsPerBar']} beats; downbeat = beat {d['beat']} ({d['source']})"
         + (f"; votes by phase {d['votes']}" if d.get("votes") else "")
         + (f"; low-band energy by phase {d['lowband_by_phase']} (not voting)" if d.get("lowband_by_phase") else "") + ".",
         "- Stems: " + (f"`{r['stems']['dir']}`, sum-vs-mix residual {r['stems']['residual_db']} dB." if not r["stems"]["proxies"]
                        else r["stems"]["note"] + "."),
         f"- Loudness references (presence, groove, features, bands): {r['refs']['source']}.", ""]
    L = [x for x in L if x is not None]
    if d.get("cues") and not d.get("unanimous"):
        L += ["## Downbeat cues (they disagree)", ""]
        L += [f"- {c['cue']} at beat {c['beat']} ({c['db']} dB): phase {c['phase']}" for c in d["cues"]]
        if d.get("vocals"):
            L.append(f"- vocals first enter at beat {d['vocals']['beat']}: phase {d['vocals']['phase']} (not voting)")
        L += ["", "Check: the bar where bass or drums first enter must show their first X on step 0 of its groove string; a "
              "first X on step 4k means the downbeat is k beats later. Settle it with --downbeat K.", ""]
    if r["sections"]:
        L += ["## Sections", ""]
        L += [f"- {s['name']}: bars {s['bars'][0]}-{s['bars'][1]}{' (last bar partial)' if s.get('partial') else ''} "
              f"({s['change']}), song {s['start']:.2f}-{s['end']:.2f} s, "
              f"T {s['start'] + off:.2f}-{s['end'] + off:.2f}" for s in r["sections"]]
        L += ["", "Names are guesses from stem presence; the +/- changes are measured.", ""]
    L += ["## Bars", "", "RMS in dBFS; groove in 16ths (X strong, x weak, - past the window end).", "",
          "| bar | song s | T | mix | drums | bass | vocals | other | bass | kick | clap | hat |",
          "|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|---|"]
    for b in r["barMap"]:
        rd, gr = b["rms_db"], b["groove"]
        n = f"{b['n']} (partial, {b['beats']} beats)" if b.get("partial") else b["n"]
        L.append(f"| {n} | {b['start']:.3f} | {b['T']:.3f} | {rd['mix']} | {rd['drums']} | {rd['bass']} | {rd['vocals']} | "
                 f"{rd['other']} | `{gr['bass']}` | `{gr['kick']}` | `{gr['clap']}` | `{gr['hat']}` |")
    if r["words"]:
        L += ["", "## Lyric anchors", "", "ASR on the vocal stem: use for timing only, never as on-screen lyrics.", ""]
        L += [f"- song {w['s']:.2f} s (beat {(w['s'] - r['beatOrigin']) / r['period']:.2f}, T {w['s'] + off:.2f}): {w['w']}"
              for w in r["words"]]
    open(path, "w").write("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
