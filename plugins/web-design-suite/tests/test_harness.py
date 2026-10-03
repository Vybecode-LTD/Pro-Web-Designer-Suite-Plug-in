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
import os
import pathlib
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
        with open(pathlib.Path(holder.name) / "held.txt", "w", encoding="utf-8") as held:
            held.write("x")
            held.flush()
            holder.cleanup()


if __name__ == "__main__":
    unittest.main()
