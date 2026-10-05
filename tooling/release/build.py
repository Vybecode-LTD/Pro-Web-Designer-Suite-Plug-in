"""Build a release of plugins/web-design-suite from git: the plugin's zip, one
.skill file per skill, and their SHA-256 sums.

usage: python tooling/release/build.py <out dir> [--rev REV]

Everything comes from what git holds at REV (default HEAD), and nothing else:
- only tracked files, so a local node_modules, .DS_Store or editor backup never ships;
- git's file modes, so a script git marks executable is executable when unpacked;
- every entry dated at REV's commit time, in sorted order, so two builds of
  one commit are the same, byte for byte, with the same zlib. Python 3.14
  deflates with zlib-ng on Windows and with zlib on the CI's Linux, so a
  build there and the release differ in bytes and SHA256SUMS while every
  file is the same: compare them with tooling/release/compare.py.

It refuses, and writes nothing, when the plugin holds something an archive
cannot carry everywhere (a symbolic link, a submodule), a tracked file that
`git archive` leaves out (`export-ignore`), or a skill the platform refuses:
its folder and `name` must match, and the name and description must keep to
https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview
("Field requirements": a name of at most 64 characters, lowercase letters,
numbers and hyphens, without "anthropic" or "claude"; a description of at
most 1024 characters, without XML tags).

Into <out dir>, which must be empty or not exist yet:
  web-design-suite-<version>.zip  the plugin, under web-design-suite/: folders
                                  stored and files deflated, with Unix modes
  <skill>.skill                   each skill as Anthropic's skill-creator
                                  packages one (skills/skill-creator/scripts/
                                  package_skill.py in github.com/anthropics/
                                  skills): a deflated zip of the skill's
                                  folder, files only, without __pycache__,
                                  node_modules, *.pyc, .DS_Store or a top-level
                                  evals/. It adds the plugin's LICENSE, which
                                  the MIT license asks every copy to carry.
  SHA256SUMS                      every file above, in sha256sum's format
The version is plugin.json's at REV. The files removed since the previous v*
tag are listed.

A description longer than 200 characters is a warning, not a refusal: the
claude.ai help center gives that limit for uploads ("How to create custom
skills"), where the platform's own is 1024.

Run it from anywhere inside the repository: it builds that repository. The
variables that tie git to one repository (GIT_DIR and the rest `git rev-parse
--local-env-vars` names), inherited from a hook or a shell, are dropped.
Exit codes: 0 built, 1 refused or an archive failed its own test, 2 bad invocation.
"""
from __future__ import annotations

import argparse
import functools
import hashlib
import io
import json
import os
import pathlib
import re
import stat
import subprocess
import sys
import tarfile
import time
import zipfile

PLUGIN = "plugins/web-design-suite"
TOP = "web-design-suite/"
FILE_MODES = {"100644", "100755"}          # git's modes for a file; 120000 is a link, 160000 a submodule
SKILL_EXCLUDED_PARTS = {"__pycache__", "node_modules"}
SKILL_EXCLUDED_NAMES = {".DS_Store"}
NAME = re.compile(r"[a-z0-9-]{1,64}")
UPLOAD_DESCRIPTION = 200


def git(*args: str, env: dict[str, str] | None = None, cwd: str | None = None) -> bytes:
    return subprocess.run(["git", *args], check=True, capture_output=True, env=env, cwd=cwd).stdout


def own_repository() -> tuple[dict[str, str], str]:
    """The environment without git's repository variables, and the top folder
    of the repository the builder runs in."""
    local = set(git("rev-parse", "--local-env-vars").decode().split())
    env = {k: v for k, v in os.environ.items() if k not in local}
    return env, git("rev-parse", "--show-toplevel", env=env).decode().strip()


def frontmatter(text: str) -> dict[str, str]:
    """`name` and `description` from a SKILL.md's frontmatter: plain, quoted
    or folded values, each joined into one line."""
    m = re.match(r"---\r?\n(.*?)\r?\n---", text, re.S)
    fields: dict[str, str] = {}
    key = None
    for line in (m.group(1) if m else "").splitlines():
        km = re.match(r"([A-Za-z][\w-]*):\s*(.*)$", line)
        if km:
            key = km.group(1)
            fields[key] = km.group(2)
        elif key and line.strip():
            fields[key] += " " + line.strip()
    out = {}
    for k in ("name", "description"):
        value = " ".join(fields.get(k, "").split())
        value = re.sub(r"^[>|][+-]?\s*", "", value)
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
            value = value[1:-1]
        out[k] = value
    return out


def skill_problems(folder: str, meta: dict[str, str]) -> list[str]:
    name, description = meta["name"], meta["description"]
    problems = []
    if name != folder:
        problems.append(f"its name is {name!r}, and its folder {folder!r}")
    if not NAME.fullmatch(name) or "anthropic" in name or "claude" in name:
        problems.append(f"the name {name!r} is not 1 to 64 lowercase letters, numbers and hyphens "
                        f"without 'anthropic' or 'claude'")
    if not description or len(description) > 1024 or re.search(r"<[^>]*>", description):
        problems.append(f"the description is empty, longer than 1024 characters, or holds an XML tag")
    return problems


