#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["playwright>=1.45"]
# ///
"""Text a viewer can read on a phone: every text element in a HyperFrames composition at or above the brand's phone
minimum, and no word broken across two lines.

Why: a Codex run (2026-09-26) shipped 18-26 px body text against a brand minimum of 36 px, and a label that broke
mid-word; its eyeball check at phone size passed both. This makes the rule mechanical.

Usage:
  text_check.py hf/ --brand BRAND.json [--min 36] [--json qa/text.json]
Loads hf/index.html in headless Chrome at the canvas size with GSAP blocked, so every element sits in its resting
CSS state (the timeline does not run; web fonts load when online, so line breaks match the render). Checks:
  size    computed font size (times any resting CSS scale; SVG text times its on-screen scale) below the minimum: error
  broken  a word that wraps onto two lines (a long label in a narrow box): error
  widow   a heading (.t-title, .hero, h1-h3, or any text block at 1.5x the minimum) ending in a one-word line: warning
Minimum: --min, else the portrait brand's type_scale_px_1080p.min_phone_readable (min_phone_readable_9x16 when present)
or the landscape brand's type_scale_px_1920x1080.min_readable, scaled the way hf_scaffold scales type (x height/1080
landscape, x width/1080 portrait); default 36.
Text inside an element with data-decorative (kickers that repeat a title, HUD labels, step numbers) is listed but
never fails: never put information only in decorative text. Exit 1 on any error.
Chrome: the installed Google Chrome, else EDITBAY_CHROME, else HyperFrames' cached chrome-headless-shell.
"""
import argparse, glob, json, os, re, sys

JS = r"""
async (minPx) => {
  await document.fonts.ready;
  const root = document.querySelector('[data-composition-id]') || document.body;
  const pathOf = (el) => {
    const p = [];
    for (let e = el; e && e !== root && p.length < 4; e = e.parentElement) {
      p.unshift(e.id ? '#' + e.id : e.tagName.toLowerCase() + [...e.classList].slice(0, 2).map(c => '.' + c).join(''));
      if (e.id) break;
    }
    return p.join(' > ');
  };
  const scaleOf = (el) => {
    if (el instanceof SVGElement) {
      const m = el.getScreenCTM && el.getScreenCTM();
      return m ? Math.sqrt(Math.abs(m.a * m.d - m.b * m.c)) : 1;
    }
    const r = el.getBoundingClientRect();
    return (el.offsetWidth > 0 && r.width > 0) ? r.width / el.offsetWidth : 1;
  };
  const wordRects = (node) => {
    const out = []; const re = /\S+/g; let m;
    while ((m = re.exec(node.textContent))) {
      const r = document.createRange(); r.setStart(node, m.index); r.setEnd(node, m.index + m[0].length);
      const rects = [...r.getClientRects()].filter(x => x.width > 0.5 && x.height > 0.5);
      out.push({ word: m[0], tops: [...new Set(rects.map(x => Math.round(x.top)))] });
    }
    return out;
  };
  const items = []; const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT); let n;
  while ((n = walker.nextNode())) {
    const text = n.textContent.replace(/\s+/g, ' ').trim(); const el = n.parentElement;
    if (!text || !el || ['SCRIPT', 'STYLE', 'TITLE', 'NOSCRIPT'].includes(el.tagName)) continue;
    const cs = getComputedStyle(el);
    if (cs.display === 'none') continue;
    const broken = wordRects(n).filter(w => w.word.length >= 3 && w.tops.length > 1).map(w => w.word);
    items.push({ text: text.slice(0, 80), size: Math.round(parseFloat(cs.fontSize) * scaleOf(el) * 10) / 10,
                 decorative: !!el.closest('[data-decorative]'), path: pathOf(el), broken });
  }
  const widows = [];
  // Headings: the scaffold's title classes and h1-h3, plus any leaf block set at 1.5x the minimum or larger.
  const heads = new Set(root.querySelectorAll('.t-title, .hero, h1, h2, h3'));
  for (const el of root.querySelectorAll('*')) {
    const cs = getComputedStyle(el);
    if (parseFloat(cs.fontSize) < 1.5 * minPx || cs.display.startsWith('inline') || cs.display === 'none') continue;
    if ([...el.children].some(c => !getComputedStyle(c).display.startsWith('inline'))) continue;
    if (!el.closest('[data-decorative]') && el.textContent.trim().split(/\s+/).length > 1) heads.add(el);
  }
  for (const h of heads) {
    const words = []; const w2 = document.createTreeWalker(h, NodeFilter.SHOW_TEXT); let t;
    while ((t = w2.nextNode())) for (const w of wordRects(t)) if (w.tops.length) words.push({ word: w.word, top: w.tops[0] });
    const lines = [...new Set(words.map(w => w.top))].sort((a, b) => a - b);
    if (lines.length > 1 && words.filter(w => w.top === lines[lines.length - 1]).length === 1)
      widows.push({ path: pathOf(h), text: h.textContent.replace(/\s+/g, ' ').trim().slice(0, 80) });
  }
  return { items, widows };
}
"""


