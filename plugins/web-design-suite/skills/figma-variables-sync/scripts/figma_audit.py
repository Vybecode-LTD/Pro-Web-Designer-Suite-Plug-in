#!/usr/bin/env python3
"""Audit a Figma variables export against the token contract, BEFORE anyone builds.

Dependency-free (Python 3.9+, stdlib only). Reads whatever the designer could
plausibly hand you and reports every value that is not on the closed scale, not
on a color ramp, not bound to a type role, or not legible.

The whole point is to move the "that 28px isn't a thing" argument OUT of the
build and into the twenty minutes before it. Findings are written to be pasted
to a designer, not to win an argument.

INPUT SHAPES (auto-detected, --shape to force)
----------------------------------------------
  rest      GET /v1/files/:key/variables/local  ->  {"meta": {"variables": {...},
            "variableCollections": {...}}}                    (Enterprise only)
  plugin    A Variables plugin export: {"collections": [{name, modes, variables}]}
  dtcg      W3C DTCG nested tokens:  {"space": {"6": {"$value": "24px"}}}
  records   A flat list: [{"name": ..., "type": ..., "value": ...}, ...]

Text and effect styles are read from a `styles`, `textStyles` or `effectStyles`
key at the top level, or from a second file passed with --styles.

USAGE
-----
  python scripts/figma_audit.py variables.json
  python scripts/figma_audit.py variables.json --format markdown > for-the-designer.md
  python scripts/figma_audit.py variables.json --format json | jq '.summary'
  python scripts/figma_audit.py rest-dump.json --styles file-styles.json
  python scripts/figma_audit.py variables.json --fail-on error   # looser CI gate
  python scripts/figma_audit.py variables.json --tokens src/styles/tokens.css
                                     # the project's own ramps, e.g. a client's brand

EXIT CODES
----------
  0  no findings at or above --fail-on (default: any finding at all)
  1  findings  -> the gate is red, the handoff is not done
  2  the input could not be read or understood
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

# A sibling import would otherwise leave __pycache__ inside the installed
# plugin, which is read-only as far as a project is concerned.
sys.dont_write_bytecode = True
# The reader figma_to_tokens.py uses too (LC-C3): the colour maths, as_color,
# as_px, as_ms and as_alias, FVar, FCollection, FDoc, slugify, load_document
# and attach_styles.
try:                                              # python -m scripts.figma_audit
    from .figma_common import *                   # type: ignore[import-not-found]  # noqa: F403
    from .project_config import ConfigError, ProjectTokens, read_tokens, token_sources
except ImportError:                               # python scripts/figma_audit.py
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from figma_common import *                    # type: ignore[no-redef]  # noqa: F403
    from project_config import ConfigError, ProjectTokens, read_tokens, token_sources  # type: ignore[no-redef]

# ===========================================================================
# THE CONTRACT. These tables are the closed scales from token-contract.md and
# the exact ramp values from tokens.css. They are the reason this script can
# say "that is not a thing" with a straight face. If tokens.css changes, change
# these in the same commit -- a fork here is a fork in the vocabulary.
# ===========================================================================

SPACING_PX: Tuple[float, ...] = (
    0, 1, 2, 4, 8, 12, 16, 20, 24, 32, 40, 48, 64, 80, 96, 128, 160, 192,
)
SPACING_NAME = {
    0: "--space-0", 1: "--space-px", 2: "--space-0-5", 4: "--space-1",
    8: "--space-2", 12: "--space-3", 16: "--space-4", 20: "--space-5",
    24: "--space-6", 32: "--space-8", 40: "--space-10", 48: "--space-12",
    64: "--space-16", 80: "--space-20", 96: "--space-24", 128: "--space-32",
    160: "--space-40", 192: "--space-48",
}

# Type scale. The last four are the *rendered endpoints* of the two fluid
# steps -- a designer working at 1440 sees 72 and 110, at 380 sees 44 and 56.
TYPE_PX: Tuple[float, ...] = (11, 12, 14, 16, 18, 22, 28, 35, 44, 56, 72, 110)
TYPE_NAME = {
    11: "--text-2xs", 12: "--text-xs", 14: "--text-sm", 16: "--text-base",
    18: "--text-lg", 22: "--text-xl", 28: "--text-2xl", 35: "--text-3xl",
    44: "--text-4xl (or --text-5xl at its 380px floor)",
    56: "--text-6xl at its 380px floor", 72: "--text-5xl at its 1440px ceiling",
    110: "--text-6xl at its 1440px ceiling",
}

LEADING = (1.0, 1.15, 1.3, 1.6, 1.75)
LEADING_NAME = {
    1.0: "--leading-none", 1.15: "--leading-tight", 1.3: "--leading-snug",
    1.6: "--leading-normal", 1.75: "--leading-relaxed",
}
TRACKING_EM = (-0.03, -0.015, 0.0, 0.02, 0.08)
TRACKING_NAME = {
    -0.03: "--tracking-tighter", -0.015: "--tracking-tight",
    0.0: "--tracking-normal", 0.02: "--tracking-wide", 0.08: "--tracking-caps",
}
WEIGHTS = (400, 500, 600, 700)
WEIGHT_NAME = {
    400: "--weight-regular", 500: "--weight-medium",
    600: "--weight-semibold", 700: "--weight-bold",
}
RADIUS_PX = (0, 2, 4, 8, 12, 16, 24, 9999)
RADIUS_NAME = {
    0: "--radius-none", 2: "--radius-xs", 4: "--radius-sm", 8: "--radius-md",
    12: "--radius-lg", 16: "--radius-xl", 24: "--radius-2xl", 9999: "--radius-full",
}
STROKE_PX = (1, 2)
STROKE_NAME = {1: "--stroke-default", 2: "--stroke-thick / --stroke-focus"}
DUR_MS = (80, 140, 220, 320, 480)
DUR_NAME = {
    80: "--dur-instant", 140: "--dur-fast", 220: "--dur-base",
    320: "--dur-slow", 480: "--dur-slower",
}
Z_STEPS = (0, 10, 100, 200, 300, 400, 500, 600)
Z_NAME = {
    0: "--z-base", 10: "--z-raised", 100: "--z-sticky", 200: "--z-dropdown",
    300: "--z-overlay", 400: "--z-modal", 500: "--z-toast", 600: "--z-tooltip",
}
BP_PX = (480, 768, 1024, 1280, 1536)
BP_NAME = {
    480: "--bp-sm", 768: "--bp-md", 1024: "--bp-lg",
    1280: "--bp-xl", 1536: "--bp-2xl",
}
TAP_MIN_PX = 44.0

# The ramps, transcribed from tokens.css as (L%, C, H). Keep byte-identical.
RAMPS: Dict[str, Dict[str, Tuple[float, float, float]]] = {
    "neutral": {
        "0": (100.0, 0.0, 0.0), "50": (98.2, 0.003, 75), "100": (96.0, 0.004, 75),
        "200": (92.2, 0.005, 75), "300": (86.5, 0.006, 75), "400": (71.5, 0.008, 75),
        "500": (53.5, 0.009, 75), "600": (47.5, 0.009, 75), "700": (38.5, 0.008, 75),
        "800": (28.0, 0.007, 75), "900": (19.5, 0.006, 75), "950": (13.0, 0.005, 75),
        "1000": (8.0, 0.004, 75),
    },
    "accent": {
        "50": (97.0, 0.020, 42), "100": (93.5, 0.042, 42), "200": (88.0, 0.078, 42),
        "300": (80.5, 0.118, 42), "400": (72.0, 0.158, 42), "500": (64.5, 0.188, 42),
        "600": (56.5, 0.176, 42), "700": (47.0, 0.148, 42), "800": (38.0, 0.118, 42),
        "900": (30.0, 0.090, 42), "950": (21.0, 0.062, 42),
    },
    "success": {"100": (94.0, 0.050, 152), "500": (62.0, 0.150, 152), "700": (45.0, 0.120, 152)},
    "warning": {"100": (95.5, 0.055, 85), "500": (75.0, 0.155, 85), "700": (52.0, 0.125, 85)},
    "danger": {"100": (94.5, 0.038, 25), "400": (64.0, 0.190, 25), "500": (58.0, 0.205, 25),
               "700": (45.0, 0.170, 25)},
    "info": {"100": (94.5, 0.035, 250), "500": (58.0, 0.160, 250), "700": (45.0, 0.140, 250)},
}

TYPE_ROLES = (
    "type-display", "type-h1", "type-h2", "type-h3", "type-h4",
    "type-lead", "type-body", "type-ui", "type-label", "type-code",
)
ELEVATION_ROLES = (
    "elevation-flat", "elevation-card", "elevation-raised",
    "elevation-overlay", "elevation-modal",
)
INTERACTION_ROLES = ("bg-hover", "bg-active", "bg-selected", "bg-disabled")

# Default surfaces per theme, used when the file carries no --bg-* of its own.
DEFAULT_SURFACE = {
    "light": {"bg-canvas": RAMPS["neutral"]["50"], "bg-surface": RAMPS["neutral"]["0"],
              "bg-sunken": RAMPS["neutral"]["100"], "bg-raised": RAMPS["neutral"]["0"],
              "bg-inverse": RAMPS["neutral"]["900"], "bg-accent": RAMPS["accent"]["600"]},
    "dark": {"bg-canvas": RAMPS["neutral"]["1000"], "bg-surface": RAMPS["neutral"]["950"],
             "bg-sunken": RAMPS["neutral"]["1000"], "bg-raised": RAMPS["neutral"]["900"],
             "bg-inverse": RAMPS["neutral"]["100"], "bg-accent": RAMPS["accent"]["500"]},
}
# The status fills keep their step in both themes, so an `on-*` ink with no fill
# in the file is measured on the system's fill, not skipped.
for _theme in DEFAULT_SURFACE.values():
    _theme.update({f"bg-{s}": RAMPS[s]["500"] for s in ("success", "warning", "danger")})

# A ramp step and a hex are not the same number: 8-bit quantisation costs about
# 0.002 in OKLab. 0.006 is comfortably above the rounding floor and far below a
# just-noticeable difference (~0.02), so "on the ramp" stays strict.
ON_RAMP_DE = 0.006
# Below this, the colour is a near-miss: almost certainly the ramp step with an
# eyedropper error, not a deliberate new colour. Worth saying so out loud.
NEAR_MISS_DE = 0.030

# ===========================================================================
# Colour math, on figma_common.py's conversions: identical to
# scripts/generate_color_ramp.py in web-design-studio -- same matrices, same
# transfer function. Two implementations that disagree by a rounding digit
# produce two different audit verdicts, which is worse than having no audit.
# ===========================================================================


def rgb_to_oklab(r: float, g: float, b: float) -> Tuple[float, float, float]:
    return linear_srgb_to_oklab(srgb_to_linear(r), srgb_to_linear(g), srgb_to_linear(b))


def delta_e_ok(c1: Tuple[float, float, float], c2: Tuple[float, float, float]) -> float:
    """Euclidean distance in OKLab. ~0.02 is a just-noticeable difference."""
    return math.dist(c1, c2)


def relative_luminance(r: float, g: float, b: float) -> float:
    rl, gl, bl = srgb_to_linear(r), srgb_to_linear(g), srgb_to_linear(b)
    return 0.2126 * rl + 0.7152 * gl + 0.0722 * bl


def contrast_ratio(fg: Tuple[float, float, float], bg: Tuple[float, float, float]) -> float:
    l1, l2 = relative_luminance(*fg), relative_luminance(*bg)
    if l1 < l2:
        l1, l2 = l2, l1
    return (l1 + 0.05) / (l2 + 0.05)


def composite_over(fg: Tuple[float, float, float], alpha: float,
                   bg: Tuple[float, float, float]) -> Tuple[float, float, float]:
    """Flatten a translucent colour onto a backdrop. Contrast is measured on
    what the eye receives, not on what the swatch declares."""
    return tuple(fg[i] * alpha + bg[i] * (1 - alpha) for i in range(3))  # type: ignore


# ===========================================================================
# Findings
# ===========================================================================

SEVERITY_ORDER = {"error": 3, "warn": 2, "info": 1}


@dataclass
class Finding:
    code: str
    severity: str
    collection: str
    mode: str
    name: str
    summary: str
    detail: str = ""
    suggestion: str = ""

    def to_dict(self) -> dict:
        return {
            "code": self.code, "severity": self.severity, "collection": self.collection,
            "mode": self.mode, "name": self.name, "summary": self.summary,
            "detail": self.detail, "suggestion": self.suggestion,
        }


CODE_TITLES = {
    "OFF_SCALE_SPACING": "Spacing values that are not on the scale",
    "OFF_SCALE_RADIUS": "Corner radii that are not on the scale",
    "OFF_SCALE_TYPE": "Font sizes that are not on the type scale",
    "OFF_SCALE_LEADING": "Line heights that are not on the leading scale",
    "OFF_SCALE_TRACKING": "Letter spacing that is not on the tracking scale",
    "OFF_SCALE_WEIGHT": "Font weights that are not on the weight scale",
    "OFF_SCALE_STROKE": "Stroke widths that are not on the scale",
    "OFF_SCALE_DURATION": "Durations that are not on the motion scale",
    "OFF_SCALE_Z": "Z-index values that are not on the ladder",
    "OFF_SCALE_BREAKPOINT": "Breakpoints that are not on the ladder",
    "OFF_RAMP_COLOR": "Colours that are not on a ramp",
    "CONTRAST_FAIL": "Text colours that do not meet WCAG 2.2 AA",
    "TAP_TARGET": "Interactive sizes below the 44px minimum",
    "UNMAPPED_TEXT_STYLE": "Text styles with no type role",
    "UNMAPPED_EFFECT_STYLE": "Effect styles with no elevation role",
    "TEXT_STYLE_OFF_SCALE": "Text styles built from off-scale values",
    "MISSING_DARK_MODE": "Semantic colour collections with no dark mode",
    "MISSING_STATE": "Interaction states that were never designed",
    "BROKEN_ALIAS": "Aliases that point at nothing",
    "ALIAS_CYCLE": "Aliases that point at each other",
    "TIER_VIOLATION": "Semantic roles bound to raw values instead of primitives",
    "UNSUPPORTED_VALUE": "Values this audit cannot read, so could not check",
}

# ===========================================================================
# Classifiers -- deciding which closed scale a variable is answerable to.
# Scope wins over name: a designer who scoped it told you what it is for.
# ===========================================================================

SPACING_NAME_RE = re.compile(
    r"(^|[-/])(space|spacing|gap|pad|padding|inset|gutter|margin|offset)([-/]|$)", re.I)
RADIUS_NAME_RE = re.compile(r"(^|[-/])(radius|corner|rounding)([-/]|$)", re.I)
TYPE_SIZE_RE = re.compile(r"(^|[-/])(text|fontsize|font-size|type-size|size-text)([-/]|$)", re.I)
LEADING_RE = re.compile(r"(^|[-/])(leading|line-height|lineheight)([-/]|$)", re.I)
TRACKING_RE = re.compile(r"(^|[-/])(tracking|letter-spacing|letterspacing)([-/]|$)", re.I)
WEIGHT_RE = re.compile(r"(^|[-/])(weight|font-weight|fontweight)([-/]|$)", re.I)
STROKE_RE = re.compile(r"(^|[-/])(stroke|border-width|borderwidth)([-/]|$)", re.I)
DURATION_RE = re.compile(r"(^|[-/])(dur|duration|motion|transition)([-/]|$)", re.I)
Z_RE = re.compile(r"(^|[-/])(z|z-index|zindex|layer|elevation-index)([-/]|$)", re.I)
BP_RE = re.compile(r"(^|[-/])(bp|breakpoint|screen|viewport)([-/]|$)", re.I)
TAP_RE = re.compile(
    r"(^|[-/])(tap|touch|target|hit|control|button|input|field|checkbox|radio|switch)([-/]|$)", re.I)
SIZE_RE = re.compile(r"(^|[-/])(size|height|min-height|minheight|min|h)([-/]|$)", re.I)
# Anchored at the START of the slug on purpose. `fg-muted` is a text role;
# `brand-ink-blue` is a primitive that happens to contain the word "ink", and a
# primitive has no backdrop to be measured against. Unanchored matching here is
# the single biggest source of false positives in a token linter.
TEXT_ROLE_RE = re.compile(r"^(fg|text|foreground|ink|content|label|on)([-/]|$)", re.I)
BG_ROLE_RE = re.compile(r"^(bg|background|surface|canvas|fill)([-/]|$)", re.I)
# token-contract.md's Tier-2 colour roles also include a `border-*` group
# (`--border-subtle`, `--border-default`, `--border-strong`, `--border-accent`,
# `--border-focus`) alongside `bg-*`/`fg-*` -- a semantic collection holding
# only border roles is exactly as much "Law 6" as one holding only bg/fg ones.
BORDER_ROLE_RE = re.compile(r"^(border)([-/]|$)", re.I)
DISABLED_RE = re.compile(r"disabled|inactive", re.I)
LARGE_TEXT_RE = re.compile(r"display|hero|h1|heading|title|large", re.I)


def float_kind(var: FVar) -> Optional[str]:
    """Which closed scale does this FLOAT answer to? Scope first, then name."""
    scopes = {s.upper() for s in var.scopes}
    if "CORNER_RADIUS" in scopes:
        return "radius"
    if "FONT_SIZE" in scopes:
        return "type"
    if "LINE_HEIGHT" in scopes:
        return "leading"
    if "LETTER_SPACING" in scopes:
        return "tracking"
    if "FONT_WEIGHT" in scopes:
        return "weight"
    if "STROKE_FLOAT" in scopes:
        return "stroke"
    if "GAP" in scopes or "PARAGRAPH_SPACING" in scopes or "PARAGRAPH_INDENT" in scopes:
        return "spacing"
    n = var.slug
    if "motion-travel" in n:          # a distance on the spacing scale, not a duration
        return "spacing"
    for regex, kind in (
        (RADIUS_NAME_RE, "radius"), (LEADING_RE, "leading"), (TRACKING_RE, "tracking"),
        (WEIGHT_RE, "weight"), (STROKE_RE, "stroke"), (DURATION_RE, "duration"),
        (BP_RE, "breakpoint"), (Z_RE, "z"), (TYPE_SIZE_RE, "type"),
        (SPACING_NAME_RE, "spacing"),
    ):
        if regex.search(n):
            return kind
    if "WIDTH_HEIGHT" in scopes and TAP_RE.search(n):
        return "tap"
    if TAP_RE.search(n) and SIZE_RE.search(n):
        return "tap"
    return None


def nearest(value: float, scale: Sequence[float]) -> Tuple[float, float]:
    best = min(scale, key=lambda s: abs(s - value))
    return best, value - best


def close_enough(value: float, scale: Sequence[float], tol: float = 0.01) -> bool:
    return any(abs(value - s) <= tol for s in scale)


# ===========================================================================
# The audit
# ===========================================================================


class Auditor:
    def __init__(self, doc: FDoc, *, tap_min: float = TAP_MIN_PX) -> None:
        self.doc = doc
        self.tap_min = tap_min
        self.findings: List[Finding] = []
        self.checked = 0
        self._resolved: Dict[Tuple[str, str], Optional[Tuple[float, float, float, float]]] = {}
        self._by_slug: Dict[Tuple[str, str], FVar] = {}
        for v in doc.variables:
            self._by_slug.setdefault((v.collection, v.slug), v)

    # -- alias resolution ---------------------------------------------------

    def target_of(self, alias: str) -> Optional[FVar]:
        if alias in self.doc.by_id:
            return self.doc.by_id[alias]
        slug = slugify(alias.replace(".", "/"))
        for (_, s), v in self._by_slug.items():
            if s == slug:
                return v
        return None

    def resolve_color(self, var: FVar, mode: str,
                      _seen: Optional[set] = None) -> Optional[Tuple[float, float, float, float]]:
        key = (var.var_id or var.name, mode)
        if _seen is None:
            if key in self._resolved:
                return self._resolved[key]
            _seen = set()
        if key in _seen:
            return None
        _seen.add(key)
        raw = var.values.get(mode)
        if raw is None and var.values:
            raw = var.values.get(next(iter(var.values)))
        alias = as_alias(raw)
        composed = raw.get("color") if isinstance(raw, dict) and "color" in raw else None
        out: Optional[Tuple[float, float, float, float]]
        if alias is not None or (composed is not None and as_alias(composed) is not None):
            tgt = self.target_of(alias if alias is not None else as_alias(composed))
            if tgt is None:
                out = None
            else:
                tmode = mode if mode in tgt.values else (
                    next(iter(tgt.values)) if tgt.values else mode)
                out = self.resolve_color(tgt, tmode, _seen)
                # A composed colour over an alias: the alias's colour at this opacity.
                op = raw.get("opacity") if composed is not None else None
                if out is not None and isinstance(op, (int, float)):
                    out = (out[0], out[1], out[2], out[3] * float(op) / 100.0)
        else:
            out = as_color(raw)
        if len(_seen) == 1:
            self._resolved[key] = out
        return out

    # -- checks -------------------------------------------------------------

    def run(self) -> List[Finding]:
        for path, why in self.doc.unsupported:
            self.add(code="UNSUPPORTED_VALUE", severity="error", collection="", mode="",
                     name=path, summary=f"not audited: {why}",
                     detail="A token this audit cannot read is a token nobody checked. "
                            "It is not in the generated tokens either.",
                     suggestion="split a typography token into --type-* roles, or give "
                                "the colour an sRGB `hex` fallback")
        self.check_aliases()
        for var in self.doc.variables:
            for mode in (var.values.keys() or [""]):
                raw = var.values.get(mode)
                if as_alias(raw) is not None:
                    continue                       # an alias is checked at its target
                self.checked += 1
                if var.resolved_type == "FLOAT":
                    self.check_float(var, mode, raw)
                elif var.resolved_type == "COLOR":
                    self.check_color(var, mode, raw)
        self.check_contrast()
        self.check_dark_mode()
        self.check_states()
        self.check_text_styles()
        self.check_effect_styles()
        self.findings.sort(key=lambda f: (-SEVERITY_ORDER[f.severity], f.code, f.name, f.mode))
        return self.findings

    def add(self, **kw: Any) -> None:
        self.findings.append(Finding(**kw))

    def check_aliases(self) -> None:
        for var in self.doc.variables:
            for mode, raw in var.values.items():
                alias = as_alias(raw)
                if alias is None:
                    continue
                tgt = self.target_of(alias)
                if tgt is None:
                    self.add(
                        code="BROKEN_ALIAS", severity="error", collection=var.collection,
                        mode=mode, name=var.name,
                        summary=f"aliases `{alias}`, which is not in this file",
                        detail="The variable it points at was deleted, lives in a library that "
                               "was not exported, or the export dropped it.",
                        suggestion="Re-export with the library included, or repoint the variable.",
                    )
                    continue
                # Walk the chain looking for a loop.
                seen = {(var.var_id or var.name, mode)}
                cur, cmode, depth = tgt, mode, 0
                while depth < 64:
                    ckey = (cur.var_id or cur.name, cmode if cmode in cur.values else (
                        next(iter(cur.values)) if cur.values else cmode))
                    if ckey in seen:
                        loop_at = cur.name if ckey[0] != (var.var_id or var.name) else var.name
                        self.add(
                            code="ALIAS_CYCLE", severity="error", collection=var.collection,
                            mode=mode, name=var.name,
                            summary=f"alias chain loops at `{loop_at}`",
                            detail="A cycle has no value at the end of it. In CSS this renders as "
                                   "an invalid custom property and the element falls back to "
                                   "`unset`, which usually looks like black text on black.",
                            suggestion="Break the loop: one of these two should hold a literal.",
                        )
                        break
                    seen.add(ckey)
                    nxt_raw = cur.values.get(ckey[1])
                    nxt_alias = as_alias(nxt_raw)
                    if nxt_alias is None:
                        break
                    nxt = self.target_of(nxt_alias)
                    if nxt is None:
                        break
                    cur, cmode, depth = nxt, ckey[1], depth + 1

    def check_float(self, var: FVar, mode: str, raw: Any) -> None:
        kind = float_kind(var)
        if kind is None:
            return
        if kind == "duration":
            ms = as_ms(raw)
            if ms is None or close_enough(ms, DUR_MS, 0.5):
                return
            best, delta = nearest(ms, DUR_MS)
            self.add(
                code="OFF_SCALE_DURATION", severity="warn", collection=var.collection,
                mode=mode, name=var.name, summary=f"{fmt(ms)}ms is not one of the five durations",
                detail=f"nearest is {fmt(best)}ms ({DUR_NAME[best]}), {signed(delta)}ms away",
                suggestion=f"use {DUR_NAME[best]}",
            )
            return

        px = as_px(raw)
        if px is None:
            return
        table: Dict[str, Tuple[Sequence[float], Dict[Any, str], str, str]] = {
            "spacing": (SPACING_PX, SPACING_NAME, "OFF_SCALE_SPACING", "px"),
            "radius": (RADIUS_PX, RADIUS_NAME, "OFF_SCALE_RADIUS", "px"),
            "type": (TYPE_PX, TYPE_NAME, "OFF_SCALE_TYPE", "px"),
            "stroke": (STROKE_PX, STROKE_NAME, "OFF_SCALE_STROKE", "px"),
            "z": (Z_STEPS, Z_NAME, "OFF_SCALE_Z", ""),
            "breakpoint": (BP_PX, BP_NAME, "OFF_SCALE_BREAKPOINT", "px"),
        }
        if kind in table:
            scale, names, code, unit = table[kind]
            if close_enough(px, scale):
                return
            best, delta = nearest(px, scale)
            token = names.get(int(best), names.get(best, ""))
            self.add(
                code=code, severity="error" if kind in ("spacing", "type") else "warn",
                collection=var.collection, mode=mode, name=var.name,
                summary=f"{fmt(px)}{unit} is not a step on the {kind} scale",
                detail=f"nearest legal step is {fmt(best)}{unit} ({token}), {signed(delta)}{unit} away",
                suggestion=f"use {token}" if abs(delta) <= max(4.0, best * 0.15)
                else f"use {token}, or make the case for a new step (Law 3 sign-off)",
            )
            return
        if kind == "leading":
            ratio = float(raw) if isinstance(raw, (int, float)) else px
            if ratio > 10:                      # authored in px or percent
                ratio = ratio / 100.0 if ratio <= 400 else ratio
            if close_enough(ratio, LEADING, 0.02):
                return
            best, delta = nearest(ratio, LEADING)
            self.add(
                code="OFF_SCALE_LEADING", severity="warn", collection=var.collection,
                mode=mode, name=var.name, summary=f"{fmt(ratio)} is not one of the five leadings",
                detail=f"nearest is {fmt(best)} ({LEADING_NAME[best]}), {signed(delta)} away",
                suggestion=f"use {LEADING_NAME[best]}",
            )
            return
        if kind == "tracking":
            em = float(raw) if isinstance(raw, (int, float)) else 0.0
            if abs(em) > 1:                     # authored in px against a 16px body
                em = em / 16.0
            if close_enough(em, TRACKING_EM, 0.002):
                return
            best, delta = nearest(em, TRACKING_EM)
            self.add(
                code="OFF_SCALE_TRACKING", severity="warn", collection=var.collection,
                mode=mode, name=var.name, summary=f"{em:g}em is not on the tracking scale",
                detail=f"nearest is {best:g}em ({TRACKING_NAME[best]}), {delta:+.4g}em away",
                suggestion=f"use {TRACKING_NAME[best]}",
            )
            return
        if kind == "weight":
            if close_enough(px, WEIGHTS, 0.5):
                return
            best, delta = nearest(px, WEIGHTS)
            self.add(
                code="OFF_SCALE_WEIGHT", severity="warn", collection=var.collection,
                mode=mode, name=var.name, summary=f"weight {fmt(px)} is not one of the four",
                detail=f"nearest is {fmt(best)} ({WEIGHT_NAME[best]}), {signed(delta)} away",
                suggestion=f"use {WEIGHT_NAME[best]}",
            )
            return
        if kind == "tap" and 0 < px < self.tap_min:
            self.add(
                code="TAP_TARGET", severity="error", collection=var.collection,
                mode=mode, name=var.name,
                summary=f"{fmt(px)}px is below the {fmt(self.tap_min)}px minimum touch target",
                detail="WCAG 2.2 SC 2.5.8 sets 24x24 as the floor; this system sets 44 "
                       "(`--tap-min`) because 24 is a legal minimum, not a usable one.",
                suggestion=f"raise to {fmt(self.tap_min)}px, or keep the visual size and add "
                           "invisible padding so the hit area reaches 44",
            )

    def check_color(self, var: FVar, mode: str, raw: Any) -> None:
        rgba = as_color(raw)
        if rgba is None:
            return
        r, g, b, a = rgba
        if a < 0.999:
            # Translucent overlays (--bg-hover, --bg-active) are deliberately off-ramp.
            return
        hexv = rgb_to_hex(r, g, b)
        if hexv in ramp_hex_index():
            return          # the 8-bit rendering of a ramp step IS the ramp step
        lab = rgb_to_oklab(r, g, b)
        best_name, best_de = "", float("inf")
        for ramp, steps in RAMPS.items():
            for step, oklch in steps.items():
                cand = rgb_to_oklab(*oklch_to_rgb(*oklch))
                de = delta_e_ok(lab, cand)
                if de < best_de:
                    best_de, best_name = de, f"--{ramp}-{step}"
        if best_de <= ON_RAMP_DE:
            return
        if best_de <= NEAR_MISS_DE:
            detail = (f"nearest ramp step is {best_name} (dEok {best_de:.3f}). That is below the "
                      "just-noticeable threshold, so this is almost certainly an eyedropper "
                      "error rather than a decision.")
            suggestion = f"bind to {best_name}"
            severity = "error"
        else:
            detail = (f"nearest ramp step is {best_name} (dEok {best_de:.3f}) -- far enough to be "
                      "a deliberate choice, which makes it a design-system change, not a fix.")
            suggestion = (f"either bind to {best_name}, or take it through the new-token path "
                          "(Law 3: adding a ramp step needs sign-off)")
            severity = "error"
        self.add(
            code="OFF_RAMP_COLOR", severity=severity, collection=var.collection,
            mode=mode, name=var.name, summary=f"{hexv} is not on any ramp",
            detail=detail, suggestion=suggestion,
        )

    def check_contrast(self) -> None:
        for var in self.doc.variables:
            if var.resolved_type != "COLOR":
                continue
            slug = var.slug
            scopes = {s.upper() for s in var.scopes}
            is_text = "TEXT_FILL" in scopes or (
                TEXT_ROLE_RE.search(slug) and not BG_ROLE_RE.search(slug))
            if not is_text or DISABLED_RE.search(slug):
                continue
            for mode in var.values:
                fg = self.resolve_color(var, mode)
                if fg is None:
                    continue
                threshold = 3.0 if LARGE_TEXT_RE.search(slug) else 4.5
                fails: List[Tuple[float, str, Tuple[float, float, float],
                                  Tuple[float, float, float]]] = []
                for bg_slug, bg in self.backdrops(var.collection, mode, slug):
                    flat_fg = composite_over(fg[:3], fg[3], bg) if fg[3] < 0.999 else fg[:3]
                    ratio = contrast_ratio(flat_fg, bg)
                    if ratio + 1e-9 < threshold:
                        fails.append((ratio, bg_slug, flat_fg, bg))
                if not fails:
                    continue
                # One finding per colour per mode, reporting its worst surface. A
                # designer does not need the same colour listed three times; they
                # need to know it has to move.
                ratio, bg_slug, flat_fg, bg = min(fails, key=lambda t: t[0])
                also = (f" (and {len(fails) - 1} other surface"
                        f"{'' if len(fails) == 2 else 's'})") if len(fails) > 1 else ""
                self.add(
                    code="CONTRAST_FAIL", severity="error", collection=var.collection,
                    mode=mode, name=var.name,
                    summary=f"{ratio:.2f}:1 against {bg_slug}{also} -- needs {threshold:g}:1",
                    detail=f"{rgb_to_hex(*flat_fg)} on {rgb_to_hex(*bg)} in mode `{mode}`. "
                           "WCAG 2.2 SC 1.4.3. Measured, not assumed.",
                    suggestion="move the foreground one ramp step further from the surface "
                               "(darker on light, lighter on dark) and re-measure; do not "
                               "adjust the background, which is load-bearing for every other "
                               "role sitting on it",
                )

    def backdrops(self, collection: str, mode: str,
                  fg_slug: str) -> List[Tuple[str, Tuple[float, float, float]]]:
        """Which surfaces does this foreground actually land on?"""
        theme = "dark" if re.search(r"dark|night", mode, re.I) else "light"
        if "on-accent" in fg_slug:
            wanted = ["bg-accent"]
        elif "on-inverse" in fg_slug:
            wanted = ["bg-inverse"]
        elif intent := re.search(r"on-(success|warning|danger)", fg_slug):
            wanted = ["bg-" + intent.group(1)]
        else:
            wanted = ["bg-canvas", "bg-surface", "bg-sunken"]
        out: List[Tuple[str, Tuple[float, float, float]]] = []
        for want in wanted:
            found = None
            for (col, slug), v in self._by_slug.items():
                if slug.endswith(want) and v.resolved_type == "COLOR":
                    if col == collection or found is None:
                        rgba = self.resolve_color(v, mode if mode in v.values else (
                            next(iter(v.values)) if v.values else mode))
                        if rgba is not None:
                            found = (v.slug, rgba[:3])
                            if col == collection:
                                break
            if found is None:
                oklch = DEFAULT_SURFACE[theme].get(want)
                if oklch is None:
                    continue
                found = (f"{want} (system default)", oklch_to_rgb(*oklch))
            out.append(found)
        # De-duplicate identical surfaces so one colour is not reported three times.
        seen, uniq = set(), []
        for name, rgb in out:
            key = rgb_to_hex(*rgb)
            if key not in seen:
                seen.add(key)
                uniq.append((name, rgb))
        return uniq

    def check_dark_mode(self) -> None:
        for cname, col in self.doc.collections.items():
            semantic = [v for v in self.doc.variables
                        if v.collection == cname and v.resolved_type == "COLOR"
                        and (BG_ROLE_RE.search(v.slug) or TEXT_ROLE_RE.search(v.slug)
                             or BORDER_ROLE_RE.search(v.slug))]
            if len(semantic) < 3:
                continue
            has_dark = any(re.search(r"dark|night", m, re.I) for m in col.modes)
            if not has_dark:
                self.add(
                    code="MISSING_DARK_MODE", severity="warn", collection=cname, mode="-",
                    name=cname,
                    summary=f"`{cname}` holds {len(semantic)} semantic colour roles and one mode",
                    detail="A second mode is the whole reason semantic roles exist. Without it, "
                           "dark mode arrives later as a set of component overrides, which is "
                           "the failure Law 6 exists to prevent.",
                    suggestion="add a Dark mode to this collection and re-point the roles; "
                               "primitives stay constant across modes",
                )

    def check_states(self) -> None:
        slugs = {v.slug for v in self.doc.variables}
        interactive = any(s.endswith("bg-accent") or s.endswith("bg-surface") for s in slugs)
        if not interactive:
            return
        missing = [r for r in INTERACTION_ROLES if not any(s.endswith(r) for s in slugs)]
        if missing:
            self.add(
                code="MISSING_STATE", severity="warn", collection="-", mode="-",
                name=", ".join(missing),
                summary=f"{len(missing)} of the interaction roles are not in the file",
                detail="Seven states ship per interactive component: default, hover, "
                       "focus-visible, active, disabled, loading, error. A role that does not "
                       "exist in the file gets invented during the build, by whoever gets there "
                       "first.",
                suggestion="design hover, active, selected and disabled once, as roles, not per "
                           "component",
            )

    def check_text_styles(self) -> None:
        for style in self.doc.text_styles:
            name = str(style.get("name") or style.get("key") or "(unnamed)")
            slug = slugify(name)
            mapped = any(slug.endswith(role) or slug == role.replace("type-", "")
                         for role in TYPE_ROLES)
            if not mapped:
                self.add(
                    code="UNMAPPED_TEXT_STYLE", severity="error", collection="text styles",
                    mode="-", name=name,
                    summary="no `--type-*` role answers to this style",
                    detail="The roles are: " + ", ".join(f"--{r}" for r in TYPE_ROLES) + ". "
                           "One text style per role, not one per usage -- `Card title` and "
                           "`Modal title` are the same role at two call sites.",
                    suggestion="rename to the role it plays, or delete it and use the role",
                )
            props = style.get("style") if isinstance(style.get("style"), dict) else style
            size = props.get("fontSize") if isinstance(props, dict) else None
            if isinstance(size, (int, float)) and not close_enough(float(size), TYPE_PX):
                best, delta = nearest(float(size), TYPE_PX)
                self.add(
                    code="TEXT_STYLE_OFF_SCALE", severity="error", collection="text styles",
                    mode="-", name=name,
                    summary=f"font-size {fmt(size)}px is not on the type scale",
                    detail=f"nearest is {fmt(best)}px ({TYPE_NAME[best]}), "
                           f"{signed(delta)}px away",
                    suggestion=f"use {TYPE_NAME[best]}",
                )
            if isinstance(props, dict):
                weight = props.get("fontWeight")
                if isinstance(weight, (int, float)) and not close_enough(float(weight), WEIGHTS, 0.5):
                    best, delta = nearest(float(weight), WEIGHTS)
                    self.add(
                        code="TEXT_STYLE_OFF_SCALE", severity="warn", collection="text styles",
                        mode="-", name=name,
                        summary=f"weight {fmt(weight)} is not one of the four",
                        detail=f"nearest is {fmt(best)} ({WEIGHT_NAME[best]})",
                        suggestion=f"use {WEIGHT_NAME[best]}",
                    )
                lh = props.get("lineHeightPx")
                if isinstance(lh, (int, float)) and isinstance(size, (int, float)) and size:
                    ratio = float(lh) / float(size)
                    if not close_enough(ratio, LEADING, 0.03):
                        best, _ = nearest(ratio, LEADING)
                        self.add(
                            code="OFF_SCALE_LEADING", severity="warn", collection="text styles",
                            mode="-", name=name,
                            summary=f"line-height {ratio:.3g} is not one of the five leadings",
                            detail=f"{fmt(lh)}px over {fmt(size)}px. Nearest is {best:g} "
                                   f"({LEADING_NAME[best]}).",
                            suggestion=f"use {LEADING_NAME[best]}",
                        )

    def check_effect_styles(self) -> None:
        for style in self.doc.effect_styles:
            name = str(style.get("name") or style.get("key") or "(unnamed)")
            slug = slugify(name)
            if any(slug.endswith(role) or slug == role.replace("elevation-", "")
                   for role in ELEVATION_ROLES):
                continue
            self.add(
                code="UNMAPPED_EFFECT_STYLE", severity="warn", collection="effect styles",
                mode="-", name=name,
                summary="no `--elevation-*` role answers to this style",
                detail="The roles are: " + ", ".join(f"--{r}" for r in ELEVATION_ROLES) + ". "
                       "An effect style named for its blur radius (`Shadow 12`) cannot be "
                       "re-tuned later without renaming it everywhere.",
                suggestion="rename to the role it plays (`elevation/card`), not the value it holds",
            )


_RAMP_HEX: Dict[str, str] = {}


def ramp_hex_index() -> Dict[str, str]:
    """hex -> token name, for every ramp step. A designer who eyedropped the
    swatch gets a byte-exact hex, and no float comparison should second-guess
    that. Built once, lazily."""
    if not _RAMP_HEX:
        for ramp, steps in RAMPS.items():
            for step, oklch in steps.items():
                _RAMP_HEX[rgb_to_hex(*oklch_to_rgb(*oklch))] = f"--{ramp}-{step}"
    return _RAMP_HEX


def load_project_ramps(tokens: ProjectTokens) -> Dict[str, Dict[str, Tuple[float, float, float]]]:
    """The colour ramps a project's token files declare (project_config's
    read_tokens): every Tier-1 `--<name>-<step>` whose default value is a
    literal colour, from a tokens.css or a contract.json. A client's brand
    ramp is the point — the migration seeds the accent from the brand on
    purpose — so checking a file against the studio's own orange called every
    brand colour "off ramp"."""
    ramps: Dict[str, Dict[str, Tuple[float, float, float]]] = {}
    for name, steps in tokens.ramps.items():
        for step, value in steps.items():
            rgba = as_color(value)
            if rgba is None or rgba[3] < 0.999:
                continue                     # not a colour this script reads, or translucent
            L, a, b = rgb_to_oklab(*rgba[:3])
            ramps.setdefault(name.lower(), {})[step] = (
                L * 100.0, math.hypot(a, b), math.degrees(math.atan2(b, a)) % 360)
    return ramps


def _number(value: str) -> Optional[float]:
    try:
        return float(value)
    except ValueError:
        return None


def _em(value: str) -> Optional[float]:
    return _number(value[:-2]) if value.endswith("em") and not value.endswith("rem") else _number(value)


def _px_or_clamp(value: str) -> List[float]:
    """A length, or both ends of a `clamp()`: the starter's two fluid type
    steps are on the type scale at their floor and their ceiling."""
    m = re.fullmatch(r"clamp\(\s*([^,]+),[^,]+,\s*([^,]+)\)", value.strip())
    ends = [as_px(m.group(1)), as_px(m.group(2))] if m else [as_px(value)]
    return [px for px in ends if px is not None]


# The closed scales a project's tokens may replace: the token name's first
# segment, this module's two tables, and how a value is read.
SCALES = (
    ("space", "SPACING_PX", "SPACING_NAME", lambda v: [as_px(v)]),
    ("radius", "RADIUS_PX", "RADIUS_NAME", lambda v: [as_px(v)]),
    ("text", "TYPE_PX", "TYPE_NAME", _px_or_clamp),
    ("stroke", "STROKE_PX", "STROKE_NAME", lambda v: [as_px(v)]),
    ("z", "Z_STEPS", "Z_NAME", lambda v: [_number(v)]),
    ("dur", "DUR_MS", "DUR_NAME", lambda v: [as_ms(v)]),
    ("leading", "LEADING", "LEADING_NAME", lambda v: [_number(v)]),
    ("tracking", "TRACKING_EM", "TRACKING_NAME", lambda v: [_em(v)]),
    ("weight", "WEIGHTS", "WEIGHT_NAME", lambda v: [_number(v)]),
    ("bp", "BP_PX", "BP_NAME", lambda v: [as_px(v)]),
)


def use_scales(tokens: ProjectTokens) -> List[str]:
    """Make the project's scales the ones each check compares against (P24).
    A scale the project declares, with a value this script can read,
    replaces the studio's: its steps, not both, so the scale stays closed
    (Law 3). Returns the scales replaced."""
    declared = dict(tokens.scales, bp=tokens.breakpoints)
    replaced = []
    for head, values_name, names_name, read in SCALES:
        steps: Dict[float, List[str]] = {}
        for step, raw in declared.get(head, {}).items():
            for value in read(raw):
                if value is not None:
                    steps.setdefault(value, []).append(f"--{head}-{step}")
        if steps:
            globals()[values_name] = tuple(sorted(steps))
            globals()[names_name] = {value: " / ".join(names) for value, names in steps.items()}
            replaced.append(head)
    return replaced


def use_ramps(ramps: Dict[str, Dict[str, Tuple[float, float, float]]]) -> None:
    """Make `ramps` the ones every check compares against: each named ramp
    replaces the studio's ramp of that name; the default surfaces follow."""
    RAMPS.update(ramps)
    _RAMP_HEX.clear()
    for theme, roles in (("light", {"bg-canvas": ("neutral", "50"), "bg-surface": ("neutral", "0"),
                                    "bg-sunken": ("neutral", "100"), "bg-raised": ("neutral", "0"),
                                    "bg-inverse": ("neutral", "900"), "bg-accent": ("accent", "600")}),
                         ("dark", {"bg-canvas": ("neutral", "1000"), "bg-surface": ("neutral", "950"),
                                   "bg-sunken": ("neutral", "1000"), "bg-raised": ("neutral", "900"),
                                   "bg-inverse": ("neutral", "100"), "bg-accent": ("accent", "500")})):
        for role, (ramp, step) in roles.items():
            if step in RAMPS.get(ramp, {}):
                DEFAULT_SURFACE[theme][role] = RAMPS[ramp][step]


