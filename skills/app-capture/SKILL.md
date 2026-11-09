---
name: app-capture
description: Capture real app footage for an edit as scripted performances on the iOS Simulator (iPhone and iPad) with the song playing in the app, synced to the soundtrack by the app's own Now Playing clock. Covers the stage (dark, 9:41 status bar, a fresh build), an XCUITest performer that fires taps, flings, typing and play/pause on song time, recording takes, frame-exact alignment of simulator video, sync measurement, touch overlays from the event log, and the pitfalls that cost re-takes. Use when a trailer, sizzle reel, app promo, demo, or music video needs genuine product UI (not mock-ups), especially when the app itself plays the music.
---

# App capture

The product is the proof: film the real app doing the real thing, and let the app's own clock prove the footage and
the soundtrack are the same moment. A performance is a UI test that plays the song in the app and then acts on song
time, so a fling can land on the drop and a pause on the last beat.

Paths: `$EB` is the editbay root, the folder holding `skills/` and `tools/` (`../..` from this skill's folder). Tools run
as `uv run $EB/tools/<tool>.py`. The performer template is in [assets/driver/](assets/driver/).

## 1. Set the stage

- Build the app you are filming fresh and install it on each simulator (`xcrun simctl install <udid> App.app`); note the
  commit. Fix brand bugs you notice before filming (a sheet that ignores the accent colour, a 100 px hero image):
  filming a bug makes it canon.
- Appearance and status bar: `xcrun simctl ui <udid> appearance dark` and
  `xcrun simctl status_bar <udid> override --time "9:41" --batteryState charged --batteryLevel 100 --wifiBars 3 --cellularBars 4`.
  Clear the overrides when done.
- Devices: an iPhone in portrait and an iPad in landscape (sidebar layouts only appear there). Know where the app's icon
  sits on the home screen if a shot uses it; the test runner installs its own icon there (patch it in the edit with a
  crop of the same wallpaper slot taken with the runner uninstalled).

**Done when:** both simulators show the current build, dark, at 9:41, and the song plays in the app by hand.

## 2. Write the performance

Copy `assets/driver/` into the project (`driver/`), set `APP_BUNDLE_ID`, adapt `startSong()` to the app's path to the
track, and write one `testTake…` per take from the edit's beat sheet: the shots you need, each at a song time.
The base class skips XCTest's idle waits (without this every gesture lands 1-2 s late while music plays), logs every
action, schedules with `at(song_seconds)`, and refines song zero from the Now Playing clock. Patterns, helpers and the
traps that cost takes: [references/performance-driver.md](references/performance-driver.md).

**Done when:** each needed shot has a scheduled action in a take, and a dry run passes (`xcodegen generate`, then a probe
test printing `app.debugDescription` for the screens you touch).

## 3. Record takes

```bash
cd driver && ./take.sh <udid> A1 Takes/testTakeBookends      # -> takes/A1.mov, .clock, .events, .xcodebuild.log
```

Record several takes cheaply (each is ~1 min) instead of fixing one: a take that drifted or hit the wrong element is
evidence for the next. Contact-sheet every take (`contact_sheet.py takes/A1.mov --every 1.5`) and read it before syncing.

**Done when:** every shot in the beat sheet exists in some take, looked at on a sheet.

## 4. Sync and align

```bash
uv run $EB/tools/sim_take.py sync takes/A1.mov --roi X,Y,W,H --start A --end B --thr 0.5   # offset = video - song
uv run $EB/tools/sim_take.py align takes/A1.mov --offset 23.618 --lead 3 --duration 41 --all-intra --out hf/assets/takes/A1.mp4
uv run $EB/tools/sim_take.py events --clock takes/A1.clock --events takes/A1.events --offset 23.618 --json takes/A1.touch.json
uv run $EB/tools/sim_take.py changes takes/A1.mov --roi X,Y,W,H --start A --end B --offset 23.618   # exact pause frame
```

Sync on a window where Now Playing is settled (not while the sheet animates), in each Now Playing window of the take
(a streaming stall shows up as a changed offset). Never convert simulator video with a plain `trim`: the recordings are
sparse VFR with DTS far behind PTS and a naive cut shifts content 0.8-2.7 s early. Details and the segment math the
edit uses (synced vs anchored segments): [references/sync-and-align.md](references/sync-and-align.md).

**Done when:** every take has an offset with spread under 0.07 s, an aligned constant-fps file, and a touch JSON.

## 5. Hand to the edit

The composition places segments from the aligned files: a **synced** segment (any shot where a clock, progress bar or
counter is visible) uses file time = trailer time - song start + lead; an **anchored** segment pins a logged event to a
beat. Touch indicators come from the touch JSON, drawn 0.09 s after each logged call. After render, run the sync gate:
OCR the in-app clock or listen counter off rendered frames and compare with the soundtrack.

**Done when:** the render's sync gate passes on every Now Playing shot, and the touch overlays sit on real taps.

## Checklist

- [ ] Fresh build, dark, 9:41, brand bugs fixed before filming
- [ ] Performer skips quiescence; takes schedule on song time; events logged
- [ ] Takes looked at on sheets; runner icon patched if the home screen shows
- [ ] Offsets measured on the app's clock; aligned with `sim_take.py align`, never a naive trim
- [ ] Synced segments for any visible clock; sync gate passes on the render
