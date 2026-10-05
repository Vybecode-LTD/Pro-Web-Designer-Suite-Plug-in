#!/usr/bin/env python3
"""
diff_system.py — classify what changed between two versions of a design system.

Semver for an API asks "can a consumer still call it?" A design system has a
second surface that no type checker sees: the RENDERED OUTPUT. A consumer who
never touches their code can still wake up to a different button. So the
question this script answers is not "did a name disappear" but:

    Does a consumer's rendered output change in a way they did not ask for?

That reframing is what produces the classification. Renaming a token is
breaking. Re-pointing a Tier-2 role is ALSO breaking — same name, same call
site, different pixels. Adding a Tier-2 role is not. Changing a Tier-1
primitive is breaking for everything downstream of it, which is why this script
computes the transitive blast radius rather than reporting one line.

What it reads
-------------
  system.json     from `design-system-docs/scripts/extract_system.py` — the
                  normalized snapshot this suite already produces. Preferred:
                  it carries components, Tier-3 sockets, variants and states,
                  so the diff can see the whole surface and not just tokens.
  tokens.css      a raw token file, when no snapshot exists. The extractor is
                  imported and run in-process when the suite is installed
                  whole; a compact vendored parser runs otherwise.

What it emits
-------------
  report            human, for the person deciding the version number
  json              machine, schema design-system-versioning/diff@1
  changelog         Keep-a-Changelog markdown, for the repo
  migration-guide   consumer-facing prose, with the codemod command per item

The gate
--------
A name that vanished with nobody warned is the one failure mode that is never
acceptable, so it is the one this script exits non-zero on. Value changes and
re-points are breaking too, but a deprecation record cannot help a consumer
whose pixels moved — a changelog entry can. `--gate major` is available for
teams that want every breaking change to carry a ledger record.

Usage
-----
    python -m scripts.diff_system OLD NEW
    python -m scripts.diff_system v1/system.json v2/system.json --report
    python -m scripts.diff_system v1/tokens.css v2/tokens.css \\
        --from-version 1.4.2 --format changelog -o CHANGELOG.fragment.md
    python -m scripts.diff_system old.json new.json \\
        --from-version 1.4.2 --format migration-guide -o docs/UPGRADE-2.0.md
    python -m scripts.diff_system old.json new.json \\
        --deprecations deprecations.json          # release gate

Contrast
--------
The OKLab/WCAG functions come from `web-design-studio/scripts/generate_color_ramp.py`.
When that file is reachable it is imported and used directly; otherwise the
byte-identical vendored copy below runs. `--check-color-impl` proves the two
agree, so a changelog quoting 4.92:1 and a ramp generator quoting 4.90:1 for
the same pair can never happen.

Exit codes: 0 clean · 1 the gate fired · 2 bad invocation.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import importlib.util
import json
import math
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

SCHEMA = "design-system-versioning/diff@1"
DOCS_SCHEMA = "design-system-docs/system/1"
LEDGER_SCHEMA = "design-system-versioning/deprecations@1"


def bail(message: str) -> "SystemExit":
    """Exit 2 — bad invocation — with the message on stderr where it belongs.

    A bare `raise SystemExit("…")` exits 1, which is the code this tool reserves
    for "the gate fired". A caller in CI cannot tell a real failure from a typo
    in a path if both exit 1.
    """
    print(message, file=sys.stderr)
    return SystemExit(2)


# ===========================================================================
# 1. COLOR MATH
#
# Vendored verbatim from web-design-studio/scripts/generate_color_ramp.py, by
# way of design-system-docs/scripts/extract_system.py. Three implementations of
# WCAG contrast in one suite is how a migration guide and a ramp generator end
# up disagreeing about the same pair. `--check-color-impl` asserts they agree.
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


def contrast_ratio_rgb(fg: Tuple[float, float, float],
                       bg: Tuple[float, float, float]) -> float:
    l1 = relative_luminance(*fg)
    l2 = relative_luminance(*bg)
    if l2 > l1:
        l1, l2 = l2, l1
    return (l1 + 0.05) / (l2 + 0.05)


def contrast_ratio_oklch(a: Tuple[float, float, float],
                         b: Tuple[float, float, float]) -> float:
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
    ("oklch(100% 0 0)", "oklch(64.5% 0.188 42)"),
    ("#ffffff", "#e8440a"),
)


def _sibling(*parts: str) -> Optional[Path]:
    """Locate a script in a sibling skill, if the suite is installed whole."""
    here = Path(__file__).resolve()
    candidates = [
        here.parent.parent.parent.joinpath(*parts),
        here.parent / parts[-1],
    ]
    for c in candidates:
        if c.is_file():
            return c
    return None


def _find_upstream(explicit: Optional[str]) -> Optional[Path]:
    if explicit:
        p = Path(explicit).expanduser()
        return p if p.is_file() else None
    return _sibling("web-design-studio", "scripts", "generate_color_ramp.py")


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, str(path))
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot import {path}")
    mod = importlib.util.module_from_spec(spec)
    # Registered BEFORE exec: @dataclass resolves a field's type by looking the
    # defining module up in sys.modules, and a module that is not there yet
    # fails with a bare AttributeError three frames deep in dataclasses.
    sys.modules[name] = mod
    try:
        spec.loader.exec_module(mod)
    except BaseException:
        sys.modules.pop(name, None)
        raise
    return mod


def use_upstream_color_impl(path: Path, *, verify: bool = True) -> List[str]:
    """Bind this module's color functions to the studio's own implementation."""
    global COLOR_IMPL, parse_color, contrast_ratio_oklch, oklch_to_rgb, rgb_to_hex
    mod = _load_module(path, "_wds_color_ramp")
    problems: List[str] = []
    if verify:
        for fg, bg in COLOR_PROBES:
            mine = contrast_ratio_oklch(parse_color(fg), parse_color(bg))
            theirs = mod.contrast_ratio_oklch(mod.parse_color(fg), mod.parse_color(bg))
            if abs(mine - theirs) > 1e-9:
                problems.append(f"{fg} on {bg}: vendored {mine:.6f} vs upstream {theirs:.6f}")
    parse_color = mod.parse_color                       # type: ignore[assignment]
    contrast_ratio_oklch = mod.contrast_ratio_oklch     # type: ignore[assignment]
    oklch_to_rgb = mod.oklch_to_rgb                     # type: ignore[assignment]
    rgb_to_hex = mod.rgb_to_hex                         # type: ignore[assignment]
    COLOR_IMPL = f"upstream:{path.name}"
    return problems


# ===========================================================================
# 2. THE TIER TABLE
#
# Straight out of token-contract.md, and deliberately identical to
# extract_system.py's. The tier is a property of the NAME'S MEANING, not of its
# first word — which is why --space-section is Tier 2 and a prefix-only
# classifier gets it wrong.
# ===========================================================================

TIER2_EXCEPTIONS = {
    "--space-section", "--space-subsection", "--space-block",
    "--space-fluid-sm", "--space-fluid-md", "--space-fluid-lg", "--space-fluid-xl",
}

TIER1_PREFIXES: Tuple[str, ...] = (
    "--space-", "--density", "--neutral-", "--accent-", "--success-", "--warning-",
    "--danger-", "--info-", "--text-", "--leading-", "--tracking-", "--weight-",
    "--font-", "--radius-", "--stroke-", "--shadow-", "--dur-", "--ease-", "--bp-",
    "--z-", "--measure-", "--width-", "--tap-", "--grid-columns",
)

TIER2_PREFIXES: Tuple[str, ...] = (
    "--gap-", "--pad-", "--gutter-", "--bg-", "--fg-", "--border-", "--type-",
    "--elevation-", "--motion-",
)

GROUPS: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("spacing", ("--space-", "--gap-", "--pad-", "--gutter-", "--density", "--tap-")),
    ("typography", ("--font-", "--text-", "--leading-", "--tracking-", "--weight-",
                    "--type-", "--measure-")),
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


def classify_tier(name: str, refs: Sequence[str]) -> int:
    if name in TIER2_EXCEPTIONS:
        return 2
    if any(name.startswith(p) for p in TIER2_PREFIXES):
        return 2
    if any(name.startswith(p) for p in TIER1_PREFIXES):
        return 1
    return 2 if refs else 1


# ===========================================================================
# 3. THE FALLBACK TOKEN PARSER
#
# Used only when design-system-docs is not reachable. It reads the same shapes
# out of tokens.css that extract_system.py does — :root, [data-theme="x"],
# @media (prefers-color-scheme: dark) — and resolves var() chains. It is
# deliberately smaller: a diff needs to know whether a resolved value CHANGED,
# which is a string comparison, not a layout engine.
# ===========================================================================

VAR_CALL = re.compile(r"var\(\s*(--[\w-]+)\s*(?:,([^()]*(?:\([^()]*\)[^()]*)*))?\)")
VAR_REF = re.compile(r"var\(\s*(--[\w-]+)")
THEME_SEL = re.compile(r'\[data-theme\s*[~^|$*]?=\s*["\']?([\w-]+)')
DENSITY_SEL = re.compile(r'\[data-density\s*[~^|$*]?=\s*["\']?([\w-]+)')
LAYER_STMT = re.compile(r"@layer\s+([^;{]+);")
OKLCH_ALPHA = re.compile(
    r"^oklch\(\s*([\d.]+%?)\s+([\d.]+)\s+(-?[\d.]+)(?:deg)?\s*(?:/\s*([\d.]+%?)\s*)?\)$",
    re.IGNORECASE)
NUM_UNIT = re.compile(r"^([+-]?(?:\d+\.?\d*|\.\d+))([a-z%]*)$", re.I)
ABSOLUTE_UNITS = {"px": 1.0, "rem": 16.0, "pt": 96 / 72, "pc": 16.0, "in": 96.0,
                  "cm": 96 / 2.54, "mm": 9.6 / 2.54}
CALC_CALL = re.compile(r"\bcalc\((?:[^()]|\([^()]*\))*\)", re.I)


@dataclass
class RawDecl:
    prop: str
    value: str
    line: int
    context: str        # "root" | "theme:<name>" | "density:<name>" | "other"
    note: str = ""


def _strip_and_note(text: str) -> Tuple[str, Dict[int, str]]:
    """Blank comments, keeping a line -> trailing-comment map for notes."""
    out: List[str] = []
    notes: Dict[int, str] = {}
    i, n, line = 0, len(text), 1
    while i < n:
        if text[i] == "/" and i + 1 < n and text[i + 1] == "*":
            j = text.find("*/", i + 2)
            j = n if j < 0 else j + 2
            body = text[i + 2:max(i + 2, j - 2)]
            cleaned = " ".join(x.strip().lstrip("*").strip() for x in body.splitlines())
            cleaned = re.sub(r"\s{2,}", " ", cleaned).strip(" -=*")
            before = text.rfind("\n", 0, i)
            if text[before + 1:i].strip() and cleaned:
                notes[line] = cleaned
            nl = body.count("\n")
            out.append("\n" * nl)
            line += nl
            i = j
            continue
        if text[i] == "\n":
            line += 1
        out.append(text[i])
        i += 1
    return "".join(out), notes


def parse_token_css(text: str) -> Tuple[List[RawDecl], List[str], List[str]]:
    """Return (declarations, themes, layer-statement preludes)."""
    clean, notes = _strip_and_note(text)
    layers = [" ".join(m.group(1).split()) for m in LAYER_STMT.finditer(clean)]
    decls: List[RawDecl] = []
    themes: List[str] = []
    sel_stack: List[str] = []
    at_stack: List[str] = []
    buf: List[str] = []
    buf_line = 1
    line = 1
    depth_is_at: List[bool] = []

    def context() -> str:
        sel = " ".join(sel_stack)
        # @layer wraps the whole token file and creates no cascade CONTEXT — it
        # decides which declaration wins, not what a declaration resolves to.
        # Counting it as one puts every :root token in a "condition" bucket and
        # leaves the base environment empty, which resolves the entire system to
        # `<undeclared>`.
        ats = " ".join(a for a in at_stack
                       if not a.lower().startswith(("@layer", "@supports")))
        m = THEME_SEL.search(sel)
        if m:
            return f"theme:{m.group(1)}"
        m = DENSITY_SEL.search(sel)
        if m:
            return f"density:{m.group(1)}"
        if "prefers-color-scheme: dark" in ats or "prefers-color-scheme:dark" in ats:
            return "theme:dark"
        if ats.strip():
            return "condition:" + re.sub(r"\s+", " ", ats)[:48]
        if re.match(r"^(:root|html|\*)\b", sel.strip()):
            return "root"
        return "scoped:" + sel[:48]

    def flush() -> None:
        nonlocal buf
        raw = "".join(buf).strip()
        buf = []
        if not raw or raw.startswith("@"):
            return
        idx = raw.find(":")
        if idx < 0:
            return
        prop = raw[:idx].strip()
        value = " ".join(raw[idx + 1:].split())
        if prop.startswith("--"):
            decls.append(RawDecl(prop, value, buf_line, context(),
                                 notes.get(buf_line, "")))

    i, n = 0, len(clean)
    while i < n:
        c = clean[i]
        if c == "{":
            prelude = " ".join("".join(buf).split())
            buf = []
            if prelude.startswith("@"):
                at_stack.append(prelude)
                depth_is_at.append(True)
            else:
                sel_stack.append(prelude)
                depth_is_at.append(False)
                m = THEME_SEL.search(prelude)
                if m and m.group(1) not in themes:
                    themes.append(m.group(1))
            i += 1
            continue
        if c == "}":
            flush()
            if depth_is_at:
                (at_stack if depth_is_at.pop() else sel_stack).pop()
            i += 1
            continue
        if c == ";":
            flush()
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
    flush()
    if any(d.context == "theme:dark" for d in decls) and "dark" not in themes:
        themes.append("dark")
    return decls, themes, layers


def substitute(value: str, env: Dict[str, str], seen: Optional[set] = None,
               depth: int = 0) -> str:
    """Resolve every var() against `env`. Returns the text, unresolved parts intact."""
    seen = seen or set()
    if depth > 24:
        return value
    out = value
    for _ in range(32):
        m = VAR_CALL.search(out)
        if not m:
            break
        name, fallback = m.group(1), (m.group(2) or "").strip()
        if name in seen:
            return out
        if name in env:
            repl = substitute(env[name], env, seen | {name}, depth + 1)
        elif fallback:
            repl = substitute(fallback, env, seen | {name}, depth + 1)
        else:
            repl = f"<undeclared {name}>"
        out = out[:m.start()] + repl + out[m.end():]
    return " ".join(out.split())


def _eval_expr(text: str) -> Optional[float]:
    """Evaluate a pure-length arithmetic expression to px, or None."""
    toks = re.findall(r"calc\(|[()+*/]|(?<=[\d\w%) ])-(?=[ (])|"
                      r"[+-]?(?:\d+\.?\d*|\.\d+)[a-z%]*|-", text, re.I)
    pos = 0

    def atom() -> Optional[Tuple[float, str]]:
        nonlocal pos
        if pos >= len(toks):
            return None
        t = toks[pos]
        if t in ("(", "calc("):
            pos += 1
            v = summation()
            if pos < len(toks) and toks[pos] == ")":
                pos += 1
            return v
        if t == "-":
            pos += 1
            inner = atom()
            return None if inner is None else (-inner[0], inner[1])
        pos += 1
        m = NUM_UNIT.match(t)
        if not m:
            return None
        num, unit = float(m.group(1)), m.group(2).lower()
        if unit == "":
            return (num, "")
        if unit in ABSOLUTE_UNITS:
            return (num * ABSOLUTE_UNITS[unit], "px")
        return None

    def product() -> Optional[Tuple[float, str]]:
        nonlocal pos
        v = atom()
        while v is not None and pos < len(toks) and toks[pos] in ("*", "/"):
            op = toks[pos]
            pos += 1
            rhs = atom()
            if rhs is None:
                return None
            if op == "*":
                if v[1] and rhs[1]:
                    return None
                v = (v[0] * rhs[0], v[1] or rhs[1])
            else:
                if rhs[1] or abs(rhs[0]) < 1e-12:
                    return None
                v = (v[0] / rhs[0], v[1])
        return v

    def summation() -> Optional[Tuple[float, str]]:
        nonlocal pos
        v = product()
        while v is not None and pos < len(toks) and toks[pos] in ("+", "-"):
            op = toks[pos]
            pos += 1
            rhs = product()
            if rhs is None or rhs[1] != v[1]:
                return None
            v = (v[0] + (rhs[0] if op == "+" else -rhs[0]), v[1])
        return v

    got = summation()
    if got is None or pos != len(toks) or got[1] != "px":
        return None
    return got[0]


def fmt_px(px: float) -> str:
    if abs(px - round(px)) < 1e-6:
        return f"{int(round(px))}px"
    return f"{px:.3f}".rstrip("0").rstrip(".") + "px"


def resolve_display(raw: str, env: Dict[str, str]) -> Dict[str, Any]:
    """{'display', 'value', optional 'hex'/'alpha'/'px'} for one token value."""
    text = substitute(raw, env)
    entry: Dict[str, Any] = {"value": text, "display": text}
    m = OKLCH_ALPHA.match(text)
    if m:
        alpha_raw = m.group(4)
        alpha = 1.0
        if alpha_raw:
            alpha = (float(alpha_raw[:-1]) / 100 if alpha_raw.endswith("%")
                     else float(alpha_raw))
        try:
            lch = parse_color(f"oklch({m.group(1)} {m.group(2)} {m.group(3)})")
        except ColorError:
            return entry
        entry["hex"] = rgb_to_hex(*clamp_rgb(oklch_to_rgb(*lch)))
        entry["alpha"] = alpha
        entry["display"] = (entry["hex"] if alpha >= 1.0
                            else f"{entry['hex']} @ {alpha:.2f}α")
        return entry
    if _HEX_RE.match(text.strip()):
        try:
            lch = parse_color(text.strip())
        except ColorError:
            return entry
        entry["hex"] = rgb_to_hex(*clamp_rgb(oklch_to_rgb(*lch)))
        entry["alpha"] = 1.0
        entry["display"] = entry["hex"]
        return entry
    px = _eval_expr(text)
    if px is not None:
        entry["px"] = round(px, 4)
        entry["display"] = fmt_px(px)
        return entry
    # fold embedded calc() so a display never reads `calc(2px * 2)`
    def fold(mo: "re.Match[str]") -> str:
        got = _eval_expr(mo.group(0))
        return fmt_px(got) if got is not None else mo.group(0)
    entry["display"] = CALC_CALL.sub(fold, text)
    return entry


# ===========================================================================
# 4. SNAPSHOTS
#
# One normalized shape, whatever it was read from, so the differ never branches
# on where its input came from.
# ===========================================================================


@dataclass
class Snapshot:
    label: str
    path: str
    source: str                                     # system.json | tokens.css
    impl: str                                       # how it was read
    themes: List[str] = field(default_factory=list)
    densities: List[str] = field(default_factory=list)
    tokens: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    components: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    layers: List[str] = field(default_factory=list)
    layers_recorded: bool = True                    # False: a system.json from before 3.4.0
    has_components: bool = False
    _condition_envs: Dict[str, Dict[str, str]] = field(default_factory=dict, repr=False)

    def tier(self, name: str) -> int:
        return int(self.tokens.get(name, {}).get("tier", 0))

    def display(self, name: str, theme: str = "light") -> str:
        res = self.tokens.get(name, {}).get("resolved", {})
        got = res.get(theme) or res.get("light") or {}
        return str(got.get("display", ""))

    def colour(self, name: str, theme: str) -> Optional[Tuple[str, str, float]]:
        """(resolved colour text, hex, alpha), or None if it is not a colour.

        The TEXT is what contrast is measured from, never the hex. Quantising
        oklch(56.5% 0.176 42) to #c64600 first and measuring that reports
        4.91:1 where the ramp generator reports 4.92:1, and a suite whose two
        tools disagree in the second decimal is a suite nobody quotes.
        """
        res = self.tokens.get(name, {}).get("resolved", {})
        got = res.get(theme) or {}
        if "hex" not in got:
            return None
        return (str(got.get("value") or got["hex"]), str(got["hex"]),
                float(got.get("alpha", 1.0)))

    def theme_value(self, name: str, theme: str) -> str:
        """The declared value in one theme: the override if there is one, else root."""
        tok = self.tokens.get(name)
        if not tok:
            return ""
        for ov in tok.get("overrides", []):
            if ov.get("context") == "theme" and ov.get("label") == theme:
                return str(ov.get("value", ""))
        return str(tok.get("raw", ""))

    def at_density(self, name: str, density: str) -> str:
        """What `name` resolves to under [data-density=density]: the resolved
        density map when the snapshot has one, else the declared override,
        else the default density's value."""
        tok = self.tokens.get(name, {})
        got = (tok.get("density") or {}).get(density)
        if got is not None:
            return str(got)
        ov = _override(tok, "density", density)
        return ov if ov is not None else self.display(name)

    def at_condition(self, name: str, label: str) -> str:
        """What `name` resolves to for a user with media condition `label`
        (reduced motion, forced colours): the root values with that
        condition's overrides on top."""
        env = self._condition_envs.get(label)
        if env is None:
            env = {n: str(t.get("raw", "")) for n, t in self.tokens.items()}
            for n, tok in self.tokens.items():
                got = _override(tok, "condition", label)
                if got is not None:
                    env[n] = got
            self._condition_envs[label] = env
        return str(resolve_display(env.get(name, ""), env).get("display", ""))

    def condition_labels(self) -> List[str]:
        return sorted({str(ov.get("label")) for tok in self.tokens.values()
                       for ov in tok.get("overrides", [])
                       if ov.get("context") == "condition"})


