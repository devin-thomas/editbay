# Audio-reactive visuals from the track map

Nothing listens live. `track_map.py` writes one JSON per song window in edit time (T = song time + offset), and every
visual reads it by frame index `f = round(T × fps)`, so a frame renders the same way every time. Map the song once
from 0, then the edit window with `--grid-from` that map: the window keeps the song's grid and bar numbers, and its
envelopes, bands and groove are scaled against the same references (`refs`), so a one-bar window reads like the song.

## The map JSON (what the kit reads)

| key | content | typical use |
|---|---|---|
| `fps`, `offset` (`preroll`), `period`, `beat0`, `beats`, `bars` | the grid in edit time | cue placement, flurry timing |
| `features.mix / bass / drums / vox / mel` | per-frame envelopes 0-1.2 (fast attack, slower release) | glows, bloom, scale breathing |
| `bands` | per-frame 32 log bands (40 Hz-16 kHz) as 0-99 | spectrum ring or bars |
| `events.bass / kick / clap / hat / mel / words` | onset times per stem; lyric word start/end | pulses, slams, transformation anchors |
| `events.grid.bass / kick / clap / hat` | the same hits snapped to the 16th grid | pulses on a regular groove |
| `barMap`, `sections` | per-bar RMS and stems present; runs of bars (intro, hook, break); a window's incomplete last bar is included with `partial: true` (steps past the end read `-`) | the bar map, section roles |
| `wave.start, wave.dur, wave.peaks` | min/max peaks over the window; `wave.start` = the edit time where peaks[0] plays (window start + offset: equal to `offset` only when the window starts at song 0) | the waveform line (`makeWave` reads it; pass the map's `wave` unsliced) |
| `refs` | the loudness references (presence, groove, envelopes, bands) and where they came from | `--grid-from` reuse |

On a regular groove, prefer `events.grid.*` (hits snapped to the 16th grid) over raw onsets: the grid times are exact
and a missed onset leaves no hole. The example's claps (beat 3 of every hook bar) were first placed by hand from the
groove string; the tool now finds all eight and lands within 2.4 ms of the hand-placed ones.

## Recipes (values measured to read well at 1080p60)

- **Downbeat/808 pulse** on the device layer: `fromTo(scale 1.016 → 1, 0.26 s, power2.out)` at each 808.
- **Clap kick**: `fromTo(y 5 px → 0, 0.2 s)` on the device layer; camera FOV −1.2° with a 0.12 s decay in 3D.
- **Cover-wall wave** (Three.js): brightness = 0.21 + 0.5·Σ exp(−(t − t808 − d·0.025)/0.14) + 0.18·clap + 0.1·mel,
  where d is a cover's distance from the wall centre in grid units: a ring of light spreads outward on each 808.
- **Scroll parallax**: the wall scrolls with the product's fling impulses (velocity a·exp(−Δt/0.55), integrated in
  closed form), so the 3D stage moves with the list on the phone.
- **Spectrum ring**: 72 bars mirrored over 32 bands; height = 0.12 + 2.6·(band/99)^2.2·(0.6 + 0.8·mix); bloom 0.55 +
  0.5·kick + 0.25·clap. Use it for the flurry (densest frame), not throughout. Without Three.js: kit `ring.js` (2D
  canvas, same formula in units of radius/4.6; the DemoIdent ident ran it at gain 0.42 around the mark for the hit bar).
- **The logo hit's light**: an accent radial bloom centred on the mark, 2.2x its diameter, `mix-blend-mode: screen`,
  opacity 0.3 held 2 frames then to 0 in 0.25 s (`K.bloom`). On the DemoIdent ident it lifts the mark's luma 73 → 105
  and leaves the corners at 3; the draft's full-frame white overlay at 0.5 took the corners to 123.
- **Waveform (SoundCloud bars)**: 4 px bars, 2 px gaps, 8 s across the frame (240 px/s at 1920), playhead at centre;
  played part in the accent with a vertical gradient, unplayed #39404a, 28 % reflection below, edges faded over 260 px.
  Before the song starts the upcoming waveform waits to the right, still.
- **Glow**: backdrop glow opacity 0.3 + 0.8·mel in the quiet intro; 0.25 + 0.6·bass in the hook.
- **After-stop pulses**: glow peaks at the stop, then keeps the grid's rhythm through the silence, falling about
  0.62x per pulse back to rest (with an artist-approved echo, key them to `echo_tail --json` `hits`).
- **3D plates in Blender**: key the backdrop emission every 2 frames from `mel` and `vox`; sweep lights on bar
  downbeats and on a vocal accent ("Yeah").

## Counting up

A stat counts from 0 to its value over 0.55 s from the clap with an ease-out (1 − (1 − p)^2.4), computed per frame
from T (seek-safe), not with a tween's onUpdate state.
