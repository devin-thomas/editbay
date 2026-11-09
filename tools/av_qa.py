#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy", "soundfile"]
# ///
"""Objective QA on a rendered file: the defects eyes miss in a quick watch.

Checks: container/stream facts against expectations; black frames; frozen frames; silences; audio pops
(sample jumps far above the local norm, typical at bad joins); audio/video duration mismatch.

Usage:
           av_qa.py RENDER.mp4 [--expect-fps 60] [--expect-size 1920x1080] [--expect-duration 15.0]
           [--allow-black 0:0.5] [--allow-freeze 12.0:14.5] [--require-content-ends]
           [--min-silence 0.8] [--json qa.json] [--md qa.md]
Content ends (measured 2026-09-27): the Muse run's 9:16 and 16:9 deliveries open on a bare background (edge density
0.0, foreground share 0.0) and fail; a EditorialPipeline hook frame measures edge density 0.074 and passes. Floors: 0.0005 edge
density and 0.005 foreground share.
--allow-* take start:end ranges (comma-separated) where black/freeze is intentional (a fade-from-black open,
a held end card). Black frames, pops, and spec mismatches are errors (exit 1); long holds and silences are
warnings; short holds are notes. Dark designs: keep --black-ratio at 0.998+ or every minimalist frame reads black.
"""
import argparse, json, re, subprocess, sys, tempfile, os

import numpy as np


def run(args):
    return subprocess.run(args, capture_output=True, text=True)


def ranges(spec):
    out = []
    for part in (spec or "").split(","):
        if part.strip():
            s, e = part.split(":"); out.append((float(s), float(e)))
    return out


def allowed(s, e, allow):
    return any(s >= a - 0.05 and e <= b + 0.05 for a, b in allow)


