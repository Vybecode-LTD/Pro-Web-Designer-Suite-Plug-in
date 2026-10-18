"""Draw the root README's pictures: one SVG per theme for each, into
.github/assets/readme/. Standard library only; Python 3.9 or newer.

    python -B "dev plans/readme-art/build_readme_art.py"

Every colour is the suite's own output. The palette is what
`/web-design-suite:new-system "#e8440a"` writes (the quick start's brand
colour), each role read from its light or dark theme. The gate report is
audit_design.py --strict's real output on sample/src/components/card.css (and
card-fixed.css beside it for the clean run), in a project new-system wrote;
the census is extract_literals.py and cluster_values.py run on sample/legacy/.
Rerun those and update the data below if a script's output changes.

Before it writes anything, every text colour is measured against the
background it sits on: 4.5:1 for text, 3:1 for the large title and for
marks. A pair below its floor stops the build with exit 1.
"""
from __future__ import annotations

import pathlib
import sys
from xml.sax.saxutils import escape

REPO = pathlib.Path(__file__).resolve().parents[2]
OUT = REPO / ".github" / "assets" / "readme"

SANS = "ui-sans-serif,-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif"
MONO = "ui-monospace,SFMono-Regular,'Cascadia Mono','Segoe UI Mono',Consolas,'Liberation Mono',Menlo,monospace"

# new-system "#e8440a": the roles each theme binds, as hex.
LIGHT = {
    "name": "light",
    "canvas": "#fbf8f8",        # --bg-canvas   neutral-50
    "surface": "#ffffff",       # --bg-surface  neutral-0
    "sunken": "#f4f1f0",        # --bg-sunken   neutral-100
    "strong": "#090706",        # --fg-strong   neutral-950
    "text": "#171413",          # --fg-default  neutral-900
    "muted": "#615b59",         # --fg-muted    neutral-600
    "subtle": "#726b6a",        # --fg-subtle   neutral-500
    "border_subtle": "#e8e4e3",  # --border-subtle  neutral-200
    "border": "#d6d1d0",        # --border-default neutral-300
    "border_strong": "#726b6a",  # --border-strong  neutral-500
    "accent_fg": "#9e2f00",     # --fg-accent   accent-700
    "accent_bg": "#cc3c00",     # --bg-accent   accent-600
    "on_accent": "#ffffff",     # --fg-on-accent neutral-0
    "accent_tint": "#fff2ef",   # --bg-selected accent-50
    "ok": "#006731",            # success-700, text on a light surface
    "ok_tint": "#d3f5db",       # success-100
    "dot": "#d6d1d0",
    "shadow": 0.08,
    "ratio": "4.98:1",          # --fg-on-accent on --bg-accent, check_roles
}
DARK = {
    "name": "dark",
    "canvas": "#090706",        # --bg-surface  neutral-950 (the card on GitHub's dark page)
    "surface": "#171413",       # --bg-raised   neutral-900
    "sunken": "#020201",        # --bg-sunken   neutral-1000
    "strong": "#fbf8f8",        # --fg-strong   neutral-50
    "text": "#f4f1f0",          # --fg-default  neutral-100
    "muted": "#d6d1d0",         # --fg-muted    neutral-300
    "subtle": "#a8a1a0",        # --fg-subtle   neutral-400
    "border_subtle": "#171413",  # --border-subtle  neutral-900
    "border": "#2c2826",        # --border-default neutral-800
    "border_strong": "#726b6a",  # --border-strong  neutral-500
    "accent_fg": "#fe7553",     # --fg-accent   accent-400
    "accent_bg": "#e8440a",     # --bg-accent   accent-500
    "on_accent": "#020201",     # --fg-on-accent neutral-1000
    "accent_tint": "#2f0a00",   # --bg-selected accent-950
    "ok": "#259f56",            # --fg-success  success-500
    "ok_tint": "#19251b",       # success-500 at 12% on the raised surface
    "dot": "#2c2826",
    "shadow": 0.5,
    "ratio": "5.20:1",
}
# The ramp new-system wrote, 50 to 950; 500 is the brand colour, exactly.
ACCENT_RAMP = ["#fff2ef", "#ffe2dc", "#ffc9bc", "#ffa48e", "#fe7553", "#e8440a",
               "#cc3c00", "#9e2f00", "#752300", "#521700", "#2f0a00"]

PAIRS: list[tuple[str, str, str, float]] = []   # (where, fg, bg, floor)


# --- colour -----------------------------------------------------------------

