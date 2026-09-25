#!/usr/bin/env python3
"""Generate a perceptually-even OKLCH color ramp, gamut-mapped and contrast-audited.

Dependency-free (Python 3.8+, stdlib only). Produces Tier-1 ramp tokens that drop
straight into `assets/starter/styles/tokens.css` with the exact naming that file
uses (`--accent-500`, `--neutral-200`, ...), plus the WCAG 2.2 contrast matrix so
nobody has to guess which step is legal for body text.

The L curve, chroma falloff and hue drift implemented here are the same ones
documented in `references/color-system.md`. Change one, change both.

USAGE
-----
  # Accent ramp from a hex seed (peak chroma is pinned to the seed at step 500)
  python -m scripts.generate_color_ramp '#e8440a' --name accent

  # Same, but seeded in OKLCH directly
  python -m scripts.generate_color_ramp 'oklch(64.5% 0.188 42)' --name accent

  # Neutral ramp: low chroma (0.003-0.010) anchored to the accent's hue
  python -m scripts.generate_color_ramp '#e8440a' --name neutral --neutral

  # Emit JSON or TypeScript instead of CSS
  python -m scripts.generate_color_ramp '#2f6df6' --name accent --format json
  python -m scripts.generate_color_ramp '#2f6df6' --name accent --format ts

  # Custom ladder
  python -m scripts.generate_color_ramp '#2f6df6' --name brand --steps 100,300,500,700,900

  # Just check a pair
  python -m scripts.generate_color_ramp --check '#6b6b6b' '#ffffff'
  python -m scripts.generate_color_ramp --check 'oklch(47.5% 0.009 75)' 'oklch(98.2% 0.003 75)'

  # Audit a ramp against a non-default canvas
  python -m scripts.generate_color_ramp '#e8440a' --name accent --canvas '#0d0d0f'

Run it from the skill root (the directory containing `scripts/`). Running the
file directly — `python scripts/generate_color_ramp.py '#e8440a'` — works too.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from typing import Dict, List, Optional, Sequence, Tuple

# ---------------------------------------------------------------------------
# THE CURVES. These three tables ARE the house style. They are tuned, not
# generated: see references/color-system.md for why each one bends the way it
# does. Every ramp this studio ships comes off these numbers.
# ---------------------------------------------------------------------------

# Lightness per step. Non-linear on purpose: the top end is compressed (the eye
# resolves near-white poorly, so 50->200 must stay close or the tints separate
# into visible bands) and the middle is stretched (400->700 is where text and
# fills live and must be clearly distinct).
L_CURVE: Dict[int, float] = {
    50: 0.970,
    100: 0.935,
    200: 0.880,
    300: 0.805,
    400: 0.720,
    500: 0.645,
    600: 0.565,
    700: 0.470,
    800: 0.380,
    900: 0.300,
    950: 0.210,
}

# Chroma as a FRACTION of the seed's chroma. Peaks at 500 and falls off at both
# ends: full chroma near white turns neon, full chroma near black turns mud.
C_CURVE: Dict[int, float] = {
    50: 0.106,
    100: 0.223,
    200: 0.415,
    300: 0.628,
    400: 0.840,
    500: 1.000,
    600: 0.936,
    700: 0.787,
    800: 0.628,
    900: 0.479,
    950: 0.330,
}

# Hue drift magnitude in degrees. Steps lighter than 500 rotate toward the cool
# anchor, darker steps toward the warm anchor — a cool key light with warm
# bounce, which is what makes a ramp read as pigment instead of a lerp.
H_DRIFT: Dict[int, float] = {
    50: 4.0,
    100: 3.2,
    200: 2.4,
    300: 1.6,
    400: 0.8,
    500: 0.0,
    600: 1.0,
    700: 2.0,
    800: 3.0,
    900: 4.0,
    950: 5.0,
}

WARM_ANCHOR = 45.0   # red-orange
COOL_ANCHOR = 250.0  # blue

# Neutral ramp: absolute chroma, not a fraction. 0.003 at the extremes, 0.009 in
# the belly. Below 0.002 it reads as cheap screen-gray; above 0.012 the "neutral"
# starts competing with the accent.
NEUTRAL_L: Dict[int, float] = {
    0: 1.000,
    50: 0.982,
    100: 0.960,
    200: 0.922,
    300: 0.865,
    400: 0.715,
    500: 0.580,
    600: 0.475,
    700: 0.385,
    800: 0.280,
    900: 0.195,
    950: 0.130,
    1000: 0.080,
}

NEUTRAL_C: Dict[int, float] = {
    0: 0.000,
    50: 0.003,
    100: 0.004,
    200: 0.005,
    300: 0.006,
    400: 0.008,
    500: 0.009,
    600: 0.009,
    700: 0.008,
    800: 0.007,
    900: 0.006,
    950: 0.005,
    1000: 0.004,
}

DEFAULT_STEPS: List[int] = [50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950]
DEFAULT_NEUTRAL_STEPS: List[int] = [0] + DEFAULT_STEPS + [1000]

# --bg-canvas in the light theme is --neutral-50.
DEFAULT_CANVAS = "oklch(98.2% 0.003 75)"


class ColorError(ValueError):
    """Raised for anything the user typed that we cannot turn into a color."""


# ---------------------------------------------------------------------------
# sRGB <-> linear sRGB
# ---------------------------------------------------------------------------

def srgb_to_linear(c: float) -> float:
    """Undo the sRGB transfer function. Input and output are 0..1."""
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def linear_to_srgb(c: float) -> float:
    """Apply the sRGB transfer function. Input and output are 0..1."""
    return c * 12.92 if c <= 0.0031308 else 1.055 * (c ** (1 / 2.4)) - 0.055


# ---------------------------------------------------------------------------
# linear sRGB <-> OKLab (Bjorn Ottosson's M1 / M2 matrices)
# ---------------------------------------------------------------------------

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

    l = l_ ** 3
    m = m_ ** 3
    s = s_ ** 3

    return (
        +4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
        -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
        -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s,
    )


# ---------------------------------------------------------------------------
# OKLab <-> OKLCH
# ---------------------------------------------------------------------------

def oklab_to_oklch(L: float, a: float, b: float) -> Tuple[float, float, float]:
    C = math.hypot(a, b)
    H = math.degrees(math.atan2(b, a)) % 360.0
    return (L, C, H)


def oklch_to_oklab(L: float, C: float, H: float) -> Tuple[float, float, float]:
    rad = math.radians(H)
    return (L, C * math.cos(rad), C * math.sin(rad))


def hex_to_oklch(hex_str: str) -> Tuple[float, float, float]:
    r, g, b = hex_to_rgb(hex_str)
    lr, lg, lb = (srgb_to_linear(r), srgb_to_linear(g), srgb_to_linear(b))
    return oklab_to_oklch(*linear_srgb_to_oklab(lr, lg, lb))


def oklch_to_linear_rgb(L: float, C: float, H: float) -> Tuple[float, float, float]:
    return oklab_to_linear_srgb(*oklch_to_oklab(L, C, H))


def oklch_to_rgb(L: float, C: float, H: float) -> Tuple[float, float, float]:
    """Return sRGB 0..1, unclamped, so callers can test gamut membership."""
    lr, lg, lb = oklch_to_linear_rgb(L, C, H)
    return (linear_to_srgb(lr), linear_to_srgb(lg), linear_to_srgb(lb))


# ---------------------------------------------------------------------------
# Parsing and formatting
# ---------------------------------------------------------------------------

_HEX_RE = re.compile(r"^#?([0-9a-fA-F]{3}|[0-9a-fA-F]{4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")
_OKLCH_RE = re.compile(
    r"^oklch\(\s*([0-9.]+)\s*(%?)\s*[, ]\s*([0-9.]+)\s*[, ]\s*(-?[0-9.]+)\s*(deg)?\s*\)$",
    re.IGNORECASE,
)


def hex_to_rgb(hex_str: str) -> Tuple[float, float, float]:
    m = _HEX_RE.match(hex_str.strip())
    if not m:
        raise ColorError(
            f"{hex_str!r} is not a hex color. Expected #rgb, #rrggbb, or #rrggbbaa."
        )
    h = m.group(1)
    if len(h) in (3, 4):
        h = "".join(ch * 2 for ch in h)
    return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0)


def parse_color(value: str) -> Tuple[float, float, float]:
    """Parse '#e8440a' or 'oklch(64.5% 0.188 42)' into (L, C, H). L is 0..1."""
    text = value.strip()
    if not text:
        raise ColorError("Empty color string.")

    m = _OKLCH_RE.match(text)
    if m:
        raw_l, pct, raw_c, raw_h = m.group(1), m.group(2), m.group(3), m.group(4)
        L = float(raw_l) / 100.0 if pct else float(raw_l)
        if L > 1.0:
            # 'oklch(64.5 0.188 42)' with no % is almost certainly a percentage.
            L = L / 100.0
        C = float(raw_c)
        H = float(raw_h) % 360.0
        if not (0.0 <= L <= 1.0):
            raise ColorError(f"Lightness out of range in {value!r}: expected 0-100%.")
        if C < 0:
            raise ColorError(f"Negative chroma in {value!r}.")
        return (L, C, H)

    if _HEX_RE.match(text):
        return hex_to_oklch(text)

    raise ColorError(
        f"Cannot parse {value!r}. Use a hex color (#e8440a) or "
        "an OKLCH color (oklch(64.5% 0.188 42))."
    )


def rgb_to_hex(r: float, g: float, b: float) -> str:
    def ch(v: float) -> int:
        return max(0, min(255, int(round(v * 255))))

    return "#{:02x}{:02x}{:02x}".format(ch(r), ch(g), ch(b))


def fmt_num(value: float, places: int) -> str:
    s = f"{value:.{places}f}"
    return s


def _trim(value: str) -> str:
    return value.rstrip("0").rstrip(".") if "." in value else value


def format_oklch(L: float, C: float, H: float) -> str:
    """Match the formatting used in assets/starter/styles/tokens.css."""
    lightness = _trim(f"{L * 100:.1f}")
    if C < 5e-4:
        # A true achromatic swatch. Carrying a hue on it is noise.
        return f"oklch({lightness}% 0 0)"
    hue = _trim(f"{H:.1f}") or "0"
    if hue == "-0":
        hue = "0"
    return f"oklch({lightness}% {fmt_num(C, 3)} {hue})"


# ---------------------------------------------------------------------------
# Gamut mapping
# ---------------------------------------------------------------------------

def in_srgb_gamut(L: float, C: float, H: float, eps: float = 1e-4) -> bool:
    r, g, b = oklch_to_rgb(L, C, H)
    return all(-eps <= v <= 1.0 + eps for v in (r, g, b))


def gamut_map(L: float, C: float, H: float, iterations: int = 40) -> Tuple[float, float, float]:
    """Reduce chroma by binary search until the color is inside sRGB.

    L and H are preserved exactly. That is the whole point of doing this in
    OKLCH: clipping RGB channels instead would shift both lightness and hue,
    and a ramp whose step 500 silently got lighter is a ramp that no longer
    matches its neighbours.
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


