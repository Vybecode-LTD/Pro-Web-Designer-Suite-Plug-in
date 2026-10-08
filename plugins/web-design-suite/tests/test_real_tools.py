"""The shipped configs, run through the real tools (3.2.0; review item C4).

Each class skips unless its tool is available on the machine. Inside the
repository, `npm ci` in tooling/main and tooling/tailwind-v3 provides all of
them: the tests use those folders for any variable that is not set, and a
variable set to `off` switches its tests off (wds_support.tool_roots):

  WDS_ESLINT_MODULES       a node_modules with eslint 9+, eslint-plugin-jsx-a11y
                           and typescript-eslint; or several, separated by the
                           path separator, each package taken from the first
                           that has it (ESLint 10 from one project, jsx-a11y
                           from another). With eslint-plugin-tailwindcss 4 and
                           tailwindcss 4 beside them, the v4 half of the
                           ESLint config's Part 5 runs too
  WDS_TAILWIND_MODULES     a node_modules with tailwindcss 4 and @tailwindcss/node
                           (tailwind-merge too, for the merge config)
  WDS_STYLELINT_MODULES    a node_modules with stylelint 17 and
                           stylelint-config-standard 40
  WDS_TAILWIND_V3_MODULES  a node_modules with eslint, eslint-plugin-tailwindcss 3
                           and tailwindcss 3, for the v3 half of Part 5

Nothing is installed or downloaded. The configs are copied into a temporary
directory, either with their package imports pointed at those folders by
absolute URL or with a link to the folder as the project's node_modules, and
nothing is written anywhere else.

Regressions covered:
- SB-A13: the ESLint `style` rule accepted only a bare object literal, so it
  refused the pattern the references teach —
  `style={{ '--progress': pct } as React.CSSProperties}` and
  `style={span ? { '--card-span': span } : undefined}`.
- 3.2.1: stylelint 17 refused the starter's own stylesheets 32 times. The
  config had no room for system colours in forced-colors mode or `100svb`;
  its inherited formatting rule refused one-line modifier tables; and its
  inherited `url()` import notation refused every import in the documented
  Tailwind entry (the references use both spellings, so the rule is off).
- 3.2.1: the v3 block of the ESLint config's Part 5 stopped ESLint ("Could
  not resolve tailwindcss"): eslint-plugin-tailwindcss 3.18 cannot look for
  tailwindcss from a relative config path. Both blocks also gave
  `p-card px-inline-md` as a contradiction, which neither plugin flags,
  because the longhand always follows the shorthand.
- 3.2.1 review, stylelint: an override for layout files, placed after the
  component one, replaced its allowlist, so `src/components/layout/*.css` and
  `packages/ui/layout.css` lost Law 2; its geometry regex backtracked for
  hours on a long number; system colours and a hand-built box-shadow ring
  were allowed in every file, and system colours only in PascalCase; token
  files lost the duplicate-selector check.
- 3.2.1 review, Part 5: the v3 path was resolved from wherever ESLint runs,
  which ESLint 10 no longer ties to the config's folder (a monorepo root
  crashed it); both blocks reported every class of the starter's own CSS;
  the v3 whitelist hid typos of the utilities the plugin already knew; the
  helper fixture used `cn`, a default, so the v4 `functions` list went
  untested.
"""
from __future__ import annotations

import dataclasses
import json
import os
import pathlib
import re
import subprocess
import unittest

from test_rules_spec import hold_to_the_spec, spec_examples
from wds_support import (NODE, SKILLS, TOOLING_MAIN, TOOLING_V3, class_temp_dir, env, load_script, output,
                         run_py, tailwind_part5, tool_modules, tool_roots)

CONFIGS = SKILLS / "web-design-studio" / "assets" / "configs"
ESLINT_ROOTS = tool_roots("WDS_ESLINT_MODULES", TOOLING_MAIN)
ESLINT_MODULES = next((r for r in ESLINT_ROOTS
                       if (pathlib.Path(r) / "eslint" / "bin" / "eslint.js").is_file()), None)
TAILWIND_MODULES = tool_modules("WDS_TAILWIND_MODULES", "tailwindcss", "@tailwindcss/node")
STYLELINT_MODULES = tool_modules("WDS_STYLELINT_MODULES", "stylelint", "stylelint-config-standard")
STYLE_RULE = "design-laws/style-prop-custom-properties-only"
STARTER_STYLES = SKILLS / "web-design-studio" / "assets" / "starter" / "styles"
# The spec comes from this suite's own plugin, as in test_rules_spec.
SPEC = json.loads((pathlib.Path(__file__).resolve().parents[1] / "skills" / "web-design-studio" / "assets"
                   / "rules" / "design-rules.json").read_text(encoding="utf-8"))


def entry_url(modules: str | list[str], package: str) -> str:
    """The file URL of `package`'s entry point, from the first of `modules`
    that has it."""
    code = ("const r = require('module').createRequire(process.argv[1] + '/');"
            "console.log(r.resolve(process.argv[2]))")
    for root in [modules] if isinstance(modules, str) else modules:
        proc = subprocess.run([NODE, "-e", code, root, package], capture_output=True, text=True, env=env())
        if not proc.returncode:
            return pathlib.Path(proc.stdout.strip()).as_uri()
    raise unittest.SkipTest(f"{package} is not in {modules}")


