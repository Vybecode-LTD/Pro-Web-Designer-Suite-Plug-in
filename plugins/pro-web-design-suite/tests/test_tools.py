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
import re
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

    def test_needs_what_the_fix_adds(self):
        self.assertEqual("new", (ROOT / "new.txt").read_text(encoding="utf-8").strip())

    def test_errors_now(self):
        if value() == "2":
            raise KeyError("only with the fix →")

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
        self.write("plugins/pro-web-design-suite/value.txt", "1\n")
        self.write("plugins/pro-web-design-suite/old.txt", "old\n")
        self.write("plugins/pro-web-design-suite/tests/test_fake.py", FAKE_TESTS)
        self.git("add", ".")
        self.git("commit", "-q", "-m", "one")
        self.git("tag", "v0.1.0")
        self.first = self.git("rev-parse", "HEAD")
        self.write("plugins/pro-web-design-suite/value.txt", "2\n")
        self.write("plugins/pro-web-design-suite/new.txt", "new\n")
        self.git("add", "plugins/pro-web-design-suite/new.txt")
        self.git("rm", "-q", "plugins/pro-web-design-suite/old.txt")
        self.git("commit", "-q", "-am", "two")

    def files(self) -> list[str]:
        return sorted(str(p.relative_to(self.tmp)) for p in (self.tmp / "plugins").rglob("*"))


class FailBefore(FakeRepository):

    def fail_before(self, *args: str, encoding: str = "utf-8") -> tuple[
            subprocess.CompletedProcess, dict[str, tuple[str, ...]], dict[str, list[str]]]:
        """The run, its rows by test name (before, now, errors, verdict), and
        the lines printed under each row."""
        proc = subprocess.run([sys.executable, "-B", str(TOOLS / "fail_before.py"), *args], cwd=self.tmp,
                              capture_output=True, env=env(**GIT_ENV, PYTHONIOENCODING=encoding), timeout=300)
        lines = proc.stdout.decode(encoding).splitlines()
        rows, why, name = {}, {}, None
        dashes = next((i for i, line in enumerate(lines) if line.startswith("----")), len(lines))
        starts = [m.start() for m in re.finditer(r"-+", lines[dashes])] if dashes < len(lines) else []
        for line in lines[dashes + 1:]:
            if line.startswith("test_fake."):
                cells = [line[a:b].strip() for a, b in zip(starts, [*starts[1:], None])]
                name = cells[0].rsplit(".", 1)[-1]
                rows[name] = tuple(cells[1:])
            elif line.startswith("    ") and name:
                why.setdefault(name, []).append(line.strip())
        return proc, rows, why

    def test_each_verdict(self):
        before = self.files()
        proc, rows, why = self.fail_before("test_fake")
        self.assertEqual(1, proc.returncode, output(proc))      # three tests fail now
        self.assertEqual({
            "test_fixed": ("FAIL (1)", "ok", "", "fixed"),
            "test_control": ("ok", "ok", "", "control"),
            "test_still_failing": ("FAIL (1)", "FAIL (1)", "", "still failing"),
            "test_regression": ("ok", "FAIL (1)", "", "regression"),
            "test_subtests": ("FAIL (3)", "ok", "", "fixed"),
            # TEST-4 (audit, 2026-10-28): a test that cannot run on the old
            # tree, here for a file only the fix adds, read "fixed".
            "test_needs_what_the_fix_adds": ("error", "ok", "before 1", "fixed?"),
            "test_errors_now": ("ok", "error", "now 1", "regression"),
            "test_skipped": ("skipped", "skipped", "", "skipped"),
            "test_the_root_and_its_commit_come_together": ("ok", "ok", "", "control"),
            # A failing setUpClass is an error against each test of its class.
            "test_under_a_fixture_one": ("error", "ok", "before 1", "fixed?"),
            "test_under_a_fixture_two": ("error", "ok", "before 1", "fixed?"),
        }, rows)
        self.assertIn("2 fixed, 3 fixed? (an error before), 2 controls, 1 still failing, 2 regressions, 1 skipped;"
                      " against", output(proc))
        self.assertIn("before (v0.1.0)", output(proc))
        # Each failure and error says why, by run, once however many subtests.
        self.assertEqual(["before: FAIL AssertionError: '2' != '1'"], why["test_fixed"])
        self.assertEqual(["before: FAIL AssertionError: '2' != '1'"], why["test_subtests"])
        self.assertEqual(1, len(why["test_needs_what_the_fix_adds"]))
        self.assertRegex(why["test_needs_what_the_fix_adds"][0], r"^before: ERROR FileNotFoundError: .*new\.txt")
        self.assertEqual(["now: ERROR KeyError: 'only with the fix →'"], why["test_errors_now"])
        self.assertEqual(["before: ERROR AssertionError: the fixture needs the fix"], why["test_under_a_fixture_one"])
        self.assertNotIn("test_control", why)
        self.assertEqual(before, self.files())                  # no bytecode, no unpacked copy

    def test_a_revision_and_a_tests_prefix(self):
        proc, rows, _ = self.fail_before("tests.test_fake.Fake.test_fixed", "test_fake.Fake.test_control",
                                         "--rev", self.first)
        self.assertEqual(0, proc.returncode, output(proc))
        self.assertEqual({"test_fixed": ("FAIL (1)", "ok", "", "fixed"),
                          "test_control": ("ok", "ok", "", "control")}, rows)

    def test_a_reason_prints_on_a_console_without_its_characters(self):
        """A reason quotes the test's message; cp1252 has no byte for →."""
        proc, rows, why = self.fail_before("test_fake.Fake.test_errors_now", encoding="cp1252")
        self.assertEqual(1, proc.returncode, output(proc))
        self.assertEqual({"test_errors_now": ("ok", "error", "now 1", "regression")}, rows)
        self.assertEqual(["now: ERROR KeyError: 'only with the fix ?'"], why["test_errors_now"])

    def test_a_revision_git_does_not_know(self):
        proc, _, _ = self.fail_before("test_fake", "--rev", "no-such-rev")
        self.assertEqual(2, proc.returncode, output(proc))
        self.assertIn("cannot read 'no-such-rev' from git", output(proc))


