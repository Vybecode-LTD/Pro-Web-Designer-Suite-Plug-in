"""The suite's own harness: where the real-tool and browser tests find their tools.

Regressions covered (3.2.1 review):
- The toolchain defaults were written into os.environ at import, so every
  script the tests ran saw them, and seven modules each had their own copy of
  the lookup.
- "Set a variable to an empty string to switch its tests off" could not be
  done: cmd.exe and PowerShell delete a variable set to nothing, and the
  default came back; and where an empty value did survive, NODE_PATH turned the
  browser tests back on.
- A toolchain installed on Windows was used from WSL, where its native
  bindings cannot load, so tests errored instead of skipping.
- (CodeRabbit) A run from a git hook, or under `git -c`, passed GIT_DIR,
  GIT_INDEX_FILE and the like on to the tests' git commands: 19 subprocesses
  got no environment of their own, and the hook tests built theirs from
  os.environ, so `git init` and `git add` in a temporary folder would have
  gone to the hook's repository.

Regressions covered (3.3.0):
- The temporary folders and TempDirTest.write used
  `TemporaryDirectory(ignore_cleanup_errors=)` and `write_text(newline=)`,
  both Python 3.10+, so on 3.9 every test that used them errored.
  test_docs.PythonFloor runs this module on 3.9.
"""
from __future__ import annotations

import ast
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import unittest
from unittest import mock

import wds_support
from wds_support import PLUGIN, TempDirTest, env, installed_here, output, temp_dir, tool_modules, tool_roots

GIT = shutil.which("git")
SPAWN = {"run", "Popen", "call", "check_call", "check_output"}


class ToolLocations(TempDirTest):

    def folder(self, name: str, *packages: str) -> pathlib.Path:
        root = self.tmp / name
        for package in packages:
            (root / package).mkdir(parents=True)
        root.mkdir(exist_ok=True)
        return root

    def test_a_word_switches_the_tests_off(self):
        toolchain = self.folder("toolchain", "playwright")
        for value in ("off", "OFF", "0", "none", ""):
            with self.subTest(value=value), mock.patch.dict(os.environ, {"WDS_X": value,
                                                                         "NODE_PATH": str(toolchain)}):
                self.assertEqual([], tool_roots("WDS_X", toolchain, node_path=True))
                self.assertIsNone(tool_modules("WDS_X", "playwright", default=toolchain, node_path=True))

    def test_unset_falls_back_to_the_toolchain_then_node_path(self):
        toolchain = self.folder("toolchain", "stylelint")
        elsewhere = self.folder("elsewhere", "playwright")
        with mock.patch.dict(os.environ, {"NODE_PATH": str(elsewhere)}):
            os.environ.pop("WDS_X", None)                   # restored on exit
            self.assertEqual([str(toolchain.resolve())], tool_roots("WDS_X", toolchain))
            self.assertEqual([str(toolchain.resolve()), str(elsewhere.resolve())],
                             tool_roots("WDS_X", toolchain, node_path=True))
            self.assertEqual(str(elsewhere.resolve()),
                             tool_modules("WDS_X", "playwright", default=toolchain, node_path=True))

    def test_a_set_variable_wins_and_is_resolved(self):
        named = self.folder("named", "eslint")
        # Relative to a folder on the same drive: on a CI runner the checkout
        # is on D: and the temporary folder on C:, and relpath cannot cross.
        here = os.getcwd()
        os.chdir(named.parent)
        self.addCleanup(os.chdir, here)
        with mock.patch.dict(os.environ, {"WDS_X": os.path.relpath(named)}):
            self.assertEqual([str(named.resolve())], tool_roots("WDS_X", self.folder("toolchain", "eslint")))

    def test_a_toolchain_installed_for_another_platform_is_ignored(self):
        other = "linux" if sys.platform != "linux" else "win32"
        foreign = self.folder("foreign", f"lightningcss-{other}-x64", "lightningcss")
        native = self.folder("native", f"lightningcss-{sys.platform}-x64", "lightningcss")
        plain = self.folder("plain", "eslint")
        self.assertFalse(installed_here(foreign))
        self.assertTrue(installed_here(native))
        self.assertTrue(installed_here(plain))
        with mock.patch.dict(os.environ):
            os.environ.pop("WDS_X", None)
            self.assertEqual([], tool_roots("WDS_X", foreign))

    def test_the_harness_leaves_the_environment_alone(self):
        """Tool locations are looked up, never written into os.environ, so the
        scripts under test see only what the user set."""
        source = pathlib.Path(wds_support.__file__).read_text(encoding="utf-8")
        self.assertNotRegex(source, r"os\.environ\.(setdefault|update)\(|os\.environ\[[^\]]+\]\s*=")


