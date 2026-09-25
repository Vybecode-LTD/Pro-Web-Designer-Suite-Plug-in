# web-design-suite 3.0.1: full review

**Date:** 2026-09-23.
**Plugin:** `web-design-suite@web-design-suite` 3.0.1, installed at `~/.claude/local-marketplaces/web-design-suite`.
It has 13 skills, 21 Python scripts, 3 Node scripts and 72 tests.
**You asked:**
- (A) are there issues?
- (B) are there gaps?
- (C) how could it become a better, more thorough plugin?

**How to read this.** This page is the summary. Every finding has an ID, and the full write-up is in the detail folder `web-design-suite-review/`. The ID prefix tells you which file it's in:

| Prefix | Area | Detail file |
|---|---|---|
| XC | Plugin as a whole: packaging, README, how Claude runs it, scale | [crosscut.md](web-design-suite-review/crosscut.md) |
| SS | web-design-studio, systems half: tokens, colour, type, layout, starter CSS, generators | [studio-systems.md](web-design-suite-review/studio-systems.md) |
| SB | web-design-studio, build half: stack guides, accessibility and nav references, lint configs, `audit_design` | [studio-build.md](web-design-suite-review/studio-build.md) |
| LC | Lifecycle: token migration, Figma sync, system docs, versioning | [lifecycle.md](web-design-suite-review/lifecycle.md) |
| GT | Gates: accessibility runner, performance budget, component state matrix | [gates.md](web-design-suite-review/gates.md) |
| PS | Persuasion: landing page, client deck, design critique | [persuasion.md](web-design-suite-review/persuasion.md) |
| DL | Delivery: email templates, content model → UI (Supabase) | [delivery.md](web-design-suite-review/delivery.md) |

A **✔** means I re-checked the finding myself after the reviewer reported it. I reproduced it, or confirmed it in the code or the primary docs. The checks are listed in [verification.md](web-design-suite-review/verification.md). Everything else was verified by the reviewer who reported it.

---

## Summary

The suite knows a lot, and most of what it states is accurate. Reviewers checked a few hundred facts and found most of them right: Core Web Vitals thresholds, the WebAIM and GDS figures, the OKLab maths, every contrast figure in the email tokens, and the Baymard and NN/g sources. The scripts also held up against hostile input without crashing.

The problems sit in one place: **the suite's promise that its gates tell the truth.**
- The central audit prints "clean — all nine laws hold" for HTML it never opened, for any value containing `var(`, and for everything inside a media query.
- The runtime contrast check skips the OKLCH colours the suite itself requires.
- The visual-diff default is too coarse to see hover or pressed states.
- The client deck tells the client the page "passes an automated WCAG 2.2 AA check" even when the attached results list violations.

Separately:
- The **Supabase scaffold's defaults** would ship `role` and `is_admin` columns that users can edit themselves, and would display secret tokens.
- The **starter and reference code** fails the suite's own laws: its canonical button shows no keyboard focus ring, its density setting does nothing below the page root, and several of its colour pairs fall below WCAG AA contrast.

Most of the fixes are small. The bigger opportunity, in part C, is structural:
- run the audit as Claude edits, not only at commit;
- tie the docs to the code with tests, so they can't drift apart again;
- prove with an eval suite that the plugin actually helps;
- let each project describe its own design system in one config file, instead of editing the plugin's code.

| Area | Issues (high / medium / low) | Gaps | Improvements |
|---|---|---|---|
| XC plugin level | 0 / 6 / 3 | 6 | 10 |
| SS studio: systems | 4 / 11 / 4 | 7 | 9 |
| SB studio: build | 7 / 15 / 3 | 6 | 10 |
| LC lifecycle | 6 / 15 / 2 | 8 | 12 |
| GT gates | 4 / 11 / 4 | 9 | 13 |
| PS persuasion | 4 / 7 / 11 | 8 | 12 |
| DL delivery | 3 / 10 / 8 | 8 | 9 |
| **Total** | **28 / 75 / 35 = 138** | **52** | **75** |

### Fix these first

1. **The design audit passes code it never checked.**
   - It skips HTML templates and their `<style>` and `style=""` blocks (PS-A4 ✔, SB-B1).
   - A value containing `var(` switches off every raw-value check on that line (SB-A3 ✔).
   - It never checks spacing inside `@media` or `@container` (SB-A4 ✔).
   - A `//` inside `url(…)` hides the rest of the file (SB-A9).
   - A file saved with a byte-order mark fails for no reason (SS-A19 ✔).
2. **The Supabase scaffold's defaults are unsafe.**
   - Secret columns such as `reset_token` and `webhook_secret` are displayed (DL-A1 ✔).
   - `role`, `is_admin`, `owner_id` and `credits` are editable by default (DL-A2 ✔).
   - The docs' account of how row-level security makes writes fail is wrong (DL-A3 ✔).
3. **Keyboard focus is invisible in the reference code.**
   - The canonical button's shadow replaces the focus ring (SB-A1 ✔).
   - The Tailwind `focus-ring` utility removes the outline that high-contrast mode relies on (SB-A2 ✔, SS-A6).
   - The migration codemod rewrites focus rings as card shadows (LC-A5 ✔).
