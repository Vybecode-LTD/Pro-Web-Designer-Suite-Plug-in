#!/usr/bin/env python3
"""apply_codemod.py — Phase 4: do the mechanical part, reviewably.

Reads the `mapping.json` that `cluster_values.py` produced and rewrites source
files: literal values become `var(--token)`, `font-size: 15px` becomes
`font: var(--type-body)`, `p-[13px]` becomes `p-related`.

It is DRY-RUN BY DEFAULT. It prints a unified diff and exits. `--apply` is the
only way it writes, and it refuses to write over a file that has uncommitted
changes, because the one thing worse than a bad codemod is a bad codemod mixed
into somebody's work in progress.

WHAT MAKES THIS NOT `sed`
-------------------------
  comments      `/* 13px grid */` is prose. Untouched.
  strings       `content: "12px"` is a label. Untouched.
  url()         `url(hero-13px.png)` is a filename. Untouched.
  calc()        `calc(100% - 13px)` IS a length. Rewritten, correctly.
  negatives     `-16px` becomes `calc(var(--space-4) * -1)`, which keeps the
                relationship instead of inventing a second negative token.
  shorthands    `padding: 9px 17px` maps slot 1 as block padding and slot 2 as
                inline padding, and replaces only the slots that have a token.
  font-size     rewritten as a whole declaration to `font: var(--type-*)`,
                and SKIPPED when the same rule sets font-weight/line-height,
                because the shorthand would silently reset them.
  atomicity     every file is written to a temp file in the same directory and
                moved into place only after it passes brace-balance and
                declaration-count checks. A file is never left half-written.

USAGE
-----
  # Look at what it would do. Writes nothing.
  python -m scripts.apply_codemod ./src --mapping proposal/mapping.json

  # One kind at a time, one commit each. This is the whole discipline.
  python -m scripts.apply_codemod ./src --mapping proposal/mapping.json \\
      --kind color --apply
  python -m scripts.apply_codemod ./src --mapping proposal/mapping.json \\
      --kind spacing --apply

  # Scope to one directory, leaf-first (see references/migration-strategies.md)
  python -m scripts.apply_codemod ./src --mapping proposal/mapping.json \\
      --only 'src/components/**' --apply

  # Counts only, no diff
  python -m scripts.apply_codemod ./src --mapping proposal/mapping.json --report

  # Skip only the confident replacements; leave the reviewable ones for a human
  python -m scripts.apply_codemod ./src --mapping proposal/mapping.json \\
      --skip-review --apply

Run it by path from the PROJECT root, so `./src` is the project's and nothing is
written into the plugin: `python <skill>/scripts/apply_codemod.py ./src -m mapping.json`.
The `-m scripts.apply_codemod` form above is for a project that vendored scripts/.

Exit codes: 0 clean (including a dry run), 1 if a file was skipped or a rule
could not be applied safely, 2 on bad invocation.
"""

from __future__ import annotations

import argparse
import difflib
import fnmatch
import json
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional, Sequence, Tuple

# The CSS scanner, the comment blanker and the normalizers live in
# extract_literals.py. One implementation, or the codemod and the census
# disagree about what a declaration is, which is the worst possible bug here.
# A sibling import would otherwise leave __pycache__ inside the installed
# plugin, which is read-only as far as a project is concerned.
sys.dont_write_bytecode = True
try:                                                # python -m scripts.apply_codemod
    from .extract_literals import (                 # type: ignore[import-not-found]
        blank_css_comments, blank_js_comments, blank_interpolations,
        match_template, mask_strings_and_urls, normalize_color,
        normalize_length, normalize_time, scan_css_declarations,
        STYLED_TAG_RE, CLASSNAME_RE, CLASSLIST_STRING_RE, CSS_EXT, JS_EXT,
        SKIP_DIRS, is_vendor, is_token_file, GENERATED_MARKERS, norm_path,
        Slot, split_slots, line_comments,
    )
except ImportError:                                 # python scripts/apply_codemod.py
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from extract_literals import (                  # type: ignore[no-redef]
        blank_css_comments, blank_js_comments, blank_interpolations,
        match_template, mask_strings_and_urls, normalize_color,
        normalize_length, normalize_time, scan_css_declarations,
        STYLED_TAG_RE, CLASSNAME_RE, CLASSLIST_STRING_RE, CSS_EXT, JS_EXT,
        SKIP_DIRS, is_vendor, is_token_file, GENERATED_MARKERS, norm_path,
        Slot, split_slots, line_comments,
    )

LENGTH_RE = re.compile(r"^(-?\d*\.?\d+)(px|rem|em|pt|pc|in|cm|mm|q)$", re.IGNORECASE)
TIME_RE = re.compile(r"^(\d*\.?\d+)(ms|s)$", re.IGNORECASE)
HEX_RE = re.compile(r"^#[0-9a-fA-F]{3,8}$")
INT_RE = re.compile(r"^-?\d+$")
FUNC_HEAD_RE = re.compile(r"^(rgba?|hsla?|hwb|lab|lch|oklab|oklch)\($", re.IGNORECASE)

# Properties whose rule block must not already own a font decision before a
# `font:` shorthand is dropped into it.
FONT_SIBLINGS = {"font", "font-weight", "font-family", "font-style",
                 "font-variant", "font-stretch", "line-height"}


# ---------------------------------------------------------------------------
# Slot classification — the part that keeps shorthands honest
# ---------------------------------------------------------------------------

