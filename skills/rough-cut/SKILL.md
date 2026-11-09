---
name: rough-cut
description: Rough-cut talking footage on word boundaries. Removes dead air, standalone fillers, and retakes (explicit restart phrases; implicit restarts are suggested), moves every cut into real silence and onto a frame, renders frame-exact with sample-exact audio, checks that every join is silent, and exports FCPXML for Resolve or Final Cut. Use when asked to cut mistakes, silences, pauses, ums, retakes, or dead space, to tighten a recording, or to prepare a clean take for graphics. Needs a reconciled transcript (transcript-reconcile).
---

# Rough cut

Cut what the speaker would cut, keep the breath that makes it sound human, and prove every join is clean. The plan is
data (an EDL and a keep list) that a person can veto before anything renders.

Paths: `$EB` is the editbay root, the folder holding `skills/` and `tools/` (`../..` from this skill's folder). Tools run as `uv run $EB/tools/<tool>.py`.

## 1. Check the inputs

- `transcript/final.json` from transcript-reconcile, on the SOURCE timeline. A raw Whisper pass is not enough: its
  invented words become cuts in the wrong places.
- `uv run $EB/tools/media_probe.py SOURCE`: a variable-frame-rate warning means conform first
  (`ffmpeg -i SRC -fps_mode cfr -r 30 ...`), or frames will drift against the EDL.

**Done when:** the transcript is reconciled and the source is constant frame rate.

## 2. Plan

```bash
uv run $EB/tools/cut_plan.py transcript/final.json --media SOURCE --out cut/ \
  --max-gap 0.7 --keep-gap 0.3 --implicit-retakes suggest
```

Read `cut/KEEP-LIST.md` in full. For each removal ask: would the speaker cut this? Protect deliberate pauses, punchlines,
and reaction beats with `--protect 12.0-15.5` and re-plan. Implicit retakes are only suggested: apply one by re-running
with `--implicit-retakes apply` after reading its words, or leave it. Pacing guide:
[references/pacing.md](references/pacing.md).

A piece assembled from parts of a long take in a new order (a promo from a rambling recording) uses
`--selects selects.json`: `[{"label", "in", "out"}, {"gap": 3.0, "label": "insert"}, ...]` in output order, with
`in`/`out` at the first word's start and the last word's end. Each select keeps its first and last word (edges snap
to the silence around the words, never into them), dead air inside it is still removed, and a gap holds a black,
silent slot of exact frames for an insert placed later. A select with no silence at an edge is reported as a hard
cut: pick a neighbouring word, or let the join check judge. Take word times from the second ASR model when the first
has drifted (compare the two around each edge).

**Done when:** every removal in the keep list is either accepted or protected, and every suggestion has a decision.

## 3. Render and prove the joins

```bash
uv run $EB/tools/cut_render.py cut/edl.json --out cut/cut.mp4 --fcpxml cut/cut.fcpxml
```

The renderer keeps frames by index and audio by sample (a reordered EDL renders one forward run at a time and joins
the runs without re-encoding; gaps become black frames and silence, and a marker in the FCPXML), fades 5 ms at each
join, then measures every join: a join
louder than -30 dBFS within 25 ms means a clipped word or leftover sound (exit 1). Fix by re-planning (a wider
`--silence-db`, or protect the range), never by nudging the render.

**Done when:** video and audio durations match the EDL to the frame and every join prints `in silence`.

## 4. Verify the words

Transcribe `cut/cut.mp4` once (turbo is enough) and compare with what should remain:

```bash
uv run $EB/tools/transcript_diff.py cut/words.cut.json cut/cut.turbo.json
uv run $EB/tools/av_qa.py cut/cut.mp4 --expect-fps FPS --min-silence 1.0
```

Missing or changed words are findings. Inserted words are listed for review: ASR invents "Wait,"/"Um," over short
pauses, so listen at those timestamps once instead of trusting the transcript. On camera footage, look at a strip at
each join (`contact_sheet.py cut/cut.mp4 --around T1,T2`): a visible jump on a talking head gets covered later with a
punch-in or B-roll (note it in `cut/JUMPS.md` for the beat sheet).

**Done when:** 0 transcript findings, every insertion listened to or explained, av_qa passes, and visible jumps are
listed.

## 5. Hand off

`cut/cut.mp4` (review), `cut/cut.fcpxml` (import into Resolve: File > Import > Timeline; it points at the original
source, so the editor keeps full quality), `cut/words.cut.json` (words retimed to the cut, for captions and beats),
`cut/edl.json`, `cut/KEEP-LIST.md`.

**Done when:** the brief points at the cut and its retimed words.

## Checklist

- [ ] Reconciled transcript in, constant frame rate source
- [ ] Keep list read; protections and suggestions decided
- [ ] All joins in silence; durations match to the frame
- [ ] Transcript diff clean; insertions checked by ear; jumps noted
