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
import importlib.util
import re
import shutil
import subprocess
import sys
import unittest
import zipfile

from wds_support import PLUGIN, REPO, SKILLS, TOOLING, TempDirTest, env, output

GIT = shutil.which("git")
BUILDER = TOOLING / "release" / "build.py" if TOOLING else None
COMPARE = TOOLING / "release" / "compare.py" if TOOLING else None
GIT_ENV = {"GIT_AUTHOR_NAME": "wds-test", "GIT_AUTHOR_EMAIL": "wds-test@example.invalid",
           "GIT_COMMITTER_NAME": "wds-test", "GIT_COMMITTER_EMAIL": "wds-test@example.invalid",
           "GIT_AUTHOR_DATE": "2026-09-25T12:00:00Z", "GIT_COMMITTER_DATE": "2026-09-25T12:00:00Z"}
P = "plugins/pro-web-design-suite"
DEV_FILES = ("tests/test_x.py", "evals/routing/alpha/prompt.md", "tools/check.py")


# Anthropic's directory blocks a README of fewer than 40 words outside code blocks.
README_BODY = ("This plugin exists for the release builder's tests. It holds two skills, alpha and beta, "
               "a script that git marks executable, and a license, which is what a small plugin needs before "
               "the directory lists it. Nothing here runs outside the tests.\n")


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
        self.write(f"{P}/README.md", "# plugin\n\n" + README_BODY)
        self.write(f"{P}/LICENSE", "MIT\n")
        self.write(f"{P}/.claude-plugin/plugin.json", '{"name": "pro-web-design-suite", "version": "9.8.7"}\n')
        tool = self.write(f"{P}/scripts/tool.py", "#!/usr/bin/env python3\nprint(1)\n")
        tool.chmod(0o755)                   # where git reads modes from the disk (core.filemode) ...
        self.write(f"{P}/scripts/old.py", "print(0)\n")
        self.write(f"{P}/skills/alpha/SKILL.md", skill_md("alpha"))
        run = self.write(f"{P}/skills/alpha/scripts/run.py", "#!/usr/bin/env python3\nprint(2)\n")
        run.chmod(0o755)                    # on POSIX, the second commit's `git add .` reads modes from the disk
        self.write(f"{P}/skills/alpha/evals/case.yaml", "prompt: x\n")
        self.write(f"{P}/skills/alpha/references/evals/notes.md", "kept: only a top-level evals/ is left out\n")
        self.write(f"{P}/skills/beta/SKILL.md", skill_md("beta", "Builds betas."))
        for dev in DEV_FILES:
            self.write(f"{P}/{dev}", "development only\n")              # tracked, never shipped
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
        infos = self.infos("pro-web-design-suite-9.8.7.zip")
        self.assertEqual(sorted(infos), list(infos))
        self.assertEqual({"pro-web-design-suite/scripts/tool.py", "pro-web-design-suite/scripts/new.py",
                          "pro-web-design-suite/README.md", "pro-web-design-suite/LICENSE",
                          "pro-web-design-suite/.claude-plugin/plugin.json", "pro-web-design-suite/skills/alpha/SKILL.md",
                          "pro-web-design-suite/skills/alpha/scripts/run.py", "pro-web-design-suite/skills/alpha/evals/case.yaml",
                          "pro-web-design-suite/skills/alpha/references/evals/notes.md",
                          "pro-web-design-suite/skills/beta/SKILL.md"},
                         {n for n in infos if not n.endswith("/")})
        self.assertEqual(0o100755, infos["pro-web-design-suite/scripts/tool.py"].external_attr >> 16)
        self.assertEqual(0o100644, infos["pro-web-design-suite/scripts/new.py"].external_attr >> 16)
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
        self.assertEqual(["alpha.skill", "beta.skill", "pro-web-design-suite-9.8.7.zip"], [ln.split("  ")[1] for ln in lines])
        for line in lines:
            digest, name = line.split("  ")
            with self.subTest(file=name):
                self.assertEqual(hashlib.sha256((self.tmp / "dist" / name).read_bytes()).hexdigest(), digest)

    def test_a_tar_umask_cannot_drop_an_executable_bit(self):
        self.git("config", "tar.umask", "0111")          # git archive then writes every file as 0666
        proc = self.build()
        self.assertEqual(0, proc.returncode, output(proc))
        self.assertEqual(0o100755, self.infos("pro-web-design-suite-9.8.7.zip")["pro-web-design-suite/scripts/tool.py"]
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
        self.write("other/plugins/pro-web-design-suite/OTHER.md", "other\n")
        self.git("-C", "other", "add", ".")
        self.git("-C", "other", "commit", "-q", "-m", "other")
        other = self.tmp / "other"
        proc = self.build(GIT_DIR=str(other / ".git"), GIT_WORK_TREE=str(other))
        self.assertEqual(0, proc.returncode, output(proc))
        names = list(self.infos("pro-web-design-suite-9.8.7.zip"))
        self.assertIn("pro-web-design-suite/scripts/tool.py", names)
        self.assertNotIn("pro-web-design-suite/OTHER.md", names)

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

    def test_a_release_from_before_the_rename_builds_under_its_own_name(self):
        """Codex on #180: --rev at 3.6.0 or earlier found no
        plugins/pro-web-design-suite there, and the builder stopped. It takes
        the folder from the revision, and names the zip as its plugin.json does."""
        self.git("mv", P, "plugins/web-design-suite")
        self.write("plugins/web-design-suite/.claude-plugin/plugin.json",
                   '{"name": "web-design-suite", "version": "3.6.0"}\n')
        self.git("commit", "-q", "-am", "as it was before the rename")
        proc = self.build()
        self.assertEqual(0, proc.returncode, output(proc))
        names = list(self.infos("web-design-suite-3.6.0.zip"))
        self.assertIn("web-design-suite/scripts/tool.py", names)
        self.assertEqual(0o100755, self.infos("web-design-suite-3.6.0.zip")["web-design-suite/scripts/tool.py"]
                         .external_attr >> 16)

    def test_a_description_longer_than_an_upload_takes_is_a_warning(self):
        self.write(f"{P}/skills/beta/SKILL.md", skill_md("beta", "Builds betas. " * 15))
        self.git("commit", "-q", "-am", "a long description")
        proc = self.build()
        self.assertEqual(0, proc.returncode, output(proc))
        self.assertIn("warning: beta: its description has 209 characters; claude.ai's help center gives 200",
                      output(proc))

    def test_the_development_folders_never_ship(self):
        """4.0.0: the plugin's tests/, evals/ and tools/ stay in the development
        repository. A skill's own evals/ still ships, as before."""
        self.assertEqual(0, self.build().returncode)
        names = list(self.infos("pro-web-design-suite-9.8.7.zip"))
        for dev in DEV_FILES:
            with self.subTest(file=dev):
                self.assertNotIn(f"pro-web-design-suite/{dev}", names)
                self.assertNotIn(f"pro-web-design-suite/{dev.split('/')[0]}/", names)
        self.assertIn("pro-web-design-suite/skills/alpha/evals/case.yaml", names)

    def tree_build(self, tree: str = "tree") -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, "-B", str(BUILDER), "dist", "--tree", tree], cwd=self.tmp,
                              capture_output=True, env=env(**GIT_ENV), timeout=120)

    def test_the_tree_holds_what_the_zip_holds(self):
        """The distribution repository's contents: the zip's files, at the root."""
        proc = self.tree_build()
        self.assertEqual(0, proc.returncode, output(proc))
        tree = self.tmp / "tree"
        on_disk = sorted(p.relative_to(tree).as_posix() for p in tree.rglob("*") if p.is_file())
        with zipfile.ZipFile(self.tmp / "dist" / "pro-web-design-suite-9.8.7.zip") as z:
            zipped = {i.filename[len("pro-web-design-suite/"):]: z.read(i) for i in z.infolist()
                      if not i.filename.endswith("/")}
        self.assertEqual(sorted(zipped), on_disk)
        for rel, data in zipped.items():
            with self.subTest(file=rel):
                self.assertEqual(data, (tree / rel).read_bytes())
        if sys.platform != "win32":
            self.assertTrue((tree / "scripts" / "tool.py").stat().st_mode & 0o111)
            self.assertFalse((tree / "scripts" / "new.py").stat().st_mode & 0o111)
        self.assertIn("tree: tree (", output(proc))

    def test_the_tree_never_overwrites_a_folder(self):
        self.write("tree/kept.txt", "x\n")
        proc = self.tree_build()
        self.assertEqual(2, proc.returncode, output(proc))
        self.assertIn("tree is not an empty folder", output(proc))
        self.assertFalse((self.tmp / "dist").exists())

    def test_what_the_directory_blocks_is_refused(self):
        self.write(f"{P}/README.md", "# plugin\n\nToo short.\n")
        self.git("commit", "-q", "-am", "a short README")
        self.assert_refused("Anthropic's directory would block it: the README has 4 words outside code blocks")

    def test_what_the_directory_holds_is_a_warning(self):
        self.write(f"{P}/assets/big.md", "x" * (256 * 1024 + 1))
        self.git("add", f"{P}/assets/big.md")
        self.git("commit", "-q", "-m", "a big file")
        proc = self.build()
        self.assertEqual(0, proc.returncode, output(proc))
        self.assertIn("directory hold: assets/big.md is 262145 bytes; over 262144 is held for a reviewer",
                      output(proc))

    def test_a_held_file_in_a_development_folder_is_not_a_hold(self):
        self.write(f"{P}/tests/fixtures/big.md", "x" * (256 * 1024 + 1))
        self.git("add", f"{P}/tests/fixtures/big.md")
        self.git("commit", "-q", "-m", "a big fixture")
        proc = self.build()
        self.assertEqual(0, proc.returncode, output(proc))
        self.assertNotIn("directory hold", output(proc))

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
        self.recompress("a", "b", change={"pro-web-design-suite/README.md": b"# changed\n"})
        (self.tmp / "b" / "alpha.skill").unlink()
        proc = self.compare("a", "b")
        self.assertEqual(1, proc.returncode, output(proc))
        self.assertIn("pro-web-design-suite-9.8.7.zip: pro-web-design-suite/README.md differs in contents, size",
                      output(proc))
        self.assertIn("alpha.skill: only in a", output(proc))

    @unittest.skipUnless(COMPARE and COMPARE.is_file(), "needs the repository's tooling/release")
    def test_a_damaged_payload_under_an_intact_directory_is_a_difference(self):
        """Codex on #38: the recorded CRCs and sizes were compared, never the
        bytes, so a payload changed under an untouched directory passed."""
        self.assertEqual(0, self.build("a").returncode)
        self.recompress("a", "b")                           # stored, so the payload is the text itself
        zip_b = self.tmp / "b" / "pro-web-design-suite-9.8.7.zip"
        data = zip_b.read_bytes()
        self.assertEqual(1, data.count(b"# plugin\n"))
        zip_b.write_bytes(data.replace(b"# plugin\n", b"# pluGin\n"))
        proc = self.compare("a", "b")
        self.assertEqual(1, proc.returncode, output(proc))
        self.assertIn("pro-web-design-suite/README.md is unreadable (Bad CRC-32", output(proc))

    @unittest.skipUnless(COMPARE and COMPARE.is_file(), "needs the repository's tooling/release")
    def test_an_entry_damaged_alike_on_both_sides_is_a_difference(self):
        """CodeRabbit on #38: the same read error on both sides gave the same
        "digest", and two damaged builds compared the same."""
        self.assertEqual(0, self.build("a").returncode)
        self.recompress("a", "b")
        self.recompress("a", "c")
        for folder in ("b", "c"):
            path = self.tmp / folder / "pro-web-design-suite-9.8.7.zip"
            path.write_bytes(path.read_bytes().replace(b"# plugin\n", b"# pluGin\n"))
        proc = self.compare("b", "c")
        self.assertEqual(1, proc.returncode, output(proc))
        self.assertIn("pro-web-design-suite/README.md is unreadable", output(proc))


