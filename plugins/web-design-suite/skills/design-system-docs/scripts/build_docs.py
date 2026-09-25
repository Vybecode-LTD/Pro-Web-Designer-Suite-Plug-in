#!/usr/bin/env python3
"""
build_docs.py — turn system.json into a documentation site, and catch drift.

`extract_system.py` answers "what is in the system?". This answers "what does a
person need to see, and in what order?" — and, in `--check` mode, "what changed
since the version we published?".

Two rules the whole script is built around:

  1. GENERATED AND HAND-WRITTEN CONTENT NEVER SHARE A FILE. Everything under
     --out is disposable and is rewritten on every run. Everything under --prose
     is yours and is never written to. The pages join them; regeneration cannot
     eat prose because regeneration never opens the prose files for writing.

  2. THE SITE OBEYS THE NINE LAWS ITSELF. It is a demonstration of the system it
     documents, so a hardcoded value in its own chrome is a bug. `--emit-css`
     writes the chrome stylesheet out as a real file so `audit_design.py` can
     read it, and it carries no @generated marker on purpose: the auditor skips
     generated files, and a skipped audit proves nothing.

Prose merge convention (all optional, all relative to --prose)
--------------------------------------------------------------
  overview.md                 the landing page's body
  principles.md               the principles page
  tokens/<group>.md           prepended to that token group's section
  components/<name>.md        appended to that component's page
  components/<name>.example.html   replaces the generated example markup
  patterns/<slug>.md          one pattern page each

Usage
-----
    python -m scripts.build_docs docs/system.json --out docs/site/
    python -m scripts.build_docs docs/system.json --out docs/site/ --prose docs/prose
    python -m scripts.build_docs docs/system.json --only button --no-examples --out /tmp/d
    python -m scripts.build_docs build/system.json --baseline docs/system.json \\
        --prose docs/prose --check                              # CI: drift gate
    python -m scripts.build_docs build/system.json --out build/docs \\
        --emit-css build/docs-chrome.css --emit-examples build/examples

Exit codes: 0 built / no drift · 1 drift found in --check · 2 bad invocation.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

# The CSS scanner and the colour math live in extract_system.py. Importing them
# is the point: a second parser in this file is a second set of bugs and a
# second opinion about what a socket is.
# A sibling import would otherwise leave __pycache__ inside the installed
# plugin, which is read-only as far as a project is concerned.
sys.dont_write_bytecode = True
try:                                              # python -m scripts.build_docs
    from .extract_system import CssFile, SEVEN_STATES, strip_guards
except ImportError:                               # python scripts/build_docs.py
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from extract_system import CssFile, SEVEN_STATES, strip_guards

SCHEMA = "design-system-docs/system/1"

GROUP_ORDER = ("spacing", "typography", "color", "shape", "elevation", "motion",
               "layout", "other")

GROUP_BLURB = {
    "spacing": "Pick by relationship, never by pixels. The ladder converts meaning "
               "into a value, which is what makes the value checkable.",
    "typography": "Every role is a `font` shorthand, so weight, size, leading and "
                  "family travel together and cannot drift apart.",
    "color": "Components read roles. Dark mode re-points the roles and changes not "
             "one component rule — that is the whole test of the token layer.",
    "shape": "Primitives with no role layer: components read these directly, and "
             "that is correct.",
    "elevation": "Elevation is a shadow pair — a tight contact shadow plus a wider "
                 "ambient one. Single-shadow elevation looks like a sticker.",
    "motion": "Duration and easing travel as a pair. Split them and they drift.",
    "layout": "Breakpoints, the z-index ladder and the container widths.",
    "other": "Tokens this build could not place in a group.",
}

STATE_MEANING = {
    "default": "Nothing has happened yet. Everything else is measured against this.",
    "hover": "A pointer is over it. Must compose over the variant, not replace it.",
    "focus-visible": "The keyboard is here. The ring pairs box-shadow with a "
                     "transparent outline so it survives forced-colors mode.",
    "active": "Being pressed right now. Shorter and stronger than hover.",
    "disabled": "Cannot be used. Must not read as the brand accent, and must still "
                "be perceivable — exempt from contrast, not from legibility.",
    "loading": "Working. Must not change the box, or the thing the user was about "
               "to click moves out from under them.",
    "error": "Invalid. Carried by `aria-invalid`, never by colour alone.",
}

#: The five-part shape's own section banners. They are comments above the root
#: rule, so they look like a component summary and are not one.
FIVE_PART_BANNER = re.compile(
    r"\b(SOCKET BLOCK|THE STRUCTURE|VARIANTS|STATES|PARTS)\b", re.I)

DEFAULT_KEYBOARD = {
    "button": [("Enter / Space", "Activate"), ("Tab", "Move focus in and out")],
    "a": [("Enter", "Follow the link"), ("Tab", "Move focus in and out")],
    "input": [("Tab", "Move focus in and out"), ("Esc", "Revert, where the field supports it")],
}


# ===========================================================================
# 1. A SMALL MARKDOWN RENDERER
#
# Enough for documentation prose: headings, tables, lists, fenced code,
# blockquotes and inline spans. No dependency, no configuration, no surprises.
# ===========================================================================

INLINE_CODE = re.compile(r"`([^`]+)`")
BOLD = re.compile(r"\*\*([^*]+)\*\*")
ITALIC = re.compile(r"(?<![\w*])\*([^*\n]+)\*(?![\w*])")
LINK = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")


def esc(text: str) -> str:
    return html.escape(str(text), quote=True)


def inline_md(text: str) -> str:
    out = esc(text)
    out = INLINE_CODE.sub(lambda m: f"<code>{m.group(1)}</code>", out)
    out = BOLD.sub(lambda m: f"<strong>{m.group(1)}</strong>", out)
    out = ITALIC.sub(lambda m: f"<em>{m.group(1)}</em>", out)
    out = LINK.sub(lambda m: f'<a href="{m.group(2)}">{m.group(1)}</a>', out)
    return out


def render_markdown(md: str, *, heading_offset: int = 0,
                    collect: Optional[List[Dict[str, str]]] = None) -> str:
    """Render a markdown subset. `collect` receives every code fence."""
    lines = md.replace("\r\n", "\n").split("\n")
    out: List[str] = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        if line.strip().startswith("```"):
            lang = line.strip()[3:].strip()
            body: List[str] = []
            i += 1
            while i < n and not lines[i].strip().startswith("```"):
                body.append(lines[i])
                i += 1
            i += 1
            code = "\n".join(body)
            if collect is not None:
                collect.append({"lang": lang or "text", "code": code})
            out.append(f'<pre class="docs-code" data-lang="{esc(lang or "text")}">'
                       f"<code>{esc(code)}</code></pre>")
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            level = min(6, len(m.group(1)) + heading_offset)
            text = m.group(2).strip()
            anchor = slug(text)
            out.append(f'<h{level} id="{anchor}" class="docs-h">{inline_md(text)}</h{level}>')
            i += 1
            continue
        if re.match(r"^\s*\|.*\|\s*$", line) and i + 1 < n and re.match(
                r"^\s*\|[\s:|-]+\|\s*$", lines[i + 1]):
            head = [c.strip() for c in line.strip().strip("|").split("|")]
            i += 2
            rows = []
            while i < n and re.match(r"^\s*\|.*\|\s*$", lines[i]):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            out.append(table_html(head, rows))
            continue
        if re.match(r"^\s*([-*+]|\d+\.)\s+", line):
            ordered = bool(re.match(r"^\s*\d+\.\s+", line))
            items: List[str] = []
            while i < n and re.match(r"^\s*([-*+]|\d+\.)\s+", lines[i]):
                items.append(re.sub(r"^\s*([-*+]|\d+\.)\s+", "", lines[i]))
                i += 1
                while i < n and lines[i].startswith("  ") and lines[i].strip():
                    items[-1] += " " + lines[i].strip()
                    i += 1
            tag = "ol" if ordered else "ul"
            body = "".join(f"<li>{inline_md(x)}</li>" for x in items)
            out.append(f'<{tag} class="docs-list">{body}</{tag}>')
            continue
        if line.strip().startswith(">"):
            quote = []
            while i < n and lines[i].strip().startswith(">"):
                quote.append(lines[i].strip().lstrip(">").strip())
                i += 1
            out.append(f'<blockquote class="docs-quote">{inline_md(" ".join(quote))}</blockquote>')
            continue
        if re.match(r"^\s*(-{3,}|\*{3,}|_{3,})\s*$", line):
            out.append('<hr class="docs-rule">')
            i += 1
            continue
        if not line.strip():
            i += 1
            continue
        para = []
        while i < n and lines[i].strip() and not re.match(
                r"^\s*(#{1,6}\s|[-*+]\s|\d+\.\s|>|\||```)", lines[i]):
            para.append(lines[i].strip())
            i += 1
        out.append(f'<p class="docs-p">{inline_md(" ".join(para))}</p>')
    return "\n".join(out)


def table_html(head: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    th = "".join(f"<th>{inline_md(h)}</th>" for h in head)
    body = "".join(
        "<tr>" + "".join(f"<td>{inline_md(c)}</td>" for c in row) + "</tr>" for row in rows)
    return f'<div class="docs-scroll"><table class="docs-table"><thead><tr>{th}</tr>' \
           f"</thead><tbody>{body}</tbody></table></div>"


def slug(text: str) -> str:
    s = re.sub(r"[^\w\s-]", "", str(text).lower()).strip()
    return re.sub(r"[\s_]+", "-", s) or "x"


# ===========================================================================
# 2. THE CHROME STYLESHEET
#
# Read it as documentation in its own right: this is what a stylesheet written
# under the nine laws looks like when nobody is watching. Every value is a role;
# the only literals are the ratios and keywords that cannot be tokens.
# ===========================================================================

CHROME_CSS = """@layer reset, tokens, base, layout, components, utilities, docs, overrides;

