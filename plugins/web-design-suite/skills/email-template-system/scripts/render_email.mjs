#!/usr/bin/env node
/**
 * render_email.mjs — a built email as three kinds of client show it (DL-C3).
 *
 *   light    the email as authored, with prefers-color-scheme: light
 *   dark     the same, with prefers-color-scheme: dark, so the retained dark
 *            block applies, as in Apple Mail and the Outlook apps
 *   nostyle  every <style> element removed, as Gmail's app does with a
 *            non-Google account: only the inline styles are left
 *
 * Each is a full-page PNG at a phone's width (375px unless --width), and each
 * reports the page's width against the viewport: a page wider than the screen
 * makes the reader scroll sideways. lint_email.py's `dark` and `nostyle`
 * checks find the same failures without a browser; this shows them.
 *
 * Nothing is fetched: images keep their declared size and show their alt
 * text, so a run is the same offline and on every machine.
 *
 * The browser is found the way the suite's other browser scripts find it
 * (browser_common.mjs) and is NEVER downloaded: --browser PATH, else
 * EMAIL_CHROMIUM, else Playwright's own Chromium, else an installed Chrome or
 * Edge.
 *
 * USAGE
 *   node render_email.mjs build/receipt.html
 *   node render_email.mjs build/receipt.html --out shots --width 320 --json
 *
 * Exit codes: 0 every mode fits · 1 a mode is wider than the viewport ·
 * 2 bad invocation, no browser, or a run that failed.
 */

import fs from 'node:fs';
import path from 'node:path';
import { launchBrowser, loadPlaywright } from './browser_common.mjs';

function die(message) {
  process.stderr.write(`render_email: ${message}\n`);
  process.exit(2);
}

const MODES = [
  { name: 'light', colorScheme: 'light', strip: false },
  { name: 'dark', colorScheme: 'dark', strip: false },
  { name: 'nostyle', colorScheme: 'light', strip: true },
];

function parseArgs(argv) {
  const opts = { file: null, out: 'email-renders', width: 375, browser: process.env.EMAIL_CHROMIUM || '',
                 json: false };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    const need = () => {
      if (i + 1 >= argv.length) die(`${a} needs a value`);
      return argv[++i];
    };
    if (a === '--out') opts.out = need();
    else if (a === '--width') {
      opts.width = Number(need());
      if (!Number.isInteger(opts.width) || opts.width < 200) die('--width takes whole pixels, 200 or more');
    } else if (a === '--browser') opts.browser = need();
    else if (a === '--json') opts.json = true;
    else if (a === '-h' || a === '--help') {
      process.stdout.write('usage: node render_email.mjs EMAIL.html [--out DIR] [--width PX] ' +
                           '[--browser PATH] [--json]\n');
      process.exit(0);
    } else if (a.startsWith('-')) die(`unknown option ${a}`);
    else if (opts.file) die('one email at a time');
    else opts.file = a;
  }
  if (!opts.file) die('give the built email: node render_email.mjs build/receipt.html');
  return opts;
}

// What a client that strips <style> receives. A <style> inside a conditional
// comment goes too, which a browser would ignore anyway.
export function stripStyles(html) {
  return html.replace(/<style\b[^>]*>[\s\S]*?<\/style\s*>/gi, '');
}

async function main() {
  const opts = parseArgs(process.argv.slice(2));
  let html;
  try {
    html = fs.readFileSync(opts.file, 'utf8');
  } catch (err) {
    die(`cannot read ${opts.file}: ${err.message}`);
  }
  const { chromium } = await loadPlaywright(die, 'node render_email.mjs ...');
  const launched = await launchBrowser(chromium, opts.browser || undefined, {
    args: ['--force-color-profile=srgb', '--no-sandbox', '--disable-dev-shm-usage'],
  });
  if (!launched.browser) {
    die('no usable chromium. Tried:\n    ' + launched.tried.join('\n    ') + '\n' +
        '  Pass --browser PATH, set EMAIL_CHROMIUM, or install Chrome or Edge.');
  }
  const browser = launched.browser;
  const stem = path.basename(opts.file).replace(/\.html?$/i, '');
  const results = [];
  try {
    fs.mkdirSync(opts.out, { recursive: true });
    for (const mode of MODES) {
      // No bypassCSP: nothing is injected, the email is the page. No
      // JavaScript either: no client runs an email's scripts, and one that ran
      // here could open a WebSocket the http(s) route does not stop
      // (CodeRabbit on #58).
      const context = await browser.newContext({
        viewport: { width: opts.width, height: 800 }, deviceScaleFactor: 1,
        javaScriptEnabled: false,
        colorScheme: mode.colorScheme, locale: 'en-US', timezoneId: 'UTC',
      });
      try {
        const page = await context.newPage();
        await page.route(/^https?:/, (route) => route.abort());
        await page.setContent(mode.strip ? stripStyles(html) : html, { waitUntil: 'load' });
        const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
        const png = path.join(opts.out, `${stem}-${mode.name}.png`);
        await page.screenshot({ path: png, fullPage: true });
        results.push({ mode: mode.name, png, width: opts.width, scrollWidth,
                       fits: scrollWidth <= opts.width });
      } finally {
        await context.close().catch(() => {});
      }
    }
  } catch (err) {
    die(`the render failed: ${String(err.message || err).split('\n')[0]}`);
  } finally {
    await browser.close().catch(() => {});
  }

  if (opts.json) {
    process.stdout.write(JSON.stringify({ file: opts.file, browser: launched.label, results }, null, 2) + '\n');
  } else {
    for (const r of results) {
      process.stdout.write(`${r.mode.padEnd(8)} ${r.fits ? 'fits' : `${r.scrollWidth}px wide on a ${r.width}px screen`}` +
                           `  ${r.png}\n`);
    }
  }
  return results.every((r) => r.fits) ? 0 : 1;
}

main().then((code) => process.exit(code), (err) => die(String(err && err.stack || err)));
