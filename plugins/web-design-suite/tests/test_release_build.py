"""The release builder, tooling/release/build.py (repository only): the
plugin's zip, one .skill file per skill, and their SHA-256 sums, from git.

It runs only inside the plugin's repository, where the builder is; a plugin
unpacked on its own skips it.

Regressions covered (3.2.1 review, and XC-C6 for 3.3.0):
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
- XC-C6: there were no .skill files, and no checksums.
- N34 (3.4.0): two builds of one commit are byte-identical only with the same
  zlib, so tooling/release/compare.py compares builds by their archives' contents.
"""
from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys
import unittest
import zipfile

from wds_support import TOOLING, TempDirTest, env, output

GIT = shutil.which("git")
BUILDER = TOOLING / "release" / "build.py" if TOOLING else None
COMPARE = TOOLING / "release" / "compare.py" if TOOLING else None
GIT_ENV = {"GIT_AUTHOR_NAME": "wds-test", "GIT_AUTHOR_EMAIL": "wds-test@example.invalid",
           "GIT_COMMITTER_NAME": "wds-test", "GIT_COMMITTER_EMAIL": "wds-test@example.invalid",
           "GIT_AUTHOR_DATE": "2026-09-25T12:00:00Z", "GIT_COMMITTER_DATE": "2026-09-25T12:00:00Z"}
P = "plugins/web-design-suite"


def skill_md(name: str, description: str = "Builds alphas. Use when an alpha is needed.") -> str:
    return f"---\nname: {name}\ndescription: >\n  {description}\n---\n\n# {name}\n"