def zip_bytes(entries: list[tuple[str, int, bytes]], date_time: tuple[int, ...]) -> bytes:
    """A zip of (name, mode, data), in the order given: folders stored, files
    deflated, with Unix modes."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, mode, data in entries:
            info = zipfile.ZipInfo(name, date_time=date_time)
            info.create_system = 3
            info.external_attr = mode << 16
            if name.endswith("/"):
                info.external_attr |= 0x10                  # MS-DOS directory bit
                info.compress_type = zipfile.ZIP_STORED
            else:
                info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, data)
    return buf.getvalue()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("out", help="the folder to write into; it must be empty or not exist yet")
    parser.add_argument("--rev", default="HEAD", help="the commit to build (default: HEAD)")
    args = parser.parse_args(argv)

    out = pathlib.Path(args.out)
    if out.exists() and (not out.is_dir() or any(out.iterdir())):
        parser.error(f"{out} is not an empty folder; this tool never overwrites a release")
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
    try:
        previous = run("describe", "--tags", "--abbrev=0", "--match", "v*", commit + "^").decode().strip()
        removed = run("diff", "--name-only", "--diff-filter=D", "-z", previous, commit, "--", PLUGIN)
    except subprocess.CalledProcessError:
        previous, removed = None, b""

    tracked: dict[str, str] = {}                           # path -> git's mode
    for record in tree.split(b"\0"):
        if record:
            meta, _, path = record.partition(b"\t")
            tracked[path.decode("utf-8", "surrogateescape")] = meta.split(b" ", 1)[0].decode()

    files: dict[str, tuple[int, bytes]] = {}               # path inside the plugin -> (mode, content)
    folders: set[str] = set()
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        for member in tar.getmembers():
            if not member.name.startswith(PLUGIN):
                continue
            rel = member.name[len(PLUGIN):].strip("/")
            if member.isdir():
                folders.add(rel)
            elif member.isfile():
                executable = tracked.get(member.name) == "100755"   # not member.mode: tar.umask can mask it
                files[rel] = (stat.S_IFREG | (0o755 if executable else 0o644), tar.extractfile(member).read())

    refused = [f"{path} is a {'symbolic link' if mode == '120000' else 'submodule'}, "
               f"which an archive cannot carry everywhere"
               for path, mode in sorted(tracked.items()) if mode not in FILE_MODES]
    refused += [f"{path} is tracked, but git archive left it out (export-ignore?)"
                for path, mode in sorted(tracked.items())
                if mode in FILE_MODES and path[len(PLUGIN) + 1:] not in files]
    try:
        version = json.loads(files[".claude-plugin/plugin.json"][1])["version"]
    except (KeyError, ValueError, TypeError):
        version = None
        refused.append(".claude-plugin/plugin.json has no version")

    skills = sorted({rel.split("/")[1] for rel in files if rel.startswith("skills/") and rel.count("/") >= 2})
    warnings = []
    for skill in skills:
        doc = files.get(f"skills/{skill}/SKILL.md")
        if doc is None:
            refused.append(f"skills/{skill} has no SKILL.md")
            continue
        meta = frontmatter(doc[1].decode("utf-8", "replace"))
        refused += [f"skills/{skill}: {p}" for p in skill_problems(skill, meta)]
        if len(meta["description"]) > UPLOAD_DESCRIPTION:
            warnings.append(f"{skill}: its description has {len(meta['description'])} characters; "
                            f"claude.ai's help center gives {UPLOAD_DESCRIPTION} for an upload")
    if refused:
        for reason in refused:
            print(f"refused: {reason}", file=sys.stderr)
        print(f"nothing written to {out}", file=sys.stderr)
        return 1

    date_time = time.gmtime(stamp)[:6]
    names = sorted({TOP} | {TOP + f + "/" for f in folders if f} | {TOP + f for f in files})
    archives = {f"web-design-suite-{version}.zip": zip_bytes(
        [(n, stat.S_IFDIR | 0o755, b"") if n.endswith("/") else (n, *files[n[len(TOP):]]) for n in names],
        date_time)}
    license_file = files.get("LICENSE")
    for skill in skills:
        prefix = f"skills/{skill}/"
        entries = []
        for rel in sorted(files):
            inner = rel[len(prefix):]
            parts = inner.split("/")
            if (not rel.startswith(prefix) or parts[0] == "evals" or SKILL_EXCLUDED_PARTS & set(parts)
                    or parts[-1] in SKILL_EXCLUDED_NAMES or parts[-1].endswith(".pyc")):
                continue
            entries.append((f"{skill}/{inner}", *files[rel]))
        if license_file and f"{prefix}LICENSE" not in files:
            entries.append((f"{skill}/LICENSE", *license_file))
        archives[f"{skill}.skill"] = zip_bytes(sorted(entries), date_time)

    out.mkdir(parents=True, exist_ok=True)
    bad = []
    for name, data in archives.items():
        (out / name).write_bytes(data)
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            if z.testzip():
                bad.append(name)
    sums = "".join(f"{hashlib.sha256(data).hexdigest()}  {name}\n" for name, data in sorted(archives.items()))
    (out / "SHA256SUMS").write_bytes(sums.encode("ascii"))

    plugin_zip = next(iter(archives))
    executable = sum(1 for n in names if not n.endswith("/") and files[n[len(TOP):]][0] & 0o111)
    print(f"wrote {out} from {commit[:12]}: {plugin_zip} ({len(names)} entries, {len(files)} files, "
          f"{executable} executable), {len(skills)} .skill files, SHA256SUMS; testzip: "
          f"{', '.join(bad) or 'OK'}")
    for path in removed.decode("utf-8", "surrogateescape").split("\0"):
        if path:
            print(f"  removed since {previous}: {path[len(PLUGIN) + 1:]}")
    for warning in warnings:
        print(f"  warning: {warning}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
