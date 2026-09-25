# web-design-suite 3.1.0: phase 1 report

**2026-09-24.** Phase 1 of the [review](web-design-suite-review.md), carried out to the [plan](web-design-suite-3.1.0-plan.md). The plugin installed on this machine is now 3.1.0.

## Summary

- **Scope.** Phase 1 is complete. All **28 high-severity issues** and the **9 mediums** scheduled for 3.1.0 are fixed, 37 review items in all.
- **Also fixed.** Seven more review items, three of them only in part. Three problems the review did not list, found during the work.
- **Tests.** The regression suite grew from 72 to **151 tests**. All 79 new tests were run against the unchanged 3.0.1 plugin:
  - 76 fail there and pass on 3.1.0;
  - the other 3 are deliberate controls, which pass on both. They check that a fix did not over-correct, for example that fully tokenised CSS stays clean.

## Where everything is

| What | Where |
|---|---|
| The installed plugin. Sessions load it from this folder, so it must stay here. | `C:\Users\vybec\.claude\local-marketplaces\web-design-suite` |
| Patch, 3.0.1 → 3.1.0 | `C:\Users\vybec\.claude\local-marketplaces\web-design-suite-3.0.1-to-3.1.0.patch`: 78 files (6 of them new), 385,136 bytes, SHA-256 `afef68c4c5fa1fd24cf3e0843756c7353d0a01ac91f4cbc2e87b404c0b5aefc9` |
| Package | `C:\Users\vybec\Downloads\web-design-suite-plugin-3.1.0.zip`: 196 entries (3.0.1 had 190), 1,460,732 bytes, SHA-256 `118fe055a91f82c5765539900026a3d77aad36208dc61c63016a29f8f6ea7017` |
| Release notes | `CHANGELOG.md` in the plugin |
| Plan, with status | [web-design-suite-3.1.0-plan.md](web-design-suite-3.1.0-plan.md) |

## Before you use it

1. **Open a new Claude Code session.** A session that is already running keeps the 3.0.1 skill text it loaded.
2. **Re-baseline projects that use the design gate.** The audit now finds things it used to miss, so a gate that was green may go red on code that was always wrong:
   - a literal written beside a `var()`;
   - spacing inside `@media`, `@container` and `@supports`;
   - `<style>` blocks and `style=""` in HTML, Vue, Svelte and Astro files;
   - literal Tailwind utilities such as `duration-300` and `z-50`.

   To freeze the existing debt, run this from the project root:

   ```bash
   python C:\Users\vybec\.claude\local-marketplaces\web-design-suite\skills\web-design-studio\scripts\audit_design.py src --write-baseline .design-baseline.json
   ```

3. **The claude.ai source may still be 3.0.0.** If it is, a new zip built there would lose both rounds of fixes. Diff it against the two patches before installing it.

To upgrade another copy of 3.0.1, run this from the folder that holds `.claude-plugin`:

```bash
git -c core.autocrlf=false apply C:\Users\vybec\.claude\local-marketplaces\web-design-suite-3.0.1-to-3.1.0.patch
```

## What was fixed

In the tables below:
- the IDs are the review's;
- tests are named `Class.test_…` from the plugin's `tests/` folder;
- "browser" means the test runs in headless Chromium.

### Gates that passed code they never checked

