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
  resolver_document
                   a resolver (`*.resolver.json`, the 2025.10 resolver module)
                   as one tree for a choice of contexts, each modifier's
                   default unless an input picks another; tokens() reads its
                   default, with the resolver's folder as `base`.

WRITING
  document(values) a 2025.10 document from CSS custom properties: each name
                   split on `-` into groups (`--bg-surface` is `bg.surface`), a
                   name that is also a group's prefix as that group's `$root`,
                   `var(--x)` as a reference, and every token typed. A value
                   DTCG has no type for (`clamp()`, `calc()`, `65ch`, `1em`) is
                   reported and left out, and so is a reference to it. With
                   `only`, the named tokens alone: a theme's overrides, typed
                   and named against the whole set.
  resolver(...)    the resolver that puts a base file and each theme's
                   overrides together.

Dependency-free (Python 3.9+, stdlib only).
"""
from __future__ import annotations

import colorsys
import copy
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Iterator, List, Optional, Sequence, Tuple, Union

UNSUPPORTED = object()
# Group-level keys that are never tokens or groups themselves.
META_KEYS = {"$schema", "$description", "$extensions", "$type", "$deprecated",
             "$extends"}
Problems = List[Tuple[str, str]]
# The document's own `$extensions` key, reverse-domain as 2025.10 recommends:
# `notWritten` holds each custom property document() left out, with its value.
EXTENSION = "io.github.vybecode-ltd.web-design-suite"


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
    if alpha >= 1:
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
            suffix = "" if alpha >= 1 else f" / {_fmt(alpha)}"
            return f"oklch({_fmt(L * 100)}% {_fmt(x)} {_fmt(y)}{suffix})"
    hexv = v.get("hex")                          # the spec's sRGB fallback
    if isinstance(hexv, str) and hexv.startswith("#") and len(hexv) == 7:
        try:
            r, g, b = (int(hexv[i:i + 2], 16) / 255 for i in (1, 3, 5))
        except ValueError:
            return None
        return _rgb_css(r, g, b, alpha)
    if lossless and len(comps) == 3 and space in CSS_SPACES | {"lab", "lch"}:
        args = " ".join(_fmt(c) for c in comps) + ("" if alpha >= 1 else f" / {_fmt(alpha)}")
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
    if s.startswith("{") and s.endswith("}") and "{" not in s[1:-1] and "}" not in s[1:-1]:
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
        if not isinstance(target, dict) or "$value" in target:
            problems.append((where, f"`$extends` names {ref!r}, which is not a group here"))
        elif target is node or id(target) in active:       # itself, or a group extending this one
            problems.append((where, f"`$extends` cycle through {ref}"))
        else:
            active.add(id(node))
            _resolve_extends(target, root, path, problems, active)
            active.discard(id(node))
            merged = copy.deepcopy(target)
            _overlay(merged, node)
            node.clear()
            node.update(merged)
            if too_deep(node) or too_large(node):    # stop a fan-out before it fills memory
                raise RecursionError
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


def _bad_type(node: dict) -> Optional[str]:
    """Why a node's `$type` cannot be read, or None: it is a string (S1)."""
    if "$type" in node and not isinstance(node["$type"], str):
        return f"`$type` is {json.dumps(node['$type'])}, not a string, so this is not read"
    return None


def _own_deprecated(node: dict, inherited: Any, name: str, problems: Problems) -> Any:
    """A node's `$deprecated` if it is a string or a boolean, else what it
    inherits, with the problem named (S10). `false` undoes a group's."""
    if "$deprecated" not in node:
        return inherited
    mark = node["$deprecated"]
    if isinstance(mark, (str, bool)):
        return mark
    problems.append((name, f"`$deprecated` is {json.dumps(mark)}, neither a string nor a "
                           f"boolean, so it is not read"))
    return inherited


