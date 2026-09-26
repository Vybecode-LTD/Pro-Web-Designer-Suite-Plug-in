"""Build the release zip of plugins/web-design-suite from git.

usage: python tooling/release/build_zip.py <previous release zip> <out.zip> [--rev REV]

The zip holds what git holds at REV (default HEAD), and nothing else:
- only tracked files, so a local node_modules, .DS_Store or editor backup never ships;
- git's file modes, so a script git marks executable is executable in the zip;
- every entry dated at REV's commit time, so two builds of one commit are identical.

Entries that were in the previous release keep its order, new ones follow sorted,
and removed ones are listed. Folders are stored and files deflated, with Unix
metadata, as the earlier releases were. Run it from inside the repository.
Exit codes: 0 built, 1 the zip failed its own test, 2 bad invocation.
"""
from __future__ import annotations

import argparse
import io
import stat
import subprocess
import sys
import tarfile
import time
import zipfile

PLUGIN = "plugins/web-design-suite"
TOP = "web-design-suite/"


def git(*args: str) -> bytes:
    return subprocess.run(["git", *args], check=True, capture_output=True).stdout


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("previous", help="the previous release's zip, whose entry order is kept")
    parser.add_argument("out", help="the zip to write; it must not exist yet")
    parser.add_argument("--rev", default="HEAD", help="the commit to build (default: HEAD)")
    args = parser.parse_args(argv)

    try:
        commit = git("rev-parse", "--verify", args.rev + "^{commit}").decode().strip()
        stamp = int(git("log", "-1", "--format=%ct", commit).decode().strip())
        archive = git("archive", "--format=tar", commit, PLUGIN)
    except (OSError, subprocess.CalledProcessError) as exc:
        detail = getattr(exc, "stderr", b"") or b""
        parser.error(f"cannot read {args.rev!r} from git: {detail.decode(errors='replace').strip() or exc}")
    with zipfile.ZipFile(args.previous) as z:
        order = [i.filename for i in z.infolist()]

    date_time = time.gmtime(stamp)[:6]
    entries: dict[str, tuple[int, bytes]] = {}            # zip name -> (mode, content)
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        for member in tar.getmembers():
            rel = member.name[len(PLUGIN):].lstrip("/")
            if not member.name.startswith(PLUGIN) or member.issym() or member.islnk():
                continue
            if member.isdir():
                entries[TOP + rel + "/" if rel else TOP] = (stat.S_IFDIR | 0o755, b"")
            elif member.isfile():
                data = tar.extractfile(member).read()
                entries[TOP + rel] = (stat.S_IFREG | (0o755 if member.mode & 0o111 else 0o644), data)
    entries.setdefault(TOP, (stat.S_IFDIR | 0o755, b""))

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
