#!/usr/bin/env python3
"""Write beats/beats.json for the five-step explainer from the reconciled narration words.

Standard cues use anchors (resolved later by tools/beats_check.py). The demonstration scenes on the right-hand side
are `custom` cues whose sub-events are timed from the real word timestamps, so every tick, collapse, and check mark
lands on the word that names it. Run after narration/words.words.json exists.
"""
import json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
words = json.load(open(os.path.join(HERE, "narration/words.words.json")))
norm = lambda w: re.sub(r"[^a-z0-9']", "", w.lower())


def at(phrase, after=0.0, which="start"):
    toks = [norm(t) for t in phrase.split()]
    keys = [norm(w["text"]) for w in words]
    for i in range(len(keys) - len(toks) + 1):
        if keys[i:i + len(toks)] == toks and words[i]["start"] >= after:
            return round(words[i]["start"] if which == "start" else words[i + len(toks) - 1]["end"], 3)
    raise SystemExit(f"phrase not found: {phrase!r}")


end_of_speech = round(words[-1]["end"], 3)
duration = round(end_of_speech + 4.2, 2)
TOTAL_FRAMES = round(duration * 60)

# --- Step 1 demo: the real timestamps of "Every word gets a timestamp" appear as each word is spoken.
demo_words = []
t0 = at("Every word gets a timestamp")
keys = [norm(w["text"]) for w in words]
i0 = next(i for i, w in enumerate(words) if abs(w["start"] - t0) < 1e-6)
for w in words[i0:i0 + 5]:
    demo_words.append(w)
rows = "".join(f'<div class="ts-row" id="ts{k}"><span class="ts-t">{w["start"]:05.2f}</span><span class="ts-w">{w["text"].strip(".,")}</span></div>'
               for k, w in enumerate(demo_words))
ts_html = f'<div class="card demo"><div class="kicker">word · start (s)</div>{rows}</div>'
ts_js = " ".join(f'tl.fromTo("#ts{k}", {{opacity: 0, x: 18}}, {{opacity: 1, x: 0, duration: 0.18, ease: "power2.out"}}, {w["start"]});'
                 for k, w in enumerate(demo_words))

# --- Step 2 demo: a waveform whose dead air, filler, and retake chunks collapse as they are named.
bars, removed = [], {"dead": range(9, 13), "filler": range(19, 21), "retake": range(27, 32)}
heights = [18, 34, 52, 40, 64, 30, 46, 58, 26, 6, 5, 7, 5, 44, 62, 38, 50, 28, 42, 24, 22, 48, 60, 36, 54, 30, 40,
           46, 52, 38, 44, 50, 34, 58, 42, 28, 48, 62, 36, 30]
for k, h in enumerate(heights):
    tag = next((n for n, r in removed.items() if k in r), "")
    bars.append(f'<i class="wb {tag}" style="height:{h * 2}px"></i>')
wave_html = ('<div class="card demo"><div class="kicker">waveform · before the cut</div>'
             f'<div class="wave">{"".join(bars)}</div><div class="wave-key"><b class="k dead"></b>dead air'
             '<b class="k filler"></b>filler<b class="k retake"></b>retake</div></div>')
wave_js = " ".join(
    f'tl.to("#C21 .wb.{n}", {{scaleY: 0.02, opacity: 0.25, duration: 0.35, ease: "power2.in", stagger: 0.03}}, {at(p)});'
    for n, p in (("dead", "Dead air"), ("filler", "filler"), ("retake", "retakes")))

# --- Step 3 demo: the three things a cue needs, each on its phrase.
need = [("a word to land on", "anchor"), ("a place on screen", "zone"), ("a reason to exist", "why")]
need_html = '<div class="card demo"><div class="kicker">one cue</div>' + "".join(
    f'<div class="need" id="nd{k}"><span class="need-k">{key}</span><span class="need-v">{text}</span></div>'
    for k, (text, key) in enumerate(need)) + "</div>"
need_js = " ".join(f'tl.fromTo("#nd{k}", {{opacity: 0, y: 14}}, {{opacity: 1, y: 0, duration: 0.3, ease: "power2.out"}}, {at(text)});'
                   for k, (text, _) in enumerate(need))

# --- Step 4 demo: composition code types in, then a frame counter runs on "frame by frame".
code = ['&lt;div id="C10" class="clip"', '     data-start="12.40"', '     data-duration="4.80"&gt;',
        '  Transcribe', '&lt;/div&gt;']
code_html = ('<div class="card demo code"><div class="kicker">index.html</div>' +
             "".join(f'<div class="cl" id="cl{k}">{line}</div>' for k, line in enumerate(code)) +
             '<div class="frames">frame <span id="fc">0000</span></div></div>')
