"""One rule spec, shared by the gates (3.2.0).

web-design-studio/assets/rules/design-rules.json states the rules the audit and
the lint configs must agree on. Each tool carries its own copy of the values;
this module fails when a copy disagrees with the spec.

Regressions covered — SB-A14, the three gates disagreed about the laws:
- Nesting: the audit counted the top-level rule as depth 1, so the references'
  own `.card { & .title { &:hover {} } }` ("depth 2, the edge") failed it,
  while stylelint counted nesting below the top level.
- Margins: Law 2 allows `calc(var(--t) * -1)` and the owl selector; the
  stylelint component override allowed only 0/auto and banned every `*`.
- Fallbacks: stylelint's VAR_ONE rejected `var(--x, 12px)`, which the audit
  accepts.
- File classes: stylelint's globs and the audit's patterns named different
  token and component files (`dark-theme.css`, `Card.module.css`,
  `tokens/colour.css`).
- Zero: two references demanded `--space-0`, which the audit flags as a
  Tier-1 leak; every gate accepts a literal 0.

N2 (3.3.0): tools/sync_rules.py writes the spec's data into the gates, and
every `allowed` and `refused` example runs through each gate its section
names: the audit here, stylelint and ESLint in test_real_tools. Where a gate
still disagrees with the spec, KNOWN_DISAGREEMENTS says so and names the item
that fixes it; the test fails when a gate starts agreeing, so the list only
shrinks.
"""
from __future__ import annotations

import collections
import json
import pathlib
import re
import subprocess
import sys
import unittest

from wds_support import PLUGIN, SKILLS, TempDirTest, env, load_script, output

HERE = pathlib.Path(__file__).resolve().parent
# The spec comes from this suite's own plugin; the tools checked against it are
# the tree under test (WDS_PLUGIN_ROOT may point at an older copy).
SPEC = json.loads((HERE.parent / "skills" / "web-design-studio" / "assets" / "rules" / "design-rules.json")
                  .read_text(encoding="utf-8"))
CONFIGS = SKILLS / "web-design-studio" / "assets" / "configs"


def load_audit():
    return load_script("web-design-studio", "audit_design")


def glob_match(path: str, glob: str) -> bool:
    """A `**/`-style glob, as stylelint's `files` reads it."""
    rx = re.escape(glob).replace(r"\*\*/", "(?:.*/)?").replace(r"\*", "[^/]*")
    return re.fullmatch(rx, path) is not None


def matches_any(path: str, globs: list[str]) -> bool:
    """Whether stylelint's `files` list would take `path`; a bare file name is
    placed in a folder, as a real one always is."""
    return any(glob_match(path if "/" in path else "x/" + path, g) for g in globs)


Example = collections.namedtuple("Example", "section verdict source name text gates")


def in_layer(layer: str, css: str) -> str:
    return f"@layer {layer} {{\n{css}\n}}\n"


def jsx_component(jsx: str) -> str:
    return f"export const C = ({{ pct, span }}) => {jsx};\n"


