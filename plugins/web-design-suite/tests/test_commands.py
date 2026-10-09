"""The workflow commands (P26 part 1: XC-C3, GT-C12, LC-B4, XC-C8).

workflow-commands/ holds skills a user runs by name, each with
`disable-model-invocation: true`, so they stay out of the skill listing.
plugin.json's `skills` key adds the folder to the default skills/ scan, which
keeps them out of the 13 skills and their .skill files.
- /gate runs the three static gates on a project, with one verdict;
- /install-gate vendors the gate scripts into the project's scripts/ and
  writes the CI workflow: the gates in a pinned Playwright image, the static
  gates on Windows, and a job that records the baselines.
Part 2 (XC-C3, SS-C6, LC-C9): the systems and the lifecycle.
- /new-system and /release-check have runners: a brand colour to the starter
  system with its role pairs checked; extract, diff, gate, changelog, guide.
- /contrast, /migrate, /figma-sync and /docs-check are chains: the body runs
  the skills' own scripts through ${CLAUDE_PLUGIN_ROOT}, and the tests run
  the body's commands, in order, on a fixture project.

The SKILL.md frontmatter and the workflow go through js-yaml, a real YAML
parser, from the suite's tooling (WDS_NODE_MODULES, as for the real-tool
tests). The Windows job's commands run here, on a fixture project, so the
variant is tested on each platform CI runs.
"""
from __future__ import annotations

import hashlib
import json
import re
import shlex
import subprocess
import sys
import unittest

from wds_support import NODE, PLUGIN, TOOLING, TempDirTest, env, output, tool_modules

COMMANDS = PLUGIN / "workflow-commands"
RUN_GATES = COMMANDS / "gate" / "scripts" / "run_gates.py"
INSTALL = COMMANDS / "install-gate" / "scripts" / "install_gate.py"
YAML_MODULES = tool_modules("WDS_NODE_MODULES", "js-yaml")
LOAD_YAML = ("const yaml = require(require('path').join(process.argv[1], 'js-yaml'));"
             "process.stdout.write(JSON.stringify(yaml.load(require('fs').readFileSync(0, 'utf8'))));")
LEAK = "@layer components {\n  .card {\n    color: var(--neutral-700);\n  }\n}\n"
CLEAN = "@layer components {\n  .card {\n    color: var(--fg-default);\n  }\n}\n"
PAGE = ('<!doctype html>\n<html lang="en">\n<head><title>Home</title></head>\n'
        '<body><main><h1>Home</h1></main></body>\n</html>\n')
needs_yaml = unittest.skipUnless(NODE and YAML_MODULES, "node and js-yaml (tooling/main) are not installed")
NAMES = ["contrast", "docs-check", "figma-sync", "gate", "install-gate", "migrate", "new-system", "release-check"]
# Bash(python "${CLAUDE_SKILL_DIR}/scripts/x.py" *), or a skill's script by the
# plugin's root, with any fixed arguments before the wildcard.
RULE = re.compile(r'Bash\((python3?) ("\$\{(CLAUDE_SKILL_DIR|CLAUDE_PLUGIN_ROOT)\}/([\w./-]+)"(?: [^\s*()]+)*) \*\)')
STARTER = PLUGIN / "skills" / "web-design-studio" / "assets" / "starter" / "styles"
SCRIPTS = {name: PLUGIN / "skills" / skill / "scripts" / f"{name}.py" for skill, name in (
    ("design-system-docs", "extract_system"), ("design-system-versioning", "diff_system"))}


def load_yaml(text: str):
    proc = subprocess.run([NODE, "-e", LOAD_YAML, YAML_MODULES], input=text.encode("utf-8"), env=env(),
                          capture_output=True, timeout=60)
    assert proc.returncode == 0, output(proc)
    return json.loads(proc.stdout)


def front(skill_md) -> tuple[dict, str]:
    text = skill_md.read_text(encoding="utf-8")
    head, body = text[4:].split("\n---\n", 1)
    return load_yaml(head), body


def body_commands(body: str) -> list:
    """The commands in the body's bash blocks, in the order Claude runs them."""
    return [line.strip() for block in re.findall(r"```bash\n(.*?)```", body, re.S)
            for line in block.splitlines() if re.match(r"\s*python3? ", line)]


