#!/usr/bin/env python3
"""Beat sheet for a 15 s craft reel (style-craft-reel) in the starter-pack brand.

Everything sits on the bed's exact grid: 128 BPM, 8 bars, one chapter per bar, a half-beat flurry in bar 7, the lockup in
bar 8, and a 1.5 s ring-out. Chapters are raw custom scenes (hard cuts on the beat; each scene owns its tweens).
Motif: the brand's blue terminal caret. It drops in the first bar and lands after the wordmark in the last.
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
BPM = 128.0
SPB = 60.0 / BPM            # 0.46875 s per beat
T = lambda b: round(b * SPB, 4)
DUR = round(T(32) + 1.5, 4)  # 15.0 s of music + ring-out under the held lockup

cues = []


def scene(cid, b0, b1, html, js, why, zone="full"):
    cues.append({"id": cid, "beat": b0, "hold_beats": b1 - b0, "kind": "custom", "zone": zone, "cover_face": True,
                 "content": {"raw": True, "html": html, "js": js}, "why": why})


# 01 CARET: the motif drops on beat 1, squashes, blinks on 2 and 3, stretches into a line on 3.5.
scene("C1", 0, 4,
      '<div class="stage"><div class="base"></div><div class="caret" id="c1caret"></div></div>',
      f'tl.set("#C1", {{opacity: 1}}, S); tl.fromTo("#c1caret", {{y: -620}}, {{y: 0, duration: {T(1) - 0.02:.3f}, ease: "power2.in"}}, S);'
      f' tl.to("#c1caret", {{scaleY: 0.62, scaleX: 1.35, duration: 0.07, ease: "power1.out"}}, {T(1)});'
      f' tl.to("#c1caret", {{scaleY: 1, scaleX: 1, duration: 0.28, ease: "elastic.out(1, 0.45)"}}, {T(1) + 0.07});'
      f' tl.to("#c1caret", {{opacity: 0, duration: 0.01}}, {T(2)}); tl.to("#c1caret", {{opacity: 1, duration: 0.01}}, {T(2.5)});'
      f' tl.to("#c1caret", {{opacity: 0, duration: 0.01}}, {T(3)}); tl.to("#c1caret", {{opacity: 1, duration: 0.01}}, {T(3.25)});'
      f' tl.to("#c1caret", {{scaleX: 26, scaleY: 0.08, duration: {T(0.5) - 0.02:.3f}, ease: "power3.in"}}, {T(3.5)});',
      "the motif arrives with physics")

# 02 WORDS: one word per beat; the accent word in the accent voice; words collapse to a row of dots.
words = [("Words", ""), ("first,", ""), ("then", ""), ("frames.", "accent")]
w_html = '<div class="stage"><div class="line" id="c2line"></div><div class="words">' + "".join(
    f'<span class="w {cls}" id="c2w{k}">{w}</span>' for k, (w, cls) in enumerate(words)) + '</div><div class="dots">' + "".join(
    f'<i class="dot" id="c2d{k}"></i>' for k in range(12)) + "</div></div>"
w_js = (f'tl.set("#C2", {{opacity: 1}}, S); tl.fromTo("#c2line", {{scaleX: 1}}, {{scaleX: 0.0, duration: 0.3, ease: "power2.in"}}, S);'
        + "".join(f' tl.fromTo("#c2w{k}", {{opacity: 0, y: 70}}, {{opacity: 1, y: 0, duration: 0.22, ease: "back.out(1.6)"}}, {T(4 + k)});'
                  for k in range(4))
        + f' tl.fromTo("#c2w3", {{skewX: 0}}, {{skewX: -9, duration: 0.2}}, {T(7)});'
        + f' tl.to("#C2 .w", {{opacity: 0, scale: 0.4, duration: 0.18, ease: "power2.in"}}, {T(7.6)});'
        + "".join(f' tl.fromTo("#c2d{k}", {{scale: 0, opacity: 0}}, {{scale: 1, opacity: 1, duration: 0.12}}, {T(7.62) + k * 0.012:.4f});'
                  for k in range(12)))
scene("C2", 4, 8, w_html, w_js, "kinetic statement: transcription comes first")

# 03 GRID: the dots become a 16x9 field of carets, pulsing on every beat, a wave of blue rolling through.
cells = "".join(f'<i class="cell" style="--x:{x};--y:{y}"><b class="lit"></b></i>' for y in range(9) for x in range(16))
g_js = (f'tl.set("#C3", {{opacity: 1}}, S); tl.fromTo("#C3 .cell", {{scale: 0}}, {{scale: 1, duration: 0.2, stagger: {{each: 0.003, from: "center"}}}}, S);'
        + "".join(f' tl.fromTo("#C3 .grid", {{scale: 1.045}}, {{scale: 1, duration: 0.3, ease: "power2.out"}}, {T(b)});' for b in (9, 10, 11))
        + f' tl.fromTo("#C3 .lit", {{opacity: 0}}, {{opacity: 1, duration: 0.18, yoyo: true, repeat: 1, stagger: {{each: 0.012, grid: [9, 16], from: "start", axis: "x"}}}}, {T(9)});'
        + f' tl.to("#C3 .cell", {{scaleY: 0.06, duration: {T(0.5) - 0.02:.3f}, ease: "power3.in"}}, {T(11.5)});')
scene("C3", 8, 12, f'<div class="stage"><div class="grid">{cells}</div></div>', g_js, "density: the motif multiplied into a field")

# 04 CUT: a waveform whose dead air, filler, and retake collapse on beats 13, 14, 15.
hs = [30, 52, 70, 44, 80, 36, 60, 74, 8, 6, 9, 7, 58, 84, 46, 66, 38, 22, 20, 54, 76, 40, 62, 50, 70, 44, 58, 36, 64, 78, 48, 30]
groups = {"dead": range(8, 12), "fill": range(17, 19), "take": range(24, 29)}
bars = "".join(f'<i class="wb {next((g for g, r in groups.items() if k in r), "")}" style="height:{h * 3}px"></i>' for k, h in enumerate(hs))
labels = '<div class="wl"><span id="l1">dead air</span><span id="l2">filler</span><span id="l3">retake</span></div>'
c_js = (f'tl.set("#C4", {{opacity: 1}}, S); tl.fromTo("#C4 .wb", {{scaleY: 0.02}}, {{scaleY: 1, duration: 0.25, stagger: 0.006, ease: "power2.out"}}, S);'
        + "".join(f' tl.to("#C4 .wb.{g}", {{scaleY: 0.02, opacity: 0.2, duration: 0.16, ease: "power2.in"}}, {T(b)});'
                  f' tl.fromTo("#l{k + 1}", {{opacity: 0, y: 14}}, {{opacity: 1, y: 0, duration: 0.14}}, {T(b)});'
                  for k, (g, b) in enumerate((("dead", 13), ("fill", 14), ("take", 15))))
        + f' tl.fromTo("#C4 .flash", {{opacity: 0}}, {{opacity: 1, duration: 0.017}}, {T(16) - 0.034:.4f});')
scene("C4", 12, 16, f'<div class="stage"><div class="wave">{bars}</div>{labels}<div class="flash"></div></div>', c_js,
      "the cut, as a picture: removed chunks collapse on the beat")

# 05 BUILD: this reel's own composition code types in on half-beats, then tilts into 3D.
code = ['<span class="k">&lt;div</span> id="C5" class="clip"', f'  data-start="{T(16):.3f}"',
        f'  data-duration="{T(4):.3f}"<span class="k">&gt;</span>', '  tl.to(caret, { y: 0 }, beat(1))',
        '<span class="k">&lt;/div&gt;</span>']
code_html = '<div class="stage"><div class="code card3d" id="c5card">' + "".join(
    f'<div class="cl" id="c5l{k}">{line}</div>' for k, line in enumerate(code)) + '<div class="pill">render · 60 fps</div></div></div>'
code_js = (f'tl.set("#C5", {{opacity: 1}}, S); tl.fromTo("#c5card", {{scale: 0.92, opacity: 0}}, {{scale: 1, opacity: 1, duration: 0.2}}, S);'
           + "".join(f' tl.fromTo("#c5l{k}", {{opacity: 0, x: -18}}, {{opacity: 1, x: 0, duration: 0.1}}, {T(16.5 + k * 0.5)});' for k in range(5))
           + f' tl.to("#c5card", {{rotationY: -28, rotationX: 8, scale: 0.9, duration: {T(0.5):.3f}, ease: "power2.in"}}, {T(19.5)});')
scene("C5", 16, 20, code_html, code_js, "build: the motion is code (the values are this reel's own)")

# 06 RENDER: three cards fan out in 3D and turn on the beats; a light sweep crosses them; cut to black before the drop.
cards3 = "".join(f'<div class="c3" id="c6c{k}"><div class="sweep"></div><span>{t}</span></div>' for k, t in enumerate(("frame 0001", "frame 0480", "frame 0960")))
r_js = (f'tl.set("#C6", {{opacity: 1}}, S);'
        + "".join(f' tl.fromTo("#c6c{k}", {{rotationY: 0, x: 0, z: 0}}, {{rotationY: {-24 + k * 24}, x: {(k - 1) * 360}, z: {-abs(k - 1) * 120}, duration: 0.35, ease: "power3.out"}}, S);'
                  for k in range(3))
        + "".join(f' tl.to("#C6 .fan", {{rotationY: {-10 + 10 * b % 20}, duration: 0.3, ease: "power2.out"}}, {T(20 + b)});' for b in (1, 2, 3))
        + f' tl.fromTo("#C6 .sweep", {{x: -420}}, {{x: 420, duration: 0.9, ease: "power1.inOut", stagger: 0.08}}, {T(21)});'
        + f' tl.to("#C6", {{opacity: 0, duration: 0.02}}, {T(23.5)});')
scene("C6", 20, 24, f'<div class="stage persp"><div class="fan">{cards3}</div></div>', r_js, "render: frames as objects")

# 07 FLURRY: eight half-beat cards recapping each chapter's material (hard cuts).
recap = [("caret", '<div class="caret big"></div>'), ("words", '<div class="fl-t">WORDS</div>'),
         ("grid", '<div class="fl-grid">' + "<i></i>" * 24 + "</div>"), ("wave", '<div class="fl-wave">' + "".join(f'<i style="height:{h * 3}px"></i>' for h in hs[:16]) + "</div>"),
         ("code", '<div class="fl-t mono">&lt;/&gt;</div>'), ("frame", '<div class="fl-frame"></div>'),
         ("check", '<div class="fl-t">✓</div>'), ("fps", '<div class="fl-t mono">60</div>')]
for k, (name, inner) in enumerate(recap):
    cues.append({"id": f"F{k}", "beat": 24 + k * 0.5, "hold_beats": 0.5, "kind": "custom", "zone": "full", "cover_face": True,
                 "flash": True, "sfx": "tick",
                 "content": {"raw": True, "html": f'<div class="stage fl fl{k % 3}">{inner}</div>',
                             "js": f'tl.set("#F{k}", {{opacity: 1}}, S);'}, "why": f"flurry card: {name}"})

# 08 LOCKUP: the wordmark builds letter by letter, the caret returns and lands after the name, a quiet subline.
letters = "editbay"
lk_html = ('<div class="stage"><div class="mark">' + "".join(f'<span class="ch" id="lk{k}">{c}</span>' for k, c in enumerate(letters))
           + '<span class="caret land" id="lkcaret"></span></div><div class="sub" id="lksub">Starter Pack · Devin Thomas</div></div>')
lk_js = (f'tl.set("#C8", {{opacity: 1}}, S);'
         + "".join(f' tl.fromTo("#lk{k}", {{opacity: 0, y: 40}}, {{opacity: 1, y: 0, duration: 0.16, ease: "power3.out"}}, {T(28 + k * 0.25):.4f});'
                   for k in range(len(letters)))
         + f' tl.fromTo("#lkcaret", {{y: -700, opacity: 1}}, {{y: 0, duration: {T(1) - 0.02:.3f}, ease: "power2.in"}}, {T(29.5)});'
         + f' tl.to("#lkcaret", {{scaleY: 0.62, scaleX: 1.35, duration: 0.07}}, {T(30.5)}); tl.to("#lkcaret", {{scaleY: 1, scaleX: 1, duration: 0.3, ease: "elastic.out(1, 0.45)"}}, {T(30.5) + 0.07:.4f});'
         + f' tl.fromTo("#lksub", {{opacity: 0, y: 16}}, {{opacity: 1, y: 0, duration: 0.3}}, {T(31)});'
         + "".join(f' tl.to("#lkcaret", {{opacity: {0 if i % 2 == 0 else 1}, duration: 0.01}}, {T(32) + i * SPB:.4f});' for i in range(3))
         + f' tl.fromTo("#C8 .mark", {{scale: 1}}, {{scale: 1.03, duration: {DUR - T(28):.3f}, ease: "none"}}, S);')
cues.append({"id": "C8", "beat": 28, "hold_beats": round((DUR - T(28)) / SPB, 3), "kind": "custom", "zone": "full", "cover_face": True,
             "content": {"raw": True, "html": lk_html, "js": lk_js}, "sfx": None, "why": "lockup: the motif lands in the name"})

# Machine layer: one mono line, bottom; chapter name per bar and a bar.beat counter (brand allows numbers).
chapters = ["01 caret", "02 words", "03 field", "04 cut", "05 build", "06 render", "07 recap", "08 editbay"]
ml_html = ('<div class="mline"><span class="ml-l">editbay · showreel</span><span class="ml-c">' + "".join(
    f'<b class="chn" id="ch{k}">{c}</b>' for k, c in enumerate(chapters)) + '</span><span class="ml-r" id="bb">bar 1 · 1</span></div>')
ml_js = ("".join(f' tl.set("#ch{k}", {{opacity: 1}}, {T(k * 4)}); tl.set("#ch{k}", {{opacity: 0}}, {T(k * 4 + 4) if k < 7 else DUR});' for k in range(8))
         + f' const bb = document.getElementById("bb"); tl.eventCallback("onUpdate", () => {{ const b = Math.min(31, Math.floor(tl.time() / {SPB})); bb.textContent = `bar ${{Math.floor(b / 4) + 1}} · ${{b % 4 + 1}}`; }});')
cues.append({"id": "ML", "beat": 0, "hold_beats": round(DUR / SPB, 3), "kind": "custom", "zone": "full", "cover_face": True, "overlay_of": "C1",
             "content": {"raw": True, "html": ml_html, "js": 'tl.set("#ML", {opacity: 1}, S);' + ml_js}, "why": "machine layer"})

# Sound cues on the hand-offs and the lockup.
sfx = [(1, "click"), (4, "whoosh-short"), (8, "whoosh-short"), (12, "whoosh-short"), (16, "whoosh-short"), (20, "whoosh-short"), (30.5, "impact"), (31, "shimmer")]
for k, (b, name) in enumerate(sfx):
    cues.append({"id": f"S{k}", "beat": b, "hold_beats": 0.25, "kind": "sfx", "sfx": name, "why": f"sound: {name}"})

for c in cues:  # scene cues own the frame; the machine layer and sound markers deliberately overlap them
    if c["id"] not in ("ML",) and not c["id"].startswith("S"):
        c.setdefault("overlay_of", None)
sheet = {"timeline": "music", "grid": "../sound/bed.grid.json", "fps": 60, "duration": DUR, "min_read": 1.0,
         "composition": "index.html", "mode": "strict", "cues": cues}
os.makedirs(os.path.join(HERE, "beats"), exist_ok=True)
json.dump(sheet, open(os.path.join(HERE, "beats/beats.json"), "w"), indent=1, ensure_ascii=False)
print(f"{len(cues)} cues, {DUR}s at {BPM} BPM ({SPB * 60:.2f} frames per beat)")
