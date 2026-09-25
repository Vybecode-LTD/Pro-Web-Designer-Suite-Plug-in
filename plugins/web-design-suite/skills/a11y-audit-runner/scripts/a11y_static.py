#!/usr/bin/env python3
"""
a11y_static.py — layer one of the accessibility gate. Source only, no browser.

The sibling of `audit_design.py` and `perf_audit.py`: same report shape, same
severity model, same baseline philosophy, same comment pragmas, same exit codes.
It runs in about a second on a repo and belongs in the pre-commit hook.

What it is honest about
-----------------------
This catches the machine-checkable subset of the machine-checkable subset. In
the only controlled study with a known denominator — GDS, 2017, 143 planted
failures, ten tools — the best single automated tool found 37-41% of them. A
clean run here means the cheapest class of error is absent. It does NOT mean
the page is accessible, and it must never be reported as if it did. See
references/automation-coverage.md before quoting this tool to a client.

What it checks
--------------
  S  Structure        heading skips, multiple h1, missing/duplicate landmarks,
                      missing lang, missing or empty <title>, zoom disabled
  N  Name             <img> with no alt, alt that is a filename or "image of",
                      empty buttons and links, non-descriptive link text,
                      duplicate control names in one file
  K  Keyboard/focus   positive tabindex, click handlers on non-interactive
                      elements, aria-hidden over focusable content,
                      `outline: none` with no replacement, shadow-only rings
  R  ARIA             invalid aria-* names and values, aria-* pointing at an id
                      that does not exist, redundant explicit roles,
                      duplicate ids, presentational focusable elements
  F  Forms            controls with no label by any of the four mechanisms,
                      missing `autocomplete` on personal-data fields (SC 1.3.5),
                      invalid `autocomplete` tokens

Every finding carries the WCAG success criterion it maps to, because "the
linter says so" loses an argument and "1.3.5, and here is the fix" does not.
The criteria themselves are specified in
`web-design-studio/references/accessibility.md` §1; this file automates them,
it does not restate them.

Usage
-----
    python -m scripts.a11y_static src/
    python -m scripts.a11y_static src/ --json
    python -m scripts.a11y_static src/ --strict            # warnings fail too
    python -m scripts.a11y_static src/ --category N --category F
    python -m scripts.a11y_static src/ --sc 1.3.5
    python -m scripts.a11y_static $(git diff --cached --name-only)

Adopting it on a codebase that has never been audited
-----------------------------------------------------
    python -m scripts.a11y_static src/ --write-baseline .a11y-baseline.json
    python -m scripts.a11y_static src/            # only NEW findings fail

A gate that fails on day one is a gate somebody deletes on day two. The
baseline freezes today's debt so the gate can go on this afternoon.

Escape hatches (visible in review, which is the point)
------------------------------------------------------
    <!-- a11y-audit-ignore-next-line: N -- alt comes from the CMS, A11Y-88 -->
    {/* a11y-audit-ignore-next-line: K -- third-party embed, ticket A11Y-91 */}
    /* a11y-audit-ignore-file: R -- generated, do not hand-edit */

Tags are a category letter, a rule name, or ALL. Everything after `--` is the
reason, and a pragma with no reason should not survive review.

Exit codes: 0 clean · 1 violations found · 2 bad invocation.
"""

from __future__ import annotations

import argparse
import bisect
import json
import os
import re
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterator

# ---------------------------------------------------------------------------
# File selection
# ---------------------------------------------------------------------------

MARKUP_EXT = {".html", ".htm", ".xhtml", ".vue", ".svelte", ".astro", ".php",
              ".erb", ".hbs", ".handlebars", ".twig", ".liquid", ".jinja",
              ".j2", ".ejs"}
JSX_EXT = {".jsx", ".tsx", ".js", ".ts", ".mjs", ".cjs"}
CSS_EXT = {".css", ".scss", ".sass", ".less", ".pcss"}

SKIP_DIRS = {
    "node_modules", ".git", "dist", "build", ".next", ".nuxt", ".svelte-kit",
    "coverage", "__pycache__", ".venv", "venv", "vendor", ".turbo", "out",
    "storybook-static", ".cache",
}

GENERATED_MARKERS = ("@generated", "DO NOT EDIT", "AUTO-GENERATED", "Auto-generated")

IGNORE_LINE = re.compile(r"a11y-audit-ignore-next-line\s*:?\s*([\w,\s]*)")
IGNORE_FILE = re.compile(r"a11y-audit-ignore-file\s*:?\s*([\w,\s]*)")

SEVERITY_ORDER = {"error": 0, "warning": 1}

CATEGORY_NAMES = {
    "S": "Structure and semantics",
    "N": "Name and text alternative",
    "K": "Keyboard and focus",
    "R": "ARIA correctness",
    "F": "Forms",
}

# ---------------------------------------------------------------------------
# The HTML/JSX vocabulary
# ---------------------------------------------------------------------------

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link",
        "meta", "param", "source", "track", "wbr"}

# Elements that arrive with a role, a name, keyboard activation and a focus
# ring already attached. §2 of accessibility.md: the first accessibility tool
# is the right element.
NATIVELY_INTERACTIVE = {"a", "button", "input", "select", "textarea", "summary",
                        "option", "audio", "video", "iframe", "embed", "object",
                        "details", "label"}

NON_INTERACTIVE = {"div", "span", "p", "li", "td", "tr", "section", "article",
                   "header", "footer", "main", "aside", "nav", "ul", "ol", "dl",
                   "dt", "dd", "figure", "figcaption", "table", "tbody", "thead",
                   "tfoot", "h1", "h2", "h3", "h4", "h5", "h6", "img", "svg",
                   "blockquote", "pre", "small", "strong", "em", "b", "i"}

HEADINGS = {"h1", "h2", "h3", "h4", "h5", "h6"}

LANDMARK_TAGS = {"nav": "navigation", "main": "main", "aside": "complementary",
                 "form": "form", "search": "search"}

# <header> and <footer> are landmarks ONLY when they are not inside a sectioning
# element. A card's <footer> is not a contentinfo — this is why a page can look
# like it has six footers and actually have one.
SECTIONING = {"article", "aside", "main", "nav", "section"}

FOCUSABLE_SEL = {"a", "button", "input", "select", "textarea", "summary",
                 "iframe", "audio", "video", "details", "area", "object"}

# Input types that are not labelable text-ish controls.
INPUT_NO_LABEL_NEEDED = {"hidden", "submit", "reset", "button", "image"}
INPUT_NOT_PERSONAL = {"hidden", "submit", "reset", "button", "image", "checkbox",
                      "radio", "file", "range", "color"}

# Implicit ARIA roles, for the "you wrote the role it already had" check. Only
# the ones people actually write redundantly are listed; a missing entry means
# the rule stays quiet, which is the correct failure direction.
IMPLICIT_ROLE = {
    "button": "button", "nav": "navigation", "main": "main",
    "aside": "complementary", "article": "article", "dialog": "dialog",
    "form": "form", "table": "table", "tr": "row", "td": "cell",
    "th": "columnheader", "thead": "rowgroup", "tbody": "rowgroup",
    "tfoot": "rowgroup", "li": "listitem", "option": "option",
    "fieldset": "group", "progress": "progressbar", "output": "status",
    "hr": "separator", "textarea": "textbox", "h1": "heading", "h2": "heading",
    "h3": "heading", "h4": "heading", "h5": "heading", "h6": "heading",
    "search": "search", "figure": "figure", "summary": "button",
}
INPUT_IMPLICIT_ROLE = {
    "checkbox": "checkbox", "radio": "radio", "range": "slider",
    "number": "spinbutton", "text": "textbox", "email": "textbox",
    "tel": "textbox", "url": "textbox", "search": "searchbox",
    "submit": "button", "reset": "button", "button": "button",
}

