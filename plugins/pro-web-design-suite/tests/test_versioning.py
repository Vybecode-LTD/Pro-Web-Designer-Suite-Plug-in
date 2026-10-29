"""pro-web-design-suite: design-system-versioning's diff_system, classifying what
design-system-docs' system.json records.

Regressions covered (P14):
- LC-A8: a density-scale change, a reduced-motion change and a root-element
  change are "major, auto-detect yes" in change-classification.md, and
  system.json records all three, but diff_system compared none of them: the
  review's v1 to v3 reported RECOMMENDED BUMP PATCH "because nothing changed".
- LC-A9: a new dark-theme override that moves an existing value was minor,
  although it changes rendering in that theme (the file's own §11 Q2); and a
  local class renamed under CSS Modules, which the file calls a patch, was
  reported as part-removed, major, with the gate failing.
- LC-C5: system.json records the `@layer` order statement, so the diff
  compares it from two snapshots instead of saying it cannot.

The fixtures are the review's `fx/ver` versions, cut down: a token file, an
entry stylesheet with the layer order, and one CSS Modules card with its props.
"""
from __future__ import annotations

import json
import pathlib
import re
import subprocess
import sys
import unittest

from wds_support import SKILLS, TempDirTest, env, output, run_py

FIXTURES = pathlib.Path(__file__).resolve().parent / "fixtures"

TOKENS = """\
@layer tokens {
  :root {
    --neutral-0: oklch(100% 0 0);
    --neutral-500: oklch(53.5% 0.009 75);
    --neutral-900: oklch(23% 0.005 75);
    --space-6: 1.5rem;
    --density: 1;
    --dur-base: 220ms;
    --dur-quick: 220ms;
    --bg-canvas: var(--neutral-0);
    --bg-surface: var(--neutral-0);
    --fg-default: var(--neutral-900);
    --fg-muted: var(--neutral-500);
    --pad-card: PAD_CARD;
    --motion-hover: MOTION;
  }
  [data-theme="dark"] {
    --bg-canvas: var(--neutral-900);
    --bg-surface: var(--neutral-900);
    --fg-default: var(--neutral-0);DARK_EXTRA
  }DENSITIES
  @media (prefers-reduced-motion: reduce) {
    :root { --dur-base: REDUCED; }
  }
}
"""

CARD_CSS = """\
@layer components {
  .card {
    --card-pad: var(--pad-card);
    --card-bg: var(--bg-surface);
    padding: var(--card-pad);
    background: var(--card-bg);
  }
  .TITLE { font-weight: WEIGHT; color: var(--fg-default); }
  .card > .TITLE { margin-block-end: MARGIN; }
  .card:hover { --card-bg: var(--bg-canvas); }
}
"""

CARD_TSX = """\
IMPORTSexport interface CardProps {
  /** Heading text */
  title?: string;
}
function Label() {
  return <span>label</span>;
}
/** A surface. */
export function Card({ title }: CardProps) {
  return RENDER;
}
"""

V1 = {"pad_card": "calc(var(--space-6) * var(--density))", "dark_extra": "",
      "densities": {"compact": "0.875"}, "reduced": "1ms", "element": "div",
      "title": "card__title", "weight": "600", "margin": "0", "exports": False, "module": True, "motion": "var(--dur-base)",
      "layers": "reset, tokens, base, components, utilities"}


