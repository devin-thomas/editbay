# Sourcing notes

- **Capture sizes:** a card in a 1920x1080 frame that holds a web page reads best when the page was captured at
  1280 px wide; full-width captures shrink text below phone legibility.
- **Scroll "recordings":** capture the full page, then animate `y` on the image inside a masked card in HyperFrames.
  Timing then follows the beat sheet and never drops frames.
- **Logos:** vector (SVG) from the owner's brand or press page when it exists; record the page URL and the date.
  Use the owner's colours and clear space; do not animate a logo into something it is not.
- **Stock:** keep the licence text or page URL per file; some "free" licences forbid use in endorsements or
  require credit.
- **Generated stills:** keep the prompt, model, seed, and cost in the ledger. Photoreal people and places are the
  highest risk of being mistaken for real: label them.
- **Native asset fidelity:** inspect every generated or stock file at full native resolution before placing it, then
  inspect both rendered ratios. A macro image that looks generic in the edit can still expose visible brand marks such
  as `OLYMPUS` or `CH-2` and must be replaced or explicitly cleared before the ledger gate.
- **Generated clips:** Kling returns 24 fps. Re-encode for seek-safe placement:
  `ffmpeg -i raw.mp4 -an -vf "fps=60" -c:v libx264 -crf 16 -g 1 -keyint_min 1 -bf 0 -pix_fmt yuv420p clip-60.mp4`
  (speed changes, if any, before the fps filter with `setpts`).
- **Downloads:** results from aggregators expire (24 hours to 14 days in their docs): download immediately and hash.
- **Blocked captures:** retry a protected page once with the documented capture flags. After two 403/Cloudflare blocks,
  keep the URL, timestamps, response evidence, and the failed commands in `ESCALATION.md`; do not fabricate a screenshot.
  Use a source-labelled headline/type treatment or another accessible primary source, and mark the capture as blocked in
  the asset ledger.
- **Canonical capture fallback:** after two identical failures for a canonical page, preserve both error captures, mark
  the page unavailable, and switch to a directly related official documentation page. Credit that replacement as context
  on screen; do not retry the same URL again.
- **Extraction stalls:** timebox `core-extraction` (or the provider's equivalent) to two attempts. Record the stall,
  exclude partial output from the composition, and use only independently verified type or mark attribution.
- **Ad-heavy captures:** when ads or browser chrome dominate a live source page, do not present the screenshot as
  headline evidence. Typeset the exact headline and byline in a source-labelled card, disclose that the capture was
  omitted, and retain the canonical URL in the delivery package.