# ---------------------------------------------------------------------------
# WCAG 2.2 contrast
# ---------------------------------------------------------------------------

def relative_luminance(r: float, g: float, b: float) -> float:
    """WCAG 2.x relative luminance. Input is sRGB 0..1."""
    rl, gl, bl = srgb_to_linear(r), srgb_to_linear(g), srgb_to_linear(b)
    return 0.2126 * rl + 0.7152 * gl + 0.0722 * bl


def contrast_ratio_rgb(
    fg: Tuple[float, float, float], bg: Tuple[float, float, float]
) -> float:
    l1 = relative_luminance(*fg)
    l2 = relative_luminance(*bg)
    if l2 > l1:
        l1, l2 = l2, l1
    return (l1 + 0.05) / (l2 + 0.05)


def contrast_ratio_oklch(
    a: Tuple[float, float, float], b: Tuple[float, float, float]
) -> float:
    ra = clamp_rgb(oklch_to_rgb(*a))
    rb = clamp_rgb(oklch_to_rgb(*b))
    return contrast_ratio_rgb(ra, rb)


def clamp_rgb(rgb: Tuple[float, float, float]) -> Tuple[float, float, float]:
    return tuple(max(0.0, min(1.0, v)) for v in rgb)  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Ramp construction
# ---------------------------------------------------------------------------

