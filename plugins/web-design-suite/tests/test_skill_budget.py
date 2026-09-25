"""web-design-suite: every skill fits what Claude Code keeps (phase 2, item 13).

Regressions covered:
- PS-A11, XC-C7, SS-C8, PS-C8, DL-C8, LC-C11: after compaction Claude Code
  keeps only the first 5,000 tokens of an invoked skill. Eight SKILL.md files
  ran past that, and landing-page-conversion's ethics section started at
  about token 4,800, so a long page build lost it.
- SB-C8: navigation-patterns.md was larger than one Read (25,000 tokens).
  The Read stopped at line 611 of 755 and lost the drawer and scroll-spy code.
- PS-C9, DL-C8, LC-C11, SS-C8: descriptions ran 776-955 characters, fired on
  each other's triggers, and said nothing about what each skill is not for.
"""
from __future__ import annotations

import re
import unittest

from wds_support import SKILLS

# `claude plugin details` put landing-page-conversion's SKILL.md at ~6,600
# tokens for 28.3 KB (3.1.0) and ~5,100 for 20.9 KB (3.2.0 draft): about 4.1
# bytes a token, so 5,000 tokens is ~20,500 bytes.
SKILL_BYTES = 20_500
# The Read tool stopped navigation-patterns.md at ~61 KB (25,000 tokens), for
# this suite's density of inline code; keep every reference under that.
REFERENCE_BYTES = 60_500
DESCRIPTION_CHARS = 420


def frontmatter_description(text: str) -> str:
    return re.search(r"^description:\s*(.*)$", text, re.M).group(1).strip().strip('"')


class SkillBudget(unittest.TestCase):

    def test_every_skill_md_fits_what_compaction_keeps(self):
        for skill in sorted(SKILLS.glob("*/SKILL.md")):
            with self.subTest(skill=skill.parent.name):
                self.assertLessEqual(len(skill.read_bytes()), SKILL_BYTES)

    def test_every_reference_fits_one_read(self):
        for ref in sorted(SKILLS.glob("*/references/*.md")):
            with self.subTest(ref=f"{ref.parent.parent.name}/{ref.name}"):
                self.assertLessEqual(len(ref.read_bytes()), REFERENCE_BYTES)

    def test_every_description_is_short_and_says_what_it_is_not_for(self):
        for skill in sorted(SKILLS.glob("*/SKILL.md")):
            description = frontmatter_description(skill.read_text(encoding="utf-8"))
            with self.subTest(skill=skill.parent.name):
                self.assertLessEqual(len(description), DESCRIPTION_CHARS)
                self.assertIn("Not for", description)
                first = re.split(r"(?<=[.!?])\s", description, 1)[0]
                self.assertLessEqual(len(first), 200, "the first sentence must work alone")

    def test_the_landing_page_rules_that_must_survive_come_first(self):
        text = (SKILLS / "landing-page-conversion" / "SKILL.md").read_text(encoding="utf-8")
        workflow = text.index("### Phase 1")
        for heading in ("## The ethics boundary", "## Evidence discipline"):
            with self.subTest(section=heading):
                self.assertIn(heading, text)
                self.assertLess(text.index(heading), workflow)


if __name__ == "__main__":
    unittest.main()
