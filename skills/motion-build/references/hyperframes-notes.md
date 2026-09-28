# HyperFrames notes (house rules and gotchas)

Contract (verify details in `/hyperframes-core`):
- Root: `data-composition-id`, `data-width`, `data-height`, `data-duration`, and **`data-fps="60"`** (without it,
  snapshots quantize to 30 fps).
- Every timed element: `data-start`, `data-duration`, `class="clip"`. `data-track-index` is display-only in Studio.
- One paused GSAP timeline per composition, registered as `window.__timelines["<composition-id>"]`; positions are
  absolute seconds (`tl.to(el, vars, 12.4)`).
- Deterministic only: no `Date.now()`, no `Math.random()` (use a seeded generator), no network fetches mid-render.
- `<video>` muted, audio as a separate `<audio>`; editbay uses one `<audio>` carrying the finished mix.

Gotchas that each cost a re-render:
- Animate transforms and opacity (`x`, `y`, `scale`, `rotation`, `opacity`). Letter-spacing, width, top/left snap
  to whole pixels and fail lint (`gsap_non_transform_motion`).
- A reveal that finishes early and then holds a static frame fails `sweep_static` in check: keep one element alive
  (a slow background drift is enough).
- Tag footage plates matrix-only (`-colorspace bt709`): full colour tags make Chrome colour-manage them darker.
- `hyperframes snapshot` and `check --snapshots` describe frames through Gemini whenever GEMINI_API_KEY or
  GOOGLE_API_KEY is set, and `check` has no `--describe` flag. The CLI also reads HeyGen, HyperFrames cloud,
  OpenRouter and ElevenLabs keys. Run it through `tools/hf.py`, which removes those keys (probed in 0.8.79's cli.js).
- **Rule 1 — no `backdrop-filter`:** it makes HyperFrames fall back to screenshot capture (a Codex run's 4K render
  took ~3 min with blurred cards versus ~80 s at 1080p). Use a solid or semi-opaque surface colour instead; the
  scaffold must not emit `backdrop-filter: blur(...)`.
- **Rule 2 — burned captions:** animate each `.cap-line .w` span with opacity and colour only. Put any x/y/scale
  motion on the `.cap-line` wrapper so custom GSAP motion cannot overwrite a word's caption state.
- `check` skips the layout pass while lint has errors: re-run it once lint is clean, or overlaps stay hidden.
- Run checks through `tools/hf.py check ... --check-timeout 180`. If the browser child exceeds the bound, the wrapper
  exits 124 and emits JSON with `status: "PENDING"`, `phase`, `child_command`, and the last output; preserve that
  result in `verify_report.py` instead of calling a hung check a pass or an unexplained failure.
- Before a 4K render, `hf.py` prints free disk, the one-worker and multi-worker temporary-frame estimates, and the
  worker recommendation. Let it append `--workers 1` when auto workers do not fit; an explicit count is a warning to
  fix before rendering. One-worker streaming is the safe default near the estimate.
- `hf_scaffold.py --extra-css scenes.css` inlines that file into `index.html`. The generated HTML is the runtime source:
  rerun the scaffold after editing `scenes.css`, or patch the marked inline block and record the repair.
- For a 16:9 captioned proof, pass the same verified word array to `hf_scaffold.py --captions` and assert that the
  generated HTML contains `.cap-line` cues before rendering. Captions are a separate lower band, not an afterthought.
- Count-ups are seek-safe only when each value is a discrete timed clip or a proxy value derived from the current
  timeline time. Extract a mid-hold frame after seeking and confirm it is not the initial value; a live DOM counter that
  only worked after playing from frame 0 is a failure.
- Overlapping full-frame scene sections are intentional only with `data-layout-ignore` on every overlapping section and
  a note in the beat/build record explaining the crossfade. Do not waive layout errors globally.
- Maximum render rate is 240 fps. Motion blur: render two 240 fps passes offset by half a frame (`--variables`) and
  blend 8 samples per output frame with `tmix`, then master to ProRes 4444.
- Alpha overlays: `--format mov` (ProRes 4444) or `webm`; 4:2:2 dims saturated footage at seams, use 4:4:4.
- `h264_nvenc` into `.mkv` dropped a frame once; `-frames:v`/`-t` can cut the last audio packets: end streams with
  trim/atrim inside the filter graph.
- Kill leftover `chrome-headless-shell` processes after an interrupted render (check what they belong to first).
- Fonts: Google Fonts links load before capture; for renders that must match elsewhere, vendor the fonts into the
  project (the package ships `hyperframes-localize-fonts`) or use `--docker`.
- Studio for humans: `uv run $EB/tools/hf.py preview --background` (agent-safe), `--status`, `--stop`.
- **Render audio changes level, and not by a fixed rule** (0.8.79, measured: a -14.3 LUFS mix came out at -16.1, a
  constant -1.79 dB with zero lag; one -16.0 mix stayed at -16.1, another came out at -17.4). Whatever the target,
  master the mix in sound-bed and put it back after every render with `tools/remux_audio.py` (video copied untouched).
- `--resolution landscape-4k` renders the same composition at 2x device scale: the way to make a 4K master from a
  1080p layout (fixed-pixel CSS stays correct).
- **Rule 3 — caption colors:** scaffold-generated caption tweens use explicit hex values, not `var(--muted)` or
  `var(--accent)`. Capture a mid-caption frame where a highlighted word should be visible; first/last frames are not
  enough.
- **Rule 4 — version and holds:** set `EDITBAY_HF_VERSION` for both check and render, and pass the same pin to
  `hf_scaffold.py --hf-version`. Keep intentional hook holds in the motion sidecar; a scene whose DOM starts after a
  3 s hook must not assert that it appears by 0.5 s. Sample the full transition set before delivery.
- **Rule 5 — portrait safe stack:** with a fixed caption band, positioned wrappers that have `left` and `right` use
  `width: auto`, rail nodes reflow vertically, and non-narrated notes under the caption band move or hide. Browser
  layout can pass while the encoded review fails, so inspect a portrait contact sheet after re-layout.
- **Rule 6 — orientation-aware text:** use the landscape `min_readable` threshold for a 1920x1080 composition and the
  portrait phone threshold for 1080x1920; do not apply the portrait minimum to both orientations.
- **Rule 7 — phone-safe labels:** secondary labels in a fixed progression card use short tokens such as `BASE`, `GROW`,
  `CAP`, and `NEW`; test the actual 170 px card at phone size before approving longer labels.
- **Rule 8 — blend fallback:** treat `mix-blend-mode` as an explicit render-cost choice. Replace nonessential grain
  with a non-blended texture; when blending is essential, record the screenshot fallback and budget its measured render
  time.
- **Rule 9 — local brand paths:** when CSS is copied into a local HyperFrames root, normalize `../fonts` references to
  `/brand/fonts/...` (or another path inside the root) and fail on missing local stylesheets before rendering.
- **Rule 10 — custom-scene eyebrows:** when raw HTML includes an eyebrow, declare its position for each orientation
  instead of relying on flow layout, then run the full browser check after the final scaffold.
- **Rule 11 — caption layering:** when burned captions intentionally sit over a scene card, allow overlap only on the
  caption text nodes or their caption zone; do not waive the whole scene or root.
- **Rule 12 — portrait reflow:** after late portrait CSS changes, rerun the transition layout check, not just a hero
  snapshot; sampled transitions catch caption-to-artwork and inter-scene overlaps.
- **Rule 13 — readable utility type:** run the brand text gate before delivery; design portrait utility labels and
  diagram nodes at the full 36 px minimum, using two lines or wider nodes instead of marking factual text decorative.
- **Rule 14 — persistent shell lanes:** after widening a source chip, inspect frame 0 and every persistent-bug hold;
  reserve a separate upper-right chip lane and keep the bug at its brand anchor so opaque cards cannot cover shell art.
- **Rule 15 — caption allowances:** a caption wrapper's allowance does not reliably cover the evidence beneath it. Mark
  the caption layer and each intentionally covered evidence element with explicit `data-layout-ignore` (or the narrow
  caption-overlap attribute), then keep the text and visual gates mandatory.
- **Rule 16 — cue stacks:** cues sharing a visual zone need explicit lanes, or the previous cue must fade before the next
  enters (for example, a 0.18 s crossfade). Record intentional full-frame overlap on every overlapping section and in
  the beat record; never waive the whole composition.
- **Rule 17 — warnings still need evidence:** duplicate-media, nested-cue, and caption-tween warnings are not blockers by
  themselves, but record their exact classes and require clean `hf.py check`, text gates, and encoded proof before render
  approval. Rerun the transition check after the final layout repair.
- **Rule 18 — generated caption spacing:** join caption word spans with literal whitespace and quote every generated
  attribute selector. Capture a mid-caption highlighted word to prove the gaps and selector path render correctly.
