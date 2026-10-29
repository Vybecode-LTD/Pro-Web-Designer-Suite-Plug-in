"""sync_email_tokens.py — a project's email-tokens.json, projected from its tokens.css.

`email-tokens.json` is the email-safe projection of the token system, not a
second one (N56, P62). This script writes it from the project's token files
(tokens.css, contract.json or DTCG, as every gate reads them) and the email
file before it, so a brand change in tokens.css reaches the email build
without anyone retyping a hex:

  kept          an entry whose `from` still matches what tokens.css says is
                left as it is, value and note included. That is how an
                email decision survives: the 32px h1, the 16px button label.
  projected     an entry whose source moved is projected again: oklch() and
                rgb() to hex, rem to px, calc() at --density: 1, clamp() to
                its minimum, a font stack cut to its websafe families, a
                `--type-*` shorthand to its size, line and weight. A role that
                points at a token keeps pointing at whichever one tokens.css
                names. A note stays only while the value it describes does.
  added         a token the email file has never seen takes its family's
                treatment: `--danger-400` is projected as `--danger-500` is,
                `--dur-loop` dropped as `--dur-base` is. One with no family is
                projected when it has an email form, and stops the run when
                it has none.
  removed       an entry whose token tokens.css no longer declares is taken
                out, so a template that reads it fails the build. The
                `email-only` entries and the email's own type roles stay.

Every `contrast` note ("4.91:1 on --bg-accent") is measured again from the
hex values the build will write, and a pair under 4.5:1 is reported. Read
references/email-workflow.md §12 before the first run on a hand-made file.

USAGE
-----
  python scripts/sync_email_tokens.py
  python scripts/sync_email_tokens.py --tokens src/styles/tokens.css --out emails/email-tokens.json
  python scripts/sync_email_tokens.py --check          # in CI: exit 1 when the file is stale

`--tokens` defaults to the project's `.design-suite.json` `tokens`, and
`--out` to its `emailTokens`. `--base`, the email file whose decisions are
kept, defaults to `--out` when that exists, else the skill's own
`assets/email-tokens.json`.

Exit codes: 0 written, or up to date · 1 written, with a measured pair under
4.5:1; with --check, the file is not the projection · 2 nothing written: bad
invocation, an unreadable file, token files not read whole (a resolver's
missing source), a value with no email form, or a reference to a token the
projection lacks.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
try:                                              # python -m scripts.sync_email_tokens
    from .project_config import (ConfigError, _css_blocks, project_config, read_text, read_tokens,
                                 guard_outputs)
except ImportError:                               # python scripts/sync_email_tokens.py
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from project_config import (ConfigError, _css_blocks,  # type: ignore[no-redef]
                                project_config, read_text, read_tokens, guard_outputs)

SKILL_TOKENS = Path(__file__).resolve().parent.parent / "assets" / "email-tokens.json"
FLOOR = 4.5                         # every measured pair in the file is text on its background
ROOT_PX = 16
TRIPLE = re.compile(r"^(--type-[a-z0-9-]+?)-(size|line|weight)$")
BARE_VAR = re.compile(r"^var\(\s*(--[A-Za-z0-9_-]+)\s*\)$")
ENTRY_ORDER = ("value", "tier", "status", "from", "reason", "contrast", "note")

GENERIC_STACKS = {
    "sans-serif": ["-apple-system", "BlinkMacSystemFont", "Segoe UI", "Roboto", "Helvetica Neue",
                   "Arial", "sans-serif"],
    "serif": ["Georgia", "Times New Roman", "Times", "serif"],
    "monospace": ["Consolas", "SF Mono", "Menlo", "Monaco", "Courier New", "monospace"],
}
GENERIC_OF = {"sans-serif": "sans-serif", "serif": "serif", "monospace": "monospace",
              "ui-sans-serif": "sans-serif", "system-ui": "sans-serif", "ui-serif": "serif",
              "ui-monospace": "monospace"}
# Families installed with the systems the client matrix runs on. A web font is
# none of these: it does not load in the Word engine or most of Gmail.
WEBSAFE = {f.lower() for f in (
    "-apple-system", "BlinkMacSystemFont", "Segoe UI", "Roboto", "Helvetica Neue", "Helvetica",
    "Arial", "Arial Black", "Verdana", "Tahoma", "Trebuchet MS", "Lucida Grande",
    "Lucida Sans Unicode", "Gill Sans", "Optima", "Calibri", "Candara", "Impact",
    "Georgia", "Times New Roman", "Times", "Palatino", "Palatino Linotype", "Book Antiqua",
    "Cambria", "Garamond", "Baskerville",
    "Consolas", "SF Mono", "SFMono-Regular", "Menlo", "Monaco", "Courier New", "Courier",
    "Lucida Console", "Liberation Mono")} | set(GENERIC_STACKS)

POLICY_COLOUR = ("Every colour notation but hex (rgb(), hsl(), a 3-digit hex) is written as the 6-digit "
                 "sRGB hex of the same colour: it is the one notation every client in the matrix reads.")


class Unprojectable(ValueError):
    """A value with no email form."""


# ---------------------------------------------------------------------------
# Values: resolving var(), and the email form of each kind of value
# ---------------------------------------------------------------------------

def split_top(text: str, sep: str) -> list[str]:
    """`text` split at `sep` outside brackets and quotes."""
    parts, depth, quote, start = [], 0, "", 0
    for i, ch in enumerate(text):
        if quote:
            quote = "" if ch == quote else quote
        elif ch in "\"'":
            quote = ch
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif depth == 0 and (ch == sep or (sep == " " and ch.isspace())):
            parts.append(text[start:i])
            start = i + 1
    parts.append(text[start:])
    return [p.strip() for p in parts if p.strip()]


def resolve(value: str, tokens: dict[str, str], depth: int = 0) -> str:
    """`value` with every var() replaced by what tokens.css declares."""
    if depth > 24:
        raise Unprojectable("a var() cycle in %s" % value)
    out, i = [], 0
    while True:
        at = value.find("var(", i)
        if at < 0:
            out.append(value[i:])
            return " ".join("".join(out).split())
        out.append(value[i:at])
        level, end = 0, at + 3
        while end < len(value):
            level += {"(": 1, ")": -1}.get(value[end], 0)
            if level == 0:
                break
            end += 1
        name, _, fallback = value[at + 4:end].partition(",")
        name = name.strip()
        if name in tokens:
            out.append(resolve(tokens[name], tokens, depth + 1))
        elif fallback.strip():
            out.append(resolve(fallback.strip(), tokens, depth + 1))
        else:
            raise Unprojectable("var(%s) is not declared" % name)
        i = end + 1


def number(x: float) -> str:
    text = ("%.2f" % x).rstrip("0").rstrip(".")
    return "0" if text in ("", "-0") else text


LENGTH = re.compile(r"^(-?(?:\d+\.?\d*|\.\d+))(px|rem)?$")


def calc_value(expr: str) -> tuple[float, bool]:
    """A calc() body as (number, is a length in px): + - * / and brackets
    over px, rem and plain numbers."""
    tokens = re.findall(r"\d*\.?\d+(?:px|rem)?|[-+*/()]|calc\(", expr.replace(" ", ""))
    if "".join(tokens) != expr.replace(" ", ""):
        raise Unprojectable("calc(%s) holds a unit or function email cannot resolve" % expr)
    pos = 0

    def atom() -> tuple[float, bool]:
        nonlocal pos
        tok = tokens[pos]
        pos += 1
        if tok in ("(", "calc("):
            got = sum_()
            pos += 1                                # the ")"
            return got
        if tok == "-":
            n, px = atom()
            return -n, px
        m = LENGTH.match(tok)
        if not m:
            raise Unprojectable("calc(%s) cannot be resolved" % expr)
        n = float(m.group(1))
        return (n * ROOT_PX, True) if m.group(2) == "rem" else (n, m.group(2) == "px")

    def product() -> tuple[float, bool]:
        nonlocal pos
        n, px = atom()
        while pos < len(tokens) and tokens[pos] in "*/":
            op = tokens[pos]
            pos += 1
            m, mpx = atom()
            if (px and mpx) or (op == "/" and (mpx or m == 0)):
                raise Unprojectable("calc(%s) cannot be resolved" % expr)
            n, px = (n * m if op == "*" else n / m), px or mpx
        return n, px

    def sum_() -> tuple[float, bool]:
        nonlocal pos
        n, px = product()
        while pos < len(tokens) and tokens[pos] in "+-":
            op = tokens[pos]
            pos += 1
            m, mpx = product()
            if px != mpx and n and m:
                raise Unprojectable("calc(%s) adds a length to a number" % expr)
            n, px = (n + m if op == "+" else n - m), px or mpx
        return n, px

    try:
        got = sum_()
    except IndexError:
        raise Unprojectable("calc(%s) cannot be resolved" % expr) from None
    if pos != len(tokens):
        raise Unprojectable("calc(%s) cannot be resolved" % expr)
    return got


def length(value: str) -> tuple[str, str | None]:
    """A length's email form, and the reason when its notation changed."""
    m = LENGTH.match(value)
    if m and m.group(2) == "rem":
        return number(float(m.group(1)) * ROOT_PX) + "px", "rem-to-px"
    if m:
        return value, None
    head = value.split("(", 1)[0].lower()
    if head == "calc" and value.endswith(")"):
        n, px = calc_value(value[5:-1])
        return number(n) + ("px" if px else ""), "calc-removed"
    if head == "clamp" and value.endswith(")"):
        args = split_top(value[6:-1], ",")
        if len(args) != 3:
            raise Unprojectable("%s is not a clamp() of three values" % value)
        low, _ = length(args[0])
        return low, "clamp-to-fixed"
    raise Unprojectable("%s has no email form" % value)


