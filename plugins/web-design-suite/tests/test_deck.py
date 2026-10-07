"""client-presentation-builder, the deck honest by construction (P21, part 1):

- PS-A5: `--a11y` accepted only axe's `{violations}`; the suite's own
  `a11y_runtime.mjs --json` and `a11y_static.py --json` emit `{tool, findings}`
  and were refused with "has no `violations` key".
- PS-A6: print mode showed every presenter note whatever the toggle, and the
  printed deck carried the appendix ("never presented") and the provenance
  slide; there was no handout build.
- PS-A7: a `reversed` decision ranked like a current one and became a headline
  slide argued with its old rationale.
- PS-A10: evidence.md's "Say this" lines gave a load time from a byte count, a
  dark-mode line count and a contrast ratio that were not the token file's,
  and the coverage of automated tools with no source.
- PS-C1, in part: the manual test record is an input (`--manual`), and the
  coverage range is cited from the register.
"""
from __future__ import annotations

import json
import re
import unittest

from test_presentation import A11Y_CLEAN, A11Y_WITH_VIOLATIONS, decision_log
from wds_support import SKILLS, TempDirTest, output, run_py

RUNTIME = {"tool": "a11y_runtime", "target": "http://localhost/", "findings": [
    {"check": "axe", "rule": "color-contrast", "sc": "1.4.3", "severity": "error",
     "message": "x", "fix": "y", "nodes": ["#a", "#b"]},
    {"check": "axe", "rule": "region", "sc": "", "severity": "warning",
     "message": "best practice", "fix": ""},
    {"check": "axe", "rule": "incomplete:color-contrast", "sc": "1.4.3",
     "severity": "warning", "message": "", "fix": ""},
    {"check": "keys", "rule": "no-accessible-name", "sc": "4.1.2", "severity": "error",
     "message": "", "fix": ""},
    {"check": "static", "rule": "heading-skip", "sc": "best practice", "severity": "warning",
     "message": "", "fix": ""}]}
STATIC_WARNING = {"tool": "a11y_static", "errors": 0, "warnings": 1, "findings": [
    {"file": "a.html", "line": 3, "category": "S", "rule": "no-main-landmark",
     "sc": "best practice", "severity": "warning", "message": "", "fix": ""},
    {"file": "a.html", "line": 9, "category": "S", "rule": "heading-skip",
     "sc": "best practice", "severity": "warning", "message": "", "fix": ""}]}
STATIC_ERROR = {"tool": "a11y_static", "errors": 1, "warnings": 0, "findings": [
    {"file": "a.html", "line": 3, "category": "forms", "rule": "control-no-label",
     "sc": "1.3.1", "severity": "error", "message": "", "fix": ""},
    {"file": "b.html", "line": 9, "category": "forms", "rule": "control-no-label",
     "sc": "1.3.1", "severity": "error", "message": "", "fix": ""}]}

REVERSED_LOG = """\
# Smoke deck

## Decisions

### D1 — Tokens
**Constraint:** Many developers touch the CSS.
**Choice:** A closed token system.

### D2 — Carousel on the homepage
**Status:** reversed
**Constraint:** The client asked for motion.
**Choice:** A five-slide hero carousel.

### D3 — Single-column form
**Constraint:** Two thirds of bookings start on a phone.
**Choice:** One column at every width.
"""
REVERSALS = """
## Reversals

| Date | Decision | Reversed to | Who asked | What it cost |
|---|---|---|---|---|
| `<date>` | `<D4>` | `<what replaced it>` | `<name>` | `<hours / scope / a compromise>` |
| 2026-10-01 | D2 | A static hero with one message | the client | two days |
"""


class Deck(TempDirTest):

    def build(self, log_text, *args):
        log = self.write("DECISION_LOG.md", log_text)
        return run_py("client-presentation-builder", "build_presentation", log, *args, cwd=self.tmp)

    def html(self, log_text, *args, name="deck.html"):
        out = self.tmp / name
        proc = self.build(log_text, "-o", out, *args)
        self.assertEqual(proc.returncode, 0, output(proc))
        return re.sub(r"\s+", " ", out.read_text(encoding="utf-8"))

    def outline(self, log_text, *args):
        proc = self.build(log_text, "--dry-run", *args)
        self.assertEqual(proc.returncode, 0, output(proc))
        return proc.stdout.decode("utf-8")


