"""Output encoding outside Claude Code.

Claude Code sets PYTHONIOENCODING=utf-8, but a terminal pipe, a git pre-commit
hook or a CI runner on Windows does not. Python then writes stdout in the ANSI
code page (cp1252), and any character outside it (→, Δ, ⚠, ✓) raised
UnicodeEncodeError and killed the gate with a traceback instead of a verdict.

H15 (the owner's audit of 2026-10-14): the test that ran every script's
`--help` proved nothing, since no script's help holds a non-ASCII byte. Every
entry script is now read for the reconfigure itself, with a control that
proves the scan fires, and the workflow commands' scripts are covered too.
check_roles.py and those five had no reconfigure: check_roles wrote its
verdict's dash as cp1252.
"""
from __future__ import annotations

import ast
import subprocess
import sys
import unittest
from pathlib import Path

from wds_support import PLUGIN, SKILLS, TempDirTest, env, output, run_py

OUTSIDE_CLAUDE_CODE = {"PYTHONIOENCODING": None, "PYTHONUTF8": None}
COMMANDS = PLUGIN / "workflow-commands"


def entry_scripts() -> list[Path]:
    """Every script a user or a command runs: the skills' and the workflow
    commands'. A library (no `__main__` block) is read, then left out."""
    return sorted([*SKILLS.glob("*/scripts/*.py"), *COMMANDS.glob("*/scripts/*.py")])


def writes_utf8(source: str) -> bool | None:
    """Whether the script's `__main__` block reconfigures stdout and stderr to
    UTF-8 before it calls main(). None for a script with no such block."""
    for node in ast.parse(source).body:
        if not (isinstance(node, ast.If) and isinstance(node.test, ast.Compare)
                and isinstance(node.test.left, ast.Name) and node.test.left.id == "__name__"):
            continue
        for stmt in node.body:
            calls = [n for n in ast.walk(stmt) if isinstance(n, ast.Call)]
            text = ast.dump(stmt)
            if any(isinstance(c.func, ast.Attribute) and c.func.attr == "reconfigure"
                   and any(k.arg == "encoding" and isinstance(k.value, ast.Constant)
                           and k.value.value == "utf-8" for k in c.keywords)
                   for c in calls) and "attr='stdout'" in text and "attr='stderr'" in text:
                return True
            if any(isinstance(c.func, ast.Name) and c.func.id == "main" for c in calls):
                return False
        return False
    return None


GOOD = ('import sys\n'
        'def main():\n    return 0\n'
        'if __name__ == "__main__":\n'
        '    for _stream in (sys.stdout, sys.stderr):\n'
        '        _stream.reconfigure(encoding="utf-8", errors="replace")\n'
        '    sys.exit(main())\n')


class Utf8Output(TempDirTest):

    def test_a11y_static_reports_a_heading_jump_without_crashing(self):
        page = self.write("page.html", '<!doctype html><html lang="en"><title>t</title>'
                                       "<main><h1>One</h1><h4>Four</h4></main></html>")
        proc = run_py("a11y-audit-runner", "a11y_static", page, cwd=self.tmp,
                      env_changes=OUTSIDE_CLAUDE_CODE)
        self.assertNotIn("UnicodeEncodeError", output(proc))
        self.assertIn("h1 → h4", proc.stdout.decode("utf-8"))

    def test_check_roles_writes_its_verdict_in_utf8(self):
        # Its verdict ends "— every declared pair clears its minimum."; on a
        # Windows pipe the dash went out as cp1252's 0x97.
        tokens = SKILLS / "web-design-studio" / "assets" / "starter" / "styles" / "tokens.css"
        proc = run_py("web-design-studio", "check_roles", tokens, cwd=self.tmp,
                      env_changes=OUTSIDE_CLAUDE_CODE)
        self.assertEqual(proc.returncode, 0, output(proc))
        self.assertIn("— every declared pair", proc.stdout.decode("utf-8"))

    def test_every_entry_script_writes_utf8(self):
        found = {path: writes_utf8(path.read_text(encoding="utf-8")) for path in entry_scripts()}
        entries = [path for path, verdict in found.items() if verdict is not None]
        self.assertGreaterEqual(len(entries), 28, sorted(p.name for p in entries))
        self.assertTrue(any(p.is_relative_to(COMMANDS) for p in entries))
        for path in entries:
            with self.subTest(script=str(path.relative_to(PLUGIN))):
                self.assertTrue(found[path], "its __main__ block must reconfigure stdout and "
                                             "stderr to UTF-8 before main()")

    def test_the_scan_fires(self):
        """The control: a script with no reconfigure, one that runs main()
        first, and one that reconfigures stdout alone all fail the scan."""
        self.assertTrue(writes_utf8(GOOD))
        self.assertFalse(writes_utf8(GOOD.replace('        _stream.reconfigure(encoding="utf-8", '
                                                  'errors="replace")\n', '        pass\n')))
        late = GOOD.replace("    sys.exit(main())\n", "")
        late = late.replace('if __name__ == "__main__":\n', 'if __name__ == "__main__":\n    main()\n')
        self.assertFalse(writes_utf8(late))
        self.assertFalse(writes_utf8(GOOD.replace("(sys.stdout, sys.stderr)", "(sys.stdout,)")))
        self.assertIsNone(writes_utf8("def helper():\n    return 1\n"))

    def test_every_script_writes_utf8_to_a_pipe(self):
        for script in entry_scripts():
            if writes_utf8(script.read_text(encoding="utf-8")) is None:
                continue
            with self.subTest(script=script.name):
                if script.is_relative_to(COMMANDS):
                    proc = subprocess.run([sys.executable, "-B", str(script), "--help"], cwd=self.tmp,
                                          env=env(**OUTSIDE_CLAUDE_CODE), capture_output=True, timeout=120)
                else:
                    proc = run_py(script.parent.parent.name, script.stem, "--help", cwd=self.tmp,
                                  env_changes=OUTSIDE_CLAUDE_CODE)
                self.assertEqual(proc.returncode, 0, output(proc))
                proc.stdout.decode("utf-8")      # raises if written in cp1252


if __name__ == "__main__":
    unittest.main()
