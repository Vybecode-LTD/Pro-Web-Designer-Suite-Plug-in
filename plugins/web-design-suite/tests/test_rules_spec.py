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
"""
from __future__ import annotations

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


class TheAuditFollowsTheSpec(TempDirTest):

    @classmethod
    def setUpClass(cls):
        cls.audit = load_audit()

    def findings(self, css: str, name: str = "components/card.css") -> set[tuple[str, str]]:
        path = self.tmp / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("@layer components {\n" + css + "\n}\n", encoding="utf-8")
        found, _, _ = self.audit.audit_run([str(path)])
        return {(f.law, f.rule) for f in found}

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

    def test_nesting(self):
        for css in SPEC["nesting"]["allowed"]:
            with self.subTest(allowed=css):
                self.assertNotIn(("L5", "nesting-depth"), self.findings(css))
        for css in SPEC["nesting"]["refused"]:
            with self.subTest(refused=css):
                self.assertIn(("L5", "nesting-depth"), self.findings(css))

    def test_zero_and_margins_and_fallbacks(self):
        for css in SPEC["zero"]["allowed"]:
            with self.subTest(zero=css):
                self.assertEqual(set(), self.findings(css))
        for value in SPEC["margins_in_components"]["allowed_values"]:
            with self.subTest(margin=value):
                self.assertNotIn(("L2", "child-margin"),
                                 self.findings(f".card__media {{ margin-block-end: {value}; }}"))
        for value in SPEC["margins_in_components"]["refused_values"]:
            with self.subTest(refused_margin=value):
                self.assertTrue(self.findings(f".card__media {{ margin-block-end: {value}; }}"))
        for selector in SPEC["margins_in_components"]["owl_selectors"]:
            with self.subTest(owl=selector):
                self.assertNotIn(("L2", "child-margin"),
                                 self.findings(f"{selector} {{ margin-block-start: var(--gap-related); }}"))
        for value in SPEC["var_fallback"]["allowed"]:
            with self.subTest(fallback=value):
                self.assertEqual(set(), self.findings(f".card {{ color: {value}; }}"))

    def test_layers(self):
        # SB-A8: `vendor` was missing from the order, so an entry that imported
        # into it put third-party CSS above every layer, and three references
        # gave three different places for it.
        self.assertEqual(SPEC["layers"]["order"], self.audit.LAYER_ORDER)
        self.assertEqual(SPEC["layers"]["statement"], self.audit.LAYER_STATEMENT)
        # N25: an import into a layer, above the statement, names that layer first.
        layer_rules = {("L5", "layer-order"), ("L5", "layer-undeclared"), ("L5", "layer-statement-position")}
        for kind in ("allowed", "refused"):
            for n, css in enumerate(SPEC["layers"][kind]):
                with self.subTest(**{kind: css}):
                    path = self.tmp / f"{kind}{n}" / "index.css"
                    path.parent.mkdir()
                    path.write_text(css + "\n", encoding="utf-8")
                    found, _, _ = self.audit.audit_run([str(path)])
                    hit = {(f.law, f.rule) for f in found} & layer_rules
                    self.assertEqual(kind == "refused", len(hit) == 1, found)


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
    """The config's values, read from the file, with the value regexes run in
    Python (they are JavaScript regexes of the portable kind), so these hold
    wherever stylelint is absent. test_real_tools.StylelintConfig runs the
    real stylelint over the same config."""

    @classmethod
    def setUpClass(cls):
        cls.config = (CONFIGS / "stylelint.config.mjs").read_text(encoding="utf-8")

    def js_regex(self, name: str) -> re.Pattern:
        m = re.search(rf"const {name} = String\.raw`/(.+?)/`;", self.config)
        self.assertIsNotNone(m, f"{name} is not declared")
        return re.compile(m.group(1))

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
        corrected statement as an unknown layer; and nothing checked that a
        layer an entry imports into is in its statement. N2: the layer order,
        the nesting depth and the system colours are now written from the spec
        by tools/sync_rules.py, whose --check fails when a gate drifts
        (test_real_tools.StylelintConfig runs the spec's examples)."""
        proc = subprocess.run([sys.executable, "-B", str(PLUGIN / "tools" / "sync_rules.py"), "--check"],
                              capture_output=True, env=env())
        self.assertEqual(0, proc.returncode, output(proc))
        self.assertIn("undeclaredImport", self.config)
        self.assertRegex(self.config, r"'max-nesting-depth':\s*\[\s*MAX_NESTING,\s*\{[^}]*'pseudo-classes'")

    def test_system_colours_are_scoped_to_forced_colors(self):
        """3.2.1 allowed the system colours in every colour property of every
        file, as exact PascalCase strings. A rule now scopes them to
        `@media (forced-colors: active)`, and the allowlist reads them in any
        case (test_real_tools.StylelintConfig runs the spec's examples)."""
        self.assertRegex(self.config, r"systemColorRuleName = 'design/system-colors-in-forced-colors'")
        self.assertIn("[systemColorRuleName]: true", self.config)
        self.assertIn("plugins: [designPlugin, systemColorPlugin]", self.config)

    def test_sass_is_left_to_the_audit(self):
        """The spec says stylelint reads no Sass (`sass.gates`), so the Sass
        rules live in the audit alone. The day this config takes a Sass syntax,
        it has to follow those rules too, with a real-tool test."""
        self.assertIn("stylelint", SPEC["sass"]["gates"])
        self.assertNotRegex(self.config, r"(?i)s[ac]ss")

    def test_a_var_fallback_is_accepted(self):
        var_one = self.js_regex("VAR_ONE")
        for value in SPEC["var_fallback"]["allowed"][:2]:
            with self.subTest(value=value):
                self.assertTrue(var_one.search(value))

    def test_margins_in_components(self):
        block = re.search(r"const MARGIN_ALLOWLIST = .*?\.map\(\(prop\) => \[prop, \[(.*?)\]\]\)",
                          self.config, re.S)
        self.assertIsNotNone(block)
        strings = set(re.findall(r"'([^']+)'", block.group(1)))
        regexes = [self.js_regex(name) for name in re.findall(r"\b([A-Z_]{4,})\b", block.group(1))
                   if name != "KEYWORDS"]

        def allowed(value):
            return value in strings or any(rx.search(value) for rx in regexes)

        for value in SPEC["margins_in_components"]["allowed_values"]:
            with self.subTest(allowed=value):
                self.assertTrue(allowed(value))
        for value in SPEC["margins_in_components"]["refused_values"]:
            with self.subTest(refused=value):
                self.assertFalse(allowed(value))

    def test_the_owl_is_allowed_in_components(self):
        self.assertRegex(self.config, r"'selector-max-universal':\s*\[\s*0,\s*\{\s*ignoreAfterCombinators:"
                                      r"\s*\['>',\s*'\+'\]")


class TheDocsFollowTheSpec(unittest.TestCase):

    def test_no_reference_demands_space_0_for_zero(self):
        for doc in sorted((SKILLS / "web-design-studio" / "references").glob("*.md")):
            text = doc.read_text(encoding="utf-8")
            with self.subTest(doc=doc.name):
                self.assertNotRegex(text, r"`0`[^.|]{0,40}(which is|are)[^.|]{0,10}`--space-0`")


if __name__ == "__main__":
    unittest.main()
