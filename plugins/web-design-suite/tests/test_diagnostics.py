"""What a script cannot use is named, never dropped (the owner's audit of
2026-10-14, class 7).

S2: read_tokens() and read_deprecations() threw away every problem
dtcg.tokens() reported, so a resolver with sixteen problems read silently.
V11: `figma_to_tokens --reverse` clamped a colour outside sRGB without a word.
V12: an input whose only tokens were unsupported said "contains no variables
… pass --shape", hiding what it held. M9: the codemod dropped a generated file
with no skip row. And diff_system skipped a pair whose contrast it could not
measure.
"""
from __future__ import annotations

import json
import re
import unittest

from wds_support import PLUGIN, SKILLS, TempDirTest, load_script, output, run_py

TYPOGRAPHY = {"brand": {"$type": "color", "500": {"$value": "#2563eb"}},
              "heading": {"$type": "typography", "$value": {"fontFamily": "Inter", "fontSize": "2rem"}}}
WHY = "a typography value in a form this script cannot write as CSS yet"


class TheTokenReadersKeepTheirProblems(TempDirTest):
    """S2: read_tokens() carries them, and each gate prints them as warnings."""

    # (skill, script, arguments): each reads the project's tokens through read_tokens()
    GATES = {
        "audit_design": ("web-design-studio", "audit_design", ["--tokens", "t.tokens.json", "src"]),
        "cluster_values": ("design-token-migration", "cluster_values",
                           ["--tokens", "t.tokens.json", "literals.json", "--dry-run"]),
        "figma_audit": ("figma-variables-sync", "figma_audit", ["--tokens", "t.tokens.json", "export.tokens.json"]),
        "figma_to_tokens": ("figma-variables-sync", "figma_to_tokens",
                            ["--tokens", "t.tokens.json", "export.tokens.json"]),
        "diff_system": ("design-system-versioning", "diff_system", ["t.tokens.json", "t.tokens.json"]),
    }

    def test_read_tokens_carries_them(self):
        pc = load_script("design-system-docs", "project_config")
        tokens = pc.read_tokens([self.write("t.tokens.json", json.dumps(TYPOGRAPHY))])
        self.assertEqual({"500": "#2563eb"}, tokens.ramps["brand"])
        self.assertEqual(1, len(tokens.problems), tokens.problems)
        self.assertIn(f"heading: {WHY}", tokens.problems[0])
        collected = []
        pc.read_deprecations([self.tmp / "t.tokens.json"], collected)
        self.assertEqual(tokens.problems, collected)

    def test_every_gate_prints_them(self):
        self.write("t.tokens.json", json.dumps(TYPOGRAPHY))
        self.write("src/a.css", "@layer components { .a { color: var(--brand-500); } }\n")
        self.write("export.tokens.json", json.dumps({"c": {"$type": "color", "$value": "#ffffff"}}))
        self.write("literals.json", json.dumps({"schema": "design-token-migration/literals@1", "literals": []}))
        for gate, (skill, script, args) in self.GATES.items():
            with self.subTest(gate=gate):
                proc = run_py(skill, script, *args, cwd=self.tmp)
                self.assertNotIn("Traceback", output(proc))
                self.assertRegex(proc.stderr.decode("utf-8", "replace"),
                                 rf"{gate}: warning: \S*t\.tokens\.json: heading: {re.escape(WHY)}")
        quiet = run_py("figma-variables-sync", "figma_to_tokens", "--quiet", *self.GATES["figma_to_tokens"][2],
                       cwd=self.tmp)                                  # "do not print warnings" (Codex on #140)
        self.assertNotIn("warning:", output(quiet))


class TheFigmaScriptsSayWhatTheyLeftOut(TempDirTest):

    def test_a_colour_outside_srgb_is_named_clamped(self):
        """V11: Figma holds sRGB, so the colour is clamped, and now said so."""
        css = self.write("tokens.css", ":root {\n  --wide: oklch(70% 0.3 150);\n  --plain: oklch(70% 0.1 150);\n}\n")
        proc = run_py("figma-variables-sync", "figma_to_tokens", css, "--reverse", cwd=self.tmp)
        self.assertEqual(1, proc.returncode, output(proc))
        self.assertIn("`--wide` = `oklch(70% 0.3 150)` lies outside sRGB", output(proc))
        self.assertNotIn("`--plain`", output(proc))                   # a control: inside sRGB

    def test_no_variables_names_what_it_held(self):
        """V12: an input whose only token is unsupported named none of it."""
        only = self.write("only.tokens.json", json.dumps({"heading": TYPOGRAPHY["heading"]}))
        for script in ("figma_to_tokens", "figma_audit"):
            with self.subTest(script=script):
                proc = run_py("figma-variables-sync", script, only, cwd=self.tmp)
                self.assertEqual(2, proc.returncode, output(proc))
                self.assertIn("What it held and could not give:", output(proc))
                self.assertIn("heading", output(proc).split("could not give:", 1)[1])


class TheCodemodSaysWhatItSkipped(TempDirTest):

    def test_a_generated_file_has_a_skip_row(self):
        """M9: every skip explains itself, a generated file's too."""
        self.write("src/gen.css", "/* @generated by a tool */\n.a { margin: 13px; }\n")
        mapping = self.write("mapping.json", json.dumps({"schema": "design-token-migration/mapping@1", "rules": [
            {"id": "space-13", "kind": "spacing", "scope": "value", "prop_classes": ["gap"], "match": ["13px"],
             "replacement": "var(--gap-related)", "confidence": "snap"}]}))
        proc = run_py("design-token-migration", "apply_codemod", "-m", mapping, "src", cwd=self.tmp)
        self.assertRegex(output(proc), r"gen\.css.*generated")


class TheContrastItCannotMeasureIsNamed(TempDirTest):

    def test_an_unresolved_colour_is_a_note(self):
        """Found beside H11: diff_system skipped a pair it could not measure."""
        old = ":root {\n  --brand-500: lab(30 40 59);\n  --fg-default: var(--brand-500);\n  --bg-canvas: #ffffff;\n}\n"
        self.write("old.css", old)
        self.write("new.css", old.replace("lab(30", "lab(35"))
        proc = run_py("design-system-versioning", "diff_system", "old.css", "new.css", "--no-upstream",
                      "--format", "json", cwd=self.tmp)
        notes = json.loads(proc.stdout)["notes"]
        self.assertTrue(any("contrast not measured" in n and "--fg-default on --bg-canvas" in n for n in notes), notes)


class NoProblemListIsDropped(unittest.TestCase):
    """The class's check (audit §7, class 7): no `_problems` and no `[0]` on
    what dtcg.tokens() or normalise() returns, in any script."""

    PATTERN = re.compile(r"\b_problems\b|(?:tokens|normalise)\([^)]*\)\[0\]")

    def test_the_scan_fires(self):
        self.assertTrue(self.PATTERN.search("    found, _problems = _dtcg(path).tokens(data)"))
        self.assertTrue(self.PATTERN.search("    found = dtcg.tokens(data)[0]"))

    def test_no_script_drops_them(self):
        files = [*SKILLS.glob("*/scripts/*.py"), *PLUGIN.glob("shared/*.py")]
        self.assertTrue(files)
        hits = {p.relative_to(PLUGIN).as_posix(): m.group(0) for p in files
                for m in [self.PATTERN.search(p.read_text(encoding="utf-8"))] if m}
        self.assertEqual({}, hits)


if __name__ == "__main__":
    unittest.main()
