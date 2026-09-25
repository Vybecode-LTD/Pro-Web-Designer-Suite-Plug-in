#!/usr/bin/env python3
"""extract_literals.py — Phase 1 of a token migration: the inventory.

Walk a repository and record EVERY hardcoded design value in it — lengths,
colors, durations, shadows, radii, z-indexes, font sizes, easings — with the
property it was assigned to, the file and line it lives on, and whether it sits
in a component file. It changes nothing. It is a census, not a refactor.

Why a census first: you cannot negotiate a migration you cannot size. "Our CSS
is a mess" does not get funded. "We have 1,431 hardcoded values, 612 of them
are the same eleven decisions made over and over, and 84% of them are
mechanically replaceable" does.

WHAT IT READS
-------------
  .css .scss .sass .less .pcss   CSS declarations, SCSS/LESS variables,
                                 `darken()`/`lighten()` calls
  .js .jsx .ts .tsx .mjs .cjs    JSX inline `style={{...}}`, styled-components
                                 and Emotion template literals, Tailwind
                                 arbitrary values, hex colors in strings

Values inside comments, quoted strings and `url()` are deliberately NOT
counted: they are not design decisions and counting them inflates the estimate
you are about to put in front of a client.

USAGE
-----
  # Human-readable census, grouped by kind, most frequent first
  python -m scripts.extract_literals ./src

  # The machine-readable form — this is what cluster_values.py eats
  python -m scripts.extract_literals ./src --format json -o literals.json

  # A spreadsheet for the client conversation
  python -m scripts.extract_literals ./src --format csv -o literals.csv

  # Narrow the census to one kind, or one part of the tree
  python -m scripts.extract_literals ./src --kind color --kind length
  python -m scripts.extract_literals ./src/components --top 40

  # Include the files you would normally exclude, to see the true total
  python -m scripts.extract_literals . --include-vendor

Run it by path from the PROJECT root, so `./src` is the project's:
`python <skill>/scripts/extract_literals.py ./src`. The `-m scripts.extract_literals`
form above is for a project that vendored scripts/.

Exit codes: 0 always when the walk completed (a census cannot "fail"),
2 on bad invocation or an unreadable path.
"""

from __future__ import annotations

import argparse
import bisect
import csv
import io
import json
import os
import re
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable, Iterator, Sequence

# ---------------------------------------------------------------------------
# What counts as source
# ---------------------------------------------------------------------------

CSS_EXT = {".css", ".scss", ".sass", ".less", ".pcss"}
JS_EXT = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}

SKIP_DIRS = {
    "node_modules", ".git", "dist", "build", ".next", ".nuxt", ".svelte-kit",
    "coverage", "__pycache__", ".venv", "venv", ".turbo", "out", "storybook-static",
}

# Third-party CSS you did not write and will not migrate. Fighting it is the
# classic way a migration runs 3x over estimate; see references/
# framework-migrations.md §6 — you layer it, you do not rewrite it.
# Not `lib/`: SvelteKit keeps its components in src/lib, and a library's own
# `lib/` is usually the code being migrated. Vendored copies go in vendor/.
VENDOR_DIRS = {"vendor", "vendors", "third-party", "thirdparty"}
VENDOR_FILE_PAT = re.compile(
    r"(^|[/\\])(normalize|reset|bootstrap|foundation|bulma|materialize|"
    r"swiper|slick|aos|fontawesome|tailwind\.output)[\w.-]*\.(css|scss|less)$",
    re.IGNORECASE,
)

# The destination, not a source. Literals here are the point.
TOKEN_FILE_PAT = re.compile(r"(^|[/\\])tokens?\.(css|scss)$|(^|[/\\])theme\.css$")

GENERATED_MARKERS = ("@generated", "DO NOT EDIT", "AUTO-GENERATED", "Auto-generated")

# ---------------------------------------------------------------------------
# Property classification. `kind` is decided by the property first and by the
# value's shape second, because `1px` means something different in
# `border-radius` than in `gap` and a migration that conflates them produces a
# codemod that rounds your corners into your padding.
# ---------------------------------------------------------------------------

SPACING_PROPS = {
    "margin", "margin-top", "margin-right", "margin-bottom", "margin-left",
    "margin-block", "margin-block-start", "margin-block-end",
    "margin-inline", "margin-inline-start", "margin-inline-end",
    "padding", "padding-top", "padding-right", "padding-bottom", "padding-left",
    "padding-block", "padding-block-start", "padding-block-end",
    "padding-inline", "padding-inline-start", "padding-inline-end",
    "gap", "row-gap", "column-gap", "grid-gap", "grid-row-gap", "grid-column-gap",
    "inset", "top", "right", "bottom", "left",
    "inset-block", "inset-block-start", "inset-block-end",
    "inset-inline", "inset-inline-start", "inset-inline-end",
}

SIZE_PROPS = {
    "width", "height", "min-width", "min-height", "max-width", "max-height",
    "flex-basis", "block-size", "inline-size", "min-block-size", "max-block-size",
    "min-inline-size", "max-inline-size",
}

RADIUS_PROPS = {
    "border-radius", "border-top-left-radius", "border-top-right-radius",
    "border-bottom-left-radius", "border-bottom-right-radius",
    "border-start-start-radius", "border-start-end-radius",
    "border-end-start-radius", "border-end-end-radius",
}

BORDER_WIDTH_PROPS = {
    "border-width", "border-top-width", "border-right-width",
    "border-bottom-width", "border-left-width", "border-block-width",
    "border-inline-width", "outline-width", "outline-offset", "column-rule-width",
}

COLOR_PROPS = {
    "color", "background", "background-color", "background-image",
    "border-color", "border-top-color", "border-right-color",
    "border-bottom-color", "border-left-color", "border-block-color",
    "border-inline-color", "outline-color", "fill", "stroke", "caret-color",
    "text-decoration-color", "accent-color", "column-rule-color",
    "text-emphasis-color", "scrollbar-color",
}

SHADOW_PROPS = {"box-shadow", "text-shadow", "drop-shadow", "filter"}

MOTION_PROPS = {
    "transition", "transition-duration", "transition-delay",
    "transition-timing-function", "animation", "animation-duration",
    "animation-delay", "animation-timing-function",
}

# Border shorthands carry a width AND a color, so they are members of both sets.
BORDER_SHORTHAND = {
    "border", "border-top", "border-right", "border-bottom", "border-left",
    "border-block", "border-inline", "outline", "column-rule",
}

# ---------------------------------------------------------------------------
# Value patterns
# ---------------------------------------------------------------------------

