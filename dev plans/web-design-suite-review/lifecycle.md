# web-design-suite 3.0.1 review: lifecycle skills (prefix LC)

Scope: design-token-migration, figma-variables-sync, design-system-docs and design-system-versioning (every SKILL.md, reference and asset), plus the scripts wherever a doc makes a claim about them. Nothing in the plugin was modified. Every repro ran on a copy under `scratchpad/review/lifecycle/` (plugin copied to `wds/`, fixtures in `fx/`), with `PYTHONDONTWRITEBYTECODE=1`, cwd = the fixture, and `PYTHONPATH` = the skill folder. Nothing listed in the bug-fix report's "Fixed" or "Judged not to be bugs" tables is reported again.

## A. Issues

**LC-A1 · high · conf high · figma-mapping.md:576-582, SKILL.md:63, figma_to_tokens.py/figma_audit.py `parse_dtcg`.** The docs say that if Figma's native DTCG export is live, "it works today". It does not. DTCG reached its first stable version, 2025.10, on 2025-10-28. In that version a colour `$value` is `{colorSpace, components, alpha, hex}`, a dimension or duration is `{value, unit}`, and references can also be `$ref`, `$extends` or `$root`. The spec states that strings such as `"#ff0000"` or `"16px"` are not valid ([format 2025.10](https://www.designtokens.org/tr/2025.10/format/), [announcement](https://www.w3.org/community/design-tokens/2025/10/28/design-tokens-specification-reaches-first-stable-version/)). Repro: run `figma_to_tokens.py fx/figma/dtcg-2025-10-clean.tokens.json --format css`. It writes `--neutral-500: {'colorSpace': 'srgb', 'components': [0.4196, …], …};` and `--space-6: {'value': 24, 'unit': 'px'};` (Python dict reprs, which are invalid CSS) and exits **0**. `figma_audit.py … --fail-on error` also exits **0** with 0 errors. The same tokens written as legacy strings give `2 error` (28px is off the scale, #6b6b6b is off the ramp). A token declared with `$ref` is dropped silently. This is the failure SKILL.md:345 itself warns about: "the audit passes and the build is wrong". **Fix:** add a 2025.10 reader that handles object values, `$ref`, `$extends`, `$root`, group `$type` inheritance and `$deprecated`. Until then, exit 2 on any non-scalar value that is not understood.

