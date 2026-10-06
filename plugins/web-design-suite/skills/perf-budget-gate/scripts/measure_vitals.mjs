#!/usr/bin/env node
/**
 * measure_vitals.mjs — the runtime half of the performance gate.
 *
 * `perf_audit.py` reads bytes and markup. This opens a real browser and
 * produces the only numbers that are actually LCP, CLS and main-thread
 * blocking time. It is slower, noisier and needs care to stay non-flaky, which
 * is exactly why it is the SECOND layer: install the static gate first, get it
 * green, then add this deliberately.
 *
 * What it measures, from real PerformanceObserver entries
 * -------------------------------------------------------
 *   LCP   largest-contentful-paint, last entry, plus the element's CSS
 *         selector and the four sub-parts (TTFB, resource load delay,
 *         resource load duration, element render delay)
 *   CLS   layout-shift, session-windowed exactly as the metric defines it:
 *         1s gap, 5s cap, largest window wins, hadRecentInput excluded
 *   TBT   longtask, sum of (duration - 50ms) between FCP and TTI (the end of
 *         the last long task before 5 quiet seconds), leaving out the work
 *         of an interaction, which INP counts. This is the LAB PROXY for
 *         INP, not INP. See --interact for a real interaction.
 *   INP   only when --interact drives one; a page nobody touched has no
 *         interaction latency and this prints "n/a" rather than inventing one
 *   TTFB  the document's, from the network stack (CDP): Navigation Timing
 *         reports it before the emulated latency
 *
 * It runs N iterations in fresh contexts and reports the MEDIAN plus the
 * spread, because a single run of anything is a rumour.
 *
 * Lab is not field. A CI number is a REGRESSION DETECTOR against itself on
 * one machine with one throttle profile. It does not predict what your users
 * experience; only p75 of real field data does that (CrUX, or web-vitals in
 * your own RUM). Read references/budgets.md §8 before anyone quotes a number
 * from here in a meeting.
 *
 * Usage
 * -----
 *   node measure_vitals.mjs http://localhost:8080/
 *   node measure_vitals.mjs http://localhost:8080/ --runs 7 --throttle lighthouse
 *   node measure_vitals.mjs http://localhost:8080/ --budget perf-budget.json
 *   node measure_vitals.mjs http://localhost:8080/ --interact "button.buy" --json
 *   node measure_vitals.mjs http://localhost:8080/ --interact "button.buy" --interact-at 800
 *
 * Serve the page over HTTP. `file://` skips the network stack entirely, so
 * TTFB is ~0, resource priorities do not apply and every number flatters you.
 * This script warns and keeps going if you insist.
 *
 * Options
 * -------
 *   --runs N           iterations; median is reported          (default 5)
 *   --throttle NAME    lighthouse | slow4g | fast4g | cpu4 | off
 *                      (default lighthouse: 562.5ms per request, 1.44Mbps,
 *                      4x CPU, what Lighthouse applies for 150ms RTT at
 *                      1.6Mbps; slow4g and fast4g are lighter, see THROTTLE)
 *   --budget FILE      perf-budget.json; compares defaults.lab
 *   --page-type NAME   select a per-page-type budget from `pages`
 *   --interact SEL     click this selector after load and measure INP
 *   --interact-at MS   click it MS after navigation starts instead, while
 *                      the page still loads and hydrates
 *   --warm             measure the SECOND load (warm cache) instead of a cold one
 *   --settle MS        quiet time after load before reading   (default 3000)
 *   --viewport WxH     viewport                             (default 412x915)
 *   --dpr N            device pixel ratio                        (default 2)
 *   --resources N      how many of the largest resources to print (default 10)
 *   --json             machine-readable output
 *   --report FILE      also write the --json output to FILE; the text report
 *                      still prints, so a CI log has something a person reads
 *   --browser PATH     chromium executable   (default: found, see below)
 *   --quiet
 *
 * The browser is NEVER downloaded. It launches with an explicit
 * executablePath: --browser, else PERF_CHROMIUM, else the first that starts of
 * /opt/pw-browsers/chromium, Playwright's own Chromium, and an installed
 * Chrome or Edge. It fails with instructions if none of them starts.
 * Install the module with PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 npm i -D -E playwright
 * to use the Chrome you have. In CI, pin the browser instead: install the
 * Chromium the locked Playwright was built for (npx playwright install
 * chromium), which this script tries first. references/ci-integration.md §3.
 *
 * Exit codes
 * ----------
 *   0  every measured metric is inside its budget (or no budget was given)
 *   1  a budget was breached, or a run failed to produce a metric
 *   2  bad arguments, no usable browser, or the run itself failed (the
 *      page did not load, or a crash): a crash is never a breach
 */

import { pathToFileURL } from 'node:url';
import fs from 'node:fs';
import path from 'node:path';

import { launchBrowser, loadPlaywright, readJsonFile } from './browser_common.mjs';

