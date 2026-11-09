#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
"""Scaffold a HyperFrames composition from a resolved beat sheet and a brand profile.

The output is a working, check-clean starting point with exact timing and legible defaults; taste goes in after.
It never writes over hand-edited scenes: cues of kind "custom" carry their own HTML/JS.

Usage:
  hf_scaffold.py --beats beats/beats.resolved.json --brand BRAND.json --out hf/ [--size 1920x1080] [--fps 60]
                 [--audio sound/mix.wav] [--base media/talk.mp4] [--background grid|glow|solid]
                 [--captions words.json] [--hud "EDITBAY / EXPLAINER"] [--title "..."] [--extra-css scenes.css]
                 [--asset NAME=PATH ...]
                 [--look signal|ledger|arcade|silicon] (EditorialPipeline: load local look and shell CSS)
                 [--remap left=upper,right=lower]   (re-layout the same beat sheet for 1080x1920)
Cue kinds: title, side-card, lower-third, bullet, label, step, word-highlight, image-panel, takeover, custom.
  content fields: title, subtitle, kicker, icon (img path), items (list), src (image/video), html + js (custom),
  raw (custom only: no default fade in/out; the scene's js owns every tween, for hard cuts on the beat).
  enter/exit presets: fade, rise, drop, slide-from-left, slide-from-right, pop (transform and opacity only).
Writes OUT/index.html (+ OUT/index.motion.json from the beat sheet's sidecar when present) and copies media into
OUT/assets/. Runs `hyperframes init` first when OUT has no project (skills install skipped).
Rules baked in: data-fps on the root, one paused timeline registered as window.__timelines["main"], every timed
element has data-start/data-duration and class "clip", footage is muted with the mix as the only audio, animation
touches transform and opacity only, except burned caption word spans which animate opacity and colour; transforms for
captions belong on the .cap-line wrapper. There are no clocks or randomness. Legibility defaults pass text_check.py:
content labels never go under the brand's min_phone_readable, kickers/step numbers/HUD are data-decorative, headings
balance their lines, cards have no backdrop-filter (it forces HyperFrames into slow screenshot capture), and vertical
layouts use a 160-1500px safe stack on a 1920px canvas with a depth plane behind it; captions sit above platform UI.
EditorialPipeline scaffolds copy the selected local look/shell CSS and referenced fonts into OUT/brand/, normalize font URLs to
/brand/fonts/, and use literal hex colors for caption tweens. Explicit `--asset` files are copied into OUT/assets/;
existing project-local assets are preserved on reruns.
"""
import argparse, html, json, os, re, shutil, subprocess

PORTRAIT_SAFE_TOP = 160 / 1920
PORTRAIT_SAFE_BOTTOM = 1500 / 1920
PORTRAIT_CAPTION_FLOOR = 0.70

ZONES = {  # fractions of the canvas: x0, y0, x1, y1, flex alignment (justify, align)
    "left": (0.05, 0.08, 0.40, 0.92, "flex-start", "center"),
    "right": (0.60, 0.08, 0.95, 0.92, "flex-end", "center"),
    "top": (0.05, 0.06, 0.95, 0.30, "center", "flex-start"),
    "bottom": (0.05, 0.70, 0.95, 0.94, "center", "flex-end"),
    "center": (0.08, 0.10, 0.92, 0.90, "center", "center"),
    "full": (0.0, 0.0, 1.0, 1.0, "center", "center"),
    "pip-tl": (0.03, 0.04, 0.33, 0.36, "flex-start", "flex-start"),
    "pip-tr": (0.67, 0.04, 0.97, 0.36, "flex-end", "flex-start"),
    "pip-bl": (0.03, 0.64, 0.33, 0.96, "flex-start", "flex-end"),
    "pip-br": (0.67, 0.64, 0.97, 0.96, "flex-end", "flex-end"),
    # portrait zones for vertical cuts (--remap left=upper,right=lower); see zone_box for the vertical safe area
    "upper": (0.06, PORTRAIT_SAFE_TOP, 0.88, 0.40, "center", "center"),
    "lower": (0.06, 0.42, 0.88, PORTRAIT_SAFE_BOTTOM, "center", "center"),
}
ENTER_BY_ZONE = {"left": "slide-from-left", "right": "slide-from-right", "bottom": "rise", "top": "drop",
                 "center": "pop", "full": "fade", "upper": "drop", "lower": "rise"}
PRESET = {"fade": {}, "rise": {"y": 40}, "drop": {"y": -34}, "slide-from-left": {"x": -90}, "slide-from-right": {"x": 90},
          "pop": {"scale": 0.86}}
EASE_IN = {"pop": "back.out(1.5)"}
esc = lambda s: html.escape(str(s or ""))


