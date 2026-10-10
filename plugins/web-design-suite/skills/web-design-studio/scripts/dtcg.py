"""DTCG 2025.10: reading and writing design token files (P31).

shared/dtcg.py is the master copy. Like project_config.py, it is copied beside
every script that imports it (project_config.py's read_tokens() among them),
and tests/test_dtcg.py holds each copy byte-identical to this one.

The Design Tokens format reached its first stable version, 2025.10, on
2025-10-28 (https://www.designtokens.org/tr/2025.10/format/). A reader written
for the drafts gets it wrong without raising an error:

  * a colour is an object            {colorSpace, components, alpha?, hex?}
  * so are dimensions and durations  {value, unit}
  * a token can be a JSON Pointer    {"$ref": "#/color/neutral/500"}
  * a group can inherit a group      "$extends": "{base}"
  * a group can carry its own token  "$root": {"$value": ...}, named
                                     `{group.$root}` in a reference
  * $type and $deprecated are inherited from the enclosing group

READING
  normalise(data)  the document in the string forms figma-variables-sync's
                   scripts read ("#rrggbb", "oklch(...)", "24px", "220ms",
                   "{a.b}"), so the colour maths and every check stay in one
                   place. A value with no string form here is reported in
                   `problems` and left out, never written as a Python dict.
  tokens(data)     every token, flat and in document order, with its CSS name
                   (`color.bg.surface` is `--color-bg-surface`, Style
                   Dictionary's name/kebab) and its value as CSS: a reference
                   is `var(--name)`, and a colour space with no sRGB form is
                   written in its own CSS function (`lab(...)`, `color(display-p3
                   ...)`). project_config's read_tokens() reads a DTCG file so.

  studio_document  a Tokens Studio export (its sets, `$themes`, `$metadata`,
                   the legacy `{value, type}` keys and its math) as one 2025.10
                   tree per theme; tokens() reads its default theme.

WRITING
  document(values) a 2025.10 document from CSS custom properties: each name
                   split on `-` into groups (`--bg-surface` is `bg.surface`), a
                   name that is also a group's prefix as that group's `$root`,
                   `var(--x)` as a reference, and every token typed. A value
                   DTCG has no type for (`clamp()`, `calc()`, `65ch`, `1em`) is
                   reported and left out, and so is a reference to it.

Dependency-free (Python 3.9+, stdlib only).
"""
from __future__ import annotations

import colorsys
import copy
import math
import re
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, Union

UNSUPPORTED = object()
# Group-level keys that are never tokens or groups themselves.
META_KEYS = {"$schema", "$description", "$extensions", "$type", "$deprecated",
             "$extends"}
Problems = List[Tuple[str, str]]


def _fmt(n: float) -> str:
    return f"{round(float(n), 6):g}"


def _num(x: Any) -> float:
    """A colour component. The spec's "none" keyword is a missing component."""
    if x is None or (isinstance(x, str) and x.strip().lower() == "none"):
        return 0.0
    return float(x)


def _srgb_encode(c: float) -> float:
    return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055


def _rgb_css(r: float, g: float, b: float, alpha: float) -> str:
    """0..1 channels. Opaque becomes a hex (what Figma stores); translucent an
    rgb() with an alpha both scripts already parse."""
    r, g, b = (min(1.0, max(0.0, c)) for c in (r, g, b))
    if alpha >= 0.999:
        return "#" + "".join(f"{round(c * 255):02x}" for c in (r, g, b))
    return f"rgb({_fmt(r * 255)} {_fmt(g * 255)} {_fmt(b * 255)} / {_fmt(alpha)})"


def _hwb_rgb(h: float, w: float, b: float) -> Tuple[float, float, float]:
    """hue 0-360, whiteness and blackness 0-100 (CSS Color 4's hwb-to-rgb)."""
    w, b = w / 100, b / 100
    if w + b >= 1:
        grey = w / (w + b)
        return grey, grey, grey
    r, g, bl = colorsys.hls_to_rgb((h % 360) / 360, 0.5, 1.0)
    return tuple(c * (1 - w - b) + w for c in (r, g, bl))   # type: ignore[return-value]


# The spaces CSS writes as color(<space> ...), and the functions it has for others.
CSS_SPACES = {"display-p3", "a98-rgb", "prophoto-rgb", "rec2020", "xyz-d65", "xyz-d50"}


def colour_to_css(v: dict, lossless: bool = False) -> Optional[str]:
    """A 2025.10 colour object as CSS. With `lossless`, a space with no sRGB
    form here and no `hex` fallback is written in its own CSS function."""
    space = str(v.get("colorSpace", "")).strip().lower()
    try:
        comps = [_num(x) for x in (v.get("components") or [])]
        alpha = 1.0 if v.get("alpha") in (None, "none") else float(v.get("alpha"))
    except (TypeError, ValueError):
        return None
    if len(comps) == 3:
        if space == "srgb":
            return _rgb_css(*comps, alpha)
        if space == "srgb-linear":
            return _rgb_css(*(_srgb_encode(c) for c in comps), alpha)
        if space == "hsl":                       # hue 0-360, saturation/lightness 0-100
            r, g, b = colorsys.hls_to_rgb((comps[0] % 360) / 360, comps[2] / 100, comps[1] / 100)
            return _rgb_css(r, g, b, alpha)
        if space == "hwb" and lossless:
            return _rgb_css(*_hwb_rgb(*comps), alpha)
        if space in ("oklch", "oklab"):
            L, x, y = comps
            if space == "oklab":                 # same colour, polar form
                x, y = math.hypot(x, y), math.degrees(math.atan2(y, x)) % 360
            suffix = "" if alpha >= 0.999 else f" / {_fmt(alpha)}"
            return f"oklch({_fmt(L * 100)}% {_fmt(x)} {_fmt(y)}{suffix})"
    hexv = v.get("hex")                          # the spec's sRGB fallback
    if isinstance(hexv, str) and hexv.startswith("#") and len(hexv) == 7:
        try:
            r, g, b = (int(hexv[i:i + 2], 16) / 255 for i in (1, 3, 5))
        except ValueError:
            return None
        return _rgb_css(r, g, b, alpha)
    if lossless and len(comps) == 3 and space in CSS_SPACES | {"lab", "lch"}:
        args = " ".join(_fmt(c) for c in comps) + ("" if alpha >= 0.999 else f" / {_fmt(alpha)}")
        return f"{space}({args})" if space in ("lab", "lch") else f"color({space} {args})"
    return None


