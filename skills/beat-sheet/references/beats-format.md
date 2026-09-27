# beats.json

```json
{
  "timeline": "cut",
  "words": "../cut/words.cut.json",
  "grid": null,
  "faces": "../media/talk.faces.json",
  "fps": 60, "duration": 42.0, "min_read": 2.5,
  "composition": "index.html",
  "mode": "open",
  "cues": [
    {"id": "C01", "anchor": "Fable 5.1", "occurrence": 1, "offset": -0.15, "hold": 2.6,
     "kind": "side-card", "zone": "left", "enter": "slide-from-left", "exit": "fade",
     "content": {"title": "Fable 5.1", "subtitle": "Anthropic", "icon": "assets/logos/anthropic.svg"},
     "treatment": "glass card behind icon and text", "sfx": "whoosh-short",
     "why": "he points to his left as he says it"},
    {"id": "C02", "anchor": "best outputs ever", "until": "ever", "kind": "word-highlight", "zone": "bottom",
     "why": "the claim of the video; highlight each word as it is said"},
    {"id": "C03", "beat": 16, "hold_beats": 4, "kind": "title", "zone": "center", "content": {"title": "SHIP IT"},
     "why": "the drop"},
    {"id": "C04", "anchor": "screen recording", "hold": 3.0, "kind": "image-panel", "zone": "right",
     "content": {"src": "assets/clips/repo-scroll.mp4", "label": "screen recording"}, "origin": "agent",
     "why": "prove the claim on screen while it is said"}
  ]
}
```

Fields: `anchor` (phrase), `occurrence` (Nth, default 1), `offset` (seconds; negative lands the entrance just before
the word), `hold` or `until` (+ `tail`), `beat` + `hold_beats` (music), `at` (absolute, last resort), `zone`,
`kind`, `content`, `enter`, `exit`, `treatment`, `sfx`, `why`, `origin` (`agent` for unrequested additions),
`flash` (short on purpose), `cover_face` (deliberate takeover), `selector` (DOM id when not `#<id>`).

## OPEN-LOOPS.json

Curiosity is a timing obligation, not a vague note. Keep `beats/OPEN-LOOPS.json` beside the beat sheet:

```json
{
  "loops": [
    {"id": "L01", "question": "Why did the merchant block the agent?", "setup_time": 4.2, "payoff_time": 19.6}
  ]
}
```

`beats_check.py --open-loops beats/OPEN-LOOPS.json` fails a missing or non-numeric setup/payoff, a time outside the
piece, and any payoff at two seconds or less after its setup. Keep the question short enough to review against the
opening and name the beat that pays it off in the adjacent cue's `why`.

Beat anchors use the reconciled lexical form. If ASR splits a compound, use the joined token (`Large-scale`, not a
separate `Large`/`-scale` display) after transcript reconciliation so beat timing and captions agree.

The open-loop contract is adapted from `nateherkai/hyperframes-student-kit` (`.claude/skills/short-form-edit/`), under
its MIT license and pipeline-use permission. Preserve that attribution when reusing the wording or checker rule.

## Timing habits that read well

- Entrances land 0.1-0.2 s before the anchor word: the eye arrives as the ear does.
- Hold text for the brand's read time (2-2.5 s for a short line, +0.3 s per extra word past five).
- Exits happen on a pause or on the next anchor, not mid-word.
- One idea on screen at a time; a second element may support the first, a third competes.
- Cards live beside the face, never on it: the face is the reason people watch a talking head.
- On music: chapter changes on downbeats, hard cuts on beats or half-beats, a pre-drop gap (music ducked for half a
  beat) before the biggest hit, and the densest flurry just before the final resolve.
