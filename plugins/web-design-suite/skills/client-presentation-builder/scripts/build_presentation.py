#!/usr/bin/env python3
"""
build_presentation.py — assemble a client deck out of evidence that already exists.

You are not presenting a design. You are presenting a set of decisions. This
script does not invent any of them: it reads the decision log you kept while
building, the JSON the suite's gates already produced, the defence sheet
``design-critique-gate`` already wrote, and a directory of screenshots — and
arranges them into a deck for one named audience.

Everything it emits is traceable. Every generated number carries a
``data-cite`` attribute naming the file and the JSON path it came from, and the
same map is embedded in the deck as ``#deck-provenance`` so a reviewer (or a
test) can verify that no figure was invented. Anything the inputs do not
contain becomes a **marked gap** — visible in ``--dry-run``, in the speaker
notes, and on the slide itself once presenter notes are toggled on — never a
plausible-sounding guess.

Two honesty rules are compiled in, not documented and hoped for:

  * A decision marked ``Status: coin-flip`` is NEVER dressed up as rationale.
    It is routed to the open-questions slide and presented as a question for
    the room. A designer who can say "that one is genuinely a coin flip, what
    do you prefer?" is believed about the decisions they do defend.
  * A number with no source in an input file is not printed. If the perf JSON
    is absent, the deck makes no speed claim and says so in the gap list.

USAGE
-----
    python -m scripts.build_presentation DECISION_LOG.md --dry-run
    python -m scripts.build_presentation DECISION_LOG.md \
        --audience client \
        --audit audit.json --perf perf.json --a11y a11y.json \
        --defence defence.md --screenshots shots/ \
        --out deck.html --notes notes.md

    # Prove the deck is on the system it is arguing for:
    python -m scripts.build_presentation DECISION_LOG.md --out deck.html \
        --emit-css build-css/
    python -m scripts.audit_design build-css/ --strict     # web-design-studio

INPUTS
------
    DECISION_LOG.md   assets/DECISION_LOG.md, filled in as the work happened.
    --audit FILE      `audit_design.py --json`   (a JSON list of findings)
    --perf FILE       `perf_audit.py --json`     ({findings, ledger, budget})
    --a11y FILE       axe-core results, or {url, violations:[...]}, or a list
    --defence FILE    `critique_report.py --format defence` markdown
    --screenshots DIR .png/.jpg/.webp/.avif/.gif/.svg, inlined as data URIs.
                      `home--before.png` + `home--after.png` pair automatically.

AUDIENCES
---------
    client             risk and outcome first; plain language; ends on an ask
    team               architecture first; every decision, terse; ends on where
                       to start
    creative-director  premise first, hardest decisions first, alternatives
                       shown, weaknesses raised early

Exit codes: 0 fine · 1 the defence sheet says do not present yet · 2 bad
invocation or unreadable input.
"""

from __future__ import annotations

import argparse
import base64
import datetime as _dt
import html
import json
import mimetypes
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SKILL_ROOT = Path(__file__).resolve().parent.parent

AUDIENCES = ("client", "team", "creative-director")

IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".avif", ".gif", ".svg"}

# A status that means "this is not a decision yet" — the honesty boundary.
OPEN_STATUSES = {"coin-flip", "coinflip", "open", "preference", "taste"}

PLACEHOLDER = re.compile(r"<[a-z][^<>]{2,}>")


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

class BuildError(Exception):
    """Anything the user can fix by changing an argument or an input file."""


# ---------------------------------------------------------------------------
# The decision log
# ---------------------------------------------------------------------------

FIELD_ALIASES = {
    "constraint": "constraint", "constraints": "constraint",
    "problem": "constraint", "forcing function": "constraint",
    "options": "options", "options considered": "options",
    "alternatives": "options", "considered": "options",
    "choice": "choice", "decision": "choice", "what we did": "choice",
    "consequence": "consequence", "consequences": "consequence",
    "cost": "consequence", "tradeoff": "consequence", "trade-off": "consequence",
    "evidence": "evidence", "proof": "evidence", "source": "evidence",
    "say": "say", "say it like this": "say", "out loud": "say",
    "status": "status", "audience": "audience", "audiences": "audience",
    "tags": "tags", "tag": "tags", "owner": "owner", "date": "date",
    "reversible": "reversible",
}

META_ALIASES = {
    "project": "project", "client": "client", "presenter": "presenter",
    "author": "presenter", "date": "date", "meeting": "meeting",
    "stage": "stage", "audience": "audience",
}


@dataclass
class Decision:
    ident: str
    title: str
    status: str = "decided"
    audiences: list[str] = field(default_factory=list)
    constraint: str = ""
    options: list[str] = field(default_factory=list)
    choice: str = ""
    consequence: str = ""
    evidence: str = ""
    say: str = ""
    tags: list[str] = field(default_factory=list)
    owner: str = ""
    reversible: str = ""
    line: int = 0

    @property
    def is_open(self) -> bool:
        return self.status.strip().lower() in OPEN_STATUSES

    @property
    def is_coin_flip(self) -> bool:
        return self.status.strip().lower() in {"coin-flip", "coinflip"}

    def placeholders(self) -> list[str]:
        out = []
        for name in ("constraint", "choice", "consequence", "evidence"):
            val = getattr(self, name)
            if val and PLACEHOLDER.search(val):
                out.append(name)
        return out


@dataclass
class DecisionLog:
    meta: dict[str, str] = field(default_factory=dict)
    sections: dict[str, str] = field(default_factory=dict)
    decisions: list[Decision] = field(default_factory=list)
    path: Path | None = None


_HEAD = re.compile(r"^(#{1,4})\s+(.*?)\s*$")
_FIELD = re.compile(r"^\s*(?:[-*]\s*)?\*\*([A-Za-z][A-Za-z \-/]{1,28}):?\*\*\s*:?\s*(.*)$")
_DECISION_HEAD = re.compile(
    r"^(?:(D[-\s]?\d+|\d+)[\s.:—–-]+)?(.*)$"
)


def _split_list(value: str) -> list[str]:
    """Options may be written as `a; b; c`, as `a | b`, or as a bullet list.

    A wrapped line is NOT an item boundary. Getting this wrong silently
    chops one option into three fragments mid-sentence, which reaches the
    client as three alternatives you did not consider."""
    if not value.strip():
        return []
    lines = [l for l in value.splitlines() if l.strip()]
    if len(lines) > 1 and all(l.lstrip().startswith(("-", "*")) for l in lines):
        return [l.lstrip(" -*\t").strip() for l in lines]
    flat = " ".join(value.split())
    for sep in (";", "|"):
        if sep in flat:
            return [p.strip() for p in flat.split(sep) if p.strip()]
    return [flat]


def _norm_tags(value: str) -> list[str]:
    return [t.strip().lower() for t in re.split(r"[,;/]", value) if t.strip()]


def parse_decision_log(text: str, path: Path | None = None) -> DecisionLog:
    """Parse assets/DECISION_LOG.md.

    Deliberately forgiving: field order does not matter, `- **Choice:**` and
    `**Choice:**` are the same thing, and an unknown `**Field:**` is kept as
    prose rather than dropped. The template is meant to be filled in at 6pm
    on the day a decision was made, not proof-read.
    """
    log = DecisionLog(path=path)
    lines = text.splitlines()

    section: str | None = None          # current ## section (lowercased)
    current: Decision | None = None
    field_name: str | None = None
    buf: list[str] = []
    section_buf: dict[str, list[str]] = {}
    in_decisions = False
    in_fence = False

    def flush_field() -> None:
        nonlocal field_name, buf
        if current is not None and field_name:
            value = "\n".join(buf).strip()
            _assign(current, field_name, value)
        field_name, buf = None, []

    def _assign(dec: Decision, name: str, value: str) -> None:
        if not value:
            return
        if name == "options":
            dec.options = _split_list(value)
        elif name == "tags":
            dec.tags = _norm_tags(value)
        elif name == "audience":
            dec.audiences = [_canon_audience(a) for a in _norm_tags(value)]
            dec.audiences = [a for a in dec.audiences if a]
        elif name == "status":
            dec.status = value.strip().strip(".").lower()
        elif hasattr(dec, name):
            setattr(dec, name, value)

    for n, raw in enumerate(lines, 1):
        if raw.strip().startswith("```"):
            in_fence = not in_fence
        if in_fence:
            if field_name:
                buf.append(raw)
            continue

        head = _HEAD.match(raw)
        if head:
            flush_field()
            level, title = len(head.group(1)), head.group(2).strip()
            if level == 1:
                log.meta.setdefault("title", title)
                section = None
                continue
            if level == 2:
                key = title.lower().strip(" :")
                section = key
                in_decisions = bool(re.match(r"^(decisions?|the decisions?|log)\b", key))
                section_buf.setdefault(key, [])
                current = None
                continue
            if level == 3 and (in_decisions or re.match(r"^d\s?\d+\b", title.lower())):
                m = _DECISION_HEAD.match(title)
                ident = (m.group(1) or "").replace(" ", "").replace("-", "") if m else ""
                name = (m.group(2) or title).strip(" —–-:") if m else title
                if not ident:
                    taken = {d.ident for d in log.decisions}
                    k = len(log.decisions) + 1
                    while f"D{k}" in taken:
                        k += 1
                    ident = f"D{k}"
                current = Decision(ident=ident.upper(), title=name, line=n)
                log.decisions.append(current)
                continue
            # any other heading inside a section is prose
            if section:
                section_buf.setdefault(section, []).append(raw)
            continue

        fm = _FIELD.match(raw)
        if fm and not raw.strip().startswith(">"):
            key = fm.group(1).strip().lower()
            value = fm.group(2).strip()
            if current is not None:
                canon = FIELD_ALIASES.get(key)
                if canon:
                    flush_field()
                    field_name, buf = canon, [value]
                    continue
            else:
                canon_meta = META_ALIASES.get(key)
                if canon_meta and not log.decisions:
                    log.meta.setdefault(canon_meta, value)
                    continue
        if field_name is not None:
            if raw.strip() == "":
                flush_field()
            else:
                buf.append(raw)
            continue
        if section:
            section_buf.setdefault(section, []).append(raw)

    flush_field()

    for key, body in section_buf.items():
        joined = "\n".join(body).strip()
        if joined:
            log.sections[key] = joined
    return log


def _canon_audience(value: str) -> str:
    v = value.strip().lower().replace("_", "-").replace(" ", "-")
    if v in ("cd", "creative-director", "creativedirector", "director"):
        return "creative-director"
    if v in ("client", "stakeholder", "customer"):
        return "client"
    if v in ("team", "dev", "devs", "developer", "developers", "internal", "eng"):
        return "team"
    if v in ("all", "any", "everyone"):
        return "all"
    return ""


# ---------------------------------------------------------------------------
# Citations — every generated number knows where it came from
# ---------------------------------------------------------------------------

@dataclass
class Cite:
    value: str
    source: str            # the file the number came from
    path: str              # JSON path inside it, or "derived"
    note: str = ""

    def as_dict(self) -> dict[str, str]:
        return {"value": self.value, "source": self.source,
                "path": self.path, "note": self.note}


