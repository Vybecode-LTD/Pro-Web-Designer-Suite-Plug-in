#!/usr/bin/env python3
"""cluster_values.py — Phases 2 and 3: cluster the literals, propose the system.

Reads the JSON that `extract_literals.py` emits and answers the only question
that matters in a migration: **how many decisions are actually in here?**

12px, 13px, 14px and 15px are not four decisions. They are one decision made
four times, on four Thursdays, by three people. Clustering finds that decision,
snaps it to the closed scale, and writes down every value that does NOT fit
along with what to do about it — because the values that do not fit are where
the design work is, and pretending they fit is how a migration ships a
regression.

It emits three files into the output directory:

    tokens.css          the contract's exact token names, with the ramps
                        derived from THIS codebase's own colors, and a
                        provenance comment on every token saying which
                        literals it absorbed
    mapping.json        every original literal -> its token, in the form
                        apply_codemod.py consumes
    reconciliation.md   every value that does not map, why, and the
                        recommendation — this is the document you review

WHAT IT DOES NOT DO
-------------------
It never invents a token name outside `references/token-contract.md`, and it
never proposes a scale step that does not exist. When a value has no home, it
says so instead of widening the scale. Law 3 is the mechanism; a script that
quietly adds `--space-7` has disabled it.

USAGE
-----
  python -m scripts.extract_literals ./src --format json -o literals.json
  python -m scripts.cluster_values literals.json -o ./proposal

  # Tighter or looser snapping (px). 3px is the default; 2px is strict.
  python -m scripts.cluster_values literals.json -o ./proposal --spacing-tolerance 2

  # Color clustering sensitivity, as OKLab dE. 0.025 is the default.
  python -m scripts.cluster_values literals.json -o ./proposal --color-tolerance 0.015

  # Pin the accent instead of letting the codebase's most-used chroma win
  python -m scripts.cluster_values literals.json -o ./proposal --accent '#e8440a'

  # Land on a project's own ramps: its tokens.css or contract.json (P24).
  # Without the flag, the token files its .design-suite.json lists.
  python -m scripts.cluster_values literals.json -o ./proposal --tokens brand/contract.json

  # Just the report, nothing written
  python -m scripts.cluster_values literals.json --dry-run

Run it by path from the PROJECT root, so `-o proposal/` lands in the project:
`python <skill>/scripts/cluster_values.py literals.json -o proposal/`. The
`-m scripts.cluster_values` form above is for a project that vendored scripts/.

Exit codes: 0 on success, 2 on bad invocation or unreadable input.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

# A sibling import would otherwise leave __pycache__ inside the installed
# plugin. project_config.py is a copy of the plugin's shared/ master (P24).
sys.dont_write_bytecode = True
try:                                              # python -m scripts.cluster_values
    from .project_config import ConfigError, ProjectTokens, read_tokens, token_sources
except ImportError:                               # python scripts/cluster_values.py, or loaded by path
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from project_config import ConfigError, ProjectTokens, read_tokens, token_sources  # type: ignore[no-redef]

# ===========================================================================
# COLOR MATH
# ===========================================================================
# Copied VERBATIM from web-design-studio/scripts/generate_color_ramp.py.
# Two implementations that disagree by a rounding step produce two ramps that
# disagree by a visible step, and nobody ever finds out which one is right.
# If you change a function here, change it there in the same commit.
# ===========================================================================

L_CURVE: Dict[int, float] = {
    50: 0.970, 100: 0.935, 200: 0.880, 300: 0.805, 400: 0.720, 500: 0.645,
    600: 0.565, 700: 0.470, 800: 0.380, 900: 0.300, 950: 0.210,
}
C_CURVE: Dict[int, float] = {
    50: 0.106, 100: 0.223, 200: 0.415, 300: 0.628, 400: 0.840, 500: 1.000,
    600: 0.936, 700: 0.787, 800: 0.628, 900: 0.479, 950: 0.330,
}
H_DRIFT: Dict[int, float] = {
    50: 4.0, 100: 3.2, 200: 2.4, 300: 1.6, 400: 0.8, 500: 0.0,
    600: 1.0, 700: 2.0, 800: 3.0, 900: 4.0, 950: 5.0,
}
WARM_ANCHOR = 45.0
COOL_ANCHOR = 250.0

NEUTRAL_L: Dict[int, float] = {
    0: 1.000, 50: 0.982, 100: 0.960, 200: 0.922, 300: 0.865, 400: 0.715,
    500: 0.535, 600: 0.475, 700: 0.385, 800: 0.280, 900: 0.195, 950: 0.130,
    1000: 0.080,
}
NEUTRAL_C: Dict[int, float] = {
    0: 0.000, 50: 0.003, 100: 0.004, 200: 0.005, 300: 0.006, 400: 0.008,
    500: 0.009, 600: 0.009, 700: 0.008, 800: 0.007, 900: 0.006, 950: 0.005,
    1000: 0.004,
}


class ColorError(ValueError):
    """Raised for anything we cannot turn into a color."""


def srgb_to_linear(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def linear_to_srgb(c: float) -> float:
    return c * 12.92 if c <= 0.0031308 else 1.055 * (c ** (1 / 2.4)) - 0.055


def linear_srgb_to_oklab(r: float, g: float, b: float) -> Tuple[float, float, float]:
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l_ = math.copysign(abs(l) ** (1 / 3), l)
    m_ = math.copysign(abs(m) ** (1 / 3), m)
    s_ = math.copysign(abs(s) ** (1 / 3), s)
    return (
        0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_,
        1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_,
        0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_,
    )


def oklab_to_linear_srgb(L: float, a: float, b: float) -> Tuple[float, float, float]:
    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b
    l, m, s = l_ ** 3, m_ ** 3, s_ ** 3
    return (
        +4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
        -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
        -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s,
    )


def oklab_to_oklch(L: float, a: float, b: float) -> Tuple[float, float, float]:
    return (L, math.hypot(a, b), math.degrees(math.atan2(b, a)) % 360.0)


def oklch_to_oklab(L: float, C: float, H: float) -> Tuple[float, float, float]:
    rad = math.radians(H)
    return (L, C * math.cos(rad), C * math.sin(rad))


def oklch_to_rgb(L: float, C: float, H: float) -> Tuple[float, float, float]:
    lr, lg, lb = oklab_to_linear_srgb(*oklch_to_oklab(L, C, H))
    return (linear_to_srgb(lr), linear_to_srgb(lg), linear_to_srgb(lb))


def in_srgb_gamut(L: float, C: float, H: float, eps: float = 1e-4) -> bool:
    return all(-eps <= v <= 1.0 + eps for v in oklch_to_rgb(L, C, H))


def gamut_map(L: float, C: float, H: float, iterations: int = 40) -> Tuple[float, float, float]:
    """Reduce chroma by binary search until the color is inside sRGB.

    L and H are preserved exactly — clipping RGB instead shifts both lightness
    and hue, and a ramp whose step 500 silently got lighter no longer matches
    its neighbours.
    """
    if C <= 0:
        return (L, 0.0, H)
    if in_srgb_gamut(L, C, H):
        return (L, C, H)
    lo, hi = 0.0, C
    for _ in range(iterations):
        mid = (lo + hi) / 2.0
        if in_srgb_gamut(L, mid, H):
            lo = mid
        else:
            hi = mid
    return (L, lo, H)


def relative_luminance(r: float, g: float, b: float) -> float:
    rl, gl, bl = srgb_to_linear(r), srgb_to_linear(g), srgb_to_linear(b)
    return 0.2126 * rl + 0.7152 * gl + 0.0722 * bl


def clamp_rgb(rgb: Tuple[float, float, float]) -> Tuple[float, float, float]:
    return tuple(max(0.0, min(1.0, v)) for v in rgb)  # type: ignore[return-value]


def contrast_ratio_rgb(fg: Tuple[float, float, float],
                       bg: Tuple[float, float, float]) -> float:
    l1, l2 = relative_luminance(*fg), relative_luminance(*bg)
    if l2 > l1:
        l1, l2 = l2, l1
    return (l1 + 0.05) / (l2 + 0.05)


def _interp(table: Dict[int, float], step: int) -> float:
    keys = sorted(table)
    if step in table:
        return table[step]
    if step <= keys[0]:
        return table[keys[0]]
    if step >= keys[-1]:
        return table[keys[-1]]
    for lo, hi in zip(keys, keys[1:]):
        if lo <= step <= hi:
            t = (step - lo) / (hi - lo)
            return table[lo] + t * (table[hi] - table[lo])
    return table[keys[-1]]


def rotate_toward(hue: float, anchor: float, amount: float) -> float:
    delta = ((anchor - hue + 180.0) % 360.0) - 180.0
    if abs(delta) <= amount:
        return anchor % 360.0
    return (hue + math.copysign(amount, delta)) % 360.0


_HEX_RE = re.compile(r"^#?([0-9a-fA-F]{3}|[0-9a-fA-F]{4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")
_RGB_RE = re.compile(
    r"^rgba?\(\s*([\d.]+%?)\s*[, ]\s*([\d.]+%?)\s*[, ]\s*([\d.]+%?)\s*"
    r"(?:[,/]\s*([\d.]+%?)\s*)?\)$", re.IGNORECASE)
_HSL_RE = re.compile(
    r"^hsla?\(\s*(-?[\d.]+)(?:deg)?\s*[, ]\s*([\d.]+)%\s*[, ]\s*([\d.]+)%\s*"
    r"(?:[,/]\s*([\d.]+%?)\s*)?\)$", re.IGNORECASE)

NAMED_HEX = {
    "black": "#000000", "white": "#ffffff", "red": "#ff0000", "blue": "#0000ff",
    "green": "#008000", "gray": "#808080", "grey": "#808080", "silver": "#c0c0c0",
    "yellow": "#ffff00", "orange": "#ffa500", "purple": "#800080",
    "pink": "#ffc0cb", "brown": "#a52a2a", "cyan": "#00ffff", "navy": "#000080",
    "teal": "#008080", "olive": "#808000", "maroon": "#800000", "lime": "#00ff00",
    "aqua": "#00ffff", "fuchsia": "#ff00ff", "magenta": "#ff00ff",
    "gold": "#ffd700", "indigo": "#4b0082", "violet": "#ee82ee",
    "crimson": "#dc143c", "coral": "#ff7f50", "salmon": "#fa8072",
    "khaki": "#f0e68c", "plum": "#dda0dd", "tan": "#d2b48c", "beige": "#f5f5dc",
    "ivory": "#fffff0", "lavender": "#e6e6fa", "turquoise": "#40e0d0",
    "orchid": "#da70d6", "whitesmoke": "#f5f5f5", "gainsboro": "#dcdcdc",
    "snow": "#fffafa", "linen": "#faf0e6", "lightgray": "#d3d3d3",
    "lightgrey": "#d3d3d3", "darkgray": "#a9a9a9", "darkgrey": "#a9a9a9",
    "dimgray": "#696969", "dimgrey": "#696969", "slategray": "#708090",
    "slategrey": "#708090",
}


def _pct(v: str, scale: float) -> float:
    return float(v[:-1]) / 100.0 * scale if v.endswith("%") else float(v)


def parse_any_color(raw: str) -> Tuple[Tuple[float, float, float], float]:
    """Parse hex / rgb() / hsl() / a named color into (sRGB 0..1, alpha)."""
    s = raw.strip().lower()
    if s in NAMED_HEX:
        s = NAMED_HEX[s]
    m = _HEX_RE.match(s)
    if m:
        h = m.group(1)
        if len(h) in (3, 4):
            h = "".join(c * 2 for c in h)
        alpha = int(h[6:8], 16) / 255.0 if len(h) == 8 else 1.0
        return ((int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0,
                 int(h[4:6], 16) / 255.0), alpha)
    m = _RGB_RE.match(re.sub(r"\s+", " ", s))
    if m:
        r, g, b = (_pct(m.group(i), 255.0) / 255.0 for i in (1, 2, 3))
        a = _pct(m.group(4), 1.0) if m.group(4) else 1.0
        return ((r, g, b), a)
    m = _HSL_RE.match(re.sub(r"\s+", " ", s))
    if m:
        h_deg = float(m.group(1)) % 360.0 / 360.0
        sat, lig = float(m.group(2)) / 100.0, float(m.group(3)) / 100.0
        a = _pct(m.group(4), 1.0) if m.group(4) else 1.0
        import colorsys
        r, g, b = colorsys.hls_to_rgb(h_deg, lig, sat)
        return ((r, g, b), a)
    raise ColorError(f"cannot parse color {raw!r}")


def rgb_to_oklab(rgb: Tuple[float, float, float]) -> Tuple[float, float, float]:
    r, g, b = rgb
    return linear_srgb_to_oklab(srgb_to_linear(r), srgb_to_linear(g),
                                srgb_to_linear(b))


def delta_e_ok(a: Tuple[float, float, float], b: Tuple[float, float, float]) -> float:
    """Euclidean distance in OKLab. This is the whole metric.

    Calibration, measured on sRGB 8-bit values:
        one code value at mid-gray   0.0035
        #333333 vs #343434           0.0039   same decision, typed twice
        #e6e6e6 vs #ececec           0.0181   same rule color
        #333333 vs #3a3a3a           0.0274   same ink, two Thursdays
        #2f6df6 vs #2558c8           0.0876   brand vs brand-hover: TWO decisions
    """
    return math.dist(a, b)


def rgb_to_hex(rgb: Tuple[float, float, float]) -> str:
    return "#{:02x}{:02x}{:02x}".format(
        *(max(0, min(255, int(round(v * 255)))) for v in rgb))


def _trim(v: str) -> str:
    return v.rstrip("0").rstrip(".") if "." in v else v


def format_oklch(L: float, C: float, H: float) -> str:
    lightness = _trim(f"{L * 100:.1f}")
    if C < 5e-4:
        return f"oklch({lightness}% 0 0)"
    hue = _trim(f"{H:.1f}") or "0"
    return f"oklch({lightness}% {C:.3f} {'0' if hue == '-0' else hue})"


# ===========================================================================
# THE CLOSED SCALES — these mirror references/token-contract.md exactly.
# Adding an entry here adds a step to the design system. Do not.
# ===========================================================================

SPACE_STEPS: List[Tuple[float, str]] = [
    (0, "--space-0"), (1, "--space-px"), (2, "--space-0-5"), (4, "--space-1"),
    (8, "--space-2"), (12, "--space-3"), (16, "--space-4"), (20, "--space-5"),
    (24, "--space-6"), (32, "--space-8"), (40, "--space-10"), (48, "--space-12"),
    (64, "--space-16"), (80, "--space-20"), (96, "--space-24"),
    (128, "--space-32"), (160, "--space-40"), (192, "--space-48"),
]
SPACE_PX = [px for px, _ in SPACE_STEPS]
SPACE_NAME = dict(SPACE_STEPS)

# Tailwind theme key for each Tier-2 role, matching
# assets/configs/tailwind.config.ts. The key follows the ROLE, not the pixel
# count: `px-[18px]` becomes `px-inline-md`, not `px-grouped`, because inline
# padding and a sibling gap are different decisions that happen to measure the
# same.
TOKEN_TW_KEY = {
    "--space-0": "0", "--space-px": "px",
    "--gap-fused": "fused", "--gap-tight": "tight", "--gap-related": "related",
    "--gap-grouped": "grouped", "--gap-separate": "separate",
    "--gap-distinct": "distinct",
    "--pad-inline-xs": "inline-xs", "--pad-inline-sm": "inline-sm",
    "--pad-inline-md": "inline-md", "--pad-block-xs": "block-xs",
    "--pad-block-sm": "block-sm", "--pad-block-md": "block-md",
    "--pad-card": "card", "--pad-card-lg": "card-lg", "--pad-well": "well",
}

TYPE_STEPS: List[Tuple[float, str, str]] = [
    (11, "--text-2xs", ""), (12, "--text-xs", "--type-label"),
    (14, "--text-sm", "--type-ui"), (16, "--text-base", "--type-body"),
    (18, "--text-lg", "--type-lead"), (22, "--text-xl", "--type-h4"),
    (28, "--text-2xl", "--type-h3"), (35, "--text-3xl", "--type-h2"),
    (44, "--text-4xl", "--type-h1"),
]
TYPE_PX = [px for px, _, _ in TYPE_STEPS]

RADIUS_STEPS: List[Tuple[float, str]] = [
    (0, "--radius-none"), (2, "--radius-xs"), (4, "--radius-sm"),
    (8, "--radius-md"), (12, "--radius-lg"), (16, "--radius-xl"),
    (24, "--radius-2xl"),
]
STROKE_STEPS: List[Tuple[float, str]] = [
    (1, "--stroke-default"), (2, "--stroke-thick"),
]
DUR_STEPS: List[Tuple[float, str]] = [
    (80, "--dur-instant"), (140, "--dur-fast"), (220, "--dur-base"),
    (320, "--dur-slow"), (480, "--dur-slower"),
]
# Duration -> the Tier-2 pair a transition should actually read.
MOTION_ROLE: List[Tuple[float, str]] = [
    (100, "--motion-hover"), (180, "--motion-hover"), (260, "--motion-enter"),
    (400, "--motion-expand"), (10_000, "--motion-expand"),
]
LEADING_STEPS: List[Tuple[float, str]] = [
    (1.0, "--leading-none"), (1.15, "--leading-tight"), (1.3, "--leading-snug"),
    (1.6, "--leading-normal"), (1.75, "--leading-relaxed"),
]
TRACKING_STEPS: List[Tuple[float, str]] = [
    (-0.03, "--tracking-tighter"), (-0.015, "--tracking-tight"),
    (0.0, "--tracking-normal"), (0.02, "--tracking-wide"),
    (0.08, "--tracking-caps"),
]
WIDTH_STEPS: List[Tuple[float, str]] = [
    (448, "--width-form"), (1152, "--width-content"), (1440, "--width-wide"),
]
EASINGS: List[Tuple[str, Tuple[float, float, float, float]]] = [
    ("--ease-out", (0.22, 1.0, 0.36, 1.0)),
    ("--ease-in", (0.64, 0.0, 0.78, 0.0)),
    ("--ease-in-out", (0.65, 0.0, 0.35, 1.0)),
    ("--ease-spring", (0.34, 1.56, 0.64, 1.0)),
]
# The contract's eight rungs start at --z-base (0). A literal 0 is left alone,
# so only the seven rungs above it are ever assigned.
Z_LADDER = ["--z-raised", "--z-sticky", "--z-dropdown", "--z-overlay",
            "--z-modal", "--z-toast", "--z-tooltip"]
ELEVATION_BY_BLUR: List[Tuple[float, str]] = [
    (4, "--elevation-card"), (12, "--elevation-raised"),
    (28, "--elevation-overlay"), (10_000, "--elevation-modal"),
]

# Proximity ladder: px -> Tier-2 role, for space BETWEEN things.
GAP_LADDER = {4: "--gap-fused", 8: "--gap-tight", 12: "--gap-related",
              16: "--gap-grouped", 24: "--gap-separate", 40: "--gap-distinct"}
PAD_INLINE = {8: "--pad-inline-xs", 12: "--pad-inline-sm", 16: "--pad-inline-md",
              24: "--pad-card", 32: "--pad-card-lg"}
PAD_BLOCK = {4: "--pad-block-xs", 8: "--pad-block-sm", 12: "--pad-block-md",
             16: "--pad-well", 24: "--pad-card", 32: "--pad-card-lg"}
PAD_ALL = {16: "--pad-well", 24: "--pad-card", 32: "--pad-card-lg"}

PROP_CLASS_TABLE = {
    "gap": GAP_LADDER, "pad-inline": PAD_INLINE, "pad-block": PAD_BLOCK,
    "pad-all": PAD_ALL,
}

# Which prop class each CSS property maps to. Shorthand slot resolution lives
# in apply_codemod.py, which is the only place that can see the slot count.
GAP_PROPS = {
    "gap", "row-gap", "column-gap", "grid-gap", "grid-row-gap",
    "grid-column-gap", "margin", "margin-top", "margin-right", "margin-bottom",
    "margin-left", "margin-block", "margin-block-start", "margin-block-end",
    "margin-inline", "margin-inline-start", "margin-inline-end",
}
PAD_INLINE_PROPS = {"padding-left", "padding-right", "padding-inline",
                    "padding-inline-start", "padding-inline-end"}
PAD_BLOCK_PROPS = {"padding-top", "padding-bottom", "padding-block",
                   "padding-block-start", "padding-block-end"}
PAD_ALL_PROPS = {"padding"}
RADIUS_PROPS = {"border-radius", "border-top-left-radius",
                "border-top-right-radius", "border-bottom-left-radius",
                "border-bottom-right-radius", "border-start-start-radius",
                "border-start-end-radius", "border-end-start-radius",
                "border-end-end-radius"}
STROKE_PROPS = {"border-width", "border-top-width", "border-right-width",
                "border-bottom-width", "border-left-width", "outline-width",
                "border", "border-top", "border-right", "border-bottom",
                "border-left", "border-block", "border-inline", "outline",
                "column-rule"}
FG_PROPS = {"color", "fill", "caret-color", "text-decoration-color",
            "text-emphasis-color"}
BG_PROPS = {"background", "background-color", "accent-color"}
BORDER_COLOR_PROPS = {"border-color", "border-top-color", "border-right-color",
                      "border-bottom-color", "border-left-color",
                      "border-block-color", "border-inline-color",
                      "outline-color", "column-rule-color", "border",
                      "border-top", "border-right", "border-bottom",
                      "border-left", "outline", "stroke"}


def prop_class_for(prop: str, kind: str) -> str:
    """The coarse class a literal's property belongs to."""
    if kind == "color":
        if prop.startswith("tw:"):
            return TW_COLOR_CLASS.get(prop[3:], "other")
        if prop in FG_PROPS:
            return "fg"
        if prop in BG_PROPS:
            return "bg"
        if prop in BORDER_COLOR_PROPS:
            return "border"
        if prop.startswith("$") or prop.startswith("@") or prop.startswith("--"):
            return "var"
        return "other"
    if kind == "length":
        if prop in GAP_PROPS:
            return "gap"
        if prop in PAD_INLINE_PROPS:
            return "pad-inline"
        if prop in PAD_BLOCK_PROPS:
            return "pad-block"
        if prop in PAD_ALL_PROPS:
            return "pad-all"
        if prop.startswith("tw:"):
            return tw_prop_class(prop[3:])
        if prop in {"width", "height", "max-width", "min-width", "max-height",
                    "min-height", "flex-basis"}:
            return "size"
        if prop in {"top", "right", "bottom", "left", "inset", "inset-block",
                    "inset-inline"}:
            return "inset"
        return "other"
    return kind


