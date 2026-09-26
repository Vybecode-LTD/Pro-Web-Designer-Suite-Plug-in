"""Build the release zip of plugins/web-design-suite from git.

usage: python tooling/release/build_zip.py <previous release zip> <out.zip> [--rev REV]

The zip holds what git holds at REV (default HEAD), and nothing else:
- only tracked files, so a local node_modules, .DS_Store or editor backup never ships;
- git's file modes, so a script git marks executable is executable in the zip;
- every entry dated at REV's commit time, so two builds of one commit are identical.

It refuses, and writes nothing, when the plugin holds something a zip cannot
carry everywhere (a symbolic link, a submodule) or a tracked file that
`git archive` leaves out (`export-ignore`). Entries that were in the previous
release keep its order, new ones follow sorted, and removed ones are listed.
Folders are stored and files deflated, with Unix metadata, as the earlier
releases were.

Run it from anywhere inside the repository: it builds that repository. The
variables that tie git to one repository (GIT_DIR, GIT_INDEX_FILE and the rest
`git rev-parse --local-env-vars` names), inherited from a hook or a shell, are
dropped.
Exit codes: 0 built, 1 refused or the zip failed its own test, 2 bad invocation.
"""
from __future__ import annotations

import argparse
import functools
import io
import os
import stat
import subprocess
import sys
import tarfile
import time
import zipfile

PLUGIN = "plugins/web-design-suite"
TOP = "web-design-suite/"
FILE_MODES = {"100644", "100755"}          # git's modes for a file; 120000 is a link, 160000 a submodule


def git(*args: str, env: dict[str, str] | None = None, cwd: str | None = None) -> bytes:
    return subprocess.run(["git", *args], check=True, capture_output=True, env=env, cwd=cwd).stdout


def own_repository() -> tuple[dict[str, str], str]:
    """The environment without git's repository variables, and the top folder
    of the repository the builder runs in."""
    local = set(git("rev-parse", "--local-env-vars").decode().split())
    env = {k: v for k, v in os.environ.items() if k not in local}
    return env, git("rev-parse", "--show-toplevel", env=env).decode().strip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("previous", help="the previous release's zip, whose entry order is kept")
    parser.add_argument("out", help="the zip to write; it must not exist yet")
    parser.add_argument("--rev", default="HEAD", help="the commit to build (default: HEAD)")
    args = parser.parse_args(argv)

    try:
        env, top = own_repository()
        run = functools.partial(git, env=env, cwd=top)
        commit = run("rev-parse", "--verify", args.rev + "^{commit}").decode().strip()
        stamp = int(run("log", "-1", "--format=%ct", commit).decode().strip())
        tree = run("ls-tree", "-r", "-z", commit, "--", PLUGIN)
        archive = run("archive", "--format=tar", commit, PLUGIN)
    except (OSError, subprocess.CalledProcessError) as exc:
        detail = getattr(exc, "stderr", b"") or b""
        parser.error(f"cannot read {args.rev!r} from git: {detail.decode(errors='replace').strip() or exc}")
    with zipfile.ZipFile(args.previous) as z:
        order = [i.filename for i in z.infolist()]

    tracked: dict[str, str] = {}                           # path -> git's mode
    for record in tree.split(b"\0"):
        if record:
            meta, _, path = record.partition(b"\t")
            tracked[path.decode("utf-8", "surrogateescape")] = meta.split(b" ", 1)[0].decode()

    date_time = time.gmtime(stamp)[:6]
    entries: dict[str, tuple[int, bytes]] = {}            # zip name -> (mode, content)
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        for member in tar.getmembers():
            rel = member.name[len(PLUGIN):].lstrip("/")
            if not member.name.startswith(PLUGIN):
                continue
            if member.isdir():
                entries[TOP + rel + "/" if rel else TOP] = (stat.S_IFDIR | 0o755, b"")
            elif member.isfile():
                data = tar.extractfile(member).read()
                executable = tracked.get(member.name) == "100755"   # not member.mode: tar.umask can mask it
                entries[TOP + rel] = (stat.S_IFREG | (0o755 if executable else 0o644), data)
    entries.setdefault(TOP, (stat.S_IFDIR | 0o755, b""))

    refused = [f"{path} is a {'symbolic link' if mode == '120000' else 'submodule'}, "
               f"which a zip cannot carry everywhere"
               for path, mode in sorted(tracked.items()) if mode not in FILE_MODES]
    refused += [f"{path} is tracked, but git archive left it out (export-ignore?)"
                for path, mode in sorted(tracked.items())
                if mode in FILE_MODES and TOP + path[len(PLUGIN) + 1:] not in entries]
    if refused:
        for reason in refused:
            print(f"refused: {reason}", file=sys.stderr)
        print(f"nothing written to {args.out}", file=sys.stderr)
        return 1

    names = [n for n in order if n in entries] + sorted(n for n in entries if n not in set(order))
    removed = [n for n in order if n not in entries]

    try:
        zout = zipfile.ZipFile(args.out, "x")
    except FileExistsError:
        parser.error(f"{args.out} exists; this tool never overwrites a release")
    with zout:
        for name in names:
            mode, data = entries[name]
            info = zipfile.ZipInfo(name, date_time=date_time)
            info.create_system = 3
            info.external_attr = mode << 16
            if name.endswith("/"):
                info.external_attr |= 0x10                  # MS-DOS directory bit
                info.compress_type = zipfile.ZIP_STORED
            else:
                info.compress_type = zipfile.ZIP_DEFLATED
            zout.writestr(info, data)

    with zipfile.ZipFile(args.out) as z:
        bad = z.testzip()
        infos = z.infolist()
    executable = sum(1 for i in infos if not i.is_dir() and (i.external_attr >> 16) & 0o111)
    print(f"wrote {args.out} from {commit[:12]}: {len(infos)} entries "
          f"({sum(i.is_dir() for i in infos)} folders, {len(infos) - sum(i.is_dir() for i in infos)} files, "
          f"{executable} executable), testzip: {bad or 'OK'}")
    for name in removed:
        print(f"  removed since the previous release: {name}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
