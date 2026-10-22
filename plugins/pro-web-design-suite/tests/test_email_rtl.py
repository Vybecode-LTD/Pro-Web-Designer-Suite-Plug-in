"""Right-to-left email, and a label a translation lengthens (DL-B5, P41 part 2).

Regressions covered: the skill had one line on direction (`dir="ltr"`, email-
architecture.md §2). Nothing showed a right-to-left email, and the linter
passed an Arabic email laid out left to right, a ghost table that runs its
columns left to right, and a VML button whose German label could not fit the
literal width VML gives it.
"""
from __future__ import annotations

import json
import subprocess
import unittest

from wds_support import NODE, SKILLS, TempDirTest, env, output, run_py, tool_modules

EMAIL = SKILLS / "email-template-system"
RTL = EMAIL / "assets" / "templates" / "product-announcement-rtl.html"
LTR = EMAIL / "assets" / "templates" / "product-announcement.html"
MODULES = tool_modules("WDS_NODE_MODULES", "playwright", node_path=True)
PAGE = ('<!doctype html><html lang="{lang}"{dir}><head><meta charset="utf-8"><title>t</title></head>'
        '<body>{body}</body></html>')
BUTTON = ('<!--[if mso]><v:roundrect xmlns:v="urn:schemas-microsoft-com:vml" href="https://example.com/a" '
          'style="height:48px;v-text-anchor:middle;width:{width}px;" arcsize="25%" stroke="f" fillcolor="#2b5d8a">'
          '<center style="color:#ffffff;font-family:Arial,sans-serif;font-size:16px;font-weight:bold;">{label}'
          '</center></v:roundrect><![endif]-->')
# Where each .col div lands, in a browser that lays the built email out.
PROBE = r"""
const fs = require('fs');
const { chromium } = require('playwright');
(async () => {
  let browser;
  try { browser = await chromium.launch(); }
  catch (e) {
    try { browser = await chromium.launch({ channel: 'chrome' }); }
    catch (e2) { console.error('no usable chromium'); process.exit(2); }
  }
  const out = {};
  for (const file of process.argv.slice(2)) {
    const page = await browser.newPage({ viewport: { width: 640, height: 900 }, javaScriptEnabled: false });
    await page.setContent(fs.readFileSync(file, 'utf8'));
    out[file] = await page.$$eval('.col', cols => cols.map(c => c.getBoundingClientRect().left));
    await page.close();
  }
  await browser.close();
  console.log(JSON.stringify(out));
})();
"""


class Lint(TempDirTest):

    def findings(self, html: str, *args: str) -> list[dict]:
        page = self.write("mail.html", html)
        proc = run_py("email-template-system", "lint_email", page, "--format", "json", *args, cwd=self.tmp)
        self.assertIn(proc.returncode, (0, 1), output(proc))
        return json.loads(proc.stdout.decode("utf-8"))["files"][str(page)]["findings"]

    def of(self, html: str, check: str) -> list[dict]:
        return [f for f in self.findings(html) if f["check"] == check]

    def build(self, source) -> str:
        out = self.tmp / "built.html"
        proc = run_py("email-template-system", "build_email", source, "--out", out, cwd=self.tmp)
        self.assertEqual(0, proc.returncode, output(proc))
        return out.read_bytes().decode("utf-8")