class DiffSystemClassifiesWhatSystemJsonRecords(TempDirTest):

    def snapshot(self, name: str, **changes) -> str:
        """One version of the fixture system, extracted into its system.json."""
        v = dict(V1, **changes)
        root = self.tmp / name
        dens = "".join(f'\n  [data-density="{label}"] {{ --density: {value}; }}'
                       for label, value in v["densities"].items())
        tokens = (TOKENS.replace("PAD_CARD", v["pad_card"])
                  .replace("DARK_EXTRA", v["dark_extra"])
                  .replace("DENSITIES", dens).replace("REDUCED", v["reduced"])
                  .replace("MOTION", v["motion"]))
        self.write(f"{name}/styles/tokens.css", tokens)
        if v["layers"] is not None:
            self.write(f"{name}/styles/index.css",
                       f"@layer {v['layers']};\n@import url(\"tokens.css\");\n")
        css_name = "Card.module.css" if v["module"] else "card.css"
        self.write(f"{name}/src/components/{css_name}",
                   CARD_CSS.replace("TITLE", v["title"]).replace("WEIGHT", v["weight"])
                   .replace("MARGIN", v["margin"]))
        el = v["element"]
        render = f'<{el} className="card">{{title}}</{el}>' if el else "<>{title}</>"
        self.write(f"{name}/src/components/Card.tsx", CARD_TSX.replace("RENDER", render).replace(
            "IMPORTS", 'import styles from "./Card.module.css";\nexport { styles };\n'
            if v["exports"] else ""))
        out = root / "system.json"
        proc = run_py("design-system-docs", "extract_system", "styles", "src",
                      "--root", str(root), "--out", str(out), cwd=root)
        self.assertEqual(proc.returncode, 0, output(proc))
        return str(out)

    def diff(self, old: str, new: str, *extra: str) -> dict:
        proc = run_py("design-system-versioning", "diff_system", old, new,
                      "--format", "json", *extra, cwd=self.tmp)
        self.assertNotIn("Traceback", output(proc), output(proc))
        self.assertIn(proc.returncode, (0, 1), output(proc))
        return json.loads(proc.stdout)

    def kinds(self, res: dict) -> dict:
        return {c["kind"]: c for c in res["changes"]}

    # -- LC-A8 ------------------------------------------------------------

    def test_a_density_scale_change_is_major(self):
        res = self.diff(self.snapshot("v1"),
                        self.snapshot("v2", densities={"compact": "0.8"}))
        change = self.kinds(res).get("density-changed")
        self.assertIsNotNone(change, res["changes"])
        self.assertEqual(change["severity"], "major")
        self.assertEqual(change["subject"], "--density")
        self.assertIn("compact", change["detail"])
        self.assertIn("--pad-card 21px -> 19.2px", change["detail"])
        self.assertEqual(res["bump"]["level"], "major", res["bump"])

    def test_a_reduced_motion_change_is_major(self):
        res = self.diff(self.snapshot("v1"), self.snapshot("v2", reduced="0.01ms"))
        change = self.kinds(res).get("condition-changed")
        self.assertIsNotNone(change, res["changes"])
        self.assertEqual(change["severity"], "major")
        self.assertEqual(change["subject"], "--dur-base")
        self.assertIn("reduced-motion", change["detail"])
        self.assertEqual((change["before"], change["after"]), ("1ms", "0.01ms"))
        self.assertEqual(res["bump"]["level"], "major", res["bump"])

    def test_a_root_element_change_is_major(self):
        res = self.diff(self.snapshot("v1"), self.snapshot("v2", element="section"))
        change = self.kinds(res).get("element-changed")
        self.assertIsNotNone(change, res["changes"])
        self.assertEqual(change["severity"], "major")
        self.assertEqual(change["component"], "card")
        self.assertEqual((change["before"], change["after"]), ("div", "section"))

    def test_a_root_that_becomes_a_fragment_is_reported(self):
        # Codex on #48: an undetectable root (a fragment) hid the change.
        res = self.diff(self.snapshot("v1"), self.snapshot("v2", element=""))
        change = self.kinds(res).get("element-changed")
        self.assertIsNotNone(change, res["changes"])
        self.assertEqual(change["severity"], "major")
        self.assertEqual(change["before"], "div")

    def test_a_re_point_equal_by_default_but_not_under_reduced_motion_is_major(self):
        # Codex on #48: 220ms either way, but 1ms against 220ms for reduced motion.
        res = self.diff(self.snapshot("v1"), self.snapshot("v2", motion="var(--dur-quick)"))
        change = self.kinds(res).get("tier2-repointed")
        self.assertIsNotNone(change, res["changes"])
        self.assertIn("reduced-motion", change["detail"])
        self.assertEqual(res["bump"]["level"], "major", res["bump"])

    def test_the_reviews_v1_to_v3_is_not_a_patch(self):
        res = self.diff(self.snapshot("v1"),
                        self.snapshot("v3", densities={"compact": "0.8"},
                                      reduced="0.01ms", element="section"))
        self.assertEqual(res["bump"]["level"], "major", res["bump"])
        self.assertNotEqual(res["bump"]["reason"], "nothing changed")
        self.assertLessEqual({"density-changed", "condition-changed", "element-changed"},
                             set(self.kinds(res)), res["changes"])

    def test_a_re_point_equal_in_light_but_not_at_a_density_is_major(self):
        # 24px either way at the default density; 21px against 24px at compact.
        res = self.diff(self.snapshot("v1"),
                        self.snapshot("v2", pad_card="var(--space-6)"))
        change = self.kinds(res).get("tier2-repointed")
        self.assertIsNotNone(change, res["changes"])
        self.assertNotIn("tier2-repointed-equal", self.kinds(res))
        self.assertEqual(res["bump"]["level"], "major", res["bump"])

    def test_the_vendored_token_parser_sees_density_and_conditions_too(self):
        self.snapshot("v1")
        self.snapshot("v2", densities={"compact": "0.8"}, reduced="0.01ms")
        res = self.diff(str(self.tmp / "v1" / "styles" / "tokens.css"),
                        str(self.tmp / "v2" / "styles" / "tokens.css"), "--no-upstream")
        self.assertEqual(res["new"]["source"], "tokens.css")
        kinds = self.kinds(res)
        self.assertEqual(kinds["density-changed"]["severity"], "major", res["changes"])
        self.assertIn("--pad-card 21px -> 19.2px", kinds["density-changed"]["detail"])
        self.assertEqual(kinds["condition-changed"]["severity"], "major")
        self.assertEqual(res["bump"]["level"], "major", res["bump"])

    def test_a_density_added_is_minor_and_one_removed_is_major(self):
        both = {"compact": "0.875", "spacious": "1.25"}
        res = self.diff(self.snapshot("v1"), self.snapshot("v2", densities=both))
        self.assertEqual(self.kinds(res)["density-added"]["severity"], "minor")
        self.assertNotIn("density-changed", self.kinds(res), res["changes"])
        self.assertEqual(res["bump"]["level"], "minor", res["bump"])

        res = self.diff(self.snapshot("v3", densities=both), self.snapshot("v4"))
        self.assertEqual(self.kinds(res)["density-removed"]["severity"], "major")
        self.assertNotIn("density-changed", self.kinds(res), res["changes"])

    # -- LC-A9 ------------------------------------------------------------

    def test_a_dark_override_that_moves_a_value_is_major(self):
        dark = "\n    --fg-muted: oklch(40% 0.005 75);"
        res = self.diff(self.snapshot("v1"), self.snapshot("v4", dark_extra=dark))
        change = self.kinds(res).get("theme-override-added")
        self.assertIsNotNone(change, res["changes"])
        self.assertEqual(change["severity"], "major")
        self.assertEqual(change["theme"], "dark")
        self.assertEqual(res["bump"]["level"], "major", res["bump"])
        crossed = [r for r in res["contrast"]
                   if r["fg"] == "--fg-muted" and r["theme"] == "dark" and r["crossings"]]
        self.assertTrue(crossed, res["contrast"])

    def test_a_dark_override_that_resolves_identically_is_a_patch(self):
        # Control: the root value already resolves this way in dark.
        dark = "\n    --fg-muted: var(--neutral-500);"
        res = self.diff(self.snapshot("v1"), self.snapshot("v4", dark_extra=dark))
        self.assertEqual(self.kinds(res)["theme-override-added"]["severity"], "patch")
        self.assertEqual(res["bump"]["level"], "patch", res["bump"])

    def test_a_local_class_renamed_under_css_modules_is_a_patch(self):
        old = self.snapshot("v1")
        new = self.snapshot("v2", title="card__heading")
        res = self.diff(old, new)
        kinds = self.kinds(res)
        self.assertNotIn("part-removed", kinds, res["changes"])
        change = kinds.get("part-renamed-local")
        self.assertIsNotNone(change, res["changes"])
        self.assertEqual((change["severity"], change["before"], change["after"]),
                         ("patch", "card__title", "card__heading"))
        self.assertEqual(res["bump"]["level"], "patch", res["bump"])

        ledger = self.write("deprecations.json", json.dumps(
            {"schema": "design-system-versioning/deprecations@1", "deprecations": []}))
        proc = run_py("design-system-versioning", "diff_system", old, new,
                      "--deprecations", str(ledger), cwd=self.tmp)
        self.assertEqual(proc.returncode, 0, output(proc))

    def test_a_local_rename_that_also_changes_a_value_is_not_a_patch(self):
        # Codex on #48: the same properties are not the same rule.
        res = self.diff(self.snapshot("v1"),
                        self.snapshot("v2", title="card__heading", weight="700"))
        kinds = self.kinds(res)
        self.assertNotIn("part-renamed-local", kinds, res["changes"])
        self.assertEqual(kinds["part-removed"]["severity"], "major")

    def test_a_local_rename_restyled_in_a_second_rule_is_not_a_patch(self):
        # CodeRabbit on #48: every rule that styles the part, not only the first.
        res = self.diff(self.snapshot("v1"),
                        self.snapshot("v2", title="card__heading", margin="4px"))
        self.assertNotIn("part-renamed-local", self.kinds(res), res["changes"])

    def test_a_rename_in_a_module_whose_styles_are_exported_is_major(self):
        # CodeRabbit on #48: an exported styles object makes the key the API.
        res = self.diff(self.snapshot("v1", exports=True),
                        self.snapshot("v2", exports=True, title="card__heading"))
        kinds = self.kinds(res)
        self.assertNotIn("part-renamed-local", kinds, res["changes"])
        self.assertEqual(kinds["part-removed"]["severity"], "major")

    def test_the_same_rename_in_global_css_stays_major(self):
        # Control: a global class is a name any consumer can write.
        res = self.diff(self.snapshot("v1", module=False),
                        self.snapshot("v2", module=False, title="card__heading"))
        kinds = self.kinds(res)
        self.assertEqual(kinds["part-removed"]["severity"], "major", res["changes"])
        self.assertNotIn("part-renamed-local", kinds)

    # -- LC-C5: the layer order -------------------------------------------

    def test_system_json_records_the_layer_order(self):
        data = json.loads(pathlib.Path(self.snapshot("v1")).read_bytes())
        self.assertEqual(data["layers"], ["reset, tokens, base, components, utilities"])

    def test_a_layer_reorder_between_two_snapshots_is_major(self):
        res = self.diff(self.snapshot("v1"),
                        self.snapshot("v2", layers="reset, base, tokens, components, utilities"))
        change = self.kinds(res).get("layer-order-changed")
        self.assertIsNotNone(change, res["changes"])
        self.assertEqual(change["severity"], "major")
        self.assertFalse([n for n in res["notes"] if "layer order was not compared" in n],
                         res["notes"])

    def test_an_older_snapshot_without_the_layer_order_says_to_re_extract(self):
        old = self.snapshot("v1")
        data = json.loads(pathlib.Path(old).read_bytes())
        del data["layers"]
        legacy = self.write("legacy/system.json", json.dumps(data))
        res = self.diff(str(legacy), self.snapshot("v2"))
        notes = [n for n in res["notes"] if "layer order was not compared" in n]
        self.assertTrue(notes, res["notes"])
        self.assertIn("extract_system", notes[0])


