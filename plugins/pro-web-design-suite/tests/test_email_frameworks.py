"""MJML and React Email from the email tokens (DL-B4, P41 part 3).

Regressions covered: the router sent "MJML" to email-template-system, which
said nothing about it, and nothing reached React Email. `export_email_theme.py`
writes the tokens as an MJML head to `mj-include` or a React Email theme
module, each with the dark-mode and phone rules the skill's own templates carry.
Each starter is compiled by the real tool (MJML 5.4, React Email 6.11 through
TypeScript's transpiler) and the HTML passes `lint_email.py --strict`; a
browser reads the dark and phone rules on the compiled markup.

Compiling MJML's output found two false positives in the linter, fixed here:
a hidden preheader's colour was measured (MJML's is white), and a
`font-size:0` wrapper round inline-block columns was read as 0px text.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import unittest
import xml.etree.ElementTree as ET

from wds_support import NODE, SKILLS, TempDirTest, env, load_script, output, run_py, tool_modules

EMAIL = SKILLS / "email-template-system"
TOKENS = EMAIL / "assets" / "email-tokens.json"
MJML_STARTER = EMAIL / "assets" / "templates" / "mjml" / "product-announcement.mjml"
REACT_STARTER = EMAIL / "assets" / "templates" / "react-email" / "product-announcement.tsx"
MJML_MODULES = tool_modules("WDS_NODE_MODULES", "mjml")
REACT_MODULES = tool_modules("WDS_NODE_MODULES", "typescript", "react", "react-dom", "react-email")
BROWSER_MODULES = tool_modules("WDS_NODE_MODULES", "playwright", node_path=True)

# Compile an .mjml file as the docs say: includes allowed, strict validation.
MJML_RUN = r"""
const fs = require('fs'); const path = require('path'); const mjml = require('mjml');
(async () => {
  const file = path.resolve(process.argv[2]);
  const options = { filePath: file, validationLevel: 'strict' };
  if (process.argv[4] !== 'default') options.ignoreIncludes = false;
  const result = await mjml(fs.readFileSync(file, 'utf8'), options);
  fs.writeFileSync(process.argv[3], result.html);
  console.log(JSON.stringify(result.errors));
})().catch((e) => { console.error(e.stack || e.message); process.exit(1); });
"""

# Transpile every .ts and .tsx in a folder as a bundler would, then render the
# template's default export with React Email and pass it through withMso.
REACT_RUN = r"""
const fs = require('fs'); const path = require('path'); const ts = require('typescript');
(async () => {
  const dir = path.resolve(process.argv[2]);
  for (const name of fs.readdirSync(dir).filter((f) => /\.tsx?$/.test(f))) {
    const out = ts.transpileModule(fs.readFileSync(path.join(dir, name), 'utf8'), {
      fileName: name, reportDiagnostics: true,
      compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX,
                         target: ts.ScriptTarget.ES2022, esModuleInterop: true } });
    if (out.diagnostics.length) {
      throw new Error(name + ': ' + out.diagnostics.map((d) => ts.flattenDiagnosticMessageText(d.messageText, '\n')).join('; '));
    }
    fs.writeFileSync(path.join(dir, name.replace(/\.tsx?$/, '.js')), out.outputText);
  }
  const React = require('react'); const { render } = require('react-email');
  const { withMso } = require(path.join(dir, 'theme.js'));
  const template = require(path.join(dir, process.argv[3]));
  const html = withMso(await render(React.createElement(template.default)));
  fs.writeFileSync(process.argv[4], html);
  console.log(JSON.stringify({ again: withMso(html) === html }));
})().catch((e) => { console.error(e.stack || e.message); process.exit(1); });
"""

# Each probe's computed text colour and the first opaque background behind
# it, in each scheme, and the h1's size on a phone and on a desktop.
PROBE = r"""
const fs = require('fs');
const { chromium } = require('playwright');
(async () => {
  let browser;
  try { browser = await chromium.launch(); }
  catch (e) {
    try { browser = await chromium.launch({ channel: 'chrome' }); }
    catch (e2) { console.error('no usable chromium'); process.exit(3); }
  }
  const probes = JSON.parse(process.argv[3]);
  const read = (probes) => Object.fromEntries(Object.entries(probes).map(([name, text]) => {
    const all = [...document.querySelectorAll('body *')].filter((el) => el.childNodes.length
      && [...el.childNodes].some((n) => n.nodeType === 3 && n.textContent.includes(text)));
    const el = all[all.length - 1];
    if (!el) return [name, null];
    let bg = null;
    for (let at = el; at && !bg; at = at.parentElement) {
      const c = getComputedStyle(at).backgroundColor;
      if (c !== 'rgba(0, 0, 0, 0)' && c !== 'transparent') bg = c;
    }
    const cs = getComputedStyle(el);
    return [name, { color: cs.color, bg, size: cs.fontSize, left: Math.round(el.getBoundingClientRect().left) }];
  }));
  const out = {};
  for (const [label, scheme, width] of [['light', 'light', 800], ['dark', 'dark', 800], ['phone', 'light', 375]]) {
    const context = await browser.newContext({ colorScheme: scheme, viewport: { width, height: 900 },
                                               javaScriptEnabled: false });
    const page = await context.newPage();
    await page.setContent(fs.readFileSync(process.argv[2], 'utf8'));
    out[label] = await page.evaluate(read, probes);
    await context.close();
  }
  await browser.close();
  console.log(JSON.stringify(out));
})();
"""
PROBES = {"h1": "The Ridgeline is back", "legal": "Northbeam Ltd, 12 Harbour Street",
          "button": "Shop the Ridgeline", "body": "Every seam, buckle and zip"}


def rgb(hex_colour: str) -> str:
    h = hex_colour.lstrip("#")
    return "rgb(%d, %d, %d)" % (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def px(value: str) -> int:
    return int(value.removesuffix("px")) if hasattr(value, "removesuffix") else int(value[:-2])


def tokens() -> dict[str, str]:
    """The skill's tokens, references resolved, as the build reads them."""
    return load_script("email-template-system", "build_email").load_tokens(TOKENS)


