---
name: video-director
description: Entry point for making or editing a video with editbay. Turns a request into an edit brief (goal, audience, sources, deliverables, brand, style, voice and consent, mode, human boundaries), routes it through the editbay steps or a HyperFrames workflow, plans which machine does what, sets a goal condition the run must prove with printed evidence, and runs the loop with checkpoints to delivery and a retro. Use when asked to edit a video, cut and package footage, make a reel, explainer, short, or motion piece, or "do the whole thing" from a file, URL, or idea.
---

# Video director

One request, one brief, one loop: intake, transcript, cut, voice, beat sheet, sound, sources, build, verify, deliver,
retro. The director decides what applies, keeps the creator's boundaries, and never calls a step done without its
evidence.

Paths: `$EB` is the editbay root, the folder holding `skills/` and `tools/` (`../..` from this skill's folder). Machine facts come from
`~/.config/editbay/config.json`.

## 1. Write the brief

Fill `EDIT.md` from the request ([references/edit-brief.md](references/edit-brief.md)). A good edit request carries:
the source, the tool, a style in a few words, the order of work, beats tied to spoken phrases and screen places,
legibility treatments, what the agent may source or generate, the point of the piece, and how it proves itself. Ask
only for what cannot be inferred: usually the brand, the voice, and the deliverables. Record voice-clone consent and
any spend in `HUMAN_QUEUE.md`.

**Done when:** `EDIT.md` names goal, audience, sources, deliverables and profiles, brand, style, voice, mode, and
boundaries, and nothing in it contradicts the brand profile.

## 2. Route

Pick the chain from [references/routes.md](references/routes.md): talking-head edit, narrated explainer, music-led
reel, footage reel from a big folder, captions only, or a pure HyperFrames workflow (hand off to `/hyperframes` when
the request is exactly one of its routes and editbay adds nothing). Plan the machines: downloads, ASR, and the cloned
voice on the GPU host; renders, encodes and tools locally (measured in docs/PROVIDERS.md, "Which machine does
what").

**Done when:** the chain of skills and the machine for each step are written into `EDIT.md`.

## 3. Set the goal condition

For long unattended runs, set a goal whose evaluator can check it from the transcript alone: it names the evidence
lines the run must print (the QA report verdict, the loudness lines, the delivery path) and a turn cap.
[references/goal-conditions.md](references/goal-conditions.md).

**Done when:** the condition is written in `EDIT.md` and every item in it is something a tool prints.

## 4. Run the loop

Execute the chain, one skill at a time, each to its **Done when**. In collaborative mode pause at the plan (BEATS.md)
and the final look; in autonomous mode post the same summaries and keep one question before publishing. Fire slow
jobs (TTS, ASR, renders, generation) in the background and overlap them with planning. Read sheets at phase
boundaries, in batches.

**Done when:** render-verify passes and delivery-pack has written `deliver/DELIVERY.md`.

## 5. Close

Hand over the delivery folder with a short summary of what was checked and what was not, then run skill-retro.

**Done when:** the creator has the folder and the summary, and `RETRO.md` exists with owners for every lesson.

## Checklist

- [ ] Brief complete; consent and spend in HUMAN_QUEUE.md
- [ ] Route and machines chosen
- [ ] Goal condition checkable from printed evidence
- [ ] Each step done to its criterion; checkpoints kept
- [ ] Delivered with an honest summary; retro written
