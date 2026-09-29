# Example: Lil Gohan app trailer (style-music-promo + app-capture)

A 39.5 s "Coming Soon™" trailer for the Lil Gohan iPhone/iPad app, in 16:9 and 9:16, cut to the first two sections of
"Changed My Phone 📲 Remix!" (125 BPM) playing from the app itself. Built 2026-09-29 with
[style-music-promo](../../skills/style-music-promo/SKILL.md) and [app-capture](../../skills/app-capture/SKILL.md).

- Map: intro bars 1-8 (no drums), hook bars 9-16, break 17-18; lyric anchors in the hook cue the iPhone ↔ iPad swaps.
- Footage: five XCUITest performances on the iOS Simulator (iPhone 17, iPad Pro 13" landscape), synced to the song by
  the app's Now Playing clock (3-6 ms), aligned frame-exactly (`driver/` is the performer used).
- Motif: the app icon as liquid glass (Blender Cycles): clear on bars 3-4, aqua filling from bar 5 with a ring of
  release covers orbiting, a spin on bar 7, a dive into the liquid on the drop, back as the lockup (`blender/`).
- Hook: a Three.js wall of all 343 release covers pulsing on the 808s, real taps on downbeats and claps, stat slams
  from the catalog (663 songs, 27 hours), a flurry on half beats, a sphere and spectrum ring, the real pause 53 ms
  after beat 65, a quarter-note echo tail under the lockup, Uppercut Labs on bar 19.
- Build: `hf/build.py` writes both `index.html` (16:9) and `vertical.html` (9:16) from one shot list; `hf/timeline.js`
  holds one pose table for both aspects.
- Records: [EDIT.md](EDIT.md), [beats/BEATS.md](beats/BEATS.md), [RETRO.md](RETRO.md), [qa/REPORT.md](qa/REPORT.md).
- Code as run (the tools now generalise it): [hf/](hf/) (build.py, timeline.js, CSS, the Three.js stage),
  [driver/UITests/Choreo.swift](driver/UITests/Choreo.swift) (the five takes; `app-capture` holds the template),
  [blender/glass_icon.py](blender/glass_icon.py) + [portrait.py](blender/portrait.py) (`glass_logo.py` rebuilds them from a
  JSON), [build_music.py](build_music.py) (`echo_tail.py` reproduces its bed bit for bit).

Media (takes, plates, renders, the song) is not committed.
