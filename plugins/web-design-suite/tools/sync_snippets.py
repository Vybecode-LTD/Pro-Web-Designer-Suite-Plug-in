"""Keep the code the references quote from the starter identical to the starter.

A reference quotes a region of a starter file with a marker on the line
directly above the code fence:

    <!-- snippet: layout.css#flow -->
    ```css
    …replaced from the region…
    ```

and the source file marks the region with two comments:

    /* @snippet flow */
    …
    /* @end-snippet */

A bare file name is looked up in web-design-studio/assets/starter/styles/; a
path with a slash is relative to skills/. The region is dedented, so a rule
indented inside `@layer layout { … }` is quoted flush left.

    python tools/sync_snippets.py            rewrite every quote from its source
    python tools/sync_snippets.py --check    exit 1 and list the stale quotes

Exit codes: 0 in sync (or rewritten), 1 stale under --check, 2 a marker names a
file or region that does not exist.
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys
import textwrap

PLUGIN = pathlib.Path(__file__).resolve().parents[1]
SKILLS = PLUGIN / "skills"
STARTER = SKILLS / "web-design-studio" / "assets" / "starter" / "styles"
QUOTE = re.compile(r"^<!--\s*snippet:\s*(?P<src>[^#\s]+)#(?P<name>[\w-]+)\s*-->\n"
                   r"```(?P<lang>\w*)\n(?P<body>.*?)^```", re.S | re.M)


class MissingRegion(Exception):
    pass


def source_path(src: str, skills: pathlib.Path = SKILLS) -> pathlib.Path:
    starter = skills / "web-design-studio" / "assets" / "starter" / "styles"
    return skills / src if "/" in src else starter / src


def region(src: str, name: str, skills: pathlib.Path = SKILLS) -> str:
    path = source_path(src, skills)
    if not path.is_file():
        raise MissingRegion(f"{src}: no such file")
    m = re.search(rf"^[ \t]*/\*\s*@snippet\s+{re.escape(name)}\s*\*/[ \t]*\n(.*?)^[ \t]*/\*\s*@end-snippet\s*\*/",
                  path.read_text(encoding="utf-8"), re.S | re.M)
    if not m:
        raise MissingRegion(f"{src}: no region '{name}'")
    return textwrap.dedent(m.group(1)).rstrip() + "\n"


def quoted_blocks(skills: pathlib.Path = SKILLS):
    """(doc, match) for every quote in the skills' markdown."""
    for doc in sorted(skills.rglob("*.md")):
        for m in QUOTE.finditer(doc.read_text(encoding="utf-8")):
            yield doc, m


def sync(check: bool, skills: pathlib.Path = SKILLS) -> list[str]:
    """Return the stale quotes; rewrite them unless `check`."""
    stale = []
    for doc in sorted(skills.rglob("*.md")):
        text = doc.read_text(encoding="utf-8")

        def fresh(m: re.Match) -> str:
            want = region(m["src"], m["name"], skills)
            if m["body"] != want:
                stale.append(f"{doc.relative_to(skills).as_posix()}: {m['src']}#{m['name']}")
            return f"<!-- snippet: {m['src']}#{m['name']} -->\n```{m['lang']}\n{want}```"

        new = QUOTE.sub(fresh, text)
        if new != text and not check:
            doc.write_text(new, encoding="utf-8", newline="")
    return stale


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--check", action="store_true", help="report stale quotes instead of rewriting them")
    args = ap.parse_args()
    try:
        stale = sync(args.check)
    except MissingRegion as exc:
        print(f"sync_snippets: {exc}", file=sys.stderr)
        return 2
    for line in stale:
        print(("stale: " if args.check else "rewrote: ") + line)
    if args.check and stale:
        print(f"{len(stale)} quote(s) differ from the starter; run tools/sync_snippets.py", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