def builder_module():
    spec = importlib.util.spec_from_file_location("wds_release_build", BUILDER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@unittest.skipUnless(BUILDER and BUILDER.is_file(), "needs the repository's tooling/release")
class TheDirectoryChecks(unittest.TestCase):
    """4.0.0: what Anthropic's directory blocks on or holds for a reviewer
    (claude.com/docs/plugins/pre-submission-checklist, read 2026-10-19), found
    before a release reaches the distribution repository. Each check has a
    clean plugin as its control."""

    @classmethod
    def setUpClass(cls):
        cls.build = builder_module()

    def plugin(self, **extra: bytes) -> dict:
        files = {".claude-plugin/plugin.json": b'{"name": "x", "version": "1.0.0", "license": "MIT"}',
                 "README.md": ("word " * 40).encode(), "skills/a/SKILL.md": b"---\nname: a\n---\n"}
        files.update(extra)
        return {path: (0o100644, data) for path, data in files.items()}

    def findings(self, **extra: bytes) -> tuple:
        return self.build.directory_findings(self.plugin(**extra))

    def test_a_clean_plugin_has_no_findings(self):
        self.assertEqual(([], []), self.findings())

    def test_the_shipped_plugin_has_no_findings(self):
        files = {p.relative_to(PLUGIN).as_posix(): (0o100644, p.read_bytes()) for p in PLUGIN.rglob("*")
                 if p.is_file() and p.relative_to(PLUGIN).parts[0] not in self.build.DEV_ONLY
                 and "__pycache__" not in p.parts and "node_modules" not in p.parts}
        self.assertEqual(([], []), self.build.directory_findings(files))
        self.assertLess(len(files), self.build.DIRECTORY_MAX_FILES)

    def test_what_blocks(self):
        cases = {
            "README.md": ({"README.md": b"# x\n\n```\n" + b"word " * 50 + b"\n```\n"}, "the README has 2 words"),
            "plugin.json": ({".claude-plugin/plugin.json": b"{"}, "no readable .claude-plugin/plugin.json"),
            "a system file": ({"skills/.DS_Store": b"x"}, "skills/.DS_Store is an operating system's file"),
            "a device name": ({"docs/con.md": b"x"}, "docs/con.md is not a valid file name on Windows"),
            "a colon": ({"docs/a:b.md": b"x"}, "docs/a:b.md is not a valid file name on Windows"),
            "a trailing dot": ({"docs./a.md": b"x"}, "docs. is not a valid file name on Windows"),
            "two cases": ({"Skills/b/SKILL.md": b"x"}, "differ only by capitalization"),
            "unpinned npx": ({".mcp.json": b'{"mcpServers": {"s": {"command": "npx", "args": ["-y", "pkg"]}}}'},
                             ".mcp.json runs npx pkg: pin it"),
            "unpinned uvx": ({"hooks/hooks.json": b'{"hooks": {"Stop": [{"hooks": [{"type": "command", '
                                                  b'"command": "uvx tool"}]}]}}'}, "hooks/hooks.json runs uvx tool"),
            "uv run unlocked": ({".mcp.json": b'{"mcpServers": {"s": {"command": "uv", "args": ["run", "s.py"]}}}'},
                                "uv run (without --locked or --frozen)"),
            "bad hooks.json": ({"hooks/hooks.json": b"{"}, "hooks/hooks.json is not valid JSON"),
        }
        for name, (extra, needle) in cases.items():
            with self.subTest(case=name):
                blocks, _ = self.build.directory_findings(self.plugin_with(extra))
                self.assertTrue(any(needle in b for b in blocks), blocks)

    def plugin_with(self, extra: dict) -> dict:
        files = self.plugin()
        files.update({path: (0o100644, data) for path, data in extra.items()})
        return files

    def test_a_license_in_plugin_json_is_enough(self):
        self.assertEqual([], self.findings()[0])
        blocks, _ = self.build.directory_findings(self.plugin_with(
            {".claude-plugin/plugin.json": b'{"name": "x", "version": "1.0.0"}'}))
        self.assertIn("there is no LICENSE file and no license in plugin.json", blocks)
        self.assertEqual(([], []), self.build.directory_findings(self.plugin_with(
            {".claude-plugin/plugin.json": b'{"name": "x", "version": "1.0.0"}', "LICENSE": b"MIT"})))

    def test_pinned_launchers_pass(self):
        for command in ('"npx", "args": ["-y", "pkg@1.2.3"]', '"npx", "args": ["@scope/pkg@1.2.3"]',
                        '"uvx", "args": ["tool==1.2.3"]', '"uv", "args": ["run", "--locked", "s.py"]',
                        '"node", "args": ["${CLAUDE_PLUGIN_ROOT}/s.mjs"]'):
            with self.subTest(command=command):
                config = ('{"mcpServers": {"s": {"command": %s}}}' % command).encode()
                self.assertEqual([], self.build.directory_findings(self.plugin_with({".mcp.json": config}))[0])
        blocks, _ = self.build.directory_findings(self.plugin_with(
            {".mcp.json": b'{"mcpServers": {"s": {"command": "npx", "args": ["@scope/pkg"]}}}'}))
        self.assertTrue(any("npx @scope/pkg" in b for b in blocks), blocks)

    def test_what_holds(self):
        many = {f"skills/a/references/{i}.md": b"x" for i in range(self.build.DIRECTORY_MAX_FILES)}
        cases = {
            "too many files": (many, "files; over 512"),
            "a large file": ({"skills/a/big.md": b"x" * (256 * 1024 + 1)}, "skills/a/big.md is 262145 bytes"),
            "a binary file": ({"skills/a/doc.pdf": b"%PDF\0"}, "skills/a/doc.pdf is a binary file"),
            "an MCP bundle": ({"mcp/server.mcpb": b"x"}, "a bundled MCP server"),
            "a lockfile install": ({"package.json": b"{}", "package-lock.json": b"{}"}, "package.json beside a lockfile"),
        }
        for name, (extra, needle) in cases.items():
            with self.subTest(case=name):
                blocks, holds = self.build.directory_findings(self.plugin_with(extra))
                self.assertEqual([], blocks)
                self.assertTrue(any(needle in h for h in holds), holds)

    def test_images_and_fonts_are_not_held_by_size(self):
        big = b"\0" * (256 * 1024 + 1)
        self.assertEqual(([], []), self.build.directory_findings(self.plugin_with(
            {"assets/hero.png": big, "assets/font.woff2": big})))


class TheAuditsReleaseMediums(unittest.TestCase):
    """P54 part 8, the audit of 2026-10-14's §3.7: D1, D2 and D3. The first two
    read files outside the plugin, so they skip in an unpacked copy (Codex on #152)."""

    @unittest.skipUnless(TOOLING, "needs the repository: release.yml and tooling/ sit outside the plugin")
    def test_the_release_job_pins_its_actions_and_keeps_no_credential(self):
        """D2: release.yml pinned checkout and setup-uv by tag while holding
        `contents: write` and GH_TOKEN, and checkout kept its credential."""
        text = (REPO / ".github" / "workflows" / "release.yml").read_bytes().decode("utf-8")
        uses = re.findall(r"^\s*-?\s*uses:\s*(\S+)", text, re.M)
        self.assertEqual(4, len(uses))                      # two in `release`, two in `distribute`
        for action in uses:
            with self.subTest(action=action):
                self.assertRegex(action, r"@[0-9a-f]{40}$")
        checkouts = [m.start() for m in re.finditer(r"actions/checkout@", text)]
        self.assertEqual(2, len(checkouts))
        for start in checkouts:
            with self.subTest(checkout_at=start):
                self.assertRegex(text[start:start + 400], r"persist-credentials:\s*false")

    @unittest.skipUnless(TOOLING, "needs the repository: release.yml sits outside the plugin")
    def test_the_distribution_is_written_only_forward(self):
        """4.0.0: the `distribute` job writes the distribution repository with
        a deploy key, after the release, never forcing a push or rewriting a
        release's tag, and holds no token for this repository."""
        text = (REPO / ".github" / "workflows" / "release.yml").read_bytes().decode("utf-8")
        job = text[text.index("\n  distribute:"):]
        self.assertIn("needs: release", job)
        self.assertRegex(job, r"permissions:\s*\n\s*contents: read")
        self.assertIn("secrets.DIST_DEPLOY_KEY", job)
        self.assertIn("StrictHostKeyChecking=yes", job)
        self.assertIn('git ls-remote --exit-code --tags origin "refs/tags/$GITHUB_REF_NAME"', job)
        self.assertIn("--tree", job)
        self.assertNotIn("GH_TOKEN", job)
        # Codex on #181: main and the tag move together or not at all; every
        # release waits its turn; an older release never replaces a newer one.
        pushes = re.findall(r"git push[^\n]*", job)
        self.assertEqual(['git push --quiet --atomic origin main "refs/tags/$GITHUB_REF_NAME"'], pushes)
        self.assertRegex(job, r"concurrency:\s*\n\s*group: distribute\s*\n\s*queue: max")
        self.assertNotIn("cancel-in-progress", job)
        self.assertIn("sort -V", job)
        self.assertIn("an older release never replaces it", job)
        self.assertNotRegex(job, r"--force|\+refs/|\+main")

    @unittest.skipUnless(TOOLING, "needs the repository: release.yml and tooling/ sit outside the plugin")
    def test_the_tooling_readme_says_why_a_local_build_differs(self):
        """D1: tooling/README.md said a build is "byte-identical on a rebuild",
        though build.py says Windows' zlib-ng and the release's zlib differ."""
        text = (TOOLING / "README.md").read_bytes().decode("utf-8")
        self.assertNotIn("byte-identical on a rebuild", text)
        for needle in ("zlib-ng", "compare.py"):
            with self.subTest(needle=needle):
                self.assertIn(needle, text)

    def test_the_readme_counts_the_node_scripts(self):
        """D3: the plugin README said "the three browser scripts need Node";
        there are six entry scripts in `.mjs`."""
        words = {5: "five", 6: "six", 7: "seven", 8: "eight"}
        entries = [p for p in SKILLS.glob("*/scripts/*.mjs")
                   if p.name not in ("project_config.mjs", "browser_common.mjs")]
        readme = (SKILLS.parent / "README.md").read_bytes().decode("utf-8")
        self.assertIn(f"the {words[len(entries)]} `.mjs`", " ".join(readme.split()))


if __name__ == "__main__":
    unittest.main()
