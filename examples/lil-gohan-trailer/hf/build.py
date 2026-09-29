"""Builds index.html for the Lil Gohan trailer from a beat-locked shot list.

Time: T is trailer time. The song starts at T = PRE; beat k is at B(k) = 1.5 + 0.48005 k (125 BPM).
Takes are song-aligned files (file time = song time + LEAD), so a 'sync' segment shows exactly what the app showed
at that point of the song (its clock matches the soundtrack); an 'anchor' segment pins a chosen moment of a take
(a real tap) to a chosen trailer time."""
import json, os, html

HERE = os.path.dirname(os.path.abspath(__file__))
PRE, LEAD, PER, B0 = 1.442, 3.0, 0.48005, 1.5
DUR = 39.5
def B(k): return round(B0 + PER * k, 4)
def bar(n, beat=1): return B(4 * (n - 1) + (beat - 1))

TAKES = json.load(open(f"{HERE}/assets/takes/takes.json"))
AUD = json.load(open(f"{HERE}/assets/audio.json"))
ART = [a["file"] for a in json.load(open(f"{HERE}/assets/art256/art.json"))]
TOUCH = 0.09  # XCUITest call -> touch on screen, measured on A6 (pause icon)
SCREEN = {"ph": (402, 874), "pad": (1376, 1032), "fl": (402, 874)}
SONG_STOP_T = PRE + 31.313  # the real pause in take E2
ECHO0 = 32.4457  # echo_tail --json throwTransient: echo repeat k is heard at ECHO0 + k beats (onsets on the mix
                 # 32.928, 33.408, 33.888, 34.368), 0.309 s before SONG_STOP_T + k beats, where each repeat ends
CUT_LOCK = round(B(65) + PER / 2, 4)   # hold the paused phone ~0.19 s, then cut to the lockup on the half beat
LOCK_PLATE_T0 = 1965 / 60                                     # first rendered lockup frame

# ---------------------------------------------------------------- segments
def ev(take, name, nth=0):
    """Song time of a logged performance event (its call; the touch lands TOUCH later)."""
    return [e["song"] for e in TAKES[take]["events"] if e["name"] == name][nth]

segs = []
def seg(dev, take, T0, T1, sync=True, sa=None, Ta=None, ripples=True, crop=None):
    f0 = (T0 - PRE + LEAD) if sync else (sa + LEAD + (T0 - Ta))
    segs.append(dict(dev=dev, take=take, T0=round(T0, 4), T1=round(T1, 4), f0=round(f0, 4), ripples=ripples))

H = {k: bar(k) for k in range(1, 20)}   # bar downbeats
CLAP = AUD["events"]["clap"]            # beat 3 of hook bars
W1 = {"I": 26.54, "changed": 26.78, "phone": 27.24}      # "I changed my phone" (trailer time)
W2 = {"had": 29.98, "change": 30.64, "phone": 31.08}    # "had to change my phone"

# cold open -> Now Playing -> home screen (E2, synced)
seg("ph", "E2", 0.0, 5.40)
# drop: flinging through 663 songs (A6, synced: the first fling is already moving on the downbeat)
seg("ph", "A6", H[9], H[10] + 0.30)
# iPad flings (C4, anchored so its second fling launches on bar 10)
seg("pad", "C4", H[10], H[11], sync=False, sa=ev("C4", "songs.fling2.start") + TOUCH, Ta=H[10] + 0.06)
# iPhone: Albums tap on bar 11, Collections tap on its clap (A6 anchored)
seg("ph", "A6", H[11], CLAP[2], sync=False, sa=ev("A6", "seg.albums") + TOUCH, Ta=H[11])
seg("ph", "A6", CLAP[2], H[12], sync=False, sa=ev("A6", "seg.collections") + TOUCH, Ta=CLAP[2])
# iPad: Home with the hero, then the sidebar folds into the tab bar on the clap (C5 anchored)
seg("pad", "C5", H[12], CLAP[3], sync=False, sa=9.30, Ta=H[12])
seg("pad", "C5", CLAP[3], H[13], sync=False, sa=ev("C5", "sidebar.hide") + TOUCH, Ta=CLAP[3])
# iPhone: Producers, then Now Playing rises (A6 synced)
seg("ph", "A6", H[13], W1["changed"] + 0.30)
# "I changed my phone": iPad Now Playing (C4 synced)
seg("pad", "C4", W1["changed"] - 0.20, H[15] + 0.10)
# flurry on the iPhone (B2 anchored moments), labels in FLURRY
FLURRY = [  # (T0, T1, take song time, label)
    (H[15], B(57), 9.45, "Dynamic Island"),
    (B(57), B(58), 26.20, "Ask"),
    (B(58), B(58) + PER / 2, 31.35, "Your listening"),
    (B(58) + PER / 2, B(59), 29.60, "Videos"),
    (B(59), B(59) + PER / 2, 34.62, "Sleep timer"),
    (B(59) + PER / 2, H[16], 37.55, "Up Next"),
]
for T0, T1, sa, _ in FLURRY:
    seg("fl", "B2", T0, T1, sync=False, sa=sa, Ta=T0, ripples=False)