CLIENT = [".meta { color: var(--fg-subtle); }",
          ".meta-strong { color: var(--fg-subtle); font-weight: 600; }",
          ".rule { border-color: var(--fg-subtle); }",
          ".icon { fill: var(--fg-subtle); stroke: var(--fg-subtle); }",
          ".divider { border-bottom: 1px solid var(--fg-subtle); }",
          ".card { --card-meta-fg: var(--fg-subtle); }"]


def multi_line(rule: str) -> str:
    sel, _, body = rule.partition("{")
    decls = [d.strip() for d in body.rstrip("} ").split(";") if d.strip()]
    return sel.rstrip() + " {\n" + "".join(f"  {d};\n" for d in decls) + "}"


class DeprecateKeepsRemovalsInAMajor(TempDirTest):
    """LC-A23: deprecation.md puts a removal in X+1.0.0, and deprecate.py took
    `--removal 2.2.0` for `--since 2.1.0`."""

    def add(self, removal, *extra):
        return run_py("design-system-versioning", "deprecate", "--ledger", self.tmp / "dep.json",
                      "add", "--name=--fg-subtle", "--kind", "token", "--since", "2.1.0",
                      "--removal", removal, "--replacement=--fg-faint", *extra, cwd=self.tmp)

    def test_a_removal_outside_a_major_is_refused(self):
        for removal in ("2.2.0", "2.1.1", "3.1.0"):
            with self.subTest(removal=removal):
                proc = self.add(removal)
                self.assertEqual(proc.returncode, 2, output(proc))
                self.assertIn("3.0.0", output(proc))

    def test_a_removal_in_a_later_major_is_taken(self):
        for removal in ("3.0.0", "4.0.0"):
            with self.subTest(removal=removal):
                self.assertEqual(self.add(removal).returncode, 0)
        self.assertEqual(self.add("2.2.0", "--force", "--notes", "deliberate").returncode, 0)


class TheMarkerKeepsTheFilesLineEndings(TempDirTest):
    """H1 (the 2026-10-14 audit): `deprecate add --source` read the token file
    with universal newlines and wrote it in the platform's, so one marker line
    became a whole-file diff: LF came back CRLF on Windows, CRLF LF elsewhere."""

    LINES = (":root {", "  --fg-faint: #6b6b6b;", "  --fg-subtle: #767676;", "}", "")

    def add(self, ledger, tokens):
        proc = run_py("design-system-versioning", "deprecate", "--ledger", ledger, "add",
                      "--name=--fg-subtle", "--kind", "token", "--since", "2.1.0", "--removal", "3.0.0",
                      "--replacement=--fg-faint", "--source", tokens, cwd=self.tmp)
        self.assertEqual(proc.returncode, 0, output(proc))

    def test_one_line_is_added_in_the_files_own_ending(self):
        for n, ending in enumerate(("\n", "\r\n")):
            with self.subTest(ending=repr(ending)):
                before = ending.join(self.LINES).encode("utf-8")
                tokens = self.write(f"tokens{n}.css", before)
                self.add(self.tmp / f"dep{n}.json", tokens)
                after = tokens.read_bytes().splitlines(keepends=True)
                added = [line for line in after if b"@deprecated" in line]
                self.assertEqual(len(added), 1, after)
                self.assertTrue(added[0].endswith(ending.encode()), added)
                self.assertEqual([line for line in after if line not in added],
                                 before.splitlines(keepends=True))
                self.add(self.tmp / f"dep{n}.json", tokens)          # a second run is already current
                self.assertEqual(tokens.read_bytes().splitlines(keepends=True), after)

    def test_the_ledger_keeps_its_own_ending(self):
        # The same bug in the ledger deprecate rewrites whole.
        tokens = self.write("tokens.css", "\n".join(self.LINES))
        for n, ending in enumerate(("\n", "\r\n")):
            with self.subTest(ending=repr(ending)):
                ledger = self.write(f"dep{n}.json", ending.join(['{', '  "schema": "design-system-versioning/deprecations@1",',
                                                                '  "deprecations": []', '}', '']).encode())
                self.add(ledger, tokens)
                data = ledger.read_bytes()
                lines = data.split(b"\n")[:-1]
                self.assertGreater(len(lines), 4, data)
                self.assertEqual({line.endswith(b"\r") for line in lines}, {ending == "\r\n"}, data)
                self.assertIn(b"--fg-subtle", data)


