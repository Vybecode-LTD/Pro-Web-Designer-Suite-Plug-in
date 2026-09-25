"""web-design-suite: regressions found in the parallel bug hunt across
design-system-docs, design-system-versioning, figma-variables-sync and
email-template-system.

Regressions covered:
- SYS-1: extract_system.py's undocumented-component/orphan-doc gaps embedded
  the machine's absolute path (username included) in "where" instead of
  routing it through rel(), and rel() itself used the OS path separator --
  so system.json was neither "relative to --root" nor portable across OSes.
- SYS-2: deprecate.py's `retire` let a deprecation that was never scanned
  through silently (usage == {}), although `status` calls that exact
  situation "NEVER SCANNED ... do not delete on the strength of the plan
  alone" and references/deprecation.md promises retire "refuses outright
  unless you pass --force".
- SYS-4: build_docs.py's `--check` linted var()/`.class` references in fenced
  css blocks inside prose *.md but never inside a components/<name>.example.html
  override (the documented mechanism for replacing generated example markup),
  so a broken override was never caught.
- FIGMA-1: figma_to_tokens.py's parse_records (the "records" input shape)
  never merged rows sharing (collection, name) across modes into one
  variable the way parse_plugin's _ingest does, so --format css emitted the
  token twice under :root and produced no [data-theme="dark"] block.
- FIGMA-3: figma_to_tokens.py listed font-sans/font-mono in COMPOSITE_ONLY,
  so --reverse dropped these plain STRING tokens as unsupported composites
  and exited 1, contradicting figma-mapping.md's own STRING mapping table.
- FIGMA-4: figma_audit.py's check_dark_mode only counted bg-*/fg-* slugs as
  semantic colour roles, so a single-mode collection holding only border-*
  roles never tripped MISSING_DARK_MODE, although token-contract.md lists
  border-* as its own Tier-2 colour role group alongside bg-*/fg-*.
- GATE-6: lint_email.py's check_head used a stricter, second definition of
  "preheader" (display:none AND max-height:0) than is_preheader() (accepts
  max-height:0 OR opacity:0, which check_css already relies on to exempt the
  preheader's hiding declarations) -- so a preheader hidden with
  display:none;opacity:0 was silently exempted in check_css but reported as
  entirely missing by check_head: a false "no preheader found" error.
"""
from __future__ import annotations

import json
import re
import unittest

from wds_support import TempDirTest, output, run_py


# ---------------------------------------------------------------------------
# SYS-1 -- extract_system.py: rel() and the two prose-gap emitters
# ---------------------------------------------------------------------------

class ExtractSystemPathsAreRelativeAndPosix(TempDirTest):

    def build_system(self):
        self.write("src/tokens.css", ":root {\n  --bg-accent: #3355ff;\n}\n")
        self.write("src/components/button.css",
                   ".button {\n  --button-bg: var(--bg-accent);\n"
                   "  background: var(--button-bg);\n}\n"
                   ".button__icon {\n  width: 1rem;\n}\n")
        # A doc for a component that does not exist -> orphan-doc.
        # "button" itself has no doc -> undocumented-component.
        self.write("docs/prose/components/tooltip.md", "# Tooltip\n\nWhy it exists.\n")
        out = self.tmp / "system.json"
        proc = run_py("design-system-docs", "extract_system", "src",
                      "--root", str(self.tmp), "--prose", str(self.tmp / "docs" / "prose"),
                      "--out", str(out), cwd=self.tmp)
        self.assertEqual(proc.returncode, 0, output(proc))
        return out, json.loads(out.read_text(encoding="utf-8"))

    def test_gap_where_and_file_fields_are_relative_posix_paths(self):
        _, data = self.build_system()
        kinds = {g["kind"] for g in data["gaps"]}
        self.assertIn("undocumented-component", kinds, data["gaps"])
        self.assertIn("orphan-doc", kinds, data["gaps"])

        def path_like_values(obj):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if key in ("file", "where") and isinstance(value, str):
                        yield value
                    else:
                        yield from path_like_values(value)
            elif isinstance(obj, list):
                for item in obj:
                    yield from path_like_values(item)

        values = list(path_like_values(data))
        self.assertTrue(values, data)
        for value in values:
            with self.subTest(value=value):
                self.assertNotIn("\\", value)
                self.assertFalse(value.startswith("/"), value)
                self.assertNotRegex(value, r"^[A-Za-z]:", value)

    def test_build_docs_and_diff_system_still_accept_the_output(self):
        out, _ = self.build_system()
        site = self.tmp / "site"
        proc = run_py("design-system-docs", "build_docs", str(out), "--out", str(site),
                      cwd=self.tmp)
        self.assertEqual(proc.returncode, 0, output(proc))
        self.assertTrue((site / "components.html").is_file(), output(proc))

        proc = run_py("design-system-versioning", "diff_system", str(out), str(out),
                      "--format", "json", cwd=self.tmp)
        self.assertNotIn("Traceback", output(proc), output(proc))
        self.assertIn(proc.returncode, (0, 1), output(proc))