@unittest.skipUnless(GIT and BUILDER and BUILDER.is_file(), "needs git and the repository's tooling/release")
class ReleaseBuild(TempDirTest):

    def git(self, *args: str) -> str:
        proc = subprocess.run([GIT, *args], cwd=self.tmp, capture_output=True, env=env(**GIT_ENV))
        self.assertEqual(0, proc.returncode, output(proc))
        return proc.stdout.decode("utf-8")

    def setUp(self):
        super().setUp()
        self.git("init", "-q")
        self.git("config", "core.autocrlf", "false")
        self.write(f"{P}/README.md", "# plugin\n")
        self.write(f"{P}/LICENSE", "MIT\n")
        self.write(f"{P}/.claude-plugin/plugin.json", '{"name": "web-design-suite", "version": "9.8.7"}\n')
        tool = self.write(f"{P}/scripts/tool.py", "#!/usr/bin/env python3\nprint(1)\n")
        tool.chmod(0o755)                   # where git reads modes from the disk (core.filemode) ...
        self.write(f"{P}/scripts/old.py", "print(0)\n")
        self.write(f"{P}/skills/alpha/SKILL.md", skill_md("alpha"))
        run = self.write(f"{P}/skills/alpha/scripts/run.py", "#!/usr/bin/env python3\nprint(2)\n")
        run.chmod(0o755)                    # on POSIX, the second commit's `git add .` reads modes from the disk
        self.write(f"{P}/skills/alpha/evals/case.yaml", "prompt: x\n")
        self.write(f"{P}/skills/alpha/references/evals/notes.md", "kept: only a top-level evals/ is left out\n")
        self.write(f"{P}/skills/beta/SKILL.md", skill_md("beta", "Builds betas."))
        self.git("add", ".")
        for path in ("scripts/tool.py", "skills/alpha/scripts/run.py"):
            self.git("update-index", "--chmod=+x", f"{P}/{path}")                  # ... and where not
        self.git("commit", "-q", "-m", "one")
        self.git("tag", "v9.8.6")
        self.git("rm", "-q", f"{P}/scripts/old.py")
        self.write(f"{P}/scripts/new.py", "print(2)\n")
        self.git("add", ".")
        self.git("commit", "-q", "-m", "two")
        # On disk, not in git: what a release must never carry.
        self.write(f"{P}/scripts/node_modules/pkg/index.js", "x\n")
        self.write(f"{P}/.DS_Store", "x")
        self.write(f"{P}/README.md.orig", "x")
        self.write(f"{P}/skills/alpha/__pycache__/run.cpython-314.pyc", "x")

    def build(self, out: str = "dist", **env_changes: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, "-B", str(BUILDER), out], cwd=self.tmp,
                              capture_output=True, env=env(**GIT_ENV, **env_changes), timeout=120)

    def infos(self, name: str, out: str = "dist") -> dict[str, zipfile.ZipInfo]:
        with zipfile.ZipFile(self.tmp / out / name) as z:
            return {i.filename: i for i in z.infolist()}

    def test_the_zip_holds_what_git_holds_with_its_modes(self):
        proc = self.build()
        self.assertEqual(0, proc.returncode, output(proc))
        infos = self.infos("web-design-suite-9.8.7.zip")
        self.assertEqual(sorted(infos), list(infos))
        self.assertEqual({"web-design-suite/scripts/tool.py", "web-design-suite/scripts/new.py",
                          "web-design-suite/README.md", "web-design-suite/LICENSE",
                          "web-design-suite/.claude-plugin/plugin.json", "web-design-suite/skills/alpha/SKILL.md",
                          "web-design-suite/skills/alpha/scripts/run.py", "web-design-suite/skills/alpha/evals/case.yaml",
                          "web-design-suite/skills/alpha/references/evals/notes.md",
                          "web-design-suite/skills/beta/SKILL.md"},
                         {n for n in infos if not n.endswith("/")})
        self.assertEqual(0o100755, infos["web-design-suite/scripts/tool.py"].external_attr >> 16)
        self.assertEqual(0o100644, infos["web-design-suite/scripts/new.py"].external_attr >> 16)
        self.assertIn("removed since v9.8.6: scripts/old.py", output(proc))

    def test_each_skill_is_a_skill_file(self):
        self.assertEqual(0, self.build().returncode)
        alpha = self.infos("alpha.skill")
        self.assertEqual(["alpha/LICENSE", "alpha/SKILL.md", "alpha/references/evals/notes.md",
                          "alpha/scripts/run.py"], list(alpha))
        self.assertEqual(0o100755, alpha["alpha/scripts/run.py"].external_attr >> 16)
        self.assertTrue(all(i.compress_type == zipfile.ZIP_DEFLATED for i in alpha.values()))
        self.assertEqual(["beta/LICENSE", "beta/SKILL.md"], list(self.infos("beta.skill")))

    def test_the_sums_are_the_files(self):
        self.assertEqual(0, self.build().returncode)
        lines = (self.tmp / "dist" / "SHA256SUMS").read_text(encoding="ascii").splitlines()
        self.assertEqual(["alpha.skill", "beta.skill", "web-design-suite-9.8.7.zip"], [ln.split("  ")[1] for ln in lines])
        for line in lines:
            digest, name = line.split("  ")
            with self.subTest(file=name):
                self.assertEqual(hashlib.sha256((self.tmp / "dist" / name).read_bytes()).hexdigest(), digest)

    def test_a_tar_umask_cannot_drop_an_executable_bit(self):
        self.git("config", "tar.umask", "0111")          # git archive then writes every file as 0666
        proc = self.build()
        self.assertEqual(0, proc.returncode, output(proc))
        self.assertEqual(0o100755, self.infos("web-design-suite-9.8.7.zip")["web-design-suite/scripts/tool.py"]
                         .external_attr >> 16)

    def test_two_builds_of_one_commit_are_identical(self):
        self.assertEqual(0, self.build("a").returncode)
        (self.tmp / P / "README.md").touch()
        self.assertEqual(0, self.build("b").returncode)
        for name in sorted(p.name for p in (self.tmp / "a").iterdir()):
            with self.subTest(file=name):
                self.assertEqual((self.tmp / "a" / name).read_bytes(), (self.tmp / "b" / name).read_bytes())

    def test_it_never_overwrites_a_release(self):
        self.assertEqual(0, self.build().returncode)
        proc = self.build()
        self.assertEqual(2, proc.returncode, output(proc))
        self.assertIn("never overwrites", output(proc))

    def test_it_builds_the_repository_it_runs_in(self):
        self.git("init", "-q", "other")
        self.write("other/plugins/web-design-suite/OTHER.md", "other\n")
        self.git("-C", "other", "add", ".")
        self.git("-C", "other", "commit", "-q", "-m", "other")
        other = self.tmp / "other"
        proc = self.build(GIT_DIR=str(other / ".git"), GIT_WORK_TREE=str(other))
        self.assertEqual(0, proc.returncode, output(proc))
        names = list(self.infos("web-design-suite-9.8.7.zip"))
        self.assertIn("web-design-suite/scripts/tool.py", names)
        self.assertNotIn("web-design-suite/OTHER.md", names)

    def assert_refused(self, reason: str):
        proc = self.build()
        self.assertEqual(1, proc.returncode, output(proc))
        self.assertIn(reason, output(proc))
        self.assertFalse((self.tmp / "dist").exists())

    def test_a_link_is_refused(self):
        blob = self.git("hash-object", "-w", f"{P}/README.md").strip()
        self.git("update-index", "--add", "--cacheinfo", f"120000,{blob},{P}/link.md")
        self.git("commit", "-q", "-m", "a link")
        self.assert_refused(f"{P}/link.md is a symbolic link")

    def test_a_file_git_archive_leaves_out_is_refused(self):
        self.write(".gitattributes", f"{P}/scripts/new.py export-ignore\n")
        self.git("add", ".gitattributes")
        self.git("commit", "-q", "-m", "export-ignore")
        self.assert_refused(f"{P}/scripts/new.py is tracked, but git archive left it out")

    def test_a_skill_the_platform_refuses_is_refused(self):
        self.write(f"{P}/skills/beta/SKILL.md", skill_md("Beta-Claude"))
        self.git("commit", "-q", "-am", "a bad name")
        self.assert_refused("skills/beta: its name is 'Beta-Claude', and its folder 'beta'")

    def test_a_description_longer_than_an_upload_takes_is_a_warning(self):
        self.write(f"{P}/skills/beta/SKILL.md", skill_md("beta", "Builds betas. " * 15))
        self.git("commit", "-q", "-am", "a long description")
        proc = self.build()
        self.assertEqual(0, proc.returncode, output(proc))
        self.assertIn("warning: beta: its description has 209 characters; claude.ai's help center gives 200",
                      output(proc))

    def compare(self, a: str, b: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, "-B", str(COMPARE), a, b], cwd=self.tmp,
                              capture_output=True, env=env())

    def recompress(self, src: str, dst: str, change: dict | None = None) -> None:
        """A copy of a build whose archives are stored, not deflated, as a
        different zlib would leave them: other bytes, the same files."""
        (self.tmp / dst).mkdir()
        for path in sorted((self.tmp / src).iterdir()):
            target = self.tmp / dst / path.name
            if not zipfile.is_zipfile(path):
                target.write_bytes(path.read_bytes())
                continue
            with zipfile.ZipFile(path) as a, zipfile.ZipFile(target, "w") as b:
                for info in a.infolist():
                    data = (change or {}).get(info.filename, a.read(info))
                    info.compress_type = zipfile.ZIP_STORED
                    b.writestr(info, data)

    @unittest.skipUnless(COMPARE and COMPARE.is_file(), "needs the repository's tooling/release")
    def test_builds_that_compress_differently_compare_the_same(self):
        """N34: Windows' Python 3.14 deflates with zlib-ng and the CI's with
        zlib, so 3.3.0's release matched no local build of its commit byte for
        byte, though every file was the same."""
        self.assertEqual(0, self.build("a").returncode)
        self.recompress("a", "b")
        zips = [p.name for p in (self.tmp / "a").iterdir() if p.suffix in (".zip", ".skill")]
        self.assertGreaterEqual(len(zips), 3)
        for name in zips:
            with self.subTest(file=name):
                self.assertNotEqual((self.tmp / "a" / name).read_bytes(), (self.tmp / "b" / name).read_bytes())
        proc = self.compare("a", "b")
        self.assertEqual(0, proc.returncode, output(proc))
        self.assertIn("the same", output(proc))

    @unittest.skipUnless(COMPARE and COMPARE.is_file(), "needs the repository's tooling/release")
    def test_a_changed_or_missing_file_is_a_difference(self):
        self.assertEqual(0, self.build("a").returncode)
        self.recompress("a", "b", change={"web-design-suite/README.md": b"# changed\n"})
        (self.tmp / "b" / "alpha.skill").unlink()
        proc = self.compare("a", "b")
        self.assertEqual(1, proc.returncode, output(proc))
        self.assertIn("web-design-suite-9.8.7.zip: web-design-suite/README.md differs in CRC, size", output(proc))
        self.assertIn("alpha.skill: only in a", output(proc))


if __name__ == "__main__":
    unittest.main()
