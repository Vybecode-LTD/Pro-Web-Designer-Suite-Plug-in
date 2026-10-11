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
"""
from __future__ import annotations

import json
import re
import subprocess
import unittest

from wds_support import NODE, PLUGIN, SKILLS, TempDirTest, env, output, run_py, tool_modules

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
                    self.assertIn("--fg-default on --bg-inverse (dark, light scheme)", output(proc))

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
        page = self.write("page.html", html)
        probe = self.write("probe.mjs", PROBE_JS)
        proc = subprocess.run([NODE, probe, (PLUGIN / "shared" / "browser_common.mjs").as_uri(), page],
                              cwd=self.tmp, env=env(NODE_PATH=MODULES), capture_output=True, timeout=180)
        if proc.returncode == 3:
            self.skipTest(output(proc))
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