class TheSuitesOwnA11yJsonIsAnInput(Deck):
    """PS-A5."""

    def test_the_runtime_audits_findings_are_violations_when_they_name_a_criterion(self):
        a11y = self.write("a11y.json", json.dumps(RUNTIME))
        text = self.outline(decision_log("D1 — Tokens"), "--audience", "client", "--a11y", a11y)
        # color-contrast (2 nodes) and no-accessible-name (1): the best-practice
        # warning and the `incomplete` result are the tool's, not claims.
        self.assertIn("not clean (2 violation(s) on 3 element(s))", text)
        html = self.html(decision_log("D1 — Tokens"), "--a11y", a11y)
        self.assertNotIn("passes an automated WCAG 2.2 AA check", html)
        self.assertIn("color-contrast", html)
        self.assertNotIn("heading-skip", html)
        self.assertIn("<p class='metric__label'>target(s) scanned", html)

    def test_the_static_audits_findings_count_per_file(self):
        warning = self.write("w.json", json.dumps(STATIC_WARNING))
        html = self.html(decision_log("D1 — Tokens"), "--a11y", warning)
        self.assertIn("passes an automated WCAG 2.2 AA check", html)
        error = self.write("e.json", json.dumps(STATIC_ERROR))
        text = self.outline(decision_log("D1 — Tokens"), "--a11y", error)
        self.assertIn("not clean (2 violation(s) on 2 element(s))", text)
        html = self.html(decision_log("D1 — Tokens"), "--a11y", error, name="e.html")
        self.assertIn("#count(distinct findings[].file)\" data-value=\"2\">2</span></p>"
                      "<p class='metric__label'>file(s) with findings", html)
        self.assertNotIn("page(s) scanned", html)
        warn = self.html(decision_log("D1 — Tokens"), "--a11y", warning, name="w.html")
        self.assertIn("data-value=\"0\">0</span></p><p class='metric__label'>file(s) with findings", warn)

    def test_axe_results_still_read_and_anything_else_names_both_shapes(self):
        axe = self.write("axe.json", json.dumps(A11Y_WITH_VIOLATIONS))
        text = self.outline(decision_log("D1 — Tokens"), "--a11y", axe)
        self.assertIn("not clean (2 violation(s) on 3 element(s))", text)
        other = self.write("other.json", json.dumps({"summary": {}}))
        proc = self.build(decision_log("D1 — Tokens"), "--dry-run", "--a11y", other)
        self.assertEqual(proc.returncode, 2, output(proc))
        self.assertIn("has no `violations` and no `findings` key", output(proc))
        self.assertIn("a11y_runtime.mjs --json", output(proc))

    def test_a_findings_list_from_an_unknown_tool_is_refused_and_the_label_follows_the_shape(self):
        """Review of #65 (CodeRabbit): `{"findings": []}` from any tool read as
        a clean automated WCAG result, and the violations metric still said
        "across the pages scanned" for the static shape."""
        other = self.write("other.json", json.dumps({"tool": "lighthouse", "findings": []}))
        proc = self.build(decision_log("D1 — Tokens"), "--dry-run", "--a11y", other)
        self.assertEqual(proc.returncode, 2, output(proc))
        self.assertIn("its `tool` is 'lighthouse', not a11y_runtime or a11y_static", output(proc))
        bare = self.write("bare.json", json.dumps({"findings": []}))
        proc = self.build(decision_log("D1 — Tokens"), "--dry-run", "--a11y", bare)
        self.assertEqual(proc.returncode, 2, output(proc))
        mixed = self.write("mixed.json", json.dumps([A11Y_CLEAN, STATIC_WARNING]))
        proc = self.build(decision_log("D1 — Tokens"), "--dry-run", "--a11y", mixed)
        self.assertEqual(proc.returncode, 2, output(proc))
        self.assertIn("mixes shapes (axe and a11y_static) in one list", output(proc))
        two_axe = self.write("two.json", json.dumps([A11Y_CLEAN, A11Y_CLEAN]))
        self.assertIn("2</span></p><p class='metric__label'>page(s) scanned",
                      self.html(decision_log("D1 — Tokens"), "--a11y", two_axe, name="two.html"))
        empty = self.write("empty.json", json.dumps({"tool": "a11y_static", "findings": []}))
        html = self.html(decision_log("D1 — Tokens"), "--a11y", empty)
        self.assertIn("passes an automated WCAG 2.2 AA check", html)
        self.assertIn("across the file(s) with findings", html)
        self.assertNotIn("across the pages scanned", html)

    def test_the_manual_record_is_an_input(self):
        a11y = self.write("a11y.json", json.dumps(A11Y_CLEAN))
        record = self.write("tested.md", "Keyboard: every page, Tab and Shift+Tab, 2026-10-01.\n")
        html = self.html(decision_log("D1 — Tokens"), "--a11y", a11y, "--manual", record)
        self.assertIn("keyboard-tested by hand", html)
        empty = self.write("empty.md", "<!-- what was tested, by whom -->\n")
        html = self.html(decision_log("D1 — Tokens"), "--a11y", a11y, "--manual", empty, name="n.html")
        self.assertNotIn("keyboard-tested by hand", html)
        proc = self.build(decision_log("D1 — Tokens"), "--dry-run", "--manual", "missing.md")
        self.assertEqual(proc.returncode, 2, output(proc))


