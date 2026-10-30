#!/usr/bin/env python3
"""
check_roles.py — the role-pair contrast gate.

generate_color_ramp.py checks ramp steps against one canvas. Components read
Tier-2 ROLES, per theme, in pairs: body text on a sunken well, a link on a
card, a label on the accent fill, text inside an .inverse band. This resolves
every role through its var() chain in each scope of tokens.css and checks the
pairs components actually use:

  light          :root (and :root:not([data-theme="dark"]))
  dark           :root + [data-theme="dark"]
  inverse        light + .inverse                  (on the light --bg-inverse)
  dark-inverse   dark + .inverse + [data-theme="dark"] .inverse
                                                   (on the dark --bg-inverse)

A block belongs to a scope by project_config's classify_rule(), the answer
every reader takes: `html[data-theme=dark]` is the dark theme however it is
spelled, `:root:not(…)` is the root, and the light root alone when its guard
leaves the dark theme out; each block keeps its own selector's weight, so
`:root` beats a later `html`. With no block that is the dark theme (a
dark theme written only in `@media (prefers-color-scheme: dark)`, or as a
class such as `html.dark`), the dark scopes are named on stderr and their pairs
are not measured, unless the roles are `light-dark()` under `color-scheme:
light dark`; measuring them on the light colours passed a dark theme the gate
never saw (PY-B-7). An `.inverse` band with no block is still measured: its
text inherits the parent's ink, which is what the page shows.

Where two blocks of a scope set the same property, the cascade decides, as in
a browser: the heavier selector wins, and of two the same weight the block
written later does. `:root` and `[data-theme="dark"]` weigh the same, so a
`:root` written below the dark block beats it on a dark page, while the dark
band's selector is heavier than `.inverse`, whatever the order. Several files
are one system, written in the order they are listed. Cascade layers are not
modelled: a block inside `@layer` counts like an unlayered one, so a system
that splits its scopes across layers (the starter keeps them all in `tokens`)
can differ from the browser, which ranks an unlayered block above a layered one.

A role written `light-dark(LIGHT, DARK)` (P33) takes the branch of the scope's
`color-scheme`, the last one its blocks declare: the one it names alone
(`.inverse { color-scheme: dark }` reads the dark branch), both when it allows
both (`light dark`), since the visitor's preference then picks, and light when
it names neither, as `normal` does.

Text needs 4.5:1 (WCAG 1.4.3). Borders that mark a control's boundary, and the
focus ring, need 3:1 (1.4.11). Translucent roles (--bg-hover, --bg-scrim) are
overlays; a11y_runtime measures those composited in a browser.

Usage — run by path from the PROJECT root:
    python <skill>/scripts/check_roles.py src/styles/tokens.css
    python <skill>/scripts/check_roles.py tokens.css --pairs role-pairs.json
    python <skill>/scripts/check_roles.py tokens.css --table     # the role table
    python <skill>/scripts/check_roles.py tokens.css --json

A pairs file is a JSON list of {"fg", "bg", "min", "scopes"} objects (scopes
from the four above; "on" names a different scope for the background). It
replaces the built-in list, which is written for the starter's roles.

Exit codes: 0 every pair passes · 1 a pair fails · 2 bad invocation, a role
that cannot be resolved to a colour, or no pair measured at all.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import pathlib
import re
import sys

sys.dont_write_bytecode = True     # the sibling import below must not leave __pycache__
HERE = pathlib.Path(__file__).resolve().parent
try:                                # python -m scripts.check_roles
    from scripts import generate_color_ramp as ramp  # type: ignore
except ImportError:                 # run by path
    _spec = importlib.util.spec_from_file_location("wds_generate_color_ramp", HERE / "generate_color_ramp.py")
    ramp = importlib.util.module_from_spec(_spec)
    sys.modules[_spec.name] = ramp
    _spec.loader.exec_module(ramp)
try:                                # the sibling copy of the shared reader
    from scripts.project_config import class_themes, classify_rule  # type: ignore
except ImportError:
    sys.path.insert(0, str(HERE))
    from project_config import class_themes, classify_rule  # type: ignore[no-redef]

DARK = '[data-theme="dark"]'
LIGHT_ROOT = ':root:not([data-theme="dark"])'      # a root rule the dark theme is left out of
BAND = re.compile(r"""(?:((?::root|html)?\[data-theme\s*=\s*(?:"dark"|'dark'|dark)\s*\])\s+)?\.inverse""")
NOT_DARK = re.compile(r""":not\(\s*(?::root|html)?\[data-theme\s*=\s*(?:"dark"|'dark'|dark)\s*\]\s*\)""")
SCOPES = {
    "light": [":root", LIGHT_ROOT],
    "dark": [":root", DARK],
    "inverse": [":root", LIGHT_ROOT, ".inverse"],
    "dark-inverse": [":root", DARK, ".inverse", f"{DARK} .inverse"],
}
TEXT = ["--fg-default", "--fg-strong", "--fg-muted", "--fg-subtle", "--fg-link", "--fg-accent"]
SURFACES = ["--bg-canvas", "--bg-surface", "--bg-raised", "--bg-sunken"]
BOTH = ["light", "dark"]


def _read_text(path: pathlib.Path) -> str:
    """A project's text file in the encoding json.detect_encoding() finds: a
    UTF-16 file (PowerShell 5.1's `>`) read as UTF-8 was garbage (class 4).
    project_config.read_text(), kept here so this script runs on its own."""
    raw = pathlib.Path(path).read_bytes()
    return raw.decode(json.detect_encoding(raw), errors="replace")


def default_pairs() -> list[dict]:
    """The pairs the starter's components actually put together."""
    pairs = [{"fg": fg, "bg": bg, "min": 4.5, "scopes": BOTH} for fg in TEXT for bg in SURFACES]
    pairs += [{"fg": fg, "bg": bg, "min": 4.5, "scopes": BOTH}
              for fg in ("--fg-danger", "--fg-success", "--fg-warning")
              for bg in ("--bg-canvas", "--bg-surface")]
    pairs += [{"fg": "--fg-on-accent", "bg": bg, "min": 4.5, "scopes": BOTH}
              for bg in ("--bg-accent", "--bg-accent-hover")]
    pairs += [{"fg": "--fg-on-inverse", "bg": "--bg-inverse", "min": 4.5, "scopes": BOTH}]
    pairs += [{"fg": fg, "bg": "--bg-inverse", "min": 4.5, "scopes": [scope], "on": on}
              for fg in TEXT[:5] for scope, on in (("inverse", "light"), ("dark-inverse", "dark"))]
    pairs += [{"fg": "--border-strong", "bg": bg, "min": 3.0, "scopes": BOTH}
              for bg in ("--bg-canvas", "--bg-surface", "--bg-sunken")]
    pairs += [{"fg": "--border-focus", "bg": bg, "min": 3.0, "scopes": BOTH}
              for bg in ("--bg-canvas", "--bg-surface", "--bg-sunken")]
    pairs += [{"fg": f"--fg-on-{intent}", "bg": f"--bg-{intent}", "min": 4.5, "scopes": BOTH}
              for intent in ("success", "warning", "danger")]
    pairs += [{"fg": "--border-invalid", "bg": bg, "min": 3.0, "scopes": BOTH}
              for bg in ("--bg-canvas", "--bg-surface", "--bg-sunken")]
    return pairs


class Unresolvable(Exception):
    pass


# The one @supports read: a positive query on light-dark(), which every
# current browser applies. `not`, `or` and `and` are left out, since the
# gate cannot tell when they hold (CodeRabbit on #112).
LIGHT_DARK_QUERY = re.compile(r"@supports\s*\(\s*(?:background-)?color\s*:\s*light-dark\([^()]*\)\s*\)\s*$", re.I)


def own_text(body: str) -> str:
    """A block's text at its own depth: each nested block, its prelude
    included, left out."""
    out, depth = [], 0
    for ch in body:
        if ch == "{":
            if depth == 0:
                text = "".join(out)
                out = [text[:text.rfind(";") + 1]]
            depth += 1
        elif ch == "}":
            depth -= 1
        elif depth == 0:
            out.append(ch)
    return "".join(out)


def rules(css: str) -> list[tuple[list[str], dict[str, str]]]:
    """Innermost `selectors { declarations }` blocks outside any @media or
    @supports (a conditional block is not a theme). One @supports is read: a
    condition on light-dark() holds the roles every current browser uses,
    over the concrete ones older browsers keep (P33, Codex on #112)."""
    css = re.sub(r"/\*.*?\*/", " ", css, flags=re.S)
    out, stack, start = [], [], 0
    for i, ch in enumerate(css):
        if ch == "{":
            stack.append((css[start:i].strip().rsplit(";", 1)[-1].strip(), i + 1))
            start = i + 1
        elif ch == "}":
            prelude, opened = stack.pop() if stack else ("", start)
            # A rule's own declarations, its nested blocks left out: native
            # nesting (`:root { --x: …; @media (…) {…} }`) kept the whole
            # rule unread (the audit's W8).
            body = own_text(css[opened:i])
            if not prelude.startswith("@") and not any(
                    p.startswith(("@media", "@container"))
                    or (p.startswith("@supports") and not LIGHT_DARK_QUERY.match(p)) for p, _ in stack):
                decls = dict(re.findall(r"(--[\w-]+)\s*:\s*([^;]+);?", body))
                # Which branch of light-dark() the scope reads (P33).
                decls.update(re.findall(r"(?<![\w-])(color-scheme)\s*:\s*([^;]+);?", body))
                out.append(([s.strip() for s in prelude.split(",")], {k: v.strip() for k, v in decls.items()}))
            start = i + 1
    return out


def element(selector: str) -> str:
    """Which element a scope's selector is on: the root (`:root` and its
    `[data-theme]`) or the inverse band (`.inverse`, and the dark one)."""
    return "band" if selector.endswith(".inverse") else "root"


def weight(selector: str) -> tuple[int, int, int]:
    """A selector's specificity, (ids, classes, types), as the browser ranks
    it: `:root` and `[data-theme="dark"]` weigh a class each and `html` a
    type, so `:root` beats a later `html` (Codex on #226); `:where()` and `*`
    weigh nothing, and `:not()` weighs what it holds."""
    s = re.sub(r":where\((?:[^()]|\([^()]*\))*\)", "", selector)
    s = re.sub(r":(?:not|is)\(", " ", s).replace(")", " ")
    return (len(re.findall(r"#[\w-]+", s)),
            len(re.findall(r"\.[\w-]+|\[[^\]]*\]|:[\w-]+", s)),
            len(re.findall(r"(?:^|[\s>+~])([a-zA-Z][\w-]*)", s)))


def canonical(selectors: list[str]) -> dict[str, tuple[int, int, int]]:
    """The scope selectors a block's list stands for, each read by
    classify_rule(), with the weight of the selector that stands for it: the
    root, or the light root when a guard leaves the dark theme out
    (`:root:not([data-theme="dark"])`, Codex on #226); the dark theme however
    it is spelled (`html[data-theme=dark]`); and the two bands."""
    out: dict[str, tuple[int, int, int]] = {}
    for selector in selectors:
        kind = classify_rule(selector)
        scope = None
        if kind == "default":
            scope = LIGHT_ROOT if NOT_DARK.search(selector) else ":root"
        elif kind == "theme:dark":
            scope = DARK
        else:
            band = BAND.fullmatch(" ".join(selector.split()))
            if band:
                scope = f"{DARK} .inverse" if band.group(1) else ".inverse"
        if scope:
            out[scope] = max(out.get(scope, (0, 0, 0)), weight(selector))
    return out


def scopes(css: str) -> dict[str, dict[str, str]]:
    blocks = [(canonical(sels), decls) for sels, decls in rules(css)]
    merged = {}
    for name, wanted in SCOPES.items():
        env: dict[str, str] = {}
        for el in dict.fromkeys(element(w) for w in wanted):
            here = [w for w in wanted if element(w) == el]
            # The browser's cascade for the element: the heavier selector wins,
            # and the block written later between two of the same weight, so
            # `:root` below `[data-theme="dark"]` beats it (N51, CodeRabbit on #187).
            # The weight is the written selector's, not its scope's (Codex on #226).
            matching = sorted(((max(sels[w] for w in here if w in sels), i, decls)
                               for i, (sels, decls) in enumerate(blocks) if any(w in sels for w in here)),
                              key=lambda m: m[:2])
            declared = None
            for _, _, decls in matching:
                env.update({k: v for k, v in decls.items() if k != "color-scheme"})
                declared = decls.get("color-scheme", declared)
            # Read once the element's own properties are all in, whatever their
            # order, then inherited by the band (CodeRabbit on #112).
            if declared is not None:
                env["color-scheme"] = substitute(env, declared)
        merged[name] = env
    return merged


def unread(css: str) -> dict[str, str]:
    """The dark scopes, with why, when no block of the stylesheet names the
    dark theme, root or band: their pairs would be measured on the light colours and pass
    (PY-B-7). A dark scope whose roles are light-dark() under `light dark` is
    read, block or not. A band with no block of its own is still measured:
    its text inherits the parent's ink, which is what it shows."""
    present = set().union(*(canonical(sels) for sels, _ in rules(css)))
    # The dark band alone is a dark theme the gate sees: its root re-points nothing.
    if DARK in present or f"{DARK} .inverse" in present or "dark" in schemes(scopes(css)["dark"]):
        return {}
    found = [f"`{t}`" for sels, _ in rules(css) for s in sels for t in class_themes(s)]
    if re.search(r"prefers-color-scheme\s*:\s*dark", css):
        found.append("`@media (prefers-color-scheme: dark)`")
    why = f"no {DARK} block" + (f"; the dark theme in {', '.join(dict.fromkeys(found))} is not read: "
                                f"write it as {DARK} too" if found else "")
    return {"dark": why, "dark-inverse": why}


def substitute(env: dict[str, str], value: str) -> str:
    """`value` with each `var(--x[, fallback])` replaced from `env`, as the
    browser does before it reads a property (`color-scheme: var(--scheme)`)."""
    pattern = re.compile(r"var\(\s*(--[\w-]+)\s*(?:,\s*([^()]*))?\)")
    for _ in range(16):                            # a chain, never a cycle forever
        new = pattern.sub(lambda m: env.get(m.group(1), m.group(2) or ""), value)
        if new == value:
            break
        value = new
    return value


def used(env: dict[str, str], preference: str) -> str:
    """The scheme a scope uses for a visitor who prefers `preference`: the one
    its `color-scheme` names alone, the preference under `light dark`, light
    under none."""
    can = schemes(env)
    return preference if preference in can and len(can) == 2 else can[0]


def schemes(env: dict[str, str]) -> list[str]:
    """The colour schemes a scope's light-dark() roles can take (P33): the one
    its `color-scheme` names alone (`dark`, `only light`); both when it allows
    both (`light dark`), because the visitor's preference picks then, not the
    scope's name (Codex on #112); light when it names neither, as `normal`."""
    named = set(env.get("color-scheme", "").split()) - {"only"}
    if named in ({"light"}, {"dark"}):
        return [named.pop()]
    return ["light", "dark"] if {"light", "dark"} <= named else ["light"]


def nominal(env: dict[str, str], scope: str) -> str:
    """The scheme the role table shows for a scope: its own theme when the
    scope can take it, else the one it is held to."""
    own = "dark" if scope.startswith("dark") else "light"
    can = schemes(env)
    return own if own in can else can[0]


def light_dark(value: str):
    """`light-dark(A, B)` as (A, B), split at its one top-level comma, or None."""
    m = re.fullmatch(r"light-dark\((.*)\)", value.strip(), flags=re.S)
    if not m:
        return None
    depth, parts, start = 0, [], 0
    for i, ch in enumerate(m.group(1)):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth < 0:                  # `light-dark(a) b(c)`: not one call
                return None
        elif ch == "," and depth == 0:
            parts.append(m.group(1)[start:i])
            start = i + 1
    parts.append(m.group(1)[start:])
    return (parts[0].strip(), parts[1].strip()) if len(parts) == 2 and depth == 0 else None


def resolve(env: dict[str, str], name: str, theme: str = "light") -> str:
    value, seen = env.get(name), {name}
    if value is None:
        raise Unresolvable(f"{name} is not declared")
    while True:
        branches = light_dark(value)
        if branches is not None:
            value = branches[theme == "dark"]
            continue
        m = re.fullmatch(r"var\(\s*(--[\w-]+)\s*(?:,\s*(.+))?\)", value.strip())
        if not m:
            break
        ref, fallback = m.group(1), m.group(2)
        if ref in seen:
            raise Unresolvable(f"{name}: var() cycle through {ref}")
        seen.add(ref)
        value = env.get(ref, fallback)
        if value is None:
            raise Unresolvable(f"{name}: {ref} is not declared")
    return value.strip()


def colour(env: dict[str, str], name: str, theme: str = "light"):
    raw = resolve(env, name, theme)
    # The alpha is read apart (the audit's W1): the parser reads a colour
    # without it, `#00000080` and `oklch(0% 0 0 / 0.5)` as solid black.
    try:
        alpha = ramp.alpha_of(raw)
        parsed = ramp.parse_color(raw)
    except Exception as exc:  # noqa: BLE001 - the parser's own message is the useful part
        raise Unresolvable(f"{name} = {raw}: not a colour ({exc})") from None
    if alpha < 1:
        raise Unresolvable(f"{name} = {raw} is translucent; measure it composited")
    return parsed


def valid_pairs(pairs: object) -> list[dict]:
    """A pairs file's pairs, or ValueError naming the pair and the key (W6):
    a string `scopes` was read as letters, and `min: "4.5"` a traceback."""
    if not isinstance(pairs, list):
        raise ValueError(f"the top level must be a list of pairs, not {json.dumps(pairs)[:40]}")
    for i, pair in enumerate(pairs):
        if not isinstance(pair, dict):
            raise ValueError(f"pair {i} must be an object, not {json.dumps(pair)[:40]}")
        for key in ("fg", "bg"):
            if not isinstance(pair.get(key), str):
                raise ValueError(f"pair {i}: `{key}` must be a custom property's name")
        if isinstance(pair.get("min"), bool) or not isinstance(pair.get("min"), (int, float)):
            raise ValueError(f"pair {i}: `min` must be a number, not "
                             f"{json.dumps(pair['min']) if 'min' in pair else 'missing'}")
        scopes = pair.get("scopes", BOTH)
        if not isinstance(scopes, list) or not all(isinstance(s, str) for s in scopes):
            raise ValueError(f"pair {i}: `scopes` must be a list of scope names, not {json.dumps(scopes)[:40]}")
        if not isinstance(pair.get("on", ""), str):
            raise ValueError(f"pair {i}: `on` must be a scope's name")
    return pairs


def check(css: str, pairs: list[dict]) -> list[dict]:
    envs = scopes(css)
    absent = unread(css)
    results = []
    for pair in pairs:
        for scope in pair.get("scopes", BOTH):
            on = pair.get("on", scope)
            if scope in absent or on in absent:          # main() names it (PY-B-7)
                continue
            seen = set()
            # Each preference the visitor can have: a scope that forces its
            # scheme keeps it, and one under `light dark` follows, so a forced
            # band is also measured on its parent's other scheme (CodeRabbit on #112).
            for preference in ("light", "dark"):
                theme, bg_theme = used(envs[scope], preference), used(envs[on], preference)
                values = (resolve(envs[scope], pair["fg"], theme), resolve(envs[on], pair["bg"], bg_theme))
                if values in seen:                       # the same colours: one result is enough
                    continue
                seen.add(values)
                ratio = ramp.worst_contrast(colour(envs[scope], pair["fg"], theme),
                                                  colour(envs[on], pair["bg"], bg_theme))
                varies = len(schemes(envs[scope])) == 2 or len(schemes(envs[on])) == 2
                ok = ratio + 1e-9 >= pair["min"]
                # Two places, as the report prints it; a pair under its minimum
                # is cut, not rounded, so 4.4997 fails as 4.49, never as a
                # "4.50:1, needs 4.5:1" (PY-B-20).
                shown = round(ratio, 2) if ok else math.floor(ratio * 100) / 100
                results.append({"fg": pair["fg"], "bg": pair["bg"], "scope": scope, "on": on, "scheme": theme,
                                **({"preference": preference} if varies else {}),
                                "ratio": shown, "min": pair["min"], "ok": ok})
    return results


TABLE_ROLES = ["--bg-canvas", "--bg-surface", "--bg-raised", "--bg-sunken", "--bg-inverse",
               "--fg-default", "--fg-strong", "--fg-muted", "--fg-subtle", "--fg-disabled",
               "--fg-accent", "--fg-link", "--fg-on-accent", "--fg-on-inverse",
               "--border-subtle", "--border-default", "--border-strong", "--border-focus",
               "--bg-accent", "--bg-accent-hover", "--fg-danger", "--bg-danger"]


def table(css: str) -> str:
    """The role table color-system.md quotes: each role's primitive per theme,
    and text roles' ratios on the canvas."""
    envs = scopes(css)

    def step(scope, role):
        value = envs[scope].get(role, "")
        branches = light_dark(value)
        if branches is not None:           # P33: the branch this scope reads
            value = branches[nominal(envs[scope], scope) == "dark"]
        m = re.fullmatch(r"var\((--[\w-]+)\)", value.strip())
        return f"`{m.group(1)}`" if m else (f"`{value}`" if value else "—")

    def on_canvas(scope, role):
        if not role.startswith(("--fg-", "--border-")) or role in ("--fg-on-accent", "--fg-on-inverse"):
            return ""
        theme = nominal(envs[scope], scope)
        try:
            return (f"{ramp.worst_contrast(colour(envs[scope], role, theme), colour(envs[scope], '--bg-canvas', theme)):.2f}"
                    ":1")
        except Unresolvable:
            return ""

    lines = ["| Tier-2 role | Light | Dark | On the canvas, light / dark |", "|---|---|---|---|"]
    for role in TABLE_ROLES:
        if role not in envs["light"]:
            continue
        ratios = " / ".join(r for r in (on_canvas("light", role), on_canvas("dark", role)) if r)
        lines.append(f"| `{role}` | {step('light', role)} | {step('dark', role)} | {ratios} |")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="Role-pair contrast gate: resolve Tier-2 roles per theme and check the pairs components use.")
    ap.add_argument("tokens", nargs="+",
                    help="the project's tokens.css; several files are one system, read in order, the last winning")
    ap.add_argument("--pairs", metavar="FILE", help="JSON pair list, replacing the built-in one")
    ap.add_argument("--table", action="store_true", help="print the role table (markdown) and exit")
    ap.add_argument("--json", action="store_true", help="machine-readable results")
    args = ap.parse_args()

    paths = [pathlib.Path(t) for t in args.tokens]
    missing = next((p for p in paths if not p.is_file()), None)
    if missing:
        print(f"check_roles: no such file: {missing}", file=sys.stderr)
        return 2
    # A project may keep its ramps in one file and its roles in another; the
    # config reader merges them in order, and so does this (Codex on #187).
    css = "\n".join(_read_text(p) for p in paths)
    if args.table:
        sys.stdout.write(table(css))
        return 0
    try:
        # bytes: json detects UTF-16 and a BOM, which PowerShell's `>` writes
        pairs = valid_pairs(json.loads(pathlib.Path(args.pairs).read_bytes())) if args.pairs else default_pairs()
        results = check(css, pairs)
    except (OSError, ValueError, KeyError) as exc:
        print(f"check_roles: bad pairs file {args.pairs}: {exc}", file=sys.stderr)
        return 2
    except Unresolvable as exc:
        print(f"check_roles: {exc}", file=sys.stderr)
        return 2
    absent = unread(css)
    for scope, why in absent.items():
        print(f"check_roles: the {scope} scope is not measured: {why}", file=sys.stderr)
    if not results:                     # a gate that measured nothing passed nothing (CodeRabbit on #226)
        print("check_roles: no pair was measured, so the gate proves nothing: "
              + (f"every scope the pairs name is unread ({', '.join(absent)})" if absent else "the pairs name no scope"),
              file=sys.stderr)
        return 2
    failed = [r for r in results if not r["ok"]]
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        for r in failed:
            where = r["scope"] if r["on"] == r["scope"] else f"{r['scope']} on the {r['on']} {r['bg']}"
            if "preference" in r:                        # it depends on the visitor's preference
                where += f", {r['preference']} preference"
            print(f"FAIL  {r['fg']} on {r['bg']} ({where}): {r['ratio']:.2f}:1, needs {r['min']}:1")
        print(f"role pairs: {len(results) - len(failed)} of {len(results)} pass"
              + ("" if failed else " — every declared pair clears its minimum.")
              + (f" Not measured: {', '.join(absent)}." if absent else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    # A Windows pipe (git hook, CI, `> file`) defaults to the ANSI code page,
    # where printing a dash or an arrow writes cp1252 or raises. Consoles and
    # Claude Code already use UTF-8 and are left alone.
    for _stream in (sys.stdout, sys.stderr):
        if getattr(_stream, "encoding", "utf-8").lower() not in ("utf-8", "utf8"):
            _stream.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
