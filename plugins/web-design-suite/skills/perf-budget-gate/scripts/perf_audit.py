#!/usr/bin/env python3
"""
perf_audit.py — the static half of the performance gate.

This is `audit_design.py`'s counterpart. That script fails the build when the
design regresses; this one fails it when the *performance* does. Same shape,
same severity model, same baseline-adoption philosophy, same comment pragmas.

It reads bytes on disk and markup in source. It never opens a browser, so it
is deterministic, takes about a second, and can run on every commit. That is
the point: the cheap layer catches the regressions that actually ship — an
un-preloaded font, an LCP image marked `loading="lazy"`, a 900KB hero JPEG, a
bundle that grew 40% — while the expensive layer (`measure_vitals.mjs`) is
reserved for the numbers only a real browser can produce.

What it checks
--------------
  B  Budget         per-type transfer bytes, request counts, largest asset,
                    third-party origins, and the growth delta vs a baseline
  L  LCP risk       lazy-loaded hero images, missing fetchpriority, render-
                    blocking CSS, sync scripts in <head>, @import, fonts with
                    no preload, third-party origins with no preconnect
  C  CLS risk       <img>/<iframe> without dimensions, @font-face with no
                    metric-matched fallback or no font-display, transitions on
                    layout-affecting properties, banners injected at body start
  T  Main thread    scripts without defer/async, duplicated dependencies
  W  Weight         oversized images, legacy/unsubset fonts, poor formats,
                    missing srcset, unused-looking CSS

Byte accounting
---------------
Text assets are budgeted on their **gzip -6 size**, computed here with the
stdlib, because that is roughly what crosses the wire and raw bytes on disk
are not. Binary assets that are already compressed (images, woff2, video) are
budgeted on raw size, because gzipping them changes nothing. Brotli ships
about 15-20% smaller than gzip for text; this deliberately over-counts rather
than under-counts, and the budget file can say `"measure": "raw"` to opt out.

Usage
-----
    python -m scripts.perf_audit dist/
    python -m scripts.perf_audit dist/ --src src/ --budget perf-budget.json
    python -m scripts.perf_audit dist/ --json
    python -m scripts.perf_audit dist/ --strict           # warnings fail too
    python -m scripts.perf_audit dist/ --page-type marketing

Adopting it on an existing slow site
------------------------------------
    python -m scripts.perf_audit dist/ --write-baseline .perf-baseline.json
    python -m scripts.perf_audit dist/                    # only NEW findings fail

The baseline records today's violations *and* today's byte totals, so the gate
can be turned on this afternoon on a site that is already over budget. Existing
debt is frozen; growth past `budget.growth` still fails. A gate that fails on
day one is a gate somebody deletes on day two.

Escape hatches (use sparingly, they are visible in review)
----------------------------------------------------------
    <!-- perf-audit-ignore-next-line: C -- dimensions come from the CMS -->
    /* perf-audit-ignore-file: W -- vendor bundle, tracked in PERF-412 */
    // perf-audit-ignore-next-line: img-no-dimensions -- square by construction

Exit codes: 0 clean · 1 violations found · 2 bad invocation.
"""

from __future__ import annotations

import argparse
import fnmatch
import gzip
import json
import os
import re
import struct
import sys
from dataclasses import dataclass, asdict, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable, Iterator

# A sibling import would otherwise leave __pycache__ inside the installed
# plugin. project_config.py is a copy of the plugin's shared/ master (P24).
sys.dont_write_bytecode = True
try:                                              # python -m scripts.perf_audit
    from .project_config import ConfigError, config_path, project_config
except ImportError:                               # python scripts/perf_audit.py, or loaded by path
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from project_config import ConfigError, config_path, project_config  # type: ignore[no-redef]

# ---------------------------------------------------------------------------
# Configuration — the vocabulary this skill enforces.
# ---------------------------------------------------------------------------

HTML_EXT = {".html", ".htm", ".xhtml"}
CSS_EXT = {".css", ".scss", ".sass", ".less", ".pcss"}
JS_EXT = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}
IMG_EXT = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".avif", ".svg", ".ico",
           ".bmp", ".tif", ".tiff"}
FONT_EXT = {".woff2", ".woff", ".ttf", ".otf", ".eot"}
MEDIA_EXT = {".mp4", ".webm", ".mov", ".m4v", ".mp3", ".wav", ".ogg", ".ogv",
             ".m4a", ".flac"}

# Formats that are already entropy-coded. Gzipping them buys nothing, so they
# are budgeted raw.
PRECOMPRESSED = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".avif", ".woff2",
                 ".woff", ".mp4", ".webm", ".mov", ".m4v", ".mp3", ".m4a",
                 ".ogg", ".ogv", ".flac", ".zip", ".gz", ".br", ".ico"}

SKIP_DIRS = {
    "node_modules", ".git", ".next/cache", "coverage", "__pycache__",
    ".venv", "venv", ".turbo", ".cache", ".parcel-cache", ".vercel",
}

# Not shipped to a browser on a normal page view. Counting them makes every
# budget meaningless, which is how a budget stops being believed.
NOT_SHIPPED = re.compile(
    r"\.map$|\.d\.ts$|\.LICENSE\.txt$|(^|/)(sitemap|robots)\.txt$"
    r"|(^|/)stats\.(json|html)$|(^|/)report\.html$"
)

CATEGORY_NAMES = {
    "B": "Budget",
    "L": "LCP risk",
    "C": "CLS risk",
    "T": "Main-thread risk",
    "W": "Weight and waste",
}

SEVERITY_ORDER = {"error": 0, "warning": 1}

# An element is a *likely* LCP candidate when it is the first image in the
# document or it is named like a hero. This is a heuristic and it is allowed to
# be, because the cost of a false positive is one pragma and the cost of a
# false negative is a four-second LCP. measure_vitals.mjs reports the real one.
HERO_PAT = re.compile(
    r"hero|banner|cover|masthead|splash|jumbotron|above-?fold|lead-?image|"
    r"feature(d)?-image|poster", re.I)

# Properties whose animation forces layout on every frame. The compositor-only
# rule and its substitutions live in web-design-studio/references/motion-system.md §5.
LAYOUT_ANIMATED = {
    "width", "height", "top", "right", "bottom", "left", "inset",
    "margin", "margin-top", "margin-right", "margin-bottom", "margin-left",
    "padding", "padding-top", "padding-right", "padding-bottom", "padding-left",
    "font-size", "line-height", "border-width", "flex-basis", "block-size",
    "inline-size", "min-height", "max-height", "min-width", "max-width",
}

# The tag list runs up to the `--` that introduces the reason. Rule names
# contain hyphens (`img-no-dimensions`), so the list cannot simply stop at the
# first `-`; it stops at a DOUBLE hyphen, which is the documented separator.
IGNORE_LINE = re.compile(r"perf-audit-ignore-next-line\s*:?\s*([^\n]*)")
IGNORE_FILE = re.compile(r"perf-audit-ignore-file\s*:?\s*([^\n]*)")
GENERATED_MARKERS = ("@generated", "DO NOT EDIT", "AUTO-GENERATED")

URL_FUNC = re.compile(r"url\(\s*['\"]?([^'\")]+)['\"]?\s*\)", re.I)
ABS_URL = re.compile(r"^(?:https?:)?//([^/?#]+)", re.I)
NODE_MODULES_PKG = re.compile(r"node_modules/((?:@[\w.-]+/)?[\w.-]+)")
PKG_AT_VERSION = re.compile(r"((?:@[\w.-]+/)?[\w.-]+)@(\d+\.\d+\.\d+)")
CSS_CLASS_SEL = re.compile(r"\.(-?[_a-zA-Z][\w-]*)")
WORDS = re.compile(r"[A-Za-z_][\w-]*")

# ---------------------------------------------------------------------------
# The default budget.
#
# These numbers are a starting point derived in references/budgets.md §1 from
# "LCP under 2.5s on a mid-tier Android over Slow 4G". They are deliberately
# printed when no budget file is found, because a budget nobody chose is a
# budget nobody defends.
# ---------------------------------------------------------------------------

DEFAULT_BUDGET: dict = {
    "$schema": "perf-budget-gate/1",
    "measure": "gzip",
    "first_party_origins": [],
    "defaults": {
        "bytes": {
            "total": 600_000,
            "html": 25_000,
            "css": 60_000,
            "js": 170_000,
            "image": 300_000,
            "font": 100_000,
            "media": 0,
            "other": 50_000,
        },
        "requests": {
            "total": 50, "css": 4, "js": 10, "image": 20, "font": 3,
        },
        "largest_asset": {
            "image": 150_000, "js": 120_000, "css": 40_000, "font": 40_000,
        },
        "third_party": {"origins": 3, "scripts": 3},
        "lab": {"lcp_ms": 2500, "cls": 0.10, "tbt_ms": 200, "ttfb_ms": 800},
    },
    "growth": {"total_pct": 5, "js_pct": 5, "image_pct": 10},
    "pages": {},
}

