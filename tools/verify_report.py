#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
"""Run every automated gate on a render and write qa/REPORT.md. A gate that did not run is PENDING, never PASS.

Usage:
  verify_report.py --render renders/review.mp4 --out qa/ [--profile reel] [--config ~/.config/editbay/config.json]
      [--expect-duration 15] [--allow-black 0:0.3] [--allow-freeze 12.0:15.5,40.2:44.0]   (comma-separated start:end ranges)
      [--hf-project hf/]                         hyperframes check (DOM: layout, contrast, motion sidecars), through hf.py
      [--brand BRAND.json]                       with --hf-project: text_check.py (phone-size text, words split across lines)
      [--grid beats/grid.json --half]            cuts on the beat grid (music-led pieces)
      [--faces media/x.faces.json --source SRC [--face-mode diff|detect] [--face-offset 0] [--face-skip a-b,...]]
      [--expected words.json --heard heard.json] words on screen / in the mix vs what should be there
      [--sheet-every 0.5]                        overview sheet interval (default: 0.5 s under 60 s, else 5 s)
Profiles come from the config's delivery_profiles (size, fps, lufs, true_peak). The av-qa gate also checks the first
and last video frames for background-only emptiness. Exit 1 when any gate fails.
"""
import argparse, datetime, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))


def tool(name, *args, uv=True):
    cmd = (["uv", "run", "-q", os.path.join(HERE, name)] if uv else ["python3", os.path.join(HERE, name)]) + [str(x) for x in args]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode, (r.stdout + r.stderr).strip()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--render", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--profile"); ap.add_argument("--config", default=os.path.expanduser("~/.config/editbay/config.json"))
    ap.add_argument("--expect-duration", type=float); ap.add_argument("--allow-black")
    ap.add_argument("--allow-freeze", help="intentional holds as comma-separated start:end ranges, e.g. 12:15,40:44.5")
    ap.add_argument("--brand", help="brand profile JSON: gates on-screen text against its phone minimum")
    ap.add_argument("--hf-project"); ap.add_argument("--grid"); ap.add_argument("--half", action="store_true")
    ap.add_argument("--tolerance-ms", type=float)
    ap.add_argument("--faces"); ap.add_argument("--source"); ap.add_argument("--face-mode", default="diff")
    ap.add_argument("--face-offset", type=float, default=0.0); ap.add_argument("--face-skip", default="")
    ap.add_argument("--expected"); ap.add_argument("--heard"); ap.add_argument("--sheet-every", type=float)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    prof = {}
    if a.profile and os.path.exists(a.config):
        prof = json.load(open(a.config)).get("delivery_profiles", {}).get(a.profile, {})
    gates, evidence = [], []

    def gate(name, code, text, path=None):
        status = "PASS" if code == 0 else "FAIL"
        gates.append({"gate": name, "status": status, "detail": text.splitlines()[-1] if text else ""})
        if path:
            evidence.append(path)
        open(os.path.join(a.out, f"{name}.log"), "w").write(text + "\n")

    # 1. Composition (DOM)
    if a.hf_project:
        r = subprocess.run(["uv", "run", "-q", os.path.join(HERE, "hf.py"), "check", a.hf_project, "--json"],
                           capture_output=True, text=True)
        try:
            d = json.loads(r.stdout)
            summary = ", ".join(f"{k} {'ok' if v.get('ok') else 'FAIL'}" for k, v in d.items()
                                if isinstance(v, dict) and "ok" in v)
            open(os.path.join(a.out, "hyperframes-check.json"), "w").write(r.stdout)
            gate("hyperframes-check", 0 if d.get("ok") else 1, summary, os.path.join(a.out, "hyperframes-check.json"))
        except json.JSONDecodeError:
            gate("hyperframes-check", 1, (r.stdout + r.stderr)[-2000:])
    else:
        gates.append({"gate": "hyperframes-check", "status": "PENDING", "detail": "no --hf-project given"})
    if a.hf_project and a.brand:
        gate("text", *tool("text_check.py", a.hf_project, "--brand", a.brand, "--json", os.path.join(a.out, "text.json")),
             os.path.join(a.out, "text.json"))
    else:
        gates.append({"gate": "text", "status": "PENDING", "detail": "no --hf-project/--brand: phone-size text not checked"})

    # 2. Encoded file
    args = [a.render, "--json", os.path.join(a.out, "av_qa.json")]
    if prof.get("fps"):
        args += ["--expect-fps", prof["fps"]]
    if prof.get("size"):
        args += ["--expect-size", prof["size"]]
    if a.expect_duration:
        args += ["--expect-duration", a.expect_duration]
    if a.allow_black:
        args += ["--allow-black", a.allow_black]
    if a.allow_freeze:
        args += ["--allow-freeze", a.allow_freeze]
    args += ["--require-content-ends"]
    gate("av-qa", *tool("av_qa.py", *args), os.path.join(a.out, "av_qa.json"))
    lu = ["--target", prof["lufs"], "--tp", prof.get("true_peak", -1.0)] if prof.get("lufs") is not None else []
    gate("loudness", *tool("loudness.py", a.render, *lu, "--json", os.path.join(a.out, "loudness.json"), uv=False),
         os.path.join(a.out, "loudness.json"))

    # 3. Beat grid
    if a.grid:
        cuts = os.path.join(a.out, "cuts.json")
        tool("scene_cuts.py", a.render, "--json", cuts, uv=False)
        tol = a.tolerance_ms or (1000 / prof["fps"] if prof.get("fps") else 17)
        gate("beat-align", *tool("beat_grid.py", "align", "--cuts", cuts, "--beats", a.grid, "--tolerance-ms", round(tol, 1),
                                 *(["--half"] if a.half else [])), cuts)
    else:
        gates.append({"gate": "beat-align", "status": "PENDING", "detail": "no --grid (not music-led, or not given)"})

    # 4. Face keep-clear
    if a.faces and a.source:
        gate("face-clear", *tool("face_clear.py", "--source", a.source, "--render", a.render, "--faces", a.faces,
                                 "--mode", a.face_mode, "--offset", a.face_offset, "--skip", a.face_skip,
                                 "--json", os.path.join(a.out, "face_clear.json")), os.path.join(a.out, "face_clear.json"))
    else:
        gates.append({"gate": "face-clear", "status": "PENDING", "detail": "no --faces/--source (no talking head?)"})

    # 5. Words
    if a.expected and a.heard:
        gate("words", *tool("transcript_diff.py", a.expected, a.heard, "--json", os.path.join(a.out, "words.json")),
             os.path.join(a.out, "words.json"))
    else:
        gates.append({"gate": "words", "status": "PENDING", "detail": "no --expected/--heard"})

    # 6. Sheets for the visual gate
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", a.render],
                               capture_output=True, text=True).stdout)
    every = a.sheet_every or (0.5 if dur <= 60 else 5.0)
    _, sheets = tool("contact_sheet.py", a.render, "--every", every, "--out", os.path.join(a.out, "overview"))
    cuts_json = os.path.join(a.out, "cuts.json")
    if not os.path.exists(cuts_json):
        tool("scene_cuts.py", a.render, "--json", cuts_json, uv=False)
    strips = ""
    if json.load(open(cuts_json))["cuts"]:
        _, strips = tool("contact_sheet.py", a.render, "--cuts", cuts_json, "--rows", 6, "--width", 320,
                         "--out", os.path.join(a.out, "strips"))
    sheet_files = [l for l in (sheets + "\n" + strips).splitlines() if l.endswith(".jpg")]
    gates.append({"gate": "visual", "status": "PENDING",
                  "detail": f"read {len(sheet_files)} sheet(s) at this phase boundary and record what you saw below"})

    failed = [g for g in gates if g["status"] == "FAIL"]
    lines = [f"# QA report: {os.path.basename(a.render)}", "",
             f"- when: {datetime.datetime.now().isoformat(timespec='seconds')}",
             f"- profile: {a.profile or 'none'} {json.dumps(prof) if prof else ''}",
             f"- verdict: **{'FAIL' if failed else 'automated gates pass'}**; the visual gate needs a reader", "",
             "| gate | status | detail |", "|---|---|---|"]
    lines += [f"| {g['gate']} | {g['status']} | {g['detail'].replace('|', '/')} |" for g in gates]
    lines += ["", "## Evidence", ""] + [f"- {os.path.relpath(p, a.out)}" for p in evidence + sheet_files]
    lines += ["", "## Visual gate (fill in after reading the sheets)", "", "- overview:", "- cuts and transitions:",
              "- text legibility at phone size:", "", "## Repairs", "", "| # | finding | fix | pass |", "|---|---|---|---|", ""]
    open(os.path.join(a.out, "REPORT.md"), "w").write("\n".join(lines))
    json.dump({"render": a.render, "gates": gates, "evidence": evidence, "sheets": sheet_files},
              open(os.path.join(a.out, "report.json"), "w"), indent=1)
    for g in gates:
        print(f"{g['status']:8} {g['gate']:18} {g['detail']}")
    print(f"report: {os.path.join(a.out, 'REPORT.md')}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
