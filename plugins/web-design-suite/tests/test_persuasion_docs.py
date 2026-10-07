"""The persuasion references: one rule for a risky request, and facts and
advice that hold on their own terms (P23).

Regressions covered (3.4.0):
- PS-A8: evidence.md §7.3 said to build a contrast failure the client asked
  for ("It is their site"), objection-handling §4 said "I'll build it either
  way" while §5 held the line on accessibility, and landing-page-conversion
  declined deceptive patterns: opposite answers to one request.
- PS-A9: DSA Art. 25 was said to "additionally" prohibit dark patterns, though
  it binds only online platforms and yields to the UCPD and the GDPR (Art.
  25(2)); the Digital Fairness Act was called "proposed" when it is announced.
- PS-A14: NN/g's five-user rule, which is for iterative qualitative testing,
  was applied to a five-second test that compares answers.
- PS-A15: "about 4% of male users" for colour vision deficiency; the NEI says
  about 1 in 12 men.
- PS-A16: critique-method §3.5's fix failed the suite's own gate, its §3.1 rg
  recipe counted every value once, and two docs said type roles carry
  tracking, which the `font` shorthand cannot.
- PS-A18: "captions and a transcript" for video at AA, though a transcript does
  not meet 1.2.5, and nothing for an audio-only demo (1.2.1).
- PS-A22: page-sections.css's comments against its code.

The docs are read through SKILLS, which honours WDS_PLUGIN_ROOT, so
tools/fail_before.py runs these against the previous release's docs.
"""
from __future__ import annotations

import re
import unittest

from wds_support import SKILLS, TempDirTest, output, run_py

LANDING = SKILLS / "landing-page-conversion"
DECK = SKILLS / "client-presentation-builder"
GATE = SKILLS / "design-critique-gate"


def read(path) -> str:
    """The file with its whitespace collapsed, so a wrapped phrase still matches."""
    return " ".join(path.read_text(encoding="utf-8").split())


def section(text: str, start: str, end: str = "\n## ") -> str:
    assert start in text, f"no {start!r}"
    return text.split(start, 1)[1].split(end, 1)[0]


class OneRuleForARiskyRequest(unittest.TestCase):

    def test_no_doc_builds_an_accessibility_failure_on_request(self):
        self.assertNotIn("Then build it. It is their site.", read(DECK / "references" / "evidence.md"))
        self.assertNotIn("I'll build it either way", read(DECK / "references" / "objection-handling.md"))

    def test_the_rule_is_stated_once_and_the_others_point_to_it(self):
        handling = (DECK / "references" / "objection-handling.md").read_text(encoding="utf-8")
        rule = section(handling, "**A risky request has one rule**", "\n---")
        for outcome in ("build it", "Hold the line", "Decline it", "their lawyer"):
            with self.subTest(outcome=outcome):
                self.assertIn(outcome, rule)
        for doc in (DECK / "references" / "evidence.md", LANDING / "SKILL.md"):
            with self.subTest(doc=doc.name):
                self.assertIn("objection-handling.md §5", read(doc))


class TheLegalStatements(unittest.TestCase):

    def test_the_dsa_and_the_digital_fairness_act_as_the_sources_say(self):
        law = section((LANDING / "references" / "conversion-audit.md").read_text(encoding="utf-8"),
                      "## 11. Dark patterns")
        law = " ".join(law.split())
        self.assertNotIn("additionally prohibits", law)
        self.assertNotIn("a proposed Digital Fairness Act", law)
        self.assertIn('"shall not apply to practices covered by Directive 2005/29/EC or '
                      'Regulation (EU) 2016/679"', law)
        self.assertIn('"Announced"', law)
        self.assertRegex(law, r"As of \d{4}-\d{2}-\d{2}")


class FiveSecondsIsNotAMeasure(unittest.TestCase):

    def test_five_people_catch_a_gross_failure_and_a_comparison_needs_twenty(self):
        audit = (LANDING / "references" / "conversion-audit.md").read_text(encoding="utf-8")
        test = " ".join(section(audit, "## 2. The five-second test").split())
        self.assertIn("a gross failure, not a measurement", test)
        self.assertIn("20 users", test)
        row = next(line for line in audit.splitlines() if line.startswith("| **Usability testing with five"))
        self.assertIn("Not for choosing between two versions", row)


