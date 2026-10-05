#!/usr/bin/env python3
"""
extract_system.py — read a design system out of its own source.

Documentation that is written by hand drifts. Documentation that is EXTRACTED
cannot: it is a projection of the code, and a projection of the code is correct
by construction or it is a parser bug. This script does the extraction. It emits
one normalized `system.json` describing every token, every component, every
Tier-3 socket, and — the part people actually act on — every gap between what
the system claims and what the source contains.

What it reads
-------------
  token files      tokens.css / theme.css / any file passed with --tokens
                   -> three tiers, theme re-points, references, resolved values
  component CSS    the five-part component shape (socket block, structure,
                   variants, states, parts) -> the Tier-3 public API
  component TS/TSX props, defaults and the JSDoc that carries the WHY

What it emits
-------------
  system.json      deterministic (sorted, no timestamps) so `build_docs.py
                   --check` can diff two of them and get a real answer

Usage
-----
    python -m scripts.extract_system styles/ src/components/ --out docs/system.json
    python -m scripts.extract_system --tokens styles/tokens.css \\
        --components "src/components/*.css" --props "src/components/*.tsx" \\
        --prose docs/prose --out docs/system.json
    python -m scripts.extract_system styles/ src/components/ --out build/system.json --report

The committed baseline (docs/system.json) and every CI run must read the same
source, or an unchanged repo reports drift.

Contrast
--------
The contrast column is computed with the OKLab/WCAG functions from the
`web-design-studio` skill's `generate_color_ramp.py`. When that file is
reachable it is imported and used directly; otherwise the byte-identical
vendored copy below runs instead. `--check-color-impl PATH` proves the two
agree, so this skill can ship standalone without the two ever disagreeing.

Exit codes: 0 extracted · 1 --strict and gaps were found · 2 bad invocation.
"""

from __future__ import annotations

import argparse
import glob as globmod
import importlib.util
import json
import math
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Sequence, Tuple

SCHEMA = "design-system-docs/system/1"

# ===========================================================================
# 1. COLOR MATH
#
# Vendored verbatim from web-design-studio/scripts/generate_color_ramp.py.
# Two implementations of WCAG contrast in one suite is how a docs page and a
# ramp generator end up reporting 4.48 and 4.52 for the same pair, and how a
# reviewer learns to trust neither. `--check-color-impl` asserts they agree.
# ===========================================================================


class ColorError(ValueError):
    """Raised when a color string cannot be parsed."""


def srgb_to_linear(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def linear_to_srgb(c: float) -> float:
    return 12.92 * c if c <= 0.0031308 else 1.055 * (c ** (1 / 2.4)) - 0.055


def linear_srgb_to_oklab(r: float, g: float, b: float) -> Tuple[float, float, float]:
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l_, m_, s_ = (
        math.copysign(abs(l) ** (1 / 3), l),
        math.copysign(abs(m) ** (1 / 3), m),
        math.copysign(abs(s) ** (1 / 3), s),
    )
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


def oklch_to_oklab(L: float, C: float, H: float) -> Tuple[float, float, float]:
    h = math.radians(H)
    return (L, C * math.cos(h), C * math.sin(h))


def oklch_to_linear_rgb(L: float, C: float, H: float) -> Tuple[float, float, float]:
    return oklab_to_linear_srgb(*oklch_to_oklab(L, C, H))


def oklch_to_rgb(L: float, C: float, H: float) -> Tuple[float, float, float]:
    r, g, b = oklch_to_linear_rgb(L, C, H)
    return (linear_to_srgb(r), linear_to_srgb(g), linear_to_srgb(b))


def clamp_rgb(rgb: Tuple[float, float, float]) -> Tuple[float, float, float]:
    return tuple(max(0.0, min(1.0, v)) for v in rgb)  # type: ignore[return-value]


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
    return contrast_ratio_rgb(clamp_rgb(oklch_to_rgb(*a)), clamp_rgb(oklch_to_rgb(*b)))


_HEX_RE = re.compile(r"^#?([0-9a-fA-F]{3}|[0-9a-fA-F]{4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")
_OKLCH_RE = re.compile(
    r"^oklch\(\s*([0-9.]+)\s*(%?)\s*[, ]\s*([0-9.]+)\s*[, ]\s*(-?[0-9.]+)\s*(deg)?\s*\)$",
    re.IGNORECASE,
)


def hex_to_rgb(hex_str: str) -> Tuple[float, float, float]:
    m = _HEX_RE.match(hex_str.strip())
    if not m:
        raise ColorError(f"{hex_str!r} is not a hex color.")
    h = m.group(1)
    if len(h) in (3, 4):
        h = "".join(ch * 2 for ch in h)
    return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0)


def rgb_to_oklab(r: float, g: float, b: float) -> Tuple[float, float, float]:
    return linear_srgb_to_oklab(srgb_to_linear(r), srgb_to_linear(g), srgb_to_linear(b))


def oklab_to_oklch(L: float, a: float, b: float) -> Tuple[float, float, float]:
    C = math.hypot(a, b)
    H = math.degrees(math.atan2(b, a)) % 360.0
    return (L, C, H)


def hex_to_oklch(hex_str: str) -> Tuple[float, float, float]:
    return oklab_to_oklch(*rgb_to_oklab(*hex_to_rgb(hex_str)))


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
            L = L / 100.0
        C = float(raw_c)
        H = float(raw_h) % 360.0
        if not (0.0 <= L <= 1.0):
            raise ColorError(f"Lightness out of range in {value!r}.")
        if C < 0:
            raise ColorError(f"Negative chroma in {value!r}.")
        return (L, C, H)
    if _HEX_RE.match(text):
        return hex_to_oklch(text)
    raise ColorError(f"Cannot parse {value!r} as a color.")


def rgb_to_hex(r: float, g: float, b: float) -> str:
    def ch(v: float) -> int:
        return max(0, min(255, int(round(v * 255))))

    return "#{:02x}{:02x}{:02x}".format(ch(r), ch(g), ch(b))


#: Which implementation is live. Set by `use_upstream_color_impl`.
COLOR_IMPL = "vendored"

#: Probe pairs used to prove the vendored copy and the upstream module agree.
COLOR_PROBES: Tuple[Tuple[str, str], ...] = (
    ("oklch(19.5% 0.006 75)", "oklch(98.2% 0.003 75)"),
    ("oklch(47.5% 0.009 75)", "oklch(100% 0 0)"),
    ("oklch(53.5% 0.009 75)", "oklch(96.0% 0.004 75)"),
    ("oklch(100% 0 0)", "oklch(56.5% 0.176 42)"),
    ("oklch(96.0% 0.004 75)", "oklch(8.0% 0.004 75)"),
    ("#ffffff", "#e8440a"),
)


def _find_upstream(explicit: Optional[str]) -> Optional[Path]:
    """Locate web-design-studio's generate_color_ramp.py, if it is reachable."""
    if explicit:
        p = Path(explicit).expanduser()
        return p if p.is_file() else None
    here = Path(__file__).resolve()
    candidates = [
        here.parent.parent.parent / "web-design-studio" / "scripts" / "generate_color_ramp.py",
        here.parent / "generate_color_ramp.py",
    ]
    for c in candidates:
        if c.is_file():
            return c
    return None


