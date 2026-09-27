# editbay

Agent skills for editing and making videos with a coding agent (Claude Code or Codex), built on
[HyperFrames](https://github.com/heygen-com/hyperframes). One method, measured from real runs: **transcribe, cut, plan
the beats, build, verify**, with two loops that make it better with use: **reference to style** and **feedback into
the skill**. Design: [docs/DESIGN.md](docs/DESIGN.md). Paid services vs free/local routes: [docs/PROVIDERS.md](docs/PROVIDERS.md).
The research behind it: [docs/research/ANALYSIS.md](docs/research/ANALYSIS.md).

## Install

Claude Code (plugin):

```bash
claude plugin marketplace add devin-thomas/editbay
claude plugin install editbay@editbay
```

Codex: put the editbay tree (at least `skills/` and `tools/`, side by side) in a skills folder Codex scans, such as
`<project>/.agents/skills/editbay/`. Codex finds the nested skills and lists them as `editbay:<skill>`, and `$EB` in
every skill is that `editbay/` folder. Tested with Codex CLI 0.145 (2026-09-26); `~/.codex/skills/editbay/` should work
the same way for all projects but is untested. Don't copy skill folders on their own: they lose their tools.

```bash
mkdir -p .agents/skills/editbay && git -C ~/dev/editbay archive HEAD | tar -x -C .agents/skills/editbay
```

Prerequisites: `uv`, `ffmpeg`/`ffprobe`, Node 22+ (HyperFrames runs through `npx hyperframes@0.8.79`), and
`~/.config/editbay/config.json` (copy [config/config.example.json](config/config.example.json)) naming your GPU host,
voices, credentials file, and delivery profiles. Install HyperFrames' own skills with `npx hyperframes skills update`.

## Skills

Start with `video-director`: it writes the brief, picks the route, and runs the other skills in order.

| When you want to | Skill | You get |
|---|---|---|
| edit or make a video from a file, URL, or idea | `video-director` | an edit brief, a route, a goal condition backed by printed evidence, the loop run to delivery |
| bring in files, URLs, or a folder of footage and look at it | `footage-intake` | inventory, contact sheets, audio, proxies, face zones |
| a transcript you can trust | `transcript-reconcile` | two-model transcript voted against captions or the script, glossary fixes, a corrections log |
| cut dead air, fillers, retakes | `rough-cut` | frame-exact cut, silent joins, retimed words, FCPXML for Resolve |
| narration from a script (your cloned voice or a stock one) | `voiceover` | sentence-checked narration and word timings |
| decide what appears when and where | `beat-sheet` | anchored cues, zone and read-time checks, motion assertions |
| screenshots, recordings, logos, stock, or generated images | `broll-sourcing` | sourced assets with a provenance ledger and a gate for unlicensed or unlabelled media |
| music, sound effects, a mix at spec | `sound-bed` | bed with an exact beat grid, SFX, ducked mix at -16/-14 LUFS |
| motion graphics and overlays in HyperFrames | `motion-build` | a check-clean composition and renders |
| proof the render is right | `render-verify` | gates on the DOM and the encoded file, one visual read, a QA report |
| hand it off | `delivery-pack` | 4K master, review copy, vertical cut, captions, chapters, thumbnails, manifest |
| a house style learned from a video you admire | `reference-to-style` | measurements, a breakdown, and a new style skill that keeps the principles and leaves the signature |
| a short motion reel in the craft-reel style | `style-craft-reel` | the style's rules, motif, and acceptance table (built by reference-to-style) |
| the next run to go better | `skill-retro` | RETRO.md: what the creator corrected, which skill or tool changes, and who owns each change |

## Tools

`tools/` holds the measurements and generators the skills call; each runs with `uv run tools/<name>.py --help`.
Probe and look: `media_probe`, `contact_sheet`, `scene_cuts`, `palette`, `faces`, `reference_report`. Words:
`transcribe_faster_whisper` and `asr_remote` (GPU host), `reconcile`, `transcript_diff`. Cutting: `cut_plan`, `cut_render`. Voice:
`voiceover`, `voiceover_check`, `tts_worker_runner` (GPU host). Planning: `beats_check`. Sourcing: `asset_ledger`.
Sound: `beat_grid`, `beat_bed`, `sfx_synth`, `mix`, `loudness`, `remux_audio`. Build, verify, deliver: `hf` (the
HyperFrames CLI with paid-service keys removed), `hf_scaffold`, `text_check`, `av_qa`, `face_clear`, `verify_report`,
`deliver`.

## Examples

- [examples/rough-cut-fixture](examples/rough-cut-fixture): synthetic narration with a deliberate retake, filler, and
  dead air; shows transcript voting, silence-snapped cuts, join checks, and positive/negative controls.
- [examples/explainer-five-steps](examples/explainer-five-steps): a 60 s explainer narrated in devin-v1, planned on a
  beat sheet, built in HyperFrames, verified (loudness, words, motion, layout, contrast), and delivered in 4K, 1080p,
  and 9:16 with captions.
- [examples/style-from-kenn-reel](examples/style-from-kenn-reel): a 15 s one-prompt motion reel measured and broken
  down (tempo, cut grid, palette, pacing) into principles; the reference's own frames stay out of git.
- [examples/showreel-craft](examples/showreel-craft): an original 128 BPM reel built with the style from that
  breakdown, checked against the style's acceptance table and mastered to -14 LUFS.

Media is not committed; each example's records (briefs, beat sheets, reports) are.

## Validate

```bash
python3 scripts/validate.py
```
