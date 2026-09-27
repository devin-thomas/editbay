#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
"""Provenance for every asset an edit uses, and a gate that fails when something on screen has none.

Usage:
  asset_ledger.py add assets/ledger.json FILE --kind capture|official|stock|generated|own --source URL_OR_NOTE
                  [--license "..."] [--label "on-screen label"] [--prompt "..."] [--tool "..."] [--cost-usd 0.12]
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
    return hashlib.sha256(open(path, "rb").read()).hexdigest()[:16]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    ad = sub.add_parser("add"); ad.add_argument("ledger"); ad.add_argument("file")
    ad.add_argument("--kind", choices=KINDS, required=True); ad.add_argument("--source", required=True)
    ad.add_argument("--license", default=""); ad.add_argument("--label", default=""); ad.add_argument("--prompt", default="")
    ad.add_argument("--tool", default=""); ad.add_argument("--cost-usd", type=float, default=0.0); ad.add_argument("--note", default="")
    ck = sub.add_parser("check"); ck.add_argument("ledger"); ck.add_argument("--composition", required=True)
    ls = sub.add_parser("list"); ls.add_argument("ledger")
    a = ap.parse_args()
    led = load(a.ledger)
    if a.cmd == "add":
        entry = {"file": os.path.basename(a.file), "sha256_16": sha(a.file), "kind": a.kind, "source": a.source, "license": a.license,
                 "label": a.label, "prompt": a.prompt, "tool": a.tool, "cost_usd": a.cost_usd, "note": a.note,
                 "added": datetime.date.today().isoformat()}
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
        for g in gaps:
            print("GAP", g)
        print(f"{len(used)} assets used; {len(gaps)} gaps")
        sys.exit(1 if gaps else 0)


if __name__ == "__main__":
    main()
