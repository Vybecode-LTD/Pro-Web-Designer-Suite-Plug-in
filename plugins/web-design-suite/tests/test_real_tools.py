"""The shipped configs, run through the real tools (3.2.0; review item C4).

Each class skips unless its tool is available on the machine:

  WDS_ESLINT_MODULES    a node_modules with eslint 9+, eslint-plugin-jsx-a11y
                        and typescript-eslint; or several, separated by the
                        path separator, each package taken from the first
                        that has it (ESLint 10 from one project, jsx-a11y
                        from another)
  WDS_TAILWIND_MODULES  a node_modules with tailwindcss 4 and @tailwindcss/node
                        (tailwind-merge too, for the merge config)

Nothing is installed or downloaded. The configs are copied into a temporary
directory with their package imports pointed at those folders by absolute
URL, and nothing is written anywhere else.

Regressions covered:
- SB-A13: the ESLint `style` rule accepted only a bare object literal, so it
  refused the pattern the references teach —
  `style={{ '--progress': pct } as React.CSSProperties}` and
  `style={span ? { '--card-span': span } : undefined}`.
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import subprocess
import tempfile
import unittest

from wds_support import NODE, SKILLS, TempDirTest, output

CONFIGS = SKILLS / "web-design-studio" / "assets" / "configs"
ESLINT_ROOTS = [p for p in os.environ.get("WDS_ESLINT_MODULES", "").split(os.pathsep) if p]
ESLINT_MODULES = next((r for r in ESLINT_ROOTS
                       if (pathlib.Path(r) / "eslint" / "bin" / "eslint.js").is_file()), None)
TAILWIND_MODULES = os.environ.get("WDS_TAILWIND_MODULES")
STYLE_RULE = "design-laws/style-prop-custom-properties-only"


def entry_url(modules: str | list[str], package: str) -> str:
    """The file URL of `package`'s entry point, from the first of `modules`
    that has it."""
    code = ("const r = require('module').createRequire(process.argv[1] + '/');"
            "console.log(r.resolve(process.argv[2]))")
    for root in [modules] if isinstance(modules, str) else modules:
        proc = subprocess.run([NODE, "-e", code, root, package], capture_output=True, text=True)
        if not proc.returncode:
            return pathlib.Path(proc.stdout.strip()).as_uri()
    raise unittest.SkipTest(f"{package} is not in {modules}")


ALLOWED_STYLES = ("<div style={{ '--progress': pct } as React.CSSProperties} />",
                  "<div style={span ? { '--card-span': span } : undefined} />",
                  "<div style={open && { '--panel-h': height }} />")
REFUSED_STYLES = ("<div style={{ padding: 13 }} />",
                  "<div style={span ? { padding: 13 } : undefined} />",
                  "<div style={{ padding: 13 } as React.CSSProperties} />")
LITERAL_UTILITIES = ("duration-300", "z-50", "border-2", "bg-accent/37", "p-(--space-6)")


def component(jsx: str) -> str:
    return f"export const C = ({{ pct, span, open, height }}) => {jsx};\n"


@unittest.skipUnless(NODE and ESLINT_MODULES, "set WDS_ESLINT_MODULES to run the ESLint fixtures")
class DesignEslintConfig(unittest.TestCase):
    """Every fixture is linted in ONE ESLint run (typescript-eslint takes most
    of the time to load); each test reads its own files' results."""

    @classmethod
    def setUpClass(cls):
        from test_doc_snippets import snippets
        holder = tempfile.TemporaryDirectory(prefix="wds-eslint-", ignore_cleanup_errors=True)
        cls.addClassCleanup(holder.cleanup)
        tmp = pathlib.Path(holder.name)
        config = (CONFIGS / "eslint.design.config.mjs").read_text(encoding="utf-8")
        a11y = entry_url(ESLINT_ROOTS, "eslint-plugin-jsx-a11y")
        ts = entry_url(ESLINT_ROOTS, "typescript-eslint")
        files = {
            "eslint.design.config.mjs": config.replace("from 'eslint-plugin-jsx-a11y'", f"from '{a11y}'"),
            "eslint.config.mjs": (f"import tseslint from '{ts}';\n"
                                  "import design from './eslint.design.config.mjs';\n"
                                  "export default [\n"
                                  "  { files: ['**/*.tsx', '**/*.jsx'],\n"
                                  "    languageOptions: { parser: tseslint.parser,\n"
                                  "                       parserOptions: { ecmaFeatures: { jsx: true } } } },\n"
                                  "  ...design,\n"
                                  "];\n"),
        }
        linted = {}
        for n, jsx in enumerate(ALLOWED_STYLES):
            linted[f"src/components/Allowed{n}.tsx"] = component(jsx)
        for n, jsx in enumerate(REFUSED_STYLES):
            linted[f"src/components/Refused{n}.tsx"] = component(jsx)
        for n, cls_ in enumerate(LITERAL_UTILITIES):
            linted[f"src/components/Utility{n}.tsx"] = component(f'<div className="flex {cls_}" />')
        linted["src/components/NoAlt.tsx"] = component('<img src="/hero.png" />')
        cls.snippet_at = {}
        for n, (doc, line, lang, body) in enumerate(snippets()):
            if lang in ("tsx", "jsx"):
                name = f"src/components/Snippet{n}.{lang}"
                linted[name] = body
                cls.snippet_at[name] = f"{doc.relative_to(SKILLS)}:{line}"
        for name, text in {**files, **linted}.items():
            path = tmp / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        proc = subprocess.run([NODE, str(pathlib.Path(ESLINT_MODULES) / "eslint" / "bin" / "eslint.js"),
                               "-c", "eslint.config.mjs", "--format", "json", *linted],
                              cwd=tmp, capture_output=True, timeout=600)
        if proc.returncode not in (0, 1):
            raise AssertionError(output(proc))
        cls.messages = {pathlib.Path(r["filePath"]).relative_to(tmp).as_posix(): r["messages"]
                        for r in json.loads(proc.stdout)}

    def rules_in(self, name: str) -> list[str]:
        messages = self.messages[name]
        self.assertFalse([m for m in messages if m.get("fatal")], messages)
        return [m["ruleId"] for m in messages]

    def test_jsx_a11y_runs_under_this_eslint(self):
        """SB-A17: the header recommends ESLint 10 with an override for
        jsx-a11y's peer range; its rules must actually fire there."""
        self.assertIn("jsx-a11y/alt-text", self.rules_in("src/components/NoAlt.tsx"))

    def test_the_style_patterns_the_references_teach_are_allowed(self):
        for n, jsx in enumerate(ALLOWED_STYLES):
            with self.subTest(jsx=jsx):
                self.assertNotIn(STYLE_RULE, self.rules_in(f"src/components/Allowed{n}.tsx"))

    def test_a_plain_property_is_refused_in_every_branch(self):
        for n, jsx in enumerate(REFUSED_STYLES):
            with self.subTest(jsx=jsx):
                self.assertIn(STYLE_RULE, self.rules_in(f"src/components/Refused{n}.tsx"))

    def test_literal_utilities_are_refused(self):
        for n, cls_ in enumerate(LITERAL_UTILITIES):
            with self.subTest(cls=cls_):
                self.assertTrue(self.rules_in(f"src/components/Utility{n}.tsx"), cls_)

    def test_the_references_tsx_snippets_pass_the_design_config(self):
        """SB-C5: what a reference offers for copying passes ESLint too, not
        only the audit. A fragment the parser cannot read is left out."""
        self.assertGreater(len(self.snippet_at), 10)
        parsed = 0
        for name, where in self.snippet_at.items():
            messages = self.messages[name]
            if any(m.get("fatal") for m in messages):
                continue
            parsed += 1
            with self.subTest(snippet=where):
                self.assertEqual([], [f"{m['ruleId']}: {m['message'][:90]}" for m in messages
                                      if m.get("severity") == 2])
        self.assertGreater(parsed, 5)


