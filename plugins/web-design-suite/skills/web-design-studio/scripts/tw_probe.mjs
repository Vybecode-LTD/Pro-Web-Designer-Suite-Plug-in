#!/usr/bin/env node
/**
 * tw_probe.mjs — which classes the project's own Tailwind v4 generates.
 *
 * Tailwind generates no CSS for a class it does not know, and says nothing,
 * so "the theme removed `p-4`" and "the theme gives `bg-surface`" are claims
 * nobody sees fail. This compiles the project's entry stylesheet with the
 * project's own tailwindcss and checks both (SB-C3):
 *
 *   roles   every theme variable the entry's `@theme` blocks declare, in a
 *           namespace Tailwind turns into utilities, gives its class
 *           (`--color-surface` gives `bg-surface`, `--spacing-card` gives
 *           `p-card`, `--breakpoint-md` gives `md:`);
 *   stock   none of a sample of Tailwind's default classes generates
 *           (`p-4`, `bg-neutral-800`, `text-sm`), unless the theme declares
 *           that name itself. One that does means a default namespace
 *           survived: `--spacing` alone keeps every numeric spacing class.
 *
 * The namespaces are tailwindcss.com's "Theme variable namespaces" table
 * (docs/theme, read 2026-10-13). A class counts as generated when Tailwind
 * writes a rule for it: the stylesheet's own CSS (a `.stack` in layout.css)
 * is not Tailwind's, so it does not count.
 *
 * Usage, from the project's root:
 *   node tw_probe.mjs [--entry FILE] [--expect CLASS]... [--refuse CLASS]... [--json] [CLASS ...]
 *
 *   --entry FILE    the stylesheet that imports tailwindcss (default
 *                   src/styles/index.css, stack-tailwind.md §2)
 *   --expect CLASS  a class that must generate (repeatable)
 *   --refuse CLASS  a class that must not (repeatable)
 *   CLASS ...       classes to report on, without a verdict
 *
 * tailwindcss is found in the node_modules folders above the working folder,
 * then in NODE_PATH; never in the plugin. Exit 0 when every check holds, 1
 * when one fails, 2 when it cannot run (no tailwindcss 4, no entry, a file
 * it imports that cannot be read).
 */

import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { pathToFileURL } from 'node:url';

const DEFAULT_ENTRY = 'src/styles/index.css';

// Theme variable namespace → the class one of its variables gives. The
// longer prefix first: `--font-weight-*` before `--font-*`.
const NAMESPACES = [
  ['--color-', (k) => `bg-${k}`],
  ['--font-weight-', (k) => `font-${k}`],
  ['--font-', (k) => `font-${k}`],
  ['--text-', (k) => `text-${k}`],
  ['--tracking-', (k) => `tracking-${k}`],
  ['--leading-', (k) => `leading-${k}`],
  ['--tab-size-', (k) => `tab-${k}`],
  ['--breakpoint-', (k) => `${k}:block`],
  ['--container-', (k) => `@${k}:block`],
  ['--spacing-', (k) => `p-${k}`],
  ['--radius-', (k) => `rounded-${k}`],
  ['--shadow-', (k) => `shadow-${k}`],
  ['--inset-shadow-', (k) => `inset-shadow-${k}`],
  ['--drop-shadow-', (k) => `drop-shadow-${k}`],
  ['--blur-', (k) => `blur-${k}`],
  ['--perspective-', (k) => `perspective-${k}`],
  ['--zoom-', (k) => `zoom-${k}`],
  ['--aspect-', (k) => `aspect-${k}`],
  ['--ease-', (k) => `ease-${k}`],
  ['--animate-', (k) => `animate-${k}`],
];

// A sample of Tailwind's defaults, each with what keeps it alive. A theme
// that replaced the scale (`--*: initial`) generates none of them.
const STOCK = [
  ['p-4', '--spacing'], ['m-2', '--spacing'], ['gap-4', '--spacing'], ['w-4', '--spacing'],
  ['leading-7', '--spacing'],
  ['bg-neutral-800', '--color-*'], ['bg-gray-100', '--color-*'], ['text-white', '--color-*'],
  ['text-sm', '--text-*'], ['font-bold', '--font-weight-*'], ['font-sans', '--font-*'],
  ['tracking-wide', '--tracking-*'], ['rounded-lg', '--radius-*'], ['shadow-md', '--shadow-*'],
  ['inset-shadow-xs', '--inset-shadow-*'], ['drop-shadow-md', '--drop-shadow-*'],
  ['max-w-md', '--container-*'], ['blur-md', '--blur-*'], ['ease-out', '--ease-*'],
  ['animate-spin', '--animate-*'], ['aspect-video', '--aspect-*'], ['perspective-near', '--perspective-*'],
];

