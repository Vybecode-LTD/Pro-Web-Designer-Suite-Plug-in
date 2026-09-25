"""design-token-migration: extract_literals.py, cluster_values.py, apply_codemod.py.

Regressions covered:
- Tailwind `max-w-[…]`/`min-w-`/`max-h-`/`min-h-` were classed as margin ("gap")
  because they start with "m", so `max-w-[16px]` became the non-class `max-w-grouped`.
- A quoted hex colour in a JSX `style={{…}}` was counted twice (inline-style and
  js-string), inflating the census.
- JSX inline-style values were counted as "mechanically replaceable" although
  apply_codemod never rewrites them (Law 4, Phase 4f by hand).
- A mapping.json that is not JSON, or not a mapping, exited 1 (the "something was
  skipped" code) instead of 2 (bad invocation).
- The z-index note said "an 7-rung ladder" against the contract's eight rungs;
  the ladder is the seven rungs above --z-base.
- The "refuses to write over uncommitted changes" guard missed any file whose
  name has non-ASCII characters: `git status --porcelain` prints such names
  quoted and octal-escaped ("caf\\303\\251.css"), which never matched a real path.
- On Windows git's UTF-8 output was decoded as cp1252, so a repository under a
  folder with non-ASCII characters either crashed the script or turned the
  guard off for the whole repository ("treating every file as clean").
"""
from __future__ import annotations

import json
import shutil
import subprocess
import unittest

from wds_support import TempDirTest, output, run_py

GIT = shutil.which("git")
CSS = ".card { margin: 13px; }\n"


class ApplyCodemodDirtyGuard(TempDirTest):

    def setUp(self):
        super().setUp()
        self.mapping = self.write("mapping.json", json.dumps({
            "schema": "design-token-migration/mapping@1",
            "rules": [{"id": "space-13", "kind": "spacing", "scope": "value",
                       "prop_classes": ["gap"], "match": ["13px"],
                       "replacement": "var(--space-3)", "confidence": "snap"}],
        }))

    def apply(self, target, cwd):
        return run_py("design-token-migration", "apply_codemod",
                      "-m", self.mapping, "--apply", target, cwd=cwd)

    def git_repo(self, name):
        repo = self.tmp / name
        repo.mkdir(parents=True)
        subprocess.run([GIT, "init", "-q", str(repo)], check=True, capture_output=True)
        return repo

    def test_a_clean_file_outside_git_is_rewritten(self):
        css = self.write("plain/a.css", CSS)
        proc = self.apply(css.parent, cwd=self.tmp)
        self.assertIn("var(--space-3)", css.read_text(encoding="utf-8"), output(proc))

    @unittest.skipUnless(GIT, "git is not installed")
    def test_uncommitted_file_with_a_non_ascii_name_is_left_alone(self):
        repo = self.git_repo("repo")
        css = repo / "styles" / "café.css"
        css.parent.mkdir()
        css.write_text(CSS, encoding="utf-8")
        proc = self.apply(css.parent, cwd=repo)
        self.assertEqual(css.read_text(encoding="utf-8"), CSS, output(proc))
        self.assertIn("uncommitted", output(proc))

    @unittest.skipUnless(GIT, "git is not installed")
    def test_repository_under_a_non_ascii_folder_keeps_the_guard(self):
        repo = self.git_repo("Łódź café")
        css = repo / "a.css"
        css.write_text(CSS, encoding="utf-8")
        proc = self.apply(css, cwd=repo)
        self.assertNotIn("Traceback", output(proc))
        self.assertNotIn("treating every file as clean", output(proc))
        self.assertEqual(css.read_text(encoding="utf-8"), CSS, output(proc))
        self.assertIn("uncommitted", output(proc))

    @unittest.skipUnless(GIT, "git is not installed")
    def test_a_staged_rename_and_the_entry_after_it_are_both_guarded(self):
        repo = self.git_repo("renames")
        (repo / "old.css").write_text(CSS, encoding="utf-8")
        git = [GIT, "-C", str(repo), "-c", "user.name=wds-test",
               "-c", "user.email=wds-test@example.invalid"]
        for args in (["add", "old.css"], ["commit", "-q", "-m", "fixture"], ["mv", "old.css", "new.css"]):
            subprocess.run(git + args, check=True, capture_output=True)
        (repo / "other.css").write_text(CSS, encoding="utf-8")
        proc = self.apply(repo, cwd=repo)
        for name in ("new.css", "other.css"):
            self.assertEqual((repo / name).read_text(encoding="utf-8"), CSS, f"{name}: {output(proc)}")