class Provenance:
    """The deck's bibliography. Nothing numeric is rendered without one."""

    def __init__(self) -> None:
        self.items: list[Cite] = []

    def add(self, value: Any, source: str, path: str, note: str = "") -> Cite:
        c = Cite(str(value), source, path, note)
        self.items.append(c)
        return c

    def as_json(self) -> str:
        return json.dumps([c.as_dict() for c in self.items], indent=2)


# ---------------------------------------------------------------------------
# Evidence loaders
# ---------------------------------------------------------------------------

def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_bytes())
    except OSError as exc:
        raise BuildError(f"cannot read {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise BuildError(
            f"{path} is not valid JSON ({exc}). If you piped a tool's output, "
            f"check that nothing else printed to stdout — use `--json > file`.") from exc


@dataclass
class AuditFacts:
    source: str
    errors: int
    warnings: int
    files: int
    by_law: dict[str, int]
    clean: bool


def load_audit(path: Path) -> AuditFacts:
    data = _read_json(path)
    if isinstance(data, dict) and "findings" in data:
        data = data["findings"]
    if not isinstance(data, list):
        raise BuildError(
            f"{path} does not look like `audit_design.py --json` output "
            f"(expected a JSON list of findings).")
    errors = sum(1 for f in data if isinstance(f, dict) and f.get("severity") == "error")
    warnings = sum(1 for f in data if isinstance(f, dict) and f.get("severity") == "warning")
    by_law: dict[str, int] = {}
    files = set()
    for f in data:
        if not isinstance(f, dict):
            continue
        by_law[f.get("law", "--")] = by_law.get(f.get("law", "--"), 0) + 1
        files.add(f.get("file", ""))
    return AuditFacts(str(path), errors, warnings, len(files), by_law,
                      clean=not data)


@dataclass
class PerfFacts:
    source: str
    total_bytes: int | None
    budget_total: int | None
    by_kind: dict[str, int]
    budget_by_kind: dict[str, int]
    errors: int
    warnings: int
    largest: dict[str, Any] | None


def load_perf(path: Path) -> PerfFacts:
    data = _read_json(path)
    if not isinstance(data, dict) or "ledger" not in data:
        raise BuildError(
            f"{path} does not look like `perf_audit.py --json` output "
            f"(expected an object with a `ledger` key).")
    ledger = data.get("ledger") or {}
    by_kind = {k: v for k, v in (ledger.get("bytes") or {}).items()
               if isinstance(v, int)}
    budget = (data.get("budget") or {}).get("bytes") or {}
    findings = data.get("findings") or []
    assets = ledger.get("assets") or []
    return PerfFacts(
        source=str(path),
        total_bytes=by_kind.get("total"),
        budget_total=budget.get("total"),
        by_kind=by_kind,
        budget_by_kind={k: v for k, v in budget.items() if isinstance(v, int)},
        errors=sum(1 for f in findings if f.get("severity") == "error"),
        warnings=sum(1 for f in findings if f.get("severity") == "warning"),
        largest=assets[0] if assets else None,
    )


@dataclass
class A11yFacts:
    source: str
    pages: int
    violations: int
    nodes: int
    by_impact: dict[str, int]
    top_rules: list[tuple[str, int]]
    passes: int | None
    contrast: int = 0          # elements failing axe's color-contrast rule


def load_a11y(path: Path) -> A11yFacts:
    data = _read_json(path)
    runs = data if isinstance(data, list) else [data]
    violations = 0
    nodes = 0
    passes = 0
    saw_passes = False
    by_impact: dict[str, int] = {}
    rules: dict[str, int] = {}
    pages = 0
    for run in runs:
        if not isinstance(run, dict):
            continue
        pages += 1
        vs = run.get("violations")
        if vs is None:
            raise BuildError(
                f"{path} has no `violations` key. Supply an axe-core result "
                f"object, a list of them, or any JSON with the same shape.")
        for v in vs:
            violations += 1
            impact = (v.get("impact") or "unspecified").lower()
            n = len(v.get("nodes") or []) or 1
            nodes += n
            by_impact[impact] = by_impact.get(impact, 0) + n
            rid = v.get("id") or v.get("rule") or "unnamed"
            rules[rid] = rules.get(rid, 0) + n
        if isinstance(run.get("passes"), list):
            saw_passes = True
            passes += len(run["passes"])
    top = sorted(rules.items(), key=lambda kv: (-kv[1], kv[0]))[:4]
    return A11yFacts(str(path), pages, violations, nodes, by_impact, top,
                     passes if saw_passes else None,
                     contrast=rules.get("color-contrast", 0))


@dataclass
class DefenceFacts:
    source: str
    decisions: list[dict[str, str]]
    preferences: list[tuple[str, str]]
    flaws: list[tuple[str, str, str]]
    blockers: list[str]


_MD_ROW = re.compile(r"^\|(.+)\|\s*$")


def _md_table(block: list[str]) -> list[list[str]]:
    rows = []
    for line in block:
        m = _MD_ROW.match(line.strip())
        if not m:
            continue
        cells = [c.strip() for c in m.group(1).split("|")]
        if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
            continue
        rows.append(cells)
    return rows[1:] if rows else []      # drop the header row


def load_defence(path: Path) -> DefenceFacts:
    """Consume `critique_report.py --format defence`. Do not re-derive it."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise BuildError(f"cannot read {path}: {exc}") from exc

    blocks: dict[str, list[str]] = {}
    key = ""
    for line in text.splitlines():
        if line.startswith("## "):
            key = line[3:].strip().lower()
            blocks[key] = []
        elif key:
            blocks[key].append(line)

    def find(*needles: str) -> list[str]:
        for k, v in blocks.items():
            if all(nd in k for nd in needles):
                return v
        return []

    decisions = []
    for row in _md_table(find("decisions")):
        if len(row) >= 4:
            decisions.append({"decision": row[0], "rationale": row[1],
                              "alternative": row[2], "cost": row[3]})
    preferences = [(r[0], r[1]) for r in _md_table(find("preferences")) if len(r) >= 2]
    flaws = [(r[0], r[1], r[2]) for r in _md_table(find("flaws")) if len(r) >= 3]
    blockers = [l.strip("- ").strip() for l in find("do not present")
                if l.strip().startswith("-")]
    return DefenceFacts(str(path), decisions, preferences, flaws, blockers)


# ---------------------------------------------------------------------------
# Screenshots
# ---------------------------------------------------------------------------

@dataclass
class Shot:
    name: str
    caption: str
    data_uri: str
    kind: str = "single"      # single | before | after
    group: str = ""
    bytes: int = 0


_BA = re.compile(r"(?:^|[-_.]{1,2})(before|after)(?:$|[-_.])", re.I)


def load_screenshots(directory: Path) -> tuple[list[Shot], list[tuple[Shot, Shot]]]:
    if not directory.is_dir():
        raise BuildError(f"--screenshots {directory} is not a directory")
    shots: list[Shot] = []
    for p in sorted(directory.iterdir()):
        if p.suffix.lower() not in IMAGE_EXT or not p.is_file():
            continue
        raw = p.read_bytes()
        mime = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
        if p.suffix.lower() == ".svg":
            mime = "image/svg+xml"
        uri = f"data:{mime};base64,{base64.b64encode(raw).decode('ascii')}"
        stem = p.stem
        m = _BA.search(stem)
        kind, group = "single", ""
        if m:
            kind = m.group(1).lower()
            group = _BA.sub("", stem).strip(" -_.")
        caption_file = p.with_suffix(".txt")
        caption = ""
        if caption_file.exists():
            caption = caption_file.read_text(encoding="utf-8").strip()
        if not caption:
            caption = re.sub(r"^\d+[-_. ]*", "", group or stem)
            caption = caption.replace("-", " ").replace("_", " ").strip()
            caption = caption[:1].upper() + caption[1:] if caption else p.name
        shots.append(Shot(p.name, caption, uri, kind, group or stem, len(raw)))

    pairs: list[tuple[Shot, Shot]] = []
    befores = {s.group: s for s in shots if s.kind == "before"}
    afters = {s.group: s for s in shots if s.kind == "after"}
    for g in sorted(set(befores) & set(afters)):
        pairs.append((befores[g], afters[g]))
    paired = {id(s) for pair in pairs for s in pair}
    singles = [s for s in shots if id(s) not in paired]
    return singles, pairs


# ---------------------------------------------------------------------------
# Slides
# ---------------------------------------------------------------------------

@dataclass
class Slide:
    kind: str
    title: str
    kicker: str = ""
    blocks: list[str] = field(default_factory=list)      # rendered HTML
    notes: list[str] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)
    outline: list[str] = field(default_factory=list)     # dry-run detail


# --- tiny inline markdown ---------------------------------------------------

def esc(text: str) -> str:
    return html.escape(text or "", quote=True)


def inline(text: str) -> str:
    """Escape, then honour `code` and **bold**. Nothing else — this is a deck."""
    out = esc(text)
    out = re.sub(r"`([^`]+)`", r"<code class='code'>\1</code>", out)
    out = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", out)
    out = out.replace("\n\n", "<br><br>").replace("\n", " ")
    return out


def quoted(text: str, source: str = "decision-log") -> str:
    """Words that are not the generator's, marked with whose they are.

    Everything the deck did not compute itself carries this. A number inside a
    quoted span is the author's claim, sourced from the decision log or the
    critique gate's defence sheet; a number outside one is the deck's own and
    must carry a `data-cite`. That split is what makes "no invented figures"
    a checkable property rather than a promise."""
    return f"<span data-quoted=\"{esc(source)}\">{inline(text)}</span>"


def derived(value: int, of: str) -> str:
    """A count of the deck's own content — slides, decisions, rows."""
    return (f"<span class='num' data-derived=\"{esc(of)}\">{value}</span>")


def cited(cite: Cite, display: str | None = None) -> str:
    ref = f"{cite.source}#{cite.path}"
    return (f"<span class='num' data-cite=\"{esc(ref)}\" "
            f"data-value=\"{esc(cite.value)}\">{esc(display or cite.value)}</span>")


def human_bytes(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.2f} MB"
    if n >= 1000:
        return f"{n / 1000:.1f} KB"
    return f"{n} B"


# --- block builders ---------------------------------------------------------

def blk_lede(text: str) -> str:
    return f"<p class='lede'>{inline(text)}</p>"


def blk_prose(text: str, source: str = "decision-log") -> str:
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    out = []
    for p in paras:
        if p.startswith(("-", "*")):
            items = [quoted(l.strip(" -*"), source)
                     for l in p.splitlines() if l.strip(" -*")]
            out.append("<ul class='list'>" +
                       "".join(f"<li>{i}</li>" for i in items) + "</ul>")
        else:
            out.append(f"<p class='body'>{quoted(p, source)}</p>")
    return "".join(out)