class AReversedDecisionIsShownAsReversed(Deck):
    """PS-A7."""

    def test_a_reversed_decision_is_not_a_headline_and_the_slide_says_what_replaced_it(self):
        text = self.outline(REVERSED_LOG + REVERSALS)
        self.assertNotRegex(text, r"decision\s+Carousel on the homepage")
        self.assertRegex(text, r"changed\s+What changed since last time")
        self.assertNotIn("D2 is reversed but nothing says what replaced it", text)
        html = self.html(REVERSED_LOG + REVERSALS)
        self.assertIn("A static hero with one message (asked by the client); cost: two days", html)
        self.assertLess(html.index("What changed since last time"), html.index("data-kind='decision'"))

    def test_a_reversal_row_alone_reverses_and_a_bare_status_is_a_gap(self):
        row_only = REVERSED_LOG.replace("**Status:** reversed\n", "") + REVERSALS
        text = self.outline(row_only)
        self.assertNotRegex(text, r"decision\s+Carousel on the homepage")
        self.assertRegex(text, r"changed\s+What changed")
        text = self.outline(REVERSED_LOG)
        self.assertRegex(text, r"changed\s+What changed")
        self.assertIn("D2 is reversed but nothing says what replaced it", text)
        plain = self.outline(decision_log("D1 — Tokens"))
        self.assertNotIn("What changed", plain)

    def test_a_reversed_to_line_on_the_block_counts(self):
        """Review of #65 (CodeRabbit): the line alone, with no status, must
        reverse the decision too."""
        log = REVERSED_LOG.replace("**Choice:** A five-slide hero carousel.\n",
                                   "**Choice:** A five-slide hero carousel.\n"
                                   "**Reversed to:** A static hero.\n").replace("**Status:** reversed\n", "")
        self.assertNotIn("Status", log)
        text = self.outline(log)
        self.assertNotIn("nothing says what replaced it", text)
        self.assertNotRegex(text, r"decision\s+Carousel on the homepage")
        self.assertRegex(text, r"changed\s+What changed")
        html = self.html(log)
        self.assertIn("A static hero", html)
        self.assertIn("What changed since last time", html)


