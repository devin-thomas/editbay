#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
"""Run the HyperFrames CLI at the pinned version with every paid-service key removed from its environment.

Why: HyperFrames 0.8.79 reads GEMINI_API_KEY or GOOGLE_API_KEY and, when one is set, sends frames to Gemini from
`snapshot` and from `check --snapshots`. `check` has no --describe flag to turn that off (probed 2026-09-26), and a
Codex run once dropped `--describe false` after `check` rejected it. The CLI also reads HeyGen, HyperFrames cloud,
OpenRouter and ElevenLabs keys. Removing the keys makes every paid path impossible instead of relying on a flag.

Usage:
  hf.py check hf/ --json --at-transitions
  hf.py snapshot hf/ --at 1.2,4.8          (--describe false is added when absent)
  hf.py render --fps 60 --quality high -o ../renders/review.mp4     (run from inside the project, as with npx)
  hf.py --allow-paid snapshot hf/ --describe "Is the logo visible?"  (keeps the keys: only with the creator's approval
                                                                      and an estimate in HUMAN_QUEUE.md)
  hf.py --dry-run snapshot hf/ --at 1       (print the command and the keys that would be removed; run nothing)
Version: EDITBAY_HF_VERSION or 0.8.79. Exit code is the CLI's.
"""
import os, subprocess, sys

VERSION = os.environ.get("EDITBAY_HF_VERSION", "0.8.79")
PAID_KEYS = ("GEMINI_API_KEY", "GOOGLE_API_KEY", "HYPERFRAMES_API_KEY", "HEYGEN_API_KEY", "OPENROUTER_API_KEY",
             "ELEVENLABS_API_KEY", "OPENAI_API_KEY", "KIE_API_KEY", "FISH_AUDIO_API_KEY")


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__); return 0
    allow_paid = "--allow-paid" in args
    dry = "--dry-run" in args
    args = [x for x in args if x not in ("--allow-paid", "--dry-run")]
    if args and args[0] == "snapshot" and "--describe" not in args and not allow_paid:
        args += ["--describe", "false"]
    env = dict(os.environ)
    removed = [] if allow_paid else [k for k in PAID_KEYS if k in env]
    for k in removed:
        env.pop(k)
    cmd = ["npx", "--yes", f"hyperframes@{VERSION}", *args]
    if allow_paid:
        print("hf.py: --allow-paid keeps paid-service keys; this run may call paid APIs", file=sys.stderr)
    if dry:
        print(" ".join(cmd)); print("removed from env:", ", ".join(removed) or "none (no paid keys set)")
        return 0
    return subprocess.run(cmd, env=env).returncode


if __name__ == "__main__":
    sys.exit(main())