def allows(prefix: str, command: str) -> bool:
    """A `Bash(prefix *)` rule's match: the prefix, then a word boundary."""
    return command == prefix or command.startswith(prefix + " ")


class TheCommandFiles(unittest.TestCase):
    """XC-C3: each command is a skill only the user invokes, and it may run
    exactly the scripts its body runs, with no permission prompt."""

    def test_the_manifest_adds_the_folder_to_the_skills(self):
        manifest = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_bytes())
        self.assertEqual(["./workflow-commands/"], manifest["skills"])
        self.assertEqual(NAMES, sorted(p.parent.name for p in COMMANDS.glob("*/SKILL.md")))

    @needs_yaml
    def test_each_command_is_user_invoked_and_runs_what_it_allows(self):
        """Every command the body runs starts with a rule's prefix, every rule
        is one the body runs, and each has its python3 twin for macOS. A rule
        names a script that exists: the command's own, by ${CLAUDE_SKILL_DIR},
        or a skill's, by ${CLAUDE_PLUGIN_ROOT}."""
        commands = sorted(COMMANDS.glob("*/SKILL.md"))
        self.assertTrue(commands)                          # no vacuous pass
        for skill_md in commands:
            with self.subTest(command=skill_md.parent.name):
                fields, body = front(skill_md)
                self.assertEqual(skill_md.parent.name, fields["name"])
                self.assertTrue(0 < len(fields["description"]) <= 1024)
                self.assertIs(True, fields["disable-model-invocation"])
                rules = fields["allowed-tools"]
                self.assertIsInstance(rules, list)
                prefixes = []
                for rule in rules:
                    found = RULE.fullmatch(rule)
                    self.assertIsNotNone(found, rule)
                    own = found.group(3) == "CLAUDE_SKILL_DIR"
                    self.assertRegex(found.group(4), r"^scripts/[\w.]+$" if own else r"^skills/[\w-]+/scripts/[\w.]+$")
                    self.assertTrue(((skill_md.parent if own else PLUGIN) / found.group(4)).is_file(), rule)
                    prefixes.append(f"{found.group(1)} {found.group(2)}")
                python = sorted(p for p in prefixes if p.startswith("python "))
                self.assertEqual(python, sorted("python " + p[8:] for p in prefixes if p.startswith("python3 ")))
                run = body_commands(body)
                self.assertTrue(run)
                for command in run:                           # each one the body runs is allowed
                    self.assertTrue(any(allows(p, command) for p in prefixes), command)
                for prefix in python:                         # and nothing it never runs is
                    self.assertTrue(any(allows(prefix, c) for c in run), f"allowed, never run: {prefix}")


class CommandTest(TempDirTest):
    def setUp(self):
        super().setUp()
        self.write(".git/HEAD", "x\n")
        self.write("src/components/card.css", CLEAN)
        self.write("src/index.html", PAGE)
        self.write("dist/index.html", PAGE)

    def run_py(self, *args, **changes):
        return subprocess.run([sys.executable, "-B", *map(str, args)], cwd=self.tmp, capture_output=True,
                              env=env(PYTHONPATH=None, **changes), timeout=300)


