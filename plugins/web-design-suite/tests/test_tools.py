"""The PR tools: tools/fail_before.py and tools/check.py.

fail_before.py runs against a fake repository of two commits, made in a
temporary folder: a fix, a control, a test that still fails, a regression, a
test with failing subtests, and a skipped one. check.py's choice of tests is
checked on its own, and its list of changed files against a fake repository.
Nothing is written into the plugin.
"""
from __future__ import annotations

import importlib.util
import pathlib
import shutil
import subprocess
import sys
import unittest

from wds_support import PLUGIN, TempDirTest, env, output

GIT = shutil.which("git")
TOOLS = PLUGIN / "tools"
GIT_ENV = {"GIT_AUTHOR_NAME": "wds-test", "GIT_AUTHOR_EMAIL": "wds-test@example.invalid",
           "GIT_COMMITTER_NAME": "wds-test", "GIT_COMMITTER_EMAIL": "wds-test@example.invalid",
           "GIT_AUTHOR_DATE": "2026-10-02T12:00:00Z", "GIT_COMMITTER_DATE": "2026-10-02T12:00:00Z"}

FAKE_TESTS = '''\
import os
import pathlib
import unittest

ROOT = pathlib.Path(os.environ.get("WDS_PLUGIN_ROOT") or pathlib.Path(__file__).resolve().parents[1])


def value():
    return (ROOT / "value.txt").read_text(encoding="utf-8").strip()


class Fake(unittest.TestCase):

    def test_fixed(self):
        self.assertEqual("2", value())

    def test_control(self):
        self.assertTrue((ROOT / "value.txt").exists())

    def test_still_failing(self):
        self.assertEqual("3", value())

    def test_regression(self):
        self.assertTrue((ROOT / "old.txt").exists())

    def test_subtests(self):
        for n in (1, 2, 3):
            with self.subTest(n=n):
                self.assertEqual("2", value())

    @unittest.skip("on purpose")
    def test_skipped(self):
        pass

    def test_the_root_and_its_commit_come_together(self):
        self.assertEqual("WDS_PLUGIN_ROOT" in os.environ, "WDS_PLUGIN_REV" in os.environ)


class FakeFixture(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        assert value() == "2", "the fixture needs the fix"

    def test_under_a_fixture_one(self):
        pass

    def test_under_a_fixture_two(self):
        pass
'''


