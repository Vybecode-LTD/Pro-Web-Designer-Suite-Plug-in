/**
 * browser_common.mjs — what the suite's browser scripts share:
 * resolving Playwright and a browser from disk, never from the network;
 * freezing animations before a measurement; reading a JSON file a person
 * may have saved from PowerShell or Notepad; reaching a page that needs a
 * wait, steps, a session or a header; reading through shadow roots; running
 * a gate once per page and viewport; and WCAG's contrast ratio.
 *
 * The master copy is shared/browser_common.mjs, at the plugin's root. The
 * scripts/ folders of a11y-audit-runner, component-state-matrix,
 * design-critique-gate, email-template-system and perf-budget-gate each hold
 * a byte-identical copy, with a copy of shared/project_config.mjs beside it,
 * so each skill still runs on its own: change the master, copy it over all
 * five, and tests/test_browser_scripts.py fails until they match. (GT-C13: the copies
 * had drifted. a11y_runtime shortened animations without pausing them, so a
 * spinner beside a button with no focus ring counted as a ring.)
 */

import { execSync, spawnSync } from 'node:child_process';
import { fileURLToPath, pathToFileURL } from 'node:url';
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

// The message a script prints, then exits 2 on, when `out` is one of its
// inputs; null when it is none of them (the owner's audit of 2026-10-14,
// class 5: G4). project_config.py's refuse_overwrite() in Node: an existing
// pair is compared by file identity, any other by its resolved path. A
// file:// URL is its file, and a web URL no file at all (Codex on #136).
export function refuseOverwrite(out, ...inputs) {
  const local = (p) => {
    if (typeof p !== 'string' || !/^[a-z][a-z0-9+.-]+:/i.test(p)) return p;
    if (!/^file:/i.test(p)) return null;
    try { return fileURLToPath(p); } catch { return null; }
  };
  out = local(out);
  inputs = inputs.map(local);
  if (!out || out === '-') return null;
  const id = (p) => { try { const s = fs.statSync(p, { bigint: true }); return `${s.dev}:${s.ino}`; } catch { return null; } };
  const fold = (p) => (process.platform === 'win32' ? p.toLowerCase() : p);
  for (const given of inputs) {
    if (!given || given === '-') continue;
    const [a, b] = [id(out), id(given)];
    const same = a && b ? a === b : fold(path.resolve(out)) === fold(path.resolve(given));
    if (same) return `${out} is the input ${given}: writing there would replace it. Choose another output.`;
  }
  return null;
}

