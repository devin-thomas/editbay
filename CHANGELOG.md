# Changelog

## Unreleased

- Music promo kit, from the Lil Gohan app trailer (2026-09-29, 125 BPM, 39.5 s, 16:9 + 9:16):
  - New skill `style-music-promo`: trailers, sizzle reels, intros, outros, interstitials and idents cut to a supplied
    song. Map the track first, give sections roles (motif, drop, flurry, resolve), drive pulses from the song's own
    analysis, a liquid-glass motif, stop on an event with a tempo-synced echo, two aspects decided up front. Includes
    the HyperFrames kit (device frames, SoundCloud-style waveform, a Three.js cover wall/sphere/spectrum ring,
    timeline helpers) and a new route in video-director.
  - New skill `app-capture`: real iOS app footage as XCUITest performances on song time (XCTest's idle waits skipped:
    gestures went from 1-2 s late to ~0.05 s), aligned frame-exactly and synced by the app's own clock (3-6 ms).
  - New tools: `track_map.py` (tempo/phase fit, bars, sections from stems, 16th-note groove, lyric anchors, per-frame
    features for HyperFrames), `echo_tail.py` (stop on an event with an echo throw, or fade over N bars),
    `sim_take.py` (sync, align, changes, events for simulator recordings: a naive trim or decode shifted content 0.8-2.7 s early),
    `glass_logo.py` (Blender liquid-glass logo plates, 16:9 and 9:16), `logo_matte.py` (alpha from several flat
    backgrounds).
  - Found by the tools on the run's own files: the song's MP3 decodes 0.81 dB over full scale, so the first music bed
    hard-clipped 922 samples in the hook (rebuilt with 1.5 dB of headroom; `echo_tail.py --gain` and a clip warning);
    low-band energy picks the wrong downbeat when the 808 alternates beats 1 and 2 (track_map votes on stem entries
    first).
  - Owner's ruling on the trailer's sound (2026-09-29): nothing may sound before the song's first note (a -24 dB swell
    and a tap click there were heard as a wrong first note), and nothing may be added to the artist's song (the echo
    throw was "an echo I didn't personally add"). style-music-promo rules 2 and 7 now require a silent pre-roll and a
    plain fade into the ending event; tonal sound design stays fine once the music has visibly stopped.
    `echo_tail.py --fade-from F --stop S`: a plain linear fade to zero on the stop, nothing after (reproduces the
    trailer's new bed sample for sample; negative controls: F past the stop, F with --fade-bars, and echo mode without
    a tempo each exit 1; echo mode unchanged, 0 of 1,896,000 frames differ).
  - From the trailer's final QA: `glass_logo.py` splits the shine sweep (the white bar reflected lavender in the thin
    film, off-brand for an aqua mark; the reflection copy is tinted (0.45, 0.9, 1.0)) and keys sweeps as CONSTANT
    steps (0.01 s-apart keys merged on one frame and left 3 s BEZIER ramps); `verify_report --allow-silence` (an
    end card decaying to silence, like `--allow-freeze`; negative control: a waiver from 38.2 s still fails the
    37.08 s silence); kit.md: one project folder per aspect (`multiple_root_compositions`), and clips on one track do not
    stack (the stage canvas starting 0.06 s early on the plate's track blanked it for 3 frames before the drop); master
    to -1.5 dBTP for AAC delivery (a -1.0 master went over in the encode and remux_audio's limiter cost 0.4 LU and
    2 dB of peak; -1.5 came through at -1.4).
  - Cold-read test (a fresh agent made a 7.3 s channel ident on "Villains", 140 BPM, from the skill alone) and fixes:
    - track_map picked beat 3 on Villains 0:60 with no note: its one-bar change windows voted the groove's bass gap
      (phase 2 316 dB vs phase 0 237, no 2/3 majority, so low-band energy decided). Changes are now 2 bars against 2
      bars, the first bass/drums entrance votes its rise, low-band energy and the first vocal entrance only report,
      and any disagreement prints per-phase votes, every cue and a MAP.md check. Villains 0:60 now beat 0 (86 %,
      flagged: the bass returns on beat 3 of bar 33); "Changed My Phone" 0:45, 10:45, 0:30, 30:90 and whole song
      unchanged and unanimous (0:45: same 124.997 BPM, grid, features, bands, events and sections).
    - `--grid-from map.json`: a short window keeps the song's grid, bar numbers, loudness references and stems (the
      ident window alone refit 140.018 to 139.655 BPM and moved its first beat). A window's partial last bar is mapped
      and flagged, so bar 9 keeps its hits (bass 1.964, 2.392, 2.821) and reads `X...X...Xxxxxxxx` as in the 0:60
      map, not 12 X against itself. Missing, broken or non-map files exit 1 with the reason.
    - echo_tail: `--json` `hits` (each repeat's audible transient: within 3.9 ms of onsets measured on the Villains
      bed, 8 of 8; the trailer had keyed type 0.31 s after them); an 8 ms fade-in when the bed starts mid-song (it
      stepped 0 → 0.051 in one sample); `--gain` applied at load, so `--gain -1.5` now equals the trailer's
      rebuilt music.wav sample for sample (it was ±1 LSB in 10,843 samples).
    - Kit: `template.html` (pinned GSAP, local fonts, root attributes, mix audio, inline timeline registry; an
      external timeline.js fails `missing_timeline_registry`), `mark.css` + `K.flatMark` (the no-GPU motif) and
      `K.bloom` (the hit as an accent bloom ≤ 0.35 on the mark: the draft's 0.5 white overlay took the dark corners
      from luma 3 to 123), `ring.js` (standalone spectrum ring), `wave.js` starting at `AUD.wave.start` (no manual
      slicing), `immediateRender: false` on every helper fromTo (without it the pulse layer sat 1.75 % large and
      4.5 px low until the first 808), `stage.js` reading `events.bass` and checking its phases.
    - Docs: one downbeat check with numbers, the map-once-then-`--grid-from` pattern, ident = 2 bars + a 2-4 s echo
      tail with one bar recipe, wordmark 1.0-1.2x the brand headline, vocal-free bars for idents, SFX `gain_db`
      relative to sfx_synth's -3 dBFS peak, the beat-align gate's real tolerance (one frame, 16.7 ms at 60 fps).
      Proof: the ident rebuilt from the kit passes `verify_report` reel (16:9) and shorts (9:16).

