"""Write caniemail.com's test results into the email skill, so a client that
changes is a diff (DL-C9): the client matrix's table and its notes, and the
client lists lint_email.py names. Standard library only; Python 3.9 or newer.

usage:
    python tools/sync_caniemail.py               rewrite both blocks from the pinned data
    python tools/sync_caniemail.py --check       exit 1 and list the stale blocks
    python tools/sync_caniemail.py --data FILE   pin a new download first, then rewrite

The pinned data is tests/fixtures/caniemail.json: the features in ROWS, cut
from caniemail's api/data.json (MIT licence, copyright 2019 Remi Parmentier)
to the families and platforms in COLUMNS. To refresh it:
    curl -o caniemail.json https://www.caniemail.com/api/data.json
    python tools/sync_caniemail.py --data caniemail.json
then read the diff: every cell that moved is a client that changed.

A cell is caniemail's result at the last version it lists for the platform.
caniemail lists them oldest first, so Outlook for Mac's 16.80 follows its
2016, which a numeric sort would get wrong. A column that joins platforms
(Apple Mail's macOS and iOS) is partial when they differ. caniemail records
the Gmail app with a non-Google account (GANGA) as a note on the Gmail app's
result. "Not supported with non Google accounts" makes the GANGA column not
supported and leaves the Google-account column the rest of the result; "Only
supported with non Google accounts" is the other way round. caniemail does not test the
new Outlook for Windows, so the table has no column for it.

The matrix holds one block between a `BEGIN caniemail` comment and an `END
caniemail` one, and lint_email.py one more; everything outside them is the
file's own. Files are written as UTF-8 with LF line endings, byte for byte the
same on every rerun. Exit codes: 0 in step (or rewritten), 1 stale (--check)
or a file without its block, 2 data this tool cannot read.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

PLUGIN = pathlib.Path(__file__).resolve().parents[1]
PINNED = "tests/fixtures/caniemail.json"
MATRIX = "skills/email-template-system/references/email-client-matrix.md"
LINT = "skills/email-template-system/scripts/lint_email.py"
SOURCE = "https://www.caniemail.com/api/data.json"
LICENCE = "MIT licence, copyright (c) 2019 Remi Parmentier; https://github.com/hteumeuleu/caniemail"

# Each column: its header, its key and its name in the lint's findings, and the
# (family, platform) pairs of caniemail's data it reads.
GMAIL_APP = (("gmail", "ios"), ("gmail", "android"))
COLUMNS = (
    ("Outlook Win (Word)", "word", "classic Outlook for Windows (Word engine)", (("outlook", "windows"),)),
    ("Outlook.com", "outlook-com", "Outlook.com", (("outlook", "outlook-com"),)),
    ("Outlook Mac", "outlook-mac", "Outlook for Mac", (("outlook", "macos"),)),
    ("Gmail web", "gmail-web", "Gmail on the web", (("gmail", "desktop-webmail"),)),
    ("Gmail app", "gmail-app", "the Gmail app", GMAIL_APP),
    ("GANGA", "ganga", "the Gmail app with a non-Google account", GMAIL_APP),
    ("Apple Mail", "apple-mail", "Apple Mail", (("apple-mail", "macos"), ("apple-mail", "ios"))),
    ("Yahoo", "yahoo", "Yahoo Mail", (("yahoo", "desktop-webmail"), ("yahoo", "ios"), ("yahoo", "android"))),
    ("Samsung", "samsung", "Samsung Email", (("samsung-email", "android"),)),
    ("Thunderbird", "thunderbird", "Thunderbird", (("thunderbird", "macos"), ("thunderbird", "windows"))),
)
# The matrix's rows: its label, and caniemail's feature. Every feature
# lint_email.py names is one, so each of its errors traces to a row.
ROWS = (
    ("`<body>` element", "html-body"),
    ("`<style>` element", "html-style"),
    ("`@media` queries", "css-at-media"),
    ("`@media (prefers-color-scheme)`", "css-at-media-prefers-color-scheme"),
    ("`display:flex`", "css-display-flex"),
    ("`display:grid`", "css-display-grid"),
    ("`flex-direction:column`", "css-flex-direction"),
    ("`justify-content`", "css-justify-content"),
    ("`align-items`", "css-align-items"),
    ("`gap`", "css-gap"),
    ("`float`", "css-float"),
    ("`position`", "css-position"),
    ("`max-width`", "css-max-width"),
    ("`min-height`", "css-min-height"),
    ("`padding`", "css-padding"),
    ("`margin`", "css-margin"),
    ("`border-radius`", "css-border-radius"),
    ("`box-shadow`", "css-box-shadow"),
    ("`text-shadow`", "css-text-shadow"),
    ("`letter-spacing`", "css-letter-spacing"),
    ("`opacity`", "css-opacity"),
    ("`background-image`", "css-background-image"),
    ("`background-size`", "css-background-size"),
    ("`object-fit`", "css-object-fit"),
    ("`filter`", "css-filter"),
    ("`transform`", "css-transform"),
    ("`transition`", "css-transition"),
    ("`animation`", "css-animation"),
    ("`:hover`", "css-pseudo-class-hover"),
    ("Web fonts (`@font-face`)", "css-at-font-face"),
    ("CSS custom properties", "css-variables"),
    ("`<svg>`", "html-svg"),
    ("`<video>`", "html-video"),
    ("`dir` attribute", "html-dir"),
    ("`lang` attribute", "html-lang"),
)
SYMBOL = {"y": "✅", "a": "⚠️", "n": "❌", "u": "?"}
RESULT = re.compile(r"^([ynau])((?: #\d+)*)$")
# caniemail's two notes on the Gmail app's accounts: "Not supported with non
# Google accounts" and "Only supported with non Google accounts".
NOT_WITH_GANGA = re.compile(r"\bnot supported with non[- ]?Google accounts?\b", re.I)
ONLY_WITH_GANGA = re.compile(r"\bonly supported with non[- ]?Google accounts?\b", re.I)
SUPERSCRIPT = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")
FEATURE_URL = "https://www.caniemail.com/features/"
NOTE = "written by tools/sync_caniemail.py from caniemail's data; never edit it by hand"
BLOCK = {
    MATRIX: re.compile(r"^<!-- BEGIN caniemail\b.*?^<!-- END caniemail[^\n]*", re.M | re.S),
    LINT: re.compile(r"^# BEGIN caniemail\b.*?^# END caniemail[^\n]*", re.M | re.S),
}


class DataError(ValueError):
    """The data holds something this tool cannot read."""


def need(value, kind, where: str):
    """`value` if it is a `kind`, else a DataError naming `where`."""
    if not isinstance(value, kind) or isinstance(value, bool):
        raise DataError(f"{where} is not a {kind.__name__}")
    return value


def excerpt(data) -> dict:
    """The features in ROWS from caniemail's whole api/data.json, each cut to
    the platforms COLUMNS read, keeping caniemail's order of versions."""
    need(data, dict, "the data")
    features = need(data.get("data"), list, "data")
    by_slug = {}
    for i, feature in enumerate(features):
        need(feature, dict, f"data[{i}]")
        by_slug.setdefault(feature.get("slug"), feature)
    platforms = {pair for *_, pairs in COLUMNS for pair in pairs}
    kept = []
    for _, slug in ROWS:
        feature = by_slug.get(slug)
        if feature is None:
            raise DataError(f"no feature {slug!r}")
        stats = need(feature.get("stats"), dict, f"{slug}.stats")
        cut = {}
        for family, plats in stats.items():
            for platform, versions in need(plats, dict, f"{slug}.stats.{family}").items():
                if (family, platform) in platforms:
                    cut.setdefault(family, {})[platform] = versions
        entry = {key: feature.get(key) for key in ("slug", "title", "url", "last_test_date", "notes_by_num")}
        entry["stats"] = cut
        kept.append(entry)
    return {"source": SOURCE, "licence": LICENCE, "api_version": data.get("api_version"),
            "last_update_date": data.get("last_update_date"), "data": kept}


