"""web-design-suite: the documented recipes run as written (phase 2, item 10).

Each test takes the commands, configs or code out of the docs themselves, so a
recipe cannot be fixed in one place and left broken in its copy elsewhere.

Regressions covered:
- LC-A18: the drift gate's baseline was written to `system.json` and read
  from `docs/system.json`. build_docs said "no baseline, checking prose only"
  and passed, so the gate compared nothing. Under that, CI extracted
  `styles/ src/` while the baseline read `styles/ src/components/`, so fixing
  the path alone made an unchanged repo report drift for any page stylesheet
  that declares sockets.
- GT-A11: the docs write perf-budget.json with comments ("the device and
  network in a comment"; budgets.md §6 is JSONC) and both readers accepted
  strict JSON only, exiting 2. measure_vitals read the budget after every
  run, so a typo in it cost the whole measurement.
- GT-A15: the CI workflows ran on Node 20 actions, which GitHub removed on
  2026-09-23. They never waited for the server they started. The a11y job
  never installed Playwright, so its runtime layer exited 2. The perf job's
  readable second run (`--runs 0 ... || true`) always failed and was
  swallowed, and its PR comment used an undefined `$PR` with no token. All
  of them ran on whatever Chrome the runner image carried, although the docs
  say to pin the browser. Their bash went to PowerShell on Windows runners.
- SB-A17: the stylelint install line (`stylelint@^16` with an unpinned
  stylelint-config-standard, now 40.x) stopped npm with ERESOLVE. The ESLint
  line named ESLint 9, past end of life. The Tailwind plugin notes described
  a 3.x plugin that no longer exists as `latest`, and called
  `no-arbitrary-value` an !important check.
- SB-A20: navigation-patterns.md's code. The safe triangle deferred a switch
  by one 60 ms timeout and then made it anyway, so crossing another trigger on
  the way into a panel swapped the panel out. Clicking a trigger that hover
  had opened closed its panel. The drawer's light dismiss (`e.target ===
  drawer`) also fired on clicks in the drawer's own padding. The scroll-spy
  read `--nav-offset` with parseFloat, which gives NaN for its calc() text,
  so it always used 64 px. And the Popover rows told readers to set
  `aria-expanded` by hand, which the browser already exposes.
- SS-A12: the `@property` recipe used `initial-value: 1.5rem`. That is not
  computationally independent, so browsers drop the rule. The socket it made
  non-inheriting (--card-inset) is one that `.card__media` reads from the
  card root.
"""
from __future__ import annotations

import importlib.util
import json
import os
import pathlib
import re
import shlex
import shutil
import subprocess
import sys
import unittest

from test_browser_scripts import STUB_PLAYWRIGHT
from wds_support import NODE, SKILLS, TempDirTest, env, output, run_node, run_py, tailwind_part5, tool_modules

SHELL_BREAK = {"&&", "||", "|", ";", ">", ">>", "2>&1", "&"}


def command_lines(text: str):
    """(line, command) for every shell command the markdown shows: each line
    of a fenced block (continuations joined, a YAML `run:` prefix dropped) and
    each `> python ...` quick-start line outside a fence."""
    found, fenced, buf, start = [], False, "", 0
    for n, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if line.startswith("```"):
            fenced, buf = not fenced, ""
            continue
        if not fenced:
            m = re.match(r">\s*(python3?\s.*)", line)
            if m:
                found.append((n, m.group(1)))
            continue
        line = re.sub(r"^(- )?run:\s*", "", line)
        if not buf and (not line or line == "|" or line.startswith("#")):
            continue
        if not buf:
            start = n
        line = re.sub(r"\s+#\s.*$", "", line)
        if line.endswith("\\"):
            buf += line[:-1] + " "
            continue
        found.append((start, buf + line))
        buf = ""
    return found


def documented(script: str):
    """(where, argv) for every documented invocation of a shipped script,
    across every skill: the arguments after the script, up to any shell
    operator."""
    calls = []
    for md in sorted(SKILLS.glob("*/SKILL.md")) + sorted(SKILLS.glob("*/references/*.md")):
        for n, cmd in command_lines(md.read_text(encoding="utf-8")):
            if script not in cmd:
                continue
            try:
                tokens = shlex.split(cmd)
            except ValueError:
                continue
            for i, tok in enumerate(tokens):
                if tok == f"scripts.{script}" or re.search(rf"(^|/){script}\.py$", tok):
                    args = []
                    for t in tokens[i + 1:]:
                        if t in SHELL_BREAK:
                            break
                        args.append(t)
                    calls.append((f"{md.relative_to(SKILLS).as_posix()}:{n}", args))
                    break
    return calls