# ARIA 1.2 attributes and the shape of their values. An attribute not in this
# table is not a real ARIA attribute — the overwhelmingly common cause is a
# typo (`aria-labeledby`), which is silently ignored by every browser.
ARIA_ATTRS: dict[str, tuple[str, tuple[str, ...]]] = {
    "aria-activedescendant": ("idref", ()),
    "aria-atomic": ("bool", ()),
    "aria-autocomplete": ("token", ("inline", "list", "both", "none")),
    "aria-braillelabel": ("string", ()),
    "aria-brailleroledescription": ("string", ()),
    "aria-busy": ("bool", ()),
    "aria-checked": ("token", ("true", "false", "mixed", "undefined")),
    "aria-colcount": ("int", ()),
    "aria-colindex": ("int", ()),
    "aria-colindextext": ("string", ()),
    "aria-colspan": ("int", ()),
    "aria-controls": ("idrefs", ()),
    "aria-current": ("token", ("page", "step", "location", "date", "time",
                               "true", "false")),
    "aria-describedby": ("idrefs", ()),
    "aria-description": ("string", ()),
    "aria-details": ("idrefs", ()),
    "aria-disabled": ("bool", ()),
    "aria-errormessage": ("idref", ()),
    "aria-expanded": ("token", ("true", "false", "undefined")),
    "aria-flowto": ("idrefs", ()),
    "aria-haspopup": ("token", ("false", "true", "menu", "listbox", "tree",
                                "grid", "dialog")),
    "aria-hidden": ("token", ("true", "false", "undefined")),
    "aria-invalid": ("token", ("grammar", "false", "spelling", "true")),
    "aria-keyshortcuts": ("string", ()),
    "aria-label": ("string", ()),
    "aria-labelledby": ("idrefs", ()),
    "aria-level": ("int", ()),
    "aria-live": ("token", ("assertive", "off", "polite")),
    "aria-modal": ("bool", ()),
    "aria-multiline": ("bool", ()),
    "aria-multiselectable": ("bool", ()),
    "aria-orientation": ("token", ("horizontal", "vertical", "undefined")),
    "aria-owns": ("idrefs", ()),
    "aria-placeholder": ("string", ()),
    "aria-posinset": ("int", ()),
    "aria-pressed": ("token", ("true", "false", "mixed", "undefined")),
    "aria-readonly": ("bool", ()),
    "aria-relevant": ("tokenlist", ("additions", "all", "removals", "text")),
    "aria-required": ("bool", ()),
    "aria-roledescription": ("string", ()),
    "aria-rowcount": ("int", ()),
    "aria-rowindex": ("int", ()),
    "aria-rowindextext": ("string", ()),
    "aria-rowspan": ("int", ()),
    "aria-selected": ("token", ("true", "false", "undefined")),
    "aria-setsize": ("int", ()),
    "aria-sort": ("token", ("ascending", "descending", "none", "other")),
    "aria-valuemax": ("number", ()),
    "aria-valuemin": ("number", ()),
    "aria-valuenow": ("number", ()),
    "aria-valuetext": ("string", ()),
}
# Deprecated in ARIA 1.2 but still valid attribute names.
ARIA_DEPRECATED = {"aria-dropeffect", "aria-grabbed"}

ARIA_IDREF_ATTRS = {a for a, (kind, _) in ARIA_ATTRS.items()
                    if kind in ("idref", "idrefs")}

VALID_ROLES = {
    "alert", "alertdialog", "application", "article", "banner", "blockquote",
    "button", "caption", "cell", "checkbox", "code", "columnheader", "combobox",
    "command", "complementary", "composite", "contentinfo", "definition",
    "deletion", "dialog", "directory", "document", "emphasis", "feed", "figure",
    "form", "generic", "grid", "gridcell", "group", "heading", "img", "input",
    "insertion", "landmark", "link", "list", "listbox", "listitem", "log",
    "main", "mark", "marquee", "math", "menu", "menubar", "menuitem",
    "menuitemcheckbox", "menuitemradio", "meter", "navigation", "none", "note",
    "option", "paragraph", "presentation", "progressbar", "radio", "radiogroup",
    "range", "region", "roletype", "row", "rowgroup", "rowheader", "scrollbar",
    "search", "searchbox", "section", "sectionhead", "select", "separator",
    "slider", "spinbutton", "status", "strong", "structure", "subscript",
    "suggestion", "superscript", "switch", "tab", "table", "tablist", "tabpanel",
    "term", "textbox", "time", "timer", "toolbar", "tooltip", "tree", "treegrid",
    "treeitem", "widget", "window",
}

# SC 1.3.5. An invalid token is WORSE than none: the browser ignores it and the
# criterion is not met, so the field looks handled and is not.
AUTOCOMPLETE_TOKENS = {
    "on", "off", "name", "honorific-prefix", "given-name", "additional-name",
    "family-name", "honorific-suffix", "nickname", "username", "new-password",
    "current-password", "one-time-code", "organization-title", "organization",
    "street-address", "address-line1", "address-line2", "address-line3",
    "address-level4", "address-level3", "address-level2", "address-level1",
    "country", "country-name", "postal-code", "cc-name", "cc-given-name",
    "cc-additional-name", "cc-family-name", "cc-number", "cc-exp",
    "cc-exp-month", "cc-exp-year", "cc-csc", "cc-type", "transaction-currency",
    "transaction-amount", "language", "bday", "bday-day", "bday-month",
    "bday-year", "sex", "tel", "tel-country-code", "tel-national",
    "tel-area-code", "tel-local", "tel-extension", "impp", "url", "photo",
    "email", "webauthn",
}
AUTOCOMPLETE_PREFIX = {"shipping", "billing", "home", "work", "mobile", "fax",
                       "pager"}

# name/id/placeholder fragment -> the token SC 1.3.5 expects. Ordered: the first
# match wins, so the more specific patterns come first.
PERSONAL_FIELD_HINTS: tuple[tuple[str, str], ...] = (
    (r"confirm[_-]?password|new[_-]?password|password2", "new-password"),
    (r"current[_-]?password|^password$|passwd|\bpwd\b", "current-password"),
    (r"one[_-]?time|otp|2fa|mfa|auth[_-]?code|verification[_-]?code", "one-time-code"),
    (r"user[_-]?name|^login$|^userid$", "username"),
    (r"e[-_]?mail", "email"),
    (r"first[_-]?name|given[_-]?name|^fname$", "given-name"),
    (r"last[_-]?name|family[_-]?name|surname|^lname$", "family-name"),
    (r"full[_-]?name|^name$|your[_-]?name|display[_-]?name", "name"),
    (r"organi[sz]ation|company|business[_-]?name|^employer$", "organization"),
    (r"job[_-]?title|^title$&", "organization-title"),
    (r"address[_-]?line[_-]?2|^addr2$|apartment|suite|unit", "address-line2"),
    (r"address[_-]?line[_-]?1|^addr1$|street", "address-line1"),
    (r"^address$|mailing[_-]?address", "street-address"),
    (r"^city$|town|locality", "address-level2"),
    (r"^state$|province|^region$|county", "address-level1"),
    (r"zip|post[_-]?code|postal", "postal-code"),
    (r"country", "country-name"),
    (r"card[_-]?number|cc[_-]?number|credit[_-]?card", "cc-number"),
    (r"cc[_-]?exp|expiry|expiration", "cc-exp"),
    (r"\bcvv\b|\bcvc\b|\bcsc\b|security[_-]?code", "cc-csc"),
    (r"card[_-]?holder|cc[_-]?name|name[_-]?on[_-]?card", "cc-name"),
    (r"birth|^dob$|^bday$", "bday"),
    (r"^tel$|phone|mobile|telephone|^cell$", "tel"),
    (r"^url$|website|homepage", "url"),
)

# 2.4.4. Matched against the WHOLE normalised link text, never as a substring:
# "Continue to the next section" is a fine link and "Continue" is not.
VAGUE_LINK_TEXT = {
    "click here", "click", "here", "read more", "more", "learn more", "details",
    "link", "this", "this page", "continue", "go", "go there", "download",
    "info", "more info", "see more", "view", "view more", "find out more",
    "start", "submit", "next", "read on", "full story", "see details",
    "click this link", "link to page", "open", "check it out",
}

ALT_PREFIX_NOISE = re.compile(
    r"^\s*(image|photo|photograph|picture|graphic|icon|logo|screenshot)\s*"
    r"(of|showing|:|-)\s", re.I)
ALT_FILENAME = re.compile(
    r"^[\w\s./\\-]*\.(png|jpe?g|gif|svg|webp|avif|bmp|ico|tiff?)\s*$", re.I)
ALT_PLACEHOLDER = re.compile(
    r"^\s*(image|img|photo|picture|graphic|icon|logo|alt|alt text|untitled|"
    r"spacer|placeholder|dsc[_-]?\d+|img[_-]?\d+|screenshot)\s*\d*\s*$", re.I)

BARE_URL = re.compile(r"^\s*(https?://|www\.)\S*\s*$", re.I)


# ---------------------------------------------------------------------------
# Findings
# ---------------------------------------------------------------------------

@dataclass
class Finding:
    file: str
    line: int
    category: str
    rule: str
    sc: str
    severity: str
    message: str
    fix: str
    snippet: str = ""

    def key(self) -> str:
        """Stable identity for baselining. Excludes the line number so that an
        unrelated edit above a violation does not resurrect it."""
        return f"{self.file}|{self.rule}|{self.snippet.strip()[:120]}"


# ---------------------------------------------------------------------------
# A small tag scanner that survives both HTML and JSX
# ---------------------------------------------------------------------------
#
# Not a parser. It needs to answer: what elements exist, what attributes do they
# carry, what text is inside them, and what is nested in what. A real parser
# would refuse JSX's `{expr}` attribute values and its unbalanced conditional
# fragments; this deliberately tolerates both and reports what it can see.

TAG_START = re.compile(r"<(/?)([A-Za-z][\w:.-]*)")
ATTR_NAME = re.compile(r"[A-Za-z_@:$][\w:.$@-]*")

# A JSX attribute value of `{...}` is opaque: we know the attribute is PRESENT
# but not what it evaluates to. Rules must treat that as "cannot tell", never as
# "empty" — a false positive on a dynamic value is how a team disables a linter.
EXPR = "\x00EXPR\x00"


@dataclass
class Tag:
    name: str
    attrs: dict
    attr_lines: dict
    line: int
    start: int
    end: int
    self_closing: bool
    closing: bool


def _skip_braces(text: str, i: int) -> int:
    """Index just past the `}` matching the `{` at i, honouring quotes."""
    depth, n = 0, len(text)
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