class TheGateCommand(CommandTest):
    """XC-C3's /gate: design, accessibility and performance in one run."""

    def verdict(self, proc):
        text = proc.stdout.decode("utf-8", "replace")
        return dict(re.findall(r"^  (design|accessibility|performance)\s+(.+?)\s*$", text.split("== verdict")[-1], re.M))

    def test_a_clean_project_passes_all_three(self):
        proc = self.run_py(RUN_GATES, "--src", "src")
        self.assertEqual(0, proc.returncode, output(proc))
        self.assertEqual({"design": "passed", "accessibility": "passed", "performance": "passed"}, self.verdict(proc))

    def test_a_leak_fails_the_design_gate(self):
        self.write("src/components/card.css", LEAK)
        proc = self.run_py(RUN_GATES, "--src", "src")
        self.assertEqual(1, proc.returncode, output(proc))
        self.assertEqual("FAILED", self.verdict(proc)["design"])
        self.assertIn("tier1-leak", output(proc))

    def test_without_a_build_the_performance_gate_says_it_was_skipped(self):
        (self.tmp / "dist" / "index.html").unlink()
        (self.tmp / "dist").rmdir()
        proc = self.run_py(RUN_GATES, "--src", "src")
        self.assertEqual(0, proc.returncode, output(proc))
        self.assertTrue(self.verdict(proc)["performance"].startswith("skipped (no build output"))

    def test_a_named_build_that_is_missing_could_not_run(self):
        """CodeRabbit on #85: a --dist that does not exist was skipped, and
        the run passed. Only a build found by looking may be skipped."""
        proc = self.run_py(RUN_GATES, "--src", "src", "--dist", "nowhere")
        self.assertEqual(2, proc.returncode, output(proc))
        self.assertEqual("could not run (exit 2)", self.verdict(proc)["performance"])

    def test_the_projects_config_reaches_the_gates(self):
        """XC-C8: the gates read .design-suite.json, so the project's ramps
        and components count, and a baseline it names holds."""
        self.write(".design-suite.json", json.dumps({"schema": 1, "tokens": "src/brand/palette.css",
                                                     "components": ["src/widgets/**"],
                                                     "baselines": {"audit": "ci/audit-baseline.json"}}))
        self.write("src/brand/palette.css", "@layer tokens {\n  :root {\n    --brand-500: #b4400a;\n  }\n}\n")
        self.write("src/widgets/card.css", "@layer layout {\n  .card {\n    color: var(--brand-500);\n  }\n}\n")
        proc = self.run_py(RUN_GATES, "--src", "src")
        self.assertEqual("FAILED", self.verdict(proc)["design"], output(proc))
        audit = PLUGIN / "skills" / "web-design-studio" / "scripts" / "audit_design.py"
        self.assertEqual(0, self.run_py(audit, "--write-baseline", "ci/audit-baseline.json").returncode)
        self.assertEqual("passed", self.verdict(self.run_py(RUN_GATES, "--src", "src"))["design"])


