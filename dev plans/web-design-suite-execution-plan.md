# web-design-suite: the execution plan

**Written 2026-10-02, after PRs #12 to #14.** It covers every open item in the [inventory](web-design-suite-completion-inventory.md) and every open N-item in the [completion plan](web-design-suite-completion-plan.md): 145 review items, two of them partly done, and nineteen N-items, ten of them from the reviews of PRs #12 to #15.

The completion plan says what each item needs; this plan says in which PR it gets done, in which order, and how to do it cheaply. Where the two disagree on order, this plan wins. `check_execution_plan.py`, beside this file, fails if an open item is missing from the schedule below or placed twice. Run it after every change to either file.

The user decided on 2026-10-02 to keep phase 6, and asked for the end-all-be-all web development plugin for Claude. Phase 7 is how to go past the review.

---

## 1. What "done" means

The plugin is done when all of these hold:

1. **Every review item is closed.** That means fixed with a test seen failing on the previous release, or closed as "will not do" with the user's agreement, recorded in the inventory.
2. **The three gates agree.** The audit, stylelint and ESLint are generated from one rule spec, and the same conformance fixtures pass through all three real tools.
3. **CI is green on every platform:** Windows, Linux and macOS, on Python 3.9 and 3.14, with the Node tools installed. Today macOS has never run, and Linux runs without Node.
4. **It is a full Claude Code plugin:**
   - skills that route correctly even when the skill listing is crowded;
   - an opt-in gate hook;
   - workflow commands;
   - subagents;
   - an MCP server;
   - an LSP server, if the spike says it can work on Windows.
5. **Evals prove it.** Every skill fires on its routing cases and stays quiet on its "must not fire" cases, and on its outcome cases it beats a no-plugin baseline, within the agreed cost cap.
6. **The docs are true and portable.** Every command works in cmd, PowerShell and bash. Every outside fact is re-read at its source and registered in `evidence.json`. Every quote of starter code is generated from the starter.
7. **It is released and installed:** tagged, released by CI, and mirrored into the local marketplace and the cache.

## 2. Decisions

**All decided by the user on 2026-10-02: yes to every recommendation below, and D5's cap is $15 per full run.**

| # | Decision | Recommendation | Blocks |
|---|---|---|---|
| D1 | **CI replaces the two local full runs.** Today every commit runs the full suite on 3.14 and 3.9 locally, about ten minutes. With CI, a PR runs only the affected tests locally, and the CI matrix runs everything on three platforms before merge. | Yes. It is the biggest saving in the plan, and it adds Linux with Node and macOS. GitHub Actions is free for a public repository. | P1 |
| D2 | **N1, the five rows where the gates disagree and the spec is silent.** Rows 6 to 8 already follow the spec, so only the tools change there. | (1) and (2) refuse a factor on a role token: a scaled token is an invented step (Law 3). `* -1` stays allowed, as the spec already says. (3) refuse `em` font sizes except `1em`, which sizes an icon to its text. (4) refuse a literal `65ch`: use the measure token. (5) refuse type selectors in component files. They belong in `base` or a flow container. | P3 |
| D3 | **Sass in stylelint** (open since 3.3.0). | Yes: ship `postcss-scss`, in P37, so SCSS gets the same three gates. | P37 |
| D4 | **The Tailwind lint plugin** (decision 3 of the completion plan). | Decide inside P36, after a spike that runs both plugins over the same fixtures. Switching replaces Part 5 of the ESLint config, so it is breaking: it goes in a major release. | P36 |
| D5 | **The eval cost cap** (decision 4). | **$15 per full run** (the user, 2026-10-02). A run that would pass it stops first. Routing cases are cheap and run on every release; outcome cases run before each release and when a skill changes. | P29, P30 |
| D6 | **Phase 6's release number.** | 4.0.0, because of D4. | R4 |
| D7 | **Stacked PRs, merged in batches.** | Yes: up to three stacked PRs, merged in order, as #12 to #14. It saves a review round per PR. | all |
| D8 | **Phase 7.** | Approve the method in §7 now; approve each new skill when its evidence is in. | P44+ |

## 3. Why this order: the efficiency rules

1. **Multipliers first.** P1 builds CI and two tools that every later PR uses:
   - `tools/fail_before.py <tests>` unpacks the previous tag, runs only the named tests against it, and prints one table of fail-before and pass-after. It replaces about ten hand-run commands per PR.
   - `tools/check.py` runs the static checks in one command: pointers, snippets, the rule sync from P2, the size budgets, and the affected tests.
