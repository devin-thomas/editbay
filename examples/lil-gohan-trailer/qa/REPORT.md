# QA: Lil Gohan app trailer

Two deliverables from one beat sheet. Each has its own verify_report run (every automated gate, contact sheets, the
exact last frame) plus the clock sync gate (`tools/sync_gate.py`: OCR of the in-app clock / listen counter on rendered
Now Playing frames against the soundtrack).

| deliverable | report | automated gates | sync gate | visual read |
|---|---|---|---|---|
| 16:9 master (1920x1080, 60 fps, 39.5 s) | [16x9/REPORT.md](16x9/REPORT.md) | PASS: hyperframes-check, text, av-qa, loudness (-13.6 LUFS, -1.4 dBTP), beat-align 3/3 | PASS 10/10 | done: sheets and end card read |
| 9:16 master (1080x1920, 60 fps, 39.5 s) | [9x16/REPORT.md](9x16/REPORT.md) | PASS: hyperframes-check, text, av-qa, loudness (-13.6 LUFS, -1.4 dBTP), beat-align 3/3 | PASS 10/10 | done: sheets and end card read |

Repairs found by QA and review on the way to the 16:9 final (details in [../RETRO.md](../RETRO.md)):
- the shine sweep reflected lavender in the thin-film glass (off-brand): split light, 631 frames re-rendered;
- lockup type and glow keyed 0.31 s after the audible echo hits: moved onto the hits;
- 3 black frames before the drop (the stage canvas started 0.06 s early on the plate's track): stage starts on the drop;
- two root compositions in one folder (lint): one project per aspect;
- 2.4 s of dead air under the studio badge: the ident rings out (hall reverb), last second waived as a decay;
- a -1.0 dBTP master tripped remux_audio's limiter in AAC: mastered at -1.5 dBTP;
- owner's notes on the sound: silence before the song's first note (the swell and tap click removed) and a plain
  fade into the pause instead of the echo tail; silences waived as intended (0-1.5, 32.7-36.1, 38.2-39.5).