def google_fonts(brand):
    fams = []
    for role in ("display", "body", "mono"):
        f = (brand.get("fonts") or {}).get(role) or {}
        if f.get("family") and f["family"] not in [x[0] for x in fams]:
            fams.append((f["family"], sorted(set(f.get("weights") or [400, 700]))))
    q = "&".join(f"family={f.replace(' ', '+')}:wght@{';'.join(str(w) for w in ws)}" for f, ws in fams)
    return f'<link href="https://fonts.googleapis.com/css2?{q}&display=block" rel="stylesheet" />' if fams else ""


def explicit_color(value, fallback):
    return value if isinstance(value, str) and re.fullmatch(r"#[0-9a-fA-F]{3,8}", value.strip()) else fallback


def EditorialPipeline_styles(brand_path, look_data, out, look):
    """Copy the selected local CSS and its fonts, normalizing parent-traversal font URLs."""
    brand_dir = os.path.dirname(os.path.abspath(brand_path))
    repo_dir = os.path.dirname(brand_dir)
    sources = [
        (os.path.join(repo_dir, look_data["css"]), os.path.join(out, "brand", "looks", look, "look.css")),
        (os.path.join(brand_dir, "shell", "shell.css"), os.path.join(out, "brand", "shell", "shell.css")),
    ]
    for source, _ in sources:
        if not os.path.isfile(source):
            raise SystemExit(f"hf_scaffold: missing local EditorialPipeline stylesheet: {source}")
    copied = []
    for source, target in sources:
        text = open(source, encoding="utf-8").read()
        text = re.sub(r"url\(([\"']?)(?:\.\./)+fonts/([^\)\"']+)\1\)", r'url("/brand/fonts/\2")', text)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        open(target, "w", encoding="utf-8").write(text)
        copied.append((source, text))
        for font in sorted(set(re.findall(r'url\("/brand/fonts/([^"/]+)"\)', text))):
            source_font = os.path.join(brand_dir, "fonts", font)
            if not os.path.isfile(source_font):
                raise SystemExit(f"hf_scaffold: missing local EditorialPipeline font: {source_font}")
            target_font = os.path.join(out, "brand", "fonts", font)
            os.makedirs(os.path.dirname(target_font), exist_ok=True)
            shutil.copy2(source_font, target_font)
    return copied


def EditorialPipeline_caption_colors(brand_path, look_data, brand):
    """Read look caption tokens as literals so GSAP never interpolates CSS variables."""
    fallback_muted = explicit_color((brand.get("palette") or {}).get("text_muted"), "#a3abb8")
    fallback_accent = explicit_color((brand.get("palette") or {}).get("accent"), "#5b8cff")
    source = os.path.join(os.path.dirname(os.path.abspath(brand_path)), "..", look_data["css"])
    source = os.path.abspath(source)
    if not os.path.isfile(source):
        raise SystemExit(f"hf_scaffold: missing local EditorialPipeline stylesheet: {source}")
    text = open(source, encoding="utf-8").read()
    def token(name, fallback):
        match = re.search(rf"--{re.escape(name)}\s*:\s*([^;]+);", text)
        return explicit_color(match.group(1).strip() if match else "", fallback)
    return token("cb-cap-ink", fallback_muted), token("cb-cap-hi", fallback_accent)


