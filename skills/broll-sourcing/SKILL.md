---
name: broll-sourcing
description: Source the images, clips, logos, and screen captures an edit needs, with provenance for every file. Captures first (site captures, screenshots, scroll pans built from full-page captures, own recordings), then official brand assets, then licensed stock, then generation, local before paid; every file recorded in a ledger with source, licence, and on-screen label, and gated before render. Use when an edit needs B-roll, screenshots, screen recordings, logos, stills, generated images or clips, or "proof on screen" for a claim.
---

# B-roll sourcing

Proof beats illustration. When the narration makes a claim, the best B-roll is the real thing captured; an official
asset comes next; stock and generation fill gaps and say what they are. Every file on screen has a ledger entry, and
the gate fails the build when one does not.

Paths: `$EB` is the editbay root, the folder holding `skills/` and `tools/` (`../..` from this skill's folder). Tools run as `uv run $EB/tools/<tool>.py`.
Paid providers, their costs, and the free routes on our machines: `$EB/docs/PROVIDERS.md`.

## 1. List what each cue needs

From the beat sheet, list every cue that shows media: what it must prove or illustrate, its zone and size, how long it
holds, and whether it is a capture of something real or an illustration. Write the list in `assets/NEEDS.md`.

**Done when:** every media cue has a need, a size, and "real" or "illustration" marked.

## 2. Capture the real things

- Websites and apps: `uv run $EB/tools/hf.py capture URL --skip-vision -o assets/capture/NAME` (screenshots, assets,
  video manifest; `--skip-vision` keeps frames from being sent to an AI captioner). A "screen recording" of a page is
  usually better built than recorded: pan a full-page capture in the composition (seek-safe, sharp, re-timeable).
- Real screen recordings (a terminal, an app flow): record at the delivery size or larger, 60 fps, a tight viewport so
  text reads inside a card (1280 px wide pages read well in a half-frame card).
- Games and hardware: the creator's capture tools (OBS, emulator captures); label emulator footage as such.
- Contact-sheet every capture before using it (`contact_sheet.py`); a capture nobody looked at is not B-roll yet.

**Done when:** every "real" need has a capture, looked at, recorded in the ledger as `capture`.

## 3. Official assets, then stock

Logos and product imagery from the owner's press or brand page (record the page and terms), used as the owner allows:
unaltered colours, clear space, no implied endorsement. Stock from licensed libraries (Pexels, Pixabay, Mixkit): record
the licence per file. Brand rules win: a brand that forbids stock footage gets captures or motion instead.

**Done when:** each official or stock file has a licence or terms note in the ledger.

## 4. Generate what cannot be captured

Local first: HyperFrames motion on stills (parallax, camera moves, masks) covers most "moving B-roll"; local image
models on the GPU host or the Mac when an illustration is needed. Paid generation (Seedream, Nano Banana, Kling, Veo via
kie.ai; Gemini) only with a cost estimate approved in `HUMAN_QUEUE.md`; two attempts per asset, then change the plan.
Generated media is an illustration: label it on screen when it could be mistaken for a capture, never present it as
evidence. Kling-style 24 fps clips: re-encode all-intra at the render fps before placing them (seek-safe). Details:
[references/sourcing-notes.md](references/sourcing-notes.md).

**Done when:** every generated file is in the ledger with its prompt, tool, cost, and label (or the reason it needs none).

## 5. Gate

```bash
uv run $EB/tools/asset_ledger.py check assets/ledger.json --composition hf/
# If unused templates are copied into hf/, add an explicit ignore:
uv run $EB/tools/asset_ledger.py check assets/ledger.json --composition hf/ --ignore 'brand/shell/snippets/**'
```

The ledger follows files the composition actually loads; nested `url()` references inside a `data:` SVG are not media.
Use an explicit ignore glob for unused example/snippet files and record the reason in the QA notes.

**Done when:** the check exits 0: every file the composition uses has provenance, licences where needed, and labels
on generated media.

## Checklist

- [ ] Needs listed per cue, real vs illustration
- [ ] Captures first, each looked at on a sheet
- [ ] Official and stock assets with licence notes; brand rules respected
- [ ] Generation local first; paid only with an approved estimate; labelled
- [ ] Ledger gate passes before render
