# Gates: what each proves, and the usual fixes

| Gate | Proves | Usual failures and fixes |
|---|---|---|
| hyperframes-check | DOM: no overlaps, contrast AA, no runtime errors, motion sidecar holds | contrast: use the finding's `suggestedColor`; `gsap_non_transform_motion`: animate x/y/scale/opacity, not letter-spacing or width; `sweep_static`: keep one element alive through long holds |
| av-qa | size, fps, duration, no black/freeze outside allowed ranges, no pops, audio as long as video, and content in the opening and closing frames | truncated audio: end streams with trim/atrim in the graph, not `-t`; black open: allow it only if the plan fades in; background-only ends need a hook or end card |
| loudness | integrated LUFS and true peak on the delivered file | too quiet: loudnorm two-pass in the mix, then re-mux; TP over: lower the limiter ceiling (AAC adds ~0.3 dB) |
| beat-align | every hard cut within one frame of a beat or half-beat | a cut late by N frames: move the clip boundary, not the music; measured references need `--auto-offset` |
| face-clear | overlays never sit on the speaker's face | move the card to a free zone from faces.json; intentional takeovers go in `--face-skip` |
| words | captions / cut / narration contain the expected words | missing words: the cut clipped a word (re-plan with silence snapping) or captions skipped a line |
| visual | a human-grade read of the whole piece | off-brand device, unreadable small text at 390 px wide, a transition that reads as a glitch |
| opening-frame | encoded frame 0 and the first three seconds show the planned hook, not an empty/background-only opening | extract the encoded frame 0 and a 3-second contact strip; repair the hook, then rerun `av-qa` |
| encoded-tail | the exact encoded last frame is an end card carrying the voice disclosure | `verify_report.py --require-end-card --end-card-proof qa/end-card.json` extracts `qa/encoded-last-frame.png`; inspect that exact frame and record `{"frame":"encoded-last-frame.png","is_end_card":true,"voice_disclosure":"Narrated with a voice model trained on the creator's own voice."}`; anything missing fails |
| revision-proof | a post-remux/package encode still has the planned frame 0, exact N-1 tail, mid-hold seek state (or an explicit static result), and approved logo bytes | run the proofs on each copied delivery file; record the frame hashes and logo SHA-256 values, and call a static card `not animated` rather than claiming a count-up was tested |
| logo-fidelity | every official logo in the encoded video matches its ledger/source file in colour, proportions, and clear space | compare a frame crop with the source SVG/PNG; animate the wrapper or replace the incorrect asset |
| duration-ledger | real footage/captures, generated media, and the final encoded duration are separately accounted for | list each source segment and generated clip; reconcile the sum against the render instead of hiding a missing or repeated segment |
| persistent-shell | frame 0 and each persistent-bug hold keep the source chip, bug, lockup, and kicker in separate readable lanes | reserve a chip lane after long credits wrap; inspect exact frames because opaque shell layers can hide collisions from DOM checks |

Planned holds: pass every intentional interval in one comma-separated value, for example
`--allow-freeze 12.0:15.5,40.2:44.0`; the literal separator is `:` (`start:end`), and each range must match the plan.
Thresholds used by the tools: black frame = 99.8% of pixels below 6% luma (dark designs are not black); content ends
need edge density >= 0.0005 and foreground detail share >= 0.005; static picture > 2 s is a warning; silence > 0.8 s
at -50 dB is a warning; a join louder than -30 dBFS within 25 ms fails.
