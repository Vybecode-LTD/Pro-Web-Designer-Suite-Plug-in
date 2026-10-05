#!/usr/bin/env python3
"""Convert Figma variables into tokens.css / tokens.json / tokens.ts -- and back.

Dependency-free (Python 3.9+, stdlib only). Forward, it turns an export into
generated token files whose names match the contract exactly. Reverse, it turns
a tokens.json into a body for `POST /v1/files/:file_key/variables`, so code can
be the source of truth and Figma the mirror.

Names are the whole job. Figma's `/` grouping and the `--category-role-variant`
grammar are the same grammar with a different separator, so `Semantic/bg/surface`
and `--bg-surface` are the same token and a round trip has to prove it. Anything
this script cannot place against a known token name is emitted with its slug and
flagged loudly, never silently renamed.

INPUT SHAPES (auto-detected by figma_common.py, as for figma_audit.py)
  rest | plugin | dtcg | records      -- see figma_audit.py's docstring

USAGE
-----
  # Figma -> code
  python scripts/figma_to_tokens.py variables.json --out src/styles/tokens.css
  python scripts/figma_to_tokens.py variables.json --format json --out design/tokens.json
  python scripts/figma_to_tokens.py variables.json --format ts   --out src/lib/tokens.ts
  python scripts/figma_to_tokens.py variables.json --format all  --out-dir build/tokens

  # Code -> Figma (a POST /v1/files/:key/variables body; Enterprise-only endpoint)
  python scripts/figma_to_tokens.py design/tokens.json --reverse --out figma-payload.json

  # Drift check in CI: regenerate and compare, no writes
  python scripts/figma_to_tokens.py variables.json --format css | diff -u src/styles/tokens.css -

EXIT CODES
  0  wrote (or would write) cleanly
  1  wrote, but with unresolved aliases / unmapped names / skipped composites
  2  could not read the input
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

# A sibling import would otherwise leave __pycache__ inside the installed
# plugin, which is read-only as far as a project is concerned.
sys.dont_write_bytecode = True
# The reader the audit uses too (LC-C3): the colour maths, as_color, as_px and
# as_alias, FVar, FCollection, FDoc, slugify and load_document.
try:                                              # python -m scripts.figma_to_tokens
    from .figma_common import *                   # type: ignore[import-not-found]  # noqa: F403
except ImportError:                               # python scripts/figma_to_tokens.py
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from figma_common import *                    # type: ignore[no-redef]  # noqa: F403

# ===========================================================================
# The contract's token names. This list is what makes the round trip lossless:
# a Figma variable called `Primitive/Space/6` has to come back as `--space-6`
# and not `--primitive-space-6`, and the only reliable way to know that is to
# hold the real vocabulary. Keep in step with tokens.css.
# ===========================================================================

TIER1 = [
    "space-0", "space-px", "space-0-5", "space-1", "space-2", "space-3", "space-4",
    "space-5", "space-6", "space-8", "space-10", "space-12", "space-16", "space-20",
    "space-24", "space-32", "space-40", "space-48",
    "space-fluid-sm", "space-fluid-md", "space-fluid-lg", "space-fluid-xl", "density",
    "font-sans", "font-mono",
    "text-2xs", "text-xs", "text-sm", "text-base", "text-lg", "text-xl",
    "text-2xl", "text-3xl", "text-4xl", "text-5xl", "text-6xl",
    "leading-none", "leading-tight", "leading-snug", "leading-normal", "leading-relaxed",
    "tracking-tighter", "tracking-tight", "tracking-normal", "tracking-wide", "tracking-caps",
    "weight-regular", "weight-medium", "weight-semibold", "weight-bold",
    "radius-none", "radius-xs", "radius-sm", "radius-md", "radius-lg", "radius-xl",
    "radius-2xl", "radius-full",
    "stroke-hairline", "stroke-default", "stroke-thick", "stroke-focus",
    "shadow-none", "shadow-xs", "shadow-sm", "shadow-md", "shadow-lg", "shadow-xl",
    "shadow-focus",
    "dur-instant", "dur-fast", "dur-base", "dur-slow", "dur-slower",
    "ease-out", "ease-in", "ease-in-out", "ease-spring", "ease-linear",
    "bp-sm", "bp-md", "bp-lg", "bp-xl", "bp-2xl",
    "tap-min", "grid-columns",
    "measure-prose", "measure-narrow", "width-content", "width-wide", "width-form",
]
for _ramp, _steps in (
    ("neutral", ("0", "50", "100", "200", "300", "400", "500", "600", "700", "800",
                 "900", "950", "1000")),
    ("accent", ("50", "100", "200", "300", "400", "500", "600", "700", "800", "900", "950")),
    ("success", ("100", "500", "700")), ("warning", ("100", "500", "700")),
    ("danger", ("100", "500", "700")), ("info", ("100", "500", "700")),
):
    TIER1 += [f"{_ramp}-{s}" for s in _steps]

TIER2 = [
    "gap-fused", "gap-tight", "gap-related", "gap-grouped", "gap-separate", "gap-distinct",
    "pad-inline-xs", "pad-inline-sm", "pad-inline-md",
    "pad-block-xs", "pad-block-sm", "pad-block-md",
    "pad-card", "pad-card-lg", "pad-well",
    "space-section", "space-subsection", "space-block", "gutter-page",
    "bg-canvas", "bg-surface", "bg-raised", "bg-sunken", "bg-inverse", "bg-scrim",
    "bg-hover", "bg-active", "bg-selected", "bg-disabled",
    "fg-default", "fg-strong", "fg-muted", "fg-subtle", "fg-disabled",
    "fg-on-accent", "fg-on-inverse", "fg-on-success", "fg-on-warning", "fg-on-danger",
    "fg-accent", "fg-link",
    "border-subtle", "border-default", "border-strong", "border-accent", "border-focus",
    "border-invalid",
    "bg-accent", "bg-accent-hover", "bg-success", "bg-warning", "bg-danger",
    "fg-success", "fg-warning", "fg-danger",
    "type-display", "type-h1", "type-h2", "type-h3", "type-h4",
    "type-lead", "type-body", "type-ui", "type-label", "type-code",
    "elevation-flat", "elevation-card", "elevation-raised", "elevation-overlay",
    "elevation-modal", "elevation-focus",
    "motion-hover", "motion-enter", "motion-exit", "motion-expand", "motion-emphasis",
    "motion-instant", "motion-loop",
    "motion-travel-xs", "motion-travel-sm", "motion-travel-md",
    "z-base", "z-raised", "z-sticky", "z-dropdown", "z-overlay", "z-modal",
    "z-toast", "z-tooltip",
]
KNOWN: Dict[str, str] = {}
for _n in TIER1:
    KNOWN[_n] = "primitive"
for _n in TIER2:
    KNOWN[_n] = "semantic"

# Tokens whose value is a composite CSS shorthand (`font` shorthand, a shadow
# pair, a duration+easing pair) or a clamp(). Figma variables are single scalars,
# so these cannot cross the boundary in either direction. Naming them here is
# what turns silent data loss into a printed warning.
COMPOSITE_ONLY = {n for n in TIER2 if n.startswith(("type-", "motion-", "elevation-"))
                  and not n.startswith("motion-travel-")}   # a distance, one FLOAT
COMPOSITE_ONLY |= {n for n in TIER1 if n.startswith(("shadow-", "ease-", "space-fluid-"))}
COMPOSITE_ONLY |= {"text-5xl", "text-6xl"}

# Category words a designer puts in front of everything. Stripping them is only
# safe when what remains is a token we recognise, which is why they are tried
# one at a time and always checked against KNOWN.
CATEGORY_PREFIXES = {
    "color", "colour", "colors", "colours", "size", "sizing", "dimension", "dimensions",
    "number", "numbers", "typography", "spacing", "space", "effect", "effects",
    "string", "boolean", "float", "value", "values", "scale",
}


# ===========================================================================
# Colour out -- figma_common.py's matrices, the same as
# web-design-studio/scripts/generate_color_ramp.py.
# ===========================================================================


def rgb_to_oklch(r: float, g: float, b: float) -> Tuple[float, float, float]:
    L, a, bb = linear_srgb_to_oklab(srgb_to_linear(r), srgb_to_linear(g), srgb_to_linear(b))
    return (L * 100.0, math.hypot(a, bb), math.degrees(math.atan2(bb, a)) % 360.0)


def _trim(x: float, places: int) -> str:
    s = f"{x:.{places}f}".rstrip("0").rstrip(".")
    return s if s not in ("", "-0") else "0"


# The canonical ramps, so a colour that IS a ramp step comes back as the exact
# OKLCH tokens.css holds rather than the hex round trip's drift. Near-zero
# chroma makes hue numerically unstable -- #faf9f7 reconstructs as hue 84.6 when
# the source said 75 -- and a generated file that differs from the canonical one
# by a hue digit produces a diff in every CI run forever.
RAMP_OKLCH: Dict[str, Dict[str, Tuple[float, float, float]]] = {
    "neutral": {"0": (100.0, 0.0, 0.0), "50": (98.2, 0.003, 75), "100": (96.0, 0.004, 75),
                "200": (92.2, 0.005, 75), "300": (86.5, 0.006, 75), "400": (71.5, 0.008, 75),
                "500": (53.5, 0.009, 75), "600": (47.5, 0.009, 75), "700": (38.5, 0.008, 75),
                "800": (28.0, 0.007, 75), "900": (19.5, 0.006, 75), "950": (13.0, 0.005, 75),
                "1000": (8.0, 0.004, 75)},
    "accent": {"50": (97.0, 0.020, 42), "100": (93.5, 0.042, 42), "200": (88.0, 0.078, 42),
               "300": (80.5, 0.118, 42), "400": (72.0, 0.158, 42), "500": (64.5, 0.188, 42),
               "600": (56.5, 0.176, 42), "700": (47.0, 0.148, 42), "800": (38.0, 0.118, 42),
               "900": (30.0, 0.090, 42), "950": (21.0, 0.062, 42)},
    "success": {"100": (94.0, 0.050, 152), "500": (62.0, 0.150, 152), "700": (45.0, 0.120, 152)},
    "warning": {"100": (95.5, 0.055, 85), "500": (75.0, 0.155, 85), "700": (52.0, 0.125, 85)},
    "danger": {"100": (94.5, 0.038, 25), "400": (64.0, 0.190, 25), "500": (58.0, 0.205, 25),
               "700": (45.0, 0.170, 25)},
    "info": {"100": (94.5, 0.035, 250), "500": (58.0, 0.160, 250), "700": (45.0, 0.140, 250)},
}
_CANONICAL: Dict[str, Tuple[float, float, float]] = {}


def canonical_oklch(hex_value: str) -> Optional[Tuple[float, float, float]]:
    if not _CANONICAL:
        for _rows in RAMP_OKLCH.values():
            for _oklch in _rows.values():
                _CANONICAL[rgb_to_hex(*oklch_to_rgb(*_oklch))] = _oklch
    return _CANONICAL.get(hex_value)


def format_oklch(r: float, g: float, b: float, a: float = 1.0) -> str:
    canon = canonical_oklch(rgb_to_hex(r, g, b))
    if canon is not None:
        L, C, H = canon
    else:
        L, C, H = rgb_to_oklch(r, g, b)
    if C < 0.0005:
        body = f"{_trim(L, 1)}% 0 0"
    else:
        body = f"{_trim(L, 1)}% {_trim(C, 3)} {_trim(H, 1)}"
    return f"oklch({body})" if a >= 0.999 else f"oklch({body} / {_trim(a, 3)})"


# ===========================================================================
# Names. Parsing is figma_common.py's, shared with figma_audit.py: the two
# scripts must agree about what a file says, or the audit passes and the build
# is wrong.
# ===========================================================================


def natural_key(token: str) -> Tuple:
    """`neutral-50` before `neutral-300` before `neutral-1000`. Ramp steps are
    numbers; sorting them as text puts 1000 next to 100 and reads as a bug."""
    return tuple(
        (1, int(p)) if p.isdigit() else (0, p)
        for p in re.split(r"(\d+)", token) if p != "")


def to_token_name(figma_name: str) -> Tuple[str, bool]:
    """Return (token name without `--`, recognised?).

    Tries the slug, then the slug with one leading category word removed at a
    time. Only a hit in KNOWN counts as recognised; everything else is emitted
    verbatim and reported, because a generator that guesses at names is how two
    vocabularies quietly become three."""
    slug = slugify(figma_name)
    if slug in KNOWN:
        return slug, True
    parts = slug.split("-")
    for i in range(1, min(len(parts), 4)):
        if parts[i - 1] not in CATEGORY_PREFIXES:
            break
        cand = "-".join(parts[i:])
        if cand in KNOWN:
            return cand, True
    # A ramp written as `accent/500` under a `color` group, or `gray` for
    # `neutral` -- the two aliases that show up in every file.
    swapped = re.sub(r"^(gray|grey)-", "neutral-", slug)
    if swapped in KNOWN:
        return swapped, True
    return slug, False


# ===========================================================================
# Mode -> selector. A Figma COLLECTION is a tier; a Figma MODE is a theme.
# That one sentence is the whole mapping, and this function is where it lands.
# ===========================================================================

DENSITY_MODES = {"compact": 0.875, "comfortable": 1.0, "cosy": 1.0, "cozy": 1.0,
                 "spacious": 1.125, "default": 1.0}


def mode_selector(mode: str, is_default: bool) -> Tuple[str, str]:
    """Return (css selector, kind). `kind` is 'root' | 'theme' | 'density'."""
    m = mode.strip().lower()
    if is_default:
        return ":root", "root"
    if re.fullmatch(r"(dark|night|dark mode|dark theme)", m):
        return '[data-theme="dark"]', "theme"
    if re.fullmatch(r"(light|day|light mode|light theme)", m):
        return '[data-theme="light"]', "theme"
    if m in DENSITY_MODES:
        return f'[data-density="{m}"]', "density"
    return f'[data-theme="{re.sub(r"[^a-z0-9]+", "-", m).strip("-")}"]', "theme"


# ===========================================================================
# Resolution
# ===========================================================================


@dataclass
class Problem:
    kind: str
    name: str
    message: str


class Converter:
    def __init__(self, doc: FDoc, *, color_format: str = "oklch",
                 unit: str = "rem", theme_diff_only: bool = True) -> None:
        self.doc = doc
        self.color_format = color_format
        self.unit = unit
        self.theme_diff_only = theme_diff_only
        self.problems: List[Problem] = []
        self.by_id: Dict[str, FVar] = dict(doc.by_id)
        self.by_slug: Dict[str, FVar] = {}
        for v in doc.variables:
            self.by_slug.setdefault(slugify(v.name), v)
        self.token_of: Dict[str, str] = {}
        for v in doc.variables:
            name, ok = to_token_name(v.name)
            self.token_of[v.var_id or v.name] = name
            if not ok:
                self.problems.append(Problem(
                    "unmapped-name", v.name,
                    f"`{v.name}` is not a name in the contract; emitted as `--{name}`. "
                    "Rename it in Figma or add it to the contract -- do not let both exist."))
        for path, why in doc.unsupported:
            self.problems.append(Problem(
                "unsupported-value", path,
                f"`{path}` was left out: {why}. Writing it anyway would put a value "
                "CSS cannot read into tokens.css; split a typography token into "
                "--type-* roles, or give the colour an sRGB `hex` fallback."))

    # -- lookups ------------------------------------------------------------

    def target(self, alias: str) -> Optional[FVar]:
        if alias in self.by_id:
            return self.by_id[alias]
        return self.by_slug.get(slugify(alias.replace(".", "/")))

    def token_name(self, var: FVar) -> str:
        return self.token_of.get(var.var_id or var.name, slugify(var.name))

    # -- value rendering ----------------------------------------------------

    def css_value(self, var: FVar, mode: str, raw: Any,
                  chain: Optional[List[str]] = None) -> Tuple[str, bool]:
        """Return (css text, resolved?). Aliases become `var(--other)` -- the
        reference is the point; flattening it would throw away the tiering."""
        chain = chain or []
        alias = as_alias(raw)
        if alias is not None:
            key = var.var_id or var.name
            if key in chain:
                self.problems.append(Problem(
                    "alias-cycle", var.name,
                    f"`{var.name}` is in an alias cycle ({' -> '.join(chain + [key])}). "
                    "Emitted as an unresolvable reference; CSS will treat it as invalid at "
                    "computed-value time, which is loud and therefore correct."))
                return (f"/* alias cycle */ var(--{self.token_name(var)})", False)
            tgt = self.target(alias)
            if tgt is None:
                self.problems.append(Problem(
                    "broken-alias", var.name,
                    f"`{var.name}` aliases `{alias}`, which is not in this export. "
                    "Emitted as a comment so the build fails visibly rather than silently "
                    "inheriting."))
                return (f"/* unresolved alias: {alias} */", False)
            # Guard the cycle by walking the target's own value with this in the chain.
            tmode = mode if mode in tgt.values else (
                next(iter(tgt.values)) if tgt.values else mode)
            nxt = tgt.values.get(tmode)
            if as_alias(nxt) is not None:
                _, ok = self.css_value(tgt, tmode, nxt, chain + [var.var_id or var.name])
                if not ok:
                    return (f"var(--{self.token_name(tgt)})", False)
            return (f"var(--{self.token_name(tgt)})", True)

        if var.resolved_type == "COLOR":
            if isinstance(raw, dict) and "color" in raw and (
                    as_alias(raw["color"]) is not None or as_alias(raw.get("opacity")) is not None):
                return self.composed_css(var, mode, raw, chain)
            rgba = as_color(raw)
            if rgba is None:
                if isinstance(raw, str):
                    return (raw, False)      # a keyword: transparent, currentColor
                # Never str() an object into tokens.css: a Python dict repr is
                # CSS nobody can read, and it used to exit 0.
                self.problems.append(Problem(
                    "unreadable-color", var.name,
                    f"`{var.name}` ({mode}) is not a colour this script can read: "
                    f"{str(raw)[:60]}. Emitted commented out."))
                return ("/* unreadable colour */", False)
            if self.color_format == "hex" and rgba[3] >= 0.999:
                return (rgb_to_hex(*rgba[:3]), True)
            return (format_oklch(*rgba), True)

        if var.resolved_type == "FLOAT":
            token = self.token_name(var)
            if token.startswith(("z-", "grid-", "weight-", "density")):
                px = as_px(raw)
                return (f"{px:g}" if px is not None else str(raw), True)
            if token.startswith("leading-") or token.startswith("tracking-"):
                n = float(raw) if isinstance(raw, (int, float)) else (as_px(raw) or 0.0)
                if token.startswith("tracking-"):
                    return (f"{n:g}em" if abs(n) <= 1 else f"{n / PX_PER_REM:g}em", True)
                return (f"{n:g}", True)
            if token.startswith("dur-"):
                n = as_px(raw)
                return (f"{n:g}ms" if n is not None else str(raw), True)
            px = as_px(raw)
            if px is None:
                return (str(raw), False)
            if self.unit == "px" or token in ("space-px", "stroke-hairline", "stroke-default",
                                              "stroke-thick", "stroke-focus"):
                return (f"{px:g}px", True)
            if px == 0:
                return ("0", True)
            return (f"{px / PX_PER_REM:g}rem", True)

        if var.resolved_type == "BOOLEAN":
            return ("1" if raw else "0", True)
        return (str(raw), True)

    def composed_css(self, var: FVar, mode: str, raw: dict,
                     chain: Optional[List[str]] = None) -> Tuple[str, bool]:
        """A VariableComposedColor with an alias in either channel. The link is
        the point, so it survives as `color-mix(in oklch, var(--x) 8%,
        transparent)`: the percentage is Figma's opacity, 0-100, unchanged."""
        opacity = raw.get("opacity", 100)
        op_alias = as_alias(opacity)
        if op_alias is not None:
            tgt = self.target(op_alias)
            if tgt is None:
                self.problems.append(Problem(
                    "broken-alias", var.name,
                    f"`{var.name}`'s opacity aliases `{op_alias}`, which is not in this export."))
                return (f"/* unresolved alias: {op_alias} */", False)
            pct, pct_css = None, f"calc(var(--{self.token_name(tgt)}) * 1%)"
        else:
            try:
                pct = float(opacity)
            except (TypeError, ValueError):
                self.problems.append(Problem(
                    "unreadable-color", var.name,
                    f"`{var.name}`'s opacity {opacity!r} is not a number."))
                return ("/* unreadable opacity */", False)
            pct_css = f"{pct:g}%"
        colour = raw["color"]
        if as_alias(colour) is not None:
            base, ok = self.css_value(var, mode, colour, chain)
        else:
            rgba = as_color(colour)
            if rgba is None:
                return ("/* unreadable colour */", False)
            base, ok = format_oklch(*rgba), True
        if not ok:
            return (base, False)
        if pct is not None and pct >= 100:
            return (base, True)
        return (f"color-mix(in oklch, {base} {pct_css}, transparent)", True)

    def json_value(self, var: FVar, mode: str, raw: Any) -> dict:
        css, ok = self.css_value(var, mode, raw)
        entry: Dict[str, Any] = {"value": css, "type": var.resolved_type.lower()}
        alias = as_alias(raw)
        composed = raw.get("color") if isinstance(raw, dict) and "color" in raw else None
        if alias is not None:
            tgt = self.target(alias)
            entry["alias"] = self.token_name(tgt) if tgt else alias
        elif composed is not None and as_alias(composed) is not None:
            tgt = self.target(as_alias(composed))
            entry["alias"] = self.token_name(tgt) if tgt else as_alias(composed)
            if isinstance(raw.get("opacity"), (int, float)):
                entry["alpha"] = round(float(raw["opacity"]) / 100.0, 6)
        elif var.resolved_type == "COLOR":
            rgba = as_color(raw)
            if rgba:
                entry["hex"] = rgb_to_hex(*rgba[:3])
                if rgba[3] < 0.999:
                    # Alpha stays a float. Folding it into an 8-digit hex would
                    # quantise a 4%-black overlay to 3.9%, which is a diff in
                    # every CI run and eventually a re-tuned overlay nobody asked for.
                    entry["alpha"] = round(rgba[3], 6)
        elif var.resolved_type == "FLOAT":
            px = as_px(raw)
            if px is not None:
                entry["px"] = px
        if var.description:
            entry["description"] = var.description
        if var.scopes:
            entry["figmaScopes"] = var.scopes
        entry["figmaName"] = var.name
        if not ok:
            entry["unresolved"] = True
        return entry

    # -- grouping -----------------------------------------------------------

    def tier_of(self, var: FVar) -> str:
        name = self.token_name(var)
        if name in KNOWN:
            return KNOWN[name]
        c = var.collection.strip().lower()
        for word, tier in (("primitive", "primitive"), ("core", "primitive"),
                           ("global", "primitive"), ("foundation", "primitive"),
                           ("semantic", "semantic"), ("alias", "semantic"),
                           ("theme", "semantic"), ("role", "semantic"),
                           ("component", "component")):
            if word in c:
                return tier
        return "semantic"

    def blocks(self) -> "Dict[str, List[Tuple[str, str, FVar, str, Any]]]":
        """selector -> [(tier, token, var, mode, raw)], tier-first and stable."""
        out: Dict[str, List[Tuple[str, str, FVar, str, Any]]] = {}
        order = {"primitive": 0, "semantic": 1, "component": 2}
        for var in self.doc.variables:
            col = self.doc.collections.get(var.collection)
            default = col.default_mode if col else next(iter(var.values), "Value")
            if default not in var.values and var.values:
                default = next(iter(var.values))
            for mode, raw in var.values.items():
                sel, _ = mode_selector(mode, mode == default)
                out.setdefault(sel, []).append(
                    (self.tier_of(var), self.token_name(var), var, mode, raw))
        for sel in out:
            out[sel].sort(key=lambda t: (order.get(t[0], 9), natural_key(t[1])))
        # `:root` first, then themes, then density.
        ordered = dict(sorted(out.items(), key=lambda kv: (kv[0] != ":root", kv[0])))
        if not self.theme_diff_only:
            return ordered
        # A theme block re-points Tier 2 and nothing else. Emitting tokens whose
        # value is identical to `:root` makes a theme look like it owns values it
        # merely inherits -- and the next person edits the wrong one.
        root = {}
        for tier, token, var, mode, raw in ordered.get(":root", []):
            root[token] = self.css_value(var, mode, raw)[0]
        trimmed: Dict[str, List[Tuple[str, str, FVar, str, Any]]] = {}
        for sel, rows in ordered.items():
            if sel == ":root":
                trimmed[sel] = rows
                continue
            keep = [r for r in rows if self.css_value(r[2], r[3], r[4])[0] != root.get(r[1])]
            if keep:
                trimmed[sel] = keep
        return trimmed


