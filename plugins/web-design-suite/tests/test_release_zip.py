"""The release zip builder, tooling/release/build_zip.py (repository only).

It runs only inside the plugin's repository, where the builder is; a plugin
unpacked on its own skips it.

Regressions covered (3.2.1 review):
- It packaged whatever was on disk: a node_modules from `npm ci` in a skill's
  scripts folder, .DS_Store, Thumbs.db, editor backups.
- It took file modes from the previous release's zip, so a script git marks
  executable never became executable in the zip (completion plan, N5), and a
  new file was always 0644.
- It refused any release that removed a file, dated entries by the checkout's
  mtimes, so two builds of one commit differed, and exited 0 when its own
  test of the zip failed.
- (CodeRabbit) A GIT_DIR inherited from a hook or a shell made it build that
  repository. It skipped a tracked symbolic link, and a file `export-ignore`
  keeps out of `git archive`, and still reported success.
"""
from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys
import unittest
import zipfile

from wds_support import TOOLING, TempDirTest, env, output

GIT = shutil.which("git")
BUILDER = TOOLING / "release" / "build_zip.py" if TOOLING else None
GIT_ENV = {"GIT_AUTHOR_NAME": "wds-test", "GIT_AUTHOR_EMAIL": "wds-test@example.invalid",
           "GIT_COMMITTER_NAME": "wds-test", "GIT_COMMITTER_EMAIL": "wds-test@example.invalid",
           "GIT_AUTHOR_DATE": "2026-09-25T12:00:00Z", "GIT_COMMITTER_DATE": "2026-09-25T12:00:00Z"}


@unittest.skipUnless(GIT and BUILDER and BUILDER.is_file(), "needs git and the repository's tooling/release")
class ReleaseZip(TempDirTest):

    def git(self, *args: str) -> str:
        proc = subprocess.run([GIT, *args], cwd=self.tmp, capture_output=True, env=env(**GIT_ENV))
        self.assertEqual(0, proc.returncode, output(proc))
        return proc.stdout.decode("utf-8")

    def setUp(self):
        super().setUp()
        self.git("init", "-q")
        self.git("config", "core.autocrlf", "false")
        self.write("plugins/web-design-suite/README.md", "# plugin\n")
        tool = self.write("plugins/web-design-suite/scripts/tool.py", "#!/usr/bin/env python3\nprint(1)\n")
        tool.chmod(0o755)                   # where git reads modes from the disk (core.filemode) ...
        self.write("plugins/web-design-suite/scripts/old.py", "print(0)\n")
        self.git("add", ".")
        self.git("update-index", "--chmod=+x", "plugins/web-design-suite/scripts/tool.py")   # ... and where not
        self.git("commit", "-q", "-m", "one")
        # The previous release: the same layout, with a file this release removes.
        with zipfile.ZipFile(self.tmp / "previous.zip", "w") as z:
            for name in ("web-design-suite/", "web-design-suite/scripts/", "web-design-suite/scripts/old.py",
                         "web-design-suite/scripts/tool.py", "web-design-suite/README.md"):
                z.writestr(name, b"")
        self.git("rm", "-q", "plugins/web-design-suite/scripts/old.py")
        self.write("plugins/web-design-suite/scripts/new.py", "print(2)\n")
        self.git("add", ".")
        self.git("commit", "-q", "-m", "two")
        # On disk, not in git: what a release must never carry.
        self.write("plugins/web-design-suite/scripts/node_modules/pkg/index.js", "x\n")
        self.write("plugins/web-design-suite/.DS_Store", "x")
        self.write("plugins/web-design-suite/README.md.orig", "x")

    def build(self, name: str, **env_changes: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(BUILDER), "previous.zip", name], cwd=self.tmp,
                              capture_output=True, env=env(**GIT_ENV, **env_changes), timeout=120)

    def test_the_zip_holds_what_git_holds_with_its_modes(self):
        proc = self.build("out.zip")
        self.assertEqual(0, proc.returncode, output(proc))
        with zipfile.ZipFile(self.tmp / "out.zip") as z:
            infos = {i.filename: i for i in z.infolist()}
        self.assertEqual(["web-design-suite/", "web-design-suite/scripts/", "web-design-suite/scripts/tool.py",
                          "web-design-suite/README.md", "web-design-suite/scripts/new.py"], list(infos))
        self.assertEqual(0o100755, infos["web-design-suite/scripts/tool.py"].external_attr >> 16)
        self.assertEqual(0o100644, infos["web-design-suite/scripts/new.py"].external_attr >> 16)
        self.assertIn("removed since the previous release: web-design-suite/scripts/old.py", output(proc))

    def test_a_tar_umask_cannot_drop_an_executable_bit(self):
        self.git("config", "tar.umask", "0111")          # git archive then writes every file as 0666
        proc = self.build("out.zip")
        self.assertEqual(0, proc.returncode, output(proc))
        with zipfile.ZipFile(self.tmp / "out.zip") as z:
            self.assertEqual(0o100755, z.getinfo("web-design-suite/scripts/tool.py").external_attr >> 16)

    def test_two_builds_of_one_commit_are_identical(self):
        self.assertEqual(0, self.build("a.zip").returncode)
        (self.tmp / "plugins/web-design-suite/README.md").touch()
        self.assertEqual(0, self.build("b.zip").returncode)
        self.assertEqual((self.tmp / "a.zip").read_bytes(), (self.tmp / "b.zip").read_bytes())

    def test_it_never_overwrites_a_release(self):
        self.assertEqual(0, self.build("out.zip").returncode)
        proc = self.build("out.zip")
        self.assertEqual(2, proc.returncode, output(proc))
        self.assertIn("never overwrites", output(proc))

    def test_it_builds_the_repository_it_runs_in(self):
        self.git("init", "-q", "other")
        self.write("other/plugins/web-design-suite/OTHER.md", "other\n")
        self.git("-C", "other", "add", ".")
        self.git("-C", "other", "commit", "-q", "-m", "other")
        other = self.tmp / "other"
        proc = self.build("out.zip", GIT_DIR=str(other / ".git"), GIT_WORK_TREE=str(other))
        self.assertEqual(0, proc.returncode, output(proc))
        with zipfile.ZipFile(self.tmp / "out.zip") as z:
            names = z.namelist()
        self.assertIn("web-design-suite/scripts/tool.py", names)
        self.assertNotIn("web-design-suite/OTHER.md", names)

    def test_a_link_is_refused(self):
        blob = self.git("hash-object", "-w", "plugins/web-design-suite/README.md").strip()
        self.git("update-index", "--add", "--cacheinfo", f"120000,{blob},plugins/web-design-suite/link.md")
        self.git("commit", "-q", "-m", "a link")
        proc = self.build("out.zip")
        self.assertEqual(1, proc.returncode, output(proc))
        self.assertIn("plugins/web-design-suite/link.md is a symbolic link", output(proc))
        self.assertFalse((self.tmp / "out.zip").exists())

    def test_a_file_git_archive_leaves_out_is_refused(self):
        self.write(".gitattributes", "plugins/web-design-suite/scripts/new.py export-ignore\n")
        self.git("add", ".gitattributes")
        self.git("commit", "-q", "-m", "export-ignore")
        proc = self.build("out.zip")
        self.assertEqual(1, proc.returncode, output(proc))
        self.assertIn("plugins/web-design-suite/scripts/new.py is tracked, but git archive left it out", output(proc))
        self.assertFalse((self.tmp / "out.zip").exists())


if __name__ == "__main__":
    unittest.main()