def read_feature(feature, slug: str) -> tuple[str, str, str, dict, dict]:
    """A pinned feature's title, URL, test date, notes and stats, each checked."""
    need(feature, dict, slug)
    title = need(feature.get("title"), str, f"{slug}.title")
    url = need(feature.get("url"), str, f"{slug}.url")
    if url != f"{FEATURE_URL}{slug}/":
        raise DataError(f"{slug}.url is not caniemail's page for it: {url!r}")
    tested = need(feature.get("last_test_date"), str, f"{slug}.last_test_date")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", tested):
        raise DataError(f"{slug}.last_test_date is not a date: {tested!r}")
    notes = feature.get("notes_by_num")
    notes = {} if notes is None else need(notes, dict, f"{slug}.notes_by_num")
    for num, text in notes.items():
        need(text, str, f"{slug}.notes_by_num.{num}")
    stats = need(feature.get("stats"), dict, f"{slug}.stats")
    return title, url, tested, notes, stats


def latest(stats: dict, family: str, platform: str, slug: str) -> tuple[str, list[str]] | None:
    """caniemail's result at the last version it lists: its code and note numbers."""
    versions = stats.get(family, {})
    need(versions, dict, f"{slug}.stats.{family}")
    results = versions.get(platform)
    if results is None:
        return None
    need(results, dict, f"{slug}.stats.{family}.{platform}")
    if not results:
        return None
    raw = need(list(results.values())[-1], str, f"{slug}.stats.{family}.{platform}")
    match = RESULT.match(raw.strip())
    if not match:
        raise DataError(f"{slug}.stats.{family}.{platform}: unknown result {raw!r}")
    return match.group(1), re.findall(r"\d+", match.group(2))


