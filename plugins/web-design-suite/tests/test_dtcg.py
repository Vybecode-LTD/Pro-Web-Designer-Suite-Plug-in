"""P31 part 1: shared/dtcg.py, DTCG 2025.10 read and write (LC-C2, LC-B2).

Regressions covered (each fails on v3.5.0):
- a reference to a group's own token, `{brand.$root}` or `#/brand/$root`, the
  spelling the format gives it, was left unresolved;
- a group's `$deprecated` did not reach its tokens;
- a DTCG file in `.design-suite.json`'s tokens, or passed as `--tokens`, was
  refused as "not a contract.json", and diff_system refused one as a snapshot;
- there was no way to write DTCG: figma_to_tokens.py had no `--format dtcg`,
  a tokens.css could not be converted, and the migration proposal was CSS only;
- (part 3) themes could not be written: `--format dtcg` wrote the default mode
  alone, and a DTCG resolver (`*.resolver.json`) was read as no tokens;
- (part 4) a removal the old DTCG file had marked `$deprecated` failed the
  release gate, and the deprecation ledger could not take the marks;
- (the 3.6.0 live check) a DTCG file against the stylesheet it was written
  from was a major release: every value it spells another way was an edit,
  and every token it cannot hold was added.
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
import sys
import unittest

from wds_support import NODE, PLUGIN, SKILLS, TempDirTest, env, load_script, output, run_py

MASTER = PLUGIN / "shared" / "dtcg.py"
STARTER = SKILLS / "web-design-studio" / "assets" / "starter" / "styles" / "tokens.css"


def dtcg_module():
    spec = importlib.util.spec_from_file_location("wds_test_dtcg", MASTER)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class TheCopiesAreTheMaster(unittest.TestCase):
    """dtcg.py sits beside every project_config.py, which reads a DTCG token
    file through it, byte-identical to shared/dtcg.py."""

    def test_every_project_config_has_the_master_beside_it(self):
        readers = sorted(p.parent for p in SKILLS.glob("*/scripts/project_config.py"))
        self.assertEqual(10, len(readers))
        self.assertEqual(readers, sorted(p.parent for p in SKILLS.glob("*/scripts/dtcg.py")))
        master = MASTER.read_bytes()
        self.assertEqual([], [str(r.relative_to(PLUGIN)) for r in readers if (r / "dtcg.py").read_bytes() != master],
                         "copy shared/dtcg.py over these")
        self.assertEqual([], [str(p) for p in PLUGIN.rglob("dtcg_values.py")])     # the master replaced it

    def test_the_gates_vendor_it(self):
        """/install-gate copies the audit's project_config.py, so dtcg.py too."""
        text = (PLUGIN / "workflow-commands" / "install-gate" / "scripts" / "install_gate.py").read_text(encoding="utf-8")
        self.assertRegex(text, r'"web-design-studio": \[[^\]]*"dtcg.py"[^\]]*"project_config.py"')


class TheWriter(unittest.TestCase):
    """document(): CSS custom properties as a 2025.10 document."""

    @classmethod
    def setUpClass(cls):
        cls.dtcg = dtcg_module()
        pc = load_script("design-system-docs", "project_config")
        cls.starter = pc.read_tokens([STARTER]).values()

    def test_the_starter_round_trips(self):
        doc, problems = self.dtcg.document(self.starter.items())
        back, read_problems = self.dtcg.tokens(doc)
        self.assertEqual([], read_problems)
        left_out = dict(problems)
        written = {t.name: t.css() for t in back}
        self.assertEqual(sorted(n for n in self.starter if n not in left_out), sorted(written))
        self.assertGreater(len(written), 150)
        for name, value in written.items():
            with self.subTest(name=name):                # the same DTCG value, whatever the CSS spelling
                self.assertEqual(self.dtcg.css_value(name, self.starter[name]), self.dtcg.css_value(name, value))

    def test_every_token_is_typed_and_colours_are_objects(self):
        doc, _ = self.dtcg.document(self.starter.items())
        tokens = []

        def walk(node):
            if "$value" in node:
                tokens.append(node)
                return
            for key, child in node.items():
                if isinstance(child, dict):
                    walk(child)
        walk(doc)
        self.assertTrue(tokens)
        self.assertEqual([], [t for t in tokens if t.get("$type") not in (
            "color", "dimension", "duration", "number", "fontWeight", "fontFamily", "cubicBezier", "shadow",
            "border")])
        neutral = doc["neutral"]["500"]["$value"]
        self.assertEqual("oklch", neutral["colorSpace"])
        self.assertRegex(neutral["hex"], r"^#[0-9a-f]{6}$")
        self.assertEqual({"$type": "color", "$value": "{neutral.0}"}, doc["bg"]["surface"])
        self.assertEqual({"value": 1, "unit": "rem"}, doc["space"]["4"]["$value"])
        self.assertEqual({"value": 220, "unit": "ms"}, doc["dur"]["base"]["$value"])

    def test_what_dtcg_cannot_hold_is_named_never_written(self):
        doc, problems = self.dtcg.document([
            ("--space-fluid", "clamp(1rem, 2vw, 2rem)"), ("--tracking", "-0.02em"), ("--measure", "65ch"),
            ("--gap", "calc(var(--space-4) * var(--density))"), ("--space-4", "1rem"),
            ("--section", "var(--space-fluid)"), ("--a", "var(--b)"), ("--b", "var(--a)"),
            ("--odd.name", "1px"), ("--c", "var(--missing)")])
        why = dict(problems)
        self.assertEqual({"--space-fluid", "--tracking", "--measure", "--gap", "--section", "--a", "--b",
                          "--odd.name", "--c"}, set(why))
        self.assertIn("em has no 2025.10 type", why["--tracking"])
        self.assertIn("reads --space-fluid, which is not written", why["--section"])
        self.assertIn("reads another token inside an expression", why["--gap"])
        self.assertIn("cycle", why["--a"] + why["--b"])
        self.assertEqual({"space", "$extensions"}, set(doc))
        held = self.dtcg.not_written(doc)                           # kept in the file (Codex on #119)
        self.assertEqual(sorted(why), sorted(held))
        self.assertEqual("65ch", held["--measure"])

    def test_a_name_that_is_also_a_group_is_its_root(self):
        doc, problems = self.dtcg.document([("--brand", "#e8440a"), ("--brand-hover", "#c63a08"),
                                            ("--bg-brand", "var(--brand)"), ("--focus", "2px solid var(--brand)")])
        self.assertEqual([], problems)
        self.assertEqual("#e8440a", doc["brand"]["$root"]["$value"]["hex"])
        self.assertEqual("{brand.$root}", doc["bg"]["brand"]["$value"])
        self.assertEqual("color", doc["bg"]["brand"]["$type"])
        self.assertEqual({"color": "{brand.$root}", "width": {"value": 2, "unit": "px"}, "style": "solid"},
                         doc["focus"]["$value"])
        back = {t.name: t.css() for t in self.dtcg.tokens(doc)[0]}
        self.assertEqual("var(--brand)", back["--bg-brand"])

    def test_a_shadow_reads_its_references(self):
        doc, problems = self.dtcg.document([("--stroke", "2px"), ("--canvas", "#ffffff"),
                                            ("--ring", "0 0 0 var(--stroke) var(--canvas)")])
        self.assertEqual([], problems)
        self.assertEqual({"color": "{canvas}", "offsetX": {"value": 0, "unit": "px"},
                          "offsetY": {"value": 0, "unit": "px"}, "blur": {"value": 0, "unit": "px"},
                          "spread": "{stroke}"}, doc["ring"]["$value"])
        self.assertEqual("0px 0px 0px var(--stroke) var(--canvas)",
                         {t.name: t.css() for t in self.dtcg.tokens(doc)[0]}["--ring"])

    def test_colour_spaces_keep_their_space(self):
        for css, space, hexed in (("#e8440a", "srgb", "#e8440a"), ("rgb(232 68 10 / 50%)", "srgb", "#e8440a"),
                                  ("hsl(20deg 80% 50%)", "hsl", "#e65e19"), ("oklch(62% 0.19 45)", "oklch", None),
                                  ("lab(50 40 59.5)", "lab", None), ("color(display-p3 1 0 0)", "display-p3", None),
                                  ("transparent", "srgb", "#000000")):
            with self.subTest(css=css):
                colour = self.dtcg.css_colour(css)
                self.assertEqual(space, colour["colorSpace"])
                if hexed:
                    self.assertEqual(hexed, colour["hex"])
                self.assertEqual(3, len(colour["components"]))
        self.assertEqual(0.5, self.dtcg.css_colour("rgb(232 68 10 / 50%)")["alpha"])
        self.assertNotIn("hex", self.dtcg.css_colour("lab(50 40 59.5)"))

    def test_the_legacy_comma_form_keeps_its_alpha_under_either_name(self):
        """The audit's S4: `rgb()` and `rgba()` are aliases since CSS Color 4,
        and so are `hsl()` and `hsla()`, but a fourth comma argument was read
        only after the `a` names, so `rgb(255, 0, 0, 0.5)` was not written."""
        for short, long in (("rgb(255, 0, 0, 0.5)", "rgba(255, 0, 0, 0.5)"),
                            ("hsl(0, 100%, 50%, 0.5)", "hsla(0, 100%, 50%, 0.5)")):
            with self.subTest(css=short):
                self.assertEqual(self.dtcg.css_colour(long), self.dtcg.css_colour(short))
                self.assertEqual(0.5, self.dtcg.css_colour(short)["alpha"])
                doc, problems = self.dtcg.document([("--scrim", short)])
                self.assertEqual([], problems)
                self.assertEqual("color", doc["scrim"]["$type"])
                self.assertEqual({}, self.dtcg.not_written(doc))
        # A fourth argument is legacy syntax, comma-separated; the modern form
        # puts alpha after `/` (Codex on #143, CSS Color 4 §4.1).
        for css in ("rgb(1 2 3 0.5)", "rgba(1 2 3 0.5)", "hsl(0 100% 50% 0.5)"):
            with self.subTest(css=css):
                self.assertIsNone(self.dtcg.css_colour(css))