BOX_SIDE_CLASSES = {
    # slot count -> class per slot, for `padding`
    1: ["pad-all"],
    2: ["pad-block", "pad-inline"],
    3: ["pad-block", "pad-inline", "pad-block"],
    4: ["pad-block", "pad-inline", "pad-block", "pad-inline"],
}

PROP_SLOT_CLASS = {
    "gap": "gap", "row-gap": "gap", "column-gap": "gap", "grid-gap": "gap",
    "grid-row-gap": "gap", "grid-column-gap": "gap",
    "margin": "gap", "margin-top": "gap", "margin-right": "gap",
    "margin-bottom": "gap", "margin-left": "gap", "margin-block": "gap",
    "margin-block-start": "gap", "margin-block-end": "gap",
    "margin-inline": "gap", "margin-inline-start": "gap",
    "margin-inline-end": "gap",
    "padding-left": "pad-inline", "padding-right": "pad-inline",
    "padding-inline": "pad-inline", "padding-inline-start": "pad-inline",
    "padding-inline-end": "pad-inline",
    "padding-top": "pad-block", "padding-bottom": "pad-block",
    "padding-block": "pad-block", "padding-block-start": "pad-block",
    "padding-block-end": "pad-block",
    "color": "fg", "fill": "fg", "caret-color": "fg",
    "text-decoration-color": "fg", "text-emphasis-color": "fg",
    "background": "bg", "background-color": "bg", "accent-color": "bg",
    "border-color": "border", "border-top-color": "border",
    "border-right-color": "border", "border-bottom-color": "border",
    "border-left-color": "border", "border-block-color": "border",
    "border-inline-color": "border", "outline-color": "border",
    "column-rule-color": "border", "stroke": "border",
    "box-shadow": "shadow", "text-shadow": "shadow",
    "z-index": "z-index", "letter-spacing": "tracking",
    "width": "size", "height": "size", "max-width": "size",
    "min-width": "size", "max-height": "size", "min-height": "size",
}
RADIUS_PROPS = {"border-radius", "border-top-left-radius",
                "border-top-right-radius", "border-bottom-left-radius",
                "border-bottom-right-radius", "border-start-start-radius",
                "border-start-end-radius", "border-end-start-radius",
                "border-end-end-radius"}
BORDER_SHORTHAND = {"border", "border-top", "border-right", "border-bottom",
                    "border-left", "border-block", "border-inline", "outline",
                    "column-rule"}
BORDER_WIDTH_PROPS = {"border-width", "border-top-width", "border-right-width",
                      "border-bottom-width", "border-left-width",
                      "outline-width", "column-rule-width"}
MOTION_PROPS = {"transition", "animation", "transition-duration",
                "animation-duration", "transition-timing-function",
                "animation-timing-function", "transition-delay",
                "animation-delay"}


MATH_FN_RE = re.compile(r"^(calc|min|max|clamp)\(", re.IGNORECASE)


def expand_math(slots: Sequence[Slot], value: str) -> List[Tuple[Slot, int]]:
    """Flatten `calc(...)` into its leaf operands, keeping absolute offsets.

    `calc(100% - 13px)` is one slot to the splitter and two values to a
    designer. The 13px inside it is as much a spacing decision as a bare one,
    and it is exactly the kind of literal that survives every migration because
    grep-based tools cannot see inside the parentheses.

    Returns (leaf slot, index of the slot it came from) so the caller can keep
    using the outer slot's property class.
    """
    out: List[Tuple[Slot, int]] = []
    for idx, slot in enumerate(slots):
        if not MATH_FN_RE.match(slot.text):
            out.append((slot, idx))
            continue
        open_paren = slot.text.index("(")
        body_start = slot.start + open_paren + 1
        body_end = slot.end - 1 if slot.text.endswith(")") else slot.end
        body = value[body_start:body_end]
        for leaf in split_slots(body):
            leaf_abs = Slot(leaf.text, body_start + leaf.start,
                            body_start + leaf.end)
            if MATH_FN_RE.match(leaf.text):
                out.extend((s2, idx) for s2, _ in
                           expand_math([leaf_abs], value))
            elif leaf.text not in {"+", "-", "*", "/"}:
                out.append((leaf_abs, idx))
    return out


def slot_classes(prop: str, slots: Sequence[Slot]) -> List[str]:
    """The prop class for each slot. This is the whole shorthand story."""
    n = len(slots)
    if prop == "padding":
        # Position is decided by the SLOT COUNT, including `0` and `auto`.
        # `padding: 0 18px` is two slots, so the 18px is inline padding — count
        # only the slots that carry a unit and you read it as all-sides, which
        # is how a codemod turns a page gutter into a card inset.
        pattern = BOX_SIDE_CLASSES.get(n, ["pad-all"] * n)
        return [pattern[i] if i < len(pattern) else "pad-all"
                for i in range(n)]
    if prop in RADIUS_PROPS:
        return ["radius"] * n
    if prop in BORDER_WIDTH_PROPS:
        return ["stroke"] * n
    if prop in BORDER_SHORTHAND:
        out = []
        for s in slots:
            if LENGTH_RE.match(s.text):
                out.append("stroke")
            elif is_color_slot(s.text):
                out.append("border")
            else:
                out.append("")
        return out
    if prop in MOTION_PROPS:
        out = []
        for s in slots:
            if TIME_RE.match(s.text):
                out.append("duration")
            elif s.text.lower().startswith(("cubic-bezier(", "steps(")):
                out.append("easing")
            else:
                out.append("")
        return out
    if prop in {"box-shadow", "text-shadow"}:
        return ["shadow"] * n       # matched as a whole value, not per slot
    base = PROP_SLOT_CLASS.get(prop, "")
    if base in {"fg", "bg", "border"}:
        return [base if is_color_slot(s.text) else "" for s in slots]
    if base:
        return [base] * n
    return [""] * n


