"""tw_probe.mjs (SB-C3): the project's own Tailwind v4, asked which classes
its theme generates.

The theme's claims ("`--*: initial` removed `p-4`", "the theme gives
`bg-surface`") are silent when false: Tailwind writes no CSS for a class it
does not know. These tests compile the starter's own Tailwind wiring with the
tooling's tailwindcss, found as a project finds it (NODE_PATH stands in for
the project's node_modules), and break it the ways a project does.
"""
from __future__ import annotations

import json
import re
import subprocess
import unittest
from pathlib import Path

from wds_support import NODE, SKILLS, TOOLING_V3, TempDirTest, env, output, tool_modules

SCRIPT = SKILLS / "web-design-studio" / "scripts" / "tw_probe.mjs"
CONFIGS = SKILLS / "web-design-studio" / "assets" / "configs"
STARTER = SKILLS / "web-design-studio" / "assets" / "starter" / "styles"
TAILWIND = tool_modules("WDS_TAILWIND_MODULES", "tailwindcss")
TAILWIND_V3 = tool_modules("WDS_TAILWIND_V3_MODULES", "tailwindcss", default=TOOLING_V3)


class ProbeProject(TempDirTest):
    """The starter's Tailwind wiring in src/styles/, as a project copies it."""

    def setUp(self):
        super().setUp()
        self.write("src/styles/index.css", (CONFIGS / "index.tailwind.css").read_bytes().decode("utf-8"))
        self.write("src/styles/theme.css", (CONFIGS / "theme.css").read_bytes().decode("utf-8"))
        for name in ("tokens.css", "base.css", "layout.css"):
            self.write(f"src/styles/{name}", (STARTER / name).read_bytes().decode("utf-8"))

    def probe(self, *args, modules=None):
        return subprocess.run([NODE, str(SCRIPT), *args], cwd=self.tmp, capture_output=True, timeout=300,
                              env=env(NODE_PATH=modules or TAILWIND))

    def report(self, *args) -> dict:
        proc = self.probe("--json", *args)
        self.assertIn(proc.returncode, (0, 1), output(proc))
        return json.loads(proc.stdout)

    def add_theme(self, css: str):
        self.write("src/styles/index.css",
                   (self.tmp / "src/styles/index.css").read_bytes().decode("utf-8") + css)


