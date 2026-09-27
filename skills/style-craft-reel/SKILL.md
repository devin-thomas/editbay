---
name: style-craft-reel
description: A 12-20 second craft showreel on a beat grid, in which one brand motif travels through five to seven labelled craft chapters, accelerates into a half-beat flurry, and resolves on a lockup. Use when asked for a showreel, sizzle opener, motion-design reel, brand sting longer than a logo, or "show what you can do" piece, or when a brief names this style. Learned from a measured reference (see Source); sources its motif, words, and palette from the brand.
---

# Style: craft reel

Range, proven in fifteen seconds: each chapter is a different discipline, and one motif ties them together so the
variety reads as one voice. Source of truth: the breakdown in `examples/style-from-kenn-reel/reference/BREAKDOWN.md`
of the editbay repository (principles 1-9); this skill restates them as rules with numbers.

Paths: `$EB` is the editbay root, the folder holding `skills/` and `tools/` (`../..` from this skill's folder). Tools run as `uv run $EB/tools/<tool>.py`.

## Grammar

1. **One motif.** Take the brand's most reduced element (a caret, a dot, a corner of the logo, one letter). It appears
   in the first second and lands in the lockup as part of the name.
2. **Five to seven chapters, each a different craft** (kinetic type, shape field, diagram, interface, material,
   particles or texture). Label each in the machine layer: number and plain name.
3. **Hand-offs transform.** The current chapter's material becomes the next chapter's material (motif to line, words to
   dots, dots to grid, grid to interface). Where that would be forced, a 1-2 frame flash cuts. Plain hard cuts belong
   to the flurry.
4. **Cuts on the grid.** Chapter changes on beats (downbeats first), flurry cards on half-beats. Every hard cut within
   2 frames of the piece's own beat grid.
5. **Accelerate, then resolve.** About 70% development, 15% flurry, 15% lockup and hold. More than half of all cuts
   fall in the last third.
6. **Density breathes.** Alternate sparse and dense chapters; the densest frame comes just before the flurry; the
   lockup is the sparsest.
7. **Palette discipline.** Neutrals cover at least 70% of the frame; one or two brand accents under 10% combined,
   reserved for the motif and one emphasis per chapter.
8. **Three type voices.** Display for statements, one accent voice for a single emotional word, mono for the machine
   layer.
9. **The machine layer frames, never competes** (only when the brand allows HUD numbers): corner marks, a label,
   format and tempo, timecode, chapter; small and low contrast.

## Plan

Bars = round(seconds x BPM / 240). At 128 BPM, 15 s is 8 bars of 1.875 s: bar 1 motif, bars 2-6 one chapter each,
bar 7 the flurry (8 half-beat cards recapping each chapter's material), bar 8 the lockup, plus an end-hit ring-out.
Generate the bed with the same numbers so the grid is exact
(`beat_bed.py --bpm 128 --sections intro:1,build:1,drop:5,hold:1 --end-hit`), and write the beat sheet with `beat`
cues (`beats_check.py` resolves them on `bed.grid.json`). Scene ideas: [references/scene-library.md](references/scene-library.md).

## Sound

120-130 BPM. A soft whoosh on each hand-off, a tick with each chapter label, silence for half a beat before the
flurry (a pre-drop gap), an impact on the lockup, the end-hit ringing under the hold. Master at -14 LUFS, -1 dBTP.

## Brand adaptation

- HUD numbers forbidden: keep only the chapter labels, no timecode or tempo.
- Particles forbidden: make the density peak a wall of type or a grid.
- Glitch forbidden: flurry cards change on plain cuts.
- The brand's accent replaces any colour the reference used; never import the reference's palette.
- Keep the reference's signature out (see the breakdown's last section).

## Acceptance

- `beat_grid.py align --cuts qa/cuts.json --beats sound/bed.grid.json --half --tolerance-ms 34` passes (60 fps).
- Cuts by third back-loaded (last third > 50% of cuts); 5-7 labelled chapters; final hold at least 1.5 s.
- -14 LUFS within 1 LU, true peak at or below -1 dBTP; `hyperframes check` clean.

## Checklist

- [ ] Motif from the brand; appears in the first second and lands in the lockup
- [ ] 5-7 chapters, each a different craft, each labelled
- [ ] Bed and beat sheet on the same grid; cuts verified against it
- [ ] Acceleration, density, and palette rules met; reference signature absent