def css(brand, W, H, background):
    p, f, sc = brand.get("palette", {}), brand.get("fonts", {}), brand.get("type_scale_px_1080p", {})
    k = H / 1080 if W >= H else W / 1080
    px = lambda v: f"{round(v * k)}px"
    fam = lambda role, fb: f"'{(f.get(role) or {}).get('family', fb)}', {fb}"
    radius = (brand.get("shape") or {}).get("radius_px", [10, 14])
    EditorialPipeline = brand.get("id") == "EditorialPipeline"
    bg = {"solid": "var(--bg)",
          "glow": "radial-gradient(1200px 700px at 70% 30%, color-mix(in srgb, var(--accent) 22%, transparent), transparent 70%), var(--bg)",
          "grid": ("radial-gradient(1100px 650px at 72% 28%, color-mix(in srgb, var(--accent) 20%, transparent), transparent 70%),"
                   " linear-gradient(color-mix(in srgb, var(--text) 5%, transparent) 1px, transparent 1px) 0 0 / 32px 32px,"
                   " linear-gradient(90deg, color-mix(in srgb, var(--text) 5%, transparent) 1px, transparent 1px) 0 0 / 32px 32px,"
                   " var(--bg)")}[background]
    # Vertical: keep captions above the bottom band that Shorts, Reels and TikTok cover with their own UI.
    cap_bottom = f"{round(0.26 * H)}px" if H > W else px(56)
    cap_right = "12%" if H > W else "6%"
    if EditorialPipeline:
        bg_token, surface_token, text_token = "var(--cb-bg)", "var(--cb-surface)", "var(--cb-text)"
        muted_token, accent_token, line_token = "var(--cb-muted)", "var(--cb-accent)", "var(--cb-line)"
        radius_token, radius_sm_token = "var(--cb-radius)", "var(--cb-radius-sm)"
        display_token, body_token, mono_token = "var(--cb-font-display)", "var(--cb-font-body)", "var(--cb-font-mono)"
        scale = {"hero": "var(--cb-v-hero)" if H > W else "var(--cb-w-hero)",
                 "headline": "var(--cb-v-headline)" if H > W else "var(--cb-w-headline)",
                 "body": "var(--cb-v-body)" if H > W else "var(--cb-w-body)",
                 "label": "var(--cb-v-label)" if H > W else "var(--cb-w-label)",
                 "small": "var(--cb-v-min)" if H > W else "var(--cb-w-min)"}
    else:
        bg_token, surface_token, text_token = p.get("background", "#0e1014"), p.get("surface", "#171a21"), p.get("text", "#f2f4f8")
        muted_token, accent_token, line_token = p.get("text_muted", "#a3abb8"), p.get("accent", "#5b8cff"), p.get("line", "#2b323c")
        radius_token, radius_sm_token = f"{radius[-1]}px", f"{radius[0]}px"
        display_token, body_token, mono_token = fam("display", "Inter, sans-serif"), fam("body", "Inter, sans-serif"), fam("mono", "ui-monospace, monospace")
        scale = {"hero": px(sc.get("hero", 120)), "headline": px(sc.get("headline", 72)),
                 "body": px(sc.get("body", 44)), "label": px(sc.get("label", 28)),
                 "small": px(max(sc.get("label", 28), sc.get("min_phone_readable", 36)))}
    return f"""
      :root {{
        --bg: {bg_token}; --surface: {surface_token}; --text: {text_token};
        --muted: {muted_token}; --accent: {accent_token}; --line: {line_token};
        --radius: {radius_token}; --radius-sm: {radius_sm_token};
        --font-display: {display_token}; --font-body: {body_token}; --font-mono: {mono_token};
        --hero: {scale['hero']}; --headline: {scale['headline']}; --body: {scale['body']};
        --label: {scale['label']}; --small: {scale['small']};
      }}
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{ width: {W}px; height: {H}px; overflow: hidden; background: var(--bg); }}
      #root {{ position: relative; width: {W}px; height: {H}px; overflow: hidden; color: var(--text); font-family: var(--font-body);
               overflow-wrap: normal; word-break: normal; hyphens: manual; }}
      #bg {{ position: absolute; inset: 0; background: {bg}; }}
      #bg-glow {{ position: absolute; inset: -10%; background: radial-gradient(800px 500px at 30% 70%, color-mix(in srgb, var(--accent) 10%, transparent), transparent 70%); }}
      #base {{ position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }}
      .zone {{ position: absolute; display: flex; pointer-events: none; }}
      .zone > .clip {{ position: relative; }}
      .z-full > .clip {{ width: 100%; height: 100%; }}
      .card {{ background: color-mix(in srgb, var(--surface) 94%, transparent);
              border: 1px solid color-mix(in srgb, var(--text) 13%, transparent); border-radius: var(--radius);
              box-shadow: 0 {px(18)} {px(60)} rgba(0,0,0,.38); padding: {px(28)} {px(36)}; max-width: 100%; }}
      .card .row {{ display: flex; align-items: center; gap: {px(24)}; }}
      .card img.icon {{ width: {px(96)}; height: {px(96)}; object-fit: contain; }}
      .kicker {{ font-family: var(--font-mono); font-size: var(--label); letter-spacing: .11em; text-transform: uppercase;
                color: var(--accent); margin-bottom: {px(10)}; }}
      .t-title {{ font-family: var(--font-display); font-weight: 750; font-size: var(--headline); letter-spacing: -0.035em; line-height: 1.02; text-wrap: balance; }}
      .t-sub {{ font-size: var(--body); color: var(--muted); margin-top: {px(10)}; line-height: 1.25; text-wrap: pretty; }}
      .hero {{ font-family: var(--font-display); font-weight: 800; font-size: var(--hero); letter-spacing: -0.045em; line-height: .98; text-align: center; text-wrap: balance; }}
      .hero .w {{ display: inline-block; margin-right: .22em; }}
      .lt {{ display: flex; gap: {px(18)}; align-items: stretch; }}
      .lt .bar {{ width: {px(8)}; background: var(--accent); border-radius: 4px; }}
      .bullets {{ list-style: none; }}
      .bullets li {{ font-size: var(--body); line-height: 1.3; margin: {px(8)} 0; display: flex; gap: {px(16)}; text-wrap: pretty; }}
      .bullets li::before {{ content: ""; width: {px(12)}; height: {px(12)}; margin-top: {px(18)}; border-radius: 50%; background: var(--accent); flex: none; }}
      .pill {{ font-family: var(--font-mono); font-size: var(--small); padding: {px(10)} {px(18)}; border-radius: 999px;
              border: 1px solid var(--accent); color: var(--text); background: color-mix(in srgb, var(--bg) 70%, transparent); }}
      .step .num {{ font-family: var(--font-mono); font-size: var(--label); color: var(--accent); letter-spacing: .12em; }}
      .panel {{ padding: {px(12)}; }}
      .panel img, .panel video {{ display: block; width: 100%; border-radius: var(--radius-sm); }}
      .panel .cap {{ font-family: var(--font-mono); font-size: var(--small); color: var(--muted); margin-top: {px(10)}; }}
      .band {{ font-family: var(--font-display); font-weight: 700; font-size: var(--headline); letter-spacing: -0.02em; text-wrap: balance; }}
      .band .w {{ position: relative; display: inline-block; margin: 0 .16em; isolation: isolate; }}
      .cap-line .w {{ display: inline-block; margin: 0 .16em; color: var(--muted); opacity: .72; }}
      /* the highlight sits under the word (z 0 < 1) without a negative z-index; GSAP owns its scaleX (no CSS transform) */
      .band .w .hl {{ position: absolute; left: -0.08em; right: -0.08em; bottom: .06em; height: .30em;
              background: var(--accent); border-radius: 3px; z-index: 0; transform-origin: left center; }}
      .band .w .tx {{ position: relative; z-index: 1; }}
      .takeover {{ position: absolute; inset: 0; background: var(--bg); display: flex; flex-direction: column;
              align-items: center; justify-content: center; text-align: center; }}
      .cap-line {{ position: absolute; left: 6%; right: {cap_right}; bottom: {cap_bottom}; text-align: center; font-family: var(--font-display);
              font-weight: 700; font-size: {px(60 if H > W else 54)}; line-height: 1.15; text-shadow: 0 2px 12px rgba(0,0,0,.65); text-wrap: balance; }}
      #hud {{ position: absolute; inset: {px(28)}; pointer-events: none; font-family: var(--font-mono); font-size: {px(18)};
              letter-spacing: .12em; color: color-mix(in srgb, var(--text) 62%, transparent); text-transform: uppercase; }}
      #hud .c {{ position: absolute; width: {px(26)}; height: {px(26)}; border-color: color-mix(in srgb, var(--text) 45%, transparent); border-style: solid; }}
      #hud .tl {{ left: 0; top: 0; border-width: 2px 0 0 2px; }} #hud .tr {{ right: 0; top: 0; border-width: 2px 2px 0 0; }}
      #hud .bl {{ left: 0; bottom: 0; border-width: 0 0 2px 2px; }} #hud .br {{ right: 0; bottom: 0; border-width: 0 2px 2px 0; }}
      #hud .lab {{ position: absolute; left: {px(40)}; top: {px(4)}; }} #hud .tc {{ position: absolute; left: {px(40)}; bottom: {px(4)}; }}
"""


