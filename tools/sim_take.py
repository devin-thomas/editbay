#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10,<3.14"
# dependencies = [
#   "numpy",
#   "pyobjc-framework-Vision; sys_platform == 'darwin'",
#   "pyobjc-framework-Quartz; sys_platform == 'darwin'",
# ]
# ///
"""iOS Simulator screen recordings (`xcrun simctl io <udid> recordVideo`) synced to the song the app is playing.

Subcommands:
  sync TAKE.mov --roi x,y,w,h --start A --end B [--thr 1.5] [--json sync.json]
      The take's song offset from the app's own Now Playing elapsed clock: offset = video time - song time.
      Decodes the ROI (the elapsed label) with true PTS, keeps frames whose mean absolute difference from the
      previous frame exceeds --thr, OCRs them (2x upscale, macOS Vision), and turns every new "m:ss" reading into a
      sync point. Prints the median offset, its spread (p90 - p10) and every tick. Exit 1 "no ticks" when nothing
      matched. Pick a window where Now Playing is on screen; a lower --thr catches more ticks (see below).
  align TAKE.mov --offset S [--lead 3.0] [--song-start 0] --duration 41 --out OUT.mp4 [--fps 60] [--crf 15]
        [--all-intra]
      A song-aligned constant-fps H.264 copy, no audio: file time = song time - song-start + lead. --all-intra
      makes every frame a keyframe (-g 1) for frame-exact seeking in a browser composition. Exit 1 if the take ends
      before the requested duration.
  changes TAKE.mov --roi x,y,w,h --start A --end B [--offset S] [--thr 0.8] [--json out.json]
      Every frame where a region changes (video time, and song time with --offset): the exact frame a pause icon
      flips or a sheet lands. "mean" is the region's brightness after the change. Exit 1 when nothing changes.
  events --clock takes/NAME.clock --events takes/NAME.events --offset S [--json events.json]
      The driver's EVT log in song time (song = wall - recording-start wall - offset); X.start/X.end pairs become
      drags, events at 0,0 (buttons, markers) become marks. x/y stay in points: multiply by the device scale.
Exit codes: 0 ok, 1 a failed gate (above), 2 cannot run (not macOS for sync, bad ROI or input, ffmpeg error).

Inputs: the driver writes takes/NAME.clock (a "rec <wall> Recording started" line from simctl's stderr) and
takes/NAME.events (`EVT wall=<unix> song=<test clock> <name> x=<pt> y=<pt>`). ROIs are in displayed pixels:
ffmpeg applies the take's rotation first (an iPad take recorded in landscape decodes landscape).

Why sync works: the app's elapsed label is driven by a 1 s periodic AVPlayer time observer, so it changes exactly
when playback crosses each whole second, and every "0:NN" change is a sync point. A tick is a reading higher than
the previous reading in the same run of readable change frames; the run's first reading (the window's opening
state, or a label sliding in with a sheet) is not a tick, and an unreadable frame ends the run. Settled ticks agree
within 2-6 ms, and across a take's separate Now Playing windows; ticks while a sheet animates can land 10-35 ms
late, which the median absorbs. The mean-difference threshold matters: on E2's ROI the 0:25->0:26 change is 0.82
and 0:28->0:29 is 1.44, so the default 1.5 skips those two ticks (--thr 0.5 finds all seven, 0:25-0:31).

Why align is written this way: simctl HEVC recordings are sparse VFR (a frame only when the screen changes) with
DTS up to ~3 s behind PTS. A plain decode uses DTS-driven best-effort timestamps, and `trim=start=X` starts at the
next *existing* frame; both shift content early. So decode on PTS (`-fflags +igndts`), make the whole take
constant fps first (a frame holds until the next screen change), then cut by frame index:
N0 = round((offset + song_start - lead) * fps).

Measured 2026-09-29 on the Demo Artist trailer takes (macOS 27, ffmpeg 9.0.2):
  sync E2.mov (iPhone) --roi 30,2040,200,55 --start 48.5 --end 55.4: offset 24.217 s, spread 0.006 s, 5 ticks
    (0:25 read mid-animation at +6 ms; the rest 24.215-24.217).
  sync C4.mov (iPad, landscape) --roi 800,1370,120,40 --start 26.8 --end 32.5 --thr 0.3: offset 24.937 s,
    spread 0.025 s (0:03 and 0:04 land 13 and 33 ms late while the sheet settles). The take's later window
    (0:25-0:31) gave 24.937 too.
  sync E2.mov, same ROI, --start 35 --end 40 (no Now Playing; OCR reads "When", lyric fragments): exit 1 no ticks.
  align E2.mov --offset 24.217 --lead 3 --song-start 28 --duration 8 --all-intra: OCR of the output reads 0:29 at
    frame 299 and 0:30 at frame 300 (file 5.000 s = song 30.000), 0:30 at 359 and 0:31 at 360; sync on the
    output: six ticks 0:26-0:31 at 1.000 ... 6.000 s, offset -25.000 (= lead - song-start), spread 0.000.
    Negative control, the naive `-i TAKE -vf trim=start=49.217,setpts=PTS-STARTPTS,fps=60`: reads 0:31 from frame
    298 to 361 (song 29.97-31.02); its ticks run 2.0 s early, then 0.65 s apart (2.7 s early by 0:31).
    Each cause alone: the DTS decode with the correct fps-first cut is 1.8-2.5 s early and uneven; trim-first on
    PTS is exact here but at --song-start 29.033 (X = 50.25, inside a 50.215 -> 51.072 frame gap) runs a constant
    0.817 s early, where align stays exact (offset -26.033, spread 0). The run's retro had 0.2-1.4 s.
  changes E2.mov --roi 538,2183,130,130 --start 55.2 --end 56.0 --offset 24.217: the pause icon flips at video
    55.530 = song 31.313 (diff 47.1), then fades up for ~0.4 s. Same ROI at 60.0-61.5 (static): exit 1.
  events E2 --offset 24.217: nowplaying.pause at song 31.197 (the UI test's own clock said 31.216); the icon
    flips 0.116 s after the tap.
"""
import argparse, json, re, statistics, subprocess, sys

