"""check_roles.py, the role-pair contrast gate (3.2.0).

Regressions covered:
- SS-B1, SS-C2: nothing resolved the Tier-2 roles per theme and checked the
  pairs components use, so every "Verified n:1" was written by hand. That is
  how SS-A4 shipped: dark error text, .inverse text and control borders under
  AA.
- SS-A8: color-system.md §6's role table disagreed with tokens.css in four
  rows, and its "live audit findings" described a problem the tokens had
  already fixed another way. The table is now generated, and checked here.
- SS-B3 (3.6.0): a role written `light-dark(LIGHT, DARK)` was not a colour to
  the gate, so a system themed without JavaScript could not be checked; and
  style-architecture.md §10's `light-dark()` example runs in a browser here.
- N51 (P57, CodeRabbit on #187): a scope's blocks were applied by selector,
  `:root` first and the dark block after, whatever order they were written
  in. The browser applies the heavier selector, then the later block.
"""
from __future__ import annotations

import json
import re
import subprocess
import unittest

from wds_support import NODE, PLUGIN, SKILLS, TempDirTest, env, no_browser, output, run_py, tool_modules

STUDIO = SKILLS / "web-design-studio"
STARTER = STUDIO / "assets" / "starter" / "styles" / "tokens.css"
MODULES = tool_modules("WDS_NODE_MODULES", "playwright", node_path=True)


def merge_dark(css: str, light_at: str, dark_block: str, roles_re: str) -> str:
    """Each role the `dark_block` re-points becomes `light-dark(light, dark)`
    at its first declaration after `light_at`, and leaves the dark block."""
    head, sep, rest = css.partition(dark_block)
    body, close, tail = rest.partition("\n  }\n")
    # One line each: a comment may name a role (`--border-strong: 5.17:1 on…`) with no `;`.
    roles = re.findall(rf"\n\s*({roles_re}):\s*([^;\n]+);", body)
    assert sep and close and roles, f"the starter's {dark_block.strip()} block moved"
    before, mark, after = head.partition(light_at)
    assert mark, light_at
    for name, dark in roles:
        after, n = re.subn(rf"(\n\s*{re.escape(name)}:\s*)([^;\n]+);",
                           lambda m: f"{m.group(1)}light-dark({m.group(2).strip()}, {dark.strip()});", after, count=1)
        assert n == 1, name
        body = re.sub(rf"\n\s*{re.escape(name)}:\s*[^;\n]+;", "", body, count=1)
    return before + mark + after + sep + body + close + tail


def light_dark_starter() -> str:
    """The starter as a light-dark() system: each colour role the dark block
    re-points becomes `light-dark(light, dark)` on :root, each role the dark
    `.inverse` re-points does the same in `.inverse`, and the dark blocks keep
    only what is not a colour role. :root follows the OS (`light dark`), and
    `[data-theme="dark"]` keeps its `color-scheme: dark`."""
    css = STARTER.read_text(encoding="utf-8")
    css = merge_dark(css, ":root {", '  [data-theme="dark"] {', r"--(?:bg|fg|border)-[\w-]+")
    css = merge_dark(css, "  .inverse {", '  [data-theme="dark"] .inverse {', r"--[\w-]+")
    return css.replace(":root {", ":root {\n    color-scheme: light dark;", 1)


def by_scheme(results: list) -> set:
    """What a visitor in each scheme sees, whichever scope's selectors got them there."""
    return {(r["fg"], r["bg"], r["scheme"], r["ratio"], r["ok"]) for r in results}


