# QA report: trailer-16x9.mp4

- when: 2026-09-29T18:47:28
- profile: reel {"size": "1920x1080", "fps": 60, "lufs": -14, "true_peak": -1.0}
- verdict: **automated gates pass**; the visual gate needs a reader

| gate | status | detail |
|---|---|---|
| hyperframes-check | PASS | lint ok, runtime ok, layout ok, motion ok, contrast ok |
| text | PASS | 21 text items; 0 errors, 0 warnings  PASS |
| av-qa | PASS | PASS |
| encoded-tail | PENDING | decoded frame 2369 of 2369 to qa/16x9/encoded-last-frame.png; inspect it and record end-card proof before delivery |
| loudness | PASS | renders/trailer-16x9.mp4: -13.6 LUFS, LRA 16.0 LU, TP -1.4 dBTP  OK (target -14.0 ±1 LU, TP <= -1.0) |
| beat-align | PASS | 3/3 cuts within ±16.7 ms |
| face-clear | PENDING | no --faces/--source (no talking head?) |
| words | PENDING | both --expected and --heard are required for the words gate |
| visual | PENDING | read 6 sheet(s) at this phase boundary and record what you saw below |

## Evidence

- hyperframes-check.json
- text.json
- av_qa.json
- encoded-last-frame.png
- loudness.json
- cuts.json
- overview_01.jpg
- overview_02.jpg
- overview_03.jpg
- overview_04.jpg
- overview_05.jpg
- strips_01.jpg

## Visual gate (fill in after reading the sheets)

- overview (5 sheets, 0.5 s): real search tap and Now Playing with the waveform (0-4.5), home-screen push into the
  icon, glass icon with cool-white shine sweeps (no lavender), aqua fill and cover ring, spin and dive (5.3-16.8);
  drop into the cover wall with count-ups 663 songs / 27 hours / 68 albums / 49 collections / 338 producers, iPhone
  and iPad takes (16.9-25.5); sphere, flurry cards, iPhone -> iPad -> iPhone swaps on the lyric, spectrum ring, push
  into the pause (26-32.7); glass lockup "Lil Gohan / Coming Soon™ / iPhone · iPad" on the echo hits, fade, Uppercut
  Labs badge held to the end (32.9-39.5). No blank, cropped or duplicated frames; the drop's 3 black frames are gone.
- cuts and transitions: flash-cuts into and out of the glass (5.34, 16.86, 32.94) by design; 3/3 hard cuts on the grid.
- text legibility at phone size: numerals 150-236 px, labels ≥ 46 px, the smallest line ("iPhone · iPad") ≥ 26 px;
  text gate 21 items, 0 warnings.
- end card: encoded-last-frame.png (frame 2369 of 2369) is the Uppercut Labs badge and wordmark, centred, on the dark
  stage: the end-card proof.
- sound (owner's notes 2026-09-29): digital silence before the song's first note (T 0-1.44); a plain linear
  fade from the end of "had to change my phone." (T 31.48) to zero at the in-app pause (T 32.755); no echo or
  reverb on the song; the real pause-tap click, then silence under the lockup until the Uppercut Labs hit rings out.
  Silences waived as intended: 0-1.5, 32.7-36.1, 38.2-39.5.
- sync: in-app clock / listen counter match the soundtrack at 10 of 10 sampled Now Playing frames (sync_gate.txt).

## Repairs

| # | finding | fix | pass |
|---|---|---|---|
