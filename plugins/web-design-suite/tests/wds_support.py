"""Helpers shared by the web-design-suite regression tests. Standard library only.

Run every test from the plugin root:

    python -m unittest discover -s tests -v

Set WDS_PLUGIN_ROOT to run the same tests against another copy of the plugin,
for example an unpacked earlier release, to see which bugs it still has.
"""
from __future__ import annotations

import os
import pathlib
import re
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
# no toolchain, and those tests skip as before.
_PARENTS = pathlib.Path(__file__).resolve().parents
REPO = _PARENTS[3] if len(_PARENTS) > 3 else None
TOOLING = REPO / "tooling" if REPO and (REPO / ".claude-plugin" / "marketplace.json").is_file() else None
TOOLING_MAIN = TOOLING / "main" / "node_modules" if TOOLING else None
TOOLING_V3 = TOOLING / "tailwind-v3" / "node_modules" if TOOLING else None

# `set WDS_NODE_MODULES=` in cmd.exe and `$env:WDS_NODE_MODULES = ''` in
# PowerShell delete the variable rather than empty it, so a word is the switch.
OFF = {"", "0", "off", "no", "none", "false"}


def installed_here(node_modules: pathlib.Path) -> bool:
    """Whether npm installed `node_modules` for this platform. A native package
    ships one binary per platform, so a tree installed on Windows and read from
    WSL holds only win32 bindings: lightningcss, which Tailwind 4 loads, is the
    one in the toolchain."""
    if not node_modules.is_dir():
        return False
    bindings = [p.name for p in node_modules.glob("lightningcss-*")]
    return not bindings or any(b.startswith(f"lightningcss-{sys.platform}") for b in bindings)


def tool_roots(var: str, default: pathlib.Path | None = None, *, node_path: bool = False) -> list[str]:
    """The node_modules folders one group of real-tool or browser tests may use,
    in order, as absolute paths. The variable `var` names them (several joined by
    the path separator); a value in OFF switches the tests off. Unset, it falls
    back to `default` (the repository's toolchain, when installed for this
    platform) and then, with `node_path`, to NODE_PATH."""
    value = os.environ.get(var)
    if value is not None:
        if value.strip().lower() in OFF:
            return []
        return [str(pathlib.Path(p).resolve()) for p in value.split(os.pathsep) if p.strip()]
    roots = [str(default.resolve())] if default is not None and installed_here(default) else []
    if node_path:
        roots += [str(pathlib.Path(p).resolve()) for p in os.environ.get("NODE_PATH", "").split(os.pathsep)
                  if p.strip()]
    return roots


def tool_modules(var: str, *packages: str, default: pathlib.Path | None = TOOLING_MAIN,
                 node_path: bool = False) -> str | None:
    """The first of `tool_roots(var, …)` that holds every one of `packages`, or None."""
    return next((root for root in tool_roots(var, default, node_path=node_path)
                 if all((pathlib.Path(root) / p).is_dir() for p in packages)), None)


def tailwind_part5(config_text: str) -> tuple[str, dict[int, str]]:
    """Part 5 of eslint.design.config.mjs, uncommented as a project copies it:
    the shared lines between the `import tailwind` line and the first block, and
    each block by the plugin major its title names."""
    part5 = config_text.split("PART 5", 1)[1].split("EXPORTS", 1)[0]
    code = []
    for line in part5.splitlines():
        if line.startswith("//"):
            code.append(re.sub(r"^// ?", "", line))
        elif code:
            break
    text = "\n".join(code)
    text = text.split("import tailwind from 'eslint-plugin-tailwindcss';", 1)[1]
    pieces = re.split(r"^Tailwind v\d, eslint-plugin-tailwindcss@(\d+):\n", text, flags=re.M)
    blocks = {int(pieces[i]): pieces[i + 1].rstrip() + "\n" for i in range(1, len(pieces), 2)}
    return pieces[0].strip() + "\n", blocks


# The variables that tie git to one repository, as `git rev-parse
# --local-env-vars` names them (git 2.55). A run from a git hook, or under
# `git -c`, inherits them, and they would point the tests' git commands, and
# the hook under test, at that repository instead of a temporary one.
GIT_REPOSITORY_VARIABLES = frozenset({
    "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_CONFIG", "GIT_CONFIG_PARAMETERS", "GIT_CONFIG_COUNT",
    "GIT_OBJECT_DIRECTORY", "GIT_DIR", "GIT_WORK_TREE", "GIT_IMPLICIT_WORK_TREE", "GIT_GRAFT_FILE",
    "GIT_INDEX_FILE", "GIT_NO_REPLACE_OBJECTS", "GIT_REPLACE_REF_BASE", "GIT_PREFIX", "GIT_SHALLOW_FILE",
    "GIT_COMMON_DIR"})


def env(**changes: str | None) -> dict[str, str]:
    """The environment for every subprocess a test starts: the current one
    without git's repository variables, plus `changes`; a value of None removes
    that variable.

    PYTHONIOENCODING defaults to utf-8, as it is inside Claude Code, so results do
    not depend on where the tests are launched from. Tests about the real-world
    terminal behaviour remove it explicitly.
    """
    e = {k: v for k, v in os.environ.items() if k not in GIT_REPOSITORY_VARIABLES}
    e.update(PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8")
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


if sys.version_info >= (3, 10):
    def temp_dir(prefix: str) -> tempfile.TemporaryDirectory:
        """A temporary folder whose cleanup leaves behind what it cannot delete
        (a file Windows still holds open) instead of failing the test."""
        return tempfile.TemporaryDirectory(prefix=prefix, ignore_cleanup_errors=True)
else:
    class _TemporaryDirectory(tempfile.TemporaryDirectory):
        """Python 3.9 has no ignore_cleanup_errors. Its own cleanup already
        clears read-only files, such as git's objects, and retries; what it
        still cannot delete is left behind, as ignore_cleanup_errors does."""

        @classmethod
        def _rmtree(cls, name):
            try:
                super()._rmtree(name)
            except OSError:
                pass

    def temp_dir(prefix: str) -> tempfile.TemporaryDirectory:
        """A temporary folder whose cleanup leaves behind what it cannot delete
        (a file Windows still holds open) instead of failing the test."""
        return _TemporaryDirectory(prefix=prefix)


def class_temp_dir(cls, prefix: str) -> pathlib.Path:
    """A temporary folder for one test class, removed after its tests, as a
    resolved path. Node reports files under the resolved folder (getcwd()
    resolves /var to /private/var on macOS), so paths compare only when both
    sides are resolved."""
    holder = temp_dir(prefix)
    cls.addClassCleanup(holder.cleanup)
    return pathlib.Path(holder.name).resolve()


class TempDirTest(unittest.TestCase):
    """A test case with a fresh temporary directory in self.tmp."""

    def setUp(self):
        holder = temp_dir("wds-test-")
        self.addCleanup(holder.cleanup)
        self.tmp = pathlib.Path(holder.name)

    def write(self, rel: str, content: str | bytes) -> pathlib.Path:
        path = self.tmp / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_bytes(content.encode("utf-8"))      # LF as written; write_text(newline=) is 3.10+
        return path