MODULE_FILE = re.compile(r"\.module\.(?:css|scss|sass|less|pcss)$", re.I)


def _normalize_docs_json(data: Dict[str, Any], label: str, path: str) -> Snapshot:
    snap = Snapshot(label=label, path=path, source="system.json",
                    impl="design-system-docs/system.json",
                    themes=list(data.get("themes") or ["light"]),
                    densities=list(data.get("densities") or []),
                    layers=list(data.get("layers") or []),
                    layers_recorded="layers" in data)
    for t in data.get("tokens", []):
        snap.tokens[t["name"]] = {
            "tier": t.get("tier", 0),
            "group": t.get("group", group_of(t["name"])),
            "kind": t.get("kind", "other"),
            "raw": t.get("raw", ""),
            "note": t.get("note", ""),
            "references": list(t.get("references") or []),
            "referenced_by": list(t.get("referenced_by") or []),
            "overrides": list(t.get("overrides") or []),
            "resolved": dict(t.get("resolved") or {}),
            "density": dict(t.get("density") or {}),
            "file": t.get("file", ""),
            "line": t.get("line", 0),
        }
    for c in data.get("components", []):
        snap.components[c["name"]] = {
            "file": c.get("file", ""),
            "line": c.get("line", 0),
            "doc": c.get("doc", ""),
            "element": c.get("element", ""),
            "prop_file": c.get("prop_file", ""),
            "module": bool(MODULE_FILE.search(str(c.get("file", "")))),
            "sockets": {s["name"]: s for s in c.get("sockets", [])},
            "variants": {v["name"]: v for v in c.get("variants", [])},
            "sizes": {s["name"]: s for s in c.get("sizes", [])},
            "states": {s["state"]: s for s in c.get("states", [])},
            "parts": {p["class"]: p for p in c.get("parts", [])},
            "props": {p["name"]: p for p in c.get("props", [])},
            "reads_roles": list(c.get("reads_roles") or []),
        }
    snap.has_components = bool(snap.components)
    return snap


