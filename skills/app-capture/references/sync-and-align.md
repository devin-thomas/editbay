# Sync and align

## Why the app's clock is the best sync signal

An AVPlayer-based app updates its elapsed label from a 1 s periodic time observer, which fires when the item time
crosses each whole second. So the frame where "0:29" becomes "0:30" is song time 30.000 s (plus ~1 display frame).
Detect label changes in a small region, OCR the changed frames, and every tick gives `offset = video_time - seconds`.
Measured on five takes: 3-6 ms spread across ticks; the first two ticks after a sheet opens are unreliable (the sheet
is still moving) and are outliers. Also check each later Now Playing window in the same take: a streaming stall shows
up as a changed offset (none happened in 2026-09-29's takes, but one take showed 0.16 s until re-recorded).

Region of interest: the elapsed label under the progress bar. iPhone 17 (1206×2622 px): `30,2040,200,55` with `--thr 0.5` (some digit changes move the region by less than 1.5 grey levels; 0.5 caught all seven ticks in a window). iPad Pro 13"
landscape form sheet (2752×2064 px after rotation): `800,1370,120,40` with `--thr 0.3` (small text changes few pixels).

The system audio path (a loopback input on the interface) was silent without a routing change, so the soundtrack is the
same file the app streams, and sync comes from the clock, not from recorded audio. Changing the machine's audio routing
is the owner's call.

## Why a plain cut is wrong

`simctl io recordVideo` writes HEVC with a frame only when the screen changes (sparse VFR: frames seconds apart on a
static screen, 120 Hz during scrolls) and DTS up to ~3 s behind PTS. Two ffmpeg defaults then shift content early:
- `trim=start=X,setpts=PTS-STARTPTS` starts at the next *existing* frame after X and calls it zero;
- a plain decode (no `-ss`) uses DTS-driven best-effort timestamps.
Measured on take E2: the clock read 0:31 where the soundtrack was at 0:30; around song 26-31 s the naive path ran 2.0-2.7 s early (the DTS-driven decode alone 1.8-2.5 s, the trim alone a constant 0.82 s when the start fell in a gap). The fix (what
`sim_take.py align` does): decode on PTS (`-fflags +igndts`), make the whole take constant-rate first (`fps=60`: a frame
holds until the next change), then cut by frame index. Verified: the clock flips between 54.20 and 54.23 s, true tick
54.217 s. Encode all-intra (`-g 1`) at the render rate so HyperFrames seeks cleanly, tagged `-colorspace bt709`.

## Segment math for the edit

With aligned files where `file_time = song_time + LEAD` and the song starting at trailer time `PRE`:
- **synced** segment (a clock, progress bar, listen counter or lyric-visible screen): `media_start = T0 - PRE + LEAD`;
- **anchored** segment (a tap pinned to a beat): `media_start = s_event + TOUCH + LEAD + (T0 - T_anchor)`, where
  `s_event` comes from the event log (not the test's own clock: they differ by a few ms, enough to drop a tap that sits
  on a segment's first frame) and `TOUCH` ≈ 0.09 s.
- A touch at song time `s` inside a segment shows at `T0 + (s + TOUCH - s0)`, `s0 = media_start - LEAD`. Draw a 44 pt
  soft white circle with a thin ring (Apple-demo style), fade in 0.07 s, expand and fade by 0.5 s; drags as a dot moving
  from start to end over the logged duration.

## The sync gate on the render

Sample frames where a Now Playing is on screen, OCR the frame in overlapping tiles at 2× (a clock is ~11 px tall in a
device frame at 1080p), and pass when the clock equals floor(T - PRE) or the listen counter is within 1 s. Skip frames
mid-transition. The 2026-09-29 draft passed 9 of 10 samples; the tenth was a morphing frame where OCR read nothing.