DTCG_ROOTS = {
    "brand": {"$type": "color", "$root": {"$value": {"colorSpace": "srgb", "components": [0.9, 0.3, 0.05]}},
              "hover": {"$value": {"colorSpace": "srgb", "components": [0.8, 0.2, 0.0]}}},
    "bg": {"$type": "color", "brand": {"$value": "{brand.$root}"}, "pointer": {"$ref": "#/brand/$root"}},
    "old": {"$type": "color", "$deprecated": "use bg.brand",
            "accent": {"$value": "{brand.hover}"}, "kept": {"$value": "{brand.hover}", "$deprecated": False}},
}


class TheReaderFollowsTheFormat(TempDirTest):
    """DTCG 2025.10 names a group's own token `{group.$root}`, and a group's
    `$deprecated` applies to its tokens unless one says otherwise."""

    def css(self, data):
        src = self.write("export.tokens.json", json.dumps(data))
        proc = run_py("figma-variables-sync", "figma_to_tokens", src, "--format", "css", "--color-format", "hex",
                      cwd=self.tmp)
        return proc, proc.stdout.decode("utf-8")

    def test_a_reference_to_a_root_token_resolves(self):
        proc, css = self.css(DTCG_ROOTS)
        self.assertIn("--bg-brand: var(--brand);", css)
        self.assertIn("--bg-pointer: var(--brand);", css)
        self.assertNotIn("$root", output(proc))

    def test_a_groups_deprecation_reaches_its_tokens(self):
        _, css = self.css(DTCG_ROOTS)
        self.assertRegex(css, r"--old-accent: [^;]+; +/\* \(deprecated: use bg\.brand\) \*/")
        self.assertNotRegex(css, r"--old-kept: [^;]+; +/\*")


class TheProjectReadsDtcg(TempDirTest):
    """A DTCG file is a token file: in `.design-suite.json`, as `--tokens`,
    and as a snapshot for diff_system."""

    def setUp(self):
        super().setUp()
        self.write(".git/HEAD", "x\n")
        self.write("tokens/design.tokens.json", json.dumps(DTCG_ROOTS))

    def test_the_config_and_the_flag_read_it(self):
        self.write("tokens/legacy.tokens", json.dumps({"x": {"$type": "color", "$value": "#010203"}}))
        for args in (("--tokens", "tokens/design.tokens.json"), ("--tokens", "tokens/legacy.tokens")):
            with self.subTest(args=args):
                proc = run_py("figma-variables-sync", "figma_to_tokens", self.write("x.tokens.json", "{}"), *args,
                              cwd=self.tmp)
                self.assertNotIn("not a contract.json", output(proc))
                self.assertRegex(output(proc), r"token names from tokens[/\\]")
        pc = load_script("design-system-docs", "project_config")             # what the intake holds (CodeRabbit)
        tokens = pc.read_tokens([self.tmp / "tokens" / "design.tokens.json"])
        self.assertEqual("var(--brand)", tokens.roles["--bg-brand"])
        self.assertEqual("var(--brand-hover)", tokens.roles["--old-accent"])
        self.write(".design-suite.json", '{"schema": 1, "tokens": "tokens/design.tokens.json"}')
        self.write("src/card.css", ".card { color: var(--bg-brand); }\n")
        proc = run_py("web-design-studio", "audit_design", "src", "--json", cwd=self.tmp)
        self.assertNotIn("not a contract.json", output(proc))
        self.assertIn(proc.returncode, (0, 1), output(proc))

    def test_diff_system_compares_two_dtcg_files(self):
        new = json.loads(json.dumps(DTCG_ROOTS))
        del new["bg"]["pointer"]
        self.write("tokens/next.tokens.json", json.dumps(new))
        proc = run_py("design-system-versioning", "diff_system", "tokens/design.tokens.json",
                      "tokens/next.tokens.json", "--format", "json", cwd=self.tmp)
        report = json.loads(proc.stdout)
        self.assertEqual("DTCG", report["old"]["source"])
        self.assertIn("--bg-pointer", {c["subject"] for c in report["changes"]})
        self.assertTrue(any("a DTCG file holds default values" in n for n in report["notes"]), report["notes"])


class FigmaToTokensWritesDtcg(TempDirTest):
    """`--format dtcg`, from a Figma export or a tokens.css."""

    def test_an_export_becomes_a_2025_10_document(self):
        src = self.write("export.tokens.json", json.dumps(DTCG_ROOTS))
        proc = run_py("figma-variables-sync", "figma_to_tokens", src, "--format", "dtcg", cwd=self.tmp)
        text = proc.stdout.decode("utf-8")
        doc = json.loads(text)
        self.assertEqual("{brand.$root}", doc["bg"]["brand"]["$value"])
        self.assertEqual("oklch", doc["brand"]["$root"]["$value"]["colorSpace"])   # --color-format's default
        self.assertEqual("use bg.brand", doc["old"]["accent"]["$deprecated"])
        for pattern in (r'"\$value"\s*:\s*"\{[\w.$-]+\}"', r'"colorSpace"\s*:', r'"\$type"\s*:\s*"color"'):
            self.assertRegex(text, pattern)                     # what evals/lifecycle/dtcg-export grades
        self.assertNotIn("{'", text)

    def test_a_tokens_css_becomes_one_and_its_themes_are_named(self):
        out = self.tmp / "tokens.json"
        proc = run_py("figma-variables-sync", "figma_to_tokens", STARTER, "--format", "dtcg", "--out", out,
                      cwd=self.tmp)
        self.assertEqual(1, proc.returncode, output(proc))              # written, with what it left out
        self.assertIn('[data-theme="dark"]: 33 token(s) left out', output(proc))
        self.assertIn("--space-fluid-sm: `clamp(", output(proc))
        doc = json.loads(out.read_bytes())
        self.assertEqual("{neutral.0}", doc["bg"]["surface"]["$value"])
        refused = run_py("figma-variables-sync", "figma_to_tokens", STARTER, "--format", "css", cwd=self.tmp)
        self.assertEqual(2, refused.returncode)


STUDIO_REVIEW = {                                  # the review's fx/figma/tokens-studio.json (LC-B2)
    "global": {"neutral": {"0": {"value": "#ffffff", "type": "color"}, "900": {"value": "#1f1d1b", "type": "color"}},
               "space": {"base": {"value": "4", "type": "spacing"}, "6": {"value": "{space.base} * 6", "type": "spacing"}}},
    "light": {"bg": {"surface": {"value": "{neutral.0}", "type": "color"}}},
    "dark": {"bg": {"surface": {"value": "{neutral.900}", "type": "color"}}},
    "$themes": [{"id": "l", "name": "Light", "selectedTokenSets": {"global": "source", "light": "enabled"}},
                {"id": "d", "name": "Dark", "selectedTokenSets": {"global": "source", "dark": "enabled"}}],
    "$metadata": {"tokenSetOrder": ["global", "light", "dark"]},
}