def cell(column: str, pairs, stats: dict, notes: dict, slug: str) -> tuple[str, list[str]]:
    """One column's code (y, a, n, u, or "" untested) and its note numbers."""
    codes, nums = [], []
    for family, platform in pairs:
        got = latest(stats, family, platform, slug)
        if got is None:
            continue
        code, refs = got
        if pairs is GMAIL_APP:
            without = [n for n in refs if NOT_WITH_GANGA.search(notes.get(n, ""))]
            only = [n for n in refs if ONLY_WITH_GANGA.search(notes.get(n, ""))]
            if column == "GANGA" and (without or only):
                code, refs = ("n", without) if without else ("y", only)
            elif without:
                refs = [n for n in refs if n not in without]
                code = "y" if code == "a" and not refs else code
            elif only:
                code, refs = "n", only
        codes.append(code)
        nums.extend(n for n in refs if n not in nums)
    if not codes:
        return "", []
    return (codes[0] if len(set(codes)) == 1 else "a"), sorted(nums, key=int)


def verdicts(pinned) -> list[tuple[str, str, str, str, list[tuple[str, list[str]]], dict]]:
    """Each row: its label, slug, URL, test date, cells and notes."""
    need(pinned, dict, "the pinned data")
    by_slug = {f.get("slug"): f for f in need(pinned.get("data"), list, "data") if isinstance(f, dict)}
    rows = []
    for label, slug in ROWS:
        if slug not in by_slug:
            raise DataError(f"no feature {slug!r}; run with --data")
        _, url, tested, notes, stats = read_feature(by_slug[slug], slug)
        cells = [cell(header, pairs, stats, notes, slug) for header, *_, pairs in COLUMNS]
        rows.append((label, slug, url, tested, cells, notes))
    return rows


def md_cell(code: str, nums: list[str]) -> str:
    if not code:
        return "—"
    return " ".join([SYMBOL[code], *(n.translate(SUPERSCRIPT) for n in nums)])


