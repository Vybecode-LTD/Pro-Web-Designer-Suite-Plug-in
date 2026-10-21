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

Gaps closed (4.0.0, P42):
- PS-B1: the skill prescribed countdowns, carousels, sticky bars, modals,
  consent banners, multi-step signup and toasts, and never held one to the
  WCAG 2.2 criterion it meets; the critique gate's layer 8 did not either.

The docs are read through SKILLS, which honours WDS_PLUGIN_ROOT, so
tools/fail_before.py runs these against the previous release's docs.
"""
from __future__ import annotations

import json
import re
import subprocess
import unittest

from wds_support import NODE, PLUGIN, SKILLS, TempDirTest, env, output, run_py, tool_modules

LANDING = SKILLS / "landing-page-conversion"
DECK = SKILLS / "client-presentation-builder"
GATE = SKILLS / "design-critique-gate"
A11Y = SKILLS / "a11y-audit-runner"
REGISTER = json.loads((PLUGIN / "tests" / "fixtures" / "evidence.json").read_bytes())
AXE = tool_modules("WDS_NODE_MODULES", "axe-core")


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
        # Codex on #70: the rule let the failing version ship on a written
        # sign-off, which the landing SKILL's "held, not built" contradicted.
        held = next(line for line in rule.splitlines() if line.startswith("| It breaks accessibility"))
        self.assertIn("not the failing one", held)
        self.assertNotIn("signs the site off", read(DECK / "references" / "evidence.md"))
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


# The level WCAG 2.2 gives each criterion the devices meet (the W3C
# Recommendation of 12 December 2024, re-read 2026-10-21).
LEVELS = {"1.3.5": "AA", "1.4.2": "A", "1.4.3": "AA", "1.4.13": "AA", "2.1.1": "A", "2.1.2": "A",
          "2.2.1": "A", "2.2.2": "A", "2.4.3": "A", "2.4.11": "AA", "2.5.8": "AA", "3.3.7": "A",
          "3.3.8": "AA", "4.1.3": "AA"}
# The devices PS-B1 names, and a criterion each must be held to.
DEVICES = {"countdown": "2.2.2", "held basket": "2.2.1", "carousel": "2.2.2", "audio demo": "1.4.2",
           "sticky": "2.4.11", "modal": "2.1.2", "on hover": "1.4.13", '"No thanks"': "2.5.8",
           "decline link": "1.4.3", "multi-step": "3.3.7", "sign-in": "3.3.8", "toast": "4.1.3",
           "consent banner": "2.4.11"}


def device_rows() -> list[list[str]]:
    """conversion-audit.md §7.1's rows: device, criteria, requirement, checked by."""
    text = (LANDING / "references" / "conversion-audit.md").read_text(encoding="utf-8")
    table = section(text, "### 7.1 The persuasive devices, against WCAG 2.2", "\n---")
    return [[c.strip() for c in line.strip().strip("|").split("|")]
            for line in table.splitlines() if line.startswith("| ") and not line.startswith("| Device")]


def criteria(cell: str) -> dict[str, str]:
    return dict(re.findall(r"(\d\.\d+\.\d+) [^;]*?\((A{1,3})\)", cell))


def no_gate_decides() -> set[str]:
    """The criteria a11y-audit-runner's coverage table leaves to a person: no
    tool decides them, or none in this suite does."""
    found = set()
    for line in (A11Y / "references" / "automation-coverage.md").read_text(encoding="utf-8").splitlines():
        m = re.match(r"\| \*\*(\d\.\d+\.\d+)\*\* [^|]+\| ([^|]+) \| ([^|]+) \|", line)
        if m and ("None" in m.group(2) or "*Not in this suite.*" in m.group(3)):
            found.add(m.group(1))
    return found


