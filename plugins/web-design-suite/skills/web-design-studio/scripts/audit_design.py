#!/usr/bin/env python3
"""
audit_design.py — the enforcement gate for the web-design-studio skill.

This script is Law 9. Nothing ships until it is clean.

It exists because every rule in this skill is the kind of rule that people
agree with and then violate at 6pm on a Thursday. Code review catches maybe
half; a script catches all of it, in a second, for free, forever.

What it checks
--------------
  L1  Tokens or nothing        raw lengths, colors, durations, z-indexes,
                               shadows, font sizes and weights outside the
                               token file
  L2  Parents own the gaps     outer margins on children in component files
  L3  The scale is closed      values that are not on the spacing/type scale
  L4  One home per component   JSX inline styles that set visual properties,
                               plus a CROSS-FILE pass: a class styled from
                               two files, or the same property owned twice
  L5  Layers, not specificity  !important, IDs, nesting depth, unlayered CSS,
                               layer-statement order
  L6  Semantic before primitive  Tier-1 tokens read from component code

Usage
-----
    python -m scripts.audit_design src/
    python -m scripts.audit_design src/ --json
    python -m scripts.audit_design src/ --strict          # warnings fail too
    python -m scripts.audit_design $(git diff --cached --name-only)

What it reads
-------------
    .css .scss .less .pcss              every declaration
    .js .jsx .ts .tsx .mjs .cjs         inline styles, class strings, colours
    .html .htm .vue .svelte .astro      <style> blocks, style="" attributes,
                                        class attributes (HTML email is left
                                        to email-template-system's lint_email)

A file named explicitly with any other extension is skipped and listed, never
guessed at. So is indented Sass (.sass): it has no braces for the scanner to
follow, and reading it would pass it as clean. A folder with nothing auditable in it is an error, not "clean".

Adopting it on a legacy codebase
--------------------------------
    python -m scripts.audit_design src/ --write-baseline .design-baseline.json
    python -m scripts.audit_design src/                   # only NEW findings fail

The baseline records existing violations so the gate can be turned on today
and the debt paid down deliberately, instead of the gate being turned off.
Its keys are paths relative to the baseline file, so `src/`, `./src` and the
absolute path all match, from any working directory.

Escape hatches (use sparingly, they are visible in review)
---------------------------------------------------------
    /* design-audit-ignore-next-line: L2 -- CMS flow container, see ADR-014 */
    /* design-audit-ignore-file: L1 -- generated, do not hand-edit */

Exit codes: 0 clean · 1 violations found · 2 bad invocation.
"""

from __future__ import annotations

import argparse
import bisect
import json
import os
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Iterable, Iterator

# ---------------------------------------------------------------------------
# Configuration — the vocabulary this skill enforces.
# ---------------------------------------------------------------------------

CSS_EXT = {".css", ".scss", ".sass", ".less", ".pcss"}
JS_EXT = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}
# Markup that carries CSS: <style> blocks, style="" attributes, class lists.
TEMPLATE_EXT = {".html", ".htm", ".vue", ".svelte", ".astro"}
# Files whose CSS is plain CSS, where `//` is not a comment (line_comments).
PLAIN_CSS_EXT = {".css", ".pcss", ".html", ".htm"}
KEYFRAMES_AT = re.compile(r"@(-[a-z]+-)?keyframes\b", re.I)
# Sass (design-rules.json: sass). A @mixin or @function body emits nothing
# where it is written. A variable holding a literal is a literal; a breakpoint
# has to be one, because a media query condition cannot read a custom property.
SASS_DEFINITION_AT = re.compile(r"@(mixin|function)\b", re.I)
SASS_FUNCTION_AT = re.compile(r"@function\b", re.I)
SASS_VARIABLE = re.compile(r"^([\w-]+\.)?\$[\w-]+$")
SASS_BREAKPOINT = re.compile(r"\$(bp|breakpoints?)([-_][\w-]*)?$", re.I)

SKIP_DIRS = {
    "node_modules", ".git", "dist", "build", ".next", ".nuxt", ".svelte-kit",
    "coverage", "__pycache__", ".venv", "venv", "vendor", ".turbo", "out",
    # Generated HTML reports and static exports, now that HTML is read.
    "storybook-static", "playwright-report", "test-results", "htmlcov", "_site",
}

# Files where literal values are not merely allowed but required: this is the
# one place a raw value is a design decision rather than a leak.
TOKEN_FILE_PAT = re.compile(
    # tokens.css, brand-tokens.css, deck-tokens.css, design.tokens.css, any
    # file in a tokens/ folder, theme.css, dark-theme.css — the file classes
    # in assets/rules/design-rules.json. A separator before "tokens" and
    # "theme" is required, so "mytokens.css" and "theming.css" are not waved
    # through, and the spec's globs are plural: "brand-token.css" is not.
    r"(^|[/\\])([\w.-]*[-.])?tokens\.(css|scss)$"
    r"|(^|[/\\])tokens[/\\][\w.-]+\.(css|scss)$"
    r"|(^|[/\\])([\w.-]*[-.])?theme\.(css|scss)$"
)
COMPONENT_FILE_PAT = re.compile(
    # A components/ or ui/ folder at any depth, the project root included (the
    # common Next.js layout, SB-A9), a CSS module, and components.css itself,
    # not mycomponents.css: the component file class in design-rules.json.
    # Matched against a lower-case path with forward slashes.
    r"\.module\.|(^|/)(components|ui)/|(^|/)components\.css$"
)

# Nesting below the top-level rule (design-rules.json).
MAX_NESTING = 2


def pseudo_classes_only(selector: str) -> bool:
    """`:hover`, `:is(a, b):focus` — every list item starts with a
    pseudo-class (not `&`, and not a `::pseudo-element`)."""
    parts = [p.strip() for p in selector.split(",")]
    return all(p.startswith(":") and not p.startswith("::") for p in parts if p)

# Generated files are audited against their source, not by hand.
CONFIG_FILE_PAT = re.compile(
    r"(^|[/\\])[\w.-]*\.(config|conf|rc)\.(m|c)?[jt]s$"
    r"|(^|[/\\])(eslint|stylelint|prettier|vite|rollup|webpack|next|tailwind)[\w.-]*\.(m|c)?[jt]s$"
)

GENERATED_MARKERS = ("@generated", "DO NOT EDIT", "AUTO-GENERATED", "Auto-generated")

# Properties whose value must resolve through a token.
SPACING_PROPS = {
    "margin", "margin-top", "margin-right", "margin-bottom", "margin-left",
    "margin-block", "margin-block-start", "margin-block-end",
    "margin-inline", "margin-inline-start", "margin-inline-end",
    "padding", "padding-top", "padding-right", "padding-bottom", "padding-left",
    "padding-block", "padding-block-start", "padding-block-end",
    "padding-inline", "padding-inline-start", "padding-inline-end",
    "gap", "row-gap", "column-gap", "grid-gap", "inset",
    "top", "right", "bottom", "left",
    "inset-block", "inset-block-start", "inset-block-end",
    "inset-inline", "inset-inline-start", "inset-inline-end",
}

# Outer margins — the Law 2 set. Padding is inset and is fine.
OUTER_MARGIN_PROPS = {p for p in SPACING_PROPS if p.startswith("margin")}

COLOR_PROPS = {
    "color", "background", "background-color", "border-color", "outline-color",
    "border-top-color", "border-right-color", "border-bottom-color",
    "border-left-color", "border-block-color", "border-inline-color",
    "fill", "stroke", "caret-color", "text-decoration-color", "accent-color",
    "column-rule-color", "text-emphasis-color",
}
# Shorthands whose value can carry a colour among widths and styles.
COLOR_SHORTHANDS = {
    "border", "border-top", "border-right", "border-bottom", "border-left",
    "border-block", "border-block-start", "border-block-end",
    "border-inline", "border-inline-start", "border-inline-end",
    "outline", "column-rule", "text-decoration",
}

TYPE_PROPS = {"font-size", "line-height", "letter-spacing", "font-weight", "font"}
MOTION_PROPS = {"transition", "transition-duration", "animation",
                "animation-duration", "transition-timing-function",
                "animation-timing-function"}
MOTION_SHORTHANDS = {"transition", "animation"}
RADIUS_PROPS = {"border-radius", "border-start-start-radius",
                "border-start-end-radius", "border-end-start-radius",
                "border-end-end-radius", "border-top-left-radius",
                "border-top-right-radius", "border-bottom-left-radius",
                "border-bottom-right-radius"}
SHADOW_PROPS = {"box-shadow", "text-shadow"}

