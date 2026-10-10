"""What figma_to_tokens.py and figma_audit.py share: one reader for every shape
of Figma export, and the colour and value helpers it needs.

Not a command. Both scripts import it, so the converter and the audit read a
file the same way by construction: the same variables, collections, modes and
types. Copied apart, the two readers drifted (LC-C3): the audit split a records
export's modes into one variable each, which figma_to_tokens had stopped doing.

Dependency-free (Python 3.9+, stdlib only), like dtcg.py beside it.
"""

from __future__ import annotations

import json
import math
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union

sys.dont_write_bytecode = True
try:                                              # python -m scripts.<script>
    from . import dtcg                            # type: ignore[import-not-found]
except ImportError:                               # python scripts/<script>.py
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import dtcg                                   # type: ignore[no-redef]

__all__ = [
    "dtcg",
    "PX_PER_REM",
    "srgb_to_linear",
    "linear_to_srgb",
    "linear_srgb_to_oklab",
    "oklab_to_linear_srgb",
    "oklch_to_oklab",
    "oklch_to_rgb",
    "rgb_to_hex",
    "as_color",
    "as_px",
    "as_ms",
    "as_alias",
    "TIER_PREFIXES",
    "slugify",
    "FVar",
    "FCollection",
    "FDoc",
    "detect_shape",
    "parse_rest",
    "parse_plugin",
    "parse_records",
    "dtcg_type",
    "parse_dtcg",
    "load_document",
    "attach_styles",
]


# ===========================================================================
# Colour maths: the same matrices and transfer function as
# web-design-studio/scripts/generate_color_ramp.py.
# ===========================================================================

PX_PER_REM = 16.0


