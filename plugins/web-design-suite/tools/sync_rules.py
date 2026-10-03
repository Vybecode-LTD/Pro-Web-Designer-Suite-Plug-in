"""Write the rule spec's data into the gates that restate it, so a change to
what a gate accepts is one edit to skills/web-design-studio/assets/rules/
design-rules.json and a rerun. Standard library only; Python 3.9 or newer.

usage:
    python tools/sync_rules.py            rewrite every block from the spec
    python tools/sync_rules.py --check    exit 1 and list the stale blocks

Each gate holds one block between a `BEGIN design-rules` comment line and an
`END design-rules` one. Everything between them is written here; everything
outside them is the gate's own. A block holds the constants its gate uses
(TARGETS), from:
  LAYER_ORDER, LAYER_STATEMENT   layers.order, layers.statement
  MAX_NESTING                    nesting.max_depth
  SYSTEM_COLOR_NAMES             system_colors.names
  SYSTEM_COLOR_PROPERTY          system_colors.properties
  KEYWORDS, COLOUR_FUNCTIONS     values.keywords, values.colour_functions
  LITERAL_UNITS                  inline_styles.literal_units
  GEOMETRY_PROPERTIES            geometry.properties
  COLOUR_WORDS                   values.colour_words and the system colours
  SHAPES                         every shape in values.shapes, each a constant
                                 of its own name (VAR_SEQ, VAR_ONE, …)
  VALUE_ALLOWLIST                values.families: each property and its values
  MARGIN_ALLOWLIST               margins_in_components.properties and .values
  MARGIN_VALUES                  margins_in_components.values (the audit's form)
  BINDING_ALLOWLIST              bindings.allow, keyed by property pattern
  BINDING_VALUES                 the same, as (pattern, allowed) pairs for the audit
  <FAMILY>_VALUES                one family's properties and values (SIZING_VALUES)
(The markers avoid "@generated": the audit and the migration tool skip a
file that says it in its first 800 characters.)
Files are written as UTF-8 with LF line endings, byte for byte the same on
every rerun. Exit codes: 0 in step (or rewritten), 1 stale (--check), a gate
without its block, or a spec this tool cannot write.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

PLUGIN = pathlib.Path(__file__).resolve().parents[1]
SPEC = "skills/web-design-studio/assets/rules/design-rules.json"
# Each gate, its language, and the constants it uses, in the order they are
# written (COLOUR_WORDS reads SYSTEM_COLOR_NAMES, the allowlists the shapes).
TARGETS = {
    "skills/web-design-studio/scripts/audit_design.py":
        ("py", ("LAYER_ORDER", "LAYER_STATEMENT", "MAX_NESTING", "SYSTEM_COLOR_NAMES", "SYSTEM_COLOR_PROPERTY",
                "KEYWORDS", "COLOUR_FUNCTIONS", "LITERAL_UNITS", "GEOMETRY_PROPERTIES", "COLOUR_WORDS", "SHAPES",
                "SPACING_VALUES", "STROKE_VALUES", "MOTION_VALUES", "SIZING_VALUES", "MARGIN_VALUES",
                "BINDING_VALUES")),
    "skills/web-design-studio/assets/configs/stylelint.config.mjs":
        ("js", ("LAYER_ORDER", "MAX_NESTING", "SYSTEM_COLOR_NAMES", "SYSTEM_COLOR_PROPERTY", "KEYWORDS",
                "COLOUR_FUNCTIONS", "COLOUR_WORDS", "SHAPES", "VALUE_ALLOWLIST", "MARGIN_ALLOWLIST",
                "BINDING_ALLOWLIST")),
    "skills/web-design-studio/assets/configs/eslint.design.config.mjs":
        ("js", ("COLOUR_FUNCTIONS", "LITERAL_UNITS")),
}
NOTE = "written by tools/sync_rules.py from assets/rules/design-rules.json; edit the spec, then rerun it"
LISTS = ("KEYWORDS", "COLOUR_WORDS")         # the names a family's `values` may use besides the shapes


class SpecError(ValueError):
    """The spec holds something this tool cannot write into a gate."""


def wrapped(items: list[str], head: str, tail: str, indent: str, width: int = 100) -> str:
    """`head` + items joined with ", " + `tail`, on one line when it fits,
    else one indented line per run of items that fits."""
    one = head + ", ".join(items) + tail
    if len(one) <= width:
        return one
    lines, line = [], indent
    for item in items:
        piece = item + ","
        if len(line) + len(piece) + 1 > width and line.strip():
            lines.append(line.rstrip())
            line = indent
        line += piece + " "
    lines.append(line.rstrip())
    return head.rstrip() + "\n" + "\n".join(lines) + "\n" + tail.lstrip()


def js_string(text: str) -> str:
    if "'" in text or "\\" in text:
        raise SpecError(f"cannot write {text!r} as a plain JavaScript string")
    return f"'{text}'"


def js_entry(entry: str, shapes: dict, written: tuple[str, ...]) -> str:
    """One allowed value: a shape or a list by name, else the value itself. A
    name must be one the block writes before the allowlist that reads it, or
    the config would name a constant it never declares."""
    if entry in shapes or entry in LISTS:
        if entry not in written:
            raise SpecError(f"an allowlist reads {entry}, which the block does not write before it")
        return "...KEYWORDS" if entry == "KEYWORDS" else entry
    if re.fullmatch(r"[A-Z][A-Z_]*", entry):
        raise SpecError(f"{entry} is neither a shape in values.shapes nor one of {', '.join(LISTS)}")
    return js_string(entry)


def js_allowlist(name: str, groups: list[tuple[str, list[dict]]], shapes: dict, written: tuple[str, ...]) -> str:
    """`const NAME = { property: [values], … };`, one line per property, under
    a comment for each named group."""
    lines = [f"const {name} = {{"]
    for title, allow in groups:
        if title:
            lines.append(f"  // {title}")
        for group in allow:
            values = ", ".join(js_entry(v, shapes, written) for v in group["values"])
            for prop in group["properties"]:
                key = prop if re.fullmatch(r"[a-z]+", prop) else js_string(prop)
                lines.append(f"  {key}: [{values}],")
    return "\n".join(lines + ["};"])


def block(spec: dict, lang: str, names: tuple[str, ...]) -> str:
    values = spec["values"]
    data = {"LAYER_ORDER": spec["layers"]["order"], "LAYER_STATEMENT": spec["layers"]["statement"],
            "MAX_NESTING": int(spec["nesting"]["max_depth"]), "SYSTEM_COLOR_NAMES": spec["system_colors"]["names"],
            "KEYWORDS": values["keywords"], "COLOUR_FUNCTIONS": values["colour_functions"],
            "LITERAL_UNITS": spec["inline_styles"]["literal_units"],
            "GEOMETRY_PROPERTIES": spec["geometry"]["properties"]}
    py = lang == "py"
    text = (lambda s: json.dumps(s)) if py else js_string
    names = tuple(n for name in names for n in (tuple(values["shapes"]) if name == "SHAPES" else (name,)))
    lines = []
    for n, name in enumerate(names):
        if name not in data:
            lines.append((py_constant if py else js_constant)(name, spec, names[:n]))
            continue
        value = data[name]
        head, tail = (f"{name} = ", "") if py else (f"const {name} = ", ";")
        if isinstance(value, list):
            lines.append(wrapped([text(v) for v in value], head + "[", "]" + tail, "    " if py else "  "))
        else:
            lines.append(head + (str(value) if isinstance(value, int) else text(value)) + tail)
    mark = "#" if py else "//"
    return f"{mark} BEGIN design-rules: {NOTE}\n" + "\n".join(lines) + f"\n{mark} END design-rules"


def written_before(name: str, before: tuple[str, ...], reader: str) -> None:
    if name not in before:
        raise SpecError(f"{reader} reads {name}, so the block must write {name} first")


def raw_pattern(name: str, pattern: str, lang: str) -> str:
    """A regular expression's source as a raw literal of the gate's language."""
    if lang == "py":
        if '"' in pattern or pattern.endswith("\\"):
            raise SpecError(f"the {name} pattern cannot sit in a Python raw string")
        return f'r"{pattern}"'
    if "`" in pattern or "${" in pattern:
        raise SpecError(f"the {name} pattern cannot sit in a String.raw template")
    return f"String.raw`{pattern}`"


def family_of(name: str, spec: dict) -> dict | None:
    """The family a `<FAMILY>_VALUES` name stands for (SIZING_VALUES: sizing)."""
    m = re.fullmatch(r"([A-Z]+)_VALUES", name)
    return spec["values"]["families"].get(m.group(1).lower()) if m else None


def py_entries(values: list[str], shapes: dict, before: tuple[str, ...], reader: str) -> str:
    """Allowed values as the inside of a Python tuple: a shape or a list by
    name, which the block must write first, else the value as a string."""
    entries = []
    for entry in values:
        if entry in shapes or entry in LISTS:
            written_before(entry, before, reader)
            entries.append(f"*{entry}" if entry == "KEYWORDS" else entry)
        elif re.fullmatch(r"[A-Z][A-Z_]*", entry):
            raise SpecError(f"{entry} has no Python form for {reader}")
        else:
            entries.append(json.dumps(entry))
    return ", ".join(entries) + ("," if len(entries) == 1 else "")


def property_pattern(prop: str, reader: str) -> str:
    """A `/…/` property key's source, for re.compile."""
    m = re.fullmatch(r"/(.+)/", prop)
    if not m:
        raise SpecError(f"{reader}: {prop!r} is not a /pattern/ property key")
    return m.group(1)


