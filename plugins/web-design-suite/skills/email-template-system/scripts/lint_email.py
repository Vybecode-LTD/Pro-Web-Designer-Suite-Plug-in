#!/usr/bin/env python3
"""lint_email.py — the gate for a built email. Run it on the COMPILED file.

`audit_design.py` gates the website. This gates the email, and it checks different
things, because email fails differently: a rule that is merely inelegant on the web
is invisible to a third of readers in an inbox.

Every check here traces to a row in references/email-client-matrix.md. Nothing is
flagged on taste. If the linter objects, a named client drops the thing on the floor.

WHAT IT CHECKS
--------------
  tokens      any `var(--…)` that survived the build — the compiler failed or was skipped
  css         properties no client in the matrix supports (flex, grid, position, …)
  structure   layout tables without role="presentation"; forms, script, iframe, video
  images      missing alt, missing explicit width/height, missing dimensions in style
  head        lang, <title>, charset, viewport, preheader, the MSO PixelsPerInch block,
              and the MSO font rule when a stack starts with a font Windows lacks
  links       relative URLs, non-descriptive link text, a missing unsubscribe link
  size        total bytes against Gmail's 102,400-byte clipping threshold, and the
              16,384-byte ceiling on surviving <style> content
  contrast    every element that sets a colour, measured against its nearest
              resolvable background, at the WCAG 2.2 AA thresholds
  dark        the same measure with the retained prefers-color-scheme: dark rules
              applied, as a client that honours them renders the email
  type        text below the 13px email floor
  nostyle     an inline width wider than a 375px phone, which is all that is left
              where a client strips <style>

SOURCE TEMPLATES (--source)
---------------------------
  source      on the template BEFORE the build: a var() of a dropped token (an
              error that names the token to use), a var() of no token, a var()
              fallback, a hand-written colour (an error: Law 1), and a length or
              weight literal, with the tokens that hold the same value

USAGE
-----
  python -m scripts.lint_email build/receipt.html
  python -m scripts.lint_email build/receipt.html --transactional
  python -m scripts.lint_email build/*.html --format json -o lint.json
  python -m scripts.lint_email build/receipt.html --strict     # warnings fail too
  python -m scripts.lint_email build/receipt.html --ignore contrast,link-text
  python -m scripts.lint_email assets/templates/receipt.html --source

Exit codes: 0 clean (or warnings only) · 1 at least one error (or, with --strict,
at least one warning) · 2 bad invocation or an unreadable file.

CI: `python -m scripts.lint_email build/*.html --format report` is the whole gate.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

# Importing the compiler must not leave a __pycache__ in the plugin.
sys.dont_write_bytecode = True
# The compiler's CSS parser and selector matcher, so the dark pass reaches the
# elements the build's own cascade would (DL-B6).
try:                                              # python -m scripts.lint_email
    from .build_email import (VAR_RE, TokenError, compile_selector, default_tokens_path,
                              dropped_message, load_dropped, load_tokens, parse_declarations,
                              parse_stylesheet)
except ImportError:                               # python scripts/lint_email.py
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from build_email import (VAR_RE, TokenError, compile_selector,  # type: ignore[no-redef]
                             default_tokens_path, dropped_message, load_dropped, load_tokens,
                             parse_declarations, parse_stylesheet)

GMAIL_CLIP_BYTES = 102_400
GMAIL_STYLE_BYTES = 16_384
EMAIL_MIN_FONT_PX = 13
# The phone width the no-<style> check holds inline widths to (DL-A12).
PHONE_PX = 375
COLOR_LITERAL_RE = re.compile(r"#[0-9a-fA-F]{3,8}\b|\b(?:rgba?|hsla?|hwb|lab|lch|oklab|oklch)\(")
LENGTH_LITERAL_RE = re.compile(r"(?<![\w.#-])(\d*\.?\d+)(px|em|rem)\b")
DARK_RE = re.compile(r"prefers-color-scheme\s*:\s*dark", re.I)

VOID_TAGS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link",
    "meta", "param", "source", "track", "wbr",
}

# Properties no client worth supporting honours, mapped to who drops them and what
# to use instead. Sourced from references/email-client-matrix.md §2.
UNSUPPORTED_PROPS = {
    "display": {
        "flex": ("classic Outlook for Windows (Word engine) and the Gmail app with a non-Google "
                 "account; Gmail also drops flex-direction everywhere",
                 "table cells, or an inline-block fluid-hybrid column"),
        "inline-flex": ("same as display:flex", "inline-block"),
        "grid": ("classic Outlook for Windows (Word engine) and the Gmail app with a non-Google "
                 "account",
                 "table cells"),
        "inline-grid": ("same as display:grid", "table cells"),
    },
    "position": (None, "Gmail strips it entirely; the Word engine has no support",
                 "normal table flow — there is nothing to position against"),
    "float": (None, "the Word engine honours it inconsistently and never unsets it",
              "table cells, or align on the <td>"),
    "gap": (None, "no client in the matrix supports it",
            "cell padding and spacer rows — see email-architecture.md §3"),
    "row-gap": (None, "no client in the matrix supports it", "spacer rows"),
    "column-gap": (None, "no client in the matrix supports it", "a gutter cell"),
    "box-shadow": (None, "the Word engine ignores it; several clients flatten it",
                   "a 1px border (--email-edge)"),
    "text-shadow": (None, "the Word engine ignores it", "nothing"),
    "transform": (None, "Gmail strips it; the Word engine has no support", "nothing"),
    "transition": (None, "no state changes survive", "nothing"),
    "animation": (None, "Gmail strips it; only WebKit clients would run it", "a static frame"),
    "filter": (None, "Gmail strips it", "a pre-processed image"),
    "object-fit": (None, "unsupported in the Word engine and Gmail",
                   "crop the image at build time"),
    "flex-direction": (None, "meaningless without flex", "table rows"),
    "justify-content": (None, "meaningless without flex", "align on the <td>"),
    "align-items": (None, "meaningless without flex", "valign on the <td>"),
    "grid-template-columns": (None, "meaningless without grid", "table cells"),
}

# Properties that work but only in some clients — worth knowing, never fatal.
PARTIAL_PROPS = {
    "border-radius": "square corners in Outlook Windows (Word engine). Fine as "
                     "degradation; use VML if the shape is load-bearing.",
    "max-width": "ignored by the Word engine, which is why the ghost table exists.",
    "background-image": "the Word engine needs VML; Gmail with a non-Google account "
                        "may not show it at all. Always set a background-color too.",
    "background-size": "not supported in Gmail. Use the `background` shorthand.",
    "letter-spacing": "ignored by the Word engine. Harmless.",
    "min-height": "Yahoo rewrites `height` to `min-height`; do not rely on either.",
    "opacity": "unreliable outside WebKit clients.",
    "width": None,  # handled separately, never flagged
}

WEAK_LINK_TEXT = {
    "click here", "here", "read more", "more", "learn more", "link", "this",
    "this link", "click", "go", "see more", "details", "continue", "download",
    "read", "view", "shop", "info", "find out more",
}

NAMED_COLORS = {
    "white": "#ffffff", "black": "#000000", "red": "#ff0000", "blue": "#0000ff",
    "green": "#008000", "gray": "#808080", "grey": "#808080", "silver": "#c0c0c0",
    "navy": "#000080", "teal": "#008080", "olive": "#808000", "lime": "#00ff00",
    "aqua": "#00ffff", "fuchsia": "#ff00ff", "maroon": "#800000", "purple": "#800080",
    "yellow": "#ffff00", "orange": "#ffa500", "transparent": None, "inherit": None,
}


# ---------------------------------------------------------------------------
# DOM
# ---------------------------------------------------------------------------


class Node:
    __slots__ = ("kind", "tag", "attrs", "children", "parent", "data", "line")

    def __init__(self, kind, tag="", data="", line=0):
        self.kind = kind
        self.tag = tag
        self.attrs: dict[str, str] = {}
        self.children: list[Node] = []
        self.parent: Node | None = None
        self.data = data
        self.line = line

    def get(self, name, default=None):
        return self.attrs.get(name, default)

    @property
    def classes(self) -> list[str]:
        return (self.attrs.get("class") or "").split()

    def walk(self):
        yield self
        for child in self.children:
            yield from child.walk()

    def elements(self):
        for node in self.walk():
            if node.kind == "element":
                yield node

    def text_content(self) -> str:
        return "".join(n.data for n in self.walk() if n.kind == "text")

    def ancestors(self):
        node = self.parent
        while node is not None:
            yield node
            node = node.parent


class DomParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("element", "#document")
        self.stack = [self.root]

    def _append(self, node):
        node.parent = self.stack[-1]
        self.stack[-1].children.append(node)

    def handle_starttag(self, tag, attrs):
        node = Node("element", tag, line=self.getpos()[0])
        for key, value in attrs:
            node.attrs[key] = value if value is not None else ""
        self._append(node)
        if tag not in VOID_TAGS:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        node = Node("element", tag, line=self.getpos()[0])
        for key, value in attrs:
            node.attrs[key] = value if value is not None else ""
        self._append(node)

    def handle_endtag(self, tag):
        for depth in range(len(self.stack) - 1, 0, -1):
            if self.stack[depth].tag == tag:
                del self.stack[depth:]
                return

    def handle_data(self, data):
        self._append(Node("text", data=data, line=self.getpos()[0]))

    def handle_comment(self, data):
        self._append(Node("comment", data=data, line=self.getpos()[0]))


# ---------------------------------------------------------------------------
# Colour & contrast
# ---------------------------------------------------------------------------


def parse_color(value: str) -> tuple[int, int, int] | None:
    if not value:
        return None
    value = value.strip().lower()
    if value in NAMED_COLORS:
        mapped = NAMED_COLORS[value]
        return parse_color(mapped) if mapped else None
    m = re.fullmatch(r"#([0-9a-f]{3})", value)
    if m:
        d = m.group(1)
        return tuple(int(c * 2, 16) for c in d)  # type: ignore[return-value]
    m = re.fullmatch(r"#([0-9a-f]{6})", value)
    if m:
        d = m.group(1)
        return tuple(int(d[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]
    m = re.fullmatch(r"#([0-9a-f]{8})", value)
    if m:
        d = m.group(1)
        return tuple(int(d[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]
    m = re.match(r"rgba?\(\s*([0-9.]+)[\s,]+([0-9.]+)[\s,]+([0-9.]+)", value)
    if m:
        return tuple(max(0, min(255, int(float(g)))) for g in m.groups())  # type: ignore[return-value]
    return None


def relative_luminance(rgb) -> float:
    channels = []
    for raw in rgb:
        c = raw / 255
        channels.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def contrast_ratio(fg, bg) -> float:
    lf, lb = relative_luminance(fg), relative_luminance(bg)
    hi, lo = max(lf, lb), min(lf, lb)
    return (hi + 0.05) / (lo + 0.05)


def is_preheader(node) -> bool:
    if node.get("data-preheader") is not None:
        return True
    style = (node.get("style") or "").replace(" ", "").lower()
    return "display:none" in style and ("max-height:0" in style or "opacity:0" in style)


def declarations(style: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for piece in style.split(";"):
        if ":" not in piece:
            continue
        prop, _, value = piece.partition(":")
        out[prop.strip().lower()] = re.sub(r"!\s*important\s*$", "", value.strip(), flags=re.I).strip()
    return out


# Families classic Outlook's Word engine finds on Windows, and the generics.
# Windows maps Helvetica to Arial.
WINDOWS_FAMILIES = {
    "arial", "helvetica", "georgia", "times new roman", "times", "verdana", "tahoma",
    "trebuchet ms", "courier new", "courier", "segoe ui", "calibri", "cambria",
    "sans-serif", "serif", "monospace", "inherit",
}


def first_family(stack: str) -> str:
    """The first family in a font-family value, unquoted and lower-cased."""
    first = re.sub(r"!\s*important\s*$", "", stack, flags=re.I).split(",")[0]
    return first.strip().strip("'\"").strip().lower()


# The token names a literal in each property could come from: a 26px font
# size is not "held" by a 26px line height.
TOKEN_FAMILIES = (
    (("font-size",), ("-size",)),
    (("line-height",), ("-line",)),
    (("font-weight",), ("-weight",)),
    (("letter-spacing",), ("--tracking",)),
    (("border-radius",), ("--radius",)),
    (("border",), ("--stroke", "--email-edge")),
    (("padding", "margin", "gap"), ("--space-", "--gap-", "--pad-", "--gutter-")),
    (("width", "max-width", "min-width", "height", "max-height", "min-height"),
     ("--email-width", "--space-", "--gap-", "--gutter-", "--email-tap")),
)


def token_family(prop: str) -> tuple[str, ...]:
    for props, parts in TOKEN_FAMILIES:
        if prop in props or any(prop.startswith(p + "-") for p in props):
            if prop.startswith("border") and "radius" in prop:
                continue
            return parts
    return ()


def px(value: str) -> float | None:
    if not value:
        return None
    m = re.match(r"\s*(-?[0-9.]+)\s*px\s*$", value)
    return float(m.group(1)) if m else None


# ---------------------------------------------------------------------------
# Findings
# ---------------------------------------------------------------------------


class Finding:
    __slots__ = ("severity", "check", "message", "line", "detail", "fix")

    def __init__(self, severity, check, message, line=0, detail="", fix=""):
        self.severity = severity  # "error" | "warning" | "info"
        self.check = check
        self.message = message
        self.line = line
        self.detail = detail
        self.fix = fix

    def as_dict(self):
        return {
            "severity": self.severity, "check": self.check, "message": self.message,
            "line": self.line, "detail": self.detail, "fix": self.fix,
        }


class Linter:
    def __init__(self, source: str, path: str, transactional: bool = False,
                 tokens: dict[str, str] | None = None, dropped: dict | None = None,
                 roles: set[str] | None = None):
        self.source = source
        self.path = path
        self.transactional = transactional
        # Given only for --source: the token file the build would resolve
        # against, its dropped map, and its Tier-2 role names.
        self.tokens = tokens
        self.dropped = dropped or {}
        self.roles = roles or set()
        parser = DomParser()
        parser.feed(source)
        parser.close()
        self.root = parser.root
        self.findings: list[Finding] = []

    def add(self, severity, check, message, line=0, detail="", fix=""):
        self.findings.append(Finding(severity, check, message, line, detail, fix))

    # -- checks -------------------------------------------------------------

    def check_tokens(self):
        for match in re.finditer(r"var\(\s*(--[A-Za-z0-9_-]+)", self.source):
            line = self.source.count("\n", 0, match.start()) + 1
            self.add(
                "error", "tokens",
                "unresolved token %s" % match.group(1), line,
                "No email client resolves CSS custom properties reliably: Outlook, "
                "Yahoo, Samsung and Thunderbird have no support at all, and Gmail "
                "supports var() only for values it never lets you declare.",
                "run build_email.py on the SOURCE template, or add the token to "
                "assets/email-tokens.json",
            )

    def check_css(self):
        for node in self.root.elements():
            style = node.get("style")
            if not style:
                continue
            decls = declarations(style)
            for prop, value in decls.items():
                entry = UNSUPPORTED_PROPS.get(prop)
                if entry is None:
                    continue
                if isinstance(entry, dict):
                    hit = entry.get(value.split()[0] if value else "")
                    if hit is None:
                        continue
                    who, fix = hit
                    self.add("error", "css", "%s:%s is unsupported" % (prop, value),
                             node.line, "dropped by %s" % who, "use %s" % fix)
                else:
                    _, who, fix = entry
                    self.add("error", "css", "%s is unsupported" % prop, node.line,
                             who, "use %s" % fix)

        # The same sweep over whatever <style> content survived.
        for node in self.root.elements():
            if node.tag != "style":
                continue
            css = node.text_content()
            for prop in UNSUPPORTED_PROPS:
                entry = UNSUPPORTED_PROPS[prop]
                for match in re.finditer(r"(?<![\w-])%s\s*:\s*([^;}]+)" % re.escape(prop), css):
                    value = match.group(1).strip()
                    if isinstance(entry, dict):
                        if value.split()[0] not in entry:
                            continue
                        who, fix = entry[value.split()[0]]
                    else:
                        _, who, fix = entry
                    self.add("error", "css",
                             "%s:%s in the retained <style> block" % (prop, value),
                             node.line, who, "use %s" % fix)

        for node in self.root.elements():
            style = node.get("style") or ""
            if is_preheader(node):
                continue  # its opacity:0 / max-width:0 are the technique, not a risk
            decls = declarations(style)
            for prop, note in PARTIAL_PROPS.items():
                if note and prop in decls:
                    self.add("info", "css-partial", "%s is only partially supported" % prop,
                             node.line, note)

    def check_structure(self):
        for node in self.root.elements():
            if node.tag == "table":
                role = (node.get("role") or "").lower()
                has_header = any(
                    d.tag in ("th", "caption") for d in node.walk() if d.kind == "element"
                )
                if role == "presentation":
                    continue
                if role in ("table", "grid") or has_header:
                    if role not in ("table", "grid"):
                        self.add("warning", "structure",
                                 "<table> has <th>/<caption> but no role", node.line,
                                 "If it is a real data table, say so with role=\"table\"; "
                                 "if it is layout, remove the <th> and add "
                                 "role=\"presentation\".")
                    continue
                self.add("error", "structure", "layout <table> without role=\"presentation\"",
                         node.line,
                         "A screen reader in an email client announces every layout table "
                         "as a table with N rows and N columns, and a nested email skeleton "
                         "is four of them. role=\"presentation\" removes the table semantics "
                         "and nothing else.",
                         'add role="presentation"')

            if node.tag in ("form", "input", "button", "select", "textarea"):
                self.add("error", "structure", "<%s> in an email" % node.tag, node.line,
                         "Forms are stripped by most clients and treated as a phishing "
                         "signal by the rest.",
                         "link to a page that hosts the form")
            if node.tag in ("script", "iframe", "object", "embed"):
                self.add("error", "structure", "<%s> in an email" % node.tag, node.line,
                         "Stripped universally, and a strong spam signal.", "remove it")
            if node.tag == "video":
                self.add("warning", "structure", "<video> in an email", node.line,
                         "Plays only in Apple Mail and a few WebKit clients. Everywhere "
                         "else the fallback is what renders — so the fallback is the design.",
                         "use a poster image linking to the hosted video")
            if node.tag == "svg":
                self.add("warning", "structure", "<svg> in an email", node.line,
                         "Blocked in Gmail and Outlook; renders in Apple Mail. Never "
                         "acceptable for a logo.",
                         "export a PNG at 2x")

    def check_images(self):
        for node in self.root.elements():
            if node.tag != "img":
                continue
            decls = declarations(node.get("style") or "")
            if "alt" not in node.attrs:
                self.add("error", "images", "<img> has no alt attribute", node.line,
                         "Images are blocked by default in several clients and on many "
                         "corporate gateways. Without alt, a blocked image is a silent "
                         "hole where the message was.",
                         'add alt="…" carrying the meaning, or alt="" if purely decorative')
            elif not (node.get("alt") or "").strip():
                src = node.get("src") or ""
                if not re.search(r"spacer|pixel|shim|track|1x1|open", src, re.I):
                    self.add("info", "images", "<img> has alt=\"\" (decorative)", node.line,
                             "Correct only if the image adds nothing a reader would miss.")

            if not node.get("width") or not node.get("height"):
                self.add("error", "images",
                         "<img> is missing an explicit width/height attribute", node.line,
                         "The Word engine sizes images from the HTML attributes, not from "
                         "CSS. Without them a 1200px retina source renders at 1200px and "
                         "blows the 600px column apart.",
                         "set width and height attributes to the DISPLAY size")

            if "width" not in decls:
                self.add("warning", "images", "<img> has no width in its style", node.line,
                         "Needed alongside the attribute for the clients that scale.",
                         "add width:NNNpx or width:100%;max-width:NNNpx")

            if decls.get("display") != "block":
                self.add("warning", "images", "<img> is not display:block", node.line,
                         "Inline images sit on the text baseline, and several clients add "
                         "3-5px of phantom space under them. It is the most common "
                         "'why is there a gap below my image' cause.",
                         "add display:block")

    def check_head(self):
        html = next((n for n in self.root.elements() if n.tag == "html"), None)
        if html is None:
            self.add("error", "head", "no <html> element")
        elif not (html.get("lang") or "").strip():
            self.add("error", "head", "<html> has no lang attribute", html.line if html else 0,
                     "A screen reader picks a pronunciation engine from it. With no lang "
                     "it uses the system default, which reads English copy in the user's "
                     "own language's phonemes.",
                     'add lang="en" (or the real language)')

        title = next((n for n in self.root.elements() if n.tag == "title"), None)
        if title is None or not title.text_content().strip():
            self.add("error", "head", "no <title>, or an empty one",
                     title.line if title else 0,
                     "It is the accessible name of the document and what several webmail "
                     "'view in browser' pages use as the page title.",
                     "add a <title> that restates the subject line")

        has_charset = any(
            n.tag == "meta" and ((n.get("charset")) or
                                 (n.get("http-equiv") or "").lower() == "content-type")
            for n in self.root.elements()
        )
        if not has_charset:
            self.add("error", "head", "no charset declaration",
                     detail="Without it a client guesses, and a smart quote becomes â€™.",
                     fix='add <meta charset="utf-8">')

        has_viewport = any(
            n.tag == "meta" and (n.get("name") or "").lower() == "viewport"
            for n in self.root.elements()
        )
        if not has_viewport:
            self.add("warning", "head", "no viewport meta",
                     detail="Android clients will zoom the email out to fit a 600px "
                            "layout on a 360px screen.",
                     fix='add <meta name="viewport" content="width=device-width, '
                         'initial-scale=1">')

        has_mso = any(
            n.kind == "comment" and "PixelsPerInch" in n.data for n in self.root.walk()
        )
        if not has_mso:
            self.add("warning", "head", "no <o:PixelsPerInch> block",
                     detail="On a Windows machine at 125% display scaling, the Word engine "
                            "scales some values and not others. The result is 20% larger "
                            "text in a container that did not grow.",
                     fix="build with build_email.py, or paste the mso conditional from "
                         "references/email-architecture.md §2")

        # DL-A11: the Word engine cannot resolve a first family Windows lacks
        # (-apple-system, a web font) and lands on its default serif, unless
        # an [if mso] block sets a font it has.
        mso_font = any(
            n.kind == "comment" and re.match(r"\s*\[if\s+mso", n.data, re.I)
            and "font-family" in n.data for n in self.root.walk()
        )
        if not mso_font:
            stacks = [declarations(n.get("style") or "").get("font-family", "")
                      for n in self.root.elements()]
            stacks += [m.group(1) for n in self.root.elements() if n.tag == "style"
                       for m in re.finditer(r"font-family\s*:\s*([^;}]+)", n.text_content())]
            missing = sorted({first for first in (first_family(s) for s in stacks)
                              if first and first not in WINDOWS_FAMILIES
                              and not first.startswith("var(")})
            if missing:
                self.add("warning", "head", "no MSO font rule, and a stack starts with %s"
                         % ", ".join(missing),
                         detail="Classic Outlook's Word engine cannot resolve that family "
                                "and lands on its own default serif "
                                "(references/email-architecture.md §2).",
                         fix="build with build_email.py, which adds the [if mso] font rule, "
                             "or paste it from references/email-architecture.md §2")

        # Use the same test check_css() uses to exempt the preheader's hiding
        # declarations (is_preheader): that one also accepts opacity:0 without
        # max-height:0, and a node missed here but caught there produced a
        # false "no preheader found" for a preheader check_css already knew about.
        preheader = next((node for node in self.root.elements() if is_preheader(node)), None)
        if preheader is None:
            self.add("error", "head", "no preheader found",
                     detail="The inbox list shows the subject and then the first text in "
                            "the body. With no preheader that is your logo's alt text, or "
                            "'View in browser', on every client, for every reader.",
                     fix="add a hidden preheader div as the first thing in <body>; see "
                         "references/email-workflow.md §3")
        else:
            text = " ".join(preheader.text_content().split())
            visible = re.sub(r"[‌ \s]", "", text)
            if len(visible) < 15:
                self.add("warning", "head", "preheader is very short (%d chars)" % len(visible),
                         preheader.line,
                         "Most clients show 35-100 characters. Under ~40 you are leaving "
                         "the rest of the line to whatever follows in the body.")
            elif len(visible) > 140:
                self.add("info", "head", "preheader is %d characters" % len(visible),
                         preheader.line, "Everything past ~100 is invisible in every client.")

    def check_links(self):
        seen_unsubscribe = False
        for node in self.root.elements():
            if node.tag != "a":
                continue
            href = (node.get("href") or "").strip()
            label = " ".join(node.text_content().split())

            if not href:
                self.add("error", "links", "<a> with no href", node.line,
                         fix="remove the anchor or give it a destination")
                continue

            if re.search(r"unsubscribe|optout|opt-out|list-unsub", href, re.I) or \
               re.search(r"unsubscribe|opt out", label, re.I):
                seen_unsubscribe = True

            if not re.match(r"^(https?:|mailto:|tel:|sms:|\{\{|\{%|\*\||%%|#)", href, re.I):
                self.add("error", "links", "relative URL: %s" % href[:60], node.line,
                         "An email has no base URL. A relative href resolves against the "
                         "webmail client's own domain, which is a 404 at best.",
                         "use an absolute https:// URL")
            elif href.lower().startswith("http://"):
                self.add("warning", "links", "plain http:// URL: %s" % href[:60], node.line,
                         "Mixed content in a webmail client, and a mild spam signal.",
                         "use https://")

            if label and label.lower().strip(" .!:>»→»") in WEAK_LINK_TEXT:
                # An error by the suite's choice. SC 2.4.4 (Level A) lets the
                # surrounding sentence explain a link; the rule for a link read out
                # of context is 2.4.9 (Link Only), Level AAA. Email readers list
                # links out of context all the time, so this skill holds 2.4.9.
                self.add("error", "link-text", 'link text is "%s"' % label, node.line,
                         "A screen reader user can pull up a list of every link in the "
                         "message with no surrounding text. Six links all called 'Read "
                         "more' is a list of six identical rows. SC 2.4.9 (Link Only), "
                         "Level AAA, which this skill holds as its floor for email.",
                         "say where it goes: 'Read the full breakdown'")
            if not label and not any(
                d.tag == "img" for d in node.walk() if d.kind == "element"
            ):
                self.add("error", "link-text", "link has no text and no image", node.line,
                         fix="give it a label")

        for node in self.root.elements():
            if node.tag != "img":
                continue
            if node.parent is not None and node.parent.tag == "a":
                if not (node.get("alt") or "").strip():
                    self.add("error", "link-text",
                             "linked image with an empty alt — the link has no name",
                             node.line,
                             "A link whose only content is an image with alt=\"\" is "
                             "announced as its URL.",
                             "put the link's destination in the alt text")

        if not seen_unsubscribe:
            severity = "info" if self.transactional else "error"
            self.add(severity, "links", "no unsubscribe link found",
                     detail="Required by CAN-SPAM for commercial email and by GDPR/PECR "
                            "for consent-based sending; Gmail and Yahoo bulk-sender rules "
                            "additionally expect one-click unsubscribe on marketing mail. "
                            "Transactional mail (receipts, password resets) is exempt from "
                            "both the body link and the one-click headers (Google's sender "
                            "FAQ: 'Transactional messages are excluded').",
                     fix="add an unsubscribe link, or pass --transactional if this really "
                         "is a receipt/password reset")

    def check_size(self):
        total = len(self.source.encode("utf-8"))
        pct = total / GMAIL_CLIP_BYTES * 100
        if total > GMAIL_CLIP_BYTES:
            self.add("error", "size",
                     "%s bytes exceeds Gmail's %s-byte clipping threshold (%.0f%%)"
                     % (f"{total:,}", f"{GMAIL_CLIP_BYTES:,}", pct),
                     detail="Gmail truncates the HTML part and hides the remainder behind "
                            "a 'View entire message' link. Everything past the cut — "
                            "usually the footer, the unsubscribe link and the tracking "
                            "pixel — does not render, and the open never registers.",
                     fix="drop base64 images, collapse repeated inline styles, shorten "
                         "the <style> block, or build with --minify")
        elif pct > 90:
            self.add("warning", "size", "%s bytes is %.0f%% of the clipping threshold"
                     % (f"{total:,}", pct),
                     detail="ESP link-tracking rewrites and merge-tag expansion add bytes "
                            "AFTER you hand this over. Measure the delivered message, not "
                            "the template.",
                     fix="leave headroom: aim under 90 KB pre-send")

        style_bytes = sum(
            len(m.group(1).encode("utf-8"))
            for m in re.finditer(r"<style[^>]*>(.*?)</style>", self.source, re.S | re.I)
        )
        if style_bytes > GMAIL_STYLE_BYTES:
            self.add("error", "size",
                     "<style> content is %s bytes in total; Gmail removes every <style> "
                     "element that crosses %s bytes, counting all of them together, and "
                     "every element after it" % (f"{style_bytes:,}", f"{GMAIL_STYLE_BYTES:,}"),
                     detail="One block over the ceiling loses ALL of its CSS, not just the "
                            "end (hteumeuleu/email-bugs#90). Several smaller blocks, most "
                            "important first, lose only the tail: build_email.py splits the "
                            "retained CSS that way past the ceiling.",
                     fix="inline more of it; only media queries and pseudo-classes need "
                         "to stay")

    def check_contrast(self):
        for node in self.root.elements():
            decls = declarations(node.get("style") or "")
            color = decls.get("color") or node.get("color")
            if not color:
                continue
            fg = parse_color(color)
            if fg is None:
                continue
            if not " ".join(node.text_content().split()):
                continue

            bg, source_tag = self.resolve_background(node)
            if bg is None:
                continue

            size, bold, required = self.text_size(node, decls)
            ratio = contrast_ratio(fg, bg)

            if ratio < required:
                self.add("error", "contrast",
                         "%s on %s is %.2f:1, needs %.1f:1"
                         % (color, source_tag, ratio, required),
                         node.line,
                         "%.0fpx%s text. WCAG 2.2 SC 1.4.3. Email is read on phones in "
                         "sunlight more than any other medium, so the floor is a floor."
                         % (size, " bold" if bold else ""),
                         "darken the foreground or lighten the background; the token file "
                         "records the measured ratio for every role pair")
            elif ratio < required + 0.6:
                self.add("info", "contrast",
                         "%s on %s is %.2f:1 — just over the %.1f:1 floor"
                         % (color, source_tag, ratio, required), node.line,
                         "Dark-mode colour inversion in Gmail iOS and Outlook can move "
                         "this either way. No headroom means no margin for that.")

    def text_size(self, node, decls) -> tuple[float, bool, float]:
        """The size, the boldness and the WCAG floor for this element's text."""
        size = px(decls.get("font-size", "")) or self.inherited_font_size(node) or 16.0
        weight_raw = decls.get("font-weight", "") or self.inherited_weight(node)
        bold = weight_raw in ("bold", "bolder") or (
            weight_raw.isdigit() and int(weight_raw) >= 700
        )
        large = size >= 24 or (bold and size >= 18.66)
        return size, bold, 3.0 if large else 4.5

    def dark_rules(self) -> list:
        """(compiled selector, rule) for each retained rule under
        `prefers-color-scheme: dark` whose selector the compiler can match."""
        found = []
        for node in self.root.elements():
            if node.tag != "style":
                continue
            for rule in parse_stylesheet(node.text_content()):
                if not rule.at_rule or not DARK_RE.search(rule.at_rule):
                    continue
                for selector in rule.selectors:
                    compiled = compile_selector(selector)
                    if compiled is not None:
                        found.append((compiled, rule))
        return found

    def check_dark(self):
        """DL-A10, DL-B6: apply the retained dark rules as a client that honours
        prefers-color-scheme does, by the cascade build_email inlines with, and
        measure the contrast again. Only what the dark rules change is measured:
        the rest is the light pass's."""
        rules = self.dark_rules()
        if not rules:
            return
        cache: dict[int, dict[str, str]] = {}

        def dark(node) -> dict[str, str]:
            if id(node) not in cache:
                bucket = [((3 if d.important else 1, 9, 9, 9, 10**9), d.prop, d.value)
                          for d in parse_declarations(node.get("style") or "")]
                for compiled, rule in rules:
                    if compiled.matches(node):
                        for d in rule.declarations:
                            rank = (2 if d.important else 0,) + compiled.specificity + (rule.order,)
                            bucket.append((rank, d.prop, d.value))
                bucket.sort(key=lambda item: item[0])
                final: dict[str, str] = {}
                for _rank, prop, value in bucket:
                    if prop == "background":
                        prop, value = "background-color", (value.split() or [""])[0]
                    final[prop] = value
                cache[id(node)] = final
            return cache[id(node)]

        def dark_background(node):
            for current in [node, *node.ancestors()]:
                if current.kind != "element" or current.tag == "#document":
                    continue
                raw = dark(current).get("background-color")
                color = parse_color(raw) if raw else None
                if color:
                    return color, raw
                raw = current.get("bgcolor")
                color = parse_color(raw) if raw else None
                if color:
                    return color, raw
            return None, ""

        for node in self.root.elements():
            if node.tag in ("#document", "style", "head", "title"):
                continue
            color = dark(node).get("color") or node.get("color")
            fg = parse_color(color) if color else None
            if fg is None or not " ".join(node.text_content().split()):
                continue
            bg, source = dark_background(node)
            if bg is None:
                continue
            light = declarations(node.get("style") or "").get("color") or node.get("color")
            if (parse_color(light) if light else None, self.resolve_background(node)[0]) == (fg, bg):
                continue
            size, bold, required = self.text_size(node, declarations(node.get("style") or ""))
            ratio = contrast_ratio(fg, bg)
            if ratio < required:
                self.add("error", "dark",
                         "in dark mode, %s on %s is %.2f:1, needs %.1f:1"
                         % (color, source, ratio, required),
                         node.line,
                         "%.0fpx%s <%s>%s. Clients that honour prefers-color-scheme apply "
                         "the retained dark block (email-client-matrix.md), and an "
                         "!important rule there beats the inline colour."
                         % (size, " bold" if bold else "", node.tag,
                            " class=\"%s\"" % node.get("class") if node.get("class") else ""),
                         "re-point this element's colour in the dark block; a class rule "
                         "beats an element rule such as `a`")

    def resolve_background(self, node) -> tuple[tuple[int, int, int] | None, str]:
        for current in [node, *node.ancestors()]:
            if current.kind != "element":
                continue
            decls = declarations(current.get("style") or "")
            for key in ("background-color", "background"):
                raw = decls.get(key)
                if raw:
                    color = parse_color(raw.split()[0]) if raw else None
                    if color:
                        return color, raw.split()[0]
            bgcolor = current.get("bgcolor")
            if bgcolor:
                color = parse_color(bgcolor)
                if color:
                    return color, bgcolor
        return None, ""

    def inherited_font_size(self, node) -> float | None:
        for current in node.ancestors():
            if current.kind != "element":
                continue
            size = px(declarations(current.get("style") or "").get("font-size", ""))
            if size:
                return size
        return None

    def inherited_weight(self, node) -> str:
        for current in [node, *node.ancestors()]:
            if current.kind != "element":
                continue
            if current.tag in ("b", "strong", "h1", "h2", "h3", "h4", "h5", "h6"):
                return "700"
            weight = declarations(current.get("style") or "").get("font-weight", "")
            if weight:
                return weight
        return ""

    def check_type(self):
        for node in self.root.elements():
            decls = declarations(node.get("style") or "")
            size = px(decls.get("font-size", ""))
            if size is None:
                continue
            text = " ".join(node.text_content().split())
            if size < EMAIL_MIN_FONT_PX and text and len(re.sub(r"[‌ ]", "", text)) > 3:
                style = (node.get("style") or "").replace(" ", "").lower()
                if "display:none" in style or "max-height:0" in style:
                    continue  # the preheader, legitimately 1px
                self.add("warning", "type", "font-size:%gpx is below the %dpx email floor"
                         % (size, EMAIL_MIN_FONT_PX), node.line,
                         "iOS Mail auto-enlarges text under about 13px and does it per "
                         "element, so one small legal line drags its container out of "
                         "alignment with everything beside it.",
                         "use --type-legal-size (13px) as the smallest real text")

    def check_nostyle(self):
        """DL-A12, DL-B6: where a client strips <style> (Gmail's app with a
        non-Google account), only inline widths are left. One wider than a
        phone, and not capped by a max-width that fits, overflows the screen."""
        for node in self.root.elements():
            if node.tag in ("#document", "html", "head", "body") or is_preheader(node):
                continue
            decls = declarations(node.get("style") or "")
            if "width" in decls:
                width = px(decls["width"])
            else:
                attr = (node.get("width") or "").strip()
                width = float(attr) if re.fullmatch(r"\d+(\.\d+)?", attr) else None
            if width is None or width <= PHONE_PX:
                continue
            cap = decls.get("max-width", "")
            if cap.endswith("%") or (px(cap) is not None and px(cap) <= PHONE_PX):
                continue
            self.add("error", "nostyle",
                     "<%s> is %gpx wide with no <style>, on a %dpx phone"
                     % (node.tag, width, PHONE_PX), node.line,
                     "Gmail's app with a non-Google account removes <style>, so the "
                     "media query that narrows this never arrives.",
                     "inline width:100% with a max-width cap, and keep the fixed width "
                     "in the [if mso] ghost table (references/email-architecture.md)")

    def source_declarations(self):
        """(line, where, prop, value) for every declaration a source template
        writes: inline styles, and the rules of each <style> block."""
        for node in self.root.elements():
            if node.tag == "style":
                for rule in parse_stylesheet(node.text_content()):
                    where = "`%s`" % ", ".join(rule.selectors) if rule.selectors else "an at-rule"
                    for d in rule.declarations:
                        yield node.line, where, d.prop, d.value
            elif node.get("style") and not is_preheader(node):
                for d in parse_declarations(node.get("style")):
                    if node.tag == "img" and d.prop in ("width", "height"):
                        continue          # an image's own size, mirrored from its attributes
                    yield node.line, "<%s>" % node.tag, d.prop, d.value

    def check_source(self):
        """DL-A13, DL-C5: Law 1 on the source, before the build turns every
        token into a literal and nothing can tell them apart."""
        tokens = self.tokens or {}
        by_value: dict[str, list[str]] = {}
        for name, value in tokens.items():
            by_value.setdefault(value.strip().lower(), []).append(name)
        for line, where, prop, value in self.source_declarations():
            for m in VAR_RE.finditer(value):
                name, fallback = m.group(1), m.group(2)
                if name in self.dropped and name not in tokens:
                    self.add("error", "source", dropped_message(name, self.dropped[name]),
                             line, "in %s %s" % (where, prop),
                             "the build refuses it, fallback or not")
                elif name not in tokens and fallback is None:
                    self.add("error", "source", "var(%s) is not a token" % name, line,
                             "in %s %s; the build stops on it" % (where, prop),
                             "use a role from assets/email-tokens.json")
                elif name not in tokens:
                    self.add("warning", "source",
                             "var(%s, %s): not a token, so the email ships the fallback"
                             % (name, fallback.strip()), line, "in %s %s" % (where, prop),
                             "use a token, or add one to assets/email-tokens.json")
                elif fallback is not None:
                    self.add("warning", "source",
                             "var(%s, %s): the fallback never applies" % (name, fallback.strip()),
                             line, "in %s %s" % (where, prop),
                             "drop it: it only waits to hide a renamed token")
            bare = VAR_RE.sub("", value)
            if COLOR_LITERAL_RE.search(bare):
                self.add("error", "source", "a hand-written colour, %s: %s" % (prop, bare.strip()),
                         line, "in %s. Law 1: the token file is the source of truth." % where,
                         "use a role token")
            literals = ["%s%s" % (n, unit) for n, unit in LENGTH_LITERAL_RE.findall(bare)
                        if float(n) != 0]
            if prop == "font-weight" and re.fullmatch(r"\s*\d+\s*", bare):
                literals.append(bare.strip())
            for literal in literals:
                family = token_family(prop)
                holders = [n for n in by_value.get(literal.lower(), [])
                           if n in self.roles and any(part in n for part in family)]
                if holders:
                    self.add("warning", "source", "%s: %s is a literal" % (prop, literal), line,
                             "in %s; %s hold%s it" % (where, ", ".join(sorted(holders)[:3]),
                                                      "s" if len(holders) == 1 else ""),
                             "use var(%s)" % sorted(holders)[0])
                else:
                    self.add("warning", "source", "%s: %s is off the scale" % (prop, literal),
                             line, "in %s; no %s role token holds it"
                             % (where, prop if family else "matching"),
                             "use the nearest role token, or add the value to the token file")

    def run(self) -> list[Finding]:
        if self.tokens is not None:
            self.check_source()
            return self.sorted_findings()
        self.check_tokens()
        self.check_css()
        self.check_structure()
        self.check_images()
        self.check_head()
        self.check_links()
        self.check_size()
        self.check_contrast()
        self.check_dark()
        self.check_type()
        self.check_nostyle()
        return self.sorted_findings()

    def sorted_findings(self) -> list[Finding]:
        rank = {"error": 0, "warning": 1, "info": 2}
        self.findings.sort(key=lambda f: (rank[f.severity], f.check, f.line))
        return self.findings


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

