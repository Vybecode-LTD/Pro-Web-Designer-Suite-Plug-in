#!/usr/bin/env python3
"""Generate a component state/variant proof sheet from a matrix.json manifest.

The proof sheet renders every component across the axes that can interfere with
each other — state x variant x size x density x theme x content fixture — as one
self-contained HTML file. Every cell carries a stable `data-cell-id` so a
screenshot tool can target it individually (see `snapshot_matrix.mjs`).

Two things this does that a screenshot of your app cannot:

  1. It FORCES pseudo-class states. You cannot hover 200 cells at once, so the
     generator reads each component's own CSS, finds every rule whose selector
     contains `:hover`, `:active`, `:focus-visible` or `:focus`, and emits a
     mirrored rule keyed on `[data-force-state~="..."]`. Same specificity, later
     in the same layer, so it wins on document order rather than on a fight.
  2. It reports STATE COVERAGE. A state with no matching rule in the component's
     own stylesheet is labelled on the sheet and listed in the summary. That is
     the "did I actually implement all seven states" question, answered.

Usage
-----
    python -m scripts.generate_matrix matrix.json --out proof-sheet.html

    # narrow the axes while iterating
    python -m scripts.generate_matrix matrix.json \
        --only button --themes dark --densities compact,comfortable \
        --out /tmp/button-sheet.html

    # the full cross product, when you are hunting a specific interaction
    python -m scripts.generate_matrix matrix.json --profile full --out full.html

    # emit the sheet's own chrome stylesheet so audit_design.py can read it,
    # then gate on it in CI
    python -m scripts.generate_matrix matrix.json --out sheet.html \
        --emit-css build/matrix-chrome.css --strict
    python -m scripts.audit_design build/matrix-chrome.css

Exit codes
----------
    0  sheet written
    1  --strict was passed and at least one component is missing a state rule
    2  bad arguments, missing files, or an invalid manifest

Standard library only. Python 3.9+.
"""

from __future__ import annotations

import argparse
import html
import itertools
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Sequence, Tuple

SCHEMA = "component-state-matrix/1"

# ---------------------------------------------------------------------------
# The state model
# ---------------------------------------------------------------------------
# Every interactive component implements all seven. `attrs` is what the cell's
# markup gets; `force` is the pseudo-class that must be transposed because it
# cannot be set statically; `detect` is how we decide whether the component's
# own CSS says anything about this state at all.
#
# Note what is NOT here: `is-*` classes. State is a real ARIA attribute where
# one exists, `data-state` otherwise. See references/state-coverage.md.

STATE_MODEL: Dict[str, Dict[str, Any]] = {
    "default": {
        "attrs": {},
        "force": None,
        "detect": None,  # the root rule is the default state, always present
        "blurb": "the resting state everything else is measured against",
    },
    "hover": {
        "attrs": {"data-force-state": "hover"},
        "force": "hover",
        "detect": [":hover"],
        "blurb": "pointer over the target; must never be the only affordance",
    },
    "focus-visible": {
        "attrs": {"data-force-state": "focus-visible"},
        "force": "focus-visible",
        "detect": [":focus-visible", ":focus"],
        "blurb": "keyboard focus; the ring must survive forced-colors",
    },
    "active": {
        "attrs": {"data-force-state": "active"},
        "force": "active",
        "detect": [":active"],
        "blurb": "pressed; confirms the press landed before the result does",
    },
    "disabled": {
        "attrs": {"aria-disabled": "true"},
        "form_attrs": {"disabled": ""},
        "force": None,
        "detect": [":disabled", "[aria-disabled", "[disabled"],
        "blurb": "not operable now; exempt from contrast, not from legibility",
    },
    "loading": {
        "attrs": {"data-state": "loading", "aria-busy": "true"},
        "force": None,
        "detect": ['data-state="loading"', 'data-state~="loading"', "[aria-busy"],
        "blurb": "work in flight; must hold its own size or the layout jumps",
    },
    "error": {
        "attrs": {"aria-invalid": "true", "data-state": "error"},
        "force": None,
        "detect": ["[aria-invalid", 'data-state="error"', "[data-invalid"],
        "blurb": "invalid or failed; colour alone never carries this",
    },
}

SEVEN_STATES = list(STATE_MODEL)

# Longest-first so `:focus-visible` is matched before `:focus`.
FORCEABLE_PSEUDO = ("focus-visible", "focus-within", "focus", "hover", "active",
                    "visited", "target")
PSEUDO_RE = re.compile(
    r"(?<!:):(" + "|".join(FORCEABLE_PSEUDO) + r")\b"
)

FORM_TAG_RE = re.compile(r"<\s*(button|input|select|textarea|fieldset|optgroup|option)\b", re.I)

DEFAULT_THEMES = ["light", "dark"]
DEFAULT_DENSITIES = ["compact", "comfortable", "spacious"]


class ManifestError(Exception):
    """A manifest problem the user can fix. Printed without a traceback."""


# ---------------------------------------------------------------------------
# A small, brace-aware CSS block reader
# ---------------------------------------------------------------------------
# Not a parser. It only needs to know where blocks start and end so that rules
# can be mirrored with their at-rule context intact — a `:hover` rule nested in
# `@media (hover: hover)` must keep that guard, or the proof sheet would claim a
# hover style that touch devices never see.


class Node:
    __slots__ = ("kind", "head", "body", "children")

    def __init__(self, kind: str, head: str, body: str = "", children=None):
        self.kind = kind            # "at-block" | "at-stmt" | "rule" | "text"
        self.head = head            # prelude or selector
        self.body = body            # declaration text, for rules
        self.children: List["Node"] = children if children is not None else []


def strip_comments(css: str) -> str:
    out: List[str] = []
    i, n = 0, len(css)
    while i < n:
        c = css[i]
        if c == "/" and i + 1 < n and css[i + 1] == "*":
            j = css.find("*/", i + 2)
            i = n if j == -1 else j + 2
            out.append(" ")
            continue
        if c in "\"'":
            q = c
            out.append(c)
            i += 1
            while i < n and css[i] != q:
                if css[i] == "\\" and i + 1 < n:
                    out.append(css[i])
                    i += 1
                out.append(css[i])
                i += 1
            if i < n:
                out.append(css[i])
                i += 1
            continue
        out.append(c)
        i += 1
    return "".join(out)


