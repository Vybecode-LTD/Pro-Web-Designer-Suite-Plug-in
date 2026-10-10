/**
 * project_config.mjs — the project contract for Node (P24): a project's
 * .design-suite.json, found and checked by the rules shared/project_config.py
 * applies for the Python scripts, with the same messages; its token files,
 * read into the contract's sections as read_tokens() reads them; and what the
 * stylelint and ESLint configs take from both (N37). tests/test_project_config.py
 * runs both readers on the same files. The JSON is strict, as Python's is: no
 * comments.
 *
 * The master copy is shared/project_config.mjs, at the plugin's root. A
 * byte-identical copy sits beside each file that imports it: browser_common.mjs
 * in the scripts/ of a11y-audit-runner, component-state-matrix,
 * design-critique-gate, email-template-system and perf-budget-gate, which
 * re-exports the config reader; the two lint configs in web-design-studio's
 * assets/configs/; and the plugin's hooks, hooks/design_hooks.mjs. Change the
 * master, copy it over all seven, and tests/test_project_config.py fails until
 * they match.
 */

import fs from 'node:fs';
import path from 'node:path';

export const CONFIG_NAME = '.design-suite.json';
const CONFIG_KEYS = ['schema', 'tokens', 'emailTokens', 'components', 'emails', 'stack', 'budgets', 'baselines',
                     'hooks'];
const STACKS = ['vanilla-css', 'css-modules', 'tailwind-v3', 'tailwind-v4'];
const BUDGETS = ['perf', 'a11y'];
const BASELINES = ['audit', 'a11y', 'perf', 'docs', 'snapshots', 'system'];
const HOOKS = ['designGate', 'generatedFiles', 'tokenDiff',       // the plugin's hooks a project turns on (P25,
               'a11yGate', 'emailBuild'];                        // P27)
const EMAILS = ['emails/**/*.html'];                             // the email templates, unless `emails` names them

export class ConfigError extends Error {}

// As Python's Path.resolve(): links resolved as far as the path exists.
function realPath(p) {
  const abs = path.resolve(p);
  try { return fs.realpathSync.native(abs); } catch { /* not there: resolve its folder */ }
  const parent = path.dirname(abs);
  return parent === abs ? abs : path.join(realPath(parent), path.basename(abs));
}

// The first .design-suite.json walking up from `start`, never past the
// folder that holds .git, or null.
export function findConfig(start = process.cwd()) {
  let here = realPath(start);
  if (fs.existsSync(here) && fs.statSync(here).isFile()) here = path.dirname(here);
  for (;;) {
    const candidate = path.join(here, CONFIG_NAME);
    if (fs.existsSync(candidate) && fs.statSync(candidate).isFile()) return candidate;
    if (fs.existsSync(path.join(here, '.git'))) return null;
    const up = path.dirname(here);
    if (up === here) return null;
    here = up;
  }
}