def _line_finder(text: str):
    """pos -> 1-based line number, by bisecting a newline index built once.
    Counting newlines from the top of the file for every tag and attribute made
    large pages quadratic."""
    starts = [0] + [m.end() for m in re.finditer("\n", text)]
    return lambda pos: bisect.bisect_right(starts, pos)


def scan_tags(text: str) -> list[Tag]:
    tags: list[Tag] = []
    n = len(text)
    i = 0
    line_of = _line_finder(text)
    while i < n:
        j = text.find("<", i)
        if j < 0:
            break
        m = TAG_START.match(text, j)
        if not m:
            i = j + 1
            continue
        closing = bool(m.group(1))
        name = m.group(2)
        k = m.end()
        attrs: dict = {}
        attr_lines: dict = {}
        self_closing = False
        line = line_of(j)
        while k < n:
            while k < n and text[k].isspace():
                k += 1
            if k >= n:
                break
            if text.startswith("/>", k):
                k += 2
                self_closing = True
                break
            if text[k] == ">":
                k += 1
                break
            if text[k] == "{":                       # JSX spread: {...props}
                k = _skip_braces(text, k)
                attrs["\x00spread"] = EXPR
                continue
            am = ATTR_NAME.match(text, k)
            if not am:
                k += 1
                continue
            raw_name = am.group(0)
            aline = line_of(k)
            k = am.end()
            while k < n and text[k].isspace():
                k += 1
            value: str = ""
            if k < n and text[k] == "=":
                k += 1
                while k < n and text[k].isspace():
                    k += 1
                if k < n and text[k] in "\"'":
                    q = text[k]
                    end = text.find(q, k + 1)
                    if end < 0:
                        end = n
                    value = text[k + 1:end]
                    k = end + 1
                elif k < n and text[k] == "{":
                    start = k
                    k = _skip_braces(text, k)
                    inner = text[start + 1:k - 1].strip()
                    # {"literal"} and {'literal'} are knowable; anything else
                    # is a runtime value and must be treated as unknown.
                    lit = re.fullmatch(r"""['"`]([^'"`]*)['"`]""", inner)
                    value = lit.group(1) if lit else EXPR
                else:
                    vm = re.match(r"[^\s>]+", text[k:])
                    value = vm.group(0) if vm else ""
                    k += len(value)
            key = raw_name.lower()
            # React spells them camelCase; normalise so one rule covers both.
            key = {"classname": "class", "htmlfor": "for"}.get(key, key)
            if key not in attrs:
                attrs[key] = value
                attr_lines[key] = aline
        tags.append(Tag(name.lower() if name[:1].islower() else name,
                        attrs, attr_lines, line, j, k, self_closing, closing))
        i = max(k, j + 1)
    return tags


@dataclass
class Node:
    tag: Tag
    text: str          # inner text, tags stripped
    inner_start: int
    inner_end: int
    descendants: list   # list[Node]


def build_tree(text: str, tags: list[Tag]) -> list[Node]:
    """Pair open and close tags. Unbalanced markup is normal in templates, so a
    tag that is never closed simply gets an empty body rather than derailing
    the file."""
    nodes: list[Node] = []
    stack: list[tuple[Tag, int]] = []
    opened: dict[int, Node] = {}
    for t in tags:
        if t.closing:
            for idx in range(len(stack) - 1, -1, -1):
                if stack[idx][0].name == t.name:
                    ot, oi = stack[idx]
                    node = opened[oi]
                    node.inner_end = t.start
                    node.text = strip_tags(text[node.inner_start:t.start])
                    del stack[idx:]
                    break
            continue
        if t.self_closing or t.name in VOID:
            node = Node(t, "", t.end, t.end, [])
            nodes.append(node)
            if stack:
                opened[stack[-1][1]].descendants.append(node)
            continue
        node = Node(t, "", t.end, t.end, [])
        nodes.append(node)
        if stack:
            opened[stack[-1][1]].descendants.append(node)
        opened[len(nodes) - 1] = node
        stack.append((t, len(nodes) - 1))
    return nodes


def strip_tags(s: str) -> str:
    """Inner text with markup removed. A JSX `{expr}` becomes a placeholder
    rather than nothing, so `<button>{label}</button>` is not "empty"."""
    out = []
    i, n = 0, len(s)
    while i < n:
        c = s[i]
        if c == "<":
            m = TAG_START.match(s, i)
            if m:
                depth = 0
                k = m.end()
                while k < n:
                    if s[k] in "\"'":
                        q = s[k]
                        e = s.find(q, k + 1)
                        k = n if e < 0 else e + 1
                        continue
                    if s[k] == "{":
                        k = _skip_braces(s, k)
                        continue
                    if s[k] == ">":
                        k += 1
                        break
                    k += 1
                i = k
                continue
            out.append(c)
            i += 1
            continue
        if c == "{":
            k = _skip_braces(s, i)
            inner = s[i + 1:k - 1].strip()
            if not inner.startswith("/*"):
                out.append("\x01")     # an expression: unknown but present
            i = k
            continue
        out.append(c)
        i += 1
    txt = "".join(out)
    txt = re.sub(r"&[#\w]+;", "\x01", txt)
    return re.sub(r"\s+", " ", txt).strip()


def has_real_text(s: str) -> bool:
    """An expression placeholder counts as text; whitespace does not."""
    return bool(s.replace("\x01", "x").strip())


def norm_text(s: str) -> str:
    return re.sub(r"\s+", " ", s.replace("\x01", "")).strip().lower()


# ---------------------------------------------------------------------------
# Comment handling
# ---------------------------------------------------------------------------

COMMENT_RANGES = [
    (re.compile(r"<!--.*?-->", re.S), "html"),
    (re.compile(r"\{\s*/\*.*?\*/\s*\}", re.S), "jsx"),
    (re.compile(r"/\*.*?\*/", re.S), "block"),
]


def extract_pragmas(text: str) -> tuple[set, dict]:
    """Pull ignore pragmas out of every comment syntax these files use."""
    file_ignores: set = set()
    line_ignores: dict = {}
    spans: list[tuple[int, int, str]] = []
    for rx, _ in COMMENT_RANGES:
        for m in rx.finditer(text):
            spans.append((m.start(), m.end(), m.group(0)))
    for m in re.finditer(r"//[^\n]*", text):
        spans.append((m.start(), m.end(), m.group(0)))
    line_of = _line_finder(text)
    for start, end, body in spans:
        fm = IGNORE_FILE.search(body)
        if fm:
            file_ignores |= {t.strip().upper() for t in fm.group(1).split(",") if t.strip()}
        lm = IGNORE_LINE.search(body)
        if lm:
            end_line = line_of(end)
            tags = {t.strip().upper() for t in lm.group(1).split(",") if t.strip()}
            # The pragma applies to the next line, and to the rest of this one
            # (an inline pragma before a tag on the same line).
            line_ignores.setdefault(end_line, set()).update(tags)
            line_ignores.setdefault(end_line + 1, set()).update(tags)
    return file_ignores, line_ignores


def blank_comments(text: str) -> str:
    """Blank comment bodies, preserving offsets and line numbers, so commented
    -out markup is not audited."""
    out = list(text)
    for rx, _ in COMMENT_RANGES:
        for m in rx.finditer(text):
            for i in range(m.start(), m.end()):
                if out[i] != "\n":
                    out[i] = " "
    return "".join(out)


# ---------------------------------------------------------------------------
# Markup audit
# ---------------------------------------------------------------------------