# N51: the dark theme keeps its canvas and its ink in one block; `:root` sets
# the ink again, dark on dark. The two selectors weigh the same, so a page in
# the dark theme gets the ink of whichever block is written last.
DARK_BLOCK = '[data-theme="dark"] { --bg-canvas: #1a1a1a; --fg-default: #f5f5f5; }'
ROOT_BLOCK = ":root { --fg-default: #222222; }"
DARK_PAIR = [{"fg": "--fg-default", "bg": "--bg-canvas", "min": 4.5, "scopes": ["dark"]}]
# (name, the blocks in that order, what the gate exits with, the ink the page shows)
ORDERS = (("dark block first", (DARK_BLOCK, ROOT_BLOCK), 1, "rgb(34, 34, 34)"),
          ("root block first", (ROOT_BLOCK, DARK_BLOCK), 0, "rgb(245, 245, 245)"))


def contrast(a: str, b: str) -> float:
    """WCAG's ratio between two `rgb(r, g, b)` strings, as a browser prints them."""
    def luminance(rgb: str) -> float:
        lin = [(c / 255 / 12.92) if c / 255 <= 0.04045 else ((c / 255 + 0.055) / 1.055) ** 2.4
               for c in map(int, re.findall(r"\d+", rgb)[:3])]
        return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]
    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


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

    def test_a_rule_with_a_nested_block_is_still_read(self):
        """W8 (audit, 2026-10-14): a rule holding a nested block (native
        nesting) was skipped whole, so the starter with one nested @media
        said "--fg-default is not declared" (exit 2). The rule's own
        declarations are read; the nested block, a condition, is not."""
        nested = "\n    @media (prefers-contrast: more) { --fg-default: #ffffff; }\n"
        css = re.sub(r"(--fg-default:[^;]*;)", lambda m: m.group(1) + nested, self.starter(), count=1)
        self.assertIn("prefers-contrast", css)
        proc = self.roles(css)
        self.assertEqual(proc.returncode, 0, output(proc))
        self.assertIn("every declared pair clears its minimum", output(proc))
        after = css.index(nested) + len(nested)                 # a declaration after it is read
        css = css[:after] + re.sub(r"--fg-subtle:[^;]*;", "--fg-subtle: var(--neutral-0);", css[after:], count=1)
        proc = self.roles(css)
        self.assertEqual(proc.returncode, 1, output(proc))
        self.assertIn("--fg-subtle", output(proc))

    def test_status_inks_and_the_invalid_border_are_held(self):
        """P7 (SS-B2, SB-B4): white on --bg-warning is 2.25:1, so a filled
        badge had no legal ink, and an invalid field had no border role."""
        for name, decl in (("--fg-on-warning", "--fg-on-warning:  var(--neutral-1000);"),
                           ("--border-invalid", "--border-invalid: var(--danger-500);")):
            with self.subTest(role=name):
                css = self.starter().replace(decl, decl.replace(decl.split(":", 1)[1].strip(),
                                                                "var(--neutral-0);"), 1)
                self.assertNotEqual(css, self.starter())
                proc = self.roles(css)
                self.assertEqual(proc.returncode, 1, output(proc))
                self.assertIn(name, output(proc))

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

    def with_fg_default(self, value: str) -> str:
        css, n = re.subn(r"(--fg-default:\s*)[^;]+;", lambda m: f"{m.group(1)}{value};", self.starter(), count=1)
        self.assertEqual(n, 1)
        return css

    def test_a_translucent_role_is_not_measured_as_if_it_were_solid(self):
        """The audit's W1: `#00000080` was read as solid black, 20:1 on the
        canvas, and `oklch(… / 0.5)` was "not a colour": the translucency
        check came after a parser that drops a hex's alpha and refuses a
        function's. A translucent role is a11y_runtime's to measure."""
        for value in ("#00000080", "#0008", "oklch(20% 0 0 / 0.5)", "oklch(20% 0 0 / 50%)"):
            with self.subTest(value=value):
                proc = self.roles(self.with_fg_default(value))
                self.assertEqual(proc.returncode, 2, output(proc))
                self.assertIn(f"--fg-default = {value} is translucent", output(proc))
        proc = self.roles(self.with_fg_default("#1a1a1aff"))           # an opaque alpha is opaque
        self.assertEqual(proc.returncode, 0, output(proc))

    def test_a_colour_outside_srgb_is_held_to_its_worse_fallback(self):
        """The audit's W2: the gate clipped the channels, under which
        `oklch(59% 0.35 273)` is 6.49:1 on white; chroma-mapped, as a browser
        may show it, 4.40:1. `worst_contrast` takes the worse of the two."""
        proc = self.roles(self.with_fg_default("oklch(59% 0.35 273)"))
        self.assertEqual(proc.returncode, 1, output(proc))
        self.assertRegex(output(proc), r"--fg-default on --bg-canvas \(light\)")

    def test_the_ramps_check_refuses_alpha_and_takes_the_worse_fallback(self):
        """W1 and W2 in `generate_color_ramp.py --check`."""
        proc = run_py("web-design-studio", "generate_color_ramp", "--check", "#00000080", "#fafafa", cwd=self.tmp)
        self.assertEqual(proc.returncode, 2, output(proc))
        self.assertIn("translucent", output(proc))
        proc = run_py("web-design-studio", "generate_color_ramp", "--check", "oklch(59% 0.35 273)", "#ffffff",
                      cwd=self.tmp)
        self.assertEqual(proc.returncode, 0, output(proc))
        self.assertIn("contrast ratio  4.40:1  (outside sRGB", output(proc))
        self.assertRegex(output(proc), r"FAIL\s+4\.5:1  Body text")
        # A ramp from a translucent seed, or on a translucent canvas, was built
        # as if solid (CodeRabbit on #145).
        for argv in (["#e8440a80"], ["#e8440a", "--canvas", "#ffffff80"]):
            with self.subTest(argv=argv):
                proc = run_py("web-design-studio", "generate_color_ramp", *argv, cwd=self.tmp)
                self.assertEqual(proc.returncode, 2, output(proc))
                self.assertIn("translucent", output(proc))

    def test_a_role_that_does_not_resolve_is_a_bad_invocation(self):
        proc = self.roles(":root { --fg-default: var(--nope); --bg-canvas: oklch(98% 0 0); }")
        self.assertEqual(proc.returncode, 2, output(proc))
        self.assertIn("--nope is not declared", output(proc))

    def test_a_light_dark_system_measures_as_its_theme_blocks_do(self):
        """SS-B3: the same roles written with light-dark() give the same
        ratios, pair for pair, and the same role table."""
        written = light_dark_starter()
        self.assertIn("--bg-canvas:      light-dark(var(--neutral-50), var(--neutral-1000));", written)
        self.assertIn("--fg-default:     light-dark(var(--neutral-100), var(--neutral-900));", written)
        blocks, ours = self.roles(self.starter(), "--json"), self.roles(written, "--json")
        self.assertEqual(ours.returncode, 0, output(ours))
        # The light scope follows the OS now, so it is held in both schemes
        # (Codex on #112): the dark results it adds are the dark theme's.
        self.assertEqual(by_scheme(json.loads(ours.stdout)), by_scheme(json.loads(blocks.stdout)))
        self.assertIn(("light", "dark"), {(r["scope"], r["scheme"]) for r in json.loads(ours.stdout)})
        self.assertEqual(self.roles(written, "--table").stdout, self.roles(self.starter(), "--table").stdout)

    def test_a_scopes_color_scheme_picks_the_branch(self):
        """An inverse band set `color-scheme: dark` reads the dark branch, and
        a dark page set `light` reads the light one. A dark scope that leaves
        `light dark` in place is held in both: the visitor's preference picks
        the branch, not the selector (Codex on #112)."""
        css = (":root { color-scheme: light dark; --bg-canvas: light-dark(oklch(98% 0 0), oklch(15% 0 0));"
               " --fg-default: light-dark(oklch(25% 0 0), oklch(96% 0 0)); --bg-inverse: oklch(15% 0 0); }"
               " EXTRA")
        pairs = self.write("pairs.json", json.dumps([
            {"fg": "--fg-default", "bg": "--bg-inverse", "min": 4.5, "scopes": ["inverse"], "on": "light"},
            {"fg": "--fg-default", "bg": "--bg-inverse", "min": 4.5, "scopes": ["dark"]}]))
        forced = '.inverse { color-scheme: %s; } [data-theme="dark"] { color-scheme: %s; }'
        for extra, code in (("", 1), (forced % ("dark", "dark"), 0), (forced % ("only dark", "only dark"), 0),
                            (".inverse { color-scheme: dark; }", 1), (forced % ("dark", "light"), 1)):
            with self.subTest(extra=extra):
                proc = self.roles(css.replace("EXTRA", extra), "--pairs", pairs)
                self.assertEqual(proc.returncode, code, output(proc))
                if extra == ".inverse { color-scheme: dark; }":
                    self.assertIn("--fg-default on --bg-inverse (dark, light preference)", output(proc))

    def test_a_system_split_across_files_is_read_as_one(self):
        """Codex on #187: the config reader merges a project's token files in
        order, so one system may keep its ramps in one file and its roles in
        another. check_roles reads them together; each alone stays unresolvable."""
        self.write("ramps.css", ":root { --neutral-0: #ffffff; --neutral-900: #1a1a1a; }\n")
        self.write("roles.css", ":root { --bg-surface: var(--neutral-0); --fg-default: var(--neutral-900); }\n")
        pairs = self.write("pairs.json", json.dumps([{"fg": "--fg-default", "bg": "--bg-surface", "min": 4.5}]))
        both = run_py("web-design-studio", "check_roles", "ramps.css", "roles.css", "--pairs", pairs, cwd=self.tmp)
        self.assertEqual(0, both.returncode, output(both))
        for alone in ("ramps.css", "roles.css"):
            with self.subTest(alone=alone):
                proc = run_py("web-design-studio", "check_roles", alone, "--pairs", pairs, cwd=self.tmp)
                self.assertEqual(2, proc.returncode, output(proc))

    def test_the_block_written_last_wins_at_equal_weight(self):
        """N51 (CodeRabbit on #187; reproduced on v3.6.0 in one file): `:root`
        and `[data-theme="dark"]` are one selector heavy each, so the dark
        theme gets the ink of the block written last. The gate applied `:root`
        first and the dark block after, so a `:root` that set the ink again
        below the dark block passed, and the page showed dark text on dark."""
        pairs = self.write("pairs.json", json.dumps(DARK_PAIR))
        for name, blocks, code, _ in ORDERS:
            with self.subTest(order=name):
                proc = self.roles("\n".join(blocks), "--pairs", pairs)
                self.assertEqual(proc.returncode, code, output(proc))
                if code:
                    self.assertIn("FAIL  --fg-default on --bg-canvas (dark)", output(proc))

    def test_files_are_written_in_the_order_they_are_listed(self):
        """N51, several files: they are read as one system in the order given
        (the config reader's order), so the file listed last is written last."""
        pairs = self.write("pairs.json", json.dumps(DARK_PAIR))
        self.write("dark.css", DARK_BLOCK + "\n")
        self.write("root.css", ROOT_BLOCK + "\n")
        for name, files, code in (("dark listed first", ("dark.css", "root.css"), 1),
                                  ("root listed first", ("root.css", "dark.css"), 0)):
            with self.subTest(order=name):
                proc = run_py("web-design-studio", "check_roles", *files, "--pairs", pairs, cwd=self.tmp)
                self.assertEqual(proc.returncode, code, output(proc))

    def test_a_heavier_selector_beats_a_later_lighter_one(self):
        """The control for the test above, passing on v3.6.0 and now: in a
        dark band, `[data-theme="dark"] .inverse` is two selectors heavy and
        `.inverse` one, so the dark block wins whichever is written last. A
        gate that read source order alone would take the dark ink on dark."""
        dark_band = '[data-theme="dark"] .inverse { --fg-default: #f5f5f5; }'
        light_band = ".inverse { --fg-default: #222222; }"
        pairs = self.write("pairs.json", json.dumps([
            {"fg": "--fg-default", "bg": "--bg-inverse", "min": 4.5, "scopes": ["dark-inverse"], "on": "dark"}]))
        for name, blocks in (("dark band first", (dark_band, light_band)), ("dark band last", (light_band, dark_band))):
            with self.subTest(order=name):
                proc = self.roles("\n".join((":root { --bg-inverse: #1a1a1a; }", *blocks)), "--pairs", pairs)
                self.assertEqual(proc.returncode, 0, output(proc))

    def test_a_color_scheme_through_var_is_read_where_it_is_declared(self):
        """Codex on #112: `color-scheme: var(--scheme)` is the value of
        `--scheme` where it is declared, then inherited: an inverse band that
        only re-sets `--scheme` keeps its parent's scheme."""
        roles = ("--bg-canvas: light-dark(oklch(98% 0 0), oklch(15% 0 0));"
                 " --fg-default: light-dark(oklch(25% 0 0), oklch(15% 0 0));")
        pairs = self.write("pairs.json", json.dumps([
            {"fg": "--fg-default", "bg": "--bg-canvas", "min": 4.5, "scopes": ["light", "inverse"]}]))
        for css, code in ((f":root {{ --scheme: dark; color-scheme: var(--scheme); {roles} }}", 1),
                          (f":root {{ --scheme: light; color-scheme: var(--scheme, dark); {roles} }}", 0),
                          (f":root {{ color-scheme: var(--unset, light); {roles} }}", 0),
                          (f":root {{ --scheme: light; color-scheme: var(--scheme); {roles} }}"
                           " .inverse { --scheme: dark; }", 0)):
            with self.subTest(css=css):
                proc = self.roles(css, "--pairs", pairs)
                self.assertEqual(proc.returncode, code, output(proc))

    def test_the_light_dark_supports_block_is_what_the_gate_measures(self):
        """Codex on #112: concrete roles for older browsers, the light-dark()
        ones inside `@supports (color: light-dark(...))`. The gate measures the
        roles a current browser renders; any other @supports stays out."""
        concrete = ":root { --fg-default: oklch(25% 0 0); --bg-canvas: oklch(98% 0 0); }"
        modern = (":root { color-scheme: light dark; --fg-default: light-dark(oklch(25% 0 0), oklch(30% 0 0));"
                  " --bg-canvas: light-dark(oklch(98% 0 0), oklch(15% 0 0)); }")
        pairs = self.write("pairs.json", json.dumps([
            {"fg": "--fg-default", "bg": "--bg-canvas", "min": 4.5, "scopes": ["light"]}]))
        for wrapper, code in (("@supports (color: light-dark(#000, #fff))", 1), ("@supports (display: grid)", 0),
                              ("@media (prefers-color-scheme: dark)", 0)):
            with self.subTest(wrapper=wrapper):
                proc = self.roles(f"{concrete} {wrapper} {{ {modern} }}", "--pairs", pairs)
                self.assertEqual(proc.returncode, code, output(proc))
                if code:
                    self.assertIn("--fg-default on --bg-canvas (light, dark preference)", output(proc))

    def test_the_gate_models_what_the_browser_applies(self):
        """CodeRabbit on #112: a negated @supports is not applied by a browser
        that has light-dark(); `color-scheme: var(--scheme)` reads `--scheme`
        from any block on the same element, in any order; and a band that
        forces its scheme still sits on a parent that follows the visitor."""
        fails = "--fg-default: light-dark(oklch(25% 0 0), oklch(15% 0 0));"     # 1:1 in dark
        canvas = "--bg-canvas: light-dark(oklch(98% 0 0), oklch(15% 0 0));"
        canvas_pair = self.write("canvas.json", json.dumps([
            {"fg": "--fg-default", "bg": "--bg-canvas", "min": 4.5, "scopes": ["light"]}]))
        band_pair = self.write("band.json", json.dumps([
            {"fg": "--fg-default", "bg": "--bg-inverse", "min": 4.5, "scopes": ["inverse"], "on": "light"}]))
        cases = (
            ("negated @supports",
             f":root {{ color-scheme: light dark; {fails} {canvas} }}"
             " @supports not (color: light-dark(#000, #fff)) { :root { --fg-default: oklch(25% 0 0);"
             " --bg-canvas: oklch(98% 0 0); color-scheme: light; } }", canvas_pair, None),
            ("order on one element",
             f":root {{ color-scheme: var(--scheme); {fails} {canvas} }} :root {{ --scheme: dark; }}",
             canvas_pair, "--fg-default on --bg-canvas (light)"),
            ("forced band",
             ":root { color-scheme: light dark; --bg-inverse: light-dark(oklch(98% 0 0), oklch(15% 0 0)); }"
             " .inverse { color-scheme: dark; --fg-default: light-dark(oklch(15% 0 0), oklch(98% 0 0)); }",
             band_pair, "(inverse on the light --bg-inverse, light preference)"),
        )
        for name, css, pairs, says in cases:
            with self.subTest(case=name):
                proc = self.roles(css, "--pairs", pairs)
                self.assertEqual(proc.returncode, 1, output(proc))
                if says:
                    self.assertIn(says, output(proc))

    def test_a_light_dark_that_is_not_one_pair_is_not_a_colour(self):
        for value in ("light-dark(oklch(98% 0 0))", "light-dark(oklch(98% 0 0), oklch(15% 0 0), red)",
                      "light-dark(red, blue) green"):
            with self.subTest(value=value):
                proc = self.roles(f":root {{ --fg-default: {value}; --bg-canvas: oklch(98% 0 0); }}")
                self.assertEqual(proc.returncode, 2, output(proc))
                self.assertIn("not a colour", output(proc))

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


