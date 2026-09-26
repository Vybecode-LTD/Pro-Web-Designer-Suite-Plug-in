"""web-design-studio: assets/configs/pre-commit-design-gate.sh, run for real.

Regressions covered:
- The hook called `python -m scripts.audit_design --staged ...`; audit_design
  has no --staged option, so argparse failed and every commit that touched a
  file was refused, clean or not.
- It ran `python3`, which on Windows is often the Microsoft Store placeholder:
  on PATH, but it only prints an install hint and fails — refusing the commit.
- It looked for scripts/audit_design.py even when DESIGN_GATE_AUDIT_MODULE
  pointed elsewhere, so the override silently skipped the audit.

3.1.0:
- GT-A4: the accessibility floor had no place in the shipped hook, so
  a11y-audit-runner's SKILL.md taught an inline snippet with no shebang (Git
  for Windows cannot run it) and no `set -e` (a design-audit failure was
  ignored when a11y_static passed). The shipped hook now runs a11y_static on
  the staged files whenever scripts/a11y_static.py is vendored.
- SB-A16: every staged file went to audit_design, which read a README.md as
  JavaScript and refused the commit over an example in prose.
"""
from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import sys
import unittest

from wds_support import SKILLS, TempDirTest, env

GIT = shutil.which("git")
HOOK = SKILLS / "web-design-studio" / "assets" / "configs" / "pre-commit-design-gate.sh"
TOKENS = (SKILLS / "web-design-studio" / "assets" / "starter" / "styles" / "tokens.css")