def _snapshot_from_css_upstream(paths: List[Path], label: str,
                                extractor_path: Path) -> Optional[Snapshot]:
    """Run design-system-docs' extractor in-process and normalize its output."""
    try:
        mod = _load_module(extractor_path, "_dsd_extract_system")
        ex = mod.Extractor(Path("."), 16.0)
        ex.read_tokens(paths)
        ex.compute_contrast()
        data = ex.to_dict()
    except Exception as exc:                        # noqa: BLE001 — never fatal
        print(f"warning: could not run {extractor_path.name} ({type(exc).__name__}: "
              f"{exc}); falling back to the vendored token parser.", file=sys.stderr)
        return None
    snap = _normalize_docs_json(data, label, str(paths[0]))
    snap.source = "tokens.css"
    snap.impl = f"upstream:{extractor_path.name}"
    snap.layers = _layers_from(paths)
    return snap


def _layers_from(paths: Sequence[Path]) -> List[str]:
    out: List[str] = []
    for p in paths:
        try:
            text = p.read_text(encoding="utf-8")
        except OSError:
            continue
        for m in LAYER_STMT.finditer(text):
            prelude = " ".join(m.group(1).split())
            if prelude not in out:
                out.append(prelude)
    return out


def _snapshot_from_css_vendored(paths: List[Path], label: str) -> Snapshot:
    snap = Snapshot(label=label, path=str(paths[0]), source="tokens.css",
                    impl="vendored token parser")
    base: Dict[str, str] = {}
    overrides: Dict[str, List[Dict[str, Any]]] = {}
    themes: List[str] = ["light"]
    for p in paths:
        decls, found_themes, layers = parse_token_css(p.read_text(encoding="utf-8"))
        for t in found_themes:
            if t not in themes:
                themes.append(t)
        for lay in layers:
            if lay not in snap.layers:
                snap.layers.append(lay)
        for d in decls:
            if d.context == "root":
                base[d.prop] = d.value
                refs = sorted(set(VAR_REF.findall(d.value)))
                snap.tokens[d.prop] = {
                    "tier": classify_tier(d.prop, refs),
                    "group": group_of(d.prop), "kind": "other",
                    "raw": d.value, "note": d.note, "references": refs,
                    "referenced_by": [], "overrides": [], "resolved": {},
                    "file": str(p), "line": d.line,
                }
            elif d.context.startswith(("theme:", "density:", "condition:")):
                ctx, _, lab = d.context.partition(":")
                overrides.setdefault(d.prop, []).append({
                    "context": ctx, "label": lab, "value": d.value,
                    "file": str(p), "line": d.line,
                })
    for name, entries in overrides.items():
        if name not in snap.tokens:
            first = entries[0]
            refs = sorted(set(VAR_REF.findall(first["value"])))
            snap.tokens[name] = {
                "tier": classify_tier(name, refs), "group": group_of(name),
                "kind": "other", "raw": first["value"], "note": "",
                "references": refs, "referenced_by": [], "overrides": [],
                "resolved": {}, "file": first["file"], "line": first["line"],
            }
        snap.tokens[name]["overrides"].extend(entries)

    envs: Dict[str, Dict[str, str]] = {"light": dict(base)}
    for theme in themes[1:]:
        env = dict(base)
        for name, tok in snap.tokens.items():
            for ov in tok["overrides"]:
                if ov["context"] == "theme" and ov["label"] == theme:
                    env[name] = ov["value"]
        envs[theme] = env
    for name, tok in snap.tokens.items():
        for theme, env in envs.items():
            source = env.get(name, tok["raw"])
            tok["resolved"][theme] = resolve_display(source, env)
        got = tok["resolved"].get("light", {})
        tok["kind"] = ("color" if "hex" in got else
                       "length" if "px" in got else "other")
    # Each density is the default environment plus its own overrides, recorded
    # only where it differs, as design-system-docs records it.
    for name, tok in snap.tokens.items():
        tok["density"] = {}
        for ov in tok["overrides"]:
            if ov["context"] == "density" and ov["label"] not in snap.densities:
                snap.densities.append(ov["label"])
    for density in snap.densities:
        env = dict(base)
        for name, tok in snap.tokens.items():
            got = _override(tok, "density", density)
            if got is not None:
                env[name] = got
        for name, tok in snap.tokens.items():
            shown = resolve_display(env.get(name, tok["raw"]), env).get("display", "")
            if shown != tok["resolved"].get("light", {}).get("display", ""):
                tok["density"][density] = shown
    for name, tok in snap.tokens.items():
        for ref in tok["references"]:
            if ref in snap.tokens and name not in snap.tokens[ref]["referenced_by"]:
                snap.tokens[ref]["referenced_by"].append(name)
        for ov in tok["overrides"]:
            for ref in VAR_REF.findall(ov["value"]):
                if ref in snap.tokens and name not in snap.tokens[ref]["referenced_by"]:
                    snap.tokens[ref]["referenced_by"].append(name)
    snap.themes = themes
    return snap


def load_snapshot(raw: str, label: str, *, no_upstream: bool = False) -> Snapshot:
    p = Path(raw)
    if not p.exists():
        raise bail(f"diff_system: no such snapshot: {raw}")
    if p.is_dir():
        css = sorted(list(p.rglob("tokens.css")) + list(p.rglob("theme.css")))
        js = sorted(p.rglob("system.json"))
        if js:
            p = js[0]
        elif css:
            return _load_css(css, label, no_upstream)
        else:
            raise bail(
                f"diff_system: {raw} contains neither system.json nor tokens.css.\n"
                f"Point at one directly, or generate a snapshot with:\n"
                f"  python -m scripts.extract_system {raw} --out system.json")
    if p.suffix.lower() == ".json":
        try:
            data = json.loads(p.read_bytes())
        except (OSError, json.JSONDecodeError) as exc:
            raise bail(f"diff_system: {p} is not readable JSON ({exc}).")
        schema = str(data.get("schema", ""))
        if schema.split("/")[0] != "design-system-docs":
            raise bail(
                f"diff_system: {p} is not a design-system-docs snapshot "
                f"(schema={schema!r}). Produce one with:\n"
                f"  python -m scripts.extract_system styles/ src/ --out system.json")
        snap = _normalize_docs_json(data, label, str(p))
        return snap
    return _load_css([p], label, no_upstream)


def _load_css(paths: List[Path], label: str, no_upstream: bool) -> Snapshot:
    extractor = None if no_upstream else _sibling(
        "design-system-docs", "scripts", "extract_system.py")
    if extractor is not None:
        snap = _snapshot_from_css_upstream(paths, label, extractor)
        if snap is not None:
            return snap
    return _snapshot_from_css_vendored(paths, label)


# ===========================================================================
# 5. THE TAXONOMY
#
# The full argument for every row is in references/change-classification.md.
# The one-line WHY lives here too, because a report that says "major" without
# saying why is a report people argue with instead of acting on.
# ===========================================================================


@dataclass(frozen=True)
class Kind:
    id: str
    severity: str          # major | minor | patch
    label: str
    why: str
    detect: str            # auto | partial
    burden: str            # none | codemod | manual | review
    gate: bool             # can a deprecation record cover this?


def K(*args: Any) -> Kind:
    return Kind(*args)


