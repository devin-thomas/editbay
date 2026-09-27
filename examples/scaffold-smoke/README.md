# Scaffold smoke test

A 12 s synthetic beat sheet that uses every text cue kind (title, side card with kicker, numbered step, bullets,
label, word highlight) plus burned-in captions, scaffolded at 16:9 and 9:16. It is the regression test for
`hf_scaffold.py`'s defaults; nothing here is rendered.

```bash
uv run ../../tools/hf_scaffold.py --beats beats.resolved.json --brand ../../brands/starter-pack.json --out /tmp/s169 \
  --captions words.json --size 1920x1080
uv run ../../tools/hf_scaffold.py --beats beats.resolved.json --brand ../../brands/starter-pack.json --out /tmp/s916 \
  --captions words.json --size 1080x1920 --remap left=upper,right=lower,center=upper,bottom=lower,top=lower
uv run ../../tools/hf.py check /tmp/s169 --json      # and /tmp/s916
uv run ../../tools/text_check.py /tmp/s169 --brand ../../brands/starter-pack.json
```

Results on 2026-09-27 (HyperFrames 0.8.79):

| scaffold | hyperframes check | text_check |
|---|---|---|
| before (editbay 0.2.0) | FAIL: 31 `gsap_css_transform_conflict`, 1 `negative_z_index`; layout pass skipped because lint failed | FAIL: kicker, step number, and label at 26 px (minimum 36); 9:16 title with a one-word last line |
| after, first pass | lint clean; layout now runs and finds captions overlapping bottom-zone cards (14 at 16:9, 19 at 9:16) | PASS |
| after (0.3.0) | PASS in both formats (only the advisory `nested_structure_needs_subcomposition`) | PASS in both formats |

What changed to get there: highlights no longer carry a CSS transform or a negative z-index; kickers, step numbers
and the HUD are `data-decorative`; labels and image captions use the phone minimum; headings balance their lines;
zones stop above the caption band; vertical layouts keep the bottom 26% and right 12% clear for platform UI; and the
scaffold warns when two cues share a zone at the same time (the fixture's 9:16 remap had one, now fixed).