class TokensStudio(TempDirTest):
    """P31 part 2 (LC-B2): a Tokens Studio export's sets are merged, its
    `$themes` are modes, and its math is worked out. It was read as plain
    groups: `--light-bg-surface` and `--dark-bg-surface` in place of a
    `[data-theme]` block, and `--space-6: {space.base} * 6;`."""

    def css(self, data, *args):
        src = self.write("studio.json", json.dumps(data))
        proc = run_py("figma-variables-sync", "figma_to_tokens", src, "--color-format", "hex", *args, cwd=self.tmp)
        text = proc.stdout.decode("utf-8").replace("\r\n", "\n")
        blocks = dict(re.findall(r"^  (:root|\[data-theme=\"[\w-]+\"\]) \{\n(.*?)^  \}", text, re.M | re.S))
        return proc, text, blocks

    def test_themes_are_modes_not_prefixes(self):
        proc, text, blocks = self.css(STUDIO_REVIEW)
        self.assertIn("--bg-surface: var(--neutral-0);", blocks[":root"])
        self.assertIn("--bg-surface: var(--neutral-900);", blocks['[data-theme="dark"]'])
        self.assertIn("--space-6: 1.5rem;", blocks[":root"])
        for wrong in ("--light-", "--dark-", "--global-", "{space.base}"):
            self.assertNotIn(wrong, text)

    def test_each_theme_group_is_a_collection(self):
        from test_project_config import STUDIO_GROUPS
        _, text, blocks = self.css(STUDIO_GROUPS)
        self.assertIn("--accent: var(--blue);", blocks[":root"])
        self.assertIn("--accent: var(--red);", blocks['[data-theme="b"]'])
        self.assertIn("--bg: #000000;", blocks['[data-theme="dark"]'])
        self.assertIn("--size-2: 1rem;", blocks[":root"])
        self.assertNotIn("--brand-", text)

    def test_math_it_cannot_work_out_is_named_and_left_out(self):
        from test_project_config import STUDIO_LEGACY
        proc, text, blocks = self.css(STUDIO_LEGACY)
        self.assertEqual(1, proc.returncode, output(proc))
        for name in ("space/mixed", "space/zero", "space/lost"):
            self.assertIn(f"`{name}` was left out: math this script cannot work out", output(proc))
        for decl in ("--space-half: 0.09375rem;", "--space-neg: -0.3125rem;", "--font-bold: 700;",
                     "--opacity-hover: 0.16;", "--space-fluid: calc(1rem + 2vw);", "--bg-surface: var(--neutral-0);"):
            self.assertIn(decl, blocks[":root"])
        self.assertNotIn("{space", text)

    def test_a_themes_own_sets_beat_the_sets_it_only_reads(self):
        """Source sets merge first, then enabled ones, as sd-transforms'
        permutateThemes orders them, whatever `tokenSetOrder` says."""
        from test_project_config import STUDIO_ORDER
        _, _, blocks = self.css(STUDIO_ORDER)
        self.assertIn("--bg-surface: #ffffff;", blocks[":root"])
        pc = load_script("design-system-docs", "project_config")
        tokens = pc.read_tokens([self.write("tokens/order.json", json.dumps(STUDIO_ORDER))])
        self.assertEqual("#ffffff", tokens.constants.get("--bg-surface", tokens.scales.get("bg", {}).get("surface")))

    def test_a_group_named_type_is_a_group(self):
        """Codex on #102: `type` is legacy metadata only when it is a value."""
        data = json.loads(json.dumps(STUDIO_REVIEW))
        data["global"]["type"] = {"body": {"value": "16px", "type": "fontSizes"}}
        data["global"]["font"] = {"type": {"value": "Inter", "type": "fontFamilies"}}
        _, _, blocks = self.css(data)
        self.assertIn("--type-body: 1rem;", blocks[":root"])
        self.assertIn("--font-type: Inter;", blocks[":root"])
        pc = load_script("design-system-docs", "project_config")
        values = pc.read_tokens([self.write("tokens/t.json", json.dumps(data))]).values()
        self.assertEqual("16px", values["--type-body"])

    def test_a_token_only_a_later_theme_sets_stays_out_of_root(self):
        """Codex on #102: a Dark-only token was written in `:root`."""
        data = json.loads(json.dumps(STUDIO_REVIEW))
        data["dark"]["bg"]["overlay"] = {"value": "#000000", "type": "color"}
        _, _, blocks = self.css(data)
        self.assertNotIn("--bg-overlay", blocks[":root"])
        self.assertIn("--bg-overlay: #000000;", blocks['[data-theme="dark"]'])

    def test_a_token_two_theme_groups_set_is_named(self):
        """Codex on #102: the second group's values were dropped silently."""
        from test_project_config import STUDIO_GROUPS
        data = json.loads(json.dumps(STUDIO_GROUPS))
        data["brand/b"]["bg"] = {"$type": "color", "$value": "#ff00ff"}
        proc, _, _ = self.css(data)
        self.assertIn("`bg` was left out: set by two theme groups", output(proc))

    def test_math_is_remembered_and_composites_keep_their_references(self):
        """CodeRabbit on #102: a 30-step fan-out of `{x} + {x} - {x}` ran 3^30 times,
        and `2px solid {colors.red}` was taken for math and left out."""
        from test_project_config import STUDIO_MATH
        pc = load_script("design-system-docs", "project_config")
        values = pc.read_tokens([self.write("tokens/m.json", json.dumps(STUDIO_MATH))]).values()
        self.assertEqual("1px", values["--x30"])
        self.assertEqual("2px solid var(--colors-red)", values["--edge"])
        self.assertEqual("var(--x0) var(--x1)", values["--pair"])

    def test_a_palette_each_theme_reads_is_a_mode(self):
        """CodeRabbit on #102: the Dark palette, a source set only Dark reads,
        was lost, and `{palette.bg}` meant the Light one in both modes."""
        from test_project_config import STUDIO_PALETTES
        _, _, blocks = self.css(STUDIO_PALETTES)
        self.assertIn("--palette-bg: #ffffff;", blocks[":root"])
        self.assertIn("--palette-bg: #000000;", blocks['[data-theme="dark"]'])
        self.assertIn("--bg-surface: var(--palette-bg);", blocks[":root"])

    def test_the_project_reads_its_default_theme(self):
        pc = load_script("design-system-docs", "project_config")
        tokens = pc.read_tokens([self.write("tokens/studio.json", json.dumps(STUDIO_REVIEW))])
        self.assertEqual({"--bg-surface": "var(--neutral-0)"}, tokens.roles)
        self.assertEqual({"base": "4px", "6": "24px"}, tokens.scales["space"])