def srgb_to_linear(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def linear_to_srgb(c: float) -> float:
    return c * 12.92 if c <= 0.0031308 else 1.055 * (c ** (1 / 2.4)) - 0.055


def linear_srgb_to_oklab(r: float, g: float, b: float) -> Tuple[float, float, float]:
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l_ = math.copysign(abs(l) ** (1 / 3), l)
    m_ = math.copysign(abs(m) ** (1 / 3), m)
    s_ = math.copysign(abs(s) ** (1 / 3), s)
    return (
        0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_,
        1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_,
        0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_,
    )


def oklab_to_linear_srgb(L: float, a: float, b: float) -> Tuple[float, float, float]:
    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b
    l, m, s = l_ ** 3, m_ ** 3, s_ ** 3
    return (
        +4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
        -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
        -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s,
    )


def oklch_to_oklab(L: float, C: float, H: float) -> Tuple[float, float, float]:
    rad = math.radians(H)
    return (L, C * math.cos(rad), C * math.sin(rad))


def oklch_to_rgb(L_pct: float, C: float, H: float) -> Tuple[float, float, float]:
    """OKLCH (L in percent) -> sRGB 0..1, clamped to gamut."""
    lr, lg, lb = oklab_to_linear_srgb(*oklch_to_oklab(L_pct / 100.0, C, H))
    return tuple(min(1.0, max(0.0, linear_to_srgb(c))) for c in (lr, lg, lb))  # type: ignore


def rgb_to_hex(r: float, g: float, b: float) -> str:
    return "#" + "".join(f"{round(min(1.0, max(0.0, c)) * 255):02x}" for c in (r, g, b))


# ===========================================================================
# Values. Figma hands you numbers; plugins hand you strings; DTCG hands you
# strings with units. All three have to arrive here as the same thing.
# ===========================================================================

_HEX = re.compile(r"^#?([0-9a-fA-F]{3,8})$")

_RGB_FN = re.compile(r"^rgba?\(([^)]*)\)$", re.I)

_OKLCH_FN = re.compile(r"^oklch\(([^)]*)\)$", re.I)

_NUM_UNIT = re.compile(r"^(-?\d*\.?\d+)\s*(px|rem|em|pt|%|ms|s)?$", re.I)


def as_color(value: Any) -> Optional[Tuple[float, float, float, float]]:
    """Return (r, g, b, a) in 0..1, or None if this is not a colour."""
    if isinstance(value, dict):
        if all(k in value for k in ("r", "g", "b")):
            try:
                return (float(value["r"]), float(value["g"]), float(value["b"]),
                        float(value.get("a", 1.0)))
            except (TypeError, ValueError):
                return None
        # VariableComposedColor (Sept 2026): colour and opacity authored apart.
        # Figma gives `opacity` as a PERCENTAGE, 0-100; read as 0-1, every
        # translucent hover and scrim was audited as opaque.
        if "color" in value:
            base = as_color(value["color"])
            if base is None:
                return None
            if isinstance(value.get("opacity"), (int, float)):
                return (base[0], base[1], base[2], base[3] * float(value["opacity"]) / 100.0)
            if isinstance(value.get("alpha"), (int, float)):
                return (base[0], base[1], base[2], float(value["alpha"]))
            return base                      # an alias in the opacity channel
        return None
    if not isinstance(value, str):
        return None
    raw = value.strip()
    m = _HEX.match(raw)
    if m and raw.startswith("#"):
        h = m.group(1)
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        elif len(h) == 4:
            h = "".join(c * 2 for c in h)
        if len(h) == 6:
            h += "ff"
        if len(h) != 8:
            return None
        v = [int(h[i:i + 2], 16) / 255.0 for i in range(0, 8, 2)]
        return (v[0], v[1], v[2], v[3])
    m = _RGB_FN.match(raw)
    if m:
        parts = [p.strip() for p in re.split(r"[,\s/]+", m.group(1)) if p.strip()]
        try:
            chans = []
            for p in parts[:3]:
                chans.append(float(p[:-1]) / 100.0 if p.endswith("%") else float(p) / 255.0)
            alpha = 1.0
            if len(parts) > 3:
                a = parts[3]
                alpha = float(a[:-1]) / 100.0 if a.endswith("%") else float(a)
            return (chans[0], chans[1], chans[2], alpha)
        except (ValueError, IndexError):
            return None
    m = _OKLCH_FN.match(raw)
    if m:
        parts = [p.strip() for p in re.split(r"[\s/]+", m.group(1)) if p.strip()]
        try:
            L = float(parts[0][:-1]) if parts[0].endswith("%") else float(parts[0]) * 100.0
            C = float(parts[1])
            H = float(parts[2].rstrip("deg")) if len(parts) > 2 else 0.0
            alpha = 1.0
            if len(parts) > 3:
                a = parts[3]
                alpha = float(a[:-1]) / 100.0 if a.endswith("%") else float(a)
            r, g, b = oklch_to_rgb(L, C, H)
            return (r, g, b, alpha)
        except (ValueError, IndexError):
            return None
    return None


def as_px(value: Any) -> Optional[float]:
    """Return a pixel number, or None. Bare numbers are px -- that is what a
    Figma FLOAT variable is."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str):
        return None
    m = _NUM_UNIT.match(value.strip())
    if not m:
        return None
    n, unit = float(m.group(1)), (m.group(2) or "px").lower()
    if unit == "px":
        return n
    if unit in ("rem", "em"):
        return n * PX_PER_REM
    if unit == "pt":
        return n * 4.0 / 3.0
    return None


def as_ms(value: Any) -> Optional[float]:
    """Return milliseconds, or None. A bare number is milliseconds."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    if isinstance(value, str):
        m = _NUM_UNIT.match(value.strip())
        if m:
            n, unit = float(m.group(1)), (m.group(2) or "ms").lower()
            return n * 1000.0 if unit == "s" else n
    return None


def as_alias(value: Any) -> Optional[str]:
    """Return the alias target (a variable id, or a dotted/slashed path)."""
    if isinstance(value, dict):
        if value.get("type") == "VARIABLE_ALIAS" and "id" in value:
            return str(value["id"])
        for key in ("alias", "aliasTo", "variableAlias"):
            if key in value and isinstance(value[key], str):
                return value[key]
        return None
    if isinstance(value, str):
        s = value.strip()
        if s.startswith("{") and s.endswith("}"):
            return s[1:-1]
        if s.startswith("$") and len(s) > 1 and not s.startswith("$#"):
            return s[1:]
    return None


# ===========================================================================
# The document model, and one reader per export shape
# ===========================================================================

TIER_PREFIXES = {
    "primitive", "primitives", "core", "global", "base", "raw", "foundation",
    "semantic", "semantics", "alias", "aliases", "theme", "themes", "role", "roles",
    "component", "components", "token", "tokens", "design", "ds",
}


def slugify(name: str) -> str:
    """`Primitive/Space/6` -> `space-6`. Figma's `/` grouping is the same
    grammar as `--category-role-variant`; this is the round trip."""
    parts = [p.strip() for p in str(name).replace("\\", "/").split("/") if p.strip()]
    while len(parts) > 1 and parts[0].strip().lower() in TIER_PREFIXES:
        parts = parts[1:]
    slug = "-".join(parts).lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug).strip("-")
    return re.sub(r"-{2,}", "-", slug)


