"""The email templates, their build and their lint (P18).

- DL-A10: the dark block's `a { color: … !important }` beat the button's
  inline label colour (2.56:1 on the accent fill), and the announcement's
  eyebrow kept its light accent on the dark surface (2.50:1).
- DL-B6, DL-C3: lint_email measured contrast with the dark rules never
  applied, so it reported none of that. It has a dark pass now.
- DL-A11: the docs promised an [if mso] font rule that the build never added.
- DL-A12: the receipt's container was 600px wide inline, so with <style>
  stripped it overflowed a phone.
- DL-A20: any comment holding `{{` was kept as an ESP directive, so the
  receipt's authoring notes went out in every build.
"""
from __future__ import annotations

import json
import re

from wds_support import SKILLS, TempDirTest, output, run_py

EMAIL = SKILLS / "email-template-system"
TEMPLATES = sorted((EMAIL / "assets" / "templates").glob("*.html"))

HEAD = ('<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        '<title>t</title>\n{head}</head>\n<body>\n'
        '<div data-preheader="1" style="display:none;max-height:0;overflow:hidden;">'
        'Your order has shipped and arrives on Thursday this week</div>\n'
        '<table role="presentation" width="100%"><tr><td>{body}</td></tr></table>\n'
        '</body>\n</html>\n')


class EmailTest(TempDirTest):

    def build(self, source, *args):
        out = self.tmp / ("built-" + source.name)
        proc = run_py("email-template-system", "build_email", source, "-o", out, *args,
                      cwd=self.tmp)
        self.assertEqual(proc.returncode, 0, output(proc))
        return out, output(proc)

    def lint(self, path):
        proc = run_py("email-template-system", "lint_email", path, "--format", "json",
                      cwd=self.tmp)
        self.assertIn(proc.returncode, (0, 1), output(proc))
        return json.loads(proc.stdout.decode("utf-8"))["files"][str(path)]["findings"]

    def page(self, name, body, head=""):
        return self.write(name, HEAD.format(head=head, body=body))


class TemplatesInDarkMode(EmailTest):
    """DL-A10."""

    def test_every_template_builds_and_lints_clean(self):
        for template in TEMPLATES:
            with self.subTest(template=template.name):
                out, _ = self.build(template)
                errors = [f for f in self.lint(out) if f["severity"] != "info"]
                self.assertEqual(errors, [], template.name)

    def test_every_filled_link_is_a_button_the_dark_block_repoints(self):
        for template in TEMPLATES:
            with self.subTest(template=template.name):
                html = self.build(template)[0].read_text(encoding="utf-8")
                links = re.findall(r"<a\b[^>]*>", html)
                filled = [a for a in links if "background-color:" in a]
                for a in filled:
                    self.assertRegex(a, r'class="[^"]*\bbutton\b', "a filled link with no class")
                dark = re.search(r"@media \(prefers-color-scheme: dark\)\s*\{(.*?)\}\s*\}",
                                 html, re.S)
                self.assertIsNotNone(dark, template.name)
                if filled:
                    self.assertRegex(dark.group(1).replace(" ", ""),
                                     r"\.button\{color:#ffffff!important")

    def test_the_eyebrow_is_repointed(self):
        html = self.build(EMAIL / "assets" / "templates" / "product-announcement.html")[0]
        self.assertRegex(html.read_text(encoding="utf-8").replace(" ", ""),
                         r"\.label\{color:#ffa582!important")


class LintHasADarkPass(EmailTest):
    """DL-B6, DL-C3: the retained dark rules applied by build_email's own
    matcher, and the contrast measured again."""

    DARK = ("<style>@media (prefers-color-scheme: dark) {{ "
            ".wrap {{ background-color: #171512 !important; }} "
            "a {{ color: #ffa582 !important; }} {extra}}}</style>\n")
    BUTTON = ('<div class="wrap" style="background-color:#ffffff;">'
              '<a class="button" href="https://example.com/o" style="display:inline-block;'
              'background-color:#c64600;color:#ffffff;">View your order</a></div>')

    def dark_findings(self, extra="", body=None):
        page = self.page("dark.html", body or self.BUTTON, self.DARK.format(extra=extra))
        return [f for f in self.lint(page) if f["check"] == "dark"]

    def test_an_element_rule_that_beats_the_inline_label_is_an_error(self):
        found = self.dark_findings()
        self.assertEqual(len(found), 1, found)
        self.assertEqual(found[0]["severity"], "error")
        self.assertIn("#ffa582 on #c64600 is 2.56:1", found[0]["message"])

    def test_a_class_rule_after_it_wins_back_the_label(self):
        self.assertEqual(self.dark_findings(".button { color: #ffffff !important; } "), [])

    def test_text_left_light_on_a_dark_background_is_an_error(self):
        body = ('<div class="wrap" style="background-color:#ffffff;">'
                '<p style="color:#9b3400;">Back in stock</p></div>')
        found = self.dark_findings(body=body)
        self.assertEqual(len(found), 1, found)
        self.assertIn("#9b3400 on #171512 is 2.50:1", found[0]["message"])

    def test_what_the_dark_rules_leave_alone_is_the_light_pass_s(self):
        """A pair no dark rule touches is reported once, by `contrast`."""
        body = '<p style="background-color:#ffffff;color:#aaaaaa;">Pale on white</p>'
        findings = self.lint(self.page("pale.html", body, self.DARK.format(extra="")))
        self.assertEqual([f["check"] for f in findings if f["check"] in ("contrast", "dark")
                          and f["severity"] == "error"], ["contrast"])

    def test_no_dark_block_no_dark_findings(self):
        page = self.page("light.html", self.BUTTON)
        self.assertEqual([f for f in self.lint(page) if f["check"] == "dark"], [])


