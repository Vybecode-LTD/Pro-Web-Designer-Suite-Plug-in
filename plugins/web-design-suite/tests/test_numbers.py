"""Numbers written in comments and prose hold (3.2.0).

Regressions covered:
- SS-A8: "Verified 8.22:1" in the dark theme sat above --fg-muted (neutral-300,
  13.80:1) but was neutral-400's ratio. A claim now names its pair —
  `Verified 4.60:1 (--neutral-500 on --neutral-100)` — so it can be recomputed.
- SS-A15: the fluid spacing clamps declare anchors of 380 and 1440px but their
  intercepts ran low, so they met their bounds near 400 and 1460px.
- SS-A15: tokens.css told readers to regenerate the fluid steps with
  scripts/generate_space_scale.py, which has never shipped.
- SS-A9, SS-C5 (3.3.0): the type generator only "approximately" reproduced
  tokens.css (9/11/13/16/20/25/31/39/49 against 11/12/14/16/18/22/28/35/44),
  SKILL.md's Phase 1 command printed 9.26px and 11.11px steps, and a step
  under 11px was only a warning.
- SS-B5 (3.3.0): typography.md called a rem intercept sufficient for zoom. A
  fluid size also needs its maximum within 2.5 times its minimum.
"""
from __future__ import annotations

import importlib.util
import json
import re
import shlex
import sys
import unittest

from wds_support import PLUGIN, SKILLS, TempDirTest, output, run_py

STUDIO = SKILLS / "web-design-studio"
TOKENS = STUDIO / "assets" / "starter" / "styles" / "tokens.css"
TYPOGRAPHY = STUDIO / "references" / "typography.md"
TEXT_STEP = re.compile(r"(--text-[a-z0-9]+):\s*([^;]+);")
FLUID_TEXT = re.compile(r"(--text-[a-z0-9]+):\s*clamp\(([\d.]+)rem,\s*([\d.]+)rem \+ ([\d.]+)vw,\s*([\d.]+)rem\)")
CLAIM = re.compile(r"(\d+\.\d\d):1\s+\((--[a-z0-9-]+) on (--[a-z0-9-]+)\)")   # may wrap
BARE_VERIFIED = re.compile(r"(?i)verified:?\s+(\d+\.\d\d):1(?!\s+\(--)")


def texts():
    for path in sorted(SKILLS.rglob("*")):
        if path.suffix in {".css", ".md", ".json", ".html"}:
            yield path, path.read_text(encoding="utf-8")


