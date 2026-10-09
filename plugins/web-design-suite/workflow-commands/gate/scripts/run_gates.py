#!/usr/bin/env python3
"""run_gates.py — /web-design-suite:gate (P26, XC-C3): the three static gates
in one run, from the project's root, with one verdict.

  1. design         web-design-studio's audit_design.py --strict
  2. accessibility  a11y-audit-runner's a11y_static.py --strict
  3. performance    perf-budget-gate's perf_audit.py on the build output, when
                    there is one (--dist, else dist/ or build/ if it exists)

Each script reads the project's .design-suite.json itself, so its token files,
component globs, budgets and baselines count, as they do in CI (XC-C8). The
browser halves of the a11y and perf gates need a served build; /install-gate's
CI template runs them.

Usage, from the project's root:
    python run_gates.py [paths ...] [--src DIR] [--dist DIR]

Exit codes: 0 every gate that ran passed, 1 a gate failed, 2 a gate could not
run or bad invocation. Standard library only; Python 3.9 or newer.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

sys.dont_write_bytecode = True
PLUGIN = Path(__file__).resolve().parents[3]
SKILLS = PLUGIN / "skills"
AUDIT = SKILLS / "web-design-studio" / "scripts" / "audit_design.py"
A11Y = SKILLS / "a11y-audit-runner" / "scripts" / "a11y_static.py"
PERF = SKILLS / "perf-budget-gate" / "scripts" / "perf_audit.py"
BUILDS = ("dist", "build")


def gates(paths: List[str], src: Optional[str], dist: Optional[str]) -> List[Tuple[str, Optional[List[str]], str]]:
    """Each gate's name, its command (None when it cannot run here) and why."""
    build = dist or next((b for b in BUILDS if Path(b).is_dir()), None)
    perf: Optional[List[str]] = None
    note = ""
    if build is None:
        note = "no build output: build the site, then pass --dist DIR"
    elif not Path(build).exists():
        note = f"{build} does not exist"
    else:
        perf = [str(PERF), build, *(["--src", src] if src else [])]
    return [("design", [str(AUDIT), *paths, "--strict"], ""),
            ("accessibility", [str(A11Y), *(paths or ([src] if src else [])), "--strict"], ""),
            ("performance", perf, note)]


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        prog="run_gates.py",
        description="Run the design, accessibility and performance gates on this project.")
    ap.add_argument("paths", nargs="*", help="what the design and accessibility gates read (default: the "
                                              "project, or --src)")
    ap.add_argument("--src", metavar="DIR", help="the source folder, for the accessibility gate and for "
                                                 "perf_audit's --src")
    ap.add_argument("--dist", metavar="DIR", help="the build output the performance gate weighs "
                                                  "(default: dist/ or build/, if one exists)")
    args = ap.parse_args(argv)

    results = []
    for name, command, note in gates(args.paths, args.src, args.dist):
        print(f"\n== {name} gate " + "=" * max(0, 60 - len(name)), flush=True)
        if command is None:
            print(f"skipped: {note}", flush=True)
            results.append((name, None, note))
            continue
        code = subprocess.call([sys.executable, "-B", *command])
        results.append((name, code, ""))

    print("\n== verdict " + "=" * 52)
    worst = 0
    for name, code, note in results:
        if code is None:
            verdict = f"skipped ({note})"
        elif code == 0:
            verdict = "passed"
        elif code == 1:
            verdict, worst = "FAILED", max(worst, 1)
        else:
            verdict, worst = f"could not run (exit {code})", 2
        print(f"  {name:<14} {verdict}")
    return worst


if __name__ == "__main__":
    sys.exit(main())
