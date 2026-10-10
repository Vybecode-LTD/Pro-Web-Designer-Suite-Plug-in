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

// A token file named `*.json` or `*.tokens` is JSON: a contract.json or a
// DTCG document (P31). Anything else is CSS.
export function isContract(file) {
  return ['.json', '.tokens'].includes(path.extname(file).toLowerCase());
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

// --- DTCG 2025.10 token files (P31) -------------------------------------------
// A port of what read_tokens() takes from dtcg.py: tokens(), the lossless
// reading. Each token's CSS name is its path joined by `-`, a reference is
// `var(--name)`, `$extends` groups merge, `$root` is the group's own token,
// `$type` is inherited, and a value with no CSS form is left out. The numbers
// are written as Python's f"{round(x, 6):g}" writes them, so both readers give
// the same values (tests/test_project_config.py holds them to it).
const DTCG_META = new Set(['$schema', '$description', '$extensions', '$type', '$deprecated', '$extends']);
const UNSUPPORTED = Symbol('unsupported');
const CSS_SPACES = new Set(['display-p3', 'a98-rgb', 'prophoto-rgb', 'rec2020', 'xyz-d65', 'xyz-d50']);
// Python's float `%` (CPython's float_rem): fmod, moved to the divisor's sign.
const pyMod = (a, b) => {
  const mod = a % b;
  if (mod) return (b < 0) !== (mod < 0) ? mod + b : mod;
  return b < 0 ? -0 : 0;
};
const pyTruthy = (v) => !(v === undefined || v === null || v === false || v === 0 || v === ''
  || (Array.isArray(v) && !v.length) || (isObject(v) && !Object.keys(v).length));

// Python's float() for a JSON value: a number, a boolean or a numeric string.
function pyFloat(x) {
  if (typeof x === 'number') return x;
  if (typeof x === 'boolean') return Number(x);
  if (typeof x === 'string') {
    const t = x.trim().toLowerCase().replace(/(?<=\d)_(?=\d)/g, '');
    if (/^[+-]?(?:\d+\.?\d*|\.\d+)(?:e[+-]?\d+)?$/.test(t)) return Number(t);
    if (/^[+-]?(?:inf|infinity)$/.test(t)) return t.startsWith('-') ? -Infinity : Infinity;
    if (/^[+-]?nan$/.test(t)) return NaN;
  }
  throw new TypeError('not a number');
}

// The digits of |x| to 100 places (exact for any double under 1e21).
function roundHalfEven(x, places) {
  if (!Number.isFinite(x) || Math.abs(x) >= 1e21) return x;
  const [whole, frac] = Math.abs(x).toFixed(100).split('.');
  const kept = whole + frac.slice(0, places);
  const rest = frac.slice(places);
  let digits = BigInt(kept);
  const half = '5' + '0'.repeat(rest.length - 1);
  if (rest > half || (rest === half && digits % 2n === 1n)) digits += 1n;
  const text = digits.toString().padStart(places + 1, '0');
  const value = Number(`${text.slice(0, text.length - places)}.${text.slice(text.length - places)}`);
  return x < 0 || Object.is(x, -0) ? -value : value;
}

// Python's f"{x:g}": six significant digits, trailing zeros dropped.
function formatG(x) {
  if (Number.isNaN(x)) return 'nan';
  if (!Number.isFinite(x)) return x > 0 ? 'inf' : '-inf';
  if (x === 0) return Object.is(x, -0) ? '-0' : '0';
  const [mantissa, exp] = x.toExponential(5).split('e');
  const e = Number(exp);
  const strip = (s) => (s.includes('.') ? s.replace(/0+$/, '').replace(/\.$/, '') : s);
  if (e < -4 || e >= 6) return `${strip(mantissa)}e${e < 0 ? '-' : '+'}${String(Math.abs(e)).padStart(2, '0')}`;
  return strip(x.toFixed(5 - e));
}

const fmt = (n) => formatG(roundHalfEven(pyFloat(n), 6));
const pyRoundInt = (v) => {
  const f = Math.floor(v);
  const d = v - f;
  return d > 0.5 ? f + 1 : d < 0.5 ? f : (f % 2 === 0 ? f : f + 1);
};
const componentOf = (x) => (x === null || x === undefined || (typeof x === 'string' && x.trim().toLowerCase() === 'none') ? 0 : pyFloat(x));
const srgbEncode = (c) => (c <= 0.0031308 ? 12.92 * c : 1.055 * c ** (1 / 2.4) - 0.055);

function rgbCss(r, g, b, alpha) {
  const [cr, cg, cb] = [r, g, b].map((c) => Math.min(1, Math.max(0, c)));
  if (alpha >= 1) return `#${[cr, cg, cb].map((c) => pyRoundInt(c * 255).toString(16).padStart(2, '0')).join('')}`;
  return `rgb(${fmt(cr * 255)} ${fmt(cg * 255)} ${fmt(cb * 255)} / ${fmt(alpha)})`;
}

// Python's colorsys.hls_to_rgb.
function hlsToRgb(h, l, s) {
  if (s === 0) return [l, l, l];
  const m2 = l <= 0.5 ? l * (1 + s) : l + s - l * s;
  const m1 = 2 * l - m2;
  const v = (hue) => {
    const x = pyMod(hue, 1);
    if (x < 1 / 6) return m1 + (m2 - m1) * x * 6;
    if (x < 0.5) return m2;
    if (x < 2 / 3) return m1 + (m2 - m1) * (2 / 3 - x) * 6;
    return m1;
  };
  return [v(h + 1 / 3), v(h), v(h - 1 / 3)];
}

function hwbRgb(h, w, b) {
  const [ww, bb] = [w / 100, b / 100];
  if (ww + bb >= 1) {
    const grey = ww / (ww + bb);
    return [grey, grey, grey];
  }
  return hlsToRgb(pyMod(h, 360) / 360, 0.5, 1).map((c) => c * (1 - ww - bb) + ww);
}

function colourToCss(v) {
  const space = String(has(v, 'colorSpace') ? v.colorSpace : '').trim().toLowerCase();
  let comps, alpha;
  try {
    const raw = v.components;                       // Python: `components or []`, iterated
    if (pyTruthy(raw) && !Array.isArray(raw)) return null;
    comps = (pyTruthy(raw) ? raw : []).map(componentOf);
    alpha = v.alpha === undefined || v.alpha === null || v.alpha === 'none' ? 1 : pyFloat(v.alpha);
  } catch {
    return null;
  }
  if (comps.length === 3) {
    if (space === 'srgb') return rgbCss(...comps, alpha);
    if (space === 'srgb-linear') return rgbCss(...comps.map(srgbEncode), alpha);
    if (space === 'hsl') return rgbCss(...hlsToRgb(pyMod(comps[0], 360) / 360, comps[2] / 100, comps[1] / 100), alpha);
    if (space === 'hwb') return rgbCss(...hwbRgb(...comps), alpha);
    if (space === 'oklch' || space === 'oklab') {
      let [L, x, y] = comps;
      if (space === 'oklab') [x, y] = [Math.hypot(x, y), pyMod(Math.atan2(y, x) * (180 / Math.PI), 360)];
      return `oklch(${fmt(L * 100)}% ${fmt(x)} ${fmt(y)}${alpha >= 1 ? '' : ` / ${fmt(alpha)}`})`;
    }
  }
  const hex = v.hex;
  if (typeof hex === 'string' && hex.startsWith('#') && hex.length === 7) {
    const parts = [1, 3, 5].map((i) => hex.slice(i, i + 2));
    if (!parts.every((p) => /^\s*[+-]?[0-9a-f]+\s*$/i.test(p))) return null;
    return rgbCss(...parts.map((p) => parseInt(p.trim(), 16) / 255), alpha);
  }
  if (comps.length === 3 && (CSS_SPACES.has(space) || space === 'lab' || space === 'lch')) {
    const args = comps.map(fmt).join(' ') + (alpha >= 1 ? '' : ` / ${fmt(alpha)}`);
    return space === 'lab' || space === 'lch' ? `${space}(${args})` : `color(${space} ${args})`;
  }
  return null;
}

// A run of ASCII a custom property cannot hold unescaped is one `-`, as css_name() writes it.
const dtcgName = (parts) => `--${parts.map((p) => String(p).replace(/[^A-Za-z0-9_\-\u0080-\u{10FFFF}]+/gu, '-')).join('-')}`;

// Objects or arrays nested more than 64 deep, as dtcg.py's too_deep() finds them.
function tooDeep(data, limit = 64) {
  const stack = [[data, 0]];
  while (stack.length) {
    const [node, depth] = stack.pop();
    if (depth > limit) return true;
    if (isObject(node)) for (const v of Object.values(node)) stack.push([v, depth + 1]);
    else if (Array.isArray(node)) for (const v of node) stack.push([v, depth + 1]);
  }
  return false;
}

function refCss(v) {
  const alias = typeof v === 'string' && v.trim().startsWith('{') ? pointerAlias(v) : null;
  return alias ? `var(${dtcgName(alias.split('.'))})` : UNSUPPORTED;
}

function dimension(v, kind) {
  if (typeof v === 'string') return refCss(v);
  if (!(isObject(v) && has(v, 'value') && has(v, 'unit'))) return UNSUPPORTED;
  let n;
  try {
    n = pyFloat(v.value);
  } catch {
    return UNSUPPORTED;
  }
  const unit = String(v.unit).trim().toLowerCase();
  if (kind === 'duration' || unit === 'ms' || unit === 's') return unit === 's' ? `${fmt(n * 1000)}ms` : `${fmt(n)}ms`;
  return `${fmt(n)}${unit}`;
}

function colourValue(v) {
  if (isObject(v)) return colourToCss(v) || UNSUPPORTED;
  if (typeof v === 'string' && !v.trim().startsWith('{')) return v;
  return refCss(v);
}

function shadow(layers) {
  const out = [];
  for (const layer of layers) {
    if (!isObject(layer)) return UNSUPPORTED;
    const parts = ['offsetX', 'offsetY', 'blur', 'spread'].map((k) => dimension(layer[k], 'dimension'));
    const colour = colourValue(layer.color);
    if (parts.includes(UNSUPPORTED) || colour === UNSUPPORTED) return UNSUPPORTED;
    out.push((layer.inset ? 'inset ' : '') + [...parts, colour].join(' '));
  }
  return out.join(', ');
}

function bezier(v) {
  if (Array.isArray(v) && v.length === 4 && v.every((x) => ['number', 'boolean'].includes(typeof x))) return `cubic-bezier(${v.map(fmt).join(', ')})`;
  return typeof v === 'string' && !v.startsWith('{') ? v : UNSUPPORTED;
}

function convertValue(value, kind) {
  if (isObject(value) && has(value, '$ref')) {
    const alias = pointerAlias(value.$ref);
    return alias ? `{${alias}}` : UNSUPPORTED;
  }
  if (value === null || ['string', 'number', 'boolean'].includes(typeof value)) return value;
  const k = String(kind || '').toLowerCase();
  if (isObject(value)) {
    if (has(value, 'colorSpace') || k === 'color') return colourValue(value);
    if (['dimension', 'duration', ''].includes(k) && has(value, 'value') && has(value, 'unit')) return dimension(value, k);
    if (k === 'shadow') return shadow([value]);
    if (k === 'border') {
      const parts = [dimension(value.width, 'dimension'), value.style, colourValue(value.color)];
      return parts.includes(UNSUPPORTED) || typeof parts[1] !== 'string' ? UNSUPPORTED : parts.join(' ');
    }
    if (k === 'transition') {
      const parts = [dimension(value.duration, 'duration'), bezier(value.timingFunction),
        dimension(has(value, 'delay') ? value.delay : { value: 0, unit: 'ms' }, 'duration')];
      return parts.includes(UNSUPPORTED) ? UNSUPPORTED : parts.join(' ');
    }
    return UNSUPPORTED;
  }
  if (Array.isArray(value)) {
    if (k === 'cubicbezier') return bezier(value);
    if (k === 'shadow') return shadow(value);
    if ((k === 'fontfamily' || k === '') && value.length && value.every((x) => typeof x === 'string')) {
      return value.map((x) => (x.includes(' ') ? `"${x}"` : x)).join(', ');
    }
  }
  return UNSUPPORTED;
}

function pointerAlias(ref) {
  if (typeof ref !== 'string') return null;
  const s = ref.trim();
  let parts;
  if (s.startsWith('{') && s.endsWith('}')) parts = s.slice(1, -1).split('.');
  else if (s.startsWith('#/')) {
    parts = s.slice(2).split('/').map((p) => p.replaceAll('~1', '/').replaceAll('~0', '~'));
    if (parts.length && parts[parts.length - 1] === '$value') parts = parts.slice(0, -1);
  } else return null;
  if (parts.length > 1 && parts[parts.length - 1] === '$root') parts = parts.slice(0, -1);
  if (!parts.length || parts.some((p) => !p || p.startsWith('$'))) return null;
  return parts.join('.');
}

function lookupGroup(root, ref) {
  const alias = pointerAlias(ref);
  if (alias === null) return null;
  let node = root;
  for (const part of alias.split('.')) {
    if (!isObject(node) || !has(node, part)) return null;
    node = node[part];
  }
  return node;
}

function overlay(base, own) {
  for (const [key, value] of Object.entries(own)) {
    if (isObject(value) && isObject(base[key]) && has(base, key) && !has(value, '$value') && !has(base[key], '$value')) {
      overlay(base[key], value);
    } else {
      base[key] = structuredClone(value);
    }
  }
}

function resolveExtends(node, root, active) {
  if (!isObject(node)) return;
  if (has(node, '$extends')) {
    const ref = node.$extends;
    delete node.$extends;
    const target = lookupGroup(root, ref);
    if (isObject(target) && !has(target, '$value') && target !== node && !active.has(target)) {
      active.add(node);
      resolveExtends(target, root, active);
      active.delete(node);
      const merged = structuredClone(target);
      overlay(merged, node);
      for (const key of Object.keys(node)) delete node[key];
      Object.assign(node, merged);
    }
  }
  for (const [key, child] of Object.entries(node)) {
    if (isObject(child) && !DTCG_META.has(key)) resolveExtends(child, root, active);
  }
}

// What a JSON Pointer addresses, or UNSUPPORTED, as _pointer() reads it.
function jsonPointer(root, ref) {
  let node = root;
  for (const raw of ref.slice(2).split('/')) {
    const part = raw.replaceAll('~1', '/').replaceAll('~0', '~');
    if (isObject(node) && has(node, part)) node = node[part];
    else if (Array.isArray(node) && /^[0-9]+$/.test(part) && Number(part) < node.length) node = node[Number(part)];
    else return UNSUPPORTED;
  }
  return node;
}

// A property-level `$ref` is the literal it points at, as _inline_pointers() does.
function inlinePointers(node, root) {
  const literal = (ref, seen) => {
    const target = seen.includes(ref) ? UNSUPPORTED : jsonPointer(root, ref);
    return target === UNSUPPORTED ? target : fix(structuredClone(target), [...seen, ref]);
  };
  const fix = (value, seen) => {
    if (isObject(value) && typeof value.$ref === 'string' && value.$ref.startsWith('#/')) {
      const alias = pointerAlias(value.$ref);
      if (alias) return `{${alias}}`;
      const found = literal(value.$ref, seen);
      return found === UNSUPPORTED ? value : found;
    }
    if (isObject(value)) return Object.fromEntries(Object.entries(value).map(([k, v]) => [k, fix(v, seen)]));
    if (Array.isArray(value)) return value.map((v) => fix(v, seen));
    return value;
  };
  if (!isObject(node)) return;
  const ref = node.$ref;
  if (has(node, '$value')) {
    node.$value = fix(node.$value, []);
  } else if (typeof ref === 'string' && ref.startsWith('#/') && !pointerAlias(ref)) {
    const found = literal(ref, []);
    if (found !== UNSUPPORTED) {
      node.$value = found;
      delete node.$ref;
    }
  } else {
    for (const [key, child] of Object.entries(node)) if (!DTCG_META.has(key)) inlinePointers(child, root);
  }
}

// [[name, value as CSS or null]] in document order.
function dtcgEntries(data) {
  if (tooDeep(data)) return [];
  const doc = structuredClone(data);
  resolveExtends(doc, doc, new Set());
  inlinePointers(doc, doc);
  const out = [];
  const token = (node, path, kind) => {
    const type = has(node, '$type') ? node.$type : kind;
    let value;
    if (!has(node, '$value')) {
      const alias = pointerAlias(node.$ref);
      if (alias === null) return;
      value = `{${alias}}`;
    } else {
      value = convertValue(node.$value, type);
      if (value === UNSUPPORTED) return;
    }
    const alias = typeof value === 'string' && value.startsWith('{') && value.endsWith('}') ? pointerAlias(value) : null;
    let css;
    if (alias) css = `var(${dtcgName(alias.split('.'))})`;
    else if (typeof value === 'boolean' || value === null) css = null;
    else if (typeof value === 'number') css = fmt(value);
    else css = String(value).split(/\s+/).filter(Boolean).join(' ') || null;
    out.push([dtcgName(path), css]);
  };
  const walk = (node, path, kind) => {
    if (!isObject(node)) return;
    if (has(node, '$value') || has(node, '$ref')) {
      token(node, path, kind);
      return;
    }
    const groupKind = has(node, '$type') ? node.$type : kind;
    for (const [key, child] of Object.entries(node)) {
      if (key === '$root') {
        if (isObject(child)) token(child, path, groupKind);    // the group's own token: same path
      } else if (!DTCG_META.has(key)) {
        walk(child, [...path, key], groupKind);
      }
    }
  };
  walk(doc, [], null);
  // Each member of a reference cycle is left out, as tokens() leaves it out.
  const graph = new Map();
  for (const [name, css] of out) {
    const m = /^var\((--.+)\)$/.exec(css ?? '');
    if (m) graph.set(name, m[1]);
  }
  const cyclic = new Set();
  for (const start of graph.keys()) {
    const chain = [];
    let cur = start;
    while (graph.has(cur) && !chain.includes(cur)) {
      chain.push(cur);
      cur = graph.get(cur);
    }
    if (chain.includes(cur)) chain.slice(chain.indexOf(cur)).forEach((n) => cyclic.add(n));
  }
  return out.filter(([name]) => !cyclic.has(name));
}

function isDtcg(data) {
  if (isObject(data) && has(data, 'schema')) return false;
  const holds = (node, depth) => {
    if (!isObject(node) || depth > 64) return false;
    if (depth && (has(node, '$value') || typeof node.$ref === 'string')) return true;
    return Object.entries(node).some(([k, v]) => k !== '$extensions' && k !== '$schema' && holds(v, depth + 1));
  };
  return holds(data, 0);
}

function dtcgTokens(data) {
  const tokens = new Tokens();
  for (const [name, value] of dtcgEntries(data)) {
    if (value !== null) tokens.add(name, value, value.includes('var(') ? 2 : 1);   // as cssTokens files them
  }
  return tokens;
}

// A project's token files, contract.json, DTCG or tokens.css, read in order into
// one set of sections, as read_tokens() does: a later file's value wins, step
// by step for a ramp or a scale, and a name a later file files in another
// section leaves the earlier one.
export function readTokens(paths) {
  const out = new Tokens();
  for (const file of paths) {
    let part;
    const json = isContract(file) ? readJson(file) : null;
    if (isContract(file) && isDtcg(json)) {
      part = dtcgTokens(json);
    } else if (isContract(file)) {
      if (!(isObject(json) && has(json, 'schema'))) {
        throw new ConfigError(`${file}: neither a contract.json (no "schema") nor a DTCG token file (no "$value")`);
      }
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