def py_constant(name: str, spec: dict, before: tuple[str, ...]) -> str:
    """The Python forms: a shape, the system-colour properties, the colour
    words, the component margins, the theme bindings as (pattern, allowed)
    pairs, or one family as {property: (allowed, …)}, a shape compiled and a
    value matched exactly."""
    shapes = spec["values"]["shapes"]
    if name in shapes:
        return f"{name} = re.compile({raw_pattern(name, shapes[name]['pattern'], 'py')})"
    if name == "SYSTEM_COLOR_PROPERTY":
        return f"{name} = re.compile({raw_pattern(name, spec['system_colors']['properties'], 'py')}, re.I)"
    if name == "COLOUR_WORDS":
        written_before("SYSTEM_COLOR_NAMES", before, name)
        words = ", ".join(json.dumps(w) for w in spec["values"]["colour_words"])
        return f'{name} = re.compile("^(?:" + "|".join([{words}, *SYSTEM_COLOR_NAMES]) + ")$", re.I)'
    if name == "MARGIN_VALUES":
        return f"{name} = ({py_entries(spec['margins_in_components']['values'], shapes, before, name)})"
    if name == "BINDING_VALUES":
        lines = [f"{name} = ("]
        for group in spec["bindings"]["allow"]:
            entries = py_entries(group["values"], shapes, before, name)
            for prop in group["properties"]:
                pattern = raw_pattern(name, property_pattern(prop, name), "py")
                lines.append(f"    (re.compile({pattern}), ({entries})),")
        return "\n".join(lines + [")"])
    family = family_of(name, spec)
    if family is None:
        raise SpecError(f"{name} has no Python form")
    lines = [f"{name} = {{"]
    for group in family["allow"]:
        entries = py_entries(group["values"], shapes, before, name)
        for prop in group["properties"]:
            lines.append(f"    {json.dumps(prop)}: ({entries}),")
    return "\n".join(lines + ["}"])


