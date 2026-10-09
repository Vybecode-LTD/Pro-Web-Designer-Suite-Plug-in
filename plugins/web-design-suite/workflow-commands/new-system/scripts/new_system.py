#!/usr/bin/env python3
"""new_system.py — /web-design-suite:new-system (P26, XC-C3 and SS-C6): a brand
colour to a working token system.

  1. the accent ramp, from the brand colour, the colour kept exact at its
     nearest step (web-design-studio's generate_color_ramp.py --anchor-seed);
  2. the neutral ramp, on the brand's hue or --neutral-hue (--neutral);
  3. the type scale: the starter's, or generate_type_scale.py's for the scale
     flags given (--ratio, --dual-ratio, --base, --fluid, --snap-px);
  4. the starter styles (reset, base, layout, utilities, overrides, index and
     tokens.css) written to --out, with those ramps and that scale in
     tokens.css;
  5. check_roles.py on the new tokens.css: every role pair, in every theme.

It never overwrites a file without --force. The Tier-2 roles are the starter's:
when a pair fails, the fix is a role pointing at another step (check_roles
names the pair), never a new literal.

Usage, from the project's root:
    python new_system.py BRAND [--out DIR] [--neutral-hue H] [--hue-shift X]
                         [--gamut srgb|p3] [--ratio R] [--dual-ratio R]
                         [--base PX] [--fluid MIN_VW MAX_VW] [--snap-px] [--force]

Exit codes: 0 written and every role pair passes, 1 written but a role pair
fails, 2 nothing written (bad invocation, a file in the way, a generator that
refused), or written but check_roles could not run. Standard library only;
Python 3.9 or newer.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence

sys.dont_write_bytecode = True
PLUGIN = Path(__file__).resolve().parents[3]
STUDIO = PLUGIN / "skills" / "web-design-studio"
RAMP = STUDIO / "scripts" / "generate_color_ramp.py"
TYPE = STUDIO / "scripts" / "generate_type_scale.py"
ROLES = STUDIO / "scripts" / "check_roles.py"
STARTER = STUDIO / "assets" / "starter" / "styles"
DECLARATION = re.compile(r"^(\s*)(--[\w-]+):\s*(.+?;.*?)\s*$")
RAMP_NAME = re.compile(r"--(accent|neutral)-\d+$")
TEXT_NAME = re.compile(r"--text-[\w-]+$")


class Refused(Exception):
    """Nothing is written; the message says why."""


def run(command: List[str]) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-B", *command], capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def declarations(css: str, name: "re.Pattern[str]") -> Dict[str, str]:
    """Each matching custom property, with its value and trailing comment."""
    found = {}
    for line in css.splitlines():
        m = DECLARATION.match(line)
        if m and name.fullmatch(m.group(2)):
            found[m.group(2)] = m.group(3)
    return found


def generate(what: str, command: List[str], name: "re.Pattern[str]") -> Dict[str, str]:
    proc = run(command)
    if proc.returncode != 0:
        raise Refused(f"the {what} generator refused:\n{(proc.stderr or proc.stdout).strip()}")
    found = declarations(proc.stdout, name)
    if not found:
        raise Refused(f"the {what} generator printed no declarations")
    seed = proc.stderr.split("WCAG 2.2 contrast matrix")[0].strip()   # check_roles measures
    if seed:
        print(f"-- {what}\n{seed}\n")
    return found


def substitute(css: str, values: Dict[str, str], what: str) -> str:
    """The starter's declarations of these names, given the new values. The
    names must be the starter's own: a role reads each one."""
    starter = declarations(css, RAMP_NAME if what != "type scale" else TEXT_NAME)
    if what != "type scale":
        starter = {k: v for k, v in starter.items() if k.startswith(f"--{what.split()[0]}-")}
    if set(starter) != set(values):
        missing = sorted(set(starter) - set(values), key=css.find)
        extra = sorted(set(values) - set(starter))
        raise Refused(f"the {what} does not have the starter's steps, which its roles read"
                      + (f"; missing {', '.join(missing)}" if missing else "")
                      + (f"; not in the starter {', '.join(extra)}" if extra else "")
                      + (". Keep 3 steps down and 7 up: --dual-ratio widens the headings and keeps "
                         "the small steps legible" if what == "type scale" else ""))
    out = []
    for line in css.split("\n"):
        m = DECLARATION.match(line)
        if m and m.group(2) in values:
            line = f"{m.group(1)}{m.group(2)}: {values[m.group(2)]}"
        out.append(line)
    return "\n".join(out)


