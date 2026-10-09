"""The workflow commands (P26 part 1: XC-C3, GT-C12, LC-B4, XC-C8).

workflow-commands/ holds skills a user runs by name, each with
`disable-model-invocation: true`, so they stay out of the skill listing.
plugin.json's `skills` key adds the folder to the default skills/ scan, which
keeps them out of the 13 skills and their .skill files.
- /gate runs the three static gates on a project, with one verdict;
- /install-gate vendors the gate scripts into the project's scripts/ and
  writes the CI workflow: the gates in a pinned Playwright image, the static
  gates on Windows, and a job that records the baselines.

The SKILL.md frontmatter and the workflow go through js-yaml, a real YAML
parser, from the suite's tooling (WDS_NODE_MODULES, as for the real-tool
tests). The Windows job's commands run here, on a fixture project, so the
variant is tested on each platform CI runs.
"""
from __future__ import annotations

import hashlib
import json
import re
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


def load_yaml(text: str):
    proc = subprocess.run([NODE, "-e", LOAD_YAML, YAML_MODULES], input=text.encode("utf-8"), env=env(),
                          capture_output=True, timeout=60)
    assert proc.returncode == 0, output(proc)
    return json.loads(proc.stdout)


def front(skill_md) -> tuple[dict, str]:
    text = skill_md.read_text(encoding="utf-8")
    head, body = text[4:].split("\n---\n", 1)
    return load_yaml(head), body


class TheCommandFiles(unittest.TestCase):
    """XC-C3: each command is a skill only the user invokes, and it may run
    exactly the script it names, with no permission prompt."""

    def test_the_manifest_adds_the_folder_to_the_skills(self):
        manifest = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_bytes())
        self.assertEqual(["./workflow-commands/"], manifest["skills"])
        self.assertEqual(["gate", "install-gate"], sorted(p.parent.name for p in COMMANDS.glob("*/SKILL.md")))

    @needs_yaml
    def test_each_command_is_user_invoked_and_runs_what_it_allows(self):
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
                scripts = set()
                for rule in rules:
                    found = re.fullmatch(r'Bash\((python3?) "\$\{CLAUDE_SKILL_DIR\}/(scripts/[\w.]+)" \*\)', rule)
                    self.assertIsNotNone(found, rule)
                    self.assertTrue((skill_md.parent / found.group(2)).is_file(), found.group(2))
                    scripts.add(found.group(2))
                commands = re.findall(r"^(python3? \S+)", body, re.M)
                self.assertTrue(commands)
                for command in commands:                      # each one the body runs is allowed
                    self.assertIn(command, {f'{py} "${{CLAUDE_SKILL_DIR}}/{s}"' for py in ("python", "python3")
                                            for s in scripts})


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

    def test_a_path_the_workflow_cannot_run_unquoted_is_refused(self):
        """Codex on #85: the workflow runs each path unquoted, so `web source`
        became two arguments."""
        for args in (["--src", "web source"], ["--dist", "../out"], ["--dest", "/abs"], ["--build", "npm run b # x"]):
            with self.subTest(args=args):
                self.assertIn("must be", output(self.install(*args, code=2)))
        for baseline in ("my baselines/a.json", "ci/a;rm -rf x.json", "ci/$(id).json"):     # CodeRabbit on #85
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


if __name__ == "__main__":
    unittest.main()
