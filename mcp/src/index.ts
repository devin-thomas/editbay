import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { WebStandardStreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/webStandardStreamableHttp.js";
import { ErrorCode, ListResourcesRequestSchema, McpError, ReadResourceRequestSchema, type CallToolResult } from "@modelcontextprotocol/sdk/types.js";
import { z } from "zod";
import { documents, documentUri, documentUrl, findDocument, revision, searchDocuments, type Document, type SearchHit } from "./content.ts";

function summarize(description: string): string {
  const sentence: string = /^.+?[.!?](?=\s|$)/.exec(description)?.[0] ?? description;
  return sentence.length > 140 ? `${sentence.slice(0, 137)}...` : sentence;
}

const skillDocuments: readonly Document[] = documents.filter((document: Document): boolean => document.skill !== null);
const skillIndex: string = skillDocuments.map((document: Document): string => `- ${document.skill}: ${summarize(document.description)}`).join("\n");
const instructions: string = `editbay skills for editing and making videos. When a request matches a skill below (cutting, captions, transcripts, motion graphics, sound, verification, delivery, app footage, style references), load that skill before starting: use the prompt of the same name, or get_skill.\n${skillIndex}\nStart with video-director for a whole edit. list_skills returns each skill's full "use when" description.\n\n` + "editbay is a read-only source of video-editing skills, documentation and runbooks. Start with list_skills or search_editbay, then get_skill and read_document. Follow references using exact repository-relative paths; resolve Markdown links relative to the document path. Read all pages using nextOffset. Responses identify their committed source revision and SHA-256. Historical provider prices and host benchmarks are documentation, not current guarantees. Tools, media editing, rendering, downloads, local files and paid services run on the caller's machine, never on this server. $EB in runbooks means a caller-installed editbay checkout. This server serves no personal config, examples or credentials.";
const annotations = { readOnlyHint: true, destructiveHint: false, idempotentHint: true, openWorldHint: false } as const;
const authMeta = { securitySchemes: [{ type: "noauth" }] } as const;
const pathSchema = z.string().min(1).max(300).describe("Exact repository-relative document path, such as skills/video-director/SKILL.md");

function result(value: Record<string, unknown>): CallToolResult {
  return { content: [{ type: "text", text: JSON.stringify(value) }], structuredContent: value };
}

function metadata(document: Document, baseUrl: string): Record<string, unknown> {
  return { path: document.path, title: document.title, uri: documentUri(document.path), url: documentUrl(baseUrl, document.path), revision, sha256: document.sha256 };
}

function requireDocument(path: string): Document {
  const document: Document | undefined = findDocument(path);
  if (!document) throw new McpError(ErrorCode.InvalidParams, "Unknown document. Use search_editbay or resources/list for exact published paths.");
  return document;
}

export function createServer(baseUrl: string): McpServer {
  let server: McpServer = new McpServer({ name: "editbay", version: "0.1.0" }, { instructions });
  server.registerTool("list_skills", {
    description: "Browse every editbay skill with its purpose and document path. Start with video-director for an end-to-end editing runbook.",
    inputSchema: {}, annotations, _meta: authMeta,
  }, (): CallToolResult => result({ revision, skills: documents.filter((document: Document): boolean => document.skill !== null).map((document: Document): Record<string, unknown> => ({ name: document.skill, description: document.description, ...metadata(document, baseUrl) })) }));

  server.registerTool("search_editbay", {
    description: "Search editbay skills, reference runbooks and documentation. Space-separated terms must all match. Returns excerpts and exact paths for read_document.",
    inputSchema: { query: z.string().trim().min(1).max(200), limit: z.number().int().min(1).max(20).default(8) }, annotations, _meta: authMeta,
  }, ({ query, limit }: { query: string; limit: number }): CallToolResult => result({ revision, results: searchDocuments(query, limit).map((hit: SearchHit): Record<string, unknown> => ({ ...hit, url: documentUrl(baseUrl, hit.path) })) }));

  server.registerTool("get_skill", {
    description: "Load a complete editbay skill and list its supporting reference documents. Read those documents separately as needed. Instructions describe work performed by the calling agent, not server execution.",
    inputSchema: { name: z.string().regex(/^[a-z0-9-]{1,80}$/) }, annotations, _meta: authMeta,
  }, ({ name }: { name: string }): CallToolResult => {
    const document: Document = requireDocument(`skills/${name}/SKILL.md`);
    return result({ ...metadata(document, baseUrl), content: document.text, references: documents.filter((candidate: Document): boolean => candidate.path.startsWith(`skills/${name}/references/`)).map((candidate: Document): Record<string, unknown> => metadata(candidate, baseUrl)) });
  });

  server.registerTool("read_document", {
    description: "Read an exact published document path. Pagination uses JavaScript string character offsets; follow nextOffset until null. Returns source revision, hash and a public citation URL.",
    inputSchema: { path: pathSchema, offset: z.number().int().min(0).default(0), limit: z.number().int().min(1).max(24000).default(12000) }, annotations, _meta: authMeta,
  }, ({ path, offset, limit }: { path: string; offset: number; limit: number }): CallToolResult => {
    const document: Document = requireDocument(path);
    if (offset > document.text.length) throw new McpError(ErrorCode.InvalidParams, "Offset exceeds document length");
    const end: number = Math.min(offset + limit, document.text.length);
    return result({ ...metadata(document, baseUrl), content: document.text.slice(offset, end), offset, nextOffset: end < document.text.length ? end : null, totalCharacters: document.text.length });
  });

  for (const skill of skillDocuments) {
    const name: string = skill.skill ?? "";
    const references: readonly Document[] = documents.filter((candidate: Document): boolean => candidate.path.startsWith(`skills/${name}/references/`));
    server.registerPrompt(name, {
      title: `editbay: ${name}`,
      description: skill.description,
      argsSchema: { task: z.string().trim().max(2000).optional().describe("What you want to do with this skill; added above the skill text") },
    }, ({ task }: { task?: string | undefined }) => {
      const lines: string[] = [
        `Follow the editbay skill "${name}" (source revision ${revision}, SHA-256 ${skill.sha256}).`,
        ...(task ? ["", `Task: ${task}`] : []),
        "",
        skill.text,
        "",
        references.length === 0 ? "This skill has no separate reference documents." : `Supporting references (read each with read_document using the path, or as a resource):\n${references.map((reference: Document): string => `- ${reference.path} (${documentUri(reference.path)})`).join("\n")}`,
        "",
        "This server only serves instructions. Tools, rendering, media and files run on your machine; $EB means a local editbay checkout.",
      ];
      return { description: skill.description, messages: [{ role: "user" as const, content: { type: "text" as const, text: lines.join("\n") } }] };
    });
  }

  server.server.registerCapabilities({ resources: {} });
  server.server.setRequestHandler(ListResourcesRequestSchema, (): { resources: { uri: string; name: string; description: string; mimeType: string }[] } => ({
    resources: documents.map((document: Document): { uri: string; name: string; description: string; mimeType: string } => ({ uri: documentUri(document.path), name: document.path, description: document.description || document.title, mimeType: "text/markdown" })),
  }));
  server.server.setRequestHandler(ReadResourceRequestSchema, (request): { contents: { uri: string; mimeType: string; text: string }[] } => {
    if (!request.params.uri.startsWith("editbay://docs/")) throw new McpError(ErrorCode.InvalidParams, "Expected an editbay://docs/ resource URI");
    const document: Document = requireDocument(request.params.uri.replace(/^editbay:\/\/docs\//, ""));
    return { contents: [{ uri: documentUri(document.path), mimeType: "text/markdown", text: document.text }] };
  });
  return server;
}

function withHeaders(response: Response): Response {
  let headers: Headers = new Headers(response.headers);
  headers.set("Access-Control-Allow-Origin", "*");
  headers.set("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
  headers.set("Access-Control-Allow-Headers", "Content-Type, Accept, MCP-Protocol-Version, MCP-Session-Id, Last-Event-ID");
  headers.set("Access-Control-Expose-Headers", "MCP-Session-Id, MCP-Protocol-Version");
  headers.set("X-Content-Type-Options", "nosniff");
  headers.set("Cache-Control", "no-store");
  return new Response(response.body, { status: response.status, statusText: response.statusText, headers });
}

export async function handleRequest(request: Request): Promise<Response> {
  const url: URL = new URL(request.url);
  if (request.method === "OPTIONS") return withHeaders(new Response(null, { status: 204 }));
  if (url.pathname === "/health" && request.method === "GET") {
    return withHeaders(Response.json({ status: "ok", name: "editbay", revision, documents: documents.length, skills: documents.filter((document: Document): boolean => document.skill !== null).length, mode: "read-only" }));
  }
  if (url.pathname === "/about.json" && request.method === "GET") {
    return withHeaders(Response.json({ name: "editbay", description: "Free, read-only skills, documentation and video editing runbooks", mcp: `${url.origin}/mcp`, transport: "Streamable HTTP", authentication: "none", revision, instructions }));
  }
  if (url.pathname.startsWith("/docs/") && request.method === "GET") {
    let path: string;
    try { path = decodeURIComponent(url.pathname.slice(6)); }
    catch { return withHeaders(new Response("Invalid path encoding", { status: 400 })); }
    const document: Document | undefined = findDocument(path);
    if (!document) return withHeaders(new Response("Document not found", { status: 404 }));
    return withHeaders(new Response(document.text, { headers: { "Content-Type": "text/plain; charset=utf-8", "X-Editbay-Revision": revision, "X-Content-SHA256": document.sha256 } }));
  }
  if (url.pathname !== "/mcp") return withHeaders(new Response("Not found", { status: 404 }));
  if (request.method !== "GET" && request.method !== "POST") return withHeaders(new Response("Method not allowed", { status: 405, headers: { Allow: "GET, POST, OPTIONS" } }));
  let server: McpServer = createServer(url.origin);
  let transport: WebStandardStreamableHTTPServerTransport = new WebStandardStreamableHTTPServerTransport({ enableJsonResponse: true, maxRequestBodySize: 16384 });
  await server.connect(transport);
  try { return withHeaders(await transport.handleRequest(request)); }
  finally { await server.close(); }
}

export default { fetch: handleRequest };