def _ref_css(v: Any, lossless: bool) -> Any:
    """A reference inside a composite: `var(--name)` when lossless, else none."""
    alias = pointer_alias(v) if isinstance(v, str) and v.strip().startswith("{") else None
    if lossless and alias:
        return "var(" + css_name(alias.split(".")) + ")"
    return UNSUPPORTED


def _dimension(v: Any, kind: str, lossless: bool = False) -> Any:
    if isinstance(v, str):
        return _ref_css(v, lossless)
    if not (isinstance(v, dict) and "value" in v and "unit" in v):
        return UNSUPPORTED
    try:
        n = float(v["value"])
    except (TypeError, ValueError):
        return UNSUPPORTED                       # e.g. a reference inside
    unit = str(v["unit"]).strip().lower()
    if kind == "duration" or unit in ("ms", "s"):
        return f"{_fmt(n * 1000)}ms" if unit == "s" else f"{_fmt(n)}ms"
    return f"{_fmt(n)}{unit}"


def _colour_value(v: Any, lossless: bool = False) -> Any:
    if isinstance(v, dict):
        css = colour_to_css(v, lossless)
        return css if css else UNSUPPORTED
    if isinstance(v, str) and not v.strip().startswith("{"):
        return v
    return _ref_css(v, lossless)                 # a reference inside a composite


def _shadow(layers: List[Any], lossless: bool = False) -> Any:
    out = []
    for layer in layers:
        if not isinstance(layer, dict):
            return UNSUPPORTED
        parts = [_dimension(layer.get(k), "dimension", lossless)
                 for k in ("offsetX", "offsetY", "blur", "spread")]
        colour = _colour_value(layer.get("color"), lossless)
        if UNSUPPORTED in parts or colour is UNSUPPORTED:
            return UNSUPPORTED
        out.append(("inset " if layer.get("inset") else "") + " ".join(parts + [colour]))
    return ", ".join(out)


def _bezier(v: Any) -> Any:
    if isinstance(v, list) and len(v) == 4 and all(isinstance(x, (int, float)) for x in v):
        return f"cubic-bezier({', '.join(_fmt(x) for x in v)})"
    return v if isinstance(v, str) and not v.startswith("{") else UNSUPPORTED


def convert(value: Any, kind: Optional[str], lossless: bool = False) -> Any:
    """A 2025.10 $value as the string the scripts read, or UNSUPPORTED."""
    if isinstance(value, dict) and "$ref" in value:
        alias = pointer_alias(value["$ref"])
        return "{" + alias + "}" if alias else UNSUPPORTED
    if isinstance(value, str) and value.strip().startswith("{") and value.strip().endswith("}"):
        alias = pointer_alias(value)             # `{brand.$root}` is `{brand}` here
        return "{" + alias + "}" if alias else value
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    k = (kind or "").lower()
    if isinstance(value, dict):
        if "colorSpace" in value or k == "color":
            return _colour_value(value, lossless)
        if k in ("dimension", "duration", "") and "value" in value and "unit" in value:
            return _dimension(value, k)
        if k == "shadow":
            return _shadow([value], lossless)
        if k == "border":
            parts = (_dimension(value.get("width"), "dimension", lossless), value.get("style"),
                     _colour_value(value.get("color"), lossless))
            if UNSUPPORTED in parts or not isinstance(parts[1], str):
                return UNSUPPORTED
            return " ".join(parts)
        if k == "transition":
            parts = (_dimension(value.get("duration"), "duration", lossless),
                     _bezier(value.get("timingFunction")),
                     _dimension(value.get("delay", {"value": 0, "unit": "ms"}), "duration", lossless))
            return UNSUPPORTED if UNSUPPORTED in parts else " ".join(parts)
        return UNSUPPORTED                       # typography, gradient, strokeStyle, ...
    if isinstance(value, list):
        if k == "cubicbezier":
            return _bezier(value)
        if k == "shadow":
            return _shadow(value, lossless)
        if k in ("fontfamily", "") and value and all(isinstance(x, str) for x in value):
            return ", ".join(f'"{x}"' if " " in x else x for x in value)
    return UNSUPPORTED


def pointer_alias(ref: Any) -> Optional[str]:
    """`#/color/neutral/500`, `#/color/neutral/500/$value` or `{color.neutral.500}`
    -> `color.neutral.500`. A group's own token is `{brand.$root}` or
    `#/brand/$root`, which is `brand` here: the scripts file a `$root` token
    under its group's path. A pointer into part of a value
    (…/$value/components/0) has no alias form."""
    if not isinstance(ref, str):
        return None
    s = ref.strip()
    if s.startswith("{") and s.endswith("}"):
        parts = s[1:-1].split(".")
    elif s.startswith("#/"):
        parts = [p.replace("~1", "/").replace("~0", "~") for p in s[2:].split("/")]
        if parts and parts[-1] == "$value":
            parts = parts[:-1]
    else:
        return None
    if len(parts) > 1 and parts[-1] == "$root":
        parts = parts[:-1]
    if not parts or any(not p or p.startswith("$") for p in parts):
        return None
    return ".".join(parts)


