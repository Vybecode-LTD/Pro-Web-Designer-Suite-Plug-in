// Turn social/*.svg into the PNGs GitHub's social preview takes (1280x640,
// under 1 MB), with tooling/main's pinned Playwright and its Chromium.
//
//     node "dev plans/readme-art/render_social.mjs"
//
// Playwright is loaded by its path in tooling/main's node_modules, never by
// name: a bare name walks up to any parent's node_modules and NODE_PATH, and
// would run an unpinned copy when tooling/main has none (CodeRabbit on #236).
import { createRequire } from "node:module";
import { readdirSync, statSync } from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const pinned = path.join(here, "..", "..", "tooling", "main", "node_modules", "playwright");
const { chromium } = createRequire(import.meta.url)(pinned);

const dir = path.join(here, "social");
const svgs = readdirSync(dir).filter((f) => f.endsWith(".svg"));
if (svgs.length === 0) {
  console.error(`no SVG in ${dir}: run build_readme_art.py first`);
  process.exit(2);
}
const browser = await chromium.launch();
try {
  const page = await browser.newPage({ viewport: { width: 1280, height: 640 }, deviceScaleFactor: 1 });
  for (const name of svgs) {
    await page.goto(pathToFileURL(path.join(dir, name)).href);
    const out = path.join(dir, name.replace(/\.svg$/, ".png"));
    await page.screenshot({ path: out, clip: { x: 0, y: 0, width: 1280, height: 640 }, timeout: 15000 });
    const kb = statSync(out).size / 1024;
    console.log(`wrote ${name.replace(/\.svg$/, ".png")}: ${kb.toFixed(0)} KB${kb >= 1024 ? " (over GitHub's 1 MB)" : ""}`);
  }
} finally {
  await browser.close();
}