@layer docs {
  /* ------------------------------------------------------------------
     1. THE SOCKET BLOCK — the docs shell's Tier-3 API. Every adjustable
        value, declared once, defaulting to a Tier-2 role.
     ------------------------------------------------------------------ */
  .docs {
    --docs-rail:        calc(var(--width-content) / 4);
    --docs-gap:         var(--gap-separate);
    --docs-pad:         var(--pad-card);
    --docs-bg:          var(--bg-canvas);
    --docs-fg:          var(--fg-default);
    --docs-border:      var(--border-subtle);
    --docs-radius:      var(--radius-lg);
    --docs-motion:      var(--motion-hover);

    display: grid;
    grid-template-columns: minmax(0, 1fr);
    gap: var(--docs-gap);
    min-block-size: 100svh;
    padding-inline: var(--gutter-page);
    padding-block: var(--space-block);
    background-color: var(--docs-bg);
    color: var(--docs-fg);
    font: var(--type-body);
  }

  @media (min-width: 64rem) {
    .docs { grid-template-columns: var(--docs-rail) minmax(0, 1fr); }
  }

  /* ------------------------------------------------------------------
     2. THE RAIL
     ------------------------------------------------------------------ */
  .docs__rail {
    display: flex;
    flex-direction: column;
    gap: var(--gap-grouped);
    align-self: start;
    position: sticky;
    inset-block-start: var(--space-block);
  }

  .docs__brand { font: var(--type-h4); color: var(--fg-strong); }
  .docs__tagline { font: var(--type-label); color: var(--fg-muted); }

  .docs__nav { display: flex; flex-direction: column; gap: var(--gap-fused); }

  .docs__link {
    padding-inline: var(--pad-inline-sm);
    padding-block: var(--pad-block-xs);
    border-radius: var(--radius-md);
    color: var(--fg-muted);
    font: var(--type-ui);
    text-decoration: none;
    transition: background-color var(--docs-motion), color var(--docs-motion);
  }

  .docs__link:hover { background-color: var(--bg-hover); color: var(--fg-default); }

  .docs__link:focus-visible {
    outline: var(--stroke-focus) solid transparent;
    box-shadow: var(--shadow-focus);
  }

  .docs__link[aria-current="page"] {
    background-color: var(--bg-selected);
    color: var(--fg-accent);
  }

  /* ------------------------------------------------------------------
     3. CONTROLS — search, theme, density
     ------------------------------------------------------------------ */
  .docs__controls { display: flex; flex-wrap: wrap; gap: var(--gap-tight); }

  .docs__search {
    inline-size: 100%;
    padding-inline: var(--pad-inline-sm);
    padding-block: var(--pad-block-sm);
    border: var(--stroke-default) solid var(--border-default);
    border-radius: var(--radius-md);
    background-color: var(--bg-sunken);
    color: var(--fg-default);
    font: var(--type-ui);
  }

  .docs__search:focus-visible {
    outline: var(--stroke-focus) solid transparent;
    box-shadow: var(--shadow-focus);
  }

  .docs__toggle {
    display: inline-flex;
    align-items: center;
    gap: var(--gap-fused);
    min-block-size: var(--tap-min);
    padding-inline: var(--pad-inline-sm);
    border: var(--stroke-default) solid var(--border-default);
    border-radius: var(--radius-md);
    background-color: var(--bg-surface);
    color: var(--fg-default);
    font: var(--type-ui);
    cursor: pointer;
    transition: background-color var(--docs-motion), border-color var(--docs-motion);
  }

  .docs__toggle:hover { background-color: var(--bg-hover); border-color: var(--border-strong); }

  .docs__toggle:focus-visible {
    outline: var(--stroke-focus) solid transparent;
    box-shadow: var(--shadow-focus);
  }

  /* ------------------------------------------------------------------
     4. CONTENT
     ------------------------------------------------------------------ */
  .docs__main { display: flex; flex-direction: column; gap: var(--space-subsection); }

  .docs__section { display: flex; flex-direction: column; gap: var(--gap-grouped); }

  .docs-h { color: var(--fg-strong); font: var(--type-h3); }
  h1.docs-h, .docs__title { font: var(--type-h1); }
  h2.docs-h { font: var(--type-h2); }
  h4.docs-h, h5.docs-h, h6.docs-h { font: var(--type-h4); }
  .docs-p { max-inline-size: var(--measure-prose); }
  .docs-list { max-inline-size: var(--measure-prose); padding-inline-start: var(--space-block); }
  .docs-rule { border: 0; border-block-start: var(--stroke-default) solid var(--docs-border); }

  .docs-quote {
    padding-inline-start: var(--pad-inline-md);
    border-inline-start: var(--stroke-thick) solid var(--border-accent);
    color: var(--fg-muted);
    max-inline-size: var(--measure-prose);
  }

  .docs-code {
    padding: var(--pad-well);
    border-radius: var(--radius-md);
    background-color: var(--bg-sunken);
    color: var(--fg-default);
    font: var(--type-code);
    overflow-x: auto;
  }

  .docs-scroll { overflow-x: auto; }

  .docs-table {
    inline-size: 100%;
    border-collapse: collapse;
    font: var(--type-ui);
  }

  .docs-table th {
    padding-inline: var(--pad-inline-sm);
    padding-block: var(--pad-block-sm);
    border-block-end: var(--stroke-default) solid var(--border-default);
    color: var(--fg-muted);
    font: var(--type-label);
    text-align: start;
    white-space: nowrap;
  }

  .docs-table td {
    padding-inline: var(--pad-inline-sm);
    padding-block: var(--pad-block-sm);
    border-block-end: var(--stroke-default) solid var(--docs-border);
    vertical-align: top;
  }

  .docs-table code { font: var(--type-code); }

  /* ------------------------------------------------------------------
     5. PARTS — swatches, cards, badges, examples
     ------------------------------------------------------------------ */
  .docs__swatch {
    display: inline-block;
    inline-size: var(--tap-min);
    block-size: var(--space-6);
    border: var(--stroke-default) solid var(--docs-border);
    border-radius: var(--radius-sm);
    background-color: var(--docs-swatch, transparent);
    vertical-align: middle;
  }

  .docs__card {
    display: flex;
    flex-direction: column;
    gap: var(--gap-related);
    padding: var(--docs-pad);
    border: var(--stroke-default) solid var(--docs-border);
    border-radius: var(--docs-radius);
    background-color: var(--bg-surface);
    box-shadow: var(--elevation-card);
  }

  .docs__badge {
    display: inline-flex;
    align-items: center;
    padding-inline: var(--pad-inline-xs);
    padding-block: var(--pad-block-xs);
    border-radius: var(--radius-full);
    background-color: var(--bg-sunken);
    color: var(--fg-muted);
    font: var(--type-label);
    white-space: nowrap;
  }

  .docs__badge[data-tone="pass"] { background-color: var(--bg-selected); color: var(--fg-success); }
  .docs__badge[data-tone="fail"] { color: var(--fg-danger); }
  .docs__badge[data-tone="tier-1"] { color: var(--fg-muted); }
  .docs__badge[data-tone="tier-2"] { color: var(--fg-accent); }
  .docs__badge[data-tone="tier-3"] { color: var(--fg-strong); }

  .docs__stage {
    display: flex;
    flex-wrap: wrap;
    gap: var(--gap-separate);
    padding: var(--pad-card);
    border: var(--stroke-default) solid var(--docs-border);
    border-radius: var(--docs-radius);
    background-color: var(--bg-canvas);
  }

  .docs__cell { display: flex; flex-direction: column; gap: var(--gap-tight); align-items: start; }
  .docs__cell-label { color: var(--fg-subtle); font: var(--type-label); }

  .docs__grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(var(--measure-narrow), 1fr));
    gap: var(--gap-grouped);
  }

  .docs__gap { border-inline-start: var(--stroke-thick) solid var(--border-strong); }
  .docs__gap[data-severity="error"] { border-inline-start-color: var(--bg-danger); }
  .docs__gap[data-severity="warning"] { border-inline-start-color: var(--bg-warning); }

  .docs__note { color: var(--fg-muted); font: var(--type-ui); max-inline-size: var(--measure-prose); }
  .docs__source { color: var(--fg-subtle); font: var(--type-label); }

  .docs__hit[hidden] { display: none; }
}
"""


# ===========================================================================
# 3. HTML SHELL
# ===========================================================================

def page_shell(*, title: str, project: str, nav: str, body: str,
               inline_sources: str, search_index: str, current: str) -> str:
    return f"""<!doctype html>
