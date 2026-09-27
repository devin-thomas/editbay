# Example: craft reel (style-craft-reel, starter-pack brand)

The proof piece for [reference-to-style](../../skills/reference-to-style/SKILL.md): a 16.5 s reel built with the
[style-craft-reel](../../skills/style-craft-reel/SKILL.md) skill that was generated from the measured reference in
[../style-from-kenn-reel](../style-from-kenn-reel/reference/BREAKDOWN.md).

- Motif: the brand's blue terminal caret. Statement: "Words first, then frames." Chapters: caret, words, field, cut,
  build, render, recap, lockup. 128 BPM, 8 bars, a pre-drop gap before the flurry, an end hit under the hold.
- Build: `build.py` writes the beat sheet on the bed's grid; `beats_check.py`, `mix.py`, `hf_scaffold.py`, render,
  then `remux_audio.py` for the -14 LUFS target.
- Verification: [qa/REPORT.md](qa/REPORT.md) (all gates pass; every hard cut within 34 ms of the grid).
