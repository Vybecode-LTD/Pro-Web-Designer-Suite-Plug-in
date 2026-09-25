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

from wds_support import SKILLS

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


if __name__ == "__main__":
    unittest.main()
