#!/usr/bin/env python3
"""Validate the editbay plugin without dependencies.

Checks: SKILL.md frontmatter (name == folder, description present), entry points under 500 lines, a Codex
interface file per skill, plugin.json lists exactly the skill folders, every `tools/*.py` a skill names exists,
JSON files parse, local Markdown links resolve, and no Markdown leaks a personal home path.
Exit 0 = pass, 1 = findings.
"""
from pathlib import Path
import json
import re
import sys
from urllib.parse import unquote, urlsplit

root = Path(__file__).resolve().parents[1]
errors, warnings = [], []
skills = sorted(root.glob("skills/*/SKILL.md"))

for entry in skills:
    rel = entry.relative_to(root)
    text = entry.read_text()
    m = re.match(r"\A---\n(.*?)\n---\n", text, re.S)
    if not m:
        errors.append(f"{rel}: missing frontmatter"); continue
    fields = m.group(1)
    if not re.search(rf"^name: {re.escape(entry.parent.name)}$", fields, re.M):
        errors.append(f"{rel}: folder/name mismatch")
    if not re.search(r"^description: .+", fields, re.M):
        errors.append(f"{rel}: missing description")
    lines = len(text.splitlines())
    if lines >= 500:
        errors.append(f"{rel}: {lines} lines; entry point needs progressive disclosure")
    elif lines > 200:
        warnings.append(f"{rel}: {lines} lines; consider moving detail into references/")
    yaml = entry.parent / "agents" / "openai.yaml"
    if not yaml.exists():
        errors.append(f"{rel}: missing agents/openai.yaml (Codex interface)")
    else:
        y = yaml.read_text()
        for key in ("display_name:", "short_description:", "default_prompt:"):
            if key not in y:
                errors.append(f"{yaml.relative_to(root)}: missing {key}")
        # Codex lists skills installed with the editbay tree as editbay:<skill>, so prompts mention that name.
        if f"$editbay:{entry.parent.name}" not in y:
            errors.append(f"{yaml.relative_to(root)}: default_prompt should mention $editbay:{entry.parent.name}")
    for tool in set(re.findall(r"tools/([\w\-]+\.py)", text)):
        if not (root / "tools" / tool).exists():
            errors.append(f"{rel}: names tools/{tool}, which does not exist")
    for script in set(re.findall(r"(?<![\w/])scripts/([\w\-]+\.(?:py|mjs|ps1|sh))", text)):
        if not (entry.parent / "scripts" / script).exists() and not (root / "scripts" / script).exists():
            errors.append(f"{rel}: names scripts/{script}, which does not exist")

plugin = root / ".claude-plugin" / "plugin.json"
if plugin.exists():
    listed = {Path(p).name for p in json.loads(plugin.read_text()).get("skills", [])}
    folders = {e.parent.name for e in skills}
    for missing in sorted(folders - listed):
        errors.append(f"plugin.json: skill folder {missing} not listed")
    for extra in sorted(listed - folders):
        errors.append(f"plugin.json: lists {extra}, which has no SKILL.md")
else:
    errors.append(".claude-plugin/plugin.json missing")

for doc in sorted(root.rglob("*.json")):
    if any(p in doc.parts for p in (".git", "node_modules")):
        continue
    try:
        json.loads(doc.read_text())
    except json.JSONDecodeError as e:
        errors.append(f"{doc.relative_to(root)}: invalid JSON ({e})")

for doc in sorted(root.rglob("*.md")):
    if any(p in doc.parts for p in (".git", "node_modules")):
        continue
    text = doc.read_text()
    if re.search(r"/Users/[^/\s]+/|/home/[^/\s]+/|C:\\\\Users\\\\[^\\\\\s]+\\\\", text):
        errors.append(f"{doc.relative_to(root)}: machine-specific home path")
    for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", text):
        parsed = urlsplit(target.strip("<>"))
        if parsed.scheme or not parsed.path:
            continue
        if not (doc.parent / unquote(parsed.path)).exists():
            errors.append(f"{doc.relative_to(root)}: missing link {target}")

for w in warnings:
    print("warn:", w, file=sys.stderr)
for e in errors:
    print(e, file=sys.stderr)
if errors:
    sys.exit(1)
print(f"PASS: {len(skills)} skills; frontmatter, Codex interfaces, plugin list, tools, JSON, links, home paths")