def package_major(root: str, package: str) -> int | None:
    try:
        manifest = json.loads((pathlib.Path(root) / package / "package.json").read_text(encoding="utf-8"))
        return int(manifest["version"].split(".")[0])
    except (OSError, ValueError, KeyError):
        return None


def tailwind_lint_modules(roots: list[str], major: int) -> str | None:
    """The first of `roots` holding ESLint with eslint-plugin-tailwindcss and
    tailwindcss, both of `major`."""
    return next((r for r in roots if package_major(r, "eslint")
                 and package_major(r, "eslint-plugin-tailwindcss") == major
                 and package_major(r, "tailwindcss") == major), None)


TAILWIND_V4_LINT = tailwind_lint_modules(ESLINT_ROOTS, 4)
TAILWIND_V3_LINT = tailwind_lint_modules(tool_roots("WDS_TAILWIND_V3_MODULES", TOOLING_V3), 3)


def temp_project(cls, prefix: str, modules: str) -> pathlib.Path:
    """A temporary project whose node_modules is a link to `modules`, so the
    tools resolve every package exactly as a real project does: a directory
    junction on Windows (it needs no privilege), a symlink elsewhere. The link
    is removed first, so cleaning up never reaches the folder it points at."""
    tmp = class_temp_dir(cls, prefix)
    target, link = pathlib.Path(modules).resolve(), tmp / "node_modules"
    if os.name == "nt":
        import _winapi
        _winapi.CreateJunction(str(target), str(link))
        cls.addClassCleanup(os.rmdir, link)        # the junction, not its target
    else:
        link.symlink_to(target, target_is_directory=True)
        cls.addClassCleanup(link.unlink)
    return tmp


def json_report(proc: subprocess.CompletedProcess) -> list | None:
    """The JSON array a linter printed, from whichever stream holds it and
    wherever it starts, so a Node warning printed ahead of it cannot hide it."""
    for stream in (proc.stdout, proc.stderr):
        text = stream.decode("utf-8", "replace")
        for start in re.finditer(r"^\[", text, re.M):
            try:
                return json.JSONDecoder().raw_decode(text, start.start())[0]
            except ValueError:
                continue
    return None


def write_files(root: pathlib.Path, files: dict[str, str]) -> None:
    """Each file with LF line endings, byte for byte as the plugin ships them."""
    for name, text in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode("utf-8"))


