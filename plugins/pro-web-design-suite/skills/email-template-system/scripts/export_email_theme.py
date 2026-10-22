"""export_email_theme.py — the email tokens as an MJML head or a React Email theme.

The token file stays the source of truth whatever compiles the email. A team
that writes its templates in MJML or React Email gets the same roles this
skill's own compiler resolves, generated from the same `email-tokens.json`,
never typed by hand (DL-B4):

  --format mjml         an `<mjml><mj-head>` file to `mj-include` inside a
                        template's `<mj-head>`: `<mj-attributes>` (the defaults
                        for `mj-all`, `mj-body`, `mj-section`, `mj-text`,
                        `mj-button`, `mj-divider`, `mj-spacer` and `mj-table`,
                        and one `mj-class` per type role, colour, surface, gap
                        and inset), `<mj-breakpoint>`, and an `<mj-style>`
                        with the dark-mode and phone rules.
  --format react-email  a TypeScript module (JavaScript when `--out` ends in
                        `.js` or `.mjs`) exporting `tokens`, `text`, `styles`,
                        `spacers`, `classes` and `headCss`, for `style=` and
                        `className=` on React Email's components and a
                        `<style>` in its `<Head>`.

Every class carries a `wds-` name that the dark-mode and phone rules select,
so the rules this skill's templates write by hand come with the theme. Read
references/email-workflow.md §11 before wiring either into a project.

USAGE
-----
  python scripts/export_email_theme.py --format mjml --out emails/theme.mjml
  python scripts/export_email_theme.py --format react-email --out emails/theme.ts

`--tokens` defaults to the project's `.design-suite.json` `emailTokens`, else
the skill's `assets/email-tokens.json`, as for build_email.py.

A role the token file lacks is left to the framework's own default and named
on stderr and in the file's header. A value that could end the attribute, the
declaration or the comment it is written into (`;`, `{`, `}`, `<`, `>`, a
backslash, a line break, `/*` or `*/`) is refused.

Exit codes: 0 written · 1 with --strict, a role the tokens lack · 2 bad
invocation, unreadable or unsafe tokens, or an output that is an input.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
try:                                              # python -m scripts.export_email_theme
    from .build_email import (MSO_FONT_STYLE, MSO_HEAD_BLOCK, TokenError, default_tokens_path,
                              load_dropped, load_tokens)
    from .project_config import ConfigError, project_config, refuse_overwrite
except ImportError:                               # python scripts/export_email_theme.py
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from build_email import (MSO_FONT_STYLE, MSO_HEAD_BLOCK, TokenError,  # type: ignore[no-redef]
                             default_tokens_path, load_dropped, load_tokens)
    from project_config import ConfigError, project_config, refuse_overwrite  # type: ignore[no-redef]

# A value placed in an attribute, a declaration or a comment must not be able
# to end it. The token file can be a stranger's (a cloned repository's).
UNSAFE = re.compile(r"[;{}<>\\\r\n]|/\*|\*/")
PX = re.compile(r"^(\d+(?:\.\d+)?)px$")

# The type roles, as the source templates' classes read them: size, line and
# weight from the `--type-*` triples (legal has no weight), and the colour role
# each one is set in.
TYPE_ROLES = (
    ("display", "--fg-strong", "--tracking-tight"),
    ("h1", "--fg-strong", "--tracking-tight"),
    ("h2", "--fg-strong", None),
    ("h3", "--fg-strong", None),
    ("lead", "--fg-default", None),
    ("body", "--fg-default", None),
    ("ui", "--fg-default", None),
    ("label", "--fg-muted", "--tracking-caps"),
    ("legal", "--fg-muted", None),
)
COLOURS = (("strong", "--fg-strong"), ("muted", "--fg-muted"), ("subtle", "--fg-subtle"),
           ("accent", "--fg-accent"))
SURFACES = (("canvas", "--bg-canvas"), ("surface", "--bg-surface"), ("sunken", "--bg-sunken"))
GAPS = (("gap-tight", "--gap-tight"), ("gap-related", "--gap-related"), ("gap-grouped", "--gap-grouped"),
        ("gap-separate", "--gap-separate"), ("gap-distinct", "--gap-distinct"),
        ("gap-section", "--space-section"))
INSETS = (("pad-card", "--pad-card"), ("pad-well", "--pad-well"))

# Dark mode: the role each class reads instead. The muted family keeps its
# lower contrast; every other text class reads the dark foreground.
DARK_MUTED = {"label", "legal", "muted", "subtle"}
DARK_SURFACE = {"canvas": "--email-dark-canvas", "surface": "--email-dark-surface",
                "sunken": "--email-dark-sunken"}
# The phone sizes the source templates give their headings.
MOBILE_TYPE = {"h1": ("--email-h1-size-mobile", "--email-h1-line-mobile"),
               "h2": ("--email-h2-size-mobile", "--email-h2-line-mobile")}


def class_name(role: str) -> str:
    return "wds-" + role


class Theme:
    """The tokens, read once, with the roles a writer asked for and did not find."""

    def __init__(self, tokens: dict[str, str]):
        self.tokens = tokens
        self.missing: list[str] = []

    def get(self, name: str) -> str | None:
        value = self.tokens.get(name)
        if value is None or not value.strip():
            if name not in self.missing:
                self.missing.append(name)
            return None
        value = value.strip()
        if UNSAFE.search(value):
            raise TokenError("token %s's value %r could end the markup or CSS it is written into"
                             % (name, value))
        return value

    def pairs(self, *pairs: tuple[str, str]) -> list[tuple[str, str]]:
        """(name, token) to (name, value), leaving out a token the file lacks."""
        out = []
        for key, token in pairs:
            value = self.get(token)
            if value is not None:
                out.append((key, value))
        return out

    def below(self, token: str) -> str | None:
        """The phone query's width: one pixel under the breakpoint, where MJML's
        desktop query (`min-width`) stops applying; the arithmetic is done here,
        as the token file's policy has it."""
        value = self.get(token)
        if value is None:
            return None
        match = PX.match(value)
        if not match:
            return value
        width = float(match.group(1)) - 1
        return "%gpx" % width


