# QA report: trailer-9x16.mp4

- when: 2026-09-29T19:14:21
- profile: shorts {"size": "1080x1920", "fps": 60, "lufs": -14, "true_peak": -1.0, "max_seconds": 60}
- verdict: **automated gates pass**; the visual gate needs a reader

| gate | status | detail |
|---|---|---|
| hyperframes-check | PASS | lint ok, runtime ok, layout ok, motion ok, contrast ok |
| text | PASS | 21 text items; 0 errors, 0 warnings  PASS |
| av-qa | PASS | PASS |
| encoded-tail | PENDING | decoded frame 2369 of 2369 to qa/9x16/encoded-last-frame.png; inspect it and record end-card proof before delivery |
| loudness | PASS | renders/trailer-9x16.mp4: -13.6 LUFS, LRA 16.0 LU, TP -1.4 dBTP  OK (target -14.0 ±1 LU, TP <= -1.0) |
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

- overview (5 sheets, 0.5 s): the same beats as 16:9, re-laid out for 1080x1920: the real search tap and Now Playing
  with the waveform below (0-4.5), home-screen push into the icon, portrait glass plate (camera pulled back for the
  upright cover ring), fill and dive (5.3-16.8); cover wall with the count-ups centred above the device, iPhone and
  iPad takes (16.9-25.5); sphere, flurry, lyric swaps, spectrum ring, push into the pause (26-32.7); glass lockup
  "Lil Gohan / Coming Soon™ / iPhone · iPad", fade, Uppercut Labs badge held to the end (32.9-39.5). Type and
  numerals sit in the upper band and nothing key sits in the bottom 20 %.
- cuts and transitions: flash-cuts into and out of the glass (5.34, 16.86, 32.94) by design; 3/3 hard cuts on the grid.
- text legibility at phone size: text gate 21 items, 0 warnings.
- end card: encoded-last-frame.png (frame 2369 of 2369) is the Uppercut Labs badge and wordmark: the end-card proof.
- sound: the same mix as 16:9 (silence before the first note; plain fade into the pause; no echo).

## Repairs

| # | finding | fix | pass |
|---|---|---|---|
