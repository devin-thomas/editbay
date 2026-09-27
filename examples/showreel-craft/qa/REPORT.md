# QA report: final.mp4

- when: 2026-09-26T22:31:04
- profile: reel {"size": "1920x1080", "fps": 60, "lufs": -14, "true_peak": -1.0}
- verdict: **PASS** on every applicable gate, and on the style's acceptance numbers (below)

| gate | status | detail |
|---|---|---|
| hyperframes-check | PASS | lint ok, runtime ok, layout ok, motion ok, contrast ok |
| av-qa | PASS | - note static picture 8.53-9.15s (0.6s; allow intentional holds with --allow-freeze) |
| loudness | PASS | renders/final.mp4: -14.3 LUFS, LRA 1.5 LU, TP -1.4 dBTP  OK (target -14.0 ±1 LU, TP <= -1.0) |
| beat-align | PASS | 10/10 cuts within ±34.0 ms |
| face-clear | PENDING | no --faces/--source (no talking head?) |
| words | PENDING | no --expected/--heard |
| visual | PASS | read at 0.25 s per frame (qa/look_*.jpg): see Visual gate |

## Evidence

- hyperframes-check.json
- av_qa.json
- loudness.json
- cuts.json
- overview_01.jpg
- overview_02.jpg
- overview_03.jpg
- strips_01.jpg
- strips_02.jpg

## Visual gate

- overview: eight bars read as eight ideas: the caret drops and blinks; "Words first, then frames." lands a word per
  beat with the accent word in light blue; the caret multiplies into a 16x9 field with a blue wave; the waveform's
  dead air, filler, and retake collapse on beats 13-15; this reel's own composition code types in (its data-start
  really is 7.500) and tilts into 3D frames; after a half-beat of silence, eight half-beat recap cards; the wordmark
  builds and the caret lands after it, blinking through the hold.
- cuts and transitions: chapter changes are transformations (caret to line, words to dots, grid to line, code card to
  3D frames) or a two-frame flash (into bar 5); hard cuts only in the flurry.
- legibility: statement, code, labels, and lockup read at 1080p; the machine line is deliberately small and dim.
- signature check: no corner-bracket HUD, no format/fps/BPM label block, no borrowed statement or colour; the motif,
  words, chapters, and palette come from the starter-pack brand and the subject.

## Style acceptance (style-craft-reel)

| Rule | Reference (Kenn's reel) | This reel | Pass |
|---|---|---|---|
| hard cuts on the grid | 7/12 within 2 frames after removing detector lag | 10/10 within 34 ms of the bed's exact grid (median 8 ms) | yes |
| cuts back-loaded | by third 2, 1, 9 | by third 0, 1, 9 | yes |
| chapters | 6 crafts + flurry + lockup | 6 crafts + flurry + lockup, each labelled | yes |
| final hold | 2.0 s | 3.4 s (13.13-16.5 s) | yes |
| loudness | -12.4 LUFS, -0.6 dBTP | -14.3 LUFS, -1.4 dBTP (after remux) | yes |

## Repairs

| # | finding | fix | pass |
|---|---|---|---|
| 1 | mix peaked -1.4 dBTP against a -1.5 ceiling | loudness.py trims true-peak overshoot after linear loudnorm | tool fix |
| 2 | render measured -16.1 LUFS from a -14.3 LUFS mix | measured a constant -1.79 dB render gain (HyperFrames normalises to about -16); remux_audio.py puts the mastered mix back | tool fix |
