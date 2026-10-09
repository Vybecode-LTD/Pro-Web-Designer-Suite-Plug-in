#!/usr/bin/env python3
"""deck.py — /web-design-suite:deck (P26, PS-C11): from the audits and a
critique to the client deck, stopping on blockers.

  1. audit     web-design-studio's audit_design.py --json, on the paths given
               or the project; perf-budget-gate's perf_audit.py --json on the
               build, when there is one (--dist, else dist/ or build/)
  2. critique  design-critique-gate's critique_report.py on the critique's
               findings (--findings), merged with the audit, --fail-on
               blocking: a blocking finding stops the deck here
  3. defence   the same findings as the out-loud defence sheet
  4. deck      client-presentation-builder's build_presentation.py from the
               decision log, with the audit, the performance report and the
               defence as its evidence

The critique itself is a person's or the design critic's: this runs on its
findings.json. Everything goes in --out (default design-reports/deck).

Usage, from the project's root:
    python deck.py DECISION_LOG.md --findings FILE [paths ...]
                   [--audience client|team] [--dist DIR] [--out DIR]

Exit codes: 0 the deck is built, 1 a blocking finding stopped it, 2 a step
could not run or bad invocation. Standard library only; Python 3.9 or newer.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Sequence

sys.dont_write_bytecode = True
PLUGIN = Path(__file__).resolve().parents[3]
SKILLS = PLUGIN / "skills"
AUDIT = SKILLS / "web-design-studio" / "scripts" / "audit_design.py"
PERF = SKILLS / "perf-budget-gate" / "scripts" / "perf_audit.py"
CRITIQUE = SKILLS / "design-critique-gate" / "scripts" / "critique_report.py"
PRESENT = SKILLS / "client-presentation-builder" / "scripts" / "build_presentation.py"
BUILDS = ("dist", "build")


def step(title: str) -> None:
    print(f"\n== {title} " + "=" * max(0, 60 - len(title)), flush=True)


def call(command: List[str]) -> int:
    return subprocess.call([sys.executable, "-B", *command])


def capture(command: List[str], to: Path) -> int:
    """A script's --json, kept in a file for the next step."""
    proc = subprocess.run([sys.executable, "-B", *command], capture_output=True)
    to.write_bytes(proc.stdout)
    sys.stderr.write(proc.stderr.decode("utf-8", "replace"))
    return proc.returncode


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="deck.py",
                                 description="Audit, critique, defence and deck, stopping on blockers.")
    ap.add_argument("log", metavar="DECISION_LOG.md", help="the decisions the deck argues")
    ap.add_argument("paths", nargs="*", help="what the design audit reads (default: the project)")
    ap.add_argument("--findings", metavar="FILE", required=True,
                    help="the critique's findings.json (design-critique-gate)")
    ap.add_argument("--audience", choices=("client", "team"), default="client")
    ap.add_argument("--dist", metavar="DIR", help="the build the performance audit weighs "
                                                  "(default: dist/ or build/, if one exists)")
    ap.add_argument("--out", default="design-reports/deck", metavar="DIR",
                    help="where the reports and the deck go (default: design-reports/deck)")
    args = ap.parse_intermixed_args(argv)              # paths after --findings, on Python 3.9 too

    for path, what in ((args.log, "the decision log"), (args.findings, "the critique's findings")):
        if not Path(path).is_file():
            print(f"error: {what}, {path}, does not exist", file=sys.stderr)
            return 2
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for stale in ("audit.json", "perf.json", "defence.md", "deck.html", "notes.md"):   # no old run's evidence
        if (out / stale).is_file():
            (out / stale).unlink()

    step("audit")
    audit = out / "audit.json"
    if capture([str(AUDIT), *args.paths, "--json"], audit) not in (0, 1):
        print("stopped: the design audit could not run")
        return 2
    print(f"the design audit -> {audit}")
    build = args.dist or next((b for b in BUILDS if Path(b).is_dir()), None)
    perf = None
    if build:
        perf = out / "perf.json"
        if capture([str(PERF), build, "--json"], perf) not in (0, 1):
            print("stopped: the performance audit could not run")
            return 2
        print(f"the performance audit of {build} -> {perf}")
    else:
        print("no build output: the deck has no performance evidence (pass --dist DIR)")

    step("critique")
    code = call([str(CRITIQUE), args.findings, "--audit", str(audit), "--fail-on", "blocking"])
    if code == 1:
        print("stopped: a blocking finding. Fix it, or record it as a decision, before it is presented.")
        return 1
    if code != 0:
        return 2

    step("defence")
    defence = out / "defence.md"
    if call([str(CRITIQUE), args.findings, "--audit", str(audit), "--format", "defence",   # the same evidence
             "-o", str(defence)]) != 0:                                                       # (Codex on #88)
        return 2
    print(f"the defence sheet -> {defence}")

    step("deck")
    deck, notes = out / "deck.html", out / "notes.md"
    code = call([str(PRESENT), args.log, "--audience", args.audience, "--audit", str(audit),
                 *(["--perf", str(perf)] if perf else []), "--defence", str(defence),
                 "--out", str(deck), "--notes", str(notes)])
    if code != 0:
        print("stopped: the deck could not be built")
        return 2
    print(f"\nthe deck -> {deck}\nthe speaker notes -> {notes}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