def _lookup(root: dict, ref: Any) -> Optional[Any]:
    alias = pointer_alias(ref)
    if alias is None:
        return None
    node: Any = root
    for part in alias.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def _resolve_extends(node: Any, root: dict, path: List[str],
                     problems: Problems, active: set) -> None:
    """Replace each `$extends` group with a deep copy of the group it names,
    overlaid with its own entries. Chains resolve; a cycle is reported."""
    if not isinstance(node, dict):
        return
    if "$extends" in node:
        where = "/".join(path) or "(root)"
        ref = node.pop("$extends")
        target = _lookup(root, ref)
        if id(node) in active:
            problems.append((where, f"`$extends` cycle through {ref}"))
        elif not isinstance(target, dict) or "$value" in target:
            problems.append((where, f"`$extends` names {ref!r}, which is not a group here"))
        else:
            active.add(id(node))
            _resolve_extends(target, root, path, problems, active)
            active.discard(id(node))
            merged = copy.deepcopy(target)
            _overlay(merged, node)
            node.clear()
            node.update(merged)
    for key, child in list(node.items()):
        if isinstance(child, dict) and key not in META_KEYS:
            _resolve_extends(child, root, path + [key], problems, active)


def _overlay(base: dict, own: dict) -> None:
    for key, value in own.items():
        if (isinstance(value, dict) and isinstance(base.get(key), dict)
                and "$value" not in value and "$value" not in base[key]):
            _overlay(base[key], value)
        else:
            base[key] = copy.deepcopy(value)


def _token(node: dict, path: List[str], kind: Optional[str], deprecated: Any,
           problems: Problems, lossless: bool) -> Optional[dict]:
    name = "/".join(path) or "$root"
    kind = node.get("$type", kind)
    tok = {k: v for k, v in node.items() if k not in ("$ref", "$deprecated")}
    if "$value" not in node:                     # the whole token is a $ref
        alias = pointer_alias(node.get("$ref"))
        if alias is None:
            problems.append((name, f"`$ref` {node.get('$ref')!r} is not a whole-token pointer"))
            return None
        tok["$value"] = "{" + alias + "}"
    else:
        value = convert(node["$value"], kind, lossless)
        if value is UNSUPPORTED:
            problems.append((name, f"a {kind or 'untyped'} value in a form this script "
                                   f"cannot write as CSS yet ({_short(node['$value'])})"))
            return None
        tok["$value"] = value
    if kind and "$type" not in tok:
        tok["$type"] = kind
    deprecated = node.get("$deprecated", deprecated)  # its own, or its group's (false undoes it)
    if deprecated:
        tok["$deprecated"] = deprecated
    return tok


def _short(value: Any) -> str:
    text = str(value)
    return text if len(text) <= 60 else text[:57] + "..."


def _walk(node: Any, path: List[str], kind: Optional[str], deprecated: Any,
          problems: Problems, lossless: bool) -> Any:
    if not isinstance(node, dict):
        return node
    if "$value" in node or "$ref" in node:
        return _token(node, path, kind, deprecated, problems, lossless)
    group_kind = node.get("$type", kind)
    group_deprecated = node.get("$deprecated", deprecated)
    out: Dict[str, Any] = {}
    for key, child in node.items():
        if key in META_KEYS:
            out[key] = child
        elif key == "$root":                     # the group's own token: same path
            tok = (_token(child, path, group_kind, group_deprecated, problems, lossless)
                   if isinstance(child, dict) else None)
            if tok is not None:
                out[key] = tok
        else:
            walked = _walk(child, path + [key], group_kind, group_deprecated, problems, lossless)
            if walked is not None:
                out[key] = walked
    return out


def normalise(data: Any, lossless: bool = False) -> Tuple[Any, Problems]:
    """(the document in string forms, [(token path, problem)]). A token keeps
    `$deprecated` when it or a group around it is deprecated."""
    problems: Problems = []
    if not isinstance(data, dict):
        return data, problems
    doc = copy.deepcopy(data)
    _resolve_extends(doc, doc, [], problems, set())
    return _walk(doc, [], None, None, problems, lossless), problems


# ---------------------------------------------------------------------------
# Reading: the flat view
# ---------------------------------------------------------------------------


def is_document(data: Any, depth: int = 0) -> bool:
    """A DTCG document holds at least one token: an object with `$value`, or
    a whole-token `$ref`, at any depth."""
    if not isinstance(data, dict) or depth > 64:
        return False
    if depth == 0 and is_studio(data):
        return True
    if "$value" in data or isinstance(data.get("$ref"), str):
        return depth > 0
    return any(is_document(v, depth + 1) for k, v in data.items()
               if isinstance(v, dict) and k not in ("$extensions", "$schema"))


def css_name(path: Sequence[str]) -> str:
    """A token's path as a CSS custom property: Style Dictionary's name/kebab
    and Terrazzo's default (`color.bg.surface` -> `--color-bg-surface`)."""
    return "--" + "-".join(path)