TOKENIZABLE_UNIT = r"px|rem|em|pt|pc|in|cm|mm|Q"
LENGTH_RE = re.compile(
    rf"(?<![\w.#$@-])(-?\d*\.?\d+)\s*({TOKENIZABLE_UNIT})(?![\w-])", re.IGNORECASE
)
UNITLESS_ZERO_RE = re.compile(r"(?<![\w.#$@-])(-?0(?:\.0+)?)(?![\w.%-])")
HEX_RE = re.compile(r"#[0-9a-fA-F]{3,8}(?![\w-])")
FUNC_COLOR_RE = re.compile(
    r"\b(rgba?|hsla?|hwb|lab|lch|oklab|oklch|color-mix|color)\s*\(", re.IGNORECASE
)
NAMED_COLORS = {
    "red", "blue", "green", "black", "white", "gray", "grey", "yellow", "orange",
    "purple", "pink", "brown", "cyan", "magenta", "silver", "gold", "navy",
    "teal", "olive", "maroon", "lime", "aqua", "fuchsia", "indigo", "violet",
    "crimson", "salmon", "coral", "khaki", "plum", "tan", "beige", "ivory",
    "lavender", "turquoise", "orchid", "slategray", "slategrey", "dimgray",
    "dimgrey", "lightgray", "lightgrey", "darkgray", "darkgrey", "whitesmoke",
    "gainsboro", "snow", "linen",
}
NAMED_COLOR_RE = re.compile(
    r"(?<![\w#$@-])(" + "|".join(sorted(NAMED_COLORS, key=len, reverse=True)) + r")(?![\w-])",
    re.IGNORECASE,
)
TIME_RE = re.compile(r"(?<![\w.#$@-])(\d*\.?\d+)\s*(ms|s)(?![\w-])", re.IGNORECASE)
BEZIER_RE = re.compile(r"\b(cubic-bezier|steps)\s*\([^)]*\)", re.IGNORECASE)
SCSS_COLOR_FN_RE = re.compile(
    r"\b(darken|lighten|saturate|desaturate|adjust-hue|fade-in|fade-out|"
    r"transparentize|opacify|mix|rgba)\s*\(\s*(\$[\w-]+|#[0-9a-fA-F]{3,8})",
    re.IGNORECASE,
)
INT_RE = re.compile(r"(?<![\w.#$@-])(-?\d+)(?![\w.%-])")

# Values that are legitimately literal and are not design decisions.
KEYWORD_OK = {
    "auto", "none", "inherit", "initial", "unset", "revert", "revert-layer",
    "currentcolor", "transparent", "normal", "min-content", "max-content",
    "fit-content", "stretch", "baseline", "center", "start", "end", "solid",
    "dashed", "dotted", "inset", "outset", "ridge", "groove", "double", "hidden",
}

# Tailwind arbitrary value: `p-[13px]`, `text-[#3a3a3a]`, `duration-[350ms]`.
TW_ARBITRARY_RE = re.compile(r"(?<![\w:./-])((?:[a-z]+:)*)([a-z][\w-]*?)-\[([^\]\s]+)\]")
# Arbitrary values that are not design values — grid tracks, aspect ratios,
# content strings, data/aria selectors.
TW_NON_DESIGN_PREFIX = re.compile(
    r"^(grid-cols|grid-rows|grid-area|col-span|row-span|aspect|content|mask|"
    r"supports|data|aria|has|group|peer|translate|rotate|scale|skew|order|"
    r"basis|columns|animate|delay-\[var)$"
)

CLASSNAME_RE = re.compile(
    r"""(?:className|class)\s*=\s*(?:\{\s*)?(?:`([^`]*)`|"([^"]*)"|'([^']*)')""",
    re.DOTALL,
)
# `clsx("px-[13px]", cond && "mt-[7px]")` and `cva({ variants: ... })` keep
# their classes in ordinary strings, so sweep template/quoted strings that look
# like class lists too.
CLASSLIST_STRING_RE = re.compile(r"""(?:`([^`]*)`|"([^"]*)"|'([^']*)')""", re.DOTALL)

STYLED_TAG_RE = re.compile(
    r"\b(?:styled\s*(?:\.\s*[\w$]+|\(\s*[\w$.]+\s*\))(?:\s*\.\s*(?:attrs|withConfig)\s*\([^)]*\))?"
    r"|css|createGlobalStyle|keyframes|injectGlobal)\s*`",
    re.DOTALL,
)

JSX_STYLE_RE = re.compile(r"\bstyle\s*=\s*\{\{")
JS_HEX_STRING_RE = re.compile(r"""['"`](#[0-9a-fA-F]{3,8})['"`]""")

CAMEL_BOUNDARY_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")

# Properties that take a bare number in JSX inline styles without it being a
# length (React only appends "px" to length-ish properties).
JSX_UNITLESS = {
    "z-index", "opacity", "flex", "flex-grow", "flex-shrink", "order",
    "line-height", "font-weight", "zoom", "tab-size", "column-count",
    "fill-opacity", "stroke-opacity", "grid-row", "grid-column", "aspect-ratio",
}


# ---------------------------------------------------------------------------
# The record
# ---------------------------------------------------------------------------

@dataclass
class Literal:
    """One hardcoded design value, in the place it was found."""

    kind: str           # length|color|duration|easing|shadow|radius|z-index|
                        # font-size|line-height|border-width|color-function
    raw: str            # exactly as written: "13px", "#3A3A3A", ".3s"
    normalized: str     # canonical: "13px", "#3a3a3a", "300ms"
    prop: str           # CSS property, kebab-case; "" when unknown
    file: str
    line: int
    col: int            # 1-based column of `raw` on that line
    context: str        # css-decl|scss-var|less-var|inline-style|styled|
                        # tailwind-arbitrary|js-string
    selector: str       # nearest selector or variable name
    component: bool     # sits in a file where Laws 2/4/6 bite
    declaration: str    # the whole `prop: value` it came from, trimmed

    def group_key(self) -> tuple:
        return (self.kind, self.normalized)


# ---------------------------------------------------------------------------
# Shared text utilities
# ---------------------------------------------------------------------------