@dataclass
class FVar:
    name: str
    collection: str
    resolved_type: str
    values: Dict[str, Any] = field(default_factory=dict)   # mode name -> raw value
    scopes: List[str] = field(default_factory=list)
    code_syntax: Dict[str, str] = field(default_factory=dict)
    description: str = ""
    var_id: str = ""
    # DTCG `$deprecated`, the token's own or a group's: true, or the reason.
    deprecated: Union[bool, str] = False

    @property
    def slug(self) -> str:
        return slugify(self.name)

    @property
    def described(self) -> str:
        """The description, with a note when the token is deprecated."""
        if not self.deprecated:
            return self.description
        note = "deprecated" + (f": {self.deprecated}" if isinstance(self.deprecated, str) else "")
        return " ".join(x for x in (self.description, f"({note})") if x)


@dataclass
class FCollection:
    name: str
    modes: List[str] = field(default_factory=list)
    default_mode: str = ""


@dataclass
class FDoc:
    shape: str
    collections: Dict[str, FCollection] = field(default_factory=dict)
    variables: List[FVar] = field(default_factory=list)
    text_styles: List[dict] = field(default_factory=list)
    effect_styles: List[dict] = field(default_factory=list)
    by_id: Dict[str, FVar] = field(default_factory=dict)
    notes: List[str] = field(default_factory=list)
    # (token path, why) for DTCG values this script cannot read; each one is a
    # finding, because an unaudited token must never look like a clean one.
    unsupported: List[Tuple[str, str]] = field(default_factory=list)


def _is_leaf_token(node: Any) -> bool:
    return isinstance(node, dict) and ("$value" in node or "value" in node)


def detect_shape(data: Any) -> str:
    if isinstance(data, list):
        return "records"
    if not isinstance(data, dict):
        raise ValueError("top level of the file is neither an object nor an array")
    meta = data.get("meta")
    if isinstance(meta, dict) and ("variables" in meta or "variableCollections" in meta):
        return "rest"
    if isinstance(data.get("collections"), list):
        return "plugin"
    if isinstance(data.get("variables"), list):
        return "records"
    if isinstance(data.get("variables"), dict) and isinstance(data.get("variableCollections"), dict):
        return "rest"
    return "dtcg"


def parse_rest(data: dict) -> FDoc:
    meta = data.get("meta", data)
    raw_cols = meta.get("variableCollections", {}) or {}
    raw_vars = meta.get("variables", {}) or {}
    doc = FDoc(shape="rest")
    mode_names: Dict[str, Dict[str, str]] = {}      # collection id -> modeId -> name
    col_of: Dict[str, str] = {}                      # collection id -> collection name
    for cid, col in raw_cols.items():
        cname = col.get("name") or cid
        modes = col.get("modes") or []
        names, seen = [], {}
        for m in modes:
            mid = m.get("modeId") or m.get("id") or ""
            mn = m.get("name") or mid or "Mode"
            if mn in seen:                            # duplicate mode labels happen
                mn = f"{mn} ({mid})"
            seen[mn] = True
            names.append(mn)
            mode_names.setdefault(cid, {})[mid] = mn
        default_id = col.get("defaultModeId") or (modes[0].get("modeId") if modes else "")
        doc.collections[cname] = FCollection(
            name=cname, modes=names,
            default_mode=mode_names.get(cid, {}).get(default_id, names[0] if names else "Value"),
        )
        col_of[cid] = cname
    for vid, v in raw_vars.items():
        cid = v.get("variableCollectionId", "")
        cname = col_of.get(cid, "(unknown collection)")
        if cname not in doc.collections:
            doc.collections[cname] = FCollection(name=cname, modes=["Value"], default_mode="Value")
        values: Dict[str, Any] = {}
        for mid, val in (v.get("valuesByMode") or {}).items():
            values[mode_names.get(cid, {}).get(mid, mid)] = val
        fv = FVar(
            name=v.get("name", vid), collection=cname,
            resolved_type=(v.get("resolvedType") or "").upper(),
            values=values, scopes=list(v.get("scopes") or []),
            code_syntax=dict(v.get("codeSyntax") or {}),
            description=v.get("description") or "", var_id=vid,
        )
        doc.variables.append(fv)
        doc.by_id[vid] = fv
        if v.get("key"):
            doc.by_id.setdefault(str(v["key"]), fv)
    return doc


