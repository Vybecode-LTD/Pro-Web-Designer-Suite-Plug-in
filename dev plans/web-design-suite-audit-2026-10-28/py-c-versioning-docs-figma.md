# PY-C: design-system-versioning, design-system-docs and figma-variables-sync scripts

Audited 2026-10-28 at main 8441ff0. Files read in full: `skills/design-system-versioning/scripts/deprecate.py`, `skills/design-system-versioning/scripts/diff_system.py`, `skills/design-system-docs/scripts/build_docs.py`, `skills/design-system-docs/scripts/extract_system.py`, `skills/figma-variables-sync/scripts/figma_audit.py`, `skills/figma-variables-sync/scripts/figma_common.py`, `skills/figma-variables-sync/scripts/figma_to_tokens.py`; the three skills' `SKILL.md` and `references/scripts.md`; the relevant parts of `references/deprecation.md`, `references/figma-mapping.md`, `web-design-studio/assets/starter/styles/tokens.css`, `web-design-studio/scripts/generate_color_ramp.py` (`parse_color`, `ColorError`) and `design-token-migration/scripts/apply_codemod.py` (`--kind`). Tests consulted: `tests/test_docs.py`, `tests/test_versioning.py`, `tests/test_figma_sync.py`, `tests/fixtures/worked-release.json` (grep for coverage of each case). Commands run (all read-only against fixtures in the session scratchpad, `scratchpad/py-c/`): `extract_system.py --tokens <starter tokens.css>`, `extract_system.py --tokens <fixture>` ×4, `extract_system.py <dir under build/>`, `extract_system.py --out X --contract X`, `diff_system.py OLD NEW` (report, json, changelog, migration-guide; with/without `--no-upstream`, `--deprecations`, `--color-impl`) ×8, `deprecate.py add` ×3 (`--dry-run`, with `--mapping`, with `--mapping` = `--source`), `deprecate.py scan` ×2, `deprecate.py status` ×2, `build_docs.py --check --prose`, `figma_audit.py` ×2, `figma_to_tokens.py` ×4, and small in-process Python checks of `as_ms`, `contrast_ratio_oklch` and the starter's `system.json`. Scope exclusions honoured: `project_config.py` and `dtcg.py` copies were only read where a call site depends on them.

## Summary

26 findings: 1 critical, 7 high, 8 medium, 10 low. By class (counted from the headings): bug 15, gap 4, inconsistency 4, risk 2, compat 1. The three that matter most:

1. **Both extractors read `[data-theme="dark"] .inverse { … }` as the dark theme's own override** and, because the last override wins, the starter's own dark theme resolves `--fg-default` to neutral-900 on a neutral-1000 canvas: the generated docs measure the starter's dark text at 1.14:1, and `diff_system` diffs the wrong dark values (PY-C-1).
2. **A bare number is read as a hex colour** (`600` → `#660000`): every `--weight-*` and `--z-*` token in the starter is `kind: color` with a swatch in the docs, and the diff reports a weight change as `#660000 -> #770000` (PY-C-2).
3. **Three silent gate failures around deprecation**: the migration guide tells every consumer to run `apply_codemod … --kind color` even for a spacing rename, which `apply_codemod` refuses (PY-C-5); `deprecate scan` silently merges two consumers whose folders share a basename, so the ledger's evidence undercounts (PY-C-6); and `deprecate add --mapping` writes over a `--source` file without the `refuse_overwrite` check the rest of the suite uses (PY-C-7).

## Findings

### PY-C-1 · critical · bug