def blank_css_comments(text: str) -> str:
    """Replace comment bodies with spaces, preserving every offset and newline.

    Offsets must survive because every record carries a file/line/col that a
    human is going to open. A stripping pass that shifts offsets produces an
    inventory nobody trusts, and an untrusted inventory does not get funded.
    """
    out = list(text)
    i, n = 0, len(text)
    while i < n:
        ch = text[i]
        if ch in "\"'":
            quote, i = ch, i + 1
            while i < n and text[i] != quote:
                if text[i] == "\\":
                    i += 1
                i += 1
            i += 1
            continue
        if ch == "/" and i + 1 < n and text[i + 1] == "*":
            start = i
            i += 2
            while i + 1 < n and not (text[i] == "*" and text[i + 1] == "/"):
                i += 1
            i = min(i + 2, n)
            for j in range(start, i):
                if out[j] != "\n":
                    out[j] = " "
            continue
        if ch == "/" and i + 1 < n and text[i + 1] == "/":
            start = i
            while i < n and text[i] != "\n":
                i += 1
            for j in range(start, i):
                out[j] = " "
            continue
        i += 1
    return "".join(out)


def blank_js_comments(text: str) -> str:
    """Same contract as blank_css_comments, for JS/TS source."""
    out = list(text)
    i, n = 0, len(text)
    while i < n:
        ch = text[i]
        if ch in "\"'`":
            quote, i = ch, i + 1
            while i < n and text[i] != quote:
                if text[i] == "\\":
                    i += 1
                i += 1
            i += 1
            continue
        if ch == "/" and i + 1 < n and text[i + 1] == "*":
            start = i
            i += 2
            while i + 1 < n and not (text[i] == "*" and text[i + 1] == "/"):
                i += 1
            i = min(i + 2, n)
            for j in range(start, i):
                if out[j] != "\n":
                    out[j] = " "
            continue
        if ch == "/" and i + 1 < n and text[i + 1] == "/":
            start = i
            while i < n and text[i] != "\n":
                i += 1
            for j in range(start, i):
                out[j] = " "
            continue
        i += 1
    return "".join(out)


def mask_strings_and_urls(value: str) -> str:
    """Blank quoted strings and `url(...)` bodies inside one declaration value.

    `background: url(spacer-10px.gif) no-repeat` contains the text `10px` and
    contains no design decision. `content: "12px"` is a label. Both are how a
    naive grep-driven migration corrupts a file.
    """
    out = list(value)
    i, n = 0, len(value)
    while i < n:
        ch = value[i]
        if ch in "\"'":
            quote = ch
            j = i + 1
            while j < n and value[j] != quote:
                if value[j] == "\\":
                    j += 1
                j += 1
            for k in range(i, min(j + 1, n)):
                out[k] = " "
            i = j + 1
            continue
        if value.lower().startswith("url(", i):
            depth, j = 0, i + 3
            while j < n:
                if value[j] == "(":
                    depth += 1
                elif value[j] == ")":
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            for k in range(i, min(j + 1, n)):
                out[k] = " "
            i = j + 1
            continue
        i += 1
    return "".join(out)


# (text, newline index) for the few texts in use. Holding the text keeps its id
# from being reused, so the identity check below cannot match a different file.
_LINE_STARTS: list[tuple[str, list[int]]] = []


def line_col(text: str, offset: int) -> tuple[int, int]:
    """1-based line and column of `offset`. The newline index is built once per
    text and bisected: counting from the top of the file for every literal made
    one long line — minified CSS, a many-layer shadow — quadratic."""
    for cached, starts in _LINE_STARTS:
        if cached is text:
            break
    else:
        starts = [0] + [m.end() for m in re.finditer("\n", text)]
        _LINE_STARTS.insert(0, (text, starts))
        del _LINE_STARTS[4:]
    line = bisect.bisect_right(starts, offset)
    return line, offset - starts[line - 1] + 1


def kebab(name: str) -> str:
    """`marginTop` -> `margin-top`; `--custom` and `WebkitBoxShadow` survive."""
    if name.startswith("--"):
        return name
    if name.startswith("Webkit") or name.startswith("Moz") or name.startswith("ms"):
        name = name[0].lower() + name[1:]
    return CAMEL_BOUNDARY_RE.sub("-", name).lower()


# ---------------------------------------------------------------------------
# File classification
# ---------------------------------------------------------------------------

def norm_path(path: Path) -> str:
    return str(path).replace(os.sep, "/")


def is_token_file(path: Path) -> bool:
    return bool(TOKEN_FILE_PAT.search(norm_path(path)))


def is_vendor(path: Path) -> bool:
    s = norm_path(path).lower()
    if VENDOR_FILE_PAT.search(s):
        return True
    return any(f"/{d}/" in f"/{s}" for d in VENDOR_DIRS)


def is_component_file(path: Path) -> bool:
    """Where Laws 2, 4 and 6 bite. Same test the audit script uses."""
    s = norm_path(path).lower()
    return (
        ".module." in s
        or "/components/" in s
        or "/ui/" in s
        or s.endswith("components.css")
    )


# ---------------------------------------------------------------------------
# CSS declaration scanning
# ---------------------------------------------------------------------------

@dataclass
class Decl:
    prop: str
    value: str
    value_offset: int   # absolute offset of the first char of `value`
    decl_offset: int    # absolute offset of the first char of `prop`
    selector: str
    block_start: int = -1   # offset of the `{` that opens the enclosing rule


def scan_css_declarations(text: str, base_offset: int = 0) -> Iterator[Decl]:
    """Yield every `prop: value` in a stylesheet, with absolute offsets.

    Not a parser: it tracks braces, parens, strings and the selector at each
    level, which is all a value census needs. `text` must already have had its
    comments blanked, so offsets are still true.
    """
    buf: list[str] = []
    buf_start = 0
    sel_stack: list[str] = []
    block_stack: list[int] = []
    i, n, paren = 0, len(text), 0

    def flush_decl(end: int) -> Decl | None:
        stmt = "".join(buf)
        if ":" not in stmt:
            return None
        head, _, tail = stmt.partition(":")
        prop = head.strip()
        if not prop or prop.startswith("@") or prop.startswith("//"):
            return None
        # `a:hover` caught mid-selector, and `progid:DXImageTransform` filth.
        if not re.fullmatch(r"[-$@]?[\w-]+", prop):
            return None
        lead_pad = len(head) - len(head.lstrip())
        value_pad = len(tail) - len(tail.lstrip())
        selector = next((s for s in reversed(sel_stack) if s), "")
        return Decl(
            prop=prop.lower(),
            value=tail.strip(),
            value_offset=base_offset + buf_start + len(head) + 1 + value_pad,
            decl_offset=base_offset + buf_start + lead_pad,
            selector=selector,
            block_start=block_stack[-1] if block_stack else -1,
        )

    while i < n:
        ch = text[i]
        if ch in "\"'":
            quote = ch
            buf.append(ch)
            i += 1
            while i < n and text[i] != quote:
                if text[i] == "\\" and i + 1 < n:
                    buf.append(text[i])
                    i += 1
                buf.append(text[i])
                i += 1
            if i < n:
                buf.append(text[i])
                i += 1
            continue
        if ch == "(":
            paren += 1
        elif ch == ")":
            paren = max(0, paren - 1)

        if ch == "{" and paren == 0:
            head = "".join(buf).strip()
            sel_stack.append("" if head.startswith("@") else head)
            block_stack.append(base_offset + i)
            buf, buf_start = [], i + 1
            i += 1
            continue
        if ch == "}" and paren == 0:
            d = flush_decl(i)
            if d:
                yield d
            if sel_stack:
                sel_stack.pop()
            if block_stack:
                block_stack.pop()
            buf, buf_start = [], i + 1
            i += 1
            continue
        if ch == ";" and paren == 0:
            d = flush_decl(i)
            if d:
                yield d
            buf, buf_start = [], i + 1
            i += 1
            continue
        if not buf:
            buf_start = i
        buf.append(ch)
        i += 1

    tail = flush_decl(n)
    if tail:
        yield tail