TAILWIND_HARNESS = r"""
import fs from 'node:fs';
const [nodeUrl, themePath, base, candidatesJson] = process.argv.slice(2);
const { compile } = await import(nodeUrl);
const theme = fs.readFileSync(themePath, 'utf8');
// Wired as theme.css's own header says: Tailwind's theme and utilities in
// their layers, then this file.
const input = '@layer theme, utilities;\n'
  + '@import "tailwindcss/theme.css" layer(theme);\n'
  + '@import "tailwindcss/utilities.css" layer(utilities);\n' + theme;
const out = {};
for (const candidate of JSON.parse(candidatesJson)) {
  const compiler = await compile(input, { base, onDependency() {} });
  out[candidate] = compiler.build([candidate]);
}
console.log(JSON.stringify(out));
"""


@unittest.skipUnless(NODE and TAILWIND_MODULES, "set WDS_TAILWIND_MODULES to run the Tailwind fixtures")
class TailwindTheme(unittest.TestCase):
    """theme.css compiled by the real Tailwind v4 compiler, one class at a time."""

    CANDIDATES = ["border-stroke", "border-default", "border-hairline",
                  "p-4", "bg-neutral-800", "text-sm",
                  "duration-300", "z-50", "border-2",
                  "p-card", "bg-surface", "text-default", "z-modal", "motion-hover"]

    @classmethod
    def setUpClass(cls):
        holder = tempfile.TemporaryDirectory(prefix="wds-tailwind-", ignore_cleanup_errors=True)
        cls.addClassCleanup(holder.cleanup)
        harness = pathlib.Path(holder.name) / "compile.mjs"
        harness.write_text(TAILWIND_HARNESS, encoding="utf-8")
        node_url = entry_url(TAILWIND_MODULES, "@tailwindcss/node")
        proc = subprocess.run([NODE, str(harness), node_url, str(CONFIGS / "theme.css"),
                               str(pathlib.Path(TAILWIND_MODULES).parent), json.dumps(cls.CANDIDATES)],
                              capture_output=True, timeout=300)
        if proc.returncode:
            raise AssertionError(output(proc))
        cls.css = json.loads(proc.stdout)

    def declarations(self, candidate: str) -> str:
        """Every declaration in the rules for `.candidate`, in one string."""
        selector = re.escape("." + candidate.replace("/", "\\/"))
        return " ".join(re.findall(rf"{selector}\s*\{{([^}}]*)\}}", self.css[candidate]))

    def test_the_stroke_width_utility_does_not_paint(self):
        """SB-A19: `@utility border-default` shared its name with the colour
        `--color-default`, so the width utility also set the border colour to
        body text."""
        self.assertNotIn("border-width", self.declarations("border-default"))
        stroke = self.declarations("border-stroke")
        self.assertIn("border-width", stroke)
        self.assertNotIn("border-color", stroke)

    def test_off_scale_classes_generate_nothing(self):
        """SB-A12: silent, not a build error — which is why the references now
        say so, and why lint is what catches them."""
        for candidate in ("p-4", "bg-neutral-800", "text-sm"):
            with self.subTest(candidate=candidate):
                self.assertEqual("", self.declarations(candidate).strip())

    def test_literal_utilities_still_generate(self):
        """SB-A5: `--*: initial` does not remove bare-number utilities, so the
        lint rules and the audit have to."""
        for candidate in ("duration-300", "z-50", "border-2"):
            with self.subTest(candidate=candidate):
                self.assertTrue(self.declarations(candidate).strip())

    def test_the_role_classes_generate(self):
        for candidate in ("p-card", "bg-surface", "text-default", "z-modal", "motion-hover",
                          "border-hairline"):
            with self.subTest(candidate=candidate):
                self.assertIn("var(--", self.declarations(candidate))