SYMBOL = {"error": "ERROR  ", "warning": "WARN   ", "info": "note   "}


def render_report(path: str, findings: list[Finding], verbose: bool) -> str:
    lines = ["", path, "=" * len(path)]
    counts = {"error": 0, "warning": 0, "info": 0}
    for finding in findings:
        counts[finding.severity] += 1

    if not findings:
        lines.append("clean — no findings.")
        lines.append("")
        return "\n".join(lines)

    seen: set[tuple] = set()
    for finding in findings:
        key = (finding.severity, finding.check, finding.message)
        if key in seen and not verbose:
            continue
        seen.add(key)
        where = "line %d" % finding.line if finding.line else "-"
        lines.append("%s[%s] %s  (%s)" % (SYMBOL[finding.severity], finding.check,
                                          finding.message, where))
        if finding.detail:
            for wrapped in wrap_text(finding.detail, 76):
                lines.append("         %s" % wrapped)
        if finding.fix:
            for i, wrapped in enumerate(wrap_text(finding.fix, 70)):
                lines.append("         %s %s" % ("fix:" if i == 0 else "    ", wrapped))
        lines.append("")

    hidden = len(findings) - len(seen)
    if hidden > 0 and not verbose:
        lines.append("(%d repeated finding(s) collapsed; --verbose to list every one)" % hidden)
    lines.append("%d error(s), %d warning(s), %d note(s)"
                 % (counts["error"], counts["warning"], counts["info"]))
    lines.append("")
    return "\n".join(lines)


