#!/usr/bin/env node
/**
 * a11y_runtime.mjs — layer two of the accessibility gate. A real browser.
 *
 * `a11y_static.py` reads source. This renders it and asks the questions source
 * cannot answer: what is this control's computed accessible name, where does
 * Tab actually go, is the focus ring visible in pixels, does it survive
 * forced-colors, what contrast does this text ACTUALLY have once the overlay
 * above it is composited in.
 *
 * The honest coverage statement, up front
 * ---------------------------------------
 * Automated tools find well under half of the barriers. In the only controlled
 * study with a known denominator — GDS, 2017, a page with 143 deliberately
 * planted failures across 19 categories, ten tools run against it — the best
 * single tool found 37-41%, and 29% of the barriers were found by no tool at
 * all. Deque's widely-quoted 57% is measured differently (by VOLUME of issues
 * across 13,000 real pages, fully automated). By criterion, a tool fully
 * decides 7 of the 55 WCAG 2.2 A and AA criteria and part of 31 more
 * (references/automation-coverage.md §3). All of it points one way:
 *
 *   A clean run here means the machine-checkable subset passes.
 *   It is never, in any report, to any client, "the page is accessible".
 *
 * The value is that the part a machine CAN catch is caught on every commit
 * for free, so the human hours go to the rest, which needs judgement.
 * references/manual-protocol.md is that human pass, and it is not optional.
 *
 * What it runs
 * ------------
 *   axe        axe-core, injected from node_modules (never a CDN), with a
 *              configurable tag set; violations with selector, impact and fix
 *   names      the computed accessible name and role of every interactive
 *              element, flagging empty, duplicate and type-only names
 *   taborder   the REAL tab sequence, with traps, skips and jumps named
 *   focus      focus-indicator visibility MEASURED — the focused and unfocused
 *              element screenshotted and differenced, in pixels and contrast
 *   forced     the same measurement under forced-colors, reporting what vanished
 *              (on a page, both repeat at each data-density its stylesheets name)
 *   contrast   text contrast from computed styles, including the overlay case
 *              that static analysis gets wrong
 *   keys       keyboard traversal against an expected key map from a config file
 *   reflow     400% zoom, a 320px viewport (1.4.10); horizontal scroll at 200%
 *              is a warning, since it does not fail 1.4.4
 *
 * Usage
 * -----
 *   node a11y_runtime.mjs --url http://127.0.0.1:8080/
 *   node a11y_runtime.mjs --file build/index.html --tags wcag2a,wcag2aa,wcag22aa
 *   node a11y_runtime.mjs --url http://127.0.0.1:8080/ --keymap a11y-keymap.json
 *   node a11y_runtime.mjs --matrix build/proof-sheet.html --only "button--"
 *   node a11y_runtime.mjs --url http://127.0.0.1:8080/ --budget a11y-budget.json --json
 *
 * Serve the page over HTTP. `file://` blocks fetch, breaks a page that loads
 * anything, and gives you a document no user will ever get. --file is there for
 * a self-contained artefact (a proof sheet); everything else wants --url.
 *
 * Options
 * -------
 *   --url URL             the page to audit
 *   --file PATH           a local HTML file (opened as file://)
 *   --matrix PATH         a component-state-matrix proof sheet: audit every
 *                         [data-cell-id] cell, so every STATE is audited and
 *                         not merely every page
 *   --tags LIST           axe tag set  (default wcag2a,wcag2aa,wcag21a,
 *                         wcag21aa,wcag22aa,best-practice)
 *   --keymap FILE         expected keyboard behaviour per pattern
 *   --budget FILE         a11y-budget.json; non-zero exit on breach
 *   --only SUBSTR         with --matrix, only cells containing SUBSTR (repeatable);
 *                         it does not pick checks, so a page refuses it
 *   --densities LIST      on a page, the data-density values to measure focus
 *                         at as well (default auto: each one the page's own
 *                         stylesheets name; none turns it off)
 *   --skip CHECK          skip a check: axe names taborder focus forced
 *                         contrast keys reflow  (repeatable)
 *   --max-stops N         how many tab stops to measure focus on   (default 40)
 *   --max-cells N         with --matrix, cap the cells measured    (default 120)
 *   --focus-threshold N   min fraction of pixels a ring must change (default 0.005)
 *   --viewport WxH        viewport                            (default 1280x900)
 *   --dpr N               device pixel ratio                        (default 1)
 *   --axe PATH            axe.min.js to inject
 *   --browser PATH        chromium executable   (default: A11Y_CHROMIUM, else the
 *                         first that starts of /opt/pw-browsers/chromium,
 *                         Playwright's own Chromium, Chrome or Edge)
 *   --json                machine-readable output
 *   --report FILE         also write the --json output to FILE; the text report
 *                         still prints, so a CI log has something a person reads
 *   --quiet
 *
 * The browser is NEVER downloaded, and axe is NEVER fetched from a CDN. Both
 * are resolved from disk and the run fails with instructions if they are not
 * there. A gate that pulls 150MB on every CI run is a gate somebody turns off;
 * a gate that depends on a third-party CDN is a gate that goes red when that
 * CDN does, which teaches the same lesson faster.
 *
 *   PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 npm i -D -E playwright axe-core
 *
 * That uses the Chrome you have. In CI, pin the browser instead: install the
 * Chromium the locked Playwright was built for (npx playwright install
 * chromium), which this script tries first. See SKILL.md, CI wiring.
 *
 * Exit codes
 * ----------
 *   0  no error-severity findings, and inside budget if one was given
 *   1  violations found, or a budget breach
 *   2  bad arguments, no usable browser, no axe-core, the page failed to load,
 *      or the run itself failed: a crash is never a finding
 */

import { createRequire } from 'node:module';
import { pathToFileURL, fileURLToPath } from 'node:url';
import fs from 'node:fs';
import path from 'node:path';

import { FREEZE_ANIMATIONS_CSS, launchBrowser, loadPlaywright, nodeModulesAbove, npmGlobalRoot, readJsonFile } from './browser_common.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const DEFAULT_TAGS = 'wcag2a,wcag2aa,wcag21a,wcag21aa,wcag22aa,best-practice';
const ALL_CHECKS = ['axe', 'names', 'taborder', 'focus', 'forced', 'contrast',
                    'keys', 'reflow'];

const COVERAGE_NOTE =
  'Automated testing finds well under half of the barriers (GDS 2017: the ' +
  'best single tool found 37-41% of 143 planted failures; 29% were found by ' +
  'no tool at all). A clean run is a floor, not a result. Report it as "the ' +
  'automated checks pass", never as "accessible", and run ' +
  'references/manual-protocol.md.';

// ---------------------------------------------------------------------------
// Arguments
// ---------------------------------------------------------------------------

function die(msg, code = 2) {
  process.stderr.write(`a11y_runtime: ${msg}\n`);
  process.exit(code);
}

function parseArgs(argv) {
  const opts = {
    url: null, file: null, matrix: null,
    tags: DEFAULT_TAGS.split(','),
    keymap: null, budget: null,
    only: [], skip: new Set(),
    maxStops: 40, maxCells: 120,
    focusThreshold: 0.005,
    densities: 'auto',
    viewport: { width: 1280, height: 900 },
    dpr: 1,
    axe: null,
    browser: process.env.A11Y_CHROMIUM || '',
    json: false, quiet: false, report: null,
  };
  const need = (i, flag) => {
    if (i + 1 >= argv.length) die(`${flag} needs a value`);
    return argv[i + 1];
  };
  const num = (v, flag) => {
    const n = Number(v);
    if (!Number.isFinite(n)) die(`${flag} needs a number, got "${v}"`);
    return n;
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
      case '--url': opts.url = need(i, a); i++; break;
      case '--file': opts.file = need(i, a); i++; break;
      case '--matrix': opts.matrix = need(i, a); i++; break;
      case '--tags': opts.tags = need(i, a).split(',').map((s) => s.trim())
        .filter(Boolean); i++; break;
      case '--keymap': opts.keymap = need(i, a); i++; break;
      case '--budget': opts.budget = need(i, a); i++; break;
      case '--only': opts.only.push(need(i, a)); i++; break;
      case '--skip': opts.skip.add(need(i, a).toLowerCase()); i++; break;
      case '--max-stops': opts.maxStops = num(need(i, a), a); i++; break;
      case '--max-cells': opts.maxCells = num(need(i, a), a); i++; break;
      case '--focus-threshold': opts.focusThreshold = num(need(i, a), a); i++; break;
      case '--densities': {
        const v = need(i, a).trim(); i++;
        if (v === 'auto' || v === 'none') { opts.densities = v; break; }
        const list = v.split(',').map((d) => d.trim()).filter(Boolean);
        if (!list.length || list.some((d) => !/^[\w-]+$/.test(d))) {
          die(`--densities takes auto, none or a list like compact,spacious; got "${v}"`);
        }
        opts.densities = list;
        break;
      }
      case '--dpr': opts.dpr = num(need(i, a), a); i++; break;
      case '--axe': opts.axe = need(i, a); i++; break;
      case '--browser': opts.browser = need(i, a); i++; break;
      case '--json': opts.json = true; break;
      case '--report': opts.report = need(i, a); i++; break;
      case '--quiet': opts.quiet = true; break;
      case '--viewport': {
        const v = need(i, a); i++;
        const m = /^(\d+)x(\d+)$/.exec(v);
        if (!m) die(`--viewport must look like 1280x900, got "${v}"`);
        opts.viewport = { width: Number(m[1]), height: Number(m[2]) };
        break;
      }
      default:
        if (a.startsWith('-')) die(`unknown option ${a} (try --help)`);
        // A bare argument is the target, so the common invocation works.
        else if (!opts.url && !opts.file && !opts.matrix) {
          if (/^https?:\/\//i.test(a)) opts.url = a; else opts.file = a;
        } else die(`unexpected argument "${a}"`);
    }
  }
  const targets = [opts.url, opts.file, opts.matrix].filter(Boolean);
  if (targets.length === 0) {
    die('needs a target: --url URL, --file PATH or --matrix PROOF-SHEET ' +
        '(try --help)');
  }
  if (targets.length > 1) {
    die('pass exactly one of --url, --file and --matrix; they are three ' +
        'different jobs and combining them would silently audit one of them');
  }
  // Ignoring an option is how a run reports on less than its caller asked for:
  // `--only contrast` on a page used to run every check.
  if (opts.only.length && !opts.matrix) {
    die('--only narrows the cells of a --matrix proof sheet; it does not pick ' +
        'checks. Leave a check out with --skip CHECK.');
  }
  if (Array.isArray(opts.densities) && opts.matrix) {
    die('--densities is for a page: a proof sheet already has a cell per density.');
  }
  for (const s of opts.skip) {
    if (!ALL_CHECKS.includes(s)) {
      die(`--skip "${s}" is not a check. Known: ${ALL_CHECKS.join(', ')}`);
    }
  }
  if (!(opts.maxStops >= 1)) die('--max-stops must be at least 1');
  if (!(opts.focusThreshold >= 0 && opts.focusThreshold <= 1)) {
    die('--focus-threshold must be a fraction between 0 and 1');
  }
  return opts;
}

// ---------------------------------------------------------------------------
// Resolving axe-core from disk, never from the network (Playwright: browser_common.mjs)
// ---------------------------------------------------------------------------

function resolveAxe(explicit) {
  const candidates = [];
  if (explicit) candidates.push(explicit);
  const require_ = createRequire(import.meta.url);
  try { candidates.push(require_.resolve('axe-core/axe.min.js')); } catch { /* not here */ }
  candidates.push(path.join(HERE, 'node_modules/axe-core/axe.min.js'));
  candidates.push(path.join(HERE, '..', 'node_modules/axe-core/axe.min.js'));
  for (const nm of nodeModulesAbove(process.cwd())) {
    candidates.push(path.join(nm, 'axe-core/axe.min.js'));
  }
  if (process.env.NODE_PATH) {
    for (const root of process.env.NODE_PATH.split(path.delimiter)) {
      if (root) candidates.push(path.join(root, 'axe-core/axe.min.js'));
    }
  }
  const globalRoot = npmGlobalRoot();
  if (globalRoot) candidates.push(path.join(globalRoot, 'axe-core/axe.min.js'));

  const tried = [...new Set(candidates.filter(Boolean))];
  for (const c of tried) {
    if (fs.existsSync(c)) return c;
  }
  die(
    'cannot find axe-core on disk.\n' +
    '      npm i -D axe-core\n' +
    '  in the project under test or in this skill\'s scripts/ directory, or\n' +
    '  pass --axe /path/to/axe.min.js.\n' +
    '  This tool deliberately does NOT load axe from a CDN: a CI gate that\n' +
    '  depends on a third-party CDN goes red when that CDN does, and a team\n' +
    '  that has been taught red means "re-run it" is a team with no gate.\n' +
    '  Tried:\n    ' + tried.join('\n    ')
  );
}