# ---------------------------------------------------------------------------
# SYS-2 -- deprecate.py: cmd_retire must refuse an unscanned deprecation
# ---------------------------------------------------------------------------

class DeprecateRetireRefusesWithoutAScan(TempDirTest):

    def add_entry(self, ledger):
        return run_py("design-system-versioning", "deprecate", "--ledger", str(ledger),
                      "add", "--name=--fg-subtle", "--kind", "token",
                      "--since", "2.1.0", "--removal", "3.0.0",
                      "--replacement=--fg-faint", "--reason", "x", cwd=self.tmp)

    def retire(self, ledger, *extra):
        return run_py("design-system-versioning", "deprecate", "--ledger", str(ledger),
                      "retire", "--name=--fg-subtle", *extra, cwd=self.tmp)

    def test_retire_without_a_scan_is_refused(self):
        ledger = self.tmp / "dep.json"
        self.assertEqual(self.add_entry(ledger).returncode, 0)

        proc = self.retire(ledger)
        self.assertEqual(proc.returncode, 1, output(proc))
        entry = json.loads(ledger.read_text(encoding="utf-8"))["deprecations"][0]
        self.assertEqual(entry["status"], "active", output(proc))

    def test_retire_with_force_needs_no_scan(self):
        ledger = self.tmp / "dep.json"
        self.assertEqual(self.add_entry(ledger).returncode, 0)

        proc = self.retire(ledger, "--force")
        self.assertEqual(proc.returncode, 0, output(proc))
        entry = json.loads(ledger.read_text(encoding="utf-8"))["deprecations"][0]
        self.assertEqual(entry["status"], "removed", output(proc))

    def test_retire_after_a_zero_hit_scan_is_allowed(self):
        ledger = self.tmp / "dep.json"
        self.assertEqual(self.add_entry(ledger).returncode, 0)
        consumers = self.tmp / "consumers"
        consumers.mkdir()

        scan = run_py("design-system-versioning", "deprecate", "--ledger", str(ledger),
                      "scan", str(consumers), "--record", cwd=self.tmp)
        self.assertEqual(scan.returncode, 0, output(scan))

        proc = self.retire(ledger)
        self.assertEqual(proc.returncode, 0, output(proc))


# ---------------------------------------------------------------------------
# SYS-4 -- build_docs.py: --check must lint *.example.html overrides too
# ---------------------------------------------------------------------------