TW_COLOR_CLASS = {
    "text": "fg", "fill": "fg", "caret": "fg", "decoration": "fg",
    "placeholder": "fg", "bg": "bg", "from": "bg", "to": "bg", "via": "bg",
    "accent": "bg", "border": "border", "ring": "border", "outline": "border",
    "divide": "border", "stroke": "border", "shadow": "other",
}


def tw_prop_class(prefix: str) -> str:
    if prefix in {"p", "size"}:
        return "pad-all"
    if prefix in {"px", "pl", "pr", "ps", "pe"}:
        return "pad-inline"
    if prefix in {"py", "pt", "pb"}:
        return "pad-block"
    # Before the margin test: max-w/min-w/max-h/min-h start with "m" too.
    if prefix in {"w", "h", "min-w", "max-w", "min-h", "max-h"}:
        return "size"
    if prefix.startswith(("m", "gap", "space")):
        return "gap"
    return "other"


# ===========================================================================
# Snapping
# ===========================================================================

PX_PER_REM = 16.0


def to_px(normalized: str) -> Optional[float]:
    """Normalize a length literal to px. `em` is deliberately excluded.

    `em` is a RATIO to the current font size, so an em value tracks type rather
    than bypassing the scale. Snapping it to a px step would silently break
    that relationship.
    """
    m = re.fullmatch(r"(-?[\d.]+)(px|rem|pt)", normalized, re.IGNORECASE)
    if not m:
        return None
    v, unit = float(m.group(1)), m.group(2).lower()
    if unit == "px":
        return v
    if unit == "rem":
        return v * PX_PER_REM
    return v * 4.0 / 3.0  # pt


@dataclass
class Snap:
    """One value's journey onto the scale."""
    original_px: float
    step_px: float
    token: str
    delta: float
    tie: bool = False
    review: bool = False
    reason: str = ""


def snap_to_scale(px: float, steps: Sequence[float], tolerance: float,
                  weights: Optional[Dict[float, int]] = None,
                  tie_prefers: str = "down") -> Optional[Tuple[float, float, bool]]:
    """Snap `px` to the nearest step. Returns (step, delta, was_a_tie).

    Ties are broken by FREQUENCY first — if 12px appears 40 times and 16px
    twice, a stray 14px belongs with the crowd, because the crowd is the
    decision and the 14 is the typo. Only when the crowd is silent does the
    fallback direction apply.
    """
    if not steps:
        return None
    dists = sorted(((abs(px - s), s) for s in steps), key=lambda t: (t[0], t[1]))
    best_d, best_s = dists[0]
    if best_d > tolerance:
        return None
    ties = [s for d, s in dists if abs(d - best_d) < 1e-9]
    was_tie = len(ties) > 1
    if was_tie:
        if weights:
            ranked = sorted(ties, key=lambda s: (-weights.get(s, 0), s))
            if weights.get(ranked[0], 0) > weights.get(ranked[1], 0):
                best_s = ranked[0]
                return (best_s, best_s - px, True)
        best_s = min(ties) if tie_prefers == "down" else max(ties)
    return (best_s, best_s - px, was_tie)


# ===========================================================================
# Clustering
# ===========================================================================

@dataclass
class ColorCluster:
    members: List[str]                       # normalized literals
    counts: Dict[str, int]
    alpha: float
    centroid_rgb: Tuple[float, float, float] = (0, 0, 0)
    centroid_lab: Tuple[float, float, float] = (0, 0, 0)
    ramp_token: str = ""
    ramp_rgb: Tuple[float, float, float] = (0, 0, 0)
    roles: Dict[str, str] = field(default_factory=dict)   # prop class -> role
    diameter: float = 0.0

    @property
    def total(self) -> int:
        return sum(self.counts.values())

    @property
    def dominant(self) -> str:
        return max(self.counts.items(), key=lambda kv: (kv[1], kv[0]))[0]


CHROMATIC_C = 0.010      # at or above this, a color has a hue worth respecting
ACHROMATIC_C = 0.005     # below this, the hue angle is numerical noise
TINT_C = 0.015           # at or above this, a near-white is a TINT, not a gray
HUE_GUARD_DEG = 30.0


def _merge_allowed(a_lab: Tuple[float, float, float],
                   b_lab: Tuple[float, float, float]) -> Tuple[bool, str]:
    """The two guards that stop single linkage turning a palette into porridge."""
    _La, Ca, Ha = oklab_to_oklch(*a_lab)
    _Lb, Cb, Hb = oklab_to_oklch(*b_lab)
    if Ca >= CHROMATIC_C and Cb >= CHROMATIC_C:
        dh = abs(((Ha - Hb + 180.0) % 360.0) - 180.0)
        if dh > HUE_GUARD_DEG:
            return False, f"hue {dh:.0f}deg apart"
    # A tint is not a gray. #eef2ff and #e6e6e6 are 0.04 apart in dE and are two
    # different decisions: one is an info surface, one is a rule. Near white,
    # OKLab compresses hard enough that dE alone stops telling them apart.
    if (Ca < ACHROMATIC_C) != (Cb < ACHROMATIC_C):
        if max(Ca, Cb) >= TINT_C:
            return False, "a tint is not a gray"
    return True, ""


def cluster_colors(entries: Dict[str, int], tolerance: float,
                   diameter_factor: float = 1.5) -> List[ColorCluster]:
    """Single-linkage clustering in OKLab, with a diameter cap.

    Single linkage is right for this job: near-duplicates form chains
    (`#333` -> `#343434` -> `#3a3a3a`) and chains are exactly what we want to
    collapse. It is also single linkage's famous failure mode, so the chain is
    capped: a merge is refused when it would make the cluster's widest pair
    exceed `diameter_factor x tolerance`. Without the cap, one codebase's worth
    of grays merges into a single "color" that is white at one end.

    Pure white and pure black never absorb a neighbour. They are structural
    anchors — the surface and the ink — and every design system re-points them
    independently. Merging `#fff` into `#fafaf9` costs you the canvas/surface
    distinction that makes cards read as cards.
    """
    parsed: Dict[str, Tuple[Tuple[float, float, float], float]] = {}
    for raw in entries:
        try:
            parsed[raw] = parse_any_color(raw)
        except ColorError:
            continue

    by_alpha: Dict[float, List[str]] = defaultdict(list)
    for raw, (_rgb, alpha) in parsed.items():
        by_alpha[round(alpha, 2)].append(raw)

    clusters: List[ColorCluster] = []
    for alpha, members in sorted(by_alpha.items(), reverse=True):
        labs = {m: rgb_to_oklab(parsed[m][0]) for m in members}
        anchors = {m for m in members
                   if parsed[m][0] in ((1.0, 1.0, 1.0), (0.0, 0.0, 0.0))}

        groups: List[List[str]] = [[m] for m in sorted(
            members, key=lambda m: (-entries[m], m))]

        merged = True
        while merged:
            merged = False
            for i in range(len(groups)):
                for j in range(i + 1, len(groups)):
                    gi, gj = groups[i], groups[j]
                    if (anchors & set(gi)) or (anchors & set(gj)):
                        continue
                    link = min(delta_e_ok(labs[a], labs[b])
                               for a in gi for b in gj)
                    if link > tolerance:
                        continue
                    if any(not _merge_allowed(labs[a], labs[b])[0]
                           for a in gi for b in gj):
                        continue
                    union = gi + gj
                    diameter = max(delta_e_ok(labs[a], labs[b])
                                   for a in union for b in union)
                    if diameter > tolerance * diameter_factor:
                        continue
                    groups[i] = union
                    groups.pop(j)
                    merged = True
                    break
                if merged:
                    break

        for g in groups:
            counts = {m: entries[m] for m in g}
            total = sum(counts.values()) or 1
            cen = tuple(
                sum(parsed[m][0][k] * counts[m] for m in g) / total
                for k in range(3)
            )
            diam = max((delta_e_ok(labs[a], labs[b]) for a in g for b in g),
                       default=0.0)
            clusters.append(ColorCluster(
                members=sorted(g, key=lambda m: (-counts[m], m)),
                counts=counts, alpha=alpha,
                centroid_rgb=cen, centroid_lab=rgb_to_oklab(cen),  # type: ignore[arg-type]
                diameter=diam,
            ))
    clusters.sort(key=lambda c: -c.total)
    return clusters