- tts_worker_runner: queues on the GPU lock (polls every 5 s, up to 45 min, job `lock_wait_s` overrides) instead of
  exiting on the first "GPU busy"; removes a lock only while it names this process. In CacheBrief wave 1 a producer hit
  the lock twice, exited, and shipped a macOS `say` fallback. Test: a waiter acquired 7.1 s after the holder released;
  with a 2 s wait it exited 1 (negative control).

From CacheBrief's three pilot shorts, AUDIT, and HEAD review (STEWARD pass 2, 2026-09-27):
- voiceover and asr_remote: remote work dirs are namespaced `story--producer` (from --story-slug/--producer-callsign,
  EDITBAY_* env, or the run folder), so concurrent producers on the GPU host never share a directory; `--dry-run`
  prints the namespace. Two concurrent dry runs produced distinct paths.
- hf.py: bounded `check` (180 s default; a hung browser child becomes PENDING, not a hang); disk-aware 4K workers.
- verify_report: exact encoded last frame must be the end card (two pilots lost it in the final 2-3 frames).
- asset_ledger: full sha256, source-segment reuse/overlap gate; gates.md adds opening-frame, logo-fidelity, and
  duration-ledger evidence.
- beats_check `--open-loops` (idea from nateherkai/hyperframes-student-kit, MIT): every open loop pays off > 2 s later.
- hf_scaffold: brand looks and shell by `--look`, local fonts only, inline CSS marked with its source, landscape
  caption proof.
- sourcing notes: after two blocked captures, fall back honestly; motion notes: per-section crossfade waivers,
  seek-safe count-ups.

- New skill `style-edit-talks-back`: a talking-head edit where the edit is a second character (monospace asides,
  running counters, punch words, parody lower thirds, a parody-world cold open), learned with reference-to-style from
  eight measured videos by corbin (203-235 wpm, 30-60 visual events a minute, LRA 2.3 LU). The references were studied
  at 720p and deleted; only the text breakdown is kept. Proof piece: the Daily Combo Trials dev vlog.
- Titan jobs run at full speed: Windows puts processes started over ssh in its efficiency mode (x264 at Normal priority
  12 fps, at AboveNormal 53 fps; the same job 288 s vs 60 s). `transcribe_faster_whisper.py` raises its own priority
  at start; `tts_worker_runner.py` raises the worker's whole tree, because a venv's python.exe is a launcher whose real
  interpreter does not inherit AboveNormal. Both verified on Titan (0x20 -> 0x8000).
- remux_audio: when AAC overshoots the true-peak ceiling, limit the transients instead of trimming the whole mix. The
  trim loop collapsed the dev vlog's copies to -17.3 LUFS: Sum Slight's near-square drum hits encode at 160k to
  -0.9 dBTP untrimmed and +1.5 dBTP after a 0.2 dB trim. A limit 3 dB under the ceiling gives -1.1 dBTP at -15.0 LUFS.

From the Muse run's retro, folded in by CacheBrief's STEWARD desk (2026-09-27):
- av_qa `--require-content-ends` (on by default in verify_report): fails a delivery whose first or last frame is only
  background. The Muse 9:16 and 16:9 deliveries both open empty (edge density 0.0) and now fail; a real hook frame
  (0.074) passes.
