---
name: motion-build
description: Build the motion for an edit in HyperFrames from a checked beat sheet. Scaffolds a composition with exact cue timing and the brand's tokens (cards beside the face, legible type, transform-only motion, one mixed audio track), then layers taste on top, and gates it with hyperframes check before rendering drafts and masters. Use when adding motion graphics, overlays, captions, lower thirds, kinetic type, or animated scenes to a video, or building a motion piece from a beat sheet; after beat-sheet, before render-verify. HyperFrames' own skills own the authoring contract; this skill owns editbay's conventions.
---

# Motion build

The beat sheet decided what happens when; this builds it. Scaffold first so timing and legibility are right by
construction, then spend taste on the scenes that carry the idea. HyperFrames' skills (`/hyperframes`,
`/hyperframes-core`, `/hyperframes-animation`, `/hyperframes-cli`) are the reference for anything this file does
not say; install them with `npx hyperframes skills update` when they are missing.

Paths: `$EB` is the editbay root, the folder holding `skills/` and `tools/` (`../..` from this skill's folder). Tools run as `uv run $EB/tools/<tool>.py`.

## 1. Scaffold

```bash
uv run $EB/tools/hf_scaffold.py --beats beats/beats.resolved.json --brand BRAND.json --out hf/ \
  --audio sound/mix.wav [--base media/talk.mp4] [--background grid] [--captions cut/words.cut.json] [--hud "LABEL"]
```

It runs `hyperframes init` if needed, copies media into `hf/assets/`, writes `hf/index.html` (one element per cue,
id = cue id, timed with `data-start`/`data-duration`), and copies the beat sheet's motion sidecar next to it. Brand
tokens become CSS variables; `--hud` only when the brand allows HUD numbers. Audio is the finished mix from
sound-bed (the base video is muted), so loudness is decided in one place.

**Done when:** `hf/index.html` exists and `npx hyperframes lint hf/` reports no errors.

## 2. Dress the scenes

Keep the scaffold's timing; change the look. Replace defaults where the idea needs a custom scene (`kind: custom`
cues carry their own `html` and `js`, with `S` and `E` bound to the cue's start and end). House rules and the
gotchas that each cost a re-render: [references/hyperframes-notes.md](references/hyperframes-notes.md). Patterns for
the common overlays (glass cards beside a face, word highlights, pip face-cam, split whiteboard, step rails, HUD
frames, end cards): [references/overlay-patterns.md](references/overlay-patterns.md).

**Done when:** every cue's scene says its idea at a glance, and every flourish you added is in the beat sheet with
`"origin": "agent"`.

## 3. Check before rendering

```bash
npx hyperframes check hf/ --json --at-transitions
npx hyperframes snapshot hf/ --at 1.2,4.8,9.5 --describe false
```

`check` runs lint, runtime, layout, contrast, and the motion sidecar in one pass. Fix errors in the HTML; mark
intentional overlaps with the escape-hatch attributes and a comment. Snapshots at hero moments are the cheap look
before a render; read them together.

**Done when:** `check` exits 0 and the hero snapshots look like the plan.

## 4. Render drafts, then the master

```bash
cd hf && npx hyperframes render --fps 60 --quality draft -o ../renders/draft.mp4       # iterate
cd hf && npx hyperframes render --fps 60 --quality high -o ../renders/review.mp4       # to render-verify
```

Drafts for iteration, `high` for review and delivery; `--docker` when the render must match another machine
bit-for-bit. Masters above 1080p (4K for YouTube): render at the master size, then make the review copy by
downscaling, never the reverse. Motion blur, ProRes 4444, and alpha overlays: see the notes.

**Done when:** `renders/review.mp4` exists at the profile's size and fps, and render-verify has it.

## Checklist

- [ ] Scaffolded from the resolved beat sheet; motion sidecar beside the composition
- [ ] Scenes dressed; agent flourishes recorded in the beat sheet
- [ ] `hyperframes check` clean; hero snapshots read (with `--describe false`)
- [ ] Review render at the delivery profile handed to render-verify
