#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
"""Run the HyperFrames CLI at the pinned version with paid-service keys removed.

Why: HyperFrames 0.8.79 reads GEMINI_API_KEY or GOOGLE_API_KEY and, when one is set, sends frames to Gemini from
`snapshot` and from `check --snapshots`. `check` has no --describe flag to turn that off (probed 2026-09-26), and a
Codex run once dropped `--describe false` after `check` rejected it. The CLI also reads HeyGen, HyperFrames cloud,
OpenRouter and ElevenLabs keys. Removing the keys makes every paid path impossible instead of relying on a flag.

Usage:
  hf.py check hf/ --json --at-transitions [--check-timeout 180]
  hf.py snapshot hf/ --at 1.2,4.8          (--describe false is added when absent)
  hf.py render --fps 60 --quality high -o ../renders/review.mp4     (run from inside the project, as with npx)
  hf.py render --resolution landscape-4k ...  (prints disk preflight; auto workers fall back to one when needed)
  hf.py --allow-paid snapshot hf/ --describe "Is the logo visible?"  (keeps the keys: only with the creator's approval
                                                                        and an estimate in HUMAN_QUEUE.md)
  hf.py --dry-run snapshot hf/ --at 1       (print the command and the keys that would be removed; run nothing)
Version: EDITBAY_HF_VERSION or 0.8.79. Exit code is the CLI's; a timed-out check exits 124 and reports PENDING JSON.
"""
import json
import os
import re
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile

VERSION = os.environ.get("EDITBAY_HF_VERSION", "0.8.79")
PAID_KEYS = ("GEMINI_API_KEY", "GOOGLE_API_KEY", "HYPERFRAMES_API_KEY", "HEYGEN_API_KEY", "OPENROUTER_API_KEY",
             "ELEVENLABS_API_KEY", "OPENAI_API_KEY", "KIE_API_KEY", "FISH_AUDIO_API_KEY")
FOUR_K_RESOLUTIONS = {"4k", "landscape-4k", "portrait-4k", "uhd"}
FRAME_BYTES_PER_PIXEL = 0.125  # conservative HyperFrames temporary-frame estimate, calibrated against the 11.6 GB run
ESTIMATE_HEADROOM = 1.15


def option_value(args, name):
    for i, value in enumerate(args):
        if value == name and i + 1 < len(args):
            return args[i + 1]
        if value.startswith(name + "="):
            return value.split("=", 1)[1]
    return None


def project_dir(args):
    """Find a render project's index.html, or use the caller's project directory."""
    skip_next = False
    for value in args[1:]:
        if skip_next:
            skip_next = False
            continue
        if value in ("--fps", "--quality", "--resolution", "--workers", "-o", "--output"):
            skip_next = True
            continue
        if value.startswith("-"):
            continue
        if os.path.isdir(value) and os.path.isfile(os.path.join(value, "index.html")):
            return os.path.abspath(value)
    return os.getcwd()


def render_preflight(args):
    """Return adjusted render args and a human-readable disk preflight."""
    if not args or args[0] != "render":
        return args, []
    resolution = (option_value(args, "--resolution") or "").lower()
    if resolution not in FOUR_K_RESOLUTIONS:
        return args, []
    dims = (2160, 3840) if "portrait" in resolution else (3840, 2160)
    project = project_dir(args)
    index = os.path.join(project, "index.html")
    duration = None
    fps = option_value(args, "--fps")
    if os.path.isfile(index):
        source = open(index, encoding="utf-8", errors="ignore").read()
        match = re.search(r'data-duration=["\']([0-9]+(?:\.[0-9]+)?)["\']', source)
        if match:
            duration = float(match.group(1))
        if fps is None:
            match = re.search(r'data-fps=["\']([0-9]+(?:\.[0-9]+)?)["\']', source)
            if match:
                fps = match.group(1)
    fps_value = float(fps or 60)
    free = shutil.disk_usage(tempfile.gettempdir()).free
    lines = [f"hf.py 4K disk preflight: project={project} resolution={dims[0]}x{dims[1]} free={free / 1024**3:.2f} GiB"]
    if duration is None:
        lines.append("hf.py 4K disk preflight: duration unavailable; cannot estimate temporary frames; use --workers 1")
        return args, lines
    frame_count = max(1, round(duration * fps_value))
    one_worker = frame_count * dims[0] * dims[1] * FRAME_BYTES_PER_PIXEL
    workers_value = option_value(args, "--workers")
    workers = 4 if not workers_value or workers_value.lower() == "auto" else int(workers_value)
    multi_worker = one_worker * max(workers, 1)
    threshold = multi_worker * ESTIMATE_HEADROOM
    lines.append(f"hf.py 4K disk preflight: {duration:g}s @ {fps_value:g} fps = {frame_count} frames; "
                 f"one-worker estimate={one_worker / 1024**3:.2f} GiB; multi-worker estimate="
                 f"{multi_worker / 1024**3:.2f} GiB ({workers} workers); headroom threshold={threshold / 1024**3:.2f} GiB")
    adjusted = list(args)
    if free < threshold and (not workers_value or workers_value.lower() == "auto"):
        adjusted += ["--workers", "1"]
        lines.append("hf.py 4K disk preflight: recommendation=--workers 1 (appended; multi-worker estimate is too close to free disk)")
    elif free < threshold and workers > 1:
        lines.append("hf.py 4K disk preflight: WARNING explicit worker count may exceed free disk; choose --workers 1")
    else:
        lines.append(f"hf.py 4K disk preflight: recommendation=--workers {workers}")
    if free < one_worker * ESTIMATE_HEADROOM:
        lines.append("hf.py 4K disk preflight: WARNING even the one-worker estimate is close to or above free disk")
    return adjusted, lines