def blk_table(headers: list[str], rows: list[list[str]]) -> str:
    if not any(h.strip() for h in headers):
        body = "".join(
            "<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>"
            for row in rows)
        return f"<table class='dtable'><tbody>{body}</tbody></table>"
    head = "".join(f"<th scope='col'>{esc(h)}</th>" for h in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>" for row in rows)
    return (f"<table class='dtable'><thead><tr>{head}</tr></thead>"
            f"<tbody>{body}</tbody></table>")


def blk_metrics(items: list[tuple[str, str, str]]) -> str:
    """`value` and `foot` are HTML — a number in either must already be cited."""
    cells = []
    for value_html, label, foot_html in items:
        cells.append(
            f"<div class='metric'><p class='metric__value'>{value_html}</p>"
            f"<p class='metric__label'>{inline(label)}</p>"
            f"<p class='metric__foot'>{foot_html}</p></div>")
    return f"<div class='metrics'>{''.join(cells)}</div>"


def blk_callout(tone: str, title: str, body: str) -> str:
    return (f"<aside class='callout' data-tone='{esc(tone)}'>"
            f"<p class='callout__title'>{inline(title)}</p>"
            f"<div class='callout__body'>{body}</div></aside>")


def blk_cards(cards: list[tuple[str, str]]) -> str:
    out = []
    for title, body in cards:
        out.append(f"<div class='card'><p class='card__title'>{inline(title)}</p>"
                   f"<div class='card__body'>{body}</div></div>")
    return f"<div class='cards'>{''.join(out)}</div>"


def blk_shot(shot: Shot, label: str = "") -> str:
    cap = label or shot.caption
    return (f"<figure class='shot'><img class='shot__img' src='{shot.data_uri}' "
            f"alt='{esc(shot.caption)}' loading='lazy' decoding='async'>"
            f"<figcaption class='shot__cap'>{inline(cap)}</figcaption></figure>")


# ---------------------------------------------------------------------------
# Decision ranking — the three to five this audience actually cares about
# ---------------------------------------------------------------------------

TAG_WEIGHTS = {
    "client": {"conversion", "content", "brand", "cost", "timeline", "trust",
               "seo", "mobile", "accessibility", "scope", "copy"},
    "team": {"architecture", "tokens", "perf", "performance", "states", "data",
             "api", "build", "component", "testing", "a11y", "accessibility"},
    "creative-director": {"type", "typography", "color", "colour", "layout",
                          "motion", "craft", "brand", "hierarchy", "grid"},
}


def rank_decisions(decisions: list[Decision], audience: str) -> list[Decision]:
    def score(d: Decision) -> tuple[int, int]:
        s = 0
        if audience in d.audiences:
            s += 100
        if "all" in d.audiences:
            s += 60
        if not d.audiences:
            s += 25
        hits = len(TAG_WEIGHTS.get(audience, set()) & set(d.tags))
        s += 12 * min(hits, 2)
        if d.evidence:
            s += 15
        if d.consequence:
            s += 10
        if audience == "creative-director":
            # A creative director is buying judgement, so lead with the calls
            # that had the most live alternatives — those are the hard ones.
            s += 8 * len(d.options)
        return (-s, d.line)

    return sorted([d for d in decisions if not d.is_open], key=score)


def decision_block(d: Decision, audience: str) -> tuple[str, list[str]]:
    """Render one decision in the shape the audience needs. Returns (html, gaps)."""
    gaps: list[str] = []
    if not d.constraint:
        gaps.append(f"{d.ident} has no constraint. Without one it is taste — "
                    f"find the forcing function or move it to the open questions.")
    if not d.consequence:
        gaps.append(f"{d.ident} has no consequence. Every real decision costs "
                    f"something; naming it first is what makes the rest credible.")
    if not d.evidence:
        gaps.append(f"{d.ident} has no evidence. Say so out loud — "
                    f"\"that one is judgement, not data\" — rather than implying one.")
    for fieldname in d.placeholders():
        gaps.append(f"{d.ident}: `{fieldname}` still contains a template "
                    f"placeholder. Fill it or cut the slide.")

    rows: list[tuple[str, str]] = []
    if audience == "client":
        order = [("The problem", d.constraint),
                 ("What we did", d.choice),
                 ("What it costs", d.consequence),
                 ("How we know", d.evidence)]
    elif audience == "team":
        order = [("Decision", d.choice),
                 ("Forced by", d.constraint),
                 ("Consequence you inherit", d.consequence),
                 ("Evidence", d.evidence)]
    else:
        order = [("Constraint", d.constraint),
                 ("Choice", d.choice),
                 ("Consequence", d.consequence),
                 ("Evidence", d.evidence)]
    for label, value in order:
        if value:
            rows.append((label, quoted(value)))

    parts = [f"<dl class='dlist'>" + "".join(
        f"<div class='dlist__row'><dt class='dlist__key'>{esc(k)}</dt>"
        f"<dd class='dlist__val'>{v}</dd></div>" for k, v in rows) + "</dl>"]

    if d.options:
        label = ("We also considered" if audience == "client"
                 else "Rejected, and why" if audience == "creative-director"
                 else "Alternatives")
        items = "".join(f"<li>{quoted(o)}</li>" for o in d.options)
        emphasis = "strong" if audience == "creative-director" else "quiet"
        parts.append(f"<div class='options' data-emphasis='{emphasis}'>"
                     f"<p class='options__title'>{esc(label)}</p>"
                     f"<ul class='list'>{items}</ul></div>")
    elif audience == "creative-director":
        gaps.append(f"{d.ident} lists no alternative. A director reads a "
                    f"decision with no rejected option as a first idea kept.")
    return "".join(parts), gaps


# ---------------------------------------------------------------------------
# Evidence slides — plain language, numbers cited
# ---------------------------------------------------------------------------

def slide_system(audit: AuditFacts, prov: Provenance, audience: str) -> Slide:
    s = Slide("evidence-system", "One system, not one page")
    if audit.clean:
        c = prov.add(0, audit.source, "$[*].severity == error",
                     "audit_design.py reported no findings at all")
        if audience == "client":
            s.kicker = "What this buys you"
            s.blocks.append(blk_lede(
                "Every value on the site — every colour, every space, every type "
                "size — comes from one file. A brand change is one edit, not a "
                "month of finding places it was typed in by hand."))
        elif audience == "team":
            s.kicker = "Conformance"
            s.blocks.append(blk_lede(
                "`audit_design.py` is clean. The gate is wired into the "
                "pre-commit hook: the next person cannot quietly leave the "
                "system without the build telling them."))
        else:
            s.kicker = "Craft, mechanically checked"
            s.blocks.append(blk_lede(
                "Laws 1–6 are machine-checked, and the audit is clean: no hardcoded "
                "value survived into the build, so the system is real rather than "
                "aspirational."))
        s.blocks.append(blk_metrics([
            (cited(c, "0"), "violations",
             inline("design audit, strict mode")),
        ]))
        s.notes.append("Say the consequence, not the tool: a rebrand is one file. "
                       "Do not name the script unless someone asks.")
    else:
        c_err = prov.add(audit.errors, audit.source,
                         "count($[?severity=='error'])")
        c_warn = prov.add(audit.warnings, audit.source,
                          "count($[?severity=='warning'])")
        s.blocks.append(blk_lede(
            "The system is in place and not yet fully clean. Naming that here "
            "is cheaper than having it found."))
        s.blocks.append(blk_metrics([
            (cited(c_err), "errors open", inline("design audit")),
            (cited(c_warn), "warnings", inline("design audit")),
        ]))
        s.gaps.append(
            f"The design audit is not clean ({audit.errors} error(s)). Either "
            f"fix before the meeting or put it on the known-flaws slide with a "
            f"date — do not leave it here for someone to find.")
        s.notes.append("If asked: these are conformance items, not visual "
                       "defects, and they are a known list with an owner.")
    return s


def slide_perf(perf: PerfFacts, prov: Provenance, audience: str) -> Slide:
    # The title is a claim, so it comes from the numbers: a byte ledger says
    # what the page weighs, never that it is fast.
    over = bool(perf.total_bytes and perf.budget_total
                and perf.total_bytes > perf.budget_total)
    if over:
        title = "Over its weight budget, and what happens next"
    elif perf.budget_total and perf.total_bytes is not None and not perf.errors:
        title = "Inside the weight budget we agreed"
    else:
        title = "What the page weighs"
    s = Slide("evidence-perf", title)
    if over:
        s.gaps.append(
            f"The page is {round(perf.total_bytes / perf.budget_total * 100)}% of its "
            f"weight budget. Fix it before the meeting, or put it on the known-flaws "
            f"slide with an owner and a date.")
    rows: list[tuple[str, str, str]] = []
    if perf.total_bytes is not None:
        c_total = prov.add(perf.total_bytes, perf.source, "ledger.bytes.total")
        foot = inline("total page weight")
        if perf.budget_total:
            c_budget = prov.add(perf.budget_total, perf.source, "budget.bytes.total")
            budget_html = cited(c_budget, human_bytes(perf.budget_total))
            pct = round(perf.total_bytes / perf.budget_total * 100)
            c_pct = prov.add(pct, perf.source,
                             "derived: ledger.bytes.total / budget.bytes.total")
            foot = f"of a {budget_html} budget agreed before the build"
            rows.append((cited(c_pct, f"{pct}%"), "of budget used",
                         f"budget {budget_html}"))
        rows.append((cited(c_total, human_bytes(perf.total_bytes)),
                     "page weight", foot))
    if perf.largest:
        big = perf.largest
        c_big = prov.add(big.get("transfer", 0), perf.source, "ledger.assets[0].transfer")
        rows.append((cited(c_big, human_bytes(int(big.get("transfer", 0)))),
                     "largest single asset",
                     quoted(str(big.get("path", "")), perf.source)))

    if audience == "client":
        s.kicker = "What a number means here"
        s.blocks.append(blk_lede(
            "A page budget is a promise about a device and a network, written "
            "down before the build so it cannot be argued away afterwards."))
    elif audience == "team":
        s.kicker = "The budget and the gate"
        s.blocks.append(blk_lede(
            "`perf_audit.py` runs on every commit against a committed budget. "
            "Existing debt is baselined; new weight fails the build."))
    else:
        s.kicker = "Weight, measured"
        s.blocks.append(blk_lede(
            "The visual decisions were made inside a weight budget rather than "
            "against one afterwards."))
    if rows:
        s.blocks.append(blk_metrics(rows))
    else:
        s.gaps.append("The performance JSON contained no byte ledger, so this "
                      "slide makes no claim. Re-run `perf_audit.py --json` "
                      "against the built output, not the source.")
    if perf.errors or perf.warnings:
        c_e = prov.add(perf.errors, perf.source, "count(findings[?severity=='error'])")
        c_w = prov.add(perf.warnings, perf.source, "count(findings[?severity=='warning'])")
        s.blocks.append(blk_callout(
            "note", "Open performance findings",
            f"<p class='body'>{cited(c_e)} error(s), {cited(c_w)} warning(s) "
            f"from the static audit. Raise these yourself, before anyone "
            f"asks.</p>"))
    s.notes.append(
        "Never present a lab number as a user-experience guarantee. The honest "
        "sentence is: 'this is what it weighs, measured on the build we are "
        "shipping; field data at the 75th percentile is the number that "
        "actually matters and we will watch it after launch.'")
    return s


def manual_testing(log: DecisionLog) -> str:
    """What the decision log records as tested by hand (`## Tested by hand`).
    The deck claims manual testing only from here — never by default."""
    for key in ("tested by hand", "manual testing", "tested manually", "manual checks"):
        # The template's own guidance is an HTML comment; it records nothing.
        text = re.sub(r"<!--.*?-->", "", log.sections.get(key, ""), flags=re.S).strip()
        if text:
            return text
    return ""


def slide_a11y(a11y: A11yFacts, prov: Provenance, audience: str,
               manual: str = "") -> Slide:
    s = Slide("evidence-a11y", "Accessibility, stated honestly")
    c_v = prov.add(a11y.violations, a11y.source, "count(violations)")
    c_n = prov.add(a11y.nodes, a11y.source, "sum(len(violations[].nodes))")
    c_p = prov.add(a11y.pages, a11y.source, "count(results)")
    metrics = [
        (cited(c_v), "automated violations", inline("across the pages scanned")),
        (cited(c_n), "elements affected", inline("each one a real node")),
        (cited(c_p), "page(s) scanned", inline("automated pass")),
    ]
    s.blocks.append(blk_metrics(metrics))
    serious = sum(v for k, v in a11y.by_impact.items()
                  if k in ("critical", "serious"))
    if a11y.by_impact:
        c_s = prov.add(serious, a11y.source,
                       "sum(by_impact[critical,serious])")
        rows = []
        for impact in ("critical", "serious", "moderate", "minor", "unspecified"):
            if impact in a11y.by_impact:
                c = prov.add(a11y.by_impact[impact], a11y.source,
                             f"by_impact.{impact}")
                rows.append([esc(impact), cited(c)])
        s.blocks.append(blk_table(["Impact", "Elements"], rows))
        _ = c_s
    # Every sentence below is chosen from the data. "Passes" only when the
    # automated result has no violations; "keyboard-tested" only when the
    # decision log records it (## Tested by hand).
    limits = ("Automated tools find only part of the problems — they cannot "
              "judge whether alt text is <em>accurate</em> or whether an "
              "interaction makes sense to a screen reader user.")
    if a11y.violations:
        claim = (f"The honest claim today: the automated WCAG 2.2 AA check still "
                 f"finds {cited(c_v)} issue(s) on {cited(c_n)} element(s), and "
                 f"they are listed here with an owner and a date.")
        s.gaps.append(
            f"The automated accessibility check is not clean ({a11y.violations} "
            f"violation(s) on {a11y.nodes} element(s)). Fix before presenting, or "
            f"put them on the known-flaws slide with an owner and a date.")
    else:
        claim = "The honest claim: this page passes an automated WCAG 2.2 AA check"
        claim += (" and has been keyboard-tested by hand." if manual else
                  ". Keyboard and screen-reader passes are manual, and none is "
                  "recorded for this build, so this deck does not claim one.")
    wording = (f"{claim} {limits} Claiming 'fully accessible' from a green tool "
               f"result is the one claim in this deck that can be disproved by a "
               f"single user.")
    if audience == "client":
        s.kicker = "What we can and cannot promise"
        s.blocks.append(blk_callout("note", "Say it this way",
                                    f"<p class='body'>{wording}</p>"))
    elif audience == "team":
        s.kicker = "State of the a11y gate"
        s.blocks.append(blk_callout(
            "note", "What the number is not",
            "<p class='body'>Automated checks cover only part of WCAG. The "
            "keyboard pass and the screen-reader pass are manual and belong in "
            "the definition of done.</p>"))
    else:
        s.kicker = "The floor, measured"
        if a11y.contrast:
            c_c = prov.add(a11y.contrast, a11y.source, "violations[id==color-contrast].nodes")
            body = (f"{cited(c_c)} element(s) still fail the automated contrast "
                    f"check; they are listed below, and they are defects, not taste.")
        else:
            body = (f"The automated pass found no contrast failure on the "
                    f"{cited(c_p)} page(s) scanned, which is why the colour "
                    f"decisions in this deck are not arguments about taste.")
        s.blocks.append(blk_callout("note", "Contrast is measured, never judged",
                                    f"<p class='body'>{body}</p>"))
    if a11y.top_rules:
        rows = []
        for rid, count in a11y.top_rules:
            c = prov.add(count, a11y.source, f"violations[id=={rid}].nodes")
            rows.append([f"<code class='code'>{esc(rid)}</code>", cited(c)])
        s.blocks.append(blk_table(["Rule", "Elements"], rows))
    s.notes.append("If the number is not zero, say the number, the owner and "
                   "the date before anyone asks for them.")
    return s


# ---------------------------------------------------------------------------
# The plan
# ---------------------------------------------------------------------------

@dataclass
class Inputs:
    log: DecisionLog
    audit: AuditFacts | None = None
    perf: PerfFacts | None = None
    a11y: A11yFacts | None = None
    defence: DefenceFacts | None = None
    shots: list[Shot] = field(default_factory=list)
    pairs: list[tuple[Shot, Shot]] = field(default_factory=list)


AUDIENCE_LEDE = {
    "client": ("Decisions, not designs",
               "Every screen in this deck is the result of a decision with a "
               "reason, an alternative we rejected, and a cost we accepted. "
               "You cannot usefully approve a layout. You can absolutely "
               "approve a tradeoff."),
    "team": ("How this is built, and what not to break",
             "The decisions below are load-bearing. Each one names the "
             "constraint that forced it, so you can tell a deliberate "
             "constraint from an accident when you extend this."),
    "creative-director": ("The argument the work is making",
                          "Each decision below is stated as a constraint, the "
                          "options it left open, the one taken, and what it "
                          "cost. The calls that were genuinely preference are "
                          "labelled as preference."),
}


def _open_decisions(log: DecisionLog) -> list[Decision]:
    return [d for d in log.decisions if d.is_open]


def build_plan(inp: Inputs, audience: str, max_decisions: int) -> list[Slide]:
    prov = Provenance()
    plan = _plan_for(inp, audience, max_decisions, prov)
    for s in plan:
        if s.kind == "provenance":
            # Script content is raw text, not markup: HTML-escaping it would
            # make it un-parseable. Neutralise `</script>` instead.
            payload = prov.as_json().replace("<", "\\u003c")
            s.blocks.append(
                f"<script type=\"application/json\" id=\"deck-provenance\">"
                f"{payload}</script>")
    return plan


def _cover(inp: Inputs, audience: str) -> Slide:
    meta = inp.log.meta
    title = meta.get("project") or meta.get("title") or "Design review"
    kicker, lede = AUDIENCE_LEDE[audience]
    s = Slide("cover", title, kicker=kicker)
    s.blocks.append(blk_lede(lede))
    bits = []
    for key, label in (("client", "Client"), ("presenter", "Presented by"),
                       ("date", "Date"), ("stage", "Stage")):
        if meta.get(key):
            bits.append([esc(label), quoted(meta[key])])
    if bits:
        s.blocks.append(blk_table(["", ""], bits))
    s.notes.append(
        "Do not open with 'here's what we made'. Open with the problem in "
        "their words, then the one sentence that says what changed. The first "
        "ninety seconds decide whether the rest is heard as reasoning or as "
        "decoration.")
    if not meta.get("date"):
        s.gaps.append("No date in the decision log header. A deck with no date "
                      "cannot be cited later in a scope argument.")
    return s


def _brief(inp: Inputs, audience: str, headline: list[Decision]) -> Slide | None:
    body = (inp.log.sections.get("brief")
            or inp.log.sections.get("the brief")
            or inp.log.sections.get("constraints")
            or inp.log.sections.get("what you told us"))
    title = {"client": "What you told us",
             "team": "The constraints this was built under",
             "creative-director": "The premise"}[audience]
    if audience == "creative-director":
        body = (inp.log.sections.get("premise")
                or inp.log.sections.get("the premise") or body)
    s = Slide("brief", title)
    if body:
        s.blocks.append(blk_prose(body))
    constraints = [d for d in headline if d.constraint][:4]
    if constraints:
        s.blocks.append(blk_cards(
            [(d.title, f"<p class='body'>{quoted(d.constraint)}</p>")
             for d in constraints]))
    if not body and not constraints:
        return None
    s.notes.append(
        "Say this in their words before you say anything in yours. A room that "
        "hears its own problem read back listens to the answer differently.")
    if not body:
        s.gaps.append(
            "No `## Brief` (or `## Premise`) section in the decision log, so "
            "this slide is assembled from decision constraints. Write two "
            "sentences of brief — it is the strongest opening you have.")
    return s


def _decision_index(headline: list[Decision], audience: str) -> Slide:
    n = len(headline)
    title = {"client": "The decisions worth your time",
             "team": "The decisions you are inheriting",
             "creative-director": "The calls, hardest first"}[audience]
    s = Slide("decision-index", title)
    s.blocks.append(
        f"<p class='lede'>{derived(n, 'decisions presented')} decisions. "
        f"Each one has a constraint that forced it, the option we turned down, "
        f"and what it cost.</p>")
    rows = []
    for d in headline:
        summary = d.choice or d.title
        rows.append([f"<strong>{esc(d.ident)}</strong>", quoted(d.title),
                     quoted(summary)])
    s.blocks.append(blk_table(["", "Decision", "What we did"], rows))
    s.notes.append("Read the list, then say which one you expect to be the "
                   "argument. Naming it first removes its power to ambush you.")
    return s


def _open_questions(inp: Inputs, audience: str) -> Slide | None:
    opens = _open_decisions(inp.log)
    prefs = inp.defence.preferences if inp.defence else []
    if not opens and not prefs:
        return None
    n_open = len(opens) + len(prefs)
    title = {"client": "Where we would like your preference",
             "team": "Open — pick one and log it",
             "creative-director": "Genuinely preference, and labelled as such"}[audience]
    s = Slide("open-questions", title)
    s.blocks.append(
        f"<p class='lede'>{derived(n_open, 'open questions')} open "
        f"question(s).</p>")
    s.blocks.append(blk_lede(
        "These are not decisions with hidden reasons. They are choices where "
        "the reasoning ran out and either answer is defensible. Saying so is "
        "what makes the rest of this deck worth believing."))
    rows = []
    for d in opens:
        options = "; ".join(d.options) if d.options else "—"
        status = "coin flip" if d.is_coin_flip else d.status
        rows.append([f"<strong>{esc(d.ident)}</strong>", quoted(d.title),
                     quoted(options), esc(status)])
    for what, say in prefs:
        rows.append(["<strong>taste</strong>", quoted(what, "defence-sheet"),
                     quoted(say, "defence-sheet"), "preference"])
    s.blocks.append(blk_table(
        ["", "Question", "The options", "Why it is open"], rows))
    ask = {"client": "Which do you prefer? Either is fine by us, and we will "
                     "build whichever you pick without re-opening it.",
           "team": "Pick one and append it to DESIGN_DECISIONS.md so the next "
                   "person does not re-litigate it.",
           "creative-director": "I have no argument either way on these. I would "
                                "rather take your call than manufacture a "
                                "reason."}[audience]
    s.blocks.append(blk_callout("open", "What we are asking",
                                f"<p class='body'>{inline(ask)}</p>"))
    s.notes.append(
        "Do not let these drift into justification under pressure. The whole "
        "credibility of the defended decisions rests on this slide being "
        "honest. If someone pushes for a reason, the line is: 'there isn't "
        "one I'd stand behind — that's why it's on this slide.'")
    return s


def _flaws(inp: Inputs, audience: str) -> Slide | None:
    flaws = inp.defence.flaws if inp.defence else []
    if not flaws:
        return None
    title = {"client": "What we are not happy with yet",
             "team": "Known debt — these are your first tickets",
             "creative-director": "What I already know is weak"}[audience]
    s = Slide("flaws", title)
    s.blocks.append(blk_lede(
        "Raised here, early, by us. A flaw you name is a judgement call; the "
        "same flaw found by the room is an oversight."))
    rows = [[quoted(t, "defence-sheet"), esc(sev),
             quoted(say, "defence-sheet")] for t, sev, say in flaws]
    s.blocks.append(blk_table(["What", "Severity", "The plan"], rows))
    s.gaps.append("Each row needs an owner and a date before the meeting. "
                  "'We know about it' without a date reads as 'we are not "
                  "going to fix it'.")
    s.notes.append("Say these before the visual walkthrough, not after. "
                   "Volunteering the weak part buys you the benefit of the "
                   "doubt on everything else.")
    return s


def _comparison(inp: Inputs) -> list[Slide]:
    out = []
    for before, after in inp.pairs:
        s = Slide("comparison", f"Before and after — {before.caption}")
        s.blocks.append(
            f"<div class='compare'>{blk_shot(before, 'Before')}"
            f"{blk_shot(after, 'After')}</div>")
        s.notes.append(
            "Show the real before at the same width and the same content. A "
            "flattered before — cropped tighter, older screenshot, worse "
            "content — is the fastest way to lose a room that has seen the "
            "old site more recently than you have.")
        s.gaps.append(
            "Confirm both frames are the same viewport width and the same page "
            "state. State what changed in one sentence, or the room invents "
            "its own reading.")
        out.append(s)
    return out


def _screens(inp: Inputs, audience: str) -> Slide | None:
    if not inp.shots:
        return None
    title = ("The work" if audience != "team" else "The screens you will extend")
    s = Slide("screens", title)
    s.blocks.append("<div class='shots'>" +
                    "".join(blk_shot(sh) for sh in inp.shots[:6]) + "</div>")
    if len(inp.shots) > 6:
        s.gaps.append(f"{len(inp.shots) - 6} further screenshot(s) were not "
                      f"placed. Put them on their own slides or cut them — a "
                      f"grid of nine thumbnails is a contact sheet, not an "
                      f"argument.")
    s.notes.append("Full-width, one idea per screen. Do not narrate what they "
                   "can see; say what it is doing and why.")
    return s


def _ask(inp: Inputs, audience: str) -> Slide:
    body = (inp.log.sections.get("ask")
            or inp.log.sections.get("the ask")
            or inp.log.sections.get("next"))
    title = {"client": "What we need from you today",
             "team": "Where to start",
             "creative-director": "What I want from this review"}[audience]
    s = Slide("ask", title)
    if body:
        s.blocks.append(blk_prose(body))
    else:
        default = {
            "client": ["Sign-off on the decisions above, or a named objection "
                       "to any one of them.",
                       "A preference on the open questions.",
                       "Confirmation of the launch date we are building to."],
            "team": ["Read DESIGN_DECISIONS.md before the first commit.",
                     "Run the design and performance gates locally once.",
                     "Take the known-debt list as the first tickets."],
            "creative-director": ["Push on the decisions, not the pixels.",
                                  "Tell me which open question you would take "
                                  "and why.",
                                  "Tell me if the premise is wrong — that is "
                                  "the only finding that changes everything."],
        }[audience]
        s.blocks.append("<ul class='list'>" +
                        "".join(f"<li>{inline(i)}</li>" for i in default) +
                        "</ul>")
        s.gaps.append(
            "No `## Ask` section in the decision log, so this slide is a "
            "generic default. A presentation without a specific ask gets a "
            "vague answer — write the three things you need said out loud.")
    s.blocks.append(blk_callout(
        "note", "Capture the room",
        "<p class='body'>Whatever is decided here goes into "
        "<code class='code'>MEETING_RECORD.md</code> before the end of the day, "
        "with owners and costs. It is the deliverable everyone forgets and the "
        "only thing that makes a scope conversation short later.</p>"))
    s.notes.append(
        "Close on the ask and then stop talking. The pause is the ask.")
    return s


def _appendix(inp: Inputs) -> Slide:
    s = Slide("appendix", "Every decision, for the record")
    rows = []
    for d in inp.log.decisions:
        status = "coin flip" if d.is_coin_flip else d.status
        rows.append([f"<strong>{esc(d.ident)}</strong>", quoted(d.title),
                     quoted(d.choice or "—"), esc(status)])
    s.blocks.append(blk_table(["", "Decision", "Choice", "Status"], rows))
    s.notes.append("Never presented. It exists so that any question lands on a "
                   "row rather than on memory.")
    return s


def _provenance_slide(inp: Inputs) -> Slide:
    s = Slide("provenance", "Where every number came from")
    sources = []
    for label, obj in (("design audit", inp.audit), ("performance", inp.perf),
                       ("accessibility", inp.a11y)):
        if obj is not None:
            sources.append([esc(label), f"<code class='code'>"
                                        f"{esc(getattr(obj, 'source'))}</code>"])
    if inp.defence:
        sources.append(["defence sheet",
                        f"<code class='code'>{esc(inp.defence.source)}</code>"])
    if inp.log.path:
        sources.append(["decision log",
                        f"<code class='code'>{esc(str(inp.log.path))}</code>"])
    s.blocks.append(blk_table(["Claim", "File"], sources))
    s.blocks.append(blk_callout(
        "note", "The rule this enforces",
        "<p class='body'>A number you cannot defend is worse than no number. "
        "Every figure on the preceding slides carries the file and the JSON "
        "path it was read from; nothing here was typed from memory.</p>"))
    s.notes.append("Only open this if a number is challenged. Then open it "
                   "immediately — being able to is most of the argument.")
    return s


def _plan_for(inp: Inputs, audience: str, max_decisions: int,
              prov: Provenance) -> list[Slide]:
    ranked = rank_decisions(inp.log.decisions, audience)
    if audience == "team":
        headline = ranked                      # a team gets all of them
    else:
        headline = ranked[:max_decisions]

    decision_slides: list[Slide] = []
    for d in headline:
        body, gaps = decision_block(d, audience)
        s = Slide("decision", d.title, kicker=d.ident)
        s.blocks.append(body)
        s.gaps.extend(gaps)
        if d.say:
            s.notes.append("Say: " + " ".join(d.say.split()))
        else:
            s.notes.append(
                "One sentence, no hedging: constraint, choice, cost. If you "
                "cannot say it without an 'um, we sort of felt', the decision "
                "is not made yet.")
        decision_slides.append(s)

    cover = _cover(inp, audience)
    brief = _brief(inp, audience, headline)
    index = _decision_index(headline, audience) if headline else None
    opens = _open_questions(inp, audience)
    flaws = _flaws(inp, audience)
    comparisons = _comparison(inp)
    screens = _screens(inp, audience)
    ask = _ask(inp, audience)

    sys_slide = slide_system(inp.audit, prov, audience) if inp.audit else None
    perf_slide = slide_perf(inp.perf, prov, audience) if inp.perf else None
    a11y_slide = (slide_a11y(inp.a11y, prov, audience, manual_testing(inp.log))
                  if inp.a11y else None)

    plan: list[Slide] = []
    if audience == "client":
        # Risk and outcome first; the system evidence is the reassurance that
        # follows the work, not the reason to care about it.
        plan = [cover, brief, index, *decision_slides, *comparisons]
        plan += [screens]
        plan += [perf_slide, a11y_slide, sys_slide]
        plan += [opens, flaws, ask, _appendix(inp), _provenance_slide(inp)]
    elif audience == "team":
        # A developer's first question is "how is this put together", and
        # their second is "what breaks if I touch it".
        plan = [cover, sys_slide, brief, index, *decision_slides]
        plan += [perf_slide, a11y_slide]
        plan += [opens, flaws, screens, *comparisons, ask,
                 _provenance_slide(inp)]
    else:
        # A creative director is buying judgement: premise, then the hardest
        # calls with their alternatives, then the weaknesses before anyone
        # finds them.
        plan = [cover, brief, index, *decision_slides, flaws, opens]
        plan += [*comparisons, screens, sys_slide, perf_slide, a11y_slide]
        plan += [ask, _provenance_slide(inp)]

    plan = [s for s in plan if s is not None]

    # Deck-level gaps, attached to the cover so they are impossible to miss.
    if inp.audit is None:
        cover.gaps.append("No `--audit` JSON. The deck makes no claim about "
                          "system integrity — do not make one out loud.")
    if inp.perf is None:
        cover.gaps.append("No `--perf` JSON. The deck contains no speed claim. "
                          "Saying 'it's fast' without the file is the exact "
                          "number you cannot defend.")
    if inp.a11y is None:
        cover.gaps.append("No `--a11y` report. Say nothing about accessibility "
                          "beyond what you tested by hand, and say which.")
    if not inp.shots and not inp.pairs:
        cover.gaps.append("No screenshots. A deck of decisions with no work on "
                          "screen is a memo — put the work up.")
    if inp.defence is None:
        cover.gaps.append("No `--defence` sheet. Run design-critique-gate "
                          "first: `python -m scripts.critique_report "
                          "findings.json --format defence`.")
    if inp.defence and inp.defence.blockers:
        cover.gaps.append(
            "The defence sheet lists " + str(len(inp.defence.blockers)) +
            " blocking item(s) under 'do not present until fixed'. Fix them, "
            "then rebuild.")
    if inp.defence:
        known = {d.title.lower() for d in inp.log.decisions}
        for row in inp.defence.decisions:
            name = row.get("decision", "").lower()
            if name and not any(name[:24] in k or k[:24] in name for k in known):
                cover.gaps.append(
                    f"The defence sheet declares a decision the log does not: "
                    f"“{row.get('decision')}”. Add it to "
                    f"DECISION_LOG.md or drop it from the sheet.")
    return plan


# ---------------------------------------------------------------------------
# Rendering — HTML
# ---------------------------------------------------------------------------

DECK_CSS = """@layer layout {
  /* ------------------------------------------------------------------
     .deck — the presentation shell. One scroll-free viewport, a chrome
     bar that never moves, and a slide region that owns nothing but its
     own inset. Layout lives here so components stay position-agnostic.
     ------------------------------------------------------------------ */
  .deck {
    --deck-inset: var(--gutter-page);
    --deck-bar: var(--tap-min);

    display: grid;
    grid-template-rows: 1fr auto;
    block-size: 100dvh;
    background-color: var(--bg-canvas);
    color: var(--fg-default);
    font: var(--type-body);
  }

  .deck__stage {
    display: grid;
    align-items: start;
    overflow-y: auto;
    padding: var(--deck-inset);
  }

  .stack {
    display: flex;
    flex-direction: column;
    gap: var(--gap-separate);
  }
}

@layer components {
  /* ==================================================================
     1. SOCKET BLOCK — this deck's Tier-3 API. Re-point any of these on
        .deck to re-skin the presentation without touching a rule.
     ================================================================== */
  .slide {
    --slide-inset: var(--pad-card-lg);
    --slide-gap: var(--gap-separate);
    --slide-bg: var(--bg-surface);
    --slide-fg: var(--fg-default);
    --slide-radius: var(--radius-xl);
    --slide-border: var(--border-subtle);
    --slide-elevation: var(--elevation-card);
    --slide-measure: var(--measure-prose);
    --slide-motion: var(--motion-enter);

  /* ==================================================================
     2. STRUCTURE — true of every slide, whatever it contains.
     ================================================================== */
    display: none;
    flex-direction: column;
    gap: var(--slide-gap);
    inline-size: min(100%, var(--width-content));
    margin-inline: auto;
    padding: var(--slide-inset);
    border: var(--stroke-default) solid var(--slide-border);
    border-radius: var(--slide-radius);
    background-color: var(--slide-bg);
    color: var(--slide-fg);
    box-shadow: var(--slide-elevation);
  }

  .slide[data-state="current"] {
    display: flex;
    animation: slide-in var(--slide-motion);
  }

  @media (prefers-reduced-motion: reduce) {
    .slide[data-state="current"] { animation: none; }
  }

  @keyframes slide-in {
    from { opacity: 0; }
    to   { opacity: 1; }
  }

  /* ==================================================================
     3. VARIANTS — re-point sockets only, never add structure.
     ================================================================== */
  .slide[data-kind="cover"] {
    --slide-inset: var(--pad-card-lg);
    --slide-bg: var(--bg-inverse);
    --slide-fg: var(--fg-on-inverse);
    --slide-border: transparent;
    --slide-elevation: var(--elevation-raised);
  }

  .slide[data-kind="appendix"],
  .slide[data-kind="provenance"] {
    --slide-bg: var(--bg-sunken);
    --slide-elevation: var(--elevation-flat);
  }

  /* ==================================================================
     4. STATES — the deck has three that matter: current, notes-on,
        and print. Everything else is a document, not an app.
     ================================================================== */
  .slide:focus-visible {
    outline: var(--stroke-focus) solid transparent;
    box-shadow: var(--elevation-focus);
  }

  /* ==================================================================
     5. PARTS — addressed by class, never by element.
     ================================================================== */
  .slide__head {
    display: flex;
    flex-direction: column;
    gap: var(--gap-tight);
  }

  .slide__kicker {
    font: var(--type-label);
    letter-spacing: var(--tracking-caps);
    text-transform: uppercase;
    color: var(--fg-accent);
  }

  .slide[data-kind="cover"] .slide__kicker { color: var(--fg-on-inverse); }

  .slide__title {
    font: var(--type-h2);
    letter-spacing: var(--tracking-tight);
    color: var(--fg-strong);
  }

  .slide[data-kind="cover"] .slide__title {
    font: var(--type-h1);
    color: var(--fg-on-inverse);
  }

  .slide__body {
    display: flex;
    flex-direction: column;
    gap: var(--gap-separate);
  }

  .slide__foot {
    display: flex;
    gap: var(--gap-related);
    justify-content: space-between;
    padding-block-start: var(--pad-block-md);
    border-block-start: var(--stroke-hairline) solid var(--border-subtle);
    font: var(--type-label);
    color: var(--fg-subtle);
  }

  .lede {
    max-inline-size: var(--measure-prose);
    font: var(--type-lead);
    color: var(--fg-default);
  }

  .slide[data-kind="cover"] .lede { color: var(--fg-on-inverse); }

  .body {
    max-inline-size: var(--measure-prose);
    font: var(--type-body);
  }

  .list {
    display: flex;
    flex-direction: column;
    gap: var(--gap-tight);
    max-inline-size: var(--measure-prose);
    padding-inline-start: var(--pad-inline-md);
    font: var(--type-body);
  }

  .code {
    padding: var(--pad-block-xs) var(--pad-inline-xs);
    border-radius: var(--radius-sm);
    background-color: var(--bg-sunken);
    font: var(--type-code);
  }

  /* -- .dtable — decisions as rows, because a decision is a row ------ */
  .dtable {
    --dtable-cell-block: var(--pad-block-md);
    --dtable-cell-inline: var(--pad-inline-md);

    inline-size: 100%;
    border-collapse: collapse;
    font: var(--type-ui);
    text-align: start;
  }

  .dtable th,
  .dtable td {
    padding: var(--dtable-cell-block) var(--dtable-cell-inline);
    border-block-end: var(--stroke-hairline) solid var(--border-subtle);
    vertical-align: top;
    text-align: start;
  }

  .dtable th {
    font: var(--type-label);
    letter-spacing: var(--tracking-wide);
    text-transform: uppercase;
    color: var(--fg-muted);
  }

  /* -- .dlist — one decision, in the five-part shape ----------------- */
  /* --dlist-key is a socket with a default, so a container (the help
     panel) can narrow the key column without restyling the list. */
  .dlist {
    display: grid;
    gap: var(--gap-grouped);
  }

  .dlist__row {
    display: grid;
    grid-template-columns: var(--dlist-key, minmax(auto, var(--measure-narrow))) 1fr;
    gap: var(--gap-related);
    align-items: baseline;
  }

  .dlist__key {
    font: var(--type-label);
    letter-spacing: var(--tracking-wide);
    text-transform: uppercase;
    color: var(--fg-muted);
  }

  .dlist__val {
    font: var(--type-body);
    color: var(--fg-default);
  }

  /* -- .options — what was rejected, at two emphases ------------------ */
  .options {
    --options-bg: var(--bg-sunken);
    --options-fg: var(--fg-muted);
    --options-border: transparent;

    display: flex;
    flex-direction: column;
    gap: var(--gap-tight);
    padding: var(--pad-well);
    border-inline-start: var(--stroke-thick) solid var(--options-border);
    border-radius: var(--radius-md);
    background-color: var(--options-bg);
    color: var(--options-fg);
  }

  .options[data-emphasis="strong"] {
    --options-fg: var(--fg-default);
    --options-border: var(--border-accent);
  }

  .options__title {
    font: var(--type-label);
    letter-spacing: var(--tracking-wide);
    text-transform: uppercase;
  }

  /* -- .metrics / .metric — a number and its meaning ------------------ */
  .metrics {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(var(--measure-narrow), 1fr));
    gap: var(--gap-grouped);
  }

  .metric {
    --metric-bg: var(--bg-sunken);
    --metric-accent: var(--fg-accent);

    display: flex;
    flex-direction: column;
    gap: var(--gap-fused);
    padding: var(--pad-card);
    border-radius: var(--radius-lg);
    background-color: var(--metric-bg);
  }

  .metric__value {
    font: var(--type-h1);
    letter-spacing: var(--tracking-tighter);
    color: var(--metric-accent);
  }

  .metric__label {
    font: var(--type-ui);
    color: var(--fg-default);
  }

  .metric__foot {
    font: var(--type-label);
    color: var(--fg-subtle);
  }

  .num { font-variant-numeric: tabular-nums; }

  /* -- .cards -------------------------------------------------------- */
  .cards {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(var(--measure-narrow), 1fr));
    gap: var(--gap-grouped);
  }

  .card {
    display: flex;
    flex-direction: column;
    gap: var(--gap-tight);
    padding: var(--pad-card);
    border: var(--stroke-default) solid var(--border-subtle);
    border-radius: var(--radius-lg);
    background-color: var(--bg-surface);
  }

  .card__title {
    font: var(--type-h4);
    color: var(--fg-strong);
  }

  /* -- .callout ------------------------------------------------------ */
  .callout {
    --callout-bg: var(--bg-sunken);
    --callout-border: var(--border-default);

    display: flex;
    flex-direction: column;
    gap: var(--gap-tight);
    padding: var(--pad-card);
    border-inline-start: var(--stroke-thick) solid var(--callout-border);
    border-radius: var(--radius-md);
    background-color: var(--callout-bg);
  }

  .callout[data-tone="open"] { --callout-border: var(--border-accent); }
  .callout[data-tone="gap"] { --callout-border: var(--fg-warning); }

  .callout__title {
    font: var(--type-h4);
    color: var(--fg-strong);
  }

  /* -- .shot / .compare ---------------------------------------------- */
  .shots,
  .compare {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(var(--measure-narrow), 1fr));
    gap: var(--gap-grouped);
  }

  .shot {
    display: flex;
    flex-direction: column;
    gap: var(--gap-tight);
  }

  .shot__img {
    inline-size: 100%;
    block-size: auto;
    border: var(--stroke-default) solid var(--border-subtle);
    border-radius: var(--radius-lg);
    background-color: var(--bg-sunken);
  }

  .shot__cap {
    font: var(--type-label);
    color: var(--fg-muted);
  }

  /* -- .notes — presenter notes, toggled, never printed by accident --- */
  .notes {
    display: none;
    flex-direction: column;
    gap: var(--gap-tight);
    padding: var(--pad-card);
    border-radius: var(--radius-lg);
    background-color: var(--bg-selected);
    font: var(--type-ui);
    color: var(--fg-default);
  }

  .deck[data-notes="on"] .notes { display: flex; }

  .notes__title {
    font: var(--type-label);
    letter-spacing: var(--tracking-caps);
    text-transform: uppercase;
    color: var(--fg-accent);
  }

  .gap {
    display: none;
    gap: var(--gap-tight);
    padding: var(--pad-well);
    border-inline-start: var(--stroke-thick) solid var(--fg-warning);
    border-radius: var(--radius-md);
    background-color: var(--bg-sunken);
    font: var(--type-ui);
    color: var(--fg-warning);
  }

  .deck[data-notes="on"] .gap { display: flex; flex-direction: column; }

  /* -- .bar — the chrome --------------------------------------------- */
  .bar {
    --bar-bg: var(--bg-surface);

    display: flex;
    gap: var(--gap-related);
    align-items: center;
    justify-content: space-between;
    padding: var(--pad-block-sm) var(--pad-inline-md);
    border-block-start: var(--stroke-hairline) solid var(--border-subtle);
    background-color: var(--bar-bg);
    font: var(--type-label);
    color: var(--fg-muted);
  }

  .bar__group {
    display: flex;
    gap: var(--gap-tight);
    align-items: center;
  }

  .bar__btn {
    --btn-bg: var(--bg-surface);
    --btn-fg: var(--fg-default);
    --btn-overlay: transparent;

    display: inline-flex;
    gap: var(--gap-fused);
    align-items: center;
    justify-content: center;
    min-inline-size: var(--tap-min);
    min-block-size: var(--tap-min);
    padding: var(--pad-block-sm) var(--pad-inline-sm);
    border: var(--stroke-default) solid var(--border-default);
    border-radius: var(--radius-md);
    background-color: var(--btn-bg);
    background-image: linear-gradient(var(--btn-overlay), var(--btn-overlay));
    color: var(--btn-fg);
    font: var(--type-ui);
    cursor: pointer;
    transition: background-color var(--motion-hover),
                border-color var(--motion-hover);
  }

  .bar__btn:hover:not(:disabled) { --btn-overlay: var(--bg-hover); }
  .bar__btn:active:not(:disabled) { --btn-overlay: var(--bg-active); }

  .bar__btn:focus-visible {
    outline: var(--stroke-focus) solid transparent;
    box-shadow: var(--elevation-focus);
  }

  .bar__btn:disabled {
    --btn-bg: var(--bg-disabled);
    --btn-fg: var(--fg-disabled);
    cursor: not-allowed;
  }

  .bar__btn[aria-pressed="true"] {
    --btn-bg: var(--bg-selected);
    --btn-fg: var(--fg-accent);
  }

  .progress {
    --progress-track: var(--bg-sunken);
    --progress-fill: var(--bg-accent);

    position: relative;
    flex: 1;
    block-size: var(--stroke-thick);
    border-radius: var(--radius-full);
    background-color: var(--progress-track);
  }

  /* scaleX, not inline-size: a width transition relayouts every frame and
     drags its siblings with it. The scale factor arrives as a custom
     property, which is the one thing an inline style may legally set. */
  .progress__fill {
    --progress-scale: 0;

    position: absolute;
    inset-block: 0;
    inset-inline: 0;
    transform: scaleX(var(--progress-scale));
    transform-origin: left center;
    border-radius: var(--radius-full);
    background-color: var(--progress-fill);
    transition: transform var(--motion-enter);
  }

  /* -- .help — the keyboard map -------------------------------------- */
  .help {
    position: fixed;
    inset: 0;
    z-index: var(--z-modal);
    display: none;
    place-items: center;
    padding: var(--gutter-page);
    background-color: var(--bg-inverse);
    color: var(--fg-on-inverse);
  }

  .deck[data-help="open"] .help { display: grid; }

  .help__panel {
    /* The panel is --width-form wide; the list's default key column would
       leave each answer a few words' width. Split it evenly instead. */
    --dlist-key: minmax(0, 1fr);

    display: flex;
    flex-direction: column;
    gap: var(--gap-grouped);
    max-inline-size: var(--width-form);
    padding: var(--pad-card-lg);
    border-radius: var(--radius-xl);
    background-color: var(--bg-surface);
    color: var(--fg-default);
    box-shadow: var(--elevation-modal);
  }

  /* A hairline is the smallest length the system has a name for, used here
     as a 1px box so the element is announced and never occupies layout.
     --stroke-* is a primitive with no Tier-2 role, so a component reading it
     is correct rather than a Law 6 violation. */
  .visually-hidden {
    position: absolute;
    inline-size: var(--stroke-hairline);
    block-size: var(--stroke-hairline);
    overflow: hidden;
    clip-path: inset(50%);
    white-space: nowrap;
  }

  /* ==================================================================
     PRINT — one slide per page, notes underneath, chrome gone. This is
     the PDF everyone asks for by email an hour after the meeting.
     ================================================================== */
  @media print {
    .deck {
      display: block;
      block-size: auto;
      background-color: var(--bg-surface);
    }

    .deck__stage {
      display: block;
      overflow: visible;
      padding: 0;
    }

    .slide {
      display: flex;
      break-after: page;
      break-inside: avoid;
      border-color: transparent;
      border-radius: var(--radius-none);
      box-shadow: var(--elevation-flat);
    }

    .slide[data-state="offscreen"] { display: flex; }

    .bar,
    .help { display: none; }

    .notes {
      display: flex;
      background-color: var(--bg-sunken);
      break-inside: avoid;
    }

    .gap { display: none; }

    .shot__img { break-inside: avoid; }
  }
}
"""

DECK_JS = """(function () {
  "use strict";
  var deck = document.querySelector(".deck");
  var slides = Array.prototype.slice.call(document.querySelectorAll(".slide"));
  var counter = document.querySelector("[data-deck-counter]");
  var fill = document.querySelector(".progress__fill");
  var live = document.querySelector("[data-deck-live]");
  var prevBtn = document.querySelector("[data-deck-prev]");
  var nextBtn = document.querySelector("[data-deck-next]");
  var notesBtn = document.querySelector("[data-deck-notes]");
  var fsBtn = document.querySelector("[data-deck-fullscreen]");
  var total = slides.length;
  var index = 0;

  function clamp(i) { return Math.max(0, Math.min(total - 1, i)); }

  function show(i, updateHash, moveFocus) {
    index = clamp(i);
    for (var n = 0; n < total; n++) {
      var on = n === index;
      slides[n].dataset.state = on ? "current" : "offscreen";
      slides[n].setAttribute("aria-hidden", on ? "false" : "true");
    }
    if (counter) { counter.textContent = (index + 1) + " / " + total; }
    if (fill) {
      fill.style.setProperty("--progress-scale", (index + 1) / total);
    }
    if (prevBtn) { prevBtn.disabled = index === 0; }
    if (nextBtn) { nextBtn.disabled = index === total - 1; }
    if (live) {
      live.textContent = "Slide " + (index + 1) + " of " + total + ": " +
        (slides[index].getAttribute("data-title") || "");
    }
    if (updateHash !== false) {
      try { history.replaceState(null, "", "#s" + (index + 1)); } catch (e) {}
    }
    if (moveFocus !== false) { slides[index].focus({ preventScroll: true }); }
    slides[index].scrollTop = 0;
  }

  function next() { if (index < total - 1) { show(index + 1); } }
  function prev() { if (index > 0) { show(index - 1); } }

  function toggleNotes(force) {
    var on = typeof force === "boolean"
      ? force : deck.dataset.notes !== "on";
    deck.dataset.notes = on ? "on" : "off";
    if (notesBtn) { notesBtn.setAttribute("aria-pressed", on ? "true" : "false"); }
  }

  function toggleFullscreen() {
    var el = document.documentElement;
    if (!document.fullscreenElement && el.requestFullscreen) {
      el.requestFullscreen().catch(function () {});
    } else if (document.exitFullscreen) {
      document.exitFullscreen().catch(function () {});
    }
  }

  function toggleHelp(force) {
    var on = typeof force === "boolean"
      ? force : deck.dataset.help !== "open";
    deck.dataset.help = on ? "open" : "closed";
  }

  function fromHash() {
    var m = /^#s(\\d+)$/.exec(window.location.hash || "");
    return m ? parseInt(m[1], 10) - 1 : 0;
  }

  document.addEventListener("keydown", function (event) {
    if (event.metaKey || event.ctrlKey || event.altKey) { return; }
    var t = event.target;
    if (t && (t.isContentEditable ||
        /^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName || ""))) { return; }
    var key = event.key;
    if (key === "ArrowRight" || key === "ArrowDown" || key === "PageDown" ||
        key === " " || key === "Spacebar") {
      event.preventDefault(); next();
    } else if (key === "ArrowLeft" || key === "ArrowUp" || key === "PageUp" ||
               key === "Backspace") {
      event.preventDefault(); prev();
    } else if (key === "Home") {
      event.preventDefault(); show(0);
    } else if (key === "End") {
      event.preventDefault(); show(total - 1);
    } else if (key === "n" || key === "N") {
      event.preventDefault(); toggleNotes();
    } else if (key === "f" || key === "F") {
      event.preventDefault(); toggleFullscreen();
    } else if (key === "?" || key === "h" || key === "H") {
      event.preventDefault(); toggleHelp();
    } else if (key === "Escape") {
      toggleHelp(false);
    }
  });

  if (prevBtn) { prevBtn.addEventListener("click", prev); }
  if (nextBtn) { nextBtn.addEventListener("click", next); }
  if (notesBtn) { notesBtn.addEventListener("click", function () { toggleNotes(); }); }
  if (fsBtn) { fsBtn.addEventListener("click", toggleFullscreen); }
  var helpClose = document.querySelector("[data-deck-help-close]");
  if (helpClose) {
    helpClose.addEventListener("click", function () { toggleHelp(false); });
  }
  window.addEventListener("hashchange", function () {
    show(fromHash(), false, false);
  });
  window.addEventListener("beforeprint", function () { toggleHelp(false); });

  show(fromHash(), false, false);
})();
"""


def render_slide(slide: Slide, number: int, total: int, meta: dict[str, str]) -> str:
    head = [f"<p class='slide__kicker'>{esc(slide.kicker)}</p>"] if slide.kicker else []
    head.append(f"<h2 class='slide__title'>{inline(slide.title)}</h2>")
    notes_html = ""
    if slide.notes:
        items = "".join(f"<p class='body'>{inline(n)}</p>" for n in slide.notes)
        notes_html = (f"<div class='notes'><p class='notes__title'>"
                      f"Presenter notes</p>{items}</div>")
    gap_html = ""
    if slide.gaps:
        items = "".join(f"<li>{inline(g)}</li>" for g in slide.gaps)
        gap_html = (f"<div class='gap'><p class='notes__title'>Gaps — fix before "
                    f"you present</p><ul class='list'>{items}</ul></div>")
    foot = (f"<div class='slide__foot'><span>{esc(meta.get('project', ''))}</span>"
            f"<span>{number} / {total}</span></div>")
    return (
        f"<section class='slide' data-kind='{esc(slide.kind)}' "
        f"data-state='offscreen' data-title=\"{esc(slide.title)}\" "
        f"aria-hidden='true' tabindex='-1' "
        f"aria-label=\"Slide {number} of {total}: {esc(slide.title)}\">"
        f"<header class='slide__head'>{''.join(head)}</header>"
        f"<div class='slide__body'>{''.join(slide.blocks)}</div>"
        f"{notes_html}{gap_html}{foot}</section>")


def render_html(plan: list[Slide], inp: Inputs, audience: str,
                tokens_css: str) -> str:
    meta = inp.log.meta
    title = meta.get("project") or meta.get("title") or "Design review"
    total = len(plan)
    slides = "".join(render_slide(s, i + 1, total, meta)
                     for i, s in enumerate(plan))
    help_rows = [
        ("→ / ↓ / space / Page Down", "next slide"),
        ("← / ↑ / backspace / Page Up", "previous slide"),
        ("Home / End", "first / last slide"),
        ("N", "presenter notes and gap markers"),
        ("F", "fullscreen"),
        ("? or H", "this panel"),
        ("Ctrl/Cmd + P", "print to PDF, one slide per page"),
    ]
    help_html = "".join(
        f"<div class='dlist__row'><dt class='dlist__key'>{esc(k)}</dt>"
        f"<dd class='dlist__val'>{esc(v)}</dd></div>" for k, v in help_rows)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="generator" content="client-presentation-builder/build_presentation.py">
<meta name="deck-audience" content="{esc(audience)}">
<title>{esc(title)}</title>
<style data-deck-css="tokens">
@layer reset, tokens, base, layout, components, utilities, overrides;
{tokens_css}
</style>
<style data-deck-css="deck-components">
{DECK_CSS}
</style>
</head>
<body>
<div class="deck" data-notes="off" data-help="closed"
     data-audience="{esc(audience)}">
  <main class="deck__stage">
    {slides}
  </main>
  <nav class="bar" aria-label="Slide navigation">
    <div class="bar__group">
      <button class="bar__btn" type="button" data-deck-prev>&larr;<span
        class="visually-hidden"> previous slide</span></button>
      <button class="bar__btn" type="button" data-deck-next>&rarr;<span
        class="visually-hidden"> next slide</span></button>
      <span data-deck-counter>1 / {total}</span>
    </div>
    <div class="progress"><div class="progress__fill"></div></div>
    <div class="bar__group">
      <button class="bar__btn" type="button" data-deck-notes
        aria-pressed="false">Notes</button>
      <button class="bar__btn" type="button" data-deck-fullscreen>Full</button>
    </div>
  </nav>
  <div class="help" role="dialog" aria-modal="true"
       aria-label="Keyboard shortcuts">
    <div class="help__panel">
      <h2 class="slide__title">Keyboard</h2>
      <dl class="dlist">{help_html}</dl>
      <button class="bar__btn" type="button" data-deck-help-close>Close</button>
    </div>
  </div>
  <p class="visually-hidden" role="status" aria-live="polite" data-deck-live></p>
</div>
<script>
{DECK_JS}
</script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Rendering — speaker notes and the dry-run outline
# ---------------------------------------------------------------------------

def render_notes(plan: list[Slide], inp: Inputs, audience: str) -> str:
    meta = inp.log.meta
    out = [f"# Speaker notes — {meta.get('project') or meta.get('title') or 'Deck'}",
           "",
           f"**Audience:** {audience}  ",
           f"**Slides:** {len(plan)}  ",
           f"**Generated:** {_dt.date.today().isoformat()}",
           "",
           "Read the room, not the notes. These exist so that the sentence you "
           "need under pressure already exists in writing.",
           ""]
    for i, s in enumerate(plan, 1):
        out.append(f"## {i}. {s.title}" + (f" — {s.kicker}" if s.kicker else ""))
        out.append("")
        for n in s.notes:
            out.append("- " + " ".join(n.split()))
        if s.gaps:
            out.append("")
            out.append("**Gaps:**")
            for g in s.gaps:
                out.append("- [ ] " + " ".join(g.split()))
        out.append("")
    all_gaps = [(i, g) for i, s in enumerate(plan, 1) for g in s.gaps]
    out.append("---")
    out.append("")
    out.append("## Before you walk in")
    out.append("")
    if all_gaps:
        for i, g in all_gaps:
            out.append(f"- [ ] (slide {i}) " + " ".join(g.split()))
    else:
        out.append("- No gaps recorded. Rehearse the objections anyway: "
                   "`references/objection-handling.md`.")
    out.append("")
    return "\n".join(out)


def render_outline(plan: list[Slide], inp: Inputs, audience: str) -> str:
    out = [f"Slide plan — audience: {audience} — {len(plan)} slides", ""]
    for i, s in enumerate(plan, 1):
        kicker = f"  [{s.kicker}]" if s.kicker else ""
        out.append(f"{i:>3}. {s.kind:<17} {s.title}{kicker}")
        for line in s.outline:
            out.append(f"      · {line}")
        for g in s.gaps:
            out.append(f"      ! GAP  {g}")
    ranked = rank_decisions(inp.log.decisions, audience)
    out.append("")
    out.append("Decision ranking for this audience (open questions excluded):")
    for n, d in enumerate(ranked, 1):
        tags = ",".join(d.tags) or "-"
        aud = ",".join(d.audiences) or "-"
        out.append(f"  {n:>2}. {d.ident:<5} {d.title[:52]:<54} "
                   f"audience={aud} tags={tags}")
    opens = _open_decisions(inp.log)
    if opens:
        out.append("")
        out.append("Held back as open questions (never presented as rationale):")
        for d in opens:
            out.append(f"      {d.ident:<5} {d.title[:60]}  [{d.status}]")
    out.append("")
    gaps = [g for s in plan for g in s.gaps]
    out.append(f"{len(gaps)} gap(s) the generator could not fill from the inputs.")
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------
# CSS emission (so the deck can be audited by the gate it is arguing for)
# ---------------------------------------------------------------------------

def emit_css(directory: Path, tokens_css: str) -> list[Path]:
    directory.mkdir(parents=True, exist_ok=True)
    tokens_path = directory / "tokens.css"
    deck_path = directory / "deck-components.css"
    tokens_path.write_text(
        "@layer reset, tokens, base, layout, components, utilities, overrides;\n"
        + tokens_css, encoding="utf-8")
    deck_path.write_text(DECK_CSS, encoding="utf-8")
    return [tokens_path, deck_path]


def find_tokens(explicit: str | None) -> tuple[str, str]:
    """Return (css, provenance). The client's own tokens beat the bundled copy."""
    candidates: list[Path] = []
    if explicit:
        p = Path(explicit)
        if not p.exists():
            raise BuildError(f"--tokens {p} does not exist")
        candidates.append(p)
    candidates.append(SKILL_ROOT / "assets" / "deck-tokens.css")
    candidates.append(SKILL_ROOT.parent / "web-design-studio" / "assets" /
                      "starter" / "styles" / "tokens.css")
    for c in candidates:
        if c.exists():
            return c.read_text(encoding="utf-8"), str(c)
    raise BuildError(
        "no tokens.css found. Pass --tokens path/to/tokens.css — the deck is "
        "built on the same token contract as the work it presents.")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="python -m scripts.build_presentation",
        description="Assemble a client deck from a decision log and the "
                    "evidence the suite's gates already produced.",
        epilog="You are not presenting a design. You are presenting a set of "
               "decisions.")
    ap.add_argument("decisions", help="DECISION_LOG.md (see assets/)")
    ap.add_argument("--audience", choices=AUDIENCES, default="client",
                    help="who is in the room; changes emphasis AND order "
                         "(default: client)")
    ap.add_argument("--audit", metavar="FILE",
                    help="`audit_design.py --json` output")
    ap.add_argument("--perf", metavar="FILE",
                    help="`perf_audit.py --json` output")
    ap.add_argument("--a11y", metavar="FILE",
                    help="axe-core style accessibility results JSON")
    ap.add_argument("--defence", metavar="FILE",
                    help="`critique_report.py --format defence` markdown")
    ap.add_argument("--screenshots", metavar="DIR",
                    help="directory of images, inlined as data URIs; "
                         "`x--before.png` + `x--after.png` pair automatically")
    ap.add_argument("-o", "--out", metavar="FILE", default="deck.html",
                    help="deck output path (default: deck.html)")
    ap.add_argument("--notes", metavar="FILE",
                    help="also write speaker notes as markdown")
    ap.add_argument("--emit-css", metavar="DIR",
                    help="write the deck's CSS out so `audit_design.py "
                         "--strict DIR` can prove it is on the system")
    ap.add_argument("--tokens", metavar="FILE",
                    help="tokens.css to build the deck on (default: the "
                         "bundled copy; pass the client's for their brand)")
    ap.add_argument("--max-decisions", type=int, default=5, metavar="N",
                    help="headline decisions for client/creative-director "
                         "(default: 5; a team gets all of them)")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the slide plan and the gaps; write nothing")
    args = ap.parse_args(argv)

    if args.max_decisions < 1:
        print("build_presentation: --max-decisions must be at least 1",
              file=sys.stderr)
        return 2

    try:
        log_path = Path(args.decisions)
        if not log_path.exists():
            raise BuildError(
                f"{log_path} does not exist. Start from "
                f"assets/DECISION_LOG.md — the deck is assembled from it, "
                f"not invented the night before.")
        log = parse_decision_log(log_path.read_text(encoding="utf-8"), log_path)
        if not log.decisions:
            raise BuildError(
                f"{log_path} contains no decisions. The parser expects "
                f"`## Decisions` followed by `### D1 — Title` blocks with "
                f"`**Constraint:**` / `**Choice:**` fields. See "
                f"assets/DECISION_LOG.md.")
        first_seen: dict[str, int] = {}
        for d in log.decisions:
            if d.ident in first_seen:
                raise BuildError(
                    f"{log_path}: decision {d.ident} appears twice (lines "
                    f"{first_seen[d.ident]} and {d.line}). Give every "
                    f"`### D<n> — Title` block its own number — the deck's "
                    f"appendix and the meeting record refer to decisions by id.")
            first_seen[d.ident] = d.line

        inp = Inputs(log=log)
        if args.audit:
            inp.audit = load_audit(Path(args.audit))
        if args.perf:
            inp.perf = load_perf(Path(args.perf))
        if args.a11y:
            inp.a11y = load_a11y(Path(args.a11y))
        if args.defence:
            inp.defence = load_defence(Path(args.defence))
        if args.screenshots:
            inp.shots, inp.pairs = load_screenshots(Path(args.screenshots))

        tokens_css, tokens_from = find_tokens(args.tokens)
    except BuildError as exc:
        print(f"build_presentation: {exc}", file=sys.stderr)
        return 2

    plan = build_plan(inp, args.audience, args.max_decisions)

    if args.dry_run:
        sys.stdout.write(render_outline(plan, inp, args.audience))
        return 0

    out_path = Path(args.out)
    html_text = render_html(plan, inp, args.audience, tokens_css)
    size = len(html_text.encode("utf-8"))
    written = [f"{out_path} ({human_bytes(size)})"]
    # All three outputs get the same treatment: missing folders are created,
    # and a path that cannot be written is a bad invocation (exit 2), not a
    # traceback.
    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(html_text, encoding="utf-8")
        if args.notes:
            notes_path = Path(args.notes)
            notes_path.parent.mkdir(parents=True, exist_ok=True)
            notes_path.write_text(render_notes(plan, inp, args.audience),
                                  encoding="utf-8")
            written.append(args.notes)
        if args.emit_css:
            for p in emit_css(Path(args.emit_css), tokens_css):
                written.append(str(p))
    except OSError as exc:
        print(f"build_presentation: cannot write {exc.filename or args.out}: "
              f"{exc.strerror or exc}", file=sys.stderr)
        return 2

    gaps = [(i, g) for i, s in enumerate(plan, 1) for g in s.gaps]
    print(f"build_presentation: {len(plan)} slides for `{args.audience}` "
          f"from {len(log.decisions)} logged decision(s).")
    print(f"  tokens: {tokens_from}")
    print(f"  wrote:  {', '.join(written)}")
    if inp.pairs:
        print(f"  paired: {len(inp.pairs)} before/after comparison(s)")
    if size > 12_000_000:
        print(f"\n  The deck is {human_bytes(size)}. Screenshots are inlined so "
              f"the file works with no network and survives being emailed — but "
              f"past about 10 MB it will not survive an email gateway. Export "
              f"the screenshots at the size they are shown, not at 3x retina.")
    if gaps:
        print(f"\n{len(gaps)} gap(s) the inputs could not fill — press N in the "
              f"deck to see them in place:")
        for i, g in gaps:
            print(f"  slide {i:>2}  {g}")
    if inp.defence and inp.defence.blockers:
        print("\nDo not present yet. The defence sheet lists blocking items:",
              file=sys.stderr)
        for b in inp.defence.blockers:
            print(f"  - {b}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    # A Windows pipe (git hook, CI, `> file`) defaults to the ANSI code page,
    # where printing →, Δ or ✓ raises UnicodeEncodeError. Consoles and
    # Claude Code already use UTF-8 and are left alone.
    for _stream in (sys.stdout, sys.stderr):
        if getattr(_stream, "encoding", "utf-8").lower() not in ("utf-8", "utf8"):
            _stream.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