class FailBeforeAcrossTheRename(FailBefore):
    """Codex on #180: 4.0.0 moved the plugin to plugins/pro-web-design-suite,
    and 3.6.0, the release a fix is shown failing on, holds only
    plugins/web-design-suite, so `git archive` of the new path failed before
    either run. Every FailBefore test runs again, with the tag before the move."""

    def setUp(self):
        TempDirTest.setUp(self)
        old, new = "plugins/web-design-suite", "plugins/pro-web-design-suite"
        self.git("init", "-q")
        self.git("config", "core.autocrlf", "false")
        self.write(f"{old}/value.txt", "1\n")
        self.write(f"{old}/old.txt", "old\n")
        self.write(f"{old}/tests/test_fake.py", FAKE_TESTS)
        self.git("add", ".")
        self.git("commit", "-q", "-m", "one, before the rename")
        self.git("tag", "v0.1.0")
        self.first = self.git("rev-parse", "HEAD")
        self.git("mv", old, new)
        self.write(f"{new}/value.txt", "2\n")
        self.write(f"{new}/new.txt", "new\n")
        self.git("add", f"{new}/new.txt")
        self.git("rm", "-q", "--cached", f"{new}/old.txt")
        (self.tmp / new / "old.txt").unlink()
        self.git("commit", "-q", "-am", "two, renamed")


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

    def test_a_changed_test_runs_itself_and_the_tests_that_read_every_test(self):
        """#230: a loop with no subTest in a new test passed check.py and failed
        CI's six legs, since test_static_checks reads every module by glob."""
        self.assertEqual(["test_harness", "test_static_checks", "test_tools"],
                         self.affected("plugins/pro-web-design-suite/tests/test_tools.py"))

    def test_a_script_runs_the_tests_that_name_its_skill_or_its_stem(self):
        self.assertEqual(["test_policies", "test_release_build.TheDirectoryChecks", "test_schema_sources"],
                         self.affected("plugins/pro-web-design-suite/skills/content-model-to-ui/scripts/scaffold_ui.py"))

    def test_a_document_runs_the_tests_that_name_it(self):
        self.assertEqual(["test_docs", "test_release_build.TheDirectoryChecks"],
                         self.affected("plugins/pro-web-design-suite/CHANGELOG.md"))
        self.assertEqual([], self.affected("dev plans/web-design-suite-execution-plan.md"))

    def test_a_folder_read_by_glob_runs_the_tests_that_read_it(self):
        """TEST-2, PY-E-9 (audit, 2026-10-28): four of the six agents, and
        /new-system and /release-check, selected no test, since the tests that
        check them read their folder and never spell the file."""
        P, directory = "plugins/pro-web-design-suite/", "test_release_build.TheDirectoryChecks"
        for path, want in (
                ("agents/gate-runner.md", ["test_agents", "test_pointers", directory]),
                ("workflow-commands/new-system/scripts/new_system.py", ["test_commands", "test_pointers", directory]),
                ("workflow-commands/deck/SKILL.md", ["test_commands", "test_deck", "test_pointers", directory,
                                                     "test_skill_budget"]),
                ("hooks/hooks.json", ["test_hooks", directory]),
                ("mcp/design_gates.mjs", ["test_mcp", directory]),
                ("evals/routing/web-design-studio/graders/fires.md", ["test_evals"]),
                ("SECURITY.md", [directory]),
                (".claude-plugin/pro-web-design-suite-icon.png", [directory, "test_release_build.TheListingIcon"])):
            with self.subTest(path=path):
                self.assertEqual(want, self.affected(P + path))

    def test_a_reference_runs_the_snippet_and_pointer_tests(self):
        """TEST-3: a CSS block in eleven skills' references ran neither the
        audit on the references' snippets nor stylelint and ESLint on them."""
        snippets = ["test_doc_snippets", "test_pointers",
                    "test_real_tools.DesignEslintConfig.test_the_references_tsx_snippets_pass_the_design_config",
                    "test_real_tools.StylelintConfig.test_the_references_css_snippets_pass_the_config"]
        for path in ("skills/perf-budget-gate/references/budgets.md", "skills/figma-variables-sync/SKILL.md"):
            with self.subTest(path=path):
                found = self.affected("plugins/pro-web-design-suite/" + path)
                self.assertEqual([], [t for t in snippets if t not in found], found)
        # A module that runs whole takes the place of its tests.
        self.assertIn("test_real_tools",
                      self.affected("plugins/pro-web-design-suite/skills/web-design-studio/references/x.md"))
        self.assertNotIn("test_real_tools.StylelintConfig.test_the_references_css_snippets_pass_the_config",
                         self.affected("plugins/pro-web-design-suite/skills/web-design-studio/references/x.md"))

    def test_a_shared_file_runs_everything(self):
        for path in ("plugins/pro-web-design-suite/tests/wds_support.py",
                     "plugins/pro-web-design-suite/skills/web-design-studio/assets/rules/design-rules.json",
                     "plugins/pro-web-design-suite/skills/web-design-studio/assets/configs/stylelint.config.mjs",
                     "plugins/pro-web-design-suite/tools/check_pointers.py",
                     "tooling/main/package-lock.json"):
            with self.subTest(path=path):
                self.assertIsNone(self.affected(path))


