import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { mkdirSync, realpathSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
const root = realpathSync(fileURLToPath(new URL("../../", import.meta.url)));
const git = (...args) => execFileSync("git", ["-C", root, ...args], { encoding: "utf8", maxBuffer: 8 * 1024 * 1024 });
export function isPublishedPath(path) {
  return path === "README.md" || path === "mcp/README.md" || /^docs\/[A-Z-]+\.md$/.test(path) || /^skills\/[a-z0-9-]+\/(SKILL\.md|references\/[a-z0-9-]+\.md)$/.test(path);
}
export function buildContent() {
  if (realpathSync(git("rev-parse", "--show-toplevel").trim()) !== root) throw new Error("Build only from a standalone public checkout, not a folder inside another repository");
  if (git("status", "--porcelain", "--untracked-files=all").trim()) throw new Error("Commit the reviewed public files before building; working tree is dirty");
  const revision = git("rev-parse", "HEAD").trim();
  const marker = JSON.parse(git("show", `${revision}:PUBLIC_RELEASE.json`));
  if (marker.site !== "https://editbay.uppercut-labs.com") throw new Error("Missing public release marker");
  const manifest = JSON.parse(git("show", `${revision}:mcp/public-documents.json`));
  if (manifest.schema !== 1 || !Array.isArray(manifest.documents) || new Set(manifest.documents).size !== manifest.documents.length) throw new Error("Invalid explicit document manifest");
  const documents = manifest.documents.map((path) => {
    if (typeof path !== "string" || !isPublishedPath(path)) throw new Error("Unapproved document path");
    const text = git("show", `${revision}:${path}`);
    const title = /^# (.+)$/m.exec(text)?.[1] ?? path;
    const skill = /^skills\/([^/]+)\/SKILL\.md$/.exec(path)?.[1] ?? null;
    const description = skill === null ? "" : /^description: (.+)$/m.exec(text)?.[1]?.replace(/^"(.*)"$/, "$1");
    if (skill !== null && !description) throw new Error(`Missing description: ${path}`);
    return { path, title, skill, description: description ?? "", text, sha256: createHash("sha256").update(text).digest("hex") };
  });
  if (!documents.some((document) => document.skill === "video-director")) throw new Error("Missing entry skill");
  const directory = new URL("../src/generated/", import.meta.url);
  mkdirSync(directory, { recursive: true });
  writeFileSync(new URL("content.json", directory), `${JSON.stringify({ revision, documents })}\n`);
  console.log(`Bundled ${documents.length} explicitly approved documents from public commit ${revision}`);
}
if (process.argv[1] === fileURLToPath(import.meta.url)) buildContent();
