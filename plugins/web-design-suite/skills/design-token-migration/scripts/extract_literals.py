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
  .css .scss .less .pcss         CSS declarations, SCSS/LESS variables,
                                 `darken()`/`lighten()` and `color.adjust()`,
                                 `color.scale()`, `color.change()`, `color.mix()`
  .js .jsx .ts .tsx .mjs .cjs    JSX inline `style={{...}}`, styled-components
                                 and Emotion template literals, style objects
                                 (MUI `sx`, Emotion and Panda `css({...})`,
                                 vanilla-extract `style({...})`), Tailwind
                                 arbitrary values and v4's numeric classes
                                 (`p-4`, while the theme keeps `--spacing`),
                                 hex colors in strings
  .vue .svelte .astro .html .htm `<style>` blocks (CSS, SCSS, Less), `style=""`
                                 attributes, Tailwind arbitrary values in
                                 `class="..."`

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
from typing import Callable, Iterable, Iterator, Sequence

# A sibling import would otherwise leave __pycache__ inside the installed
# plugin. project_config.py is a copy of the plugin's shared/ master (P24).
sys.dont_write_bytecode = True
try:                                              # python -m scripts.extract_literals
    from .project_config import refuse_overwrite  # type: ignore[import-not-found]
except ImportError:                               # python scripts/extract_literals.py, or loaded by path
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from project_config import refuse_overwrite   # type: ignore[no-redef]

# ---------------------------------------------------------------------------
# What counts as source
# ---------------------------------------------------------------------------

CSS_EXT = {".css", ".scss", ".less", ".pcss"}
# Indented Sass has no braces for the scanner to follow, so reading it would
# count nothing; the census says it was not read instead (N13).
INDENTED_SASS_EXT = ".sass"
JS_EXT = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}
# Single-file components and pages: their <style> blocks are stylesheets, their
# style="" attributes inline styles, their class="" attributes class lists (LC-B5).
MARKUP_EXT = {".vue", ".svelte", ".astro", ".html", ".htm"}
SFC_EXT = {".vue", ".svelte", ".astro"}           # a component by definition
STYLE_BLOCK_RE = re.compile(r"(<style\b)([^>]*)>(.*?)</style\s*>", re.IGNORECASE | re.DOTALL)
SCRIPT_BLOCK_RE = re.compile(r"<script\b[^>]*>(.*?)</script\s*>", re.IGNORECASE | re.DOTALL)
ASTRO_FRONTMATTER_RE = re.compile(r"\A\s*---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|\Z)", re.DOTALL)
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
STYLE_LANG_RE = re.compile(r"""\blang\s*=\s*["']?([\w-]+)""", re.IGNORECASE)
# The suffix a <style lang="…"> block is read as; a language the scanner cannot
# follow (indented Sass, Stylus) is reported, as a .sass file is.
STYLE_LANG_SUFFIX = {"": ".css", "css": ".css", "postcss": ".pcss", "pcss": ".pcss",
                     "scss": ".scss", "less": ".less"}