def load_parser(skill: str, script: str):
    """The script's own argparse parser, so a recipe is read the way the
    script reads it."""
    name = f"wds_recipes_{skill.replace('-', '_')}_{script}"
    spec = importlib.util.spec_from_file_location(name, SKILLS / skill / "scripts" / f"{script}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod.build_parser()


def parse(parser, where, argv):
    try:
        ns, extra = parser.parse_known_args(argv)
    except SystemExit:
        raise AssertionError(f"{where}: the script's parser rejects {argv}")
    if extra:
        raise AssertionError(f"{where}: unknown arguments {extra}")
    return ns


# ---------------------------------------------------------------------------
# LC-A18 -- one baseline, one set of inputs
# ---------------------------------------------------------------------------

def source_of(ns) -> tuple:
    """What an extraction reads. Two runs that read the same source must
    produce the same system.json, or the drift gate reports noise."""
    return (tuple(ns.paths), tuple(ns.tokens), tuple(ns.components), tuple(ns.props),
            ns.root, ns.root_font_size)


class DriftGateRecipe(TempDirTest):

    @classmethod
    def setUpClass(cls):
        ex = load_parser("design-system-docs", "extract_system")
        bd = load_parser("design-system-docs", "build_docs")
        cls.extractions = [(w, parse(ex, w, a)) for w, a in documented("extract_system")]
        cls.checks = [(w, ns) for w, ns in
                      ((w, parse(bd, w, a)) for w, a in documented("build_docs")) if ns.check]

    def writer(self, path: str):
        """The documented extraction whose output is `path`."""
        writers = [(w, ns) for w, ns in self.extractions if ns.out == path]
        return writers[0] if writers else (None, None)

    def test_every_documented_extraction_reads_the_same_source(self):
        # The one exception is the explicit --tokens/--components form, shown
        # for when auto-detection guesses wrong; it is not a baseline.
        sources = {}
        for where, ns in self.extractions:
            if ns.paths:
                sources.setdefault(source_of(ns), []).append(where)
        self.assertEqual(len(sources), 1,
                         "the baseline and the CI run must read the same source:\n"
                         + "\n".join(f"  {k[0]}: {v}" for k, v in sources.items()))

    def test_every_drift_check_reads_a_baseline_the_docs_write(self):
        self.assertGreaterEqual(len(self.checks), 3)
        for where, ns in self.checks:
            with self.subTest(check=where):
                self.assertTrue(ns.baseline, f"{where}: a drift check with no baseline "
                                             "checks prose only")
                base_at, base = self.writer(ns.baseline)
                self.assertIsNotNone(base, f"{where} reads {ns.baseline}, which no "
                                           "documented command writes")
                fresh_at, fresh = self.writer(ns.system)
                self.assertIsNotNone(fresh, f"{where} checks {ns.system}, which no "
                                            "documented command writes")
                self.assertEqual(source_of(base), source_of(fresh),
                                 f"{base_at} and {fresh_at} read different source")

    def test_an_unchanged_repo_reports_no_drift(self):
        """The SKILL.md workflow, run as written on a repo where nothing
        changed between the baseline and CI."""
        self.write("styles/tokens.css", ":root {\n  --space-4: 1rem;\n  --bg-surface: #ffffff;\n}\n")
        self.write("src/components/card.css",
                   ".card {\n  --card-bg: var(--bg-surface);\n  --card-inset: var(--space-4);\n"
                   "  background: var(--card-bg);\n  padding: var(--card-inset);\n}\n")
        # A page stylesheet with its own socket block, as real apps have.
        self.write("src/pages/home.css",
                   ".home {\n  --home-gap: var(--space-4);\n  gap: var(--home-gap);\n}\n")
        self.write("docs/prose/components/card.md", "# Card\n\nThe surface for one idea.\n")
        check_at, check = next((w, ns) for w, ns in self.checks
                               if w.startswith("design-system-docs/SKILL.md"))
        base_at, base = self.writer(check.baseline)
        fresh_at, fresh = self.writer(check.system)
        self.assertIsNotNone(base, f"{check_at}: no documented command writes {check.baseline}")
        self.assertIsNotNone(fresh, f"{check_at}: no documented command writes {check.system}")
        argv = dict(documented("extract_system"))
        for where in (base_at, fresh_at):
            proc = run_py("design-system-docs", "extract_system", *argv[where], cwd=self.tmp)
            self.assertEqual(proc.returncode, 0, f"{where}\n{output(proc)}")
        proc = run_py("design-system-docs", "build_docs", *dict(documented("build_docs"))[check_at],
                      cwd=self.tmp)
        self.assertEqual(proc.returncode, 0, f"{check_at}\n{output(proc)}")
        self.assertIn("No drift", output(proc))
        self.assertNotIn("no baseline", output(proc))

    def test_a_named_baseline_that_is_missing_fails_the_gate(self):
        self.write("styles/tokens.css", ":root {\n  --space-4: 1rem;\n}\n")
        proc = run_py("design-system-docs", "extract_system", "styles/", "--out",
                      "build/system.json", cwd=self.tmp)
        self.assertEqual(proc.returncode, 0, output(proc))
        proc = run_py("design-system-docs", "build_docs", "build/system.json", "--baseline",
                      "docs/system.json", "--check", cwd=self.tmp)
        self.assertEqual(proc.returncode, 2, output(proc))
        self.assertIn("docs/system.json", output(proc))


# ---------------------------------------------------------------------------
# GT-A11 -- the budget file the docs show, comments and all
# ---------------------------------------------------------------------------

def budget_example() -> str:
    """The perf-budget.json that references/budgets.md §6 shows."""
    text = (SKILLS / "perf-budget-gate" / "references" / "budgets.md").read_text(encoding="utf-8")
    section = text.split("## 6. The budget file", 1)[1]
    return re.search(r"```jsonc?\n(.*?)```", section, re.S).group(1)


TRICKY_JSONC = """\ufeff{
  "$schema": "perf-budget-gate/1", /* block */
  "first_party_origins": ["https://cdn.acme.com", "say \\"/* hi */\\""],  // URL keeps its //
  "pages": { "dashboard/*": { "lab": { "lcp_ms": 3000, } }, },
  // a comment between the trailing comma and its bracket
}
"""


def playwright_modules():
    return tool_modules("WDS_NODE_MODULES", "playwright", node_path=True)


class PerfBudgetFile(TempDirTest):

    def setUp(self):
        super().setUp()
        self.page = self.write("dist/index.html", "<!doctype html><html lang=\"en\"><title>t</title>"
                                                  "<main><h1>Hi</h1></main></html>\n")
        # The docs ask for the device and network "in a comment".
        self.example = "// Moto G Power on Slow 4G, per budgets.md §1\n" + budget_example()

    def test_the_static_audit_reads_the_documented_budget(self):
        for encoding in ("utf-8", "utf-16"):                # utf-16: PowerShell's `>`
            with self.subTest(encoding=encoding):
                self.write("perf-budget.json", self.example.encode(encoding))
                proc = run_py("perf-budget-gate", "perf_audit", "dist/", "--budget",
                              "perf-budget.json", cwd=self.tmp)
                self.assertIn(proc.returncode, (0, 1), output(proc))
                self.assertNotIn("cannot read budget", output(proc))

    def stub_run(self, budget):
        self.write("node_modules/playwright/index.mjs", STUB_PLAYWRIGHT)
        self.write("perf-budget.json", budget)
        return run_node("perf-budget-gate", "measure_vitals.mjs", self.page, "--budget",
                        "perf-budget.json", cwd=self.tmp,
                        env_changes={"NODE_PATH": str(self.tmp / "node_modules"),
                                     "PERF_CHROMIUM": None, "STUB_FAIL_LAUNCH": None})

    @unittest.skipUnless(NODE, "node is not installed")
    def test_the_lab_budget_is_read_before_any_browser_starts(self):
        """measure_vitals measured every run first and only then found the
        budget unreadable, so a typo cost the whole run."""
        proc = self.stub_run('{ "defaults": { "lab": { "lcp_ms": 2500 } ')
        self.assertEqual(proc.returncode, 2, output(proc))
        self.assertIn("cannot parse", output(proc))
        self.assertNotIn("STUB-LAUNCH", output(proc))

    @unittest.skipUnless(NODE, "node is not installed")
    def test_the_documented_budget_parses_before_the_browser_starts(self):
        for budget in (self.example, TRICKY_JSONC):
            with self.subTest(budget=budget[:40]):
                proc = self.stub_run(budget)
                self.assertEqual(proc.returncode, 42, output(proc))   # the stub browser launched
                self.assertNotIn("cannot parse", output(proc))

    def test_comments_are_dropped_and_strings_are_kept(self):
        name = "wds_recipes_perf_audit"
        spec = importlib.util.spec_from_file_location(
            name, SKILLS / "perf-budget-gate" / "scripts" / "perf_audit.py")
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
        self.assertEqual(mod.read_jsonc(TRICKY_JSONC.encode("utf-8")), {
            "$schema": "perf-budget-gate/1",
            "first_party_origins": ["https://cdn.acme.com", 'say "/* hi */"'],
            "pages": {"dashboard/*": {"lab": {"lcp_ms": 3000}}}})

    @unittest.skipUnless(NODE and playwright_modules(), "needs node plus WDS_NODE_MODULES "
                                                         "pointing at playwright")
    def test_a_measured_run_applies_the_documented_budget(self):
        self.write("perf-budget.json", self.example)
        proc = run_node("perf-budget-gate", "measure_vitals.mjs", self.page, "--runs", "1",
                        "--budget", "perf-budget.json", cwd=self.tmp, timeout=240,
                        env_changes={"NODE_PATH": playwright_modules()})
        if proc.returncode == 2 and "no usable chromium" in output(proc):
            self.skipTest(output(proc))
        self.assertIn(proc.returncode, (0, 1), output(proc))
        self.assertNotIn("cannot parse", output(proc))
        self.assertRegex(output(proc), r"Budget|breach")


# ---------------------------------------------------------------------------
# GT-A15 -- the CI workflows the docs ship
# ---------------------------------------------------------------------------

# The first major of each action that runs on Node 24, read from each tag's
# action.yml on 2026-09-25 (upload-artifact@v5 still says node20). GitHub
# removed Node 20 from its runners on 2026-09-23 (github.blog changelog,
# 2025-09-19).
NODE24 = {"actions/checkout": 5, "actions/setup-node": 5, "actions/setup-python": 6,
          "actions/cache": 5, "actions/upload-artifact": 6}
PLAYWRIGHT_SCRIPTS = ("a11y_runtime.mjs", "measure_vitals.mjs", "snapshot_matrix.mjs")


def doc_texts():
    for md in sorted(SKILLS.glob("*/SKILL.md")) + sorted(SKILLS.glob("*/references/*.md")):
        yield md.relative_to(SKILLS).as_posix(), md.read_text(encoding="utf-8")


def workflows():
    """(where, text) for every GitHub Actions workflow the docs show."""
    found = []
    for where, text in doc_texts():
        for m in re.finditer(r"^```ya?ml\n(.*?)^```", text, re.S | re.M):
            if re.search(r"^\s*jobs:", m.group(1), re.M):
                found.append((f"{where}:{text.count(chr(10), 0, m.start()) + 1}", m.group(1)))
    return found


def run_blocks(workflow: str):
    """The shell script of every `run:` step."""
    blocks, lines = [], workflow.splitlines()
    for i, line in enumerate(lines):
        m = re.match(r"^(\s*)(?:- )?run:\s*(.*)$", line)
        if not m or not m.group(2):
            continue                                        # `defaults: run:` is a mapping
        if m.group(2) not in ("|", "|-", ">", ">-"):
            blocks.append(m.group(2))
            continue
        indent, body = None, []
        for nxt in lines[i + 1:]:
            if not nxt.strip():
                body.append("")
                continue
            depth = len(nxt) - len(nxt.lstrip())
            if indent is None:
                if depth <= len(m.group(1)):
                    break
                indent = depth
            if depth < indent:
                break
            body.append(nxt[indent:])
        blocks.append("\n".join(body).strip())
    return blocks


class CiRecipes(unittest.TestCase):
    """GT-A15: the workflows, read the way a runner reads them."""

    @classmethod
    def setUpClass(cls):
        cls.flows = workflows()

    def test_the_docs_ship_workflows(self):
        self.assertGreaterEqual(len(self.flows), 4, [w for w, _ in self.flows])

    def test_every_action_runs_on_node_24(self):
        for where, text in doc_texts():                     # partial snippets too
            for name, major in re.findall(r"uses:\s*(actions/[\w-]+)@v(\d+)", text):
                with self.subTest(where=where, action=name):
                    self.assertIn(name, NODE24, "read its action.yml and add it to NODE24")
                    self.assertGreaterEqual(int(major), NODE24[name])

    def test_every_workflow_runs_its_steps_in_bash(self):
        """The steps use `\\` continuations, `||`, `${VAR:-0}` and `&`, and a
        Windows runner's default shell is PowerShell."""
        for where, flow in self.flows:
            with self.subTest(where=where):
                self.assertRegex(flow, r"defaults:\s*\n\s+run:\s*\n\s+shell:\s*bash\b")

    def test_a_server_is_waited_for_in_the_step_that_uses_it(self):
        started = 0
        for where, flow in self.flows:
            for block in run_blocks(flow):
                lines = block.splitlines()
                for i, line in enumerate(lines):
                    if not re.search(r"(?<!&)&\s*$", line):
                        continue
                    started += 1
                    rest = "\n".join(lines[i + 1:])
                    with self.subTest(where=where, line=line.strip()):
                        self.assertIn("wait-on", rest, "a server started in the background "
                                                       "is waited for in the same step")
                        self.assertRegex(rest, r"127\.0\.0\.1|localhost", "and used there")
        self.assertGreaterEqual(started, 2)

    def test_no_failure_is_swallowed(self):
        for where, flow in self.flows:
            with self.subTest(where=where):
                self.assertNotRegex(flow, r"\|\|\s*true\b")
                self.assertNotIn("continue-on-error: true", flow)
                self.assertNotRegex(flow, r"--runs\s+0\b")        # "must be at least 1"

    def test_a_browser_script_runs_on_the_pinned_browser(self):
        for where, flow in self.flows:
            if not any(s in flow for s in PLAYWRIGHT_SCRIPTS):
                continue
            with self.subTest(where=where):
                self.assertIn("npx playwright install", flow,
                              "install the Chromium the locked Playwright was built for; "
                              "the runner image's Chrome changes with every image")
                self.assertNotIn("PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD", flow)
                self.assertNotRegex("\n".join(run_blocks(flow)), r"\bnpm (i|install|add)\b",
                                    "CI installs from the lockfile (npm ci), never ad hoc")
                if re.search(r"a11y_runtime\.mjs|measure_vitals\.mjs", flow):
                    # snapshot_matrix writes its report with --out DIR instead.
                    self.assertRegex(flow, r"--report\s", "the log shows a report a person reads")

    def test_no_doc_says_the_runner_image_browser_is_the_pinned_one(self):
        for where, text in doc_texts():
            with self.subTest(doc=where):
                self.assertNotRegex(text, r"(?i)never download one here|browser is already in "
                                          r"the image|the image already has one")

    def test_every_tool_a_workflow_runs_is_set_up(self):
        for where, flow in self.flows:
            steps = "\n".join(run_blocks(flow))
            with self.subTest(where=where):
                if re.search(r"\bpython3?\b", steps):
                    self.assertIn("actions/setup-python", flow)
                if re.search(r"\b(node|npm|npx)\b", steps):
                    self.assertIn("actions/setup-node", flow)

    def test_a_pr_comment_has_a_number_a_token_and_permission(self):
        seen = 0
        for where, text in doc_texts():
            if "gh pr comment" not in text:
                continue
            seen += 1
            with self.subTest(doc=where):
                self.assertRegex(text, r"PR:\s*\$\{\{\s*github\.event\.pull_request\.number\s*\}\}")
                self.assertRegex(text, r"GH_TOKEN:\s*\$\{\{\s*(github\.token|secrets\.GITHUB_TOKEN)")
                self.assertIn("pull-requests: write", text)
        self.assertTrue(seen)

    def test_every_run_step_is_valid_bash(self):
        bash = shutil.which("bash")
        if not bash or "system32" in bash.lower():          # WSL's launcher is not a bash
            self.skipTest("no bash on PATH")
        for where, flow in self.flows:
            for block in run_blocks(flow):
                script = re.sub(r"\$\{\{[^}]*\}\}", "X", block)   # GitHub expressions
                with self.subTest(where=where, step=block[:60]):
                    proc = subprocess.run([bash, "-n"], input=script.encode("utf-8"),
                                          capture_output=True, timeout=60, env=env())
                    self.assertEqual(proc.returncode, 0, output(proc))


# ---------------------------------------------------------------------------
# SB-A17 -- the configs' install lines, against the registry
# ---------------------------------------------------------------------------

# Read from registry.npmjs.org, eslint.org/version-support and the 4.4.0
# README on 2026-09-25:
#   stylelint 17.15.0; stylelint-config-standard 40.0.0 peers stylelint ^17.0.0
#   eslint 10.11.0; ESLint 9 reached end of life on 2026-08-06
#   eslint-plugin-jsx-a11y 6.10.2 peers eslint "^3 || ... || ^9"
#   eslint-plugin-tailwindcss 4.4.0 is "Made for Tailwind CSS v4" (peer
#   tailwindcss ^4); v3 projects stay on 3.x
CONFIG_DIR = SKILLS / "web-design-studio" / "assets" / "configs"
TAILWIND_PLUGIN_RULES = {
    4: {"classnames-order", "enforces-canonical-classname", "enforces-negative-arbitrary-values",
        "enforces-shorthand", "important-modifier-suffix", "no-arbitrary-value",
        "no-contradicting-classname", "no-custom-classname", "no-unnecessary-arbitrary-value"},
    3: {"classnames-order", "enforces-negative-arbitrary-values", "enforces-shorthand",
        "migration-from-tailwind-2", "no-arbitrary-value", "no-custom-classname",
        "no-contradicting-classname", "no-unnecessary-arbitrary-value"},
}


def major(text: str, package: str):
    m = re.search(rf"(?<![\w-]){re.escape(package)}@\^?(\d+)", text)
    return int(m.group(1)) if m else None


class DependencyFacts(unittest.TestCase):

    def header(self, name):
        return (CONFIG_DIR / name).read_text(encoding="utf-8").split("*/", 1)[0]

    def test_stylelint_is_the_major_its_standard_config_needs(self):
        head = self.header("stylelint.config.mjs")
        self.assertEqual(major(head, "stylelint"), 17,
                         "stylelint-config-standard 40 needs stylelint ^17: npm stops with ERESOLVE")
        self.assertEqual(major(head, "stylelint-config-standard"), 40)

    def test_eslint_is_a_supported_major_and_jsx_a11y_is_let_onto_it(self):
        head = self.header("eslint.design.config.mjs")
        self.assertGreaterEqual(major(head, "eslint") or 0, 10,
                                "ESLint 9 reached end of life on 2026-08-06")
        # jsx-a11y 6.10.2's peer range stops at ^9.
        self.assertRegex(head, r'"overrides":\s*\{\s*"eslint-plugin-jsx-a11y":\s*'
                               r'\{\s*"eslint":\s*"\$eslint"\s*\}')

    def test_each_tailwind_plugin_block_fits_its_major(self):
        text = (CONFIG_DIR / "eslint.design.config.mjs").read_text(encoding="utf-8")
        part5 = text.split("PART 5", 1)[1].split("EXPORTS", 1)[0]
        _, found = tailwind_part5(text)
        self.assertEqual(sorted(found), [3, 4], "one block per plugin major")
        self.assertIn("cssConfigPath", found[4], "4.x reads the v4 CSS entry")
        self.assertNotRegex(found[4], r"\b(config|callees):", "v3 settings; 4.x ignores them")
        self.assertRegex(part5, r"eslint-plugin-tailwindcss@3\b", "a v3 project pins 3.x")
        for plugin_major, block in found.items():
            for rule in re.findall(r"'tailwindcss/([\w-]+)'", block):
                with self.subTest(major=plugin_major, rule=rule):
                    self.assertIn(rule, TAILWIND_PLUGIN_RULES[plugin_major])
        lines = part5.splitlines()
        for i, line in enumerate(lines):
            if "tailwindcss/no-arbitrary-value" in line:
                self.assertNotIn("!important", lines[i - 1], "the rule is about arbitrary values")


# ---------------------------------------------------------------------------
# SB-A20 -- navigation-patterns.md's reference code, run in Chromium
# ---------------------------------------------------------------------------

NAV = SKILLS / "web-design-studio" / "references" / "navigation-patterns.md"
NAV_CODE = SKILLS / "web-design-studio" / "references" / "navigation-code.md"
STARTER = SKILLS / "web-design-studio" / "assets" / "starter" / "styles"


def section_code(heading: str, doc: pathlib.Path = NAV) -> dict[str, list[str]]:
    """The fenced blocks under `heading`, up to the next heading, by language."""
    text = doc.read_text(encoding="utf-8")
    start = text.index(heading)
    end = re.compile(r"^#{2,3} ", re.M).search(text, start + len(heading))
    blocks: dict[str, list[str]] = {}
    for lang, code in re.findall(r"^```(\w+)\n(.*?)^```", text[start:end.start() if end else None],
                                 re.S | re.M):
        blocks.setdefault(lang, []).append(code)
    return blocks


def page_with(css: str, body: str, script: str = "") -> str:
    links = "".join(f'<link rel="stylesheet" href="{(STARTER / f).as_uri()}">'
                    for f in ("reset.css", "tokens.css", "base.css"))
    return (f"<!doctype html><html lang=\"en\"><head><title>t</title><style>@layer reset, "
            f"tokens, base, layout, components;</style>{links}<style>{css}</style></head>"
            f"<body>{body}<script>{script}</script></body></html>")


MEGAMENU_BODY = """
<nav class="nav" aria-label="Main"><ul class="nav__list" data-megamenu>
  <li class="nav__item">
    <button type="button" class="nav__trigger" id="trigger-a" aria-expanded="false"
            aria-controls="panel-a">Apparel</button>
    <div class="megamenu" id="panel-a" aria-labelledby="trigger-a" hidden>
      <div class="megamenu__col"><ul class="megamenu__list"><li><a class="megamenu__link" href="#a1">Coats</a></li></ul></div></div></li>
  <li class="nav__item">
    <button type="button" class="nav__trigger" id="trigger-b" aria-expanded="false"
            aria-controls="panel-b">Shoes</button>
    <div class="megamenu" id="panel-b" aria-labelledby="trigger-b" hidden>
      <div class="megamenu__col"><ul class="megamenu__list"><li><a class="megamenu__link" href="#b1">Trail</a></li></ul></div></div></li>
</ul></nav>"""
# Layout the reference leaves to the page: a positioned bar with room above it.
MEGAMENU_FRAME = (".nav { position: relative; margin-block-start: 120px; }"
                  ".nav__list { display: flex; list-style: none; margin: 0; padding: 0; }"
                  ".nav__trigger { inline-size: 120px; block-size: 44px; }")

MEGAMENU_SCENARIO = r"""
const page = await browser.newPage({ viewport: { width: 1000, height: 700 } });
// The page's timers run on a fake clock that only the scenario advances, so
// the hover-intent delays see the planned timing on a slow runner too.
await page.clock.install();
await page.goto(pathToFileURL(process.argv[2]).href);
const expanded = async (id) => (await page.getAttribute('#' + id, 'aria-expanded')) === 'true';
// The clock does not decide when Chromium delivers a move: on a loaded runner
// one could land after runFor() fired the hover-intent look, which then saw a
// still pointer and switched menus (CI, macOS). Each step waits, in real time,
// until the page has seen its move.
const seen = async (x, y) => {
  for (let n = 0; n < 200; n++) {
    const at = await page.evaluate(() => window.lastMove);
    if (at && Math.abs(at.x - x) < 1 && Math.abs(at.y - y) < 1) return;
    await new Promise((done) => setTimeout(done, 5));
  }
  throw new Error(`the page never saw the move to ${x}, ${y}`);
};
const glide = async (from, to, steps, ms) => {
  for (let i = 1; i <= steps; i++) {
    const x = from.x + (to.x - from.x) * i / steps, y = from.y + (to.y - from.y) * i / steps;
    await page.mouse.move(x, y);
    await seen(x, y);
    await page.clock.runFor(ms);
  }
};
await page.evaluate(() => {
  window.aOpened = 0;
  addEventListener('pointermove', (e) => { window.lastMove = { x: e.clientX, y: e.clientY }; }, true);
  const a = document.getElementById('trigger-a');
  new MutationObserver(() => { if (a.getAttribute('aria-expanded') === 'true') window.aOpened++; })
    .observe(a, { attributes: true });
});
const a = await page.locator('#trigger-a').boundingBox();
const b = await page.locator('#trigger-b').boundingBox();
const bottom = a.y + a.height;
const result = {};

// Open B by hover, then head for B's panel low along the bar, across trigger A
// (~120 ms over it), and down into the panel. Each step goes one pixel down for
// ten across: at two thirds of a pixel, some steps rounded to none, and a step
// straight sideways is not heading into the panel (CI, macOS).
await page.mouse.move(b.x + b.width / 2, b.y - 40);
await glide({ x: b.x + b.width / 2, y: b.y - 40 }, { x: b.x + b.width / 2, y: bottom - 14 }, 4, 20);
await page.clock.runFor(100);
result.hoverOpensB = await expanded('trigger-b');
await glide({ x: b.x + b.width / 2, y: bottom - 14 }, { x: a.x + a.width / 2, y: bottom - 2 }, 12, 20);
await glide({ x: a.x + a.width / 2, y: bottom - 2 }, { x: a.x + a.width / 2 - 20, y: bottom + 40 }, 4, 20);
await page.clock.runFor(400);
result.diagonalKeepsB = (await expanded('trigger-b')) && (await page.evaluate(() => window.aOpened)) === 0;

// Leave, then hover A from above and click it: the click must not close it.
await page.mouse.move(a.x + a.width / 2, bottom + 300);
await page.mouse.move(900, 20);
await page.clock.runFor(100);
await glide({ x: a.x + a.width / 2, y: a.y - 40 }, { x: a.x + a.width / 2, y: a.y + a.height / 2 }, 4, 20);
await page.clock.runFor(100);
await page.mouse.down(); await page.mouse.up();
await page.clock.runFor(100);
result.clickAfterHoverKeepsOpen = await expanded('trigger-a');

// Along the bar, sideways, the switch is prompt.
await glide({ x: a.x + a.width / 2, y: a.y + a.height / 2 }, { x: b.x + b.width / 2, y: b.y + b.height / 2 }, 6, 15);
await page.clock.runFor(120);
result.sidewaysSwitchIsPrompt = await expanded('trigger-b');
console.log(JSON.stringify(result));
await browser.close();
"""

DRAWER_SCENARIO = r"""
const page = await browser.newPage({ viewport: { width: 1000, height: 700 } });
await page.goto(pathToFileURL(process.argv[2]).href);
const isOpen = () => page.evaluate(() => document.getElementById('nav-drawer').open);
const result = {};
await page.click('#nav-toggle');
await page.waitForTimeout(800);
const r = await page.locator('#nav-drawer').boundingBox();
await page.mouse.click(r.x + r.width / 2, r.y + r.height - 20);   // the drawer's own box
await page.waitForTimeout(100);
result.ownClickKeepsOpen = await isOpen();
await page.mouse.click(10, r.y + r.height / 2);                     // the backdrop
await page.waitForTimeout(100);
result.backdropCloses = !(await isOpen());
console.log(JSON.stringify(result));
await browser.close();
"""

OFFSET_SCENARIO = r"""
const page = await browser.newPage({ viewport: { width: 1000, height: 700 } });
await page.goto(pathToFileURL(process.argv[2]).href);
const result = {};
result.read = await page.evaluate(process.env.NAV_OFFSET_EXPR);
result.real = await page.evaluate(() => {
  const probe = document.createElement('div');
  probe.style.blockSize = 'var(--nav-offset)';
  document.body.append(probe);
  const px = probe.getBoundingClientRect().height;
  probe.remove();
  return px;
});
console.log(JSON.stringify(result));
await browser.close();
"""

POPOVER_SCENARIO = r"""
const page = await browser.newPage();
await page.setContent('<button popovertarget="p">Menu</button><div id="p" popover><a href="#x">x</a></div>');
const cdp = await page.context().newCDPSession(page);
await cdp.send('Accessibility.enable');
const expanded = async () => {
  const { nodes } = await cdp.send('Accessibility.getFullAXTree');
  const n = nodes.find((x) => x.role?.value === 'button' && x.name?.value === 'Menu');
  return (n.properties || []).find((p) => p.name === 'expanded')?.value.value ?? null;
};
const result = { closed: await expanded() };
await page.locator('button').click();
result.open = await expanded();
await page.mouse.click(400, 400);                    // light dismiss
result.dismissed = await expanded();
console.log(JSON.stringify(result));
await browser.close();
"""


@unittest.skipUnless(NODE and playwright_modules(), "needs node plus WDS_NODE_MODULES "
                                                     "pointing at playwright")
class NavigationCodeInABrowser(TempDirTest):
    """SB-A20: the four behaviour bugs in navigation-patterns.md §2.4 and §6."""

    def scenario(self, name, html, script, **env_changes):
        from test_starter_css import PROBE
        page = self.write(f"{name}.html", html)
        probe = self.write(f"{name}.mjs", PROBE.split("const page =")[0] + script)
        proc = subprocess.run([NODE, str(probe), str(page)], capture_output=True, timeout=240,
                              env=env(NODE_PATH=playwright_modules(), **env_changes))
        if proc.returncode == 3:
            self.skipTest(output(proc))
        self.assertEqual(proc.returncode, 0, output(proc))
        return json.loads(proc.stdout.decode("utf-8").strip().splitlines()[-1])

    def test_the_safe_triangle_holds_and_a_click_keeps_a_hovered_panel(self):
        code = section_code("## 2. Mega menu", NAV_CODE)
        seen = self.scenario("megamenu", page_with("".join(code["css"]) + MEGAMENU_FRAME,
                                                   MEGAMENU_BODY, "".join(code["js"])),
                             MEGAMENU_SCENARIO)
        self.assertEqual(seen, {"hoverOpensB": True, "diagonalKeepsB": True,
                                "clickAfterHoverKeepsOpen": True, "sidewaysSwitchIsPrompt": True})

    def test_a_click_inside_the_drawer_does_not_close_it(self):
        code = section_code("## 3. Off-canvas drawer", NAV_CODE)
        seen = self.scenario("drawer", page_with("".join(code["css"]), "".join(code["html"]),
                                                 "".join(code["js"])), DRAWER_SCENARIO)
        self.assertEqual(seen, {"ownClickKeepsOpen": True, "backdropCloses": True})

    def test_the_scroll_spy_reads_the_real_nav_offset(self):
        spec = next(c for c in section_code("## 4. Spacing spec")["css"] if "--nav-offset:" in c)
        js = "".join(section_code("## 4. Scroll-spy", NAV_CODE)["js"])
        expr = re.search(r"const navOffset = (.*?);\n", js, re.S).group(1)
        seen = self.scenario("offset", page_with(spec, "<main>x</main>"), OFFSET_SCENARIO,
                             NAV_OFFSET_EXPR=expr)
        self.assertGreater(seen["real"], 0)
        self.assertEqual(seen["read"], seen["real"])

    def test_popover_invokers_get_their_expanded_state_from_the_browser(self):
        seen = self.scenario("popover", "<!doctype html><title>t</title>", POPOVER_SCENARIO)
        self.assertEqual(seen, {"closed": False, "open": True, "dismissed": False})
        text = NAV.read_text(encoding="utf-8")
        self.assertNotRegex(text, r"(?i)you must still set it|does \**not\** set `aria-expanded`")


# ---------------------------------------------------------------------------
# SS-A12 -- the @property recipe in style-architecture.md §7
# ---------------------------------------------------------------------------

REFERENCES = SKILLS / "web-design-studio" / "references"
PROPERTY = re.compile(r"@property\s+(--[\w-]+)\s*\{([^}]*)\}")

PROPERTY_SCENARIO = r"""
const page = await browser.newPage();
await page.goto(pathToFileURL(process.argv[2]).href);
const names = JSON.parse(process.env.REGISTERED);
const result = {};
for (const name of names) {
  // An element that declares nothing reads the initial value only if the
  // registration took; a dropped @property leaves the property unset ("").
  result[name] = await page.evaluate((n) =>
    getComputedStyle(document.getElementById('bare')).getPropertyValue(n).trim(), name);
}
console.log(JSON.stringify(result));
await browser.close();
"""


def property_recipe():
    text = (REFERENCES / "style-architecture.md").read_text(encoding="utf-8")
    trap = text.split("### The inheritance trap", 1)[1].split("\n## ", 1)[0]
    return PROPERTY.findall(trap)


class PropertyRecipe(TempDirTest):
    """SS-A12: the recipe registered --card-inset with `initial-value: 1.5rem`.
    A rem is not computationally independent, so the browser dropped the rule.
    And had it worked, `inherits: false` would have starved `.card__media`,
    which reads --card-inset from the card root."""

    def test_the_recipe_registers_something(self):
        self.assertTrue(property_recipe())

    def test_a_non_inheriting_socket_is_read_by_no_part(self):
        for name, body in property_recipe():
            if not re.search(r"inherits:\s*false", body):
                continue
            for md in sorted(REFERENCES.glob("*.md")):
                for block in re.findall(r"^```css\n(.*?)^```", md.read_text(encoding="utf-8"),
                                        re.S | re.M):
                    block = re.sub(r"/\*.*?\*/", "", block, flags=re.S)
                    for selector, decls in re.findall(r"([^{};]+)\{([^{}]*)\}", block):
                        selector = selector.strip()
                        if f"var({name}" in decls:
                            with self.subTest(socket=name, doc=md.name, selector=selector):
                                # A part: a BEM element, or anything below the root.
                                self.assertNotRegex(selector, r"__|\s",
                                                    "a part reads it: it must inherit")

    @unittest.skipUnless(NODE and playwright_modules(), "needs node plus WDS_NODE_MODULES "
                                                         "pointing at playwright")
    def test_the_browser_accepts_the_registration(self):
        from test_starter_css import PROBE
        recipe = property_recipe()
        css = "".join(f"@property {name} {{{body}}}" for name, body in recipe)
        page = self.write("prop.html", f"<!doctype html><title>t</title><style>{css}</style>"
                                       "<div id=\"bare\">x</div>")
        probe = self.write("prop.mjs", PROBE.split("const page =")[0] + PROPERTY_SCENARIO)
        proc = subprocess.run([NODE, str(probe), str(page)], capture_output=True, timeout=240,
                              env=env(NODE_PATH=playwright_modules(),
                                      REGISTERED=json.dumps([n for n, _ in recipe])))
        if proc.returncode == 3:
            self.skipTest(output(proc))
        self.assertEqual(proc.returncode, 0, output(proc))
        seen = json.loads(proc.stdout.decode("utf-8").strip().splitlines()[-1])
        for name, value in seen.items():
            with self.subTest(socket=name):
                self.assertNotEqual(value, "", f"the browser dropped @property {name}")


@unittest.skipUnless(NODE and playwright_modules(), "needs node plus WDS_NODE_MODULES "
                                                     "pointing at playwright")
class RuntimeReportFile(TempDirTest):
    """GT-A15: `--json > file` left the CI log with nothing a person could read,
    and the perf recipe's second, readable run (`--runs 0`) always failed."""

    def check(self, proc, report):
        if proc.returncode == 2 and b"browser" in proc.stderr.lower():
            self.skipTest("no usable browser: " + output(proc)[-200:])
        self.assertIn(proc.returncode, (0, 1), output(proc))
        self.assertFalse(proc.stdout.lstrip().startswith(b"{"), "stdout is for a person")
        return json.loads((self.tmp / report).read_bytes())

    def test_measure_vitals_prints_its_report_and_writes_the_json(self):
        page = self.write("index.html", "<!doctype html><html lang=\"en\"><title>t</title>"
                                        "<main><h1>Hi</h1></main></html>\n")
        proc = run_node("perf-budget-gate", "measure_vitals.mjs", page, "--runs", "1",
                        "--report", "perf-runtime.json", cwd=self.tmp, timeout=240,
                        env_changes={"NODE_PATH": playwright_modules()})
        data = self.check(proc, "perf-runtime.json")
        self.assertIn("LCP", proc.stdout.decode("utf-8"))
        self.assertIn("stats", data)

    @unittest.skipUnless(playwright_modules() and os.path.isdir(
        os.path.join(playwright_modules(), "axe-core")), "needs axe-core beside playwright")
    def test_a11y_runtime_prints_its_report_and_writes_the_json(self):
        page = self.write("page.html", "<!doctype html><html lang=\"en\"><title>t</title>"
                                       "<main><h1>Hi</h1><button>Go</button></main></html>\n")
        proc = run_node("a11y-audit-runner", "a11y_runtime.mjs", "--file", page,
                        "--report", "a11y-report.json", cwd=self.tmp, timeout=300,
                        env_changes={"NODE_PATH": playwright_modules()})
        data = self.check(proc, "a11y-report.json")
        self.assertIn("findings", data)


if __name__ == "__main__":
    unittest.main()