def use_upstream_color_impl(path: Path, *, verify: bool = True) -> List[str]:
    """Bind this module's color functions to the studio's own implementation.

    Returns a list of disagreement messages (empty when the two agree). The
    point is not defensiveness; it is that a docs page quoting 4.48:1 and a ramp
    generator quoting 4.52:1 for the same pair destroys trust in both.
    """
    global COLOR_IMPL, parse_color, contrast_ratio_oklch, oklch_to_rgb, rgb_to_hex
    spec = importlib.util.spec_from_file_location("_wds_color_ramp", str(path))
    if spec is None or spec.loader is None:
        raise ColorError(f"Cannot import a color implementation from {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    problems: List[str] = []
    if verify:
        for fg, bg in COLOR_PROBES:
            mine = contrast_ratio_oklch(parse_color(fg), parse_color(bg))
            theirs = mod.contrast_ratio_oklch(mod.parse_color(fg), mod.parse_color(bg))
            if abs(mine - theirs) > 1e-9:
                problems.append(f"{fg} on {bg}: vendored {mine:.6f} vs upstream {theirs:.6f}")

    parse_color = mod.parse_color              # type: ignore[assignment]
    contrast_ratio_oklch = mod.contrast_ratio_oklch  # type: ignore[assignment]
    oklch_to_rgb = mod.oklch_to_rgb            # type: ignore[assignment]
    rgb_to_hex = mod.rgb_to_hex                # type: ignore[assignment]
    COLOR_IMPL = f"upstream:{path.name}"
    return problems


# ===========================================================================
# 2. THE CSS SCANNER
#
# Tolerant by design. A docs extractor that refuses to read a file because of
# one construct it does not model is a docs extractor nobody runs twice.
# ===========================================================================


@dataclass
class Decl:
    prop: str
    value: str
    line: int
    selectors: Tuple[str, ...]     # the nested selector chain, outermost first
    at_rules: Tuple[str, ...]      # the enclosing at-rule preludes
    note: str = ""                 # adjacent comment, cleaned


@dataclass
class Rule:
    selector: str
    line: int
    selectors: Tuple[str, ...]
    at_rules: Tuple[str, ...]
    decls: List[Decl] = field(default_factory=list)
    note: str = ""


_BANNER = re.compile(r"^[\s*=\-_/]*$")


def clean_comment(body: str) -> str:
    """Strip comment furniture and banner rules, keep the prose."""
    lines = []
    for raw in body.splitlines():
        s = raw.strip().lstrip("*").strip()
        s = re.sub(r"^[-=]{3,}$", "", s)
        s = re.sub(r"[-=]{6,}", "", s)
        if _BANNER.match(s):
            continue
        lines.append(s)
    out = " ".join(x for x in lines if x).strip()
    return re.sub(r"\s{2,}", " ", out)


class CssFile:
    """A parsed stylesheet: rules, declarations and the comments attached to them."""

    def __init__(self, path: str, text: str) -> None:
        self.path = path
        self.text = text
        self.rules: List[Rule] = []
        self.decls: List[Decl] = []
        self.at_statements: List[Tuple[str, int]] = []
        self._parse()

    # -- parsing ----------------------------------------------------------
    def _parse(self) -> None:
        text = self.text
        n = len(text)
        i = 0
        line = 1
        buf: List[str] = []
        buf_line = 1
        sel_stack: List[str] = []
        at_stack: List[str] = []
        rule_stack: List[Optional[Rule]] = []
        # comment bookkeeping: end line -> cleaned body, and same-line trailing
        pending: Dict[int, str] = {}
        trailing: Dict[int, str] = {}

        def flush_decl() -> None:
            nonlocal buf, buf_line
            raw = "".join(buf).strip()
            buf = []
            if not raw:
                return
            if raw.startswith("@"):
                self.at_statements.append((raw, buf_line))
                return
            idx = _split_colon(raw)
            if idx < 0:
                return
            prop = raw[:idx].strip()
            value = " ".join(raw[idx + 1:].split())
            if not prop:
                return
            d = Decl(prop, value, buf_line, tuple(sel_stack), tuple(at_stack))
            self.decls.append(d)
            if rule_stack and rule_stack[-1] is not None:
                rule_stack[-1].decls.append(d)

        while i < n:
            c = text[i]
            if c == "/" and i + 1 < n and text[i + 1] == "*":
                j = text.find("*/", i + 2)
                j = n if j < 0 else j + 2
                body = text[i:j]
                start_line = line
                end_line = line + body.count("\n")
                cleaned = clean_comment(body[2:-2] if body.endswith("*/") else body[2:])
                if cleaned:
                    before = text.rfind("\n", 0, i)
                    prefix = text[before + 1:i].strip()
                    # Something on the line already? Then this comment annotates
                    # THAT line. Otherwise it annotates whatever comes next.
                    if prefix:
                        trailing[start_line] = cleaned
                    else:
                        pending[end_line] = cleaned
                line = end_line
                i = j
                continue
            if c in "\"'":
                j = i + 1
                while j < n:
                    if text[j] == "\\":
                        j += 2
                        continue
                    if text[j] == c:
                        break
                    j += 1
                chunk = text[i:min(j + 1, n)]
                buf.append(chunk)
                line += chunk.count("\n")
                i = min(j + 1, n)
                continue
            if c == "(":
                depth = 0
                j = i
                while j < n:
                    if text[j] == "(":
                        depth += 1
                    elif text[j] == ")":
                        depth -= 1
                        if depth == 0:
                            j += 1
                            break
                    elif text[j] in "\"'":
                        q = text[j]
                        j += 1
                        while j < n and text[j] != q:
                            j += 2 if text[j] == "\\" else 1
                    j += 1
                chunk = text[i:j]
                if not "".join(buf).strip():
                    buf_line = line
                buf.append(chunk)
                line += chunk.count("\n")
                i = j
                continue
            if c == "{":
                prelude = " ".join("".join(buf).split())
                buf = []
                if prelude.startswith("@"):
                    at_stack.append(prelude)
                    rule_stack.append(None)
                else:
                    sel_stack.append(prelude)
                    r = Rule(prelude, line, tuple(sel_stack), tuple(at_stack))
                    self.rules.append(r)
                    rule_stack.append(r)
                i += 1
                continue
            if c == "}":
                flush_decl()
                frame = rule_stack.pop() if rule_stack else None
                if frame is None:
                    if at_stack:
                        at_stack.pop()
                else:
                    if sel_stack:
                        sel_stack.pop()
                i += 1
                continue
            if c == ";":
                flush_decl()
                i += 1
                continue
            if c == "\n":
                line += 1
                buf.append(c)
                i += 1
                continue
            if not "".join(buf).strip() and not c.isspace():
                buf_line = line
            buf.append(c)
            i += 1
        flush_decl()

        # Notes are attached in a second pass, because a trailing comment is
        # read AFTER the `;` that already flushed the declaration it describes.
        self.trailing_notes = trailing
        self.leading_notes = pending
        for d in self.decls:
            d.note = trailing.get(d.line, "") or pending.get(d.line - 1, "")
        for r in self.rules:
            r.note = pending.get(r.line - 1, "")

    def note_for_line(self, line: int) -> str:
        return self.trailing_notes.get(line, "") or self.leading_notes.get(line - 1, "")


def _split_colon(raw: str) -> int:
    depth = 0
    for idx, ch in enumerate(raw):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif ch == ":" and depth == 0:
            return idx
    return -1


# ===========================================================================
# 3. THE TIER TABLE
#
# Straight out of token-contract.md. The tier is a property of the NAME'S
# MEANING, not of its first word — which is why the exception list exists and
# why a purely prefix-based classifier gets --space-section wrong.
# ===========================================================================

TIER2_EXCEPTIONS = {
    "--space-section", "--space-subsection", "--space-block",
    "--space-fluid-sm", "--space-fluid-md", "--space-fluid-lg", "--space-fluid-xl",
}

# Tier-1 name prefixes. --radius/--stroke/--z/--bp/--font/--measure/--width/
# --tap-min have no Tier-2 equivalent: components read them directly and that
# is correct (token-contract.md, "Tier-2 roles").
TIER1_PREFIXES: Tuple[Tuple[str, str], ...] = (
    ("--space-", "raw step on the closed 4px scale"),
    ("--density", "the density dial itself"),
    ("--neutral-", "raw ramp step"),
    ("--accent-", "raw ramp step"),
    ("--success-", "raw ramp step"),
    ("--warning-", "raw ramp step"),
    ("--danger-", "raw ramp step"),
    ("--info-", "raw ramp step"),
    ("--text-", "raw step on the type scale"),
    ("--leading-", "raw leading value"),
    ("--tracking-", "raw tracking value"),
    ("--weight-", "raw weight value"),
    ("--font-", "font stack; no Tier-2 equivalent"),
    ("--radius-", "primitive with no Tier-2 equivalent"),
    ("--stroke-", "primitive with no Tier-2 equivalent"),
    ("--shadow-", "raw shadow; --elevation-* is the role"),
    ("--dur-", "raw duration; --motion-* is the role pair"),
    ("--ease-", "raw easing; --motion-* is the role pair"),
    ("--bp-", "primitive with no Tier-2 equivalent"),
    ("--z-", "primitive with no Tier-2 equivalent"),
    ("--measure-", "primitive with no Tier-2 equivalent"),
    ("--width-", "primitive with no Tier-2 equivalent"),
    ("--tap-", "primitive with no Tier-2 equivalent"),
    ("--grid-columns", "primitive with no Tier-2 equivalent"),
)

TIER2_PREFIXES: Tuple[Tuple[str, str], ...] = (
    ("--gap-", "proximity role"),
    ("--pad-", "inset role"),
    ("--gutter-", "page rhythm role"),
    ("--bg-", "surface / interaction role"),
    ("--fg-", "foreground role"),
    ("--border-", "border role"),
    ("--type-", "type role"),
    ("--elevation-", "elevation role"),
    ("--motion-", "motion role pair"),
)

GROUPS: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("spacing", ("--space-", "--gap-", "--pad-", "--gutter-", "--density", "--tap-")),
    ("typography", ("--font-", "--text-", "--leading-", "--tracking-", "--weight-", "--type-", "--measure-")),
    ("color", ("--neutral-", "--accent-", "--success-", "--warning-", "--danger-",
               "--info-", "--bg-", "--fg-", "--border-")),
    ("shape", ("--radius-", "--stroke-")),
    ("elevation", ("--shadow-", "--elevation-")),
    ("motion", ("--dur-", "--ease-", "--motion-")),
    ("layout", ("--bp-", "--z-", "--width-", "--grid-")),
)


def group_of(name: str) -> str:
    for group, prefixes in GROUPS:
        if any(name.startswith(p) for p in prefixes):
            return group
    return "other"


def classify_tier(name: str, value: str, refs: Sequence[str]) -> Tuple[int, str]:
    """Return (tier, why). Two signals: the name, then what the value references."""
    if name in TIER2_EXCEPTIONS:
        return 2, ("contract exception list — page rhythm lives in the --space-* namespace "
                   "but the tier is a property of the name's MEANING, not its first word")
    for pfx, why in TIER2_PREFIXES:
        if name.startswith(pfx):
            return 2, f"name — {pfx}* → {why}"
    for pfx, why in TIER1_PREFIXES:
        if name.startswith(pfx):
            label = pfx if pfx.endswith("-") else pfx + " "
            return 1, f"name — {label.strip()}{'*' if pfx.endswith('-') else ''} → {why}"
    # No name match: fall back to what it references. A property whose value is
    # a literal is a primitive; one that re-points another token is a role.
    if refs:
        return 2, "structure — re-points another token, so it is a role, not a raw value"
    return 1, "structure — a literal value under a name the contract does not list"