# ---------------------------------------------------------------------------
# Value slots
# ---------------------------------------------------------------------------

@dataclass
class Slot:
    """One top-level value in a declaration, with offsets into the value."""
    text: str
    start: int
    end: int


def split_slots(value: str) -> list[Slot]:
    """Split a declaration value into top-level slots, keeping offsets.

    `0 1px 3px rgba(0, 0, 0, .08)` is four slots, not seven: the commas inside
    the function separate nothing. Splitting on whitespace alone is how a naive
    tool turns one shadow into four broken ones.
    """
    slots: list[Slot] = []
    i, n, depth = 0, len(value), 0
    start = None
    while i < n:
        ch = value[i]
        if ch in "\"'":
            q = ch
            i += 1
            while i < n and value[i] != q:
                if value[i] == "\\":
                    i += 1
                i += 1
            i += 1
            continue
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        if depth == 0 and (ch.isspace() or ch == ","):
            if start is not None:
                slots.append(Slot(value[start:i], start, i))
                start = None
        elif start is None:
            start = i
        i += 1
    if start is not None:
        slots.append(Slot(value[start:n], start, n))
    return slots


# `padding: 9px 17px` sets block padding and inline padding, which are two
# different decisions that happen to be written in one line. Recording both as
# "padding" loses the distinction the proximity/inset vocabulary is built on,
# so each slot is filed under the side it actually sets.
BOX_SIDE_PROPS = {
    1: ["padding"],
    2: ["padding-block", "padding-inline"],
    3: ["padding-block", "padding-inline", "padding-block"],
    4: ["padding-block", "padding-inline", "padding-block", "padding-inline"],
}


def slot_prop(prop: str, value: str, offset: int) -> str:
    """The property a literal at `offset` within `value` really sets."""
    if prop != "padding":
        return prop
    slots = split_slots(value)
    pattern = BOX_SIDE_PROPS.get(len(slots))
    if not pattern:
        return prop
    for i, s in enumerate(slots):
        if s.start <= offset < s.end:
            return pattern[i] if i < len(pattern) else prop
    return prop


# ---------------------------------------------------------------------------
# Turning one declaration into Literal records
# ---------------------------------------------------------------------------

def classify_length(prop: str) -> str:
    if prop in RADIUS_PROPS:
        return "radius"
    if prop == "font-size":
        return "font-size"
    if prop in BORDER_WIDTH_PROPS:
        return "border-width"
    if prop == "letter-spacing":
        return "tracking"
    if prop in SPACING_PROPS or prop in SIZE_PROPS:
        return "length"
    return "length"


def normalize_length(num: str, unit: str) -> str:
    unit = unit.lower()
    try:
        v = float(num)
    except ValueError:
        return f"{num}{unit}"
    s = f"{v:g}"
    return f"{s}{unit}"


def normalize_time(num: str, unit: str) -> str:
    try:
        v = float(num)
    except ValueError:
        return f"{num}{unit}"
    ms = v * 1000.0 if unit.lower() == "s" else v
    return f"{ms:g}ms"


def normalize_color(raw: str) -> str:
    """Canonicalize so `#333`, `#333333` and `#333333FF` collapse to one key.

    They are one decision typed three ways; a report that lists them as three
    colors makes the palette look worse than it is and makes the clustering
    step do work the normalizer should have done.
    """
    s = raw.strip().lower()
    if s.startswith("#"):
        h = s[1:]
        if len(h) in (3, 4):
            h = "".join(c * 2 for c in h)
        if len(h) == 8 and h[6:] == "ff":
            h = h[:6]
        return "#" + h
    return re.sub(r"\s+", " ", s)


def extract_func_color(value: str, start: int) -> tuple[str, int] | None:
    """Return the full `rgba( ... )` text starting at `start`, and its end."""
    depth, i, n = 0, start, len(value)
    while i < n:
        if value[i] == "(":
            depth += 1
        elif value[i] == ")":
            depth -= 1
            if depth == 0:
                return value[start:i + 1], i + 1
        i += 1
    return None


