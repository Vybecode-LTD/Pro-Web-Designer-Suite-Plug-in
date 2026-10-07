#!/usr/bin/env node
/**
 * critique_snapshots.mjs — the critique's "needs a human" checks, as files a
 * reviewer (or Claude) can look at (PS-B5, PS-C5).
 *
 *   390.png  1440.png      the page at a phone's width and a desktop's, full
 *                          length: what the five-second test and the phone
 *                          pass look at
 *   1440-blur.png          blurred 8px: the squint test
 *   1440-greyscale.png     no colour: is the hierarchy carried by value?
 *   1440-mirror.png        flipped left to right: balance, with fresh eyes
 *   1440-25.png            at a quarter of its size: rhythm and section beat
 *   390-dark.png  1440-dark.png                     prefers-color-scheme: dark
 *   390-reduced-motion.png  1440-reduced-motion.png prefers-reduced-motion: reduce
 *   contrast.md            every text colour on its background, light and
 *                          dark, at both widths, from computed styles (form
 *                          controls' text and opacity included): the ratio,
 *                          the AA floor for its size, and where it is used
 *
 * They stand in for the checks; they do not replace the people. A 390px
 * capture is not a phone in a hand, a blur is not someone else's first five
 * seconds, and nothing stands in for a night's sleep: CRITIQUE_TEMPLATE.md
 * records each check as run, run with a proxy (and which file), or "not run —
 * needs a human".
 *
 * The blur, greyscale, mirror and 25% views are made from the 1440 capture in
 * a page of their own, so nothing is injected into the page under review and
 * its Content-Security-Policy is left alone. The contrast table walks each
 * text's own ancestors; text over an image, a gradient or a positioned layer
 * that is not its ancestor is listed as not measured: a11y_runtime.mjs
 * measures that case, from pixels.
 *
 * The browser is found the way the suite's other browser scripts find it
 * (browser_common.mjs) and is NEVER downloaded: --browser PATH, else
 * CRITIQUE_CHROMIUM, else Playwright's own Chromium, else an installed Chrome
 * or Edge.
 *
 * USAGE
 *   node critique_snapshots.mjs http://localhost:3000/pricing
 *   node critique_snapshots.mjs build/index.html --out critique-shots --json
 *
 * Exit codes: 0 written, every measured pair meets its AA floor · 1 written,
 * and a measured pair is below its floor · 2 bad invocation, no browser, or a
 * run that failed.
 */

import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { contrastRatio, launchBrowser, loadPlaywright } from './browser_common.mjs';

function die(message) {
  process.stderr.write(`critique_snapshots: ${message}\n`);
  process.exit(2);
}

export const WIDTHS = [390, 1440];
export const MODES = [
  { name: '', colorScheme: 'light', reducedMotion: 'no-preference' },
  { name: 'dark', colorScheme: 'dark', reducedMotion: 'no-preference' },
  { name: 'reduced-motion', colorScheme: 'light', reducedMotion: 'reduce' },
];
// Made from the 1440 capture. The 8px blur and the 25% are the protocol's
// (self-review-protocol.md, step 3).
export const VIEWS = [
  { name: 'blur', style: 'filter: blur(8px)' },
  { name: 'greyscale', style: 'filter: grayscale(1)' },
  { name: 'mirror', style: 'transform: scaleX(-1)' },
  { name: '25', scale: 0.25 },
];
// Which check each file stands in for, and what it cannot tell you.
export const PROXIES = [
  { check: 'Five seconds with someone else', files: ['1440.png', '390.png'],
    limit: 'your eyes, not a stranger\'s: look for five seconds, then write what it is for' },
  { check: 'Squint / blur', files: ['1440-blur.png', '1440-25.png'], limit: '' },
  { check: 'Flip it', files: ['1440-mirror.png'], limit: '' },
  { check: 'Greyscale', files: ['1440-greyscale.png'], limit: '' },
  { check: 'On an actual phone', files: ['390.png', '390-dark.png'],
    limit: 'no thumb, glare, real network or real fonts on the device' },
  { check: 'Dark mode looked at', files: ['1440-dark.png', '390-dark.png'], limit: '' },
  { check: 'prefers-reduced-motion emulated', files: ['1440-reduced-motion.png', '390-reduced-motion.png'],
    limit: 'a still: watch the page move to see what reduce removes' },
  { check: 'Leave it overnight', files: [], limit: 'no proxy: not run — needs a human' },
];