def _interp(table: Dict[int, float], step: int) -> float:
    """Piecewise-linear read of a curve table at an arbitrary step number."""
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
    return table[keys[-1]]  # unreachable


def rotate_toward(hue: float, anchor: float, amount: float) -> float:
    """Rotate `hue` toward `anchor` by at most `amount` degrees, shortest path."""
    delta = ((anchor - hue + 180.0) % 360.0) - 180.0
    if abs(delta) <= amount:
        return anchor % 360.0
    return (hue + math.copysign(amount, delta)) % 360.0


class Swatch:
    __slots__ = ("step", "L", "C", "H", "rgb", "hex", "css", "requested_c", "clipped")

    def __init__(self, step: int, L: float, C: float, H: float, requested_c: float):
        self.step = step
        self.L, self.C, self.H = L, C, H
        self.rgb = clamp_rgb(oklch_to_rgb(L, C, H))
        self.hex = rgb_to_hex(*self.rgb)
        self.css = format_oklch(L, C, H)
        self.requested_c = requested_c
        self.clipped = requested_c - C > 1e-3

    @property
    def clip_pct(self) -> float:
        if self.requested_c <= 0:
            return 0.0
        return 100.0 * (self.requested_c - self.C) / self.requested_c


def build_ramp(
    seed: Tuple[float, float, float],
    steps: Sequence[int],
    neutral: bool = False,
    chroma_scale: float = 1.0,
    hue_shift: float = 1.0,
) -> List[Swatch]:
    """Build the ramp from a seed (L, C, H).

    Accent mode pins peak chroma at step 500 to the seed's chroma and scales
    every other step by C_CURVE. Neutral mode ignores the seed's chroma
    entirely and uses the absolute NEUTRAL_C budget at the seed's hue, which is
    how you get a neutral that belongs to the accent instead of sitting next to
    it.
    """
    _, seed_c, seed_h = seed
    out: List[Swatch] = []

    for step in steps:
        if neutral:
            L = _interp(NEUTRAL_L, step)
            C = _interp(NEUTRAL_C, step) * chroma_scale
            H = seed_h if C > 0 else 0.0
        else:
            L = _interp(L_CURVE, step)
            C = seed_c * _interp(C_CURVE, step) * chroma_scale
            mag = _interp(H_DRIFT, step) * hue_shift
            if step < 500:
                H = rotate_toward(seed_h, COOL_ANCHOR, mag)
            elif step > 500:
                H = rotate_toward(seed_h, WARM_ANCHOR, mag)
            else:
                H = seed_h

        requested_c = C
        L, C, H = gamut_map(L, C, H)
        out.append(Swatch(step, L, C, H, requested_c))

    return out


