"""Numbers written in comments and prose hold (3.2.0).

Regressions covered:
- SS-A8: "Verified 8.22:1" in the dark theme sat above --fg-muted (neutral-300,
  13.80:1) but was neutral-400's ratio. A claim now names its pair —
  `Verified 4.60:1 (--neutral-500 on --neutral-100)` — so it can be recomputed.
- SS-A15: the fluid spacing clamps declare anchors of 380 and 1440px but their
  intercepts ran low, so they met their bounds near 400 and 1460px.
- SS-A15: tokens.css told readers to regenerate the fluid steps with
  scripts/generate_space_scale.py, which has never shipped.
"""
from __future__ import annotations

import importlib.util
import re
import sys
import unittest

from wds_support import SKILLS

STUDIO = SKILLS / "web-design-studio"
TOKENS = STUDIO / "assets" / "starter" / "styles" / "tokens.css"
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


if __name__ == "__main__":
    unittest.main()
