"""The checks every PR runs locally, in one command, with one summary.
Standard library only; Python 3.9 or newer.

usage: python tools/check.py [--all] [--base REF]

  1. tools/check_pointers.py
  2. tools/sync_snippets.py --check
  3. tools/sync_rules.py --check, once it exists
  4. dev plans/check_execution_plan.py, inside the plugin's repository
  5. the audit on the plugin's own skills: audit_design.py skills --strict
  6. test_skill_budget
  7. the affected tests

The affected tests come from the files changed since `git merge-base
origin/main HEAD` (or REF with --base): committed, staged, unstaged and
untracked. A changed test module runs itself. Any other file runs the test
modules whose source names its skill's folder, its stem if it is a script,
or its file name if not. A change to a shared file runs the whole suite, as
--all does: tests/wds_support.py, design-rules.json, a config in
assets/configs/, anything in tools/, or the pinned toolchain in tooling/.
CI runs the whole suite on every platform anyway; this is the quick local pass.

Exit codes: 0 when every check passes, 1 when one fails.
"""
from __future__ import annotations

import argparse
import os
import pathlib
import subprocess
import sys
import time

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
IN_REPO = "plugins/web-design-suite/"
SHARED = ("tests/wds_support.py", "skills/web-design-studio/assets/rules/design-rules.json")
SCRIPT_SUFFIXES = (".py", ".mjs", ".js", ".sh")


def affected(changed: list[str], sources: dict[str, str]) -> list[str] | None:
    """The test modules to run for these changed paths, given relative to the
    repository, or None for the whole suite. `sources` maps each test module
    to its source text."""
    modules: set[str] = set()
    for path in changed:
        rel = path[len(IN_REPO):] if path.startswith(IN_REPO) else None
        if rel is None:
            if path.startswith(("tooling/main/", "tooling/tailwind-v3/")):
                return None
            keys = [path.rsplit("/", 1)[-1]]                    # dev plans, .github, tooling/release
        else:
            parts = rel.split("/")
            if rel in SHARED or parts[0] == "tools" or "/assets/configs/" in f"/{rel}":
                return None
            if parts[0] == "tests" and len(parts) == 2 and parts[1].startswith("test_") and rel.endswith(".py"):
                modules.add(parts[1][:-3])
                continue
            name = parts[-1]
            keys = [name.rsplit(".", 1)[0] if name.endswith(SCRIPT_SUFFIXES) else name]
            if parts[0] == "skills" and len(parts) > 2:
                keys.append(parts[1])
        modules.update(m for m, text in sources.items() if any(k in text for k in keys))
    return sorted(modules)


def changed_files(base: str | None) -> list[str] | None:
    """Paths changed since the merge base, relative to the repository; None
    when git cannot say."""
    def git(*args: str, cwd: pathlib.Path | None = None) -> str | None:
        proc = subprocess.run(["git", *args], cwd=cwd or PLUGIN_ROOT, capture_output=True)
        return proc.stdout.decode("utf-8", "replace") if proc.returncode == 0 else None

    top = git("rev-parse", "--show-toplevel")
    fork = git("merge-base", base or "origin/main", "HEAD")
    if not top or not fork:
        return None
    # From the top, so every path is relative to it, untracked ones included;
    # NUL-separated, so a space (dev plans/) or a non-ASCII name stays whole.
    top_dir = pathlib.Path(top.strip())
    diff = git("diff", "--name-only", "--no-renames", "-z", fork.strip(), cwd=top_dir)
    untracked = git("ls-files", "--others", "--exclude-standard", "-z", cwd=top_dir)
    if diff is None or untracked is None:
        return None
    return sorted({p for p in (diff + "\0" + untracked).split("\0") if p})


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--all", action="store_true", help="run the whole suite as the last check")
    parser.add_argument("--base", help="compare with this ref instead of origin/main")
    args = parser.parse_args(argv)
    # A report must print on any console: a cp1252 one (a redirect on Windows)
    # has no byte for many characters a check prints, and the checks write
    # UTF-8, which is how their output is read back.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONIOENCODING": "utf-8"}
    py = [sys.executable, "-B"]
    tests = PLUGIN_ROOT / "tests"
    repo_plan = PLUGIN_ROOT.parents[1] / "dev plans" / "check_execution_plan.py"
    sources = {p.stem: p.read_text(encoding="utf-8", errors="replace") for p in sorted(tests.glob("test_*.py"))}

    changed = None if args.all else changed_files(args.base)
    modules = None if changed is None else affected(changed, sources)
    if modules is None:
        why = "--all" if args.all else ("a shared file changed" if changed is not None else "git cannot say what changed")
        suite = ("the whole suite", why, [*py, "-m", "unittest", "discover", "-s", "tests"], PLUGIN_ROOT)
    else:
        modules = [m for m in modules if m != "test_skill_budget"]
        suite = ("the affected tests", ", ".join(modules) or "none",
                 [*py, "-m", "unittest", *modules] if modules else None, tests)

    checks = [
        ("check_pointers", "", [*py, "tools/check_pointers.py"], PLUGIN_ROOT),
        ("sync_snippets --check", "", [*py, "tools/sync_snippets.py", "--check"], PLUGIN_ROOT),
        ("sync_rules --check", "", [*py, "tools/sync_rules.py", "--check"]
         if (PLUGIN_ROOT / "tools" / "sync_rules.py").exists() else None, PLUGIN_ROOT),
        ("check_execution_plan", "", [*py, str(repo_plan)] if repo_plan.exists() else None, repo_plan.parent),
        ("the audit on skills --strict", "",
         [*py, "skills/web-design-studio/scripts/audit_design.py", "skills", "--strict"], PLUGIN_ROOT),
        ("test_skill_budget", "", [*py, "-m", "unittest", "test_skill_budget"], tests),
        suite,
    ]
    results = []
    for name, note, command, cwd in checks:
        if command is None:
            results.append((name, "skip", note or "not here", 0.0))
            continue
        start = time.monotonic()
        proc = subprocess.run(command, cwd=cwd, env=env, capture_output=True)
        took = time.monotonic() - start
        ok = proc.returncode == 0
        results.append((name, "pass" if ok else "FAIL", note, took))
        if not ok:
            text = (proc.stdout + proc.stderr).decode("utf-8", "replace").rstrip().splitlines()
            print(f"--- {name} ---", *text[-25:], sep="\n")

    print()
    for name, verdict, note, took in results:
        print(f"{verdict:4}  {name}{f' ({note})' if note else ''}{f'  {took:.0f}s' if took else ''}")
    return 1 if any(r[1] == "FAIL" for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
