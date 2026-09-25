# web-design-suite 3.2.0: phase 2 work plan

Phase 2 of [web-design-suite-review.md](web-design-suite-review.md) ties the docs to the code. Most of part A lived in the gap between the references, the starter files, the configs and the scripts. Phase 2 puts tests on that gap, then fixes what the tests find.

Every fix gets a regression test that is **seen failing on 3.1.0 and passing on 3.2.0**. Fail-before runs use `WDS_PLUGIN_ROOT` pointed at a pristine 3.1.0 unpacked from `Downloads\web-design-suite-plugin-3.1.0.zip`, into the session scratchpad at `wds-3.1.0`.

Status is updated at milestones. `[x]` means fixed, tested, and seen failing before.

## Tests on the gap (C3 and C4)

| # | IDs | Work | Status |
|---|---|---|---|
| 1 | SB-C5, SS-C3; closes SS-A6 (rest), SS-A7 | Every CSS, TSX and JSX block in the references passes the audit. Deliberate bad examples carry an explicit `example: wrong` marker. Token blocks are audited as a tokens file. Fix every canonical snippet that fails. | [x] |
| 2 | SS-C4, SS-A7 | One source for shared CSS. Mark regions in base.css and layout.css; `tools/sync_snippets.py --check` keeps the references' quoted copies identical. | [x] |
| 3 | SS-C3; SS-A8 (comment), SS-A15 | Numbers in comments hold: each "Verified n:1" is recomputed, and each `clamp()` anchor is solved. Remove the phantom `generate_space_scale.py`. | [x] |
| 4 | XC-C5; GT-A10 (flags) | Every documented command uses only flags its script's real parser accepts (checked against `--help`). | [x] |
| 5 | DL-C6, DL-A18 | § pointers: every pointer resolves. Each cross-file pointer resolves to the heading it means, via a checked register. Fix the ten known-wrong pointers, including the ones in generated code. | [x] |
| 6 | XC-C5 | The 14 token-contract copies are identical. Every description parses as YAML and stays within its limits. | [x] |
| 7 | C4, SB-A13, SB-A18, SB-A19 | Real-tool fixtures, each skipped when its tool is absent. The tools are ESLint with the design config, a Tailwind v4 compile of theme.css, tailwind-merge with the documented config, and a Chromium check that the focus-ring CAVEAT's recipe keeps the ring visible. They run read-only from projects already on this machine, pointed at by `WDS_ESLINT_MODULES`, `WDS_TAILWIND_MODULES` and `WDS_NODE_MODULES`; nothing is downloaded. stylelint stays unverified (see Decisions). | [x] |

## New tools

| # | IDs | Work | Status |
|---|---|---|---|
| 8 | SS-C2, SS-B1; SS-A8, SS-A13, SB-A21 (a) | `check_roles.py` resolves the Tier-2 roles for light, dark, `.inverse` and dark `.inverse`, then checks a declared pair list (text 4.5:1, UI and focus 3:1). It becomes an opt-in hook stage, and it generates the table in color-system.md §6; a test keeps the doc and the generator equal. The false status-colour claim and the stale fg-subtle figures are corrected. | [x] |
| 9 | SB-C2, SB-A14 | One rule spec, `assets/rules/design-rules.json`, shared by `audit_design`, ESLint and stylelint. `tools/sync_rules.py --check` generates the config sections from it. Conformance fixtures give the expected verdicts: the audit always runs them, ESLint runs them when available, stylelint when available. | [x], reduced; see "Done along the way (item 9)" |

## Corrections found by the review (A7, A8)

| # | IDs | Work | Status |
|---|---|---|---|
| 10 | LC-A18, GT-A11, GT-A15, SB-A13, SB-A17, SB-A18, SB-A19, SB-A20, SS-A12 | Recipes that fail or lose work: snapshot paths, JSONC budgets (and the budget is read before measuring), the CI recipes, the ESLint `style` rule, dependency versions, the tailwind-merge config, the `border-default` collision, four navigation bugs, and the `@property` recipe. | [x] |
| 11 | GT-A10, GT-A7, GT-A9, SS-A11, SS-A13, SB-A21, SS-A16, GT-A19, DL-A15, DL-A16, DL-A17, LC-A7, LC-A16, XC-A3 | Docs that are not true: runtime promises, coverage sources, "Not Evaluated", containment, legal baselines, levels, email-client facts, Figma plans, Bootstrap and MUI, and standalone `.skill` files. | [x] |
| 12 | C5, PS-C10 | Evidence register: each quoted figure with value, source, date checked and quote, plus a test that every statistic in the prose is registered. | [x] |

