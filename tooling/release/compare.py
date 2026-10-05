"""Compare two release builds by what their archives hold, not by their bytes.

usage: python tooling/release/compare.py <build A> <build B>

build.py makes two builds of one commit byte-identical with the same zlib,
and only then. Python 3.14 on Windows deflates with zlib-ng and the CI's
Linux Python with zlib, so a local build and the release differ in their
compressed bytes and in SHA256SUMS while every file inside is the same (N34,
found when 3.3.0 was released). This compares the two folders' archives
entry by entry: the entries' names in order, and each one's CRC-32,
uncompressed size, date and Unix mode. A file in either folder that is not
a zip is compared byte for byte; SHA256SUMS is skipped, since it hashes the
compressed bytes.

Exit codes: 0 the same, 1 a difference (each one is printed), 2 bad invocation.
"""
from __future__ import annotations

import argparse
import pathlib
import sys
import zipfile

SKIPPED = {"SHA256SUMS"}


def entries(path: pathlib.Path) -> list[tuple]:
    with zipfile.ZipFile(path) as archive:
        return [(i.filename, i.CRC, i.file_size, i.date_time, i.external_attr >> 16)
                for i in archive.infolist()]


def differences(a: pathlib.Path, b: pathlib.Path) -> list[str]:
    names = {folder: {p.name for p in folder.iterdir() if p.is_file() and p.name not in SKIPPED}
             for folder in (a, b)}
    found = [f"{name}: only in {folder}" for folder, other in ((a, b), (b, a))
             for name in sorted(names[folder] - names[other])]
    for name in sorted(names[a] & names[b]):
        x, y = a / name, b / name
        if not (zipfile.is_zipfile(x) and zipfile.is_zipfile(y)):
            if x.read_bytes() != y.read_bytes():
                found.append(f"{name}: the bytes differ")
            continue
        ex, ey = entries(x), entries(y)
        if [e[0] for e in ex] != [e[0] for e in ey]:
            found.append(f"{name}: the entries differ, or their order does")
            continue
        for p, q in zip(ex, ey):
            fields = [field for field, u, v in zip(("CRC", "size", "date", "mode"), p[1:], q[1:]) if u != v]
            if fields:
                found.append(f"{name}: {p[0]} differs in {', '.join(fields)}")
    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("a", help="one build folder")
    parser.add_argument("b", help="the other")
    args = parser.parse_args(argv)
    a, b = pathlib.Path(args.a), pathlib.Path(args.b)
    for folder in (a, b):
        if not folder.is_dir():
            parser.error(f"{folder} is not a folder")
    found = differences(a, b)
    for line in found:
        print(line)
    if not found:
        count = len([p for p in a.iterdir() if p.is_file() and p.name not in SKIPPED])
        print(f"the same: {count} files, compared by content")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
