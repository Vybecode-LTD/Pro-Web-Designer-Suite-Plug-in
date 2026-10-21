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
- PS-B2: nothing on UK consumer law, though the author is a UK company (the
  DMCC Act's reviews, total price and fines; the subscription rules to
  come), nor on the EU's reviews, "was" prices, personalised prices or
  withdrawal button; and drip pricing was missing from the ethics table.
- PS-B3: §9 treated a price test like any A/B test: no disclosure duty, no
  lowest-price record, and revenue per visitor's extra noise unsaid.
- PS-B8: §8 and §9 recommended session recordings, heatmaps and form
  analytics with no word on consent (ePrivacy, the GDPR, PECR as amended in
  2026) or on masking what people type, and the consent banner, a dark
  pattern of its own, had no rule.

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

    def test_the_target_size_row_keeps_every_exception(self):
        """Codex and CodeRabbit on #190: 24px or spacing is not all of 2.5.8.
        A link inside a sentence, an equivalent control, a browser's own
        control and an essential presentation are exempt."""
        row = next(r for r in device_rows() if "2.5.8" in r[1])
        for exception in ("A link inside a sentence", "a control with an equivalent elsewhere on the page",
                          "a browser's own control", "an essential presentation are exempt"):
            with self.subTest(exception=exception):
                self.assertIn(exception, row[2])

    def test_authentication_is_not_account_creation(self):
        """CodeRabbit on #190: 3.3.8 holds the steps that authenticate; WCAG's
        Understanding puts its focus on logging in, not on creating an account."""
        row = next(r for r in device_rows() if "3.3.8" in r[1])
        self.assertIn("3.3.8 holds the steps that authenticate, not account creation", row[2])
        self.assertNotIn("A signup or sign-in step", row[0])
        self.assertIn("1.3.5", criteria(row[1]))

    def test_a_modals_way_out_is_left_to_a_person(self):
        """Codex on #190: `taborder` presses only Tab, and an open modal may
        hold focus, so a modal with no keyboard way out passes it."""
        runtime = (A11Y / "scripts" / "a11y_runtime.mjs").read_text(encoding="utf-8")
        self.assertIn("const behindModal", runtime)                  # a modal may hold focus
        row = next(r for r in device_rows() if "modal" in r[0])
        self.assertIn("Esc, the close control and whether the order makes sense, a person", row[3])
        self.assertIn("`taborder` presses only Tab, and lets a modal hold focus", row[3])

    def test_the_catalogs_fix_keeps_two_point_two_points_conditions(self):
        """CodeRabbit on #190: a pause control is owed to movement that starts
        on its own and runs past five seconds beside other content, not to
        every movement."""
        catalog = (GATE / "references" / "failure-catalog.md").read_text(encoding="utf-8")
        entry = " ".join(section(catalog.split("## Layer 8", 1)[1], "### L8-6 ·", "\n---").split())
        self.assertNotIn("a pause control on every movement", entry)
        self.assertIn("a pause control on movement that starts on its own and runs past five seconds beside "
                      "other content (2.2.2's case)", entry)
        self.assertIn("a sticky bar that hides a button reached by Tab", entry)

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


def audit_text() -> str:
    return (LANDING / "references" / "conversion-audit.md").read_text(encoding="utf-8")


def law_rows() -> dict[str, list[str]]:
    """conversion-audit.md §11.1's rows by what the page does: UK, EU, flag."""
    table = section(audit_text(), "### 11.1 The UK and EU rules to flag for legal review", "\n---")
    rows = [[c.strip() for c in line.strip().strip("|").split("|")]
            for line in table.splitlines() if line.startswith("| ") and not line.startswith("| What the page")]
    return {row[0]: row[1:] for row in rows}


