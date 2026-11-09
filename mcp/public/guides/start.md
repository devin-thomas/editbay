# Start with EditBay

Connect your agent to `https://editbay.uppercut-labs.com/mcp` using Streamable HTTP. Call `get_skill` with `video-director`, or search for the step you need.

The hosted service returns instructions and source documents only. To edit media, install the public EditBay checkout locally and configure the tools required by your chosen workflow. Keep your footage, credentials, brand profiles, voice references and generated runs in a separate local project.

Give the agent a goal, audience, source-media location, output format, and constraints. Ask it to write the brief and acceptance criteria before editing, then report evidence for each completed check.

The four tools are `list_skills`, `search_editbay`, `get_skill`, and `read_document`. Read all pages when `nextOffset` is present. The MCP cannot upload, render, record or publish for you.