# Run with each OS colour scheme: every [data-probe] element's computed
# background and shadow, then again with <html data-theme="dark">.
PROBE_JS = """
import { readFileSync } from 'node:fs';
const common = await import(process.argv[2]);
const { chromium } = await common.loadPlaywright((m) => { console.error(m); process.exit(2); }, '');
const launched = await common.launchBrowser(chromium);
if (!launched.browser) { console.error('no usable chromium: ' + launched.tried.join('; ')); process.exit(3); }
const html = readFileSync(process.argv[3], 'utf8');
const read = () => Object.fromEntries([...document.querySelectorAll('[data-probe]')].map((el) => {
  const cs = getComputedStyle(el);
  return [el.dataset.probe, { bg: cs.backgroundColor, shadow: cs.boxShadow }];
}));
const out = {};
for (const scheme of ['light', 'dark']) {
  const context = await launched.browser.newContext({ colorScheme: scheme });
  const page = await context.newPage();
  await page.setContent(html);
  out[scheme] = await page.evaluate(read);
  await page.evaluate(() => { document.documentElement.dataset.theme = 'dark'; });
  out[scheme + '+dark'] = await page.evaluate(read);
  await context.close();
}
await launched.browser.close();
console.log(JSON.stringify(out));
"""


@unittest.skipUnless(NODE and MODULES, "needs node plus WDS_NODE_MODULES pointing at playwright")
class LightDarkInABrowser(TempDirTest):
    """SS-B3: style-architecture.md §10's example, run as written. The OS
    picks the theme with no script, `[data-theme]` overrides it on the page
    and on a subtree, and a token derived on :root (`--elevation-card`)
    follows, which re-pointing a role in a block cannot do (SS-A1)."""

    LIGHT, DARK = "rgb(250, 250, 250)", "rgb(10, 10, 10)"

    def example(self) -> str:
        text = (STUDIO / "references" / "style-architecture.md").read_text(encoding="utf-8")
        m = re.search(r"<!-- light-dark:example -->\s*```css\n(.*?)```", text, flags=re.S)
        self.assertIsNotNone(m, "the example lost its marker")
        return m.group(1)

    def run_probe(self) -> dict:
        tile = 'style="background: var(--bg-canvas); box-shadow: var(--elevation-card)"'
        html = ("<!doctype html><style>:root { --neutral-0: rgb(255, 255, 255); --neutral-50: %s;"
                " --neutral-100: rgb(240, 240, 240); --neutral-900: rgb(30, 30, 30);"
                " --neutral-950: rgb(20, 20, 20); --neutral-1000: %s; }\n%s</style>"
                "<div data-probe='page' %s></div>"
                "<section data-theme='dark'><div data-probe='dark' %s></div></section>"
                "<section data-theme='light'><div data-probe='light' %s></div></section>"
                % (self.LIGHT, self.DARK, self.example(), tile, tile, tile))
        return self.probe_page(html)

    def probe_page(self, html: str) -> dict:
        page = self.write("page.html", html)
        probe = self.write("probe.mjs", PROBE_JS)
        proc = subprocess.run([NODE, probe, (PLUGIN / "shared" / "browser_common.mjs").as_uri(), page],
                              cwd=self.tmp, env=env(NODE_PATH=MODULES), capture_output=True, timeout=180)
        if proc.returncode == 3:
            no_browser(self, output(proc))
        self.assertEqual(proc.returncode, 0, output(proc))
        return json.loads(proc.stdout)

    def test_the_os_picks_and_data_theme_overrides_on_a_page_and_a_subtree(self):
        seen = self.run_probe()
        light = {"bg": self.LIGHT, "alpha": "0.06"}
        dark = {"bg": self.DARK, "alpha": "0.36"}
        want = {"light": {"page": light, "dark": dark, "light": light},
                "dark": {"page": dark, "dark": dark, "light": light},
                "light+dark": {"page": dark, "dark": dark, "light": light},
                "dark+dark": {"page": dark, "dark": dark, "light": light}}
        for run, probes in want.items():
            for probe, expected in probes.items():
                with self.subTest(run=run, probe=probe):
                    got = seen[run][probe]
                    self.assertEqual(got["bg"], expected["bg"], got)
                    self.assertIn(expected["alpha"], got["shadow"], got)

    def test_the_block_written_last_wins_in_a_browser_and_the_gate_agrees(self):
        """N51: the cascade the gate now models, run in Chromium. A page in the
        dark theme shows the ink of the later of `:root` and `[data-theme]`
        (one selector heavy each), and the gate's verdict is the verdict on the
        two colours the page shows. The ink and the canvas are read off two
        probes that paint with them."""
        pairs = self.write("pairs.json", json.dumps(DARK_PAIR))
        for name, blocks, code, ink in ORDERS:
            with self.subTest(order=name):
                css = "\n".join(blocks)
                seen = self.probe_page("<!doctype html><style>%s</style>"
                                       "<div data-probe='ink' style='background: var(--fg-default)'></div>"
                                       "<div data-probe='canvas' style='background: var(--bg-canvas)'></div>"
                                       % css)["light+dark"]
                self.assertEqual(seen["ink"]["bg"], ink, seen)
                shown = contrast(seen["ink"]["bg"], seen["canvas"]["bg"])
                self.assertEqual(shown >= 4.5, code == 0, shown)
                gate = run_py("web-design-studio", "check_roles", self.write("tokens.css", css), "--pairs", pairs,
                              cwd=self.tmp)
                self.assertEqual(gate.returncode, code, output(gate))