function parseArgs(argv) {
  const opts = { page: null, out: 'critique-shots', browser: process.env.CRITIQUE_CHROMIUM || '',
                 json: false, settle: 300 };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    const need = () => {
      if (i + 1 >= argv.length) die(`${a} needs a value`);
      return argv[++i];
    };
    if (a === '--out') opts.out = need();
    else if (a === '--browser') opts.browser = need();
    else if (a === '--settle') {
      opts.settle = Number(need());
      if (!Number.isInteger(opts.settle) || opts.settle < 0) die('--settle takes whole milliseconds, 0 or more');
    } else if (a === '--json') opts.json = true;
    else if (a === '-h' || a === '--help') {
      process.stdout.write('usage: node critique_snapshots.mjs URL|FILE.html [--out DIR] [--settle MS] ' +
                           '[--browser PATH] [--json]\n');
      process.exit(0);
    } else if (a.startsWith('-')) die(`unknown option ${a}`);
    else if (opts.page) die('one page at a time');
    else opts.page = a;
  }
  if (!opts.page) die('give a page: node critique_snapshots.mjs http://localhost:3000/ or build/index.html');
  return opts;
}

function pageUrl(page) {
  if (/^(https?|file):/i.test(page)) return page;
  if (!fs.existsSync(page)) die(`${page} is neither a URL nor a file`);
  return pathToFileURL(path.resolve(page)).href;
}

// Runs in the page. Every text's colour on the background its own ancestors
// paint, composited as the browser does, as sRGB triples; the ratio is worked
// out in Node with the suite's one copy of the WCAG maths. Text is a text
// node, or what a form control shows: its value, a button input's label, or
// its placeholder (Codex on #71).
const SAMPLE_TEXT = () => {
  const pixel = document.createElement('canvas');
  pixel.width = 1;
  pixel.height = 1;
  const ctx = pixel.getContext('2d', { willReadFrequently: true });
  // A computed colour is serialised in the space it was written in (oklch(),
  // color(), lab()...): painting it into a pixel is the browser's own
  // conversion to sRGB.
  const cache = new Map();
  const parse = (c) => {
    if (!c) return null;
    if (cache.has(c)) return cache.get(c);
    ctx.clearRect(0, 0, 1, 1);
    ctx.fillStyle = 'rgba(0, 0, 0, 0)';
    ctx.fillStyle = c;
    ctx.fillRect(0, 0, 1, 1);
    const d = ctx.getImageData(0, 0, 1, 1).data;
    const out = { r: d[0], g: d[1], b: d[2], a: d[3] / 255 };
    cache.set(c, out);
    return out;
  };
  // Premultiplied layers. `under` puts a layer beneath what is there; `fade`
  // is an element's opacity, which the browser applies to everything the
  // element holds, its own background and its text alike, before the result
  // meets what is behind the element (Codex on #71: a faded text passed).
  const pre = (c) => ({ r: c.r * c.a, g: c.g * c.a, b: c.b * c.a, a: c.a });
  const under = (top, below) => ({
    r: top.r + below.r * (1 - top.a), g: top.g + below.g * (1 - top.a),
    b: top.b + below.b * (1 - top.a), a: top.a + below.a * (1 - top.a),
  });
  const fade = (c, o) => ({ r: c.r * o, g: c.g * o, b: c.b * o, a: c.a * o });
  const probe = document.createElement('div');
  probe.style.backgroundColor = 'Canvas';
  document.documentElement.appendChild(probe);
  const canvasColour = pre(parse(getComputedStyle(probe).backgroundColor));
  probe.remove();

  const where = (el) => {
    const cls = typeof el.className === 'string' ? el.className.trim().split(/\s+/).filter(Boolean)[0] : '';
    return el.tagName.toLowerCase() + (el.id ? `#${el.id}` : cls ? `.${cls}` : '');
  };
  const out = [];
  const sample = (el, colour, label) => {
    const cs = getComputedStyle(el);
    if (cs.visibility !== 'visible' || !el.getClientRects().length) return;
    let text = pre(parse(colour) || { r: 0, g: 0, b: 0, a: 0 });
    let back = { r: 0, g: 0, b: 0, a: 0 };
    let shown = 1;
    let painted = null;
    for (let n = el; n; n = n.parentElement) {
      const ns = getComputedStyle(n);
      // An image only matters where nothing opaque already covers it.
      if (back.a < 1 && ns.backgroundImage && ns.backgroundImage !== 'none') {
        painted = 'an image or gradient';
        break;
      }
      const bg = parse(ns.backgroundColor);
      if (bg && bg.a > 0) {
        text = under(text, pre(bg));
        back = under(back, pre(bg));
      }
      const o = parseFloat(ns.opacity);
      if (o < 1) {
        text = fade(text, o);
        back = fade(back, o);
        shown *= o;
      }
    }
    if (shown === 0) return;
    const row = { where: label, size: parseFloat(cs.fontSize), weight: parseInt(cs.fontWeight, 10) || 400 };
    if (painted) {
      out.push({ ...row, unmeasured: painted });
      return;
    }
    const round = (c) => [Math.round(c.r), Math.round(c.g), Math.round(c.b)];
    out.push({ ...row, fg: round(under(text, canvasColour)), bg: round(under(back, canvasColour)) });
  };

  const seen = new Set();
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let node;
  while ((node = walker.nextNode())) {
    const el = node.parentElement;
    if (!el || seen.has(el) || (node.nodeValue || '').trim().length < 2) continue;
    seen.add(el);
    if (/^(script|style|noscript|template|textarea|select|option)$/i.test(el.tagName)) continue;
    sample(el, getComputedStyle(el).color, where(el));
  }
  const NO_TEXT = /^(hidden|checkbox|radio|range|color|file|image)$/;
  for (const el of document.querySelectorAll('input, textarea, select')) {
    if (el.tagName === 'INPUT' && NO_TEXT.test((el.type || '').toLowerCase())) continue;
    const value = el.tagName === 'SELECT'
      ? (el.selectedOptions[0] ? el.selectedOptions[0].text : '') : el.value;
    if (value.trim()) sample(el, getComputedStyle(el).color, where(el));
    else if (el.placeholder) {
      sample(el, getComputedStyle(el, '::placeholder').color, `${where(el)}::placeholder`);
    }
  }
  return out;
};