// A JSON file's text in the encoding Python's json.detect_encoding() finds
// in bytes: UTF-32 or UTF-16 by their byte-order marks, UTF-8 with or without
// one, and UTF-16 or UTF-32 of either order without one, by where the zero
// bytes fall (Codex on #81: a UTF-16BE file was refused here and read there).
function jsonText(buf) {
  const starts = (...bytes) => buf.length >= bytes.length && bytes.every((b, i) => buf[i] === b);
  let enc = 'utf-8';
  let skip = 0;
  if (starts(0, 0, 0xFE, 0xFF) || starts(0xFF, 0xFE, 0, 0)) [enc, skip] = [buf[0] ? 'utf-32le' : 'utf-32be', 4];
  else if (starts(0xFE, 0xFF) || starts(0xFF, 0xFE)) [enc, skip] = [buf[0] === 0xFF ? 'utf-16le' : 'utf-16be', 2];
  else if (starts(0xEF, 0xBB, 0xBF)) skip = 3;
  else if (buf.length >= 4 && !buf[0]) enc = buf[1] ? 'utf-16be' : 'utf-32be';
  else if (buf.length >= 4 && !buf[1]) enc = buf[2] || buf[3] ? 'utf-16le' : 'utf-32le';
  else if (buf.length === 2 && !buf[0]) enc = 'utf-16be';
  else if (buf.length === 2 && !buf[1]) enc = 'utf-16le';
  const body = buf.subarray(skip);
  if (enc.startsWith('utf-32')) {
    if (body.length % 4) throw new Error('truncated UTF-32');
    let text = '';
    for (let i = 0; i < body.length; i += 4) {
      const code = enc === 'utf-32le' ? body.readUInt32LE(i) : body.readUInt32BE(i);
      if (code > 0x10FFFF) throw new Error(`no character ${code} in UTF-32`);
      text += String.fromCodePoint(code);
    }
    return text;
  }
  if (enc === 'utf-16be') return new TextDecoder('utf-16le', { fatal: true }).decode(Buffer.from(body).swap16());
  return new TextDecoder(enc, { fatal: true, ignoreBOM: true }).decode(body);
}

// A JSON file as Python's json reads bytes (jsonText). The hooks read a config
// that fails its checks through it too.
export function readJson(file, shown = file) {
  let buf;
  try {
    buf = fs.readFileSync(file);
  } catch (err) {
    throw new ConfigError(`${shown}: ${err.code === 'ENOENT' ? 'No such file or directory' : err.message}`);
  }
  try {
    return JSON.parse(jsonText(buf));
  } catch (err) {
    throw new ConfigError(`${shown}: not JSON (${err.message})`);
  }
}

const has = (obj, key) => Object.prototype.hasOwnProperty.call(obj, key);
const isObject = (v) => typeof v === 'object' && v !== null && !Array.isArray(v);

export function loadConfig(file) {
  const where = realPath(file);
  const data = readJson(where, where);
  const fail = (msg) => { throw new ConfigError(`${where}: ${msg}`); };
  if (!isObject(data)) fail('the top level must be an object');
  const unknown = Object.keys(data).filter((k) => !CONFIG_KEYS.includes(k)).sort();
  if (unknown.length) fail(`unknown key '${unknown[0]}'; the keys are ${CONFIG_KEYS.join(', ')}`);
  if (data.schema !== 1) fail('"schema" must be 1');
  const base = path.dirname(where);
  const onePath = (key, value) => {
    if (typeof value !== 'string' || !value.trim()) fail(`"${key}" must be a path, as a string`);
    return path.resolve(base, value);
  };
  const globList = (key, fallback) => {
    let value = has(data, key) ? data[key] : [...fallback];
    if (typeof value === 'string') value = [value];
    if (!Array.isArray(value) || !value.every((g) => typeof g === 'string' && g))
      fail(`"${key}" must be a glob or a list of globs`);
    return value;
  };
  const components = globList('components', []);
  const emails = globList('emails', EMAILS);
  const stack = has(data, 'stack') ? data.stack : null;
  if (stack !== null && !STACKS.includes(stack)) fail(`"stack" must be one of ${STACKS.join(', ')}`);
  let tokens = has(data, 'tokens') ? data.tokens : [];
  if (typeof tokens === 'string') tokens = [tokens];
  if (!Array.isArray(tokens)) fail('"tokens" must be a path or a list of paths');
  tokens = tokens.map((v) => onePath('tokens', v));
  const email = has(data, 'emailTokens') ? data.emailTokens : null;
  const emailTokens = email === null ? null : onePath('emailTokens', email);
  const pathMap = (key, names) => {
    const value = has(data, key) ? data[key] : {};
    if (!isObject(value)) fail(`"${key}" must be an object`);
    const extra = Object.keys(value).filter((k) => !names.includes(k)).sort();
    if (extra.length) fail(`unknown key '${extra[0]}' in "${key}"; the keys are ${names.join(', ')}`);
    return Object.fromEntries(Object.entries(value).map(([name, v]) => [name, onePath(`${key}.${name}`, v)]));
  };
  const hookFlags = () => {
    const value = has(data, 'hooks') ? data.hooks : {};
    if (!isObject(value)) fail('"hooks" must be an object');
    const extra = Object.keys(value).filter((k) => !HOOKS.includes(k)).sort();
    if (extra.length) fail(`unknown key '${extra[0]}' in "hooks"; the keys are ${HOOKS.join(', ')}`);
    const bad = Object.keys(value).find((k) => typeof value[k] !== 'boolean');
    if (bad !== undefined) fail(`"hooks.${bad}" must be true or false`);
    return { ...value };
  };
  return { path: where, root: base, tokens, emailTokens, components, emails, stack,
           budgets: pathMap('budgets', BUDGETS), baselines: pathMap('baselines', BASELINES), hooks: hookFlags() };
}