def audit_markup(path: Path, text: str, is_jsx: bool) -> list[Finding]:
    findings: list[Finding] = []
    lines = text.splitlines()
    file_ignores, line_ignores = extract_pragmas(text)
    clean = blank_comments(text)

    def add(line: int, cat: str, rule: str, sc: str, sev: str,
            msg: str, fix: str) -> None:
        tags = line_ignores.get(line, set()) | file_ignores
        if cat in tags or rule.upper() in tags or "ALL" in tags:
            return
        snippet = lines[line - 1].strip() if 0 < line <= len(lines) else ""
        findings.append(Finding(str(path), line, cat, rule, sc, sev, msg,
                                fix, snippet[:200]))

    tags = scan_tags(clean)
    nodes = build_tree(clean, tags)
    open_tags = [t for t in tags if not t.closing]

    # ---- ids, for reference checking -------------------------------------
    ids: dict[str, list[int]] = {}
    dynamic_ids = False
    for t in open_tags:
        raw = t.attrs.get("id")
        if raw is None:
            continue
        if raw == EXPR:
            dynamic_ids = True
            continue
        for part in raw.split():
            ids.setdefault(part, []).append(t.line)

    for ident, where in sorted(ids.items()):
        if len(where) > 1:
            add(where[1], "R", "duplicate-id", "4.1.1 (removed) / 1.3.1",
                "warning",
                f"id `{ident}` is used {len(where)} times "
                f"(lines {', '.join(str(w) for w in where)}).",
                "Duplicate ids are no longer a conformance failure in WCAG 2.2 "
                "— 4.1.1 Parsing was removed — but they still break every "
                "aria-labelledby, aria-describedby, aria-controls and <label "
                "for> that points at them, because the browser resolves an id "
                "to the FIRST match. The reference silently names the wrong "
                "element, which is worse than naming nothing.")

    # ---- per-element rules ------------------------------------------------
    nav_labels: list[tuple[str, int]] = []
    header_footer_top: dict[str, int] = {}
    heading_seq: list[tuple[int, int, str]] = []
    control_names: dict[tuple[str, str], list[tuple[int, str]]] = {}
    saw_main = 0
    saw_html = False
    saw_head = False
    has_title = False
    title_text = ""
    doc_like = False

    # A node index so a rule can ask "what is inside this element?"
    node_by_start = {n.tag.start: n for n in nodes}

    # Each open tag's enclosing element, found in ONE pass over the tags. The
    # open-element stack only ever loses a suffix, so the stack beneath any
    # element is exactly its chain of parents — walking the chain gives the
    # same answer the per-call rescan did, in O(depth) instead of O(tags).
    parent_of: dict[int, Tag | None] = {}
    open_stack: list[Tag] = []
    for other in tags:
        if other.closing:
            for i in range(len(open_stack) - 1, -1, -1):
                if open_stack[i].name == other.name:
                    del open_stack[i:]
                    break
            continue
        parent_of[other.start] = open_stack[-1] if open_stack else None
        if not (other.self_closing or other.name in VOID):
            open_stack.append(other)

    def ancestors_of(t: Tag) -> list[str]:
        """Enclosing element names, outermost first — good enough for the two
        questions that need it (is this header at page level, is this input
        wrapped in a label)."""
        out = []
        p = parent_of.get(t.start)
        while p is not None:
            out.append(p.name)
            p = parent_of.get(p.start)
        out.reverse()
        return out

    label_fors = ids_with_for(open_tags)     # the page's <label for=…> ids, once

    for t in open_tags:
        name = t.name
        a = t.attrs
        line = t.line
        node = node_by_start.get(t.start)
        inner = node.text if node else ""

        if name == "html":
            saw_html = True
            doc_like = True
        if name == "head":
            saw_head = True
            doc_like = True
        if name == "title":
            has_title = True
            title_text = inner

        # ---- K: positive tabindex ----------------------------------------
        ti = a.get("tabindex")
        if ti not in (None, EXPR):
            try:
                tival = int(str(ti).strip())
            except ValueError:
                tival = None
            if tival is not None and tival > 0:
                add(t.attr_lines.get("tabindex", line), "K", "positive-tabindex",
                    "2.4.3", "error",
                    f"`tabindex=\"{ti}\"` on <{name}>.",
                    "A positive tabindex creates a SECOND tab order that runs "
                    "before every tabindex=\"0\" element on the page, including "
                    "the browser's own controls. One positive value anywhere "
                    "means every other interactive element must also be "
                    "numbered, forever, in every future change. Use 0 to join "
                    "the natural order at the element's DOM position, or -1 for "
                    "a programmatic focus target. If the order is wrong, "
                    "reorder the DOM — that is the same fix 1.3.2 wants anyway.")

        # ---- R: aria attribute names and values --------------------------
        for attr, val in a.items():
            if not attr.startswith("aria-"):
                continue
            if attr in ARIA_DEPRECATED:
                add(t.attr_lines.get(attr, line), "R", "aria-deprecated",
                    "4.1.2", "warning",
                    f"`{attr}` is deprecated in ARIA 1.2.",
                    "Drag-and-drop ARIA was never implemented consistently and "
                    "is being removed. Use a real non-drag alternative (2.5.7) "
                    "and announce the result with a live region instead.")
                continue
            spec = ARIA_ATTRS.get(attr)
            if spec is None:
                close = _nearest(attr, ARIA_ATTRS)
                add(t.attr_lines.get(attr, line), "R", "aria-unknown-attr",
                    "4.1.2", "error",
                    f"`{attr}` is not an ARIA attribute"
                    + (f" — did you mean `{close}`?" if close else "."),
                    "An unrecognised aria-* attribute is not an error the "
                    "browser reports; it is simply ignored. The control ends up "
                    "with whatever name and state it would have had with no "
                    "ARIA at all, and the markup looks like the problem was "
                    "handled. `aria-labeledby` (one l) is the classic.")
                continue
            kind, allowed = spec
            if val == EXPR:
                continue                       # runtime value: cannot judge
            v = str(val).strip()
            if kind == "bool" and v.lower() not in ("true", "false"):
                add(t.attr_lines.get(attr, line), "R", "aria-bad-value",
                    "4.1.2", "error",
                    f"`{attr}=\"{v}\"` — expected `true` or `false`.",
                    "ARIA booleans are the literal strings \"true\" and "
                    "\"false\". An empty value, `yes`, `1` or the attribute's "
                    "mere presence do not work: the state resolves to its "
                    "default, so the control announces the opposite of what it "
                    "is doing.")
            elif kind in ("token",) and v.lower() not in allowed:
                add(t.attr_lines.get(attr, line), "R", "aria-bad-value",
                    "4.1.2", "error",
                    f"`{attr}=\"{v}\"` is not a valid value "
                    f"({', '.join(allowed)}).",
                    "An invalid token falls back to the attribute's default, "
                    "which is usually the opposite of what the author meant. "
                    "`aria-expanded=\"yes\"` announces \"collapsed\" while the "
                    "menu is open.")
            elif kind == "tokenlist" and v:
                bad = [p for p in v.split() if p.lower() not in allowed]
                if bad:
                    add(t.attr_lines.get(attr, line), "R", "aria-bad-value",
                        "4.1.2", "error",
                        f"`{attr}` contains invalid token(s): {', '.join(bad)}.",
                        f"Allowed: {', '.join(allowed)}.")
            elif kind in ("int", "number") and v:
                ok = re.fullmatch(r"-?\d+", v) if kind == "int" \
                    else re.fullmatch(r"-?\d*\.?\d+", v)
                if not ok:
                    add(t.attr_lines.get(attr, line), "R", "aria-bad-value",
                        "4.1.2", "error",
                        f"`{attr}=\"{v}\"` is not a{'n integer' if kind == 'int' else ' number'}.",
                        "A non-numeric value is dropped, so the control reports "
                        "no position or value at all.")
            elif kind in ("idref", "idrefs") and v and not dynamic_ids and ids:
                missing = [p for p in v.split() if p not in ids]
                if missing and (name.islower() or not is_jsx):
                    add(t.attr_lines.get(attr, line), "R", "aria-dangling-ref",
                        "1.3.1 / 4.1.2", "error",
                        f"`{attr}` points at id(s) that do not exist in this "
                        f"file: {', '.join(missing)}.",
                        "A reference to nothing is not an error the browser "
                        "reports — the relationship simply does not exist. An "
                        "aria-labelledby that resolves to nothing leaves the "
                        "control with NO accessible name while the markup looks "
                        "as though it has one, which is exactly the failure a "
                        "scanner is expected to catch and a reviewer is not. If "
                        "the target is rendered by another component, move the "
                        "reference so both ends live in one file.")

        # ---- R: role validity and redundancy ------------------------------
        role = a.get("role")
        if role not in (None, EXPR) and role.strip():
            first = role.split()[0].lower()
            if first not in VALID_ROLES:
                add(t.attr_lines.get("role", line), "R", "invalid-role",
                    "4.1.2", "error",
                    f"`role=\"{role}\"` is not an ARIA role.",
                    "An unknown role is ignored, so the element keeps (or "
                    "loses) whatever semantics it had. Check the spelling "
                    "against the ARIA roles list; `role=\"buttton\"` and "
                    "`role=\"nav\"` are the two that show up most.")
            else:
                implicit = IMPLICIT_ROLE.get(name)
                if name == "input":
                    implicit = INPUT_IMPLICIT_ROLE.get(
                        str(a.get("type", "text")).lower())
                if name == "a" and a.get("href") is not None:
                    implicit = "link"
                if name in ("ul", "ol") and first == "list":
                    implicit = None    # the deliberate Safari/VoiceOver hack
                if implicit and first == implicit:
                    add(t.attr_lines.get("role", line), "R", "redundant-role",
                        "4.1.2", "warning",
                        f"`<{name} role=\"{role}\">` restates the role the "
                        f"element already has.",
                        "Harmless today and a liability tomorrow: the next "
                        "person reads it as load-bearing and keeps it when the "
                        "element changes, at which point it is actively wrong. "
                        "It also trains a codebase to reach for ARIA before "
                        "HTML. Delete it. (The one legitimate exception is "
                        "`role=\"list\"` on a `<ul>` with `list-style: none`, "
                        "which Safari needs, and which this rule allows.)")

        # ---- K: aria-hidden / presentational over focusable content -------
        if str(a.get("aria-hidden", "")).lower() == "true" and node:
            focusables = [d for d in node.descendants
                          if d.tag.name in FOCUSABLE_SEL
                          and not (d.tag.name == "a" and d.tag.attrs.get("href") is None)
                          and "disabled" not in d.tag.attrs
                          or str(d.tag.attrs.get("tabindex", "")).strip() in ("0",)]
            if focusables:
                add(line, "K", "aria-hidden-focusable", "1.3.1 / 4.1.2", "error",
                    f"`aria-hidden=\"true\"` on <{name}> which contains "
                    f"{len(focusables)} focusable element(s).",
                    "aria-hidden removes the subtree from the accessibility "
                    "tree but NOT from the tab order. A keyboard user tabs into "
                    "a region a screen reader insists is not there, and lands "
                    "on a control with no name, no role and no announcement — a "
                    "trap with no exit message. If you are hiding a region, use "
                    "`inert`, which removes it from BOTH. Reserve aria-hidden "
                    "for non-focusable decoration inside a labelled control.")
        if str(a.get("role", "")).lower() in ("presentation", "none"):
            if name in FOCUSABLE_SEL or str(a.get("tabindex", "")).strip() == "0":
                add(line, "K", "presentation-on-focusable", "4.1.2", "error",
                    f"`role=\"{a.get('role')}\"` on a focusable <{name}>.",
                    "The element stays reachable by Tab and loses its "
                    "semantics, so focus lands on something assistive "
                    "technology cannot see or name. Either make it genuinely "
                    "non-focusable, or keep its role.")

        # ---- N: images ----------------------------------------------------
        if name == "img":
            alt = a.get("alt")
            if alt is None:
                if str(a.get("role", "")).lower() in ("presentation", "none") \
                        or "\x00spread" in a:
                    pass          # role handles it, or a spread may supply `alt`
                else:
                    add(line, "N", "img-no-alt", "1.1.1", "error",
                        f"<img> has no `alt` attribute"
                        + (f" (src={a['src']})" if a.get("src") not in (None, EXPR) else "") + ".",
                        "A MISSING alt and an EMPTY alt are different things. "
                        "With no attribute at all, screen readers fall back to "
                        "announcing the filename — `hero-final-v3-compressed` — "
                        "which is noise the user must sit through. Decorative? "
                        "`alt=\"\"`, attribute present. Informative? Describe "
                        "the information, not the composition. Inside a link or "
                        "button? Describe the destination or the action. The "
                        "decision tree is accessibility.md §9.")
            elif alt != EXPR:
                av = alt.strip()
                if av and ALT_FILENAME.match(av):
                    add(t.attr_lines.get("alt", line), "N", "alt-is-filename",
                        "1.1.1", "error",
                        f"`alt=\"{av}\"` is a filename.",
                        "This passes every scanner that only checks for the "
                        "attribute's presence, and conveys nothing. It is the "
                        "cleanest example of why a clean automated run is not "
                        "an accessible page: the machine can see that alt "
                        "EXISTS and cannot see that it is wrong.")
                elif av and ALT_PLACEHOLDER.match(av):
                    add(t.attr_lines.get("alt", line), "N", "alt-placeholder",
                        "1.1.1", "error",
                        f"`alt=\"{av}\"` is a placeholder, not a description.",
                        "Either the image carries information — describe it — "
                        "or it does not, in which case `alt=\"\"` is correct "
                        "and better, because it removes the image from the "
                        "screen reader's path entirely.")
                elif av and ALT_PREFIX_NOISE.match(av):
                    add(t.attr_lines.get("alt", line), "N", "alt-redundant-prefix",
                        "1.1.1", "warning",
                        f"`alt` starts with \"{av.split()[0]} {av.split()[1] if len(av.split()) > 1 else ''}\".",
                        "The role is already announced — a screen reader says "
                        "\"graphic\" before it reads the alt, so \"image of a "
                        "bar chart\" becomes \"graphic, image of a bar chart\". "
                        "Start with the content. Do name the medium when it IS "
                        "the point: \"Illustration of…\", \"Screenshot of…\", "
                        "\"Chart showing…\".")

        # ---- N / K: click handlers on non-interactive elements ------------
        click_attr = next((k for k in a if k in ("onclick", "onmousedown",
                                                 "onmouseup", "onpointerdown")), None)
        if click_attr and name in NON_INTERACTIVE:
            has_role = a.get("role") not in (None, EXPR) and str(a.get("role")).strip()
            ti_ok = str(a.get("tabindex", "")).strip() in ("0",) or a.get("tabindex") == EXPR
            has_key = any(k in a for k in ("onkeydown", "onkeyup", "onkeypress"))
            missing = []
            if not has_role:
                missing.append("a role")
            if not ti_ok:
                missing.append("tabindex=\"0\"")
            if not has_key:
                missing.append("a keyboard handler")
            sev = "error" if missing else "warning"
            add(line, "K", "handler-on-noninteractive", "2.1.1 / 4.1.2", sev,
                f"<{name}> has `{click_attr}` and is missing "
                f"{', '.join(missing) if missing else 'nothing — but it is still an imitation'}.",
                "ARIA adds no behaviour whatsoever: `role=\"button\"` does not "
                "make Enter work, and `tabindex=\"0\"` does not make the element "
                "announce a pressed state. A <button> arrives with a role, a "
                "name from its content, Enter AND Space activation (Space on "
                "keyup, Enter on keydown), a focus ring, a disabled state, form "
                "participation and correct forced-colors styling. Every one of "
                "those is a thing you now have to write and keep working. Use "
                "the element. If it must not look like a button, style the "
                "button — that is one line of CSS against an open-ended "
                "maintenance liability. NOTE: this is one of the traps axe "
                "cannot see; a div with role, tabindex and a keydown handler "
                "passes every scanner and can still be unreachable.")

        # ---- F: labels ----------------------------------------------------
        if name in ("input", "select", "textarea"):
            itype = str(a.get("type", "text")).lower() if name == "input" else name
            if itype not in INPUT_NO_LABEL_NEEDED:
                labelled = _labelled(t, label_fors, a, ancestors_of(t))
                if labelled is None and "\x00spread" not in a:
                    add(line, "F", "control-no-label", "3.3.2 / 4.1.2", "error",
                        f"<{name}"
                        + (f" type=\"{itype}\"" if name == "input" else "")
                        + "> has no label by any of the four mechanisms.",
                        "The four, in order of preference: `<label for=\"id\">` "
                        "(explicit, survives DOM moves, clickable, works "
                        "everywhere); a `<label>` wrapping the control; "
                        "`aria-labelledby` pointing at visible text that cannot "
                        "be a <label>; `aria-label` as a LAST resort, when no "
                        "visible text exists at all. Not `title` (a tooltip, "
                        "absent on touch and keyboard) and not `placeholder` — "
                        "a placeholder vanishes the moment the user types, so "
                        "they cannot check what the field was asking for, and "
                        "it fails 4.5:1 at nearly every design system's muted "
                        "grey.")
                elif labelled == "title":
                    add(line, "F", "label-by-title", "3.3.2", "warning",
                        f"<{name}> is named only by `title`.",
                        "`title` is a tooltip, not a label: it never appears on "
                        "touch, it does not appear on keyboard focus in most "
                        "browsers, and it is announced inconsistently across "
                        "screen readers. Promote it to a real <label>.")
                elif labelled == "placeholder":
                    add(line, "F", "placeholder-as-label", "3.3.2 / 1.4.3",
                        "error",
                        f"<{name}> is named only by `placeholder`.",
                        "The placeholder disappears when the user types, so a "
                        "person checking their own answer has nothing to check "
                        "it against — and anyone interrupted mid-form has to "
                        "clear the field to find out what it wanted. It also "
                        "fails 4.5:1 at every typical placeholder grey, is not "
                        "announced as a label by all assistive technology, and "
                        "breaks autofill. Add the label; usually you can then "
                        "delete the placeholder entirely.")

            # ---- F: autocomplete (SC 1.3.5) -------------------------------
            if name in ("input", "select") and itype not in INPUT_NOT_PERSONAL:
                hint = _personal_field(a)
                ac = a.get("autocomplete")
                if ac in (None,) and hint:
                    add(line, "F", "missing-autocomplete", "1.3.5", "error",
                        f"<{name} name=\"{a.get('name') or a.get('id') or '?'}\"> "
                        f"collects the user's own data and has no "
                        f"`autocomplete` (expected `{hint}`).",
                        "1.3.5 is an AA criterion and it is the one teams "
                        "discover during a procurement review. It also raises "
                        "completion rates and is half of what makes password "
                        "managers work (3.3.8). Add "
                        f"`autocomplete=\"{hint}\"`. Prefix address fields with "
                        "`shipping`/`billing` when a form has more than one "
                        "address.")
                elif ac not in (None, EXPR) and ac.strip():
                    bad = _bad_autocomplete(ac)
                    if bad:
                        add(t.attr_lines.get("autocomplete", line), "F",
                            "invalid-autocomplete", "1.3.5", "error",
                            f"`autocomplete=\"{ac}\"` — `{bad}` is not a valid "
                            f"token.",
                            "An invalid token is WORSE than no attribute: the "
                            "browser ignores the whole value, so autofill does "
                            "not work AND the criterion is not met, while the "
                            "markup looks as though it was handled. Check it "
                            "against the HTML autofill token list.")

        # ---- N: empty and vague controls ----------------------------------
        if name in ("button", "a") or (name == "input" and
                                       str(a.get("type", "")).lower() == "image"):
            named = _has_name(t, a, inner, node)
            is_link = name == "a" and a.get("href") is not None
            if not named:
                if (name == "a" and a.get("href") is None) or "\x00spread" in a:
                    pass          # anchor with no href is text; a spread may supply a name
                else:
                    add(line, "N", "empty-control", "4.1.2 / 2.4.4", "error",
                        f"<{name}> has no accessible name — no text, no "
                        f"`aria-label`, no labelled image inside it.",
                        "It is announced as \"button\" or \"link\" and nothing "
                        "else. Icon-only controls are where this lives: the "
                        "<svg> inside is decoration (`aria-hidden=\"true\" "
                        "focusable=\"false\"`) and the NAME belongs on the "
                        "control (`aria-label=\"Close\"`). If the control has "
                        "visible text, 2.5.3 requires the accessible name to "
                        "CONTAIN that text in the same order, or voice-control "
                        "users cannot activate what they can see.")
            elif is_link:
                txt = norm_text(inner) or norm_text(str(a.get("aria-label", "")))
                if txt in VAGUE_LINK_TEXT:
                    add(line, "N", "vague-link-text", "2.4.4", "warning",
                        f"Link text is \"{txt}\".",
                        "Screen reader users pull up a list of every link on "
                        "the page; three \"Read more\" rows in that list are "
                        "three identical, useless entries. Write the "
                        "destination into the link — \"Read the 2026 "
                        "accessibility report\". If the design demands \"Read "
                        "more\", extend the name with visually-hidden text "
                        "AFTER the visible words, which keeps 2.5.3 satisfied "
                        "because the name still starts with what is on screen.")
                elif BARE_URL.match(inner):
                    add(line, "N", "bare-url-link", "2.4.4", "warning",
                        "Link text is a bare URL.",
                        "A screen reader reads it character by character, "
                        "including the protocol and every slash. Use the "
                        "destination's name as the link text.")
            if named:
                key = ("link" if is_link else "button",
                       norm_text(str(a.get("aria-label", "")) if a.get("aria-label") not in (None, EXPR) else inner))
                if key[1]:
                    dest = str(a.get("href", "")) if is_link else ""
                    control_names.setdefault(key, []).append((line, dest))

        # ---- S: landmarks --------------------------------------------------
        if name == "main":
            saw_main += 1
        if name in LANDMARK_TAGS and name != "form":
            label = a.get("aria-label") or a.get("aria-labelledby")
            if name == "nav":
                nav_labels.append((str(label) if label else "", line))
            if label not in (None, EXPR) and label and \
                    re.search(r"\bnavigation\b|\bnav\b", str(label), re.I) and name == "nav":
                add(t.attr_lines.get("aria-label", line), "S", "landmark-label-noise",
                    "1.3.1", "warning",
                    f"`<nav aria-label=\"{label}\">` repeats the role in the label.",
                    "The role is already announced, so this reads as "
                    "\"primary navigation navigation\". Name what it is FOR: "
                    "\"Primary\", \"Footer\", \"Breadcrumb\", \"Docs sidebar\".")
        if name in ("header", "footer"):
            anc = ancestors_of(t)
            if not (set(anc) & SECTIONING):
                header_footer_top[name] = header_footer_top.get(name, 0) + 1

        # ---- S: zoom disabled ---------------------------------------------
        if name == "meta" and str(a.get("name", "")).lower() == "viewport":
            content = str(a.get("content", ""))
            if re.search(r"user-scalable\s*=\s*(no|0)", content, re.I) or \
               re.search(r"maximum-scale\s*=\s*(1(\.0+)?|0?\.\d+)\b", content, re.I):
                add(line, "S", "zoom-disabled", "1.4.4", "error",
                    "The viewport meta tag disables or caps pinch-zoom.",
                    "`user-scalable=no` and `maximum-scale=1` block the single "
                    "most-used accessibility feature on a phone. iOS Safari has "
                    "ignored them since iOS 10, which means this line does "
                    "nothing except break Android and announce that nobody "
                    "tested it. Delete everything after "
                    "`width=device-width, initial-scale=1`.")

        # ---- S: headings ---------------------------------------------------
        if name in HEADINGS:
            heading_seq.append((int(name[1]), line, inner))

    # ---- S: document-level ------------------------------------------------
    if saw_html:
        html_tag = next((t for t in open_tags if t.name == "html"), None)
        lang = html_tag.attrs.get("lang") if html_tag else None
        if lang is None:
            add(html_tag.line if html_tag else 1, "S", "no-lang", "3.1.1", "error",
                "<html> has no `lang` attribute.",
                "`lang` sets screen-reader pronunciation, hyphenation, quote "
                "marks and font fallback. English read by a French speech "
                "synthesiser is not accented — it is unintelligible. Use the "
                "right subtag (`en-GB`, `pt-BR`), and mark inline language "
                "changes with `<span lang=\"fr\">` (3.1.2).")
        elif lang not in (EXPR,) and not re.fullmatch(
                r"[A-Za-z]{2,3}(-[A-Za-z0-9]{2,8})*", str(lang).strip()):
            add(html_tag.attr_lines.get("lang", html_tag.line), "S", "bad-lang",
                "3.1.1", "error",
                f"`lang=\"{lang}\"` is not a valid BCP 47 language tag.",
                "An unparseable tag is ignored, so the page falls back to the "
                "user agent's language. `lang=\"english\"` and `lang=\"EN_US\"` "
                "are the two that appear; the correct forms are `en` and "
                "`en-US`.")

    if doc_like:
        if not has_title:
            add(1, "S", "no-title", "2.4.2", "error",
                "The document has no <title>.",
                "The title is the first thing a screen reader announces on "
                "load, the label in the tab strip, the bookmark name and the "
                "search result heading. Shape: \"Page — Section — Site\", most "
                "specific first, because a user with twenty tabs open sees "
                "about thirty characters.")
        elif not has_real_text(title_text):
            add(next((t.line for t in open_tags if t.name == "title"), 1),
                "S", "empty-title", "2.4.2", "error",
                "<title> is empty.",
                "Same effect as having none: the browser falls back to the URL, "
                "and the user hears a path. Give every route its own title, and "
                "update it on client-side navigation — a SPA that never changes "
                "the title tells a screen reader user nothing happened.")
        if saw_main == 0:
            add(1, "S", "no-main-landmark", "1.3.1 / 2.4.1", "error",
                "The document has no <main> landmark.",
                "Screen reader users jump straight to `main` more than they use "
                "any other landmark — it is how you skip a header you have "
                "already heard on nine pages. Exactly one per page, "
                "`<main id=\"main\" tabindex=\"-1\">` so the skip link can move "
                "focus into it rather than only scrolling to it.")
        elif saw_main > 1:
            add(next((t.line for t in open_tags if t.name == "main"), 1),
                "S", "multiple-main", "1.3.1", "error",
                f"{saw_main} <main> elements.",
                "There is one main region per page by definition. Two means the "
                "jump-to-main shortcut lands somewhere arbitrary.")
        for tag_name, count in header_footer_top.items():
            if count > 1:
                add(1, "S", "duplicate-landmark", "1.3.1", "warning",
                    f"{count} page-level <{tag_name}> elements "
                    f"(role {'banner' if tag_name == 'header' else 'contentinfo'}).",
                    "A page-level header/footer is a landmark; one inside "
                    "<article>, <aside>, <main>, <nav> or <section> is not. Two "
                    "of the same landmark with no distinguishing label are two "
                    "identical rows in the landmark list. Either nest them "
                    "inside a sectioning element or give each an `aria-label`.")

    if len(nav_labels) > 1:
        unlabelled = [ln for lbl, ln in nav_labels if not lbl or lbl == EXPR]
        labels = [lbl.lower() for lbl, _ in nav_labels if lbl and lbl != EXPR]
        if unlabelled:
            add(unlabelled[0], "S", "unlabelled-duplicate-landmark", "1.3.1",
                "error",
                f"{len(nav_labels)} <nav> landmarks, {len(unlabelled)} with no "
                f"accessible name.",
                "Every repeated landmark of the same type needs a "
                "distinguishing `aria-label`. Two entries both announced as "
                "\"navigation\" is a navigation failure — the user opens the "
                "landmark list precisely to choose between them. Do not put the "
                "word \"navigation\" in the label; the role already says it.")
        elif len(set(labels)) != len(labels):
            dup = [l for l in set(labels) if labels.count(l) > 1]
            add(nav_labels[0][1], "S", "duplicate-landmark-label", "1.3.1",
                "warning",
                f"Two <nav> landmarks share the label {', '.join(dup)}.",
                "Identical labels are the same problem as no labels.")

    # ---- S: heading outline ----------------------------------------------
    h1s = [(lvl, ln) for lvl, ln, _ in heading_seq if lvl == 1]
    if len(h1s) > 1:
        add(h1s[1][1], "S", "multiple-h1", "1.3.1 / 2.4.6", "error",
            f"{len(h1s)} <h1> elements (lines {', '.join(str(l) for _, l in h1s)}).",
            "The h1 is the page's subject and should roughly match the "
            "<title>. Two of them means the outline has two roots, and a user "
            "navigating by heading cannot tell which one the page is about. "
            "Choose the level by STRUCTURE, not by size — a visually small "
            "section heading that is structurally an h2 is "
            "`<h2 class=\"type-h4\">`.")
    prev = 0
    for lvl, ln, txt in heading_seq:
        if prev and lvl > prev + 1:
            add(ln, "S", "heading-skip", "1.3.1", "error",
                f"Heading level jumps h{prev} → h{lvl}"
                + (f" (\"{txt[:48]}\")" if txt else "") + ".",
                "A skipped level tells a screen reader user a section was lost "
                "and makes them stop to work out whether they missed something. "
                "Going back UP (h4 → h2) is fine and normal; only going down "
                "more than one step at a time is a defect. Read the outline on "
                "its own: it has to work as a table of contents.")
        prev = lvl
    if doc_like and heading_seq and heading_seq[0][0] != 1:
        add(heading_seq[0][1], "S", "no-h1", "1.3.1 / 2.4.6", "warning",
            f"The first heading is an h{heading_seq[0][0]}, not an h1.",
            "The outline has no root. If this file is a fragment rendered "
            "inside a page that supplies the h1, add an "
            "`a11y-audit-ignore-file: no-h1` pragma with that reason.")

    # ---- N: duplicate accessible names ------------------------------------
    for (kind, nm), sites in sorted(control_names.items()):
        if len(sites) < 2:
            continue
        dests = {d for _, d in sites}
        if kind == "link" and len(dests) == 1:
            continue                   # same name, same destination: correct
        add(sites[1][0], "N", "duplicate-name", "2.4.4 / 4.1.2", "warning",
            f"{len(sites)} {kind}s share the accessible name \"{nm}\" "
            f"(lines {', '.join(str(l) for l, _ in sites)})"
            + (" with different destinations." if kind == "link" else "."),
            "Two controls with one name are indistinguishable in the links or "
            "form-controls list, and voice control cannot address either — "
            "\"click Edit\" is ambiguous, so the user gets a disambiguation "
            "prompt or nothing. Name them by their object: \"Edit the report "
            "title\", \"Edit the summary\". The runtime pass computes real "
            "accessible names from the rendered tree and finds the ones this "
            "static approximation cannot; see scripts/a11y_runtime.mjs.")

    return findings