# ===========================================================================
# 4. THE STATIC RESOLVER
#
# What a browser does with var() and calc() at layout time, done here without a
# browser — and, where that is impossible, SAID so. An honest "viewport
# dependent, 64px..144px" is worth more in a doc than a confident wrong number.
# ===========================================================================

VAR_CALL = re.compile(r"var\(\s*(--[\w-]+)\s*(?:,([^()]*(?:\([^()]*\)[^()]*)*))?\)")
VAR_REF = re.compile(r"var\(\s*(--[\w-]+)")
NUM_UNIT = re.compile(r"^([+-]?(?:\d+\.?\d*|\.\d+))([a-z%]*)$", re.I)

ABSOLUTE_UNITS = {"px": 1.0, "pt": 96 / 72, "pc": 16.0, "in": 96.0, "cm": 96 / 2.54,
                  "mm": 9.6 / 2.54, "q": 96 / 2.54 / 40}
#: Units that cannot be resolved without a viewport, a container or an element.
DYNAMIC_UNITS = {"vw", "vh", "vmin", "vmax", "svw", "svh", "lvw", "lvh", "dvw", "dvh",
                 "%", "ch", "ex", "em", "cqw", "cqh", "cqi", "cqb", "cqmin", "cqmax", "fr"}


UNIT_REASONS = {
    "em": "relative to the element's own font-size",
    "ch": "relative to the rendered font's `0` advance",
    "ex": "relative to the rendered font's x-height",
    "%": "relative to the containing block",
    "fr": "a grid fraction, resolved at layout",
}


def unit_reason(unit: str) -> str:
    if unit in UNIT_REASONS:
        return UNIT_REASONS[unit]
    if unit.startswith("cq"):
        return "relative to a query container's size"
    return "relative to the viewport"