# Tier-1 primitives that HAVE a Tier-2 role, so reading them from a component
# is a Law 6 violation. Prefixes without a semantic equivalent (--radius-*,
# --stroke-*, --weight-*, --z-*, --bp-*, --font-*, --measure-*, --width-*,
# --tap-min) are deliberately absent: they are primitives with no role layer,
# and using them directly is correct. Weight is one: the hierarchy method sets
# weight without changing size, which no --type-* shorthand can do.
TIER1_WITH_ROLE = {
    "space-": "a proximity/inset role (--gap-related, --pad-card, --space-section)",
    "neutral-": "a color role (--bg-surface, --fg-muted, --border-default)",
    "accent-": "a color role (--bg-accent, --fg-accent, --border-accent)",
    "success-": "a color role (--bg-success, --fg-success)",
    "warning-": "a color role (--bg-warning, --fg-warning)",
    "danger-": "a color role (--bg-danger, --fg-danger)",
    "info-": "a color role",
    "text-": "a type role (--type-body, --type-h2, --type-ui)",
    "leading-": "a type role (--type-*), which carries leading in its shorthand",
    "shadow-": "an elevation role (--elevation-card, --elevation-modal)",
}
# Softer: sometimes you genuinely need one half of a motion pair.
TIER1_MOTION = {"dur-", "ease-"}

# Tokens that START with a Tier-1 prefix but ARE Tier-2 roles. Page rhythm
# lives in the --space-* namespace because it reads better there; the tier is
# a property of the name's meaning, not its first word.
TIER2_EXCEPTIONS = {
    "--space-section", "--space-subsection", "--space-block",
    "--space-fluid-sm", "--space-fluid-md", "--space-fluid-lg", "--space-fluid-xl",
}

# Four or more classes chained in one selector is specificity built to win a
# fight that layers already settled (stylelint's selector-max-specificity
# 0,3,1 draws the same line).
COMPOUND_SEL = re.compile(r"(\.[\w-]+(?:\s*[>+~]?\s*)){3,}\.[\w-]+")

# Non-tokenizable units. Viewport and container units express a relationship to
# the viewport, not a spacing decision; % is relational; ch/ex are typographic.
RELATIONAL_UNIT = re.compile(
    r"^-?\d*\.?\d+(%|ch|ex|fr|dvh|svh|lvh|dvw|svw|lvw|vh|vw|vmin|vmax|cqw|cqh|cqi|cqb|cqmin|cqmax)$"
)
LENGTH_LITERAL = re.compile(r"(?<![\w.#-])-?\d*\.?\d+(px|rem|em|pt|pc|in|cm|mm|q)\b", re.I)
HEX_COLOR = re.compile(r"#[0-9a-fA-F]{3,8}\b")
FUNC_COLOR = re.compile(r"\b(rgba?|hsla?|hwb|lab|lch|oklab|oklch|color)\s*\(", re.I)
NAMED_COLOR = re.compile(
    r"\b(red|blue|green|black|white|gray|grey|yellow|orange|purple|pink|brown|"
    r"cyan|magenta|silver|gold|navy|teal|olive|maroon|lime|aqua|fuchsia)\b", re.I
)
TIME_LITERAL = re.compile(r"(?<![\w.-])\d*\.?\d+m?s\b", re.I)
BEZIER_LITERAL = re.compile(r"\bcubic-bezier\s*\(|\bsteps\s*\(", re.I)
VAR_REF = re.compile(r"var\(\s*(--[\w-]+)")
ID_SELECTOR = re.compile(r"(?<![\w\\\[\"'=])#[a-zA-Z_][\w-]*")

# JSX / Tailwind
TW_ARBITRARY = re.compile(r"(?<![\w])(?:[a-z][\w-]*?)-\[[^\]\s]+\]")
TW_IMPORTANT = re.compile(r"(?<![\w-])!(?:[a-z][\w-]*-)+[\w./\[\]-]+")
TW_SPACE_XY = re.compile(r"(?<![\w-])(?:[a-z]{2}:)*space-[xy]-[\w(][\w().-]*")
# Literal values Tailwind generates whatever the theme says (`--*: initial`
# does not remove them): durations, delays, z-indexes, stroke widths, offsets.
TW_LITERAL = re.compile(
    r"(?<![-\w])(?:duration|delay|-?z|border(?:-[xytrblse])?|ring|ring-offset|outline"
    r"|outline-offset|underline-offset)-\d+(?:\.\d+)?(?![\w./-])")
TW_OPACITY = re.compile(
    r"(?<![-\w])(?:bg|text|border|ring|fill|stroke|outline|shadow|decoration|from|via|to"
    r"|placeholder|accent|caret|divide)-[a-z][\w-]*/\d+(?!\w)")
TW_TIER1_VAR = re.compile(
    r"\(--(?:space-(?!section|subsection|block|fluid)|neutral-|accent-|success-|warning-"
    r"|danger-|info-|text-|leading-|shadow-)[\w-]*\)")
JSX_STYLE = re.compile(r"\bstyle\s*=\s*\{\{")
CLASS_ATTR = re.compile(r"""(?:className|class)\s*=\s*(?:\{?\s*)?["'`]([^"'`]*)["'`]""")
# Arbitrary VARIANTS select a state and carry no value; an image URL and a
# pseudo-element's content string cannot be tokens. Every other arbitrary
# value is off the scale, as the ESLint config also rules.
TW_ARBITRARY_OK = re.compile(
    r"^(?:data|aria|group|peer|has|not|in|supports|nth|nth-last)-\["
    r"|^(?:bg|mask)-\[url\(|^content-\[['\"]")
TW_ARBITRARY_PROPERTY = re.compile(r"(?<![-\w])\[-{0,2}[a-zA-Z][\w-]*:[^\]\s]+\]")
TW_IMPORTANT_SUFFIX = re.compile(r"(?<![\w!\[:-])[a-z][\w:./\[\]()-]*[\w\])]!(?=\s|$)")
# Class strings also arrive as arguments of the class helpers (the ESLint
# config reads the same list), including cva/tv variant maps.
CLASS_HELPER = re.compile(r"\b(?:cn|clsx|classNames|classnames|cva|tv|twMerge|twJoin|cx)\s*\(")
JS_STRING = re.compile(r"""(['"`])((?:\\.|(?!\1)[^\\])*?)\1""", re.S)
# styled-components / emotion templates: their bodies are CSS.
CSS_IN_JS = re.compile(
    r"\b(?:styled(?:\.[A-Za-z]\w*|\s*\([^()]*\))(?:\s*\.attrs\s*\([^()]*\))?|css)\s*`")

# Templates
STYLE_BLOCK = re.compile(r"<style\b[^>]*>(.*?)</style\s*>", re.I | re.S)
SCRIPT_BLOCK = re.compile(r"<script\b[^>]*>(.*?)</script\s*>", re.I | re.S)
TAG_STYLE_ATTR = re.compile(r"""<[a-zA-Z][\w:-]*\b[^>]*?\sstyle\s*=\s*(["'])(.*?)\1""", re.S)
# HTML email cannot use custom properties or layers, so this script's laws do
# not fit it; email-template-system's lint_email is its gate.
EMAIL_MARKERS = ("<!--[if mso", "<!--[if gte mso", "urn:schemas-microsoft-com")

IGNORE_LINE = re.compile(r"design-audit-ignore-next-line\s*:?\s*([\w,\s]*)")
IGNORE_FILE = re.compile(r"design-audit-ignore-file\s*:?\s*([\w,\s]*)")

# Escape hatches with a named reason, for the genuinely-legitimate exceptions.
OPTICAL_PROP = re.compile(r"--[\w-]*(nudge|optical)[\w-]*")

SEVERITY_ORDER = {"error": 0, "warning": 1}


# ---------------------------------------------------------------------------
# Findings
# ---------------------------------------------------------------------------

@dataclass
class Finding:
    file: str
    line: int
    law: str
    rule: str
    severity: str
    message: str
    fix: str
    snippet: str = ""

    def key(self, root: Path | None = None) -> str:
        """Stable identity for baselining. Deliberately excludes the line
        number so that unrelated edits above a violation do not resurrect it.

        With `root` (the baseline file's folder) the path is made relative to
        it, so `src/`, `./src`, `/abs/path/src` and `../src` from a subfolder
        all produce the same key. Keys written before 3.1.0 were relative to
        the working directory, which is where the default baseline lives, so
        they keep matching."""
        path = self.file
        if root is not None and not path.startswith("<"):
            try:
                path = os.path.relpath(Path(path).resolve(), root)
            except ValueError:                    # another drive on Windows
                path = str(Path(path).resolve())
        return portable_key(f"{path}|{self.rule}|{self.snippet.strip()[:120]}")


def portable_key(key: str) -> str:
    """Baseline keys use `/` in the path, so a baseline written on Windows still
    matches on Linux CI and the reverse — including baselines written before
    keys were normalised."""
    path, sep, rest = key.partition("|")
    return path.replace("\\", "/") + sep + rest


# ---------------------------------------------------------------------------
# CSS scanning
# ---------------------------------------------------------------------------