MERGE_HARNESS = r"""
import fs from 'node:fs';
const [mergeUrl, docPath, casesJson] = process.argv.slice(2);
const { extendTailwindMerge } = await import(mergeUrl);
const doc = fs.readFileSync(docPath, 'utf8');
// The config exactly as the reference writes it: the argument of its
// extendTailwindMerge(...) call, balanced parentheses and all.
const at = doc.indexOf('extendTailwindMerge({');
let depth = 0, end = -1;
for (let i = at + 'extendTailwindMerge'.length; i < doc.length; i++) {
  if (doc[i] === '(') depth++;
  else if (doc[i] === ')' && --depth === 0) { end = i; break; }
}
const config = eval('(' + doc.slice(at + 'extendTailwindMerge('.length, end) + ')');
const merge = extendTailwindMerge(config);
const out = {};
for (const input of JSON.parse(casesJson)) out[input.join(' | ')] = merge(...input);
console.log(JSON.stringify(out));
"""


@unittest.skipUnless(NODE and TAILWIND_MODULES, "set WDS_TAILWIND_MODULES to run the tailwind-merge fixtures")
class TailwindMergeConfig(unittest.TestCase):
    """SB-A18: the config stack-tailwind.md documents, run through the real
    tailwind-merge. It classed `font-regular` as a font family, so
    `cn('font-body', 'font-regular')` dropped the family; the roles for
    leading and tracking were never registered; and `z-modal z-50` both
    survived, in a custom group beside tailwind-merge's own `z`."""

    CASES = {
        ("p-card", "p-card-lg"): "p-card-lg",                   # the doc's own checks
        ("bg-surface", "bg-raised"): "bg-raised",
        ("z-modal", "z-toast"): "z-toast",
        ("motion-hover", "motion-expand"): "motion-expand",
        ("font-body", "font-semibold"): "font-body font-semibold",   # family and weight
        ("font-regular", "font-bold"): "font-bold",
        ("leading-body", "leading-heading"): "leading-heading",
        ("tracking-ui", "tracking-allcaps"): "tracking-allcaps",
        ("z-modal", "z-50"): "z-50",                             # a role and a stock class
        ("border-hairline", "border-stroke"): "border-stroke",
    }

    @classmethod
    def setUpClass(cls):
        holder = tempfile.TemporaryDirectory(prefix="wds-merge-", ignore_cleanup_errors=True)
        cls.addClassCleanup(holder.cleanup)
        harness = pathlib.Path(holder.name) / "merge.mjs"
        harness.write_text(MERGE_HARNESS, encoding="utf-8")
        proc = subprocess.run([NODE, str(harness), entry_url(TAILWIND_MODULES, "tailwind-merge"),
                               str(SKILLS / "web-design-studio" / "references" / "stack-tailwind.md"),
                               json.dumps([list(k) for k in cls.CASES])], capture_output=True, timeout=120)
        if proc.returncode:
            raise AssertionError(output(proc))
        cls.merged = json.loads(proc.stdout)

    def test_the_documented_config_merges_the_roles(self):
        for inputs, expected in self.CASES.items():
            with self.subTest(cn=inputs):
                self.assertEqual(self.merged[" | ".join(inputs)], expected)


if __name__ == "__main__":
    unittest.main()
