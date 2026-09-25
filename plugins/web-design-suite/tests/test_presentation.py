"""client-presentation-builder: build_presentation.py; design-critique-gate: critique_report.py.

Regressions covered:
- `--notes` into a folder that did not exist, `--emit-css` onto an existing file
  and `-o` onto a folder raised raw tracebacks (exit 1) instead of the
  documented exit 2; `-o` created missing folders but `--notes` did not.
- Two `### D1 — …` blocks both rendered as "D1", indistinguishable in the deck,
  and an auto-numbered block could take an id an explicit block already had.
- The keyboard-help panel squeezed its answers into a ~60px column; the panel
  now sets the `.dlist` key-column socket (rendered widths are in the report —
  this suite checks the CSS still passes the gate the deck argues for).
- (bug 5) `--dry-run` and critique_report crashed on non-cp1252 text outside
  Claude Code.

3.1.0:
- PS-A1: the deck's claims were fixed text. The accessibility slide told the
  client "this page passes an automated WCAG 2.2 AA check and has been
  keyboard-tested by hand" beside a table of violations and with no record of
  any keyboard test; the performance slide was titled "It is fast, and it
  stays fast" at 152% of budget; the creative-director slides claimed "Nine
  laws, machine-enforced" (the audit checks L1–L6).
- PS-A2: the defence sheet's "Known flaws" kept only findings that were NOT
  confirmed, so confirmed defects vanished while suspicions were presented as
  known flaws — and the deck's "What we are not happy with yet" slide copied it.
- PS-A3: a hand finding that merely contained an audit rule's name as an
  ordinary word ("the most important plan"; the rule is `important`) silently
  folded that rule's whole machine group, defeating --audit-blocking too.
"""
from __future__ import annotations

import json
import re
import unittest

from wds_support import TempDirTest, output, run_py

OUTSIDE_CLAUDE_CODE = {"PYTHONIOENCODING": None, "PYTHONUTF8": None}


def decision_log(*blocks: str, title: str = "Test deck") -> str:
    body = "\n".join(f"### {b}\n**Constraint:** Many developers touch the CSS.\n"
                     f"**Choice:** A closed token system.\n" for b in blocks)
    return f"# {title}\n\n## Decisions\n\n{body}"


class BuildPresentation(TempDirTest):

    def build(self, log_text, *args, env_changes=None):
        log = self.write("DECISION_LOG.md", log_text)
        return run_py("client-presentation-builder", "build_presentation", log, *args,
                      cwd=self.tmp, env_changes=env_changes)

    def test_notes_are_written_into_a_folder_that_does_not_exist_yet(self):
        proc = self.build(decision_log("D1 — Tokens"), "-o", self.tmp / "deck.html",
                          "--notes", self.tmp / "handouts" / "notes.md")
        self.assertEqual(proc.returncode, 0, output(proc))
        self.assertTrue((self.tmp / "handouts" / "notes.md").exists())

    def test_unwritable_targets_are_bad_invocations(self):
        self.write("blocked", "a file where a folder is expected")
        (self.tmp / "a-folder").mkdir()
        cases = {"--emit-css onto a file": ["-o", self.tmp / "d.html", "--emit-css", self.tmp / "blocked"],
                 "-o onto a folder": ["-o", self.tmp / "a-folder"]}
        for label, args in cases.items():
            with self.subTest(case=label):
                proc = self.build(decision_log("D1 — Tokens"), *args)
                self.assertNotIn("Traceback", output(proc))
                self.assertEqual(proc.returncode, 2, output(proc))

    def test_duplicate_decision_ids_are_refused(self):
        proc = self.build(decision_log("D1 — First", "D1 — Second"), "--dry-run")
        self.assertEqual(proc.returncode, 2, output(proc))
        self.assertIn("D1", output(proc))

    def test_auto_numbering_skips_ids_already_taken(self):
        proc = self.build(decision_log("D2 — Explicit", "No id on this one"), "--dry-run")
        self.assertEqual(proc.returncode, 0, output(proc))
        self.assertEqual(output(proc).count("[D2]"), 1, output(proc))
        self.assertIn("[D3]", output(proc))

    def test_the_decks_css_still_passes_the_design_gate(self):
        css_dir = self.tmp / "deck-css"
        proc = self.build(decision_log("D1 — Tokens"), "-o", self.tmp / "d.html", "--emit-css", css_dir)
        self.assertEqual(proc.returncode, 0, output(proc))
        components = (css_dir / "deck-components.css").read_text(encoding="utf-8")
        self.assertRegex(components, r"\.help__panel\s*\{[^}]*--dlist-key")
        audit = run_py("web-design-studio", "audit_design", css_dir, "--strict", cwd=self.tmp)
        self.assertEqual(audit.returncode, 0, output(audit))

    def test_dry_run_prints_non_cp1252_text_outside_claude_code(self):
        proc = self.build(decision_log("D1 — Launch 🚀 → now", title="Déjà vu Δ"), "--dry-run",
                          env_changes=OUTSIDE_CLAUDE_CODE)
        self.assertNotIn("UnicodeEncodeError", output(proc))
        self.assertIn("🚀", proc.stdout.decode("utf-8"))