class Unresolvable(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


Quantity = Dict[str, float]   # unit -> coefficient; "" is a bare number


def _q(number: float, unit: str, root_px: float) -> Quantity:
    unit = unit.lower()
    if unit == "":
        return {"": number}
    if unit == "rem":
        return {"px": number * root_px}
    if unit in ABSOLUTE_UNITS:
        return {"px": number * ABSOLUTE_UNITS[unit]}
    if unit in DYNAMIC_UNITS:
        return {unit: number}
    raise Unresolvable(f"unknown unit `{unit}`")


def _add(a: Quantity, b: Quantity, sign: float = 1.0) -> Quantity:
    out = dict(a)
    for k, v in b.items():
        out[k] = out.get(k, 0.0) + sign * v
    return {k: v for k, v in out.items() if abs(v) > 1e-12} or {"": 0.0}


def _mul(a: Quantity, b: Quantity) -> Quantity:
    if set(a) == {""}:
        return {k: v * a[""] for k, v in b.items()}
    if set(b) == {""}:
        return {k: v * b[""] for k, v in a.items()}
    raise Unresolvable("calc() multiplies two dimensioned values")


def _div(a: Quantity, b: Quantity) -> Quantity:
    if set(b) != {""}:
        raise Unresolvable("calc() divides by a dimensioned value")
    if abs(b[""]) < 1e-12:
        raise Unresolvable("calc() divides by zero")
    return {k: v / b[""] for k, v in a.items()}


class _Expr:
    """A recursive-descent evaluator for the calc() subset that appears in tokens."""

    def __init__(self, text: str, root_px: float) -> None:
        self.toks = re.findall(r"[a-zA-Z_-][\w.%-]*\(|[()+*/]|(?<=[\d\w%) ])-(?=[ (])|"
                               r"[+-]?(?:\d+\.?\d*|\.\d+)[a-z%]*|,|-", text, re.I)
        self.i = 0
        self.root_px = root_px

    def peek(self) -> Optional[str]:
        return self.toks[self.i] if self.i < len(self.toks) else None

    def next(self) -> str:
        t = self.toks[self.i]
        self.i += 1
        return t

    def parse(self) -> Quantity:
        v = self.sum()
        if self.peek() is not None:
            raise Unresolvable(f"unparsed trailing `{self.peek()}`")
        return v

    def sum(self) -> Quantity:
        v = self.product()
        while self.peek() in ("+", "-"):
            op = self.next()
            v = _add(v, self.product(), 1.0 if op == "+" else -1.0)
        return v

    def product(self) -> Quantity:
        v = self.atom()
        while self.peek() in ("*", "/"):
            op = self.next()
            v = _mul(v, self.atom()) if op == "*" else _div(v, self.atom())
        return v

    def atom(self) -> Quantity:
        t = self.peek()
        if t is None:
            raise Unresolvable("truncated expression")
        if t == "(":
            self.next()
            v = self.sum()
            if self.peek() == ")":
                self.next()
            return v
        if t.endswith("("):
            fn = self.next()[:-1].lower()
            args: List[Quantity] = []
            cur_start = self.i
            depth = 1
            pieces: List[List[str]] = [[]]
            while self.i < len(self.toks):
                tok = self.next()
                if tok.endswith("(") or tok == "(":
                    depth += 1
                elif tok == ")":
                    depth -= 1
                    if depth == 0:
                        break
                if depth == 1 and tok == ",":
                    pieces.append([])
                    continue
                pieces[-1].append(tok)
            for piece in pieces:
                sub = _Expr(" ".join(piece), self.root_px)
                sub.toks = piece
                args.append(sub.sum())
            if fn == "calc":
                return args[0]
            if fn in ("min", "max"):
                scalars = [_to_px(a) for a in args]
                return {"px": (min(scalars) if fn == "min" else max(scalars))}
            if fn == "clamp":
                raise Unresolvable("nested clamp()")
            raise Unresolvable(f"unsupported function `{fn}()`")
        t = self.next()
        if t in ("+", "-"):
            return _mul({"": -1.0 if t == "-" else 1.0}, self.atom())
        m = NUM_UNIT.match(t)
        if not m:
            raise Unresolvable(f"not a number: `{t}`")
        return _q(float(m.group(1)), m.group(2), self.root_px)


def _to_px(q: Quantity) -> float:
    if set(q) - {"px", ""} or (set(q) == {""} and q[""] != 0):
        raise Unresolvable("value is not a pure length")
    return q.get("px", 0.0)


def fmt_px(px: float) -> str:
    if abs(px - round(px)) < 1e-6:
        return f"{int(round(px))}px"
    return f"{px:.3f}".rstrip("0").rstrip(".") + "px"


@dataclass
class Resolved:
    status: str                 # exact | range | literal | unresolved
    value: str = ""             # the substituted text, always populated
    px: Optional[float] = None
    min_px: Optional[float] = None
    max_px: Optional[float] = None
    reason: str = ""            # why it is not `exact`
    kind: str = "other"         # length | color | shadow | font | time | easing | number
    hex: str = ""               # for colors
    alpha: float = 1.0
    parts: Dict[str, str] = field(default_factory=dict)   # for the font shorthand

    def display(self) -> str:
        if self.status == "exact" and self.px is not None:
            return fmt_px(self.px)
        if self.status == "range" and self.min_px is not None:
            return f"{fmt_px(self.min_px)} … {fmt_px(self.max_px or self.min_px)}"
        if self.kind == "color" and self.hex:
            return self.hex if self.alpha >= 1.0 else f"{self.hex} @ {self.alpha:.2f}α"
        return self.value


CLAMP_RE = re.compile(r"^clamp\((.*)\)$", re.S | re.I)
OKLCH_ALPHA = re.compile(
    r"^oklch\(\s*([\d.]+%?)\s+([\d.]+)\s+(-?[\d.]+)(?:deg)?\s*(?:/\s*([\d.]+%?)\s*)?\)$", re.I)


def split_args(text: str) -> List[str]:
    out, depth, cur = [], 0, []
    for ch in text:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            out.append("".join(cur).strip())
            cur = []
            continue
        cur.append(ch)
    if cur:
        out.append("".join(cur).strip())
    return out


class Resolver:
    """Resolves var() chains inside one cascade context (a theme, a density)."""

    def __init__(self, env: Dict[str, str], root_px: float = 16.0) -> None:
        self.env = env
        self.root_px = root_px
        self._cache: Dict[str, Resolved] = {}

    # -- substitution -----------------------------------------------------
    def substitute(self, value: str, seen: Optional[set] = None, depth: int = 0) -> str:
        seen = seen or set()
        if depth > 24:
            raise Unresolvable("var() chain deeper than 24 levels (a cycle?)")
        out = value
        for _ in range(24):
            m = VAR_CALL.search(out)
            if not m:
                break
            name, fallback = m.group(1), (m.group(2) or "").strip()
            if name in seen:
                raise Unresolvable(f"circular reference through {name}")
            if name in self.env:
                repl = self.substitute(self.env[name], seen | {name}, depth + 1)
            elif fallback:
                repl = self.substitute(fallback, seen | {name}, depth + 1)
            else:
                raise Unresolvable(f"{name} is referenced but never declared")
            out = out[:m.start()] + repl + out[m.end():]
        return " ".join(out.split())

    # -- evaluation -------------------------------------------------------
    def resolve(self, name_or_value: str, *, is_name: bool = False) -> Resolved:
        if is_name:
            if name_or_value in self._cache:
                return self._cache[name_or_value]
            raw = self.env.get(name_or_value)
            if raw is None:
                return Resolved("unresolved", name_or_value,
                                reason=f"{name_or_value} is not declared in this context")
            r = self.resolve_value(raw, seen={name_or_value})
            self._cache[name_or_value] = r
            return r
        return self.resolve_value(name_or_value)

    def resolve_value(self, raw: str, seen: Optional[set] = None) -> Resolved:
        try:
            text = self.substitute(raw, seen or set())
        except Unresolvable as exc:
            return Resolved("unresolved", raw, reason=exc.reason, kind=guess_kind(raw))
        kind = guess_kind(text)

        # color -----------------------------------------------------------
        m = OKLCH_ALPHA.match(text)
        if m:
            alpha_raw = m.group(4)
            alpha = 1.0
            if alpha_raw:
                alpha = float(alpha_raw[:-1]) / 100 if alpha_raw.endswith("%") else float(alpha_raw)
            try:
                lch = parse_color(f"oklch({m.group(1)} {m.group(2)} {m.group(3)})")
                hexval = rgb_to_hex(*clamp_rgb(oklch_to_rgb(*lch)))
            except ColorError as exc:
                return Resolved("unresolved", text, reason=str(exc), kind="color")
            return Resolved("exact", text, kind="color", hex=hexval, alpha=alpha)
        if _HEX_RE.match(text.strip()):
            try:
                lch = parse_color(text.strip())
                return Resolved("exact", text, kind="color",
                                hex=rgb_to_hex(*clamp_rgb(oklch_to_rgb(*lch))))
            except ColorError as exc:
                return Resolved("unresolved", text, reason=str(exc), kind="color")

        # the `font` shorthand that every --type-* role is -------------------
        if kind == "font":
            parts = parse_font_shorthand(text)
            if parts:
                parts["size_px"] = self.resolve_value(parts["size"]).display()
                return Resolved("literal", text, kind="font", parts=parts)

        # clamp() ----------------------------------------------------------
        cm = CLAMP_RE.match(text.strip())
        if cm:
            args = split_args(cm.group(1))
            if len(args) == 3:
                try:
                    lo = _to_px(_Expr(args[0], self.root_px).parse())
                    hi = _to_px(_Expr(args[2], self.root_px).parse())
                    return Resolved("range", text, min_px=lo, max_px=hi, kind="length",
                                    reason="clamp(): the preferred term is viewport-dependent")
                except Unresolvable as exc:
                    return Resolved("unresolved", text, reason=exc.reason, kind="length")
            return Resolved("unresolved", text, reason="clamp() with an unexpected arity",
                            kind="length")

        # numbers and lengths ----------------------------------------------
        if kind in ("length", "number"):
            try:
                q = _Expr(text, self.root_px).parse()
            except (Unresolvable, IndexError) as exc:
                reason = exc.reason if isinstance(exc, Unresolvable) else "malformed expression"
                return Resolved("unresolved", text, reason=reason, kind=kind)
            dyn = sorted(set(q) & DYNAMIC_UNITS)
            if dyn:
                return Resolved("unresolved", text, kind=kind,
                                reason=f"depends on {', '.join(dyn)} — "
                                       f"{unit_reason(dyn[0])}, which source cannot supply")
            if set(q) == {""}:
                return Resolved("exact", text, px=None, kind="number")
            try:
                return Resolved("exact", text, px=_to_px(q), kind="length")
            except Unresolvable as exc:
                return Resolved("unresolved", text, reason=exc.reason, kind=kind)

        return Resolved("literal", self.fold_calc(text), kind=kind)

    def fold_calc(self, text: str) -> str:
        """Evaluate calc() that is embedded in a larger literal, e.g. the second
        ring of --shadow-focus. A doc that prints `calc(2px * 2)` has told the
        reader nothing they could not read in the source themselves."""
        def sub(m: "re.Match[str]") -> str:
            try:
                return fmt_px(_to_px(_Expr(m.group(0), self.root_px).parse()))
            except (Unresolvable, IndexError, ValueError):
                return m.group(0)
        return CALC_CALL.sub(sub, text)


TIME_RE = re.compile(r"^[\d.]+m?s$", re.I)
NUMBER_RE = re.compile(r"^[+-]?[\d.]+$")


COLOR_FUNC = re.compile(r"\b(oklch|oklab|rgba?|hsla?|lab|lch|hwb|color)\s*\(", re.I)
CALC_CALL = re.compile(r"\bcalc\((?:[^()]|\([^()]*\))*\)", re.I)


def parse_font_shorthand(text: str) -> Optional[Dict[str, str]]:
    """Split `600 2.1875rem/1.15 "Geist Sans", …` into its four parts.

    Depth-aware, because after var() substitution the size is frequently a
    whole `clamp(…)` with spaces and commas in it — which is exactly the case a
    naive `[^\\s/]+` for the size gets wrong, and exactly the case --type-display
    hits in the canonical token file.
    """
    s = text.strip()
    m = re.match(r"^(\d{3}|bold|normal|lighter|bolder)\s+", s)
    if not m:
        return None
    weight = m.group(1)
    rest = s[m.end():]
    depth = 0
    slash = -1
    for i, ch in enumerate(rest):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif ch == "/" and depth == 0:
            slash = i
            break
    if slash < 0:
        return None
    size = rest[:slash].strip()
    after = rest[slash + 1:].lstrip()
    depth = 0
    cut = -1
    for i, ch in enumerate(after):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif ch.isspace() and depth == 0:
            cut = i
            break
    if cut < 0:
        return None
    return {"weight": weight, "size": size,
            "leading": after[:cut].strip(), "family": after[cut:].strip()}


def guess_kind(text: str) -> str:
    """Classify a resolved value. Order matters: a shadow contains a colour and
    three lengths, so it has to be ruled out before either of those wins."""
    t = text.strip().lower()
    if not t:
        return "other"
    if t in ("none", "transparent", "currentcolor", "auto", "inherit", "initial"):
        return "keyword"
    if _HEX_RE.match(t) or (COLOR_FUNC.match(t) and t.endswith(")") and "," not in
                            re.sub(r"\([^)]*\)", "", t)):
        return "color"
    if COLOR_FUNC.search(t) and (re.search(r"\d(px|rem|em)\b", t) or "inset" in t):
        return "shadow"
    if TIME_RE.match(t):
        return "time"
    if re.search(r"\b[\d.]+m?s\b", t) and re.search(r"cubic-bezier|\bease|\blinear|\bsteps\(", t):
        return "motion-pair"
    if "cubic-bezier" in t or t.startswith("steps(") or t in (
            "linear", "ease", "ease-in", "ease-out", "ease-in-out"):
        return "easing"
    if parse_font_shorthand(text):
        return "font"
    if NUMBER_RE.match(t):
        return "number"
    if re.match(r"^(clamp|calc|min|max)\(", t) or NUM_UNIT.match(t.split()[0] if t.split() else ""):
        return "length"
    if "," in t and not re.search(r"\d", t):
        return "font-stack"
    return "other"


# ===========================================================================
# 5. THE TOKEN LAYER
# ===========================================================================

THEME_SEL = re.compile(r'\[data-theme\s*[~^|$*]?=\s*["\']?([\w-]+)')
DENSITY_SEL = re.compile(r'\[data-density\s*[~^|$*]?=\s*["\']?([\w-]+)')
ROOT_SEL = re.compile(r"^(:root|html|:where\(:root\)|\*)\b")


def context_of(d: Decl) -> Tuple[str, str]:
    """Classify the cascade context a declaration lives in. (kind, label)."""
    sel = " ".join(d.selectors)
    ats = " ".join(d.at_rules)
    m = THEME_SEL.search(sel)
    if m:
        return "theme", m.group(1)
    m = DENSITY_SEL.search(sel)
    if m:
        return "density", m.group(1)
    if "prefers-color-scheme: dark" in ats or "prefers-color-scheme:dark" in ats:
        return "theme", "dark"
    if "prefers-reduced-motion" in ats:
        return "condition", "reduced-motion"
    if "forced-colors" in ats:
        return "condition", "forced-colors"
    if "prefers-contrast" in ats:
        return "condition", "more-contrast"
    if ats.startswith("@media") or "@media" in ats:
        return "condition", re.sub(r"\s+", " ", ats)[:60]
    if ROOT_SEL.match(sel.strip()):
        return "root", "light"
    return "scoped", sel[:60]


@dataclass
class Token:
    name: str
    tier: int
    tier_why: str
    group: str
    file: str
    line: int
    raw: str
    note: str = ""
    references: List[str] = field(default_factory=list)
    referenced_by: List[str] = field(default_factory=list)
    overrides: List[Dict[str, Any]] = field(default_factory=list)
    resolved: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    density: Dict[str, str] = field(default_factory=dict)
    kind: str = "other"
    contrast: List[Dict[str, Any]] = field(default_factory=list)


SURFACES = ("--bg-canvas", "--bg-surface", "--bg-raised", "--bg-sunken")
CONTRAST_PAIRS_EXTRA = (
    ("--fg-on-accent", "--bg-accent"),
    ("--fg-on-accent", "--bg-accent-hover"),
    ("--fg-on-accent", "--bg-danger"),
    ("--fg-on-inverse", "--bg-inverse"),
    ("--fg-on-success", "--bg-success"),
    ("--fg-on-warning", "--bg-warning"),
    ("--fg-on-danger", "--bg-danger"),
)


# ===========================================================================
# 6. COMPONENTS
# ===========================================================================

STATE_SIGNATURES: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("hover", (":hover",)),
    ("focus-visible", (":focus-visible",)),
    ("active", (":active",)),
    ("disabled", (":disabled", "[aria-disabled", '[data-state="disabled"')),
    ("loading", ('[data-state="loading"', "[aria-busy", '[data-loading'),),
    ("error", ("[aria-invalid", '[data-state="error"', "[data-invalid")),
)
SEVEN_STATES = ("default", "hover", "focus-visible", "active", "disabled", "loading", "error")