// ---------------------------------------------------------------------------
// Findings
// ---------------------------------------------------------------------------

function finding(check, rule, sc, severity, message, fix, extra = {}) {
  return { check, rule, sc, severity, message, fix, ...extra };
}

// Shorten at a word boundary and say so. A hard cut left text like
// "Element do" running straight into the help URL.
function clip(text, max) {
  if (text.length <= max) return text;
  const cut = text.slice(0, max + 1);
  const at = cut.lastIndexOf(' ');
  return `${(at > 0 ? cut.slice(0, at) : text.slice(0, max)).replace(/[\s,;:]+$/, '')} …`;
}

// ---------------------------------------------------------------------------
// In-page helpers, installed before any page script runs
// ---------------------------------------------------------------------------

const HELPERS = () => {
  const FOCUSABLE =
    'a[href],area[href],button,input,select,textarea,summary,iframe,object,' +
    'embed,audio[controls],video[controls],[tabindex],[contenteditable=""],' +
    '[contenteditable="true"]';

  const cssPath = (el) => {
    if (!el || el.nodeType !== 1) return null;
    const parts = [];
    let node = el;
    while (node && node.nodeType === 1 && parts.length < 6) {
      let part = node.nodeName.toLowerCase();
      // A proof sheet nests every cell six divs deep inside a grid inside a
      // pass, and the full path is unreadable and useless. The cell id is the
      // stable identifier that component-state-matrix already guarantees, so
      // anchor there and stop.
      const cid = node.getAttribute && node.getAttribute('data-cell-id');
      if (cid) {
        parts.unshift(`[data-cell-id="${cid}"]`);
        break;
      }
      if (node.id && /^[A-Za-z][\w-]*$/.test(node.id)) {
        parts.unshift(`${part}#${node.id}`);
        break;
      }
      const cls = (node.getAttribute('class') || '').trim()
        .split(/\s+/).filter((c) => /^[A-Za-z_-][\w-]*$/.test(c)).slice(0, 2);
      if (cls.length) part += '.' + cls.join('.');
      const parent = node.parentElement;
      if (parent) {
        const sibs = Array.prototype.filter.call(
          parent.children, (c) => c.nodeName === node.nodeName);
        if (sibs.length > 1) {
          part += `:nth-of-type(${Array.prototype.indexOf.call(sibs, node) + 1})`;
        }
      }
      parts.unshift(part);
      node = node.parentElement;
    }
    return parts.join(' > ');
  };

  const visible = (el) => {
    if (!el || !el.isConnected) return false;
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden' ||
        cs.visibility === 'collapse' || Number(cs.opacity) === 0) return false;
    const r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0;
  };

  const inertOrHidden = (el) => {
    let n = el;
    while (n && n.nodeType === 1) {
      if (n.hasAttribute('inert')) return true;
      if (n.getAttribute('aria-hidden') === 'true') return 'aria-hidden';
      n = n.parentElement;
    }
    return false;
  };

  // An open modal (<dialog> via showModal()) makes everything outside it inert:
  // not focusable, not in the accessibility tree. The rest of the page is NOT
  // "unreachable" and its links have not lost their names — they are simply
  // behind the modal, which is exactly what a modal is for.
  const openModal = () => {
    try { return document.querySelector(':modal'); } catch { return null; }
  };
  const behindModal = (el) => {
    const m = openModal();
    return !!m && !m.contains(el);
  };

  // Every element that SHOULD be a tab stop. The tab sequence is compared
  // against this: an element here that never receives focus is a skip.
  const expectedTabbables = (root) => {
    const out = [];
    const all = (root || document).querySelectorAll(FOCUSABLE);
    const order = Array.prototype.indexOf.bind(
      Array.prototype.slice.call(document.querySelectorAll('*')));
    const index = new Map();
    let i = 0;
    for (const e of document.querySelectorAll('*')) index.set(e, i++);
    for (const el of all) {
      const ti = el.getAttribute('tabindex');
      if (ti !== null && Number(ti) < 0) continue;
      if (el.disabled) continue;
      if (el.closest('[inert]')) continue;
      if (behindModal(el)) continue;
      if (!visible(el)) continue;
      if (el.tagName === 'A' && !el.hasAttribute('href')) continue;
      out.push({
        sel: cssPath(el),
        tag: el.tagName.toLowerCase(),
        tabindex: ti === null ? 0 : Number(ti),
        docIndex: index.get(el) ?? -1,
        ariaHidden: inertOrHidden(el) === 'aria-hidden',
      });
    }
    return out;
  };

  const describeActive = () => {
    let el = document.activeElement;
    if (!el || el === document.body || el === document.documentElement) {
      return { sel: '(document)', tag: 'body', docIndex: -1 };
    }
    let i = 0;
    let idx = -1;
    for (const e of document.querySelectorAll('*')) {
      if (e === el) { idx = i; break; }
      i++;
    }
    // Focus inside a same-origin iframe leaves document.activeElement on the
    // <iframe> itself, so every Tab looked like "focus did not move". Follow it
    // into the frame; the frame's position in this document stands in for
    // the element's document order.
    let prefix = '';
    while (el && el.tagName === 'IFRAME') {
      let inner = null;
      try { inner = el.contentDocument && el.contentDocument.activeElement; } catch { inner = null; }
      if (!inner || inner === el.contentDocument.body ||
          inner === el.contentDocument.documentElement) break;
      prefix += cssPath(el) + ' >>> ';
      el = inner;
    }
    const r = el.getBoundingClientRect();
    return {
      sel: prefix + cssPath(el),
      tag: el.tagName.toLowerCase(),
      tabindex: el.getAttribute('tabindex'),
      docIndex: idx,
      text: (el.textContent || el.getAttribute('aria-label') || '').trim().slice(0, 40),
      x: Math.round(r.left + window.scrollX),
      y: Math.round(r.top + window.scrollY),
    };
  };

  // Not in the accessibility tree at all: inert, aria-hidden, or behind a modal.
  const hiddenFromAT = (el) => !!inertOrHidden(el) || behindModal(el);

  // Whether the page cancelled the last Tab. Chrome wraps Tab from the last
  // stop to the first inside the page, so on a page with one stop a wrap and
  // a trap look alike; a trap built on the key cancels it.
  // The event is kept and read once its dispatch is over, after every
  // listener the page has, wherever it was added.
  let lastTab = null;
  window.addEventListener('keydown', (e) => {
    if (e.key === 'Tab') lastTab = e;
  }, true);
  const takeTabCancelled = () => {
    const v = !!(lastTab && lastTab.defaultPrevented);
    lastTab = null;
    return v;
  };

  window.__a11y = { FOCUSABLE, cssPath, visible, expectedTabbables, describeActive,
                    hiddenFromAT, openModal, takeTabCancelled };
};

// ---------------------------------------------------------------------------
// Colour maths (WCAG 2.x relative luminance), shared by contrast and focus
// ---------------------------------------------------------------------------

function srgbToLin(c) {
  const s = c / 255;
  return s <= 0.04045 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
}
function luminance([r, g, b]) {
  return 0.2126 * srgbToLin(r) + 0.7152 * srgbToLin(g) + 0.0722 * srgbToLin(b);
}
function contrastRatio(a, b) {
  const la = luminance(a), lb = luminance(b);
  const hi = Math.max(la, lb), lo = Math.min(la, lb);
  return (hi + 0.05) / (lo + 0.05);
}

// ---------------------------------------------------------------------------
// axe
// ---------------------------------------------------------------------------

async function injectAxe(page, axePath) {
  await page.addScriptTag({ path: axePath });
  // Every frame too: axe.run() in the top frame collects results from frames
  // that have axe, and reports the rest only as "frame-tested (incomplete)" —
  // which is how an iframe's unlabelled input used to go unreported.
  // axe only answers frames whose origin it allows. A page opened with --file
  // has opaque "null" origins everywhere, so the default (same origin) left
  // every frame unanswered; the harness owns every frame here, so allow them.
  const allowFrames = () => {
    try { axe.configure({ allowedOrigins: ['<unsafe_all_origins>'] }); } catch { /* old axe */ }
  };
  for (const frame of page.frames()) {
    if (frame === page.mainFrame()) continue;
    try {
      await frame.addScriptTag({ path: axePath });
      await frame.evaluate(allowFrames);
    } catch { /* detached or blocked */ }
  }
  const ok = await page.evaluate(() => typeof window.axe === 'object' && !!axe.version);
  if (ok) await page.evaluate(allowFrames);
  if (!ok) die('axe-core was injected but did not define window.axe; the page ' +
               'may have a Content-Security-Policy that blocks inline scripts. ' +
               'Serve the page with a CSP that allows the test harness, or run ' +
               'against a build without one.');
  return page.evaluate(() => axe.version);
}

async function runAxe(page, tags, context) {
  return page.evaluate(async ({ tags, context }) => {
    const target = context ? document.querySelector(context) : document;
    const res = await axe.run(target || document, {
      runOnly: { type: 'tag', values: tags },
      resultTypes: ['violations', 'incomplete'],
      elementRef: false,
    });
    const pack = (arr) => arr.map((v) => ({
      id: v.id,
      impact: v.impact,
      help: v.help,
      helpUrl: v.helpUrl,
      tags: v.tags.filter((t) => /^wcag|^best-practice$/.test(t)),
      nodes: v.nodes.slice(0, 8).map((n) => ({
        target: Array.isArray(n.target) ? n.target.join(' ') : String(n.target),
        summary: (n.failureSummary || '').replace(/\s+/g, ' ').trim(),
        cell: (() => {
          try {
            const el = document.querySelector(
              Array.isArray(n.target) ? n.target[0] : n.target);
            const c = el && el.closest('[data-cell-id]');
            return c ? c.getAttribute('data-cell-id') : null;
          } catch { return null; }
        })(),
      })),
      count: v.nodes.length,
    }));
    return { violations: pack(res.violations), incomplete: pack(res.incomplete) };
  }, { tags, context: context || null });
}

const AXE_SEVERITY = { critical: 'error', serious: 'error', moderate: 'warning',
                       minor: 'warning' };

function axeFindings(res) {
  const out = [];
  for (const v of res.violations) {
    const sc = (v.tags.find((t) => /^wcag\d{3}$/.test(t)) || '')
      .replace(/^wcag(\d)(\d)(\d)$/, '$1.$2.$3');
    out.push(finding(
      'axe', v.id, sc || v.tags.join(','),
      AXE_SEVERITY[v.impact] || 'warning',
      `${v.help} — ${v.count} element(s), impact ${v.impact}.`,
      `${clip(v.nodes[0] ? v.nodes[0].summary : '', 300)} ${v.helpUrl}`.trim(),
      { nodes: v.nodes.map((n) => n.target), cells: [...new Set(v.nodes.map((n) => n.cell).filter(Boolean))] }));
  }
  for (const v of res.incomplete) {
    out.push(finding(
      'axe', `${v.id} (incomplete)`, v.tags.join(','), 'warning',
      `axe could not decide: ${v.help} — ${v.count} element(s).`,
      'An "incomplete" result is axe telling you a human has to look. It is ' +
      'NOT a pass, and a CI job that reports only violations silently drops ' +
      'this entire class. Most incompletes are contrast against an image or ' +
      'gradient, and colour-only meaning. Resolve each one by hand and record ' +
      'the decision. ' + v.helpUrl,
      { nodes: v.nodes.map((n) => n.target), cells: [...new Set(v.nodes.map((n) => n.cell).filter(Boolean))] }));
  }
  return out;
}

// ---------------------------------------------------------------------------
// Accessible names and roles
// ---------------------------------------------------------------------------
//
// Computed with axe-core's own accname implementation, which is a real
// implementation of the Accessible Name and Description Computation spec —
// content, aria-labelledby, aria-label, native mechanisms, the lot. Reading
// `aria-label` out of the source, as the static layer must, is an
// approximation; this is the thing a screen reader will actually say.