class Export(TempDirTest):

    def export(self, fmt: str, out: str, *args: str, code: int = 0) -> str:
        proc = run_py("email-template-system", "export_email_theme", "--format", fmt, "--out", out, *args,
                      cwd=self.tmp)
        self.assertEqual(code, proc.returncode, output(proc))
        self.log = output(proc)
        path = self.tmp / out
        return path.read_bytes().decode("utf-8") if code != 2 and path.exists() else ""

    def tokens_file(self, name: str = "email-tokens.json", **changes: str | None) -> str:
        data = json.loads(TOKENS.read_bytes())
        for key, value in changes.items():
            token = "--" + key.replace("_", "-")
            if value is None:
                del data["tokens"][token]
            else:
                data["tokens"][token] = {"value": value}
        self.write(name, json.dumps(data))
        return name

    def mjml(self, *args: str, code: int = 0) -> ET.Element:
        text = self.export("mjml", "theme.mjml", *args, code=code)
        return ET.fromstring(text)

    def json_export(self, text: str, name: str):
        m = re.search(r"^export const %s = (.*?)(?: as const)?;$" % name, text, re.S | re.M)
        self.assertIsNotNone(m, "no export %s" % name)
        return json.loads(m.group(1))


class TheMjmlHead(Export):

    def test_the_defaults_and_classes_read_the_token_roles(self):
        t = tokens()
        head = self.mjml().find("mj-head")
        attrs = head.find("mj-attributes")
        self.assertEqual(t["--font-sans"], attrs.find("mj-all").get("font-family"))
        button = attrs.find("mj-button")
        self.assertEqual((t["--bg-accent"], t["--fg-on-accent"], t["--email-button-pad"]),
                         (button.get("background-color"), button.get("color"), button.get("inner-padding")))
        self.assertEqual(t["--email-width"], attrs.find("mj-body").get("width"))
        classes = {c.get("name"): c for c in attrs.findall("mj-class")}
        h1 = classes["h1"]
        self.assertEqual((t["--type-h1-size"], t["--type-h1-line"], t["--type-h1-weight"], t["--fg-strong"]),
                         (h1.get("font-size"), h1.get("line-height"), h1.get("font-weight"), h1.get("color")))
        self.assertEqual("uppercase", classes["label"].get("text-transform"))
        self.assertEqual(t["--gap-grouped"], classes["gap-grouped"].get("height"))
        self.assertEqual(t["--email-bp-stack"], head.find("mj-breakpoint").get("width"))

    def test_a_gap_or_an_inset_keeps_the_sections_class(self):
        """MJML replaces a tag's css-class with an mj-class's, so a section
        given `mj-class="pad-card"` would lose `wds-surface` and its dark rule."""
        classes = {c.get("name"): c for c in self.mjml().iter("mj-class")}
        for name in ("gap-tight", "gap-section", "pad-card", "pad-well"):
            with self.subTest(name=name):
                self.assertIsNone(classes[name].get("css-class"))
        for name in ("h1", "muted", "sunken", "gutter"):
            with self.subTest(name=name):
                self.assertEqual("wds-" + name, classes[name].get("css-class"))
        section = self.mjml().find("mj-head/mj-attributes/mj-section")
        self.assertEqual("wds-surface wds-gutter", section.get("css-class"))

    def test_the_style_carries_dark_mode_and_the_phone_rules(self):
        t = tokens()
        style = self.export("mjml", "theme.mjml")
        dark = style.split("prefers-color-scheme: dark", 1)[1].split("@media only screen", 1)[0]
        self.assertIn(".wds-h1 div", dark)
        self.assertIn(t["--email-dark-fg"], dark)
        self.assertIn(".wds-button a { color: %s !important; }" % t["--fg-on-accent"], dark)
        phone = style.split("@media only screen and (max-width: 599px)", 1)[1]
        self.assertIn(".wds-h1 div { font-size: %s !important" % t["--email-h1-size-mobile"], phone)
        self.assertIn('<mj-style inline="inline">a { color: %s; }</mj-style>' % t["--fg-link"], style)
        self.assertIn("font-family: Arial, Helvetica, sans-serif !important;", style)

    def test_the_project_config_names_the_tokens_and_a_flag_beats_it(self):
        self.tokens_file("brand.json", bg_accent="#123456")
        self.write(".design-suite.json", json.dumps({"schema": 1, "emailTokens": "brand.json"}))
        self.assertEqual("#123456", self.mjml().find("mj-head/mj-attributes/mj-button").get("background-color"))
        flagged = self.mjml("--tokens", str(TOKENS)).find("mj-head/mj-attributes/mj-button")
        self.assertEqual(tokens()["--bg-accent"], flagged.get("background-color"))

    def test_a_role_the_tokens_lack_is_named_and_strict_fails(self):
        self.tokens_file(email_dark_link=None)
        text = self.export("mjml", "theme.mjml", "--tokens", "email-tokens.json")
        self.assertIn("email-dark-link", self.log)
        self.assertNotRegex(text.split("prefers-color-scheme", 1)[1], r"(?m)^\s*a \{")
        comment = text.split("-->", 1)[0][4:]
        self.assertIn("email-dark-link", comment)
        self.assertNotIn("--", comment, "an XML comment cannot hold --")
        self.export("mjml", "theme.mjml", "--tokens", "email-tokens.json", "--strict", code=1)

    def test_a_value_that_could_end_its_markup_is_refused(self):
        for value in ("red;background:url(x)", "#fff</mj-style>", "red} a {color:red", "#fff */"):
            with self.subTest(value=value):
                self.tokens_file(fg_link=value)
                self.export("mjml", "theme.mjml", "--tokens", "email-tokens.json", code=2)
                self.assertIn("--fg-link", self.log)

    def test_a_double_quote_in_a_stack_is_escaped(self):
        stack = '"Segoe UI", Arial, sans-serif'
        self.tokens_file(font_sans=stack)
        head = self.mjml("--tokens", "email-tokens.json")
        self.assertEqual(stack, head.find("mj-head/mj-attributes/mj-all").get("font-family"))

    def test_it_never_writes_over_its_tokens(self):
        self.tokens_file()
        self.export("mjml", "email-tokens.json", "--tokens", "email-tokens.json", code=2)
        self.assertIn("is the input", self.log)