class BuildDocsChecksExampleHtmlOverrides(TempDirTest):

    def build_system_json(self):
        self.write("src/tokens.css", ":root {\n  --bg-accent: #3355ff;\n}\n")
        self.write("src/components/button.css",
                   ".button {\n  --button-bg: var(--bg-accent);\n"
                   "  background: var(--button-bg);\n}\n"
                   ".button__icon {\n  width: 1rem;\n}\n")
        out = self.tmp / "system.json"
        proc = run_py("design-system-docs", "extract_system", "src", "--out", str(out),
                      cwd=self.tmp)
        self.assertEqual(proc.returncode, 0, output(proc))
        return out

    def check(self, system):
        return run_py("design-system-docs", "build_docs", str(system),
                      "--prose", "docs/prose", "--check", cwd=self.tmp)

    def test_bad_var_and_class_in_an_override_are_reported(self):
        system = self.build_system_json()
        self.write("docs/prose/components/button.example.html",
                   '<button class="button" {attrs} '
                   'style="color: var(--this-token-does-not-exist)">'
                   '<span class="button__nonexistent-part">{content}</span></button>')
        proc = self.check(system)
        out = output(proc)
        self.assertEqual(proc.returncode, 1, out)
        self.assertIn("--this-token-does-not-exist", out)
        self.assertIn("button__nonexistent-part", out)

    def test_a_correct_override_has_no_finding(self):
        system = self.build_system_json()
        self.write("docs/prose/components/button.example.html",
                   '<button class="button" {attrs} style="color: var(--bg-accent)">'
                   '<span class="button__icon">{content}</span></button>')
        proc = self.check(system)
        out = output(proc)
        self.assertEqual(proc.returncode, 0, out)
        self.assertIn("No drift", out)


# ---------------------------------------------------------------------------
# FIGMA-1 -- figma_to_tokens.py: parse_records must merge across modes
# ---------------------------------------------------------------------------

BLOCK_RE = re.compile(r'(:root|\[data-theme="[^"]+"\])\s*\{([^}]*)\}')
BG_SURFACE_RE = re.compile(r"--bg-surface:\s*([^;]+);")


def bg_surface_by_selector(css_text: str) -> dict[str, str]:
    out = {}
    for sel, body in BLOCK_RE.findall(css_text):
        m = BG_SURFACE_RE.search(body)
        if m:
            out[sel] = m.group(1).strip()
    return out


class FigmaToTokensRecordsMergeAcrossModes(TempDirTest):

    def test_records_shape_merges_like_plugin_shape_does(self):
        records = self.write("records.json", json.dumps([
            {"name": "bg-surface", "type": "COLOR", "value": "#ffffff",
             "collection": "semantic", "mode": "Light"},
            {"name": "bg-surface", "type": "COLOR", "value": "#111111",
             "collection": "semantic", "mode": "Dark"},
        ]))
        plugin = self.write("plugin.json", json.dumps({
            "collections": [{
                "name": "semantic",
                "modes": [
                    {"name": "Light", "variables": [
                        {"name": "bg-surface", "type": "COLOR", "value": "#ffffff"}]},
                    {"name": "Dark", "variables": [
                        {"name": "bg-surface", "type": "COLOR", "value": "#111111"}]},
                ],
            }],
        }))

        records_proc = run_py("figma-variables-sync", "figma_to_tokens", str(records),
                              "--format", "css", cwd=self.tmp)
        plugin_proc = run_py("figma-variables-sync", "figma_to_tokens", str(plugin),
                             "--format", "css", cwd=self.tmp)
        self.assertEqual(records_proc.returncode, 0, output(records_proc))
        self.assertEqual(plugin_proc.returncode, 0, output(plugin_proc))

        records_css = records_proc.stdout.decode("utf-8")
        plugin_css = plugin_proc.stdout.decode("utf-8")

        # No duplicate declaration under :root, and a real [data-theme="dark"] block.
        self.assertEqual(records_css.count("--bg-surface:"), 2, records_css)

        records_values = bg_surface_by_selector(records_css)
        plugin_values = bg_surface_by_selector(plugin_css)
        self.assertEqual(set(records_values), {":root", '[data-theme="dark"]'}, records_css)
        self.assertEqual(records_values, plugin_values)


# ---------------------------------------------------------------------------
# FIGMA-3 -- figma_to_tokens.py: font-sans/font-mono are not composites
# ---------------------------------------------------------------------------