def fmt(n: Any) -> str:
    try:
        f = float(n)
    except (TypeError, ValueError):
        return str(n)
    return f"{f:g}"


def signed(n: float) -> str:
    return f"{n:+g}"


# ===========================================================================
# Output
# ===========================================================================

BOLD, DIM, RED, YEL, CYA, GRN, OFF = (
    "\033[1m", "\033[2m", "\033[31m", "\033[33m", "\033[36m", "\033[32m", "\033[0m")
SEV_COLOR = {"error": RED, "warn": YEL, "info": CYA}


def group(findings: Sequence[Finding]) -> Dict[str, List[Finding]]:
    out: Dict[str, List[Finding]] = {}
    for f in findings:
        out.setdefault(f.code, []).append(f)
    return out


def render_report(doc: FDoc, findings: Sequence[Finding], checked: int, use_color: bool) -> str:
    c = (lambda s, col: f"{col}{s}{OFF}") if use_color else (lambda s, col: s)
    lines: List[str] = []
    lines.append(c("Figma audit", BOLD))
    lines.append(f"  shape       {doc.shape}")
    col_bits = ", ".join(
        f"{k} [{len(v.modes)} mode{'' if len(v.modes) == 1 else 's'}]"
        for k, v in doc.collections.items())
    lines.append(f"  collections {len(doc.collections)}  ({col_bits})")
    lines.append(f"  variables   {len(doc.variables)}  ({checked} concrete values checked)")
    if doc.text_styles or doc.effect_styles:
        lines.append(f"  styles      {len(doc.text_styles)} text, {len(doc.effect_styles)} effect")
    lines.append("")
    if not findings:
        lines.append(c("  Clean. Every value resolves to the contract. Build it.", GRN))
        return "\n".join(lines)
    counts = {s: sum(1 for f in findings if f.severity == s) for s in ("error", "warn", "info")}
    lines.append("  " + "  ".join(
        c(f"{counts[s]} {s}", SEV_COLOR[s]) for s in ("error", "warn", "info") if counts[s]))
    lines.append("")
    for code, rows in group(findings).items():
        lines.append(c(f"  {CODE_TITLES.get(code, code)}  ({len(rows)})", BOLD))
        for f in rows:
            tag = c(f.severity.upper().ljust(5), SEV_COLOR[f.severity])
            where = f"{f.collection} / {f.mode}" if f.mode not in ("-", "") else f.collection
            lines.append(f"    {tag} {c(f.name, BOLD)}  {c(where, DIM)}")
            lines.append(f"          {f.summary}")
            if f.detail:
                for wrapped in wrap(f.detail, 84):
                    lines.append(f"          {c(wrapped, DIM)}")
            if f.suggestion:
                lines.append(f"          {c('-> ' + f.suggestion, CYA)}")
        lines.append("")
    return "\n".join(lines)