class TheReactTheme(Export):

    def test_typescript_by_default_and_javascript_for_mjs(self):
        ts = self.export("react-email", "theme.ts")
        self.assertIn("} as const;", ts)
        self.assertIn("export function withMso(html: string): string {", ts)
        js = self.export("react-email", "theme.mjs")
        self.assertNotIn("as const", js)
        self.assertIn("export function withMso(html) {", js)

    def test_the_exports_read_the_token_roles(self):
        t = tokens()
        text = self.export("react-email", "theme.ts")
        self.assertEqual(t["--bg-canvas"], self.json_export(text, "tokens")["bgCanvas"])
        self.assertEqual(t["--email-h1-size-mobile"], self.json_export(text, "tokens")["emailH1SizeMobile"])
        h1 = self.json_export(text, "text")["h1"]
        self.assertEqual({"fontSize": t["--type-h1-size"], "fontWeight": int(t["--type-h1-weight"]),
                          "color": t["--fg-strong"], "margin": 0},
                         {k: h1[k] for k in ("fontSize", "fontWeight", "color", "margin")})
        self.assertEqual(t["--email-button-pad"], self.json_export(text, "styles")["button"]["padding"])
        self.assertEqual({"height": t["--gap-grouped"], "fontSize": 0, "lineHeight": 0},
                         self.json_export(text, "spacers")["gapGrouped"])
        self.assertEqual("wds-h1", self.json_export(text, "classes")["h1"])
        css = self.json_export(text, "headCss")
        self.assertIn(".wds-h1, .wds-h2", css)
        self.assertIn(".wds-gutter > tbody > tr > td", css)
        self.assertNotIn(".wds-surface >", css)

    def test_two_tokens_with_one_javascript_name_are_refused(self):
        self.tokens_file(bgCanvas="#000000")
        self.export("react-email", "theme.ts", "--tokens", "email-tokens.json", code=2)
        self.assertIn("bgCanvas", self.log)