def literals_from_value(
    prop: str,
    value: str,
    value_offset: int,
    source: str,
    *,
    file: str,
    context: str,
    selector: str,
    component: bool,
    declaration: str,
) -> list[Literal]:
    """Pull every design literal out of one declaration value."""
    out: list[Literal] = []
    masked = mask_strings_and_urls(value)
    prop_l = prop.lower()
    seen_spans: list[tuple[int, int]] = []

    def overlaps(a: int, b: int) -> bool:
        return any(not (b <= s or a >= e) for s, e in seen_spans)

    def record(kind: str, raw: str, normalized: str, span: tuple[int, int]) -> None:
        if overlaps(*span):
            return
        seen_spans.append(span)
        ln, col = line_col(source, value_offset + span[0])
        out.append(Literal(
            kind=kind, raw=raw, normalized=normalized,
            prop=slot_prop(prop_l, masked, span[0]), file=file,
            line=ln, col=col, context=context, selector=selector,
            component=component, declaration=declaration,
        ))

    is_color_prop = prop_l in COLOR_PROPS or prop_l in BORDER_SHORTHAND
    is_shadow_prop = prop_l in SHADOW_PROPS
    is_motion_prop = prop_l in MOTION_PROPS

    # ---- whole-value kinds first, so their parts are not double-counted -----
    if is_shadow_prop and prop_l in {"box-shadow", "text-shadow"}:
        body = masked.strip()
        if body and body.lower() not in {"none", "inherit", "initial", "unset"} \
                and "var(--" not in body:
            record("shadow", value.strip(), re.sub(r"\s+", " ", body.lower()),
                   (0, len(masked)))
            return out

    # ---- colors ------------------------------------------------------------
    if is_color_prop or is_shadow_prop or context in {"inline-style", "js-string"} \
            or prop_l.startswith("$") or prop_l.startswith("@") or prop_l.startswith("--"):
        for m in HEX_RE.finditer(masked):
            record("color", m.group(0), normalize_color(m.group(0)), m.span())
        for m in FUNC_COLOR_RE.finditer(masked):
            got = extract_func_color(masked, m.end() - 1)
            if not got:
                continue
            body, end = got
            full = m.group(1) + body
            span = (m.start(), end)
            if full.lower().startswith("color-mix") or "var(--" in full:
                seen_spans.append(span)
                continue
            record("color", value[span[0]:span[1]], normalize_color(full), span)
        for m in NAMED_COLOR_RE.finditer(masked):
            if prop_l in COLOR_PROPS or prop_l in BORDER_SHORTHAND:
                record("color", m.group(0), m.group(0).lower(), m.span())

    for m in SCSS_COLOR_FN_RE.finditer(masked):
        got = extract_func_color(masked, masked.index("(", m.start()))
        if not got:
            continue
        end = m.start() + 0
        body, end = got
        full = masked[m.start():end]
        if full.lower().startswith("rgba(") and "$" not in full and "#" not in full:
            continue
        record("color-function", value[m.start():end],
               re.sub(r"\s+", "", full.lower()), (m.start(), end))

    # ---- durations and easings --------------------------------------------
    if is_motion_prop or context == "inline-style":
        for m in TIME_RE.finditer(masked):
            record("duration", m.group(0), normalize_time(m.group(1), m.group(2)),
                   m.span())
        for m in BEZIER_RE.finditer(masked):
            record("easing", m.group(0), re.sub(r"\s+", "", m.group(0).lower()),
                   m.span())

    # ---- z-index -----------------------------------------------------------
    if prop_l == "z-index":
        for m in INT_RE.finditer(masked):
            if m.group(1) == "0":
                continue
            record("z-index", m.group(1), m.group(1), m.span())
        return out

    # ---- line-height as a bare ratio --------------------------------------
    if prop_l == "line-height":
        body = masked.strip()
        if re.fullmatch(r"\d*\.?\d+", body):
            record("line-height", body, f"{float(body):g}", (masked.index(body),
                                                             masked.index(body) + len(body)))
            return out

    # ---- lengths -----------------------------------------------------------
    kind = classify_length(prop_l)
    for m in LENGTH_RE.finditer(masked):
        num, unit = m.group(1), m.group(2)
        if float(num) == 0:
            continue
        this_kind = kind
        if is_shadow_prop or is_color_prop and prop_l in BORDER_SHORTHAND:
            this_kind = "border-width" if prop_l in BORDER_SHORTHAND else kind
        record(this_kind, m.group(0), normalize_length(num, unit), m.span())

    return out


# ---------------------------------------------------------------------------
# CSS / SCSS / LESS files
# ---------------------------------------------------------------------------

def extract_css(path: Path, text: str) -> list[Literal]:
    out: list[Literal] = []
    blanked = blank_css_comments(text)
    component = is_component_file(path)
    fname = norm_path(path)

    for d in scan_css_declarations(blanked):
        prop = d.prop
        if prop.startswith("$"):
            context = "scss-var"
        elif prop.startswith("@") and path.suffix.lower() == ".less":
            context = "less-var"
        elif prop.startswith("--"):
            context = "custom-property"
        else:
            context = "css-decl"
        value = text[d.value_offset:d.value_offset + len(d.value)]
        if "var(--" in value and context == "css-decl":
            # Already tokenized, wholly or partly. A partial hit still leaks a
            # literal, so keep scanning; the masker below drops the var() body.
            value_scan = re.sub(r"var\(\s*--[\w-]+", lambda m: " " * len(m.group(0)), value)
        else:
            value_scan = value
        decl_text = text[d.decl_offset:d.value_offset + len(d.value)].strip()
        out.extend(literals_from_value(
            prop, value_scan, d.value_offset, text,
            file=fname, context=context, selector=d.selector,
            component=component, declaration=re.sub(r"\s+", " ", decl_text),
        ))
    return out


# ---------------------------------------------------------------------------
# JS / JSX / TS / TSX files
# ---------------------------------------------------------------------------

def match_braces(text: str, start: int) -> int:
    """Index just past the `}` that closes the `{` at `start`."""
    depth, i, n = 0, start, len(text)
    while i < n:
        c = text[i]
        if c in "\"'`":
            q, i = c, i + 1
            while i < n and text[i] != q:
                if text[i] == "\\":
                    i += 1
                i += 1
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return n


def match_template(text: str, start: int) -> int:
    """Index of the backtick that closes the template literal opened at `start`."""
    i, n = start + 1, len(text)
    while i < n:
        c = text[i]
        if c == "\\":
            i += 2
            continue
        if c == "$" and i + 1 < n and text[i + 1] == "{":
            i = match_braces(text, i + 1)
            continue
        if c == "`":
            return i
        i += 1
    return n


def blank_interpolations(segment: str) -> str:
    """Blank `${...}` bodies inside a styled-components template.

    The interpolation is JS, not CSS. Leaving it in makes the CSS scanner read
    `${(p) => p.pad}px` as a declaration and invent a property named `p`.
    """
    out = list(segment)
    i, n = 0, len(segment)
    while i < n:
        if segment[i] == "$" and i + 1 < n and segment[i + 1] == "{":
            end = match_braces(segment, i + 1)
            for j in range(i, min(end, n)):
                if out[j] != "\n":
                    out[j] = " "
            i = end
            continue
        i += 1
    return "".join(out)