def parse_css(css: str) -> List[Node]:
    """Parse into a shallow tree of at-blocks, rules and statements."""
    css = strip_comments(css)
    root: List[Node] = []
    stack: List[List[Node]] = [root]
    heads: List[str] = []
    buf: List[str] = []
    depth_paren = 0
    i, n = 0, len(css)
    while i < n:
        c = css[i]
        if c in "\"'":
            q = c
            buf.append(c)
            i += 1
            while i < n and css[i] != q:
                if css[i] == "\\" and i + 1 < n:
                    buf.append(css[i])
                    i += 1
                buf.append(css[i])
                i += 1
            if i < n:
                buf.append(css[i])
                i += 1
            continue
        if c == "(":
            depth_paren += 1
        elif c == ")":
            depth_paren = max(0, depth_paren - 1)

        if c == "{" and depth_paren == 0:
            head = "".join(buf).strip()
            buf = []
            node = Node("at-block" if head.startswith("@") else "rule", head)
            stack[-1].append(node)
            stack.append(node.children)
            heads.append(head)
            i += 1
            continue
        if c == "}" and depth_paren == 0:
            leftover = "".join(buf).strip()
            buf = []
            if leftover and len(stack) > 1:
                stack[-1].append(Node("text", "", leftover))
            if len(stack) > 1:
                stack.pop()
                heads.pop()
            i += 1
            continue
        if c == ";" and depth_paren == 0:
            stmt = "".join(buf).strip()
            buf = []
            if stmt.startswith("@"):
                stack[-1].append(Node("at-stmt", stmt))
            elif stmt:
                stack[-1].append(Node("text", "", stmt))
            i += 1
            continue
        buf.append(c)
        i += 1

    # Fold declaration `text` children of a rule back into its body.
    def fold(nodes: List[Node]) -> None:
        for nd in nodes:
            if nd.kind == "rule":
                decls = [c.body for c in nd.children if c.kind == "text"]
                nested = [c for c in nd.children if c.kind != "text"]
                nd.body = ";\n  ".join(d for d in decls if d)
                nd.children = nested
                fold(nested)
            elif nd.kind == "at-block":
                fold(nd.children)

    fold(root)
    return root


def transpose_selector(selector: str) -> Optional[str]:
    """Rewrite `.b:hover:not(:disabled)` -> `.b[data-force-state~="hover"]:not(:disabled)`.

    Only pseudo-classes at paren depth 0 are rewritten: `:not(:hover)` is a
    *guard*, not a state, and rewriting it would invert the rule. Comma parts
    with no forceable pseudo-class are dropped — keeping them would apply the
    hover styles unconditionally, which is the exact bug this tool exists to
    find.
    """
    kept: List[str] = []
    for part in split_selector_list(selector):
        rewritten, hits = transpose_part(part)
        if hits:
            kept.append(rewritten)
    return ", ".join(kept) if kept else None


def split_selector_list(selector: str) -> List[str]:
    parts, buf, depth = [], [], 0
    for ch in selector:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        if ch == "," and depth == 0:
            parts.append("".join(buf).strip())
            buf = []
            continue
        buf.append(ch)
    tail = "".join(buf).strip()
    if tail:
        parts.append(tail)
    return parts


def transpose_part(part: str) -> Tuple[str, int]:
    out: List[str] = []
    depth = 0
    i, n = 0, len(part)
    hits = 0
    while i < n:
        ch = part[i]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        if ch == ":" and depth == 0:
            m = PSEUDO_RE.match(part, i)
            if m:
                out.append('[data-force-state~="%s"]' % m.group(1))
                hits += 1
                i = m.end()
                continue
        out.append(ch)
        i += 1
    return "".join(out), hits


def build_force_shim(nodes: Sequence[Node]) -> str:
    """Emit mirrored rules for every forceable pseudo-class, context intact."""
    lines: List[str] = []

    def walk(items: Sequence[Node], stack: Tuple[str, ...]) -> None:
        for nd in items:
            if nd.kind == "at-block":
                walk(nd.children, stack + (nd.head,))
            elif nd.kind == "rule":
                sel = transpose_selector(nd.head)
                if sel and nd.body.strip():
                    emit(stack, sel, nd.body)
                walk(nd.children, stack)

    def emit(stack: Tuple[str, ...], sel: str, body: str) -> None:
        indent = ""
        for head in stack:
            lines.append(f"{indent}{head} {{")
            indent += "  "
        lines.append(f"{indent}{sel} {{")
        for decl in [d.strip() for d in body.split(";") if d.strip()]:
            lines.append(f"{indent}  {decl};")
        lines.append(f"{indent}}}")
        for k in range(len(stack) - 1, -1, -1):
            lines.append(f"{'  ' * k}}}")

    walk(nodes, ())
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# The token rebind shim — the single subtlest thing this generator does
# ---------------------------------------------------------------------------
# A custom property's `var()` references are substituted at computed-value time
# ON THE ELEMENT WHERE THE PROPERTY IS DECLARED. So:
#
#     :root            { --density: 1; --pad-card: calc(var(--space-6) * var(--density)); }
#     [data-density="compact"] { --density: 0.875; }
#
# computes `--pad-card` to 24px at `:root` and inherits that NUMBER downward.
# Setting `data-density="compact"` on a descendant changes `--density` there and
# changes nothing else: `--pad-card` was already resolved. Verified in Chromium.
#
# In a real app this never surfaces, because `data-theme` and `data-density` sit
# on `<html>` — which IS the element the tokens are declared on. A proof sheet
# puts many themes and densities on one page, so it has to rebind every root
# token that transitively depends on something a theme or density block
# re-points, on the stage element itself. Miss this and the sheet renders every
# density identically and every dark cell with light-theme shadows — i.e. it
# would quietly pass Law 7 and Law 6 while proving nothing.
#
# The set is derived from the token file rather than hand-listed, so it stays
# correct when the token file grows.

CUSTOM_DECL_RE = re.compile(r"(--[\w-]+)\s*:\s*([^;]+)")


def _collect_token_decls(nodes: Sequence[Node], in_media: bool,
                         root: Dict[str, str], overridden: set) -> None:
    for nd in nodes:
        if nd.kind == "at-block":
            _collect_token_decls(nd.children, in_media or not nd.head.startswith("@layer"),
                                 root, overridden)
        elif nd.kind == "rule":
            sels = [s.strip() for s in split_selector_list(nd.head)]
            is_root = all(s in (":root", "html", ":root,html") for s in sels)
            for m in CUSTOM_DECL_RE.finditer(nd.body):
                name, value = m.group(1), m.group(2).strip()
                if is_root and not in_media:
                    root[name] = value
                elif not is_root:
                    overridden.add(name)
            _collect_token_decls(nd.children, in_media, root, overridden)