class TheLawToFlagForReview(unittest.TestCase):
    """PS-B2: the UK and EU rules a page meets, dated, each with the
    provision its source gives, and flagged for a lawyer, never advised on."""

    # What each row must cite, read at its source on 2026-10-21: the DMCC Act
    # at legislation.gov.uk, the directives through the EU Publications Office.
    CITES = {"reviews": ("Schedule 20, paragraph 13", "23b", "23c", "Art. 7(6)"),
             "fees": ("s. 230", "drip pricing", "Price Marking Order 2004", "Price Indication Directive Art. 2"),
             '"was" price': ("s. 226", "30 days", "Art. 6a"),
             "algorithm": ("Schedule 2", "Art. 6(1)(ea)", "recital 45"),
             "EU consumers": ("19 June 2026", '"withdraw from contract here"', "Art. 11a"),
             "subscription": ("not in force", "1 January 2027", "if Parliament approves")}

    def test_the_table_is_dated_and_flags_rather_than_advises(self):
        head = " ".join(section(audit_text(), "### 11.1 The UK and EU rules to flag", "\n| ").split())
        self.assertRegex(head, r"^[^*]*\*As of \d{4}-\d{2}-\d{2}\.\*")
        self.assertIn("not legal advice", head)
        self.assertIn("`objection-handling.md` §5", head)
        self.assertIn("in force since 6 April 2025", head)
        self.assertIn("10% of a trader's turnover or £300,000, whichever is higher", head)

    def test_each_rule_cites_the_provision_its_source_gives(self):
        rows = law_rows()
        for key, cites in self.CITES.items():
            with self.subTest(row=key):
                row = next((cells for what, cells in rows.items() if key in what), None)
                self.assertIsNotNone(row, f"no row for {key}")
                self.assertEqual(3, len(row))
                self.assertTrue(row[2], "nothing to flag")
                text = " ".join(" ".join(row).split())
                for cite in cites:
                    self.assertIn(cite, text)

    def test_the_uk_subscription_rules_are_not_called_in_force(self):
        uk = next(cells for what, cells in law_rows().items() if "subscription" in what)[0]
        self.assertNotRegex(uk, r"(?<!not )in force")
        self.assertIn("draft", uk.lower())

    def test_drip_pricing_is_declined_and_the_law_is_where_skill_md_says(self):
        skill = (LANDING / "SKILL.md").read_text(encoding="utf-8")
        boundary = section(skill, "## The ethics boundary", "\n---")
        self.assertRegex(boundary, r"\| Fees, delivery or tax added at checkout \| Drip pricing \|")
        self.assertIn("The UK, EU and US law behind each, to flag for legal review, is in "
                      "`references/conversion-audit.md` §11.", " ".join(boundary.split()))

    def test_the_dates_the_fine_and_the_figure_are_registered_at_their_sources(self):
        doc = "landing-page-conversion/references/conversion-audit.md"
        for figure, host in (("6 April 2025", "www.legislation.gov.uk"), ("10%", "www.legislation.gov.uk"),
                             ("30 days", "eur-lex.europa.eu"), ("19 June 2026", "eur-lex.europa.eu"),
                             ("1 January 2027", "www.gov.uk"), ("40%", "baymard.com")):
            with self.subTest(figure=figure):
                entry = next((e for e in REGISTER["entries"] if e["figure"] == figure and doc in e["docs"]), None)
                self.assertIsNotNone(entry)
                self.assertEqual(host, entry["url"].split("/")[2])
        fine = next(e for e in REGISTER["entries"] if e["figure"] == "10%" and doc in e["docs"])
        self.assertIn("£300,000", fine["also"])


