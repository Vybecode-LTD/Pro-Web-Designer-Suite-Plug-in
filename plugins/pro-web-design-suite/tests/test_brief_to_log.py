"""brief_to_log.py, a message brief's choices into the deck's decision log (P43).

Gaps closed (4.0.0):
- PS-C12: MESSAGE_BRIEF.md and DECISION_LOG.md never met. The positioning a
  landing page was built on reached the review only if someone wrote it up
  again, and the assumptions the brief listed were never asked in the room.

The worked example is the template's own: its brief, carried into the
template's decision log, read by the deck builder.
"""
from __future__ import annotations

import re
import unittest

from wds_support import SKILLS, TempDirTest, output, run_py

BRIEF = SKILLS / "landing-page-conversion" / "assets" / "MESSAGE_BRIEF.md"
LOG = SKILLS / "client-presentation-builder" / "assets" / "DECISION_LOG.md"


def worked_brief() -> str:
    """The template's worked example, as a brief of its own."""
    example = BRIEF.read_text(encoding="utf-8").split("# Worked example", 1)[1]
    return "# Message Brief — Referent" + example.split("\n", 1)[1]


def blocks(text: str) -> dict[str, str]:
    text = text.replace("\r\n", "\n")                             # a Windows console's stdout
    return {m.group(1): m.group(2)
            for m in re.finditer(r"^### D\d+ — ([^\n]+)\n(.*?)(?=^### |^## |\Z)", text, re.S | re.M)}