def parse_style_object(body: str) -> list[tuple[str, str, int]]:
    """Parse a JSX inline-style object body into (prop, value, offset) triples.

    Handles `marginTop: 13`, `'padding-left': '8px'`, `color: "#3a3a3a"` and
    shorthand nesting one level deep. Spread and computed keys are skipped —
    they are not literals and guessing at them is how a codemod corrupts JSX.
    """
    out: list[tuple[str, str, int]] = []
    i, n, depth = 0, len(body), 0
    while i < n:
        ch = body[i]
        if ch in "\"'`":
            q, i = ch, i + 1
            while i < n and body[i] != q:
                if body[i] == "\\":
                    i += 1
                i += 1
            i += 1
            continue
        if ch in "{[(":
            depth += 1
            i += 1
            continue
        if ch in "}])":
            depth -= 1
            i += 1
            continue
        if ch == ":" and depth == 0:
            # Walk back for the key.
            j = i - 1
            while j >= 0 and body[j] in " \t\n\r":
                j -= 1
            if j >= 0 and body[j] in "\"'":
                q = body[j]
                k = j - 1
                while k >= 0 and body[k] != q:
                    k -= 1
                key = body[k + 1:j]
                key_start = k
            else:
                k = j
                while k >= 0 and (body[k].isalnum() or body[k] in "_$-"):
                    k -= 1
                key = body[k + 1:j + 1]
                key_start = k + 1
            # Walk forward for the value, to the next top-level comma.
            v = i + 1
            vdepth = 0
            while v < n:
                c = body[v]
                if c in "\"'`":
                    q, v = c, v + 1
                    while v < n and body[v] != q:
                        if body[v] == "\\":
                            v += 1
                        v += 1
                elif c in "{[(":
                    vdepth += 1
                elif c in "}])":
                    if vdepth == 0:
                        break
                    vdepth -= 1
                elif c == "," and vdepth == 0:
                    break
                v += 1
            raw_value = body[i + 1:v]
            if key and re.fullmatch(r"[-\w$]+", key):
                out.append((key, raw_value, i + 1))
            i = v + 1
            del key_start
            continue
        i += 1
    return out


def extract_js(path: Path, text: str) -> list[Literal]:
    out: list[Literal] = []
    clean = blank_js_comments(text)
    component = is_component_file(path) or path.suffix.lower() in {".jsx", ".tsx"}
    fname = norm_path(path)
    consumed: list[tuple[int, int]] = []

    def claim(a: int, b: int) -> None:
        consumed.append((a, b))

    def claimed(pos: int) -> bool:
        return any(a <= pos < b for a, b in consumed)

    # ---- styled-components / Emotion template literals ---------------------
    for m in STYLED_TAG_RE.finditer(clean):
        open_tick = clean.index("`", m.end() - 1)
        close_tick = match_template(clean, open_tick)
        body_start, body_end = open_tick + 1, close_tick
        claim(m.start(), min(close_tick + 1, len(clean)))
        raw_body = clean[body_start:body_end]
        css_body = blank_interpolations(blank_css_comments(raw_body))
        selector_hint = m.group(0).strip().rstrip("`").strip()
        for d in scan_css_declarations(css_body, base_offset=body_start):
            value = text[d.value_offset:d.value_offset + len(d.value)]
            if "var(--" in value:
                value = re.sub(r"var\(\s*--[\w-]+",
                               lambda mm: " " * len(mm.group(0)), value)
            decl_text = text[d.decl_offset:d.value_offset + len(d.value)].strip()
            out.extend(literals_from_value(
                d.prop, value, d.value_offset, text, file=fname, context="styled",
                selector=d.selector or selector_hint, component=component,
                declaration=re.sub(r"\s+", " ", decl_text),
            ))

    # ---- JSX inline styles -------------------------------------------------
    for m in JSX_STYLE_RE.finditer(clean):
        if claimed(m.start()):
            continue
        open_at = clean.index("{", m.start())
        end = match_braces(clean, open_at)
        # Claimed, or the bare-hex pass below counts every quoted colour twice.
        claim(m.start(), end)
        inner_start = clean.index("{", open_at + 1) + 1 if "{" in clean[open_at + 1:end] else open_at + 1
        body = clean[inner_start:end - 2] if end - 2 > inner_start else ""
        for key, raw_value, rel in parse_style_object(body):
            prop = kebab(key)
            abs_off = inner_start + rel
            v = raw_value.strip()
            lead = len(raw_value) - len(raw_value.lstrip())
            if v[:1] in "\"'`" and v[-1:] == v[:1] and len(v) >= 2:
                v_text, v_off = v[1:-1], abs_off + lead + 1
            elif re.fullmatch(r"-?\d*\.?\d+", v):
                # React turns a bare number into px for length properties.
                v_text = v if prop in JSX_UNITLESS else f"{v}px"
                v_off = abs_off + lead
            else:
                continue  # an expression, not a literal
            out.extend(literals_from_value(
                prop, v_text, v_off, text, file=fname, context="inline-style",
                selector="style={{...}}", component=component,
                declaration=f"{key}: {v}",
            ))

    # ---- Tailwind arbitrary values ----------------------------------------
    seen_tw: set[tuple[int, int]] = set()
    for sm in list(CLASSNAME_RE.finditer(clean)) + list(CLASSLIST_STRING_RE.finditer(clean)):
        group = next((g for g in sm.groups() if g is not None), None)
        if group is None:
            continue
        base = sm.start(sm.lastindex or 1)
        if claimed(base):
            continue
        for m in TW_ARBITRARY_RE.finditer(group):
            span = (base + m.start(), base + m.end())
            if span in seen_tw:
                continue
            seen_tw.add(span)
            prefix, body = m.group(2), m.group(3)
            if TW_NON_DESIGN_PREFIX.match(prefix):
                continue
            body_clean = body.replace("_", " ")
            if body_clean.startswith("var(") or body_clean.startswith("--"):
                continue
            ln, col = line_col(text, span[0])
            kind, normalized = classify_tailwind(prefix, body_clean)
            if not kind:
                continue
            out.append(Literal(
                kind=kind, raw=m.group(0), normalized=normalized,
                prop=f"tw:{prefix}", file=fname, line=ln, col=col,
                context="tailwind-arbitrary", selector="className",
                component=component, declaration=m.group(0),
            ))

    # ---- bare hex colors in JS strings -------------------------------------
    for m in JS_HEX_STRING_RE.finditer(clean):
        if claimed(m.start()):
            continue
        ctx_line = text[max(0, text.rfind("\n", 0, m.start())):
                        text.find("\n", m.start()) if text.find("\n", m.start()) > 0 else len(text)]
        if re.search(r"(href|anchor|hash|sha|commit|id=)", ctx_line, re.IGNORECASE):
            continue
        ln, col = line_col(text, m.start(1))
        out.append(Literal(
            kind="color", raw=m.group(1), normalized=normalize_color(m.group(1)),
            prop="", file=fname, line=ln, col=col, context="js-string",
            selector="", component=component, declaration=ctx_line.strip()[:120],
        ))

    return out