def line_comments(path: Path) -> bool:
    """`//` starts a comment in Sass, Less, a styled template and a single-file
    component's style block, which may be Sass; never in CSS itself, where it
    is part of a value (`--terms: https://…`)."""
    return path.suffix.lower() not in PLAIN_CSS_EXT


def unquoted_url_end(text: str, j: int) -> int | None:
    """The index of the `)` that closes an unquoted address starting at `j`,
    just after `url(`; None when the argument is not one. An unquoted address
    is a single token: no quote, no `(` and no inner whitespace, and an
    escaped character (`\\)`) is part of it."""
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


def strip_css_comments(text: str, slash_comments: bool = True) -> tuple[str, dict[int, str]]:
    """Blank out comments while preserving line numbers and offsets.

    Returns the blanked text plus a map of line number -> original comment
    text, so ignore-pragmas remain readable. `//` comments count only with
    `slash_comments`, and an unquoted `url(…)` is one token either way: the
    `//` in `url(https://cdn…)` is the address, not a comment.
    """
    out = list(text)
    comments: dict[int, str] = {}
    i, n, line = 0, len(text), 1
    while i < n:
        ch = text[i]
        if ch == "\n":
            line += 1
            i += 1
            continue
        if (ch in "uU" and text[i:i + 4].lower() == "url("
                and not (i and (text[i - 1].isalnum() or text[i - 1] in "-_"))):
            end = unquoted_url_end(text, i + 4)
            if end is not None:
                line += text.count("\n", i, end)
                i = end
                continue
            # Otherwise a quoted address, read as a string below, or a Sass
            # expression (`url($asset)`), whose comments are still comments.
        if ch in "\"'":
            quote, i = ch, i + 1
            while i < n and text[i] != quote:
                if text[i] == "\\":
                    i += 1
                elif text[i] == "\n":
                    line += 1
                i += 1
            i += 1
            continue
        if ch == "/" and i + 1 < n and text[i + 1] == "*":
            start, start_line = i, line
            i += 2
            while i + 1 < n and not (text[i] == "*" and text[i + 1] == "/"):
                if text[i] == "\n":
                    line += 1
                i += 1
            i = min(i + 2, n)
            body = text[start:i]
            # Keyed by the line the comment ENDS on: a pragma wrapped over two
            # lines covers the declaration after it, not its own second line.
            comments[line] = comments.get(line, "") + body
            for j in range(start, i):
                if out[j] != "\n":
                    out[j] = " "
            continue
        if slash_comments and ch == "/" and i + 1 < n and text[i + 1] == "/":
            start, start_line = i, line
            while i < n and text[i] != "\n":
                i += 1
            comments[start_line] = comments.get(start_line, "") + text[start:i]
            for j in range(start, i):
                out[j] = " "
            continue
        i += 1
    return "".join(out), comments


@dataclass
class CssDecl:
    prop: str
    value: str
    line: int
    selectors: tuple[str, ...]
    at_rules: tuple[str, ...]
    depth: int


def scan_css(text: str) -> Iterator[CssDecl | tuple]:
    """A deliberately small CSS scanner.

    Not a parser — it does not need to be. It tracks brace nesting, the
    selector at each level, and the enclosing at-rules, which is everything the
    rules below actually ask about.
    """
    buf: list[str] = []
    line = 1
    sel_stack: list[str] = []
    at_stack: list[str] = []
    i, n = 0, len(text)
    paren = 0

    def rule_depth() -> int:
        # At-rules push an empty marker to keep the stack aligned with
        # braces; they are not style-rule nesting and must not count. Nor
        # does a rule of pseudo-classes alone (`:hover`, unlike `&:hover`):
        # stylelint's max-nesting-depth ignores those too (design-rules.json).
        return sum(1 for s in sel_stack if s and not pseudo_classes_only(s))

    while i < n:
        ch = text[i]
        if ch == "\n":
            line += 1
            buf.append(ch)
            i += 1
            continue
        if ch in "\"'":
            quote = ch
            buf.append(ch)
            i += 1
            while i < n and text[i] != quote:
                if text[i] == "\\" and i + 1 < n:
                    buf.append(text[i]); i += 1
                if text[i] == "\n":
                    line += 1
                buf.append(text[i]); i += 1
            if i < n:
                buf.append(text[i]); i += 1
            continue
        if ch == "#" and text.startswith("{", i + 1):
            # Sass interpolation, `.card-#{$name}`: text, whose braces open
            # and close nothing (SB-A24).
            j, nested = i + 1, 0
            while j < n:
                if text[j] == "{":
                    nested += 1
                elif text[j] == "}":
                    nested -= 1
                    if nested == 0:
                        break
                j += 1
            chunk = text[i:j + 1]
            line += chunk.count("\n")
            buf.append(chunk)
            i = j + 1
            continue
        if ch == "(":
            paren += 1
        elif ch == ")":
            paren = max(0, paren - 1)

        if ch == "{" and paren == 0:
            head = "".join(buf).strip()
            buf = []
            if head.startswith("@"):
                at_stack.append(head)
                sel_stack.append("")          # keeps depth bookkeeping simple
                yield ("at_open", head, line, tuple(at_stack))
            else:
                sel_stack.append(head)
                yield ("rule_open", head, line, rule_depth(), tuple(at_stack))
            i += 1
            continue

        if ch == "}" and paren == 0:
            leftover = "".join(buf).strip()
            if leftover and ":" in leftover:
                p, _, v = leftover.partition(":")
                yield CssDecl(p.strip().lower(), v.strip(), line,
                              tuple(s for s in sel_stack if s),
                              tuple(at_stack), rule_depth())
            buf = []
            if sel_stack:
                closed = sel_stack.pop()
                if not closed and at_stack:
                    at_stack.pop()
            yield ("rule_close", "", line, rule_depth())
            i += 1
            continue

        if ch == ";" and paren == 0:
            stmt = "".join(buf).strip()
            buf = []
            if stmt.startswith("@"):
                yield ("at_statement", stmt, line, tuple(at_stack))
            elif ":" in stmt:
                p, _, v = stmt.partition(":")
                yield CssDecl(p.strip().lower(), v.strip(), line,
                              tuple(s for s in sel_stack if s),
                              tuple(at_stack), rule_depth())
            i += 1
            continue

        buf.append(ch)
        i += 1


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def is_token_file(path: Path) -> bool:
    return bool(TOKEN_FILE_PAT.search(str(path).replace(os.sep, "/")))


def is_component_file(path: Path) -> bool:
    """A component file is where Laws 2 and 6 bite hardest."""
    return bool(COMPONENT_FILE_PAT.search(str(path).replace(os.sep, "/").lower()))


def in_layer(at_rules: Iterable[str], name: str) -> bool:
    return any(a.startswith("@layer") and name in a for a in at_rules)


VAR_MARK = " var() "


def _close_paren(text: str, open_at: int) -> int:
    """Index of the `)` matching the `(` at `open_at` (len(text) if unmatched)."""
    depth = 0
    for k in range(open_at, len(text)):
        if text[k] == "(":
            depth += 1
        elif text[k] == ")":
            depth -= 1
            if depth == 0:
                return k
    return len(text)


def strip_var_refs(value: str) -> str:
    """`value` with every var(…) reference — fallback included, however deeply
    nested — replaced by a ` var() ` marker. What is left is what the author
    wrote as a literal. Containing a var() is not the same as being tokenized:
    `var(--pad-sm) 13px` still hardcodes 13px."""
    out: list[str] = []
    low, i = value.lower(), 0
    while True:
        j = low.find("var(", i)
        if j < 0:
            out.append(value[i:])
            return "".join(out)
        if j > 0 and (low[j - 1].isalnum() or low[j - 1] in "-_"):
            out.append(value[i:j + 4])            # part of a longer name
            i = j + 4
            continue
        out.append(value[i:j])
        out.append(VAR_MARK)
        i = _close_paren(value, j + 3) + 1


def raw_colour(value: str) -> tuple[str, str] | None:
    """(rule, text) for the first colour written as a literal, else None.

    var() references and their fallbacks are ignored, and so is a colour
    function that derives from a token — `oklch(from var(--x) l c h / .5)`,
    `rgb(var(--rgb) / .5)` — because the token still decides the colour.
    `url(…)` is ignored too: `url(#fade)` is a reference, not a hex colour."""
    rest = re.sub(r"url\([^)]*\)", " url() ", strip_var_refs(value), flags=re.I)
    m = HEX_COLOR.search(rest)
    if m:
        return "raw-color", m.group(0)
    for fm in FUNC_COLOR.finditer(rest):
        body = rest[fm.end() - 1:_close_paren(rest, fm.end() - 1)]
        if VAR_MARK.strip() not in body:
            return "raw-color", fm.group(0).rstrip("( ")
    m = NAMED_COLOR.search(rest)
    if m:
        return "named-color", m.group(0)
    return None