def type_props(theme: Theme, role: str, colour: str, tracking: str | None) -> list[tuple[str, str]]:
    props = theme.pairs(("font-size", "--type-%s-size" % role), ("line-height", "--type-%s-line" % role))
    if role != "legal":
        props += theme.pairs(("font-weight", "--type-%s-weight" % role))
    if tracking:
        props += theme.pairs(("letter-spacing", tracking))
    if role == "label":
        props.append(("text-transform", "uppercase"))
    props += theme.pairs(("color", colour))
    return props


def text_classes() -> list[str]:
    return ["text", *[role for role, _, _ in TYPE_ROLES], *[name for name, _ in COLOURS]]


# ---------------------------------------------------------------------------
# The CSS both outputs carry: dark mode and the phone rules
# ---------------------------------------------------------------------------

def css_rules(theme: Theme, select) -> list[str]:
    """The `<style>` rules, each selector built by `select(kind, role)`: the
    MJML and React Email markups put the class on different elements."""
    rules: list[str] = []

    def rule(selectors: list[str], decls: list[tuple[str, str]]) -> str | None:
        if not decls:
            return None
        body = "; ".join("%s: %s !important" % (k, v) for k, v in decls)
        return "%s { %s; }" % (", ".join(selectors), body)

    dark: list[str | None] = []
    for role, token in DARK_SURFACE.items():
        dark.append(rule(select("surface", role), theme.pairs(("background-color", token))))
    fg = [r for r in text_classes() if r not in DARK_MUTED]
    muted = [r for r in text_classes() if r in DARK_MUTED]
    dark.append(rule([s for r in fg for s in select("text", r)], theme.pairs(("color", "--email-dark-fg"))))
    dark.append(rule([s for r in muted for s in select("text", r)],
                     theme.pairs(("color", "--email-dark-fg-muted"))))
    dark.append(rule(select("divider", "divider"), theme.pairs(("border-top-color", "--email-dark-border"))))
    dark.append(rule(["a"], theme.pairs(("color", "--email-dark-link"))))
    # A class beats `a`: without it the dark link colour lands on the accent fill.
    dark.append(rule(select("button", "button"), theme.pairs(("color", "--fg-on-accent"))))
    dark_rules = [r for r in dark if r]
    if dark_rules:
        rules.append("@media (prefers-color-scheme: dark) {\n  %s\n}" % "\n  ".join(dark_rules))

    phone: list[str | None] = []
    for role, (size, line) in MOBILE_TYPE.items():
        phone.append(rule(select("text", role), theme.pairs(("font-size", size), ("line-height", line))))
    phone.append(rule(select("gutter", "surface"),
                      theme.pairs(("padding-left", "--email-gutter-mobile"),
                                  ("padding-right", "--email-gutter-mobile"))))
    phone_rules = [r for r in phone if r]
    width = theme.below("--email-bp-stack")
    if phone_rules and width:
        rules.append("@media only screen and (max-width: %s) {\n  %s\n}" % (width, "\n  ".join(phone_rules)))
    return rules


