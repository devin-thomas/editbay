# Transcript failure modes seen in practice

| Pattern | Example | Caught by |
|---|---|---|
| Invented filler after a pause | large-v3 adds "Wait," or "Um," at sentence starts after 0.3-2 s of silence, even with previous-text conditioning off | majority vote; token pass drops words neither other source has |
| Prompt-induced phrase | a vocab prompt nudges large-v3 into "that shows you how to do that" | majority vote (turbo and captions lack it) |
| Dropped sentence | large-v3 skips a whole clause that turbo and captions both have | majority vote re-inserts it |
| Name as a common word | "Cloud Code", "11 Labs", "key.ai", "GBD6", "free school" | glossary |
| Context-dependent name | "Cloud." that was really "Kling" | patch with a frame as evidence |
| Split compound | "timestamp" vs "time stamp"; `one` + `-time` | join the caption token after checking the script; preserve audio |
| Clean verbatim | turbo drops "um"/"uh" | keep large-v3 as primary when cutting fillers |
| Garbled synthetic speech | TTS produced wrong words; both models agree on the nonsense | voiceover_check.py against the script |
| Word timing drift | word edges off by 100-300 ms around pauses | rough-cut snaps cuts to silence, not to word edges |

Whisper's `initial_prompt` biases spelling and style for the first window only; keep it to a comma list of names.