# ---------------------------------------------------------------------------
# Emitters
# ---------------------------------------------------------------------------

def emit_css(name: str, ramp: Sequence[Swatch]) -> str:
    width = max(len(f"--{name}-{s.step}:") for s in ramp)
    value_width = max(len(s.css) for s in ramp) + 1
    lines = [
        f"/* {name} ramp — generated by scripts/generate_color_ramp.py.",
        "   Tier 1. No component may reference these names directly; bind them to",
        "   a Tier-2 role below and read the role. */",
    ]
    for s in ramp:
        decl = f"--{name}-{s.step}:".ljust(width + 1)
        value = (s.css + ";").ljust(value_width)
        lines.append(f"{decl}{value}  /* {s.hex} */")
    return "\n".join(lines)


def emit_json(name: str, ramp: Sequence[Swatch]) -> str:
    payload = {
        name: {
            str(s.step): {
                "oklch": s.css,
                "hex": s.hex,
                "l": round(s.L, 4),
                "c": round(s.C, 4),
                "h": round(s.H, 2),
            }
            for s in ramp
        }
    }
    return json.dumps(payload, indent=2)


def emit_ts(name: str, ramp: Sequence[Swatch]) -> str:
    ident = re.sub(r"[^0-9a-zA-Z]+", "_", name).strip("_") or "ramp"
    lines = [
        f"// {name} ramp — generated by scripts/generate_color_ramp.py",
        f"export const {ident} = {{",
    ]
    for s in ramp:
        lines.append(f'  {s.step}: "{s.css}", // {s.hex}')
    lines.append("} as const;")
    lines.append("")
    lines.append(f"export type {ident.capitalize()}Step = keyof typeof {ident};")
    return "\n".join(lines)


EMITTERS = {"css": emit_css, "json": emit_json, "ts": emit_ts}


# ---------------------------------------------------------------------------
# Contrast report
# ---------------------------------------------------------------------------

WHITE = (1.0, 0.0, 0.0)  # OKLCH white
BLACK = (0.0, 0.0, 0.0)  # OKLCH black


def verdict(ratio: float, threshold: float) -> str:
    return "PASS" if ratio + 1e-9 >= threshold else "FAIL"


