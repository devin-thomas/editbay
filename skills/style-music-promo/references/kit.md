# The HyperFrames kit

Files in [../assets/kit/](../assets/kit/); the complete, working generator they came from (both aspects) is in the
editbay example `examples/demo-artist-trailer/hf/` (build.py, timeline.js, style.css, vertical.css). The smallest
complete build from the kit alone was the DemoIdent channel ident (2026-09-29): a ~110-line build.py filled
`template.html` for 16:9 and 9:16 and passed `hf.py check` and `verify_report` (reel and shorts) with no GPU work.

| file | what it does | reads |
|---|---|---|
| `template.html` | the page: pinned GSAP, local @font-face, root composition attributes, the mix `<audio>`, script order, the inline timeline registry; the build replaces its `{{TOKENS}}` | the build's CSS, body, timeline |
| `devices.css` | CSS-3D iPhone (portrait) and iPad (landscape) frames with metal rims, 8-layer edge thickness, glare, touch dots | — |
| `mark.css` | the flat mark (no-GPU motif): the mark in a disc, grey/colour layers, white and accent rings, burst, accent bloom | — |
| `wave.js` | `makeWave(canvas, AUD, opts)` → `draw(T)`: SoundCloud-style waveform scrolling with the song; starts at `AUD.wave.start` | `AUD.wave` |
| `ring.js` | `makeRing(canvas, AUD, opts)` → `draw(T, on)`: 2D spectrum ring (size, colour, bar count, gain, spin) | `AUD.fps`, `AUD.bands`, `AUD.features.mix` |
| `promo.js` | `makePromo(tl, {vertical, fps})`: pose `pick(h, v)`, touch overlays, beat pulses, a per-frame driver, frame-0 state, `bloom`, `flatMark` | the shot data |
| `stage.js` | Three.js stage: every cover as a wall that scrolls with the product's flings and pulses on 808s, morphing into an orbiting sphere, a 72-bar spectrum ring for the flurry, implode at the stop; bloom; drawn at 2× | `window.STAGE`, `window.AUD` |

`window.AUD` is the map JSON's `fps`, `features`, `bands` and `wave`, copied as written (no slicing: `wave.start`
places it). `stage.js` is trailer-shaped: it throws unless `window.STAGE` has every phase time: `{start, end, W, H,
fov (36 for 16:9, 56 for 9:16), events: {bass, clap}, flings: [[t, velocity]...], flingTau, phase: {enter, wallTurn,
morphStart, morphEnd, swap1, flurry, swap2, ringIn, ringOut, implodeStart, implodeEnd}, art: [file names]}`, optional
`artDir` ("assets/art256/"), `canvas` ("stage"), `cols` (28), `rows` (26). `events.bass` is track_map's
`events.grid.bass` (the trailer's build called it `b808`; both are read). For a spectrum ring without the wall, use
`ring.js`.

## Build pattern

A Python build script writes the composition from a shot list, so timing lives in one place and both aspects come from
one source: segments (`seg(device, take, T0, T1, sync | anchor)`), touches from the performance events, the stage
config, and one project per aspect: `hf/index.html` (16:9) and `hf-vertical/index.html` (9:16, with `assets` and `js`
symlinked to `hf/`). Never leave both in one folder: two root compositions fail `hf.py check` with
`multiple_root_compositions` (the runtime may play both audio tracks), and `snapshot`/`check` only read `index.html`.
The timeline is one paused GSAP timeline; poses are `pick({…16:9…}, {…9:16…})`.
From the template: copy the kit files you use into the project's `kit/`, write `js/data.js` (`window.AUD`,
`window.SHOT`), and replace the tokens (TITLE, W, H, DUR, FPS, VERTICAL, FONT_FAMILY, FONT_FILE, CSS, BODY, TIMELINE).
Times come from the maps, never typed: bars from `ident.json` `bars`, hits from `events.grid`, the stop and the type
cues from `echo.json` (`stop.edit`; `hits` only when the artist asked for an echo).

## Gotchas (each cost a render)

- A zero-duration `tl.set` at time 0 is not applied to the very first rendered frame: set the opening state on load too
  (`openState`), or frame 0 renders the CSS default (black).