function die(message) {
  process.stderr.write(`tw_probe: ${message}\n`);
  process.exit(2);
}

function parseArgs(argv) {
  const args = { entry: DEFAULT_ENTRY, expect: [], refuse: [], probe: [], json: false };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    const value = () => {
      if (i + 1 >= argv.length || argv[i + 1].startsWith('--')) die(`${a} needs a value`);
      return argv[++i];
    };
    if (a === '--entry') args.entry = value();
    else if (a === '--expect') args.expect.push(value());
    else if (a === '--refuse') args.refuse.push(value());
    else if (a === '--json') args.json = true;
    else if (a === '--help' || a === '-h') {
      process.stdout.write('usage: node tw_probe.mjs [--entry FILE] [--expect CLASS]... '
        + '[--refuse CLASS]... [--json] [CLASS ...]\n');
      process.exit(0);
    } else if (a === '--') args.probe.push(...argv.slice(i + 1)), i = argv.length;
    else if (a.startsWith('--')) die(`unknown option ${a}`);
    else args.probe.push(a);
  }
  return args;
}

// A manifest an editor saved may start with a byte-order mark, which
// JSON.parse refuses.
function readJson(file) {
  const text = fs.readFileSync(file, 'utf8');
  return JSON.parse(text.charCodeAt(0) === 0xfeff ? text.slice(1) : text);
}

function nodeModulesRoots(dir) {
  const roots = [];
  for (let d = path.resolve(dir); ; d = path.dirname(d)) {
    roots.push(path.join(d, 'node_modules'));
    if (path.dirname(d) === d) break;
  }
  if (process.env.NODE_PATH) roots.push(...process.env.NODE_PATH.split(path.delimiter).filter(Boolean));
  return roots;
}

function findPackage(name, from) {
  for (const root of nodeModulesRoots(from)) {
    const dir = path.join(root, ...name.split('/'));
    if (fs.existsSync(path.join(dir, 'package.json'))) return dir;
  }
  return null;
}

// A bare `@import "pkg"` or `@import "pkg/file.css"`: the package's `style`
// export or field, else its index.css; a subpath as written.
function packageStylesheet(id, base) {
  const parts = id.split('/');
  const name = id.startsWith('@') ? parts.slice(0, 2).join('/') : parts[0];
  const sub = id.slice(name.length + 1);
  const dir = findPackage(name, base);
  if (!dir) die(`cannot find the package of @import "${id}" from ${base}`);
  if (sub) {
    const file = path.join(dir, sub);
    return fs.existsSync(file) || path.extname(sub) ? file : `${file}.css`;
  }
  const manifest = readJson(path.join(dir, 'package.json'));
  const dot = manifest.exports && (manifest.exports['.'] ?? manifest.exports);
  const style = (dot && typeof dot === 'object' && dot.style) || manifest.style || 'index.css';
  return path.join(dir, style);
}