async function collectNames(page, scope) {
  return page.evaluate(({ scope }) => {
    const out = [];
    try { axe.setup(document); } catch { /* already set up */ }
    const roots = scope
      ? Array.prototype.slice.call(document.querySelectorAll(scope))
      : [document.documentElement];
    for (const root of roots) {
      const cell = root.getAttribute && root.getAttribute('data-cell-id');
      const els = root.querySelectorAll(window.__a11y.FOCUSABLE +
        ',[role=button],[role=link],[role=menuitem],[role=tab],[role=option],' +
        '[role=checkbox],[role=radio],[role=switch],[role=slider],[role=combobox]');
      for (const el of els) {
        if (!window.__a11y.visible(el)) continue;
        // A screen reader cannot reach it, so it has no name to announce — and
        // axe computes "" for it, which read as "missing name" on every link
        // behind an open cookie dialog.
        if (window.__a11y.hiddenFromAT(el)) continue;
        if (el.tagName === 'A' && !el.hasAttribute('href') &&
            !el.hasAttribute('role')) continue;
        let name = null, role = null, roleType = null;
        try { name = axe.commons.text.accessibleTextVirtual(axe.utils.getNodeFromTree(el)); }
        catch { try { name = axe.commons.text.accessibleText(el); } catch { name = null; } }
        try { role = axe.commons.aria.getRole(el); } catch { role = null; }
        try { roleType = role ? axe.commons.aria.getRoleType(role) : null; }
        catch { roleType = null; }

        // Only WIDGETS are required to have a name. `<main tabindex="-1">`,
        // `<h1 tabindex="-1">` and a dialog container with tabindex="-1" are
        // focus TARGETS, not controls: they are in this list because they
        // match [tabindex], and a "missing name" finding on them would be
        // noise — and noise is how a check gets switched off.
        const nativeControl = /^(a|button|input|select|textarea|summary|iframe)$/
          .test(el.tagName.toLowerCase());
        const ti = el.getAttribute('tabindex');
        const programmaticOnly = ti !== null && Number(ti) < 0;
        if (!nativeControl && roleType !== 'widget') continue;
        if (programmaticOnly && !nativeControl && roleType !== 'widget') continue;
        if (programmaticOnly && roleType && roleType !== 'widget') continue;
        const cs = getComputedStyle(el);
        out.push({
          sel: window.__a11y.cssPath(el),
          tag: el.tagName.toLowerCase(),
          type: el.getAttribute('type') || null,
          role,
          name: (name || '').trim(),
          visibleText: (el.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 60),
          hasAriaLabel: el.hasAttribute('aria-label'),
          disabled: !!el.disabled || el.getAttribute('aria-disabled') === 'true',
          cell: cell || (el.closest('[data-cell-id]')
            ? el.closest('[data-cell-id]').getAttribute('data-cell-id') : null),
          fontSize: parseFloat(cs.fontSize) || 16,
        });
      }
    }
    try { axe.teardown(); } catch { /* fine */ }
    return out;
  }, { scope: scope || null });
}

// Names that are the element type restated. A control called "Button" tells the
// user exactly what the role already told them.
const TYPE_ONLY_NAME = new Set([
  'button', 'link', 'submit', 'click', 'menu', 'input', 'field', 'textbox',
  'checkbox', 'radio', 'tab', 'option', 'icon', 'image', 'img', 'toggle',
  'item', 'more', 'ok', 'go', 'select', 'choose', 'open', 'close button',
  'untitled', 'label', 'text', 'element', 'control',
]);

function nameFindings(controls) {
  const out = [];
  const byName = new Map();

  for (const c of controls) {
    if (c.disabled && !c.name) continue;
    if (!c.name) {
      out.push(finding(
        'names', 'no-accessible-name', '4.1.2', 'error',
        `<${c.tag}${c.type ? ` type="${c.type}"` : ''}> (role ${c.role || 'none'}) ` +
        'has an EMPTY computed accessible name.',
        'A screen reader announces the role and nothing else: "button", ' +
        '"link", "edit text". The user has to guess, activate it, and find ' +
        'out. This is the computed name from the rendered tree, so it already ' +
        'accounts for aria-labelledby, wrapped labels and content — if you ' +
        'thought this control had a name, the mechanism you used is not ' +
        'working. Check that the aria-labelledby target exists and is not ' +
        'itself hidden, and that the icon inside is not the only content ' +
        '(an <svg> with no <title> contributes nothing).',
        { selector: c.sel, cell: c.cell }));
      continue;
    }
    const n = c.name.toLowerCase().replace(/\s+/g, ' ').trim();
    if (TYPE_ONLY_NAME.has(n) || n === (c.role || '').toLowerCase()) {
      out.push(finding(
        'names', 'type-only-name', '2.4.6 / 4.1.2', 'warning',
        `<${c.tag}> is named "${c.name}", which is its own type.`,
        'The role is announced anyway, so this reads as "button, button". ' +
        'The name has to say what the control DOES to this object: "Delete ' +
        'invoice 4021", not "Delete"; "Open the account menu", not "Menu".',
        { selector: c.sel, cell: c.cell }));
    }
    // 2.5.3 Label in Name: if there is visible text, the accessible name must
    // contain it, in order, or voice control cannot address the control.
    if (c.hasAriaLabel && c.visibleText && c.visibleText.length > 1) {
      const vt = c.visibleText.toLowerCase().replace(/\s+/g, ' ').trim();
      if (vt && !n.includes(vt)) {
        out.push(finding(
          'names', 'label-not-in-name', '2.5.3', 'error',
          `Visible text "${c.visibleText}" is not contained in the accessible ` +
          `name "${c.name}".`,
          'A voice-control user says "click " plus what they can see, and ' +
          'nothing happens — the command matches the accessible name, not the ' +
          'pixels. If you add aria-label to a control that has visible text, ' +
          'the name must START with that text. Usually the right fix is to ' +
          'delete the aria-label and extend the content with visually-hidden ' +
          'text instead.',
          { selector: c.sel, cell: c.cell }));
      }
    }
    const key = JSON.stringify([c.role || c.tag, n, c.cell || '']);
    if (!byName.has(key)) byName.set(key, []);
    byName.get(key).push(c);
  }

  for (const [key, group] of byName) {
    if (group.length < 2) continue;
    const [role] = JSON.parse(key);
    out.push(finding(
      'names', 'duplicate-name', '2.4.4 / 4.1.2', 'warning',
      `${group.length} ${role}s share the accessible name "${group[0].name}".`,
      'Indistinguishable in the links and form-controls lists, which is how ' +
      'screen reader users navigate, and ambiguous to voice control, which ' +
      'will either pick one arbitrarily or ask. Name each by its object. ' +
      'Note that two links with the same name AND the same destination are ' +
      'fine; this is flagged per rendering context, so check the ' +
      'destinations before you act on it.',
      { selector: group.map((g) => g.sel).slice(0, 5).join(' | '),
        cell: group[0].cell }));
  }
  return out;
}

// ---------------------------------------------------------------------------
// Tab order
// ---------------------------------------------------------------------------

async function tabSequence(page, { steps, shift }) {
  await page.evaluate(() => {
    if (document.activeElement && document.activeElement !== document.body) {
      document.activeElement.blur();
    }
    window.scrollTo(0, 0);
  });
  const seq = [];
  for (let i = 0; i < steps; i++) {
    await page.keyboard.press(shift ? 'Shift+Tab' : 'Tab');
    // eslint-disable-next-line no-await-in-loop
    const stop = await page.evaluate(() => ({ ...window.__a11y.describeActive(),
                                              cancelled: window.__a11y.takeTabCancelled() }));
    seq.push(stop);
    if (stop.sel === '(document)' && seq.length > 2 &&
        seq[seq.length - 2].sel === '(document)') break;   // left the page
  }
  return seq;
}

function analyseTabOrder(forward, reverse, expected, opts) {
  const out = [];
  const reached = new Set(forward.map((s) => s.sel).filter((s) => s !== '(document)'));
  const reachedBack = new Set(reverse.map((s) => s.sel).filter((s) => s !== '(document)'));

  // --- 1. TRAP: focus that stops making progress ------------------------
  // The shape is a short cycle that repeats to the end of the run while the
  // page still has tab stops outside it. A legitimate wrap-around visits every
  // stop before repeating; a trap visits two or three.
  const tail = forward.slice(-Math.min(12, forward.length));
  const tailSet = new Set(tail.map((s) => s.sel));
  if (forward.length >= 8 && tailSet.size <= 3 && tailSet.size < expected.length) {
    const unreachedFromTail = expected.filter((e) => !reached.has(e.sel));
    if (unreachedFromTail.length) {
      out.push(finding(
        'taborder', 'keyboard-trap', '2.1.2', 'error',
        `Focus is trapped: the last ${tail.length} Tab presses cycled among ` +
        `${tailSet.size} element(s) (${[...tailSet].join(', ')}) and never ` +
        `reached the remaining ${unreachedFromTail.length} tab stop(s).`,
        'A keyboard user who tabs into this can never leave it — not the rest ' +
        'of the page, not the browser chrome, not the URL bar, not ' +
        'find-in-page. This is a Level A failure and it makes the page ' +
        'unusable, not degraded. The cause is almost always a hand-rolled ' +
        'Tab-cycling loop: a keydown handler that preventDefaults Tab and ' +
        'moves focus itself. Delete it. A MODAL dialog is the one thing that ' +
        'should trap focus, and the correct construction is <dialog> with ' +
        'showModal(), or `inert` on everything outside plus an Esc handler — ' +
        'both of which leave the browser\'s own chrome reachable. Nothing ' +
        'else — not a dropdown, not a carousel, not a video player — may ' +
        'swallow Tab.',
        { selector: [...tailSet].join(', ') }));
    }
  }
  // Focus that does not move at all. An <iframe> reported as the stop is a
  // cross-origin frame this script cannot look into, not a trap. On a page
  // with one stop, Chrome's wrap lands on the same element, so there it is a
  // trap only if the page cancelled the key.
  const wraps = expected.length === 1;
  for (let i = 1; i < forward.length; i++) {
    if (forward[i].sel === forward[i - 1].sel && forward[i].sel !== '(document)' &&
        forward[i].tag !== 'iframe' && (!wraps || forward[i].cancelled)) {
      out.push(finding(
        'taborder', 'focus-stuck', '2.1.2', 'error',
        `Tab did not move focus away from ${forward[i].sel}.`,
        'Either a handler is calling preventDefault on Tab and re-focusing ' +
        'the same element, or the element is the only tab stop in an ' +
        'inert-everything-else region that nothing closes.',
        { selector: forward[i].sel }));
      break;
    }
  }

  // --- 2. SKIP: a control that should be reachable and is not ------------
  const skipped = expected.filter((e) => !reached.has(e.sel));
  if (skipped.length) {
    const ariaHidden = skipped.filter((e) => e.ariaHidden);
    out.push(finding(
      'taborder', 'unreachable-control', '2.1.1', 'error',
      `${skipped.length} focusable element(s) were never reached by Tab: ` +
      `${skipped.slice(0, 6).map((e) => e.sel).join(', ')}` +
      `${skipped.length > 6 ? ' …' : ''}.`,
      'These are elements the browser considers tabbable that the tab ' +
      'sequence never visits. Three causes, in order of frequency: focus is ' +
      'trapped before them (fix the trap first and re-run — this list usually ' +
      'empties); a positive tabindex elsewhere has rewritten the order; or ' +
      'something is swallowing the keystroke. If a control is genuinely meant ' +
      'not to be a tab stop — a roving-tabindex item inside a composite ' +
      'widget — it needs tabindex="-1", not to be silently skipped.' +
      (ariaHidden.length
        ? ` ${ariaHidden.length} of them are inside aria-hidden="true", which ` +
          'is the worst version of this: reachable by keyboard, invisible to ' +
          'assistive technology. Use `inert`.'
        : ''),
      { selector: skipped.map((e) => e.sel).slice(0, 10).join(' | ') }));
  }

  // --- 3. JUMP: an order that is valid and nonsensical -------------------
  // Take the first cycle only: one backwards step is the legitimate wrap.
  const firstSeen = new Map();
  let cycleEnd = forward.length;
  for (let i = 0; i < forward.length; i++) {
    const s = forward[i].sel;
    if (firstSeen.has(s)) { cycleEnd = i; break; }
    firstSeen.set(s, i);
  }
  const cycle = forward.slice(0, cycleEnd).filter((s) => s.sel !== '(document)');
  const backSteps = [];
  for (let i = 1; i < cycle.length; i++) {
    if (cycle[i].docIndex >= 0 && cycle[i - 1].docIndex >= 0 &&
        cycle[i].docIndex < cycle[i - 1].docIndex) {
      backSteps.push([cycle[i - 1], cycle[i]]);
    }
  }
  const positive = expected.filter((e) => e.tabindex > 0);
  if (positive.length) {
    out.push(finding(
      'taborder', 'positive-tabindex-order', '2.4.3', 'error',
      `${positive.length} element(s) carry a positive tabindex, so they are ` +
      `visited BEFORE everything else on the page: ` +
      `${positive.map((e) => `${e.sel} (tabindex=${e.tabindex})`).slice(0, 5).join(', ')}.`,
      'The measured sequence above shows the result: the page is now read in ' +
      'an order its markup does not describe, and the effect is invisible to ' +
      'anyone using a mouse. One positive value anywhere means every other ' +
      'interactive element on the page must also be numbered, forever. ' +
      'Remove it and fix the DOM order instead — 1.3.2 requires that anyway.',
      { selector: positive.map((e) => e.sel).join(' | ') }));
  }
  for (const [from, to] of backSteps.slice(0, 5)) {
    if (positive.length && (Number(to.tabindex) > 0 || Number(from.tabindex) > 0)) continue;
    out.push(finding(
      'taborder', 'focus-order-jump', '2.4.3', 'warning',
      `Tab moved BACKWARDS in the DOM: ${from.sel} → ${to.sel}.`,
      'Focus order must preserve meaning and operability. A backwards step ' +
      'that is not the end-of-page wrap means the visual order and the DOM ' +
      'order disagree — a CSS `order` or `grid-area` reorder, an ' +
      'absolutely-positioned control, or an overlay rendered at the top of ' +
      'the DOM and shown at the bottom. Reorder the DOM, not the layout. ' +
      'Note that this check reads DOM order; it cannot tell you whether the ' +
      'resulting sequence makes SENSE to a person, which is the part of ' +
      '2.4.3 no tool can evaluate.',
      { selector: `${from.sel} -> ${to.sel}` }));
  }

  // --- 4. Asymmetry between forward and backward -------------------------
  const onlyForward = [...reached].filter((s) => !reachedBack.has(s));
  if (onlyForward.length && reverse.length > 3) {
    out.push(finding(
      'taborder', 'reverse-order-asymmetry', '2.1.1 / 2.4.3', 'warning',
      `${onlyForward.length} element(s) reachable with Tab were not reachable ` +
      `with Shift+Tab: ${onlyForward.slice(0, 5).join(', ')}.`,
      'Backwards order is where broken focus management hides, because ' +
      'almost nobody tests it. A one-directional stop usually means a ' +
      'handler that moves focus on Tab without a matching branch for ' +
      'Shift+Tab.',
      { selector: onlyForward.slice(0, 8).join(' | ') }));
  }
  return out;
}