- **Where:** `plugins/pro-web-design-suite/skills/design-system-docs/scripts/extract_system.py:1061-1065` (`context_of`) and `:1631-1637` (theme environments); the same logic in `plugins/pro-web-design-suite/skills/design-system-versioning/scripts/diff_system.py:461-466` (`context()`) and `:968-974` (`_resolve_snapshot`).
- **What:** `context_of` runs `THEME_SEL.search` over the whole joined selector, so a theme-scoped re-point such as `[data-theme="dark"] .inverse { --fg-default: var(--neutral-900) }` is filed as a `("theme", "dark")` override of `--fg-default`. The theme environment is built with "last override wins", and in the starter the `.inverse` block comes after the `[data-theme="dark"]` block, so the inverse band's values replace the dark theme's.
- **Evidence:** `extract_system.py --tokens web-design-studio/assets/starter/styles/tokens.css` → `--fg-default` resolved dark `#171512` (neutral-900) with overrides `[('theme','dark','[data-theme="dark"]','var(--neutral-100)'), ('scoped','.inverse',…), ('theme','dark','[data-theme="dark"] .inverse','var(--neutral-900)')]`; its dark contrast rows: `--bg-canvas 1.14`, `--bg-surface 1.10`, `--bg-raised 1.0`; `--fg-muted` dark `3.11 / 3.01 / 2.74`. The same selector reaches `diff_system`'s vendored parser through `THEME_SEL.search(sel)` at `:463`.
- **Effect:** The token reference and contrast table of a docs site built from the starter say the dark theme fails AA on every role `.inverse` re-points (`--fg-default`, `--fg-strong`, `--fg-muted`, `--fg-subtle`, `--fg-accent`, `--fg-link`, three `--border-*`); a committed `docs/system.json` baseline carries the wrong numbers; `diff_system` measures dark contrast deltas and `moves_elsewhere` against the inverse values. No test asserts a dark ratio on the starter, which is why 4.0.1 passes.
- **Fix:** Treat a selector as a theme or density context only when the `[data-theme=…]`/`[data-density=…]` compound is the whole selector (optionally preceded by `:root`/`html`), i.e. match the last compound and require no combinator after it; anything else is `scoped`. One regex change in each script. Regression test: the starter's `--fg-default` resolves to neutral-100 in dark and measures above 15:1 on `--bg-canvas` dark; fails on v4.0.1.
- **Confidence:** confirmed

### PY-C-2 · high · bug

- **Where:** `plugins/pro-web-design-suite/skills/design-system-docs/scripts/extract_system.py:165` (`_HEX_RE` makes `#` optional), `:1027` (`guess_kind` → `"color"`), `:899-908` (the hex branch of `resolve_value`); `plugins/pro-web-design-suite/skills/design-system-versioning/scripts/diff_system.py:194`, `:653-666` (`resolve_display`).
- **What:** A value of three, four, six or eight hex digits with no `#` is parsed as a colour. `600`, `700`, `400`, `100`, `1000` all qualify.
- **Evidence:** Starter extraction: `--weight-semibold kind=color display=#660000`, `--weight-regular #440000`, `--z-sticky #110000`, `--z-toast #550000`. `diff_system OLD NEW` with `--weight-semibold: 600 → 700`: `[tier1-value-changed] --weight-semibold  value #660000 -> #770000  detail 600 -> 700` (both with and without `--no-upstream`).
- **Effect:** The docs token table shows a swatch and a hex "resolved" value for every weight and z-index token; `system.json` records `kind: color`; `contract_of` (`extract_system.py:1993`) files any `--<name>-<digits>` token of kind color as a ramp step, so a numeric-step scale like `--z-100: 100` would land in `ramps`; the changelog and migration guide quote `#660000 → #770000` for a weight change.
- **Fix:** In both resolvers require the leading `#` (`text.startswith("#")` before the hex branch, and in `guess_kind`), keeping the lenient form for `parse_color`'s CLI use only. Regression test: `--weight-semibold: 600` → `kind: number`, display `600`, no `hex`.
- **Confidence:** confirmed

### PY-C-3 · high · bug

- **Where:** `plugins/pro-web-design-suite/skills/design-system-docs/scripts/extract_system.py:1734` (`compute_contrast`, no handler) and `:896`, `:909` (`except ColorError` catches the local class only); `plugins/pro-web-design-suite/skills/design-system-versioning/scripts/diff_system.py:1622-1629` (same) and `:1623`. The rebinding at `extract_system.py:278` / `diff_system.py:317` makes `parse_color` the upstream function, whose `ColorError` (`web-design-studio/scripts/generate_color_ramp.py:164`) is a different class.
- **What:** `OKLCH_ALPHA` accepts `oklch(l c h / a)` and reads `/ 1` or `/ 100%` as opaque, so the pair reaches contrast measurement, where `parse_color` (vendored or upstream, neither accepts an alpha slot) raises. In `compute_contrast` nothing catches it; in the two `except ColorError` sites the upstream exception is not an instance of the local class, so it would not be caught either.
- **Evidence:** `--fg-muted: oklch(47.5% 0.009 75 / 1)` → `extract_system.py` traceback ending `_wds_color_ramp.ColorError: Cannot parse 'oklch(47.5% 0.009 75 / 1)'` at `extract_system.py:1734`; `diff_system.py --no-upstream` traceback at `diff_system.py:1623`.
- **Effect:** One explicit-alpha colour aborts extraction, the docs build pipeline and the version diff with a stack trace instead of a report.
- **Fix:** Measure from the alpha-stripped text already assembled at `extract_system.py:894` (store it on `Resolved`, or re-strip in `compute_contrast`/`contrast_deltas`), and catch `ValueError` (the base of both `ColorError` classes) or rebind `ColorError = mod.ColorError` alongside the functions. Regression test: the value above on white produces a ratio, no traceback.
- **Confidence:** confirmed