# ===========================================================================
# Emitters
# ===========================================================================


def build_date() -> Optional[str]:
    """The date to stamp, or None. Only SOURCE_DATE_EPOCH (the reproducible-
    builds convention) sets one: a clock time made two runs on an unchanged
    export differ, so the documented CI drift check failed every time."""
    epoch = os.environ.get("SOURCE_DATE_EPOCH", "").strip()
    if not epoch:
        return None
    try:
        return datetime.fromtimestamp(int(epoch), timezone.utc).strftime("%Y-%m-%d")
    except (ValueError, OverflowError, OSError):
        return None


def header(source: str, extra: Sequence[str] = ()) -> List[str]:
    stamp = build_date()
    lines = [
        "GENERATED FILE -- DO NOT EDIT BY HAND.",
        "",
        f"  source     {source}",
        f"  generator  scripts/figma_to_tokens.py",
        *([f"  generated  {stamp}"] if stamp else []),
        "",
        "Hand edits here are lost on the next sync, and worse, they make the",
        "design file and the code disagree while both look authoritative. Change",
        "the source, re-run the generator, commit both in one commit.",
    ]
    lines += list(extra)
    return lines


def emit_css(conv: Converter, source: str) -> str:
    out = ["/* " + "=" * 71, *[f"   {l}".rstrip() for l in header(source)],
           "   " + "=" * 71 + " */", "", "@layer tokens {", ""]
    for sel, rows in conv.blocks().items():
        out.append(f"  {sel} {{")
        last_tier = None
        for tier, token, var, mode, raw in rows:
            if tier != last_tier:
                if last_tier is not None:
                    out.append("")
                label = {"primitive": "TIER 1 -- primitives",
                         "semantic": "TIER 2 -- roles (components read these)",
                         "component": "TIER 3 -- component tokens"}.get(tier, tier)
                out.append(f"    /* {label} */")
                last_tier = tier
            css, ok = conv.css_value(var, mode, raw)
            comment = f"  /* {var.description} */" if var.description else ""
            if not ok and css.startswith("/*"):
                # Comment the whole declaration out rather than emit a property
                # with a comment for a value, which is invalid CSS and would take
                # the rest of the block down with it.
                out.append(f"    /* --{token}: {css.strip('/* ').strip()} */")
            else:
                out.append(f"    --{token}: {css};{comment}")
        out.append("  }")
        out.append("")
    out.append("}")
    return "\n".join(out) + "\n"


