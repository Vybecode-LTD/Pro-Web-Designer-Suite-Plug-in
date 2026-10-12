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
3.3.0:
- N12: `//` was a comment in plain CSS, as in the audit (SB-A9), so after
  `url(https://…)` the census filed every literal under `background` and the
  codemod rewrote none of them.
3.5.0:
- P26: `extract_literals -o` into a folder that did not exist failed, where
  cluster_values, extract_system and diff_system create it; /migrate writes
  its census to design-reports/migration/.
"""
from __future__ import annotations

import json
import pathlib
import re
import shutil
import subprocess
import sys
import time
import unittest

import test_starter_css as starter
from wds_support import SKILLS, TempDirTest, env, output, run_py, temp_dir

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
        subprocess.run([GIT, "init", "-q", str(repo)], check=True, capture_output=True, env=env())
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
            subprocess.run(git + args, check=True, capture_output=True, env=env())
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

    def codemod(self, src):
        proc = run_py("design-token-migration", "apply_codemod", "-m",
                      self.tmp / "proposal" / "mapping.json", src, cwd=self.tmp)
        self.assertIn(proc.returncode, (0, 1), output(proc))
        return proc.stdout.decode("utf-8")

    def pad_token(self, mapping):
        return next(r["token"] for r in mapping["rules"]
                    if r["kind"] == "spacing" and "padding" in r.get("props", []))

    def test_a_negative_cancel_points_at_its_parents_padding_token(self):
        # LC-A11, the reference's own example (fx/mig2): the bleed must cancel the
        # token the padding became, not the one 16px in a margin clusters to.
        self.write("src/Card.module.css",
                   ".card { padding: 16px; font-size: 15px; }\n"
                   ".card__media { margin: -16px -16px 16px; }\n"
                   ".body { font-size: 15px; }\n")
        self.write("src/panel.css",
                   ".panel { padding: 16px; }\n.panel > .bleed { margin-inline: -16px; }\n"
                   ".well { padding: 16px; .media { margin-block-start: -16px; } }\n")
        mapping, _ = self.cluster(self.extract(self.tmp / "src")[0])
        pad = self.pad_token(mapping)
        gap = next(r["token"] for r in mapping["rules"]
                   if r["kind"] == "spacing" and "gap" in r.get("prop_classes", []))
        self.assertNotEqual(pad, gap, mapping["rules"])
        diff = self.codemod(self.tmp / "src")
        cancel = f"calc(var({pad}) * -1)"
        self.assertIn(f"+.card__media {{ margin: {cancel} {cancel} var({gap}); }}", diff)
        self.assertIn(f"+.panel > .bleed {{ margin-inline: {cancel}; }}", diff)
        self.assertIn(f".media {{ margin-block-start: {cancel}; }}", diff)

    def test_a_cancel_keeps_to_its_axis_and_reads_a_grouped_selector(self):
        # Codex on #49: `-8px` inline is not the 8px block padding's cancel, and a
        # padding declared for `.a, .panel` is `.panel`'s padding.
        self.write("src/a.css", ".card { padding: 8px 16px; }\n.card__media { margin-inline: -8px; }\n"
                                ".a, .panel { padding: 16px; }\n.panel > .bleed { margin-inline: -16px; }\n")
        mapping, _ = self.cluster(self.extract(self.tmp / "src")[0])

        def token(klass, value):
            return next(r["token"] for r in mapping["rules"]
                        if klass in r.get("prop_classes", []) and value in r["match"])

        diff = self.codemod(self.tmp / "src")
        media = next(l for l in diff.splitlines() if l.startswith("+.card__media"))
        self.assertNotIn(f"var({token('pad-block', '8px')})", media)
        self.assertIn(f"+.panel > .bleed {{ margin-inline: calc(var({token('pad-all', '16px')}) * -1); }}",
                      diff)

    def test_a_cancel_keeps_to_its_side_the_cascade_and_each_selector(self):
        # CodeRabbit on #49: the right margin is not the left padding's cancel; a
        # later `padding-inline` wins over `padding`; each member of a grouped
        # margin selector finds its own parent.
        self.write("src/a.css", ".s { padding-left: 16px; padding-right: 8px; }\n"
                                ".s__x { margin-right: -16px; }\n"
                                ".c { padding: 16px; padding-inline: 16px; }\n"
                                ".c__x { margin-inline: -16px; }\n"
                                ".g { padding: 16px; }\n.h { padding: 16px; }\n"
                                ".g__m, .h__m { margin-block-start: -16px; }\n")
        mapping, _ = self.cluster(self.extract(self.tmp / "src")[0])

        def token(klass, value):
            return next(r["token"] for r in mapping["rules"]
                        if klass in r.get("prop_classes", []) and value in r["match"])

        inline16, all16 = token("pad-inline", "16px"), token("pad-all", "16px")
        self.assertNotEqual(inline16, all16, mapping["rules"])
        diff = self.codemod(self.tmp / "src")
        line = {l.split(" {")[0][1:]: l for l in diff.splitlines() if l.startswith("+.")}
        self.assertNotIn(f"var({inline16})", line[".s__x"])
        self.assertIn(f"margin-inline: calc(var({inline16}) * -1)", line[".c__x"])
        self.assertIn(f"margin-block-start: calc(var({all16}) * -1)", line[".g__m, .h__m"])

    def test_a_cancel_reads_the_padding_of_its_own_media_query(self):
        # CodeRabbit on #49: a padding in one @media is not a margin's elsewhere.
        self.write("src/a.css", "@media (min-width: 40rem) { .p { padding: 16px; } }\n"
                                "@media print { .p__x { margin-inline: -16px; } }\n"
                                "@media print { .q { padding: 16px; } .q__x { margin-inline: -16px; } }\n")
        mapping, _ = self.cluster(self.extract(self.tmp / "src")[0])
        all16 = next(r["token"] for r in mapping["rules"]
                     if "pad-all" in r.get("prop_classes", []) and "16px" in r["match"])
        lines = self.codemod(self.tmp / "src").splitlines()
        p_x = next(l for l in lines if l.startswith("+@media print { .p__x"))
        q_x = next(l for l in lines if l.startswith("+@media print { .q {"))
        self.assertNotIn(f"var({all16})", p_x)
        self.assertIn(f".q__x {{ margin-inline: calc(var({all16}) * -1); }}", q_x)

    def test_a_padding_set_in_two_blocks_is_not_cancelled(self):
        # CodeRabbit on #49: a later `.p` padding wins over a print one in print,
        # and an unlayered padding wins over a later layered one. Which padding
        # applies is not certain, so the margin keeps its own gap token.
        self.write("src/a.css", "@media print { .p { padding: 16px; } }\n.p { padding: 8px; }\n"
                                "@media print { .p__x { margin-inline: -16px; } }\n"
                                ".l { padding: 8px; }\n@layer components { .l { padding: 16px; } }\n"
                                ".l__x { margin-inline: -16px; }\n"
                                ".n { padding: 16px; @media print { padding: 8px; } }\n"
                                ".n__x { margin-inline: -16px; }\n")
        mapping, _ = self.cluster(self.extract(self.tmp / "src")[0])
        gap = next(r["token"] for r in mapping["rules"]
                   if r["kind"] == "spacing" and "gap" in r.get("prop_classes", []))
        lines = self.codemod(self.tmp / "src").splitlines()
        for name in ("p", "l", "n"):
            with self.subTest(rule=name):
                line = next(l for l in lines if f".{name}__x {{" in l and l.startswith("+"))
                self.assertIn(f"margin-inline: calc(var({gap}) * -1)", line)

    def test_an_important_padding_is_one_value_and_wins_its_block(self):
        # CodeRabbit on #49: `!important` was split off as a second slot, so
        # `padding: 16px !important` read as block padding only, and the last
        # declaration won even beside an earlier `!important` one.
        self.write("src/a.css", ".i { padding: 16px !important; padding: 8px; }\n"
                                ".i__x { margin-inline: -16px; }\n"
                                ".j { padding: 16px !important; }\n.j__x { margin-inline: -16px; }\n")
        mapping, _ = self.cluster(self.extract(self.tmp / "src")[0])
        all16 = next(r["token"] for r in mapping["rules"]
                     if "pad-all" in r.get("prop_classes", []) and "16px" in r["match"])
        lines = self.codemod(self.tmp / "src").splitlines()
        for name in ("i", "j"):
            with self.subTest(rule=name):
                line = next(l for l in lines if l.startswith(f"+.{name}__x"))
                self.assertIn(f"margin-inline: calc(var({all16}) * -1)", line)

    def test_a_logical_side_pairs_only_when_both_directions_agree(self):
        # CodeRabbit on #49: `padding-inline-start` is the left padding only left
        # to right; in a right-to-left page `.r__x`'s left padding is 8px.
        self.write("src/a.css", ".r { padding-inline-start: 16px; padding-inline-end: 8px; }\n"
                                ".r__x { margin-left: -16px; }\n"
                                ".s { padding-inline-start: 16px; padding-inline-end: 16px; }\n"
                                ".s__x { margin-inline-start: -16px; }\n"
                                ".t { padding: 16px; }\n.t__x { margin-inline-start: -16px; }\n")
        mapping, _ = self.cluster(self.extract(self.tmp / "src")[0])

        def token(klass):
            return next(r["token"] for r in mapping["rules"]
                        if klass in r.get("prop_classes", []) and "16px" in r["match"])

        lines = {l.split(" {")[0][1:]: l for l in self.codemod(self.tmp / "src").splitlines()
                 if l.startswith("+.")}
        self.assertIn(f"calc(var({token('gap')}) * -1)", lines[".r__x"])
        self.assertIn(f"calc(var({token('pad-inline')}) * -1)", lines[".s__x"])
        self.assertIn(f"calc(var({token('pad-all')}) * -1)", lines[".t__x"])

    def test_a_negative_margin_with_nothing_to_cancel_keeps_its_own_token(self):
        # Control: no padding in the parent rule, so it is a spacing value of its own.
        self.write("src/a.css", ".row { gap: 16px; }\n.row__item { margin-block-start: -16px; }\n"
                                ".box { padding: 16px; }\n")
        mapping, _ = self.cluster(self.extract(self.tmp / "src")[0])
        gap = next(r["token"] for r in mapping["rules"]
                   if r["kind"] == "spacing" and "gap" in r.get("prop_classes", []))
        self.assertIn(f"margin-block-start: calc(var({gap}) * -1)", self.codemod(self.tmp / "src"))

    def test_a_type_tie_snaps_up_even_when_the_smaller_step_is_commoner(self):
        # LC-A12: "15px becomes 16, text does not shrink", though 14px is commoner.
        self.write("src/a.css", ".a { font-size: 15px; }\n" + "".join(
            f".b{i} {{ font-size: 14px; }}\n" for i in range(3)))
        mapping, _ = self.cluster(self.extract(self.tmp / "src")[0])
        rule = next(r for r in mapping["rules"] if r["kind"] == "type" and "15px" in r["match"])
        self.assertEqual(rule["token"], "--type-body", rule)
        self.assertEqual(rule["delta_px"], 1.0, rule)
        self.assertIn("UP to 16px", rule["note"])

    def test_a_duration_moves_by_milliseconds_in_the_report(self):
        # LC-A23: the review table printed a duration's delta as "-30px".
        self.write("src/a.css", ".a { transition: opacity 250ms ease; }\n")
        _, report = self.cluster(self.extract(self.tmp / "src")[0])
        row = next(l for l in report.splitlines() if l.startswith("| `250ms"))
        self.assertIn("| -30ms |", row)

    def test_a_held_colour_is_deleted_not_re_pointed(self):
        # LC-A23: framework-migrations.md says delete a `$brand` variable at the
        # call sites; the report told the reader to re-point it.
        # Codex and CodeRabbit on #54: only a preprocessor variable is deleted; a
        # custom property points at a role, and a plain property keeps its line.
        self.write("src/a.scss", "$brand: #2f6df6;\n.a { color: $brand; }\n"
                                 ".b { --brand-x: #e8440a; }\n"
                                 ".c { scrollbar-color: #1f9d55 transparent; }\n")
        _, report = self.cluster(self.extract(self.tmp / "src")[0])
        recs = {h: report.split(f"`{h}`", 1)[1].split("**`", 1)[0]
                for h in ("$brand", "--brand-x", "scrollbar-color")}
        self.assertIn("Delete it", recs["$brand"])
        self.assertIn("Point it at the role", recs["--brand-x"])
        self.assertIn("keep the declaration", recs["scrollbar-color"])
        self.assertNotIn("Delete it", recs["scrollbar-color"])

    def test_one_colour_in_two_kinds_of_holder_gets_both_kinds_of_advice(self):
        # CodeRabbit on #54: the cluster's first holder chose the advice for all.
        self.write("src/a.scss", "$mix: #7a3cf0;\n.a { color: $mix; }\n.b { --mix: #7a3cf0; }\n")
        _, report = self.cluster(self.extract(self.tmp / "src")[0])
        self.assertIn("held in the preprocessor variable `$mix`", report)
        self.assertIn("held in the custom property `--mix`", report)
        # CodeRabbit on #54, again: two plain properties named only the first.
        self.write("src/a.scss", ".c { scrollbar-color: #1f9d55 transparent; }\n"
                                 ".d { background-image: linear-gradient(#1f9d55, transparent); }\n")
        _, report = self.cluster(self.extract(self.tmp / "src")[0])
        self.assertIn("in `scrollbar-color`, a property with no colour role", report)
        self.assertIn("in `background-image`, a property with no colour role", report)

    def test_the_review_table_names_its_units(self):
        # CodeRabbit on #54: a duration sat under "more than 2px".
        self.write("src/a.css", ".a { transition: opacity 250ms ease; }\n")
        _, report = self.cluster(self.extract(self.tmp / "src")[0])
        self.assertIn("## Replacements to review", report)
        self.assertNotIn("more than 2px\n", report)
        # CodeRabbit on #54: a colour's row read "+0px"; its distance is a ΔE.
        self.write("src/a.css", "".join(f".c{i} {{ color: {c}; }}\n" for i, c in enumerate(
            ("#2f6df6", "#2f6df6", "#5a5a5a", "#8a6d3b", "#c0392b"))))
        _, report = self.cluster(self.extract(self.tmp / "src")[0])
        review = report.split("## Replacements to review", 1)[1]
        row = next(l for l in review.splitlines() if l.startswith("| `#8a6d3b`"))
        self.assertIn("| ΔE 0.043 |", row)

    def test_the_z_index_note_counts_the_rungs_above_base(self):
        rules = "\n".join(f".z{i} {{ z-index: {v}; }}" for i, v in
                          enumerate((1, 5, 10, 20, 50, 100, 200, 500, 999, 9999)))
        self.write("src/z.css", rules + "\n")
        _, report = self.cluster(self.extract(self.tmp / "src")[0])
        self.assertNotIn("an 7-rung", report)
        self.assertIn("--z-base", report)


class TheWorkedRun(TempDirTest):
    """LC-C12: references/worked-run.md is the 8-file fixture in
    tests/fixtures/worked-run, run the way the page runs it. Every number the page
    quotes (the census, the clustering, the replacements, the audit before and
    after, the remaining errors) must be what the tools print for it today."""

    KINDS = "color spacing type radius stroke duration shadow z-index tracking".split()

    def test_the_page_quotes_what_the_tools_print(self):
        import collections
        shutil.copytree(pathlib.Path(__file__).resolve().parent / "fixtures" / "worked-run" / "src",
                        self.tmp / "src")
        def census():
            # A relative path, as the page runs it.
            proc = subprocess.run([sys.executable, "-B", str(SKILLS / "web-design-studio" / "scripts"
                                                            / "audit_design.py"), "src", "--json"],
                                  cwd=self.tmp, capture_output=True, env=env())
            found = json.loads(proc.stdout)
            errors = [f for f in found if f["severity"] == "error"]
            return ({"errors": len(errors), "warnings": len(found) - len(errors),
                     **collections.Counter(f["law"] for f in errors)},
                    collections.Counter(f"{f['law']} {f['rule']}" for f in errors))

        before, _ = census()
        printed = output(run_py("design-token-migration", "extract_literals", "./src", cwd=self.tmp))
        run_py("design-token-migration", "extract_literals", "./src", "--format", "json",
               "-o", "literals.json", cwd=self.tmp)
        printed += output(run_py("design-token-migration", "cluster_values", "literals.json",
                                 "-o", "./proposal", cwd=self.tmp))
        shutil.copyfile(self.tmp / "proposal" / "tokens.css", self.tmp / "src" / "styles" / "tokens.css")
        made = {}
        for kind in self.KINDS:
            out = output(run_py("design-token-migration", "apply_codemod", "./src", "-m",
                                "proposal/mapping.json", "--kind", kind, "--apply", cwd=self.tmp))
            m = re.search(r"(\d+) replacement\(s\) in", out)
            if m and int(m.group(1)):
                made[kind] = int(m.group(1))
        after, remaining = census()

        page = (SKILLS / "design-token-migration" / "references" / "worked-run.md").read_text(encoding="utf-8")
        flat = " ".join(printed.split())
        for line in re.findall(r"^#   (.+)$", page, re.M):
            with self.subTest(line=line):
                m = re.match(r"(\d+) replacements: (.+)$", line)
                if m:
                    quoted = {k: int(n) for k, n in re.findall(r"([\w-]+) (\d+)", m.group(2))}
                    self.assertEqual((int(m.group(1)), quoted), (sum(made.values()), made))
                else:
                    self.assertIn(" ".join(line.split()), flat)
        rows = re.findall(r"^\| (Audit errors|Audit warnings|L\d)[^|]*\| (\d+) \| \**(\d+)\** \|$", page, re.M)
        self.assertEqual(len(rows), 7, rows)
        for label, was, now in rows:
            key = {"Audit errors": "errors", "Audit warnings": "warnings"}.get(label, label)
            with self.subTest(row=label):
                self.assertEqual((int(was), int(now)), (before.get(key, 0), after.get(key, 0)))
        listed = {f: int(n) for n, f in re.findall(r"^\| (\d+) \| `(L\d [\w-]+)` \|", page, re.M)}
        self.assertEqual(listed, dict(remaining))
        self.assertIn(f"The {after['errors']} remaining errors", page)


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

    def test_indented_sass_is_reported_not_counted_as_clean(self):
        # N13: the census follows braces and indented Sass has none, so a .sass
        # file full of literals was "no hardcoded design values found".
        self.write("src/components/card.sass", ".card\n  padding: 13px\n  color: #123456\n")
        _, data = self.extract("src")
        self.assertEqual([], data["literals"])
        self.assertTrue(any("indented Sass" in p and "card.sass" in p for p in data["problems"]),
                        data["problems"])
        proc = run_py("design-token-migration", "extract_literals", "src", cwd=self.tmp)
        self.assertIn("did not read 1 indented Sass file(s)", output(proc))

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


class AddressesAreNotComments(TempDirTest):
    """N12: the migration tool read `//` as a comment in plain CSS, as the
    audit did (SB-A9), so `url(https://…)` hid the rest of its line from the
    census and the codemod, and a custom property holding an address did too.
    In Sass `//` is still a comment, except inside url()."""

    extract = MigrationPipeline.extract
    MAPPING = VendorScopeAndScale.MAPPING
    CSS = ("@layer components {\n"
           "  .hero { background: url(https://cdn.example.com/hero.svg); margin: 13px; }\n"
           "  .card { --terms: https://example.com/terms; color: #123456; }\n"
           "}\n")
    SCSS = ("@layer components {\n"
            "  .card {\n"
            "    // margin: 7px;\n"
            "    background: url(//cdn.example.com/b.svg); margin: 13px;\n"
            "  }\n"
            "}\n")
    # A Sass url() may hold an expression, whose comments are still comments.
    EXPR = '$asset: "hero.svg";\n.x { background: url($asset /* " */); margin: 13px; }\n'

    def test_literals_after_an_address_are_in_the_census(self):
        self.write("src/components/hero.css", self.CSS)
        self.write("src/components/card.scss", self.SCSS)
        # `\)` inside an unquoted url() is part of the address. (The codemod
        # leaves such a file alone: its parentheses do not balance.)
        self.write("src/components/escaped.scss", ".e { background: url(//cdn.example.com/a\\)//b.svg); margin: 13px; }\n")
        self.write("src/components/expr.scss", self.EXPR)
        _, data = self.extract("src")
        # Each under its own property: the unclosed url( made `background`'s
        # value run on, so its literals were found but filed under it.
        found = {(pathlib.PurePath(l["file"].replace("\\", "/")).name, l["line"], l["prop"], l["normalized"])
                 for l in data["literals"]}
        for want in (("hero.css", 2, "margin", "13px"), ("hero.css", 3, "color", "#123456"),
                     ("card.scss", 4, "margin", "13px"), ("escaped.scss", 1, "margin", "13px"),
                     ("expr.scss", 2, "margin", "13px")):
            with self.subTest(want=want):
                self.assertIn(want, found)
        self.assertNotIn("7px", {n for *_, n in found})

    def test_the_codemod_rewrites_after_an_address(self):
        mapping = self.write("mapping.json", json.dumps(self.MAPPING))
        css = self.write("src/components/hero.css", self.CSS)
        scss = self.write("src/components/card.scss", self.SCSS)
        expr = self.write("src/components/expr.scss", self.EXPR)
        proc = run_py("design-token-migration", "apply_codemod", "-m", mapping, "--apply", "src",
                      cwd=self.tmp)
        self.assertIn('/* " */); margin: var(--gap-related); }', expr.read_text(encoding="utf-8"), output(proc))
        self.assertIn("hero.svg); margin: var(--gap-related); }", css.read_text(encoding="utf-8"), output(proc))
        self.assertIn("b.svg); margin: var(--gap-related);", scss.read_text(encoding="utf-8"), output(proc))
        self.assertIn("// margin: 7px;", scss.read_text(encoding="utf-8"))


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
    with temp_dir("wds-test-") as holder:
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


class LifecycleDocClaims(unittest.TestCase):
    """LC-A17, LC-A23 (CodeRabbit on #54): the lifecycle docs' corrected claims,
    held to what they describe."""

    def test_a_breaking_announcement_names_a_major_and_commits_once(self):
        text = (SKILLS / "design-system-versioning" / "references" / "rollout.md").read_text(
            encoding="utf-8")
        found = re.findall(r"\*\*Design system (\d+)\.(\d+)\.(\d+)\.\*\* One breaking change"
                           r".*?`UPGRADE-([\d.]+)\.md`", text)
        self.assertTrue(found)
        for major, minor, patch, guide in found:
            self.assertEqual((minor, patch, guide), ("0", "0", f"{major}.0.0"))
        procedure = text.split("## 3.", 1)[1].split("## 4.", 1)[0]
        self.assertNotIn("git commit -am", procedure)
        self.assertEqual(procedure.count("git commit"), 1)

    def test_the_deprecated_gate_is_the_lint_rule_not_tsc(self):
        text = (SKILLS / "design-system-versioning" / "references" / "deprecation.md").read_text(
            encoding="utf-8")
        self.assertIn("@typescript-eslint/no-deprecated", text)
        self.assertNotRegex(text, r"surfaced by[^.]*`tsc`")

    def test_the_algorithm_count_matches_its_table(self):
        text = (SKILLS / "design-token-migration" / "SKILL.md").read_text(encoding="utf-8")
        m = re.search(r"(\w+) separate algorithms[^\n]*\n\n(\|.*?)\n\n", text, re.S)
        rows = m.group(2).splitlines()[2:]
        self.assertEqual({"four": 4, "five": 5, "six": 6}[m.group(1).lower()], len(rows))

    def test_the_plan_template_names_each_token_at_its_size(self):
        tokens = (SKILLS / "web-design-studio" / "assets" / "starter" / "styles"
                  / "tokens.css").read_text(encoding="utf-8")
        size = {n: int(px) for n, px in
                re.findall(r"--(space-[\w-]+):\s*[^;]+;\s*/\*\s*(\d+)px", tokens)}
        for name, step in re.findall(r"--((?:pad|gap)-[\w-]+):\s*calc\(var\(--(space-[\w-]+)\)",
                                     tokens):
            size[name] = size[step]
        plan = (SKILLS / "design-token-migration" / "assets" / "MIGRATION_PLAN.md").read_text(
            encoding="utf-8")
        pairs = re.findall(r"(\d+)px --((?:pad|gap|space)-[\w-]+)", plan)
        self.assertTrue(pairs)
        for px, name in pairs:
            self.assertEqual(size.get(name), int(px), name)


class TheCensusMakesItsFolder(TempDirTest):
    """P26: /migrate writes the census where nothing exists yet."""

    def test_the_output_folder_is_created(self):
        self.write("src/card.css", ".card {\n  padding: 13px;\n}\n")
        proc = run_py("design-token-migration", "extract_literals", "src", "--format", "json",
                      "-o", "design-reports/migration/literals.json", cwd=self.tmp)
        self.assertEqual(0, proc.returncode, output(proc))
        literals = json.loads((self.tmp / "design-reports" / "migration" / "literals.json").read_bytes())
        self.assertTrue(literals["literals"])


class TheCensusReadsEveryStyleSource(TempDirTest):
    """LC-B5 (P39): the census missed Sass's module colour functions, the
    <style> blocks and style="" attributes of Vue, Svelte, Astro and HTML
    files, and CSS-in-JS style objects, so a migration sized from it came
    in short, and the codemod never reached the blocks."""

    extract = MigrationPipeline.extract
    cluster = MigrationPipeline.cluster
    MAPPING = VendorScopeAndScale.MAPPING

    def found(self, data, name):
        return [(l["line"], l["context"], l["prop"], l["raw"]) for l in data["literals"]
                if l["file"].replace("\\", "/").endswith(name)]

    def test_sass_module_colour_functions_are_counted(self):
        self.write("src/buttons.scss", "$brand: #e16037;\n"
                   ".a { color: darken($brand, 10%); background: color.adjust($brand, $lightness: -10%); }\n"
                   ".b { color: color.scale($brand, $lightness: 20%); outline-color: color.change($brand, $alpha: 0.5); }\n"
                   ".c { color: adjust-color($brand, $blue: 5); }\n")
        _, data = self.extract("src")
        functions = [raw.split("(")[0] for _, context, _, raw in self.found(data, "buttons.scss")
                     if context == "css-decl"]
        self.assertEqual(functions, ["darken", "color.adjust", "color.scale", "color.change", "adjust-color"])

    def test_style_blocks_of_single_file_components_are_stylesheets(self):
        self.write("src/Card.vue", "<template>\n  <!-- <div style=\"padding: 99px\"></div> -->\n"
                   "  <div class=\"card\"><slot /></div>\n</template>\n"
                   "<script setup>\nconst css = \"<style>.x { margin: 98px; }</style>\";\n</script>\n"
                   "<style scoped lang=\"scss\">\n.card { padding: 13px; } // .card { margin: 97px; }\n</style>\n"
                   "<style lang=\"sass\">\n.card\n  margin: 5px\n</style>\n")
        self.write("src/Badge.svelte", "<span>x</span>\n<style>\n  span { border-radius: 6px; }\n</style>\n")
        self.write("src/Hero.astro", "---\nconst title = 'Hi';\n---\n<h1>{title}</h1>\n"
                   "<style>\n  h1 { gap: 21px; }\n</style>\n")
        _, data = self.extract("src")
        self.assertEqual(self.found(data, "Card.vue"), [(9, "css-decl", "padding", "13px")])
        self.assertEqual(self.found(data, "Badge.svelte"), [(3, "css-decl", "border-radius", "6px")])
        self.assertEqual(self.found(data, "Hero.astro"), [(6, "css-decl", "gap", "21px")])
        self.assertTrue(all(l["component"] for l in data["literals"]), data["literals"])
        self.assertTrue(any('Card.vue (<style lang="sass">)' in p for p in data["problems"]), data["problems"])

    def test_style_attributes_are_inline_styles_and_left_to_hand_work(self):
        self.write("src/page.html", "<p style=\"margin-top: 13px; color: #123456\" class=\"p-[7px]\">x</p>\n"
                   "<p :style=\"{ color: c }\" style:color=\"red\">y</p>\n<style>p { margin: 13px; }</style>\n")
        literals, data = self.extract("src")
        self.assertEqual(self.found(data, "page.html"), [
            (1, "inline-style", "margin-top", "13px"), (1, "inline-style", "color", "#123456"),
            (1, "tailwind-arbitrary", "tw:p", "p-[7px]"), (3, "css-decl", "margin", "13px")])
        mapping, report = self.cluster(literals)
        mapped = sum(r["occurrences"] for r in mapping["rules"] if "13px" in r["match"])
        self.assertEqual(mapped, 1, mapping["rules"])                   # the <style> block's, not the attribute's
        self.assertIn('style=""', report)

    def test_style_objects_are_counted_and_left_to_hand_work(self):
        self.write("src/Box.tsx", "export const B = () => <Box sx={{ p: 2, color: '#334455', "
                   "'&:hover': { bgcolor: '#556677' }, padding: { xs: '8px', md: '24px' } }} />;\n"
                   "export const C = () => <div css={{ marginTop: 12 }} />;\n"
                   "const S = styled.div({ gap: 18 });\nconst other = style({ padding: 99 });\n")
        self.write("src/button.css.ts", "import { style } from '@vanilla-extract/css';\n"
                   "export const button = style({ padding: 10, ':hover': { color: '#778899' } });\n")
        self.write("src/panda.ts", "import { css } from '../styled-system/css';\n"
                   "export const c = css({ p: 4, color: '#101010' });\n")
        literals, data = self.extract("src")
        self.assertEqual(self.found(data, "Box.tsx"), [
            (1, "style-object", "color", "#334455"), (1, "style-object", "background-color", "#556677"),
            (1, "style-object", "padding", "8px"), (1, "style-object", "padding", "24px"),
            (2, "style-object", "margin-top", "12px"), (3, "style-object", "gap", "18px")])
        self.assertEqual(self.found(data, "button.css.ts"), [
            (2, "style-object", "padding", "10px"), (2, "style-object", "color", "#778899")])
        self.assertEqual(self.found(data, "panda.ts"), [(2, "style-object", "color", "#101010")])
        mapping, report = self.cluster(literals)
        self.assertFalse([r for r in mapping["rules"] if "#334455" in r["match"]], mapping["rules"])
        self.assertIn("CSS-in-JS style object", report)

    def test_a_sass_function_seeded_with_a_hex_is_one_decision(self):
        # Codex on #116: the hex inside was claimed first, so the call read as a plain colour.
        self.write("src/seeds.scss", ".a { color: color.adjust(#123456, $lightness: 10%); "
                   "background: darken(#abcdef, 5%); border-color: color.mix(#123456, #fedcba, 50%); }\n")
        _, data = self.extract("src")
        self.assertEqual([(c, raw.split("(")[0]) for _, c, _, raw in self.found(data, "seeds.scss")],
                         [("css-decl", "color.adjust"), ("css-decl", "darken"), ("css-decl", "color.mix")])
        self.assertEqual({"color-function"}, {l["kind"] for l in data["literals"]})

    def test_a_responsive_array_is_read_item_by_item(self):
        # Codex on #116: an array value was skipped, and its object claimed, so nothing counted it.
        self.write("src/Hero.tsx", "export const H = () => <Box sx={{ color: ['#333333', '#444444'], "
                   "padding: ['8px', '16px'], m: [1, 2] }} css={{ gap: [4, { md: '12px' }] }} />;\n")
        _, data = self.extract("src")
        self.assertEqual([(prop, raw) for _, _, prop, raw in self.found(data, "Hero.tsx")], [
            ("color", "#333333"), ("color", "#444444"), ("padding", "8px"), ("padding", "16px"),
            ("gap", "4px"), ("gap", "12px")])

    def test_astro_frontmatter_is_read_once(self):
        # CodeRabbit on #116: a <script> inside the frontmatter's code was a second block.
        self.write("src/Page.astro", "---\nconst snippet = '<script>const c = \"#121212\";</script>';\n---\n"
                   "<p>{snippet}</p>\n")
        _, data = self.extract("src")
        self.assertEqual([raw for _, _, _, raw in self.found(data, "Page.astro")], ["#121212"])

    def test_the_codemod_rewrites_a_style_block_and_leaves_the_attribute(self):
        mapping = self.write("mapping.json", json.dumps(self.MAPPING))
        vue = self.write("src/Card.vue", "<template>\n  <div style=\"margin: 13px\">x</div>\n</template>\n"
                         "<style lang=\"scss\">\n.card { margin: 13px; } // margin: 13px\n</style>\n")
        proc = run_py("design-token-migration", "apply_codemod", "-m", mapping, "--apply", "src",
                      cwd=self.tmp)
        self.assertEqual(vue.read_text(encoding="utf-8"),
                         "<template>\n  <div style=\"margin: 13px\">x</div>\n</template>\n"
                         "<style lang=\"scss\">\n.card { margin: var(--gap-related); } // margin: 13px\n</style>\n",
                         output(proc))


if __name__ == "__main__":
    unittest.main()