def wrap(text: str, width: int) -> List[str]:
    out, line = [], ""
    for word in text.split():
        if line and len(line) + 1 + len(word) > width:
            out.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    if line:
        out.append(line)
    return out


def render_json(doc: FDoc, findings: Sequence[Finding], checked: int) -> str:
    return json.dumps({
        "shape": doc.shape,
        "summary": {
            "collections": len(doc.collections),
            "variables": len(doc.variables),
            "values_checked": checked,
            "text_styles": len(doc.text_styles),
            "effect_styles": len(doc.effect_styles),
            "findings": len(findings),
            "errors": sum(1 for f in findings if f.severity == "error"),
            "warnings": sum(1 for f in findings if f.severity == "warn"),
            "info": sum(1 for f in findings if f.severity == "info"),
            "clean": not findings,
        },
        "collections": {k: {"modes": v.modes, "default_mode": v.default_mode}
                        for k, v in doc.collections.items()},
        "findings": [f.to_dict() for f in findings],
    }, indent=2)


MD_INTRO = """\
# Design system check — {n} thing{s} to decide before I build

I ran the file through the token checker. This is not a list of mistakes; it is
a list of **decisions that have to be made by someone**, and it is much cheaper
to make them now than halfway through the build.

For each one there are three possible answers, and all three are fine:

1. **The design is right** — the system is missing something. I open a token
   proposal and we add it properly, with sign-off.
2. **The system is right** — it was a stray value. You nudge it to the nearest
   step and nothing else changes.
3. **Both are right** — there is a real reason for the exception. We write it
   down in `DESIGN_DECISIONS.md` and I hard-code it once, on purpose.

**Timed default — if I have not heard back by {deadline}, I take option 2** on
everything still open: nearest legal step, each one listed in the PR description
so any of them is a one-line revert. Handoff does not get to stall on a reply.
"""