def emit_json(conv: Converter, source: str) -> str:
    payload: Dict[str, Any] = {
        "$generated": {
            "generator": "scripts/figma_to_tokens.py",
            "source": source,
            **({"generated": build_date()} if build_date() else {}),
            "warning": "GENERATED FILE -- edit the source, not this.",
            "note": ("For COLOR entries, `hex` is the exact value and `value` is the "
                     "human-readable OKLCH rounded for display. --reverse reads `hex`. "
                     "If you hand-edit one, edit both or delete `hex`."),
        },
        "primitive": {}, "semantic": {}, "component": {}, "themes": {},
    }
    for sel, rows in conv.blocks().items():
        for tier, token, var, mode, raw in rows:
            entry = conv.json_value(var, mode, raw)
            if sel == ":root":
                payload[tier][token] = entry
            else:
                theme = re.sub(r'^\[data-(theme|density)="(.*)"\]$', r"\2", sel)
                payload["themes"].setdefault(theme, {})[token] = entry
    for key in ("primitive", "semantic", "component"):
        payload[key] = dict(sorted(payload[key].items()))
    return json.dumps(payload, indent=2) + "\n"


def emit_ts(conv: Converter, source: str) -> str:
    blocks = conv.blocks()
    out = ["/**", *[f" * {l}".rstrip() for l in header(source)], " */", ""]
    root = blocks.get(":root", [])
    out.append("export const tokens = {")
    for _tier, token, var, mode, raw in root:
        css, _ = conv.css_value(var, mode, raw)
        out.append(f"  {json.dumps(token)}: {json.dumps(css)},")
    out.append("} as const;")
    out.append("")
    out.append("export type TokenName = keyof typeof tokens;")
    out.append("")
    out.append("/** `var(--token)`, typed. Use this rather than writing the string. */")
    out.append("export const cssVar = (name: TokenName): string => `var(--${name})`;")
    out.append("")
    themes = {sel: rows for sel, rows in blocks.items() if sel != ":root"}
    if themes:
        out.append("export const themes = {")
        for sel, rows in themes.items():
            theme = re.sub(r'^\[data-(theme|density)="(.*)"\]$', r"\2", sel)
            out.append(f"  {json.dumps(theme)}: {{")
            for _tier, token, var, mode, raw in rows:
                css, _ = conv.css_value(var, mode, raw)
                out.append(f"    {json.dumps(token)}: {json.dumps(css)},")
            out.append("  },")
        out.append("} as const;")
        out.append("")
        out.append("export type ThemeName = keyof typeof themes;")
    return "\n".join(out) + "\n"