def is_color_slot(text: str) -> bool:
    t = text.strip().lower()
    return bool(HEX_RE.match(t)) or bool(
        re.match(r"^(rgba?|hsla?|hwb|lab|lch|oklab|oklch)\(", t))


def canon_slot(text: str) -> List[str]:
    """Every canonical key a slot could match a rule by."""
    t = text.strip()
    keys = [t.lower()]
    if HEX_RE.match(t) or re.match(r"^(rgba?|hsla?)\(", t, re.IGNORECASE):
        keys.append(normalize_color(t))
    m = LENGTH_RE.match(t)
    if m:
        keys.append(normalize_length(m.group(1), m.group(2)))
    m = TIME_RE.match(t)
    if m:
        keys.append(normalize_time(m.group(1), m.group(2)))
    keys.append(re.sub(r"\s+", " ", t.lower()))
    seen, out = set(), []
    for k in keys:
        if k not in seen:
            seen.add(k)
            out.append(k)
    return out


def is_negative(text: str) -> bool:
    m = LENGTH_RE.match(text.strip())
    return bool(m and float(m.group(1)) < 0)


# ---------------------------------------------------------------------------
# The mapping
# ---------------------------------------------------------------------------

@dataclass
class Mapping:
    value_rules: Dict[Tuple[str, str], dict] = field(default_factory=dict)
    decl_rules: Dict[Tuple[str, str], dict] = field(default_factory=dict)
    motion_rules: Dict[str, dict] = field(default_factory=dict)
    tw_rules: Dict[str, dict] = field(default_factory=dict)
    kinds: set = field(default_factory=set)

    @classmethod
    def load(cls, path: Path, kinds: Optional[Sequence[str]],
             skip_review: bool) -> "Mapping":
        # Exit 2, like every other bad invocation: `raise SystemExit("msg")`
        # exits 1, which the docs reserve for "a file was skipped".
        try:
            payload = json.loads(path.read_bytes())
        except (OSError, ValueError) as exc:
            print(f"apply_codemod: {path} is not readable JSON ({exc}).\n"
                  f"Generate it with:\n"
                  f"  python -m scripts.cluster_values literals.json -o ./proposal",
                  file=sys.stderr)
            raise SystemExit(2)
        schema = payload.get("schema") if isinstance(payload, dict) else None
        if str(schema or "").split("@")[0] != "design-token-migration/mapping":
            print(f"apply_codemod: {path} is not a codemod mapping "
                  f"(schema={schema!r}). It must come from cluster_values.py.",
                  file=sys.stderr)
            raise SystemExit(2)
        m = cls()
        wanted = {k.lower() for k in kinds} if kinds else None
        for rule in payload.get("rules", []):
            m.kinds.add(rule["kind"])          # before filtering, so the error
            if wanted and rule["kind"].lower() not in wanted:   # message can
                continue                                        # list them
            if skip_review and rule.get("confidence") == "review":
                continue
            scope = rule.get("scope", "value")
            if scope == "tailwind":
                for match in rule["match"]:
                    m.tw_rules[match] = rule
            elif scope == "motion":
                for match in rule["match"]:
                    for key in canon_slot(match):
                        m.motion_rules.setdefault(key, rule)
            elif scope == "declaration":
                for prop in rule.get("props") or ["font-size"]:
                    for match in rule["match"]:
                        for key in canon_slot(match):
                            m.decl_rules[(prop, key)] = rule
            else:
                classes = rule.get("prop_classes") or [""]
                for klass in classes:
                    for match in rule["match"]:
                        for key in canon_slot(match):
                            m.value_rules.setdefault((klass, key), rule)
        return m

    def value_rule(self, klass: str, slot: str) -> Tuple[Optional[dict], bool]:
        """(rule, negate). `negate` is true only when the slot was negative AND
        the rule matched its ABSOLUTE value — `-13px` matching a `13px` rule.
        A rule that matches `-0.03em` on the nose already carries the sign, and
        wrapping it in `calc(… * -1)` would flip it back."""
        keys = canon_slot(slot)
        for key in keys:
            hit = self.value_rules.get((klass, key))
            if hit:
                return hit, False
        if is_negative(slot):
            for key in canon_slot(slot.strip().lstrip("-")):
                hit = self.value_rules.get((klass, key))
                if hit:
                    return hit, True
        return None, False

    def motion_rule(self, duration: str) -> Optional[dict]:
        for key in canon_slot(duration):
            hit = self.motion_rules.get(key)
            if hit:
                return hit
        return None

    def decl_rule(self, prop: str, value: str) -> Optional[dict]:
        for key in canon_slot(value):
            hit = self.decl_rules.get((prop, key))
            if hit:
                return hit
        return None


# ---------------------------------------------------------------------------
# Edits
# ---------------------------------------------------------------------------

@dataclass
class Edit:
    start: int
    end: int
    replacement: str
    rule_id: str
    kind: str
    line: int
    before: str


@dataclass
class Skip:
    file: str
    line: int
    reason: str
    snippet: str


