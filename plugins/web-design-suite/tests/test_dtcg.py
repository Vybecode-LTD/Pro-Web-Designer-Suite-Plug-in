"""P31 part 1: shared/dtcg.py, DTCG 2025.10 read and write (LC-C2, LC-B2).

Regressions covered (each fails on v3.5.0):
- a reference to a group's own token, `{brand.$root}` or `#/brand/$root`, the
  spelling the format gives it, was left unresolved;
- a group's `$deprecated` did not reach its tokens;
- a DTCG file in `.design-suite.json`'s tokens, or passed as `--tokens`, was
  refused as "not a contract.json", and diff_system refused one as a snapshot;
- there was no way to write DTCG: figma_to_tokens.py had no `--format dtcg`,
  a tokens.css could not be converted, and the migration proposal was CSS only.
"""
from __future__ import annotations

import importlib.util
import json
import re
import sys
import unittest

from wds_support import PLUGIN, SKILLS, TempDirTest, load_script, output, run_py

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
        self.assertEqual({"space"}, set(doc))

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
        from test_project_config import EXTENDS_CHAIN, EXTENDS_FAN
        for doc in (EXTENDS_CHAIN, EXTENDS_FAN):
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


if __name__ == "__main__":
    unittest.main()