# ===========================================================================
# Reverse: tokens.json -> a POST /v1/files/:file_key/variables body
#
# Verified against Figma's Variables REST docs (Sept 2026): the body takes four
# optional arrays -- variableCollections, variableModes, variables,
# variableModeValues -- each entry carrying action CREATE | UPDATE | DELETE.
# Temporary ids are scoped to one request body and may be used in `id` and in a
# collection's `initialModeId`. Colours are {r,g,b,a} in 0..1. Aliases are
# {"type":"VARIABLE_ALIAS","id":...}. The endpoint is Enterprise-only and needs
# the `file_variables:write` scope; this script only builds the body, it never
# calls the API.
# ===========================================================================

SCOPES_FOR = [
    (re.compile(r"^space-|^gap-|^pad-|^gutter-"), ["GAP", "WIDTH_HEIGHT"]),
    (re.compile(r"^radius-"), ["CORNER_RADIUS"]),
    (re.compile(r"^text-"), ["FONT_SIZE"]),
    (re.compile(r"^leading-"), ["LINE_HEIGHT"]),
    (re.compile(r"^tracking-"), ["LETTER_SPACING"]),
    (re.compile(r"^weight-"), ["FONT_WEIGHT"]),
    (re.compile(r"^stroke-"), ["STROKE_FLOAT"]),
    (re.compile(r"^bg-"), ["FRAME_FILL", "SHAPE_FILL"]),
    (re.compile(r"^fg-"), ["TEXT_FILL"]),
    (re.compile(r"^border-"), ["STROKE_COLOR"]),
    (re.compile(r"^(neutral|accent|success|warning|danger|info)-"), ["ALL_FILLS", "STROKE_COLOR"]),
    (re.compile(r"^font-"), ["FONT_FAMILY"]),
]