def renote(css: str, brand: str, accent: List[str], neutral: List[str], scale: List[str]) -> str:
    """The starter's notes that describe its own values, rewritten for these
    (Codex on #87): the ramps' commands, Ember, and the scale when it changed.
    Its measured ratios stay as the starter's, labelled so."""
    seed = f'"{brand}"'
    notes = [
        (r"/\* Neutral — .*?\*/", "/* Neutral, from /web-design-suite:new-system: generate_color_ramp.py\n       "
                                  + " ".join([seed, "--neutral", *neutral]) + " prints it. */"),
        (r"/\* Accent — .*?\*/", "/* Accent, from /web-design-suite:new-system: generate_color_ramp.py\n       "
                                 + " ".join([seed, "--anchor-seed", *accent]) + " prints it. The L values\n"
                                 "       are the studio's, tuned for contrast; check_roles.py measures the roles. */"),
    ]
    if scale:
        notes += [(r"Modular scale, ratio 1\.200.*?the studio preset\.",
                   "From /web-design-suite:new-system: generate_type_scale.py\n       "
                   + " ".join(scale) + " prints these steps."),
                  (r"/\* Same 380 -> 1440 viewport anchors.*?\*/",
                   "/* The fluid steps come from the same command. Keep the fluid spacing's\n"
                   "       anchors and these the same pair. */")]
    for pattern, note in notes:
        css, found = re.subn(pattern, lambda m: note, css, count=1, flags=re.S)
        if not found:
            raise Refused(f"the starter's tokens.css no longer has the note {pattern!r}")
    return css.replace("Verified ", "The starter measured ")


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="new_system.py",
                                 description="A brand colour to the starter's token system, with its "
                                             "ramps, type scale and styles, role pairs checked.")
    ap.add_argument("brand", help="the brand colour: hex (#e8440a) or OKLCH (oklch(64.5%% 0.188 42))")
    ap.add_argument("--out", default="src/styles", help="where the styles go (default: src/styles)")
    ap.add_argument("--neutral-hue", metavar="H", help="the neutral ramp's hue (default: the brand's)")
    ap.add_argument("--hue-shift", metavar="X", help="the accent ramp's hue drift (generate_color_ramp)")
    ap.add_argument("--gamut", choices=("srgb", "p3"), help="the ramps' gamut (generate_color_ramp)")
    scale = ap.add_argument_group("the type scale (default: the starter's)")
    scale.add_argument("--ratio")
    scale.add_argument("--dual-ratio")
    scale.add_argument("--base")
    scale.add_argument("--fluid", nargs=2, metavar=("MIN_VW", "MAX_VW"))
    scale.add_argument("--snap-px", action="store_true")
    ap.add_argument("--force", action="store_true", help="overwrite the styles already in --out")
    args = ap.parse_args(argv)

    out = Path(args.out)
    sources = sorted(STARTER.glob("*.css"))
    if not args.force:
        taken = [str(out / s.name) for s in sources if (out / s.name).exists()]
        if taken:
            print("error: these files exist, and new-system never overwrites one without --force:\n  "
                  + "\n  ".join(taken), file=sys.stderr)
            return 2

    gamut = ["--gamut", args.gamut] if args.gamut else []
    accent_flags = [*(["--hue-shift", args.hue_shift] if args.hue_shift else []), *gamut]
    neutral_flags = [*(["--neutral-hue", args.neutral_hue] if args.neutral_hue else []), *gamut]
    scale_flags = [*(["--ratio", args.ratio] if args.ratio else []),
                   *(["--dual-ratio", args.dual_ratio] if args.dual_ratio else []),
                   *(["--base", args.base] if args.base else []),
                   *(["--fluid", *args.fluid] if args.fluid else []),
                   *(["--snap-px"] if args.snap_px else [])]
    tokens = (STARTER / "tokens.css").read_bytes().decode("utf-8")
    try:
        accent = generate("accent ramp", [str(RAMP), args.brand, "--name", "accent", "--anchor-seed",
                                          *accent_flags, "--format", "css"], RAMP_NAME)
        neutral = generate("neutral ramp", [str(RAMP), args.brand, "--neutral", "--name", "neutral",
                                            *neutral_flags, "--format", "css"], RAMP_NAME)
        tokens = substitute(tokens, accent, "accent ramp")
        tokens = substitute(tokens, neutral, "neutral ramp")
        if scale_flags:
            tokens = substitute(tokens, generate("type scale", [str(TYPE), *scale_flags, "--format", "css"],
                                                 TEXT_NAME), "type scale")
        tokens = renote(tokens, args.brand, accent_flags, neutral_flags, scale_flags)
    except Refused as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    out.mkdir(parents=True, exist_ok=True)
    for source in sources:
        data = tokens.encode("utf-8") if source.name == "tokens.css" else source.read_bytes()
        (out / source.name).write_bytes(data)
    print(f"wrote {len(sources)} files to {out}: {', '.join(s.name for s in sources)}")
    print(f"  the ramps from {args.brand}; the type scale "
          + (f"from {' '.join(scale_flags)}" if scale_flags else "the starter's"))

    print("\n-- the role pairs (check_roles.py)", flush=True)
    code = subprocess.call([sys.executable, "-B", str(ROLES), str(out / "tokens.css")])
    return 0 if code == 0 else (1 if code == 1 else 2)


if __name__ == "__main__":
    sys.exit(main())
