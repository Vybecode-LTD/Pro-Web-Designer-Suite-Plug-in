"""The release gate: CI passed on the commit a tag names. Standard library only.

usage: python tooling/release/ci_gate.py SHA [--repo OWNER/NAME]

release.yml runs it before it builds anything (OPS-2, P67): a pushed v* tag
released whatever commit it named, red or cancelled, and the distribution
repository and the directory took it from there. It reads the commit's check
runs with `gh api` (GH_TOKEN, `checks: read`), takes the latest run of each
name (a rerun leaves the failed one beside it), and requires each of CI's
seven jobs to be there and to have concluded `success`. Other checks on the
commit (this workflow's own jobs, a review bot's) are not CI's and do not
count.

Exit codes: 0 when CI passed, 1 when it did not (each missing, failed or
unfinished job named), 2 when the check runs cannot be read.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

# ci.yml's jobs: the suite on each OS and Python, then the validate job.
# tests/test_ci_workflow.py holds these to ci.yml's matrix and names.
REQUIRED = tuple(f"{os_} · Python {py}" for os_ in ("ubuntu-latest", "windows-latest", "macos-latest")
                 for py in ("3.9", "3.14")) + ("claude plugin validate --strict",)


def problems(check_runs: list[dict], required: tuple[str, ...] = REQUIRED) -> list[str]:
    """What stops a release, given a commit's check runs: one line for each
    required job that is missing, unfinished or not a success, judged by its
    latest run (the highest id). Only GitHub Actions' runs count."""
    latest: dict[str, dict] = {}
    for run in check_runs:
        if run.get("app") != "github-actions":
            continue
        name = run.get("name")
        if name not in latest or run["id"] > latest[name]["id"]:
            latest[name] = run
    found = []
    for name in required:
        run = latest.get(name)
        if run is None:
            found.append(f"{name}: no run on this commit")
        elif run.get("status") != "completed":
            found.append(f"{name}: still {run.get('status')}; rerun this job once CI has finished")
        elif run.get("conclusion") != "success":
            found.append(f"{name}: {run.get('conclusion')}")
    return found


def check_runs(repo: str, sha: str) -> list[dict]:
    """Every check run on the commit, through `gh api`, one JSON object a line."""
    proc = subprocess.run(
        ["gh", "api", "--paginate", f"repos/{repo}/commits/{sha}/check-runs?per_page=100",
         "--jq", ".check_runs[] | {id, name, status, conclusion, app: .app.slug}"],
        capture_output=True, check=True)
    return [json.loads(line) for line in proc.stdout.decode("utf-8").splitlines() if line.strip()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("sha")
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY"))
    args = parser.parse_args(argv)
    if not args.repo:
        parser.error("--repo is needed outside GitHub Actions")
    try:
        runs = check_runs(args.repo, args.sha)
    except (OSError, subprocess.CalledProcessError) as exc:
        detail = getattr(exc, "stderr", b"") or b""
        print(f"ci_gate: cannot read the check runs on {args.sha}: "
              f"{detail.decode(errors='replace').strip() or exc}", file=sys.stderr)
        return 2
    found = problems(runs)
    for line in found:
        print(f"::error::CI on {args.sha[:12]}: {line}")
    if found:
        print(f"ci_gate: CI has not passed on {args.sha}, so nothing is released.", file=sys.stderr)
        return 1
    print(f"ci_gate: CI passed on {args.sha}: {len(REQUIRED)} jobs, each a success on its latest run.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