// ---------------------------------------------------------------------------
// Focus indicator visibility — measured, not assumed
// ---------------------------------------------------------------------------
//
// `:focus-visible` existing in a stylesheet does not mean a ring is drawn. It
// can be overridden, clipped by an ancestor's overflow, painted in a colour
// identical to the background, or — the one this suite cares about most —
// composed entirely of box-shadow, which forced-colors mode discards. The only
// way to know is to look at the pixels, so that is what this does.

const DIFF_FN = ({ aURL, bURL }) => new Promise(async (resolve) => {
  const load = async (url) => {
    const bmp = await createImageBitmap(await (await fetch(url)).blob());
    const c = new OffscreenCanvas(bmp.width, bmp.height);
    const ctx = c.getContext('2d', { willReadFrequently: true });
    ctx.drawImage(bmp, 0, 0);
    return { w: bmp.width, h: bmp.height,
             d: ctx.getImageData(0, 0, bmp.width, bmp.height).data };
  };
  const lin = (c) => {
    const s = c / 255;
    return s <= 0.04045 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
  };
  const lum = (r, g, b) => 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b);

  const A = await load(aURL);
  const B = await load(bURL);
  if (A.w !== B.w || A.h !== B.h) { resolve({ sizeChanged: true }); return; }
  const total = A.w * A.h;
  let changed = 0;
  const sumA = [0, 0, 0], sumB = [0, 0, 0];
  // A histogram of PER-PIXEL contrast, not a contrast of mean colours. The
  // suite's focus ring is two bands — an inner one in the canvas colour and an
  // outer one in the accent — so averaging the changed pixels blends a 5.7:1
  // band with a 1.0:1 band and reports a ring that is plainly visible as
  // failing. SC 2.4.13 asks about the indicator's own pixels, which is what
  // the 90th percentile of this histogram describes.
  const BUCKETS = 400;
  const hist = new Uint32Array(BUCKETS);
  for (let i = 0; i < A.d.length; i += 4) {
    const dr = Math.abs(A.d[i] - B.d[i]);
    const dg = Math.abs(A.d[i + 1] - B.d[i + 1]);
    const db = Math.abs(A.d[i + 2] - B.d[i + 2]);
    // 12/255 ignores antialiasing jitter without ignoring a real indicator.
    if (dr + dg + db > 12) {
      changed++;
      sumA[0] += A.d[i]; sumA[1] += A.d[i + 1]; sumA[2] += A.d[i + 2];
      sumB[0] += B.d[i]; sumB[1] += B.d[i + 1]; sumB[2] += B.d[i + 2];
      const la = lum(A.d[i], A.d[i + 1], A.d[i + 2]);
      const lb = lum(B.d[i], B.d[i + 1], B.d[i + 2]);
      const ratio = (Math.max(la, lb) + 0.05) / (Math.min(la, lb) + 0.05);
      hist[Math.min(BUCKETS - 1, Math.floor((ratio - 1) / 20 * BUCKETS))]++;
    }
  }
  let p90 = null;
  if (changed) {
    const want = Math.max(1, Math.floor(changed * 0.90));
    let seen = 0;
    for (let b = 0; b < BUCKETS; b++) {
      seen += hist[b];
      if (seen >= want) { p90 = 1 + (b + 0.5) / BUCKETS * 20; break; }
    }
  }
  resolve({
    sizeChanged: false,
    total,
    changed,
    fraction: changed / total,
    // p90 is the reported number; the mean colours are kept for the JSON so a
    // disputed finding can be reconstructed.
    ratio: p90,
    before: changed ? sumA.map((v) => v / changed) : null,
    after: changed ? sumB.map((v) => v / changed) : null,
  });
});

async function measureFocus(page, cmpPage, selectors, opts, label) {
  const results = [];
  for (const sel of selectors) {
    let entry = { sel, label, ok: false };
    try {
      const handle = await page.$(sel);
      if (!handle) { entry.error = 'not found'; results.push(entry); continue; }
      await handle.evaluate((el) => {
        el.scrollIntoView({ block: 'center', inline: 'center', behavior: 'instant' });
      });
      const box = await handle.boundingBox();
      if (!box || box.width < 1 || box.height < 1) {
        entry.error = 'no box'; results.push(entry); continue;
      }
      const vp = page.viewportSize() || opts.viewport;
      const pad = 10;
      const clip = {
        x: Math.max(0, Math.floor(box.x - pad)),
        y: Math.max(0, Math.floor(box.y - pad)),
        width: Math.min(vp.width, Math.ceil(box.width + pad * 2)),
        height: Math.min(vp.height, Math.ceil(box.height + pad * 2)),
      };
      if (clip.x + clip.width > vp.width) clip.width = vp.width - clip.x;
      if (clip.y + clip.height > vp.height) clip.height = vp.height - clip.y;
      if (clip.width < 2 || clip.height < 2) {
        entry.error = 'off-screen'; results.push(entry); continue;
      }

      // A component-state-matrix proof sheet renders the focus-visible state by
      // MIRRORING the rule onto `[data-force-state~="focus-visible"]`, so the
      // ring is already painted at rest. Blurring and focusing such a cell
      // changes nothing and would report "no focus indicator" on the one cell
      // that exists to prove the indicator — a false positive of exactly the
      // kind that gets a check switched off. For those cells the A/B is the
      // state attribute itself, which is the same comparison by a different
      // lever, and it works identically under forced-colors.
      const simulated = await handle.evaluate((el) => {
        const v = el.getAttribute('data-force-state');
        return v && /focus/.test(v) ? v : null;
      });
      entry.method = simulated ? 'state-attribute' : 'focus';

      if (simulated) {
        await handle.evaluate((el) => el.removeAttribute('data-force-state'));
      } else {
        await page.evaluate(() => {
          if (document.activeElement && document.activeElement.blur) {
            document.activeElement.blur();
          }
        });
      }
      await page.evaluate(() => new Promise((r) =>
        requestAnimationFrame(() => requestAnimationFrame(r))));
      const off = await page.screenshot({ clip });

      // Keyboard-style focus: :focus-visible only matches for keyboard input
      // or a text field, so focusing programmatically after a MOUSE action
      // deliberately shows no ring. Playwright's .focus() is not a mouse
      // action, and Chromium treats a scripted focus as keyboard-initiated
      // here, which is what we want to measure.
      if (simulated) {
        await handle.evaluate((el, v) => el.setAttribute('data-force-state', v),
                              simulated);
      } else {
        await handle.evaluate((el) => el.focus({ preventScroll: true }));
      }
      await page.evaluate(() => new Promise((r) =>
        requestAnimationFrame(() => requestAnimationFrame(r))));
      const on = await page.screenshot({ clip });

      const res = await cmpPage.evaluate(DIFF_FN, {
        aURL: 'data:image/png;base64,' + off.toString('base64'),
        bURL: 'data:image/png;base64,' + on.toString('base64'),
      });
      if (res.sizeChanged) { entry.error = 'clip size changed'; results.push(entry); continue; }
      entry.ok = true;
      entry.changed = res.changed;
      entry.total = res.total;
      entry.fraction = res.fraction;
      entry.ratio = res.ratio;
      entry.meanRatio = (res.before && res.after)
        ? contrastRatio(res.before, res.after) : null;
      entry.before = res.before;
      entry.after = res.after;
    } catch (err) {
      entry.error = String(err.message || err).split('\n')[0].slice(0, 120);
    }
    results.push(entry);
  }
  await page.evaluate(() => {
    if (document.activeElement && document.activeElement.blur) {
      document.activeElement.blur();
    }
  });
  return results;
}