def figma_scopes(token: str) -> List[str]:
    for regex, scopes in SCOPES_FOR:
        if regex.match(token):
            return scopes
    return ["ALL_SCOPES"]


def figma_name(token: str) -> str:
    """`bg-surface` -> `bg/surface`; `space-6` -> `space/6`; `accent-500` ->
    `accent/500`. One `/` after the category word is what makes the Figma
    variables panel group the way the CSS namespace already does."""
    parts = token.split("-")
    if len(parts) == 1:
        return token
    head = parts[0]
    if head in ("space", "text", "leading", "tracking", "weight", "radius", "stroke",
                "shadow", "dur", "ease", "bp", "z", "gap", "pad", "bg", "fg", "border",
                "type", "elevation", "motion", "neutral", "accent", "success", "warning",
                "danger", "info", "measure", "width", "font", "tap", "grid", "gutter"):
        return f"{head}/{'-'.join(parts[1:])}"
    return token


VAR_REF = re.compile(r"^var\(\s*--([a-z0-9-]+)\s*\)$", re.I)


def alias_of(entry: dict) -> Optional[str]:
    alias = entry.get("alias")
    if alias:
        return str(alias)
    raw = entry.get("value")
    if isinstance(raw, str):
        m = VAR_REF.match(raw.strip())
        if m:
            return m.group(1)
    return None