## Leaner skills (C12)

| # | IDs | Work | Status |
|---|---|---|---|
| 13 | XC-C7, SS-C8, SB-C8, LC-C11, GT-C7, GT-C8, PS-C8, PS-C9, DL-C8, PS-A11, XC-B6 | Each SKILL.md at about 5k tokens or less, with the rules that must survive compaction at the top. Worked examples, CI YAML and tables move to references, and navigation-patterns.md is split. Descriptions of about 350 characters, with a first sentence that works alone and a "Not for" line. Tests enforce all of it. | [x] |

## Leftovers from 3.1.0

| # | IDs | Work | Status |
|---|---|---|---|
| 14 | SB-C7, SB-A16 (b)–(e), SB-A10 (rest) | Hook hardening:<br>• configs resolved at the repo root, and a missing config fails unless `DESIGN_GATE_ALLOW_SKIP=1`;<br>• `--no-warn-ignored`;<br>• `git rev-parse --git-common-dir`;<br>• a bypass trailer;<br>• an optional audit of the staged index content.<br><br>The audit reads class helpers (`cn()`, `cva()`, `clsx()`), arbitrary values and the v4 syntax. | [x] |
| 15 | — | Version 3.2.0, CHANGELOG, patch from 3.1.0, zip, report, memory. | [x] |

## Done along the way (items 1, 2, 6)

The snippet test found conflicts between the docs and the gate, and each was settled in the gate or in the starter, with a test:
- **SS-A10.** `--weight-*` may be read by components: weight has no Tier-2 role, and the hierarchy method needs it.
- **SB-A14, zero.** `margin: 0` is not a child margin.
- **Pseudo-elements.** `::before` and `::after` may space themselves from their own text.
- **Motion longhands.** They may read `--dur-*` and `--ease-*`, since a pair only fits a shorthand.
- **New roles.** `--motion-instant` (press, toggle, check) and `--bg-scrim`. They are in the starter, the deck, the 14 contracts, both Tailwind configs, the migration template, the Figma importer and the email map, and a test now checks every role against every consumer.
- **One prose rhythm, in layout.css.** `.prose` and `.flow` share it; `.prose` moved there, because styling one class from two files is Law 4's two homes. Four docs described four different rhythms; they now quote the one in layout.css. One skip link (the starter's). `.band--sunken` replaces an inline style.
- **Starter fact errors.** The claim that an `overflow: hidden` ancestor clips a box-shadow ring but not an outline is false; both are clipped (measured in Chromium). "Block-level `gap` is shipping" is false. "`in oklch` works wherever `oklch()` does" is false.
- **Doc bugs.** The spring "fallback first" pattern broke with custom properties and is now gated with `@supports`. The focus-ring references taught the old box-shadow "bridge". The Bootstrap binding missed `.btn-primary` (LC-A16, in part).

## Done along the way (item 9)

Item 9 shipped as the spec plus tests, not as a generator:
- There is no `tools/sync_rules.py`, and no config section is generated.
- `test_rules_spec.py` tests the spec against three things: the audit's behaviour, the stylelint config's patterns and globs, and the docs.
- ESLint has no conformance class. `test_real_tools` exercises its style rules.
- stylelint is not installed here, so its conformance comes from reading the config, not from linting fixtures.

## Done along the way (item 10)

Item 10's tests are in `tests/test_recipes.py`. Each takes its commands, workflows, configs or code from the docs themselves.
- **The drift gate compared nothing.** Step 1 wrote `system.json`, while CI read `docs/system.json`, and `build_docs --check` treated a missing baseline as "prose only" and passed. Now there is one baseline (`docs/system.json`) and one input set (`styles/ src/components/`), and a named baseline that does not exist exits 2. The versioning snapshot (`published/system.json`) is a second file on purpose; the docs now say so.
- **Budgets are JSONC.** Both readers accept comments and trailing commas, in UTF-8 or UTF-16. `measure_vitals` reads the budget before it starts a browser.
- **`--report FILE`** is new in `measure_vitals.mjs` and `a11y_runtime.mjs`. It writes the JSON and still prints the readable report, so a CI log shows the failure.
- **The CI workflows:**
  - Node 24 majors: checkout@v5, setup-node@v5, setup-python@v6, cache@v5 and upload-artifact@v6. upload-artifact@v5 is still Node 20. These were read from each tag's action.yml on 2026-09-25; GitHub removed Node 20 on 2026-09-23.
  - `shell: bash` under `defaults`.
  - The server is started, waited for and used in one step.
  - The lockfile's Chromium is installed and cached.
  - Nothing is installed ad hoc.
  - The PR comment has its number, its token and its permission.
