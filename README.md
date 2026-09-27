# editbay

Agent skills for editing and making videos with a coding agent (Claude Code or Codex), built on
[HyperFrames](https://github.com/heygen-com/hyperframes). One method, measured from real runs: **transcribe, cut, plan
the beats, build, verify**, with two loops that make it better with use: **reference to style** and **feedback into
the skill**. Design: [docs/DESIGN.md](docs/DESIGN.md). Paid services vs free/local routes: [docs/PROVIDERS.md](docs/PROVIDERS.md).

## Install

Claude Code (plugin):

```bash
claude plugin marketplace add devin-thomas/editbay
claude plugin install editbay@editbay
```

Codex: copy the skill folders you want into `~/.codex/skills/` together with `tools/` (skills reach tools two folders
up), or use the synced copy in devin-thomas/private-skills (`Research/editbay/`).

Prerequisites: `uv`, `ffmpeg`/`ffprobe`, Node 22+ (HyperFrames runs through `npx hyperframes@0.8.79`), and
`~/.config/editbay/config.json` (copy [config/config.example.json](config/config.example.json)) naming your GPU host,
voices, credentials file, and delivery profiles. Install HyperFrames' own skills with `npx hyperframes skills update`.

## Skills

| When you want to | Skill | You get |
|---|---|---|
| bring in files, URLs, or a folder of footage and look at it | `footage-intake` | inventory, contact sheets, audio, proxies, face zones |
| a transcript you can trust | `transcript-reconcile` | two-model transcript voted against captions or the script, glossary fixes, a corrections log |
| cut dead air, fillers, retakes | `rough-cut` | frame-exact cut, silent joins, retimed words, FCPXML for Resolve |
| narration from a script (your cloned voice or a stock one) | `voiceover` | sentence-checked narration and word timings |
| decide what appears when and where | `beat-sheet` | anchored cues, zone and read-time checks, motion assertions |
| music, sound effects, a mix at spec | `sound-bed` | bed with an exact beat grid, SFX, ducked mix at -16/-14 LUFS |
| motion graphics and overlays in HyperFrames | `motion-build` | a check-clean composition and renders |
| proof the render is right | `render-verify` | gates on the DOM and the encoded file, one visual read, a QA report |

Coming next: `reference-to-style`, `broll-sourcing`, `delivery-pack`, `skill-retro`, `video-director`.

## Tools

`tools/` holds the measurements and generators the skills call; each runs with `uv run tools/<name>.py --help`.
Probe and look: `media_probe`, `contact_sheet`, `scene_cuts`, `palette`, `faces`. Words: `transcribe_faster_whisper`
(GPU host), `reconcile`, `transcript_diff`. Cutting: `cut_plan`, `cut_render`. Voice: `voiceover`, `voiceover_check`,
`tts_worker_runner` (GPU host). Planning: `beats_check`. Sound: `beat_grid`, `beat_bed`, `sfx_synth`, `mix`,
`loudness`. Build and verify: `hf_scaffold`, `av_qa`, `face_clear`, `verify_report`.

## Examples

- [examples/rough-cut-fixture](examples/rough-cut-fixture): synthetic narration with a deliberate retake, filler, and
  dead air; shows transcript voting, silence-snapped cuts, join checks, and positive/negative controls.
- [examples/explainer-five-steps](examples/explainer-five-steps): a 60 s explainer narrated in devin-v1, planned on a
  beat sheet, built in HyperFrames, and verified (loudness, words, motion, layout, contrast).

Media is not committed; each example's records (briefs, beat sheets, reports) are.

## Validate

```bash
python3 scripts/validate.py
```