2. **The generator before the rules it generates.** P2 makes `design-rules.json` generate each tool's rule sections. After that, each gate fix in P3 to P5 is one spec edit and a regenerate, never three hand edits.
3. **Shared code before its users.** The runtime helpers (P9) come before the three runtime gates, `figma_common.py` (P16) before the Figma fixes, and `dtcg.py` (P31) before the token tools. Each fix is then written once.
4. **One PR per file cluster.** Every item that touches a script lands in the same PR, so no file is read and verified twice. Eight items move across phases for this reason (§5).
5. **Docs corrections per skill.** Reference fixes are batched per skill. The facts in them are re-read in one pass, with one fetch per source.
6. **Releases only at phase ends.** A release costs a session's worth of verification and installation, so there are four.
7. **Infrastructure for phase 5 comes from phase 3.** CI (P1) and the project contract (P24) are what the hook, the commands and the evals stand on.

## 4. The schedule

Size: S is about a quarter of a session, M about a third, L about half. A session is up to 750 thousand tokens, with no compacting (the user, 2026-10-02); the sizes were set against 500 thousand. Each PR follows §6.

### Phase 3 · 3.3.0: safe defaults and one set of rules

PRs #12 to #15 were merged on 2026-10-02. P0 fixes what their reviews found.

| PR | What | Items | Main files | Size |
|---|---|---|---|---|
| P0, #16 | What the reviews of #12 to #15 found: the parser's `$` names, `DROP` and `RENAME COLUMN`, unknown `ADD CONSTRAINT`; the scaffold's schema, reserved words, policy-name length and write-policy roles; the entry's missing sheets; an import or a rule before the layer statement | N16, N17, N18, N19, N20, N21, N22, N23, N24, N25, N29 | `introspect_schema.py`, `scaffold_ui.py`, `audit_design.py`, `stylelint.config.mjs`, `design-rules.json`, `starter/styles/index.css` | M |
| P1, #17 | CI, the release build, and the lean tooling | XC-C6, XC-B3, N5 | `.github/workflows/`, `tooling/release/`, `tools/fail_before.py`, `tools/check.py`, git file modes | L |
| P2, #18 and #19 | The rule spec generates the gates' rule sections, with conformance fixtures through the real tools. #18 is the generator and the data blocks; #19 the value allowlists, ESLint's colour functions and the conformance tests, which found N30 | N2, SB-C2 | `tools/sync_rules.py`, `design-rules.json`, `tests/test_rules_spec.py`, `test_real_tools.py` | M-L |
| P3 part 1, #20 | The gates agree on every example of the spec: N1's eight constructs, and what P2's conformance test found. `KNOWN_DISAGREEMENTS` is empty | N1, N30 | the audit, `stylelint.config.mjs`, `eslint.design.config.mjs`, `design-rules.json` | M |
| P3 part 2, #23 | The holes in the stylelint allowlist, and the two disagreements found in part 1 | SB-A15, N31 | `design-rules.json`, the audit, `stylelint.config.mjs`, `eslint.design.config.mjs` | M |
| P4, #24 | Audit accuracy, the checks the docs promise, its speed on large JSX, and SARIF output | SB-A11, SB-A25, SB-C10 | `audit_design.py` | M |
| P5, #26 | The references' CSS passes stylelint, the Tailwind v3 entry, and the specificity limits in the spec | N3, SB-C9, N32 | `web-design-studio/references/*.md`, `assets/configs/` | M |
| P6 part 1, #28 | The type generator reproduces the starter (`--preset studio`, the default), refuses steps under 11px, and fluid type's zoom bound; SS-A9, SS-B7 and SS-C5's type halves | SS-B5 | `generate_type_scale.py`, `typography.md`, `test_numbers.py` | M |
| P6 part 2, #29 | The colour generator reproduces the starter: the seed anchored, the neutral's lightness and hue, P3, fluid spacing, tested against `tokens.css` | SS-A9, SS-B6, SS-B7, SS-C5 | `generate_color_ramp.py`, `tokens.css`, `test_numbers.py` | M |
| P7 part 1, #31 | The contract's missing roles: the status inks, an invalid-field border and travel distance, in every consumer and the role gate | SB-B4 | `token-contract.md` (14 copies), `tokens.css`, `check_roles.py`, the consumers | M |
| P7 part 2, #32 | The files the starter refers to, the comments the files contradict, and reset.css's scroll behaviour | SS-B2, SS-C9, SS-A17, SS-A18 | `tokens.css`, `reset.css`, starter files | S |
| P8 part 1, #34 | Hygiene: accessibility.md's testing procedure in its own file, the contract's master copy, the two marketplaces held to each other, the review's header, and the vanilla stack's rule 4 | N4, XC-A5, N9, N10, N33 | `accessibility.md`, `token-contract.md` (14 copies), `test_contract.py`, `test_docs.py` | S |
| P8 part 2, #35 | Docs that work in cmd and PowerShell: the GitHub install route, TypeScript pinned beside typescript-eslint, and the shell-only recipes | XC-A2, XC-B5, XC-C9, N7, N8 | READMEs, the references' shell blocks, `evidence.json` | M |
| R1, #36 | Release 3.3.0: the version, the README's install paths and `.skill` files, the CHANGELOG's heading | — | `plugin.json`, `README.md`, `CHANGELOG.md` | S |

