"""Helpers shared by the web-design-suite regression tests. Standard library only.

Run every test from the plugin root:

    python -m unittest discover -s tests -v

Set WDS_PLUGIN_ROOT to run the same tests against another copy of the plugin,
for example an unpacked earlier release, to see which bugs it still has.
"""
from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

PLUGIN = pathlib.Path(os.environ.get("WDS_PLUGIN_ROOT")
                      or pathlib.Path(__file__).resolve().parents[1])
SKILLS = PLUGIN / "skills"
NODE = shutil.which("node")
NPM = shutil.which("npm")

# Inside its repository (plugins/web-design-suite, with `npm ci` run in
# tooling/main and tooling/tailwind-v3), the plugin's tests use the
# repository's pinned toolchain for any tool location that is not set. The
# toolchain sits beside the plugin, never above it: Node looks for packages in
# every parent folder, and a node_modules above the scripts would stand in for
# the stub modules the resolution tests plant. A plugin unpacked on its own has
# no toolchain, and those tests skip as before. Set a variable to an empty
# string to switch its tests off.
_PARENTS = pathlib.Path(__file__).resolve().parents
REPO = _PARENTS[3] if len(_PARENTS) > 3 else None
TOOLING = REPO / "tooling" if REPO and (REPO / ".claude-plugin" / "marketplace.json").is_file() else None
if TOOLING and (TOOLING / "main" / "node_modules").is_dir():
    for _var in ("WDS_NODE_MODULES", "WDS_ESLINT_MODULES", "WDS_TAILWIND_MODULES",
                 "WDS_STYLELINT_MODULES"):
        os.environ.setdefault(_var, str(TOOLING / "main" / "node_modules"))
if TOOLING and (TOOLING / "tailwind-v3" / "node_modules").is_dir():
    os.environ.setdefault("WDS_TAILWIND_V3_MODULES", str(TOOLING / "tailwind-v3" / "node_modules"))


def env(**changes: str | None) -> dict[str, str]:
    """The current environment plus `changes`; a value of None removes that variable.

    PYTHONIOENCODING defaults to utf-8, as it is inside Claude Code, so results do
    not depend on where the tests are launched from. Tests about the real-world
    terminal behaviour remove it explicitly.
    """
    e = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8")
    for key, value in changes.items():
        if value is None:
            e.pop(key, None)
        else:
            e[key] = value
    return e


def run_py(skill: str, module: str, *args, cwd, env_changes=None, timeout=120, stdin=None):
    """Run `python -m scripts.<module>` the way the docs do, with the skill folder
    on sys.path and a disposable working directory, so nothing is written into
    the plugin itself."""
    e = env(PYTHONPATH=str(SKILLS / skill), **(env_changes or {}))
    return subprocess.run([sys.executable, "-m", f"scripts.{module}", *map(str, args)],
                          cwd=cwd, env=e, capture_output=True, timeout=timeout, input=stdin)


def run_node(skill: str, script: str, *args, cwd, env_changes=None, timeout=120):
    return subprocess.run([NODE, str(SKILLS / skill / "scripts" / script), *map(str, args)],
                          cwd=cwd, env=env(**(env_changes or {})),
                          capture_output=True, timeout=timeout)


def output(proc: subprocess.CompletedProcess) -> str:
    """stdout + stderr of a finished process, decoded for assertions."""
    return (proc.stdout + proc.stderr).decode("utf-8", "replace")


class TempDirTest(unittest.TestCase):
    """A test case with a fresh temporary directory in self.tmp."""

    def setUp(self):
        holder = tempfile.TemporaryDirectory(prefix="wds-test-", ignore_cleanup_errors=True)
        self.addCleanup(holder.cleanup)
        self.tmp = pathlib.Path(holder.name)

    def write(self, rel: str, content: str | bytes) -> pathlib.Path:
        path = self.tmp / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content, encoding="utf-8", newline="")
        return path