def replacement_for(rule: dict, negate: bool) -> str:
    """`var(--token)`, or the negation form when the original was negative.

    A negative margin that cancels a known token is legal under Law 2 in
    exactly this shape. `-16px` -> `-var(--space-4)` is not valid CSS;
    `calc(var(--space-4) * -1)` is, and it keeps the relationship visible.
    """
    text = rule["replacement"]
    if negate and text.startswith("var("):
        return f"calc({text} * -1)"
    return text


def selector_key(selector: str) -> str:
    return " ".join(selector.split())


LONGHAND_SIDES = {
    "top": ("top",), "right": ("right",), "bottom": ("bottom",), "left": ("left",),
    "block": ("top", "bottom"), "inline": ("left", "right"),
    "block-start": ("top",), "block-end": ("bottom",),
    "inline-start": ("left",), "inline-end": ("right",),      # left to right
}
SHORTHAND_SIDES = {
    1: [("top", "right", "bottom", "left")],
    2: [("top", "bottom"), ("left", "right")],
    3: [("top",), ("left", "right"), ("bottom",)],
    4: [("top",), ("right",), ("bottom",), ("left",)],
}


def box_sides(prop: str, count: int, index: int) -> Tuple[str, ...]:
    """The sides one slot of a padding or margin sets."""
    if "-" in prop:
        side = prop.split("-", 1)[1]
        sides = LONGHAND_SIDES.get(side, ())
        if side in ("block", "inline") and count == 2:        # start, then end
            return sides[index:index + 1]
        return sides
    slots = SHORTHAND_SIDES.get(count, [])
    return slots[index] if index < len(slots) else ()


def selector_list(selector: str) -> List[str]:
    """`.a, .panel` as its members, split at top-level commas only."""
    out, depth, start = [], 0, 0
    for i, ch in enumerate(selector):
        depth += {"(": 1, ")": -1}.get(ch, 0)
        if ch == "," and depth == 0:
            out.append(selector[start:i])
            start = i + 1
    out.append(selector[start:])
    return [selector_key(s) for s in out if s.strip()]


# {selector: {side: [(block, at-rule context, !important, the value's keys,
#                     its rule or None)]}}
Pads = Dict[str, Dict[str, List[Tuple[int, tuple, bool, set, Optional[dict]]]]]


def padding_rules(text: str, decls: Sequence, mapping: Mapping) -> Pads:
    """Every padding declaration in the file, by selector (each member of a
    selector list) and side, in source order, with the block it sits in."""
    out: Pads = {}
    for d in decls:
        if not d.prop.startswith("padding"):
            continue
        value = text[d.value_offset:d.value_offset + len(d.value)]
        # `!important` is not a slot: `padding: 16px !important` is one side value.
        important = "!important" in value.lower()
        if important:
            value = value[:value.lower().index("!important")]
        slots = split_slots(mask_strings_and_urls(value))
        for i, (slot, klass) in enumerate(zip(slots, slot_classes(d.prop, slots))):
            real = value[slot.start:slot.end]
            rule = mapping.value_rule(klass, real)[0] if klass else None
            for member in selector_list(d.selector):
                for side in box_sides(d.prop, len(slots), i):
                    out.setdefault(member, {}).setdefault(side, []).append(
                        (d.block_start, d.context, important, set(canon_slot(real)), rule))
    return out


def parent_contexts(member: str, nested_in: str) -> List[List[str]]:
    """Where one member of a margin's selector can find the padding it cancels,
    in order: the rule it is nested in (every member of that rule's list), the
    left side of a descendant or child selector (`.panel > .bleed`), and a BEM
    element's block (`.card__media` in `.card`)."""
    out = [selector_list(nested_in)] if nested_in else []
    m = re.search(r"\s*(?:>|\s)\s*(?=[^\s>]+$)", member)
    if m:
        out.append([member[:m.start()]])
    m = re.match(r"^(\.[A-Za-z][\w-]*?)__[\w-]+$", member)
    if m:
        out.append([m.group(1)])
    return out


def cancelled_padding(d, slot: str, sides: Sequence[str], pads: Pads) -> Optional[dict]:
    """The rule of the padding a negative margin cancels: its parent rule's
    padding of the same size on each side the margin sets, all of them mapping
    by one rule, for every member of the margin's selector list
    (extraction-and-clustering.md §10). A negative cancel must read the token the
    padding reads, or the bleed breaks the day the padding changes; `-16px` in a
    margin alone clusters to a gap token."""
    keys = set(canon_slot(slot.strip().lstrip("-")))

    def padding(parent: str, side: str):
        # Only a padding set in one block of the whole file is certain: the last
        # `!important` declaration there wins, or else the last one. Set in two
        # blocks, which wins depends on the @media that applies, the @layer, or
        # the order, so keep the gap token. A padding inside another media
        # query never applies here.
        found = pads.get(parent, {}).get(side, [])
        if not found or len({entry[0] for entry in found}) > 1:
            return None
        _, context, _, keys, rule = ([e for e in found if e[2]] or found)[-1]
        return (keys, rule) if d.context[:len(context)] == context else None

    def in_parent(parent: str) -> Optional[dict]:
        found = [padding(parent, side) for side in sides]
        if not found or not all(f and f[1] and f[0] & keys for f in found):
            return None
        rules = {id(f[1]) for f in found}
        return found[0][1] if len(rules) == 1 else None

    picked = []
    for member in selector_list(d.selector):
        hit = None
        for group in parent_contexts(member, d.parent):
            hits = [in_parent(p) for p in group]
            if hits and all(hits) and len({id(h) for h in hits}) == 1:
                hit = hits[0]
                break
        if hit is None:
            return None
        picked.append(hit)
    return picked[0] if picked and len({id(h) for h in picked}) == 1 else None


