# web-design-suite: the completion plan

**Written 2026-09-25, after 3.2.1, for the agent that does the rest of the work.** It covers everything left:
- the open issues, gaps and improvements from the [review](web-design-suite-review.md);
- what phase 2 and 3.2.1 found along the way.

It is organised as four more phases and fourteen workstreams.

The [inventory](web-design-suite-completion-inventory.md) lists all 265 review items with where each stands. The generator that wrote this plan stopped if any item was left out or placed twice.

## Start here

1. Read the repository's `CLAUDE.md` and `docs/HANDOFF.md`, then this plan.
2. Install the test tools once: `npm ci` in `tooling/main` and in `tooling/tailwind-v3` (`tooling/README.md`).
3. From `plugins/web-design-suite`, run `python -B -m unittest discover -s tests` (`-B`: no bytecode in the plugin). It must report 392 tests OK before you change anything; if it does not, fix that first.
4. Work the phases in order. Inside a phase the workstreams are independent, so take them one at a time and ship the phase as one release.
5. When a workstream is done, update its rows in the inventory: the release, and the test that holds each fix.

### How the work is done (binding)

- **Fail before, pass after.** Every fix gets a regression test, and the test is seen failing on the previous release. Get that release from its tag, `git archive v3.2.1 plugins/web-design-suite | tar --strip-components=1 -x -C <scratch folder>`, and run the suite with `WDS_PLUGIN_ROOT` pointed at the `web-design-suite` folder it unpacks. The 3.1.0 and 3.2.0 reports show how to report it: the fail-before counts, plus the controls and guards that pass on both versions.
- **Reproduce first.** Some items were fixed under another ID (the inventory marks those known). If an item no longer reproduces, record which release fixed it and which test holds it; do not write a fix for it.
- **Read the item in its detail file** (`web-design-suite-review/<area>.md`) before you touch it. The detail files give where, why, and usually how. The tables below carry only the first sentence.
- **Two Python versions.** Before each commit that changes the plugin, run the full suite from `plugins/web-design-suite` on Python 3.14, `uv run --no-project --python 3.14 python -B -m unittest discover -s tests`, and on the floor, the same with `3.9`. The command is the same in cmd, PowerShell and Git Bash.
- **One set of rules.** A change to what a gate accepts goes into `skills/web-design-studio/assets/rules/design-rules.json` first. Then it goes into the audit, the stylelint config and the ESLint config, with a real-tool test in `test_real_tools.py`.
- **Facts from outside the plugin** (laws, standards, vendor limits, prices, dates) are re-read at their source on the day and registered in `tests/fixtures/evidence.json` with their quote.
- **Git.** One branch per phase, conventional commits, and a PR. Tag after the merge. Read the staged diff before every commit: never commit a secret.
- **Where things go.**
  - Plans and reports go in `dev plans/`.
  - Nothing goes in OneDrive or its redirected folders (Documents, Desktop and the rest).
  - The session scratchpad is for throwaway byproducts only.
  - Tests never write into the plugin folder.
- **Cost.** The user is cost-sensitive. Do not fan work out to subagents or workflows unless the user asks. Read one detail file at a time, and keep docs lean.

### Decisions only the user can make

Ask before the phase that needs each one.

1. **Private or public.** *Decided 2026-09-28: public, and MIT-licensed at the root as well as in the plugin.* The repository went public with its own `dev plans/` as it was. That folder and the history name paths on the maintainer's machine (`C:\Users\vybec\…` and session temp folders) and two other projects, `audio-promptmonster` and `Basefra.me`, and every commit carries `info@apmonster.ai`. A scan of every commit found no secrets, and the user chose to leave that material as it is.
2. **Python 3.9** (W4). *Decided 2026-09-25: support 3.9. Done for 3.3.0 (N6).* The floor was 3.10, but the Python that macOS still ships is 3.9; the test harness changes too.
3. **The Tailwind lint plugin** (W12). Stay on eslint-plugin-tailwindcss, which 3.2.1 verified, or move to eslint-plugin-better-tailwindcss as SB-C4 proposes.
4. **Eval spend** (W9). `claude plugin eval` runs real sessions and costs money. Agree a cost cap per run first.
5. **Large downloads.** The user approved downloads for this work on 2026-09-25. Still ask before anything large, such as a browser build or a container image.

## Where things stand

3.2.1 is released (`v3.2.1`, 2026-09-26), and 3.3.0 is in progress on `main`:
- **Tests:** 392, passing on Python 3.9 and 3.14 on Windows. 3.2.1's 339 passed on 3.10 to 3.14.
- **Linux (WSL):** the suite passes with the Node tests skipped, because that Linux has no Node.
- **macOS:** never run.
- **Real tools:** the shipped ESLint config, the stylelint config, both Tailwind blocks of Part 5, Tailwind 4 and tailwind-merge all run in the suite, at the versions pinned in `tooling/`.

| | Total | Fixed | Partly done | Planned here |
|---|---|---|---|---|
| A. Issues | 138 | 83 | 0 | 55 |
| B. Gaps | 52 | 5 | 5 | 42 |
| C. Improvements | 75 | 26 | 5 | 44 |