def ids_with_for(open_tags: list[Tag]) -> set:
    return {str(t.attrs.get("for")) for t in open_tags
            if t.name == "label" and t.attrs.get("for") not in (None, EXPR)}


def _labelled(t: Tag, label_fors: set, a: dict, ancestors: list) -> str | None:
    """Return the mechanism that names this control, or None."""
    if a.get("aria-labelledby") not in (None, "", EXPR) or a.get("aria-labelledby") == EXPR:
        return "aria-labelledby"
    if a.get("aria-label") not in (None, "") or a.get("aria-label") == EXPR:
        return "aria-label"
    ident = a.get("id")
    if ident == EXPR:
        return "aria-label"           # dynamic id: assume a matching label
    if ident and str(ident) in label_fors:
        return "label-for"
    if "label" in ancestors:
        return "label-wrap"
    if a.get("title") not in (None, ""):
        return "title"
    if a.get("placeholder") not in (None, ""):
        return "placeholder"
    return None


def _has_name(t: Tag, a: dict, inner: str, node) -> bool:
    if has_real_text(inner):
        return True
    for attr in ("aria-label", "aria-labelledby", "title", "value", "alt"):
        v = a.get(attr)
        if v == EXPR or (v is not None and str(v).strip()):
            return True
    if node:
        for d in node.descendants:
            da = d.tag.attrs
            if d.tag.name == "img" and str(da.get("alt", "")).strip():
                return True
            if d.tag.name == "svg" and str(da.get("aria-label", "")).strip():
                return True
            if str(da.get("aria-label", "")).strip() or str(da.get("title", "")).strip():
                return True
            if d.tag.name == "title":
                return True
    return False