4. **The starter CSS breaks its own laws.**
   - Density doesn't work on a section of the page (SS-A1 ✔).
   - Form fields become unreadable when the page theme and the operating system's dark mode disagree (SS-A2 ✔).
   - `hidden` elements stay visible inside layout components (SS-A3 ✔).
   - Dark-mode error text is 4.38:1 and input borders 1.51:1, both below AA (SS-A4 ✔).
   - A tall modal can't scroll (SS-A5 ✔).
5. **The runtime gates can't see what they exist to catch.**
   - The contrast check skips OKLCH colours (GT-A1 ✔).
   - The visual diff ignores the suite's own hover and pressed states (GT-A3 ✔).
   - A correct modal dialog or iframe is reported as a keyboard trap (GT-A2).
6. **Client-facing output claims more than the evidence supports.**
   - The deck's accessibility, speed and "nine laws" claims are fixed text that ignores the data (PS-A1 ✔).
   - The "known flaws" sheet leaves out confirmed defects (PS-A2 ✔).
   - One ordinary word in a hand-written finding deletes a whole group of machine findings (PS-A3 ✔).
7. **The Figma and token pipeline produces wrong output without saying so.**
   - Figma's current export format becomes invalid CSS, and the run exits 0 (LC-A1 ✔).
   - Translucent colours become solid, because Figma gives opacity as 0–100 and the script expects 0–1 (LC-A2 ✔).
   - A client's own brand colours are rejected as off-palette (LC-A3 ✔).
   - The drift check fails on an unchanged export, because of a timestamp (LC-A4 ✔).
8. **Documented recipes lose work or fail.**
   - The rebase conflict recipe keeps the wrong side and drops a teammate's edits (LC-A6 ✔).
   - The `git stash … && … && git stash pop` sequence never reaches the `pop`: the audit exits with an error first, so the batch is left in the stash (LC-A13).
   - The pre-commit snippets in SKILL.md can't run on Windows and let failing commits through (GT-A4 ✔, SB-A16).
   - The README quick start fails at step 2 (XC-A1 ✔).
9. **No skill says which folder to run its scripts from** (XC-A8 ✔, reported in five of the seven review areas). Taken literally, this writes the user's files into the installed plugin. Separately, the audit baseline stops matching when the same folder is spelled differently, such as a full path instead of `src/` (XC-A9 ✔).
10. **The docs describe tools and behaviour that don't exist.**
    - A token build script, `build-tokens.mjs` (SB-A6 ✔).
    - Tailwind v3 "native cascade layers" (SB-A7).
    - Audit checks that were never written (SB-A11).
    - Runtime features: `--strict`, full keyboard coverage, reduced motion, and clipping at 200% zoom (GT-A10).

### What already holds up

- **Research quality.** Reviewers confirmed:
  - the CWV thresholds and dates, and the WebAIM Million 2026 and GDS figures;
  - axe-core 4.13 as current, and the UCPD and ROSCA readings, with the FTC rule's status correct as of March 2026;
  - Baymard, NN/g and the Deloitte study;
  - every ΔE value in the lifecycle references (to ±0.001);
  - all 38 colour conversions and 20 contrast ratios in the email tokens.
- **Robustness.** No script crashed on hostile input (unterminated comments, 100k-character selectors, 3,000-deep nesting, 50k unclosed tags). Most scripts scale well: 1,500 files in 54 s, and 2,000 files in 9 s for the performance audit.
- **Correct plumbing.** The main migration chain (extract literals → mapping → codemod) uses consistent names, flags, schema and exit codes. All 134 documented commands parse, except the two README lines above. All 21 Python scripts run from any folder when called by their path. Every script parses as Python 3.8 or later. The validators pass, and the 72 tests pass on Python 3.12 and 3.14.
- **Generated code.** The content-model scaffold's output type-checks clean under TypeScript 6 strict with React 19 types, and never injects raw HTML. The plain-text email generator is good. The scaffold's distinction between "you can't see this" and "your filter matched nothing" is a real strength.

---

## A. Issues

This lists every high-severity issue and the most consequential medium ones, grouped by what goes wrong. The detail files have all 138.

### A1. Gates report "clean" on things they didn't check
This is the most important cluster: each item is a false pass on the suite's core promise.