// The density values a page's own stylesheets name in a [data-density=…]
// selector, in the order they appear, and the one its root has now. A
// cross-origin sheet cannot be read; name its densities with --densities.
const DENSITIES_FN = () => {
  const found = [];
  const walk = (rules) => {
    for (const r of rules) {
      if (r.selectorText) {
        for (const m of r.selectorText.matchAll(/\[data-density\s*[~|^$*]?=\s*["']?([\w-]+)/g)) {
          if (!found.includes(m[1])) found.push(m[1]);
        }
      }
      if (r.cssRules) walk(r.cssRules);
    }
  };
  for (const sheet of document.styleSheets) {
    try { walk(sheet.cssRules); } catch { /* cross-origin */ }
  }
  return { found, current: document.documentElement.getAttribute('data-density') };
};

async function setDensity(page, density) {
  await page.evaluate((d) => {
    if (d === null) document.documentElement.removeAttribute('data-density');
    else document.documentElement.setAttribute('data-density', d);
  }, density);
  await page.evaluate(() => new Promise((r) =>
    requestAnimationFrame(() => requestAnimationFrame(r))));
}

function focusFindings(measurements, opts) {
  const out = [];
  for (const m of measurements) {
    if (!m.ok) continue;
    if (m.fraction < opts.focusThreshold) {
      out.push(finding(
        'focus', 'no-visible-focus-indicator', '2.4.7 / 2.4.13', 'error',
        `${m.sel} changed ${m.changed}/${m.total} pixels ` +
        `(${(m.fraction * 100).toFixed(3)}%) between unfocused and focused — ` +
        `below the ${(opts.focusThreshold * 100).toFixed(1)}% floor.`,
        'Measured, not inferred: the element was screenshotted unfocused and ' +
        'focused and the images are effectively identical, so there is no ' +
        'indicator regardless of what the stylesheet says. The usual cause is ' +
        '`outline: none` with no replacement — the most common accessibility ' +
        'bug on the web. The fix is to delete the reset, not to add a ring ' +
        'back at a higher specificity. If you want no ring for mouse users, ' +
        '`:focus-visible` already does that.',
        { selector: m.sel, cell: m.cell, fraction: m.fraction }));
    } else if (m.ratio != null && m.ratio < 3) {
      out.push(finding(
        'focus', 'weak-focus-indicator', '1.4.11 / 2.4.13', 'warning',
        `${m.sel} has a focus indicator, but even its strongest band measures ` +
        `${m.ratio.toFixed(2)}:1 against the same pixels unfocused ` +
        `(3:1 required; 90th percentile of ${m.changed} changed pixels).`,
        'There IS a ring and it is too faint to see against the thing it is ' +
        'drawn on. This is nearly always a ring in a single colour that works ' +
        'on the page background and disappears on a filled button or a photo. ' +
        'The suite\'s answer is a two-part ring — an inner band in the canvas ' +
        'colour and an outer band in the accent — so the indicator never sits ' +
        'directly against the component\'s own colour: `--shadow-focus` is ' +
        '`0 0 0 2px var(--bg-canvas), 0 0 0 4px var(--border-focus)`.',
        { selector: m.sel, cell: m.cell, ratio: m.ratio }));
    }
  }
  return out;
}

function forcedColorFindings(normal, forced, opts) {
  const out = [];
  const byNormal = new Map(normal.map((m) => [m.sel, m]));
  for (const f of forced) {
    if (!f.ok) continue;
    const n = byNormal.get(f.sel);
    if (!n || !n.ok) continue;
    if (n.fraction >= opts.focusThreshold && f.fraction < opts.focusThreshold) {
      out.push(finding(
        'forced', 'focus-ring-lost-in-forced-colors', '1.4.11 / 2.4.7', 'error',
        `${f.sel} has a focus ring in normal mode ` +
        `(${(n.fraction * 100).toFixed(2)}% of pixels change) and NONE in ` +
        `forced-colors mode (${(f.fraction * 100).toFixed(3)}%).`,
        'forced-colors mode DISCARDS box-shadow. A ring built only from ' +
        'box-shadow does not degrade there — it vanishes completely, and a ' +
        'Windows High Contrast user has no focus indicator anywhere on the ' +
        'page. The bridge is one line: pair the shadow with a TRANSPARENT ' +
        'outline. `outline: var(--stroke-focus) solid transparent;` is ' +
        'invisible in normal mode and is forced to a system colour in ' +
        'forced-colors, where it becomes the ring. That is why the token ' +
        'contract specifies the focus ring as a pair and not as a shadow. ' +
        'See references/token-contract.md, Accessibility floor.',
        { selector: f.sel, cell: f.cell,
          normalFraction: n.fraction, forcedFraction: f.fraction }));
    }
  }
  return out;
}

async function forcedColorsSurvey(page) {
  // Deterministic from computed style: what on this page is carried ONLY by a
  // property forced-colors removes or overrides.
  //
  // The focus ring is deliberately NOT surveyed here. A ring only exists while
  // :focus-visible matches, and reading computed style during a scripted focus
  // is unreliable — Chromium resolves `outline-width` for `outline-style: auto`
  // lazily, so the UA's own ring reads as 0px until it has painted. The ring is
  // measured in pixels instead, in both modes, which is the only answer that
  // cannot be wrong. See measureFocus / forcedColorFindings.
  return page.evaluate(() => {
    let shadowOnly = 0, bgImage = 0, fillOnly = 0, transparentBorder = 0;
    const examples = { shadowOnly: [], bgImage: [], fillOnly: [] };
    for (const el of document.querySelectorAll('*')) {
      if (!window.__a11y.visible(el)) continue;
      const cs = getComputedStyle(el);
      if (cs.boxShadow && cs.boxShadow !== 'none') {
        shadowOnly++;
        if (examples.shadowOnly.length < 4) {
          examples.shadowOnly.push(window.__a11y.cssPath(el));
        }
      }
      if (cs.backgroundImage && cs.backgroundImage !== 'none') {
        bgImage++;
        if (examples.bgImage.length < 4) examples.bgImage.push(window.__a11y.cssPath(el));
      }
      const noBorder = cs.borderStyle === 'none' || cs.borderTopWidth === '0px';
      const hasFill = cs.backgroundColor && cs.backgroundColor !== 'rgba(0, 0, 0, 0)' &&
        cs.backgroundColor !== 'transparent';
      if (hasFill && noBorder &&
          /button|a|summary/.test(el.tagName.toLowerCase())) {
        fillOnly++;
        if (examples.fillOnly.length < 4) examples.fillOnly.push(window.__a11y.cssPath(el));
      }
      if (/transparent|rgba\(0, 0, 0, 0\)/.test(cs.borderTopColor) &&
          cs.borderTopStyle !== 'none' && cs.borderTopWidth !== '0px') {
        transparentBorder++;
      }
    }
    return { shadowOnly, bgImage, fillOnly, transparentBorder, examples };
  });
}

// ---------------------------------------------------------------------------
// Contrast from computed styles, including the overlay case
// ---------------------------------------------------------------------------

const CONTRAST_FN = () => {
  // A computed colour is serialised in the space it was written in: rgb() for
  // legacy colours, but oklch(), lab(), color(…) for the rest — which is every
  // token this suite ships. Reading rgb() alone skipped those silently: no
  // finding and no "unmeasurable" warning, on exactly the sites built with the
  // suite. Anything that is not rgb() is painted into a 1x1 canvas and read
  // back, which is the browser's own conversion to sRGB.
  const pixel = document.createElement('canvas');
  pixel.width = 1;
  pixel.height = 1;
  const ctx = pixel.getContext('2d', { willReadFrequently: true });
  // design-audit-ignore-next-line: L1 -- a parse sentinel, not a design colour
  const SENTINEL = '#010203';     // fillStyle left at this means "unparseable"
  const cache = new Map();
  const parse = (c) => {
    if (!c) return null;
    if (cache.has(c)) return cache.get(c);
    let out = null;
    const m = /^rgba?\(([^)]+)\)$/.exec(c.trim());
    if (m) {
      const p = m[1].split(/[,\s/]+/).filter(Boolean).map(Number);
      out = { r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1 };
    } else if (ctx) {
      ctx.clearRect(0, 0, 1, 1);
      ctx.fillStyle = SENTINEL;
      ctx.fillStyle = c;
      if (ctx.fillStyle !== SENTINEL) {
        ctx.fillRect(0, 0, 1, 1);
        const d = ctx.getImageData(0, 0, 1, 1).data;
        out = { r: d[0], g: d[1], b: d[2], a: Math.round((d[3] / 255) * 1000) / 1000 };
      }
    }
    cache.set(c, out);
    return out;
  };
  const over = (fg, bg) => ({
    r: fg.r * fg.a + bg.r * (1 - fg.a),
    g: fg.g * fg.a + bg.g * (1 - fg.a),
    b: fg.b * fg.a + bg.b * (1 - fg.a),
    a: 1,
  });

  // SC 1.4.3 exempts text that is part of an inactive component, and axe
  // skips the same set: a disabled control or fieldset and everything in it,
  // anything inside aria-disabled="true", and the label of a disabled control.
  // The first legend of a disabled fieldset is not disabled (HTML), so what
  // it holds is measured, and so is a control that only looks disabled
  // (GT-A14).
  const inactive = (el) => {
    if (el.closest('[aria-disabled="true"]')) return true;
    for (let n = el; n; n = n.parentElement) {
      if (!n.matches(':disabled')) continue;
      if (n.tagName !== 'FIELDSET') return true;
      const legend = n.querySelector(':scope > legend');
      if (!legend || !legend.contains(el)) return true;
    }
    const label = el.closest('label');
    return !!(label && label.control && label.control.matches(':disabled'));
  };

  const out = [];
  const seen = new Set();
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let node;
  while ((node = walker.nextNode())) {
    const text = (node.nodeValue || '').trim();
    if (text.length < 2) continue;
    const el = node.parentElement;
    if (!el || seen.has(el)) continue;
    if (/^(script|style|noscript|title)$/i.test(el.tagName)) continue;
    if (!window.__a11y.visible(el)) continue;
    seen.add(el);
    if (inactive(el)) continue;

    const cs = getComputedStyle(el);
    const fg = parse(cs.color);
    if (!fg) continue;
    const size = parseFloat(cs.fontSize) || 16;
    const weight = Number(cs.fontWeight) || 400;
    const large = size >= 24 || (size >= 18.66 && weight >= 700);

    // Walk ancestors compositing background-color until opaque.
    let bg = { r: 255, g: 255, b: 255, a: 1 };
    let unmeasurable = null;
    let n = el;
    const stack = [];
    while (n && n.nodeType === 1) {
      const s = getComputedStyle(n);
      if (s.backgroundImage && s.backgroundImage !== 'none') {
        unmeasurable = 'background-image on ' + window.__a11y.cssPath(n);
        break;
      }
      const c = parse(s.backgroundColor);
      if (c && c.a > 0) {
        stack.push(c);
        if (c.a >= 1) break;
      }
      n = n.parentElement;
    }
    if (unmeasurable) {
      out.push({ sel: window.__a11y.cssPath(el), text: text.slice(0, 50),
                 unmeasurable, size, large });
      continue;
    }
    for (let i = stack.length - 1; i >= 0; i--) bg = over(stack[i], bg);

    // --- The overlay case -------------------------------------------------
    // Something painted ON TOP of this text changes what the eye receives,
    // and a source-level contrast check cannot see it at all: the colour pair
    // in the stylesheet is fine and the rendered result is not.
    const r = el.getBoundingClientRect();
    const cx = Math.min(window.innerWidth - 1, Math.max(0, r.left + r.width / 2));
    const cy = Math.min(window.innerHeight - 1, Math.max(0, r.top + r.height / 2));
    const overlays = [];
    let hits = [];
    try { hits = document.elementsFromPoint(cx, cy); } catch { hits = []; }
    for (const h of hits) {
      if (h === el) break;
      if (h.contains(el)) continue;
      const hs = getComputedStyle(h);
      const hc = parse(hs.backgroundColor);
      if (hc && hc.a > 0) overlays.push(hc);
    }
    // elementsFromPoint skips pointer-events:none, which is exactly how most
    // scrims are built, so they are found separately.
    for (const cand of document.querySelectorAll('*')) {
      if (cand === el || cand.contains(el) || el.contains(cand)) continue;
      const cs2 = getComputedStyle(cand);
      if (cs2.pointerEvents !== 'none' && cs2.position === 'static') continue;
      if (cs2.pointerEvents !== 'none') continue;
      const cc = parse(cs2.backgroundColor);
      if (!cc || cc.a === 0) continue;
      const cr = cand.getBoundingClientRect();
      if (cx >= cr.left && cx <= cr.right && cy >= cr.top && cy <= cr.bottom) {
        overlays.push(cc);
      }
    }

    let efg = fg.a < 1 ? over(fg, bg) : fg;
    let ebg = bg;
    for (let i = overlays.length - 1; i >= 0; i--) {
      efg = over(overlays[i], efg);
      ebg = over(overlays[i], ebg);
    }

    out.push({
      sel: window.__a11y.cssPath(el),
      text: text.slice(0, 50),
      size, weight, large,
      fg: [efg.r, efg.g, efg.b],
      bg: [ebg.r, ebg.g, ebg.b],
      rawFg: [fg.r, fg.g, fg.b],
      rawBg: [bg.r, bg.g, bg.b],
      overlays: overlays.length,
      cell: el.closest('[data-cell-id]')
        ? el.closest('[data-cell-id]').getAttribute('data-cell-id') : null,
    });
  }
  return out;
};

function contrastFindings(samples) {
  const out = [];
  let unmeasurable = 0;
  const unmeasurableWhere = [];
  for (const s of samples) {
    if (s.unmeasurable) {
      unmeasurable++;
      if (unmeasurableWhere.length < 5) unmeasurableWhere.push(s.unmeasurable);
      continue;
    }
    const need = s.large ? 3 : 4.5;
    const ratio = contrastRatio(s.fg, s.bg);
    if (ratio + 0.005 < need) {
      const rawRatio = contrastRatio(s.rawFg, s.rawBg);
      out.push(finding(
        'contrast', s.overlays ? 'contrast-under-overlay' : 'contrast-too-low',
        s.large ? '1.4.3 (large text)' : '1.4.3', 'error',
        `"${s.text}" measures ${ratio.toFixed(2)}:1 (needs ${need}:1 at ` +
        `${s.size}px${s.weight >= 700 ? ' bold' : ''})` +
        (s.overlays
          ? ` — ${s.overlays} translucent overlay(s) composited in. The colour ` +
            `pair in the stylesheet reads as ${rawRatio.toFixed(2)}:1.`
          : '.'),
        s.overlays
          ? 'This is the case a source-level contrast check cannot see and ' +
            'reports as a pass: the declared colours are fine, and something ' +
            'is painted over them. A scrim, a "fade" gradient, a disabled ' +
            'overlay, a loading veil. Composite the overlay before you judge ' +
            'the pair, or move the text above it. Note that 1.4.3 has no ' +
            'exemption for "it is only during loading".'
          : 'Contrast is measured, never assumed. 4.5:1 for text under 24px ' +
            'regular / 18.66px bold, 3:1 at or above. The five places teams ' +
            'fail are placeholder text (it is text, there is no exemption), ' +
            'genuinely-disabled controls (exempt, and only if genuinely ' +
            'inactive), focus rings, icon-only buttons, and control ' +
            'boundaries. Check any pair with `python -m ' +
            'scripts.generate_color_ramp --check A B` in web-design-studio.',
        { selector: s.sel, cell: s.cell, ratio, required: need }));
    }
  }
  if (unmeasurable) {
    out.push(finding(
      'contrast', 'contrast-unmeasurable', '1.4.3', 'warning',
      `${unmeasurable} text element(s) sit on a background-image or gradient, ` +
      'so their contrast cannot be computed from styles.',
      'This is a genuine limit, not a bug: contrast against a photograph ' +
      'varies per pixel, and the worst pixel is the one that matters. A tool ' +
      'that silently passed these would be lying. Check them by eye against ' +
      'the busiest region of the image, or remove the question by putting the ' +
      'text on a solid scrim that is itself measured. Examples: ' +
      unmeasurableWhere.join(', '),
      {}));
  }
  return out;
}

// ---------------------------------------------------------------------------
// Keyboard traversal against an expected key map
// ---------------------------------------------------------------------------
//
// The key maps come from accessibility.md §4, which is the ARIA Authoring
// Practices behaviour a user has already learned somewhere else. Deviating is a
// usability failure even when it is technically conformant, which is exactly
// the kind of thing a scanner never reports and a user notices immediately.

const PATTERN_HELP = {
  dialog: 'Dialog (modal): Tab and Shift+Tab cycle WITHIN it, Esc closes it, ' +
          'focus moves in on open and returns to the trigger on close. Use ' +
          '<dialog> with showModal() unless you have a specific reason not to.',
  menu: 'Menu button: Enter, Space or ArrowDown opens and focuses the first ' +
        'item; ArrowUp opens and focuses the last. Arrows move and wrap. Esc ' +
        'closes AND returns focus to the trigger. Tab closes the menu and ' +
        'moves on. Items are not individually in the tab order.',
  tabs: 'Tabs: Tab reaches the tablist once, then the panel. Arrow keys move ' +
        'between tabs with a roving tabindex. Home/End go to first/last. ' +
        'Exactly one tab carries tabindex="0" at any moment.',
  disclosure: 'Disclosure: Enter and Space toggle it, focus STAYS on the ' +
              'trigger, and aria-expanded reflects the state. Do not move ' +
              'focus into a disclosure.',
  combobox: 'Combobox: ArrowDown or Alt+ArrowDown opens, arrows move, Enter ' +
            'commits, Esc closes without committing.',
};

async function runKeymap(page, config) {
  const out = [];
  for (const spec of config.patterns || []) {
    const name = spec.name || spec.trigger || spec.container || '(unnamed)';
    const pattern = (spec.pattern || '').toLowerCase();
    if (!PATTERN_HELP[pattern]) {
      out.push(finding('keys', 'unknown-pattern', '-', 'warning',
        `"${name}": pattern "${spec.pattern}" is not one this tool drives ` +
        `(${Object.keys(PATTERN_HELP).join(', ')}).`,
        'Everything else is a manual check — references/manual-protocol.md §2.',
        {}));
      continue;
    }
    const fail = (rule, sc, msg) => out.push(finding(
      'keys', rule, sc, 'error', `"${name}": ${msg}`, PATTERN_HELP[pattern],
      { selector: spec.trigger || spec.container }));

    try {
      if (spec.trigger) {
        const t = await page.$(spec.trigger);
        if (!t) {
          out.push(finding('keys', 'trigger-not-found', '-', 'warning',
            `"${name}": no element matches trigger "${spec.trigger}".`,
            'The key map names a control that is not on this page. Fix the ' +
            'selector or scope the config per page.', {}));
          continue;
        }
        await t.evaluate((el) => el.focus({ preventScroll: true }));
      }

      if (pattern === 'dialog' || pattern === 'menu' || pattern === 'combobox') {
        const openKey = pattern === 'combobox' ? 'ArrowDown' : 'Enter';
        await page.keyboard.press(openKey);
        await page.waitForTimeout(120);

        const state = await page.evaluate(({ container, trigger }) => {
          const c = container ? document.querySelector(container) : null;
          const active = document.activeElement;
          return {
            containerExists: !!c,
            open: c ? (c.open === true || window.__a11y.visible(c)) : null,
            focusInside: c ? c.contains(active) : null,
            expanded: trigger
              ? (document.querySelector(trigger) || {}).getAttribute
                ? document.querySelector(trigger).getAttribute('aria-expanded')
                : null
              : null,
            activeSel: window.__a11y.cssPath(active),
          };
        }, { container: spec.container || null, trigger: spec.trigger || null });

        if (spec.container && !state.containerExists) {
          fail('container-not-found', '-',
               `container "${spec.container}" does not exist after ${openKey}.`);
          continue;
        }
        if (spec.container && !state.open) {
          fail('does-not-open-by-keyboard', '2.1.1',
               `${openKey} on the trigger did not open it.`);
        }
        if (pattern !== 'combobox' && spec.container && state.open &&
            !state.focusInside) {
          fail('focus-not-moved-in', '2.4.3',
               `it opened and focus stayed outside it (on ${state.activeSel}). ` +
               'A screen reader user is now reading a page that has visually ' +
               'changed underneath them with no announcement.');
        }
        if (spec.trigger && state.expanded !== null &&
            state.expanded !== 'true' && pattern !== 'dialog') {
          fail('aria-expanded-not-updated', '4.1.2',
               `aria-expanded is "${state.expanded}" while it is open. An ` +
               'aria-expanded that never changes tells the user the menu is ' +
               'closed while it is open, which is worse than saying nothing.');
        }

        if (pattern === 'menu' && spec.items) {
          const first = await page.evaluate((s) => window.__a11y.cssPath(document.activeElement), spec.items);
          await page.keyboard.press('ArrowDown');
          await page.waitForTimeout(60);
          const second = await page.evaluate(() => window.__a11y.cssPath(document.activeElement));
          if (first === second) {
            fail('arrow-does-not-move', '2.1.1',
                 'ArrowDown did not move focus between items. A menu is ONE ' +
                 'tab stop with a roving tabindex inside it; arrows move, Tab ' +
                 'leaves.');
          }
        }

        if (pattern === 'dialog' || pattern === 'menu') {
          await page.keyboard.press('Escape');
          await page.waitForTimeout(150);
          const after = await page.evaluate(({ container, trigger }) => {
            const c = container ? document.querySelector(container) : null;
            return {
              stillOpen: c ? (c.open === true || window.__a11y.visible(c)) : null,
              focusOnTrigger: trigger
                ? document.activeElement === document.querySelector(trigger)
                : null,
              activeSel: window.__a11y.cssPath(document.activeElement),
            };
          }, { container: spec.container || null, trigger: spec.trigger || null });
          if (after.stillOpen) {
            fail('escape-does-not-close', '2.1.2',
                 'Esc did not close it. Esc always cancels the innermost ' +
                 'dismissible thing, and it is the escape hatch a user reaches ' +
                 'for before anything else.');
          } else if (spec.trigger && after.focusOnTrigger === false) {
            fail('focus-not-returned', '2.4.3',
                 `it closed and focus went to ${after.activeSel} instead of ` +
                 'back to the trigger. When focus falls to <body>, a screen ' +
                 'reader user is silently returned to the top of the document ' +
                 'and the next Tab starts from the beginning of the page. ' +
                 'Store the opener on open and restore it on close.');
          }
        }
      }

      if (pattern === 'disclosure' && spec.trigger) {
        const before = await page.$eval(spec.trigger, (el) =>
          el.getAttribute('aria-expanded'));
        await page.keyboard.press('Enter');
        await page.waitForTimeout(120);
        const after = await page.evaluate((s) => ({
          expanded: document.querySelector(s).getAttribute('aria-expanded'),
          focusStayed: document.activeElement === document.querySelector(s),
        }), spec.trigger);
        if (before === after.expanded) {
          fail('disclosure-does-not-toggle', '2.1.1 / 4.1.2',
               `aria-expanded stayed "${before}" after Enter.`);
        }
        if (!after.focusStayed) {
          fail('disclosure-moves-focus', '2.4.3',
               'focus moved off the trigger. A disclosure does not move ' +
               'focus; the content appears after the trigger in the DOM and ' +
               'the user Tabs into it if they want it.');
        }
      }

      if (pattern === 'tabs' && spec.container) {
        const roving = await page.evaluate((sel) => {
          const list = document.querySelector(sel);
          if (!list) return null;
          const tabs = Array.prototype.slice.call(
            list.querySelectorAll('[role=tab]'));
          return {
            count: tabs.length,
            zeroes: tabs.filter((t) => (t.getAttribute('tabindex') || '0') === '0').length,
          };
        }, spec.container);
        if (!roving || !roving.count) {
          out.push(finding('keys', 'no-tabs-found', '-', 'warning',
            `"${name}": no [role=tab] inside "${spec.container}".`,
            PATTERN_HELP.tabs, {}));
        } else {
          if (roving.zeroes !== 1) {
            fail('no-roving-tabindex', '2.4.3',
                 `${roving.zeroes} of ${roving.count} tabs are in the tab ` +
                 'order. A composite widget is a SINGLE tab stop: one tab ' +
                 'carries tabindex="0" and the rest carry -1, and the arrow ' +
                 'keys move between them. A 40-item widget that is 40 tab ' +
                 'stops is a failure even though every item is reachable.');
          }
          const firstTab = await page.$(`${spec.container} [role=tab]`);
          if (firstTab) {
            await firstTab.evaluate((el) => el.focus({ preventScroll: true }));
            const a = await page.evaluate(() => window.__a11y.cssPath(document.activeElement));
            await page.keyboard.press('ArrowRight');
            await page.waitForTimeout(80);
            const b = await page.evaluate(() => window.__a11y.cssPath(document.activeElement));
            if (a === b) {
              fail('arrow-does-not-move', '2.1.1',
                   'ArrowRight did not move between tabs.');
            }
          }
        }
      }
    } catch (err) {
      out.push(finding('keys', 'traversal-error', '-', 'warning',
        `"${name}": ${String(err.message || err).split('\n')[0].slice(0, 160)}`,
        'The traversal could not complete. Check the selectors in the key map.',
        {}));
    }
  }
  return out;
}

// ---------------------------------------------------------------------------
// Zoom and reflow
// ---------------------------------------------------------------------------

async function checkReflow(page, opts) {
  const out = [];
  const original = page.viewportSize() || opts.viewport;
  // 1280x1024 at 400% zoom is equivalent to a 320 CSS px viewport, which is
  // how 1.4.10 is actually specified and tested.
  const steps = [
    { label: '200% zoom', width: 640, height: 512, sc: '1.4.4' },
    { label: '400% zoom / 320px reflow (1.4.10)', width: 320, height: 256, sc: '1.4.10' },
  ];
  for (const s of steps) {
    await page.setViewportSize({ width: s.width, height: s.height });
    await page.waitForTimeout(220);
    const res = await page.evaluate(() => {
      const doc = document.documentElement;
      const over = [];
      for (const el of document.querySelectorAll('body *')) {
        if (!window.__a11y.visible(el)) continue;
        const r = el.getBoundingClientRect();
        if (r.width > window.innerWidth + 2 &&
            getComputedStyle(el).overflowX !== 'auto' &&
            getComputedStyle(el).overflowX !== 'scroll') {
          over.push({ sel: window.__a11y.cssPath(el), width: Math.round(r.width) });
        }
      }
      return {
        scrollWidth: doc.scrollWidth,
        innerWidth: window.innerWidth,
        overflowing: over.slice(0, 6),
      };
    });
    if (res.scrollWidth > res.innerWidth + 2 && s.sc === '1.4.4') {
      // 1.4.4 asks that text resize to 200% without loss of content or
      // function; scrolling sideways at 200% does not fail it. Worth knowing,
      // since it is usually the 1.4.10 failure arriving early.
      out.push(finding(
        'reflow', 'horizontal-scroll-at-200-percent', '-', 'warning',
        `At ${s.label} the document scrolls horizontally: content is ` +
        `${res.scrollWidth}px wide in a ${res.innerWidth}px viewport` +
        (res.overflowing.length
          ? `. Widest: ${res.overflowing.map((o) => `${o.sel} (${o.width}px)`).join(', ')}`
          : '') + '.',
        'Not a WCAG failure at 200%. Check by eye that no text is clipped or ' +
        'overlapping, which is what 1.4.4 asks, and fix the widest element ' +
        'before it fails 1.4.10 at 400%.',
        {}));
    } else if (res.scrollWidth > res.innerWidth + 2) {
      out.push(finding(
        'reflow', 'two-dimensional-scrolling', s.sc, 'error',
        `At ${s.label} the document scrolls horizontally: content is ` +
        `${res.scrollWidth}px wide in a ${res.innerWidth}px viewport` +
        (res.overflowing.length
          ? `. Widest offender(s): ${res.overflowing.map((o) => `${o.sel} (${o.width}px)`).join(', ')}`
          : '') + '.',
        'Reflow means a user at 400% zoom reads one column and scrolls one ' +
        'way. Two-dimensional scrolling means reading every line requires a ' +
        'horizontal scroll and back, which is why the criterion exists. The ' +
        'usual causes are a fixed-width container, a table that will not ' +
        'wrap, a long unbroken string (a URL or a code sample — use ' +
        '`overflow-wrap: anywhere` on prose), and a sticky header that at ' +
        '400% eats half the viewport and should collapse. Data tables and ' +
        'maps are the specified exceptions; a marketing page is not.',
        {}));
    }
  }
  await page.setViewportSize(original);
  await page.waitForTimeout(150);
  return out;
}

// ---------------------------------------------------------------------------
// Budget
// ---------------------------------------------------------------------------

const BUDGET_KEYS = {
  axe_violations: (f) => f.filter((x) => x.check === 'axe' && !/incomplete/.test(x.rule)).length,
  axe_serious: (f) => f.filter((x) => x.check === 'axe' && x.severity === 'error').length,
  axe_incomplete: (f) => f.filter((x) => x.check === 'axe' && /incomplete/.test(x.rule)).length,
  unnamed_controls: (f) => f.filter((x) => x.rule === 'no-accessible-name').length,
  duplicate_names: (f) => f.filter((x) => x.rule === 'duplicate-name').length,
  tab_traps: (f) => f.filter((x) => x.check === 'taborder' &&
    /trap|stuck/.test(x.rule)).length,
  unreachable_controls: (f) => f.filter((x) => x.rule === 'unreachable-control').length,
  focus_invisible: (f) => f.filter((x) => x.rule === 'no-visible-focus-indicator').length,
  focus_weak: (f) => f.filter((x) => x.rule === 'weak-focus-indicator').length,
  forced_colors_lost: (f) => f.filter((x) => x.check === 'forced').length,
  contrast_failures: (f) => f.filter((x) => x.check === 'contrast' &&
    x.severity === 'error').length,
  reflow_failures: (f) => f.filter((x) => x.check === 'reflow' &&
    x.severity === 'error').length,
  keymap_failures: (f) => f.filter((x) => x.check === 'keys' &&
    x.severity === 'error').length,
};

function loadBudget(file) {
  if (!file) return null;
  if (!fs.existsSync(file)) die(`no such budget file: ${file}`);
  let data;
  try { data = readJsonFile(file); }
  catch (err) { die(`cannot parse ${file}: ${err.message}`); }
  if (data.$schema && data.$schema !== 'a11y-audit-runner/1') {
    die(`${file} declares $schema "${data.$schema}"; this tool understands ` +
        '"a11y-audit-runner/1"');
  }
  const limits = Object.assign({}, data.defaults || data);
  delete limits.$schema;
  for (const k of Object.keys(limits)) {
    if (!(k in BUDGET_KEYS)) {
      die(`${file}: unknown budget key "${k}". Known keys:\n    ` +
          Object.keys(BUDGET_KEYS).join('\n    '));
    }
  }
  return limits;
}

// ---------------------------------------------------------------------------
// Reporting
// ---------------------------------------------------------------------------

function wrap(s, width) {
  const words = String(s).split(/\s+/);
  const out = [];
  let cur = '';
  for (const w of words) {
    if (cur.length + w.length + 1 > width) { out.push(cur); cur = w; }
    else cur = cur ? `${cur} ${w}` : w;
  }
  if (cur) out.push(cur);
  return out;
}

function textReport(o, opts) {
  const L = [];
  L.push(`a11y_runtime — ${o.target}`);
  L.push(`  axe ${o.axeVersion}, tags ${o.tags.join(',')}, viewport ` +
         `${o.viewport}, checks: ${o.ran.join(' ')}` +
         (o.skipped.length ? `  (skipped: ${o.skipped.join(' ')})` : ''));
  if (o.mode === 'matrix') {
    L.push(`  proof sheet: ${o.cellsTotal} cell(s), ${o.cellsMeasured} measured`);
  }
  if (o.densities && o.densities.length) {
    L.push(`  focus also measured at data-density ${o.densities.join(', ')}`);
  }
  L.push('');

  const byCheck = new Map();
  for (const f of o.findings) {
    if (!byCheck.has(f.check)) byCheck.set(f.check, []);
    byCheck.get(f.check).push(f);
  }
  const order = ['axe', 'names', 'taborder', 'focus', 'forced', 'contrast',
                 'keys', 'reflow'];
  for (const check of order) {
    const items = byCheck.get(check);
    if (!items || !items.length) continue;
    L.push(`${check.toUpperCase()}`);
    for (const f of items) {
      const tag = f.severity === 'error' ? 'error' : 'warn ';
      L.push(`  ${tag}  ${f.rule.padEnd(32)} ${f.message}`);
      if (f.selector) L.push(`         at ${f.selector}`);
      if (f.cell) L.push(`         cell ${f.cell}`);
      if (f.nodes && f.nodes.length) {
        for (const n of f.nodes.slice(0, 4)) L.push(`         at ${n}`);
        if (f.nodes.length > 4) L.push(`         … ${f.nodes.length - 4} more`);
      }
      if (!opts.quiet) {
        L.push(`         SC ${f.sc}`);
        for (const ln of wrap(f.fix, 86)) L.push(`         ${ln}`);
      }
    }
    L.push('');
  }

  if (o.tabOrder && o.tabOrder.length) {
    L.push('Tab order as measured (the real sequence, not the DOM order)');
    // Once the sequence starts repeating it is either the legitimate wrap or a
    // trap, and printing forty rows of the same two buttons buries everything
    // above it. Print the first pass and say what happened after it.
    const seen = new Set();
    let printed = 0;
    let repeatFrom = -1;
    for (const [i, s] of o.tabOrder.entries()) {
      if (seen.has(s.sel)) { repeatFrom = i; break; }
      seen.add(s.sel);
      if (printed >= 40) { L.push(`  … ${o.tabOrder.length - printed} more`); break; }
      printed++;
      L.push(`  ${String(i + 1).padStart(3)}. ${s.sel}` +
             (s.tabindex && Number(s.tabindex) > 0 ? `  [tabindex=${s.tabindex}]` : '') +
             (s.text ? `  "${s.text}"` : ''));
    }
    if (repeatFrom >= 0) {
      const rest = o.tabOrder.slice(repeatFrom);
      const distinct = new Set(rest.map((s) => s.sel));
      L.push(`  ↺ from step ${repeatFrom + 1} the sequence repeats, cycling ` +
             `among ${distinct.size} element(s) for the remaining ` +
             `${rest.length} press(es)` +
             (distinct.size <= 3
               ? ` — ${[...distinct].join(', ')}. A cycle this short is a TRAP, ` +
                 'not a wrap.'
               : '. A full-length cycle is the normal end-of-page wrap.'));
    }
    L.push('');
  }

  if (o.focusTable && o.focusTable.length) {
    L.push('Focus indicator, measured in pixels');
    L.push('  normal   forced    contrast  element');
    for (const row of o.focusTable.slice(0, 30)) {
      const n = row.normal == null ? '   n/a' : `${(row.normal * 100).toFixed(2)}%`;
      const f = row.forced == null ? '   n/a' : `${(row.forced * 100).toFixed(2)}%`;
      const c = row.ratio == null ? '  n/a' : `${row.ratio.toFixed(2)}:1`;
      L.push(`  ${n.padStart(7)}  ${f.padStart(7)}  ${c.padStart(8)}  ${row.sel}` +
             (row.cell ? `   [${row.cell}]` : ''));
    }
    if (o.focusTable.length > 30) L.push(`  … ${o.focusTable.length - 30} more`);
    L.push('');
  }

  if (o.forcedSurvey) {
    const s = o.forcedSurvey;
    L.push('What forced-colors mode will change on this page');
    if (o.ringStats && o.ringStats.measured) {
      L.push(`  ${String(o.ringStats.lost).padStart(4)} of ` +
             `${o.ringStats.measured} measured focus ring(s) DISAPPEAR in ` +
             'forced-colors — measured in pixels, not inferred; a ring built ' +
             'only from box-shadow does not degrade there, it vanishes');
    }
    L.push(`  ${String(s.shadowOnly).padStart(4)} element(s) use box-shadow at ` +
           'rest — DISCARDED in forced-colors (every "raised" card goes flush)');
    L.push(`  ${String(s.bgImage).padStart(4)} element(s) use background-image ` +
           '— forced-colors keeps these, so a decorative image can end up the ' +
           'only thing not re-coloured');
    L.push(`  ${String(s.fillOnly).padStart(4)} control(s) are distinguished ` +
           'only by background-color with no border — filled and ghost ' +
           'buttons collapse to the same ButtonFace');
    L.push(`  ${String(s.transparentBorder).padStart(4)} element(s) have a ` +
           'transparent border — forced to a visible system colour (deliberate ' +
           'in the focus-ring bridge, a bug everywhere else)');
    L.push('');
  }

  if (o.breaches && o.breaches.length) {
    L.push('Budget breaches');
    for (const b of o.breaches) {
      L.push(`  ${b.key.padEnd(24)} ${b.actual} > ${b.limit}`);
    }
    L.push('');
  } else if (o.budgetApplied) {
    L.push('Budget: every counter is inside its limit.');
    L.push('');
  }

  const errors = o.findings.filter((f) => f.severity === 'error').length;
  const warns = o.findings.length - errors;
  L.push('Summary');
  for (const check of order) {
    const items = byCheck.get(check);
    if (!items) continue;
    const e = items.filter((f) => f.severity === 'error').length;
    L.push(`  ${check.padEnd(10)} ${String(items.length).padStart(4)} finding(s), ` +
           `${e} error(s)`);
  }
  L.push(`\n  ${errors} error(s), ${warns} warning(s).`);
  L.push('');
  for (const ln of wrap(COVERAGE_NOTE, 86)) L.push(`  ${ln}`);
  return L.join('\n') + '\n';
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main() {
  const opts = parseArgs(process.argv.slice(2));
  const axePath = resolveAxe(opts.axe);

  let target, mode;
  if (opts.url) { target = opts.url; mode = 'page'; }
  else if (opts.matrix) {
    if (!fs.existsSync(opts.matrix)) die(`no such proof sheet: ${opts.matrix}`);
    target = pathToFileURL(path.resolve(opts.matrix)).href;
    mode = 'matrix';
  } else {
    if (!fs.existsSync(opts.file)) die(`no such file: ${opts.file}`);
    target = pathToFileURL(path.resolve(opts.file)).href;
    mode = 'page';
  }

  let keymap = null;
  if (opts.keymap) {
    if (!fs.existsSync(opts.keymap)) die(`no such keymap file: ${opts.keymap}`);
    try { keymap = readJsonFile(opts.keymap); }
    catch (err) { die(`cannot parse ${opts.keymap}: ${err.message}`); }
  }
  const budget = loadBudget(opts.budget);

  const ran = ALL_CHECKS.filter((c) => !opts.skip.has(c));
  const log = (s) => { if (!opts.quiet && !opts.json) process.stderr.write(s + '\n'); };

  const { chromium } = await loadPlaywright(die, 'node a11y_runtime.mjs --url ...');
  const launched = await launchBrowser(chromium, opts.browser, {
    args: ['--force-color-profile=srgb', '--disable-lcd-text',
           '--font-render-hinting=none', '--no-sandbox',
           '--disable-dev-shm-usage'],
  });
  if (!launched.browser) {
    die('no usable chromium. Tried:\n    ' + launched.tried.join('\n    ') + '\n' +
        '  Pass --browser PATH, set A11Y_CHROMIUM, or install Chrome or Edge.\n' +
        '  This script never downloads a browser: a gate that pulls 150MB on ' +
        'every CI run is a gate somebody turns off.');
  }
  if (launched.auto) log(`browser: ${launched.label}`);
  const browser = launched.browser;

  const findings = [];
  let axeVersion = '?';
  let tabOrder = null;
  let focusTable = [];
  let forcedSurvey = null;
  let ringStats = null;
  let forcedSupported = false;
  let densities = [];
  let cellsTotal = 0, cellsMeasured = 0;

  const newPage = async (forcedColors) => {
    const ctx = await browser.newContext({
      viewport: opts.viewport,
      deviceScaleFactor: opts.dpr,
      forcedColors: forcedColors || 'none',
      colorScheme: 'light',
      locale: 'en-US',
      timezoneId: 'UTC',
      reducedMotion: 'no-preference',
      // A strict Content-Security-Policy refuses the stylesheet and scripts
      // this run injects; the audit is of the page, not of its CSP (GT-A5).
      bypassCSP: true,
    });
    await ctx.addInitScript(HELPERS);
    const page = await ctx.newPage();
    const resp = await page.goto(target, { waitUntil: 'load', timeout: 45000 })
      .catch((err) => { die(`could not load ${target}: ${err.message.split('\n')[0]}`); });
    if (resp && !resp.ok() && /^https?:/.test(target)) {
      die(`${target} returned HTTP ${resp.status()}. Audit a page that loads.`);
    }
    await page.evaluate(async () => {
      if (document.fonts && document.fonts.ready) await document.fonts.ready;
      if (typeof window.matrixShowAll === 'function') window.matrixShowAll();
    });
    // Animations stop and transitions finish: a ring measured mid-transition is
    // a false negative, and a spinner still turning a false positive (GT-A14).
    await page.addStyleTag({ content: FREEZE_ANIMATIONS_CSS });
    await page.evaluate(() => new Promise((r) =>
      requestAnimationFrame(() => requestAnimationFrame(r))));
    return { ctx, page };
  };

  try {
    const { ctx, page } = await newPage('none');
    const cmpCtx = await browser.newContext({ bypassCSP: true });
    const cmpPage = await cmpCtx.newPage();
    await cmpPage.goto('about:blank');

    axeVersion = await injectAxe(page, axePath);
    log(`  axe-core ${axeVersion} injected from ${path.relative(process.cwd(), axePath)}`);

    let cellIds = [];
    if (mode === 'matrix') {
      cellIds = await page.$$eval('[data-cell-id]', (els) =>
        els.map((e) => e.getAttribute('data-cell-id')));
      cellsTotal = cellIds.length;
      if (!cellIds.length) {
        die(`${opts.matrix} contains no [data-cell-id] elements. Generate it ` +
            'with component-state-matrix\'s generate_matrix.py, or point ' +
            '--matrix at the right file.');
      }
      if (opts.only.length) {
        cellIds = cellIds.filter((id) => opts.only.some((s) => id.includes(s)));
        if (!cellIds.length) die(`--only ${opts.only.join(', ')} matched no cells.`);
      }
      if (cellIds.length > opts.maxCells) {
        log(`  ${cellIds.length} cells; measuring the first ${opts.maxCells} ` +
            '(raise with --max-cells, or narrow with --only)');
        cellIds = cellIds.slice(0, opts.maxCells);
      }
      cellsMeasured = cellIds.length;
    }

    // ---- axe -------------------------------------------------------------
    if (ran.includes('axe')) {
      log('  axe…');
      const res = await runAxe(page, opts.tags, null);
      const af = axeFindings(res);
      if (mode === 'matrix') {
        // A proof sheet is generated scaffolding wrapped around your
        // components. A violation in the sheet's own filter bar is not a
        // finding about your design system, and reporting it as one is how a
        // team learns to ignore this whole report. Violations are attributed
        // to the cell they landed in; the rest are kept, clearly labelled,
        // and demoted.
        for (const f of af) {
          if (!f.cells || !f.cells.length) {
            f.severity = 'warning';
            f.rule = `${f.rule} (sheet chrome)`;
            f.fix = 'This landed in the proof sheet\'s own scaffolding, not ' +
              'inside a [data-cell-id] cell, so it is a finding about the ' +
              'generated page rather than about your components. Demoted, not ' +
              'hidden: if it is in a template the generator emits, it is worth ' +
              'a bug report to component-state-matrix. ' + f.fix;
          }
        }
      }
      findings.push(...af);
    }

    // ---- names -----------------------------------------------------------
    if (ran.includes('names')) {
      log('  accessible names…');
      const scope = mode === 'matrix' ? '[data-cell-id]' : null;
      const controls = await collectNames(page, scope);
      findings.push(...nameFindings(controls));
    }

    // ---- tab order -------------------------------------------------------
    let stopSelectors = [];
    if (mode === 'page' && ran.includes('taborder')) {
      log('  tab order…');
      const expected = await page.evaluate(() => window.__a11y.expectedTabbables());
      const steps = Math.min(400, expected.length * 2 + 20);
      const forward = await tabSequence(page, { steps, shift: false });
      const reverse = await tabSequence(page, { steps, shift: true });
      findings.push(...analyseTabOrder(forward, reverse, expected, opts));
      tabOrder = forward.filter((s) => s.sel !== '(document)');
      const seen = new Set();
      stopSelectors = [...tabOrder.map((s) => s.sel), ...expected.map((e) => e.sel)]
        .filter((s) => s && !seen.has(s) && seen.add(s))
        .slice(0, opts.maxStops);
    } else if (mode === 'page') {
      const expected = await page.evaluate(() => window.__a11y.expectedTabbables());
      stopSelectors = expected.map((e) => e.sel).slice(0, opts.maxStops);
    }

    // In matrix mode the focus targets are the interactive elements inside
    // each cell: the whole point is proving the ring renders in every state,
    // density and theme, which is the one thing a page-level audit never sees.
    let cellOf = new Map();
    if (mode === 'matrix') {
      const perCell = await page.evaluate(({ ids }) => {
        const out = [];
        for (const id of ids) {
          const cell = document.querySelector(`[data-cell-id="${CSS.escape(id)}"]`);
          if (!cell) continue;
          const els = cell.querySelectorAll(window.__a11y.FOCUSABLE);
          for (const el of els) {
            if (!window.__a11y.visible(el)) continue;
            if (el.disabled) continue;
            out.push({ sel: window.__a11y.cssPath(el), cell: id });
            break;                       // one representative control per cell
          }
        }
        return out;
      }, { ids: cellIds });
      stopSelectors = perCell.map((p) => p.sel).slice(0, opts.maxCells);
      cellOf = new Map(perCell.map((p) => [p.sel, p.cell]));
    }

    // ---- focus visibility -------------------------------------------------
    let normalFocus = [];
    if (ran.includes('focus') && stopSelectors.length) {
      log(`  focus indicator on ${stopSelectors.length} element(s)…`);
      normalFocus = await measureFocus(page, cmpPage, stopSelectors, opts, 'normal');
      for (const m of normalFocus) m.cell = cellOf.get(m.sel) || null;
      findings.push(...focusFindings(normalFocus, opts));
    }

    // ---- contrast ---------------------------------------------------------
    if (ran.includes('contrast')) {
      log('  contrast from computed styles…');
      const samples = await page.evaluate(CONTRAST_FN);
      findings.push(...contrastFindings(samples));
    }

    // ---- keyboard traversal ----------------------------------------------
    if (ran.includes('keys')) {
      if (keymap) {
        log('  keyboard traversal…');
        findings.push(...await runKeymap(page, keymap));
      } else if (mode === 'page') {
        findings.push(finding(
          'keys', 'no-keymap', '2.1.1', 'warning',
          'No --keymap was given, so no composite widget was driven.',
          'Every dialog, menu, tab set, disclosure and combobox on this page ' +
          'is currently unverified. Write a keymap file naming each one and ' +
          'its pattern; the expected key behaviour comes from ' +
          'web-design-studio/references/accessibility.md §4, which is the ' +
          'behaviour users have already learned elsewhere. Example: {"patterns":' +
          '[{"name":"Account menu","pattern":"menu","trigger":"#acct",' +
          '"container":"#acct-menu","items":"[role=menuitem]"}]}',
          {}));
      }
    }

    // ---- reflow -----------------------------------------------------------
    if (ran.includes('reflow') && mode === 'page') {
      log('  zoom and reflow…');
      findings.push(...await checkReflow(page, opts));
    }

    // ---- forced colors ----------------------------------------------------
    if (ran.includes('forced')) {
      log('  forced-colors…');
      forcedSurvey = await forcedColorsSurvey(page);
      const { ctx: fctx, page: fpage } = await newPage('active');
      const supported = await fpage.evaluate(() =>
        matchMedia('(forced-colors: active)').matches);
      forcedSupported = supported;
      if (!supported) {
        findings.push(finding(
          'forced', 'forced-colors-not-emulated', '-', 'warning',
          'The browser did not report forced-colors: active under emulation.',
          'Without it this check is meaningless, so it was skipped rather ' +
          'than reported as a pass. Update Playwright/Chromium, and verify on ' +
          'real Windows High Contrast before launch either way — emulation is ' +
          'close, and the real thing also changes the system colour values.',
          {}));
      } else if (stopSelectors.length) {
        const forcedFocus = await measureFocus(fpage, cmpPage, stopSelectors,
                                               opts, 'forced');
        for (const m of forcedFocus) m.cell = cellOf.get(m.sel) || null;
        findings.push(...forcedColorFindings(normalFocus, forcedFocus, opts));
        const fmap = new Map(forcedFocus.map((m) => [m.sel, m]));
        ringStats = {
          measured: normalFocus.filter((m) => m.ok && m.fraction >= opts.focusThreshold).length,
          lost: normalFocus.filter((m) => {
            const f = fmap.get(m.sel);
            return m.ok && f && f.ok && m.fraction >= opts.focusThreshold &&
              f.fraction < opts.focusThreshold;
          }).length,
        };
        focusTable = normalFocus.map((m) => ({
          sel: m.sel, cell: m.cell,
          normal: m.ok ? m.fraction : null,
          forced: fmap.get(m.sel) && fmap.get(m.sel).ok ? fmap.get(m.sel).fraction : null,
          ratio: m.ratio,
        }));
      }
      await fctx.close().catch(() => {});
    }

    // ---- density ----------------------------------------------------------
    // The starter's density dial (data-density on the root) rescales every
    // gap and padding, so a ring that fits at one density can be clipped by an
    // overflow at another. On a page, focus is measured again at each density
    // its stylesheets name, in normal colours and, when forced runs, under
    // forced colours (SB-B3). A proof sheet has a cell per density already.
    // What the default density already reported is not reported again.
    if (mode === 'page' && stopSelectors.length && opts.densities !== 'none' &&
        (ran.includes('focus') || ran.includes('forced'))) {
      const declared = await page.evaluate(DENSITIES_FN);
      densities = (opts.densities === 'auto' ? declared.found : opts.densities)
        .filter((d) => d !== declared.current);
      const known = new Set(findings.map((f) => `${f.rule}|${f.selector}`));
      const atDensity = (list, d) => list
        .filter((f) => !known.has(`${f.rule}|${f.selector}`))
        .map((f) => ({ ...f, density: d,
          message: `${f.message.replace(/\.$/, '')} at data-density="${d}".` }));
      const forcedPage = ran.includes('forced') && forcedSupported && densities.length
        ? await newPage('active') : null;
      for (const d of densities) {
        log(`  focus at data-density="${d}"…`);
        await setDensity(page, d);
        const normal = await measureFocus(page, cmpPage, stopSelectors, opts, `normal@${d}`);
        if (ran.includes('focus')) findings.push(...atDensity(focusFindings(normal, opts), d));
        if (forcedPage) {
          await setDensity(forcedPage.page, d);
          const forced = await measureFocus(forcedPage.page, cmpPage, stopSelectors, opts,
                                            `forced@${d}`);
          findings.push(...atDensity(forcedColorFindings(normal, forced, opts), d));
        }
      }
      if (densities.length) await setDensity(page, declared.current);
      if (forcedPage) await forcedPage.ctx.close().catch(() => {});
    }

    if (!focusTable.length && normalFocus.length) {
      focusTable = normalFocus.map((m) => ({
        sel: m.sel, cell: m.cell, normal: m.ok ? m.fraction : null,
        forced: null, ratio: m.ratio,
      }));
    }

    await cmpCtx.close().catch(() => {});
    await ctx.close().catch(() => {});
  } finally {
    await browser.close().catch(() => {});
  }

  findings.sort((a, b) => (a.severity === b.severity ? 0 :
    a.severity === 'error' ? -1 : 1));

  const counters = {};
  for (const [k, fn] of Object.entries(BUDGET_KEYS)) counters[k] = fn(findings);
  const breaches = [];
  if (budget) {
    for (const [k, limit] of Object.entries(budget)) {
      if (counters[k] > limit) breaches.push({ key: k, actual: counters[k], limit });
    }
  }

  const out = {
    tool: 'a11y_runtime',
    coverageNote: COVERAGE_NOTE,
    target, mode,
    axeVersion,
    tags: opts.tags,
    viewport: `${opts.viewport.width}x${opts.viewport.height}@${opts.dpr}x`,
    ran, skipped: [...opts.skip],
    cellsTotal, cellsMeasured,
    counters,
    budgetApplied: Boolean(budget),
    budget, breaches,
    findings,
    tabOrder,
    focusTable,
    densities,
    forcedSurvey,
    ringStats,
  };

  if (opts.report) {
    fs.mkdirSync(path.dirname(path.resolve(opts.report)), { recursive: true });
    fs.writeFileSync(opts.report, JSON.stringify(out, null, 2) + '\n');
  }
  process.stdout.write(opts.json
    ? JSON.stringify(out, null, 2) + '\n'
    : textReport(out, opts));

  const errors = findings.filter((f) => f.severity === 'error').length;
  return (errors || breaches.length) ? 1 : 0;
}

// 1 means the page has violations, so a run that failed exits 2 (GT-A5).
main().then((code) => process.exit(code)).catch((err) => {
  process.stderr.write(`a11y_runtime: the run failed: ${err && err.stack ? err.stack : err}\n`);
  process.exit(2);
});