class TheEdgesOfTheFormat(TempDirTest):
    """The reviews of #101 (Codex, CodeRabbit): what a valid document may hold
    and the readers and the writer must not mishandle."""

    @classmethod
    def setUpClass(cls):
        cls.dtcg = dtcg_module()

    def read(self, data, name="t.tokens.json"):
        pc = load_script("design-system-docs", "project_config")
        return pc.read_tokens([self.write(name, json.dumps(data))])

    def test_a_key_with_a_space_is_a_css_name(self):
        tokens = self.read({"Button background": {"$type": "color", "$value": "#ffffff"},
                            "Card (raised)": {"$type": "color", "$value": "{Button background}"}})
        self.assertEqual({"--Card-raised-": "var(--Button-background)"}, tokens.roles)
        self.assertEqual("#ffffff", tokens.values()["--Button-background"])

    def test_alpha_just_below_one_is_kept(self):
        tokens = self.read({"veil": {"$type": "color", "$value": {
            "colorSpace": "srgb", "components": [1, 0, 0], "alpha": 0.9995}}})
        self.assertEqual("rgb(255 0 0 / 0.9995)", tokens.constants["--veil"])

    def test_an_extends_cycle_is_reported(self):
        for doc in ({"a": {"$extends": "{a}", "x": {"$type": "color", "$value": "#000000"}}},
                    {"a": {"$extends": "{b}", "x": {"$type": "color", "$value": "#000000"}},
                     "b": {"$extends": "{a}", "y": {"$type": "color", "$value": "#ffffff"}}}):
            with self.subTest(doc=list(doc)):
                _, problems = self.dtcg.normalise(doc)
                self.assertTrue(any("cycle" in why for _, why in problems), problems)

    def test_a_document_nested_too_deep_is_refused_not_a_traceback(self):
        deep = {"$type": "color", "$value": "#000000"}
        for _ in range(300):
            deep = {"g": deep}
        doc = {"top": {"$type": "color", "$value": "#ffffff"}, "deep": deep}
        _, problems = self.dtcg.normalise(doc)
        self.assertIn("more than 64 levels", problems[0][1])
        self.assertEqual({}, self.read(doc).values())

    def test_a_property_level_pointer_is_its_value(self):
        from test_project_config import DTCG_POINTERS
        values = self.read(DTCG_POINTERS).values()
        self.assertEqual("0.5", values["--chan"])                    # #/base/$value/components/0
        self.assertEqual("#400000", values["--mix"])                 # a component that is a pointer
        self.assertEqual("var(--base)", values["--shade"])           # a whole-token pointer inside a value

    def test_an_alias_cycle_is_left_out(self):
        from test_project_config import DTCG_POINTERS
        tokens, problems = self.dtcg.tokens(DTCG_POINTERS)
        names = {t.name for t in tokens}
        self.assertFalse({"--a", "--b", "--self"} & names)
        self.assertIn("--c", names)                                  # it reads into the cycle, but is not in it
        self.assertEqual(3, sum("reference cycle" in why for _, why in problems))

    def test_a_non_ascii_reference_is_written(self):
        doc, problems = self.dtcg.document([("--café", "#ffffff"), ("--alias", "var(--café)")])
        self.assertEqual([], problems)
        self.assertEqual("{café}", doc["alias"]["$value"])

    def test_extends_that_expand_too_far_are_refused(self):
        """CodeRabbit on #101: a shallow file whose `$extends` chain or fan-out
        expands past the limits is refused, not a traceback or a full memory."""
        from test_project_config import EXTENDS_CHAIN, EXTENDS_FAN, POINTER_FAN
        for doc in (EXTENDS_CHAIN, EXTENDS_FAN, POINTER_FAN):           # POINTER_FAN: CodeRabbit on #102
            with self.subTest(size=len(doc)):
                _, problems = self.dtcg.normalise(doc)
                self.assertIn("expand it past 64 levels or 100000 entries", problems[-1][1])
                self.assertEqual({}, self.read(doc).values())

    def test_weight_keywords_and_unbounded_numbers(self):
        doc, problems = self.dtcg.document([("--weight-bold", "bold"), ("--weight-body", "normal"),
                                            ("--huge", "1e999"), ("--gap", "1e999px")])
        self.assertEqual({"$type": "fontWeight", "$value": "bold"}, doc["weight"]["bold"])
        self.assertEqual("normal", doc["weight"]["body"]["$value"])
        self.assertEqual({"--huge", "--gap"}, {name for name, _ in problems})
        json.dumps(doc, allow_nan=False)                 # no Infinity in the file

    def test_a_keyword_colour_is_written_not_dropped(self):
        src = self.write("e.tokens.json", json.dumps({"veil": {"$type": "color", "$value": "transparent"},
                                                      "ink": {"$type": "color", "$value": "#111111"}}))
        proc = run_py("figma-variables-sync", "figma_to_tokens", src, "--format", "dtcg", cwd=self.tmp)
        doc = json.loads(proc.stdout)
        self.assertEqual(0, doc["veil"]["$value"]["alpha"])

    def test_a_deprecation_reason_cannot_end_a_comment(self):
        src = self.write("e.tokens.json", json.dumps({"ink": {"$type": "color", "$value": "#111111",
                                                              "$deprecated": "gone */ body { display: none }"}}))
        proc = run_py("figma-variables-sync", "figma_to_tokens", src, "--color-format", "hex", cwd=self.tmp)
        css = proc.stdout.decode("utf-8")
        self.assertIn("/* (deprecated: gone * / body { display: none }) */", css)
        self.assertNotIn("*/ body", css)

    def test_a_type_that_is_not_a_string_is_named(self):
        """S1 (the 2026-10-14 audit): a `$type` of 5, ["color"] or true over an
        object value was an AttributeError in read_tokens and every gate above
        it. The token, or the group, is left out and named."""
        doc = {"five": {"$type": 5, "a": {"$value": {"colorSpace": "srgb", "components": [1, 0, 0]}}},
               "list": {"b": {"$type": ["color"], "$value": {"colorSpace": "srgb", "components": [0, 1, 0]}}},
               "flag": {"$type": True, "c": {"$value": {"value": 4, "unit": "px"}}},
               "brand": {"$type": "color", "500": {"$value": "#2563eb"}}}
        toks, problems = self.dtcg.tokens(doc)
        self.assertEqual(["--brand-500"], [t.name for t in toks])
        self.assertEqual({"five": "`$type` is 5, not a string, so this is not read",
                          "list/b": "`$type` is [\"color\"], not a string, so this is not read",
                          "flag": "`$type` is true, not a string, so this is not read"}, dict(problems))
        tokens = self.read(doc)
        self.assertEqual({"500": "#2563eb"}, tokens.ramps["brand"])
        self.assertNotIn("five", json.dumps(tokens.values()))
        legacy = self.write("legacy.json", json.dumps({"a": {"value": "#ffffff", "type": 5}}))
        proc = run_py("figma-variables-sync", "figma_audit", legacy, cwd=self.tmp)   # figma_common.dtcg_type
        self.assertNotIn("Traceback", output(proc))
        self.assertIn(proc.returncode, (0, 1), output(proc))

    def test_a_deprecation_that_is_neither_a_string_nor_a_boolean_is_named(self):
        """S10 (Codex on #137): a `$deprecated` of any JSON type was carried as
        the reason. A string or a boolean is read (false undoes a group's);
        anything else is named, and the token keeps what it inherits."""
        doc = {"ink": {"$type": "color", "$value": "#111111", "$deprecated": {"reason": "x"}},
               "old": {"$type": "color", "$deprecated": "use ink",
                       "a": {"$value": "#222222", "$deprecated": 5},
                       "b": {"$value": "#333333", "$deprecated": False}},
               "odd": {"$type": "color", "$deprecated": [1], "c": {"$value": "#444444"}}}
        toks, problems = self.dtcg.tokens(doc)
        self.assertEqual({"--ink": False, "--old-a": "use ink", "--old-b": False, "--odd-c": False},
                         {t.name: t.deprecated for t in toks})
        self.assertEqual(["ink", "old/a", "odd"], [where for where, _ in problems])
        self.assertIn("`$deprecated` is {\"reason\": \"x\"}, neither a string nor a boolean", problems[0][1])

    def test_a_tokens_css_converts_whatever_the_project_lists(self):
        self.write(".git/HEAD", "x\n")
        self.write(".design-suite.json", '{"schema": 1, "tokens": "missing.json"}')
        proc = run_py("figma-variables-sync", "figma_to_tokens", self.write("t.css", ":root { --ink: #111111; }\n"),
                      "--format", "dtcg", cwd=self.tmp)
        self.assertEqual(0, proc.returncode, output(proc))
        self.assertEqual("#111111", json.loads(proc.stdout)["ink"]["$value"]["hex"])


class TheProposalIsDtcgToo(TempDirTest):
    """LC-B2: cluster_values writes its proposal as DTCG tokens.json."""

    def test_the_proposal_writes_tokens_json(self):
        self.write("src/app.css", ".btn { background: #2f6df6; color: #ffffff; padding: 16px; }\n")
        run_py("design-token-migration", "extract_literals", "src", "--format", "json", "-o", "literals.json",
               cwd=self.tmp)
        proc = run_py("design-token-migration", "cluster_values", "literals.json", "-o", "out", cwd=self.tmp)
        self.assertEqual(0, proc.returncode, output(proc))
        self.assertRegex(output(proc), r"tokens\.json +DTCG 2025\.10; \d+ value\(s\) it cannot type left out")
        doc = json.loads((self.tmp / "out" / "tokens.json").read_bytes())
        dtcg = dtcg_module()
        names = {t.name for t in dtcg.tokens(doc)[0]}
        pc = load_script("design-system-docs", "project_config")
        css = pc.read_tokens([self.tmp / "out" / "tokens.css"]).values()
        self.assertGreater(len(names), 100)
        self.assertLessEqual(names, set(css))
        self.assertTrue(re.match(r"oklch|srgb", doc["accent"]["500"]["$value"]["colorSpace"]))


