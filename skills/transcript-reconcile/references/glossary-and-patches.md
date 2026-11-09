# Glossary and patches

## glossary.json

```json
{"terms": [
  {"canonical": "Claude Code", "variants": ["cloud code", "claude to go"], "why": "Anthropic's coding agent (on screen 0:48)"},
  {"canonical": "kie.ai", "variants": ["key.ai", "kei ai"], "why": "named in the on-screen prompt at 7:02"}
]}
```

- Variants are matched as whole words, case-insensitively, longest first, after punctuation is stripped.
- A variant that is also an ordinary word ("cloud", "school") belongs in the glossary only when the video never uses
  the ordinary sense. Otherwise make it a time-anchored patch.
- Canonical spelling comes from evidence, in this order: on-screen text in the video, the official site or repo, the
  video's own description. Write where you saw it in `why`.

## patches.json

```json
{"patches": [
  {"at": "06:39", "find": "Cloud. In order", "replace": "Kling in order", "why": "on screen 6:35: 'Sending both to Kling'"}
 ],
 "notes": [
  {"at": "09:10", "note": "Sizzle reel plays: the quotes below are attendees, with burned-in captions."}
 ]}
```

- `at` anchors the search (the nearest match within `window` seconds, default 15, wins); `find` is matched on
  normalized words, so punctuation and case in `find` do not matter.
- Patches run before the glossary: write `find` in the raw transcript's words.
- `notes` become italic lines in the readable Markdown (music beds, other speakers, on-screen-only content).
- A patch miss means the words were not where you said: fix the anchor, never delete the patch silently.

## Evidence

A patch without evidence is a guess. Good evidence: a frame showing the word (save it under `transcript/evidence/`),
agreement of two other sources, or a listen at the timestamp with the reason written down.

## Normalization before another voice take

- Treat stable currency punctuation and proper-name splits as transcript normalization when the audio is intelligible:
  reconcile `$5,499`, `M5 Ultra Mac Studio`, or `Di Benedetto` against the script, glossary, and secondary ASR, then
  record the patch instead of rerolling the voice.
- Join an ASR hyphen suffix into the preceding caption/beat token (`one` + `-time` -> `one-time`; `Large` + `-scale`
  -> `Large-scale`). Preserve the first token's start, the suffix's end, and the spoken audio.
- After reconciliation, compare every company, product, and person name in final captions against the script and
  glossary. A sentence-level WER pass does not clear a caption-only proper-noun error.