def chrome_launch(pw):
    try:
        return pw.chromium.launch(channel="chrome")
    except Exception:
        pass
    exe = os.environ.get("EDITBAY_CHROME")
    if not exe:
        pats = ["~/.cache/puppeteer/chrome-headless-shell/*/*/chrome-headless-shell",
                "~/.cache/puppeteer/chrome-headless-shell/*/*/chrome-headless-shell.exe"]
        hits = [h for p in pats for h in glob.glob(os.path.expanduser(p))]
        exe = sorted(hits)[-1] if hits else None
    if not exe:
        sys.exit("no Chrome found: install Google Chrome, set EDITBAY_CHROME, or run a HyperFrames render once")
    return pw.chromium.launch(executable_path=exe)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project"); ap.add_argument("--brand"); ap.add_argument("--min", type=float); ap.add_argument("--json")
    a = ap.parse_args()
    index = os.path.join(a.project, "index.html") if os.path.isdir(a.project) else a.project
    doc = open(index, encoding="utf-8").read()
    W = int((re.search(r'data-width="(\d+)"', doc) or [0, 1920])[1]); H = int((re.search(r'data-height="(\d+)"', doc) or [0, 1080])[1])
    k = H / 1080 if W >= H else W / 1080
    base, src = 36.0, "default"
    if a.brand:
        brand = json.load(open(a.brand))
        if W < H:
            sc = brand.get("type_scale_px_1080p", {})
            key = "min_phone_readable_9x16" if "min_phone_readable_9x16" in sc else "min_phone_readable"
        else:
            sc = brand.get("type_scale_px_1920x1080", {})
            if "min_readable" in sc:
                key = "min_readable"
            else:
                sc = brand.get("type_scale_px_1080p", {})
                key = "min_phone_readable"
        if key in sc:
            base, src = float(sc[key]), f"brand {os.path.basename(a.brand)} {key}"
    min_px = a.min if a.min is not None else round(base * k, 1)
    if a.min is not None:
        src = "--min"
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        browser = chrome_launch(pw)
        page = browser.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
        page.route(re.compile(r".*gsap.*\.js.*"), lambda route: route.abort())
        page.goto("file://" + os.path.abspath(index), wait_until="load")
        res = page.evaluate(JS, min_px)
        browser.close()
    seen, items = set(), []
    for it in res["items"]:
        key = (it["path"], it["text"], it["size"])
        if key not in seen:
            seen.add(key); items.append(it)
    errors = [{"check": "size", **it} for it in items if not it["decorative"] and it["size"] < min_px - 0.05]
    errors += [{"check": "broken", **it} for it in items if it["broken"]]
    warnings = [{"check": "widow", **w} for w in res["widows"]]
    deco = [it for it in items if it["decorative"]]
    print(f"text_check: {W}x{H}, minimum {min_px:g} px ({src} x {k:g})")
    for e in errors:
        what = f"{e['size']:g}px" if e["check"] == "size" else "word split across lines: " + ", ".join(e["broken"])
        print(f"ERROR {e['check']:6} {what:28} {e['path']}  \"{e['text'][:60]}\"")
    for w in warnings:
        print(f"WARN  widow  one word on the last line   {w['path']}  \"{w['text'][:60]}\"")
    if deco:
        print(f"decorative (not gated): {len(deco)} items, smallest {min(d['size'] for d in deco):g} px")
    verdict = "FAIL" if errors else "PASS"
    print(f"{len(items)} text items; {len(errors)} errors, {len(warnings)} warnings  {verdict}")
    if a.json:
        json.dump({"canvas": [W, H], "min_px": min_px, "source": src, "items": items, "errors": errors, "warnings": warnings},
                  open(a.json, "w"), indent=1)
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
