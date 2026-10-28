"""The process gates: what CI requires of a leg and what a release requires of CI.

They read files outside the plugin (.github/, tooling/release/), so they skip in
an unpacked copy. Regressions covered (P67, the 2026-10-28 audit):
- OPS-1: CI cancelled main's run when the next merge landed, so 5 of 60 main
  commits had no finished run.
- OPS-2: a pushed v* tag released its commit without asking whether CI passed
  on it.
- OPS-3, TEST-11: the validate job installed whatever CLI npm's latest was.
- OPS-9: ci.yml pinned its actions to tags, and nothing moved any pin.
- OPS-13: a leg passed however many tests skipped.
- OPS-14, TEST-10: the browsers downloaded on every Linux run, and Windows and
  macOS tested the runner image's Chrome, whose version nobody chose.
- TEST-1: a browser test that found no browser skipped on Windows and macOS.
"""
from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
import unittest

from test_runtime_engines import ci_workflow
from wds_support import PLUGIN, REPO, TOOLING, TempDirTest, env, output

GATE = REPO / "tooling" / "release" / "ci_gate.py" if REPO else None
CEILING = PLUGIN / "tools" / "skip_ceiling.py"


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Workflow(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.text = ci_workflow()
        if cls.text is None:
            raise unittest.SkipTest("the repository's workflows are not here")
        cls.suite_job, _, cls.validate_job = cls.text.partition("\n  validate:\n")
        cls.steps = cls.suite_job.split("\n      - ")

    def step(self, needle):
        found = [s for s in self.steps if needle in s]
        self.assertEqual(1, len(found), f"one step of the suite job holds {needle!r}")
        return found[0]


class TheCiWorkflow(Workflow):

    def test_only_a_pull_requests_run_is_cancelled(self):
        self.assertRegex(self.text, r"(?m)^  cancel-in-progress: \$\{\{ github\.event_name == 'pull_request' \}\}$")

    def test_every_action_is_pinned_to_a_commit(self):
        uses = re.findall(r"(?m)^\s*-?\s*uses:\s*(\S+)(.*)$", self.text)
        self.assertGreaterEqual(len(uses), 10)
        for action, comment in uses:
            with self.subTest(action=action):
                self.assertRegex(action, r"^[\w.-]+/[\w./-]+@[0-9a-f]{40}$")
                self.assertRegex(comment, r"#\s*v\d", "a version comment beside the commit")

    def test_the_validate_job_installs_one_version_of_the_cli(self):
        self.assertRegex(self.validate_job,
                         r"(?m)^\s+run: npm install --global @anthropic-ai/claude-code@\d+\.\d+\.\d+$")

    def test_every_leg_requires_a_browser(self):
        suite = self.step("name: The suite\n")
        self.assertRegex(suite, r'(?m)^\s+WDS_REQUIRE_BROWSER: "1"$')

    def test_every_leg_tests_playwrights_own_chromium_from_the_cache(self):
        where = self.step("PLAYWRIGHT_BROWSERS_PATH=")
        key = re.search(r"(?m)^\s+id: (\S+)$", where).group(1)
        self.assertIn("require('./tooling/main/node_modules/playwright/package.json').version", where)
        steps = [s for s in self.steps if f"steps.{key}.outputs.key" in s]
        self.assertEqual(2, len(steps), "a restore and a save, keyed by the version")
        restore, save = steps
        self.assertIn("actions/cache/restore@", restore)
        self.assertIn("actions/cache/save@", save)
        restored = re.search(r"(?m)^\s+id: (\S+)$", restore).group(1)
        self.assertIn(f"steps.{restored}.outputs.cache-hit != 'true'", save)
        for step, text in (("restore", restore), ("save", save)):
            with self.subTest(step=step):
                self.assertRegex(text, r"(?m)^\s+path: \$\{\{ runner\.temp \}\}/ms-playwright$")
        linux = self.step("install --only-shell --with-deps")
        other = self.step("npx playwright install --only-shell chromium)")
        self.assertIn("if: runner.os == 'Linux'", linux)
        self.assertIn("if: runner.os != 'Linux'", other)
        order = [self.steps.index(s) for s in (where, restore, linux, other, save)]
        self.assertEqual(sorted(order), order)
        self.assertLess(self.steps.index(save), self.steps.index(self.step("name: The suite\n")))

    def test_a_leg_fails_over_its_skip_ceiling(self):
        suite = self.step("name: The suite\n")
        log = re.search(r'\| tee "(\$RUNNER_TEMP/[\w.]+)"\n', suite)
        self.assertIsNotNone(log, "the suite's output is kept")
        ceiling = self.step("tools/skip_ceiling.py")
        self.assertIn(f'tools/skip_ceiling.py "{log.group(1)}" --max ', ceiling)
        self.assertLess(self.steps.index(suite), self.steps.index(ceiling))


class TheDependencyUpdates(unittest.TestCase):

    def test_the_actions_and_both_tooling_folders_are_updated(self):
        path = REPO / ".github" / "dependabot.yml" if REPO else None
        if not (path and (REPO / ".github" / "workflows" / "ci.yml").is_file()):
            self.skipTest("the repository's workflows are not here")
        self.assertTrue(path.is_file(), ".github/dependabot.yml")
        text = path.read_text(encoding="utf-8")
        entries = re.findall(r"(?m)^  - package-ecosystem: (\S+)\n    directory: (\S+)$", text)
        self.assertEqual([("github-actions", "/"), ("npm", "/tooling/main"), ("npm", "/tooling/tailwind-v3")],
                         entries)
        self.assertIn("dependency-name: tailwindcss", text.split("/tooling/tailwind-v3", 1)[1])


@unittest.skipUnless(TOOLING, "needs the repository: release.yml and tooling/release sit outside the plugin")
class TheReleaseGate(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.gate = load(GATE, "wds_ci_gate") if GATE.is_file() else None

    def setUp(self):
        self.assertIsNotNone(self.gate, "tooling/release/ci_gate.py")

    def run_(self, name, conclusion="success", status="completed", id_=1, app="github-actions"):
        return {"id": id_, "name": name, "status": status, "conclusion": conclusion, "app": app}

    def passing(self):
        return [self.run_(name, id_=n) for n, name in enumerate(self.gate.REQUIRED, 1)]

    def test_the_required_jobs_are_ci_ymls(self):
        text = (REPO / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        oses = re.search(r"(?m)^\s+os: \[([^\]]+)\]$", text).group(1).split(", ")
        pythons = [p.strip('"') for p in re.search(r"(?m)^\s+python: \[([^\]]+)\]$", text).group(1).split(", ")]
        self.assertRegex(text, r"(?m)^    name: \$\{\{ matrix\.os \}\} · Python \$\{\{ matrix\.python \}\}$")
        validate = re.search(r"(?m)^  validate:\n    name: (.+)$", text).group(1)
        self.assertEqual({f"{o} · Python {p}" for o in oses for p in pythons} | {validate}, set(self.gate.REQUIRED))
        self.assertEqual(7, len(self.gate.REQUIRED))

    def test_a_commit_ci_passed_on_is_released(self):
        self.assertEqual([], self.gate.problems(self.passing()))

    def test_a_red_job_stops_it_unless_its_rerun_passed(self):
        name = self.gate.REQUIRED[0]
        runs = self.passing()
        runs[0] = self.run_(name, "failure", id_=50)
        self.assertEqual([f"{name}: failure"], self.gate.problems(runs))
        self.assertEqual([], self.gate.problems(runs + [self.run_(name, id_=51)]))       # the rerun
        self.assertEqual([f"{name}: failure"],
                         self.gate.problems([self.run_(name, id_=49)] + runs))           # an older pass

    def test_a_missing_or_unfinished_job_stops_it(self):
        runs = self.passing()
        missing, running = runs.pop(), runs.pop()
        runs.append(self.run_(running["name"], None, "in_progress", id_=99))
        found = self.gate.problems(runs)
        self.assertEqual(2, len(found), found)
        self.assertIn(f"{missing['name']}: no run on this commit", found)
        self.assertTrue(found[0].startswith(f"{running['name']}: still in_progress"), found)

    def test_only_ci_counts(self):
        """The release's own jobs and a review bot also report on the commit."""
        runs = self.passing() + [self.run_("release", None, "in_progress", id_=100),
                                 self.run_("CodeRabbit", "neutral", id_=101, app="coderabbitai")]
        self.assertEqual([], self.gate.problems(runs))
        name = self.gate.REQUIRED[1]
        self.assertIn(f"{name}: no run on this commit",
                      self.gate.problems([r for r in self.passing() if r["name"] != name]
                                         + [self.run_(name, id_=200, app="coderabbitai")]))

    def test_the_release_asks_before_it_builds(self):
        text = (REPO / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
        job = text.split("\n  distribute:", 1)[0]
        gate = job.index('tooling/release/ci_gate.py "$GITHUB_SHA"')
        self.assertLess(gate, job.index("tooling/release/build.py"))
        self.assertIn("GH_TOKEN: ${{ github.token }}", job[job.rindex("- name:", 0, gate):gate])
        self.assertRegex(text, r"(?m)^permissions:\n  contents: write\n  checks: read$")

    def test_a_check_run_it_cannot_read_exits_2(self):
        proc = subprocess.run([sys.executable, "-B", str(GATE), "0" * 40, "--repo", "Vybecode-LTD/none"],
                              capture_output=True, timeout=60, env=env(GH_TOKEN="not-a-token", PATH=""))
        self.assertEqual(2, proc.returncode, output(proc))
        self.assertIn("cannot read the check runs", output(proc))


class TheSkipCeiling(TempDirTest):

    def ceiling(self, log, most):
        path = self.write("suite.log", log)
        return subprocess.run([sys.executable, "-B", str(CEILING), str(path), "--max", str(most)],
                              capture_output=True, timeout=60, env=env())

    def test_a_leg_at_or_under_its_ceiling_passes(self):
        for log in ("Ran 9 tests in 1.0s\n\nOK (skipped=5)\n", "Ran 9 tests\r\n\r\nOK\r\n",
                    "OK (skipped=7)\nRan 9 tests\n\nOK (skipped=2)\n"):
            with self.subTest(log=log):
                proc = self.ceiling(log, 5)
                self.assertEqual(0, proc.returncode, output(proc))

    def test_a_leg_over_it_fails(self):
        proc = self.ceiling("Ran 1663 tests in 900s\n\nFAILED (failures=1, skipped=13)\n", 12)
        self.assertEqual(1, proc.returncode, output(proc))
        self.assertIn("13 tests skipped; this leg allows 12", output(proc))

    def test_a_log_with_no_summary_is_not_a_pass(self):
        proc = self.ceiling("Traceback (most recent call last):\n", 99)
        self.assertEqual(2, proc.returncode, output(proc))
        self.assertIn("has no unittest summary line", output(proc))


if __name__ == "__main__":
    unittest.main()
