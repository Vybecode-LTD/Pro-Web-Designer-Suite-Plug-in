#!/usr/bin/env python3
"""install_gate.py — /web-design-suite:install-gate (P26: XC-C3, GT-C12,
LC-B4): put the suite's gates into a project, so CI runs them on every push.

  1. Vendors the gate scripts into the project's scripts/ (--dest), the folder
     every CI recipe, the pre-commit hook and each SKILL.md's
     `python -m scripts.<name>` already assume: audit_design, check_roles and
     generate_color_ramp (web-design-studio), a11y_static and a11y_runtime
     (a11y-audit-runner), perf_audit and measure_vitals (perf-budget-gate), and
     the readers and browser helpers they import. A clean checkout then has
     every script it runs, with no plugin and no PYTHONPATH (LC-B4).
     scripts/design-gates.json lists each file with its SHA-256 and the
     plugin's version.
  2. Writes .github/workflows/design-gates.yml from the template beside this
     folder (GT-C12): the three gates on Linux in the Playwright image built
     for the project's own playwright, the static gates on Windows, and a job
     run by hand that records the baselines and uploads them.

It reads the project's .design-suite.json for the baselines' paths. It never
overwrites a file it did not write, unless --force: a vendored file is its own
when design-gates.json lists it with the SHA-256 it still has.

Usage, from the project's root:
    python install_gate.py [--dest scripts] [--src src] [--dist dist]
                           [--build "npm run build"] [--force] [--dry-run]

Exit codes: 0 installed, 1 refused (a file in the way, or no exact playwright
version to pin), 2 bad invocation. Standard library only; Python 3.9 or newer.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence

sys.dont_write_bytecode = True
PLUGIN = Path(__file__).resolve().parents[3]
SKILLS = PLUGIN / "skills"
TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "design-gates.yml"
WORKFLOW = Path(".github") / "workflows" / "design-gates.yml"
STAMP = "design-gates.json"
# The playwright the suite's own tests run (tooling/main/package.json).
TESTED_PLAYWRIGHT = "1.63.0"

# What each gate runs, and what those scripts import from their own folder.
VENDORED = {
    "web-design-studio": ["audit_design.py", "check_roles.py", "generate_color_ramp.py", "project_config.py"],
    "a11y-audit-runner": ["a11y_static.py", "a11y_runtime.mjs", "browser_common.mjs", "project_config.mjs"],
    "perf-budget-gate": ["perf_audit.py", "measure_vitals.mjs"],
}
BASELINES = {"audit": ".design-baseline.json", "a11y": ".a11y-baseline.json", "perf": ".perf-baseline.json"}

sys.path.insert(0, str(PLUGIN / "shared"))
from project_config import ConfigError, project_config  # noqa: E402


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def plugin_version() -> str:
    return json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_bytes())["version"]


def pinned_playwright(root: Path) -> Optional[str]:
    """The exact playwright version package.json pins, or None. A range is not
    a pin: the image's browsers fit one version."""
    try:
        package = json.loads((root / "package.json").read_bytes())
    except (OSError, ValueError):
        return None
    for group in ("devDependencies", "dependencies"):
        for name in ("playwright", "@playwright/test"):
            spec = str((package.get(group) or {}).get(name, ""))
            if re.fullmatch(r"\d+\.\d+\.\d+", spec):
                return spec
            if spec:
                return f"range:{spec}"
    return None


def posix(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="install_gate.py",
                                 description="Vendor the gates into this project and write their CI workflow.")
    ap.add_argument("--dest", default="scripts", help="where the gate scripts go (default: scripts)")
    ap.add_argument("--src", default="src", help="the source folder the gates read (default: src)")
    ap.add_argument("--dist", default="dist", help="the build output (default: dist)")
    ap.add_argument("--build", default="npm run build", help='the build command (default: "npm run build")')
    ap.add_argument("--force", action="store_true", help="overwrite files this command did not write")
    ap.add_argument("--dry-run", action="store_true", help="say what would be written, and write nothing")
    args = ap.parse_args(argv)
    for name in ("dest", "src", "dist", "build"):
        value = getattr(args, name)
        if not value.strip() or "@" in value or "\n" in value:
            ap.error(f"--{name} must be a plain path or command")

    root = Path.cwd()
    try:
        config = project_config(root)
    except ConfigError as exc:
        print(f"install_gate: {exc}", file=sys.stderr)
        return 2
    pin = pinned_playwright(root)
    if pin and pin.startswith("range:"):
        print(f"install_gate: package.json asks for playwright {pin[6:]}, a range. The CI image's browsers fit one "
              f"version, so pin it: npm i -D -E playwright@{TESTED_PLAYWRIGHT}", file=sys.stderr)
        return 1
    playwright = pin or TESTED_PLAYWRIGHT

    # 1. the scripts
    dest = root / args.dest
    files: Dict[str, bytes] = {}
    for skill, names in VENDORED.items():
        for name in names:
            files[name] = (SKILLS / skill / "scripts" / name).read_bytes()
    stamp_path = dest / STAMP
    try:
        last = json.loads(stamp_path.read_bytes())
    except (OSError, ValueError):
        last = {}
    last = last if isinstance(last, dict) else {}

    # 2. the workflow
    baselines = {key: posix(config.baselines[key], root) if config and key in config.baselines else default
                 for key, default in BASELINES.items()}
    text = TEMPLATE.read_text(encoding="utf-8")
    for key, value in {"VERSION": plugin_version(), "PLAYWRIGHT": playwright, "DEST": args.dest.strip("/"),
                       "SRC": args.src, "DIST": args.dist, "BUILD": args.build,
                       "AUDIT_BASELINE": baselines["audit"], "A11Y_BASELINE": baselines["a11y"],
                       "PERF_BASELINE": baselines["perf"]}.items():
        text = text.replace(f"@{key}@", value)
    workflow = text.encode("utf-8")

    writes: Dict[Path, bytes] = {dest / name: data for name, data in files.items()}
    writes[root / WORKFLOW] = workflow
    in_the_way: List[str] = []
    for path, data in writes.items():
        if not path.exists() or path.read_bytes() == data:
            continue
        mine = (last.get("files") or {}).get(path.name) if path.parent == dest else last.get("workflow")
        if mine != sha(path.read_bytes()) and not args.force:
            in_the_way.append(posix(path, root))
    if in_the_way:
        print("install_gate: nothing was written. These files are in the way: this command did not write them, "
              "or they changed since it did (pass --force to replace them):\n  " + "\n  ".join(in_the_way),
              file=sys.stderr)
        return 1

    stamp = {"plugin": "web-design-suite", "version": plugin_version(),
             "files": {name: sha(data) for name, data in sorted(files.items())}, "workflow": sha(workflow)}
    writes[stamp_path] = (json.dumps(stamp, indent=2) + "\n").encode("utf-8")
    verb = "would write" if args.dry_run else "wrote"
    for path, data in writes.items():
        if not args.dry_run:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        print(f"{verb} {posix(path, root)}")
    print(f"\nThe CI image is mcr.microsoft.com/playwright:v{playwright}-noble.")
    if not pin:
        print(f"package.json pins no playwright, so the image is the one the suite tests with. The browser gates "
              f"need it in the lockfile, with axe-core, serve and wait-on:\n"
              f"  npm i -D -E playwright@{playwright} axe-core serve wait-on")
    print("Commit both, then run the workflow by hand with update-baselines ticked to record the baselines in CI.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