def parse_plugin(data: dict) -> FDoc:
    """The `{"collections": [...]}` family. Two sub-shapes exist in the wild:
    variables listed once per mode, and variables listed once with valuesByMode.
    Both arrive here."""
    doc = FDoc(shape="plugin")
    for col in data.get("collections", []):
        if not isinstance(col, dict):
            continue
        cname = col.get("name") or "tokens"
        raw_modes = col.get("modes") or []
        mode_labels: List[str] = []
        merged: Dict[str, FVar] = {}
        # A flat variable's valuesByMode is keyed by mode id; the collection
        # lists modes by name. Read both as the name.
        name_of = {str(m["modeId"]): str(m.get("name") or m["modeId"])
                   for m in raw_modes if isinstance(m, dict) and m.get("modeId")}

        def _ingest(entry: dict, mode: str) -> None:
            if not isinstance(entry, dict) or "name" not in entry:
                return
            key = str(entry["name"])
            fv = merged.get(key)
            if fv is None:
                fv = FVar(
                    name=key, collection=cname,
                    resolved_type=str(entry.get("type") or entry.get("resolvedType") or "").upper(),
                    scopes=list(entry.get("scopes") or []),
                    code_syntax=dict(entry.get("codeSyntax") or {}),
                    description=entry.get("description") or "",
                    var_id=str(entry.get("id") or key),
                )
                merged[key] = fv
                doc.by_id.setdefault(fv.var_id, fv)
                doc.by_id.setdefault(key, fv)
            vbm = entry.get("valuesByMode")
            if isinstance(vbm, dict):
                for mk, mv in vbm.items():
                    label = name_of.get(str(mk), str(mk))
                    fv.values[label] = mv
                    if label not in mode_labels:
                        mode_labels.append(label)
            elif "value" in entry or "$value" in entry:
                fv.values[mode] = entry.get("value", entry.get("$value"))

        # Sub-shape 1: modes carry their own variable lists.
        nested = False
        for m in raw_modes:
            if isinstance(m, dict) and isinstance(m.get("variables"), list):
                nested = True
                mname = m.get("name") or m.get("modeId") or "Value"
                if mname not in mode_labels:
                    mode_labels.append(mname)
                for entry in m["variables"]:
                    _ingest(entry, mname)
            elif isinstance(m, dict):
                mn = m.get("name") or m.get("modeId") or "Value"
                if mn not in mode_labels:
                    mode_labels.append(mn)
            elif isinstance(m, str) and m not in mode_labels:
                mode_labels.append(m)
        # Sub-shape 2: a flat variable list with valuesByMode.
        if not nested:
            for entry in col.get("variables", []) or []:
                _ingest(entry, mode_labels[0] if mode_labels else "Value")
        if not mode_labels:
            mode_labels = ["Value"]
        default = col.get("defaultMode") or col.get("defaultModeId") or mode_labels[0]
        default = name_of.get(str(default), default)
        if default not in mode_labels:
            default = mode_labels[0]
        doc.collections[cname] = FCollection(cname, mode_labels, default)
        doc.variables.extend(merged.values())
    return doc


def parse_records(data: Any, collection: str) -> FDoc:
    rows = data if isinstance(data, list) else (data.get("variables") or [])
    doc = FDoc("records")
    doc.collections[collection] = FCollection(collection, ["Value"], "Value")
    # Rows are one (collection, name, mode) triple each. Like `parse_plugin`'s
    # `_ingest`, merge rows that share (collection, name) into one FVar with a
    # multi-mode `values` dict -- otherwise each mode becomes its own variable,
    # and `Converter.blocks()` cannot tell "no value for :root" from "this is
    # the only mode", so it treats every split-off variable as its own default
    # and every mode collapses onto `:root`.
    merged: Dict[Tuple[str, str], FVar] = {}
    for row in rows:
        if not isinstance(row, dict) or "name" not in row:
            continue
        cname = row.get("collection") or collection
        mode = row.get("mode", "Value")
        doc.collections.setdefault(cname, FCollection(cname, [], mode))
        if mode not in doc.collections[cname].modes:
            doc.collections[cname].modes.append(mode)
        if not doc.collections[cname].default_mode:
            doc.collections[cname].default_mode = mode
        key = (cname, str(row["name"]))
        fv = merged.get(key)
        if fv is None:
            fv = FVar(str(row["name"]), cname,
                      str(row.get("type") or row.get("resolvedType") or "").upper(),
                      {}, list(row.get("scopes") or []), {}, row.get("description") or "",
                      str(row.get("id") or row["name"]))
            merged[key] = fv
            doc.variables.append(fv)
            doc.by_id.setdefault(fv.var_id, fv)
            doc.by_id.setdefault(fv.name, fv)
        fv.values[mode] = row.get("value", row.get("$value"))
    return doc