# `style="…"` but never Vue's `:style` / `v-bind:style` (an expression) or
# Svelte's `style:color` directive.
STYLE_ATTR_RE = re.compile(r"""(?<![\w:@.-])style\s*=\s*(?:"([^"]*)"|'([^']*)')""", re.IGNORECASE)

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
# The audit's file classes (web-design-studio's audit_design.py and
# design-rules.json): token files are skipped, component files are held to
# Laws 2, 4 and 6. tests/test_rules_spec.py holds both copies to the spec.
TOKEN_FILE_PAT = re.compile(
    r"(^|[/\\])([\w.-]*[-.])?tokens\.(css|scss)$"
    r"|(^|[/\\])tokens[/\\][\w.-]+\.(css|scss)$"
    r"|(^|[/\\])([\w.-]*[-.])?theme\.(css|scss)$"
)
COMPONENT_FILE_PAT = re.compile(r"\.module\.|(^|/)(components|ui)/|(^|/)components\.css$")

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
# Not after a hyphen: Sass's adjust-color() is not CSS's color() (LC-B5).
FUNC_COLOR_RE = re.compile(
    r"(?<![\w-])(rgba?|hsla?|hwb|lab|lch|oklab|oklch|color-mix|color)\s*\(", re.IGNORECASE
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
    # The sass:color module's functions first, which the Sass docs send users
    # to in place of darken() and the rest (LC-B5), then the global names.
    r"\b(color\.(?:adjust|scale|change|mix)|adjust-color|scale-color|change-color|"
    r"darken|lighten|saturate|desaturate|adjust-hue|fade-in|fade-out|"
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
# Object styles (LC-B5): MUI's and Emotion's props, the libraries' functions,
# and styled-components' and Emotion's object form. `style`, `styleVariants`
# and `recipe` count only in a file importing vanilla-extract, `cva` and
# `sva` only beside Panda's import: elsewhere those names mean other things.
OBJECT_STYLE_RE = re.compile(
    r"\b(?P<prop>sx|css)\s*=\s*\{\s*(?=\{)"
    r"|\b(?P<fn>css|cva|sva|style|styleVariants|recipe)\s*\(\s*(?=\{)"
    r"|\bstyled\s*(?:\.\s*[\w$]+|\(\s*[^()]*\))\s*\(\s*(?=\{)"
)
VANILLA_ONLY = {"style", "styleVariants", "recipe"}
PANDA_ONLY = {"cva", "sva"}
VANILLA_IMPORT_RE = re.compile(r"""from\s+['"]@vanilla-extract/(?:css|recipes)['"]""")
PANDA_IMPORT_RE = re.compile(r"""from\s+['"](?:[^'"]*styled-system/[\w/-]+|@pandacss/[\w/-]+)['"]""")
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
                        # tailwind-arbitrary|tailwind-spacing|js-string
    selector: str       # nearest selector or variable name
    component: bool     # sits in a file where Laws 2/4/6 bite
    declaration: str    # the whole `prop: value` it came from, trimmed

    def group_key(self) -> tuple:
        return (self.kind, self.normalized)


# ---------------------------------------------------------------------------
# Shared text utilities
# ---------------------------------------------------------------------------

# `//` starts a comment in Sass, Less and a styled template, never in CSS
# itself, where it is part of a value (`--terms: https://…`). The audit's
# line_comments makes the same split (SB-A9, N12).
PLAIN_CSS_EXT = {".css", ".pcss"}


def line_comments(path: Path) -> bool:
    return path.suffix.lower() not in PLAIN_CSS_EXT


def unquoted_url_end(text: str, j: int) -> int | None:
    """The index of the `)` that closes an unquoted address starting at `j`,
    just after `url(`; None when the argument is not one. An unquoted address
    is a single token: no quote, no `(` and no inner whitespace, and an
    escaped character (`\\)`) is part of it. The audit has the same test."""
    n = len(text)
    while j < n and text[j] in " \t\r\n":
        j += 1
    while j < n:
        c = text[j]
        if c == "\\":
            j += 2
        elif c == ")":
            return j
        elif c in "\"'(":
            return None
        elif c in " \t\r\n":
            while j < n and text[j] in " \t\r\n":
                j += 1
            return j if j < n and text[j] == ")" else None
        else:
            j += 1
    return None


def blank_css_comments(text: str, slash_comments: bool = True) -> str:
    """Replace comment bodies with spaces, preserving every offset and newline.

    Offsets must survive because every record carries a file/line/col that a
    human is going to open. A stripping pass that shifts offsets produces an
    inventory nobody trusts, and an untrusted inventory does not get funded.

    `//` comments count only with `slash_comments`, and an unquoted `url(…)` is
    one token either way: the `//` in `url(https://cdn…)` is the address.
    """
    out = list(text)
    i, n = 0, len(text)
    while i < n:
        ch = text[i]
        if (ch in "uU" and text[i:i + 4].lower() == "url("
                and not (i and (text[i - 1].isalnum() or text[i - 1] in "-_"))):
            end = unquoted_url_end(text, i + 4)
            if end is not None:
                i = end
                continue
            # Otherwise a quoted address, read as a string below, or a Sass
            # expression (`url($asset)`), whose comments are still comments.
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
        if slash_comments and ch == "/" and i + 1 < n and text[i + 1] == "/":
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
    return bool(COMPONENT_FILE_PAT.search(norm_path(path).lower()))


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
    parent: str = ""        # the selector of the rule it is nested in, if any
    context: tuple = ()     # the at-rules it sits in (@media, @supports), not @layer


def scan_css_declarations(text: str, base_offset: int = 0) -> Iterator[Decl]:
    """Yield every `prop: value` in a stylesheet, with absolute offsets.

    Not a parser: it tracks braces, parens, strings and the selector at each
    level, which is all a value census needs. `text` must already have had its
    comments blanked, so offsets are still true.
    """
    buf: list[str] = []
    buf_start = 0
    sel_stack: list[str] = []
    at_stack: list[str] = []
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
        named = [s for s in sel_stack if s]
        selector = named[-1] if named else ""
        return Decl(
            prop=prop.lower(),
            value=tail.strip(),
            value_offset=base_offset + buf_start + len(head) + 1 + value_pad,
            decl_offset=base_offset + buf_start + lead_pad,
            selector=selector,
            block_start=block_stack[-1] if block_stack else -1,
            parent=named[-2] if len(named) > 1 else "",
            context=tuple(" ".join(h.split()) for h in at_stack
                          if h and not h.lower().startswith("@layer")),
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
            at_stack.append(head if head.startswith("@") else "")
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
            if at_stack:
                at_stack.pop()
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
    if "!important" in value.lower():         # not a slot: `16px !important` is one
        value = value[:value.lower().index("!important")]
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


def mixes_a_literal(body: str) -> bool:
    """Whether a color-mix() body holds a colour written out: a hex, a named
    colour, or a colour function that reads no custom property."""
    if HEX_RE.search(body) or NAMED_COLOR_RE.search(body):
        return True
    for m in FUNC_COLOR_RE.finditer(body):
        got = extract_func_color(body, m.end() - 1)
        if got and m.group(1).lower() != "color-mix" and "var(--" not in got[0]:
            return True
    return False


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

    # ---- Sass colour functions, before the colours inside them -------------
    # `color.adjust(#123456, $lightness: 10%)` is one decision, not a hex
    # (Codex on #116): the whole call is claimed first.
    for m in SCSS_COLOR_FN_RE.finditer(masked):
        got = extract_func_color(masked, masked.index("(", m.start()))
        if not got:
            continue
        body, end = got
        full = masked[m.start():end]
        if full.lower().startswith("rgba(") and "$" not in full and "#" not in full:
            continue
        record("color-function", value[m.start():end],
               re.sub(r"\s+", "", full.lower()), (m.start(), end))

    # ---- colors ------------------------------------------------------------
    if is_color_prop or is_shadow_prop or context in {"inline-style", "js-string"} \
            or prop_l.startswith("$") or prop_l.startswith("@") or prop_l.startswith("--"):
        # A colour inside color-mix() is part of a mix the codemod cannot
        # rewrite, so the call is claimed before the hex pass, and counted as
        # one colour function when it mixes a literal (H12).
        for m in FUNC_COLOR_RE.finditer(masked):
            if m.group(1).lower() != "color-mix":
                continue
            got = extract_func_color(masked, m.end() - 1)
            if not got:
                continue
            body, end = got
            if mixes_a_literal(body):
                record("color-function", value[m.start():end],
                       re.sub(r"\s+", " ", (m.group(1) + body).lower()), (m.start(), end))
            else:
                seen_spans.append((m.start(), end))
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

def extract_css(path: Path, text: str, *, suffix: str | None = None,
                component: bool | None = None) -> list[Literal]:
    """A stylesheet's literals. `suffix` reads `text` as another syntax (a
    `<style lang="scss">` block in a .vue file, blanked around to its length)."""
    out: list[Literal] = []
    suffix = (suffix or path.suffix).lower()
    blanked = blank_css_comments(text, suffix not in PLAIN_CSS_EXT)
    if component is None:
        component = is_component_file(path)
    fname = norm_path(path)

    for d in scan_css_declarations(blanked):
        prop = d.prop
        if prop.startswith("$"):
            context = "scss-var"
        elif prop.startswith("@") and suffix == ".less":
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
# Vue, Svelte, Astro and HTML files (LC-B5)
# ---------------------------------------------------------------------------

def _spaces(s: str) -> str:
    return re.sub(r"[^\r\n]", " ", s)


def keep_only(text: str, start: int, end: int) -> str:
    """`text` blanked outside [start, end), newlines kept: offsets and line
    numbers stay those of the file."""
    return _spaces(text[:start]) + text[start:end] + _spaces(text[end:])


def blank_spans(text: str, spans: Iterable[tuple[int, int]]) -> str:
    out, at = [], 0
    for a, b in sorted(spans):
        if b <= at:
            continue
        a = max(a, at)
        out += [text[at:a], _spaces(text[a:b])]
        at = b
    return "".join(out) + text[at:]


def script_blocks(text: str) -> list[tuple[int, int]]:
    """Each `<script>` block's body, and an Astro component's frontmatter. A
    `<script>` inside the frontmatter's code is not a block (CodeRabbit on #116)."""
    front = ASTRO_FRONTMATTER_RE.match(text)
    clean = HTML_COMMENT_RE.sub(lambda m: _spaces(m.group(0)), text)
    if front:
        clean = blank_spans(clean, [front.span(1)])
    spans = [m.span(1) for m in SCRIPT_BLOCK_RE.finditer(clean)]
    return ([front.span(1)] if front else []) + spans


def style_blocks(text: str) -> list[tuple[int, int, str | None, str]]:
    """Each `<style>` block outside an HTML comment and a script: its body's
    (start, end), the suffix it is read as (None for a language the scanner
    cannot follow) and its `lang`. apply_codemod rewrites the same blocks."""
    clean = blank_spans(HTML_COMMENT_RE.sub(lambda m: _spaces(m.group(0)), text),
                        script_blocks(text))
    out = []
    for m in STYLE_BLOCK_RE.finditer(clean):
        lang = STYLE_LANG_RE.search(m.group(2))
        lang_name = lang.group(1).lower() if lang else ""
        out.append((m.start(3), m.end(3), STYLE_LANG_SUFFIX.get(lang_name), lang_name))
    return out


def template_of(text: str) -> str:
    """The markup outside its style and script blocks and its comments."""
    spans = [(s, e) for s, e, _, _ in style_blocks(text)] + script_blocks(text)
    spans += [m.span() for m in HTML_COMMENT_RE.finditer(text)]
    return blank_spans(text, spans)


def extract_markup(path: Path, text: str, unread: list[str], tw: TwSpacing | None = None) -> list[Literal]:
    out: list[Literal] = []
    fname = norm_path(path)
    component = path.suffix.lower() in SFC_EXT or is_component_file(path)
    for start, end, suffix, lang in style_blocks(text):
        if suffix is None:
            unread.append(f'{fname} (<style lang="{lang}">)')
            continue
        out.extend(extract_css(path, keep_only(text, start, end), suffix=suffix,
                               component=component))
    for start, end in script_blocks(text):
        out.extend(extract_js(path, keep_only(text, start, end), component=component, tw=tw))
    template = template_of(text)
    # style="" is an inline style: hand work (Law 4), as JSX's style={{}} is.
    for m in STYLE_ATTR_RE.finditer(template):
        group = 1 if m.group(1) is not None else 2
        body, at = m.group(group), m.start(group)
        for decl in re.finditer(r"[^;]+", body):
            prop, colon, value = decl.group(0).partition(":")
            if not colon or "{" in value:          # Svelte and Astro interpolate with {…}
                continue
            value_at = at + decl.start() + len(prop) + 1
            value = re.sub(r"var\(\s*--[\w-]+", lambda mm: " " * len(mm.group(0)), value)
            out.extend(literals_from_value(
                prop.strip().lower(), value, value_at, text, file=fname,
                context="inline-style", selector='style=""', component=component,
                declaration=re.sub(r"\s+", " ", decl.group(0).strip()),
            ))
    out.extend(tailwind_literals(CLASSNAME_RE.finditer(template), text, fname, component, tw=tw))
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
            # A selector or a media query (`'&:hover'`) keys a nested object.
            if key and (re.fullmatch(r"[-\w$]+", key) or raw_value.lstrip().startswith("{")):
                out.append((key, raw_value, i + 1))
            i = v + 1
            del key_start
            continue
        i += 1
    return out


def tailwind_literals(matches: Iterable[re.Match], text: str, fname: str, component: bool,
                      claimed=lambda pos: False, tw: TwSpacing | None = None,
                      class_list=lambda sm: True) -> list[Literal]:
    """The arbitrary values (`p-[13px]`) in each matched class list, and with a
    v4 theme that keeps `--spacing` (`tw`), its numeric classes (`p-4`) in
    each match `class_list` takes for a class list."""
    out: list[Literal] = []
    seen: set[tuple[int, int]] = set()
    step = tw.length() if tw else None
    for sm in matches:
        group = next((g for g in sm.groups() if g is not None), None)
        if group is None:
            continue
        base = sm.start(sm.lastindex or 1)
        if claimed(base):
            continue
        for m in TW_TOKEN_RE.finditer(group) if step and class_list(sm) else ():
            variants, utility, at = tw_utility(m.group(0))
            if tw.prefix and variants[:1] != [tw.prefix]:
                continue
            num = TW_NUMERIC_RE.fullmatch(utility)
            if not num or (num.group(1) and num.group(2) not in TW_NEGATIVE_UTILITIES):
                continue
            times = tw_multiplier(num.group(3))
            span = (base + m.start(), base + m.end())
            if not times or span in seen:          # `p-0` is no design value
                continue
            seen.add(span)
            ln, col = line_col(text, span[0] + at)
            value = -times * step[0] if num.group(1) else times * step[0]
            out.append(Literal(
                kind="length", raw=f"{tw.prefix}:{utility}" if tw.prefix else utility,
                normalized=normalize_length(f"{value:.6g}", step[1]),
                prop=f"tw:{num.group(2)}", file=fname, line=ln, col=col,
                context="tailwind-spacing", selector="className",
                component=component, declaration=m.group(0),
            ))
        for m in TW_ARBITRARY_RE.finditer(group):
            span = (base + m.start(), base + m.end())
            if span in seen:
                continue
            seen.add(span)
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
    return out


# The properties a style object's key can name; a key outside them (`xs`, `md`,
# `primary`) under one that is (`padding: { xs: '8px' }`) takes its parent's.
STYLE_PROPS = (SPACING_PROPS | SIZE_PROPS | RADIUS_PROPS | BORDER_WIDTH_PROPS | COLOR_PROPS
               | SHADOW_PROPS | MOTION_PROPS | set(BORDER_SHORTHAND)
               | {"font", "font-size", "line-height", "letter-spacing", "z-index", "border"})
# MUI's and Panda's shorthand keys, by their CSS property (kebab-cased).
STYLE_SHORTHANDS = {
    "bg": "background", "bgcolor": "background-color", "bg-color": "background-color",
    "p": "padding", "pt": "padding-top", "pr": "padding-right", "pb": "padding-bottom",
    "pl": "padding-left", "px": "padding-inline", "py": "padding-block",
    "m": "margin", "mt": "margin-top", "mr": "margin-right", "mb": "margin-bottom",
    "ml": "margin-left", "mx": "margin-inline", "my": "margin-block",
    "w": "width", "h": "height", "rounded": "border-radius",
}


def object_style_literals(clean: str, text: str, open_at: int, end: int, *, fname: str,
                          component: bool, numbers_are_px: bool, selector: str) -> list[Literal]:
    """Every literal in a style object, nested objects included: selectors
    (`'&:hover'`), media queries, variants and responsive values."""
    out: list[Literal] = []

    def leaf(key: str, prop: str, v: str, at: int) -> None:
        if v[:1] in "\"'" and v[-1:] == v[:1] and len(v) >= 2:
            v_text, v_off = v[1:-1], at + 1
        elif v[:1] == "`" and v[-1:] == "`" and "${" not in v and len(v) >= 2:
            v_text, v_off = v[1:-1], at + 1
        elif numbers_are_px and re.fullmatch(r"-?\d*\.?\d+", v):
            v_text, v_off = (v if prop in JSX_UNITLESS else f"{v}px"), at
        else:
            return                            # an expression, a theme step or a token name
        out.extend(literals_from_value(
            prop, v_text, v_off, text, file=fname, context="style-object",
            selector=selector, component=component, declaration=f"{key}: {v}",
        ))

    def walk(start: int, stop: int, inherited: str | None, depth: int) -> None:
        if depth > 32:                        # no real style object nests this deep
            return
        for key, raw_value, rel in parse_style_object(clean[start:stop]):
            prop = STYLE_SHORTHANDS.get(kebab(key), kebab(key))
            at = start + rel
            v = raw_value.strip()
            lead = len(raw_value) - len(raw_value.lstrip())
            if prop not in STYLE_PROPS and inherited:
                prop = inherited
            if v.startswith("{"):
                inner = at + lead
                walk(inner + 1, match_braces(clean, inner) - 1,
                     prop if prop in STYLE_PROPS else inherited, depth + 1)
            elif v.startswith("["):
                # A responsive array, one value per breakpoint (Codex on #116).
                for item, item_at in array_items(clean, at + lead):
                    if item.startswith("{"):
                        walk(item_at + 1, match_braces(clean, item_at) - 1, prop, depth + 1)
                    else:
                        leaf(key, prop, item, item_at)
            else:
                leaf(key, prop, v, at + lead)

    walk(open_at + 1, end - 1, None, 0)
    return out


def array_items(text: str, open_at: int) -> list[tuple[str, int]]:
    """Each top-level item of the array literal whose `[` is at `open_at`,
    stripped, with the offset it starts at."""
    out, depth, i, n, start = [], 0, open_at, len(text), open_at + 1

    def push(a: int, b: int) -> None:
        item = text[a:b]
        if item.strip():
            out.append((item.strip(), a + len(item) - len(item.lstrip())))

    while i < n:
        ch = text[i]
        if ch in "\"'`":
            j = i + 1
            while j < n and text[j] != ch:
                j += 2 if text[j] == "\\" else 1
            i = j
        elif ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
            if depth == 0:
                push(start, i)
                break
        elif ch == "," and depth == 1:
            push(start, i)
            start = i + 1
        i += 1
    return out


def extract_js(path: Path, text: str, *, component: bool | None = None,
               tw: TwSpacing | None = None) -> list[Literal]:
    out: list[Literal] = []
    clean = blank_js_comments(text)
    if component is None:
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

    # ---- Style objects: MUI sx, css({}), vanilla-extract, styled({}) -------
    vanilla = bool(VANILLA_IMPORT_RE.search(clean))
    panda = bool(PANDA_IMPORT_RE.search(clean))
    for m in OBJECT_STYLE_RE.finditer(clean):
        name = m.group("prop") or m.group("fn") or "styled"
        if claimed(m.start()) or (name in VANILLA_ONLY and not vanilla) or (name in PANDA_ONLY and not panda):
            continue
        open_at = m.end()
        end = match_braces(clean, open_at)
        claim(m.start(), end)
        # A number is a theme step in MUI's sx and a token name in Panda's
        # functions, not a pixel length, so only their strings are counted.
        out.extend(object_style_literals(
            clean, text, open_at, end, fname=fname, component=component,
            numbers_are_px=not (name == "sx" or panda),
            selector=f"{name}={{{{...}}}}" if m.group("prop") else f"{name}({{...}})"))

    # ---- Tailwind arbitrary values ----------------------------------------
    out.extend(tailwind_literals(
        list(CLASSNAME_RE.finditer(clean)) + list(CLASSLIST_STRING_RE.finditer(clean)),
        text, fname, component, claimed, tw, in_class_list(class_list_spans(clean))))

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
# Tailwind v4's numeric classes (LC-B5)
# ---------------------------------------------------------------------------

# In v4, `p-4` is `padding: calc(var(--spacing) * 4)` (tailwindcss.com/docs/padding).
# While the theme keeps `--spacing`, every multiple of it is a class, and the
# census counts each at its value. These are the utilities whose number
# multiplies `--spacing` and that the contract has roles for; translate-,
# scroll-m-, indent-, basis- and border-spacing- read it too, and are
# tw_probe's to refuse.
TW_SPACING_UTILITIES = (
    "p", "px", "py", "ps", "pe", "pt", "pr", "pb", "pl", "pbs", "pbe",
    "m", "mx", "my", "ms", "me", "mt", "mr", "mb", "ml", "mbs", "mbe",
    "gap", "gap-x", "gap-y", "space-x", "space-y",
    "inset", "inset-x", "inset-y", "top", "right", "bottom", "left",
    "w", "h", "min-w", "min-h", "max-w", "max-h", "size", "leading",
)
# The ones a leading `-` negates (`-mt-4`, `-top-2`); `-p-4` generates nothing.
TW_NEGATIVE_UTILITIES = {"m", "mx", "my", "ms", "me", "mt", "mr", "mb", "ml", "mbs", "mbe",
                         "space-x", "space-y", "inset", "inset-x", "inset-y",
                         "top", "right", "bottom", "left"}
TW_NUMERIC_RE = re.compile(
    r"(-?)(" + "|".join(re.escape(u) for u in sorted(TW_SPACING_UTILITIES, key=len, reverse=True))
    + r")-(\d+(?:\.\d+)?)")
# A class list's tokens; a `:` inside brackets or parentheses separates no variant.
TW_TOKEN_RE = re.compile(r"[^\s'\"`{},]+")
TW_IMPORT_RE = re.compile(
    r"""@import\s+(?:url\(\s*)?(["']?)([^"'\s;)]+)\1\s*\)?([^;]*);""")
TW_PREFIX_RE = re.compile(r"\bprefix\(\s*([A-Za-z][\w-]*)\s*\)")
TW_THEME_RE = re.compile(r"@theme\b([^{;]*)\{")
# The stock theme's `--spacing` (tailwindcss.com/docs/theme), when the
# project's own copy of Tailwind is not installed to read it from.
TW_STOCK_SPACING = "0.25rem"


@dataclass
class TwSpacing:
    """What a Tailwind v4 entry makes of `--spacing`: its value (None once a
    theme clears it), the class prefix, and where the value came from."""

    entry: str
    value: str | None
    prefix: str
    source: str
    unread: list[str]

    def length(self) -> tuple[float, str] | None:
        m = LENGTH_RE.fullmatch(self.value or "")
        return (float(m.group(1)), m.group(2).lower()) if m else None


def tw_utility(token: str) -> tuple[list[str], str, int]:
    """A class token's variants, its utility and where the utility starts:
    `md:hover:-mt-4!` is (['md', 'hover'], '-mt-4', 9). The important mark
    (`!`, at either end) is dropped, and a `:` inside brackets or parentheses
    separates no variant (`[&:hover]:p-4`)."""
    parts, depth, start = [], 0, 0
    for i, ch in enumerate(token):
        if ch in "[(":
            depth += 1
        elif ch in "])":
            depth = max(0, depth - 1)
        elif ch == ":" and depth == 0:
            parts.append(token[start:i])
            start = i + 1
    utility = token[start:]
    if utility.startswith("!"):
        utility, start = utility[1:], start + 1
    return parts, utility.rstrip("!"), start


def tw_multiplier(text: str) -> float | None:
    """The number of a numeric class, or None when Tailwind generates nothing
    for it: v4 (4.3.3, tried) takes a multiple of 0.25 written as JavaScript
    prints it, so `p-2.5` and `p-2.25` are classes and `p-2.50`, `p-04` and
    `p-0.3` are not."""
    num = float(text)
    if num * 4 != int(num * 4):
        return None
    canonical = str(int(num)) if num.is_integer() else repr(num)
    return num if canonical == text else None


# The calls whose strings are class lists: eslint-plugin-better-tailwindcss
# 4.9.0's default callees, and the classNames and classnames Part 5 adds.
CLASS_HELPERS = ("cc", "clb", "clsx", "cn", "cnb", "ctl", "cva", "cx", "dcnb", "objstr",
                 "tv", "twJoin", "twMerge", "classNames", "classnames")
CLASS_HELPER_RE = re.compile(r"(?<![\w$])(?:" + "|".join(CLASS_HELPERS) + r")\s*\(")
CLASS_EXPRESSION_RE = re.compile(r"\b(?:className|class)\s*=\s*\{")


def blank_js_strings(text: str) -> str:
    """`text` with each string's and template's contents blanked, the quotes
    and a template's `${…}` code kept, so a search for syntax never matches
    inside data. Same length, so offsets carry over."""
    out, i, n = list(text), 0, len(text)
    modes, braces = ["code"], [0]          # a brace count for each code level
    while i < n:
        ch = text[i]
        if modes[-1] == "template":
            if ch == "`":
                modes.pop()
            elif ch == "$" and text[i + 1:i + 2] == "{":
                modes.append("code")
                braces.append(0)
                i += 1
            elif ch == "\\":
                out[i] = " "
                if i + 1 < n and text[i + 1] != "\n":
                    out[i + 1] = " "
                i += 1
            elif ch != "\n":
                out[i] = " "
        elif ch in "'\"":
            j = i + 1
            while j < n and text[j] not in (ch, "\n"):
                step = 2 if text[j] == "\\" and j + 1 < n and text[j + 1] != "\n" else 1
                for k in range(j, j + step):
                    out[k] = " "
                j += step
            i = j
        elif ch == "`":
            modes.append("template")
        elif ch == "{":
            braces[-1] += 1
        elif ch == "}":
            if braces[-1] == 0 and len(modes) > 1:       # the end of a ${ … }
                modes.pop()
                braces.pop()
            else:
                braces[-1] -= 1
        i += 1
    return "".join(out)


def class_list_spans(clean: str) -> list[tuple[int, int]]:
    """Where a script's class lists are: a `className={…}` expression and a
    class helper's arguments (`cn("p-4", ok && "mt-1")`). A numeric class is
    read only there, since a bare `"p-4"` may be any data (Codex on #129).
    Both are found in code only: `'cn('` is a string, not a call."""
    code = blank_js_strings(clean)
    spans = [(m.end(), match_braces(code, m.end() - 1)) for m in CLASS_EXPRESSION_RE.finditer(code)]
    for m in CLASS_HELPER_RE.finditer(code):
        depth, i, quote = 1, m.end(), ""
        while i < len(code) and depth:
            ch = code[i]
            if quote:
                if ch == quote:
                    quote = ""
            elif ch in "'\"`":
                quote = ch
            elif ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
            i += 1
        spans.append((m.end(), i))
    return spans


def in_class_list(spans: Sequence[tuple[int, int]]) -> Callable[[re.Match], bool]:
    """Whether a matched string is a class list: a `class=""` or `className=""`
    attribute, or a string inside one of `spans`."""
    return lambda sm: sm.re is CLASSNAME_RE or any(a <= sm.start() < b for a, b in spans)


def _theme_blocks(css: str) -> Iterator[tuple[str, list[str]]]:
    """Each `@theme` block's options and its own declarations; a nested block
    (`@keyframes`) is skipped, as tw_probe's themeVariables() skips it."""
    for m in TW_THEME_RE.finditer(css):
        decls, depth, i, start = [], 1, m.end(), m.end()
        while i < len(css) and depth:
            ch = css[i]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    decls.append(css[start:i])
                elif depth == 1:
                    start = i + 1
            elif ch == ";" and depth == 1:
                decls.append(css[start:i])
                start = i + 1
            i += 1
        yield m.group(1), decls


def _package_sheet(target: str, start: Path) -> Path | None:
    """A package's stylesheet as an `@import` finds it: the package in the
    nearest `node_modules`, then its subpath, its package.json's `style`, or
    its `index.css`. None when it is not installed."""
    parts = target.split("/")
    cut = 2 if target.startswith("@") else 1
    name, sub = "/".join(parts[:cut]), "/".join(parts[cut:])
    for folder in [start, *start.parents]:
        root = folder / "node_modules" / name
        if not root.is_dir():
            continue
        if sub:
            found = root / sub
            return found if found.is_file() or found.suffix else found.with_name(found.name + ".css")
        try:
            meta = json.loads((root / "package.json").read_bytes())
        except (OSError, ValueError):
            meta = {}
        exports = meta.get("exports") if isinstance(meta, dict) else None
        dot = exports.get(".") if isinstance(exports, dict) else None
        for choice in (meta.get("style") if isinstance(meta, dict) else None,
                       dot.get("style") if isinstance(dot, dict) else None, "index.css"):
            if isinstance(choice, str) and (root / choice).is_file():
                return root / choice
        return None
    return None


def _stock_spacing(entry: Path) -> tuple[str, str]:
    """`--spacing` as the project's installed Tailwind sets it, else the docs'."""
    for folder in [entry.parent, *entry.parent.parents]:
        theme = folder / "node_modules" / "tailwindcss" / "theme.css"
        if theme.is_file():
            try:
                found = re.search(r"--spacing\s*:\s*([^;]+);", theme.read_text(encoding="utf-8"))
            except OSError:
                break
            if found:
                return found.group(1).strip(), norm_path(theme)
            break
    return TW_STOCK_SPACING, "Tailwind's stock theme"


def tailwind_spacing(entry: Path) -> TwSpacing | None:
    """What a v4 entry stylesheet makes of `--spacing`, or None when it is no
    entry (no `@import "tailwindcss"` or `tailwindcss/utilities`). The sheets
    are read in cascade order, each import where it stands, and the theme as
    Tailwind builds it: `--*: initial`, `--spacing-*: initial` (it takes
    `--spacing` with it) and `--spacing: initial` clear it, and a `default`
    block never overrides a value the project set."""
    state = {"value": None, "default": True, "prefix": "", "source": "", "entry": False}
    unread: list[str] = []
    seen: set[str] = set()

    def read(sheet: Path) -> None:
        key = os.path.normcase(str(sheet.resolve()))
        if key in seen:
            return
        seen.add(key)
        try:
            css = blank_css_comments(sheet.read_text(encoding="utf-8", errors="replace"),
                                     slash_comments=False)
        except OSError:
            unread.append(norm_path(sheet))
            return
        for m in TW_IMPORT_RE.finditer(css):
            target, options = m.group(2), m.group(3)
            if target == "tailwindcss" or target.startswith("tailwindcss/"):
                sub = re.sub(r"\.css$", "", target[len("tailwindcss/"):]) if "/" in target else ""
                if sub in ("", "utilities"):
                    state["entry"] = True
                if sub in ("", "theme"):
                    if state["value"] is None or state["default"]:
                        state["value"], state["source"] = _stock_spacing(entry)
                        state["default"] = True
                prefix = TW_PREFIX_RE.search(options)
                if prefix:
                    state["prefix"] = prefix.group(1)
            elif re.match(r"[a-z][\w+.-]*:", target) or target.startswith("//"):
                continue                              # a URL: Tailwind leaves it to the browser
            else:
                found = Path(os.path.normpath(sheet.parent / target))     # named as the census names it
                if not found.exists() and not found.suffix:
                    found = found.with_name(found.name + ".css")
                if not found.exists() and not target.startswith((".", "/")):
                    package = _package_sheet(target, sheet.parent)
                    if package is None:
                        unread.append(target)                 # not installed
                        continue
                    found = package
                read(found)
        for options, decls in _theme_blocks(css):
            prefix = TW_PREFIX_RE.search(options)
            if prefix:
                state["prefix"] = prefix.group(1)
            default = bool(re.search(r"\bdefault\b", options))
            for decl in decls:
                name, colon, value = decl.partition(":")
                name, value = name.strip(), value.strip()
                if not colon:
                    continue
                if value == "initial" and name in ("--*", "--spacing-*", "--spacing"):
                    state["value"], state["default"] = None, False
                elif name == "--spacing" and (not default or state["value"] is None
                                              or state["default"]):
                    state["value"], state["default"] = value, default
                    state["source"] = norm_path(sheet)

    read(entry)
    if not state["entry"]:
        return None
    return TwSpacing(entry=norm_path(entry), value=state["value"], prefix=state["prefix"],
                     source=state["source"], unread=unread)


# ---------------------------------------------------------------------------
# Walking
# ---------------------------------------------------------------------------

def iter_files(paths: Sequence[str], *, include_vendor: bool,
               include_tokens: bool,
               vendor_skipped: list[Path] | None = None,
               unread: list[Path] | None = None) -> Iterator[Path]:
    """Files to scan. A file named explicitly is always scanned (the user asked
    for it); inside a folder, vendor files are left out and collected in
    `vendor_skipped`, so the census can say what it did not count. Indented
    Sass is never scanned, and is collected in `unread`."""
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
            if fp.suffix.lower() == INDENTED_SASS_EXT and unread is not None:
                unread.append(fp)
            if fp.suffix.lower() not in CSS_EXT | JS_EXT | MARKUP_EXT:
                continue
            if not include_vendor and not explicit and is_vendor(fp):
                if vendor_skipped is not None:
                    vendor_skipped.append(fp)
                continue
            if not include_tokens and is_token_file(fp):
                continue
            yield fp


def tailwind_theme(paths: Sequence[str], *, include_vendor: bool,
                   problems: list[str]) -> tuple[TwSpacing | None, list[TwSpacing]]:
    """The v4 entries among the stylesheets, token files included, and the one
    `--spacing` their numeric classes are counted at. Entries that disagree
    count none: the census cannot tell which entry builds which file."""
    entries: list[TwSpacing] = []
    for fp in iter_files(paths, include_vendor=include_vendor, include_tokens=True):
        if fp.suffix.lower() not in (".css", ".pcss"):
            continue
        try:
            head = fp.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if "tailwindcss" in head:
            found = tailwind_spacing(fp)
            if found:
                entries.append(found)
    if not entries:
        return None, entries
    unread = sorted({u for e in entries for u in e.unread})
    if unread:
        # A stylesheet the census cannot read can set or clear --spacing
        # (Codex on #129), so a count at the value read would be wrong.
        more = f" and {len(unread) - 5} more" if len(unread) > 5 else ""
        problems.append(f"the Tailwind v4 entries import what the census could not read "
                        f"({', '.join(unread[:5])}{more}), which can set --spacing, so the numeric "
                        f"classes (p-4) were not counted: install the dependencies and run it again")
        return None, entries
    kinds = {(e.value, e.prefix) for e in entries}
    if len(kinds) > 1:
        said = ", ".join(f"{e.entry} {e.value or 'cleared'}" for e in entries)
        problems.append(f"the Tailwind v4 entries disagree on --spacing ({said}), so the numeric "
                        f"classes (p-4) were not counted: run the census on each app")
        return None, entries
    tw = entries[0]
    if tw.value is None:
        problems.append(f"{tw.entry} clears --spacing, so a numeric class (p-4) generates "
                        f"nothing there and is not counted: tw_probe.mjs lists any left")
        return None, entries
    if not tw.length():
        problems.append(f"--spacing is `{tw.value}` ({tw.source}), not a length the census "
                        f"can multiply, so the numeric classes (p-4) were not counted")
        return None, entries
    return tw, entries


def extract(paths: Sequence[str], *, include_vendor: bool = False,
            include_tokens: bool = False,
            tailwind: dict | None = None) -> tuple[list[Literal], list[str]]:
    literals: list[Literal] = []
    problems: list[str] = []
    vendor_skipped: list[Path] = []
    unread: list[Path] = []
    unread_blocks: list[str] = []
    tw, entries = tailwind_theme(paths, include_vendor=include_vendor, problems=problems)
    if tailwind is not None and entries:
        tailwind.update(entries=[asdict(e) for e in entries],
                        spacing=tw.value if tw else None, prefix=tw.prefix if tw else "")
    for fp in iter_files(paths, include_vendor=include_vendor,
                         include_tokens=include_tokens,
                         vendor_skipped=vendor_skipped, unread=unread):
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
            elif fp.suffix.lower() in MARKUP_EXT:
                literals.extend(extract_markup(fp, text, unread_blocks, tw))
            else:
                literals.extend(extract_js(fp, text, tw=tw))
        except Exception as exc:                     # noqa: BLE001 — never abort a census
            problems.append(f"{fp}: parse failed ({type(exc).__name__}: {exc})")
    if vendor_skipped:
        names = ", ".join(norm_path(p) for p in vendor_skipped[:5])
        more = f" and {len(vendor_skipped) - 5} more" if len(vendor_skipped) > 5 else ""
        problems.append(f"excluded {len(vendor_skipped)} vendor file(s): {names}{more} "
                        f"— you layer vendor CSS, you do not migrate it; "
                        f"--include-vendor counts them")
    if unread:
        names = ", ".join(norm_path(p) for p in unread[:5])
        more = f" and {len(unread) - 5} more" if len(unread) > 5 else ""
        problems.append(f"did not read {len(unread)} indented Sass file(s): {names}{more} "
                        f"— the census follows braces, which .sass does not have; "
                        f"count their literals in the compiled CSS, or convert them to .scss")
    if unread_blocks:
        names = ", ".join(unread_blocks[:5])
        more = f" and {len(unread_blocks) - 5} more" if len(unread_blocks) > 5 else ""
        problems.append(f"did not read {len(unread_blocks)} <style> block(s) in a language the census "
                        f"cannot follow: {names}{more} — count their literals in the compiled CSS")
    if tw:
        counted = sum(1 for l in literals if l.context == "tailwind-spacing")
        problems.append(f"counted {counted} numeric Tailwind class(es) (p-4 is 4 x --spacing) at "
                        f"--spacing: {tw.value}, from {tw.source} through {tw.entry}"
                        + (f", prefix {tw.prefix}:" if tw.prefix else ""))
        if tailwind is not None:
            tailwind["counted"] = counted
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
                "the wrong directory.\n"
                + "".join(f"  ! {p}\n" for p in problems))

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
                problems: Sequence[str], tailwind: dict | None = None) -> str:
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
    if tailwind:                              # the v4 entries and the --spacing counted at
        payload["tailwind"] = tailwind
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
    # Against every file the census reads, a folder's included (the audit's
    # class 5; Codex on #136).
    scanned = iter_files(args.paths, include_vendor=args.include_vendor,
                         include_tokens=args.include_tokens)
    clash = refuse_overwrite(args.output, *args.paths, *scanned)
    if clash:
        print(f"extract_literals: {clash}", file=sys.stderr)
        return 2

    tailwind: dict = {}
    literals, problems = extract(args.paths,
                                 include_vendor=args.include_vendor,
                                 include_tokens=args.include_tokens, tailwind=tailwind)

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
        text = render_json(literals, args.paths, problems, tailwind)
    elif args.format == "csv":
        text = render_csv(literals)
    else:
        text = render_report(literals, top=args.top, problems=problems)

    if args.output:
        try:
            Path(args.output).parent.mkdir(parents=True, exist_ok=True)   # as the other scripts' -o do
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