def _personal_field(a: dict) -> str | None:
    """Does this field collect information ABOUT THE USER? (SC 1.3.5)"""
    itype = str(a.get("type", "")).lower()
    direct = {"email": "email", "tel": "tel", "url": "url", "password": "current-password"}
    haystack = " ".join(
        str(a.get(k, "")) for k in ("name", "id", "placeholder", "aria-label")
        if a.get(k) not in (None, EXPR)).lower()
    for pattern, token in PERSONAL_FIELD_HINTS:
        if re.search(pattern, haystack):
            return token
    if itype in direct:
        return direct[itype]
    return None


def _bad_autocomplete(value: str) -> str | None:
    parts = [p for p in str(value).strip().lower().split() if p]
    if not parts:
        return None
    for i, p in enumerate(parts):
        if p.startswith("section-"):
            continue
        if i < len(parts) - 1 and p in AUTOCOMPLETE_PREFIX:
            continue
        if p in AUTOCOMPLETE_TOKENS:
            continue
        return p
    return None


def _nearest(word: str, table) -> str | None:
    """Cheap edit-distance suggestion. `aria-labeledby` -> `aria-labelledby` is
    the single most common ARIA bug and it deserves to be named."""
    best, best_d = None, 99
    for cand in table:
        if abs(len(cand) - len(word)) > 2:
            continue
        d = _lev(word, cand)
        if d < best_d:
            best, best_d = cand, d
    return best if best_d <= 2 else None


