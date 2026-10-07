#!/usr/bin/env python3
"""Turn critique findings into the three artifacts a critique actually ships as.

A critique that lives in someone's head is not a deliverable. This takes
findings as JSON — hand-written observations, optionally merged with machine
findings from ``audit_design.py --json`` — and emits one of:

    critique   a ranked markdown critique, written to be acted on
    triage     one terse line per finding, for a ticket tracker
    defence    the decisions you must be able to justify out loud

plus ``--summary``, which prints the top three things to fix and nothing else,
because three is what actually gets fixed before the meeting.

USAGE
-----
    python -m scripts.critique_report findings.json
    python -m scripts.critique_report findings.json --format triage
    python -m scripts.critique_report findings.json --format defence
    python -m scripts.critique_report findings.json --summary

    # Merge the mechanical gate in as conformance-layer findings:
    python -m scripts.audit_design src/ --json > audit.json
    python -m scripts.critique_report findings.json --audit audit.json

    # Read findings from stdin:
    cat findings.json | python -m scripts.critique_report -

    # Fail a pre-presentation check:
    python -m scripts.critique_report findings.json --fail-on major

FINDINGS SCHEMA
---------------
Either a bare JSON list of findings, or an object::

    {
      "subject":   "Acme pricing page, desktop + 390px",   # optional
      "reviewer":  "self",                                  # optional
      "date":      "2026-09-17",                            # optional
      "decisions": [                                        # optional, for --format defence
        {"decision":  "Hero has no image",
         "rationale": "The proposition is a number; a photo would dilute it",
         "alternative": "Product screenshot, rejected — it dates the page",
         "cost":      "Less scroll-stopping in a feed"}
      ],
      "findings":  [ ... ]
    }

A finding::

    {
      "layer":      "hierarchy",        # REQUIRED, one of the ten run-order layers
      "severity":   "major",            # REQUIRED: blocking | major | minor | taste
      "title":      "Two competing primary actions in the hero",
      "mechanism":  "Both buttons use --bg-accent at the same size, so neither "
                    "wins the first fixation; the eye lands, compares, and stalls.",
      "evidence":   "hero.css:41, hero.css:58 — identical background and padding",
      "fix":        "Demote the second to the ghost variant; accent means "
                    "'the one action' and spending it twice costs the signal.",
      "confidence": "confirmed",        # confirmed | likely | suspected (default likely)
      "is_taste":   false,              # true == preference, not defect
      "status":     "open",             # open | fixed (default open)
      "defend":     false,              # carry onto the defence sheet even when fixed
      "covers":     ["important"],      # audit rules this finding owns (merge)
      "id":         "hero-two-primaries",
      "ref":        "review-checklist 5.6"
    }

Merging --audit: a machine group is folded into a hand finding only when the
hand finding claims it — the rule id in `covers`, or written in backticks
(`important`). An ordinary word never folds a rule, and a rule raised with
--audit-blocking is never folded. Every merge is reported on stderr.

Layers, in the order a reviewer's attention moves — a finding at layer 1 can
make every finding below it moot, so they rank above them:

    premise · first-impression · hierarchy · structure · craft · color ·
    states · interaction · conformance · presentation

Severity rubric:

    blocking  it breaks — unusable, unreadable, inaccessible, or wrong page
    major     it misleads — the user reads the wrong thing as the point
    minor     it cheapens — reads as almost-professional
    taste     it merely differs from preference (always labelled as taste)

A finding marked ``"status": "fixed"`` stays in the critique, labelled fixed,
but leaves "Fix these three first", --summary, --fail-on and the defence
sheet's "do not present" list; ``defend: true`` keeps it on the sheet's known
flaws, labelled fixed.

Exit status: 0; 1 when an open finding at or above ``--fail-on`` survives;
2 on bad input or an ``--out`` that cannot be written.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Vocabulary
# ---------------------------------------------------------------------------

LAYERS: list[tuple[str, str]] = [
    ("premise", "Premise"),
    ("first-impression", "First impression"),
    ("hierarchy", "Hierarchy"),
    ("structure", "Structure and rhythm"),
    ("craft", "Craft"),
    ("color", "Color and contrast"),
    ("states", "States and edges"),
    ("interaction", "Interaction and motion"),
    ("conformance", "Conformance"),
    ("presentation", "Presentation readiness"),
]
LAYER_ORDER = {name: i for i, (name, _) in enumerate(LAYERS)}
LAYER_LABEL = dict(LAYERS)

LAYER_ALIASES = {
    "brief": "premise", "problem": "premise", "0": "premise",
    "firstimpression": "first-impression", "first": "first-impression",
    "squint": "first-impression", "impression": "first-impression",
    "hierarchy": "hierarchy", "emphasis": "hierarchy",
    "structureandrhythm": "structure", "rhythm": "structure",
    "grouping": "structure", "layout": "structure", "alignment": "structure",
    "craft": "craft", "detail": "craft", "spacing": "craft", "type": "craft",
    "colorandcontrast": "color", "colour": "color", "contrast": "color",
    "statesandedges": "states", "state": "states", "edges": "states",
    "interactionandmotion": "interaction", "motion": "interaction",
    "a11y": "interaction", "accessibility": "interaction",
    "conformance": "conformance", "audit": "conformance", "tokens": "conformance",
    "presentationreadiness": "presentation", "readiness": "presentation",
    "defence": "presentation", "defense": "presentation",
}

SEVERITIES = ["blocking", "major", "minor", "taste"]
SEVERITY_ORDER = {s: i for i, s in enumerate(SEVERITIES)}
SEVERITY_RUBRIC = {
    "blocking": "it breaks",
    "major": "it misleads",
    "minor": "it cheapens",
    "taste": "it merely differs from preference",
}
SEVERITY_ALIASES = {
    "critical": "blocking", "block": "blocking", "fail": "blocking",
    "high": "major", "error": "major",
    "medium": "minor", "low": "minor", "warning": "minor", "warn": "minor",
    "nit": "taste", "preference": "taste", "opinion": "taste",
}

CONFIDENCES = ["confirmed", "likely", "suspected"]
CONFIDENCE_ORDER = {c: i for i, c in enumerate(CONFIDENCES)}
CONFIDENCE_ALIASES = {
    "certain": "confirmed", "measured": "confirmed", "verified": "confirmed",
    "probable": "likely", "probably": "likely",
    "possible": "suspected", "unsure": "suspected", "hunch": "suspected",
}

# audit_design.py severity -> critique severity. Conformance findings are
# system-integrity failures: an error misleads the next person who reads the
# file, a warning cheapens. Neither is blocking on its own; accessibility and
# contrast failures come in as hand findings, measured.
AUDIT_SEVERITY_MAP = {"error": "major", "warning": "minor"}

LAW_TEXT = {
    "L1": "Law 1 — tokens or nothing; literals live only in tokens.css",
    "L2": "Law 2 — parents own the gaps",
    "L3": "Law 3 — the scale is closed",
    "L4": "Law 4 — one home per component's styles",
    "L5": "Law 5 — layers, not specificity",
    "L6": "Law 6 — semantic before primitive",
    "L7": "Law 7 — density is a dial",
    "L8": "Law 8 — novel patterns pass the gate",
    "L9": "Law 9 — nothing ships un-audited",
}


class CritiqueError(Exception):
    """A problem with the input the caller can fix."""


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

@dataclass
class Finding:
    layer: str
    severity: str
    title: str
    mechanism: str = ""
    evidence: str = ""
    fix: str = ""
    confidence: str = "likely"
    is_taste: bool = False
    defend: bool = False
    id: str = ""
    ref: str = ""
    source: str = "hand"          # hand | machine
    count: int = 1                # machine findings collapse by rule
    also_by_hand: bool = False
    sites: list[str] = field(default_factory=list)   # machine findings only
    status: str = "open"          # open | fixed
    covers: list[str] = field(default_factory=list)  # audit rule ids it owns

    def claims(self, rule: str) -> bool:
        """Does this hand finding take ownership of an audit rule? Only when it
        says so: the id in `covers`, or the id in backticks. A plain-text
        search folded `important` into "the most important plan"."""
        return rule in self.covers or f"`{rule.lower()}`" in self.haystack()

    @property
    def rank(self) -> tuple:
        """Sort key. Severity dominates; within a severity, the earlier layer
        wins, because an earlier finding can make a later one moot. Confidence
        breaks remaining ties — say the sure thing first."""
        return (
            SEVERITY_ORDER[self.severity],
            LAYER_ORDER[self.layer],
            CONFIDENCE_ORDER[self.confidence],
            0 if self.source == "hand" else 1,
            -self.count,
            self.title.lower(),
        )

    @property
    def slug(self) -> str:
        if self.id:
            return self.id
        s = re.sub(r"[^a-z0-9]+", "-", self.title.lower()).strip("-")
        return f"{self.layer}-{s}"[:60]

    def haystack(self) -> str:
        return " ".join(
            (self.title, self.mechanism, self.evidence, self.fix, self.ref)
        ).lower()


# ---------------------------------------------------------------------------
# Normalising input
# ---------------------------------------------------------------------------

def _norm_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def normalise_layer(value: Any, where: str) -> str:
    raw = str(value or "").strip()
    if raw.lower() in LAYER_ORDER:
        return raw.lower()
    key = _norm_key(raw)
    for name in LAYER_ORDER:
        if key == _norm_key(name):
            return name
    for candidate in (key, key.replace("and", "")):
        if candidate in LAYER_ALIASES:
            return LAYER_ALIASES[candidate]
    raise CritiqueError(
        f"{where}: unknown layer {raw!r}. Use one of: "
        + ", ".join(LAYER_ORDER)
    )


def normalise_severity(value: Any, where: str) -> str:
    raw = str(value or "").strip().lower()
    if raw in SEVERITY_ORDER:
        return raw
    if raw in SEVERITY_ALIASES:
        return SEVERITY_ALIASES[raw]
    raise CritiqueError(
        f"{where}: unknown severity {raw!r}. Use one of: "
        + ", ".join(f"{s} ({SEVERITY_RUBRIC[s]})" for s in SEVERITIES)
    )


def normalise_confidence(value: Any, where: str) -> str:
    raw = str(value or "likely").strip().lower()
    if raw in CONFIDENCE_ORDER:
        return raw
    if raw in CONFIDENCE_ALIASES:
        return CONFIDENCE_ALIASES[raw]
    raise CritiqueError(
        f"{where}: unknown confidence {raw!r}. Use one of: " + ", ".join(CONFIDENCES)
    )


def normalise_status(value: Any, where: str) -> str:
    raw = str(value or "open").strip().lower()
    if raw in ("open", "fixed"):
        return raw
    if raw in ("done", "resolved", "closed"):
        return "fixed"
    raise CritiqueError(f"{where}: unknown status {raw!r}. Use open or fixed.")


def _str_list(value: Any) -> list[str]:
    if isinstance(value, str):
        value = value.split(",")
    return [str(v).strip() for v in (value or []) if str(v).strip()]


def parse_finding(raw: Any, where: str) -> Finding:
    if not isinstance(raw, dict):
        raise CritiqueError(f"{where}: expected an object, got {type(raw).__name__}")
    missing = [k for k in ("layer", "severity", "title") if not raw.get(k)]
    if missing:
        raise CritiqueError(
            f"{where}: missing required field(s) {', '.join(missing)}. "
            "Every finding needs at minimum layer, severity and title."
        )
    severity = normalise_severity(raw["severity"], where)
    is_taste = bool(raw.get("is_taste", False))
    if severity == "taste":
        is_taste = True
    if is_taste and severity != "taste":
        # A finding cannot be both a defect and a preference. Preference wins:
        # the whole point of the flag is that it stops you spending a client's
        # attention on something you merely want differently.
        severity = "taste"
    f = Finding(
        layer=normalise_layer(raw["layer"], where),
        severity=severity,
        title=str(raw["title"]).strip(),
        mechanism=str(raw.get("mechanism", "")).strip(),
        evidence=str(raw.get("evidence", "")).strip(),
        fix=str(raw.get("fix", "")).strip(),
        confidence=normalise_confidence(raw.get("confidence"), where),
        is_taste=is_taste,
        defend=bool(raw.get("defend", False)),
        id=str(raw.get("id", "")).strip(),
        ref=str(raw.get("ref", "")).strip(),
        status=normalise_status(raw.get("status"), where),
        covers=_str_list(raw.get("covers")),
        source=str(raw.get("source", "hand")).strip() or "hand",
        count=int(raw.get("count", 1) or 1),
    )
    return f


@dataclass
class Critique:
    subject: str = "Untitled"
    reviewer: str = ""
    date: str = ""
    decisions: list[dict] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)


def load_critique(path: str) -> Critique:
    text = _read(path)
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise CritiqueError(f"{path}: not valid JSON — {exc}") from exc

    if isinstance(data, list):
        items, meta = data, {}
    elif isinstance(data, dict):
        if "findings" not in data:
            raise CritiqueError(
                f"{path}: object form needs a 'findings' key holding a list. "
                "A bare list of findings is also accepted."
            )
        items, meta = data["findings"], data
    else:
        raise CritiqueError(f"{path}: expected a list or an object, got {type(data).__name__}")

    if not isinstance(items, list):
        raise CritiqueError(f"{path}: 'findings' must be a list.")

    findings = [parse_finding(x, f"{path}[{i}]") for i, x in enumerate(items)]
    decisions = meta.get("decisions", []) or []
    if not isinstance(decisions, list):
        raise CritiqueError(f"{path}: 'decisions' must be a list of objects.")
    return Critique(
        subject=str(meta.get("subject", "Untitled")),
        reviewer=str(meta.get("reviewer", "")),
        date=str(meta.get("date", "")),
        decisions=[d for d in decisions if isinstance(d, dict)],
        findings=findings,
    )


def _read(path: str) -> bytes:
    # Bytes, so json.loads detects UTF-16 or a BOM (PowerShell's `>` writes both).
    if path == "-":
        return sys.stdin.buffer.read()
    p = Path(path)
    if not p.exists():
        raise CritiqueError(f"{path}: no such file. Pass a JSON file or '-' for stdin.")
    try:
        return p.read_bytes()
    except OSError as exc:
        raise CritiqueError(f"{path}: cannot read — {exc}") from exc


# ---------------------------------------------------------------------------
# Machine findings: audit_design.py --json
# ---------------------------------------------------------------------------

def load_audit(path: str, escalate: set[str]) -> list[Finding]:
    """Fold ``audit_design.py --json`` output into conformance-layer findings.

    Collapsed by rule, not by occurrence: 'raw-spacing in 14 places' is one
    finding with one system-level fix. Fourteen separate findings would push
    every judgement call off the top of the list, which is exactly the failure
    mode this whole script exists to prevent."""
    text = _read(path)
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise CritiqueError(f"{path}: not valid JSON from audit_design --json — {exc}") from exc
    if not isinstance(data, list):
        raise CritiqueError(
            f"{path}: expected the list produced by 'audit_design.py --json'."
        )

    groups: dict[str, dict] = {}
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            raise CritiqueError(f"{path}[{i}]: expected an audit finding object.")
        rule = str(item.get("rule", "audit")).strip() or "audit"
        law = str(item.get("law", "")).strip()
        sev = str(item.get("severity", "warning")).strip().lower()
        g = groups.setdefault(rule, {
            "rule": rule, "law": law, "severity": sev,
            "messages": [], "fixes": [], "sites": [],
        })
        if SEVERITY_ORDER[AUDIT_SEVERITY_MAP.get(sev, "minor")] < \
           SEVERITY_ORDER[AUDIT_SEVERITY_MAP.get(g["severity"], "minor")]:
            g["severity"] = sev
        msg = str(item.get("message", "")).strip()
        fix = str(item.get("fix", "")).strip()
        if msg and msg not in g["messages"]:
            g["messages"].append(msg)
        if fix and fix not in g["fixes"]:
            g["fixes"].append(fix)
        g["sites"].append(f"{item.get('file', '?')}:{item.get('line', '?')}")

    out: list[Finding] = []
    for rule, g in groups.items():
        sev = "blocking" if rule in escalate else AUDIT_SEVERITY_MAP.get(g["severity"], "minor")
        sites = g["sites"]
        law_line = LAW_TEXT.get(g["law"], g["law"] or "the token contract")
        out.append(Finding(
            layer="conformance",
            severity=sev,
            title=f"{rule} × {len(sites)}",
            mechanism=(
                f"{law_line}. {g['messages'][0] if g['messages'] else ''} "
                "A literal or a mis-tiered token is a decision nobody can find, "
                "so it survives every rebrand, theme and density change unchanged."
            ).strip(),
            evidence=_sites_line(sites),
            fix=g["fixes"][0] if g["fixes"] else "Fix at the system level, not locally.",
            confidence="confirmed",
            id=f"audit-{rule}",
            ref=f"audit_design rule {rule}",
            source="machine",
            count=len(sites),
            sites=sites,
        ))
    return out


def _sites_line(sites: list[str]) -> str:
    shown = ", ".join(sites[:5])
    if len(sites) > 5:
        shown += f" (+{len(sites) - 5} more)"
    return f"audit_design --json · {shown}"


_SITE = re.compile(r"[\w./\\-]+\.(?:css|scss|jsx?|tsx?|html)\s*:\s*\d+")


def _site_key(raw: str) -> str:
    """`src/ui/card.css:7` and `/abs/path/components/card.css:7` are the same
    site. Compare on basename + line so a hand note written from the editor
    still matches a machine finding written from an absolute path."""
    path, _, line = re.sub(r"\s+", "", raw).rpartition(":")
    return f"{path.replace(chr(92), '/').rsplit('/', 1)[-1]}:{line}"


def merge(hand: list[Finding], machine: list[Finding],
          escalate: frozenset[str] = frozenset()) -> tuple[list[Finding], list[str]]:
    """Drop machine findings a human already wrote up, and say which.

    Two matchers, both deliberately conservative — a false merge hides a real
    finding, which is worse than a duplicate line:
      1. the hand finding CLAIMS the rule: its id in `covers`, or in backticks;
      2. the hand finding cites a file:line the machine finding also cites.
    A rule raised with --audit-blocking is never folded: it was escalated so
    that it stays visible, and folding it would make --fail-on blocking pass.
    """
    notes: list[str] = []
    hand_sites: dict[str, Finding] = {}
    for f in hand:
        for m in _SITE.finditer(f.haystack()):
            hand_sites.setdefault(_site_key(m.group(0)), f)

    kept: list[Finding] = []
    for mf in machine:
        rule = mf.id.replace("audit-", "")
        if rule in escalate:
            kept.append(mf)
            continue
        sites = mf.sites or _SITE.findall(mf.evidence)
        covered = [s for s in sites if _site_key(s) in hand_sites]

        # The human claimed the rule: they have taken ownership of all of it.
        owner = next((f for f in hand if rule and f.claims(rule)), None)
        if owner is not None:
            notes.append(f"{mf.title} — folded whole (claimed by \"{owner.title}\")")
            owner.also_by_hand = True
            continue

        # The human cited some of the same sites: subtract those and keep the
        # rest. Folding the whole group because one of eleven sites matched is
        # how a merge quietly deletes ten real findings.
        if covered:
            hand_sites[_site_key(covered[0])].also_by_hand = True
            if len(covered) >= len(sites):
                notes.append(f"{mf.title} — folded whole (every site cited by hand)")
                continue
            rest = [s for s in sites if _site_key(s) not in hand_sites]
            mf.count = len(rest)
            mf.sites = rest
            mf.title = f"{rule} × {len(rest)}"
            mf.evidence = (_sites_line(rest) +
                           f" · {len(covered)} further site(s) already cited by hand")
            notes.append(
                f"{rule} — {len(covered)} of {len(sites)} sites cited by hand; "
                f"{len(rest)} kept as a machine finding")
        kept.append(mf)
    return hand + kept, notes


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def _badge(f: Finding) -> str:
    return f"{f.severity.upper()} · {LAYER_LABEL[f.layer]}"


def _meta_line(c: Critique) -> str:
    bits = [b for b in (c.reviewer and f"Reviewer: {c.reviewer}", c.date and c.date) if b]
    return " · ".join(bits)


def _tally(findings: list[Finding]) -> str:
    counts = {s: sum(1 for f in findings if f.severity == s) for s in SEVERITIES}
    fixed = sum(1 for f in findings if f.status == "fixed")
    return (" · ".join(f"{counts[s]} {s}" for s in SEVERITIES)
            + (f", {fixed} of them marked fixed" if fixed else ""))


def _merge_notes(notes: list[str]) -> list[str]:
    return ["", "## Merge notes", "", *(f"- {n}" for n in notes)] if notes else []


def render_critique(c: Critique, findings: list[Finding], notes: list[str]) -> str:
    ranked = sorted(findings, key=lambda f: f.rank)
    defects = [f for f in ranked if f.severity != "taste"]
    open_defects = [f for f in defects if f.status != "fixed"]
    tastes = [f for f in ranked if f.severity == "taste"]

    out: list[str] = []
    out.append(f"# Critique — {c.subject}")
    meta = _meta_line(c)
    if meta:
        out.append("")
        out.append(meta)
    out.append("")
    out.append(f"{len(findings)} findings: {_tally(findings)}.")
    out.append("")
    out.append(
        "Read top-down and stop when you run out of time — the order is the "
        "recommendation. Severity dominates; within a severity the earlier "
        "layer wins, because fixing a premise or hierarchy failure changes "
        "what everything below it looks like."
    )

    out.append("")
    out.append("## Fix these three first")
    out.append("")
    top = open_defects[:3]
    if not top and defects:
        out.append("Every defect is marked fixed. Re-check each against the page before you present.")
    elif not top:
        out.append("Nothing at defect severity. Everything below is taste — label it as such when you present it.")
    for i, f in enumerate(top, 1):
        out.append(f"{i}. **{f.title}** — {_first_sentence(f.mechanism) or 'see below'} "
                   f"({f.severity}, {LAYER_LABEL[f.layer].lower()})")

    out.append("")
    out.append("## Findings")

    # Grouped by severity, because severity is what decides what gets fixed.
    # Layer is carried on each finding's badge: it decides order *within* a
    # severity, not which section a finding belongs to.
    current_sev = None
    for i, f in enumerate(defects, 1):
        if f.severity != current_sev:
            current_sev = f.severity
            out.append("")
            out.append(f"### {f.severity.capitalize()} — {SEVERITY_RUBRIC[f.severity]}")
        out.append("")
        out.append(f"#### {i}. {f.title}")
        out.append("")
        out.append(f"`{_badge(f)}` · confidence: {f.confidence}"
                   + (" · **fixed**" if f.status == "fixed" else "")
                   + (f" · {f.count} occurrences" if f.count > 1 else "")
                   + (" · also flagged by the auditor" if f.also_by_hand else ""))
        out.append("")
        if f.mechanism:
            out.append(f"**Mechanism.** {f.mechanism}")
            out.append("")
        if f.evidence:
            out.append(f"**Evidence.** {f.evidence}")
            out.append("")
        if f.fix:
            out.append(f"**Fix.** {f.fix}")
            out.append("")
        if f.ref:
            out.append(f"*Ref: {f.ref}*")
            out.append("")

    if tastes:
        out.append("")
        out.append("## Taste, not defect")
        out.append("")
        out.append(
            "These are preferences. They are separated so that disagreeing with "
            "them costs you nothing above — a critique that mixes taste into "
            "defects gets the defects dismissed along with the taste."
        )
        out.append("")
        for f in tastes:
            line = f"- **{f.title}** ({LAYER_LABEL[f.layer].lower()}"
            line += ", fixed)" if f.status == "fixed" else ")"
            if f.mechanism:
                line += f" — {f.mechanism}"
            out.append(line)

    clean = [LAYER_LABEL[n] for n in LAYER_ORDER
             if not any(f.layer == n for f in findings)]
    if clean:
        out.append("")
        out.append("## Layers with no findings")
        out.append("")
        out.append(", ".join(clean) + ".")

    out += _merge_notes(notes)
    out.append("")
    return "\n".join(out)


def render_triage(c: Critique, findings: list[Finding], notes: list[str]) -> str:
    # Open work first, in rank order; a fixed finding is listed last, as fixed.
    ranked = sorted(findings, key=lambda f: (f.status == "fixed", f.rank))
    out = [f"# Triage — {c.subject}", ""]
    for f in ranked:
        tag = "TASTE" if f.severity == "taste" else f.severity.upper()
        if f.status == "fixed":
            tag += ", FIXED"
        fix = _first_sentence(f.fix) or _first_sentence(f.mechanism) or "no fix recorded"
        bits = [f"[{tag}]", f"[{f.layer}]", f.title, "—", fix]
        suffix = [f.confidence]
        if f.count > 1:
            suffix.append(f"×{f.count}")
        if f.ref:
            suffix.append(f.ref)
        out.append(f"- {' '.join(bits)} ({', '.join(suffix)})  <!-- {f.slug} -->")
    if not ranked:
        out.append("- (no findings)")
    out += _merge_notes(notes)
    out.append("")
    return "\n".join(out)


def render_defence(c: Critique, findings: list[Finding], notes: list[str]) -> str:
    """Every decision you will be asked about, and the sentence you answer with.

    Three sources: declared decisions, anything labelled taste (a reviewer will
    read your preference as an accident unless you can name it as a choice),
    and any finding you are shipping with — a known flaw you can name is a
    judgement call; the same flaw unnamed is an oversight."""
    ranked = sorted(findings, key=lambda f: f.rank)
    out = [f"# Presentation defence — {c.subject}", ""]
    meta = _meta_line(c)
    if meta:
        out += [meta, ""]
    out.append(
        "One row, one sentence you say out loud. If you cannot say it in one "
        "sentence without hedging, the decision is not made yet."
    )

    out += ["", "## Decisions you chose", ""]
    if c.decisions:
        out.append("| Decision | Why | What you rejected | What it costs |")
        out.append("|---|---|---|---|")
        for d in c.decisions:
            out.append("| {} | {} | {} | {} |".format(
                _cell(d.get("decision")), _cell(d.get("rationale")),
                _cell(d.get("alternative")), _cell(d.get("cost"))))
    else:
        out.append(
            "*None declared. If the page contains a single non-obvious choice — "
            "and it does — list it in the `decisions` array before the meeting.*")

    taste = [f for f in ranked if f.severity == "taste"]
    out += ["", "## Preferences a reviewer may read as mistakes", ""]
    if taste:
        out.append("| What they will point at | What you say |")
        out.append("|---|---|")
        for f in taste:
            answer = f.mechanism or f.fix or "Deliberate; state the reason."
            out.append(f"| {_cell(f.title)} | {_cell(answer)} |")
    else:
        out.append("*None recorded.*")

    # Every open defect you are presenting with — confirmed ones above all.
    # Open blocking ones are not "carried": they have their own section below.
    # A fixed one is carried only when `defend` asks, and is said as fixed.
    carried = [f for f in ranked if f.severity != "taste" and (
        (f.status == "fixed" and f.defend)
        or (f.status != "fixed" and f.severity != "blocking"))]
    out += ["", "## Known flaws you are carrying in", ""]
    if carried:
        out.append(
            "Name these before anyone else does. A flaw you raise is a judgement "
            "call; the same flaw raised by the reviewer is an oversight. A "
            "suspicion is said as a suspicion.")
        out.append("")
        out.append("| Flaw | Severity | What you say |")
        out.append("|---|---|---|")
        for f in carried:
            say = _first_sentence(f.fix) or _first_sentence(f.mechanism) or "Known; fix is scoped."
            if f.status == "fixed":
                sev = f"{f.severity}, fixed"
            elif f.confidence == "confirmed":
                sev = f.severity
            else:
                sev = f"{f.severity} ({f.confidence})"
            out.append(f"| {_cell(f.title)} | {sev} | {_cell(say)} |")
    else:
        out.append("*Nothing open. Every finding is fixed, blocking (below) or taste.*")

    blocking = [f for f in ranked if f.severity == "blocking" and f.status != "fixed"]
    out += ["", "## Do not present until these are fixed", ""]
    if blocking:
        for f in blocking:
            out.append(f"- **{f.title}** — {_first_sentence(f.mechanism)}")
    else:
        out.append("*Clear.*")

    out += _merge_notes(notes)
    out.append("")
    return "\n".join(out)


def render_summary(c: Critique, findings: list[Finding]) -> str:
    defects = [f for f in sorted(findings, key=lambda f: f.rank)
               if f.severity != "taste" and f.status != "fixed"]
    if not defects:
        if not findings:
            return "No findings recorded. That is a result you have to earn — re-run the method.\n"
        if any(f.severity != "taste" for f in findings):
            return ("No open defects: every one is marked fixed. Re-check each against "
                    "the page before you present.\n")
        return "No defects. Taste findings only — present as is, labelled as taste.\n"
    out = []
    for i, f in enumerate(defects[:3], 1):
        fix = _first_sentence(f.fix) or _first_sentence(f.mechanism) or ""
        out.append(f"{i}. [{f.severity}] {f.title}")
        if fix:
            out.append(f"   -> {fix}")
    rest = len(defects) - len(defects[:3])
    if rest > 0:
        out.append(f"({rest} more, not shown — fix these three first.)")
    return "\n".join(out) + "\n"


def _first_sentence(text: str) -> str:
    text = " ".join((text or "").split())
    if not text:
        return ""
    m = re.search(r"(?<=[.;])\s", text)
    return text[:m.start()] if m else text


def _cell(text: Any) -> str:
    return " ".join(str(text or "—").split()).replace("|", "\\|")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="critique_report",
        description="Rank critique findings and emit a critique, a triage list, "
                    "or a presentation defence sheet.",
        epilog="python -m scripts.critique_report findings.json --audit audit.json --summary",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("findings", help="findings JSON (list or {subject, findings}), or '-' for stdin")
    ap.add_argument("--format", choices=["critique", "triage", "defence"],
                    default="critique", help="output shape (default: critique)")
    ap.add_argument("--audit", metavar="FILE",
                    help="output of 'audit_design.py --json', merged as conformance findings")
    ap.add_argument("--audit-blocking", metavar="RULES", default="",
                    help="comma-separated audit rule names to raise to blocking severity")
    ap.add_argument("--summary", action="store_true",
                    help="print only the top three things to fix, then exit")
    ap.add_argument("--layer", action="append", metavar="LAYER",
                    help="restrict to a layer (repeatable)")
    ap.add_argument("--min-severity", choices=SEVERITIES, default="taste",
                    help="drop findings below this severity (default: taste, i.e. keep all)")
    ap.add_argument("--no-taste", action="store_true", help="drop taste findings entirely")
    ap.add_argument("--fail-on", choices=SEVERITIES + ["never"], default="never",
                    help="exit 1 if any finding is at or above this severity")
    ap.add_argument("-o", "--out", metavar="FILE", help="write to FILE instead of stdout")
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        critique = load_critique(args.findings)
        findings = list(critique.findings)
        notes: list[str] = []
        if args.audit:
            escalate = {r.strip() for r in args.audit_blocking.split(",") if r.strip()}
            machine = load_audit(args.audit, escalate)
            findings, notes = merge(findings, machine, frozenset(escalate))
            # Said in every format: a merge that nobody sees is how findings
            # used to disappear from triage, defence and --summary.
            for note in notes:
                print(f"critique_report: merged {note}", file=sys.stderr)

        if args.layer:
            wanted = {normalise_layer(l, "--layer") for l in args.layer}
            findings = [f for f in findings if f.layer in wanted]
        cutoff = SEVERITY_ORDER[args.min_severity]
        findings = [f for f in findings if SEVERITY_ORDER[f.severity] <= cutoff]
        if args.no_taste:
            findings = [f for f in findings if f.severity != "taste"]

        if args.summary:
            text = render_summary(critique, findings)
        elif args.format == "triage":
            text = render_triage(critique, findings, notes)
        elif args.format == "defence":
            text = render_defence(critique, findings, notes)
        else:
            text = render_critique(critique, findings, notes)
    except CritiqueError as exc:
        print(f"critique_report: {exc}", file=sys.stderr)
        return 2

    if args.out:
        try:
            Path(args.out).write_text(text, encoding="utf-8")
        except OSError as exc:
            print(f"critique_report: cannot write {args.out} — {exc}", file=sys.stderr)
            return 2
    else:
        sys.stdout.write(text)

    if args.fail_on != "never":
        threshold = SEVERITY_ORDER[args.fail_on]
        if any(SEVERITY_ORDER[f.severity] <= threshold and f.status != "fixed"
               for f in findings):
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
