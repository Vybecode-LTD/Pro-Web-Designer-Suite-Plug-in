# PY-B: web-design-studio and design-token-migration scripts

Audited 2026-10-28 at main 8441ff0. Files read in full: `plugins/pro-web-design-suite/skills/web-design-studio/scripts/audit_design.py`, `check_roles.py`, `generate_color_ramp.py`, `generate_type_scale.py`, `skills/design-token-migration/scripts/apply_codemod.py`, `cluster_values.py`, `extract_literals.py`, both SKILL.md files, `assets/rules/design-rules.json`; `assets/configs/eslint.design.config.mjs` grepped for the Tailwind patterns only. Tests consulted: `tests/test_audit_design.py`, `test_check_roles.py`, `test_token_migration.py`, `test_rules_spec.py` (grepped for the cases below). Commands run (every probe in the scratchpad `…\scratchpad\py-b\`, each with `python -B`): `audit_design.py src --no-color --quiet` on four probe trees (a, h, i and the Vue one); `check_roles.py tokens.css` and `--json` on a dark theme written as `@media (prefers-color-scheme: dark)` and `html[data-theme="dark"]`; `apply_codemod.py src -m mapping.json` (dry run, with and without `--no-diff`) on three hand-written mappings; `extract_literals.py src/b.css --format csv`; `cluster_values.py literals.json -o proposal`, `--dry-run --accent blurple`, `--tokens tokens.json -o .` and `--tokens tokens.css -o .`; `generate_type_scale.py --base 18 --ratio 1.25 --steps-down 1 --steps-up 2 --snap-px --preview`; `generate_color_ramp.py --check` with `oklch(50% 0.1 20 / 1)`, `oklch(50% none 20)` and `rgb(0 0 0)`; grep for 3.10-only syntax (none).

## Summary

26 findings: 1 critical, 4 high, 10 medium, 11 low. By class (counted from the headings): bug 14, gap 4, inconsistency 4, risk 3, dead-code 1. Every finding marked confirmed was reproduced with a command in the scratchpad; the rest are from reading.

The three that matter most: (1) `cluster_values.py --tokens tokens.json -o <that folder>` overwrites the project's own DTCG token file, because the overwrite guard names three outputs and the script writes four (PY-B-1). (2) The codemod turns `transition: opacity ease 200ms` into `opacity ease var(--motion-hover)`, which expands to two timing functions and is a transition the browser drops, and `cluster_z` maps z-index 1, 2, 3 and 10 all to `--z-raised` while its notes say "rank 1 of 4" to "rank 4 of 4" (PY-B-2, PY-B-3). (3) The design gate never reports a stylesheet as unlayered when its top-level rules are `:root`, `:where(body)` or `:is(…)`, because a pseudo-class-only selector counts as depth 0 at the top level too, which also under-counts nesting by one beneath it (PY-B-4).

## Findings

### PY-B-1 · critical · risk

- **Where:** `plugins/pro-web-design-suite/skills/design-token-migration/scripts/cluster_values.py:2858` and `:2974`
- **What:** The overwrite guard checks `tokens.css`, `mapping.json` and `reconciliation.md` against the inputs, but the script also writes `tokens.json` (added with P31), which it never checks. With `--tokens tokens.json` (a DTCG file, which `read_tokens` accepts) and `-o` pointing at that file's folder, the input is replaced by the proposal.
- **Evidence:** Line 2858 `for dest in ("tokens.css", "mapping.json", "reconciliation.md"):`; line 2974 `(out / "tokens.json").write_text(...)`. Probe `f/`: a DTCG `tokens.json` passed as `--tokens tokens.json -o .` → exit 0, `cmp` reports OVERWRITTEN, the file now starts `"$description": "cluster_values.py's proposal…"`. The same run with `--tokens tokens.css -o .` is refused: "tokens.css is the input tokens.css: writing there would replace it."
- **Effect:** A project that keeps its tokens in DTCG loses its token file (git recovers it, an uncommitted edit does not), with no message.
- **Fix:** Add `"tokens.json"` to the guarded names at line 2858; regression test: `--tokens tokens.json -o .` must exit 2 and leave the file byte-identical.
- **Confidence:** confirmed

### PY-B-2 · high · bug

- **Where:** `plugins/pro-web-design-suite/skills/design-token-migration/scripts/apply_codemod.py:740-742`
- **What:** `plan_motion` replaces the span from the duration to the last easing *after* it; an easing written before the duration (`transition: opacity ease 200ms`, which CSS allows in any order) survives beside the inserted `--motion-*` pair. The pair carries its own easing (`--motion-hover: var(--dur-fast) var(--ease-out)`), so the declaration becomes `opacity ease 150ms ease-out`: two timing functions, which is invalid, and the browser drops the whole transition.
- **Evidence:** `span_end = max([times[0].end] + [e.end for e in easings if e.start > times[0].start])`. Probe `c/`: `.a { transition: opacity ease 200ms; }` with a motion rule for 200ms → diff `+.a { transition: opacity ease var(--motion-hover); }`, counted as "duration x1", exit 0.
- **Effect:** A silently broken transition in every rule that wrote the easing first; the reconciliation marks pair rules `review`, but the diff looks right at a glance.
- **Fix:** Take the span from the earliest of the duration and any easing to the latest of them (`min(starts)`, `max(ends)`), or leave a layer with an easing before its duration to the per-slot pass. Needs a regression test with the easing in each position.
- **Confidence:** confirmed

### PY-B-3 · high · bug

- **Where:** `plugins/pro-web-design-suite/skills/design-token-migration/scripts/cluster_values.py:1743-1750`
- **What:** `cluster_z` picks a rung by magnitude band, then "enforces rank order" with a backward pass that can only *lower* an earlier value's rung (`assigned[i - 1] = max(0, assigned[i] - 1)`). Values in the same band therefore collapse onto one rung instead of being spread upward, and the docstring's promise that "no two values swap places" fails: distinct z-indexes become equal, so DOM order decides what they used to decide.
- **Evidence:** Probe `e/`: literals z-index 1, 2, 3, 10 → mapping rules `z-001 ['1'] -> var(--z-raised)`, `z-002 ['2'] -> var(--z-raised)`, `z-003 ['3'] -> var(--z-raised)`, `z-004 ['10'] -> var(--z-raised)`, each noted "rank n of 4. Confirm against the real stacking order". `tests/test_token_migration.py:434-440` only checks the note's wording, never that distinct values get distinct rungs.
- **Effect:** A legacy codebase's `z-index: 1 / 2 / 5 / 10` ladder (the common one) is flattened; a sticky header and a raised card end on the same rung.
- **Fix:** After banding, walk forward and raise each value to at least the previous rung + 1 while rungs remain (collapse only when values outnumber rungs, which the note already covers), and say in the note when two values share a rung. Regression test: 1, 2, 3 → three distinct rungs.
- **Confidence:** confirmed

### PY-B-4 · high · bug

- **Where:** `plugins/pro-web-design-suite/skills/web-design-studio/scripts/audit_design.py:318-322`, `:671-676`, `:1281`, `:1330`, `:1332`
- **What:** `rule_depth()` skips every selector that `pseudo_classes_only` accepts, meant for a nested `:hover`, but it is applied at the top level too. A top-level `:root {…}`, `:where(body) {…}` or `:is(.a, .b) {…}` therefore opens at depth 0, so the `depth == 1` test at line 1330 never records it as the first unlayered rule, nesting below it is counted one short (line 1281), and a mixin holding only such a rule is not an emitting mixin (line 1332).
- **Evidence:** Probe `a/`: `src/styles/base.css` = `:where(body) { margin: 0; … }` + `:root { --page-bg: … }` with no `@layer` → no finding at all, while `src/styles/layout.css` = `.stack { padding: 0; }` → `L5 unlayered`. Probe `h/`: inside `@layer base`, `:root { & .a { & .b { & .c { & .d {…} } } } }` reports one `nesting-depth 3`; the same chain under `.x` reports `nesting-depth 3` and `4`. `tests/test_audit_design.py` has no top-level pseudo-only case.
- **Effect:** A base stylesheet written the way the starter writes it (`:where()` everywhere) passes Law 5 with no `@layer` at all; nesting past the cap hides one level deeper under `:root`.
- **Fix:** Exempt pseudo-class-only selectors from the depth count only when they are nested (`len(sel_stack) > 1` at the time of the push), or count the top-level rule always. Regression tests: an unlayered `:where(body)` file fails `unlayered`; `:root` nesting counts like `.x` nesting.
- **Confidence:** confirmed

### PY-B-5 · high · bug

- **Where:** `plugins/pro-web-design-suite/skills/design-token-migration/scripts/extract_literals.py:1001` and `:464-501`; `plugins/pro-web-design-suite/skills/design-token-migration/scripts/apply_codemod.py:618`, `:663`, `:674`
- **What:** Both scripts scan the comment-blanked text to find declarations, then read the value back from the *real* text (`value = text[d.value_offset:d.value_offset + len(d.value)]`) and pass it through `mask_strings_and_urls`, which masks strings and `url()` but not comments. A comment inside a value, before its last slot, is counted by the census and rewritten by the codemod; both docstrings say comments are untouched. The extra comment words also inflate the slot count, so `padding` sides are misfiled.
- **Evidence:** Probe `c/src/b.css`: `.b { padding: 16px /* was 12px */ 8px; }` and `.e { margin: 0 /* 12px */ auto; }`. Census CSV lists `12px` twice (cols 27 and 19, both `css-decl`) and files all three padding values under `padding` (six slots, not two). Codemod diff: `padding: var(--pad-card) /* was var(--pad-sm) */ 8px;` and `margin: 0 /* var(--pad-sm) */ auto;`. A comment at the end of the value (`16px /* was 12px */;`) is safe, because `d.value` is stripped before its length is taken.
- **Effect:** The headline numbers a client is shown count annotations; the codemod edits comments and, with a comment between slots, misreads which side a padding sets.
- **Fix:** Read the value from the blanked text (or blank comments in `value` with the same offsets before masking) in `extract_css`, `extract_js`'s styled bodies, `plan_css` and `padding_rules`; regression tests for the census count and the codemod diff with a comment between slots.
- **Confidence:** confirmed

### PY-B-6 · medium · bug

- **Where:** `plugins/pro-web-design-suite/skills/design-token-migration/scripts/apply_codemod.py:1200-1232`
- **What:** The exit code is `1 if any(r.skipped for r in results) or line_skips else 0`. A skip that `process()` records with line 0 (a file whose rewrite failed the safety check, whose planning raised, that is generated, or unreadable) returns `None`, so it is in neither `results` nor `line_skips`: it is printed under "left alone" and the run exits 0. The docstring (line 56) and SKILL.md ("1 something was skipped") promise 1.
- **Evidence:** Probe `d/`: a mapping whose replacement holds `;` → "1 file(s) were left alone: src/a.css rewrite failed its safety check (`;` count changed 1 -> 2) — file left untouched", `exit=0`.
- **Effect:** A CI step or the batch loop SKILL.md warns about reads a refused rewrite as clean.
- **Fix:** Return 1 when `file_skips` is non-empty too (keep generated files out of it if that is meant to be quiet). Regression test on the exit code.
- **Confidence:** confirmed

### PY-B-7 · medium · gap

- **Where:** `plugins/pro-web-design-suite/skills/web-design-studio/scripts/check_roles.py:69-74`, `:154-156`, `:189-191`
- **What:** A scope is the blocks whose selector list holds exactly `:root`, `[data-theme="dark"]`, `.inverse` or `[data-theme="dark"] .inverse`. When no block matches a scope's own selector (the dark theme lives in `@media (prefers-color-scheme: dark)`, which `rules()` excludes by design and `tests/test_check_roles.py:310` pins, or in `html[data-theme="dark"]`, `.dark`, `[data-theme=dark]`), the scope silently equals its parent and every dark pair is measured on the light colours.
- **Evidence:** Probe `b/tokens.css`: dark surfaces `#111` with `--fg-default: #222` written both as a media query and as `html[data-theme="dark"]` → "role pairs: 82 of 100 pass", the 45 `"scope": "dark"` results all carry the light values, nothing says the dark theme was not read.
- **Effect:** A project with a dark theme the gate cannot see gets a passing dark column; SKILL.md says the gate "resolves every Tier-2 role in light, dark and `.inverse`".
- **Fix:** When a scope's own selectors match no block, say so on stderr (or exit 2, as an unresolvable role does) instead of inheriting; optionally read `@media (prefers-color-scheme: dark) { :root {…} }` as the dark scope. Regression test: a tokens.css with no `[data-theme="dark"]` block warns.
- **Confidence:** confirmed

### PY-B-8 · medium · inconsistency

- **Where:** `plugins/pro-web-design-suite/skills/web-design-studio/scripts/audit_design.py:1603`
- **What:** z-index is the one family checked by hand rather than through `off_family`: `"var(--" not in value and value.strip() not in ("0", "auto")`. The spec (`design-rules.json` stacking: `VAR_ONE, 0, auto, KEYWORDS`) allows the CSS-wide keywords, and `sass.variables` says a Sass reference is read as a token; the audit refuses both, and stylelint does not.
- **Evidence:** Probe `a/`: `.card { z-index: inherit; }`, `.card2 { z-index: unset; }` and, in `card.scss`, `.card { z-index: $z-modal; }` → three `L1 raw-z-index … is a literal` errors.
- **Effect:** The two gates disagree; `z-index: unset` (how a component drops a stacking context) fails the audit only.
- **Fix:** Route z-index through `off_family` with a `(VAR_ONE, "0", "auto", *KEYWORDS)` tuple generated by `sync_rules.py`; add the keyword and `$var` cases to the conformance examples.
- **Confidence:** confirmed

### PY-B-9 · medium · inconsistency

- **Where:** `plugins/pro-web-design-suite/skills/web-design-studio/scripts/audit_design.py:445`, `:464-466`
- **What:** `TW_ARBITRARY` matches the longest `name-[…]` and `TW_ARBITRARY_OK` whitelists only a variant whose *first* word is `data|aria|group|peer|…`, so the compound arbitrary variants `group-data-[state=open]:`, `peer-aria-[checked=true]:`, `group-has-[…]:` are reported as arbitrary values. ESLint's pattern (`eslint.design.config.mjs:102`, `(?!(?:data|aria|group|peer|…)\b)`) refuses to start a match at `group`, so it allows them.
- **Evidence:** Probe `a/src/components/Card.jsx`: `className="group-data-[state=open]:bg-surface peer-aria-[checked=true]:p-card"` → `L3 tw-arbitrary group-data-[state=open]` and `peer-aria-[checked=true]`.
- **Effect:** A class the spec calls a state variant fails the audit and passes ESLint.
- **Fix:** Make `TW_ARBITRARY_OK` accept a variant prefix before the arbitrary part (`^(?:group|peer)-(?:data|aria|has|…)-\[`), or test the token's first segment as ESLint does; add the two classes to `tailwind_arbitrary.allowed`.
- **Confidence:** confirmed

### PY-B-10 · medium · bug

- **Where:** `plugins/pro-web-design-suite/skills/web-design-studio/scripts/audit_design.py:1521-1522`
- **What:** The system-colour check splits the raw `value`, not `strip_var_refs(value)`, so a system colour inside a `var()` fallback is reported, against `var_fallback` ("a var() fallback is not checked").
- **Evidence:** Probe `a/`: `.card3 { color: var(--fg-strong, CanvasText); }` → `L1 system-color CanvasText is a CSS system colour, outside @media (forced-colors: active)`.
- **Effect:** A forced-colours fallback written the way the rule invites fails.
- **Fix:** Split `strip_var_refs(value)` at line 1522; add `color: var(--fg-strong, CanvasText)` to `system_colors.allowed`.
- **Confidence:** confirmed

### PY-B-11 · medium · gap

- **Where:** `plugins/pro-web-design-suite/skills/web-design-studio/scripts/audit_design.py:460` (`CLASS_ATTR`)
- **What:** `CLASS_ATTR` captures ``[^"'`]*`` after the opening quote, so a Vue `:class="{ 'p-[17px]': on }"` object yields `{ ` and nothing is audited; the census's `CLASSNAME_RE` (`extract_literals.py:264-267`) captures to the matching quote and counts every arbitrary value inside, and the codemod rewrites them. ESLint parses no `.vue`, so these classes have no gate.
- **Evidence:** Probe `i/src/components/Card.vue`: `:class="{ 'p-[17px]': on, 'bg-[#e8440a]': hot }" class="p-[13px]"` → the audit reports 1 `tw-arbitrary` (`p-[13px]`); the census lists all three as `tailwind-arbitrary`.
- **Effect:** Arbitrary values and literal colours in Vue's bound class objects pass Law 1 and 3.
- **Fix:** Match the attribute's value to its own closing quote (as `CLASSNAME_RE` does) and run the Tailwind checks on the quoted strings inside it; test with the probe file.
- **Confidence:** confirmed

### PY-B-12 · medium · bug

- **Where:** `plugins/pro-web-design-suite/skills/design-token-migration/scripts/cluster_values.py:1926-1927`, `:2846-2854`
- **What:** `--accent` is parsed with `parse_any_color`, whose `ColorError` nothing catches (`main` catches only `ConfigError`), so a bad seed is a traceback, not the exit-2 message the docstring promises for a bad invocation.
- **Evidence:** `cluster_values.py literals.json --dry-run --accent blurple` → `File "...cluster_values.py", line 295, in parse_any_color … ColorError: cannot parse color 'blurple'`.
- **Effect:** A typo in the brand hex looks like a crash in the tool.
- **Fix:** Validate `args.accent` in `main` and print `cluster_values: --accent …: cannot parse color`, return 2; one test.
- **Confidence:** confirmed

### PY-B-13 · medium · risk

- **Where:** `plugins/pro-web-design-suite/skills/web-design-studio/scripts/audit_design.py:2748-2752`, `:3019-3021`
- **What:** A rule that raises while auditing a file becomes one `internal-error` finding of severity `warning` ("a crashed rule must never block a commit"), and warnings fail only with `--strict`. So a file the audit could not parse passes the default gate, and the pre-commit hook SKILL.md prescribes (`audit_design src/`, no `--strict`) lets it through.
- **Evidence:** The `except Exception` at 2748 and `failing = [f for f in findings if f.severity == "error" or (args.strict and …)]` at 3019.
- **Effect:** A parser crash on one file is a silent pass for that file; the deliberate choice is documented only in a code comment.
- **Fix:** Either make `internal-error` an error (the file was not audited, which is the one thing Law 9 forbids), or say in SKILL.md that the hook must run `--strict`. No test needed beyond the severity assertion.
- **Confidence:** confirmed (by reading; the behaviour is explicit)

### PY-B-14 · medium · gap

- **Where:** `plugins/pro-web-design-suite/skills/web-design-studio/scripts/generate_color_ramp.py:254-257`, `:300-327`; `check_roles.py:285-294`
- **What:** `parse_color` reads a hex and `oklch(L C H)` only. Valid spellings of the same colour (`oklch(50% 0.1 20 / 1)`, `oklch(50% none 20)`, a chroma in `%`) and `rgb()`/`hsl()` are "Cannot parse", so `check_roles` exits 2 on a tokens.css that writes a ramp in rgb() or hsl(), while `cluster_values.parse_any_color` reads those. The docstrings say hex or oklch, but SKILL.md calls `check_roles` "the palette's gate" for any `tokens.css`.
- **Evidence:** `generate_color_ramp.py --check "oklch(50% 0.1 20 / 1)" "#ffffff"`, `… "oklch(50% none 20)" …`, `… "rgb(0 0 0)" …` → each `error: Cannot parse …`.
- **Effect:** A project whose tokens are not hex/oklch cannot run the role-pair gate at all (exit 2), and `--check` refuses CSS a browser accepts.
- **Fix:** Share `cluster_values.parse_any_color` (extended with `none` and `/ alpha` for oklch) across the three scripts, or at least accept `/ 1` and `none` in `_OKLCH_RE`; tests for each spelling.
- **Confidence:** confirmed

### PY-B-15 · medium · bug

- **Where:** `plugins/pro-web-design-suite/skills/design-token-migration/scripts/cluster_values.py:2878`, `:597`, `:1476`
- **What:** Strokes snap with tolerance `0.5` and `snap_to_scale` refuses only when `best_d > tolerance`, so a `0.5px` hairline (the retina hairline idiom) is exactly at the limit and snaps to `--stroke-default` (1px) with confidence `snapped`, since the review threshold is a 2px delta.
- **Evidence:** Probe `j/`: a single `border-width: 0.5px` literal → rule `(['0.5px'], 'var(--stroke-default)', 'snapped', 0.5)`; nothing in the reconciliation's review table.
- **Effect:** Every hairline border doubles, below the review threshold.
- **Fix:** Refuse at `>=` for the stroke scale, or mark a relative move over 25% as `review`; one test for `0.5px`.
- **Confidence:** confirmed

### PY-B-16 · low · inconsistency

- **Where:** `plugins/pro-web-design-suite/skills/web-design-studio/scripts/audit_design.py:1543-1565`, `:1532-1540` vs `design-rules.json:328`, `:375`
- **What:** The type family is checked by literal shape only, so `font-weight: bold`, `line-height: normal` and `font-family: Georgia, serif` pass the audit while the spec's allowlist (`VAR_ONE, KEYWORDS`) refuses them in stylelint; `box-shadow: inset 0 0 0 var(--stroke-default) var(--border-default)` passes the audit (no literal length or colour) while the spec allows `VAR_ONE, none, KEYWORDS` only.
- **Evidence:** Probe `a/`: `.card4` and `.card5` draw no finding.
- **Effect:** The two gates disagree on these declarations.
- **Fix:** Read the type and elevation allowlists through `off_family` as the spacing, stroke, motion and sizing families are, or state in `values.rule` that the audit reads literals only for these two.
- **Confidence:** confirmed

### PY-B-17 · low · bug

- **Where:** `plugins/pro-web-design-suite/skills/web-design-studio/scripts/audit_design.py:450-452` (`TW_LITERAL`), same regex in `eslint.design.config.mjs:147`
- **What:** `z-0`, `border-0`, `duration-0`, `ring-0`, `outline-0` are reported as literal values, though 0 is on every allowlist the spec writes (`zero`, `stacking`, `stroke`, `motion`'s `0s`).
- **Evidence:** Probe `a/`: `className="z-0 border-0 duration-0"` → three `L1 tw-literal`.
- **Effect:** `border-0` (the usual way to drop a border in Tailwind) fails both gates.
- **Fix:** Exclude `-0(?:\.0+)?` in both regexes; add `border-0` to a conformance example.
- **Confidence:** confirmed

### PY-B-18 · low · bug

- **Where:** `plugins/pro-web-design-suite/skills/web-design-studio/scripts/audit_design.py:434-437` with `:1059-1069`; `:1777-1783`
- **What:** `raw_colour` removes `url()` and `var()` but not quoted strings, so a named colour inside a string is a finding; and the JS hex check takes any 3-to-8-hex-digit id string for a colour unless the line mentions `href|id|anchor|hash|sha|commit`.
- **Evidence:** Probe `a/`: `.card6 { background: image-set("gold.png" 1x); }` → `L1 named-color`; `document.querySelector('#add')` → `L1 js-raw-color Hardcoded colour #add in JS` (warning).
- **Effect:** False positives in image-set() and in selector strings.
- **Fix:** Blank strings in `raw_colour` (as `SASS_STRING.sub` already does for `!important`); skip a JS hex that is also a plausible id when the line holds `querySelector`/`getElement`. Low priority.
- **Confidence:** confirmed

### PY-B-19 · low · bug

- **Where:** `plugins/pro-web-design-suite/skills/web-design-studio/scripts/generate_type_scale.py:382`
- **What:** `snap_to_px` uses Python's `round()`, which rounds halves to even: 22.5 → 22, 23.5 → 24. The docstring says "nearest", and JavaScript's `Math.round` (what a designer checks with) gives 23.
- **Evidence:** `--base 18 --ratio 1.25 --steps-down 1 --steps-up 2 --snap-px --preview` → `--text-lg 1.375rem 22`; `python -c "print(round(22.5), round(23.5))"` → `22 24`.
- **Effect:** A half-pixel step rounds down or up depending on parity.
- **Fix:** `math.floor(px + 0.5)`; one test with base 18.
- **Confidence:** confirmed

### PY-B-20 · low · bug

- **Where:** `plugins/pro-web-design-suite/skills/web-design-studio/scripts/check_roles.py:340`, `:421`
- **What:** `ok` compares the unrounded ratio (`ratio + 1e-9 >= min`) but the report prints `round(ratio, 2)`, so a pair at 4.4996:1 prints "FAIL … 4.50:1, needs 4.5:1".
- **Evidence:** `"ratio": round(ratio, 2), … "ok": ratio + 1e-9 >= pair["min"]`.
- **Effect:** A confusing line in the rare case; the verdict itself is right.
- **Fix:** Print three decimals, or print the unrounded value in the FAIL line.
- **Confidence:** likely (by reading)

### PY-B-21 · low · dead-code

- **Where and what (each verified by grep across the plugin and `tests/`):**
  - `audit_design.py:1217`, `:1345` — `declared_props` is filled and never read.
  - `audit_design.py:2654-2656` — `iter_files()` has no caller (every caller uses `iter_files_with_roots`; the `a11y_static.py`, `deprecate.py`, `perf_audit.py` hits are their own functions).
  - `audit_design.py:620` — `start_line` is assigned in the block-comment branch and unused there (only the `//` branch uses it).
  - `apply_codemod.py:111-112` — `INT_RE` and `FUNC_HEAD_RE` are defined and never used.
  - `apply_codemod.py:619-624` — `tail` is computed, then `del tail`.
  - `cluster_values.py:571-580` — the `Snap` dataclass is never instantiated (`snap_to_scale` returns a tuple).
  - `cluster_values.py:1163` — `kind_label` parameter of `cluster_spacing` is never passed or read (ruff ARG001).
  - `extract_literals.py:243-248` — `KEYWORD_OK` is defined and never used.
  - `extract_literals.py:587` — `flush_decl(end)` ignores `end` (ruff ARG001).
- **Effect:** Maintenance noise only.
- **Fix:** Delete them; no test.
- **Confidence:** confirmed

### PY-B-22 · low · bug

- **Where:** `plugins/pro-web-design-suite/skills/web-design-studio/scripts/audit_design.py:2729-2731`
- **What:** `except OSError: continue` drops a file the audit cannot read from the audited count and from the skipped list, so the run reports nothing about it.
- **Evidence:** The bare `continue` with no `skipped.append`.
- **Effect:** A permission error on one stylesheet is invisible; with only such files in a folder the run says "0 files audited" with no reason.
- **Fix:** Append `(fp, f"unreadable: {exc.strerror}")` to `skipped`.
- **Confidence:** confirmed (by reading)

### PY-B-23 · low · risk

- **Where:** `plugins/pro-web-design-suite/skills/design-token-migration/scripts/apply_codemod.py:1122`
- **What:** `git_root(Path(args.paths[0]))` reads the dirty set of the first path's repository only; a second path in another repository (or outside any) is treated as clean, and the "not a git repository" warning is only printed when the first path has no repo.
- **Evidence:** `root = git_root(Path(args.paths[0]))`.
- **Effect:** The uncommitted-changes guard SKILL.md calls load-bearing does not cover a multi-repo invocation.
- **Fix:** Compute the root per path (cache by folder) or refuse paths from more than one repository.
- **Confidence:** likely

### PY-B-24 · low · bug

- **Where:** `plugins/pro-web-design-suite/skills/design-token-migration/scripts/apply_codemod.py:295-314` vs `:638`, `:646`, `:691`
- **What:** `rules_problem` validates `kind`, `replacement`, `match`, `props`, `prop_classes` and `scope`, but `plan_css` reads `rule["id"]` and `drule["token"]` unchecked; a hand-edited mapping missing either raises `KeyError`, which `process()` turns into "planning failed … file left untouched" — and, with PY-B-6, exit 0.
- **Evidence:** The two accessor lines and the `except Exception` at 1015.
- **Effect:** A mapping edit by hand (which SKILL.md invites: "edit it, commit it") fails per file with a Python key name instead of a schema message at load time.
- **Fix:** Add `id` and `token` to `rules_problem`'s required strings.
- **Confidence:** confirmed (by reading)

### PY-B-25 · low · inconsistency

- **Where:** `plugins/pro-web-design-suite/skills/design-token-migration/scripts/extract_literals.py:1726` vs `plugins/pro-web-design-suite/skills/web-design-studio/scripts/audit_design.py:791-796`, `:1491`, `:1971`
- **What:** The census treats every `.jsx`/`.tsx` file as a component ("a component by definition"); the audit treats a file as a component only by path (`components/`, `ui/`, `.module.`). A styled-components body in `src/pages/Home.tsx` is audited inside a synthetic `@layer components`, so Law 6 applies, but `component_file` is false, so Law 2 (`child-margin`, `foreign-selector`) does not.
- **Evidence:** The three locations above.
- **Effect:** A child margin in a styled template outside `components/` passes the audit while the census counts it as a component literal.
- **Fix:** Decide one rule (the census's is simpler) and apply it in `is_component_file` for JS files, or document the difference in `file_classes`.
- **Confidence:** likely

### PY-B-26 · low · gap

- **Where:** `plugins/pro-web-design-suite/skills/design-token-migration/SKILL.md:215`, `:250-258`
- **What:** The `extract_literals` flag table lists twelve `--kind` values and omits `other-length` (`KIND_ORDER`, `extract_literals.py:2323-2325`, which the report prints as its own section); the `apply_codemod` table omits `--include-vendor` (`apply_codemod.py:1091`). Both are in `--help`.
- **Evidence:** The lines cited.
- **Effect:** Documentation only.
- **Fix:** Add the two entries.
- **Confidence:** confirmed

## Static-analysis candidates, resolved

- `apply_codemod.py:780` ARG005 (`sm` unused in `class_list=lambda sm: True`) — fine-by-design: the default predicate must take the match the real one (`in_class_list`) takes.
- `apply_codemod.py:894` and `:912` PLW1510 (`subprocess.run` without `check`) — fine-by-design: `returncode` is read by hand and a failure must become `None`, which `check=True` would turn into an exception.
- `cluster_values.py:480` PIE810 — harmless style (`startswith(("$", "@", "--"))` would be shorter).
- `cluster_values.py:1163` ARG001 (`kind_label`) — dead parameter, PY-B-21.
- `extract_literals.py:528`, `:593`, `:903`, `:1609` PIE810 — harmless style.
- `extract_literals.py:587` ARG001 (`end` in `flush_decl`) — dead parameter, PY-B-21.
- `extract_literals.py:1564` and `:1565` ARG005 (`claimed=lambda pos: False`, `class_list=lambda sm: True`) — fine-by-design, default predicates.
- `generate_type_scale.py:687` PLW3301 (nested `max`) — harmless; `rows` is never empty because `main` refuses a one-step scale (line 860), so the inner `max` cannot raise.

## What is covered well

The CSS scanner's hard cases are handled and tested: `url()` with `//`, Sass `#{…}` interpolation, strings with escaped quotes, `@layer` sub-layer paths, `@import … layer()` ordering, the BOM and UTF-16 (`json.detect_encoding`), and selector specificity as `@csstools/selector-specificity` computes it, including `:where()`, `:is()`, `:has()`, `:nth-child(… of S)` and `&`. The codemod's write path is careful: bytes are read and written in the file's own encoding and line endings, edits are spliced from the end so offsets hold, overlaps are refused, a temp file in the same folder is fsynced and `os.replace`d with the mode copied, and the dirty-file guard parses `git status -z` with renames. `cluster_values` keeps the scale closed and reports what does not fit rather than widening it, measures contrast per role against the surface it lands on, and refuses to land on project ramp steps the contract does not name. The colour maths (OKLab matrices, the sRGB-to-P3 matrix, gamut mapping by chroma reduction, `worst_contrast` over both sRGB fallbacks) is correct and the two copies agree. No Python 3.10-only syntax is used; `from __future__ import annotations` covers every `X | None` annotation on 3.9.
