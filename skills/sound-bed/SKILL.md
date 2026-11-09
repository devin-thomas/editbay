---
name: sound-bed
description: "Sound for an edit: a music bed at an exact tempo (generated with its beat grid, or a supplied track measured for one), a small palette of synthesised SFX placed on the beat sheet's cues, music ducked under the voice, and a mix normalised to the delivery target with true-peak headroom. Use when a video needs music, sound effects, sound design, ducking, a mix, or loudness to spec (-14 LUFS for reels and shorts, -16 for narrated explainers); before motion-build renders its review cut."
---

# Sound bed

Sound is half of what reads as "editing". The bed sets pace, SFX punctuate what the eye sees, the voice always wins,
and the file that ships is measured, not assumed.

Paths: `$EB` is the editbay root, the folder holding `skills/` and `tools/` (`../..` from this skill's folder). Tools run as `uv run $EB/tools/<tool>.py`.
Loudness targets come from the delivery profile in config; music policy from the brand (`audio.music_policy`).

## 1. Choose the music

In order of preference, subject to the brand's music policy: the creator's own music; a generated bed from
`beat_bed.py` (original, deterministic, exact grid); CC0 or CC BY tracks with credit written into the delivery
notes. Generated-by-API music (Suno through kie.ai, ElevenLabs Music) is a paid, opt-in route: estimate the cost in
`HUMAN_QUEUE.md` first.

```bash
uv run $EB/tools/beat_bed.py --bpm 104 --sections intro:2,build:2,main:8,outro:2 --style pulse --out sound/bed --end-hit
```

A supplied track gets a grid by measurement: `beat_grid.py detect track.wav --json sound/track.grid.json`, then check
the tempo by ear (detectors halve or double it; measured beats lag true onsets by about 35 ms).

**Done when:** `sound/*.wav` plus a grid JSON exist, and the music's licence is written down.

## 2. Build the SFX palette

`uv run $EB/tools/sfx_synth.py --out sound/sfx --preview` makes a deterministic palette (whoosh, click, tick, pop,
impact, riser, shimmer, glitch, type, ding, swell). Listen to `_preview.wav`, then put an `sfx` name on the cues that
earn one: entrances get a whoosh or click, a lock-up gets an impact, a list item gets a tick, a reveal gets a shimmer.
One sound per idea. Placement rules and levels: [references/mix-rules.md](references/mix-rules.md).

**Done when:** every `sfx` in the beat sheet names a file in `sound/sfx/`.

## 3. Mix

```bash
uv run $EB/tools/mix.py --out sound/mix.wav --duration DUR --voice narration/narration.wav \
  --music sound/bed.wav --music-gain -8 --duck 14 --sfx beats/beats.resolved.json --sfx-dir sound/sfx \
  --target -16 --tp -1.5
```

The music ducks 14 dB under speech (60 ms attack, 350 ms release), SFX land 50 ms ahead of their cue, and the master
is normalised two-pass to the target with a true-peak ceiling. Stems land beside the mix.

**Done when:** `mix.wav` measures within 1 LU of the target with true peak under the ceiling, and the bed sits at
least 18 LU under the voice at sentence starts (listen to three).

## 4. Hand to the build

The composition plays `sound/mix.wav` as its only audio. HyperFrames changes the rendered audio level (by -1.4 to
-1.8 dB in our measurements, sometimes not at all), so put the mastered mix back after each render, whatever the target:
`uv run $EB/tools/remux_audio.py renders/review.mp4 sound/mix.wav --out renders/final.mp4 --target -14 --tp -1.0`
(the video is copied; AAC true-peak overshoot is trimmed). Render-verify then measures the delivered file.

**Done when:** the mix path is in the brief, the build uses it, and the delivered file measures on target.

## Checklist

- [ ] Music source allowed by the brand; licence recorded; grid exists
- [ ] SFX palette previewed; one sound per idea on the cues
- [ ] Voice on top: ducking on, bed well under sentence starts
- [ ] Mix at target and ceiling; delivered file measured again