KINDS: Dict[str, Kind] = {k.id: k for k in [
    # --- Tier 1 -----------------------------------------------------------
    K("tier1-added", "minor", "Tier-1 primitive added",
      "Nothing resolved differently yesterday. A new step on a closed scale is a "
      "design decision to review, not a break.", "auto", "none", False),
    K("tier1-removed", "major", "Tier-1 primitive removed",
      "Every role and every component downstream of it resolves to nothing. "
      "A var() with no declaration and no fallback drops the whole declaration.",
      "auto", "codemod", True),
    K("tier1-renamed", "major", "Tier-1 primitive renamed",
      "Same as removed, for anyone who read it directly — which, under Law 6, "
      "should be nobody, and in practice never is.", "partial", "codemod", True),
    K("tier1-value-changed", "major", "Tier-1 value changed",
      "The primitive is the root of a reference tree. Everything downstream "
      "re-renders, and no consumer asked for any of it.", "auto", "review", False),
    K("breakpoint-changed", "major", "Breakpoint moved",
      "Every layout that switches at that width switches somewhere else now. "
      "Nothing errors; the tablet view simply arrives at a different size.",
      "auto", "review", False),
    K("breakpoint-added", "minor", "Breakpoint added",
      "Existing queries are untouched until someone writes one against it.",
      "auto", "none", False),
    # --- Tier 2 -----------------------------------------------------------
    K("tier2-added", "minor", "Tier-2 role added",
      "A new word in the vocabulary. Nobody reads it yet, so nobody's output "
      "moves.", "auto", "none", False),
    K("tier2-removed", "major", "Tier-2 role removed",
      "Component CSS reads Tier 2. A removed role is a removed public API.",
      "auto", "codemod", True),
    K("tier2-renamed", "major", "Tier-2 role renamed",
      "The call site still says var(--old). CSS does not error — the declaration "
      "is simply dropped, so the element inherits or falls back to nothing.",
      "partial", "codemod", True),
    K("tier2-repointed", "major", "Tier-2 role re-pointed",
      "The subtle one. Same name, same call site, different pixels. A consumer "
      "who relied on the old value did not ask for the new one.", "auto", "review",
      False),
    K("tier2-repointed-equal", "patch", "Tier-2 role re-sourced, same value",
      "The reference chain changed but the resolved value did not. Refactor, "
      "not a change — provided the new source moves in lockstep from here on.",
      "auto", "none", False),
    K("theme-override-changed", "major", "Theme re-point changed",
      "Exactly a re-point, scoped to one theme. Consumers in that theme render "
      "differently; consumers in the other notice nothing, which is why this one "
      "reaches production.", "auto", "review", False),
    K("theme-override-added", "major", "Theme re-point added",
      "A role that followed its root value in that theme now has its own. "
      "Additive in the default theme, and a re-point in that one: its consumers "
      "render differently. A patch when it resolves to what it did.",
      "auto", "review", False),
    K("theme-override-removed", "major", "Theme re-point removed",
      "The role falls back to its root value in that theme. Usually a dark-mode "
      "regression that light-mode review cannot see.", "auto", "review", True),
    K("theme-added", "minor", "Theme added",
      "Nobody's current theme changed.", "auto", "none", False),
    K("theme-removed", "major", "Theme removed",
      "Every consumer setting data-theme to it silently renders the default.",
      "auto", "manual", True),
    K("density-changed", "major", "Density scale changed",
      "Every spacing role at that density moves. Nothing errors; the compact "
      "view simply packs differently. A patch when nothing resolves differently.",
      "auto", "review", False),
    K("density-added", "minor", "Density added",
      "Nobody's current density changed.", "auto", "none", False),
    K("density-removed", "major", "Density removed",
      "Every consumer setting data-density to it silently renders the default "
      "density.", "auto", "manual", True),
    K("condition-changed", "major", "Media-condition override changed",
      "A render change for every user with that setting: reduced motion, forced "
      "colours, more contrast. The users least able to absorb a surprise, and "
      "nobody reviewing without the setting sees it.", "auto", "review", False),
    # --- Tier 3 / components ----------------------------------------------
    K("socket-added", "minor", "Tier-3 socket added",
      "New public CSS API with a default that reproduces today's rendering.",
      "auto", "none", False),
    K("socket-removed", "major", "Tier-3 socket removed",
      "A consumer's override of it stops doing anything, silently. Their CSS "
      "still parses; it just has no effect.", "auto", "codemod", True),
    K("socket-default-changed", "major", "Socket default changed",
      "Every consumer who did NOT override it renders differently — that is most "
      "of them, and they are the ones who never read the changelog.", "auto",
      "review", False),
    K("socket-default-equal", "patch", "Socket default re-sourced, same value",
      "The default now reads a different role that resolves identically.",
      "auto", "none", False),
    K("component-added", "minor", "Component added", "Nothing existing changed.",
      "auto", "none", False),
    K("component-removed", "major", "Component removed",
      "An import that no longer resolves, or a class that no longer styles.",
      "auto", "manual", True),
    K("component-renamed", "major", "Component renamed",
      "Both the import and every descendant selector written against the old "
      "class name.", "partial", "codemod", True),
    K("variant-added", "minor", "Variant added",
      "data-variant values nobody passes yet.", "auto", "none", False),
    K("variant-removed", "major", "Variant removed",
      "The attribute is still legal HTML, so it renders as the base variant with "
      "no error anywhere. The worst failure shape there is.", "auto", "manual", True),
    K("variant-changed", "major", "Variant appearance changed",
      "No API moved. The pixels did. A design system's output IS its API.",
      "auto", "review", False),
    K("size-added", "minor", "Size added", "Nothing existing changed.",
      "auto", "none", False),
    K("size-removed", "major", "Size removed",
      "data-size falls back to the default size, silently.", "auto", "manual", True),
    K("state-added", "minor", "State added",
      "A state that used to render as `default` now renders as itself. Additive "
      "in API terms and visible in the proof sheet — review it there.",
      "auto", "review", False),
    K("state-removed", "major", "State removed",
      "The state renders as `default`. No error, no warning, and a focus ring "
      "that is simply gone.", "auto", "manual", True),
    K("part-added", "minor", "DOM part added",
      "A new `__` element. Safe unless a consumer's `> *` selector counts children.",
      "auto", "review", False),
    K("part-removed", "major", "DOM structure changed",
      "Descendant selectors and test queries written against it break, even "
      "though nothing visual changed and nothing type-checks differently.",
      "auto", "manual", True),
    K("part-renamed-local", "patch", "Local class renamed (CSS Modules)",
      "The rendered class is hashed, so no consumer could write the old name. "
      "Major after all if the component exports its styles object: then the "
      "key is the API.", "auto", "none", False),
    K("element-changed", "major", "Root element changed",
      "Semantics, focusability, default styles, and every `div.card` selector "
      "a consumer wrote.", "auto", "manual", False),
    K("prop-added-optional", "minor", "Optional prop added",
      "Existing call sites still compile.", "auto", "none", False),
    K("prop-added-required", "major", "Required prop added",
      "Every existing call site is now a type error.", "auto", "manual", True),
    K("prop-removed", "major", "Prop removed",
      "A type error at best; an ignored prop at worst.", "auto", "codemod", True),
    K("prop-default-changed", "major", "Prop default changed",
      "Every call site that omitted it behaves differently, and none of them "
      "changed a line.", "auto", "review", False),
    K("prop-type-changed", "major", "Prop type changed",
      "Narrowing is a type error; widening is not, which makes widening the "
      "one that reaches production.", "auto", "manual", True),
    # --- system-wide -------------------------------------------------------
    K("layer-order-changed", "major", "Layer order changed",
      "Specificity is not what resolves a conflict here — layer order is. "
      "Reordering it re-decides every conflict in the system at once.",
      "auto", "review", False),
    K("note-changed", "patch", "Comment or note changed",
      "The WHY was rewritten. Nothing resolves differently.", "auto", "none", False),
    K("moved", "patch", "Declaration moved file",
      "Same name, same value, different file. Invisible to consumers.",
      "auto", "none", False),
]}

SEVERITY_RANK = {"patch": 0, "minor": 1, "major": 2}


@dataclass
class Change:
    kind: str
    subject: str
    severity: str = ""
    before: str = ""
    after: str = ""
    detail: str = ""
    theme: str = ""
    component: str = ""
    replacement: str = ""
    blast: Dict[str, List[str]] = field(default_factory=dict)
    contrast: List[Dict[str, Any]] = field(default_factory=list)
    deprecation: Optional[Dict[str, Any]] = None

    def __post_init__(self) -> None:
        if not self.severity:
            self.severity = KINDS[self.kind].severity

    @property
    def meta(self) -> Kind:
        return KINDS[self.kind]

    @property
    def title(self) -> str:
        if self.component and self.subject:
            return f"{self.component} · {self.subject}"
        return self.subject or self.component

    def key(self) -> Tuple[int, str, str]:
        return (-SEVERITY_RANK[self.severity], self.kind, self.title)


# ===========================================================================
# 6. THE DIFFER
# ===========================================================================

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
#: Non-text roles that still carry a contrast obligation. SC 1.4.11 asks 3:1 of
#: the *boundary* of a control and of a focus indicator, so a focus ring or a
#: filled button that shifts against the page is exactly as reportable as body
#: text — and it is the half of the obligation teams forget, because no linter
#: calls a border "text".
UI_ROLES = ("--border-focus", "--border-strong", "--border-accent", "--border-invalid",
            "--bg-accent", "--bg-accent-hover", "--bg-danger", "--bg-success",
            "--bg-warning")
UI_SURFACES = ("--bg-canvas", "--bg-surface", "--bg-sunken")   # inputs sit on sunken

TEXT_THRESHOLDS = ((4.5, "body text (SC 1.4.3)"), (3.0, "large text (SC 1.4.3)"))
UI_THRESHOLDS = ((3.0, "UI boundary / focus indicator (SC 1.4.11, 2.4.13)"),)


def detect_renames(old: Snapshot, new: Snapshot,
                   removed: Sequence[str], added: Sequence[str]) -> Dict[str, str]:
    """Pair a vanished name with a new one holding the identical declaration.

    A rename is not recorded anywhere in CSS, so it has to be inferred: a token
    that disappeared and a token that appeared with the SAME raw value, the same
    tier and the same theme overrides is a rename with high confidence. It is
    still a guess, and the report says so — but guessing right here is the
    difference between a migration guide that says "renamed to --fg-faint" and
    one that says "removed", which sends the reader looking for a replacement
    that the tool already knew about.
    """
    out: Dict[str, str] = {}
    used: set = set()
    for gone in removed:
        told = old.tokens[gone]
        best: Optional[str] = None
        for cand in added:
            if cand in used:
                continue
            tnew = new.tokens[cand]
            if tnew.get("raw") != told.get("raw"):
                continue
            if tnew.get("tier") != told.get("tier"):
                continue
            if _override_fingerprint(told) != _override_fingerprint(tnew):
                continue
            best = cand
            break
        if best:
            out[gone] = best
            used.add(best)
    return out


def _override_fingerprint(tok: Dict[str, Any]) -> Tuple[Tuple[str, str, str], ...]:
    return tuple(sorted(
        (str(o.get("context")), str(o.get("label")), str(o.get("value")))
        for o in tok.get("overrides", [])
        if o.get("context") in ("theme", "density", "condition")))


def themes_in_both(old: Snapshot, new: Snapshot) -> List[str]:
    return [t for t in new.themes if t in old.themes]


def downstream(old: Snapshot, new: Snapshot, name: str) -> Dict[str, List[str]]:
    """Every role and component that re-renders because `name` moved.

    Breadth-first over referenced_by, so the report can say which roles read the
    primitive DIRECTLY and which are one more hop away — the difference between
    "check these two" and "check these two and everything they feed".

    The graph is the UNION of both versions. A role that read the primitive
    before and was re-pointed away from it in the same release is still affected
    by the release; reporting only the new graph hides exactly the changes that
    travel together, and those are the ones that surprise people.
    """
    def kids(who: str) -> List[str]:
        out: List[str] = []
        for src in (old, new):
            for k in src.tokens.get(who, {}).get("referenced_by", []):
                if k not in out:
                    out.append(k)
        return sorted(out)

    direct = kids(name)
    seen = set(direct) | {name}
    transitive: List[str] = []
    frontier = list(direct)
    while frontier:
        nxt: List[str] = []
        for role in frontier:
            for child in kids(role):
                if child in seen:
                    continue
                seen.add(child)
                transitive.append(child)
                nxt.append(child)
        frontier = nxt
    comps: List[str] = []
    for src in (old, new):
        for cname, comp in sorted(src.components.items()):
            if cname in comps:
                continue
            reads = set(comp.get("reads_roles") or [])
            for sock in comp.get("sockets", {}).values():
                reads |= set(VAR_REF.findall(str(sock.get("default", ""))))
            if reads & seen:
                comps.append(cname)
    out: Dict[str, List[str]] = {}
    if direct:
        out["roles"] = direct
    if transitive:
        out["transitive"] = sorted(transitive)
    if comps:
        out["components"] = sorted(comps)
    return out


def chain_of(snap: Snapshot, name: str, theme: str, depth: int = 0) -> set:
    """Every token `name` resolves through in one theme."""
    if depth > 24 or name not in snap.tokens:
        return set()
    value = snap.theme_value(name, theme)
    out = set()
    for ref in VAR_REF.findall(value):
        if ref in out:
            continue
        out.add(ref)
        out |= chain_of(snap, ref, theme, depth + 1)
    return out


