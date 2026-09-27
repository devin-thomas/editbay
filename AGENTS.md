# editbay: agent notes

editbay is a Claude Code plugin and a Codex skill collection for agentic video editing on HyperFrames.
Design: [docs/DESIGN.md](docs/DESIGN.md). Paid services and their free/local alternatives: [docs/PROVIDERS.md](docs/PROVIDERS.md).

## Layout

- `skills/<name>/SKILL.md` (+ `agents/openai.yaml`, `references/`): one skill per step of the loop. SKILL.md stays under
  about 130 lines: a contract, numbered stages that end in **Done when:**, pointers to references, a checklist.
- `tools/*.py`: the measurements and generators the skills call. Each script declares its dependencies inline
  (PEP 723), so `uv run tools/x.py` works on macOS and Windows. Standard library where possible.
- `brands/`: brand profiles (JSON). Personal brands live in `~/.config/editbay/brands/`, not here.
- `config/config.example.json`: the shape of `~/.config/editbay/config.json` (machines, voices, credentials by
  variable name only, delivery profiles). Machine facts never go into skills.
- `examples/`: real runs with their records (briefs, beat sheets, reports). Media stays out of git.

## Rules

- Run `python3 scripts/validate.py` before committing; it must print PASS. Also `git diff --check`.
- No personal home paths, secrets, cookies, or tokens in any tracked file. Credentials are named, never stored.
- Every tool change is tested on a real input, with a negative control when the tool is a gate (a gate that
  cannot fail proves nothing). Record what was measured in the tool's docstring when it drives a default.
- Honest evidence: a check that did not run is "pending", never "passed"; generated media is labelled.
- Paid APIs are opt-in per run with a written estimate in the project's HUMAN_QUEUE.md; add any new provider you
  meet to docs/PROVIDERS.md with its cost, benefit, and the free/local alternative.
- editbay is the source of truth for these skills; `scripts/sync-private-skills.sh` copies them into
  devin-thomas/private-skills. Edit here, then sync.