class DeprecateRewritesAndCountsAColourRename(TempDirTest):
    """LC-A14, the review's `fx/dep/client`: a colour rename beside a
    font-weight, and the scan's labels on one-line rules."""

    def setUp(self):
        super().setUp()
        self.ledger = self.tmp / "deprecations.json"
        proc = run_py("design-system-versioning", "deprecate", "--ledger", self.ledger, "add",
                      "--name=--fg-subtle", "--kind", "token", "--since", "1.5.0",
                      "--removal", "2.0.0", "--replacement=--fg-faint", cwd=self.tmp)
        self.assertEqual(proc.returncode, 0, output(proc))
        proc = run_py("design-system-versioning", "deprecate", "--ledger", self.ledger,
                      "mapping", "-o", self.tmp / "mapping.json", cwd=self.tmp)
        self.assertEqual(proc.returncode, 0, output(proc))

    def codemod(self, folder: str) -> str:
        proc = run_py("design-token-migration", "apply_codemod", "-m", self.tmp / "mapping.json",
                      self.tmp / folder, cwd=self.tmp)
        self.assertIn(proc.returncode, (0, 1), output(proc))
        return proc.stdout.decode("utf-8")

    def scan(self, folder: str) -> dict:
        proc = run_py("design-system-versioning", "deprecate", "--ledger", self.ledger, "scan",
                      self.tmp / folder, "--format", "json", cwd=self.tmp)
        self.assertIn(proc.returncode, (0, 1), output(proc))
        hits = [h for per in json.loads(proc.stdout)["results"]["--fg-subtle"].values()
                for h in per]
        return {v: sum(1 for h in hits if h["verdict"] == v) for v in ("codemod", "manual")}

    def test_the_scan_reads_important_and_quoted_text_as_the_codemod_does(self):
        # CodeRabbit on #50: the codemod rewrites `!important` declarations, and a
        # token named inside a CSS string is text, not a use.
        self.write("quoted/src/app.css",
                   ".a { color: var(--fg-subtle) !important; }\n"
                   '.b::after { content: "label; color: var(--fg-subtle);"; }\n'
                   '.c::after { content: "label\\"; color: var(--fg-subtle);"; }\n')
        self.assertEqual(self.scan("quoted"), {"codemod": 1, "manual": 0})

    def test_a_colour_rename_beside_a_font_weight_is_rewritten(self):
        self.write("client/src/app.css", "\n".join(CLIENT) + "\n")
        out = self.codemod("client")
        self.assertIn("+.meta-strong { color: var(--fg-faint); font-weight: 600; }", out)
        self.assertNotIn("would reset", out)

    def test_a_rename_keeps_its_important(self):
        # Codex on #50: the rewrite replaced through `!important` and dropped it.
        self.write("prio/src/app.css",
                   ".x { color: var(--fg-subtle) !important; font-weight: 600; }\n")
        self.assertIn("+.x { color: var(--fg-faint) !important; font-weight: 600; }",
                      self.codemod("prio"))

    def test_the_scan_labels_a_one_line_rule_as_the_codemod_treats_it(self):
        self.write("one/src/app.css", "\n".join(CLIENT) + "\n")
        self.write("many/src/app.css", "\n".join(multi_line(r) for r in CLIENT) + "\n")
        one, many = self.scan("one"), self.scan("many")
        self.assertEqual(one, many)
        rewritten = re.search(r"(\d+) replacement\(s\)", self.codemod("one"))
        self.assertEqual(one["codemod"], int(rewritten.group(1)), one)
        self.assertEqual(one["manual"], 2, one)     # the shorthand and the socket default


def collapsed(text: str) -> str:
    return " ".join(text.split())


class TheWorkedRelease(TempDirTest):
    """LC-C12: versioning SKILL.md's worked release is the five edits in
    tests/fixtures/worked-release.json, applied to the starter's tokens.css. Its
    quoted report, and every before → after ratio its notes quote, must be what
    diff_system prints for them today."""

    def test_the_skill_quotes_what_the_diff_prints(self):
        fx = json.loads((FIXTURES / "worked-release.json").read_text(encoding="utf-8"))
        old = (SKILLS / "web-design-studio" / "assets" / "starter" / "styles" / "tokens.css").read_text(encoding="utf-8")
        new = old
        for edit in fx["edits"]:
            with self.subTest(edit=edit):
                count = new.count(edit["old"])
                self.assertTrue(count == 1 or (edit.get("all") and count), edit)
                new = new.replace(edit["old"], edit["new"])
        a, b = self.write("a/tokens.css", old), self.write("b/tokens.css", new)
        proc = run_py("design-system-versioning", "diff_system", a, b,
                      "--from-version", fx["from_version"], cwd=self.tmp)
        report = collapsed(proc.stdout.decode("utf-8"))
        self.assertIn("RECOMMENDED BUMP", report, output(proc))
        # A re-point that moved by default lists no theme, density or condition.
        self.assertIn("detail var(--accent-600) -> var(--accent-500) consumer", report)

        skill = (SKILLS / "design-system-versioning" / "SKILL.md").read_text(encoding="utf-8")
        section = skill.split("## A worked release", 1)[1].split("\n---", 1)[0]
        block = section.split("```", 2)[1]
        for line in filter(str.strip, block.splitlines()):
            with self.subTest(line=line.strip()):
                self.assertIn(collapsed(line), report)
        pairs = re.findall(r"(\d\.\d\d)(?::1)? → (\d\.\d\d)", section.split("```", 2)[2])
        self.assertTrue(pairs)
        for before, after in pairs:
            with self.subTest(ratio=f"{before} → {after}"):
                self.assertIn(f"{before}:1 {after}:1", report)


