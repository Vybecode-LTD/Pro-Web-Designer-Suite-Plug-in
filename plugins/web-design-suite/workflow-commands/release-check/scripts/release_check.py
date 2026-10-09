#!/usr/bin/env python3
"""release_check.py — /web-design-suite:release-check (P26, LC-C9): is the
design system ready to release, and what does the release say?

  1. extract  design-system-docs' extract_system.py: the candidate snapshot,
              from the paths given, else src/ (tokens, component CSS, props)
  2. diff     design-system-versioning's diff_system.py, the published
              snapshot (--published, else the config's baselines.system)
              against the candidate: every change, its severity, the bump
  3. gate     the diff's gate, binding with a deprecation ledger
              (--deprecations, else deprecations.json when there is one):
              a name that vanished unannounced stops the release here
  4. changelog  the diff as a changelog entry, CHANGELOG.part.md
  5. guide      the migration guide, UPGRADE.md, when a change is breaking

Everything goes in --out (default design-reports/release). Nothing in the
project is edited.

Usage, from the project's root:
    python release_check.py [paths ...] [--published FILE] [--from-version X.Y.Z]
                            [--deprecations FILE] [--project NAME] [--out DIR]

Exit codes: 0 ready (the gate passed or is advisory), 1 the gate failed,
2 a step could not run or bad invocation. Standard library only; Python 3.9
or newer.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Sequence

sys.dont_write_bytecode = True
PLUGIN = Path(__file__).resolve().parents[3]
EXTRACT = PLUGIN / "skills" / "design-system-docs" / "scripts" / "extract_system.py"
DIFF = PLUGIN / "skills" / "design-system-versioning" / "scripts" / "diff_system.py"
sys.path.insert(0, str(PLUGIN / "shared"))
from project_config import ConfigError, config_path, project_config  # noqa: E402


def step(title: str) -> None:
    print(f"\n== {title} " + "=" * max(0, 60 - len(title)), flush=True)


def call(command: List[str]) -> int:
    return subprocess.call([sys.executable, "-B", *command])


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="release_check.py",
                                 description="Extract, diff and gate the design system, then write the "
                                             "changelog and the migration guide.")
    ap.add_argument("paths", nargs="*", help="what extract_system reads (default: src/, if it exists, "
                                              "else the config's token files)")
    ap.add_argument("--published", metavar="FILE", help="the published snapshot (default: the "
                                                        ".design-suite.json's baselines.system)")
    ap.add_argument("--from-version", metavar="X.Y.Z", help="the version the published snapshot shipped as")
    ap.add_argument("--deprecations", metavar="FILE", help="the deprecation ledger, which makes the gate "
                                                           "binding (default: deprecations.json, if it exists)")
    ap.add_argument("--project", metavar="NAME", help="the name in the changelog and the guide")
    ap.add_argument("--out", default="design-reports/release", metavar="DIR",
                    help="where the reports go (default: design-reports/release)")
    args = ap.parse_args(argv)

    try:
        config = project_config()
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    published = args.published or config_path(config, "baselines", "system")
    if not published:
        print("error: no published snapshot to compare with. Pass --published FILE, or name it in "
              ".design-suite.json as baselines.system. A first release has none: snapshot the system "
              "when you publish it (extract_system.py src --out published/system.json) and commit it.",
              file=sys.stderr)
        return 2
    if not Path(published).is_file():
        print(f"error: the published snapshot {published} does not exist", file=sys.stderr)
        return 2
    ledger = args.deprecations or ("deprecations.json" if Path("deprecations.json").is_file() else None)
    paths = args.paths or (["src"] if Path("src").is_dir() else [])
    out = Path(args.out)
    candidate = out / "system.json"
    common = [*(["--from-version", args.from_version] if args.from_version else []),
              *(["--project", args.project] if args.project else [])]
    gate = ["--deprecations", ledger] if ledger else []

    written = [out / name for name in ("system.json", "diff.json", "CHANGELOG.part.md", "UPGRADE.md")]
    if Path(published).resolve() in [w.resolve() for w in written]:
        print(f"error: --out {out} would overwrite the published snapshot, {published}. Choose another --out.",
              file=sys.stderr)                         # CodeRabbit on #87
        return 2
    for stale in written[1:]:                          # a stopped run leaves no old report behind
        if stale.is_file():
            stale.unlink()

    step("extract")
    if call([str(EXTRACT), *paths, "--out", str(candidate)]) != 0:
        print("stopped: extract_system could not read the system")
        return 2

    step("diff")
    code = call([str(DIFF), published, str(candidate), *common, *gate])
    if code not in (0, 1):
        print("stopped: diff_system could not compare the snapshots")
        return 2
    report = out / "diff.json"
    if (call([str(DIFF), published, str(candidate), *common, *gate, "--format", "json", "-o", str(report)])
            not in (0, 1) or not report.is_file()):
        print("stopped: diff_system could not write its report")
        return 2
    diff = json.loads(report.read_bytes())

    step("gate")
    failures = diff["gate"]["failures"]
    if not ledger:
        print("advisory: no deprecation ledger, so a vanished name is reported, not refused"
              + (f" ({', '.join(failures)})" if failures else ""))
    elif code == 1:
        print(f"FAILED: {', '.join(failures)} vanished with no deprecation record in {ledger}.\n"
              "Deprecate each before it is removed (design-system-versioning's deprecate.py add), "
              "and ship the shim. Stopped: no changelog until the gate passes.")
        return 1
    else:
        print(f"passed: every vanished name has a record in {ledger}")

    step("changelog")
    changelog = out / "CHANGELOG.part.md"
    if call([str(DIFF), published, str(candidate), *common, *gate, "--format", "changelog",
             "-o", str(changelog)]) != 0:
        return 2

    step("guide")
    guide = None
    if diff["counts"]["major"]:
        guide = out / "UPGRADE.md"
        if call([str(DIFF), published, str(candidate), *common, *gate, "--format", "migration-guide",
                 "-o", str(guide)]) != 0:
            return 2
    else:
        print("no breaking change: no migration guide")

    step("verdict")
    version = diff.get("version") or {}
    print(f"  bump       {diff['bump']['level']} ({diff['bump']['reason']})")
    if version.get("to"):
        print(f"  version    {version.get('from')} -> {version['to']}")
    print(f"  changes    {diff['counts']['major']} major, {diff['counts']['minor']} minor, "
          f"{diff['counts']['patch']} patch")
    print(f"  gate       {'passed' if ledger else 'advisory'}")
    print(f"  changelog  {changelog}")
    print(f"  guide      {guide or 'none'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