t_web = at("as a web page")
code_js = " ".join(f'tl.fromTo("#cl{k}", {{opacity: 0, x: -10}}, {{opacity: 1, x: 0, duration: 0.15}}, {round(t_web - 1.2 + k * 0.28, 3)});'
                   for k in range(len(code)))
t_fbf = at("renders it")  # start on "renders" so the count lands and holds before the card leaves
code_js += (f' const fcEl = document.getElementById("fc"); const fco = {{n: 0}};'
            f' tl.to(fco, {{n: {TOTAL_FRAMES}, duration: 1.0, ease: "power1.out", onUpdate: () => {{ fcEl.textContent = String(Math.round(fco.n)).padStart(4, "0"); }}}}, {t_fbf});')

# --- Step 5 demo: this video's own checks, ticked as they are named.
# Every line is something this video's own QA proved (qa/REPORT.md): loudness gate, words gate, motion sidecar.
checks = [("the loudness", "−16 LUFS · −1 dBTP"), ("every cut", "149 of 149 words heard"), ("every card", "every card on its word"),
          ("fixes what fails", "repair, then hand over")]
chk_html = '<div class="card demo"><div class="kicker">render-verify</div>' + "".join(
    f'<div class="chk" id="ck{k}"><span class="tick">✓</span>{label}</div>' for k, (_, label) in enumerate(checks)) + "</div>"
chk_js = " ".join(f'tl.fromTo("#ck{k}", {{opacity: 0.18}}, {{opacity: 1, duration: 0.2}}, {at(p)});'
                  f' tl.fromTo("#ck{k} .tick", {{scale: 0}}, {{scale: 1, duration: 0.3, ease: "back.out(2)"}}, {at(p)});'
                  for k, (p, _) in enumerate(checks))

# --- Step rail (top): all five steps; a glow layer (no text) lights the active chip, opacity-only.
steps = ["Transcribe", "Cut", "Plan the beats", "Build", "Verify"]
starts = [at(f"Step {w}") for w in ("one", "two", "three", "four", "five")]
rail_end = at("Then the loop") - 0.12
rail_html = '<div class="rail">' + "".join(
    f'<div class="chip" id="chip{k}"><span class="glow"></span><span class="n">0{k + 1}</span>{s_}</div>'
    for k, s_ in enumerate(steps)) + "</div>"
rail_js = ""
for k, t_on in enumerate(starts):
    t_off = starts[k + 1] if k + 1 < len(starts) else rail_end - 0.3
    rail_js += (f'tl.to("#chip{k} .glow", {{opacity: 1, duration: 0.25}}, {round(t_on - 0.1, 3)});'
                f' tl.to("#chip{k} .glow", {{opacity: 0, duration: 0.25}}, {round(t_off - 0.1, 3)}); ')

# --- Loop diagram for the ending.
loop_html = ('<div class="loop"><svg viewBox="0 0 900 260" width="900" height="260">'
             '<path id="loop-path" d="M 90 130 C 90 20, 810 20, 810 130 C 810 240, 90 240, 90 130" fill="none" '
             'stroke="var(--accent)" stroke-width="4" stroke-dasharray="1400" stroke-dashoffset="1400"/></svg>'
             '<div class="loop-labels"><span>edit</span><span>feedback</span><span>skills</span><span>next edit</span></div></div>')
loop_js = f'tl.to("#loop-path", {{strokeDashoffset: 0, duration: 1.6, ease: "power2.inOut"}}, {at("back into the skills")});'

