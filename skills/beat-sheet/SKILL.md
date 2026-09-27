---
name: beat-sheet
description: Plan the beats of an edit before building anything. Turns a transcript (or a music grid) and a brief into cues anchored to spoken words or musical beats ("when I say X, show Y, there, like this, because Z"), resolves them to exact times, checks read time, zones, face keep-clear, and text density, and writes the motion assertions the verifier enforces. Use when planning motion graphics, overlays, B-roll placement, captions emphasis, cut points on music, or a storyboard for a video; after transcript-reconcile or rough-cut, before motion-build.
---

# Beat sheet

The beat sheet is where taste becomes checkable. Every visual event is anchored to a word the viewer hears or a beat
they feel, placed in a zone that keeps the face clear, and held long enough to read. The build follows the sheet;
the verifier holds the build to it.

Paths: `$EB` is the editbay root, the folder holding `skills/` and `tools/` (`../..` from this skill's folder). Tools run as `uv run $EB/tools/<tool>.py`.

## 1. Gather the spine

- Voice-led pieces: the word array on the timeline the build will use (`cut/words.cut.json` after a rough cut,
  `narration/words.words.json` for narration, `transcript/final.words.json` for untouched footage).
- Music-led pieces: `beat_grid.py grid --bpm B --duration D --fps F --json beats/grid.json` for music you control,
  or `beat_grid.py detect track.wav --json beats/grid.json` for a track you were given (check the tempo by ear:
  detectors halve or double it).
- Footage with a face: `faces.py SRC --json media/NAME.faces.json` gives the keep-clear box and free zones.
- The brand profile (read time, allowed and forbidden devices) and the style skill, if one applies.

**Done when:** the words or grid, the face zones (if any), and the brand profile are in hand.

## 2. Write the cues

One cue per visual event in `beats/beats.json`. The anatomy, from the brief's own words where possible:
- **anchor**: the phrase that triggers it ("Fable 5.1"), or a beat index for music-led cues
- **kind and content**: side-card, lower-third, title, bullet, word-highlight, image-panel, pip, takeover, sfx-only
- **zone**: where it lives (left/right/top/bottom/center/full/pip-*), chosen from the free zones; pointing and gaze
  in the footage decide sides ("I point left, so the card enters from the left")
- **treatment**: what keeps it legible over footage (a glass or solid card behind text), and its enter/exit
- **why**: the story reason; a cue without a why is decoration

Schema, cue kinds, and worked examples: [references/beats-format.md](references/beats-format.md). Mode comes from the
brief: **strict** (only the cues listed) or **open** (the agent may add flourishes, each marked `"origin": "agent"`
with its why, so the creator can veto it on the sheet).

**Done when:** every moment the brief asks for has a cue, every cue has a why, and agent-added cues are marked.

Before polish, make three rough first-three-second openings and compare them for a clear news statement. If the piece
uses curiosity, list each question in `beats/OPEN-LOOPS.json` with `question`, `setup_time`, and `payoff_time`.

## 3. Resolve and check

```bash
uv run $EB/tools/beats_check.py beats/beats.json --brand BRAND.json --open-loops beats/OPEN-LOOPS.json
```

Errors (an anchor not found, with the nearest matches printed; a cue outside the piece) block the build. Warnings are
decisions: text shorter than the brand's read time (make it longer, or mark `"flash": true` if it is a flash), two
cues in one zone at once, more than two text elements on screen, a zone that overlaps the face (move it, or set
`"cover_face": true` with a reason for a deliberate takeover). Music-led cuts land on beats or half-beats; a flurry
of sub-beat cuts belongs just before a resolve, not in the middle of a read. Open-loop checks fail a missing payoff or a
payoff at two seconds or less after setup.

**Done when:** 0 errors, and every warning is fixed or answered in the cue's why.

## 4. Hand off

`beats/beats.resolved.json` (exact times, the build's input), `beats/BEATS.md` (the table and a per-zone timeline,
the review surface for the creator), and `beats/<composition>.motion.json` (every cue appears by its start + 0.5 s,
stays in frame, keeps its order: `hyperframes check` enforces it automatically when the sidecar sits next to the
composition). Show the creator `BEATS.md` before building when the brief asks for a review.

**Done when:** the three files exist and the motion sidecar is copied next to the composition it describes.

## Checklist

- [ ] Spine on the right timeline (post-cut words, narration words, or the music grid)
- [ ] Every requested moment has a cue with anchor, zone, treatment, and why
- [ ] 0 errors; warnings fixed or justified
- [ ] Motion sidecar placed next to the composition
- [ ] Three rough openings compared before polish; open loops have a payoff more than 2 s after setup