class TheAuditsVersioningMediums(TempDirTest):
    """P54 parts 4 and 5, the audit of 2026-10-14's §3.4: V2 to V6, V9 and
    V10, and what the 2026-10-15 session found: the 8-digit hex and
    `extract_system --tokens` on a JSON file."""

    def deprecate(self, *args):
        return run_py("design-system-versioning", "deprecate", "--ledger", self.tmp / "proj" / "deprecations.json",
                      *args, cwd=self.tmp)

    def test_the_kinds_table_is_the_codes(self):
        """V15 (audit, 2026-10-14): change-classification.md listed
        `component-renamed`, which diff_system never emits, and gave a theme
        override's change or removal as major where the code gives patch
        when it resolves as before."""
        code = (SKILLS / "design-system-versioning" / "scripts" / "diff_system.py").read_text(encoding="utf-8")
        kinds = set(re.findall(r'^\s*K\("([\w-]+)"', code, re.M))
        doc = (SKILLS / "design-system-versioning" / "references" / "change-classification.md").read_text(
            encoding="utf-8")
        rows = {}
        for line in doc.splitlines():
            if re.match(r"^\| `[\w-]+`", line):
                cells = line.split("|")
                rows.update((kind, cells[2]) for kind in re.findall(r"`([\w-]+)`", cells[1]))
        self.assertGreater(len(kinds), 40)
        self.assertEqual(kinds, set(rows))
        self.assertNotIn("component-renamed", kinds)
        for kind in ("theme-override-changed", "theme-override-removed"):
            with self.subTest(kind=kind):
                self.assertIn("patch if it resolves as before", rows[kind])

    def test_another_docs_schema_version_is_refused(self):
        """V14 (audit, 2026-10-14): diff_system read any design-system-docs
        schema (`DOCS_SCHEMA` was unused) while build_docs takes one."""
        good = self.write("good.json", json.dumps({"schema": "design-system-docs/system/1", "tokens": []}))
        for schema in ("design-system-docs/system/2", "design-system-docs/other/1"):
            with self.subTest(schema=schema):
                other = self.write("other.json", json.dumps({"schema": schema, "tokens": []}))
                proc = run_py("design-system-versioning", "diff_system", other, good, cwd=self.tmp)
                self.assertEqual(2, proc.returncode, output(proc))
                self.assertIn("expected 'design-system-docs/system/1'", output(proc))
        proc = run_py("design-system-versioning", "diff_system", good, good, cwd=self.tmp)
        self.assertIn(proc.returncode, (0, 1), output(proc))                    # its own is read

    def test_the_scan_skips_the_suites_own_records(self):
        """V4: the mapping's rules hold `var(--fg-subtle)`, so the scan read it
        as a use, "NOT SAFE to remove", forever; the ledger and a scan report too."""
        self.write("proj/app.css", ".a { color: var(--fg-subtle); }\n")
        self.assertEqual(0, self.deprecate("add", "--name=--fg-subtle", "--kind", "token", "--since", "1.5.0",
                                           "--removal", "2.0.0", "--replacement=--fg-faint").returncode)
        self.assertEqual(0, self.deprecate("mapping", "-o", self.tmp / "proj" / "mapping.json").returncode)
        self.write("proj/notes.json", json.dumps({"todo": "var(--fg-subtle) in the old header"}))   # not ours: read
        self.write("proj/contract.json", json.dumps({"schema": "web-design-suite/contract/1",       # Codex on #147
                                                     "roles": {"--fg-muted": "var(--fg-subtle)"}}))
        proc = self.deprecate("scan", self.tmp / "proj", "--format", "json")
        hits = [h for per in json.loads(proc.stdout)["results"]["--fg-subtle"].values() for h in per]
        self.assertEqual(["app.css", "notes.json"], sorted(pathlib.Path(h["file"]).name for h in hits))

    def test_a_replacement_must_be_live_and_declared(self):
        """V5: `--replacement` was never looked up, so the mapping could rewrite
        one deprecated name onto another, or onto a name no source declares."""
        # The replacement shares a line with its selector (Codex on #147).
        self.write("proj/tokens.css", ":root { --fg-faint: #777777;\n  --fg-subtle: #666666;\n"
                                      "  /* --fg-gone: #888888; retired */\n}\n")     # a comment declares nothing
        tokens = str(self.tmp / "proj" / "tokens.css")
        add = ("add", "--kind", "token", "--since", "1.5.0", "--removal", "2.0.0")
        self.assertEqual(0, self.deprecate(*add, "--name=--fg-subtle", "--replacement=--fg-faint").returncode)
        for argv, said in ((["--name=--fg-muted", "--replacement=--fg-subtle"], "is itself deprecated"),
                           (["--name=--fg-muted", "--replacement=--fg-gone", "--source", tokens],
                            "declared in none of --source"),
                           (["--name=--fg-muted", "--replacement=--fg-muted"], "is the token being deprecated")):
            with self.subTest(argv=argv):
                proc = self.deprecate(*add, *argv)
                self.assertEqual(2, proc.returncode, output(proc))
                self.assertIn(said, output(proc))
        self.assertEqual(0, self.deprecate(*add, "--name=--fg-muted", "--replacement=--fg-subtle",
                                           "--force").returncode)
        self.assertEqual(0, self.deprecate(*add, "--name=--fg-strong", "--replacement=--fg-faint",
                                           "--source", tokens, "--dry-run").returncode)

    def test_a_note_cannot_end_the_inlined_search_index(self):
        """V6: build_docs inlines the search index into a <script>, and a
        `</script>` in a token's note ended it."""
        self.write("tokens.css", ":root {\n  --fg-default: #111111;   /* body text </script><b>x</b> */\n"
                                 "  --bg-canvas: #ffffff;\n}\n")
        run_py("design-system-docs", "extract_system", "tokens.css", "--out", "system.json", cwd=self.tmp)
        self.assertIn("</script><b>", (self.tmp / "system.json").read_text(encoding="utf-8"))
        proc = run_py("design-system-docs", "build_docs", "system.json", "--out", "site", cwd=self.tmp)
        self.assertEqual(0, proc.returncode, output(proc))
        pages = sorted((self.tmp / "site").glob("*.html"))
        self.assertTrue(pages)
        for page in pages:
            with self.subTest(page=page.name):
                self.assertNotIn("</script><b>", page.read_text(encoding="utf-8"))

    def test_a_folder_that_holds_a_contract_is_a_snapshot(self):
        """V9: the docs say "a contract.json, or a directory containing one";
        a folder was searched for system.json and tokens.css only (exit 2)."""
        self.write("tokens.css", ":root {\n  --fg-default: #111111;\n  --bg-canvas: #ffffff;\n}\n")
        for v in ("v1", "v2"):
            run_py("design-system-docs", "extract_system", "tokens.css", "--contract", f"{v}/contract.json",
                   cwd=self.tmp)
        proc = run_py("design-system-versioning", "diff_system", "v1", "v2", "--no-upstream", "--format", "json",
                      cwd=self.tmp)
        self.assertEqual(0, proc.returncode, output(proc))

    def test_an_eight_digit_hex_is_translucent(self):
        """Found 2026-10-15: `#2563eb80` was read as solid, so its contrast was
        measured; `oklch(… / 0.5)` was already a translucent note."""
        old = ":root {\n  --brand-500: #2563eb80;\n  --fg-default: var(--brand-500);\n  --bg-canvas: #ffffff;\n}\n"
        self.write("old.css", old)
        self.write("new.css", old.replace("#2563eb80", "#2563eb99"))
        for upstream in ((), ("--no-upstream",)):          # extract_system reads it by default (Codex on #147)
            with self.subTest(upstream=upstream):
                proc = run_py("design-system-versioning", "diff_system", "old.css", "new.css", *upstream,
                              "--format", "json", cwd=self.tmp)
                notes = json.loads(proc.stdout)["notes"]
                self.assertTrue(any("--fg-default on --bg-canvas [light]: translucent" in n for n in notes), notes)

    EXT = "io.github.vybecode-ltd.web-design-suite"
    REM = {"$type": "dimension", "$value": {"value": 1, "unit": "rem"}}

    def dtcg(self, rel, tokens, record=None, marks=None):
        """A DTCG file that writes `tokens` and records `record` as left out."""
        doc = dict(tokens)
        own = {"notWritten": record or {}}
        if marks:
            own["deprecated"] = marks
        doc["$extensions"] = {self.EXT: own}
        self.write(rel, json.dumps(doc))

    def test_a_later_files_record_wins(self):
        """V2: with several DTCG files, a later file's record of a token lost to
        an earlier file's written value, a false MAJOR `tier1-value-changed`.
        Read in order, the last file wins either way."""
        hero = "clamp(2rem, 1rem + 4vw, 4rem)"
        self.write("old.css", f":root {{\n  --space-4: 1rem;\n  --size-hero: {hero};\n}}\n")
        self.dtcg("a.tokens.json", {"space": {"4": self.REM},
                                    "size": {"hero": {"$type": "dimension", "$value": {"value": 2, "unit": "rem"}}}})
        self.dtcg("b.tokens.json", {"space": {"4": self.REM}}, {"--size-hero": hero})
        for order, changed in ((["a.tokens.json", "b.tokens.json"], []),
                               (["b.tokens.json", "a.tokens.json"], ["--size-hero"])):     # the control
            with self.subTest(order=order):
                self.write(".design-suite.json", json.dumps({"schema": 1, "tokens": order}))
                proc = run_py("design-system-versioning", "diff_system", "old.css", "--format", "json",
                              cwd=self.tmp)
                self.assertIn(proc.returncode, (0, 1), output(proc))
                self.assertEqual(changed, sorted({c["subject"] for c in json.loads(proc.stdout)["changes"]}))

    def test_import_reads_the_records_marks(self):
        """V3: `deprecate.py import` read only the written tokens' marks, so a
        deprecated token the file could not hold never reached the ledger,
        though diff_system honoured its mark. A later file that records it
        again without the mark takes it off, as for a written token."""
        hero = "clamp(2rem, 1rem + 4vw, 4rem)"
        self.dtcg("proj/v1.tokens.json", {"space": {"4": self.REM}}, {"--hero": hero},
                  {"--hero": "Use {space.4} instead"})
        self.dtcg("proj/v2.tokens.json", {"space": {"4": self.REM}}, {"--hero": hero})
        window = ("--since", "1.5.0", "--removal", "2.0.0")
        for files, want in ((["v1.tokens.json"], {"--hero": "--space-4"}),
                            (["v1.tokens.json", "v2.tokens.json"], {})):                    # the control
            with self.subTest(files=files):
                ledger = self.tmp / "proj" / "deprecations.json"
                if ledger.exists():
                    ledger.unlink()
                proc = run_py("design-system-versioning", "deprecate", "--ledger", ledger, "import",
                              *files, *window, cwd=self.tmp / "proj")
                self.assertEqual(0, proc.returncode, output(proc))
                got = json.loads(ledger.read_bytes())["deprecations"] if ledger.exists() else []
                self.assertEqual(want, {e["name"]: e["replacement"] for e in got})

    def test_extract_system_reads_a_json_token_file(self):
        """Found 2026-10-15: `extract_system --tokens tokens.json` read the JSON
        as CSS, so a DTCG file gave no token and exit 0, and a config that
        listed one was skipped. Read through read_tokens, as the gates do, with
        the file's record of what it left out."""
        hero = "clamp(2rem, 1rem + 4vw, 4rem)"
        self.dtcg("tokens.json", {"space": {"4": self.REM},
                                  "fg": {"default": {"$type": "color", "$value": "{space.4}"}}},
                  {"--size-hero": hero})
        self.write("contract.json", json.dumps({"schema": "web-design-suite/contract/1",
                                                "roles": {"--fg-muted": "var(--space-4)"}}))
        self.write(".git/HEAD", "x\n")
        cases = (("--tokens", "tokens.json"), ("--tokens", "contract.json"), ())
        wants = ({"--space-4": "1rem", "--fg-default": "var(--space-4)", "--size-hero": hero},
                 {"--fg-muted": "var(--space-4)"},
                 {"--space-4": "1rem", "--fg-default": "var(--space-4)", "--size-hero": hero})
        self.write(".design-suite.json", json.dumps({"schema": 1, "tokens": ["tokens.json"]}))
        for args, want in zip(cases, wants):
            with self.subTest(args=args):
                proc = run_py("design-system-docs", "extract_system", *args, "--out", "system.json", cwd=self.tmp)
                self.assertEqual(0, proc.returncode, output(proc))
                got = json.loads((self.tmp / "system.json").read_bytes())["tokens"]
                self.assertEqual(want, {t["name"]: t["raw"] for t in got})
                self.assertEqual({0}, {t["line"] for t in got})

    def test_a_later_source_that_writes_a_token_ends_its_record(self):
        """Codex and CodeRabbit on #149: in a resolver, an earlier source's
        record of a token outlived a later source that writes it, so the
        record's value replaced the resolved one and its mark came back."""
        hero = "clamp(2rem, 1rem + 4vw, 4rem)"
        self.dtcg("pub/a.tokens.json", {"space": {"4": self.REM}}, {"--size-hero": hero},
                  {"--size-hero": "Use {space.4} instead"})
        self.dtcg("pub/b.tokens.json", {"size": {"hero": {"$type": "dimension", "$value": {"value": 2, "unit": "rem"}}}})
        self.write("pub/tokens.resolver.json", json.dumps({"version": "2025.10", "resolutionOrder": [
            {"type": "set", "name": "base", "sources": [{"$ref": "a.tokens.json"}, {"$ref": "b.tokens.json"}]}]}))
        resolver = str(self.tmp / "pub" / "tokens.resolver.json")
        proc = run_py("design-system-docs", "extract_system", "--tokens", resolver, "--out", "system.json", cwd=self.tmp)
        self.assertEqual(0, proc.returncode, output(proc))
        got = {t["name"]: t["raw"] for t in json.loads((self.tmp / "system.json").read_bytes())["tokens"]}
        self.assertEqual("2rem", got["--size-hero"])
        self.write("old.css", ":root {\n  --space-4: 1rem;\n  --size-hero: 2rem;\n}\n")
        proc = run_py("design-system-versioning", "diff_system", "old.css", resolver, "--format", "json", cwd=self.tmp)
        self.assertEqual([], json.loads(proc.stdout)["changes"], output(proc))
        proc = run_py("design-system-versioning", "deprecate", "--ledger", self.tmp / "ledger.json", "import",
                      resolver, "--since", "1.5.0", "--removal", "2.0.0", cwd=self.tmp)
        self.assertEqual(0, proc.returncode, output(proc))
        self.assertFalse((self.tmp / "ledger.json").exists(), "a mark the later source took off")

    def test_an_inline_source_that_writes_a_token_ends_its_record(self):
        """Codex on #149, round 2: a source written inline in the resolver, after
        a file that records the token, never cleared the record."""
        hero = "clamp(2rem, 1rem + 4vw, 4rem)"
        self.dtcg("pub/a.tokens.json", {"space": {"4": self.REM}}, {"--size-hero": hero})
        self.write("pub/tokens.resolver.json", json.dumps({"version": "2025.10", "resolutionOrder": [
            {"type": "set", "name": "base", "sources": [
                {"$ref": "a.tokens.json"},
                {"size": {"hero": {"$type": "dimension", "$value": {"value": 2, "unit": "rem"}}}}]}]}))
        resolver = str(self.tmp / "pub" / "tokens.resolver.json")
        proc = run_py("design-system-docs", "extract_system", "--tokens", resolver, "--out", "system.json", cwd=self.tmp)
        self.assertEqual(0, proc.returncode, output(proc))
        got = {t["name"]: t["raw"] for t in json.loads((self.tmp / "system.json").read_bytes())["tokens"]}
        self.assertEqual("2rem", got["--size-hero"])

    def test_a_later_files_section_decides_the_tier(self):
        """Codex on #149, round 2: a later contract that files `--surface` as a
        role left it Tier 1, as the earlier contract's constant was."""
        schema = "web-design-suite/contract/1"
        self.write("first.json", json.dumps({"schema": schema, "constants": {"--surface": "#eeeeee"}}))
        self.write("second.json", json.dumps({"schema": schema, "roles": {"--surface": "#ffffff"}}))
        for order, tier in ((("first.json", "second.json"), 2), (("second.json", "first.json"), 1)):
            with self.subTest(order=order):
                args = [a for name in order for a in ("--tokens", name)]
                proc = run_py("design-system-docs", "extract_system", *args, "--out", "system.json", cwd=self.tmp)
                self.assertEqual(0, proc.returncode, output(proc))
                tiers = {t["name"]: t["tier"] for t in json.loads((self.tmp / "system.json").read_bytes())["tokens"]}
                self.assertEqual({"--surface": tier}, tiers)

    def test_a_contracts_literal_role_stays_tier_two(self):
        """Codex on #149: flattened to CSS, a contract's `--surface: #ffffff`
        role was Tier 1 by its value, and `--contract` moved it to constants."""
        self.write("contract.json", json.dumps({"schema": "web-design-suite/contract/1",
                                                "roles": {"--surface": "#ffffff"}}))
        proc = run_py("design-system-docs", "extract_system", "--tokens", "contract.json", "--out", "system.json",
                      "--contract", "round.json", cwd=self.tmp)
        self.assertEqual(0, proc.returncode, output(proc))
        tiers = {t["name"]: t["tier"] for t in json.loads((self.tmp / "system.json").read_bytes())["tokens"]}
        self.assertEqual({"--surface": 2}, tiers)
        self.assertEqual({"--surface": "#ffffff"}, json.loads((self.tmp / "round.json").read_bytes())["roles"])

    def test_each_copy_note_names_the_helpers(self):
        """V10: the note on copying a skill's scripts into a project's own
        `scripts/` named the commands only, not the project_config.py, dtcg.py
        or figma_common.py they import, so a copied command failed with
        ModuleNotFoundError. Copy what each note names, then run each Python
        command in the form its SKILL.md writes."""
        line = re.compile(r"^> This skill's scripts are in `\$\{CLAUDE_SKILL_DIR\}/scripts/` \((.*)\)\.$", re.M)
        seen = 0
        for skill in sorted(p for p in SKILLS.iterdir() if (p / "scripts").is_dir()):
            with self.subTest(skill=skill.name):
                text = (skill / "SKILL.md").read_bytes().decode("utf-8")
                m = line.search(text)
                self.assertIsNotNone(m, "no note names the scripts")
                named = set(re.findall(r"[\w.-]+\.(?:py|mjs)\b", m.group(1)))
                here = {p.name for p in (skill / "scripts").iterdir() if p.suffix in (".py", ".mjs")}
                self.assertEqual(here, named)
                project = self.tmp / skill.name
                (project / "scripts").mkdir(parents=True)
                for name in named:
                    (project / "scripts" / name).write_bytes((skill / "scripts" / name).read_bytes())
                module = "python -m scripts.NAME" in text
                for name in sorted(n for n in m.group(1).split(";")[0].replace(" ", "").split(",")
                                   if n.endswith(".py")):
                    form = ("-m", f"scripts.{name[:-3]}") if module else (f"scripts/{name}",)
                    proc = subprocess.run([sys.executable, "-B", *form, "--help"], cwd=project,
                                          env=env(PYTHONPATH=None), capture_output=True, timeout=120)
                    self.assertEqual(0, proc.returncode, f"{name}: {output(proc)}")
                seen += 1
        self.assertEqual(13, seen)


