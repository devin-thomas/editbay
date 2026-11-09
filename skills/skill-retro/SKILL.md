---
name: skill-retro
description: Fold what a run taught back into the skills that ran it. Collects the creator's feedback (liked, disliked, with timestamps), QA findings and repairs, and anything the creator had to repeat, decides which skill, style, brand profile, or config owns each lesson, makes the change as a rule with a number, logs it, and validates. Use after an edit is delivered or reviewed, when feedback arrives on a render, or when the same instruction has been given twice.
---

# Skill retro

A skill improves only when someone writes the lesson into it. If the creator had to say it twice, the second time
belongs in a skill; if QA had to fix it twice, the first fix belongs upstream.

Paths: `$EB` is the editbay root, the folder holding `skills/` and `tools/` (`../..` from this skill's folder).

## 1. Collect

Gather into `RETRO.md` (format: [references/retro-format.md](references/retro-format.md)):
- the creator's notes, each tied to a timestamp or a file;
- QA findings and repairs from `qa/REPORT.md`, with which pass fixed them;
- instructions that appeared in more than one prompt or brief;
- anything slow, flaky, or surprising in the tools (with the measurement).

**Done when:** every note, finding, repeat, and surprise from the run is a row with its evidence.

## 2. Decide where each lesson lives

| Lesson is about | Owner |
|---|---|
| one brand's look, voice, or forbidden devices | the brand profile (`~/.config/editbay/brands/`) |
| a style's grammar or taste | the style skill (`skills/style-*`) and its feedback log |
| how a step is done (cut, beats, build, verify) | that editbay skill or its reference file |
| a tool's default or a bug | the tool, with a test on a real input and a negative control |
| a machine, path, or provider | the config (never a skill) |
| one project only | the project's brief; not a skill |

**Done when:** each row names exactly one owner, or "project only".

## 3. Change the owner

If the lesson is mechanical or checkable and has already been written down once (it recurred), make it a tool or a gate
with a negative control instead of more text; leave judgement calls as rules. Otherwise, write each lesson as a rule with a number or an example ("hold step cards until the next step's first word; no empty
frames between steps"), not a mood ("better pacing"). Positive phrasing first; a prohibition only as a guardrail next
to its positive target. Add a dated line to the owner's changelog or feedback log. Keep SKILL.md short: detail goes in
its references.

**Done when:** every lesson is in its owner, logged, and `python3 $EB/scripts/validate.py` prints PASS.

## 4. Prove the change

When it is cheap, re-run the step the lesson touched on the same inputs and show the difference (a sheet, a number).
When it is not, add the lesson to the next run's brief as a check. If you keep local copies or overrides of these
skills, update them after changing an editbay file.

**Done when:** each change is either demonstrated or scheduled as a check in the next brief.

## Checklist

- [ ] Feedback, findings, repeats, and surprises collected with evidence
- [ ] One owner per lesson
- [ ] Rules with numbers, logged, validated
- [ ] Changes demonstrated or scheduled; local copies updated