def spec_examples() -> list[Example]:
    """Every `allowed` and `refused` example in the spec, each as a file of its
    own for the gates its section names: a rule in a component file, a whole
    entry stylesheet, or a JSX component. The Sass examples, which only the
    audit reads, are test_sass's."""
    examples: list[Example] = []

    def add(section: str, verdict: str, source: str, text: str, ext: str = "css") -> None:
        n = len(examples)
        name = (f"src/entries/{verdict}-{n}/index.css" if section == "layers"
                else f"src/components/{section.replace('.', '-')}-{verdict}-{n}.{ext}")
        examples.append(Example(section, verdict, source, name, text, tuple(SPEC[section.split(".")[0]]["gates"])))

    def rule(css: str) -> str:
        return in_layer("components", css)

    margins = SPEC["margins_in_components"]
    for verdict in ("allowed", "refused"):
        for section in ("nesting", "zero", "system_colors"):
            for css in SPEC[section].get(verdict, []):
                add(section, verdict, css, rule(css))
        for css in SPEC["layers"][verdict]:
            add("layers", verdict, css, css + "\n")
        for value in SPEC["var_fallback"].get(verdict, []):
            add("var_fallback", verdict, value, rule(f".card {{ color: {value}; }}"))
        for value in margins[f"{verdict}_values"]:      # margin-block takes one value or two
            add("margins_in_components", verdict, value, rule(f".card__media {{ margin-block: {value}; }}"))
        if verdict == "allowed":
            for selector in margins["owl_selectors"]:
                add("margins_in_components", verdict, selector,
                    rule(f"{selector} {{ margin-block-start: var(--gap-related); }}"))
        else:
            for selector in margins["refused_selectors"]:
                add("margins_in_components", verdict, selector, rule(f"{selector} {{ color: var(--fg-strong); }}"))
        for family, values in SPEC["values"]["families"].items():
            for declaration in values[verdict]:
                add(f"values.{family}", verdict, declaration, rule(f".card {{ {declaration}; }}"))
        for jsx in SPEC["inline_styles"][verdict]:
            add("inline_styles", verdict, jsx, jsx_component(jsx), ext="tsx")
    return examples


# Where a gate still gives the opposite verdict, keyed by (gate, the example as
# the spec writes it), with the item that brings it in line. Each must still
# disagree: when a fix makes a gate agree, its entry goes.
KNOWN_DISAGREEMENTS: dict[tuple[str, str], str] = {
    ("stylelint", "var(--fg-muted, #666666)"): "N1 row 6: color-no-hex reads a var() fallback (P3)",
    ("stylelint", ".stack > * + *"): "N1 row 7: the owl's margin is refused as a value (P3)",
    ("stylelint", ".flow > * + *"): "N1 row 7: the owl's margin is refused as a value (P3)",
    ("audit", ".card p"): "N1 row 5: a type selector in a component file (P3)",
    ("audit", ".badge { color: GrayText; }"): "N1 row 8: a system colour outside forced-colors mode (P3)",
    ("audit", ".panel { border: var(--stroke-default) solid ButtonBorder; }"): "N1 row 8 (P3)",
    ("audit", ".card *"): "N30: a universal selector after a space in a component file (P3)",
    ("audit", "transition-duration: 0s"): "N30: 0s is read as a literal duration (P3)",
    ("audit", "font-size: 1.125rem"): "N30: the type check skips any length ending in em, rem too (P3)",
    ("audit", "color: red"): "N30: a named colour is only a warning (P3)",
    ("audit", "max-width: 600px"): "N30: the audit reads no sizing property (P3)",
    ("audit", "<div style={{ '--gap': '12px' }} />"): "N30: a literal in an inline custom property (P3)",
    ("audit", "<div style={{ '--tint': 'hwb(20 10% 30%)' }} />"): "N30: as above (P3)",
}


def hold_to_the_spec(test: unittest.TestCase, gate: str, problems_of) -> None:
    """Each example of a section `gate` enforces: an allowed one draws no
    problem at all from it, a refused one at least one error. `problems_of`
    maps an Example to (errors, every problem) as short strings."""
    examples = [e for e in spec_examples() if gate in e.gates]
    test.assertTrue(examples, f"no section names {gate}")
    for ex in examples:
        with test.subTest(gate=gate, section=ex.section, **{ex.verdict: ex.source}):
            errors, problems = problems_of(ex)
            known = KNOWN_DISAGREEMENTS.get((gate, ex.source))
            agrees = not problems if ex.verdict == "allowed" else bool(errors)
            if known:
                test.assertFalse(agrees, f"{gate} now agrees with the spec ({known}): "
                                         "remove it from KNOWN_DISAGREEMENTS")
            else:
                test.assertTrue(agrees, problems or "nothing reported")