def matrix_block(pinned: dict, rows) -> str:
    lines = [f"<!-- BEGIN caniemail: {NOTE} -->",
             f"caniemail.com's data of {str(pinned.get('last_update_date') or '?')[:10]}; each row is linked to "
             "its page, which lists every version tested.",
             "",
             "| Feature | Tested | " + " | ".join(c[0] for c in COLUMNS) + " |",
             "|---|---|" + "---|" * len(COLUMNS)]
    for label, _, url, tested, cells, _ in rows:
        lines.append(f"| [{label}]({url}) | {tested} | " + " | ".join(md_cell(*c) for c in cells) + " |")
    lines += ["", "caniemail's notes on the results in the table:", ""]
    for label, slug, _, _, cells, notes in rows:
        used = sorted({n for _, nums in cells for n in nums}, key=int)
        missing = [n for n in used if n not in notes]
        if missing:
            raise DataError(f"{slug}: a result cites note {missing[0]}, which it does not have")
        if used:
            text = " ".join(f"{n.translate(SUPERSCRIPT)} {' '.join(notes[n].split())}" for n in used)
            lines.append(f"- **{label}:** {text}")
    lines.append("<!-- END caniemail -->")
    return "\n".join(lines)


def lint_block(rows) -> str:
    lines = [f"# BEGIN caniemail: {NOTE}",
             "# Each client's name in a finding; then each feature: the date caniemail tested it,",
             "# and the clients without support and with partial support at the last version",
             "# tested, by key.",
             "CANIEMAIL_CLIENTS = {"]
    lines += [f'    "{key}": "{name}",' for _, key, name, _ in COLUMNS]
    lines += ["}", "CANIEMAIL = {"]
    for _, slug, _, tested, cells, _ in rows:
        never = " ".join(key for (_, key, _, _), (code, _) in zip(COLUMNS, cells) if code == "n")
        partial = " ".join(key for (_, key, _, _), (code, _) in zip(COLUMNS, cells) if code == "a")
        head = f'    "{slug}": ("{tested}", '
        line = f'{head}"{never}", "{partial}"),'
        if len(line) > 100:
            line = f'{head}"{never}",\n{" " * len(head)}"{partial}"),'
        lines.append(line)
    lines += ["}", "# END caniemail"]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--check", action="store_true", help="exit 1 and list the stale blocks; write nothing")
    parser.add_argument("--data", type=pathlib.Path, help="caniemail's api/data.json, to pin before writing")
    parser.add_argument("--root", type=pathlib.Path, default=PLUGIN, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.check and args.data:
        parser.error("--check reads the pinned data; refresh it without --check")

    try:
        if args.data:
            pinned = excerpt(json.loads(args.data.read_bytes().decode("utf-8-sig")))
        else:
            pinned = json.loads((args.root / PINNED).read_bytes().decode("utf-8"))
        rows = verdicts(pinned)
        blocks = {MATRIX: matrix_block(pinned, rows), LINT: lint_block(rows)}
    except (OSError, ValueError) as exc:      # DataError and a JSONDecodeError are ValueErrors
        print(f"sync_caniemail: {args.data or PINNED}: {exc}", file=sys.stderr)
        return 2
    if args.data:
        text = json.dumps(pinned, ensure_ascii=False, indent=1) + "\n"
        (args.root / PINNED).write_bytes(text.encode("utf-8"))
        print(f"pinned: {PINNED}")

    stale, missing = [], []
    for rel, pattern in BLOCK.items():
        path = args.root / rel
        text = path.read_bytes().decode("utf-8")
        if len(pattern.findall(text)) != 1:
            missing.append(f"{rel}: {len(pattern.findall(text))} caniemail blocks, not one")
            continue
        new = pattern.sub(lambda _, rel=rel: blocks[rel], text)
        if new != text:
            stale.append(rel)
            if not args.check:
                path.write_bytes(new.encode("utf-8"))
    for line in missing:
        print(f"sync_caniemail: {line}", file=sys.stderr)
    for rel in stale:
        print(f"{'stale' if args.check else 'rewrote'}: {rel}")
    if args.check and stale:
        print(f"{len(stale)} block(s) differ from {PINNED}; run tools/sync_caniemail.py", file=sys.stderr)
    return 1 if missing or (args.check and stale) else 0


if __name__ == "__main__":
    sys.exit(main())