- **PS-A4 ✔ / SB-B1 · high.** `audit_design` walks only CSS and JS. Given an `.html` file, it treats it as JavaScript, ignores `<style>` and `style=""`, and prints "clean — all nine laws hold." Vue, Svelte and Astro files get the same.
- **SB-A3 ✔ · high.** Any `var(--` in a value turns off every raw-value (L1) check for that declaration. For example, `padding: var(--pad-block-sm) 13px`, `transition: opacity 300ms var(--ease-out)` and `box-shadow: 0 1px 2px #000, var(--elevation-card)` all pass.
- **SB-A4 ✔ · high.** Spacing inside `@media`, `@container` and `@supports` is never checked. Container queries are the responsive tool the references themselves recommend.
- **SB-A5 / SB-A12 · high/medium.** The Tailwind v4 theme still generates literal utilities that no gate stops: `duration-300`, `z-50`, `bg-accent/37`, `p-(--space-6)` and `space-y-*`. Off-scale classes such as `p-4` don't cause a build error: they silently produce no CSS.
- **SB-A9, SB-A10, SB-A11, SB-A24 · medium.**
  - `//` inside `url(…)` hides the rest of the file.
  - Rules after a closed `@layer` block are never reported as unlayered.
  - A root-level `components/` folder isn't treated as component code.
  - Tailwind checks date from v3, so `bg-[#hex]`, classes inside `cn()` and `cva()`, and CSS-in-JS all pass.
  - The audit docs promise breakpoint-drift and type-role checks that don't exist.
  - Sass variables holding raw values pass.