class NotesNeverReachTheClient(Deck):
    """PS-A6."""

    def test_print_shows_notes_only_while_they_are_showing(self):
        html = self.html(decision_log("D1 — Tokens"))
        print_block = re.search(r"@media print \{(.*?)\n  \}", html.replace(" ", " "), re.S)
        css = html[html.index("@media print"):]
        self.assertIn(".notes { display: none; }", css)
        self.assertIn('.deck[data-notes="on"] .notes { display: flex;', css)
        self.assertNotRegex(css[:css.index('.deck[data-notes="on"] .notes')],
                            r"(?<![\]\w])\.notes \{ display: flex")
        _ = print_block

    def test_the_handout_carries_nothing_presenter_only(self):
        a11y = self.write("a11y.json", json.dumps(A11Y_WITH_VIOLATIONS))
        out = self.tmp / "deck.html"
        handout = self.tmp / "out" / "handout.html"
        proc = self.build(REVERSED_LOG + REVERSALS, "-o", out, "--handout", handout, "--a11y", a11y)
        self.assertEqual(proc.returncode, 0, output(proc))
        deck = out.read_text(encoding="utf-8")
        kept = handout.read_text(encoding="utf-8")
        for presenter_only in ("Presenter notes", "Gaps — fix before you present",
                               "Every decision, for the record", "Where every number came from",
                               "deck-provenance", "<script", "aria-hidden", "data-deck-notes",
                               "Fix before presenting"):
            self.assertIn(presenter_only, deck)
            self.assertNotIn(presenter_only, kept, presenter_only)
        self.assertIn('data-handout="on"', kept)
        self.assertIn('<meta name="deck-handout" content="yes">', kept)
        for slide in ("What changed since last time", "Accessibility, stated honestly",
                      "Single-column form", "A static hero with one message"):
            self.assertIn(slide, kept)
        self.assertIn("data-kind='decision'", kept)

    def test_the_handouts_css_is_the_decks_and_passes_the_gate(self):
        handout = self.tmp / "handout.html"
        proc = self.build(decision_log("D1 — Tokens"), "-o", self.tmp / "d.html", "--handout", handout,
                          "--emit-css", self.tmp / "css")
        self.assertEqual(proc.returncode, 0, output(proc))
        proc = run_py("web-design-studio", "audit_design", self.tmp / "css", "--strict", cwd=self.tmp)
        self.assertEqual(proc.returncode, 0, output(proc))
        self.assertIn('.deck[data-handout="on"]', handout.read_text(encoding="utf-8"))


class TheSayThisLinesCarryOnlyWhatTheInputsGive(Deck):
    """PS-A10."""

    def test_no_figure_the_inputs_cannot_give(self):
        text = (SKILLS / "client-presentation-builder" / "references" / "evidence.md").read_text(encoding="utf-8")
        for invented in ("under two seconds", "eleven lines", "4.6 to 1", "four-second wait",
                         "roughly a third of"):
            self.assertNotIn(invented, text, invented)
        for placeholder in ("`<total>`", "`<ratio>` to 1", "`<N>` re-pointed tokens", "measure_vitals.mjs"):
            self.assertIn(placeholder, text, placeholder)
        self.assertIn("41% of 143 planted barriers", text)
        self.assertIn("57% of issues by volume", text)

    def test_the_deck_cites_the_coverage_range(self):
        a11y = self.write("a11y.json", json.dumps(A11Y_CLEAN))
        html = self.html(decision_log("D1 — Tokens"), "--a11y", a11y)
        self.assertIn("the best single tool found 41% of 143 planted barriers", html)
        self.assertIn("Deque's study puts automation at 57% of issues by volume", html)
        self.assertNotIn("roughly a third", html)


SINCE = """
## Since last time

| You asked | What we did | If not, why not |
|---|---|---|
| `<their words>` | `<the change, with its decision id>` | `<the constraint, and what was done instead>` |
| A bigger logo | Doubled the mark in the header (D4) | |
| A carousel on the homepage | | It halves the LCP budget; the static hero carries the three messages instead |
| Blue buttons | | |
| A bigger map | Not implemented | |
| Fewer form fields | `<the change, with its decision id>` | `<the constraint, and what was done instead>` |
"""