# ---------------------------------------------------------------------------
# MJML
# ---------------------------------------------------------------------------

def mjml_select(kind: str, role: str) -> list[str]:
    """Where MJML 5 puts `css-class`: on the `<td>` round an `mj-text`'s
    `<div>` and an `mj-button`'s or `mj-divider`'s inner markup, on the `<div>`
    of an `mj-section` or `mj-column` (whose `<table>` repeats the background),
    and on `<body>` for `mj-body` (whose `<div>` repeats it)."""
    name = "." + class_name(role)
    if kind == "text":
        return [name + " div"]
    if kind == "surface":
        return [name, name + " > div", name + " > table"]
    if kind == "gutter":
        return [name + " > table > tbody > tr > td"]
    if kind == "button":
        return [name + " a"]
    if kind == "divider":
        return [name + " p"]
    raise ValueError(kind)


def xml_attr(value: str) -> str:
    return (value.replace("&", "&amp;").replace('"', "&quot;")
            .replace("<", "&lt;").replace(">", "&gt;"))


def mj_tag(tag: str, attrs: list[tuple[str, str]]) -> str:
    return "<%s %s />" % (tag, " ".join('%s="%s"' % (k, xml_attr(v)) for k, v in attrs))


def mjml_head(theme: Theme, source: str, dropped: int) -> str:
    zero = theme.get("--space-0") or "0"
    defaults = [
        ("mj-all", theme.pairs(("font-family", "--font-sans"))),
        ("mj-body", [*theme.pairs(("width", "--email-width"), ("background-color", "--bg-canvas")),
                     ("css-class", class_name("canvas"))]),
        ("mj-section", [*theme.pairs(("background-color", "--bg-surface"),
                                     ("padding-top", "--gap-separate"), ("padding-bottom", "--gap-separate"),
                                     ("padding-left", "--gutter-page"), ("padding-right", "--gutter-page")),
                        ("css-class", class_name("surface"))]),
        ("mj-text", [*type_props(theme, "body", "--fg-default", None), ("padding", zero),
                     ("css-class", class_name("text"))]),
        ("mj-button", [*theme.pairs(("background-color", "--bg-accent"), ("color", "--fg-on-accent"),
                                    ("font-size", "--type-ui-size"), ("line-height", "--type-ui-line"),
                                    ("font-weight", "--type-ui-weight"), ("border-radius", "--radius-md"),
                                    ("inner-padding", "--email-button-pad")),
                       ("padding", zero), ("css-class", class_name("button"))]),
        ("mj-divider", [*theme.pairs(("border-color", "--border-subtle"), ("border-width", "--stroke-hairline")),
                        ("padding", zero), ("css-class", class_name("divider"))]),
        ("mj-spacer", theme.pairs(("height", "--gap-separate"))),
        ("mj-table", [*theme.pairs(("color", "--fg-default"), ("font-size", "--type-body-size"),
                                   ("line-height", "--type-body-line")), ("padding", zero)]),
    ]
    classes = []
    styled = {*text_classes(), *(name for name, _ in SURFACES)}
    for role, colour, tracking in TYPE_ROLES:
        classes.append((role, type_props(theme, role, colour, tracking)))
    for name, token in COLOURS:
        classes.append((name, theme.pairs(("color", token))))
    for name, token in SURFACES:
        classes.append((name, theme.pairs(("background-color", token))))
    for name, token in GAPS:
        classes.append((name, theme.pairs(("height", token))))
    for name, token in INSETS:
        classes.append((name, theme.pairs(("padding", token))))

    lines = ["<mj-attributes>"]
    lines += ["  " + mj_tag(tag, attrs) for tag, attrs in defaults if attrs]
    # A class's css-class replaces the tag's (MJML 5 merges only mj-classes'),
    # so a gap or an inset carries none: a section keeps its wds-surface.
    lines += ["  " + mj_tag("mj-class", [("name", name), *attrs,
                                         *([("css-class", class_name(name))] if name in styled else [])])
              for name, attrs in classes if attrs]
    lines.append("</mj-attributes>")
    breakpoint = theme.get("--email-bp-stack")
    if breakpoint:
        lines.append(mj_tag("mj-breakpoint", [("width", breakpoint)]))
    # MJML writes the PixelsPerInch block but no font for the Word engine, which
    # lands on its serif for a stack that starts with -apple-system: the
    # build's own rule, as build_email.py adds it.
    lines.append('<mj-raw><meta name="color-scheme" content="light dark" />'
                 '<meta name="supported-color-schemes" content="light dark" />'
                 '<!--[if mso]>%s<![endif]--></mj-raw>' % " ".join(MSO_FONT_STYLE.split()))
    link = theme.get("--fg-link")
    if link:
        # Inlined by MJML onto every link; a button's own colour stays (juice
        # keeps an element's inline style over a stylesheet's).
        lines.append('<mj-style inline="inline">a { color: %s; }</mj-style>' % link)
    rules = css_rules(theme, mjml_select)
    if rules:
        lines.append("<mj-style>")
        lines += ["  " + line for rule in rules for line in rule.splitlines()]
        lines.append("</mj-style>")

    head = "\n".join("    " + line for line in lines)
    return "%s\n<mjml>\n  <mj-head>\n%s\n  </mj-head>\n</mjml>\n" % (
        mjml_comment(theme, source, dropped), head)


