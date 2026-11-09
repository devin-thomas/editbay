import assert from "node:assert/strict";
import { chromium } from "playwright";
import { mkdtemp } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
const base = new URL(process.argv[2] || "http://127.0.0.1:8793");
if (!["http:", "https:"].includes(base.protocol) || base.username || base.password) throw new Error("Expected a plain HTTP(S) preview URL");
const output = await mkdtemp(join(tmpdir(), "editbay-browser-"));
const browser = await chromium.launch();
try {
  for (const width of [1440, 1024, 768, 390, 320]) {
    const context = await browser.newContext({ viewport: { width, height: 1000 } });
    const page = await context.newPage();
    const errors = [];
    page.on("pageerror", (error) => errors.push(error.message));
    await page.goto(base.href, { waitUntil: "networkidle" });
    assert.equal(await page.locator("h1").count(), 1);
    assert.ok(await page.locator("#connect").isVisible());
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1), false, `horizontal overflow at ${width}`);
    await page.locator("#demo-toggle").click();
    await page.waitForTimeout(300);
    assert.equal(await page.locator("#demo-toggle").getAttribute("aria-pressed"), "true");
    await page.locator("#demo-toggle").click();
    assert.equal(await page.locator("#demo-toggle").getAttribute("aria-pressed"), "false");
    await page.screenshot({ path: join(output, `${width}.png`), fullPage: true });
    assert.deepEqual(errors, []);
    await context.close();
  }
  const context = await browser.newContext({ reducedMotion: "reduce" });
  const page = await context.newPage();
  await page.goto(base.href);
  assert.equal(await page.locator("#demo-toggle").innerText(), "Step illustration");
  await page.locator("#demo-toggle").click();
  assert.equal(await page.locator("#demo-toggle").getAttribute("aria-pressed"), "false");
  const frame = await page.locator("#frame-counter").innerText();
  await page.waitForTimeout(250);
  assert.equal(await page.locator("#frame-counter").innerText(), frame);
  await page.evaluate(() => Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText: async () => { throw new Error("denied"); } } }));
  await page.locator("#copy-endpoint").click();
  await page.getByRole("status").filter({ hasText: "Clipboard unavailable" }).waitFor();
  await page.evaluate(() => Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText: async (text) => { if (text !== "https://editbay.uppercut-labs.com/mcp") throw new Error("wrong endpoint"); } } }));
  await page.locator("#copy-endpoint").click();
  await page.getByRole("status").filter({ hasText: "Endpoint copied" }).waitFor();
  await context.close();
  console.log(`PASS: five viewports, animation control, reduced motion, clipboard denial and success. Screenshots: ${output}`);
} finally { await browser.close(); }