// The config that governs `start`, read and checked, or null.
export function projectConfig(start = process.cwd()) {
  const found = findConfig(start);
  return found ? loadConfig(found) : null;
}

// --- The `components` globs ---------------------------------------------
// glob_regex's tokens: `**/` any number of folders, none included; `**` any
// text; `*` and `?` within a folder; anything else itself.
function globTokens(pattern) {
  const p = pattern.replace(/\\/g, '/').replace(/^\/+/, '');
  const out = [];
  for (let i = 0; i < p.length;) {
    const token = ['**/', '**', '*', '?'].find((t) => p.startsWith(t, i)) ?? p[i];
    out.push(token);                  // a literal is one character, so never a token
    i += token.length;
  }
  return out;
}

const escapeRegex = (s) => s.replace(/[.*+?^${}()|[\]\\/]/g, '\\$&');

// A `components` glob as a regex over a path with forward slashes, as
// project_config.py's glob_regex() builds it.
export function globRegex(pattern) {
  const parts = { '**/': '(?:.*/)?', '**': '.*', '*': '[^/]*', '?': '[^/]' };
  return new RegExp(`^${globTokens(pattern).map((t) => parts[t] ?? escapeRegex(t)).join('')}$`);
}

// True when `file` matches one of `globs`, read relative to the config's folder.
function matches(config, globs, file) {
  if (!config || !globs.length) return false;
  const rel = path.relative(config.root, realPath(file));
  if (!rel || rel === '..' || rel.startsWith(`..${path.sep}`) || path.isAbsolute(rel)) return false;  // outside
  const posix = rel.split(path.sep).join('/');
  return globs.some((g) => globRegex(g).test(posix));
}

// True when `file` matches one of the config's `components`, read relative to
// its folder, as ProjectConfig.is_component() decides.
export function isComponent(config, file) {
  return matches(config, config?.components ?? [], file);
}

// True when `file` is one of the config's email templates, by `emails`, as
// ProjectConfig.is_email() decides.
export function isEmail(config, file) {
  return matches(config, config?.emails ?? [], file);
}

// stylelint matches an override's `files` with micromatch (dot: true), whose
// `**` is special only as a whole folder name, so each glob becomes the
// micromatch globs that match exactly what globRegex() does, under the
// config's folder. Runs of stars are merged as the regex reads them; a `**`
// inside a name is `*` or `*/**/*`, and a `**/` inside one is nothing or
// `*/**/`. A character micromatch reads is escaped in brackets, since
// stylelint turns every backslash into a slash.
const literalGlob = (s) => s.replace(/[[\]{}()*?]/g, (c) => `[${c}]`);