class TheAuditFollowsTheSpec(TempDirTest):

    @classmethod
    def setUpClass(cls):
        cls.audit = load_audit()

    def test_file_classes(self):
        # SB-A9: a root-level components/ folder, the common Next.js layout,
        # was not a component file. The migration tool keeps its own copy of
        # the audit's test, so the spec holds both.
        migration = load_script("design-token-migration", "extract_literals")
        for kind, tool, check in (("token_files", "audit", self.audit.is_token_file),
                                  ("component_files", "audit", self.audit.is_component_file),
                                  ("token_files", "migration", migration.is_token_file),
                                  ("component_files", "migration", migration.is_component_file)):
            spec = SPEC["file_classes"][kind]
            for path in spec["examples"]:
                with self.subTest(kind=kind, tool=tool, path=path):
                    self.assertTrue(check(pathlib.Path(path)))
            for path in spec["not"]:
                with self.subTest(kind=kind, tool=tool, not_=path):
                    self.assertFalse(check(pathlib.Path(path)))

    def sass_findings(self, scss: str) -> set[tuple[str, str]]:
        """A partial as written: no layer around it, and neither a token file
        nor a component file."""
        path = self.tmp / "src" / "styles" / "_partial.scss"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(scss + "\n", encoding="utf-8")
        found, _, _ = self.audit.audit_run([str(path)])
        return {(f.law, f.rule) for f in found}

    def test_sass(self):
        # SB-A24: a rule inside a @mixin was unlayered CSS, an interpolation's
        # braces closed the layer around it, and a variable holding a literal
        # passed.
        for kind, finding in (("definitions", ("L5", "unlayered")), ("variables", ("L1", "sass-literal"))):
            for scss in SPEC["sass"][kind]["allowed"]:
                with self.subTest(kind=kind, allowed=scss):
                    self.assertEqual(set(), self.sass_findings(scss))
            for scss in SPEC["sass"][kind]["refused"]:
                with self.subTest(kind=kind, refused=scss):
                    self.assertEqual({finding}, self.sass_findings(scss))

    def test_every_example(self):
        # SB-A8 and N25 (layers), SB-A14 (nesting, zero, margins, fallbacks),
        # N2 (the value families and inline styles): every example of every
        # section the audit enforces, through the audit as shipped.
        def problems_of(ex: Example) -> tuple[list[str], list[str]]:
            path = self.write(ex.name, ex.text)
            found, _, _ = self.audit.audit_run([str(path)])
            return ([f"{f.law} {f.rule}" for f in found if f.severity == "error"],
                    [f"{f.law} {f.rule} ({f.severity})" for f in found])
        hold_to_the_spec(self, "audit", problems_of)


class TheDocsStateTheSpecsOrder(unittest.TestCase):

    def test_every_layer_statement_follows_the_spec(self):
        """SB-A8 and SB-C9: the contract's statement left `vendor` out, and three
        references put it in three places, one of them after `overrides`."""
        order = SPEC["layers"]["order"]
        assets = SKILLS / "web-design-studio" / "assets"
        paths = [*SKILLS.glob("*/SKILL.md"), *SKILLS.glob("*/references/*.md"),
                 SKILLS.parent / "shared" / "token-contract.md",
                 *(assets / "configs").iterdir(), *(assets / "starter" / "styles").iterdir()]
        wrong, full = [], 0
        for path in paths:
            for m in re.finditer(r"@layer ([a-z][\w-]*(?:,\s*[a-z][\w-]*)+);", path.read_text(encoding="utf-8")):
                names = [n.strip() for n in m.group(1).split(",")]
                known = [n for n in names if n in order]
                if {"reset", "overrides"} <= set(names):
                    full += 1
                    if "vendor" not in names:
                        wrong.append(f"{path.name}: {m.group(0)} (no vendor)")
                if known != [n for n in order if n in known]:
                    wrong.append(f"{path.name}: {m.group(0)} (out of order)")
        self.assertGreater(full, 20)
        self.assertEqual([], wrong)

    def test_the_entry_names_a_file_for_every_layer(self):
        """N24: the canonical entry stopped after layout.css, so a project that
        copied it never imported utilities.css or overrides.css."""
        entry = (SKILLS / "web-design-studio" / "assets" / "starter" / "styles" / "index.css").read_text(
            encoding="utf-8")
        for layer in SPEC["layers"]["order"]:
            with self.subTest(layer=layer):
                if layer == "theme":                    # only a Tailwind entry names it
                    continue
                spelled = {"vendor": ') layer(vendor);', "components": '@import url("components/'}
                self.assertIn(spelled.get(layer, f'@import url("{layer}.css");'), entry)