class Direction(Lint):

    TABLE = '<table role="presentation"{dir}><tr><td>{cell}</td></tr></table>'

    def page(self, lang="ar", html_dir=' dir="rtl"', table_dir=' dir="rtl"', cell="مرحبا"):
        return PAGE.format(lang=lang, dir=html_dir, body=self.TABLE.format(dir=table_dir, cell=cell))

    def test_the_template_is_clean_and_keeps_its_direction_when_built(self):
        built = self.build(RTL)
        self.assertEqual([], [f for f in self.findings(built) if f["check"] in ("direction", "vml")])
        self.assertIn('<html lang="ar" dir="rtl"', built)
        tables = built.count("<table")
        self.assertGreaterEqual(tables, 4)                    # two in the page, two ghost tables
        self.assertEqual(tables, built.count('<table role="presentation" class="wrap" dir="rtl"')
                         + built.count('<table role="presentation" dir="rtl"')
                         + built.count('<table role="presentation" class="container" dir="rtl"'))

    def test_a_right_to_left_language_needs_dir(self):
        found = self.of(self.page(html_dir="", table_dir=""), "direction")
        self.assertEqual(["error", "error"], [f["severity"] for f in found], found)
        self.assertIn('lang="ar"> is written right to left', found[0]["message"])
        self.assertIn("outer <table>", found[1]["message"])
        for lang in ("he", "fa-IR", "ur", "ku-Arab", "yi"):
            with self.subTest(lang=lang):
                self.assertTrue(self.of(self.page(lang=lang, html_dir="", table_dir=""), "direction"))
        for lang in ("en", "az-Latn", "de"):                   # left to right, with no dir anywhere
            with self.subTest(lang=lang):
                self.assertEqual([], self.of(self.page(lang=lang, html_dir="", table_dir=""), "direction"))

    def test_the_outer_table_carries_it_since_body_may_not_survive(self):
        found = self.of(self.page(table_dir=""), "direction")
        self.assertEqual(1, len(found), found)
        self.assertIn("caniemail.com, tested 2021-11-30", found[0]["detail"])     # html-body's row
        self.assertEqual([], self.of(self.page(table_dir=' style="direction:rtl"'), "direction"))
        nested = PAGE.format(lang="ar", dir=' dir="rtl"', body='<table role="presentation" dir="rtl"><tr><td>'
                             + self.TABLE.format(dir="", cell="مرحبا") + "</td></tr></table>")
        self.assertEqual([], self.of(nested, "direction"))           # an inner table inherits

    def test_a_ghost_table_carries_it_too(self):
        ghost = ('<!--[if mso]><table role="presentation" style="width:600px;"><tr><td><![endif]-->'
                 '<p>مرحبا</p><!--[if mso]></td></tr></table><![endif]-->')
        found = self.of(self.page(cell=ghost), "direction")
        self.assertEqual(["warning"], [f["severity"] for f in found], found)
        self.assertIn("ghost table", found[0]["message"])
        fixed = ghost.replace('<table role="presentation"', '<table role="presentation" dir="rtl"')
        self.assertEqual([], self.of(self.page(cell=fixed), "direction"))
        self.assertEqual([], self.of(self.page(lang="en", html_dir="", table_dir="", cell=ghost), "direction"))

    def test_a_left_alignment_is_mirrored(self):
        for cell in ('<p align="left">مرحبا</p>', '<p style="text-align:left">مرحبا</p>'):
            with self.subTest(cell=cell):
                found = self.of(self.page(cell=cell), "direction")
                self.assertEqual(1, len(found), found)
                self.assertIn("left alignment", found[0]["message"])
        self.assertEqual([], self.of(self.page(cell='<p style="text-align:right">مرحبا</p>'), "direction"))
        self.assertEqual([], self.of(self.page(lang="en", html_dir="", table_dir="",
                                               cell='<p align="left">Hello</p>'), "direction"))

    def test_a_language_without_its_script_subtag_is_read_by_cldr(self):
        # Codex on #196: nqo (N'Ko) and rhg (Hanifi Rohingya) omit their script.
        for lang in ("nqo", "rhg", "ckb", "ar-EG", "pa-PK", "uz-AF"):
            with self.subTest(lang=lang):
                found = self.of(self.page(lang=lang, html_dir="", table_dir=""), "direction")
                self.assertIn("is written right to left", found[0]["message"] if found else "", found)
        for lang in ("pa", "uz", "sd-IN", "ug-KZ", "sd-Deva"):    # left to right there
            with self.subTest(lang=lang):
                self.assertEqual([], self.of(self.page(lang=lang, html_dir="", table_dir=""), "direction"))

    def test_every_word_engine_condition_holds_a_ghost_table(self):
        # Codex on #196: [if gte mso 9] and [if (gte mso 9)|(IE)] are the Word engine's too.
        for condition in ("gte mso 9", "(gte mso 9)|(IE)", "mso | IE"):
            ghost = ('<!--[if %s]><table role="presentation" style="width:600px;"><tr><td><![endif]-->'
                     '<p>مرحبا</p><!--[if %s]></td></tr></table><![endif]-->' % (condition, condition))
            with self.subTest(condition=condition):
                found = self.of(self.page(cell=ghost), "direction")
                self.assertEqual(["ghost table"], [f["message"].split(" in ")[0][2:] for f in found], found)
        branch = '<!--[if !mso]><!-- --><table role="presentation"><tr><td>x</td></tr></table><!--<![endif]-->'
        self.assertEqual([], self.of(self.page(cell=branch.replace("<table", '<table dir="rtl"')), "direction"))

    def test_a_versioned_condition_carries_the_font_rule(self):
        # The same match decides whether the head has the Word engine's font rule.
        head = ('<!--[if gte mso 9]><style>table, td, div, p, a { font-family: Arial, sans-serif !important; }'
                '</style><![endif]-->')
        page = ('<!doctype html><html lang="en"><head><meta charset="utf-8"><title>t</title>%s</head><body>'
                '<p style="font-family:Inter, Arial, sans-serif">Hi</p></body></html>')
        rule = [f for f in self.findings(page % head) if "no MSO font rule" in f["message"]]
        self.assertEqual([], rule)
        self.assertTrue([f for f in self.findings(page % "") if "no MSO font rule" in f["message"]])

    def test_dir_on_a_left_to_right_language_is_a_warning(self):
        found = self.of(self.page(lang="en", cell="Hello"), "direction")
        self.assertEqual(["warning"], [f["severity"] for f in found], found)