def _channel(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def luminance(hex_colour: str) -> float:
    r, g, b = (int(hex_colour[i:i + 2], 16) / 255 for i in (1, 3, 5))
    return 0.2126 * _channel(r) + 0.7152 * _channel(g) + 0.0722 * _channel(b)


def contrast(a: str, b: str) -> float:
    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def blend(fg: str, bg: str, alpha: float) -> str:
    f = [int(fg[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(bg[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x * alpha + y * (1 - alpha)):02x}" for x, y in zip(f, b))


def pair(where: str, fg: str, bg: str, floor: float = 4.5) -> str:
    PAIRS.append((where, fg, bg, floor))
    return fg


# --- drawing ----------------------------------------------------------------

def width(s: str, size: float, mono: bool = False, bold: bool = False) -> float:
    """A generous estimate: the pills are sized for the widest common font."""
    return len(s) * size * (0.62 if mono else (0.6 if bold else 0.54))


def text(x, y, s, size, fill, *, mono=False, weight=400, anchor="start", spacing=None, extra=""):
    family = "mono" if mono else "sans"
    ls = f' letter-spacing="{spacing}"' if spacing is not None else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" class="{family}" font-size="{size}" font-weight="{weight}" '
            f'fill="{fill}" text-anchor="{anchor}"{ls}{extra}>{escape(s)}</text>')


def check_mark(x, y, size, colour, stroke=2.4):
    s = size
    return (f'<path d="M{x:.1f} {y + s * 0.52:.1f} l{s * 0.32:.1f} {s * 0.32:.1f} l{s * 0.6:.1f} {-s * 0.66:.1f}" '
            f'fill="none" stroke="{colour}" stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round"/>')


def cross_mark(x, y, size, colour, stroke=2.4):
    return (f'<path d="M{x:.1f} {y:.1f} l{size:.1f} {size:.1f} M{x + size:.1f} {y:.1f} l{-size:.1f} {size:.1f}" '
            f'fill="none" stroke="{colour}" stroke-width="{stroke}" stroke-linecap="round"/>')


def svg(w, h, title, body, desc=""):
    style = ("<style>.sans{font-family:" + SANS + "}.mono{font-family:" + MONO + "}"
             "text{font-kerning:normal}</style>")
    d = f"<desc>{escape(desc)}</desc>" if desc else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'role="img" aria-labelledby="title">\n<title id="title">{escape(title)}</title>\n{d}{style}\n'
            + "\n".join(body) + "\n</svg>\n")


def card(w, h, p, rx=28):
    return f'<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="{rx}" fill="{p["canvas"]}" stroke="{p["border"]}"/>'


def eyebrow(x, y, s, p, bg):
    return text(x, y, s, 15, pair(f"eyebrow {s}", p["accent_fg"], bg), mono=True, weight=700, spacing=2.5)


# --- the hero ---------------------------------------------------------------

def hero(p) -> str:
    W, H = 1280, 600
    c, s = p["canvas"], p["surface"]
    o = [card(W, H, p)]
    o.append('<defs>'
             f'<pattern id="dots" width="24" height="24" patternUnits="userSpaceOnUse">'
             f'<circle cx="2" cy="2" r="1.5" fill="{p["dot"]}"/></pattern>'
             '<linearGradient id="fade" x1="0" x2="1" y1="0" y2="0">'
             '<stop offset="0.38" stop-color="#fff" stop-opacity="0"/>'
             '<stop offset="0.72" stop-color="#fff" stop-opacity="1"/></linearGradient>'
             f'<mask id="m"><rect width="{W}" height="{H}" fill="url(#fade)"/></mask>'
             f'<clipPath id="clip"><rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="28"/></clipPath>'
             f'<filter id="shadow" x="-20%" y="-20%" width="140%" height="150%">'
             f'<feDropShadow dx="0" dy="18" stdDeviation="22" flood-color="#000" flood-opacity="{p["shadow"]}"/></filter>'
             '</defs>')
    o.append(f'<g clip-path="url(#clip)"><rect width="{W}" height="{H}" fill="url(#dots)" mask="url(#m)"/></g>')

    # Left: the words.
    o.append(eyebrow(80, 122, "CLAUDE CODE PLUGIN", p, c))
    o.append(f'<rect x="80" y="140" width="40" height="5" rx="2.5" fill="{p["accent_bg"]}"/>')
    o.append(text(76, 228, "Pro Web", 74, pair("title", p["strong"], c, 3), weight=800, spacing=-2))
    o.append(text(76, 308, "Designer Suite", 74, p["strong"], weight=800, spacing=-2))
    pair("tagline", p["text"], c)
    pair("tagline accent", p["accent_fg"], c)
    o.append(f'<text x="80" y="370" class="sans" font-size="30" font-weight="600" fill="{p["text"]}">'
             f'A design system with a <tspan fill="{p["accent_fg"]}">gate</tspan> on it.</text>')
    o.append(text(80, 416, "Tokens, one home for every component's styles,", 21, pair("body", p["muted"], c)))
    o.append(text(80, 448, "measured contrast, and gates that fail on drift.", 21, p["muted"]))
    x = 80
    for n, word in (("13", "skills"), ("16", "commands"), ("6", "subagents"), ("5", "gate tools")):
        w = width(f"{n} {word}", 18, bold=True) + 34
        o.append(f'<rect x="{x}" y="490" width="{w:.1f}" height="44" rx="22" fill="{s}" stroke="{p["border"]}"/>')
        o.append(f'<text x="{x + w / 2:.1f}" y="518" class="sans" font-size="18" font-weight="700" '
                 f'text-anchor="middle" fill="{pair("chip", p["text"], s)}">'
                 f'<tspan fill="{pair("chip number", p["accent_fg"], s)}">{n}</tspan> {word}</text>')
        x += w + 12

    # Right: a component's spec, the way a designer reads one.
    X, Y, CW, CH = 744, 56, 472, 500
    cx = X + CW / 2
    o.append(f'<rect x="{X}" y="{Y}" width="{CW}" height="{CH}" rx="22" fill="{s}" stroke="{p["border"]}" filter="url(#shadow)"/>')
    o.append(text(X + 28, Y + 42, "components/button.css", 16, pair("spec file", p["subtle"], s), mono=True))
    o.append(f'<rect x="{X + CW - 184}" y="{Y + 20}" width="156" height="34" rx="17" fill="{p["ok_tint"]}"/>')
    o.append(check_mark(X + CW - 168, Y + 28, 16, p["ok"]))
    o.append(text(X + CW - 144, Y + 43, "gate: clean", 15, pair("spec pill", p["ok"], p["ok_tint"]), mono=True, weight=700))
    o.append(f'<line x1="{X}" y1="{Y + 74}" x2="{X + CW}" y2="{Y + 74}" stroke="{p["border_subtle"]}"/>')

    # The button at 200%: padding 12px 24px, radius 8px, a 16px label.
    bw, bh = 300, 96
    bx, by = cx - bw / 2, Y + 118
    o.append(f'<rect x="{bx}" y="{by}" width="{bw}" height="{bh}" rx="16" fill="{p["accent_bg"]}"/>')
    o.append(f'<rect x="{bx + 48}" y="{by + 24}" width="{bw - 96}" height="{bh - 48}" fill="none" '
             f'stroke="{p["on_accent"]}" stroke-opacity="0.55" stroke-dasharray="5 5"/>')
    o.append(text(cx, by + 59, "Get started", 30, pair("button", p["on_accent"], p["accent_bg"]), weight=650, anchor="middle"))
    red = p["accent_fg"]
    ty = by - 16
    o.append(f'<path d="M{bx} {ty - 6} v12 M{bx} {ty} h48 M{bx + 48} {ty - 6} v12" stroke="{red}" stroke-width="1.5" fill="none"/>')
    o.append(text(bx + 24, ty - 10, "24", 14, pair("redline", red, s), mono=True, weight=700, anchor="middle"))
    lx = bx - 16
    o.append(f'<path d="M{lx - 6} {by} h12 M{lx} {by} v24 M{lx - 6} {by + 24} h12" stroke="{red}" stroke-width="1.5" fill="none"/>')
    o.append(text(lx - 10, by + 17, "12", 14, red, mono=True, weight=700, anchor="end"))

    rows = (("padding", "var(--space-3) var(--space-6)"), ("radius", "var(--radius-md)"),
            ("fill", "var(--bg-accent)"), ("label", "var(--fg-on-accent)"))
    for i, (k, v) in enumerate(rows):
        yy = Y + 270 + i * 28
        o.append(text(X + 28, yy, k, 16, p["subtle"], mono=True))
        o.append(text(X + 118, yy, v, 16, pair("spec value", p["text"], s), mono=True))
    o.append(f'<line x1="{X}" y1="{Y + 372}" x2="{X + CW}" y2="{Y + 372}" stroke="{p["border_subtle"]}"/>')

    # The contrast, measured.
    ry = Y + 386
    o.append(f'<rect x="{X + 28}" y="{ry}" width="44" height="44" rx="10" fill="{p["accent_bg"]}"/>')
    o.append(text(X + 50, ry + 29, "Aa", 19, p["on_accent"], weight=700, anchor="middle"))
    o.append(text(X + 88, ry + 31, p["ratio"], 28, pair("ratio", p["strong"], s), weight=800, spacing=-0.5))
    o.append(text(X + 204, ry + 19, "label on fill", 15, pair("ratio note", p["muted"], s)))
    o.append(text(X + 204, ry + 39, "AA for body text", 15, p["muted"]))
    o.append(f'<circle cx="{X + CW - 46}" cy="{ry + 22}" r="18" fill="{p["ok_tint"]}"/>')
    o.append(check_mark(X + CW - 55, ry + 13, 18, p["ok"], 2.6))

    # The accent ramp, 50 to 950; the ring marks the brand colour.
    sw = (CW - 56) / len(ACCENT_RAMP)
    for i, col in enumerate(ACCENT_RAMP):
        rx = X + 28 + i * sw
        o.append(f'<rect x="{rx:.1f}" y="{Y + CH - 52}" width="{sw - 3:.1f}" height="24" rx="5" fill="{col}"/>')
    i5 = ACCENT_RAMP.index("#e8440a")
    o.append(f'<rect x="{X + 28 + i5 * sw - 3:.1f}" y="{Y + CH - 55}" width="{sw + 3:.1f}" height="30" rx="7" '
             f'fill="none" stroke="{p["strong"]}" stroke-width="2"/>')
    return svg(W, H, "Pro Web Designer Suite: a design system with a gate on it",
               o, "A Claude Code plugin. A button's spec at 200%: padding, radius and colour as tokens, "
                  f"its label's contrast measured at {p['ratio']}, and the accent ramp from 50 to 950.")


# --- the census: 17 greys in, 7 roles out -----------------------------------

GREYS = ["#333333", "#343434", "#353535", "#3a3a3a", "#444444", "#464646", "#666666", "#696969",
         "#777777", "#787878", "#888888", "#999999", "#9a9a9a", "#cccccc", "#dddddd", "#dedede", "#e0e0e0"]
ROLES = [("--fg-default", "neutral-900", "#171512"), ("--fg-muted", "neutral-600", "#5f5c57"),
         ("--fg-subtle", "neutral-500", "#706d68"), ("--fg-disabled", "neutral-400", "#a6a29e"),
         ("--border-strong", "neutral-500", "#706d68"), ("--border-default", "neutral-300", "#d5d2ce"),
         ("--border-subtle", "neutral-200", "#e7e5e2")]
# cluster_values.py's mapping.json, rule by rule.
LINKS = {"#333333": [0], "#343434": [0], "#353535": [0], "#3a3a3a": [0], "#444444": [1], "#464646": [1],
         "#666666": [2], "#696969": [2], "#777777": [2], "#787878": [2], "#888888": [3],
         "#999999": [3, 4], "#9a9a9a": [3, 4], "#cccccc": [5], "#dddddd": [6], "#dedede": [6], "#e0e0e0": [6]}


def census(p) -> str:
    W, H = 1280, 660
    c = p["canvas"]
    o = [card(W, H, p)]
    o.append(eyebrow(64, 78, "THE CENSUS", p, c))
    o.append(text(W - 64, 78, "/web-design-suite:migrate · 3 files · 42 literals", 15,
                  pair("census note", p["subtle"], c), mono=True, anchor="end"))
    o.append(text(62, 128, "17 greys in. 7 roles out.", 38, pair("census title", p["strong"], c, 3), weight=800, spacing=-1))
    o.append(text(64, 166, "Every hard-coded value, found and clustered into the role it was trying to be.", 20,
                  pair("census sub", p["muted"], c)))
    o.append(text(64, 222, "BEFORE  ·  17 DISTINCT GREYS", 14, pair("band", p["subtle"], c), mono=True, weight=700, spacing=2))
    step, size, x0 = 66, 52, 86
    gx = [x0 + size / 2 + i * step for i in range(len(GREYS))]
    r0, r1 = 136, W - 136
    rx = [r0 + j * (r1 - r0) / (len(ROLES) - 1) for j in range(len(ROLES))]
    top, bottom = 314, 470
    for i, g in enumerate(GREYS):
        for j in LINKS[g]:
            o.append(f'<path d="M{gx[i]:.1f} {top} C{gx[i]:.1f} {top + 80} {rx[j]:.1f} {bottom - 80} {rx[j]:.1f} {bottom}" '
                     f'fill="none" stroke="{p["border_strong"]}" stroke-opacity="0.5" stroke-width="2"/>')
    for i, g in enumerate(GREYS):
        o.append(f'<rect x="{gx[i] - size / 2:.1f}" y="236" width="{size}" height="{size}" rx="10" fill="{g}" stroke="{p["border"]}"/>')
        o.append(text(gx[i], 306, g[1:], 13, p["subtle"], mono=True, anchor="middle"))
    for j, (role, step_name, hexv) in enumerate(ROLES):
        o.append(f'<rect x="{rx[j] - 30:.1f}" y="{bottom}" width="60" height="60" rx="14" fill="{hexv}" stroke="{p["border"]}"/>')
        o.append(text(rx[j], bottom + 88, role, 16, pair("role", p["strong"], c), mono=True, weight=700, anchor="middle"))
        o.append(text(rx[j], bottom + 110, step_name, 14, p["subtle"], mono=True, anchor="middle"))
    o.append(text(64, H - 24, "AFTER  ·  7 ROLES ON ONE NEUTRAL RAMP", 14, p["subtle"], mono=True, weight=700, spacing=2))
    return svg(W, H, "The census: 17 greys in, 7 roles out", o,
               "The migration's census of a three-file sample found 17 distinct greys; the proposal maps them "
               "onto seven roles: fg-default, fg-muted, fg-subtle, fg-disabled, border-strong, border-default "
               "and border-subtle.")


# --- the skills, as the chain a project follows -----------------------------

PHASES = [
    ("Start", "inherited or handed over", ["design-token-migration", "figma-variables-sync"]),
    ("Build", "design and build it", ["web-design-studio", "content-model-to-ui", "landing-page-conversion"]),
    ("Prove", "every state, fast, usable", ["component-state-matrix", "perf-budget-gate", "a11y-audit-runner",
                                             "design-critique-gate"]),
    ("Hand over", "docs and the client's case", ["design-system-docs", "client-presentation-builder"]),
    ("Govern", "every change after launch", ["design-system-versioning"]),
    ("Alongside", "the same tokens, as email", ["email-template-system"]),
]


def skill_map(p) -> str:
    W, H = 1280, 760
    c, s = p["canvas"], p["surface"]
    o = [card(W, H, p)]
    o.append(eyebrow(64, 78, "THE USUAL CHAIN ON A CLIENT PROJECT", p, c))
    o.append(text(62, 128, "Thirteen skills, one system.", 38, pair("map title", p["strong"], c, 3), weight=800, spacing=-1))
    o.append(text(64, 166, "Each loads when the work reaches it. web-design-studio holds the tokens and the gate the rest stand on.",
                  20, pair("map sub", p["muted"], c)))
    y0, step = 236, 92
    last = y0 + step * (len(PHASES) - 2)
    o.append(f'<line x1="96" y1="{y0}" x2="96" y2="{last}" stroke="{p["border"]}" stroke-width="2"/>')
    o.append(f'<line x1="96" y1="{last}" x2="96" y2="{last + step}" stroke="{p["border"]}" stroke-width="2" stroke-dasharray="4 6"/>')
    for k, (name, purpose, skills) in enumerate(PHASES):
        yc = y0 + k * step
        side = name == "Alongside"
        node_dash = ' stroke-dasharray="4 4"' if side else ""
        o.append(f'<circle cx="96" cy="{yc}" r="19" fill="{s}" stroke="{p["border"] if side else p["accent_bg"]}" '
                 f'stroke-width="2"{node_dash}/>')
        o.append(text(96, yc + 6, "+" if side else str(k + 1), 16, pair("node", p["accent_fg"], s), weight=800, anchor="middle"))
        o.append(text(134, yc - 3, name, 21, pair("phase", p["strong"], c), weight=750))
        o.append(text(134, yc + 21, purpose, 15, pair("purpose", p["muted"], c)))
        x = 352
        for sk in skills:
            hub = sk == "web-design-studio"
            w = width(sk, 15, mono=True) + 34
            fill = p["accent_tint"] if hub else s
            stroke = p["accent_bg"] if hub else p["border"]
            dash = ' stroke-dasharray="5 4"' if side else ""
            weight = ' stroke-width="1.6"' if hub else ""
            o.append(f'<rect x="{x:.1f}" y="{yc - 22}" width="{w:.1f}" height="44" rx="22" fill="{fill}" stroke="{stroke}"'
                     f'{weight}{dash}/>')
            colour = pair("hub pill", p["accent_fg"], fill) if hub else pair("pill", p["text"], fill)
            o.append(text(x + w / 2, yc + 5, sk, 15, colour, mono=True, weight=700 if hub else 500, anchor="middle"))
            x += w + 12
    return svg(W, H, "Thirteen skills, one system: the usual chain on a client project", o,
               "Start: design-token-migration, figma-variables-sync. Build: web-design-studio, content-model-to-ui, "
               "landing-page-conversion. Prove: component-state-matrix, perf-budget-gate, a11y-audit-runner, "
               "design-critique-gate. Hand over: design-system-docs, client-presentation-builder. Govern: "
               "design-system-versioning. Alongside: email-template-system.")


# --- where drift gets caught --------------------------------------------------

STAGES = [
    ("Claude edits a file", "opt-in hooks", ["design audit", "static a11y check", "token diff", "email build",
                                              "generated-file guard"]),
    ("You commit", "pre-commit hook", ["stylelint + ESLint", "design audit", "static a11y check", "role contrast"]),
    ("PR or push to main", "design-gates.yml", ["design audit", "a11y + perf, static", "a11y + perf, browser",
                                                 "Linux: all of it", "Windows: static only"]),
    ("You release", "/…:release-check", ["system diff", "major · minor · patch", "removals gated", "changelog",
                                          "migration guide"]),
]


def pipeline(p) -> str:
    W, H = 1280, 580
    c, s = p["canvas"], p["surface"]
    o = [card(W, H, p)]
    o.append(eyebrow(64, 78, "WHERE DRIFT GETS CAUGHT", p, c))
    o.append(text(62, 128, "Caught where it starts.", 38, pair("pipe title", p["strong"], c, 3), weight=800, spacing=-1))
    o.append(text(64, 166, "The same rules, from Claude's edit to the release: the audit, stylelint and ESLint share one rule spec.",
                  20, pair("pipe sub", p["muted"], c)))
    cw, gap, x0, y = 272, 36, 42, 206
    for k, (title, sub, items) in enumerate(STAGES):
        x = x0 + k * (cw + gap)
        o.append(f'<rect x="{x}" y="{y}" width="{cw}" height="338" rx="20" fill="{s}" stroke="{p["border"]}"/>')
        o.append(f'<circle cx="{x + 40}" cy="{y + 42}" r="18" fill="{p["accent_bg"]}"/>')
        o.append(text(x + 40, y + 48, str(k + 1), 17, pair("stage number", p["on_accent"], p["accent_bg"]), weight=800, anchor="middle"))
        o.append(text(x + 24, y + 98, title, 20, pair("stage title", p["strong"], s), weight=750))
        o.append(text(x + 24, y + 124, sub, 14, pair("stage sub", p["accent_fg"], s), mono=True, weight=700))
        o.append(f'<line x1="{x + 24}" y1="{y + 146}" x2="{x + cw - 24}" y2="{y + 146}" stroke="{p["border_subtle"]}"/>')
        for i, item in enumerate(items):
            iy = y + 178 + i * 32
            o.append(check_mark(x + 26, iy - 13, 14, p["ok"], 2.2))
            o.append(text(x + 50, iy, item, 16, pair("stage item", p["text"], s)))
        if k < len(STAGES) - 1:
            ax = x + cw + 8
            o.append(f'<path d="M{ax} {y + 169} h{gap - 16} m-8 -8 l8 8 l-8 8" fill="none" stroke="{p["accent_fg"]}" '
                     f'stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>')
    pair("pipe ok mark", p["ok"], s, 3)
    return svg(W, H, "Where drift gets caught: Claude's edit, the commit, the pull request, the release", o,
               "1, Claude edits a file: the opt-in hooks run the design audit, the static accessibility check, the token "
               "diff, the email build and the generated-file guard. 2, you commit: the pre-commit hook runs stylelint, "
               "ESLint, the design audit, the static accessibility check and role contrast. 3, a pull request or a push "
               "to main: design-gates.yml runs the design audit and the accessibility and performance gates, static and "
               "in a browser, on Linux, and the static gates on Windows. 4, you release: release-check diffs the system, classes the change, "
               "gates removals, and writes the changelog and migration guide.")


# --- the gate, in a terminal ------------------------------------------------

CODE = [
    ("@layer components {", False), ("  .card {", False), ("    padding: 13px 20px;", True),
    ("    background: var(--bg-surface);", False), ("    color: #333;", True), ("    border-radius: 6px;", True),
    ("  }", False), ("  .card__title {", False), ("    margin-bottom: 10px;", True), ("    font-size: 17px;", True),
    ("  }", False), ("  #promo .card {", True), ("    z-index: 999 !important;", True), ("  }", False), ("}", False),
]
# audit_design.py src/components/card.css --strict: each finding's first line, cut to its rule and code.
FINDINGS = [
    ("3", "L1", "raw-spacing", "padding: 13px 20px"), ("5", "L1", "raw-color", "color: #333"),
    ("6", "L1", "raw-radius", "border-radius: 6px"), ("9", "L1", "raw-spacing", "margin-bottom: 10px"),
    ("9", "L2", "child-margin", "margin-bottom"), ("10", "L1", "raw-type", "font-size: 17px"),
    ("12", "L5", "compound-specificity", "#promo .card"), ("12", "L5", "id-selector", "#promo"),
    ("13", "L5", "important", "!important on z-index"), ("13", "L1", "raw-z-index", "z-index: 999 !important"),
]
SUMMARY = [("L1", "Tokens or nothing", "6"), ("L2", "Parents own the gaps", "1"), ("L5", "Layers, not specificity", "3")]


def gate_report() -> str:
    W, H = 1280, 720
    bg, bar, line = "#090706", "#171413", "#2c2826"
    fg, strong, muted, subtle = "#f4f1f0", "#fbf8f8", "#d6d1d0", "#a8a1a0"
    accent, danger, warn, ok, info = "#fe7553", "#e9504d", "#dba400", "#259f56", "#4d9fe8"
    law = {"L1": accent, "L2": warn, "L5": info}
    o = [f'<defs><clipPath id="win"><rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="20"/></clipPath></defs>',
         f'<g clip-path="url(#win)"><rect width="{W}" height="{H}" fill="{bg}"/>',
         f'<rect width="{W}" height="52" fill="{bar}"/>',
         f'<rect y="{H - 78}" width="{W}" height="78" fill="{bar}"/></g>',
         f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="20" fill="none" stroke="{line}"/>',
         f'<line x1="0" y1="52" x2="{W}" y2="52" stroke="{line}"/>',
         f'<line x1="0" y1="{H - 78}" x2="{W}" y2="{H - 78}" stroke="{line}"/>']
    for i, col in enumerate((danger, warn, ok)):
        o.append(f'<circle cx="{28 + i * 22}" cy="26" r="7" fill="{col}"/>')
    o.append(text(W / 2, 32, "design gate  ·  audit_design.py --strict", 15, pair("term title", subtle, bar), mono=True, anchor="middle"))

    # The component, as Claude left it.
    o.append(f'<line x1="500" y1="52" x2="500" y2="{H - 78}" stroke="{line}"/>')
    o.append(text(28, 90, "src/components/card.css", 15, pair("tab", muted, bg), mono=True, weight=700))
    o.append(f'<rect x="28" y="100" width="206" height="2" fill="{accent}"/>')
    for i, (code, bad) in enumerate(CODE):
        yy = 140 + i * 30
        if bad:
            o.append(f'<rect x="0" y="{yy - 21}" width="500" height="30" fill="{danger}" fill-opacity="0.16"/>')
            o.append(f'<rect x="0" y="{yy - 21}" width="4" height="30" fill="{danger}"/>')
        o.append(text(52, yy, str(i + 1), 16, pair("line no", subtle, blend(danger, bg, 0.16)), mono=True, anchor="end"))
        indent = len(code) - len(code.lstrip())
        body = code.lstrip()
        if body.endswith("{") and not body.startswith("@"):
            parts = [(body[:-1], accent), ("{", subtle)]
        elif body.startswith("@"):
            parts = [("@layer ", accent), ("components ", fg), ("{", subtle)]
        elif ":" in body:
            prop, val = body.split(":", 1)
            parts = [(prop, muted), (":", subtle), (val[:-1], strong), (";", subtle)]
        else:
            parts = [(body, subtle)]
        spans = "".join(f'<tspan fill="{col}">{escape(t)}</tspan>' for t, col in parts)
        o.append(f'<text x="{68 + indent * 10.8:.1f}" y="{yy}" class="mono" font-size="18" xml:space="preserve">{spans}</text>')
    pair("code fg", strong, blend(danger, bg, 0.16))
    pair("code prop", muted, blend(danger, bg, 0.16))
    pair("code accent", accent, blend(danger, bg, 0.16))

    # What the gate said.
    o.append(f'<text x="528" y="94" class="mono" font-size="16"><tspan fill="{pair("prompt", accent, bg)}">$ </tspan>'
             f'<tspan fill="{pair("cmd", fg, bg)}">python audit_design.py src/components/card.css --strict</tspan></text>')
    o.append(text(528, 132, "src/components/card.css", 16, strong, mono=True, weight=700))
    for i, (ln, lw, rule, snip) in enumerate(FINDINGS):
        yy = 166 + i * 29
        o.append(text(556, yy, ln, 16, subtle, mono=True, anchor="end"))
        o.append(text(572, yy, "error", 16, pair("error", danger, bg), mono=True))
        tint = blend(law[lw], bg, 0.18)
        o.append(f'<rect x="634" y="{yy - 17}" width="40" height="23" rx="6" fill="{tint}"/>')
        o.append(text(654, yy, lw, 15, pair(f"law {lw}", law[lw], tint), mono=True, weight=700, anchor="middle"))
        o.append(text(688, yy, rule, 16, muted, mono=True))
        o.append(text(910, yy, snip, 16, fg, mono=True))
    o.append(text(528, 476, "Summary", 16, strong, mono=True, weight=700))
    for i, (lw, name, n) in enumerate(SUMMARY):
        yy = 506 + i * 28
        o.append(text(548, yy, lw, 16, law[lw], mono=True, weight=700))
        o.append(text(592, yy, name, 16, muted, mono=True))
        o.append(text(930, yy, n, 16, strong, mono=True, weight=700, anchor="end"))
    o.append(text(528, 612, "10 error(s), 0 warning(s) across 1 file(s).", 16, danger, mono=True, weight=700))
    o.append(f'<rect x="{W - 132}" y="592" width="104" height="30" rx="15" fill="{blend(danger, bg, 0.18)}"/>')
    o.append(cross_mark(W - 116, 601, 11, danger, 2.2))
    o.append(text(W - 98, 612, "exit 1", 15, pair("exit 1", danger, blend(danger, bg, 0.18)), mono=True, weight=700))

    # The same component on tokens.
    fy = H - 34
    o.append(f'<circle cx="40" cy="{fy - 5}" r="14" fill="{blend(ok, bar, 0.12)}"/>')
    o.append(check_mark(32, fy - 13, 16, ok, 2.4))
    o.append(text(66, fy, "after the fix, on tokens:", 16, pair("after", muted, bar), mono=True))
    o.append(text(330, fy, "design audit: clean — L1–L6 hold across 1 file(s).", 16, pair("clean", ok, bar), mono=True, weight=700))
    o.append(f'<rect x="{W - 132}" y="{fy - 21}" width="104" height="30" rx="15" fill="{blend(ok, bar, 0.12)}"/>')
    o.append(check_mark(W - 118, fy - 15, 13, ok, 2.2))
    o.append(text(W - 98, fy, "exit 0", 15, pair("exit 0", ok, blend(ok, bar, 0.12)), mono=True, weight=700))
    pair("muted on code bg", muted, bg)
    pair("subtle on bg", subtle, bg)
    for lw, colour in law.items():
        pair(f"summary {lw}", colour, bg)
    return svg(W, H, "The design gate on a drifting component: 10 errors, then clean on tokens", o,
               "audit_design.py --strict on src/components/card.css: raw spacing, a raw colour, a raw radius, a child "
               "margin, an off-scale font size, an ID selector, compound specificity, !important and a raw z-index: "
               "10 errors across Laws 1, 2 and 5, exit 1. After the fix, on tokens: design audit: clean, exit 0.")


def main() -> int:
    files = {}
    for p in (LIGHT, DARK):
        files[f"hero-{p['name']}.svg"] = hero(p)
        files[f"census-{p['name']}.svg"] = census(p)
        files[f"skill-map-{p['name']}.svg"] = skill_map(p)
        files[f"pipeline-{p['name']}.svg"] = pipeline(p)
    files["gate-report.svg"] = gate_report()
    failed = [(w, f, b, round(contrast(f, b), 2), fl) for w, f, b, fl in PAIRS if contrast(f, b) < fl]
    for row in failed:
        print("below its floor: %s  %s on %s = %.2f:1 (needs %.1f:1)" % row, file=sys.stderr)
    if failed:
        return 1
    OUT.mkdir(parents=True, exist_ok=True)
    for name, body in files.items():
        with open(OUT / name, "w", encoding="utf-8", newline="\n") as f:   # 3.9 has no write_text(newline=)
            f.write(body)
    lowest = min(PAIRS, key=lambda r: contrast(r[1], r[2]) / r[3])
    print(f"wrote {len(files)} files to {OUT.relative_to(REPO).as_posix()}; {len(PAIRS)} colour pairs measured, "
          f"the closest to its floor {lowest[0]!r} at {contrast(lowest[1], lowest[2]):.2f}:1 (floor {lowest[3]}:1)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
