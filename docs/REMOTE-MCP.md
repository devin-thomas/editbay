# Hosted guidance, local execution

The showcase and hosted guidance service share `https://editbay.uppercut-labs.com`. Connect to `/mcp` using Streamable HTTP. No sign-in or API key is required for this read-only documentation service.

Use `list_skills`, `search_editbay`, `get_skill`, and `read_document`. Follow pagination until `nextOffset` is null. Document responses include the public source revision and SHA-256. Resource reads expose the same approved corpus.

The service has no media upload, local file access, shell, SSH, rendering, model invocation, provider credentials, or user-data storage. Those operations remain local. A hosted documentation response is not proof that a local editing operation has run.

Only paths explicitly listed in `mcp/public-documents.json` are served. A newly added Markdown file is not automatically public through the MCP. `/health` reports the public revision; `/docs/<repository-relative-path>` serves the corresponding source document. Configuration, executable tools, examples, and contributor instructions are not published as MCP resources.

See [the server README](../mcp/README.md) for build and deployment checks.