VARIANT_ATTR = re.compile(r'\[data-variant\s*[~^|$*]?=\s*["\']([\w-]+)')
SIZE_ATTR = re.compile(r'\[data-size\s*[~^|$*]?=\s*["\']([\w-]+)')
CLASS_RE = re.compile(r"\.(-?[_a-zA-Z][\w-]*)")
NOT_GUARD = re.compile(r":not\([^)]*\)")


def strip_guards(selector: str) -> str:
    """Drop `:not(...)` before looking for states.

    `.button:hover:not(:disabled)` is a HOVER rule. The `:disabled` inside the
    guard is a condition on when hover applies, not a disabled-state rule, and
    reading it as one makes a component look like it implements a state it does
    not."""
    return NOT_GUARD.sub("", selector)
INTERACTIVE_HINTS = (":hover", ":active", ":focus", "cursor: pointer", "cursor:pointer")

#: Tier-1 prefixes that have a Tier-2 role, so a component reading one is a
#: Law 6 violation. Mirrors TIER1_WITH_ROLE in audit_design.py — same rule,
#: same list, so the two tools never disagree about what counts as a leak.
LEAKY_TIER1_PREFIXES = ("--space-", "--neutral-", "--accent-", "--success-", "--warning-",
                        "--danger-", "--info-", "--text-", "--leading-", "--weight-",
                        "--shadow-")
#: Zero is zero. `--space-0` nulls a socket out; it asserts no value, so reading
#: it from a component is not the tier violation the prefix makes it look like.
TIER1_NULLS = {"--space-0", "--radius-none", "--shadow-none"}


@dataclass
class Socket:
    name: str
    default: str
    line: int
    note: str = ""
    accepts: str = "<any>"
    kind: str = "other"
    consumed_by: List[str] = field(default_factory=list)
    repointed_by: List[str] = field(default_factory=list)
    resolved: Dict[str, str] = field(default_factory=dict)


@dataclass
class Component:
    name: str
    root_class: str
    file: str
    line: int
    note: str = ""
    sockets: List[Socket] = field(default_factory=list)
    variants: List[Dict[str, Any]] = field(default_factory=list)
    sizes: List[Dict[str, Any]] = field(default_factory=list)
    states: List[Dict[str, Any]] = field(default_factory=list)
    parts: List[Dict[str, Any]] = field(default_factory=list)
    props: List[Dict[str, Any]] = field(default_factory=list)
    prop_file: str = ""
    doc: str = ""
    element: str = ""
    interactive: bool = False
    reads_roles: List[str] = field(default_factory=list)
    tier1_reads: List[str] = field(default_factory=list)
    theme_aware: Dict[str, bool] = field(default_factory=dict)


ACCEPT_BY_KIND = {
    "length": "<length>",
    "color": "<color>",
    "time": "<time>",
    "easing": "<easing-function>",
    "motion-pair": "<time> <easing-function>",
    "shadow": "<shadow>+",
    "font": "<font-shorthand>",
    "font-stack": "<family-name>#",
    "number": "<number>",
    "keyword": "<keyword>",
}


def socket_prefix(class_name: str) -> str:
    return "--" + class_name + "-"


def parse_components(files: List[CssFile], resolvers: Dict[str, Resolver]) -> List[Component]:
    comps: List[Component] = []
    for cf in files:
        by_selector: Dict[str, List[Rule]] = {}
        for r in cf.rules:
            by_selector.setdefault(r.selector, []).append(r)
        # A component root is a rule whose selector is exactly one class and
        # which declares custom properties namespaced to that class. That is the
        # socket block from style-architecture.md §6, and it is self-identifying.
        roots: List[Tuple[str, Rule]] = []
        for r in cf.rules:
            sel = r.selector.strip()
            if not re.fullmatch(r"\.[-\w]+", sel):
                continue
            cls = sel[1:]
            pfx = socket_prefix(cls)
            if any(d.prop.startswith(pfx) for d in r.decls):
                roots.append((cls, r))
        seen_cls = set()
        for cls, root in roots:
            if cls in seen_cls:
                continue
            seen_cls.add(cls)
            comps.append(build_component(cf, cls, root, resolvers))
    comps.sort(key=lambda c: c.name)
    return comps


def build_component(cf: CssFile, cls: str, root: Rule,
                    resolvers: Dict[str, Resolver]) -> Component:
    pfx = socket_prefix(cls)
    # The comment above the root rule describes the component; the comment above
    # the first declaration describes that declaration. Do not confuse them —
    # the socket block's banner is not a component summary.
    comp = Component(name=cls, root_class=cls, file=cf.path, line=root.line,
                     note=root.note)
    sockets: Dict[str, Socket] = {}
    for d in root.decls:
        if d.prop.startswith(pfx):
            r = resolvers["light"].resolve_value(d.value)
            sockets[d.prop] = Socket(
                name=d.prop, default=d.value, line=d.line, note=d.note,
                accepts=ACCEPT_BY_KIND.get(r.kind, "<any>"), kind=r.kind,
            )
            for theme, res in resolvers.items():
                rv = res.resolve_value(d.value)
                sockets[d.prop].resolved[theme] = rv.display()

    own_rules = [r for r in cf.rules
                 if r.selector.startswith("." + cls) or f".{cls}" in r.selector]
    # which declarations consume which socket
    for r in own_rules:
        for d in r.decls:
            for ref in VAR_REF.findall(d.value):
                if ref in sockets and not d.prop.startswith("--"):
                    if d.prop not in sockets[ref].consumed_by:
                        sockets[ref].consumed_by.append(d.prop)

    variants: Dict[str, Dict[str, Any]] = {}
    sizes: Dict[str, Dict[str, Any]] = {}
    states: Dict[str, Dict[str, Any]] = {"default": {
        "state": "default", "selector": root.selector, "line": root.line, "sets": {}}}
    parts: Dict[str, Dict[str, Any]] = {}
    reads: set = set()
    tier1_reads: List[str] = []

    for r in own_rules:
        sel = r.selector
        sets = {d.prop: d.value for d in r.decls if d.prop.startswith(pfx)}
        other = {d.prop: d.value for d in r.decls if not d.prop.startswith("--")}
        for d in r.decls:
            for ref in VAR_REF.findall(d.value):
                if not ref.startswith(pfx):
                    reads.add(ref)
        for name in VARIANT_ATTR.findall(sel):
            v = variants.setdefault(name, {"name": name, "selector": sel,
                                           "line": r.line, "sets": {}})
            v["sets"].update(sets)
        for name in SIZE_ATTR.findall(sel):
            s = sizes.setdefault(name, {"name": name, "selector": sel,
                                        "line": r.line, "sets": {}})
            s["sets"].update(sets)
        sel_states = strip_guards(sel)
        for state, needles in STATE_SIGNATURES:
            if any(nd in sel_states for nd in needles):
                st = states.setdefault(state, {"state": state, "selector": sel,
                                               "line": r.line, "sets": {}})
                st["sets"].update(sets)
                if other:
                    st.setdefault("declares", {}).update(other)
        if ":focus-within" in sel_states and "focus-visible" not in states:
            states.setdefault("focus-within", {"state": "focus-within", "selector": sel,
                                               "line": r.line, "sets": sets})
        for c in CLASS_RE.findall(sel):
            if c.startswith(cls + "__"):
                # `declares` (3.4.0) lets diff_system tell a renamed local
                # class from one renamed and restyled.
                parts.setdefault(c, {"class": c, "line": r.line,
                                     "props": sorted(other.keys()),
                                     "declares": dict(sorted(other.items()))})
        for socket_name, v in sets.items():
            if socket_name in sockets and sel != root.selector:
                if sel not in sockets[socket_name].repointed_by:
                    sockets[socket_name].repointed_by.append(sel)

    text_of_rules = " ".join(r.selector for r in own_rules)
    decl_text = " ".join(f"{d.prop}: {d.value}" for r in own_rules for d in r.decls)
    comp.interactive = any(h in text_of_rules or h in decl_text for h in INTERACTIVE_HINTS)

    comp.sockets = [sockets[k] for k in sorted(sockets)]
    comp.variants = [variants[k] for k in sorted(variants)]
    comp.sizes = [sizes[k] for k in sorted(sizes)]
    comp.states = [states[k] for k in sorted(states, key=lambda s: (
        SEVEN_STATES.index(s) if s in SEVEN_STATES else 99, s))]
    comp.parts = [parts[k] for k in sorted(parts)]
    comp.reads_roles = sorted(reads)
    comp.tier1_reads = sorted(
        t for t in reads
        if t not in TIER2_EXCEPTIONS
        and t not in TIER1_NULLS
        and classify_tier(t, "", [])[0] == 1
        and any(t.startswith(p) for p in LEAKY_TIER1_PREFIXES)
    )
    return comp


# ===========================================================================
# 7. TS / TSX PROPS
#
# The CSS gives you the socket table. The TSX gives you props, defaults and the
# JSDoc — and the JSDoc is where the only un-generatable content in a component
# doc lives, so it is worth parsing properly rather than skipping.
# ===========================================================================

IFACE_RE = re.compile(
    r"(?:export\s+)?(?:interface\s+(\w+)Props\s*(?:extends[^{]+)?\{|type\s+(\w+)Props\s*=\s*\{)",
    re.M)
FUNC_RE = re.compile(r"(?:export\s+)?(?:default\s+)?function\s+(\w+)\s*\(", re.M)
ARROW_RE = re.compile(r"(?:export\s+)?const\s+(\w+)\s*(?::[^=]+)?=\s*\(", re.M)
JSDOC_RE = re.compile(r"/\*\*(.*?)\*/", re.S)


