"""Check that the execution plan schedules every open item exactly once.

Open items: rows of the inventory whose status does not start with "fixed" or
"done", and the completion plan's N-items whose line does not say "Done for".
Scheduled items: the IDs in the Items column of the execution plan's PR rows.

    python "dev plans/check_execution_plan.py"

Exit 0 when the two sets match and nothing is placed twice; 1 otherwise.
"""
from __future__ import annotations

import collections
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
ID = re.compile(r"\b(?:[A-Z]{2}-[ABC]\d+|N\d+)\b")


def open_items() -> set[str]:
    found = set()
    for line in (HERE / "web-design-suite-completion-inventory.md").read_text(encoding="utf-8").splitlines():
        m = re.match(r"\| ([A-Z]{2}-[ABC]\d+) \| [^|]* \| ([^|]*) \|", line)
        if m and not m.group(2).strip().startswith(("fixed", "done")):
            found.add(m.group(1))
    named, done = set(), set()
    for line in (HERE / "web-design-suite-completion-plan.md").read_text(encoding="utf-8").splitlines():
        m = re.search(r"\*\*N(\d+)\b", line)
        if m:
            named.add(f"N{m.group(1)}")
            if "Done for" in line:
                done.add(f"N{m.group(1)}")
    return found | (named - done)


def scheduled() -> collections.Counter:
    counts: collections.Counter = collections.Counter()
    for line in (HERE / "web-design-suite-execution-plan.md").read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.split("|")]
        if len(cells) > 4 and re.fullmatch(r"P\d+", cells[1]):
            counts.update(ID.findall(cells[3]))
    return counts


def main() -> int:
    want, have = open_items(), scheduled()
    missing = sorted(want - set(have))
    extra = sorted(set(have) - want)
    twice = sorted(i for i, n in have.items() if n > 1)
    print(f"{len(want)} open items, {len(have)} scheduled")
    for label, ids in (("not scheduled", missing), ("scheduled but not open", extra), ("scheduled twice", twice)):
        if ids:
            print(f"{label}: {', '.join(ids)}")
    return 1 if missing or extra or twice else 0


if __name__ == "__main__":
    sys.exit(main())
