---
name: footage-intake
description: Bring sources into an edit project and look at them before editing. Downloads at full quality (yt-dlp through the configured download host and browser cookies, including X/Twitter posts), inventories every file (frame rate, colour tags, audio streams, warnings), conforms problem files, extracts 16 kHz audio, and builds contact sheets and cut lists; indexes big folders of recordings by transcript. Use when given a video file, a URL, a folder of recordings, or event footage to edit, analyse, or pull clips from.
---

# Footage intake

Nobody edits footage they have not looked at. Intake turns "here are some files" into an inventory, sheets you can
read at a glance, and audio ready for transcription, with every warning resolved or written down.

Paths: `$EB` is the editbay root, the folder holding `skills/` and `tools/` (`../..` from this skill's folder). Tools run as `uv run $EB/tools/<tool>.py`.
Download host and cookie arguments come from `~/.config/editbay/config.json` (`downloads`).

## 1. Fetch

- Local files: reference them in place (large media stays out of git); copy only what you will modify.
- URLs: run yt-dlp on the configured download host with its cookie arguments, then copy the file over. Full-quality
  YouTube formats often 403 without a signed-in browser's cookies; X posts need them for most videos.

```bash
yt-dlp --cookies-from-browser firefox -f "bv*[height<=1080][vcodec^=avc1]+ba[ext=m4a]/bv*+ba/b" \
  --merge-output-format mp4 --write-info-json -o "%(uploader_id)s_%(id)s.%(ext)s" URL
```

Add `--write-auto-subs --sub-langs en,en-orig --sub-format vtt` for YouTube (a third source for transcript-reconcile).
Record the URL, uploader, date, and licence situation in `media/SOURCES.md`: third-party footage is reference
material unless its licence says otherwise.

**Done when:** every source is on disk with its info JSON (for URLs) and a line in `media/SOURCES.md`.

## 2. Inventory

```bash
uv run $EB/tools/media_probe.py media/ --json media/inventory.json --md media/INVENTORY.md
```

Resolve every warning: variable frame rate (conform to CFR), untagged colour (tag bt709 on re-encode), rotation
metadata, several audio streams (pick one), odd dimensions. Recipes: [references/conform.md](references/conform.md).

**Done when:** `INVENTORY.md` has no unresolved warning; each is fixed or explained in a note under the table.

## 3. Look

- Long talks and recordings: `contact_sheet.py SRC --every 10 --out media/sheets/NAME` (5 s for 5-20 min).
- Edited or motion pieces: `contact_sheet.py SRC --every 0.25` for pieces under 20 s, plus
  `scene_cuts.py SRC --json media/NAME.cuts.json` and `contact_sheet.py SRC --cuts media/NAME.cuts.json`.
- Read the sheets at this phase boundary, all at once; write what you saw in `media/NOTES.md` (who, where, what is on
  screen, where the good moments are, anything that will trip an edit).

**Done when:** every source has a sheet and a paragraph in `NOTES.md`.

## 4. Prepare

- Audio for transcription: `ffmpeg -i SRC -vn -ac 1 -ar 16000 -c:a pcm_s16le media/audio/NAME.wav`.
- Proxies for anything over 1080p or 30 minutes: `ffmpeg -i SRC -vf scale=-2:720 -c:v libx264 -crf 23 -preset fast
  -c:a aac media/proxy/NAME.mp4`; edit decisions on proxies, final renders from sources.
- Faces (talking heads, for overlay placement and vertical reframes): `faces.py SRC --json media/NAME.faces.json`.

**Done when:** every speech source has a WAV, big sources have proxies, talking heads have face zones.

## 5. Big folders

For a folder of hours (an event, a season of streams): inventory everything, transcribe everything
(transcript-reconcile, turbo only for a first pass), then search the transcripts for moments before watching any.
Watch only the candidates, with sheets. Method: [references/big-folders.md](references/big-folders.md).

**Done when:** candidates are listed with timestamps, quotes, and why each matters.

## Checklist

- [ ] Sources on disk, listed in SOURCES.md with origin and licence status
- [ ] Inventory warnings resolved or explained
- [ ] Sheets read and NOTES.md written
- [ ] Audio, proxies, and face zones prepared where needed
