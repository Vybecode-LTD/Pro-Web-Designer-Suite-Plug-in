"""The PR tools: tools/fail_before.py and tools/check.py.

fail_before.py runs against a fake repository of two commits, made in a
temporary folder: a fix, a control, a test that still fails, a regression, a
test with failing subtests, and a skipped one. check.py's choice of tests is
checked on its own, and its list of changed files against a fake repository.
Nothing is written into the plugin.
"""
from __future__ import annotations

import importlib.util
import io
import json
import pathlib
import shutil
import subprocess
import sys
import unittest
from unittest import mock

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


class CheckReportsOnAnyConsole(unittest.TestCase):

    def test_a_failure_prints_where_the_console_cannot_encode_it(self):
        # A failing check's output reached a cp1252 stdout (a redirect on
        # Windows) holding a character cp1252 has no byte for, and printing it
        # raised UnicodeEncodeError, so no report came at all.
        check = load_tool("check")
        failed = subprocess.CompletedProcess([], 1, "§ → café".encode("utf-8"), b"")
        out = io.TextIOWrapper(io.BytesIO(), encoding="cp1252", newline="\n")
        with mock.patch.object(check.subprocess, "run", return_value=failed), mock.patch.object(sys, "stdout", out):
            self.assertEqual(1, check.main(["--all"]))
            out.flush()
        report = out.buffer.getvalue().decode("cp1252")
        self.assertIn("--- check_pointers ---\n§ ? café\n", report)
        self.assertIn("FAIL  check_pointers", report)


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


class SyncRules(TempDirTest):
    """tools/sync_rules.py (N2): the spec's data written into the gates, on a
    copy of the three files in a temporary folder."""

    SPEC = "skills/web-design-studio/assets/rules/design-rules.json"
    GATES = ("skills/web-design-studio/scripts/audit_design.py",
             "skills/web-design-studio/assets/configs/stylelint.config.mjs",
             "skills/web-design-studio/assets/configs/eslint.design.config.mjs")

    def setUp(self):
        super().setUp()
        self.root = self.tmp / "plugin"
        for rel in (self.SPEC, *self.GATES):
            (self.root / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(PLUGIN / rel, self.root / rel)

    def sync(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, "-B", str(TOOLS / "sync_rules.py"), "--root", str(self.root), *args],
                              capture_output=True, env=env(), timeout=60)

    def gates(self) -> list[bytes]:
        return [(self.root / rel).read_bytes() for rel in self.GATES]

    def test_a_spec_change_is_stale_until_rewritten(self):
        spec = self.root / self.SPEC
        spec.write_bytes(spec.read_bytes().replace(b'"max_depth": 2,', b'"max_depth": 3,'))
        proc = self.sync("--check")
        self.assertEqual(1, proc.returncode, output(proc))
        for rel in self.GATES[:2]:                     # ESLint's block holds no nesting depth
            self.assertIn(f"stale: {rel}", output(proc))
        self.assertNotIn(f"stale: {self.GATES[2]}", output(proc))
        self.assertEqual(0, self.sync().returncode)
        audit, stylelint, _ = self.gates()
        self.assertIn(b"\nMAX_NESTING = 3\n", audit)
        self.assertIn(b"\nconst MAX_NESTING = 3;\n", stylelint)
        self.assertNotIn(b"\r\n", audit + stylelint)
        self.assertEqual(0, self.sync("--check").returncode)

    def test_the_audit_explains_the_limit_the_spec_sets(self):
        # The finding's message and its fix both name the generated limit, so a
        # spec change cannot leave the fix quoting the old one (#18's review).
        spec = self.root / self.SPEC
        spec.write_bytes(spec.read_bytes().replace(b'"max_depth": 2,', b'"max_depth": 3,'))
        self.assertEqual(0, self.sync().returncode)
        css = self.write("deep.css", "@layer components {\n.a { .b { .c { .d { .e { color: red; } } } } }\n}\n")
        proc = subprocess.run([sys.executable, "-B", str(self.root / self.GATES[0]), str(css), "--json",
                               "--law", "L5"], capture_output=True, env=env(), timeout=60)
        found = [f for f in json.loads(proc.stdout) if f["rule"] == "nesting-depth"]
        self.assertEqual(1, len(found), output(proc))
        self.assertIn("exceeds the limit of 3", found[0]["message"])
        self.assertIn("past depth 3 ", found[0]["fix"])

    def edit_spec(self, change) -> None:
        spec = self.root / self.SPEC
        data = json.loads(spec.read_text(encoding="utf-8"))
        change(data)
        spec.write_text(json.dumps(data), encoding="utf-8")

    def test_the_value_allowlists_are_written_from_the_spec(self):
        # N2, part 2: a family's values and the component margins are spec data.
        def change(spec):
            spec["values"]["families"]["spacing"]["allow"][2]["values"].insert(2, "auto")
            spec["margins_in_components"]["values"].remove("0 auto")
        self.edit_spec(change)
        self.assertEqual(0, self.sync().returncode)
        stylelint = self.gates()[1].decode("utf-8")
        self.assertIn("\n  gap: [VAR_SEQ, '0', 'auto', ...KEYWORDS],\n", stylelint)
        self.assertIn("\n  margin: ['0', 'auto', 'auto 0', CANCEL, ...KEYWORDS],\n", stylelint)
        self.assertEqual(0, self.sync("--check").returncode)

    def test_a_colour_function_reaches_the_audit_and_eslint(self):
        self.edit_spec(lambda spec: spec["values"]["colour_functions"].append("color-mix"))
        self.assertEqual(0, self.sync().returncode)
        audit, _, eslint = (text.split(b"BEGIN design-rules")[1].split(b"END design-rules")[0]
                            for text in self.gates())
        self.assertIn(b'"color-mix"', audit)
        self.assertIn(b"'color-mix'", eslint)
        css = self.write("mix.css", "@layer components {\n.a { color: color-mix(in oklch, red, blue); }\n}\n")
        proc = subprocess.run([sys.executable, "-B", str(self.root / self.GATES[0]), str(css), "--json"],
                              capture_output=True, env=env(), timeout=60)
        self.assertIn("raw-color", [f["rule"] for f in json.loads(proc.stdout)], output(proc))

    def test_a_name_the_spec_does_not_define_writes_nothing(self):
        self.edit_spec(lambda spec: spec["values"]["families"]["type"]["allow"][0]["values"].append("VAR_TYPO"))
        before = self.gates()
        proc = self.sync()
        self.assertEqual(1, proc.returncode, output(proc))
        self.assertIn("VAR_TYPO is neither a shape", output(proc))
        self.assertEqual(before, self.gates())

    def test_a_rewrite_of_a_tree_in_step_changes_nothing(self):
        before = self.gates()
        proc = self.sync()
        self.assertEqual(0, proc.returncode, output(proc))
        self.assertEqual("", proc.stdout.decode("utf-8"))
        self.assertEqual(before, self.gates())

    def test_a_gate_without_its_block_is_an_error(self):
        audit = self.root / self.GATES[0]
        audit.write_bytes(audit.read_bytes().replace(b"# BEGIN design-rules", b"# begin"))
        proc = self.sync("--check")
        self.assertEqual(1, proc.returncode, output(proc))
        self.assertIn("0 design-rules blocks, not one", output(proc))


if __name__ == "__main__":
    unittest.main()