def contrast_deltas(old: Snapshot, new: Snapshot, rename: Dict[str, str],
                    changed: set) -> List[Dict[str, Any]]:
    """Every text/background pair whose measured ratio moved, and why.

    `changed` is the set of OLD-side token names whose value or re-point moved.
    A pair is reported when either side resolves THROUGH one of them, which is
    what makes a one-line accent edit show up as six ratios instead of none.
    """
    fgs = sorted(n for n, t in new.tokens.items()
                 if n.startswith("--fg-") and t.get("tier") == 2
                 and not n.startswith("--fg-on-"))
    pairs: List[Tuple[str, str, str]] = []
    for fg in fgs:
        for bg in SURFACES:
            if bg in new.tokens:
                pairs.append((fg, bg, "text"))
    pairs.extend((a, b, "text") for a, b in CONTRAST_PAIRS_EXTRA
                 if a in new.tokens and b in new.tokens)
    for fg in UI_ROLES:
        for bg in UI_SURFACES:
            if fg in new.tokens and bg in new.tokens and fg != bg:
                pairs.append((fg, bg, "ui"))

    back = {v: k for k, v in rename.items()}
    rows: List[Dict[str, Any]] = []
    for fg_new, bg_new, role in pairs:
        fg_old, bg_old = back.get(fg_new, fg_new), back.get(bg_new, bg_new)
        if fg_old not in old.tokens or bg_old not in old.tokens:
            continue
        for theme in themes_in_both(old, new):
            a = old.colour(fg_old, theme)
            b = old.colour(bg_old, theme)
            c = new.colour(fg_new, theme)
            d = new.colour(bg_new, theme)
            if not (a and b and c and d):
                continue
            if min(a[2], b[2], c[2], d[2]) < 1.0:
                continue        # translucent: the honest answer is "it depends"
            try:
                before = contrast_ratio_oklch(parse_color(a[0]), parse_color(b[0]))
                after = contrast_ratio_oklch(parse_color(c[0]), parse_color(d[0]))
            except ColorError:
                continue
            if abs(before - after) < 0.005:
                continue
            cause = sorted(
                (chain_of(old, fg_old, theme) | chain_of(old, bg_old, theme)
                 | {fg_old, bg_old}) & changed)
            crossings = []
            for limit, label in (TEXT_THRESHOLDS if role == "text"
                                 else UI_THRESHOLDS):
                if (before >= limit) != (after >= limit):
                    crossings.append({
                        "threshold": limit, "label": label,
                        "direction": "below" if after < limit else "above",
                    })
            rows.append({
                "theme": theme, "fg": fg_new, "bg": bg_new, "role": role,
                "before": round(before, 2), "after": round(after, 2),
                "delta": round(after - before, 2),
                "fg_hex": c[1], "bg_hex": d[1],
                "before_fg_hex": a[1], "before_bg_hex": b[1],
                "crossings": crossings, "caused_by": cause,
            })
    rows.sort(key=lambda r: (not r["crossings"], r["role"] != "text", r["theme"],
                             r["fg"], r["bg"]))
    return rows


def diff_tokens(old: Snapshot, new: Snapshot, out: List[Change],
                inherited: List[str]) -> Tuple[Dict[str, str], set]:
    old_names, new_names = set(old.tokens), set(new.tokens)
    removed = sorted(old_names - new_names)
    added = sorted(new_names - old_names)
    rename = detect_renames(old, new, removed, added)
    renamed_new = set(rename.values())
    changed_values: set = set()

    # Which DECLARATIONS an author actually edited. This is the line between a
    # change and its fallout: --elevation-focus resolves differently because
    # --accent-600 moved, but nobody touched --elevation-focus, and listing it
    # as its own breaking change turns a one-line edit into a six-item
    # changelog that reads like six decisions. It is blast radius, not a change.
    edited: set = {n for n in old_names & new_names
                   if old.tokens[n].get("raw") != new.tokens[n].get("raw")}
    edited |= set(removed) | (set(added) - renamed_new)
    for n in old_names & new_names:
        for theme in themes_in_both(old, new):
            if _theme_override(old.tokens[n], theme) != \
                    _theme_override(new.tokens[n], theme):
                edited.add(n)

    for name in removed:
        tier = old.tier(name)
        if name in rename:
            kind = "tier1-renamed" if tier == 1 else "tier2-renamed"
            ch = Change(kind=kind, subject=name, replacement=rename[name],
                        before=old.display(name), after=new.display(rename[name]),
                        detail=f"every `var({name})` in a consumer resolves to nothing")
        else:
            kind = "tier1-removed" if tier == 1 else "tier2-removed"
            ch = Change(kind=kind, subject=name, before=old.display(name),
                        detail=f"declared at {old.tokens[name].get('file')}"
                               f":{old.tokens[name].get('line')} in the old version")
        ch.blast = downstream(old, new, name)
        out.append(ch)

    for name in added:
        if name in renamed_new:
            continue
        tier = new.tier(name)
        if name.startswith("--bp-"):
            kind = "breakpoint-added"
        else:
            kind = "tier1-added" if tier == 1 else "tier2-added"
        out.append(Change(kind=kind, subject=name, after=new.display(name),
                          detail=new.tokens[name].get("note", "")))

    for name in sorted(old_names & new_names):
        told, tnew = old.tokens[name], new.tokens[name]
        tier = new.tier(name)
        raw_changed = told.get("raw") != tnew.get("raw")
        base_moved = old.display(name) != new.display(name)

        if base_moved and not raw_changed:
            # Resolution moved without an edit here: somebody upstream moved.
            # Suppress it as its own change when that upstream edit is already
            # reported; only a resolution change with no reported cause — which
            # should be impossible — gets promoted to a change of its own.
            if chain_of(new, name, "light") & edited or \
                    chain_of(old, name, "light") & edited:
                inherited.append(name)
                changed_values.add(name)
                continue

        if raw_changed or base_moved:
            if tier == 1:
                kind = "breakpoint-changed" if name.startswith("--bp-") else \
                    "tier1-value-changed"
                ch = Change(kind=kind, subject=name, before=old.display(name),
                            after=new.display(name),
                            detail=f"{told.get('raw')}  ->  {tnew.get('raw')}")
                ch.blast = downstream(old, new, name)
                changed_values.add(name)
                out.append(ch)
            else:
                # Equal means equal everywhere: 24px at the default density
                # and 21px against 24px at compact is a re-point (§11 Q2).
                elsewhere = [] if base_moved else moves_elsewhere(old, new, name)
                same = not base_moved and not elsewhere
                detail = f"{told.get('raw')}  ->  {tnew.get('raw')}"
                if elsewhere:
                    detail += "; " + "; ".join(elsewhere)
                ch = Change(kind="tier2-repointed-equal" if same else "tier2-repointed",
                            subject=name, before=old.display(name),
                            after=new.display(name), detail=detail)
                if not same:
                    ch.blast = downstream(old, new, name)
                    changed_values.add(name)
                out.append(ch)
        elif told.get("note") != tnew.get("note") and (told.get("note") or
                                                       tnew.get("note")):
            out.append(Change(kind="note-changed", subject=name,
                              before=str(told.get("note") or "(none)"),
                              after=str(tnew.get("note") or "(none)")))
        elif told.get("file") and tnew.get("file") and \
                Path(str(told["file"])).name != Path(str(tnew["file"])).name:
            # Basenames, not paths. The two snapshots live in different
            # directories by definition, so comparing full paths reports the
            # whole token file as "moved" on every run.
            out.append(Change(kind="moved", subject=name,
                              before=Path(str(told["file"])).name,
                              after=Path(str(tnew["file"])).name))

    # theme re-points, per theme, on names that survive
    for theme in themes_in_both(old, new):
        if theme == "light":
            continue
        for name in sorted(old_names & new_names):
            a = _theme_override(old.tokens[name], theme)
            b = _theme_override(new.tokens[name], theme)
            if a == b:
                continue
            before = old.display(name, theme)
            after = new.display(name, theme)
            if a is None:
                kind = "theme-override-added"
            elif b is None:
                kind = "theme-override-removed"
            else:
                kind = "theme-override-changed"
            severity = "patch" if before == after else ""
            ch = Change(kind=kind, subject=name, theme=theme, severity=severity,
                        before=before, after=after,
                        detail=f"[data-theme=\"{theme}\"]  {a or '(inherits root)'}"
                               f"  ->  {b or '(inherits root)'}")
            if before != after:
                changed_values.add(name)
                ch.blast = downstream(old, new, name)
            out.append(ch)

    for theme in new.themes:
        if theme not in old.themes:
            out.append(Change(kind="theme-added", subject=theme))
    for theme in old.themes:
        if theme not in new.themes:
            out.append(Change(kind="theme-removed", subject=theme))

    diff_densities(old, new, out)
    diff_conditions(old, new, out)
    return rename, changed_values


def diff_densities(old: Snapshot, new: Snapshot, out: List[Change]) -> None:
    """Density overrides on names that survive, per density in both versions.

    An added, changed or removed override is one change, major unless nothing
    resolves differently at that density. The roles that move with it (a
    padding that multiplies --density) are its blast radius, quoted in the
    detail, not changes of their own.
    """
    both = set(old.tokens) & set(new.tokens)
    for density in densities_in_both(old, new):
        for name in sorted(both):
            a = _override(old.tokens[name], "density", density)
            b = _override(new.tokens[name], "density", density)
            if a == b:
                continue
            before = old.at_density(name, density)
            after = new.at_density(name, density)
            blast = downstream(old, new, name)
            moved = [f"{n} {old.at_density(n, density)} -> {new.at_density(n, density)}"
                     for n in blast.get("roles", []) + blast.get("transitive", [])
                     if n in both and old.at_density(n, density) != new.at_density(n, density)]
            detail = (f"[data-density=\"{density}\"]  {a or '(inherits root)'}"
                      f"  ->  {b or '(inherits root)'}")
            if moved:
                detail += "; moves " + ", ".join(moved)
            severity = "patch" if before == after and not moved else ""
            ch = Change(kind="density-changed", subject=name, severity=severity,
                        before=before, after=after, detail=detail)
            if not severity:
                ch.blast = blast
            out.append(ch)
    for density in new.densities:
        if density not in old.densities:
            out.append(Change(kind="density-added", subject=density))
    for density in old.densities:
        if density not in new.densities:
            out.append(Change(kind="density-removed", subject=density))


def diff_conditions(old: Snapshot, new: Snapshot, out: List[Change]) -> None:
    """Overrides under a media condition (reduced motion, forced colours, more
    contrast), on names that survive. A condition is not opted into the way a
    theme is: every user with the setting gets it, so an added one is as much
    a render change as an edited one."""
    both = set(old.tokens) & set(new.tokens)
    labels = sorted(set(old.condition_labels()) | set(new.condition_labels()))
    for label in labels:
        for name in sorted(both):
            a = _override(old.tokens[name], "condition", label)
            b = _override(new.tokens[name], "condition", label)
            if a == b:
                continue
            out.append(Change(
                kind="condition-changed", subject=name,
                before=a if a is not None else f"{old.display(name)} (root)",
                after=b if b is not None else f"{new.display(name)} (root)",
                detail=f"[{label}]  {a or '(inherits root)'}  ->  {b or '(inherits root)'}"))


def densities_in_both(old: Snapshot, new: Snapshot) -> List[str]:
    return [d for d in new.densities if d in old.densities]


def moves_elsewhere(old: Snapshot, new: Snapshot, name: str) -> List[str]:
    """Where `name` resolves differently outside the default theme and density:
    another theme, a density, or a media condition a user can have."""
    out = [f"{theme} {old.display(name, theme)} -> {new.display(name, theme)}"
           for theme in themes_in_both(old, new) if theme != "light"
           and old.display(name, theme) != new.display(name, theme)]
    out += [f"{density} {old.at_density(name, density)} -> {new.at_density(name, density)}"
            for density in densities_in_both(old, new)
            if old.at_density(name, density) != new.at_density(name, density)]
    for label in sorted(set(old.condition_labels()) | set(new.condition_labels())):
        before, after = old.at_condition(name, label), new.at_condition(name, label)
        if before != after:
            out.append(f"[{label}] {before} -> {after}")
    return out


