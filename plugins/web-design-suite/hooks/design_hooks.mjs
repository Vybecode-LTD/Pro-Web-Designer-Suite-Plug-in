/**
 * design_hooks.mjs — web-design-suite's Claude Code hooks (P25). hooks.json
 * runs it as `node design_hooks.mjs <mode>`, with the event's JSON on stdin:
 *
 *   guard  PreToolUse on Edit|Write. Refuses an edit to a generated file, one
 *          that says "DO NOT EDIT", "@generated" or "AUTO-GENERATED" in its
 *          first 800 characters, as audit_design.py reads it, so Claude
 *          changes the source and regenerates instead (LC-C8).
 *   gate   PostToolUse on Edit|Write. Runs audit_design.py on the file Claude
 *          just changed and hands Claude what it found (XC-C2, SS-C6).
 *   route  UserPromptSubmit. When a prompt names a task one of the plugin's
 *          skills does, says which: a crowded skill listing drops the
 *          descriptions, and then the names are all Claude sees.
 *
 * guard and gate act only in a project whose .design-suite.json turns them on,
 * "hooks": {"generatedFiles": true, "designGate": true}, read through
 * project_config.mjs beside this file (a copy of the plugin's
 * shared/project_config.mjs). The plugin's `design_hooks` option, false, turns
 * all three off. They run under node because one name runs node on every
 * system; the gate alone needs Python, and looks for it as the pre-commit hook
 * does (WDS_PYTHON, else python3, python and py -3). A hook that cannot act
 * says so to Claude, or stays silent, and never blocks anything because of
 * its own failure.
 */

import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { findConfig, loadConfig } from './project_config.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const AUDIT = path.join(HERE, '..', 'skills', 'web-design-studio', 'scripts', 'audit_design.py');
// The files audit_design.py reads: its CSS_EXT, JS_EXT and TEMPLATE_EXT.
const AUDITED = ['.css', '.scss', '.sass', '.less', '.pcss', '.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs',
                 '.html', '.htm', '.vue', '.svelte', '.astro'];
// audit_design.py's GENERATED_MARKERS, looked for in a file's first 800 characters.
const GENERATED = ['@generated', 'DO NOT EDIT', 'AUTO-GENERATED', 'Auto-generated'];
const LIMIT = 9000;           // Claude Code caps additionalContext at 10,000 characters
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

// The config that governs `file`: { config }, { error }, or null without one.
function governing(file) {
  try {
    const found = findConfig(path.dirname(file));
    return found ? { config: loadConfig(found) } : null;
  } catch (err) {
    return { error: err.message };
  }
}

function guard(input) {
  const file = target(input);
  if (!file || !fs.existsSync(file) || !fs.statSync(file).isFile()) return;
  const project = governing(file);
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

function gate(input) {
  const file = target(input);
  if (!file || !AUDITED.includes(path.extname(file).toLowerCase()) || !fs.existsSync(file)) return;
  const project = governing(file);
  if (!project) return;
  const tell = (text) => say('PostToolUse', { additionalContext: `web-design-suite design gate: ${text}` });
  if (project.error) return tell(`.design-suite.json could not be read, so the gate did not run: ${project.error}`);
  if (!project.config.hooks.designGate) return;
  const python = findPython();
  if (!python) return tell('it needs Python 3 (WDS_PYTHON, python3, python or py -3), and found none.');
  const [exe, ...args] = python;
  // resolved, as the config's root is: a link, /var on macOS or a short 8.3 name would
  // otherwise name the file from outside its project
  const real = fs.realpathSync.native(file);
  const proc = spawnSync(exe, [...args, '-B', AUDIT, real, '--json'],
                         { cwd: project.config.root, encoding: 'utf8', timeout: 100000, windowsHide: true });
  let findings;
  try {
    findings = JSON.parse(proc.stdout);
  } catch {
    return tell(`audit_design.py stopped (exit ${proc.status}): ${(proc.stderr || '').trim().slice(0, 600)}`);
  }
  if (!Array.isArray(findings) || !findings.length) return;
  const rel = path.relative(project.config.root, real).split(path.sep).join('/');
  let text = `audit_design.py found ${findings.length} problem${findings.length === 1 ? '' : 's'} in ${rel}. ` +
    'Fix each before going on, or tell the user why it should stay:';
  let shown = 0;
  for (const f of findings) {
    const line = `\n- line ${f.line}, ${f.law} ${f.rule} (${f.severity}): ${f.message} Fix: ${f.fix}`;
    if (text.length + line.length > LIMIT) break;
    text += line;
    shown += 1;
  }
  if (shown < findings.length) text += `\n- and ${findings.length - shown} more: run audit_design.py on the file.`;
  tell(text);
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