def has_raw_length(value: str) -> str | None:
    v = strip_var_refs(value)
    m = LENGTH_LITERAL.search(v)
    if not m:
        return None
    if re.fullmatch(r"-?0+(\.0+)?(px|rem|em)?", m.group(0), re.I):
        return None
    return m.group(0)


def owl_selector(selectors: tuple[str, ...]) -> bool:
    """The parent-owned flow idiom: `> * + *` written in the PARENT's rule."""
    return any(re.search(r"\+\s*\*|\*\s*\+", s) for s in selectors)


def generated_content(selectors: tuple[str, ...]) -> bool:
    """`::before` / `::after` are the component's own generated content. Its
    rule decides what the pseudo-element sits beside, so a margin there is
    inner spacing, not a child claiming room outside itself."""
    return bool(selectors) and all(
        re.search(r"::(?:before|after|marker)\s*$", s.strip()) for s in selectors)


def margin_is_alignment(value: str) -> bool:
    """auto aligns, and 0 asserts no space at all: neither is a child claiming
    room around itself. (`margin: 0 auto` is both.)"""
    parts = value.lower().replace("!important", "").split()
    return "auto" in parts or (bool(parts) and all(
        re.fullmatch(r"[+-]?0*\.?0+(?:[a-z]+|%)?", p) for p in parts))


CANCELLED_TOKEN = re.compile(
    r"calc\(\s*(?:var\(\s*--[\w-]+\s*\)\s*\*\s*-1|-1\s*\*\s*var\(\s*--[\w-]+\s*\))\s*\)", re.I)


def margin_cancels_token(value: str) -> bool:
    """`calc(var(--token) * -1)` keeps the relationship; `-24px` does not.
    Matched as that shape: a bare "-1" substring also matched --space-16."""
    return bool(CANCELLED_TOKEN.search(value))


# ---------------------------------------------------------------------------
# CSS rules
# ---------------------------------------------------------------------------