# The canonical entries (SB-C9): the starter's index.css is linted with the rest of
# the starter, and the Tailwind v4 and v3 entries live with the configs.
CANONICAL_ENTRIES = {"src/tailwind/index.css": CONFIGS / "index.tailwind.css",
                     "src/tailwind-v3/index.css": CONFIGS / "index.tailwind-v3.css"}


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
        tmp = class_temp_dir(cls, "wds-eslint-")
        config = (CONFIGS / "eslint.design.config.mjs").read_text(encoding="utf-8")
        a11y = entry_url(ESLINT_ROOTS, "eslint-plugin-jsx-a11y")
        ts = entry_url(ESLINT_ROOTS, "typescript-eslint")
        files = {
            "eslint.design.config.mjs": config.replace("from 'eslint-plugin-jsx-a11y'", f"from '{a11y}'"),
            "project_config.mjs": (CONFIGS / "project_config.mjs").read_text(encoding="utf-8"),
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
        linted.update({ex.name: ex.text for ex in spec_examples() if "eslint" in ex.gates})
        cls.snippet_at = {}
        for n, (doc, line, lang, body) in enumerate(snippets()):
            if lang in ("tsx", "jsx"):
                name = f"src/components/Snippet{n}.{lang}"
                linted[name] = body
                cls.snippet_at[name] = f"{doc.relative_to(SKILLS)}:{line}"
        write_files(tmp, {**files, **linted})
        proc = subprocess.run([NODE, str(pathlib.Path(ESLINT_MODULES) / "eslint" / "bin" / "eslint.js"),
                               "-c", "eslint.config.mjs", "--format", "json", *linted],
                              cwd=tmp, capture_output=True, timeout=600, env=env())
        if proc.returncode not in (0, 1):
            raise AssertionError(output(proc))
        cls.messages = {pathlib.Path(r["filePath"]).resolve().relative_to(tmp).as_posix(): r["messages"]
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

    def test_every_example_of_the_spec(self):
        """N2: every example of every section ESLint enforces (test_rules_spec)."""
        def problems_of(ex):
            messages = self.messages[ex.name]
            return ([str(m["ruleId"]) for m in messages if m.get("severity") == 2],
                    [f"{m['ruleId']} ({m.get('severity')})" for m in messages])
        hold_to_the_spec(self, "eslint", problems_of)

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
        harness = class_temp_dir(cls, "wds-tailwind-") / "compile.mjs"
        harness.write_text(TAILWIND_HARNESS, encoding="utf-8")
        node_url = entry_url(TAILWIND_MODULES, "@tailwindcss/node")
        proc = subprocess.run([NODE, str(harness), node_url, str(CONFIGS / "theme.css"),
                               str(pathlib.Path(TAILWIND_MODULES).parent), json.dumps(cls.CANDIDATES)],
                              capture_output=True, timeout=300, env=env())
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
        harness = class_temp_dir(cls, "wds-merge-") / "merge.mjs"
        harness.write_text(MERGE_HARNESS, encoding="utf-8")
        proc = subprocess.run([NODE, str(harness), entry_url(TAILWIND_MODULES, "tailwind-merge"),
                               str(SKILLS / "web-design-studio" / "references" / "stack-tailwind.md"),
                               json.dumps([list(k) for k in cls.CASES])], capture_output=True, timeout=120, env=env())
        if proc.returncode:
            raise AssertionError(output(proc))
        cls.merged = json.loads(proc.stdout)

    def test_the_documented_config_merges_the_roles(self):
        for inputs, expected in self.CASES.items():
            with self.subTest(cn=inputs):
                self.assertEqual(self.merged[" | ".join(inputs)], expected)


def in_layer(layer: str, css: str) -> str:
    return f"@layer {layer} {{\n{css}\n}}\n"


ALLOWED_LIST = "declaration-property-value-allowed-list"
MARGIN_RULE = "design/component-margins"
TIER_RULE = "design/tier1-primitive"

# Fixtures for the stylelint config: a file of the project and, for a refusal,
# the rule that must report it.
REFUSED_CSS = {
    "src/components/Literal.css": (in_layer("components", ".card { padding: 13px; }"), ALLOWED_LIST),
    "src/components/Hex.css": (in_layer("components", ".card { color: #fff; }"), "design/color-no-hex"),
    "src/components/Important.css": (in_layer("components", ".card { color: var(--fg-default) !important; }"),
                                     "declaration-no-important"),
    "src/components/Id.css": (in_layer("components", "#card { color: var(--fg-default); }"), "selector-max-id"),
    "src/components/Multiplied.css": (in_layer("components", ".card { padding: calc(var(--space-4) * 1.5); }"),
                                      ALLOWED_LIST),
    "src/components/Geometry.css": (
        in_layer("components", ".card { max-inline-size: calc(100% - var(--gutter-page) * 2); }"), ALLOWED_LIST),
    "src/components/OwnMargin.css": (in_layer("components", ".card { margin-block-start: var(--gap-related); }"),
                                     MARGIN_RULE),
    "src/components/Apply.css": (in_layer("components", ".card { @apply p-card; }"), "at-rule-disallowed-list"),
    # 3.2.1 review. A component in a layout folder is still a component (Law 2):
    # an override for layout files, after the component one, took Law 2 away.
    "src/components/layout/Header.css": (
        in_layer("components", ".header { margin-block-start: var(--gap-related); }"), MARGIN_RULE),
    "packages/ui/layout.css": (in_layer("components", ".panel { margin-block-start: 1.5rem; }"), MARGIN_RULE),
    # A layout file may not multiply a token either (Law 3) ...
    "src/styles/layout/Factor.css": (
        in_layer("layout", ".center { padding-inline: calc(var(--space-4) * 1.5); }"), ALLOWED_LIST),
    # ... and refusing a long number is quick: that override's regex backtracked
    # for hours on a 30-digit run.
    "src/styles/layout/Digits.css": (
        in_layer("layout", ".c { max-inline-size: calc(33." + "3" * 30 + "% - 1rem); }"), ALLOWED_LIST),
    # A ring drawn as a box-shadow vanishes in forced-colors mode; a component
    # keeps the outline and reads --elevation-focus (token-contract.md).
    "src/components/Ring.css": (
        in_layer("components", ".btn:focus-visible { outline: none; "
                               "box-shadow: 0 0 0 var(--stroke-focus) var(--border-focus); }"), ALLOWED_LIST),
    # P45: Law 6 reads a `components` layer in any file, and the whole of a
    # component file, layered or not, as the audit does.
    "src/styles/page.css": (in_layer("components", ".card { padding: var(--space-4); }"), TIER_RULE),
    "src/components/Unlayered.css": (".card { gap: var(--space-2); }\n", TIER_RULE),
    # A second dark block that silently redefines a token.
    "src/styles/brand-tokens.css": (':root { --x: var(--space-4); }\n[data-theme="dark"] { --y: var(--x); }\n'
                                    '[data-theme="dark"] { --y: var(--x); }\n', "no-duplicate-selectors"),
    **{f"src/components/SystemColour{n}.css": (in_layer("components", css), "design/system-colors-in-forced-colors")
       for n, css in enumerate(SPEC["system_colors"]["refused"])},
    # SB-A8: the order, and a layer imported into but not stated.
    **{f"src/entries/refused{n}/index.css": (css + "\n", "design/layer-order")
       for n, css in enumerate(SPEC["layers"]["refused"])},
}
ALLOWED_CSS = {
    "src/components/SmallViewport.css": in_layer("components", ".card { min-block-size: 100svb; }"),
    "src/components/Cancel.css": in_layer("components", ".card { margin-block-start: calc(var(--card-inset) * -1); }"),
    # N3: what stack-css-modules.md teaches, in a CSS Module.
    "src/components/Button.module.css": in_layer(
        "components", ".primary { composes: root from './Base.module.css'; }\n"
                      ":global(.is-open) .primary { --button-bg: var(--bg-accent); }"),
    # Geometry over tokens goes in a socket, as the starter's layout.css does.
    "src/styles/layout/Socket.css": in_layer(
        "layout", ".center { --center-box: calc(var(--center-max) + var(--center-gutter) * 2); "
                  "max-inline-size: var(--center-box); }"),
    # P45: a token file defines Tier 2 from Tier 1; the audit skips it too, and
    # in a component folder too: there the token or theme override has the last
    # word (Codex on #73).
    "src/styles/brand/tokens.css": in_layer("tokens", ":root { --pad-card: var(--space-4); }"),
    "src/components/tokens.css": in_layer("tokens", ":root { --pad-card: var(--space-4); }"),
    "packages/ui/theme.css": "@theme inline {\n  --spacing-card: var(--space-4);\n}\n",
    **{f"src/components/ForcedColours{n}.css": in_layer("components", css)
       for n, css in enumerate(SPEC["system_colors"]["allowed"])},
    **{f"src/entries/allowed{n}/index.css": css + "\n" for n, css in enumerate(SPEC["layers"]["allowed"])},
}


@unittest.skipUnless(NODE and STYLELINT_MODULES, "set WDS_STYLELINT_MODULES to run the stylelint fixtures")
class StylelintConfig(unittest.TestCase):
    """stylelint.config.mjs as shipped, run by the real stylelint over the
    starter's own stylesheets, the documented entries and the fixtures above.
    Every file is linted in one run; each test reads its own."""

    @classmethod
    def setUpClass(cls):
        from test_doc_snippets import as_files, snippets
        tmp = temp_project(cls, "wds-stylelint-", STYLELINT_MODULES)
        files = {"stylelint.config.mjs": (CONFIGS / "stylelint.config.mjs").read_text(encoding="utf-8"),
                 "project_config.mjs": (CONFIGS / "project_config.mjs").read_text(encoding="utf-8"),
                 **{name: path.read_text(encoding="utf-8") for name, path in CANONICAL_ENTRIES.items()
                    if path.is_file()},
                 **{f"src/styles/{css.name}": css.read_text(encoding="utf-8")
                    for css in sorted(STARTER_STYLES.glob("*.css"))},
                 "src/tailwind/theme.css": (CONFIGS / "theme.css").read_text(encoding="utf-8"),
                 **{name: css for name, (css, _) in REFUSED_CSS.items()},
                 **ALLOWED_CSS,
                 **{ex.name: ex.text for ex in spec_examples() if "stylelint" in ex.gates}}
        # N3: each CSS block of the references, in the files the audit puts it in
        # (test_doc_snippets.as_files): its tokens, its layer's file, a component.
        cls.snippet_files = {}
        for n, (doc, line, lang, body) in enumerate(snippets()):
            if lang == "css":
                parts = {f"src/snippets/b{n}/{name}": text for name, text in as_files(lang, body)}
                files.update(parts)
                cls.snippet_files[f"{doc.relative_to(SKILLS).as_posix()}:{line}"] = list(parts)
        write_files(tmp, files)
        linted = [name for name in files if name.endswith(".css")]
        proc = subprocess.run([NODE, str(pathlib.Path(STYLELINT_MODULES) / "stylelint" / "bin" / "stylelint.mjs"),
                               *linted, "--config", "stylelint.config.mjs", "--formatter", "json"],
                              cwd=tmp, capture_output=True, timeout=300, env=env())
        # 0: clean, 2: problems found. stylelint 17 writes the JSON report to
        # stderr, clean or not.
        report = json_report(proc)
        if proc.returncode not in (0, 2) or report is None:
            raise AssertionError(output(proc))
        cls.results = {pathlib.Path(r["source"]).resolve().relative_to(tmp).as_posix(): r for r in report}

    def problems(self, name: str) -> list[str]:
        result = self.results[name]
        self.assertEqual([], result.get("invalidOptionWarnings", []), name)
        self.assertEqual([], result.get("parseErrors", []), name)
        return [f"{w['line']}:{w['column']} {w['rule']}" for w in result["warnings"]]

    def test_the_starter_passes_its_own_config(self):
        for css in sorted(STARTER_STYLES.glob("*.css")):
            with self.subTest(file=css.name):
                self.assertEqual([], self.problems(f"src/styles/{css.name}"))

    def test_the_canonical_entries_pass(self):
        for name, path in CANONICAL_ENTRIES.items():
            with self.subTest(entry=path.name):
                self.assertTrue(path.is_file(), path)
                self.assertEqual([], self.problems(name))

    def test_theme_css_passes_the_override_that_guards_it(self):
        """SB-A15: the theme-file override switched the allowlist off, so a binding
        to 28px or oklch() passed the file stack-tailwind.md says the gate guards.
        Its custom properties now take the spec's bindings, and theme.css's own
        `--animate-*` read the motion tokens instead of 1s and 2s."""
        self.assertEqual([], self.problems("src/tailwind/theme.css"))

    def test_what_the_laws_refuse_is_refused(self):
        for name, (_, rule) in REFUSED_CSS.items():
            with self.subTest(file=name):
                self.assertIn(rule, [p.split(" ", 1)[1] for p in self.problems(name)])

    def test_what_the_laws_allow_is_allowed(self):
        for name in ALLOWED_CSS:
            with self.subTest(file=name):
                self.assertEqual([], self.problems(name))

    def test_every_example_of_the_spec(self):
        """N2: every example of every section stylelint enforces (test_rules_spec)."""
        def problems_of(ex):
            problems = self.problems(ex.name)
            return problems, problems
        hold_to_the_spec(self, "stylelint", problems_of)

    def test_the_references_css_snippets_pass_the_config(self):
        """N3: what a reference offers for copying passes stylelint too, not only
        the audit (SB-C5 did ESLint's half). At 3.2.1, 56 of 170 blocks failed.
        A fragment stylelint cannot parse is left out, and counted."""
        self.assertGreater(len(self.snippet_files), 150)
        fragments = 0
        for where, names in self.snippet_files.items():
            if any(w["rule"] == "CssSyntaxError" for name in names for w in self.results[name]["warnings"]):
                fragments += 1
                continue
            with self.subTest(snippet=where):
                self.assertEqual([], [f"{name.split('/', 3)[3]} {p}" for name in names
                                      for p in self.problems(name)])
        self.assertLess(fragments, len(self.snippet_files) // 10)


# N37: a project's .design-suite.json, which the audit read and the lint
# configs did not, so a component under `src/widgets/` reading `--brand-500`
# failed the audit and passed stylelint.
PROJECT_CONFIG = json.dumps({"schema": 1, "tokens": "src/brand/palette.css", "components": ["src/widgets/**"]})
PROJECT_FILES = {
    # A token file the config names: literals live here (Law 1).
    "src/brand/palette.css": ("@layer tokens {\n  :root {\n    --brand-500: oklch(62% 0.19 45);\n"
                              "    --brand-600: #b4400a;\n    --bg-brand: var(--brand-500);\n  }\n}\n"),
    # A component by the config's glob, reading one of the project's ramp steps (Law 6). In
    # the layout layer, so only the file's class makes it a component.
    "src/widgets/card.css": "@layer layout {\n  .card {\n    color: var(--brand-500);\n  }\n}\n",
    # A component by the glob that pushes its sibling and styles an element (Law 2).
    "src/widgets/note.css": ("@layer layout {\n  .note {\n    margin-block-start: var(--gap-related);\n  }\n\n"
                             "  .note p {\n    color: var(--fg-default);\n  }\n}\n"),
    # Outside the globs, the components layer decides (Law 6).
    "src/styles/app.css": "@layer components {\n  .app {\n    color: var(--brand-600);\n  }\n}\n",
    "src/widgets/Card.jsx": 'export const Card = () => <div className="bg-(--brand-500)" />;\n',
    "src/widgets/Badge.jsx": "export const Badge = () => <div style={{ '--badge-fg': 'var(--brand-600)' }} />;\n",
    "src/widgets/Note.jsx": 'export const Note = () => <div className="mt-related" />;\n',
    "src/pages/Home.jsx": 'export const Home = () => <div className="mt-related" />;\n',
}
PROJECT_STYLELINT = {"src/brand/palette.css": [], "src/widgets/card.css": ["design/tier1-primitive"],
                     "src/widgets/note.css": ["design/component-margins", "selector-max-type"],
                     "src/styles/app.css": ["design/tier1-primitive"]}
PROJECT_ESLINT = {"src/widgets/Card.jsx": ["no-restricted-syntax"],
                  "src/widgets/Badge.jsx": ["design-laws/style-prop-custom-properties-only"],
                  "src/widgets/Note.jsx": ["no-restricted-syntax"], "src/pages/Home.jsx": []}
LAW_OF = {"design/tier1-primitive": "L6", "design/component-margins": "L2", "selector-max-type": "L2",
          "declaration-property-value-allowed-list": "L1", "design/color-no-hex": "L1",
          "design/no-literal-colour-function": "L1"}
OVERRIDE_JS = """
import { overrideGlobs } from %s;
import { compileOverrideMatchers } from %s;
const [root, data] = process.argv.slice(1);
const { globs, files } = JSON.parse(data);
console.log(JSON.stringify(globs.map((glob) => {
  const [override] = compileOverrideMatchers([{ files: overrideGlobs(root, glob), rules: {} }], root);
  return files.map((file) => override.matches(file));
})));
"""


@unittest.skipUnless(NODE and STYLELINT_MODULES and ESLINT_MODULES,
                     "set WDS_STYLELINT_MODULES and WDS_ESLINT_MODULES to run the project's own config")
class TheGatesReadTheProject(unittest.TestCase):
    """N37: stylelint and the ESLint config read a project's .design-suite.json
    as the audit does: its token files are token files, its `components` globs
    join the component files, and its ramp steps are primitives with a role.
    The same files in a project without the config are the control: they pass
    as they did before."""

    @classmethod
    def setUpClass(cls):
        cls.stylelint, cls.eslint, cls.audit = {}, {}, {}
        a11y = entry_url(ESLINT_ROOTS, "eslint-plugin-jsx-a11y")
        design = (CONFIGS / "eslint.design.config.mjs").read_text(encoding="utf-8")
        tools = {"stylelint.config.mjs": (CONFIGS / "stylelint.config.mjs").read_text(encoding="utf-8"),
                 "project_config.mjs": (CONFIGS / "project_config.mjs").read_text(encoding="utf-8"),
                 "eslint.design.config.mjs": design.replace("from 'eslint-plugin-jsx-a11y'", f"from '{a11y}'"),
                 "eslint.config.mjs": ("import design from './eslint.design.config.mjs';\n"
                                       "export default [\n"
                                       "  { files: ['**/*.jsx'], languageOptions: { parserOptions: "
                                       "{ ecmaFeatures: { jsx: true } } } },\n"
                                       "  ...design,\n];\n")}
        for kind, config in (("config", {".design-suite.json": PROJECT_CONFIG}), ("none", {})):
            tmp = temp_project(cls, f"wds-project-{kind}-", STYLELINT_MODULES)
            write_files(tmp, {**tools, **config, **PROJECT_FILES})
            css = [n for n in PROJECT_FILES if n.endswith(".css")]
            jsx = [n for n in PROJECT_FILES if n.endswith(".jsx")]
            proc = subprocess.run([NODE, str(pathlib.Path(STYLELINT_MODULES) / "stylelint" / "bin" / "stylelint.mjs"),
                                   *css, "--config", "stylelint.config.mjs", "--formatter", "json"],
                                  cwd=tmp, capture_output=True, timeout=300, env=env())
            report = json_report(proc)
            if proc.returncode not in (0, 2) or report is None:
                raise AssertionError(output(proc))
            cls.stylelint[kind] = {pathlib.Path(r["source"]).resolve().relative_to(tmp.resolve()).as_posix():
                                   sorted({w["rule"] for w in r["warnings"]}) for r in report}
            proc = subprocess.run([NODE, str(pathlib.Path(ESLINT_MODULES) / "eslint" / "bin" / "eslint.js"),
                                   "-c", "eslint.config.mjs", "--format", "json", *jsx],
                                  cwd=tmp, capture_output=True, timeout=300, env=env())
            if proc.returncode not in (0, 1):
                raise AssertionError(output(proc))
            cls.eslint[kind] = {pathlib.Path(r["filePath"]).resolve().relative_to(tmp.resolve()).as_posix():
                                sorted({str(m["ruleId"]) for m in r["messages"]}) for r in json.loads(proc.stdout)}
            proc = run_py("web-design-studio", "audit_design", "src", "--json", cwd=tmp)
            if proc.returncode not in (0, 1):
                raise AssertionError(output(proc))
            cls.audit[kind] = sorted({(f["file"].replace("\\", "/").split("src/")[-1], f["law"])
                                      for f in json.loads(proc.stdout)})

    def test_stylelint_reads_the_projects_config(self):
        self.assertEqual(PROJECT_STYLELINT, self.stylelint["config"])

    def test_eslint_reads_the_projects_config(self):
        self.assertEqual(PROJECT_ESLINT, self.eslint["config"])

    def test_the_audit_and_stylelint_agree_on_each_stylesheet(self):
        """The reference: the audit finds each law broken in a stylesheet
        exactly where stylelint does, with the config and without it."""
        for kind in ("config", "none"):
            with self.subTest(project=kind):
                self.assertEqual(sorted({(n.split("src/")[-1], LAW_OF[rule])
                                         for n, rules in self.stylelint[kind].items() for rule in rules}),
                                 [(n, law) for n, law in self.audit[kind] if n.endswith(".css")])

    def test_without_the_config_nothing_changes(self):
        """The control: no ramp of the project's is a primitive, no folder of
        its a component folder, and its palette is not a token file."""
        self.assertEqual({"src/brand/palette.css": ["design/color-no-hex", "design/no-literal-colour-function"],
                          "src/widgets/card.css": [], "src/widgets/note.css": [], "src/styles/app.css": []},
                         self.stylelint["none"])
        self.assertEqual({name: [] for name in PROJECT_ESLINT}, self.eslint["none"])

    def test_the_override_globs_match_what_the_audit_does(self):
        """stylelint's overrides take globs, and micromatch's `**` differs from
        the config's, so each glob is translated (overrideGlobs). Run through
        stylelint's own matcher, it matches exactly what is_component does."""
        from test_project_config import GLOB_PATHS, GLOBS
        tmp = class_temp_dir(type(self), "wds-globs-")
        (tmp / ".design-suite.json").write_bytes(b'{"schema": 1}')
        config = load_script("web-design-studio", "project_config").load_config(tmp / ".design-suite.json")
        files = [str(config.root / rel) for rel in GLOB_PATHS] + [str(config.root.parent / "src" / "a.css")]
        augment = (pathlib.Path(STYLELINT_MODULES) / "stylelint" / "lib" / "augmentConfig.mjs").as_uri()
        script = OVERRIDE_JS % (json.dumps((CONFIGS / "project_config.mjs").as_uri()), json.dumps(augment))
        proc = subprocess.run([NODE, "--input-type=module", "-e", script, str(config.root),
                               json.dumps({"globs": GLOBS, "files": files})],
                              capture_output=True, timeout=60, env=env())
        self.assertEqual(0, proc.returncode, output(proc))
        for glob, answers in zip(GLOBS, json.loads(proc.stdout)):
            one = dataclasses.replace(config, components=[glob])
            with self.subTest(glob=glob):
                self.assertEqual([one.is_component(f) for f in files], answers)


def documented_examples(block: str, rule: str) -> list[str]:
    """The backticked examples in the comment right above `rule` in `block`."""
    lines = block.splitlines()
    at = next(n for n, line in enumerate(lines) if f"'{rule}'" in line)
    comment = []
    for line in reversed(lines[:at]):
        if not line.strip().startswith("//"):
            break
        comment.insert(0, line)
    return re.findall(r"`([^`]+)`", " ".join(comment))


JSX_FIXTURE = "export const {name} = ({{ cx }}) => <div {attr} />;\n"
TAILWIND_PART5 = tailwind_part5((CONFIGS / "eslint.design.config.mjs").read_text(encoding="utf-8"))


class TailwindPluginBlock:
    """One block of the ESLint config's Part 5, uncommented with the lines the
    blocks share, run by the real eslint-plugin-tailwindcss in a project wired
    as the docs say. ESLint runs from the folder above the project, as it does
    from a monorepo root or a git hook: ESLint 10 loads a config from whichever
    folder it lints. The fixtures for the contradiction and shorthand rules are
    the examples the block's own comments give."""

    MAJOR = CONST = MODULES = None
    EXTRA: dict[str, str] = {}

    @classmethod
    def tailwind_files(cls) -> dict[str, str]:
        raise NotImplementedError

    @classmethod
    def setUpClass(cls):
        tmp = temp_project(cls, "wds-twlint-", cls.MODULES)
        shared, blocks = TAILWIND_PART5
        block = blocks[cls.MAJOR]
        conflict, *not_conflict = documented_examples(block, "tailwindcss/no-contradicting-classname")
        cls.shorthand, cls.merged = documented_examples(block, "tailwindcss/enforces-shorthand")[:2]
        cls.cases = {"Roles": 'className="p-card bg-surface text-default"',
                     "Misspelt": 'className="p-card bg-surfce"',
                     "OffScale": 'className="p-4 bg-neutral-800"',
                     # `cx` is in both blocks' helper lists and in neither plugin's defaults.
                     "Helper": "className={cx('bg-surfce', 'p-card')}",
                     "Conflict": f'className="{conflict}"',
                     "Shorthand": f'className="{cls.shorthand}"',
                     # Classes the starter's own CSS defines, and a typo of one.
                     "Starter": 'className="stack cluster--tight with-sidebar__rail u-isolate"',
                     "StarterTypo": 'className="stak"',
                     **({"NotAConflict": f'className="{not_conflict[0]}"'} if not_conflict else {}),
                     **cls.EXTRA}
        files = {"app/package.json": '{ "name": "app", "private": true }\n',
                 "app/eslint.config.mjs": (
                     "import tailwind from 'eslint-plugin-tailwindcss';\n" + shared + block
                     + "export default [\n"
                       "  { files: ['**/*.jsx'], languageOptions: { parserOptions: { ecmaFeatures: { jsx: true } } } },\n"
                       f"  {cls.CONST},\n];\n"),
                 **{f"app/{name}": text for name, text in cls.tailwind_files().items()}}
        for name, attr in cls.cases.items():
            files[f"app/src/components/{name}.jsx"] = JSX_FIXTURE.format(name=name, attr=attr)
        write_files(tmp, files)
        proc = subprocess.run([NODE, str(pathlib.Path(cls.MODULES) / "eslint" / "bin" / "eslint.js"),
                               "-c", "app/eslint.config.mjs", "--format", "json", "app/src/components"],
                              cwd=tmp, capture_output=True, timeout=300, env=env())
        if proc.returncode not in (0, 1):
            raise AssertionError(output(proc))
        cls.messages = {pathlib.Path(r["filePath"]).stem: r["messages"] for r in json.loads(proc.stdout)}

    def rules_in(self, name: str) -> list[str]:
        messages = self.messages[name]
        self.assertFalse([m for m in messages if m.get("fatal")], messages)
        return [m["ruleId"] for m in messages]

    def test_the_role_classes_pass(self):
        self.assertEqual([], self.rules_in("Roles"))

    def test_a_class_the_theme_does_not_generate_is_refused(self):
        for name in ("Misspelt", "OffScale"):
            with self.subTest(fixture=self.cases[name]):
                self.assertIn("tailwindcss/no-custom-classname", self.rules_in(name))

    def test_class_helpers_are_read(self):
        self.assertIn("tailwindcss/no-custom-classname", self.rules_in("Helper"))

    def test_the_documented_contradiction_is_caught(self):
        self.assertIn("tailwindcss/no-contradicting-classname", self.rules_in("Conflict"),
                      self.cases["Conflict"])

    def test_what_the_comment_calls_no_contradiction_is_not_flagged(self):
        if "NotAConflict" not in self.cases:
            self.skipTest("the comment names no non-conflict")
        self.assertNotIn("tailwindcss/no-contradicting-classname", self.rules_in("NotAConflict"))

    def test_the_documented_shorthand_is_suggested(self):
        messages = [m["message"] for m in self.messages["Shorthand"]
                    if m["ruleId"] == "tailwindcss/enforces-shorthand"]
        self.assertTrue(messages, self.cases["Shorthand"])
        self.assertIn(self.merged, " ".join(messages))

    def test_the_starters_own_classes_pass_and_a_typo_does_not(self):
        """3.2.1 review: both blocks reported every layout primitive (`stack`,
        `cluster`) as an unknown class."""
        self.assertEqual([], self.rules_in("Starter"))
        self.assertIn("tailwindcss/no-custom-classname", self.rules_in("StarterTypo"))


@unittest.skipUnless(NODE and TAILWIND_V4_LINT,
                     "set WDS_ESLINT_MODULES to a node_modules with eslint-plugin-tailwindcss 4 and tailwindcss 4")
class TailwindPluginV4(TailwindPluginBlock, unittest.TestCase):
    MAJOR = 4
    CONST = "tailwindConfig"
    MODULES = TAILWIND_V4_LINT

    @classmethod
    def tailwind_files(cls) -> dict[str, str]:
        files = {"src/styles/index.css": (CONFIGS / "index.tailwind.css").read_text(encoding="utf-8"),
                 "src/styles/theme.css": (CONFIGS / "theme.css").read_text(encoding="utf-8"),
                 "src/styles/components/card.css": "@layer components {}\n"}
        for name in ("tokens.css", "base.css", "layout.css"):
            files[f"src/styles/{name}"] = (STARTER_STYLES / name).read_text(encoding="utf-8")
        return files


@unittest.skipUnless(NODE and TAILWIND_V3_LINT,
                     "set WDS_TAILWIND_V3_MODULES to run the Tailwind v3 plugin fixtures")
class TailwindPluginV3(TailwindPluginBlock, unittest.TestCase):
    MAJOR = 3
    CONST = "tailwindV3Config"
    MODULES = TAILWIND_V3_LINT
    EXTRA = {"Arbitrary": 'className="p-[13px]"',
             # The utilities tailwind.config.ts adds with addUtilities, and a
             # typo of one: 3.x learns them from the config, so no whitelist
             # entry may hide the typo.
             "Utilities": 'className="focus-ring tap-target motion-hover page-gutter grid-layout"',
             "UtilityTypo": 'className="motion-hovr"'}

    @classmethod
    def tailwind_files(cls) -> dict[str, str]:
        return {"tailwind.config.ts": (CONFIGS / "tailwind.config.ts").read_text(encoding="utf-8")}

    def test_arbitrary_values_are_refused(self):
        self.assertIn("tailwindcss/no-arbitrary-value", self.rules_in("Arbitrary"))

    def test_the_configs_own_utilities_pass_and_a_typo_does_not(self):
        self.assertEqual([], self.rules_in("Utilities"))
        self.assertIn("tailwindcss/no-custom-classname", self.rules_in("UtilityTypo"))


@unittest.skipUnless(NODE, "needs node to read the config's ownClasses")
class OwnClassesCoverTheStarter(unittest.TestCase):
    """Part 5's `ownClasses` covers every class the starter's layout.css
    defines, so the list cannot fall behind the file it describes."""

    def test_every_class_in_layout_css_is_listed(self):
        shared, _ = TAILWIND_PART5
        proc = subprocess.run([NODE, "--input-type=module", "-e",
                               shared + "\nconsole.log(JSON.stringify(ownClasses));"],
                              capture_output=True, timeout=60, env=env())
        self.assertEqual(0, proc.returncode, output(proc))
        patterns = [re.compile(f"(?:{p})") for p in json.loads(proc.stdout)]
        css = re.sub(r"/\*.*?\*/", "", (STARTER_STYLES / "layout.css").read_text(encoding="utf-8"), flags=re.S)
        classes = sorted(set(re.findall(r"(?<![\w-])\.([a-z][a-z0-9_-]*)", css)))
        self.assertGreater(len(classes), 50)
        self.assertEqual([], [c for c in classes if not any(p.fullmatch(c) for p in patterns)])


if __name__ == "__main__":
    unittest.main()
