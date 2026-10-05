#!/usr/bin/env node
/**
 * snapshot_matrix.mjs — screenshot every cell of a generated proof sheet,
 * compare against baselines, write an HTML diff report, exit non-zero on a
 * regression.
 *
 * It shoots ONE IMAGE PER CELL, not one per page. A page-level baseline turns
 * every change into one enormous diff that nobody reads; a cell-level baseline
 * tells you "button / primary / hover / dark / compact moved" and nothing else.
 * That is the difference between a check people keep and a check people disable.
 *
 * Only dependency: `playwright`. The comparison runs inside the browser on a
 * canvas, so there is no pixelmatch/pngjs/sharp to install and nothing to
 * compile. The browser is never downloaded — pass --browser, set
 * MATRIX_CHROMIUM, or let it use the first that starts of
 * /opt/pw-browsers/chromium, Playwright's own Chromium, and an installed
 * Chrome or Edge. Pin one for baselines that must match across machines.
 *
 * Usage
 * -----
 *   # first run: record the baselines, then eyeball them once, then commit
 *   node snapshot_matrix.mjs build/proof-sheet.html \
 *        --baselines tests/visual/baselines --update-baselines
 *
 *   # every run after that
 *   node snapshot_matrix.mjs build/proof-sheet.html \
 *        --baselines tests/visual/baselines --out build/visual-report
 *
 *   # narrow while iterating
 *   node snapshot_matrix.mjs build/proof-sheet.html --only "button--" --only "t_dark"
 *
 *   # loosen once, deliberately, with a reason in the commit message
 *   node snapshot_matrix.mjs sheet.html --threshold 0.004 --pixel-threshold 0.12
 *
 * Options
 * -------
 *   --baselines DIR        where baseline PNGs live       (default ./matrix-baselines)
 *   --out DIR              report + current + diff output (default ./matrix-report)
 *   --update-baselines     accept everything as the new truth
 *   --prune                with --update-baselines, delete baselines with no cell
 *   --threshold N          max fraction of differing pixels per cell (default 0.002)
 *   --pixel-threshold N    perceptual tolerance per pixel, 0..1     (default 0.03)
 *
 * Every hover, active and focus-visible cell must also DIFFER from its default
 * cell, in the same run, with no baseline involved: a state that renders
 * exactly like default has no style, and that fails. (At the old 0.10
 * tolerance the suite's own 4% hover and 8% pressed overlays were below the
 * noise floor, so deleting :hover or :active passed every cell.)
 *   --allow-new            a cell with no baseline is not a failure
 *   --only SUBSTR          only cells whose id contains SUBSTR (repeatable)
 *   --viewport WxH         browser viewport                 (default 1440x900)
 *   --dpr N                device pixel ratio               (default 1)
 *   --browser PATH         chromium executable      (default: found, see above)
 *   --quiet
 *
 * Exit codes
 * ----------
 *   0  every cell matched, or baselines were updated
 *   1  at least one regression, new cell, or capture error
 *   2  bad arguments, missing sheet, no usable browser, or the run itself
 *      failed: a crash is never a regression
 */

import { createRequire } from 'node:module';
import { pathToFileURL } from 'node:url';
import fs from 'node:fs';
import path from 'node:path';

import { FREEZE_ANIMATIONS_CSS, launchBrowser, loadPlaywright } from './browser_common.mjs';

// ---------------------------------------------------------------------------
// Arguments
// ---------------------------------------------------------------------------

function die(msg, code = 2) {
  process.stderr.write(`snapshot_matrix: ${msg}\n`);
  process.exit(code);
}