class ThePresenterWindow(Deck):
    """PS-B7: pressing N on a shared screen showed the client the notes."""

    def test_the_deck_opens_a_presenter_window_kept_in_step(self):
        html = self.html(decision_log("D1 — Tokens"))
        for piece in ("new BroadcastChannel(deckId)", 'var deckId = "deck:" + window.location.pathname + ":" + document.title;',
                      "-presenter", "tell(peer)", 'target.postMessage({ deck: deckId, index: index }, "*")',
                      'window.addEventListener("message"', "peer = opened;", "toggleNotes(false);",
                      "data-deck-presenter-badge", 'key === "p" || key === "P"', "openPresenter()",
                      "show(data.index, true, false, true)", ">P<", "a presenter window"):
            self.assertIn(piece, html, piece)
        handout = self.tmp / "handout.html"
        proc = self.build(decision_log("D1 — Tokens"), "-o", self.tmp / "d.html", "--handout", handout)
        self.assertEqual(proc.returncode, 0, output(proc))
        kept = handout.read_text(encoding="utf-8")
        for piece in ("BroadcastChannel", "data-deck-presenter", "Presenter"):
            self.assertNotIn(piece, kept, piece)


class SinceLastTimeAndTheStage(Deck):
    """PS-B7 (§3.2) and PS-A13: the log could not say what was asked last time
    or what was not changed; the client order put the flaws after the screens
    and the evidence; the five structures were a promise with three orders."""

    def test_the_requests_from_last_time_are_a_slide_and_a_silent_no_is_a_gap(self):
        text = self.outline(decision_log("D1 — Tokens") + SINCE)
        self.assertRegex(text, r"changed\s+What changed since last time")
        self.assertIn('"Blue buttons" was not done and no reason is recorded', text)
        # Review of #66 (CodeRabbit): a negative outcome ("Not implemented")
        # and a row whose other cells are still the template's examples.
        self.assertIn('"A bigger map" was not done and no reason is recorded', text)
        self.assertIn('"Fewer form fields" was not done and no reason is recorded', text)
        self.assertNotIn('"A carousel on the homepage" was not done', text)
        html = self.html(decision_log("D1 — Tokens") + SINCE)
        self.assertIn("Doubled the mark in the header (D4)", html)
        self.assertIn("It halves the LCP budget", html)
        self.assertEqual(html.count("<em>not changed</em>"), 4)
        self.assertNotIn("Not implemented", html)
        self.assertNotIn("the constraint, and what was done instead", html)
        self.assertNotIn("the change, with its decision id", html)   # the template row is skipped

    def test_an_iteration_review_opens_on_what_changed_and_a_sign_off_on_the_ask(self):
        log = decision_log("D1 — Tokens", "D2 — Grid")
        plain = self.outline(log + SINCE)
        self.assertRegex(plain, r"\n  1\. cover[\s\S]*\n  2\. brief[\s\S]*\n  4\. changed")
        iteration = self.outline(log.replace("# Test deck\n", "# Test deck\n\n**Stage:** iteration review\n") + SINCE)
        self.assertRegex(iteration, r"\n  1\. cover[\s\S]*\n  2\. changed[\s\S]*\n  3\. brief")
        sign_off = self.outline(log.replace("# Test deck\n", "# Test deck\n\n**Stage:** sign-off\n"))
        # Review of #66 (Codex): the ask is the second slide, straight after
        # the cover, whether or not there is a decision index.
        self.assertRegex(sign_off, r"\n  1\. cover[\s\S]*\n  2\. ask[\s\S]*\n  3\. brief")
        narrative = (SKILLS / "client-presentation-builder" / "references" / "narrative-structure.md").read_text(encoding="utf-8")
        self.assertIn("so the table's job 6 is the second slide and the rest of its order is\nby hand", narrative)
        no_index = self.outline("# Test deck\n\n**Stage:** sign-off\n\n## Decisions\n\n### D1 — Tokens\n"
                                "**Status:** open\n**Constraint:** Many developers touch the CSS.\n"
                                "**Choice:** A closed token system.\n")
        self.assertRegex(no_index, r"\n  1\. cover[\s\S]*\n  2\. ask")

    def test_the_summary_table_agrees_with_the_order_and_the_channel_is_per_file(self):
        """Review of #66 (Codex): SKILL.md's audience table still said client
        weaknesses appear "Late, after the evidence", and two decks of one
        project on one origin shared a BroadcastChannel."""
        skill = (SKILLS / "client-presentation-builder" / "SKILL.md").read_text(encoding="utf-8")
        self.assertNotIn("Late, after the evidence", skill)
        self.assertIn("| **Weaknesses appear** | After decisions, before visuals |", skill)
        html = self.html(decision_log("D1 — Tokens"))
        self.assertIn('var deckId = "deck:" + window.location.pathname + ":" + document.title;', html)

    def test_the_flaws_come_before_the_screens_and_the_evidence(self):
        from test_presentation import FINDINGS
        path = self.write("findings.json", json.dumps({"subject": "Pricing", "findings": FINDINGS}))
        proc = run_py("design-critique-gate", "critique_report", path, "--format", "defence", cwd=self.tmp)
        self.assertEqual(proc.returncode, 0, output(proc))
        defence = self.write("defence.md", proc.stdout.decode("utf-8"))
        a11y = self.write("a11y.json", json.dumps(A11Y_CLEAN))
        text = self.outline(decision_log("D1 — Tokens"), "--defence", defence, "--a11y", a11y)
        self.assertIn("flaws", text)
        self.assertLess(text.index(". flaws "), text.index(". evidence-a11y "))
        self.assertLess(text.index(". decision "), text.index(". flaws "))