def render_markdown(doc: FDoc, findings: Sequence[Finding], checked: int,
                    deadline: str = "end of day tomorrow") -> str:
    if not findings:
        return (f"# Design system check — clean\n\n"
                f"Ran {checked} value{'s' if checked != 1 else ''} from "
                f"{len(doc.collections)} collection"
                f"{'s' if len(doc.collections) != 1 else ''} against the token contract. "
                f"Everything is on the scale, on the ramp, and legible.\n\n"
                f"Nothing needed from you — starting the build.\n")
    n = len(findings)
    out = [MD_INTRO.format(n=n, s="" if n == 1 else "s", deadline=deadline), ""]
    for code, rows in group(findings).items():
        out.append(f"## {CODE_TITLES.get(code, code)}")
        out.append("")
        out.append("| Where | What I found | Nearest thing in the system |")
        out.append("|---|---|---|")
        for f in rows:
            where = f"`{f.name}`"
            if f.mode not in ("-", ""):
                where += f" <br><sub>{f.collection} / {f.mode}</sub>"
            elif f.collection not in ("-", ""):
                where += f" <br><sub>{f.collection}</sub>"
            detail = f.detail.replace("\n", " ")
            out.append(f"| {where} | {f.summary} | {f.suggestion or detail} |")
        out.append("")
        longest = max(rows, key=lambda r: len(r.detail))
        if longest.detail:
            out.append(f"> {longest.detail}")
            out.append("")
    out.append("---")
    out.append("")
    out.append("**What I need:** a yes/no per row, or just \"take the defaults\". "
               "Reply in this doc, or grab fifteen minutes and we will go through it "
               "together — that is usually faster than typing.")
    out.append("")
    out.append(f"<sub>Generated by `scripts/figma_audit.py` from a `{doc.shape}`-shaped export. "
               f"{checked} concrete values checked. Contrast measured in sRGB per WCAG 2.2; "
               f"colour distance measured as ΔE<sub>OK</sub>.</sub>")
    return "\n".join(out)