// Lighthouse's mobile profile is 150 ms RTT, 1.6 Mbps down, 750 Kbps up and
// 4x CPU. CDP adds its latency to each request once, where a round trip is
// paid several times by a new connection (DNS, TCP, TLS, the request), so
// Lighthouse's own DevTools throttling applies 150 x 3.75 = 562.5 ms per
// request and 0.9 of the throughput (DEVTOOLS_RTT_ADJUSTMENT_FACTOR and
// DEVTOOLS_THROUGHPUT_ADJUSTMENT_FACTOR, Lantern's Constants.ts, re-read
// 2026-10-05). That is `lighthouse`, the default (GT-A6). `slow4g` and
// `fast4g` are 3.3.0's presets, kept for runs compared with old numbers:
// their 150 ms and 40 ms per request are lighter than Lighthouse, and than
// DevTools' Slow 4G (562.5 ms) and Fast 4G (165 ms).
const KBPS = 1024 / 8;      // Lighthouse's Kbps, in the bytes per second CDP wants
const THROTTLE = {
  lighthouse: { latency: 150 * 3.75, down: 1.6 * 1024 * 0.9 * KBPS, up: 750 * 0.9 * KBPS, cpu: 4 },
  slow4g: { latency: 150, down: 1.6 * 1024 * KBPS, up: 750 * KBPS, cpu: 4 },
  fast4g: { latency: 40, down: 9 * 1024 * KBPS, up: 1.5 * 1024 * KBPS, cpu: 4 },
  cpu4:   { latency: 0, down: -1, up: -1, cpu: 4 },
  off:    { latency: 0, down: -1, up: -1, cpu: 1 },
};

// ---------------------------------------------------------------------------
// Arguments
// ---------------------------------------------------------------------------

function die(msg, code = 2) {
  process.stderr.write(`measure_vitals: ${msg}\n`);
  process.exit(code);
}

function parseArgs(argv) {
  const opts = {
    target: null,
    runs: 5,
    throttle: 'lighthouse',
    budget: null,
    pageType: null,
    interact: null,
    interactAt: null,
    warm: false,
    settle: 3000,
    viewport: { width: 412, height: 915 },
    dpr: 2,
    resources: 10,
    json: false,
    report: null,
    browser: process.env.PERF_CHROMIUM || '',
    quiet: false,
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
      case '--runs': opts.runs = num(need(i, a), a); i++; break;
      case '--throttle': opts.throttle = need(i, a); i++; break;
      case '--budget': opts.budget = need(i, a); i++; break;
      case '--page-type': opts.pageType = need(i, a); i++; break;
      case '--interact': opts.interact = need(i, a); i++; break;
      case '--interact-at': opts.interactAt = num(need(i, a), a); i++; break;
      case '--warm': opts.warm = true; break;
      case '--settle': opts.settle = num(need(i, a), a); i++; break;
      case '--dpr': opts.dpr = num(need(i, a), a); i++; break;
      case '--resources': opts.resources = num(need(i, a), a); i++; break;
      case '--json': opts.json = true; break;
      case '--report': opts.report = need(i, a); i++; break;
      case '--browser': opts.browser = need(i, a); i++; break;
      case '--quiet': opts.quiet = true; break;
      case '--viewport': {
        const v = need(i, a); i++;
        const m = /^(\d+)x(\d+)$/.exec(v);
        if (!m) die(`--viewport must look like 412x915, got "${v}"`);
        opts.viewport = { width: Number(m[1]), height: Number(m[2]) };
        break;
      }
      default:
        if (a.startsWith('-')) die(`unknown option ${a} (try --help)`);
        else if (opts.target) die(`more than one target: ${opts.target} and ${a}`);
        else opts.target = a;
    }
  }
  if (!opts.target) die('needs a URL or file to measure (try --help)');
  if (!THROTTLE[opts.throttle]) {
    die(`unknown --throttle "${opts.throttle}"; pick one of ` +
        Object.keys(THROTTLE).join(', '));
  }
  if (!(opts.runs >= 1)) die('--runs must be at least 1');
  if (opts.interactAt != null) {
    if (!opts.interact) die('--interact-at MS needs --interact SELECTOR: it says when, not what');
    if (opts.interactAt < 0) die('--interact-at must be 0 or more milliseconds');
  }
  return opts;
}