<html lang="en" data-theme="light" data-density="comfortable">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} · {esc(project)}</title>
<link rel="stylesheet" href="assets/docs.css">
{inline_sources}
</head>
<body class="docs">
<aside class="docs__rail">
  <div>
    <div class="docs__brand">{esc(project)}</div>
    <div class="docs__tagline">generated from source · do not hand-edit</div>
  </div>
  <div class="docs__controls">
    <label class="docs__tagline" for="docs-search">Search</label>
    <input class="docs__search" id="docs-search" type="search" placeholder="token, component, socket"
           autocomplete="off" aria-controls="docs-results">
  </div>
  <nav class="docs__nav" aria-label="Sections">{nav}</nav>
  <div class="docs__controls">
    <button class="docs__toggle" type="button" data-docs-theme aria-pressed="false">Dark</button>
    <button class="docs__toggle" type="button" data-docs-density>Density: comfortable</button>
  </div>
  <div class="docs__note" id="docs-results" role="status"></div>
</aside>
<main class="docs__main" id="main">
{body}
</main>
<script src="assets/docs.js"></script>
<script>window.__DOCS_INDEX__ = {search_index};</script>
<script>window.docsInit && window.docsInit("{esc(current)}");</script>
</body>
</html>
"""


DOCS_JS = """/* The docs shell: search, theme, density. No framework, no network. */
(function () {
  var DENSITIES = ["compact", "comfortable", "spacious"];

  function setTheme(next) {
    document.documentElement.setAttribute("data-theme", next);
    var btn = document.querySelector("[data-docs-theme]");
    if (btn) {
      btn.textContent = next === "dark" ? "Light" : "Dark";
      btn.setAttribute("aria-pressed", next === "dark" ? "true" : "false");
    }
    try { localStorage.setItem("docs-theme", next); } catch (e) {}
  }

  function setDensity(next) {
    document.documentElement.setAttribute("data-density", next);
    var btn = document.querySelector("[data-docs-density]");
    if (btn) btn.textContent = "Density: " + next;
    try { localStorage.setItem("docs-density", next); } catch (e) {}
  }

  window.docsInit = function () {
    var stored;
    try { stored = localStorage.getItem("docs-theme"); } catch (e) {}
    setTheme(stored === "dark" ? "dark" : "light");
    try { stored = localStorage.getItem("docs-density"); } catch (e) {}
    setDensity(DENSITIES.indexOf(stored) >= 0 ? stored : "comfortable");

    var themeBtn = document.querySelector("[data-docs-theme]");
    if (themeBtn) themeBtn.addEventListener("click", function () {
      setTheme(document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark");
    });
    var densBtn = document.querySelector("[data-docs-density]");
    if (densBtn) densBtn.addEventListener("click", function () {
      var cur = document.documentElement.getAttribute("data-density");
      setDensity(DENSITIES[(DENSITIES.indexOf(cur) + 1) % DENSITIES.length]);
    });

    var input = document.getElementById("docs-search");
    var out = document.getElementById("docs-results");
    if (!input || !out) return;
    var index = window.__DOCS_INDEX__ || [];
    input.addEventListener("input", function () {
      var q = input.value.trim().toLowerCase();
      if (q.length < 2) { out.textContent = ""; return; }
      var hits = index.filter(function (row) {
        return (row.n + " " + (row.d || "")).toLowerCase().indexOf(q) >= 0;
      }).slice(0, 24);
      if (!hits.length) { out.textContent = "No match for \\u201c" + q + "\\u201d."; return; }
      out.innerHTML = hits.map(function (row) {
        return '<div><a class="docs__link" href="' + row.u + '">' + row.n + "</a></div>";
      }).join("");
    });
  };
})();
"""


# ===========================================================================
# 4. RENDERING THE GENERATED PAGES
# ===========================================================================

def badge(text: str, tone: str = "") -> str:
    attr = f' data-tone="{esc(tone)}"' if tone else ""
    return f'<span class="docs__badge"{attr}>{esc(text)}</span>'


def swatch(hexval: str, alpha: float = 1.0) -> str:
    if not hexval:
        return ""
    # Inline style is legal here precisely because every key is a custom
    # property (Law 4). A translucent role has to be composited to be seen at
    # all, so it is shown mixed with the canvas rather than as a solid lie.
    if alpha < 1.0:
        style = f"--docs-swatch: color-mix(in oklab, {hexval} {alpha * 100:.0f}%, transparent)"
    else:
        style = f"--docs-swatch: {hexval}"
    return f'<span class="docs__swatch" style="{esc(style)}" aria-hidden="true"></span>'


def tier_badge(tier: int) -> str:
    return badge(f"Tier {tier}", f"tier-{tier}")


def token_rows(tokens: Sequence[Dict[str, Any]], themes: Sequence[str]) -> str:
    head = ["", "Token", "Tier", "Source value", "Resolved"]
    head += [t for t in themes if t != "light"]
    head += ["Density", "Read by"]
    rows: List[str] = []
    for t in tokens:
        light = t["resolved"].get("light", {})
        sw = ""
        if light.get("hex"):
            sw = swatch(light["hex"], light.get("alpha", 1.0))
        cells = [
            sw,
            f'<code id="{esc(slug(t["name"]))}">{esc(t["name"])}</code>'
            + (f'<div class="docs__note">{esc(t["note"])}</div>' if t.get("note") else ""),
            tier_badge(t["tier"]),
            f'<code>{esc(t["raw"])}</code>',
            resolved_cell(light),
        ]
        for theme in themes:
            if theme == "light":
                continue
            cells.append(resolved_cell(t["resolved"].get(theme, {}),
                                       same_as=light.get("display", "")))
        dens = t.get("density") or {}
        cells.append(" · ".join(f"{k} {v}" for k, v in sorted(dens.items())) or "—")
        readers = t.get("referenced_by") or []
        cells.append(f"{len(readers)}" if readers else
                     '<span class="docs__badge" data-tone="fail">0</span>')
        rows.append("<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>")
    th = "".join(f"<th>{esc(h)}</th>" for h in head)
    return (f'<div class="docs-scroll"><table class="docs-table"><thead><tr>{th}</tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table></div>')


def resolved_cell(entry: Dict[str, Any], same_as: str = "") -> str:
    if not entry:
        return "—"
    display = entry.get("display", "")
    if same_as and display == same_as:
        return '<span class="docs__source">same</span>'
    out = f"<code>{esc(display)}</code>"
    if entry.get("status") == "range":
        out += '<div class="docs__source">fluid — viewport dependent</div>'
    elif entry.get("status") == "unresolved":
        out += f'<div class="docs__source">{esc(entry.get("reason", ""))}</div>'
    if entry.get("hex") and entry["hex"] not in display:
        out += f'<div class="docs__source">{esc(entry["hex"])}</div>'
    return out


def contrast_table(tokens: Sequence[Dict[str, Any]], themes: Sequence[str]) -> str:
    rows: List[List[str]] = []
    for t in tokens:
        for c in t.get("contrast", []):
            verdict = "pass" if c["body"] else ("large only" if c["large"] else "fail")
            tone = "pass" if c["body"] else "fail"
            rows.append([
                f'<code>{esc(t["name"])}</code>',
                f'<code>{esc(c["against"])}</code>',
                esc(c["theme"]),
                f'{c["ratio"]:.2f}:1',
                badge(verdict, tone),
                f'{swatch(c["bg_hex"])}{swatch(c["fg_hex"])}',
            ])
    if not rows:
        return ""
    head = ["Foreground", "Background", "Theme", "Measured", "4.5:1 body text", ""]
    th = "".join(f"<th>{esc(h)}</th>" for h in head)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return (f'<div class="docs-scroll"><table class="docs-table"><thead><tr>{th}</tr></thead>'
            f"<tbody>{body}</tbody></table></div>")


def socket_table(comp: Dict[str, Any], themes: Sequence[str]) -> str:
    head = ["Property", "Default", "Accepts", "Resolves to", "Consumed by", "Re-pointed by"]
    rows: List[List[str]] = []
    for s in comp["sockets"]:
        resolved = s.get("resolved", {})
        rows.append([
            f'<code>{esc(s["name"])}</code>'
            + (f'<div class="docs__note">{esc(s["note"])}</div>' if s.get("note") else ""),
            f'<code>{esc(s["default"])}</code>',
            f'<code>{esc(s["accepts"])}</code>',
            "<br>".join(f'{esc(k)}: <code>{esc(v)}</code>'
                        for k, v in sorted(resolved.items(),
                                           key=lambda kv: (kv[0] != "light", kv[0]))) or "—",
            ", ".join(f"<code>{esc(p)}</code>" for p in s["consumed_by"])
            or badge("nothing reads it", "fail"),
            ", ".join(f"<code>{esc(p)}</code>" for p in s["repointed_by"]) or "—",
        ])
    th = "".join(f"<th>{esc(h)}</th>" for h in head)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return (f'<div class="docs-scroll"><table class="docs-table"><thead><tr>{th}</tr></thead>'
            f"<tbody>{body}</tbody></table></div>")


def props_table(comp: Dict[str, Any]) -> str:
    if not comp.get("props"):
        return ""
    head = ["Prop", "Type", "Default", "Notes"]
    rows = [[
        f'<code>{esc(p["name"])}{"" if p["optional"] else " (required)"}</code>',
        f'<code>{esc(p["type"])}</code>',
        f'<code>{esc(p["default"])}</code>' if p.get("default") else "—",
        esc(p.get("doc") or ""),
    ] for p in comp["props"]]
    th = "".join(f"<th>{esc(h)}</th>" for h in head)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return (f'<div class="docs-scroll"><table class="docs-table"><thead><tr>{th}</tr></thead>'
            f"<tbody>{body}</tbody></table></div>")


def state_table(comp: Dict[str, Any], gaps: Sequence[Dict[str, Any]]) -> str:
    implemented = {s["state"]: s for s in comp["states"]}
    missing = {g["state"] for g in gaps
               if g.get("component") == comp["name"] and g["kind"] == "missing-state"}
    head = ["State", "Implemented", "Selector", "What it must do"]
    rows = []
    listed = list(SEVEN_STATES) + [s for s in implemented if s not in SEVEN_STATES]
    for state in listed:
        if state not in implemented and not comp["interactive"]:
            continue
        got = implemented.get(state)
        rows.append([
            f"<code>{esc(state)}</code>",
            badge("yes", "pass") if got else badge("no rule", "fail")
            if state in missing else badge("n/a"),
            f'<code>{esc(got["selector"])}</code>' if got else "—",
            esc(STATE_MEANING.get(state, "")),
        ])
    th = "".join(f"<th>{esc(h)}</th>" for h in head)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return (f'<div class="docs-scroll"><table class="docs-table"><thead><tr>{th}</tr></thead>'
            f"<tbody>{body}</tbody></table></div>")


ATTR_STATES = {
    "disabled": 'aria-disabled="true"',
    "loading": 'data-state="loading" aria-busy="true"',
    "error": 'aria-invalid="true"',
}
FORCED_STATES = ("hover", "focus-visible", "active")


def example_markup(comp: Dict[str, Any], custom: Optional[str]) -> str:
    """One live instance per variant, per size, and per renderable state."""
    tag = comp.get("element") or "div"
    if tag not in ("button", "a", "div", "span", "section", "article", "li", "p"):
        tag = "div"
    root = comp["root_class"]
    label = comp["name"].replace("-", " ").title()

    def instance(attrs: str, text: str) -> str:
        if custom:
            return custom.replace("{attrs}", attrs).replace("{content}", esc(text))
        inner = esc(text)
        parts = [p["class"] for p in comp.get("parts", [])]
        header = next((p for p in parts if p.endswith("__header")), None)
        body_part = next((p for p in parts if p.endswith("__body")), None)
        label_part = next((p for p in parts if p.endswith("__label")), None)
        if header or body_part:
            inner = ""
            if header:
                inner += f'<div class="{esc(header)}">{esc(label)}</div>'
            if body_part:
                inner += f'<div class="{esc(body_part)}">{esc(text)}</div>'
        elif label_part:
            inner = f'<span class="{esc(label_part)}">{esc(text)}</span>'
        closing = "" if tag in ("img", "input") else f"</{tag}>"
        return f'<{tag} class="{esc(root)}" {attrs}>{inner}{closing}'

    cells: List[Tuple[str, str]] = [("default", instance("", label))]
    for v in comp.get("variants", []):
        cells.append((f'variant: {v["name"]}',
                      instance(f'data-variant="{esc(v["name"])}"', label)))
    for s in comp.get("sizes", []):
        cells.append((f'size: {s["name"]}', instance(f'data-size="{esc(s["name"])}"', label)))
    implemented = {s["state"] for s in comp["states"]}
    for state, attrs in ATTR_STATES.items():
        if state in implemented:
            cells.append((state, instance(attrs, label)))
    for state in FORCED_STATES:
        if state in implemented:
            cells.append((f"{state} (forced)",
                          instance(f'data-force-state="{esc(state)}"', label)))
    out = "".join(
        f'<div class="docs__cell"><div class="docs__cell-label">{esc(name)}</div>{markup}</div>'
        for name, markup in cells)
    return f'<div class="docs__stage">{out}</div>'


PSEUDO_MIRROR = (
    (":focus-visible", "focus-visible"),
    (":hover", "hover"),
    (":active", "active"),
)


def forced_state_css(css_paths: Sequence[Path]) -> str:
    """Mirror every pseudo-class state rule onto a `data-force-state` attribute.

    You cannot hover a doc page's twelve examples at once. `.button:hover` and
    `.button[data-force-state~="hover"]` have identical specificity (0,1,0), so
    the mirror wins on document order alone — no specificity fight, no
    !important, and the rule stays in the same layer and the same at-rule
    context it was written in. A hover rule behind `@media (hover: hover)` stays
    behind it, and will therefore not render on a coarse pointer.
    """
    out: List[str] = []
    for path in css_paths:
        try:
            cf = CssFile(str(path), path.read_text(encoding="utf-8"))
        except OSError:
            continue
        for rule in cf.rules:
            sel = rule.selector
            mirrored = sel
            hit = False
            for pseudo, name in PSEUDO_MIRROR:
                if pseudo in strip_guards(sel):
                    mirrored = mirrored.replace(pseudo, f'[data-force-state~="{name}"]')
                    hit = True
            if not hit or not rule.decls:
                continue
            body = " ".join(f"{d.prop}: {d.value};" for d in rule.decls)
            block = f"  {mirrored} {{ {body} }}"
            for at in reversed(rule.at_rules):
                if at.startswith("@layer"):
                    continue
                block = f"  {at} {{\n  {block}\n  }}"
            layer = next((a for a in rule.at_rules if a.startswith("@layer")), "@layer components")
            out.append(f"{layer} {{\n{block}\n}}")
    return "\n".join(out)


# ===========================================================================
# 5. THE BUILD
# ===========================================================================

class Site:
    def __init__(self, system: Dict[str, Any], prose: Optional[Path], root: Path,
                 *, project: str, examples: bool, only: Sequence[str]) -> None:
        self.system = system
        self.prose = prose
        self.root = root
        self.project = project
        self.examples = examples
        self.only = [o.lower() for o in only]
        self.code_blocks: List[Dict[str, str]] = []
        self.index: List[Dict[str, str]] = []

    # -- prose -------------------------------------------------------------
    def read_prose(self, rel: str) -> str:
        if not self.prose:
            return ""
        p = self.prose / rel
        try:
            return p.read_text(encoding="utf-8")
        except OSError:
            return ""

    def prose_html(self, rel: str, *, heading_offset: int = 1) -> str:
        md = self.read_prose(rel)
        if not md.strip():
            return ""
        blocks: List[Dict[str, str]] = []
        body = render_markdown(md, heading_offset=heading_offset, collect=blocks)
        for b in blocks:
            b["source"] = rel
        self.code_blocks.extend(blocks)
        return (f'<section class="docs__section" data-prose="{esc(rel)}">{body}'
                f'<div class="docs__source">hand-written · {esc(rel)}</div></section>')

    def components(self) -> List[Dict[str, Any]]:
        comps = self.system.get("components", [])
        if self.only:
            comps = [c for c in comps if c["name"].lower() in self.only]
        return comps

    # -- pages -------------------------------------------------------------
    def nav(self, current: str) -> str:
        items = [("index", "Overview", "index.html"),
                 ("tokens", "Tokens", "tokens.html"),
                 ("components", "Components", "components.html")]
        if self.prose and (self.prose / "patterns").is_dir():
            items.append(("patterns", "Patterns", "patterns.html"))
        out = []
        for key, label, href in items:
            cur = ' aria-current="page"' if key == current else ""
            out.append(f'<a class="docs__link" href="{href}"{cur}>{esc(label)}</a>')
        return "".join(out)

    def page_index(self) -> str:
        s = self.system["stats"]
        gaps = self.system.get("gaps", [])
        errors = [g for g in gaps if g["severity"] == "error"]
        body = [f'<section class="docs__section"><h1 class="docs-h docs__title">'
                f"{esc(self.project)} design system</h1>"]
        body.append('<p class="docs-p">Every number, name and default on this site was read '
                    "out of the source files listed at the bottom of this page. Nothing here "
                    "is transcribed, so nothing here can drift. What is not here — why a "
                    "decision was made, when not to use a component — is hand-written, and "
                    "marked as such.</p>")
        cards = [
            ("Tokens", f'{s["tokens"]}', f'{s["tier1"]} primitive · {s["tier2"]} role'),
            ("Components", f'{s["components"]}', f'{s["sockets"]} Tier-3 sockets'),
            ("Themes", str(len(self.system.get("themes", []))),
             " · ".join(self.system.get("themes", []))),
            ("Open gaps", str(len(gaps)), f'{len(errors)} at error severity'),
        ]
        body.append('<div class="docs__grid">' + "".join(
            f'<div class="docs__card"><div class="docs__cell-label">{esc(t)}</div>'
            f'<div class="docs-h">{esc(v)}</div><div class="docs__note">{esc(sub)}</div></div>'
            for t, v, sub in cards) + "</div></section>")

        body.append(self.prose_html("overview.md"))
        body.append(self.prose_html("principles.md"))

        if gaps:
            body.append('<section class="docs__section"><h2 class="docs-h" id="gaps">'
                        "What the source says is missing</h2>")
            body.append('<p class="docs-p">These are not style opinions. Each one is a place '
                        "where the source contradicts the system's own rules, found by reading "
                        "the source.</p>")
            for g in gaps[:60]:
                subject = g.get("component") or g.get("token") or ""
                body.append(
                    f'<div class="docs__card docs__gap" data-severity="{esc(g["severity"])}">'
                    f'<div>{badge(g["kind"], "fail" if g["severity"] == "error" else "")}'
                    f" <code>{esc(subject)}</code></div>"
                    f'<div class="docs__note">{esc(g["detail"])}</div>'
                    f'<div class="docs__source">{esc(g["where"])}</div></div>')
            if len(gaps) > 60:
                body.append(f'<p class="docs-p">… and {len(gaps) - 60} more in '
                            "<code>system.json</code>.</p>")
            body.append("</section>")

        limits = self.system.get("limits", [])
        if limits:
            body.append('<section class="docs__section"><h2 class="docs-h" id="limits">'
                        "What could not be resolved statically</h2>"
                        '<p class="docs-p">A value that depends on a viewport, a container or '
                        "an element's own font size has no single number outside a browser. "
                        "These are reported rather than guessed.</p>")
            body.append(table_html(
                ["Token", "Status", "Why"],
                [[f"`{l['token']}`", l["status"], l["reason"]] for l in limits]))
            body.append("</section>")

        src = self.system.get("sources", {})
        body.append('<section class="docs__section"><h2 class="docs-h" id="sources">Sources</h2>'
                    + table_html(["Kind", "File"],
                                 [[kind, f"`{f}`"] for kind, files in src.items()
                                  for f in files]) + "</section>")
        return "\n".join(x for x in body if x)

    def page_tokens(self) -> str:
        tokens = self.system.get("tokens", [])
        themes = self.system.get("themes", ["light"])
        body = ['<section class="docs__section"><h1 class="docs-h docs__title">Tokens</h1>'
                '<p class="docs-p">Flow is one-way: primitive → role → component → rule. '
                "The tier column says which of those a name is, and the column after it says "
                "how that was decided.</p></section>"]
        for group in GROUP_ORDER:
            rows = [t for t in tokens if t["group"] == group]
            if not rows:
                continue
            body.append(f'<section class="docs__section"><h2 class="docs-h" id="{esc(group)}">'
                        f"{esc(group.title())}</h2>")
            body.append(f'<p class="docs-p">{GROUP_BLURB.get(group, "")}</p>')
            body.append(self.prose_html(f"tokens/{group}.md", heading_offset=2))
            for tier in (1, 2, 3):
                tier_rows = [t for t in rows if t["tier"] == tier]
                if not tier_rows:
                    continue
                body.append(f'<h3 class="docs-h">Tier {tier}</h3>')
                body.append(token_rows(tier_rows, themes))
            body.append("</section>")
            for t in rows:
                self.index.append({"n": t["name"], "d": t.get("note", ""),
                                   "u": f"tokens.html#{slug(t['name'])}"})
        ct = contrast_table(tokens, themes)
        if ct:
            body.append('<section class="docs__section"><h2 class="docs-h" id="contrast">'
                        "Contrast</h2><p class=\"docs-p\">Measured, never assumed. Every ratio "
                        "here was computed from the resolved OKLCH values with the same "
                        "function the ramp generator uses, so the two can never disagree. "
                        "Translucent roles are absent on purpose: their ratio depends on what "
                        "is behind them, which source cannot tell you.</p>")
            body.append(ct)
            body.append("</section>")
        return "\n".join(body)

    def page_components(self) -> str:
        comps = self.components()
        gaps = self.system.get("gaps", [])
        themes = self.system.get("themes", ["light"])
        body = ['<section class="docs__section"><h1 class="docs-h docs__title">Components</h1>'
                '<p class="docs-p">Each component\'s Tier-3 custom properties are its public '
                "CSS API: documented, supported, and safe to set from outside. Anything not in "
                "that table is private.</p></section>"]
        if not comps:
            body.append('<p class="docs-p">No components matched.</p>')
        for comp in comps:
            name = comp["name"]
            self.index.append({"n": name, "d": comp.get("doc", ""),
                               "u": f"components.html#{slug(name)}"})
            body.append(f'<section class="docs__section" id="{esc(slug(name))}">')
            body.append(f'<h2 class="docs-h">{esc(name)}</h2>')
            if comp.get("doc"):
                body.append(f'<p class="docs-p">{inline_md(comp["doc"])}</p>')
            elif comp.get("note") and not FIVE_PART_BANNER.search(comp["note"]):
                body.append(f'<p class="docs-p">{inline_md(comp["note"])}</p>'
                            '<div class="docs__source">from the stylesheet comment '
                            '— no JSDoc on this component</div>')
            body.append(f'<div class="docs__source">{esc(comp["file"])}:{comp["line"]}'
                        + (f' · {esc(comp["prop_file"])}' if comp.get("prop_file") else "")
                        + (" · interactive" if comp["interactive"] else " · static surface")
                        + "</div>")

            if comp.get("parts"):
                body.append('<h3 class="docs-h">Anatomy</h3>')
                body.append(table_html(["Part", "Sets"],
                                       [[f'`.{p["class"]}`', ", ".join(p["props"]) or "—"]
                                        for p in comp["parts"]]))

            if self.examples:
                body.append('<h3 class="docs-h">Examples</h3>')
                custom = self.read_prose(f"components/{name}.example.html") or None
                body.append(example_markup(comp, custom))

            body.append('<h3 class="docs-h">States</h3>')
            body.append(state_table(comp, gaps))

            body.append('<h3 class="docs-h">CSS API — Tier-3 sockets</h3>')
            body.append(socket_table(comp, themes))

            pt = props_table(comp)
            if pt:
                body.append('<h3 class="docs-h">Props</h3>')
                body.append(pt)

            keys = DEFAULT_KEYBOARD.get(comp.get("element", ""))
            if keys:
                body.append('<h3 class="docs-h">Keyboard</h3>')
                body.append(table_html(["Key", "Does"], [[k, v] for k, v in keys]))
                body.append('<div class="docs__source">Inferred from the rendered element '
                            f'&lt;{esc(comp["element"])}&gt;. Anything beyond the element\'s '
                            "own contract has to be written down by hand.</div>")

            own_gaps = [g for g in gaps if g.get("component") == name]
            if own_gaps:
                body.append('<h3 class="docs-h">Gaps</h3>')
                for g in own_gaps:
                    body.append(
                        f'<div class="docs__card docs__gap" data-severity="{esc(g["severity"])}">'
                        f'<div>{badge(g["kind"], "fail" if g["severity"] == "error" else "")}</div>'
                        f'<div class="docs__note">{esc(g["detail"])}</div></div>')

            hand = self.prose_html(f"components/{name}.md", heading_offset=2)
            if hand:
                body.append(hand)
            else:
                body.append('<div class="docs__card docs__gap" data-severity="warning">'
                            '<div class="docs__note">No hand-written page. Everything above is '
                            "the <em>what</em>; the <em>why</em>, the tradeoffs and the "
                            "<em>when not to use this</em> are missing, and a parser cannot "
                            f"produce them. Write <code>components/{esc(name)}.md</code>."
                            "</div></div>")
            body.append("</section>")
        return "\n".join(body)

    def page_patterns(self) -> str:
        body = ['<section class="docs__section"><h1 class="docs-h docs__title">Patterns</h1>'
                '<p class="docs-p">Compositions of components that solve a recurring problem. '
                "These are hand-written: a pattern is a decision, and a parser cannot read a "
                "decision out of a stylesheet.</p></section>"]
        if self.prose:
            for path in sorted((self.prose / "patterns").glob("*.md")):
                body.append(self.prose_html(f"patterns/{path.name}"))
                self.index.append({"n": path.stem, "d": "pattern",
                                   "u": f"patterns.html#{slug(path.stem)}"})
        return "\n".join(body)

    # -- write -------------------------------------------------------------
    def build(self, out: Path, *, emit_css: Optional[Path],
              emit_examples: Optional[Path]) -> List[str]:
        out.mkdir(parents=True, exist_ok=True)
        assets = out / "assets"
        assets.mkdir(exist_ok=True)

        pages: List[Tuple[str, str, str]] = [
            ("index", "Overview", self.page_index()),
            ("tokens", "Tokens", self.page_tokens()),
            ("components", "Components", self.page_components()),
        ]
        if self.prose and (self.prose / "patterns").is_dir():
            pages.append(("patterns", "Patterns", self.page_patterns()))

        source_css = self.copy_sources(assets)
        inline = "".join(f'<link rel="stylesheet" href="assets/{esc(name)}">'
                         for name in source_css)
        if self.examples:
            inline += '<link rel="stylesheet" href="assets/forced-states.css">'

        index_json = json.dumps(self.index, ensure_ascii=False)
        written: List[str] = []
        for key, title, body in pages:
            html_text = page_shell(title=title, project=self.project, nav=self.nav(key),
                                   body=body, inline_sources=inline,
                                   search_index=index_json, current=key)
            (out / f"{key}.html").write_text(html_text, encoding="utf-8")
            written.append(f"{key}.html")

        (assets / "docs.css").write_text(CHROME_CSS, encoding="utf-8")
        (assets / "docs.js").write_text(DOCS_JS, encoding="utf-8")
        (assets / "system.json").write_text(
            json.dumps(self.system, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        written += ["assets/docs.css", "assets/docs.js", "assets/system.json"]

        if emit_css:
            emit_css.parent.mkdir(parents=True, exist_ok=True)
            emit_css.write_text(CHROME_CSS, encoding="utf-8")
            written.append(str(emit_css))
        if emit_examples:
            emit_examples.mkdir(parents=True, exist_ok=True)
            for i, block in enumerate(self.code_blocks):
                ext = {"css": ".css", "scss": ".scss", "tsx": ".tsx", "jsx": ".jsx",
                       "ts": ".ts", "js": ".js", "html": ".html"}.get(block["lang"])
                if not ext:
                    continue
                stem = slug(block.get("source", "example")) + f"-{i:02d}"
                (emit_examples / f"{stem}{ext}").write_text(block["code"] + "\n",
                                                            encoding="utf-8")
                written.append(str(emit_examples / f"{stem}{ext}"))
        return written

    def copy_sources(self, assets: Path) -> List[str]:
        """Copy the project's own CSS next to the site so the examples are LIVE.

        A screenshot of a component goes stale silently. A rendered instance
        styled by the component's actual stylesheet cannot: if the stylesheet
        changes, the page changes with it.
        """
        names: List[str] = []
        css_paths: List[Path] = []
        src = self.system.get("sources", {})
        for rel in list(src.get("tokens", [])) + list(src.get("components", [])):
            path = (self.root / rel) if not Path(rel).is_absolute() else Path(rel)
            if not path.is_file():
                continue
            name = f"src-{len(names):02d}-{path.name}"
            shutil.copyfile(path, assets / name)
            names.append(name)
            css_paths.append(path)
        if self.examples:
            (assets / "forced-states.css").write_text(
                (forced_state_css(css_paths) + "\n")
                or "/* no pseudo-class state rules found */\n",
                encoding="utf-8")
        return names


# ===========================================================================
# 6. DRIFT
# ===========================================================================

RATIO_RE = re.compile(r"(\d+\.\d+)\s*:\s*1")
TOKEN_MENTION = re.compile(r"--[a-z][\w-]*")


def diff_systems(old: Dict[str, Any], new: Dict[str, Any]) -> List[str]:
    """A readable report of what changed. A JSON dump is not a report."""
    out: List[str] = []
    old_t = {t["name"]: t for t in old.get("tokens", [])}
    new_t = {t["name"]: t for t in new.get("tokens", [])}
    for name in sorted(set(old_t) - set(new_t)):
        out.append(f"token removed    {name}  (was {old_t[name]['raw']}) — every page and "
                   "every code example that mentions it is now wrong")
    for name in sorted(set(new_t) - set(old_t)):
        out.append(f"token added      {name} = {new_t[name]['raw']}")
    for name in sorted(set(old_t) & set(new_t)):
        o, n = old_t[name], new_t[name]
        if o["raw"] != n["raw"]:
            out.append(f"token changed    {name}: {o['raw']} → {n['raw']}")
        for theme in sorted(set(o.get("resolved", {})) | set(n.get("resolved", {}))):
            od = o.get("resolved", {}).get(theme, {}).get("display")
            nd = n.get("resolved", {}).get(theme, {}).get("display")
            if od != nd and o["raw"] == n["raw"]:
                out.append(f"token re-resolved {name} [{theme}]: {od} → {nd} "
                           "(its own value did not change — something it references did)")
        if o["tier"] != n["tier"]:
            out.append(f"tier changed     {name}: Tier {o['tier']} → Tier {n['tier']}")
        oc = {(c["against"], c["theme"]): c["ratio"] for c in o.get("contrast", [])}
        nc = {(c["against"], c["theme"]): c["ratio"] for c in n.get("contrast", [])}
        for key in sorted(set(oc) & set(nc)):
            if abs(oc[key] - nc[key]) >= 0.005:
                verdict = "" if nc[key] >= 4.5 else "  ** now below 4.5:1 **"
                out.append(f"contrast changed {name} on {key[0]} [{key[1]}]: "
                           f"{oc[key]:.2f}:1 → {nc[key]:.2f}:1{verdict}")

    old_c = {c["name"]: c for c in old.get("components", [])}
    new_c = {c["name"]: c for c in new.get("components", [])}
    for name in sorted(set(old_c) - set(new_c)):
        out.append(f"component removed {name} — its page documents something that is gone")
    for name in sorted(set(new_c) - set(old_c)):
        out.append(f"component added  {name} — undocumented until someone writes its page")
    for name in sorted(set(old_c) & set(new_c)):
        o, n = old_c[name], new_c[name]
        os_ = {s["name"]: s for s in o["sockets"]}
        ns_ = {s["name"]: s for s in n["sockets"]}
        for s in sorted(set(os_) - set(ns_)):
            out.append(f"socket removed   {name}.{s} — a published CSS API was deleted; "
                       "this is a breaking change")
        for s in sorted(set(ns_) - set(os_)):
            out.append(f"socket added     {name}.{s} = {ns_[s]['default']}")
        for s in sorted(set(os_) & set(ns_)):
            if os_[s]["default"] != ns_[s]["default"]:
                out.append(f"default changed  {name}.{s}: {os_[s]['default']} → "
                           f"{ns_[s]['default']}")
        ost = {s["state"] for s in o["states"]}
        nst = {s["state"] for s in n["states"]}
        for s in sorted(ost - nst):
            out.append(f"state removed    {name}:{s}")
        for s in sorted(nst - ost):
            out.append(f"state added      {name}:{s}")
        op = {p["name"]: p for p in o.get("props", [])}
        np_ = {p["name"]: p for p in n.get("props", [])}
        for p in sorted(set(op) - set(np_)):
            out.append(f"prop removed     {name}.{p}")
        for p in sorted(set(np_) - set(op)):
            out.append(f"prop added       {name}.{p}")
        for p in sorted(set(op) & set(np_)):
            if op[p].get("default") != np_[p].get("default"):
                out.append(f"prop default     {name}.{p}: {op[p].get('default')} → "
                           f"{np_[p].get('default')}")
    return out


def check_prose(system: Dict[str, Any], prose: Path) -> List[str]:
    """Every claim in hand-written prose, checked against the extracted system.

    This is the half of drift that a baseline diff cannot see: the code moved
    and the sentence about it did not.
    """
    out: List[str] = []
    tokens = {t["name"]: t for t in system.get("tokens", [])}
    sockets = {s["name"] for c in system.get("components", []) for s in c["sockets"]}
    comps = {c["name"] for c in system.get("components", [])}
    contrast_index: Dict[Tuple[str, str, str], float] = {}
    for t in system.get("tokens", []):
        for c in t.get("contrast", []):
            contrast_index[(t["name"], c["against"], c["theme"])] = c["ratio"]

    for path in sorted(prose.rglob("*.md")):
        rel = path.relative_to(prose)
        text = path.read_text(encoding="utf-8")
        if rel.parts[0] == "components" and path.stem not in comps and not path.stem.endswith(
                ".example"):
            out.append(f"{rel}: documents `{path.stem}`, which is not in the source")
        for line_no, line in enumerate(text.splitlines(), 1):
            mentioned = [m for m in TOKEN_MENTION.findall(line)
                         if m not in tokens and m not in sockets]
            for m in sorted(set(mentioned)):
                out.append(f"{rel}:{line_no}: mentions `{m}`, which no longer exists")
            ratios = RATIO_RE.findall(line)
            if not ratios:
                continue
            named = [m for m in TOKEN_MENTION.findall(line) if m in tokens]
            for raw in ratios:
                claimed = float(raw)
                matches = [v for (fg, bg, _theme), v in contrast_index.items()
                           if fg in named and bg in named]
                if not matches:
                    out.append(f"{rel}:{line_no}: states {claimed}:1 but names no measurable "
                               "token pair — an unverifiable number in a doc is a number "
                               "nobody can maintain")
                elif not any(abs(claimed - v) < 0.005 for v in matches):
                    best = ", ".join(f"{v:.2f}:1" for v in sorted(set(matches)))
                    out.append(f"{rel}:{line_no}: states {claimed}:1; measured {best}")
    return out


def check_examples(system: Dict[str, Any], prose: Optional[Path]) -> List[str]:
    """Lint every fenced code block in the prose, and every example.html override,
    as if it were source."""
    out: List[str] = []
    if not prose:
        return out
    tokens = {t["name"] for t in system.get("tokens", [])}
    sockets = {s["name"] for c in system.get("components", []) for s in c["sockets"]}
    classes = {c["root_class"] for c in system.get("components", [])}
    classes |= {p["class"] for c in system.get("components", []) for p in c.get("parts", [])}
    class_bases = {c.split("__")[0] for c in classes}

    def check_vars(rel: Path, label: str, code: str) -> None:
        for ref in set(re.findall(r"var\(\s*(--[\w-]+)", code)):
            if ref not in tokens and ref not in sockets:
                out.append(f"{rel}: {label} uses `{ref}`, which is not a token "
                           "or a socket in this system")

    def check_class(rel: Path, label: str, cls: str) -> None:
        base = cls.split("__")[0]
        if base in class_bases and cls not in classes:
            out.append(f"{rel}: {label} styles `.{cls}`, which is not a part "
                       "this component publishes")

    for path in sorted(prose.rglob("*.md")):
        rel = path.relative_to(prose)
        blocks: List[Dict[str, str]] = []
        render_markdown(path.read_text(encoding="utf-8"), collect=blocks)
        for i, block in enumerate(blocks):
            if block["lang"] not in ("css", "scss"):
                continue
            check_vars(rel, f"example {i + 1}", block["code"])
            for cls in set(re.findall(r"\.([a-z][\w-]*)\s*[{,:\[]", block["code"])):
                check_class(rel, f"example {i + 1}", cls)

    # `components/<name>.example.html` overrides the generated example markup
    # (documentation-model.md §9) and is never fenced CSS, so it needs its own
    # extraction: `var()` can appear anywhere (e.g. a style attribute), and a
    # class is spelled `class="…"`, not a `.class { }` selector.
    for path in sorted(prose.rglob("*.example.html")):
        rel = path.relative_to(prose)
        code = path.read_text(encoding="utf-8")
        check_vars(rel, "override", code)
        for attr in re.findall(r'class\s*=\s*"([^"]*)"', code):
            for cls in attr.split():
                check_class(rel, "override", cls)
    return out


# ===========================================================================
# 7. CLI
# ===========================================================================

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="python -m scripts.build_docs",
        description="Build a self-contained documentation site from system.json, "
                    "or check it for drift.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python -m scripts.build_docs docs/system.json --out docs/site/
  python -m scripts.build_docs docs/system.json --out docs/site/ --prose docs/prose
  python -m scripts.build_docs docs/system.json --only button --no-examples --out /tmp/d
  python -m scripts.build_docs build/system.json --baseline docs/system.json \\
      --prose docs/prose --check
  python -m scripts.build_docs build/system.json --out build/docs \\
      --emit-css build/docs-chrome.css --emit-examples build/examples
""")
    ap.add_argument("system", help="system.json from extract_system.py")
    ap.add_argument("--out", metavar="DIR", help="Where to write the site. Required unless "
                                                 "--check is used alone.")
    ap.add_argument("--prose", metavar="DIR", help="Hand-written markdown tree (never written to).")
    ap.add_argument("--root", metavar="DIR", default=".",
                    help="Resolves the relative source paths recorded in system.json.")
    ap.add_argument("--project", metavar="NAME", default="Design system",
                    help="Title shown on every page.")
    ap.add_argument("--only", action="append", default=[], metavar="NAME",
                    help="Build only these components (repeatable or comma-separated).")
    ap.add_argument("--no-examples", action="store_true",
                    help="Skip the live rendered examples and the forced-state stylesheet.")
    ap.add_argument("--check", action="store_true",
                    help="Drift mode: diff against the last committed system.json, check every "
                         "hand-written claim, and exit non-zero on any difference.")
    ap.add_argument("--baseline", metavar="FILE",
                    help="The committed system.json to diff against. "
                         "Default: <out>/assets/system.json.")
    ap.add_argument("--emit-css", metavar="FILE",
                    help="Write the site's own chrome stylesheet for audit_design.py.")
    ap.add_argument("--emit-examples", metavar="DIR",
                    help="Write every fenced code example as a real file, to be linted like "
                         "source. A wrong example is worse than a missing one.")
    return ap