def _token(node: dict, path: List[str], kind: Optional[str], deprecated: Any,
           problems: Problems, lossless: bool) -> Optional[dict]:
    name = "/".join(path) or "$root"
    bad = _bad_type(node)
    if bad:
        problems.append((name, bad))
        return None
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
    deprecated = _own_deprecated(node, deprecated, name, problems)  # its own, or its group's
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
    bad = _bad_type(node)
    if bad:                                      # its tokens' type is unknown (S1)
        problems.append(("/".join(path) or "(root)", bad))
        return None
    group_kind = node.get("$type", kind)
    group_deprecated = _own_deprecated(node, deprecated, "/".join(path) or "(root)", problems)
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
    if too_deep(data):                           # every step below recurses (CodeRabbit on #101)
        return {}, [("(root)", f"nested more than {MAX_DEPTH} levels deep, so not read")]
    doc = copy.deepcopy(data)
    try:                                         # each `$extends` or `$ref` copies a group in
        _resolve_extends(doc, doc, [], problems, set())
        _inline_pointers(doc, doc)
        if too_deep(doc) or too_large(doc):
            raise RecursionError
    except RecursionError:                       # a long chain or a fan-out (CodeRabbit on #101)
        return {}, [("(root)", f"`$extends` or `$ref` expand it past {MAX_DEPTH} levels or "
                               f"{MAX_NODES} entries, so not read")]
    walked = _walk(doc, [], None, None, problems, lossless)
    return (walked if walked is not None else {}), problems


def _pointer(root: Any, ref: str) -> Any:
    """What a JSON Pointer (`#/base/$value/components/0`) addresses, or UNSUPPORTED."""
    node = root
    for raw in ref[2:].split("/"):
        part = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(node, dict) and part in node:
            node = node[part]
        elif isinstance(node, list) and part.isascii() and part.isdigit() and int(part) < len(node):
            node = node[int(part)]
        else:
            return UNSUPPORTED
    return node


def _inline_pointers(node: Any, root: dict) -> None:
    """A property-level `$ref` (into a value, `#/base/$value/components/0`) is
    what it points at, a literal, so a token or a component may be one (Codex
    on #101). A whole-token `$ref` inside a value becomes `{a.b}`; one that
    is the whole token stays for _token(). A pointer to nothing, or a chain
    that returns to itself, stays as it is, and is reported as unsupported."""
    def literal(ref: str, seen: Tuple[str, ...]) -> Any:
        target = UNSUPPORTED if ref in seen else _pointer(root, ref)
        return target if target is UNSUPPORTED else fix(copy.deepcopy(target), seen + (ref,))

    budget = [MAX_NODES]                         # a pointer fan-out stops here (CodeRabbit on #102)

    def fix(value: Any, seen: Tuple[str, ...]) -> Any:
        budget[0] -= 1
        if budget[0] < 0:
            raise RecursionError
        if isinstance(value, dict) and isinstance(value.get("$ref"), str) and value["$ref"].startswith("#/"):
            alias = pointer_alias(value["$ref"])
            if alias:
                return "{" + alias + "}"
            found = literal(value["$ref"], seen)
            return value if found is UNSUPPORTED else found
        if isinstance(value, dict):
            return {k: fix(v, seen) for k, v in value.items()}
        if isinstance(value, list):
            return [fix(v, seen) for v in value]
        return value

    if not isinstance(node, dict):
        return
    ref = node.get("$ref")
    if "$value" in node:
        node["$value"] = fix(node["$value"], ())
    elif isinstance(ref, str) and ref.startswith("#/") and not pointer_alias(ref):
        found = literal(ref, ())
        if found is not UNSUPPORTED:
            node["$value"] = found
            del node["$ref"]
    else:
        for key, child in node.items():
            if key not in META_KEYS:
                _inline_pointers(child, root)


MAX_DEPTH = 64
MAX_NODES = 100_000


def too_large(data: Any, limit: int = MAX_NODES) -> bool:
    """More than `limit` objects, arrays and values, counted without recursing."""
    count, stack = 0, [data]
    while stack:
        node = stack.pop()
        count += 1
        if count > limit:
            return True
        if isinstance(node, dict):
            stack.extend(node.values())
        elif isinstance(node, list):
            stack.extend(node)
    return False