def clean_jsdoc(body: str) -> str:
    out = []
    for raw in body.splitlines():
        s = raw.strip()
        s = re.sub(r"^\*\s?", "", s)
        out.append(s)
    return " ".join(x for x in out if x).strip()


def match_brace(text: str, start: int) -> int:
    depth = 0
    i = start
    while i < len(text):
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i
        elif c in "\"'`":
            q = c
            i += 1
            while i < len(text) and text[i] != q:
                i += 2 if text[i] == "\\" else 1
        i += 1
    return len(text) - 1


def parse_props_file(path: str, text: str) -> List[Dict[str, Any]]:
    """Return [{component, props:[...], doc, element}] for each component found."""
    found: List[Dict[str, Any]] = []
    for m in IFACE_RE.finditer(text):
        name = m.group(1) or m.group(2)
        open_brace = text.index("{", m.start())
        end = match_brace(text, open_brace)
        body = text[open_brace + 1:end]
        props: List[Dict[str, Any]] = []
        pos = 0
        for pm in re.finditer(r"(?:^|\n)\s*(\w+)(\?)?\s*:\s*([^;\n]+);", body):
            doc = ""
            before = body[pos:pm.start()]
            dm = list(JSDOC_RE.finditer(before))
            if dm and before[dm[-1].end():].strip() == "":
                doc = clean_jsdoc(dm[-1].group(1))
            pos = pm.end()
            props.append({
                "name": pm.group(1),
                "optional": bool(pm.group(2)),
                "type": " ".join(pm.group(3).split()),
                "doc": doc,
                "default": None,
            })
        # defaults from the destructuring signature
        defaults: Dict[str, str] = {}
        sig = re.search(r"function\s+%s\s*\(\s*\{(.*?)\}\s*:" % re.escape(name),
                        text, re.S) or re.search(
            r"const\s+%s\s*(?::[^=]*)?=\s*\(\s*\{(.*?)\}\s*:" % re.escape(name), text, re.S)
        if sig:
            for dm2 in re.finditer(r"(\w+)\s*=\s*([^,}]+)", sig.group(1)):
                defaults[dm2.group(1)] = dm2.group(2).strip()
        for p in props:
            if p["name"] in defaults:
                p["default"] = defaults[p["name"]]
        # component-level JSDoc: the block immediately above the function
        doc = ""
        # `(?:(?!\*/).)*` instead of `.*?`: a non-greedy wildcard still lets the
        # match START at an earlier comment and swallow everything between, which
        # turns a one-line component summary into the whole props interface.
        fm = re.search(r"/\*\*((?:(?!\*/).)*)\*/\s*(?:export\s+)?(?:default\s+)?"
                       r"(?:function|const)\s+%s\b" % re.escape(name), text, re.S)
        if fm:
            doc = clean_jsdoc(fm.group(1))
        element = ""
        em = re.search(r"return\s*\(?\s*<(\w+)", text[m.end():])
        if em:
            element = em.group(1)
        found.append({"component": name, "props": props, "doc": doc,
                      "element": element, "file": path})
    return found


def kebab(name: str) -> str:
    s = re.sub(r"(?<!^)(?=[A-Z])", "-", name).lower()
    return s.replace("--", "-")


# ===========================================================================
# 8. EXTRACTION
# ===========================================================================

TOKEN_FILE_PAT = re.compile(r"(^|[/\\])[\w.-]*tokens?\.(css|scss)$|(^|[/\\])theme\.css$")
PROPS_EXT = {".ts", ".tsx", ".jsx", ".js", ".mjs"}
CSS_EXT = {".css", ".scss", ".pcss"}
SKIP_DIRS = {"node_modules", ".git", "dist", "build", "__pycache__", ".next", "out"}


def iter_paths(patterns: Sequence[str]) -> Iterator[Path]:
    for pat in patterns:
        p = Path(pat)
        if p.is_dir():
            for sub in sorted(p.rglob("*")):
                if any(part in SKIP_DIRS for part in sub.parts):
                    continue
                if sub.is_file():
                    yield sub
        elif p.is_file():
            yield p
        else:
            for hit in sorted(globmod.glob(pat, recursive=True)):
                hp = Path(hit)
                if hp.is_file():
                    yield hp


