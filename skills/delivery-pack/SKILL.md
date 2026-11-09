---
name: delivery-pack
description: Package a verified edit for delivery. Renders the variants the delivery profile asks for (4K master from the 1080p composition, the review copy, a re-laid-out vertical cut), measures each delivered file, and assembles captions, chapters that meet YouTube's rules, thumbnail candidates, a description draft with disclosures and credits, and a manifest with hashes and loudness. Use when a video is ready to hand off, upload, publish, archive, or cut down for Shorts or Reels; after render-verify passes. Uploading is a human step.
---

# Delivery pack

The last step is where small lies creep in: a master nobody measured, captions from a raw transcript, a missing
disclosure. Deliver only files that were measured as delivered, with a manifest that proves which is which.

Paths: `$EB` is the editbay root, the folder holding `skills/` and `tools/` (`../..` from this skill's folder). Tools run as `uv run $EB/tools/<tool>.py`.
Delivery profiles come from `~/.config/editbay/config.json` (`delivery_profiles`).

## 1. Render the variants

- **Master above 1080p:** render the same composition at a higher device scale; the layout does not change:
  `uv run $EB/tools/hf.py render --fps 60 --quality delivery --resolution landscape-4k -o renders/master-4k.mp4`.
- **Vertical (9:16):** re-lay out, never crop a designed piece. Scaffold a second project from the same resolved beat
  sheet: `hf_scaffold.py ... --out hf-vertical --size 1080x1920 --remap left=upper,right=lower` plus a vertical CSS
  override (rails wrap, cards widen), then `hyperframes check` and render. Footage-led pieces can reframe on the face
  instead (`faces.py` gives a 9:16 crop path).
- **Alpha overlays** for another editor: `--format mov` (ProRes 4444).

**Done when:** every variant the profile names exists and `hyperframes check` passed on each composition.

## 2. Measure what ships

For each file: `av_qa.py FILE --expect-size WxH --expect-fps F --expect-duration D` and
`loudness.py FILE --target T --tp -1.0` on the encoded file. A variant that differs from the review render in
anything but size gets its own look (a sheet at the hero moments).

**Done when:** every delivered file passes both, at the profile's size, rate, and loudness.

## 3. Package

```bash
uv run $EB/tools/deliver.py --out deliver/ --slug SLUG --file master-4k=... --file review-1080p=... --file vertical=... \
  --words FINAL_WORDS.json --beats beats/beats.resolved.json --thumb-from renders/review.mp4 --thumb-at T1,T2,T3 \
  --asset designed-thumb=thumb.jpg --asset cover=cover.jpg \
  --title "..." --summary "..." --disclosure "..." --credit "Music: ..."
```

Captions come from the verified word timings (never a raw pass). Chapters are written only when they meet YouTube's
rules (first at 0:00, at least three, each at least 10 s); otherwise the tool says why. Thumbnails are three frame
candidates, A/B/C, with no pick: the creator picks, or a designed thumbnail replaces them. The description draft
carries the voice disclosure when a cloned voice narrates, and credits for music and generated media. Use repeatable
`--asset VARIANT=PATH` for designed thumbs, covers, and other first-class image deliverables; the tool records their
hashes and pixel dimensions. Use `--asset-name VARIANT=FILENAME` when the public basename is part of the brief; this
avoids staging a source file solely to control its name. After any wrap-only or hyphen-join correction, inspect the
emitted SRT and VTT, enforce the 42-character line limit, and refresh manifest hashes. The ledger and delivery helpers
live under `$EB/tools`; EditorialPipeline stock and platform helpers live under `$CB/tools` and `$CB/publish`.
Platform details: [references/platform-specs.md](references/platform-specs.md).

**Done when:** `deliver/DELIVERY.md` lists every file with its spec and measured loudness, and `manifest.json` has a
SHA-256 for each.

## 4. Hand off

Point the brief at `deliver/`. Publishing, uploading, or scheduling is the creator's call: say what is ready and
stop. Media stays out of git; the records (`DELIVERY.md`, `manifest.json`, captions) can go in.

**Done when:** the creator has the folder path and a one-paragraph summary of what is in it and what was checked.

## Checklist

- [ ] Variants rendered as the profile asks; vertical re-laid out, not cropped
- [ ] Every delivered file measured (spec and loudness) as delivered
- [ ] Captions from verified words; chapters valid or explained; disclosure and credits in the description
- [ ] Caption lines are checked after assembly; hyphenated compounds remain joined
- [ ] Designed image assets are copied, dimensioned, and hashed in the manifest; publishing left to the creator
