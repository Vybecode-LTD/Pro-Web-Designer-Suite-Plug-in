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
                               shadows and font sizes outside the token file
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

Adopting it on a legacy codebase
--------------------------------
    python -m scripts.audit_design src/ --write-baseline .design-baseline.json
    python -m scripts.audit_design src/                   # only NEW findings fail

The baseline records existing violations so the gate can be turned on today
and the debt paid down deliberately, instead of the gate being turned off.

Escape hatches (use sparingly, they are visible in review)
---------------------------------------------------------
    /* design-audit-ignore-next-line: L2 -- CMS flow container, see ADR-014 */
    /* design-audit-ignore-file: L1 -- generated, do not hand-edit */

Exit codes: 0 clean · 1 violations found · 2 bad invocation.
"""

from __future__ import annotations

import argparse
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

SKIP_DIRS = {
    "node_modules", ".git", "dist", "build", ".next", ".nuxt", ".svelte-kit",
    "coverage", "__pycache__", ".venv", "venv", "vendor", ".turbo", "out",
}

# Files where literal values are not merely allowed but required: this is the
# one place a raw value is a design decision rather than a leak.
TOKEN_FILE_PAT = re.compile(
    # tokens.css, brand-tokens.css, deck-tokens.css, design.tokens.css,
    # theme.css, dark-theme.css. A separator before "tokens" is required so
    # that an ordinary file like "mytokens.css" is not waved through.
    r"(^|[/\\])([\w.-]*[-.])?tokens?\.(css|scss)$"
    r"|(^|[/\\])[\w.-]*theme\.(css|scss)$"
)

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

TYPE_PROPS = {"font-size", "line-height", "letter-spacing", "font-weight", "font"}
MOTION_PROPS = {"transition", "transition-duration", "animation",
                "animation-duration", "transition-timing-function",
                "animation-timing-function"}
RADIUS_PROPS = {"border-radius", "border-start-start-radius",
                "border-start-end-radius", "border-end-start-radius",
                "border-end-end-radius", "border-top-left-radius",
                "border-top-right-radius", "border-bottom-left-radius",
                "border-bottom-right-radius"}
SHADOW_PROPS = {"box-shadow", "text-shadow"}

# Tier-1 primitives that HAVE a Tier-2 role, so reading them from a component
# is a Law 6 violation. Prefixes without a semantic equivalent (--radius-*,
# --stroke-*, --z-*, --bp-*, --font-*, --measure-*, --width-*, --tap-min) are
# deliberately absent: they are primitives with no role layer, and using them
# directly is correct.
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
    "weight-": "a type role (--type-*), which carries weight in its shorthand",
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

# Three or more classes compounded in one selector is specificity built to win
# a fight that layers already settled.
COMPOUND_SEL = re.compile(r"(\.[\w-]+(?:\s*[>+~]?\s*)){3,}\.[\w-]+")

# Values that are legitimately literal anywhere.
KEYWORD_OK = {
    "0", "0px", "0rem", "auto", "none", "inherit", "initial", "unset", "revert",
    "revert-layer", "currentcolor", "transparent", "normal", "min-content",
    "max-content", "fit-content", "stretch", "baseline", "center", "start",
    "end", "flex-start", "flex-end", "space-between", "space-around",
    "space-evenly", "safe", "unsafe", "subgrid", "full-width", "100%", "50%",
}

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
TW_SPACE_XY = re.compile(r"(?<![\w-])(?:[a-z]{2}:)*space-[xy]-\d")
JSX_STYLE = re.compile(r"\bstyle\s*=\s*\{\{")

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

    def key(self) -> str:
        """Stable identity for baselining. Deliberately excludes the line
        number so that unrelated edits above a violation do not resurrect it."""
        return f"{self.file}|{self.rule}|{self.snippet.strip()[:120]}"


# ---------------------------------------------------------------------------
# CSS scanning
# ---------------------------------------------------------------------------

def strip_css_comments(text: str) -> tuple[str, dict[int, str]]:
    """Blank out comments while preserving line numbers and offsets.

    Returns the blanked text plus a map of line number -> original comment
    text, so ignore-pragmas remain readable.
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
            comments[start_line] = comments.get(start_line, "") + body
            for j in range(start, i):
                if out[j] != "\n":
                    out[j] = " "
            continue
        if ch == "/" and i + 1 < n and text[i + 1] == "/":
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
        # braces; they are not style-rule nesting and must not count.
        return sum(1 for s in sel_stack if s)

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
                yield ("rule_open", head, line, rule_depth())
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
    s = str(path).replace(os.sep, "/").lower()
    return (
        ".module." in s
        or "/components/" in s
        or "/ui/" in s
        or s.endswith("components.css")
    )