class TheLintReadsAFrameworksMarkup(TempDirTest):
    """The two false positives MJML's output showed, each with its control."""

    PAGE = ('<!doctype html><html lang="en"><head><meta charset="utf-8"><title>t</title></head>'
            '<body style="background-color:#faf9f7">%s</body></html>')

    def findings(self, body: str, check: str) -> list[dict]:
        page = self.write("mail.html", self.PAGE % body)
        proc = run_py("email-template-system", "lint_email", page, "--format", "json", "--transactional",
                      cwd=self.tmp)
        self.assertIn(proc.returncode, (0, 1), output(proc))
        found = json.loads(proc.stdout.decode("utf-8"))["files"][str(page)]["findings"]
        return [f for f in found if f["check"] == check]

    def test_a_zero_size_wrapper_round_sized_text_is_not_small_text(self):
        body = ('<table role="presentation"><tr><td style="font-size:0px;padding:0">'
                '<div style="display:inline-block;width:100%%"><div style="font-size:16px;color:#171512">'
                'A paragraph set at sixteen pixels.</div></div></td></tr></table>')
        self.assertEqual([], self.findings(body, "type"))

    def test_text_an_element_sizes_itself_still_warns(self):
        for body in ('<p style="font-size:12px;color:#171512">Twelve pixels is too small.</p>',
                     '<td style="font-size:0px">Stray text <div style="font-size:16px">and a sized one</div></td>'):
            with self.subTest(body=body):
                self.assertEqual(1, len(self.findings(body, "type")))

    def test_a_hidden_preheader_has_no_contrast(self):
        body = ('<div style="display:none;font-size:1px;color:#ffffff;line-height:1px;max-height:0px;'
                'max-width:0px;opacity:0;overflow:hidden;">Back in stock, in three new colours.</div>'
                '<p style="font-size:16px;color:#171512">Visible.</p>')
        self.assertEqual([], [f for f in self.findings(body, "contrast") if f["severity"] == "error"])

    def test_visible_white_text_on_the_canvas_still_fails(self):
        body = '<p style="font-size:16px;color:#ffffff">Visible white text.</p>'
        self.assertEqual(["error"], [f["severity"] for f in self.findings(body, "contrast")])