def token_type(entry: dict, token: str,
               table: Optional[Dict[str, dict]] = None, _depth: int = 0) -> str:
    """Figma needs a resolvedType up front. A token whose value is only
    `var(--other)` has no type of its own, so follow the alias -- typing it
    STRING because the text starts with `var(` is the classic way a whole colour
    tier lands in Figma as unusable strings."""
    t = str(entry.get("type", "")).upper()
    if t in ("COLOR", "FLOAT", "STRING", "BOOLEAN"):
        return t
    alias = alias_of(entry)
    if alias and table is not None and _depth < 16:
        tgt = table.get(alias)
        if tgt is not None:
            return token_type(tgt, alias, table, _depth + 1)
    val = entry.get("value")
    if as_color(val) is not None:
        return "COLOR"
    if as_px(val) is not None:
        return "FLOAT"
    return "STRING"


def read_tokens_json(data: Any) -> Tuple[Dict[str, dict], Dict[str, Dict[str, dict]]]:
    """Accept this script's own tokens.json, or a flat {name: value} map."""
    base: Dict[str, dict] = {}
    themes: Dict[str, Dict[str, dict]] = {}
    if not isinstance(data, dict):
        raise ValueError("tokens.json must be an object")
    tiered = any(k in data for k in ("primitive", "semantic", "component"))
    if tiered:
        for tier in ("primitive", "semantic", "component"):
            for name, entry in (data.get(tier) or {}).items():
                base[name] = entry if isinstance(entry, dict) else {"value": entry}
                base[name].setdefault("tier", tier)
        for theme, rows in (data.get("themes") or {}).items():
            themes[theme] = {n: (e if isinstance(e, dict) else {"value": e})
                             for n, e in rows.items()}
    else:
        for name, entry in data.items():
            if name.startswith("$"):
                continue
            base[name.lstrip("-")] = entry if isinstance(entry, dict) else {"value": entry}
    return base, themes


