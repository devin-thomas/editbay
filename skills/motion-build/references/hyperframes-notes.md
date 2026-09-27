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
- `hyperframes snapshot` and `check --snapshots` with a Gemini key in the environment describe frames through the
  API unless you pass `--describe false`.
- Maximum render rate is 240 fps. Motion blur: render two 240 fps passes offset by half a frame (`--variables`) and
  blend 8 samples per output frame with `tmix`, then master to ProRes 4444.
- Alpha overlays: `--format mov` (ProRes 4444) or `webm`; 4:2:2 dims saturated footage at seams, use 4:4:4.
- `h264_nvenc` into `.mkv` dropped a frame once; `-frames:v`/`-t` can cut the last audio packets: end streams with
  trim/atrim inside the filter graph.
- Kill leftover `chrome-headless-shell` processes after an interrupted render (check what they belong to first).
- Fonts: Google Fonts links load before capture; for renders that must match elsewhere, vendor the fonts into the
  project (the package ships `hyperframes-localize-fonts`) or use `--docker`.
- Studio for humans: `npx hyperframes preview --background` (agent-safe), `--status`, `--stop`.
- **Render audio is normalised to about -16 LUFS** with one static gain (0.8.79, measured: a -14.3 LUFS mix came
  out at -16.1 with a constant -1.79 dB and zero lag; a -16.0 mix stayed at -16.1). For any other loudness target,
  master the mix in sound-bed and put it back after every render with `tools/remux_audio.py` (video copied untouched).
- `--resolution landscape-4k` renders the same composition at 2x device scale: the way to make a 4K master from a
  1080p layout (fixed-pixel CSS stays correct).