def _override(tok: Dict[str, Any], context: str, label: str) -> Optional[str]:
    for ov in tok.get("overrides", []):
        if ov.get("context") == context and ov.get("label") == label:
            return str(ov.get("value"))
    return None


def _theme_override(tok: Dict[str, Any], theme: str) -> Optional[str]:
    return _override(tok, "theme", theme)


def diff_components(old: Snapshot, new: Snapshot, out: List[Change]) -> None:
    if not (old.has_components or new.has_components):
        return
    old_names, new_names = set(old.components), set(new.components)
    for name in sorted(old_names - new_names):
        out.append(Change(kind="component-removed", subject=name,
                          detail=f"was {old.components[name].get('file')}"))
    for name in sorted(new_names - old_names):
        out.append(Change(kind="component-added", subject=name,
                          detail=f"{new.components[name].get('file')}"))
    for name in sorted(old_names & new_names):
        a, b = old.components[name], new.components[name]
        # Only where both snapshots read the props file: there, an empty
        # element is a root no single tag renders (a fragment), not an unknown.
        if (a.get("prop_file") and b.get("prop_file")
                and a.get("element", "") != b.get("element", "")):
            shown = [f"<{e}>" if e else "(no single root element)"
                     for e in (a.get("element", ""), b.get("element", ""))]
            out.append(Change(kind="element-changed", subject="element", component=name,
                              before=str(a.get("element") or shown[0]),
                              after=str(b.get("element") or shown[1]),
                              detail=f"{shown[0]}  ->  {shown[1]}"))
        # Equal in every theme, not only the default one.
        _diff_map(a["sockets"], b["sockets"], name, out, "socket-added",
                  "socket-removed", value=lambda s: str(s.get("default", "")),
                  resolved=lambda s: json.dumps(s.get("resolved") or {}, sort_keys=True),
                  changed_kind="socket-default-changed",
                  equal_kind="socket-default-equal")
        _diff_map(a["variants"], b["variants"], name, out, "variant-added",
                  "variant-removed", value=lambda v: json.dumps(v.get("sets", {}),
                                                                sort_keys=True),
                  changed_kind="variant-changed")
        _diff_map(a["sizes"], b["sizes"], name, out, "size-added", "size-removed",
                  value=lambda v: json.dumps(v.get("sets", {}), sort_keys=True),
                  changed_kind="variant-changed")
        _diff_map(a["states"], b["states"], name, out, "state-added", "state-removed",
                  value=lambda s: json.dumps(
                      {"sets": s.get("sets", {}), "declares": s.get("declares", {})},
                      sort_keys=True),
                  changed_kind="variant-changed")
        parts_a, parts_b = dict(a["parts"]), dict(b["parts"])
        if a.get("module") and b.get("module"):
            for gone, came in local_renames(parts_a, parts_b):
                out.append(Change(kind="part-renamed-local", subject=gone, component=name,
                                  before=gone, after=came,
                                  detail=f"{b.get('file')}: .{gone} -> .{came}, "
                                         f"the same declarations"))
                del parts_a[gone], parts_b[came]
        _diff_map(parts_a, parts_b, name, out, "part-added", "part-removed")
        _diff_props(a["props"], b["props"], name, out)


def local_renames(a: Dict[str, Any], b: Dict[str, Any]) -> List[Tuple[str, str]]:
    """Pairs (old class, new class) under CSS Modules: a part that went and one
    that came, declaring the same properties with the same values, each the
    other's only match. A removal with no such partner is still a removed
    element, and so is every part of a snapshot from before 3.4.0, which
    recorded the properties but not their values."""
    gone = [k for k in a if k not in b and "declares" in a[k]]
    came = [k for k in b if k not in a and "declares" in b[k]]

    def shape(part: Dict[str, Any]) -> str:
        return json.dumps(part.get("declares"), sort_keys=True)

    pairs = []
    for old_key in sorted(gone):
        hits = [k for k in came if shape(b[k]) == shape(a[old_key])]
        rivals = [k for k in gone if shape(a[k]) == shape(a[old_key])]
        if len(hits) == 1 and len(rivals) == 1:
            pairs.append((old_key, hits[0]))
    return pairs


def _diff_map(a: Dict[str, Any], b: Dict[str, Any], comp: str, out: List[Change],
              added_kind: str, removed_kind: str, *, value=None, resolved=None,
              changed_kind: str = "", equal_kind: str = "") -> None:
    for key in sorted(set(a) - set(b)):
        out.append(Change(kind=removed_kind, subject=key, component=comp))
    for key in sorted(set(b) - set(a)):
        out.append(Change(kind=added_kind, subject=key, component=comp))
    if not (value and changed_kind):
        return
    for key in sorted(set(a) & set(b)):
        before, after = value(a[key]), value(b[key])
        if before == after:
            continue
        kind = changed_kind
        if equal_kind and resolved and resolved(a[key]) == resolved(b[key]):
            kind = equal_kind
        out.append(Change(kind=kind, subject=key, component=comp,
                          before=before, after=after))


def _diff_props(a: Dict[str, Any], b: Dict[str, Any], comp: str,
                out: List[Change]) -> None:
    for key in sorted(set(a) - set(b)):
        out.append(Change(kind="prop-removed", subject=key, component=comp,
                          before=str(a[key].get("type", ""))))
    for key in sorted(set(b) - set(a)):
        kind = ("prop-added-optional" if b[key].get("optional")
                else "prop-added-required")
        out.append(Change(kind=kind, subject=key, component=comp,
                          after=str(b[key].get("type", ""))))
    for key in sorted(set(a) & set(b)):
        pa, pb = a[key], b[key]
        if str(pa.get("type", "")) != str(pb.get("type", "")):
            out.append(Change(kind="prop-type-changed", subject=key, component=comp,
                              before=str(pa.get("type")), after=str(pb.get("type"))))
        if pa.get("default") != pb.get("default"):
            out.append(Change(kind="prop-default-changed", subject=key,
                              component=comp, before=str(pa.get("default")),
                              after=str(pb.get("default"))))
        if pa.get("optional") and not pb.get("optional"):
            out.append(Change(kind="prop-added-required", subject=key, component=comp,
                              detail="was optional, is now required"))


def diff_layers(old: Snapshot, new: Snapshot, out: List[Change]) -> Optional[str]:
    stale = [s.label for s in (old, new) if not s.layers_recorded]
    if stale:
        return ("layer order was not compared — the " + " and ".join(stale)
                + (" system.json predates" if len(stale) == 1 else " system.json files predate")
                + " 3.4.0, which did not record it. Re-run "
                "extract_system over the entry stylesheet too (the one with the "
                "`@layer a, b, c;` statement), or diff that file by eye; a "
                "reorder is a major change.")
    if not old.layers or not new.layers:
        return ("layer order was not compared — "
                + ("neither snapshot carries" if not (old.layers or new.layers)
                   else f"the {'old' if not old.layers else 'new'} snapshot lacks")
                + " an `@layer a, b, c;` order statement. It lives in the entry "
                "stylesheet, not in tokens.css: snapshot that file too. A reorder "
                "is a major change.")
    if old.layers != new.layers:
        out.append(Change(kind="layer-order-changed", subject="@layer",
                          before=" | ".join(old.layers),
                          after=" | ".join(new.layers)))
    return None


# ===========================================================================
# 7. THE LEDGER AND THE GATE
# ===========================================================================


def load_ledger(path: Optional[str]) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    if not path:
        return [], None
    p = Path(path)
    if not p.exists():
        return [], f"no deprecation ledger at {p}"
    try:
        data = json.loads(p.read_bytes())
    except (OSError, json.JSONDecodeError) as exc:
        raise bail(f"diff_system: {p} is not readable JSON ({exc}).")
    if str(data.get("schema", "")).split("@")[0] != LEDGER_SCHEMA.split("@")[0]:
        raise bail(
            f"diff_system: {p} is not a deprecation ledger "
            f"(schema={data.get('schema')!r}). Create one with:\n"
            f"  python -m scripts.deprecate add --name <NAME> --kind token …")
    return list(data.get("deprecations", [])), None


def attach_deprecations(changes: Sequence[Change],
                        ledger: Sequence[Dict[str, Any]]) -> None:
    index: Dict[str, Dict[str, Any]] = {}
    for entry in ledger:
        index[str(entry.get("name", ""))] = entry
    for ch in changes:
        key = ch.subject
        if ch.component and key in index:
            pass
        ch.deprecation = index.get(key)


def gate_failures(changes: Sequence[Change], mode: str) -> List[Change]:
    if mode == "none":
        return []
    out = []
    for ch in changes:
        if ch.severity != "major":
            continue
        if mode == "names" and not ch.meta.gate:
            continue
        if ch.deprecation is None:
            out.append(ch)
    return out


# ===========================================================================
# 8. VERSIONS
# ===========================================================================

SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:[-+].*)?$")


def bump(version: Optional[str], level: str) -> str:
    if not version:
        return {"major": "<next major>", "minor": "<next minor>",
                "patch": "<next patch>"}[level]
    m = SEMVER.match(version.strip().lstrip("v"))
    if not m:
        raise bail(f"diff_system: --from-version {version!r} is not semver "
                         f"(expected MAJOR.MINOR.PATCH).")
    a, b, c = (int(x) for x in m.groups())
    if level == "major":
        return f"{a + 1}.0.0" if a else "1.0.0"
    if level == "minor":
        return f"{a}.{b + 1}.0"
    return f"{a}.{b}.{c + 1}"


def recommend(changes: Sequence[Change]) -> Tuple[str, Optional[Change]]:
    if not changes:
        return "patch", None
    best = max(changes, key=lambda c: (SEVERITY_RANK[c.severity],
                                       c.meta.gate, -len(c.title)))
    return best.severity, best


PRE_1_0_NOTE = (
    "Below 1.0.0 semver gives you no promise to break: 0.x.y may change anything. "
    "Use it anyway — the discipline of deciding is the point, and the day you "
    "ship 1.0.0 the habit already exists."
)


# ===========================================================================
# 9. RENDERERS
# ===========================================================================


def _rule(title: str) -> str:
    return f"{title}\n" + "=" * max(24, len(title))