### PY-C-4 · high · bug

- **Where:** `plugins/pro-web-design-suite/skills/design-system-docs/scripts/extract_system.py:1054`, `:1063-1065`; `plugins/pro-web-design-suite/skills/design-system-versioning/scripts/diff_system.py:393`, `:463-465`.
- **What:** `THEME_SEL` matches the attribute inside a `:not(...)` guard, so `@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { … } }`, the usual "follow the OS unless overridden" idiom, is classified as a `light` theme override. Overrides labelled `light` are never applied (`themes[1:]`), and the `prefers-color-scheme` branch at `:1069` is never reached.
- **Evidence:** Fixture with that block: `themes ['light']`; `--bg-canvas` resolved `{'light': '#ffffff'}` with overrides `[('theme', 'light')]`; `diff_system --no-upstream --format json` → `old.themes ['light']`.
- **Effect:** The dark theme disappears without a word: no dark column, no dark contrast, no `theme-added`/`theme-override-*` diffs for such a project.
- **Fix:** Strip `:not(...)` before the theme/density match (`strip_guards` already exists at `extract_system.py:1135`); then the media-query branch yields `("theme", "dark")`. Same in `diff_system.context()`. Regression test with the fixture.
- **Confidence:** confirmed

### PY-C-5 · high · bug

- **Where:** `plugins/pro-web-design-suite/skills/design-system-versioning/scripts/diff_system.py:2447-2448`.
- **What:** The migration guide's per-item command is `apply_codemod … --kind {dep.get('kind_hint', 'color')}`, but nothing in the plugin writes `kind_hint` (grep: only this line), so every item says `--kind color`. `deprecate.py:347-370` emits rules of kind `spacing`, `radius`, `type`, `tracking`, `z-index`, `duration`, `easing`, `shadow` by prefix.
- **Evidence:** Guide for `--gap-separate → --gap-distinct`: line `python -m scripts.apply_codemod ./src --mapping design-system/mapping.json --kind color`; the mapping `deprecate add` wrote for it has rule kinds `['spacing']`; `apply_codemod.py:1113-1120` exits 2 with "the mapping has no rules matching --kind color".
- **Effect:** The generated guide's one mechanical step fails for every non-colour token; a consumer following it applies nothing and may ship believing the codemod ran.
- **Fix:** Derive the kind the way `codemod_rules` does (share `PREFIX_RULES`, or have `deprecate add` store it in the ledger entry and read it here), or drop `--kind` from the guide since the mapping is already scoped to the ledger. Regression test: the guide for a `--gap-*` rename names `--kind spacing`.
- **Confidence:** confirmed

### PY-C-6 · high · bug

- **Where:** `plugins/pro-web-design-suite/skills/design-system-versioning/scripts/deprecate.py:836` (`per_consumer[root.name or str(root)] = …`), `:846` (`--record` writes `consumers` from the same keys).
- **What:** Consumers are keyed by the folder's basename, so `scan ../a/src ../b/src` (or two monorepo packages, or two checkouts named `web`) keeps only the last one.
- **Evidence:** `scan c1/src c2/src` with one hit in each: report shows `src 2 hit(s)` listing only `c2/src/b.css`, verdict "2 hit(s) in 1 of 1 consumer(s)"; `--record` writes `"consumers": {"src": 2}`.
- **Effect:** The evidence `retire` and `status` rely on silently undercounts; a consumer that still reads the token can be declared clear.
- **Fix:** Key by the path as given (`str(root)`), and refuse duplicate keys. Regression test with two same-named roots.
- **Confidence:** confirmed

### PY-C-7 · high · risk

- **Where:** `plugins/pro-web-design-suite/skills/design-system-versioning/scripts/deprecate.py:680-686` (`cmd_add` writes `--mapping`); compare `cmd_mapping` at `:768`, which does call `refuse_overwrite`.
- **What:** `add --mapping FILE` writes the mapping after injecting the marker into `--source`, with no check that `FILE` is the ledger or a source.
- **Evidence:** `add … --source victim.css --mapping victim.css` → exit 0, `victim.css` now begins `{ "schema": "design-token-migration/mapping@1", …`.
- **Effect:** A mistyped path replaces a stylesheet with JSON; the suite's "class 5" guard (the 2026-10-14 audit) was applied to `mapping` but not to `add`.
- **Fix:** `refuse_overwrite(args.mapping, ledger_path, *(args.source or []))` before writing. Regression test.
- **Confidence:** confirmed

### PY-C-8 · high · bug