class CheckCoversEveryFile(unittest.TestCase):
    """TEST-2's other half: with the suite's own sources, every file of the
    plugin under test but its tests and tools selects a test, and every test
    it selects exists."""

    @classmethod
    def setUpClass(cls):
        cls.check = load_tool("check")
        # Not this module: it spells the paths it hands check.py, and would
        # select itself for them.
        cls.sources = {p.stem: p.read_text(encoding="utf-8", errors="replace")
                       for p in sorted(pathlib.Path(__file__).resolve().parent.glob("test_*.py"))
                       if p.stem != "test_tools"}

    def files(self):
        for path in sorted(PLUGIN.rglob("*")):
            rel = path.relative_to(PLUGIN).as_posix()
            if path.is_file() and rel.split("/")[0] not in ("tests", "tools") \
                    and not {"__pycache__", "node_modules"} & set(rel.split("/")):
                yield rel

    def test_every_file_selects_a_test(self):
        def selected(rel):                      # None is the whole suite
            found = self.check.affected([self.check.IN_REPO + rel], self.sources)
            return ["the whole suite"] if found is None else [m for m in found if m != "test_skill_budget"]
        self.assertEqual([], [rel for rel in self.files() if not selected(rel)])

    def test_every_test_it_selects_exists(self):
        named = {m for rel in self.files() for m in self.check.affected([self.check.IN_REPO + rel], self.sources) or []}
        for test in sorted(named):
            module, *rest = test.split(".")
            with self.subTest(test=test):
                self.assertIn(module, self.sources)
                for name in rest:
                    self.assertRegex(self.sources[module], rf"\n\s*(?:class|def) {re.escape(name)}\b")


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
        self.write("plugins/pro-web-design-suite/value.txt", "3\n")                    # unstaged
        self.write("dev plans/new plan.md", "x\n")                                  # untracked, with a space
        self.write("plugins/pro-web-design-suite/tools/new.py", "x = 1\n")
        self.git("add", "plugins/pro-web-design-suite/tools/new.py")                    # staged
        check.PLUGIN_ROOT = self.tmp / "plugins" / "pro-web-design-suite"
        self.assertEqual(["dev plans/new plan.md", "plugins/pro-web-design-suite/new.txt",
                          "plugins/pro-web-design-suite/old.txt",
                          "plugins/pro-web-design-suite/tools/new.py", "plugins/pro-web-design-suite/value.txt"],
                         check.changed_files(self.first))


