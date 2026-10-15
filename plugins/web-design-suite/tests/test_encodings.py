"""A project's file is read in the encoding it was saved in (the owner's audit
of 2026-10-14, class 4).

S8 and W7: PowerShell 5.1's `>` writes UTF-16LE. The token readers decoded
CSS as UTF-8 only, so a UTF-16 tokens.css read as no tokens and every
`var(--x)` was "unknown"; check_roles gave a UnicodeDecodeError traceback.
Every script now reads a project's text through project_config.read_text()
(json.detect_encoding()'s rules: a BOM, else the zero bytes), or a copy of it
in a script that runs on its own, and the two scripts that rewrite a file
write it back in the encoding they read it in.
"""
from __future__ import annotations

import json
import re
import shutil
import unittest

from wds_support import PLUGIN, SKILLS, TempDirTest, output, run_py

TOKENS = (":root {\n  --brand-500: #2563eb;\n  --bg-canvas: #ffffff;\n  --fg-default: #111111;\n"
          "  --bg-accent: var(--brand-500);\n  --fg-on-accent: #ffffff;\n}\n")
CHANGED = TOKENS.replace("#111111", "#222222")
EMAIL = ('<!doctype html><html lang="en"><head><title>t</title></head><body>'
         '<p style="color:#111111">Hi é</p></body></html>\n')
DECISIONS = ("# Test deck\n\n## Decisions\n\n### D1 — Tokens\n"
             "**Constraint:** Many developers touch the CSS.\n**Choice:** A closed token system.\n")
STARTER = SKILLS / "web-design-studio" / "assets" / "starter" / "styles" / "tokens.css"
UTF16 = "utf-16"            # with its byte-order mark, little-endian, as PowerShell 5.1 writes it

# label: (skill, script, files, arguments, the files saved as UTF-16 the second time)
CASES = {
    "check_roles": ("web-design-studio", "check_roles", {"tokens.css": STARTER.read_text(encoding="utf-8")},
                    ["tokens.css", "--json"], ["tokens.css"]),
    "audit_design": ("web-design-studio", "audit_design", {"src/a.css": ".a { padding: 13px; }\n"},
                     ["src", "--json"], ["src/a.css"]),
    "a11y_static": ("a11y-audit-runner", "a11y_static", {"src/a.html": '<p>é</p><img src="x.png">\n'},
                    ["src", "--json"], ["src/a.html"]),
    "extract_system": ("design-system-docs", "extract_system", {"tokens.css": TOKENS},
                       ["--tokens", "tokens.css"], ["tokens.css"]),
    "diff_system": ("design-system-versioning", "diff_system", {"old.css": TOKENS, "new.css": CHANGED},
                    ["old.css", "new.css", "--format", "json", "--no-upstream"], ["old.css", "new.css"]),
    "extract_literals": ("design-token-migration", "extract_literals",
                         {"src/a.css": ".a { color: #123456; padding: 13px; }\n"},
                         ["src", "--format", "json"], ["src/a.css"]),
    "lint_email": ("email-template-system", "lint_email", {"a.html": EMAIL},
                   ["a.html", "--format", "json"], ["a.html"]),
    "build_email": ("email-template-system", "build_email", {"a.html": EMAIL}, ["a.html"], ["a.html"]),
    "build_presentation": ("client-presentation-builder", "build_presentation",
                           {"DECISION_LOG.md": DECISIONS}, ["DECISION_LOG.md", "--dry-run"],
                           ["DECISION_LOG.md"]),
}


class EveryReaderTakesUtf16(TempDirTest):

    def run_case(self, skill, script, files, args, encoded, encoding):
        for child in list(self.tmp.iterdir()):
            shutil.rmtree(child) if child.is_dir() else child.unlink()
        for name, text in files.items():
            self.write(name, text.encode(encoding if name in encoded else "utf-8"))
        proc = run_py(skill, script, *args, cwd=self.tmp)
        return proc.returncode, proc.stdout.decode("utf-8", "replace")

    def test_utf16_reads_as_utf8_does(self):
        for case, (skill, script, files, args, encoded) in CASES.items():
            with self.subTest(case=case):
                code, out = self.run_case(skill, script, files, args, encoded, "utf-8")
                self.assertIn(code, (0, 1), out)
                self.assertEqual((code, out), self.run_case(skill, script, files, args, encoded, UTF16))

    def test_the_project_reader_takes_every_encoding(self):
        """read_tokens(): UTF-16 either way, with or without its mark, and UTF-32."""
        from wds_support import load_script
        pc = load_script("design-system-docs", "project_config")
        want = pc.read_tokens([self.write("t.css", TOKENS)]).values()
        self.assertIn("--brand-500", want)
        for encoding in ("utf-8-sig", "utf-16", "utf-16-le", "utf-16-be", "utf-32"):
            with self.subTest(encoding=encoding):
                path = self.write(f"t-{encoding}.css", TOKENS.encode(encoding))
                self.assertEqual(want, pc.read_tokens([path]).values())