- **Where:** `plugins/pro-web-design-suite/skills/figma-variables-sync/scripts/figma_to_tokens.py:426-430` (leading/tracking FLOATs); `plugins/pro-web-design-suite/skills/figma-variables-sync/scripts/figma_audit.py:542-545` (leading), `:556-559` (tracking).
- **What:** A `LINE_HEIGHT`-scoped FLOAT is written unitless (`24` becomes a 24× multiplier), while the audit reads the same `24` as a percentage (`0.24`). A tracking string such as `"0.5em"` is written as-is by the converter but read as `0.0` by the audit (`float(raw) if numeric else 0.0`), which is on the scale, so it passes.
- **Evidence:** Plugin export `leading/body = 24` (scope `LINE_HEIGHT`), `tracking/wide = "0.5em"`: `figma_to_tokens.py --format css` → `--leading-body: 24;` and `--tracking-wide: 0.5em;`; `figma_audit.py` → `0.24 is not one of the five leadings, nearest is 1 (--leading-none)` and no tracking finding.
- **Effect:** Under either reading of Figma's number (px or percent), `--leading-body: 24` is wrong CSS, and the audit's finding sends the designer the wrong way; the audit passes a tracking value the converter writes off the scale, which is the exact failure `figma_common` exists to prevent ("the audit passes and the build is wrong").
- **Fix:** Agree one unit model for line-height and letter-spacing FLOATs (Figma's scoped numbers are pixels: divide by the bound font size when known, else emit `px` and report), use it in both scripts, and read string values through `as_px`/`_em` in the audit. Regression tests on both scripts.
- **Confidence:** confirmed for the outputs; the right unit for a Figma FLOAT line-height is a design decision (likely px)

### PY-C-9 · medium · gap

- **Where:** `plugins/pro-web-design-suite/skills/figma-variables-sync/scripts/figma_common.py:437-455` (`parse_rest` reads `name`, `resolvedType`, `valuesByMode`, `scopes`, `codeSyntax`, `description`, `key` only); promised at `skills/figma-variables-sync/references/figma-mapping.md:473` ("`hiddenFromPublishing`… keep it out of the generated files").
- **What:** `deletedButReferenced`, `hiddenFromPublishing` and `remote` are never read, so a variable Figma has deleted (kept in the payload only because something still aliases it), a hidden one, or a library-owned one is converted and audited like any live local variable.
- **Evidence:** REST fixture with `neutral/0` marked `"deletedButReferenced": true`: `figma_to_tokens.py --format css` emits `--neutral-0: oklch(100% 0 0);` and `--bg-surface: var(--neutral-0);` with no problem; `figma_audit.py` reports nothing about it. No `deletedButReferenced`/`hiddenFromPublishing` string in any script or test.
- **Effect:** A deleted variable survives into `tokens.css`; an alias to it, which Figma shows as broken, audits clean.
- **Fix:** Read the three flags in `parse_rest`; report a `deletedButReferenced` target at each alias (a `BROKEN_ALIAS`-class finding) and do not emit it; keep `hiddenFromPublishing` variables out of generated files as the reference says (or emit them under a note); mark `remote` variables as library-owned in the report.
- **Confidence:** confirmed

### PY-C-10 · medium · gap

- **Where:** `plugins/pro-web-design-suite/skills/design-system-versioning/scripts/diff_system.py:2075-2098` (`attach_deprecations`, `gate_failures`) and `:2305-2307` (changelog "Deprecated" section).
- **What:** The gate asks only whether a ledger record with that name exists. It never compares the record's `since` with the release being cut (nor its `status`), so a token deprecated and removed in the same release passes, which is rule 1 of the skill ("never remove in the release you deprecated in", `deprecation.md:345`).
- **Evidence:** Ledger `--gap-separate since 2.0.0 removal 3.0.0`, diff `--from-version 1.0.0` recommending 2.0.0 with the token removed: `deprecation  recorded, since 2.0.0, removal 3.0.0 … result PASS`, exit 0. The changelog for the same run lists `--gap-separate` under **Removed** ("BREAKING … renamed") and under **Deprecated** ("still works, removed in 3.0.0").
- **Effect:** The one check the gate exists for can be satisfied by a record written in the same PR as the removal, and the changelog then contradicts itself.
- **Fix:** When `--from-version` is given, a record whose `since` is not below the recommended version does not cover a removal/rename (fail with "announced in this release"); a `status: removed` record should not cover one either. Regression test with the ledger above.
- **Confidence:** confirmed

### PY-C-11 · medium · inconsistency

- **Where:** `plugins/pro-web-design-suite/skills/design-system-versioning/scripts/deprecate.py:200-203` (`check_window`) versus its help at `:1043-1045` ("should be at least a minor away"), `references/scripts.md` ("A removal less than a minor version away is refused") and `references/deprecation.md:31-33` ("The minimum window is one minor version … refuses a record whose removal is not at least a minor version after").
- **What:** The code refuses any removal that is not `X+n.0.0` (`b[0] == a[0] or b[1:] != (0, 0)`), so `--since 2.1.0 --removal 2.3.0` is refused as "not a major release after 2.1.0", while three pieces of documentation say a minor suffices. The lifecycle table (`deprecation.md:29`) agrees with the code.
- **Evidence:** the condition at `:200`; the quoted lines.
- **Effect:** A user who follows the written rule gets exit 2 and reaches for `--force`, which the docs tell them to annotate as deliberate.
- **Fix:** Keep the code (removal is breaking, so a major) and correct the help string, `scripts.md` and `deprecation.md:31-33` to say "the next major"; or relax the check, if a minor was intended.
- **Confidence:** confirmed

### PY-C-12 · medium · bug

- **Where:** `plugins/pro-web-design-suite/skills/design-system-versioning/scripts/deprecate.py:612-624` (`replacement_problem`).
- **What:** A `--replacement` that starts with `--` must be declared in one of the `--source` files, but `--source` is where the *deprecated* name's marker goes. For a socket (`--button-pad` in `button.css`) or a component-local token whose replacement is a Tier-2 role in `tokens.css`, the check always fails.
- **Evidence:** `add --name --button-pad --kind socket --replacement --pad-inline-md --source button.css --dry-run` → exit 2 "`--replacement --pad-inline-md is declared in none of --source (…button.css)`".
- **Effect:** Every socket deprecation needs `--force`, which also disables the window check; the message blames a correct invocation.
- **Fix:** Search the project's token files too (`project_config().tokens`, or a `--tokens` flag), and apply the `--source` test only when a source is a token file. Regression test.
- **Confidence:** confirmed

### PY-C-13 · medium · inconsistency

- **Where:** `plugins/pro-web-design-suite/skills/design-system-versioning/scripts/deprecate.py:936-941` (`cmd_status --format json` returns 0 before `blocked` is computed) versus `:1008` (report returns 1).
- **What:** The documented exit 1 ("something due for removal is still in use", docstring `:52`) never happens in JSON mode.
- **Evidence:** Same ledger, `status --version 3.0.0` → exit 1; `status --version 3.0.0 --format json` → exit 0.
- **Effect:** A CI job that keeps the JSON for its summary never fails.
- **Fix:** Compute `due`/`blocked` before branching on the format, and include them in the JSON. Regression test.
- **Confidence:** confirmed

### PY-C-14 · medium · bug

- **Where:** `plugins/pro-web-design-suite/skills/design-system-docs/scripts/build_docs.py:1182` (`TOKEN_MENTION = --[a-z][\w-]*`), `:1308-1311`.
- **What:** Every `--word` in hand-written prose is a token mention, so a command quoted in a page (`build_docs … --out docs/site --check`) reports two vanished tokens.
- **Evidence:** `overview.md` containing that command in a code span: `DRIFT — … overview.md:1: mentions \`--check\`, which no longer exists`, `mentions \`--out\`, which no longer exists`; exit 1.
- **Effect:** The drift gate fails on any prose page that documents how to run the suite, including the plugin's own workflow text if pasted into `--prose`.
- **Fix:** Count a mention only in token form: `var(--x)`, `--x:` or a backticked `--x` whose first segment is a group prefix/known token; skip fenced blocks whose language is `bash`/`sh`/`console`. Regression test with the fixture.
- **Confidence:** confirmed

### PY-C-15 · medium · bug

- **Where:** `plugins/pro-web-design-suite/skills/design-system-versioning/scripts/diff_system.py:1630-1631` (skip when `abs(before - after) < 0.005`, before crossings are computed at `:1635-1642`), `:1709-1711` and `:1735-1740` (a Tier-2 literal compared by its 8-bit `display`), `:2221-2222` (`:.2f`); `plugins/pro-web-design-suite/skills/design-system-docs/scripts/extract_system.py:1736-1738` (`round(ratio, 2)` stored beside `ratio >= 4.5`); `build_docs.py:666-672` (prints `:.2f` with a `fail` badge).
- **What:** A ratio that crosses 4.5:1 (or 3:1) by less than 0.005 is dropped from the contrast report, and a Tier-2 literal colour whose OKLCH text moved by less than one 8-bit step is classified as a patch with "same value", while the suite's contrast, which it promises to measure from the OKLCH text, flips from pass to fail. The rounded display then reads `4.50:1` beside a `fail` verdict.
- **Evidence:** `--fg-muted: oklch(56.8080% 0 0)` → `oklch(56.8091% 0 0)` on white (4.500105 → 4.499900): diff → `[tier2-repointed-equal] --fg-muted  value #777777 -> #777777`, recommended bump **patch**, no contrast row; `extract_system` on the new file → contrast row `(4.5, False)`, which the docs render as `4.50:1` with a `fail` badge.
- **Effect:** The edge the whole skill is written around ("4.92 → 3.56 is the scenario") is handled, but a change that flips the suite's own AA verdict can ship as a patch, and the number a reviewer acts on is rounded onto the threshold.
- **Fix:** Compute crossings before the magnitude skip and always report a crossing; for the equal/patch call compare the resolved text (or OKLCH to three decimals), not only the hex; render ratios at the threshold with three decimals or floor-round (never up to the threshold). Regression test with the two values above.
- **Confidence:** confirmed

### PY-C-16 · medium · bug

- **Where:** `plugins/pro-web-design-suite/skills/design-system-docs/scripts/extract_system.py:1488` (`SKIP_DIRS`), `:1518-1520` (`any(part in SKIP_DIRS for part in sub.parts)` over the full path).
- **What:** The skip list is tested against every component of each path, including those above the directory given, so a project checked out under a folder named `build`, `out`, `dist` or `.next` yields no files.
- **Evidence:** `extract_system.py <scratchpad>/build/proj/styles` → "error: no token file found. Pass one with --tokens, or include a directory containing tokens.css".
- **Effect:** A CI workspace or home directory with such a segment gets a misleading error (`--tokens` works, the positional form does not).
- **Fix:** Test `sub.relative_to(p).parts`. Regression test.
- **Confidence:** confirmed

### PY-C-17 · low · inconsistency

- **Where:** `plugins/pro-web-design-suite/skills/figma-variables-sync/scripts/figma_to_tokens.py:1636-1637` versus `:1561-1565`.
- **What:** With a JSON input, `--reverse` goes straight to `reverse_main`, which only distinguishes `plugin-script`; `--format dtcg`, `ts` or `all` silently produce the REST body. For a `.css` input the same combination is refused with a message.
- **Evidence:** `t.json --reverse --format dtcg --quiet` → a `variableCollections` body, exit 0.
- **Fix:** Apply `css_main`'s format check in `main` for every `--reverse` input.
- **Confidence:** confirmed

### PY-C-18 · low · risk

- **Where:** `plugins/pro-web-design-suite/skills/design-system-docs/scripts/extract_system.py:2172-2176`, `:2186-2190`.
- **What:** `--out` and `--contract` are each checked against the inputs but not against each other, so the contract overwrites the snapshot.
- **Evidence:** `--out same.json --contract same.json` → two "wrote same.json" lines; the file's schema is `web-design-suite/contract/1`.
- **Fix:** `refuse_overwrite(args.contract, args.out)`.
- **Confidence:** confirmed

### PY-C-19 · low · bug

- **Where:** `plugins/pro-web-design-suite/skills/design-system-versioning/scripts/diff_system.py:282-286` (`_find_upstream` returns `None` for a missing explicit path), `:2597-2605` (no message when `None`).
- **What:** A mistyped `--color-impl` silently falls back to the vendored maths.
- **Evidence:** `--color-impl <missing>.py --format json` → `meta.color_impl = "vendored"`, no warning on stderr.
- **Fix:** Exit 2 (or warn) when an explicit path is not a file. `extract_system.py:240-244` has the same shape.
- **Confidence:** confirmed

### PY-C-20 · low · bug

- **Where:** `plugins/pro-web-design-suite/skills/figma-variables-sync/scripts/figma_common.py:278-287` (`as_ms` treats every unit but `s` as milliseconds); used at `figma_to_tokens.py:1015-1017` (`reverse_data.entry`) and `:1197-1198` (`to_figma_value`).
- **What:** `as_ms("50%")` and `as_ms("16px")` return 50 and 16, so a percentage token is typed FLOAT 50 for Figma without a word.
- **Evidence:** `as_ms("50%") = 50.0`, `as_px("50%") = None`.
- **Fix:** Return `None` unless the unit is `ms`, `s` or absent.
- **Confidence:** confirmed

### PY-C-21 · low · bug

- **Where:** `plugins/pro-web-design-suite/skills/design-system-docs/scripts/build_docs.py:1243-1246` (`diff_systems`).
- **What:** The drift report appends "** now below 4.5:1 **" to any changed ratio whose new value is below 4.5, even when the old one already was; it never mentions 3:1 or an upward crossing, which `diff_system` and the SKILL treat as news.
- **Evidence:** the condition `verdict = "" if nc[key] >= 4.5 else "  ** now below 4.5:1 **"`.
- **Fix:** Compare both sides to each threshold and word the verdict by direction.
- **Confidence:** confirmed

### PY-C-22 · low · compat

- **Where:** `plugins/pro-web-design-suite/skills/figma-variables-sync/scripts/figma_to_tokens.py:797`, `:830` (`read_bytes().decode("utf-8-sig", …)`), `:1535` (`write_text`), plus `write_text` at `diff_system.py:2734`, `extract_system.py:2182`, `build_docs.py:1125-1136`.
- **What:** `css_blocks` and `css_to_dtcg` bypass `read_text` (the UTF-16 detection the audit's class 4 added), so a `tokens.css` PowerShell 5.1 wrote gives `:root` tokens through `read_tokens` but no theme blocks. Separately, every generated file is written in text mode, so on Windows it carries CRLF while the SKILL's CI drift check (`figma_to_tokens.py … --format css | diff -u src/styles/tokens.css -`) compares bytes.
- **Evidence:** the two decode calls; `write_text` without `newline=`.
- **Fix:** Use `read_text` in both places; write generated files with `newline="\n"`.
- **Confidence:** confirmed by reading (not run)

### PY-C-23 · low · gap

- **Where:** `skills/design-system-versioning/references/scripts.md` §2 versus `plugins/pro-web-design-suite/skills/design-system-versioning/scripts/deprecate.py:1033-1035` (`--ledger`, which must precede the subcommand), `:1069` (`status --format json`), `:1105-1107` (`retire --force`), `:1058`, `:1082`, `:1092`, `:1107` (`--date`).
- **What:** The reference promises "every argument" but lists none of these; `--ledger` is the only way to keep the ledger anywhere but `./deprecations.json`.
- **Fix:** Add the rows.
- **Confidence:** confirmed

### PY-C-24 · low · gap

- **Where:** `plugins/pro-web-design-suite/skills/design-system-docs/scripts/build_docs.py:1097-1149` (`Site.build`), `:1509-1516` (no `refuse_overwrite` anywhere in the script).
- **What:** The SKILL says everything under `--out` "is rewritten on every run", but the folder is never cleaned: a `patterns.html` from a removed patterns folder and old `assets/src-NN-*.css` copies linger. `--out` is not checked against `--prose`, so `--out docs/prose --prose docs/prose` writes generated pages into the prose tree the SKILL promises is "never written to".
- **Fix:** Remove stale generated files (or write into a fresh temp folder and swap), and refuse `--out` inside or equal to `--prose`.
- **Confidence:** confirmed by reading

### PY-C-25 · low · bug (a mapping-contract hole; also dead code)

- **Where:** `diff_system.py:2082-2083` (`if ch.component and key in index: pass`, a no-op branch); `diff_system.py:2278` (`project` unused in `render_changelog`); `deprecate.py:631-632` (`--kind` re-validated after argparse `choices=KINDS` at `:1040`); `deprecate.py:117` (`marker_text` always writes `codemod=dep-<slug>` even when `codemod_rules` returns no rule at `:381-403`, so the marker promises a rule `mapping.json` does not hold); `extract_system.py:593` (`value` unused in `classify_tier`; callers pass `""` at `:1327`); `build_docs.py:662` and `:685` (`themes` unused in `contrast_table` and `socket_table`); `figma_to_tokens.py:593` (`header(extra=…)` never passed at `:611`, `:850`); `figma_to_tokens.py:946` (`token` unused in `token_type`).
- **Fix:** Delete the branch and the parameters; make the marker's `codemod=` reflect `entry["codemod"]`.
- **Confidence:** confirmed

### PY-C-26 · low · inconsistency

- **Where:** `plugins/pro-web-design-suite/skills/design-system-versioning/scripts/diff_system.py:1722-1731` (every Tier-1 `raw` change is `tier1-value-changed`, major).
- **What:** A Tier-1 respelling that resolves to the same display (`16px` → `1rem`, `#c64600` → `oklch(56.5% 0.176 42)`) is reported as a major with the line `value 16px -> 16px` / `#c64600 -> #c64600`; `_equivalent` (`:1374`) only recognises same-type DTCG spellings, so hex versus OKLCH is "changed". Tier 2 has `tier2-repointed-equal` for this; Tier 1 has nothing.
- **Evidence:** Report lines `[tier1-value-changed] --space-4  value 16px -> 16px  detail 16px -> 1rem` and `--accent-600  value #c64600 -> #c64600`.
- **Effect:** A px-to-rem or hex-to-OKLCH refactor of the primitives inflates the release to a major with no explanation a reader can act on (`1rem` does move with the user's root font size, so that one is defensible, but the report should say so).
- **Fix:** Add a `tier1-respelled` patch kind when display and every measured contrast are unchanged, or at least print the reason in `detail`.
- **Confidence:** confirmed

## Static-analysis candidates, resolved

- `deprecate.py:905` RUF017 — `sum(per.values(), [])` is quadratic but over a handful of lists; style only.
- `deprecate.py:961-964` RUF010 — `str(x)` inside f-strings; style only.
- `diff_system.py:308` PLW0603 — every reader (`resolve_display:645,648,658`, `contrast_deltas:1623`, `use_upstream_color_impl` itself) looks the names up at call time, so nothing keeps the old binding; the real hazard of the pattern is the `ColorError` class identity (PY-C-3).
- `diff_system.py:921` PERF403 — style only.
- `diff_system.py:2279` ARG001 `project` — dead parameter (PY-C-25).
- `extract_system.py:263` PLW0603 — same analysis as `:308` above (`resolve_value:894,905`, `compute_contrast:1734` read globals at call time); hazard is PY-C-3.
- `extract_system.py:593` ARG001 `value` — dead parameter (PY-C-25).
- `build_docs.py:662`, `:685` ARG001 `themes` — dead parameters (PY-C-25).
- `figma_audit.py:759` PIE810 — style; `:980` ARG005 — the no-colour lambda ignores `col` by design.
- `figma_common.py:480,483,490,496,498,499` B023 — `_ingest` is defined inside the `for col` loop and called only at `:512` and `:522` within the same iteration; it never escapes the iteration, so the captures are harmless. A module-level function taking `merged`, `cname`, `name_of`, `mode_labels` would silence the lint.
- `figma_to_tokens.py:426` PIE810 — style; `:946` ARG001 `token` — dead parameter (PY-C-25).
- pylint E0601 ×31 (`figma_audit.py`, `figma_to_tokens.py`) — false positives: the names come from `from figma_common import *` inside `try/except`, which pylint does not follow. `figma_common` defines `__all__` (`:29-61`), so the star import brings only listed names, and neither script's own definitions (`rgb_to_oklab`, `relative_luminance`, `contrast_ratio`, `composite_over` in the audit; `rgb_to_oklch`, `VAR_REF` in the converter) collide with it. `figma_audit.py:929-930` (`globals()[values_name] = …`) writes `SPACING_PX`…`BP_NAME`, which are defined in `figma_audit` itself (`:73-131`), not star-imported, and `check_float` reads them by global lookup at call time (`:519-526`, `:546`, `:560`, `:571`), so the rebinding works. An explicit import list would let pylint and mypy check the names; low.

## What is covered well

- Output refusal: `diff_system` (`:2612`), `extract_system` (`:2172`), `figma_audit` (`:1153`, `:1190`), `figma_to_tokens` (`:1612-1618`) and `deprecate mapping` all route through `refuse_overwrite`; only `deprecate add --mapping` (PY-C-7), `--out`/`--contract` (PY-C-18) and `build_docs` (PY-C-24) miss it.
- Encodings and endings: `inject_marker` reads and writes bytes in the file's own codec and BOM (`deprecate.py:231-260`), keeps its line ending, and the ledger keeps CRLF if it had it (`:161-168`); every CLI reconfigures a non-UTF-8 stdout.
- Input validation: `load_ledger` and `system_problem` check shapes before use; JSON is read as bytes so a BOM is handled; a missing named `--baseline` exits 2 rather than passing an empty check.
- `var()` cycles and undeclared references never crash either resolver (`diff_system.substitute:546-553`, `extract_system.Resolver.substitute:854-861`); depth is bounded.
- Determinism: tokens, gaps, limits, changes, contrast rows and ledger entries are sorted; `figma_to_tokens` stamps a date only from `SOURCE_DATE_EPOCH`; the search index escapes `<` so a `</script>` in a note cannot end the inline script.
- Secrets: no script reads `FIGMA_TOKEN` or calls the API; the `--reverse` routes only build a body or Plugin API code. DTCG resolvers are read with the resolver's own folder as the base at every call site (`figma_common.py:769`, `figma_to_tokens.py:1026,1038`, `diff_system.py:1465`); the containment check itself lives in `dtcg.py` (another pass).
- Python 3.9: every file has `from __future__ import annotations`; no `removeprefix`, `match`, `zip(strict=)`, `functools.cache` or runtime `X | Y` found; the `str | Path` annotation at `extract_system.py:1550` is a string under the future import; the one walrus (`figma_audit.py:681`) is 3.8+.