@dataclass
class Token:
    path: Tuple[str, ...]
    type: Optional[str]
    value: Any                                   # the string form, "{a.b}" for a reference
    description: str = ""
    deprecated: Union[bool, str] = False

    @property
    def name(self) -> str:
        return css_name(self.path)

    @property
    def alias(self) -> Optional[str]:
        if isinstance(self.value, str) and self.value.startswith("{") and self.value.endswith("}"):
            return pointer_alias(self.value)
        return None

    def css(self) -> Optional[str]:
        """The value as CSS: a reference as `var(--name)`. A boolean or a
        missing value has none."""
        if self.alias:
            return "var(" + css_name(self.alias.split(".")) + ")"
        if isinstance(self.value, bool) or self.value is None:
            return None
        if isinstance(self.value, (int, float)):
            return _fmt(self.value)
        text = " ".join(str(self.value).split())
        return text or None


def tokens(data: Any) -> Tuple[List[Token], Problems]:
    """Every token of a 2025.10 document, flat and in document order, its
    value lossless (see the module's docstring), with the problems. A Tokens
    Studio export is read as its default theme: each theme group's first."""
    studio: Problems = []
    if is_studio(data):                          # its default theme's sets, merged
        data, studio = studio_document(data)
    doc, problems = normalise(data, lossless=True)
    problems = studio + problems
    out: List[Token] = []

    def walk(node: Any, path: List[str]) -> None:
        if not isinstance(node, dict):
            return
        if "$value" in node:
            out.append(Token(tuple(path), node.get("$type"), node["$value"],
                             str(node.get("$description") or ""), node.get("$deprecated") or False))
            return
        for key, child in node.items():
            if key == "$root":
                walk(child, path)
            elif key not in META_KEYS:
                walk(child, path + [key])

    walk(doc, [])
    return out, problems


# ---------------------------------------------------------------------------
# Tokens Studio: sets, $themes and $metadata (P31 part 2)
# ---------------------------------------------------------------------------
# A Tokens Studio export keeps each token set under its name at the top level,
# beside `$themes` (each theme's sets: "source" for references only, "enabled"
# for its own tokens, "disabled") and `$metadata.tokenSetOrder`. Its references
# name a token without its set (`{neutral.0}`), so the sets a theme uses merge
# into one tree: its source sets, then its enabled ones, each in set order, a
# later set's token winning, as sd-transforms' permutateThemes orders them. A legacy token is `{value, type, description}`; a value may be
# math (`{space.base} * 6`); a bare number on a size is px.

STUDIO_KEYS = ("$themes", "$metadata")
# Tokens Studio's types, as the 2025.10 type each one is.
STUDIO_TYPES = {"spacing": "dimension", "sizing": "dimension", "borderradius": "dimension",
                "borderwidth": "dimension", "fontsizes": "dimension", "letterspacing": "dimension",
                "paragraphspacing": "dimension", "paragraphindent": "dimension", "dimension": "dimension",
                "fontfamilies": "fontFamily", "fontweights": "fontWeight", "lineheights": "number",
                "opacity": "number", "number": "number", "boxshadow": "shadow", "color": "color",
                "typography": "typography", "border": "border", "duration": "duration",
                "cubicbezier": "cubicBezier"}
MATH_REF = re.compile(r"\{([^{}]+)\}")
MATH_TOKEN = re.compile(r"\s*(?:(\d+\.?\d*|\.\d+)(px|rem|em|%)?|([-+*/()]))", re.I)


def is_studio(data: Any) -> bool:
    return isinstance(data, dict) and (isinstance(data.get("$themes"), list)
                                       or isinstance(data.get("$metadata"), dict))


def studio_sets(data: dict) -> List[str]:
    """The set names in `tokenSetOrder`, then any set it leaves out."""
    meta = data.get("$metadata") if isinstance(data.get("$metadata"), dict) else {}
    order = [n for n in (meta.get("tokenSetOrder") or []) if isinstance(n, str)]
    names = [n for n in order if isinstance(data.get(n), dict)]
    return names + [k for k, v in data.items()
                    if isinstance(v, dict) and k not in STUDIO_KEYS and not k.startswith("$") and k not in names]


@dataclass
class Theme:
    name: str
    group: str
    sets: List[str]                              # its "source" sets, then its "enabled" ones
    enabled: List[str]


def studio_themes(data: dict) -> List[Theme]:
    order = studio_sets(data)
    out = []
    for entry in data.get("$themes") or []:
        if not (isinstance(entry, dict) and isinstance(entry.get("name"), str)):
            continue
        chosen = entry.get("selectedTokenSets") if isinstance(entry.get("selectedTokenSets"), dict) else {}
        out.append(Theme(entry["name"], str(entry.get("group") or ""),
                         [s for s in order if chosen.get(s) == "source"]
                         + [s for s in order if chosen.get(s) == "enabled"],
                         [s for s in order if chosen.get(s) == "enabled"]))
    return out


def studio_default(data: dict) -> List[str]:
    """The sets of each theme group's first theme, the source sets first, or
    every set with no themes."""
    themes = studio_themes(data)
    if not themes:
        return studio_sets(data)
    first: Dict[str, Theme] = {}
    for theme in themes:
        first.setdefault(theme.group, theme)
    enabled = {s for theme in first.values() for s in theme.enabled}
    source = {s for theme in first.values() for s in theme.sets} - enabled
    order = studio_sets(data)
    return [s for s in order if s in source] + [s for s in order if s in enabled]


def _studio_token(node: Any) -> bool:
    return isinstance(node, dict) and ("$value" in node or (
        "value" in node and ("type" in node or not isinstance(node["value"], dict))))


