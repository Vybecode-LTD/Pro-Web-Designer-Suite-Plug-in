#!/usr/bin/env python3
"""
brief_to_log.py — a message brief's choices into the deck's decision log.

`assets/MESSAGE_BRIEF.md` records what a page argues and why: the positioning,
the claim, the assumptions it rests on. client-presentation-builder's
`assets/DECISION_LOG.md` is what its deck reads. This carries the one into the
other, so the positioning is argued in the review as a decision and what was
only assumed is asked, not presented:

  1. Positioning statement   a decision: the sentence is the choice, the first
                             answers the specificity test rewrote are the
                             options it beat, and who it is not for its cost
  3. Message hierarchy       a decision: the claim, its supports' proofs as evidence
  6. Assumptions             one open question each
  UNKNOWN in 0. or 2.        one open question each

What the brief does not say is left as a `<placeholder>`, which the deck lists
as a gap to fix before the meeting. Nothing is filled in with a guess.

Usage
-----
    python -m scripts.brief_to_log MESSAGE_BRIEF.md                         # print the blocks
    python -m scripts.brief_to_log MESSAGE_BRIEF.md --into DECISION_LOG.md  # add them under ## Decisions

`--into` numbers the new blocks after the log's own, adds them at the end of its
`## Decisions` section, and leaves out one whose title the log already has, so
running it again adds nothing. The brief's worked example, from
`# Worked example` on, is not read.

Exit codes: 0 done · 1 the brief has nothing filled in to carry · 2 bad invocation.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Optional, Union

BOLD = re.compile(r"\*\*(.+?)\*\*")
GUIDANCE = re.compile(r"\*\([^)]*\)\*")                                # *(a guidance note)*
EMPHASIS = re.compile(r"(?<![*\w])\*([^*\n]+)\*(?![*\w])")
BLANK = re.compile(r"^[_\s]*$")
ROW = re.compile(r"^\|(.+)\|\s*$")


def refuse_overwrite(out: Optional[Union[str, Path]],
                     *inputs: Optional[Union[str, Path]]) -> Optional[str]:
    """The message a script prints, then exits 2 on, when `out` is one of its
    inputs; None when it is none of them (the owner's audit of 2026-10-14,
    class 5: V7, E9, G4). An existing pair is compared by file identity, which
    sees a link and a case-folded name; any other by its resolved path. `-`
    is stdin or stdout, never a file."""
    if not out or str(out) == "-":
        return None
    for given in inputs:
        if not given or str(given) == "-":
            continue
        a, b = Path(out), Path(given)
        try:
            same = os.path.samefile(a, b) if a.exists() and b.exists() else (
                os.path.normcase(os.path.realpath(a)) == os.path.normcase(os.path.realpath(b)))
        except OSError:
            same = False
        if same:
            return f"{out} is the input {given}: writing there would replace it. Choose another output."
    return None


def read_text(path: Path) -> str:
    raw = path.read_bytes()
    return raw.decode(json.detect_encoding(raw), errors="replace")


def clean(value: str) -> str:
    """A cell or a line with the template's guidance and the markup gone. A
    whole italic cell or line is guidance; an italic word inside a sentence
    is the writer's emphasis, and its words stay."""
    value = GUIDANCE.sub("", value)
    if re.fullmatch(r"\s*\*[^*\n]+\*\s*", value):
        return ""
    value = BOLD.sub(lambda m: m.group(1), value)
    value = EMPHASIS.sub(lambda m: m.group(1), value)
    return " ".join(value.replace("☐", " ").split()).strip(" .")


def sections(text: str) -> dict[str, str]:
    """The brief's `## N.` sections by number, the worked example left out."""
    text = re.split(r"^# Worked example", text, maxsplit=1, flags=re.M)[0]
    found = {}
    for m in re.finditer(r"^## (\d+)\.[^\n]*\n(.*?)(?=^## |\Z)", text, re.S | re.M):
        found[m.group(1)] = m.group(2)
    return found


def table(body: str) -> list[list[str]]:
    rows = []
    for line in body.splitlines():
        m = ROW.match(line.strip())
        if m and not re.match(r"^[\s|:-]+$", m.group(1)):
            rows.append([c.strip() for c in m.group(1).split("|")])
    return rows


def labelled(body: str) -> dict[str, str]:
    """A two-column `| **Label** | value |` table, by label."""
    return {clean(r[0]).lower(): r[1] for r in table(body) if len(r) >= 2 and r[0].startswith("**")}