class FigmaToTokensReverseKeepsFontStackStrings(TempDirTest):

    def test_reverse_keeps_font_sans_from_the_scripts_own_json(self):
        records = self.write("records.json", json.dumps([
            {"name": "font-sans", "type": "STRING", "value": "-apple-system, sans-serif"},
        ]))
        forward = run_py("figma-variables-sync", "figma_to_tokens", str(records),
                         "--format", "json", cwd=self.tmp)
        self.assertEqual(forward.returncode, 0, output(forward))
        tokens_json = self.write("tokens.json", forward.stdout.decode("utf-8"))
        self.assertIn('"font-sans"', tokens_json.read_text(encoding="utf-8"))

        reverse = run_py("figma-variables-sync", "figma_to_tokens", str(tokens_json),
                         "--reverse", cwd=self.tmp)
        out = output(reverse)
        self.assertEqual(reverse.returncode, 0, out)
        self.assertNotIn("composite", out)
        payload = json.loads(reverse.stdout.decode("utf-8"))
        names = {v.get("name") for v in payload.get("variables", [])}
        self.assertIn("font/sans", names, out)


# ---------------------------------------------------------------------------
# FIGMA-4 -- figma_audit.py: check_dark_mode must count border-* roles too
# ---------------------------------------------------------------------------

class FigmaAuditDarkModeCountsBorderRoles(TempDirTest):

    def test_a_single_mode_border_only_collection_trips_missing_dark_mode(self):
        records = self.write("records.json", json.dumps([
            {"name": "border-subtle", "type": "COLOR", "value": "#eeeeee",
             "collection": "semantic"},
            {"name": "border-default", "type": "COLOR", "value": "#cccccc",
             "collection": "semantic"},
            {"name": "border-strong", "type": "COLOR", "value": "#999999",
             "collection": "semantic"},
            {"name": "border-accent", "type": "COLOR", "value": "#3355ff",
             "collection": "semantic"},
            {"name": "border-focus", "type": "COLOR", "value": "#3355ff",
             "collection": "semantic"},
        ]))
        proc = run_py("figma-variables-sync", "figma_audit", str(records),
                      "--format", "json", cwd=self.tmp)
        data = json.loads(proc.stdout.decode("utf-8"))
        codes = {f["code"] for f in data["findings"]}
        self.assertIn("MISSING_DARK_MODE", codes, data["findings"])


# ---------------------------------------------------------------------------
# GATE-6 -- lint_email.py: one definition of "preheader", not two
# ---------------------------------------------------------------------------

HEAD_BOILERPLATE = (
    '<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, '
    'initial-scale=1">\n<title>Your order has shipped</title>\n'
)
BODY_TABLE = '<table role="presentation"><tr><td>Hello there.</td></tr></table>\n'


class LintEmailPreheaderDetectionIsConsistent(TempDirTest):

    def lint(self, body):
        html = self.write("email.html",
                          f"<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n{HEAD_BOILERPLATE}"
                          f"</head>\n<body>\n{body}\n{BODY_TABLE}</body>\n</html>\n")
        proc = run_py("email-template-system", "lint_email", str(html), "--format", "json",
                      cwd=self.tmp)
        self.assertIn(proc.returncode, (0, 1), output(proc))  # never 2 (bad invocation/crash)
        data = json.loads(proc.stdout.decode("utf-8"))
        return data["files"][str(html)]["findings"]

    def test_a_preheader_hidden_with_opacity_zero_is_not_reported_missing(self):
        findings = self.lint(
            '<div style="display:none;opacity:0;font-size:1px;line-height:1px;'
            'overflow:hidden;mso-hide:all;">Order 41822 has shipped and will arrive '
            'Thursday, right on schedule for you</div>')
        missing = [f for f in findings if f["check"] == "head"
                  and "no preheader found" in f["message"]]
        self.assertEqual(missing, [], findings)

    def test_a_document_with_no_preheader_at_all_is_still_flagged(self):
        findings = self.lint("")
        missing = [f for f in findings if f["check"] == "head"
                  and "no preheader found" in f["message"]]
        self.assertEqual(len(missing), 1, findings)


if __name__ == "__main__":
    unittest.main()
