# Research: one-prompt video editing, September 2026

The analysis behind editbay, written 2026-09-26. Sources are our own transcript of Nate Herk's video (two Whisper
models on the GPU host, voted against YouTube's captions, 82 corrections logged), frame sheets, and the public posts
and repositories linked below. This page summarises and measures in our own words. The transcript, frames, and
downloaded media stay in the private research folder.

## Source chain

| Date (UTC) | Who | What |
|---|---|---|
| 2026-09-24 | kirill sh ([post](https://x.com/shneural/status/2103151003272962130)) | Ran one short prompt on Opus 5.5 and on GPT-6 Astra ("Astra Max" on the title card): make a 15-second motion-graphics piece that shows off the model as a motion designer, as if it were a résumé showreel. Posted the two results one after the other (about 32 s, Opus first) and preferred Opus. |
| 2026-09-25 | Kenn Ejima ([post](https://x.com/kenn/status/2103337314021937232)) | Quoted it with his own 15 s, 1080p60 reel from the same prompt at xhigh effort. The post does not name the tooling; the video says HyperFrames. Our breakdown: [BREAKDOWN.md](../../examples/style-from-kenn-reel/reference/BREAKDOWN.md). |
| 2026-09-25 | Nate Herk ([video](https://www.youtube.com/watch?v=7jHXoPGnA4c), 19:22) | Seven edits made in Claude Code with HyperFrames, mostly from one prompt each, then five steps for editing with AI. |
| ongoing | [HyperFrames Student Kit](https://github.com/nateherkai/hyperframes-student-kit) | The skills behind the video. MIT, with the AI Automation Society brand assets excluded. 15 skill folders; pins HyperFrames 0.7.109. |
| current | [HyperFrames](https://github.com/heygen-com/hyperframes) (HeyGen) | 0.8.79, Apache-2.0. HTML compositions on one paused GSAP timeline, rendered to video, with its own agent skills. |

**One prompt, one house look.** kirill's Opus result and Kenn's reel share a skeleton: a red ball dropping onto a
ruled line under a small HUD with tempo and frame-rate labels, kinetic type on paper, a word repeated into a
wallpaper, a grid of dots and shapes, voxels, and a particle swirl. The video also points out that the AIS showreel
opens with the same dropping bead. Much of that look is what Opus 5.5 does with this prompt, not one creator's
signature. So style-craft-reel keeps the principles and steers the motif, words, and palette away from it: the craft
reel uses a text caret, not a dot.

## What the video shows

Nearly every piece ran at High effort, per the video.

| At | Piece | Input and ask (summarised) | What the agent added unasked | Prompts |
|---|---|---|---|---|
| 00:00 | The video's own intro | A talking-head take. Edit it clean and engaging in HyperFrames; transcribe first; bring in the logos of two named models where he points; put a card behind anything animated so it reads; set three spoken words at the bottom and highlight them; fetch recordings, screenshots, and generated media to show the capability. | A slow push-in at the open, a chat-interface mock-up, an animated segment about checking screenshots, an overlay under the highlighted words. | 1 |
| 04:20 | YouTube showreel | Kenn's reel given to the agent to explain why it works; the explanation turned into a skill (motion-showreel); the skill run to make a reel that reads unmistakably as YouTube. | Chose a thumbnail of Nate holding a play button as the hero, and said why. Generated stills, animated them in Kling, cut the clips in. | 1, plus the skill |
| 06:58 | AIS showreel | kirill's prompt, aimed at his company: use real product assets and logos, kie.ai for anything generated, any tool for motion and sound. | Pictures from the company site and its real member count; what Nate takes to be a generated 3D image, animated to video. | 1 |
| 08:40 | AIS Live sizzle reel | A 105 GB folder of event recordings. Tell a story. | Chose attendee and speaker moments from transcripts; a tunnel of screens; the event logo assembled from scenes. Nate names flaws, such as an awkward cut in a speech. | 3 (one round of notes, one fix) |
| 10:40 | One take, three styles | A hand-drawn whiteboard explainer for a child (full screen or split with his face); a course layout (camera to a rounded crop, big short bullets, simple generated images); a fast vertical short. | Tested as it went; a verification still appears in the screen recording. Nate's critique is about content (tiny eggs, glaze in one spot), not craft. | 1 each |
| 14:53 | Lululemon spec ad | Only a mood: high energy, fast, cut to the music, sound effects. | By Nate's reading, found real product images on the brand's site and generated clips of models wearing them. | 1 |
| 16:12 | Five steps | Transcribe, cut, plan the beats, build skills, verify. | | |

## The five steps, and what makes each one hold

The five steps are right, and they are editbay's spine. As told in the video, each rests on the model's judgement.
editbay adds, for each, a measurement that can fail.

| Step | In the video | What slips without a check | editbay | The check |
|---|---|---|---|---|
| Transcribe | ElevenLabs (paid, fast) or Whisper (free, slower) | Names and brands: this video's own ASR heard the OpenAI model as "GBD6" and Claude Code as "Cloud Code" | transcript-reconcile | two models voted against captions or the script, a glossary, a corrections log, a words gate |
| Cut | remove mistakes and dead air | Word timings drift and ASR invents fillers at joins, so cuts land in a breath | rough-cut | cuts snapped to measured silence; a silence check at every join, proven with positive and negative controls |
| Plan the beats | say what comes in when; a tighter plan gives a closer result | Cues pile up, cover the face, or leave too soon to read | beat-sheet | anchored cues, zone and read-time checks, motion assertions |
| Skills | build skills for repeated work; feed each run's likes and dislikes back | Lessons stay in chat and get repeated | reference-to-style, skill-retro | a style skill with an acceptance table; RETRO.md with an owner for every change |
| Verify | the agent watches its own output and iterates before handing over | One glance passes for a check; loudness, true peak, and word accuracy cannot be judged from frames | render-verify, delivery-pack | printed gates, one visual read per pass, at most two repair passes, and PENDING for any check that did not run |

## Why the prompts worked

The intro prompt is the model to copy. It names the source and the tool, the order of work, beats tied to spoken
phrases and to places on screen, a legibility rule, an emphasis rule, what the agent may fetch or generate, and the
point the piece must prove. The brief template in
[edit-brief.md](../../skills/video-director/references/edit-brief.md) turns that into ten lines, with our own
examples.

Two moves in the video matter more than any single prompt:
- **Feelings plus a reference.** When he could not describe the result, he described how it should feel and handed
  over a video he liked; the reference carried the specifics. reference-to-style makes that repeatable: it measures
  the reference (tempo, cut grid, palette, pacing), writes the principles into a style skill, and leaves the
  reference's signature behind.
- **Plan density is a dial.** A full beat plan gets exactly those beats; a loose one invites the agent's own ideas,
  which were often the best parts of the intro. beat-sheet records which mode a run is in (strict or open).

## Agent behaviours worth keeping

1. Words before graphics: the transcript sets both the timing and the story.
2. Legibility without being told: cards and scrims under anything over footage.
3. Asset choices with reasons, stated (the hero thumbnail).
4. Draft, look, fix, before handing over. The Student Kit's motion-showreel skill makes this concrete: re-analyse
   its own render with cuts within about 35 ms of the beat, 10-frame strips across every transition, a brand test on
   random frames, -14 LUFS, and a VERIFY.md.
5. Skills distilled from references, then refined run by run.

## What the video leaves out

- **Paid defaults.** ElevenLabs Scribe, kie.ai, Kling, and ElevenLabs sound effects are the easy path in the kit.
  With a 4090 and an M5 Max, local routes cover most of it: faster-whisper for words, the Qwen3-TTS clone for
  narration, synthesised effects and beds on an exact grid. Costs and alternatives: [PROVIDERS.md](../PROVIDERS.md).
- **Render loudness.** The kit masters to -14 LUFS / -1.2 dBTP, but HyperFrames 0.8.79 changes the level of the
  audio it renders (measured -1.8 dB on a -14.3 LUFS mix, and -1.4 dB on one of two -16.0 LUFS mixes). Every render
  needs the mastered mix put back and measured again: `tools/remux_audio.py`.
- **Provenance.** Product photos, logos, and generated clips of people in a brand's clothing are fine for a private
  test and a problem in anything published. broll-sourcing records every asset's kind, source, and licence, labels
  generated media, and fails the build when something on screen has no record.
- **Narration.** The video only edits the creator's own takes. editbay adds narration in the creator's cloned voice,
  with consent recorded and a disclosure on screen.
- **Evidence.** An agent saying it watched its render is a claim. editbay's gates print their results; for unattended runs, a `/goal`
  condition must name those printed lines and a turn cap, because its evaluator reads only the transcript
  ([goal-conditions.md](../../skills/video-director/references/goal-conditions.md)).
- **Effort.** The video ran at High and Kenn at xhigh; Claude Code's default for Opus 5.5 is medium. Set it per run:
  high or xhigh for motion builds, lower for mechanical cuts.

## Student Kit and editbay

| | Student Kit | editbay |
|---|---|---|
| Words | ElevenLabs Scribe by default, Whisper optional | two local Whisper models voted against captions or the script, glossary, corrections log |
| Cuts | transcript-driven pause and mistake removal | the same, snapped to measured silence and gated at every join; FCPXML for Resolve |
| Voice | none | cloned or stock narration, sentence-checked against the script |
| Music and effects | kie.ai (Suno) beds and ElevenLabs effects | synthesised beds with an exact grid and synthesised effects; paid options documented |
| Style | motion-showreel, built from Kenn's reel | reference-to-style (any reference) and style-craft-reel, built without the reference's signature |
| Verification | VERIFY.md with strips, re-analysis, a brand test | printed gates with controls, PENDING for anything unchecked, a QA report, a phone-width read |
| Packaging | Claude Code skills with a Codex mirror | a Claude Code plugin with Codex interfaces, synced to private-skills |

## Measured

From the reference reel ([MEASUREMENTS.md](../../examples/style-from-kenn-reel/reference/MEASUREMENTS.md)): about
129 BPM detected (its on-screen label says 128); 7 of 12 cuts within 2 frames of a half-beat once the detector's lag
is removed; cuts by third 2, 1, 9; a 2 s final hold; mastered at -12.4 LUFS and -0.6 dBTP.

From our own runs:
- large-v3 sometimes inserts a word after a long pause; turbo drops fillers. A vote with the script or captions as
  the third source catches both.
- A word the ASR hears at a join is only a lead to review; the silence check at the join is the gate.
- Cloned narration drifts when stretched or batched. One sentence per request, one seed per beat, 0.4 s between
  sentences and 1.0 s between paragraphs gave 158 wpm, with 149 of 149 words heard back.
- The beat detector lags about 34 ms. Calibrate before judging cut timing.
- At 1920 px wide, text under about 36 px stops reading on a 390 px phone.
- The craft reel built from the breakdown: 10 of 10 cuts within 34 ms of its grid (median 8 ms); cuts by third 0, 1,
  9; a 3.4 s hold; -14.3 LUFS and -1.4 dBTP after the remux.
  [REPORT.md](../../examples/showreel-craft/qa/REPORT.md)

## Terms corrected in our transcript

Fable 5.1 (Anthropic) and GPT-6 Astra (OpenAI), HyperFrames, ElevenLabs, Claude Code, Skool, kie.ai, Kling,
motion-showreel, Kenn (Ejima), showreel.