class Extractor:
    def __init__(self, root: Path, root_px: float = 16.0) -> None:
        self.root = root
        self.root_px = root_px
        self.tokens: Dict[str, Token] = {}
        self.token_files: List[CssFile] = []
        self.component_files: List[CssFile] = []
        self.prop_files: List[str] = []
        self.components: List[Component] = []
        self.gaps: List[Dict[str, Any]] = []
        self.limits: List[Dict[str, Any]] = []
        self.themes: List[str] = ["light"]
        self.densities: List[str] = []
        self.resolvers: Dict[str, Resolver] = {}
        self.density_resolvers: Dict[str, Resolver] = {}
        self.envs: Dict[str, Dict[str, str]] = {}

    def rel(self, p: str | Path) -> str:
        try:
            return Path(p).resolve().relative_to(self.root.resolve()).as_posix()
        except ValueError:
            return Path(p).as_posix()

    # -- tokens -----------------------------------------------------------
    def read_tokens(self, files: Sequence[Path]) -> None:
        for path in files:
            cf = CssFile(self.rel(path), path.read_text(encoding="utf-8"))
            self.token_files.append(cf)
        base_env: Dict[str, str] = {}
        overrides: Dict[str, List[Dict[str, Any]]] = {}

        for cf in self.token_files:
            for d in cf.decls:
                if not d.prop.startswith("--"):
                    continue
                kind, label = context_of(d)
                if kind == "root":
                    base_env[d.prop] = d.value
                    if d.prop not in self.tokens:
                        refs = sorted(set(VAR_REF.findall(d.value)))
                        tier, why = classify_tier(d.prop, d.value, refs)
                        self.tokens[d.prop] = Token(
                            name=d.prop, tier=tier, tier_why=why, group=group_of(d.prop),
                            file=cf.path, line=d.line, raw=d.value, note=d.note,
                            references=refs)
                    else:
                        t = self.tokens[d.prop]
                        t.overrides.append({"context": "root", "label": "later declaration",
                                            "selector": " ".join(d.selectors),
                                            "value": d.value, "file": cf.path, "line": d.line})
                        t.raw = d.value
                else:
                    overrides.setdefault(d.prop, []).append({
                        "context": kind, "label": label,
                        "selector": " ".join(d.selectors) or "(at-rule)",
                        "at_rules": list(d.at_rules),
                        "value": d.value, "file": cf.path, "line": d.line,
                    })
                    if kind == "theme" and label not in self.themes:
                        self.themes.append(label)
                    if kind == "density" and label not in self.densities:
                        self.densities.append(label)

        for name, entries in overrides.items():
            if name not in self.tokens:
                # Declared only inside a theme: still a real token, and the fact
                # that it has no root value is itself worth reporting.
                first = entries[0]
                refs = sorted(set(VAR_REF.findall(first["value"])))
                tier, why = classify_tier(name, first["value"], refs)
                self.tokens[name] = Token(name=name, tier=tier, tier_why=why,
                                          group=group_of(name), file=first["file"],
                                          line=first["line"], raw=first["value"],
                                          references=refs)
                self.gaps.append({
                    "kind": "theme-only-token", "severity": "warning", "token": name,
                    "where": f"{first['file']}:{first['line']}",
                    "detail": f"{name} is declared only in the `{first['label']}` context. "
                              "It resolves to nothing in the default theme.",
                })
            self.tokens[name].overrides.extend(entries)

        # cascade contexts we can resolve in
        self.envs["light"] = dict(base_env)
        for theme in self.themes[1:]:
            env = dict(base_env)
            for name, t in self.tokens.items():
                for o in t.overrides:
                    if o["context"] == "theme" and o["label"] == theme:
                        env[name] = o["value"]
            self.envs[theme] = env
        self.resolvers = {k: Resolver(v, self.root_px) for k, v in self.envs.items()}

        # Density is a multiplier, not a second set of values (Law 7), so it
        # gets its own resolvers rather than doubling the theme matrix.
        density_resolvers: Dict[str, Resolver] = {}
        for name, t in self.tokens.items():
            if name != "--density":
                continue
            for o in t.overrides:
                if o["context"] == "density":
                    env = dict(base_env)
                    env["--density"] = o["value"]
                    density_resolvers[o["label"]] = Resolver(env, self.root_px)
        self.density_resolvers = density_resolvers

        # resolve, and record what we could not
        for name, t in sorted(self.tokens.items()):
            for theme, res in self.resolvers.items():
                r = res.resolve(name, is_name=True)
                t.kind = r.kind if r.kind != "other" else t.kind
                entry: Dict[str, Any] = {"status": r.status, "value": r.value,
                                         "display": r.display()}
                if r.px is not None:
                    entry["px"] = round(r.px, 4)
                if r.min_px is not None:
                    entry["min_px"] = round(r.min_px, 4)
                    entry["max_px"] = round(r.max_px or r.min_px, 4)
                if r.hex:
                    entry["hex"] = r.hex
                    entry["alpha"] = r.alpha
                if r.reason:
                    entry["reason"] = r.reason
                if r.parts:
                    entry["parts"] = r.parts
                t.resolved[theme] = entry
                if r.status in ("unresolved", "range") and theme == "light":
                    self.limits.append({
                        "token": name, "status": r.status, "reason": r.reason,
                        "value": r.value,
                    })
            base_display = t.resolved.get("light", {}).get("display", "")
            for label, res in sorted(self.density_resolvers.items()):
                got = res.resolve(name, is_name=True).display()
                if got != base_display:
                    t.density.setdefault(label, got)

        # reference graph
        for name, t in self.tokens.items():
            for ref in t.references:
                if ref in self.tokens and name not in self.tokens[ref].referenced_by:
                    self.tokens[ref].referenced_by.append(name)
            for o in t.overrides:
                for ref in VAR_REF.findall(o["value"]):
                    if ref in self.tokens and name not in self.tokens[ref].referenced_by:
                        self.tokens[ref].referenced_by.append(name)

        # a theme may only re-point Tier 2 (token-contract.md, "The three tiers")
        for name, t in sorted(self.tokens.items()):
            if t.tier != 1:
                continue
            for o in t.overrides:
                if o["context"] in ("theme", "condition"):
                    self.gaps.append({
                        "kind": "theme-repoints-tier1", "severity": "info",
                        "token": name, "where": f"{o['file']}:{o['line']}",
                        "detail": f"The `{o['label']}` context re-points the Tier-1 primitive "
                                  f"{name}. Themes re-point Tier 2 only; a Tier-1 re-point is "
                                  "either a documented exception or a role that was never made.",
                    })

    # -- contrast ---------------------------------------------------------
    def compute_contrast(self) -> None:
        pairs: List[Tuple[str, str]] = []
        for name, t in self.tokens.items():
            # `--fg-on-*` names its own background. Measuring it against the
            # canvas produces white-on-white and a 1.00:1 that means nothing.
            if name.startswith("--fg-") and t.tier == 2 and not name.startswith("--fg-on-"):
                for bg in SURFACES:
                    if bg in self.tokens:
                        pairs.append((name, bg))
        pairs.extend(p for p in CONTRAST_PAIRS_EXTRA
                     if p[0] in self.tokens and p[1] in self.tokens)
        for fg, bg in pairs:
            for theme, res in self.resolvers.items():
                rf = res.resolve(fg, is_name=True)
                rb = res.resolve(bg, is_name=True)
                if rf.kind != "color" or rb.kind != "color" or not rf.hex or not rb.hex:
                    continue
                if rf.alpha < 1.0 or rb.alpha < 1.0:
                    self.limits.append({
                        "token": fg, "status": "no-contrast",
                        "reason": f"{fg} on {bg} is translucent; the ratio depends on what is "
                                  "behind it, so it is not computable from source.",
                        "value": rf.value,
                    })
                    continue
                ratio = contrast_ratio_oklch(parse_color(rf.value), parse_color(rb.value))
                self.tokens[fg].contrast.append({
                    "against": bg, "theme": theme, "ratio": round(ratio, 2),
                    "fg_hex": rf.hex, "bg_hex": rb.hex,
                    "body": ratio >= 4.5, "large": ratio >= 3.0, "ui": ratio >= 3.0,
                })

    # -- components -------------------------------------------------------
    def read_components(self, css_files: Sequence[Path], prop_files: Sequence[Path]) -> None:
        for path in css_files:
            self.component_files.append(CssFile(self.rel(path), path.read_text(encoding="utf-8")))
        self.components = parse_components(self.component_files, self.resolvers)

        prop_index: Dict[str, Dict[str, Any]] = {}
        for path in prop_files:
            text = path.read_text(encoding="utf-8")
            for entry in parse_props_file(self.rel(path), text):
                prop_index[kebab(entry["component"])] = entry
            self.prop_files.append(self.rel(path))
        for comp in self.components:
            entry = prop_index.get(comp.name)
            if entry:
                comp.props = entry["props"]
                comp.doc = entry["doc"]
                comp.element = entry["element"]
                comp.prop_file = entry["file"]
                if comp.element in ("button", "a", "input", "select", "textarea"):
                    comp.interactive = True

        # Does each component actually change between themes? Only ask of
        # components that have something colour-shaped to change: a layout
        # primitive holds nothing a theme could re-point, and flagging seventeen
        # of them is how a gap list stops being read.
        for comp in self.components:
            themeable = [s for s in comp.sockets if s.kind in ("color", "shadow")]
            if not themeable:
                continue
            for theme in self.resolvers:
                if theme == "light":
                    continue
                comp.theme_aware[theme] = any(
                    s.resolved.get(theme) != s.resolved.get("light") for s in themeable)

    # -- gaps -------------------------------------------------------------
    def find_gaps(self, prose_dir: Optional[Path]) -> None:
        for comp in self.components:
            implemented = {s["state"] for s in comp.states}
            if comp.interactive:
                for state in SEVEN_STATES:
                    if state in implemented:
                        continue
                    if state == "focus-visible" and "focus-within" in implemented:
                        self.gaps.append({
                            "kind": "weak-state", "severity": "warning",
                            "component": comp.name, "state": state,
                            "where": f"{comp.file}:{comp.line}",
                            "detail": f"`{comp.name}` styles :focus-within but not "
                                      ":focus-visible. The container lights up; the control "
                                      "that actually has focus does not.",
                        })
                        continue
                    self.gaps.append({
                        "kind": "missing-state", "severity": "error",
                        "component": comp.name, "state": state,
                        "where": f"{comp.file}:{comp.line}",
                        "detail": f"`{comp.name}` is interactive but has no rule for the "
                                  f"`{state}` state. An unwritten state renders as `default`, "
                                  "so nothing fails and nobody notices.",
                    })
            for s in comp.sockets:
                if not s.consumed_by and not s.repointed_by:
                    self.gaps.append({
                        "kind": "unconsumed-socket", "severity": "warning",
                        "component": comp.name, "socket": s.name,
                        "where": f"{comp.file}:{s.line}",
                        "detail": f"{s.name} is declared on `.{comp.root_class}` but no "
                                  "declaration reads it. It is published API that does nothing; "
                                  "either wire it up or delete it before someone depends on it.",
                    })
            for t in comp.tier1_reads:
                self.gaps.append({
                    "kind": "tier1-leak", "severity": "error",
                    "component": comp.name, "token": t,
                    "where": f"{comp.file}:{comp.line}",
                    "detail": f"`{comp.name}` reads the Tier-1 primitive {t}. Law 6: components "
                              "read roles. Documenting this as API would publish a mistake.",
                })
            for theme, changed in sorted(comp.theme_aware.items()):
                if not changed:
                    self.gaps.append({
                        "kind": "no-theme-coverage", "severity": "warning",
                        "component": comp.name, "theme": theme,
                        "where": f"{comp.file}:{comp.line}",
                        "detail": f"Every socket on `{comp.name}` resolves identically in "
                                  f"`light` and `{theme}`. Either it is colourless, or its "
                                  "colours are not roles.",
                    })

        for name, t in sorted(self.tokens.items()):
            if t.referenced_by:
                continue
            used = any(name in comp.reads_roles for comp in self.components)
            if used:
                continue
            if any(o["context"] in ("theme", "density", "condition") for o in t.overrides):
                continue
            self.gaps.append({
                "kind": "orphan-token",
                "severity": "warning" if t.tier >= 2 else "info",
                "token": name, "tier": t.tier, "where": f"{t.file}:{t.line}",
                "detail": f"{name} (Tier {t.tier}) is declared and referenced by nothing. "
                          + ("A Tier-2 role nobody reads is a decision nobody took."
                             if t.tier >= 2 else
                             "A spare ramp step is fine; an unused role is not. Confirm which."),
            })

        if prose_dir is not None:
            documented = {p.stem for p in prose_dir.glob("components/*.md")}
            names = {c.name for c in self.components}
            for comp in sorted(names - documented):
                self.gaps.append({
                    "kind": "undocumented-component", "severity": "warning",
                    "component": comp, "where": self.rel(prose_dir / "components" / f"{comp}.md"),
                    "detail": f"`{comp}` exists in code with no hand-written page. The generated "
                              "page will have the what and none of the why.",
                })
            for doc in sorted(documented - names):
                self.gaps.append({
                    "kind": "orphan-doc", "severity": "error",
                    "component": doc,
                    "where": self.rel(prose_dir / "components" / f"{doc}.md"),
                    "detail": f"`{doc}.md` documents a component that no longer exists in the "
                              "source. A doc for a deleted component is worse than no doc: it "
                              "is an instruction to use something that is gone.",
                })

        order = {"error": 0, "warning": 1, "info": 2}
        self.gaps.sort(key=lambda g: (order.get(g["severity"], 3), g["kind"],
                                      g.get("component", ""), g.get("token", ""),
                                      g.get("state", "")))

    def layer_order(self) -> List[str]:
        """Each `@layer a, b, c;` order statement, in the order read.

        It usually sits in the entry stylesheet beside the imports, so every
        stylesheet given is read for it, not only the token files.
        diff_system compares it: a reorder re-decides every conflict in the
        system at once (Law 5)."""
        out: List[str] = []
        for cf in self.token_files + self.component_files:
            for raw, _line in cf.at_statements:
                m = re.match(r"@layer\s+([^{};]+?)\s*;?$", raw.strip(), re.I)
                if m:
                    prelude = " ".join(m.group(1).split())
                    if prelude not in out:
                        out.append(prelude)
        return out

    # -- output -----------------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema": SCHEMA,
            "themes": sorted(self.themes),
            "densities": sorted(self.densities),
            "layers": self.layer_order(),
            "sources": {
                "tokens": [cf.path for cf in self.token_files],
                "components": [cf.path for cf in self.component_files],
                "props": sorted(self.prop_files),
            },
            "tokens": [
                {
                    "name": t.name, "tier": t.tier, "tier_why": t.tier_why,
                    "group": t.group, "kind": t.kind, "file": t.file, "line": t.line,
                    "raw": t.raw, "note": t.note,
                    "references": t.references,
                    "referenced_by": sorted(set(t.referenced_by)),
                    "overrides": t.overrides,
                    "resolved": t.resolved,
                    "density": t.density,
                    "contrast": t.contrast,
                }
                for _, t in sorted(self.tokens.items())
            ],
            "components": [
                {
                    "name": c.name, "root_class": c.root_class, "file": c.file,
                    "line": c.line, "doc": c.doc, "note": c.note, "element": c.element,
                    "interactive": c.interactive, "prop_file": c.prop_file,
                    "sockets": [
                        {"name": s.name, "default": s.default, "line": s.line,
                         "note": s.note, "accepts": s.accepts, "kind": s.kind,
                         "consumed_by": s.consumed_by, "repointed_by": s.repointed_by,
                         "resolved": s.resolved}
                        for s in c.sockets
                    ],
                    "variants": c.variants, "sizes": c.sizes, "states": c.states,
                    "parts": c.parts, "props": c.props,
                    "reads_roles": c.reads_roles,
                    "theme_aware": c.theme_aware,
                }
                for c in self.components
            ],
            "gaps": self.gaps,
            "limits": sorted(self.limits, key=lambda l: (l["token"], l["status"])),
            "stats": {
                "tokens": len(self.tokens),
                "tier1": sum(1 for t in self.tokens.values() if t.tier == 1),
                "tier2": sum(1 for t in self.tokens.values() if t.tier == 2),
                "components": len(self.components),
                "sockets": sum(len(c.sockets) for c in self.components),
                "gaps": len(self.gaps),
                "unresolved": len([l for l in self.limits if l["status"] == "unresolved"]),
            },
        }


