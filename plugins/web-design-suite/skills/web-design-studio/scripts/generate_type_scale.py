#!/usr/bin/env python3
"""Generate a closed modular type scale for web-design-studio.

Emits `--text-*` tokens that match `assets/starter/styles/tokens.css` exactly in
name, plus a *recommended* line-height and letter-spacing per step derived from
the heuristics documented in `references/typography.md`. Doc and script are kept
in sync on purpose: if you change a constant here, change it there.

Stdlib only. Python 3.9+.

USAGE
-----
Run as a file:

    python scripts/generate_type_scale.py --preview
    python scripts/generate_type_scale.py --format css
    python scripts/generate_type_scale.py --base 16 --ratio minor-third \\
        --dual-ratio major-third --steps-down 3 --steps-up 7 --format css

Run as a module (from inside `scripts/`, or with `scripts/` on PYTHONPATH):

    python -m generate_type_scale --preview
    python -m generate_type_scale --format json
    PYTHONPATH=scripts python -m generate_type_scale --format tailwind

The shipped tokens.css scale is (approximately) reproduced by:

    python scripts/generate_type_scale.py --base 16 --ratio minor-third \\
        --dual-ratio major-third --steps-down 3 --steps-up 7 --snap-px \\
        --fluid 380 1440 --fluid-steps 2 --format css

See the REPRODUCING TOKENS.CSS note at the bottom of this docstring for the
exact places where the shipped file was hand-tuned away from the generator.

HEURISTICS
----------
Leading (line-height), unitless:

    running text   lh = 1.10 + 8.0 / size_px      clamped to [1.45, 1.75]
    headings       lh = 0.98 + 7.0 / size_px      clamped to [1.00, 1.35]

    A step is treated as a heading when size_px > base_px * 1.25, i.e. the first
    step that is unambiguously not body copy. Both curves are inverse in size —
    the taller the glyph, the less extra leading the eye needs to find the next
    line — but headings sit lower because they are short, few-line, and set at a
    narrow measure.

    The inverse rule governs MULTI-LINE running text. A single-line UI label at
    12px does not want 1.75; it wants `--leading-snug` so the control's box stays
    the height you designed. The script flags every sub-base step accordingly.

Tracking (letter-spacing), em:

    studio model   ls = 0.605 / size_px - 0.0378   clamped to [-0.040, +0.030]
    classic model  ls = 0.350 / size_px - 0.0055   clamped to [-0.040, +0.030]

    Both are the same family (ls = B/size + A): tracking falls as size rises,
    steeply at small sizes and asymptotically at display sizes. The `classic`
    constants are the ones quoted around the web; they are calibrated for a face
    with loose default fitting and never go meaningfully negative (they cross
    zero at ~64px), which is why they disagree with this skill's tokens at every
    heading size. The `studio` constants are fitted to those tokens and
    reproduce every band exactly: +0.02em at 11-12px, 0em at 14-18px,
    -0.015em at 22-35px, -0.03em at 44px and up. That is the default.

    Neither is gospel — a typeface's own fitting outranks any curve. Always
    eyeball the result. Uppercase is not modelled: add ~+0.06em on top (that is
    `--tracking-caps`).

Basis for fluid steps:

    A fluid step is one token serving two sizes, so the two heuristics read
    different ends of it. Leading is computed from the MIN (mobile) size: too
    loose at 110px is a look, too tight at 56px is descenders colliding with the
    next line. Tracking is computed from the MAX (desktop) size: loose fitting is
    most visible where the glyphs are biggest.

REPRODUCING TOKENS.CSS
----------------------
1. Sub-base steps in tokens.css are hand-rounded to whole pixels (14 / 12 / 11)
   rather than strict 1.2 ratio steps (13.33 / 11.11 / 9.26). Use --snap-px.
   9px is unusable, so the bottom of the scale is deliberately compressed.
2. `--text-lg` (18px) is base x 1.125, not base x the up ratio; 18px is a
   lead-paragraph size, not a scale step. The 1.25 chain runs from there:
   18 -> 22.5 -> 28.1 -> 35.2 -> 43.9, which snaps to the shipped 22/28/35/44.
3. The fluid maxima in tokens.css (72px, 110px) are hand-amplified well past the
   1.25 chain. That is a legitimate Law-3 override for a marketing hero; this
   script will not invent it. Pass --fluid-min-ratio to widen the fluid span.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, asdict
from typing import List, Optional, Sequence

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #

ROOT_FONT_PX_DEFAULT = 16.0  # what 1rem means in the browser, unless the user
#                              has changed it. Never assume it is immutable.

NAMED_RATIOS = {
    "minor-second": 1.067,
    "major-second": 1.125,
    "minor-third": 1.200,
    "major-third": 1.250,
    "perfect-fourth": 1.333,
    "aug-fourth": 1.414,
    "perfect-fifth": 1.500,
    "golden": 1.618,
}

# The closed leading ladder from tokens.css. Computed values snap to these.
LEADING_TOKENS = {
    1.00: "--leading-none",
    1.15: "--leading-tight",
    1.30: "--leading-snug",
    1.60: "--leading-normal",
    1.75: "--leading-relaxed",
}

# The closed tracking ladder from tokens.css. `--tracking-caps` (0.08em) is
# excluded: it applies to uppercase runs, which are a case decision, not a size.
TRACKING_TOKENS = {
    -0.030: "--tracking-tighter",
    -0.015: "--tracking-tight",
    0.000: "--tracking-normal",
    0.020: "--tracking-wide",
}

TRACKING_MODELS = {
    # name: (B, A)  ->  ls_em = B / size_px + A
    "studio": (0.605, -0.0378),
    "classic": (0.350, -0.0055),
}
TRACKING_FLOOR = -0.040
TRACKING_CEIL = 0.030

# Role hints, keyed by token suffix. Matches the comments in tokens.css.
ROLES = {
    "3xs": "too small to ship — delete this step",
    "2xs": "legal, dense table meta",
    "xs": "labels, badges",
    "sm": "secondary UI text",
    "base": "body copy — never smaller for reading",
    "lg": "lead paragraph",
    "xl": "h4 / card title",
    "2xl": "h3",
    "3xl": "h2",
    "4xl": "h1",
    "5xl": "display",
    "6xl": "hero",
    "7xl": "oversize display — usability-gate it",
    "8xl": "oversize display — usability-gate it",
}


# --------------------------------------------------------------------------- #
# Model
# --------------------------------------------------------------------------- #


@dataclass
class Step:
    """One rung of the scale."""

    name: str  # "base", "2xl" — the token suffix
    token: str  # "--text-2xl"
    index: int  # signed distance from base
    px: float
    rem: float
    line_height: float  # snapped to the closed ladder
    line_height_raw: float  # what the curve actually said
    leading_token: str
    letter_spacing: float  # snapped, em
    letter_spacing_raw: float
    tracking_token: str
    role: str
    fluid: Optional[dict] = None  # {"min_px","max_px","min_rem","max_rem",
    #                                "intercept_rem","vw","css","algebra"}

    @property
    def css_value(self) -> str:
        if self.fluid:
            return self.fluid["css"]
        return f"{fmt(self.rem)}rem"


def js(value) -> str:
    """JSON-encode for a JS/TS literal, keeping real em dashes readable."""
    return json.dumps(value, ensure_ascii=False)


def fmt(value: float, places: int = 4) -> str:
    """Round to `places` and trim trailing FRACTIONAL zeros only.

    Stripping unconditionally turns 380 into 38 and 1.10 into 1.1 — one of those
    is fine and the other silently corrupts a viewport anchor. Only strip when
    there is a decimal point to strip back to.
    """
    text = f"{value:.{places}f}"
    if places > 0 and "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def step_name(index: int) -> str:
    """Token suffix for a signed step index. 0 is the base."""
    if index == 0:
        return "base"
    if index > 0:
        return {1: "lg", 2: "xl"}.get(index, f"{index - 1}xl")
    down = -index
    return {1: "sm", 2: "xs"}.get(down, f"{down - 1}xs")


def resolve_ratio(value: str) -> float:
    """Accept a named ratio or a float > 1."""
    key = value.strip().lower()
    if key in NAMED_RATIOS:
        return NAMED_RATIOS[key]
    try:
        number = float(key)
    except ValueError:
        names = ", ".join(sorted(NAMED_RATIOS))
        raise argparse.ArgumentTypeError(
            f"{value!r} is not a number or a known ratio. Known: {names}"
        ) from None
    if number <= 1.0:
        raise argparse.ArgumentTypeError(
            f"ratio must be > 1 (got {number}); a ratio of 1 or less produces a "
            "scale with no hierarchy."
        )
    if number > 2.5:
        raise argparse.ArgumentTypeError(
            f"ratio {number} is beyond usable (> 2.5). Even the golden ratio "
            "(1.618) needs a dual ratio to stay sane past h1."
        )
    return number


def snap(value: float, ladder: dict) -> tuple:
    """Snap a computed value to the nearest rung of a closed ladder."""
    best = min(ladder, key=lambda rung: abs(rung - value))
    return best, ladder[best]


def is_heading(px: float, base_px: float) -> bool:
    """True for steps that are unambiguously not running text."""
    return px > base_px * 1.25


def leading_for(px: float, base_px: float) -> float:
    """Recommended unitless line-height. See HEURISTICS in the module docstring."""
    if is_heading(px, base_px):
        return max(1.00, min(1.35, 0.98 + 7.0 / px))
    return max(1.45, min(1.75, 1.10 + 8.0 / px))


def tracking_for(px: float, model: str, base_px: float) -> float:
    """Recommended letter-spacing in em. See HEURISTICS in the module docstring.

    Running-text steps are floored at 0: negative tracking on lowercase body copy
    closes the counters and destroys word-shape recognition, which is the thing
    reading speed actually depends on. Tighten headings, never paragraphs.
    """
    b, a = TRACKING_MODELS[model]
    value = max(TRACKING_FLOOR, min(TRACKING_CEIL, b / px + a))
    if not is_heading(px, base_px):
        value = max(0.0, value)
    return value


def fluid_clamp(
    min_px: float,
    max_px: float,
    min_vw: float,
    max_vw: float,
    root_px: float,
) -> dict:
    """Solve the two-point line and express it as a clamp().

    Two anchors: (min_vw, min_px) and (max_vw, max_px). We want
    size_px(vw) = m * vw + c, rendered in CSS as `c_rem + (m*100)vw`.

        m = (max_px - min_px) / (max_vw - min_vw)
        c = min_px - m * min_vw

    The middle term keeps its intercept in `rem`, not `px`, so that a user who
    raises their default font size still scales the whole curve. A pure-vw
    middle term is a WCAG 1.4.4 failure.
    """
    span = max_vw - min_vw
    slope = (max_px - min_px) / span
    intercept_px = min_px - slope * min_vw
    vw = slope * 100.0
    min_rem = min_px / root_px
    max_rem = max_px / root_px
    intercept_rem = intercept_px / root_px
    css = (
        f"clamp({fmt(min_rem)}rem, "
        f"{fmt(intercept_rem)}rem + {fmt(vw, 3)}vw, "
        f"{fmt(max_rem)}rem)"
    )
    algebra = (
        f"{fmt(min_px, 2)}px @ {fmt(min_vw, 0)}px  ->  "
        f"{fmt(max_px, 2)}px @ {fmt(max_vw, 0)}px | "
        f"m = ({fmt(max_px, 2)} - {fmt(min_px, 2)}) / "
        f"({fmt(max_vw, 0)} - {fmt(min_vw, 0)}) = {fmt(slope, 6)} "
        f"-> {fmt(vw, 3)}vw | "
        f"c = {fmt(min_px, 2)} - {fmt(slope, 6)}*{fmt(min_vw, 0)} = "
        f"{fmt(intercept_px, 3)}px = {fmt(intercept_rem)}rem"
    )
    return {
        "min_px": round(min_px, 3),
        "max_px": round(max_px, 3),
        "min_rem": round(min_rem, 4),
        "max_rem": round(max_rem, 4),
        "intercept_rem": round(intercept_rem, 4),
        "vw": round(vw, 3),
        "css": css,
        "algebra": algebra,
    }


def build_scale(
    base: float,
    ratio: float,
    dual_ratio: Optional[float],
    steps_up: int,
    steps_down: int,
    snap_px: bool,
    root_px: float,
    tracking_model: str,
    fluid: Optional[Sequence[float]],
    fluid_steps: int,
    fluid_min_ratio: Optional[float],
) -> List[Step]:
    up_ratio = dual_ratio if dual_ratio else ratio
    indices = list(range(-steps_down, steps_up + 1))

    sizes = {}
    for i in indices:
        if i == 0:
            px = base
        elif i > 0:
            px = base * (up_ratio ** i)
        else:
            px = base / (ratio ** (-i))
        if snap_px:
            # Integer px below 32 (hinting and rounding actually bite there);
            # nearest half-px above, which rem math renders cleanly.
            px = round(px) if px < 32 else round(px * 2) / 2
        sizes[i] = px

    fluid_indices = set()
    if fluid is not None:
        if fluid_steps > 0:
            fluid_indices = set(indices[-fluid_steps:])

    steps: List[Step] = []
    for i in indices:
        px = sizes[i]
        name = step_name(i)

        fluid_data = None
        if i in fluid_indices:
            min_vw, max_vw = fluid
            shrink = fluid_min_ratio or up_ratio
            min_px = px / shrink
            if snap_px:
                min_px = round(min_px) if min_px < 32 else round(min_px * 2) / 2
            fluid_data = fluid_clamp(min_px, px, min_vw, max_vw, root_px)

        # Leading reads the small end of a fluid step, tracking the large end.
        lh_basis = fluid_data["min_px"] if fluid_data else px
        lh_raw = leading_for(lh_basis, base)
        lh, lh_token = snap(lh_raw, LEADING_TOKENS)
        ls_raw = tracking_for(px, tracking_model, base)
        ls, ls_token = snap(ls_raw, TRACKING_TOKENS)

        role = ROLES.get(name, "unassigned — give it a role or delete it")
        if i < 0:
            role += " [1-line: --leading-snug]"

        steps.append(
            Step(
                name=name,
                token=f"--text-{name}",
                index=i,
                px=round(px, 3),
                rem=round(px / root_px, 4),
                line_height=lh,
                line_height_raw=round(lh_raw, 3),
                leading_token=lh_token,
                letter_spacing=ls,
                letter_spacing_raw=round(ls_raw, 4),
                tracking_token=ls_token,
                role=role,
                fluid=fluid_data,
            )
        )
    return steps


# --------------------------------------------------------------------------- #
# Emitters
# --------------------------------------------------------------------------- #


def header_lines(args, up_ratio: float) -> List[str]:
    dual = (
        f"{fmt(args.ratio_value, 3)} below base / {fmt(up_ratio, 3)} above base"
        if args.dual_ratio
        else f"{fmt(args.ratio_value, 3)} throughout"
    )
    return [
        "Generated by scripts/generate_type_scale.py — do not hand-edit.",
        f"base {fmt(args.base, 2)}px | ratio {dual} | "
        f"{args.steps_down} down, {args.steps_up} up",
        f"tracking model: {args.tracking_model} "
        f"(ls_em = {TRACKING_MODELS[args.tracking_model][0]}/px "
        f"{TRACKING_MODELS[args.tracking_model][1]:+})",
        "The scale is CLOSED. Need a size between two steps? The layout is "
        "wrong, not the scale.",
    ]


def emit_css(steps: List[Step], args, up_ratio: float) -> str:
    out = ["/* " + "=" * 72]
    for line in header_lines(args, up_ratio):
        out.append("   " + line)
    out.append("   " + "=" * 72 + " */")
    out.append("")
    out.append("@layer tokens {")
    out.append("  :root {")
    out.append("")
    out.append("    /* Sizes — TIER 1 */")
    width = max(len(s.token) for s in steps) + 1
    decls = [f"{s.token + ':':<{width}} {s.css_value};" for s in steps]
    pad = max(len(d) for d in decls) + 2
    for s, decl in zip(steps, decls):
        out.append(f"    {decl:<{pad}}/* {fmt(s.px, 2):>6}px  {s.role} */")
        if s.fluid:
            out.append(f"    /* ^ {s.fluid['algebra']} */")
    out.append("")
    out.append("    /* Recommended pairing per step. These are the tokens the")
    out.append("       Tier-2 `--type-*` roles should compose, not new values. */")
    for s in steps:
        out.append(
            f"    /* {s.token:<12} -> line-height {s.leading_token:<18}"
            f"({fmt(s.line_height, 2)}, curve said {fmt(s.line_height_raw, 3)})"
            f"  letter-spacing {s.tracking_token:<19}"
            f"({fmt(s.letter_spacing, 3)}em, curve said "
            f"{fmt(s.letter_spacing_raw, 4)}em) */"
        )
    out.append("  }")
    out.append("}")
    return "\n".join(out)


def emit_json(steps: List[Step], args, up_ratio: float) -> str:
    payload = {
        "meta": {
            "base_px": args.base,
            "ratio_down": args.ratio_value,
            "ratio_up": up_ratio,
            "root_px": args.root,
            "tracking_model": args.tracking_model,
            "steps_up": args.steps_up,
            "steps_down": args.steps_down,
            "generator": "scripts/generate_type_scale.py",
        },
        "steps": [asdict(s) for s in steps],
    }
    return json.dumps(payload, indent=2)


def emit_ts(steps: List[Step], args, up_ratio: float) -> str:
    out = ["/**"]
    for line in header_lines(args, up_ratio):
        out.append(" * " + line)
    out.append(" */")
    out.append("")
    out.append("export const typeScale = {")
    for s in steps:
        key = s.name if s.name.isalpha() else f'"{s.name}"'
        out.append(
            f"  {key}: {{ size: {js(s.css_value)}, "
            f"lineHeight: {fmt(s.line_height, 2)}, "
            f"letterSpacing: {js(fmt(s.letter_spacing, 3) + 'em')}, "
            f"role: {js(s.role)} }},"
        )
    out.append("} as const;")
    out.append("")
    out.append("export type TypeStep = keyof typeof typeScale;")
    return "\n".join(out)


def emit_tailwind(steps: List[Step], args, up_ratio: float) -> str:
    out = ["// " + header_lines(args, up_ratio)[0]]
    out.append("// Mirror of the CSS custom properties. Keep both in sync or")
    out.append("// Tailwind will quietly reintroduce the sizes you deleted.")
    out.append("module.exports = {")
    out.append("  theme: {")
    out.append("    fontSize: {")
    for s in steps:
        out.append(
            f"      {js(s.name)}: [{js(s.css_value)}, "
            f"{{ lineHeight: {js(fmt(s.line_height, 2))}, "
            f"letterSpacing: {js(fmt(s.letter_spacing, 3) + 'em')} }}],"
            f"  // {fmt(s.px, 2)}px {s.role}"
        )
    out.append("    },")
    out.append("  },")
    out.append("};")
    return "\n".join(out)


def emit_preview(steps: List[Step], args, up_ratio: float) -> str:
    cols = ("step", "rem", "px", "line-height", "tracking", "role")
    rows = []
    for s in steps:
        size = s.fluid["css"] if s.fluid else f"{fmt(s.rem)}rem"
        px = (
            f"{fmt(s.fluid['min_px'], 2)}→{fmt(s.fluid['max_px'], 2)}"
            if s.fluid
            else fmt(s.px, 2)
        )
        rows.append(
            (
                s.token,
                size,
                px,
                f"{fmt(s.line_height, 2)} {s.leading_token}",
                f"{fmt(s.letter_spacing, 3)}em {s.tracking_token}",
                s.role,
            )
        )
    widths = [
        max(len(cols[i]), max(len(r[i]) for r in rows)) for i in range(len(cols))
    ]
    line = "  ".join("-" * w for w in widths)
    out = []
    for h in header_lines(args, up_ratio):
        out.append("# " + h)
    out.append("")
    out.append("  ".join(c.ljust(w) for c, w in zip(cols, widths)))
    out.append(line)
    for r in rows:
        out.append("  ".join(c.ljust(w) for c, w in zip(r, widths)))
    out.append(line)
    out.append("")
    out.append(
        "line-height/tracking are RECOMMENDATIONS snapped to the closed "
        "ladders in tokens.css."
    )
    out.append(
        "Uppercase runs: add ~+0.06em on top (--tracking-caps). "
        "Single-line UI labels below the base size: override to --leading-snug."
    )
    for s in steps:
        if s.fluid:
            out.append(f"{s.token}: {s.fluid['algebra']}")
    return "\n".join(out)


EMITTERS = {
    "css": emit_css,
    "json": emit_json,
    "ts": emit_ts,
    "tailwind": emit_tailwind,
}


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="generate_type_scale",
        description=(
            "Generate a closed modular type scale with recommended leading and "
            "tracking, in CSS / JSON / TS / Tailwind form."
        ),
        epilog=(
            "Examples:\n"
            "  python -m generate_type_scale --preview\n"
            "  python -m generate_type_scale --ratio major-third --format css\n"
            "  python -m generate_type_scale --ratio minor-third "
            "--dual-ratio major-third \\\n"
            "      --snap-px --fluid 380 1440 --format css\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--base", type=float, default=16.0,
        help="Base body size in px (default 16). Below 16 fails WCAG in "
             "practice; the script warns.",
    )
    p.add_argument(
        "--ratio", default="1.2",
        help="Scale ratio: a number > 1 or one of "
             + ", ".join(sorted(NAMED_RATIOS)) + " (default 1.2 / minor-third).",
    )
    p.add_argument(
        "--dual-ratio", default=None,
        help="Second ratio applied ABOVE the base, as this skill's tokens do "
             "(tight at body sizes, wider for headings). Same accepted values.",
    )
    p.add_argument("--steps-up", type=int, default=7,
                   help="Steps above the base (default 7 -> lg..6xl).")
    p.add_argument("--steps-down", type=int, default=3,
                   help="Steps below the base (default 3 -> sm, xs, 2xs).")
    p.add_argument("--root", type=float, default=ROOT_FONT_PX_DEFAULT,
                   help="Browser root font size used for rem math (default 16).")
    p.add_argument(
        "--snap-px", action="store_true",
        help="Round each step to whole px below 32px and half px above. "
             "Matches how tokens.css was authored.",
    )
    p.add_argument(
        "--tracking-model", choices=sorted(TRACKING_MODELS), default="studio",
        help="Letter-spacing curve (default studio; see module docstring).",
    )
    p.add_argument(
        "--fluid", nargs=2, type=float, metavar=("MIN_VW", "MAX_VW"),
        default=None,
        help="Emit clamp() for the top steps, interpolating between these two "
             "viewport widths in px (e.g. --fluid 380 1440).",
    )
    p.add_argument("--fluid-steps", type=int, default=2,
                   help="How many top steps go fluid (default 2).")
    p.add_argument(
        "--fluid-min-ratio", type=float, default=None,
        help="How far below its desktop size a fluid step starts. Default: the "
             "up ratio (one scale step down). Larger = more dramatic shrink.",
    )
    p.add_argument("--format", choices=sorted(EMITTERS), default="css",
                   help="Output format (default css).")
    p.add_argument("--preview", action="store_true",
                   help="Print an ASCII table instead of token output.")
    return p


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        args.ratio_value = resolve_ratio(args.ratio)
        up_ratio = (
            resolve_ratio(args.dual_ratio) if args.dual_ratio else args.ratio_value
        )
    except argparse.ArgumentTypeError as exc:
        parser.error(str(exc))
        return 2  # unreachable; keeps type checkers calm

    if args.base <= 0:
        parser.error("--base must be positive.")
    if args.root <= 0:
        parser.error("--root must be positive.")
    if args.steps_up < 0 or args.steps_down < 0:
        parser.error("--steps-up and --steps-down cannot be negative.")
    if args.steps_up + args.steps_down == 0:
        parser.error("A scale of one step is not a scale.")
    if args.fluid is not None:
        min_vw, max_vw = args.fluid
        if min_vw <= 0 or max_vw <= 0:
            parser.error("--fluid viewports must be positive px values.")
        if min_vw >= max_vw:
            parser.error(
                f"--fluid MIN_VW ({fmt(min_vw, 0)}) must be less than MAX_VW "
                f"({fmt(max_vw, 0)}); the slope is undefined otherwise."
            )
        if args.fluid_steps < 0:
            parser.error("--fluid-steps cannot be negative.")
        if args.fluid_steps > args.steps_up + args.steps_down + 1:
            parser.error(
                f"--fluid-steps {args.fluid_steps} exceeds the "
                f"{args.steps_up + args.steps_down + 1} steps in this scale."
            )
    if args.fluid_min_ratio is not None and args.fluid_min_ratio <= 1:
        parser.error("--fluid-min-ratio must be > 1.")
    if args.base < 16:
        print(
            f"warning: --base {fmt(args.base, 2)}px puts body copy below 16px. "
            "That is a readability failure on phones and an accessibility "
            "complaint waiting to happen.",
            file=sys.stderr,
        )

    steps = build_scale(
        base=args.base,
        ratio=args.ratio_value,
        dual_ratio=up_ratio if args.dual_ratio else None,
        steps_up=args.steps_up,
        steps_down=args.steps_down,
        snap_px=args.snap_px,
        root_px=args.root,
        tracking_model=args.tracking_model,
        fluid=args.fluid,
        fluid_steps=args.fluid_steps,
        fluid_min_ratio=args.fluid_min_ratio,
    )

    smallest = min(s.px for s in steps)
    if smallest < 11:
        print(
            f"warning: smallest step is {fmt(smallest, 2)}px. Nothing below 11px "
            "is legible on a real screen — drop a --steps-down, or hand-round "
            "the bottom of the scale as tokens.css does (14 / 12 / 11).",
            file=sys.stderr,
        )

    if args.preview:
        print(emit_preview(steps, args, up_ratio))
    else:
        print(EMITTERS[args.format](steps, args, up_ratio))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