def expand_only(values: Sequence[str]) -> List[str]:
    out: List[str] = []
    for v in values:
        out.extend(x.strip() for x in v.split(",") if x.strip())
    return out


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = build_parser()
    args = ap.parse_args(argv)

    try:
        system = json.loads(Path(args.system).read_bytes())
    except OSError as exc:
        print(f"error: cannot read {args.system}: {exc}", file=sys.stderr)
        return 2
    except json.JSONDecodeError as exc:
        print(f"error: {args.system} is not valid JSON: {exc}", file=sys.stderr)
        return 2
    if system.get("schema") != SCHEMA:
        print(f"error: {args.system} has schema {system.get('schema')!r}; expected {SCHEMA!r}. "
              "Regenerate it with extract_system.py.", file=sys.stderr)
        return 2

    prose = Path(args.prose) if args.prose else None
    if prose and not prose.is_dir():
        print(f"error: --prose {prose} is not a directory", file=sys.stderr)
        return 2

    if args.check:
        baseline = Path(args.baseline) if args.baseline else (
            Path(args.out) / "assets" / "system.json" if args.out else None)
        if args.baseline and not baseline.is_file():
            # A named baseline that is not there is a wrong path, not a first
            # run: skipping the diff here made the gate pass while comparing
            # nothing.
            print(f"error: --baseline {args.baseline} does not exist. Commit the baseline "
                  "that extract_system.py wrote (docs/system.json in the documented "
                  "workflow), or drop --baseline to check prose only.", file=sys.stderr)
            return 2
        problems: List[str] = []
        if baseline and baseline.is_file():
            old = json.loads(baseline.read_bytes())
            problems += diff_systems(old, system)
        elif baseline:
            print(f"note: no baseline at {baseline}; checking prose only.", file=sys.stderr)
        else:
            print("note: no baseline given (--baseline or --out); checking prose only.",
                  file=sys.stderr)
        if prose:
            problems += check_prose(system, prose)
            problems += check_examples(system, prose)
        if not problems:
            print("No drift: the docs and the source agree.")
            return 0
        print(f"DRIFT — {len(problems)} finding(s). The docs no longer describe the source.\n")
        for p in problems:
            print(f"  {p}")
        print("\nRe-run extract_system.py and build_docs.py, and fix every hand-written "
              "claim listed above, in the same commit as the change that caused it.")
        return 1

    if not args.out:
        ap.error("--out is required unless you are running --check")
    out = Path(args.out)
    site = Site(system, prose, Path(args.root), project=args.project,
                examples=not args.no_examples, only=expand_only(args.only))
    written = site.build(out,
                         emit_css=Path(args.emit_css) if args.emit_css else None,
                         emit_examples=Path(args.emit_examples) if args.emit_examples else None)
    print(f"wrote {len(written)} files to {out}")
    gaps = system.get("gaps", [])
    errors = sum(1 for g in gaps if g["severity"] == "error")
    if gaps:
        print(f"note: {len(gaps)} gap(s) ({errors} error) are documented on the overview page.",
              file=sys.stderr)
    return 0


if __name__ == "__main__":
    # A Windows pipe (git hook, CI, `> file`) defaults to the ANSI code page,
    # where printing →, Δ or ✓ raises UnicodeEncodeError. Consoles and
    # Claude Code already use UTF-8 and are left alone.
    for _stream in (sys.stdout, sys.stderr):
        if getattr(_stream, "encoding", "utf-8").lower() not in ("utf-8", "utf8"):
            _stream.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