BYTE_TYPES = ("html", "css", "js", "image", "font", "media", "other")


# ---------------------------------------------------------------------------
# Findings — same shape as audit_design.Finding, on purpose.
# ---------------------------------------------------------------------------

@dataclass
class Finding:
    file: str
    line: int
    cat: str
    rule: str
    severity: str
    message: str
    fix: str
    snippet: str = ""

    def key(self) -> str:
        """Stable identity for baselining. Excludes the line number so that an
        unrelated edit above a violation does not resurrect it."""
        return f"{self.file}|{self.rule}|{self.snippet.strip()[:120]}"


@dataclass
class Asset:
    path: Path
    rel: str
    kind: str
    raw: int
    transfer: int
    width: int = 0
    height: int = 0
    counted: bool = True
    alternate_of: str = ""


# Encoding a hero as AVIF, WebP and JPEG is correct, and exactly one of the
# three is ever fetched. Counting all three makes every image budget a lie and
# punishes the team for doing the right thing.
ALT_FORMATS = (".avif", ".webp", ".jpg", ".jpeg", ".png", ".gif")


def mark_alternates(assets: list[Asset]) -> None:
    """Collapse same-stem image format variants to the largest one.

    Worst case, not average: if the budget holds for the JPEG it holds for the
    AVIF too. What this does NOT collapse is a `srcset` width ladder
    (`hero-640.jpg`, `hero-1280.jpg`) — those have different stems, so they are
    all counted. That over-counts, deliberately: this script cannot know which
    rung a given viewport picks, and an over-count is a conversation while an
    under-count is a regression nobody sees.
    """
    groups: dict[tuple[str, str], list[Asset]] = {}
    for a in assets:
        if a.kind != "image" or a.path.suffix.lower() not in ALT_FORMATS:
            continue
        groups.setdefault((str(a.path.parent), a.path.stem), []).append(a)
    for group in groups.values():
        if len(group) < 2:
            continue
        keep = max(group, key=lambda x: x.transfer)
        for a in group:
            if a is not keep:
                a.counted = False
                a.alternate_of = keep.rel


@dataclass
class Ledger:
    assets: list[Asset] = field(default_factory=list)

    def shipped(self) -> list[Asset]:
        return [a for a in self.assets if a.counted]

    def by_kind(self, kind: str) -> list[Asset]:
        return [a for a in self.assets if a.kind == kind and a.counted]

    def bytes_of(self, kind: str) -> int:
        return sum(a.transfer for a in self.by_kind(kind))

    def total_bytes(self) -> int:
        return sum(a.transfer for a in self.shipped())

    def counts(self) -> dict[str, int]:
        out = {k: len(self.by_kind(k)) for k in BYTE_TYPES}
        out["total"] = len(self.shipped())
        return out

    def byte_table(self) -> dict[str, int]:
        out = {k: self.bytes_of(k) for k in BYTE_TYPES}
        out["total"] = self.total_bytes()
        return out


# ---------------------------------------------------------------------------
# Asset classification and measurement
# ---------------------------------------------------------------------------

