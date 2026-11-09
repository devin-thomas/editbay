---
name: voiceover
description: Script to narration you can time against, in the creator's own cloned voice when configured. Writes the spoken layer, generates one sentence per TTS call with one seed per beat (a cloned voice on the GPU host, a local Qwen3-TTS worker, macOS say for drafts, or HyperFrames Kokoro), joins sentences with fixed gaps, checks every sentence against the script with ASR, re-rolls failures, and hands word timings to the beat sheet. Use when a video needs a voiceover, narration, or TTS, when a faceless explainer needs a voice, or when rehearsing a script's timing.
---

# Voiceover

Pace is set when the voice is generated, never by stretching audio afterwards. Cloned voices read fast in one shot
(171-215 wpm measured); one request per sentence with one seed per beat, joined with 0.4 s, reads about 144 wpm.
It also keeps failures small: a garbled sentence is re-rolled alone, and the rest stays byte-identical.

Paths: `$EB` is the editbay root, the folder holding `skills/` and `tools/` (`../..` from this skill's folder). Tools run as `uv run $EB/tools/<tool>.py`.
TTS engines and their paths come from `~/.config/editbay/config.json` (`tts`).

## 1. Write the spoken layer

Keep what is said separate from what is shown: cue blocks (`~~~cue ... ~~~`), notes (`>`), headings, table metadata,
and lines beginning `On-screen:`, `Pronunciation:`, or `Metadata:` are skipped by the generator and copied to
`narration/script-metadata.md`. One paragraph per beat, tagged `[B01]`. Write numbers, times, and symbols the way they
are said ("five point five", "three P M"), spell out acronyms the voice would mangle, and keep sentences under about
25 words. Pronunciation notes belong in `transcript/glossary.json` or a skipped metadata block, never as plain text in a
spoken paragraph. When a glossary is supplied, validate every term before starting TTS: it must include non-empty
`canonical`, `variants`, and `why` fields, even when the canonical form is the only accepted spelling. Voice and tone rules come from the brand profile
(`voice`). Guide: [references/script-craft.md](references/script-craft.md).

**Done when:** every paragraph carries a beat tag and reads aloud cleanly at 140-160 words per minute (count it).

## 2. Choose the voice

The config's `tts.default_voice` names the voice; `tts.voices.<name>` says how it runs. Read the configured voice ID
and pass that exact ID; never infer a voice from an example name. A creator's cloned voice runs
on the GPU host through its own worker (`engine: remote`) and carries a `consent` note and a `disclosure` line: use it
when the creator asked for it (record where and when in `HUMAN_QUEUE.md`), and put the disclosure in the video's
description or end card. A stock voice needs neither. Drafts can use `--engine say` to rehearse timing for free.

**Done when:** the voice is chosen, and for a clone the consent line and the disclosure placement are written down.

## 3. Generate

```bash
uv run $EB/tools/voiceover.py script.md --out narration/ --engine remote --voice-config creator-clone \
  --story-slug STORY_SLUG --producer-callsign PRODUCER_CALLSIGN   # cloned voice; isolated gpu-workstation namespace
uv run $EB/tools/voiceover.py script.md --out narration/ --engine qwen3-worker --voice aiden \
  --python "$TTS_PY" --worker "$TTS_WORKER" --ckpt "$TTS_CKPT" --device mps                    # local stock voice
```

The remote engine sends only the sentences that need generating to `tools/tts_worker_runner.py` on the host, which
takes that machine's GPU lock (shared with other narration pipelines there), keeps the model loaded for the batch,
and returns the WAVs in one transfer. Its remote directory is `STORY_SLUG--PRODUCER_CALLSIGN`, never a generic
`narration/` basename; use `--dry-run` to print the namespace before taking the GPU lock. `narration/narration.json`
records each sentence's text, seed, and position; re-runs reuse unchanged sentences within that isolated namespace.
When other jobs hold the GPU lock, the runner queues (up to 45 min, printing "GPU busy ... waiting"), so start remote TTS
in the background and poll its log. Inspect the full owner command before diagnosing a busy lock; never stop the owner
or retry indefinitely. Record the lock evidence, and use a timing fallback only when it is explicitly labelled and never
delivered. Never substitute another voice for a cloned one: if the lock times out, rerun or escalate, keeping the
cloned-voice delivery risk explicit.

**Done when:** `narration.wav` and `narration.json` exist and the overall pace is 140-165 wpm (the tool prints it;
short sentences read faster, so judge pace on the real script, not a fragment).

## 4. Check every sentence

Transcribe `narration.wav` once (transcript-reconcile step 2; turbo is enough), then:

```bash
uv run $EB/tools/voiceover_check.py narration/narration.json t.turbo.json --glossary transcript/glossary.json
```

The check aligns the heard words to the script by sequence (Whisper stamps sentence starts 0.2-0.3 s early, so time
windows would drop first words). A failing sentence prints what was heard and a ready `--redo` list. Re-run step 3
with `--redo N,M` (new seed for those sentences only), re-check, and stop after two re-rolls of the same sentence:
rewrite it (shorter, different words). A beat still too fast after four seeds is a script problem. TTS failures
sound fluent; only the check catches them.

**Done when:** every sentence passes, with the number of re-rolls noted in `narration/NOTES.md`.

## 5. Hand off timings

Reconcile the narration transcript with the script as the third source
(`reconcile.py --primary t.v3.json --secondary t.turbo.json --script script.md --out narration/words`): the result's
`words.words.json` is what beat-sheet anchors to and what captions display.

**Done when:** `narration/words.words.json` exists and its word count matches the script's spoken words.

## Checklist

- [ ] Spoken layer written with beat tags; pace counted
- [ ] Glossary entries validated with `variants`; pronunciation and on-screen metadata are not spoken and are filed separately
- [ ] Voice chosen; clone consent and disclosure placement recorded when used
- [ ] One seed per beat; pace 140-165 wpm on the real script
- [ ] Shared GPU lock evidence recorded; any fallback is timing-only and labelled
- [ ] Every sentence checked against the script; re-rolls logged
- [ ] Word timings reconciled against the script and handed to the beat sheet