class PersuasiveDevicesAgainstWcag(unittest.TestCase):
    """PS-B1: each device the skill writes for, held to its WCAG 2.2
    criterion, with the check that decides it or a person where none does."""

    def test_each_device_is_held_to_its_criteria_at_their_levels(self):
        rows = device_rows()
        self.assertGreaterEqual(len(rows), len(set(DEVICES.values())))
        for row in rows:
            with self.subTest(device=row[0]):
                held = criteria(row[1])
                self.assertTrue(held, row[1])
                for sc, level in held.items():
                    self.assertEqual(LEVELS.get(sc), level, sc)
        for device, sc in DEVICES.items():
            with self.subTest(device=device):
                row = next((r for r in rows if device in r[0]), None)
                self.assertIsNotNone(row, f"no row for {device}")
                self.assertIn(sc, criteria(row[1]))

    def test_a_check_the_table_names_runs_and_reports_that_criterion(self):
        runtime = (A11Y / "scripts" / "a11y_runtime.mjs").read_text(encoding="utf-8")
        reports: dict[str, set] = {}
        for check, sc in re.findall(r"'(\w+)',\s*(?:'[\w-]+'|\w+),\s*'(\d\.\d+\.\d+)'", runtime):
            reports.setdefault(check, set()).add(sc)
        static = (A11Y / "scripts" / "a11y_static.py").read_text(encoding="utf-8")
        named = 0
        for row in device_rows():
            held = set(criteria(row[1]))
            for check in re.findall(r"`a11y_runtime`'s `(\w+)`(?: and `(\w+)`)?", row[3]):
                for name in filter(None, check):
                    named += 1
                    with self.subTest(device=row[0], check=name):
                        self.assertTrue(reports.get(name, set()) & held, (name, reports.get(name)))
            for rule in re.findall(r"`a11y_static`'s `([\w-]+)` \((\d\.\d+\.\d+)\)", row[3]):
                with self.subTest(device=row[0], rule=rule[0]):
                    self.assertRegex(static, rf'"{rule[0]}", "{re.escape(rule[1])}"')
                    self.assertIn(rule[1], held)
        self.assertGreaterEqual(named, 4)

    @unittest.skipUnless(NODE and AXE, "needs node plus WDS_NODE_MODULES holding axe-core")
    def test_an_axe_rule_the_table_names_carries_that_criterions_tag(self):
        wanted = [(rule, sorted(criteria(row[1]))) for row in device_rows()
                  for rule in re.findall(r"axe's `([\w-]+)`", row[3])]
        self.assertGreaterEqual(len(wanted), 3)
        proc = subprocess.run([NODE, "-e", "const a=require('axe-core');console.log(JSON.stringify("
                               "Object.fromEntries(a.getRules().map(r=>[r.ruleId,r.tags]))))"],
                              env=env(NODE_PATH=AXE), capture_output=True, timeout=60)
        self.assertEqual(proc.returncode, 0, output(proc))
        tags = json.loads(proc.stdout)
        for rule, held in wanted:
            with self.subTest(rule=rule):
                self.assertIn(rule, tags)
                self.assertTrue({"wcag" + sc.replace(".", "") for sc in held} & set(tags[rule]), tags[rule])

    def test_a_criterion_no_gate_decides_is_left_to_a_person(self):
        """automation-coverage.md §3 and this table agree: a device whose
        criteria no tool decides, or none in this suite, names no check."""
        manual = no_gate_decides()
        self.assertTrue({"2.2.1", "3.3.7", "4.1.3", "2.2.2"} <= manual, manual)
        for row in device_rows():
            held = set(criteria(row[1]))
            with self.subTest(device=row[0]):
                if held <= manual:
                    self.assertTrue(row[3].startswith("A person"), row[3])
                    self.assertNotIn("`", row[3])
                else:
                    self.assertIn("`", row[3])

    def test_the_aa_minimum_and_the_suites_floor_are_told_apart(self):
        audit = " ".join((LANDING / "references" / "conversion-audit.md").read_text(encoding="utf-8").split())
        self.assertIn("The 44px is the suite's policy; WCAG 2.2 AA asks less", audit)
        row = next(r for r in device_rows() if "2.5.8" in r[1])
        self.assertIn("24 by 24 CSS pixels", row[2])
        self.assertIn("`--tap-min` (44px) is its own policy, stricter than AA", row[2])

    def test_the_critique_gate_holds_the_same_devices(self):
        skill = (GATE / "SKILL.md").read_text(encoding="utf-8")
        layer = " ".join(section(skill, "### 8 — Interaction and motion", "\n### ").split())
        self.assertIn("`references/failure-catalog.md` L8-6", layer)
        catalog = (GATE / "references" / "failure-catalog.md").read_text(encoding="utf-8")
        entry = " ".join(section(catalog.split("## Layer 8", 1)[1], "### L8-6 ·", "\n---").split())
        self.assertIn("`references/conversion-audit.md` §7.1", entry)
        self.assertIn("failure-catalog.md` L8-6", " ".join(
            (LANDING / "references" / "conversion-audit.md").read_text(encoding="utf-8").split()))

    def test_the_criteria_figures_are_registered_at_the_w3c(self):
        doc = "landing-page-conversion/references/conversion-audit.md"
        for figure, anchor in (("24 by 24 CSS pixels", "target-size-minimum"), ("20 seconds", "timing-adjustable"),
                               ("five seconds", "pause-stop-hide"), ("3 seconds", "audio-control")):
            with self.subTest(figure=figure):
                entry = next((e for e in REGISTER["entries"] if e["figure"] == figure), None)
                self.assertIsNotNone(entry)
                self.assertEqual(f"https://www.w3.org/TR/WCAG22/#{anchor}", entry["url"])
                self.assertIn(doc, entry["docs"])


if __name__ == "__main__":
    unittest.main()