class PriceTests(unittest.TestCase):
    """PS-B3: a price test tests the business, carries duties a headline test
    does not, and is measured on a noisier number."""

    def test_packaging_first_and_four_things_flagged(self):
        tests = " ".join(section(audit_text(), "### 9.1 Price tests", "\n---").split())
        self.assertIn("Test the packaging before the price", tests)
        for flag in ("**Personalisation.**", "**The lowest price shown is on the record.**",
                     "**The checkout charges what the page showed,**", "**Customers compare.**"):
            with self.subTest(flag=flag):
                self.assertIn(flag, tests)
        self.assertIn("(§11.1)", tests)

    def test_the_revenue_per_visitor_arithmetic_holds(self):
        """The doc's figures, from its own formula: n ≈ 16·σ²/δ², with
        σ² = p(1 − p) for a conversion and p·μ²(1 + c² − p) for revenue per
        visitor, where c is the orders' coefficient of variation."""
        tests = " ".join(section(audit_text(), "### 9.1 Price tests", "\n---").split())
        p, lift = 0.03, 0.20
        conversion = 16 * p * (1 - p) / (lift * p) ** 2
        revenue = 16 * (1 + 1 - p) / (lift ** 2 * p)                       # c = 1, μ cancels
        self.assertIn(f"about {round(conversion, -2):,.0f} visitors per variant on conversion", tests)
        self.assertIn(f"about {round(revenue, -2):,.0f} on revenue per visitor at c = 1", tests)
        def ratio(c: float) -> float:                                      # revenue's n over conversion's
            return (1 + c * c - p) / (1 - p)

        self.assertAlmostEqual(ratio(1), 2, delta=0.1)
        self.assertIn("about twice when order values vary as much as their mean (c = 1)", tests)
        self.assertAlmostEqual(ratio(2), 5, delta=0.2)
        self.assertIn("five times at c = 2", tests)
        # The baseline and the change are §9's own example.
        nine = " ".join(section(audit_text(), "## 9. A/B testing, honestly", "\n### 9.1").split())
        self.assertIn("Baseline conversion 3%", nine)
        self.assertIn("20% *relative* improvement", nine)
        self.assertIn(f"{round(conversion, -2):,.0f} per variant", nine)


class ConsentForTracking(unittest.TestCase):
    """PS-B8: what the instrumentation list needs before it runs, in the EU
    and the UK, read at the sources on 2026-10-21."""

    def consent(self) -> str:
        return " ".join(section(audit_text(), "### 8.1 Consent for what you measure", "\n---").split())

    def test_it_is_dated_and_flagged_for_a_lawyer(self):
        self.assertRegex(self.consent(), r"^[^*]*\*As of \d{4}-\d{2}-\d{2}, and a list to flag for the client's lawyer")

    def test_the_eu_row_cites_the_directive_the_regulation_and_planet49(self):
        text = self.consent()
        for cite in ("ePrivacy Directive Art. 5(3)", "strictly necessary", "GDPR Art. 4(11)",
                     "a pre-ticked box is not one", "C-673/17", "as easy as giving it (GDPR Art. 7(3))"):
            with self.subTest(cite=cite):
                self.assertIn(cite, text)

    def test_the_uk_row_gives_the_2026_statistics_exception_and_its_conditions(self):
        text = self.consent()
        self.assertIn("Since 5 February 2026, PECR (as the Data (Use and Access) Act 2025 amended it)", text)
        for condition in ("with a view to improving it", "can object simply and for free", "has not objected",
                          "the data goes to no one but those helping to improve the site",
                          "Schedule A1, paragraph 5"):
            with self.subTest(condition=condition):
                self.assertIn(condition, text)
        self.assertIn("an advertising pixel, still need consent", text)

    def test_recordings_are_masked_and_the_banner_is_held_to_the_edpb_and_wcag(self):
        text = self.consent()
        self.assertIn('"adequate, relevant and limited to what is necessary" (Art. 5(1)(c))', text)
        self.assertIn("Mask every input by default", text)
        self.assertIn("adopted on 17 January 2023", text)
        self.assertIn("no reject option on the layer that holds the accept button", text)
        self.assertIn("held to 1.4.3 like any other text (§7.1)", text)
        banner = next(r for r in device_rows() if r[0] == "A consent banner")
        self.assertIn("§8.1", banner[2])

    def test_the_instrumentation_list_points_to_the_rule(self):
        audit = " ".join(audit_text().split())
        self.assertIn("Record the field, never what was typed in it (§8.1).", audit)
        self.assertIn("With consent where the law asks for it, and every input masked (§8.1)", audit)

    def test_the_dates_are_registered_at_their_sources(self):
        doc = "landing-page-conversion/references/conversion-audit.md"
        for figure, host in (("5 February 2026", "www.legislation.gov.uk"), ("17 January 2023", "www.edpb.europa.eu")):
            with self.subTest(figure=figure):
                entry = next((e for e in REGISTER["entries"] if e["figure"] == figure and doc in e["docs"]), None)
                self.assertIsNotNone(entry)
                self.assertEqual(host, entry["url"].split("/")[2])


if __name__ == "__main__":
    unittest.main()