def _linear_to_srgb(c: float) -> float:
    c = max(0.0, min(1.0, c))
    return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055


def _srgb_to_linear(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _channel(text: str, scale: float) -> float:
    try:
        return float(text[:-1]) / 100 if text.endswith("%") else float(text) / scale
    except ValueError:
        raise Unprojectable("%r is not a number a colour channel can take" % text) from None


HUE = re.compile(r"^(-?(?:\d+\.?\d*|\.\d+))(deg|turn|rad|grad)?$")
DEGREES = {None: 1.0, "deg": 1.0, "turn": 360.0, "rad": 180 / math.pi, "grad": 0.9}


def _hue(text: str) -> float:
    """A hue in degrees, in any of CSS's angle units (CodeRabbit on #209)."""
    m = HUE.match(text)
    if not m:
        raise Unprojectable("%r is not a hue" % text)
    return float(m.group(1)) * DEGREES[m.group(2)]


def _opaque(alpha: str | None, value: str) -> None:
    if alpha is not None and _channel(alpha.strip(), 1) < 1:
        raise Unprojectable("%s is translucent, and email has no transparency to show it" % value)


def to_hex(value: str) -> tuple[str, str | None]:
    """A colour as #rrggbb, and the reason when its notation changed."""
    text = value.strip().lower()
    m = re.match(r"^#([0-9a-f]{3,8})$", text)
    if m and len(m.group(1)) in (3, 4, 6, 8):
        h = m.group(1)
        if len(h) in (3, 4):
            h = "".join(c * 2 for c in h)
        if h[6:] not in ("", "ff"):
            raise Unprojectable("%s is translucent, and email has no transparency to show it" % value)
        return "#" + h[:6], (None if text == "#" + h[:6] else "colour-to-hex")
    fn = re.match(r"^(oklch|rgba?|hsla?)\((.*)\)$", text)
    if not fn:
        raise Unprojectable("%s is not a colour email can write" % value)
    body, alpha = fn.group(2), None
    if "/" in body:
        body, alpha = body.split("/", 1)
    parts = [p for p in re.split(r"[\s,]+", body.strip()) if p]
    if fn.group(1).endswith("a") and len(parts) == 4:
        parts, alpha = parts[:3], parts[3]
    if len(parts) != 3:
        raise Unprojectable("%s is not a colour email can write" % value)
    _opaque(alpha, value)
    parts = ["0" if p == "none" else p for p in parts]
    if fn.group(1) == "oklch":
        L = _channel(parts[0], 1)
        C = _channel(parts[1], 1) * (0.4 if parts[1].endswith("%") else 1)    # 100% is 0.4
        h = math.radians(_hue(parts[2]))
        a, b = C * math.cos(h), C * math.sin(h)
        l_ = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3
        m_ = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3
        s_ = (L - 0.0894841775 * a - 1.2914855480 * b) ** 3
        rgb = [_linear_to_srgb(v) for v in (
            +4.0767416621 * l_ - 3.3077115913 * m_ + 0.2309699292 * s_,
            -1.2684380046 * l_ + 2.6097574011 * m_ - 0.3413193965 * s_,
            -0.0041960863 * l_ - 0.7034186147 * m_ + 1.7076147010 * s_)]
        reason = "oklch-to-hex"
    elif fn.group(1).startswith("rgb"):
        rgb = [_channel(p, 255) for p in parts]
        reason = "colour-to-hex"
    else:
        hue = _hue(parts[0]) % 360
        sat, light = _channel(parts[1], 100), _channel(parts[2], 100)

        def hsl(n: int) -> float:                   # CSS Color 4's hslToRgb
            k = (n + hue / 30) % 12
            return light - sat * min(light, 1 - light) * max(-1, min(k - 3, 9 - k, 1))
        rgb = [hsl(0), hsl(8), hsl(4)]
        reason = "colour-to-hex"
    return "#" + "".join("%02x" % round(max(0.0, min(1.0, c)) * 255) for c in rgb), reason


def contrast(fg: str, bg: str) -> float:
    def lum(h: str) -> float:
        r, g, b = (_srgb_to_linear(int(h[i:i + 2], 16) / 255) for i in (1, 3, 5))
        return 0.2126 * r + 0.7152 * g + 0.0722 * b
    hi, lo = sorted((lum(fg), lum(bg)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def font_stack(value: str) -> str:
    """The websafe families of a stack, in its order, then the email stack of
    its generic family for whatever the project's own did not name."""
    families = [f.strip().strip("\"'") for f in split_top(value, ",")]
    generic = next((GENERIC_OF[f.lower()] for f in reversed(families) if f.lower() in GENERIC_OF),
                   "sans-serif")
    kept = [f for f in families if f.lower() in WEBSAFE and f.lower() not in GENERIC_STACKS]
    for f in GENERIC_STACKS[generic]:
        if f.lower() not in {k.lower() for k in kept}:
            kept.append(f)
    return ", ".join("'%s'" % f if " " in f else f for f in kept)


def shorthand(value: str) -> tuple[str, str, str]:
    """A resolved `font` shorthand's weight, size and line height. The slash
    may have spaces round it (`2.75rem / 1.15`; Codex on #209)."""
    tight, depth, after = [], 0, False
    for ch in value:
        depth += {"(": 1, ")": -1}.get(ch, 0)
        if ch == "/" and depth == 0:
            while tight and tight[-1].isspace():
                tight.pop()
            tight.append(ch)
            after = True
        elif not (after and ch.isspace()):
            tight.append(ch)
            after = False
    words = split_top("".join(tight), " ")
    at = next((i for i, w in enumerate(words) if len(split_top(w, "/")) == 2), None)
    if at is None:
        raise Unprojectable("%s is not a font shorthand with a line height" % value)
    size, line = split_top(words[at], "/")
    weight = next((w for w in words[:at] if re.fullmatch(r"\d{3}|bold|normal", w)), "400")
    return {"bold": "700", "normal": "400"}.get(weight, weight), size, line


def project(name: str, source: str) -> dict:
    """The email form of a resolved value: value, status, and reason."""
    if name.startswith("--font-"):
        stack = font_stack(source)
        return {"value": stack, "status": "substituted", "reason": "webfont-to-stack"}
    try:
        value, reason = to_hex(source)
    except Unprojectable:
        if re.match(r"^(#|oklch\(|rgba?\(|hsla?\()", source.strip().lower()):
            raise
        if re.fullmatch(r"-?(?:\d+\.?\d*|\.\d+)(em)?", source):
            value, reason = source, None                # a number, or em tracking: email keeps both
        else:
            value, reason = length(source)
    return {"value": value, "status": "substituted" if reason else "survives",
            **({"reason": reason} if reason else {})}


def triple(source: str, part: str) -> dict:
    """One of a type role's three entries, from its resolved shorthand."""
    weight, size, line = shorthand(source)
    px, _ = length(size)
    if not px.endswith("px"):
        raise Unprojectable("%s's size, %s, is not a length" % (source, size))
    if part == "weight":
        return {"value": weight, "status": "substituted", "reason": "shorthand-font-removed"}
    if part == "size":
        return {"value": px, "status": "substituted", "reason": "shorthand-font-removed"}
    if re.fullmatch(r"\d*\.?\d+", line):
        return {"value": number(math.floor(float(px[:-2]) * float(line) + 0.5)) + "px",
                "status": "substituted", "reason": "shorthand-font-removed"}
    line_px, _ = length(line)
    return {"value": line_px, "status": "substituted", "reason": "shorthand-font-removed"}


def triple_from(source: str) -> str:
    """What a type triple was projected from: weight size/line, no family."""
    weight, size, line = shorthand(source)
    return "%s %s/%s" % (weight, size, line)


# ---------------------------------------------------------------------------
# The projection
# ---------------------------------------------------------------------------

def family(name: str) -> str:
    """`--danger-` for `--danger-400`; nothing for `--density`."""
    head = name.rsplit("-", 1)[0]
    return head + "-" if head.startswith("--") and len(head) > 2 else ""


class Projection:
    """The new email file's sections, and what changed against the base."""

    def __init__(self, base: dict, tokens: dict[str, str], tiers: dict[str, int],
                 order: dict[str, int], groups: set[str]):
        self.base, self.css, self.tiers, self.order = base, tokens, tiers, order
        self.entries: list[list] = [[n, e, n in groups] for n, e in base.get("tokens", {}).items()]
        self.dropped: list[list] = [[n, e, n in groups] for n, e in base.get("dropped", {}).items()]
        self.kept = 0
        self.again: list[tuple[str, str, str]] = []
        self.added: list[tuple[str, str]] = []
        self.removed: list[str] = []
        self.measured: list[tuple[str, str, str]] = []
        self.under: list[str] = []
        self.problems: list[str] = []
        self.reasons: set[str] = set()

    # -- where an entry's value comes from -------------------------------
    def source_of(self, name: str) -> str | None:
        if name in self.css:
            return name
        m = TRIPLE.match(name)
        return m.group(1) if m and m.group(1) in self.css else None

    def provenance(self, name: str, source: str) -> str:
        resolved = resolve(self.css[source], self.css)
        return triple_from(resolved) if source != name else resolved

    # -- the passes -----------------------------------------------------------
    def run(self) -> None:
        # New tokens first, so that a role tokens.css re-points at one finds it.
        names = {n for n, _, _ in self.entries}
        dropped = {n for n, _, _ in self.dropped}
        shorthands = {TRIPLE.match(n).group(1) for n in names if TRIPLE.match(n)}
        base = [item for item in self.entries]
        for name in sorted(self.css, key=lambda n: self.order.get(n, 1 << 30)):
            if name in names or name in dropped or name in shorthands:
                continue
            try:
                self.add(name, names, dropped)
            except Unprojectable as exc:
                self.problems.append("%s: %s, and the email file has no treatment for it: project it "
                                     "or add it to `dropped` with a reason" % (name, exc))
        for item in base:
            name, entry = item[0], item[1]
            source = self.source_of(name)
            if source is None:
                if entry.get("status") == "email-only" or TRIPLE.match(name):
                    self.kept += 1
                else:
                    self.remove(item)
                    names.discard(name)
                continue
            try:
                self.update(item, source, names, dropped)
            except Unprojectable as exc:
                self.problems.append("%s: %s" % (name, exc))
        self.check_references()
        self.measure()

    def update(self, item: list, source: str, names: set[str], dropped: set[str]) -> None:
        name, entry = item[0], item[1]
        raw = self.css[source]
        target = BARE_VAR.match(raw)
        # A role the email file keeps as a pointer follows tokens.css's
        # pointer; one it keeps as a value (--space-section's fixed 48px)
        # is projected from what the pointer resolves to.
        if source == name and target and BARE_VAR.match(str(entry.get("value", ""))):
            to = target.group(1)
            if entry.get("value") == raw:
                self.kept += 1
                return
            if to in dropped and to not in names:
                use = dict(self.dropped_entry(to)).get("use")
                self.remove(item, quiet=True)
                names.discard(name)
                self.drop(name, {"reason": "It points at %s, which email drops." % to,
                                 **({"use": use} if use else {})})
                self.again.append((name, str(entry.get("value")), "dropped: points at %s" % to))
                return
            if to in names:
                new = dict(entry, value=raw)
                new.pop("note", None)                   # it described the old pointer
                item[1] = ordered(new)
                self.again.append((name, str(entry.get("value")), raw))
                return
        provenance = self.provenance(name, source)
        if entry.get("from") == provenance or ("from" not in entry and entry.get("value") == provenance):
            self.kept += 1
            return
        made = triple(resolve(raw, self.css), TRIPLE.match(name).group(2)) if source != name \
            else project(name, provenance)
        new = {"value": made["value"], "tier": entry.get("tier", self.tiers.get(name, 1)),
               "status": made["status"]}
        if made["status"] != "survives":
            new.update({"from": provenance, "reason": made["reason"]})
            self.reasons.add(made["reason"])
        for key in ("contrast",) + (("note",) if made["value"] == entry.get("value") else ()):
            if key in entry:
                new[key] = entry[key]
        item[1] = ordered(new)
        self.again.append((name, str(entry.get("value")), made["value"]))

    def add(self, name: str, names: set[str], dropped: set[str]) -> None:
        raw = self.css[name]
        if name.startswith("--type-") and "/" in raw:
            resolved = resolve(raw, self.css)
            for part in ("size", "line", "weight"):
                made = triple(resolved, part)
                self.insert(self.entries, "%s-%s" % (name, part),
                            {"value": made["value"], "tier": 2, "status": made["status"],
                             "from": triple_from(resolved), "reason": made["reason"]}, names)
                self.reasons.add(made["reason"])
            self.added.append((name, "the size, line and weight of %s" % triple_from(resolved)))
            return
        fam = family(name)
        kin_kept = [n for n in names if fam and n.startswith(fam) and not TRIPLE.match(n)]
        kin_dropped = [n for n in dropped if fam and n.startswith(fam)]
        if kin_dropped and not kin_kept:
            kin = self.nearest(name, kin_dropped)
            entry = {k: v for k, v in self.dropped_entry(kin).items() if k in ("reason", "use")}
            self.drop(name, entry)
            self.added.append((name, "dropped, as %s is" % kin))
            return
        target = BARE_VAR.match(raw)
        if target and target.group(1) in names:
            made = {"value": raw, "status": "survives"}
            provenance = raw
        else:
            provenance = resolve(raw, self.css)
            made = project(name, provenance)
        entry = {"value": made["value"], "tier": self.tiers.get(name, 1), "status": made["status"]}
        if made["status"] != "survives":
            entry.update({"from": provenance, "reason": made["reason"]})
            self.reasons.add(made["reason"])
        self.insert(self.entries, name, entry, names)
        self.added.append((name, made["value"]))

    # -- bookkeeping ----------------------------------------------------------
    def dropped_entry(self, name: str) -> dict:
        return next(e for n, e, _ in self.dropped if n == name)

    def nearest(self, name: str, kin: list[str]) -> str:
        mine = self.order.get(name, 1 << 30)
        return min(kin, key=lambda n: (abs(self.order.get(n, 1 << 30) - mine), n))

    def remove(self, item: list, quiet: bool = False) -> None:
        at = self.entries.index(item)
        if item[2] and at and not self.entries[at - 1][2]:
            self.entries[at - 1][2] = True
        del self.entries[at]
        if not quiet:
            self.removed.append(item[0])

    def drop(self, name: str, entry: dict) -> None:
        self.insert(self.dropped, name, entry, {n for n, _, _ in self.dropped})

    def insert(self, section: list[list], name: str, entry: dict, names: set[str]) -> None:
        """After the family member tokens.css declares just before it, else
        before the one it declares just after, else in a group of its own at
        the end."""
        fam, mine = (TRIPLE.match(name).group(1)[:7] if TRIPLE.match(name) else family(name)), \
            self.order.get(name, 1 << 30)
        kin = [i for i, (n, _, _) in enumerate(section) if fam and n.startswith(fam)]
        before = [i for i in kin if self.order.get(section[i][0], -1) < mine]
        if before:
            at = max(before, key=lambda i: (self.order.get(section[i][0], -1), i))
            ends = section[at][2]
            section[at][2] = False
            section.insert(at + 1, [name, entry, ends])
        elif kin:
            section.insert(min(kin), [name, entry, False])
        else:
            if section:
                section[-1][2] = True
            section.append([name, entry, False])
        names.add(name)

    # -- checks -----------------------------------------------------------------
    def flat(self) -> dict[str, str]:
        return {n: str(e.get("value", "")) for n, e, _ in self.entries}

    def literal(self, name: str, flat: dict[str, str]) -> str:
        value = flat.get(name)
        if value is None:
            raise Unprojectable("%s is not in the email file" % name)
        for _ in range(12):
            target = BARE_VAR.match(value)
            if not target:
                return value
            if target.group(1) not in flat:
                raise Unprojectable("it points at %s, which the email file lacks" % target.group(1))
            value = flat[target.group(1)]
        raise Unprojectable("a var() cycle")

    def check_references(self) -> None:
        flat = self.flat()
        for name, value in flat.items():
            for ref in re.findall(r"var\(\s*(--[A-Za-z0-9_-]+)", value):
                if ref not in flat:
                    self.problems.append("%s: it points at %s, which tokens.css no longer declares; "
                                         "point it at another token in the email file" % (name, ref))

    def measure(self) -> None:
        flat = self.flat()
        pair = re.compile(r"(\d+(?:\.\d+)?):1 on (--[A-Za-z0-9_-]+)|(--[A-Za-z0-9_-]+) on it is "
                          r"(\d+(?:\.\d+)?):1")
        for item in self.entries:
            name, entry = item[0], item[1]
            if "contrast" not in entry:
                continue
            note = str(entry["contrast"])

            def figure(m: "re.Match[str]") -> str:
                other = m.group(2) or m.group(3)
                fg, bg = (name, other) if m.group(2) else (other, name)
                try:
                    ratio = contrast(to_hex(self.literal(fg, flat))[0], to_hex(self.literal(bg, flat))[0])
                except Unprojectable as exc:
                    self.problems.append("%s: its contrast note names %s: %s" % (name, other, exc))
                    return m.group(0)
                text = "%.2f" % ratio
                if ratio < FLOOR:                       # never "4.50:1, under 4.5:1"
                    self.under.append("%s: %.2f:1 on %s, under %s:1" % (
                        fg, math.floor(ratio * 100) / 100, bg, number(FLOOR)))
                return ("%s:1 on %s" % (text, other)) if m.group(2) else ("%s on it is %s:1" % (other, text))

            again = pair.sub(figure, note)
            if again != note:
                item[1] = dict(entry, contrast=again)
                self.measured.append((name, note, again))

    def document(self, source: str) -> dict:
        doc = {k: v for k, v in self.base.items() if k not in ("tokens", "dropped")}
        doc["source"] = source
        policy = dict(doc.get("substitution_policy") or {})
        if "colour-to-hex" in self.reasons and "colour-to-hex" not in policy:
            policy["colour-to-hex"] = POLICY_COLOUR
            doc["substitution_policy"] = policy
        doc["tokens"] = {n: e for n, e, _ in self.entries}
        doc["dropped"] = {n: e for n, e, _ in self.dropped}
        return doc


def ordered(new: dict) -> dict:
    keys = [k for k in ENTRY_ORDER if k in new] + [k for k in new if k not in ENTRY_ORDER]
    return {k: new[k] for k in keys}


# ---------------------------------------------------------------------------
# Reading and writing
# ---------------------------------------------------------------------------

def email_file(text: str) -> dict:
    """An email-tokens.json, its shape checked: ValueError names what is wrong."""
    doc = json.loads(text)
    if not isinstance(doc, dict) or not isinstance(doc.get("tokens"), dict):
        raise ValueError('it has no "tokens" object')
    for key in ("dropped", "substitution_policy"):
        if not isinstance(doc.get(key, {}), dict):
            raise ValueError("`%s` is not an object" % key)
    for section in ("tokens", "dropped"):
        for name, entry in (doc.get(section) or {}).items():
            if not isinstance(entry, dict) or (section == "tokens" and not isinstance(entry.get("value"), str)):
                raise ValueError("%s in `%s` is not an object%s" % (
                    name, section, " with a string `value`" if section == "tokens" else ""))
    return doc


def declared_order(paths: list[Path], names: list[str]) -> dict[str, int]:
    order: dict[str, int] = {}
    for path in paths:
        if path.suffix.lower() == ".css":
            for _, declaration in _css_blocks(read_text(path)):
                name = declaration.partition(":")[0].strip()
                if name.startswith("--"):
                    order.setdefault(name, len(order))
    for name in names:
        order.setdefault(name, len(order))
    return order


def group_ends(text: str) -> set[str]:
    """The entries a blank line follows in the email file: its groups."""
    ends, last = set(), None
    for line in text.splitlines():
        m = re.match(r'^\s*"((?:--|\[)[^"]*(?:\\"[^"]*)*)"\s*:', line)
        if m:
            last = json.loads('"%s"' % m.group(1))
        elif not line.strip() and last:
            ends.add(last)
            last = None
    return ends


def render(doc: dict, ends: set[str]) -> str:
    """One entry a line, keys aligned in each group, a blank line between groups."""
    dump = lambda v: json.dumps(v, ensure_ascii=False)                  # noqa: E731
    head = [k for k in doc if not isinstance(doc[k], (dict, list))]
    out = ["{"]
    blocks = [",\n".join("  %s: %s" % (dump(k), dump(doc[k])) for k in head)]
    for key in (k for k in doc if k not in head):
        value = doc[key]
        if isinstance(value, list):
            lines = ["    " + dump(v) for v in value]
            blocks.append("  %s: [\n%s\n  ]" % (dump(key), ",\n".join(lines)))
            continue
        groups, group = [], []
        for name, entry in value.items():
            group.append((dump(name), entry))
            if name in ends:
                groups.append(group)
                group = []
        if group:
            groups.append(group)
        rows = []
        for i, group in enumerate(groups):
            width = max(len(k) for k, _ in group) + 1
            for j, (k, entry) in enumerate(group):
                body = dump(entry) if not isinstance(entry, dict) else (
                    "{ " + dump(entry)[1:-1] + " }" if entry else "{}")
                last = i == len(groups) - 1 and j == len(group) - 1
                rows.append("    " + (k + ":").ljust(width) + " " + body + ("" if last else ","))
            if i < len(groups) - 1:
                rows.append("")
        blocks.append("  %s: {\n%s\n  }" % (dump(key), "\n".join(rows)))
    out.append(",\n\n".join(blocks))
    out.append("}")
    return "\n".join(out) + "\n"


def relative(paths: list[Path], out: Path | None) -> str:
    names = []
    for path in paths:
        try:
            names.append(Path(os.path.relpath(path.resolve(), (out.resolve().parent if out else
                                                                 Path.cwd()))).as_posix())
        except ValueError:                                  # another drive
            names.append(path.resolve().as_posix())
    return ", ".join(names)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m scripts.sync_email_tokens",
        description="Write email-tokens.json from the project's tokens.css, keeping the email "
                    "file's own decisions while their source is unchanged.",
    )
    parser.add_argument("--tokens", nargs="+", help="the project's token files (default: "
                                                    ".design-suite.json's tokens)")
    parser.add_argument("--out", "-o", help="the email-tokens.json to write; - for stdout "
                                            "(default: .design-suite.json's emailTokens)")
    parser.add_argument("--base", help="the email file whose decisions are kept (default: --out "
                                       "when it exists, else assets/email-tokens.json)")
    parser.add_argument("--check", action="store_true", help="write nothing; exit 1 when --out is "
                                                             "not the projection")
    parser.add_argument("--format", choices=("text", "json"), default="text", help="the report's form")
    args = parser.parse_args(argv)

    try:
        config = None if args.tokens and args.out else project_config()
    except ConfigError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2
    sources = [Path(p) for p in args.tokens] if args.tokens else list(config.tokens) if config else []
    if args.out == "-":
        out = None
    elif args.out:
        out = Path(args.out)
    else:
        out = config.email_tokens if config else None
    if not sources:
        print("error: name the token files with --tokens, or list them in .design-suite.json's "
              "`tokens`", file=sys.stderr)
        return 2
    if out is None and (args.check or args.out != "-"):
        print("error: name the email file with --out, or set .design-suite.json's `emailTokens`",
              file=sys.stderr)
        return 2
    clash = guard_outputs([out], sources)        # the email file is refreshed in place, its --base too
    if clash:
        print("error: %s" % clash, file=sys.stderr)
        return 2
    base_path = Path(args.base) if args.base else out if out and out.is_file() else SKILL_TOKENS
    try:
        base_text = base_path.read_bytes().decode("utf-8-sig")
        base = email_file(base_text)
    except (OSError, ValueError) as exc:
        print("error: %s: %s" % (base_path, exc), file=sys.stderr)
        return 2
    current = None
    if args.check:
        try:
            current = email_file(out.read_bytes().decode("utf-8-sig"))
        except (OSError, ValueError) as exc:
            print("error: %s: %s" % (out, exc), file=sys.stderr)
            return 2
    try:
        found = read_tokens(sources)
        order = declared_order(sources, list(found.values()))   # a second read (CodeRabbit on #209)
    except (ConfigError, OSError) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2
    if found.problems:                      # a token left out would be taken out of the email file
        for problem in found.problems:
            print("error: %s" % problem, file=sys.stderr)
        print("error: nothing written: the token files were not read whole (Codex on #209)",
              file=sys.stderr)
        return 2
    projection = Projection(base, found.values(), found.tiers(), order, group_ends(base_text))
    projection.run()
    if projection.problems:
        for problem in projection.problems:
            print("error: %s" % problem, file=sys.stderr)
        print("error: nothing written: %d value(s) without an email form" % len(projection.problems),
              file=sys.stderr)
        return 2
    doc = projection.document(relative(sources, out))
    text = render(doc, {n for n, _, end in projection.entries + projection.dropped if end})

    stale = None
    if current is not None:
        stale = sorted(n for section in ("tokens", "dropped")
                       for n in set(doc[section]) | set(current.get(section) or {})
                       if doc[section].get(n) != (current.get(section) or {}).get(n))
        if not stale and {k: v for k, v in doc.items() if k not in ("tokens", "dropped")} != \
                {k: v for k, v in current.items() if k not in ("tokens", "dropped")}:
            stale = ["(the header)"]
    elif out is None:
        sys.stdout.flush()
        sys.stdout.buffer.write(text.encode("utf-8"))     # LF, as the file has it, on Windows too
        sys.stdout.buffer.flush()
    else:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(text.encode("utf-8"))

    report = {"out": str(out) if out else "-", "kept": projection.kept,
              "again": [{"name": n, "was": a, "now": b} for n, a, b in projection.again],
              "added": [{"name": n, "now": v} for n, v in projection.added],
              "removed": projection.removed,
              "contrast": [{"name": n, "was": a, "now": b} for n, a, b in projection.measured],
              "under": projection.under}
    if args.check:
        report["stale"] = stale
    stream = sys.stderr if out is None else sys.stdout
    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2), file=stream)
    else:
        print("%s %s: %d kept, %d projected again, %d added, %d removed" % (
            "checked" if args.check else "wrote", report["out"], projection.kept,
            len(projection.again), len(projection.added), len(projection.removed)), file=stream)
        for n, a, b in projection.again:
            print("  again    %s: %s -> %s" % (n, a, b), file=stream)
        for n, v in projection.added:
            print("  added    %s: %s" % (n, v), file=stream)
        for n in projection.removed:
            print("  removed  %s: tokens.css no longer declares it" % n, file=stream)
        for n, a, b in projection.measured:
            print("  contrast %s: %s (was %s)" % (n, b, a), file=stream)
        for line in projection.under:
            print("UNDER    %s" % line, file=stream)
        if args.check:
            print("STALE    %s" % ", ".join(stale) if stale else "up to date", file=stream)
    return 1 if projection.under or stale else 0


if __name__ == "__main__":
    for _stream in (sys.stdout, sys.stderr):
        if getattr(_stream, "encoding", "utf-8").lower() not in ("utf-8", "utf8"):
            _stream.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