def subsection(body: str, title: str) -> str:
    m = re.search(rf"^### {title}[^\n]*\n(.*?)(?=^### |\Z)", body, re.S | re.M | re.I)
    return m.group(1) if m else ""


def prose(body: str) -> str:
    """The text a person wrote under a heading: no guidance, no table, no rule."""
    lines = [clean(line) for line in body.splitlines()
             if line.strip() and not line.lstrip().startswith(("|", ">", "---", "#"))]
    return " ".join(line for line in lines if line)


def positioning(body: str) -> tuple[str, list[str], str]:
    """§1: the sentence, the first answers the test rewrote, who it is not for."""
    quote = " ".join(line.lstrip("> ").strip() for line in body.splitlines() if line.startswith(">"))
    blanks = BOLD.findall(quote)
    sentence = ""
    if len(blanks) >= 5 and not any(BLANK.match(b) for b in blanks[:5]):
        sentence = clean(quote)
    rejected = []
    for row in table(subsection(body, "The specificity test")):
        if len(row) >= 4 and row[0] not in ("Blank",):
            first, rewritten = clean(row[1]), clean(row[3])
            if first and rewritten and first.lower() != rewritten.lower():
                rejected.append(f'{row[0].lower()}: "{first}"')
    not_for = prose(subsection(body, "Who this is explicitly"))
    m = re.search(r"\*\*Not for:\*\*\s*(.+)", body)
    if m:
        not_for = clean(m.group(1))
    return sentence, rejected, not_for


def claim_and_proofs(body: str) -> tuple[str, list[str]]:
    """§3: the claim, and each support's proof."""
    m = re.search(r"\*\*Claim:\*\*\s*(.+)", body)
    if m:                                                          # the worked example's form, set in italics
        claim = clean(m.group(1).strip().strip("*"))
    else:                                                          # the template's: a quote under its heading
        part = subsection(body, "The claim")
        quote = " ".join(line.lstrip("> ").strip() for line in part.splitlines() if line.startswith(">"))
        claim = "" if BLANK.match(quote) else clean(quote)
    proofs = []
    for n in (1, 2, 3):
        rows = labelled(subsection(body, f"Support {n}"))
        proof = clean(rows.get("proof", ""))
        if proof:
            proofs.append(proof)
    rows = table(body)
    header = [clean(c).lower() for c in rows[0]] if rows else []
    if not proofs and "proof" in header:                           # one table with a Proof column
        i = header.index("proof")
        proofs = [clean(r[i]) for r in rows[1:] if len(r) > i and clean(r[i])]
    return claim, proofs


def assumptions(body: str) -> list[str]:
    """§6's numbered items that have text on their own line: the template's
    empty `1.` is not an assumption, nor the line after it."""
    return [clean(m.group(1)) for m in re.finditer(r"^[ \t]*\d+\.[ \t]*(\S.*)$", body, re.M) if clean(m.group(1))]


def unknowns(found: dict[str, str]) -> list[str]:
    """The labelled cells §0 and §2 mark UNKNOWN, as the brief asks."""
    return [clean(row[0]) for key in ("0", "2") for row in table(found.get(key, ""))
            if len(row) >= 2 and row[0].startswith("**") and clean(row[1]).upper() == "UNKNOWN"]


def field(name: str, value: str, placeholder: str) -> str:
    return f"**{name}:** {value or f'<{placeholder}>'}"