class TheRewritersKeepTheEncoding(TempDirTest):
    """The codemod and `deprecate add --source` write a file back as they read
    it: a UTF-16 file stays UTF-16, its mark included."""

    def test_the_codemod(self):
        for encoding in ("utf-16", "utf-8-sig"):
            with self.subTest(encoding=encoding):
                css = self.write(f"{encoding}/card.css", "@layer components {\r\n  .card { margin: 13px; }\r\n}\r\n"
                                 .encode(encoding))
                mapping = self.write("mapping.json", json.dumps({
                    "schema": "design-token-migration/mapping@1",
                    "rules": [{"id": "space-13", "kind": "spacing", "scope": "value", "prop_classes": ["gap"],
                               "match": ["13px"], "replacement": "var(--gap-related)", "confidence": "snap"}]}))
                proc = run_py("design-token-migration", "apply_codemod", "-m", mapping, "--apply", css.parent,
                              cwd=self.tmp)
                self.assertEqual(0, proc.returncode, output(proc))
                self.assertEqual("@layer components {\r\n  .card { margin: var(--gap-related); }\r\n}\r\n"
                                 .encode(encoding), css.read_bytes())

    def test_deprecate_add(self):
        for encoding in ("utf-16", "utf-16-be", "utf-8-sig"):
            with self.subTest(encoding=encoding):
                before = ":root {\n  --fg-faint: #6b6b6b;\n  --fg-subtle: #767676;\n}\n"
                if encoding == "utf-16-be":                  # with its mark, big-endian
                    raw = b"\xfe\xff" + before.encode("utf-16-be")
                else:
                    raw = before.encode(encoding)
                tokens = self.write(f"tokens-{encoding}.css", raw)
                proc = run_py("design-system-versioning", "deprecate", "--ledger", self.tmp / f"{encoding}.json",
                              "add", "--name=--fg-subtle", "--kind", "token", "--since", "2.1.0",
                              "--removal", "3.0.0", "--replacement=--fg-faint", "--source", tokens, cwd=self.tmp)
                self.assertEqual(0, proc.returncode, output(proc))
                after = tokens.read_bytes()
                self.assertEqual(raw[:2], after[:2])                 # the mark, and so the byte order
                text = after.decode("utf-16" if encoding != "utf-8-sig" else "utf-8-sig")
                self.assertIn("@deprecated", text)
                self.assertEqual(before, "".join(line for line in text.splitlines(keepends=True)
                                                 if "@deprecated" not in line))


class NoScriptReadsUtf8Only(unittest.TestCase):
    """The class's check (audit §7, class 4): no script reads a file with an
    encoding it assumes. Reading the plugin's own template is allowed."""

    PATTERN = re.compile(r'\.read_text\(encoding="utf-8|open\((?![^)]*"w)[^)]*encoding="utf-8"')
    ALLOWED = {("install_gate.py", "TEMPLATE.read_text")}

    def offenders(self, text, name):
        return [line.strip() for line in text.splitlines() if self.PATTERN.search(line)
                and not any(name == f and a in line for f, a in self.ALLOWED)]

    def test_the_scan_fires(self):
        self.assertTrue(self.offenders('    css = path.read_text(encoding="utf-8-sig")\n', "x.py"))
        self.assertTrue(self.offenders('    with open(p, encoding="utf-8", newline="") as fh:\n', "x.py"))
        self.assertFalse(self.offenders('    with open(p, "w", encoding="utf-8") as fh:\n', "x.py"))

    def test_no_script_assumes_utf8(self):
        scripts = [p for p in [*SKILLS.glob("*/scripts/*.py"), *PLUGIN.glob("workflow-commands/*/scripts/*.py")]]
        self.assertTrue(scripts)
        found = {p.name: self.offenders(p.read_text(encoding="utf-8"), p.name) for p in scripts}
        self.assertEqual({}, {name: lines for name, lines in found.items() if lines})


if __name__ == "__main__":
    unittest.main()
