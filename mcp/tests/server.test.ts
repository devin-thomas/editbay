import assert from "node:assert/strict";
import { test } from "node:test";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StreamableHTTPClientTransport } from "@modelcontextprotocol/sdk/client/streamableHttp.js";
import { z } from "zod";
import { handleRequest } from "../src/index.ts";
import { documents, findDocument, revision } from "../src/content.ts";

async function connect(): Promise<Client> {
  let client: Client = new Client({ name: "editbay-test", version: "1.0.0" });
  let transport: StreamableHTTPClientTransport = new StreamableHTTPClientTransport(new URL("https://editbay.test/mcp"), {
    fetch: async (input, init): Promise<Response> => handleRequest(new Request(input, init)),
  });
  await client.connect(transport);
  return client;
}

test("real SDK initialization, tool discovery, skill loading and reference reading", async (): Promise<void> => {
  let client: Client = await connect();
  try {
    const tools = await client.listTools();
    assert.deepEqual(tools.tools.map((tool): string => tool.name).sort(), ["get_skill", "list_skills", "read_document", "search_editbay"]);
    assert.ok(tools.tools.every((tool): boolean => tool.annotations?.readOnlyHint === true));
    const skills = await client.callTool({ name: "list_skills", arguments: {} });
    assert.match(JSON.stringify(skills), /video-director/);
    const skill = await client.callTool({ name: "get_skill", arguments: { name: "video-director" } });
    assert.equal(skill.isError, undefined);
    assert.match(JSON.stringify(skill), /references\/routes.md/);
    const resource = await client.readResource({ uri: "editbay://docs/skills/video-director/references/routes.md" });
    assert.match(JSON.stringify(resource), /talking.head/i);
    assert.ok((await client.listResources()).resources.length === documents.length);
  } finally { await client.close(); }
});

test("server instructions name every skill so a model can route to it", async (): Promise<void> => {
  let client: Client = await connect();
  try {
    const instructions: string = client.getInstructions() ?? "";
    const names: string[] = documents.flatMap((document): string[] => (document.skill === null ? [] : [document.skill]));
    assert.ok(names.length >= 17);
    for (const name of names) assert.ok(instructions.includes(`- ${name}:`), name);
    assert.ok(instructions.length < 6000, `instructions too long: ${instructions.length}`);
  } finally { await client.close(); }
});

test("every skill is a prompt that carries the skill text, task and references", async (): Promise<void> => {
  let client: Client = await connect();
  try {
    const skills = documents.filter((document): boolean => document.skill !== null);
    const prompts = await client.listPrompts();
    assert.deepEqual(prompts.prompts.map((prompt): string => prompt.name).sort(), skills.map((document): string => document.skill ?? "").sort());
    for (const prompt of prompts.prompts) {
      const skill = skills.find((document): boolean => document.skill === prompt.name);
      assert.ok(skill);
      assert.equal(prompt.description, skill.description);
    }
    const loaded = await client.getPrompt({ name: "rough-cut", arguments: { task: "cut the pauses from interview.mp4" } });
    const text: string = JSON.stringify(loaded.messages);
    assert.match(text, /cut the pauses from interview\.mp4/);
    assert.match(text, /skills\/rough-cut\/references\/pacing\.md/);
    assert.match(text, new RegExp(findDocument("skills/rough-cut/SKILL.md")?.sha256 ?? "missing"));
    const bare = await client.getPrompt({ name: "video-director" });
    assert.doesNotMatch(JSON.stringify(bare.messages), /Task:/);
    await assert.rejects(client.getPrompt({ name: "not-a-skill" }));
  } finally { await client.close(); }
});