function parseArgs(argv) {
  const opts = {
    sheet: null,
    baselines: 'matrix-baselines',
    out: 'matrix-report',
    update: false,
    prune: false,
    threshold: 0.002,
    // 0.03 (a YIQ distance of ~32): a 4% black overlay on white moves each
    // channel ~10 levels (distance ~51), 8% ~210. At 0.10 (~352) both were
    // invisible. The antialiasing escape below still absorbs sub-pixel shifts.
    pixelThreshold: 0.03,
    allowNew: false,
    only: [],
    viewport: { width: 1440, height: 900 },
    dpr: 1,
    browser: process.env.MATRIX_CHROMIUM || '',
    quiet: false,
  };
  const need = (i, flag) => {
    if (i + 1 >= argv.length) die(`${flag} needs a value`);
    return argv[i + 1];
  };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    switch (a) {
      case '-h': case '--help':
        process.stdout.write(fs.readFileSync(new URL(import.meta.url), 'utf8')
          .replace(/^#!.*\r?\n/, '').split('*/')[0]
          .replace(/^\/\*\*?\r?\n?/, '').replace(/^ ?\* ?/gm, ''));
        process.exit(0);
        break;
      case '--baselines': opts.baselines = need(i, a); i++; break;
      case '--out': opts.out = need(i, a); i++; break;
      case '--update-baselines': opts.update = true; break;
      case '--prune': opts.prune = true; break;
      case '--threshold': opts.threshold = Number(need(i, a)); i++; break;
      case '--pixel-threshold': opts.pixelThreshold = Number(need(i, a)); i++; break;
      case '--allow-new': opts.allowNew = true; break;
      case '--only': opts.only.push(need(i, a)); i++; break;
      case '--dpr': opts.dpr = Number(need(i, a)); i++; break;
      case '--browser': opts.browser = need(i, a); i++; break;
      case '--quiet': opts.quiet = true; break;
      case '--viewport': {
        const v = need(i, a); i++;
        const m = /^(\d+)x(\d+)$/.exec(v);
        if (!m) die(`--viewport must look like 1440x900, got "${v}"`);
        opts.viewport = { width: Number(m[1]), height: Number(m[2]) };
        break;
      }
      default:
        if (a.startsWith('-')) die(`unknown option ${a} (try --help)`);
        else if (opts.sheet) die(`more than one sheet given: ${opts.sheet} and ${a}`);
        else opts.sheet = a;
    }
  }
  if (!opts.sheet) die('no proof sheet given. Usage: node snapshot_matrix.mjs <sheet.html> [options]');
  if (!Number.isFinite(opts.threshold) || opts.threshold < 0 || opts.threshold > 1)
    die('--threshold must be a fraction between 0 and 1');
  if (!Number.isFinite(opts.pixelThreshold) || opts.pixelThreshold < 0 || opts.pixelThreshold > 1)
    die('--pixel-threshold must be between 0 and 1');
  if (!fs.existsSync(opts.sheet)) die(`no such proof sheet: ${opts.sheet}`);
  return opts;
}

// ---------------------------------------------------------------------------
// Determinism
// ---------------------------------------------------------------------------
// Every line here removes one source of flake. A visual check that fails at
// random is worse than no visual check, because the team learns to ignore it.

const FREEZE_CSS = FREEZE_ANIMATIONS_CSS + `
  html { scrollbar-width: none; }
  ::-webkit-scrollbar { display: none !important; }
`;

const STUB_JS = `
  // Dates and randomness are the two things that differ between two runs of
  // the same code. Pin both before any page script runs.
  const FIXED = new Date('2020-01-02T03:04:05.000Z').getTime();
  const RealDate = Date;
  function FrozenDate(...args) {
    return args.length ? new RealDate(...args) : new RealDate(FIXED);
  }
  FrozenDate.prototype = RealDate.prototype;
  FrozenDate.now = () => FIXED;
  FrozenDate.parse = RealDate.parse;
  FrozenDate.UTC = RealDate.UTC;
  globalThis.Date = FrozenDate;
  let seed = 0x2f6e2b1;
  Math.random = () => {
    seed ^= seed << 13; seed ^= seed >>> 17; seed ^= seed << 5;
    return ((seed >>> 0) % 1e6) / 1e6;
  };
`;

// ---------------------------------------------------------------------------
// A cell's computed style — runs in the page. Every element of the cell, the
// cell included, with its ::before and ::after, as one string. Properties
// that never change a pixel (the cursor, pointer events, selection, motion
// timing) are left out, so a state that changes only those has no style.
const STYLE_SIGNATURE_FN = (id) => {
  const SKIP = /^(cursor|pointer-events|user-select|-webkit-user-select|touch-action|will-change|transition|animation)/;
  const cell = document.querySelector(`[data-cell-id="${CSS.escape(id)}"]`);
  if (!cell) return null;
  const style = (el, pseudo) => {
    const cs = getComputedStyle(el, pseudo);
    const out = [];
    for (let i = 0; i < cs.length; i++) {
      if (!SKIP.test(cs[i])) out.push(`${cs[i]}:${cs.getPropertyValue(cs[i])}`);
    }
    return out.join(';');
  };
  const parts = [];
  const walk = (el) => {
    parts.push(el.tagName, style(el, null), style(el, '::before'), style(el, '::after'));
    for (const child of el.children) walk(child);
  };
  walk(cell);
  return parts.join('\n');
};