**LC-A2 · high · conf high · figma-mapping.md:155-159, `as_color` in both figma scripts.** The docs say "Both scripts read" `VariableComposedColor`. Figma defines `opacity` as "an opacity percentage from 0 to 100" and requires at least one channel to be an alias ([variables types](https://developers.figma.com/docs/rest-api/variables-types/)). Repro with `fx/figma/composed.json` (REST shape):
- The alias-colour case, `{"color":{VARIABLE_ALIAS},"opacity":8}`, is emitted as `--bg-hover: {'color': {'type': 'VARIABLE_ALIAS', …}, 'opacity': 8};` with exit 0, and the audit reports nothing.
- The scripts treat opacity as 0..1: `opacity:12` becomes fully opaque `oklch(22.9% 0.006 67.5)`, and only `0.12` produces `/ 0.12`. Every translucent hover or scrim role therefore becomes an opaque fill.
- The note "no CSS equivalent" is also wrong: `color-mix(in oklch, var(--x) 8%, transparent)` and `oklch(from var(--x) l c h / var(--o))` both keep the link.

**Fix:** resolve an alias in the colour channel, divide opacity by 100, and emit `color-mix()` so the alias survives.

**LC-A3 · high · conf high · figma_audit.py:118 (`RAMPS` hard-coded), audit-and-reconcile.md:115-118 & 433-442.** The audit and the generator compare every file against the studio's own ramps, and no flag accepts the project's `tokens.css`. The README's chain goes design-token-migration → figma-variables-sync, and the migration step deliberately seeds the accent from the client's brand. Repro: export the 11 accent steps from `cluster_values`' `proposal/tokens.css` (seed #2f6df6) as records, then run `figma_audit.py project-accent.json`. Result: **11 errors, OFF_RAMP_COLOR**, with suggestions to "bind to --info-100 / --neutral-300 / --info-500". The reference says the audit is "built to have none" of these false positives and that a project must *edit the plugin script* to add a token, which a plugin update then overwrites. **Fix:** `--tokens path/to/tokens.css` (or a `contract.json` from extract_system) as the source of ramps and scales in every script. See LC-C1.

**LC-A4 · high · conf high · SKILL.md:255-262; figma_to_tokens.py:860, 911.** Generated `tokens.css` and `tokens.json` embed `generated <UTC minute>` and an ISO timestamp, so the documented CI drift check fails on an **unchanged** export. Repro: run `figma_to_tokens.py plugin.json --format css | diff -u src/styles/tokens.css -` one minute after generating. Output: `-generated 2026-09-24 01:07 UTC / +… 01:08 UTC` and "tokens.css is stale", exit 1. The suite's own rule (extraction.md §10: "a timestamp … makes every CI run report drift, and the gate is switched off within a week") is broken here. **Fix:** drop the stamp or honour `SOURCE_DATE_EPOCH`, and add a test that two runs produce identical output.

**LC-A5 · high · conf high · extraction-and-clustering.md:290; cluster_values.py.** The reference says a `0 0 0 3px rgba()` focus ring "belongs to `--shadow-focus` … the classifier will get it wrong, so check for it". Nothing checks. Repro: `apply_codemod ./src -m ../proposal/mapping.json` rewrites `.button:focus-visible { box-shadow: 0 0 0 3px rgba(47,109,246,.4) }` to `var(--elevation-card)`. Rule `sh-001` has confidence `snapped`, so the rewrite also survives `--skip-review`, and reconciliation.md does not list it. The visible focus indicator is lost (WCAG 2.4.7). **Fix:** classify zero-offset, zero-blur, spread-only shadows as `--elevation-focus`, or mark them `review`.

**LC-A6 · high · conf high · migration-strategies.md:358-371, MIGRATION_PLAN.md:136.** "Rebase daily, never merge", then resolve conflicts with `git checkout --theirs file` and re-run the codemod. During a rebase, `--theirs` is *your migration commit* ([git-checkout docs](https://git-scm.com/docs/git-checkout): ours and theirs "may appear swapped"). Repro in `fx/rb`:
- The teammate's `font-style: italic` and `#fafaf9` edits vanish. The codemod reports `0 replacement(s)` and exits **0**.
- With the correct side (`--ours`), the codemod refuses the file: `SKIP … has uncommitted changes`, exit 1.

**Fix:** `git checkout --ours -- f && git add f && apply_codemod f -m … --apply && git add f && git rebase --continue`. This sequence was verified: the teammate's change is kept and the file is migrated.

**LC-A7 · medium · conf high for the styles and Plugin API facts, medium for the MCP plan details · SKILL.md:26-40, figma-mapping.md:511-515 & 567-574.** Two claims are out of date. The first is "No scripting workaround on Professional/Organization … the exported-JSON path … is the only path". In fact the Plugin API reads and writes variables on every plan. The official Figma MCP server (Dev or Full seat on Professional, Organization or Enterprise; Starter is capped at 6 calls a month) gives Claude `get_variable_defs` and `search_design_system`, and `use_figma` runs Plugin API code that can create collections, modes and variables ([tools](https://developers.figma.com/docs/figma-mcp-server/tools-and-prompts/), [mcp-server-guide](https://github.com/figma/mcp-server-guide/blob/main/skills/figma-use/references/variable-patterns.md), [FAQ](https://help.figma.com/hc/en-us/articles/39252411778583-Figma-MCP-server-FAQs)). The second is the "Read styles: Enterprise only" row. `GET /v1/files/:key/styles` is **not** Enterprise-gated (scope `library_content:read`), but it returns only **published** styles ([docs](https://developers.figma.com/docs/rest-api/component-endpoints/)), so the "local includes unpublished drafts" advice does not carry over to styles. For a draft file, `styles.json` comes back empty and the UNMAPPED_* checks see nothing. The Enterprise gate on the Variables REST API itself, and the details of §14 (scopes, tiers, extended-collection fields, composed colour), check out.

**LC-A8 · medium · conf high · change-classification.md:165, 203-204 vs diff_system.py.** The doc says density-scale changes, reduced-motion changes and root-element changes are "major · auto-detect yes". Repro: v1→v3 in `fx/ver` changes only `--density: 0.875→0.8`, reduced-motion `1ms→0.01ms` and `<div>`→`<section>`. The result is **`RECOMMENDED BUMP PATCH … because nothing changed`**, although system.json records all three (`density/compact 21px→19.2px`, `overrides`, `element`). **Fix:** compare the density environments, the condition overrides and `element`, or mark those rows "not detected".

**LC-A9 · medium · conf high · change-classification.md:76, 163, 167 vs §1/§11 and diff_system.py.**
- `theme-override-added` is classified minor, but it changes rendering in that theme, which is major by the file's own test (§11 Q2: "any theme"). Removing an override is classified major. Repro v1→v4: a new dark override takes `--fg-muted` from 3.27:1 to **1.83:1 ("CROSSED 3.0:1 DOWNWARD")**, yet the tool reports `RECOMMENDED BUMP MINOR` and the gate says PASS.
- "Add a part: minor" contradicts §11 Q3 (a DOM change is major).
- "Rename a class under CSS Modules: patch" is reported by the tool as `part-removed` (major) with a gate FAIL (`Card.module.css`, `card__title`→`card__heading`).

**Fix:** make added overrides and parts major whenever an existing value moves, and record `.module.css` in system.json.

**LC-A10 · medium · conf high · extract_literals.py:79 (`VENDOR_DIRS` includes `lib`, `libs`), used by apply_codemod.** SvelteKit's `src/lib` is where its components live, and it is silently treated as vendor. Repro `fx/lib`: the census counts 1 of 3 literals and does not mention any exclusion. `apply_codemod src/lib/components/button.css -m …` gives `0 replacement(s)` even though the file was named explicitly. apply_codemod has no `--include-vendor` flag. SKILL.md:59 says to use `--include-vendor` "once … then never again". **Fix:** only treat `lib/` as vendor under `node_modules` or when a marker says so, report the excluded count, and add the flag to the codemod.

**LC-A11 · medium · conf high · extraction-and-clustering.md:352-357, SKILL.md:117.** The reference says a negative cancel must "point at the **same token** the padding uses… Never" point elsewhere. Using the reference's own example (`fx/mig2`): `padding:16px` becomes `var(--pad-well)`, while `margin:-16px` becomes `calc(var(--gap-grouped) * -1)`. The reference's suggested target, `--pad-card`, is 24px, which is also wrong for a 16px padding. **Fix:** pair each negative margin with the padding of its parent rule (if not found, report it), and correct the example.

**LC-A12 · medium · conf high · SKILL.md:77, extraction-and-clustering.md:246-248.** The docs say "15px … becomes 16 (`--type-body`), not 14. Text does not shrink." When 14px occurs more often, the tool maps 15px to `--type-ui` (14px) and writes the note "snapped UP to 14px. Text does not shrink", while its delta is `-1.0`. **Fix:** either document that frequency comes first or break ties upward for type, and generate the note from the actual direction.

**LC-A13 · medium · conf high · SKILL.md:134-137.** `git stash && audit_design … > /tmp/before.json && git stash pop`: the audit exits 1 on any legacy code, so `pop` never runs. Repro: after `--kind color --apply`, the chain exits 1 and the working tree is back at base, with the batch left in `stash@{0}`. It also does not measure "before" once batches are committed, and `/tmp` does not exist on Windows. **Fix:** `git worktree add ../base <base-sha>` and audit there, or use `;` in place of `&&`.

**LC-A14 · medium · conf high · deprecation.md:218, 223; apply_codemod font guard; deprecate.py scan.**
- deprecate.py emits a colour rename. On `.meta-strong { color: var(--fg-subtle); font-weight: 600 }`, the codemod refuses with "`font: var(--fg-faint)` would reset font-weight … delete those first". That tells the consumer to delete a legitimate `font-weight` in order to rename a colour. Apply the guard only when the replacement starts with `font:`.
- `scan` labels single-line rules `[manual] why: not a plain declaration`. On `fx/dep/client` it reports "0 codemod · 9 manual", but the codemod rewrites 7 of them. Multi-line formatting labels them correctly, so "the honest list" depends on whitespace.

**LC-A15 · medium · conf high · framework-migrations.md:330, 357.** The doc says that after replacing the Tailwind theme, "an off-scale class does not exist and the build errors on it". It does not error. Tailwind "generate[s] CSS for these tokens, discarding any that don't map to known utility classes" ([docs](https://tailwindcss.com/docs/detecting-classes-in-source-files)), so leftover `p-4` or `bg-gray-100` classes silently lose their styling. **Fix:** grep for the removed stock utilities, or add a class-name lint rule before replacing the theme.

**LC-A16 · medium · conf high · framework-migrations.md:405-435.**
- Re-pointing `--bs-primary` does not reach `.btn-primary`, which sets `--bs-btn-bg: #0d6efd` literally ([bootstrap.css](https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/css/bootstrap.css)), or `.bg-primary` and `.text-primary`, which use `rgba(var(--bs-primary-rgb)…) !important` ([bootstrap-utilities.css](https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/css/bootstrap-utilities.css)).
- Because `!important` is inverted across layers, putting Bootstrap in the lowest layer (`@layer vendor`) makes its `!important` utilities beat everything in `components` and `overrides`. The "layer order beats specificity entirely" line never mentions this.
- The MUI example (`main: 'var(--bg-accent)'`) needs `cssVariables: { nativeColor: true }` ([MUI native color](https://mui.com/material-ui/customization/css-theme-variables/native-color)).

**LC-A17 · medium · conf high · rollout.md:249, 98 vs 189-193.** The model announcement reads "**Design system 2.1.0.** One breaking change: `--bg-accent` moved…". That is a breaking re-point shipped as a minor, the exact failure this skill exists to prevent (a re-point is major, SKILL.md:27). Step 3's `git commit -am` also splits the upgrade into several commits, which contradicts §6's one-commit rollback. **Fix:** make the example 3.0.0, and commit once after step 6.

**LC-A18 · medium · conf high · docs SKILL.md:95 vs 141; drift-detection.md:43 vs 154; versioning SKILL.md:57.**
- The baseline is extracted from `styles/ src/components/`, but CI extracts from `styles/ src/`. Repro `fx/drift`: an unchanged repo gives `DRIFT — component added home`, exit 1, because `src/pages/home.css` declares its own socket block.
- The same snapshot is committed under three names: `system.json`, `docs/system.json` and `published/system.json`.

**Fix:** keep one path and one set of inputs, saved in a config file that both skills read.

**LC-A19 · medium · conf high · extraction.md:251 vs 260.** The doc says "tier1-leak … agree[s] by construction" with audit_design L6. It does not. In a `.module.css` file, audit_design flags `var(--space-0)` and `var(--shadow-none)` as L6 errors, while extract_system exempts them as "null-outs" (`fx/l6`). The two gates disagree about the same line. **Fix:** move the prefix and exception lists into one module that both import, with a parity test.

**LC-A20 · medium · conf high · migration SKILL.md:180, figma SKILL.md:301; deprecate.py default `--ledger ./deprecations.json`.** "Run them from this skill's root" combined with cwd-relative defaults writes project artifacts (literals.json, proposal/, the deprecation ledger) into the plugin install, which a plugin update replaces. The ledger really did land in the skill folder in this test. **Fix:** document `PYTHONPATH="${CLAUDE_SKILL_DIR}" python -m scripts.X`, run from the project root.

**LC-A21 · medium · conf high · README.md:111-114 (the migration hand-off).** `extract_literals --format report` writes no literals.json, so `cluster_values literals.json` fails with "no such file", exit 2. `apply_codemod proposal/mapping.json --kind spacing` then fails with "the following arguments are required: -m/--mapping", exit 2. SKILL.md itself is correct.

**LC-A22 · low · conf med · `--reverse` (SKILL.md:221-225, figma-mapping.md:562-565).** Three problems with the generated POST body:
- Initial modes are never named. The Plugin API names a new collection's first mode "Mode 1", and Figma's REST docs show an `UPDATE` on the temporary id to rename it. "initialModeId only names it" is therefore misleading.
- The body carries a `_comment` key. The payload itself says "Figma rejects unknown top-level keys", but SKILL.md never says to strip it.
- Primitives get picker scopes (`ALL_FILLS`, `GAP`). This invites binding Tier 1, which is the Law 6 failure SKILL.md:359 describes. Figma's guide uses `scopes = []` to hide them.

**LC-A23 · low · conf high · smaller accuracy and consistency items.**
- deprecation.md:136: "`@deprecated` … surfaced by `tsc`" is false. `tsc` does not report it; use `@typescript-eslint/no-deprecated` ([docs](https://typescript-eslint.io/rules/no-deprecated/)).
- deprecate.py accepts `--removal 2.2.0` for `--since 2.1.0`, but the contract (deprecation.md:29) puts removals in X+1.0.0.
- MIGRATION_PLAN.md:114 says "20px --pad-inline-sm", but `--pad-inline-sm` is 12px.
- SKILL.md:71 says "Four separate algorithms" and then lists six; versioning SKILL.md:112 says "Four edits" and then lists five.
- reconciliation.md prints durations as "Δ -40px".
- The reconciliation recommends `$brand: var(--fg-default)` for the brand blue ("point it at the role"). framework-migrations.md:112 says to delete such variables, not re-point them.
- framework-migrations.md:139 says darken() distances are reported; they are canned text.
- 13 of the 19 functions that the two figma scripts "share" (SKILL.md:345) have already diverged.

## B. Gaps

- **LC-B1 · no non-Enterprise route into Figma.** `--reverse` only builds a REST body that requires Enterprise. Most teams need a path through the Plugin API or `use_figma` (see LC-A7), and Claude Code can drive it directly through the MCP server. Scope: a `--format plugin-script` output and a routing row in SKILL.md.
- **LC-B2 · Style Dictionary, Tokens Studio and Terrazzo teams get nothing.** None of them is mentioned anywhere in the plugin (Style Dictionary 5.5.5, sd-transforms 2.0.3 and Terrazzo 2.7.1 on npm today). A Tokens Studio export (`fx/figma/tokens-studio.json`) becomes `--light-bg-surface` and `--dark-bg-surface` in place of a `[data-theme]` block, and `--space-6: {space.base} * 6;`. Such a team needs:
  - Tokens Studio `$themes` read as modes.
  - A way to map Style Dictionary's name transforms onto the contract grammar, so the tier and Law 6 checks work on `--color-bg-surface`.
  - Diffs and deprecations at the DTCG JSON level (`$deprecated` fed into the ledger).
  - The migration proposal output as DTCG `tokens.json`.
- **LC-B3 · no way to supply a project contract.** Brand ramps, added Tier-2 roles and custom breakpoints all require editing plugin code (see LC-A3). audit-and-reconcile.md:433-442 even tells users to do this.
- **LC-B4 · no CI bootstrap.** Every CI snippet (the drift-detection.md:170-209 workflow, rollout.md §3) runs `python -m scripts.X` in a clean checkout with no scripts present. Chaining skills needs every skill root on `PYTHONPATH`. That works, because the `scripts` folders are namespace packages (verified), but nothing documents it. The versioning skill depends on four sibling skills, which contradicts the README's claim that each skill works standalone.
- **LC-B5 · migration coverage.** Missing:
  - `<style>` blocks in Vue, Svelte and Astro files.
  - HTML `style=""` attributes.
  - Object-style CSS-in-JS (vanilla-extract, Panda, MUI `sx`).
  - Sass module functions (`color.adjust`, `color.scale`, `color.mix`) are not counted at all. In `fx/sass`, 1 of 4 colour functions was found. The Sass docs ([sass:color](https://sass-lang.com/documentation/modules/color/)) point users away from `darken()` and to these functions.
  - Tailwind v4 `@theme`, where `--spacing` is a multiplier and replacing named keys does not remove `p-4`.
  - `.sass` is listed, but the scanner is brace-based.
- **LC-B6 · Figma plan realities.** Mode limits are Starter 1, Professional 10, Organization 20 and Enterprise 40 ([Schema 2025](https://help.figma.com/hc/en-us/articles/35794667554839-What-s-new-from-Schema-2025), [REST limits](https://developers.figma.com/docs/rest-api/variables-endpoints/)). Theme × density × brand modes can exceed them, and MISSING_DARK_MODE fires on Starter, where a second mode is impossible. Also missing: branch file keys, and the fact that published and local styles differ.
- **LC-B7 · rollout gaps.** §3 has no step to "capture baselines on the old version" before `npm install`, so baselines created afterwards simply approve whatever the new version renders. There is no `npm deprecate` for a bad release, and no Renovate or Dependabot recipe that keeps exact pins with a visual-diff check.
- **LC-B8 · claims with no gate.** Examples: "tokens.css is `git`-enforced read-only" (SKILL.md:246), where nothing enforces it and the CI check is broken (LC-A4); the two parity claims (LC-A19, LC-A23); and the worked-run numbers (migration SKILL.md:245-292, versioning SKILL.md:112-135), which come from fixtures that are not shipped.

## C. Improvements

| ID | What | Why | Effort | Priority |
|---|---|---|---|---|
| LC-C1 | Add `contract.json`, emitted by extract_system from the project's tokens.css and read through `--tokens` by figma_audit, figma_to_tokens, cluster_values, audit_design and diff_system. Delete the hard-coded `RAMPS` and scale tables. | Fixes LC-A3 and LC-B3. One source of truth replaces five copies. | L | P1 |
| LC-C2 | Add a shared `dtcg.py` for 2025.10 read and write, Tokens Studio sets and themes, and `$deprecated` → ledger, plus a `--format dtcg` output. | Fixes LC-A1 and LC-B2. Brings Style Dictionary 5, Terrazzo and Figma native interop. | M | P1 |
| LC-C3 | Move the two figma scripts' shared code into `figma_common.py`, and add a parity test for extract_system tier1-leak vs audit_design L6. | Turns the "share" and "by construction" claims into facts (LC-A19, LC-A23). | S | P1 |
| LC-C4 | Add regression tests for LC-A5, A10, A11, A12, A14 and A2, then fix each one: focus-ring detection, the vendor rule, negative-cancel pairing, the type-tie note, the font guard scope, and composed opacity. | Each is a silent wrong result from the step marked "mechanical". | M | P1 |
| LC-C5 | diff_system: cover density, conditions, `element` and CSS Modules; record `@layer` in system.json; make an added override major when an existing value moves. | Fixes LC-A8 and LC-A9. The docs can then keep their "auto-detect: yes". | M | P1 |
| LC-C6 | Instruction fixes: the rebase recipe (LC-A6), a worktree-based before/after audit (LC-A13), the `${CLAUDE_SKILL_DIR}` invocation (LC-A20), one snapshot path with its inputs in config (LC-A18), the README (LC-A21), the rollout example (LC-A17), and a CI-bootstrap section (LC-B4). | These documented commands currently lose work or give false results. | S | P1 |
| LC-C7 | A Figma MCP route: a SKILL.md routing row that says "if `get_variable_defs` is available, read with it"; a `--reverse --format plugin-script` output for `use_figma` that renames "Mode 1", sets `scopes: []` on primitives and sets `codeSyntax.WEB`. | Fixes LC-A7 and LC-B1. Gives automation on the plans most teams actually have. | M | P1 |
| LC-C8 | Hooks: a PreToolUse hook on `Edit\|Write` that blocks files headed "GENERATED — DO NOT EDIT"; a PostToolUse hook with `if: "Edit(**/tokens.css)"` that runs diff_system against the published snapshot and returns the bump and any contrast crossings as `additionalContext`. | Enforces the read-only claim, and catches "we changed a token and something broke" at edit time. | M | P2 |
| LC-C9 | User-invocable workflow skills (`disable-model-invocation: true`): `/wds-migrate-census`, `/wds-release-check` (extract → diff → gate → changelog → guide), `/wds-figma-handoff`, `/wds-docs-check`, each with `allowed-tools` pre-approving its exact Bash command. Plus a read-only `codemod-batch-reviewer` agent that checks each batch against reconciliation.md and the known traps. | Multi-script chains become one reliable command, with the correct paths. | M | P2 |
| LC-C10 | A `claude plugin eval` suite, with a `scaffold_script` for each fixture. Proposed cases: a DTCG 2025.10 export (regex `not_contains "{'"` on the generated file); "is re-pointing `--bg-accent` a patch?" (llm grader: major); "resolve this rebase conflict" (`not_contains --theirs`); a SvelteKit `src/lib` census; "our CSS is a mess" (census before any `--apply`); and trigger cases with sibling-specific `input_match`. | Measures lift over the no-plugin baseline and pins these findings. | M | P2 |
| LC-C11 | Descriptions and token budget. Cut each description from about 820–950 characters to about 350, front-loaded. Scope versioning's triggers ("a codemod, a changelog, a version bump") and docs' triggers ("a docs site", "where is this documented") to design systems, since both currently fire on any library or doc task. Move "How to sell this" (migration SKILL.md:296-348), the worked runs and the anti-pattern tables (repeated almost verbatim in SKILL.md and the references) into references. | About 1.5–2.5k tokens saved per invocation, and less mis-routing. | S | P2 |
| LC-C12 | Ship the 8-file migration fixture and the five-edit release as test fixtures, and have CI regenerate the SKILL.md numbers from them. | The worked examples stop rotting, and they double as eval scaffolds. | S | P3 |

**Hand-off verdict.** The literals → mapping → codemod chain uses consistent names, flags, the `design-token-migration/mapping@1` schema and the 0/1/2 exit codes. The exceptions are that the README is broken and the `--kind` vocabularies differ between extract (`length`, `font-size`) and codemod (`spacing`, `type`); `easing` rules are never applied by the documented loop or the batch order. deprecate → mapping → apply_codemod works for multi-line declarations (LC-A14). extract_system → system.json → build_docs/diff_system works, but the snapshot paths and inputs disagree (LC-A18). Figma export → tokens is where the pipeline breaks (LC-A1 to LC-A4).

## Reviewed

**Files read in full:**
- The 4 SKILL.md files.
- All 11 references: extraction-and-clustering, framework-migrations, migration-strategies, figma-mapping, audit-and-reconcile, documentation-model, extraction, drift-detection, change-classification, deprecation, rollout.
- token-contract.md, which is byte-identical in all 13 skills (md5 checked).
- MIGRATION_PLAN.md, the root README, plugin.json, and the bug-fix report.

**Scripts read where the docs make claims:** the CLIs and the relevant functions of all 9 scripts, plus audit_design's layer-order and baseline code.

**Commands run on the copy:**
- The full migration chain on a 4-file fixture: extract → cluster → dry-run and `--apply` → audit JSON snippets. The documented git-stash command and the rebase recipe were each run on real git repos.
- `figma_to_tokens` in css/all/`--reverse` modes and `figma_audit` on six inputs: plugin, legacy DTCG, 2025.10 DTCG, composed colour, Tokens Studio, and the project accent ramp.
- `extract_system`, `build_docs --check` and `diff_system` on the canonical starter styles (confirming the 11 re-points, 17 layout primitives and 17 limits) and on v1–v4 variant systems.
- `deprecate add`, `scan` and dry runs, feeding the mapping into apply_codemod on two consumer repos.
- `--check-color-impl` (passes), an AST parse for Python 3.9 (all 9 scripts pass), multi-root `PYTHONPATH` chaining (works), and an OKLab recomputation of every ΔE quoted in the references (all correct to ±0.001).

**Sources checked:**
- Figma: REST variables endpoints and types, component endpoints, plugin update 139 (composed colours, 2026-09-17), MCP server tools, mcp-server-guide, Schema 2025 (extended collections are Enterprise-only; mode limits).
- DTCG 2025.10 format and its announcement.
- Tailwind, Bootstrap 5.3.8 dist CSS, MUI native-color, typescript-eslint, git-checkout.
- npm versions of Style Dictionary, sd-transforms and Terrazzo.
- The sibling `claude-code-capabilities.md`, for the plugin-feature facts in LC-C8 to LC-C11.

**Not tested:** the live Figma REST API (Enterprise-only), whether Figma accepts a POST body containing `_comment`, and macOS.
