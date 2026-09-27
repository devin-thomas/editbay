# editbay design

editbay is a suite of agent skills for editing and making videos with a coding agent (Claude Code or Codex).
It packages one method, measured from real runs: **transcribe, cut, plan the beats, build with skills,
verify**, plus two loops that make the suite improve with use: **reference to style** and **feedback into
the skill**. "editbay" is a working name.

## Where it sits

HyperFrames (HeyGen, Apache-2.0) is the render engine and ships its own agent skills: `/hyperframes`
routes creation requests to workflows (`talking-head-recut`, `motion-graphics`, `music-to-video`,
`general-video`, …) and domain skills (`hyperframes-core`, `-animation`, `-keyframes`, `media-use`,
`hyperframes-cli`, …). editbay does not re-teach composition authoring. It owns what those skills leave to
the operator:

| Layer | Owner | Examples |
|---|---|---|
| Direction | editbay | the edit brief, the beat sheet, brand and style precedence, human boundaries |
| Measurement | editbay | transcripts reconciled across models, cut rhythm, beat grids, palettes, face zones, loudness |
| Machines | editbay | GPU host for ASR/TTS, local renders, cookies for downloads, credential names |
| Composition and render | HyperFrames skills | HTML timelines, GSAP, registry blocks, captions, `render` |
| Verification | both | `hyperframes check` for the DOM; editbay for the encoded file, the footage, the ear |
| Memory | editbay | style skills from references, retro notes folded back into skills |

## The loop

```
intake ──> transcribe ──> cut ──> beat sheet ──> build ──> verify ──> deliver
   │            │                     ▲            │          │
   │            └── word timings ─────┘            │          └──> retro ──> update the skill
   └── reference video ──> reference-to-style ──> style skill ─┘
```

Each stage writes files into one project folder, so any stage can be re-entered and any claim checked.

## Skills

| Skill | Owns | Main outputs |
|---|---|---|
| `video-director` | Turning a request into a brief, a route, and a run with checkpoints | `EDIT.md`, `HUMAN_QUEUE.md` |
| `footage-intake` | Getting sources in and looking at them | `media/inventory.json`, contact sheets, 16 kHz WAVs, proxies |
| `transcript-reconcile` | Word-timed transcripts you can trust (multi-pass, glossary, evidence) | `transcript/*.json`, `.words.json`, `.srt`, `.md`, corrections log |
| `rough-cut` | Removing flubs, retakes, dead air, and filler on word boundaries, frame-exact | `cut/edl.json`, `cut.mp4`, `cut.fcpxml`, keep list |
| `beat-sheet` | Anchoring every visual event to a spoken word or a musical beat | `beats/BEATS.md`, `beats.json`, beat grid |
| `motion-build` | editbay's HyperFrames conventions: overlays that respect the face, legibility, brand tokens | `hf/` project |
| `sound-bed` | Music, SFX, ducking, loudness to target | `sound/mix.wav`, stems, `loudness.json` |
| `broll-sourcing` | Screen recordings, screenshots, official logos, optional generation, with provenance | `assets/`, `assets/ledger.json` |
| `render-verify` | The verification loop on the rendered file, with evidence and a repair budget | `qa/REPORT.md`, strips, sheets |
| `delivery-pack` | Masters, review copies, vertical cut, captions, chapters, thumbnails, manifest | `deliver/` |
| `reference-to-style` | Measuring a reference video and writing a reusable style skill from it | a new `style-*` skill |
| `skill-retro` | Folding feedback and QA findings back into the skills that produced them | `RETRO.md`, skill edits, changelog |

A style skill (for example `style-signal-reel`) is the output of `reference-to-style`: a grammar, a measured
breakdown, templates, and its own acceptance numbers.

## Precedence

1. **Brand profile** (hard constraints: palette, fonts, forbidden devices, loudness, voice rules).
2. **Style skill** (grammar learned from references).
3. **The request** (one-off direction).
4. **Agent taste** (fills gaps; must be named in the plan so it can be vetoed).

When a style asks for something the brand forbids (HUD numbers, particles, glitch, orange), the brand wins and
the plan says so.

## Project folder contract

```
<project>/
  EDIT.md          brief: goal, audience, sources, deliverables, brand, style, mode, boundaries
  HUMAN_QUEUE.md   only real boundaries: spend, sign-ins, voice likeness, publishing, final taste
  media/           sources (or links to them), proxies, inventory.json, sheets/
  transcript/      reconciled transcript + glossary + corrections log
  cut/             edl.json, cut.mp4, cut.fcpxml
  beats/           BEATS.md (human), beats.json (machine), grid.json (music-led)
  assets/          ledger.json + images/ clips/ logos/ fonts/
  sound/           music, sfx, stems, mix.wav, loudness.json
  hf/              HyperFrames project (index.html, compositions/, assets symlinked or copied)
  renders/         draft/, review/, master/
  qa/              REPORT.md + evidence
  deliver/         final files, captions, chapters, thumbnails, manifest.json (sha256)
  RETRO.md         what to keep, what to change, which skill it belongs to
```

Media stays out of git; records (briefs, sheets, reports, manifests) go in.

## Configuration

Machine and person-specific facts live in config, never in skills:
`~/.config/editbay/config.json` (user) and optional `<project>/editbay.json` (project override).
See `config/config.example.json`. It names the GPU host (ssh alias, shell, work root, Python),
the credentials file and the variable names each provider reads, the default brand, and delivery profiles.
Brand profiles are JSON (`brands/_template.json`); personal brands live in `~/.config/editbay/brands/`.

## Verification contract

- **Automated gates** run on every render: `hyperframes check` (DOM: layout, contrast, motion sidecars),
  `tools/av_qa.py` (encoded file: spec, black, freeze, silence, pops, A/V length),
  `tools/loudness.py` (target and true peak on the delivered file), `tools/beat_grid.py align` (cuts on the
  grid, music-led pieces), the face keep-clear check (overlays vs. `tools/faces.py` zones), captions vs. the
  reconciled transcript.
- **Visual gate**: one overview sheet (2 fps for pieces under 60 s) and a strip at every cut, read at phase
  boundaries, not per frame. Attached images re-price the context: batch them.
- **Repair budget**: two autonomous repair passes per finding, then it goes to `HUMAN_QUEUE.md` with the
  timestamp and the evidence file.
- **Honest labels**: generated media is labelled as generated and never presented as evidence; unperformed
  checks are reported as pending, never as passed.

## Privacy and cost

- `hyperframes snapshot --describe false` always: with a Gemini key in the environment, describe mode sends
  frames to Gemini.
- Telemetry off (`HYPERFRAMES_SKIP_SKILLS=1` for scaffolding in CI-like runs, `hyperframes telemetry disable`
  only with the user's consent since it is persistent).
- Paid generation (kie.ai, Kling, Veo, Suno, ElevenLabs) is opt-in per run, with an estimate written to
  `HUMAN_QUEUE.md` before the first call. Local and free paths come first: procedural SFX and beds, local
  TTS, own captures.

## Portability

Every skill works in Claude Code and Codex: `SKILL.md` (name + description frontmatter) plus
`agents/openai.yaml`. Tools are Python with inline `uv` metadata (`uv run tools/x.py`), so they run the same on
macOS and Windows. Skills name tools by path relative to the plugin root.
