# Hosted guidance, local execution

The showcase and hosted guidance service share `https://editbay.uppercut-labs.com`. Connect to `/mcp` using Streamable HTTP. No sign-in or API key is required for this read-only documentation service.

Use `list_skills`, `search_editbay`, `get_skill`, `read_document`, `list_tools`, and `get_tool`. Every skill is also an MCP prompt of the same name (in clients that list prompts, such as Claude Code's `/mcp__editbay__rough-cut`), with an optional `task` argument, and the server instructions name every skill so an agent can route a request to one without being told to look. Follow pagination until `nextOffset` is null. Document responses include the public source revision and SHA-256. Resource reads expose the same approved corpus.

`list_tools` and `get_tool` serve the Python scripts in `tools/` as source text with their SHA-256 and source revision. Nothing runs on the server. A caller saves the scripts together in `$EB/tools` (some call their siblings), verifies each hash, reads the code before running it, and runs it locally with `uv run`. Fetched code runs with the caller's own permissions, so the revision and hash are what to pin and audit.

The service has no media upload, local file access, shell, SSH, rendering, model invocation, provider credentials, or user-data storage. Those operations remain local. A hosted documentation response is not proof that a local editing operation has run.

Only paths explicitly listed in `mcp/public-documents.json` are served. A newly added Markdown file is not automatically public through the MCP. `/health` reports the public revision; `/docs/<repository-relative-path>` serves the corresponding source document. Configuration, examples, contributor instructions, and any file in `tools/` that is not a `.py` script are not published as MCP resources.

See [the server README](../mcp/README.md) for build and deployment checks.
