"""Everything the suite generates passes the gate the suite ships.

Guards, not regressions: the skills promise it ("the sheet obeys the laws too",
"the site obeys the laws", "so does every example", the scaffold "exits clean
on a fresh run"), so a stricter audit rule or a generator change cannot
silently break it. The presentation deck's CSS is covered in test_presentation.
"""
from __future__ import annotations

import json
import unittest

from wds_support import SKILLS, TempDirTest, output, run_py

STARTER = SKILLS / "web-design-studio" / "assets" / "starter" / "styles"
BUTTON_CSS = """@layer components {
  .button {
    padding: var(--pad-control-y) var(--pad-control-x);
    border-radius: var(--radius-md);
    background-color: var(--bg-accent);
    color: var(--fg-on-accent);
    font: var(--type-ui);
  }
  .button:hover { background-color: var(--bg-accent-hover); }
  .button:focus-visible { outline: var(--stroke-focus) solid var(--border-focus); }
  .button:disabled { opacity: var(--opacity-disabled); }
}
"""


class GeneratedOutputPassesTheGate(TempDirTest):

    def assert_clean(self, *paths):
        proc = run_py("web-design-studio", "audit_design", *paths, "--strict", cwd=self.tmp)
        self.assertEqual(proc.returncode, 0, output(proc))

    def test_state_matrix_sheet_css(self):
        self.write("components/button.css", BUTTON_CSS)
        self.write("templates.html", '<template id="button"><button class="button" {attrs}>'
                                     "{content}</button></template>\n")
        manifest = self.write("matrix.json", json.dumps({
            "$schema": "component-state-matrix/1", "project": "Guard",
            "tokens": str(STARTER / "tokens.css"), "base": [str(STARTER / "base.css")],
            "templates": "templates.html", "themes": ["light", "dark"],
            "densities": ["compact", "comfortable", "spacious"],
            "components": [{"name": "button", "css": "components/button.css",
                            "variants": ["default"], "sizes": ["default"],
                            "states": ["default", "hover", "focus-visible", "disabled"],
                            "content": {"default": "Save"}}]}))
        proc = run_py("component-state-matrix", "generate_matrix", manifest, "--out",
                      self.tmp / "sheet.html", "--emit-css", self.tmp / "matrix-chrome.css",
                      cwd=self.tmp)
        self.assertIn(proc.returncode, (0, 1), output(proc))
        self.assert_clean(self.tmp / "matrix-chrome.css")

    def test_docs_site_css_and_examples(self):
        self.write("src/components/button.css", BUTTON_CSS)
        self.write("prose/components/button.md",
                   "# Button\n\n```css\n.button { color: var(--fg-on-accent); }\n```\n")
        system = self.tmp / "system.json"
        proc = run_py("design-system-docs", "extract_system", STARTER, self.tmp / "src" / "components",
                      "--root", self.tmp, "--out", system, cwd=self.tmp)
        self.assertTrue(system.exists(), output(proc))
        proc = run_py("design-system-docs", "build_docs", system, "--out", self.tmp / "site",
                      "--prose", self.tmp / "prose", "--emit-css", self.tmp / "docs-chrome.css",
                      "--emit-examples", self.tmp / "examples", cwd=self.tmp)
        self.assertEqual(proc.returncode, 0, output(proc))
        self.assert_clean(self.tmp / "docs-chrome.css", self.tmp / "examples")

    def test_tailwind_scaffold(self):
        ddl = self.write("schema.sql", "create table products (\n  id uuid primary key default "
                                       "gen_random_uuid(),\n  name text not null,\n  price "
                                       "numeric(10,2) not null,\n  published boolean default false\n);\n")
        model = self.tmp / "model.json"
        proc = run_py("content-model-to-ui", "introspect_schema", ddl, "-o", model, cwd=self.tmp)
        self.assertTrue(model.exists(), output(proc))
        proc = run_py("content-model-to-ui", "scaffold_ui", model, "--stack", "tailwind",
                      "--out", self.tmp / "out-tw", cwd=self.tmp)
        self.assertEqual(proc.returncode, 0, output(proc))
        self.assert_clean(self.tmp / "out-tw")


if __name__ == "__main__":
    unittest.main()