# ===========================================================================
# Ramp construction — derived from THIS codebase
# ===========================================================================

@dataclass
class Ramp:
    name: str
    steps: Dict[int, Tuple[float, float, float]]   # step -> OKLCH

    def css(self, comments: Optional[Dict[int, str]] = None) -> str:
        comments = comments or {}
        lines = []
        width = max(len(f"--{self.name}-{s}:") for s in self.steps)
        for step in sorted(self.steps):
            L, C, H = self.steps[step]
            decl = f"--{self.name}-{step}:"
            note = comments.get(step, "")
            body = f"    {decl:<{width}} {format_oklch(L, C, H)};"
            if note:
                body = f"{body:<52}/* {note} */"
            lines.append(body)
        return "\n".join(lines)

    def rgb(self, step: int) -> Tuple[float, float, float]:
        return clamp_rgb(oklch_to_rgb(*self.steps[step]))


def build_accent_ramp(seed_rgb: Tuple[float, float, float], name: str) -> Ramp:
    """The studio's tuned L / chroma-falloff / hue-drift curves, seeded here."""
    L0, C0, H0 = oklab_to_oklch(*rgb_to_oklab(seed_rgb))
    steps: Dict[int, Tuple[float, float, float]] = {}
    for step in sorted(L_CURVE):
        L = _interp(L_CURVE, step)
        C = C0 * _interp(C_CURVE, step)
        anchor = COOL_ANCHOR if step < 500 else WARM_ANCHOR
        H = rotate_toward(H0, anchor, _interp(H_DRIFT, step))
        steps[step] = gamut_map(L, C, H)
    return Ramp(name, steps)


def build_neutral_ramp(hue: float, name: str = "neutral") -> Ramp:
    steps = {step: gamut_map(_interp(NEUTRAL_L, step), _interp(NEUTRAL_C, step), hue)
             for step in sorted(NEUTRAL_L)}
    return Ramp(name, steps)


# The status ramps are fixed by the contract: green means success everywhere,
# and a codebase's idiosyncratic red is not a reason to move the hue.
STATUS_RAMPS = {
    "success": {100: (0.940, 0.050, 152.0), 500: (0.620, 0.150, 152.0),
                700: (0.450, 0.120, 152.0)},
    "warning": {100: (0.955, 0.055, 85.0), 500: (0.750, 0.155, 85.0),
                700: (0.520, 0.125, 85.0)},
    "danger": {100: (0.945, 0.038, 25.0), 400: (0.640, 0.190, 25.0),
               500: (0.580, 0.205, 25.0), 700: (0.450, 0.170, 25.0)},
    "info": {100: (0.945, 0.035, 250.0), 500: (0.580, 0.160, 250.0),
             700: (0.450, 0.140, 250.0)},
}

STATUS_HUE = {"success": 152.0, "warning": 85.0, "danger": 25.0, "info": 250.0}

# The ramps the contract names; the role tables below are keyed by them.
CONTRACT_RAMPS = ("neutral", "accent", *STATUS_RAMPS)
OKLCH_TEXT = re.compile(r"oklch\(\s*([\d.]+)(%?)\s+([\d.]+)\s+([\d.]+)(?:deg)?\s*\)", re.I)


def project_ramps(tokens: ProjectTokens, prop: Proposal) -> Dict[str, Dict[int, Tuple[float, float, float]]]:
    """The project's own steps of the contract's ramps (P24: LC-C1), as OKLCH.
    A ramp the contract does not name has no roles to land on, so it is
    named in the notes and left out."""
    out: Dict[str, Dict[int, Tuple[float, float, float]]] = {}
    for name, steps in tokens.ramps.items():
        if name not in CONTRACT_RAMPS:
            prop.notes.append(f"The project's tokens declare a `{name}` ramp, which the contract "
                              f"has no roles for; the migration does not land on it.")
            continue
        for step, value in steps.items():
            m = OKLCH_TEXT.fullmatch(value.strip())
            if m:
                lch = (float(m.group(1)) / (100.0 if m.group(2) else 1.0), float(m.group(3)), float(m.group(4)))
            else:
                try:
                    rgb, alpha = parse_any_color(value)
                except ColorError:
                    continue                 # a colour space this script does not read
                if alpha < 0.999:
                    continue
                lch = oklab_to_oklch(*rgb_to_oklab(rgb))
            out.setdefault(name, {})[int(step)] = lch
    return out


def nearest_ramp_step(lab: Tuple[float, float, float],
                      ramps: Dict[str, Ramp]) -> Tuple[str, int, float]:
    """Nearest (ramp, step) to a color, by OKLab dE.

    A tint may not land on a neutral step. Near white, OKLab compresses hard
    enough that `#fff8e1` measures marginally closer to `--neutral-50` than to
    `--warning-100`, which would quietly turn a notice background into the page
    canvas. Chroma is the design intent here and dE is not allowed to overrule
    it — the same rule the clustering guard applies.
    """
    _L, C, _H = oklab_to_oklch(*lab)
    tinted = C >= TINT_C
    best = ("", 0, math.inf)
    for name, ramp in ramps.items():
        for step, (_sl, sc, _sh) in ramp.steps.items():
            if tinted and sc < CHROMATIC_C:
                continue
            d = delta_e_ok(lab, rgb_to_oklab(ramp.rgb(step)))
            if d < best[2]:
                best = (name, step, d)
    if not best[0]:                      # every step filtered out: fall back
        for name, ramp in ramps.items():
            for step in ramp.steps:
                d = delta_e_ok(lab, rgb_to_oklab(ramp.rgb(step)))
                if d < best[2]:
                    best = (name, step, d)
    return best


# Ramp step -> Tier-2 role, per property class. This table IS the color half of
# the proposal: it is where "a gray" becomes "the muted foreground".
FG_ROLE_BY_STEP = {
    ("neutral", 0): "--fg-on-accent", ("neutral", 50): "--fg-on-inverse",
    ("neutral", 100): "--fg-on-inverse", ("neutral", 300): "--fg-disabled",
    ("neutral", 400): "--fg-disabled", ("neutral", 500): "--fg-subtle",
    ("neutral", 600): "--fg-muted", ("neutral", 700): "--fg-muted",
    ("neutral", 800): "--fg-default", ("neutral", 900): "--fg-default",
    ("neutral", 950): "--fg-strong", ("neutral", 1000): "--fg-strong",
}
BG_ROLE_BY_STEP = {
    ("neutral", 0): "--bg-surface", ("neutral", 50): "--bg-canvas",
    ("neutral", 100): "--bg-sunken", ("neutral", 200): "--bg-sunken",
    ("neutral", 300): "--bg-disabled", ("neutral", 400): "--bg-disabled",
    ("neutral", 900): "--bg-inverse", ("neutral", 950): "--bg-inverse",
    ("neutral", 1000): "--bg-inverse",
}
BORDER_ROLE_BY_STEP = {
    ("neutral", 100): "--border-subtle", ("neutral", 200): "--border-subtle",
    ("neutral", 300): "--border-default", ("neutral", 400): "--border-strong",
    ("neutral", 500): "--border-strong",
}


def role_for(ramp_name: str, step: int, klass: str) -> Tuple[str, str]:
    """(role token, note). An empty role means 'a human decides this one'."""
    if ramp_name == "neutral":
        table = {"fg": FG_ROLE_BY_STEP, "bg": BG_ROLE_BY_STEP,
                 "border": BORDER_ROLE_BY_STEP}.get(klass)
        if table:
            role = table.get((ramp_name, step), "")
            if role:
                return role, ""
        return "", f"neutral-{step} has no Tier-2 {klass} role in the contract"
    if ramp_name == "accent":
        # The step matters. --fg-accent IS accent-700 and --bg-accent IS
        # accent-600; pointing a pale accent-100 badge fill at --bg-accent
        # turns a tint into a saturated button, which is the single most
        # visible way an automated color migration goes wrong.
        if klass == "fg":
            if step >= 600:
                return "--fg-accent", ""
            return "", (f"accent-{step} is too light for text — --fg-accent is "
                        f"accent-700, and a lighter accent will not clear 4.5:1")
        if klass == "bg":
            if step <= 100:
                return "--bg-selected", ""
            if 400 <= step <= 600:
                return "--bg-accent", ""
            if step == 700:
                return "--bg-accent-hover", ""
            return "", (f"accent-{step} sits between the tint role "
                        f"(--bg-selected) and the fill role (--bg-accent)")
        if klass == "border":
            if step <= 200:
                return "", (f"accent-{step} is too light to read as a border; "
                            f"--border-accent is accent-500")
            return ("--border-accent" if step <= 500 else "--border-focus"), ""
    if ramp_name in ("success", "warning", "danger"):
        if klass == "fg" and step >= 600:
            return f"--fg-{ramp_name}", ""
        if klass == "bg" and step >= 400:
            return f"--bg-{ramp_name}", ""
        if step <= 300:
            return "", (f"a SUBTLE {ramp_name} tint — --bg-{ramp_name} is the "
                        f"saturated 500 fill, not this")
        return "", f"{ramp_name}-{step} has no Tier-2 {klass} role"
    if ramp_name == "info":
        return "", "the contract has no --fg-info / --bg-info role; add one or use accent"
    return "", f"{ramp_name}-{step} has no Tier-2 {klass} role"


# ===========================================================================
# Shadows
# ===========================================================================

SHADOW_NUM_RE = re.compile(r"(-?\d*\.?\d+)(?:px|rem|em)?(?![\w.%])", re.IGNORECASE)
SHADOW_COLOR_RE = re.compile(
    r"\b(rgba?|hsla?|hwb|lab|lch|oklab|oklch|color)\([^()]*\)|#[0-9a-fA-F]{3,8}",
    re.IGNORECASE)


def split_top_level_commas(value: str) -> List[str]:
    """Split on commas that are not inside a function. `rgba(0, 0, 0, .1)` is
    one token, not four, and a splitter that does not know that turns a
    two-layer shadow into five broken ones."""
    out, depth, start = [], 0, 0
    for i, ch in enumerate(value):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        elif ch == "," and depth == 0:
            out.append(value[start:i])
            start = i + 1
    out.append(value[start:])
    return [p for p in (s.strip() for s in out) if p]


def shadow_signature(value: str) -> Tuple[int, float, float]:
    """(layer count, max blur px, max |y-offset| px) — the structural fingerprint.

    Structure, not alpha: two shadows with the same geometry are the same
    elevation decision even when their alphas differ by 0.02, which they always
    do, because somebody eyeballed one of them at 3pm.

    The numbers are read positionally — x, y, blur, spread — which is the only
    way to read them, because `0 12px 28px` leads with a UNITLESS zero and a
    regex that insists on `px` silently reads the blur as the y-offset and
    files a modal shadow as a card.
    """
    layers = split_top_level_commas(value)
    blurs, offsets = [0.0], [0.0]
    for layer in layers:
        body = SHADOW_COLOR_RE.sub(" ", layer)
        nums = [float(m.group(1)) for m in SHADOW_NUM_RE.finditer(body)]
        if len(nums) >= 2:
            offsets.append(abs(nums[1]))
        if len(nums) >= 3:
            blurs.append(abs(nums[2]))
    return (max(1, len(layers)), max(blurs), max(offsets))


def spread_ring(value: str) -> Optional[str]:
    """'outer' or 'inset' when every layer is a pure ring — no offset, no blur,
    only spread (`0 0 0 3px …`) — else None. A ring is a focus indicator or a
    border drawn with a shadow; it is never an elevation, and filing it with
    the card shadows (same zero blur) rewrote focus rings to --elevation-card."""
    kinds = set()
    for layer in split_top_level_commas(value):
        body = SHADOW_COLOR_RE.sub(" ", layer)
        nums = [float(m.group(1)) for m in SHADOW_NUM_RE.finditer(body)]
        if len(nums) < 4 or any(nums[:3]) or not nums[3]:
            return None
        kinds.add("inset" if re.search(r"\binset\b", body, re.I) else "outer")
    return kinds.pop() if len(kinds) == 1 else None


def elevation_for_blur(blur: float) -> str:
    for limit, token in ELEVATION_BY_BLUR:
        if blur <= limit:
            return token
    return "--elevation-modal"


# ===========================================================================
# The proposal
# ===========================================================================

@dataclass
class Rule:
    """One mechanical replacement, in the form apply_codemod.py consumes."""
    id: str
    kind: str
    scope: str                      # value | declaration | tailwind
    match: List[str]
    replacement: str
    token: str
    prop_classes: List[str] = field(default_factory=list)
    props: List[str] = field(default_factory=list)
    occurrences: int = 0
    delta_px: float = 0.0
    confidence: str = "exact"       # exact | snapped | review
    note: str = ""


@dataclass
class Unmapped:
    kind: str
    value: str
    occurrences: int
    where: List[str]
    reason: str
    recommendation: str


@dataclass
class Proposal:
    rules: List[Rule] = field(default_factory=list)
    unmapped: List[Unmapped] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    accent_seed: str = ""
    neutral_hue: float = 75.0
    provenance: Dict[str, List[str]] = field(default_factory=lambda: defaultdict(list))
    contrast: List[Tuple[str, str, float, float, str]] = field(default_factory=list)


def literal_index(payload: dict) -> Dict[str, List[dict]]:
    idx: Dict[str, List[dict]] = defaultdict(list)
    for lit in payload.get("literals", []):
        idx[lit["kind"]].append(lit)
    return idx


UNMAPPED_KIND = {"length": "spacing", "font-size": "type", "border-width": "stroke"}


def route_inline_styles(idx: Dict[str, List[dict]], prop: Proposal) -> None:
    """JSX `style={{…}}` values are Law 4 hand work (Phase 4f): apply_codemod
    never rewrites them, because the declaration has to move into a stylesheet
    under a class name. Left in the pools they were counted as mechanically
    replaceable, so they get their own unmapped rows instead."""
    for kind in list(idx):
        inline = [l for l in idx[kind] if l.get("context") == "inline-style"]
        if not inline:
            continue
        idx[kind] = [l for l in idx[kind] if l.get("context") != "inline-style"]
        by_value: Dict[str, List[dict]] = defaultdict(list)
        for l in inline:
            by_value[l["normalized"]].append(l)
        for value, items in sorted(by_value.items()):
            prop.unmapped.append(Unmapped(
                kind=UNMAPPED_KIND.get(kind, kind), value=value, occurrences=len(items),
                where=where_of(items),
                reason="set in a JSX inline style (Law 4) — the codemod does not rewrite these",
                recommendation=("Phase 4f: move the declaration into the component's "
                                "stylesheet under a class name, then re-run "
                                "extract_literals so it is mapped with the rest."),
            ))


