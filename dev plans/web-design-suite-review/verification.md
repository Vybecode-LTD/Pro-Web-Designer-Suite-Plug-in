# Lead's spot-verification of reviewer claims

**Coverage:** 25 of the 28 high-severity issues were re-checked independently, along with 5
medium ones. The three high items not re-run rest on the reviewer's own evidence. SB-A5 and
SB-A7 need Tailwind builds; the reviewer compiled with tailwindcss 4.3.1 and 3.4.19. GT-A2
needs the reviewer's browser fixtures for a modal dialog and an iframe.

Each reviewer ran their own checks. The lead then independently re-checked the high-severity
claims (and a sample of medium ones) with the commands below before accepting them.
Plugin under test: the installed 3.0.1 at `~/.claude/local-marketplaces/web-design-suite`,
run with `PYTHONDONTWRITEBYTECODE=1` so nothing was written into it.

| Claim | How it was checked | Result |
|---|---|---|
| SS-A1 density does nothing on a subtree | tokens.css:93-110 declares every `--gap-*`/`--pad-*` role as `calc(var(--space-N) * var(--density))` in the root block; :487-489 `[data-density=…]` sets only `--density`. Custom properties resolve `var()` where declared and inherit the result. | Confirmed (mechanism) |
| SS-A2 native fields unreadable when theme and scheme disagree | reset.css:110 `color-scheme: light`; the `[data-theme="dark"]` block (tokens.css:425) never sets `color-scheme`; the OS media query (:473-476) sets `color-scheme: dark` but no tokens. | Confirmed (mechanism) |
| SS-A3 `[hidden]` loses to layout primitives | `[hidden]` rule is in `@layer reset` (reset.css:421); primitives are in `@layer layout`; a later layer wins regardless of specificity. | Confirmed (mechanism) |
| SS-A4 role pairs fail AA | `generate_color_ramp --check`: danger-500 on dark canvas **4.38:1**, on dark surface **4.24:1**; `--border-default` (neutral-300) on white **1.51:1**. | Confirmed (exact numbers reproduced) |
| SS-A5 reset removes the dialog size limit | reset.css:446-454 `dialog { … max-inline-size: none; max-block-size: none; }` | Confirmed (code) |
| SS-A14 / XC-A8 script cwd ambiguity | Reported separately by SS-A14, and also as LC-A20, DL-A19 and GT-C6. All 21 scripts run by file path from an unrelated cwd. | Confirmed |
| SS-A19 BOM breaks `audit_design` | Same 3-line `@layer components{…}` file with and without a UTF-8 BOM: plain → "clean", exit 0; BOM → `L5 unlayered`, exit 1. | Confirmed (reproduced) |
| XC-A9 baseline depends on path spelling | Baseline written with `src/`; `src/`, `src`, `./src` exit 0; absolute path exits 1 (also with `--baseline <abs>`). | Confirmed (reproduced) |
| LC-A1 DTCG 2025.10 export → invalid CSS, exit 0 | Re-ran the reviewer's fixture (valid 2025.10 shape: `{colorSpace, components, alpha, hex}`, `{value, unit}`, group `$type`) against the installed scripts: `figma_to_tokens --format css` wrote `--neutral-500: {'colorSpace': 'srgb', …};` and `--space-6: {'value': 24, 'unit': 'px'};`, exit 0; `figma_audit --fail-on error` exit 0. | Confirmed (reproduced) |
| LC-A2 composed-colour opacity treated as 0..1 | figma_to_tokens.py:266 uses `opacity` directly as alpha. Figma's variables-types page (fetched): opacity is "An opacity percentage from 0 to 100, or an alias to a `FLOAT` variable"; the colour channel may be "an alias to a `COLOR` variable". | Confirmed (code + primary docs) |
| LC-A3 project ramps rejected | figma_audit.py:118 hard-codes `RAMPS`; no `--tokens` argument exists. | Confirmed (code) |
| LC-A4 timestamp breaks the CI drift check | figma_to_tokens.py:860 (`datetime.now(…).strftime("%Y-%m-%d %H:%M UTC")`) and :911 (`isoformat`) stamp every output. | Confirmed (code) |
| LC-A5 focus ring rewritten to elevation | cluster_values.py's only "focus" logic is border-colour naming (:849) and the emitted token file (:2028-2039); no shadow rule routes a spread-only ring to `--shadow-focus`. The exact rewritten output (`var(--elevation-card)`) is from the reviewer's end-to-end repro. | Confirmed (code: no such rule exists) |
| LC-A6 rebase recipe loses teammates' work | Git semantics: during `git rebase`, `--ours` is the upstream being rebased onto and `--theirs` is the commit being replayed (git-checkout docs: the sides "may appear swapped"). `--theirs` therefore keeps the already-migrated file and drops the teammate's change. | Confirmed (git semantics) |
| LC-A10 SvelteKit `src/lib` treated as vendor | extract_literals.py:79 `VENDOR_DIRS` includes `lib`, `libs`; apply_codemod has no `--include-vendor` (0 matches). | Confirmed (code) |
| DL-A1 secret columns displayed | introspect_schema.py:174-176: the credential rule is an anchored exact-name list (`^(password\|…\|api_key\|access_token\|refresh_token\|private_key)$`); field-mapping.md:125 promises `*_hash`, `*_token` patterns. `api_token`, `reset_token`, `webhook_secret`, `token_hash` cannot match. | Confirmed (code vs doc) |
| DL-A2 authorization columns editable | introspect_schema.py:1863-1868: the read-only question's default is only columns already non-editable; no rule anywhere mentions `role`, `is_admin`, `owner_id`, `tenant_id` (0 matches). | Confirmed (code) |
| DL-A3 wrong RLS failure model | supabase-integration.md:99 "a blocked write is loud", :105 `23503` "often a parent the user cannot see", :247. Postgres: referential-integrity checks bypass row security, and an UPDATE/DELETE on rows hidden by `USING` affects 0 rows without error. | Confirmed (doc text + Postgres semantics) |
| GT-A1 runtime contrast skips OKLCH | a11y_runtime.mjs:1162-1166: `parse` matches only `/rgba?\(/` and returns null otherwise; Chromium serialises colours authored in `oklch()` as `oklch(…)` (CSS Color 4), which is what the suite's tokens produce. | Confirmed (code + serialisation rule) |
| GT-A3 visual gate blind to hover/active | snapshot_matrix.mjs:42 per-pixel tolerance 0.10 → pixelmatch max YIQ Δ = 35215 × 0.1² ≈ 352. A 4% dark overlay on white moves each channel ≈10 → Δ ≈ 0.505 × 10² ≈ 51; 8% → ≈ 210. Both are under 352, so those pixels never count as different. | Confirmed (arithmetic) |
| GT-A4 SKILL.md hook snippet | a11y SKILL.md:73-79: no shebang, no `set -e` (exit code is the last command's), unquoted `$CHANGED` of every staged file, "three checks" with two shown. | Confirmed (text) |
| PS-A1 deck claims "passes … keyboard-tested" regardless of data | build_presentation.py:952-958: `wording = ("The honest claim: this page passes an automated WCAG 2.2 AA check and has been keyboard-tested by hand. …")` is assigned unconditionally after the violations table; :868 fixed title "It is fast, and it stays fast"; :838 "Nine laws, machine-enforced". | Confirmed (code) |
| PS-A2 defence sheet drops confirmed defects | critique_report.py:678 `carried = [f … if f.severity != "taste" and (f.defend or f.confidence != "confirmed")]` — a confirmed finding is carried only if `defend` is set, which the template has no field for. | Confirmed (code) |
| PS-A3 merge folds whole rule groups on a word | critique_report.py:474 `if rule and rule in hand_text:` — plain substring test; the L5 rule id is `important`. | Confirmed (code) |
| SB-A1 canonical Button has no keyboard focus ring | reset.css:334-348 puts the ring on `:focus-visible` as `box-shadow` with a transparent outline, inside `@layer reset`; stack-vanilla-css.md §8 sets `.button { box-shadow: var(--btn-shadow) }` in `@layer components` and has no focus rule (0 "focus" matches in :364-487). The later layer wins, so the ring is replaced. | Confirmed (mechanism) |
| SB-A2 Tailwind `focus-ring` utility drops the forced-colors fallback | theme.css:738-741 `@utility focus-ring { outline: none; box-shadow: var(--shadow-focus); }` | Confirmed (code) |
| SB-A3 any `var(` disables L1 for the declaration | `padding: var(--pad-block-sm) 13px`, `transition: opacity 300ms var(--ease-out)`, `box-shadow: 0 1px 2px #000, var(--elevation-card)` in a component file: `0 error(s)`, no L1 finding. | Confirmed (reproduced) |
| SB-A4 spacing inside `@media` never checked | `@layer layout { @media (width >= 48rem) { .page-hero { margin-top: 13px; padding: 7px 9px } } }` → "clean"; the same rule outside `@media` → 2 L1 errors. | Confirmed (reproduced) |
| SB-A6 handoff pipeline script doesn't exist | handoff-conventions.md names `build-tokens.mjs` 4 times; no `build-tokens*` file exists anywhere in the plugin. | Confirmed |
| PS-A4 HTML passes the design gate unaudited | New fixture: `<style>` with `margin-top:37px; color:#ff0000; font-size:13px !important` and `style="margin:13px;color:#f00"`. `audit_design <folder> --strict` and `audit_design <file.html> --strict` both print "design audit: clean — all nine laws hold.", exit 0. | Confirmed (reproduced) |