// The comparator — runs in the browser, on a canvas.
// ---------------------------------------------------------------------------
// Per-pixel RGB equality is the wrong metric: it treats a 1/255 shift in a
// shadow as identical in weight to a button turning red, and it treats a
// one-pixel text reflow as a catastrophe. This uses the YIQ colour-difference
// metric (luma weighted far above chroma, because that is how eyes work) plus a
// 3x3 neighbourhood escape so sub-pixel antialiasing does not count.

const COMPARE_FN = async ({ aURL, bURL, pixelThreshold }) => {
  const load = async (url) => {
    const bmp = await createImageBitmap(await (await fetch(url)).blob());
    const c = new OffscreenCanvas(bmp.width, bmp.height);
    const ctx = c.getContext('2d', { willReadFrequently: true });
    ctx.drawImage(bmp, 0, 0);
    return { w: bmp.width, h: bmp.height, d: ctx.getImageData(0, 0, bmp.width, bmp.height).data };
  };
  const A = await load(aURL);
  const B = await load(bURL);
  if (A.w !== B.w || A.h !== B.h) {
    return { sizeChanged: true, a: [A.w, A.h], b: [B.w, B.h] };
  }
  const { w, h } = A;
  // Max possible YIQ distance, used to normalise into 0..1.
  const MAX = 35215;
  const at = (d, i) => {
    const a = d[i + 3] / 255;
    // Composite onto white so a transparency change is still a visible change.
    return [
      255 + (d[i] - 255) * a,
      255 + (d[i + 1] - 255) * a,
      255 + (d[i + 2] - 255) * a,
    ];
  };
  const delta = (p, q) => {
    const y = 0.29889531 * (p[0] - q[0]) + 0.58662247 * (p[1] - q[1]) + 0.11448223 * (p[2] - q[2]);
    const i = 0.59597799 * (p[0] - q[0]) - 0.27417610 * (p[1] - q[1]) - 0.32180189 * (p[2] - q[2]);
    const q2 = 0.21147017 * (p[0] - q[0]) - 0.52261711 * (p[1] - q[1]) + 0.31114694 * (p[2] - q[2]);
    return 0.5053 * y * y + 0.299 * i * i + 0.1957 * q2 * q2;
  };
  const tol = pixelThreshold * pixelThreshold * MAX;

  const out = new OffscreenCanvas(w, h);
  const octx = out.getContext('2d');
  const img = octx.createImageData(w, h);
  let mismatched = 0;
  let worst = 0;
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      const i = (y * w + x) * 4;
      const pa = at(A.d, i);
      const pb = at(B.d, i);
      let dv = delta(pa, pb);
      if (dv > tol) {
        // Antialiasing escape: if ANY neighbour in the other image is within
        // tolerance, this is a sub-pixel shift, not a change of design.
        let excused = false;
        for (let dy = -1; dy <= 1 && !excused; dy++) {
          for (let dx = -1; dx <= 1; dx++) {
            const nx = x + dx, ny = y + dy;
            if (nx < 0 || ny < 0 || nx >= w || ny >= h || (dx === 0 && dy === 0)) continue;
            const j = (ny * w + nx) * 4;
            if (delta(pa, at(B.d, j)) <= tol && delta(pb, at(A.d, j)) <= tol) {
              excused = true; break;
            }
          }
        }
        if (!excused) {
          mismatched++;
          if (dv > worst) worst = dv;
          img.data[i] = 255; img.data[i + 1] = 40; img.data[i + 2] = 90; img.data[i + 3] = 255;
          continue;
        }
      }
      // Unchanged pixels: dimmed greyscale, so the red reads instantly.
      const g = 255 - (255 - (pb[0] * 0.3 + pb[1] * 0.59 + pb[2] * 0.11)) * 0.2;
      img.data[i] = g; img.data[i + 1] = g; img.data[i + 2] = g; img.data[i + 3] = 255;
    }
  }
  octx.putImageData(img, 0, 0);
  const blob = await out.convertToBlob({ type: 'image/png' });
  const buf = new Uint8Array(await blob.arrayBuffer());
  let bin = '';
  for (let i = 0; i < buf.length; i++) bin += String.fromCharCode(buf[i]);
  return {
    sizeChanged: false,
    width: w, height: h,
    mismatched, total: w * h,
    ratio: mismatched / (w * h),
    worst: Math.sqrt(worst / MAX),
    diff: btoa(bin),
  };
};

