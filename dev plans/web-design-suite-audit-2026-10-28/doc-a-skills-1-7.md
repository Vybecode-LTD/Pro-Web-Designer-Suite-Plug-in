# DOC-A: the documents of seven skills (a11y-audit-runner … design-system-versioning)

Audited 2026-10-28 at main 8441ff0. Files read in full: a11y-audit-runner 6 (SKILL.md, 4 references, token-contract.md); client-presentation-builder 7 (SKILL.md, 3 references, 2 assets, deck-tokens.css); component-state-matrix 3 (SKILL.md, 2 references); content-model-to-ui 6 (SKILL.md, 5 references); design-critique-gate 5 (SKILL.md, 2 references, 2 assets); design-system-docs 5 (SKILL.md, 4 references); design-system-versioning 5 (SKILL.md, 4 references); plus `shared/token-contract.md` once (its 7 copies here are byte-identical). Commands run: `python -B <script> --help` for a11y_static.py, build_presentation.py, generate_matrix.py, introspect_schema.py, scaffold_ui.py, critique_report.py, build_docs.py, extract_system.py, diff_system.py, deprecate.py (and its `add`, `scan`, `status`, `retire`, `mapping`, `import` subcommands); `node <script> --help` for a11y_runtime.mjs, snapshot_matrix.mjs, critique_snapshots.mjs; `python -B plugins/pro-web-design-suite/tools/check_pointers.py` (exit 0, no output); `brief_to_log.py --help` (landing-page-conversion, named by DECISION_LOG.md); greps and existence checks only otherwise. No script was run beyond `--help`.

## Summary

