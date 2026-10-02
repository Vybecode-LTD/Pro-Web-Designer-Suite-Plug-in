"""git's file modes in the plugin (N5).

A file that starts with `#!` is executable in git (100755), and nothing else
is. The release zip takes its modes from git, so this is what makes a script
runnable as `./scripts/<name>` once the zip is unpacked.

Regressions covered:
- N5: only the nine scripts that were executable in 3.0.0 were marked; 17
  more had a shebang and were stored as 100644.

The modes come from git: in a checkout, from the index; under
tools/fail_before.py, from the commit WDS_PLUGIN_REV names, whose files are
unpacked at WDS_PLUGIN_ROOT. Outside a checkout, as in an unpacked zip, the
test skips.
"""
from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import unittest

from wds_support import PLUGIN, env

GIT = shutil.which("git")
HERE = pathlib.Path(__file__).resolve().parent


def git(cwd: pathlib.Path, *args: str) -> bytes | None:
    proc = subprocess.run([GIT, *args], cwd=cwd, capture_output=True, env=env())
    return proc.stdout if proc.returncode == 0 else None


def tracked_modes() -> dict[str, str]:
    """Each tracked file of the plugin under test, by its path inside the
    plugin, with git's mode for it. Empty when git cannot say."""
    if not GIT:
        return {}
    rev = os.environ.get("WDS_PLUGIN_REV")
    if rev:
        top = (git(HERE, "rev-parse", "--show-toplevel") or b"").decode().strip()
        out = git(pathlib.Path(top), "ls-tree", "-r", "-z", rev, "--", "plugins/web-design-suite") if top else None
        prefix = "plugins/web-design-suite/"
    else:
        out = git(PLUGIN, "ls-files", "-s", "-z", "--", ".")
        prefix = ""
    modes = {}
    for record in (out or b"").split(b"\0"):
        if record:
            meta, _, path = record.partition(b"\t")
            name = path.decode("utf-8", "surrogateescape")
            modes[name[len(prefix):] if name.startswith(prefix) else name] = meta.split(b" ", 1)[0].decode()
    return modes


MODES = tracked_modes()


@unittest.skipUnless(MODES, "the plugin is not in a git checkout, and no WDS_PLUGIN_REV names its commit")
class FileModes(unittest.TestCase):

    def test_a_file_with_a_shebang_is_executable_and_nothing_else_is(self):
        wrong, scripts = [], 0
        for name, mode in sorted(MODES.items()):
            if mode not in ("100644", "100755"):            # a link or a submodule: the release builder refuses those
                continue
            with open(PLUGIN / name, "rb") as f:
                shebang = f.read(2) == b"#!"
            scripts += shebang
            if shebang != (mode == "100755"):
                wrong.append(f"{mode} {name}")
        self.assertEqual([], wrong, "mark with: git update-index --chmod=+x <path> (or -x)")
        self.assertGreaterEqual(scripts, 20)                # the check is not vacuous


if __name__ == "__main__":
    unittest.main()
