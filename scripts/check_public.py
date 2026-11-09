#!/usr/bin/env python3
"""Check the complete release tree, not only Markdown or the website's static assets."""
from __future__ import annotations
import argparse
import ast
import hashlib
import html
import json
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import unquote

SKIP = {".git", "node_modules", ".wrangler", "__pycache__", ".pytest_cache"}
GENERATED = {"mcp/dist", "mcp/src/generated"}
PATTERNS = {
    "home-path": r"(?:/Users/|/home/)[A-Za-z0-9_.-]+(?:[/\\]|\b)|[A-Za-z]:[/\\]+Users[/\\]+[A-Za-z0-9_.-]+",
    "private-network": r"\b(?:192\.168\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})\b",
    "private-key": r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----",
    "provider-token": r"\b(?:gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[0-9A-Z]{16}|sk-(?:proj-|ant-)?[A-Za-z0-9_-]{24,}|xox[baprs]-[A-Za-z0-9-]{20,})\b",
    "credential-url": r"\b(?:https?|postgres(?:ql)?|mysql)://[^\s/:]+:[^\s/@]+@",
    "jwt": r"\beyJ[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{12,}\b",
}
DENIED_NAMES = {".env", ".npmrc", ".pypirc", ".netrc", "id_rsa", "id_ed25519", "cookies.txt", "credentials.json"}


def normalize(text: str) -> str:
    for _ in range(3):
        text = html.unescape(unquote(text))
        text = re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m[1], 16)), text)
    return text


def findings(path: str, text: str) -> list[str]:
    normalized = normalize(text)
    return [f"{path}: {name}" for name, pattern in PATTERNS.items() if re.search(pattern, normalized)]


def scan(root: Path, verify_manifest: bool = False) -> tuple[int, list[str]]:
    errors, blobs = [], {}
    for p in sorted(root.rglob("*")):
        rel = p.relative_to(root).as_posix()
        if any(part in SKIP for part in p.relative_to(root).parts) or any(rel == x or rel.startswith(x + "/") for x in GENERATED):
            continue
        if p.is_symlink():
            errors.append(f"{rel}: symlink")
            continue
        if not p.is_file():
            continue
        if p.name in DENIED_NAMES or (p.name.startswith(".env.") and p.name != ".env.example"):
            errors.append(f"{rel}: credential-file")
        if any(x in {"publication", "private", "productions", "receipts"} for x in p.relative_to(root).parts):
            errors.append(f"{rel}: private-directory")
        data = p.read_bytes()
        blobs[rel] = hashlib.sha256(data).hexdigest()
        try:
            if b"\0" in data:
                raise ValueError("NUL")
            text = data.decode("utf-8", "strict")
        except (UnicodeError, ValueError):
            errors.append(f"{rel}: unreviewed-binary")
            continue
        errors.extend(findings(rel, text))
        try:
            if rel.endswith(".json"):
                json.loads(text)
            if rel.endswith(".py"):
                ast.parse(text, filename=rel)
        except (ValueError, SyntaxError) as exc:
            errors.append(f"{rel}: parse-error {type(exc).__name__}")
    marker = root / "PUBLIC_RELEASE.json"
    if not marker.is_file():
        errors.append("Missing PUBLIC_RELEASE.json; refuse to publish an unprepared checkout")
    elif verify_manifest:
        try:
            recorded = json.loads(marker.read_text())["files"]
            actual = {p: h for p, h in blobs.items() if p != "PUBLIC_RELEASE.json"}
            for path in sorted(set(recorded) | set(actual)):
                if recorded.get(path) != actual.get(path):
                    errors.append(f"{path}: release-manifest-mismatch")
        except (ValueError, KeyError, TypeError):
            errors.append("Invalid release manifest")
    return len(blobs), errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--verify-manifest", action="store_true")
    args = parser.parse_args()
    count, errors = scan(args.root.resolve(), args.verify_manifest)
    for error in errors:
        print(error, file=sys.stderr)  # Do not print matched secrets or file excerpts.
    if errors:
        return 1
    print(f"PASS: {count} public text files; paths, credentials, syntax and release boundary")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
