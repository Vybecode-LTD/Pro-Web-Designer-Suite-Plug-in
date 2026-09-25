"""The shipped configs, run through the real tools (3.2.0; review item C4).

Each class skips unless its tool is available on the machine. Inside the
repository, `npm ci` in tooling/main and tooling/tailwind-v3 provides all of
them (wds_support points these variables there when they are not set):

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
  config had no room for the layout primitives' geometry over tokens, the
  focus ring's gap, system colours in forced-colors mode or `100svb`; its
  inherited formatting rule refused one-line modifier tables; and its
  inherited `url()` import notation refused every import in the documented
  Tailwind entry (the references use both spellings, so the rule is off).
- 3.2.1: the v3 block of the ESLint config's Part 5 stopped ESLint ("Could
  not resolve tailwindcss"): eslint-plugin-tailwindcss 3.18 cannot look for
  tailwindcss from a relative config path. Both blocks also gave
  `p-card px-inline-md` as a contradiction, which neither plugin flags,
  because the longhand always follows the shorthand.
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
STYLELINT_MODULES = os.environ.get("WDS_STYLELINT_MODULES")
STYLE_RULE = "design-laws/style-prop-custom-properties-only"
STARTER_STYLES = SKILLS / "web-design-studio" / "assets" / "starter" / "styles"


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
TAILWIND_V3_LINT = tailwind_lint_modules(
    [p for p in [os.environ.get("WDS_TAILWIND_V3_MODULES", "")] if p], 3)


def temp_project(cls, prefix: str, modules: str) -> pathlib.Path:
    """A temporary project whose node_modules is a link to `modules`, so the
    tools resolve every package exactly as a real project does: a directory
    junction on Windows (it needs no privilege), a symlink elsewhere. The link
    is removed first, so cleaning up never reaches the folder it points at."""
    holder = tempfile.TemporaryDirectory(prefix=prefix, ignore_cleanup_errors=True)
    cls.addClassCleanup(holder.cleanup)
    tmp = pathlib.Path(holder.name)
    target, link = pathlib.Path(modules).resolve(), tmp / "node_modules"
    if os.name == "nt":
        import _winapi
        _winapi.CreateJunction(str(target), str(link))
        cls.addClassCleanup(os.rmdir, link)        # the junction, not its target
    else:
        link.symlink_to(target, target_is_directory=True)
        cls.addClassCleanup(link.unlink)
    return tmp


def write_files(root: pathlib.Path, files: dict[str, str]) -> None:
    for name, text in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def documented_entry(doc: str = "stack-tailwind.md", header: str = "/* src/styles/index.css */") -> str:
    """The entry file a reference tells a project to write: by default the
    Tailwind v4 entry of stack-tailwind.md §2."""
    text = (SKILLS / "web-design-studio" / "references" / doc).read_text(encoding="utf-8")
    start = text.index(header)
    return text[start:text.index("```", start)]


# The two spellings the references use: strings in the Tailwind entry, `url()`
# in the vanilla one.
DOCUMENTED_ENTRIES = {
    "src/styles/index.css": ("stack-tailwind.md", "/* src/styles/index.css */"),
    "src/vanilla/index.css": ("handoff-conventions.md",
                              "/* src/styles/index.css — the whole cascade, in one place. */"),
}


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


# Component-file fixtures for the stylelint config: what the laws refuse (and
# the rule that must say so), and what they allow.
REFUSED_CSS = {
    "Literal": (".card { padding: 13px; }", "declaration-property-value-allowed-list"),
    "Hex": (".card { color: #fff; }", "color-no-hex"),
    "Important": (".card { color: var(--fg-default) !important; }", "declaration-no-important"),
    "Id": ("#card { color: var(--fg-default); }", "selector-max-id"),
    "Multiplied": (".card { padding: calc(var(--space-4) * 1.5); }",
                   "declaration-property-value-allowed-list"),
    "GeometryOutsideLayout": (".card { max-inline-size: calc(100% - var(--gutter-page) * 2); }",
                              "declaration-property-value-allowed-list"),
    "OwnMargin": (".card { margin-block-start: var(--gap-related); }",
                  "declaration-property-value-allowed-list"),
    "Apply": (".card { @apply p-card; }", "at-rule-disallowed-list"),
}
ALLOWED_CSS = {
    "Ring": ".card:focus-visible { box-shadow: 0 0 0 var(--stroke-focus) var(--bg-canvas); }",
    "SystemColour": "@media (forced-colors: active) { .card { border-color: ButtonText; } }",
    "SmallViewport": ".card { min-block-size: 100svb; }",
    "Cancel": ".card { margin-block-start: calc(var(--card-inset) * -1); }",
}


@unittest.skipUnless(NODE and STYLELINT_MODULES, "set WDS_STYLELINT_MODULES to run the stylelint fixtures")
class StylelintConfig(unittest.TestCase):
    """stylelint.config.mjs as shipped, run by the real stylelint over the
    starter's own stylesheets, the documented Tailwind entry, and component
    fixtures. Every file is linted in one run; each test reads its own."""

    @classmethod
    def setUpClass(cls):
        tmp = temp_project(cls, "wds-stylelint-", STYLELINT_MODULES)
        files = {"stylelint.config.mjs": (CONFIGS / "stylelint.config.mjs").read_text(encoding="utf-8"),
                 **{name: documented_entry(*where) for name, where in DOCUMENTED_ENTRIES.items()}}
        for css in sorted(STARTER_STYLES.glob("*.css")):
            files[f"src/styles/{css.name}"] = css.read_text(encoding="utf-8")
        for stem, css in {**{k: v[0] for k, v in REFUSED_CSS.items()}, **ALLOWED_CSS}.items():
            files[f"src/components/{stem}.css"] = "@layer components {\n" + css + "\n}\n"
        write_files(tmp, files)
        linted = [name for name in files if name.endswith(".css")]
        proc = subprocess.run([NODE, str(pathlib.Path(STYLELINT_MODULES) / "stylelint" / "bin" / "stylelint.mjs"),
                               *linted, "--config", "stylelint.config.mjs", "--formatter", "json"],
                              cwd=tmp, capture_output=True, timeout=300)
        # 0: clean, 2: problems found. stylelint 17 writes the report to stderr
        # when it finds a problem and to stdout when it does not.
        report = next((s for s in (proc.stdout, proc.stderr) if s.strip().startswith(b"[")), None)
        if proc.returncode not in (0, 2) or report is None:
            raise AssertionError(output(proc))
        cls.results = {pathlib.Path(r["source"]).relative_to(tmp).as_posix(): r
                       for r in json.loads(report.decode("utf-8"))}

    def problems(self, name: str) -> list[str]:
        result = self.results[name]
        self.assertEqual([], result.get("invalidOptionWarnings", []), name)
        self.assertEqual([], result.get("parseErrors", []), name)
        return [f"{w['line']}:{w['column']} {w['rule']}" for w in result["warnings"]]

    def test_the_starter_passes_its_own_config(self):
        for css in sorted(STARTER_STYLES.glob("*.css")):
            with self.subTest(file=css.name):
                self.assertEqual([], self.problems(f"src/styles/{css.name}"))

    def test_the_documented_entries_pass(self):
        for name, (doc, _) in DOCUMENTED_ENTRIES.items():
            with self.subTest(entry=doc):
                self.assertEqual([], self.problems(name))

    def test_what_the_laws_refuse_is_refused(self):
        for stem, (css, rule) in REFUSED_CSS.items():
            with self.subTest(css=css):
                self.assertIn(rule, [p.split(" ", 1)[1] for p in self.problems(f"src/components/{stem}.css")])

    def test_what_the_laws_allow_is_allowed(self):
        for stem, css in ALLOWED_CSS.items():
            with self.subTest(css=css):
                self.assertEqual([], self.problems(f"src/components/{stem}.css"))


def part5_block(title: str) -> str:
    """The Part 5 block under `// {title}`, uncommented as a project would."""
    lines = (CONFIGS / "eslint.design.config.mjs").read_text(encoding="utf-8").splitlines()
    block = []
    for line in lines[lines.index(f"// {title}") + 1:]:
        if not line.startswith("//") or line.startswith("// Tailwind v"):
            break
        block.append(re.sub(r"^// ?", "", line))
    return "\n".join(block).rstrip() + "\n"


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


JSX_FIXTURE = "export const {name} = ({{ cn }}) => <div {attr} />;\n"


class TailwindPluginBlock:
    """One block of the ESLint config's Part 5, uncommented, run by the real
    eslint-plugin-tailwindcss in a project wired as the docs say. The fixtures
    for the contradiction and shorthand rules are the examples the block's own
    comments give."""

    TITLE = CONST = MODULES = None
    EXTRA: dict[str, str] = {}

    @classmethod
    def tailwind_files(cls) -> dict[str, str]:
        raise NotImplementedError

    @classmethod
    def setUpClass(cls):
        tmp = temp_project(cls, "wds-twlint-", cls.MODULES)
        block = part5_block(cls.TITLE)
        conflict, *not_conflict = documented_examples(block, "tailwindcss/no-contradicting-classname")
        cls.shorthand, cls.merged = documented_examples(block, "tailwindcss/enforces-shorthand")[:2]
        cls.cases = {"Roles": 'className="p-card bg-surface text-default"',
                     "Misspelt": 'className="p-card bg-surfce"',
                     "OffScale": 'className="p-4 bg-neutral-800"',
                     "Helper": "className={cn('bg-surfce', 'p-card')}",
                     "Conflict": f'className="{conflict}"',
                     "Shorthand": f'className="{cls.shorthand}"',
                     **({"NotAConflict": f'className="{not_conflict[0]}"'} if not_conflict else {}),
                     **cls.EXTRA}
        files = {"eslint.config.mjs": (
            "import tailwind from 'eslint-plugin-tailwindcss';\n" + block
            + "export default [\n"
              "  { files: ['**/*.jsx'], languageOptions: { parserOptions: { ecmaFeatures: { jsx: true } } } },\n"
              f"  {cls.CONST},\n];\n"), **cls.tailwind_files()}
        for name, attr in cls.cases.items():
            files[f"src/components/{name}.jsx"] = JSX_FIXTURE.format(name=name, attr=attr)
        write_files(tmp, files)
        proc = subprocess.run([NODE, str(pathlib.Path(cls.MODULES) / "eslint" / "bin" / "eslint.js"),
                               "-c", "eslint.config.mjs", "--format", "json", "src/components"],
                              cwd=tmp, capture_output=True, timeout=300)
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


@unittest.skipUnless(NODE and TAILWIND_V4_LINT,
                     "set WDS_ESLINT_MODULES to a node_modules with eslint-plugin-tailwindcss 4 and tailwindcss 4")
class TailwindPluginV4(TailwindPluginBlock, unittest.TestCase):
    TITLE = "Tailwind v4, eslint-plugin-tailwindcss@4:"
    CONST = "tailwindConfig"
    MODULES = TAILWIND_V4_LINT

    @classmethod
    def tailwind_files(cls) -> dict[str, str]:
        files = {"src/styles/index.css": documented_entry(),
                 "src/styles/theme.css": (CONFIGS / "theme.css").read_text(encoding="utf-8"),
                 "src/styles/components/card.css": "@layer components {}\n"}
        for name in ("tokens.css", "base.css", "layout.css"):
            files[f"src/styles/{name}"] = (STARTER_STYLES / name).read_text(encoding="utf-8")
        return files


@unittest.skipUnless(NODE and TAILWIND_V3_LINT,
                     "set WDS_TAILWIND_V3_MODULES to run the Tailwind v3 plugin fixtures")
class TailwindPluginV3(TailwindPluginBlock, unittest.TestCase):
    TITLE = "Tailwind v3, eslint-plugin-tailwindcss@3:"
    CONST = "tailwindV3Config"
    MODULES = TAILWIND_V3_LINT
    EXTRA = {"Arbitrary": 'className="p-[13px]"',
             "Whitelisted": 'className="focus-ring tap-target motion-hover"'}

    @classmethod
    def tailwind_files(cls) -> dict[str, str]:
        return {"tailwind.config.ts": (CONFIGS / "tailwind.config.ts").read_text(encoding="utf-8")}

    def test_arbitrary_values_are_refused(self):
        self.assertIn("tailwindcss/no-arbitrary-value", self.rules_in("Arbitrary"))

    def test_the_whitelisted_utilities_pass(self):
        self.assertEqual([], self.rules_in("Whitelisted"))


if __name__ == "__main__":
    unittest.main()