A11Y_WITH_VIOLATIONS = {"violations": [
    {"id": "color-contrast", "impact": "serious", "nodes": [{}, {}]},
    {"id": "label", "impact": "critical", "nodes": [{}]}]}
A11Y_CLEAN = {"violations": [], "passes": [{"id": "image-alt"}]}


class DeckClaimsFollowTheData(TempDirTest):
    """PS-A1."""

    build = BuildPresentation.build

    def deck(self, log_text, *args):
        out = self.tmp / "deck.html"
        proc = self.build(log_text, "-o", out, *args)
        self.assertEqual(proc.returncode, 0, output(proc))
        return re.sub(r"\s+", " ", out.read_text(encoding="utf-8"))

    def test_an_accessibility_slide_with_violations_claims_no_pass(self):
        a11y = self.write("a11y.json", json.dumps(A11Y_WITH_VIOLATIONS))
        html = self.deck(decision_log("D1 — Tokens"), "--audience", "client", "--a11y", a11y)
        self.assertNotIn("passes an automated WCAG 2.2 AA check", html)
        self.assertNotIn("keyboard-tested by hand", html)

    def test_keyboard_testing_is_claimed_only_when_the_log_records_it(self):
        a11y = self.write("a11y.json", json.dumps(A11Y_CLEAN))
        html = self.deck(decision_log("D1 — Tokens"), "--audience", "client", "--a11y", a11y)
        self.assertIn("passes an automated WCAG 2.2 AA check", html)
        self.assertNotIn("keyboard-tested by hand", html)
        template_only = decision_log("D1 — Tokens") + (
            "\n## Tested by hand\n\n<!-- What was checked manually, by whom, when. -->\n")
        html = self.deck(template_only, "--audience", "client", "--a11y", a11y)
        self.assertNotIn("keyboard-tested by hand", html)       # a comment records nothing
        tested = decision_log("D1 — Tokens") + (
            "\n## Tested by hand\n\nKeyboard: every page, Tab and Shift+Tab, 2026-09-20.\n")
        html = self.deck(tested, "--audience", "client", "--a11y", a11y)
        self.assertIn("keyboard-tested by hand", html)

    def test_a_page_over_budget_is_not_called_fast(self):
        perf = self.write("perf.json", json.dumps({
            "ledger": {"bytes": {"total": 912000}, "assets": []},
            "budget": {"bytes": {"total": 600000}},
            "findings": [{"severity": "error", "rule": "B total-over-budget"}]}))
        html = self.deck(decision_log("D1 — Tokens"), "--audience", "client", "--perf", perf)
        self.assertNotIn("It is fast, and it stays fast", html)
        self.assertIn("over", html.lower())

    def test_the_audit_is_credited_with_the_laws_it_checks(self):
        audit = self.write("audit.json", "[]")
        html = self.deck(decision_log("D1 — Tokens"), "--audience", "creative-director",
                         "--audit", audit, "--a11y", self.write("a.json", json.dumps(A11Y_CLEAN)))
        self.assertNotIn("Nine laws, machine-enforced", html)
        self.assertNotIn("clears its floor by measurement", html)