def in_layer(at_rules: Iterable[str], name: str) -> bool:
    return any(a.startswith("@layer") and name in a for a in at_rules)


def in_query_prelude(at_rules: Iterable[str]) -> bool:
    return any(a.startswith(("@media", "@container", "@supports")) for a in at_rules)


def value_is_tokenized(value: str) -> bool:
    v = value.strip().lower().rstrip("!important").strip()
    if not v:
        return True
    if "var(--" in v:
        return True
    if v in KEYWORD_OK:
        return True
    parts = [p for p in re.split(r"[\s,/]+", v) if p]
    return all(
        p in KEYWORD_OK or RELATIONAL_UNIT.match(p) or "var(--" in p
        for p in parts
    )


def has_raw_length(value: str) -> str | None:
    v = re.sub(r"var\(--[\w-]+(\s*,[^()]*)?\)", " ", value)
    m = LENGTH_LITERAL.search(v)
    if not m:
        return None
    if re.fullmatch(r"-?0+(\.0+)?(px|rem|em)?", m.group(0), re.I):
        return None
    return m.group(0)


def owl_selector(selectors: tuple[str, ...]) -> bool:
    """The parent-owned flow idiom: `> * + *` written in the PARENT's rule."""
    return any(re.search(r"\+\s*\*|\*\s*\+", s) for s in selectors)


def margin_is_alignment(value: str) -> bool:
    return "auto" in value.lower()


def margin_cancels_token(value: str) -> bool:
    """`calc(var(--token) * -1)` keeps the relationship; `-24px` does not."""
    return "var(--" in value and "-1" in value.replace(" ", "")


# ---------------------------------------------------------------------------
# CSS rules
# ---------------------------------------------------------------------------