const hex = (rgb) => '#' + rgb.map((c) => c.toString(16).padStart(2, '0')).join('');

// WCAG 2.2 SC 1.4.3: 4.5:1, or 3:1 for large-scale text (at least 18pt, or
// 14pt bold: 24px and about 18.66px in CSS pixels).
export function aaFloor(size, weight) {
  return size >= 24 || (size >= 18.66 && weight >= 700) ? 3 : 4.5;
}

export function contrastTable(samples, scheme, width) {
  const view = `${width} ${scheme}`;
  const pairs = new Map();
  for (const s of samples) {
    const key = s.unmeasured ? `unmeasured|${s.unmeasured}|${s.where}`
      : `${hex(s.fg)}|${hex(s.bg)}|${aaFloor(s.size, s.weight)}`;
    const row = pairs.get(key) || (s.unmeasured
      ? { view, width, scheme, text: null, background: s.unmeasured, ratio: null, floor: null, uses: 0, where: [] }
      : { view, width, scheme, text: hex(s.fg), background: hex(s.bg),
          ratio: Math.floor(contrastRatio(s.fg, s.bg) * 100) / 100,
          floor: aaFloor(s.size, s.weight), uses: 0, where: [] });
    row.uses += 1;
    if (row.where.length < 3 && !row.where.includes(s.where)) row.where.push(s.where);
    pairs.set(key, row);
  }
  const rows = [...pairs.values()];
  for (const r of rows) r.passes = r.ratio === null ? null : r.ratio >= r.floor;
  return rows.sort((a, b) => (a.ratio ?? Infinity) - (b.ratio ?? Infinity));
}

export function renderContrast(page, rows) {
  const out = [`# Contrast — ${page}`, '',
               'From computed styles: each text colour on the background its ancestors paint. ' +
               'Ratios are rounded down, so a pair shown at the floor meets it.', '',
               '| View | Text | Background | Ratio | AA floor | Result | Where (uses) |',
               '|---|---|---|---|---|---|---|'];
  for (const r of rows) {
    const where = `${r.where.map((w) => `\`${w}\``).join(', ')} (${r.uses})`;
    out.push(r.ratio === null
      ? `| ${r.view} | — | ${r.background} | — | — | not measured: run a11y_runtime.mjs | ${where} |`
      : `| ${r.view} | \`${r.text}\` | \`${r.background}\` | ${r.ratio.toFixed(2)}:1 | ${r.floor}:1 | ` +
        `${r.passes ? 'meets' : '**below**'} | ${where} |`);
  }
  if (!rows.length) out.push('| — | — | — | — | — | no text on the page | — |');
  return out.join('\n') + '\n';
}

async function capture(page, file) {
  // Chromium's headless shell sometimes refuses a full-page capture ("Unable
  // to capture screenshot") and the next attempt succeeds (#60's Linux CI).
  for (let attempt = 1; ; attempt++) {
    try {
      return await page.screenshot({ path: file, fullPage: true });
    } catch (err) {
      if (attempt >= 3 || !/Unable to capture screenshot/.test(String(err.message))) throw err;
      await page.waitForTimeout(200);
    }
  }
}