class TheInstallGate(CommandTest):
    """XC-C3's /install-gate, GT-C12's CI template and LC-B4's bootstrap."""

    def install(self, *args, code=0):
        proc = self.run_py(INSTALL, *args)
        self.assertEqual(code, proc.returncode, output(proc))
        return proc

    def workflow(self):
        return (self.tmp / ".github" / "workflows" / "design-gates.yml").read_text(encoding="utf-8")

    def test_the_scripts_are_vendored_with_their_hashes(self):
        self.install()
        stamp = json.loads((self.tmp / "scripts" / "design-gates.json").read_bytes())
        manifest = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_bytes())
        self.assertEqual(manifest["version"], stamp["version"])
        self.assertIn("audit_design.py", stamp["files"])
        for name, digest in stamp["files"].items():
            with self.subTest(file=name):
                source = next(PLUGIN.glob(f"skills/*/scripts/{name}")).read_bytes()
                self.assertEqual(hashlib.sha256(source).hexdigest(), digest)
                self.assertEqual(source, (self.tmp / "scripts" / name).read_bytes())
        self.assertEqual(hashlib.sha256(self.workflow().encode("utf-8")).hexdigest(), stamp["workflow"])

    def test_the_vendored_gates_run_without_the_plugin(self):
        """LC-B4: every CI recipe runs `python -m scripts.X` in a clean
        checkout. After the install, both forms run from the project alone."""
        self.install()
        for args in (["scripts/audit_design.py", "--strict"], ["-m", "scripts.audit_design", "--strict"],
                     ["scripts/a11y_static.py", "src", "--strict"], ["-m", "scripts.a11y_static", "src"],
                     ["scripts/perf_audit.py", "dist", "--src", "src"], ["scripts/check_roles.py", "--help"]):
            with self.subTest(args=args):
                proc = self.run_py(*args)
                self.assertEqual(0, proc.returncode, output(proc))
        self.write("src/components/card.css", LEAK)
        self.assertEqual(1, self.run_py("scripts/audit_design.py", "--strict").returncode)

    @unittest.skipUnless(NODE, "node is not installed")
    def test_the_browser_gates_find_their_helpers(self):
        self.install()
        for script in ("a11y_runtime.mjs", "measure_vitals.mjs"):
            with self.subTest(script=script):
                proc = subprocess.run([NODE, f"scripts/{script}", "--help"], cwd=self.tmp, capture_output=True,
                                      env=env(), timeout=60)
                self.assertEqual(0, proc.returncode, output(proc))

    @needs_yaml
    def test_the_workflow_pins_the_projects_playwright(self):
        """GT-C12: the image's browsers fit one playwright, the project's."""
        self.write("package.json", json.dumps({"devDependencies": {"playwright": "1.62.1"}}))
        self.write(".design-suite.json", json.dumps({"schema": 1, "baselines": {"a11y": "ci/a11y.json"}}))
        self.install()
        text = self.workflow()
        self.assertNotRegex(text, r"@[A-Z_0-9]+@")
        flow = load_yaml(text)
        self.assertEqual({"gates", "windows", "baselines"}, set(flow["jobs"]))
        for job in ("gates", "baselines"):
            self.assertEqual("mcr.microsoft.com/playwright:v1.62.1-noble", flow["jobs"][job]["container"])
        self.assertEqual("windows-latest", flow["jobs"]["windows"]["runs-on"])
        checkouts = [s for job in flow["jobs"].values() for s in job["steps"]
                     if s.get("uses", "").startswith("actions/checkout@")]
        self.assertEqual(3, len(checkouts))
        for step in checkouts:                    # CodeRabbit on #85: no token for npm's install scripts
            self.assertIs(False, step["with"]["persist-credentials"])
        self.assertIn("update-baselines", flow["on"]["workflow_dispatch"]["inputs"])
        runs = "\n".join(step.get("run", "") for step in flow["jobs"]["gates"]["steps"])
        self.assertIn("npx wait-on http://127.0.0.1:8080", runs)
        self.assertIn("apt-get install -y --no-install-recommends python3", runs)
        recorded = "\n".join(step.get("run", "") for step in flow["jobs"]["baselines"]["steps"])
        self.assertIn("--write-baseline ci/a11y.json", recorded)
        self.assertIn("--write-baseline .design-baseline.json", recorded)

    @needs_yaml
    def test_the_build_command_stays_a_string(self):
        """Codex on #85: `run: true` is a YAML boolean, not the command
        `true`. The build sits in a block scalar, so any command line reads as
        itself."""
        for build in ("true", "null", "npm run b # x", "make: all"):
            with self.subTest(build=build):
                self.install("--build", build, "--force")
                runs = [s["run"] for job in load_yaml(self.workflow())["jobs"].values() for s in job["steps"]
                        if s.get("name") == "build"]
                self.assertEqual([build + "\n"] * 3, runs)

    @needs_yaml
    def test_the_baselines_upload_takes_dot_files(self):
        """Codex on #85: upload-artifact leaves hidden files out unless told,
        and the default baselines all start with a dot."""
        self.install()
        [upload] = [s for s in load_yaml(self.workflow())["jobs"]["baselines"]["steps"]
                    if s.get("uses", "").startswith("actions/upload-artifact@")]
        self.assertIs(True, upload["with"]["include-hidden-files"])
        self.assertEqual("error", upload["with"]["if-no-files-found"])
        self.assertIn(".design-baseline.json", upload["with"]["path"])

    @needs_yaml
    def test_the_windows_job_runs_here(self):
        """GT-C12's Windows variant: its gate steps, run on the fixture as
        written, pass on a clean project and fail on a leak."""
        self.install()
        steps = [s["run"] for s in load_yaml(self.workflow())["jobs"]["windows"]["steps"]
                 if s.get("run", "").startswith("python ")]
        self.assertEqual(3, len(steps))
        for step in steps:
            with self.subTest(step=step):
                self.assertEqual(0, self.run_py(*step.split()[1:]).returncode)
        self.write("src/components/card.css", LEAK)
        self.assertEqual(1, self.run_py(*steps[0].split()[1:]).returncode)

    @needs_yaml
    def test_the_baseline_job_runs_here(self):
        """GT-C12's baseline job, run as written on a fresh checkout: the
        config's baselines sit in a folder that does not exist yet, and each
        gate used to stop there with a traceback instead of creating it."""
        self.write(".design-suite.json", json.dumps({"schema": 1, "baselines": {
            "audit": "ci/audit.json", "a11y": "ci/a11y.json", "perf": "ci/perf.json"}}))
        self.write("src/components/card.css", LEAK)
        self.install()
        [record] = [s["run"] for s in load_yaml(self.workflow())["jobs"]["baselines"]["steps"]
                    if s.get("name") == "record the baselines"]
        for line in record.splitlines():
            with self.subTest(line=line):
                self.assertEqual("python3", line.split()[0])
                proc = self.run_py(*line.split()[1:])
                self.assertEqual(0, proc.returncode, output(proc))
        for name in ("audit", "a11y", "perf"):
            self.assertTrue((self.tmp / "ci" / f"{name}.json").is_file(), name)
        self.assertEqual(0, self.run_py("scripts/audit_design.py", "--strict").returncode)   # the leak, recorded

    def test_a_missing_or_ranged_playwright(self):
        proc = self.install()
        self.assertIn("mcr.microsoft.com/playwright:v1.63.0-noble", self.workflow())
        self.assertIn("npm i -D -E playwright@1.63.0 axe-core serve wait-on", output(proc))
        self.write("package.json", json.dumps({"devDependencies": {"playwright": "^1.60.0"}}))
        (self.tmp / ".github" / "workflows" / "design-gates.yml").unlink()
        self.assertIn("a range", output(self.install(code=1)))
        self.assertFalse((self.tmp / ".github" / "workflows" / "design-gates.yml").exists())

    def test_the_browser_gates_packages_are_named_when_missing(self):
        """Codex on #85: with playwright pinned, nothing said axe-core, serve
        and wait-on were missing, and a11y_runtime stops without axe-core."""
        self.write("package.json", json.dumps({"devDependencies": {"playwright": "1.62.1"}}))
        text = output(self.install())
        self.assertIn("does not list them: axe-core, serve, wait-on", text)
        self.assertIn("npm i -D -E axe-core serve wait-on", text)
        self.write("package.json", json.dumps({"devDependencies": {
            "playwright": "1.62.1", "axe-core": "4.11.0", "serve": "14.2.4", "wait-on": "8.0.3"}}))
        self.assertNotIn("npm i -D -E", output(self.install()))

    def test_a_stamp_it_did_not_write_is_in_the_way(self):
        """Codex on #85: scripts/design-gates.json was written without the
        check every other file gets."""
        self.write("scripts/design-gates.json", '{"ours": true}\n')
        self.assertIn("scripts/design-gates.json", output(self.install(code=1)))
        self.assertEqual('{"ours": true}\n', (self.tmp / "scripts" / "design-gates.json").read_text())
        self.install("--force")
        # Codex on #85: a stamp naming the plugin with no map of files, and a
        # changed script, stopped with a traceback, even under --force
        self.write("scripts/design-gates.json", '{"plugin": "web-design-suite", "files": [1]}\n')
        self.write("scripts/audit_design.py", "# edited\n")
        self.assertIn("scripts/design-gates.json", output(self.install(code=1)))
        self.install("--force")

    def test_a_path_the_workflow_cannot_run_unquoted_is_refused(self):
        """Codex on #85: the workflow runs each path unquoted, so `web source`
        became two arguments."""
        for args in (["--src", "web source"], ["--dist", "../out"], ["--dest", "/abs"],
                     ["--src=-assets"], ["--dest=-scripts"]):       # Codex, CodeRabbit on #85: an option, not a path
            with self.subTest(args=args):
                self.assertIn("must be", output(self.install(*args, code=2)))
        for baseline in ("my baselines/a.json", "ci/a;rm -rf x.json", "ci/$(id).json", "-b.json"):
            with self.subTest(baseline=baseline):
                self.write(".design-suite.json", json.dumps({"schema": 1, "baselines": {"audit": baseline}}))
                self.assertIn("baselines.audit", output(self.install(code=2)))
        self.assertFalse((self.tmp / "scripts").exists())

    @unittest.skipUnless(TOOLING, "the repository's tooling/ is not beside the plugin")
    def test_the_default_image_is_the_playwright_the_suite_tests(self):
        tested = json.loads((TOOLING / "main" / "package.json").read_bytes())["devDependencies"]["playwright"]
        self.assertIn(f'TESTED_PLAYWRIGHT = "{tested}"', INSTALL.read_text(encoding="utf-8"))

    def test_it_never_overwrites_what_it_did_not_write(self):
        self.write(".github/workflows/design-gates.yml", "name: ours\n")
        self.assertIn(".github/workflows/design-gates.yml", output(self.install(code=1)))
        self.assertFalse((self.tmp / "scripts").exists())                 # nothing was written
        self.install("--force")
        self.install()                                                    # its own files, again
        self.write("scripts/audit_design.py", "# edited\n")
        self.assertIn("scripts/audit_design.py", output(self.install(code=1)))
        self.install("--force")

    def test_a_dry_run_writes_nothing(self):
        proc = self.install("--dry-run")
        self.assertIn("would write .github/workflows/design-gates.yml", output(proc))
        self.assertFalse((self.tmp / "scripts").exists())
        self.assertFalse((self.tmp / ".github").exists())


