"""web-design-studio's starter CSS: tokens.css, reset.css (3.1.0).

Regressions covered:
- SS-A1: the density roles (--gap-*, --pad-*) and the theme-derived tokens
  (--elevation-*, --shadow-focus) were declared on :root only, so they were
  resolved once and inherited: a subtree's data-density or data-theme changed
  the dial and nothing else.
- SS-A2: the dark theme never set color-scheme, and the OS-dark media query
  flipped ONLY color-scheme, so native form fields rendered at 1.12:1 / 1.63:1.
- SS-A3: [hidden] sat in the weakest layer, so .stack[hidden] still rendered.
- SS-A4: dark --fg-danger was 4.38:1 on the canvas, .inverse had no role
  re-points (headings 1.10:1), and the only control-boundary border was 1.51:1.
- SS-A5: the reset removed <dialog>'s viewport limit, so a tall modal could
  not scroll.
- SB-A1: the reset drew the focus ring as a box-shadow, which any component's
  own box-shadow (in a later layer) replaced: no visible focus.
"""
from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import unittest

from wds_support import NODE, SKILLS, TempDirTest, env, no_browser, output, tool_modules

STYLES = SKILLS / "web-design-studio" / "assets" / "starter" / "styles"


def css(name: str) -> str:
    return re.sub(r"/\*.*?\*/", " ", (STYLES / name).read_text(encoding="utf-8"), flags=re.S)


def rules(text: str) -> list[tuple[list[str], dict[str, str]]]:
    """Innermost `selectors { declarations }` blocks, in order."""
    out = []
    for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", text):
        sels = [s.strip() for s in m.group(1).split(",")]
        decls = {k.strip(): v.strip() for k, v in
                 re.findall(r"(--[\w-]+|[a-z-]+)\s*:\s*([^;]+);?", m.group(2))}
        out.append((sels, decls))
    return out


def declaring(text: str, prop: str) -> list[list[str]]:
    return [sels for sels, decls in rules(text) if prop in decls]


class StarterStructure(unittest.TestCase):

    def test_density_roles_are_declared_where_the_dial_is_turned(self):
        for prop in ("--gap-grouped", "--pad-card"):
            with self.subTest(prop=prop):
                self.assertTrue(any("[data-density]" in s for s in declaring(css("tokens.css"), prop)))

    def test_theme_derived_tokens_are_declared_on_themed_elements(self):
        for prop in ("--elevation-card", "--shadow-focus"):
            with self.subTest(prop=prop):
                self.assertTrue(any("[data-theme]" in s for s in declaring(css("tokens.css"), prop)))

    def test_the_themes_carry_their_colour_scheme(self):
        tokens = css("tokens.css")
        dark = [d for s, d in rules(tokens) if s == ['[data-theme="dark"]']]
        self.assertTrue(dark and dark[0].get("color-scheme") == "dark")
        media = re.search(r"@media\s*\(prefers-color-scheme:\s*dark\)\s*\{(.*?)\}\s*\}", tokens, re.S)
        self.assertFalse(media and "color-scheme" in media.group(1),
                         "an OS-dark query that flips only color-scheme")

    def test_hidden_beats_every_layer(self):
        hidden = [d for s, d in rules(css("reset.css")) if any(x.startswith("[hidden]") for x in s)]
        self.assertTrue(hidden and "!important" in hidden[0].get("display", ""))

    def test_the_dialog_keeps_its_viewport_limit(self):
        dialog = [d for s, d in rules(css("reset.css")) if s == ["dialog"]]
        self.assertTrue(dialog)
        self.assertNotIn("none", dialog[0].get("max-block-size", ""))

    def test_the_focus_ring_is_an_outline_a_component_shadow_cannot_remove(self):
        ring = [d for s, d in rules(css("reset.css")) if s == [":focus-visible"]]
        self.assertTrue(ring)
        self.assertNotIn("transparent", ring[0].get("outline", "transparent"))


