# QA report: review.mp4

- when: 2026-09-26T21:55:09
- profile: explainer {"size": "1920x1080", "fps": 60, "lufs": -16, "true_peak": -1.0, "master": "3840x2160@60 plus 1080p60 review"}
- verdict: **automated gates pass**; the visual gate needs a reader

| gate | status | detail |
|---|---|---|
| hyperframes-check | PASS | lint ok, runtime ok, layout ok, motion ok, contrast ok |
| av-qa | PASS | - note static picture 50.00-50.90s (0.9s; allow intentional holds with --allow-freeze) |
| loudness | PASS | renders/review.mp4: -16.1 LUFS, LRA 3.9 LU, TP -1.4 dBTP  OK (target -16.0 ±1 LU, TP <= -1.0) |
| beat-align | PENDING | no --grid (not music-led, or not given) |
| face-clear | PENDING | no --faces/--source (no talking head?) |
| words | PASS | 149 expected words, 149 heard; 0 findings, 0 insertions to review |
| visual | PENDING | read 8 sheet(s) at this phase boundary and record what you saw below |

## Evidence

- hyperframes-check.json
- av_qa.json
- loudness.json
- words.json
- overview_01.jpg
- overview_02.jpg
- overview_03.jpg
- overview_04.jpg
- overview_05.jpg
- overview_06.jpg
- overview_07.jpg
- overview_08.jpg

## Visual gate (fill in after reading the sheets)

- overview:
- cuts and transitions:
- text legibility at phone size:

## Repairs

| # | finding | fix | pass |
|---|---|---|---|
