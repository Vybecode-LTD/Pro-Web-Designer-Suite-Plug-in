"""Check the § pointers in the skills.

Every pointer must land on a numbered heading. A cross-file pointer must also
land on the SAME heading it was checked against, recorded in
tests/fixtures/section-pointers.json: renumber a reference and every pointer
into it fails until someone reads each one again.

Forms understood:
    `references/accessibility.md` §4      accessibility.md §4, section 4
    §7 of `email-architecture.md`         critique-method §2 (a known name)
    `rollout.md` §3, §4 / §2 and §6       continuations share the file
    §4 on its own, in markdown            a pointer into the same file

    python tools/check_pointers.py                    report (exit 1 on any problem)
    python tools/check_pointers.py --write-register   record the current targets;
                                                      read each new pointer first
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from dataclasses import dataclass

PLUGIN = pathlib.Path(__file__).resolve().parents[1]
SKILLS = PLUGIN / "skills"
REGISTER = PLUGIN / "tests" / "fixtures" / "section-pointers.json"
SOURCES = {".md", ".py", ".mjs", ".css", ".html", ".json"}
NUM = r"(\d+(?:\.\d+)*)"
HEADING = re.compile(r"^#{1,6}[ \t]+(?:§[ \t]?)?(\d+(?:\.\d+)*)[.)]?[ \t]+(.+)$", re.M)
FENCE = re.compile(r"^```.*?^```", re.S | re.M)


@dataclass(frozen=True)
class Pointer:
    source: str      # relative to skills/
    line: int
    target: str      # relative to skills/
    section: str
    cross_file: bool


CSS_SECTION = re.compile(r"^\s*§(\d+(?:\.\d+)*)\s+(\S.*)$")         # theme.css: §0  TITLE
CSS_NUMBERED = re.compile(r"^\s*(\d+(?:\.\d+)*)\.?\s+(\S.*)$")      # layout.css: 0.2 Title
RULE = re.compile(r"^\s*(?:/\*\s*)?[=-]{10,}\s*$")


def headings(path: pathlib.Path) -> dict[str, str]:
    """{number: title} for the first heading with each number. In markdown a
    numbered heading, code excluded; in CSS a numbered comment header."""
    out: dict[str, str] = {}
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".css":
        lines = text.splitlines()
        for i, line in enumerate(lines):
            m = CSS_SECTION.match(line) or (i and RULE.match(lines[i - 1]) and CSS_NUMBERED.match(line))
            if m:
                out.setdefault(m.group(1), m.group(2).strip())
        return out
    for m in HEADING.finditer(FENCE.sub("", text)):
        out.setdefault(m.group(1), m.group(2).strip())
    return out


def reference_index(skills: pathlib.Path) -> dict[str, list[pathlib.Path]]:
    """Pointer targets by the name a doc uses: a markdown stem, or a CSS file name."""
    index: dict[str, list[pathlib.Path]] = {}
    for p in [*skills.glob("*/references/*.md"), *skills.glob("*/assets/**/*.md")]:
        index.setdefault(p.stem, []).append(p)
    for p in skills.glob("*/assets/**/*.css"):
        index.setdefault(p.name, []).append(p)
    return index


def resolve(spelled: str, source: pathlib.Path, skills: pathlib.Path, index) -> pathlib.Path | None:
    """The file a pointer names: an explicit skill path, then the source's own
    skill, then the one file of that name in the suite."""
    spelled = spelled.strip("`")
    explicit = re.match(r"([\w-]+)/references/([\w-]+)\.md$", spelled)
    if explicit and (skills / explicit.group(1) / "references" / f"{explicit.group(2)}.md").is_file():
        return skills / explicit.group(1) / "references" / f"{explicit.group(2)}.md"
    stem = re.sub(r"\.md$", "", spelled.rsplit("/", 1)[-1])
    candidates = index.get(stem, [])
    skill = source.relative_to(skills).parts[0]
    own = [p for p in candidates if p.relative_to(skills).parts[0] == skill]
    if len(own) == 1:
        return own[0]
    if len({p.read_bytes() for p in candidates}) == 1:          # unique, or identical copies
        return candidates[0]
    return None


def pointers(skills: pathlib.Path = SKILLS) -> list[Pointer]:
    index = reference_index(skills)
    names = "|".join(re.escape(n) for n in sorted(index, key=len, reverse=True))
    ref = rf"`?((?:[\w-]+/)*(?:{names})(?:\.md)?)`?"
    forward = re.compile(rf"{ref},?\s+(?:§§?\s?|section\s+){NUM}", re.I)
    backward = re.compile(rf"§\s?{NUM}\s+of\s+{ref}")
    more = re.compile(rf"\s*(?:,|and|&|[–—]|to)\s*§?\s?{NUM}")
    found: list[Pointer] = []
    for path in sorted(p for p in skills.rglob("*") if p.suffix in SOURCES and p.is_file()):
        text = path.read_text(encoding="utf-8")
        used: set[int] = set()
        line = lambda i: text.count("\n", 0, i) + 1
        src = path.relative_to(skills).as_posix()

        def add(start: int, spelled: str, section: str, section_at: int) -> None:
            target = resolve(spelled, path, skills, index)
            if target is not None:
                used.add(section_at)
                found.append(Pointer(src, line(start), target.relative_to(skills).as_posix(),
                                     section, target != path))

        for m in forward.finditer(text):
            add(m.start(), m.group(1), m.group(2), m.start(2))
            end = m.end()
            while (c := more.match(text, end)):
                add(c.start(1), m.group(1), c.group(1), c.start(1))
                end = c.end()
        for m in backward.finditer(text):
            add(m.start(), m.group(2), m.group(1), m.start(1))
        if path.suffix in {".md", ".css"}:
            for m in re.finditer(rf"§§?\s?{NUM}", text):
                if m.start(1) not in used:
                    found.append(Pointer(src, line(m.start()), src, m.group(1), False))
    return found


def check(skills: pathlib.Path = SKILLS, register: pathlib.Path = REGISTER):
    """(unresolved, unregistered, moved, stale) — each a list of strings."""
    recorded = {(r["from"], r["to"], r["section"]): r["heading"]
                for r in json.loads(register.read_text(encoding="utf-8"))} if register.is_file() else {}
    unresolved, unregistered, moved = [], [], []
    seen = set()
    cache: dict[str, dict[str, str]] = {}
    for p in pointers(skills):
        heads = cache.setdefault(p.target, headings(skills / p.target))
        where = f"{p.source}:{p.line}"
        if p.section not in heads:
            unresolved.append(f"{where}: §{p.section} of {p.target} does not exist")
            continue
        if not p.cross_file:
            continue
        key = (p.source, p.target, p.section)
        seen.add(key)
        if key not in recorded:
            unregistered.append(f"{where}: §{p.section} of {p.target} ({heads[p.section]}) is not in the register")
        elif recorded[key] != heads[p.section]:
            moved.append(f"{where}: §{p.section} of {p.target} was '{recorded[key]}', is now '{heads[p.section]}'")
    stale = [f"{f} -> {t} §{s}" for (f, t, s) in recorded if (f, t, s) not in seen]
    return unresolved, unregistered, moved, stale


def write_register(skills: pathlib.Path = SKILLS, register: pathlib.Path = REGISTER) -> int:
    rows = {}
    for p in pointers(skills):
        if p.cross_file:
            heads = headings(skills / p.target)
            if p.section in heads:
                rows[(p.source, p.target, p.section)] = heads[p.section]
    data = [{"from": f, "to": t, "section": s, "heading": h} for (f, t, s), h in sorted(rows.items())]
    register.parent.mkdir(parents=True, exist_ok=True)
    register.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="")
    return len(data)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--write-register", action="store_true", help="record every cross-file pointer's current heading")
    args = ap.parse_args()
    if args.write_register:
        print(f"recorded {write_register()} cross-file pointers in {REGISTER.relative_to(PLUGIN)}")
        return 0
    problems = [line for group in check() for line in group]
    for line in problems:
        print(line)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