DEPRECATING = {"brand": {"$type": "color", "$root": {"$value": "#123456"}, "hover": {"$value": "#234567"}},
               "bg": {"$type": "color", "brand": {"$value": "{brand.$root}"}},
               "old": {"$type": "color", "$deprecated": "Please use {bg.brand} instead",
                       "accent": {"$value": "{brand.hover}"}, "kept": {"$value": "#345678", "$deprecated": False}},
               "legacy": {"$type": "color", "$value": "#456789", "$deprecated": True},
               "gone": {"$type": "color", "$value": "#567890"}}


class DeprecationsReachTheLedger(TempDirTest):
    """P31 part 4 (LC-C2, LC-B2): a DTCG file's `$deprecated` reaches the
    release gate. A removal the old file had already marked failed the gate as
    if nobody had been warned, and the ledger could not take the marks."""

    def setUp(self):
        super().setUp()
        self.write("v1.tokens.json", json.dumps(DEPRECATING))
        nxt = json.loads(json.dumps(DEPRECATING))
        for group, name in (("old", "accent"), ("old", "kept"), (None, "legacy"), (None, "gone")):
            del (nxt[group] if group else nxt)[name]
        self.write("v2.tokens.json", json.dumps(nxt))

    def diff(self, *args):
        proc = run_py("design-system-versioning", "diff_system", "v1.tokens.json", "v2.tokens.json",
                      "--format", "json", "--deprecations", "deprecations.json", *args, cwd=self.tmp)
        return proc, json.loads(proc.stdout)

    def test_a_removal_the_old_file_deprecated_passes_the_gate(self):
        proc, report = self.diff()
        failing = {c["subject"] for c in report["changes"] if c["severity"] == "major" and not c["deprecation"]}
        self.assertEqual({"--old-kept", "--gone"}, failing)        # unmarked, or marked not deprecated
        marked = {c["subject"]: c["deprecation"] for c in report["changes"] if c["deprecation"]}
        self.assertEqual({"--old-accent", "--legacy"}, set(marked))
        self.assertEqual("--bg-brand", marked["--old-accent"]["replacement"])
        self.assertEqual("$deprecated in v1.tokens.json", marked["--old-accent"]["marked"])
        self.assertEqual(1, proc.returncode, output(proc))      # --gone and --old-kept still fail it
        text = run_py("design-system-versioning", "diff_system", "v1.tokens.json", "v2.tokens.json",
                      "--deprecations", "deprecations.json", cwd=self.tmp)
        self.assertIn("deprecation  marked: $deprecated in v1.tokens.json", output(text))

    def test_the_ledger_imports_the_marks(self):
        proc = run_py("design-system-versioning", "deprecate", "import", "v1.tokens.json", "--since", "2.1.0",
                      "--removal", "3.0.0", "--date", "2026-10-11", cwd=self.tmp)
        self.assertEqual(0, proc.returncode, output(proc))
        self.assertIn("recorded: 2 token(s) marked $deprecated, 0 already in deprecations.json", output(proc))
        ledger = json.loads((self.tmp / "deprecations.json").read_bytes())
        entries = {e["name"]: e for e in ledger["deprecations"]}
        self.assertEqual({"--old-accent", "--legacy"}, set(entries))
        self.assertEqual(("--bg-brand", "mechanical", "Please use {bg.brand} instead"),
                         tuple(entries["--old-accent"][k] for k in ("replacement", "codemod", "reason")))
        self.assertEqual(("", "none", ""), tuple(entries["--legacy"][k] for k in ("replacement", "codemod", "reason")))
        again = run_py("design-system-versioning", "deprecate", "import", "v1.tokens.json", "--since", "2.2.0",
                       "--removal", "3.0.0", cwd=self.tmp)
        self.assertIn("recorded: 0 token(s) marked $deprecated, 2 already in", output(again))
        self.assertEqual("2.1.0", json.loads((self.tmp / "deprecations.json").read_bytes())
                         ["deprecations"][0]["since"])                     # a ledger entry is kept
        _, report = self.diff()
        recorded = {c["subject"]: c["deprecation"] for c in report["changes"] if c["deprecation"]}
        self.assertEqual("2.1.0", recorded["--old-accent"]["since"])       # the ledger's record wins

    def test_the_removal_window_still_binds(self):
        proc = run_py("design-system-versioning", "deprecate", "import", "v1.tokens.json", "--since", "3.0.0",
                      "--removal", "3.0.0", cwd=self.tmp)
        self.assertEqual(2, proc.returncode, output(proc))
        self.assertFalse((self.tmp / "deprecations.json").exists())

    def test_a_later_file_that_sets_a_token_again_takes_the_mark_off(self):
        self.write("fix.tokens.json", json.dumps({"legacy": {"$type": "color", "$value": "#000000"}}))
        pc = load_script("design-system-versioning", "project_config")
        marks = pc.read_deprecations([self.tmp / "v1.tokens.json", self.tmp / "fix.tokens.json"])
        self.assertEqual({"--old-accent": "Please use {bg.brand} instead"}, marks)
        self.assertEqual("--brand", pc.replacement_of("use {brand.$root}"))
        self.assertEqual("", pc.replacement_of(True))

    def test_a_later_css_or_contract_file_takes_the_mark_off(self):
        # CodeRabbit on #106: read_tokens() lets a tokens.css or a contract.json
        # set a token again, and the DTCG file's mark outlived its value.
        self.write("tokens.css", "@layer tokens {\n  :root {\n    --legacy: #000000;\n  }\n}\n")
        self.write("contract.json", json.dumps({"schema": "web-design-suite/contract/1",
                                                "roles": {"--old-accent": "var(--brand)"}}))
        pc = load_script("design-system-versioning", "project_config")
        v1, css, contract = (self.tmp / n for n in ("v1.tokens.json", "tokens.css", "contract.json"))
        self.assertEqual({"--old-accent": "Please use {bg.brand} instead"}, pc.read_deprecations([v1, css]))
        self.assertEqual({"--legacy": True}, pc.read_deprecations([v1, contract]))
        self.assertEqual({"--old-accent", "--legacy"}, set(pc.read_deprecations([css, contract, v1])))  # control
        proc = run_py("design-system-versioning", "deprecate", "import", "v1.tokens.json", "tokens.css",
                      "--since", "2.1.0", "--removal", "3.0.0", cwd=self.tmp)
        self.assertEqual(0, proc.returncode, output(proc))
        self.assertIn("recorded: 1 token(s) marked $deprecated", output(proc))