class LabelWidth(Lint):

    def page(self, label: str, width: int) -> str:
        return PAGE.format(lang="de", dir="", body='<table role="presentation"><tr><td>'
                           + BUTTON.format(width=width, label=label) + "</td></tr></table>")

    def test_a_translated_label_that_outgrows_its_shape_is_flagged(self):
        found = self.of(self.page("Jetzt die Ridgeline kaufen", 216), "vml")
        self.assertEqual(1, len(found), found)
        self.assertEqual("warning", found[0]["severity"])
        self.assertIn("26 characters at 16px: about 282px", found[0]["detail"])
        self.assertEqual([], self.of(self.page("Jetzt die Ridgeline kaufen", 296), "vml"))
        self.assertEqual([], self.of(self.page("Shop the Ridgeline", 216), "vml"))

    def test_an_entity_counts_as_one_character(self):
        self.assertEqual([], self.of(self.page("Tea &amp; cakes for all", 216), "vml"))     # 19 characters, not 23

    def test_the_shipped_templates_fit(self):
        for template in sorted((EMAIL / "assets" / "templates").glob("*.html")):
            with self.subTest(template=template.name):
                self.assertEqual([], [f for f in self.findings(self.build(template)) if f["check"] == "vml"])


@unittest.skipUnless(NODE and MODULES, "needs node plus WDS_NODE_MODULES pointing at playwright")
class TheColumnsFlip(Lint):
    """§11's claim, in a browser: dir="rtl" on the container runs the
    fluid-hybrid columns right to left, with the source in reading order."""

    def test_the_first_column_is_on_the_right(self):
        built = {}
        for name, source in (("ltr", LTR), ("rtl", RTL)):
            path = self.tmp / f"{name}.html"
            path.write_bytes(self.build(source).encode("utf-8"))
            built[name] = str(path)
        probe = self.write("probe.cjs", PROBE)
        proc = subprocess.run([NODE, str(probe), built["ltr"], built["rtl"]], cwd=self.tmp, capture_output=True,
                              env=env(NODE_PATH=MODULES), timeout=180)
        if proc.returncode == 2 and b"no usable chromium" in proc.stderr:
            self.skipTest("no usable chromium")
        self.assertEqual(0, proc.returncode, output(proc))
        lefts = json.loads(proc.stdout)
        ltr, rtl = lefts[built["ltr"]], lefts[built["rtl"]]
        self.assertEqual(2, len(ltr))
        self.assertEqual(2, len(rtl))
        self.assertLess(ltr[0], ltr[1])            # left to right: the first column on the left
        self.assertGreater(rtl[0], rtl[1])         # right to left: the first on the right


if __name__ == "__main__":
    unittest.main()