- A `fromTo` renders its from-values when it is created (GSAP `immediateRender`), so a pulse layer sits at its
  from-state until the first hit: pass `immediateRender: false` (the kit's helpers do). The trailer's phone sits 1.6 %
  large through its intro for this reason (its pulses are created without it); on the DemoIdent ident the mark's ring
  measured 522 px instead of 513 and 4.5 px low from frame 0 to the first 808 at T 1.964.
- The timeline must be inline in `index.html`: moved to an external `timeline.js`, `hf.py check` fails with
  `missing_timeline_registry` (exit 1) even though `window.__timelines` is set there.
- Two `<img>` of the same file (a grey copy under the colour one) warn `duplicate_media_discovery_risk`; put the
  second copy on a div as a CSS `background-image` (as `mark.css` does).
- A font file over 2 MB is not inlined into the bundle (SFNS.ttf 7.5 MB); local renders still find it. Subset it
  only when the bundle must be self-contained.
- Never time a wrapper and its `<video>` both; device wrappers are untimed, videos are the clips.
- Clips on the same `data-track-index` do not stack: once the later clip starts, the earlier one stops showing. The
  trailer's Three.js stage canvas (transparent until the wall entered on the drop) started 0.06 s early on the glass
  plate's track and blanked the plate for 3 frames right before the drop (av-qa: black 16.82-16.87 s; padding the
  plate changed nothing). Start the next clip on a shared track exactly where the previous should vanish, or give it
  its own track.
- Canvases at 2× their CSS size (`width=3840` for a 1920 layout) keep covers and the waveform sharp, and survive a 4K
  render; the browser renders WebGL on the GPU here (capture ~1 min for 39.5 s at 60 fps).
- CSS 3D contexts force screenshot capture (fine: 2-3 min per full render on an M5 Max).
- `filter: blur()` on a preserve-3d wrapper flattens it: set `filter: "none"` after a blur tween so the edges come back.
- The layout check flags a per-frame-updated counter as overlapping its label; mark the children
  `data-layout-allow-overlap` after checking a snapshot.
- `text_check.py` counts a ™ at 0.5 em as text: keep it ≥ the minimum (0.6 em at 46 px).
- The scene transition into a 3D plate: push the product's own icon to the plate's first-frame size and position,
  blur the last 0.2 s, and cut under a 0.4 s flash.

## Glass plates (`glass_logo.py`)

No GPU (or Blender busy): the flat mark, `mark.css` + `K.flatMark("#mark", {reveal: [bar 8, bar 9], hit, echoes:
hits, bloom: "#bloom"})`, then `K.pulses(bass, claps, "#mark .fm-pulse")`. To crop into an avatar, move the `img` box
and give `.fm-grey` the same crop (the DemoIdent ident: img left −30 %, top −28 %, 160 %; background-size 160 %,
position 50 % 46.67 %).

- Render three test frames (clear, mid-fill with orbit, lockup) at 20 % size before any full render; look for light
  blobs, framing, and where the lockup type goes.
- Keep studio HDRIs out of glossy and transmission rays; their round panels mirror in flat glass as blown-out discs
  over the logo, and rotating the HDRI only moves them. Strip lights draw the edges.
- A white light bar reflected in the thin-film glass reads lavender (the trailer's shine sweeps: a pale violet
  streak across the face, frames 551-919 and the lockup; 575 frames re-rendered). `glass_logo.py` splits the sweep:
  white lights the logo through the glass, a (0.45, 0.9, 1.0) copy shows only in reflections, reading cool white.
- Key light on/off as CONSTANT steps: keys 0.01 s apart round onto one frame and leave long BEZIER ramps (the
  sweep faded up over 3 s between sweeps and sat at full power through the lockup's first 83 frames).
- 16 spp + OpenImageDenoise is indistinguishable from 32-72 spp (mean difference 0.7/255) at half the time; running two
  renders at once did not raise throughput.
- Renders are resumable (`use_overwrite=False` + placeholders); an empty placeholder left by a killed render must be
  deleted before resuming. Pre-create empty files for frames you do not need.
- Key any after-stop glow to the real stop time from the product take, not to a planned one.

## Vertical (9:16)

Devices ~10 % larger than a straight scale and lower (y +200 to +290 px), type in a top band from ~235 px (platform
headers sit above it), lockup type under the icon at ~1190 px, the waveform along the bottom in the cold open,
the stage camera at FOV 56. The 3D plates re-rendered at 1080×1920: with sensor fit AUTO the icon keeps its size against
the short side; stand the cover ring upright and back the camera off while it is up.