class ASnapshotAgainstItsStylesheet(TempDirTest):
    """The 3.6.0 live check: a published DTCG file against the stylesheet it
    was written from read 27 primitives as edited (`oklch(88% …)` for the
    source's `oklch(88.0% …)`, `0px 1px 2px 0px …` for `0 1px 2px …`,
    `cubic-bezier(0, 0, 1, 1)` for `linear`), and the 53 tokens a DTCG file
    cannot hold as added: a major release for an unchanged system. The file
    now records those 53 with their values, and diff_system reads them back
    (Codex on #119, three findings)."""

    EXT = "io.github.vybecode-ltd.web-design-suite"

    def diff(self, old, new):
        proc = run_py("design-system-versioning", "diff_system", old, new, "--format", "json",
                      cwd=self.tmp)
        self.assertIn(proc.returncode, (0, 1), output(proc))
        report = json.loads(proc.stdout)
        return [(c["kind"], c["subject"]) for c in report["changes"]], report["notes"]

    def publish(self):
        proc = run_py("figma-variables-sync", "figma_to_tokens", str(STARTER), "--format", "dtcg",
                      "--out-dir", "published", "--quiet", cwd=self.tmp)
        self.assertIn(proc.returncode, (0, 1), output(proc))   # 1: written, the untyped values named
        return "published/tokens.json"

    def starter_with(self, old, new):
        css = STARTER.read_bytes().decode("utf-8")
        self.assertEqual(1, css.count(old))
        self.write("tokens.css", css.replace(old, new))
        return "tokens.css"

    def test_an_unchanged_system_is_no_change(self):
        published = self.publish()
        held = json.loads((self.tmp / published).read_bytes())["$extensions"][self.EXT]["notWritten"]
        self.assertEqual(53, len(held))
        self.assertEqual("clamp(1rem, 0.8208rem + 0.755vw, 1.5rem)", held["--space-fluid-sm"])
        for old in (published, "published/tokens.resolver.json"):   # a resolver's, in its sources
            with self.subTest(old=old):
                self.assertEqual([], self.diff(old, str(STARTER))[0])

    def test_the_other_way_is_no_change_either(self):
        """Codex on #119: a stylesheet against its DTCG export read the 53 as
        removed, a major bump that failed the names gate."""
        self.assertEqual([], self.diff(str(STARTER), self.publish())[0])

    def test_a_token_added_since_is_still_added(self):
        """Codex on #119: what DTCG cannot hold is not therefore old."""
        published = self.publish()
        new = self.starter_with("--accent-200: oklch(88.0% 0.078 42);",
                                "--accent-200: oklch(88.0% 0.078 42);\n    --size-hero: clamp(2rem, 1rem + 4vw, 4rem);")
        self.assertEqual([("tier1-added", "--size-hero")], self.diff(published, new)[0])

    def test_a_recorded_token_that_changed_is_a_change(self):
        """Codex on #119: the record kept names alone, so a new clamp() for a
        recorded token went unseen."""
        published = self.publish()
        new = self.starter_with("--space-fluid-sm:  clamp(1rem,    0.8208rem + 0.755vw, 1.5rem);",
                                "--space-fluid-sm:  clamp(1rem, 0.75rem + 1vw, 1.5rem);")
        # as a stylesheet against the stylesheet reports it: the starter's tiers are by name
        self.assertEqual([("tier2-repointed", "--space-fluid-sm")], self.diff(published, new)[0])

    def test_a_record_of_another_shape_is_no_record(self):
        published = self.publish()
        doc = json.loads((self.tmp / published).read_bytes())
        for own in ("x", {"notWritten": "--space-fluid-sm"}, {"notWritten": ["--space-fluid-sm"]},
                    {"notWritten": {"--space-fluid-sm": 5, "space": "1rem"}}):
            with self.subTest(own=own):
                doc["$extensions"] = {self.EXT: own}
                self.write("other.tokens.json", json.dumps(doc))
                changes, _notes = self.diff("other.tokens.json", str(STARTER))
                self.assertEqual(53, len([c for c in changes if c[0].endswith("-added")]))
        doc["$extensions"] = []
        self.write("other.tokens.json", json.dumps(doc))
        self.assertEqual(53, len(self.diff("other.tokens.json", str(STARTER))[0]))

    def test_every_listed_file_s_record_is_read(self):
        """Codex on #119: with several DTCG files in `.design-suite.json`, the
        record was read from the first alone."""
        self.publish()
        extra, _ = dtcg_module().document([("--extra", "4px"), ("--size-hero", "clamp(2rem, 1rem + 4vw, 4rem)")])
        self.write("published/extra.tokens.json", json.dumps(extra))
        self.write(".git/HEAD", "x\n")
        self.write(".design-suite.json", json.dumps(
            {"schema": 1, "tokens": ["published/tokens.json", "published/extra.tokens.json"]}))
        old = self.starter_with("--accent-200: oklch(88.0% 0.078 42);",
                                "--accent-200: oklch(88.0% 0.078 42);\n    --extra: 4px;\n"
                                "    --size-hero: clamp(2rem, 1rem + 4vw, 4rem);")
        proc = run_py("design-system-versioning", "diff_system", old, "--format", "json", cwd=self.tmp)
        self.assertIn(proc.returncode, (0, 1), output(proc))
        self.assertEqual([], json.loads(proc.stdout)["changes"])

    def test_a_resolver_reads_its_default_contexts_record_only(self):
        """Codex on #119: a record in a context the default does not select
        (the dark theme's file) was read into the default snapshot."""
        self.publish()
        dark = json.loads((self.tmp / "published" / "theme-dark.json").read_bytes())
        dark["$extensions"] = {self.EXT: {"notWritten": {"--size-hero": "clamp(2rem, 1rem + 4vw, 4rem)"}}}
        self.write("published/theme-dark.json", json.dumps(dark))
        self.assertEqual([], self.diff("published/tokens.resolver.json", str(STARTER))[0])

    def test_a_recorded_token_keeps_its_deprecation(self):
        """Codex on #119: a deprecated token the file could not hold lost its
        mark, so removing it failed the names gate."""
        dtcg = dtcg_module()
        v1, _ = dtcg.document([("--space-4", "1rem"), ("--hero", "clamp(1rem, 2vw, 2rem)")],
                              deprecated={"--hero": "Use {space.4} instead"})
        self.assertEqual({"--hero": "Use {space.4} instead"}, dtcg.not_written_marks(v1))
        self.write("v1.tokens.json", json.dumps(v1))
        self.write("v2.tokens.json", json.dumps(dtcg.document([("--space-4", "1rem")])[0]))
        self.write("deprecations.json", json.dumps({"schema": "design-system-versioning/deprecations@1",
                                                    "deprecations": []}))
        proc = run_py("design-system-versioning", "diff_system", "v1.tokens.json", "v2.tokens.json",
                      "--format", "json", "--deprecations", "deprecations.json", cwd=self.tmp)
        self.assertEqual(0, proc.returncode, output(proc))
        gone = {c["subject"]: c for c in json.loads(proc.stdout)["changes"]}
        self.assertEqual("$deprecated in v1.tokens.json", gone["--hero"]["deprecation"]["marked"])

    def test_a_quoted_keyword_is_another_family(self):
        """Codex on #119: `"serif"` names a family called serif, `serif` the
        generic one. Any other name is the same family quoted or not."""
        self.write("v1/tokens.css", ':root {\n  --font-display: "serif";\n  --font-body: "Inter", sans-serif;\n}\n')
        self.write("v2/tokens.css", ":root {\n  --font-display: serif;\n  --font-body: Inter, sans-serif;\n}\n")
        self.assertEqual([("tier1-value-changed", "--font-display")],
                         self.diff("v1/tokens.css", "v2/tokens.css")[0])

    def test_a_spelling_is_not_an_edit(self):
        css = STARTER.read_bytes().decode("utf-8")
        respelled = (css.replace("--accent-200: oklch(88.0% 0.078 42);", "--accent-200: oklch(88% 0.078 42);")
                     .replace("--shadow-xs:  0 1px 2px  oklch(0% 0 0 / 0.05);",
                              "--shadow-xs: 0px 1px 2px 0px oklch(0% 0 0 / 0.050);")
                     .replace("--ease-linear:  linear;", "--ease-linear: cubic-bezier(0, 0, 1, 1);"))
        self.assertEqual(3, sum(a != b for a, b in zip(css.splitlines(), respelled.splitlines())))
        self.write("v1/tokens.css", respelled)                 # one name: a file's own is compared too
        self.write("v2/tokens.css", css)
        self.assertEqual([], self.diff("v1/tokens.css", "v2/tokens.css")[0])

    def test_a_real_edit_is_still_one(self):
        """The guard: the alignment must not swallow a change of value."""
        css = STARTER.read_bytes().decode("utf-8").replace(
            "--accent-200: oklch(88.0% 0.078 42);", "--accent-200: oklch(90% 0.078 42);")
        self.write("tokens.css", css)
        self.assertEqual([("tier1-value-changed", "--accent-200")],
                         self.diff(self.publish(), "tokens.css")[0])


THEMED_CSS = """@layer tokens {
  :root {
    --neutral-0: #ffffff;
    --neutral-900: #1f1d1b;
    --accent-500: #2563eb;
    --bg-surface: var(--neutral-0);
    --fg-default: var(--neutral-900);
    --space-4: 1rem;
    --density: 1;
  }
  [data-theme="dark"] {
    --bg-surface: var(--neutral-900);
    --fg-default: var(--neutral-0);
  }
  [data-density="compact"] {
    --density: 0.875;
  }
}
"""
BLOCK = re.compile(r"^  ([^{}\n]+?) ?\{\n?(.*?)^  \}", re.M | re.S)
DECLARATION = re.compile(r"^\s*(--[\w-]+):\s*([^;]+);", re.M)


def css_blocks(text):
    """{selector: {--name: value}} for each block of a tokens.css."""
    return {m.group(1).strip(): dict(DECLARATION.findall(m.group(2))) for m in BLOCK.finditer(text)}