function resolveTarget(target) {
  if (/^https?:\/\//i.test(target)) return { url: target, isFile: false };
  if (/^file:\/\//i.test(target)) return { url: target, isFile: true };
  const p = path.resolve(target);
  if (!fs.existsSync(p)) die(`no such URL or file: ${target}`);
  return { url: pathToFileURL(p).href, isFile: true };
}

// ---------------------------------------------------------------------------
// Playwright, resolved without ever downloading anything
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// The in-page collector.
//
// Injected with addInitScript so it runs BEFORE any page script. Every
// observer uses buffered:true as well, so an entry emitted during the gap
// between navigation commit and script execution is still delivered.
// ---------------------------------------------------------------------------

const COLLECTOR = () => {
  const store = {
    lcp: null,
    lcpSelector: null,
    lcpUrl: null,
    lcpSize: 0,
    cls: 0,
    clsSources: [],
    fcp: null,
    longTasks: [],
    interactions: [],
    errors: [],
  };
  window.__vitals = store;

  const cssPath = (el) => {
    if (!el || el.nodeType !== 1) return null;
    const parts = [];
    let node = el;
    while (node && node.nodeType === 1 && parts.length < 6) {
      let part = node.nodeName.toLowerCase();
      if (node.id) { parts.unshift(`${part}#${node.id}`); break; }
      const cls = (node.getAttribute('class') || '').trim()
        .split(/\s+/).filter(Boolean).slice(0, 2);
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

  const observe = (type, cb, extra) => {
    try {
      const po = new PerformanceObserver((list) => list.getEntries().forEach(cb));
      po.observe(Object.assign({ type, buffered: true }, extra || {}));
      return po;
    } catch (err) {
      store.errors.push(`${type}: ${err.message}`);
      return null;
    }
  };

  // -- LCP: the LAST entry wins; earlier ones are superseded candidates.
  observe('largest-contentful-paint', (e) => {
    store.lcp = e.startTime;
    store.lcpSize = e.size;
    store.lcpUrl = e.url || null;
    store.lcpSelector = cssPath(e.element) ||
      (e.url ? `(element detached) ${e.url}` : null);
  });

  // -- FCP, needed as the start of the TBT window.
  observe('paint', (e) => {
    if (e.name === 'first-contentful-paint') store.fcp = e.startTime;
  });

  // -- CLS: session windows, exactly as the metric defines them. A burst is
  //    shifts less than 1s apart, capped at 5s total, and CLS is the LARGEST
  //    burst — not the sum of every shift on the page.
  let winValue = 0;
  let winEntries = [];
  observe('layout-shift', (e) => {
    if (e.hadRecentInput) return;              // within 500ms of an input: expected
    const first = winEntries[0];
    const last = winEntries[winEntries.length - 1];
    if (winEntries.length &&
        e.startTime - last.startTime < 1000 &&
        e.startTime - first.startTime < 5000) {
      winValue += e.value;
      winEntries.push(e);
    } else {
      winValue = e.value;
      winEntries = [e];
    }
    if (winValue > store.cls) {
      store.cls = winValue;
      store.clsSources = winEntries.map((s) => ({
        value: Number(s.value.toFixed(5)),
        at: Math.round(s.startTime),
        nodes: Array.prototype.map.call(
          s.sources || [], (src) => cssPath(src.node)).filter(Boolean).slice(0, 3),
      }));
    }
  });

  // -- Long tasks: the raw material of TBT. The API only reports >50ms.
  observe('longtask', (e) => {
    store.longTasks.push({ start: e.startTime, duration: e.duration });
  });

  // -- Interactions: real INP inputs, when something actually interacts.
  observe('event', (e) => {
    if (!e.interactionId) return;
    store.interactions.push({
      name: e.name,
      duration: e.duration,
      inputDelay: Math.round(e.processingStart - e.startTime),
      processing: Math.round(e.processingEnd - e.processingStart),
      presentation: Math.round(e.startTime + e.duration - e.processingEnd),
      // Absolute times, to keep the interaction's own work out of TBT.
      at: e.startTime,
      handlerStart: e.processingStart,
      end: e.startTime + e.duration,
    });
  }, { durationThreshold: 16 });
};

// Read everything back out. Runs after the settle window.
const HARVEST = ({ topN, ttfb: networkTtfb, requests: networkRequests }) => {
  const v = window.__vitals || {};
  const nav = performance.getEntriesByType('navigation')[0] || {};
  // The network stack's TTFB when CDP gave one: Navigation Timing's
  // responseStart comes before the emulated latency (GT-A6).
  const ttfb = networkTtfb != null ? networkTtfb : (nav.responseStart || 0);

  const resources = performance.getEntriesByType('resource').map((r) => ({
    name: r.name,
    type: r.initiatorType,
    transfer: r.transferSize || 0,
    encoded: r.encodedBodySize || 0,
    start: Math.round(r.startTime),
    duration: Math.round(r.duration),
    end: Math.round(r.responseEnd),
  }));

  // An interaction's own work belongs to INP, not TBT: a long task that
  // starts after the input and runs into its handlers is left out, or
  // --interact counted the handler twice (GT-A17). A task the input waited
  // behind started before it, or ended before the handlers, and stays: that
  // is the page's work.
  // The diagnostics below (count, longest, total) keep every long task.
  const ends = (t) => t.start + t.duration;
  const own = v.interactions || [];
  const allTasks = v.longTasks || [];
  const tasks = allTasks.filter((t) => !own.some((i) =>
    t.start >= i.at && t.start < i.end && ends(t) > i.handlerStart));

  // TBT: blocking time is (duration - 50ms), summed over long tasks between
  // FCP and TTI. The window starts at FCP by definition, so a 400ms
  // parser-blocking script that finishes before anything has painted
  // contributes ZERO TBT while being the worst thing on the page. That is a
  // real gap in the metric, not a bug here, so the total over every long
  // task is reported alongside it.
  const fcp = v.fcp || 0;
  // TTI: the end of the last long task before the first 5-second window
  // after FCP with no long task and at most two requests in flight. When no
  // such window fits in the run, every long task in it is before TTI. The
  // requests come from CDP, unfinished ones included (an end of null): a
  // request still in flight has no Resource Timing entry, so a page with
  // three hanging fetches looked quiet (Codex on #45).
  const now = performance.now();
  const requests = (networkRequests ||
    [[0, nav.responseEnd || 0], ...resources.map((r) => [r.start, r.end])])
    .map(([a, b]) => [a, b == null ? Infinity : b]);
  const busiest = (s, e) => {
    const marks = requests.filter(([a, b]) => a < e && b > s)
      .flatMap(([a, b]) => [[Math.max(a, s), 1], [Math.min(b, e), -1]])
      .sort((x, y) => x[0] - y[0] || x[1] - y[1]);
    let n = 0;
    let peak = 0;
    for (const [, d] of marks) { n += d; peak = Math.max(peak, n); }
    return peak;
  };
  let tti = null;
  const candidates = [fcp, ...tasks.map(ends), ...requests.map((r) => r[1])]
    .filter((s) => s >= fcp && Number.isFinite(s)).sort((a, b) => a - b);
  for (const s of candidates) {
    const e = s + 5000;
    if (e > now) break;
    if (tasks.some((t) => t.start < e && ends(t) > s) || busiest(s, e) > 2) continue;
    tti = Math.max(fcp, ...tasks.filter((t) => ends(t) <= s).map(ends));
    break;
  }
  const tbt = tasks
    .filter((t) => ends(t) > fcp && (tti == null || t.start < tti))
    .reduce((sum, t) => sum + Math.max(0, t.duration - 50), 0);
  const blockingTotal = allTasks
    .reduce((sum, t) => sum + Math.max(0, t.duration - 50), 0);
  const longestTask = allTasks.reduce((m, t) => Math.max(m, t.duration), 0);

  // The four LCP sub-parts, when the LCP element is a resource we can find.
  let phases = null;
  if (v.lcp != null) {
    const res = v.lcpUrl ? resources.find((r) => r.name === v.lcpUrl) : null;
    if (res) {
      phases = {
        ttfb: Math.round(ttfb),
        loadDelay: Math.round(res.start - ttfb),
        loadDuration: Math.round(res.end - res.start),
        renderDelay: Math.round(v.lcp - res.end),
      };
    } else {
      // A text LCP element has no resource: everything after TTFB is render
      // delay, which is the honest description.
      phases = {
        ttfb: Math.round(ttfb),
        loadDelay: 0,
        loadDuration: 0,
        renderDelay: Math.round(v.lcp - ttfb),
      };
    }
  }

  const inp = (v.interactions || []).length
    ? Math.max(...v.interactions.map((i) => i.duration))
    : null;

  return {
    lcp: v.lcp,
    lcpSelector: v.lcpSelector,
    lcpUrl: v.lcpUrl,
    lcpSize: v.lcpSize,
    lcpPhases: phases,
    cls: Number((v.cls || 0).toFixed(5)),
    clsSources: v.clsSources || [],
    fcp: v.fcp,
    ttfb: Math.round(ttfb),
    tti: tti == null ? null : Math.round(tti),
    tbt: Math.round(tbt),
    blockingTotal: Math.round(blockingTotal),
    longestTask: Math.round(longestTask),
    longTaskCount: allTasks.length,
    inp,
    interactions: v.interactions || [],
    resourceCount: resources.length,
    transferTotal: resources.reduce((s, r) => s + r.transfer, 0),
    resources: resources.sort((a, b) => b.transfer - a.transfer).slice(0, topN),
    observerErrors: v.errors || [],
  };
};

// ---------------------------------------------------------------------------
// One run
// ---------------------------------------------------------------------------

// --interact-at: click while the page still loads, where hydration makes INP
// worst (references/diagnosis.md §8); --interact alone clicks after the
// settle time (GT-C11). The target is found as soon as it is visible, and the
// click goes through the browser's input pipeline at MS after navigation
// starts, so it queues behind whatever task holds the main thread then, as a
// user's does. MS counts from the page's own time origin: a cold browser can
// take half a second to send the request. The wait is read off the page's
// clock (performance.now), not Date.now() against performance.timeOrigin:
// those are two processes' wall clocks, which a busy CI machine can skew
// apart. Returns when it clicked, on the page's clock, or null.
// The document's TTFB in ms from CDP: from the request's first timestamp
// (seconds) to the end of its headers, or null when CDP left the timing
// unset (it marks an unset field -1), so Navigation Timing stands in.
// test_browser_scripts.VitalsTiming runs this function on its own.
function networkTtfb(start, timing) {
  if (!timing || !(timing.requestTime > 0) || !(timing.receiveHeadersEnd >= 0)) return null;
  return (timing.requestTime - start) * 1000 + timing.receiveHeadersEnd;
}

// The page's clock against Node's monotonic one, paired as NTP pairs them:
// a reading taken between `sent` and `back` is good to half that round trip,
// whether the request queued or the reply stalled, so the narrowest of three
// samples wins. Returns page time minus Node time.
// test_browser_scripts.VitalsTiming runs this function on its own.
async function pageClockOffset(readPage, now, samples = 3) {
  let best = null;
  for (let i = 0; i < samples; i++) {
    const sent = now();
    const pageNow = await readPage();
    const back = now();
    if (!best || back - sent < best.rtt) best = { rtt: back - sent, offset: pageNow - (sent + back) / 2 };
  }
  return best.offset;
}

async function clickDuringLoad(page, opts) {
  try {
    const target = page.locator(opts.interact).first();
    await target.waitFor({ state: 'visible', timeout: opts.interactAt + 10000 });
    const box = await target.boundingBox();
    if (!box) throw new Error('the target has no layout box');
    const offset = await pageClockOffset(() => page.evaluate(() => performance.now()),
                                         () => performance.now());
    const onPage = () => performance.now() + offset;
    const wait = opts.interactAt - onPage();
    if (wait > 0) await new Promise((r) => setTimeout(r, wait));
    const at = Math.round(onPage());
    await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
    return at;
  } catch (err) {
    process.stderr.write(
      `measure_vitals: --interact "${opts.interact}" with --interact-at ` +
      `${opts.interactAt} did not click: ${err.message.split('\n')[0]}\n`);
    return null;
  }
}

async function runOnce(browser, opts, url) {
  const t = THROTTLE[opts.throttle];
  const context = await browser.newContext({
    viewport: opts.viewport,
    deviceScaleFactor: opts.dpr,
    locale: 'en-US',
    timezoneId: 'UTC',
    colorScheme: 'light',
    // Reduced motion OFF on purpose: the animations users see are the
    // animations whose cost we are measuring.
    // No bypassCSP, unlike the other two scripts: the collector is an init
    // script, which CSP does not govern, and a bypass would load what the
    // page's CSP blocks, so the numbers would describe a page no user gets.
  });
  try {
    const page = await context.newPage();
    await page.addInitScript(COLLECTOR);

    const cdp = await context.newCDPSession(page);
    await cdp.send('Network.enable');
    await cdp.send('Network.emulateNetworkConditions', {
      offline: false,
      latency: t.latency,
      downloadThroughput: t.down,
      uploadThroughput: t.up,
      connectionType: 'cellular4g',
    });
    await cdp.send('Emulation.setCPUThrottlingRate', { rate: t.cpu });

    // The document's time to first byte, as the network stack saw it:
    // receiveHeadersEnd comes after CDP's emulated latency, and Navigation
    // Timing's responseStart before it, so `--throttle slow4g` reported a
    // TTFB of 5 ms (GT-A6). Redirects keep the request id, so it counts them.
    let doc = null;
    // Every GET from its start to its end, for TTI's network-quiet test: a
    // request still in flight when the run is read keeps an end of null.
    let flights = new Map();
    cdp.on('Network.requestWillBeSent', (e) => {
      if (!doc && e.type === 'Document') doc = { id: e.requestId, start: e.timestamp, ttfb: null };
      if (e.request.method === 'GET' && !/^data:/.test(e.request.url) && !flights.has(e.requestId)) {
        flights.set(e.requestId, [e.timestamp, null]);
      }
    });
    const landed = (e) => {
      const flight = flights.get(e.requestId);
      if (flight) flight[1] = e.timestamp;
    };
    cdp.on('Network.loadingFinished', landed);
    cdp.on('Network.loadingFailed', landed);
    cdp.on('Network.responseReceived', (e) => {
      if (doc && e.requestId === doc.id && doc.ttfb == null) {
        doc.ttfb = networkTtfb(doc.start, e.response && e.response.timing);
      }
    });

    if (opts.warm) {
      await page.goto(url, { waitUntil: 'load', timeout: 60000 });
      await page.waitForTimeout(500);
      // Second load in the same context: HTTP cache is warm, observers are
      // re-installed by addInitScript, counters start from zero.
      doc = null;
      flights = new Map();
    }

    let clickedAt = null;
    if (opts.interactAt != null) {
      await page.goto(url, { waitUntil: 'commit', timeout: 60000 });
      clickedAt = await clickDuringLoad(page, opts);
      await page.waitForLoadState('load', { timeout: 60000 });
      await page.waitForTimeout(opts.settle);
    } else {
      await page.goto(url, { waitUntil: 'load', timeout: 60000 });
      await page.waitForTimeout(opts.settle);
    }

    if (opts.interact && opts.interactAt == null) {
      try {
        await page.click(opts.interact, { timeout: 5000 });
        await page.waitForTimeout(500);
      } catch (err) {
        process.stderr.write(
          `measure_vitals: --interact "${opts.interact}" did not match: ` +
          `${err.message.split('\n')[0]}\n`);
      }
    }

    // In the page's own timeline, which starts with the document's request.
    const requests = doc ? [...flights.values()].map(([s, e]) =>
      [(s - doc.start) * 1000, e == null ? null : (e - doc.start) * 1000]) : null;
    const result = await page.evaluate(HARVEST,
      { topN: opts.resources, ttfb: doc && doc.ttfb != null ? doc.ttfb : null, requests });
    result.clickedAt = clickedAt;
    await cdp.detach().catch(() => {});
    return result;
  } finally {
    await context.close().catch(() => {});
  }
}

// ---------------------------------------------------------------------------
// Statistics
// ---------------------------------------------------------------------------

function median(xs) {
  const v = xs.filter((x) => typeof x === 'number' && Number.isFinite(x))
    .slice().sort((a, b) => a - b);
  if (!v.length) return null;
  const mid = v.length >> 1;
  return v.length % 2 ? v[mid] : (v[mid - 1] + v[mid]) / 2;
}

function spread(xs) {
  const v = xs.filter((x) => typeof x === 'number' && Number.isFinite(x));
  if (!v.length) return null;
  const min = Math.min(...v);
  const max = Math.max(...v);
  const med = median(v);
  return { min, max, median: med, range: max - min,
           rangePct: med ? (max - min) / med * 100 : 0, n: v.length };
}

// ---------------------------------------------------------------------------
// Budget
// ---------------------------------------------------------------------------

function globMatch(pattern, value) {
  const rx = new RegExp('^' + pattern.split('*').map((s) =>
    s.replace(/[.+^${}()|[\]\\?]/g, '\\$&')).join('.*') + '$');
  return rx.test(value);
}

function loadLabBudget(file, pageType) {
  if (!file) return null;
  if (!fs.existsSync(file)) die(`no such budget file: ${file}`);
  let data;
  try {
    data = readJsonFile(file);
  } catch (err) {
    die(`cannot parse ${file}: ${err.message}`);
  }
  if (data.$schema && data.$schema !== 'perf-budget-gate/1') {
    die(`${file} declares $schema "${data.$schema}"; ` +
        'this tool understands "perf-budget-gate/1"');
  }
  let lab = Object.assign({}, (data.defaults || {}).lab || {});
  if (pageType && data.pages) {
    for (const [pattern, over] of Object.entries(data.pages)) {
      if (globMatch(pattern, pageType)) Object.assign(lab, (over || {}).lab || {});
    }
  }
  return Object.keys(lab).length ? lab : null;
}

// Thresholds verified against web.dev, September 2026. CLS "good" is <= 0.1,
// LCP <= 2.5s, INP <= 200ms, all AT THE 75TH PERCENTILE OF REAL PAGE LOADS.
// These are shown as orientation for a lab number, not as a pass mark for one.
const CWV = {
  lcp: { good: 2500, poor: 4000, unit: 'ms', label: 'LCP' },
  cls: { good: 0.1, poor: 0.25, unit: '', label: 'CLS' },
  inp: { good: 200, poor: 500, unit: 'ms', label: 'INP' },
  tbt: { good: 200, poor: 600, unit: 'ms', label: 'TBT' },
  ttfb: { good: 800, poor: 1800, unit: 'ms', label: 'TTFB' },
};

function rate(metric, value) {
  const t = CWV[metric];
  if (!t || value == null) return '';
  if (value <= t.good) return 'good';
  if (value <= t.poor) return 'needs-improvement';
  return 'poor';
}

// ---------------------------------------------------------------------------
// Reporting
// ---------------------------------------------------------------------------

const fmt = (n, d = 0) => (n == null ? 'n/a' : Number(n).toFixed(d));
const kb = (n) => (n >= 1e6 ? `${(n / 1e6).toFixed(2)}MB` : `${(n / 1000).toFixed(1)}KB`);

function textReport(o) {
  const L = [];
  L.push(`measure_vitals — ${o.url}`);
  L.push(`  ${o.runs} run(s), throttle ${o.throttle} ` +
         `(${o.throttleDetail}), viewport ${o.viewport}, ` +
         `${o.warm ? 'warm' : 'cold'} cache`);
  L.push('');
  L.push('Metric      median      min       max    spread  rating (CWV lab orientation)');
  for (const key of ['lcp', 'cls', 'tbt', 'ttfb', 'fcp', 'inp']) {
    const s = o.stats[key];
    if (!s) { L.push(`  ${CWV[key]?.label || key.toUpperCase().padEnd(5)}      n/a`); continue; }
    const d = key === 'cls' ? 3 : 0;
    const label = (CWV[key]?.label || key.toUpperCase()).padEnd(6);
    L.push(`  ${label} ${fmt(s.median, d).padStart(9)} ` +
           `${fmt(s.min, d).padStart(9)} ${fmt(s.max, d).padStart(9)} ` +
           `${(fmt(s.rangePct, 0) + '%').padStart(8)}  ${rate(key, s.median)}`);
  }
  if (o.longTasks) {
    L.push(`  long tasks    ${o.longTasks.count} task(s), longest ` +
           `${o.longTasks.longest}ms, ${o.longTasks.blockingTotal}ms blocking ` +
           `in total (TBT counts only what lands after FCP, before TTI, ` +
           'and outside an interaction)');
  }
  L.push('');
  L.push(`  LCP element   ${o.lcpSelector || '(not identified)'}`);
  if (o.lcpUrl) L.push(`  LCP resource  ${o.lcpUrl}`);
  if (o.lcpPhases) {
    const p = o.lcpPhases;
    const tot = p.ttfb + p.loadDelay + p.loadDuration + p.renderDelay || 1;
    const pct = (x) => `${Math.round(x / tot * 100)}%`;
    L.push('');
    L.push('  LCP sub-parts                        target  (references/diagnosis.md §2)');
    L.push(`    TTFB                  ${String(p.ttfb).padStart(6)}ms  ${pct(p.ttfb).padStart(5)}   ~40%`);
    L.push(`    resource load delay   ${String(p.loadDelay).padStart(6)}ms  ${pct(p.loadDelay).padStart(5)}   <10%`);
    L.push(`    resource load duration${String(p.loadDuration).padStart(6)}ms  ${pct(p.loadDuration).padStart(5)}   ~40%`);
    L.push(`    element render delay  ${String(p.renderDelay).padStart(6)}ms  ${pct(p.renderDelay).padStart(5)}   <10%`);
  }
  if (o.clsSources && o.clsSources.length) {
    L.push('');
    L.push('  Largest CLS window (worst run)');
    for (const s of o.clsSources.slice(0, 5)) {
      L.push(`    ${String(s.value).padStart(8)}  at ${String(s.at).padStart(5)}ms  ` +
             `${s.nodes.join(', ') || '(source node not retained)'}`);
    }
  }
  if (o.resources && o.resources.length) {
    L.push('');
    L.push(`  Largest resources (${o.resourceCount} requests, ${kb(o.transferTotal)} transferred)`);
    for (const r of o.resources) {
      L.push(`    ${kb(r.transfer).padStart(9)}  ${String(r.duration).padStart(5)}ms  ` +
             `${r.type.padEnd(10)} ${r.name.replace(/^https?:\/\/[^/]+/, '')}`);
    }
  }
  if (o.breaches.length) {
    L.push('');
    L.push('Budget breaches');
    for (const b of o.breaches) {
      L.push(`  ${b.metric.toUpperCase().padEnd(5)} ${b.actual} > ${b.limit}   ${b.advice}`);
    }
  } else if (o.budgetApplied) {
    L.push('');
    L.push('Budget: every measured metric is inside its limit.');
  }
  if (o.notes.length) {
    L.push('');
    for (const n of o.notes) L.push(`note: ${n}`);
  }
  return L.join('\n') + '\n';
}

const ADVICE = {
  lcp: 'Read the sub-parts above: the biggest one names the fix. ' +
       'references/diagnosis.md §2.',
  cls: 'The CLS window above names the shifting nodes. references/diagnosis.md §5.',
  tbt: 'Long tasks after FCP. Break them up or ship less JS. ' +
       'references/diagnosis.md §8.',
  inp: 'Yield between handler work and the next paint. references/diagnosis.md §8.',
  ttfb: 'Server or CDN, not the front end. references/diagnosis.md §3.',
};

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main() {
  const opts = parseArgs(process.argv.slice(2));
  const { url, isFile } = resolveTarget(opts.target);
  const notes = [];
  if (isFile) {
    notes.push(
      'measuring a file:// URL. There is no network stack, so TTFB is near ' +
      'zero, resource priorities do not apply and throttling barely bites. ' +
      'The numbers are not comparable to a served page — run a local HTTP ' +
      'server (python -m http.server) and point this at that instead.');
  }

  // Read the budget before measuring: a typo found after N runs costs them all.
  const lab = loadLabBudget(opts.budget, opts.pageType);

  const { chromium } = await loadPlaywright(die, 'node measure_vitals.mjs ...');
  const launched = await launchBrowser(chromium, opts.browser, {
    args: ['--force-color-profile=srgb', '--disable-lcd-text',
           '--font-render-hinting=none', '--no-sandbox',
           '--disable-dev-shm-usage'],
  });
  if (!launched.browser) {
    die('no usable chromium. Tried:\n    ' + launched.tried.join('\n    ') + '\n' +
        '  Pass --browser PATH, set PERF_CHROMIUM, or install Chrome or Edge.\n' +
        '  This script never downloads a browser: a gate that pulls 150MB on ' +
        'every CI run is a gate somebody turns off.');
  }
  if (launched.auto && !opts.quiet && !opts.json) {
    process.stderr.write(`browser: ${launched.label}\n`);
  }
  const browser = launched.browser;

  const runs = [];
  try {
    for (let i = 0; i < opts.runs; i++) {
      const r = await runOnce(browser, opts, url);
      runs.push(r);
      if (!opts.quiet && !opts.json) {
        process.stderr.write(
          `  run ${i + 1}/${opts.runs}  LCP ${fmt(r.lcp)}ms  ` +
          `CLS ${fmt(r.cls, 3)}  TBT ${fmt(r.tbt)}ms\n`);
      }
    }
  } finally {
    await browser.close().catch(() => {});
  }

  const stats = {};
  for (const key of ['lcp', 'cls', 'tbt', 'ttfb', 'fcp', 'inp']) {
    stats[key] = spread(runs.map((r) => r[key]));
  }
  stats.tti = spread(runs.map((r) => r.tti));
  if (!stats.inp && opts.interact) {
    notes.push(`--interact "${opts.interact}" produced no interaction entries.`);
  }
  const late = runs.map((r) => r.clickedAt).filter((at) => at != null && at > opts.interactAt + 50);
  if (late.length) {
    notes.push(
      `--interact-at ${opts.interactAt}: the target was ready only at ` +
      `${Math.min(...late)} ms or later in ${late.length} run(s), and was clicked then.`);
  }
  if (!opts.interact) {
    notes.push(
      'INP is n/a because nothing interacted with the page. TBT is the lab ' +
      'proxy; drive a real interaction with --interact SELECTOR, and measure ' +
      'INP properly in the field with a RUM library.');
  }
  for (const key of ['lcp', 'cls', 'tbt']) {
    const s = stats[key];
    if (s && s.n > 2 && s.rangePct > 25) {
      notes.push(
        `${key.toUpperCase()} varied ${Math.round(s.rangePct)}% across runs. ` +
        'That is too noisy to gate on as it stands — raise --runs, pin the ' +
        'CI runner, or widen the threshold with the headroom argument in ' +
        'references/ci-integration.md §4.');
    }
  }

  // The run with the worst CLS is the one whose shift sources are worth
  // printing: the median run may not have shifted at all.
  const worstCls = runs.reduce((a, b) => (b.cls > a.cls ? b : a), runs[0]);
  const medLcp = stats.lcp ? stats.lcp.median : null;
  const lcpRun = runs.reduce(
    (a, b) => (Math.abs((b.lcp ?? 1e9) - medLcp) < Math.abs((a.lcp ?? 1e9) - medLcp) ? b : a),
    runs[0]);

  const breaches = [];
  if (lab) {
    const map = { lcp_ms: 'lcp', cls: 'cls', tbt_ms: 'tbt', inp_ms: 'inp',
                  ttfb_ms: 'ttfb', fcp_ms: 'fcp' };
    for (const [field, metric] of Object.entries(map)) {
      if (lab[field] == null || !stats[metric]) continue;
      const actual = stats[metric].median;
      if (actual > lab[field]) {
        breaches.push({
          metric,
          actual: metric === 'cls' ? actual.toFixed(3) : Math.round(actual),
          limit: lab[field],
          advice: ADVICE[metric] || '',
        });
      }
    }
  }

  const t = THROTTLE[opts.throttle];
  const out = {
    url,
    runs: opts.runs,
    throttle: opts.throttle,
    throttleDetail: t.down < 0
      ? `no network shaping, ${t.cpu}x CPU`
      : `${(t.down * 8 / 1024 / 1024).toFixed(2)}Mbps down, ${t.latency}ms per request, ${t.cpu}x CPU`,
    viewport: `${opts.viewport.width}x${opts.viewport.height}@${opts.dpr}x`,
    warm: opts.warm,
    stats,
    lcpSelector: lcpRun.lcpSelector,
    lcpUrl: lcpRun.lcpUrl,
    lcpPhases: lcpRun.lcpPhases,
    clsSources: worstCls.clsSources,
    longTasks: {
      count: median(runs.map((r) => r.longTaskCount)) ?? 0,
      longest: median(runs.map((r) => r.longestTask)) ?? 0,
      blockingTotal: median(runs.map((r) => r.blockingTotal)) ?? 0,
    },
    resources: lcpRun.resources,
    resourceCount: lcpRun.resourceCount,
    transferTotal: lcpRun.transferTotal,
    budgetApplied: Boolean(lab),
    budget: lab,
    breaches,
    notes,
    perRun: runs.map((r) => ({
      lcp: r.lcp, cls: r.cls, tbt: r.tbt, ttfb: r.ttfb, fcp: r.fcp, tti: r.tti,
      inp: r.inp, longTaskCount: r.longTaskCount, clickedAt: r.clickedAt,
    })),
  };

  if (opts.report) {
    fs.mkdirSync(path.dirname(path.resolve(opts.report)), { recursive: true });
    fs.writeFileSync(opts.report, JSON.stringify(out, null, 2) + '\n');
  }
  process.stdout.write(opts.json
    ? JSON.stringify(out, null, 2) + '\n'
    : textReport(out));

  if (breaches.length) return 1;
  if (stats.lcp == null) {
    process.stderr.write(
      'measure_vitals: no LCP was recorded in any run. The page may have ' +
      'rendered nothing, or failed to load.\n');
    return 1;
  }
  return 0;
}

// 1 means a budget was breached, so a run that failed exits 2 (GT-A5).
main().then((code) => process.exit(code)).catch((err) => {
  process.stderr.write(`measure_vitals: the run failed: ${err && err.stack || err}\n`);
  process.exit(2);
});
