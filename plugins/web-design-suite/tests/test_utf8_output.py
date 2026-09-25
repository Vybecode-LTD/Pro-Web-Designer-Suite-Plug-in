"""Output encoding outside Claude Code.

Claude Code sets PYTHONIOENCODING=utf-8, but a terminal pipe, a git pre-commit
hook or a CI runner on Windows does not. Python then writes stdout in the ANSI
code page (cp1252), and any character outside it (→, Δ, ⚠, ✓) raised
UnicodeEncodeError and killed the gate with a traceback instead of a verdict.
"""
from __future__ import annotations

import unittest

from wds_support import SKILLS, TempDirTest, output, run_py

OUTSIDE_CLAUDE_CODE = {"PYTHONIOENCODING": None, "PYTHONUTF8": None}


class Utf8Output(TempDirTest):

    def test_a11y_static_reports_a_heading_jump_without_crashing(self):
        page = self.write("page.html", '<!doctype html><html lang="en"><title>t</title>'
                                       "<main><h1>One</h1><h4>Four</h4></main></html>")
        proc = run_py("a11y-audit-runner", "a11y_static", page, cwd=self.tmp,
                      env_changes=OUTSIDE_CLAUDE_CODE)
        self.assertNotIn("UnicodeEncodeError", output(proc))
        self.assertIn("h1 → h4", proc.stdout.decode("utf-8"))

    def test_every_script_writes_utf8_to_a_pipe(self):
        for script in sorted(SKILLS.glob("*/scripts/*.py")):
            with self.subTest(script=script.name):
                proc = run_py(script.parent.parent.name, script.stem, "--help", cwd=self.tmp,
                              env_changes=OUTSIDE_CLAUDE_CODE)
                self.assertEqual(proc.returncode, 0, output(proc))
                proc.stdout.decode("utf-8")      # raises if written in cp1252


if __name__ == "__main__":
    unittest.main()