def plan_css(text: str, mapping: Mapping, *, base: int = 0,
             source_name: str = "", skips: Optional[List[Skip]] = None,
             blanked: Optional[str] = None, slash_comments: bool = True) -> List[Edit]:
    """Compute the edits for one CSS body. `text` is the REAL source."""
    edits: List[Edit] = []
    skips = skips if skips is not None else []
    scan_text = blanked if blanked is not None else blank_css_comments(text, slash_comments)

    decls = list(scan_css_declarations(scan_text))
    # Group declarations by their enclosing block so a `font:` shorthand can
    # check what else the rule already decides.
    block_props: Dict[int, set] = {}
    for d in decls:
        block_props.setdefault(d.block_start, set()).add(d.prop)

    def line_of(off: int) -> int:
        return text.count("\n", 0, off) + 1

    pads = padding_rules(text, decls, mapping)

    for d in decls:
        prop = d.prop
        if prop.startswith("--"):
            continue                    # a token file's own declarations
        value = text[d.value_offset:d.value_offset + len(d.value)]
        if "!important" in value.lower():
            i = value.lower().index("!important")
            value_eff, tail = value[:i], value[i:]
        else:
            value_eff, tail = value, ""
        del tail

        # ---- whole-declaration rewrites (font-size -> a --type-* role) -----
        drule = mapping.decl_rule(prop, value_eff.strip())
        if drule:
            # Only a rewrite INTO the `font` shorthand resets the longhands
            # beside it. A colour rename (`color: var(--fg-faint)`, from
            # deprecate.py) keeps its property and resets nothing.
            siblings = block_props.get(d.block_start, set()) - {prop}
            into_font = drule["replacement"].startswith("font:") and prop != "font"
            clash = siblings & FONT_SIBLINGS if into_font else set()
            if clash:
                skips.append(Skip(
                    source_name, line_of(d.decl_offset),
                    f"`font: var({drule['token']})` would reset "
                    f"{', '.join(sorted(clash))} declared in the same rule — "
                    f"delete those first, the --type-* role carries them",
                    text[d.decl_offset:d.value_offset + len(d.value)].strip()))
            else:
                edits.append(Edit(                  # up to `!important`, which stays
                    base + d.decl_offset,
                    base + d.value_offset + len(value_eff.rstrip()),
                    drule["replacement"], drule["id"], drule["kind"],
                    line_of(d.decl_offset),
                    text[d.decl_offset:d.value_offset + len(d.value)]))
            continue

        # ---- whole-value rewrites (shadows) --------------------------------
        if prop in {"box-shadow", "text-shadow"}:
            rule, _neg = mapping.value_rule(
                "shadow", re.sub(r"\s+", " ", value_eff.strip()))
            if rule:
                edits.append(Edit(
                    base + d.value_offset,
                    base + d.value_offset + len(value_eff.rstrip()),
                    rule["replacement"], rule["id"], rule["kind"],
                    line_of(d.value_offset), value_eff.strip()))
            continue

        masked = mask_strings_and_urls(value_eff)

        # ---- transition / animation: collapse to a --motion-* PAIR ---------
        if prop in {"transition", "animation"} and mapping.motion_rules:
            handled, layer_edits = plan_motion(
                masked, value_eff, d.value_offset, base, line_of, mapping)
            edits.extend(layer_edits)
            if handled:
                continue

        # ---- per-slot rewrites ---------------------------------------------
        slots = split_slots(masked)
        classes = slot_classes(prop, slots)
        for slot, parent in expand_math(slots, masked):
            klass = classes[parent] if parent < len(classes) else ""
            if not klass:
                continue
            real = value_eff[slot.start:slot.end]
            if not real.strip() or "var(--" in real:
                continue
            rule, negate = mapping.value_rule(klass, real)
            if not rule:
                continue
            if negate and prop.startswith("margin"):
                rule = cancelled_padding(d, real, box_sides(prop, len(slots), parent), pads) or rule
            edits.append(Edit(
                base + d.value_offset + slot.start,
                base + d.value_offset + slot.end,
                replacement_for(rule, negate), rule["id"], rule["kind"],
                line_of(d.value_offset + slot.start), real))
    return edits


EASING_KEYWORD = {"ease", "ease-in", "ease-out", "ease-in-out", "linear",
                  "step-start", "step-end"}


def is_easing(text: str) -> bool:
    t = text.strip().lower()
    return t in EASING_KEYWORD or t.startswith(("cubic-bezier(", "steps("))