@unittest.skipUnless(NODE and TAILWIND, "set WDS_TAILWIND_MODULES to a node_modules with tailwindcss 4")
class TheProbe(ProbeProject):

    def test_the_starters_theme_passes(self):
        """Every role it declares gives its class, and no stock class survives."""
        proc = self.probe()
        self.assertEqual(0, proc.returncode, output(proc))
        report = self.report()
        self.assertGreater(len(report["roles"]), 50)
        self.assertEqual([], [r for r in report["roles"] if not r["generates"]])
        self.assertTrue(report["stock"])
        self.assertEqual([], [s for s in report["stock"] if s["generates"]])
        self.assertEqual("pass", report["verdict"])

    def test_each_namespace_gives_its_class(self):
        roles = {r["variable"]: r["class"] for r in self.report()["roles"]}
        for variable, cls in (("--color-surface", "bg-surface"), ("--spacing-card", "p-card"),
                              ("--breakpoint-md", "md:block")):
            with self.subTest(variable=variable):
                self.assertEqual(cls, roles.get(variable))

    def test_a_kept_spacing_multiplier_brings_the_numbers_back(self):
        """LC-B5: `--spacing` alone keeps `p-4`, `w-4` and `leading-7`."""
        self.add_theme("@theme { --spacing: 0.25rem; }\n")
        proc = self.probe()
        self.assertEqual(1, proc.returncode, output(proc))
        failing = {s["class"] for s in self.report()["stock"] if s["generates"]}
        self.assertTrue({"p-4", "w-4", "leading-7"} <= failing, failing)
        self.assertIn("--spacing: initial", output(proc))

    def test_tailwinds_own_theme_fails_the_stock_check(self):
        self.write("src/styles/index.css", '@import "tailwindcss";\n')
        report = self.report()
        self.assertEqual("fail", report["verdict"])
        self.assertIn("bg-neutral-800", {s["class"] for s in report["stock"] if s["generates"]})

    def test_named_classes_are_reported_and_expectations_held(self):
        report = self.report("p-card", "p-4", "stack", "md:p-card", "bg-surface/50")
        found = {p["class"]: p["generates"] for p in report["probe"]}
        self.assertEqual({"p-card": True, "p-4": False, "md:p-card": True, "bg-surface/50": True,
                          # layout.css's own class is the stylesheet's, not Tailwind's
                          "stack": False}, found)
        self.assertEqual("pass", report["verdict"])
        proc = self.probe("--expect", "bg-surfce", "--refuse", "p-card")
        self.assertEqual(1, proc.returncode, output(proc))
        self.assertIn("bg-surfce: expected", output(proc))
        self.assertIn("p-card: refused", output(proc))

    def test_a_container_size_gives_its_query_variant(self):
        self.add_theme("@theme { --container-card: 40rem; }\n")
        report = self.report("@card:p-card")
        self.assertIn({"variable": "--container-card", "class": "@card:block", "generates": True}, report["roles"])
        self.assertEqual([{"class": "@card:p-card", "generates": True}], report["probe"])

    def test_an_inline_source_does_not_hide_its_classes(self):
        """`@source inline()` put its classes in the first build, so asking
        for them added nothing: a role read as missing, and an inline `p-4`
        hid a surviving `--spacing` (Codex and CodeRabbit on #126)."""
        self.add_theme('@source inline("bg-surface {hover:,}p-card p-4");\n')
        report = self.report("hover:p-card")
        self.assertEqual("pass", report["verdict"], report["failures"])
        self.assertEqual([{"class": "hover:p-card", "generates": True}], report["probe"])
        self.add_theme("@theme { --spacing: 0.25rem; }\n")
        self.assertIn("p-4", {s["class"] for s in self.report()["stock"] if s["generates"]})

    def test_a_prefixed_theme_is_probed_with_its_prefix(self):
        """Codex on #126: with `prefix(tw)` Tailwind knows `tw:bg-surface`,
        so unprefixed candidates failed every role and passed every stock."""
        self.write("src/styles/index.css", '@import "tailwindcss" prefix(tw);\n')
        report = self.report()
        self.assertIn("tw:bg-neutral-800", {s["class"] for s in report["stock"] if s["generates"]})
        entry = (CONFIGS / "index.tailwind.css").read_bytes().decode("utf-8")
        self.write("src/styles/index.css", entry.replace(
            '@import "tailwindcss/theme.css"     layer(theme);',
            '@import "tailwindcss/theme.css"     layer(theme) prefix(tw);', 1))
        report = self.report()
        self.assertEqual("pass", report["verdict"], report["failures"])
        self.assertIn("tw:bg-surface", {r["class"] for r in report["roles"]})

    def test_a_declared_name_owns_every_class_it_gives(self):
        """Codex on #126: `--spacing-4` gives `p-4`, `gap-4` and `w-4` on
        purpose, and `--container-md` gives `max-w-md`; none is a stock leak."""
        self.add_theme("@theme { --spacing-4: 1rem; --container-md: 28rem; }\n")
        report = self.report()
        self.assertEqual("pass", report["verdict"], report["failures"])
        self.assertFalse({"p-4", "gap-4", "w-4", "max-w-md"} & {s["class"] for s in report["stock"]})

    def test_an_unquoted_url_import_is_followed(self):
        """Codex on #126: `@import url(./more.css)` compiled, but its @theme
        was never read."""
        self.write("src/styles/more.css", "@theme { --color-extra: oklch(60% 0.1 200); }\n")
        entry = (self.tmp / "src/styles/index.css").read_bytes().decode("utf-8")
        # After theme.css, whose `--*: initial` would clear it.
        self.write("src/styles/index.css",
                   entry.replace('@import "./theme.css";', '@import "./theme.css";\n@import url(./more.css);', 1))
        roles = {r["variable"]: r for r in self.report()["roles"]}
        self.assertIn("--color-extra", roles)

    def test_a_namespace_cleared_after_its_variables_drops_them(self):
        self.add_theme("@theme { --radius-*: initial; }\n")
        roles = {r["variable"] for r in self.report()["roles"]}
        self.assertFalse([v for v in roles if v.startswith("--radius-")])
        self.assertTrue([v for v in roles if v.startswith("--color-")])

    def test_a_cleared_namespace_keeps_what_tailwind_keeps_under_it(self):
        """The audit's W3: Tailwind's clearNamespace() keeps `--font-weight-*`
        and `--font-size-*` under `--font-*: initial`. The probe cleared them,
        so the theme's own `font-bold` read as a stock class that survived."""
        self.add_theme("@theme {\n  --font-weight-bold: 700;\n  --font-*: initial;\n}\n")
        proc = self.probe()
        self.assertEqual(0, proc.returncode, output(proc))
        report = self.report()
        roles = {r["variable"]: r for r in report["roles"]}
        self.assertEqual("font-bold", roles["--font-weight-bold"]["class"])
        self.assertTrue(roles["--font-weight-bold"]["generates"])
        self.assertFalse([v for v in roles if v.startswith("--font-") and not v.startswith("--font-weight-")])
        self.assertEqual([], [s["class"] for s in report["stock"] if s["generates"]])

    def test_what_it_cannot_run_on_exits_2(self):
        for args, modules, message in (
                (("--entry", "src/missing.css"), None, "no entry stylesheet"),
                ((), str(self.tmp / "nowhere"), "cannot find tailwindcss"),
                (("--frobnicate",), None, "unknown option")):
            with self.subTest(message=message):
                proc = self.probe(*args, modules=modules)
                self.assertEqual(2, proc.returncode, output(proc))
                self.assertIn(message, output(proc))
        self.write("src/styles/index.css", '@import "./gone.css";\n')
        proc = self.probe()
        self.assertEqual(2, proc.returncode, output(proc))
        self.assertIn("gone.css", output(proc))

    @unittest.skipUnless(TAILWIND_V3, "set WDS_TAILWIND_V3_MODULES to a node_modules with tailwindcss 3")
    def test_tailwind_3_is_sent_to_the_lint_plugin(self):
        proc = self.probe(modules=TAILWIND_V3)
        self.assertEqual(2, proc.returncode, output(proc))
        self.assertIn("tailwindConfig", output(proc))