25 findings: 3 high, 11 medium, 11 low. By class (counted from the headings): contradiction 10, stale 7, hazard 2, missing-file 2, undocumented-flag 2, budget 1, promise 1. Frontmatter: no finding (all seven parse, `name` equals the folder, descriptions are 191–200 characters and say what the skill is not for). Documented-but-missing flags: none (the suite's `DocumentedFlags` test already pins that). `check_pointers.py` is clean.

The three that matter most:

1. **a11y-audit-runner/SKILL.md tells Claude to write "an estimated third of WCAG success criteria" into a client report** — the exact wording its own `automation-coverage.md` §6 says is the wrong quantity ("None of the three counts *criteria*"), and which client-presentation-builder's `evidence.md` names as a figure "neither study gives". `test_no_doc_calls_automation_a_third_of_the_criteria` exists to forbid this sentence and its regex misses this spelling (DOC-A-1).
2. **`automation-coverage.md` §5.5 says the six WebAIM failures "are all Full rows in §3 and all six are in `a11y_static.py`"**: by its own §3 four of the six are Partial, and low-contrast text is a runtime check that the static script does not run at all (DOC-A-2).
3. **`snapshot_matrix.mjs --help` shows `--pixel-threshold 0.12` as the way to "loosen once, deliberately"**, two paragraphs after explaining that at 0.10 the suite's own hover and pressed overlays became invisible and deleting `:hover` passed every cell; `visual-regression.md` §4 says the same. A user who copies the example disables the check the reference calls the reason the gate is kept (DOC-A-3).

## Findings

### DOC-A-1 · high · contradiction

- **Where:** `plugins/pro-web-design-suite/skills/a11y-audit-runner/SKILL.md:137`
- **What:** The "short version" of the report wording that §7 of `automation-coverage.md` is said to supply states automation coverage as a fraction of *success criteria* — a quantity the reference says none of the sources measure, and a phrase a sibling skill explicitly rejects.
- **Evidence:** SKILL.md:135–137: "`references/automation-coverage.md` §7 has the wording to use instead … The short version: *"… Automated testing covers an estimated third of WCAG success criteria; the manual evaluation recorded in Appendix B covers the remainder …"*". `automation-coverage.md:251`: "None of the three counts *criteria*. For that, use the table in §3: a tool fully decides 7 of the 55 A and AA criteria and part of 31 more." `automation-coverage.md:281` (the §7 wording itself): "Automated checks fully decide 7 of the 55 WCAG 2.2 A and AA success criteria and part of 31 more; the other 48 were evaluated manually". `client-presentation-builder/references/evidence.md:140`: ""Roughly a third" is not a figure either study gives." `tests/test_facts.py:221–224` forbids `(a|one) third of (the |WCAG )*(success )?criteria` and `(roughly|about) a third of WCAG`; "an estimated third of WCAG success criteria" matches neither, so the test passes.
- **Effect:** Claude, or a user following step 5, pastes a coverage claim into a VPAT/ACR that the skill's own reference and the presentation skill both say is unsupportable; the skill contradicts itself on the one sentence it exists to police.
- **Fix:** Replace the clause with the §7 wording ("fully decide 7 of the 55 … and part of 31 more"), and widen the regex in `test_facts.py` to `(an? (estimated |rough )?|one )third of (the |WCAG )*(success )?criteria`.
- **Confidence:** confirmed

### DOC-A-2 · high · contradiction

- **Where:** `plugins/pro-web-design-suite/skills/a11y-audit-runner/references/automation-coverage.md:230`
- **What:** The §5.5 priority list claims its six failures are all fully machine-decided and all caught by the static script; the file's own §3 table and the scripts reference say otherwise for four of the six, and contrast is not a static check.
- **Evidence:** line 230: "All six are **Full** rows in §3 and all six are in `a11y_static.py` — no browser, one second, every commit." The six (lines 223–228) are low-contrast text (1.4.3), missing alt (1.1.1), missing form labels (3.3.2), empty links (2.4.4), empty buttons (4.1.2), missing `lang` (3.1.1). In §3: line 70 "**1.4.3** Contrast (Minimum) | **Partial**", line 57 "**1.1.1** … **Partial**", line 86 "**2.4.4** … **Partial**", line 107 "**4.1.2** … **Partial**"; only 3.3.2 (line 102) and 3.1.1 (line 97) are **Full**. `references/scripts.md:9–15`'s category table for `a11y_static.py` (S, N, K, R, F) has no contrast check; `scripts.md:58` lists `contrast` under `a11y_runtime.mjs` as "text contrast from computed styles … the case static analysis reports as a pass". `test_facts.py` checks only the "N of the 55" sentences, so this one is unpinned.
- **Effect:** A team standing up the gate "on a codebase with no accessibility work" is told the static commit hook closes low-contrast text; it does not, and nothing in CI will say so.
- **Fix:** "Two of the six are Full rows and four are Partial; five are in `a11y_static.py`, and low-contrast text is `a11y_runtime.mjs`'s `contrast` check (or one axe rule) on a served build." Then the "no browser, one second" clause applies to five, not six.
- **Confidence:** confirmed

### DOC-A-3 · high · contradiction

- **Where:** `plugins/pro-web-design-suite/skills/component-state-matrix/scripts/snapshot_matrix.mjs` `--help` (Usage block, "loosen once" example) against `references/visual-regression.md:121`
- **What:** The script's own usage text recommends a per-pixel tolerance the reference, and the same help text one screen lower, say blinds the hover and active checks.
- **Evidence:** `--help`: "# loosen once, deliberately, with a reason in the commit message / node snapshot_matrix.mjs sheet.html --threshold 0.004 --pixel-threshold 0.12". Same `--help`, after `--forced-colors`: "(At the old 0.10 tolerance the suite's own 4% hover and 8% pressed overlays were below the noise floor, so deleting :hover or :active passed every cell.)". `visual-regression.md:121`: "at `0.10` (a distance of ~352) the suite's own 4% hover overlay (~51) and 8% pressed overlay (~210) were invisible, so deleting `:hover` or `:active` passed every cell. At `0.03` (~32) both count." `SKILL.md:299`: "`--pixel-threshold N` | … (default `0.03`: the suite's 4% hover overlay is a distance of ~0.038)". `test_docs.DocumentedFlags` checks that documented flags exist, not the values.
- **Effect:** The first thing a user reads when a run is flaky is an example that turns the state-differs check off for every hover and active cell; the reference says never to do that.
- **Fix:** Change the help example to the knob the reference permits raising (`--threshold`) with a value inside the band, e.g. `--threshold 0.004`, and drop `--pixel-threshold 0.12`; or show `--pixel-threshold 0.04` with the sentence that the hover overlay is ~0.038. Also move the "Every hover, active and focus-visible cell must also DIFFER…" paragraph out of the middle of the Options list (it sits between `--forced-colors` and `--allow-new`), where it reads as part of `--forced-colors`.
- **Confidence:** confirmed

### DOC-A-4 · medium · contradiction

- **Where:** `plugins/pro-web-design-suite/skills/component-state-matrix/references/state-coverage.md:81` vs `plugins/pro-web-design-suite/skills/a11y-audit-runner/references/runtime-checks.md:179`
- **What:** Two skills disagree on whether SC 2.4.13 (AAA) is part of the suite's floor.
- **Evidence:** state-coverage.md:81: "or thinner than 2px (the 2px perimeter is 2.4.13, Level AAA, which this suite holds as a floor)". runtime-checks.md:179: "**Indicator contrast.** SC 2.4.13 (Level AAA, so beyond this skill's AA floor) asks for 3:1". token-contract.md:109: "WCAG 2.2 Level AA, treated as a floor." `test_facts.test_every_level_quoted_is_the_criterions_level` checks only that "2.4.13, Level AAA" carries the right letter, so the policy claim is unpinned.
- **Effect:** The matrix skill tells a reviewer to fail a 1px ring as below the floor; the a11y skill tells the same reviewer the floor is AA and 2.4.13 is extra. A critique that cites either is contradicted by the other.
- **Fix:** Pick one. If the 2px ring is suite policy (the contract's `--stroke-focus` is 2px), say "suite policy, above the AA floor" in state-coverage.md as runtime-checks.md does; the floor stays AA everywhere.
- **Confidence:** confirmed

### DOC-A-5 · medium · stale

- **Where:** `plugins/pro-web-design-suite/skills/a11y-audit-runner/references/automation-coverage.md:187`; also `component-state-matrix/references/visual-regression.md:33–37` and `a11y-audit-runner/references/runtime-checks.md:36`
- **What:** Three descriptions of how the browser scripts freeze animation before measuring disagree with each other about the mechanism and where it lives.
- **Evidence:** automation-coverage.md:187: "Freeze animations before scanning. `a11y_runtime.mjs` injects a 1ms animation/transition override for exactly this". runtime-checks.md:36: "the runner pauses every animation and finishes every transition, with the same freeze `snapshot_matrix.mjs` uses (`scripts/browser_common.mjs`). Shortening an animation is not enough: a spinner that keeps turning changes pixels between the two screenshots". visual-regression.md:36–37 (column "Where in `snapshot_matrix.mjs`"): "Animations mid-flight | `animation-play-state: paused`, `animation-delay: -1ms` | `FREEZE_CSS`" and "Transitions mid-flight | `transition-duration: 1ms`". `grep` shows `FREEZE_CSS` only in `snapshot_matrix.mjs` and `FREEZE_ANIMATIONS_CSS` (`animation-play-state: paused !important`) in `browser_common.mjs`. Which freeze each script uses: **to verify in code** (`a11y_runtime.mjs`, `snapshot_matrix.mjs`, `browser_common.mjs`).
- **Effect:** A reader diagnosing a ring measured mid-animation is told three different things about what the runner did.
- **Fix:** One sentence, in `runtime-checks.md` §1, naming the constant and the file; `automation-coverage.md:187` and the visual-regression table point at it.
- **Confidence:** likely

### DOC-A-6 · medium · stale

- **Where:** `plugins/pro-web-design-suite/skills/content-model-to-ui/references/supabase-integration.md:25` (and the table at 27–43)
- **What:** The source-fidelity section still says the reader takes three inputs; the skill now takes five, and the SKILL.md sends the reader here for the fidelity table.
- **Evidence:** supabase-integration.md:25: "Three sources, three fidelities. `introspect_schema.py` reads all three and records what each one could not carry". Its table has columns for DDL, `gen types` and `information_schema` only. SKILL.md:63: "Reads a `.sql` DDL file, a … `.ts` file, a Prisma schema, a Drizzle `pgTable` schema, or a JSON schema dump, and normalises all five". SKILL.md:65: "`references/supabase-integration.md` §1 has the fidelity table and the measured difference." scripts.md:21: "**Prisma and Drizzle (3.6.0).** … Prisma has no CHECK constraints … Neither file carries row-level security" (CHANGELOG 3.6.0 confirms the version).
- **Effect:** A user with a Prisma or Drizzle schema looks up what their source loses and finds no row for it.
- **Fix:** "Five sources" and two more columns (Prisma, Drizzle) in the table, from the facts already in scripts.md:21.
- **Confidence:** confirmed

### DOC-A-7 · medium · missing-file

- **Where:** `plugins/pro-web-design-suite/skills/design-system-versioning/SKILL.md:126`; `content-model-to-ui/references/worked-example.md:7`; `content-model-to-ui/references/supabase-integration.md:45`; `shared/token-contract.md:3` (14 copies)
- **What:** Shipped documents name files under `tests/`, a folder `build.py` strips from every release (`DEV_ONLY = {"tests", "evals", "tools"}`), so in the distribution repository and in every installed plugin the paths do not exist.
- **Evidence:** versioning SKILL.md:126: "Five edits to the starter's `tokens.css` (`tests/fixtures/worked-release.json`, rerun by a test)". worked-example.md:7: "shipped as `tests/fixtures/supabase/shop.sql` … (`tests/test_schema_sources.py` checks that it still does)". supabase-integration.md:45: "which the plugin's tests carry in three forms (`tests/fixtures/supabase/`, held by `tests/test_schema_sources.py`)". token-contract.md:3: "change the master, copy it over all thirteen, and `tests/test_contract.py` fails until they match." `tooling/release/build.py:83`: `DEV_ONLY = {"tests", "evals", "tools"}`. `test_docs.NoMachinePaths` checks for the author's machine paths, not for dev-only repository paths.
- **Effect:** worked-example.md says the fixture is "shipped"; a user of the installed plugin cannot open it. Low cost, but the word "shipped" is false and the contract's note tells a forker to run a test they do not have.
- **Fix:** "in the development repository's `tests/fixtures/…`" wording, or drop the path and keep the description; a test that greps shipped docs for `tests/`, `evals/`, `tools/` outside the development-only notes.
- **Confidence:** confirmed

### DOC-A-8 · medium · missing-file

- **Where:** `plugins/pro-web-design-suite/skills/content-model-to-ui/references/screen-patterns.md:249`
- **What:** The dashboard anatomy names a layout modifier the studio's primitives do not define.
- **Evidence:** screen-patterns.md:249: "├── .switcher--max-4     headline metrics, equal peers". `web-design-studio/assets/starter/styles/layout.css` defines `.switcher--max-2` and `.switcher--max-3` (lines 578–583) plus `--tight`, `--loose`, `--narrow-threshold`; `layout-composition.md:271` names `--max-2` and `--max-3` only. screen-patterns.md:7 says the primitives "are used by name". `scaffold_ui.py` emits no `switcher--max-*` class (grep), so only the document is wrong.
- **Effect:** A developer composing the dashboard from the doc writes a class that does nothing; four metrics then wrap as the default switcher allows, which the same paragraph says must not happen ("three become three rows at narrow widths, never two-plus-one").
- **Fix:** `.switcher--max-3` with "at most three per row", or add `--max-4` to the starter and the layout reference (owner: web-design-studio).
- **Confidence:** confirmed

### DOC-A-9 · medium · undocumented-flag

- **Where:** `plugins/pro-web-design-suite/skills/design-critique-gate/SKILL.md:289–325` (the only flag documentation the skill has)
- **What:** `critique_report.py` and `critique_snapshots.mjs` accept flags no document in the skill names; the skill has no `references/scripts.md`, and `test_docs.TheScriptReferences` covers four other scripts only, so nothing pins this.
- **Evidence:** `critique_report.py --help`: `--layer LAYER` ("restrict to a layer (repeatable)"), `--min-severity {blocking,major,minor,taste}` ("drop findings below this severity"), `--no-taste` ("drop taste findings entirely"); grep of the skill's `.md` files finds 0 mentions of each. `critique_snapshots.mjs --help`: `usage: node critique_snapshots.mjs URL|FILE.html [--out DIR] [--settle MS] [--browser PATH] [--json] [--wait-for SEL] [--steps FILE] [--storage-state FILE] [--header "Name: V"]...` — `--settle` and `--browser` have 0 mentions; the header comment names `CRITIQUE_CHROMIUM` as the browser variable, which no document names either. The help is a one-line usage with no descriptions, defaults or exit codes (the exit codes are in the file's header comment only; SKILL.md:319 and 325 state them).
- **Effect:** A user who needs the critique narrowed to one layer, or a page that renders late, or a pinned browser for reproducible captures, cannot find the flag.
- **Fix:** A flag table for both scripts in SKILL.md's "The scripts" section (3 + 2 rows), and `--settle`/`--browser` descriptions in the usage text.
- **Confidence:** confirmed

### DOC-A-10 · medium · undocumented-flag

- **Where:** `a11y-audit-runner/references/scripts.md:19–27` and `68–80`; `component-state-matrix/SKILL.md:273–306`; `design-system-versioning/references/scripts.md:46–61`
- **What:** Flags each script accepts that its skill's flag tables omit.
- **Evidence:** `a11y_static.py --help` has `--quiet` ("suppress the fix guidance") and `--no-color` (no help text at all); scripts.md §1 lists neither (its one `--quiet` is a11y_runtime's, line 80). `a11y_runtime.mjs --help` has `--report FILE`; the §2 flag table (lines 68–80) omits it (it appears only in prose at line 135 and in SKILL.md:187). `generate_matrix.py --help` and `snapshot_matrix.mjs --help` both have `--quiet`; 0 mentions in component-state-matrix. `deprecate.py`: `add --date YYYY-MM-DD`, `scan --date`, `retire --date`, `status --format {report,json}`, `import --date/--force/--dry-run` are absent from the versioning scripts.md tables (the file's one `--date` is diff_system's, line 13, so a whole-file regex test would pass). `build_presentation.py --help` `--tokens` default is "the CSS token files the project's .design-suite.json lists, else the bundled copy"; SKILL.md:253 says only "default: `.design-suite.json`'s CSS `tokens`".
- **Effect:** Minor for `--quiet`; for `deprecate … --date` it hides the only way to backdate a ledger record (the field the §9 walkthrough shows as `"recorded": "2026-09-17"`).
- **Fix:** One row each in the tables; give `--no-color` a help string.
- **Confidence:** confirmed

### DOC-A-11 · medium · budget

- **Where:** `design-critique-gate/SKILL.md` (20,497 bytes), `client-presentation-builder/SKILL.md` (20,494), `component-state-matrix/SKILL.md` (20,494), `design-system-versioning/SKILL.md` (20,434)
- **What:** Four of the seven SKILL.md files sit within 100 bytes of `test_skill_budget.SKILL_BYTES = 20_500` (three within 6 bytes).
- **Evidence:** `tests/test_skill_budget.py:23`: `SKILL_BYTES = 20_500`; sizes measured with `stat`. References are nowhere near `REFERENCE_BYTES = 60_500` (largest: runtime-checks.md, 40,948).
- **Effect:** Any wording fix from this audit (DOC-A-1 lands in a11y's SKILL.md, which has room; DOC-A-9 lands in design-critique-gate's, which has 3 bytes; DOC-A-16 lands in design-system-docs', which has 2,692) fails CI until something else is cut; a one-word clarification is a trim-and-rewrite.
- **Fix:** Move the critique gate's "Failure modes of critique itself" table (SKILL.md:346–356, already in critique-method.md §6) and the versioning skill's second anti-pattern table (SKILL.md:228–244, duplicated in rollout.md §9) into their references, freeing ~1.5 KB each.
- **Confidence:** confirmed

### DOC-A-12 · medium · promise

- **Where:** `plugins/pro-web-design-suite/skills/a11y-audit-runner/references/automation-coverage.md:53` and the §3 rows at 64, 74, 82, 92, 100
- **What:** The table's convention says a row without "*Not in this suite.*" is a mechanism one of the two scripts runs; five rows name mechanisms that no documented check implements. **To verify in code** (`a11y_static.py`, `a11y_runtime.mjs`).
- **Evidence:** line 53: "a row whose mechanism neither `a11y_static.py` nor `a11y_runtime.mjs` runs says *Not in this suite.*" Rows without the marker: line 64 "**1.3.2** … DOM order vs visual order disagreements from CSS `order`, `grid-area`, `position: absolute`"; line 74 "**1.4.11** … icon and border contrast against a solid adjacent colour" (scripts.md documents focus-ring contrast only: line 56); line 82 "**2.3.1** … frame-differencing a recording, in principle | Nobody does this in CI. Treat as manual"; line 92 "**2.5.2** … actions bound to `pointerdown`/`mousedown` rather than `click`"; line 100 "**3.2.3 / 3.2.4 / 3.2.6** … compare nav order and component names across a crawl" (scripts.md:135 describes `--urls` as "Each run is the script on one page at one size, in a process of its own"; no cross-page comparison is described). None of these mechanisms appears in scripts.md's category table (§1) or check table (§2).
- **Effect:** A reader auditing coverage believes the suite checks DOM-vs-visual order, non-text contrast of icons and borders, pointer cancellation and cross-page consistency.
- **Fix:** Add "*Not in this suite.*" to each row the code does not implement (the 2.3.1 row should say it either way), or implement and document the check.
- **Confidence:** likely

### DOC-A-13 · medium · stale

- **Where:** `plugins/pro-web-design-suite/skills/client-presentation-builder/assets/deck-tokens.css:395–409` (byte-identical to `web-design-studio/assets/starter/styles/tokens.css`; report once, owner is the studio)
- **What:** The shipped token file's comment on the focus elevation role describes the older "bridge" ring (shadow ring + transparent outline) that the contract and the a11y reference have since replaced with an outline ring.
- **Evidence:** deck-tokens.css:404–408: "The focus ring is an elevation role too. … Pair it with a transparent `outline` at the call site: forced-colors mode discards box-shadow, and the outline is what survives to become the indicator." and 395–396: `--shadow-focus: 0 0 0 var(--stroke-focus) var(--bg-canvas), 0 0 0 calc(var(--stroke-focus) * 2) var(--border-focus);` (a two-band ring drawn by shadow). token-contract.md:109: "the focus ring is an `outline` (`var(--stroke-focus) solid var(--border-focus)`, offset by `--stroke-focus`) … A component that adds `box-shadow: var(--elevation-focus)` keeps an outline beside it". runtime-checks.md:266: "The older "bridge", a transparent outline under a box-shadow ring, also survives forced colours, but in normal mode any component shadow replaces its ring." `test_docs.test_no_focus_style_removes_the_outline` guards `outline: none`, not a transparent one.
- **Effect:** A developer reading the token file (the place the docs skill says the rationale lives) is told to draw the ring the suite now says loses to any component shadow.
- **Fix:** Rewrite the comment to the contract's rule ("the ring is the outline from reset.css; `--elevation-focus` is the gap/separation shadow beside it, never a replacement") and consider whether `--shadow-focus` still needs its second band.
- **Confidence:** confirmed

### DOC-A-14 · medium · contradiction

- **Where:** `plugins/pro-web-design-suite/skills/content-model-to-ui/references/field-mapping.md:7` vs `references/worked-example.md:12–30`
- **What:** The mapping reference says every signal string the script prints is quoted from it; the worked example reproduces the script's output and its signal strings are not in the reference.
- **Evidence:** field-mapping.md:7: "every rule below is a rule in that file, and every `signal` string it emits is quoted from here." worked-example.md:12: "the record's title — one line, always, regardless of how much room the column allows"; line 30: "is_/has_ prefix — a boolean the user flips, not a form checkbox"; line 24: "`categories` reads as a lookup table, which is almost always under 20 rows". `grep` of field-mapping.md for "regardless of how much room", "a boolean the user flips", "reads as a lookup table": no hits.
- **Effect:** A reviewer told to "audit the machine's reasoning" (SKILL.md:214) by looking a signal up in the reference does not find it.
- **Fix:** "every `signal` string it emits paraphrases a rule here" — or quote the rule text in the signals (a code change).
- **Confidence:** confirmed

### DOC-A-15 · low · stale

- **Where:** `plugins/pro-web-design-suite/skills/design-system-docs/references/extraction.md:92`
- **What:** A count against "the canonical token file" no longer matches that file. **To verify by running `extract_system.py` on the starter** (not run here).
- **Evidence:** extraction.md:92: "Against the canonical token file this recovers 31 dark re-points, 3 density modes and 6 reduced-motion overrides". The `[data-theme="dark"]` block of the canonical file (deck-tokens.css:491–545, identical to the starter) declares 33 tokens: 6 surfaces, 4 interaction, 9 foreground, 4 borders, 2 accent, 3 intent foregrounds, 5 shadows. The 6 reduced-motion overrides (lines 610–615) and 3 densities (597–599) still match.
- **Effect:** A reader checking the extractor against the figure sees 33 and doubts the tool.
- **Fix:** Re-count after running the extractor, or drop the number.
- **Confidence:** possible

### DOC-A-16 · low · contradiction

- **Where:** `plugins/pro-web-design-suite/skills/design-system-docs/SKILL.md:121` vs `SKILL.md:130` and `references/documentation-model.md:85–91`
- **What:** The site is described as four pages, then given a fifth.
- **Evidence:** SKILL.md:121: "Four pages, no build step, no network, opens from `file://`: an overview, a token reference …, a component reference …, and a patterns page if you have written any." SKILL.md:130: "principles.md                  the principles page". documentation-model.md §3 table lists Overview, Token group, Component, Pattern, Principles; §7 is "The principles page".
- **Effect:** Wording only.
- **Fix:** "Five page kinds" or drop the count.
- **Confidence:** confirmed

### DOC-A-17 · low · contradiction

- **Where:** `plugins/pro-web-design-suite/skills/design-system-docs/references/documentation-model.md:128`
- **What:** The component page is introduced as eight sections with seven generated; nine follow and two are hand-written.
- **Evidence:** line 128: "This is the page that justifies the skill. Eight sections, seven of them generated." Subsections run §5.1 to §5.9; line 177 (§5.8): "Hand-written. Always."; line 181 (§5.9): "Hand-written, and worth the two minutes"; §5.1 and §5.7 are "partly generated".
- **Effect:** Wording only.
- **Fix:** "Nine sections, five generated, two partly, two by hand."
- **Confidence:** confirmed

### DOC-A-18 · low · stale

- **Where:** `client-presentation-builder/references/objection-handling.md:11–19`; `design-system-docs/references/documentation-model.md:9–20`; `content-model-to-ui/references/supabase-integration.md:386`
- **What:** Sections appended after a file's "three sentences"/"Related" footer are missing from its Contents list.
- **Evidence:** objection-handling.md's Contents ends at "9. Presenting alongside more senior designers"; line 428 is "## 10. The client who rejects the whole direction" (and client-presentation-builder/SKILL.md's routing table at 316–324 does not point at §10 either). documentation-model.md's Contents ends at "12. Anti-patterns"; line 334 is "## 13. Why not Storybook" (SKILL.md:89 points at §13). supabase-integration.md:386 "Related: …" sits before "## 9. Who talks to the database" at line 390. `test_facts` GT-A19 fixed a Contents list "numbered against the wrong headings"; omissions are unchecked.
- **Effect:** A reader scanning Contents for "the whole direction is rejected" or "Storybook" does not find the section.
- **Fix:** Add the entries; move the footer below §9.
- **Confidence:** confirmed

### DOC-A-19 · low · contradiction

- **Where:** `a11y-audit-runner/SKILL.md:61` vs `references/manual-protocol.md:7`
- **What:** The manual pass is budgeted differently in the two places.
- **Evidence:** SKILL.md:61: "| Runtime | ~1 second | ~30–90 seconds | 45–90 minutes per template |". manual-protocol.md:7: "**Budget: 60–90 minutes per template the first time, 30–45 once the team knows it.**" (its sections add to 75 minutes).
- **Effect:** Wording only.
- **Fix:** "30–90 minutes per template" in the SKILL.md table.
- **Confidence:** confirmed

### DOC-A-20 · low · contradiction

- **Where:** `component-state-matrix/SKILL.md:304` vs `SKILL.md:308` and `references/visual-regression.md:275`; same shape in `a11y-audit-runner/SKILL.md:194` vs `a11y_runtime.mjs --help`
- **What:** The documented browser search order puts a CI-image path before Playwright's own Chromium, while the CI notes say the Playwright Chromium is tried first.
- **Evidence:** matrix SKILL.md:304: "default `$MATRIX_CHROMIUM`, else the first that starts of `/opt/pw-browsers/chromium`, Playwright's own Chromium, an installed Chrome or Edge". SKILL.md:308: "It installs the Chromium that the locked Playwright was built for, which the script tries first". visual-regression.md:275: "`npx playwright install chromium` installs the Chromium that the locked Playwright was built for, and `snapshot_matrix.mjs` tries it first." a11y SKILL.md:194: "`a11y_runtime.mjs` tries it first"; `a11y_runtime.mjs --help`: "default: A11Y_CHROMIUM, else the first that starts of /opt/pw-browsers/chromium, Playwright's own Chromium, Chrome or Edge". `test_recipes.test_a_browser_script_runs_on_the_pinned_browser` checks the workflow text, not this sentence.
- **Effect:** On a runner image that ships `/opt/pw-browsers/chromium`, the baseline is taken with the image's build, not the lockfile's, which is the drift the CI notes say the cache prevents.
- **Fix:** "tries it before the image's own Chrome" (true) instead of "first", or put the Playwright Chromium first in the search order (a code change).
- **Confidence:** confirmed

### DOC-A-21 · low · contradiction

- **Where:** `design-critique-gate/references/failure-catalog.md:277` vs `component-state-matrix/references/state-coverage.md:229`
- **What:** Two skills give two unregistered figures for translation expansion.
- **Evidence:** failure-catalog.md:277: "translations (often 30% longer)". state-coverage.md:229: "German is ~35% longer than English". `tests/fixtures/evidence.json` registers W3C's figure ("200–300% for strings of up to 10 characters, about 130% for strings over 70"); neither 30% nor 35% is registered, and `test_evidence` pins attributed figures only.
- **Effect:** Wording only.
- **Fix:** One figure, with the W3C entry's qualifier, in both.
- **Confidence:** confirmed

### DOC-A-22 · low · hazard

- **Where:** `design-critique-gate/references/failure-catalog.md:370`; `client-presentation-builder/references/evidence.md:75`; `client-presentation-builder/SKILL.md:120`
- **What:** The chain studio → critique → presentation names two different decision records and no document says how one feeds the other.
- **Evidence:** failure-catalog.md:370 (L10-1 fix): "`DESIGN_DECISIONS.md` written as decisions are made, plus `critique_report.py --format defence`". web-design-studio/SKILL.md:120: "`DESIGN_DECISIONS.md` for the non-obvious choices" (handoff-conventions.md:44: "Why non-obvious choices were made. Append-only."). evidence.md:75 lists `DESIGN_DECISIONS.md` as an artifact to translate. client-presentation-builder/SKILL.md:120: "`DECISION_LOG.md` | `assets/DECISION_LOG.md`, kept as you worked"; DECISION_LOG.md:9: "`scripts/build_presentation.py` reads this file. Keep the field names."
- **Effect:** A project that followed the studio has an append-only `DESIGN_DECISIONS.md`; `build_presentation.py` reads only the field-structured `DECISION_LOG.md`, so the "evidence that already exists" (SKILL.md:113) has to be re-typed.
- **Fix:** One sentence in client-presentation-builder's step 1 saying `DESIGN_DECISIONS.md` is the studio's record and `DECISION_LOG.md` is its presentation-ready form (or make the builder read the studio file).
- **Confidence:** confirmed

### DOC-A-23 · low · stale

- **Where:** `plugins/pro-web-design-suite/skills/design-system-docs/SKILL.md:217`
- **What:** The adoption step's command fragment mixes one script's flag with another's argument shape, and names `/tmp`, which the suite's own test forbids in commands.
- **Evidence:** SKILL.md:217: "**Extract first, publish nothing.** `--out /tmp/docs --report`." `--report` is `extract_system.py`'s ("Print a human summary to stderr"), whose `--out FILE` is "Where to write system.json"; `/tmp/docs` reads as `build_docs.py`'s site directory. `test_docs.test_no_doc_runs_python3_or_writes_to_tmp` passes because the fragment is inline code, not a fenced command. (`build_docs.py --help`'s own Examples also use `--out /tmp/d`.)
- **Effect:** A reader copies a fragment that writes `system.json` to a file called `/tmp/docs`.
- **Fix:** `python -m scripts.extract_system styles/ src/components/ --out build/system.json --report`.
- **Confidence:** confirmed

### DOC-A-24 · low · stale

- **Where:** `plugins/pro-web-design-suite/skills/content-model-to-ui/scripts/introspect_schema.py` `--help` (positional `schema` text)
- **What:** The script's own help names three input kinds while its `--format` choices and the docs name five.
- **Evidence:** `--help`: "schema  a .sql DDL file, a `supabase gen types typescript` .ts file, or a .json dump." and "--format {auto,ddl,ts,json,prisma,drizzle}". scripts.md:12: "`.prisma`, and a `.ts` or `.js` file with `pgTable(`, are found by themselves".
- **Effect:** A user reading `--help` does not learn Prisma and Drizzle are accepted.
- **Fix:** Add them to the positional's help string (a one-line code change).
- **Confidence:** confirmed

### DOC-A-25 · low · hazard

- **Where:** every hit of the word "icon" in the seven skills' shipped text (check 7); the one inside a code span is `a11y-audit-runner/references/scripts.md:131`
- **What:** The directory held 4.0.1 for the word "icon" in a code span (CLAUDE.md gotcha); these seven skills contain 31 ordinary uses of the word, one of them in a code span.
- **Evidence:** In a code span: scripts.md:131 "`main > x-card >> button.icon`". In quotes: runtime-checks.md:68 ""Button", "Link", "Menu", "Icon"". In prose: automation-coverage.md:74 ("icon and border contrast"), :226 ("an icon-only control"); manual-protocol.md:157 ("Icon-only buttons"), :179 ("the round icon"); token-contract.md:74 ("icon + label", ×7 copies); deck-tokens.css:53, :109, :336, :344; state-coverage.md:155; screen-patterns.md:83; supabase-integration.md:331 ("broken-image icons"); critique-method.md:124, :211 (heading "An icon set drawn at mixed optical weights"), :213, :214, :219, :222; failure-catalog.md:94, :210, :414; design-critique-gate/SKILL.md:168; change-classification.md:243. No hit names a bundled image's path or stem.
- **Effect:** None of these is the pattern that caused the hold (a bundled image's stem); the `button.icon` selector is the nearest in shape, so it is the one to watch if the directory's check proves to be a word match.
- **Fix:** Nothing now; if a future hold cites one of these, `button.icon` → `button.glyph` in the example path costs nothing.
- **Confidence:** confirmed

## Flags: documented vs --help

| Script | Documented but missing | Present but undocumented | Default / exit mismatches |
|---|---|---|---|
| `a11y_static.py` | none | `--quiet`, `--no-color` (no help text) | none; exits 0/1/2 match scripts.md:38 |
| `a11y_runtime.mjs` | none | `--report` absent from the §2 flag table (in prose at scripts.md:135 and in SKILL.md:187); `--max-stops` (40), `--max-cells` (120), `--focus-threshold` (0.005), `--viewport` (1280x900), `--dpr` (1) listed at scripts.md:80 with no description or default | `--tags`, `--densities auto`, `--max-urls 50` match; exits match scripts.md:82 |
| `build_presentation.py` | none | none (`--manual` is at SKILL.md:123) | `--tokens` default omits "else the bundled copy" (SKILL.md:253); exits 0/1/2 match the docstring |
| `generate_matrix.py` | none | `--quiet`, `-o` alias | `--profile pruned`, `--root` match; exit 2 "missing files" not in SKILL.md:284 |
| `snapshot_matrix.mjs` | none | `--quiet` | thresholds 0.002/0.03 match; `--viewport` default 1440x900 unstated; help example `--pixel-threshold 0.12` contradicts the reference (DOC-A-3) |
| `introspect_schema.py` | none | none | positional help omits Prisma/Drizzle (DOC-A-24); exits match scripts.md:19 |
| `scaffold_ui.py` | none | none | `--out src`, `--stack`, `--framework react` match; exits match scripts.md:43 |
| `critique_report.py` | none | `--layer`, `--min-severity`, `--no-taste` | `--format critique`, `--min-severity taste` unstated; `--fail-on` exit 1 matches |
| `critique_snapshots.mjs` | none | `--settle MS`, `--browser PATH`, `CRITIQUE_CHROMIUM` | help has no descriptions, defaults or exit codes; the header comment's exit codes match SKILL.md:319/325 |
| `extract_system.py` | none | none (pinned by `TheScriptReferences`) | `--root-font-size 16`, `--out` stdout match |
| `build_docs.py` | none | none (pinned) | `--baseline` default matches scripts.md:42 |
| `diff_system.py` | none | none | `--format report`, `--gate names`, `--date` today match; exits match |
| `deprecate.py` | none (`deprecate list`, which I tried, is documented nowhere and does not exist) | `add --date`, `scan --date`, `retire --date`, `status --format`, `import --date/--force/--dry-run`; `scan --limit` default 6 unstated | `--ledger ./deprecations.json`, `--codemod auto` match; both `--name=--x` and `--name --x` forms work (normalize_argv, scripts.md:65) |

## Sizes against the caps

| File | Bytes | Cap | Margin |
|---|---|---|---|
| design-critique-gate/SKILL.md | 20,497 | 20,500 | **3** |
| client-presentation-builder/SKILL.md | 20,494 | 20,500 | **6** |
| component-state-matrix/SKILL.md | 20,494 | 20,500 | **6** |
| design-system-versioning/SKILL.md | 20,434 | 20,500 | **66** |
| content-model-to-ui/SKILL.md | 20,384 | 20,500 | 116 |
| a11y-audit-runner/SKILL.md | 19,617 | 20,500 | 883 |
| design-system-docs/SKILL.md | 17,808 | 20,500 | 2,692 |
| a11y-audit-runner/references/runtime-checks.md (largest reference) | 40,948 | 60,500 | 19,552 |
| content-model-to-ui/references/supabase-integration.md | 36,446 | 60,500 | 24,054 |
| a11y-audit-runner/references/automation-coverage.md | 33,551 | 60,500 | 26,949 |
| every other reference | ≤ 31,217 | 60,500 | ≥ 29,283 |

Descriptions: 191–200 characters (cap 200 in `test_skill_budget.py`, 1,024 at the platform). Frontmatter keys: `name`, `description` only; `name` equals the folder in all seven; no CRLF.

## External URLs named

| URL | Where | Context |
|---|---|---|
| https://accessibility.blog.gov.uk/2017/02/24/what-we-found-when-we-tested-tools-on-the-worlds-least-accessible-webpage/ | a11y SKILL.md:24; automation-coverage.md:247 | GDS 2017, 143 planted failures, 37–41% (registered in evidence.json) |
| https://www.deque.com/blog/automated-testing-study-identifies-57-percent-of-digital-accessibility-issues/ | a11y SKILL.md:26; automation-coverage.md:248 | Deque 2021, 57% by volume (registered) |
| https://webaim.org/projects/million/ | automation-coverage.md:249 | WebAIM Million 2026: 95.9%, 56.1, 83.9% … (registered; "2026" matches the register) |
| https://www.w3.org/WAI/WCAG22/Understanding/focus-not-obscured-minimum.html | runtime-checks.md:193 | 2.4.11 wording |
| https://www.w3.org/WAI/WCAG22/Understanding/content-on-hover-or-focus.html | runtime-checks.md:377 | 1.4.13's three conditions |
| https://www.w3.org/WAI/WCAG22/Understanding/text-spacing.html | runtime-checks.md:424 | 1.4.12's values |
| https://www.nei.nih.gov/learn-about-eye-health/eye-conditions-and-diseases/color-blindness | failure-catalog.md:208 | "1 in 12 men" (registered) |
| https://nextjs.org/docs/app/guides/forms | supabase-integration.md:423 | server actions must verify auth |
| https://github.com/supabase/supabase/tree/master/examples/auth/nextjs | supabase-integration.md:425 | the server client the scaffold copies |
| https://supabase.com/docs/guides/auth/server-side/creating-a-client | supabase-integration.md:425 | `setAll` in a try |
| https://nextjs.org/docs/app/guides/environment-variables | supabase-integration.md:432 | `NEXT_PUBLIC_` is inlined |
| https://docs.renovatebot.com/configuration-options/ | rollout.md:75 | `rangeStrategy: "pin"`, `minimumReleaseAge` |
| https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference | rollout.md:91 | `versioning-strategy: increase`, `cooldown` |
| https://docs.npmjs.com/cli/commands/npm-deprecate | rollout.md:248 | `npm deprecate` keeps the version installable |
| https://www.designtokens.org/tr/2025.10/format/#deprecated | versioning scripts.md:27 | DTCG 2025.10 `$deprecated` (the version matches every other "DTCG 2025.10" mention) |
| http://127.0.0.1:…, http://localhost:3000/…, https://staging.example.com/, https://xyz.supabase.co/… | a11y SKILL.md and scripts.md; critique SKILL.md:318–320; supabase-integration.md:333 | example hosts only |

No URL names a version or date that another document contradicts. Facts quoted beside these URLs that are not in `evidence.json`: the "30%"/"~35%" translation figures (DOC-A-21); everything else attributed is registered.

## What is covered well

- Every `§` pointer in these seven skills resolves and is registered (`check_pointers.py` exit 0; cross-file pointers into `web-design-studio` — accessibility.md §1/§4/§6, accessibility-testing.md §3, color-system.md §7, spacing-system.md §7/§13, style-architecture.md §6/§7/§8, review-checklist's 91 checks in 12 groups, layout-composition.md, conversion-audit.md §7.1/§13 — all land on the heading named). Every `${CLAUDE_SKILL_DIR}`/`${CLAUDE_PLUGIN_ROOT}` path in the seven "Running the scripts" blocks exists, and every sibling script named (audit_design.py, perf_audit.py, measure_vitals.mjs, generate_color_ramp.py, check_roles.py, apply_codemod.py, cluster_values.py, figma_audit.py, figma_to_tokens.py, lint_claims.py, brief_to_log.py with `--into`) exists with the flag the doc uses.
- No leftover of the old id outside the four allowed forms; no `/web-design-suite:` command prefix; no subagent, command or MCP tool is named by these seven skills at all, so none can be wrong.
- The counts the a11y table makes (7 Full, 31 Partial, 17 None of 55) are right and pinned; the WCAG levels quoted beside criteria are right (test-pinned); every attributed figure (GDS, Deque, WebAIM, NEI, GitHub LFS, Supabase's 3,000 and "end of 2026") is registered with its quote.
- The three CI workflows shown (a11y, design, baselines) are consistent with each other and with the suite's recipe tests: bash default shell, no `continue-on-error`, the server waited for in its step, the browser from the lockfile. The matrix's pruning arithmetic (108 vs 1,260 cells; 19 components or 10 with forced colours before 2,000 baselines) checks out.
- Tool versions are stated consistently across the seven skills (axe-core 4.13 in four places; React 19 / Vue 3.5 / Svelte 5 in four; no stylelint/ESLint/Tailwind version appears here).