def audit_css(path: Path, text: str) -> list[Finding]:
    findings: list[Finding] = []
    lines = text.splitlines()
    clean, comments = strip_css_comments(text, line_comments(path))

    file_ignores = set()
    for body in comments.values():
        m = IGNORE_FILE.search(body)
        if m:
            file_ignores |= {t.strip().upper() for t in m.group(1).split(",") if t.strip()}
    if any(mark in text[:800] for mark in GENERATED_MARKERS):
        return []

    line_ignores: dict[int, set[str]] = {}
    for ln, body in comments.items():
        m = IGNORE_LINE.search(body)
        if m:
            line_ignores[ln + 1] = {t.strip().upper() for t in m.group(1).split(",") if t.strip()}

    token_file = is_token_file(path)
    component_file = is_component_file(path)
    saw_layer_statement = False
    layer_statement_line = 0
    first_rule_line = 0
    first_unlayered_line = 0
    declared_props: set[str] = set()

    def add(line: int, law: str, rule: str, sev: str, msg: str, fix: str) -> None:
        tags = line_ignores.get(line, set()) | file_ignores
        if law in tags or rule.upper() in tags or "ALL" in tags:
            return
        snippet = lines[line - 1].strip() if 0 < line <= len(lines) else ""
        findings.append(Finding(str(path), line, law, rule, sev, msg, fix, snippet))

    for ev in scan_css(clean):
        if isinstance(ev, tuple):
            kind = ev[0]
            if kind == "at_statement":
                stmt = ev[1]
                if stmt.startswith("@layer") and "," in stmt:
                    saw_layer_statement = True
                    layer_statement_line = ev[2]
                    declared = [s.strip() for s in stmt[6:].strip().rstrip(";").split(",")]
                    canonical = ["reset", "tokens", "base", "layout",
                                 "components", "utilities", "overrides"]
                    present = [d for d in declared if d in canonical]
                    if present != [c for c in canonical if c in present]:
                        add(ev[2], "L5", "layer-order", "error",
                            f"Layer statement is out of order: {', '.join(declared)}.",
                            "Use: @layer reset, tokens, base, layout, components, "
                            "utilities, overrides; extra layers may be inserted, "
                            "but the canonical ones must keep their relative order.")
            elif kind == "rule_open":
                sel, line, depth, at_rules = ev[1], ev[2], ev[3], ev[4]
                if not first_rule_line:
                    first_rule_line = line
                # depth counts the top-level rule as 1; nesting starts below it,
                # as stylelint counts (design-rules.json: max_depth 2).
                if depth - 1 > MAX_NESTING:
                    add(line, "L5", "nesting-depth", "error",
                        f"Nesting depth {depth - 1} exceeds the limit of {MAX_NESTING}.",
                        "Native nesting desugars through :is(), which takes the "
                        "specificity of its most specific argument — past depth 2 "
                        "nobody can predict the resulting number. Flatten it.")
                if COMPOUND_SEL.search(sel):
                    add(line, "L5", "compound-specificity", "warning",
                        f"Selector chains 4+ classes: `{sel[:70]}`.",
                        "A selector this long is usually trying to WIN rather "
                        "than to describe an element. Layers already decide who "
                        "wins — say what the element is and move the rule to the "
                        "right layer. If it is reaching into another component, "
                        "use that component's Tier-3 properties instead.")
                m = ID_SELECTOR.search(sel)
                if m and not sel.strip().startswith("@"):
                    add(line, "L5", "id-selector", "error",
                        f"ID selector `{m.group(0)}` in a style rule.",
                        "IDs buy specificity you then have to match forever. "
                        "Use a class; layers already decide who wins.")
                # The at-rules open around this rule, not every one seen so
                # far: a rule after a closed @layer block is unlayered (SB-A9).
                # A keyframe (`from`, `to`, `50%`) is not a style rule; the
                # references and the scaffold keep @keyframes outside layers.
                # A Sass @mixin or @function emits nothing where it is written
                # (SB-A24); the layer is checked where it is included.
                if not token_file and depth == 1 and not first_unlayered_line and not any(
                    a.startswith("@layer") or KEYFRAMES_AT.match(a) or SASS_DEFINITION_AT.match(a)
                    for a in at_rules
                ):
                    first_unlayered_line = line
            elif kind == "rule_close":
                pass
            continue

        d: CssDecl = ev
        prop, value, line = d.prop, d.value, d.line

        if prop.startswith("--"):
            declared_props.add(prop)
            # A Tier-3 socket is where a component binds a role to a part.
            # `--card-inset: var(--pad-card)` is the whole point;
            # `--card-inset: 28px` is the same literal the rest of Law 1
            # forbids, just wearing a custom property as a disguise — and
            # it is the easiest place for one to hide, because it LOOKS
            # like tokenized code. Unitless numbers, ratios and fallbacks
            # are fine; a length, a colour or a duration is not — including
            # one written beside a var(), as in `calc(var(--pad) + 28px)`.
            if not token_file:
                rest = strip_var_refs(value)
                colour = raw_colour(value)
                if OPTICAL_PROP.search(prop):
                    pass                       # declared optical correction
                elif has_raw_length(value) and not RELATIONAL_UNIT.match(value.strip()):
                    add(line, "L1", "socket-literal", "error",
                        f"Socket `{prop}` is declared as the literal `{value.strip()}`.",
                        "A custom property is not a token. Bind the socket to "
                        "a Tier-2 role — that is what makes the component "
                        "theme-able, density-aware and auditable. If no role "
                        "fits, the missing role is the actual finding.")
                elif colour and colour[0] == "raw-color":
                    add(line, "L1", "socket-literal", "error",
                        f"Socket `{prop}` hardcodes the colour `{value.strip()}`.",
                        "Dark mode re-points roles, not sockets. A literal "
                        "here is a colour the theme can never reach.")
                elif TIME_LITERAL.search(rest) or BEZIER_LITERAL.search(rest):
                    add(line, "L1", "socket-literal", "error",
                        f"Socket `{prop}` hardcodes motion: `{value.strip()}`.",
                        "Bind it to a --motion-* pair so duration and easing "
                        "stay together and prefers-reduced-motion still "
                        "applies.")

        # ---- L1 Sass variables ----------------------------------------------
        # `$card-padding: 24px` is the literal Law 1 forbids, moved one line
        # up (SB-A24; design-rules.json: sass.variables).
        if (SASS_VARIABLE.match(prop) and not token_file and not SASS_BREAKPOINT.search(prop)
                and not any(SASS_FUNCTION_AT.match(a) for a in d.at_rules)):
            rest = strip_var_refs(value)
            colour = raw_colour(value)
            if (has_raw_length(value) or (colour and colour[0] == "raw-color")
                    or TIME_LITERAL.search(rest) or BEZIER_LITERAL.search(rest)):
                add(line, "L1", "sass-literal", "error",
                    f"Sass variable `{prop}` holds a literal: `{value.strip()}`.",
                    "A Sass variable is fixed at compile time: no theme re-points "
                    "it, --density cannot reach it and DevTools does not show it. "
                    "Declare the value as a token and read it with var(). Only a "
                    "breakpoint ($bp-*) has to be a Sass value, because a media "
                    "query condition cannot read a custom property.")

        # ---- L5 !important -------------------------------------------------
        if "!important" in value.lower():
            add(line, "L5", "important", "error",
                f"`!important` on `{prop}`.",
                "!important inverts layer order (an !important in an EARLIER "
                "layer beats one in a later layer), so it makes the next "
                "override strictly harder. Move the rule to the right layer.")

        # ---- The token file is where literals live -------------------------
        if token_file:
            continue

        # ---- L1 / L3 spacing -----------------------------------------------
        # Inside @media / @container / @supports too: the prelude is never a
        # declaration, and responsive rules are where literals collect.
        if prop in SPACING_PROPS:
            raw = has_raw_length(value)
            # em is a RATIO to the current font size, so an em offset tracks
            # type instead of bypassing the scale. Legitimate for positioning
            # (sup/sub, optical nudges), never for layout gaps.
            if raw and raw.lower().endswith("em") and prop not in (
                    OUTER_MARGIN_PROPS | {"gap", "row-gap", "column-gap",
                                          "grid-gap"}) and not prop.startswith("padding"):
                raw = None
            if raw:
                on_scale_note = ""
                if raw.lower().endswith("px"):
                    try:
                        px = float(raw[:-2])
                        if px % 4 != 0:
                            on_scale_note = f" {raw} is not even on the 4px grid."
                    except ValueError:
                        pass
                add(line, "L1", "raw-spacing", "error",
                    f"`{prop}: {value}` uses the literal `{raw}`.{on_scale_note}",
                    "Pick the relationship, not the pixels: --gap-fused / "
                    "--gap-tight / --gap-related / --gap-grouped / --gap-separate "
                    "/ --gap-distinct for space between siblings, --pad-* for "
                    "inset. See references/spacing-system.md §6.")

        # ---- L2 outer margins in components --------------------------------
        if (component_file and prop in OUTER_MARGIN_PROPS
                and not margin_is_alignment(value)
                and not margin_cancels_token(value)
                and not owl_selector(d.selectors)
                and not generated_content(d.selectors)
                and "prose" not in " ".join(d.selectors).lower()):
            add(line, "L2", "child-margin", "error",
                f"`{prop}` on a component. A child may not set its own outer margin.",
                "The parent owns the space between siblings — set `gap` on the "
                "parent instead. A component cannot know what it sits next to, "
                "so a margin here is a fact asserted from inside. "
                "(Legal: margin:auto for alignment, calc(var(--t) * -1) to "
                "cancel a known token, an owl selector in the parent's rule.)")

        # ---- L1 colour ------------------------------------------------------
        # Every check below looks at what is left once var() references are
        # taken out, so a token beside a literal no longer hides the literal.
        if prop in COLOR_PROPS or prop in COLOR_SHORTHANDS:
            colour = raw_colour(value)
            if colour and colour[0] == "raw-color":
                add(line, "L1", "raw-color", "error",
                    f"`{prop}: {value.strip()}` hardcodes a colour.",
                    "Use a role: --bg-surface / --fg-muted / --border-default "
                    "/ --bg-accent. A hardcoded colour is a colour that dark "
                    "mode cannot re-point, which is how a theme silently breaks.")
            elif colour:
                add(line, "L1", "named-color", "warning",
                    f"`{prop}: {value.strip()}` uses a CSS named colour.",
                    "Named colours are outside the ramp and outside the "
                    "contrast budget. Use a role token.")

        # ---- L1 shadows ------------------------------------------------------
        if (prop in SHADOW_PROPS
                and value.strip().lower() not in ("none", "inherit", "initial",
                                                  "unset", "revert", "revert-layer")
                and (has_raw_length(value) or raw_colour(value))):
            add(line, "L1", "raw-shadow", "error",
                f"`{prop}` is a literal shadow.",
                "Use an elevation role: --elevation-card / --elevation-raised / "
                "--elevation-overlay / --elevation-modal. Hand-rolled shadows "
                "drift out of the light model within about three commits.")

        # ---- L1 typography ---------------------------------------------------
        if prop in TYPE_PROPS:
            if prop == "line-height" and re.fullmatch(r"[\d.]+", value.strip()):
                add(line, "L3", "raw-leading", "warning",
                    f"`line-height: {value.strip()}` is a literal ratio.",
                    "Use --leading-* in base.css, or better, a --type-* role "
                    "which carries leading in its font shorthand.")
            elif prop == "font-weight" and re.fullmatch(r"\d{1,4}", value.strip()):
                # No unit, so the length check below never saw it.
                add(line, "L1", "raw-weight", "error",
                    f"`font-weight: {value.strip()}` hardcodes a weight.",
                    "Use --weight-regular / -medium / -semibold / -bold (weight "
                    "has no Tier-2 role), or a --type-* role, which carries the "
                    "weight in its font shorthand.")
            elif (has_raw_length(value)
                  and not RELATIONAL_UNIT.match(value.strip())
                  and not (has_raw_length(value) or "").lower().endswith("em")):
                add(line, "L1", "raw-type", "error",
                    f"`{prop}: {value.strip()}` is off the type scale.",
                    "Use a --type-* role (--type-body, --type-h2, --type-ui). "
                    "Orphan sizes are how hierarchy stops reading as hierarchy.")

        # ---- L1 radius -------------------------------------------------------
        if prop in RADIUS_PROPS and has_raw_length(value):
            add(line, "L1", "raw-radius", "error",
                f"`{prop}: {value.strip()}` is a literal radius.",
                "Use --radius-*. Concentric corners depend on the radius and the "
                "inset being related — see references/spacing-system.md §8.")

        # ---- L1 motion -------------------------------------------------------
        if prop in MOTION_PROPS:
            rest = strip_var_refs(value)
            if TIME_LITERAL.search(rest):
                add(line, "L1", "raw-duration", "error",
                    f"`{prop}: {value.strip()}` hardcodes a duration.",
                    "Use --motion-hover / --motion-enter / --motion-exit / "
                    "--motion-expand. A literal duration also ignores "
                    "prefers-reduced-motion, which the tokens handle for you.")
            elif BEZIER_LITERAL.search(rest):
                add(line, "L1", "raw-easing", "error",
                    f"`{prop}` hardcodes an easing curve.",
                    "Use --ease-out (arriving), --ease-in (leaving), "
                    "--ease-in-out (moving within view), or a --motion-* pair.")
        if prop == "transition" and re.match(r"^\s*all\b", value, re.I):
            add(line, "L1", "transition-all", "warning",
                "`transition: all` animates properties you did not choose.",
                "Name the properties. `all` costs layout work on every change "
                "and produces animations nobody designed.")

        # ---- L1 z-index ------------------------------------------------------
        if prop == "z-index" and "var(--" not in value and value.strip() not in ("0", "auto"):
            add(line, "L1", "raw-z-index", "error",
                f"`z-index: {value.strip()}` is a literal.",
                "Use the ladder: --z-raised / --z-sticky / --z-dropdown / "
                "--z-overlay / --z-modal / --z-toast / --z-tooltip. Literal "
                "z-indexes are how you end up with 9999.")

        # ---- L6 Tier-1 leakage ------------------------------------------------
        if component_file or in_layer(d.at_rules, "components"):
            for ref in VAR_REF.findall(value):
                if ref in TIER2_EXCEPTIONS:
                    continue
                bare = ref[2:]
                for pfx, advice in TIER1_WITH_ROLE.items():
                    if bare.startswith(pfx):
                        # Declaring a Tier-3 socket FROM a Tier-2 role is the
                        # sanctioned pattern; reading a Tier-1 primitive is not.
                        add(line, "L6", "tier1-leak", "error",
                            f"Component code reads the Tier-1 primitive `{ref}`.",
                            f"Right value, wrong tier — use {advice}. The day "
                            f"'more air in cards' lands, you want to change one "
                            f"role, not grep for {ref} across the repo.")
                        break
                else:
                    # Only a shorthand can take a --motion-* pair. A longhand
                    # (animation-duration, transition-timing-function) must read
                    # the primitive — view-transition pseudo-elements and
                    # scroll-driven animations need exactly that.
                    if any(bare.startswith(p) for p in TIER1_MOTION) and prop in MOTION_SHORTHANDS:
                        add(line, "L6", "tier1-motion", "warning",
                            f"Component code reads `{ref}` directly.",
                            "Prefer a --motion-* pair so duration and easing "
                            "travel together; they drift apart when split.")

        # ---- Optical corrections must be declared as such ---------------------
        if (prop in {"translate", "transform"} and has_raw_length(value)
                and not OPTICAL_PROP.search(value)):
            add(line, "L1", "raw-transform-offset", "warning",
                f"`{prop}: {value.strip()}` nudges by a literal.",
                "If it is an optical correction, declare it as "
                "`--<thing>-optical-nudge` with a comment stating the "
                "perceptual reason, and keep it under 2px. If it is bigger "
                "than 2px it is a layout bug being papered over.")

    # ---- File-level checks --------------------------------------------------
    if not token_file and first_unlayered_line:
        add(first_unlayered_line, "L5", "unlayered", "error",
            "This stylesheet has rules outside any @layer.",
            "Unlayered CSS beats every layer regardless of specificity, so one "
            "unwrapped file quietly makes its rules unoverridable. Wrap the "
            "file in @layer components { … } (or the layer it belongs to).")

    if saw_layer_statement and first_rule_line and layer_statement_line > first_rule_line:
        add(layer_statement_line, "L5", "layer-statement-position", "error",
            "The @layer statement appears after rules have already been seen.",
            "A layer's position is fixed the first time its name is used, so "
            "the statement must be the first thing in the entry stylesheet, "
            "before every @import and every rule.")

    return findings