test("search finds a relevant runbook and returns no invented matches", async (): Promise<void> => {
  let client: Client = await connect();
  try {
    const found = await client.callTool({ name: "search_editbay", arguments: { query: "loudness", limit: 3 } });
    assert.match(JSON.stringify(found), /loudness/i);
    assert.match(JSON.stringify(found), /https:\/\/editbay.test\/docs\//);
    const absent = await client.callTool({ name: "search_editbay", arguments: { query: "zzzxnonexistent987" } });
    assert.deepEqual(z.object({ results: z.array(z.unknown()) }).parse(absent.structuredContent).results, []);
  } finally { await client.close(); }
});

test("document pagination reconstructs the source without gaps", async (): Promise<void> => {
  let client: Client = await connect();
  try {
    const document = findDocument("skills/video-director/SKILL.md");
    assert.ok(document);
    let text: string = "";
    let offset: number | null = 0;
    while (offset !== null) {
      const page = await client.callTool({ name: "read_document", arguments: { path: document.path, offset, limit: 701 } });
      const value = z.object({ content: z.string(), revision: z.string(), sha256: z.string(), nextOffset: z.number().nullable() }).parse(page.structuredContent);
      assert.equal(value.revision, revision);
      assert.equal(value.sha256, document.sha256);
      text += value.content;
      offset = value.nextOffset;
    }
    assert.equal(text, document.text);
  } finally { await client.close(); }
});

test("unknown documents, path traversal, invalid inputs and unknown skills fail explicitly", async (): Promise<void> => {
  let client: Client = await connect();
  try {
    for (const path of [".env", "config/config.example.json", "../README.md", "docs/../AGENTS.md", "skills/nope/SKILL.md"]) {
      const result = await client.callTool({ name: "read_document", arguments: { path } });
      assert.equal(result.isError, true, path);
    }
    for (const args of [{ query: " " }, { query: "cut", limit: 1000 }]) {
      assert.equal((await client.callTool({ name: "search_editbay", arguments: args })).isError, true);
    }
    assert.equal((await client.callTool({ name: "get_skill", arguments: { name: "missing" } })).isError, true);
    assert.equal((await client.callTool({ name: "read_document", arguments: { path: "README.md", offset: 9999999 } })).isError, true);
  } finally { await client.close(); }
});

test("only the committed documentation allowlist is exposed", (): void => {
  assert.match(revision, /^[a-f0-9]{40}$/);
  for (const document of documents) {
    assert.ok(document.path === "README.md" || document.path === "mcp/README.md" || document.path.startsWith("docs/") || /^skills\/[^/]+\/(SKILL.md|references\/.*.md)$/.test(document.path));
    assert.match(document.sha256, /^[a-f0-9]{64}$/);
    assert.ok(!document.path.includes(".env"));
    assert.ok(!document.path.startsWith("examples/"));
  }
});

test("published bytes come from the pinned commit rather than the working tree", (): void => {
  const root: string = fileURLToPath(new URL("../../", import.meta.url));
  for (const document of documents) {
    const committed: string = execFileSync("git", ["-C", root, "show", `${revision}:${document.path}`], { encoding: "utf8" });
    assert.equal(document.text, committed, document.path);
  }
});

test("public citation documents match MCP sources and private paths stay inaccessible", async (): Promise<void> => {
  const response: Response = await handleRequest(new Request("https://editbay.test/docs/skills/video-director/SKILL.md"));
  assert.equal(response.status, 200);
  assert.equal(response.headers.get("X-Editbay-Revision"), revision);
  assert.equal(await response.text(), findDocument("skills/video-director/SKILL.md")?.text);
  for (const path of [".env", "config/config.example.json", "AGENTS.md", "examples/anything.md"]) {
    assert.equal((await handleRequest(new Request(`https://editbay.test/docs/${path}`))).status, 404);
  }
  assert.equal((await handleRequest(new Request("https://editbay.test/docs/%GG"))).status, 400);
});

test("CORS, method handling and oversized bodies", async (): Promise<void> => {
  const preflight: Response = await handleRequest(new Request("https://editbay.test/mcp", { method: "OPTIONS", headers: { Origin: "https://example.org" } }));
  assert.equal(preflight.status, 204);
  assert.equal(preflight.headers.get("Access-Control-Allow-Origin"), "*");
  assert.equal((await handleRequest(new Request("https://editbay.test/mcp", { method: "DELETE" }))).status, 405);
  const oversized: Response = await handleRequest(new Request("https://editbay.test/mcp", { method: "POST", headers: { "Content-Type": "application/json", Accept: "application/json, text/event-stream" }, body: JSON.stringify({ jsonrpc: "2.0", id: 1, method: "tools/call", params: { name: "search_editbay", arguments: { query: "a".repeat(20000) } } }) }));
  assert.equal(oversized.status, 413);
});