def header_lines(theme: Theme, source: str, dropped: int) -> list[str]:
    lines = ["Generated by email-template-system's export_email_theme.py from %s." % source,
             "Do not edit: change the tokens and run it again."]
    if dropped:
        lines.append("%d entries in the token file's `dropped` have no email form: no class reads them." % dropped)
    if theme.missing:
        lines.append("Not in the token file, so left to the framework's default: %s." % ", ".join(theme.missing))
    return lines


def mjml_comment(theme: Theme, source: str, dropped: int) -> str:
    lines = header_lines(theme, source, dropped) + [
        "Include it inside the template's <mj-head> and compile with includes allowed:",
        "MJML 5 ignores them by default (email-template-system, email-workflow.md section 11).",
        "A css-class of your own replaces the theme's wds- class: write both."]
    # `--` cannot appear inside an XML comment, so a token's name loses it here.
    body = "\n".join("  " + re.sub(r"-{2,}", "-", re.sub(r"(?<![\w-])--", "", line)) for line in lines)
    return "<!--\n%s\n-->" % body


# ---------------------------------------------------------------------------
# React Email
# ---------------------------------------------------------------------------

def camel(name: str) -> str:
    """`--bg-canvas` to `bgCanvas`, `--email-h1-size-mobile` to `emailH1SizeMobile`."""
    parts = [p for p in name.lstrip("-").split("-") if p]
    if not parts:
        return name
    return parts[0] + "".join(p[:1].upper() + p[1:] for p in parts[1:])