class BriefToLog(TempDirTest):

    def bridge(self, brief: str, *args):
        self.write("MESSAGE_BRIEF.md", brief)
        return run_py("landing-page-conversion", "brief_to_log", "MESSAGE_BRIEF.md", *args, cwd=self.tmp)

    def test_the_positioning_and_the_claim_become_decisions(self):
        proc = self.bridge(worked_brief())
        self.assertEqual(0, proc.returncode, output(proc))
        found = blocks(proc.stdout.decode("utf-8"))
        position = found["Positioning: who the page is for, and what it replaces"]
        self.assertIn("**Status:** decided", position)
        self.assertIn("**Choice:** For mixing engineers who deliver three to ten client revisions a week, Referent is "
                      "the reference-matching plugin", position)
        self.assertIn("**Constraint:** The page continues what its traffic started: Gearspace threads", position)
        self.assertIn("**Consequence:** Not for: mastering engineers who want a finished chain", position)
        self.assertIn("**Evidence:** 11 named beta testers", position)
        claim = found["The claim: Match your mix to a reference track's tonal balance in one pass"]
        self.assertIn("**Evidence:** Browser demo: drop in any two files", claim)
        # What the brief does not record stays a placeholder, never a guess.
        self.assertIn("**Constraint:** <the objection or the proof that made this the claim>", claim)
        self.assertIn("**Options:** <the claim you did not make>", claim)

    def test_each_assumption_becomes_an_open_question_and_keeps_its_emphasis(self):
        found = blocks(self.bridge(worked_brief()).stdout.decode("utf-8"))
        assumed = {t: b for t, b in found.items() if t.startswith("Assumed: ")}
        self.assertEqual(3, len(assumed))
        for title, body in assumed.items():
            with self.subTest(title=title):
                self.assertIn("**Status:** open", body)
                self.assertIn("**Say:** The page assumes that", body)
        self.assertIn("Assumed: The audience's primary pain is revision turnaround time, not audio quality."
                      " If it is actually quality, the claim's emphasis is wrong and the hero needs rewriting", found)

    def test_the_specificity_tests_first_answers_are_the_options_it_beat(self):
        brief = BRIEF.read_text(encoding="utf-8").split("# Worked example", 1)[0]
        brief = brief.replace("> For **__________________________** *(a specific person in a specific situation)*",
                              "> For **mixing engineers on deadline**", 1)
        for blank, fill in (("product", "Referent"), ("category", "a reference-matching plugin"),
                            ("the one thing it does better", "matches tonal balance in one pass"),
                            ("what they use today", "an hour of A/B-ing")):
            brief = brief.replace(f"**__________________________** *({blank})*", f"**{fill}**", 1)
        brief = brief.replace("| Who | | ☐ yes ☐ no | |", "| Who | creators | ☒ yes | mixing engineers on deadline |", 1)
        found = blocks(self.bridge(brief).stdout.decode("utf-8"))
        position = found["Positioning: who the page is for, and what it replaces"]
        self.assertIn('**Options:** who: "creators"', position)

    def test_an_unknown_becomes_an_open_question(self):
        brief = worked_brief().replace(
            "| **Traffic source** | Gearspace threads, a YouTube mixing channel, and the maker's newsletter |",
            "| **Traffic source** | UNKNOWN |", 1)
        found = blocks(self.bridge(brief).stdout.decode("utf-8"))
        self.assertIn("**Status:** open", found["Unknown: Traffic source"])

    def test_the_empty_template_has_nothing_to_carry(self):
        self.write("MESSAGE_BRIEF.md", BRIEF.read_text(encoding="utf-8"))
        proc = run_py("landing-page-conversion", "brief_to_log", "MESSAGE_BRIEF.md", cwd=self.tmp)
        self.assertEqual(1, proc.returncode, output(proc))
        self.assertIn("filled in to carry", output(proc))

    def test_into_adds_under_decisions_after_the_logs_own_and_only_once(self):
        log = self.write("DECISION_LOG.md", LOG.read_text(encoding="utf-8"))
        first = self.bridge(worked_brief(), "--into", "DECISION_LOG.md")
        self.assertEqual(0, first.returncode, output(first))
        self.assertIn("added 5 block(s)", output(first))
        text = log.read_text(encoding="utf-8")
        decisions = text.split("## Decisions", 1)[1].split("\n## ", 1)[0]
        self.assertEqual(["D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8"], re.findall(r"^### (D\d+)", decisions, re.M))
        self.assertRegex(decisions, r"### D4 — Positioning")
        self.assertTrue(decisions.rstrip().endswith("---"), "the template's rule after the blocks")
        again = self.bridge(worked_brief(), "--into", "DECISION_LOG.md")
        self.assertIn("added 0 block(s)", output(again))
        self.assertEqual(text, log.read_text(encoding="utf-8"))

    def test_into_a_log_with_no_decisions_or_none_at_all_is_refused(self):
        self.write("notes.md", "# Notes\n\nNo decisions here.\n")
        self.assertEqual(2, self.bridge(worked_brief(), "--into", "notes.md").returncode)
        self.assertEqual(2, self.bridge(worked_brief(), "--into", "missing.md").returncode)

    def test_the_deck_reads_what_it_wrote(self):
        self.write("DECISION_LOG.md", LOG.read_text(encoding="utf-8"))
        self.assertEqual(0, self.bridge(worked_brief(), "--into", "DECISION_LOG.md").returncode)
        proc = run_py("client-presentation-builder", "build_presentation", "DECISION_LOG.md", "--dry-run", cwd=self.tmp)
        plan = output(proc)
        self.assertIn("Positioning: who the page is for, and what it replaces", plan)
        self.assertIn("The claim: Match your mix to a reference track's tonal balance in one pass", plan)
        # Its gaps are named, not hidden: the claim's constraint was never in the brief.
        self.assertRegex(plan, r"D\d+: `constraint` still contains a template placeholder")


class TheBridgeIsWhereTheSkillsSayItIs(unittest.TestCase):

    def test_the_brief_the_log_and_the_skill_name_it(self):
        brief = " ".join(BRIEF.read_text(encoding="utf-8").split("# Worked example", 1)[0].split())
        self.assertIn("python -m scripts.brief_to_log MESSAGE_BRIEF.md --into DECISION_LOG.md", brief)
        self.assertIn("landing-page-conversion's `brief_to_log.py`", " ".join(LOG.read_text(encoding="utf-8").split()))
        skill = (SKILLS / "landing-page-conversion" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("(lint_claims.py, brief_to_log.py)", skill)
        self.assertIn("scripts.brief_to_log", skill)


if __name__ == "__main__":
    unittest.main()
