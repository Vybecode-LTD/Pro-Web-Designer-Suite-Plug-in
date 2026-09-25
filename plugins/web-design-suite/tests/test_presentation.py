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
"""
from __future__ import annotations

import json
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


if __name__ == "__main__":
    unittest.main()
