#!/usr/bin/env python3
"""
deprecate.py — remove something from a design system without breaking anyone.

A deprecation is a promise with four stages: announce, warn, migrate, remove.
This script is the ledger that makes the promise checkable, the marker that
makes it visible in the source, the codemod that makes it cheap, and — the part
teams actually lack — the evidence that says whether removal is safe yet.

    announce   `add` records it and injects a machine-readable marker
    warn       the marker is what a linter, the auditor and a grep all see
    migrate    `mapping.json` is emitted in apply_codemod.py's own format
    remove     `scan` counts real usage across consumer repos; `status` says
               what is due and whether anything still reads it

The rule the whole thing exists to enforce: **never remove in the release you
deprecated in.** A deprecation a consumer has not had a chance to act on is not
a deprecation, it is a removal with an apology attached.

The ledger — deprecations.json
------------------------------
    {
      "schema": "design-system-versioning/deprecations@1",
      "deprecations": [{
        "name":        "--fg-subtle",      the thing going away
        "kind":        "token",            token|socket|component|variant|
                                           state|prop|theme|repoint
        "since":       "2.1.0",            version that announced it
        "removal":     "3.0.0",            version that deletes it
        "replacement": "--fg-faint",       "" when there is no one-to-one
        "codemod":     "mechanical",       mechanical|manual|none
        "reason":      "…",                why, in a consumer's terms
        "notes":       "…",                what a codemod cannot do for them
        "recorded":    "2026-09-17",
        "status":      "active",           active|removed
        "marker":      "styles/tokens.css:278",
        "usage":       {…}                 written by `scan --record`
      }]
    }

Usage
-----
    python -m scripts.deprecate add --name --fg-subtle --kind token \\
        --since 2.1.0 --removal 3.0.0 --replacement --fg-faint \\
        --reason "…" --source styles/tokens.css --mapping build/mapping.json

    python -m scripts.deprecate status --version 3.0.0
    python -m scripts.deprecate scan ../client-a ../client-b --record
    python -m scripts.deprecate mapping -o build/mapping.json
    python -m scripts.deprecate retire --name --fg-subtle

Exit codes: 0 fine · 1 something due for removal is still in use (or --scan
with --fail-on-usage found hits) · 2 bad invocation.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Sequence, Tuple

LEDGER_SCHEMA = "design-system-versioning/deprecations@1"
MAPPING_SCHEMA = "design-token-migration/mapping@1"


def bail(message: str) -> "SystemExit":
    """Exit 2 — bad invocation — with the message on stderr where it belongs.

    A bare `raise SystemExit("…")` exits 1, which is the code this tool reserves
    for "the gate fired". A caller in CI cannot tell a real failure from a typo
    in a path if both exit 1.
    """
    print(message, file=sys.stderr)
    return SystemExit(2)

KINDS = ("token", "socket", "component", "variant", "state", "prop", "theme",
         "repoint")
CODEMOD_MODES = ("auto", "mechanical", "manual", "none")
STATUSES = ("active", "removed")


# ===========================================================================
# 1. THE MARKER
#
# One line, one grammar, both languages. A deprecation that exists only in a
# changelog is invisible at the call site, and the call site is where the
# decision to keep using it gets made.
# ===========================================================================

MARKER_RE = re.compile(
    r"@deprecated\s+(?P<name>\S+)\s+since=(?P<since>\S+)"
    r"(?:\s+use=(?P<use>\S+))?(?:\s+remove=(?P<remove>\S+))?"
    r"(?:\s+codemod=(?P<codemod>\S+))?")


def marker_text(entry: Dict[str, Any]) -> str:
    parts = [f"@deprecated {entry['name']}", f"since={entry['since']}"]
    if entry.get("replacement"):
        parts.append(f"use={entry['replacement']}")
    if entry.get("removal"):
        parts.append(f"remove={entry['removal']}")
    parts.append(f"codemod={rule_id(entry)}")
    line = " ".join(parts)
    if entry.get("reason"):
        line += f" — {entry['reason']}"
    return line


def rule_id(entry: Dict[str, Any]) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", str(entry["name"]).lower()).strip("-")
    return f"dep-{slug}"


# ===========================================================================
# 2. THE LEDGER
# ===========================================================================


def empty_ledger() -> Dict[str, Any]:
    return {"schema": LEDGER_SCHEMA, "deprecations": []}


def load_ledger(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return empty_ledger()
    try:
        data = json.loads(path.read_bytes())
    except (OSError, json.JSONDecodeError) as exc:
        raise bail(f"deprecate: {path} is not readable JSON ({exc}). "
                         f"Fix it or move it aside; this script will not "
                         f"overwrite a file it cannot read.")
    if str(data.get("schema", "")).split("@")[0] != LEDGER_SCHEMA.split("@")[0]:
        raise bail(f"deprecate: {path} is not a deprecation ledger "
                         f"(schema={data.get('schema')!r}).")
    data.setdefault("deprecations", [])
    return data


def save_ledger(path: Path, data: Dict[str, Any]) -> None:
    data["deprecations"].sort(key=lambda d: (str(d.get("kind")), str(d.get("name"))))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")


def find_entry(ledger: Dict[str, Any], name: str) -> Optional[Dict[str, Any]]:
    for entry in ledger["deprecations"]:
        if entry.get("name") == name:
            return entry
    return None


# ===========================================================================
# 3. VERSIONS
# ===========================================================================

SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:[-+].*)?$")


def parse_version(raw: str, what: str) -> Tuple[int, int, int]:
    m = SEMVER.match(raw.strip().lstrip("v"))
    if not m:
        raise bail(f"deprecate: {what} {raw!r} is not semver "
                         f"(expected MAJOR.MINOR.PATCH).")
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)))


def check_window(since: str, removal: str) -> Optional[str]:
    """The one rule this script refuses to let you break silently."""
    a, b = parse_version(since, "--since"), parse_version(removal, "--removal")
    if b <= a:
        return (f"--removal {removal} is not after --since {since}. Removing in "
                f"the release that announced it is not a deprecation, it is a "
                f"removal with an apology attached.")
    if b[0] == a[0] and b[1] == a[1]:
        return (f"{since} -> {removal} is a patch apart. A consumer on a "
                f"quarterly upgrade cadence will meet the removal and the "
                f"announcement in the same diff. Give them a minor version.")
    return None


# ===========================================================================
# 4. MARKER INJECTION
#
# Idempotent by construction: an existing marker for the same name on the line
# above is REPLACED, never stacked. Re-running `add` after editing the reason is
# a normal thing to do and must not litter the file.
# ===========================================================================

CSS_EXT = {".css", ".scss", ".pcss"}
TS_EXT = {".ts", ".tsx", ".js", ".jsx", ".mjs"}


@dataclass
class Injection:
    path: str
    line: int
    action: str          # inserted | replaced | already-current | not-found


def inject_marker(path: Path, entry: Dict[str, Any]) -> Injection:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    target = locate(lines, entry, path.suffix.lower())
    if target is None:
        return Injection(str(path), 0, "not-found")
    idx, indent = target
    css = path.suffix.lower() in CSS_EXT
    body = marker_text(entry)
    line = (f"{indent}/* {body} */\n" if css else f"{indent}/** {body} */\n")
    prev = lines[idx - 1] if idx > 0 else ""
    m = MARKER_RE.search(prev)
    if m and m.group("name") == entry["name"]:
        if prev == line:
            return Injection(str(path), idx + 1, "already-current")
        lines[idx - 1] = line
        path.write_text("".join(lines), encoding="utf-8")
        return Injection(str(path), idx + 1, "replaced")
    lines.insert(idx, line)
    path.write_text("".join(lines), encoding="utf-8")
    return Injection(str(path), idx + 2, "inserted")


def locate(lines: Sequence[str], entry: Dict[str, Any],
           suffix: str) -> Optional[Tuple[int, str]]:
    """Index of the line that declares `name`, plus its indent."""
    name = str(entry["name"])
    kind = str(entry.get("kind"))
    pats: List[re.Pattern] = []
    if suffix in CSS_EXT:
        if name.startswith("--"):
            pats.append(re.compile(r"^(\s*)" + re.escape(name) + r"\s*:"))
        else:
            cls = name if name.startswith(".") else "." + name
            pats.append(re.compile(r"^(\s*)" + re.escape(cls) + r"\b[^{]*\{"))
            pats.append(re.compile(r'^(\s*)\[data-variant[~^|$*]?=["\']'
                                   + re.escape(name) + r'["\']'))
    else:
        ident = name.lstrip("-")
        pats.append(re.compile(r"^(\s*)(?:export\s+)?(?:default\s+)?"
                               r"(?:function|const|class|interface|type)\s+"
                               + re.escape(ident) + r"\b"))
        if kind == "prop":
            pats.append(re.compile(r"^(\s*)" + re.escape(ident) + r"\??\s*:"))
    for pat in pats:
        for i, raw in enumerate(lines):
            m = pat.match(raw)
            if m:
                return (i, m.group(1))
    return None


# ===========================================================================
# 5. THE CODEMOD MAPPING
#
# Emitted in apply_codemod.py's format, because a second codemod engine in one
# suite is a second set of bugs about comments, strings and url().
#
# WHICH SCOPE, AND WHY
# --------------------
# apply_codemod's per-slot pass deliberately SKIPS any slot that already
# contains `var(--` — its job is literals -> tokens, and rewriting inside an
# existing var() is not that job. So a token rename goes through the
# DECLARATION scope, one rule per property, where the whole declaration is
# replaced. That is the door the engine leaves open, and it is enough for the
# ordinary case: `color: var(--old);` -> `color: var(--fg-faint);`.
#
# Shadows are the exception in the other direction: box-shadow is matched as a
# whole VALUE with no var() guard, so an elevation role renames through the
# value scope cleanly.
#
# What it does NOT reach, honestly:
#   --x: var(--old)          a Tier-3 socket default. apply_codemod skips custom
#                            properties on purpose; they are the system's own
#                            layer, not a consumer's call site.
#   border: 1px solid var(--old)   a shorthand. The rule would have to enumerate
#                            every surrounding text.
# `scan` finds every one of those and labels it `manual`, which is the honest
# answer to "is the codemod enough".
# ===========================================================================

COLOR_PROPS = ["color", "fill", "stroke", "caret-color", "text-decoration-color",
               "text-emphasis-color", "background-color", "border-color",
               "outline-color", "accent-color", "column-rule-color"]
BG_PROPS = ["background-color", "background", "fill", "accent-color",
            "border-color", "color"]
BORDER_PROPS = ["border-color", "border-top-color", "border-right-color",
                "border-bottom-color", "border-left-color", "border-block-color",
                "border-inline-color", "outline-color", "column-rule-color",
                "stroke"]
GAP_PROPS = ["gap", "row-gap", "column-gap", "margin", "margin-block",
             "margin-inline", "margin-top", "margin-right", "margin-bottom",
             "margin-left", "margin-block-start", "margin-block-end",
             "margin-inline-start", "margin-inline-end"]
PAD_PROPS = ["padding", "padding-inline", "padding-block", "padding-top",
             "padding-right", "padding-bottom", "padding-left",
             "padding-inline-start", "padding-inline-end",
             "padding-block-start", "padding-block-end"]
RADIUS_PROPS = ["border-radius", "border-top-left-radius",
                "border-top-right-radius", "border-bottom-left-radius",
                "border-bottom-right-radius"]
SIZE_PROPS = ["width", "height", "min-width", "max-width", "min-height",
              "max-height", "flex-basis", "inline-size", "block-size"]

#: prefix -> (apply_codemod `kind`, prop_class, properties). The `kind` names
#: are apply_codemod's own, so `--kind color` filters these the same way it
#: filters a migration's rules.
PREFIX_RULES: Tuple[Tuple[str, str, str, List[str]], ...] = (
    ("--fg-", "color", "fg", COLOR_PROPS),
    ("--bg-", "color", "bg", BG_PROPS),
    ("--border-", "color", "border", BORDER_PROPS),
    ("--gap-", "spacing", "gap", GAP_PROPS),
    ("--pad-", "spacing", "pad-inline", PAD_PROPS),
    ("--gutter-", "spacing", "pad-inline", PAD_PROPS + GAP_PROPS),
    ("--space-", "spacing", "gap", GAP_PROPS + PAD_PROPS),
    ("--radius-", "radius", "radius", RADIUS_PROPS),
    ("--stroke-", "stroke", "stroke", ["border-width", "border-top-width",
                                       "border-bottom-width", "outline-width"]),
    ("--type-", "type", "font-size", ["font"]),
    ("--text-", "type", "font-size", ["font-size"]),
    ("--tracking-", "tracking", "tracking", ["letter-spacing"]),
    ("--leading-", "type", "leading", ["line-height"]),
    ("--weight-", "type", "weight", ["font-weight"]),
    ("--z-", "z-index", "z-index", ["z-index"]),
    ("--dur-", "duration", "duration", ["transition-duration",
                                        "animation-duration"]),
    ("--ease-", "easing", "easing", ["transition-timing-function",
                                     "animation-timing-function"]),
    ("--measure-", "spacing", "size", SIZE_PROPS),
    ("--width-", "spacing", "size", SIZE_PROPS),
)
SHADOW_PREFIXES = ("--shadow-", "--elevation-")


def codemod_rules(entry: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], str]:
    """(rules, why-not) for one ledger entry."""
    name, repl = str(entry["name"]), str(entry.get("replacement") or "")
    kind = str(entry.get("kind"))
    base = rule_id(entry)
    note = (f"Deprecated in {entry.get('since')}, removed in "
            f"{entry.get('removal', 'a future major')}.")
    if str(entry.get("codemod")) in ("manual", "none"):
        return [], (f"the ledger marks this one `{entry.get('codemod')}` — "
                    f"{entry.get('notes') or 'no mechanical rule exists'}")
    if not repl:
        return [], ("no replacement, so there is nothing to rewrite TO. A "
                    "removal with no successor is a design decision each "
                    "consumer makes for themselves.")
    if kind in ("component", "variant", "state"):
        # className strings only: the tailwind scope is the one place
        # apply_codemod rewrites an identifier rather than a value.
        return ([{
            "id": base, "kind": "color", "scope": "tailwind",
            "match": [name.lstrip(".")], "replacement": repl.lstrip("."),
            "token": repl, "prop_classes": [], "props": [],
            "occurrences": 0, "delta_px": None, "confidence": "review",
            "note": note + " className strings only — the import, the "
                           "stylesheet and any descendant selector are yours.",
        }], "")
    if kind in ("prop", "theme", "repoint"):
        return [], (f"a {kind} change is not a value substitution; there is "
                    f"nothing for a value codemod to match.")
    if not name.startswith("--"):
        return [], "only custom properties have a mechanical CSS rewrite here."

    if any(name.startswith(p) for p in SHADOW_PREFIXES):
        return ([{
            "id": base, "kind": "shadow", "scope": "value",
            "match": [f"var({name})"], "replacement": f"var({repl})",
            "token": repl, "prop_classes": ["shadow"],
            "props": ["box-shadow", "text-shadow"],
            "occurrences": 0, "delta_px": None, "confidence": "exact",
            "note": note,
        }], "")

    match = None
    for prefix, ck, klass, props in PREFIX_RULES:
        if name.startswith(prefix):
            match = (ck, klass, props)
            break
    if match is None:
        match = ("color", "", COLOR_PROPS + GAP_PROPS + PAD_PROPS)
    ck, klass, props = match
    rules = []
    for prop in props:
        rules.append({
            "id": f"{base}-{prop}", "kind": ck, "scope": "declaration",
            "match": [f"var({name})"], "replacement": f"{prop}: var({repl})",
            "token": repl, "prop_classes": [klass], "props": [prop],
            "occurrences": 0, "delta_px": None, "confidence": "exact",
            "note": note,
        })
    return rules, ""


def build_mapping(ledger: Dict[str, Any], ledger_path: Path
                  ) -> Tuple[Dict[str, Any], List[Tuple[str, str]]]:
    rules: List[Dict[str, Any]] = []
    manual: List[Tuple[str, str]] = []
    for entry in ledger["deprecations"]:
        if str(entry.get("status", "active")) != "active":
            continue
        got, why = codemod_rules(entry)
        rules.extend(got)
        if why:
            manual.append((str(entry["name"]), why))
    mapping = {
        "schema": MAPPING_SCHEMA,
        "generated_from": str(ledger_path),
        "token_file": "tokens.css",
        "settings": {"generator": "design-system-versioning/deprecate.py"},
        "rules": rules,
        "unmapped": [
            {"kind": "deprecation", "value": name, "occurrences": 0,
             "where": [], "reason": why,
             "recommendation": "Handle this one by hand; `deprecate scan` "
                               "lists every call site."}
            for name, why in manual
        ],
    }
    return mapping, manual


# ===========================================================================
# 6. THE SCAN
#
# "Is it safe to remove?" answered with a count, per consumer, rather than with
# a feeling. A deprecation window that expires on the calendar rather than on
# the evidence is how a consumer who never upgraded gets broken on schedule.
# ===========================================================================

SKIP_DIRS = {"node_modules", ".git", "dist", "build", "__pycache__", ".next",
             "out", "coverage", ".venv", "vendor"}
SCAN_EXT = CSS_EXT | TS_EXT | {".html", ".vue", ".svelte", ".astro", ".md",
                               ".mdx", ".json"}
CUSTOM_PROP_DECL = re.compile(r"^\s*--[\w-]+\s*:")

@dataclass
class Hit:
    consumer: str
    file: str
    line: int
    text: str
    verdict: str        # codemod | manual
    why: str = ""


def covered_props(name: str) -> List[str]:
    if any(name.startswith(p) for p in SHADOW_PREFIXES):
        return ["box-shadow", "text-shadow"]
    for prefix, _ck, _klass, props in PREFIX_RULES:
        if name.startswith(prefix):
            return props
    return []


def iter_files(root: Path) -> Iterator[Path]:
    if root.is_file():
        yield root
        return
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        for f in sorted(files):
            p = Path(base) / f
            if p.suffix.lower() in SCAN_EXT:
                yield p


def scan_one(root: Path, entry: Dict[str, Any]) -> List[Hit]:
    name = str(entry["name"])
    consumer = root.name or str(root)
    if name.startswith("--"):
        needle = re.compile(r"var\(\s*" + re.escape(name) + r"\s*[,)]")
        decl = re.compile(r"^\s*" + re.escape(name) + r"\s*:")
    else:
        needle = re.compile(r"\b" + re.escape(name.lstrip(".")) + r"\b")
        decl = None
    props = covered_props(name)
    hits: List[Hit] = []
    for path in iter_files(root):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if name not in text:
            continue
        is_css = path.suffix.lower() in CSS_EXT
        for i, raw in enumerate(text.splitlines(), 1):
            if not needle.search(raw):
                continue
            # Each declaration on the line, so `.meta { color: var(--x); }`
            # reads as the declaration it is, however the rule is wrapped. A
            # quoted string is text: its `;` splits nothing, and a token named
            # inside it is not a use.
            pieces = [raw]
            if is_css:
                masked = re.sub(r"\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'",
                                lambda q: q.group(0)[0] + " " * (len(q.group(0)) - 2)
                                + q.group(0)[-1], raw)
                bounds = [-1] + [s.start() for s in re.finditer(r"[{};]", masked)] + [len(raw)]
                pieces = [raw[a + 1:b] for a, b in zip(bounds, bounds[1:])
                          if needle.search(masked[a + 1:b])]
            for piece in pieces:
                if decl is not None and decl.match(piece):
                    continue            # the declaration itself, not a use
                verdict, why = classify_hit(piece, path, name, props)
                hits.append(Hit(consumer, str(path), i, raw.strip()[:110],
                                verdict, why))
    return hits


def classify_hit(raw: str, path: Path, name: str,
                 props: Sequence[str]) -> Tuple[str, str]:
    if path.suffix.lower() not in CSS_EXT:
        return ("codemod" if not name.startswith("--") else "manual",
                "" if not name.startswith("--") else
                "a token inside JS/markup — the codemod reads styled-components "
                "bodies and className strings, nothing else")
    if CUSTOM_PROP_DECL.match(raw):
        return ("manual", "a custom-property declaration — apply_codemod skips "
                          "those on purpose; a Tier-3 socket default is the "
                          "system's own layer, so you re-point it by hand")
    m = re.match(r"^\s*([-\w]+)\s*:\s*(.+?)\s*;?\s*$", raw)
    if not m:
        return ("manual", "not a plain declaration")
    prop, value = m.group(1), m.group(2)
    # apply_codemod rewrites up to `!important` and keeps it.
    value = re.sub(r"\s*!important\s*$", "", value, flags=re.IGNORECASE)
    if prop not in props:
        return ("manual", f"`{prop}` is not in the rule's property list")
    if value.strip() != f"var({name})":
        return ("manual", "the token is part of a longer value (a shorthand); "
                          "the rule matches the whole declaration value")
    return ("codemod", "")


# ===========================================================================
# 7. COMMANDS
# ===========================================================================


def cmd_add(args: argparse.Namespace) -> int:
    ledger_path = Path(args.ledger)
    ledger = load_ledger(ledger_path)
    if args.kind not in KINDS:
        raise bail(f"deprecate: --kind must be one of {', '.join(KINDS)}")
    problem = check_window(args.since, args.removal)
    if problem and not args.force:
        print(f"deprecate: {problem}\n"
              f"Pass --force if you really mean it, and write the reason into "
              f"--notes so the next person knows it was deliberate.",
              file=sys.stderr)
        return 2
    codemod = args.codemod
    if codemod == "auto":
        codemod = "mechanical" if args.replacement else "none"

    entry: Dict[str, Any] = {
        "name": args.name, "kind": args.kind, "since": args.since,
        "removal": args.removal, "replacement": args.replacement or "",
        "codemod": codemod, "reason": args.reason or "",
        "notes": args.notes or "",
        "recorded": args.date or _dt.date.today().isoformat(),
        "status": "active", "marker": "", "usage": {},
    }
    existing = find_entry(ledger, args.name)
    if existing:
        entry["recorded"] = existing.get("recorded", entry["recorded"])
        entry["usage"] = existing.get("usage", {})
        ledger["deprecations"].remove(existing)
    ledger["deprecations"].append(entry)

    injections: List[Injection] = []
    for raw in args.source or []:
        p = Path(raw)
        if not p.exists():
            print(f"deprecate: no such source file: {p}", file=sys.stderr)
            return 2
        if args.dry_run:
            injections.append(Injection(str(p), 0, "dry-run"))
            continue
        injections.append(inject_marker(p, entry))
    placed = [i for i in injections if i.action in ("inserted", "replaced",
                                                    "already-current")]
    if placed:
        entry["marker"] = f"{placed[0].path}:{placed[0].line}"

    rules, why = codemod_rules(entry)
    mapping_written = ""
    if args.mapping and not args.dry_run:
        mapping, _manual = build_mapping(ledger, ledger_path)
        Path(args.mapping).parent.mkdir(parents=True, exist_ok=True)
        Path(args.mapping).write_text(
            json.dumps(mapping, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8")
        mapping_written = args.mapping

    if not args.dry_run:
        save_ledger(ledger_path, ledger)

    print(f"{'DRY RUN — nothing written' if args.dry_run else 'recorded'}: "
          f"{entry['name']} ({entry['kind']})")
    print(f"  announced   {entry['since']}")
    print(f"  removed in  {entry['removal']}")
    print(f"  replacement {entry['replacement'] or '(none — see notes)'}")
    print(f"  ledger      {ledger_path}")
    for inj in injections:
        verb = {"inserted": "marker inserted", "replaced": "marker updated",
                "already-current": "marker already current",
                "dry-run": "marker would be injected",
                "not-found": "MARKER NOT PLACED"}[inj.action]
        where = f"{inj.path}:{inj.line}" if inj.line else inj.path
        print(f"  {verb:<26}{where}")
        if inj.action == "not-found":
            print(f"      could not find a declaration of {entry['name']} in "
                  f"that file. Add the marker by hand:")
            print(f"      /* {marker_text(entry)} */")
    if rules:
        print(f"  codemod     {len(rules)} rule(s)"
              + (f" -> {mapping_written}" if mapping_written else
                 " (pass --mapping FILE to write them)"))
    else:
        print(f"  codemod     none — {why}")
    if not args.dry_run:
        print()
        print("Next: ship this release with BOTH names working. The shim is the "
              "point; see references/deprecation.md §4.")
    return 0


def cmd_mapping(args: argparse.Namespace) -> int:
    ledger_path = Path(args.ledger)
    ledger = load_ledger(ledger_path)
    mapping, manual = build_mapping(ledger, ledger_path)
    text = json.dumps(mapping, indent=2, ensure_ascii=False) + "\n"
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"wrote {args.out} — {len(mapping['rules'])} rule(s), "
              f"{len(manual)} deprecation(s) with no mechanical rule",
              file=sys.stderr)
        for name, why in manual:
            print(f"  manual: {name} — {why}", file=sys.stderr)
    else:
        sys.stdout.write(text)
    return 0


def cmd_retire(args: argparse.Namespace) -> int:
    ledger_path = Path(args.ledger)
    ledger = load_ledger(ledger_path)
    entry = find_entry(ledger, args.name)
    if entry is None:
        print(f"deprecate: {args.name} is not in {ledger_path}.", file=sys.stderr)
        return 2
    usage = entry.get("usage") or {}
    if not usage and not args.force:
        print(f"deprecate: {args.name} has never been scanned. A removal date is "
              f"a plan, not evidence. Run `deprecate scan <consumer repos> --record` "
              f"first, or pass --force if you have decided to retire it without "
              f"evidence.", file=sys.stderr)
        return 1
    if usage.get("total") and not args.force:
        print(f"deprecate: {args.name} was last seen {usage['total']} time(s) in "
              f"{len([c for c, n in (usage.get('consumers') or {}).items() if n])} "
              f"consumer(s) on {usage.get('scanned')}. Re-scan, or pass --force "
              f"if you have decided to break them on purpose.", file=sys.stderr)
        return 1
    entry["status"] = "removed"
    entry["retired"] = args.date or _dt.date.today().isoformat()
    save_ledger(ledger_path, ledger)
    print(f"retired {args.name} — it no longer emits a codemod rule. Delete the "
          f"declaration and the marker in the same commit.")
    return 0


def cmd_scan(args: argparse.Namespace) -> int:
    ledger_path = Path(args.ledger)
    ledger = load_ledger(ledger_path)
    active = [e for e in ledger["deprecations"]
              if str(e.get("status", "active")) == "active"]
    if not active:
        print(f"deprecate: no active deprecations in {ledger_path}; nothing to "
              f"scan for.")
        return 0
    roots = [Path(r) for r in args.paths]
    missing = [r for r in roots if not r.exists()]
    if missing:
        print(f"deprecate: no such path: {', '.join(str(m) for m in missing)}",
              file=sys.stderr)
        return 2

    results: Dict[str, Dict[str, List[Hit]]] = {}
    for entry in active:
        per_consumer: Dict[str, List[Hit]] = {}
        for root in roots:
            per_consumer[root.name or str(root)] = scan_one(root, entry)
        results[str(entry["name"])] = per_consumer

    if args.record:
        stamp = args.date or _dt.date.today().isoformat()
        for entry in active:
            per = results[str(entry["name"])]
            entry["usage"] = {
                "scanned": stamp,
                "total": sum(len(h) for h in per.values()),
                "consumers": {c: len(h) for c, h in sorted(per.items())},
                "roots": [str(r) for r in roots],
            }
        save_ledger(ledger_path, ledger)

    if args.format == "json":
        payload = {
            "schema": "design-system-versioning/scan@1",
            "ledger": str(ledger_path),
            "roots": [str(r) for r in roots],
            "results": {
                name: {c: [h.__dict__ for h in hits] for c, hits in per.items()}
                for name, per in results.items()
            },
        }
        sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    else:
        sys.stdout.write(render_scan(ledger_path, roots, active, results,
                                     args.limit))

    total = sum(len(h) for per in results.values() for h in per.values())
    return 1 if (total and args.fail_on_usage) else 0


def render_scan(ledger_path: Path, roots: Sequence[Path],
                active: Sequence[Dict[str, Any]],
                results: Dict[str, Dict[str, List[Hit]]], limit: int) -> str:
    out: List[str] = []
    out.append("DEPRECATION USAGE SCAN")
    out.append("=" * 24)
    out.append(f"  ledger     {ledger_path}   ({len(active)} active)")
    out.append(f"  consumers  {', '.join(str(r) for r in roots)}")
    out.append("")
    verdicts: List[str] = []
    for entry in sorted(active, key=lambda e: str(e["name"])):
        name = str(entry["name"])
        per = results[name]
        total = sum(len(h) for h in per.values())
        out.append(f"{name}   since {entry.get('since')} · removal "
                   f"{entry.get('removal')} · codemod {entry.get('codemod')}")
        for consumer in sorted(per):
            hits = per[consumer]
            if not hits:
                out.append(f"  {consumer:<24}  0 hits   clear")
                continue
            auto = sum(1 for h in hits if h.verdict == "codemod")
            out.append(f"  {consumer:<24}  {len(hits)} hit(s)   "
                       f"{auto} codemod · {len(hits) - auto} manual")
            for h in hits[:limit]:
                rel = h.file
                out.append(f"      {rel}:{h.line}  [{h.verdict}]")
                out.append(f"          {h.text}")
                if h.why:
                    out.append(f"          why: {h.why}")
            if len(hits) > limit:
                out.append(f"      … and {len(hits) - limit} more "
                           f"(raise --limit to see them)")
        dirty = [c for c, h in per.items() if h]
        if total:
            manual = sum(1 for h in sum(per.values(), []) if h.verdict == "manual")
            verdicts.append(
                f"  {name:<22} NOT SAFE to remove — {total} hit(s) in "
                f"{len(dirty)} of {len(per)} consumer(s)"
                + (f", {manual} of them need a human" if manual else
                   ", all of them mechanical"))
        else:
            verdicts.append(f"  {name:<22} safe to remove — 0 hits in "
                            f"{len(per)} consumer(s) scanned")
        out.append("")
    out.append("VERDICT")
    out.append("=" * 24)
    out.extend(verdicts)
    out.append("")
    out.append("  A clear scan is evidence about the repos you scanned, and "
               "nothing else. A consumer you did not clone is a consumer you "
               "did not check.")
    out.append("")
    return "\n".join(out)


def cmd_status(args: argparse.Namespace) -> int:
    ledger_path = Path(args.ledger)
    ledger = load_ledger(ledger_path)
    entries = ledger["deprecations"]
    if not entries:
        print(f"deprecate: {ledger_path} is empty. Nothing is deprecated, which "
              f"is either very good news or a ledger nobody writes to.")
        return 0
    target = parse_version(args.version, "--version") if args.version else None

    if args.format == "json":
        sys.stdout.write(json.dumps(
            {"schema": LEDGER_SCHEMA, "ledger": str(ledger_path),
             "version": args.version, "deprecations": entries},
            indent=2, ensure_ascii=False) + "\n")
        return 0

    out: List[str] = []
    out.append("DEPRECATION LEDGER")
    out.append("=" * 24)
    out.append(f"  {ledger_path}   {len(entries)} record(s)")
    if args.version:
        out.append(f"  evaluating against version {args.version}")
    out.append("")
    head = (f"  {'name':<24}{'kind':<10}{'since':<9}{'removal':<9}"
            f"{'codemod':<11}{'status':<9}usage")
    out.append(head)
    out.append("  " + "-" * (len(head) - 2))
    due: List[Dict[str, Any]] = []
    blocked: List[Dict[str, Any]] = []
    for entry in sorted(entries, key=lambda e: (str(e.get("kind")),
                                                str(e.get("name")))):
        usage = entry.get("usage") or {}
        usage_txt = ("not scanned" if not usage else
                     f"{usage.get('total', 0)} hit(s) @ {usage.get('scanned')}")
        out.append(f"  {str(entry.get('name')):<24}{str(entry.get('kind')):<10}"
                   f"{str(entry.get('since')):<9}{str(entry.get('removal')):<9}"
                   f"{str(entry.get('codemod')):<11}"
                   f"{str(entry.get('status', 'active')):<9}{usage_txt}")
        if str(entry.get("status", "active")) != "active":
            continue
        if target and parse_version(str(entry.get("removal", "999.0.0")),
                                    "removal") <= target:
            due.append(entry)
            if (entry.get("usage") or {}).get("total"):
                blocked.append(entry)
    out.append("")

    if target:
        out.append(f"DUE FOR REMOVAL at {args.version}")
        out.append("=" * 24)
        if not due:
            out.append("  nothing — every active deprecation has a later removal "
                       "target.")
        for entry in due:
            usage = entry.get("usage") or {}
            if not usage:
                out.append(f"  {entry['name']:<24} due, but NEVER SCANNED. "
                           f"Run `deprecate scan <consumer repos> --record` "
                           f"before you delete anything.")
            elif usage.get("total"):
                who = ", ".join(c for c, n in (usage.get("consumers") or {}).items()
                                if n) or "(unknown)"
                out.append(f"  {entry['name']:<24} due, but STILL IN USE — "
                           f"{usage['total']} hit(s) in {who} "
                           f"(scanned {usage.get('scanned')})")
            else:
                out.append(f"  {entry['name']:<24} due and clear — 0 hits at "
                           f"{usage.get('scanned')}. Delete it, its marker and "
                           f"its ledger rule in one commit.")
        out.append("")

    stale = [e for e in entries if str(e.get("status", "active")) == "active"
             and not (e.get("usage") or {})]
    if stale:
        out.append("NEVER SCANNED")
        out.append("=" * 24)
        out.append("  " + ", ".join(str(e["name"]) for e in stale))
        out.append("  A removal date is a plan. A scan is evidence. Do not "
                   "delete on the strength of the plan alone.")
        out.append("")
    sys.stdout.write("\n".join(out) + "\n")
    return 1 if blocked else 0


# ===========================================================================
# 8. CLI
# ===========================================================================


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="python -m scripts.deprecate",
        description="Record, mark, codemod and track a design-system "
                    "deprecation, so a removal is a scheduled event rather "
                    "than an incident.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python -m scripts.deprecate add --name --fg-subtle --kind token \\
      --since 2.1.0 --removal 3.0.0 --replacement --fg-faint \\
      --reason "…" --source styles/tokens.css --mapping build/mapping.json
  python -m scripts.deprecate scan ../client-a ../client-b --record
  python -m scripts.deprecate status --version 3.0.0
  python -m scripts.deprecate mapping -o build/mapping.json
  python -m scripts.deprecate retire --name --fg-subtle
""")
    ap.add_argument("--ledger", default="deprecations.json", metavar="FILE",
                    help="the ledger (default: ./deprecations.json)")
    sub = ap.add_subparsers(dest="command", required=True)

    a = sub.add_parser("add", help="record a deprecation and mark the source")
    a.add_argument("--name", required=True,
                   help="the token, socket, component, variant or prop going away")
    a.add_argument("--kind", required=True, choices=KINDS)
    a.add_argument("--since", required=True, metavar="X.Y.Z",
                   help="the version that announces it")
    a.add_argument("--removal", required=True, metavar="X.Y.Z",
                   help="the version that deletes it — must be later, and "
                        "should be at least a minor away")
    a.add_argument("--replacement", default="",
                   help="what to use instead; omit when there is no one-to-one")
    a.add_argument("--reason", default="",
                   help="why, written for a consumer, not for you")
    a.add_argument("--notes", default="",
                   help="what a codemod cannot do for them")
    a.add_argument("--codemod", choices=CODEMOD_MODES, default="auto",
                   help="auto: mechanical when a replacement exists (default)")
    a.add_argument("--source", action="append", metavar="FILE",
                   help="file to inject the marker into (repeatable)")
    a.add_argument("--mapping", metavar="FILE",
                   help="also write the whole ledger's mapping.json here")
    a.add_argument("--date", metavar="YYYY-MM-DD")
    a.add_argument("--force", action="store_true",
                   help="record it even when the removal window is too short")
    a.add_argument("--dry-run", action="store_true",
                   help="print what would happen; write nothing")
    a.set_defaults(func=cmd_add)

    s = sub.add_parser("status", help="what is pending, what is due, what is "
                                      "still in use")
    s.add_argument("--version", metavar="X.Y.Z",
                   help="evaluate removals against this version")
    s.add_argument("--format", choices=("report", "json"), default="report")
    s.set_defaults(func=cmd_status)

    sc = sub.add_parser("scan", help="count real usage across consumer repos")
    sc.add_argument("paths", nargs="+", metavar="REPO",
                    help="consumer repositories or directories")
    sc.add_argument("--record", action="store_true",
                    help="write the counts back into the ledger as evidence")
    sc.add_argument("--fail-on-usage", action="store_true",
                    help="exit 1 if anything is still in use")
    sc.add_argument("--limit", type=int, default=6, metavar="N",
                    help="call sites printed per consumer (default 6)")
    sc.add_argument("--format", choices=("report", "json"), default="report")
    sc.add_argument("--date", metavar="YYYY-MM-DD")
    sc.set_defaults(func=cmd_scan)

    m = sub.add_parser("mapping", help="emit the codemod mapping for the ledger")
    m.add_argument("-o", "--out", metavar="FILE")
    m.set_defaults(func=cmd_mapping)

    r = sub.add_parser("retire", help="mark a deprecation as removed")
    r.add_argument("--name", required=True)
    r.add_argument("--force", action="store_true",
                   help="retire it even though the last scan found usage")
    r.add_argument("--date", metavar="YYYY-MM-DD")
    r.set_defaults(func=cmd_retire)
    return ap