STARTER = SKILLS / "web-design-studio" / "assets" / "starter" / "styles" / "tokens.css"
# The "follow the OS unless overridden" idiom: the dark theme behind a guard.
OS_DARK = (":root { --neutral-50: #ffffff; --neutral-900: #171512;\n"
           "  --bg-canvas: var(--neutral-50); --fg-default: var(--neutral-900); }\n"
           "@media (prefers-color-scheme: dark) {\n"
           '  :root:not([data-theme="light"]) { --bg-canvas: var(--neutral-900); --fg-default: var(--neutral-50); }\n}\n')
DARK_BAND = "  [data-theme=\"dark\"] .inverse {\n    --fg-default:     var(--neutral-900);"


class TheDarkThemeIsTheDarkTheme(TempDirTest):
    """P71 (the 2026-10-28 audit's class 2): the docs and the diff read a rule
    as every reader does, by project_config.classify_rule(). PY-C-1: the dark
    band, `[data-theme="dark"] .inverse`, was filed as the dark theme and,
    written after it, replaced the dark text with the band's. PY-C-4: a
    `:not([data-theme="light"])` guard named a `light` theme and hid the dark."""

    def extract(self, css: str) -> dict:
        self.write("tokens.css", css)
        proc = run_py("design-system-docs", "extract_system", "tokens.css", "--out", "system.json", cwd=self.tmp)
        self.assertEqual(proc.returncode, 0, output(proc))
        data = json.loads((self.tmp / "system.json").read_text(encoding="utf-8"))
        tokens = data["tokens"]
        return {t["name"]: t for t in tokens} if isinstance(tokens, list) else tokens, data

    def diff(self, old: str, new: str) -> dict:
        self.write("old.css", old)
        self.write("new.css", new)
        proc = run_py("design-system-versioning", "diff_system", "old.css", "new.css", "--format", "json",
                      "--no-upstream", cwd=self.tmp)
        self.assertIn(proc.returncode, (0, 1), output(proc))
        return json.loads(proc.stdout)

    def test_the_starters_dark_text_is_measured_on_the_dark_surfaces(self):
        tokens, _ = self.extract(STARTER.read_text(encoding="utf-8"))
        for role, least in (("--fg-default", 15), ("--fg-strong", 15), ("--fg-muted", 4.5), ("--fg-link", 4.5)):
            with self.subTest(role=role):
                dark = {c["against"]: c["ratio"] for c in tokens[role]["contrast"] if c["theme"] == "dark"}
                self.assertGreater(dark["--bg-canvas"], least)

    def test_the_os_dark_theme_behind_a_guard_is_the_dark_theme(self):
        tokens, data = self.extract(OS_DARK)
        self.assertIn("dark", data["themes"])
        self.assertNotIn("light", [o["label"] for o in tokens["--bg-canvas"]["overrides"]])
        dark = {c["against"]: c for c in tokens["--fg-default"]["contrast"] if c["theme"] == "dark"}
        self.assertEqual("#171512", dark["--bg-canvas"]["bg_hex"])

    def test_the_diff_reads_the_os_dark_theme_too(self):
        res = self.diff(OS_DARK, OS_DARK.replace("--fg-default: var(--neutral-50); }", "--fg-default: #eeeeee; }"))
        self.assertEqual(["dark", "light"], sorted(res["old"]["themes"]))
        self.assertIn(("theme-override-changed", "--fg-default", "dark"),
                      [(c["kind"], c["subject"], c.get("theme")) for c in res["changes"]])

    def test_a_band_nested_under_a_theme_list_is_the_band(self):
        # CodeRabbit on #226: the chain joined by a space read
        # `[data-theme="dark"], .theme-dark { .inverse {…} }` as the dark theme.
        tokens, _ = self.extract(OS_DARK.split("@media")[0]
                                 + '[data-theme="dark"], .theme-dark { --bg-canvas: var(--neutral-900);'
                                 " --fg-default: var(--neutral-50);\n  .inverse { --fg-default: var(--neutral-900); }\n}\n")
        dark = {c["against"]: c["ratio"] for c in tokens["--fg-default"]["contrast"] if c["theme"] == "dark"}
        self.assertGreater(dark["--bg-canvas"], 15)

    def test_a_re_point_of_the_dark_text_is_a_visible_change(self):
        # PY-C-1 in the diff: the dark theme resolved to the band's values,
        # written after it, so re-pointing the dark text showed the same value
        # before and after, and the change was rated a patch.
        starter = STARTER.read_text(encoding="utf-8")
        theme = starter.index('  [data-theme="dark"] {')
        head, tail = starter[:theme], starter[theme:]
        new_tail, n = re.subn(r"(--fg-default:\s*)var\(--neutral-\d+\)", r"\1var(--neutral-500)", tail, count=1)
        self.assertEqual(1, n)
        res = self.diff(starter, head + new_tail)
        change = next(c for c in res["changes"] if c["subject"] == "--fg-default" and c.get("theme") == "dark")
        self.assertNotEqual(change["before"], change["after"])
        self.assertEqual("major", change["severity"])

    def test_a_change_in_the_dark_band_is_no_dark_theme_change(self):
        starter = STARTER.read_text(encoding="utf-8")
        self.assertIn(DARK_BAND, starter)
        res = self.diff(starter, starter.replace(DARK_BAND, DARK_BAND.replace("neutral-900", "neutral-800")))
        self.assertEqual([], [c for c in res["changes"] if c["kind"].startswith("theme-")
                              and c["subject"] == "--fg-default"])


if __name__ == "__main__":
    unittest.main()
