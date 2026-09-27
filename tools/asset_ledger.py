#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
"""Provenance for every asset an edit uses, and a gate that fails when something on screen has none.

Usage:
  asset_ledger.py add assets/ledger.json FILE --kind capture|official|stock|generated|own --source URL_OR_NOTE
                  [--license "..."] [--label "on-screen label"] [--prompt "..."] [--tool "..."] [--cost-usd 0.12]
                  [--source-file SOURCE] [--source-start SECONDS --source-end SECONDS]
  asset_ledger.py check assets/ledger.json --composition hf/   (every src/href under hf/ that points at a file has an entry;
                                                               generated and stock entries carry a licence; generated
                                                               entries carry an on-screen label or a reason)
  asset_ledger.py list assets/ledger.json
Kinds: capture (our own screenshot or recording of something), official (a brand's own logo or press asset), stock
(licensed library media), generated (made by a model: label it), own (made for this project: renders, synthesis).
Exit 1 when check finds a gap.
"""
import argparse, datetime, hashlib, json, os, re, sys

KINDS = ("capture", "official", "stock", "generated", "own")


def load(path):
    return json.load(open(path)) if os.path.exists(path) else {"assets": []}


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    ad = sub.add_parser("add"); ad.add_argument("ledger"); ad.add_argument("file")
    ad.add_argument("--kind", choices=KINDS, required=True); ad.add_argument("--source", required=True)
    ad.add_argument("--license", default=""); ad.add_argument("--label", default=""); ad.add_argument("--prompt", default="")
    ad.add_argument("--tool", default=""); ad.add_argument("--cost-usd", type=float, default=0.0); ad.add_argument("--note", default="")
    ad.add_argument("--source-file", default="", help="source recording for a clip segment")
    ad.add_argument("--source-start", type=float); ad.add_argument("--source-end", type=float)
    ck = sub.add_parser("check"); ck.add_argument("ledger"); ck.add_argument("--composition", required=True)
    ls = sub.add_parser("list"); ls.add_argument("ledger")
    a = ap.parse_args()
    led = load(a.ledger)
    if a.cmd == "add":
        if (a.source_start is None) != (a.source_end is None):
            raise SystemExit("asset_ledger: --source-start and --source-end must be supplied together")
        if a.source_file and a.source_start is None:
            raise SystemExit("asset_ledger: --source-file requires --source-start and --source-end")
        if a.source_start is not None and not a.source_file:
            raise SystemExit("asset_ledger: --source-file is required for a source segment")
        if a.source_start is not None and a.source_start >= a.source_end:
            raise SystemExit("asset_ledger: source segment end must be after its start")
        digest = sha(a.file)
        entry = {"file": os.path.basename(a.file), "sha256": digest, "sha256_16": digest[:16], "kind": a.kind, "source": a.source, "license": a.license,
                 "label": a.label, "prompt": a.prompt, "tool": a.tool, "cost_usd": a.cost_usd, "note": a.note,
                 "added": datetime.date.today().isoformat()}
        if a.source_file:
            entry["source_file"] = a.source_file
        if a.source_start is not None:
            entry["source_start"] = a.source_start
            entry["source_end"] = a.source_end
        led["assets"] = [e for e in led["assets"] if e["file"] != entry["file"]] + [entry]
        os.makedirs(os.path.dirname(os.path.abspath(a.ledger)), exist_ok=True)
        json.dump(led, open(a.ledger, "w"), indent=1)
        print(f"recorded {entry['file']} ({a.kind})")
    elif a.cmd == "list":
        for e in led["assets"]:
            print(f"{e['kind']:9} {e['file']:40} {e['license'] or '-':22} {e['source']}")
        print(f"{len(led['assets'])} assets; generation spend ${sum(e.get('cost_usd', 0) for e in led['assets']):.2f}")
    else:
        known = {e["file"]: e for e in led["assets"]}
        used, gaps = set(), []
        for root, _, files in os.walk(a.composition):
            if "node_modules" in root:
                continue
            for f in files:
                if f.endswith((".html", ".css")):
                    text = open(os.path.join(root, f), encoding="utf-8", errors="ignore").read()
                    for ref in re.findall(r'(?:src|href)="([^"#:]+)"|url\(["\']?([^"\')]+)["\']?\)', text):
                        ref = ref[0] or ref[1]
                        if ref and not ref.startswith(("http", "data:", "//")) and not ref.endswith((".html", ".css")):
                            used.add(os.path.basename(ref))
        for u in sorted(used):
            e = known.get(u)
            if not e:
                gaps.append(f"{u}: used in the composition, not in the ledger")
            elif e["kind"] in ("stock", "generated", "official") and not e["license"]:
                gaps.append(f"{u}: {e['kind']} asset without a licence or terms note")
            elif e["kind"] == "generated" and not (e["label"] or e["note"]):
                gaps.append(f"{u}: generated asset without an on-screen label or a reason for none")
        segments = []
        for entry in led["assets"]:
            if not entry.get("source_file") or entry.get("source_start") is None or entry.get("source_end") is None:
                continue
            try:
                start, end = float(entry["source_start"]), float(entry["source_end"])
            except (TypeError, ValueError):
                gaps.append(f"{entry.get('file', '?')}: source segment times must be numeric")
                continue
            if start >= end:
                gaps.append(f"{entry.get('file', '?')}: source segment end must be after start")
                continue
            segments.append((entry["source_file"], start, end, entry.get("file", "?")))
        for i, (source, start, end, file) in enumerate(segments):
            for other_source, other_start, other_end, other_file in segments[i + 1:]:
                if source != other_source or start >= other_end or other_start >= end:
                    continue
                relation = "duplicate source segment" if start == other_start and end == other_end else "overlapping source segments"
                gaps.append(f"{file} and {other_file}: {relation} in {source} ({max(start, other_start):g}-{min(end, other_end):g}s)")
        for g in gaps:
            print("GAP", g)
        print(f"{len(used)} assets used; {len(gaps)} gaps")
        sys.exit(1 if gaps else 0)


if __name__ == "__main__":
    main()