#: Options whose value is routinely a CSS custom property, i.e. a string that
#: begins with two dashes and that argparse will otherwise read as a flag.
DASH_VALUE_OPTS = ("--name", "--replacement")


def normalize_argv(argv: Sequence[str], known: Sequence[str]) -> List[str]:
    """Let `--name --fg-subtle` mean what everybody means by it.

    Every subject this script takes is a CSS custom property, so the common
    case is an option value starting with `--`. argparse reads that as another
    flag and dies with "expected one argument", which is a papercut on literally
    every invocation. Joining the pair with `=` — and only when the follower is
    not itself a known flag — removes it without making `--name --kind` silently
    do something absurd.
    """
    out: List[str] = []
    i = 0
    known_set = set(known)
    while i < len(argv):
        tok = argv[i]
        if (tok in DASH_VALUE_OPTS and i + 1 < len(argv)
                and argv[i + 1].startswith("--") and "=" not in argv[i + 1]
                and argv[i + 1] not in known_set):
            out.append(f"{tok}={argv[i + 1]}")
            i += 2
            continue
        out.append(tok)
        i += 1
    return out


def known_flags(ap: argparse.ArgumentParser) -> List[str]:
    flags: List[str] = []
    for action in ap._actions:                      # noqa: SLF001 — argparse API
        flags.extend(action.option_strings)
        if isinstance(action, argparse._SubParsersAction):   # noqa: SLF001
            for sub in action.choices.values():
                flags.extend(known_flags(sub))
    return flags


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = build_parser()
    raw = list(sys.argv[1:] if argv is None else argv)
    args = ap.parse_args(normalize_argv(raw, known_flags(ap)))
    return int(args.func(args))


if __name__ == "__main__":
    # A Windows pipe (git hook, CI, `> file`) defaults to the ANSI code page,
    # where printing →, Δ or ✓ raises UnicodeEncodeError. Consoles and
    # Claude Code already use UTF-8 and are left alone.
    for _stream in (sys.stdout, sys.stderr):
        if getattr(_stream, "encoding", "utf-8").lower() not in ("utf-8", "utf8"):
            _stream.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