def probe(path):
    d = json.loads(run(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", path]).stdout)
    v = next((s for s in d["streams"] if s["codec_type"] == "video"), None)
    au = next((s for s in d["streams"] if s["codec_type"] == "audio"), None)
    num, den = (v["r_frame_rate"].split("/") if v else ("0", "1"))
    return {"duration": float(d["format"]["duration"]),
            "video": {"codec": v["codec_name"], "size": f"{v['width']}x{v['height']}", "fps": round(float(num) / float(den), 3),
                      "pix_fmt": v.get("pix_fmt"), "duration": float(v.get("duration", 0) or 0),
                      "color_primaries": v.get("color_primaries")} if v else None,
            "audio": {"codec": au["codec_name"], "sample_rate": int(au["sample_rate"]), "channels": au["channels"],
                      "duration": float(au.get("duration", 0) or 0)} if au else None}


def intervals(err, key):
    s = [float(x) for x in re.findall(rf"{key}_start:\s*(-?[\d.]+)", err)]
    e = [float(x) for x in re.findall(rf"{key}_end:\s*(-?[\d.]+)", err)]
    return list(zip(s, e + [None] * (len(s) - len(e))))


def read_frame(path, timestamp, width=256):
    """Read one scaled RGB frame so the content gate stays independent of image packages."""
    r = subprocess.run(
        ["ffmpeg", "-nostdin", "-hide_banner", "-v", "error", "-ss", f"{timestamp:.3f}", "-i", path,
         "-an", "-frames:v", "1", "-vf", f"scale={width}:-2", "-pix_fmt", "rgb24", "-f", "rawvideo", "pipe:1"],
        capture_output=True,
    )
    if r.returncode:
        detail = r.stderr.decode(errors="replace").strip()
        raise RuntimeError(detail or f"ffmpeg exited {r.returncode}")
    raw = np.frombuffer(r.stdout, dtype=np.uint8)
    row = width * 3
    if raw.size == 0 or raw.size % row:
        raise RuntimeError(f"ffmpeg returned an incomplete RGB frame ({raw.size} bytes)")
    return raw.reshape((-1, width, 3))


def frame_content(frame):
    """Measure sharp detail, separating a foreground hook from a smooth background plane."""
    gray = np.dot(frame[..., :3].astype(np.float32), [0.299, 0.587, 0.114])
    if gray.shape[0] < 3 or gray.shape[1] < 3:
        return {"edge_density": 0.0, "foreground_share": 0.0}
    gx, gy = np.abs(np.diff(gray, axis=1)), np.abs(np.diff(gray, axis=0))
    edge_density = float((np.count_nonzero(gx > 18) + np.count_nonzero(gy > 18)) / (gx.size + gy.size))
    center = gray[1:-1, 1:-1]
    local = (gray[:-2, 1:-1] + gray[2:, 1:-1] + gray[1:-1, :-2] + gray[1:-1, 2:]) / 4
    foreground_share = float(np.mean(np.abs(center - local) > 10))
    return {"edge_density": edge_density, "foreground_share": foreground_share}


def content_end_report(path, duration, fps, edge_floor, foreground_floor):
    """Check the opening and final decoded frames against the measured minimum detail floors."""
    step = max(1.0 / fps, 0.05) if fps else 0.05
    points = [("opening", 0.0), ("closing", max(0.0, duration - step))]
    result = {"thresholds": {"edge_density": edge_floor, "foreground_share": foreground_floor}, "frames": []}
    for label, timestamp in points:
        metrics = frame_content(read_frame(path, timestamp))
        failures = []
        if metrics["edge_density"] < edge_floor:
            failures.append(f"edge density {metrics['edge_density']:.5f} < {edge_floor:.5f}")
        if metrics["foreground_share"] < foreground_floor:
            failures.append(f"foreground share {metrics['foreground_share']:.5f} < {foreground_floor:.5f}")
        result["frames"].append({"frame": label, "time": round(timestamp, 3), **metrics,
                                 "ok": not failures, "detail": "; ".join(failures) or "content detail present"})
    result["ok"] = all(item["ok"] for item in result["frames"])
    return result


def pops(path, ratio=6.0):
    """Sample-to-sample jumps far above the file's 99.9th percentile step: clicks at joins."""
    import soundfile as sf
    tmp = os.path.join(tempfile.mkdtemp(), "a.wav")
    run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", path, "-vn", "-ac", "1", "-ar", "48000", tmp])
    if not os.path.exists(tmp):
        return []
    y, sr = sf.read(tmp)
    if len(y) < sr:
        return []
    step = np.abs(np.diff(y)); ref = np.percentile(step, 99.9) or 1e-9
    idx = np.where(step > ratio * ref)[0]
    out, last = [], -sr
    for i in idx:
        if i - last > sr * 0.05:
            out.append(round(i / sr, 3))
        last = i
    return out[:50]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video"); ap.add_argument("--expect-fps", type=float); ap.add_argument("--expect-size")
    ap.add_argument("--expect-duration", type=float); ap.add_argument("--allow-black"); ap.add_argument("--allow-freeze")
    ap.add_argument("--allow-silence"); ap.add_argument("--min-silence", type=float, default=0.8)
    ap.add_argument("--require-content-ends", action="store_true",
                    help="fail when the opening or closing frame is only a smooth background")
    ap.add_argument("--content-edge-floor", type=float, default=0.0005)
    ap.add_argument("--content-share-floor", type=float, default=0.005)
    ap.add_argument("--black-ratio", type=float, default=0.998,
                    help="share of near-black pixels that makes a frame 'black' (dark designs need >= 0.998)")
    ap.add_argument("--max-hold", type=float, default=2.0, help="freezes longer than this are warnings")
    ap.add_argument("--json"); ap.add_argument("--md")
    a = ap.parse_args()
    info = probe(a.video)
    err = run(["ffmpeg", "-nostdin", "-hide_banner", "-i", a.video, "-vf",
               f"blackdetect=d=0.03:pic_th={a.black_ratio}:pix_th=0.06,freezedetect=n=0.001:d=0.5", "-af",
               f"silencedetect=n=-50dB:d={a.min_silence}", "-f", "null", "-"]).stderr
    black, freeze, silence = intervals(err, "black"), intervals(err, "freeze"), intervals(err, "silence")
    issues, warnings, notes = [], [], []
    fix = lambda e: e if e is not None else info["duration"]
    for s, e in black:
        if not allowed(s, fix(e), ranges(a.allow_black)):
            issues.append(f"black frames {s:.2f}-{fix(e):.2f}s")
    for s, e in freeze:
        if not allowed(s, fix(e), ranges(a.allow_freeze)):
            (warnings if fix(e) - s > a.max_hold else notes).append(
                f"static picture {s:.2f}-{fix(e):.2f}s ({fix(e) - s:.1f}s; allow intentional holds with --allow-freeze)")
    for s, e in silence:
        if info["audio"] and not allowed(s, fix(e), ranges(a.allow_silence)):
            warnings.append(f"silence {s:.2f}-{fix(e):.2f}s")
    v, au = info["video"], info["audio"]
    content_ends = {"required": a.require_content_ends, "ok": None}
    if a.require_content_ends:
        if not v:
            content_ends.update({"ok": False, "error": "no video stream"})
            issues.append("content ends unavailable: no video stream")
        else:
            try:
                content_ends = {"required": True, **content_end_report(
                    a.video, info["duration"], v["fps"], a.content_edge_floor, a.content_share_floor)}
                for item in content_ends["frames"]:
                    if not item["ok"]:
                        issues.append(f"{item['frame']} frame is background-only: {item['detail']}")
            except RuntimeError as exc:
                content_ends.update({"ok": False, "error": str(exc)})
                issues.append(f"content ends unavailable: {exc}")
    if a.expect_fps and v and abs(v["fps"] - a.expect_fps) > 0.01:
        issues.append(f"fps {v['fps']} != {a.expect_fps}")
    if a.expect_size and v and v["size"] != a.expect_size:
        issues.append(f"size {v['size']} != {a.expect_size}")
    if a.expect_duration and abs(info["duration"] - a.expect_duration) > 0.05:
        issues.append(f"duration {info['duration']:.3f}s != {a.expect_duration}s")
    if v and au and v["duration"] and au["duration"] and abs(v["duration"] - au["duration"]) > 0.05:
        issues.append(f"audio {au['duration']:.3f}s vs video {v['duration']:.3f}s (truncated or padded track)")
    if v and v.get("pix_fmt") not in ("yuv420p", None) and v["codec"] == "h264":
        issues.append(f"pix_fmt {v['pix_fmt']}: many players and platforms expect yuv420p for H.264")
    p = pops(a.video) if au else []
    issues += [f"audio click/pop near {t:.3f}s" for t in p]
    report = {"file": a.video, "probe": info, "black": black, "freeze": freeze, "silence": silence, "pops": p,
              "content_ends": content_ends, "errors": issues, "warnings": warnings, "notes": notes, "ok": not issues}
    if a.json:
        json.dump(report, open(a.json, "w"), indent=1)
    content_status = "not required" if not a.require_content_ends else ("PASS" if content_ends.get("ok") else "FAIL")
    md = [f"# AV QA: {os.path.basename(a.video)}", "", f"- probe: {json.dumps(info)}",
          f"- black: {black or 'none'}", f"- freeze: {freeze or 'none'}", f"- silence (>{a.min_silence}s): {silence or 'none'}",
          f"- pops: {p or 'none'}", f"- content ends: {content_status}", "", "## Verdict", "", "PASS" if not issues else "FAIL", ""] + \
         [f"- ERROR {i}" for i in issues] + [f"- WARN {w}" for w in warnings] + [f"- note {n}" for n in notes]
    if a.md:
        open(a.md, "w").write("\n".join(md) + "\n")
    print("\n".join(md))
    sys.exit(0 if not issues else 1)


if __name__ == "__main__":
    main()