def token_rebind_shim(tokens_css: str, selector: str) -> str:
    root: Dict[str, str] = {}
    overridden: set = set()
    _collect_token_decls(parse_css(tokens_css), False, root, overridden)
    if not overridden:
        return ""

    needs: List[str] = []
    seen = set(overridden)
    changed = True
    while changed:
        changed = False
        for name, value in root.items():
            if name in seen:
                continue
            refs = set(re.findall(r"var\(\s*(--[\w-]+)", value))
            if refs & seen:
                seen.add(name)
                needs.append(name)
                changed = True
    if not needs:
        return ""

    lines = [
        "@layer matrix {",
        "  /* Token rebind. Every root token that transitively depends on a value a",
        "     theme or density block re-points is re-declared HERE, on the element",
        "     that carries data-theme/data-density, because custom properties are",
        f"     substituted where they are declared. {len(needs)} token(s) rebound. */",
        f"  {selector} {{",
    ]
    for name in needs:
        lines.append(f"    {name}: {root[name]};")
    lines.append("  }")
    lines.append("}")
    return "\n".join(lines)


def detect_states(css_text: str, states: Iterable[str],
                  overrides: Dict[str, List[str]]) -> Dict[str, bool]:
    """Which states does this component's OWN stylesheet say anything about?

    Conservative on purpose. A focus ring can legitimately come from a global
    `:where(:focus-visible)` rule in base.css, so a miss here is a prompt, not a
    verdict — the cell still renders, and you look at it.
    """
    flat = strip_comments(css_text)
    result: Dict[str, bool] = {}
    for st in states:
        needles = overrides.get(st, STATE_MODEL.get(st, {}).get("detect"))
        if not needles:
            result[st] = True
            continue
        result[st] = any(nd in flat for nd in needles)
    return result


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------

class Component:
    def __init__(self, raw: Dict[str, Any], root: Path, index: int):
        where = f"components[{index}]"
        self.name = require_str(raw, "name", where)
        self.title = raw.get("title") or self.name.replace("-", " ").title()
        self.note = raw.get("note", "")
        self.css_paths = [resolve(root, p, where + ".css") for p in as_list(raw.get("css"))]
        if not self.css_paths:
            raise ManifestError(
                f"{where} ('{self.name}') declares no `css`. The generator reads the "
                f"component's own stylesheet to transpose its pseudo-class states and "
                f"to report state coverage; without it there is nothing to prove."
            )
        self.template = raw.get("template")
        self.template_id = raw.get("template_id")
        self.wrapper = raw.get("wrapper")  # e.g. "<table><tbody>{slot}</tbody></table>"
        self.variants = as_list(raw.get("variants")) or ["default"]
        self.sizes = as_list(raw.get("sizes")) or ["default"]
        self.states = as_list(raw.get("states")) or list(SEVEN_STATES)
        unknown = [s for s in self.states if s not in STATE_MODEL]
        if unknown:
            raise ManifestError(
                f"{where} ('{self.name}') lists unknown state(s) {unknown}. "
                f"Known states: {', '.join(SEVEN_STATES)}. If you meant a content "
                f"state (empty, partial, too-much-content), declare it as a content "
                f"fixture instead — content states are not interaction states."
            )
        self.state_detect = raw.get("state_detect", {})
        self.state_attrs = raw.get("state_attrs", {})
        self.stage_style = raw.get("stage_style", {}) or {}
        bad_keys = [k for k in self.stage_style if not k.startswith("--")]
        if bad_keys:
            raise ManifestError(
                f"{where} ('{self.name}') stage_style has non-custom-property key(s) "
                f"{bad_keys}. Law 4: inline style is legal only when every key is a "
                f"CSS custom property. Put the visual decision in the stylesheet and "
                f"pass a number through a socket instead."
            )
        content = raw.get("content", {"default": self.title})
        if isinstance(content, str):
            content = {"default": content}
        if not isinstance(content, dict) or not content:
            raise ManifestError(
                f"{where} ('{self.name}') `content` must be a string or a non-empty "
                f"object mapping fixture name -> HTML."
            )
        self.content: Dict[str, str] = {str(k): str(v) for k, v in content.items()}
        self.form_control = raw.get("form_control")

        self.css_text = ""
        for p in self.css_paths:
            self.css_text += read_text(p) + "\n"
        self.coverage = detect_states(self.css_text, self.states, self.state_detect)

    def resolved_template(self, templates: Dict[str, str]) -> str:
        if self.template:
            tpl = self.template
        else:
            key = self.template_id or self.name
            if key not in templates:
                raise ManifestError(
                    f"component '{self.name}' has neither an inline `template` nor a "
                    f"<template id=\"{key}\"> in the manifest's `templates` file. "
                    f"Known template ids: {', '.join(sorted(templates)) or '(none)'}."
                )
            tpl = templates[key]
        if "{content}" not in tpl and "{attrs}" not in tpl:
            raise ManifestError(
                f"component '{self.name}' template contains neither {{attrs}} nor "
                f"{{content}}. Without {{attrs}} the generator cannot apply state, "
                f"variant or size, so every cell would render identically."
            )
        return tpl

    def is_form_control(self, tpl: str) -> bool:
        if self.form_control is not None:
            return bool(self.form_control)
        return bool(FORM_TAG_RE.search(tpl))


class Manifest:
    def __init__(self, path: Path, root: Optional[Path] = None):
        self.path = path
        try:
            raw = json.loads(read_text(path))
        except json.JSONDecodeError as exc:
            raise ManifestError(f"{path}: not valid JSON — {exc}") from None
        if not isinstance(raw, dict):
            raise ManifestError(f"{path}: the manifest must be a JSON object.")
        schema = raw.get("$schema", SCHEMA)
        if schema != SCHEMA:
            raise ManifestError(
                f"{path}: unknown $schema '{schema}'. This generator speaks "
                f"'{SCHEMA}'."
            )
        self.root = root or path.parent
        self.project = raw.get("project", "Design system")
        self.tokens = resolve(self.root, raw["tokens"], "tokens") if raw.get("tokens") else None
        self.base = [resolve(self.root, p, "base") for p in as_list(raw.get("base"))]
        self.themes = as_list(raw.get("themes")) or list(DEFAULT_THEMES)
        self.densities = as_list(raw.get("densities")) or list(DEFAULT_DENSITIES)
        self.templates: Dict[str, str] = {}
        if raw.get("templates"):
            self.templates = read_templates(resolve(self.root, raw["templates"], "templates"))
        comps = raw.get("components")
        if not isinstance(comps, list) or not comps:
            raise ManifestError(
                f"{path}: `components` must be a non-empty array. The manifest is "
                f"hand-written on purpose — what you MEANT to support is the thing "
                f"under test."
            )
        self.components = [Component(c, self.root, i) for i, c in enumerate(comps)]
        names = [c.name for c in self.components]
        dupes = {n for n in names if names.count(n) > 1}
        if dupes:
            raise ManifestError(
                f"{path}: duplicate component name(s) {sorted(dupes)}. Cell ids are "
                f"derived from the name, so duplicates would collide baselines."
            )


