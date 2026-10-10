/**
 * design_hooks.mjs — web-design-suite's Claude Code hooks (P25). hooks.json
 * runs it as `node design_hooks.mjs <mode>`, with the event's JSON on stdin:
 *
 *   guard  PreToolUse on Edit|Write. Refuses an edit to a generated file, one
 *          that says "DO NOT EDIT", "@generated" or "AUTO-GENERATED" in its
 *          first 800 characters, as audit_design.py reads it, so Claude
 *          changes the source and regenerates instead (LC-C8).
 *   gate   PostToolUse on Edit|Write. Runs audit_design.py on the file Claude
 *          just changed and hands Claude what it found (XC-C2, SS-C6), and
 *          a11y_static.py too (GT-C9). After an edit to one of the project's
 *          token files, it also runs diff_system.py against the published
 *          snapshot and hands Claude the breaking changes and the contrast
 *          pairs that crossed a WCAG floor (LC-C8). After an edit to an email
 *          template, it lints the source, builds it into a temporary folder
 *          and lints the build, and hands Claude the errors (DL-C7).
 *   route  UserPromptSubmit. When a prompt names a task one of the plugin's
 *          skills does, says which: a crowded skill listing drops the
 *          descriptions, and then the names are all Claude sees.
 *
 * guard and gate act only in a project whose .design-suite.json turns them on,
 * "hooks": {"generatedFiles": true, "designGate": true, "tokenDiff": true,
 * "a11yGate": true, "emailBuild": true}, read through project_config.mjs beside
 * this file (a copy of the plugin's shared/project_config.mjs). The token diff
 * also needs the config's `tokens` and `baselines.system`, and stays silent
 * until that snapshot exists. An email template is a file the config's
 * `emails` globs match: by default, an .html file anywhere under emails/. The
 * plugin's `design_hooks` option, false, turns all of them off. They run under
 * node because one name runs node on every system; the gate alone needs
 * Python, and looks for it as the pre-commit hook does (WDS_PYTHON, else
 * python3, python and py -3). A hook that cannot act says so to Claude, or
 * stays silent, and never blocks anything because of its own failure.
 */

import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { findConfig, isEmail, loadConfig, readJson } from './project_config.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const AUDIT = path.join(HERE, '..', 'skills', 'web-design-studio', 'scripts', 'audit_design.py');
const DIFF = path.join(HERE, '..', 'skills', 'design-system-versioning', 'scripts', 'diff_system.py');
const A11Y = path.join(HERE, '..', 'skills', 'a11y-audit-runner', 'scripts', 'a11y_static.py');
const EMAIL = path.join(HERE, '..', 'skills', 'email-template-system', 'scripts');
// The files audit_design.py reads: its CSS_EXT, JS_EXT and TEMPLATE_EXT.
const AUDITED = ['.css', '.scss', '.sass', '.less', '.pcss', '.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs',
                 '.html', '.htm', '.vue', '.svelte', '.astro'];
// The files a11y_static.py reads: its AUDITABLE_EXT.
const A11Y_READ = ['.html', '.htm', '.xhtml', '.vue', '.svelte', '.astro', '.php', '.erb', '.hbs', '.handlebars',
                   '.twig', '.liquid', '.jinja', '.j2', '.ejs', '.jsx', '.tsx', '.js', '.ts', '.mjs', '.cjs',
                   '.css', '.scss', '.less', '.pcss'];
// audit_design.py's GENERATED_MARKERS, looked for in a file's first 800 characters.
const GENERATED = ['@generated', 'DO NOT EDIT', 'AUTO-GENERATED', 'Auto-generated'];
const LIMIT = 9000;           // Claude Code caps additionalContext at 10,000 characters
const BUDGET = 160000;        // the scripts' time together, inside hooks.json's 180 seconds
const OFF = /^(?:false|0|no|off)$/i;