def plan_motion(masked: str, value: str, value_offset: int, base: int,
                line_of, mapping: Mapping) -> Tuple[bool, List[Edit]]:
    """Rewrite `transition: opacity 250ms ease-out` to `opacity var(--motion-enter)`.

    Per comma layer, because `transition: a 180ms ease, b 180ms ease` is two
    transitions and replacing across the comma produces one broken one. A layer
    with no recognised duration is left for the per-slot pass; the caller only
    treats the declaration as handled when EVERY layer converted, so a partial
    result never half-rewrites a shorthand.
    """
    edits: List[Edit] = []
    offset = 0
    layers = []
    depth, start = 0, 0
    for i, ch in enumerate(masked):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        elif ch == "," and depth == 0:
            layers.append((start, i))
            start = i + 1
    layers.append((start, len(masked)))
    del offset

    all_converted = True
    for lo, hi in layers:
        body = masked[lo:hi]
        slots = [Slot(s.text, s.start + lo, s.end + lo) for s in split_slots(body)]
        times = [s for s in slots if TIME_RE.match(s.text)]
        if len(times) != 1:
            all_converted = False
            continue
        rule = mapping.motion_rule(times[0].text)
        if not rule:
            all_converted = False
            continue
        easings = [s for s in slots if is_easing(s.text)]
        span_start = times[0].start
        span_end = max([times[0].end] + [e.end for e in easings if e.start > times[0].start])
        edits.append(Edit(
            base + value_offset + span_start, base + value_offset + span_end,
            rule["replacement"], rule["id"], rule["kind"],
            line_of(value_offset + span_start),
            value[span_start:span_end]))
    return all_converted, edits


def plan_js(text: str, mapping: Mapping, source_name: str,
            skips: List[Skip]) -> List[Edit]:
    """styled-components bodies get the CSS treatment; classNames get the
    Tailwind rules. JSX inline styles are deliberately left alone — Law 4 says
    the DECLARATION has to move into a stylesheet, and a codemod that invents
    class names is a codemod nobody reviews."""
    edits: List[Edit] = []
    clean = blank_js_comments(text)
    consumed: List[Tuple[int, int]] = []

    for m in STYLED_TAG_RE.finditer(clean):
        open_tick = clean.index("`", m.end() - 1)
        close_tick = match_template(clean, open_tick)
        body_start, body_end = open_tick + 1, close_tick
        consumed.append((m.start(), min(close_tick + 1, len(clean))))
        body = text[body_start:body_end]
        blanked = blank_interpolations(blank_css_comments(body))
        edits.extend(plan_css(body, mapping, base=body_start,
                              source_name=source_name, skips=skips,
                              blanked=blanked))

    seen: set = set()
    for sm in list(CLASSNAME_RE.finditer(clean)) + \
            list(CLASSLIST_STRING_RE.finditer(clean)):
        idx = sm.lastindex or 1
        group = sm.group(idx)
        if group is None:
            continue
        base = sm.start(idx)
        if any(a <= base < b for a, b in consumed):
            continue
        for tok, rule in mapping.tw_rules.items():
            for hit in re.finditer(re.escape(tok) + r"(?![\w\[-])", group):
                span = (base + hit.start(), base + hit.end())
                if span in seen:
                    continue
                seen.add(span)
                edits.append(Edit(
                    span[0], span[1], rule["replacement"], rule["id"],
                    rule["kind"], text.count("\n", 0, span[0]) + 1, tok))
    return edits


def splice(text: str, edits: Sequence[Edit]) -> str:
    out = text
    for e in sorted(edits, key=lambda e: -e.start):
        out = out[:e.start] + e.replacement + out[e.end:]
    return out


def overlapping(edits: Sequence[Edit]) -> Optional[Tuple[Edit, Edit]]:
    ordered = sorted(edits, key=lambda e: (e.start, e.end))
    for a, b in zip(ordered, ordered[1:]):
        if b.start < a.end:
            return (a, b)
    return None


def structurally_sound(before: str, after: str, is_css: bool,
                       slash_comments: bool = True) -> Optional[str]:
    """Cheap invariants that catch a corrupting rewrite before it lands.

    Not a validator — a tripwire. If a replacement ever unbalances a brace or
    loses a declaration, the file does not get written and the run fails loudly
    instead of leaving somebody a broken stylesheet on a Friday.
    """
    # Braces and semicolons are structure and must be untouched. Parentheses
    # are NOT: every `13px` -> `var(--space-3)` adds a pair. They only have to
    # stay balanced.
    for ch in "{};":
        if before.count(ch) != after.count(ch):
            return f"`{ch}` count changed {before.count(ch)} -> {after.count(ch)}"
    if after.count("(") != after.count(")"):
        return (f"unbalanced parentheses after rewrite "
                f"({after.count('(')} open, {after.count(')')} close)")
    if is_css:
        n_before = len(list(scan_css_declarations(blank_css_comments(before, slash_comments))))
        n_after = len(list(scan_css_declarations(blank_css_comments(after, slash_comments))))
        if n_before != n_after:
            return f"declaration count changed {n_before} -> {n_after}"
    return None


# ---------------------------------------------------------------------------
# Git
# ---------------------------------------------------------------------------