def _studio_tree(node: Any, kind: Optional[str] = None) -> Any:
    """A set as 2025.10 keys: `$value`, `$type` as the 2025.10 type,
    `$description`, and a bare number on a size as px."""
    if not isinstance(node, dict):
        return node
    if not _studio_token(node):
        group_kind = node.get("$type", node.get("type", kind))
        return {k: (_studio_tree(v, group_kind) if not k.startswith("$")
                    else STUDIO_TYPES.get(str(v).lower(), v) if k == "$type" else v)
                for k, v in node.items() if k not in ("type",)}
    value = node["$value"] if "$value" in node else node["value"]
    studio = str(node.get("$type", node.get("type", kind)) or "")
    kind = STUDIO_TYPES.get(studio.lower(), studio or None)
    if kind == "dimension" and (isinstance(value, (int, float)) and not isinstance(value, bool)
                                or isinstance(value, str) and re.fullmatch(NUMBER, value.strip())):
        value = f"{_fmt(float(value))}px"
    out: Dict[str, Any] = {"$value": value}
    if kind:
        out["$type"] = kind
    for key in ("description", "$description"):
        if isinstance(node.get(key), str):
            out["$description"] = node[key]
    for key in ("$deprecated", "$extensions"):
        if key in node:
            out[key] = node[key]
    return out


def _merge(into: dict, tree: dict) -> None:
    for key, value in tree.items():
        if isinstance(value, dict) and isinstance(into.get(key), dict) \
                and "$value" not in value and "$value" not in into[key]:
            _merge(into[key], value)
        else:
            into[key] = copy.deepcopy(value)


def _evaluate(text: str) -> Optional[Tuple[float, str]]:
    """+ - * / and brackets over numbers that share one unit, or none."""
    pos, parts = 0, []
    while pos < len(text.rstrip()):
        m = MATH_TOKEN.match(text, pos)
        if not m:
            return None
        parts.append((float(m.group(1)), (m.group(2) or "").lower()) if m.group(1) else m.group(3))
        pos = m.end()
    units = {p[1] for p in parts if isinstance(p, tuple) and p[1]}
    if len(units) > 1:
        return None
    at = [0]

    def peek() -> Any:
        return parts[at[0]] if at[0] < len(parts) else None

    def factor() -> float:
        token = peek()
        at[0] += 1
        if token == "-":
            return -factor()
        if token == "(":
            value = expr()
            if peek() != ")":
                raise ValueError
            at[0] += 1
            return value
        if isinstance(token, tuple):
            return token[0]
        raise ValueError

    def term() -> float:
        value = factor()
        while peek() in ("*", "/"):
            op = peek()
            at[0] += 1
            right = factor()
            value = value * right if op == "*" else value / right
        return value

    def expr() -> float:
        value = term()
        while peek() in ("+", "-"):
            op = peek()
            at[0] += 1
            right = term()
            value = value + right if op == "+" else value - right
        return value

    try:
        value = expr()
    except (ValueError, ZeroDivisionError):
        return None
    if at[0] != len(parts) or not any(p in ("+", "-", "*", "/") for p in parts):
        return None
    return value, (units.pop() if units else "")


def _is_math(text: str) -> bool:
    """Math over references or numbers, not a whole reference or a CSS function."""
    if (text.startswith("{") and text.endswith("}") and pointer_alias(text)) or re.search(r"[a-z]\(", text, re.I):
        return False
    return bool(MATH_REF.search(text) or re.search(r"\d\s*[*/+]|\s-\s", text))


def _studio_math(doc: dict, problems: Problems) -> None:
    """Each value that is math over references and numbers, worked out."""
    def lookup(path: str, seen: Tuple[str, ...]) -> Any:
        node: Any = doc
        for part in path.split("."):
            if not isinstance(node, dict) or part not in node:
                return None
            node = node[part]
        if isinstance(node, dict) and "$value" not in node:
            node = node.get("$root")
        if not isinstance(node, dict) or path in seen:
            return None
        return solve(node.get("$value"), seen + (path,))

    def solve(value: Any, seen: Tuple[str, ...]) -> Any:
        if not isinstance(value, str):
            return value
        text = value.strip()
        alias = pointer_alias(text) if text.startswith("{") and text.endswith("}") else None
        if alias:
            return lookup(alias, seen)
        if not _is_math(text):
            return value
        replaced = MATH_REF.sub(lambda m: str(lookup(m.group(1), seen)), text)
        result = _evaluate(replaced)
        if result is None:
            return value
        return f"{_fmt(result[0])}{result[1]}" if result[1] else result[0]

    def walk(node: Any, path: List[str]) -> bool:
        """True: leave this token out."""
        if not isinstance(node, dict):
            return False
        if "$value" in node:
            value = node["$value"]
            if isinstance(value, str) and _is_math(value.strip()):
                solved = solve(value, (".".join(path),))
                if solved == value:
                    problems.append(("/".join(path), f"math this script cannot work out, left out "
                                                     f"({_short(value)})"))
                    return True
                node["$value"] = solved
            return False
        for key in [k for k in node if not k.startswith("$")]:
            if walk(node[key], path + [key]):
                del node[key]
        return False

    walk(doc, [])


def studio_document(data: dict, sets: Optional[Sequence[str]] = None) -> Tuple[dict, Problems]:
    """The sets (default: the default theme's, studio_default) merged into one
    2025.10 tree in set order, with its math worked out."""
    problems: Problems = []
    doc: Dict[str, Any] = {}
    for name in (studio_default(data) if sets is None else sets):
        if isinstance(data.get(name), dict):
            _merge(doc, _studio_tree(data[name]))
    _studio_math(doc, problems)
    return doc, problems