# "had to change my phone": iPad Now Playing, then back to the iPhone for the pause (C4, E2 synced)
seg("pad", "C4", H[16] - 0.05, W2["change"] + 0.30)
seg("ph", "E2", W2["change"] - 0.10, CUT_LOCK + 0.05)

# ---------------------------------------------------------------- touches
TAPS = ("play.row", "nowplaying.open", "tab.", "search", "seg.albums", "seg.collections", "seg.producers", "statusbar",
        "icon.open", "nowplaying.pause", "side.", "sidebar.", "album.open", "ask.", "sleep.", "upnext.", "island.expand")
touches = []
for i, s in enumerate(segs):
    if not s["ripples"]:
        continue
    evs = TAKES[s["take"]]["events"]; s0 = s["f0"] - LEAD
    names = [e["name"] for e in evs]
    for j, e in enumerate(evs):
        n = e["name"]
        if n.endswith(".start"):
            end = next((x for x in evs[j + 1:] if x["name"] == n[:-6] + ".end"), None)
            if not end: continue
            t0 = s["T0"] + (e["song"] + TOUCH - s0); t1 = s["T0"] + (end["song"] + TOUCH - s0)
            if s["T0"] <= t0 and t1 <= s["T1"]:
                touches.append(dict(dev=s["dev"], kind="drag", t=round(t0, 3), t1=round(t1, 3), x=e["x"], y=e["y"], x1=end["x"], y1=end["y"]))
        elif n.startswith(TAPS) and not n.endswith(".end"):
            t = s["T0"] + (e["song"] + TOUCH - s0)
            if s["T0"] - 0.001 <= t <= s["T1"] - 0.12:
                touches.append(dict(dev=s["dev"], kind="tap", t=round(t, 3), x=e["x"], y=e["y"]))

# ---------------------------------------------------------------- HTML
def vid(i, s):
    return (f'<video id="v{i}" class="clip seg" src="assets/takes/{s["take"]}.mp4" data-start="{s["T0"]}" '
            f'data-duration="{round(s["T1"] - s["T0"], 4)}" data-media-start="{s["f0"]}" data-track-index="{2 + i % 4}" muted playsinline></video>')

def device(dev_id, kind, inner_id):
    vids = "\n        ".join(vid(i, s) for i, s in enumerate(segs) if s["dev"] == dev_id)
    if dev_id == "ph":  # the test runner's icon sat on the home screen during take E2; the static wallpaper slot covers it
        vids += '\n        <img id="homePatch" src="assets/brand/home-patch.png" alt="" style="position:absolute;left:1.244%;top:32.227%;width:27.363%;height:12.204%;opacity:0" />'
    tch = "\n        ".join(f'<div class="touch" id="t{k}"></div>' for k, t in enumerate(touches) if t["dev"] == dev_id)
    edges = "".join(f'<div class="edge" style="--i:{k}"></div>' for k in range(1, 9))
    return f'''
    <div class="dev {kind}" id="{dev_id}" data-layout-allow-overflow>
      <div class="zoom" id="{inner_id}">
        {edges}
        <div class="body">
          <div class="screen">
        {vids}
        {tch}
            <div class="glare" data-layout-allow-overflow></div>
          </div>
        </div>
      </div>
    </div>'''