class BaselinesInAMissingFolder(CommandTest):
    """Each gate stopped with a traceback when --write-baseline named a file
    in a folder that does not exist yet, as a config's ci/ path is on a fresh
    checkout (found by the baseline job's test above)."""

    def test_each_gate_creates_the_folder(self):
        self.write("src/components/card.css", LEAK)
        gates = {"web-design-studio/scripts/audit_design.py": [],
                 "a11y-audit-runner/scripts/a11y_static.py": ["src"],
                 "perf-budget-gate/scripts/perf_audit.py": ["dist", "--src", "src"]}
        for script, args in gates.items():
            with self.subTest(script=script):
                name = script.rsplit("/", 1)[1]
                proc = self.run_py(PLUGIN / "skills" / script, *args, "--write-baseline", f"ci/new/{name}.json")
                self.assertEqual(0, proc.returncode, output(proc))
                self.assertTrue((self.tmp / "ci" / "new" / f"{name}.json").is_file())


class ChainTest(CommandTest):
    """Runs a command's body as Claude does: each command in its bash blocks,
    in order, with the plugin's paths substituted and each placeholder
    (`$ARGUMENTS`, PATHS, TOKENS, EXPORT, FG, BG) given the test's values."""
    command = ""

    def steps(self) -> list:
        return body_commands(front(COMMANDS / self.command / "SKILL.md")[1])

    def run_step(self, line: str, values: dict):
        argv = []
        for word in shlex.split(line):
            if word in values:
                argv += [str(v) for v in values[word]]
                continue
            self.assertFalse(word in ("$ARGUMENTS", "PATHS", "TOKENS", "EXPORT", "FG", "BG"), f"no value for {word}")
            argv.append(word.replace("${CLAUDE_PLUGIN_ROOT}", PLUGIN.as_posix())
                        .replace("${CLAUDE_SKILL_DIR}", (COMMANDS / self.command).as_posix()))
        self.assertEqual("python", argv[0])
        return self.run_py(*argv[1:])

    def starter(self, *names: str, rename: tuple = ()):
        """The starter's styles in src/styles/, a token renamed if asked."""
        for name in names or ("tokens.css",):
            text = (STARTER / name).read_bytes().decode("utf-8")
            if rename and name == "tokens.css":
                text = text.replace(*rename)
            self.write(f"src/styles/{name}", text)

    def snapshot(self, to: str):
        proc = self.run_py(SCRIPTS["extract_system"], "src", "--out", to)
        self.assertEqual(0, proc.returncode, output(proc))


