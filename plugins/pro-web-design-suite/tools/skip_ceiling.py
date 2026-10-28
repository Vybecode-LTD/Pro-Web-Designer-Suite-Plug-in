"""Fail a CI leg on which more tests skipped than its ceiling. Standard library only.

usage: python tools/skip_ceiling.py LOG --max N

LOG is the unittest run's output; its last summary line ("OK (skipped=5)",
"FAILED (failures=1, skipped=13)") gives the count. A leg passed however many
tests skipped (OPS-13, P67), so a tool that went missing turned its tests into
skips and the leg stayed green; the browser skips also fail on their own, under
WDS_REQUIRE_BROWSER. Prints the count and the ceiling.

Exit codes: 0 at or under the ceiling, 1 over it, 2 when LOG has no summary line.
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys

SUMMARY = re.compile(r"^(?:OK|FAILED)(?: \((?P<counts>[^)]*)\))?\s*$", re.M)


def skipped(text: str) -> int | None:
    """The skip count in a unittest run's last summary line, or None when it has none."""
    found = list(SUMMARY.finditer(text))
    if not found:
        return None
    m = re.search(r"\bskipped=(\d+)", found[-1].group("counts") or "")
    return int(m.group(1)) if m else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("log", type=pathlib.Path)
    parser.add_argument("--max", type=int, required=True, help="the most tests this leg may skip")
    args = parser.parse_args(argv)
    try:
        count = skipped(args.log.read_text(encoding="utf-8", errors="replace"))
    except OSError as exc:
        print(f"skip_ceiling: cannot read {args.log}: {exc}", file=sys.stderr)
        return 2
    if count is None:
        print(f"skip_ceiling: {args.log} has no unittest summary line", file=sys.stderr)
        return 2
    print(f"{count} tests skipped; this leg allows {args.max}")
    if count > args.max:
        print(f"skip_ceiling: {count} skipped is over the ceiling of {args.max}: a tool or a browser "
              "may have gone missing. Read the skips in the suite's log.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