def require_str(raw: Dict[str, Any], key: str, where: str) -> str:
    val = raw.get(key)
    if not isinstance(val, str) or not val.strip():
        raise ManifestError(f"{where}: `{key}` is required and must be a non-empty string.")
    return val.strip()


def as_list(val: Any) -> List[str]:
    if val is None:
        return []
    if isinstance(val, str):
        return [val]
    if isinstance(val, list):
        return [str(v) for v in val]
    raise ManifestError(f"expected a string or array, got {type(val).__name__}")


def resolve(root: Path, rel: str, where: str) -> Path:
    p = Path(rel)
    full = p if p.is_absolute() else (root / p)
    if not full.exists():
        raise ManifestError(f"{where}: no such file: {full}")
    return full


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ManifestError(f"cannot read {path}: {exc}") from None


TEMPLATE_RE = re.compile(
    r"<template[^>]*\bid\s*=\s*[\"']([^\"']+)[\"'][^>]*>(.*?)</template\s*>",
    re.I | re.S,
)


def read_templates(path: Path) -> Dict[str, str]:
    text = read_text(path)
    found = {m.group(1).strip(): m.group(2).strip() for m in TEMPLATE_RE.finditer(text)}
    if not found:
        raise ManifestError(
            f"{path}: no <template id=\"...\"> elements found. The templates file "
            f"holds one <template> per component, each containing the component's "
            f"markup with {{attrs}} and {{content}} placeholders."
        )
    return found


# ---------------------------------------------------------------------------
# The cell plan
# ---------------------------------------------------------------------------

class Cell:
    """One rendered instance. `cell_id` is the screenshot target and the baseline
    filename, so it must be unique in the document and stable across runs.

    The pass key is part of the id on purpose. Passes overlap at their defaults
    — the state pass and the density pass both contain (default state, default
    size, comfortable) — and two elements sharing a `data-cell-id` would mean a
    screenshot tool silently shoots the first one twice. Carrying the pass makes
    each visible cell its own target, at the cost of a handful of baselines that
    render identically. That trade is worth it: those duplicates are independent
    checks on the grid layout of each pass.
    """

    __slots__ = ("component", "pass_key", "state", "variant", "size", "density",
                 "theme", "fixture", "cell_id")

    def __init__(self, component: str, state: str, variant: str, size: str,
                 density: str, theme: str, fixture: str, pass_key: str = "x"):
        self.component = component
        self.pass_key = pass_key
        self.state = state
        self.variant = variant
        self.size = size
        self.density = density
        self.theme = theme
        self.fixture = fixture
        self.cell_id = "{c}--p_{p}--f_{f}--v_{v}--s_{s}--st_{st}--d_{d}--t_{t}".format(
            c=slug(component), p=slug(pass_key), f=slug(fixture), v=slug(variant),
            s=slug(size), st=slug(state), d=slug(density), t=slug(theme))


class Grid:
    """One rendered table: rows x columns, with the theme axis inside each cell."""

    def __init__(self, key: str, title: str, why: str,
                 row_label: str, rows: List[Tuple[str, str]],
                 col_label: str, cols: List[Tuple[str, str]],
                 make_cell):
        self.key = key
        self.title = title
        self.why = why
        self.row_label = row_label
        self.rows = rows
        self.col_label = col_label
        self.cols = cols
        self.make_cell = make_cell


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-") or "x"


def pick_default(options: Sequence[str], preferred: str) -> str:
    return preferred if preferred in options else options[0]


def plan(comp: Component, themes: List[str], densities: List[str],
         profile: str) -> List[Grid]:
    """Build the grids for one component.

    The pruning rule, implemented: render the cross-product only of the axes
    that can interfere. States interfere with variants (a ghost button's hover
    is a different problem from a primary's) and with themes (a hover overlay
    tuned for light surfaces vanishes on dark). Density interferes with size
    (both touch the same padding sockets) but not with state. Content fixtures
    interfere with density (a long string in a compact cell) but not with hover.
    """
    d_variant = comp.variants[0]
    d_size = comp.sizes[0]
    d_state = "default"
    d_density = pick_default(densities, "comfortable")
    d_fixture = next(iter(comp.content))
    grids: List[Grid] = []

    if profile == "full":
        for density in densities:
            for fixture in comp.content:
                cols = [(f"{v}|{s}", f"{v} · {s}")
                        for v in comp.variants for s in comp.sizes]
                grids.append(Grid(
                    key=f"full-{slug(density)}-{slug(fixture)}",
                    title=f"{density} · {fixture}",
                    why="Full cross product: every state against every variant and size.",
                    row_label="state",
                    rows=[(st, st) for st in comp.states],
                    col_label="variant · size",
                    cols=cols,
                    make_cell=lambda row, col, _d=density, _f=fixture: Cell(
                        comp.name, row, col.split("|")[0], col.split("|")[1],
                        _d, "@theme", _f),
                ))
        return grids

    # --- Pass 1: states x variants (x themes, inside every cell) ------------
    grids.append(Grid(
        key="state",
        title="States × variants",
        why=("A state is a token re-point, and a variant is a token re-point. "
             "They land on the same sockets, so they interfere. Read this pass "
             "for missing focus rings, hover overlays that vanish on dark, and "
             "disabled states that still look clickable."),
        row_label="state",
        rows=[(st, st) for st in comp.states],
        col_label="variant",
        cols=[(v, v) for v in comp.variants],
        make_cell=lambda row, col: Cell(comp.name, row, col, d_size,
                                        d_density, "@theme", d_fixture),
    ))

    # --- Pass 2: densities x (variant · size) -------------------------------
    grids.append(Grid(
        key="density",
        title="Densities × sizes",
        why=("Law 7 says density is a dial, not a second set of styles. Both "
             "density and size re-point the padding sockets, so they interfere. "
             "A cell whose box does not change between compact and spacious has "
             "a hardcoded value in it — that is the whole test."),
        row_label="density",
        rows=[(d, d) for d in densities],
        col_label="variant · size",
        cols=[(f"{v}|{s}", f"{v} · {s}") for v in comp.variants for s in comp.sizes],
        make_cell=lambda row, col: Cell(
            comp.name, d_state, col.split("|")[0], col.split("|")[1],
            row, "@theme", d_fixture),
    ))

    # --- Pass 3: content fixtures x densities -------------------------------
    if len(comp.content) > 1:
        grids.append(Grid(
            key="content",
            title="Content fixtures × densities",
            why=("Content states are not interaction states, and they are where "
                 "real products break. Long strings, empty values and translated "
                 "labels interact with the box, which means they interact with "
                 "density — and with nothing else on this sheet."),
            row_label="fixture",
            rows=[(f, f) for f in comp.content],
            col_label="density",
            cols=[(d, d) for d in densities],
            make_cell=lambda row, col: Cell(comp.name, d_state, d_variant,
                                            d_size, col, "@theme", row),
        ))
    return grids