- **Versions**, read from the registry on 2026-09-25:
  - stylelint ^17 with config-standard ^40.
  - ESLint ^10 (9 reached end of life on 2026-08-06), plus the jsx-a11y `overrides` entry.
  - eslint-plugin-tailwindcss 4.x for Tailwind v4 (`cssConfigPath`), pinned to 3.x on v3.
  - `WDS_ESLINT_MODULES` now takes a list of roots. The ESLint fixtures pass on 9.39.5 and on 10.4.0, with jsx-a11y rules firing on both.
- **Navigation code**, run in Chromium:
  - the safe triangle re-tests on every look up to its cap;
  - a click keeps a panel that hover opened;
  - the drawer's light dismiss tests where the click landed;
  - `--nav-offset` is registered as a `<length>`;
  - Popover invokers are left to the browser. In Chromium 153 the implicit state wins even over a hand-set attribute, so the review's "a hand-set value overrides it" is not what Chromium does, and the doc does not claim it.
- **`@property`:** a px (computationally independent) initial value, and a root-only socket (`--card-bg`) as the example.
- **Guards vs regressions.** Some checks pass on 3.1.0 because the property they check already held there.
  - DocumentedFlags (item 4) was shown to fail by mutation.
  - The `bash -n` check on workflow steps is a guard test with no fail-before.
  - The sideways-switch check and the browser half of the Popover test are guard assertions inside tests that do fail on 3.1.0, through their other assertions.
- **Still unverified by execution:** stylelint 17 (not installed) and eslint-plugin-tailwindcss 4.x (not installed). Their config text is checked against the registry and README facts only.

## Done along the way (item 11)

Item 11's tests are in `tests/test_facts.py`. Every corrected fact was re-checked at its source on 2026-09-25, and the test's docstring records the source and date. That covers W3C, VPAT 2.5, Deque, ada.gov, ETSI, WebAIM, caniemail's raw data, Microsoft Learn, Google, Postmark, Figma and MUI. Chromium facts were measured in Chromium 153.
- **Code changed, not only docs:**
  - `a11y_runtime.mjs` files horizontal scroll at 200% as a warning, not a 1.4.4 error, and the budget's `reflow_failures` counts errors only.
  - `build_email.py` splits retained CSS over Gmail's ceiling into ~4 KB blocks in authoring order; one block over the ceiling used to lose all of it.
  - The proof sheet's marks now pass 4.5:1 in both themes. The review found one failing mark; measuring found all three.
  - `lint_email.py` names the right clients for flex and grid, says what Gmail removes, cites 2.4.9 for link text as the email skill's chosen floor, and no longer tells transactional mail it needs one-click headers.
- **The review was wrong once, and the doc says what was measured instead.** A hand-set `aria-expanded` on a popover invoker does not override the browser's in Chromium 153 (item 10).
- **Not taken from the review, because it could not be confirmed:** the Figma MCP "Starter: 6 calls a month" limit, and a March 2027 enterprise date for new Outlook. The docs leave both out. The Really Good Emails "May 2027" stays, attributed.
- **New checks with reach beyond their item:**
  - every Contents list is matched to its headings;
  - every tight "N.N.N Level" pairing is matched to WCAG 2.2's levels;
  - every "N of the 55" is matched to the coverage table.

## Done along the way (item 12)

- **The register:** `tests/fixtures/evidence.json`, 15 entries covering GDS 2017, Deque 2021, WebAIM Million 2026, WebAIM survey #10, NN/g 2018, Baymard, Deloitte/Google and the ADA rule. Each entry has the figure, what it measures, source, URL, date checked (2026-09-25) and the source's own words.
- **The test** (`tests/test_evidence.py`):
  - any figure in a sentence that names a source, links out, or says study, survey or report must be registered for that doc, or listed as not a statistic with a reason;
  - a distinctive registered figure is recognised wherever it is quoted;
  - each entry's quote must carry its numbers, and no entry may outlive its figure.
- **What checking the figures found:**
  - Baymard's page says 14.88 form fields against an ideal of 7–8, not 11.3 against ~8. Fixed.
  - The Apple MPP range had no source; the numbers are gone.
  - "~30–40% of the criteria" was the barriers-versus-criteria confusion again; fixed, and item 11's test now catches that form too.
- **Limit, stated:** an unattributed figure that is not already registered cannot be told apart from an ordinary number, so it is caught only when its sentence names a source.