def blocks(brief: str) -> list[tuple[str, str]]:
    """(title, block body) for each decision and open question the brief holds."""
    found = sections(brief)
    context = labelled(found.get("0", ""))
    traffic = clean(next((v for k, v in context.items() if k.startswith("traffic source")), ""))
    proof_today = clean(next((v for k, v in context.items() if k.startswith("proof")), ""))
    out = []
    sentence, rejected, not_for = positioning(found.get("1", ""))
    if sentence:
        out.append(("Positioning: who the page is for, and what it replaces", "\n".join((
            "**Status:** decided", "**Audience:** all", "**Tags:** positioning",
            field("Constraint", f"The page continues what its traffic started: {traffic}" if traffic else "",
                  "what forced this audience: the traffic, the research"),
            field("Options", "; ".join(rejected), "the positioning you rejected"),
            field("Choice", sentence, "the positioning sentence"),
            field("Consequence", f"Not for: {not_for}" if not_for else "", "who this turns away"),
            field("Evidence", proof_today, "what proves it today")))))
    claim, proofs = claim_and_proofs(found.get("3", ""))
    if claim:
        out.append((f"The claim: {claim}", "\n".join((
            "**Status:** decided", "**Audience:** all", "**Tags:** positioning, copy",
            field("Constraint", "", "the objection or the proof that made this the claim"),
            field("Options", "", "the claim you did not make"),
            field("Choice", claim, "the claim"),
            field("Consequence", "", "what the page no longer says"),
            field("Evidence", "; ".join(proofs), "each support's proof")))))
    for text in assumptions(found.get("6", "")):
        out.append((f"Assumed: {text}", "\n".join((
            "**Status:** open", "**Audience:** all", "**Tags:** assumption",
            f"**Say:** The page assumes that {text[0].lower() + text[1:]}; nothing has tested it yet. "
            "Do you know otherwise?"))))
    for label in unknowns(found):
        out.append((f"Unknown: {label}", "\n".join((
            "**Status:** open", "**Audience:** all", "**Tags:** assumption",
            f"**Say:** The brief has no answer for {label.lower()}. Who can give us one?"))))
    return out


def render(new: list[tuple[str, str]], first: int) -> str:
    return "".join(f"### D{first + i} — {title}\n\n{body}\n\n" for i, (title, body) in enumerate(new))


def into(log: str, new: list[tuple[str, str]]) -> tuple[str, int]:
    """The log with the new blocks at the end of its `## Decisions`, numbered
    after its own; a title it already has is left out."""
    m = re.search(r"^## Decisions?\b[^\n]*\n", log, re.M | re.I)
    if not m:
        raise ValueError("it has no `## Decisions` section")
    have = {t.strip().lower() for t in re.findall(r"^### D\d+\s*[—–-]\s*(.+)$", log, re.M)}
    new = [(t, b) for t, b in new if t.lower() not in have]
    numbers = [int(n) for n in re.findall(r"^### D(\d+)\b", log, re.M)]
    end = re.search(r"^## ", log[m.end():], re.M)
    at = m.end() + end.start() if end else len(log)
    head = log[:at].rstrip("\n")
    if head.endswith("---"):                                       # keep the template's rule after the blocks
        head, rule = head[:-3].rstrip("\n"), "---\n\n"
    else:
        rule = ""
    return head + "\n\n" + render(new, max(numbers, default=0) + 1) + rule + log[at:], len(new)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Carry a message brief's positioning and claim into a decision log as decisions, "
                    "and its assumptions and unknowns as open questions.")
    ap.add_argument("brief", help="the filled-in MESSAGE_BRIEF.md")
    ap.add_argument("--into", metavar="LOG", help="a DECISION_LOG.md to add the blocks to, in place")
    args = ap.parse_args(argv)

    brief = Path(args.brief)
    if not brief.is_file():
        print(f"brief_to_log: no such file: {brief}", file=sys.stderr)
        return 2
    refused = refuse_overwrite(args.into, brief)
    if refused:
        print(f"brief_to_log: {refused}", file=sys.stderr)
        return 2
    new = blocks(read_text(brief))
    if not new:
        print("brief_to_log: the brief has no positioning, claim, assumption or UNKNOWN filled in to carry",
              file=sys.stderr)
        return 1
    if not args.into:
        sys.stdout.write(render(new, 1))
        return 0
    log = Path(args.into)
    if not log.is_file():
        print(f"brief_to_log: no such decision log: {log}", file=sys.stderr)
        return 2
    try:
        text, added = into(read_text(log), new)
    except ValueError as exc:
        print(f"brief_to_log: {log}: {exc}", file=sys.stderr)
        return 2
    log.write_text(text, encoding="utf-8", newline="\n")
    print(f"brief_to_log: added {added} block(s) to {log}"
          + (f"; {len(new) - added} were there already" if added < len(new) else ""))
    return 0


if __name__ == "__main__":
    # A Windows pipe (git hook, CI, `> file`) defaults to the ANSI code page,
    # where printing a dash writes cp1252 or raises. Consoles and Claude Code
    # already use UTF-8 and are left alone.
    for _stream in (sys.stdout, sys.stderr):
        if getattr(_stream, "encoding", "utf-8").lower() not in ("utf-8", "utf8"):
            _stream.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
