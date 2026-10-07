# web-design-suite: the completion plan

**Written 2026-09-25, after 3.2.1, for the agent that does the rest of the work.** It covers everything left:
- the open issues, gaps and improvements from the [review](web-design-suite-review.md);
- what phase 2 and 3.2.1 found along the way.

It is organised as four more phases and fourteen workstreams.

The [inventory](web-design-suite-completion-inventory.md) lists all 265 review items with where each stands. The generator that wrote this plan stopped if any item was left out or placed twice.

## Start here

1. Read the repository's `CLAUDE.md` and `docs/HANDOFF.md`, then this plan.
2. Install the test tools once: `npm ci` in `tooling/main` and in `tooling/tailwind-v3` (`tooling/README.md`).
3. From `plugins/web-design-suite`, run `python -B -m unittest discover -s tests` (`-B`: no bytecode in the plugin). It must report 406 tests OK before you change anything; if it does not, fix that first.
4. Work the phases in order. Inside a phase the workstreams are independent, so take them one at a time and ship the phase as one release.
5. When a workstream is done, update its rows in the inventory: the release, and the test that holds each fix.

### How the work is done (binding)

- **Fail before, pass after.** Every fix gets a regression test, and the test is seen failing on the previous release. Get that release from its tag, `git archive v3.2.1 plugins/web-design-suite | tar --strip-components=1 -x -C <scratch folder>`, and run the suite with `WDS_PLUGIN_ROOT` pointed at the `web-design-suite` folder it unpacks. The 3.1.0 and 3.2.0 reports show how to report it: the fail-before counts, plus the controls and guards that pass on both versions.
- **Reproduce first.** Some items were fixed under another ID (the inventory marks those known). If an item no longer reproduces, record which release fixed it and which test holds it; do not write a fix for it.
- **Read the item in its detail file** (`web-design-suite-review/<area>.md`) before you touch it. The detail files give where, why, and usually how. The tables below carry only the first sentence.
- **Two Python versions.** Before each commit that changes the plugin, run the full suite from `plugins/web-design-suite` on Python 3.14, `uv run --no-project --python 3.14 python -B -m unittest discover -s tests`, and on the floor, the same with `3.9`. The command is the same in cmd, PowerShell and Git Bash. *From P1 of the execution plan on (D1, 2026-10-02), CI runs the full suite on Windows, Linux and macOS, on both Pythons, on every push. A PR then runs only its affected tests locally.*
- **CI (decision D1).** In force once CI is green on all six jobs of PR #17: CI then runs the full suite on Windows, Linux and macOS, at Python 3.9 and 3.14, for every PR, and replaces the two local full runs. Locally, run `python tools/check.py` (the static checks and the affected tests) and `python tools/fail_before.py <test ids>` (the fail-before table, against the latest tag or `--rev`).
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
3. **The Tailwind lint plugin** (W12). Stay on eslint-plugin-tailwindcss, which 3.2.1 verified, or move to eslint-plugin-better-tailwindcss as SB-C4 proposes. *Decided 2026-10-02: a spike in P36 of the execution plan decides, with both plugins run over the same fixtures. A switch goes in 4.0.0.*
4. **Eval spend** (W9). `claude plugin eval` runs real sessions and costs money. Agree a cost cap per run first. *Decided 2026-10-02: $15 per full run.*
5. **Large downloads.** The user approved downloads for this work on 2026-09-25. Still ask before anything large, such as a browser build or a container image.

## Where things stand