| ID | 3.0.1 | 3.1.0 | Tests |
|---|---|---|---|
| PS-A4 | `audit_design` read HTML as JavaScript, ignored `<style>` and `style=""`, skipped Vue, Svelte and Astro files, and said "all nine laws hold" | Those files are audited. HTML email is routed to `lint_email`. A file it cannot read is skipped and listed. A folder with nothing auditable exits 2. The message names L1–L6. | `AuditPrecision`: `html_style_blocks…`, `single_file_component…`, `files_it_cannot_audit…`, `a_folder_with_nothing_auditable…`, `the_clean_message…` |
| SB-A3 | Any `var()` in a value switched off every raw-value check for that declaration | A literal beside a `var()` is flagged | `a_var_reference_does_not_hide_a_literal…` |
| SB-A4 | Spacing inside `@media`, `@container` and `@supports` was never checked | Checked | `spacing_inside_media_container_and_supports…` |
| SB-A5 | Literal Tailwind utilities (`duration-300`, `z-50`, `bg-accent/37`, `p-(--space-6)`) passed | Flagged by the audit and by the ESLint config | `literal_tailwind_utilities…`, `the_eslint_config_bans_the_same_classes` |
| SS-A19 | A stylesheet saved with a BOM failed as "unlayered" | Read as UTF-8 with or without a BOM | `a_stylesheet_saved_with_a_bom…` |
| XC-A9 | A baseline matched only if the path was spelled the same way | Keys are relative to the baseline file; a missing named baseline is reported | `a_baseline_matches_however…`, `a_named_baseline_that_does_not_exist…` |
| GT-A1 | Runtime contrast parsed `rgb()` only, so the suite's own OKLCH colours were never measured | Any colour syntax is measured | `RuntimeInABrowser.oklch_colours_are_measured` (browser) |
| GT-A2 | A correct modal `<dialog>` was a "keyboard trap", plus 8 more errors; iframes failed the same way | Modals, `inert` and same-origin iframes are handled; axe runs in every frame | `an_open_modal_dialog_is_not_a_trap`, `focus_inside_an_iframe…` (browser) |
| GT-A3 | Per-pixel tolerance 0.10, coarser than the hover (4%) and pressed (8%) overlays | 0.03; every hover, active and focus cell must differ from its default cell | `MatrixSeesStateChanges` ×2 (browser) |
| GT-A4 | The a11y skill's hook snippet had no shebang and no `set -e`; the shipped hook never ran the accessibility check | The shipped hook runs `a11y_static` when it is vendored. All three docs that hand-rolled a hook now point at the shipped one. | `PreCommitHook.the_accessibility_floor_runs…`, `HookGuidance.no_doc_hand_rolls…`, `A11yStaticScaleAndScope.files_named_explicitly…` |
| XC-A6 | `a11y_static` was quadratic: 46 s on a 4,000-row page | Linear: 0.7 s | `a_large_page_is_audited_in_roughly_linear_time` |

### Unsafe defaults

| ID | 3.0.1 | 3.1.0 | Tests |
|---|---|---|---|
| DL-A1 | Credential columns were matched from a short list of exact names | The documented patterns (`*_token`, `*_hash`, `*_secret`, `*_key` and others); such columns are never displayed or editable | `SupabaseSecurityDefaults`: `secret_columns…`, `the_draft_type_leaves…` |
| DL-A2 | Columns that carry authority (`role`, `is_admin`, `owner_id` and others) were editable and in the Draft type | Read-only by default, released only by answering their own question | `authority_columns_are_read_only…`, `a_human_can_release…`, `the_draft_type_leaves…` |
| DL-A3 | The docs' model of how writes fail under RLS was wrong | Corrected: 0 rows with success, and foreign-key and unique checks that bypass RLS; plus how to protect columns | `SupabaseGuidance.the_rls_write_model…` |
| SS-A1 | Density and theme did nothing on a section of the page | Roles are re-declared on `[data-density]` and `[data-theme]` | `StarterStructure` ×2, `StarterInABrowser` |
| SS-A2 | Page colours and `color-scheme` could disagree, putting native fields at 1.12:1 or 1.63:1 | Each theme sets its `color-scheme` | `the_themes_carry_their_colour_scheme`, browser |
| SS-A3 | `[hidden]` lost to layered styles | `display: none !important` | `hidden_beats_every_layer`, browser |
| SS-A4 | Dark error text 4.38:1, `.inverse` headings 1.10:1, control borders 1.51:1 | At least 4.5:1 for text and 3:1 for borders, as measured | `StarterRoleContrast` ×3 |
| SS-A5 | `<dialog>` lost its viewport limit | Kept | `the_dialog_keeps_its_viewport_limit`, browser |
| SB-A1 | The focus ring was a box-shadow, which a component's own shadow replaced | An outline ring | `the_focus_ring_is_an_outline…`, browser |
| SB-A2 | The Tailwind `focus-ring` utility set `outline: none` | An outline ring, in both the v4 utility and the v3 config | `StudioGuidance.no_focus_style_removes_the_outline` |

### Honest output

| ID | 3.0.1 | 3.1.0 | Tests |
|---|---|---|---|
| PS-A1 | The deck's claims were fixed text: "passes", "keyboard-tested by hand", "It is fast" at 152% of budget, "Nine laws" | Every claim is chosen from the data. "Keyboard-tested" appears only when the decision log records it. | `DeckClaimsFollowTheData` ×4 |
| PS-A2 | The defence sheet dropped confirmed defects and kept suspicions | It carries open confirmed defects, labels suspicions, and leaves out fixed ones | `the_defence_sheet_carries…` |
| PS-A3 | An ordinary word ("the most important plan") folded away a rule's findings | Only an explicit claim folds a rule: `covers`, or the rule id in backticks. Every fold is reported. | `an_ordinary_word…`, `a_rule_is_folded_when…` |