def contrast_report(name: str, ramp: Sequence[Swatch], canvas: Tuple[float, float, float]) -> str:
    canvas_css = format_oklch(*canvas)
    lines = [
        "",
        "WCAG 2.2 contrast matrix",
        f"  canvas under test: {canvas_css}  ({rgb_to_hex(*clamp_rgb(oklch_to_rgb(*canvas)))})",
        "",
        "  token            hex       vs #fff  4.5  3.0  |  vs #000  4.5  3.0  |  vs canvas  body  ui",
        "  " + "-" * 94,
    ]

    body_safe: List[str] = []
    ui_safe: List[str] = []

    for s in ramp:
        c_white = contrast_ratio_oklch((s.L, s.C, s.H), WHITE)
        c_black = contrast_ratio_oklch((s.L, s.C, s.H), BLACK)
        c_canvas = contrast_ratio_oklch((s.L, s.C, s.H), canvas)

        token = f"--{name}-{s.step}"
        body = verdict(c_canvas, 4.5)
        ui = verdict(c_canvas, 3.0)
        if body == "PASS":
            body_safe.append(token)
        if ui == "PASS":
            ui_safe.append(token)

        lines.append(
            "  {token:<16} {hex:<9} {cw:>6.2f}  {cw45:<4} {cw30:<4} |"
            " {cb:>7.2f}  {cb45:<4} {cb30:<4} | {cc:>8.2f}  {body:<5} {ui}".format(
                token=token,
                hex=s.hex,
                cw=c_white,
                cw45=verdict(c_white, 4.5),
                cw30=verdict(c_white, 3.0),
                cb=c_black,
                cb45=verdict(c_black, 4.5),
                cb30=verdict(c_black, 3.0),
                cc=c_canvas,
                body=body,
                ui=ui,
            )
        )

    clipped = [
        f"--{name}-{s.step}(-{s.clip_pct:.0f}%)" for s in ramp if s.clipped
    ]

    lines += [
        "",
        "  body  = >= 4.5:1 on the canvas. Legal for text under 24px/19px-bold.",
        "  ui    = >= 3.0:1 on the canvas. Legal for large text, icons, borders,",
        "          component boundaries and focus indicators (WCAG 2.2 SC 1.4.11; focus geometry is 2.4.13).",
        "",
        f"  Safe for body text on this canvas: {', '.join(body_safe) if body_safe else 'NONE'}",
        f"  Safe for UI / large text:         {', '.join(ui_safe) if ui_safe else 'NONE'}",
    ]

    core_clip = [
        s for s in ramp if s.clipped and 400 <= s.step <= 700 and s.clip_pct > 10.0
    ]

    if clipped:
        lines.append(f"  Chroma pulled in to fit sRGB:      {', '.join(clipped)}")
        lines.append(
            "  (Heavy clipping at 50-200 is normal: sRGB has no saturated near-white."
        )
        if core_clip:
            names = ", ".join(f"--{name}-{s.step}" for s in core_clip)
            lines.append(
                f"   BUT {names} lost >10% in the 400-700 band, where the brand"
            )
            lines.append(
                "   actually lives. The seed is more chromatic than this hue can hold —"
            )
            lines.append("   lower the seed's C until this clears, or the ramp will read flat.)")
        else:
            lines.append(
                "   The 400-700 band — where the brand actually lives — is intact.)"
            )
    else:
        lines.append("  Chroma pulled in to fit sRGB:      none — whole ramp is in gamut.")

    return "\n".join(lines)


