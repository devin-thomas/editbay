# QA report: review.mp4

- when: 2026-09-26T22:11:24
- profile: explainer {"size": "1920x1080", "fps": 60, "lufs": -16, "true_peak": -1.0, "master": "3840x2160@60 plus 1080p60 review"}
- verdict: **PASS**: every applicable gate passed; beat-align and face-clear do not apply (voice-led, no footage)

| gate | status | detail |
|---|---|---|
| hyperframes-check | PASS | lint ok, runtime ok, layout ok, motion ok, contrast ok |
| av-qa | PASS | - note static picture 50.00-50.90s (0.9s; allow intentional holds with --allow-freeze) |
| loudness | PASS | renders/review.mp4: -16.1 LUFS, LRA 3.9 LU, TP -1.4 dBTP  OK (target -16.0 ±1 LU, TP <= -1.0) |
| beat-align | PENDING | no --grid (not music-led, or not given) |
| face-clear | PENDING | no --faces/--source (no talking head?) |
| words | PASS | 149 expected words, 149 heard; 0 findings, 0 insertions to review |
| visual | PASS | read at 1 s per frame after each pass, plus pass-2 strips and a 390 px phone preview: see Visual gate |

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

Read as one-per-second sheets (`qa/look1s_*.jpg`) after the draft and after each repair pass, plus strips around the
two pass-2 fixes (`qa/pass2_01.jpg`) and a 390 px phone preview (`qa/phone_01.jpg`, `qa/phone_after_01.jpg`).

- overview: calm teaching layout on the starter-pack grid; each step holds a step card (left) and a live
  demonstration (right) under a five-step rail. After pass 1 no step leaves an empty frame; every demo event lands on
  the word that names it (timestamps tick with the words, waveform chunks collapse on "dead air", "filler",
  "retakes", checks tick on "loudness", "every cut", "every card", "fixes").
- cuts and transitions: step changes cross-fade inside 0.3 s; the end card fades in at 55.93 s with nothing under it
  (pass 2).
- text legibility at phone size (390 px wide): titles, step names, demo rows, checklist, rail chips (36 px after the
  phone fix), and the voice disclosure (36 px) all read. Smallest remaining text: the mono STEP kickers (26 px), which
  repeat the rail and are decorative.
- honesty: every checklist line is backed by this report (loudness gate, words gate, motion sidecar in
  hyperframes-check); the frame counter ends on the real frame count (3587).

## Repairs

| # | finding | fix | pass |
|---|---|---|---|
| 1 | check before any render: stacked rail highlights overlapped text; end card had a zero-size box; tweens aimed at missing subtitles; highlight z-index could escape its word | one rail with opacity-only glow layers; full-zone scenes get a real box; subtitle tween only when a subtitle exists; `isolation: isolate` on words | pre-render |
| 2 | draft: about 1 s of empty background between every step (0:16, 0:24, 0:32, 0:39, 0:48, 0:56) | scenes hold until the next step's first word (`until_start` in beats_check) | 1 |
| 3 | draft: checklist claimed "every cut on its beat", a gate this voice-led piece never ran | replaced with "149 of 149 words heard", which the words gate proves | 1 |
| 4 | draft: frame counter stopped at 0638 behind its fading card | counts to the real frame count; pass 2 starts it on "renders" so 3587 lands and holds | 1, 2 |
| 5 | pass 1: closing title and loop cross-faded through the end card at 0:56 | tails trimmed so they finish as the end card begins | 2 |
| 6 | phone check: rail chips (32 px) and disclosure (28 px) below the brand's 36 px phone minimum | both raised to 36 px | 1 (phone) |
| 7 | tooling: words gate failed on "1" vs "one" | transcript_diff and voiceover_check compare numbers 0-99 as words | tool fix |