class ColourVisionDeficiency(unittest.TestCase):

    def test_the_figure_is_the_neis(self):
        catalog = read(GATE / "references" / "failure-catalog.md")
        self.assertNotIn("4% of male users", catalog)
        self.assertIn("About 1 in 12 men have a color vision deficiency", catalog)


class TheAdviceHoldsOnItsOwnTerms(TempDirTest):

    def method(self) -> str:
        return (GATE / "references" / "critique-method.md").read_text(encoding="utf-8")

    def test_the_focus_ring_fix_passes_the_suites_gate(self):
        fix = section(self.method(), "### 3.5", "\n### ").split("**System fix.**", 1)[1]
        declarations = re.findall(r"`([a-z-]+:\s*[^`;]+)`", fix)
        self.assertGreaterEqual(len(declarations), 3, declarations)
        self.write("src/components/button.css",
                   "@layer components {\n  .button:focus-visible {\n"
                   + "".join(f"    {d};\n" for d in declarations) + "  }\n}\n")
        proc = run_py("web-design-studio", "audit_design", self.tmp / "src", "--strict", cwd=self.tmp)
        self.assertEqual(proc.returncode, 0, output(proc))

    def test_the_rg_recipe_drops_the_file_names(self):
        recipe = next(line for line in self.method().splitlines() if "uniq -c" in line)
        self.assertRegex(recipe, r"\brg (?:-I -o|-o -I|-oI|-Io|--no-filename)\b")

    def test_no_doc_says_a_type_role_carries_tracking(self):
        self.assertNotIn("Roles carry size, leading, tracking and weight", read(GATE / "references" / "critique-method.md"))
        copy = read(LANDING / "references" / "copy-patterns.md")
        self.assertNotIn("already carries `--leading-tight` and `--tracking-tighter`", copy)
        # What the docs now say is true: base.css tracks .text-display, and the
        # role itself is a font shorthand with no letter-spacing.
        styles = SKILLS / "web-design-studio" / "assets" / "starter" / "styles"
        self.assertRegex(styles.joinpath("base.css").read_text(encoding="utf-8"),
                         r"\.text-display \{[^}]*letter-spacing: var\(--tracking-tighter\)")
        role = re.search(r"--type-display:([^;]+);", styles.joinpath("tokens.css").read_text(encoding="utf-8"))
        self.assertNotIn("tracking", role.group(1))


class TheMediaAdvice(unittest.TestCase):

    def test_a_transcript_is_not_audio_description_and_audio_needs_text(self):
        architecture = read(LANDING / "references" / "page-architecture.md")
        self.assertNotIn("(WCAG 2.2 A/AA)", architecture)
        self.assertIn("a transcript meets 1.2.3 at A, not 1.2.5 at AA", architecture)
        self.assertIn("text alternative that presents the same information (1.2.1, A)", architecture)


class PageSectionsSaysWhatItDoes(unittest.TestCase):

    def setUp(self):
        self.css = (LANDING / "assets" / "page-sections.css").read_text(encoding="utf-8")

    def rule(self, selector: str) -> str:
        return re.search(rf"^\s*{re.escape(selector)} \{{([^}}]*)\}}", self.css, re.M).group(1)

    def test_the_header_counts_its_shells(self):
        words = {"seven": 7, "eight": 8, "nine": 9}
        stated = re.search(r"owns the (\w+) SECTION SHELLS", self.css).group(1).lower()
        header = self.css.split("RULES THIS FILE OBEYS", 1)[0]
        self.assertEqual(words[stated], len(re.findall(r"\b\d\. [A-Z]", header)))

    def test_the_avatar_gap_is_the_one_the_comment_and_the_reference_give(self):
        self.assertIn("Avatar -> name is --gap-fused", self.css)
        self.assertIn("gap: var(--gap-fused)", self.rule(".testimonial__attribution"))
        self.assertIn("Avatar → name `--gap-fused`", read(LANDING / "references" / "page-architecture.md"))

    def test_the_avatar_is_not_sized_as_a_tap_target(self):
        self.assertNotIn("--tap-min", self.rule(".testimonial__avatar"))

    def test_no_raw_opacity(self):
        self.assertNotRegex(self.css, r"opacity:\s*0?\.\d")

    def test_the_media_variant_comment_describes_the_media_variant(self):
        comment = self.css.split(".feature-card--media { padding: 0; }", 1)[0].rsplit("/*", 1)[1]
        self.assertNotIn("Bordered variant", comment)
        self.assertIn("Media variant", comment)


if __name__ == "__main__":
    unittest.main()
