"""check_roles.py, the role-pair contrast gate (3.2.0).

Regressions covered:
- SS-B1, SS-C2: nothing resolved the Tier-2 roles per theme and checked the
  pairs components use, so every "Verified n:1" was written by hand. That is
  how SS-A4 shipped: dark error text, .inverse text and control borders under
  AA.
- SS-A8: color-system.md §6's role table disagreed with tokens.css in four
  rows, and its "live audit findings" described a problem the tokens had
  already fixed another way. The table is now generated, and checked here.
"""
from __future__ import annotations

import json
import re
import unittest

from wds_support import SKILLS, TempDirTest, output, run_py

STUDIO = SKILLS / "web-design-studio"
STARTER = STUDIO / "assets" / "starter" / "styles" / "tokens.css"


class CheckRoles(TempDirTest):

    def roles(self, css: str, *args):
        path = self.write("tokens.css", css)
        return run_py("web-design-studio", "check_roles", path, *args, cwd=self.tmp)

    def starter(self) -> str:
        return STARTER.read_text(encoding="utf-8")

    def test_the_starter_passes_every_declared_pair(self):
        proc = self.roles(self.starter())
        self.assertEqual(proc.returncode, 0, output(proc))
        self.assertIn("every declared pair clears its minimum", output(proc))

    def test_subtle_text_on_a_lightened_ramp_fails_on_the_well(self):
        css, n = re.subn(r"(--neutral-500:\s*oklch\()53\.5%", r"\g<1>60%", self.starter())
        self.assertEqual(n, 1)
        proc = self.roles(css)
        self.assertEqual(proc.returncode, 1, output(proc))
        self.assertIn("--fg-subtle on --bg-sunken (light)", output(proc))

    def test_inverse_text_is_measured_on_the_parent_themes_inverse_surface(self):
        css, n = re.subn(r"\n  \.inverse \{.*?\n  \}\n", "\n", self.starter(), flags=re.S)
        self.assertEqual(n, 1)
        proc = self.roles(css)
        self.assertEqual(proc.returncode, 1, output(proc))
        self.assertIn("--fg-default on --bg-inverse (inverse on the light --bg-inverse)", output(proc))

    def test_a_role_that_does_not_resolve_is_a_bad_invocation(self):
        proc = self.roles(":root { --fg-default: var(--nope); --bg-canvas: oklch(98% 0 0); }")
        self.assertEqual(proc.returncode, 2, output(proc))
        self.assertIn("--nope is not declared", output(proc))

    def test_a_pairs_file_written_by_powershell_is_read(self):
        pairs = self.tmp / "pairs.json"
        pairs.write_text(json.dumps([{"fg": "--fg-default", "bg": "--bg-canvas", "min": 4.5,
                                      "scopes": ["light", "dark"]}]), encoding="utf-16")
        proc = self.roles(self.starter(), "--pairs", pairs)
        self.assertEqual(proc.returncode, 0, output(proc))
        self.assertIn("2 of 2 pass", output(proc))


class RoleTableInTheDocs(TempDirTest):

    def test_color_system_quotes_the_generated_table(self):
        doc = (STUDIO / "references" / "color-system.md").read_text(encoding="utf-8")
        m = re.search(r"<!-- check_roles:table -->\n(.*?)<!-- /check_roles:table -->", doc, re.S)
        self.assertIsNotNone(m, "color-system.md §6 has no generated table")
        proc = run_py("web-design-studio", "check_roles", STARTER, "--table", cwd=self.tmp)
        self.assertEqual(proc.returncode, 0, output(proc))
        self.assertEqual(m.group(1), proc.stdout.decode("utf-8").replace("\r\n", "\n"))


if __name__ == "__main__":
    unittest.main()