def studio_paths(data: dict, name: str) -> List[Tuple[str, ...]]:
    """The tokens one set holds, as paths."""
    out: List[Tuple[str, ...]] = []

    def walk(node: Any, path: Tuple[str, ...]) -> None:
        if _studio_token(node):
            out.append(path)
        elif isinstance(node, dict):
            for key, child in node.items():
                if key == "$root":
                    walk(child, path)
                elif not key.startswith("$") and key != "type":
                    walk(child, path + (key,))
    walk(data.get(name), ())
    return out


# ---------------------------------------------------------------------------
# Writing: CSS custom properties -> a 2025.10 document
# ---------------------------------------------------------------------------

NUMBER = r"[+-]?(?:\d+\.?\d*|\.\d+)(?:e[+-]?\d+)?"
VAR_ONLY = re.compile(r"^var\(\s*(--[A-Za-z0-9_-]+)\s*\)$")
DIMENSION = re.compile(rf"^({NUMBER})(px|rem)$", re.I)
DURATION = re.compile(rf"^({NUMBER})(ms|s)$", re.I)
PLAIN_NUMBER = re.compile(rf"^{NUMBER}$", re.I)
OTHER_UNIT = re.compile(rf"^{NUMBER}([a-z%]+)$", re.I)
EASINGS = {"linear": [0, 0, 1, 1], "ease": [0.25, 0.1, 0.25, 1], "ease-in": [0.42, 0, 1, 1],
           "ease-out": [0, 0, 0.58, 1], "ease-in-out": [0.42, 0, 0.58, 1]}
BORDER_STYLES = {"solid", "dashed", "dotted", "double", "groove", "ridge", "inset", "outset"}
# A font stack's name: the starter's `--font-sans`, `--font-mono`, or a family.
FONT_FAMILY = re.compile(r"^--font-(?:famil(?:y|ies)|sans|serif|mono|display|body|heading|ui|code)"
                         r"(?:-|$)|^--font-?family")
COLOUR_FUNCTION = re.compile(r"^(rgba?|hsla?|hwb|lab|lch|oklab|oklch|color)\((.*)\)$", re.I | re.S)
NAMED = {"black": (0, 0, 0), "white": (1, 1, 1)}
# CSS spellings of the 2025.10 colour spaces color() takes.
COLOR_FN_SPACES = {"srgb", "srgb-linear", "display-p3", "a98-rgb", "prophoto-rgb", "rec2020",
                   "xyz-d65", "xyz-d50", "xyz"}


def _out(x: float) -> Union[int, float]:
    r = round(float(x), 6) + 0.0                 # + 0.0 turns -0.0 into 0.0
    return int(r) if r == int(r) and abs(r) < 1e15 else r


def _split_top(text: str, sep: str) -> List[str]:
    """`text` split on `sep` outside brackets and quotes; " " splits on runs of
    whitespace."""
    parts, depth, quote, start = [], 0, "", 0
    for i, ch in enumerate(text):
        if quote:
            if ch == quote:
                quote = ""
        elif ch in "\"'":
            quote = ch
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        elif depth == 0 and (ch == sep or (sep == " " and ch.isspace())):
            parts.append(text[start:i])
            start = i + 1
    parts.append(text[start:])
    return [p.strip() for p in parts if p.strip()]


def _hue(text: str) -> Union[float, str]:
    t = text.strip().lower()
    if t == "none":
        return "none"
    for unit, scale in (("deg", 1.0), ("grad", 0.9), ("rad", 180 / math.pi), ("turn", 360.0)):
        if t.endswith(unit):
            return float(t[: -len(unit)]) * scale % 360
    return float(t) % 360


def _part(text: str, percent: float = 1.0) -> Union[float, str]:
    """A component: `none`, a number, or a percentage of `percent`."""
    t = text.strip().lower()
    if t == "none":
        return "none"
    if t.endswith("%"):
        return float(t[:-1]) / 100 * percent
    return float(t)


def _hex_of(r: float, g: float, b: float) -> str:
    return "#" + "".join(f"{round(min(1.0, max(0.0, c)) * 255):02x}" for c in (r, g, b))


def _oklab_srgb(L: float, a: float, b: float) -> Tuple[float, float, float]:
    l_ = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m_ = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s_ = (L - 0.0894841775 * a - 1.2914855480 * b) ** 3
    lin = (4.0767416621 * l_ - 3.3077115913 * m_ + 0.2309699292 * s_,
           -1.2684380046 * l_ + 2.6097574011 * m_ - 0.3413193965 * s_,
           -0.0041960863 * l_ - 0.7034186147 * m_ + 1.7076147010 * s_)
    return tuple(_srgb_encode(min(1.0, max(0.0, c))) for c in lin)   # type: ignore[return-value]