def find_sh():
    """A POSIX sh — on Windows the one Git ships, never WSL's bash.exe."""
    if os.name != "nt":
        return shutil.which("sh")
    if GIT:
        # ...\Git\cmd\git.exe from cmd/PowerShell; ...\Git\mingw64\bin\git.exe
        # from Git Bash, one level deeper.
        for root in pathlib.Path(GIT).resolve().parents[1:3]:
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
        subprocess.run([GIT, "init", "-q", str(self.repo)], check=True, capture_output=True, env=env())
        shutil.copytree(SKILLS / "web-design-studio" / "scripts", self.repo / "scripts",
                        ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copy(TOKENS, self.repo / "tokens.css")

    def stage(self, rel, text):
        path = self.repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        subprocess.run([GIT, "-C", str(self.repo), "add", rel], check=True, capture_output=True, env=env())

    def run_hook(self, **env_changes):
        # stylelint is not installed here, so the CSS stage may skip. The tests
        # about a missing config pass DESIGN_GATE_ALLOW_SKIP=None.
        hook_env = env(**{"DESIGN_GATE_BYPASS": None, "DESIGN_GATE_PYTHON": PY, "DESIGN_GATE_ALLOW_SKIP": "1",
                          **env_changes})
        proc = subprocess.run([SH, str(HOOK)], cwd=self.repo, env=hook_env, capture_output=True, timeout=180)
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

    def vendor_a11y(self):
        shutil.copy(SKILLS / "a11y-audit-runner" / "scripts" / "a11y_static.py",
                    self.repo / "scripts" / "a11y_static.py")

    def test_the_accessibility_floor_runs_when_vendored(self):
        self.vendor_a11y()
        self.stage("site/index.html", '<!doctype html><html lang="en"><title>t</title>'
                                      '<main><img src="hero.png"></main></html>\n')
        code, out = self.run_hook()
        self.assertEqual(code, 1, out)
        self.assertIn("a11y_static", out)
        self.assertIn("img-no-alt", out)

    def test_both_gates_must_pass(self):
        self.vendor_a11y()
        self.stage("components/card.css", "@layer components {\n  .card { padding: 13px; }\n}\n")
        self.stage("site/index.html", '<!doctype html><html lang="en"><title>t</title>'
                                      '<main><h1>Clean</h1></main></html>\n')
        code, out = self.run_hook()
        self.assertEqual(code, 1, out)                  # the design audit still refuses
        self.assertIn("13px", out)

    def lightened_tokens(self) -> str:
        """The starter's tokens with --neutral-500 lifted from L 53.5% to 60%:
        --fg-subtle then fails 4.5:1 on the sunken well."""
        css = TOKENS.read_text(encoding="utf-8")
        lifted = css.replace("--neutral-500: oklch(53.5%", "--neutral-500: oklch(60%", 1)
        self.assertNotEqual(css, lifted)
        return lifted

    def test_role_pairs_are_checked_when_a_tokens_file_is_staged(self):
        """SS-C2: check_roles runs in the hook, once vendored (the harness
        vendors every studio script)."""
        self.stage("styles/tokens.css", self.lightened_tokens())
        code, out = self.run_hook()
        self.assertEqual(code, 1, out)
        self.assertIn("check_roles", out)
        self.assertIn("--fg-subtle on --bg-sunken", out)

    def test_the_starters_palette_passes_the_role_stage(self):
        self.stage("styles/tokens.css", TOKENS.read_text(encoding="utf-8"))
        code, out = self.run_hook()
        self.assertEqual(code, 0, out)

    def test_the_role_stage_is_opt_in(self):
        (self.repo / "scripts" / "check_roles.py").unlink(missing_ok=True)
        self.stage("styles/tokens.css", self.lightened_tokens())
        code, out = self.run_hook()
        self.assertEqual(code, 0, out)
        self.assertNotIn("check_roles", out)

    def test_a_staged_readme_does_not_block_the_commit(self):
        self.vendor_a11y()
        self.stage("README.md", 'Avoid <div className="p-[13px]"> and <img src="x.png">.\n')
        code, out = self.run_hook()
        self.assertEqual(code, 0, out)

    # --- 3.2.0: SB-C7, SB-A16 (b)-(e) -----------------------------------------

    def test_a_missing_stylelint_config_fails_unless_skipping_is_allowed(self):
        """(b) The default path, assets/configs/, is not in the canonical tree,
        and a missing config was a silent SKIPPED that let the commit through."""
        self.stage("components/card.css", "@layer components {\n  .card { padding: var(--pad-card); }\n}\n")
        code, out = self.run_hook(DESIGN_GATE_ALLOW_SKIP=None)
        self.assertEqual(code, 1, out)
        self.assertIn("stylelint config", out)
        code, out = self.run_hook(DESIGN_GATE_ALLOW_SKIP="1")
        self.assertEqual(code, 0, out)
        self.assertIn("SKIPPED", out)

    def test_a_missing_audit_fails_unless_skipping_is_allowed(self):
        (self.repo / "scripts" / "audit_design.py").unlink()
        self.stage("site/index.html", '<!doctype html><html lang="en"><title>t</title>'
                                      '<main><h1>Hi</h1></main></html>\n')
        code, out = self.run_hook(DESIGN_GATE_ALLOW_SKIP=None)
        self.assertEqual(code, 1, out)
        self.assertIn("audit_design", out)

    def stub_npx(self):
        bin_dir = self.tmp / "stub-bin"
        bin_dir.mkdir(exist_ok=True)
        npx = bin_dir / "npx"
        npx.write_text('#!/bin/sh\nprintf "%s\\n" "$@" >> "$NPX_LOG"\nexit 0\n',
                       encoding="utf-8", newline="\n")
        npx.chmod(0o755)
        return bin_dir

    def test_eslint_is_not_failed_by_a_file_it_ignores(self):
        """(c) --max-warnings 0 turned "File ignored because of a matching
        ignore pattern" into a refused commit."""
        bin_dir = self.stub_npx()
        log = self.tmp / "npx.log"
        self.stage("src/Card.tsx", "export const Card = () => <div className=\"p-card\" />;\n")
        code, out = self.run_hook(PATH=str(bin_dir) + os.pathsep + os.environ["PATH"],
                                  NPX_LOG=str(log))
        self.assertEqual(code, 0, out)
        args = log.read_text(encoding="utf-8").split("\n")
        self.assertIn("eslint", args)
        self.assertIn("--no-warn-ignored", args)

    def test_a_linked_worktree_logs_the_bypass_in_the_shared_git_dir(self):
        """(d) In a linked worktree .git is a file: the log write failed with
        "Not a directory" and the hook still said it had recorded the bypass."""
        subprocess.run([GIT, "-C", str(self.repo), "-c", "user.email=a@b.c", "-c", "user.name=a",
                        "commit", "-q", "--allow-empty", "-m", "root"], check=True, capture_output=True, env=env())
        worktree = self.tmp / "wt"
        subprocess.run([GIT, "-C", str(self.repo), "worktree", "add", "-q", str(worktree)],
                       check=True, capture_output=True, env=env())
        (worktree / "a.css").write_text(".a { padding: 13px; }\n", encoding="utf-8")
        subprocess.run([GIT, "-C", str(worktree), "add", "a.css"], check=True, capture_output=True, env=env())
        proc = subprocess.run([SH, str(HOOK)], cwd=worktree, env=env(DESIGN_GATE_PYTHON=PY, DESIGN_GATE_BYPASS="1"),
                              capture_output=True, timeout=180)
        out = (proc.stdout + proc.stderr).decode("utf-8", "replace")
        self.assertEqual(proc.returncode, 0, out)
        self.assertNotIn("Not a directory", out)
        self.assertIn("BYPASS", (self.repo / ".git" / "design-gate.log").read_text(encoding="utf-8"))

    def test_a_bypass_travels_with_the_commit_as_a_trailer(self):
        """(d) The local log never leaves the clone. The same script, installed
        as the commit-msg hook, writes a trailer into the commit itself."""
        hooks = self.repo / ".git" / "hooks"
        for name in ("pre-commit", "commit-msg"):
            shutil.copy(HOOK, hooks / name)
            (hooks / name).chmod(0o755)
        self.stage("components/card.css", "@layer components {\n  .card { padding: 13px; }\n}\n")
        commit_env = env(DESIGN_GATE_PYTHON=PY, DESIGN_GATE_BYPASS="1",
                         DESIGN_GATE_BYPASS_REASON="client demo in an hour")
        proc = subprocess.run([GIT, "-c", "user.email=a@b.c", "-c", "user.name=a", "commit", "-q",
                               "-m", "Ship the card"], cwd=self.repo, env=commit_env, capture_output=True,
                              timeout=180)
        self.assertEqual(proc.returncode, 0, (proc.stdout + proc.stderr).decode("utf-8", "replace"))
        message = subprocess.run([GIT, "-C", str(self.repo), "log", "-1", "--format=%B"],
                                 capture_output=True, text=True, env=env()).stdout
        self.assertRegex(message, r"Design-Gate-Bypass: client demo in an hour")

    def test_the_staged_content_can_be_audited_instead_of_the_working_tree(self):
        """(e) The audit read the working tree, so a violation staged with
        `git add -p` and then fixed only on disk went through."""
        self.stage("components/card.css", "@layer components {\n  .card { padding: 13px; }\n}\n")
        (self.repo / "components" / "card.css").write_text(
            "@layer components {\n  .card { padding: var(--pad-card); }\n}\n", encoding="utf-8")
        code, out = self.run_hook()
        self.assertEqual(code, 0, out)                   # the working tree is clean
        code, out = self.run_hook(DESIGN_GATE_INDEX="1")
        self.assertEqual(code, 1, out)                   # what would be committed is not
        self.assertIn("13px", out)


if __name__ == "__main__":
    unittest.main()
