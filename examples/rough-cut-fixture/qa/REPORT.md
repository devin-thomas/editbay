# QA report: cut.mp4

- when: 2026-09-26T21:04:38
- profile: none 
- verdict: **automated gates pass**; the visual gate needs a reader

| gate | status | detail |
|---|---|---|
| hyperframes-check | PENDING | no --hf-project given |
| av-qa | PASS | PASS |
| loudness | PASS | cut/cut.mp4: -20.1 LUFS, LRA 5.1 LU, TP -6.1 dBTP |
| beat-align | PENDING | no --grid (not music-led, or not given) |
| face-clear | PENDING | no --faces/--source (no talking head?) |
| words | PASS | 52 expected words, 55 heard; 0 findings, 3 insertions to review |
| visual | PENDING | read 3 sheet(s) at this phase boundary and record what you saw below |

## Evidence

- av_qa.json
- loudness.json
- words.json
- overview_01.jpg
- overview_02.jpg
- overview_03.jpg

## Visual gate (fill in after reading the sheets)

- overview:
- cuts and transitions:
- text legibility at phone size:

## Repairs

| # | finding | fix | pass |
|---|---|---|---|