class SyncRules(TempDirTest):
    """tools/sync_rules.py (N2): the spec's data written into the gates, on a
    copy of the three files in a temporary folder."""

    SPEC = "skills/web-design-studio/assets/rules/design-rules.json"
    GATES = ("skills/web-design-studio/scripts/audit_design.py",
             "skills/web-design-studio/assets/configs/stylelint.config.mjs",
             "skills/web-design-studio/assets/configs/eslint.design.config.mjs")
    # Not a gate, but sync_rules writes Law 6's lists into it (LC-A19).
    READERS = ("skills/design-system-docs/scripts/extract_system.py",)

    def setUp(self):
        super().setUp()
        self.root = self.tmp / "plugin"
        for rel in (self.SPEC, *self.GATES, *self.READERS):
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
            with self.subTest(rel=rel):
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
            spec["margins_in_components"]["values"][0:1] = ["0", "auto"]      # a shape becomes two values
        self.edit_spec(change)
        self.assertEqual(0, self.sync().returncode)
        stylelint = self.gates()[1].decode("utf-8")
        self.assertIn("\n  gap: [VAR_SEQ, '0', 'auto', ...KEYWORDS],\n", stylelint)
        self.assertIn("\n  margin: ['0', 'auto', CANCEL, ...KEYWORDS],\n", stylelint)
        self.assertIn('\nMARGIN_VALUES = ("0", "auto", CANCEL, *KEYWORDS)\n', self.gates()[0].decode("utf-8"))
        self.assertEqual(0, self.sync("--check").returncode)

    def test_a_colour_function_reaches_the_gates(self):
        # SB-A15: stylelint reads the list too (design/no-literal-colour-function).
        self.edit_spec(lambda spec: spec["values"]["colour_functions"].append("device-cmyk"))
        self.assertEqual(0, self.sync().returncode)
        audit, stylelint, eslint = (text.split(b"BEGIN design-rules")[1].split(b"END design-rules")[0]
                                    for text in self.gates())
        self.assertIn(b'"device-cmyk"', audit)
        self.assertIn(b"'device-cmyk'", stylelint)
        self.assertIn(b"'device-cmyk'", eslint)
        css = self.write("mix.css", "@layer components {\n.a { color: device-cmyk(0 81% 81% 30%); }\n}\n")
        proc = subprocess.run([sys.executable, "-B", str(self.root / self.GATES[0]), str(css), "--json"],
                              capture_output=True, env=env(), timeout=60)
        self.assertIn("raw-color", [f["rule"] for f in json.loads(proc.stdout)], output(proc))

    def test_a_new_shape_is_written_before_the_allowlist_that_reads_it(self):
        # #19's review: a shape the spec added and a family used was named in
        # the allowlist but never declared, so the config could not load while
        # --check passed.
        def change(spec):
            spec["values"]["shapes"]["PERCENT"] = {"pattern": "^\\d+%$", "means": "a percentage"}
            spec["values"]["families"]["sizing"]["allow"][0]["values"].insert(-1, "PERCENT")
        self.edit_spec(change)
        self.assertEqual(0, self.sync().returncode)
        stylelint = self.gates()[1].decode("utf-8")
        declared = stylelint.find("\nconst PERCENT = String.raw`/^\\d+%$/`;\n")
        self.assertGreater(declared, 0)
        self.assertLess(declared, stylelint.index("\nconst VALUE_ALLOWLIST = {\n"))
        self.assertIn("\n  'max-width': [VAR_ONE, 'none', '100%', 'max-content', 'min-content', 'fit-content', "
                      "PERCENT, ...KEYWORDS],\n", stylelint)
        # The audit reads the sizing family too, so its block declares the shape as well.
        audit = self.gates()[0].decode("utf-8")
        self.assertLess(audit.index('\nPERCENT = re.compile(r"^\\d+%$")\n'), audit.index("\nSIZING_VALUES = {\n"))

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
