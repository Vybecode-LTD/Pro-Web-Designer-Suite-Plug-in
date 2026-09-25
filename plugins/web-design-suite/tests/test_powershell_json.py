"""JSON written by PowerShell.

The suite's pipelines hand JSON from one tool to the next with a redirect
(`audit_design.py --json > audit.json`, then `--audit audit.json`). Windows
PowerShell's `>` writes that file as UTF-16, and PowerShell configured for
UTF-8 writes a byte-order mark; every reader used
`json.loads(path.read_text(encoding="utf-8"))` and rejected both as invalid
JSON — the error message even recommended the redirect that caused it.
"""
from __future__ import annotations

import json
import re
import unittest

from wds_support import NODE, SKILLS, TempDirTest, output, run_node, run_py

POWERSHELL_ENCODINGS = ("utf-8-sig", "utf-16")     # PS 7 / configured PS 5.1, stock PS 5.1
DECISION_LOG = """# Test deck

## Decisions

### D1 — One token system
**Constraint:** Many developers touch the CSS.
**Choice:** A closed token system with one home per component.
"""


class JsonFromPowerShell(TempDirTest):

    def reencode(self, path, encoding):
        """Rewrite a UTF-8 JSON file the way PowerShell would have written it."""
        target = path.with_name(f"{path.stem}.{encoding}{path.suffix}")
        target.write_bytes(path.read_text(encoding="utf-8").encode(encoding))
        return target

    def audit_json(self):
        css = self.write("src/components/card.css", "@layer components { .card { padding: 13px; } }\n")
        proc = run_py("web-design-studio", "audit_design", css.parent, "--json", cwd=self.tmp)
        self.assertIn(b"13px", proc.stdout, output(proc))
        return self.write("audit.json", proc.stdout)

    def test_critique_report_reads_findings_and_audit_json(self):
        findings = self.write("findings.json", "[]")
        audit = self.audit_json()
        for enc in POWERSHELL_ENCODINGS:
            with self.subTest(encoding=enc):
                proc = run_py("design-critique-gate", "critique_report",
                              self.reencode(findings, enc), "--audit", self.reencode(audit, enc),
                              cwd=self.tmp)
                self.assertNotIn("not valid JSON", output(proc))
                self.assertIn(proc.returncode, (0, 1), output(proc))

    def test_build_presentation_reads_audit_json(self):
        log = self.write("DECISION_LOG.md", DECISION_LOG)
        audit = self.audit_json()
        for enc in POWERSHELL_ENCODINGS:
            with self.subTest(encoding=enc):
                proc = run_py("client-presentation-builder", "build_presentation", log,
                              "--audit", self.reencode(audit, enc), "--dry-run", cwd=self.tmp)
                self.assertEqual(proc.returncode, 0, output(proc))

    def test_apply_codemod_reads_mapping_json(self):
        css = self.write("plain/a.css", ".card { margin: 13px; }\n")
        mapping = self.write("mapping.json", json.dumps({
            "schema": "design-token-migration/mapping@1",
            "rules": [{"id": "space-13", "kind": "spacing", "scope": "value", "prop_classes": ["gap"],
                       "match": ["13px"], "replacement": "var(--space-3)", "confidence": "snap"}]}))
        for enc in POWERSHELL_ENCODINGS:
            with self.subTest(encoding=enc):
                proc = run_py("design-token-migration", "apply_codemod", "-m",
                              self.reencode(mapping, enc), css, cwd=self.tmp)
                self.assertEqual(proc.returncode, 0, output(proc))
                self.assertIn("var(--space-3)", output(proc))

    def test_cluster_values_reads_literals_json(self):
        css = self.write("legacy/site.css", ".a { margin: 13px; color: #3a3a3a; }\n"
                                            ".b { padding: 16px; color: #3b3b3b; }\n")
        literals = self.tmp / "literals.json"
        proc = run_py("design-token-migration", "extract_literals", css.parent,
                      "--format", "json", "-o", literals, cwd=self.tmp)
        self.assertTrue(literals.exists(), output(proc))
        for enc in POWERSHELL_ENCODINGS:
            with self.subTest(encoding=enc):
                proc = run_py("design-token-migration", "cluster_values",
                              self.reencode(literals, enc), "--dry-run", cwd=self.tmp)
                self.assertEqual(proc.returncode, 0, output(proc))

    @unittest.skipUnless(NODE, "node is not installed")
    def test_a11y_runtime_reads_keymap_and_budget_json(self):
        from test_browser_scripts import STUB_PLAYWRIGHT
        self.write("proj/node_modules/playwright/index.mjs", STUB_PLAYWRIGHT)
        axe = self.write("proj/node_modules/axe-core/axe.min.js", "window.axe = {};")
        page = self.write("proj/page.html", "<!doctype html><title>t</title><main>hi</main>")
        browser = self.write("fake-browser.exe", "x")
        keymap = self.write("keymap.json", "{}")
        budget = self.write("budget.json", "{}")
        for enc in POWERSHELL_ENCODINGS:
            with self.subTest(encoding=enc):
                proc = run_node("a11y-audit-runner", "a11y_runtime.mjs", "--file", page,
                                "--axe", axe, "--browser", browser,
                                "--keymap", self.reencode(keymap, enc),
                                "--budget", self.reencode(budget, enc),
                                cwd=self.tmp / "proj", env_changes={"NODE_PATH": None})
                self.assertEqual(proc.returncode, 42, output(proc))


class NoFragileJsonReads(unittest.TestCase):
    """Source scan, so a reader added later cannot reintroduce the bug."""

    def test_python_json_is_parsed_from_bytes(self):
        for script in SKILLS.glob("*/scripts/*.py"):
            for n, line in enumerate(script.read_text(encoding="utf-8").splitlines(), 1):
                with self.subTest(file=script.name, line=n):
                    self.assertNotRegex(line, r"json\.loads?\(.*read_text\(",
                                        "parse JSON from read_bytes(); json detects the encoding")

    def test_node_json_is_read_through_the_bom_aware_helper(self):
        for script in SKILLS.glob("*/scripts/*.mjs"):
            text = script.read_text(encoding="utf-8")
            with self.subTest(file=script.name):
                self.assertIsNone(re.search(r"JSON\.parse\(\s*fs\.readFileSync", text))


if __name__ == "__main__":
    unittest.main()