def css_colour(text: str) -> Optional[dict]:
    """A CSS colour as a 2025.10 colour object, with the sRGB `hex` fallback
    wherever this module can compute one (clipped to sRGB), or None."""
    t = " ".join(text.strip().split()).lower()
    if t == "transparent":
        return {"colorSpace": "srgb", "components": [0, 0, 0], "alpha": 0, "hex": "#000000"}
    if t in NAMED:
        return {"colorSpace": "srgb", "components": list(NAMED[t]), "hex": _hex_of(*NAMED[t])}
    m = re.fullmatch(r"#([0-9a-f]{3,4}|[0-9a-f]{6}|[0-9a-f]{8})", t)
    if m:
        h = m.group(1)
        if len(h) <= 4:
            h = "".join(c * 2 for c in h)
        rgb = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
        out: Dict[str, Any] = {"colorSpace": "srgb", "components": [_out(c) for c in rgb],
                               "hex": "#" + h[:6]}
        if len(h) == 8 and h[6:] != "ff":
            out["alpha"] = _out(int(h[6:], 16) / 255)
        return out
    m = COLOUR_FUNCTION.fullmatch(t)
    if not m:
        return None
    fn, body = m.group(1), m.group(2)
    body, _, alpha_text = body.partition("/")
    args = [a for a in re.split(r"[\s,]+", body.strip()) if a]
    try:
        alpha = 1.0 if not alpha_text.strip() else float(_part(alpha_text, 1.0))
        if fn in ("rgba", "hsla") and len(args) == 4:
            alpha, args = float(_part(args[3], 1.0)), args[:3]
        space = fn
        if fn == "color":
            space, args = (args[0] if args else ""), args[1:]
            space = "xyz-d65" if space == "xyz" else space
            if space not in COLOR_FN_SPACES - {"xyz"}:
                return None
            comps: List[Any] = [_part(a, 1.0) for a in args]
        elif fn in ("rgb", "rgba"):
            space = "srgb"
            comps = [_part(a, 255.0) for a in args]
            comps = [c if c == "none" else c / 255 for c in comps]
        elif fn in ("hsl", "hsla", "hwb"):
            space = "hwb" if fn == "hwb" else "hsl"
            comps = [_hue(args[0])] + [_part(a, 100.0) for a in args[1:]]
        elif fn == "lab":
            comps = [_part(args[0], 100.0), _part(args[1], 125.0), _part(args[2], 125.0)]
        elif fn == "lch":
            comps = [_part(args[0], 100.0), _part(args[1], 150.0), _hue(args[2])]
        elif fn == "oklab":
            comps = [_part(args[0], 1.0), _part(args[1], 0.4), _part(args[2], 0.4)]
        else:                                    # oklch
            comps = [_part(args[0], 1.0), _part(args[1], 0.4), _hue(args[2])]
    except (ValueError, IndexError):
        return None
    if len(comps) != 3 or not 0 <= alpha <= 1:
        return None
    out = {"colorSpace": space, "components": [c if c == "none" else _out(c) for c in comps]}
    if alpha < 1:
        out["alpha"] = _out(alpha)
    plain = [0.0 if c == "none" else float(c) for c in comps]
    rgb: Optional[Tuple[float, float, float]] = None
    if space == "srgb":
        rgb = (plain[0], plain[1], plain[2])
    elif space == "srgb-linear":
        rgb = tuple(_srgb_encode(min(1.0, max(0.0, c))) for c in plain)   # type: ignore[assignment]
    elif space == "hsl":
        rgb = colorsys.hls_to_rgb((plain[0] % 360) / 360, plain[2] / 100, plain[1] / 100)
    elif space == "hwb":
        rgb = _hwb_rgb(*plain)
    elif space == "oklab":
        rgb = _oklab_srgb(*plain)
    elif space == "oklch":
        h = math.radians(plain[2])
        rgb = _oklab_srgb(plain[0], plain[1] * math.cos(h), plain[1] * math.sin(h))
    if rgb is not None:
        out["hex"] = _hex_of(*rgb)
    return out


def _dim(text: str) -> Optional[dict]:
    if text == "0":
        return {"value": 0, "unit": "px"}
    m = DIMENSION.fullmatch(text)
    return {"value": _out(float(m.group(1))), "unit": m.group(2).lower()} if m else None


def _reference(text: str) -> Optional[str]:
    m = VAR_ONLY.fullmatch(text)
    return m.group(1) if m else None


def _dim_or_ref(text: str) -> Optional[dict]:
    ref = _reference(text)
    return {"$var": ref} if ref else _dim(text)


def _shadow_layer(text: str) -> Optional[dict]:
    """One layer: two to four lengths and a colour, any of them a reference.
    With no literal colour, the last reference is the colour."""
    words = _split_top(text, " ")
    inset = "inset" in words
    words = [w for w in words if w != "inset"]
    literal = [i for i, w in enumerate(words) if css_colour(w)]
    refs = [i for i, w in enumerate(words) if _reference(w)]
    at = literal[0] if len(literal) == 1 else (refs[-1] if not literal and refs else None)
    if at is None:
        return None
    dims = [_dim_or_ref(w) for i, w in enumerate(words) if i != at]
    if not 2 <= len(dims) <= 4 or None in dims:
        return None
    dims += [{"value": 0, "unit": "px"}] * (4 - len(dims))
    out: Dict[str, Any] = {"color": css_colour(words[at]) or {"$var": _reference(words[at])}}
    out.update(zip(("offsetX", "offsetY", "blur", "spread"), dims))
    if inset:
        out["inset"] = True
    return out


def _border(text: str) -> Optional[dict]:
    words = _split_top(text, " ")
    if len(words) != 3:
        return None
    style = next((w for w in words if w in BORDER_STYLES), None)
    width = next((d for d in map(_dim, words) if d), None)
    rest = [w for w in words if w != style and not _dim(w)]   # the colour, literal or a reference
    if not (style and width and len(rest) == 1):
        return None
    colour = css_colour(rest[0]) or ({"$var": _reference(rest[0])} if _reference(rest[0]) else None)
    return {"color": colour, "width": width, "style": style} if colour else None