def where_of(lits: Sequence[dict], limit: int = 3) -> List[str]:
    seen: List[str] = []
    for l in lits:
        loc = f"{l['file']}:{l['line']}"
        if loc not in seen:
            seen.append(loc)
        if len(seen) >= limit:
            break
    return seen


# ---------------------------------------------------------------------------

def cluster_spacing(lits: Sequence[dict], tol: float, prop: Proposal,
                    kind_label: str = "length") -> None:
    """Snap every length onto the closed 4px scale, per property class."""
    by_class: Dict[str, Dict[float, List[dict]]] = defaultdict(lambda: defaultdict(list))
    for l in lits:
        px = to_px(l["normalized"])
        if px is None or px == 0:
            continue
        klass = prop_class_for(l["prop"], "length")
        by_class[klass][abs(px)].append(l)

    # Frequency weights: how much mass already sits ON each step, across the
    # whole codebase. A tie goes to the crowd.
    weights: Dict[float, int] = defaultdict(int)
    for klass, groups in by_class.items():
        for px, items in groups.items():
            if px in SPACE_PX:
                weights[px] += len(items)

    rid = 0
    for klass in sorted(by_class):
        table = PROP_CLASS_TABLE.get(klass)
        for px in sorted(by_class[klass]):
            items = by_class[klass][px]
            # Strip the sign: the rule is about the MAGNITUDE. A `-13px`
            # listed as its own match would be replaced by a bare
            # `var(--gap-related)`, silently flipping a negative margin
            # positive. apply_codemod re-applies the sign as
            # `calc(var(--token) * -1)`.
            raws = sorted({l["normalized"].lstrip("-") for l in items})
            tw_items = [l for l in items if l["context"] == "tailwind-arbitrary"]
            css_items = [l for l in items if l["context"] != "tailwind-arbitrary"]
            snapped = snap_to_scale(px, SPACE_PX, tol, weights, tie_prefers="down")
            if snapped is None:
                nearest = min(SPACE_PX, key=lambda s: abs(s - px))
                prop.unmapped.append(Unmapped(
                    kind="spacing", value=f"{px:g}px", occurrences=len(items),
                    where=where_of(items),
                    reason=f"{abs(px - nearest):g}px from the nearest step "
                           f"({nearest:g}px) — outside the {tol:g}px tolerance",
                    recommendation=_spacing_recommendation(px, klass),
                ))
                continue
            step, delta, was_tie = snapped
            rid += 1
            token = ""
            note = ""
            if table and step in table:
                token = table[step]
            elif klass in ("size",):
                got = snap_to_scale(px, [w for w, _ in WIDTH_STEPS], 24.0)
                if got:
                    token = dict(WIDTH_STEPS)[got[0]]
                    step, delta = got[0], got[1]
            if not token:
                prop.unmapped.append(Unmapped(
                    kind="spacing", value=f"{px:g}px", occurrences=len(items),
                    where=where_of(items),
                    reason=f"snaps to {step:g}px, which has no Tier-2 role for "
                           f"`{klass}` in the contract",
                    recommendation=_no_role_recommendation(step, klass),
                ))
                continue
            confidence = "exact" if abs(delta) < 1e-9 else "snapped"
            if abs(delta) > 2.0:
                confidence = "review"
                note = (f"moves {abs(delta):g}px — big enough to see. "
                        f"Screenshot this one.")
            elif was_tie:
                note = (f"{px:g}px was equidistant between two steps; "
                        f"resolved to {step:g}px by frequency.")
            if css_items:
                prop.rules.append(Rule(
                    id=f"sp-{rid:03d}-{klass}", kind="spacing", scope="value",
                    match=raws, replacement=f"var({token})", token=token,
                    prop_classes=[klass],
                    props=sorted({l["prop"] for l in css_items
                                  if not l["prop"].startswith("tw:")}),
                    occurrences=len(css_items), delta_px=round(delta, 3),
                    confidence=confidence, note=note,
                ))
                prop.provenance[token].append(
                    f"{px:g}px x{len(css_items)} ({klass})")
            if tw_items:
                key = TOKEN_TW_KEY.get(token)
                if key:
                    for tw in sorted({l["raw"] for l in tw_items}):
                        prefix = tw.split("-[")[0]
                        prop.rules.append(Rule(
                            id=f"tw-{rid:03d}-{prefix}", kind="spacing",
                            scope="tailwind", match=[tw],
                            replacement=f"{prefix}-{key}", token=token,
                            prop_classes=[klass], props=[],
                            occurrences=sum(1 for l in tw_items if l["raw"] == tw),
                            delta_px=round(delta, 3), confidence=confidence,
                            note=note or "Tailwind theme key, see "
                                         "assets/configs/tailwind.config.ts",
                        ))
                else:
                    prop.unmapped.append(Unmapped(
                        kind="tailwind", value=", ".join(sorted({l["raw"] for l in tw_items})),
                        occurrences=len(tw_items), where=where_of(tw_items),
                        reason=f"snaps to {step:g}px, which the Tailwind theme "
                               f"exposes under no spacing key",
                        recommendation="Add a theme key in tailwind.config.ts "
                                       "pointing at the Tier-2 role, or move the "
                                       "value to a rung the ladder already has.",
                    ))


def _spacing_recommendation(px: float, klass: str) -> str:
    lo = max((s for s in SPACE_PX if s <= px), default=0)
    hi = min((s for s in SPACE_PX if s >= px), default=SPACE_PX[-1])
    if px >= 48 and klass in ("pad-block", "pad-all", "gap"):
        return (f"Section-scale space. Use the fluid page rhythm — "
                f"--space-section / --space-subsection / --space-block — rather "
                f"than freezing {px:g}px, which is cramped at 1440px and a "
                f"scroll tax at 390px.")
    return (f"Decide between {lo:g}px ({SPACE_NAME.get(lo, '?')}) and "
            f"{hi:g}px ({SPACE_NAME.get(hi, '?')}) by RELATIONSHIP, not by "
            f"which is closer. If neither reads right, the layout is wrong, "
            f"not the scale.")


def _no_role_recommendation(step: float, klass: str) -> str:
    name = SPACE_NAME.get(step, "?")
    if klass == "gap":
        rungs = ", ".join(f"{px:g}px {tok}" for px, tok in sorted(GAP_LADDER.items()))
        return (f"{step:g}px is on the scale but off the proximity ladder "
                f"({rungs}). Pick the rung whose RELATIONSHIP matches, or add a "
                f"Tier-2 role in tokens.css bound to {name}.")
    if klass == "inset":
        return (f"Positioning offset, not proximity. Read {name} directly, or "
                f"better, ask whether the element needs absolute positioning.")
    if klass == "size":
        return (f"A width/height, not spacing. Use --width-content / "
                f"--width-form / --measure-prose, or a relational unit.")
    return (f"{step:g}px is on the scale as {name} but has no Tier-2 role for "
            f"`{klass}`. Add one in tokens.css — Tier-2 roles are cheap; "
            f"components reading {name} directly is Law 6.")


# ---------------------------------------------------------------------------

def cluster_type(lits: Sequence[dict], tol: float, prop: Proposal) -> None:
    """Snap font sizes onto the type scale and rewrite them to --type-* roles.

    The replacement is a whole-DECLARATION rewrite (`font-size: 15px` becomes
    `font: var(--type-body)`) because a --type-* role carries size, leading,
    weight and family as one shorthand. Half a role is how a 35px heading ends
    up at body leading, which is the most common typographic bug on the web.
    """
    groups: Dict[float, List[dict]] = defaultdict(list)
    for l in lits:
        px = to_px(l["normalized"])
        if px:
            groups[px].append(l)

    role_by_px = {px: role for px, _prim, role in TYPE_STEPS}
    prim_by_px = {px: prim for px, prim, _role in TYPE_STEPS}

    for i, px in enumerate(sorted(groups), start=1):
        items = groups[px]
        raws = sorted({l["normalized"] for l in items})
        # Ties snap UP: text never shrinks to settle a tie. 15px becomes 16px
        # body, not 14px UI text, however common 14px is: frequency settles a
        # spacing tie (the crowd is the decision), never a type one.
        got = snap_to_scale(px, TYPE_PX, tol, None, tie_prefers="up")
        if got is None:
            nearest = min(TYPE_PX, key=lambda s: abs(s - px))
            prop.unmapped.append(Unmapped(
                kind="type", value=f"{px:g}px", occurrences=len(items),
                where=where_of(items),
                reason=f"{abs(px - nearest):g}px from the nearest type step "
                       f"({nearest:g}px)",
                recommendation=f"Either this is a display size that belongs on "
                               f"--text-5xl/--text-6xl (both fluid clamps), or "
                               f"it is a heading that should be {nearest:g}px. "
                               f"A hierarchy with two sizes 3px apart reads as "
                               f"a mistake, not as a level.",
            ))
            continue
        step, delta, was_tie = got
        role = role_by_px.get(step, "")
        if not role:
            prop.unmapped.append(Unmapped(
                kind="type", value=f"{px:g}px", occurrences=len(items),
                where=where_of(items),
                reason=f"snaps to {step:g}px ({prim_by_px.get(step, '?')}), "
                       f"which has no --type-* role",
                recommendation=f"{prim_by_px.get(step)} exists as a primitive for "
                               f"dense table meta and legal text. If this text is "
                               f"neither, move it to --type-label (12px). "
                               f"Reading the primitive from a component is Law 6.",
            ))
            continue
        confidence = "exact" if abs(delta) < 1e-9 else "snapped"
        note = ""
        if abs(delta) > 2.0:
            confidence = "review"
            note = f"moves {abs(delta):g}px — check the heading hierarchy still reads."
        elif was_tie:
            note = (f"{px:g}px was equidistant; snapped {'UP' if delta > 0 else 'DOWN'} "
                    f"to {step:g}px." + (" Text does not shrink to settle a tie."
                                         if delta > 0 else ""))
        css_items = [l for l in items if l["context"] != "tailwind-arbitrary"]
        tw_items = [l for l in items if l["context"] == "tailwind-arbitrary"]
        if css_items:
            prop.rules.append(Rule(
                id=f"ty-{i:03d}", kind="type", scope="declaration",
                match=raws, replacement=f"font: var({role})", token=role,
                prop_classes=["font-size"], props=["font-size"],
                occurrences=len(css_items), delta_px=round(delta, 3),
                confidence=confidence, note=note,
            ))
            prop.provenance[role].append(f"{px:g}px x{len(css_items)}")
        if tw_items:
            tw_key = role.replace("--type-", "")
            for tw in sorted({l["raw"] for l in tw_items}):
                prefix = tw.split("-[")[0]
                prop.rules.append(Rule(
                    id=f"tw-ty-{i:03d}", kind="type", scope="tailwind",
                    match=[tw], replacement=f"{prefix}-{tw_key}", token=role,
                    prop_classes=["font-size"], props=[],
                    occurrences=sum(1 for l in tw_items if l["raw"] == tw),
                    delta_px=round(delta, 3), confidence=confidence, note=note,
                ))


# ---------------------------------------------------------------------------

def cluster_simple(lits: Sequence[dict], steps: Sequence[Tuple[float, str]],
                   tol: float, kind: str, prop: Proposal,
                   props: Sequence[str], recommendation: str,
                   unit: str = "px", tw_key: Optional[Dict[float, str]] = None) -> None:
    """Radius, stroke, duration: one scale, one property class, no roles."""
    step_px = [s for s, _ in steps]
    name = dict(steps)
    groups: Dict[float, List[dict]] = defaultdict(list)
    for l in lits:
        v = to_px(l["normalized"]) if unit == "px" else _to_ms(l["normalized"])
        if v is None:
            continue
        groups[abs(v)].append(l)
    weights = {v: len(items) for v, items in groups.items() if v in step_px}
    for i, v in enumerate(sorted(groups), start=1):
        items = groups[v]
        raws = sorted({l["normalized"].lstrip("-") for l in items})
        got = snap_to_scale(v, step_px, tol, weights, tie_prefers="down")
        if got is None:
            nearest = min(step_px, key=lambda s: abs(s - v))
            prop.unmapped.append(Unmapped(
                kind=kind, value=f"{v:g}{unit}", occurrences=len(items),
                where=where_of(items),
                reason=f"{abs(v - nearest):g}{unit} from the nearest step "
                       f"({nearest:g}{unit})",
                recommendation=recommendation,
            ))
            continue
        step, delta, _tie = got
        token = name[step]
        confidence = "exact" if abs(delta) < 1e-9 else "snapped"
        css_items = [l for l in items if l["context"] != "tailwind-arbitrary"]
        tw_items = [l for l in items if l["context"] == "tailwind-arbitrary"]
        if css_items:
            prop.rules.append(Rule(
                id=f"{kind[:2]}-{i:03d}", kind=kind, scope="value",
                match=raws, replacement=f"var({token})", token=token,
                prop_classes=[kind], props=list(props),
                occurrences=len(css_items), delta_px=round(delta, 3),
                confidence=confidence,
            ))
            prop.provenance[token].append(f"{v:g}{unit} x{len(css_items)}")
        if tw_items and tw_key and step in tw_key:
            for tw in sorted({l["raw"] for l in tw_items}):
                prefix = tw.split("-[")[0]
                prop.rules.append(Rule(
                    id=f"tw-{kind[:2]}-{i:03d}", kind=kind, scope="tailwind",
                    match=[tw], replacement=f"{prefix}-{tw_key[step]}",
                    token=token, prop_classes=[kind], props=[],
                    occurrences=sum(1 for l in tw_items if l["raw"] == tw),
                    delta_px=round(delta, 3), confidence=confidence,
                ))


def _to_ms(normalized: str) -> Optional[float]:
    m = re.fullmatch(r"([\d.]+)ms", normalized)
    return float(m.group(1)) if m else None