class MigrationPipeline(TempDirTest):
    """extract_literals → cluster_values → apply_codemod, as SKILL.md runs them."""

    def extract(self, src):
        literals = self.tmp / "literals.json"
        proc = run_py("design-token-migration", "extract_literals", src,
                      "--format", "json", "-o", literals, cwd=self.tmp)
        self.assertTrue(literals.exists(), output(proc))
        return literals, json.loads(literals.read_text(encoding="utf-8"))

    def cluster(self, literals):
        out = self.tmp / "proposal"
        proc = run_py("design-token-migration", "cluster_values", literals, "-o", out, cwd=self.tmp)
        self.assertIn(proc.returncode, (0, 1), output(proc))
        return (json.loads((out / "mapping.json").read_text(encoding="utf-8")),
                (out / "reconciliation.md").read_text(encoding="utf-8"))

    def test_tailwind_size_utilities_are_not_classed_as_margin(self):
        self.write("src/Thing.tsx", 'export const T = () => <div className="max-w-[16px] min-h-[16px] '
                                    'min-w-[16px] max-h-[16px] mt-[16px]" />;\n')
        mapping, _ = self.cluster(self.extract(self.tmp / "src")[0])
        tw = [r for r in mapping["rules"] if r.get("scope") == "tailwind"]
        self.assertTrue(any(r["match"][0].startswith("mt-") for r in tw), tw)
        for rule in tw:
            if rule["match"][0].startswith(("max-w-", "min-w-", "max-h-", "min-h-")):
                self.assertNotIn("gap", rule["prop_classes"], rule)

    def test_a_jsx_inline_colour_is_counted_once(self):
        self.write("src/Card.jsx", 'export const C = () => <p style={{ color: "#3a3a3a" }}>x</p>;\n')
        _, data = self.extract(self.tmp / "src")
        hits = [l for l in data["literals"] if l["normalized"] == "#3a3a3a"]
        self.assertEqual(len(hits), 1, hits)

    def test_inline_styles_are_not_counted_as_mechanically_replaceable(self):
        self.write("src/Card.jsx", 'export const C = () => <p style={{ color: "#3a3a3a" }}>x</p>;\n')
        self.write("src/card.css", ".card { color: #3a3a3a; }\n")
        mapping, report = self.cluster(self.extract(self.tmp / "src")[0])
        applied = sum(r["occurrences"] for r in mapping["rules"] if "#3a3a3a" in r["match"])
        self.assertEqual(applied, 1, mapping["rules"])
        self.assertIn("inline style", report)

    def test_a_bad_mapping_is_a_bad_invocation(self):
        css = self.write("plain/a.css", ".card { margin: 13px; }\n")
        for name, text in (("not-json.json", "this is not json"), ("not-mapping.json", '{"foo": 1}')):
            with self.subTest(mapping=name):
                proc = run_py("design-token-migration", "apply_codemod", "-m", self.write(name, text),
                              css, cwd=self.tmp)
                self.assertEqual(proc.returncode, 2, output(proc))

    def test_the_z_index_note_counts_the_rungs_above_base(self):
        rules = "\n".join(f".z{i} {{ z-index: {v}; }}" for i, v in
                          enumerate((1, 5, 10, 20, 50, 100, 200, 500, 999, 9999)))
        self.write("src/z.css", rules + "\n")
        _, report = self.cluster(self.extract(self.tmp / "src")[0])
        self.assertNotIn("an 7-rung", report)
        self.assertIn("--z-base", report)


if __name__ == "__main__":
    unittest.main()