def zone_box(zone, W, H, captions):
    """Zone fractions, kept inside the safe area. Vertical: the bottom 26% and the right 12% stay clear for the
    Shorts/Reels/TikTok UI, and with captions on the zones stop above the caption band (0.64-0.74). Landscape with
    captions: zones stop at 0.86, above the caption line."""
    x0, y0, x1, y1, just, align = ZONES.get(zone, ZONES["center"])
    if zone == "full":
        return x0, y0, x1, y1, just, align
    portrait = H > W
    if portrait and zone == "center":
        x0, y0, x1, y1 = 0.06, PORTRAIT_SAFE_TOP, 0.88, PORTRAIT_SAFE_BOTTOM
    floor = (PORTRAIT_CAPTION_FLOOR if captions else PORTRAIT_SAFE_BOTTOM) if portrait else (0.86 if captions else 1.0)
    if y1 > floor:
        y1 = floor
        if y1 - y0 < 0.12:
            y0 = max(0.02, y1 - 0.18)
    if portrait:
        x1 = min(x1, 0.88)
    return x0, y0, x1, y1, just, align


def zone_div(cid, zone, W, H, inner, extra_cls="", captions=False):
    x0, y0, x1, y1, just, align = zone_box(zone, W, H, captions)
    style = (f"left:{x0 * W:.0f}px;top:{y0 * H:.0f}px;width:{(x1 - x0) * W:.0f}px;height:{(y1 - y0) * H:.0f}px;"
             f"justify-content:{just};align-items:{align};")
    return f'<div class="zone {extra_cls}" style="{style}">{inner}</div>'