// ---------------------------------------------------------------------------
// Report
// ---------------------------------------------------------------------------

const esc = (s) => String(s).replace(/[&<>"]/g, (c) =>
  ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

function writeReport(outDir, rows, opts, started) {
  const order = { error: 0, new: 1, fail: 2, orphan: 3, pass: 4 };
  const sorted = [...rows].sort((a, b) =>
    (order[a.status] - order[b.status]) || (b.ratio || 0) - (a.ratio || 0));
  const counts = rows.reduce((m, r) => (m[r.status] = (m[r.status] || 0) + 1, m), {});
  const bad = (counts.fail || 0) + (counts.error || 0) + (opts.allowNew ? 0 : counts.new || 0);

  const body = sorted.map((r) => {
    const cells = ['baseline', 'current', 'diff'].map((k) => r[k + 'Rel']
      ? `<figure><img src="${esc(r[k + 'Rel'])}" alt="${esc(k)} ${esc(r.id)}"><figcaption>${k}</figcaption></figure>`
      : `<figure class="empty"><div>—</div><figcaption>${k}</figcaption></figure>`).join('');
    return `<section class="row ${esc(r.status)}">
  <header><span class="badge">${esc(r.status)}</span><code>${esc(r.id)}</code>
  <span class="note">${esc(r.note || '')}</span></header>
  <div class="imgs">${cells}</div>
</section>`;
  }).join('\n');

  const html = `<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Visual regression — ${rows.length} cells</title>
<style>
  :root { color-scheme: light dark; font-family: ui-sans-serif, system-ui, sans-serif; }
  body { margin: 0; padding: 1.5rem; background: Canvas; color: CanvasText; }
  h1 { font-size: 1.25rem; }
  .summary { display: flex; gap: 1rem; flex-wrap: wrap; font: 0.875rem/1.4 ui-monospace, monospace; }
  .summary span { padding: 0.25rem 0.5rem; border: 1px solid; border-radius: 999px; }
  .row { border: 1px solid; border-radius: 0.5rem; padding: 0.75rem; margin-block-start: 0.75rem; }
  .row.pass { opacity: 0.55; }
  .row.fail, .row.error { border-width: 2px; }
  header { display: flex; gap: 0.75rem; align-items: center; flex-wrap: wrap; }
  .badge { font: 600 0.75rem ui-monospace, monospace; text-transform: uppercase;
           padding: 0.125rem 0.5rem; border: 1px solid; border-radius: 999px; }
  .note { font-size: 0.8125rem; opacity: 0.8; }
  code { font: 0.8125rem ui-monospace, monospace; }
  .imgs { display: flex; gap: 0.75rem; flex-wrap: wrap; margin-block-start: 0.5rem; }
  figure { margin: 0; }
  figure img { display: block; max-inline-size: 22rem; border: 1px solid; image-rendering: pixelated; }
  figure.empty div { inline-size: 8rem; block-size: 4rem; display: grid; place-items: center; border: 1px dashed; }
  figcaption { font: 0.75rem ui-monospace, monospace; opacity: 0.7; }
</style></head><body>
<h1>Visual regression report</h1>
<p class="summary">
  <span>sheet ${esc(path.basename(opts.sheet))}</span>
  <span>threshold ${opts.threshold}</span>
  <span>pixel-threshold ${opts.pixelThreshold}</span>
  <span>dpr ${opts.dpr}</span>
  <span>${((Date.now() - started) / 1000).toFixed(1)}s</span>
  ${Object.entries(counts).map(([k, v]) => `<span>${esc(k)} ${v}</span>`).join('')}
  <span>${bad ? 'FAILING' : 'clean'}</span>
</p>
${body}
</body></html>`;
  const p = path.join(outDir, 'index.html');
  fs.writeFileSync(p, html, 'utf8');
  return { path: p, counts, bad };
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main() {
  const opts = parseArgs(process.argv.slice(2));
  const started = Date.now();
  const log = (s) => { if (!opts.quiet) process.stdout.write(s + '\n'); };

  const { chromium } = await loadPlaywright(die, 'node snapshot_matrix.mjs ...');
  const launched = await launchBrowser(chromium, opts.browser, {
    args: ['--force-color-profile=srgb', '--disable-lcd-text',
           '--font-render-hinting=none', '--hide-scrollbars'],
  });
  if (!launched.browser) {
    die('no usable chromium. Tried:\n    ' + launched.tried.join('\n    ') + '\n' +
        '  This script never downloads a browser. Point it at one:\n' +
        '      node snapshot_matrix.mjs sheet.html --browser /path/to/chrome\n' +
        '  or set MATRIX_CHROMIUM.');
  }
  if (launched.auto) log(`browser: ${launched.label}`);
  const browser = launched.browser;
  fs.mkdirSync(opts.baselines, { recursive: true });
  const curDir = path.join(opts.out, 'current');
  const diffDir = path.join(opts.out, 'diff');
  fs.mkdirSync(curDir, { recursive: true });
  fs.mkdirSync(diffDir, { recursive: true });
  const context = await browser.newContext({
    viewport: opts.viewport,
    deviceScaleFactor: opts.dpr,
    reducedMotion: 'reduce',
    forcedColors: 'none',
    colorScheme: 'light',   // the sheet sets data-theme itself; never inherit the OS
    locale: 'en-US',
    timezoneId: 'UTC',
    // A strict Content-Security-Policy refuses the injected freeze
    // stylesheet; the capture is of the sheet, not of its CSP (GT-A5).
    bypassCSP: true,
  });
  await context.addInitScript(STUB_JS);

  const page = await context.newPage();
  await page.goto(pathToFileURL(path.resolve(opts.sheet)).href, { waitUntil: 'load' });
  await page.addStyleTag({ content: FREEZE_CSS });
  await page.evaluate(async () => {
    if (document.fonts && document.fonts.ready) await document.fonts.ready;
    if (typeof window.matrixShowAll === 'function') window.matrixShowAll();
  });
  // Two frames: one for the style tag, one for the relayout it caused.
  await page.evaluate(() => new Promise((r) =>
    requestAnimationFrame(() => requestAnimationFrame(r))));

  let ids = await page.$$eval('[data-cell-id]', (els) =>
    els.map((e) => e.getAttribute('data-cell-id')));
  if (!ids.length) {
    await browser.close();
    die(`${opts.sheet} contains no [data-cell-id] elements. Generate it with ` +
        'generate_matrix.py, or point at the right file.');
  }
  if (opts.only.length) ids = ids.filter((id) => opts.only.some((s) => id.includes(s)));
  if (!ids.length) {
    await browser.close();
    die(`--only ${opts.only.join(', ')} matched no cells.`);
  }

  const cmp = await context.newPage();
  await cmp.goto('about:blank');

  const rows = [];
  const seen = new Set();
  const shots = new Map();        // id -> PNG buffer, for the state-vs-default check
  for (const id of ids) {
    seen.add(id);
    const file = `${id}.png`;
    const basePath = path.join(opts.baselines, file);
    const curPath = path.join(curDir, file);
    let buf;
    try {
      const el = await page.$(`[data-cell-id="${CSS_escape(id)}"]`);
      if (!el) throw new Error('element vanished between enumeration and capture');
      buf = await el.screenshot({ animations: 'disabled', caret: 'hide' });
    } catch (err) {
      rows.push({ id, status: 'error', note: err.message });
      continue;
    }
    fs.writeFileSync(curPath, buf);
    shots.set(id, buf);

    if (opts.update) {
      fs.writeFileSync(basePath, buf);
      rows.push({ id, status: 'pass', note: 'baseline written',
                  currentRel: path.relative(opts.out, curPath) });
      continue;
    }
    if (!fs.existsSync(basePath)) {
      rows.push({ id, status: 'new',
                  note: 'no baseline — review it, then re-run with --update-baselines',
                  currentRel: path.relative(opts.out, curPath) });
      continue;
    }

    const aURL = 'data:image/png;base64,' + fs.readFileSync(basePath).toString('base64');
    const bURL = 'data:image/png;base64,' + buf.toString('base64');
    const res = await cmp.evaluate(COMPARE_FN,
      { aURL, bURL, pixelThreshold: opts.pixelThreshold });

    if (res.sizeChanged) {
      rows.push({ id, status: 'fail', ratio: 1,
                  note: `size changed ${res.a.join('x')} → ${res.b.join('x')}`,
                  baselineRel: path.relative(opts.out, basePath),
                  currentRel: path.relative(opts.out, curPath) });
      continue;
    }
    const diffPath = path.join(diffDir, file);
    fs.writeFileSync(diffPath, Buffer.from(res.diff, 'base64'));
    const failed = res.ratio > opts.threshold;
    rows.push({
      id,
      status: failed ? 'fail' : 'pass',
      ratio: res.ratio,
      note: `${res.mismatched}/${res.total} px (${(res.ratio * 100).toFixed(3)}%), ` +
            `worst ${(res.worst * 100).toFixed(1)}%`,
      baselineRel: path.relative(opts.out, basePath),
      currentRel: path.relative(opts.out, curPath),
      diffRel: failed ? path.relative(opts.out, diffPath) : undefined,
    });
  }

  // A hover, active or focus-visible cell whose every element, ::before and
  // ::after included, computes the same style as in its default cell has no
  // style for that state. That needs no baseline: it is wrong on the first
  // run, and a baseline recorded from it would enshrine it. Styles, not
  // pixels: the cells sit side by side at different subpixel offsets, and on
  // Linux and macOS text is antialiased by where it sits, so twin cells never
  // match pixel for pixel there.
  const STATE_SEG = /--st_(hover|active|focus-visible)(?=--|$)/;
  for (const id of shots.keys()) {
    const m = STATE_SEG.exec(id);
    if (!m) continue;
    const defaultId = id.replace(STATE_SEG, '--st_default');
    if (!shots.has(defaultId)) continue;
    const mine = await page.evaluate(STYLE_SIGNATURE_FN, id);
    if (mine === null || mine !== await page.evaluate(STYLE_SIGNATURE_FN, defaultId)) continue;
    const note = `computes the same style as ${defaultId}: the ${m[1]} state has no visible style`;
    const row = rows.find((r) => r.id === id);
    if (row) {
      row.status = 'fail';
      row.note = row.note ? `${note}; ${row.note}` : note;
    } else {
      rows.push({ id, status: 'fail', note });
    }
  }

  // Baselines with no cell: either a cell was renamed or a component was
  // dropped. Silently ignoring them is how a baseline directory becomes noise.
  for (const f of fs.readdirSync(opts.baselines)) {
    if (!f.endsWith('.png')) continue;
    const id = f.slice(0, -4);
    if (seen.has(id)) continue;
    if (opts.only.length && !opts.only.some((s) => id.includes(s))) continue;
    if (opts.update && opts.prune) {
      fs.unlinkSync(path.join(opts.baselines, f));
      continue;
    }
    rows.push({ id, status: 'orphan',
                note: 'baseline with no matching cell — renamed or removed; ' +
                      're-run with --update-baselines --prune to drop it',
                baselineRel: path.relative(opts.out, path.join(opts.baselines, f)) });
  }

  await browser.close();
  const { path: reportPath, counts, bad } = writeReport(opts.out, rows, opts, started);

  log(`snapshot_matrix: ${rows.length} cell(s) — ` +
      Object.entries(counts).map(([k, v]) => `${k} ${v}`).join(', '));
  for (const r of rows) {
    if (r.status === 'fail' || r.status === 'error' || r.status === 'new') {
      log(`  ${r.status.padEnd(6)} ${r.id}  ${r.note}`);
    }
  }
  log(`  report: ${reportPath}`);
  if (opts.update) log('  baselines updated. Look at them before you commit them.');

  process.exit(bad ? 1 : 0);
}

// Minimal CSS.escape for attribute selectors; the ids are already slugified by
// the generator, so this only has to survive the characters it actually emits.
function CSS_escape(s) {
  return String(s).replace(/["\\]/g, '\\$&');
}

// 1 means a regression, so a run that failed exits 2 (GT-A5).
main().catch((err) => {
  process.stderr.write(`snapshot_matrix: the run failed: ${err && err.stack ? err.stack : err}\n`);
  process.exit(2);
});
