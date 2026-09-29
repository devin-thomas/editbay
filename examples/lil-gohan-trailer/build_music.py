# /// script
# dependencies = ["numpy", "soundfile", "librosa"]
# ///
"""The trailer's music track (48 kHz stereo): the song from the in-app tap, faded to silence on the in-app pause.
Nothing is added to the song: silence before its first note, and a plain linear fade (no echo, no reverb) from the
end of "had to change my phone." (song 30.04 s) to zero at the pause (song 31.313 s). Owner's call 2026-09-29: sounds
before the first note and an echo he did not put in the song are not his music. (The echo-throw version is
build_music.echo.py.)"""
import numpy as np, soundfile as sf, librosa
SR = 48000; PREROLL = 1.442; FADE0 = 30.04; STOP = 31.313; DUR = 39.5
y, _ = librosa.load("source/changed-my-phone-remix.mp3", sr=SR, mono=False)   # (2, n)
y *= 10 ** (-1.5 / 20)   # the MP3 decodes up to 0.81 dB over full scale; leave headroom (mix.py sets the level)
out = np.zeros((2, int(DUR * SR)))
n0, n1, a = int(FADE0 * SR), int(STOP * SR), int(PREROLL * SR)
song = y[:, :n1].copy()
song[:, n0:n1] *= np.linspace(1.0, 0.0, n1 - n0)                                # plain linear fade to zero
out[:, a:a + n1] = song
sf.write("sound/music.wav", out.T.astype(np.float32), SR, subtype="PCM_24")
print(f"music.wav {DUR} s; song from T {PREROLL}; fade T {PREROLL + FADE0:.3f} -> {PREROLL + STOP:.3f} (zero at the pause)")