class CritiqueReport(TempDirTest):

    def test_summary_prints_non_cp1252_text_outside_claude_code(self):
        findings = self.write("findings.json", json.dumps(
            [{"layer": "premise", "severity": "minor", "title": "Hero promise unclear 😀 → fix"}]))
        for args in ([], ["--summary"], ["--format", "triage"], ["--format", "defence"]):
            with self.subTest(args=args):
                proc = run_py("design-critique-gate", "critique_report", findings, *args,
                              cwd=self.tmp, env_changes=OUTSIDE_CLAUDE_CODE)
                self.assertNotIn("UnicodeEncodeError", output(proc))
                self.assertIn(proc.returncode, (0, 1), output(proc))


FINDINGS = [
    {"layer": "color", "severity": "major", "confidence": "confirmed",
     "title": "Muted text on the sunken band fails contrast",
     "evidence": "Measured 3.2:1", "fix": "Re-point --fg-muted on sunken bands."},
    {"layer": "craft", "severity": "minor", "confidence": "suspected",
     "title": "Icon weights may differ", "fix": "Check the icon set."},
    {"layer": "color", "severity": "minor", "confidence": "confirmed", "status": "fixed",
     "title": "Link underline too faint", "fix": "Done in 4f2a."},
]
AUDIT_IMPORTANT = [{"file": f"src/a{i}.css", "line": i, "law": "L5", "rule": "important",
                    "severity": "error", "message": "`!important` on `color`.", "fix": "",
                    "snippet": ".a { color: red !important; }"} for i in range(1, 4)]


class CritiqueDefenceAndMerge(TempDirTest):
    """PS-A2 and PS-A3."""

    def run_report(self, findings, *args):
        path = self.write("findings.json", json.dumps({"subject": "Pricing", "findings": findings}))
        return run_py("design-critique-gate", "critique_report", path, *args, cwd=self.tmp)

    def test_the_defence_sheet_carries_open_confirmed_defects_and_labels_suspicions(self):
        proc = self.run_report(FINDINGS, "--format", "defence")
        text = proc.stdout.decode("utf-8")
        flaws = text.split("## Known flaws you are carrying in", 1)[1].split("## ", 1)[0]
        self.assertIn("Muted text on the sunken band fails contrast", flaws)
        self.assertRegex(flaws, r"Icon weights may differ \| minor[^|]*suspected")
        self.assertNotIn("Link underline too faint", flaws)          # status: fixed

    def test_an_ordinary_word_does_not_fold_a_rule(self):
        audit = self.write("audit.json", json.dumps(AUDIT_IMPORTANT))
        hand = [{"layer": "hierarchy", "severity": "major",
                 "title": "The most important plan is not visually recommended"}]
        proc = self.run_report(hand, "--audit", audit, "--format", "triage")
        self.assertIn("important × 3", proc.stdout.decode("utf-8"), output(proc))
        proc = self.run_report(hand, "--audit", audit, "--audit-blocking", "important",
                               "--fail-on", "blocking", "--summary")
        self.assertEqual(proc.returncode, 1, output(proc))

    def test_a_rule_is_folded_when_the_hand_finding_claims_it(self):
        audit = self.write("audit.json", json.dumps(AUDIT_IMPORTANT))
        for claim in ({"covers": ["important"]}, {"evidence": "the audit's `important` rule, 3 sites"}):
            with self.subTest(claim=claim):
                hand = [dict({"layer": "conformance", "severity": "major",
                              "title": "Specificity fights in the legacy sheets"}, **claim)]
                proc = self.run_report(hand, "--audit", audit, "--format", "triage")
                self.assertNotIn("important × 3", proc.stdout.decode("utf-8"))
                self.assertIn("folded", output(proc))                  # said, on stderr


if __name__ == "__main__":
    unittest.main()