# ===========================================================================
# CLI
# ===========================================================================


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="figma_audit.py",
        description="Audit a Figma variables export against the token contract.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Exit 0 = clean, 1 = findings, 2 = could not read the input.",
    )
    p.add_argument("path", help="the exported JSON")
    p.add_argument("--styles", help="a second JSON holding text/effect styles "
                                    "(e.g. GET /v1/files/:key/styles)")
    p.add_argument("--format", choices=("report", "json", "markdown"), default="report")
    p.add_argument("--shape", choices=("rest", "plugin", "dtcg", "records"),
                   help="skip auto-detection")
    p.add_argument("--collection", default="tokens",
                   help="collection name for shapes that carry none (default: tokens)")
    p.add_argument("--fail-on", choices=("error", "warn", "info", "never"), default="info",
                   help="lowest severity that exits non-zero (default: info = any finding)")
    p.add_argument("--tap-min", type=float, default=TAP_MIN_PX,
                   help=f"minimum touch target in px (default: {TAP_MIN_PX:g})")
    p.add_argument("--deadline", default="end of day tomorrow",
                   help="the timed default's cutoff, printed in --format markdown")
    p.add_argument("--tokens", metavar="TOKENS_CSS",
                   help="the project's tokens.css, or its contract.json (extract_system "
                        "--contract): its colour ramps (any --<name>-<step> holding a literal "
                        "colour) replace the studio's ramps of the same name. Without it, the "
                        "token files a .design-suite.json lists")
    p.add_argument("--no-color", action="store_true")
    return p


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        doc = load_document(Path(args.path), args.shape, args.collection)
        if args.styles:
            extra = json.loads(Path(args.styles).read_bytes())
            attach_styles(doc, extra)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"could not read {args.path}: {exc}", file=sys.stderr)
        return 2

    if not doc.variables and not doc.text_styles and not doc.effect_styles:
        # "Clean" here would be a lie with consequences: an empty result is a
        # wrong file, a failed export or an unsupported shape, never a design
        # system with nothing wrong with it.
        print(f"{args.path} parsed as `{doc.shape}` but contains no variables and no styles. "
              "That is a wrong file or an export shape this script does not know; pass "
              "--shape to force one.", file=sys.stderr)
        return 2

    # A flag beats the config: the project's token files only without --tokens (P24).
    try:
        sources, config_path = token_sources(args.tokens)
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if sources:
        origin = ", ".join(str(s) for s in sources) + (f" (from {config_path})" if config_path else "")
        try:
            # Step by step: two files may each hold part of one ramp, and a
            # later file's step wins (Codex on #76).
            tokens = read_tokens(sources)
        except ConfigError as exc:
            print(f"could not read the project's tokens: {exc}", file=sys.stderr)
            return 2
        ramps = load_project_ramps(tokens)
        if ramps:
            use_ramps(ramps)
            doc.notes.append(f"colour ramps from {origin}: {', '.join(sorted(ramps))}")
        else:
            print(f"{origin} declares no colour ramps (--<name>-<step>: <colour>); "
                  "auditing against the studio's ramps.", file=sys.stderr)
        scales = use_scales(tokens)
        if scales:
            doc.notes.append(f"scales from {origin}: {', '.join(scales)}")

    auditor = Auditor(doc, tap_min=args.tap_min)
    findings = auditor.run()

    try:
        if args.format == "json":
            print(render_json(doc, findings, auditor.checked))
        elif args.format == "markdown":
            print(render_markdown(doc, findings, auditor.checked, args.deadline))
        else:
            use_color = sys.stdout.isatty() and not args.no_color
            print(render_report(doc, findings, auditor.checked, use_color))
    except BrokenPipeError:          # piped into `head`; not an audit failure
        try:
            sys.stdout.close()
        except BrokenPipeError:
            pass
        return 1 if findings and args.fail_on != "never" else 0

    if args.fail_on == "never":
        return 0
    floor = SEVERITY_ORDER[args.fail_on]
    return 1 if any(SEVERITY_ORDER[f.severity] >= floor for f in findings) else 0


if __name__ == "__main__":
    # A Windows pipe (git hook, CI, `> file`) defaults to the ANSI code page,
    # where printing →, Δ or ✓ raises UnicodeEncodeError. Consoles and
    # Claude Code already use UTF-8 and are left alone.
    for _stream in (sys.stdout, sys.stderr):
        if getattr(_stream, "encoding", "utf-8").lower() not in ("utf-8", "utf8"):
            _stream.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
