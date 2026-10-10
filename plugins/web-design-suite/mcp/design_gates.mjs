/**
 * design_gates.mjs — web-design-suite's MCP server (P28, XC-B1). The plugin's
 * .mcp.json runs it as `node design_gates.mjs`, and Claude Code names its
 * tools mcp__plugin_web-design-suite_gates__<tool>:
 *
 *   audit_design  web-design-studio's design audit, the nine Laws
 *   a11y_static   a11y-audit-runner's static accessibility checks
 *   perf_audit    perf-budget-gate's build weigh-in against the budget
 *   check_roles   web-design-studio's role-pair contrast gate
 *   diff_system   design-system-versioning's diff against the published snapshot
 *
 * Each runs the skill's script in the project's folder, where the scripts find
 * its .design-suite.json, and returns the script's JSON with its exit code and
 * a verdict: pass (0), fail (1), or an error the script could not get past.
 * A report too long for Claude's context keeps the head of its longest list
 * and says how much it left out.
 *
 * MCP over stdio: JSON-RPC 2.0, one message per line, nothing else on stdout.
 * Node runs it because one name runs node on every system, as for the hooks
 * (claude-code-capabilities.md §6); it looks for Python as they do
 * (WDS_PYTHON, else python3, python and py -3).
 */

import { spawn, spawnSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import readline from 'node:readline';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const PLUGIN = path.join(HERE, '..');
const VERSION = JSON.parse(fs.readFileSync(path.join(PLUGIN, '.claude-plugin', 'plugin.json'), 'utf8')).version;
const PROTOCOLS = ['2025-06-18', '2025-03-26', '2024-11-05'];   // the newest first
// Characters of JSON a result may hold, about 15,000 tokens: Claude Code warns
// past 10,000 tokens of tool output and stops at 25,000 (MAX_MCP_OUTPUT_TOKENS).
const LIMIT = 60000;
const TIMEOUT = 600000;       // a whole site's audit, not a hung script

const paths = (what) => ({ type: 'array', items: { type: 'string' }, description: what });
const flag = (what) => ({ type: 'boolean', description: what });
const file = (what) => ({ type: 'string', description: what });
// A path the model passes never reaches a script as an option: the
// positionals follow `--`, and an option's value is joined to it with `=`.
const positional = (list) => (list.length ? ['--', ...list] : []);

const TOOLS = {
  audit_design: {
    script: 'skills/web-design-studio/scripts/audit_design.py',
    description: 'Audit stylesheets, templates and components against the design system\'s nine Laws ' +
      '(tokens, tiers, layers, scales): the findings with file, line, Law, rule, severity and the fix. ' +
      'The project\'s .design-suite.json supplies its token files, component globs and baseline.',
    properties: { paths: paths('files or folders to audit, relative to the project (default: the project)'),
                  strict: flag('fail on warnings too') },
    args: ({ paths: p = [], strict }) => ['--json', ...(strict ? ['--strict'] : []), ...positional(p)],
  },
  a11y_static: {
    script: 'skills/a11y-audit-runner/scripts/a11y_static.py',
    description: 'Run the static accessibility checks on markup, JSX and CSS: each finding with its WCAG ' +
      'success criterion, severity and fix. The machine-checkable floor, not an accessibility result.',
    properties: { paths: paths('files or folders to check, relative to the project (default: the project)'),
                  strict: flag('fail on warnings too') },
    args: ({ paths: p = [], strict }) => ['--json', ...(strict ? ['--strict'] : []), ...positional(p)],
  },
  perf_audit: {
    script: 'skills/perf-budget-gate/scripts/perf_audit.py',
    description: 'Weigh a built site against its performance budget: bundle and asset sizes, render-blocking ' +
      'resources and the LCP and CLS risks a build can show, with the fix for each.',
    properties: { paths: paths('the build output to weigh, relative to the project (default: the project)'),
                  src: paths('source folders, for the checks that read the source'),
                  budget: file('the budget file (default: the project\'s budgets.perf)'),
                  strict: flag('fail on warnings too') },
    args: ({ paths: p = [], src = [], budget, strict }) => ['--json', ...(strict ? ['--strict'] : []),
      ...src.map((s) => `--src=${s}`), ...(budget ? [`--budget=${budget}`] : []), ...positional(p)],
  },
  check_roles: {
    script: 'skills/web-design-studio/scripts/check_roles.py',
    description: 'Resolve a tokens.css\'s Tier-2 roles in every theme and measure the contrast of each ' +
      'pair components use against its WCAG floor.',
    properties: { tokens: file('the tokens.css, relative to the project'),
                  pairs: file('a JSON list of pairs, replacing the built-in one') },
    required: ['tokens'],
    args: ({ tokens, pairs }) => ['--json', ...(pairs ? [`--pairs=${pairs}`] : []), ...positional([tokens])],
  },
  diff_system: {
    script: 'skills/design-system-versioning/scripts/diff_system.py',
    description: 'Compare the design system with its published snapshot: each change with its severity, ' +
      'the release it makes (major, minor or patch) and the contrast pairs that crossed a WCAG floor.',
    properties: { old: file('the published snapshot (default: the project\'s baselines.system)'),
                  new: file('the system now (default: the project\'s token files); needs old') },
    args: ({ old, new: now }) => ['--format=json', '--gate=none', ...positional([old, now].filter(Boolean))],
  },
};

// --- Python ----------------------------------------------------------------

let python;
// The first Python 3: WDS_PYTHON, else the names the platform uses, each
// asked for its major version (Windows' python3 is often the Store's
// placeholder, which runs nothing). Found once, on the first call.
function findPython() {
  if (python !== undefined) return python;
  const named = process.env.WDS_PYTHON;
  const candidates = named ? [[named]]
    : process.platform === 'win32' ? [['python'], ['py', '-3'], ['python3']] : [['python3'], ['python']];
  python = candidates.find(([exe, ...args]) => {
    const probe = spawnSync(exe, [...args, '-c', 'import sys; print(sys.version_info[0])'],
                            { encoding: 'utf8', timeout: 15000, windowsHide: true });
    return probe.status === 0 && probe.stdout.trim() === '3';
  }) ?? null;
  return python;
}

// The folder the scripts run in: the project Claude Code opened.
const project = () => process.env.CLAUDE_PROJECT_DIR || process.cwd();

function run(exe, args, cwd) {
  return new Promise((resolve) => {
    const child = spawn(exe[0], [...exe.slice(1), ...args], { cwd, windowsHide: true });
    const out = [];
    const err = [];
    const timer = setTimeout(() => child.kill(), TIMEOUT);
    child.stdout.on('data', (d) => out.push(d));
    child.stderr.on('data', (d) => err.push(d));
    child.on('error', (e) => { clearTimeout(timer); resolve({ error: e.message }); });
    child.on('close', (status) => {
      clearTimeout(timer);
      resolve({ status, stdout: Buffer.concat(out).toString('utf8'), stderr: Buffer.concat(err).toString('utf8') });
    });
  });
}

// A payload whose JSON fits LIMIT: the longest list in the report keeps its head.
function fit(payload) {
  if (JSON.stringify(payload).length <= LIMIT) return payload;
  const { report } = payload;
  const lists = Array.isArray(report) ? [[null, report]]
    : Object.entries(report ?? {}).filter(([, v]) => Array.isArray(v));
  if (!lists.length) return payload;
  const [key, list] = lists.reduce((a, b) => (JSON.stringify(b[1]).length > JSON.stringify(a[1]).length ? b : a));
  const cut = (n) => {
    const head = list.slice(0, n);
    return { ...payload, report: key === null ? head : { ...report, [key]: head },
             truncated: { list: key ?? 'the report', shown: n, total: list.length,
                          rest: `run ${path.basename(TOOLS[payload.tool].script)} for the whole report` } };
  };
  let lo = 0;
  let hi = list.length;
  while (lo < hi) {                         // the most items that fit
    const mid = Math.ceil((lo + hi) / 2);
    if (JSON.stringify(cut(mid)).length <= LIMIT) lo = mid; else hi = mid - 1;
  }
  return cut(lo);
}

async function call(name, args) {
  const tool = TOOLS[name];
  const exe = findPython();
  const text = (t, isError) => ({ content: [{ type: 'text', text: t }], isError });
  if (!exe) return text(`${name}: the gates need Python 3 (WDS_PYTHON, python3, python or py -3), and none was found.`, true);
  const proc = await run([...exe, '-B', path.join(PLUGIN, tool.script)], tool.args(args), project());
  if (proc.error) return text(`${name} could not run: ${proc.error}`, true);
  let report;
  try {
    report = JSON.parse(proc.stdout);
  } catch {
    return text(`${name} stopped (exit ${proc.status}): ${proc.stderr.trim().slice(0, 2000)}`, true);
  }
  if (proc.status !== 0 && proc.status !== 1) {
    return text(`${name} stopped (exit ${proc.status}): ${proc.stderr.trim().slice(0, 2000)}`, true);
  }
  const verdict = proc.status === 0 ? 'pass' : 'fail';
  return text(JSON.stringify(fit({ tool: name, exit: proc.status, verdict, report })), false);
}

// --- JSON-RPC --------------------------------------------------------------

class RpcError extends Error {
  constructor(code, message) {
    super(message);
    this.code = code;
  }
}

// The arguments a tool takes, checked against its schema: only its names, of
// their types, a path never empty.
function checked(name, args) {
  const tool = TOOLS[name];
  const given = args ?? {};
  if (typeof given !== 'object' || Array.isArray(given)) throw new RpcError(-32602, `${name}: arguments must be an object`);
  for (const [key, value] of Object.entries(given)) {
    const want = tool.properties[key];
    if (!want) throw new RpcError(-32602, `${name}: unknown argument '${key}'; it takes ${Object.keys(tool.properties).join(', ')}`);
    const ok = want.type === 'boolean' ? typeof value === 'boolean'
      : want.type === 'string' ? typeof value === 'string' && value.trim() !== ''
        : Array.isArray(value) && value.every((v) => typeof v === 'string' && v.trim() !== '');
    if (!ok) throw new RpcError(-32602, `${name}: '${key}' must be ${want.type === 'array' ? 'a list of paths' : want.type === 'string' ? 'a path' : 'true or false'}`);
  }
  for (const key of tool.required ?? []) {
    if (!(key in given)) throw new RpcError(-32602, `${name}: '${key}' is required`);
  }
  if (name === 'diff_system' && given.new && !given.old) throw new RpcError(-32602, 'diff_system: \'new\' needs \'old\'');
  return given;
}

const listing = () => Object.entries(TOOLS).map(([name, t]) => ({
  name,
  description: t.description,
  inputSchema: { type: 'object', properties: t.properties, ...(t.required ? { required: t.required } : {}),
                 additionalProperties: false },
  annotations: { readOnlyHint: true, openWorldHint: false },
}));

const METHODS = {
  initialize: (params) => ({
    protocolVersion: PROTOCOLS.includes(params?.protocolVersion) ? params.protocolVersion : PROTOCOLS[0],
    capabilities: { tools: { listChanged: false } },
    serverInfo: { name: 'web-design-suite-gates', version: VERSION },
    instructions: 'The design, accessibility, performance and contrast gates, and the token diff, as tools. ' +
      'Each runs in the project\'s folder and reads its .design-suite.json.',
  }),
  ping: () => ({}),
  'tools/list': () => ({ tools: listing() }),
  'tools/call': (params) => {
    const name = params?.name;
    if (!Object.prototype.hasOwnProperty.call(TOOLS, name)) {
      throw new RpcError(-32602, `unknown tool '${name}'; the tools are ${Object.keys(TOOLS).join(', ')}`);
    }
    return call(name, checked(name, params.arguments));
  },
};

const send = (message) => process.stdout.write(`${JSON.stringify({ jsonrpc: '2.0', ...message })}\n`);

async function handle(line) {
  if (!line.trim()) return;
  let msg;
  try {
    msg = JSON.parse(line);
  } catch {
    return send({ id: null, error: { code: -32700, message: 'not JSON' } });
  }
  if (msg === null || typeof msg !== 'object' || Array.isArray(msg) || typeof msg.method !== 'string') {
    if (msg && typeof msg === 'object' && 'id' in msg && !('method' in msg)) return;   // a reply to nothing we asked
    return send({ id: msg?.id ?? null, error: { code: -32600, message: 'not a JSON-RPC request' } });
  }
  const isRequest = 'id' in msg;
  const method = Object.prototype.hasOwnProperty.call(METHODS, msg.method) ? METHODS[msg.method] : null;
  if (!isRequest) return;                  // notifications/initialized, cancelled: nothing to answer
  if (!method) return send({ id: msg.id, error: { code: -32601, message: `no method '${msg.method}'` } });
  try {
    send({ id: msg.id, result: await method(msg.params) });
  } catch (err) {
    send({ id: msg.id, error: { code: err.code ?? -32603, message: err.message } });
  }
}

const lines = readline.createInterface({ input: process.stdin, crlfDelay: Infinity });
lines.on('line', (line) => { handle(line); });