def classify(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in HTML_EXT:
        return "html"
    if ext in CSS_EXT:
        return "css"
    if ext in JS_EXT:
        return "js"
    if ext in IMG_EXT:
        return "image"
    if ext in FONT_EXT:
        return "font"
    if ext in MEDIA_EXT:
        return "media"
    return "other"


def transfer_size(path: Path, raw: bytes, measure: str) -> int:
    """What this file costs on the wire, near enough to budget against.

    Text is gzipped at level 6 (deterministic, mtime pinned). Already-
    compressed binaries are counted raw, because gzipping a JPEG makes it
    bigger and pretending otherwise inflates every image budget.
    """
    if measure == "raw" or path.suffix.lower() in PRECOMPRESSED:
        return len(raw)
    try:
        return len(gzip.compress(raw, compresslevel=6, mtime=0))
    except Exception:
        return len(raw)


# ---- Intrinsic image dimensions, from the file header, no dependencies ----

def image_size(data: bytes, ext: str) -> tuple[int, int]:
    """Intrinsic pixel dimensions, or (0, 0) when the header is not understood.

    Only needs enough of each format to find the width and height. A format
    this does not know simply skips the oversized-image check rather than
    guessing.
    """
    try:
        if data[:8] == b"\x89PNG\r\n\x1a\n" and data[12:16] == b"IHDR":
            w, h = struct.unpack(">II", data[16:24])
            return w, h
        if data[:6] in (b"GIF87a", b"GIF89a"):
            w, h = struct.unpack("<HH", data[6:10])
            return w, h
        if data[:2] == b"\xff\xd8":                      # JPEG
            i, n = 2, len(data)
            while i + 9 < n:
                if data[i] != 0xFF:
                    i += 1
                    continue
                marker = data[i + 1]
                if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
                    i += 2
                    continue
                seglen = struct.unpack(">H", data[i + 2:i + 4])[0]
                if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
                              0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                    h, w = struct.unpack(">HH", data[i + 5:i + 9])
                    return w, h
                i += 2 + seglen
            return 0, 0
        if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
            fourcc = data[12:16]
            if fourcc == b"VP8X":
                w = int.from_bytes(data[24:27], "little") + 1
                h = int.from_bytes(data[27:30], "little") + 1
                return w, h
            if fourcc == b"VP8 ":
                w = struct.unpack("<H", data[26:28])[0] & 0x3FFF
                h = struct.unpack("<H", data[28:30])[0] & 0x3FFF
                return w, h
            if fourcc == b"VP8L":
                bits = int.from_bytes(data[21:25], "little")
                return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
            return 0, 0
        if data[4:8] == b"ftyp":                          # AVIF / HEIF
            idx = data.find(b"ispe")
            if idx > 0 and idx + 12 <= len(data):
                w, h = struct.unpack(">II", data[idx + 4 + 4:idx + 4 + 12])
                return w, h
            return 0, 0
        if ext == ".svg":
            head = data[:4000].decode("utf-8", errors="replace")
            m = re.search(r'viewBox\s*=\s*["\']\s*[-\d.]+[,\s]+[-\d.]+[,\s]+'
                          r'([\d.]+)[,\s]+([\d.]+)', head)
            if m:
                return int(float(m.group(1))), int(float(m.group(2)))
            mw = re.search(r'\bwidth\s*=\s*["\']?([\d.]+)', head)
            mh = re.search(r'\bheight\s*=\s*["\']?([\d.]+)', head)
            if mw and mh:
                return int(float(mw.group(1))), int(float(mh.group(1)))
    except Exception:
        return 0, 0
    return 0, 0


# ---------------------------------------------------------------------------
# Pragmas
# ---------------------------------------------------------------------------

def collect_pragmas(text: str) -> tuple[set[str], dict[int, set[str]]]:
    """Ignore pragmas, read from raw text in any comment syntax.

    Reading them from raw text rather than from parsed comments means the same
    three lines of code serve HTML, CSS and JS, and an ignore that is written
    in the wrong comment style still works. The cost is that a pragma inside a
    string literal also counts, which has never once been a real problem.
    """
    def tags(raw_tail: str) -> set[str]:
        # Everything before `--` is the tag list; everything after is the
        # reason, which is for the reviewer, not for this parser.
        head = re.split(r"\s--|\*/|-->", raw_tail, maxsplit=1)[0]
        return {t.strip().upper() for t in head.split(",") if t.strip()}

    file_tags: set[str] = set()
    line_tags: dict[int, set[str]] = {}
    for idx, raw in enumerate(text.splitlines(), start=1):
        m = IGNORE_FILE.search(raw)
        if m:
            file_tags |= tags(m.group(1))
        m = IGNORE_LINE.search(raw)
        if m:
            line_tags.setdefault(idx + 1, set()).update(tags(m.group(1)))
    return file_tags, line_tags


class Reporter:
    """Collects findings for one file, applying that file's pragmas."""

    def __init__(self, path: str, text: str = "") -> None:
        self.path = path
        self.lines = text.splitlines()
        self.file_tags, self.line_tags = collect_pragmas(text)
        self.out: list[Finding] = []

    def add(self, line: int, cat: str, rule: str, sev: str,
            msg: str, fix: str, snippet: str | None = None) -> None:
        tags = {t.upper() for t in self.line_tags.get(line, set()) | self.file_tags}
        if cat.upper() in tags or rule.upper() in tags or "ALL" in tags:
            return
        if snippet is None:
            snippet = (self.lines[line - 1].strip()
                       if 0 < line <= len(self.lines) else "")
        self.out.append(Finding(self.path, line, cat, rule, sev, msg, fix,
                                snippet[:200]))


# ---------------------------------------------------------------------------
# HTML scanning
# ---------------------------------------------------------------------------

@dataclass
class ImgUse:
    """One `<img>` occurrence, kept until the CSS has been read.

    How wide an image is actually rendered is usually decided in CSS, not in
    the markup, so the oversized check cannot run until both halves are in.
    """
    doc: str
    line: int
    src: str
    tokens: tuple[str, ...]
    attr_width: int = 0


@dataclass
class DocFacts:
    """What one HTML document tells the rest of the audit."""
    preloaded_fonts: set[str] = field(default_factory=set)
    preconnects: set[str] = field(default_factory=set)
    third_party_origins: set[str] = field(default_factory=set)
    third_party_scripts: int = 0
    class_tokens: set[str] = field(default_factory=set)
    img_uses: list[ImgUse] = field(default_factory=list)


class MarkupScanner(HTMLParser):
    """A small, forgiving HTML pass.

    It answers four questions: what will block the first paint, what will shift
    the layout, what is discoverable in the initial markup, and who else's
    origin are we on the hook for. It is not a validator and does not try to be.
    """

    def __init__(self, rep: Reporter, budget: dict, facts: DocFacts) -> None:
        super().__init__(convert_charrefs=True)
        self.rep = rep
        self.budget = budget
        self.facts = facts
        self.in_head = False
        self.seen_body = False
        self.img_index = 0
        self.first_img_reported = False
        self.first_party = set(budget.get("first_party_origins") or [])
        self.blocking_css: list[tuple[int, str]] = []

    def finish(self) -> None:
        """Checks that need the whole document.

        One render-blocking stylesheet is the price of doing business and
        firing on it would train everyone to ignore this rule. Every stylesheet
        AFTER the first is a serial round trip on a cold connection, and that
        is worth a line in the report.
        """
        for line, href in self.blocking_css[1:]:
            self.rep.add(
                line, "L", "render-blocking-css", "warning",
                f"`{Path(href).name}` is render-blocking stylesheet "
                f"#{self.blocking_css.index((line, href)) + 1} in <head>.",
                "A stylesheet in <head> blocks the first paint until it is "
                "downloaded, parsed and applied — it sits in front of every LCP "
                "phase. The first one is unavoidable. Each additional one adds "
                "its own place in the queue, and on a cold high-latency "
                "connection they do not all fit in the first congestion window. "
                "Concatenate them at build time, or inline the above-the-fold "
                "rules and load the rest with "
                "`media=\"print\" onload=\"this.media='all'\"`. The honest "
                "tradeoffs of critical CSS are in references/diagnosis.md §7.")

    # -- helpers ----------------------------------------------------------
    def _line(self) -> int:
        return self.getpos()[0]

    def _origin(self, url: str) -> str | None:
        m = ABS_URL.match(url.strip())
        if not m:
            return None
        host = m.group(1).lower().split("@")[-1]
        if host in self.first_party:
            return None
        return host

    def _note_url(self, url: str, is_script: bool = False) -> None:
        if not url:
            return
        origin = self._origin(url)
        if origin:
            self.facts.third_party_origins.add(origin)
            if is_script:
                self.facts.third_party_scripts += 1

    # -- tags -------------------------------------------------------------
    def handle_starttag(self, tag: str, attrs_list) -> None:
        a = {k.lower(): (v or "") for k, v in attrs_list}
        line = self._line()
        if tag == "head":
            self.in_head = True
        elif tag == "body":
            self.in_head = False
            self.seen_body = True
        if "class" in a:
            self.facts.class_tokens.update(WORDS.findall(a["class"]))
        if "id" in a:
            self.facts.class_tokens.add(a["id"])

        handler = getattr(self, f"_tag_{tag}", None)
        if handler:
            handler(a, line)

    def handle_endtag(self, tag: str) -> None:
        if tag == "head":
            self.in_head = False

    # -- per-tag rules ----------------------------------------------------
    def _tag_link(self, a: dict, line: int) -> None:
        rel = a.get("rel", "").lower()
        href = a.get("href", "")
        self._note_url(href)
        if "preconnect" in rel or "dns-prefetch" in rel:
            o = ABS_URL.match(href.strip())
            if o:
                self.facts.preconnects.add(o.group(1).lower())
        if "preload" in rel:
            if a.get("as", "").lower() == "font":
                self.facts.preloaded_fonts.add(Path(href.split("?")[0]).name)
                if "crossorigin" not in a:
                    self.rep.add(
                        line, "L", "font-preload-no-crossorigin", "error",
                        f"Font preload `{Path(href).name}` has no `crossorigin`.",
                        "Fonts are fetched in CORS mode even same-origin, so a "
                        "preload without `crossorigin` lands in a different cache "
                        "partition than the @font-face request. The file "
                        "downloads TWICE and the preload buys nothing — it costs "
                        "bandwidth during the exact window you were trying to "
                        "protect. See web-design-studio/references/typography.md §8.")
        if "stylesheet" in rel:
            media = a.get("media", "").lower()
            if (self.in_head or not self.seen_body) and media != "print" \
                    and "onload" not in a:
                self.blocking_css.append((line, href))

    def _tag_script(self, a: dict, line: int) -> None:
        src = a.get("src", "")
        typ = a.get("type", "").lower()
        if typ in ("application/json", "application/ld+json", "text/template"):
            return
        if src:
            self._note_url(src, is_script=True)
        is_module = typ == "module"
        has_defer = "defer" in a or "async" in a
        if src and not has_defer and not is_module:
            if self.in_head or not self.seen_body:
                self.rep.add(
                    line, "L", "sync-script-head", "error",
                    f"Synchronous `<script src>` in <head>: {Path(src).name}.",
                    "A classic script with no defer/async stops the HTML parser "
                    "dead: nothing after it is parsed, no later resource is "
                    "discovered, and the LCP image is not even known to exist "
                    "until this file has been fetched AND executed. Add `defer` "
                    "(runs after parsing, keeps order) or `type=\"module\"` "
                    "(deferred by definition). Use `async` only for a script "
                    "with no dependents, such as analytics.")
            else:
                self.rep.add(
                    line, "T", "script-no-defer", "warning",
                    f"`<script src>` with no defer/async: {Path(src).name}.",
                    "At the end of <body> this does not block the parser, but it "
                    "still executes before the parser finishes and competes with "
                    "rendering for the main thread. `defer` costs nothing and "
                    "keeps execution order.")
    def _tag_img(self, a: dict, line: int) -> None:
        self.img_index += 1
        src = a.get("src", "") or a.get("data-src", "")
        self._note_url(src)
        name = " ".join([a.get("class", ""), a.get("id", ""), src, a.get("alt", "")])
        likely_lcp = (self.img_index == 1 and not self.in_head) or bool(HERO_PAT.search(name))

        style = a.get("style", "")
        has_dims = ("width" in a and "height" in a) or "aspect-ratio" in style

        if src and not src.startswith("data:"):
            try:
                attr_w = int(re.sub(r"[^\d].*$", "", a.get("width", "0")) or 0)
            except ValueError:
                attr_w = 0
            self.facts.img_uses.append(ImgUse(
                doc=self.rep.path, line=line,
                src=Path(src.split("?")[0]).name,
                tokens=tuple(WORDS.findall(a.get("class", "")) +
                             ([a["id"]] if "id" in a else [])),
                attr_width=attr_w))
        if not has_dims:
            self.rep.add(
                line, "C", "img-no-dimensions", "error",
                f"`<img>` has no width/height: {Path(src).name or '(no src)'}.",
                "Without both attributes the browser reserves zero height, lays "
                "out everything below at the wrong position, then shifts it all "
                "down when the image header arrives. The attributes do not fix "
                "the rendered size — modern browsers turn them into an intrinsic "
                "`aspect-ratio` and your CSS `width: 100%; height: auto` still "
                "wins. Put the INTRINSIC pixel size in the attributes, or set "
                "`aspect-ratio` in CSS. See references/diagnosis.md §5.")

        if likely_lcp:
            if a.get("loading", "").lower() == "lazy":
                self.rep.add(
                    line, "L", "lcp-lazy", "error",
                    f"Likely LCP image is `loading=\"lazy\"`: {Path(src).name}.",
                    "This is the single most common own-goal in web performance. "
                    "A lazy image is not requested until layout has run and the "
                    "browser knows it is in view, which adds a full resource-load "
                    "delay to the critical path — often 500-1500ms of pure waiting "
                    "on the metric you are trying to fix. Lazy-load what is BELOW "
                    "the fold. The LCP image gets `fetchpriority=\"high\"` and no "
                    "`loading` attribute at all.")
            elif a.get("fetchpriority", "").lower() != "high":
                self.rep.add(
                    line, "L", "lcp-no-fetchpriority", "warning",
                    f"Likely LCP image has no `fetchpriority=\"high\"`: "
                    f"{Path(src).name}.",
                    "The preload scanner finds this image, but it queues at Low "
                    "priority until layout proves it is in the viewport, and it "
                    "loses the connection to stylesheets and scripts. "
                    "`fetchpriority=\"high\"` moves it to the front of the queue "
                    "immediately and is typically worth 100-500ms of LCP for one "
                    "attribute. Only ever put it on ONE image per page.")
            if "data-src" in a and not a.get("src"):
                self.rep.add(
                    line, "L", "lcp-js-discovered", "error",
                    "Likely LCP image is loaded by JavaScript (`data-src`).",
                    "The preload scanner cannot see `data-src`, so this image is "
                    "not requested until the lazy-load library has downloaded, "
                    "parsed, executed and run its observer. That is the whole JS "
                    "pipeline in front of your largest paint. Use a real `src` "
                    "with `fetchpriority=\"high\"` for the hero and keep the "
                    "library for what is below the fold.")

    def _tag_iframe(self, a: dict, line: int) -> None:
        self._note_url(a.get("src", ""))
        style = a.get("style", "")
        if not (("width" in a and "height" in a) or "aspect-ratio" in style):
            self.rep.add(
                line, "C", "iframe-no-dimensions", "warning",
                "`<iframe>` has no width/height.",
                "An embed that sizes itself after load pushes every following "
                "block down. Reserve the box with `aspect-ratio` on a wrapper, "
                "or explicit attributes. Third-party embeds are the second "
                "biggest source of CLS after images.")

    def _tag_video(self, a: dict, line: int) -> None:
        self._note_url(a.get("src", ""))
        self._note_url(a.get("poster", ""))
        if not ("width" in a and "height" in a):
            self.rep.add(
                line, "C", "video-no-dimensions", "warning",
                "`<video>` has no width/height.",
                "Same mechanism as an image: no reserved box, so everything "
                "below shifts when metadata arrives. A `poster` also makes the "
                "video an LCP candidate, so it wants the same treatment as a "
                "hero image.")

    def _tag_source(self, a: dict, line: int) -> None:
        self._note_url(a.get("src", "") or a.get("srcset", "").split(",")[0].strip().split(" ")[0])

    def _tag_use(self, a: dict, line: int) -> None:
        self._note_url(a.get("href", "") or a.get("xlink:href", ""))


def audit_html(path: Path, text: str, budget: dict) -> tuple[list[Finding], DocFacts]:
    rep = Reporter(str(path), text)
    facts = DocFacts()
    if any(m in text[:800] for m in GENERATED_MARKERS):
        return [], facts
    scanner = MarkupScanner(rep, budget, facts)
    try:
        scanner.feed(text)
        scanner.close()
        scanner.finish()
    except Exception as exc:
        rep.add(1, "--", "internal-error", "warning",
                f"perf_audit could not fully parse this file: {exc}",
                "Please report this file shape; the rest of the audit completed "
                "normally.")

    # Inline styles carrying a background image are invisible to the preload
    # scanner in exactly the same way `data-src` is.
    for m in URL_FUNC.finditer(text):
        url = m.group(1)
        if url.startswith("data:"):
            continue
        line = text.count("\n", 0, m.start()) + 1
        window = text[max(0, m.start() - 400):m.start()]
        if HERO_PAT.search(window):
            rep.add(line, "L", "lcp-css-background", "warning",
                    f"A hero-ish element takes its image from CSS: {Path(url).name}.",
                    "A CSS background image is discovered only after the "
                    "stylesheet has been downloaded, parsed, and matched against "
                    "the element — so it starts late by construction and cannot "
                    "carry `fetchpriority`. If it is the LCP element, make it a "
                    "real `<img>`; if it must stay in CSS, add "
                    "`<link rel=\"preload\" as=\"image\" fetchpriority=\"high\">`.")
    return rep.out, facts


# ---------------------------------------------------------------------------
# CSS scanning
# ---------------------------------------------------------------------------

def strip_css_comments(text: str) -> str:
    """Blank out comments while preserving line numbers and offsets."""
    out = list(text)
    i, n = 0, len(text)
    while i < n:
        ch = text[i]
        if ch in "\"'":
            quote, i = ch, i + 1
            while i < n and text[i] != quote:
                if text[i] == "\\":
                    i += 1
                i += 1
            i += 1
            continue
        if ch == "/" and i + 1 < n and text[i + 1] == "*":
            start = i
            i += 2
            while i + 1 < n and not (text[i] == "*" and text[i + 1] == "/"):
                i += 1
            i = min(i + 2, n)
            for j in range(start, i):
                if out[j] != "\n":
                    out[j] = " "
            continue
        i += 1
    return "".join(out)


@dataclass
class FontFace:
    family: str
    line: int
    src_files: list[str]
    has_display: bool
    has_metrics: bool
    has_unicode_range: bool
    is_local_only: bool


def parse_font_faces(clean: str) -> list[FontFace]:
    faces: list[FontFace] = []
    for m in re.finditer(r"@font-face\s*\{", clean):
        start = m.end()
        depth, i, n = 1, start, len(clean)
        while i < n and depth:
            if clean[i] == "{":
                depth += 1
            elif clean[i] == "}":
                depth -= 1
            i += 1
        body = clean[start:i - 1]
        fam = re.search(r"font-family\s*:\s*['\"]?([^;'\"]+)", body)
        srcs = [u for u in URL_FUNC.findall(body) if not u.startswith("data:")]
        faces.append(FontFace(
            family=(fam.group(1).strip() if fam else "?"),
            line=clean.count("\n", 0, m.start()) + 1,
            src_files=[Path(u.split("?")[0]).name for u in srcs],
            has_display="font-display" in body,
            has_metrics=bool(re.search(
                r"size-adjust|ascent-override|descent-override|line-gap-override", body)),
            has_unicode_range="unicode-range" in body,
            is_local_only=(not srcs and "local(" in body),
        ))
    return faces


def audit_css(path: Path, text: str
              ) -> tuple[list[Finding], list[FontFace], set[str], dict[str, int]]:
    rep = Reporter(str(path), text)
    if any(m in text[:800] for m in GENERATED_MARKERS):
        return [], [], set(), {}
    clean = strip_css_comments(text)

    for m in re.finditer(r"@import\b[^;]*;", clean):
        line = clean.count("\n", 0, m.start()) + 1
        rep.add(line, "L", "css-import", "error",
                "`@import` in a stylesheet.",
                "@import is discovered only after the importing sheet has been "
                "downloaded AND parsed, so it serialises what should be parallel: "
                "two round trips instead of one, both of them render-blocking. "
                "The preload scanner cannot see it either. Let the bundler "
                "inline it, or add a second `<link>` in the HTML — a link is "
                "found by the preload scanner in the first few kilobytes.")

    faces = parse_font_faces(clean)
    families = {f.family.strip().strip("'\"").lower() for f in faces}
    for f in faces:
        if f.is_local_only:
            continue
        if not f.has_display:
            rep.add(f.line, "C", "font-display-missing", "warning",
                    f"@font-face `{f.family}` does not set `font-display`.",
                    "The default is `auto`, which most engines treat as `block`: "
                    "up to three seconds of invisible text, and every one of "
                    "those frames is a frame where your LCP text has not "
                    "painted. Set `swap` and kill the reflow with a "
                    "metric-matched fallback, or `optional` if you would rather "
                    "drop the face than shift. See "
                    "web-design-studio/references/typography.md §8.")
        if not f.has_unicode_range:
            rep.add(f.line, "W", "font-not-subset", "warning",
                    f"@font-face `{f.family}` declares no `unicode-range`.",
                    "Without it the browser downloads the whole face for a page "
                    "that uses Latin. A subset plus `unicode-range` lets the "
                    "engine skip ranges the page never renders, and is usually a "
                    "50-80% saving on a font that ships Cyrillic and Greek "
                    "nobody asked for.")

    metric_families = {f.family.strip().strip("'\"").lower()
                       for f in faces if f.has_metrics}
    for f in faces:
        if f.is_local_only or f.has_metrics:
            continue
        fam = f.family.strip().strip("'\"").lower()
        if any(fam in other and other != fam for other in metric_families):
            continue
        if not metric_families:
            rep.add(f.line, "C", "font-no-metric-fallback", "warning",
                    f"`{f.family}` has no metric-matched fallback @font-face.",
                    "When the web font swaps in, a fallback with a different "
                    "x-height, ascent and descent re-wraps the text and changes "
                    "the block height — that reflow IS your CLS. Declare a second "
                    "@font-face over `local(Arial)` with MEASURED `size-adjust`, "
                    "`ascent-override`, `descent-override` and "
                    "`line-gap-override`, and slot it between the web font and "
                    "the generic stack. Real code and the arithmetic are in "
                    "references/diagnosis.md §6 and "
                    "web-design-studio/references/typography.md §8.")
            break

    for m in re.finditer(r"(transition(?:-property)?|animation(?:-name)?)\s*:\s*([^;}]+)",
                         clean):
        prop, value = m.group(1), m.group(2)
        line = clean.count("\n", 0, m.start()) + 1
        named = {p.strip().lower() for p in re.split(r"[,\s]+", value) if p.strip()}
        hits = sorted(named & LAYOUT_ANIMATED)
        if prop.startswith("transition") and hits:
            rep.add(line, "C", "animated-layout-prop", "warning",
                    f"`{prop}` animates layout propert"
                    f"{'y' if len(hits) == 1 else 'ies'}: {', '.join(hits)}.",
                    "Every frame of this animation runs layout, paint and "
                    "composite on the main thread, and every frame moves its "
                    "siblings — so it is a CLS source and a jank source at once. "
                    "`transform` and `opacity` are handled on the compositor "
                    "thread and cost neither. The substitution table (top/left → "
                    "translate, width/height → scale, box-shadow → an opacity "
                    "fade) is in "
                    "web-design-studio/references/motion-system.md §5.")
        if prop.startswith("transition") and re.match(r"^\s*all\b", value):
            rep.add(line, "C", "transition-all", "warning",
                    "`transition: all` animates properties you did not choose.",
                    "`all` includes every layout property the element might ever "
                    "have, so a future rule turns a cheap hover into a layout "
                    "pass. Name the properties.")

    # Selectors only: strip declaration blocks, at-rule statements and any
    # url(), so a `.css` in `@import url("extra.css")` is not read as a class.
    selectors_only = re.sub(r"\{[^{}]*\}", " ", clean)
    selectors_only = re.sub(r"@[\w-]+[^;{]*;", " ", selectors_only)
    selectors_only = URL_FUNC.sub(" ", selectors_only)
    classes = set(CSS_CLASS_SEL.findall(selectors_only))

    # `.hero__image { width: 720px }` is how most images get their rendered
    # size; the width attribute is the exception, not the rule.
    widths: dict[str, int] = {}
    for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", clean):
        sel, body = m.group(1), m.group(2)
        wm = re.search(r"(?<![\w-])(?:max-)?width\s*:\s*([\d.]+)px", body)
        if not wm:
            continue
        px = int(float(wm.group(1)))
        for cls in CSS_CLASS_SEL.findall(sel):
            widths[cls] = min(widths.get(cls, 10 ** 9), px)
        for idm in re.finditer(r"#([\w-]+)", sel):
            widths[idm.group(1)] = min(widths.get(idm.group(1), 10 ** 9), px)
    return rep.out, faces, classes, widths


# ---------------------------------------------------------------------------
# JS scanning
# ---------------------------------------------------------------------------

BODY_INJECT = re.compile(
    r"(document\.body|document\.documentElement)\s*\.\s*"
    r"(prepend|insertBefore)\b"
    r"|insertAdjacentHTML\s*\(\s*['\"]afterbegin['\"]")


def audit_js(path: Path, text: str) -> tuple[list[Finding], dict[str, set[str]], set[str]]:
    rep = Reporter(str(path), text)
    if any(m in text[:800] for m in GENERATED_MARKERS):
        return [], {}, set()

    for m in BODY_INJECT.finditer(text):
        line = text.count("\n", 0, m.start()) + 1
        rep.add(line, "C", "body-prepend", "warning",
                "Content is injected at the start of <body> after load.",
                "A cookie banner, promo bar or A/B wrapper prepended after "
                "first paint pushes the entire page down — one shift with a "
                "distance fraction near 1.0, which on its own can blow the 0.1 "
                "CLS budget. Reserve the space in the server-rendered HTML, "
                "render it in the initial response, or overlay it with "
                "`position: fixed` so it takes the page out of flow instead of "
                "displacing it.")

    pkgs: dict[str, set[str]] = {}
    for m in NODE_MODULES_PKG.finditer(text):
        pkgs.setdefault(m.group(1), set())
    for m in PKG_AT_VERSION.finditer(text):
        name, ver = m.group(1), m.group(2)
        if name in pkgs or "node_modules" in text:
            pkgs.setdefault(name, set()).add(ver)

    idents = set(WORDS.findall(text))
    return rep.out, pkgs, idents


# ---------------------------------------------------------------------------
# Budget loading and evaluation
# ---------------------------------------------------------------------------

def deep_merge(base: dict, over: dict) -> dict:
    out = dict(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def read_jsonc(raw: bytes):
    """Parse JSON that may carry // and /* */ comments and trailing commas.

    The budget file is written with the device and network in a comment
    (references/budgets.md §6), so it is JSONC, not JSON. Strings pass
    through untouched. The bytes may be UTF-16 or carry a byte-order mark,
    as PowerShell's `>` writes them."""
    text = raw.decode(json.detect_encoding(raw)).lstrip("﻿")
    pieces: list[tuple[bool, str]] = []
    i, n = 0, len(text)
    while i < n:
        if text[i] == '"':
            j = i + 1
            while j < n and text[j] != '"':
                j += 2 if text[j] == "\\" else 1
            pieces.append((True, text[i:j + 1]))
            i = j + 1
        elif text.startswith("//", i):
            j = text.find("\n", i)
            i = n if j < 0 else j
        elif text.startswith("/*", i):
            j = text.find("*/", i + 2)
            i = n if j < 0 else j + 2
        else:
            j = i
            while j < n and text[j] != '"' and not text.startswith(("//", "/*"), j):
                j += 1
            pieces.append((False, text[i:j]))
            i = j
    # Merge the code between strings, so a comment between a trailing comma
    # and its bracket cannot hide the comma from the regex.
    out, code = [], ""
    for is_string, piece in pieces:
        if is_string:
            out += [re.sub(r",(\s*[}\]])", r"\1", code), piece]
            code = ""
        else:
            code += piece
    out.append(re.sub(r",(\s*[}\]])", r"\1", code))
    return json.loads("".join(out))


def load_budget(path: str | None) -> tuple[dict, str]:
    """Returns (budget, provenance). A missing file is not an error — it is a
    prompt to go and set one."""
    if not path:
        return DEFAULT_BUDGET, "built-in defaults"
    p = Path(path)
    if not p.exists():
        return DEFAULT_BUDGET, f"built-in defaults ({path} not found)"
    try:
        data = read_jsonc(p.read_bytes())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SystemExit(f"perf_audit: cannot read budget {path}: {exc}")
    if data.get("$schema") not in (None, "perf-budget-gate/1"):
        raise SystemExit(
            f"perf_audit: {path} declares $schema {data.get('$schema')!r}; "
            f"this tool understands \"perf-budget-gate/1\".")
    return deep_merge(DEFAULT_BUDGET, data), str(p)


def resolve_page_budget(budget: dict, page_type: str | None) -> dict:
    """A marketing landing page and a data-heavy dashboard cannot share one
    number. `pages` entries are glob patterns over the page type or route."""
    resolved = dict(budget.get("defaults") or {})
    if not page_type:
        return resolved
    for pattern, over in (budget.get("pages") or {}).items():
        if fnmatch.fnmatch(page_type, pattern):
            resolved = deep_merge(resolved, over)
    return resolved


def human(n: float) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.2f}MB"
    if n >= 1000:
        return f"{n / 1000:.1f}KB"
    return f"{int(n)}B"


def check_budget(ledger: Ledger, pb: dict, facts: DocFacts) -> list[Finding]:
    rep = Reporter("<budget>")
    byte_budget = pb.get("bytes") or {}
    table = ledger.byte_table()
    for kind in ("total",) + BYTE_TYPES:
        limit = byte_budget.get(kind)
        if limit is None:
            continue
        actual = table.get(kind, 0)
        if actual > limit:
            over = actual - limit
            pct = (over / limit * 100) if limit else 100.0
            rep.add(1, "B", f"budget-{kind}", "error",
                    f"{kind} bytes {human(actual)} exceed the budget "
                    f"{human(limit)} by {human(over)} ({pct:.0f}%).",
                    f"A budget is a decision made before the pressure, so the "
                    f"answer is not to raise it here. Either cut {human(over)} "
                    f"from the {kind} column — the largest assets are listed "
                    f"above and the biggest one is almost always the answer — or "
                    f"run the review in references/budgets.md §7 and raise the "
                    f"number in the budget file with the reason in the commit "
                    f"message.",
                    snippet=f"{kind}:{limit}")

    req_budget = pb.get("requests") or {}
    counts = ledger.counts()
    for kind, limit in req_budget.items():
        actual = counts.get(kind, 0)
        if actual > limit:
            rep.add(1, "B", f"requests-{kind}", "error",
                    f"{kind} request count {actual} exceeds the budget {limit}.",
                    "Request count matters independently of bytes: each one is a "
                    "queue slot, and on a high-latency connection the round trips "
                    "dominate. Merge, inline the small ones, or drop the asset.",
                    snippet=f"req:{kind}:{limit}")

    largest = pb.get("largest_asset") or {}
    PER_KIND_FIX = {
        "image": "Resize it to twice the largest rendered CSS width, re-encode "
                 "as AVIF with a WebP and JPEG fallback, and ship a `srcset` so "
                 "a phone never downloads the desktop file.",
        "js": "Find what got imported — a bundle analyzer names it in about a "
              "minute — then code-split it behind the interaction that needs "
              "it, or replace the dependency. Moving it to a second chunk that "
              "still loads on first paint does not help; see "
              "references/diagnosis.md §9.",
        "css": "One stylesheet this large is usually a framework shipping for "
               "four components. Measure real coverage with DevTools' Coverage "
               "panel against a user journey before deleting anything.",
        "font": "Subset to the ranges the page renders and declare "
                "`unicode-range`; convert to woff2; prefer one variable file "
                "over three static weights.",
    }
    for kind, limit in largest.items():
        for a in sorted(ledger.by_kind(kind), key=lambda x: -x.transfer):
            if a.transfer <= limit:
                break
            rep.add(1, "B", "largest-asset", "error",
                    f"{a.rel} is {human(a.transfer)}, over the {kind} "
                    f"single-asset ceiling of {human(limit)}.",
                    "A per-asset ceiling exists because a total budget can be "
                    "met by a hundred small files or blown by one enormous one, "
                    "and only the second is a bug you can fix in an afternoon. "
                    + PER_KIND_FIX.get(kind, "Split it or delete it."),
                    snippet=a.rel)

    tp = pb.get("third_party") or {}
    if "origins" in tp and len(facts.third_party_origins) > tp["origins"]:
        rep.add(1, "B", "third-party-origins", "error",
                f"{len(facts.third_party_origins)} third-party origins exceed "
                f"the budget of {tp['origins']}: "
                f"{', '.join(sorted(facts.third_party_origins))}.",
                "Each new origin is a DNS lookup plus a TCP handshake plus a TLS "
                "negotiation before its first byte — 300-600ms on a mobile "
                "connection, spent before anything useful arrives. Third-party "
                "weight is budgeted separately because it is the one line nobody "
                "owns and therefore the one line that always grows; see "
                "references/budgets.md §5.",
                snippet="third-party-origins")
    if "scripts" in tp and facts.third_party_scripts > tp["scripts"]:
        rep.add(1, "B", "third-party-scripts", "error",
                f"{facts.third_party_scripts} third-party scripts exceed the "
                f"budget of {tp['scripts']}.",
                "A third-party script executes with your privileges on your main "
                "thread and can inject anything at any time, so it costs INP and "
                "CLS as well as bytes — and its size is not under your control "
                "between one deploy and the next. Budget the count, measure the "
                "bytes at runtime, and containerise the rest.",
                snippet="third-party-scripts")
    return rep.out


# ---------------------------------------------------------------------------
# Growth against a committed baseline
# ---------------------------------------------------------------------------

def load_baseline(path: str) -> tuple[set[str], dict]:
    p = Path(path)
    if not p.exists():
        return set(), {}
    try:
        data = json.loads(p.read_bytes())
    except (OSError, json.JSONDecodeError):
        print(f"perf_audit: could not read baseline {p}; auditing everything.",
              file=sys.stderr)
        return set(), {}
    if isinstance(data, list):           # audit_design's plain-list form
        return set(data), {}
    return set(data.get("findings") or []), (data.get("totals") or {})


def check_growth(ledger: Ledger, totals: dict, growth: dict) -> list[Finding]:
    """Report the delta per category, not just a pass/fail.

    Growth is the check that catches the regression nobody meant to make: a
    dependency added in a PR that looks unrelated. It is expressed as a
    percentage because an absolute ceiling is already covered by the byte
    budget, and because "this PR added 40% to the JS bundle" is a sentence a
    reviewer acts on.
    """
    rep = Reporter("<growth>")
    old = (totals or {}).get("bytes") or {}
    if not old:
        return []
    new = ledger.byte_table()
    for kind in ("total",) + BYTE_TYPES:
        before, after = old.get(kind), new.get(kind, 0)
        if not before:
            continue
        delta = after - before
        pct = delta / before * 100
        limit = growth.get(f"{kind}_pct")
        arrow = "+" if delta >= 0 else "-"
        if limit is None:
            continue
        if pct > limit:
            rep.add(1, "B", f"growth-{kind}", "error",
                    f"{kind} grew {arrow}{human(abs(delta))} "
                    f"({pct:+.1f}%) since the baseline: {human(before)} -> "
                    f"{human(after)}. Allowed: +{limit}%.",
                    "Growth is checked separately from the absolute budget "
                    "because a site can be inside its budget and still be one "
                    "dependency away from leaving it, and because a percentage "
                    "names the commit that did it. Find what was added — "
                    "`--json` prints the per-asset ledger — then either remove "
                    "it, split it out of the initial bundle, or re-record the "
                    "baseline in the same commit as the change that justifies it.",
                    snippet=f"growth:{kind}")
    return rep.out


def growth_summary(ledger: Ledger, totals: dict) -> list[str]:
    old = (totals or {}).get("bytes") or {}
    if not old:
        return []
    new = ledger.byte_table()
    rows = []
    for kind in ("total",) + BYTE_TYPES:
        before = old.get(kind)
        if before is None:
            continue
        after = new.get(kind, 0)
        if before == 0 and after == 0:
            continue
        delta = after - before
        pct = (delta / before * 100) if before else 0.0
        rows.append(f"  {kind:<8} {human(before):>9} -> {human(after):>9}  "
                    f"{('+' if delta >= 0 else '-') + human(abs(delta)):>10}  "
                    f"{pct:+6.1f}%")
    return rows


# ---------------------------------------------------------------------------
# Cross-file analysis
# ---------------------------------------------------------------------------

def audit_cross_file(ledger: Ledger, facts: DocFacts, faces: list[FontFace],
                     css_classes: set[str], source_tokens: set[str],
                     pkg_by_file: dict[str, dict[str, set[str]]],
                     any_html: bool) -> list[Finding]:
    """The findings no single file reveals.

    A font is not "un-preloaded" until you have read both the stylesheet that
    declares it and every HTML file that could have preloaded it. An origin is
    not "un-preconnected" until you know nobody added the hint. A dependency is
    not "duplicated" until you have seen two chunks.
    """
    rep = Reporter("<cross-file>")

    if any_html:
        for f in faces:
            if f.is_local_only or not f.src_files:
                continue
            if not any(name in facts.preloaded_fonts for name in f.src_files):
                rep.add(1, "L", "font-not-preloaded", "warning",
                        f"`{f.family}` is never preloaded ({', '.join(f.src_files)}).",
                        "A font referenced from CSS is discovered only after the "
                        "stylesheet is parsed AND an element matching the rule is "
                        "laid out — third in a chain of round trips. Preload the "
                        "ONE face used above the fold with `as=\"font\" "
                        "crossorigin`; preloading five makes all five slower "
                        "because they compete for the same connection.",
                        snippet=f.family)

        for origin in sorted(facts.third_party_origins):
            if origin not in facts.preconnects:
                rep.add(1, "L", "missing-preconnect", "warning",
                        f"Third-party origin `{origin}` has no preconnect.",
                        "The first request to a new origin pays DNS + TCP + TLS "
                        "before a single byte of the resource moves — typically "
                        "300-600ms on mobile. `<link rel=\"preconnect\">` runs "
                        "that handshake in parallel with the HTML parse. Use it "
                        "for origins on the critical path only (at most 3-4); "
                        "`dns-prefetch` is the cheaper hint for the rest. The "
                        "better fix for most of these is to self-host or delete "
                        "the origin.",
                        snippet=origin)

    for a in ledger.by_kind("font"):
        ext = a.path.suffix.lower()
        if ext in (".ttf", ".otf", ".eot", ".woff"):
            rep.add(1, "W", "legacy-font-format", "error",
                    f"{a.rel} ships as {ext} ({human(a.transfer)}).",
                    "woff2 is 25-35% smaller than woff and roughly half the size "
                    "of a raw ttf/otf, and it is supported by every browser that "
                    "has shipped since 2016. Shipping ttf, otf, eot or woff is "
                    "paying for compatibility nobody needs. Convert and delete "
                    "the old files.",
                    snippet=a.rel)

    for a in ledger.by_kind("image"):
        ext = a.path.suffix.lower()
        if ext in (".jpg", ".jpeg", ".png") and a.transfer > 100_000:
            stem = a.path.with_suffix("")
            modern = any(Path(str(stem) + e).exists() for e in (".avif", ".webp"))
            if not modern:
                rep.add(1, "W", "image-format", "warning",
                        f"{a.rel} is {human(a.transfer)} of {ext[1:].upper()} "
                        f"with no AVIF/WebP sibling.",
                        "AVIF typically lands 40-60% below JPEG at matched "
                        "quality and WebP 25-35% below, and both are supported "
                        "everywhere that matters. Emit all three and let "
                        "`<picture>` choose, so a browser that cannot decode "
                        "AVIF still gets the JPEG. Format is the cheapest of the "
                        "three image levers; the other two are dimensions and "
                        "quality, in that order of yield.",
                        snippet=a.rel)
        if ext == ".svg" and a.raw > 20_000:
            rep.add(1, "W", "svg-oversized", "warning",
                    f"{a.rel} is {human(a.raw)} of SVG.",
                    "An SVG this large is almost always a traced raster or an "
                    "un-run export: full-precision path coordinates, editor "
                    "metadata, and one <path> per pixel cluster. Run it through "
                    "SVGO, or admit it is a photograph and ship an AVIF. SVG "
                    "wins on flat shapes and loses badly on gradients and "
                    "traced detail.",
                    snippet=a.rel)

    # A package present in two chunks is shipped twice; two versions of one
    # package is the same code compiled twice with different bugs.
    everywhere: dict[str, set[str]] = {}
    versions: dict[str, set[str]] = {}
    for file, pkgs in pkg_by_file.items():
        for name, vers in pkgs.items():
            everywhere.setdefault(name, set()).add(file)
            versions.setdefault(name, set()).update(vers)
    for name, files in sorted(everywhere.items()):
        if len(versions.get(name, set())) > 1:
            rep.add(1, "W", "duplicate-dependency-version", "error",
                    f"`{name}` appears at {len(versions[name])} versions: "
                    f"{', '.join(sorted(versions[name]))}.",
                    "Two versions of one package is that package's whole cost "
                    "paid twice, plus a class of bug where two copies of a "
                    "singleton disagree. Run `npm ls <pkg>` to find who pinned "
                    "the old one, then dedupe or add a resolutions/overrides "
                    "entry.",
                    snippet=name)
        elif len(files) > 1:
            rep.add(1, "W", "duplicate-dependency", "warning",
                    f"`{name}` is inlined into {len(files)} chunks "
                    f"({', '.join(sorted(Path(f).name for f in files)[:3])}).",
                    "A shared dependency copied into several chunks is "
                    "downloaded and parsed once per chunk. Promote it to a "
                    "shared chunk so it is fetched once and cached across "
                    "routes. Detection here reads `node_modules/` paths left in "
                    "the output, so it sees what the bundler chose to keep — "
                    "run your bundle analyzer to confirm before acting.",
                    snippet=name)

    if css_classes and source_tokens:
        unmatched = {c for c in css_classes if c not in source_tokens}
        if css_classes and len(unmatched) / len(css_classes) > 0.4 and len(css_classes) > 40:
            pct = len(unmatched) / len(css_classes) * 100
            sample = ", ".join(sorted(unmatched)[:6])
            rep.add(1, "W", "unused-css", "warning",
                    f"{pct:.0f}% of class selectors ({len(unmatched)} of "
                    f"{len(css_classes)}) match no class in any scanned "
                    f"HTML or JS: {sample}…",
                    "This is a HEURISTIC and it is wrong whenever class names "
                    "are composed at runtime (`btn-${variant}`), injected by a "
                    "CMS, or used in a template this run did not scan — so "
                    "confirm before deleting anything. What it is good for is "
                    "the shape of the number: 60% unmatched usually means a full "
                    "framework stylesheet is shipping for four components. The "
                    "reliable version of this measurement is Chrome DevTools' "
                    "Coverage panel against a real user journey.",
                    snippet="unused-css")
    return rep.out


def check_oversized_images(ledger: Ledger, uses: list[ImgUse],
                           class_widths: dict[str, int]) -> list[Finding]:
    """An image is oversized when its intrinsic pixels far exceed the box it
    is rendered into.

    Rendered width comes from the `width` attribute when there is one and from
    a px `width`/`max-width` on one of the element's classes otherwise. A width
    in `%`, `ch`, `vw` or `auto` is not resolvable without a layout, so those
    images are skipped rather than guessed at — `measure_vitals.mjs` reports
    real rendered sizes when you need them.

    2x intrinsic is correct: it is what a retina display consumes. 2.5x is
    worth a warning, 3x and beyond is an error, because bytes scale with the
    SQUARE of the linear ratio.
    """
    rep = Reporter("<images>")
    by_name: dict[str, Asset] = {}
    for a in ledger.assets:
        if a.kind == "image":
            by_name.setdefault(a.path.name, a)

    seen: set[tuple[str, int]] = set()
    for use in uses:
        a = by_name.get(use.src)
        if not a or not a.width:
            continue
        css_w = use.attr_width or min(
            [class_widths[t] for t in use.tokens if t in class_widths] or [0])
        if css_w <= 0:
            continue
        ratio = a.width / css_w
        if ratio < 2.5:
            continue
        if (a.rel, css_w) in seen:
            continue
        seen.add((a.rel, css_w))
        ideal = int(a.transfer / (ratio / 2) ** 2)
        sev = "error" if ratio >= 3 else "warning"
        rep.add(1, "W", "oversized-image", sev,
                f"{a.rel} is {a.width}x{a.height} intrinsic but renders at "
                f"{css_w}px wide ({ratio:.1f}x). {human(a.transfer)} where "
                f"~{human(ideal)} would look identical.",
                "Bytes scale with the SQUARE of linear size, so shipping at 3x "
                "the needed width costs about nine times the pixels and buys "
                "nothing over a 2x file — the extra detail is thrown away by "
                "the downscale before it reaches a single retina subpixel. "
                "Resize to twice the largest rendered CSS width, then let "
                "`srcset`/`sizes` pick per viewport, which is the only way one "
                "file stops being wrong for every device.",
                snippet=f"{a.rel}@{Path(use.doc).name}:{use.line}")
    return rep.out


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def iter_files(paths: Iterable[str]) -> Iterator[Path]:
    for raw in paths:
        p = Path(raw)
        if p.is_file():
            yield p
        elif p.is_dir():
            for root, dirs, files in os.walk(p):
                dirs[:] = [d for d in dirs
                           if d not in SKIP_DIRS and not d.startswith(".")]
                for f in sorted(files):
                    yield Path(root) / f


SRC_EXT = HTML_EXT | CSS_EXT | JS_EXT


def audit(build_paths: list[str], src_paths: list[str], budget: dict,
          page_type: str | None, include_maps: bool) -> tuple[list[Finding], Ledger, DocFacts]:
    measure = budget.get("measure", "gzip")
    ledger = Ledger()
    findings: list[Finding] = []
    facts = DocFacts()
    faces: list[FontFace] = []
    css_classes: set[str] = set()
    class_widths: dict[str, int] = {}
    source_tokens: set[str] = set()
    pkg_by_file: dict[str, dict[str, set[str]]] = {}
    any_html = False

    roots = [Path(p) for p in build_paths]

    def relative(fp: Path) -> str:
        for r in roots:
            try:
                if r.is_dir():
                    return str(fp.relative_to(r))
            except ValueError:
                continue
        return str(fp)

    def scan_source(fp: Path) -> None:
        nonlocal faces, css_classes, source_tokens, any_html, class_widths
        ext = fp.suffix.lower()
        if ext not in SRC_EXT:
            return
        try:
            text = fp.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return
        try:
            if ext in HTML_EXT:
                any_html = True
                f, doc = audit_html(fp, text, budget)
                findings.extend(f)
                facts.preloaded_fonts |= doc.preloaded_fonts
                facts.preconnects |= doc.preconnects
                facts.third_party_origins |= doc.third_party_origins
                facts.third_party_scripts += doc.third_party_scripts
                facts.class_tokens |= doc.class_tokens
                facts.img_uses.extend(doc.img_uses)
                source_tokens |= doc.class_tokens
            elif ext in CSS_EXT:
                f, ff, cls, widths = audit_css(fp, text)
                findings.extend(f)
                faces.extend(ff)
                css_classes |= cls
                for k, v in widths.items():
                    class_widths[k] = min(class_widths.get(k, 10 ** 9), v)
            else:
                f, pkgs, idents = audit_js(fp, text)
                findings.extend(f)
                if pkgs:
                    pkg_by_file[str(fp)] = pkgs
                source_tokens |= idents
        except Exception as exc:       # a crashed rule must never block a commit
            findings.append(Finding(
                str(fp), 1, "--", "internal-error", "warning",
                f"perf_audit could not fully analyse this file: {exc}",
                "Please report this file shape; the rest of the audit completed "
                "normally."))

    for fp in iter_files(build_paths):
        rel = relative(fp).replace(os.sep, "/")
        if NOT_SHIPPED.search(rel) and not include_maps:
            continue
        try:
            data = fp.read_bytes()
        except OSError:
            continue
        kind = classify(fp)
        w = h = 0
        if kind == "image":
            w, h = image_size(data, fp.suffix.lower())
        ledger.assets.append(Asset(
            path=fp, rel=rel, kind=kind, raw=len(data),
            transfer=transfer_size(fp, data, measure), width=w, height=h))
        scan_source(fp)

    mark_alternates(ledger.assets)

    for fp in iter_files(src_paths):
        scan_source(fp)

    pb = resolve_page_budget(budget, page_type)
    findings.extend(check_budget(ledger, pb, facts))
    findings.extend(audit_cross_file(ledger, facts, faces, css_classes,
                                     source_tokens, pkg_by_file, any_html))
    findings.extend(check_oversized_images(ledger, facts.img_uses, class_widths))
    findings.sort(key=lambda f: (f.file, f.line, SEVERITY_ORDER.get(f.severity, 9)))
    return findings, ledger, facts


# ---------------------------------------------------------------------------
# Reporting — deliberately the same shape as audit_design.py's
# ---------------------------------------------------------------------------

def _wrap(s: str, width: int) -> list[str]:
    words, out, cur = s.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > width:
            out.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        out.append(cur)
    return out


def ledger_report(ledger: Ledger, pb: dict, provenance: str,
                  use_color: bool) -> str:
    def c(code: str, s: str) -> str:
        return f"\033[{code}m{s}\033[0m" if use_color else s

    byte_budget = pb.get("bytes") or {}
    table = ledger.byte_table()
    counts = ledger.counts()
    buf = [c("1", "Weight ledger") + f"   (budget: {provenance})",
           f"  {'':8} {'transfer':>10} {'budget':>10} {'used':>7}  requests"]
    for kind in ("total",) + BYTE_TYPES:
        actual = table.get(kind, 0)
        if actual == 0 and kind != "total" and byte_budget.get(kind) is None:
            continue
        limit = byte_budget.get(kind)
        pct = f"{actual / limit * 100:.0f}%" if limit else "  -"
        over = limit is not None and actual > limit
        row = (f"  {kind:<8} {human(actual):>10} "
               f"{(human(limit) if limit is not None else '-'):>10} {pct:>7}  "
               f"{counts.get(kind, 0)}")
        buf.append(c("31", row) if over else row)

    biggest = sorted(ledger.assets, key=lambda a: -a.transfer)[:8]
    if biggest:
        buf.append("")
        buf.append(c("1", "  Largest assets"))
        for a in biggest:
            dims = f"  {a.width}x{a.height}" if a.width else ""
            alt = f"   [alternate of {a.alternate_of}, not counted]" \
                if not a.counted else ""
            buf.append(f"    {human(a.transfer):>9}  {a.kind:<6} "
                       f"{a.rel}{dims}{alt}")
    return "\n".join(buf) + "\n"


def report(findings: list[Finding], *, use_color: bool, show_fix: bool) -> str:
    if not findings:
        return "perf audit: clean — every budget holds.\n"

    def c(code: str, s: str) -> str:
        return f"\033[{code}m{s}\033[0m" if use_color else s

    buf: list[str] = []
    by_file: dict[str, list[Finding]] = {}
    for f in findings:
        by_file.setdefault(f.file, []).append(f)

    for file, items in by_file.items():
        buf.append(c("1", file))
        for f in items:
            tag = c("31", "error") if f.severity == "error" else c("33", "warn ")
            buf.append(f"  {f.line:>5}  {tag}  {c('36', f.cat)} "
                       f"{f.rule:<28} {f.message}")
            if show_fix:
                for ln in _wrap(f.fix, 92):
                    buf.append(f"         {c('2', ln)}")
        buf.append("")

    errors = sum(1 for f in findings if f.severity == "error")
    warns = len(findings) - errors
    buf.append(c("1", "Summary"))
    counts: dict[str, int] = {}
    for f in findings:
        counts[f.cat] = counts.get(f.cat, 0) + 1
    for cat in sorted(counts):
        buf.append(f"  {cat}   {CATEGORY_NAMES.get(cat, ''):<20} {counts[cat]}")
    buf.append(f"\n  {errors} error(s), {warns} warning(s) "
               f"across {len(by_file)} file(s).")
    return "\n".join(buf) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="python -m scripts.perf_audit",
        description="The static performance gate: byte budgets, LCP/CLS/"
                    "main-thread risks, and growth against a baseline.",
        epilog="Exit codes: 0 clean, 1 violations, 2 bad invocation.")
    ap.add_argument("paths", nargs="*", default=["."],
                    help="build output directories or files; these are weighed "
                         "AND scanned (default: .)")
    ap.add_argument("--src", action="append", default=[], metavar="DIR",
                    help="source to scan for markup/CSS/JS problems but NOT "
                         "count toward byte budgets (repeatable)")
    ap.add_argument("--budget", metavar="FILE", default=None,
                    help="budget file (default: the project's .design-suite.json "
                         "budgets.perf, else perf-budget.json; built-in defaults "
                         "are used if it is missing)")
    ap.add_argument("--page-type", metavar="NAME",
                    help="select a per-page-type budget from the `pages` map")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--strict", action="store_true",
                    help="warnings fail the run too")
    ap.add_argument("--quiet", action="store_true",
                    help="suppress the fix guidance")
    ap.add_argument("--no-color", action="store_true")
    ap.add_argument("--no-ledger", action="store_true",
                    help="suppress the weight table")
    ap.add_argument("--include-maps", action="store_true",
                    help="count sourcemaps and other non-shipped files")
    ap.add_argument("--baseline", metavar="FILE", default=None,
                    help="ignore findings recorded here and compare byte totals "
                         "against it (default: the project's .design-suite.json "
                         "baselines.perf, else .perf-baseline.json)")
    ap.add_argument("--write-baseline", metavar="FILE",
                    help="record current findings and byte totals so only NEW "
                         "violations and real growth fail")
    ap.add_argument("--category", action="append", metavar="X",
                    help="only report these categories: B L C T W (repeatable)")
    args = ap.parse_args(argv)

    paths = args.paths or ["."]
    missing = [p for p in list(paths) + list(args.src) if not Path(p).exists()]
    if missing:
        print(f"perf_audit: no such path: {', '.join(missing)}", file=sys.stderr)
        return 2

    # A flag beats the project's .design-suite.json, which beats the default (P24).
    try:
        config = project_config()
    except ConfigError as exc:
        print(f"perf_audit: {exc}", file=sys.stderr)
        return 2
    args.budget = args.budget or config_path(config, "budgets", "perf") or "perf-budget.json"
    args.baseline = args.baseline or config_path(config, "baselines", "perf") or ".perf-baseline.json"

    try:
        budget, provenance = load_budget(args.budget)
    except SystemExit as exc:
        print(str(exc), file=sys.stderr)
        return 2

    findings, ledger, facts = audit(list(paths), list(args.src), budget,
                                    args.page_type, args.include_maps)
    pb = resolve_page_budget(budget, args.page_type)

    if args.category:
        wanted = {c.upper() for c in args.category}
        findings = [f for f in findings if f.cat in wanted]

    if args.write_baseline:
        payload = {
            "$schema": "perf-budget-gate/baseline/1",
            "findings": sorted({f.key() for f in findings}),
            "totals": {"bytes": ledger.byte_table(),
                       "requests": ledger.counts()},
        }
        Path(args.write_baseline).write_text(
            json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(f"perf_audit: recorded {len(findings)} finding(s) and "
              f"{human(ledger.total_bytes())} of assets as the baseline in "
              f"{args.write_baseline}.\nOnly NEW violations and growth past "
              f"`budget.growth` will fail from now on. Pay the debt down per "
              f"page type, not all at once.")
        return 0

    baseline_keys, baseline_totals = load_baseline(args.baseline)
    findings.extend(check_growth(ledger, baseline_totals,
                                 budget.get("growth") or {}))
    if baseline_keys:
        findings = [f for f in findings if f.key() not in baseline_keys]
    findings.sort(key=lambda f: (f.file, f.line, SEVERITY_ORDER.get(f.severity, 9)))

    if args.json:
        print(json.dumps({
            "findings": [asdict(f) for f in findings],
            "ledger": {
                "bytes": ledger.byte_table(),
                "requests": ledger.counts(),
                "assets": [{"path": a.rel, "kind": a.kind, "raw": a.raw,
                            "transfer": a.transfer,
                            **({"width": a.width, "height": a.height}
                               if a.width else {})}
                           for a in sorted(ledger.assets, key=lambda x: -x.transfer)],
            },
            "budget": pb,
            "third_party_origins": sorted(facts.third_party_origins),
        }, indent=2))
    else:
        use_color = not args.no_color and sys.stdout.isatty()
        if not args.no_ledger:
            sys.stdout.write(ledger_report(ledger, pb, provenance, use_color))
            rows = growth_summary(ledger, baseline_totals)
            if rows:
                sys.stdout.write("\nSince baseline\n" + "\n".join(rows) + "\n")
            sys.stdout.write("\n")
        sys.stdout.write(report(findings, use_color=use_color,
                                show_fix=not args.quiet))

    failing = [f for f in findings
               if f.severity == "error" or (args.strict and f.severity == "warning")]
    return 1 if failing else 0


if __name__ == "__main__":
    # A Windows pipe (git hook, CI, `> file`) defaults to the ANSI code page,
    # where printing →, Δ or ✓ raises UnicodeEncodeError. Consoles and
    # Claude Code already use UTF-8 and are left alone.
    for _stream in (sys.stdout, sys.stderr):
        if getattr(_stream, "encoding", "utf-8").lower() not in ("utf-8", "utf8"):
            _stream.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