def _lev(a: str, b: str) -> int:
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


# ---------------------------------------------------------------------------
# CSS audit — the focus indicator lives here, so the gate has to read CSS
# ---------------------------------------------------------------------------

OUTLINE_KILLED = re.compile(r"^(none|0|0px|0rem|hidden)$", re.I)
FOCUS_SEL = re.compile(r":focus(-visible|-within)?\b", re.I)


def audit_css(path: Path, text: str, origin: str | None = None,
              line_offset: int = 0) -> list[Finding]:
    findings: list[Finding] = []
    lines = (origin or text).splitlines()
    file_ignores, line_ignores = extract_pragmas(text)

    def add(line: int, cat: str, rule: str, sc: str, sev: str,
            msg: str, fix: str) -> None:
        tags = line_ignores.get(line, set()) | file_ignores
        if cat in tags or rule.upper() in tags or "ALL" in tags:
            return
        real = line + line_offset
        snippet = lines[real - 1].strip() if 0 < real <= len(lines) else ""
        findings.append(Finding(str(path), real, cat, rule, sc, sev, msg, fix,
                                snippet[:200]))

    src = re.sub(r"/\*.*?\*/", lambda m: " " * len(m.group(0)), text, flags=re.S)
    line_of = _line_finder(src)

    # Rule blocks: selector { declarations }. Nesting is rare in a focus rule
    # and a nested block simply audits as its own block, which is correct.
    depth = 0
    buf: list[str] = []
    sel = ""
    sel_line = 1
    body_start = 0
    i, n = 0, len(src)
    blocks: list[tuple[str, int, str, int]] = []
    while i < n:
        c = src[i]
        if c == "{":
            if depth == 0:
                sel = "".join(buf).strip()
                sel_line = line_of(i)
                body_start = i + 1
                buf = []
            depth += 1
            i += 1
            continue
        if c == "}":
            depth -= 1
            if depth == 0:
                blocks.append((sel, sel_line, src[body_start:i], body_start))
                buf = []
            i += 1
            continue
        if depth == 0:
            buf.append(c)
        i += 1

    for sel, sel_line, body, body_off in blocks:
        if sel.startswith("@") and "{" not in body:
            continue
        decls: dict[str, tuple[str, int]] = {}
        for m in re.finditer(r"([-\w]+)\s*:\s*([^;{}]+)", body):
            prop = m.group(1).strip().lower()
            val = m.group(2).strip()
            ln = line_of(body_off + m.start())
            decls[prop] = (val, ln)

        outline = decls.get("outline") or decls.get("outline-style") or \
            decls.get("outline-width")
        if outline and OUTLINE_KILLED.match(outline[0].split("!")[0].strip()):
            replacement = [p for p in ("box-shadow", "border", "border-color",
                                       "background", "background-color",
                                       "text-decoration", "outline-offset")
                           if p in decls and
                           not OUTLINE_KILLED.match(decls[p][0].split("!")[0].strip())]
            if not replacement:
                add(outline[1], "K", "outline-none-no-replacement", "2.4.7",
                    "error",
                    f"`{sel.strip()[:60]}` sets "
                    f"`outline: {outline[0].strip()}` and provides no "
                    f"replacement indicator.",
                    "This is the most common accessibility bug on the web. It "
                    "removes the only cursor a keyboard user has — not degraded, "
                    "unusable. And the fix is not to add an outline back at a "
                    "higher specificity somewhere else; the fix is to DELETE the "
                    "reset. If the default ring is ugly, restyle it as an "
                    "outline, which forced-colors mode keeps and no component "
                    "box-shadow can remove: `:focus-visible { outline: "
                    "var(--stroke-focus) solid var(--border-focus); "
                    "outline-offset: var(--stroke-focus); }`. If you genuinely want "
                    "no ring for MOUSE users, that is what `:focus-visible` "
                    "already does for you.")
            elif replacement == ["box-shadow"] and FOCUS_SEL.search(sel):
                add(decls["box-shadow"][1], "K", "focus-ring-shadow-only",
                    "1.4.11 / 2.4.7", "error",
                    f"`{sel.strip()[:60]}` replaces the outline with "
                    f"`box-shadow` alone.",
                    "In forced-colors mode (Windows High Contrast) box-shadow "
                    "is DISCARDED. A shadow-only ring does not degrade there — "
                    "it vanishes completely, and the user has no focus "
                    "indicator at all on any control on the page. Pair it with "
                    "a transparent outline, which is forced to a system colour "
                    "and becomes the visible ring: `outline: "
                    "var(--stroke-focus) solid transparent; outline-offset: "
                    "var(--stroke-focus); box-shadow: var(--shadow-focus);`. "
                    "That one line is the whole difference. See "
                    "references/token-contract.md, Accessibility floor.")
        # A focus rule that changes nothing visible at all.
        if FOCUS_SEL.search(sel) and decls and not any(
                p in decls for p in ("outline", "outline-color", "outline-style",
                                     "outline-width", "box-shadow", "border",
                                     "border-color", "background",
                                     "background-color", "color",
                                     "text-decoration", "filter", "transform")):
            add(sel_line, "K", "focus-rule-invisible", "2.4.7", "warning",
                f"`{sel.strip()[:60]}` is a focus rule that sets no visible "
                f"property.",
                "Whatever this is doing, it is not indicating focus. Either it "
                "is dead code or the indicator it was meant to draw was removed "
                "and nobody noticed — which is indistinguishable from source, "
                "and is exactly why the runtime pass measures the ring in "
                "pixels rather than reading the stylesheet.")
        if "transition" in decls and re.search(r"\boutline\b", decls["transition"][0]):
            add(decls["transition"][1], "K", "focus-ring-transition", "2.4.7",
                "warning",
                "The focus outline is transitioned.",
                "A ring that fades in is a ring that is not there when focus "
                "arrives, and with `prefers-reduced-motion` honoured it may not "
                "arrive at all. Transition colour if you must; never the "
                "indicator's existence.")

    return findings