REFERENCE = SKILLS / "web-design-studio" / "references" / "stack-tailwind.md"
# Compiles one stylesheet with the given tailwindcss, as the build does, and
# prints what it generates for the candidates.
COMPILE = r"""
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
const [twDir, file, candidatesJson] = process.argv.slice(2);
const { compile } = await import(pathToFileURL(path.join(twDir, 'dist', 'lib.mjs')).href);
const loadStylesheet = async (id, base) => {
  let p;
  if (id === 'tailwindcss' || id.startsWith('tailwindcss/')) {
    let sub = id === 'tailwindcss' ? 'index.css' : id.slice('tailwindcss/'.length);
    if (!path.extname(sub)) sub += '.css';
    p = path.join(twDir, sub);
  } else p = path.resolve(base, id);
  return { path: p, base: path.dirname(p), content: fs.readFileSync(p, 'utf8') };
};
const compiler = await compile(fs.readFileSync(file, 'utf8'), { base: path.dirname(file), loadStylesheet });
process.stdout.write(compiler.build(JSON.parse(candidatesJson)));
"""


def variants_block() -> str:
    """The CSS block stack-tailwind.md §2.10 marks, as a project copies it."""
    m = re.search(r"<!-- tw-probe:variants -->\n```css\n(.*?)```", REFERENCE.read_bytes().decode("utf-8"), re.S)
    if not m:
        raise AssertionError("stack-tailwind.md marks no variants block")
    return m.group(1)


@unittest.skipUnless(NODE and TAILWIND, "set WDS_TAILWIND_MODULES to a node_modules with tailwindcss 4")
class TheVariantsTheReferenceTeaches(ProbeProject):
    """SB-B5: stack-tailwind.md §2.10, compiled as written against the
    starter's wiring: the variants v4 keeps after `--*: initial`, the ones it
    loses, and the files that need the theme from outside the entry."""

    def compile(self, rel: str, candidates=()) -> str:
        harness = self.write("compile.mjs", COMPILE)
        proc = subprocess.run([NODE, str(harness), str(Path(TAILWIND) / "tailwindcss"), str(self.tmp / rel),
                               json.dumps(list(candidates))],
                              cwd=self.tmp, capture_output=True, timeout=300, env=env())
        self.assertEqual(0, proc.returncode, output(proc))
        return proc.stdout.decode("utf-8")

    def test_each_variant_the_section_names_generates(self):
        self.add_theme(variants_block())
        expect = ["cq-wide:p-card-lg", "cq-card-wide:p-card", "@container", "@container/card",
                  "motion-safe:motion-hover", "motion-reduce:transform-none", "motion-reduce:animate-none",
                  "forced-colors:border-stroke", "starting:opacity-0", "transition-opacity",
                  "not-hover:bg-surface", "not-data-open:hidden"]
        refuse = ["@md:p-card-lg", "space-y-related", "space-x-related"]
        proc = self.probe(*[a for c in expect for a in ("--expect", c)],
                          *[a for c in refuse for a in ("--refuse", c)])
        self.assertEqual(0, proc.returncode, output(proc))

    def test_the_container_variants_are_literal_queries(self):
        self.add_theme(variants_block())
        css = self.compile("src/styles/index.css", ["cq-wide:p-card-lg", "cq-card-wide:p-card", "@container/card"])
        self.assertIn("@container (inline-size >= 40rem)", css)
        self.assertIn("@container card (inline-size >= 40rem)", css)
        self.assertRegex(css, r"container-name:\s*card")
        self.assertNotIn("max-w-", css)

    def test_inline_sources_generate_with_no_candidate(self):
        self.add_theme(variants_block())
        css = self.compile("src/styles/index.css")
        for selector in (".bg-surface", ".p-card", r".hover\:p-card"):
            with self.subTest(selector=selector):
                self.assertIn(selector + " {", css.replace(":hover", ""))

    def test_a_module_reads_the_theme_through_reference_only(self):
        """Without `@reference`, `@variant dark` compiles with no error
        against Tailwind's own dark, the media query, not the project's."""
        body = ".card { @variant dark { color: var(--fg-default); } }\n"
        self.write("src/components/card.module.css", body)
        alone = self.compile("src/components/card.module.css")
        self.assertIn("prefers-color-scheme: dark", alone)
        self.assertNotIn("data-theme", alone)
        self.write("src/components/card.module.css", '@reference "../styles/index.css";\n' + body)
        referenced = self.compile("src/components/card.module.css")
        self.assertIn('[data-theme="dark"]', referenced)
        self.assertNotIn("prefers-color-scheme", referenced)
        self.assertNotIn(".stack", referenced, "a reference emits none of the entry")
        self.write("src/components/card.module.css", '@import "../styles/index.css";\n' + body)
        imported = self.compile("src/components/card.module.css")
        self.assertIn(".stack", imported, "an import copies the entry in")
        self.assertGreater(len(imported), 30000)