Open issues: 55 (30 medium, 16 low, 9 low-medium). None is high severity. The two high-severity items left are gaps, DL-B1 and DL-B2, which is why W1 comes first.

---

## Phase 3 · 3.3.0: safe defaults and one set of rules

The Supabase access boundary is the only high-severity work left. And the hook in phase 5 must not run gates that disagree with each other. So this phase fixes both, plus the systems files the gates check.

### W1 · Supabase: the access boundary

The scaffold decides which columns are writable and emits client-only validation. But it says nothing about keys, row-level security or server-side checks.

Target:
- *Done for 3.3.0.* A security pass in `introspect_schema` that reads RLS and policies, and prints a SECURITY block first (DL-C1). `scaffold_ui` repeats the blocking findings and still writes the screens; `--strict` refuses, for CI (the user's decision, 2026-10-01).
- *Done for 3.3.0 (N15, from the review of PR #9).* The reference told readers to revoke `update` on single columns, which Postgres ignores while a table-level grant stands (Supabase's default). The reference and the security pass now say: revoke on the table, grant the columns back.
- *Done for 3.3.0 (N14, found on the way).* The skill's command, `introspect_schema supabase/migrations/*.sql`, failed on more than one file. Several DDL files are now read as one schema.
- A `policies.todo.sql` per table, with a smoke-test stub (DL-B2).
- *Done for 3.3.0.* A rewrite of supabase-integration.md §2, §4 and §6 (DL-C4), with a new §9, "Who talks to the database". It covers which key goes where, the publishable and secret key formats, forwarding the user's token from FastAPI, `search_path` on security-definer functions, and `app_metadata` only.
- *Done for 3.3.0.* Real `db pull` and `gen types` files as fixtures, so the parser is tested on what Supabase emits (DL-C2, DL-B8): the worked example as a migration, a real `pg_dump` of it and its generated types, plus Brewr's real `gen types`. Brewr's real dump is still to add, when the user runs `pg_dump`.

Re-check every Supabase fact at supabase.com on the day, and register it.

| ID | Severity or size | What is wrong or missing |
|---|---|---|
| DL-A5 | medium | unsafe or stale guidance. *Done for 3.3.0.* |
| DL-A6 | medium | the tool cannot see RLS. *Done for 3.3.0.* |
| DL-A7 | medium | Supabase's own schema outputs are silently misread. *Done for 3.3.0.* |
| DL-B1 | high | no data-access boundary. *Partly done: the reference states it (§9); the scaffold does not yet generate `lib/supabase.ts`.* |
| DL-B2 | high | authorization and server validation belong to nobody. |
| DL-B8 | low | unverifiable claims. *Done for 3.3.0.* |
| DL-C1 | M | A security pass in `introspect_schema`: classify sensitive columns, parse RLS and policies, print a SECURITY block first. *Done for 3.3.0.* |
| DL-C2 | M | A sturdier schema parser, tested on real `db pull` and `gen types` files. *Done for 3.3.0.* |
| DL-C4 | S | rewrite supabase-integration.md §2/§4/§6 *Done for 3.3.0.* |

### W2 · One rule spec for all three gates

This is the rest of 3.2.0's item 9, plus what running the real tools found in 3.2.1.

**N1 · The gates disagree.** Measured 2026-09-25 with stylelint 17.15. For each row, decide the rule in `design-rules.json` and make all three gates follow it:

| Construct | audit_design | stylelint config | The spec today |
|---|---|---|---|
| `padding: calc(var(--pad-card) * 1.5)`, a factor on a role token (on a Tier-1 token such as `--space-4` the audit refuses it too, as L6) | accepts | refuses (Law 3: an invented step) | silent |
| `gap: calc(var(--gap-related) * 3)` (on `--space-2` the audit refuses it too, as L6) | accepts | refuses | silent |
| `font-size: 0.75em` | accepts ("`em` as a ratio", README) | refuses ("no `em`") | silent |
| `max-inline-size: 65ch` | accepts | refuses (line length is a spacing decision) | silent |
| Type selectors in component files | accepts | refuses (`selector-max-type: 0`) | silent |
| A hex inside a `var()` fallback | accepts | refuses (`color-no-hex`) | "a fallback is not checked", so stylelint is wrong |
| A margin inside an owl rule in a component file | accepts | refuses the value | the owl is allowed, so stylelint is wrong |
| A CSS system colour outside `@media (forced-colors: active)` (`color: Canvas`) | accepts | refuses (`design/system-colors-in-forced-colors`, 3.2.1) | refused (3.2.1), so the audit is wrong |

**N2 · The rest of item 9.**
- `tools/sync_rules.py --check`, which generates each tool's rule sections from the spec.
- Conformance fixtures from the spec, run through the real audit, ESLint and stylelint. `test_rules_spec` still reads the configs as text.

**N3 · The references' CSS against the stylelint config.** 56 of the 170 CSS snippet files fail it (3.2.1). The failures by rule:
- 27 `selector-max-type`;
- 20 value allowlist;
- 11 `design/layer-order`;
- 9 parse errors, which are fragments;
- 6 `no-descending-specificity`;
- 5 `no-duplicate-selectors`;
- a handful of others.

Add a stylelint snippet test like `DesignEslintConfig.test_the_references_tsx_snippets_pass_the_design_config`. Then fix the snippets or the config, as N1 decides.

**N11 and N12 · found while fixing SB-A9.** The token migration tool keeps its own copies of the audit's scanner helpers.
- **N11.** *Done for 3.3.0.* Its file classes had drifted from the spec: its token-file pattern predated 3.2.0 (four of the spec's six examples missed), and its component test shared SB-A9's `components/` bug. It now uses the audit's patterns, and `test_rules_spec.test_file_classes` holds both copies.
- **N12.** *Done for 3.3.0.* `extract_literals.blank_css_comments` read `//` as a comment in plain CSS, as the audit did (SB-A9 (a)). After `url(https://…)` the census filed the literals that followed under `background`, and the codemod rewrote none of them. It now reads comments as the audit does; `test_token_migration.AddressesAreNotComments` holds it.

**N13 · found while fixing SB-A24.** *Done for 3.3.0.* Sass the scripts could not read.
- **The audit.** The braces of an interpolation (`.card-#{$name}`) closed the layer around them, and indented Sass (`.sass`), which has no braces, passed as clean. The audit now reads an interpolation as text and lists a `.sass` file as skipped.
- **The other scripts.** Three more listed `.sass` and follow braces. On a `.sass` file full of literals (measured 2026-10-01), `extract_literals` reported "no hardcoded design values found" and `a11y_static` reported clean for `outline: none`. Both now say which `.sass` files they did not read (`test_token_migration`, `test_content_and_a11y`). `perf_audit` only weighs the file, which is right.

| ID | Severity or size | What is wrong or missing |
|---|---|---|
| SB-A8 | medium | The canonical `index.css` puts third-party CSS on top of every layer. |
| SB-A9 | medium | The scanner has bugs that hide violations. *Done for 3.3.0; part (d) was SS-A19, fixed in 3.1.0.* |
| SB-A11 | medium | Docs promise checks that don't exist; for example, the audit does not diff `--breakpoint-*` against `--bp-*`. |
| SB-A15 | medium | The stylelint allowlist has holes. |
| SB-A23 | low-medium | The files disagree on how to wrap imports in layers. |
| SB-A24 | low-medium | SCSS: a `@mixin`-only partial fails L5, while `$card-padding: 24px` passes. *Done for 3.3.0, with the Sass rules in the spec (`sass`).* |
| SB-A25 | low | Smaller accuracy points: `url(#fade)` false positive, a zero-specificity warning, a pragma inside a multi-line comment. |
| SB-C1 | S-M | Fix the audit's precision (SB-A3, A4, A9, A10, A24) before wiring the PostToolUse hook. *Done: 3.1.0 did SB-A3, A4 and A10, and 3.3.0 did SB-A9 and A24.* |
| SB-C2 | M · high | Write one machine-readable rule spec plus conformance fixtures, shared by audit_design, stylelint and ESLint. *Partly done: 3.2.0 shipped the spec with tests; the generator and conformance fixtures are left.* |
| SB-C9 | S · medium | Keep one canonical `index.css` per stack (vanilla, modules, Tailwind v4, Tailwind v3) in a single file that every reference points to, with the vendor layer and the forced-colors focus rule built in. |

### W3 · Studio systems: generators, roles and starter files

The generators cannot reproduce the starter's own tokens (SS-A9). The contract still lacks roles the references use: on-status text, an invalid-field border and translucency. And the starter refers to files it does not ship. Regenerate the starter's numbers from the generators and test that they agree (SS-B7).

| ID | Severity or size | What is wrong or missing |
|---|---|---|
| SS-A9 | medium | Type: generate_type_scale.py:26-30 says --snap-px --fluid 380 1440 --fluid-steps 2 reproduces tokens.css "approximately". |
| SS-A17 | low | tokens.css:9 says components never read Tier 1, but the contract allows some primitives (token-contract.md:95). |
| SS-A18 | low | 374-384 says `html:has(:target)` limits smooth scrolling to anchor clicks. |
| SS-B2 | — | Tier-2 roles and starter files are missing. *Partly done: 3.2.0 added the press motion pair and weight access; on-status text roles and the rest are left.* |
| SS-B5 | — | Fluid type and zoom (SC 1.4.4) is only half taught. |
| SS-B6 | — | The brand's exact colour isn't preserved. |
| SS-B7 | — | Nothing tests docs, tokens and generators against each other. *Partly done: 3.2.0 tied docs and tokens; generators against tokens (SS-A9) is left.* |
| SS-C5 | — | Generator upgrades (M, P1). |
| SS-C9 | — | Ship what the starter refers to (S, P1). |
| SB-B4 | — | the contract is missing roles the references need. *Partly done: 3.2.0 added --motion-instant, --bg-scrim and weight access; invalid-border and translucency roles are left.* |

### W4 · Cross-cutting and distribution hygiene

These are from the review:

| ID | Severity or size | What is wrong or missing |
|---|---|---|
| XC-A2 | low | The README's install instructions use a placeholder. |
| XC-A5 | low | `shared/token-contract.md` is referenced by nothing, and its role as the master copy is not stated. |
| XC-B5 | — | The docs are bash-first (backslash continuations, `&&`, `/tmp/`, `$(…)`, `python3`): fine through Git Bash, broken when pasted into cmd or PowerShell 5.1. |
| XC-C9 | S · low | Cross-platform docs: PowerShell/cmd equivalents for the few shell-only recipes, or one `python -m scripts.gate` entry point. |

These were found in phase 2 and 3.2.1:

- **N4.** `accessibility.md` is 60.1 KB, at the limit of one Read. Split it the way 3.2.0 split navigation-patterns.md, and keep `test_skill_budget` passing.
- **N5.** Only the nine scripts that were executable in 3.0.0 are marked executable (the hook is one of them). Mark the other 17 scripts that have a shebang, and add a test that reads git's file modes. Since 3.2.1 the zip builder takes modes from git, so the zip carries them.
- **N6.** *Done for 3.3.0.* Python 3.9 is the floor (decision 2). The harness no longer needs 3.10, `test_docs.PythonFloor` runs `test_harness` on 3.9, and the README states 3.9.
- **N7.** TypeScript 7 is npm's latest, and typescript-eslint 8.70 accepts TypeScript below 6.1. A project that installs typescript-eslint without pinning TypeScript gets a peer conflict. Say so wherever the docs install typescript-eslint.
- **N8.** The plugin README's install section names only a local folder. Add the GitHub route, `/plugin marketplace add Vybecode-LTD/Pro-Web-Designer-Suite-Plug-in`, which anyone can use now that the repository is public.
- **N9.** Add a repository-level check that the root `.claude-plugin/marketplace.json` and the plugin's own agree on name, description, category and keywords.
- **N10.** The review's ✔ marks are stale. The inventory replaces them, so point the review's header at the inventory.

---

## Phase 4 · 3.4.0: runtime gates, lifecycle, email and persuasion

These are the remaining medium and low issues in the other four areas. Each workstream is a set of independent fixes. Read each item's detail paragraph, reproduce it, write the failing test, then fix.

### W5 · Runtime gates

a11y_runtime:
- `bypassCSP`;
- two false measurements;
- axe tag advice that is wrong in both directions;
- hard errors attributed to the wrong success criteria.

snapshot_matrix:
- focus mirroring;
- custom states.

measure_vitals:
- throttle presets that are not Lighthouse's;
- `--interact` adding its own handler to TBT.

SB-B3 adds a focus and forced-colors probe to one of the gates.

| ID | Severity or size | What is wrong or missing |
|---|---|---|
| SB-B3 | — | focus, forced-colors and density aren't checked by any gate in the build flow. |
| GT-A5 | medium | no `bypassCSP`. |
| GT-A6 | medium | the throttle presets are not Lighthouse's, and TTFB is never throttled. |
| GT-A8 | medium | the axe tag advice is wrong in both directions. |
| GT-A12 | medium | rules written with `:focus` or `:focus-within` are mirrored to `[data-force-state~="focus"]`. |
| GT-A13 | medium | only the seven fixed states are allowed. |
| GT-A14 | medium | two measurements give false results (fixture `$W\e11\probes.html`). |
| GT-A16 | low-medium | two rows of the "same method" table cannot be reproduced with that method (TTFB = 4·RTT + 200 ms, minus 300 + 150 ms). |
| GT-A17 | low-medium | `--interact` adds the interaction's own handler to TBT. |
| GT-A18 | low-medium | `multiple-h1`, `heading-skip` and `no-main-landmark` are hard errors attributed to SCs 1.3.1, 2.4.6 and 2.4.1. |
| GT-C2 | S–M · P0 | Fix colour parsing, modals, iframes, inert content, `bypassCSP`, animation pausing and the disabled-control exemption. *Partly done: 3.1.0 did colours, modals, iframes and pausing; A5 and A14 are left.* |
| GT-C3 | M · P0 | Matrix: the within-run "differs from default" gate, a tuned tolerance, focus mirroring, custom states, `data-state="error"` on non-form templates. *Partly done: 3.1.0 did the differs-from-default gate; focus mirroring (A12) and custom states (A13) are left.* |
| GT-C5 | S · P0 | A correction pass on the docs (A7–A10, A16, A19). *Partly done: 3.2.0 corrected A7, A9, A10 and A19; A8 and A16 are left.* |

### W6 · Lifecycle: versioning, migration and Figma

- diff_system's classification errors: density, theme overrides, and conditions.
- The migration docs' promises.
- deprecate.py's colour rename.
- The `--reverse` body.
- LC-C12 ships the migration fixture and the five-edit release as tests, so the worked-run numbers in the SKILL.md files come from them.

| ID | Severity or size | What is wrong or missing |
|---|---|---|
| LC-A8 | medium | The doc says density-scale changes, reduced-motion changes and root-element changes are "major · auto-detect yes". |
| LC-A9 | medium | theme-override-added is classified minor, but it changes rendering in that theme, which is major by the file's own test (§11 Q2: "any theme"). |
| LC-A11 | medium | The reference says a negative cancel must "point at the **same token** the padding uses… Never" point elsewhere. |
| LC-A12 | medium | The docs say "15px … becomes 16 (`--type-body`), not 14. |
| LC-A14 | medium | deprecate.py emits a colour rename. |
| LC-A17 | medium | The model announcement reads "**Design system 2.1.0.** One breaking change: `--bg-accent` moved…". |
| LC-A19 | medium | The doc says "tier1-leak … agree[s] by construction" with audit_design L6. |
| LC-A22 | low | Three problems with the POST body `--reverse` generates. |
| LC-A23 | low | Smaller accuracy and consistency items. |
| LC-B8 | — | claims with no gate. |
| LC-C3 | — | Move the two figma scripts' shared code into `figma_common.py`, and add a parity test for extract_system tier1-leak vs audit_design L6. |
| LC-C4 | — | Add regression tests for LC-A5, A10, A11, A12, A14 and A2, then fix each one: focus-ring detection, the vendor rule, negative-cancel pairing, the type-tie note, the font guard scope, and composed opacity. |
| LC-C5 | — | diff_system: cover density, conditions, `element` and CSS Modules; record `@layer` in system.json; make an added override major when an existing value moves. |
| LC-C6 | — | Instruction fixes: the rebase recipe (LC-A6), a worktree-based before/after audit (LC-A13), the `${CLAUDE_SKILL_DIR}` invocation (LC-A20), one snapshot path with its inputs in config (LC-A18), the README (LC-A21), the ro *Partly done: 3.1.0 fixed the rebase, before/after and invocation recipes; check what else it lists.* |
| LC-C12 | — | Ship the 8-file migration fixture and the five-edit release as test fixtures, and have CI regenerate the SKILL.md numbers from them. |

### W7 · Email and the schema scaffold

- The email templates:
  - the dark-mode call to action;
  - the Outlook font rule;
  - the fluid receipt;
  - authoring notes that ship in the email.
- A dark pass and a no-`<style>` check in `lint_email`, and `render_email.py` (DL-C3).
- The scaffold ignores interview answers and misses promised a11y wiring.
- The Microsoft and Google bulk-sender rules (DL-B7). Re-check them at the source.

| ID | Severity or size | What is wrong or missing |
|---|---|---|
| DL-A8 | medium | interview answers are ignored. |
| DL-A9 | medium | generated forms lack promised a11y wiring |
| DL-A10 | medium | dark mode breaks the call-to-action. |
| DL-A11 | medium | the Outlook font rule is never added. |
| DL-A12 | medium | the receipt isn't fluid. |
| DL-A13 | medium | nothing enforces "Law 1 holds at build time". |
| DL-A14 | low | the inliner isn't "the real cascade" when shorthand and longhand mix. |
| DL-A20 | low | authoring notes ship in the email. |
| DL-A21 | low | Consistency: "same 18 steps" and the email tokens' weight note are wrong. |
| DL-B6 | medium | Checks the docs promise but nothing runs: email dark-mode contrast, the MSO font block, the no-`<style>` layout, source literals, generated-form ARIA. |
| DL-B7 | low | deliverability is dated. |
| DL-C3 | M | Email: fix A10–A12, then add a dark pass and a no-`<style>` check to `lint_email`, and `render_email.py`. |
| DL-C5 | S | `lint_email --source`: flag literals, `var()` fallbacks and dropped tokens. |

### W8 · Persuasion: deck, critique and landing

The deck:
- sends presenter notes to the client in print;
- presents reversed decisions as current;
- and its "Say this" lines break the numbers rule.

PS-C1 makes the deck honest by construction: wording chosen from the data, a `--handout` print, and a presenter window. PS-C2 fixes the critique merge. The rest are doc and reference corrections. Re-check the two legal statements (PS-A9) at the source.

| ID | Severity or size | What is wrong or missing |
|---|---|---|
| PS-A5 | medium | `--a11y` rejects the suite's own accessibility JSON. |
| PS-A6 | medium | The printed deck sends every presenter note to the client. |
| PS-A7 | medium | A reversed decision is presented as current. |
| PS-A8 | medium | The skills give opposite instructions for a risky client request. |
| PS-A9 | medium | Two legal statements are wrong. |
| PS-A10 | medium | The "Say this" lines break the skill's own rule on numbers. |
| PS-A12 | low-medium | The markup breaks the skill's own full-bleed rule. |
| PS-A13 | low-medium | Flaw timing and deck structures contradict the method. |
| PS-A14 | low-medium | The NN/g five-user rule is misapplied to five-second tests. |
| PS-A15 | low | The colour-blindness figure is about half the standard one. |
| PS-A16 | low-medium | Three pieces of reference advice fail on their own terms. |
| PS-A17 | low | The rule to stop at the first blocking finding is too broad. |
| PS-A18 | low | The media accessibility advice is incomplete. |
| PS-A19 | low-medium | The meeting record overstates its legal effect. |
| PS-A20 | low | Counts and structure in design-critique-gate are wrong. |
| PS-A21 | low | Smaller mismatches between docs and behaviour. |
| PS-A22 | low | The header says "SEVEN SECTION SHELLS" but lists eight (:7-13). |
| PS-B5 | — | Checks Claude can't honestly run. |
| PS-B7 | — | Presenting in practice. |
| PS-C1 | — | Make the deck honest by construction: wording from the data, manual-test evidence as input, `--handout`, a presenter window. |
| PS-C2 | — | Fix critique_report: a `covers` field for merges, merge notes in every format, a `status` field. |

---

## Phase 5 · 3.5.0: a full Claude Code plugin (the review's phase 3)

### W9 · The plugin's own components, CI and evals

The gates now tell the truth and agree with each other, so Claude can run them on every edit. Do this phase in this order:

1. **Release engineering and CI first** (XC-C6, GT-C12, XC-B3), so everything after it is tested on every push.
   - A GitHub Actions matrix: Windows, Linux and macOS × Python 3.9 to 3.14, with a Node in ESLint 10's range (20.19+, 22.13+ or 24+).
   - The matrix runs `npm ci` in `tooling/`, the suite, and `claude plugin validate`.
   - A build tool that makes the zip and the 13 `.skill` files reproducibly. It replaces `tooling/release/build_zip.py`.
   - GitHub releases from tags. CI is the only thing that creates a release.
2. **The project contract** (XC-C8, LC-C1, LC-B3). A `.design-suite.json` with token files, component globs, stack, budgets and baselines. A `contract.json` generated from the project's tokens.css replaces the hard-coded ramps and scales.
3. **The opt-in design-gate hook** (XC-C2, SS-C6, LC-C8).
   - A PostToolUse hook on Edit and Write for CSS, SCSS, HTML, JSX and TSX, in exec form so it works on Windows.
   - It does nothing unless the repository opts in, and a `userConfig` switch turns it off globally.
4. **Workflow commands** as skills with `disable-model-invocation: true`: gate, install-gate, new-system, critique, migrate, release-check, figma-sync, tw-probe (XC-C3, LC-C9, PS-C11, GT-C9).
5. **Subagents:** design-critic, gate-runner, supabase-security-reviewer, codemod-batch-reviewer (XC-C4, PS-C4, GT-C9, DL-C7).
6. **The eval suite** (XC-C1, XC-B2, SS-C7, SB-C6, PS-C7, GT-C10, LC-C10).
   - Routing cases, including "must not fire" cases.
   - Outcome cases from the review, run against a no-plugin baseline with a cost cap (decision 4).
   - Cases that run scripts need Bash, which on this machine means WSL2.

`dev plans/web-design-suite-review/claude-code-capabilities.md` has the plugin features with doc links. Re-check them against the current Claude Code docs before building: they change often.

| ID | Severity or size | What is wrong or missing |
|---|---|---|
| XC-B1 | — | The plugin ships only skills: no agents, hooks, commands or MCP/LSP servers, so Law 9 is never applied to Claude's own edits. |
| XC-B2 | — | No eval suite, so nothing shows the skills fire on the right prompts or beat the no-plugin baseline. |
| XC-B3 | — | The tests are regression and guard tests only: no smoke test per documented command, no CI, no declared minimum Python. *Partly done: the Python floor is stated (3.2.1); CI is left.* |
| XC-C1 | L · high | An eval suite (`evals/`): per-skill triggering cases and outcome graders, run with ablation, in CI with a cost ceiling. |
| XC-C2 | M · high | An opt-in design-gate hook: PostToolUse on Edit/Write runs `audit_design` on the changed file and returns the findings to Claude. |
| XC-C3 | M · high | User-invocable workflows as skills with `disable-model-invocation: true`: /gate, /install-gate, /critique, /new-system and more. |
| XC-C4 | M · medium | Subagents (design-critic, a11y-auditor), so heavy references load in an isolated context. |
| XC-C6 | M · medium | Build and release: a build tool for the zip and the 13 `.skill` files, `claude plugin tag`, and a CI matrix of Windows/Linux/macOS × Python 3.9–3.14 with Node. |
| XC-C8 | M · medium | One project config file, `.design-suite.json`, read by every script, the hook and the commands. |
| SS-C6 | — | Use Claude Code plugin features (M, P1). |
| SS-C7 | — | An eval suite of script-graded cases, run against a no-plugin baseline. |
| SB-C6 | M · medium | Add build-half cases to the XC-C1 eval suite: "Tailwind button with loading state", "vanilla card with stretched link", "mega menu", "add a vendor datepicker stylesheet". |
| LC-B3 | — | no way to supply a project contract. |
| LC-B4 | — | no CI bootstrap. |
| LC-C1 | — | Add `contract.json`, emitted by extract_system from the project's tokens.css and read through `--tokens` by figma_audit, figma_to_tokens, cluster_values, audit_design and diff_system. |
| LC-C8 | — | Hooks: block edits to files headed "GENERATED — DO NOT EDIT", and on a tokens.css edit run diff_system and return the bump and any contrast crossings. |
| LC-C9 | — | User-invocable workflow skills (`disable-model-invocation: true`): `/wds-migrate-census`, `/wds-release-check` (extract → diff → gate → changelog → guide), `/wds-figma-handoff`, `/wds-docs-check`, each with `allowed-tool |
| LC-C10 | — | A `claude plugin eval` suite, with a `scaffold_script` for each fixture. |
| GT-C9 | M · P1 | Plugin components: a `gate-runner` agent, an opt-in PostToolUse hook running a11y_static, user-invoked gate skills. |
| GT-C10 | M · P1 | A `claude plugin eval` suite for the gates, run under WSL2. |
| GT-C12 | M · P1 | One CI template for all three gates in a pinned Playwright container, with a baseline-update job and a tested Windows variant. |
| GT-C13 | S · P2 | Vendor the shared runtime helpers into each skill as identical copies, with a test that they match. |
| PS-C4 | — | Add an adversarial critic subagent, `agents/design-critic.md`, that returns `findings.json` from a fresh context. |
| PS-C7 | — | Add an eval suite in `evals/`, scored against a no-plugin baseline. |
| PS-C11 | — | Add a user-invocable chain skill: audit → critique → defence → deck, stopping on blockers. |
| DL-C7 | M | plugin features for these skills. |

---

## Phase 6 · 3.6.0 onward: broader coverage (the review's phase 4)

Each workstream is independent and fits its own release. Do them in the order the user's projects need, and ask which comes first.

### W10 · Tokens and Figma

DTCG 2025.10, Tokens Studio and Style Dictionary through a shared `dtcg.py`. A Figma route for teams without Enterprise, through the MCP server or a plugin script. Figma's mode limits per plan. `light-dark()` theming.

| ID | Severity or size | What is wrong or missing |
|---|---|---|
| SS-B3 | — | Theming without JavaScript. |
| LC-B1 | — | no non-Enterprise route into Figma. |
| LC-B2 | — | Style Dictionary, Tokens Studio and Terrazzo teams get nothing. |
| LC-B6 | — | Figma plan realities. |
| LC-C2 | — | Add a shared `dtcg.py` for 2025.10 read and write, Tokens Studio sets and themes, and `$deprecated` → ledger, plus a `--format dtcg` output. |
| LC-C7 | — | A Figma MCP route: a SKILL.md routing row that says "if `get_variable_defs` is available, read with it"; a `--reverse --format plugin-script` output for `use_figma` that renames "Mode 1", sets `scopes: []` on primitives  |

### W11 · Gate coverage

- Runtime and matrix:
  - single-page apps (`--wait-for`, `--steps`);
  - logged-in pages (`--storage-state`);
  - shadow DOM;
  - several URLs and viewports.
- Accessibility: the cheap automatable checks the coverage table lists but nothing runs.
- Performance: field data (`crux_check.py`).
- Matrix and engines: the matrix model and baseline lifecycle, and engines other than Chromium.

| ID | Severity or size | What is wrong or missing |
|---|---|---|
| GT-B1 | — | SPA and dynamic states. |
| GT-B2 | — | Authenticated pages. |
| GT-B3 | — | Shadow DOM. |
| GT-B4 | — | Multiple URLs and viewports. |
| GT-B5 | — | The field-data loop. |
| GT-B6 | — | Checks the coverage table lists as automatable but that don't exist. |
| GT-B7 | — | The matrix model. |
| GT-B8 | — | The baseline lifecycle. |
| GT-B9 | — | Chromium only. |
| GT-C11 | M · P2 | A `lighthouse` throttle preset, TTFB from CDP, `--interact-at MS`, and `crux_check.py`. |

### W12 · Build coverage

- Tailwind v4: its variants, and a `tw_probe` tool.
- SCSS linting.
- Next.js App Router, Vue, Svelte and Astro.
- Modern CSS: `@starting-style`, the top layer, `cqi`.
- Migration coverage for CSS-in-JS and Sass functions.
- The rollout recipes.
- The audit's speed on large JSX, and SARIF output.
- Decision 3: which Tailwind lint plugin.

| ID | Severity or size | What is wrong or missing |
|---|---|---|
| SS-B4 | — | Modern CSS the systems references should teach: `@starting-style`, the top layer against the z-index ladder, `cqi`, `font-size-adjust`, `color-mix()`. |
| SB-B5 | — | parts of Tailwind v4 aren't covered. |
| SB-B6 | — | SCSS and other stacks. |
| SB-C3 | S-M · high | Ship a `tw_probe` script and a `/tw-probe` skill command. |
| SB-C4 | S · high | Replace Part 5 with eslint-plugin-better-tailwindcss 4.7 (peers ESLint 7–10 and Tailwind 3.3/4.1). |
| SB-C10 | S · low | In `audit_js`, `line_of()` costs O(n) per finding: a 1 MB JSX file with 20k findings took 12.6 s, against 5.1 s for 0.9 MB of CSS with 40k findings. |
| LC-B5 | — | migration coverage. |
| LC-B7 | — | rollout gaps. |

### W13 · Delivery coverage

- Prisma and Drizzle input.
- MJML or React Email output from the email tokens.
- A right-to-left email template.
- A maintainer script that regenerates the email client matrix from caniemail's data.

| ID | Severity or size | What is wrong or missing |
|---|---|---|
| DL-B3 | medium | stacks the description implies but doesn't serve. |
| DL-B4 | medium | email frameworks. |
| DL-B5 | medium | email translation and RTL. |
| DL-C9 | M | Keep the email client matrix honest: regenerate its cells from caniemail's data, with test dates. |

### W14 · Persuasion coverage

- Tables of the UK and EU consumer law to flag for legal review: the DMCC Act, "was" prices, personalised prices, the withdrawal button.
- Persuasive patterns mapped to the WCAG criteria they touch.
- Price experiments.
- More page types.
- Consent for tracking.
- `lint_claims.py`, and critique snapshots that make the "needs a human" checks runnable.

| ID | Severity or size | What is wrong or missing |
|---|---|---|
| PS-B1 | — | Accessibility of persuasive patterns. |
| PS-B2 | — | Consumer law beyond the EU/US basics. |
| PS-B3 | — | Price experiments. |
| PS-B4 | — | Page types and audiences. |
| PS-B6 | — | No claims layer, and siblings don't route to each other. |
| PS-B8 | — | Consent for tracking. |
| PS-C5 | — | Add `critique_snapshots.mjs`: PNGs at 390 and 1440px plus blur, greyscale, mirror, 25%, dark and reduced-motion variants. |
| PS-C6 | — | Add `lint_claims.py`: load-time countdowns, fake scarcity, pre-checked opt-ins, unsourced percentages and the like. |
| PS-C12 | — | Bridge MESSAGE_BRIEF to DECISION_LOG. |

---

## Release procedure (every phase)

1. Write the CHANGELOG entry first, then set the version in `plugins/web-design-suite/.claude-plugin/plugin.json`.
2. Verify:
   - the full suite on Python 3.14 and 3.9, the floor;
   - the fail-before run against the previous tag;
   - Linux through WSL: `wsl -e sh -c "cd /mnt/c/DEV/Pro-Web-Designer-Suite-Plug-in/plugins/web-design-suite && PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests"`;
   - `claude plugin validate --strict` on the repository root, on the plugin folder, and on `plugin.json`.

   Use the desktop app's bundled CLI, `%APPDATA%\Claude\claude-code\<version>\claude.exe`; the one on PATH is older.
3. Write the report as `dev plans/web-design-suite-<version>-report.md`, modelled on the 3.1.0 and 3.2.0 reports. Update the inventory and the `dev plans` README.
4. Build the zip from the merged commit with `python tooling/release/build_zip.py <previous release zip> <out zip> --rev <commit or tag>` (until phase 5 replaces it). It packs only what git tracks, with git's file modes, dated at the commit, so a rebuild is byte-identical; entries keep the previous zip's order, and removed files are listed. It refuses, and writes nothing, if the plugin holds a link or a submodule, or a file `git archive` leaves out. Write the output into `Downloads`, which is not redirected to OneDrive. Then extract the zip into one folder and `git archive` of the same commit into another with `tar --strip-components=1`, so each holds a `web-design-suite` folder, and `diff -r` the two.
5. Open the PR, merge, then tag `vX.Y.Z` on main and push the tag.
6. Update the installed copy.
   - Mirror the release into `C:\Users\vybec\.claude\local-marketplaces\web-design-suite\`, removing files that were deleted: extract the zip from step 4 (or `git archive` of the release commit) and mirror that, never the working folder, which can hold a `__pycache__` or a `node_modules`. That folder is the marketplace that `claude plugin update` installs from, so never move or delete it; sessions load the cached copy the last bullet names.
   - Check it with `diff -r`, then run `claude plugin update web-design-suite@web-design-suite`.
   - Confirm with `claude plugin details web-design-suite@web-design-suite`.
   - Sessions load the plugin from `C:\Users\vybec\.claude\plugins\cache\web-design-suite\web-design-suite\<version>`, and `update` refreshes that folder only when the version changes: it answers "already at the latest version" otherwise. So `diff -r -x .in_use` the cache against the release too, and if a rebuild of the same version left it stale, mirror the release into it as well, keeping `.in_use`. That happened with 3.2.1, first installed from `8b27ff7`.
7. Do the handoff: rewrite `docs/HANDOFF.md`, update the Current State in `CLAUDE.md`, and update the memory note.