def react_select(kind: str, role: str) -> list[str]:
    """React Email puts `className` on the element itself: `<Text>`'s `<p>`,
    `<Section>`'s or `<Container>`'s `<table>`, `<Body>`'s `<body>`,
    `<Button>`'s `<a>`, `<Hr>`'s `<hr>`; a gutter is the section's cells."""
    name = "." + class_name(role)
    if kind == "gutter":
        return [name + " > tbody > tr > td"]
    return [name]


def js_props(props: list[tuple[str, str]]) -> dict:
    out: dict = {}
    for key, value in props:
        js_key = camel(key)
        if key == "font-weight" and re.fullmatch(r"\d+", value):
            out[js_key] = int(value)       # React's types take a weight as a number
        elif value == "0":
            out[js_key] = 0
        else:
            out[js_key] = value
    return out


def react_theme(theme: Theme, source: str, dropped: int, typescript: bool) -> str:
    names: dict[str, str] = {}
    for token in theme.tokens:
        key = camel(token)
        if key in names:
            raise TokenError("tokens %s and %s are both %s in JavaScript" % (names[key], token, key))
        names[key] = token
    tokens = {camel(k): v for k, v in theme.tokens.items()}

    font = theme.pairs(("font-family", "--font-sans"))
    text = {role: js_props(font + type_props(theme, role, colour, tracking) + [("margin", "0")])
            for role, colour, tracking in TYPE_ROLES}
    edge = [("border-top", "%s solid %s" % (w, c))
            for w, c in [(theme.get("--stroke-hairline"), theme.get("--border-subtle"))] if w and c]
    styles = {
        "body": js_props([("margin", "0"), ("padding", "0"), *font,
                          *theme.pairs(("background-color", "--bg-canvas"))]),
        "container": js_props([("width", "100%"),
                               *theme.pairs(("max-width", "--email-width"), ("background-color", "--bg-surface"))]),
        "section": js_props(theme.pairs(("padding-top", "--gap-separate"), ("padding-bottom", "--gap-separate"),
                                        ("padding-left", "--gutter-page"), ("padding-right", "--gutter-page"))),
        "button": js_props([*font, *theme.pairs(("background-color", "--bg-accent"), ("color", "--fg-on-accent"),
                                                ("font-size", "--type-ui-size"), ("line-height", "--type-ui-line"),
                                                ("font-weight", "--type-ui-weight"),
                                                ("border-radius", "--radius-md"),
                                                ("padding", "--email-button-pad")),
                            ("text-decoration", "none")]),
        "divider": js_props([("border", "none"), *edge, ("margin", "0")]),
        "link": js_props(theme.pairs(("color", "--fg-link"))),
    }
    for name, token in COLOURS:
        styles[name] = js_props(theme.pairs(("color", token)))
    for name, token in SURFACES:
        styles[name] = js_props(theme.pairs(("background-color", token)))
    for name, token in INSETS:
        styles[camel(name)] = js_props(theme.pairs(("padding", token)))
    styles = {k: v for k, v in styles.items() if v}
    spacers = {camel(name): js_props([*theme.pairs(("height", token)), ("font-size", "0"), ("line-height", "0")])
               for name, token in GAPS if theme.get(token)}
    roles = ["canvas", "surface", "sunken", "text", "button", "divider",
             *[r for r, _, _ in TYPE_ROLES], *[n for n, _ in COLOURS]]
    classes = {camel(r): class_name(r) for r in roles}
    head_css = "\n".join(css_rules(theme, react_select))

    const = " as const;" if typescript else ";"

    def export(name: str, value) -> str:
        return "export const %s = %s%s" % (name, json.dumps(value, indent=2, ensure_ascii=False), const)

    lines = ["// " + line for line in header_lines(theme, source, dropped) + [
        "Put headCss in a <style> inside <Head>, and give each element its class beside its",
        "style: <Text className={classes.h1} style={text.h1}>. The class is what dark mode reads.",
        "Send withMso(await render(<Email />)): React cannot write the Word engine's block."]]
    signature = "html: string): string" if typescript else "html)"
    with_mso = WITH_MSO % (json.dumps(MSO_HEAD_BLOCK), signature)
    return "\n".join([*lines, "", export("tokens", tokens), "", export("text", text), "",
                      export("styles", styles), "", export("spacers", spacers), "",
                      export("classes", classes), "", export("headCss", head_css), "", with_mso])


