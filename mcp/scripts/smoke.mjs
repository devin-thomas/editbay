import assert from "node:assert/strict";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StreamableHTTPClientTransport } from "@modelcontextprotocol/sdk/client/streamableHttp.js";

const endpoint = process.argv[2];
if (!endpoint) throw new Error("Usage: npm run smoke -- https://YOUR-WORKER.workers.dev/mcp");
const base = new URL(endpoint).origin;
const healthResponse = await fetch(`${base}/health`);
assert.equal(healthResponse.status, 200);
const health = await healthResponse.json();
assert.equal(health.mode, "read-only");
let client = new Client({ name: "editbay-smoke", version: "1.0.0" });
try {
  await client.connect(new StreamableHTTPClientTransport(new URL(endpoint)));
  const tools = await client.listTools();
  assert.equal(tools.tools.length, 4);
  const skill = await client.callTool({ name: "get_skill", arguments: { name: "video-director" } });
  assert.ok(!skill.isError);
  assert.equal(skill.structuredContent.revision, health.revision);
  // Citations name the canonical host (wrangler dev presents the custom-domain host), so read the
  // cited path from the server under test; in production the two origins are the same.
  const cited = new URL(skill.structuredContent.url);
  assert.ok(cited.pathname.startsWith("/docs/"));
  const source = await fetch(new URL(cited.pathname, base));
  assert.equal(source.status, 200);
  assert.equal(await source.text(), skill.structuredContent.content);
  const search = await client.callTool({ name: "search_editbay", arguments: { query: "rough cut", limit: 5 } });
  assert.ok(search.structuredContent.results.length > 0);
  const invalid = await client.callTool({ name: "read_document", arguments: { path: ".env" } });
  assert.equal(invalid.isError, true);
  const resources = await client.listResources();
  assert.equal(resources.resources.length, health.documents);
  const runbook = await client.readResource({ uri: "editbay://docs/skills/video-director/references/routes.md" });
  assert.ok(runbook.contents.length > 0);
  console.log(JSON.stringify({ status: "PASS", endpoint, revision: health.revision, skills: health.skills, documents: health.documents, tools: tools.tools.map((tool) => tool.name) }));
} finally { await client.close(); }