// micromatch compares a path as the tool spelt it, so a glob is written for
// each spelling of the project's folder (CodeRabbit on #81): as resolved; as
// reached through a link, a junction or a subst drive, by the working
// directory or the shell's PWD; and on Windows with either case of drive
// letter, since an editor sends `c:\`.
function rootSpellings(root, start) {
  const out = new Set([root]);
  for (const logical of [start, process.env.PWD]) {
    if (!logical) continue;
    for (let a = path.resolve(logical); ; a = path.dirname(a)) {
      if (realPath(a) === root) { out.add(a); break; }
      if (path.dirname(a) === a) break;
    }
  }
  return [...out];
}

const driveCases = (p) => (/^[A-Za-z]:/.test(p) ? [p[0].toUpperCase() + p.slice(1), p[0].toLowerCase() + p.slice(1)] : [p]);
const asGlob = (p) => literalGlob(p.split(path.sep).join('/'));

// A file's spellings: as the config names it and as resolved, a link inside
// the project being one of each (CodeRabbit on #81), each under every
// spelling of the project's folder.
function fileSpellings(file, roots) {
  const out = new Set();
  for (const spelling of new Set([path.resolve(file), realPath(file)])) {
    const rel = path.relative(roots[0], spelling);
    const under = rel && rel !== '..' && !rel.startsWith(`..${path.sep}`) && !path.isAbsolute(rel);
    for (const p of under ? roots.map((r) => path.join(r, rel)) : [spelling]) driveCases(p).forEach((c) => out.add(c));
  }
  return [...out];
}

// `root` is the config's folder, resolved, or the list rootSpellings() gives.
export function overrideGlobs(root, pattern) {
  const merged = [];
  for (const t of globTokens(pattern)) {
    const last = merged[merged.length - 1];
    if (t === '**' && (last === '**/' || last === '**')) merged[merged.length - 1] = '**';
    else if ((t === '**/' || t === '*') && last === '**') continue;
    else if (t === '**/' && last === '**/') continue;
    else merged.push(t);
  }
  const roots = Array.isArray(root) ? root : [realPath(root)];
  let globs = [...new Set(roots.flatMap(driveCases))].map((r) => `${asGlob(r)}/`);
  merged.forEach((t, n) => {
    const atFolder = n === 0 || merged[n - 1] === '/';
    const alternatives = { '**/': atFolder ? ['**/'] : ['', '*/**/'], '**': ['*', '*/**/*'], '*': ['*'],
                           '?': ['?'] }[t] ?? [literalGlob(t)];
    globs = globs.flatMap((g) => alternatives.map((a) => g + a));
  });
  return globs;
}

// --- The token files --------------------------------------------------------
const CONTRACT_SCHEMA = 'web-design-suite/contract/1';
const CONTRACT_SECTIONS = ['ramps', 'scales', 'roles', 'breakpoints', 'constants'];

// A token file named `*.json` is a contract.json; anything else is CSS.
export function isContract(file) {
  return path.extname(file).toLowerCase() === '.json';
}

// Read and check a contract.json, as read_contract() does.
export function readContract(file) {
  const data = readJson(file, file);
  if (!isObject(data) || data.schema !== CONTRACT_SCHEMA)
    throw new ConfigError(`${file}: not a contract.json ("schema" is not "${CONTRACT_SCHEMA}")`);
  for (const section of CONTRACT_SECTIONS) {
    const value = has(data, section) ? data[section] : {};
    if (!isObject(value)) throw new ConfigError(`${file}: "${section}" must be an object`);
    const nested = section === 'ramps' || section === 'scales';
    for (const [name, entry] of Object.entries(value)) {
      if (section === 'ramps' && isObject(entry)) {
        const step = Object.keys(entry).find((s) => !/^[0-9]+$/.test(s));
        if (step !== undefined) throw new ConfigError(`${file}: "ramps.${name}.${step}" must be a numeric step`);
      }
      const values = nested && isObject(entry) ? Object.values(entry) : [entry];
      if ((nested && !isObject(entry)) || !values.every((v) => typeof v === 'string')) {
        throw new ConfigError(`${file}: "${section}.${name}" must be ${nested ? 'an object of strings' : 'a string'}`);
      }
    }
    data[section] = value;
  }
  return data;
}