# ---------------------------------------------------------------------------
# JS / JSX rules
# ---------------------------------------------------------------------------

def strip_js_comments(text: str) -> str:
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


def match_braces(text: str, start: int) -> int:
    """Index just past the `}}` that closes a `{{` opened at `start`."""
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


def audit_js(path: Path, text: str) -> list[Finding]:
    # Lint and build configs quote example code as data. Auditing them
    # audits the examples, which is noise, not signal.
    if CONFIG_FILE_PAT.search(str(path).replace(os.sep, '/')):
        return []
    findings: list[Finding] = []
    lines = text.splitlines()
    clean = strip_js_comments(text)

    file_ignores: set[str] = set()
    line_ignores: dict[int, set[str]] = {}
    for idx, raw in enumerate(lines, start=1):
        m = IGNORE_FILE.search(raw)
        if m:
            file_ignores |= {t.strip().upper() for t in m.group(1).split(",") if t.strip()}
        m = IGNORE_LINE.search(raw)
        if m:
            line_ignores[idx + 1] = {t.strip().upper() for t in m.group(1).split(",") if t.strip()}
    if any(mark in text[:800] for mark in GENERATED_MARKERS):
        return []

    line_of = _line_finder(clean)

    def add(line: int, law: str, rule: str, sev: str, msg: str, fix: str) -> None:
        tags = line_ignores.get(line, set()) | file_ignores
        if law in tags or rule.upper() in tags or "ALL" in tags:
            return
        snippet = lines[line - 1].strip() if 0 < line <= len(lines) else ""
        findings.append(Finding(str(path), line, law, rule, sev, msg, fix, snippet))

    _audit_jsx_styles(clean, line_of, add)
    _audit_class_lists(clean, line_of, add)
    for f in _audit_css_in_js(path, clean, line_of):
        tags = line_ignores.get(f.line, set()) | file_ignores
        if not (f.law in tags or f.rule.upper() in tags or "ALL" in tags):
            findings.append(f)

    # ---- Hardcoded colours in JS strings -----------------------------------
    for m in re.finditer(r"""["'`](#[0-9a-fA-F]{3,8})["'`]""", clean):
        ln = line_of(m.start())
        ctx = lines[ln - 1] if 0 < ln <= len(lines) else ""
        if re.search(r"\b(test|spec|stories|mock|fixture)\b", str(path), re.I):
            continue
        if "#" in ctx and re.search(r"(href|id|anchor|hash|sha|commit)", ctx, re.I):
            continue
        add(ln, "L1", "js-raw-color", "warning",
            f"Hardcoded colour `{m.group(1)}` in JS.",
            "Read the token instead — getComputedStyle().getPropertyValue('--bg-accent') "
            "for canvas/chart code, or set it from CSS via a custom property. A "
            "colour in JS is a colour dark mode cannot re-point.")

    return findings


def _line_finder(text: str):
    """pos -> 1-based line number, by bisecting a newline index (one pass over
    the text, instead of counting newlines again for every finding)."""
    starts = [0] + [m.end() for m in re.finditer("\n", text)]
    return lambda pos: bisect.bisect_right(starts, pos)


def _audit_jsx_styles(clean: str, line_of, add) -> None:
    # ---- L4 inline style ---------------------------------------------------
    for m in JSX_STYLE.finditer(clean):
        open_at = clean.index("{", m.start())
        end = match_braces(clean, open_at)
        body = clean[open_at:end]
        inner = body[2:-2] if body.endswith("}}") else body
        keys = re.findall(r"(?:^|[{,\s])\s*(?:['\"]([^'\"]+)['\"]|([A-Za-z_$][\w$]*))\s*:", inner)
        names = [a or b for a, b in keys]
        offenders = [k for k in names if not k.startswith("--")]
        if not names:
            continue
        if offenders:
            add(line_of(m.start()), "L4", "inline-style", "error",
                f"Inline `style` sets visual propert{'y' if len(offenders) == 1 else 'ies'}: "
                f"{', '.join(offenders[:4])}.",
                "Inline style is the highest-specificity declaration short of "
                "!important, and it is invisible to every stylesheet, linter and "
                "theme. The one legal use is passing a runtime NUMBER in as a "
                "custom property: style={{'--card-span': n}}, with the rule that "
                "consumes it living in the component's stylesheet.")


def _call_end(text: str, open_at: int) -> int:
    """Index of the `)` closing the call opened at `open_at`, skipping strings."""
    depth, k, n = 0, open_at, len(text)
    while k < n:
        c = text[k]
        if c in "\"'`":
            q, k = c, k + 1
            while k < n and text[k] != q:
                k += 2 if text[k] == "\\" else 1
        elif c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return k
        k += 1
    return n


def _class_strings(clean: str) -> Iterator[tuple[str, int]]:
    """(class string, position): `className="…"` values, and every string
    literal inside a class-helper call, once each."""
    seen: set[int] = set()
    for sm in CLASS_ATTR.finditer(clean):
        seen.add(sm.start(1))
        yield sm.group(1), sm.start(1)
    for hm in CLASS_HELPER.finditer(clean):
        open_at = hm.end() - 1
        for lm in JS_STRING.finditer(clean, open_at, _call_end(clean, open_at)):
            if lm.start(2) not in seen:
                seen.add(lm.start(2))
                yield lm.group(2), lm.start(2)


def _audit_css_in_js(path: Path, clean: str, line_of) -> list[Finding]:
    """A styled-components or emotion template body is CSS: audit it as the
    component's CSS, at the lines it sits on. An interpolation is a runtime
    value, so it stands in as a var()."""
    found: list[Finding] = []
    for m in CSS_IN_JS.finditer(clean):
        start = m.end()                      # just past the opening backtick
        k, n, body = start, len(clean), []
        while k < n and clean[k] != "`":
            if clean.startswith("${", k):
                end = match_braces(clean, k + 1)
                body.append("var(--interpolated)" + "\n" * clean.count("\n", k, end))
                k = end
                continue
            body.append(clean[k])
            k += 2 if clean[k] == "\\" else 1
        css = ("\n" * (line_of(start) - 1) + "@layer components { .css-in-js {"
               + "".join(body) + "} }")
        found.extend(audit_css(path, css))
    return found


def _audit_class_lists(clean: str, line_of, add) -> None:
    # ---- Tailwind arbitrary values / bang / space-x ------------------------
    for cls, at in _class_strings(clean):
        for m in TW_ARBITRARY.finditer(cls):
            tok = m.group(0)
            if TW_ARBITRARY_OK.match(tok):
                continue
            add(line_of(at), "L3", "tw-arbitrary", "error",
                f"Tailwind arbitrary value `{tok}`.",
                "The theme IS the token file, so an on-scale class already "
                "exists for whatever this is. An arbitrary value re-opens the "
                "unbounded value space the closed scale exists to shut.")
        for m in TW_ARBITRARY_PROPERTY.finditer(cls):
            add(line_of(at), "L1", "tw-arbitrary-property", "error",
                f"`{m.group(0)}` puts a whole declaration in a class list.",
                "No theme, stylesheet or audit that reads CSS can see it. If "
                "Tailwind has no utility for the property, add an @utility in "
                "theme.css or give it a rule in the component's own stylesheet.")
        for m in TW_IMPORTANT_SUFFIX.finditer(cls):
            add(line_of(at), "L5", "tw-important", "error",
                f"`{m.group(0)}` forces !important (the v4 suffix).",
                "!important inverts layer order and makes the next override "
                "harder. Fix the layer or the variant instead.")
        for m in TW_SPACE_XY.finditer(cls):
            add(line_of(at), "L2", "tw-space-xy", "error",
                f"`{m.group(0)}` spaces children with margins.",
                "space-x/space-y compile to child margins with a :not(:last-child) "
                "selector — the same double-ownership problem, behind a nicer "
                "name. Use gap-* on the parent.")
        for m in TW_IMPORTANT.finditer(cls):
            add(line_of(at), "L5", "tw-important", "error",
                f"`{m.group(0)}` forces !important.",
                "!important inverts layer order and makes the next override "
                "harder. Fix the layer or the variant instead.")
        for m in TW_LITERAL.finditer(cls):
            add(line_of(at), "L1", "tw-literal", "error",
                f"`{m.group(0)}` is a literal value.",
                "Tailwind generates a bare number for duration-, delay-, z-, "
                "border-, ring- and offset- utilities whatever the theme says, "
                "so the closed scale does not remove it. Use the role: "
                "motion-hover, z-modal, border-stroke, focus-ring. A literal "
                "duration also skips the reduced-motion tokens.")
        for m in TW_OPACITY.finditer(cls):
            add(line_of(at), "L1", "tw-opacity-modifier", "error",
                f"`{m.group(0)}` sets a literal alpha.",
                "A /NN modifier compiles to color-mix() with a number nobody "
                "chose. Translucency has roles (bg-hover, bg-active, the scrim "
                "role) that dark mode and the contrast checks can reach.")
        for m in TW_TIER1_VAR.finditer(cls):
            add(line_of(at), "L6", "tier1-leak", "error",
                f"`{m.group(0)}` reads a Tier-1 primitive.",
                "Use the role: p-card rather than p-(--space-6), bg-surface "
                "rather than bg-(--neutral-800).")