def render_report(res: Dict[str, Any], changes: Sequence[Change],
                  contrast: Sequence[Dict[str, Any]], notes: Sequence[str]) -> str:
    out: List[str] = []
    out.append(_rule("DESIGN SYSTEM DIFF"))
    out.append(f"  old   {res['old']['path']}   ({res['old']['tokens']} tokens, "
               f"{res['old']['components']} components · {res['old']['impl']})")
    out.append(f"  new   {res['new']['path']}   ({res['new']['tokens']} tokens, "
               f"{res['new']['components']} components · {res['new']['impl']})")
    out.append("")
    bump_level = res["bump"]["level"]
    out.append(f"  RECOMMENDED BUMP   {bump_level.upper()}   "
               f"{res['version']['from']} -> {res['version']['to']}")
    if res["bump"]["reason"]:
        out.append(f"  because            {res['bump']['reason']}")
    counts = res["counts"]
    out.append(f"  changes            {counts['major']} major · "
               f"{counts['minor']} minor · {counts['patch']} patch")
    out.append("")

    for level in ("major", "minor", "patch"):
        group = [c for c in changes if c.severity == level]
        if not group:
            continue
        heading = {"major": "BREAKING (major)", "minor": "ADDITIVE (minor)",
                   "patch": "INVISIBLE (patch)"}[level]
        out.append(_rule(f"{heading} — {len(group)}"))
        for ch in sorted(group, key=lambda c: c.key()):
            head = f"  [{ch.kind}]  {ch.title}"
            if ch.replacement:
                head += f"  ->  {ch.replacement}"
            out.append(head)
            if ch.theme:
                out.append(f"      theme        {ch.theme}")
            if ch.before or ch.after:
                label = "note" if ch.kind == "note-changed" else "value"
                out.append(f"      {label:<13}{ch.before or '(none)'}  ->  "
                           f"{ch.after or '(none)'}")
            if ch.detail:
                out.append(f"      detail       {ch.detail}")
            out.append(f"      consumer     {ch.meta.why}")
            if ch.blast:
                for label in ("roles", "transitive", "components"):
                    if ch.blast.get(label):
                        items = ch.blast[label]
                        shown = ", ".join(items[:8])
                        if len(items) > 8:
                            shown += f", … (+{len(items) - 8})"
                        out.append(f"      blast·{label:<11}{len(items):>3}  {shown}")
            if ch.meta.gate:
                if ch.deprecation:
                    dep = ch.deprecation
                    out.append(f"      deprecation  recorded, since "
                               f"{dep.get('since', '?')}, removal "
                               f"{dep.get('removal', '?')}")
                else:
                    out.append("      deprecation  MISSING — this is what the gate "
                               "fails on")
            out.append("")
        out.append("")

    if contrast:
        out.append(_rule(f"CONTRAST — {len(contrast)} pair(s) moved"))
        out.append(f"  {'theme':<7}{'pair':<42}{'before':>9}{'after':>9}  verdict")
        for row in contrast:
            pair = f"{row['fg']} on {row['bg']}"
            verdict = "moved, no threshold crossed"
            if row["crossings"]:
                cross = row["crossings"][0]
                verdict = (f"CROSSED {cross['threshold']}:1 "
                           f"{'DOWNWARD' if cross['direction'] == 'below' else 'upward'}"
                           f" — {cross['label']}")
            out.append(f"  {row['theme']:<7}{pair:<42}{row['before']:>7.2f}:1"
                       f"{row['after']:>7.2f}:1  {verdict}")
            if row["caused_by"]:
                out.append(f"  {'':<7}caused by {', '.join(row['caused_by'])}")
        out.append("")

    if notes:
        out.append(_rule("NOTES"))
        for n in notes:
            out.append(f"  · {n}")
        out.append("")

    gate = res["gate"]
    out.append(_rule("GATE"))
    out.append(f"  mode         {gate['mode']}"
               + ("" if gate["binding"] else
                  "   (ADVISORY — pass --deprecations to make it binding)"))
    if gate["mode"] == "none":
        out.append("  result       skipped (--gate none)")
    elif not gate["failures"]:
        out.append(f"  result       PASS — {gate['checked']} breaking change(s) "
                   f"checked, every one carries a deprecation record")
    else:
        out.append(f"  result       FAIL — {len(gate['failures'])} breaking "
                   f"change(s) with no deprecation record:")
        for name in gate["failures"]:
            out.append(f"                 {name}")
        out.append("")
        out.append("  Record each one before you ship it:")
        for name in gate["failures"][:4]:
            out.append(f"    python -m scripts.deprecate add --name={name} "
                       f"--kind <kind> \\")
            out.append(f"        --since <this version> --removal <target> "
                       f"--replacement <new name> --reason '…'")
    out.append("")
    return "\n".join(out)


CHANGELOG_SECTIONS = [
    ("Removed", {"tier1-removed", "tier2-removed", "socket-removed",
                 "component-removed", "variant-removed", "size-removed",
                 "state-removed", "part-removed", "prop-removed", "theme-removed",
                 "theme-override-removed", "density-removed",
                 # A rename removes the name a consumer greps for. Filing it
                 # under "Changed" is how someone scanning for what broke misses
                 # the one line that did.
                 "tier1-renamed", "tier2-renamed", "component-renamed"}),
    ("Added", {"tier1-added", "tier2-added", "socket-added", "component-added",
               "variant-added", "size-added", "state-added", "part-added",
               "prop-added-optional", "prop-added-required", "theme-added",
               "breakpoint-added", "density-added"}),
    # An added theme override is a re-point in that theme, so it is filed
    # under Changed with the other re-points.
    ("Changed", None),      # everything else
]


def render_changelog(res: Dict[str, Any], changes: Sequence[Change],
                     contrast: Sequence[Dict[str, Any]], project: str,
                     date: str, ledger: Sequence[Dict[str, Any]] = ()) -> str:
    out: List[str] = []
    version = res["version"]["to"]
    out.append(f"## [{version}] - {date}")
    out.append("")
    breaking = [c for c in changes if c.severity == "major"]
    if breaking:
        out.append(f"**Breaking.** {len(breaking)} change(s) alter rendered output "
                   f"or remove a published name. Read `UPGRADE-{version}.md` before "
                   f"you bump — the codemod does most of it.")
        out.append("")
    claimed: set = set()
    for title, kinds in CHANGELOG_SECTIONS:
        if kinds is None:
            group = [c for c in changes if id(c) not in claimed]
        else:
            group = [c for c in changes if c.kind in kinds]
            claimed |= {id(c) for c in group}
        if not group:
            continue
        out.append(f"### {title}")
        out.append("")
        for ch in sorted(group, key=lambda c: c.key()):
            out.append(_changelog_line(ch))
        out.append("")
    announced = [d for d in ledger
                 if str(d.get("since", "")) == version
                 and str(d.get("status", "active")) == "active"]
    if announced:
        out.append("### Deprecated")
        out.append("")
        for dep in sorted(announced, key=lambda d: str(d.get("name"))):
            line = (f"- `{dep.get('name')}` — still works, removed in "
                    f"`{dep.get('removal', 'a future major')}`.")
            if dep.get("replacement"):
                line += f" Use `{dep['replacement']}`."
            if dep.get("reason"):
                line += f" {dep['reason']}"
            out.append(line)
        out.append("")
    crossings = [r for r in contrast if r["crossings"]]
    if crossings:
        out.append("### Accessibility")
        out.append("")
        for row in crossings:
            cross = row["crossings"][0]
            direction = ("no longer meets" if cross["direction"] == "below"
                         else "now meets")
            out.append(f"- `{row['fg']}` on `{row['bg']}` ({row['theme']}) "
                       f"{direction} {cross['threshold']}:1 for {cross['label']} — "
                       f"{row['before']}:1 → {row['after']}:1.")
        out.append("")
    return "\n".join(out)


def _changelog_line(ch: Change) -> str:
    mark = "**BREAKING** " if ch.severity == "major" else ""
    name = f"`{ch.subject}`"
    if ch.component:
        name = f"`{ch.component}` — `{ch.subject}`"
    body = f"- {mark}{name}: {ch.meta.label.lower()}."
    if ch.replacement:
        body += f" Use `{ch.replacement}` instead."
    if (ch.before and ch.after and ch.before != ch.after
            and ch.kind not in ("note-changed", "moved")):
        body += f" {ch.before} → {ch.after}."
    if ch.blast.get("roles"):
        roles = ch.blast["roles"]
        shown = ", ".join(f"`{r}`" for r in roles[:6])
        if len(roles) > 6:
            shown += f" and {len(roles) - 6} more"
        body += f" Downstream: {shown}."
    if ch.kind == "note-changed":
        body += " Comment only; nothing resolves differently."
    return body


def render_migration_guide(res: Dict[str, Any], changes: Sequence[Change],
                           contrast: Sequence[Dict[str, Any]], project: str,
                           mapping_path: str) -> str:
    version = res["version"]["to"]
    frm = res["version"]["from"]
    breaking = sorted([c for c in changes if c.severity == "major"],
                      key=lambda c: c.key())
    minor = [c for c in changes if c.severity == "minor"]
    out: List[str] = []
    out.append(f"# Upgrading {project} to {version}")
    out.append("")
    if not breaking:
        out.append(f"Nothing in {version} changes what your pages render. Bump the "
                   f"version, run the gate, move on.")
        out.append("")
    else:
        out.append(f"{frm} → {version} makes **{len(breaking)} breaking "
                   f"change(s)**. Breaking here means *your rendered output moves "
                   f"even if you change nothing* — not only that a name went away. "
                   f"Budget an hour, not a sprint: most of the work below is one "
                   f"codemod and one look at a visual diff.")
        out.append("")
        out.append("## Do this, in this order")
        out.append("")
        out.append("```bash")
        out.append("git checkout -b upgrade/design-system-" + version)
        out.append(f"# 1. pin the new version (never `latest`)")
        out.append(f"npm install @your-org/design-system@{version} --save-exact")
        out.append("# 2. the mechanical part")
        out.append(f"python -m scripts.apply_codemod ./src --mapping {mapping_path}")
        out.append(f"python -m scripts.apply_codemod ./src --mapping {mapping_path} "
                   f"--apply")
        out.append("# 3. the gate that proves the code is still legal")
        out.append("python -m scripts.audit_design src/ --strict")
        out.append("# 4. the gate that proves the PIXELS are still right")
        out.append("node scripts/snapshot_matrix.mjs build/proof-sheet.html \\")
        out.append("     --baselines tests/visual/baselines --out build/matrix-report")
        out.append("```")
        out.append("")
        out.append("Step 4 is the acceptance test, not step 3. A design-system "
                   "upgrade that type-checks and lints clean can still be visually "
                   "wrong — that is the normal case, not the exotic one.")
        out.append("")

    for i, ch in enumerate(breaking, 1):
        out.append(f"## {i}. `{ch.title}`")
        out.append("")
        moved = (f" {ch.before} → {ch.after}."
                 if ch.before and ch.after and ch.before != ch.after else "")
        out.append(f"**What changed.** {ch.meta.label}."
                   + (f" `{ch.subject}` → `{ch.replacement}`." if ch.replacement else "")
                   + moved)
        out.append("")
        out.append(f"**What you will see if you skip it.** {ch.meta.why}")
        out.append("")
        mine = [r for r in contrast
                if ch.subject in r["caused_by"] and r["crossings"]]
        for row in mine:
            cross = row["crossings"][0]
            verb = ("no longer meets" if cross["direction"] == "below"
                    else "now meets")
            out.append(f"**Accessibility.** `{row['fg']}` on `{row['bg']}` "
                       f"({row['theme']}) {verb} {cross['threshold']}:1 for "
                       f"{cross['label']} — {row['before']}:1 → {row['after']}:1. "
                       + ("Fix it in your own theme or accept it deliberately; "
                          "it will not fix itself."
                          if cross["direction"] == "below" else
                          "This one is the reason the change was made."))
            out.append("")
        if ch.blast:
            parts = []
            nouns = {"roles": ("role", "roles"),
                     "transitive": ("role one hop further",
                                    "roles one hop further"),
                     "components": ("component", "components")}
            for label in ("roles", "transitive", "components"):
                items = ch.blast.get(label) or []
                if not items:
                    continue
                noun = nouns[label][0 if len(items) == 1 else 1]
                parts.append(f"{len(items)} {noun} "
                             f"({', '.join('`%s`' % x for x in items[:6])}"
                             + (", …" if len(items) > 6 else "") + ")")
            out.append(f"**Blast radius.** {'; '.join(parts)}.")
            out.append("")
        dep = ch.deprecation or {}
        if ch.meta.burden == "codemod" and ch.replacement:
            out.append("**Do this.**")
            out.append("")
            out.append("```bash")
            out.append(f"python -m scripts.apply_codemod ./src --mapping "
                       f"{mapping_path} --kind {dep.get('kind_hint', 'color')}")
            out.append("```")
            out.append("")
            if dep.get("removal"):
                out.append(f"`{ch.subject}` still works in {version} as an alias and "
                           f"is removed in {dep['removal']}. You have one minor "
                           f"version; do not spend it.")
                out.append("")
        elif ch.meta.burden == "review":
            out.append("**Do this.** Nothing mechanical — this one is a look, not "
                       "an edit. Re-run your visual baselines and accept or reject "
                       "the diff deliberately.")
            out.append("")
        else:
            out.append("**Do this.** By hand. There is no mechanical rule; see the "
                       "note below for what the replacement expects.")
            out.append("")
        if dep.get("reason"):
            out.append(f"**Why we did it.** {dep['reason']}")
            out.append("")
        if dep.get("notes"):
            out.append(f"**Note.** {dep['notes']}")
            out.append("")

    crossings = [r for r in contrast if r["crossings"]]
    if crossings:
        out.append("## Contrast that crossed a WCAG threshold")
        out.append("")
        out.append("| Theme | Pair | Before | After | Verdict |")
        out.append("|---|---|---|---|---|")
        for row in crossings:
            cross = row["crossings"][0]
            verdict = (f"**fails {cross['threshold']}:1** — {cross['label']}"
                       if cross["direction"] == "below"
                       else f"now passes {cross['threshold']}:1")
            out.append(f"| {row['theme']} | `{row['fg']}` on `{row['bg']}` | "
                       f"{row['before']}:1 | {row['after']}:1 | {verdict} |")
        out.append("")
        out.append("A pair that crossed **downward** is a regression this release "
                   "introduced into your product, not a warning about ours. If you "
                   "override either role, re-measure yours:")
        out.append("")
        out.append("```bash")
        out.append("python -m scripts.generate_color_ramp --check '<fg>' '<bg>'")
        out.append("```")
        out.append("")

    if minor:
        out.append("## New, optional")
        out.append("")
        for ch in sorted(minor, key=lambda c: c.key()):
            out.append(f"- `{ch.title}` — {ch.meta.label.lower()}."
                       + (f" {ch.after}." if ch.after else ""))
        out.append("")

    out.append("## When you are done")
    out.append("")
    out.append("Commit the codemod, the baseline updates and the version bump "
               "**together**. A baseline update on its own is unreviewable; "
               "alongside its cause it reads as \"this changed, so these fourteen "
               "images changed\".")
    out.append("")
    return "\n".join(out)