def wrap_text(text: str, width: int) -> list[str]:
    words = text.split()
    if not words:
        return []
    out, current = [], words[0]
    for word in words[1:]:
        if len(current) + 1 + len(word) <= width:
            current += " " + word
        else:
            out.append(current)
            current = word
    out.append(current)
    return out


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m scripts.lint_email",
        description="Gate a BUILT email against what actually renders in the clients "
                    "that matter.",
    )
    parser.add_argument("files", nargs="+", help="compiled email HTML file(s), or source "
                                                 "templates with --source")
    parser.add_argument("--source", action="store_true",
                        help="lint source templates for Law 1: literals, var() fallbacks, "
                             "dropped tokens")
    parser.add_argument("--tokens", help="token file for --source "
                                         "(default: assets/email-tokens.json)")
    parser.add_argument("--format", choices=("report", "json"), default="report")
    parser.add_argument("-o", "--out", help="write output here instead of stdout")
    parser.add_argument("--transactional", action="store_true",
                        help="this is a receipt/reset/alert: demote the unsubscribe check")
    parser.add_argument("--strict", action="store_true", help="warnings fail the build too")
    parser.add_argument("--ignore", default="",
                        help="comma-separated check names to silence "
                             "(tokens,css,css-partial,structure,images,head,links,"
                             "link-text,size,contrast,dark,type,nostyle,source)")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="list every occurrence instead of collapsing repeats")
    args = parser.parse_args(argv)

    ignored = {name.strip() for name in args.ignore.split(",") if name.strip()}
    tokens = dropped = roles = None
    if args.source:
        tokens_path = Path(args.tokens) if args.tokens else default_tokens_path()
        try:
            tokens = load_tokens(tokens_path)
        except TokenError as exc:
            print("error: %s" % exc, file=sys.stderr)
            return 2
        dropped = load_dropped(tokens_path)
        raw = json.loads(tokens_path.read_bytes()).get("tokens", {})
        roles = {n for n, e in raw.items() if isinstance(e, dict) and e.get("tier") == 2}
    results: dict[str, list[Finding]] = {}
    exit_code = 0

    for name in args.files:
        path = Path(name)
        try:
            source = path.read_text(encoding="utf-8")
        except OSError as exc:
            print("error: cannot read %s: %s" % (path, exc), file=sys.stderr)
            return 2
        findings = [
            f for f in Linter(source, str(path), args.transactional, tokens, dropped, roles).run()
            if f.check not in ignored
        ]
        results[str(path)] = findings
        if any(f.severity == "error" for f in findings):
            exit_code = 1
        elif args.strict and any(f.severity == "warning" for f in findings):
            exit_code = 1

    if args.format == "json":
        payload = {
            "clip_threshold_bytes": GMAIL_CLIP_BYTES,
            "style_threshold_bytes": GMAIL_STYLE_BYTES,
            "files": {
                name: {
                    "errors": sum(1 for f in items if f.severity == "error"),
                    "warnings": sum(1 for f in items if f.severity == "warning"),
                    "notes": sum(1 for f in items if f.severity == "info"),
                    "findings": [f.as_dict() for f in items],
                }
                for name, items in results.items()
            },
        }
        text = json.dumps(payload, indent=2) + "\n"
    else:
        text = "".join(render_report(n, f, args.verbose) for n, f in results.items())

    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)

    return exit_code


if __name__ == "__main__":
    # A Windows pipe (git hook, CI, `> file`) defaults to the ANSI code page,
    # where printing →, Δ or ✓ raises UnicodeEncodeError. Consoles and
    # Claude Code already use UTF-8 and are left alone.
    for _stream in (sys.stdout, sys.stderr):
        if getattr(_stream, "encoding", "utf-8").lower() not in ("utf-8", "utf8"):
            _stream.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
