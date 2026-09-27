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

Planned holds: pass every intentional interval in one comma-separated value, for example
`--allow-freeze 12.0:15.5,40.2:44.0`; the literal separator is `:` (`start:end`), and each range must match the plan.
Thresholds used by the tools: black frame = 99.8% of pixels below 6% luma (dark designs are not black); content ends
need edge density >= 0.0005 and foreground detail share >= 0.005; static picture > 2 s is a warning; silence > 0.8 s
at -50 dB is a warning; a join louder than -30 dBFS within 25 ms fails.