def git_root(path: Path) -> Optional[Path]:
    # Git prints paths as UTF-8 whatever the platform; text=True would decode
    # them with the locale (cp1252 on Windows) and mangle or crash on them.
    try:
        out = subprocess.run(
            ["git", "-C", str(path if path.is_dir() else path.parent),
             "rev-parse", "--show-toplevel"],
            capture_output=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    top = out.stdout.decode("utf-8", "surrogateescape").strip()
    return Path(top) if out.returncode == 0 and top else None


def dirty_files(root: Path) -> Optional[set]:
    """Paths with uncommitted changes, relative to the repo root."""
    # -uall, because `git status --porcelain` collapses a directory of
    # untracked files into a single `?? src/` line, and a guard that compares
    # file paths against `src/` protects nothing.
    # -z, because without it git quotes and octal-escapes any name with a
    # non-ASCII character ("caf\303\251.css"), which never matches the file.
    try:
        out = subprocess.run(
            ["git", "-C", str(root), "status", "--porcelain", "-z",
             "--untracked-files=all"],
            capture_output=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    dirty = set()
    fields = iter(out.stdout.decode("utf-8", "surrogateescape").split("\0"))
    for raw in fields:
        if len(raw) < 4:
            continue
        status, name = raw[:2], raw[3:]
        if "R" in status or "C" in status:
            next(fields, None)        # -z gives "XY new\0old\0"; skip the old name
        entry = (root / name).resolve()
        dirty.add(str(entry))
        if entry.is_dir():
            dirty.update(str(p) for p in entry.rglob("*") if p.is_file())
    return dirty


# ---------------------------------------------------------------------------
# Walking
# ---------------------------------------------------------------------------

def iter_files(paths: Sequence[str], only: Sequence[str], *,
               include_vendor: bool = False,
               vendor_skipped: List[Path] | None = None) -> Iterator[Path]:
    """A file named explicitly is always rewritten (the user asked for it);
    inside a folder, vendor files are left alone unless --include-vendor, and
    collected in `vendor_skipped` so the summary can say so."""
    for raw in paths:
        p = Path(raw)
        candidates: List[Path]
        explicit = p.is_file()
        if explicit:
            candidates = [p]
        else:
            candidates = []
            for root, dirs, files in os.walk(p):
                dirs[:] = [d for d in dirs
                           if d not in SKIP_DIRS and not d.startswith(".")]
                candidates.extend(Path(root) / f for f in sorted(files))
        for fp in candidates:
            if fp.suffix.lower() not in CSS_EXT | JS_EXT:
                continue
            if is_token_file(fp):
                continue
            if not (explicit or include_vendor) and is_vendor(fp):
                if vendor_skipped is not None:
                    vendor_skipped.append(fp)
                continue
            if only and not any(
                    fnmatch.fnmatch(norm_path(fp), pat) or
                    fnmatch.fnmatch(norm_path(fp.resolve()), pat)
                    for pat in only):
                continue
            yield fp


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

@dataclass
class FileResult:
    path: Path
    edits: List[Edit]
    before: str
    after: str
    written: bool = False
    skipped: str = ""


def process(fp: Path, mapping: Mapping, skips: List[Skip]) -> Optional[FileResult]:
    try:
        text = fp.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        skips.append(Skip(norm_path(fp), 0, f"unreadable: {exc}", ""))
        return None
    if any(mark in text[:800] for mark in GENERATED_MARKERS):
        return None
    is_css = fp.suffix.lower() in CSS_EXT
    try:
        edits = (plan_css(text, mapping, source_name=norm_path(fp), skips=skips,
                          slash_comments=line_comments(fp))
                 if is_css else plan_js(text, mapping, norm_path(fp), skips))
    except Exception as exc:                          # noqa: BLE001
        skips.append(Skip(norm_path(fp), 0,
                          f"planning failed ({type(exc).__name__}: {exc}) — "
                          f"file left untouched", ""))
        return None
    if not edits:
        return None
    clash = overlapping(edits)
    if clash:
        skips.append(Skip(norm_path(fp), clash[0].line,
                          f"two rules ({clash[0].rule_id}, {clash[1].rule_id}) "
                          f"want the same text — file left untouched", ""))
        return None
    after = splice(text, edits)
    problem = structurally_sound(text, after, is_css, line_comments(fp))
    if problem:
        skips.append(Skip(norm_path(fp), 0,
                          f"rewrite failed its safety check ({problem}) — "
                          f"file left untouched", ""))
        return None
    return FileResult(fp, edits, text, after)


def write_atomically(fp: Path, content: str) -> None:
    """Temp file in the same directory, fsync, then os.replace.

    Same directory because os.replace is only atomic within a filesystem, and
    /tmp is frequently a different one.
    """
    fd, tmp = tempfile.mkstemp(dir=str(fp.parent), prefix=f".{fp.name}.",
                               suffix=".codemod")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
            fh.write(content)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, fp)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="python -m scripts.apply_codemod",
        description="Phase 4 of a token migration: apply the mapping. "
                    "Dry-run by default — nothing is written without --apply.",
        epilog="Apply one --kind at a time and commit between batches. A "
               "500-file diff gets rubber-stamped; a 40-file diff gets read.",
    )
    ap.add_argument("paths", nargs="+", help="files or directories to rewrite")
    ap.add_argument("-m", "--mapping", required=True, metavar="FILE",
                    help="mapping.json from cluster_values.py")
    ap.add_argument("--apply", action="store_true",
                    help="actually write the files (default: dry run)")
    ap.add_argument("--kind", action="append", metavar="KIND",
                    help="only this kind of replacement (repeatable): "
                         "spacing, color, type, radius, stroke, duration, "
                         "easing, shadow, z-index, tracking")
    ap.add_argument("--only", action="append", metavar="GLOB", default=[],
                    help="only files matching this glob (repeatable), e.g. "
                         "'src/components/**'")
    ap.add_argument("--skip-review", action="store_true",
                    help="skip rules marked `review` — the ones that move a "
                         "value far enough to see")
    ap.add_argument("--report", action="store_true",
                    help="counts per file instead of the diff")
    ap.add_argument("--no-diff", action="store_true",
                    help="suppress the diff (implies a summary only)")
    ap.add_argument("--force", action="store_true",
                    help="write over files with uncommitted changes")
    ap.add_argument("--include-vendor", action="store_true",
                    help="also rewrite vendor/third-party files found inside a folder "
                         "(a file named explicitly is always rewritten)")
    return ap


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    mapping_path = Path(args.mapping)
    if not mapping_path.exists():
        print(f"apply_codemod: no such mapping: {mapping_path}\n"
              f"Generate one with:\n"
              f"  python -m scripts.extract_literals ./src --format json -o literals.json\n"
              f"  python -m scripts.cluster_values literals.json -o ./proposal",
              file=sys.stderr)
        return 2
    missing = [p for p in args.paths if not Path(p).exists()]
    if missing:
        print(f"apply_codemod: no such path: {', '.join(missing)}", file=sys.stderr)
        return 2

    mapping = Mapping.load(mapping_path, args.kind, args.skip_review)
    if not (mapping.value_rules or mapping.decl_rules or mapping.tw_rules):
        print(f"apply_codemod: the mapping has no rules matching "
              f"--kind {', '.join(args.kind or [])}. Kinds present: "
              f"{', '.join(sorted(mapping.kinds)) or '(none)'}.", file=sys.stderr)
        return 2

    root = git_root(Path(args.paths[0]))
    dirty: set = set()
    if root:
        found = dirty_files(root)
        if found is None:
            print("apply_codemod: git status failed; treating every file as clean.",
                  file=sys.stderr)
        else:
            dirty = found
    elif args.apply:
        print("apply_codemod: not a git repository. There is no undo here — "
              "make a copy before you --apply.", file=sys.stderr)

    skips: List[Skip] = []
    results: List[FileResult] = []
    vendor_skipped: List[Path] = []
    for fp in iter_files(args.paths, args.only, include_vendor=args.include_vendor,
                         vendor_skipped=vendor_skipped):
        res = process(fp, mapping, skips)
        if not res:
            continue
        if str(fp.resolve()) in dirty and not args.force:
            res.skipped = ("has uncommitted changes — commit or stash first, "
                           "or pass --force")
            skips.append(Skip(norm_path(fp), 0, res.skipped, ""))
            results.append(res)
            continue
        if args.apply:
            try:
                write_atomically(fp, res.after)
                res.written = True
            except OSError as exc:
                res.skipped = f"could not write: {exc}"
                skips.append(Skip(norm_path(fp), 0, res.skipped, ""))
        results.append(res)

    # ---- output ------------------------------------------------------------
    touched = [r for r in results if not r.skipped]
    total_edits = sum(len(r.edits) for r in touched)

    if not args.report and not args.no_diff:
        for r in touched:
            diff = difflib.unified_diff(
                r.before.splitlines(keepends=True),
                r.after.splitlines(keepends=True),
                fromfile=f"a/{norm_path(r.path)}",
                tofile=f"b/{norm_path(r.path)}", n=2)
            sys.stdout.writelines(diff)

    print()
    print("=" * 72)
    print("CODEMOD " + ("APPLIED" if args.apply else "DRY RUN — nothing written"))
    print("=" * 72)
    by_kind: Dict[str, int] = {}
    for r in touched:
        for e in r.edits:
            by_kind[e.kind] = by_kind.get(e.kind, 0) + 1
    for r in sorted(results, key=lambda r: norm_path(r.path)):
        if r.skipped:
            print(f"  SKIP  {norm_path(r.path)}  — {r.skipped}")
            continue
        kinds: Dict[str, int] = {}
        for e in r.edits:
            kinds[e.kind] = kinds.get(e.kind, 0) + 1
        detail = ", ".join(f"{k} x{v}" for k, v in sorted(kinds.items()))
        print(f"  {len(r.edits):>4}  {norm_path(r.path)}  ({detail})")
    print()
    print(f"  {total_edits} replacement(s) in {len(touched)} file(s): "
          + ", ".join(f"{k} x{v}" for k, v in sorted(by_kind.items())))

    line_skips = [s for s in skips if s.line]
    file_skips = [s for s in skips if not s.line]
    if line_skips:
        print()
        print(f"  {len(line_skips)} replacement(s) were NOT made, on purpose:")
        for s in line_skips[:30]:
            print(f"    {s.file}:{s.line}  {s.reason}")
            if s.snippet:
                print(f"        {s.snippet[:100]}")
        if len(line_skips) > 30:
            print(f"    … and {len(line_skips) - 30} more.")
    untouched = [s for s in file_skips
                 if not any(r.skipped and norm_path(r.path) == s.file
                            for r in results)]
    if untouched:
        print()
        print(f"  {len(untouched)} file(s) were left alone:")
        for s in untouched:
            print(f"    {s.file}  {s.reason}")
    if vendor_skipped:
        print()
        print(f"  {len(vendor_skipped)} vendor file(s) not rewritten (you layer vendor "
              f"CSS, you do not migrate it; --include-vendor, or name the file):")
        for fp in vendor_skipped[:10]:
            print(f"    {norm_path(fp)}")

    if not args.apply and total_edits:
        print()
        print("  Re-run with --apply to write. Do it one --kind at a time and "
              "commit between batches.")
    print()

    return 1 if any(r.skipped for r in results) or line_skips else 0


if __name__ == "__main__":
    # A Windows pipe (git hook, CI, `> file`) defaults to the ANSI code page,
    # where printing →, Δ or ✓ raises UnicodeEncodeError. Consoles and
    # Claude Code already use UTF-8 and are left alone.
    for _stream in (sys.stdout, sys.stderr):
        if getattr(_stream, "encoding", "utf-8").lower() not in ("utf-8", "utf8"):
            _stream.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