class VerifiedRatios(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location(
            "wds_ramp_numbers", STUDIO / "scripts" / "generate_color_ramp.py")
        cls.gen = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = cls.gen
        spec.loader.exec_module(cls.gen)
        cls.primitives = dict(re.findall(r"(--[a-z]+-\d+):\s*(oklch\([^)]*\))",
                                         TOKENS.read_text(encoding="utf-8")))

    def ratio(self, fg: str, bg: str) -> float:
        return self.gen.contrast_ratio_oklch(self.gen.parse_color(self.primitives[fg]),
                                             self.gen.parse_color(self.primitives[bg]))

    def test_every_verified_ratio_names_its_pair(self):
        for path, text in texts():
            for m in BARE_VERIFIED.finditer(text):
                with self.subTest(file=str(path.relative_to(SKILLS)), claim=m.group(0)):
                    self.fail("a verified ratio must say what it measured: "
                              "`Verified 4.60:1 (--neutral-500 on --neutral-100)`")

    def test_every_named_ratio_is_the_ratio(self):
        checked = 0
        for path, text in texts():
            for m in CLAIM.finditer(text):
                claimed, fg, bg = float(m.group(1)), m.group(2), m.group(3)
                if fg not in self.primitives or bg not in self.primitives:
                    continue
                checked += 1
                with self.subTest(file=str(path.relative_to(SKILLS)), claim=m.group(0)):
                    self.assertAlmostEqual(self.ratio(fg, bg), claimed, delta=0.006)
        self.assertGreaterEqual(checked, 4)


class FluidClamps(unittest.TestCase):
    """Solve each `clamp(min, c + m·vw, max)` for the widths where it reaches
    its bounds; they must be the anchors the file declares (380 and 1440)."""

    ANCHORS = (380, 1440)

    def test_every_fluid_step_reaches_its_bounds_at_the_anchors(self):
        clamp = re.compile(r"(--[\w-]+):\s*clamp\(([\d.]+)rem,\s*([\d.]+)rem \+ ([\d.]+)vw,\s*([\d.]+)rem\)")
        found = clamp.findall(TOKENS.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(found), 6)
        for name, lo, c, m, hi in found:
            lo_px, c_px, hi_px, per_px = float(lo) * 16, float(c) * 16, float(hi) * 16, float(m) / 100
            reach = ((lo_px - c_px) / per_px, (hi_px - c_px) / per_px)
            with self.subTest(token=name, reaches=tuple(round(r) for r in reach)):
                self.assertAlmostEqual(reach[0], self.ANCHORS[0], delta=2)
                self.assertAlmostEqual(reach[1], self.ANCHORS[1], delta=2)


class NamedScriptsExist(unittest.TestCase):

    def test_every_script_a_doc_names_ships(self):
        shipped = {p.name for p in SKILLS.glob("*/scripts/*") if p.suffix in {".py", ".mjs"}}
        self.assertGreater(len(shipped), 15)
        for path, text in texts():
            for name in sorted(set(re.findall(r"scripts/([a-z][a-z0-9_]*\.(?:py|mjs))\b", text))):
                with self.subTest(file=str(path.relative_to(SKILLS)), script=name):
                    self.assertIn(name, shipped)


def text_steps(css: str) -> dict:
    """`--text-*` declarations, with whitespace normalised."""
    return {name: " ".join(value.split()) for name, value in TEXT_STEP.findall(css)}


def fluid_text_steps() -> dict:
    """Each fluid `--text-*` in tokens.css as (min, intercept, vw, max), in px
    but for vw."""
    return {name: (float(lo) * 16, float(c) * 16, float(m), float(hi) * 16)
            for name, lo, c, m, hi in FLUID_TEXT.findall(TOKENS.read_text(encoding="utf-8"))}


def computed(step: tuple, viewport: float) -> float:
    lo, c, m, hi = step
    return min(hi, max(lo, c + m * viewport / 100))


def doc_commands(script: str):
    """(doc, args) for every command running `script` in the docs' code
    blocks, with continuation lines joined."""
    docs = [PLUGIN / "README.md", *sorted(SKILLS.glob("*/SKILL.md")),
            *sorted(SKILLS.glob("*/references/*.md"))]
    for doc in docs:
        text = doc.read_text(encoding="utf-8")
        for block in re.findall(r"^[ \t]*```[a-z]*\n(.*?)^[ \t]*```", text, flags=re.S | re.M):
            for line in re.sub(r"\\\n\s*", " ", block).splitlines():
                if script not in line:
                    continue
                words = shlex.split(line, comments=True)
                at = next(i for i, w in enumerate(words) if script in w)
                if words[0] == "python":
                    yield doc.relative_to(PLUGIN).as_posix(), words[at + 1:]


class TypeScale(TempDirTest):
    """The type generator reproduces tokens.css, the docs' commands run as
    written, and a step under 11px is refused unless forced."""

    def generate(self, *args):
        return run_py("web-design-studio", "generate_type_scale", *args, cwd=self.tmp)

    def assert_prints_the_starters_scale(self, proc):
        self.assertEqual(proc.returncode, 0, output(proc))
        printed = text_steps(proc.stdout.decode("utf-8"))
        starter = text_steps(TOKENS.read_text(encoding="utf-8"))
        self.assertEqual(len(starter), 11)
        self.assertEqual(printed, starter)

    def test_the_studio_preset_prints_the_starters_scale(self):
        self.assert_prints_the_starters_scale(self.generate("--preset", "studio", "--format", "css"))

    def test_with_no_scale_flags_the_studio_preset_is_the_default(self):
        self.assert_prints_the_starters_scale(self.generate("--format", "css"))

    def test_skill_md_phase_1_type_command_reproduces_the_starter(self):
        skill = (STUDIO / "SKILL.md").read_text(encoding="utf-8")
        phase = skill[skill.index("### Phase 1"):skill.index("### Phase 2")]
        item = phase[phase.index("**Type.**"):]
        command = re.search(r"python -m scripts\.generate_type_scale([^\n]*)", item).group(1)
        self.assert_prints_the_starters_scale(self.generate(*shlex.split(command)))

    def test_every_documented_type_command_runs_clean(self):
        commands = list(doc_commands("generate_type_scale"))
        self.assertGreaterEqual(len(commands), 4)
        for doc, args in commands:
            with self.subTest(doc=doc, args=" ".join(args)):
                proc = self.generate(*args)
                self.assertEqual(proc.returncode, 0, output(proc))
                self.assertEqual(proc.stderr.decode("utf-8"), "")

    def test_a_step_under_11px_is_refused_with_the_ways_out(self):
        for args, small in ((["--ratio", "1.2"], "9.26px"),
                            (["--ratio", "1.2", "--snap-px"], "9px")):
            with self.subTest(args=args):
                proc = self.generate(*args)
                self.assertEqual(proc.returncode, 2, output(proc))
                self.assertEqual(proc.stdout, b"")
                message = proc.stderr.decode("utf-8")
                for way in (f"--text-2xs is {small}", "--steps-down 2", "1.125",
                            "11.24px", "--allow-small"):
                    self.assertIn(way, message)

    def test_a_fluid_minimum_under_11px_is_refused(self):
        proc = self.generate("--ratio", "1.2", "--steps-down", "2", "--fluid", "380", "1440",
                             "--fluid-steps", "10")
        self.assertEqual(proc.returncode, 2, output(proc))
        self.assertIn("--text-xs is 9.26px", output(proc))
        self.assertIn("--fluid-steps", output(proc))

    def test_allow_small_emits_it_with_a_warning(self):
        proc = self.generate("--ratio", "1.2", "--allow-small", "--format", "css")
        self.assertEqual(proc.returncode, 0, output(proc))
        self.assertEqual(text_steps(proc.stdout.decode("utf-8"))["--text-2xs"], "0.5787rem")
        self.assertIn("warning: --text-2xs is 9.26px", proc.stderr.decode("utf-8"))

    def test_a_narrower_ratio_keeps_three_steps_down(self):
        """The control: the way out the refusal names works."""
        proc = self.generate("--ratio", "1.125", "--format", "css")
        self.assertEqual(proc.returncode, 0, output(proc))
        self.assertEqual(text_steps(proc.stdout.decode("utf-8"))["--text-2xs"], "0.7023rem")

    def test_the_preset_takes_no_scale_flags(self):
        proc = self.generate("--preset", "studio", "--ratio", "1.2")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("is a fixed scale", output(proc))

    def test_a_fluid_span_over_2_5_times_is_refused(self):
        proc = self.generate("--steps-down", "2", "--fluid", "380", "1440", "--fluid-min-ratio", "3")
        self.assertEqual(proc.returncode, 2, output(proc))
        self.assertIn("SC 1.4.4", output(proc))

    def test_a_snapped_fluid_span_over_2_5_times_is_refused(self):
        """Codex on #28: --snap-px rounds a fluid step's two ends apart, so a
        2.485 shrink emitted 16 -> 40.5px, a 2.53 times span."""
        proc = self.generate("--base", "16.2", "--ratio", "1.1", "--dual-ratio", "2.485",
                             "--steps-down", "0", "--steps-up", "1", "--snap-px",
                             "--fluid", "380", "1440", "--fluid-steps", "1", "--fluid-min-ratio", "2.485")
        self.assertEqual(proc.returncode, 2, output(proc))
        self.assertIn("--text-lg spans 16px to 40.5px, 2.53 times its minimum", output(proc))
        self.assertEqual(proc.stdout, b"")


    def test_fluid_space_prints_the_starters_fluid_spacing(self):
        proc = self.generate("--fluid-space", "--format", "css")
        self.assertEqual(proc.returncode, 0, output(proc))
        space = re.compile(r"(--space-fluid-[a-z]+):\s*([^;]+);")
        printed = {n: " ".join(v.split()) for n, v in space.findall(proc.stdout.decode("utf-8"))}
        starter = {n: " ".join(v.split()) for n, v in space.findall(TOKENS.read_text(encoding="utf-8"))}
        self.assertEqual(len(starter), 4)
        self.assertEqual(printed, starter)

    def test_fluid_space_needs_the_anchors(self):
        proc = self.generate("--steps-down", "2", "--fluid-space")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("--fluid-space solves the spacing for the type's viewport anchors", output(proc))


RAMP_STEP = re.compile(r"(--(?:accent|neutral)-\d+):\s*(oklch\([^)]*\))")


class ColourRamps(TempDirTest):
    """SS-A9, SS-B6, SS-B7, SS-C5: the colour generator reproduces the
    starter's ramps, keeps a brand's hex on request, and says how far the
    ramp moved it."""

    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location(
            "wds_ramp_colours", STUDIO / "scripts" / "generate_color_ramp.py")
        cls.gen = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = cls.gen
        spec.loader.exec_module(cls.gen)

    def generate(self, *args):
        return run_py("web-design-studio", "generate_color_ramp", *args, cwd=self.tmp)

    def values(self, css: str) -> dict:
        return {name: tuple(round(v, 4) for v in self.gen.parse_color(value))
                for name, value in RAMP_STEP.findall(css)}

    def assert_reproduce_the_starter(self, commands):
        printed = {}
        for args in commands:
            proc = self.generate(*args)
            self.assertEqual(proc.returncode, 0, output(proc))
            printed.update(self.values(proc.stdout.decode("utf-8")))
        starter = self.values(TOKENS.read_text(encoding="utf-8"))
        self.assertEqual(len(starter), 24)
        self.assertEqual(printed, starter)

    @staticmethod
    def commands_in(text: str) -> list:
        return [shlex.split(m) for m in re.findall(r"python -m scripts\.generate_color_ramp ([^\n]*)", text)]

    def test_skill_md_phase_1_colour_commands_reproduce_the_starter(self):
        skill = (STUDIO / "SKILL.md").read_text(encoding="utf-8")
        item = skill[skill.index("1. **Color.**"):skill.index("2. **Type.**")]
        commands = self.commands_in(item)
        self.assertEqual(len(commands), 2)
        self.assert_reproduce_the_starter(commands)

    def test_color_system_md_commands_reproduce_the_starter(self):
        doc = (STUDIO / "references" / "color-system.md").read_text(encoding="utf-8")
        section = doc[doc.index("The starter's ramps are"):doc.index("### 2.5")]
        commands = self.commands_in(section)
        self.assertEqual(len(commands), 2)
        self.assert_reproduce_the_starter(commands)

    def test_every_documented_colour_command_runs(self):
        commands = list(doc_commands("generate_color_ramp"))
        self.assertGreaterEqual(len(commands), 8)
        for doc, args in commands:
            with self.subTest(doc=doc, args=" ".join(args)):
                proc = self.generate(*args)
                self.assertEqual(proc.returncode, 0, output(proc))

    def test_the_neutral_500_clears_4_5_on_the_sunken_well(self):
        """SS-A9: NEUTRAL_L[500] was 0.580, which regenerated the 4.08:1
        --fg-subtle failure tokens.css fixed by hand."""
        ramp = {s.step: s for s in self.gen.build_ramp(
            self.gen.parse_color("oklch(58% 0.009 75)"), self.gen.DEFAULT_NEUTRAL_STEPS, neutral=True)}
        ratio = self.gen.contrast_ratio_oklch(*((s.L, s.C, s.H) for s in (ramp[500], ramp[100])))
        self.assertGreaterEqual(ratio, 4.5)

    def test_neutral_hue_sets_the_neutrals_hue(self):
        proc = self.generate("#e8440a", "--neutral", "--neutral-hue", "75", "--no-contrast")
        self.assertEqual(proc.returncode, 0, output(proc))
        hues = {round(h, 1) for _, c, h in self.values(proc.stdout.decode("utf-8")).values() if c}
        self.assertEqual(hues, {75.0})

    def test_the_new_flags_are_refused_where_they_mean_nothing(self):
        for args, why in ((["#e8440a", "--neutral-hue", "75"], "add --neutral"),
                          (["#e8440a", "--neutral", "--anchor-seed"], "accent ramp")):
            with self.subTest(args=args):
                proc = self.generate(*args)
                self.assertEqual(proc.returncode, 2)
                self.assertIn(why, output(proc))

    def test_anchor_seed_keeps_the_brand_hex(self):
        """SS-B6: #e8440a became --accent-500: #f14d1a, and appeared nowhere."""
        proc = self.generate("#e8440a", "--anchor-seed", "--format", "json")
        self.assertEqual(proc.returncode, 0, output(proc))
        step = json.loads(proc.stdout)["accent"]["500"]
        self.assertEqual(step["hex"], "#e8440a")
        lch = self.gen.parse_color(step["oklch"])
        self.assertEqual(self.gen.oklch_to_hex(*lch), "#e8440a")
        self.assertIn("--accent-500 is the seed, exactly", proc.stderr.decode("utf-8"))

    def test_anchor_seed_takes_the_step_nearest_in_lightness(self):
        proc = self.generate("oklch(48% 0.12 250)", "--anchor-seed", "--format", "json")
        self.assertEqual(proc.returncode, 0, output(proc))
        ramp = json.loads(proc.stdout)["accent"]
        self.assertEqual(self.gen.parse_color(ramp["700"]["oklch"]), self.gen.parse_color("oklch(48% 0.12 250)"))
        self.assertEqual(ramp["600"]["l"], 0.565)

    def test_the_report_gives_the_seeds_distance_from_500(self):
        proc = self.generate("#e8440a")
        self.assertEqual(proc.returncode, 0, output(proc))
        report = proc.stderr.decode("utf-8")
        self.assertIn("--accent-500 is oklch(64.5% 0.208 36)  #f14d1a: 0.024 from the seed", report)
        self.assertIn("--anchor-seed puts it at its nearest step", report)

    def test_color_system_md_quotes_the_report(self):
        doc = " ".join((STUDIO / "references" / "color-system.md").read_text(encoding="utf-8").split())
        seed = self.gen.parse_color("#e8440a")
        five = next(s for s in self.gen.build_ramp(seed, self.gen.DEFAULT_STEPS) if s.step == 500)
        self.assertIn(f"`#e8440a` is L {seed[0] * 100:.1f}%, and step 500 is {five.L * 100:.1f}%", doc)
        self.assertIn(f"is `{five.hex}`", doc)
        self.assertIn(f"(ΔE_OK {self.gen.delta_e_ok(seed, (five.L, five.C, five.H)):.3f} here)", doc)


class FluidTypeZoom(unittest.TestCase):
    """SS-B5: a fluid size passes SC 1.4.4 when its maximum is at most 2.5
    times its minimum, and the figures typography.md §10 quotes recompute."""

    WINDOW = 1440
    ZOOM_STEPS = (2.0, 2.5, 3.0, 4.0, 5.0)   # Chrome's zoom levels from 200% up

    def test_every_fluid_text_step_is_within_2_5_times_its_minimum(self):
        steps = fluid_text_steps()
        self.assertEqual(len(steps), 2)
        for name, (lo, _, _, hi) in steps.items():
            with self.subTest(token=name, span=round(hi / lo, 2)):
                self.assertLessEqual(hi / lo, 2.5)

    def test_typography_md_quotes_what_tokens_css_gives(self):
        text = " ".join(TYPOGRAPHY.read_text(encoding="utf-8").split())
        steps = fluid_text_steps()
        for name, (lo, _, _, hi) in steps.items():
            with self.subTest(token=name):
                self.assertIn(f"{hi:g} / {lo:g} = {hi / lo:.2f}×", text)

        hero = steps["--text-6xl"]
        widest = hero[3]
        self.assertAlmostEqual(computed(hero, self.WINDOW), widest, delta=0.01)
        viewport = self.WINDOW / 2
        size = computed(hero, viewport)
        self.assertIn(f"grows only {2 * size / widest:.2f}× at 200% zoom", text)
        self.assertIn(f"the CSS viewport is {viewport:g}px, so it computes to {size:.1f}px, "
                      f"{2 * size:.1f} screen pixels against {widest:g}", text)
        first = next(z for z in self.ZOOM_STEPS
                     if z * computed(hero, self.WINDOW / z) >= 2 * widest)
        zoomed = first * computed(hero, self.WINDOW / first)
        self.assertIn(f"first reaches 2× at the browser's {first * 100:g}% step", text)
        self.assertIn(f"{zoomed:g} against {widest:g}, {zoomed / widest:.2f}×", text)


if __name__ == "__main__":
    unittest.main()