def cluster_motion(lits: Sequence[dict], tol: float, prop: Proposal) -> None:
    """Durations become --dur-*; whole transitions become a --motion-* pair.

    A bare duration token is Tier 1. The contract wants components to read a
    --motion-* pair so duration and easing travel together — split them and
    they drift apart within a quarter. So when the declaration is a complete
    `transition: <props> <time> [easing]`, rewrite the declaration; otherwise
    fall back to the primitive and say so.
    """
    groups: Dict[float, List[dict]] = defaultdict(list)
    for l in lits:
        ms = _to_ms(l["normalized"])
        if ms:
            groups[ms].append(l)
    dur_px = [s for s, _ in DUR_STEPS]
    weights = {v: len(items) for v, items in groups.items() if v in dur_px}
    for i, ms in enumerate(sorted(groups), start=1):
        items = groups[ms]
        raws = sorted({l["normalized"] for l in items} |
                      {l["raw"].strip() for l in items})
        got = snap_to_scale(ms, dur_px, tol, weights, tie_prefers="down")
        if got is None:
            prop.unmapped.append(Unmapped(
                kind="duration", value=f"{ms:g}ms", occurrences=len(items),
                where=where_of(items),
                reason=f"more than {tol:g}ms from every step "
                       f"({', '.join(f'{d:g}' for d in dur_px)})",
                recommendation="Duration scales with distance travelled and "
                               "element size. Pick the step by what MOVES: "
                               "--dur-fast for hover, --dur-base for a "
                               "dropdown, --dur-slow for a drawer.",
            ))
            continue
        step, delta, _ = got
        token = dict(DUR_STEPS)[step]
        role = next(r for limit, r in MOTION_ROLE if ms <= limit)
        css_items = [l for l in items if l["context"] != "tailwind-arbitrary"]
        tw_items = [l for l in items if l["context"] == "tailwind-arbitrary"]
        if css_items:
            # Two rules, deliberately. A whole `transition: opacity 250ms ease`
            # collapses to the Tier-2 PAIR, because a duration and an easing
            # that live in separate tokens drift apart inside a quarter. A bare
            # `transition-duration` has no easing to pair with, so it falls
            # back to the Tier-1 step.
            prop.rules.append(Rule(
                id=f"mo-{i:03d}-pair", kind="duration", scope="motion",
                match=raws, replacement=f"var({role})", token=role,
                prop_classes=["motion"], props=["transition", "animation"],
                occurrences=len(css_items), delta_px=round(delta, 3),
                confidence="review",
                note=f"{ms:g}ms -> {role}. Confirm the ROLE, not the number: "
                     f"enter and exit are deliberately asymmetric (things "
                     f"arrive slower than they leave).",
            ))
            prop.rules.append(Rule(
                id=f"mo-{i:03d}", kind="duration", scope="value",
                match=raws, replacement=f"var({token})", token=token,
                prop_classes=["duration"],
                props=["transition-duration", "animation-duration",
                       "transition-delay", "animation-delay"],
                occurrences=len(css_items), delta_px=round(delta, 3),
                confidence="exact" if abs(delta) < 1e-9 else "snapped",
                note=f"Tier 1, for a standalone duration property. A whole "
                     f"`transition` shorthand takes var({role}) instead.",
            ))
            prop.provenance[token].append(f"{ms:g}ms x{len(css_items)}")
            prop.provenance[role].append(f"{ms:g}ms x{len(css_items)}")
        if tw_items:
            prop.unmapped.append(Unmapped(
                kind="tailwind", value=", ".join(sorted({l["raw"] for l in tw_items})),
                occurrences=len(tw_items), where=where_of(tw_items),
                reason="arbitrary Tailwind duration",
                recommendation=f"Use the theme's transitionDuration key bound to "
                               f"{token}, or drop the utility and let the "
                               f"component stylesheet own the transition.",
            ))


def cluster_easing(lits: Sequence[dict], prop: Proposal) -> None:
    for i, value in enumerate(sorted({l["normalized"] for l in lits}), start=1):
        items = [l for l in lits if l["normalized"] == value]
        nums = re.findall(r"-?[\d.]+", value)
        if len(nums) != 4:
            prop.unmapped.append(Unmapped(
                kind="easing", value=value, occurrences=len(items),
                where=where_of(items), reason="not a 4-point cubic-bezier",
                recommendation="Use --ease-out (arriving), --ease-in (leaving) "
                               "or --ease-in-out (moving within view).",
            ))
            continue
        pt = tuple(float(n) for n in nums)
        token, dist = min(
            ((name, math.dist(pt, ctrl)) for name, ctrl in EASINGS),
            key=lambda t: t[1])
        prop.rules.append(Rule(
            id=f"ea-{i:03d}", kind="easing", scope="value",
            match=sorted({l["raw"] for l in items} | {value}),
            replacement=f"var({token})", token=token,
            prop_classes=["easing"],
            props=["transition", "transition-timing-function", "animation",
                   "animation-timing-function"],
            occurrences=len(items), confidence="snapped" if dist > 0.05 else "exact",
            note=f"control-point distance {dist:.2f} from {token}",
        ))
        prop.provenance[token].append(f"{value} x{len(items)}")


def cluster_shadows(lits: Sequence[dict], prop: Proposal) -> None:
    sigs: Dict[Tuple[int, float, float], List[dict]] = defaultdict(list)
    rings: Dict[str, List[dict]] = defaultdict(list)
    borders: Dict[str, List[dict]] = defaultdict(list)
    for l in lits:
        ring = spread_ring(l["normalized"])
        if ring == "outer" or (ring and ":focus" in (l.get("selector") or "")):
            rings[l["normalized"]].append(l)
        elif ring:
            borders[l["normalized"]].append(l)
        else:
            sigs[shadow_signature(l["normalized"])].append(l)

    # Focus rings map to the contract's ring role — at `review`, because the
    # contract ring is two-ringed and must be paired with a transparent
    # outline, which is a hand edit the codemod cannot make.
    for j, (value, items) in enumerate(sorted(rings.items()), start=1):
        raws = sorted({value} | {re.sub(r"\s+", " ", l["raw"].strip()) for l in items})
        prop.rules.append(Rule(
            id=f"ring-{j:03d}", kind="shadow", scope="value",
            match=raws, replacement="var(--elevation-focus)", token="--elevation-focus",
            prop_classes=["shadow"], props=["box-shadow"],
            occurrences=len(items), confidence="review",
            note="a spread-only ring is a focus indicator, not an elevation. "
                 "--elevation-focus is the contract's ring; also add "
                 "`outline: var(--stroke-focus) solid transparent` beside it so the "
                 "ring survives forced-colors mode, which discards box-shadow.",
        ))
        prop.provenance["--elevation-focus"].append(f"{value} x{len(items)}")
    for value, items in sorted(borders.items()):
        prop.unmapped.append(Unmapped(
            kind="shadow", value=value, occurrences=len(items), where=where_of(items),
            reason="a spread-only inset ring is a border drawn with a shadow, "
                   "not an elevation",
            recommendation="use a real border (`border: var(--stroke-default) solid "
                           "var(--border-default)`), or bind the ring's colour to a "
                           "--border-* role by hand.",
        ))

    for i, (sig, items) in enumerate(
            sorted(sigs.items(), key=lambda kv: (-len(kv[1]), kv[0])), start=1):
        n_layers, blur, offset = sig
        token = elevation_for_blur(blur)
        raws = sorted({l["normalized"] for l in items} |
                      {re.sub(r"\s+", " ", l["raw"].strip()) for l in items})
        prop.rules.append(Rule(
            id=f"sh-{i:03d}", kind="shadow", scope="value",
            match=raws, replacement=f"var({token})", token=token,
            prop_classes=["shadow"], props=["box-shadow"],
            occurrences=len(items),
            confidence="review" if n_layers > 1 else "snapped",
            note=f"structural signature: {n_layers} layer(s), "
                 f"{blur:g}px blur, {offset:g}px offset. The contract's "
                 f"elevations are two-layer (contact + ambient); a "
                 f"single-layer original will read slightly flatter.",
        ))
        prop.provenance[token].append(
            f"{len(items)} shadow(s) @ {blur:g}px blur")


def cluster_z(lits: Sequence[dict], prop: Proposal) -> None:
    """Z-index is ORDER, not magnitude. Rank the values, then assign rungs.

    9999 does not mean "very high". It means "higher than the last person's
    999". Sorting and re-assigning preserves the only thing the numbers
    encoded, and it is the one kind where the script must not guess silently —
    every mapping here is marked for review.
    """
    values = sorted({int(l["normalized"]) for l in lits
                     if re.fullmatch(r"-?\d+", l["normalized"])})
    if not values:
        return
    if len(values) > len(Z_LADDER):
        prop.notes.append(
            f"{len(values)} distinct z-indexes for the {len(Z_LADDER)} rungs above "
            f"`--z-base`. Several values are collapsed onto one rung; read the "
            f"stacking contexts before applying.")
    # Magnitude picks the starting rung — 9999 means "above everything", and
    # that intent is worth keeping — then rank order is enforced so no two
    # values swap places.
    bands = [(49, 0), (149, 1), (249, 2), (349, 3), (449, 4), (549, 5)]
    assigned: List[int] = []
    for v in values:
        idx_rung = next((b for limit, b in bands if v <= limit), len(Z_LADDER) - 1)
        assigned.append(idx_rung)
    for i in range(len(assigned) - 1, 0, -1):
        if assigned[i - 1] >= assigned[i]:
            assigned[i - 1] = max(0, assigned[i] - 1)
    for i, v in enumerate(values):
        rung = Z_LADDER[assigned[i]]
        items = [l for l in lits if l["normalized"] == str(v)]
        prop.rules.append(Rule(
            id=f"z-{i + 1:03d}", kind="z-index", scope="value",
            match=[str(v)], replacement=f"var({rung})", token=rung,
            prop_classes=["z-index"], props=["z-index"],
            occurrences=len(items), confidence="review",
            note=f"rank {i + 1} of {len(values)}. Confirm against the real "
                 f"stacking order — a z-index only ever meant 'above the other "
                 f"one', and rank is the only part of it worth keeping.",
        ))
        prop.provenance[rung].append(f"z-index {v} x{len(items)}")


def cluster_leading(lits: Sequence[dict], prop: Proposal) -> None:
    for value in sorted({l["normalized"] for l in lits}):
        items = [l for l in lits if l["normalized"] == value]
        v = float(value)
        token, delta = min(((name, abs(v - step)) for step, name in LEADING_STEPS),
                           key=lambda t: t[1])
        prop.unmapped.append(Unmapped(
            kind="line-height", value=value, occurrences=len(items),
            where=where_of(items),
            reason="a --type-* role already carries leading in its font shorthand",
            recommendation=f"DELETE this declaration once the sibling font-size "
                           f"becomes `font: var(--type-*)`. If it must survive "
                           f"on its own, {token} is the nearest step "
                           f"({delta:+.2f}). Two sources for leading is how a "
                           f"heading ends up at body leading.",
        ))


def cluster_tracking(lits: Sequence[dict], prop: Proposal) -> None:
    for i, value in enumerate(sorted({l["normalized"] for l in lits}), start=1):
        items = [l for l in lits if l["normalized"] == value]
        m = re.fullmatch(r"(-?[\d.]+)em", value)
        if not m:
            continue
        v = float(m.group(1))
        token, delta = min(((name, abs(v - step)) for step, name in TRACKING_STEPS),
                           key=lambda t: t[1])
        if delta > 0.012:
            prop.unmapped.append(Unmapped(
                kind="tracking", value=value, occurrences=len(items),
                where=where_of(items),
                reason=f"{delta:.3f}em from the nearest tracking step",
                recommendation="Tracking is optical: tighter as type grows, "
                               "looser as it shrinks. Use --tracking-tighter "
                               "(44px+), --tracking-tight (22-35px), "
                               "--tracking-wide (12-14px UI).",
            ))
            continue
        prop.rules.append(Rule(
            id=f"tr-{i:03d}", kind="tracking", scope="value",
            match=[value], replacement=f"var({token})", token=token,
            prop_classes=["tracking"], props=["letter-spacing"],
            occurrences=len(items),
            confidence="exact" if delta < 1e-9 else "snapped",
        ))
        prop.provenance[token].append(f"{value} x{len(items)}")


# ---------------------------------------------------------------------------

def held_colour(holder: str) -> Tuple[str, str]:
    """Why a colour held outside a role does not map, and what to do, by what
    holds it: a preprocessor variable, a custom property, a plain property, or
    JavaScript."""
    if holder and holder.startswith(("$", "@")):
        return (f"held in the preprocessor variable `{holder}`",
                f"Delete it, and use the role at each call site "
                f"(`var(--fg-default)`, or whichever role that site means). "
                f"Re-pointed, `{holder}: var(--fg-default)` is a tier that means "
                f"nothing (framework-migrations.md). Keep a variable only for a "
                f"value the browser cannot hold, such as a breakpoint inside "
                f"`@media`.")
    if holder and holder.startswith("--"):
        return (f"held in the custom property `{holder}`",
                f"Point it at the role instead: `{holder}: var(--fg-default)` "
                f"(pick the right role). A component's own property defaulting "
                f"to a role is a Tier-3 socket; holding a literal, it is a tier "
                f"missing.")
    if holder:
        return (f"in `{holder}`, a property with no colour role",
                f"Replace the colour inside `{holder}` with the role it means at "
                f"that call site (`var(--fg-default)`, `var(--border-default)`, "
                f"…); keep the declaration.")
    return ("a color constant in JavaScript",
            "A color in JS is a color dark mode cannot re-point. Move the "
            "decision into CSS and read it back with "
            "getComputedStyle().getPropertyValue('--fg-muted') if canvas or "
            "chart code genuinely needs the value.")


