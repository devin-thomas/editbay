# Start with EditBay

In Claude Code, install the plugin. It adds the skills and the local Python tools:

```
claude plugin marketplace add devin-thomas/editbay
claude plugin install editbay@editbay
```

Start a new session and ask for the `video-director` skill.

In Codex, Cursor or another agent, connect `https://editbay.uppercut-labs.com/mcp` using Streamable HTTP. Call `get_skill` with `video-director`, or search for the step you need. Every skill is also an MCP prompt of the same name.

The hosted service returns text only: instructions, source documents and the Python scripts. It runs nothing. The skills name scripts as `$EB/tools/<name>.py`. Without the plugin, pick a folder for `$EB` (for example `~/editbay`), call `list_tools`, and save every script it lists in `$EB/tools`, because some call their siblings. Check each SHA-256, read what you are about to run, and run it locally with `uv run`. Keep your footage, credentials, brand profiles, voice references and generated runs in a separate local project.

Give the agent a goal, audience, source-media location, output format, and constraints. Ask it to write the brief and acceptance criteria before editing, then report evidence for each completed check.

The six tools are `list_skills`, `search_editbay`, `get_skill`, `read_document`, `list_tools`, and `get_tool`. Read all pages when `nextOffset` is present. The MCP cannot upload, render, record or publish for you.