def emit_reverse(data: Any, collection_split: bool = True) -> Tuple[str, List[Problem]]:
    base, themes = read_tokens_json(data)
    problems: List[Problem] = []

    tiers: Dict[str, Dict[str, dict]] = {"primitive": {}, "semantic": {}, "component": {}}
    for name, entry in base.items():
        tier = entry.get("tier") or KNOWN.get(name) or "semantic"
        tiers.setdefault(tier, {})[name] = entry
    # Primitives get no scopes, so no picker offers them: a designer binds
    # `bg/surface`, never the `neutral/0` it aliases (Law 6). Scopes only hide;
    # the semantic tier still aliases them.
    primitives = set(tiers["primitive"])
    if not collection_split:
        merged = {}
        for rows in tiers.values():
            merged.update(rows)
        tiers = {"tokens": merged}

    collections: List[dict] = []
    modes: List[dict] = []
    variables: List[dict] = []
    mode_values: List[dict] = []
    var_id_of: Dict[str, str] = {}
    mode_id_of: Dict[Tuple[str, str], str] = {}

    theme_names = sorted(themes.keys())
    tier_of: Dict[str, str] = {t: tier for tier, rows in tiers.items() for t in rows}

    def default_mode_for(tier: str) -> str:
        if tier == "primitive" or not theme_names:
            return "Value"
        # A `light` theme means `:root` was another one: two modes of one name
        # in a collection is a body Figma refuses.
        return "Default" if "light" in (t.lower() for t in theme_names) else "Light"

    def to_figma_value(token: str, entry: dict,
                       vtype: str) -> Tuple[Any, Optional[str]]:
        raw = entry.get("value")
        alias = alias_of(entry)
        if alias:
            tgt = var_id_of.get(alias)
            if tgt is None:
                why = ("is a composite that cannot cross into Figma"
                       if alias in COMPOSITE_ONLY else "is not in this tokens.json")
                return None, (f"`--{token}` aliases `--{alias}`, which {why}. Dropped from the "
                              "payload -- a variable with a wrong value is worse than a "
                              "variable that is visibly missing.")
            return {"type": "VARIABLE_ALIAS", "id": tgt}, None
        if vtype == "COLOR":
            # `hex` wins over `value` when both are present. `value` is rounded for
            # human reading (one decimal of L); `hex` is the exact 8-bit colour, and
            # Figma is an 8-bit sRGB surface anyway. Using `value` costs ~0.1% L on
            # every round trip, which shows up as a diff in CI forever.
            exact = as_color(entry.get("hex"))
            parsed = as_color(raw)
            rgba = exact or parsed
            if rgba is None:
                return None, f"`--{token}` is typed COLOR but `{raw}` does not parse as one."
            alpha = entry.get("alpha")
            if alpha is None:
                alpha = parsed[3] if parsed is not None else rgba[3]
            return {"r": round(rgba[0], 6), "g": round(rgba[1], 6),
                    "b": round(rgba[2], 6), "a": round(float(alpha), 6)}, None
        if vtype == "FLOAT":
            px = entry.get("px")
            if px is None:
                px = as_px(raw)
            if px is None:
                return None, f"`--{token}` is typed FLOAT but `{raw}` has no numeric value."
            return (round(px, 4) if px % 1 else int(px)), None
        if vtype == "BOOLEAN":
            return bool(raw), None
        return str(raw), None

    # Pass 1 -- which tokens can exist as Figma variables at all.
    for tier, rows in tiers.items():
        for token in rows:
            if token in COMPOSITE_ONLY:
                problems.append(Problem(
                    "composite", token,
                    f"`--{token}` is a composite (a CSS shorthand, a shadow pair or a clamp). "
                    "A Figma variable holds one scalar, so this cannot cross. Ship it as a "
                    "text or effect STYLE in Figma instead, named for the same role."))
                continue
            var_id_of[token] = f"tmp_var_{re.sub(r'[^a-z0-9]+', '_', token)}"

    # Pass 2 -- drop anything whose value cannot be produced, then re-check,
    # because dropping a token orphans everything aliased to it. Converges in a
    # couple of rounds on any real token file; the bound stops a pathological one.
    for _round in range(8):
        dropped: List[str] = []
        for token, tier in tier_of.items():
            if token not in var_id_of:
                continue
            entry = tiers[tier][token]
            vtype = token_type(entry, token, base)
            _, err = to_figma_value(token, entry, vtype)
            if err:
                problems.append(Problem("dropped", token, err))
                dropped.append(token)
        for token in dropped:
            var_id_of.pop(token, None)
        if not dropped:
            break

    # Pass 3 -- emit.
    for tier, rows in tiers.items():
        live = [t for t in sorted(rows) if t in var_id_of]
        if not live:
            continue
        col_id = f"tmp_collection_{tier}"
        default_mode = default_mode_for(tier)
        default_mode_id = f"tmp_mode_{tier}_{re.sub(r'[^a-z0-9]+', '_', default_mode.lower())}"
        collections.append({"action": "CREATE", "id": col_id, "name": tier,
                            "initialModeId": default_mode_id})
        # The initial mode comes into being with the collection, under Figma's
        # own name; `initialModeId` only gives it an id. An UPDATE names it, as
        # Figma's REST example does. Only the extra modes get a CREATE of their
        # own, or Figma is asked to make the first one twice.
        modes.append({"action": "UPDATE", "id": default_mode_id, "name": default_mode,
                      "variableCollectionId": col_id})
        mode_id_of[(tier, default_mode)] = default_mode_id
        if tier != "primitive":
            for theme in theme_names:
                mid = f"tmp_mode_{tier}_{re.sub(r'[^a-z0-9]+', '_', theme.lower())}"
                mode_id_of[(tier, theme)] = mid
                modes.append({"action": "CREATE", "id": mid, "name": theme.title(),
                              "variableCollectionId": col_id})
        for token in live:
            entry = rows[token]
            vtype = token_type(entry, token, base)
            variables.append({
                "action": "CREATE", "id": var_id_of[token], "name": figma_name(token),
                "variableCollectionId": col_id, "resolvedType": vtype,
                "scopes": [] if token in primitives else figma_scopes(token),
                "codeSyntax": {"WEB": f"var(--{token})"},
                **({"description": entry["description"]} if entry.get("description") else {}),
            })
            value, _ = to_figma_value(token, entry, vtype)
            mode_values.append({"variableId": var_id_of[token],
                                "modeId": default_mode_id, "value": value})
            if tier == "primitive":
                continue
            for theme in theme_names:
                tmid = mode_id_of.get((tier, theme))
                if tmid is None:
                    continue
                src = themes[theme].get(token) or entry
                tvalue, terr = to_figma_value(token, src, token_type(src, token, base))
                if terr:
                    continue        # already reported; the default mode carries the token
                mode_values.append({"variableId": var_id_of[token], "modeId": tmid,
                                    "value": tvalue})

    # Only the four arrays the endpoint takes, so the file is POSTed as it is.
    body = {
        "variableCollections": collections,
        "variableModes": modes,
        "variables": variables,
        "variableModeValues": mode_values,
    }
    return json.dumps(body, indent=2) + "\n", problems