class Subprocesses(unittest.TestCase):

    def test_env_leaves_out_gits_repository_variables(self):
        # The assertions compare names only: a failure must not print the
        # environment, which can hold tokens, into a log.
        inherited = {"GIT_DIR": "elsewhere/.git", "GIT_INDEX_FILE": "elsewhere/index", "GIT_EDITOR": "true"}
        with mock.patch.dict(os.environ, inherited):
            given = env()
            self.assertEqual(["GIT_EDITOR"], [name for name in inherited if name in given])
            self.assertEqual("true", given.get("GIT_EDITOR"))
            self.assertEqual("mine", env(GIT_DIR="mine").get("GIT_DIR"))

    @unittest.skipUnless(GIT, "needs git")
    def test_those_are_the_variables_git_names(self):
        proc = subprocess.run([GIT, "rev-parse", "--local-env-vars"], capture_output=True, env=env(), timeout=60)
        self.assertEqual(0, proc.returncode, output(proc))
        self.assertLessEqual(set(proc.stdout.decode("utf-8").split()), wds_support.GIT_REPOSITORY_VARIABLES)

    def test_every_subprocess_a_test_starts_gets_env(self):
        found = []
        for path in sorted((PLUGIN / "tests").glob("*.py")):
            for node in ast.walk(ast.parse(path.read_bytes())):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                if (isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name)
                        and func.value.id == "subprocess" and func.attr in SPAWN
                        and not any(k.arg == "env" for k in node.keywords)):
                    found.append(f"{path.name}:{node.lineno}: subprocess.{func.attr} without env=")
                if (isinstance(func, ast.Name) and func.id == "dict" and node.args
                        and ast.unparse(node.args[0]) == "os.environ"):
                    found.append(f"{path.name}:{node.lineno}: an environment built from os.environ")
        self.assertEqual([], found)


class NoBytecode(unittest.TestCase):

    def test_importing_the_helpers_turns_bytecode_off(self):
        """T7 (audit, 2026-10-14): only test_doc_snippets set the flag, part
        way through a run, so a hand run without -B could write __pycache__
        into the plugin through load_script, depending on module order."""
        clean = env()
        clean.pop("PYTHONDONTWRITEBYTECODE", None)
        proc = subprocess.run([sys.executable, "-c", "import sys, wds_support; print(sys.dont_write_bytecode)"],
                              cwd=pathlib.Path(__file__).parent, capture_output=True, env=clean, timeout=60)
        self.assertEqual(0, proc.returncode, output(proc))
        self.assertEqual("True", proc.stdout.decode("utf-8").strip())


class TempFolders(TempDirTest):

    def test_write_keeps_the_text_as_given(self):
        """LF stays LF on Windows: the byte-for-byte tests depend on it."""
        self.assertEqual(b"a {\n  color: red;\n}\n", self.write("a/b.css", "a {\n  color: red;\n}\n").read_bytes())
        self.assertEqual(b"\x00\r\n", self.write("c.bin", b"\x00\r\n").read_bytes())

    def test_cleanup_leaves_behind_what_it_cannot_delete(self):
        """A file still open cannot be deleted on Windows. Cleanup leaves it
        there instead of failing the test; POSIX simply deletes it."""
        holder = temp_dir("wds-held-")
        self.addCleanup(shutil.rmtree, holder.name, ignore_errors=True)
        path = pathlib.Path(holder.name) / "held.txt"
        with open(path, "w", encoding="utf-8") as held:
            held.write("x")
            held.flush()
            holder.cleanup()
            # TEST-16 (audit, 2026-10-28): it asserted only that cleanup did
            # not raise.
            if os.name == "nt":
                self.assertTrue(path.is_file(), "the held file is left behind")
            else:
                self.assertFalse(pathlib.Path(holder.name).exists(), "POSIX deletes it, open or not")