### Pipelines

| ID | 3.0.1 | 3.1.0 | Tests |
|---|---|---|---|
| LC-A1 | A DTCG 2025.10 export became invalid CSS (Python dicts), with exit 0 | Reads colour objects, `{value, unit}`, `$ref`, `$extends`, `$root` and group `$type`; values it cannot express are reported | `Dtcg2025` ×4 |
| LC-A2 | Composed-colour opacity (0–100) was read as 0–1, and an alias became a dict | Read as a percentage; the alias is kept through `color-mix()` | `ComposedColours` |
| LC-A3 | The Figma audit hard-coded the studio's palette | `--tokens` checks against the project's own ramps | `ProjectRamps` |
| LC-A4 | A timestamp in every output broke the CI drift check | No clock time; `SOURCE_DATE_EPOCH` stamps a date when one is wanted | `DeterministicOutput` ×2 |
| LC-A5 | A focus ring was rewritten to `--elevation-card` at "snapped" confidence | Mapped to `--elevation-focus` for review; inset rings are left for a person to decide | `FocusRingsStayFocusRings` ×2 |
| LC-A10 | `src/lib` was treated as vendor code and left out without a word | Counted. Exclusions are reported. `--include-vendor` added; files named explicitly are rewritten. | `VendorScopeAndScale` ×3 |
| XC-A7 | `extract_literals` was quadratic on long lines: 12.5 s on 387 KB of minified CSS | Linear, with byte-identical output: 0.83 s on 387 KB, where 3.0.1 took 7.3 s on the same file | `a_minified_stylesheet…` |

### Docs

| ID | 3.0.1 | 3.1.0 | Tests |
|---|---|---|---|
| XC-A1 | The README quick start failed at steps 2–4 | It runs as written | `ReadmeQuickStart` |
| XC-A8 | Every skill said "run from the skill root" | Each SKILL.md shows the by-path command via `${CLAUDE_SKILL_DIR}`, in its first 3,000 characters so it survives compaction | `ScriptInvocation.every_skill…` |
| LC-A6 | The rebase recipe threw away the teammate's change | It keeps the teammate's change | `MigrationRecipes.the_rebase_recipe…` (real git) |
| LC-A13 | The before/after recipe could strand work in the stash | Nothing is left in the stash | `MigrationRecipes.the_before_and_after…` (real git) |
| SB-A6 | The handoff guide described a `build-tokens.mjs` that does not ship | `tokens.css` is the source | `the_handoff_names_no_build_script…` |
| SB-A7 | Said that Tailwind v3 emits native cascade layers | Corrected: v3's utilities come out unlayered | `tailwind_v3_is_not_said…` |

### Also fixed

These are beyond the phase 1 list. Each has its own fail-before test.

| ID | 3.0.1 | 3.1.0 | Tests |
|---|---|---|---|
| SB-A12 | Nine places in five files said an off-scale Tailwind class "is a build error". Tailwind generates nothing for it, silently. `theme.css` also listed `duration-200` as removed, although duration utilities still generate. | Corrected everywhere | `a_missing_tailwind_class_is_not_called_a_build_error` |
| SS-A14 | The default deliverable was a ZIP, even inside the user's repository | Files go into the repository when there is one | `inside_a_repository…` |
| DL-A4 | The optimistic-update sample never threw, so a rejected write got no rollback and no message. The keyset sample pasted the cursor into `.or()` unchecked. | `throwOnError()` plus a zero-rows check; the cursor is validated | `SupabaseSamples` runs both samples in Node against a stand-in for supabase-js |
| XC-A4 | Running a script by path wrote `__pycache__` into the plugin | No bytecode is written | `running_a_script_by_path…` |
| SS-A6 (in part) | Three pattern examples removed the outline | An outline ring | `no_focus_style_removes_the_outline` |
| SB-A10 (in part) | `space-y-related` and `p-(--space-6)` passed | Flagged | `literal_tailwind_utilities…` |
| SB-A16 (a) | A staged README blocked the commit | Skipped | `PreCommitHook.a_staged_readme…` |
| — | `url(icons.svg#add)` was reported as a hardcoded colour | It is not | `a_url_fragment_is_not_a_colour` |
| — | The email quick start copied a template into the plugin, which is replaced on every update | It copies into the project | `the_email_quick_start…` |
| — | The migration's proposed `tokens.css` repeated SS-A1, SS-A2 and SS-A4 | It has the starter's fixes | `ProposedTokensWorkOnASection` ×2, `ProposedTokensContrast` ×3 |