## Done along the way (item 13)

- **Budgets, measured and not guessed.**
  - `claude plugin details` measured a 28.3 KB SKILL.md at ~6,600 tokens, so 5,000 tokens is ~21,500 bytes, and every SKILL.md now fits (largest 20,949).
  - The Read tool stopped navigation-patterns.md at line 611 of 755 (~61 KB). The file is now split in two, `navigation-patterns.md` (the catalog, 52.7 KB) and `navigation-code.md` (15.8 KB), and every reference must stay under 60.5 KB.
  - accessibility.md is at 60.1 KB, just under that line: split it before it grows.
- **Nothing was deleted.** The large sections moved verbatim into references as numbered sections, with a one-line pointer left behind:
  - a11y and versioning: `references/scripts.md`;
  - migration: `worked-run.md` and `selling-the-migration.md`;
  - content-model: `worked-example.md`;
  - email: `email-workflow.md` §10;
  - perf: `diagnosis.md` §12;
  - docs: `documentation-model.md` §13;
  - landing: `page-architecture.md` §8, `copy-patterns.md` §12, `conversion-audit.md` §11 and §12.

  The pointer register went from 290 to 300 entries, all checked.
- **Landing page (PS-A11).**
  - Ethics and evidence now come straight after the one principle, before the workflow.
  - The legal detail moved to a reference.
  - The quoted figures live once, in conversion-audit.md.
- **Descriptions** are 301–368 characters, down from 776–955. Each leads with a standalone first sentence (at most 200 characters) and says what the skill is not for, naming the sibling to use instead.
- **A mover bug, caught and repaired.** My section mover took a `# comment` in a shell block for a heading and truncated the worked run. The run was reassembled, the mover now skips fenced code, and every fence in the suite was checked for balance.

## Done along the way (item 14)

- **The hook**, driven for real in a scratch repo, a linked worktree and a real `git commit`:
  - configs are found at the repo root first, then in `assets/configs/`;
  - a stage that cannot run fails unless `DESIGN_GATE_ALLOW_SKIP=1`;
  - ESLint gets `--no-warn-ignored`;
  - the log goes in the common git directory;
  - the same script installed as the commit-msg hook writes a `Design-Gate-Bypass: <reason>` trailer;
  - `DESIGN_GATE_INDEX=1` audits the staged content through `git checkout-index`.

  The docs that install the hook now install both hooks.
- **The audit (SB-A10 rest).**
  - It reads class strings in `cn`, `clsx`, `classNames`, `cva`, `tv`, `twMerge`, `twJoin` and `cx` calls.
  - It refuses every arbitrary value except arbitrary variants, image URLs and pseudo-element content strings.
  - It flags arbitrary properties and the v4 `!` suffix.
  - It audits styled-components and emotion template bodies as component CSS, at their own lines, with interpolations standing in as `var()`.
  - On the review's two fixtures it goes from 2 findings to 12.
  - Deliberately out of reach: `style={box}`, an object passed by name, which ESLint cannot see either; and a literal custom property set inline, which ESLint allows too.
  - One reference block the audit could now see was a migration "before" example and got its marker.
- **Stage 3 of the hook now fails** when `scripts/audit_design.py` is not vendored. That is the point of (b), and it will stop commits in repos that installed the hook without the audit. It is called out in the CHANGELOG.

## Decisions taken by default

- **stylelint** is not installed anywhere on this machine. Its config is checked by reading it, not by running it. Installing it means a download, so I will ask first.
- **The caniemail regeneration (DL-C9)** needs a data download, so it is deferred. DL-A15's specific cells are corrected from caniemail's published pages.
- **GT-A10.** The docs are corrected to say exactly what the runtime does. New runtime checks belong to phase 4 (C15). The one code fix: horizontal scroll at 200% zoom is no longer filed as a 1.4.4 error.
- **§ pointers.** Every pointer must resolve. Cross-file pointers are checked against a register of the heading each one means; same-file pointers are checked only for existence.
- **Evidence register scope.** Figures quoted from studies, surveys and vendors in the prose. Contrast ratios are computed (items 3 and 8), not registered.

## Not in phase 2

The remaining A1–A6 and A9 mediums, such as GT-A5, GT-A8, GT-A12, GT-A14, GT-A17, SB-A8, SB-A9, SS-A9, SS-A10, LC-A8 and PS-A6 to PS-A10, are not in the roadmap's phase 2. An item's test may still flag one of them. If it does, it gets fixed here and is listed in the report.