class TheDocsKeepTheirOwnRules(unittest.TestCase):
    """PS-A12, PS-A13, PS-A19, PS-B7: the prose and the markup."""

    def test_the_meeting_record_claims_no_legal_effect(self):
        text = (SKILLS / "client-presentation-builder" / "assets" / "MEETING_RECORD.md").read_text(encoding="utf-8")
        self.assertNotIn("turns a document into an agreement", text)
        self.assertIn("not an agreement and not legal advice", text)
        self.assertIn("Silence is not acceptance", text)

    def test_the_log_and_the_playbooks_cover_the_iteration_and_the_rejection(self):
        log = (SKILLS / "client-presentation-builder" / "assets" / "DECISION_LOG.md").read_text(encoding="utf-8")
        self.assertIn("## Since last time", log)
        self.assertIn("| You asked | What we did | If not, why not |", log)
        objections = (SKILLS / "client-presentation-builder" / "references" / "objection-handling.md").read_text(encoding="utf-8")
        self.assertIn("## 10. The client who rejects the whole direction", objections)
        self.assertIn("Do not redraw in the room", objections)
        narrative = (SKILLS / "client-presentation-builder" / "references" / "narrative-structure.md").read_text(encoding="utf-8")
        self.assertIn("§3.2 is the\nsame deck with `Stage: iteration review`", narrative)
        self.assertIn("`objection-handling.md` §7 |", narrative)
        self.assertNotIn("`objection-handling.md` §8 |", narrative)

    def test_every_painted_band_in_the_worked_example_bleeds_and_nests_a_page_grid(self):
        text = (SKILLS / "landing-page-conversion" / "references" / "worked-example.md").read_text(encoding="utf-8")
        painted = re.findall(r"^  <section [^\n]*section--(?:surface|sunken|inverse)[^\n]*\n([^\n]*)", text, re.M)
        self.assertEqual(len(painted), 5)
        for opening in re.findall(r"^  <section [^\n]*section--(?:surface|sunken|inverse)[^\n]*$", text, re.M):
            self.assertIn("bleed-full", opening, opening)
        for following in painted:
            self.assertEqual(following.strip(), '<div class="page-grid">', following)
        self.assertEqual(text.count("</div>\n  </section>"), 6, "the hero and the five bands")


if __name__ == "__main__":
    unittest.main()