def audit_css(path: Path, text: str) -> list[Finding]:
    findings: list[Finding] = []
    lines = text.splitlines()
    clean, comments = strip_css_comments(text)

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
    any_top_level_rule_outside_layer = False
    declared_props: set[str] = set()

    def add(line: int, law: str, rule: str, sev: str, msg: str, fix: str) -> None:
        tags = line_ignores.get(line, set()) | file_ignores
        if law in tags or rule.upper() in tags or "ALL" in tags:
            return
        snippet = lines[line - 1].strip() if 0 < line <= len(lines) else ""
        findings.append(Finding(str(path), line, law, rule, sev, msg, fix, snippet))

    at_depth_stack: list[str] = []

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
            elif kind == "at_open":
                at_depth_stack.append(ev[1])
            elif kind == "rule_open":
                sel, line, depth = ev[1], ev[2], ev[3]
                if not first_rule_line:
                    first_rule_line = line
                if depth > 2:
                    add(line, "L5", "nesting-depth", "error",
                        f"Nesting depth {depth} exceeds the limit of 2.",
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
                if not token_file and depth == 1 and not any(
                    a.startswith("@layer") for a in at_depth_stack
                ):
                    any_top_level_rule_outside_layer = True
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
            # are fine; a length, a colour or a duration is not.
            if not token_file and "var(--" not in value:
                if OPTICAL_PROP.search(prop):
                    pass                       # declared optical correction
                elif has_raw_length(value) and not RELATIONAL_UNIT.match(value.strip()):
                    add(line, "L1", "socket-literal", "error",
                        f"Socket `{prop}` is declared as the literal `{value.strip()}`.",
                        "A custom property is not a token. Bind the socket to "
                        "a Tier-2 role — that is what makes the component "
                        "theme-able, density-aware and auditable. If no role "
                        "fits, the missing role is the actual finding.")
                elif HEX_COLOR.search(value) or FUNC_COLOR.search(value):
                    add(line, "L1", "socket-literal", "error",
                        f"Socket `{prop}` hardcodes the colour `{value.strip()}`.",
                        "Dark mode re-points roles, not sockets. A literal "
                        "here is a colour the theme can never reach.")
                elif TIME_LITERAL.search(value) or BEZIER_LITERAL.search(value):
                    add(line, "L1", "socket-literal", "error",
                        f"Socket `{prop}` hardcodes motion: `{value.strip()}`.",
                        "Bind it to a --motion-* pair so duration and easing "
                        "stay together and prefers-reduced-motion still "
                        "applies.")

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

        tokenized = value_is_tokenized(value)

        # ---- L1 / L3 spacing -----------------------------------------------
        if prop in SPACING_PROPS and not in_query_prelude(d.at_rules):
            raw = has_raw_length(value)
            # em is a RATIO to the current font size, so an em offset tracks
            # type instead of bypassing the scale. Legitimate for positioning
            # (sup/sub, optical nudges), never for layout gaps.
            if raw and raw.lower().endswith("em") and prop not in (
                    OUTER_MARGIN_PROPS | {"gap", "row-gap", "column-gap",
                                          "grid-gap"}) and not prop.startswith("padding"):
                raw = None
            if raw and not tokenized:
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
                and "prose" not in " ".join(d.selectors).lower()):
            add(line, "L2", "child-margin", "error",
                f"`{prop}` on a component. A child may not set its own outer margin.",
                "The parent owns the space between siblings — set `gap` on the "
                "parent instead. A component cannot know what it sits next to, "
                "so a margin here is a fact asserted from inside. "
                "(Legal: margin:auto for alignment, calc(var(--t) * -1) to "
                "cancel a known token, an owl selector in the parent's rule.)")

        # ---- L1 colour ------------------------------------------------------
        if prop in COLOR_PROPS or prop == "border":
            if "var(--" not in value:
                m = HEX_COLOR.search(value) or FUNC_COLOR.search(value)
                if m:
                    add(line, "L1", "raw-color", "error",
                        f"`{prop}: {value.strip()}` hardcodes a colour.",
                        "Use a role: --bg-surface / --fg-muted / --border-default "
                        "/ --bg-accent. A hardcoded colour is a colour that dark "
                        "mode cannot re-point, which is how a theme silently breaks.")
                elif NAMED_COLOR.search(value) and prop in COLOR_PROPS:
                    add(line, "L1", "named-color", "warning",
                        f"`{prop}: {value.strip()}` uses a CSS named colour.",
                        "Named colours are outside the ramp and outside the "
                        "contrast budget. Use a role token.")

        # ---- L1 shadows ------------------------------------------------------
        if prop in SHADOW_PROPS and "var(--" not in value and value.strip() != "none":
            add(line, "L1", "raw-shadow", "error",
                f"`{prop}` is a literal shadow.",
                "Use an elevation role: --elevation-card / --elevation-raised / "
                "--elevation-overlay / --elevation-modal. Hand-rolled shadows "
                "drift out of the light model within about three commits.")

        # ---- L1 typography ---------------------------------------------------
        if prop in TYPE_PROPS and "var(--" not in value:
            if prop == "line-height" and re.fullmatch(r"[\d.]+", value.strip()):
                add(line, "L3", "raw-leading", "warning",
                    f"`line-height: {value.strip()}` is a literal ratio.",
                    "Use --leading-* in base.css, or better, a --type-* role "
                    "which carries leading in its font shorthand.")
            elif (has_raw_length(value)
                  and not RELATIONAL_UNIT.match(value.strip())
                  and not (has_raw_length(value) or "").lower().endswith("em")):
                add(line, "L1", "raw-type", "error",
                    f"`{prop}: {value.strip()}` is off the type scale.",
                    "Use a --type-* role (--type-body, --type-h2, --type-ui). "
                    "Orphan sizes are how hierarchy stops reading as hierarchy.")

        # ---- L1 radius -------------------------------------------------------
        if prop in RADIUS_PROPS and "var(--" not in value and has_raw_length(value):
            add(line, "L1", "raw-radius", "error",
                f"`{prop}: {value.strip()}` is a literal radius.",
                "Use --radius-*. Concentric corners depend on the radius and the "
                "inset being related — see references/spacing-system.md §8.")

        # ---- L1 motion -------------------------------------------------------
        if prop in MOTION_PROPS and "var(--" not in value:
            if TIME_LITERAL.search(value):
                add(line, "L1", "raw-duration", "error",
                    f"`{prop}: {value.strip()}` hardcodes a duration.",
                    "Use --motion-hover / --motion-enter / --motion-exit / "
                    "--motion-expand. A literal duration also ignores "
                    "prefers-reduced-motion, which the tokens handle for you.")
            elif BEZIER_LITERAL.search(value):
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
                    if any(bare.startswith(p) for p in TIER1_MOTION) and prop in MOTION_PROPS:
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
    if not token_file and any_top_level_rule_outside_layer:
        add(first_rule_line or 1, "L5", "unlayered", "error",
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

    def line_of(pos: int) -> int:
        return clean.count("\n", 0, pos) + 1

    def add(line: int, law: str, rule: str, sev: str, msg: str, fix: str) -> None:
        tags = line_ignores.get(line, set()) | file_ignores
        if law in tags or rule.upper() in tags or "ALL" in tags:
            return
        snippet = lines[line - 1].strip() if 0 < line <= len(lines) else ""
        findings.append(Finding(str(path), line, law, rule, sev, msg, fix, snippet))

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

    # ---- Tailwind arbitrary values / bang / space-x ------------------------
    for sm in re.finditer(r"""(?:className|class)\s*=\s*(?:\{?\s*)?["'`]([^"'`]*)["'`]""", clean):
        cls, at = sm.group(1), sm.start(1)
        for m in TW_ARBITRARY.finditer(cls):
            tok = m.group(0)
            if re.match(r"^(grid-cols|grid-rows|aspect|content|mask|bg|supports|data|aria)-\[", tok):
                continue
            add(line_of(at), "L3", "tw-arbitrary", "error",
                f"Tailwind arbitrary value `{tok}`.",
                "The theme IS the token file, so an on-scale class already "
                "exists for whatever this is. An arbitrary value re-opens the "
                "unbounded value space the closed scale exists to shut.")
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
        clean, _ = strip_css_comments(text)
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

def iter_files(paths: list[str]) -> Iterator[Path]:
    for raw in paths:
        p = Path(raw)
        if p.is_file():
            yield p
        elif p.is_dir():
            for root, dirs, files in os.walk(p):
                dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
                for f in sorted(files):
                    fp = Path(root) / f
                    if fp.suffix.lower() in CSS_EXT | JS_EXT:
                        yield fp


def audit(paths: list[str]) -> list[Finding]:
    out: list[Finding] = []
    css_sources: list[tuple[Path, str]] = []
    for fp in iter_files(paths):
        try:
            text = fp.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if fp.suffix.lower() in CSS_EXT:
            css_sources.append((fp, text))
        try:
            if fp.suffix.lower() in CSS_EXT:
                out.extend(audit_css(fp, text))
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
    return out


LAW_NAMES = {
    "L1": "Tokens or nothing",
    "L2": "Parents own the gaps",
    "L3": "The scale is closed",
    "L4": "One home per component's styles",
    "L5": "Layers, not specificity",
    "L6": "Semantic before primitive",
}


def report(findings: list[Finding], *, use_color: bool, show_fix: bool) -> str:
    if not findings:
        return "design audit: clean — all nine laws hold.\n"

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
    ap.add_argument("--baseline", metavar="FILE", default=".design-baseline.json",
                    help="ignore findings recorded in this file (default: .design-baseline.json)")
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

    findings = audit(paths)

    if args.law:
        wanted = {l.upper() for l in args.law}
        findings = [f for f in findings if f.law in wanted]

    if args.write_baseline:
        Path(args.write_baseline).write_text(
            json.dumps(sorted({f.key() for f in findings}), indent=2) + "\n",
            encoding="utf-8")
        print(f"audit_design: recorded {len(findings)} finding(s) as the baseline in "
              f"{args.write_baseline}.\nOnly NEW violations will fail from now on. "
              f"Pay the debt down per directory, not all at once.")
        return 0

    baseline: set[str] = set()
    bp = Path(args.baseline)
    if bp.exists():
        try:
            baseline = set(json.loads(bp.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            print(f"audit_design: could not read baseline {bp}; auditing everything.",
                  file=sys.stderr)
    if baseline:
        findings = [f for f in findings if f.key() not in baseline]

    if args.json:
        print(json.dumps([asdict(f) for f in findings], indent=2))
    else:
        use_color = not args.no_color and sys.stdout.isatty()
        sys.stdout.write(report(findings, use_color=use_color, show_fix=not args.quiet))

    failing = [f for f in findings
               if f.severity == "error" or (args.strict and f.severity == "warning")]
    return 1 if failing else 0


if __name__ == "__main__":
    sys.exit(main())
