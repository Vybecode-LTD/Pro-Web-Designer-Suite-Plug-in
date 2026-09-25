"""web-design-studio: audit_design.py, the suite's central gate.

Regressions covered:
- Law 2: a plain `margin-top: var(--space-16)` counted as the legal
  `calc(var(--t) * -1)` cancellation, because the check looked for the
  substring "-1" anywhere — so any token named *-1, *-10 … *-19 waved it through.
- Law 1: `font-weight: 700` was never flagged; the type check only looked for
  values with a unit.
- Law 1: a raw colour inside a border/outline shorthand other than plain
  `border` (`border-bottom: 1px solid #ccc`, `outline: 2px solid #000`) was
  never flagged, and a named colour in any shorthand (`border: 1px solid red`)
  was not either.
- Baselines: keys embedded the OS path separator, so a baseline written on
  Windows suppressed nothing on Linux CI, and vice versa.
"""
from __future__ import annotations

import json
import unittest

from wds_support import TempDirTest, output, run_py


class AuditDesign(TempDirTest):

    def audit(self, css, *args):
        path = self.write("src/components/card.css", "@layer components {\n" + css + "\n}\n")
        proc = run_py("web-design-studio", "audit_design", "src", "--json", *args, cwd=self.tmp)
        self.assertIn(proc.returncode, (0, 1), output(proc))
        return path, json.loads(proc.stdout)

    def rules(self, css):
        return {(f["law"], f["rule"]) for f in self.audit(css)[1]}

    def test_law2_margin_with_a_token_named_like_minus_one_is_still_a_child_margin(self):
        for token in ("--space-1", "--space-10", "--space-16"):
            with self.subTest(token=token):
                self.assertIn(("L2", "child-margin"),
                              self.rules(f".card {{ margin-top: var({token}); }}"))

    def test_law2_real_token_cancellation_stays_legal(self):
        for value in ("calc(var(--space-4) * -1)", "calc(var(--space-16)*-1)",
                      "calc(-1 * var(--space-4))"):
            with self.subTest(value=value):
                self.assertNotIn(("L2", "child-margin"),
                                 self.rules(f".card {{ margin-top: {value}; }}"))

    def test_law1_numeric_font_weight_is_flagged(self):
        self.assertTrue(any(law == "L1" for law, _ in self.rules(".card { font-weight: 700; }")))
        self.assertEqual(self.rules(".card { font-weight: inherit; }"), set())

    def test_law1_colours_inside_border_and_outline_shorthands_are_flagged(self):
        cases = {
            "border-bottom: 1px solid #cccccc": "raw-color",
            "outline: 2px solid rgb(0 0 0)": "raw-color",
            "border-inline-start: 4px solid #333": "raw-color",
            "column-rule: 1px solid #ddd": "raw-color",
            "border: 1px solid red": "named-color",
            "outline: 2px solid navy": "named-color",
        }
        for decl, rule in cases.items():
            with self.subTest(decl=decl):
                self.assertIn(("L1", rule), self.rules(f".card {{ {decl}; }}"))

    def test_law1_tokenised_or_keyword_shorthands_stay_clean(self):
        for decl in ("border-bottom: 1px solid var(--border-default)",
                     "border: 1px solid transparent", "outline: none"):
            with self.subTest(decl=decl):
                found = {r for law, r in self.rules(f".card {{ {decl}; }}") if law == "L1"}
                self.assertFalse(found & {"raw-color", "named-color"}, decl)

    def test_a_baseline_works_whichever_os_wrote_it(self):
        css = ".card { padding: 13px; }"
        self.audit(css)                                   # creates the file
        baseline = self.tmp / "baseline.json"
        proc = run_py("web-design-studio", "audit_design", "src", "--write-baseline", baseline,
                      cwd=self.tmp)
        keys = json.loads(baseline.read_text(encoding="utf-8"))
        self.assertTrue(keys, output(proc))
        for sep in ("/", "\\"):                           # as Linux/macOS, as Windows
            with self.subTest(separator=sep):
                other = [k.split("|", 1)[0].replace("\\", "/").replace("/", sep) + "|" + k.split("|", 1)[1]
                         for k in keys]
                variant = self.write(f"baseline{ord(sep)}.json", json.dumps(other))
                proc = run_py("web-design-studio", "audit_design", "src", "--json",
                              "--baseline", variant, cwd=self.tmp)
                self.assertEqual(json.loads(proc.stdout), [], output(proc))
                self.assertEqual(proc.returncode, 0)


if __name__ == "__main__":
    unittest.main()
