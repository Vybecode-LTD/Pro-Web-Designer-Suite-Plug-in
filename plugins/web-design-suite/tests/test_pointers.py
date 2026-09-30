"""Section pointers land on the section they mean (3.2.0).

Regressions covered:
- DL-A18: ten pointers named the wrong section; 3.0.1 had checked only that
  each target existed. Three were in code the scaffold generates into a user's
  project (screen-patterns section 10 for the states, 6 for delete, 11 for
  form UX).
- The same review found more: the absent decision-maker at objection-handling
  §8 (it is §7), layout-composition's anti-patterns at §11 (§10), focus through
  transitions at accessibility §4 (§3, Focus), a 2.x branch at rollout §5 (§7),
  and five pointers that named no file at all ("§8", "§7 of that file").

tools/check_pointers.py finds every pointer. Each must land on a numbered
heading, and each cross-file pointer on the heading recorded for it in
tests/fixtures/section-pointers.json, so renumbering a reference fails here
until every pointer into it has been read again.
"""
from __future__ import annotations

import importlib.util
import pathlib
import sys
import unittest

from wds_support import SKILLS, TempDirTest

HERE = pathlib.Path(__file__).resolve().parent


def load_tool(name: str):
    """A maintainer tool from this suite's own plugin, run against the tree
    under test (WDS_PLUGIN_ROOT may point at an older copy without it)."""
    spec = importlib.util.spec_from_file_location(f"wds_{name}", HERE.parent / "tools" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class SectionPointers(unittest.TestCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        cls.tool = load_tool("check_pointers")
        cls.unresolved, cls.unregistered, cls.moved, cls.stale = cls.tool.check(
            SKILLS, HERE / "fixtures" / "section-pointers.json")

    def test_the_tool_still_finds_the_pointers(self):
        self.assertGreater(len(self.tool.pointers(SKILLS)), 500)

    def test_every_pointer_lands_on_a_numbered_heading(self):
        self.assertEqual([], self.unresolved)

    def test_every_cross_file_pointer_lands_where_it_was_checked(self):
        self.assertEqual([], self.moved)
        self.assertEqual([], self.unregistered)        # a new pointer: read it, then register it
        self.assertEqual([], self.stale)


class WritingTheRegister(TempDirTest):
    """N6: --write-register records each cross-file pointer's heading as UTF-8
    with LF endings. It wrote with write_text(newline=""), which Python 3.9
    does not accept."""

    def test_a_non_ascii_heading_is_recorded_byte_for_byte(self):
        skills = self.tmp / "skills"
        self.write("skills/demo/SKILL.md", "Read `guide.md` §2 first.\n")
        self.write("skills/demo/references/guide.md", "# Guide\n\n## 2. Café crème\n\nText.\n")
        register = self.tmp / "fixtures" / "section-pointers.json"
        tool = load_tool("check_pointers")
        self.assertEqual(1, tool.write_register(skills, register))
        self.assertEqual(('[\n {\n  "from": "demo/SKILL.md",\n  "to": "demo/references/guide.md",\n'
                          '  "section": "2",\n  "heading": "Café crème"\n }\n]\n').encode("utf-8"),
                         register.read_bytes())
        self.assertEqual(([], [], [], []), tool.check(skills, register))


if __name__ == "__main__":
    unittest.main()