// Every @theme block's top-level custom properties, in order, with
// `--*: initial` and `--ns-*: initial` clearing what came before.
function themeVariables(sheets) {
  const vars = new Map();
  for (const css of sheets) {
    const text = css.replace(/\/\*[\s\S]*?\*\//g, '');
    const opener = /@theme\b[^{;]*\{/g;
    let m;
    while ((m = opener.exec(text))) {
      // The block's own declarations; a nested block (`@keyframes`) is skipped.
      const decls = [];
      let depth = 1, i = opener.lastIndex, start = i;
      for (; i < text.length; i++) {
        const ch = text[i];
        if (ch === '{') {
          depth++;
        } else if (ch === '}') {
          depth--;
          if (depth === 0) { decls.push(text.slice(start, i)); break; }
          if (depth === 1) start = i + 1;
        } else if (ch === ';' && depth === 1) {
          decls.push(text.slice(start, i));
          start = i + 1;
        }
      }
      for (const d of decls) {
        const found = /^\s*(--[\w-]*(?:\*)?)\s*:\s*([\s\S]*?)\s*$/.exec(d);
        if (!found) continue;
        const [, name, value] = found;
        if (value === 'initial') {
          if (name === '--*') vars.clear();
          else if (name.endsWith('-*')) {
            for (const k of [...vars.keys()]) if (k.startsWith(name.slice(0, -1))) vars.delete(k);
          } else vars.delete(name);
        } else if (!name.includes('*')) {
          vars.set(name, value);
        }
      }
      opener.lastIndex = i;
    }
  }
  return vars;
}

function roleClass(variable) {
  for (const [prefix, cls] of NAMESPACES) {
    if (!variable.startsWith(prefix)) continue;
    const key = variable.slice(prefix.length);
    // `--text-h1--line-height` is a property of `text-h1`, not a class.
    return key && !key.includes('--') ? cls(key) : null;
  }
  return null;
}

// CSS.escape, as Tailwind escapes a class into its selector.
function cssEscape(s) {
  let out = '';
  for (let i = 0; i < s.length; i++) {
    const c = s.charCodeAt(i);
    if (c === 0) out += '�';
    else if ((c >= 1 && c <= 0x1f) || c === 0x7f || (i === 0 && c >= 0x30 && c <= 0x39)
      || (i === 1 && c >= 0x30 && c <= 0x39 && s.charCodeAt(0) === 0x2d)) out += `\\${c.toString(16)} `;
    else if (i === 0 && s.length === 1 && c === 0x2d) out += `\\${s[i]}`;
    else if (c >= 0x80 || c === 0x2d || c === 0x5f || (c >= 0x30 && c <= 0x39)
      || (c >= 0x41 && c <= 0x5a) || (c >= 0x61 && c <= 0x7a)) out += s[i];
    else out += `\\${s[i]}`;
  }
  return out;
}

// How many rules' selectors name `.cls`, the class ending where the
// selector does.
function selectorCount(css, cls) {
  const needle = `.${cssEscape(cls)}`;
  let n = 0;
  for (let at = css.indexOf(needle); at !== -1; at = css.indexOf(needle, at + 1)) {
    const next = css[at + needle.length] || '';
    if (!/[\w\\-]/.test(next) && !(next >= '\u0080')) n++;
  }
  return n;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const cwd = process.cwd();
  const twDir = findPackage('tailwindcss', cwd);
  if (!twDir) {
    die('cannot find tailwindcss in the node_modules folders above this folder, or in NODE_PATH.\n'
      + '  Run it from the project\'s root, after the project\'s own install.');
  }
  const version = readJson(path.join(twDir, 'package.json')).version;
  if (Number(version.split('.')[0]) < 4) {
    die(`the project has tailwindcss ${version}. Tailwind 3 has no CSS entry to compile: Part 5 of `
      + 'eslint.design.config.mjs, with its tailwindConfig line, checks a v3 project\'s classes.');
  }
  const entry = path.resolve(cwd, args.entry);
  if (!fs.existsSync(entry)) die(`no entry stylesheet at ${args.entry}: pass --entry FILE`);

  const require = createRequire(path.join(twDir, 'package.json'));
  // require.resolve finds the CommonJS build, whose exports arrive as `default`.
  const tailwind = await import(pathToFileURL(require.resolve('tailwindcss')).href);
  const compile = tailwind.compile ?? tailwind.default?.compile;
  if (typeof compile !== 'function') die(`tailwindcss ${version} exports no compile()`);
  const resolveImport = (id, base) => {
    if (id === 'tailwindcss' || id.startsWith('tailwindcss/')) {
      let sub = id === 'tailwindcss' ? 'index.css' : id.slice('tailwindcss/'.length);
      if (!path.extname(sub)) sub += '.css';
      return path.join(twDir, sub);
    }
    if (id.startsWith('.') || path.isAbsolute(id)) return path.resolve(base, id);
    return packageStylesheet(id, base);
  };
  const read = (file, id) => {
    try {
      return fs.readFileSync(file, 'utf8');
    } catch (err) {
      return die(`cannot read @import "${id}" (${file}): ${err.code || err.message}`);
    }
  };
  // `@source inline("p-card")` puts its classes in the very first build, so
  // asking for one adds no rule and it would read as not generated. Those
  // lines are set aside: a class counts for what Tailwind generates when
  // asked. `@source not inline()` stays, and still blocks its classes.
  const withoutInline = (css) => css.replace(/@source\s+inline\(\s*(?:"[^"]*"|'[^']*')\s*\)\s*;?/g, '');
  const loadStylesheet = async (id, base) => {
    const file = resolveImport(id, base);
    return { path: file, base: path.dirname(file), content: withoutInline(read(file, id)) };
  };
  // The project's stylesheets in cascade order, each after the files it
  // imports (an @import precedes every rule of its file). Tailwind's own
  // files are left out: its default theme is what a project replaces.
  const ownSheets = (file, id, seen = new Set(), out = []) => {
    if (seen.has(file)) return out;
    seen.add(file);
    const text = read(file, id).replace(/\/\*[\s\S]*?\*\//g, '');
    for (const m of text.matchAll(/@(?:import|reference)\s+(?:url\(\s*)?["']([^"']+)["']/g)) {
      const child = resolveImport(m[1], path.dirname(file));
      const inTailwind = !path.relative(twDir, child).startsWith('..') && !path.isAbsolute(path.relative(twDir, child));
      if (!inTailwind) ownSheets(child, m[1], seen, out);
    }
    out.push(text);
    return out;
  };
  const loadModule = async (id, base) => {
    const file = createRequire(path.join(base, 'tw_probe.cjs')).resolve(id);
    const mod = await import(pathToFileURL(file).href);
    return { path: file, base: path.dirname(file), module: mod.default ?? mod };
  };

  const source = withoutInline(read(entry, args.entry));
  let compiler;
  try {
    compiler = await compile(source, { base: path.dirname(entry), from: entry, loadStylesheet, loadModule });
  } catch (err) {
    die(`Tailwind could not compile ${args.entry}: ${err.message}`);
  }

  const variables = themeVariables(ownSheets(entry, args.entry));
  const roles = [...variables.keys()].map((v) => ({ variable: v, class: roleClass(v) })).filter((r) => r.class);
  const own = new Set(roles.map((r) => r.class));
  const stock = STOCK.filter(([cls]) => !own.has(cls)).map(([cls, clear]) => ({ class: cls, clear }));

  // One compiler, the candidates added one at a time: what a step adds to a
  // class's selectors is what Tailwind generated for it, and the project's
  // own CSS (in the very first build) never counts.
  const generated = new Map();
  const wanted = [...new Set([...roles.map((r) => r.class), ...stock.map((s) => s.class),
    ...args.expect, ...args.refuse, ...args.probe])];
  let css = compiler.build([]);
  const added = [];
  for (const cls of wanted) {
    const before = selectorCount(css, cls);
    added.push(cls);
    css = compiler.build(added);
    generated.set(cls, selectorCount(css, cls) > before);
  }

  const result = {
    tailwindcss: version,
    entry: path.relative(cwd, entry).split(path.sep).join('/'),
    roles: roles.map((r) => ({ ...r, generates: generated.get(r.class) })),
    stock: stock.map((s) => ({ ...s, generates: generated.get(s.class) })),
    expect: args.expect.map((c) => ({ class: c, generates: generated.get(c) })),
    refuse: args.refuse.map((c) => ({ class: c, generates: generated.get(c) })),
    probe: args.probe.map((c) => ({ class: c, generates: generated.get(c) })),
  };
  const failures = [
    ...result.roles.filter((r) => !r.generates).map((r) => `${r.class}: ${r.variable} gives no class`),
    ...result.stock.filter((s) => s.generates)
      .map((s) => `${s.class}: Tailwind's default generates; ${s.clear} survived (add \`${s.clear}: initial\`)`),
    ...result.expect.filter((e) => !e.generates).map((e) => `${e.class}: expected, generates nothing`),
    ...result.refuse.filter((e) => e.generates).map((e) => `${e.class}: refused, but generates`),
  ];
  result.verdict = failures.length ? 'fail' : 'pass';
  result.failures = failures;

  if (args.json) {
    process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
  } else {
    const lines = [`tw_probe: tailwindcss ${version}, ${result.entry}`,
      `  roles: ${roles.length} theme variables give a class; `
        + `${result.roles.filter((r) => r.generates).length} generate`,
      `  stock: ${result.stock.filter((s) => s.generates).length} of ${stock.length} of Tailwind's defaults generate`];
    for (const p of result.probe) lines.push(`  ${p.class}: ${p.generates ? 'generates' : 'generates nothing'}`);
    for (const f of failures) lines.push(`  FAIL ${f}`);
    lines.push(`verdict: ${result.verdict}`);
    process.stdout.write(`${lines.join('\n')}\n`);
  }
  process.exit(failures.length ? 1 : 0);
}

main().catch((err) => die(err && err.stack ? err.stack : String(err)));