def tree(root) -> dict:
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


class TheNewSystem(ChainTest):
    """XC-C3 and SS-C6: /new-system, a brand colour to the starter's system."""
    command = "new-system"

    def new(self, *args):
        (step,) = self.steps()
        return self.run_step(step, {"$ARGUMENTS": args})

    def test_a_brand_colour_becomes_a_system_the_gates_pass(self):
        proc = self.new("#2563eb")
        self.assertEqual(0, proc.returncode, output(proc))
        styles = self.tmp / "src" / "styles"
        self.assertEqual(sorted(p.name for p in STARTER.glob("*.css")), sorted(p.name for p in styles.iterdir()))
        tokens = (styles / "tokens.css").read_text(encoding="utf-8")
        self.assertRegex(tokens, r"--accent-600: oklch\(54\.6% 0\.215 262\.9\);\s*/\* #2563eb \*/")   # exact
        self.assertIn("--neutral-500: oklch(53.5% 0.009 262.9);", tokens)                            # its hue
        self.assertEqual((STARTER / "layout.css").read_bytes(), (styles / "layout.css").read_bytes())
        self.assertIn("100 of 100 pass", output(proc))
        gate = self.run_py(RUN_GATES, "src")                 # design and accessibility on src, perf on dist
        self.assertEqual(0, gate.returncode, output(gate))

    def test_a_failing_role_pair_is_named_and_the_files_kept(self):
        proc = self.new("#00ff00")
        self.assertEqual(1, proc.returncode, output(proc))
        self.assertIn("FAIL  --fg-on-accent on --bg-accent (light)", output(proc))
        self.assertTrue((self.tmp / "src" / "styles" / "tokens.css").is_file())

    def test_it_never_overwrites_without_force(self):
        self.assertEqual(0, self.new("#2563eb").returncode)
        before = tree(self.tmp / "src" / "styles")
        proc = self.new("#e8440a")
        self.assertEqual(2, proc.returncode, output(proc))
        self.assertIn("never overwrites", output(proc))
        self.assertEqual(before, tree(self.tmp / "src" / "styles"))
        self.assertEqual(0, self.new("#e8440a", "--force").returncode)
        self.assertNotEqual(before, tree(self.tmp / "src" / "styles"))

    def test_a_scale_replaces_the_starters_and_one_the_generator_refuses_writes_nothing(self):
        proc = self.new("#2563eb", "--ratio", "1.125", "--dual-ratio", "1.25", "--fluid", "380", "1440",
                        "--out", "styles")
        self.assertEqual(0, proc.returncode, output(proc))
        tokens = (self.tmp / "styles" / "tokens.css").read_text(encoding="utf-8")
        self.assertIn("--text-6xl: clamp(3.8147rem,", tokens)
        self.assertIn("--text-2xs:", tokens)
        proc = self.new("#2563eb", "--ratio", "1.25", "--out", "other")
        self.assertEqual(2, proc.returncode, output(proc))
        self.assertIn("11px", output(proc))
        self.assertFalse((self.tmp / "other").exists())