def cluster_color_phase(lits: Sequence[dict], tol: float, prop: Proposal,
                        accent_override: Optional[str],
                        project: Optional[Dict[str, Dict[int, Tuple[float, float, float]]]] = None,
                        ) -> Tuple[Ramp, Ramp, Dict[str, Ramp]]:
    freq: Dict[str, int] = defaultdict(int)
    for l in lits:
        freq[l["normalized"]] += 1

    clusters = cluster_colors(freq, tol)

    # ---- choose the accent seed -------------------------------------------
    chromatic: List[Tuple[int, ColorCluster]] = []
    neutral_hues: List[Tuple[int, float]] = []
    for c in clusters:
        L, C, H = oklab_to_oklch(*c.centroid_lab)
        if C >= 0.04:
            chromatic.append((c.total, c))
        elif 0.001 <= C <= 0.012:
            # Above 0.012 it is a tint with a hue of its own, not a neutral
            # whose temperature we are trying to read. The contract's neutral
            # ramp peaks at C 0.009.
            neutral_hues.append((c.total * C, H))
    if accent_override:
        seed_rgb, _a = parse_any_color(accent_override)
        prop.accent_seed = accent_override
    elif project and project.get("accent"):
        # The project's steps replace the built ones below; seeding from its
        # own step keeps any it does not declare on its hue.
        anchor = min(project["accent"], key=lambda step: abs(step - 500))
        seed_rgb = clamp_rgb(oklch_to_rgb(*project["accent"][anchor]))
        prop.accent_seed = rgb_to_hex(seed_rgb)
        prop.notes.append(f"Accent seeded from the project's --accent-{anchor} ({prop.accent_seed}).")
    elif chromatic:
        # Most-used chromatic color that is not obviously a status color.
        def status_distance(c: ColorCluster) -> float:
            _L, _C, H = oklab_to_oklch(*c.centroid_lab)
            return min(abs(((H - sh + 180) % 360) - 180) for sh in STATUS_HUE.values())
        ranked = sorted(chromatic, key=lambda t: (-t[0], -status_distance(t[1])))
        best = ranked[0][1]
        seed_rgb = best.centroid_rgb
        prop.accent_seed = rgb_to_hex(seed_rgb)
        prop.notes.append(
            f"Accent seeded from {prop.accent_seed} — the codebase's most-used "
            f"chromatic color ({best.total} occurrences, originally "
            f"{', '.join(best.members[:4])}).")
    else:
        seed_rgb, _a = parse_any_color("#2f6df6")
        prop.accent_seed = "#2f6df6"
        prop.notes.append(
            "No chromatic color found in the codebase, so the accent falls back "
            "to the studio default. Ask the client for the brand hex before "
            "shipping this ramp.")

    # Hue is weighted by count x chroma, because a hue angle read off a color
    # with C=0.001 is numerical noise and would otherwise outvote a real one.
    # Below the evidence floor the house default wins: a codebase whose grays
    # are #333 and #666 has no neutral temperature to preserve.
    evidence = sum(w for w, _ in neutral_hues)
    if neutral_hues and evidence >= 0.05:
        sin = sum(w * math.sin(math.radians(h)) for w, h in neutral_hues) / evidence
        cos = sum(w * math.cos(math.radians(h)) for w, h in neutral_hues) / evidence
        prop.neutral_hue = round(math.degrees(math.atan2(sin, cos)) % 360.0, 1)
        prop.notes.append(
            f"Neutral hue {prop.neutral_hue:g}deg, the chroma-weighted mean of the "
            f"codebase's own grays. Pure #808080 neutrals read as cheap on "
            f"screens; the existing warmth was worth keeping.")
    else:
        prop.neutral_hue = 75.0
        prop.notes.append(
            "The codebase's grays are all but achromatic, so the neutral ramp "
            "keeps the house warm-graphite hue (75deg). There was no neutral "
            "temperature to preserve.")

    accent = build_accent_ramp(seed_rgb, "accent")
    neutral = build_neutral_ramp(prop.neutral_hue)
    status = {name: Ramp(name, dict(steps)) for name, steps in STATUS_RAMPS.items()}
    ramps: Dict[str, Ramp] = {"neutral": neutral, "accent": accent, **status}
    # The project's own steps replace the built ones, step by step: the
    # literals land on its ramps, and tokens.css writes its values. --accent
    # beats the project's accent, as a flag beats the config.
    taken = []
    for name, steps in (project or {}).items():
        if name == "accent" and accent_override:
            continue
        ramps[name].steps.update(steps)
        taken.append(f"{name} ({len(steps)} of {len(ramps[name].steps)} steps)")
    if taken:
        prop.notes.append(f"Ramps from the project's tokens: {', '.join(taken)}. A step they do not "
                          f"declare is built as it would be without them.")

    canvas_rgb = neutral.rgb(50)

    for idx, c in enumerate(clusters, start=1):
        rname, step, dist = nearest_ramp_step(c.centroid_lab, ramps)
        c.ramp_token = f"--{rname}-{step}"
        c.ramp_rgb = ramps[rname].rgb(step)
        members = [l for l in lits if l["normalized"] in c.counts]
        by_class: Dict[str, List[dict]] = defaultdict(list)
        for l in members:
            by_class[prop_class_for(l["prop"], "color")].append(l)

        if c.alpha < 0.99:
            prop.unmapped.append(Unmapped(
                kind="color", value=", ".join(c.members), occurrences=c.total,
                where=where_of(members),
                reason=f"translucent (alpha {c.alpha:g})",
                recommendation="Translucent fills are interaction overlays, not "
                               "palette entries: --bg-hover and --bg-active "
                               "already compose over any surface. A translucent "
                               "SHADOW color belongs to an --elevation-* role.",
            ))
            continue

        for klass, items in sorted(by_class.items()):
            if klass in ("other", "var"):
                # One entry per kind of holder: a `$` variable and a custom
                # property in one cluster get different advice.
                kinds: Dict[str, list] = {}
                for item in items:
                    holder = item["prop"] or ""
                    kinds.setdefault(holder[:1] if holder[:1] in ("$", "@") else
                                     holder[:2] if holder.startswith("--") else
                                     holder or "js", []).append(item)
                for group in kinds.values():
                    reason, rec = held_colour(group[0]["prop"])
                    prop.unmapped.append(Unmapped(
                        kind="color", value=", ".join(c.members),
                        occurrences=len(group), where=where_of(group),
                        reason=reason, recommendation=rec,
                    ))
                continue
            role, why = role_for(rname, step, klass)
            if not role:
                prop.unmapped.append(Unmapped(
                    kind="color", value=", ".join(c.members), occurrences=len(items),
                    where=where_of(items),
                    reason=why or f"nearest ramp step {c.ramp_token} has no "
                                  f"Tier-2 {klass} role",
                    recommendation=f"Either move the value to a step that has a "
                                   f"role, or add the role to tokens.css. Do not "
                                   f"let a component read {c.ramp_token}: that is "
                                   f"Law 6, and it is what makes dark mode a "
                                   f"grep job later.",
                ))
                continue
            c.roles[klass] = role
            confidence = "exact" if dist < tol else "review"
            note = ""
            if dist >= tol:
                note = (f"nearest ramp step is dE {dist:.3f} away — the original "
                        f"{c.dominant} does not sit on the generated ramp. "
                        f"Eyeball it.")
            prop.rules.append(Rule(
                id=f"co-{idx:03d}-{klass}", kind="color", scope="value",
                match=sorted(set(c.members)),
                replacement=f"var({role})", token=role,
                prop_classes=[klass],
                props=sorted({l["prop"] for l in items
                              if not l["prop"].startswith("tw:")}),
                occurrences=len(items), delta_px=round(dist, 3),    # a colour's is ΔE
                confidence=confidence, note=note,
            ))
            prop.provenance[role].append(
                f"{', '.join(c.members)} x{len(items)} ({klass})")

            tw_items = [l for l in items if l["context"] == "tailwind-arbitrary"]
            tw_key = TW_COLOR_KEY.get(role)
            if tw_items and tw_key:
                for tw in sorted({l["raw"] for l in tw_items}):
                    prefix = tw.split("-[")[0]
                    prop.rules.append(Rule(
                        id=f"tw-co-{idx:03d}-{prefix}", kind="color",
                        scope="tailwind", match=[tw],
                        replacement=f"{prefix}-{tw_key}", token=role,
                        prop_classes=[klass], props=[],
                        occurrences=sum(1 for l in tw_items if l["raw"] == tw),
                        confidence=confidence, note=note,
                    ))

            if klass == "fg":
                # An ink is measured against the surface it actually lands on.
                # Scoring --fg-on-accent against the canvas manufactures a
                # failure for white-on-blue, which is the one pairing that was
                # never in question.
                against = CONTRAST_PARTNER.get(role, "--bg-canvas")
                bg_rgb = clamp_rgb(resolve_role(against, ramps))
                before = contrast_ratio_rgb(c.centroid_rgb, bg_rgb)
                after = contrast_ratio_rgb(clamp_rgb(resolve_role(role, ramps)),
                                           bg_rgb)
                verdict = "PASS" if after >= 4.5 else (
                    "LARGE-TEXT ONLY" if after >= 3.0 else "FAIL")
                prop.contrast.append(
                    (c.dominant, f"{role} on {against}", before, after, verdict))

    return neutral, accent, status


# Which surface each foreground role is actually read on.
CONTRAST_PARTNER = {
    "--fg-on-accent": "--bg-accent", "--fg-on-inverse": "--bg-inverse",
    "--fg-default": "--bg-canvas", "--fg-strong": "--bg-canvas",
    "--fg-muted": "--bg-canvas", "--fg-subtle": "--bg-sunken",
    "--fg-disabled": "--bg-canvas", "--fg-accent": "--bg-canvas",
    "--fg-link": "--bg-canvas", "--fg-success": "--bg-canvas",
    "--fg-warning": "--bg-canvas", "--fg-danger": "--bg-canvas",
    "--fg-on-success": "--bg-success", "--fg-on-warning": "--bg-warning",
    "--fg-on-danger": "--bg-danger",
}

TW_COLOR_KEY = {
    "--fg-default": "default", "--fg-strong": "strong", "--fg-muted": "muted",
    "--fg-subtle": "subtle", "--fg-disabled": "disabled-fg",
    "--fg-on-accent": "on-accent", "--fg-on-inverse": "on-inverse",
    "--fg-accent": "accent-fg", "--fg-link": "link",
    "--bg-canvas": "canvas", "--bg-surface": "surface", "--bg-sunken": "sunken",
    "--bg-inverse": "inverse", "--bg-accent": "accent",
    "--bg-accent-hover": "accent-hover", "--bg-danger": "danger",
    "--bg-success": "success", "--bg-warning": "warning",
    "--bg-disabled": "disabled",
    "--border-subtle": "line-subtle", "--border-default": "line",
    "--border-strong": "line-strong", "--border-accent": "line-accent",
    "--border-focus": "focus",
    "--fg-danger": "danger-fg", "--fg-success": "success-fg",
    "--fg-warning": "warning-fg",
    "--fg-on-success": "on-success", "--fg-on-warning": "on-warning",
    "--fg-on-danger": "on-danger", "--border-invalid": "line-invalid",
}

# Where each Tier-2 color role points in the light theme. Mirrors tokens.css.
ROLE_SOURCE = {
    "--fg-default": ("neutral", 900), "--fg-strong": ("neutral", 950),
    "--fg-muted": ("neutral", 600), "--fg-subtle": ("neutral", 500),
    "--fg-disabled": ("neutral", 400), "--fg-on-accent": ("neutral", 0),
    "--fg-on-inverse": ("neutral", 50), "--fg-accent": ("accent", 700),
    "--fg-link": ("accent", 700),
    "--bg-canvas": ("neutral", 50), "--bg-surface": ("neutral", 0),
    "--bg-raised": ("neutral", 0), "--bg-sunken": ("neutral", 100),
    "--bg-inverse": ("neutral", 900), "--bg-disabled": ("neutral", 100),
    "--bg-accent": ("accent", 600), "--bg-accent-hover": ("accent", 700),
    "--border-subtle": ("neutral", 200), "--border-default": ("neutral", 300),
    "--border-strong": ("neutral", 500), "--border-accent": ("accent", 500),
    "--border-focus": ("accent", 600),
    "--bg-success": ("success", 500), "--bg-warning": ("warning", 500),
    "--bg-danger": ("danger", 500), "--fg-success": ("success", 700),
    "--fg-warning": ("warning", 700), "--fg-danger": ("danger", 700),
    "--fg-on-success": ("neutral", 1000), "--fg-on-warning": ("neutral", 1000),
    "--fg-on-danger": ("neutral", 0), "--border-invalid": ("danger", 500),
}


def resolve_role(role: str, ramps: Dict[str, Ramp]) -> Tuple[float, float, float]:
    ramp_name, step = ROLE_SOURCE.get(role, ("neutral", 900))
    ramp = ramps.get(ramp_name)
    if ramp is None or step not in ramp.steps:
        return (0.0, 0.0, 0.0)
    return ramp.rgb(step)


# ===========================================================================
# tokens.css
# ===========================================================================