def too_deep(data: Any, limit: int = MAX_DEPTH) -> bool:
    """Objects or arrays nested more than `limit` deep, found without recursing."""
    stack = [(data, 0)]
    while stack:
        node, depth = stack.pop()
        if depth > limit:
            return True
        if isinstance(node, dict):
            stack.extend((v, depth + 1) for v in node.values())
        elif isinstance(node, list):
            stack.extend((v, depth + 1) for v in node)
    return False


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
    and Terrazzo's default (`color.bg.surface` -> `--color-bg-surface`). A run
    of ASCII a name cannot hold unescaped (a space, `/`, `(`) is one `-`, so
    `Button background` is `--Button-background` (Codex on #101)."""
    return "--" + "-".join(NAME_UNSAFE.sub("-", str(p)) for p in path)


NAME_UNSAFE = re.compile(r"[^A-Za-z0-9_\-\u0080-\U0010ffff]+")


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


def tokens(data: Any, base: Optional[Union[str, Path]] = None) -> Tuple[List[Token], Problems]:
    """Every token of a 2025.10 document, flat and in document order, its
    value lossless (see the module's docstring), with the problems. A Tokens
    Studio export is read as its default theme: each theme group's first. A
    resolver is read as its default, its files found from `base`."""
    studio: Problems = []
    if is_studio(data):                          # its default theme's sets, merged
        data, studio = studio_document(data)
    elif is_resolver(data):
        data, studio = resolver_document(data, base)
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
    # A cycle of references is invalid in DTCG and in CSS alike: each member
    # is left out and named (Codex on #101). One that reads into it stays.
    graph = {t.name: m.group(1) for t in out for m in [re.fullmatch(r"var\((--.+)\)", t.css() or "")] if m}
    cyclic: set = set()
    for start in graph:
        chain, cur = [], start
        while cur in graph and cur not in chain:
            chain.append(cur)
            cur = graph[cur]
        if cur in chain:
            cyclic.update(chain[chain.index(cur):])
    problems += [("/".join(t.path), "is part of a reference cycle, left out") for t in out if t.name in cyclic]
    return [t for t in out if t.name not in cyclic], problems


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
        # A legacy group's `type` is metadata only when it is a value: a
        # group or a token named `type` is a token (Codex on #102).
        legacy = "type" in node and not isinstance(node["type"], (dict, list))
        group_kind = node["$type"] if "$type" in node else node["type"] if legacy else kind
        return {k: (_studio_tree(v, group_kind) if not k.startswith("$")
                    else STUDIO_TYPES.get(str(v).lower(), v) if k == "$type" else v)
                for k, v in node.items() if not (k == "type" and legacy)}
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


def _math_parts(text: str) -> Optional[List[Any]]:
    """Numbers (with a unit) and operators, or None for anything else."""
    pos, parts = 0, []
    while pos < len(text.rstrip()):
        m = MATH_TOKEN.match(text, pos)
        if not m:
            return None
        parts.append((float(m.group(1)), (m.group(2) or "").lower()) if m.group(1) else m.group(3))
        pos = m.end()
    return parts


def _evaluate(text: str) -> Optional[Tuple[float, str]]:
    """+ - * / and brackets over numbers that share one unit, or none."""
    parts = _math_parts(text)
    if parts is None:
        return None
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
    except (ValueError, ZeroDivisionError, RecursionError):   # `((((…` (CodeRabbit on #102)
        return None
    if at[0] != len(parts) or not any(p in ("+", "-", "*", "/") for p in parts):
        return None
    return value, (units.pop() if units else "")


def _is_math(text: str) -> bool:
    """Math over references or numbers: with each reference as a number, only
    numbers, units, brackets and at least one operator. Not a whole reference,
    a CSS function, or a composite such as `1px solid {color.red}`."""
    if (text.startswith("{") and text.endswith("}") and pointer_alias(text)) or re.search(r"[a-z]\(", text, re.I):
        return False
    parts = _math_parts(MATH_REF.sub("1", text))
    return parts is not None and any(p in ("+", "-", "*", "/") for p in parts)


def _var_of(m: "re.Match[str]") -> str:
    """`{color.red}` inside a string, as `var(--color-red)`."""
    alias = pointer_alias("{" + m.group(1) + "}")
    return f"var({css_name(alias.split('.'))})" if alias else m.group(0)


def _studio_math(doc: dict, problems: Problems) -> None:
    """Each value that is math over references and numbers, worked out; a
    reference inside any other string is `var(--name)`. Each lookup is
    remembered and a chain stops at MAX_DEPTH, so neither a fan-out nor a
    long chain can run away (CodeRabbit on #102)."""
    memo: Dict[str, Any] = {}

    def lookup(path: str, seen: Tuple[str, ...]) -> Any:
        if path in memo:
            return memo[path]
        if len(seen) > MAX_DEPTH:
            return None
        memo[path] = found = _lookup_solved(path, seen)
        return found

    def _lookup_solved(path: str, seen: Tuple[str, ...]) -> Any:
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
            if isinstance(value, str) and not _is_math(value.strip()) and MATH_REF.search(value) \
                    and not pointer_alias(value.strip()):
                node["$value"] = MATH_REF.sub(_var_of, value)      # `1px solid {color.red}` (CodeRabbit on #102)
            elif isinstance(value, str) and _is_math(value.strip()):
                try:
                    solved = solve(value, (".".join(path),))
                except RecursionError:
                    solved = value
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
    if too_deep(data):                           # _studio_tree recurses, as normalise() does
        return {}, [("(root)", f"nested more than {MAX_DEPTH} levels deep, so not read")]
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
                elif not key.startswith("$") and not (key == "type" and not isinstance(child, (dict, list))):
                    walk(child, path + (key,))
    walk(data.get(name), ())
    return out


# ---------------------------------------------------------------------------
# The resolver module: themes as sets and modifiers (P31 part 3)
# ---------------------------------------------------------------------------
# A 2025.10 resolver (https://www.designtokens.org/tr/2025.10/resolver/) puts
# token files together. `sets` and `modifiers` are named in `resolutionOrder`,
# "tokens later in the array overriding any tokens that came before them". A
# modifier is one choice (a theme, a density) among its `contexts`, each a list
# of sources, and `default` names the context read when no input picks one. A
# source is inline tokens or a `$ref`: a file "relative to this document", a
# pointer into the resolver (`#/sets/base`), or both (`tokens.json#/color`).
# Keys beside a `$ref` override what it points at, shallowly. Only
# `resolutionOrder` may point at a modifier.

RESOLVER_VERSION = "2025.10"
Loader = Callable[[str], Any]


def is_resolver(data: Any) -> bool:
    return isinstance(data, dict) and isinstance(data.get("resolutionOrder"), list)


@dataclass
class Modifier:
    name: str
    contexts: List[str]
    default: Optional[str]                       # None when it names none, or one it lacks


def _unescape(part: str) -> str:
    return part.replace("~1", "/").replace("~0", "~")


def _escape(part: str) -> str:
    return part.replace("~", "~0").replace("/", "~1")


def _order(data: dict, problems: Problems) -> List[Tuple[str, str, dict]]:
    """`resolutionOrder` as (kind, name, definition), each `$ref` followed
    into `sets` or `modifiers`, its sibling keys over the definition."""
    out: List[Tuple[str, str, dict]] = []
    for i, entry in enumerate(data.get("resolutionOrder") or []):
        where = f"resolutionOrder/{i}"
        if not isinstance(entry, dict):
            problems.append((where, "is not an object, so not read"))
            continue
        ref = entry.get("$ref")
        if isinstance(ref, str):
            m = re.fullmatch(r"#/(sets|modifiers)/([^/]+)", ref)
            table = data.get(m.group(1)) if m else None
            name = _unescape(m.group(2)) if m else ""
            if not (isinstance(table, dict) and isinstance(table.get(name), dict)):
                problems.append((where, f"`{ref}` names no set or modifier in this resolver, so not read"))
                continue
            definition = dict(table[name])
            definition.update((k, v) for k, v in entry.items() if k != "$ref")
            out.append(("set" if m.group(1) == "sets" else "modifier", name, definition))
        elif entry.get("type") in ("set", "modifier") and isinstance(entry.get("name"), str):
            out.append((entry["type"], entry["name"], entry))
        else:
            problems.append((where, "is neither a `$ref` nor a set or modifier with a `name`, so not read"))
    return out


def resolver_modifiers(data: dict) -> List[Modifier]:
    """Each modifier `resolutionOrder` names, in its order."""
    out = []
    for kind, name, definition in _order(data, []):
        contexts = definition.get("contexts")
        if kind == "modifier" and isinstance(contexts, dict) and contexts:
            default = definition.get("default")       # a string, or none (CodeRabbit on #105)
            out.append(Modifier(name, list(contexts), default if isinstance(default, str)
                                and default in contexts else None))
    return out


def default_sources(data: dict) -> List[Any]:
    """The sources a resolver's default resolution reads, in its order: each
    set's, and each modifier's default context's (its string `default`, else
    its first), as resolver_document() picks them."""
    out: List[Any] = []
    for kind, _name, definition in _order(data, []):
        sources = definition.get("sources")
        if kind == "modifier":
            contexts = definition.get("contexts")
            if not (isinstance(contexts, dict) and contexts):
                continue
            default = definition.get("default")
            sources = contexts[default] if isinstance(default, str) and default in contexts \
                else next(iter(contexts.values()))
        if isinstance(sources, list):
            out.extend(sources)
    return out


class OutsideFolder(OSError):
    """A source whose real path is not in the resolver's folder."""


def file_loader(base: Optional[Union[str, Path]]) -> Loader:
    """Read a source file named relative to `base` (the resolver's folder):
    JSON in UTF-8, UTF-16 or UTF-32, with or without a BOM. A file whose real
    path leaves the folder, through a symlink or a junction, is refused with
    OutsideFolder (Codex on #105)."""
    def load(name: str) -> Any:
        folder = Path(base or ".").resolve()
        target = (folder / name).resolve()
        if folder not in target.parents:
            raise OutsideFolder(name)
        return json.loads(target.read_bytes())
    return load


def outside(name: str) -> bool:
    """A source name that leaves the resolver's folder: absolute (`/x`, `C:x`,
    `\\server`) or with a `..` step. project_config.mjs's port reads it the
    same, on every system."""
    return bool(re.match(r"^([\\/]|[A-Za-z]:)", name)) or ".." in re.split(r"[\\/]", name)


def _sources(sources: Any, data: dict, load: Loader, problems: Problems, where: str,
             seen: Tuple[str, ...] = (), budget: Optional[List[int]] = None) -> List[dict]:
    """Each source as a token tree, in order: inline tokens as they are, a
    `$ref` loaded or followed. What cannot be read is named and skipped. A
    fan-out of sets that name sets raises RecursionError past MAX_NODES."""
    budget = [MAX_NODES] if budget is None else budget
    if not isinstance(sources, list):
        problems.append((where, "is not a list of sources, so not read"))
        return []
    trees: List[dict] = []
    for i, source in enumerate(sources):
        at = f"{where}/{i}"
        budget[0] -= 1
        if budget[0] < 0:
            raise RecursionError
        if not isinstance(source, dict):
            problems.append((at, "is not an object, so not read"))
            continue
        ref = source.get("$ref")
        if not isinstance(ref, str):
            trees.append(source)
            continue
        siblings = {k: v for k, v in source.items() if k != "$ref"}
        name, _, pointer = ref.partition("#")
        if not name:                                 # a pointer into the resolver
            # Anywhere but a modifier or resolutionOrder: a set's sources, or
            # one source (`#/sets/base/sources/0`) (Codex on #105).
            target = _pointer(data, "#" + pointer) if pointer.startswith("/") else UNSUPPORTED
            if re.match(r"/(modifiers|resolutionOrder)(/|$)", pointer):
                problems.append((at, f"`{ref}`: only resolutionOrder may point at a modifier, and nothing "
                                     "may point into resolutionOrder, so not read"))
            elif ref in seen:
                problems.append((at, f"`{ref}` is part of a cycle, so not read"))
            elif isinstance(target, dict):
                own = {**target, **siblings}
                is_set = re.fullmatch(r"/sets/[^/]+", pointer)
                trees += _sources(own.get("sources") if is_set else [own], data, load, problems, ref[2:],
                                  seen + (ref,), budget)
            else:
                problems.append((at, f"`{ref}` points at no object in this resolver, so not read"))
            continue
        if re.match(r"^[a-z][a-z0-9+.-]*://", name, re.I):
            problems.append((at, f"`{name}` is a URL; only files beside the resolver are read"))
            continue
        if outside(name):                        # CodeRabbit on #105: a cloned repo's resolver
            problems.append((at, f"`{name}` is outside the resolver's folder; only files in it or "
                                 "below are read"))
            continue
        try:
            tree = load(name)
        except OutsideFolder:
            problems.append((at, f"`{name}` is outside the resolver's folder; only files in it or "
                                 "below are read"))
            continue
        except (OSError, ValueError, RecursionError) as exc:     # missing, unreadable, not JSON
            problems.append((at, f"`{name}` could not be read ({type(exc).__name__}), so not read"))
            continue
        if pointer:
            tree = _pointer(tree, "#" + pointer)
        if not isinstance(tree, dict) or too_deep(tree):
            problems.append((at, f"`{ref}` is not a token tree of at most {MAX_DEPTH} levels, so not read"))
            continue
        trees.append({**tree, **siblings} if siblings else tree)
    return trees


def resolver_document(data: dict, base: Optional[Union[str, Path]] = None,
                      inputs: Optional[Dict[str, str]] = None, only: Optional[str] = None,
                      load: Optional[Loader] = None) -> Tuple[dict, Problems]:
    """The tokens the resolver resolves to, merged in `resolutionOrder`: each
    modifier's context is the one `inputs` picks (names compared without
    case), else its `default`, else its first, which is reported. With
    `only`, that modifier's context alone: the tokens it sets."""
    problems: Problems = []
    if too_deep(data):
        return {}, [("(root)", f"nested more than {MAX_DEPTH} levels deep, so not read")]
    if data.get("version") != RESOLVER_VERSION:
        problems.append(("version", f"is {data.get('version')!r}, not \"{RESOLVER_VERSION}\": read as "
                                    f"{RESOLVER_VERSION}"))
    load = load or file_loader(base)
    picked = {str(k).lower(): str(v).lower() for k, v in (inputs or {}).items()}
    doc: Dict[str, Any] = {}
    budget = [MAX_NODES]
    try:
        for tree in _resolved(data, load, picked, only, problems, budget):
            _merge(doc, tree)
            if too_deep(doc) or too_large(doc):
                raise RecursionError
    except RecursionError:                       # a fan-out of sets, or a merge too big
        return {}, problems + [("(root)", f"its sources expand past {MAX_DEPTH} levels or "
                                          f"{MAX_NODES} entries, so not read")]
    return doc, problems


def _resolved(data: dict, load: Loader, picked: Dict[str, str], only: Optional[str],
              problems: Problems, budget: List[int]) -> Iterator[dict]:
    """Each source tree resolver_document merges, in order."""
    for kind, name, definition in _order(data, problems):
        if kind == "set":
            if only is not None:
                continue
            trees = _sources(definition.get("sources"), data, load, problems, f"sets/{name}",
                             (f"#/sets/{_escape(name)}",), budget)
        else:
            if only is not None and only != name:
                continue
            contexts = definition.get("contexts")
            if not (isinstance(contexts, dict) and contexts):
                problems.append((f"modifiers/{name}", "declares no contexts, so not read"))
                continue
            want = picked.get(name.lower())
            context = next((c for c in contexts if c.lower() == want), None) if want else None
            if context is None:
                default = definition.get("default")
                default = default if isinstance(default, str) and default in contexts else None
                context = default if default is not None else next(iter(contexts))
                if default is None and not want:
                    problems.append((f"modifiers/{name}", f"names no default among its contexts: "
                                                          f"`{context}`, its first, is read"))
            trees = _sources(contexts[context], data, load, problems,
                             f"modifiers/{name}/contexts/{context}", (), budget)
        yield from trees


def token_paths(tree: Any) -> List[Tuple[str, ...]]:
    """The tokens a tree holds, as paths (a group's `$root` at the group's)."""
    out: List[Tuple[str, ...]] = []
    stack: List[Tuple[Any, Tuple[str, ...]]] = [(tree, ())]
    while stack:                                 # without recursing: a source may be deep
        node, path = stack.pop()
        if not isinstance(node, dict):
            continue
        if path and ("$value" in node or isinstance(node.get("$ref"), str)):
            out.append(path)
            continue
        children = [(child, path if key == "$root" else path + (key,))
                    for key, child in node.items() if key == "$root" or key not in META_KEYS]
        stack.extend(reversed(children))
    return out


def resolver(name: str, base_file: str, modifiers: Sequence[Tuple[str, str, Dict[str, Optional[str]]]],
             description: str = "") -> Dict[str, Any]:
    """A resolver: the set `base` (one file), then each modifier as (name,
    default context, {context: its file of overrides, or None for none})."""
    doc: Dict[str, Any] = {"version": RESOLVER_VERSION, "name": name}
    if description:
        doc["description"] = description
    doc["sets"] = {"base": {"sources": [{"$ref": base_file}]}}
    if modifiers:
        doc["modifiers"] = {m: {"contexts": {c: [{"$ref": f}] if f else [] for c, f in contexts.items()},
                                "default": default}
                            for m, default, contexts in modifiers}
    doc["resolutionOrder"] = [{"$ref": "#/sets/base"}] + [{"$ref": f"#/modifiers/{_escape(m)}"}
                                                          for m, _, _ in modifiers]
    return doc


# ---------------------------------------------------------------------------
# Writing: CSS custom properties -> a 2025.10 document
# ---------------------------------------------------------------------------

NUMBER = r"[+-]?(?:\d+\.?\d*|\.\d+)(?:e[+-]?\d+)?"
VAR_ONLY = re.compile(r"^var\(\s*(--[A-Za-z0-9_\-\u0080-\U0010ffff]+)\s*\)$")   # `--café` too (Codex)
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
    if not math.isfinite(r):                     # 1e999: JSON has no Infinity (CodeRabbit on #101)
        raise ValueError(f"{x} is not a finite number")
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
        if fn in ("rgb", "rgba", "hsl", "hsla") and len(args) == 4 and "," in body:   # the legacy form only
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
    try:
        return _css_value(name, value)
    except (ValueError, OverflowError):          # a number no JSON can hold
        return None, UNSUPPORTED


def _css_value(name: str, value: str) -> Tuple[Optional[str], Any]:
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
    if "weight" in name.lower() and low in ("normal", "bold"):
        return "fontWeight", low                 # 2025.10's names for 400 and 700 (Codex on #101)
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
             note: str = "", only: Optional[Iterable[str]] = None) -> Tuple[Dict[str, Any], Problems]:
    """A 2025.10 document from (custom property, CSS value) pairs, in order,
    with the problems as [(name, why)]. See the module's docstring. With
    `only`, the document and the problems hold those names alone, typed and
    placed (`$root` or not) as in the whole set: a theme's overrides."""
    descriptions, deprecated = descriptions or {}, deprecated or {}
    keep = None if only is None else set(only)
    problems: Problems = []
    parsed: Dict[str, Tuple[Tuple[str, ...], Optional[str], Any]] = {}
    given: Dict[str, str] = {}
    for name, value in values:
        given[name] = value
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
    if keep is not None:
        problems = [p for p in problems if p[0] in keep]
    for name, (path, kind, val) in parsed.items():
        if keep is not None and name not in keep:
            continue
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
    if keep is None and problems:
        # Kept in the file with their values, so a diff against the
        # stylesheet it was written from compares them too: a token left out
        # is neither added nor removed, and a new clamp() is still a change
        # (Codex on #119).
        names = sorted({n for n, _ in problems})
        own: Dict[str, Any] = {"notWritten": {name: str(given.get(name, "")) for name in names}}
        marks = {name: deprecated[name] for name in names if deprecated.get(name)}
        if marks:                                # a $deprecated the file could not carry (Codex on #119)
            own["deprecated"] = marks
        doc["$extensions"] = {EXTENSION: own}
    return doc, problems