# ---------------------------------------------------------------------------
# Markup
# ---------------------------------------------------------------------------

def esc(s: Any) -> str:
    return html.escape(str(s), quote=True)


def attrs_for(comp: Component, cell: Cell, is_form: bool) -> str:
    pairs: List[Tuple[str, str]] = []
    if cell.variant != "default":
        pairs.append(("data-variant", cell.variant))
    if cell.size != "default":
        pairs.append(("data-size", cell.size))

    spec = dict(STATE_MODEL[cell.state])
    state_attrs = dict(spec.get("attrs") or {})
    if cell.state == "disabled" and is_form:
        state_attrs.update(spec.get("form_attrs") or {})
    state_attrs.update(comp.state_attrs.get(cell.state, {}))
    for k, v in state_attrs.items():
        pairs.append((k, v))

    out = []
    for k, v in pairs:
        out.append(esc(k) if v == "" else f'{esc(k)}="{esc(v)}"')
    return " ".join(out)


def render_cell(comp: Component, cell: Cell, tpl: str, is_form: bool) -> str:
    body = tpl.replace("{attrs}", attrs_for(comp, cell, is_form))
    body = body.replace("{content}", comp.content[cell.fixture])
    body = body.replace("{cell_id}", cell.cell_id)
    if comp.wrapper:
        body = comp.wrapper.replace("{slot}", body)

    style = ";".join(f"{k}:{v}" for k, v in comp.stage_style.items())
    style_attr = f' style="{esc(style)}"' if style else ""
    missing = not comp.coverage.get(cell.state, True)
    flag = ('<span class="msheet__flag" title="No rule for this state in the '
            'component\'s own stylesheet.">no rule</span>') if missing else ""
    return (
        f'<div class="msheet__slot" data-axis-theme="{esc(cell.theme)}">'
        f'<div class="msheet__slot-tag">{esc(cell.theme)}{flag}</div>'
        f'<div class="msheet__stage" data-theme="{esc(cell.theme)}" '
        f'data-density="{esc(cell.density)}" data-cell-id="{esc(cell.cell_id)}"'
        f'{style_attr}>{body}</div>'
        f"</div>"
    )


class _IdSet(set):
    """A set that refuses a duplicate cell id, loudly.

    Two elements sharing a `data-cell-id` is not a cosmetic problem: a screenshot
    tool resolves the selector to the first match and shoots it twice, so one
    cell is never checked and its baseline is a lie. Fail at generation time.
    """

    def add(self, value):  # type: ignore[override]
        if value in self:
            raise ManifestError(
                f"internal: duplicate cell id '{value}'. Two cells would share one "
                f"screenshot target, so one of them would never be checked. This is "
                f"a generator bug — please report the manifest that produced it.")
        super().add(value)


def render_grid(comp: Component, grid: Grid, themes: List[str], tpl: str,
                is_form: bool, seen_ids: set) -> str:
    out: List[str] = []
    out.append(f'<section class="msheet__pass" data-pass="{esc(grid.key)}">')
    out.append(f'<h3 class="msheet__pass-title">{esc(grid.title)}</h3>')
    out.append(f'<p class="msheet__pass-why">{esc(grid.why)}</p>')
    out.append('<div class="msheet__grid" style="--msheet-columns:%d">' % len(grid.cols))
    out.append(f'<div class="msheet__corner">{esc(grid.row_label)} ╲ '
               f'{esc(grid.col_label)}</div>')
    for _, label in grid.cols:
        out.append(f'<div class="msheet__colhead">{esc(label)}</div>')
    for row_key, row_label in grid.rows:
        blurb = STATE_MODEL.get(row_key, {}).get("blurb", "")
        missing = grid.key == "state" and not comp.coverage.get(row_key, True)
        cls = "msheet__rowhead" + (" msheet__rowhead--gap" if missing else "")
        out.append(f'<div class="{cls}">'
                   f'<span class="msheet__rowhead-name">{esc(row_label)}</span>'
                   + (f'<span class="msheet__rowhead-blurb">{esc(blurb)}</span>'
                      if blurb else "")
                   + "</div>")
        for col_key, _ in grid.cols:
            proto = grid.make_cell(row_key, col_key)
            out.append('<div class="msheet__cell"'
                       f' data-axis-state="{esc(proto.state)}"'
                       f' data-axis-density="{esc(proto.density)}"'
                       f' data-axis-variant="{esc(proto.variant)}">')
            for theme in themes:
                cell = Cell(proto.component, proto.state, proto.variant,
                            proto.size, proto.density, theme, proto.fixture,
                            grid.key)
                seen_ids.add(cell.cell_id)
                out.append(render_cell(comp, cell, tpl, is_form))
            out.append("</div>")
    out.append("</div></section>")
    return "\n".join(out)


def render_coverage(components: List[Component]) -> str:
    out = ['<section class="msheet__coverage" id="coverage">',
           '<h2 class="msheet__h2">State coverage</h2>',
           '<p class="msheet__prose">Read from each component&rsquo;s own '
           'stylesheet. A gap here is a prompt, not a verdict &mdash; a focus '
           'ring can legitimately come from a global <code>:where(:focus-visible)</code> '
           'rule in <code>base.css</code>. Look at the cell and decide.</p>',
           '<div class="msheet__table" role="table">']
    header = ["component"] + SEVEN_STATES
    out.append('<div class="msheet__trow msheet__trow--head" role="row">')
    for h in header:
        out.append(f'<div class="msheet__tcell" role="columnheader">{esc(h)}</div>')
    out.append("</div>")
    for comp in components:
        out.append('<div class="msheet__trow" role="row">')
        out.append(f'<div class="msheet__tcell" role="rowheader">{esc(comp.title)}</div>')
        for st in SEVEN_STATES:
            if st not in comp.states:
                mark, cls = "—", "msheet__mark msheet__mark--na"
                title = "not declared in the manifest for this component"
            elif comp.coverage.get(st, True):
                mark, cls = "yes", "msheet__mark msheet__mark--ok"
                title = "a rule in this component's stylesheet matches this state"
            else:
                mark, cls = "no rule", "msheet__mark msheet__mark--gap"
                title = "no rule in this component's own stylesheet matches this state"
            out.append(f'<div class="msheet__tcell" role="cell">'
                       f'<span class="{cls}" title="{esc(title)}">{esc(mark)}</span></div>')
        out.append("</div>")
    out.append("</div></section>")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# The sheet's own stylesheet