async function main() {
  const opts = parseArgs(process.argv.slice(2));
  const url = pageUrl(opts.page);
  const { chromium } = await loadPlaywright(die, 'node critique_snapshots.mjs ...');
  const launched = await launchBrowser(chromium, opts.browser || undefined, {
    args: ['--force-color-profile=srgb', '--no-sandbox', '--disable-dev-shm-usage'],
  });
  if (!launched.browser) {
    die('no usable chromium. Tried:\n    ' + launched.tried.join('\n    ') + '\n' +
        '  Pass --browser PATH, set CRITIQUE_CHROMIUM, or install Chrome or Edge.');
  }
  const browser = launched.browser;
  const shots = [];
  let contrast = [];
  let wide = null;
  try {
    fs.mkdirSync(opts.out, { recursive: true });
    for (const width of WIDTHS) {
      for (const mode of MODES) {
        // Nothing is injected into the page, so its CSP stays in force.
        const context = await browser.newContext({
          viewport: { width, height: width < 768 ? 844 : 900 }, deviceScaleFactor: 1,
          isMobile: width < 768, hasTouch: width < 768,
          colorScheme: mode.colorScheme, reducedMotion: mode.reducedMotion,
          locale: 'en-US', timezoneId: 'UTC',
        });
        try {
          const page = await context.newPage();
          await page.goto(url, { waitUntil: 'load', timeout: 60000 });
          await page.evaluate(async () => { if (document.fonts) await document.fonts.ready; });
          await page.waitForTimeout(opts.settle);
          const name = `${width}${mode.name ? `-${mode.name}` : ''}.png`;
          const png = await capture(page, path.join(opts.out, name));
          // A page with no width=device-width viewport is laid out 980px wide
          // on a phone, and shown zoomed out: the capture shows what a phone
          // does, and the width says why.
          const pageWidth = await page.evaluate(() => document.documentElement.scrollWidth);
          shots.push({ name, width, pageWidth, colorScheme: mode.colorScheme,
                       reducedMotion: mode.reducedMotion });
          if (width === 1440 && mode.name === '') wide = png;
          // Both widths: a breakpoint can show text, or recolour it, at one
          // only (Codex on #71).
          if (mode.name !== 'reduced-motion') {
            contrast = contrast.concat(contrastTable(await page.evaluate(SAMPLE_TEXT), mode.colorScheme, width));
          }
        } finally {
          await context.close().catch(() => {});
        }
      }
    }

    // The derived views: the 1440 capture shown in a page of our own.
    const uri = `data:image/png;base64,${wide.toString('base64')}`;
    for (const view of VIEWS) {
      const width = Math.round(1440 * (view.scale || 1));
      // A short viewport: the full-page capture is then the image's own height.
      const context = await browser.newContext({
        viewport: { width, height: 100 }, deviceScaleFactor: 1, javaScriptEnabled: false,
      });
      try {
        const page = await context.newPage();
        await page.setContent(
          `<!doctype html><body style="margin:0"><img alt="" src="${uri}" ` +
          `style="display:block;width:${width}px;${view.style || ''}"></body>`, { waitUntil: 'load' });
        const name = `1440-${view.name}.png`;
        await capture(page, path.join(opts.out, name));
        shots.push({ name, width, view: view.name });
      } finally {
        await context.close().catch(() => {});
      }
    }
    fs.writeFileSync(path.join(opts.out, 'contrast.md'), renderContrast(opts.page, contrast));
  } catch (err) {
    die(`the run failed: ${String(err.message || err).split('\n')[0]}`);
  } finally {
    await browser.close().catch(() => {});
  }

  const below = contrast.filter((r) => r.passes === false);
  const overflow = shots.filter((s) => s.pageWidth > s.width).map((s) => s.name);
  const warnings = [];
  if (overflow.length) {
    warnings.push(`${overflow.join(', ')}: the page is wider than the viewport. With no ` +
                  '<meta name="viewport" content="width=device-width"> a phone lays it out 980px ' +
                  'wide and shows it zoomed out; otherwise something overflows.');
  }
  if (opts.json) {
    process.stdout.write(JSON.stringify({ page: opts.page, browser: launched.label, out: opts.out,
                                          shots, contrast, proxies: PROXIES, warnings }, null, 2) + '\n');
  } else {
    process.stdout.write(`critique_snapshots: ${shots.length} PNGs and contrast.md in ${opts.out}\n\n`);
    for (const p of PROXIES) {
      process.stdout.write(`  ${p.check.padEnd(32)} ${p.files.join(', ') || '—'}` +
                           `${p.limit ? `  (${p.limit})` : ''}\n`);
    }
    process.stdout.write(`\n  contrast: ${contrast.filter((r) => r.passes !== null).length} measured pair(s), ` +
                         `${below.length} below the AA floor, ` +
                         `${contrast.filter((r) => r.passes === null).length} not measured\n`);
    for (const r of below) {
      process.stdout.write(`    ${r.view.padEnd(10)} ${r.text} on ${r.background}  ${r.ratio.toFixed(2)}:1 < ` +
                           `${r.floor}:1  ${r.where.join(', ')}\n`);
    }
    for (const w of warnings) process.stdout.write(`\n  ${w}\n`);
  }
  return below.length ? 1 : 0;
}

main().then((code) => process.exit(code), (err) => die(String(err && err.stack || err)));