def _own(data: Any, key: str) -> dict:
    ext = data.get("$extensions") if isinstance(data, dict) else None
    own = ext.get(EXTENSION) if isinstance(ext, dict) else None
    held = own.get(key) if isinstance(own, dict) else None
    return held if isinstance(held, dict) else {}


def not_written(data: Any) -> Dict[str, str]:
    """The custom properties a document says document() left out of it,
    with their CSS values."""
    return {n: v for n, v in _own(data, "notWritten").items()
            if isinstance(n, str) and n.startswith("--") and isinstance(v, str)}


def not_written_marks(data: Any) -> Dict[str, Union[bool, str]]:
    """The `$deprecated` of each token not written, as `true` or its reason."""
    return {n: v for n, v in _own(data, "deprecated").items()
            if isinstance(n, str) and n.startswith("--") and (v is True or (isinstance(v, str) and v))}


def recorded(data: Any, base: Optional[Union[str, Path]]) -> Tuple[Dict[str, str], Dict[str, Union[bool, str]]]:
    """The record of a document or a resolver: each token document() left
    out, with its CSS value, and the `$deprecated` of each. A resolver's is in
    the sources its default contexts read, in its folder `base`; a later
    source wins, as in the resolution, whether it writes the token or
    records it, and takes an earlier one's mark off.
    diff_system and project_config's read_deprecations both read it here
    (the audit's V2 and V3)."""
    docs = [data]
    if is_resolver(data):
        load = file_loader(base)
        docs = []
        for ref in _file_refs(default_sources(data))[:64]:
            if outside(ref):
                continue
            try:
                docs.append(load(ref))
            except (OSError, ValueError):
                continue
    values: Dict[str, str] = {}
    marks: Dict[str, Union[bool, str]] = {}
    for doc in docs:
        for path in token_paths(doc):            # a later source that writes it ends its record
            values.pop(css_name(path), None)     # (Codex and CodeRabbit on #149)
            marks.pop(css_name(path), None)
        got, got_marks = not_written(doc), not_written_marks(doc)
        for name, value in got.items():
            values[name] = value
            marks.pop(name, None)
            if name in got_marks:
                marks[name] = got_marks[name]
    return values, marks


def _file_refs(data: Any) -> List[str]:
    """Each file a resolver's `$ref`s name (the part before `#`), in order."""
    out: List[str] = []
    stack: List[Tuple[Any, int]] = [(data, 0)]
    while stack:
        node, depth = stack.pop()
        if depth > 32:
            continue
        if isinstance(node, dict):
            ref = node.get("$ref")
            name = ref.split("#", 1)[0] if isinstance(ref, str) else ""
            if name and name not in out:
                out.append(name)
            stack.extend((v, depth + 1) for v in reversed(list(node.values())))
        elif isinstance(node, list):
            stack.extend((v, depth + 1) for v in reversed(node))
    return out