def load_tool(name: str):
    spec = importlib.util.spec_from_file_location(f"wds_tool_{name}", TOOLS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@unittest.skipUnless(GIT, "needs git")
class FakeRepository(TempDirTest):

    def git(self, *args: str) -> str:
        proc = subprocess.run([GIT, *args], cwd=self.tmp, capture_output=True, env=env(**GIT_ENV))
        self.assertEqual(0, proc.returncode, output(proc))
        return proc.stdout.decode("utf-8").strip()

    def setUp(self):
        super().setUp()
        self.git("init", "-q")
        self.git("config", "core.autocrlf", "false")
        self.write("plugins/web-design-suite/value.txt", "1\n")
        self.write("plugins/web-design-suite/old.txt", "old\n")
        self.write("plugins/web-design-suite/tests/test_fake.py", FAKE_TESTS)
        self.git("add", ".")
        self.git("commit", "-q", "-m", "one")
        self.git("tag", "v0.1.0")
        self.first = self.git("rev-parse", "HEAD")
        self.write("plugins/web-design-suite/value.txt", "2\n")
        self.git("rm", "-q", "plugins/web-design-suite/old.txt")
        self.git("commit", "-q", "-am", "two")

    def files(self) -> list[str]:
        return sorted(str(p.relative_to(self.tmp)) for p in (self.tmp / "plugins").rglob("*"))


class FailBefore(FakeRepository):

    def fail_before(self, *args: str) -> tuple[subprocess.CompletedProcess, dict[str, tuple[str, str]]]:
        proc = subprocess.run([sys.executable, "-B", str(TOOLS / "fail_before.py"), *args], cwd=self.tmp,
                              capture_output=True, env=env(**GIT_ENV), timeout=300)
        rows = {}
        for line in proc.stdout.decode("utf-8").splitlines():
            cells = [c for c in line.split("  ") if c.strip()]
            if line.startswith("test_fake.") and len(cells) == 4:
                rows[cells[0].strip().rsplit(".", 1)[-1]] = (cells[1].strip(), cells[2].strip(), cells[3].strip())
        return proc, rows

    def test_each_verdict(self):
        before = self.files()
        proc, rows = self.fail_before("test_fake")
        self.assertEqual(1, proc.returncode, output(proc))      # two tests fail now
        self.assertEqual({
            "test_fixed": ("FAIL (1)", "ok", "fixed"),
            "test_control": ("ok", "ok", "control"),
            "test_still_failing": ("FAIL (1)", "FAIL (1)", "still failing"),
            "test_regression": ("ok", "FAIL (1)", "regression"),
            "test_subtests": ("FAIL (3)", "ok", "fixed"),
            "test_skipped": ("skipped", "skipped", "skipped"),
            "test_the_root_and_its_commit_come_together": ("ok", "ok", "control"),
            # A failing setUpClass counts against each test of its class.
            "test_under_a_fixture_one": ("FAIL (1)", "ok", "fixed"),
            "test_under_a_fixture_two": ("FAIL (1)", "ok", "fixed"),
        }, rows)
        self.assertIn("4 fixed, 2 controls, 1 still failing, 1 regressions, 1 skipped; against", output(proc))
        self.assertIn("before (v0.1.0)", output(proc))
        self.assertEqual(before, self.files())                  # no bytecode, no unpacked copy

    def test_a_revision_and_a_tests_prefix(self):
        proc, rows = self.fail_before("tests.test_fake.Fake.test_fixed", "test_fake.Fake.test_control",
                                      "--rev", self.first)
        self.assertEqual(0, proc.returncode, output(proc))
        self.assertEqual({"test_fixed": ("FAIL (1)", "ok", "fixed"), "test_control": ("ok", "ok", "control")}, rows)

    def test_a_revision_git_does_not_know(self):
        proc, _ = self.fail_before("test_fake", "--rev", "no-such-rev")
        self.assertEqual(2, proc.returncode, output(proc))
        self.assertIn("cannot read 'no-such-rev' from git", output(proc))


class CheckChoosesTheTests(unittest.TestCase):

    SOURCES = {
        "test_policies": 'run_py("content-model-to-ui", "scaffold_ui", ...)',
        "test_schema_sources": 'run_py("content-model-to-ui", "introspect_schema", ...)',
        "test_docs": "CHANGELOG.md, the README",
        "test_real_tools": "stylelint.config.mjs in web-design-studio",
        "test_skill_budget": "SKILL.md",
    }

    @classmethod
    def setUpClass(cls):
        cls.check = load_tool("check")

    def affected(self, *paths: str):
        return self.check.affected(list(paths), self.SOURCES)

    def test_a_changed_test_runs_itself(self):
        self.assertEqual(["test_tools"], self.affected("plugins/web-design-suite/tests/test_tools.py"))

    def test_a_script_runs_the_tests_that_name_its_skill_or_its_stem(self):
        self.assertEqual(["test_policies", "test_schema_sources"],
                         self.affected("plugins/web-design-suite/skills/content-model-to-ui/scripts/scaffold_ui.py"))

    def test_a_document_runs_the_tests_that_name_it(self):
        self.assertEqual(["test_docs"], self.affected("plugins/web-design-suite/CHANGELOG.md"))
        self.assertEqual([], self.affected("dev plans/web-design-suite-execution-plan.md"))

    def test_a_shared_file_runs_everything(self):
        for path in ("plugins/web-design-suite/tests/wds_support.py",
                     "plugins/web-design-suite/skills/web-design-studio/assets/rules/design-rules.json",
                     "plugins/web-design-suite/skills/web-design-studio/assets/configs/stylelint.config.mjs",
                     "plugins/web-design-suite/tools/check_pointers.py",
                     "tooling/main/package-lock.json"):
            with self.subTest(path=path):
                self.assertIsNone(self.affected(path))


class CheckReadsTheChanges(FakeRepository):

    def test_committed_staged_unstaged_and_untracked_with_their_whole_names(self):
        check = load_tool("check")
        self.write("plugins/web-design-suite/value.txt", "3\n")                    # unstaged
        self.write("dev plans/new plan.md", "x\n")                                  # untracked, with a space
        self.write("plugins/web-design-suite/tools/new.py", "x = 1\n")
        self.git("add", "plugins/web-design-suite/tools/new.py")                    # staged
        check.PLUGIN_ROOT = self.tmp / "plugins" / "web-design-suite"
        self.assertEqual(["dev plans/new plan.md", "plugins/web-design-suite/old.txt",
                          "plugins/web-design-suite/tools/new.py", "plugins/web-design-suite/value.txt"],
                         check.changed_files(self.first))


if __name__ == "__main__":
    unittest.main()