STYLE_BLOCK = re.compile(r"<style\b[^>]*>(.*?)</style>", re.S | re.I)


def audit_embedded_css(path: Path, text: str) -> list[Finding]:
    out: list[Finding] = []
    for m in STYLE_BLOCK.finditer(text):
        offset = text.count("\n", 0, m.start(1))
        out.extend(audit_css(path, m.group(1), origin=text, line_offset=offset))
    return out


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

AUDITABLE_EXT = MARKUP_EXT | JSX_EXT | CSS_EXT


def iter_files(paths: list[str]) -> Iterator[Path]:
    for raw in paths:
        p = Path(raw)
        if p.is_file():
            yield p                  # named explicitly: audited or reported skipped
        elif p.is_dir():
            for root, dirs, files in os.walk(p):
                dirs[:] = [d for d in dirs
                           if d not in SKIP_DIRS and not d.startswith(".")]
                for f in sorted(files):
                    fp = Path(root) / f
                    if fp.suffix.lower() in AUDITABLE_EXT:
                        yield fp


def audit(paths: list[str]) -> list[Finding]:
    return audit_run(paths)[0]


def audit_run(paths: list[str]) -> tuple[list[Finding], list[Path]]:
    """(findings, files named explicitly that are not markup, JSX or CSS).

    A hook passes every staged file; README.md or render.py must be skipped
    and listed, not parsed as HTML and failed."""
    out: list[Finding] = []
    skipped: list[Path] = []
    for fp in iter_files(paths):
        if fp.suffix.lower() not in AUDITABLE_EXT:
            skipped.append(fp)
            continue
        try:
            text = fp.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if any(mark in text[:800] for mark in GENERATED_MARKERS):
            continue
        suffix = fp.suffix.lower()
        try:
            if suffix in CSS_EXT:
                out.extend(audit_css(fp, text))
            else:
                out.extend(audit_markup(fp, text, is_jsx=suffix in JSX_EXT))
                out.extend(audit_embedded_css(fp, text))
        except Exception as exc:     # a crashed rule must never block a commit
            out.append(Finding(str(fp), 1, "--", "internal-error", "--",
                               "warning",
                               f"a11y_static could not fully parse this file: {exc}",
                               "Please report this file shape; the rest of the "
                               "audit completed normally."))
    out.sort(key=lambda f: (f.file, f.line, SEVERITY_ORDER.get(f.severity, 9)))
    return out, skipped


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


COVERAGE_NOTE = (
    "This is the machine-checkable floor, not an accessibility result. In the "
    "only controlled study with a known denominator (GDS 2017, 143 planted "
    "failures, 10 tools) the best single tool found 37-41%. Run the runtime "
    "layer, then the manual protocol: references/manual-protocol.md."
)


def report(findings: list[Finding], *, use_color: bool, show_fix: bool) -> str:
    def c(code: str, s: str) -> str:
        return f"\033[{code}m{s}\033[0m" if use_color else s

    if not findings:
        return ("a11y static: clean — no source-level violations.\n"
                f"  {COVERAGE_NOTE}\n")

    buf: list[str] = []
    by_file: dict[str, list[Finding]] = {}
    for f in findings:
        by_file.setdefault(f.file, []).append(f)

    for file, items in by_file.items():
        buf.append(c("1", file))
        for f in items:
            tag = c("31", "error") if f.severity == "error" else c("33", "warn ")
            buf.append(f"  {f.line:>5}  {tag}  {c('36', f.category)} "
                       f"{f.rule:<28} {f.message}")
            if show_fix:
                buf.append(f"         {c('2', 'SC ' + f.sc)}")
                for ln in _wrap(f.fix, 88):
                    buf.append(f"         {c('2', ln)}")
        buf.append("")

    errors = sum(1 for f in findings if f.severity == "error")
    warns = len(findings) - errors
    buf.append(c("1", "Summary"))
    counts: dict[str, int] = {}
    for f in findings:
        counts[f.category] = counts.get(f.category, 0) + 1
    for cat in sorted(counts):
        buf.append(f"  {cat}  {CATEGORY_NAMES.get(cat, ''):<30} {counts[cat]}")
    buf.append(f"\n  {errors} error(s), {warns} warning(s) across "
               f"{len(by_file)} file(s).")
    buf.append("")
    for ln in _wrap(COVERAGE_NOTE, 88):
        buf.append(f"  {c('2', ln)}")
    return "\n".join(buf) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="python -m scripts.a11y_static",
        description="Layer one of the accessibility gate: source-level WCAG "
                    "checks, no browser, every commit.",
        epilog="A clean run means the cheapest class of error is absent. It "
               "does not mean the page is accessible — see "
               "references/automation-coverage.md.",
    )
    ap.add_argument("paths", nargs="*", default=["."],
                    help="files or directories to audit (default: .)")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--strict", action="store_true",
                    help="warnings fail the run too")
    ap.add_argument("--quiet", action="store_true",
                    help="suppress the fix guidance")
    ap.add_argument("--no-color", action="store_true")
    ap.add_argument("--baseline", metavar="FILE", default=".a11y-baseline.json",
                    help="ignore findings recorded in this file "
                         "(default: .a11y-baseline.json)")
    ap.add_argument("--write-baseline", metavar="FILE",
                    help="record current findings so only NEW ones fail")
    ap.add_argument("--category", action="append", metavar="S|N|K|R|F",
                    help="only report these categories (repeatable)")
    ap.add_argument("--sc", action="append", metavar="1.3.5",
                    help="only report findings for these success criteria "
                         "(repeatable)")
    args = ap.parse_args(argv)

    paths = args.paths or ["."]
    missing = [p for p in paths if not Path(p).exists()]
    if missing:
        print(f"a11y_static: no such path: {', '.join(missing)}", file=sys.stderr)
        return 2

    findings, skipped = audit_run(paths)
    if skipped:
        names = ", ".join(str(p) for p in skipped[:5]) + (" …" if len(skipped) > 5 else "")
        print(f"a11y_static: skipped {len(skipped)} file(s) that are not markup, JSX "
              f"or CSS: {names}", file=sys.stderr)

    if args.category:
        wanted = {c.upper() for c in args.category}
        findings = [f for f in findings if f.category in wanted]
    if args.sc:
        findings = [f for f in findings
                    if any(s in f.sc for s in args.sc)]

    if args.write_baseline:
        Path(args.write_baseline).write_text(
            json.dumps(sorted({f.key() for f in findings}), indent=2) + "\n",
            encoding="utf-8")
        print(f"a11y_static: recorded {len(findings)} finding(s) as the "
              f"baseline in {args.write_baseline}.\n"
              "Only NEW violations will fail from now on. Pay the debt down per "
              "directory, not all at once — and start with the categories a "
              "user feels first: F (labels), K (focus), N (names).")
        return 0

    baseline: set = set()
    bp = Path(args.baseline)
    if bp.exists():
        try:
            baseline = set(json.loads(bp.read_bytes()))
        except (OSError, json.JSONDecodeError):
            print(f"a11y_static: could not read baseline {bp}; auditing "
                  f"everything.", file=sys.stderr)
    if baseline:
        findings = [f for f in findings if f.key() not in baseline]

    if args.json:
        print(json.dumps({
            "tool": "a11y_static",
            "coverage_note": COVERAGE_NOTE,
            "errors": sum(1 for f in findings if f.severity == "error"),
            "warnings": sum(1 for f in findings if f.severity == "warning"),
            "findings": [asdict(f) for f in findings],
        }, indent=2))
    else:
        use_color = not args.no_color and sys.stdout.isatty()
        sys.stdout.write(report(findings, use_color=use_color,
                                show_fix=not args.quiet))

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