class TheReleaseCheck(ChainTest):
    """LC-C9: /release-check, extract, diff, gate, changelog, guide."""
    command = "release-check"
    LEDGER = {"schema": "design-system-versioning/deprecations@1", "deprecations": []}

    def setUp(self):
        super().setUp()
        self.starter()
        self.snapshot("published/system.json")
        self.write(".design-suite.json", json.dumps({"schema": 1, "baselines": {"system": "published/system.json"}}))
        self.out = self.tmp / "design-reports" / "release"

    def check(self, *args):
        (step,) = self.steps()
        return self.run_step(step, {"$ARGUMENTS": ["--from-version", "1.2.0", *args]})

    def test_an_unchanged_system_is_a_patch_with_its_changelog(self):
        proc = self.check()
        self.assertEqual(0, proc.returncode, output(proc))
        self.assertRegex(output(proc), r"version\s+1\.2\.0 -> 1\.2\.1")
        self.assertTrue((self.out / "CHANGELOG.part.md").is_file())
        self.assertFalse((self.out / "UPGRADE.md").exists())

    def test_a_rename_without_a_ledger_is_advisory_and_gets_its_guide(self):
        self.starter(rename=("--fg-subtle:", "--fg-faint:"))
        proc = self.check()
        self.assertEqual(0, proc.returncode, output(proc))
        self.assertIn("advisory", output(proc))
        self.assertRegex(output(proc), r"version\s+1\.2\.0 -> 2\.0\.0")
        self.assertTrue((self.out / "UPGRADE.md").is_file())

    def test_a_vanished_name_stops_the_release_at_the_gate(self):
        self.starter(rename=("--fg-subtle:", "--fg-faint:"))
        self.write("deprecations.json", json.dumps(self.LEDGER))
        self.write("design-reports/release/CHANGELOG.part.md", "an earlier run's\n")
        proc = self.check()
        self.assertEqual(1, proc.returncode, output(proc))
        self.assertIn("FAILED: --fg-subtle vanished", output(proc))
        self.assertFalse((self.out / "CHANGELOG.part.md").exists())      # none, not a stale one

    def test_with_no_published_snapshot_it_cannot_run(self):
        (self.tmp / ".design-suite.json").unlink()
        proc = self.check()
        self.assertEqual(2, proc.returncode, output(proc))
        self.assertIn("baselines.system", output(proc))