def js_constant(name: str, spec: dict, before: tuple[str, ...]) -> str:
    """The JavaScript forms of the value rules: a shape, the colour words, the
    system-colour properties, or an allowlist for
    declaration-property-value-allowed-list."""
    values = spec["values"]
    shapes = values["shapes"]
    if name in shapes:
        return f"const {name} = {raw_pattern(name, '/' + shapes[name]['pattern'] + '/', 'js')};"
    if name == "SYSTEM_COLOR_PROPERTY":
        return f"const {name} = new RegExp({raw_pattern(name, spec['system_colors']['properties'], 'js')}, 'i');"
    if name == "COLOUR_WORDS":
        written_before("SYSTEM_COLOR_NAMES", before, name)
        words = ", ".join(js_string(w) for w in values["colour_words"])
        return f"const COLOUR_WORDS = String.raw`/^(?:${{[{words}, ...SYSTEM_COLOR_NAMES].join('|')}})$/i`;"
    if name == "VALUE_ALLOWLIST":
        groups = [(f"{family}: Law{'s' if ',' in rule['laws'] else ''} {rule['laws']}", rule["allow"])
                  for family, rule in values["families"].items()]
        return js_allowlist(name, groups, shapes, before)
    if name == "MARGIN_ALLOWLIST":
        margins = spec["margins_in_components"]
        return js_allowlist(name, [("", [{"properties": margins["properties"], "values": margins["values"]}])],
                            shapes, before)
    if name == "BINDING_ALLOWLIST":
        for group in spec["bindings"]["allow"]:
            for prop in group["properties"]:
                property_pattern(prop, name)
        return js_allowlist(name, [("", spec["bindings"]["allow"])], shapes, before)
    raise SpecError(f"{name} has no JavaScript form")


BLOCK = re.compile(r"^(#|//) BEGIN design-rules\b.*?^\1 END design-rules[^\n]*", re.M | re.S)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--check", action="store_true", help="exit 1 and list the stale blocks; write nothing")
    parser.add_argument("--root", type=pathlib.Path, default=PLUGIN, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    spec = json.loads((args.root / SPEC).read_text(encoding="utf-8"))
    try:                                     # every block first, so a bad spec writes nothing
        blocks = {rel: block(spec, lang, names) for rel, (lang, names) in TARGETS.items()}
    except SpecError as exc:
        print(f"sync_rules: {SPEC}: {exc}", file=sys.stderr)
        return 1
    stale, missing = [], []
    for rel in TARGETS:
        path = args.root / rel
        text = path.read_text(encoding="utf-8")
        found = BLOCK.findall(text)
        if len(found) != 1:
            missing.append(f"{rel}: {len(found)} design-rules blocks, not one")
            continue
        new = BLOCK.sub(lambda _: blocks[rel], text)
        if new != text:
            stale.append(rel)
            if not args.check:
                path.write_bytes(new.encode("utf-8"))
    for line in missing:
        print(f"sync_rules: {line}", file=sys.stderr)
    for rel in stale:
        print(f"{'stale' if args.check else 'rewrote'}: {rel}")
    if args.check and stale:
        print(f"{len(stale)} block(s) differ from {SPEC}; run tools/sync_rules.py", file=sys.stderr)
    return 1 if missing or (args.check and stale) else 0


if __name__ == "__main__":
    sys.exit(main())
