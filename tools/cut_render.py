#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy", "soundfile"]
# ///
"""Render an EDL (cut_plan.py) frame-exactly, and export it as an FCPXML timeline for Resolve/Final Cut.

Usage:
  cut_render.py cut/edl.json --out cut/cut.mp4 [--crf 17] [--fcpxml cut/cut.fcpxml] [--no-render]
How: video frames are kept by timestamp in one decode pass (select + setpts), audio is sliced sample-exactly in
numpy with 5 ms fades at every join, then both are muxed. Each keep contributes round(dur*fps) frames and exactly
frames*sr/fps samples, so picture and sound stay the same length across any number of cuts. (Seeking each
segment with -ss on millisecond-rounded times skips one frame and holds another; this avoids that.)
After rendering, every join is measured: a join louder than --join-db (-30 dBFS) within 25 ms means a clipped word
or leftover sound, and exits 1. Results go to <out>.render.json.
"""
import argparse, json, os, subprocess, tempfile
from fractions import Fraction

import numpy as np
import soundfile as sf

SR = 48000


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"command failed: {' '.join(cmd[:6])} ...\n{r.stderr[-1500:]}")
    return r


def render(edl, out, crf, fade_ms=5):
    src, fps = edl["source"], edl["fps"]
    keeps = [(k["in"], k["out"]) for k in edl["keep"]]
    fr = lambda t: round(t * fps)
    tmp = tempfile.mkdtemp(prefix="cut_")
    # Video: keep frames whose index falls in [F_in, F_out) for any keep.
    expr = "+".join(f"between(n\\,{fr(s)}\\,{fr(e) - 1})" for s, e in keeps)
    vid = os.path.join(tmp, "v.mp4")
    run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", src, "-an", "-vf", f"select='{expr}',setpts=N/FRAME_RATE/TB",
         "-fps_mode", "passthrough", "-c:v", "libx264", "-crf", str(crf), "-preset", "medium", "-pix_fmt", "yuv420p",
         "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", vid])
    # Audio: exact sample slices at 48 kHz.
    wav = os.path.join(tmp, "a.wav")
    run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", src, "-vn", "-ac", "2", "-ar", str(SR), "-c:a", "pcm_f32le", wav])
    y, _ = sf.read(wav, always_2d=True)
    spf = Fraction(SR) / Fraction(fps).limit_denominator(1001)
    parts, fade = [], int(SR * fade_ms / 1000)
    ramp = np.linspace(0, 1, fade)[:, None]
    for s, e in keeps:
        a0, a1 = int(round(fr(s) * spf)), int(round(fr(e) * spf))
        seg = y[a0:a1].copy()
        if len(seg) < a1 - a0:
            seg = np.vstack([seg, np.zeros((a1 - a0 - len(seg), y.shape[1]))])
        if len(seg) > 2 * fade:
            seg[:fade] *= ramp; seg[-fade:] *= ramp[::-1]
        parts.append(seg)
    cut_wav = os.path.join(tmp, "cut.wav")
    audio = np.vstack(parts)
    sf.write(cut_wav, audio, SR, subtype="FLOAT")
    # Every join should sit in silence: loud audio within 25 ms of a join means a clipped word or a leftover.
    joins, acc = [], 0
    mono = audio.mean(axis=1)
    for p_ in parts[:-1]:
        acc += len(p_)
        w = mono[max(acc - int(0.025 * SR), 0): acc + int(0.025 * SR)]
        db = 20 * np.log10(np.sqrt(np.mean(w ** 2)) + 1e-9) if len(w) else -120
        joins.append({"t": round(acc / SR, 3), "rms_db": round(float(db), 1)})
    render.joins = joins
    run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", vid, "-i", cut_wav, "-map", "0:v", "-map", "1:a", "-c:v", "copy",
         "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", "-shortest", out])
    frames = sum(fr(e) - fr(s) for s, e in keeps)
    return frames / fps


