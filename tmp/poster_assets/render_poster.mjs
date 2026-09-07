import { pathToFileURL } from "url";
import { createRequire } from "module";

const require = createRequire(import.meta.url);
const { chromium } = require("playwright");

const input = "/Users/sreeharshak/Dev/research-agents/tmp/poster_assets/poster.html";
const output = "/Users/sreeharshak/Dev/research-agents/tmp/poster_assets/poster-preview.png";
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 5184, height: 4032 }, deviceScaleFactor: 1 });
await page.goto(pathToFileURL(input).href, { waitUntil: "networkidle" });
await page.screenshot({ path: output, fullPage: false });
await browser.close();
