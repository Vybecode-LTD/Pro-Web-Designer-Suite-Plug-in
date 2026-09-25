"""web-design-studio: assets/configs/pre-commit-design-gate.sh, run for real.

Regressions covered:
- The hook called `python -m scripts.audit_design --staged ...`; audit_design
  has no --staged option, so argparse failed and every commit that touched a
  file was refused, clean or not.
- It ran `python3`, which on Windows is often the Microsoft Store placeholder:
  on PATH, but it only prints an install hint and fails — refusing the commit.
- It looked for scripts/audit_design.py even when DESIGN_GATE_AUDIT_MODULE
  pointed elsewhere, so the override silently skipped the audit.
"""
from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import sys
import unittest

from wds_support import SKILLS, TempDirTest

GIT = shutil.which("git")
HOOK = SKILLS / "web-design-studio" / "assets" / "configs" / "pre-commit-design-gate.sh"
TOKENS = (SKILLS / "web-design-studio" / "assets" / "starter" / "styles" / "tokens.css")


def find_sh():
    """A POSIX sh — on Windows the one Git ships, never WSL's bash.exe."""
    if os.name != "nt":
        return shutil.which("sh")
    if GIT:
        root = pathlib.Path(GIT).resolve().parents[1]           # ...\Git\cmd\git.exe
        for sh in (root / "bin" / "sh.exe", root / "usr" / "bin" / "sh.exe"):
            if sh.exists():
                return str(sh)
    return None


SH = find_sh()
PY = pathlib.Path(sys.executable).as_posix()


@unittest.skipUnless(GIT and SH, "git and a POSIX sh are needed to run the hook")
class PreCommitHook(TempDirTest):

    def setUp(self):
        super().setUp()
        self.repo = self.tmp / "repo"
        self.repo.mkdir()
        subprocess.run([GIT, "init", "-q", str(self.repo)], check=True, capture_output=True)
        shutil.copytree(SKILLS / "web-design-studio" / "scripts", self.repo / "scripts",
                        ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copy(TOKENS, self.repo / "tokens.css")

    def stage(self, rel, text):
        path = self.repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        subprocess.run([GIT, "-C", str(self.repo), "add", rel], check=True, capture_output=True)

    def run_hook(self, **env_changes):
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        env.pop("DESIGN_GATE_BYPASS", None)
        env.update({"DESIGN_GATE_PYTHON": PY, **env_changes})
        env = {k: v for k, v in env.items() if v is not None}
        proc = subprocess.run([SH, str(HOOK)], cwd=self.repo, env=env, capture_output=True, timeout=180)
        return proc.returncode, (proc.stdout + proc.stderr).decode("utf-8", "replace")

    def test_a_clean_change_is_allowed(self):
        self.stage("components/card.css",
                   "@layer components {\n  .card { padding: var(--pad-card); }\n}\n")
        code, out = self.run_hook()
        self.assertNotIn("unrecognized arguments", out)
        self.assertEqual(code, 0, out)

    def test_a_violation_is_refused_by_the_audit_itself(self):
        self.stage("components/card.css", "@layer components {\n  .card { padding: 13px; }\n}\n")
        code, out = self.run_hook()
        self.assertEqual(code, 1, out)
        self.assertIn("13px", out)
        self.assertNotIn("unrecognized arguments", out)

    def test_a_broken_python3_placeholder_is_skipped(self):
        bin_dir = self.tmp / "bin"
        bin_dir.mkdir()
        fake = bin_dir / "python3"
        fake.write_text("#!/bin/sh\necho 'Python was not found; run without arguments to "
                        "install from the Microsoft Store'\nexit 9009\n", encoding="utf-8", newline="\n")
        real = bin_dir / "python"
        real.write_text(f'#!/bin/sh\nexec "{PY}" "$@"\n', encoding="utf-8", newline="\n")
        for f in (fake, real):
            f.chmod(0o755)
        self.stage("components/card.css",
                   "@layer components {\n  .card { padding: var(--pad-card); }\n}\n")
        code, out = self.run_hook(DESIGN_GATE_PYTHON=None,
                                  PATH=str(bin_dir) + os.pathsep + os.environ["PATH"])
        self.assertNotIn("Microsoft Store", out)
        self.assertEqual(code, 0, out)

    def test_the_audit_module_override_is_honoured(self):
        shutil.move(str(self.repo / "scripts"), str(self.repo / "tools"))
        self.stage("components/card.css", "@layer components {\n  .card { padding: 13px; }\n}\n")
        code, out = self.run_hook(DESIGN_GATE_AUDIT_MODULE="tools.audit_design")
        self.assertNotRegex(out, r"audit_design(\.py)? not found")
        self.assertEqual(code, 1, out)
        self.assertIn("13px", out)


if __name__ == "__main__":
    unittest.main()
