import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
const root = fileURLToPath(new URL("../../", import.meta.url));
const python = process.env["PYTHON"] || (process.platform === "win32" ? "python" : "python3");
execFileSync(python, ["scripts/check_public.py", "--root", root], { cwd: root, stdio: "inherit" });
/** @type {{revision:string, documents:Array<{path:string,text:string,sha256:string}>}} */
const corpus = JSON.parse(readFileSync(new URL("../src/generated/content.json", import.meta.url), "utf8"));
/** @type {{documents:string[]}} */
const manifest = JSON.parse(readFileSync(new URL("../public-documents.json", import.meta.url), "utf8"));
assert.deepEqual(corpus.documents.map((doc) => doc.path).sort(), [...manifest.documents].sort());
for (const doc of corpus.documents) {
  const committed = execFileSync("git", ["-C", root, "show", `${corpus.revision}:${doc.path}`], { encoding: "utf8" });
  assert.equal(doc.text, committed, `Bundled bytes drifted: ${doc.path}`);
  assert.equal(doc.sha256, createHash("sha256").update(committed).digest("hex"));
}
console.log(`PASS: ${corpus.documents.length} served documents match the explicit list and public commit`);