def render_tokens_css(prop: Proposal, neutral: Ramp, accent: Ramp,
                      status: Dict[str, Ramp], source: str) -> str:
    def prov(token: str) -> str:
        entries = prop.provenance.get(token, [])
        return "; ".join(entries[:3]) + ("; …" if len(entries) > 3 else "")

    def line(decl: str, value: str, pad: int = 22) -> str:
        note = prov(decl.rstrip(":"))
        body = f"    {decl:<{pad}} {value}"
        return f"{body:<58}/* was: {note} */" if note else body

    neutral_comments = {}
    accent_comments = {}
    for step in neutral.steps:
        hits = prop.provenance.get(f"--neutral-{step}")
        if hits:
            neutral_comments[step] = "; ".join(hits[:2])
    for step in accent.steps:
        hits = prop.provenance.get(f"--accent-{step}")
        if hits:
            accent_comments[step] = "; ".join(hits[:2])

    spacing_lines = []
    for px, name in SPACE_STEPS:
        value = "0" if px == 0 else (f"{px}px" if px == 1 else f"{px / 16:g}rem")
        note = prov(name)
        comment = f"{px:g}px" + (f"  <- {note}" if note else "")
        spacing_lines.append(
            f"    {name + ':':<14} {value + ';':<13} /* {comment} */")

    role_lines = []
    for name, base, comment in [
        ("--gap-fused", "--space-1", "icon + its label"),
        ("--gap-tight", "--space-2", "label + its input"),
        ("--gap-related", "--space-3", "items in one group"),
        ("--gap-grouped", "--space-4", "sibling cards, rows"),
        ("--gap-separate", "--space-6", "distinct groups"),
        ("--gap-distinct", "--space-10", "unrelated blocks"),
    ]:
        note = prov(name)
        role_lines.append(
            f"    {name + ':':<18} calc(var({base}) * var(--density));"
            f"  /* {comment}{('  <- ' + note) if note else ''} */")

    inset_lines = []
    for name, base in [
        ("--pad-inline-xs", "--space-2"), ("--pad-inline-sm", "--space-3"),
        ("--pad-inline-md", "--space-4"), ("--pad-block-xs", "--space-1"),
        ("--pad-block-sm", "--space-2"), ("--pad-block-md", "--space-3"),
        ("--pad-card", "--space-6"), ("--pad-card-lg", "--space-8"),
        ("--pad-well", "--space-4"),
    ]:
        note = prov(name)
        inset_lines.append(
            f"    {name + ':':<18} calc(var({base}) * var(--density));"
            f"{('  /* <- ' + note + ' */') if note else ''}")

    type_lines = []
    for px, prim, role in TYPE_STEPS:
        note = prov(prim)
        type_lines.append(
            f"    {prim + ':':<14} {px / 16:g}rem;"
            f"{' ' * max(1, 10 - len(f'{px / 16:g}rem'))}"
            f"/* {px:g}px{('  <- ' + note) if note else ''} */")

    type_role_lines = []
    for px, prim, role in TYPE_STEPS:
        if not role:
            continue
        note = prov(role)
        weight = {"--type-h1": "--weight-bold", "--type-h2": "--weight-semibold",
                  "--type-h3": "--weight-semibold", "--type-h4": "--weight-semibold",
                  "--type-ui": "--weight-medium", "--type-label": "--weight-medium",
                  }.get(role, "--weight-regular")
        leading = {"--type-h1": "--leading-tight", "--type-h2": "--leading-tight",
                   "--type-h3": "--leading-snug", "--type-h4": "--leading-snug",
                   "--type-ui": "--leading-snug", "--type-label": "--leading-snug",
                   }.get(role, "--leading-normal")
        type_role_lines.append(
            f"    {role + ':':<16} var({weight}) var({prim})/var({leading}) "
            f"var(--font-sans);{('  /* <- ' + note + ' */') if note else ''}")

    contrast_block = []
    for original, role, before, after, verdict in prop.contrast:
        contrast_block.append(
            f"       {original:<9} -> {role:<16} {before:>5.2f}:1 -> "
            f"{after:>5.2f}:1  {verdict}")

    return f"""/* =========================================================================
   TOKENS — proposed, derived from {source}
   =========================================================================

   GENERATED by scripts/cluster_values.py. Read it, argue with it, edit it,
   commit it. After the first human edit this file is hand-maintained; do not
   regenerate over the top of decisions somebody made on purpose.

   Every token below carries a `was:` comment naming the literals it absorbed.
   That comment is the audit trail for the codemod and the answer to "why is
   this 16 and not 18" three months from now. Keep it until the migration
   closes, then delete the comments, not the tokens.

   Accent seeded from {prop.accent_seed} (this codebase's most-used chromatic
   color). Neutral ramp at hue {prop.neutral_hue:g}deg.
   Ramps use the studio's tuned L / chroma-falloff / hue-drift curves, so the
   steps are perceptually even — regenerate either with
   `python -m scripts.generate_color_ramp '{prop.accent_seed}' --name accent`.

   MEASURED CONTRAST for the text roles this codebase actually needs:
{chr(10).join(contrast_block) if contrast_block else "       (no foreground colors found)"}

   THREE TIERS. Flow is one-way: PRIMITIVE -> SEMANTIC -> COMPONENT -> rule.
   Components read Tier 2 only. A component reading --space-6 has skipped a
   tier, and the day "more air in cards" lands you will be grepping for 6s.
   ========================================================================= */

@layer tokens {{

  :root {{

    /* ---------------------------------------------------------------------
       1. SPACING — TIER 1. 4px base, and the scale is CLOSED.
       There is no --space-7, --space-9, --space-11, --space-14. That is the
       point. If a gap "needs" 28px, the layout is wrong, not the scale.
       --------------------------------------------------------------------- */

{chr(10).join(spacing_lines)}

    --space-fluid-sm:  clamp(1rem,    0.811rem + 0.755vw,  1.5rem);   /* 16 -> 24  */
    --space-fluid-md:  clamp(1.5rem,  0.943rem + 2.264vw,  3rem);     /* 24 -> 48  */
    --space-fluid-lg:  clamp(2.5rem,  1.368rem + 4.528vw,  5.5rem);   /* 40 -> 88  */
    --space-fluid-xl:  clamp(4rem,    2.113rem + 7.547vw,  9rem);     /* 64 -> 144 */

    --density: 1;
  }}

  /* ---------------------------------------------------------------------
     2. SPACING — TIER 2 (roles). Components read THESE.
     Named for the RELATIONSHIP they express, not the number they hold.
     Declared on every element that turns the density dial: a custom
     property resolves var() where it is declared, so roles declared on
     :root alone ignored data-density on a section.
     --------------------------------------------------------------------- */

  :root, [data-density], .region-compact {{
{chr(10).join(role_lines)}

{chr(10).join(inset_lines)}
  }}

  :root {{

    --space-section:    var(--space-fluid-xl);
    --space-subsection: var(--space-fluid-lg);
    --space-block:      var(--space-fluid-md);
    --gutter-page:      var(--space-fluid-sm);

    --measure-prose:    68ch;
    --measure-narrow:   48ch;
    --width-content:    72rem;
    --width-wide:       90rem;
    --width-form:       28rem;

    /* ---------------------------------------------------------------------
       3. TYPOGRAPHY — TIER 1
       --------------------------------------------------------------------- */

    --font-sans: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto,
                 "Helvetica Neue", Arial, sans-serif;
    --font-mono: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas,
                 "Liberation Mono", monospace;

{chr(10).join(type_lines)}
    --text-5xl:  clamp(2.75rem, 2.1226rem + 2.642vw, 4.5rem);   /* display */
    --text-6xl:  clamp(3.5rem,  2.2901rem + 5.094vw, 6.875rem); /* hero    */

    --leading-none:    1;
    --leading-tight:   1.15;
    --leading-snug:    1.3;
    --leading-normal:  1.6;
    --leading-relaxed: 1.75;

    --tracking-tighter: -0.03em;
    --tracking-tight:   -0.015em;
    --tracking-normal:  0em;
    --tracking-wide:    0.02em;
    --tracking-caps:    0.08em;

    --weight-regular:  400;
    --weight-medium:   500;
    --weight-semibold: 600;
    --weight-bold:     700;

    /* ---------------------------------------------------------------------
       4. TYPOGRAPHY — TIER 2 (roles). Size, leading, weight and family
       travel together or a 35px heading ends up at body leading.
       --------------------------------------------------------------------- */

{chr(10).join(type_role_lines)}
    --type-display:  var(--weight-bold) var(--text-6xl)/var(--leading-tight) var(--font-sans);
    --type-code:     var(--weight-regular) var(--text-sm)/var(--leading-normal) var(--font-mono);

    /* ---------------------------------------------------------------------
       5. COLOR — TIER 1 (OKLCH ramps, derived from this codebase)
       --------------------------------------------------------------------- */

{neutral.css(neutral_comments)}

{accent.css(accent_comments)}

{chr(10).join(status[name].css() for name in ("success", "warning", "danger", "info"))}

    /* ---------------------------------------------------------------------
       6. COLOR — TIER 2 (roles). Components read THESE and only these.
       Dark mode re-points these names; no component rule changes.
       --------------------------------------------------------------------- */

{line("--bg-canvas:", "var(--neutral-50);")}
{line("--bg-surface:", "var(--neutral-0);")}
{line("--bg-raised:", "var(--neutral-0);")}
{line("--bg-sunken:", "var(--neutral-100);")}
{line("--bg-inverse:", "var(--neutral-900);")}
    --bg-scrim:       oklch(0% 0 0 / 0.5);

    --bg-hover:       oklch(0% 0 0 / 0.04);
    --bg-active:      oklch(0% 0 0 / 0.08);
{line("--bg-selected:", "var(--accent-50);")}
{line("--bg-disabled:", "var(--neutral-100);")}

{line("--fg-default:", "var(--neutral-900);")}
{line("--fg-strong:", "var(--neutral-950);")}
{line("--fg-muted:", "var(--neutral-600);")}
{line("--fg-subtle:", "var(--neutral-500);")}
{line("--fg-disabled:", "var(--neutral-400);")}
{line("--fg-on-accent:", "var(--neutral-0);")}
{line("--fg-on-inverse:", "var(--neutral-50);")}
{line("--fg-on-success:", "var(--neutral-1000);")}
{line("--fg-on-warning:", "var(--neutral-1000);")}
{line("--fg-on-danger:", "var(--neutral-0);")}
{line("--fg-accent:", "var(--accent-700);")}
{line("--fg-link:", "var(--accent-700);")}

{line("--border-subtle:", "var(--neutral-200);")}
{line("--border-default:", "var(--neutral-300);")}
{line("--border-strong:", "var(--neutral-500);")}
{line("--border-accent:", "var(--accent-500);")}
{line("--border-focus:", "var(--accent-600);")}
{line("--border-invalid:", "var(--danger-500);")}

{line("--bg-accent:", "var(--accent-600);")}
{line("--bg-accent-hover:", "var(--accent-700);")}
{line("--bg-success:", "var(--success-500);")}
{line("--bg-warning:", "var(--warning-500);")}
{line("--bg-danger:", "var(--danger-500);")}
{line("--fg-success:", "var(--success-700);")}
{line("--fg-warning:", "var(--warning-700);")}
{line("--fg-danger:", "var(--danger-700);")}

    /* ---------------------------------------------------------------------
       7. RADIUS, STROKE, ELEVATION
       --------------------------------------------------------------------- */

{line("--radius-none:", "0;")}
{line("--radius-xs:", "0.125rem;")}
{line("--radius-sm:", "0.25rem;")}
{line("--radius-md:", "0.5rem;")}
{line("--radius-lg:", "0.75rem;")}
{line("--radius-xl:", "1rem;")}
{line("--radius-2xl:", "1.5rem;")}
    --radius-full: 9999px;

{line("--stroke-hairline:", "1px;")}
{line("--stroke-default:", "1px;")}
{line("--stroke-thick:", "2px;")}
    --stroke-focus:    2px;

    /* Each elevation is a PAIR: a tight contact shadow plus a wider ambient
       one. Single-shadow elevation always looks like a sticker. */
    --shadow-none: none;
    --shadow-xs:  0 1px 2px  oklch(0% 0 0 / 0.05);
    --shadow-sm:  0 1px 2px  oklch(0% 0 0 / 0.06), 0 2px 4px  oklch(0% 0 0 / 0.04);
    --shadow-md:  0 2px 4px  oklch(0% 0 0 / 0.06), 0 6px 12px oklch(0% 0 0 / 0.06);
    --shadow-lg:  0 4px 8px  oklch(0% 0 0 / 0.06), 0 12px 24px oklch(0% 0 0 / 0.08);
    --shadow-xl:  0 8px 16px oklch(0% 0 0 / 0.07), 0 24px 48px oklch(0% 0 0 / 0.10);
  }}

  /* Theme-derived: these read colours or shadows a theme re-points, so they
     are declared on themed elements too, not resolved once on :root. */
  :root, [data-theme] {{
    --shadow-focus: 0 0 0 var(--stroke-focus) var(--bg-canvas),
                    0 0 0 calc(var(--stroke-focus) * 2) var(--border-focus);

{line("--elevation-flat:", "var(--shadow-none);")}
{line("--elevation-card:", "var(--shadow-sm);")}
{line("--elevation-raised:", "var(--shadow-md);")}
{line("--elevation-overlay:", "var(--shadow-lg);")}
{line("--elevation-modal:", "var(--shadow-xl);")}
{line("--elevation-focus:", "var(--shadow-focus);")}
  }}

  :root {{

    /* ---------------------------------------------------------------------
       8. MOTION
       --------------------------------------------------------------------- */

{line("--dur-instant:", "80ms;")}
{line("--dur-fast:", "140ms;")}
{line("--dur-base:", "220ms;")}
{line("--dur-slow:", "320ms;")}
{line("--dur-slower:", "480ms;")}

{line("--ease-out:", "cubic-bezier(0.22, 1, 0.36, 1);", 16)}
{line("--ease-in:", "cubic-bezier(0.64, 0, 0.78, 0);", 16)}
{line("--ease-in-out:", "cubic-bezier(0.65, 0, 0.35, 1);", 16)}
{line("--ease-spring:", "cubic-bezier(0.34, 1.56, 0.64, 1);", 16)}
    --ease-linear:  linear;

    --motion-hover:    var(--dur-fast)  var(--ease-out);
    --motion-enter:    var(--dur-base)  var(--ease-out);
    --motion-exit:     var(--dur-fast)  var(--ease-in);
    --motion-expand:   var(--dur-slow)  var(--ease-in-out);
    --motion-emphasis: var(--dur-slow)  var(--ease-spring);
    --motion-instant:  var(--dur-instant) var(--ease-out);
    /* Looping motion keeps its own duration, out of the reduced-motion
       block: a spinner that stops reads as a hung page. */
    --dur-loop:        900ms;
    --motion-loop:     var(--dur-loop) var(--ease-linear);
    --motion-travel-xs: var(--space-1);
    --motion-travel-sm: var(--space-2);
    --motion-travel-md: var(--space-4);

    /* ---------------------------------------------------------------------
       9. Z-INDEX — a closed ladder. Never write a literal z-index again.
       --------------------------------------------------------------------- */

{line("--z-base:", "0;")}
{line("--z-raised:", "10;")}
{line("--z-sticky:", "100;")}
{line("--z-dropdown:", "200;")}
{line("--z-overlay:", "300;")}
{line("--z-modal:", "400;")}
{line("--z-toast:", "500;")}
{line("--z-tooltip:", "600;")}

    /* ---------------------------------------------------------------------
       10. LAYOUT & BREAKPOINTS
       --------------------------------------------------------------------- */

    --bp-sm:  30rem;
    --bp-md:  48rem;
    --bp-lg:  64rem;
    --bp-xl:  80rem;
    --bp-2xl: 96rem;

    --tap-min: 2.75rem;
    --grid-columns: 12;
  }}

  /* =======================================================================
     DARK THEME — re-points Tier 2 only. Not one component selector below.
     ======================================================================= */

  [data-theme="dark"] {{
    color-scheme: dark;     /* native controls follow the tokens */

    --bg-canvas:      var(--neutral-1000);
    --bg-surface:     var(--neutral-950);
    --bg-raised:      var(--neutral-900);
    --bg-sunken:      var(--neutral-1000);
    --bg-inverse:     var(--neutral-100);
    --bg-scrim:       oklch(0% 0 0 / 0.6);

    --bg-hover:       oklch(100% 0 0 / 0.06);
    --bg-active:      oklch(100% 0 0 / 0.10);
    --bg-selected:    var(--accent-950);
    --bg-disabled:    var(--neutral-900);

    --fg-default:     var(--neutral-100);
    --fg-strong:      var(--neutral-50);
    --fg-muted:       var(--neutral-300);
    --fg-subtle:      var(--neutral-400);
    --fg-disabled:    var(--neutral-700);
    --fg-on-accent:   var(--neutral-1000);
    --fg-on-inverse:  var(--neutral-900);
    --fg-accent:      var(--accent-400);
    --fg-link:        var(--accent-400);

    --border-subtle:  var(--neutral-900);
    --border-default: var(--neutral-800);
    --border-strong:  var(--neutral-500);
    --border-invalid: var(--danger-400);

    --bg-accent:       var(--accent-500);
    --bg-accent-hover: var(--accent-400);

    --fg-success:     var(--success-500);
    --fg-warning:     var(--warning-500);
    --fg-danger:      var(--danger-400);

    --shadow-xs:  0 1px 2px  oklch(0% 0 0 / 0.30);
    --shadow-sm:  0 1px 2px  oklch(0% 0 0 / 0.36), 0 2px 4px  oklch(0% 0 0 / 0.24);
    --shadow-md:  0 2px 4px  oklch(0% 0 0 / 0.36), 0 6px 12px oklch(0% 0 0 / 0.30);
    --shadow-lg:  0 4px 8px  oklch(0% 0 0 / 0.40), 0 12px 24px oklch(0% 0 0 / 0.36);
    --shadow-xl:  0 8px 16px oklch(0% 0 0 / 0.44), 0 24px 48px oklch(0% 0 0 / 0.44);
  }}

  [data-theme="light"] {{ color-scheme: light; }}

  /* An inverse band re-points its text and border roles like any theme. */
  .inverse {{
    --fg-default:     var(--neutral-100);
    --fg-strong:      var(--neutral-50);
    --fg-muted:       var(--neutral-300);
    --fg-subtle:      var(--neutral-400);
    --fg-accent:      var(--accent-300);
    --fg-link:        var(--accent-300);
    --border-subtle:  var(--neutral-800);
    --border-default: var(--neutral-700);
    --border-strong:  var(--neutral-500);
  }}

  [data-theme="dark"] .inverse {{
    --fg-default:     var(--neutral-900);
    --fg-strong:      var(--neutral-1000);
    --fg-muted:       var(--neutral-600);
    --fg-subtle:      var(--neutral-500);
    --fg-accent:      var(--accent-700);
    --fg-link:        var(--accent-700);
    --border-subtle:  var(--neutral-200);
    --border-default: var(--neutral-300);
    --border-strong:  var(--neutral-500);
  }}

  [data-density="compact"]     {{ --density: 0.875; }}
  [data-density="comfortable"] {{ --density: 1; }}
  [data-density="spacious"]    {{ --density: 1.125; }}

  @media (prefers-reduced-motion: reduce) {{
    :root {{
      --dur-instant: 1ms;
      --dur-fast:    1ms;
      --dur-base:    1ms;
      --dur-slow:    1ms;
      --dur-slower:  1ms;
      --ease-spring: var(--ease-out);
    }}
  }}
}}
"""


