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

3.1.0:
- LC-A10: `lib/` and `libs/` counted as vendor folders, so SvelteKit's
  `src/lib` — where its components live — was silently left out of the census
  and the codemod, even when a file there was named explicitly. Vendor files
  that were excluded were never mentioned.
- XC-A7: every literal's line number was counted from the top of the file, so
  one long line (minified CSS, a many-layer shadow) was quadratic.
- LC-A5: a spread-only focus ring (`0 0 0 3px …`) was clustered with the card
  shadows and rewritten to `var(--elevation-card)` at "snapped" confidence,
  deleting the keyboard focus indicator (WCAG 2.4.7).
- The proposed tokens.css repeated the starter's faults (SS-A1, SS-A2,
  SS-A4): roles resolved once on :root, so data-density and data-theme on a
  section changed nothing; no color-scheme; dark error text, .inverse text
  and the control border under AA. A migrated project inherited all of them.
"""
from __future__ import annotations

import json
import pathlib
import re
import shutil
import subprocess
import tempfile
import time
import unittest

import test_starter_css as starter
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


class VendorScopeAndScale(TempDirTest):
    """LC-A10 and XC-A7."""

    extract = MigrationPipeline.extract

    MAPPING = {"schema": "design-token-migration/mapping@1",
               "rules": [{"id": "space-13", "kind": "spacing", "scope": "value",
                          "prop_classes": ["gap"], "match": ["13px"],
                          "replacement": "var(--gap-related)", "confidence": "snap"}]}

    def test_sveltekit_src_lib_is_part_of_the_census(self):
        self.write("src/lib/components/button.css", ".b { padding: 13px; color: #123456; }\n")
        _, data = self.extract("src")
        self.assertTrue(any("src/lib/components/button.css" in l["file"].replace("\\", "/")
                            for l in data["literals"]), data["problems"])

    def test_excluded_vendor_files_are_reported(self):
        self.write("src/app.css", ".a { padding: 13px; }\n")
        self.write("src/vendor/datepicker.css", ".dp { padding: 7px; }\n")
        _, data = self.extract("src")
        self.assertTrue(any("vendor" in p for p in data["problems"]), data["problems"])

    def test_the_codemod_rewrites_files_named_explicitly_and_can_include_vendor(self):
        mapping = self.write("mapping.json", json.dumps(self.MAPPING))
        lib = self.write("src/lib/components/button.css", ".b { margin: 13px; }\n")
        vend = self.write("src/vendor/datepicker.css", ".t { margin: 13px; }\n")
        run_py("design-token-migration", "apply_codemod", "-m", mapping, "--apply", lib,
               cwd=self.tmp)
        self.assertIn("var(--gap-related)", lib.read_text(encoding="utf-8"))
        run_py("design-token-migration", "apply_codemod", "-m", mapping, "--apply", "src",
               cwd=self.tmp)
        self.assertIn("13px", vend.read_text(encoding="utf-8"))          # skipped by default
        proc = run_py("design-token-migration", "apply_codemod", "-m", mapping, "--apply",
                      "--include-vendor", "src", cwd=self.tmp)
        self.assertIn("var(--gap-related)", vend.read_text(encoding="utf-8"), output(proc))

    def timed(self, n):
        css = self.write(f"min{n}/app.css", "".join(
            f".c{i}{{margin:{i % 40}px;color:#3a{i % 10}a3a;padding:7px 13px}}" for i in range(n)))
        start = time.perf_counter()
        proc = run_py("design-token-migration", "extract_literals", css.parent, "--format",
                      "json", "-o", self.tmp / f"lits{n}.json", cwd=self.tmp, timeout=900)
        self.assertIn(proc.returncode, (0, 1), output(proc))
        return time.perf_counter() - start

    def test_a_minified_stylesheet_is_extracted_in_roughly_linear_time(self):
        small, large = self.timed(2000), self.timed(8000)
        self.assertLess(large / small, 6, f"2,000 rules {small:.1f}s, 8,000 rules {large:.1f}s")


class FocusRingsStayFocusRings(TempDirTest):
    """LC-A5."""

    extract = MigrationPipeline.extract
    cluster = MigrationPipeline.cluster

    def test_a_spread_only_focus_ring_is_not_mapped_to_an_elevation(self):
        self.write("src/button.css",
                   ".button:focus-visible { box-shadow: 0 0 0 3px rgba(47,109,246,.4); }\n"
                   ".card { box-shadow: 0 1px 2px rgba(0,0,0,.08); }\n"
                   ".panel { box-shadow: 0 1px 3px rgba(0,0,0,.1); }\n")
        literals, _ = self.extract("src")
        mapping, _ = self.cluster(literals)
        ring = [r for r in mapping["rules"] if any("0 0 0 3px" in m for m in r["match"])]
        self.assertEqual(len(ring), 1, mapping["rules"])
        self.assertEqual(ring[0]["replacement"], "var(--elevation-focus)")
        self.assertEqual(ring[0]["confidence"], "review")      # not applied by --skip-review
        cards = [r for r in mapping["rules"] if any("0 1px" in m for m in r["match"])]
        self.assertTrue(cards and all("elevation-card" in r["replacement"] for r in cards))

    def test_an_inset_border_ring_is_left_for_a_hand_decision(self):
        self.write("src/field.css", ".field { box-shadow: inset 0 0 0 1px #d4d4d4; }\n")
        literals, _ = self.extract("src")
        mapping, report = self.cluster(literals)
        self.assertFalse([r for r in mapping["rules"] if r["kind"] == "shadow"], mapping["rules"])
        self.assertIn("border drawn with a shadow", report)


def proposed_tokens_css() -> str:
    """extract_literals → cluster_values on a small project; the proposed
    tokens.css, comments removed."""
    with tempfile.TemporaryDirectory(prefix="wds-test-", ignore_cleanup_errors=True) as holder:
        tmp = pathlib.Path(holder)
        (tmp / "src").mkdir()
        (tmp / "src" / "card.css").write_text(
            ".card { padding: 13px; color: #3a3a3a; background: #fafafa; "
            "border: 1px solid #d0d0d0; box-shadow: 0 1px 2px rgba(0, 0, 0, .2); }\n",
            encoding="utf-8")
        run_py("design-token-migration", "extract_literals", tmp / "src", "--format", "json",
               "-o", tmp / "literals.json", cwd=tmp)
        proc = run_py("design-token-migration", "cluster_values", tmp / "literals.json",
                      "-o", tmp / "proposal", cwd=tmp)
        tokens = tmp / "proposal" / "tokens.css"
        if not tokens.exists():
            raise AssertionError(f"no proposal was written: {output(proc)}")
        text = tokens.read_text(encoding="utf-8")
    return re.sub(r"/\*.*?\*/", " ", text, flags=re.S)


class ProposedTokensWorkOnASection(unittest.TestCase):
    """The proposal's tokens.css, checked the way the starter's is."""

    @classmethod
    def setUpClass(cls):
        cls.tokens = proposed_tokens_css()

    def test_roles_are_declared_where_density_and_theme_are_set(self):
        for prop, where in (("--gap-grouped", "[data-density]"), ("--pad-card", "[data-density]"),
                            ("--elevation-card", "[data-theme]"), ("--shadow-focus", "[data-theme]")):
            with self.subTest(prop=prop):
                self.assertTrue(any(where in s for s in starter.declaring(self.tokens, prop)))

    def test_the_dark_theme_carries_its_colour_scheme(self):
        dark = [d for s, d in starter.rules(self.tokens) if s == ['[data-theme="dark"]']]
        self.assertTrue(any(d.get("color-scheme") == "dark" for d in dark))


class ProposedTokensContrast(starter.StarterRoleContrast):
    """The starter's contrast checks, run on the proposal."""

    @classmethod
    def tokens_text(cls) -> str:
        return proposed_tokens_css()


if __name__ == "__main__":
    unittest.main()