def build(V):
    W, Hh = (1080, 1920) if V else (1920, 1080)
    css = open(f"{HERE}/style.css").read() + (open(f"{HERE}/vertical.css").read() if V else "")
    tag = "_v" if V else ""
    tl_js = open(f"{HERE}/timeline.js").read()
    stage_cfg = {
        "start": H[9], "end": 32.86,   # on the drop: it shares track 1 with the glass plate, and an earlier start hid the plate (3 black frames)
        "events": {"b808": AUD["events"]["b808"], "clap": CLAP},
        "flings": [[H[9] - 0.30, 5.5], [H[9] + 1.0, 6.5], [H[10] + 0.06, 6.0], [H[10] + 1.2, -4.0], [H[11] + 0.5, 3.5], [H[11] + 1.6, 3.5], [H[13] + 0.8, 4.0]],
        "flingTau": 0.55,
        "phase": {"enter": H[9], "wallTurn": H[11], "morphStart": H[13] + 0.2, "morphEnd": H[14], "swap1": W1["changed"] - 0.1,
                  "flurry": H[15], "swap2": W2["change"] - 0.1, "ringIn": H[15], "ringOut": H[17] + 0.1,
                  "implodeStart": H[17] - 0.10, "implodeEnd": SONG_STOP_T + 0.05},
        "art": ART, "W": W, "H": Hh, "fov": 56 if V else 36,
    }
    data_js = ("window.AUD=" + json.dumps({"fps": AUD["fps"], "features": AUD["features"], "bands": AUD["bands"], "wave": AUD["wave"]}, separators=(",", ":")) + ";\n"
               + "window.STAGE=" + json.dumps(stage_cfg, separators=(",", ":")) + ";\n"
               + "window.SHOT=" + json.dumps({"PRE": PRE, "PER": PER, "B0": B0, "DUR": DUR, "H": H, "CLAP": CLAP, "W1": W1, "W2": W2,
                                              "FLURRY": [[a, b, l] for a, b, _, l in FLURRY], "TOUCHES": touches, "SCREEN": SCREEN,
                                              "STOP": SONG_STOP_T, "ECHO0": ECHO0, "SEGS": segs, "V": V, "CUT_LOCK": CUT_LOCK}, separators=(",", ":")) + ";\n")
    open(f"{HERE}/js/data{tag}.js", "w").write(data_js)
    
    flurry_labels = "\n    ".join(f'<div class="flabel" id="fl{k}"><span>{html.escape(l)}</span></div>' for k, (_, _, _, l) in enumerate(FLURRY))
    doc = f'''<!doctype html>
    <html lang="en">
    <head>
      <meta charset="UTF-8" />
      <meta name="viewport" content="width={W}, height={Hh}" />
      <title>Lil Gohan — trailer</title>
      <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
      <script type="importmap">
      {{ "imports": {{ "three": "https://cdn.jsdelivr.net/npm/three@0.181.2/build/three.module.js",
                      "three/addons/": "https://cdn.jsdelivr.net/npm/three@0.181.2/examples/jsm/" }} }}
      </script>
      <style>
    {css}
      </style>
    </head>
    <body>
      <div id="root" data-composition-id="main" data-start="0" data-width="{W}" data-height="{Hh}" data-duration="{DUR}" data-fps="60">
        <div id="bg"><div id="glow"></div></div>
        <canvas id="wave" class="clip" width="{2160 if V else 3840}" height="{840 if V else 1120}" data-start="0" data-duration="5.6" data-track-index="1"></canvas>
        <video id="plateIntro" class="clip plate" src="assets/plates/intro{tag}.mp4" data-start="{H[3]}" data-duration="{round(H[9] - H[3] + 0.02, 4)}" data-media-start="0.0071" data-track-index="1" muted playsinline></video>
        <canvas id="stage" data-layout-allow-overflow class="clip" width="{W * 2}" height="{Hh * 2}" data-start="{stage_cfg["start"]}" data-duration="{round(stage_cfg["end"] - stage_cfg["start"], 4)}" data-track-index="1"></canvas>
        <video id="plateLock" class="clip plate" src="assets/plates/lockup{tag}.mp4" data-start="{round(CUT_LOCK, 4)}" data-duration="{round(H[19] - CUT_LOCK, 4)}" data-media-start="{round(CUT_LOCK - LOCK_PLATE_T0, 4)}" data-track-index="1" muted playsinline></video>
        <div id="scrim"></div>
        <div id="vign"></div>
        <div id="devs">
          {device("ph", "iphone", "phz")}
          {device("pad", "ipad", "padz")}
          {device("fl", "iphone", "flz")}
        </div>
        <div id="type">
          <div class="stat" id="st1" data-layout-allow-overlap><div class="num" id="st1n" data-layout-allow-overlap>0</div><div class="lab" data-layout-allow-overlap>songs</div></div>
          <div class="stat" id="st2" data-layout-allow-overlap><div class="num">27</div><div class="lab">hours of music</div></div>
          <div class="cap" id="cp1" data-layout-allow-overlap><div class="num">68</div><div class="lab">albums</div></div>
          <div class="cap" id="cp2" data-layout-allow-overlap><div class="num">49</div><div class="lab">collections</div></div>
          <div class="cap" id="cp3" data-layout-allow-overlap><div class="num">338</div><div class="lab">producers</div></div>
        {flurry_labels}
          <div id="lock"><div id="lockName">Lil Gohan</div><div id="lockSoon">Coming Soon<span class="tm">™</span></div><div id="lockDev">iPhone&nbsp;&nbsp;·&nbsp;&nbsp;iPad</div></div>
          <div id="studio"><div id="badgeWrap"><img id="badge" src="assets/brand/uppercut-badge.png" alt="Uppercut Labs" /><div id="sweep"></div></div><div id="studioName">Uppercut Labs</div></div>
        </div>
        <div id="flash"></div>
        <div id="black"></div>
        <div id="grain"></div>
        <audio id="mix" src="assets/mix.wav" data-start="0" data-duration="{DUR}" data-track-index="0" data-volume="1"></audio>
      </div>
      <script src="js/data{tag}.js"></script>
      <script>
    {tl_js}
      </script>
      <script type="module" src="js/stage.js"></script>
    </body>
    </html>
    '''
    # the 9:16 cut is its own project (assets/js shared via symlinks): two root compositions in one folder fail lint
    # (multiple_root_compositions: the runtime may play both audio tracks)
    out = f"{HERE}/../hf-vertical/index.html" if V else f"{HERE}/index.html"
    open(out, "w").write(doc)
    print(f"{os.path.relpath(out, HERE)}: {W}x{Hh}, segments {len(segs)}, touches {len(touches)}")

build(False)
build(True)
