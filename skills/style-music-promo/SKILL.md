---
name: style-music-promo
description: Music-led promo pieces cut to a supplied song, in six formats (trailer, sizzle reel, intro/opener, outro, interstitial, ident), in 16:9 and 9:16. Maps the track first (tempo, bars, sections from stems, groove, lyric anchors), gives each section a role (motif, drop, flurry, resolve), drives pulses and visuals from the song's own analysis, turns the brand mark into a 3D liquid-glass motif, ends on an event with a tempo-synced echo tail, and locks every cut to the grid. Use when asked for an app or product trailer on a song, a sizzle or hype reel, a channel intro or outro, a stinger, bumper, interstitial, ident, logo sting, "coming soon" teaser, or any piece where a specific song drives the edit.
---

# Style: music promo

The song is the script. Map it before anything else, plan on bars, and let every visual event land on something the
viewer hears: a downbeat, a clap, an 808, a lyric, the stop. Measured and built on the Demo Artist app trailer
(2026-09-29, 125 BPM, 39.5 s, 16:9 + 9:16); worked example: [references/example-music-promo.md](references/example-music-promo.md).

Paths: `$EB` is the editbay root, the folder holding `skills/` and `tools/` (`../..` from this skill's folder). Tools run as
`uv run $EB/tools/<tool>.py`. Reusable HyperFrames building blocks: [assets/kit/](assets/kit/).

## Grammar

1. **Map first.** `track_map.py` gives BPM and beat phase, bar downbeats, sections by which stems play, the groove
   (808/kick, clap, hats per 16th) and lyric anchors. Plan in bars; convert to seconds last.
2. **The song starts the piece, and nothing sounds before it.** At most 1.5 s of pre-roll, in digital silence: no
   swell, riser, click or tone before the song's first note (a sound there is heard as the song's first note: the
   Demo Artist owner rejected a -24 dB swell and a tap click, 2026-09-29); the only alternative is a non-tonal cold-open
   sound the artist asks for (e.g. an analog TV power-on without its whine). If the product plays music, the song
   starts from a real action in it (tap to play) and ends on one (pause): the edit is bookended by the product.
3. **Sections have roles.** Intro phrase: the motif and one hero idea, one change per bar or one continuous 3D shot.
   Drop: the product at full energy, cuts on downbeats and claps. The last bar before the resolve: a flurry on half
   beats (the densest frame). The resolve: the lockup (the sparsest frame).
4. **Hits map to sound.** Downbeat/808: device layer scale +1.6 % decaying in 0.26 s, cover-wall brightness wave.
   Clap (beat 3 in half-time grooves): a 5 px kick, stat slams, camera FOV −1.2°. Hats: nothing (too dense to read).
   The logo hit's light is an accent bloom on the mark (peak ≤ 0.35, 2 frames, gone in 0.25 s), never a full-frame
   white overlay: the DemoIdent draft's 0.5 overlay lifted its dark corners from luma 3 to 123 (flat grey).
5. **Lyrics cue, never caption.** A lyric anchor ("I changed my phone") times a transformation (iPhone turns into iPad);
   no lyrics on screen. Idents and interstitials sit on vocal-free bars (MAP.md: no `vocals` in the bar's stems), and a
   lyric is a cue only after its words are read in MAP.md's anchors and fit the brand (DemoIdent' first line is not).