## Evidence

### Test runs

Each run was from the plugin root, with `PYTHONDONTWRITEBYTECODE=1`. `WDS_NODE_MODULES` pointed at the Playwright 1.63 and axe-core 4.13 already in `C:\DEV\audio-promptmonster\frontend\node_modules`, so the browser tests ran too.

| Command | Python | Result |
|---|---|---|
| `python -m unittest discover -s tests` | 3.14.5 | Ran 151 tests in 76.0 s: **OK** |
| `py -3.12 -m unittest discover -s tests` | 3.12.10 | Ran 151 tests in 89.9 s: **OK** |
| The same suite with `WDS_PLUGIN_ROOT` set to an unpacked 3.0.1 | 3.14.5 | Ran 151 tests in 107.9 s: **FAILED (failures=176)**, as intended |

Against 3.0.1:
- 76 of the 79 new tests fail (176 failures counting sub-tests).
- None of 3.0.1's own 72 tests fails.
- These 3 controls pass on both versions:
  - `AuditPrecision.test_fully_tokenised_values_stay_clean`;
  - `AuditPrecision.test_a_clean_page_and_an_html_email_pass`;
  - `PreCommitHook.test_both_gates_must_pass`.

### Other checks

- `audit_design.py skills --strict` on the plugin's own CSS and JS: clean, L1–L6, across 13 files. The 3 email templates are skipped with a pointer to `lint_email`.
- `claude plugin validate --strict` passed, for the marketplace and for `plugin.json`.
- `claude plugin update` moved the plugin from 3.0.1 to 3.1.0. `claude plugin details` lists 13 skills.
- **Patch.** Built from the 3.0.1 zip's contents and the 3.1.0 tree, then applied with `git -c core.autocrlf=false apply` to a fresh extraction of the 3.0.1 zip. `diff -r` against the installed plugin shows no differences.
- **Zip.** Rebuilt with the 3.0.1 zip's layout; `testzip` OK. Extracted, then `diff -r` against the installed plugin: no differences.

### Measured

| Workload | 3.0.1 | 3.1.0 |
|---|---|---|
| `a11y_static`, 4,000-row page | 46 s | 0.7 s |
| `a11y_static`, large page | 2.8 MB: not finished after 180 s | 2.2 MB (20,000 rows): 2.9 s |
| `extract_literals`, 387 KB of minified CSS on one line (6,142 rules) | 7.31 s (the review measured 12.5 s on its own file) | 0.83 s, byte-identical output |

## What was not tested

- **Email clients.** Outlook and Gmail were not tested, and the email skill changed only in its docs.
- **Operating systems.** macOS and Linux were not tested; everything ran on Windows 11. The hook tests ran under Git for Windows' `sh`.
- **Forced colours.** The focus ring is checked to be an outline, in the CSS and in Chromium, but Windows High Contrast (forced-colors) mode itself was not emulated.
- **Linters.** ESLint and stylelint were not run. The new ESLint patterns are checked as regular expressions in Python.
- **Tailwind.** No Tailwind build was run. Which classes generate rests on the review's probe.
- **Figma.** Fixtures only; no live Figma export or REST call.
- **Supabase.** The doc samples ran against a stand-in client that behaves like supabase-js, not against a live project.
- **Browsers.** Headless Chromium only.

## Next: phase 2 (3.2.0)

The roadmap's phase 2 ties the docs to the code:
- a module of tests that check the docs against the code (C3);
- browser and config fixtures (C4);
- `check_roles.py`;
- one shared rule spec;
- the medium-severity doc corrections (A7, A8);
- the evidence register;
- the SKILL.md diet with new descriptions (C12).

Leftovers from this pass that belong there:
- SB-A16 (b)–(e):
  - the hook's default config paths;
  - ESLint's `--no-warn-ignored`;
  - linked worktrees and the bypass log;
  - a cross-file pass that sees only staged files.
- The rest of SB-A10: class helpers such as `cn()` and `cva()`, arbitrary-value classes, and CSS-in-JS.
- The rest of SS-A6: reference CSS examples that fail the gate.
- SB-A17: dependency versions.

Phase 3 (3.3.0) makes it a full Claude Code plugin: the opt-in hook, workflow commands, subagents, the project contract, evals and release tooling. Phase 4 broadens coverage.