TW_SPACING_PREFIX = {
    "p", "px", "py", "pt", "pr", "pb", "pl", "ps", "pe",
    "m", "mx", "my", "mt", "mr", "mb", "ml", "ms", "me",
    "gap", "gap-x", "gap-y", "space-x", "space-y",
    "top", "right", "bottom", "left", "inset", "inset-x", "inset-y",
    "w", "h", "min-w", "min-h", "max-w", "max-h", "size",
}
TW_COLOR_PREFIX = {"text", "bg", "border", "ring", "fill", "stroke", "from", "to",
                   "via", "shadow", "outline", "decoration", "divide", "accent",
                   "caret", "placeholder"}
TW_RADIUS_PREFIX = {"rounded", "rounded-t", "rounded-r", "rounded-b", "rounded-l",
                    "rounded-tl", "rounded-tr", "rounded-br", "rounded-bl"}
TW_DURATION_PREFIX = {"duration", "delay", "transition"}


def classify_tailwind(prefix: str, body: str) -> tuple[str, str]:
    """Map a Tailwind arbitrary value onto a literal kind and canonical form."""
    body = body.strip()
    if prefix in TW_COLOR_PREFIX and (body.startswith("#") or FUNC_COLOR_RE.match(body)):
        return "color", normalize_color(body)
    if prefix == "text":
        m = LENGTH_RE.fullmatch(body)
        if m:
            return "font-size", normalize_length(m.group(1), m.group(2))
    if prefix in TW_RADIUS_PREFIX:
        m = LENGTH_RE.fullmatch(body)
        if m:
            return "radius", normalize_length(m.group(1), m.group(2))
    if prefix in TW_DURATION_PREFIX:
        m = TIME_RE.fullmatch(body)
        if m:
            return "duration", normalize_time(m.group(1), m.group(2))
    if prefix in {"z"} and re.fullmatch(r"-?\d+", body):
        return "z-index", body
    if prefix in TW_SPACING_PREFIX:
        m = LENGTH_RE.fullmatch(body)
        if m:
            return "length", normalize_length(m.group(1), m.group(2))
    m = LENGTH_RE.fullmatch(body)
    if m:
        return "length", normalize_length(m.group(1), m.group(2))
    if body.startswith("#"):
        return "color", normalize_color(body)
    return "", ""


# ---------------------------------------------------------------------------
# Walking
# ---------------------------------------------------------------------------

def iter_files(paths: Sequence[str], *, include_vendor: bool,
               include_tokens: bool,
               vendor_skipped: list[Path] | None = None) -> Iterator[Path]:
    """Files to scan. A file named explicitly is always scanned (the user asked
    for it); inside a folder, vendor files are left out and collected in
    `vendor_skipped`, so the census can say what it did not count."""
    for raw in paths:
        p = Path(raw)
        explicit = p.is_file()
        if explicit:
            candidates = [p]
        else:
            candidates = []
            for root, dirs, files in os.walk(p):
                dirs[:] = [d for d in dirs
                           if d not in SKIP_DIRS and not d.startswith(".")]
                for f in sorted(files):
                    candidates.append(Path(root) / f)
        for fp in candidates:
            if fp.suffix.lower() not in CSS_EXT | JS_EXT:
                continue
            if not include_vendor and not explicit and is_vendor(fp):
                if vendor_skipped is not None:
                    vendor_skipped.append(fp)
                continue
            if not include_tokens and is_token_file(fp):
                continue
            yield fp


def extract(paths: Sequence[str], *, include_vendor: bool = False,
            include_tokens: bool = False) -> tuple[list[Literal], list[str]]:
    literals: list[Literal] = []
    problems: list[str] = []
    vendor_skipped: list[Path] = []
    for fp in iter_files(paths, include_vendor=include_vendor,
                         include_tokens=include_tokens,
                         vendor_skipped=vendor_skipped):
        try:
            text = fp.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            problems.append(f"{fp}: unreadable ({exc})")
            continue
        if any(mark in text[:800] for mark in GENERATED_MARKERS):
            continue
        try:
            if fp.suffix.lower() in CSS_EXT:
                literals.extend(extract_css(fp, text))
            else:
                literals.extend(extract_js(fp, text))
        except Exception as exc:                     # noqa: BLE001 — never abort a census
            problems.append(f"{fp}: parse failed ({type(exc).__name__}: {exc})")
    if vendor_skipped:
        names = ", ".join(norm_path(p) for p in vendor_skipped[:5])
        more = f" and {len(vendor_skipped) - 5} more" if len(vendor_skipped) > 5 else ""
        problems.append(f"excluded {len(vendor_skipped)} vendor file(s): {names}{more} "
                        f"— you layer vendor CSS, you do not migrate it; "
                        f"--include-vendor counts them")
    literals.sort(key=lambda l: (l.file, l.line, l.col))
    return literals, problems


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

KIND_ORDER = ["length", "color", "font-size", "radius", "duration", "shadow",
              "z-index", "border-width", "line-height", "easing", "tracking",
              "color-function"]


def render_report(literals: Sequence[Literal], *, top: int,
                  problems: Sequence[str]) -> str:
    if not literals:
        return ("extract_literals: no hardcoded design values found.\n"
                "Either this tree is already tokenized, or you pointed it at "
                "the wrong directory.\n")

    buf: list[str] = []
    files = sorted({l.file for l in literals})
    comp = sum(1 for l in literals if l.component)
    buf.append("=" * 78)
    buf.append("LITERAL INVENTORY")
    buf.append("=" * 78)
    buf.append(f"  {len(literals)} literal value(s) across {len(files)} file(s).")
    buf.append(f"  {comp} of them ({pct(comp, len(literals))}) sit in component files, "
               f"where they also break Laws 2, 4 and 6.")
    buf.append("")

    by_kind: dict[str, list[Literal]] = {}
    for l in literals:
        by_kind.setdefault(l.kind, []).append(l)

    order = [k for k in KIND_ORDER if k in by_kind] + \
            [k for k in sorted(by_kind) if k not in KIND_ORDER]

    for kind in order:
        items = by_kind[kind]
        groups: dict[str, list[Literal]] = {}
        for l in items:
            groups.setdefault(l.normalized, []).append(l)
        distinct = len(groups)
        buf.append("-" * 78)
        buf.append(f"{kind.upper()}  —  {len(items)} occurrence(s), "
                   f"{distinct} distinct value(s)")
        buf.append("-" * 78)
        ranked = sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[0]))
        for value, occurrences in ranked[:top]:
            props = sorted({o.prop for o in occurrences if o.prop})
            prop_note = ", ".join(props[:4]) + ("…" if len(props) > 4 else "")
            buf.append(f"  {len(occurrences):>5}×  {value:<24} {prop_note}")
            locs: dict[str, int] = {}
            for o in occurrences:
                locs[o.file] = locs.get(o.file, 0) + 1
            top_locs = sorted(locs.items(), key=lambda kv: -kv[1])[:3]
            first = occurrences[0]
            buf.append(f"          first: {first.file}:{first.line}  "
                       f"({first.context})")
            buf.append("          top:   " + ", ".join(
                f"{f} ×{c}" for f, c in top_locs))
        if distinct > top:
            buf.append(f"  … and {distinct - top} more distinct value(s). "
                       f"Raise --top to see them.")
        buf.append("")

    # The number that actually sells the migration.
    lengths = by_kind.get("length", [])
    off_grid = [l for l in lengths
                if l.normalized.endswith("px")
                and _is_off_grid(l.normalized)]
    buf.append("=" * 78)
    buf.append("HEADLINE NUMBERS")
    buf.append("=" * 78)
    buf.append(f"  distinct spacing values      {len({l.normalized for l in lengths})}"
               f"   (the closed scale has 18)")
    buf.append(f"  off the 4px grid entirely    {len(off_grid)} occurrence(s)")
    buf.append(f"  distinct colors              "
               f"{len({l.normalized for l in by_kind.get('color', [])})}")
    buf.append(f"  distinct font sizes          "
               f"{len({l.normalized for l in by_kind.get('font-size', [])})}"
               f"   (the type scale has 11)")
    buf.append(f"  distinct shadows             "
               f"{len({l.normalized for l in by_kind.get('shadow', [])})}"
               f"   (the elevation ladder has 6)")
    buf.append("")
    buf.append("  Next: python -m scripts.cluster_values literals.json -o ./proposal")
    buf.append("")

    if problems:
        buf.append("NOTES")
        for p in problems:
            buf.append(f"  ! {p}")
        buf.append("")
    return "\n".join(buf)


