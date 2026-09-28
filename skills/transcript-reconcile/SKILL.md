---
name: transcript-reconcile
description: Word-timed transcripts you can cut and caption against. Transcribes speech twice (Whisper large-v3 and turbo, on the configured GPU host), votes the passes against a third source (platform captions or the script), fixes names with a glossary and evidence-backed patches, and logs every change. Use when a video, recording, stream, or narration needs a transcript, captions, subtitles, word timestamps, or a transcript correction, and before any cut, beat sheet, or caption work. Feeds rough-cut, beat-sheet, and motion-build.
---

# Transcript reconcile

A transcript is only as good as its worst name. Two Whisper passes plus a third source, a glossary, and patches you can
defend: every change lands in a log with its reason, and nothing downstream reads an unreconciled transcript.

Paths: `$EB` is the editbay root, the folder holding `skills/` and `tools/` (`../..` from this skill's folder). Tools run as `uv run $EB/tools/<tool>.py`.
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

```bash
uv run $EB/tools/asr_remote.py audio.wav --out-dir transcript/ --prompt-file vocab.txt \
  --story-slug STORY_SLUG --producer-callsign PRODUCER_CALLSIGN
```

It copies the audio and `transcribe_faster_whisper.py` to the configured GPU host, runs large-v3 (sequential, with
the prompt) and turbo (batched), brings back `t.v3.*` and `t.turbo.*`, and prints both word counts and whether they
agree within 5%. `vocab.txt` is a comma list of the glossary's canonical names (spelling bias, not an instruction).
Remote mechanics, for debugging: [references/remote-gpu.md](references/remote-gpu.md). With no GPU host, run
`$EB/tools/transcribe_faster_whisper.py` locally with `--device cpu --compute int8` (slow), or
`uv run $EB/tools/hf.py transcribe audio.wav --model large-v3` for a single pass. Remote ASR uses the same
`STORY_SLUG--PRODUCER_CALLSIGN` namespace under the configured work root; use `--dry-run` to inspect it without using
the GPU host.

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

Before another voice reroll, compare both ASR passes with the supplied narration and normalize stable currency punctuation
and glossary product/person tokens against the script; an intelligible split such as `$5,499` is a transcript patch, not a
reason to regenerate audio. Keep the reconciled heard-word file with the original timings and patch evidence. After any
punctuation, hyphen, or timestamp reconciliation, rebuild the composition and sidecar captions from `final.words.json`,
rerender before packaging, and seek into any count-up hold so captions and motion use the same final word array.

If the script has a bare numeral but the rendered speech clearly says its ordinal form (for example, `13` heard as
`13th`), patch the final caption token to the heard form with a timestamp-safe evidence note. Do not change the spoken
script unless the fact itself changed; log the wording correction so the timing decision is reproducible.

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
- [ ] Stable numeric/proper-name splits are patched with evidence; hyphenated caption tokens stay joined
- [ ] Any timing or punctuation repair was rebuilt and rerendered before packaging
- [ ] Captions and cuts built from `final.*`, never from a raw pass