### Phase 4 · 3.4.0: runtime gates, lifecycle, email and persuasion

| PR | What | Items | Main files | Size |
|---|---|---|---|---|
| P9, #38 | One copy of the runtime helpers, vendored into each gate, with a test that the copies match; and the release build compares archives by content (N34) | GT-C13, N34 | `a11y_runtime.mjs`, `measure_vitals.mjs`, `generate_matrix.py` and their helpers | S-M |
| P10 part 1, #39 | a11y_runtime: `bypassCSP` where a browser script injects (not in measure_vitals), a crash exits 2, Chrome's one-stop wrap is not a trap, and disabled controls are exempt from contrast; the rest of C2 was done in 3.1.0 and P9 | GT-A5, GT-A14, GT-C2 | `a11y_runtime.mjs`, `snapshot_matrix.mjs`, `measure_vitals.mjs` | M |
| P10 part 2, #40 | a11y_runtime: the focus, forced-colors and density probe, run in the studio's build flow; `--only` refused on a page | SB-B3 | `a11y_runtime.mjs`, web-design-studio's Phase 5 | M |
| P11, #41 | a11y_static's success criteria, a11y_runtime's best-practice findings as warnings (in budgets too), the axe tag advice, and the gate docs' corrections | GT-A8, GT-A16, GT-A18, GT-C5 | `a11y_static.py`, `a11y_runtime.mjs`, a11y and perf references | M |
| P12 part 1, #42 | The snapshot matrix: focus mirroring, custom states and combinations, the error attributes; the differs-from-default gate was done in 3.1.0 | GT-A12, GT-A13, GT-C3 | `generate_matrix.py` | M |
| P12 part 2, #44 | The snapshot matrix's model (RTL, a forced-colors pass, interaction states) and its baseline lifecycle | GT-B7, GT-B8 | `generate_matrix.py`, `snapshot_matrix` | M-L |
| P13 part 1, #45 | measure_vitals: Lighthouse's throttling as the default preset, TTFB from CDP, `--interact` without its own handler, TBT bounded by TTI, and `--interact-at` | GT-A6, GT-A17, most of GT-C11 | `measure_vitals.mjs` | M |
| P13 part 2, #46 | Field data through `crux_check.py`, which finishes GT-C11 | GT-C11, GT-B5 | new `crux_check.py` | S-M |
| P14, #48 | diff_system's classification: density, theme overrides, conditions, `element`, CSS Modules and `@layer` | LC-A8, LC-A9, LC-C5 | `diff_system.py`, `change-classification.md` | M |
| P15 part 1, #49 | The migration tools: the negative cancel, the rounding promise, and the tier-1 claim (the L6 lists in the spec) | LC-A11, LC-A12, LC-A19 | `design-token-migration/scripts/`, `design-rules.json`, `sync_rules.py` | M |
| P15 part 2, #50 | The migration tools, part 2: deprecate.py's colour rename and scan labels, and the fixture and five-edit release as tests | LC-A14, LC-C4, LC-C12 | `design-token-migration/scripts/`, `design-system-versioning/scripts/deprecate.py` | L |
| P16, #53 | The Figma scripts share `figma_common.py`, with a parity test, and `--reverse` builds a correct body | LC-A22, LC-C3 | `figma-variables-sync/scripts/` | M |
| P17, #54 | Lifecycle instructions: the announcement example, the rebase recipe, the before-and-after audit, and claims with no gate | LC-A17, LC-A23, LC-B8, LC-C6 | lifecycle references and SKILL.md files | S-M |
| P18 part 1, #57 | Email templates and build: the dark-mode call to action, the Outlook font rule, the fluid receipt, no authoring notes in the email, and the lint's dark pass that measures them | DL-A10, DL-A11, DL-A12, DL-A20 | `email-template-system/assets/templates/`, `build_email.py`, `lint_email.py` | M |
| P18 | Email lint, part 2: the no-`<style>` check, Law 1 at build time, `render_email.py`, and `lint_email --source` (the dark pass came in part 1) | DL-A13, DL-B6, DL-C3, DL-C5 | `lint_email.py`, new `render_email.py` | M |
| P19 | Email build and facts: the shorthand cascade, the counts, and the bulk-sender rules re-read at the source | DL-A14, DL-A21, DL-B7 | `build_email.py`, email references, `evidence.json` | M |
| P20 | The scaffold reads every interview answer, wires its forms for accessibility, and emits a server schema (pydantic and zod) that mirrors the constraints | DL-A8, DL-A9, DL-B2 | `scaffold_ui.py`, content-model references | M-L |
| P21 | The deck, honest by construction: wording from the data, a `--handout` print without presenter notes, a presenter window, reversed decisions shown as reversed, and the deck's own rules kept | PS-C1, PS-A5, PS-A6, PS-A7, PS-A10, PS-A12, PS-A13, PS-A19, PS-B7 | `client-presentation-builder/scripts/`, its references | L |
| P22 | The critique: merges that carry `covers`, notes and `status`, the right counts, and snapshots that make the "needs a human" checks runnable | PS-C2, PS-A17, PS-A20, PS-A21, PS-B5, PS-C5 | `critique_report`, new `critique_snapshots.mjs` | M-L |
| P23 | Persuasion references and facts: the risky-request rule, the two legal statements, the five-user rule, the colour-blindness figure, the media advice, the section shells | PS-A8, PS-A9, PS-A14, PS-A15, PS-A16, PS-A18, PS-A22 | landing and critique references, `page-sections`, `evidence.json` | M |
| R2 | Release 3.4.0 | — | — | M |