# ---------------------------------------------------------------------------
# Templates: HTML pages and single-file components
# ---------------------------------------------------------------------------

def _blank(text: str, spans: Iterable[tuple[int, int]], keep: bool) -> str:
    """Positions and newlines preserved. keep=True blanks everything EXCEPT the
    spans; keep=False blanks the spans themselves."""
    spans = list(spans)
    if keep:
        out = [c if c == "\n" else " " for c in text]
        for s, e in spans:
            out[s:e] = text[s:e]
    else:
        out = list(text)
        for s, e in spans:
            for k in range(s, e):
                if out[k] != "\n":
                    out[k] = " "
    return "".join(out)


def audit_template(path: Path, text: str) -> list[Finding]:
    """.html / .htm / .vue / .svelte / .astro.

    <style> blocks are audited as CSS in place: everything else is blanked
    with line breaks kept, so every finding points at the real line. A
    style="" attribute that sets a visual property is the same Law 4 failure
    as a JSX inline style, and class lists get the Tailwind checks. HTML email
    never reaches here (see is_html_email)."""
    if any(mark in text[:800] for mark in GENERATED_MARKERS):
        return []

    lines = text.splitlines()
    file_ignores: set[str] = set()
    line_ignores: dict[int, set[str]] = {}
    for idx, raw in enumerate(lines, start=1):
        m = IGNORE_FILE.search(raw)
        if m:
            file_ignores |= {t.strip().upper() for t in m.group(1).split(",") if t.strip()}
        m = IGNORE_LINE.search(raw)
        if m:
            line_ignores[idx + 1] = {t.strip().upper() for t in m.group(1).split(",") if t.strip()}

    style_spans = [m.span(1) for m in STYLE_BLOCK.finditer(text)]
    findings = audit_css(path, _blank(text, style_spans, keep=True)) if style_spans else []

    markup = _blank(text, style_spans + [m.span(1) for m in SCRIPT_BLOCK.finditer(text)],
                    keep=False)
    line_of = _line_finder(text)

    def add(line: int, law: str, rule: str, sev: str, msg: str, fix: str) -> None:
        tags = line_ignores.get(line, set()) | file_ignores
        if law in tags or rule.upper() in tags or "ALL" in tags:
            return
        snippet = lines[line - 1].strip() if 0 < line <= len(lines) else ""
        findings.append(Finding(str(path), line, law, rule, sev, msg, fix, snippet))

    for m in TAG_STYLE_ATTR.finditer(markup):
        props = [d.split(":", 1)[0].strip().lower()
                 for d in m.group(2).split(";") if ":" in d]
        offenders = [p for p in props if p and not p.startswith("--")]
        if offenders:
            add(line_of(m.start(2)), "L4", "inline-style", "error",
                f"style=\"\" sets visual propert{'y' if len(offenders) == 1 else 'ies'}: "
                f"{', '.join(offenders[:4])}.",
                "An inline style beats every stylesheet and layer and is invisible "
                "to the theme. Give the element a class and style it in the "
                "stylesheet; the one legal inline use is a custom property carrying "
                "a runtime value (style=\"--progress: 40%\").")

    _audit_jsx_styles(markup, line_of, add)       # Astro accepts style={{…}}
    _audit_class_lists(markup, line_of, add)

    if file_ignores:
        findings = [f for f in findings
                    if not ({f.law, f.rule.upper(), "ALL"} & file_ignores)]
    return findings


# ---------------------------------------------------------------------------
# Cross-file analysis — the violations no single file reveals
# ---------------------------------------------------------------------------

CLASS_IN_SEL = re.compile(r"\.(-?[_a-zA-Z][\w-]*)")


def audit_cross_file(files: list[tuple[Path, str]]) -> list[Finding]:
    """Law 4 and Law 2 failures that are invisible file-by-file.

    A component styled from two files has two homes, and no reviewer can
    predict its appearance from either one. Worse, when both files set the
    SAME property, which one wins is decided by specificity and load order —
    so editing the obvious one silently does nothing. That is the single most
    confusing bug shape in a stylesheet, and it can only be seen from above.

    CSS Modules scope class names per file, so `.card` in two .module.css
    files is two different classes and is not a finding. Only globally-scoped
    sheets can genuinely collide.
    """
    findings: list[Finding] = []
    # class -> prop -> [(file, line)]
    owners: dict[str, dict[str, list[tuple[str, int]]]] = {}
    seen_lines: dict[str, list[str]] = {}

    for path, text in files:
        if is_token_file(path):
            continue
        s = str(path).replace(os.sep, "/")
        if ".module." in s.lower():
            continue                      # build-time scoped: cannot collide
        if any(mark in text[:800] for mark in GENERATED_MARKERS):
            continue
        clean, _ = strip_css_comments(text, line_comments(path))
        seen_lines[str(path)] = text.splitlines()
        for ev in scan_css(clean):
            if isinstance(ev, tuple):
                continue
            d: CssDecl = ev
            if d.prop.startswith("--") or not d.selectors:
                continue
            # The LAST selector level is the element this rule is about.
            classes = set(CLASS_IN_SEL.findall(d.selectors[-1]))
            for cls in classes:
                owners.setdefault(cls, {}).setdefault(d.prop, []).append(
                    (str(path), d.line))

    for cls, props in sorted(owners.items()):
        files_touching = {f for sites in props.values() for f, _ in sites}
        if len(files_touching) < 2:
            continue

        # The sharp case: the same property for the same class, twice, in
        # two files. Specificity and load order decide; nobody can tell which.
        for prop, sites in sorted(props.items()):
            distinct = sorted({f for f, _ in sites})
            if len(distinct) < 2:
                continue
            f0, l0 = sites[0]
            law = "L2" if prop in OUTER_MARGIN_PROPS else "L4"
            others = ", ".join(Path(f).name for f in distinct[1:])
            findings.append(Finding(
                f0, l0, law, "double-owner", "error",
                f"`.{cls}` has `{prop}` set in {len(distinct)} files "
                f"({Path(f0).name}, {others}).",
                "Two rules own one value, so which wins is decided by "
                "specificity and load order — edit the obvious one and "
                "nothing changes. Pick the component's one home and delete "
                "the other. If a consumer genuinely needs to adjust this, "
                "expose it as a Tier-3 custom property instead.",
                (seen_lines.get(f0) or [""])[l0 - 1].strip()
                if l0 <= len(seen_lines.get(f0) or []) else ""))

        # The softer case: styled from several files without overlapping
        # properties. Still two homes — just not yet actively fighting.
        n = len(files_touching)
        f0, l0 = next(iter(props.values()))[0]
        where = ", ".join(sorted(Path(f).name for f in files_touching))
        findings.append(Finding(
            f0, l0, "L4", "scattered-component",
            "error" if n >= 3 else "warning",
            f"`.{cls}` is styled from {n} different files ({where}).",
            "One home per component. A reviewer who has never seen this must "
            "be able to predict its appearance from one file; right now they "
            f"would have to find and read {n}. If a consumer needs to adjust "
            "the component, give it a Tier-3 custom property and set that "
            "from outside — a documented API instead of a second home.",
            (seen_lines.get(f0) or [""])[l0 - 1].strip()
            if l0 <= len(seen_lines.get(f0) or []) else ""))

    return findings


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def file_kind(path: Path) -> str | None:
    ext = path.suffix.lower()
    if ext in CSS_EXT:
        return "css"
    if ext in JS_EXT:
        return "js"
    if ext in TEMPLATE_EXT:
        return "template"
    return None


