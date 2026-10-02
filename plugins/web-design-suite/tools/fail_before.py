"""Run tests against an earlier revision of the plugin, then against this tree,
and print one table: what each test did before, what it does now, and the
verdict. Standard library only; Python 3.9 or newer.

usage: python tools/fail_before.py <test ids…> [--rev REV] [--python EXE]

  test ids      unittest names inside the tests folder: test_policies,
                test_policies.PoliciesAreProposed or one test of it. A
                leading `tests.` is dropped.
  --rev REV     the revision to compare with: a tag, a branch or a commit
                (default: the latest v* tag, as `git describe --tags
                --abbrev=0 --match "v*"` gives it)
  --python EXE  the interpreter for both runs (default: this one)

The revision's plugin comes from `git archive`, read through Python's tarfile
into a temporary folder outside the plugin. The tests run twice, from
plugins/web-design-suite/tests: first with WDS_PLUGIN_ROOT pointing at that
folder and WDS_PLUGIN_REV naming its commit, then on this tree. Both runs set
PYTHONDONTWRITEBYTECODE=1, so nothing is written into the plugin.

Verdicts: fixed (fails before, passes now), control (passes both), still
failing, regression (passes before, fails now), and skipped (in either run).
A failing test shows its failures and errors, subtests included.

It works on the repository it runs in. The variables that tie git to one
repository (GIT_DIR and the rest `git rev-parse --local-env-vars` names) are
dropped. Exit codes: 0 when nothing fails now, 1 when something does, 2 for a
bad invocation.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import pathlib
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile

PLUGIN = "plugins/web-design-suite"

# Runs in the tests folder, under the interpreter being tested, and writes one
# row per test id: whether it passed, how many of its parts failed, and why it
# was skipped. Reading results this way, rather than unittest's text, holds
# from Python 3.9 to 3.14.
RUNNER = """
import json, re, sys, unittest

def each(suite):
    for test in suite:
        if isinstance(test, unittest.TestSuite):
            yield from each(test)
        else:
            yield test

class Result(unittest.TestResult):
    def __init__(self):
        super().__init__()
        self.rows = {}
    def row(self, test):
        return self.rows.setdefault(test.id(), {"ok": False, "failed": 0, "skipped": None})
    def startTest(self, test):
        super().startTest(test)
        self.row(test)
    def addSuccess(self, test):
        self.row(test)["ok"] = True
    def addFailure(self, test, err):
        self.row(test)["failed"] += 1
    def addError(self, test, err):
        if isinstance(test, unittest.TestCase):
            self.row(test)["failed"] += 1
            return
        # A class or module fixture failed ("setUpClass (module.Class)"):
        # it counts against every test under it, none of which ran.
        scope = re.search(r"\\((.*)\\)", str(test))
        under = [k for k in self.rows if scope and k.startswith(scope.group(1) + ".")]
        for key in under or [str(test)]:
            self.rows.setdefault(key, {"ok": False, "failed": 0, "skipped": None})["failed"] += 1
    def addSkip(self, test, reason):
        self.row(test)["skipped"] = reason
    def addExpectedFailure(self, test, err):
        self.row(test)["ok"] = True
    def addUnexpectedSuccess(self, test):
        self.row(test)["failed"] += 1
    def addSubTest(self, test, subtest, err):
        if err is not None:
            self.row(test)["failed"] += 1

result = Result()
suite = unittest.defaultTestLoader.loadTestsFromNames(sys.argv[2:])
for test in each(suite):
    result.row(test)
suite.run(result)
with open(sys.argv[1], "w", encoding="utf-8") as f:
    json.dump(result.rows, f)