def phase_from(output):
    phases = []
    for line in output.splitlines():
        lower = line.lower()
        for phase in ("lint", "runtime", "layout", "contrast", "motion", "browser"):
            if phase in lower:
                phases.append(phase)
    return phases[-1] if phases else "browser-child"


def child_command(output):
    for line in reversed(output.splitlines()):
        line = line.strip()
        lower = line.lower()
        if line and any(token in lower for token in ("node", "playwright", "chrom", "browser")):
            return line
    return "unknown child command (see child_output_tail)"


def timeout_seconds(args):
    value = option_value(args, "--check-timeout") or os.environ.get("EDITBAY_HF_CHECK_TIMEOUT", "180")
    try:
        result = float(value)
    except ValueError as exc:
        raise SystemExit(f"hf.py: invalid check timeout {value!r}; use seconds") from exc
    if result <= 0:
        raise SystemExit("hf.py: --check-timeout must be greater than zero")
    return result


def run_check(cmd, env, args):
    timeout = timeout_seconds(args)
    proc = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                            start_new_session=True)
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        partial_out = exc.stdout or ""
        partial_err = exc.stderr or ""
        if isinstance(partial_out, bytes):
            partial_out = partial_out.decode(errors="replace")
        if isinstance(partial_err, bytes):
            partial_err = partial_err.decode(errors="replace")
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait()
        combined = (partial_out + "\n" + partial_err).strip()
        payload = {"ok": False, "status": "PENDING", "phase": phase_from(combined),
                   "command": cmd, "timeout_s": timeout,
                   "child_command": child_command(combined),
                   "detail": "HyperFrames check exceeded its bounded timeout; inspect and rerun after the browser child is fixed",
                   "child_output_tail": combined[-2000:]}
        print(json.dumps(payload))
        print(f"hf.py: check timeout after {timeout:g}s; phase={payload['phase']}; child={payload['child_command']}", file=sys.stderr)
        return 124
    if out:
        sys.stdout.write(out)
    if err:
        sys.stderr.write(err)
    return proc.returncode


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    allow_paid = "--allow-paid" in args
    dry = "--dry-run" in args
    check_timeout = None
    cleaned = []
    i = 0
    while i < len(args):
        value = args[i]
        if value == "--check-timeout":
            if i + 1 >= len(args):
                raise SystemExit("hf.py: --check-timeout needs seconds")
            check_timeout = args[i + 1]
            i += 2
            continue
        if value.startswith("--check-timeout="):
            check_timeout = value.split("=", 1)[1]
            i += 1
            continue
        if value not in ("--allow-paid", "--dry-run"):
            cleaned.append(value)
        i += 1
    args = cleaned
    if check_timeout is not None:
        os.environ["EDITBAY_HF_CHECK_TIMEOUT"] = check_timeout
    if args and args[0] == "snapshot" and "--describe" not in args and not allow_paid:
        args += ["--describe", "false"]
    args, preflight = render_preflight(args)
    for line in preflight:
        print(line, file=sys.stderr)
    env = dict(os.environ)
    removed = [] if allow_paid else [k for k in PAID_KEYS if k in env]
    for key in removed:
        env.pop(key)
    cmd = ["npx", "--yes", f"hyperframes@{VERSION}", *args]
    if allow_paid:
        print("hf.py: --allow-paid keeps paid-service keys; this run may call paid APIs", file=sys.stderr)
    if dry:
        print(" ".join(shlex.quote(x) for x in cmd))
        print("removed from env:", ", ".join(removed) or "none (no paid keys set)")
        return 0
    if args and args[0] == "check":
        return run_check(cmd, env, args)
    return subprocess.run(cmd, env=env).returncode


if __name__ == "__main__":
    sys.exit(main())