class TheAuditLeavesAReactEmailTemplate(TempDirTest):
    """The design audit read the React Email starter as a site component and
    failed its image's inline width (L4); inline styles are email's medium, and
    lint_email reads the HTML it renders, as for HTML email."""

    def audit(self, text: str):
        page = self.write("emails/announcement.tsx", text)
        return run_py("web-design-studio", "audit_design", page, "--strict", cwd=self.tmp)

    def test_a_react_email_template_is_left_to_the_email_lint(self):
        proc = self.audit(REACT_STARTER.read_bytes().decode("utf-8"))
        self.assertEqual(0, proc.returncode, output(proc))
        self.assertIn("React Email: render it, then lint the HTML", output(proc))

    def test_the_generated_theme_is_left_alone(self):
        theme = self.tmp / "emails" / "theme.ts"
        proc = run_py("email-template-system", "export_email_theme", "--format", "react-email", "--out", theme,
                      cwd=self.tmp)
        self.assertEqual(0, proc.returncode, output(proc))
        proc = run_py("web-design-studio", "audit_design", theme, "--strict", cwd=self.tmp)
        self.assertEqual(0, proc.returncode, output(proc))      # 93 L1 warnings, which --strict fails, on 9e7e61f

    def test_a_component_of_another_library_is_still_audited(self):
        starter = REACT_STARTER.read_bytes().decode("utf-8")
        other = starter.replace("from 'react-email'", "from '@acme/ui'")
        # An import commented out, or quoted in a string, is no dependency (Codex on #198).
        cases = {"another library": other,
                 "a commented import": other + "\n// import { Text } from 'react-email';\n",
                 "a quoted import": other + "\nconst sample = \"import { Text } from 'react-email'\";\n"}
        for case, text in cases.items():
            with self.subTest(case=case):
                proc = self.audit(text)
                self.assertEqual(1, proc.returncode, output(proc))
                self.assertIn("L4", output(proc))


class Compiled(TempDirTest):
    """A starter and the theme it reads, in a folder of the project's."""

    def node(self, script: str, modules: str | None, *args: str) -> str:
        (self.tmp / "run.cjs").write_bytes(script.encode())
        proc = subprocess.run([NODE, "run.cjs", *args], cwd=self.tmp, capture_output=True, timeout=180,
                              env=env(NODE_PATH=modules))
        self.assertEqual(0, proc.returncode, output(proc))
        return proc.stdout.decode("utf-8")

    def theme(self, fmt: str, out: str, *args: str):
        proc = run_py("email-template-system", "export_email_theme", "--format", fmt, "--out", out, *args,
                      cwd=self.tmp)
        self.assertEqual(0, proc.returncode, output(proc))

    def lint(self, html: str):
        proc = run_py("email-template-system", "lint_email", html, "--strict", cwd=self.tmp)
        self.assertEqual(0, proc.returncode, output(proc))

    def probe(self, html: str) -> dict:
        if BROWSER_MODULES is None:
            self.skipTest("playwright is not installed (tooling/main) or WDS_NODE_MODULES is off")
        (self.tmp / "probe.cjs").write_bytes(PROBE.encode())
        proc = subprocess.run([NODE, "probe.cjs", str(self.tmp / html), json.dumps(PROBES)], cwd=self.tmp,
                              capture_output=True, timeout=180, env=env(NODE_PATH=BROWSER_MODULES))
        if proc.returncode == 3:
            self.skipTest(output(proc))
        self.assertEqual(0, proc.returncode, output(proc))
        return json.loads(proc.stdout)

    def assert_schemes(self, seen: dict):
        t = tokens()
        self.assertEqual((rgb(t["--fg-strong"]), rgb(t["--bg-surface"])), (seen["light"]["h1"]["color"],
                                                                         seen["light"]["h1"]["bg"]))
        self.assertEqual(rgb(t["--bg-sunken"]), seen["light"]["legal"]["bg"])
        dark = seen["dark"]
        self.assertEqual((rgb(t["--email-dark-fg"]), rgb(t["--email-dark-surface"])),
                         (dark["h1"]["color"], dark["h1"]["bg"]))
        self.assertEqual(rgb(t["--email-dark-fg"]), dark["body"]["color"])
        self.assertEqual((rgb(t["--email-dark-fg-muted"]), rgb(t["--email-dark-sunken"])),
                         (dark["legal"]["color"], dark["legal"]["bg"]))
        self.assertEqual((rgb(t["--fg-on-accent"]), rgb(t["--bg-accent"])),
                         (dark["button"]["color"], dark["button"]["bg"]))
        self.assertEqual((t["--type-h1-size"], t["--email-h1-size-mobile"]),
                         (seen["light"]["h1"]["size"], seen["phone"]["h1"]["size"]))
        # The gutter, once, on every section whatever its surface (Codex on #198):
        # centred in 800px on a desktop, the phone's gutter on a 375px screen.
        desktop = (800 - px(t["--email-width"])) // 2 + px(t["--gutter-page"])
        for probe in ("h1", "body", "legal"):
            with self.subTest(probe=probe):
                self.assertEqual((desktop, px(t["--email-gutter-mobile"])),
                                 (seen["light"][probe]["left"], seen["phone"][probe]["left"]))