// A skill, what it covers, and the words that name its work. Up to two are
// named, in this order, so the specific ones come before the studio.
const ROUTES = [
  ['a11y-audit-runner', 'accessibility audits',
   [/\b(?:WCAG|axe-core|a11y|screen ?readers?)\b/i, /\baccessib\w* (?:audit|check|test|review)/i]],
  ['figma-variables-sync', 'Figma variables and tokens', [/\bfigma\b[^.?!]*\b(?:variables?|tokens?|styles?)\b/i]],
  ['email-template-system', 'HTML email', [/\b(?:html e-?mails?|e-?mail templates?|newsletters?|MJML)\b/i]],
  ['perf-budget-gate', 'performance budgets', [/\b(?:core web vitals|lighthouse|performance budgets?|page ?speed)\b/i,
                                                /\b(?:LCP|INP|CLS|TTFB)\b/]],
  ['design-token-migration', 'migrating a codebase onto tokens',
   [/\b(?:hard-?coded|magic) (?:values?|colou?rs?|numbers?|pixels?)\b/i, /\bmigrat\w*\b[^.?!]*\btokens?\b/i,
    /\bcodemods?\b/i]],
  ['design-system-versioning', 'versioning a design system',
   [/\b(?:semver|breaking changes?|deprecat\w*)\b[^.?!]*\b(?:tokens?|design system)\b/i]],
  ['design-system-docs', 'design-system documentation',
   [/\b(?:style ?guides?|storybook|design[- ]system(?:'s)? (?:docs|documentation|site))\b/i]],
  ['component-state-matrix', 'every state of a component', [/\b(?:state matrix|every state|visual regression)\b/i]],
  ['content-model-to-ui', 'screens from a data model',
   [/\b(?:CRUD|admin (?:screens?|panel|ui))\b/i, /\b(?:schema|supabase|prisma)\b[^.?!]*\b(?:forms?|screens?)\b/i]],
  ['landing-page-conversion', 'pages that convert', [/\b(?:landing pages?|conversion rates?|hero sections?|pricing pages?)\b/i,
                                                     /\bCTAs?\b/]],
  ['design-critique-gate', 'design critique', [/\b(?:critique|design review)\b/i]],
  ['client-presentation-builder', 'client presentations', [/\b(?:client presentations?|pitch decks?)\b/i]],
  ['web-design-studio', 'design systems and building them',
   [/\b(?:design tokens?|spacing scale|type scale|colou?r ramps?|cascade layers|tailwind theme|design system)\b/i]],
];

function readInput() {
  try {
    return JSON.parse(fs.readFileSync(0, 'utf8'));
  } catch {
    return null;
  }
}

function say(event, fields) {
  process.stdout.write(`${JSON.stringify({ hookSpecificOutput: { hookEventName: event, ...fields } })}\n`);
}

// The file an Edit or Write names, absolute.
function target(input) {
  const file = input?.tool_input?.file_path;
  return typeof file === 'string' && file ? path.resolve(input.cwd || process.cwd(), file) : null;
}

// The config that governs the folder `dir`: { config }, { error, found }, or
// null without one.
function governing(dir) {
  let found = null;
  try {
    found = findConfig(dir);
    return found ? { config: loadConfig(found) } : null;
  } catch (err) {
    return { error: err.message, found };
  }
}

// Does the config at `found`, which does not pass its checks, still name `real`
// among its `tokens`? Read as JSON in any encoding the reader takes, UTF-16 and
// UTF-32 too (CodeRabbit on #84), for the one message that says so.
function namesToken(found, real) {
  try {
    const data = readJson(found);
    const base = path.dirname(fs.realpathSync.native(found));
    return [data.tokens].flat().some((t) => typeof t === 'string' && t.trim() &&
      fs.existsSync(path.resolve(base, t)) && fs.realpathSync.native(path.resolve(base, t)) === real);
  } catch {
    return false;
  }
}

function guard(input) {
  const file = target(input);
  if (!file || !fs.existsSync(file) || !fs.statSync(file).isFile()) return;
  const project = governing(path.dirname(file));
  if (!project?.config?.hooks.generatedFiles) return;
  const fd = fs.openSync(file, 'r');
  const buf = Buffer.alloc(3203);                 // 800 characters of up to 4 bytes, and a BOM
  const read = fs.readSync(fd, buf, 0, buf.length, 0);
  fs.closeSync(fd);
  // 800 characters as Python counts them, code points, not UTF-16 units (Codex on #82)
  const head = Array.from(buf.subarray(0, read).toString('utf8').replace(/^﻿/, '')).slice(0, 800).join('');
  const marker = GENERATED.find((m) => head.includes(m));
  if (!marker) return;
  const rel = path.relative(project.config.root, fs.realpathSync.native(file)) || file;
  say('PreToolUse', {
    permissionDecision: 'deny',
    permissionDecisionReason:
      `${rel} is a generated file: it says "${marker}" in its first lines, so the next build overwrites ` +
      'an edit here. Change its source or its generator, and regenerate it. (web-design-suite: ' +
      '"hooks": {"generatedFiles": true} in .design-suite.json)',
  });
}

// The first Python 3 found: WDS_PYTHON, else the names the platform uses. On
// Windows `python3` is often the Store's placeholder, which runs nothing, so
// each is asked for its major version.
function findPython() {
  const named = process.env.WDS_PYTHON;
  const candidates = named ? [[named]]
    : process.platform === 'win32' ? [['python'], ['py', '-3'], ['python3']] : [['python3'], ['python']];
  return candidates.find(([exe, ...args]) => {
    const probe = spawnSync(exe, [...args, '-c', 'import sys; print(sys.version_info[0])'],
                            { encoding: 'utf8', timeout: 15000, windowsHide: true });
    return probe.status === 0 && probe.stdout.trim() === '3';
  }) ?? null;
}

// Every script one gate run starts shares BUDGET, so together they end
// before hooks.json's timeout stops the hook and drops what they found.
const deadline = Date.now() + BUDGET;

// Runs a plugin script under `python` in the config's folder: the finished
// process, or { failed } with what Claude should hear.
function spawnScript(python, script, args, root, timeout) {
  const [exe, ...pre] = python;
  // a report past spawnSync's 1 MiB default was cut short (CodeRabbit on #82)
  const proc = spawnSync(exe, [...pre, '-B', script, ...args],
                         { cwd: root, encoding: 'utf8', timeout: Math.max(1000, Math.min(timeout, deadline - Date.now())),
                           windowsHide: true, maxBuffer: 256 * 1024 * 1024 });
  return proc.error ? { failed: `${path.basename(script)} could not run: ${proc.error.message}` } : proc;
}

// The same, and the script's JSON, or { failed }.
function runScript(python, script, args, root, timeout) {
  const proc = spawnScript(python, script, args, root, timeout);
  if (proc.failed) return proc;
  try {
    return { json: JSON.parse(proc.stdout) };
  } catch {
    return { failed: `${path.basename(script)} stopped (exit ${proc.status}): ${(proc.stderr || '').trim().slice(0, 600)}` };
  }
}

// `lines` added to `text` while the whole stays within `limit`, and a last line
// that counts what did not fit.
function capped(text, lines, limit, rest) {
  let shown = 0;
  for (const line of lines) {
    if (text.length + line.length > limit) break;
    text += line;
    shown += 1;
  }
  return shown < lines.length ? `${text}\n- and ${lines.length - shown} more: ${rest}` : text;
}

const posix = (root, file) => path.relative(root, file).split(path.sep).join('/') || file;

function audit(python, config, real, limit) {
  const head = 'web-design-suite design gate: ';
  const run = runScript(python, AUDIT, [real, '--json'], config.root, 100000);
  if (run.failed) return head + run.failed;
  const findings = run.json;
  if (!Array.isArray(findings) || !findings.length) return null;
  const text = `${head}audit_design.py found ${findings.length} problem${findings.length === 1 ? '' : 's'} in ` +
    `${posix(config.root, real)}. Fix each before going on, or tell the user why it should stay:`;
  return capped(text, findings.map((f) => `\n- line ${f.line}, ${f.law} ${f.rule} (${f.severity}): ${f.message} Fix: ${f.fix}`),
                limit, 'run audit_design.py on the file.');
}

// GT-C9: the static accessibility checks on the edited file. The config's
// a11y baseline applies, as it does to a whole run: its keys hold the path as
// a run from the project's folder names the file, so the file is named so.
function a11y(python, config, real, limit) {
  const head = 'web-design-suite a11y gate: ';
  const run = runScript(python, A11Y, [path.relative(config.root, real), '--json'], config.root, 60000);
  if (run.failed) return head + run.failed;
  const findings = run.json?.findings;
  if (!Array.isArray(findings) || !findings.length) return null;
  const text = `${head}a11y_static.py found ${findings.length} problem${findings.length === 1 ? '' : 's'} in ` +
    `${posix(config.root, real)}. Fix each before going on, or tell the user why it should stay:`;
  return capped(text, findings.map((f) => `\n- line ${f.line}, ${f.rule}, WCAG ${f.sc} (${f.severity}): ${f.message} ` +
                                          `Fix: ${f.fix}`),
                limit, 'run a11y_static.py on the file.');
}

// DL-C7: an email template, linted as written (Law 1), built into a temporary
// folder, and the build linted as the inboxes will read it. Only the errors
// are listed; the warnings are counted, for /email-build to show.
function emailBuild(python, config, real, limit) {
  const head = 'web-design-suite email build: ';
  const lint = (file, more) => {
    const run = runScript(python, path.join(EMAIL, 'lint_email.py'), [file, ...more, '--format', 'json'],
                          config.root, 40000);
    if (run.failed) return run;
    const [report] = Object.values(run.json?.files ?? {});
    return report ?? { failed: 'lint_email.py returned no report' };
  };
  const errors = [];
  let warnings = 0;
  const take = (where, report) => {
    warnings += report.warnings ?? 0;
    for (const f of report.findings ?? []) {
      if (f.severity === 'error') {
        errors.push(`\n- ${where}${f.line ? `, line ${f.line}` : ''}, ${f.check}: ${f.message}` +
                    `${f.detail ? ` (${f.detail})` : ''}${f.fix ? ` Fix: ${f.fix}` : ''}`);
      }
    }
  };
  const source = lint(real, ['--source']);
  if (source.failed) return head + source.failed;
  take('the source', source);
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'wds-email-'));
  try {
    const out = path.join(dir, path.basename(real));
    const build = spawnScript(python, path.join(EMAIL, 'build_email.py'), [real, '--out', out], config.root, 40000);
    if (build.failed) return head + build.failed;
    // exit 1 is a build past Gmail's clipping threshold, which the lint of the
    // build reports as its `size` error
    if ((build.status !== 0 && build.status !== 1) || !fs.existsSync(out)) {
      errors.push(`\n- the build stopped (exit ${build.status}): ${(build.stderr || '').trim().slice(0, 600)}`);
    } else {
      const built = lint(out, []);
      if (built.failed) return head + built.failed;
      take('the build', built);
    }
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
  if (!errors.length) return null;
  const text = `${head}${posix(config.root, real)} has ${errors.length} error${errors.length === 1 ? '' : 's'}` +
    `${warnings ? ` and ${warnings} warning${warnings === 1 ? '' : 's'}` : ''} (lint_email.py on the source and ` +
    'on the build). Fix each before going on, or tell the user why it should stay:';
  return capped(text, errors, limit, 'run /email-build on the template.');
}

// LC-C8: the project's token files against the published snapshot. A change
// that is only minor or a patch, with no pair crossing a floor, is silent.
function tokenDiff(python, config, real, limit) {
  const head = 'web-design-suite token diff: ';
  const snapshot = config.baselines.system;
  const run = runScript(python, DIFF, [snapshot, '--format', 'json', '--gate', 'none'], config.root, 60000);
  if (run.failed) return head + run.failed;
  const { bump, counts, changes = [], contrast = [] } = run.json ?? {};
  const breaking = changes.filter((c) => c.severity === 'major');
  const crossed = contrast.filter((r) => r.crossings?.length);
  if (!breaking.length && !crossed.length) return null;
  const text = `${head}after this edit to ${posix(config.root, real)}, the token files against the published ` +
    `snapshot (${posix(config.root, snapshot)}) make a ${bump.level} release, ${bump.reason}: ` +
    `${counts.major} major, ${counts.minor} minor and ${counts.patch} patch changes. A breaking change needs a major ` +
    'release and a deprecation first (design-system-versioning), and a pair below its floor fails WCAG: undo what ' +
    'was not meant, or tell the user.';
  const lines = [
    ...breaking.map((c) => `\n- ${c.kind}: ${c.subject}${c.component ? ` (${c.component})` : ''}` +
      `${c.theme ? `, ${c.theme} theme` : ''}${c.replacement ? `, now ${c.replacement}` : ''}` +
      `${c.before || c.after ? `, ${c.before || 'none'} → ${c.after || 'none'}` : ''}`),
    ...crossed.map((r) => `\n- contrast, ${r.theme} theme: ${r.fg} on ${r.bg}, ${r.before}:1 → ${r.after}:1, ` +
      r.crossings.map((x) => `${x.direction} ${x.threshold}:1 (${x.label})`).join(' and ') +
      (r.caused_by?.length ? `, through ${r.caused_by.join(', ')}` : '')),
  ];
  return capped(text, lines, limit, 'run diff_system.py for the whole report.');
}

// Is `real` one of the config's token files? Both resolved, as the config's are.
function isTokenFile(config, real) {
  return config.tokens.some((t) => {
    try {
      return fs.realpathSync.native(t) === real;
    } catch {
      return false;
    }
  });
}

function gate(input) {
  const file = target(input);
  if (!file || !fs.existsSync(file) || !fs.statSync(file).isFile()) return;
  const ext = path.extname(file).toLowerCase();
  const audited = AUDITED.includes(ext) || A11Y_READ.includes(ext);
  // resolved, as the config's root is: a link, /var on macOS or a short 8.3 name would
  // otherwise name the file from outside its project
  const real = fs.realpathSync.native(file);
  const tell = (text) => say('PostToolUse', { additionalContext: text });
  const own = governing(path.dirname(file));
  // A token file may sit outside its project (`../shared/tokens.css`). Then the
  // project the session runs in is the one that names it (Codex on #84).
  const session = input.cwd ? governing(path.resolve(input.cwd)) : null;
  for (const project of [own, session]) {
    // said for a file that config would have read: one the audit reads, or a
    // token file it names, a contract.json too (Codex on #84)
    const gating = audited && project === own;
    if (project?.error && (gating || namesToken(project.found, real))) {
      return tell(`web-design-suite ${gating ? 'design gate' : 'token diff'}: .design-suite.json could not be ` +
                  `read, so ${gating ? 'the gate' : 'the token diff'} did not run: ${project.error}`);
    }
  }
  const config = own?.config;
  const auditing = AUDITED.includes(ext) && config?.hooks.designGate;
  const checking = A11Y_READ.includes(ext) && config?.hooks.a11yGate;
  const emailing = config?.hooks.emailBuild && isEmail(config, real);
  const diffConfig = [own?.config, session?.config].find((c) => c?.hooks.tokenDiff && c.baselines.system &&
    fs.existsSync(c.baselines.system) && isTokenFile(c, real));
  const diffing = Boolean(diffConfig);
  const running = [auditing && 'design gate', checking && 'a11y gate', emailing && 'email build',
                   diffing && 'token diff'].filter(Boolean);
  if (!running.length) return;
  const python = findPython();
  if (!python) {
    return tell(`web-design-suite ${running.join(', ')}: it needs Python 3 (WDS_PYTHON, python3, python or ` +
                'py -3), and found none.');
  }
  // The token diff and the email build are short and have a third of the cap
  // each; the audit and the a11y checks share what is left.
  const diffText = diffing ? tokenDiff(python, diffConfig, real, LIMIT / 3) : null;
  const emailText = emailing ? emailBuild(python, config, real, LIMIT / 3) : null;
  const used = (...texts) => texts.reduce((n, t) => n + (t ? t.length + 2 : 0), 0);
  const auditText = auditing ? audit(python, config, real, (LIMIT - used(diffText, emailText)) / (checking ? 2 : 1))
    : null;
  const a11yText = checking ? a11y(python, config, real, LIMIT - used(diffText, emailText, auditText)) : null;
  const parts = [auditText, a11yText, emailText, diffText].filter(Boolean);
  if (parts.length) tell(parts.join('\n\n'));
}

function route(input) {
  const prompt = typeof input?.prompt === 'string' ? input.prompt : '';
  if (!prompt || prompt.includes('web-design-suite:')) return;
  const hits = ROUTES.filter(([, , words]) => words.some((rx) => rx.test(prompt))).slice(0, 2);
  if (!hits.length) return;
  const named = hits.map(([skill, what]) => `/web-design-suite:${skill} (${what})`).join(' and ');
  say('UserPromptSubmit', {
    additionalContext: `web-design-suite: this looks like work for ${named}. If it fits, load the skill before you start.`,
  });
}

const MODES = { guard, gate, route };
const mode = MODES[process.argv[2]];
if (mode && !OFF.test(process.env.CLAUDE_PLUGIN_OPTION_DESIGN_HOOKS ?? '')) {
  const input = readInput();
  if (input) {
    try {
      mode(input);
    } catch {
      // a hook's own failure never blocks Claude
    }
  }
}
