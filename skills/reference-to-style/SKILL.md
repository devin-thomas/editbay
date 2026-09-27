---
name: reference-to-style
description: Turn a video you admire into a reusable style skill. Measures the reference (cut rhythm, tempo and grid discipline, acceleration, palette, loudness, holds), reads it in batched sheets, writes a timed breakdown and the principles that make it work, separates those from the reference's signature, and generates a style-* skill with its own acceptance numbers, then proves it by building one piece with it. Use when asked to make something "like this video", learn a style from a reference, analyse why an edit or reel works, or build a skill around a look.
---

# Reference to style

"Why is this so good?" gets answered with measurements and a named grammar, not adjectives. The output is a skill the
next run can follow and the verifier can hold a render to. The reference is studied, never reused: its media stays out
of every deliverable, and its signature stays with it.

Paths: `$EB` is the editbay root, the folder holding `skills/` and `tools/` (`../..` from this skill's folder). Tools run as `uv run $EB/tools/<tool>.py`.

## 1. Get the reference

Fetch it with footage-intake (downloads through the configured host and cookies; X posts included). Record the URL,
author, date, and what the post claims about how it was made in `reference/SOURCE.md`.

**Done when:** the file is local, probed, and its source is written down.

## 2. Measure

```bash
uv run $EB/tools/reference_report.py REF.mp4 --out reference/NAME/
```

It writes `MEASUREMENTS.md` (shots, flashes, cuts by third, longest shots, detected tempo, cut-to-grid residuals after
removing the detector's constant lag, loudness, holds, palette with colour roles) and the sheets to read. Treat tempo
by ear too: detectors halve or double it, and the reference's own on-screen claims (a HUD saying 128 BPM) are evidence.

**Done when:** `MEASUREMENTS.md` exists and the tempo is confirmed or corrected.

## 3. Read and break down

Read the overview sheets and cut strips in one batch. Write `reference/NAME/BREAKDOWN.md`: a timeline table (time,
chapter, what happens, how it hands off), then "what makes it work" as numbered principles, each with its number from
the measurements, then "signature to leave with the reference". Format and a worked example:
[references/breakdown-guide.md](references/breakdown-guide.md).

**Done when:** every second of the reference is in the timeline, every principle cites a measurement or a timestamp,
and the signature list names what a copy would give away.

## 4. Generate the style skill

Create `skills/style-<name>/` from [references/style-skill-template.md](references/style-skill-template.md): the
grammar (principles restated as rules with numbers), a planning recipe (bars or beats to chapters), a chapter or scene
library written for any brand, sound rules, brand adaptation (what to drop when a brand forbids a device), and
acceptance numbers render-verify can check. Link the breakdown as its source of truth. Add it to `plugin.json` and the
README table; run `scripts/validate.py`.

**Done when:** the new skill validates and every rule in it traces to the breakdown.

## 5. Prove it

Build one piece with the new style in a real brand (beat-sheet, sound-bed, motion-build, render-verify). Compare the
render's measurements with the style's acceptance numbers (`reference_report.py` on your own render works). Every
deviation is either fixed or written into the style as a rule change through skill-retro.

**Done when:** one render passes the style's acceptance numbers and render-verify, and the deviations are logged.

## Checklist

- [ ] Source recorded; reference media kept out of deliverables
- [ ] Measurements taken; tempo confirmed by ear
- [ ] Breakdown: full timeline, principles with numbers, signature named
- [ ] Style skill generated, validated, registered
- [ ] One proof piece measured against the style's acceptance numbers
