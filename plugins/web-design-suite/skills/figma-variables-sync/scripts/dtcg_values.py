"""DTCG 2025.10 support shared by figma_to_tokens.py and figma_audit.py.

The Design Tokens format reached its first stable version, 2025.10, on
2025-10-28 (https://www.designtokens.org/tr/2025.10/format/). A reader written
for the drafts gets it wrong without raising an error:

  * a colour is an object            {colorSpace, components, alpha?, hex?}
  * so are dimensions and durations  {value, unit}
  * a token can be a JSON Pointer    {"$ref": "#/color/neutral/500"}
  * a group can inherit a group      "$extends": "{base}"
  * a group can carry its own token  "$root": {"$value": …}
  * $type is inherited from the enclosing group

normalise() rewrites a document into the string forms both scripts already
read — "#rrggbb", "rgb(… / a)", "oklch(…)", "24px", "220ms", "{a.b}" — so the
colour maths, the scales and every check stay in one place. Legacy string
values pass through untouched. A value with no string form here (a typography
composite, a colour space with no sRGB fallback, a composite that contains a
reference) is reported in `problems` and left out, never written as a Python
dict. The scripts treat `$root` as the enclosing group's own token.
"""
from __future__ import annotations

import colorsys
import copy
import math
from typing import Any, Dict, List, Optional, Tuple

UNSUPPORTED = object()
# Group-level keys that are never tokens or groups themselves.
META_KEYS = {"$schema", "$description", "$extensions", "$type", "$deprecated",
             "$extends"}


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


def colour_to_css(v: dict) -> Optional[str]:
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
    return None


def _dimension(v: Any, kind: str) -> Any:
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


def _colour_value(v: Any) -> Any:
    if isinstance(v, dict):
        css = colour_to_css(v)
        return css if css else UNSUPPORTED
    if isinstance(v, str) and not v.strip().startswith("{"):
        return v
    return UNSUPPORTED                           # a reference inside a composite


def _shadow(layers: List[Any]) -> Any:
    out = []
    for layer in layers:
        if not isinstance(layer, dict):
            return UNSUPPORTED
        parts = [_dimension(layer.get(k), "dimension")
                 for k in ("offsetX", "offsetY", "blur", "spread")]
        colour = _colour_value(layer.get("color"))
        if UNSUPPORTED in parts or colour is UNSUPPORTED:
            return UNSUPPORTED
        out.append(("inset " if layer.get("inset") else "") + " ".join(parts + [colour]))
    return ", ".join(out)


def _bezier(v: Any) -> Any:
    if isinstance(v, list) and len(v) == 4 and all(isinstance(x, (int, float)) for x in v):
        return f"cubic-bezier({', '.join(_fmt(x) for x in v)})"
    return v if isinstance(v, str) and not v.startswith("{") else UNSUPPORTED


def convert(value: Any, kind: Optional[str]) -> Any:
    """A 2025.10 $value as the string the scripts read, or UNSUPPORTED."""
    if isinstance(value, dict) and "$ref" in value:
        alias = pointer_alias(value["$ref"])
        return "{" + alias + "}" if alias else UNSUPPORTED
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    k = (kind or "").lower()
    if isinstance(value, dict):
        if "colorSpace" in value or k == "color":
            return _colour_value(value)
        if k in ("dimension", "duration", "") and "value" in value and "unit" in value:
            return _dimension(value, k)
        if k == "shadow":
            return _shadow([value])
        if k == "border":
            parts = (_dimension(value.get("width"), "dimension"), value.get("style"),
                     _colour_value(value.get("color")))
            if UNSUPPORTED in parts or not isinstance(parts[1], str):
                return UNSUPPORTED
            return " ".join(parts)
        if k == "transition":
            parts = (_dimension(value.get("duration"), "duration"),
                     _bezier(value.get("timingFunction")),
                     _dimension(value.get("delay", {"value": 0, "unit": "ms"}), "duration"))
            return UNSUPPORTED if UNSUPPORTED in parts else " ".join(parts)
        return UNSUPPORTED                       # typography, gradient, strokeStyle, …
    if isinstance(value, list):
        if k == "cubicbezier":
            return _bezier(value)
        if k == "shadow":
            return _shadow(value)
        if k in ("fontfamily", "") and value and all(isinstance(x, str) for x in value):
            return ", ".join(f'"{x}"' if " " in x else x for x in value)
    return UNSUPPORTED


def pointer_alias(ref: Any) -> Optional[str]:
    """`#/color/neutral/500` or `#/color/neutral/500/$value` -> `color.neutral.500`.
    A pointer into part of a value (…/$value/components/0) has no alias form."""
    if not isinstance(ref, str):
        return None
    s = ref.strip()
    if s.startswith("{") and s.endswith("}"):
        return s[1:-1]
    if not s.startswith("#/"):
        return None
    parts = [p.replace("~1", "/").replace("~0", "~") for p in s[2:].split("/")]
    if parts and parts[-1] == "$value":
        parts = parts[:-1]
    if not parts or any(p.startswith("$") for p in parts):
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
                     problems: List[Tuple[str, str]], active: set) -> None:
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


def _token(node: dict, path: List[str], kind: Optional[str],
           problems: List[Tuple[str, str]]) -> Optional[dict]:
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
        value = convert(node["$value"], kind)
        if value is UNSUPPORTED:
            problems.append((name, f"a {kind or 'untyped'} value in a form this script "
                                   f"cannot write as CSS yet ({_short(node['$value'])})"))
            return None
        tok["$value"] = value
    if kind and "$type" not in tok:
        tok["$type"] = kind
    deprecated = node.get("$deprecated")
    if deprecated:
        note = "deprecated" + (f": {deprecated}" if isinstance(deprecated, str) else "")
        tok["$description"] = " ".join(x for x in (node.get("$description"), f"({note})") if x)
    return tok


def _short(value: Any) -> str:
    text = str(value)
    return text if len(text) <= 60 else text[:57] + "..."


def _walk(node: Any, path: List[str], kind: Optional[str],
          problems: List[Tuple[str, str]]) -> Any:
    if not isinstance(node, dict):
        return node
    if "$value" in node or "$ref" in node:
        return _token(node, path, kind, problems)
    group_kind = node.get("$type", kind)
    out: Dict[str, Any] = {}
    for key, child in node.items():
        if key in META_KEYS:
            out[key] = child
        elif key == "$root":                     # the group's own token: same path
            tok = _token(child, path, group_kind, problems) if isinstance(child, dict) else None
            if tok is not None:
                out[key] = tok
        else:
            walked = _walk(child, path + [key], group_kind, problems)
            if walked is not None:
                out[key] = walked
    return out


def normalise(data: Any) -> Tuple[Any, List[Tuple[str, str]]]:
    """(the document in string forms, [(token path, problem)])."""
    problems: List[Tuple[str, str]] = []
    if not isinstance(data, dict):
        return data, problems
    doc = copy.deepcopy(data)
    _resolve_extends(doc, doc, [], problems, set())
    return _walk(doc, [], None, problems), problems