import numpy as np

# m:ss; Vision sometimes reads the colon of a label mid-animation as a bullet or a dot (E2: "0•24").
CLOCK = re.compile(r"(\d+)[:•·.;](\d\d)")


def die(msg):
    """Cannot run (bad input, missing platform, ffmpeg error): exit 2, distinct from a failed gate (exit 1)."""
    print(msg, file=sys.stderr)
    sys.exit(2)


def roi_of(text):
    try:
        x, y, w, h = (int(v) for v in text.split(","))
    except ValueError:
        raise argparse.ArgumentTypeError("ROI is x,y,w,h in pixels")
    return x, y, w, h


def decode_roi(video, roi, start, end):
    """Grayscale ROI frames with their true presentation times (VFR kept: one row per recorded frame)."""
    x, y, w, h = roi
    # ffmpeg's crop silently clamps an ROI that leaves the frame, so check it against the displayed size.
    probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                            "stream=width,height:stream_side_data=rotation", "-of", "json", video],
                           capture_output=True, text=True)
    try:
        stream = json.loads(probe.stdout)["streams"][0]
    except (ValueError, KeyError, IndexError):
        die(f"ffprobe cannot read {video}: {probe.stderr.strip()}")
    fw, fh = stream["width"], stream["height"]
    if any(abs(sd.get("rotation", 0)) % 180 == 90 for sd in stream.get("side_data_list", [])):
        fw, fh = fh, fw
    if x < 0 or y < 0 or w < 1 or h < 1 or x + w > fw or y + h > fh:
        die(f"ROI {x},{y},{w},{h} is not inside the {fw}x{fh} displayed frame")
    # Gray before crop: a crop on 4:2:0 frames rounds odd sizes and offsets to even (55 rows became 54).
    cmd = ["ffmpeg", "-nostdin", "-hide_banner", "-v", "info", "-ss", str(start), "-to", str(end), "-copyts",
           "-i", video, "-vf", f"format=gray,crop={w}:{h}:{x}:{y},showinfo", "-fps_mode", "passthrough",
           "-f", "rawvideo", "-"]
    p = subprocess.run(cmd, capture_output=True)
    err = p.stderr.decode(errors="replace")
    size = re.search(r" s:(\d+)x(\d+) ", err)
    if size and (int(size.group(1)), int(size.group(2))) != (w, h):
        die(f"ffmpeg cropped {size.group(1)}x{size.group(2)}, not {w}x{h}: is the ROI inside the frame?")
    pts = [float(v) for v in re.findall(r"pts_time:(-?[0-9.]+)", err)]
    frames = np.frombuffer(p.stdout, np.uint8)
    frames = frames[:frames.size // (w * h) * (w * h)].reshape(-1, h, w)
    n = min(len(pts), len(frames))
    if p.returncode or not n:
        die("ffmpeg decoded no frames:\n" + "\n".join(err.strip().splitlines()[-5:]))
    return pts[:n], frames[:n]


def diffs(frames):
    """Mean absolute difference of each frame from the previous one (the first frame has none: NaN)."""
    f = frames.astype(np.int16)
    return np.r_[np.nan, np.abs(f[1:] - f[:-1]).mean((1, 2))]


def upscale2x(frames):
    """Bicubic 2x upscale of gray frames through ffmpeg (small labels OCR far better at 2x)."""
    n, h, w = frames.shape
    p = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-f", "rawvideo", "-pix_fmt", "gray", "-s", f"{w}x{h}",
                        "-i", "-", "-vf", "scale=iw*2:ih*2", "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                       input=frames.tobytes(), capture_output=True)
    if p.returncode:
        die("ffmpeg upscale failed: " + p.stderr.decode(errors="replace").strip())
    return np.frombuffer(p.stdout, np.uint8).reshape(n, h * 2, w * 2)


def vision_ocr(frames):
    """Text in each gray frame via macOS Vision (accurate, no language correction), observations left to right."""
    try:
        import objc, Quartz, Vision
        from Foundation import NSData, NSDictionary
    except ImportError as e:
        die(f"sync needs macOS Vision through pyobjc ({e}); run it with `uv run` on a Mac.")
    texts = []
    for f in frames:
        with objc.autorelease_pool():
            h, w = f.shape
            buf = np.ascontiguousarray(f).tobytes()
            provider = Quartz.CGDataProviderCreateWithCFData(NSData.dataWithBytes_length_(buf, len(buf)))
            image = Quartz.CGImageCreate(w, h, 8, 8, w, Quartz.CGColorSpaceCreateDeviceGray(),
                                         Quartz.kCGImageAlphaNone, provider, None, False,
                                         Quartz.kCGRenderingIntentDefault)
            request = Vision.VNRecognizeTextRequest.alloc().init()
            request.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
            request.setUsesLanguageCorrection_(False)
            handler = Vision.VNImageRequestHandler.alloc().initWithCGImage_options_(image, NSDictionary.dictionary())
            handler.performRequests_error_([request], None)
            found = sorted(request.results() or [], key=lambda o: o.boundingBox().origin.x)
            texts.append(" ".join(str(o.topCandidates_(1)[0].string()) for o in found if o.topCandidates_(1)))
    return texts


def sync(a):
    if sys.platform != "darwin":
        die("sync OCRs with macOS Vision and only runs on macOS; run it on a Mac (align, changes and events "
            "work anywhere).")
    pts, frames = decode_roi(a.video, a.roi, a.start, a.end)
    d = diffs(frames)
    idx = [i for i in range(len(frames)) if i == 0 or d[i] > a.thr]
    texts = vision_ocr(upscale2x(frames[idx]))
    ticks, prev = [], None
    for i, text in zip(idx, texts):
        m = CLOCK.fullmatch(text.replace(" ", ""))
        if not m:
            prev = None  # the label left, or is moving: the next reading starts a new run
            continue
        sec = int(m.group(1)) * 60 + int(m.group(2))
        if prev is not None and sec > prev:
            ticks.append({"video": round(pts[i], 6), "clock": sec, "text": text, "offset": round(pts[i] - sec, 6)})
        prev = sec
    if not ticks:
        print(f"no ticks: {len(idx)} change frames in {a.start}-{a.end} s, none a new m:ss reading")
        sys.exit(1)
    offs = [t["offset"] for t in ticks]
    med = statistics.median(offs)
    spread = float(np.percentile(offs, 90) - np.percentile(offs, 10))
    print(f"ticks {len(ticks)}  offset (video - song) median {med:.3f} s  spread {spread:.3f} s")
    for t in ticks:
        print(f"  video {t['video']:8.3f}  clock {t['text']:>5}  -> offset {t['offset']:.3f}")
    if a.json:
        with open(a.json, "w") as fh:
            json.dump({"video": a.video, "roi": list(a.roi), "window": [a.start, a.end], "offset": round(med, 6),
                       "spread": round(spread, 6), "ticks": ticks}, fh, indent=1)


def align(a):
    n0 = round((a.offset + a.song_start - a.lead) * a.fps)
    count = round(a.duration * a.fps)
    if n0 < 0:
        die(f"file time 0 (song {a.song_start - a.lead:.3f} s) is {-n0 / a.fps:.3f} s before the recording starts; "
            "use a smaller --lead or a later --song-start")
    enc = ["-c:v", "libx264", "-preset", "medium", "-crf", str(a.crf)] + (["-g", "1"] if a.all_intra else [])
    cmd = ["ffmpeg", "-nostdin", "-y", "-v", "error", "-fflags", "+igndts", "-i", a.video, "-vf",
           f"fps={a.fps:g},trim=start_frame={n0}:end_frame={n0 + count},setpts=PTS-STARTPTS,format=yuv420p",
           *enc, "-colorspace", "bt709", "-an", a.out]
    if subprocess.run(cmd).returncode:
        die("ffmpeg failed writing " + a.out)
    got = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries",
                          "stream=nb_read_frames", "-of", "csv=p=0", a.out], capture_output=True, text=True)
    frames = int(got.stdout.strip() or 0)
    print(f"wrote {a.out}: {frames} frames at {a.fps:g} fps from take frame {n0}; "
          f"file 0.000 s = song {a.song_start - a.lead:.3f} s")
    if frames < count:
        print(f"short: expected {count} frames; the take ends at song {a.song_start - a.lead + frames / a.fps:.3f} s")
        sys.exit(1)