- **SS-A19 ✔ · medium.** A CSS file saved with a byte-order mark (PowerShell 5.1's default) fails with a false "unlayered" error, so the pre-commit hook rejects clean commits.
- **XC-A9 ✔ · medium.** The audit baseline only matches when the path is spelled the same way. Audit the same folder by its full path and every baselined finding comes back.
- **GT-A1 ✔ · high.** The runtime contrast check only parses `rgb()`. Chromium reports OKLCH-authored colours as `oklch(…)`, so the suite's own token colours are never measured. Its headline check, contrast under overlays, does nothing on a site built with this suite.
- **GT-A3 ✔ · high.** The visual diff's default per-pixel tolerance (0.10) is coarser than the suite's hover (4%) and pressed (8%) overlays. Deleting `:hover` or `:active`, or changing the border token, still passes all 32 cells.
- **GT-A4 ✔, SB-A16 · high/medium.** The a11y skill's hook snippet has no shebang, so Git for Windows can't run it. It also has no `set -e`, so a design-audit failure is ignored when the accessibility check passes. The shipped hook itself also has faults:
  - it skips when a lint config is missing;
  - it audits Markdown files as JavaScript;
  - it misbehaves in git worktrees.
- **LC-A1 ✔ · high.** Figma's current DTCG export format (2025.10) becomes invalid CSS such as `--space-6: {'value': 24, 'unit': 'px'};`, and both scripts exit 0.
- **GT-A12 · medium.** The state matrix copies `:focus` rules to an attribute that the focus-visible cells never carry, so correct focus rings are reported as missing.

### A2. False alarms that teach people to ignore the gates
- **GT-A2 · high.** A correct `<dialog>` opened with `showModal()` is reported as a keyboard trap, plus 8 more errors. So is a same-origin iframe.
- **GT-A14, GT-A18, GT-A8 · medium.**
  - A disabled button is flagged for contrast, although WCAG exempts it.
  - A spinner makes the focus check pass wrongly.
  - Best-practice heading and landmark rules are treated as WCAG errors.
  - The recommended axe tag set drops all WCAG 2.1 rules.
- **GT-A5 · medium.** A page with a Content-Security-Policy header crashes the run with exit 1, which the docs define as "violations found".
- **LC-A3 ✔ · high.** The Figma audit hard-codes the studio's own palette, so a client's brand ramp gives 11 "off-ramp" errors. The docs tell users to edit the plugin script to fix this.
- **LC-A4 ✔ · high.** A timestamp in every generated file makes the documented CI drift check fail on an unchanged export.
- **SB-A14 · medium.** stylelint, ESLint and `audit_design` disagree on nesting depth, on literal `0`, on margins and on `var()` fallbacks, so the same line passes one gate and fails another.

### A3. Shipped code breaks the suite's own laws
- **SB-A1 ✔ · high.** In the canonical Button (stack-vanilla-css and stack-css-modules), the component's `box-shadow` replaces the reset's focus ring, so keyboard users see nothing. This fails WCAG 2.4.7.
- **SB-A2 ✔ · high.** The Tailwind `@utility focus-ring` sets `outline: none`, so in Windows high-contrast mode the focus indicator disappears. pattern-invention.md does the same (SS-A6).
- **SS-A1 ✔ · high.** Density (Law 7) doesn't work on a section of the page, which is how every doc uses it. The spacing roles are resolved once at the root and inherited as fixed values. For the same reason, a dark-themed section keeps light-theme shadows.
- **SS-A2 ✔ · high.** The page's colour tokens and the browser's `color-scheme` can disagree. When they do, native inputs render at 1.63:1 (OS dark, page light) or 1.12:1 (page dark, OS light).
- **SS-A3 ✔ · high.** The `[hidden]` rule sits in the lowest layer, so `.stack[hidden]` and `.cluster[hidden]` still display. The overrides file that was meant to fix this was never shipped.
- **SS-A4 ✔ · high.** Dark-mode error text is 4.38:1 on the canvas and 4.24:1 on surfaces. `.inverse` headings are 1.10:1. Input borders are 1.51:1, where WCAG 1.4.11 needs 3:1. No gate checks colour pairs.
- **SS-A5 ✔ · medium.** The reset removes the browser's size limit on `<dialog>`, so a tall modal runs off-screen and can't scroll.
- **SS-A6, SB-A22, PS-A16 · medium.** Many of the references' own CSS examples fail `audit_design --strict`: focus rings, motion recipes and Tier-1 token reads.
- **SB-A8 · medium.** The canonical `index.css` places vendor CSS above every layer, which is the opposite of what its comment says.
- **DL-A9 to DL-A12 · medium.**
  - The generated forms don't link their error and help text to the inputs.
  - In dark mode the email call-to-action is 2.56:1.
  - Classic Outlook falls back to a serif font, because the rule the docs describe is never injected.
  - The receipt template is a fixed 600px wide in Gmail apps that ignore `<style>`.

### A4. Security: content-model-to-ui with Supabase
- **DL-A1 ✔ · high.** Credential detection matches a short list of exact column names, although the docs promise `*_token` and `*_hash` patterns. `api_token`, `reset_token`, `webhook_secret` and `token_hash` are shown and editable. The docs' own `select('*')` sends secrets to the browser anyway.
- **DL-A2 ✔ · high.** Columns that carry authority (`role`, `is_admin`, `credits`, `org_id`, `owner_id` and `plan`) are editable by default and included in the Draft type. Under Supabase's standard profile policy, users could promote themselves. A TypeScript type is not access control.
- **DL-A3 ✔ · high.** The docs' model of how writes fail under row-level security is wrong, and following it produces the wrong code:
  - Postgres foreign-key and unique checks bypass row-level security, so attaching a row to another tenant's record succeeds; it doesn't raise `23503`.
  - An update or delete on a hidden row changes 0 rows and reports success.
- **DL-A4 to DL-A6 · medium.**
  - The optimistic-update sample never throws on permission errors (it lacks `throwOnError()`).
  - The pagination cursor is pasted unsanitised into `.or()`.
  - The `security definer` helper is unsafe.
  - The parser ignores `ENABLE ROW LEVEL SECURITY` and `CREATE POLICY` statements.

### A5. Pipelines that produce wrong output without warning
- **LC-A2 ✔ · high.** Figma gives a composed colour's opacity as 0–100, but the script uses it as 0–1, so every translucent hover and scrim becomes opaque. An alias in the colour channel is output as a Python dict.
- **LC-A5 ✔ · high.** The migration codemod rewrites a spread-only focus ring as `var(--elevation-card)` with "snapped" confidence, so the rewrite survives `--skip-review`.
- **LC-A10 ✔, LC-A11, LC-A12, LC-A14 · medium.**
  - SvelteKit's `src/lib` is skipped as vendor code.
  - Negative margins are mapped to a different token than the padding they cancel.
  - 15px text is snapped down while the note says "text does not shrink".
  - The font guard blocks colour renames.
- **LC-A8, LC-A9, LC-A19 · medium.**
  - `diff_system` recommends a patch release when only density, reduced motion or the root element changed.
  - A new dark-theme override that drops contrast below 3:1 is classified as a minor release.
  - The two tools that each claim to share the same Tier-1 leak rule disagree about it.
- **SS-A9 · medium.** The generators can't reproduce the starter tokens. The Phase-1 commands in SKILL.md produce steps below 11px and a pinkish neutral, and the brand's exact hex is dropped from the palette.
- **DL-A7, DL-A8, DL-A14 · medium/low.**
  - Supabase's own `db pull` and `gen types` output is misread: quoted identifiers, identity columns and wrapped enums.
  - The money answers (currency and scale) are ignored, so JPY is formatted as USD divided by 100.
  - The email CSS inliner gets shorthand-then-longhand padding wrong.

### A6. Client-facing output claims more than the evidence
- **PS-A1 ✔ · high.** The deck's "The honest claim: this page passes an automated WCAG 2.2 AA check and has been keyboard-tested by hand" is fixed text. It appears right beside a table of critical and serious violations, and no input records any keyboard test. Similarly, "It is fast, and it stays fast" appears at 152% of budget, and "Nine laws, machine-enforced" is claimed although the audit checks only six.
- **PS-A2 ✔ · high.** The defence sheet leaves out confirmed defects and keeps unconfirmed suspicions. The client slide "What we are not happy with yet" inherits the same inversion.
- **PS-A3 ✔ · high.** A hand-written finding that contains a rule's name as an ordinary word (for example "the most important plan", when the rule is called `important`) silently removes that rule's machine findings. This also defeats `--audit-blocking`.
- **PS-A6, PS-A7, PS-A10 · medium.**
  - The printed "handout" includes every presenter note ("The pause is the ask").
  - A reversed decision is presented as current.
  - Suggested lines such as "It loads in under two seconds" come from a byte count, not a measurement.
- **PS-A8, PS-A9 · medium.**
  - The skills give opposite instructions for risky client requests.
  - DSA Article 25 doesn't add anything for ordinary company sites.
  - The Digital Fairness Act is "announced", not "proposed".
- **PS-A11 · medium.** After compaction Claude Code keeps only the first 5,000 tokens of an invoked skill. landing-page-conversion's ethics section starts at about token 4.8k, so a long page build loses it.

### A7. Documented recipes that fail or lose work
- **LC-A6 ✔ · high.** During a rebase, `git checkout --theirs` means your commit, so the recipe discards the teammate's change. The codemod then reports 0 replacements with exit 0.
- **XC-A1 ✔ · medium.** The README quick start fails at steps 2–4 (a missing `-o literals.json` and a missing `-m`). The migration SKILL.md has it right.
- **LC-A13, LC-A18, GT-A11, GT-A15 · medium.**
  - `git stash … && … && git stash pop` leaves the batch stranded in the stash.
  - The docs and CI snapshot different folders, so an unchanged repo reports drift.
  - The docs ask for comments in `perf-budget.json`, which both parsers reject.
  - The CI recipes don't wait for the server, never install Playwright, swallow errors with `|| true`, and are bash-only on Windows runners.
- **SB-A13, SB-A17, SB-A18, SB-A19, SB-A20 · medium.**
  - The ESLint `style` rule rejects the pattern the references document.
  - `npm i stylelint@^16 stylelint-config-standard` would fail with ERESOLVE, because the current config needs stylelint 17 (read from the registry, not run), and ESLint 9 is past end of life.
  - The tailwind-merge config drops classes.
  - `border-default` also paints the border in body-text colour.
  - The navigation reference code has four behaviour bugs.
- **SS-A12 · medium.** The `@property` recipe is invalid, so the browser discards it.

### A8. Docs that describe things that don't exist or aren't true
- **SB-A6 ✔ · high.** handoff-conventions describes a `design/tokens.json` → `build-tokens.mjs` pipeline and a CLAUDE.md template that forbids editing tokens.css. The script doesn't exist, and tokens.css is the only real source.
- **SB-A7 · high for Tailwind v3 clients.** The claim that v3 emits into three native cascade layers is false: the utilities come out unlayered and beat every hand-written layer.
- **GT-A10, GT-A7, GT-A9 · medium.**
  - The runtime has no `--strict`, doesn't test half the keys it lists, doesn't implement reduced motion, and doesn't check for clipping at 200% zoom.
  - The Deque and GDS studies are misdescribed, and the coverage table's own counts are wrong.
  - "Not Evaluated" is recommended for A and AA criteria in an ACR, although VPAT allows it only for AAA.
- **SS-A11, SS-A13, SS-A8 · medium.**
  - Container queries no longer apply layout containment (a CSS Working Group resolution that has shipped in browsers).
  - The claim that the status colours are safe for colour-blind users is false: they are 4 L-points apart, not 33.
  - color-system §6 contradicts tokens.css.
- **SB-A21, SS-A16, GT-A19, DL-A15 to DL-A17, LC-A7, LC-A15, LC-A16 · low/medium.** Dated or wrong facts:
  - EU and ADA legal baselines;
  - WCAG levels;
  - email client support;
  - Outlook end-of-support dates;
  - Figma plan limits (the Plugin API and MCP work on non-Enterprise plans);
  - Tailwind, Bootstrap and MUI behaviour.
- **XC-A3 · medium.** "Any single `.skill` file works standalone" is not true: no `.skill` files ship, and at least eight skills depend on web-design-studio's audit.

### A9. Integration and scale
- **XC-A8 ✔ · medium, also reported as SS-A14, LC-A20, DL-A19 and GT-C6.** Every skill says to run `python -m scripts.X src/` "from the skill root". The `-m` form needs the skill folder, while `src/` means the user's project, and none of the skills uses `${CLAUDE_SKILL_DIR}`. Taken literally, this does three things:
  - it writes `literals.json`, `proposal/` and the deprecation ledger into the installed plugin;
  - it misses the project's baseline;
  - it leaves `__pycache__` in the install (XC-A4).
- **XC-A6 ✔, XC-A7 ✔ · medium.** Two scripts slow down quadratically:
  - `a11y_static` takes 46 s on a 4,000-row page and didn't finish a 2.8 MB page in 180 s.
  - `extract_literals` takes 12.5 s on 387 KB of minified CSS.
  - The profiler pins both to work that is recomputed per element and could be computed once, so both fixes are small.
- **XC-A2, XC-A5 · low.** The install placeholder in the README, and a `shared/` copy of the token contract that nothing references.

---

## B. Gaps

1. **Nothing checks the docs against the code.** There is no eval suite, no CI, and no browser-backed, lint-config or doc-snippet tests (XC-B2, XC-B3, SB-B2, SS-B7, GT-C1). The 72 tests cover script regressions only. Most of part A lives in the space between references, starter files, configs and scripts, which is exactly what those tests would catch.
2. **The plugin uses only one of Claude Code's extension points: skills** (XC-B1). It has no hooks, workflow commands, subagents or config. Law 9, "nothing ships un-audited", is never applied to Claude's own edits.
3. **Projects can't describe their own system.** Brand ramps, added roles and custom breakpoints all require editing plugin code, which the next update overwrites (LC-B3, LC-A3).
4. **The Supabase path has no access boundary** (DL-B1, DL-B2).
   - Nothing covers which key goes where, and the legacy anon and service-role keys stop working at the end of 2026.
   - Nothing covers forwarding the user's login token from FastAPI.
   - Nothing generates row-level-security policies, column grants or server-side validation.
5. **The docs promise checks that nothing runs:**
   - role-pair contrast per theme (SS-B1);
   - focus and forced-colors (SB-B3);
   - email dark mode and the layout without `<style>` (DL-B6);
   - honesty of claims on persuasive pages (PS-B6);
   - the cheap automatable accessibility checks: text spacing, focus hidden behind a sticky header, reduced motion, clipping (GT-B6).
6. **Modern stacks and formats aren't covered:**
   - DTCG 2025.10, Style Dictionary, Tokens Studio and Terrazzo (LC-B2);
   - Figma without an Enterprise plan (LC-B1);
   - single-page apps, logged-in pages, shadow DOM, and several URLs or viewports per run (GT-B1 to GT-B4);
   - linting SCSS; Next.js App Router, Vue, Svelte and Astro (SB-B6);
   - Tailwind v4 variants (SB-B5);
   - `light-dark()` theming (SS-B3);
   - MJML and React Email (DL-B4);
   - right-to-left layouts and translation (DL-B5).
7. **Compliance guidance is out of date:**
   - the UK DMCC Act, and EU rules on "was" prices, personalised prices and the withdrawal button (PS-B2);
   - consent for session recording and heatmaps (PS-B8);
   - bulk-sender rules for Microsoft and Google (DL-B7);
   - the WCAG 2.2 criteria that persuasive patterns touch (PS-B1).
8. **Windows ergonomics** (XC-B5). The docs are bash-first: `\` line continuations, `&&`, `/tmp`, globs that cmd and PowerShell don't expand, and `python3`. That's fine for Claude through Git Bash, but it breaks for a person pasting into cmd.
9. **Discoverability in a crowded install** (XC-B6). In this environment all 13 skills are listed by name only. The 13 descriptions total about 11.8k characters, which is more than the whole 8,000-character fallback budget. Users can't choose which plugin skills keep their descriptions either, because `skillOverrides` doesn't apply to plugin skills.

---

## C. How to make it better and more thorough

These come in three kinds: more **trustworthy**, more **integrated** with Claude Code, and broader **coverage**. The Claude Code facts they rely on are in [claude-code-capabilities.md](web-design-suite-review/claude-code-capabilities.md).

### More trustworthy
- **C1 · Make the gates precise before automating them.** SB-C1 and PS-C3; each item closes a specific issue:

  | Change | Closes |
  |---|---|
  | Tokenise values (strip `var()` including its fallback, then scan the rest) | SB-A3 |
  | Audit templates (`<style>`, `style=""`, single-file components) | PS-A4 |
  | Per-extension comment rules; a stack of open layers; `utf-8-sig`; skip `url(#…)` | SB-A9, SS-A19 |
  | Fail with "0 files audited" when nothing matched | — |
  | Key the baseline on paths relative to the baseline file | XC-A9 |
  | Say "L1–L6 hold", not "nine laws" | — |
  | Runtime: resolve colours through a canvas; skip inert, `:modal` and hidden content; inject axe into iframes; `bypassCSP`; pause animations; exempt disabled controls | GT-C2 |
  | Matrix: check that each hover, active and focus cell differs from its default cell | GT-C3 |

- **C2 · Add the missing checks as tools.**
  - `check_roles.py`: resolves the Tier-2 roles for light, dark and `.inverse`, checks the declared pairs, and generates the table that color-system.md quotes (SS-C2).
  - A security pass in the schema reader: sensitive-column classes, row-level security and policy parsing, and a summary printed first (DL-C1).
  - `tw_probe`: compiles candidate classes against the project's own Tailwind (SB-C3). Also move to eslint-plugin-better-tailwindcss (SB-C4).
  - `lint_claims.py` (PS-C6).
  - Render scripts for email (light, dark and no-style PNGs) and critique (blur, greyscale, 390 and 1440px) (DL-C3, PS-C5).
- **C3 · Tie the docs to the code so they can't drift apart again.** One test module can:
  - extract every CSS and TSX block from the references and run it through the audit, with an explicit anti-example marker for deliberate bad examples;
  - assert every "Verified n:1" comment and every `clamp()` anchor;
  - run every documented command against its real argument parser;
  - resolve every § pointer by keyword;
  - check the 14 token-contract copies are identical;
  - validate every description.

  Add one rule spec shared by `audit_design`, stylelint and ESLint, with conformance fixtures (SB-C2), and inject snippets from the starter files into the references (SS-C4). Sources: SS-C3, SB-C5, XC-C5, DL-C6, LC-C12.
- **C4 · Test in a real browser and a real CI.**
  - Browser tests that skip when no browser is found (GT-C1, SS-C1).
  - ESLint, stylelint and Tailwind fixtures.
  - A Windows/Linux/macOS × Python 3.10–3.14 matrix in a pinned Playwright container (XC-C6, GT-C12).
- **C5 · A dated evidence register.** Record each figure's value, source, date checked and quote, with a test that every number in the docs is registered (PS-C10). Regenerate the email client matrix from caniemail's data (DL-C9).

### More integrated with Claude Code
- **C6 · Run scripts by path, `python "${CLAUDE_SKILL_DIR}/scripts/X.py" src/`, from the project root** (XC-C10). Cross-skill calls use `${CLAUDE_PLUGIN_ROOT}/skills/…`. Pre-approve the plugin's own scripts with `allowed-tools`. This is small, removes a whole class of bugs, and should come first.
- **C7 · An opt-in design-gate hook**, added after C1 (XC-C2, SS-C6, GT-C9, LC-C8, DL-C7).
  - It runs after Edit or Write on CSS, SCSS, HTML, JSX and TSX, audits the changed file, and returns the findings to Claude as context.
  - It uses exec form (`python` plus the script path), so it works on Windows.
  - The plugin is installed for every project, so the hook must do nothing unless the repo opts in, with a `userConfig` switch as the global off.
  - Companions: a guard that blocks edits to files marked "GENERATED — DO NOT EDIT", and a `tokens.css` watcher that reports the version bump and any contrast drop.
- **C8 · Workflow commands.** Commands are now skills; set `disable-model-invocation: true` so they cost nothing in the listing. Proposed set (XC-C3, LC-C9, GT-C9, PS-C11, DL-C7):
  - `/web-design-suite:gate`: design, accessibility and performance audits of the changed files in one run.
  - `/web-design-suite:install-gate`: copy the hook, configs and project contract into the repo.
  - `/web-design-suite:new-system`: brand colour → ramps, type scale, tokens.css, role check.
  - `/web-design-suite:critique`: an adversarial critique in a fresh context.
  - `/web-design-suite:migrate`: census → proposal → reviewed batches.
  - `/web-design-suite:release-check`: extract → diff → gate → changelog → upgrade guide.
  - `/web-design-suite:figma-sync`: uses the Figma MCP server when it's available.
  - `/web-design-suite:tw-probe`.
- **C9 · Subagents**, which keep heavy output and references out of the main context:
  - `design-critic`: read-only, fresh context, returns findings.json, because self-critique in the same context is the blind spot the skill describes (PS-C4);
  - `gate-runner`: runs the runtime scripts and returns only the findings (GT-C9);
  - `supabase-security-reviewer` (DL-C7);
  - `codemod-batch-reviewer` (LC-C9).
- **C10 · One project contract.** `.design-suite.json` holds the token files, component globs, stack, budgets and baselines. A `contract.json` generated from the project's tokens.css replaces the five hard-coded copies of ramps and scales. Every script, the hook and the commands read it (LC-C1, XC-C8).
- **C11 · An eval suite** (`claude plugin eval`, with ablation against a no-plugin baseline; XC-C1).
  - **Routing cases** per skill, including sibling-specific and "must not fire" cases:
    - "screenshot-diff every button state" → matrix, not docs;
    - "write the newsletter copy" → not the email skill.
  - **Outcome cases** from this review:
    - a DTCG 2025.10 export (LC-C10);
    - a profile form from a Supabase schema (DL-C7);
    - a dark-mode receipt (DL-C7);
    - an audit that passes while compliance is still not claimed (GT-C10);
    - a deck built from failing accessibility data never says "passes" (PS-C7);
    - a compact section whose gap actually shrinks (SS-C7);
    - a Tailwind button whose focus survives forced colors (SB-C6).
  - **Running it here:** routing-only cases run natively on Windows. Cases that run scripts need Bash, which needs WSL2 on this machine. Use `--max-cost-usd`, and `--runs 1 --ablation none` while iterating. The default threshold is 1.0.
- **C12 · Leaner skills, sharper routing.**
  - SKILL.md files are 4.3k–7.0k tokens. Bring each to about 5k or less, with the rules that must survive compaction (ethics, the laws, evidence discipline) at the top.
  - Move worked examples, CI YAML and tables into references.
  - Split navigation-patterns.md (about 29k tokens, too large to read in one pass).
  - Rewrite descriptions to about 350 characters, leading with a sentence that works on its own and adding a "not for…" line. This separates siblings that currently collide: studio vs landing, matrix vs docs, critique vs landing, deck vs pptx.
  - Sources: XC-C7, SS-C8, SB-C8, LC-C11, GT-C7, GT-C8, PS-C8, PS-C9, DL-C8.
- **C13 · Release engineering** (XC-C6).
  - A `tools/build.py` that builds the zip and the 13 `.skill` files reproducibly, with no bytecode.
  - A `.gitignore`, and `sys.dont_write_bytecode` in each script.
  - A CHANGELOG (the suite teaches changelogs but doesn't keep one), and `claude plugin tag`.

### Broader coverage
- **C14 · Tokens and Figma.**
  - A shared `dtcg.py` that reads and writes 2025.10, reads Tokens Studio themes, and maps `$deprecated` into the deprecation ledger (LC-C2).
  - A Figma MCP route with a `plugin-script` output for non-Enterprise teams (LC-C7).
  - Weight, `.inverse` and on-status roles (SS-B2, SB-B4).
  - Teach `light-dark()` (SS-B3).
- **C15 · Gates.**
  - `--wait-for` and `--steps` for single-page apps.
  - `--storage-state` for logged-in pages.
  - Shadow DOM queries, and a URL list with several viewports (GT-B1 to GT-B4).
  - The automatable accessibility checks from B5.
  - A `lighthouse` throttle preset, with TTFB taken from CDP, plus `crux_check.py` for field data (GT-C11).
  - Custom states in the matrix (GT-A13).
- **C16 · Build.** SCSS linting (`stylelint-config-standard-scss`), guidance for Next.js App Router, Vue, Svelte and Astro, and Tailwind v4 variants (SB-B5, SB-B6).
- **C17 · Delivery.**
  - Generate a `policies.todo.sql` per table, plus a matching zod or pydantic schema (DL-B2).
  - Prisma and Drizzle input (DL-B3).
  - MJML or React Email output from the email tokens (DL-B4).
  - A right-to-left email template (DL-B5).
- **C18 · Persuasion.**
  - Make the deck honest by construction: wording chosen from the data, manual-test evidence taken as an input, a `--handout` print, and a presenter window (PS-C1).
  - Fix the critique merge and add a status field (PS-C2).
  - Dated "flag for legal review" tables for the UK and EU (PS-B2).
  - Map persuasive patterns to the WCAG criteria they touch (PS-B1).

---

## Roadmap

| Phase | Version | What ships | Why this order |
|---|---|---|---|
| **1. Stop the false greens and unsafe defaults** | 3.1.0 | The 28 high-severity issues plus the confirmed mediums (XC-A6 to A9, SS-A5, SS-A19, LC-A10), each with a fail-before/pass-after test. The README quick start and the rebase and stash recipes. `${CLAUDE_SKILL_DIR}` commands (C6). About the size of the 3.0.1 pass. | Everything else builds on gates that tell the truth. The minor version bump is deliberate: the audit will now find things it used to miss, so the release notes should tell users to re-baseline. |
| **2. Tie the docs to the code** | 3.2.0 | The C3 test module, browser and config fixtures (C4), `check_roles.py`, one shared rule spec, the medium-severity doc corrections (A7, A8), the evidence register, and the SKILL.md diet and new descriptions (C12). | This stops part A from coming back. It also has to come before the hook, or the hook would push stale advice into every edit. |
| **3. Become a full Claude Code plugin** | 3.3.0 | The opt-in hook (C7), workflow commands (C8), subagents (C9), the project contract (C10), the eval suite with CI and a cost cap (C11), and release tooling (C13). | The gates are now accurate enough to run on every edit, and the evals prove the plugin helps compared with no plugin. |
| **4. Broaden coverage** | later 3.x releases | C14 to C18, in the order your projects need them. The Supabase security items (C17) should move into phase 1 if a client project uses that scaffold before then. | Each item is independent and fits its own release. |

---

## Method and evidence

- **Who reviewed what.** Six reviewer agents ran in parallel, one per skill group, with each reading its SKILL.md, references, assets and scripts in full. I did the seventh area, the plugin-level (XC) pass, myself. A research agent gathered the current Claude Code plugin capabilities from the live docs and the local 2.1.280 CLI.
- **How things were run.** Every script was run on copies, with bytecode writing off. Nothing in the installed plugin was changed by this review. The tools used, already on this machine or read-only from other `C:\DEV` projects:
  - headless Chrome 153 with Playwright 1.63 and axe-core 4.13;
  - tailwindcss 4.3.1 and 3.4.19;
  - ESLint 9 and 10, typescript-eslint and tailwind-merge;
  - TypeScript 6.0.3 in strict mode with React 19.2 types;
  - real git repos for the hook, rebase and stash recipes.
- **Sources.** Facts were checked against primary sources: W3C and WCAG, MDN, the CSS Working Group, Postgres, Supabase, Figma, DTCG, Tailwind, caniemail, Microsoft, Google, EUR-Lex and the UK CMA. Links are in each detail file.
- **My own checks.** I re-checked 25 of the 28 high-severity issues myself, plus 5 medium ones; see [verification.md](web-design-suite-review/verification.md). The three I didn't re-run are SB-A5 and SB-A7, which need Tailwind builds, and GT-A2, which needs browser fixtures. They rest on the reviewers' own runs. Where I found or profiled something myself, that's recorded in crosscut.md.
- **Not tested:**
  - the live Figma REST API, which is Enterprise-only;
  - real Outlook and Gmail renders;
  - macOS;
  - GitHub-hosted Windows runners;
  - forced-colors emulation;
  - stylelint, which isn't installed here;
  - a side-by-side comparison with Lighthouse.
- **Cost.** The seven agents (six reviewers and the research agent) used about 3.8M tokens in total.
- **Raw material:**
  - `web-design-suite-review/`: the seven detail reports, `claude-code-capabilities.md` and `verification.md`;
  - `web-design-suite-review/persuasion-fixtures/`: the persuasion repro inputs;
  - the session scratchpad under `review\`: the other reviewers' fixtures, which are temporary and may be cleared by Storage Sense.