# The block build_email.py adds to <head>: the PixelsPerInch setting that
# defuses the 120-DPI bug, and a font the Word engine has. React renders no
# comment, so the theme adds it to the rendered string, once.
WITH_MSO = r"""export const msoHead = %s;

/** The rendered email with the Word engine's namespaces on <html> and its block in <head>. */
export function withMso(%s {
  if (html.includes("o:PixelsPerInch")) return html;
  const namespaces = ' xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office"';
  return html
    .replace(/<html(?![^>]*\bxmlns:o=)(?=[\s>])/i, (tag) => tag + namespaces)
    .replace(/<head(?:\s[^>]*)?>/i, (tag) => tag + msoHead);
}
"""


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m scripts.export_email_theme",
        description="Write the email tokens as an MJML head to mj-include, or a React Email theme module.",
    )
    parser.add_argument("--format", required=True, choices=("mjml", "react-email"))
    parser.add_argument("--out", "-o", help="write here (default: stdout); for react-email, a .js "
                                            "or .mjs name writes JavaScript, anything else TypeScript")
    parser.add_argument("--tokens", help="email-tokens.json (default: the project's .design-suite.json "
                                         "emailTokens, else assets/email-tokens.json)")
    parser.add_argument("--strict", action="store_true", help="exit 1 when the tokens lack a role")
    parser.add_argument("--quiet", "-q", action="store_true", help="suppress the report")
    args = parser.parse_args(argv)

    try:
        config = None if args.tokens else project_config()
    except ConfigError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2
    tokens_path = (Path(args.tokens) if args.tokens else
                   config.email_tokens if config and config.email_tokens else default_tokens_path())
    clash = refuse_overwrite(args.out, tokens_path)
    if clash:
        print("error: %s" % clash, file=sys.stderr)
        return 2
    try:
        theme = Theme(load_tokens(tokens_path))
        dropped = len(load_dropped(tokens_path))
        if args.format == "mjml":
            text = mjml_head(theme, tokens_path.name, dropped)
        else:
            typescript = not (args.out and Path(args.out).suffix.lower() in (".js", ".mjs"))
            text = react_theme(theme, tokens_path.name, dropped, typescript)
    except TokenError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2

    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(text.encode("utf-8"))
    else:
        sys.stdout.write(text)

    if not args.quiet:
        stream = sys.stdout if args.out else sys.stderr
        print("wrote   %s (%s, from %s)" % (args.out or "<stdout>", args.format, tokens_path), file=stream)
        if theme.missing:
            print("WARN    not in the token file, left to the framework's default: %s"
                  % ", ".join(theme.missing), file=stream)
    return 1 if args.strict and theme.missing else 0


if __name__ == "__main__":
    for _stream in (sys.stdout, sys.stderr):
        if getattr(_stream, "encoding", "utf-8").lower() not in ("utf-8", "utf8"):
            _stream.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
