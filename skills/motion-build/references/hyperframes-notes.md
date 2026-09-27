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