def words_in(words, s, e):
    return [w for w in words if w["start"] >= s - 0.05 and w["start"] < e]


def cue_html(c, W, H, words, captions=False):
    cid, kind, ct = c["id"], c.get("kind", "title"), c.get("content") or {}
    dur = round(c["end"] - c["start"], 4)
    timing = f'class="clip" data-start="{c["start"]}" data-duration="{dur}"'
    kicker = f'<div class="kicker" data-decorative>{esc(ct.get("kicker"))}</div>' if ct.get("kicker") else ""
    title = f'<div class="t-title">{esc(ct.get("title"))}</div>' if ct.get("title") else ""
    sub = f'<div class="t-sub">{esc(ct.get("subtitle"))}</div>' if ct.get("subtitle") else ""
    icon = f'<img class="icon" src="{esc(ct["icon"])}" alt="" />' if ct.get("icon") else ""
    zone = c.get("zone", "center")
    if kind == "title":
        spans = "".join(f'<span class="w">{esc(w)}</span>' for w in str(ct.get("title", "")).split())
        inner = f'<div id="{cid}" {timing}><div class="hero">{spans}</div>{sub}</div>'
    elif kind in ("side-card", "step"):
        num = f'<div class="num" data-decorative>{esc(ct.get("number"))}</div>' if ct.get("number") else ""
        inner = f'<div id="{cid}" {timing} class="card {kind}"><div class="row">{icon}<div>{num}{kicker}{title}{sub}</div></div></div>'
        inner = inner.replace(f'{timing} class="card', f'data-start="{c["start"]}" data-duration="{dur}" class="clip card')
    elif kind == "lower-third":
        inner = (f'<div id="{cid}" class="clip card lt" data-start="{c["start"]}" data-duration="{dur}">'
                 f'<div class="bar"></div><div>{kicker}{title}{sub}</div></div>')
    elif kind == "bullet":
        items = "".join(f'<li class="it">{esc(i)}</li>' for i in ct.get("items", [ct.get("title", "")]))
        inner = (f'<div id="{cid}" class="clip card" data-start="{c["start"]}" data-duration="{dur}">{kicker}'
                 f'{title if ct.get("items") else ""}<ul class="bullets">{items}</ul></div>')
    elif kind == "label":
        inner = f'<div id="{cid}" class="clip pill" data-start="{c["start"]}" data-duration="{dur}">{esc(ct.get("title"))}</div>'
    elif kind == "word-highlight":
        ws = words_in(words, c["start"], c["end"])
        spans = "".join(f'<span class="w" data-t="{w["start"]}"><span class="hl"></span><span class="tx">{esc(w["text"])}</span></span>' for w in ws)
        inner = f'<div id="{cid}" class="clip card band" data-start="{c["start"]}" data-duration="{dur}">{spans}</div>'
    elif kind == "image-panel":
        src = ct.get("src", "")
        media = (f'<video src="{esc(src)}" muted playsinline data-start="{c["start"]}" data-duration="{dur}" class="clip"></video>'
                 if src.lower().endswith((".mp4", ".webm", ".mov")) else f'<img src="{esc(src)}" alt="" />')
        cap = f'<div class="cap">{esc(ct.get("label"))}</div>' if ct.get("label") else ""
        inner = (f'<div id="{cid}" class="clip card panel" data-start="{c["start"]}" data-duration="{dur}" '
                 f'style="width:{ct.get("width", 0.8) * 100:.0f}%">{media}{cap}</div>')
    elif kind == "takeover":
        inner = (f'<div id="{cid}" class="clip takeover" data-start="{c["start"]}" data-duration="{dur}">'
                 f'{kicker}<div class="hero">{esc(ct.get("title"))}</div>{sub}</div>')
    elif kind == "custom":
        inner = f'<div id="{cid}" class="clip" data-start="{c["start"]}" data-duration="{dur}">{ct.get("html", "")}</div>'
    else:
        inner = f'<div id="{cid}" class="clip card" data-start="{c["start"]}" data-duration="{dur}">{title}{sub}</div>'
    return zone_div(cid, zone, W, H, inner, extra_cls=f"z-{zone}", captions=captions)


