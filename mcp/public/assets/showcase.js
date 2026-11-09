"use strict";
const endpoint = "https://editbay.uppercut-labs.com/mcp";
const copyButton = document.querySelector("#copy-endpoint");
const copyStatus = document.querySelector("#copy-status");
copyButton?.addEventListener("click", async () => {
  try {
    if (!navigator.clipboard?.writeText) throw new Error("Clipboard unavailable");
    await navigator.clipboard.writeText(endpoint);
    copyStatus.textContent = "Endpoint copied.";
  } catch {
    copyStatus.textContent = "Clipboard unavailable. Select and copy the endpoint above.";
    const range = document.createRange();
    range.selectNodeContents(document.querySelector("#endpoint"));
    const selection = window.getSelection();
    selection?.removeAllRanges();
    selection?.addRange(range);
  }
});
const toggle = document.querySelector("#demo-toggle");
const head = document.querySelector("#playhead");
const title = document.querySelector("#demo-title");
const counter = document.querySelector("#frame-counter");
const clock = document.querySelector("#demo-time");
const reduced = window.matchMedia("(prefers-reduced-motion: reduce)");
let running = false, progress = 0, previous = 0, frame = 0;
function draw() {
  const width = Math.max(0, document.querySelector(".timeline").clientWidth - 67);
  head.style.transform = `translateX(${width * progress / 12000}px)`;
  counter.textContent = `FRAME ${String(Math.floor(progress * 24 / 1000)).padStart(3, "0")}`;
  clock.textContent = `00:${String(Math.floor(progress / 1000)).padStart(2, "0")} / 00:12`;
  title.textContent = progress < 4000 ? "A better cut." : progress < 8000 ? "Every beat matters." : "Finish with proof.";
}
function stop() {
  running = false;
  cancelAnimationFrame(frame);
  toggle.textContent = reduced.matches ? "Step illustration" : "Play illustration";
  toggle.setAttribute("aria-pressed", "false");
}
function tick(now) {
  if (!running) return;
  progress = (progress + Math.min(now - previous, 100)) % 12000;
  previous = now;
  draw();
  frame = requestAnimationFrame(tick);
}
toggle?.addEventListener("click", () => {
  if (reduced.matches) { progress = (progress + 4000) % 12000; draw(); return; }
  if (running) { stop(); return; }
  running = true; previous = performance.now();
  toggle.textContent = "Pause illustration";
  toggle.setAttribute("aria-pressed", "true");
  frame = requestAnimationFrame(tick);
});
window.addEventListener("resize", draw);
document.addEventListener("visibilitychange", () => { if (document.hidden) stop(); });
reduced.addEventListener("change", stop);
stop();
draw();