# ---------------------------------------------------------------------------
# This file is a demonstration of the system it is testing, so it obeys the nine
# laws itself: every value resolves through a token, nothing sets an outer
# margin, the whole thing lives in one layer, and it reads Tier-2 roles only.
# A hardcoded value here is a bug. Verify with:
#     python -m scripts.generate_matrix ... --emit-css build/matrix-chrome.css
#     python -m scripts.audit_design build/matrix-chrome.css
#
# Deliberately NOT marked @generated: audit_design skips generated files, and a
# skipped audit proves nothing.

LAYER_STATEMENT = ("@layer reset, tokens, base, layout, components, utilities, "
                   "matrix, overrides;")

CHROME_CSS = r"""
/* Proof sheet chrome. Lives in its own `matrix` layer, declared after
   `utilities` and before `overrides`, so it can never out-rank the components
   under test by accident. That is the whole reason it is not in `components`.
   Written in the five-part component shape: sockets, structure, variants,
   states, parts. */

@layer matrix {

  /* ---- 1. SOCKETS ----------------------------------------------------- */
  .msheet {
    --msheet-gap: var(--gap-grouped);
    --msheet-inset: var(--pad-card);
    --msheet-well: var(--pad-well);
    --msheet-radius: var(--radius-lg);
    --msheet-bg: var(--bg-canvas);
    --msheet-fg: var(--fg-default);
    --msheet-rule: var(--border-subtle);
    --msheet-motion: var(--motion-hover);
    /* A grid column minimum is a container width, not a spacing decision, so
       it is derived from a breakpoint token rather than from the space scale. */
    --msheet-col-min: calc(var(--bp-sm) / 2);
    --msheet-columns: 1;

  /* ---- 2. STRUCTURE ---------------------------------------------------- */
    display: flex;
    flex-direction: column;
    gap: var(--gap-distinct);
    padding: var(--msheet-inset);
    background: var(--msheet-bg);
    color: var(--msheet-fg);
    font: var(--type-body);
  }

  .msheet__bar {
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    gap: var(--gap-separate);
    padding: var(--pad-block-md) var(--pad-inline-md);
    border: var(--stroke-default) solid var(--msheet-rule);
    border-radius: var(--msheet-radius);
    background: var(--bg-surface);
    box-shadow: var(--elevation-card);
  }

  .msheet__title { font: var(--type-h3); color: var(--fg-strong); }
  .msheet__meta  { font: var(--type-label); color: var(--fg-muted); }

  .msheet__controls {
    display: flex;
    flex-wrap: wrap;
    gap: var(--gap-related);
    align-items: center;
  }

  .msheet__control {
    display: flex;
    align-items: center;
    gap: var(--gap-tight);
    font: var(--type-label);
    color: var(--fg-muted);
  }

  .msheet__select {
    padding: var(--pad-block-xs) var(--pad-inline-sm);
    border: var(--stroke-default) solid var(--border-default);
    border-radius: var(--radius-md);
    background: var(--bg-surface);
    color: var(--fg-default);
    font: var(--type-ui);
  }

  .msheet__select:focus-visible {
    outline: var(--stroke-focus) solid transparent;
    box-shadow: var(--shadow-focus);
  }

  .msheet__toc {
    display: flex;
    flex-wrap: wrap;
    gap: var(--gap-related);
    font: var(--type-label);
  }

  .msheet__toc-link {
    padding: var(--pad-block-xs) var(--pad-inline-xs);
    border: var(--stroke-default) solid var(--msheet-rule);
    border-radius: var(--radius-full);
    color: var(--fg-link);
    text-decoration: none;
    transition: background-color var(--msheet-motion),
                border-color var(--msheet-motion);
  }

  .msheet__toc-link:hover { background: var(--bg-hover); }

  .msheet__toc-link:focus-visible {
    outline: var(--stroke-focus) solid transparent;
    box-shadow: var(--shadow-focus);
  }

  .msheet__component {
    display: flex;
    flex-direction: column;
    gap: var(--gap-separate);
  }

  .msheet__component-head {
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    gap: var(--gap-related);
    padding-block-end: var(--pad-block-sm);
    border-block-end: var(--stroke-thick) solid var(--border-default);
  }

  .msheet__h2 { font: var(--type-h2); color: var(--fg-strong); }
  .msheet__prose { font: var(--type-body); color: var(--fg-muted); max-inline-size: var(--measure-prose); }

  .msheet__pass {
    display: flex;
    flex-direction: column;
    gap: var(--gap-related);
  }

  .msheet__pass-title { font: var(--type-h4); color: var(--fg-strong); }
  .msheet__pass-why {
    font: var(--type-ui);
    color: var(--fg-muted);
    max-inline-size: var(--measure-prose);
  }

  /* The axis headers are sticky against the VIEWPORT, not against an inner
     scroller: an element with overflow-x also becomes a scrollport on the block
     axis, which silently kills `top: 0`. So the page scrolls, both ways. */
  .msheet__grid {
    display: grid;
    grid-template-columns:
      max-content repeat(var(--msheet-columns), minmax(var(--msheet-col-min), 1fr));
    gap: var(--stroke-hairline);
    background: var(--msheet-rule);
    border: var(--stroke-default) solid var(--msheet-rule);
    border-radius: var(--msheet-radius);
    overflow: clip;
  }

  .msheet__corner,
  .msheet__colhead,
  .msheet__rowhead {
    padding: var(--pad-block-sm) var(--pad-inline-sm);
    background: var(--bg-raised);
    font: var(--type-label);
    color: var(--fg-muted);
  }

  .msheet__corner {
    position: sticky;
    top: 0;
    left: 0;
    z-index: var(--z-raised);
    color: var(--fg-subtle);
  }

  .msheet__colhead {
    position: sticky;
    top: 0;
    z-index: var(--z-base);
    color: var(--fg-strong);
    text-align: center;
  }

  .msheet__rowhead {
    position: sticky;
    left: 0;
    z-index: var(--z-base);
    display: flex;
    flex-direction: column;
    gap: var(--gap-fused);
    max-inline-size: var(--measure-narrow);
  }

  .msheet__rowhead-name { color: var(--fg-strong); font: var(--type-ui); }
  .msheet__rowhead-blurb { color: var(--fg-subtle); font: var(--type-label); }

  .msheet__cell {
    display: flex;
    flex-wrap: wrap;
    gap: var(--stroke-hairline);
    background: var(--msheet-rule);
  }

  .msheet__slot {
    display: flex;
    flex-direction: column;
    flex: 1 1 var(--msheet-col-min);
    gap: var(--space-0);
  }

  .msheet__slot-tag {
    display: flex;
    gap: var(--gap-tight);
    align-items: center;
    padding: var(--pad-block-xs) var(--pad-inline-xs);
    background: var(--bg-sunken);
    color: var(--fg-subtle);
    font: var(--type-label);
  }

  /* The screenshot target. Everything outside it is chrome and must not end up
     in a baseline. */
  .msheet__stage {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--gap-related);
    flex: 1 1 auto;
    padding: var(--msheet-well);
    background: var(--bg-canvas);
    color: var(--fg-default);
  }

  .msheet__flag {
    padding: var(--pad-block-xs) var(--pad-inline-xs);
    border-radius: var(--radius-full);
    background: var(--bg-warning);
    color: var(--fg-on-inverse);
    font: var(--type-label);
  }

  .msheet__table {
    display: grid;
    gap: var(--stroke-hairline);
    background: var(--msheet-rule);
    border: var(--stroke-default) solid var(--msheet-rule);
    border-radius: var(--msheet-radius);
    overflow: clip;
  }

  .msheet__trow {
    display: grid;
    grid-template-columns: max-content repeat(7, 1fr);
    gap: var(--stroke-hairline);
    background: var(--msheet-rule);
  }

  .msheet__tcell {
    padding: var(--pad-block-sm) var(--pad-inline-sm);
    background: var(--bg-surface);
    font: var(--type-ui);
    color: var(--fg-default);
  }

  .msheet__trow--head .msheet__tcell {
    background: var(--bg-raised);
    color: var(--fg-muted);
    font: var(--type-label);
  }

  .msheet__mark {
    display: inline-flex;
    padding: var(--pad-block-xs) var(--pad-inline-xs);
    border-radius: var(--radius-full);
    font: var(--type-label);
  }

  /* ---- 3. VARIANTS ----------------------------------------------------- */
  .msheet__mark--ok  { background: var(--bg-success); color: var(--fg-on-inverse); }
  .msheet__mark--gap { background: var(--bg-danger);  color: var(--fg-on-accent); }
  .msheet__mark--na  { background: var(--bg-disabled); color: var(--fg-disabled); }

  .msheet__rowhead--gap { border-inline-start: var(--stroke-thick) solid var(--bg-danger); }

  /* ---- 4. STATES (of the sheet itself) --------------------------------- */
  /* Filters NARROW the default view. The default is everything visible, so a
     screenshot run that never touches a control still sees every cell. */
  .msheet__legend {
    display: flex;
    flex-wrap: wrap;
    gap: var(--gap-related);
    font: var(--type-label);
    color: var(--fg-muted);
  }

  /* ---- 5. PARTS -------------------------------------------------------- */
  .msheet__code {
    font: var(--type-code);
    color: var(--fg-muted);
  }

  @media print {
    /* Sticky positioning repeats headers on every printed page in some
       engines and drops them entirely in others. Neither is useful on paper. */
    .msheet__corner,
    .msheet__colhead,
    .msheet__rowhead { position: static; }
    .msheet__controls { display: none; }
    .msheet__component { break-inside: avoid; }
    .msheet__pass { break-inside: avoid; }
    .msheet__grid { break-inside: avoid; }
    .msheet { padding: var(--space-0); }
  }
}
"""