def cue_js(c, words):
    cid, kind = c["id"], c.get("kind", "title")
    s, e = c["start"], c["end"]
    enter = c.get("enter") or ENTER_BY_ZONE.get(c.get("zone", "center"), "fade")
    frm = {**PRESET.get(enter, {}), "opacity": 0}
    ease = EASE_IN.get(enter, "power3.out")
    lines = []
    if kind == "title":
        lines.append(f'tl.fromTo("#{cid} .w", {{opacity: 0, y: 46}}, {{opacity: 1, y: 0, duration: 0.5, ease: "power3.out", stagger: 0.07}}, {s});')
        if (c.get("content") or {}).get("subtitle"):
            lines.append(f'tl.fromTo("#{cid} .t-sub", {{opacity: 0}}, {{opacity: 1, duration: 0.4}}, {s + 0.25});')
    elif kind == "custom":
        raw = (c.get("content") or {}).get("raw")
        if not raw:  # raw scenes own their entrance and exit (hard cuts on the beat)
            lines.append(f'tl.fromTo("#{cid}", {{opacity: 0}}, {{opacity: 1, duration: 0.35, ease: "power2.out"}}, {s});')
        if (c.get("content") or {}).get("js"):
            lines.append("{ const S = %s, E = %s; %s }" % (s, e, c["content"]["js"]))
        if raw:
            return "\n      ".join(lines)
    else:
        lines.append(f'tl.fromTo("#{cid}", {json.dumps(frm)}, {{opacity: 1, x: 0, y: 0, scale: 1, duration: 0.5, ease: "{ease}"}}, {s});')
    if kind == "bullet":
        lines.append(f'tl.fromTo("#{cid} .it", {{opacity: 0, x: -24}}, {{opacity: 1, x: 0, duration: 0.35, stagger: 0.28, ease: "power2.out"}}, {s + 0.25});')
    if kind == "word-highlight":
        for w in words_in(words, s, e):
            lines.append(f'tl.fromTo("#{cid} .w[data-t=\\"{w["start"]}\\"] .hl", {{scaleX: 0}}, {{scaleX: 1, duration: 0.14, ease: "power2.out"}}, {w["start"]});')
    if c.get("zone") != "full" or kind != "takeover":
        lines.append(f'tl.to("#{cid}", {{opacity: 0, y: {"-16" if c.get("zone") != "top" else "16"}, duration: 0.3, ease: "power2.in"}}, {max(s + 0.6, e - 0.32)});')
    else:
        lines.append(f'tl.to("#{cid}", {{opacity: 0, duration: 0.3}}, {max(s + 0.6, e - 0.32)});')
    return "\n      ".join(lines)


