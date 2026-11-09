# Routes

| Request | Chain | Machines |
|---|---|---|
| Edit my talking-head video (graphics, B-roll, polish) | footage-intake, transcript-reconcile, rough-cut, beat-sheet (faces), broll-sourcing, sound-bed, motion-build, render-verify (face-clear), delivery-pack | GPU host: ASR; local: tools, renders |
| Cut my mistakes and pauses only | footage-intake, transcript-reconcile, rough-cut (FCPXML for the editor) | GPU host: ASR |
| Narrated explainer from a script or topic | voiceover, transcript-reconcile (script as third source), beat-sheet, broll-sourcing, sound-bed, motion-build, render-verify, delivery-pack | GPU host: cloned voice, ASR; local: renders |
| Music promo on a supplied song: trailer, sizzle reel, intro/outro, interstitial, ident (16:9 and 9:16) | style-music-promo (map the track first: `track_map.py`), app-capture (real product UI, synced by its own clock), sound-bed (`echo_tail.py` for the stop), beat-sheet (bars, lyric anchors), broll-sourcing (catalog art; glass-logo plates via `glass_logo.py`), motion-build, render-verify (beat-align + clock sync gate), delivery-pack (both aspects) | local (Blender plates are the long pole: decide aspects before rendering them) |
| Showreel, sting, or music-led piece | reference-to-style (if a reference is given) or a style skill, sound-bed (bed first: the grid drives the cuts), beat-sheet (beat cues), motion-build, render-verify (beat-align), delivery-pack | local |
| Reel from a big folder (event, streams) | footage-intake (big folders), transcript-reconcile (turbo), candidate selection, rough-cut per select, beat-sheet, sound-bed, motion-build, render-verify, delivery-pack | GPU host: extraction and ASR where the files live |
| Captions only on existing footage | transcript-reconcile, then HyperFrames `/embedded-captions` or delivery-pack captions | GPU host: ASR |
| "Make something like this video" | reference-to-style, then the showreel route with the new style | local |

After any route: skill-retro. HyperFrames' own workflows (`/talking-head-recut`, `/music-to-video`, `/faceless-explainer`,
`/product-launch-video`) are fine alternatives when the request fits one exactly and no editbay step (reconciled words,
rough cut, cloned voice, brand gate, file-level verification) is needed.
