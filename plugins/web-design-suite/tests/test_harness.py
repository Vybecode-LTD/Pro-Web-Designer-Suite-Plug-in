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
"""
from __future__ import annotations

import os
import pathlib
import sys
import unittest
from unittest import mock

import wds_support
from wds_support import TempDirTest, installed_here, tool_modules, tool_roots


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


if __name__ == "__main__":
    unittest.main()