def caption_lines(words, max_words=7, max_chars=34, gap=0.35):
    lines, cur = [], []
    for i, w in enumerate(words):
        cur.append(w)
        nxt = words[i + 1] if i + 1 < len(words) else None
        text = " ".join(x["text"] for x in cur)
        if (nxt is None or len(cur) >= max_words or len(text) >= max_chars or re.search(r"[.!?]$", w["text"])
                or (nxt and nxt["start"] - w["end"] > gap)):
            lines.append(cur); cur = []
    return lines


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--beats", required=True); ap.add_argument("--brand", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--size", default="1920x1080"); ap.add_argument("--fps", type=int, default=60)
    ap.add_argument("--audio"); ap.add_argument("--base"); ap.add_argument("--background", choices=["grid", "glow", "solid"], default="grid")
    ap.add_argument("--captions"); ap.add_argument("--hud"); ap.add_argument("--title", default="editbay composition")
    ap.add_argument("--words", help="word array for word-highlight cues (defaults to the beat sheet's words)")
    ap.add_argument("--hf-version", default=os.environ.get("EDITBAY_HF_VERSION", "0.8.79"))
    ap.add_argument("--extra-css", help="a CSS file appended to the generated styles (custom scenes; rerun after edits)")
    ap.add_argument("--asset", action="append", default=[], metavar="NAME=PATH",
                    help="copy a project-local asset into OUT/assets/ without removing existing assets")
    ap.add_argument("--look", choices=["signal", "ledger", "arcade", "silicon"], help="EditorialPipeline local look CSS")
    ap.add_argument("--remap", default="", help="zone remap for a re-layout, e.g. left=upper,right=lower (vertical cuts)")
    a = ap.parse_args()
    remap = dict(kv.split("=") for kv in a.remap.split(",") if "=" in kv)
    W, H = (int(x) for x in a.size.split("x"))
    sheet = json.load(open(a.beats)); brand = json.load(open(a.brand))
    EditorialPipeline = brand.get("id") == "EditorialPipeline"
    look = a.look or brand.get("look") or "signal"
    look_data = (brand.get("looks") or {}).get(look) if EditorialPipeline else None
    if EditorialPipeline and not look_data:
        raise SystemExit(f"hf_scaffold: unknown EditorialPipeline look {look!r}")
    caption_muted, caption_accent = (EditorialPipeline_caption_colors(a.brand, look_data, brand) if EditorialPipeline else
                                     (explicit_color((brand.get("palette") or {}).get("text_muted"), "#a3abb8"),
                                      explicit_color((brand.get("palette") or {}).get("accent"), "#5b8cff")))
    base_dir = os.path.dirname(os.path.abspath(a.beats))
    dur = sheet["duration"]
    wpath = a.words or (os.path.join(base_dir, sheet["words"]) if sheet.get("words") else None)
    words = []
    if wpath and os.path.exists(wpath):
        d = json.load(open(wpath))
        words = d if isinstance(d, list) else [{"text": w[2].strip(), "start": w[0], "end": w[1]} for s in d["segments"] for w in s["words"]]
    if not os.path.exists(os.path.join(a.out, "hyperframes.json")):
        parent, name = os.path.split(os.path.abspath(a.out))
        env = {k: v for k, v in os.environ.items() if not k.endswith("_API_KEY")} | {"HYPERFRAMES_SKIP_SKILLS": "1"}
        subprocess.run(["npx", "-y", f"hyperframes@{a.hf_version}", "init", name, "--example", "blank", "--non-interactive"],
                       cwd=parent, env=env, capture_output=True)
    os.makedirs(os.path.join(a.out, "assets"), exist_ok=True)

    def asset(path, name=None):
        if not path:
            return None
        source = os.path.abspath(path)
        if not os.path.isfile(source):
            raise SystemExit(f"hf_scaffold: missing asset: {path}")
        name = (name or os.path.basename(source)).replace("\\", "/")
        if not name or name.startswith("/") or any(part in ("", ".", "..") for part in name.split("/")):
            raise SystemExit("hf_scaffold: asset name must be a relative path without . or .. components")
        dst = os.path.join(a.out, "assets", *name.split("/"))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if source != os.path.abspath(dst):
            shutil.copy2(source, dst)
        return f"assets/{name}"

    for spec in a.asset:
        if "=" not in spec:
            raise SystemExit("hf_scaffold: --asset must be NAME=PATH")
        name, path = spec.split("=", 1)
        if not name or not path:
            raise SystemExit("hf_scaffold: --asset must include a name and path")
        source = path if os.path.isabs(path) else (os.path.join(base_dir, path) if os.path.isfile(os.path.join(base_dir, path)) else path)
        asset(source, name)

    for c in sheet["cues"]:
        if c.get("zone") in remap:
            c["zone"] = remap[c["zone"]]
        ct = c.get("content") or {}
        for k in ("icon", "src"):
            if ct.get(k) and os.path.exists(os.path.join(base_dir, ct[k])):
                ct[k] = asset(os.path.join(base_dir, ct[k]))
    audio = asset(a.audio); base = asset(a.base)
    body = [f'<div id="bg" class="clip" data-start="0" data-duration="{dur}"></div>',
            f'<div id="bg-glow" class="clip" data-start="0" data-duration="{dur}"></div>']
    if base:  # top level: HyperFrames cannot extract frames from a timed video nested in a timed element
        body.append(f'<video id="base" src="{base}" muted playsinline data-start="0" data-duration="{dur}" class="clip"></video>')
    shown = [c for c in sheet["cues"] if c.get("kind") != "sfx"]  # sfx cues only drive the mix
    # Two cues in one zone at once overlap on screen; common when a 16:9 sheet is re-laid out with --remap for 9:16.
    for i, c1 in enumerate(shown):
        for c2 in shown[i + 1:]:
            z = c1.get("zone", "center")
            if z != "full" and z == c2.get("zone", "center") and c1["start"] < c2["end"] - 0.05 and c2["start"] < c1["end"] - 0.05:
                print(f"warning: {c1['id']} and {c2['id']} share zone {z} at {max(c1['start'], c2['start']):g}s; "
                      f"move one (beat sheet zone or --remap)")
    body += [cue_html(c, W, H, words, captions=bool(a.captions)) for c in shown]
    js = [cue_js(c, words) for c in shown]
    js.append(f'tl.fromTo("#bg-glow", {{x: -60, y: 30}}, {{x: 60, y: -30, duration: {dur}, ease: "none"}}, 0);')
    if a.captions:
        cw = json.load(open(a.captions))
        cw = cw if isinstance(cw, list) else [{"text": w[2].strip(), "start": w[0], "end": w[1]} for s in cw["segments"] for w in s["words"]]
        for k, line in enumerate(caption_lines(cw)):
            s, e = line[0]["start"], max(line[-1]["end"], line[0]["start"] + 0.6)
            spans = " ".join(f'<span class="w" data-t="{w["start"]}"><span class="tx">{esc(w["text"])}</span></span>' for w in line)
            body.append(f'<div id="cap{k}" class="clip cap-line" data-start="{round(s, 3)}" data-duration="{round(e - s, 3)}" '
                        f'data-layout-allow-caption-zone>{spans}</div>')
            caption_js = []
            for i, w in enumerate(line):
                if i:
                    previous = line[i - 1]
                    previous_selector = f'#cap{k} .w[data-t=\\"{previous["start"]}\\"]'
                    caption_js.append(f'tl.to("{previous_selector}", {{opacity: 0.72, color: {json.dumps(caption_muted)}, duration: 0.12, ease: "none"}}, {w["start"]});')
                selector = f'#cap{k} .w[data-t=\\"{w["start"]}\\"]'
                caption_js.append(f'tl.to("{selector}", {{opacity: 1, color: {json.dumps(caption_accent)}, duration: 0.12, ease: "none"}}, {w["start"]});')
            js += caption_js
    if a.hud:
        body.append(f'<div id="hud" class="clip" data-decorative data-start="0" data-duration="{dur}"><div class="c tl"></div><div class="c tr"></div>'
                    f'<div class="c bl"></div><div class="c br"></div><div class="lab">{esc(a.hud)}</div>'
                    f'<div class="tc" id="hud-tc">TC 00:00:00:00</div></div>')
        js.append(f'const tc = document.getElementById("hud-tc"); const pad = (n) => String(n).padStart(2, "0");'
                  f' tl.eventCallback("onUpdate", () => {{ const t = tl.time(); const f = Math.floor((t % 1) * {a.fps});'
                  f' tc.textContent = `TC 00:00:${{pad(Math.floor(t))}}:${{pad(f)}}`; }});')
    if audio:
        body.append(f'<audio id="mix" src="{audio}" data-start="0" data-duration="{dur}" data-volume="1"></audio>')
    extra_css = ("\n/* Inlined from " + os.path.basename(a.extra_css) + "; rerun hf_scaffold.py after editing that file. */\n"
                 + open(a.extra_css, encoding="utf-8").read()) if a.extra_css else ""
    if EditorialPipeline:
        EditorialPipeline_styles(a.brand, look_data, a.out, look)
        links = (f'<link rel="stylesheet" href="{html.escape(look_data["css"], quote=True)}" />\n'
                 '    <link rel="stylesheet" href="brand/shell/shell.css" />')
        root_class = "cb-frame cb-frame--v" if H > W else "cb-frame cb-frame--w"
    else:
        links = ('<link rel="preconnect" href="https://fonts.googleapis.com" />'
                 '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />\n    ' + google_fonts(brand))
        root_class = ""
    extra_notice = (f"<!-- extra CSS is inlined from {os.path.basename(a.extra_css)}; rerun hf_scaffold.py after edits -->"
                    if a.extra_css else "")
    doc = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width={W}, height={H}" />
    <title>{esc(a.title)}</title>
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
    {links}
    <style>{css(brand, W, H, a.background)}{extra_css}
    </style>
  </head>
  <body>
    <!-- scaffolded by editbay hf_scaffold.py from {os.path.basename(a.beats)}; brand {brand.get('id')} -->
    {extra_notice}
    <div id="root" class="{root_class}" data-composition-id="main" data-start="0" data-duration="{dur}" data-fps="{a.fps}" data-width="{W}" data-height="{H}">
      {chr(10).join('      ' + b for b in body).strip()}
    </div>
    <script>
      window.__timelines = window.__timelines || {{}};
      const tl = gsap.timeline({{ paused: true }});
      {(chr(10) + '      ').join(js)}
      window.__timelines["main"] = tl;
    </script>
  </body>
</html>
"""
    open(os.path.join(a.out, "index.html"), "w").write(doc)
    side = [f for f in os.listdir(base_dir) if f.endswith(".motion.json")]
    if side:
        shutil.copy2(os.path.join(base_dir, side[0]), os.path.join(a.out, "index.motion.json"))
    print(f"wrote {os.path.join(a.out, 'index.html')}: {len(sheet['cues'])} cues, {W}x{H}@{a.fps}, {dur}s"
          + (", captions" if a.captions else "") + (", hud" if a.hud else "") + (f", audio {audio}" if audio else "")
          + (", motion sidecar" if side else "") + (f", EditorialPipeline {look} local shell" if EditorialPipeline else "")
          + (f"; extra CSS inlined from {os.path.basename(a.extra_css)} — rerun scaffold after edits" if a.extra_css else ""))


if __name__ == "__main__":
    main()