def css_value(name: str, value: str) -> Tuple[Optional[str], Any]:
    """(the 2025.10 $type, the $value) for one custom property, or (None,
    UNSUPPORTED). A reference is ("$var", "--target"); a reference inside a
    composite is {"$var": "--target"}, which document() resolves."""
    text = " ".join(str(value).split())
    low = text.lower()
    ref = _reference(text)
    if ref:
        return "$var", ref
    colour = css_colour(text)
    if colour:
        return "color", colour
    dim = _dim(low)
    if dim and low != "0":
        return "dimension", dim
    m = DURATION.fullmatch(low)
    if m:
        return "duration", {"value": _out(float(m.group(1))), "unit": m.group(2).lower()}
    if PLAIN_NUMBER.fullmatch(low):
        n = _out(float(low))
        if "weight" in name.lower() and 1 <= n <= 1000:
            return "fontWeight", n
        return "number", n
    if low in EASINGS:
        return "cubicBezier", list(EASINGS[low])
    m = re.fullmatch(r"cubic-bezier\(([^)]*)\)", low)
    if m:
        try:
            pts = [_out(float(x)) for x in m.group(1).split(",")]
        except ValueError:
            pts = []
        return ("cubicBezier", pts) if len(pts) == 4 and 0 <= pts[0] <= 1 and 0 <= pts[2] <= 1 \
            else (None, UNSUPPORTED)
    layers = [_shadow_layer(layer) for layer in _split_top(text, ",")]
    if layers and None not in layers:
        return "shadow", layers[0] if len(layers) == 1 else layers
    border = _border(text)
    if border:
        return "border", border
    if FONT_FAMILY.search(name.lower()) and not re.search(r"[()]", text):
        families = [f.strip("\"'") for f in _split_top(text, ",")]
        if families and all(families):
            return "fontFamily", families
    return None, UNSUPPORTED


def path_of(name: str) -> Optional[Tuple[str, ...]]:
    """A custom property's path: its name split on `-`. A name a split would
    break (an empty segment) is one key. None for a name DTCG cannot hold."""
    if not name.startswith("--") or len(name) < 3:
        return None
    body = name[2:]
    if any(c in body for c in "{}.") or any(p.startswith("$") for p in body.split("-")):
        return None
    parts = body.split("-")
    return tuple(parts) if all(parts) else (body,)


def _why(value: str) -> str:
    low = " ".join(value.split()).lower()
    m = OTHER_UNIT.fullmatch(low)
    if m:
        return (f"`{value}`: a DTCG dimension is px or rem, and a duration ms or s; "
                f"{m.group(1)} has no 2025.10 type")
    if "var(" in low:
        return f"`{value}` reads another token inside an expression, which DTCG cannot hold"
    return f"`{value}` has no DTCG 2025.10 type"


def document(values: Iterable[Tuple[str, str]], descriptions: Optional[Dict[str, str]] = None,
             deprecated: Optional[Dict[str, Union[bool, str]]] = None,
             note: str = "") -> Tuple[Dict[str, Any], Problems]:
    """A 2025.10 document from (custom property, CSS value) pairs, in order,
    with the problems as [(name, why)]. See the module's docstring."""
    descriptions, deprecated = descriptions or {}, deprecated or {}
    problems: Problems = []
    parsed: Dict[str, Tuple[Tuple[str, ...], Optional[str], Any]] = {}
    for name, value in values:
        path = path_of(name)
        if path is None:
            problems.append((name, "a DTCG name cannot hold `{`, `}`, `.` or a leading `$`"))
            continue
        kind, val = css_value(name, value)
        if val is UNSUPPORTED:
            problems.append((name, _why(value)))
            continue
        parsed[name] = (path, kind, val)

    def refs(kind: Optional[str], val: Any) -> List[str]:
        if kind == "$var":
            return [val]
        if isinstance(val, dict):
            return [val["$var"]] if "$var" in val else [r for v in val.values() for r in refs(None, v)]
        return [r for v in val for r in refs(None, v)] if isinstance(val, list) else []

    def type_of(name: str, seen: Tuple[str, ...] = ()) -> Optional[str]:
        path, kind, val = parsed[name]
        if kind != "$var":
            return kind
        if val in seen:
            return None
        return type_of(val, seen + (val,))

    # A reference to a token left out is left out too, and so is a cycle,
    # until nothing changes.
    changed = True
    while changed:
        changed = False
        for name in list(parsed):
            missing = [r for r in refs(*parsed[name][1:]) if r not in parsed]
            if missing:
                del parsed[name]
                problems.append((name, f"reads {missing[0]}, which is not written"))
                changed = True
        if changed:
            continue
        for name in list(parsed):
            if parsed[name][1] == "$var" and type_of(name, (name,)) is None:
                del parsed[name]
                problems.append((name, "is part of a reference cycle"))
                changed = True
                break

    groups = {path[:i] for path, _, _ in parsed.values() for i in range(1, len(path))}

    def target(ref: str) -> str:
        path = parsed[ref][0]
        return "{" + ".".join(path + (("$root",) if path in groups else ())) + "}"

    def resolve(val: Any) -> Any:
        if isinstance(val, dict) and "$var" in val:
            return target(val["$var"])
        if isinstance(val, dict):
            return {k: resolve(v) for k, v in val.items()}
        if isinstance(val, list):
            return [resolve(v) for v in val]
        return val

    doc: Dict[str, Any] = {}
    if note:
        doc["$description"] = note
    for name, (path, kind, val) in parsed.items():
        token: Dict[str, Any] = {"$type": type_of(name),
                                 "$value": target(val) if kind == "$var" else resolve(val)}
        if descriptions.get(name):
            token["$description"] = descriptions[name]
        if deprecated.get(name):
            token["$deprecated"] = deprecated[name]
        node = doc
        for part in path[:-1]:
            node = node.setdefault(part, {})
        key = path[-1]
        if path in groups:
            node.setdefault(key, {})["$root"] = token
        else:
            node[key] = token
    return doc, problems
