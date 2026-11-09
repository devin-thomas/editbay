---
name: render-verify
description: Verify a rendered video before anyone watches it. Runs the automated gates (hyperframes check on the composition; spec, black, freeze, silence, pops, loudness, beat alignment, face keep-clear, and words on the encoded file), reads one overview sheet and a strip at every cut, repairs up to twice per finding, and writes qa/REPORT.md with evidence. Use after every render and before delivery, and whenever asked to check, QA, verify, proof, or review a video. The loop that turns a first draft into the fifth.
---

# Render verify

The first render is a draft. The agent watches its own output the way an editor would, fixes what it finds, and
only then hands it over, with a report that separates what passed from what was never checked.

Paths: `$EB` is the editbay root, the folder holding `skills/` and `tools/` (`../..` from this skill's folder). Tools run as `uv run $EB/tools/<tool>.py`.
Delivery profiles (size, fps, loudness) come from `~/.config/editbay/config.json`.

## 1. Gate the composition

Before rendering a HyperFrames project: `EDITBAY_HF_VERSION=<pin> uv run $EB/tools/hf.py check hf/ --json --snapshots --at-transitions --check-timeout 180` and
`uv run $EB/tools/text_check.py hf/ --brand BRAND.json`. Layout overlaps, contrast failures, runtime errors, text
under the brand's phone minimum, words split across lines, and `*.motion.json` assertions (entrances land by their
beat, order holds, nothing leaves frame, nothing freezes) are fixed in the HTML now; they are cheap here and
expensive after a render. Run HyperFrames only through `hf.py`: with a Gemini key set, `snapshot` and even
`check --snapshots` (which has no `--describe` flag) send frames to a vision API; hf.py removes the keys.

**Done when:** `check` exits 0, or each remaining finding is marked intentional in the HTML with its escape-hatch
attribute and a comment saying why.

## 2. Gate the file

```bash
uv run $EB/tools/verify_report.py --render renders/review.mp4 --out qa/ --profile reel --hf-project hf/ \
  --brand BRAND.json --expect-duration 15 --allow-black 0:0.3 --allow-freeze 13.5:15,40:44.5 \
  --grid beats/grid.json --half \                                   # music-led pieces
  --faces media/talk.faces.json --source media/talk.mp4 \           # footage under overlays
  --expected transcript/words.json --heard transcript/reconciled.words.json --heard-kind reconciled \
  --heard-patch transcript/final.corrections.md                    # voice or captions present
  --require-end-card --end-card-proof qa/end-card.json              # exact encoded tail, inspected as the end card
```

Each gate is PASS, FAIL, or PENDING (not run, with the reason). The av-qa gate also checks that the first and last
frames contain detail rather than only a smooth background. When `--require-end-card` is set, count the encoded frames,
inspect frame N-1 in `encoded-last-frame.png`, and require the proof record to name that file, mark it as the end card,
and repeat the exact voice disclosure; verify caption ink and opacity there because a nearby timed frame does not count.
Measure loudness on the encoded review/delivery file, not only the source WAV. If the local HyperFrames AAC path
reproducibly attenuates the mix, apply a measured source compensation, rerun the encoded loudness gate, and record both
measurements. After audio remux or packaging, rerun the frame and logo proofs on the copied delivery encode, not only
the HyperFrames intermediate. If an expected review artifact is absent, record it as not checked; never invent evidence.
What each gate proves and how to fix its common failures:
[references/gates.md](references/gates.md). `--allow-*` ranges must match the plan (a fade from black, a held end card);
never widen them to make a failure go away.

**Done when:** every applicable gate has run; PENDING remains only for gates that do not apply, with the reason.

## 3. Look

Read the overview sheet(s) and the cut strips in one go, at this phase boundary: an attached image re-prices the
whole context, so batch them. Inspect exact frame 0 and every persistent-shell hold after any source-chip or kicker
reflow, then render a phone-size preview (`ffmpeg -i review.mp4 -vf scale=390:-2 phone.mp4`) and read the smallest text
on its sheet. Write what you saw in the report's visual section: overview, cuts and transitions, shell collisions,
legibility at phone size, anything off-brand.

**Done when:** the visual section is filled in with specific timestamps, not impressions.

## 4. Repair, twice at most

For each finding: fix the cause (the plan, the HTML, the mix), re-render only what changed when possible, and re-run
the failing gate plus a strip around the fix. Log each pass in the report's Repairs table. After two passes on the
same finding, stop: add it to `HUMAN_QUEUE.md` with the timestamp, the evidence file, and what you tried.

**Done when:** every finding is fixed (gate re-run shows PASS) or queued for a human with evidence.

## 5. Hand over

The report leads with the verdict: automated gates, the visual read, repairs made, and anything pending or queued.
Say "not checked" for what was not checked. The render goes to delivery-pack only when no gate is FAIL.

**Done when:** `qa/REPORT.md` reads true on its own, and a reviewer could find every claim's evidence file.

## Checklist

- [ ] `hyperframes check` clean (or intentional findings marked) before the render
- [ ] `verify_report.py` run with every gate that applies; PENDING only where it does not
- [ ] Sheets and strips read once, in a batch; phone-size legibility checked
- [ ] At most two repair passes per finding; the rest queued with evidence
- [ ] Report states what was not checked