@unittest.skipUnless(NODE and MJML_MODULES, "needs node and mjml (tooling/main), with WDS_NODE_MODULES on")
class TheMjmlStarter(Compiled):

    def setUp(self):
        super().setUp()
        (self.tmp / "emails").mkdir()
        shutil.copyfile(MJML_STARTER, self.tmp / "emails" / MJML_STARTER.name)

    def compile(self, *args: str) -> str:
        self.theme("mjml", "emails/theme.mjml", *args)
        errors = self.node(MJML_RUN, MJML_MODULES, "emails/" + MJML_STARTER.name, "out.html", "allow")
        self.assertEqual([], json.loads(errors))
        return (self.tmp / "out.html").read_bytes().decode("utf-8")

    def test_it_compiles_and_passes_the_lint(self):
        self.assertTrue(tokens()["--bg-accent"] in self.compile(), "the theme's accent is not in the email")
        self.lint("out.html")

    def test_the_projects_tokens_reach_the_compiled_email(self):
        data = json.loads(TOKENS.read_bytes())
        data["tokens"]["--bg-accent"] = {"value": "#7a2e8f"}
        self.write("brand.json", json.dumps(data))
        self.write(".design-suite.json", json.dumps({"schema": 1, "emailTokens": "brand.json"}))
        self.assertTrue("#7a2e8f" in self.compile(), "the project's accent is not in the email")

    def test_mjml_5_ignores_the_include_unless_it_is_allowed(self):
        """The premise of §11's command: without `ignoreIncludes: false`
        (`--config.allowIncludes true`) the theme never reaches the email."""
        self.theme("mjml", "emails/theme.mjml")
        self.node(MJML_RUN, MJML_MODULES, "emails/" + MJML_STARTER.name, "out.html", "default")
        html = (self.tmp / "out.html").read_bytes().decode("utf-8")
        self.assertFalse(tokens()["--bg-accent"] in html, "MJML read the include it should ignore")

    def test_dark_mode_and_the_phone_rules_apply_in_a_browser(self):
        self.compile()
        self.assert_schemes(self.probe("out.html"))


@unittest.skipUnless(NODE and REACT_MODULES, "needs node, typescript, react and react-email (tooling/main)")
class TheReactEmailStarter(Compiled):

    def setUp(self):
        super().setUp()
        shutil.copyfile(REACT_STARTER, self.tmp / REACT_STARTER.name)
        self.theme("react-email", "theme.ts")
        seen = json.loads(self.node(REACT_RUN, REACT_MODULES, ".", "product-announcement.js", "out.html"))
        self.assertTrue(seen["again"], "withMso added its block twice")
        self.html = (self.tmp / "out.html").read_bytes().decode("utf-8")

    def test_it_renders_and_passes_the_lint(self):
        self.assertEqual(1, self.html.count("<title>"), "Preview wrote a second <title>")
        self.assertEqual(1, self.html.count("o:PixelsPerInch>96"))
        self.lint("out.html")

    def test_dark_mode_and_the_phone_rules_apply_in_a_browser(self):
        self.assert_schemes(self.probe("out.html"))

    def test_the_javascript_theme_is_valid_javascript(self):
        self.theme("react-email", "theme.mjs")
        proc = subprocess.run([NODE, "--check", "theme.mjs"], cwd=self.tmp, capture_output=True, timeout=60,
                              env=env())
        self.assertEqual(0, proc.returncode, output(proc))


if __name__ == "__main__":
    unittest.main()
