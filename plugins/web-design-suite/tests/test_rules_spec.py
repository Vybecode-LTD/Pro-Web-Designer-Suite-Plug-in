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

import importlib.util
import json
import pathlib
import re
import sys
import unittest

from wds_support import SKILLS, TempDirTest

HERE = pathlib.Path(__file__).resolve().parent
# The spec comes from this suite's own plugin; the tools checked against it are
# the tree under test (WDS_PLUGIN_ROOT may point at an older copy).
SPEC = json.loads((HERE.parent / "skills" / "web-design-studio" / "assets" / "rules" / "design-rules.json")
                  .read_text(encoding="utf-8"))
CONFIGS = SKILLS / "web-design-studio" / "assets" / "configs"


def load_audit():
    spec = importlib.util.spec_from_file_location(
        "wds_audit_rules", SKILLS / "web-design-studio" / "scripts" / "audit_design.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def glob_match(path: str, glob: str) -> bool:
    """A `**/`-style glob, as stylelint's `files` reads it."""
    rx = re.escape(glob).replace(r"\*\*/", "(?:.*/)?").replace(r"\*", "[^/]*")
    return re.fullmatch(rx, path) is not None


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
        for kind, check in (("token_files", self.audit.is_token_file),
                            ("component_files", self.audit.is_component_file)):
            spec = SPEC["file_classes"][kind]
            for path in spec["examples"]:
                with self.subTest(kind=kind, path=path):
                    self.assertTrue(check(pathlib.Path(path)))
            for path in spec["not"]:
                with self.subTest(kind=kind, not_=path):
                    self.assertFalse(check(pathlib.Path(path)))

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


class StylelintFollowsTheSpec(unittest.TestCase):
    """stylelint is not installed on the machine these tests were written on;
    its config is checked here by reading the values, and the value regexes
    are run in Python (they are JavaScript regexes of the portable kind)."""

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
        token_globs = self.override_files("tokens.css") + self.override_files("theme.css")
        self.assertEqual(sorted(SPEC["file_classes"]["token_files"]["globs"]), sorted(token_globs))
        self.assertEqual(sorted(SPEC["file_classes"]["component_files"]["globs"]),
                         sorted(self.override_files("components")))
        for kind, globs in (("token_files", token_globs),
                            ("component_files", self.override_files("components"))):
            for path in SPEC["file_classes"][kind]["examples"]:
                with self.subTest(kind=kind, path=path):
                    self.assertTrue(any(glob_match(path if "/" in path else "x/" + path, g) for g in globs))

    def test_nesting_limit(self):
        m = re.search(r"'max-nesting-depth':\s*\[\s*(\d+),\s*\{([^}]*)\}", self.config)
        self.assertIsNotNone(m)
        self.assertEqual(int(m.group(1)), SPEC["nesting"]["max_depth"])
        self.assertIn("'pseudo-classes'", m.group(2))

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