const RAMP_STEP = /^--([a-z][a-z0-9]*(?:-[a-z][a-z0-9]*)*)-([0-9]+)$/;
const COLOUR_LITERAL = /^(?:#[0-9a-f]{3,8}|(?:rgba?|hsla?|hwb|lab|lch|oklab|oklch|color)\()/i;
const ROOT_SELECTOR = /^(?::root|html|:where\(:root\)|\*)(?![\w-])/;
const THEME_OR_DENSITY = /\[data-(?:theme|density)\s*[~|^$*]?=/;

// A project's tokens in the contract's sections, as Maps, so a name such as
// `__proto__` is only a name.
class Tokens {
  constructor() {
    this.ramps = new Map();
    this.scales = new Map();
    this.roles = new Map();
    this.breakpoints = new Map();
    this.constants = new Map();
  }

  names() {
    const out = [];
    for (const [ramp, steps] of this.ramps) for (const step of steps.keys()) out.push(`--${ramp}-${step}`);
    for (const [head, steps] of this.scales) for (const step of steps.keys()) out.push(`--${head}-${step}`);
    for (const name of this.breakpoints.keys()) out.push(`--bp-${name}`);
    return [...out, ...this.constants.keys(), ...this.roles.keys()];
  }

  discard(name) {
    this.roles.delete(name);
    this.constants.delete(name);
    if (name.startsWith('--bp-')) this.breakpoints.delete(name.slice(5));
    for (const section of [this.ramps, this.scales]) {
      for (const [head, steps] of [...section]) {
        if (!name.startsWith(`--${head}-`)) continue;
        steps.delete(name.slice(head.length + 3));
        if (!steps.size) section.delete(head);
      }
    }
  }

  // File one default value in its section, as ProjectTokens.add() does.
  add(name, value, tier) {
    const ramp = RAMP_STEP.exec(name);
    const into = (section, head, step) => {
      if (!section.has(head)) section.set(head, new Map());
      section.get(head).set(step, value);
    };
    if (tier === 2) this.roles.set(name, value);
    else if (name.startsWith('--bp-')) this.breakpoints.set(name.slice(5), value);
    else if (ramp && COLOUR_LITERAL.test(value)) into(this.ramps, ramp[1], ramp[2]);
    else {
      const dash = name.indexOf('-', 2);
      const step = dash < 0 ? '' : name.slice(dash + 1);
      if (step) into(this.scales, name.slice(2, dash), step);
      else this.constants.set(name, value);
    }
  }

  plain() {
    const nested = (section) => Object.fromEntries([...section].map(([k, v]) => [k, Object.fromEntries(v)]));
    return { ramps: nested(this.ramps), scales: nested(this.scales), roles: Object.fromEntries(this.roles),
             breakpoints: Object.fromEntries(this.breakpoints), constants: Object.fromEntries(this.constants) };
  }
}

// Each declaration in a stylesheet with the preludes around it, outermost
// first. Quotes and brackets are skipped, so a `;` in a data URL does not end
// a declaration.
function* cssBlocks(source) {
  const text = source.replace(/\/\*[\s\S]*?\*\//g, ' ');
  const stack = [];
  let start = 0, depth = 0, quote = '';
  for (let i = 0; i < text.length; i += 1) {
    const ch = text[i];
    if (quote) {
      if (ch === '\\') i += 1;
      else if (ch === quote) quote = '';
    } else if (ch === '"' || ch === "'") {
      quote = ch;
    } else if (ch === '(' || ch === '[') {
      depth += 1;
    } else if (ch === ')' || ch === ']') {
      depth = Math.max(0, depth - 1);
    } else if (depth === 0 && (ch === '{' || ch === '}' || ch === ';')) {
      const chunk = text.slice(start, i).trim();
      if (ch === '{') {
        stack.push(chunk);
      } else {
        if (chunk) yield [[...stack], chunk];
        if (ch === '}' && stack.length) stack.pop();
      }
      start = i + 1;
    }
  }
}

function cssTokens(file) {
  let text;
  try {
    text = fs.readFileSync(file).toString('utf8').replace(/^﻿/, '');
  } catch (err) {
    throw new ConfigError(`${file}: ${err.code === 'ENOENT' ? 'No such file or directory' : err.message}`);
  }
  const defaults = new Map();
  for (const [preludes, declaration] of cssBlocks(text)) {
    const colon = declaration.indexOf(':');
    if (colon < 0) continue;
    const name = declaration.slice(0, colon).trim();
    const value = declaration.slice(colon + 1).split(/\s+/).filter(Boolean).join(' ');
    if (!(name.startsWith('--') && value && preludes.length)) continue;
    const rule = preludes[preludes.length - 1];
    if (preludes.slice(0, -1).every((p) => p.toLowerCase().startsWith('@layer'))
        && ROOT_SELECTOR.test(rule) && !THEME_OR_DENSITY.test(rule)) {
      defaults.set(name, value);                // the cascade: the last one wins
    }
  }
  const tokens = new Tokens();
  for (const [name, value] of defaults) tokens.add(name, value, value.includes('var(') ? 2 : 1);
  return tokens;
}

// A project's token files, contract.json or tokens.css, read in order into
// one set of sections, as read_tokens() does: a later file's value wins, step
// by step for a ramp or a scale, and a name a later file files in another
// section leaves the earlier one.
export function readTokens(paths) {
  const out = new Tokens();
  for (const file of paths) {
    let part;
    if (isContract(file)) {
      const data = readContract(file);
      part = new Tokens();
      for (const section of ['ramps', 'scales']) {
        for (const [name, steps] of Object.entries(data[section])) part[section].set(name, new Map(Object.entries(steps)));
      }
      for (const section of ['roles', 'breakpoints', 'constants']) part[section] = new Map(Object.entries(data[section]));
    } else {
      part = cssTokens(file);
    }
    for (const name of part.names()) out.discard(name);
    for (const section of ['ramps', 'scales']) {
      for (const [name, steps] of part[section]) {
        if (!out[section].has(name)) out[section].set(name, new Map());
        for (const [step, value] of steps) out[section].get(name).set(step, value);
      }
    }
    for (const section of ['roles', 'breakpoints', 'constants']) {
      for (const [name, value] of part[section]) out[section].set(name, value);
    }
  }
  const plain = out.plain();
  const byNumber = (steps) => Object.fromEntries(Object.entries(steps).sort(([a], [b]) => Number(a) - Number(b)));
  return { ...plain, ramps: Object.fromEntries(Object.entries(plain.ramps).map(([n, s]) => [n, byNumber(s)])) };
}

// --- What the lint configs take from the project (N37) ---------------------
// As audit_design.py reads the same config: the token files it names are
// token files wherever they sit, its `components` globs add to the component
// files, and the ramp steps its tokens declare are Tier-1 colours with a role.
// `start` is the working directory, where the audit looks too.
export function lintProject(start = process.cwd()) {
  const config = projectConfig(start);
  if (!config) return { config: null, tokenGlobs: [], componentGlobs: [], isComponent: () => false, rampSteps: [] };
  const ramps = readTokens(config.tokens).ramps;
  const roots = rootSpellings(config.root, start);
  return {
    config,
    tokenGlobs: config.tokens.flatMap((file) => fileSpellings(file, roots).map(asGlob)),
    componentGlobs: config.components.flatMap((g) => overrideGlobs(roots, g)),
    isComponent: (file) => isComponent(config, file),
    rampSteps: Object.entries(ramps).flatMap(([ramp, steps]) => Object.keys(steps).map((s) => `--${ramp}-${s}`)),
  };
}