def _load_generator():
    spec = importlib.util.spec_from_file_location(
        "wds_color", SKILLS / "web-design-studio" / "scripts" / "generate_color_ramp.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class StarterRoleContrast(unittest.TestCase):
    """Resolve each role to its primitive per theme, then measure it."""

    @classmethod
    def tokens_text(cls) -> str:
        """The tokens file to measure; a subclass measures another one."""
        return css("tokens.css")

    @classmethod
    def setUpClass(cls):
        cls.gen = _load_generator()
        blocks = rules(cls.tokens_text())
        cls.scopes = {}
        for scope, wanted in (("light", [":root"]), ("dark", [":root", '[data-theme="dark"]']),
                              ("inverse", [":root", ".inverse"]),
                              ("dark-inverse", [":root", '[data-theme="dark"]', ".inverse",
                                                '[data-theme="dark"] .inverse'])):
            merged: dict[str, str] = {}
            for want in wanted:
                for sels, decls in blocks:
                    if want in sels or (want != ":root" and want == "[data-theme]"):
                        merged.update(decls)
            cls.scopes[scope] = merged

    def value(self, scope: str, name: str, base: str | None = None) -> tuple:
        env_ = self.scopes[scope]
        v = env_[name]
        seen = set()
        while v.startswith("var("):
            ref = re.match(r"var\(\s*(--[\w-]+)", v).group(1)
            self.assertNotIn(ref, seen)
            seen.add(ref)
            v = env_[ref]
        return self.gen.parse_color(v)

    def ratio(self, scope: str, fg: str, bg: str, bg_scope: str | None = None) -> float:
        return self.gen.contrast_ratio_oklch(self.value(scope, fg),
                                             self.value(bg_scope or scope, bg))

    def test_dark_error_text_meets_aa(self):
        for bg in ("--bg-canvas", "--bg-surface"):
            with self.subTest(bg=bg):
                self.assertGreaterEqual(self.ratio("dark", "--fg-danger", bg), 4.5)

    def test_the_control_boundary_border_meets_3_to_1(self):
        for scope in ("light", "dark"):
            for bg in ("--bg-canvas", "--bg-surface"):
                with self.subTest(scope=scope, bg=bg):
                    self.assertGreaterEqual(self.ratio(scope, "--border-strong", bg), 3.0)

    def test_inverse_sections_re_point_their_text_roles(self):
        for scope, bg_scope in (("inverse", "light"), ("dark-inverse", "dark")):
            for fg in ("--fg-default", "--fg-strong", "--fg-muted", "--fg-subtle", "--fg-link"):
                with self.subTest(scope=scope, fg=fg):
                    self.assertGreaterEqual(
                        self.ratio(scope, fg, "--bg-inverse", bg_scope), 4.5)


PROBE = r"""
import { createRequire } from 'node:module';
import { pathToFileURL } from 'node:url';
import path from 'node:path';
const require = createRequire(import.meta.url);
let pw = null;
for (const root of (process.env.NODE_PATH || '').split(path.delimiter)) {
  try { pw = require(path.join(root, 'playwright')); break; } catch { /* next */ }
}
if (!pw) { console.error('no playwright'); process.exit(3); }
let browser = null;
for (const opt of [{}, { channel: 'chrome' }, { channel: 'msedge' }]) {
  try { browser = await pw.chromium.launch(opt); break; } catch { /* next */ }
}
if (!browser) { console.error('no browser'); process.exit(3); }
const page = await browser.newPage({ viewport: { width: 1000, height: 700 } });
await page.goto(pathToFileURL(process.argv[2]).href);
await page.keyboard.press('Tab');
const out = await page.evaluate(() => {
  const cs = (id) => getComputedStyle(document.getElementById(id));
  // Read the focus ring first: showModal() moves focus into the dialog.
  const focused = document.activeElement && document.activeElement.id;
  const focusOutline = cs('btn').outlineStyle + ' ' + cs('btn').outlineColor;
  const dlg = document.getElementById('tall');
  dlg.showModal();
  const r = dlg.getBoundingClientRect();
  return {
    compactGap: cs('compact').rowGap,
    rootGap: cs('root').rowGap,
    hiddenDisplay: cs('hid').display,
    focused,
    focusOutline,
    dialogFits: r.height <= innerHeight,
    dialogScrolls: dlg.scrollHeight > dlg.clientHeight,
  };
});
console.log(JSON.stringify(out));
await browser.close();
"""


PLAYWRIGHT = tool_modules("WDS_NODE_MODULES", "playwright", node_path=True)


@unittest.skipUnless(NODE and PLAYWRIGHT,
                     "needs node plus WDS_NODE_MODULES pointing at playwright")
class StarterInABrowser(TempDirTest):

    def test_the_starter_behaves(self):
        links = "".join(f'<link rel="stylesheet" href="{(STYLES / f).as_uri()}">'
                        for f in ("reset.css", "tokens.css", "base.css", "layout.css"))
        page = self.write("page.html", f"""<!doctype html><html lang="en"><head><title>t</title>
<style>@layer reset, tokens, base, layout, components;
@layer components {{ .btn {{ box-shadow: var(--elevation-card); }} }}</style>{links}</head>
<body><main><button class="btn" id="btn">Save</button>
<div class="stack" id="root"><p>a</p><p>b</p></div>
<section data-density="compact"><div class="stack" id="compact"><p>a</p><p>b</p></div></section>
<div class="stack" id="hid" hidden><p>x</p></div>
<dialog id="tall"><div style="block-size: 3000px">tall</div></dialog></main></body></html>""")
        probe = self.write("probe.mjs", PROBE)
        modules = PLAYWRIGHT
        proc = subprocess.run([NODE, str(probe), str(page)], capture_output=True, timeout=180,
                              env=env(NODE_PATH=modules))
        if proc.returncode == 3:
            no_browser(self, output(proc))
        self.assertEqual(proc.returncode, 0, output(proc))
        got = json.loads(proc.stdout.decode("utf-8").strip().splitlines()[-1])
        self.assertNotEqual(got["compactGap"], got["rootGap"], got)     # the dial works
        self.assertEqual(got["hiddenDisplay"], "none", got)
        self.assertTrue(got["focusOutline"].startswith("solid"), got)
        self.assertNotIn("rgba(0, 0, 0, 0)", got["focusOutline"], got)
        self.assertTrue(got["dialogFits"] and got["dialogScrolls"], got)

    def test_the_caveat_fix_keeps_the_ring_visible_in_a_clipping_ancestor(self):
        """reset.css's CAVEAT said an outline is NOT clipped by an ancestor's
        overflow: hidden and told readers to swap to one. Both rings are
        clipped; the fix the CAVEAT prescribes is applied here as written."""
        caveat = re.search(r"/\*\s*CAVEAT(.*?)\*/", (STYLES / "reset.css").read_text(encoding="utf-8"), re.S)
        self.assertIsNotNone(caveat, "reset.css lost its focus-ring CAVEAT")
        recipes = [" ".join(s.split()) for s in re.findall(r"`([^`]*)`", caveat.group(1))
                   if "outline" in s and ":" in s]
        self.assertTrue(recipes, "the CAVEAT no longer quotes a declaration to copy")
        links = "".join(f'<link rel="stylesheet" href="{(STYLES / f).as_uri()}">'
                        for f in ("reset.css", "tokens.css", "base.css"))
        page = self.write("clip.html", f"""<!doctype html><html lang="en"><head><title>t</title>
<style>@layer reset, tokens, base, layout, components;
@layer components {{
  .wrap {{ overflow: hidden; inline-size: max-content; margin: 24px; }}
  #wrap-visible {{ overflow: visible; }}
  .wrap > button {{ display: block; }}
  #inside:focus-visible {{ {recipes[-1]} }}
}}</style>{links}</head>
<body><div class="wrap" id="wrap-visible"><button id="visible">Save</button></div>
<div class="wrap" id="wrap-outside"><button id="outside">Save</button></div>
<div class="wrap" id="wrap-inside"><button id="inside">Save</button></div></body></html>""")
        probe = self.write("clip.mjs", PROBE.split("const page =")[0] + CLIP_PROBE)
        modules = PLAYWRIGHT
        proc = subprocess.run([NODE, str(probe), str(page)], capture_output=True, timeout=180,
                              env=env(NODE_PATH=modules))
        if proc.returncode == 3:
            no_browser(self, output(proc))
        self.assertEqual(proc.returncode, 0, output(proc))
        seen = json.loads(proc.stdout.decode("utf-8").strip().splitlines()[-1])
        # visible: the positive control, proving the probe sees a ring at all.
        self.assertEqual(seen, {"visible": True, "outside": False, "inside": True},
                         f"CAVEAT recipe applied: {recipes[-1]}")


# Tab to each button in turn and ask: did any pixel change in and around its
# wrapper? A ring drawn outside a clipping wrapper is clipped away entirely.
CLIP_PROBE = r"""
const page = await browser.newPage({ viewport: { width: 500, height: 400 } });
await page.goto(pathToFileURL(process.argv[2]).href);
const ids = ['visible', 'outside', 'inside'];
const regions = {}, before = {}, seen = {};
for (const id of ids) {
  const b = await page.locator('#wrap-' + id).boundingBox();
  regions[id] = { x: b.x - 12, y: b.y - 12, width: b.width + 24, height: b.height + 24 };
  before[id] = await page.screenshot({ clip: regions[id] });
}
for (const id of ids) {
  await page.keyboard.press('Tab');
  const focused = await page.evaluate(() => document.activeElement?.id);
  seen[id] = focused === id ? !before[id].equals(await page.screenshot({ clip: regions[id] }))
                            : 'focus went to ' + focused;
}
console.log(JSON.stringify(seen));
await browser.close();
"""


# A page laid out as the starter's shell is, read at 320 CSS px (400% zoom).
CODE_PROBE = r"""
const page = await browser.newPage({ viewport: { width: 320, height: 640 } });
await page.goto(pathToFileURL(process.argv[2]).href);
const out = await page.evaluate(() => {
  const pre = document.getElementById('cmd');
  const code = pre.querySelector('code');
  const p = getComputedStyle(pre), canvas = getComputedStyle(document.body).backgroundColor;
  return {
    pageWidth: document.documentElement.scrollWidth,
    viewport: document.documentElement.clientWidth,
    preScrolls: pre.scrollWidth > pre.clientWidth,
    codeFont: getComputedStyle(code).fontFamily,
    monoToken: getComputedStyle(document.documentElement).getPropertyValue('--font-mono').trim(),
    // a box shows when its fill differs from the canvas or it draws an edge
    preBox: p.backgroundColor !== canvas || (parseFloat(p.borderTopWidth) > 0 && p.borderTopStyle !== 'none'),
  };
});
console.log(JSON.stringify(out));
await browser.close();
"""


@unittest.skipUnless(NODE and PLAYWRIGHT,
                     "needs node plus WDS_NODE_MODULES pointing at playwright")
class StarterCodeBlocks(TempDirTest):
    """N50 (P56 part 2), found building webdesignersuite.com on the starter:
    F1, a `pre > code` kept the UA's `monospace` (Courier) instead of
    --font-mono; F5, on the dark canvas a `pre` drew no box (--bg-sunken is the
    canvas there); F6, a .page-grid item holding a long `pre` set the page's
    width, 721px at 320px, a 1.4.10 failure."""

    def probe(self, theme: str) -> dict:
        links = "".join(f'<link rel="stylesheet" href="{(STYLES / f).as_uri()}">'
                        for f in ("reset.css", "tokens.css", "base.css", "layout.css"))
        command = "/plugin install pro-web-design-suite --marketplace Vybecode-LTD/pro-web-design-suite"
        page = self.write(f"code-{theme}.html", f"""<!doctype html><html lang="en" data-theme="{theme}"><head>
<title>t</title><style>@layer reset, tokens, base, layout, components;</style>{links}</head>
<body class="page-shell"><header class="page-grid"><p>Site</p></header>
<main><section class="page-grid"><div class="stack"><h1>Install</h1>
<pre id="cmd" tabindex="0"><code>{command}</code></pre></div></section></main>
<footer class="page-grid"><p>Footer</p></footer></body></html>""")
        probe = self.write("code.mjs", PROBE.split("const page =")[0] + CODE_PROBE)
        proc = subprocess.run([NODE, str(probe), str(page)], capture_output=True, timeout=180,
                              env=env(NODE_PATH=PLAYWRIGHT))
        if proc.returncode == 3:
            no_browser(self, output(proc))
        self.assertEqual(proc.returncode, 0, output(proc))
        return json.loads(proc.stdout.decode("utf-8").strip().splitlines()[-1])

    def test_a_long_code_line_scrolls_in_its_box_not_the_page(self):
        got = self.probe("light")
        self.assertLessEqual(got["pageWidth"], got["viewport"], got)
        self.assertTrue(got["preScrolls"], got)     # the control: the line is too long for 320px

    def test_code_is_set_in_the_mono_token(self):
        got = self.probe("light")
        first = got["monoToken"].split(",")[0].strip()
        self.assertTrue(got["codeFont"].startswith(first), got)

    def test_a_code_block_shows_its_box_in_both_themes(self):
        for theme in ("light", "dark"):
            with self.subTest(theme=theme):
                self.assertTrue(self.probe(theme)["preBox"], theme)


if __name__ == "__main__":
    unittest.main()