"""


def git(*args: str, env: dict[str, str], cwd: str) -> bytes:
    return subprocess.run(["git", *args], check=True, capture_output=True, env=env, cwd=cwd).stdout


def own_repository() -> tuple[dict[str, str], str]:
    local = set(subprocess.run(["git", "rev-parse", "--local-env-vars"], check=True,
                               capture_output=True).stdout.decode().split())
    env = {k: v for k, v in os.environ.items() if k not in local}
    return env, git("rev-parse", "--show-toplevel", env=env, cwd=os.getcwd()).decode().strip()


def unpack(archive: bytes, dest: pathlib.Path) -> pathlib.Path:
    """The plugin from a `git archive` tar, as dest/web-design-suite."""
    root = dest / "web-design-suite"
    root.mkdir(parents=True)
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        for member in tar.getmembers():
            rel = member.name[len(PLUGIN):].strip("/")
            if not member.name.startswith(PLUGIN) or not rel:
                continue
            target = root.joinpath(*rel.split("/"))
            if root.resolve() not in target.resolve().parents:
                raise ValueError(f"{member.name} would land outside {root}")
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
            elif member.isfile():
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(tar.extractfile(member).read())
                if member.mode & 0o111 and os.name != "nt":
                    target.chmod(target.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return root


def run(python: str, tests: pathlib.Path, ids: list[str], env: dict[str, str],
        out: pathlib.Path) -> dict[str, dict]:
    proc = subprocess.run([python, "-B", "-c", RUNNER, str(out), *ids], cwd=tests, env=env,
                          capture_output=True)
    if not out.exists():
        tail = (proc.stdout + proc.stderr).decode("utf-8", "replace").strip().splitlines()[-15:]
        raise RuntimeError("the test run wrote no results:\n" + "\n".join(tail))
    return json.loads(out.read_text(encoding="utf-8"))


def status(row: dict | None) -> str:
    if row is None:
        return "absent"
    if row["failed"]:
        return f"FAIL ({row['failed']})"
    if row["skipped"] is not None:
        return "skipped"
    return "ok" if row["ok"] else "no result"


def verdict(before: str, now: str) -> str:
    if "skipped" in (before, now):
        return "skipped"
    passed_before, passes_now = before == "ok", now == "ok"
    if passes_now:
        return "control" if passed_before else "fixed"
    return "regression" if passed_before else "still failing"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("ids", nargs="+", metavar="test id")
    parser.add_argument("--rev", help="the revision to compare with (default: the latest v* tag)")
    parser.add_argument("--python", default=sys.executable, help="the interpreter for both runs")
    args = parser.parse_args(argv)
    ids = [i[len("tests."):] if i.startswith("tests.") else i for i in args.ids]

    try:
        env, top = own_repository()
        rev = args.rev or git("describe", "--tags", "--abbrev=0", "--match", "v*",
                              env=env, cwd=top).decode().strip()
        commit = git("rev-parse", "--verify", rev + "^{commit}", env=env, cwd=top).decode().strip()
        archive = git("archive", "--format=tar", commit, PLUGIN, env=env, cwd=top)
    except (OSError, subprocess.CalledProcessError) as exc:
        detail = (getattr(exc, "stderr", b"") or b"").decode(errors="replace").strip()
        parser.error(f"cannot read {repr(args.rev) if args.rev else 'the latest v* tag'} from git: {detail or exc}")

    tests = pathlib.Path(top) / PLUGIN / "tests"
    base = {k: v for k, v in env.items() if k not in ("WDS_PLUGIN_ROOT", "WDS_PLUGIN_REV")}
    base["PYTHONDONTWRITEBYTECODE"] = "1"
    scratch = pathlib.Path(tempfile.mkdtemp(prefix="wds-fail-before-"))
    try:
        root = unpack(archive, scratch)
        before = run(args.python, tests, ids, {**base, "WDS_PLUGIN_ROOT": str(root), "WDS_PLUGIN_REV": commit},
                     scratch / "before.json")
        now = run(args.python, tests, ids, base, scratch / "now.json")
    except (RuntimeError, ValueError) as exc:
        print(f"fail_before: {exc}", file=sys.stderr)
        return 1
    finally:
        retry = lambda f, p, _: (os.chmod(p, stat.S_IWRITE), f(p))           # noqa: E731, a read-only file on Windows
        shutil.rmtree(scratch, **({"onexc": retry} if sys.version_info >= (3, 12) else {"onerror": retry}))

    rows = [(test, status(before.get(test)), status(now.get(test))) for test in sorted(set(before) | set(now))]
    rows = [(test, b, n, verdict(b, n)) for test, b, n in rows]
    head = ("test", f"before ({rev})", "now", "verdict")
    widths = [max(len(r[i]) for r in [head, *rows]) for i in range(4)]
    for r in [head, tuple("-" * w for w in widths), *rows]:
        print("  ".join(cell.ljust(w) for cell, w in zip(r, widths)).rstrip())
    counts = {label: sum(r[3] == v for r in rows) for v, label in (
        ("fixed", "fixed"), ("control", "controls"), ("still failing", "still failing"),
        ("regression", "regressions"), ("skipped", "skipped"))}
    print("\n" + ", ".join(f"{n} {label}" for label, n in counts.items()) + f"; against {commit[:12]}")
    return 1 if any(r[2] not in ("ok", "skipped") for r in rows) else 0


if __name__ == "__main__":
    sys.exit(main())