def _is_off_grid(normalized: str) -> bool:
    try:
        v = float(normalized[:-2])
    except ValueError:
        return False
    return v % 4 != 0


def pct(part: int, whole: int) -> str:
    return f"{(100.0 * part / whole):.0f}%" if whole else "0%"


def render_csv(literals: Sequence[Literal]) -> str:
    out = io.StringIO()
    w = csv.writer(out, lineterminator="\n")
    w.writerow(["kind", "raw", "normalized", "prop", "file", "line", "col",
                "context", "selector", "component", "declaration"])
    for l in literals:
        w.writerow([l.kind, l.raw, l.normalized, l.prop, l.file, l.line, l.col,
                    l.context, l.selector, int(l.component), l.declaration])
    return out.getvalue()


def render_json(literals: Sequence[Literal], paths: Sequence[str],
                problems: Sequence[str]) -> str:
    groups: dict[str, dict[str, int]] = {}
    for l in literals:
        groups.setdefault(l.kind, {})
        groups[l.kind][l.normalized] = groups[l.kind].get(l.normalized, 0) + 1
    payload = {
        "schema": "design-token-migration/literals@1",
        "roots": list(paths),
        "counts": {
            "literals": len(literals),
            "files": len({l.file for l in literals}),
            "by_kind": {k: sum(v.values()) for k, v in sorted(groups.items())},
            "distinct_by_kind": {k: len(v) for k, v in sorted(groups.items())},
        },
        "frequency": {k: dict(sorted(v.items(), key=lambda kv: (-kv[1], kv[0])))
                      for k, v in sorted(groups.items())},
        "problems": list(problems),
        "literals": [asdict(l) for l in literals],
    }
    return json.dumps(payload, indent=2) + "\n"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="python -m scripts.extract_literals",
        description="Phase 1 of a token migration: inventory every hardcoded "
                    "design value in a repository. Changes nothing.",
        epilog="Feed the JSON to cluster_values.py to get a proposed token "
               "system and a codemod mapping.",
    )
    ap.add_argument("paths", nargs="+",
                    help="files or directories to inventory")
    ap.add_argument("--format", choices=["report", "json", "csv"],
                    default="report", help="output shape (default: report)")
    ap.add_argument("-o", "--output", metavar="FILE",
                    help="write to FILE instead of stdout")
    ap.add_argument("--kind", action="append", metavar="KIND",
                    help="only this kind (repeatable): "
                         + "|".join(KIND_ORDER))
    ap.add_argument("--top", type=int, default=20, metavar="N",
                    help="values to list per kind in the report (default: 20)")
    ap.add_argument("--include-vendor", action="store_true",
                    help="also inventory vendor/third-party stylesheets "
                         "(normally excluded: you layer them, you do not migrate them)")
    ap.add_argument("--include-tokens", action="store_true",
                    help="also inventory tokens.css / theme.css "
                         "(normally excluded: literals there are the point)")
    ap.add_argument("--min-count", type=int, default=1, metavar="N",
                    help="drop values occurring fewer than N times (default: 1)")
    return ap


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    missing = [p for p in args.paths if not Path(p).exists()]
    if missing:
        print(f"extract_literals: no such path: {', '.join(missing)}",
              file=sys.stderr)
        return 2

    literals, problems = extract(args.paths,
                                 include_vendor=args.include_vendor,
                                 include_tokens=args.include_tokens)

    if args.kind:
        wanted = {k.lower() for k in args.kind}
        unknown = wanted - set(KIND_ORDER)
        if unknown:
            print(f"extract_literals: unknown --kind {', '.join(sorted(unknown))}. "
                  f"Valid kinds: {', '.join(KIND_ORDER)}.", file=sys.stderr)
            return 2
        literals = [l for l in literals if l.kind in wanted]

    if args.min_count > 1:
        counts: dict[tuple, int] = {}
        for l in literals:
            counts[l.group_key()] = counts.get(l.group_key(), 0) + 1
        literals = [l for l in literals if counts[l.group_key()] >= args.min_count]

    if args.format == "json":
        text = render_json(literals, args.paths, problems)
    elif args.format == "csv":
        text = render_csv(literals)
    else:
        text = render_report(literals, top=args.top, problems=problems)

    if args.output:
        try:
            Path(args.output).write_text(text, encoding="utf-8")
        except OSError as exc:
            print(f"extract_literals: cannot write {args.output}: {exc}",
                  file=sys.stderr)
            return 2
        print(f"extract_literals: {len(literals)} literal(s) -> {args.output}")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    # A Windows pipe (git hook, CI, `> file`) defaults to the ANSI code page,
    # where printing →, Δ or ✓ raises UnicodeEncodeError. Consoles and
    # Claude Code already use UTF-8 and are left alone.
    for _stream in (sys.stdout, sys.stderr):
        if getattr(_stream, "encoding", "utf-8").lower() not in ("utf-8", "utf8"):
            _stream.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