class NoBrowser(unittest.TestCase):
    """TEST-1 (P67): about 200 tests skip when no Chromium starts, and only
    the engine tests turned that into a failure, on Linux alone; a leg whose
    browser went missing printed OK with all of them skipped. Every such skip
    goes through wds_support.no_browser, which fails under
    WDS_REQUIRE_BROWSER, and CI sets it on every leg."""

    # A skip right under one of these conditions is a skip for a missing browser.
    CONDITION = re.compile(r'no usable|returncode == 3|b"browser"|rb"browser\|chromium"')
    OWN_SWITCH = {"test_runtime_engines.py": "WDS_REQUIRE_ENGINES",   # Firefox and WebKit, on Linux
                  "test_browser_scripts.py": None,                     # the resolution tests' own stubs
                  "test_harness.py": None}

    def test_it_skips_without_the_variable(self):
        with mock.patch.dict(os.environ, {"WDS_REQUIRE_BROWSER": ""}):
            with self.assertRaises(unittest.SkipTest):
                wds_support.no_browser(self, "no chromium here")

    def test_it_fails_with_it(self):
        with mock.patch.dict(os.environ, {"WDS_REQUIRE_BROWSER": "1"}):
            with self.assertRaises(self.failureException) as caught:
                wds_support.no_browser(self, "no chromium here")
        self.assertIn("no chromium here", str(caught.exception))

    def test_every_skip_for_a_missing_browser_goes_through_it(self):
        offenders, routed = [], 0
        for path in sorted((PLUGIN / "tests").glob("test_*.py")):
            if path.name in self.OWN_SWITCH:
                continue
            lines = path.read_text(encoding="utf-8").splitlines()
            routed += sum("no_browser(self, " in line for line in lines)
            for i, line in enumerate(lines):
                if "self.skipTest(" in line and ("no usable" in line or (i and self.CONDITION.search(lines[i - 1]))):
                    offenders.append(f"{path.name}:{i + 1}")
        self.assertEqual([], offenders)
        self.assertGreaterEqual(routed, 25)


class TimingEvidence(TempDirTest):
    """OPS-4 (P66): a red timing test said only that two lists differed, and a
    rerun measured again, so the numbers behind a failure were lost. The
    timing tests keep what they measured in WDS_EVIDENCE_DIR, which CI sets
    and uploads from a red leg."""

    def test_the_numbers_are_kept_where_the_variable_says(self):
        folder = self.tmp / "evidence"
        with mock.patch.dict(os.environ, {"WDS_EVIDENCE_DIR": str(folder)}):
            wds_support.keep_evidence(self, "vitals", {"lcp": 24})
        self.assertEqual({"lcp": 24}, json.loads((folder / f"{self.id()}.vitals.json").read_text(encoding="utf-8")))

    def test_nothing_is_written_without_it(self):
        with mock.patch.dict(os.environ, {"WDS_EVIDENCE_DIR": ""}):
            wds_support.keep_evidence(self, "vitals", {"lcp": 24})
        self.assertEqual([], list(self.tmp.iterdir()))

    def test_ci_sets_it_and_uploads_it_from_a_red_leg(self):
        from test_runtime_engines import ci_workflow
        text = ci_workflow()
        if text is None:
            self.skipTest("the repository's workflows are not here")
        steps = text.split("\n  validate:\n", 1)[0].split("\n      - ")
        [suite] = [s for s in steps if s.startswith("name: The suite\n")]
        self.assertRegex(suite, r"(?m)^\s+WDS_EVIDENCE_DIR: ", "the suite's step sets the folder")
        folder = re.search(r"(?m)^\s+WDS_EVIDENCE_DIR: (.+?)\s*$", suite).group(1)
        [upload] = [s for s in steps if "actions/upload-artifact@" in s]
        self.assertLess(steps.index(suite), steps.index(upload))
        self.assertRegex(upload, r"(?m)^\s+if: failure\(\)$")
        self.assertRegex(upload, rf"(?m)^\s+path: {re.escape(folder)}$")
        self.assertRegex(upload, r"(?m)^\s+retention-days: 7$")
        self.assertRegex(upload, r"uses: actions/upload-artifact@[0-9a-f]{40}\s")


if __name__ == "__main__":
    unittest.main()