# ===========================================================================
# CLI
# ===========================================================================


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="figma_to_tokens.py",
        description="Figma variables -> tokens.css/json/ts, and tokens.json -> Figma.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Exit 0 clean, 1 written with warnings, 2 unreadable input.")
    p.add_argument("path")
    p.add_argument("--format", choices=("css", "json", "ts", "all"), default="css")
    p.add_argument("--out", help="write here instead of stdout")
    p.add_argument("--out-dir", help="with --format all: write tokens.{css,json,ts} here")
    p.add_argument("--reverse", action="store_true",
                   help="read a tokens.json and emit a Figma variables POST body")
    p.add_argument("--shape", choices=("rest", "plugin", "dtcg", "records"))
    p.add_argument("--collection", default="tokens")
    p.add_argument("--color-format", choices=("oklch", "hex"), default="oklch")
    p.add_argument("--unit", choices=("rem", "px"), default="rem")
    p.add_argument("--full-themes", action="store_true",
                   help="emit every token in each theme block, not only the re-points")
    p.add_argument("--flat", action="store_true",
                   help="--reverse: one Figma collection instead of one per tier")
    p.add_argument("--quiet", action="store_true", help="do not print warnings")
    return p


def write_out(text: str, dest: Optional[str]) -> None:
    if dest:
        path = Path(dest)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        print(f"wrote {path}", file=sys.stderr)
    else:
        sys.stdout.write(text)


def report_problems(problems: Sequence[Problem], quiet: bool) -> None:
    if quiet or not problems:
        return
    by_kind: Dict[str, List[Problem]] = {}
    seen = set()
    for p in problems:
        if (p.kind, p.name, p.message) in seen:
            continue                     # --format all runs the converter per file
        seen.add((p.kind, p.name, p.message))
        by_kind.setdefault(p.kind, []).append(p)
    print("", file=sys.stderr)
    for kind, rows in by_kind.items():
        print(f"{kind} ({len(rows)}):", file=sys.stderr)
        for r in rows:
            print(f"  - {r.message}", file=sys.stderr)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    path = Path(args.path)
    try:
        if args.reverse:
            data = json.loads(path.read_bytes())
            text, problems = emit_reverse(data, collection_split=not args.flat)
            write_out(text, args.out)
            report_problems(problems, args.quiet)
            return 1 if problems else 0
        doc = load_document(path, args.shape, args.collection)
    except (OSError, ValueError, json.JSONDecodeError, KeyError) as exc:
        print(f"could not read {path}: {exc}", file=sys.stderr)
        return 2

    if not doc.variables:
        print(f"{path} parsed as `{doc.shape}` but contains no variables. Emitting an empty "
              "token file would quietly wipe a real one; pass --shape to force a shape.",
              file=sys.stderr)
        return 2

    conv = Converter(doc, color_format=args.color_format, unit=args.unit,
                     theme_diff_only=not args.full_themes)
    emitters = {"css": emit_css, "json": emit_json, "ts": emit_ts}
    if args.format == "all":
        out_dir = Path(args.out_dir or ".")
        for ext, fn in emitters.items():
            write_out(fn(conv, str(path)), str(out_dir / f"tokens.{ext}"))
    else:
        write_out(emitters[args.format](conv, str(path)), args.out)
    report_problems(conv.problems, args.quiet)
    return 1 if conv.problems else 0


if __name__ == "__main__":
    # A Windows pipe (git hook, CI, `> file`) defaults to the ANSI code page,
    # where printing →, Δ or ✓ raises UnicodeEncodeError. Consoles and
    # Claude Code already use UTF-8 and are left alone.
    for _stream in (sys.stdout, sys.stderr):
        if getattr(_stream, "encoding", "utf-8").lower() not in ("utf-8", "utf8"):
            _stream.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