# ===========================================================================
# Reconciliation report
# ===========================================================================

def render_reconciliation(prop: Proposal, payload: dict, args) -> str:
    total_lits = payload.get("counts", {}).get("literals", 0)
    covered = sum(r.occurrences for r in prop.rules)
    review = [r for r in prop.rules if r.confidence == "review"]
    unmapped_total = sum(u.occurrences for u in prop.unmapped)

    buf: List[str] = []
    buf.append("# Reconciliation report")
    buf.append("")
    buf.append(f"Source inventory: **{total_lits} literal(s)** across "
               f"{payload.get('counts', {}).get('files', 0)} file(s).")
    buf.append("")
    buf.append("| Outcome | Occurrences | Share |")
    buf.append("|---|---:|---:|")
    buf.append(f"| Mechanically replaceable | {covered} | "
               f"{_pctstr(covered, total_lits)} |")
    buf.append(f"| — of which need a human to look at the diff | "
               f"{sum(r.occurrences for r in review)} | "
               f"{_pctstr(sum(r.occurrences for r in review), total_lits)} |")
    buf.append(f"| Needs a design decision | {unmapped_total} | "
               f"{_pctstr(unmapped_total, total_lits)} |")
    buf.append("")
    buf.append("The second row is the honest part of any migration estimate. "
               "The first row is a script's afternoon; the third row is a "
               "designer's week.")
    buf.append("")

    if prop.notes:
        buf.append("## Decisions this run made for you")
        buf.append("")
        for n in prop.notes:
            buf.append(f"- {n}")
        buf.append("")

    if prop.contrast:
        buf.append("## Contrast, measured")
        buf.append("")
        buf.append("Every foreground role, original vs proposal, each measured "
                   "against the surface it actually lands on. WCAG 2.2 AA is "
                   "4.5:1 for body text and 3:1 for large text and UI "
                   "components. Measured, never assumed.")
        buf.append("")
        buf.append("| Original | Proposed role / surface | Before | After | Verdict |")
        buf.append("|---|---|---:|---:|---|")
        for original, role, before, after, verdict in prop.contrast:
            buf.append(f"| `{original}` | `{role}` | {before:.2f}:1 | "
                       f"{after:.2f}:1 | {verdict} |")
        buf.append("")
        regressions = [c for c in prop.contrast if c[3] < c[2] - 0.2]
        if regressions:
            buf.append(f"⚠ {len(regressions)} role(s) lose contrast against the "
                       f"original. That is not automatically wrong — the ramp is "
                       f"perceptually even and the original was not — but each "
                       f"one needs a human to agree before it ships.")
            buf.append("")

    if review:
        buf.append("## Replacements to review")
        buf.append("")
        buf.append("A length that moves more than 2px is roughly where a change "
                   "stops being invisible and starts being a diff someone "
                   "notices in a screenshot; a duration is here because its "
                   "role needs confirming. Each delta is in its value's unit. "
                   "Apply these in their own commit, with before/after shots.")
        buf.append("")
        buf.append("| Original | → Token | Δ | Occurrences | Why |")
        buf.append("|---|---|---:|---:|---|")
        for r in sorted(review, key=lambda r: -r.occurrences):
            # `delta_px` is the rule's own unit: a duration's is milliseconds.
            if r.kind == "color":
                delta = f"ΔE {r.delta_px:g}"
            elif r.kind == "shadow":
                delta = "—"                 # matched by structure, not by a distance
            else:
                unit = {"duration": "ms", "z-index": ""}.get(r.kind, "px")
                delta = f"{r.delta_px:+g}{unit}"
            buf.append(f"| `{', '.join(r.match[:3])}` | `{r.token}` | "
                       f"{delta} | {r.occurrences} | "
                       f"{r.note or r.kind} |")
        buf.append("")

    if prop.unmapped:
        buf.append("## Values with no home")
        buf.append("")
        buf.append("Every one of these is a design decision somebody has to "
                   "make. Do not widen the scale to absorb them — the closed "
                   "scale is the mechanism, and a scale you extend to settle an "
                   "argument has become a menu.")
        buf.append("")
        by_kind: Dict[str, List[Unmapped]] = defaultdict(list)
        for u in prop.unmapped:
            by_kind[u.kind].append(u)
        for kind in sorted(by_kind):
            buf.append(f"### {kind}")
            buf.append("")
            for u in sorted(by_kind[kind], key=lambda u: -u.occurrences):
                buf.append(f"**`{u.value}`** — {u.occurrences} occurrence(s)  ")
                buf.append(f"Where: {', '.join(u.where)}  ")
                buf.append(f"Why it does not map: {u.reason}  ")
                buf.append(f"Recommendation: {u.recommendation}")
                buf.append("")

    buf.append("## What the codemod will NOT do for you")
    buf.append("")
    buf.append("| Left behind | Why | Phase |")
    buf.append("|---|---|---|")
    buf.append("| Child `margin-*` on components | Law 2 is a layout change, "
               "not a value swap: deleting a child margin without adding the "
               "parent's `gap` collapses the layout. | Phase 4e, by hand, one "
               "container at a time |")
    buf.append("| JSX `style={{…}}` objects | Law 4. The value can be "
               "tokenized but the DECLARATION has to move into the "
               "stylesheet, which means a class name and a rule. | Phase 4f |")
    buf.append("| `!important` | Law 5. Removing it changes which rule wins; "
               "that is a cascade fix, not a find-and-replace. | Phase 4g |")
    buf.append("| `line-height` next to a tokenized `font-size` | The "
               "`--type-*` role already carries leading. The line has to be "
               "deleted, and a script that deletes lines is a script nobody "
               "approves. | Phase 4c review |")
    buf.append("| Vendor / third-party stylesheets | You layer them, you do "
               "not migrate them. | Never |")
    buf.append("")
    buf.append("## Next")
    buf.append("")
    buf.append("```sh")
    buf.append("# See the diff. This writes nothing.")
    buf.append("python -m scripts.apply_codemod ./src --mapping "
               f"{args.output or './proposal'}/mapping.json")
    buf.append("")
    buf.append("# Apply one kind at a time, one commit each.")
    buf.append("python -m scripts.apply_codemod ./src --mapping "
               f"{args.output or './proposal'}/mapping.json --kind color --apply")
    buf.append("```")
    buf.append("")
    return "\n".join(buf)


def _pctstr(part: int, whole: int) -> str:
    return f"{(100.0 * part / whole):.0f}%" if whole else "—"


# ===========================================================================
# CLI
# ===========================================================================

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="python -m scripts.cluster_values",
        description="Phases 2-3 of a token migration: cluster the extracted "
                    "literals into the decisions they were trying to be, and "
                    "propose a token system derived from them.",
        epilog="Writes tokens.css, mapping.json and reconciliation.md into the "
               "output directory. Nothing in your source tree is touched.",
    )
    ap.add_argument("literals", help="the JSON from extract_literals.py")
    ap.add_argument("-o", "--output", metavar="DIR", default="./proposal",
                    help="directory to write the proposal into "
                         "(default: ./proposal)")
    ap.add_argument("--spacing-tolerance", type=float, default=3.0, metavar="PX",
                    help="how far a length may move to reach a scale step "
                         "(default: 3.0). Anything further is reported, not "
                         "snapped.")
    ap.add_argument("--type-tolerance", type=float, default=3.0, metavar="PX",
                    help="the same, for font sizes (default: 3.0)")
    ap.add_argument("--color-tolerance", type=float, default=0.025, metavar="DE",
                    help="OKLab dE below which two colors are one decision "
                         "(default: 0.025 — about 7 sRGB code values)")
    ap.add_argument("--duration-tolerance", type=float, default=60.0, metavar="MS",
                    help="how far a duration may move (default: 60)")
    ap.add_argument("--accent", metavar="COLOR",
                    help="pin the accent seed instead of deriving it from the "
                         "codebase's most-used chromatic color")
    ap.add_argument("--tokens", action="append", default=[], metavar="FILE",
                    help="the project's token file, a tokens.css or a contract.json "
                         "(repeatable): its steps of the contract's ramps replace the "
                         "derived ones (default: the token files the project's "
                         ".design-suite.json lists)")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the reconciliation report and write nothing")
    return ap


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    src = Path(args.literals)
    if not src.exists():
        print(f"cluster_values: no such file: {src}\n"
              f"Create it first:\n"
              f"  python -m scripts.extract_literals ./src --format json "
              f"-o {src}", file=sys.stderr)
        return 2
    try:
        payload = json.loads(src.read_bytes())
    except (OSError, json.JSONDecodeError) as exc:
        print(f"cluster_values: {src} is not readable JSON ({exc}).\n"
              f"It must be the output of `extract_literals.py --format json`.",
              file=sys.stderr)
        return 2
    if payload.get("schema", "").split("@")[0] != "design-token-migration/literals":
        print(f"cluster_values: {src} is not a literal inventory "
              f"(schema={payload.get('schema')!r}). Re-run extract_literals.py "
              f"with --format json.", file=sys.stderr)
        return 2

    idx = literal_index(payload)
    prop = Proposal()
    # A flag beats the config: the project's token files only without --tokens (P24).
    try:
        sources, _config = token_sources(args.tokens)
        project = project_ramps(read_tokens(sources), prop) if sources else None
    except ConfigError as exc:
        print(f"cluster_values: {exc}", file=sys.stderr)
        return 2
    route_inline_styles(idx, prop)

    neutral, accent, status = cluster_color_phase(
        idx.get("color", []), args.color_tolerance, prop, args.accent, project)

    cluster_spacing(idx.get("length", []), args.spacing_tolerance, prop)
    cluster_type(idx.get("font-size", []), args.type_tolerance, prop)
    cluster_simple(idx.get("radius", []), RADIUS_STEPS, 2.0, "radius", prop,
                   props=sorted(RADIUS_PROPS),
                   recommendation="Radius is concentric: an inner radius should "
                                  "be the outer radius minus the inset. Get it "
                                  "wrong and corners look peeled. See "
                                  "references/spacing-system.md §8.",
                   tw_key={0: "none", 2: "xs", 4: "sm", 8: "md", 12: "lg",
                           16: "xl", 24: "2xl"})
    cluster_simple(idx.get("border-width", []), STROKE_STEPS, 0.5, "stroke", prop,
                   props=sorted(STROKE_PROPS),
                   recommendation="A stroke is either a hairline (1px), an "
                                  "emphasis (2px) or a focus ring (2px). A 3px "
                                  "border is a fill pretending to be a line.")
    cluster_motion(idx.get("duration", []), args.duration_tolerance, prop)
    cluster_easing(idx.get("easing", []), prop)
    cluster_shadows(idx.get("shadow", []), prop)
    cluster_z(idx.get("z-index", []), prop)
    cluster_leading(idx.get("line-height", []), prop)
    cluster_tracking(idx.get("tracking", []), prop)

    cf = idx.get("color-function", [])
    if cf:
        by_val: Dict[str, List[dict]] = defaultdict(list)
        for l in cf:
            by_val[l["normalized"]].append(l)
        for value, items in sorted(by_val.items()):
            prop.unmapped.append(Unmapped(
                kind="color-function", value=value, occurrences=len(items),
                where=where_of(items),
                reason="a runtime color computation, not a value",
                recommendation="`darken($brand, 8%)` is a ramp step that was "
                               "never written down. Replace it with the step: "
                               "--accent-700 for a hover on --accent-600. "
                               "Preprocessor color math is per-call and "
                               "unauditable; a ramp is one table you can check "
                               "for contrast.",
            ))

    prop.rules.sort(key=lambda r: (r.kind, -r.occurrences, r.id))

    report = render_reconciliation(prop, payload, args)

    if args.dry_run:
        sys.stdout.write(report)
        return 0

    out = Path(args.output)
    try:
        out.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        print(f"cluster_values: cannot create {out}: {exc}", file=sys.stderr)
        return 2

    tokens_css = render_tokens_css(prop, neutral, accent, status,
                                   ", ".join(payload.get("roots", ["the repo"])))
    mapping = {
        "schema": "design-token-migration/mapping@1",
        "generated_from": str(src),
        "token_file": "tokens.css",
        "settings": {
            "spacing_tolerance_px": args.spacing_tolerance,
            "type_tolerance_px": args.type_tolerance,
            "color_tolerance_de": args.color_tolerance,
            "duration_tolerance_ms": args.duration_tolerance,
            "accent_seed": prop.accent_seed,
            "neutral_hue": prop.neutral_hue,
        },
        "rules": [
            {
                "id": r.id, "kind": r.kind, "scope": r.scope, "match": r.match,
                "replacement": r.replacement, "token": r.token,
                "prop_classes": r.prop_classes, "props": r.props,
                "occurrences": r.occurrences, "delta_px": r.delta_px,
                "confidence": r.confidence, "note": r.note,
            } for r in prop.rules
        ],
        "unmapped": [
            {"kind": u.kind, "value": u.value, "occurrences": u.occurrences,
             "where": u.where, "reason": u.reason,
             "recommendation": u.recommendation}
            for u in prop.unmapped
        ],
    }

    (out / "tokens.css").write_text(tokens_css, encoding="utf-8")
    (out / "mapping.json").write_text(json.dumps(mapping, indent=2) + "\n",
                                      encoding="utf-8")
    (out / "reconciliation.md").write_text(report, encoding="utf-8")

    covered = sum(r.occurrences for r in prop.rules)
    review = sum(r.occurrences for r in prop.rules if r.confidence == "review")
    print(f"cluster_values: {len(prop.rules)} rule(s) covering {covered} "
          f"occurrence(s); {review} need review; "
          f"{sum(u.occurrences for u in prop.unmapped)} need a design decision.")
    print(f"  {out / 'tokens.css'}")
    print(f"  {out / 'mapping.json'}")
    print(f"  {out / 'reconciliation.md'}   <- read this one first")
    return 0


if __name__ == "__main__":
    # A Windows pipe (git hook, CI, `> file`) defaults to the ANSI code page,
    # where printing →, Δ or ✓ raises UnicodeEncodeError. Consoles and
    # Claude Code already use UTF-8 and are left alone.
    for _stream in (sys.stdout, sys.stderr):
        if getattr(_stream, "encoding", "utf-8").lower() not in ("utf-8", "utf8"):
            _stream.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
