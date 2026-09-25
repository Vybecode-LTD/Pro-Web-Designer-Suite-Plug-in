# web-design-suite bug hunt — web-design-studio + landing-page-conversion assets

Workdir: `...scratchpad\hunt\studio\` — plugin copied to `plugin\`, fixtures under `fixtures\`.
All repro commands run from `plugin\skills\web-design-studio\` unless noted, with
`$env:PYTHONDONTWRITEBYTECODE='1'` set. `<fx>` = the `fixtures\` folder above.

## Bugs

**STUDIO-1 · crash · `assets/configs/pre-commit-design-gate.sh:207`** (calls into
`scripts/audit_design.py`'s argparse, `:1096-1112`) — The shipped pre-commit hook invokes
`"$PYTHON" -m "$AUDIT_MODULE" --staged "$@"`, but `audit_design.py` has no `--staged` flag at
all. argparse rejects it and the gate's `run_gate()` treats any non-zero exit as failure, so
**every commit with staged CSS/JS is refused unconditionally**, regardless of real violations.
Repro: `python -m scripts.audit_design --staged <fx>\warnonly\warn.css`
Observed: `error: unrecognized arguments: --staged`, exit 2. Expected: audits the given files,
exits 0/1 by findings. Fix: drop `--staged` from the hook (it already passes bare staged paths)
or implement the flag. Confidence: high.

**STUDIO-2 · wrong-result · `scripts/audit_design.py:437`** (`margin_cancels_token`) — The
"`calc(var(t)*-1)` cancels a token" exception is `"var(--" in value and "-1" in
value.replace(" ", "")` — a bare substring test. Any plain, non-negated margin using a token
whose *name* contains "-1" (`--space-1`, `-10`, `-12`, `-16`) is wrongly treated as a legal
cancellation, silently dropping the L2 finding.
Repro: `python -m scripts.audit_design <fx>\components\button.css --json`
`.card-l2-bug-space16{margin-top:var(--space-16)}` (line 54) → only L6 reported, **no L2**.
`.card-l2-control-space6{margin-top:var(--space-6)}` (line 57, otherwise identical) → both L2
and L6 reported. Neither is `auto`, a real `calc(*-1)`, or an owl selector — both should get L2.
Fix: match the actual `calc(var(--x) * -1)` shape, not a raw substring. Confidence: high.

**STUDIO-3 · wrong-result · `scripts/audit_design.py:72-77`** (`TOKEN_FILE_PAT`) — Meant to
recognize only `tokens.css`/`brand-tokens.css`/`theme.css`-style names, but `[\w.-]*` in the
optional prefix can itself contain hyphens, so it matches **any** filename ending in
"…-token(s).css" — `broken-tokens.css`, `design-system-tokens.css`, `not-a-tokens.css`,
`layout-fake-token.css` all match and are fully exempted from Law 1.
Repro: `python <fx>\check_pat.py` (standalone regex check) → all four print `True`.
End-to-end: a file named to end in `-token.css` containing `padding: 37px;` audits clean.
Fix: anchor to one path segment / one hyphenated word, not an unbounded run. Confidence: high.

**STUDIO-4 · wrong-result · `scripts/audit_design.py:469,536`** (`declared_props` is dead code)
— Nothing ever checks that a `var(--x)` reference is a *real* token. `value_is_tokenized()`
accepts any string containing `var(--`, and L6 only recognizes a fixed prefix list inside
component files. An invented custom property — on or off the closed scale — passes everywhere:
outside component files it skips L1 *and* L6; even inside one, an unrecognized prefix skips L6.
Repro: `python -m scripts.audit_design <fx>\misc2\section-styles.css --json` (file has
`.thing-raw{padding:37px}`, `.thing-fake-token{padding:var(--totally-invented-token-xyz)}`,
`.thing-fake-space{padding:var(--space-97)}`, none in a component path/layer).
Observed: only `.thing-raw` (37px) is flagged; both var()-wrapped literals — one nonsense, one
an obviously off-scale invented Tier-1 name — get zero findings. Also reproducible inside a
component file via `.thing-invented-token-bad` in `<fx>\components\button.css`.
Fix: build the real token set from the project's token/theme files and check every `var(--x)`
against it — exactly what `declared_props` looks built for. Confidence: high.

**STUDIO-5 · wrong-result · `scripts/audit_design.py:645-657`** — `font-weight` is in
`TYPE_PROPS`, but `has_raw_length()` requires a unit (px/rem/em/…); a bare numeral has none, so
`font-weight: 700;` is never flagged by any law, despite `--weight-*` tokens existing for it.
Repro: `<fx>\components\button.css` `.btn-fontweight-bad{font-weight:700}` → zero findings vs.
`.btn-fontweight-good{font-weight:var(--weight-bold)}` → correctly flagged L6.
Fix: add a numeric-literal branch for `font-weight`. Confidence: high.

**STUDIO-6 · wrong-result · `scripts/audit_design.py:621-634`** — Named-color detection requires
`prop in COLOR_PROPS`; `border` is added only to the hex/functional-color arm
(`prop in COLOR_PROPS or prop == "border"`), not the named-color `elif`. So `border-color: red;`
is flagged (L1 named-color) but the equivalent `border: 1px solid red;` is not.
Repro: `<fx>\components\button.css` — `.btn-border-shorthand-bad{border:1px solid red}` (no
finding) vs `.btn-border-color-bad{border-color:red}` (flagged).
Fix: `elif NAMED_COLOR.search(value) and (prop in COLOR_PROPS or prop == "border")`.
Confidence: high.

**STUDIO-7 · portability · `scripts/audit_design.py:213-216`** (`Finding.key`) — A
`--write-baseline` file is not portable Windows ↔ Linux/macOS: the key embeds `self.file =
str(Path(...))`, which `pathlib` renders with `\` on Windows and `/` elsewhere for the *same*
relative argument, so a baseline frozen on one OS never suppresses the same, unmodified finding
on the other. Repro (identical relative path/cwd both times):
```
# Windows:  python scripts\audit_design.py fixtures/baselinetest/components/card.css --write-baseline win.json
# WSL:      python3 scripts/audit_design.py fixtures/baselinetest/components/card.css --write-baseline linux.json
```
Observed keys: `"fixtures\\baselinetest\\components\\card.css|raw-spacing|padding: 10px;"` vs
`"fixtures/baselinetest/components/card.css|raw-spacing|padding: 10px;"` — different strings,
same violation. Fix: normalize to `/` before hashing (`self.file.replace(os.sep, "/")`).
Confidence: high.

**STUDIO-8 · crash · `scripts/generate_type_scale.py:530`** — `--preview --fluid MIN MAX`
prints a fluid step's range using a literal "→" (U+2192), not representable in cp1252. On a
plain Windows console/pipe without `PYTHONIOENCODING=utf-8` (a real terminal, a git hook, CI),
this is an uncaught crash instead of output.
Repro (`$env:PYTHONIOENCODING=$null`): `python -m scripts.generate_type_scale --preview --fluid 380 1440`
Observed: `UnicodeEncodeError: 'charmap' codec can't encode character '→' in position
2278`, traceback, exit 1. Fix: use `->`/`..` instead of `→`, or force UTF-8 / `errors="replace"`
on stdout. Confidence: high.

**STUDIO-9 · cosmetic · `scripts/audit_design.py:155`** (`COMPOUND_SEL`) — Comment says "three
or more classes compounded", but the regex (`{3,}` repeats of the group *plus* one more required
class) actually needs 4+. Repro: `<fx>\misc\nesting-id-important.css` — `.a.b.c{}` → no
compound-specificity finding; `.a.b.c.d{}` → flagged. The emitted message ("4+ classes") is
self-consistent with the code, just not with the comment/apparent intent. Confidence: medium.

## Tested and OK

- `assets/starter/styles/*` and `landing-page-conversion/assets/page-sections.css` both pass
  `audit_design.py --strict` clean, as both READMEs claim.
- L1 raw-spacing/socket-literal/raw-color/named-color(longhand)/raw-shadow/raw-radius/raw-z-index
  fire correctly on plain violations; compliant counterparts stay clean.
- L2 documented exceptions all individually verified correct: `margin: auto`, owl selector
  (`> * + *` in the parent's own rule), `calc(var(--t) * -1)` when the token name has no stray
  "-1", and a `vw` margin still correctly triggers L2 (the relational-unit exemption is L1-only).
- em-as-ratio exception correctly scoped to positioning (`top/left/…`); still flagged for
  `gap`/`margin`/`padding`.
- L4 cross-file pass: two non-module files styling the same class → both `double-owner` (shared
  property) and `scattered-component` findings; `.module.css` correctly excluded.
- L4 JSX inline-style: real visual props flagged; an all-custom-property style object
  (`style={{'--card-span': n}}`) correctly allowed.
- L3 Tailwind arbitrary values, L2 `space-x/y-*` (with/without variant prefixes), L5
  `!important`-in-class — all correct.
- L5 nesting-depth(3), ID selectors, `!important`, layer-order (out-of-order forward
  declaration), layer-statement-position (declared after a rule), unlayered-file detection — all
  correct, including that a bare `@layer a,b,c;` forward declaration alone does not put later
  rules "in" a layer (they still need `@layer name { … }`).
- `design-audit-ignore-next-line` pragma correctly suppresses only the named law on that line.
- CLI: `--law`, `--quiet` (text), `--json`, `--strict` (warnings-only → exit 0 without it, 1 with
  it), missing path → exit 2 + message, empty file → clean/exit 0, Unicode filename *and*
  content, CRLF files, and a path containing spaces — all handled with correct line numbers.
- `generate_color_ramp.py` OKLCH↔sRGB and WCAG contrast verified against an independent
  from-scratch implementation: `#000000`/`#ffffff`→21.00, `#767676`/`#ffffff`→4.54,
  `#e8440a` vs white/black, `#808080`, `#2f6df6` — all matched to displayed precision.
- `generate_type_scale.py` `--fluid` clamp() slope/intercept and the ratio ladder (exact
  `base*ratio^n`, then `--snap-px` whole-px below 32px / half-px above, computed independently
  per step rather than compounding rounded values) verified by hand — arithmetically correct.
- `--format json/ts/tailwind` for both generators produce valid JSON / plausible JS, checked via
  direct subprocess byte capture (a naive PowerShell `|`/`>` between two python.exe processes
  injects a spurious UTF-8 BOM into the *pipe*, confirmed to be a PowerShell artifact, not
  present in the scripts' own raw stdout — not reported as a bug).
- `assets/configs/eslint.design.config.mjs` and `stylelint.config.mjs` pass `node --check`;
  `tailwind.config.ts` parses cleanly as a renamed `.mts`; `pre-commit-design-gate.sh` passes
  `bash -n` under WSL.
- Every `var(--x)` used in `tokens.css`/`reset.css`/`base.css`/`layout.css`/`theme.css`/
  `page-sections.css` resolves to a real declared custom property (the one apparent miss,
  `--span` in `layout.css`, is an intentionally consumer-set inline Tier-3 socket, not a bug).
- All classes `landing-page-conversion/SKILL.md` tells users to use (`.switcher--max-3`,
  `.cover--partial`, `.center--intrinsic`, `.grid--min-xs/-sm`, `.sections--banded`,
  `.band--tight/--loose`, `.bleed-full`, `.page-grid`, `.split--2-1`) exist in `layout.css`.
- Bad-invocation handling: invalid hex/OKLCH seed, missing seed and no `--check`, unknown
  `--ratio` keyword — all exit 2 with a clear message.

## Could not test

- Real interactive-TTY color output: this harness never gives the scripts a real console, so
  `sys.stdout.isatty()` is always false — `--no-color` vs. default color could not be
  differentiated either way.
- `perf_audit.py`, `a11y_static.py` and other sibling-skill scripts mentioned in
  web-design-studio's own quick-start — out of this area's assigned scope.
- Adversarial/malformed CSS/JS beyond the documented rule set (e.g. deliberately unbalanced
  braces, pathological input sizes) — time-boxed to the documented laws and exceptions.
- Exhaustive `--canvas`/`--neutral` contrast sweeps across many seeds — spot-checked
  representative colors only (pure black/white/grey plus two saturated hues).
