"use strict";
const endpoint = "https://editbay.uppercut-labs.com/mcp";

function selectText(node) {
  const range = document.createRange();
  range.selectNodeContents(node);
  const selection = window.getSelection();
  selection?.removeAllRanges();
  selection?.addRange(range);
}

function copier(buttonId, statusId, sourceId, text, done) {
  const button = document.getElementById(buttonId);
  const status = document.getElementById(statusId);
  button?.addEventListener("click", async () => {
    try {
      if (!navigator.clipboard?.writeText) throw new Error("Clipboard unavailable");
      await navigator.clipboard.writeText(text());
      status.textContent = done;
    } catch {
      status.textContent = "Clipboard unavailable. The text is selected; copy it manually.";
      selectText(document.getElementById(sourceId));
    }
  });
}

const prompts = {
  "pick-claude": "Install the EditBay plugin in Claude Code: run claude plugin marketplace add devin-thomas/editbay, then claude plugin install editbay@editbay. When both succeed, tell me to start a new session. In that session, load the video-director skill and use it to plan my edit. Keep my footage and renders on this machine.",
  "pick-mcp": "Connect the EditBay MCP server at https://editbay.uppercut-labs.com/mcp (Streamable HTTP, no sign-in). Load the video-director skill and use it to plan my edit. When a skill names a script, fetch it with get_tool into one local folder, check its SHA-256 and run it locally with uv run. Keep my footage and renders on this machine.",
};
for (const id of Object.keys(prompts)) {
  document.getElementById(id)?.addEventListener("click", () => {
    document.getElementById("setup-prompt").textContent = prompts[id];
    document.getElementById("prompt-status").textContent = "";
    for (const other of Object.keys(prompts)) document.getElementById(other)?.setAttribute("aria-pressed", String(other === id));
  });
}

copier("copy-prompt", "prompt-status", "setup-prompt", () => document.getElementById("setup-prompt").textContent.trim(), "Prompt copied.");
copier("copy-endpoint", "copy-status", "endpoint", () => endpoint, "URL copied.");