3.2.1 is released (`v3.2.1`, 2026-09-26), and 3.3.0 is in progress on `main`:
- **Tests:** 406, passing on Python 3.9 and 3.14 on Windows. 3.2.1's 339 passed on 3.10 to 3.14.
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
- *Done for 3.3.0.* A `policies.todo.sql` per table, with a smoke test that runs on a real Postgres in the suite (DL-B2), and the generated `lib/supabase.ts` (DL-B1).
- *Done for 3.3.0.* A rewrite of supabase-integration.md §2, §4 and §6 (DL-C4), with a new §9, "Who talks to the database". It covers which key goes where, the publishable and secret key formats, forwarding the user's token from FastAPI, `search_path` on security-definer functions, and `app_metadata` only.
- *Done for 3.3.0.* Real Postgres and Supabase output as fixtures, so the parser is tested on what they emit (DL-C2, DL-B8): the worked example as a migration, a real `pg_dump` of it made with the flags `supabase db pull` uses (a test applies the CLI's own edits to it), its generated types, and Brewr's real `gen types`. There is no `db pull` file itself (N28). A real dump of Brewr was dropped: the user has no password for its database.

Re-check every Supabase fact at supabase.com on the day, and register it.

| ID | Severity or size | What is wrong or missing |
|---|---|---|
| DL-A5 | medium | unsafe or stale guidance. *Done for 3.3.0.* |
| DL-A6 | medium | the tool cannot see RLS. *Done for 3.3.0.* |
| DL-A7 | medium | Supabase's own schema outputs are silently misread. *Done for 3.3.0.* |
| DL-B1 | high | no data-access boundary. *Done for 3.3.0: the reference (§9) and the generated `lib/supabase.ts`.* |
| DL-B2 | high | authorization and server validation belong to nobody. *Partly done for 3.3.0: per-table policies, grants and a smoke test; a server-side schema mirroring the constraints is left.* |
| DL-B8 | low | unverifiable claims. *Done for 3.3.0.* |
| DL-C1 | M | A security pass in `introspect_schema`: classify sensitive columns, parse RLS and policies, print a SECURITY block first. *Done for 3.3.0.* |
| DL-C2 | M | A sturdier schema parser, tested on real `db pull` and `gen types` files. *Done for 3.3.0.* |
| DL-C4 | S | rewrite supabase-integration.md §2/§4/§6 *Done for 3.3.0.* |

### W2 · One rule spec for all three gates

This is the rest of 3.2.0's item 9, plus what running the real tools found in 3.2.1.

**N1 · The gates disagree.** *Done for 3.3.0 (PR #20): every row follows the spec in all three gates, and each is an example the conformance tests run.* Measured 2026-09-25 with stylelint 17.15. For each row, decide the rule in `design-rules.json` and make all three gates follow it. *Decided 2026-10-02 (execution plan D2): rows 1 and 2 refuse a factor on a role token, and `* -1` stays allowed; row 3 refuses `em` font sizes except `1em`; row 4 refuses a literal `ch` measure in favour of the measure token; row 5 refuses type selectors in component files. Rows 6 to 8 follow the spec.*

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

**N2 · The rest of item 9.** *Done for 3.3.0 (PRs #18 and #19).*
- `tools/sync_rules.py` writes the spec's data into one marked block in each gate, and `--check` runs in `check.py` and CI. The audit gets the layer order and statement, the nesting depth and the colour functions. The stylelint config gets those it uses, the system colours, the value shapes, the keywords, the colour words, the allowlists of 43 properties in eight families, and the component margins. The ESLint config gets the colour functions, for its raw-colour rule and its inline-style rule. Why each family takes what it takes moved from the config's comments into the spec (`values.families.*.why`).
- Each section of the spec names the gates that enforce it (`gates`). One builder turns every `allowed` and `refused` example into a file, and the audit (`test_rules_spec`), stylelint and ESLint (`test_real_tools`) must give the spec's verdict on each. Where one does not yet, `KNOWN_DISAGREEMENTS` names the item that fixes it, and the test fails once the gate agrees. The tests that read the stylelint config as text are gone.

**N30 · What the conformance test found (P2).** *Done for 3.3.0 (PR #20), with N1: `KNOWN_DISAGREEMENTS` is empty.* The audit gave the opposite verdict on seven of the spec's examples that neither N1 nor SB-A15 lists. Each is in `KNOWN_DISAGREEMENTS`:
- `transition-duration: 0s` is refused as a literal duration, though the spec and stylelint allow `0s`;
- `.card *` in a component file passes, though stylelint refuses it (`selector-max-universal`);
- `font-size: 1.125rem` passes: the type check skips any length ending in "em", and "rem" does;
- `color: red` is only a warning (`named-color`), so a run without `--strict` passes it;
- `max-width: 600px` passes: the audit reads no sizing property;
- a design literal in an inline custom property (`style={{ '--gap': '12px' }}`, or a colour function) passes, though ESLint refuses it.

**N31 · Found while closing N1 (P3 part 1).** *Done for 3.3.0 (PR #23): `0` among tokens is allowed, a share of the container is refused in both gates, a component may space its own `::before` and `::after`, and the audit's `prose` exemption is gone.* The two disagreements, as they were found, outside the spec's examples:
- **A literal `0` among tokens.** `padding: 0 var(--pad-card)` passes the audit, and the spec's zero rule allows it, but stylelint's `VAR_SEQ` takes only `var()`s and refuses it; so do `gap` and `border-radius`. Likewise `calc(100% - var(--gutter-page))` in a spacing property: stylelint takes no calc() but a token plus or minus a token, and the audit passes it.
- **Margins the audit exempts.** The audit lets a component set a margin on its generated content (`.card::before`) and in a rule whose selector names `prose`. `design/component-margins` refuses both, and the spec says neither.

**N32 · The specificity limits are not in the spec (CodeRabbit on #24).** *Done for 3.3.0.* The audit's `compound-specificity` (four chained classes, outside `:where()`) and stylelint's `selector-max-specificity: '0,3,1'` and `selector-max-compound-selectors: 3` were each written into their gate by hand, and no example held the two gates to each other.
- `design-rules.json: selectors` now holds both limits, 0,3,1 and three compound selectors, with eight allowed and six refused examples, run through the audit and the real stylelint. `tools/sync_rules.py` writes the limits into both gates.
- The audit weighs a selector as Selectors 4 and stylelint do: `:where()` scores zero, `:is()`, `:not()` and `:has()` their heaviest argument, and a nested rule's `&` its parent's. `compound-specificity` is an error now, as stylelint's is, and the new `compound-selectors` counts compounds as stylelint 17 does.
- They did not agree on `:where()`: stylelint counts the compounds inside it, so it refuses `:where(.a .b .c .d)`. The spec sides with it, since `:where()` takes away the weight but not the knowledge of the DOM. `:where(.a.b.c.d)` is allowed.
- stylelint also counts the `+` of an An+B (`:nth-last-child(n + 5)`) as a combinator; the audit does not. The spec says so, and the starter's and layout-composition's quantity queries keep their disable comment.

**N33 · The vanilla stack's naming rule 4 (found in P7).** *Done for 3.3.0 (PR #34): `test_contract.TheStarterKeepsItsWord.test_the_vanilla_stack_names_the_starters_primitives`.* stack-vanilla-css.md's rule 4 prefixed the layout primitives `.l-stack`, `.l-grid` and `.l-center`, and the starter's layout.css defines `.stack`, `.grid` and `.center`.

**N34 · The release build is byte-identical only with the same zlib (found in R1).** *Done for 3.4.0 (PR #38): `tooling/release/compare.py`, held by `test_release_build`.* `tooling/release/build.py` says two builds of one commit are the same, byte for byte. On 2026-10-04 the local build of `88a4886` and `release.yml`'s differed in every checksum: the names, order, dates, modes and CRCs of all 14 archives matched, and 187 of 190 files compressed to other sizes, because Windows' Python 3.14 deflates with zlib-ng (`1.3.1.zlib-ng`) and the CI's with zlib. Say so in the builder, and give it a comparison by content (names, CRCs, uncompressed sizes, dates, modes), so R2's check compares what matters.

**N35 · Law 6 is enforced only by the audit (found in P15).** `audit_design.py` reads Law 6 (semantic before primitive: a component reads a role, never a ramp step) from design-rules.json's `tiers`, but neither the stylelint config nor the ESLint config checks it, so a project that gates with them alone lets `var(--accent-600)` into a component. Add the rule to both gates the way the spec's other data reaches them (`tools/sync_rules.py`), with the spec's `tiers` examples run through each (`test_rules_spec`, `test_real_tools`).

**N36 · Gmail's byte limits are unregistered (CodeRabbit on #59).** The email docs and both email scripts quote Gmail's 102,400-byte clipping threshold and its 16,384-byte `<style>` ceiling, and neither is in `tests/fixtures/evidence.json`; test_evidence's `FIGURE` pattern does not recognise a byte count, so nothing asks for one. Re-read each at its source, register it with its quote for every doc that quotes it, and teach `FIGURE` byte counts (without catching unrelated numbers). If no authoritative source supports a limit, qualify the claim.

**N3 · The references' CSS against the stylelint config.** *Done for 3.3.0.* 56 of the 170 CSS snippet files failed it at 3.2.1. The failures by rule:
- 27 `selector-max-type`;
- 20 value allowlist;
- 11 `design/layer-order`;
- 9 parse errors, which are fragments;
- 6 `no-descending-specificity`;
- 5 `no-duplicate-selectors`;
- a handful of others.

Measured again after P3: 28 of 159 blocks failed, and 9 more are fragments (`{ … }` outlines). `StylelintConfig.test_the_references_css_snippets_pass_the_config` now lints every block in the files the audit puts it in, and counts the fragments. What changed:
- **The references,** where the spec refuses what they showed. A box-shadow bar and a radius formula go through a socket. A `0px` and a `#ffffff` are gone. A view transition's pseudo-elements are styled in `base`. Rules that broke `no-descending-specificity` were reordered, and a selector over the cap uses `:where()`. Side-by-side alternatives are split into blocks of their own, and the anti-examples are marked.
- **Escape hatches** that named only the audit now name stylelint too, in the one comment both read.
- **The test's placement** (`test_doc_snippets.as_files`, which the audit's snippet test shares): `@font-face` lives with the tokens, a Tailwind `@theme` in `theme.css`, CSS Modules' syntax in a `.module.css`, and a block's other layers in their own files.
- **The config,** where the spec allows what it refused. Sub-layers inside a canonical layer (`@layer components { @layer base, skin; }`, as stack-vanilla-css teaches) are now a spec example; the rule had read the nested statement as the file's own. CSS Modules' `composes` and `:global` are known words.
- **SB-C9's v3 entry** replaced the last inline entry, the one the remaining `@import` failures came from.

**N11 and N12 · found while fixing SB-A9.** The token migration tool keeps its own copies of the audit's scanner helpers.
- **N11.** *Done for 3.3.0.* Its file classes had drifted from the spec: its token-file pattern predated 3.2.0 (four of the spec's six examples missed), and its component test shared SB-A9's `components/` bug. It now uses the audit's patterns, and `test_rules_spec.test_file_classes` holds both copies.
- **N12.** *Done for 3.3.0.* `extract_literals.blank_css_comments` read `//` as a comment in plain CSS, as the audit did (SB-A9 (a)). After `url(https://…)` the census filed the literals that followed under `background`, and the codemod rewrote none of them. It now reads comments as the audit does; `test_token_migration.AddressesAreNotComments` holds it.

**N13 · found while fixing SB-A24.** *Done for 3.3.0.* Sass the scripts could not read.
- **The audit.** The braces of an interpolation (`.card-#{$name}`) closed the layer around them, and indented Sass (`.sass`), which has no braces, passed as clean. The audit now reads an interpolation as text and lists a `.sass` file as skipped.
- **The other scripts.** Three more listed `.sass` and follow braces. On a `.sass` file full of literals (measured 2026-10-01), `extract_literals` reported "no hardcoded design values found" and `a11y_static` reported clean for `outline: none`. Both now say which `.sass` files they did not read (`test_token_migration`, `test_content_and_a11y`). `perf_audit` only weighs the file, which is right.

| ID | Severity or size | What is wrong or missing |
|---|---|---|
| SB-A8 | medium | The canonical `index.css` puts third-party CSS on top of every layer. *Done for 3.3.0.* |
| SB-A9 | medium | The scanner has bugs that hide violations. *Done for 3.3.0; part (d) was SS-A19, fixed in 3.1.0.* |
| SB-A11 | medium | Docs promise checks that don't exist; for example, the audit does not diff `--breakpoint-*` against `--bp-*`. *Done for 3.3.0 (PR #24).* |
| SB-A15 | medium | The stylelint allowlist has holes. *Done for 3.3.0 (PR #23); SCSS in stylelint is P37's.* |
| SB-A23 | low-medium | The files disagree on how to wrap imports in layers. *Done for 3.3.0.* |
| SB-A24 | low-medium | SCSS: a `@mixin`-only partial fails L5, while `$card-padding: 24px` passes. *Done for 3.3.0, with the Sass rules in the spec (`sass`).* |
| SB-A25 | low | Smaller accuracy points: `url(#fade)` false positive, a zero-specificity warning, a pragma inside a multi-line comment. *Done for 3.3.0 (PRs #23 and #24).* |
| SB-C1 | S-M | Fix the audit's precision (SB-A3, A4, A9, A10, A24) before wiring the PostToolUse hook. *Done: 3.1.0 did SB-A3, A4 and A10, and 3.3.0 did SB-A9 and A24.* |
| SB-C2 | M · high | Write one machine-readable rule spec plus conformance fixtures, shared by audit_design, stylelint and ESLint. *Done for 3.3.0 (N2): 3.2.0 shipped the spec, and 3.3.0 the generator and the conformance tests.* |
| SB-C9 | S · medium | Keep one canonical `index.css` per stack (vanilla, modules, Tailwind v4, Tailwind v3) in a single file that every reference points to, with the vendor layer and the forced-colors focus rule built in. *Done for 3.3.0: vanilla and modules (`starter/styles/index.css`), Tailwind v4 (`configs/index.tailwind.css`) and Tailwind v3 (`configs/index.tailwind-v3.css`).* |

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

- **N4.** *Done for 3.3.0 (PR #34): §10, the testing procedure, is `accessibility-testing.md` (8.5 KB), and accessibility.md is 52,963 bytes; `test_skill_budget` and the pointer register hold both.* `accessibility.md` is 60.1 KB, at the limit of one Read. Split it the way 3.2.0 split navigation-patterns.md, and keep `test_skill_budget` passing.
- **N5.** *Done for 3.3.0 (PR #17).* Only the nine scripts that were executable in 3.0.0 are marked executable (the hook is one of them). Mark the other 17 scripts that have a shebang, and add a test that reads git's file modes. Since 3.2.1 the zip builder takes modes from git, so the zip carries them.
- **N6.** *Done for 3.3.0.* Python 3.9 is the floor (decision 2). The harness no longer needs 3.10, `test_docs.PythonFloor` runs `test_harness` on 3.9, and the README states 3.9.
- **N7.** *Done for 3.3.0 (PR #35): the ESLint config's install line pins `typescript@~6.0`; typescript-eslint 8.71.0 and TypeScript 7.0.2 are in `evidence.json`, and `test_docs.PasteableCommands` holds every install to the pin.* TypeScript 7 is npm's latest, and typescript-eslint 8.70 accepts TypeScript below 6.1. A project that installs typescript-eslint without pinning TypeScript gets a peer conflict. Say so wherever the docs install typescript-eslint.
- **N8.** *Done for 3.3.0 (PR #35), with XC-A2.* The plugin README's install section names only a local folder. Add the GitHub route, `/plugin marketplace add Vybecode-LTD/Pro-Web-Designer-Suite-Plug-in`, which anyone can use now that the repository is public.
- **N9.** *Done for 3.3.0 (PR #34): `test_docs.Manifests`, which compares every field but `source` and skips outside the repository.* Add a repository-level check that the root `.claude-plugin/marketplace.json` and the plugin's own agree on name, description, category and keywords.
- **N10.** *Done for 3.3.0 (PR #34): the review's header says where each item stands now.* The review's ✔ marks are stale. The inventory replaces them, so point the review's header at the inventory.

These were found in the reviews of PRs #12 to #15 (Codex and CodeRabbit, 2026-10-01 and 02). Each was rated P2 or minor and judged real; P0 of the execution plan fixes N16 to N25. One finding is not taken: CodeRabbit's note that `w1-supabase-facts.md` should spell `--quote-all-identifiers`. That line quotes the Supabase CLI's script, which spells it `--quote-all-identifier`.

- **N16.** *Done for 3.3.0 (PR #16).* A quoted name with a `$` in it (`"amount$usd"`) is unquoted by `introspect_schema.unquote_identifiers`, and the column parser, which reads only word characters in an unquoted name, then drops the column without a word.
- **N17.** *Done for 3.3.0 (PR #16).* `ALTER TABLE … DROP COLUMN` removes the column but leaves it in the table's primary key and unique indexes, and other tables' foreign keys still point at it. Postgres drops the indexes and constraints that use the column.
- **N18.** *Done for 3.3.0 (PR #16).* `RENAME COLUMN` renames the column in its own table only. Other tables' foreign keys, and the CHECKs on the column, keep the old name; Postgres retargets them.
- **N19.** *Done for 3.3.0 (PR #16).* An `ADD CONSTRAINT` the parser does not know falls through to `ADD COLUMN`. Postgres 18's named not-null constraint (`alter table t add constraint t_name_nn not null name`) becomes a column named `constraint`.
- **N20.** *Done for 3.3.0 (PR #16).* `scaffold_ui` names `public` in every policy, grant and smoke test, even for a model introspected with `--schema app` (`source.pg_schema` in the model).
- **N21.** *Done for 3.3.0 (PR #16).* `scaffold_ui.sql_ident` quotes nine reserved words. A table named `select` or a column named `where` gives invalid SQL. It needs the full list, as `introspect_schema.KEEP_QUOTED` has, with a test that the two lists match.
- **N22.** *Done for 3.3.0 (PR #16).* A policy is named `"<table>: owner reads"`. For a table name of 55 bytes or more, Postgres truncates the four names at 63 bytes to the same name, and the second `CREATE POLICY` fails.
- **N23.** *Done for 3.3.0 (PR #16).* The smoke test's "no write policy" check counts a write policy for a server role (`to service_role`) as one the browser holds. It should read `pg_policies.roles`.
- **N24.** *Done for 3.3.0 (PR #16).* The canonical `index.css` stops after `layout.css`. The vanilla stack documents `utilities.css` and `overrides.css`, and a project that copies the entry would never import them.
- **N25.** *Done for 3.3.0 (PR #16).* An `@import … layer(vendor)` placed before the `@layer` statement fixes `vendor` first, whatever the statement then says. The audit and stylelint check the statement's position against rules only.
- **N26.** *Done for 3.3.0 (PR #15).* `check_execution_plan.py` counted an item closed as "will not do" as open.
- **N27.** *Done for 3.3.0 (PR #15).* DL-C7's parts span four PRs, and the execution plan named only the agent. P27 now says where each part lands.
- **N28.** *Done for 3.3.0 (PR #15).* W1's target said "real `db pull` files". The dump is a real `pg_dump` made with the flags `db pull` uses, and a test applies the CLI's edits to it; there is no `db pull` file.
- **N29.** *Done for 3.3.0 (PR #16).* stylelint's `design/layer-order` never checked where the `@layer` statement stands, so a rule above it passed, while the audit's `layer-statement-position` refused it. Found while fixing N25.

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
| GT-C2 | S–M · P0 | Fix colour parsing, modals, iframes, inert content, `bypassCSP`, animation pausing and the disabled-control exemption. *Done: 3.1.0 did colours, modals, iframes and inert content; 3.4.0 did pausing (PR #38), `bypassCSP` and the disabled-control exemption (PR #39).* |
| GT-C3 | M · P0 | Matrix: the within-run "differs from default" gate, a tuned tolerance, focus mirroring, custom states, `data-state="error"` on non-form templates. *Done: 3.1.0 did the differs-from-default gate; 3.4.0 focus mirroring (A12) and custom states (A13), PR #42.* |
| GT-C5 | S · P0 | A correction pass on the docs (A7–A10, A16, A19). *Done: 3.2.0 corrected A7, A9, A10 and A19, and 3.4.0 A8 and A16 (PR #41).* |

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
- The audit's speed on large JSX, and SARIF output. *Done for 3.3.0 (PR #24, SB-C10).*
- Decision 3: which Tailwind lint plugin.

| ID | Severity or size | What is wrong or missing |
|---|---|---|
| SS-B4 | — | Modern CSS the systems references should teach: `@starting-style`, the top layer against the z-index ladder, `cqi`, `font-size-adjust`, `color-mix()`. |
| SB-B5 | — | parts of Tailwind v4 aren't covered. |
| SB-B6 | — | SCSS and other stacks. |
| SB-C3 | S-M · high | Ship a `tw_probe` script and a `/tw-probe` skill command. |
| SB-C4 | S · high | Replace Part 5 with eslint-plugin-better-tailwindcss 4.7 (peers ESLint 7–10 and Tailwind 3.3/4.1). |
| SB-C10 | S · low | In `audit_js`, `line_of()` costs O(n) per finding: a 1 MB JSX file with 20k findings took 12.6 s, against 5.1 s for 0.9 MB of CSS with 40k findings. *Done for 3.3.0 (PR #24): the lookup was already a bisect; `--files-from` and SARIF are new.* |
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
   - CI is green on every job of the release PR: the suite on Windows, Linux and macOS at Python 3.9 and 3.14, the static checks, and `claude plugin validate --strict`;
   - the fail-before table for the release's fixes: `python tools/fail_before.py <test ids> --rev <previous tag>`;
   - `claude plugin tag --dry-run plugins/web-design-suite` on the merged commit: it checks that `plugin.json` and the marketplace entry agree. The release's tag stays `vX.Y.Z`; the CLI's own would be `web-design-suite--vX.Y.Z`.

   Use the desktop app's bundled CLI, `%APPDATA%\Claude\claude-code\<version>\claude.exe`; the one on PATH is older.
3. Write the report as `dev plans/web-design-suite-<version>-report.md`, modelled on the 3.1.0 and 3.2.0 reports. Update the inventory and the `dev plans` README.
4. To see the release before tagging, build it locally from the merged commit: `python tooling/release/build.py <empty folder> --rev <commit>`. It writes `web-design-suite-<version>.zip`, one `.skill` file per skill and `SHA256SUMS`, from what git tracks, with git's file modes, dated at the commit, so a rebuild is byte-identical. It refuses, and writes nothing, if the plugin holds a link or a submodule, a file `git archive` leaves out, or a skill the platform would refuse. Write it into `Downloads`, which is not redirected to OneDrive. Never publish this build: CI makes the release.
5. Merge the PR, then tag `vX.Y.Z` on main and push the tag. `.github/workflows/release.yml` checks that the tag is `plugin.json`'s version, builds the same files on GitHub's runner, and creates the GitHub release with them and the CHANGELOG's section as its notes. It is the only thing that creates a release: never run `gh release create` by hand.
6. Update the installed copy.
   - Mirror the release into `C:\Users\vybec\.claude\local-marketplaces\web-design-suite\`, removing files that were deleted: extract the zip from step 4 (or `git archive` of the release commit) and mirror that, never the working folder, which can hold a `__pycache__` or a `node_modules`. That folder is the marketplace that `claude plugin update` installs from, so never move or delete it; sessions load the cached copy the last bullet names.
   - Check it with `diff -r`, then run `claude plugin update web-design-suite@web-design-suite`.
   - Confirm with `claude plugin details web-design-suite@web-design-suite`.
   - Sessions load the plugin from `C:\Users\vybec\.claude\plugins\cache\web-design-suite\web-design-suite\<version>`, and `update` refreshes that folder only when the version changes: it answers "already at the latest version" otherwise. So `diff -r -x .in_use` the cache against the release too, and if a rebuild of the same version left it stale, mirror the release into it as well, keeping `.in_use`. That happened with 3.2.1, first installed from `8b27ff7`.
7. Do the handoff: rewrite `docs/HANDOFF.md`, update the Current State in `CLAUDE.md`, and update the memory note.
