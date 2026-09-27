# Changelog

## Unreleased

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
