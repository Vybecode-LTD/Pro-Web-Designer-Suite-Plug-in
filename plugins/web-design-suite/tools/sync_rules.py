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
(The markers avoid "@generated": the audit and the migration tool skip a
file that says it in its first 800 characters.)
Files are written as UTF-8 with LF line endings, byte for byte the same on
every rerun. Exit codes: 0 in step (or rewritten), 1 stale (--check) or a
gate without its block.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

PLUGIN = pathlib.Path(__file__).resolve().parents[1]
SPEC = "skills/web-design-studio/assets/rules/design-rules.json"
# Each gate, its language, and the constants it uses.
TARGETS = {
    "skills/web-design-studio/scripts/audit_design.py": ("py", ("LAYER_ORDER", "LAYER_STATEMENT", "MAX_NESTING")),
    "skills/web-design-studio/assets/configs/stylelint.config.mjs":
        ("js", ("LAYER_ORDER", "MAX_NESTING", "SYSTEM_COLOR_NAMES")),
}
NOTE = "written by tools/sync_rules.py from assets/rules/design-rules.json; edit the spec, then rerun it"


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


def block(spec: dict, lang: str, names: tuple[str, ...]) -> str:
    values = {"LAYER_ORDER": spec["layers"]["order"], "LAYER_STATEMENT": spec["layers"]["statement"],
              "MAX_NESTING": int(spec["nesting"]["max_depth"]), "SYSTEM_COLOR_NAMES": spec["system_colors"]["names"]}
    py = lang == "py"
    text = (lambda s: json.dumps(s)) if py else (lambda s: f"'{s}'")
    lines = []
    for name in names:
        value = values[name]
        head, tail = (f"{name} = ", "") if py else (f"const {name} = ", ";")
        if isinstance(value, list):
            lines.append(wrapped([text(v) for v in value], head + "[", "]" + tail, "    " if py else "  "))
        else:
            lines.append(head + (str(value) if isinstance(value, int) else text(value)) + tail)
    mark = "#" if py else "//"
    return f"{mark} BEGIN design-rules: {NOTE}\n" + "\n".join(lines) + f"\n{mark} END design-rules"


BLOCK = re.compile(r"^(#|//) BEGIN design-rules\b.*?^\1 END design-rules[^\n]*", re.M | re.S)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--check", action="store_true", help="exit 1 and list the stale blocks; write nothing")
    parser.add_argument("--root", type=pathlib.Path, default=PLUGIN, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    spec = json.loads((args.root / SPEC).read_text(encoding="utf-8"))
    stale, missing = [], []
    for rel, (lang, names) in TARGETS.items():
        path = args.root / rel
        text = path.read_text(encoding="utf-8")
        found = BLOCK.findall(text)
        if len(found) != 1:
            missing.append(f"{rel}: {len(found)} design-rules blocks, not one")
            continue
        new = BLOCK.sub(lambda _: block(spec, lang, names), text)
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