def filter_css(themes: List[str], densities: List[str], states: List[str]) -> str:
    """Emit the filter rules. Data-driven, so the axes come from the manifest."""
    lines = ["@layer matrix {"]
    for t in themes:
        others = [o for o in themes if o != t]
        for o in others:
            lines.append(f'  [data-theme-filter="{t}"] .msheet__slot'
                         f'[data-axis-theme="{o}"] {{ display: none; }}')
    for d in densities:
        lines.append(f'  [data-density-filter="{d}"] .msheet__cell'
                     f':not([data-axis-density="{d}"]) {{ display: none; }}')
    for s in states:
        lines.append(f'  [data-state-filter="{s}"] .msheet__cell'
                     f':not([data-axis-state="{s}"]) {{ display: none; }}')
    lines.append("}")
    return "\n".join(lines)


CONTROL_JS = """
(function () {
  var root = document.documentElement;
  function bind(id, attr) {
    var el = document.getElementById(id);
    if (!el) return;
    el.addEventListener('change', function () { root.setAttribute(attr, el.value); });
  }
  bind('f-theme', 'data-theme-filter');
  bind('f-density', 'data-density-filter');
  bind('f-state', 'data-state-filter');
  // A screenshot run must never inherit a filter someone left set. The tool
  // calls this before shooting; see snapshot_matrix.mjs.
  window.matrixShowAll = function () {
    root.setAttribute('data-theme-filter', 'all');
    root.setAttribute('data-density-filter', 'all');
    root.setAttribute('data-state-filter', 'all');
    ['f-theme', 'f-density', 'f-state'].forEach(function (id) {
      var el = document.getElementById(id);
      if (el) el.value = 'all';
    });
  };
}());
"""


def wrap_in_layer(css: str, layer: str) -> str:
    """Leave already-layered CSS alone; wrap the rest so nothing escapes."""
    if re.search(r"@layer\b", css):
        return css
    return f"@layer {layer} {{\n{css}\n}}\n"


def select_control(cid: str, label: str, options: List[str]) -> str:
    opts = ['<option value="all">all</option>']
    opts += [f'<option value="{esc(o)}">{esc(o)}</option>' for o in options]
    return (f'<label class="msheet__control" for="{esc(cid)}">{esc(label)}'
            f'<select class="msheet__select" id="{esc(cid)}">{"".join(opts)}'
            f"</select></label>")