6. **Numbers are real.** Stats come from the catalog or a measurement (663 songs, 27 hours); count up in ≤0.55 s.
7. **Endings fade the song itself, into an event.** Never add processing to the artist's song (no echo throw, reverb,
   filter sweep or stutter): "fade after the second sixteen" = a plain linear fade from the end of the last lyric
   line to zero on the section's last event (the in-app pause, the lockup cut): `echo_tail.py --fade-from F --stop S`
   (the trailer: 1.27 s, from the end of "had to change my phone." to the pause). The owner rejected the echo tail as
   "an echo I didn't personally add to the song". Silence after the event is fine; tonal sound design is fine once
   the music has visibly stopped (the studio ident's hit and ring-out). The echo throw (`echo_tail.py` default) and
   `--fade-bars` run-on fade are only for when the artist asks. The studio ident lands where the next section would
   have dropped; lockup type lands on the bar grid continued through the silence.
8. **One motif: the brand mark in liquid glass.** `glass_logo.py`: clear glass on the intro, filling with the brand
   colour through the second half, full on the drop (camera dives into it on the pre-drop), back as the lockup.
   No GPU for Blender: the flat mark (kit `mark.css` + `K.flatMark`): clear = greyscale at 35 % in a 3 px white ring;
   the hit = colour in 0.1 s, a 6 px accent ring, a ring burst to 1.6x over 0.6 s, a 6 % punch, the accent bloom.
9. **Audio-reactive means pre-analysed.** Visuals read the map JSON by frame (waveform, band ring, envelopes); nothing
   listens live, so every frame is reproducible. Recipes: [references/audio-reactive.md](references/audio-reactive.md).
10. **Palette.** Dark stage; the accent only on the motif, the played waveform, the ring, and one word per lockup.
11. **Three type voices.** Numerals (150-236 px at 1080p), labels (46-54 px, muted), one small line (≥ 26 px).
    A lone wordmark (ident, lockup name): 1.0-1.2x the brand headline (Demo Artist 94 → 94-113 px; 104 in both aspects
    of the DemoIdent ident). In 9:16 keep the same px, never under the headline; it clears text_check's 26 px floor
    by far, so the limit is width: under 60 % of the frame.
12. **Two aspects, decided up front.** 16:9 and 9:16 share beats, footage and audio; the vertical is re-laid out (a pose
    table), and its 3D plates are rendered for 9:16. Frame 0 is the product; the last frame is the lockup (feeds loop,
    no fade to black). Vertical type band from ~235 px; key content above the bottom 20 %.

Formats (bar maps, lengths, what each needs): [references/formats.md](references/formats.md).

## Plan

1. Map the song once from 0: `uv run $EB/tools/track_map.py song.mp3 --separate --words --window 0:60 --out
   beats/map.json --md beats/MAP.md`; pick the format and the window on section boundaries; write the bar map
   (section, role, what is on screen). Downbeat: accept it when the tool prints no disagreement; otherwise apply its
   check: in MAP.md the bar where bass or drums first enter must show their first X on step 0 of its groove string;
   a first X on step 4k means the downbeat is k beats later (`--downbeat K` settles it). Then map the edit window
   with `--grid-from beats/map.json --window A:B --offset O --duration D`: same tempo, bars and loudness
   references; never refit a window under ~10 s (DemoIdent 3.4 s: 140.018 → 139.655 BPM, first beat moved).
2. Sound: `echo_tail.py --fade-from F --stop S` for the bed (the stop from the product take when there is one; F at the
   end of the last lyric line), `sfx_synth.py` for one sound per idea once the song is playing (transformation whoosh,
   glass shimmer, dive sub-drop, the pause-tap click, ident impact), none before the first note; `mix.py` to −14 LUFS.
3. Footage: `app-capture` for product UI; catalog artwork for walls and orbits (ledger every file).
4. Plates: `glass_logo.py` per aspect; test three frames at 20 % size, then render at 16 spp (resumable). No GPU:
   the flat mark (rule 8), no plates.
5. Build from [assets/kit/template.html](assets/kit/template.html), the kit files and the beat sheet:
   [references/kit.md](references/kit.md). Then render-verify and delivery-pack for both aspects.

## Sound

The song carries it; SFX mark only what the eye sees, never before the song's first note: −12 dB click on the
real pause tap, −20 dB whoosh on a transformation, −20 dB shimmer when the glass appears, −16 dB sub-drop on the dive, −10 dB impact on the ident. These
are `mix.py` cue `gain_db` values on `sfx_synth.py` files, which peak at −3 dBFS (−10 dB peaks at −13 dBFS
pre-master), with the bed at `mix.py --music-gain` (default −6 dB); loudnorm then moves everything together. Master
−14 LUFS, −1.5 dBTP (AAC adds a few tenths: a −1.0 master tripped remux_audio's limiter and lost 2 dB of peak);
`remux_audio.py --tp -1.0` after every render (HyperFrames 0.8.92 put the DemoIdent ident's −14.0 LUFS mix
at −14.8). Commercial masters often decode over full scale (the example's MP3 peaked 0.81 dB over and the first bed
hard-clipped 922 samples in the hook): give the bed headroom (`echo_tail.py --gain -1.5`; it warns when the output
clips) and let `mix.py` set the level.

A studio ident rings out: send its impact and shimmer through a dark hall (RT60 ~3.4 s, wet only, about -16 dB
under the dry hit) so a 3 s badge hold is not dead air; the last second may decay below -50 dB, waived as
`verify_report --allow-silence <start>:<end>` like a held frame (`--allow-freeze`).

## Acceptance

- Hard cuts on the grid: `verify_report --grid beats/map.json --half` (the track-map JSON works as the grid) fails a
  cut more than one frame (16.7 ms at 60 fps; `--tolerance-ms` to change) from a beat, or a half beat with `--half`.
  Event cuts named in the beat sheet (the stop) are waived by hand; a piece with no hard cuts reads "0/0".
- Sync gate passes on every product clock shown; touch overlays sit on real taps.
- −14 LUFS ±1 and ≤ −1 dBTP on each delivered file; first and last frames carry detail.
- `hf.py check`, `text_check.py`, `asset_ledger.py check` pass for each aspect.

## Checklist

- [ ] Track mapped; format and window on section boundaries; bar map written
- [ ] Mapped once from 0, edit window mapped with `--grid-from`; downbeat check applied when cues disagree
- [ ] Silence before the first note; bookends from the product; a plain fade into the stop, nothing added to the song
- [ ] Motif in glass (plates per aspect after a three-frame test), or the flat mark without a GPU
- [ ] Every pulse from the map JSON; lyrics as anchors only; numbers real
- [ ] 16:9 and 9:16 verified and delivered
