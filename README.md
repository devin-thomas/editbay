# EditBay

Video-editing skills and local tools for coding agents. Turn a brief into a timed edit, verify the delivered file, and keep the evidence beside the work.

[Showcase](https://editbay.uppercut-labs.com) · [Hosted MCP](https://editbay.uppercut-labs.com/mcp) · [MCP setup](mcp/README.md)

## Start with your agent

Connect the read-only hosted MCP, then ask for `video-director`. It serves skills and runbooks; it does not accept media, access your computer, or perform edits remotely.

```json
{"mcpServers":{"editbay":{"url":"https://editbay.uppercut-labs.com/mcp"}}}
```

For local editing, install this checkout as a Claude Code plugin or link its `skills/` folders into your Codex skills installation:

```bash
claude plugin marketplace add devin-thomas/editbay
claude plugin install editbay@editbay
```

The Python tools declare dependencies inline. Run them with `uv run tools/<tool>.py --help`; configure only the engines and providers you intend to use. Copy [the example configuration](config/config.example.json) to your local configuration directory and replace placeholder paths before running remote jobs. No credentials or personal voice assets are included.

## The editing loop

Brief → intake → transcript → rough cut → beat sheet → motion and sound → verification → delivery.

The collection also includes reference-to-style, app capture, narration, music-promo patterns, and a retrospective workflow. [Design](docs/DESIGN.md) describes the file contracts. [Provider guidance](docs/PROVIDERS.md) explains local and opt-in paid routes.

The showcase's timeline is an illustrative, synthetic composition—not a recording of an editor, a rendered deliverable, or evidence of a completed production. [Examples](docs/EXAMPLES.md) explains how to make a neutral first project.

## Release checks

```bash
python3 scripts/check_public.py --verify-manifest
python3 scripts/validate.py
cd mcp
npm ci
npm run check
```

Node 24+ is required for the hosted-service checks. Python 3.10+, Git, and the dependencies required by each chosen local tool are separate prerequisites. Successful website/MCP checks do not establish that media rendering, ASR, narration, or GPU workflows work on a particular machine.

EditBay is licensed under the [Apache License 2.0](LICENSE).
