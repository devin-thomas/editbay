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

copier("copy-prompt", "prompt-status", "setup-prompt", () => document.getElementById("setup-prompt").textContent.trim(), "Prompt copied.");
copier("copy-endpoint", "copy-status", "endpoint", () => endpoint, "URL copied.");