def check_pair(fg_raw: str, bg_raw: str) -> str:
    fg = parse_color(fg_raw)
    bg = parse_color(bg_raw)
    ratio = contrast_ratio_oklch(fg, bg)

    fg_hex = rgb_to_hex(*clamp_rgb(oklch_to_rgb(*fg)))
    bg_hex = rgb_to_hex(*clamp_rgb(oklch_to_rgb(*bg)))

    rows = [
        ("Body text (SC 1.4.3, < 24px)", 4.5),
        ("Large text (>= 24px / 19px bold)", 3.0),
        ("UI component + focus indicator (SC 1.4.11, 2.4.13)", 3.0),
        ("Enhanced body text (SC 1.4.6, AAA)", 7.0),
        ("Enhanced large text (AAA)", 4.5),
    ]

    lines = [
        f"  foreground  {format_oklch(*fg):<28} {fg_hex}",
        f"  background  {format_oklch(*bg):<28} {bg_hex}",
        "",
        f"  contrast ratio  {ratio:.2f}:1",
        "",
    ]
    for label, threshold in rows:
        lines.append(f"  {verdict(ratio, threshold):<5} {threshold:>4}:1  {label}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_steps(raw: Optional[str], neutral: bool) -> List[int]:
    if raw is None:
        return list(DEFAULT_NEUTRAL_STEPS if neutral else DEFAULT_STEPS)
    steps: List[int] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            value = int(part)
        except ValueError:
            raise ColorError(
                f"--steps expects comma-separated integers like '50,100,500'; got {part!r}."
            )
        if not 0 <= value <= 1000:
            raise ColorError(f"--steps values must be between 0 and 1000; got {value}.")
        steps.append(value)
    if not steps:
        raise ColorError("--steps was empty.")
    return steps


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m scripts.generate_color_ramp",
        description=(
            "Generate an OKLCH ramp with the studio's tuned L curve, chroma falloff "
            "and hue drift, gamut-mapped to sRGB and audited against WCAG 2.2."
        ),
        epilog=(
            "Examples:\n"
            "  python -m scripts.generate_color_ramp '#e8440a' --name accent\n"
            "  python -m scripts.generate_color_ramp '#e8440a' --name neutral --neutral\n"
            "  python -m scripts.generate_color_ramp '#2f6df6' --format ts --name brand\n"
            "  python -m scripts.generate_color_ramp --check '#6b6b6b' '#ffffff'\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "seed",
        nargs="?",
        help="Seed color: hex (#e8440a) or OKLCH (oklch(64.5%% 0.188 42)).",
    )
    parser.add_argument(
        "--name",
        default="accent",
        help="Token prefix, matching tokens.css naming. Default: accent.",
    )
    parser.add_argument(
        "--steps",
        default=None,
        help="Comma-separated ladder. Default: 50,100,200,...,900,950 "
        "(0 and 1000 added in --neutral mode).",
    )
    parser.add_argument(
        "--neutral",
        action="store_true",
        help="Low-chroma neutral ramp (0.003-0.010) anchored to the seed's hue.",
    )
    parser.add_argument(
        "--format",
        choices=sorted(EMITTERS),
        default="css",
        help="Output format. Default: css.",
    )
    parser.add_argument(
        "--canvas",
        default=DEFAULT_CANVAS,
        # argparse %-formats help strings, so literal percent signs must be doubled.
        help="Background the ramp is audited against. Default: "
        f"{DEFAULT_CANVAS.replace('%', '%%')} (--bg-canvas in the light theme).",
    )
    parser.add_argument(
        "--chroma-scale",
        type=float,
        default=1.0,
        help="Multiply the whole chroma curve. Use 0.85 for dark-mode ramps. Default: 1.0.",
    )
    parser.add_argument(
        "--hue-shift",
        type=float,
        default=1.0,
        help="Scale the hue drift. 0 disables it, 2 doubles it. Default: 1.0.",
    )
    parser.add_argument(
        "--no-contrast",
        action="store_true",
        help="Suppress the contrast matrix and print only the tokens.",
    )
    parser.add_argument(
        "--check",
        nargs=2,
        metavar=("FG", "BG"),
        help="Report the contrast ratio between two colors and exit.",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.check:
            print(check_pair(args.check[0], args.check[1]))
            return 0

        if not args.seed:
            parser.error(
                "a seed color is required (or use --check FG BG). "
                "Example: python -m scripts.generate_color_ramp '#e8440a' --name accent"
            )

        if args.chroma_scale <= 0:
            raise ColorError("--chroma-scale must be greater than 0.")
        if args.hue_shift < 0:
            raise ColorError("--hue-shift must be 0 or greater.")

        seed = parse_color(args.seed)
        canvas = parse_color(args.canvas)
        steps = parse_steps(args.steps, args.neutral)

        ramp = build_ramp(
            seed,
            steps,
            neutral=args.neutral,
            chroma_scale=args.chroma_scale,
            hue_shift=args.hue_shift,
        )

        # A neutral ramp is normally audited against its own step 50, because
        # that step IS --bg-canvas. Honour an explicit --canvas over this.
        if args.neutral and args.canvas == DEFAULT_CANVAS:
            for s in ramp:
                if s.step == 50:
                    canvas = (s.L, s.C, s.H)
                    break

        print(EMITTERS[args.format](args.name, ramp))
        if not args.no_contrast:
            print(contrast_report(args.name, ramp, canvas), file=sys.stderr)
        return 0

    except ColorError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