def rational(frames, fps):
    """FCPXML time: frames at the timeline rate, as an exact rational of seconds."""
    f = Fraction(fps).limit_denominator(1001)
    t = Fraction(frames) / f
    return f"{t.numerator}/{t.denominator}s" if t.denominator != 1 else f"{t.numerator}s"


def fcpxml(edl, path):
    fps = edl["fps"]; f = Fraction(fps).limit_denominator(1001)
    frame_dur = f"{f.denominator}/{f.numerator}s"
    src = edl["source"]; name = os.path.basename(src)
    probe = json.loads(run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                            "-of", "json", src]).stdout)["streams"][0]
    fr = lambda t: round(t * fps)
    total = sum(fr(k["out"]) - fr(k["in"]) for k in edl["keep"])
    clips, off = [], 0
    for i, k in enumerate(edl["keep"], 1):
        n = fr(k["out"]) - fr(k["in"])
        clips.append(f'            <asset-clip ref="r2" name="{name} keep {i}" offset="{rational(off, fps)}" '
                     f'start="{rational(fr(k["in"]), fps)}" duration="{rational(n, fps)}" format="r1" tcFormat="NDF"/>')
        off += n
    xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE fcpxml>
<fcpxml version="1.10">
    <resources>
        <format id="r1" name="FFVideoFormat{probe['height']}p{round(fps)}" frameDuration="{frame_dur}" width="{probe['width']}" height="{probe['height']}" colorSpace="1-1-1 (Rec. 709)"/>
        <asset id="r2" name="{name}" start="0s" duration="{rational(fr(edl['duration']), fps)}" hasVideo="1" hasAudio="1" format="r1" audioSources="1" audioChannels="2" audioRate="48000">
            <media-rep kind="original-media" src="file://{src}"/>
        </asset>
    </resources>
    <library>
        <event name="editbay rough cut">
            <project name="{os.path.splitext(name)[0]} rough cut">
                <sequence format="r1" duration="{rational(total, fps)}" tcStart="0s" tcFormat="NDF" audioLayout="stereo" audioRate="48k">
                    <spine>
{chr(10).join(clips)}
                    </spine>
                </sequence>
            </project>
        </event>
    </library>
</fcpxml>
'''
    open(path, "w").write(xml)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("edl"); ap.add_argument("--out"); ap.add_argument("--crf", type=int, default=17)
    ap.add_argument("--fcpxml"); ap.add_argument("--no-render", action="store_true")
    ap.add_argument("--join-db", type=float, default=-30.0, help="joins louder than this are flagged")
    a = ap.parse_args()
    edl = json.load(open(a.edl))
    if not os.path.isabs(edl["source"]):  # sources are stored relative to the EDL's folder
        edl["source"] = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(a.edl)), edl["source"]))
    if a.fcpxml:
        fcpxml(edl, a.fcpxml); print("wrote", a.fcpxml)
    if not a.no_render:
        if not a.out:
            raise SystemExit("--out is required unless --no-render")
        expect = render(edl, a.out, a.crf)
        loud = [j for j in render.joins if j["rms_db"] > a.join_db]
        for j in render.joins:
            print(f"join {j['t']:8.3f}s  {j['rms_db']:6.1f} dB  {'LOUD: check for a clipped word or leftover' if j in loud else 'in silence'}")
        got = json.loads(run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,duration,nb_frames",
                              "-of", "json", a.out]).stdout)["streams"]
        v = next(s for s in got if s["codec_type"] == "video"); au = next(s for s in got if s["codec_type"] == "audio")
        print(f"wrote {a.out}: expected {expect:.3f}s, video {float(v['duration']):.3f}s ({v.get('nb_frames')} frames), "
              f"audio {float(au['duration']):.3f}s; {len(render.joins) - len(loud)}/{len(render.joins)} joins in silence")
        json.dump({"out": a.out, "seconds": round(expect, 3), "joins": render.joins, "loud_joins": loud},
                  open(os.path.splitext(a.out)[0] + ".render.json", "w"), indent=1)
        if loud:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