cues = [
    {"id": "C00", "anchor": "You can hand", "until": "back", "kind": "label", "zone": "top",
     "content": {"title": "EDITING WITH AN AGENT"}, "why": "name the topic before the first idea lands"},
    {"id": "C01", "anchor": "You can hand", "offset": -0.25, "until": "coding agent", "tail": 0.05, "kind": "title", "zone": "center",
     "content": {"title": "Hand it a video."}, "why": "the promise, in the viewer's words"},
    {"id": "C02", "anchor": "get a real edit back", "offset": -0.1, "hold": 2.2, "kind": "title", "zone": "center",
     "content": {"title": "Get a real edit back."}, "why": "the payoff"},
    {"id": "C03", "anchor": "a loop", "offset": -0.1, "until_start": "Step one", "tail": -0.35, "kind": "title", "zone": "center",
     "content": {"title": "A loop, not a lucky prompt."}, "sfx": "shimmer", "why": "the thesis of the video"},
    {"id": "C10", "anchor": "Step one", "until_start": "Step two", "tail": -0.12, "kind": "step", "zone": "left",
     "content": {"number": "STEP 01", "title": "Transcribe", "subtitle": "every word gets a timestamp"}, "sfx": "whoosh-short",
     "why": "step card"},
    {"id": "C11", "anchor": "Every word gets a timestamp", "offset": -0.3, "until_start": "Step two", "tail": -0.12, "kind": "custom", "zone": "right",
     "content": {"html": ts_html, "js": ts_js}, "origin": "agent", "why": "show real timestamps arriving with the words"},
    {"id": "C20", "anchor": "Step two", "until_start": "Step three", "tail": -0.12, "kind": "step", "zone": "left",
     "content": {"number": "STEP 02", "title": "Cut", "subtitle": "dead air · filler · retakes"}, "sfx": "whoosh-short", "why": "step card"},
    {"id": "C21", "anchor": "Step two", "offset": 0.3, "until_start": "Step three", "tail": -0.12, "kind": "custom", "zone": "right",
     "content": {"html": wave_html, "js": wave_js}, "origin": "agent", "why": "each kind of cut collapses as it is named"},
    {"id": "C22", "anchor": "every cut lands in silence", "hold": 2.4, "kind": "label", "zone": "bottom",
     "content": {"title": "every cut lands in silence"}, "flash": False, "why": "the rule that makes cuts invisible"},
    {"id": "C30", "anchor": "Step three", "until_start": "Step four", "tail": -0.12, "kind": "step", "zone": "left",
     "content": {"number": "STEP 03", "title": "Plan the beats", "subtitle": "a word, a place, a reason"}, "sfx": "whoosh-short",
     "why": "step card"},
    {"id": "C31", "anchor": "Each graphic gets", "until_start": "Step four", "tail": -0.12, "kind": "custom", "zone": "right",
     "content": {"html": need_html, "js": need_js}, "origin": "agent", "why": "the three fields of a cue, on their words"},
    {"id": "C40", "anchor": "Step four", "until_start": "Step five", "tail": -0.12, "kind": "step", "zone": "left",
     "content": {"number": "STEP 04", "title": "Build", "subtitle": "motion as a web page"}, "sfx": "whoosh-short", "why": "step card"},
    {"id": "C41", "anchor": "The agent writes", "offset": -0.2, "until_start": "Step five", "tail": -0.12, "kind": "custom", "zone": "right",
     "content": {"html": code_html, "js": code_js}, "origin": "agent", "why": "the composition is code; frames are rendered from it"},
    {"id": "C50", "anchor": "Step five", "until_start": "Then the loop", "tail": -0.12, "kind": "step", "zone": "left",
     "content": {"number": "STEP 05", "title": "Verify", "subtitle": "measure, check, fix"}, "sfx": "whoosh-short", "why": "step card"},
    {"id": "C51", "anchor": "It measures", "offset": -0.2, "until_start": "Then the loop", "tail": -0.12, "kind": "custom", "zone": "right",
     "content": {"html": chk_html, "js": chk_js}, "origin": "agent", "why": "this video's own QA, ticked as each check is named"},
    {"id": "C60", "anchor": "the loop feeds itself", "offset": -0.1, "until": "starts smarter", "tail": 0.35, "kind": "title", "zone": "top",
     "content": {"title": "The loop feeds itself."}, "sfx": "shimmer", "why": "callback to the thesis"},
    {"id": "C61", "anchor": "What you liked", "until": "starts smarter", "tail": 0.35, "kind": "custom", "zone": "center",
     "content": {"html": loop_html, "js": loop_js}, "origin": "agent", "why": "draw the loop as it is described"},
    {"id": "C62", "at": round(end_of_speech + 0.35, 3), "hold": 3.6, "kind": "custom", "zone": "full", "cover_face": True,
     "content": {"html": '<div class="endcard"><div class="brand">editbay</div><div class="by">Starter Pack · Devin Thomas</div>'
                 '<div class="disc">Narrated with a voice model trained on the creator\'s own voice.</div></div>'},
     "sfx": "impact", "why": "end card with the voice disclosure"},
    {"id": "R0", "anchor": "Step one", "offset": -0.4, "until_start": "Then the loop", "tail": -0.12, "kind": "custom", "zone": "top",
     "content": {"html": rail_html, "js": rail_js}, "origin": "agent", "why": "where we are in the loop; the active step lit"},
]

sheet = {"timeline": "narration", "words": "../narration/words.words.json", "fps": 60, "duration": duration,
         "min_read": 2.0, "composition": "index.html", "mode": "open", "cues": cues}
os.makedirs(os.path.join(HERE, "beats"), exist_ok=True)
json.dump(sheet, open(os.path.join(HERE, "beats/beats.json"), "w"), indent=1, ensure_ascii=False)
print(f"wrote beats/beats.json: {len(cues)} cues, duration {duration}s (speech ends {end_of_speech}s)")