class StylelintFollowsTheSpec(unittest.TestCase):
    """What the generated blocks do not carry, read from the config: the file
    globs and the overrides. The values, the layer order, the nesting depth and
    the system colours are written from the spec (N2), and
    test_real_tools.StylelintConfig runs every example through the real
    stylelint."""

    @classmethod
    def setUpClass(cls):
        cls.config = (CONFIGS / "stylelint.config.mjs").read_text(encoding="utf-8")

    def override_files(self, contains: str) -> list[str]:
        for m in re.finditer(r"files:\s*\[([^\]]*)\]", self.config):
            globs = re.findall(r"'([^']+)'", m.group(1))
            if any(contains in g for g in globs):
                return globs
        self.fail(f"no override lists a file like {contains}")

    def test_file_globs(self):
        globs = {"token_files": self.override_files("tokens.css") + self.override_files("theme.css"),
                 "component_files": self.override_files("components")}
        for kind, found in globs.items():
            self.assertEqual(sorted(SPEC["file_classes"][kind]["globs"]), sorted(found), kind)
            for path in SPEC["file_classes"][kind]["examples"]:
                with self.subTest(kind=kind, path=path):
                    self.assertTrue(matches_any(path, found))
            for path in SPEC["file_classes"][kind].get("not", []):
                with self.subTest(kind=kind, not_path=path):
                    self.assertFalse(matches_any(path, found))

    def test_the_file_class_overrides_are_the_documented_four(self):
        """3.2.1 added a fifth, for layout primitives, after the component
        block. Its allowlist replaced the component block's for any file both
        matched (`src/components/layout/*.css`, `packages/ui/layout.css`), so
        those components lost Law 2. The starter now routes its derived boxes
        through sockets and the list is back to the four the config documents."""
        self.assertEqual(4, len(re.findall(r"^    \{\n      files:", self.config, re.M)))
        self.assertIn("There are four", self.config)

    def test_the_specs_data_is_written_into_the_gates(self):
        """SB-A8: the config's LAYER_ORDER had no `vendor`, so it refused the
        corrected statement as an unknown layer. N2: tools/sync_rules.py writes
        the spec's data into the audit, the stylelint config and the ESLint
        config, and its --check fails when one drifts. The three tests that read
        this config's allowlists as text are gone: the block is the spec."""
        proc = subprocess.run([sys.executable, "-B", str(PLUGIN / "tools" / "sync_rules.py"), "--check"],
                              capture_output=True, env=env())
        self.assertEqual(0, proc.returncode, output(proc))

    def test_sass_is_left_to_the_audit(self):
        """The spec says stylelint reads no Sass (`sass.gates`), so the Sass
        rules live in the audit alone. The day this config takes a Sass syntax,
        it has to follow those rules too, with a real-tool test."""
        self.assertEqual(["audit"], SPEC["sass"]["gates"])
        self.assertNotRegex(self.config, r"(?i)s[ac]ss")


class TheDocsFollowTheSpec(unittest.TestCase):

    def test_no_reference_demands_space_0_for_zero(self):
        for doc in sorted((SKILLS / "web-design-studio" / "references").glob("*.md")):
            text = doc.read_text(encoding="utf-8")
            with self.subTest(doc=doc.name):
                self.assertNotRegex(text, r"`0`[^.|]{0,40}(which is|are)[^.|]{0,10}`--space-0`")


if __name__ == "__main__":
    unittest.main()
