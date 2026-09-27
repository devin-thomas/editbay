---
name: transcript-reconcile
description: Word-timed transcripts you can cut and caption against. Transcribes speech twice (Whisper large-v3 and turbo, on the configured GPU host), votes the passes against a third source (platform captions or the script), fixes names with a glossary and evidence-backed patches, and logs every change. Use when a video, recording, stream, or narration needs a transcript, captions, subtitles, word timestamps, or a transcript correction, and before any cut, beat sheet, or caption work. Feeds rough-cut, beat-sheet, and motion-build.
---

# Transcript reconcile

A transcript is only as good as its worst name. Two Whisper passes plus a third source, a glossary, and patches you can
defend: every change lands in a log with its reason, and nothing downstream reads an unreconciled transcript.

Paths: `$EB` is the editbay plugin root (two folders above this file). Tools run as `uv run $EB/tools/<tool>.py`.
The GPU host, its Python, and its work folder come from `~/.config/editbay/config.json` (`gpu_host`).

## 1. Prepare the audio and the third source

- Extract 16 kHz mono WAV: `ffmpeg -i SRC -vn -ac 1 -ar 16000 -c:a pcm_s16le audio.wav`.
- Pick the third source: platform auto-captions (a YouTube source: `yt-dlp --write-auto-subs --sub-langs en,en-orig
  --sub-format vtt --skip-download`), or the script (narration), or none (then two passes plus patches).
- Start `transcript/glossary.json` with every name, product, and term you can already see: the title, description,
  on-screen text, file names, the brief. Format and evidence rules: [references/glossary-and-patches.md](references/glossary-and-patches.md).

**Done when:** `audio.wav` exists, the third source is downloaded or named, and the glossary lists every proper noun
visible so far.

## 2. Transcribe twice on the GPU host

Copy `$EB/tools/transcribe_faster_whisper.py` and the WAV to the GPU host, then run it twice:

```bash
python transcribe_faster_whisper.py audio.wav --model large-v3 --prompt-file vocab.txt --out t.v3
python transcribe_faster_whisper.py audio.wav --model large-v3-turbo --batched --out t.turbo
```

`vocab.txt` is a comma list of the glossary's canonical names (spelling bias, not an instruction). Copy the four
outputs back. Remote mechanics (ssh, PowerShell, venv): [references/remote-gpu.md](references/remote-gpu.md). With
no GPU host, run the same script locally with `--device cpu --compute int8` (slow), or `npx hyperframes transcribe
audio.wav --model large-v3` for a single pass.

**Done when:** both JSON files are back and their word counts are within 5% of each other (a bigger gap means a
dropped or hallucinated stretch: find it before continuing).

## 3. Reconcile

```bash
uv run $EB/tools/reconcile.py --primary t.v3.json --secondary t.turbo.json \
  --captions src.en-orig.vtt   # or: --script script.md
  --glossary transcript/glossary.json --patches transcript/patches.json \
  --chapters src.info.json --title "..." --out transcript/final
```

Read `final.corrections.md` top to bottom. Majority fixes and glossary hits are usually right; check a sample.
Each unresolved disagreement and each low-confidence word gets a decision: look at the frame (on-screen text settles
most names), listen if needed, then add a patch with the evidence in `why`, or leave it and say why. Known failure
patterns (inventions after pauses, prompt-induced phrases, dropped sentences, split compounds):
[references/failure-modes.md](references/failure-modes.md).

**Done when:** the log shows 0 patch misses, every unresolved span has a patch or a written reason, and every
glossary term appears only in its canonical spelling.

## 4. Hand off

Outputs in `transcript/`: `final.json` (segments + words, source timeline), `final.words.json` (HyperFrames word
array), `final.srt`, `final.vtt`, `final.md` (readable, by chapter), `final.corrections.md`. Downstream tools read
`final.json` or `final.words.json`; after a cut, use the retimed words from rough-cut instead.

**Done when:** the files exist and the brief (`EDIT.md`) points at them.

## Checklist

- [ ] Two passes from different models, plus a third source when one exists
- [ ] Glossary covers every name seen on screen, in the title, and in the brief
- [ ] Corrections log read in full; 0 patch misses; every unresolved span decided with evidence
- [ ] Captions and cuts built from `final.*`, never from a raw pass