# ===========================================================================
# 10. CLI
# ===========================================================================


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="python -m scripts.diff_system",
        description="Classify every change between two design-system snapshots, "
                    "compute the blast radius and the contrast delta, and "
                    "recommend a semver bump.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python -m scripts.diff_system v1/system.json v2/system.json
  python -m scripts.diff_system old/tokens.css new/tokens.css --from-version 1.4.2
  python -m scripts.diff_system a.json b.json --format changelog -o CHANGELOG.part.md
  python -m scripts.diff_system a.json b.json --format migration-guide \\
      --from-version 1.4.2 -o docs/UPGRADE.md
  python -m scripts.diff_system a.json b.json --deprecations deprecations.json
""")
    ap.add_argument("old", help="the published snapshot: system.json, tokens.css "
                                "or a directory containing one")
    ap.add_argument("new", help="the candidate snapshot, same forms")
    ap.add_argument("--format", choices=("report", "json", "changelog",
                                         "migration-guide"),
                    default="report", help="output shape (default: report)")
    ap.add_argument("-o", "--out", metavar="FILE",
                    help="write there instead of stdout")
    ap.add_argument("--from-version", metavar="X.Y.Z",
                    help="the version `old` was published as; enables a real "
                         "recommended version instead of a placeholder")
    ap.add_argument("--project", default="the design system", metavar="NAME",
                    help="name used in the changelog and migration guide")
    ap.add_argument("--date", metavar="YYYY-MM-DD",
                    help="release date for the changelog (default: today)")
    ap.add_argument("--deprecations", metavar="FILE",
                    help="deprecations.json ledger; enables the gate")
    ap.add_argument("--mapping", default="design-system/mapping.json",
                    metavar="PATH",
                    help="codemod mapping path quoted in the migration guide")
    ap.add_argument("--gate", choices=("names", "major", "none"), default="names",
                    help="names: a vanished name with no ledger record fails "
                         "(default). major: every breaking change must carry a "
                         "record. none: never fail.")
    ap.add_argument("--no-contrast", action="store_true",
                    help="skip the contrast pass")
    ap.add_argument("--no-upstream", action="store_true",
                    help="use the vendored token parser even when "
                         "design-system-docs is reachable")
    ap.add_argument("--color-impl", metavar="PATH",
                    help="path to web-design-studio's generate_color_ramp.py")
    ap.add_argument("--check-color-impl", action="store_true",
                    help="verify the vendored colour math against the studio's "
                         "and exit")
    return ap


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = build_parser()
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--check-color-impl" in argv:
        upstream = _find_upstream(None)
        for i, a in enumerate(argv):
            if a == "--color-impl" and i + 1 < len(argv):
                upstream = _find_upstream(argv[i + 1])
        if upstream is None:
            print("No upstream generate_color_ramp.py found; nothing to check "
                  "against.", file=sys.stderr)
            return 2
        problems = use_upstream_color_impl(upstream, verify=True)
        if problems:
            print("Colour implementations DISAGREE:", file=sys.stderr)
            for p in problems:
                print(f"  {p}", file=sys.stderr)
            return 1
        print(f"Vendored colour math agrees with {upstream} on "
              f"{len(COLOR_PROBES)} probe pairs.")
        return 0

    args = ap.parse_args(argv)

    upstream = _find_upstream(args.color_impl)
    if upstream is not None:
        try:
            for p in use_upstream_color_impl(upstream, verify=True):
                print(f"warning: colour implementations disagree: {p}",
                      file=sys.stderr)
        except Exception as exc:                        # noqa: BLE001
            print(f"warning: falling back to vendored colour math ({exc})",
                  file=sys.stderr)

    old = load_snapshot(args.old, "old", no_upstream=args.no_upstream)
    new = load_snapshot(args.new, "new", no_upstream=args.no_upstream)

    changes: List[Change] = []
    inherited: List[str] = []
    rename, changed_values = diff_tokens(old, new, changes, inherited)
    diff_components(old, new, changes)
    notes: List[str] = []
    layer_note = diff_layers(old, new, changes)
    if layer_note:
        notes.append(layer_note)
    if old.has_components != new.has_components:
        notes.append("one snapshot carries components and the other does not — "
                     "component-level changes were not compared")
    elif not new.has_components:
        notes.append("neither snapshot carries components; only the token layer "
                     "was compared. Snapshot with extract_system.py over your "
                     "component CSS to widen this.")
    if inherited:
        shown = ", ".join(sorted(inherited)[:8])
        if len(inherited) > 8:
            shown += f", … (+{len(inherited) - 8})"
        notes.append(f"{len(inherited)} token(s) resolve differently without a "
                     f"declaration change — they are the blast radius above, not "
                     f"separate decisions: {shown}")
    if rename:
        notes.append("rename detection is a heuristic: a vanished name and a new "
                     "name holding an identical declaration. Confirm each one — "
                     + ", ".join(f"{k} -> {v}" for k, v in sorted(rename.items())))

    contrast = ([] if args.no_contrast
                else contrast_deltas(old, new, rename, changed_values))

    ledger, ledger_note = load_ledger(args.deprecations)
    if ledger_note:
        notes.append(ledger_note)
    attach_deprecations(changes, ledger)
    failures = gate_failures(changes, args.gate)
    checked = [c for c in changes if c.severity == "major"
               and (args.gate == "major" or c.meta.gate)]
    # The ledger is the contract. Without one there is nothing to check against,
    # so the gate reports and does not fail — otherwise every first run of this
    # script on a real release exits 1 and gets wrapped in `|| true`, which is
    # how a gate dies.
    binding = bool(args.deprecations)

    level, cause = recommend(changes)
    counts = {lvl: sum(1 for c in changes if c.severity == lvl)
              for lvl in ("major", "minor", "patch")}
    date = args.date or _dt.date.today().isoformat()

    res: Dict[str, Any] = {
        "schema": SCHEMA,
        "old": {"path": old.path, "impl": old.impl, "source": old.source,
                "tokens": len(old.tokens), "components": len(old.components),
                "themes": old.themes},
        "new": {"path": new.path, "impl": new.impl, "source": new.source,
                "tokens": len(new.tokens), "components": len(new.components),
                "themes": new.themes},
        "version": {"from": args.from_version or "<current>",
                    "to": bump(args.from_version, level)},
        "bump": {"level": level,
                 "reason": (f"{cause.meta.label.lower()}: {cause.title}"
                            if cause else "nothing changed")},
        "counts": counts,
        "renames": rename,
        "changes": [{
            "kind": c.kind, "severity": c.severity, "subject": c.subject,
            "component": c.component, "theme": c.theme,
            "replacement": c.replacement, "before": c.before, "after": c.after,
            "detail": c.detail, "why": c.meta.why, "detect": c.meta.detect,
            "burden": c.meta.burden, "gated": c.meta.gate, "blast": c.blast,
            "deprecation": c.deprecation,
        } for c in sorted(changes, key=lambda c: c.key())],
        "contrast": contrast,
        "notes": list(notes),
        "gate": {"mode": args.gate, "binding": binding,
                 "checked": len(checked),
                 "failures": [c.title for c in failures]},
        "meta": {"color_impl": COLOR_IMPL},
    }
    if not args.from_version:
        res["notes"].append("pass --from-version to get a real version number. "
                            + PRE_1_0_NOTE)
        notes = res["notes"]

    ordered = sorted(changes, key=lambda c: c.key())
    if args.format == "json":
        text = json.dumps(res, indent=2, ensure_ascii=False) + "\n"
    elif args.format == "changelog":
        text = render_changelog(res, ordered, contrast, args.project, date,
                                ledger)
    elif args.format == "migration-guide":
        text = render_migration_guide(res, ordered, contrast, args.project,
                                      args.mapping)
    else:
        text = render_report(res, ordered, contrast, notes)

    if args.out:
        outp = Path(args.out)
        outp.parent.mkdir(parents=True, exist_ok=True)
        outp.write_text(text, encoding="utf-8")
        print(f"wrote {outp} — {counts['major']} major, {counts['minor']} minor, "
              f"{counts['patch']} patch; recommended bump: {level}", file=sys.stderr)
    else:
        sys.stdout.write(text if text.endswith("\n") else text + "\n")

    return 1 if (failures and binding) else 0


if __name__ == "__main__":
    # A Windows pipe (git hook, CI, `> file`) defaults to the ANSI code page,
    # where printing →, Δ or ✓ raises UnicodeEncodeError. Consoles and
    # Claude Code already use UTF-8 and are left alone.
    for _stream in (sys.stdout, sys.stderr):
        if getattr(_stream, "encoding", "utf-8").lower() not in ("utf-8", "utf8"):
            _stream.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