### Phase 5 · 3.5.0: a full Claude Code plugin

Re-read `web-design-suite-review/claude-code-capabilities.md` against the current Claude Code docs before P24: the plugin features change often.

| PR | What | Items | Main files | Size |
|---|---|---|---|---|
| P24 | The project contract: `.design-suite.json`, read by every script, the hook and the commands, and a `contract.json` generated from the project's tokens | XC-C8, LC-C1, LC-B3 | a shared config reader, every script's argument parsing | M |
| P25 | Hooks: the opt-in design gate on Edit and Write, a block on edits to generated files, `diff_system` after a tokens edit, and a `UserPromptSubmit` router that names the right skill when the listing has dropped the descriptions | XC-C2, LC-C8, SS-C6 | `hooks/hooks.json`, `hooks/*.py` | M |
| P26 | Workflow commands and CI bootstrap: gate, install-gate (which writes the CI template for all three gates in a pinned Playwright container, with a baseline-update job), new-system, critique, migrate, release-check, figma-sync, and the audit-to-deck chain | XC-C3, LC-C9, PS-C11, LC-B4, GT-C12 | `skills/<command>/SKILL.md` with `disable-model-invocation: true`, templates | M-L |
| P27 | Subagents: design-critic, gate-runner, supabase-security-reviewer, codemod-batch-reviewer. GT-C9 and DL-C7 close here, and their other parts land with their kind: GT-C9's hook in P25; DL-C7's email-template hook in P25, its schema-to-screens and email-build commands in P26, and its delivery evals in P30 | XC-C4, PS-C4, GT-C9, DL-C7 | `agents/*.md` | M |
| P28 | An MCP server for the gates, `bin/` commands on PATH, and an LSP spike for live diagnostics. Ship the LSP only if it works on Windows | XC-B1 | `.mcp.json`, `mcp/`, `bin/`, `.lsp.json` | M |
| P29 | The eval framework and the routing cases, with "must not fire" cases between sibling skills | XC-C1, XC-B2 | `evals/`, the CI job | M-L |
| P30 | Outcome evals for every area, against a no-plugin baseline: the systems, the build half, the gates, the lifecycle and persuasion | SS-C7, SB-C6, GT-C10, LC-C10, PS-C7 | `evals/<area>/` | L |
| R3 | Release 3.5.0 | — | — | M |

### Phase 6 · 4.0.0: broader coverage