MIGRATIONS = SKILLS / "design-token-migration" / "references" / "framework-migrations.md"


def migration_block(mark: str) -> str:
    """A CSS block framework-migrations.md §5 marks, as a project copies it."""
    m = re.search(rf"<!-- tw-migrate:{mark} -->\n```css\n(.*?)```", MIGRATIONS.read_bytes().decode("utf-8"), re.S)
    if not m:
        raise AssertionError(f"framework-migrations.md marks no {mark} block")
    return m.group(1)


@unittest.skipUnless(NODE and TAILWIND, "set WDS_TAILWIND_MODULES to a node_modules with tailwindcss 4")
class TheMigrationsMoveOne(ProbeProject):
    """LC-B5 (P36): framework-migrations.md §5's Move 1 in v4's form, compiled as
    written. Named keys beside `--spacing` leave every numeric class, the
    cleared theme leaves none, and the section's tw_probe command tells them apart."""

    compile = TheVariantsTheReferenceTeaches.compile
    NUMERIC = ["p-4", "gap-2.5", "-mt-4"]

    def command(self) -> list:
        m = re.search(r'tw_probe\.mjs" (.+)$', MIGRATIONS.read_bytes().decode("utf-8"), re.M)
        self.assertIsNotNone(m, "§5 gives no tw_probe command")
        return m.group(1).split()

    def generated(self, css: str, classes) -> list:
        return [c for c in classes if "." + c.replace(".", "\\.") + " {" in css]

    def test_named_keys_beside_spacing_leave_the_numeric_classes(self):
        self.write("src/styles/index.css", '@import "tailwindcss";\n' + migration_block("wrong"))
        css = self.compile("src/styles/index.css", [*self.NUMERIC, "p-card"])
        self.assertEqual(self.generated(css, [*self.NUMERIC, "p-card"]), [*self.NUMERIC, "p-card"])
        proc = self.probe(*self.command())
        self.assertEqual(1, proc.returncode, output(proc))
        for cls in self.NUMERIC:
            self.assertIn(f"{cls}: refused, but generates", output(proc))

    def test_the_cleared_theme_leaves_only_the_roles(self):
        self.write("src/styles/index.css", '@import "tailwindcss";\n' + migration_block("right"))
        roles = ["p-card", "-mt-grouped", "gap-related", "px-inline-md", "py-block-sm", "p-well"]
        css = self.compile("src/styles/index.css", [*self.NUMERIC, *roles])
        self.assertEqual(self.generated(css, [*self.NUMERIC, *roles]), roles)
        proc = self.probe(*self.command())
        self.assertEqual(0, proc.returncode, output(proc))

    def test_clearing_the_spacing_namespace_takes_spacing_with_it(self):
        self.write("src/styles/index.css", '@import "tailwindcss";\n@theme {\n  --spacing-*: initial;\n}\n')
        self.assertEqual(self.generated(self.compile("src/styles/index.css", self.NUMERIC), self.NUMERIC), [])


if __name__ == "__main__":
    unittest.main()