class OutlookFontRule(EmailTest):
    """DL-A11."""

    FONT = re.compile(r"<!--\[if mso\]>(?:(?!<!\[endif\]-->).)*font-family: Arial", re.S)

    def test_the_build_adds_the_font_rule(self):
        for template in TEMPLATES:
            with self.subTest(template=template.name):
                out, log = self.build(template)
                html = out.read_text(encoding="utf-8")
                self.assertRegex(html, self.FONT)
                self.assertEqual(html.count("PixelsPerInch>96<"), 1)
                self.assertIn("font rule", log)

    def test_a_hand_written_dpi_block_gets_the_font_rule_once(self):
        dpi = ("<!--[if mso]><noscript><xml><o:OfficeDocumentSettings><o:PixelsPerInch>96"
               "</o:PixelsPerInch></o:OfficeDocumentSettings></xml></noscript><![endif]-->\n")
        source = self.page("dpi.html", "<p>Hi</p>", dpi)
        html = self.build(source)[0].read_text(encoding="utf-8")
        self.assertEqual(html.count("PixelsPerInch>96<"), 1)
        self.assertEqual(len(self.FONT.findall(html)), 1)
        again = self.build(self.build(source)[0])[0].read_text(encoding="utf-8")
        self.assertEqual(len(self.FONT.findall(again)), 1, "a rebuild adds a second one")

    def test_the_lint_asks_for_it_when_a_stack_starts_with_a_font_windows_lacks(self):
        def head_warnings(stack, name):
            page = self.page(name, f'<p style="font-family:{stack};color:#222222;">Hi</p>')
            return [f["message"] for f in self.lint(page) if "MSO font rule" in f["message"]]
        self.assertEqual(len(head_warnings("-apple-system, Arial, sans-serif", "a.html")), 1)
        self.assertEqual(head_warnings("Arial, Helvetica, sans-serif", "b.html"), [])
        self.assertEqual(head_warnings("'Segoe UI', Arial, sans-serif", "c.html"), [])


class ContainersAreFluid(EmailTest):
    """DL-A12: without <style>, the container's inline width is all there is."""

    def test_every_container_is_100_percent_with_a_600px_cap(self):
        for template in TEMPLATES:
            with self.subTest(template=template.name):
                html = self.build(template)[0].read_text(encoding="utf-8")
                tag = re.search(r'<table\b[^>]*class="container"[^>]*>', html).group(0)
                style = re.search(r'style="([^"]*)"', tag).group(1).replace(" ", "")
                self.assertRegex(style, r"(^|;)width:100%")
                self.assertRegex(style, r"max-width:600px")


class AuthoringCommentsAreDropped(EmailTest):
    """DL-A20."""

    def test_the_receipt_ships_without_its_authoring_notes(self):
        out, log = self.build(EMAIL / "assets" / "templates" / "transactional-receipt.html")
        html = out.read_text(encoding="utf-8")
        self.assertNotIn("SOURCE TEMPLATE", html)
        self.assertNotIn("Compile before sending", html)
        self.assertIn("<!--[if mso]>", html)
        self.assertIn("<!--[if !mso]><!-- -->", html)

    def test_esp_directives_stay_and_a_note_that_mentions_a_merge_tag_goes(self):
        kept = ["{{#if vip}}", "{{/if}}", "{{else}}", "{{^ items}}", "*|IF:FNAME|*",
                "{% if order %}", "<% if x %>"]
        body = "".join(f"<!-- {d} -->" for d in kept)
        body += "<!-- note: write the name as {{first_name}} --><p>Hi</p>"
        html = self.build(self.page("esp.html", body))[0].read_text(encoding="utf-8")
        for directive in kept:
            self.assertIn(directive, html)
        self.assertNotIn("note: write the name", html)