class TheResolver(TempDirTest):
    """P31 part 3 (LC-C2, LC-B2): themes through the DTCG resolver module.
    `--format dtcg` wrote the default mode alone and named each theme as left
    out, and a `*.resolver.json` was not read at all."""

    def to_dtcg(self, src, *args):
        return run_py("figma-variables-sync", "figma_to_tokens", src, "--format", "dtcg", "--out-dir", "dtcg",
                      *args, cwd=self.tmp)

    def to_css(self, resolver, *args):
        proc = run_py("figma-variables-sync", "figma_to_tokens", resolver, "--color-format", "hex", *args,
                      cwd=self.tmp)
        return proc, proc.stdout.decode("utf-8").replace("\r\n", "\n")

    def test_a_tokens_css_round_trips_through_a_resolver(self):
        src = self.write("tokens.css", THEMED_CSS)
        proc = self.to_dtcg(src)
        self.assertEqual(0, proc.returncode, output(proc))
        out = self.tmp / "dtcg"
        self.assertEqual(["density-compact.json", "theme-dark.json", "tokens.json", "tokens.resolver.json"],
                         sorted(f.name for f in out.iterdir()))
        resolver = json.loads((out / "tokens.resolver.json").read_bytes())
        self.assertEqual("2025.10", resolver["version"])
        self.assertEqual({"light": [], "dark": [{"$ref": "theme-dark.json"}]},
                         resolver["modifiers"]["theme"]["contexts"])
        self.assertEqual("light", resolver["modifiers"]["theme"]["default"])
        self.assertEqual("default", resolver["modifiers"]["density"]["default"])
        self.assertEqual([{"$ref": "#/sets/base"}, {"$ref": "#/modifiers/theme"}, {"$ref": "#/modifiers/density"}],
                         resolver["resolutionOrder"])
        dark = json.loads((out / "theme-dark.json").read_bytes())
        self.assertEqual({"$type": "color", "$value": "{neutral.900}"}, dark["bg"]["surface"])
        self.assertNotIn("neutral", dark)                       # its overrides only
        proc, text = self.to_css(out / "tokens.resolver.json")
        self.assertEqual(css_blocks(THEMED_CSS), css_blocks(text), output(proc))

    def test_the_starters_themes_survive_the_trip(self):
        proc = self.to_dtcg(STARTER)
        self.assertEqual(1, proc.returncode, output(proc))      # written, with what it left out
        self.assertIn("[data-theme=\"dark\"] .inverse: 9 token(s) left out", output(proc))
        self.assertIn("@media (prefers-reduced-motion: reduce) :root: 6 token(s) left out", output(proc))
        _, text = self.to_css(self.tmp / "dtcg" / "tokens.resolver.json")
        before, after = css_blocks(STARTER.read_bytes().decode("utf-8")), css_blocks(text)
        refs = {n: v for n, v in before['[data-theme="dark"]'].items() if v.startswith("var(")}
        self.assertGreater(len(refs), 20)
        for name, value in refs.items():
            # A dark value equal to the default is the default's: --full-themes keeps it.
            self.assertEqual(value, after['[data-theme="dark"]'].get(name, after[":root"].get(name)), name)
        self.assertEqual("0.875", after['[data-density="compact"]']["--density"])

    def test_a_tokens_studio_export_writes_its_themes(self):
        src = self.write("studio.json", json.dumps(STUDIO_REVIEW))
        proc = self.to_dtcg(src)
        self.assertNotIn("not written to DTCG", output(proc))
        resolver = json.loads((self.tmp / "dtcg" / "tokens.resolver.json").read_bytes())
        self.assertEqual({"light": [], "dark": [{"$ref": "theme-dark.json"}]},
                         resolver["modifiers"]["theme"]["contexts"])
        _, text = self.to_css(self.tmp / "dtcg" / "tokens.resolver.json")
        self.assertEqual({"--bg-surface": "var(--neutral-900)"}, css_blocks(text)['[data-theme="dark"]'])

    def test_a_resolver_is_read_as_modes(self):
        self.write("base.tokens.json", json.dumps(RESOLVER_BASE))
        self.write("dark.tokens.json", json.dumps(RESOLVER_DARK))
        src = self.write("app.resolver.json", json.dumps(RESOLVER))
        proc, text = self.to_css(src)
        blocks = css_blocks(text)
        self.assertEqual("var(--brand-600)", blocks[":root"]["--bg-surface"])            # its default: dark
        self.assertEqual("var(--brand-500)", blocks['[data-theme="light"]']["--bg-surface"])
        self.assertEqual("0.75rem", blocks[":root"]["--size"])                          # no default: the first
        self.assertEqual("1rem", blocks['[data-density="compact"]']["--size"])
        self.assertEqual("1rem", blocks[":root"]["--space-4"])                         # a set in a set
        self.assertEqual("#ff0000", blocks[":root"]["--accent"])                         # an inline set
        for why in ("`https://example.com/tokens.json` is a URL", "`gone.tokens.json` could not be read",
                    "`#/sets/base` is part of a cycle", "`#/modifiers/missing` names no set or modifier",
                    "names no default among its contexts: `small`"):
            self.assertIn(why, output(proc))

    def test_a_density_modifier_keeps_its_contexts_out_of_the_theme(self):
        data = {"version": "2025.10", "resolutionOrder": [
            {"type": "set", "name": "base", "sources": [{"gap": {"$type": "dimension",
                                                                  "$value": {"value": 16, "unit": "px"}}}]},
            {"type": "modifier", "name": "density", "default": "roomy", "contexts": {
                "roomy": [], "dark": [{"gap": {"$type": "dimension", "$value": {"value": 8, "unit": "px"}}}]}}]}
        _, text = self.to_css(self.write("d.resolver.json", json.dumps(data)))
        self.assertEqual({"--gap": "0.5rem"}, css_blocks(text)['[data-density="dark"]'])

    def test_a_pointer_may_name_one_source(self):
        """Codex on #105: the resolver module allows a pointer anywhere but a
        modifier or resolutionOrder, and only `#/sets/<name>` was read."""
        data = {"version": "2025.10",
                "sets": {"base": {"sources": [{"ink": {"$type": "color", "$value": "#111111"}},
                                              {"$ref": "base.tokens.json"}]}},
                "modifiers": {"theme": {"default": "light", "contexts": {
                    "light": [], "dark": [{"$ref": "#/sets/base/sources/0", "ink": {"$type": "color",
                                                                                     "$value": "#eeeeee"}}]}}},
                "resolutionOrder": [{"type": "set", "name": "first", "sources": [{"$ref": "#/sets/base/sources/1"}]},
                                    {"$ref": "#/modifiers/theme"},
                                    {"type": "set", "name": "bad", "sources": [{"$ref": "#/resolutionOrder/0"},
                                                                               {"$ref": "#/modifiers/theme/contexts"}]}]}
        self.write("base.tokens.json", json.dumps(RESOLVER_BASE))
        proc, text = self.to_css(self.write("p.resolver.json", json.dumps(data)))
        blocks = css_blocks(text)
        self.assertEqual("var(--brand-500)", blocks[":root"]["--bg-surface"])           # a file, by pointer
        self.assertEqual("#eeeeee", blocks['[data-theme="dark"]']["--ink"])              # a source, overridden
        self.assertEqual(2, output(proc).count("only resolutionOrder may point at a modifier"), output(proc))

    def test_a_context_keeps_the_spaces_in_its_value(self):
        """Codex on #105: `[data-theme="high contrast"]` became `highcontrast`,
        and a resolver's context came back slugged, so the selector no longer
        matched the page's attribute."""
        css = THEMED_CSS.replace('[data-theme="dark"]', '[data-theme="high contrast"]')
        proc = self.to_dtcg(self.write("tokens.css", css))
        resolver = json.loads((self.tmp / "dtcg" / "tokens.resolver.json").read_bytes())
        self.assertEqual({"light": [], "high contrast": [{"$ref": "theme-high-contrast.json"}]},
                         resolver["modifiers"]["theme"]["contexts"], output(proc))
        _, text = self.to_css(self.tmp / "dtcg" / "tokens.resolver.json")
        self.assertEqual(css_blocks(css), css_blocks(text))

    def test_a_source_outside_the_resolvers_folder_is_not_read(self):
        """CodeRabbit on #105: `..` or an absolute name read any JSON file the
        user can read into the project's tokens, and the hooks read a cloned
        repository's token files on their own."""
        secret = self.write("secret.tokens.json", json.dumps({"leak": {"$type": "number", "$value": 1}}))
        self.write("design/base.tokens.json", json.dumps(RESOLVER_BASE))
        data = {"version": "2025.10", "resolutionOrder": [{"type": "set", "name": "s", "sources": [
            {"$ref": "base.tokens.json"}, {"$ref": "../secret.tokens.json"}, {"$ref": "sub/..\\..\\secret.tokens.json"},
            {"$ref": str(secret)}, {"$ref": "/etc/x.json"}, {"$ref": "C:secret.tokens.json"}]}]}
        src = self.write("design/app.resolver.json", json.dumps(data))
        pc = load_script("design-system-docs", "project_config")
        self.assertNotIn("--leak", pc.read_tokens([src]).values())
        self.assertEqual("var(--brand-500)", pc.read_tokens([src]).roles["--bg-surface"])
        proc, _ = self.to_css(src)
        self.assertEqual(5, output(proc).count("is outside the resolver's folder"), output(proc))

    def test_a_link_out_of_the_resolvers_folder_is_not_followed(self):
        """Codex on #105: a symlink or a junction inside the folder that
        points outside it passed the name check, and its JSON was read."""
        outside = self.write("outside/secret.tokens.json", json.dumps({"leak": {"$type": "number", "$value": 1}}))
        self.write("design/base.tokens.json", json.dumps(RESOLVER_BASE))
        link = self.tmp / "design" / "linked"
        if os.name == "nt":
            import _winapi
            _winapi.CreateJunction(str(outside.parent), str(link))
            self.addCleanup(os.rmdir, link)              # the junction, never its target
        else:
            link.symlink_to(outside.parent, target_is_directory=True)
            self.addCleanup(link.unlink)
        data = {"version": "2025.10", "resolutionOrder": [{"type": "set", "name": "s", "sources": [
            {"$ref": "base.tokens.json"}, {"$ref": "linked/secret.tokens.json"}]}]}
        src = self.write("design/app.resolver.json", json.dumps(data))
        pc = load_script("design-system-docs", "project_config")
        tokens = pc.read_tokens([src])
        self.assertNotIn("--leak", tokens.values())
        self.assertEqual("var(--brand-500)", tokens.roles["--bg-surface"])
        proc, _ = self.to_css(src)
        self.assertIn("`linked/secret.tokens.json` is outside the resolver's folder", output(proc))
        script = (f"import {{ readTokens }} from {json.dumps((PLUGIN / 'shared' / 'project_config.mjs').as_uri())};\n"
                  f"console.log(JSON.stringify(readTokens([{json.dumps(str(src))}])));\n")
        node = subprocess.run([NODE, "--input-type=module", "-e", script], cwd=self.tmp, env=env(),
                              capture_output=True, timeout=120)
        self.assertEqual(0, node.returncode, output(node))
        self.assertNotIn("leak", node.stdout.decode("utf-8"))
        self.assertIn("--bg-surface", node.stdout.decode("utf-8"))

    def test_a_context_with_a_quote_round_trips(self):
        """Codex on #105: `[data-theme="say \\"hi\\""]`, which the reader
        writes for a context with a quote, ended at the escaped quote, so the
        block was dropped on the way back to DTCG."""
        css = THEMED_CSS.replace('[data-theme="dark"]', '[data-theme="say \\"hi\\""]')
        proc = self.to_dtcg(self.write("tokens.css", css))
        resolver = json.loads((self.tmp / "dtcg" / "tokens.resolver.json").read_bytes())
        self.assertIn('say "hi"', resolver["modifiers"]["theme"]["contexts"], output(proc))
        _, text = self.to_css(self.tmp / "dtcg" / "tokens.resolver.json")
        self.assertEqual(css_blocks(css), css_blocks(text))
        hex_css = THEMED_CSS.replace('[data-theme="dark"]', "[data-theme='say \\22 hi\\22']")
        self.to_dtcg(self.write("hex.css", hex_css), "--quiet")
        resolver = json.loads((self.tmp / "dtcg" / "tokens.resolver.json").read_bytes())
        self.assertIn('say "hi"', resolver["modifiers"]["theme"]["contexts"])

    def test_odd_shapes_are_named_not_a_traceback(self):
        """CodeRabbit on #105: a list `default` raised TypeError, and a list
        `sets` an AttributeError, in the Python reader."""
        data = {"version": "2025.10", "sets": ["x"],
                "modifiers": {"m": {"default": ["a"], "contexts": {"a": [{"x": {"$type": "number", "$value": 1}}],
                                                                   "b": []}}},
                "resolutionOrder": [{"type": "set", "name": "s", "sources": [{"$ref": "#/sets/x"}]},
                                    {"$ref": "#/modifiers/m"}]}
        dtcg = dtcg_module()
        doc, problems = dtcg.resolver_document(data, self.tmp)
        self.assertEqual({"x": {"$type": "number", "$value": 1}}, doc)
        self.assertEqual([None], [m.default for m in dtcg.resolver_modifiers(data)])
        self.assertIn(("sets/s/0", "`#/sets/x` points at no object in this resolver, so not read"), problems)

    def test_a_fan_out_of_sets_is_refused_not_expanded(self):
        dtcg = dtcg_module()
        sets = {f"s{i}": {"sources": [{"$ref": f"#/sets/s{i + 1}"}] * 10} for i in range(9)}
        sets["s9"] = {"sources": [{"x": {"$type": "number", "$value": 1}}]}
        doc, problems = dtcg.resolver_document({"version": "2025.10", "sets": sets,
                                                "resolutionOrder": [{"$ref": "#/sets/s0"}]}, self.tmp)
        self.assertEqual({}, doc)
        self.assertIn("expand past", problems[-1][1])

    def test_out_and_out_dir_are_one_or_the_other(self):
        src = self.write("tokens.css", THEMED_CSS)
        proc = self.to_dtcg(src, "--out", "x.json")
        self.assertEqual(2, proc.returncode, output(proc))
        self.assertFalse((self.tmp / "x.json").exists())

    def test_the_project_reads_a_resolvers_default(self):
        self.write("base.tokens.json", json.dumps(RESOLVER_BASE))
        self.write("dark.tokens.json", json.dumps(RESOLVER_DARK))
        src = self.write("app.resolver.json", json.dumps(RESOLVER))
        pc = load_script("design-system-docs", "project_config")
        tokens = pc.read_tokens([src])
        self.assertEqual("var(--brand-600)", tokens.roles["--bg-surface"])
        self.assertEqual({"500": "#123456", "600": "#234567"}, tokens.ramps["brand"])


