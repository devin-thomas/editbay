# /// script
# dependencies = ["numpy", "scipy", "soundfile", "librosa"]
# ///
"""The trailer's music track (48 kHz stereo): the song from the in-app tap, stopped on the in-app pause, with a
tempo-synced echo throw of the last word and a darkening reverb tail as the fade-out."""
import numpy as np, soundfile as sf, librosa
from scipy.signal import butter, sosfilt, fftconvolve
SR = 48000; PREROLL = 1.442; STOP = 31.313; D = 0.48005; DUR = 39.5
y, _ = librosa.load("source/changed-my-phone-remix.mp3", sr=SR, mono=False)   # (2, n)
y *= 10 ** (-1.5 / 20)   # the MP3 decodes up to 0.81 dB over full scale; leave headroom (mix.py sets the level)
out = np.zeros((2, int(DUR * SR)))
n = int(STOP * SR); a = int(PREROLL * SR)
dry = y[:, :n].copy()
dry[:, -int(0.008 * SR):] *= np.linspace(1, 0, int(0.008 * SR))                 # clean stop, no click
out[:, a:a + n] += dry
# echo throw: the last half beat before the pause, repeating on quarter notes, each darker and softer
send = y[:, n - int(0.50 * SR): n].copy()
ramp = int(0.03 * SR); send[:, :ramp] *= np.linspace(0, 1, ramp); send[:, -int(0.01 * SR):] *= np.linspace(1, 0, int(0.01 * SR))
bus = np.zeros_like(out)
for k in range(1, 9):
    g = 0.92 * (0.63 ** (k - 1))
    sos = butter(2, max(700, 5200 / (1 + 0.55 * k)), 'low', fs=SR, output='sos')
    hp = butter(1, 180, 'high', fs=SR, output='sos')
    e = sosfilt(hp, sosfilt(sos, send, axis=1), axis=1) * g
    pan = 0.35 if k % 2 else -0.35
    e[0] *= 1 - pan; e[1] *= 1 + pan
    s0 = a + n + int((k - 1) * D * SR) + int(D * SR) - send.shape[1]
    s0 = a + n - send.shape[1] + int(k * D * SR)
    bus[:, s0:s0 + e.shape[1]] += e[:, : max(0, min(e.shape[1], out.shape[1] - s0))]
# reverb: exponentially decaying stereo noise, low-passed (RT60 ~2.6 s)
rng = np.random.default_rng(3); L = int(2.8 * SR); t = np.arange(L) / SR
ir = rng.standard_normal((2, L)) * np.exp(-6.9 * t / 2.6)
ir = sosfilt(butter(2, 3800, 'low', fs=SR, output='sos'), ir, axis=1); ir /= np.abs(ir).sum(1, keepdims=True) ** 0.5 * 30
tail_in = bus + np.pad(out[:, : a + n], ((0, 0), (0, out.shape[1] - (a + n)))) * 0
last = np.zeros_like(out); last[:, a + n - int(0.6 * SR): a + n] = out[:, a + n - int(0.6 * SR): a + n]
wet = np.stack([fftconvolve(bus[c] + 0.35 * last[c], ir[c])[: out.shape[1]] for c in range(2)])
out += bus + 0.55 * wet
sf.write("sound/music.wav", out.T.astype(np.float32), SR, subtype="PCM_24")
print("music.wav", out.shape[1] / SR, "s; stop at T", round(PREROLL + STOP, 3), "; echoes at", [round(PREROLL + STOP + k * D, 3) for k in range(1, 6)])
