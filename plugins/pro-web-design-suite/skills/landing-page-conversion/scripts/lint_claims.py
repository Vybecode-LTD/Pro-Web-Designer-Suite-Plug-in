#!/usr/bin/env python3
"""
lint_claims.py — the claims a page makes, and the devices it uses to press them.

The design gate checks how a page is built and the accessibility gates how it
works; neither reads what it says. A countdown that restarts on every visit, a
newsletter box ticked in advance or an unsourced "47% faster" passes both.
This reads the markup (HTML, JSX, Vue, Svelte, Astro) and the scripts for the
patterns SKILL.md's ethics boundary declines and conversion-audit.md names.

What it checks
--------------
  error    pre-checked-opt-in      a marketing, consent or add-on box ticked in advance
           load-time-countdown     a deadline counted from the visitor's arrival
           invented-scarcity       a stock or viewer count made with Math.random()
  warning  scarcity-claim          "only 3 left", "12 people are viewing": true only if live
           unsourced-percentage    a percentage with no link, footnote, citation or data-source
           struck-price            a struck-through ("was") price, which needs its history
           autocomplete-off        autocomplete="off" on a field the browser could fill
           lazy-first-image        loading="lazy" on the first image, usually the LCP element
           two-filled-ctas         two filled calls to action in the first section
           mismatched-cta-labels   one destination, called two different things

A warning is a question for a person: the count may be live, the figure may be
sourced on another page. It fails the run only under --strict. What each rule
stands on is in conversion-audit.md §13.

Usage
-----
    python -m scripts.lint_claims src/
    python -m scripts.lint_claims dist/index.html --json
    python -m scripts.lint_claims src/ --strict          # warnings fail too

Escape hatches, visible in review
---------------------------------
    <!-- lint-claims-ignore-next-line: scarcity-claim -- the count is the stock API's -->
    // lint-claims-ignore-file: unsourced-percentage -- figures sourced in /methodology

Exit codes: 0 no errors · 1 errors (or warnings, with --strict) · 2 bad invocation.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from html.parser import HTMLParser
from pathlib import Path

MARKUP = {".html", ".htm", ".jsx", ".tsx", ".vue", ".svelte", ".astro"}
SCRIPT = {".js", ".mjs", ".cjs", ".ts"}
SKIP_DIRS = {"node_modules", ".git", "dist", "build", ".next", ".nuxt", ".svelte-kit",
             ".astro", "coverage", "vendor", "__pycache__"}
ERROR, WARNING = "error", "warning"

# A box whose ticking signs the visitor up, consents or adds a charge.
OPT_IN = re.compile(r"newsletter|marketing|subscri|updates|offers?\b|promo|consent|agree|terms|"
                    r"insur|protect|warrant|add-?on|upsell|donat|\btip\b|partners?", re.I)
# A deadline counted from now: Date.now() + 15 * 60 * 1000, new Date().getTime() + 900000.
FROM_NOW = re.compile(r"(?:Date\.now\(\)|new Date\(\)\.getTime\(\)|\+\s*new Date\(\)|performance\.now\(\))"
                      r"\s*\+\s*\(?\s*\d[\d_.e]*(?:\s*\*\s*\d[\d_.e]*)*")
DEADLINE_WORD = re.compile(r"countdown|deadline|offer|sale|deal|timer|ends?_?at|end_?time|until|expir", re.I)
NOT_A_DEADLINE = re.compile(r"cookie|cache|token|ttl|max-?age|session|retry|debounce|throttle", re.I)
# A countdown seeded with a constant and run down in an interval.
SEEDED = re.compile(r"\b(?:let|var)\s+(\w*(?:sec|min|time|count|left|remain)\w*)\s*=\s*(\d{2,})\b", re.I)
SCARCITY = re.compile(
    r"\bonly\s+\d+\s+(?:left|remaining|in stock|spots?|seats?|places?|copies)\b"
    r"|\b\d+\s+(?:people|others|users|customers|shoppers|visitors)\s+(?:are\s+)?"
    r"(?:viewing|looking at|watching|have bought|bought|booked)\b", re.I)
SCARCITY_WORD = re.compile(r"viewing|watching|left|in stock|remaining|bought|booked|sold", re.I)
PERCENT = re.compile(r"(?<![\w.])\d+(?:\.\d+)?\s?%")
PRICE_CUT = re.compile(r"\d+(?:\.\d+)?\s?%\s*(?:off|discount)|save\s+\d+(?:\.\d+)?\s?%", re.I)
MONEY = re.compile(r"[$£€¥]\s?\d|\d\s?(?:USD|GBP|EUR)\b|\d+[.,]\d{2}\b")
PERSONAL = re.compile(r"e-?mail|tel|phone|mobile|name|given|family|address|street|postal|post-?code|"
                      r"zip|city|country|cc-|card|organi[sz]ation|company|username|birthday|bday", re.I)
FILLED = {"cta", "btn-primary", "button--primary", "button-primary"}
NOT_FILLED = re.compile(r"secondary|ghost|outline|tertiary|link|subtle", re.I)
BLOCKS = {"p", "div", "li", "h1", "h2", "h3", "h4", "h5", "h6", "td", "th", "dd", "dt", "figcaption",
          "blockquote", "caption", "summary", "label", "button", "a"}
QUIET = {"script", "style", "code", "pre", "noscript"}
PRAGMA_LINE = re.compile(r"lint-claims-ignore-next-line:\s*([\w,\s-]+?)(?:\s+--|-->|\*/|$)")
PRAGMA_FILE = re.compile(r"lint-claims-ignore-file:\s*([\w,\s-]+?)(?:\s+--|-->|\*/|$)")

FIX = {
    "pre-checked-opt-in": "Leave it unticked: a box ticked in advance is not consent (conversion-audit.md §8.1)",
    "load-time-countdown": "Count down to a real date, the same for every visitor, or drop the timer",
    "invented-scarcity": "Show the real count from stock or analytics, or nothing",
    "scarcity-claim": "Wire it to the live stock or analytics it claims, or remove it",
    "unsourced-percentage": "Link or footnote the source, or state the mechanism without the number",
    "struck-price": "Keep the price history behind it; for goods in the EU the 'was' is the 30-day low "
                    "(conversion-audit.md §11.1)",
    "autocomplete-off": "Give the field its autocomplete token (WCAG 1.3.5); a filled field is a kept visitor",
    "lazy-first-image": "Load the first image eagerly, with fetchpriority=\"high\" (conversion-audit.md §7)",
    "two-filled-ctas": "Keep one filled call to action; make the other secondary",
    "mismatched-cta-labels": "One action, one name: use the same label wherever it leads there",
}


@dataclass
class Finding:
    file: str
    line: int
    rule: str
    severity: str
    message: str
    fix: str


def truthy(value: str | None) -> bool:
    """A boolean attribute that is present and not explicitly false:
    `checked`, `checked=""` (HTML's present is true), `checked={true}`;
    not `checked={false}` or Vue's `:checked="false"`."""
    return value is None or value.strip().strip("{}").strip().lower() not in ("false", "0")


class Page(HTMLParser):
    """One file's markup: inputs and their labels, images, calls to action,
    struck prices and the text of each block."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.found: list[tuple[int, str, str]] = []                 # (line, rule, message)
        self.stack: list[dict] = []
        self.boxes: list[dict] = []                                # ticked checkboxes
        self.images = 0
        self.first_region = False                                  # the first <section> or hero seen
        self.first_region_ctas: list[int] = []
        self.ctas: list[tuple[int, str, str]] = []                 # (line, href, label)
        self.quiet = 0

    def block(self) -> dict | None:
        return next((el for el in reversed(self.stack) if el["tag"] in BLOCKS), None)

    def handle_starttag(self, tag, attrs):
        line = self.getpos()[0]
        a = {k.lstrip(":").lower(): v for k, v in attrs}
        classes = set((a.get("class") or a.get("classname") or "").split())
        el = {"tag": tag, "line": line, "text": [], "percents": [], "sourced": False,
              "struck": tag in ("s", "del", "strike")
              or bool(re.search(r"line-through", a.get("style") or "", re.I))
              or any(re.search(r"line-through|strike|was-price|compare-at", c, re.I) for c in classes),
              "cta": None}
        if tag in QUIET:
            self.quiet += 1
        # The first section, or a hero: a site header with its nav comes
        # before it and is not where the page asks for the click.
        if not self.first_region and (tag == "section" or any("hero" in c.lower() for c in classes)):
            self.first_region = True
            el["region"] = 1
        if tag in ("cite", "sup") or "data-source" in a or (tag == "a" and a.get("href")):
            for parent in self.stack:
                if parent["tag"] in BLOCKS:
                    parent["sourced"] = True
            el["sourced"] = True
        if tag == "input":
            kind = (a.get("type") or "text").lower()
            if kind == "checkbox" and (("checked" in a and truthy(a["checked"]))
                                       or ("defaultchecked" in a and truthy(a["defaultchecked"]))):
                self.boxes.append({"line": line, "id": a.get("id") or "",
                                   "words": " ".join(filter(None, (a.get("name"), a.get("id"), a.get("value")))),
                                   "label": next((p for p in reversed(self.stack) if p["tag"] == "label"), None)})
            if (a.get("autocomplete") or "").lower() == "off" and kind not in ("checkbox", "radio", "hidden") \
                    and PERSONAL.search(" ".join(filter(None, (a.get("name"), a.get("id"), kind)))):
                self.found.append((line, "autocomplete-off",
                                   f'autocomplete="off" on the {a.get("name") or a.get("id") or kind} field, '
                                   "which the browser could fill"))
        if tag == "img":
            self.images += 1
            if self.images == 1 and (a.get("loading") or "").lower() == "lazy":
                self.found.append((line, "lazy-first-image",
                                   'The first image is loading="lazy": it is usually the LCP element'))
        filled = bool(classes & FILLED) and not any(NOT_FILLED.search(c) for c in classes)
        if tag in ("a", "button") and (filled or "cta" in {c.split("--")[0] for c in classes}):
            el["cta"] = {"href": a.get("href") or "", "filled": filled}
            region = next((p.get("region") for p in reversed(self.stack) if "region" in p), None)
            if filled and region == 1:
                self.first_region_ctas.append(line)
        if tag not in ("input", "img", "br", "hr", "meta", "link", "source", "wbr"):
            self.stack.append(el)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if self.stack and self.stack[-1]["tag"] == tag:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if not any(el["tag"] == tag for el in self.stack):
            return
        while self.stack:
            el = self.stack.pop()
            self.finish(el)
            if el["tag"] == tag:
                break

    def finish(self, el):
        text = " ".join("".join(el["text"]).split())
        if el["tag"] in QUIET:
            self.quiet -= 1
            text = ""                                              # a script's text is not the page's
        parent = self.stack[-1] if self.stack else None
        if parent is not None:                                     # a parent block reads its children's text
            parent["text"].append(" " + text + " ")
            parent["percents"].extend(el["percents"] if el["tag"] not in BLOCKS else [])
        if el["tag"] == "label":
            for box in self.boxes:
                if box["label"] is el:
                    box["words"] += " " + text
        if el["struck"] and (MONEY.search(text) or re.search(r"\d", text)):
            self.found.append((el["line"], "struck-price", f'A struck-through price, "{text[:40]}"'))
        if el["tag"] in BLOCKS and not el["sourced"]:
            for line, figure in el["percents"]:
                self.found.append((line, "unsourced-percentage",
                                   f'"{figure}" with no source beside it'))
        if el["cta"] is not None:
            self.ctas.append((el["line"], el["cta"]["href"], text))

    def handle_data(self, data):
        if not self.stack:
            return
        self.stack[-1]["text"].append(data)
        if self.quiet:
            return
        line = self.getpos()[0]
        for m in SCARCITY.finditer(data):
            self.found.append((line + data[:m.start()].count("\n"), "scarcity-claim", f'"{m.group(0)}"'))
        cuts = [m.span() for m in PRICE_CUT.finditer(data)]
        target = self.block() or self.stack[-1]
        for m in PERCENT.finditer(data):
            if not any(a <= m.start() < b for a, b in cuts):
                target["percents"].append((line + data[:m.start()].count("\n"), m.group(0).replace(" ", "")))


def label_for(source: str) -> dict[str, str]:
    """`<label for="id">text</label>` across the file, which the parser's
    stack cannot pair when the label comes after the box."""
    found = {}
    for m in re.finditer(r"<label\b[^>]*\b(?:for|htmlFor)\s*=\s*[\"'{]*([\w-]+)[\"'}]*[^>]*>(.*?)</label>",
                         source, re.S | re.I):
        found[m.group(1)] = re.sub(r"<[^>]+>", " ", m.group(2))
    return found


def markup_findings(source: str) -> list[tuple[int, str, str]]:
    page = Page()
    page.feed(source)
    page.close()
    while page.stack:                                              # an unclosed block still counts
        page.finish(page.stack.pop())
    out = list(page.found)
    labels = label_for(source)
    for box in page.boxes:
        words = box["words"] + " " + labels.get(box["id"], "")
        if OPT_IN.search(words):
            out.append((box["line"], "pre-checked-opt-in",
                        f'A box ticked in advance: "{" ".join(words.split())[:60]}"'))
    if len(page.first_region_ctas) > 1:
        out.append((page.first_region_ctas[1], "two-filled-ctas",
                    f"{len(page.first_region_ctas)} filled calls to action in the first section"))
    named: dict[str, str] = {}
    for line, href, label in page.ctas:
        label = " ".join(label.split())
        if not href or not label:
            continue
        if href in named and named[href].lower() != label.lower():
            out.append((line, "mismatched-cta-labels", f'"{label}" leads to {href}, which "{named[href]}" also names'))
        named.setdefault(href, label)
    return out


def script_findings(source: str) -> list[tuple[int, str, str]]:
    out = []
    lines = source.splitlines()
    for n, text in enumerate(lines, 1):
        if FROM_NOW.search(text) and DEADLINE_WORD.search(text) and not NOT_A_DEADLINE.search(text):
            out.append((n, "load-time-countdown", "A deadline set from the moment the page loaded"))
        if "Math.random" in text:
            near = " ".join(lines[max(0, n - 3):n + 2])
            if SCARCITY_WORD.search(near):
                out.append((n, "invented-scarcity", "A count made up with Math.random()"))
    for m in SEEDED.finditer(source):
        name = re.escape(m.group(1))
        if re.search(rf"\b{name}\s*(?:--|-=\s*1\b)", source) and "setInterval" in source:
            out.append((source[:m.start()].count("\n") + 1, "load-time-countdown",
                        f"{m.group(1)} starts at {m.group(2)} on every visit and counts down"))
    return out


def ignored(source: str) -> tuple[set[str], dict[int, set[str]]]:
    """The rules a file switches off, whole or for its next line."""
    whole = {r.strip() for m in PRAGMA_FILE.finditer(source) for r in m.group(1).split(",")}
    lines: dict[int, set[str]] = {}
    for n, text in enumerate(source.splitlines(), 1):
        m = PRAGMA_LINE.search(text)
        if m:
            lines[n + 1] = {r.strip() for r in m.group(1).split(",")}
    return whole, lines


SEVERITY = {"pre-checked-opt-in": ERROR, "load-time-countdown": ERROR, "invented-scarcity": ERROR}


def lint(path: Path, shown: str) -> list[Finding]:
    raw = path.read_bytes()
    source = raw.decode(json.detect_encoding(raw), errors="replace")
    found = script_findings(source)
    if path.suffix.lower() in MARKUP:
        found += markup_findings(source)
    whole, by_line = ignored(source)
    out, seen = [], set()
    for line, rule, message in sorted(found):
        if (line, rule, message) in seen or {rule, "ALL"} & (whole | by_line.get(line, set())):
            continue
        seen.add((line, rule, message))
        out.append(Finding(shown, line, rule, SEVERITY.get(rule, WARNING), message, FIX[rule]))
    return out


def files(paths: list[str]) -> list[Path]:
    found = []
    for p in map(Path, paths):
        if p.is_file():
            found.append(p)
            continue
        for f in sorted(p.rglob("*")):
            if f.is_file() and f.suffix.lower() in MARKUP | SCRIPT \
                    and not any(part in SKIP_DIRS or part.startswith(".") for part in f.relative_to(p).parts[:-1]):
                found.append(f)
    return found


def report(findings: list[Finding], show_fix: bool) -> str:
    if not findings:
        return "lint_claims: clean — no claim or device it can read is a problem.\n"
    lines = []
    for f in findings:
        lines.append(f"{f.file}:{f.line}  {f.severity:<7}  {f.rule:<22}  {f.message}")
        if show_fix:
            lines.append(f"{'':>10}fix: {f.fix}")
    errors = sum(f.severity == ERROR for f in findings)
    lines.append(f"lint_claims: {errors} error(s), {len(findings) - errors} warning(s). "
                 "A clean run reads only what a pattern can see; the claims themselves are a person's to check.")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="The claims a page makes and the devices that press them: pre-ticked boxes, "
                    "load-time countdowns, invented scarcity, unsourced figures, struck prices.")
    ap.add_argument("paths", nargs="*", default=["."], help="files or folders (markup, JSX, Vue, Svelte, Astro, JS)")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--strict", action="store_true", help="warnings fail the run too")
    ap.add_argument("--quiet", action="store_true", help="leave out each finding's fix")
    args = ap.parse_args(argv)

    missing = [p for p in args.paths if not Path(p).exists()]
    if missing:
        print(f"lint_claims: no such path: {', '.join(missing)}", file=sys.stderr)
        return 2
    targets = files(args.paths)
    findings: list[Finding] = []
    for path in targets:
        try:
            findings += lint(path, path.as_posix())
        except OSError as exc:
            print(f"lint_claims: cannot read {path}: {exc}", file=sys.stderr)
            return 2
    if not targets:
        print("lint_claims: no markup or script files to read", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps({"tool": "lint_claims", "files": len(targets),
                          "errors": sum(f.severity == ERROR for f in findings),
                          "warnings": sum(f.severity == WARNING for f in findings),
                          "findings": [asdict(f) for f in findings]}, indent=2))
    else:
        sys.stdout.write(report(findings, show_fix=not args.quiet))
    failing = [f for f in findings if f.severity == ERROR or (args.strict and f.severity == WARNING)]
    return 1 if failing else 0


if __name__ == "__main__":
    # A Windows pipe (git hook, CI, `> file`) defaults to the ANSI code page,
    # where printing a dash or a pound sign writes cp1252 or raises. Consoles
    # and Claude Code already use UTF-8 and are left alone.
    for _stream in (sys.stdout, sys.stderr):
        if getattr(_stream, "encoding", "utf-8").lower() not in ("utf-8", "utf8"):
            _stream.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