The workstreams are independent. Ask the user which comes first; the order below is the default.

| PR | What | Items | Main files | Size |
|---|---|---|---|---|
| P31 | `dtcg.py`: DTCG 2025.10 read and write, Tokens Studio sets and themes, `$deprecated`, and Style Dictionary and Terrazzo routes | LC-C2, LC-B2 | new `shared/dtcg.py`, token tools | M-L |
| P32 | Figma for every plan: a route without Enterprise, through the MCP server or a plugin script, and each plan's mode limits | LC-B1, LC-B6, LC-C7 | figma-variables-sync | M |
| P33 | Theming without JavaScript: `light-dark()` and `color-scheme` | SS-B3 | starter tokens, theming references | S-M |
| P34 | Runtime coverage: single-page apps (`--wait-for`, `--steps`), logged-in pages (`--storage-state`), shadow DOM, several URLs and viewports | GT-B1, GT-B2, GT-B3, GT-B4 | the three runtime gates | L |
| P35 | The cheap automatable checks the coverage table lists, and engines other than Chromium | GT-B6, GT-B9 | a11y gates, `automation-coverage.md` | M-L |
| P36 | Tailwind v4: its variants, `tw_probe` with a `/tw-probe` command, and the lint plugin (D4) | SB-B5, SB-C3, SB-C4 | `eslint.design.config.mjs` Part 5, new `tw_probe` | L |
| P37 | SCSS in stylelint (D3), and Next.js App Router, Vue, Svelte and Astro | SB-B6 | configs, stack references, fixtures | L |
| P38 | Modern CSS the systems teach: `@starting-style`, the top layer instead of z-index wars, `cqi` | SS-B4 | systems references, starter | M |
| P39 | Migration coverage for CSS-in-JS and Sass functions, and the rollout recipes | LC-B5, LC-B7 | design-token-migration | M |
| P40 | Schema inputs: Prisma and Drizzle | DL-B3 | `introspect_schema.py`, new fixtures | M |
| P41 | Email: MJML or React Email output, a right-to-left template, and a client matrix regenerated from caniemail's data | DL-B4, DL-B5, DL-C9 | email-template-system | L |
| P42 | Persuasion: the UK and EU consumer law to flag for legal review, consent for tracking, price experiments, and persuasive patterns mapped to WCAG | PS-B1, PS-B2, PS-B3, PS-B8 | landing references, `evidence.json` | M-L |
| P43 | More page types and audiences, a claims layer with `lint_claims.py`, routing between the persuasion skills, and MESSAGE_BRIEF to DECISION_LOG | PS-B4, PS-B6, PS-C6, PS-C12 | landing-page-conversion, the deck | L |
| R4 | Release 4.0.0 | — | — | M |

## 5. What moved, and why

Each of these moved into the PR that already has its file open:

| Item | From | To | The shared file |
|---|---|---|---|
| XC-C6, XC-B3 | W9, phase 5 | P1 | CI comes first, so every later PR is tested on three platforms |
| SB-C10 | W12, phase 6 | P4 | `audit_design.py` (`audit_js`) |
| GT-B5, GT-C11 | W11, phase 6 | P13 | `measure_vitals.mjs` |
| GT-B7, GT-B8 | W11, phase 6 | P12 | `generate_matrix.py` |
| PS-C5 | W14, phase 6 | P22 | The critique snapshots are what make PS-B5's checks runnable |
| GT-C13 | W9, phase 5 | P9 | The runtime helpers, before the three gates that use them |

## 6. How each PR is done (the lean protocol)