def dtcg_type(declared: Optional[str], value: Any) -> str:
    if declared:
        d = declared.lower()
        if d == "color":
            return "COLOR"
        if d in ("dimension", "number", "duration", "fontweight", "font-weight"):
            return "FLOAT"
        if d in ("fontfamily", "font-family", "string", "cubicbezier", "shadow", "typography"):
            return "STRING"
        if d == "boolean":
            return "BOOLEAN"
    if isinstance(value, bool):
        return "BOOLEAN"
    if as_color(value) is not None:
        return "COLOR"
    if as_px(value) is not None:
        return "FLOAT"
    return "STRING"


def parse_dtcg(data: dict, collection: str) -> FDoc:
    doc = FDoc(shape="dtcg")
    doc.collections[collection] = FCollection(collection, ["Value"], "Value")
    # 2025.10 objects, $ref, $extends and group $type become the string forms
    # the checks read; anything unreadable is kept as a finding.
    data, doc.unsupported = dtcg.normalise(data)
    reserved = dtcg.META_KEYS | {"$value"}

    def walk(node: Any, path: List[str]) -> None:
        if _is_leaf_token(node):
            name = "/".join(path)
            fv = FVar(
                name=name, collection=collection,
                resolved_type=dtcg_type(node.get("$type") or node.get("type"),
                                        node.get("$value", node.get("value"))),
                values={"Value": node.get("$value", node.get("value"))},
                description=node.get("$description") or node.get("description") or "",
                var_id=name,
                deprecated=node.get("$deprecated") or False,
            )
            doc.variables.append(fv)
            doc.by_id.setdefault(name, fv)
            doc.by_id.setdefault(".".join(path), fv)
            return
        if isinstance(node, dict):
            for k, v in node.items():
                if k == "$root":                   # the group's own token
                    walk(v, path)
                elif k not in reserved:
                    walk(v, path + [str(k)])

    walk(data, [])
    return doc


def load_document(path: Path, forced: Optional[str], collection: str) -> FDoc:
    data = json.loads(path.read_bytes())
    shape = forced or detect_shape(data)
    if shape == "rest":
        doc = parse_rest(data)
    elif shape == "plugin":
        doc = parse_plugin(data)
    elif shape == "records":
        doc = parse_records(data, collection)
    else:
        doc = parse_dtcg(data, collection)
    attach_styles(doc, data)
    # Fill in types the source omitted, from the value itself.
    for v in doc.variables:
        if v.resolved_type not in ("COLOR", "FLOAT", "STRING", "BOOLEAN"):
            sample = next((x for x in v.values.values() if as_alias(x) is None), None)
            v.resolved_type = dtcg_type(None, sample)
    return doc


def attach_styles(doc: FDoc, data: Any) -> None:
    if not isinstance(data, dict):
        return
    buckets: List[Any] = [data.get("textStyles"), data.get("effectStyles")]
    meta = data.get("meta")
    if isinstance(meta, dict):
        buckets += [meta.get("styles"), meta.get("textStyles"), meta.get("effectStyles")]
    buckets.append(data.get("styles"))
    for bucket in buckets:
        rows: Iterable[Any]
        if isinstance(bucket, dict):
            rows = [{**v, "key": k} for k, v in bucket.items() if isinstance(v, dict)]
        elif isinstance(bucket, list):
            rows = [r for r in bucket if isinstance(r, dict)]
        else:
            continue
        for row in rows:
            st = str(row.get("styleType") or row.get("style_type") or row.get("type") or "").upper()
            if st == "TEXT" or ("fontSize" in row or "style" in row):
                if row not in doc.text_styles:
                    doc.text_styles.append(row)
            elif st == "EFFECT" or "effects" in row:
                if row not in doc.effect_styles:
                    doc.effect_styles.append(row)
