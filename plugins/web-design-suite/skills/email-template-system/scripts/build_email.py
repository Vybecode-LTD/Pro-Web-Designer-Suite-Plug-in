#!/usr/bin/env python3
"""build_email.py — compile a token-authored source template into sendable email HTML.

The premise of this skill in one line: **the token file is the source of truth and
email is a compile target.** You author a template against the same Tier-2 roles the
website uses (`var(--fg-default)`, `var(--pad-card)`), in a readable `<style>` block
with classes, and this script resolves the tokens to literal values, inlines every
rule that can be inlined onto the elements themselves, and leaves behind only the
rules that must survive as CSS (media queries, dark-mode overrides, pseudo-classes).

Law 1 (tokens or nothing) and Law 4 (one home) are not abandoned in email. They move
from runtime to build time. No human hand-writes an inline style or a hex; a tool does.

WHAT IT DOES, IN ORDER
----------------------
  1. Load `assets/email-tokens.json` and flatten it to name -> literal value,
     resolving token-to-token references recursively.
  2. Substitute every `var(--name)` / `var(--name, fallback)` in the whole document —
     `<style>` blocks (including `@media` preludes), `style` attributes, presentational
     attributes (`bgcolor`, `width`, `align`) and MSO conditional-comment bodies.
  3. Parse the `<style>` blocks into rules. Each rule is either INLINABLE (a plain
     element/class/id/descendant/child selector, no at-rule context, no pseudo) or
     RETAINED (everything else).
  4. Inline the inlinable declarations onto matching elements with real cascade
     ordering: normal declarations sort by specificity then source order, an existing
     `style` attribute beats all normal stylesheet rules, and `!important` inverts
     the whole thing.
  5. Re-emit the retained rules in one `<style>` block in `<head>`.
  6. Inject the MSO scaffolding — the `v:`/`o:` namespaces on `<html>` and the
     `<o:PixelsPerInch>96</o:PixelsPerInch>` block that defuses Outlook's 120-DPI
     scaling — unless the source already has them or `--no-mso` is passed.
  7. Generate the plain-text alternative from the DOM, not from a regex over tags.
  8. Report the final byte size against Gmail's clipping threshold (102,400 bytes =
     100 KiB of HTML part; see references/email-client-matrix.md §7).

USAGE
-----
  # Compile one template next to its source
  python -m scripts.build_email assets/templates/transactional-receipt.html \\
      --tokens assets/email-tokens.json --out build/receipt.html

  # Write the plain-text part too (it is a deliverable, not an afterthought)
  python -m scripts.build_email assets/templates/newsletter.html \\
      --out build/newsletter.html --text build/newsletter.txt

  # Just the text part, to read it before you ship it
  python -m scripts.build_email assets/templates/newsletter.html --text-only

  # Squeeze bytes when you are near the clipping threshold
  python -m scripts.build_email assets/templates/newsletter.html \\
      --out build/newsletter.html --minify

  # Resolve tokens but leave the CSS in the <style> block, for eyeballing the
  # cascade before you commit to inlining it
  python -m scripts.build_email src.html --out /tmp/debug.html --no-inline

Run it by path from the PROJECT root, so templates and build/ are the project's:
`python <skill>/scripts/build_email.py emails/receipt.html --out build/receipt.html`.
`--tokens` defaults to the skill's own `assets/email-tokens.json` either way.

Exit codes: 0 compiled · 1 compiled but over the clipping threshold (or, with
--strict, any warning) · 2 bad invocation, unreadable input, or unresolved tokens.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable

GMAIL_CLIP_BYTES = 102_400  # 100 KiB. Verified figure — see the matrix reference.
GMAIL_STYLE_BYTES = 16_384  # Gmail drops <style> content past this.

VOID_TAGS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link",
    "meta", "param", "source", "track", "wbr",
}

# Elements whose text never belongs in the plain-text part.
TEXT_SKIP_TAGS = {"style", "script", "head", "title", "meta", "link"}

# Block-ish elements that force a line break in the plain-text part.
# `td`/`th` are deliberately NOT here: a receipt row is one line of text, not two.
# They get a soft separator instead, and the `tr` closes the line.
TEXT_BLOCK_TAGS = {
    "address", "article", "aside", "blockquote", "div", "dl", "dd", "dt",
    "fieldset", "figure", "footer", "form", "h1", "h2", "h3", "h4", "h5",
    "h6", "header", "hr", "li", "main", "nav", "ol", "p", "pre", "section",
    "table", "tr", "ul",
}

# Comments worth keeping in a sent email. Everything else is bytes the reader
# never sees, counted against Gmail's clipping threshold. Conditional comments are
# load-bearing markup; ESP directives are how merge logic is expressed in several
# platforms; authoring notes are not.
COMMENT_KEEP_RE = re.compile(
    r"\[if\b|<!\[endif\]|mc:|\*\||\{\{|\{%|<%|\bhtmlmin:", re.I
)


# ---------------------------------------------------------------------------
# A minimal, faithful DOM
# ---------------------------------------------------------------------------
#
# Why not an off-the-shelf parser: stdlib only, and email templates need byte-level
# fidelity around conditional comments. `html.parser` hands us comments intact, which
# is exactly what `<!--[if mso]>…<![endif]-->` needs. The one subtlety is the
# downlevel-revealed form `<!--[if !mso]><!-- -->`, which html.parser splits into a
# comment whose data ends in `<!--` plus ordinary markup. Re-emitting `<!--` + data +
# `-->` round-trips it byte for byte, which is all we need.


class Node:
    __slots__ = ("kind", "tag", "attrs", "children", "parent", "data", "self_closed")

    def __init__(self, kind: str, tag: str = "", data: str = "") -> None:
        self.kind = kind  # "element" | "text" | "comment" | "decl" | "pi"
        self.tag = tag
        self.attrs: list[list[str | None]] = []  # [name, value|None], order preserved
        self.children: list[Node] = []
        self.parent: Node | None = None
        self.data = data
        self.self_closed = False

    # -- attribute helpers --------------------------------------------------
    def get(self, name: str) -> str | None:
        for pair in self.attrs:
            if pair[0] == name:
                return pair[1]
        return None

    def set(self, name: str, value: str) -> None:
        for pair in self.attrs:
            if pair[0] == name:
                pair[1] = value
                return
        self.attrs.append([name, value])

    def has(self, name: str) -> bool:
        return any(p[0] == name for p in self.attrs)

    @property
    def classes(self) -> list[str]:
        return (self.get("class") or "").split()

    def walk(self) -> Iterable["Node"]:
        yield self
        for child in self.children:
            yield from child.walk()

    def elements(self) -> Iterable["Node"]:
        for node in self.walk():
            if node.kind == "element":
                yield node

    def find(self, tag: str) -> "Node | None":
        for node in self.elements():
            if node.tag == tag:
                return node
        return None

    def text_content(self) -> str:
        out = []
        for node in self.walk():
            if node.kind == "text":
                out.append(node.data)
        return "".join(out)


class DomParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.root = Node("element", "#document")
        self.stack = [self.root]

    # -- helpers ------------------------------------------------------------
    def _append(self, node: Node) -> None:
        node.parent = self.stack[-1]
        self.stack[-1].children.append(node)

    def handle_starttag(self, tag, attrs):
        node = Node("element", tag)
        node.attrs = [[k, v] for k, v in attrs]
        self._append(node)
        if tag not in VOID_TAGS:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        node = Node("element", tag)
        node.attrs = [[k, v] for k, v in attrs]
        node.self_closed = True
        self._append(node)

    def handle_endtag(self, tag):
        for depth in range(len(self.stack) - 1, 0, -1):
            if self.stack[depth].tag == tag:
                del self.stack[depth:]
                return
        # Stray close tag: ignore it rather than corrupting the tree.

    def handle_data(self, data):
        self._append(Node("text", data=data))

    def handle_entityref(self, name):
        self._append(Node("text", data="&%s;" % name))

    def handle_charref(self, name):
        self._append(Node("text", data="&#%s;" % name))

    def handle_comment(self, data):
        self._append(Node("comment", data=data))

    def handle_decl(self, decl):
        self._append(Node("decl", data=decl))

    def handle_pi(self, data):
        self._append(Node("pi", data=data))

    def unknown_decl(self, data):
        self._append(Node("decl", data=data))


def parse_html(source: str) -> Node:
    parser = DomParser()
    parser.feed(source)
    parser.close()
    return parser.root


def escape_attr(value: str) -> str:
    return value.replace("&", "&amp;").replace('"', "&quot;")


def serialize(node: Node) -> str:
    out: list[str] = []
    _serialize_into(node, out)
    return "".join(out)


def _serialize_into(node: Node, out: list[str]) -> None:
    if node.kind == "text":
        out.append(node.data)
        return
    if node.kind == "comment":
        out.append("<!--%s-->" % node.data)
        return
    if node.kind == "decl":
        out.append("<!%s>" % node.data)
        return
    if node.kind == "pi":
        out.append("<?%s>" % node.data)
        return
    if node.tag == "#document":
        for child in node.children:
            _serialize_into(child, out)
        return

    out.append("<" + node.tag)
    for name, value in node.attrs:
        if value is None:
            out.append(" " + name)
        else:
            out.append(' %s="%s"' % (name, escape_attr(value)))
    if node.tag in VOID_TAGS:
        out.append(">")
        return
    if node.self_closed and not node.children:
        out.append("/>")
        return
    out.append(">")
    for child in node.children:
        _serialize_into(child, out)
    out.append("</%s>" % node.tag)


# ---------------------------------------------------------------------------
# Tokens
# ---------------------------------------------------------------------------

VAR_RE = re.compile(r"var\(\s*(--[A-Za-z0-9_-]+)\s*(?:,([^()]*|[^()]*\([^()]*\)[^()]*))?\)")


class TokenError(Exception):
    pass


def load_tokens(path: Path) -> dict[str, str]:
    """Flatten email-tokens.json into name -> literal, resolving token references."""
    try:
        data = json.loads(path.read_bytes())
    except FileNotFoundError:
        raise TokenError("token file not found: %s" % path)
    except json.JSONDecodeError as exc:
        raise TokenError("token file is not valid JSON (%s): %s" % (path, exc))

    raw = data.get("tokens")
    if not isinstance(raw, dict):
        raise TokenError('%s has no "tokens" object' % path)

    flat: dict[str, str] = {}
    for name, entry in raw.items():
        if isinstance(entry, dict):
            if "value" not in entry:
                raise TokenError('token %s has no "value"' % name)
            flat[name] = str(entry["value"])
        else:
            flat[name] = str(entry)

    # Resolve token-to-token references. Depth-limited so a cycle reports itself
    # rather than hanging the build.
    for _ in range(12):
        changed = False
        for name, value in list(flat.items()):
            resolved, missing = substitute_vars(value, flat)
            if missing:
                raise TokenError(
                    "token %s references undefined token(s): %s"
                    % (name, ", ".join(sorted(missing)))
                )
            if resolved != value:
                flat[name] = resolved
                changed = True
        if not changed:
            break
    else:
        unresolved = sorted(n for n, v in flat.items() if "var(" in v)
        raise TokenError("token reference cycle involving: %s" % ", ".join(unresolved))

    return flat


def substitute_vars(text: str, tokens: dict[str, str]) -> tuple[str, set[str]]:
    """Replace var(--x) / var(--x, fallback). Returns (text, names that had no value).

    A `var()` with a fallback and no token resolves to the fallback and is NOT
    reported missing — that is the documented escape hatch for a value the email
    layer legitimately owns. A bare `var()` with no token is an error.
    """
    missing: set[str] = set()

    def repl(match: re.Match[str]) -> str:
        name = match.group(1)
        fallback = match.group(2)
        if name in tokens:
            return tokens[name]
        if fallback is not None:
            return fallback.strip()
        missing.add(name)
        return match.group(0)

    # Loop so a token whose value itself contains var() resolves in one pass.
    for _ in range(12):
        new = VAR_RE.sub(repl, text)
        if new == text:
            break
        text = new
    return text, missing


# ---------------------------------------------------------------------------
# CSS: a tolerant parser for the subset email templates actually use
# ---------------------------------------------------------------------------


class Declaration:
    __slots__ = ("prop", "value", "important")

    def __init__(self, prop: str, value: str, important: bool) -> None:
        self.prop = prop
        self.value = value
        self.important = important

    def render(self) -> str:
        return "%s:%s%s" % (self.prop, self.value, "!important" if self.important else "")


class Rule:
    __slots__ = ("selectors", "declarations", "order", "at_rule", "raw")

    def __init__(self, selectors, declarations, order, at_rule, raw) -> None:
        self.selectors: list[str] = selectors
        self.declarations: list[Declaration] = declarations
        self.order: int = order
        self.at_rule: str | None = at_rule
        self.raw: str = raw


def strip_css_comments(css: str) -> str:
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)


def parse_declarations(block: str) -> list[Declaration]:
    decls: list[Declaration] = []
    depth = 0
    buf: list[str] = []
    pieces: list[str] = []
    for ch in block:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        if ch == ";" and depth == 0:
            pieces.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    pieces.append("".join(buf))

    for piece in pieces:
        if ":" not in piece:
            continue
        prop, _, value = piece.partition(":")
        prop = prop.strip().lower()
        value = value.strip()
        if not prop or not value:
            continue
        important = False
        m = re.search(r"!\s*important\s*$", value, flags=re.I)
        if m:
            important = True
            value = value[: m.start()].strip()
        decls.append(Declaration(prop, value, important))
    return decls


def parse_stylesheet(css: str) -> list[Rule]:
    """Parse into a flat rule list, carrying at-rule context as a string.

    Deliberately small. It understands rules, `@media`/`@supports` blocks one level
    deep, and passes anything else through untouched as a retained raw chunk.
    """
    css = strip_css_comments(css)
    rules: list[Rule] = []
    order = 0
    i = 0
    n = len(css)

    def read_block(start: int) -> tuple[str, int]:
        """Return (inner text, index after the closing brace)."""
        depth = 0
        j = start
        while j < n:
            if css[j] == "{":
                depth += 1
            elif css[j] == "}":
                depth -= 1
                if depth == 0:
                    return css[start + 1 : j], j + 1
            j += 1
        return css[start + 1 :], n

    while i < n:
        brace = css.find("{", i)
        if brace == -1:
            break
        prelude = css[i:brace].strip()
        inner, i = read_block(brace)

        if prelude.startswith("@"):
            at_name = prelude.split(None, 1)[0].lower()
            if at_name in ("@media", "@supports"):
                for sub in parse_stylesheet(inner):
                    at = prelude if sub.at_rule is None else "%s %s" % (prelude, sub.at_rule)
                    rules.append(Rule(sub.selectors, sub.declarations, order, at, sub.raw))
                    order += 1
            else:
                # @font-face, @keyframes, @import-with-block, anything exotic:
                # keep it verbatim, never inline it.
                rules.append(Rule([], [], order, None, "%s{%s}" % (prelude, inner)))
                order += 1
            continue

        selectors = [s.strip() for s in split_selector_list(prelude) if s.strip()]
        decls = parse_declarations(inner)
        if selectors and decls:
            rules.append(Rule(selectors, decls, order, None, ""))
            order += 1

    return rules


def split_selector_list(prelude: str) -> list[str]:
    parts: list[str] = []
    depth = 0
    buf: list[str] = []
    for ch in prelude:
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth = max(0, depth - 1)
        if ch == "," and depth == 0:
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    parts.append("".join(buf))
    return parts


# ---------------------------------------------------------------------------
# Selector matching — element, class, id, descendant, child, universal
# ---------------------------------------------------------------------------

SIMPLE_RE = re.compile(
    r"""^
    (?P<tag>[A-Za-z][A-Za-z0-9-]*|\*)?
    (?P<rest>(?:[#.][A-Za-z0-9_-]+)*)
    $""",
    re.X,
)


class Compound:
    __slots__ = ("tag", "ids", "classes")

    def __init__(self, tag: str | None, ids: list[str], classes: list[str]) -> None:
        self.tag = tag
        self.ids = ids
        self.classes = classes

    def matches(self, node: Node) -> bool:
        if self.tag and node.tag != self.tag:
            return False
        if self.ids:
            node_id = node.get("id")
            if node_id is None or any(i != node_id for i in self.ids):
                return False
        if self.classes:
            have = set(node.classes)
            if not all(c in have for c in self.classes):
                return False
        return True


class CompiledSelector:
    """A sequence of (combinator, compound) steps, left to right.

    Combinators: None for the first step, " " descendant, ">" child.
    """

    __slots__ = ("steps", "specificity", "text")

    def __init__(self, steps, specificity, text) -> None:
        self.steps: list[tuple[str | None, Compound]] = steps
        self.specificity: tuple[int, int, int] = specificity
        self.text: str = text

    def matches(self, node: Node) -> bool:
        return _match_from(self.steps, len(self.steps) - 1, node)


def _match_from(steps, index: int, node: Node) -> bool:
    # steps[i] is (combinator that precedes this compound, compound).
    combinator, compound = steps[index]
    if not compound.matches(node):
        return False
    if index == 0:
        return True
    parent = node.parent
    if combinator == ">":
        if parent is None or parent.kind != "element":
            return False
        return _match_from(steps, index - 1, parent)
    # descendant
    while parent is not None and parent.kind == "element":
        if _match_from(steps, index - 1, parent):
            return True
        parent = parent.parent
    return False


def compile_selector(selector: str) -> CompiledSelector | None:
    """Return a CompiledSelector, or None if the selector is outside the subset.

    Outside the subset means: pseudo-classes, pseudo-elements, attribute selectors,
    sibling combinators, `:is()`/`:where()`/`:not()`. Those cannot be resolved to a
    static element set at build time, so their rules stay in the `<style>` block.
    """
    text = " ".join(selector.split())
    if not text:
        return None
    if re.search(r"[:\[\]~+]", text):
        return None

    tokens = re.split(r"\s*(>)\s*|\s+", text)
    tokens = [t for t in tokens if t]

    steps: list[tuple[str | None, Compound]] = []
    pending_comb: str | None = None
    ids = classes = elems = 0

    for i, tok in enumerate(tokens):
        if tok == ">":
            pending_comb = ">"
            continue
        m = SIMPLE_RE.match(tok)
        if not m:
            return None
        tag = m.group("tag")
        rest = m.group("rest") or ""
        step_ids = re.findall(r"#([A-Za-z0-9_-]+)", rest)
        step_classes = re.findall(r"\.([A-Za-z0-9_-]+)", rest)
        if tag == "*":
            tag = None
        elif tag:
            tag = tag.lower()
            elems += 1
        ids += len(step_ids)
        classes += len(step_classes)
        comb = pending_comb if steps else None
        if steps and comb is None:
            comb = " "
        steps.append((comb, Compound(tag, step_ids, step_classes)))
        pending_comb = None

    if not steps:
        return None
    return CompiledSelector(steps, (ids, classes, elems), text)


# ---------------------------------------------------------------------------
# Inlining
# ---------------------------------------------------------------------------
#
# Cascade ordering, from weakest to strongest:
#
#   0  normal declaration from the stylesheet, ordered by (specificity, source order)
#   1  normal declaration already in the element's `style` attribute
#   2  !important declaration from the stylesheet, ordered by (specificity, source)
#   3  !important declaration already in the element's `style` attribute
#
# This is the real CSS cascade for author-origin declarations, minus layers (email
# has none — Law 5 is gone here) and minus transitions/animations (email has none
# that survive). Sorting ascending and letting later writes win reproduces it.


def inline_rules(root: Node, rules: list[Rule], retained: list[Rule]) -> int:
    inlinable: list[tuple[CompiledSelector, Rule]] = []

    for rule in rules:
        if rule.raw:
            retained.append(rule)
            continue
        if rule.at_rule is not None:
            retained.append(rule)
            continue
        matched_any = False
        leftover: list[str] = []
        for selector in rule.selectors:
            compiled = compile_selector(selector)
            if compiled is None:
                leftover.append(selector)
            else:
                inlinable.append((compiled, rule))
                matched_any = True
        if leftover:
            # Split the rule: the inlinable selectors get inlined, the rest is kept.
            retained.append(Rule(leftover, rule.declarations, rule.order, None, ""))
        if not matched_any and not leftover:
            retained.append(rule)

    # element -> list of (rank, prop, value, important)
    pending: dict[int, list[tuple[tuple, str, str, bool]]] = {}
    elements = {id(n): n for n in root.elements()}

    for compiled, rule in inlinable:
        for node in root.elements():
            if node.tag in ("style", "script", "head", "title", "meta", "link"):
                continue
            if not compiled.matches(node):
                continue
            bucket = pending.setdefault(id(node), [])
            spec = compiled.specificity
            for decl in rule.declarations:
                tier = 2 if decl.important else 0
                rank = (tier, spec[0], spec[1], spec[2], rule.order)
                bucket.append((rank, decl.prop, decl.value, decl.important))

    count = 0
    for node_id, bucket in pending.items():
        node = elements[node_id]
        existing = parse_declarations(node.get("style") or "")
        for decl in existing:
            tier = 3 if decl.important else 1
            bucket.append(((tier, 9, 9, 9, 10**9), decl.prop, decl.value, decl.important))

        bucket.sort(key=lambda item: item[0])

        final: dict[str, tuple[str, bool]] = {}
        for _rank, prop, value, important in bucket:
            final[prop] = (value, important)

        if not final:
            continue
        rendered = ";".join(
            "%s:%s%s" % (prop, value, "!important" if important else "")
            for prop, (value, important) in final.items()
        )
        node.set("style", rendered)
        count += 1

    return count


def render_retained(rules: list[Rule]) -> str:
    """Re-emit the rules that must stay as CSS, grouped by at-rule context."""
    chunks: list[str] = []
    current_at: str | None = None
    buffer: list[str] = []

    def flush() -> None:
        if not buffer:
            return
        body = "".join(buffer)
        if current_at:
            chunks.append("%s{%s}" % (current_at, body))
        else:
            chunks.append(body)
        buffer.clear()

    for rule in rules:
        if rule.raw:
            flush()
            current_at = None
            chunks.append(rule.raw)
            continue
        if rule.at_rule != current_at:
            flush()
            current_at = rule.at_rule
        buffer.append(
            "%s{%s}"
            % (",".join(rule.selectors), ";".join(d.render() for d in rule.declarations))
        )
    flush()
    return "".join(chunks)


# ---------------------------------------------------------------------------
# MSO scaffolding
# ---------------------------------------------------------------------------

MSO_HEAD_BLOCK = (
    "<!--[if mso]>\n"
    "<noscript><xml><o:OfficeDocumentSettings>\n"
    "<o:AllowPNG/>\n"
    "<o:PixelsPerInch>96</o:PixelsPerInch>\n"
    "</o:OfficeDocumentSettings></xml></noscript>\n"
    "<![endif]-->"
)


def inject_mso(root: Node) -> list[str]:
    notes: list[str] = []
    html = root.find("html")
    if html is not None:
        for ns, value in (
            ("xmlns:v", "urn:schemas-microsoft-com:vml"),
            ("xmlns:o", "urn:schemas-microsoft-com:office:office"),
        ):
            if not html.has(ns):
                html.set(ns, value)
                notes.append("added %s to <html>" % ns)

    head = root.find("head")
    if head is None:
        return notes
    already = any(
        node.kind == "comment" and "PixelsPerInch" in node.data for node in head.walk()
    )
    if already:
        return notes
    comment = Node("comment", data=MSO_HEAD_BLOCK[4:-3])
    comment.parent = head
    head.children.append(comment)
    notes.append("added <o:PixelsPerInch>96</o:PixelsPerInch> (120-DPI defuse)")
    return notes


# ---------------------------------------------------------------------------
# Plain-text alternative
# ---------------------------------------------------------------------------


def generate_text(root: Node, width: int = 72) -> str:
    """Walk the DOM and produce a plain-text part a human would not be ashamed of.

    Preheader text is skipped (it is a subject-line accessory, not body copy),
    `aria-hidden` and hidden spacers are skipped, links carry their href, headings
    get an underline, and list items keep their bullets.
    """
    lines: list[str] = []
    buf: list[str] = []

    def flush() -> None:
        text = " ".join("".join(buf).split())
        buf.clear()
        if not text:
            if lines and lines[-1] != "":
                lines.append("")
            return
        lines.extend(wrap(text, width))

    def visit(node: Node) -> None:
        if node.kind == "text":
            buf.append(unescape_entities(node.data))
            return
        if node.kind != "element":
            return
        if node.tag in TEXT_SKIP_TAGS:
            return
        if node.get("data-preheader") is not None:
            return
        if (node.get("aria-hidden") or "").lower() == "true":
            return
        if node.get("data-text-skip") is not None:
            return

        if node.tag == "br":
            flush()
            return
        if node.tag == "hr":
            flush()
            lines.append("-" * min(width, 40))
            lines.append("")
            return
        if node.tag == "img":
            alt = (node.get("alt") or "").strip()
            if alt:
                buf.append("[%s]" % alt)
            return

        is_block = node.tag in TEXT_BLOCK_TAGS
        is_heading = node.tag in ("h1", "h2", "h3", "h4", "h5", "h6")

        if is_block:
            flush()
        if node.tag == "li":
            buf.append("- ")

        before = len(buf)
        for child in node.children:
            visit(child)

        if node.tag in ("td", "th") and len(buf) > before:
            # Soft separator so `Item` and `$248.00` share one line.
            if buf and not buf[-1].endswith(("  ", "\n")):
                buf.append("  ")

        if node.tag == "a":
            href = (node.get("href") or "").strip()
            label = " ".join(node.text_content().split())
            if href and not href.startswith(("mailto:", "tel:", "#")) and href != label:
                buf.append(" <%s>" % href)

        if is_block:
            if is_heading:
                text = " ".join("".join(buf).split())
                buf.clear()
                if text:
                    lines.extend(wrap(text, width))
                    lines.append(("=" if node.tag in ("h1", "h2") else "-") * min(len(text), width))
                lines.append("")
            else:
                flush()

    visit(root)
    flush()

    out: list[str] = []
    for line in lines:
        if line == "" and (not out or out[-1] == ""):
            continue
        out.append(line)
    while out and out[-1] == "":
        out.pop()
    return "\n".join(out) + "\n"


ENTITIES = {
    "&amp;": "&", "&lt;": "<", "&gt;": ">", "&quot;": '"', "&apos;": "'",
    "&nbsp;": " ", "&mdash;": "—", "&ndash;": "–", "&hellip;": "…",
    "&rsquo;": "’", "&lsquo;": "‘", "&ldquo;": "“", "&rdquo;": "”",
    "&zwnj;": "", "&copy;": "©", "&reg;": "®", "&trade;": "™",
    "&middot;": "·", "&bull;": "•", "&laquo;": "«",
    "&raquo;": "»", "&deg;": "°", "&euro;": "€", "&pound;": "£",
    "&yen;": "¥", "&cent;": "¢", "&sect;": "§", "&para;": "¶",
    "&dagger;": "†", "&times;": "×", "&divide;": "÷",
    "&frac12;": "½", "&shy;": "", "&ensp;": " ", "&emsp;": " ",
    "&thinsp;": " ", "&zwj;": "", "&larr;": "←", "&rarr;": "→",
}


def unescape_entities(text: str) -> str:
    for name, char in ENTITIES.items():
        text = text.replace(name, char)

    def numeric(match: re.Match[str]) -> str:
        body = match.group(1)
        try:
            code = int(body[1:], 16) if body[:1].lower() == "x" else int(body)
        except ValueError:
            return match.group(0)
        return chr(code) if 0 < code < 0x110000 else ""

    return re.sub(r"&#(x[0-9a-fA-F]+|\d+);", numeric, text)


def wrap(text: str, width: int) -> list[str]:
    words = text.split()
    if not words:
        return []
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        if len(current) + 1 + len(word) <= width:
            current += " " + word
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


# ---------------------------------------------------------------------------
# Minify
# ---------------------------------------------------------------------------


def minify_html(html: str) -> str:
    """Conservative. Never touches conditional comments, never joins two words."""
    placeholders: list[str] = []

    def stash(match: re.Match[str]) -> str:
        placeholders.append(match.group(0))
        return "\x00%d\x00" % (len(placeholders) - 1)

    # Conditional comments (both forms) and <pre> are protected.
    html = re.sub(r"<!--\[if[^>]*?\]>.*?<!\[endif\]-->", stash, html, flags=re.S | re.I)
    html = re.sub(r"<!--\[if[^>]*?\]><!.*?-->", stash, html, flags=re.S | re.I)
    html = re.sub(r"<!--<!\[endif\]-->", stash, html, flags=re.S | re.I)
    html = re.sub(r"<pre\b.*?</pre>", stash, html, flags=re.S | re.I)

    html = re.sub(r"<!--(?!\[if|<!\[endif).*?-->", "", html, flags=re.S)
    html = re.sub(r">\s+<", "><", html)
    html = re.sub(r"[ \t]*\n[ \t]*", "\n", html)
    html = re.sub(r"\n{2,}", "\n", html)

    for index, original in enumerate(placeholders):
        html = html.replace("\x00%d\x00" % index, original)
    return html.strip()


def minify_css(css: str) -> str:
    css = strip_css_comments(css)
    css = re.sub(r"\s+", " ", css)
    css = re.sub(r"\s*([{};:,>])\s*", r"\1", css)
    css = re.sub(r";}", "}", css)
    return css.strip()


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------


def substitute_document(root: Node, tokens: dict[str, str]) -> set[str]:
    """Resolve var() everywhere it can legally appear in an email source template."""
    missing: set[str] = set()
    attr_targets = ("style", "bgcolor", "background", "width", "height", "color", "align")

    for node in root.walk():
        if node.kind == "comment":
            new, miss = substitute_vars(node.data, tokens)
            node.data = new
            missing |= miss
        elif node.kind == "element":
            for pair in node.attrs:
                if pair[1] is None:
                    continue
                if pair[0] in attr_targets or "var(" in pair[1]:
                    new, miss = substitute_vars(pair[1], tokens)
                    pair[1] = new
                    missing |= miss
            if node.tag == "style":
                for child in node.children:
                    if child.kind == "text":
                        new, miss = substitute_vars(child.data, tokens)
                        child.data = new
                        missing |= miss
    return missing


def strip_comments(node: Node) -> int:
    """Remove authoring comments. Conditional comments and ESP directives stay."""
    removed = 0
    if node.kind != "element":
        return 0
    keep: list[Node] = []
    for child in node.children:
        if child.kind == "comment" and not COMMENT_KEEP_RE.search(child.data):
            removed += 1
            continue
        keep.append(child)
        removed += strip_comments(child)
    node.children = keep
    return removed


def build(
    source: str,
    tokens: dict[str, str],
    *,
    inline: bool = True,
    mso: bool = True,
    minify: bool = False,
    keep_comments: bool = False,
) -> tuple[str, dict]:
    root = parse_html(source)
    report: dict = {"notes": [], "warnings": []}

    missing = substitute_document(root, tokens)
    if missing:
        raise TokenError(
            "unresolved token(s) with no value and no fallback: %s"
            % ", ".join(sorted(missing))
        )

    style_nodes = [n for n in root.elements() if n.tag == "style"]
    retained: list[Rule] = []
    inlined_elements = 0
    rule_count = 0

    for style_node in style_nodes:
        css = "".join(c.data for c in style_node.children if c.kind == "text")
        keep_whole = (style_node.get("data-embed") or "").lower() in ("keep", "embed")
        if keep_whole or not inline:
            # Leave this block exactly as authored.
            continue
        rules = parse_stylesheet(css)
        rule_count += len(rules)
        inlined_elements += inline_rules(root, rules, retained)
        # Empty it; we rewrite the survivors into the first block below.
        style_node.children = []
        style_node.set("data-compiled", "1")

    if inline and style_nodes:
        survivors = render_retained(retained)
        target = None
        for node in style_nodes:
            if (node.get("data-embed") or "").lower() not in ("keep", "embed"):
                target = node
                break
        if target is not None:
            if survivors:
                text = Node("text", data="\n" + (minify_css(survivors) if minify else survivors) + "\n")
                text.parent = target
                target.children = [text]
            else:
                parent = target.parent
                if parent is not None:
                    parent.children = [c for c in parent.children if c is not target]
        for node in style_nodes:
            if node is not target and node.get("data-compiled") == "1":
                parent = node.parent
                if parent is not None:
                    parent.children = [c for c in parent.children if c is not node]

    if mso:
        report["notes"].extend(inject_mso(root))

    if not keep_comments:
        dropped = strip_comments(root)
        if dropped:
            report["notes"].append(
                "dropped %d authoring comment(s); conditional comments and ESP "
                "directives kept" % dropped
            )

    for node in root.elements():
        if node.tag == "style" and node.has("data-compiled"):
            node.attrs = [p for p in node.attrs if p[0] != "data-compiled"]

    html = serialize(root)
    if minify:
        html = minify_html(html)

    report["rules"] = rule_count
    report["retained"] = sum(1 for r in retained if not r.raw)
    report["inlined_elements"] = inlined_elements
    report["bytes"] = len(html.encode("utf-8"))
    report["clip_limit"] = GMAIL_CLIP_BYTES
    report["clip_pct"] = report["bytes"] / GMAIL_CLIP_BYTES * 100

    style_bytes = 0
    for match in re.finditer(r"<style[^>]*>(.*?)</style>", html, flags=re.S | re.I):
        style_bytes += len(match.group(1).encode("utf-8"))
    report["style_bytes"] = style_bytes

    if report["bytes"] > GMAIL_CLIP_BYTES:
        report["warnings"].append(
            "OVER Gmail's clipping threshold: %s bytes > %s. Gmail will truncate the "
            "body and hide everything past the cut behind a 'View entire message' link "
            "— including the unsubscribe footer." % (report["bytes"], GMAIL_CLIP_BYTES)
        )
    elif report["clip_pct"] > 90:
        report["warnings"].append(
            "within 10%% of the clipping threshold (%.1f%%). ESP merge tags and "
            "link-tracking rewrites add bytes after you hand this over."
            % report["clip_pct"]
        )
    if style_bytes > GMAIL_STYLE_BYTES:
        report["warnings"].append(
            "<style> content is %s bytes; Gmail drops style content past %s."
            % (style_bytes, GMAIL_STYLE_BYTES)
        )

    return html, report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def default_tokens_path() -> Path:
    return Path(__file__).resolve().parent.parent / "assets" / "email-tokens.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m scripts.build_email",
        description="Compile a token-authored source template into sendable email HTML.",
    )
    parser.add_argument("source", help="source template (.html) authored against tokens")
    parser.add_argument("--out", "-o", help="write compiled HTML here (default: stdout)")
    parser.add_argument("--tokens", help="email-tokens.json (default: assets/email-tokens.json)")
    parser.add_argument("--text", help="also write the plain-text alternative here")
    parser.add_argument("--text-only", action="store_true",
                        help="emit only the plain-text alternative (to stdout unless --out)")
    parser.add_argument("--no-inline", action="store_true",
                        help="resolve tokens but leave CSS in the <style> block")
    parser.add_argument("--no-mso", action="store_true",
                        help="skip the Outlook namespace / PixelsPerInch scaffolding")
    parser.add_argument("--minify", action="store_true",
                        help="collapse whitespace between tags and inside the <style> block")
    parser.add_argument("--keep-comments", action="store_true",
                        help="keep authoring comments (default: drop all but conditional "
                             "comments and ESP directives)")
    parser.add_argument("--width", type=int, default=72,
                        help="wrap column for the plain-text part (default 72)")
    parser.add_argument("--quiet", "-q", action="store_true", help="suppress the report")
    parser.add_argument("--strict", action="store_true", help="exit 1 on any warning")
    args = parser.parse_args(argv)

    source_path = Path(args.source)
    try:
        source = source_path.read_text(encoding="utf-8")
    except OSError as exc:
        print("error: cannot read %s: %s" % (source_path, exc), file=sys.stderr)
        return 2

    tokens_path = Path(args.tokens) if args.tokens else default_tokens_path()
    try:
        tokens = load_tokens(tokens_path)
    except TokenError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2

    try:
        html, report = build(
            source,
            tokens,
            inline=not args.no_inline,
            mso=not args.no_mso,
            minify=args.minify,
            keep_comments=args.keep_comments,
        )
    except TokenError as exc:
        print("error: %s" % exc, file=sys.stderr)
        print("       every token an email template uses must exist in %s, or carry a"
              " var(--x, fallback)." % tokens_path.name, file=sys.stderr)
        return 2

    text = generate_text(parse_html(html), width=args.width)

    if args.text_only:
        if args.out:
            Path(args.out).parent.mkdir(parents=True, exist_ok=True)
            Path(args.out).write_text(text, encoding="utf-8")
        else:
            sys.stdout.write(text)
        return 0

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(html, encoding="utf-8")
    else:
        sys.stdout.write(html)

    if args.text:
        text_path = Path(args.text)
        text_path.parent.mkdir(parents=True, exist_ok=True)
        text_path.write_text(text, encoding="utf-8")

    if not args.quiet:
        stream = sys.stderr if not args.out else sys.stdout
        print("built   %s" % (args.out or "<stdout>"), file=stream)
        print("        %d rules parsed, %d retained as CSS, %d elements got inline styles"
              % (report["rules"], report["retained"], report["inlined_elements"]), file=stream)
        print("        %d bytes of <style> survived (Gmail drops past %d)"
              % (report["style_bytes"], GMAIL_STYLE_BYTES), file=stream)
        print("        %s bytes — %.1f%% of Gmail's %s-byte clipping threshold"
              % (f"{report['bytes']:,}", report["clip_pct"], f"{GMAIL_CLIP_BYTES:,}"),
              file=stream)
        if args.text:
            print("text    %s (%d lines)" % (args.text, text.count("\n")), file=stream)
        for note in report["notes"]:
            print("note    %s" % note, file=stream)
        for warning in report["warnings"]:
            print("WARN    %s" % warning, file=stream)

    if report["bytes"] > GMAIL_CLIP_BYTES:
        return 1
    if args.strict and report["warnings"]:
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
