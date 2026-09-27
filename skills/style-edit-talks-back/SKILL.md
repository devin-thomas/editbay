---
name: style-edit-talks-back
description: A talking-head edit in which the edit itself is a second character. Deadpan monospace asides, running-gag counters, punch words, parody lower thirds and props react to what the host says, with a visual event every one to two seconds over tight speech and a parody-world cold open. Use when asked for a funny or personality-driven talking-head edit, a vlog, a behind-the-scenes piece, or an edit "like those AI-channel videos", or when a brief names this style. Learned from eight measured videos (see Source); takes its type, palette and worlds from the brand.
---

# Style: the edit talks back

The host talks; the edit answers. Every joke the edit makes is text on screen, so the voice stays the host's and the
humour comes from the reply. Source of truth: [references/breakdown.md](references/breakdown.md) (principles 1-8,
measured on eight videos); this skill restates them as rules with numbers.

Paths: `$EB` is the editbay root, the folder holding `skills/` and `tools/` (`../..` from this skill's folder). Tools run as `uv run $EB/tools/<tool>.py`.

## Grammar

1. **The editor speaks in asides.** Monospace, lowercase, one to six words, in brackets or parentheses, deadpan:
   doubt, correct, count or confirm the line just said. About one every 6-10 s of annotated A-roll. Never explain
   the joke; never put information only in an aside.
2. **One running counter per piece at least.** A boxed monospace counter in a corner, named for something the host
   keeps doing; it ticks (sound: tick) on the word, and its first tick gets an aside ("(we are counting)" is the
   reference's; write your own).
3. **Punch words** in the brand's heaviest condensed type: one to three words on the stressed syllable, beside the
   head (in the face's free zone), 0.6-1.5 s, overshoot in, fast out. A word said twice stacks and grows.
4. **Parody lower thirds** once or twice a piece: the name line plain, the second line the joke.
5. **Cold open in a world** from the brand's own domain, 10-30 s, where the host's first lines become the world's
   text (a ticker, a HUD, speech bubbles, a game's dialogue box). Hard or glitch cut out of it into the A-roll.
6. **Density:** a new visual event every 1-2 s in A-roll (cut, punch-in, word, aside, counter tick, prop, inset).
   Punch in 1.0 -> 1.10-1.15 on every second or third jump cut; never zoom continuously.
7. **Tight speech:** every pause removed at the cut (cut_plan edges in silence); target 190-235 wpm in A-roll.
8. **Props land conclusions:** an object for the idea (a tombstone for something dead, a podium for a ranking,
   stamps for a list). Explanations sit on a screen or a dark canvas with the host's cut-out in a lower corner.
9. **Reaction clips:** the host's own short lines ("damn", "this is so funny", "hold on") cut in after a card as
   replies. Only lines from the host's own footage.
10. **End on a plain frame and one last gag** (a form whose last box gets ticked late, an applause light).

## Planning recipe

1. Mark the transcript: stressed words (punch words), claims to doubt or correct (asides), repeated things
   (counters), flubs and reactions (reaction clips), pauses (cut). Write the marks into BEATS.md with times.
2. Pick the world for the cold open from the brand's domain, not the reference's (a fighting-game creator gets a
   training-mode HUD, a cook gets a cooking show).
3. Cut the A-roll tight with cut_plan `--selects`; assign punch-ins; then place one annotation event every 1-2 s.
4. Chapters of 40-120 s, each opening on a title card or world change; intro under 60 s.

## Sound

- Voice first and flat: loudness range 2-3 LU in the reference. Duck the bed under speech; effects never cover a
  word.
- Effects are small and tied to events: tick for counters, pop for punch words, whoosh or glitch for world changes,
  a bleep for censored words. Synthesize them (sfx_synth.py); no stock effects.

## Brand adaptation

The reference's signature stays with it: colour-bars "please stand by" opener, yellow condensed type on a green
backdrop, its lower-third design and wording, AI-generated versions of the host. Use the brand's type (its
heaviest, narrowest width for punch words, its monospace or a plain mono for asides), its palette for punch words
and counters, its motion language (Liquid Glass, for example), and worlds from its domain. A brand minimum text size
applies to asides too: they carry jokes.

## Acceptance numbers

| check | target | how |
|---|---|---|
| visual events in annotated A-roll | >= 25 per minute | scene > 0.07 events on the render |
| speech rate in A-roll | >= 190 wpm | transcript of the render |
| asides | >= 1 per 10 s of annotated A-roll | beat sheet count |
| running counters | >= 1 per piece | beat sheet |
| cold open | a world within 2 s, <= 30 s | render sheet |
| text | passes text_check at the brand minimum | text_check.py |
| loudness | platform target, LRA <= 6 LU | loudness.py |

## Checklist

- [ ] Transcript marked: punch words, asides, counters, reactions, cuts
- [ ] Cold-open world from the brand's domain; reference signature absent
- [ ] Event density and speech rate measured on the render
- [ ] Every aside readable at the brand minimum; nothing load-bearing only in an aside
- [ ] Effects synthesized; bed ducked; loudness passes