def changes(a):
    pts, frames = decode_roi(a.video, a.roi, a.start, a.end)
    d = diffs(frames)
    rows = [{"video": round(pts[i], 6), "song": round(pts[i] - a.offset, 6) if a.offset is not None else None,
             "diff": round(float(d[i]), 2), "mean": round(float(frames[i].mean()), 1)}
            for i in range(1, len(frames)) if d[i] > a.thr]
    for r in rows:
        song = f"  song {r['song']:.3f}" if r["song"] is not None else ""
        print(f"video {r['video']:.3f}{song}  diff {r['diff']:.1f}  mean {r['mean']:.1f}")
    if a.json:
        with open(a.json, "w") as fh:
            json.dump({"video": a.video, "roi": list(a.roi), "window": [a.start, a.end], "offset": a.offset,
                       "changes": rows}, fh, indent=1)
    if not rows:
        print(f"no changes above {a.thr} in {len(frames)} frames")
        sys.exit(1)


def events(a):
    starts = [float(line.split()[1]) for line in open(a.clock) if "Recording started" in line]
    if not starts:
        die(f"{a.clock}: no 'Recording started' line")
    rec = starts[0]
    raw = []
    for line in open(a.events):
        parts = line.split()
        if len(parts) < 3 or parts[0] != "EVT":
            continue
        kv = dict(p.split("=", 1) for p in parts[1:] if "=" in p)
        name = next((p for p in parts[1:] if "=" not in p), None)
        if name is None or "wall" not in kv:
            continue
        raw.append({"name": name, "wall": float(kv["wall"]), "song": round(float(kv["wall"]) - rec - a.offset, 3),
                    "test_song": float(kv["song"]) if "song" in kv else None,
                    "x": float(kv.get("x", 0)), "y": float(kv.get("y", 0))})
    raw.sort(key=lambda e: e["wall"])
    out, open_drags = [], {}
    for e in raw:
        base, _, edge = e["name"].rpartition(".")
        if edge == "start" and base:
            open_drags[base] = e
            continue
        if edge == "end" and base in open_drags:
            s = open_drags.pop(base)
            out.append({"name": base, "kind": "drag", "song": s["song"], "end": e["song"],
                        "from": [s["x"], s["y"]], "to": [e["x"], e["y"]]})
            continue
        kind = "mark" if e["x"] == 0 and e["y"] == 0 else "tap"  # 0,0 = no touch point (button, marker)
        out.append({"name": e["name"], "kind": kind, "song": e["song"], "x": e["x"], "y": e["y"],
                    "test_song": e["test_song"]})
    for s in open_drags.values():  # a start without its end still happened
        out.append({"name": s["name"], "kind": "tap", "song": s["song"], "x": s["x"], "y": s["y"],
                    "test_song": s["test_song"]})
    out.sort(key=lambda e: e["song"])
    for e in out:
        where = (f"({e['from'][0]:.0f},{e['from'][1]:.0f}) -> ({e['to'][0]:.0f},{e['to'][1]:.0f}) until "
                 f"{e['end']:.3f}" if e["kind"] == "drag" else f"({e['x']:.0f},{e['y']:.0f})")
        print(f"song {e['song']:8.3f}  {e['kind']:<4}  {e['name']:<28} {where}")
    if a.json:
        with open(a.json, "w") as fh:
            json.dump({"clock": a.clock, "events_log": a.events, "recording_start_wall": rec, "offset": a.offset,
                       "events": out}, fh, indent=1)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sync"); s.add_argument("video"); s.add_argument("--roi", type=roi_of, required=True)
    s.add_argument("--start", type=float, required=True); s.add_argument("--end", type=float, required=True)
    s.add_argument("--thr", type=float, default=1.5, help="mean abs diff (0-255) that counts as a change")
    s.add_argument("--json")
    al = sub.add_parser("align"); al.add_argument("video"); al.add_argument("--offset", type=float, required=True)
    al.add_argument("--lead", type=float, default=3.0, help="seconds of take before song-start")
    al.add_argument("--song-start", type=float, default=0.0, help="song time that sits at file time = lead")
    al.add_argument("--duration", type=float, required=True); al.add_argument("--out", required=True)
    al.add_argument("--fps", type=float, default=60); al.add_argument("--crf", type=int, default=15)
    al.add_argument("--all-intra", action="store_true", help="every frame a keyframe (-g 1), for seek-heavy use")
    c = sub.add_parser("changes"); c.add_argument("video"); c.add_argument("--roi", type=roi_of, required=True)
    c.add_argument("--start", type=float, required=True); c.add_argument("--end", type=float, required=True)
    c.add_argument("--offset", type=float); c.add_argument("--thr", type=float, default=0.8)
    c.add_argument("--json")
    e = sub.add_parser("events"); e.add_argument("--clock", required=True); e.add_argument("--events", required=True)
    e.add_argument("--offset", type=float, required=True); e.add_argument("--json")
    a = ap.parse_args()
    {"sync": sync, "align": align, "changes": changes, "events": events}[a.cmd](a)


if __name__ == "__main__":
    main()