- hf_scaffold: burned captions animate opacity and colour on word spans only (transforms on the `.cap-line` wrapper),
  so they coexist with custom GSAP motion; portrait layouts use a 160-1500 px safe stack on a 1920 px canvas.
- motion-build notes: no `backdrop-filter` (screenshot-capture fallback); vertical re-layout is a new layout, not the
  16:9 cards stacked at the top.
- verify_report and gates.md: `--allow-freeze` takes several comma-separated `start:end` ranges, with an example.
- PROVIDERS: Antigravity CLI (`agy`, gemini-3.8-flash-high) for generic stock images (about 30 s per image, 768x1376),
  and X API v2 posting (pay-per-use).

From the first real talking-head edit (an 8.5-minute single-take promo recording):
- cut_plan `--selects`: assemble parts of a long take in any order, with gaps for inserts. Select edges snap to the
  silence around the words, never into them: nearest-silence snapping had dropped a soft first word and clipped a
  final consonant. Edges without a pause are reported as hard cuts, at the quietest point.
- hf_scaffold: `--base` puts the footage video at the top level. Nested in a timed wrapper, HyperFrames 0.8.79 lint
  fails with video_nested_in_timed_element (its frame extractor cannot reach it); first hit building over real footage.
- cut_render: reordered EDLs render as forward runs joined by stream copy (frame-exact: each piece's first frame
  matches its source frame at 43-47 dB PSNR, neighbours at 32-34 dB); gaps render as black and silence and appear as
  markers in the FCPXML. In-order EDLs render as before (fixture regression identical).
- remux_audio: the true-peak trim repeats (up to 3 passes). At 128k AAC a single 0.3 dB trim still left -0.9 dBTP
  on the promo's share copy; repeating the trim brought it to -1.0 dBTP.

## 0.3.0 (2026-09-27)

From a Codex CLI run (gpt-5.6-luna, max effort) that made a 90 s explainer with these skills unaided, and a review of it.
- New tools: `hf.py` runs the pinned HyperFrames CLI with paid-service keys removed (with a Gemini key set, `snapshot`
  and even `check --snapshots` send frames to a vision API; `check` has no `--describe` flag); `text_check.py` fails
  text under the brand's phone minimum and words split across lines (Codex's video had 95 such errors that its own
  visual check passed); `asr_remote.py` does the GPU-host transcription round trip in one command.
- verify_report: a `text` gate (`--brand`), HyperFrames through hf.py, comma-separated `--allow-freeze` ranges documented.
- hf_scaffold: no `backdrop-filter` on cards (it forces slow screenshot capture); highlights without CSS transforms or
  negative z-index (31 lint conflicts gone); decorative text marked; labels at the phone minimum; balanced headings;
  a vertical safe area (bottom 26%, right 12%) with captions above the platform UI; a warning when two cues share a
  zone at once. Regression fixture: examples/scaffold-smoke.
- Skills call HyperFrames through hf.py; transcript-reconcile uses asr_remote.py; motion-build and render-verify gate text.
- Corrected: HyperFrames does not normalise render audio to -16 LUFS; the level change varies (-1.8 dB, -1.4 dB, or
  none measured). Remux the mastered mix after every render, whatever the target.

## 0.2.0 (2026-09-26)

- Skills: video-director (entry point: brief, route, goal condition, loop), broll-sourcing, delivery-pack,
  reference-to-style, style-craft-reel, skill-retro. 14 skills in the plugin.
- Tools: asset_ledger (provenance and a gate), deliver, reference_report, remux_audio (puts the mastered mix back after a
  render; the 0.2.0 note that HyperFrames normalises to -16 LUFS was wrong, see 0.3.0). contact_sheet captions moved under the tiles.
- Examples: explainer delivered (4K master, 1080p, 9:16, captions, thumbnails); the Kenn Ejima reel measured and
  broken down; an original craft reel built from that style.

## 0.1.0 (2026-09-26)

First cut, built from an analysis of Nate Herk's "Opus 5.5 Just Changed Video Editing Forever" (2026-09-25), the
posts behind it (Kenn Ejima, kirill sh), HyperFrames 0.8.79 and its agent skills, and Devin's own video pipelines on
Titan (GateKeyPers, wobble, commentary reel, explainers pipeline).

- Skills: footage-intake, transcript-reconcile, rough-cut, voiceover, beat-sheet, sound-bed, motion-build,
  render-verify.
- Tools: media_probe, contact_sheet, scene_cuts, beat_grid, loudness, av_qa, faces, face_clear, palette,
  transcribe_faster_whisper, reconcile, transcript_diff, cut_plan, cut_render, voiceover, voiceover_check,
  tts_worker_runner, beats_check, sfx_synth, beat_bed, mix, hf_scaffold, verify_report.
- Examples: rough-cut fixture (synthetic, with deliberate flaws), five-step explainer (devin-v1 narration).