1. **Read** each item's paragraph in `web-design-suite-review/<area>.md`, by section, never the whole file. If the paragraph shows the item belongs to another PR's files, move it, and update this plan and run the checker.
2. **Reproduce, then write the failing tests.** Run `python tools/fail_before.py <test ids>` (from P1). It prints, per test, the result on the previous tag and now. A test that passes on both is a control, and says so.
3. **Fix**, and run `python tools/check.py`: the static checks and the affected tests, locally, on 3.14.
4. **In the same PR:** the docs, the CHANGELOG entry, the inventory rows (the release and the test that holds each fix), and this plan's progress table.
5. **Commit and push.** The CI matrix runs the full suite on Windows, Linux and macOS, on 3.9 and 3.14 (D1). CI failures get fixed and pushed without asking, as the user set on 2026-10-01. Merging is Claude's too, since 2026-10-03: once CI is green on the PR's head, every review thread is resolved and GitHub reports it clean, never in a way that breaks other pending work (the next session's prompt, §0, has the safe order for a stack).
6. **Facts.** Any figure from outside the plugin is re-read at its source that day and registered in `evidence.json` with its quote. Batch the fetches: one pass per PR.
7. **Stack** up to three PRs (D7). Write the handoff at the end of each session.

Rules that still bind, from the completion plan and `CLAUDE.md`:
- one set of rules (the spec first);
- tests never write into the plugin;
- nothing goes into OneDrive;
- plans and reports go in `dev plans/`;
- read the staged diff before every commit;
- the repository is public.

## 7. Phase 7: past the review

The review measured the plugin against its own claims. "End-all-be-all" means measuring it against what people actually build. The method uses the evals from P29 and P30, so no new skill is a guess:

1. **Probe.** Write about ten realistic web tasks for each candidate area below. Run them with and without the plugin, graded by scripts where possible.
2. **Decide.** An area earns work only where Claude without the plugin falls short of the bar, and the plugin does not close the gap. The user approves each one with that evidence in hand (D8).
3. **Build.** Each approved area goes through the same pipeline as phases 3 to 6: an item in the inventory, a PR, fail-before tests, evals, and a release.

The candidate areas, none of them covered by the review:
- internationalisation and right-to-left layout for web UI;
- motion and interaction design;
- accessible data visualisation;
- forms and validation UX beyond the scaffold;
- component-library interop (shadcn/ui, Radix, Headless UI) with the token contract;
- visual regression across releases;
- security headers and CSP for the pages the gates load;
- images and media (responsive images, AVIF, video);
- offline and installable apps;
- SEO metadata and structured data. Here the plugin should route to the user's installed SEO plugins rather than duplicate them.

## 8. Cost and pace

At the sizes above:

| Phase | PRs | Sessions |
|---|---|---|
| 3 | 9 and a release | about 4 |
| 4 | 15 and a release | about 6 |
| 5 | 7 and a release | about 3.5 |
| 6 | 13 and a release | about 6 |

That is about 19 sessions, before phase 7. It is an estimate: P1 and P2 should make every later PR cheaper, and some phase 4 items will turn out to be one-line doc fixes.

To go faster without spending more per session:
- **Merge in batches** (D7).
- **Let CI do the long runs** (D1).

## 9. Progress

Update this table in each PR.

| Phase | PRs done | Items closed | Release |
|---|---|---|---|
| 3 | #12 to #36 (2026-10-02 to 04): P0 #16, P1 #17, P2 #18 and #19, P3 part 1 #20, and the skill descriptions #21; P3 part 2 #23, P4 #24, P5 #26; P6 part 1 #28 and part 2 #29; P7 part 1 #31 and part 2 #32; P8 part 1 #34 and part 2 #35 | DL-A7, DL-B8, DL-C2, DL-B1, SB-A8, SB-A23, N16 to N29, XC-C6, XC-B3, N5, N2, SB-C2, N1, N30, SB-A15, N31, SB-A11, SB-A25, SB-C10, N3, N32, SB-C9, SS-B5, SS-A9, SS-B6, SS-B7, SS-C5, SB-B4, SS-B2, SS-C9, SS-A17, SS-A18, N4, XC-A5, N9, N10, N33, XC-A2, XC-B5, XC-C9, N7, N8; DL-B2 in part | 3.3.0, released 2026-10-04: #36 merged as `88a4886`, tagged `v3.3.0`, published by `release.yml` |
| 4 | #38 (2026-10-04): P9; #39 (2026-10-05): P10 part 1; #40: P10 part 2; #41: P11; #42: P12 part 1; #44: P12 part 2; #45: P13 part 1; #46: P13 part 2; #48: P14; #49: P15 part 1; #50: P15 part 2; #53: P16; #54: P17; #57: P18 part 1 | GT-C13, N34, GT-A5, GT-A14, GT-C2, SB-B3, GT-A8, GT-A16, GT-A18, GT-C5, GT-A12, GT-A13, GT-C3, GT-B7, GT-B8, GT-A6, GT-A17, GT-C11, GT-B5, LC-A8, LC-A9, LC-C5, LC-A11, LC-A12, LC-A19, LC-A14, LC-C4, LC-C12, LC-A22, LC-C3, LC-A17, LC-A23, LC-B8, LC-C6, DL-A10, DL-A11, DL-A12, DL-A20 | — |
| 5 | — | — | — |
| 6 | — | — | — |