# ===========================================================================
# 9. CLI
# ===========================================================================

def classify_inputs(paths: Sequence[Path]) -> Tuple[List[Path], List[Path], List[Path]]:
    tokens, css, props = [], [], []
    for p in paths:
        ext = p.suffix.lower()
        if ext in CSS_EXT:
            (tokens if TOKEN_FILE_PAT.search(str(p).replace(os.sep, "/")) else css).append(p)
        elif ext in PROPS_EXT:
            props.append(p)
    return tokens, css, props


def human_report(data: Dict[str, Any]) -> str:
    s = data["stats"]
    out = [
        f"tokens      {s['tokens']:>4}   (Tier 1: {s['tier1']}, Tier 2: {s['tier2']})",
        f"components  {s['components']:>4}   ({s['sockets']} Tier-3 sockets)",
        f"themes      {', '.join(data['themes'])}",
        f"densities   {', '.join(data['densities']) or '(none declared)'}",
        f"unresolved  {s['unresolved']:>4}   (see the `limits` section)",
        "",
    ]
    if not data["gaps"]:
        out.append("gaps        none")
        return "\n".join(out)
    out.append(f"gaps        {s['gaps']}")
    by_kind: Dict[str, List[Dict[str, Any]]] = {}
    for g in data["gaps"]:
        by_kind.setdefault(f"{g['severity']}/{g['kind']}", []).append(g)
    for key in sorted(by_kind):
        items = by_kind[key]
        out.append(f"\n  {key}  ({len(items)})")
        for g in items[:12]:
            subject = g.get("component") or g.get("token") or ""
            extra = f" · {g['state']}" if g.get("state") else ""
            extra += f" · {g['socket']}" if g.get("socket") else ""
            out.append(f"    {subject}{extra}  —  {g['where']}")
        if len(items) > 12:
            out.append(f"    … and {len(items) - 12} more")
    return "\n".join(out)


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="python -m scripts.extract_system",
        description="Extract a normalized design system (tokens, components, sockets, gaps) "
                    "from its own source into system.json.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python -m scripts.extract_system styles/ src/components/ --out docs/system.json
  python -m scripts.extract_system --tokens styles/tokens.css \\
      --components "src/components/*.css" --props "src/components/*.tsx" \\
      --prose docs/prose --out docs/system.json --report
  python -m scripts.extract_system styles/ src/components/ --out build/system.json --strict
""")
    ap.add_argument("paths", nargs="*", default=[],
                    help="Files, directories or globs. Anything matching tokens.css / "
                         "theme.css is read as a token file; other CSS as component CSS; "
                         ".ts/.tsx/.jsx as prop sources.")
    ap.add_argument("--tokens", action="append", default=[], metavar="PATH",
                    help="Token file (repeatable). Overrides auto-detection.")
    ap.add_argument("--components", action="append", default=[], metavar="PATH",
                    help="Component stylesheet, directory or glob (repeatable).")
    ap.add_argument("--props", action="append", default=[], metavar="PATH",
                    help="Component TS/TSX file, directory or glob (repeatable).")
    ap.add_argument("--prose", metavar="DIR",
                    help="Hand-written markdown tree. Enables the undocumented-component "
                         "and orphan-doc gaps.")
    ap.add_argument("--out", metavar="FILE", default="-",
                    help="Where to write system.json (default: stdout).")
    ap.add_argument("--root", metavar="DIR", default=".",
                    help="Paths in the output are relative to this (default: cwd).")
    ap.add_argument("--root-font-size", type=float, default=16.0, metavar="PX",
                    help="rem basis for static resolution (default: 16).")
    ap.add_argument("--report", action="store_true",
                    help="Print a human summary to stderr.")
    ap.add_argument("--strict", action="store_true",
                    help="Exit 1 if any error-severity gap was found.")
    ap.add_argument("--color-impl", metavar="PATH",
                    help="Path to web-design-studio's generate_color_ramp.py. Default: found "
                         "next to this skill if the suite is installed whole.")
    ap.add_argument("--no-color-impl", action="store_true",
                    help="Force the vendored color math even if the studio script is present.")
    ap.add_argument("--check-color-impl", action="store_true",
                    help="Verify the vendored color math against the studio's and exit.")
    return ap


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = build_parser()
    args = ap.parse_args(argv)

    upstream = None if args.no_color_impl else _find_upstream(args.color_impl)
    if args.check_color_impl:
        if upstream is None:
            print("No upstream generate_color_ramp.py found; nothing to check against.",
                  file=sys.stderr)
            return 2
        problems = use_upstream_color_impl(upstream, verify=True)
        if problems:
            print("Color implementations DISAGREE:", file=sys.stderr)
            for p in problems:
                print(f"  {p}", file=sys.stderr)
            return 1
        print(f"Vendored color math agrees with {upstream} on "
              f"{len(COLOR_PROBES)} probe pairs.")
        return 0
    if upstream is not None:
        try:
            problems = use_upstream_color_impl(upstream, verify=True)
            for p in problems:
                print(f"warning: color implementations disagree: {p}", file=sys.stderr)
        except Exception as exc:                       # noqa: BLE001 - never fatal
            print(f"warning: falling back to vendored color math ({exc})", file=sys.stderr)

    auto = list(iter_paths(args.paths)) if args.paths else []
    auto_tokens, auto_css, auto_props = classify_inputs(auto)
    token_files = list(iter_paths(args.tokens)) + auto_tokens
    css_files = [p for p in (list(iter_paths(args.components)) + auto_css)
                 if p.suffix.lower() in CSS_EXT]
    prop_files = [p for p in (list(iter_paths(args.props)) + auto_props)
                  if p.suffix.lower() in PROPS_EXT]

    def dedupe(items: Sequence[Path]) -> List[Path]:
        seen, out = set(), []
        for p in items:
            key = p.resolve()
            if key not in seen:
                seen.add(key)
                out.append(p)
        return out

    token_files, css_files, prop_files = dedupe(token_files), dedupe(css_files), dedupe(prop_files)
    if not token_files:
        ap.error("no token file found. Pass one with --tokens, or include a directory "
                 "containing tokens.css. Without the token layer there is no tier to "
                 "report and no value to resolve.")

    root = Path(args.root)
    if not root.is_dir():
        ap.error(f"--root {args.root} is not a directory")

    ex = Extractor(root, args.root_font_size)
    try:
        ex.read_tokens(token_files)
        ex.compute_contrast()
        ex.read_components(css_files, prop_files)
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    ex.find_gaps(Path(args.prose) if args.prose else None)

    data = ex.to_dict()
    data["meta"] = {"color_impl": COLOR_IMPL, "root_font_size": args.root_font_size}
    text = json.dumps(data, indent=2, sort_keys=False, ensure_ascii=False) + "\n"
    if args.out == "-":
        sys.stdout.write(text)
    else:
        outp = Path(args.out)
        outp.parent.mkdir(parents=True, exist_ok=True)
        outp.write_text(text, encoding="utf-8")
        print(f"wrote {outp} — {data['stats']['tokens']} tokens, "
              f"{data['stats']['components']} components, {data['stats']['gaps']} gaps",
              file=sys.stderr)
    if args.report:
        print(human_report(data), file=sys.stderr)
    if args.strict and any(g["severity"] == "error" for g in data["gaps"]):
        return 1
    return 0


if __name__ == "__main__":
    # A Windows pipe (git hook, CI, `> file`) defaults to the ANSI code page,
    # where printing →, Δ or ✓ raises UnicodeEncodeError. Consoles and
    # Claude Code already use UTF-8 and are left alone.
    for _stream in (sys.stdout, sys.stderr):
        if getattr(_stream, "encoding", "utf-8").lower() not in ("utf-8", "utf8"):
            _stream.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