RESOLVER_BASE = {"brand": {"$type": "color", "500": {"$value": "#123456"}, "600": {"$value": "#234567"}},
                 "bg": {"surface": {"$type": "color", "$value": "{brand.500}"}}}
RESOLVER_DARK = {"bg": {"surface": {"$type": "color", "$value": "{brand.600}"}}}
RESOLVER = {
    "version": "2025.10",
    "sets": {"base": {"sources": [{"$ref": "base.tokens.json"}, {"$ref": "#/sets/extra"}]},
             "extra": {"sources": [{"space": {"4": {"$type": "dimension", "$value": {"value": 1, "unit": "rem"}}}},
                                   {"$ref": "#/sets/base"}]},
             "web": {"sources": [{"$ref": "https://example.com/tokens.json"}, {"$ref": "gone.tokens.json"}]}},
    "modifiers": {"theme": {"contexts": {"light": [], "dark": [{"$ref": "dark.tokens.json"}]}, "default": "dark"},
                  "density": {"contexts": {
                      "small": [{"size": {"$type": "dimension", "$value": {"value": 12, "unit": "px"}}}],
                      "compact": [{"size": {"$type": "dimension", "$value": {"value": 16, "unit": "px"}}}]}}},
    "resolutionOrder": [{"$ref": "#/sets/base"}, {"$ref": "#/sets/web"}, {"$ref": "#/modifiers/theme"},
                        {"$ref": "#/modifiers/density"},
                        {"type": "set", "name": "inline", "sources": [{"accent": {"$type": "color", "$value": "#ff0000"}}]},
                        {"$ref": "#/modifiers/missing"}, 5],
}


if __name__ == "__main__":
    unittest.main()