def iter_files(paths: list[str]) -> Iterator[Path]:
    for raw in paths:
        p = Path(raw)
        if p.is_file():
            yield p                               # named explicitly: always reported
        elif p.is_dir():
            for root, dirs, files in os.walk(p):
                dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
                for f in sorted(files):
                    fp = Path(root) / f
                    if file_kind(fp):
                        yield fp


def is_html_email(text: str) -> bool:
    """HTML email cannot use custom properties or layers, so these laws do not
    fit it; email-template-system's lint_email is its gate."""
    low = text.lower()
    return any(mark in low for mark in EMAIL_MARKERS)


SKIP_NOT_AUDITABLE = "not CSS, JS or HTML"
SKIP_EMAIL = "HTML email: lint it with email-template-system's lint_email"
SKIP_INDENTED_SASS = "indented Sass, which this audit cannot read: audit the compiled CSS, or use .scss"


def audit(paths: list[str]) -> list[Finding]:
    return audit_run(paths)[0]


def audit_run(paths: list[str]) -> tuple[list[Finding], int, list[tuple[Path, str]]]:
    """(findings, number of files audited, [(file, why it was skipped)])."""
    out: list[Finding] = []
    audited = 0
    skipped: list[tuple[Path, str]] = []
    css_sources: list[tuple[Path, str]] = []
    for fp in iter_files(paths):
        kind = file_kind(fp)
        if kind is None:
            skipped.append((fp, SKIP_NOT_AUDITABLE))
            continue
        if fp.suffix.lower() == ".sass":
            skipped.append((fp, SKIP_INDENTED_SASS))
            continue
        try:
            # utf-8-sig: PowerShell 5.1's Set-Content -Encoding utf8 writes a
            # BOM, and a BOM before `@layer` read as a rule outside any layer.
            text = fp.read_text(encoding="utf-8-sig", errors="replace")
        except OSError:
            continue
        if kind == "template" and is_html_email(text):
            skipped.append((fp, SKIP_EMAIL))
            continue
        audited += 1
        if kind == "css":
            css_sources.append((fp, text))
        try:
            if kind == "css":
                out.extend(audit_css(fp, text))
            elif kind == "template":
                out.extend(audit_template(fp, text))
            else:
                out.extend(audit_js(fp, text))
        except Exception as exc:  # a crashed rule must never block a commit
            out.append(Finding(str(fp), 1, "--", "internal-error", "warning",
                               f"audit_design could not fully parse this file: {exc}",
                               "Please report this file shape; the rest of the "
                               "audit completed normally."))
    try:
        out.extend(audit_cross_file(css_sources))
    except Exception as exc:
        out.append(Finding("<cross-file>", 1, "--", "internal-error", "warning",
                           f"cross-file analysis failed: {exc}",
                           "Per-file findings above are unaffected."))
    out.sort(key=lambda f: (f.file, f.line, SEVERITY_ORDER.get(f.severity, 9)))
    return out, audited, skipped


LAW_NAMES = {
    "L1": "Tokens or nothing",
    "L2": "Parents own the gaps",
    "L3": "The scale is closed",
    "L4": "One home per component's styles",
    "L5": "Layers, not specificity",
    "L6": "Semantic before primitive",
}


def report(findings: list[Finding], *, use_color: bool, show_fix: bool,
           audited: int | None = None) -> str:
    if not findings:
        # L1–L6, not "all nine laws": 7–9 (density, keyboard, audit) are not
        # something a static scan of source can check.
        where = f" across {audited} file(s)" if audited is not None else ""
        return f"design audit: clean — L1–L6 hold{where}.\n"

    def c(code: str, s: str) -> str:
        return f"\033[{code}m{s}\033[0m" if use_color else s

    buf: list[str] = []
    by_file: dict[str, list[Finding]] = {}
    for f in findings:
        by_file.setdefault(f.file, []).append(f)

    for file, items in by_file.items():
        buf.append(c("1", file))
        for f in items:
            tag = c("31", "error") if f.severity == "error" else c("33", "warn ")
            buf.append(f"  {f.line:>5}  {tag}  {c('36', f.law)} {f.rule:<22} {f.message}")
            if show_fix:
                for ln in _wrap(f.fix, 92):
                    buf.append(f"         {c('2', ln)}")
        buf.append("")

    errors = sum(1 for f in findings if f.severity == "error")
    warns = len(findings) - errors
    buf.append(c("1", "Summary"))
    counts: dict[str, int] = {}
    for f in findings:
        counts[f.law] = counts.get(f.law, 0) + 1
    for law in sorted(counts):
        name = LAW_NAMES.get(law, "")
        buf.append(f"  {law}  {name:<34} {counts[law]}")
    buf.append(f"\n  {errors} error(s), {warns} warning(s) "
               f"across {len(by_file)} file(s).")
    return "\n".join(buf) + "\n"


def _wrap(s: str, width: int) -> list[str]:
    words, out, cur = s.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > width:
            out.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        out.append(cur)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="python -m scripts.audit_design",
        description="Enforce the web-design-studio laws. Law 9: nothing ships un-audited.",
    )
    ap.add_argument("paths", nargs="*", default=["."],
                    help="files or directories to audit (default: .)")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--strict", action="store_true", help="warnings fail the run too")
    ap.add_argument("--quiet", action="store_true", help="suppress the fix guidance")
    ap.add_argument("--no-color", action="store_true")
    ap.add_argument("--baseline", metavar="FILE", default=None,
                    help="ignore findings recorded in this file "
                         "(default: .design-baseline.json, if it exists)")
    ap.add_argument("--write-baseline", metavar="FILE",
                    help="record current findings so only NEW ones fail")
    ap.add_argument("--law", action="append", metavar="Lx",
                    help="only report these laws (repeatable)")
    args = ap.parse_args(argv)

    paths = args.paths or ["."]
    missing = [p for p in paths if not Path(p).exists()]
    if missing:
        print(f"audit_design: no such path: {', '.join(missing)}", file=sys.stderr)
        return 2

    findings, audited, skipped = audit_run(paths)

    for why in (SKIP_NOT_AUDITABLE, SKIP_EMAIL, SKIP_INDENTED_SASS):
        group = [p for p, reason in skipped if reason == why]
        if group:
            names = ", ".join(str(p) for p in group[:5]) + (" …" if len(group) > 5 else "")
            print(f"audit_design: skipped {len(group)} file(s) ({why}): {names}",
                  file=sys.stderr)
    if audited == 0:
        folders = [p for p in paths if Path(p).is_dir()]
        if folders:
            print(f"audit_design: 0 files audited in {', '.join(folders)}, so a pass "
                  f"would prove nothing. Point it at the folder that holds the styles.",
                  file=sys.stderr)
            return 2
        if args.json:
            print("[]")
        else:
            print("design audit: nothing to audit (no CSS, JS or HTML among the files given).")
        return 0

    if args.law:
        wanted = {l.upper() for l in args.law}
        findings = [f for f in findings if f.law in wanted]

    # Keys are relative to the baseline file's folder, so the path spelling
    # and the working directory stop mattering.
    bp = Path(args.write_baseline or args.baseline or ".design-baseline.json")
    root = bp.resolve().parent

    if args.write_baseline:
        bp.write_text(
            json.dumps(sorted({f.key(root) for f in findings}), indent=2) + "\n",
            encoding="utf-8")
        print(f"audit_design: recorded {len(findings)} finding(s) as the baseline in "
              f"{args.write_baseline}.\nOnly NEW violations will fail from now on. "
              f"Pay the debt down per directory, not all at once.")
        return 0

    baseline: set[str] = set()
    if bp.exists():
        try:
            baseline = {portable_key(k) for k in json.loads(bp.read_bytes())}
        except (OSError, json.JSONDecodeError):
            print(f"audit_design: could not read baseline {bp}; auditing everything.",
                  file=sys.stderr)
    elif args.baseline:
        print(f"audit_design: baseline {args.baseline} not found; auditing everything.",
              file=sys.stderr)
    if baseline:
        findings = [f for f in findings if f.key(root) not in baseline]

    if args.json:
        print(json.dumps([asdict(f) for f in findings], indent=2))
    else:
        use_color = not args.no_color and sys.stdout.isatty()
        sys.stdout.write(report(findings, use_color=use_color, show_fix=not args.quiet,
                                audited=audited))

    failing = [f for f in findings
               if f.severity == "error" or (args.strict and f.severity == "warning")]
    return 1 if failing else 0


if __name__ == "__main__":
    # A Windows pipe (git hook, CI, `> file`) defaults to the ANSI code page,
    # where printing →, Δ or ✓ raises UnicodeEncodeError. Consoles and
    # Claude Code already use UTF-8 and are left alone.
    for _stream in (sys.stdout, sys.stderr):
        if getattr(_stream, "encoding", "utf-8").lower() not in ("utf-8", "utf8"):
            _stream.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
