/**
 * browser_common.mjs — what the suite's browser scripts share:
 * resolving Playwright and a browser from disk, never from the network;
 * freezing animations before a measurement; and reading a JSON file a person
 * may have saved from PowerShell or Notepad.
 *
 * The master copy is shared/browser_common.mjs, at the plugin's root. The
 * scripts/ folders of a11y-audit-runner, component-state-matrix,
 * email-template-system and perf-budget-gate each hold a byte-identical copy,
 * so each skill still runs on its own: change the master, copy it over all
 * four, and
 * tests/test_browser_scripts.py fails until they match. (GT-C13: the copies
 * had drifted. a11y_runtime shortened animations without pausing them, so a
 * spinner beside a button with no focus ring counted as a ring.)
 */

import { execSync } from 'node:child_process';
import { pathToFileURL } from 'node:url';
import fs from 'node:fs';
import path from 'node:path';

export const DEFAULT_BROWSER = '/opt/pw-browsers/chromium';

// Animations stop where they are and transitions finish at once, so two
// screenshots of one state differ only where the state does. A shortened but
// running animation keeps moving: an infinite spinner changes pixels between
// any two shots.
export const FREEZE_ANIMATIONS_CSS = `
  *, *::before, *::after {
    animation-play-state: paused !important;
    animation-delay: -1ms !important;
    animation-duration: 1ms !important;
    transition-duration: 1ms !important;
    transition-delay: 0ms !important;
    caret-color: transparent !important;
    scroll-behavior: auto !important;
  }
`;

// `example` is how the calling script is run, for the error message.
export async function loadPlaywright(die, example) {
  const tried = [];
  try {
    return await import('playwright');
  } catch (err) { tried.push(`import 'playwright' — ${err.code || err.message}`); }

  const roots = [];
  if (process.env.NODE_PATH) roots.push(...process.env.NODE_PATH.split(path.delimiter));
  roots.push(...nodeModulesAbove(process.cwd()), npmGlobalRoot());

  for (const root of roots.filter(Boolean)) {
    for (const entry of ['index.mjs', 'index.js']) {
      const p = path.join(root, 'playwright', entry);
      if (!fs.existsSync(p)) continue;
      try {
        return await import(pathToFileURL(p).href);
      } catch (err) { tried.push(`${p} — ${err.message}`); }
    }
  }
  die(
    'cannot load the `playwright` module.\n' +
    '  Install it without pulling a browser down:\n' +
    '      PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 npm i -D playwright\n' +
    '  or point NODE_PATH at a global install:\n' +
    `      NODE_PATH="$(npm root -g)" ${example}\n` +
    '  Tried:\n    ' + tried.join('\n    ')
  );
}

// npm is npm.cmd on Windows, which execFile cannot start without a shell;
// execSync always goes through one.
let npmRoot;
export function npmGlobalRoot() {
  if (npmRoot === undefined) {
    try {
      npmRoot = execSync('npm root -g', {
        encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'], timeout: 20000,
      }).trim();
    } catch { npmRoot = ''; }   // npm may not be on PATH; that is fine
  }
  return npmRoot;
}

// A bare import('playwright') only searches upward from this script, which
// lives in the plugin, not in the project under test.
export function nodeModulesAbove(dir) {
  const found = [];
  for (let d = path.resolve(dir); ; d = path.dirname(d)) {
    found.push(path.join(d, 'node_modules'));
    if (path.dirname(d) === d) return found;
  }
}

// The browser is never downloaded. An explicit path must exist and start;
// otherwise the first of these that starts wins: the sandbox default, the
// browser Playwright itself would launch (its own Chromium or headless shell,
// if installed), an installed Chrome or Edge. Each is tried in turn because an
// installed browser can still fail to start.
export async function launchBrowser(chromium, explicit, options) {
  const candidates = explicit ? [explicit]
    : [...(fs.existsSync(DEFAULT_BROWSER) ? [DEFAULT_BROWSER] : []), undefined,
       ...installedBrowsers().filter((p) => fs.existsSync(p))];
  const tried = [];
  for (const exe of candidates) {
    const label = exe || "Playwright's own Chromium";
    if (exe && !fs.existsSync(exe)) { tried.push(`${label}: no such file`); continue; }
    try {
      return { browser: await chromium.launch({ ...options, executablePath: exe }),
               label, auto: !explicit };
    } catch (err) {
      tried.push(`${label}: ${String(err.message || err).split('\n')[0]}`);
    }
  }
  return { tried };
}

export function installedBrowsers() {
  if (process.platform === 'win32') {
    const env = process.env;
    return [env.PROGRAMFILES, env['PROGRAMFILES(X86)'], env.LOCALAPPDATA].filter(Boolean)
      .flatMap((root) => [
        path.join(root, 'Google', 'Chrome', 'Application', 'chrome.exe'),
        path.join(root, 'Microsoft', 'Edge', 'Application', 'msedge.exe'),
      ]);
  }
  if (process.platform === 'darwin') {
    return ['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
            '/Applications/Chromium.app/Contents/MacOS/Chromium',
            '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge'];
  }
  return ['/usr/bin/chromium', '/usr/bin/chromium-browser', '/usr/bin/google-chrome',
          '/usr/bin/google-chrome-stable', '/snap/bin/chromium', '/usr/bin/microsoft-edge'];
}

// A budget or keymap saved by PowerShell (`>`, Out-File) or Notepad is UTF-16
// or starts with a byte-order mark, and JSON.parse rejects both. It may also
// be JSONC: perf-budget-gate's docs put the device and network in a comment,
// so comments and trailing commas are dropped outside strings, as
// perf_audit.py does.
export function readJsonFile(file) {
  const buf = fs.readFileSync(file);
  const utf16 = buf[0] === 0xFF && buf[1] === 0xFE;
  const text = buf.toString(utf16 ? 'utf16le' : 'utf8').replace(/^﻿/, '');
  let out = '';
  let code = '';
  const flush = () => { out += code.replace(/,(\s*[}\]])/g, '$1'); code = ''; };
  for (let i = 0; i < text.length;) {
    if (text[i] === '"') {
      let j = i + 1;
      while (j < text.length && text[j] !== '"') j += text[j] === '\\' ? 2 : 1;
      flush();
      out += text.slice(i, j + 1);
      i = j + 1;
    } else if (text.startsWith('//', i)) {
      const j = text.indexOf('\n', i);
      i = j < 0 ? text.length : j;
    } else if (text.startsWith('/*', i)) {
      const j = text.indexOf('*/', i + 2);
      i = j < 0 ? text.length : j + 2;
    } else {
      code += text[i++];
    }
  }
  flush();
  return JSON.parse(out);
}