class TheChains(ChainTest):
    """XC-C3, SS-C6 and LC-C9: the commands whose body is the chain, run in
    order on a project whose .design-suite.json names its tokens."""

    def setUp(self):
        super().setUp()
        self.starter()
        self.write(".design-suite.json", json.dumps({"schema": 1, "tokens": "src/styles/tokens.css"}))

    def test_contrast_checks_the_role_pairs_or_one_pair(self):
        self.command = "contrast"
        pair, roles = self.steps()
        proc = self.run_step(roles, {"TOKENS": ["src/styles/tokens.css"]})
        self.assertEqual(0, proc.returncode, output(proc))
        self.starter(rename=("--fg-muted:       var(--neutral-600)", "--fg-muted: var(--neutral-300)"))
        proc = self.run_step(roles, {"TOKENS": ["src/styles/tokens.css"]})
        self.assertEqual(1, proc.returncode, output(proc))
        self.assertIn("FAIL  --fg-muted", output(proc))
        proc = self.run_step(pair, {"FG": ["#767676"], "BG": ["#ffffff"]})
        self.assertEqual(0, proc.returncode, output(proc))
        self.assertRegex(output(proc), r"PASS\s+4\.5:1")

    def test_migrate_takes_the_census_and_changes_nothing(self):
        self.command = "migrate"
        self.write("src/components/card.css", ".card {\n  padding: 13px;\n  color: #333;\n}\n"
                                              ".b {\n  padding: 12px;\n  color: #343434;\n}\n")
        before = tree(self.tmp / "src")
        steps = self.steps()
        self.assertEqual(3, len(steps))
        for step in steps:
            proc = self.run_step(step, {"PATHS": ["src"]})
            self.assertEqual(0, proc.returncode, output(proc))
        self.assertTrue((self.tmp / "design-reports" / "migration" / "proposal" / "reconciliation.md").is_file())
        self.assertEqual(before, tree(self.tmp / "src"))

    def test_figma_sync_stops_on_an_audit_error_and_generates_when_clean(self):
        self.command = "figma-sync"
        audit, questions, generate, compare = self.steps()
        clean = [{"name": "space/4", "type": "FLOAT", "value": 16}, {"name": "radius/md", "type": "FLOAT", "value": 8}]
        self.write("bad.json", json.dumps(clean + [{"name": "space/odd", "type": "FLOAT", "value": 13}]))
        proc = self.run_step(audit, {"EXPORT": ["bad.json"]})
        self.assertEqual(1, proc.returncode, output(proc))               # the sync stops here
        self.assertIn("space/odd", output(self.run_step(questions, {"EXPORT": ["bad.json"]})))
        self.write("export.json", json.dumps(clean))
        for step, values in ((audit, {}), (generate, {}), (compare, {"TOKENS": ["src/styles/tokens.css"]})):
            proc = self.run_step(step, {"EXPORT": ["export.json"], **values})
            self.assertEqual(0, proc.returncode, output(proc))
        self.assertTrue((self.tmp / "design-reports" / "figma" / "tokens" / "tokens.css").is_file())
        self.assertIn("major", output(proc))                              # the starter's tokens it lacks

    def test_docs_check_finds_the_drift(self):
        self.command = "docs-check"
        self.snapshot("docs/system.json")
        self.write(".design-suite.json", json.dumps({"schema": 1, "baselines": {"docs": "docs/system.json"}}))
        extract, check = self.steps()
        for step in (extract, check):
            proc = self.run_step(step, {"PATHS": ["src"]})
            self.assertEqual(0, proc.returncode, output(proc))
        self.starter(rename=("--fg-subtle:", "--fg-faint:"))
        self.assertEqual(0, self.run_step(extract, {"PATHS": ["src"]}).returncode)
        proc = self.run_step(check, {})
        self.assertEqual(1, proc.returncode, output(proc))
        self.assertIn("token removed    --fg-subtle", output(proc))


if __name__ == "__main__":
    unittest.main()