// Reaching the page (P34: GT-B1, GT-B2). At `load` a client-rendered page is
// still an empty shell, a logged-in page has gone to its sign-in, and a
// staging host may want a header. The gates that open a URL take the same
// options:
//   --wait-for SEL        wait until SEL is visible, after the steps
//   --steps FILE          a JSON list of steps, run once the page has loaded
//   --storage-state FILE  Playwright's storageState: cookies and localStorage
//   --header "Name: V"    a request header, sent to the page's own origin
//                         only, never to a third party; "env:NAME" reads V
//                         from the environment, keeping a token off the
//                         command line (repeatable)
// A step is an object with one action:
//   {"click": SEL}   {"fill": SEL, "value": TEXT}   {"fill": SEL, "env": NAME}
//   {"press": KEY}   {"press": KEY, "on": SEL}   {"goto": URL}   {"wait-for": SEL}
// A goto is resolved against the page's URL. A step that cannot run stops the
// run with exit 2: a page never reached is not audited.
export const NAV_OPTIONS = ['--wait-for', '--steps', '--storage-state', '--header'];
export const STEP_TIMEOUT = 15000;
export const WAIT_FOR_TIMEOUT = 30000;
const STEP_FIELDS = { click: [], fill: ['value', 'env'], press: ['on'], goto: [], 'wait-for': [] };
const HEADER_NAME = /^[!#$%&'*+.^_`|~0-9A-Za-z-]+$/;
const ENV_NAME = /^[A-Za-z_][A-Za-z0-9_]*$/;

export function newNav() {
  return { waitFor: null, stepsFile: null, stateFile: null, headers: [] };
}

// Records one of NAV_OPTIONS. Returns the message to exit 2 on, or null.
export function takeNavOption(nav, flag, value) {
  const once = { '--wait-for': 'waitFor', '--steps': 'stepsFile', '--storage-state': 'stateFile' }[flag];
  if (once) {
    if (nav[once] !== null) return `${flag} is given twice`;
    if (!value.trim()) return `${flag} needs a value`;
    nav[once] = value;
    return null;
  }
  if (flag !== '--header') return `${flag} is not one of ${NAV_OPTIONS.join(', ')}`;
  const colon = value.indexOf(':');
  const name = colon < 0 ? '' : value.slice(0, colon).trim();
  if (!HEADER_NAME.test(name)) return `--header takes "Name: value", got "${value}"`;
  if (nav.headers.some(([n]) => n.toLowerCase() === name.toLowerCase())) return `--header ${name} is given twice`;
  nav.headers.push([name, value.slice(colon + 1).trim()]);
  return null;
}

function stepProblem(step, n) {
  if (!step || typeof step !== 'object' || Array.isArray(step)) return `step ${n} is not an object`;
  const actions = Object.keys(step).filter((k) => Object.hasOwn(STEP_FIELDS, k));
  if (actions.length !== 1) return `step ${n} needs exactly one of ${Object.keys(STEP_FIELDS).join(', ')}`;
  const [action] = actions;
  const extra = Object.keys(step).filter((k) => k !== action && !STEP_FIELDS[action].includes(k));
  if (extra.length) return `step ${n} (${action}) does not take ${extra.join(', ')}`;
  for (const [key, v] of Object.entries(step)) {
    if (typeof v !== 'string' || (key !== 'value' && !v.trim())) return `step ${n}: ${key} must be a string, and not an empty one`;
  }
  if (action === 'fill' && Object.hasOwn(step, 'value') === Object.hasOwn(step, 'env')) {
    return `step ${n} (fill) needs one of value and env`;
  }
  if (Object.hasOwn(step, 'env')) {
    if (!ENV_NAME.test(step.env)) return `step ${n}: env names a variable, got "${step.env}"`;
    if (process.env[step.env] === undefined) return `step ${n}: the environment has no ${step.env}`;
  }
  return null;
}

// Reads what the options name, before a browser starts: the steps, the
// storage state and each header's value. Returns { nav, problem }; with a
// problem, the script exits 2 on it.
export function readNav(given, target) {
  const nav = { waitFor: given.waitFor, steps: [], storageState: null, headers: [] };
  if (given.headers.length && !/^https?:/i.test(target || '')) {
    return { nav, problem: '--header needs an http(s) URL: a file has no server to send it to' };
  }
  for (const [name, raw] of given.headers) {
    let value = raw;
    const env = /^env:(.*)$/.exec(raw);
    if (env) {
      if (!ENV_NAME.test(env[1])) return { nav, problem: `--header ${name}: env: names a variable, got "${env[1]}"` };
      value = process.env[env[1]];
      if (value === undefined) return { nav, problem: `--header ${name}: the environment has no ${env[1]}` };
    }
    if (/[\r\n]/.test(value)) return { nav, problem: `--header ${name}: a header's value holds no line break` };
    nav.headers.push([name, value]);
  }
  const read = (flag, file) => {
    try { return { data: readJsonFile(file) }; } catch (err) { return { problem: `${flag} ${file}: ${err.message}` }; }
  };
  if (given.stepsFile) {
    const { data, problem } = read('--steps', given.stepsFile);
    if (problem) return { nav, problem };
    if (!Array.isArray(data)) return { nav, problem: `--steps ${given.stepsFile} must hold a JSON list of steps` };
    for (let i = 0; i < data.length; i++) {
      const p = stepProblem(data[i], i + 1);
      if (p) return { nav, problem: `--steps ${given.stepsFile}: ${p}` };
    }
    nav.steps = data;
  }
  if (given.stateFile) {
    const { data, problem } = read('--storage-state', given.stateFile);
    if (problem) return { nav, problem };
    const list = (k) => data[k] === undefined || Array.isArray(data[k]);
    if (!data || typeof data !== 'object' || Array.isArray(data) || !list('cookies') || !list('origins')) {
      return { nav, problem: `--storage-state ${given.stateFile} is not Playwright's storageState: an object whose cookies and origins are lists` };
    }
    nav.storageState = { cookies: data.cookies ?? [], origins: data.origins ?? [] };
  }
  return { nav, problem: null };
}

// The browser context's options for a read nav.
export function navContext(nav) {
  return nav.storageState ? { storageState: nav.storageState } : {};
}

// Sends the headers with every request to `url`'s origin, from this page.
export async function routeHeaders(page, url, nav) {
  if (!nav.headers.length) return;
  const origin = new URL(url).origin;
  const extra = Object.fromEntries(nav.headers);
  await page.route('**/*', (route) => {
    const req = route.request();
    let same = false;
    try { same = new URL(req.url()).origin === origin; } catch { /* no origin: data:, blob: */ }
    return same ? route.continue({ headers: { ...req.headers(), ...extra } }) : route.continue();
  });
}

// Waits for --wait-for's selector. Throws with the selector named.
export async function waitForNav(page, nav) {
  if (!nav.waitFor) return;
  try {
    await page.waitForSelector(nav.waitFor, { state: 'visible', timeout: WAIT_FOR_TIMEOUT });
  } catch (err) {
    throw new Error(`--wait-for ${nav.waitFor} never appeared: ${err.message.split('\n')[0]}`);
  }
}

// Opens `url` and does what the options ask: the headers, the steps, then the
// wait. Returns the first navigation's response. A failed step throws, named.
export async function arrive(page, url, nav, { waitUntil = 'load', timeout = 45000 } = {}) {
  await routeHeaders(page, url, nav);
  const resp = await page.goto(url, { waitUntil, timeout });
  for (const [i, step] of nav.steps.entries()) {
    const action = Object.keys(step).find((k) => Object.hasOwn(STEP_FIELDS, k));
    try {
      if (action === 'click') await page.click(step.click, { timeout: STEP_TIMEOUT });
      else if (action === 'fill') {
        await page.fill(step.fill, step.env ? process.env[step.env] : step.value, { timeout: STEP_TIMEOUT });
      } else if (action === 'press') {
        if (step.on) await page.press(step.on, step.press, { timeout: STEP_TIMEOUT });
        else await page.keyboard.press(step.press);
      } else if (action === 'goto') await page.goto(new URL(step.goto, page.url()).href, { waitUntil, timeout });
      else await page.waitForSelector(step['wait-for'], { state: 'visible', timeout: STEP_TIMEOUT });
    } catch (err) {
      // A fill's value is never repeated: it may be a password.
      throw new Error(`step ${i + 1} (${action} ${step[action]}) failed: ${err.message.split('\n')[0]}`);
    }
  }
  if (nav.steps.length) await page.waitForLoadState('load', { timeout });
  await waitForNav(page, nav);
  return resp;
}

// ---------------------------------------------------------------------------
// Shadow DOM (P34, GT-B3)
// ---------------------------------------------------------------------------
//
// querySelectorAll stops at a shadow root, so a web-component library's
// controls were never named, measured or tabbed to by the suite's own checks.
// DEEP_DOM runs in the page and sets window.__wdsDeep: the elements and text
// of the composed tree, through each open root and each closed one this page
// kept, in the order the browser renders and tabs through them (a slot stands
// for what is assigned to it). As an init script it runs before the page's
// own, so its attachShadow keeps every root a script makes, closed ones
// included; keepClosedRoots() hands it the closed roots the parser attached
// before any script ran (<template shadowrootmode="closed">).
export const DEEP_DOM = () => {
  if (window.__wdsDeep) return;
  const kept = new WeakMap();
  const attach = Element.prototype.attachShadow;
  if (attach) {
    Element.prototype.attachShadow = function attachShadow(init) {
      const root = attach.call(this, init);
      kept.set(this, root);
      return root;
    };
  }
  const keep = (root) => {
    if (!root || !root.host) return false;
    kept.set(root.host, root);
    return true;
  };
  // The root an element hosts: open, kept here, or kept by its own frame.
  const shadowOf = (el) => {
    if (!el || el.nodeType !== 1) return null;
    if (el.shadowRoot) return el.shadowRoot;
    const own = kept.get(el);
    if (own) return own;
    try {
      const w = el.ownerDocument.defaultView;
      return w && w !== window && w.__wdsDeep ? w.__wdsDeep.shadowOf(el) : null;
    } catch { return null; }
  };
  // A node's children as the browser renders them: a host's are its root's,
  // and a slot's are what is assigned to it, else its own fallback.
  const flatChildren = (node) => {
    if (node.nodeType === 1) {
      const root = shadowOf(node);
      if (root) return root.childNodes;
      if (node.localName === 'slot' && typeof node.assignedNodes === 'function') {
        const assigned = node.assignedNodes();
        if (assigned.length) return assigned;
      }
    }
    return node.childNodes;
  };
  // Calls visit(node, parent) on every node below `node`, in order, without
  // recursing (a deep page would overflow the stack).
  const walk = (node, visit) => {
    const stack = [];
    const push = (parent) => {
      const kids = flatChildren(parent);
      for (let i = kids.length - 1; i >= 0; i--) stack.push([kids[i], parent]);
    };
    push(node);
    while (stack.length) {
      const [n, parent] = stack.pop();
      visit(n, parent);
      if (n.nodeType === 1) push(n);
    }
  };
  // Every element below `root`; for a document (the default), its root
  // element too, as document.querySelectorAll('*') gives it.
  const all = (root) => {
    const out = [];
    let from = root || document;
    if (from.nodeType === 9) {
      if (!from.documentElement) return out;
      from = from.documentElement;
      out.push(from);
    }
    walk(from, (n) => { if (n.nodeType === 1) out.push(n); });
    return out;
  };
  const query = (root, selector) => all(root).filter((el) => el.matches(selector));
  // Each text node below `root` (the body by default), with the element it
  // renders in: a slot, for text assigned to one.
  const texts = (root) => {
    const out = [];
    const from = root || document.body;
    if (from) walk(from, (n, parent) => { if (n.nodeType === 3) out.push([n, parent]); });
    return out;
  };
  // The slot a node is assigned to. assignedSlot is null in a closed root, so
  // a kept closed root's slots are asked.
  const slotOf = (n) => {
    if (n.assignedSlot) return n.assignedSlot;
    const host = n.parentElement;
    const root = host && !host.shadowRoot ? kept.get(host) : null;
    if (!root) return null;
    for (const s of root.querySelectorAll('slot')) {
      if (s.assignedNodes().includes(n)) return s;
    }
    return null;
  };
  // The element a node renders inside: its slot, its parent, or the host of
  // the root it is at the top of.
  const parentOf = (n) => {
    if (!n) return null;
    const slot = slotOf(n);
    if (slot) return slot;
    if (n.parentElement) return n.parentElement;
    const p = n.parentNode;
    return p && p.nodeType === 11 && p.host ? p.host : null;
  };
  const contains = (a, b) => {
    for (let n = b; n; n = parentOf(n)) if (n === a) return true;
    return false;
  };
  const closest = (el, selector) => {
    for (let n = el; n; n = parentOf(n)) if (n.nodeType === 1 && n.matches(selector)) return n;
    return null;
  };
  // A slot draws no box of its own; the element that does.
  const boxOf = (el) => {
    let n = el;
    while (n && n.localName === 'slot') n = parentOf(n);
    return n;
  };
  // The focused element itself, not the host that stands for it outside.
  const active = (doc) => {
    let el = (doc || document).activeElement;
    for (let root = shadowOf(el); root && root.activeElement; root = shadowOf(el)) {
      el = root.activeElement;
    }
    return el;
  };
  // Every shadow root in the composed tree, open and kept.
  const roots = () => all(document).map(shadowOf).filter(Boolean);
  // The element a path names: one selector per tree, joined by ' >> ' at each
  // shadow boundary (as a11y_runtime's cssPath() writes them; Playwright
  // chains them the same way through open roots). A selector with no
  // boundary is looked for in the document first, then through every root. A
  // bad selector throws, as querySelector does.
  const resolve = (path) => {
    if (!path) return null;
    const parts = String(path).split(' >> ');
    let el = document.querySelector(parts[0]);
    if (!el && parts.length === 1) el = query(document, parts[0])[0] || null;
    for (const part of parts.slice(1)) {
      const root = shadowOf(el);
      el = root ? root.querySelector(part) : null;
      if (!el) return null;
    }
    return el;
  };
  window.__wdsDeep = { keep, shadowOf, flatChildren, all, query, texts, parentOf,
                       contains, closest, boxOf, active, roots, resolve };
};

// Hands every closed shadow root in the page's document to DEEP_DOM, which
// must already be in the page, through the DevTools protocol (Chromium):
// DOM.getDocument with `pierce` lists them, the parser's among them, and
// DOM.resolveNode gives each to the page. A frame's document is left to axe,
// as the checks leave it. Returns { closed, kept }, or null where the
// protocol is not available. A closed root not kept is one no check read.
export async function keepClosedRoots(page) {
  let cdp;
  try { cdp = await page.context().newCDPSession(page); } catch { return null; }
  try {
    const { root } = await cdp.send('DOM.getDocument', { depth: -1, pierce: true });
    const closed = [];
    const stack = [root];
    while (stack.length) {
      const n = stack.pop();
      for (const s of n.shadowRoots || []) {
        if (s.shadowRootType === 'closed') closed.push(s.backendNodeId);
        stack.push(s);
      }
      for (const c of n.children || []) stack.push(c);
    }
    let kept = 0;
    for (const backendNodeId of closed) {
      try {
        const { object } = await cdp.send('DOM.resolveNode', { backendNodeId });
        const { result } = await cdp.send('Runtime.callFunctionOn', {
          objectId: object.objectId, returnByValue: true,
          functionDeclaration: 'function () { const d = this.ownerDocument.defaultView.__wdsDeep; ' +
            'return !!(d && d.keep(this)); }',
        });
        if (result.value === true) kept++;
      } catch { /* gone since it was listed */ }
    }
    return { closed: closed.length, kept };
  } catch {
    return null;
  } finally {
    await cdp.detach().catch(() => {});
  }
}

// What a run says of the closed roots keepClosedRoots() did not keep, so a
// root no check read is never passed in silence; null when it kept them all.
export function unreadRoots(closed) {
  if (closed && closed.closed === closed.kept) return null;
  return closed ? `${closed.closed - closed.kept} closed shadow root(s) could not be read`
    : 'The closed shadow roots in the page could not be listed: the browser offers no ' +
      'DevTools protocol';
}

// The element a cssPath() path names in the page, through shadow roots
// (DEEP_DOM's resolve), or null. A bad selector throws.
export async function elementAt(page, path) {
  const handle = await page.evaluateHandle((p) => window.__wdsDeep.resolve(p), path);
  const el = handle.asElement();
  if (!el) await handle.dispose();
  return el;
}

// ---------------------------------------------------------------------------
// Several pages and viewports (P34, GT-B4)
// ---------------------------------------------------------------------------
//
// A run covers one page at one viewport, and a site is many templates, with
// target size and mobile navigation to check at a phone's width. --urls
// gives a gate a list, and runEach() runs the gate once per page (and per
// viewport) as a child process of its own, so nothing one page leaves in
// the browser reaches the next, then hands back every report for one
// summary whose exit is the worst of them.

export const MAX_URLS = 50;

const XML_ENTITIES = { amp: '&', lt: '<', gt: '>', quot: '"', apos: "'" };
function xmlText(s) {
  return s.replace(/^<!\[CDATA\[([\s\S]*)\]\]>$/, '$1')
    .replace(/&(#x[0-9a-f]+|#\d+|amp|lt|gt|quot|apos);/gi, (m, e) => (e[0] === '#'
      ? String.fromCodePoint(e[1] === 'x' || e[1] === 'X' ? parseInt(e.slice(2), 16) : Number(e.slice(1)))
      : XML_ENTITIES[e.toLowerCase()]));
}

// The pages a --urls value lists: a file of one URL a line (a blank line,
// and a line starting with #, skipped), a JSON list of URLs or of
// {"url", "pageType"}, or a sitemap (<urlset> of <loc>), read from a file or
// fetched from an http(s) URL. Each is an http(s) URL, listed once. Returns
// { pages, leftOut, problem }: past `max`, the rest are left out and
// counted, never dropped in silence.
export async function readUrls(source, max = MAX_URLS) {
  const fail = (why) => ({ pages: [], leftOut: 0, problem: `--urls ${source}: ${why}` });
  let text;
  if (/^https?:\/\//i.test(source)) {
    let resp;
    try { resp = await fetch(source); } catch (err) { return fail(err.message); }
    if (!resp.ok) return fail(`HTTP ${resp.status}`);
    text = await resp.text();
  } else {
    let buf;
    try { buf = fs.readFileSync(source); } catch (err) { return fail(err.code === 'ENOENT' ? 'no such file' : err.message); }
    const utf16 = buf[0] === 0xFF && buf[1] === 0xFE;
    text = buf.toString(utf16 ? 'utf16le' : 'utf8');
  }
  text = text.replace(/^﻿/, '').trim();
  let entries;
  if (text.startsWith('[')) {
    let data;
    try { data = JSON.parse(text); } catch (err) { return fail(`not valid JSON: ${err.message}`); }
    entries = [];
    for (const [i, e] of data.entries()) {
      const object = e && typeof e === 'object' && !Array.isArray(e);
      if (typeof e === 'string') entries.push({ url: e, pageType: null });
      else if (object && typeof e.url === 'string' && (e.pageType == null || typeof e.pageType === 'string')) {
        entries.push({ url: e.url, pageType: e.pageType ?? null });
      } else return fail(`entry ${i + 1} must be a URL or {"url": "...", "pageType": "..."}`);
    }
  } else if (/<sitemapindex[\s>]/i.test(text)) {
    return fail('a sitemap index: give one of the sitemaps it lists');
  } else if (/<urlset[\s>]/i.test(text)) {
    entries = [...text.matchAll(/<loc>\s*([\s\S]*?)\s*<\/loc>/gi)]
      .map((m) => ({ url: xmlText(m[1]).trim(), pageType: null }));
  } else {
    entries = text.split(/\r\n|\r|\n/).map((l) => l.trim())
      .filter((l) => l && !l.startsWith('#')).map((url) => ({ url, pageType: null }));
  }
  const seen = new Set();
  const pages = [];
  for (const e of entries) {
    if (!/^https?:\/\/[^\s]+$/i.test(e.url)) return fail(`"${e.url}" is not an http(s) URL`);
    if (seen.has(e.url)) continue;
    seen.add(e.url);
    pages.push(e);
  }
  if (!pages.length) return fail('lists no URL');
  return { pages: pages.slice(0, max), leftOut: Math.max(0, pages.length - max), problem: null };
}

// A --viewports list, "390x844,1280x900", as [{width, height}], or a
// message naming what is wrong.
export function readViewports(value) {
  const out = [];
  for (const part of String(value).split(',').map((s) => s.trim()).filter(Boolean)) {
    const m = /^(\d+)x(\d+)$/.exec(part);
    if (!m || !Number(m[1]) || !Number(m[2])) {
      return { viewports: [], problem: `--viewports takes a list like 390x844,1280x900; got "${part}"` };
    }
    out.push({ width: Number(m[1]), height: Number(m[2]) });
  }
  if (!out.length) return { viewports: [], problem: '--viewports needs at least one size, like 390x844' };
  return { viewports: out, problem: null };
}

// argv without the options that pick the pages (`valued` take a value), so
// each child run gets everything else the run was given.
export function withoutOptions(argv, valued, flags = []) {
  const out = [];
  for (let i = 0; i < argv.length; i++) {
    if (valued.includes(argv[i])) { i++; continue; }
    if (!flags.includes(argv[i])) out.push(argv[i]);
  }
  return out;
}

// Runs `script` once for each of `runs` (each {args, ...}), one after
// another, since a measurement must not share the machine with another,
// with `base` and --json. Each comes back with its exit and report, or the
// error that stopped it (exit 2). `progress(i, run)` is told before each.
export function runEach(script, base, runs, progress = () => {}) {
  return runs.map((run, i) => {
    progress(i, run);
    const proc = spawnSync(process.execPath, [script, ...base, ...run.args, '--json'],
                           { encoding: 'utf8', maxBuffer: 512 * 1024 * 1024, env: process.env });
    let report = null;
    if (proc.status === 0 || proc.status === 1) {
      try { report = JSON.parse(proc.stdout); } catch { report = null; }
    }
    const error = report ? null : proc.error ? proc.error.message
      : (proc.stderr || '').trim().split('\n').slice(-2).join(' ') || `exit ${proc.status}`;
    return { ...run, exit: report ? proc.status : 2, report, error };
  });
}

// The project contract (P24): a project's .design-suite.json, found and
// checked by project_config.mjs, which sits beside this file as a copy of the
// plugin's shared/project_config.mjs (tests/test_project_config.py holds the
// copies and the Python reader to it).
export { CONFIG_NAME, ConfigError, findConfig, loadConfig, projectConfig } from './project_config.mjs';

// WCAG 2.x: the relative luminance of an sRGB triple (0 to 255 each), and
// the contrast ratio of two, from 1 to 21. Not rounded: a caller that shows
// a ratio rounds it down, so a pair shown at a floor meets it.
function srgbToLin(c) {
  const s = c / 255;
  return s <= 0.04045 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
}
export function luminance([r, g, b]) {
  return 0.2126 * srgbToLin(r) + 0.7152 * srgbToLin(g) + 0.0722 * srgbToLin(b);
}
export function contrastRatio(a, b) {
  const la = luminance(a), lb = luminance(b);
  const hi = Math.max(la, lb), lo = Math.min(la, lb);
  return (hi + 0.05) / (lo + 0.05);
}