def build_html(man: Manifest, comps: List[Component], themes: List[str],
               densities: List[str], profile: str, chrome: str) -> Tuple[str, int]:
    parts: List[str] = []
    total = 0
    seen_ids = _IdSet()
    for comp in comps:
        tpl = comp.resolved_template(man.templates)
        is_form = comp.is_form_control(tpl)
        gaps = [s for s in comp.states if not comp.coverage.get(s, True)]
        head = [f'<section class="msheet__component" id="c-{esc(slug(comp.name))}">',
                '<header class="msheet__component-head">',
                f'<h2 class="msheet__h2">{esc(comp.title)}</h2>',
                f'<span class="msheet__code">{esc(comp.css_paths[0].name)}</span>']
        if gaps:
            head.append('<span class="msheet__flag">no rule: '
                        + esc(", ".join(gaps)) + "</span>")
        head.append("</header>")
        if comp.note:
            head.append(f'<p class="msheet__prose">{esc(comp.note)}</p>')
        parts.extend(head)
        for grid in plan(comp, themes, densities, profile):
            parts.append(render_grid(comp, grid, themes, tpl, is_form, seen_ids))
            total += len(grid.rows) * len(grid.cols) * len(themes)
        parts.append("</section>")

    all_states = [s for s in SEVEN_STATES
                  if any(s in c.states for c in comps)]
    controls = "".join([
        select_control("f-theme", "theme", themes),
        select_control("f-density", "density", densities),
        select_control("f-state", "state", all_states),
    ])

    token_css = read_text(man.tokens) if man.tokens else ""
    base_css = "\n".join(read_text(p) for p in man.base)
    comp_css = "\n".join(wrap_in_layer(c.css_text, "components") for c in comps)
    shim = "\n".join(build_force_shim(parse_css(c.css_text)) for c in comps)

    toc = "".join(
        f'<a class="msheet__toc-link" href="#c-{esc(slug(c.name))}">{esc(c.title)}</a>'
        for c in comps)
    toc += '<a class="msheet__toc-link" href="#coverage">state coverage</a>'

    doc = f"""<!doctype html>
<html lang="en" data-theme-filter="all" data-density-filter="all" data-state-filter="all">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(man.project)} — component state matrix</title>
<style>{LAYER_STATEMENT}</style>
<style data-role="tokens">
{token_css}
</style>
<style data-role="base">
{wrap_in_layer(base_css, "base") if base_css.strip() else ""}
</style>
<style data-role="components">
{comp_css}
</style>
<style data-role="forced-state-shim">
/* Mirrors of every pseudo-class rule above, keyed on [data-force-state~="..."].
   Same specificity, same layer, later in document order — so it wins on order,
   not on a specificity fight. This is what makes a static state matrix possible. */
{wrap_in_layer(shim, "components") if shim.strip() else ""}
</style>
<style data-role="token-rebind">
{token_rebind_shim(token_css, ".msheet__stage") if token_css.strip() else ""}
</style>
<style data-role="matrix-chrome">
{chrome}
{filter_css(themes, densities, all_states)}
</style>
</head>
<body>
<div class="msheet">
  <header class="msheet__bar">
    <div>
      <div class="msheet__title">{esc(man.project)} — state matrix</div>
      <div class="msheet__meta">{len(comps)} component(s) · {total} cells ·
        profile <code class="msheet__code">{esc(profile)}</code> ·
        themes {esc(", ".join(themes))} · densities {esc(", ".join(densities))}</div>
    </div>
    <div class="msheet__controls">{controls}</div>
  </header>
  <nav class="msheet__toc" aria-label="Components">{toc}</nav>
  <p class="msheet__prose">Every cell is an independent screenshot target with a
    stable <code class="msheet__code">data-cell-id</code>. The controls above only
    narrow this view; the default shows every theme side by side so a screenshot
    run that touches nothing still sees everything.</p>
  <main>
{chr(10).join(parts)}
{render_coverage(comps)}
  </main>
</div>
<script>{CONTROL_JS}</script>
</body>
</html>
"""
    return doc, total


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def comma_list(val: str) -> List[str]:
    return [v.strip() for v in val.split(",") if v.strip()]


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        prog="python -m scripts.generate_matrix",
        description="Render every component at every state × density × theme as one "
                    "self-contained proof sheet.",
        epilog="Example: python -m scripts.generate_matrix matrix.json "
               "--out proof-sheet.html --only button --themes light,dark",
    )
    ap.add_argument("manifest", help="path to matrix.json")
    ap.add_argument("--out", "-o", required=True, help="path to write the HTML sheet")
    ap.add_argument("--root", help="base directory for relative manifest paths "
                                   "(default: the manifest's own directory)")
    ap.add_argument("--themes", type=comma_list,
                    help="comma-separated subset of the manifest's themes")
    ap.add_argument("--densities", type=comma_list,
                    help="comma-separated subset of the manifest's densities")
    ap.add_argument("--only", action="append", default=[],
                    help="render only this component (repeatable, or comma-separated)")
    ap.add_argument("--profile", choices=("pruned", "full"), default="pruned",
                    help="pruned renders only the axes that interfere (default); "
                         "full renders the complete cross product")
    ap.add_argument("--emit-css", metavar="FILE",
                    help="also write the sheet's own chrome stylesheet, so "
                         "audit_design.py can read it")
    ap.add_argument("--strict", action="store_true",
                    help="exit 1 if any component is missing a state rule")
    ap.add_argument("--quiet", action="store_true", help="suppress the summary")
    args = ap.parse_args(argv)

    try:
        mpath = Path(args.manifest)
        if not mpath.exists():
            raise ManifestError(f"no such manifest: {mpath}")
        man = Manifest(mpath, Path(args.root) if args.root else None)

        themes = args.themes or man.themes
        densities = args.densities or man.densities
        bad = [t for t in themes if t not in man.themes]
        if bad:
            raise ManifestError(
                f"--themes {bad} not declared in the manifest (has: "
                f"{', '.join(man.themes)}). A theme the tokens never re-point "
                f"would render identically to the default and prove nothing.")
        bad = [d for d in densities if d not in man.densities]
        if bad:
            raise ManifestError(
                f"--densities {bad} not declared in the manifest (has: "
                f"{', '.join(man.densities)}).")

        wanted: List[str] = []
        for chunk in args.only:
            wanted.extend(comma_list(chunk))
        comps = man.components
        if wanted:
            known = {c.name for c in comps}
            missing = [w for w in wanted if w not in known]
            if missing:
                raise ManifestError(
                    f"--only {missing}: no such component. Known: "
                    f"{', '.join(sorted(known))}")
            comps = [c for c in comps if c.name in wanted]

        doc, total = build_html(man, comps, themes, densities, args.profile,
                                CHROME_CSS)
        out = Path(args.out)
        if out.parent and not out.parent.exists():
            out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(doc, encoding="utf-8")

        if args.emit_css:
            cssp = Path(args.emit_css)
            if cssp.parent and not cssp.parent.exists():
                cssp.parent.mkdir(parents=True, exist_ok=True)
            cssp.write_text(
                LAYER_STATEMENT + "\n" + CHROME_CSS
                + filter_css(themes, densities, SEVEN_STATES) + "\n",
                encoding="utf-8")

    except ManifestError as exc:
        print(f"generate_matrix: {exc}", file=sys.stderr)
        return 2

    gaps: List[str] = []
    for c in comps:
        for s in c.states:
            if not c.coverage.get(s, True):
                gaps.append(f"{c.name}:{s}")

    if not args.quiet:
        print(f"generate_matrix: wrote {out} — {len(comps)} component(s), "
              f"{total} cells, profile {args.profile}.")
        print(f"  themes:    {', '.join(themes)}")
        print(f"  densities: {', '.join(densities)}")
        if args.emit_css:
            print(f"  chrome css: {args.emit_css} "
                  f"(run audit_design.py on it — the sheet obeys the laws too)")
        if gaps:
            print("  state coverage gaps (no rule in the component's own CSS):")
            for g in gaps:
                print(f"    - {g}")
        else:
            print("  state coverage: every declared state has a matching rule.")

    if args.strict and gaps:
        print(f"generate_matrix: --strict and {len(gaps)} state coverage gap(s).",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
