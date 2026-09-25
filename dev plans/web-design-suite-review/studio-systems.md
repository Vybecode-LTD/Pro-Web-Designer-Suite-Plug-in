# web-design-suite 3.0.1 review: web-design-studio, systems half (SS)

Scope: SKILL.md; references token-contract, spacing-system, color-system, typography, motion-system, layout-composition, style-architecture, pattern-invention; starter tokens/reset/base/layout.css; generate_color_ramp.py and generate_type_scale.py. Reviewed 2026-09-23. "Chrome 153" results come from headless Chrome running the **shipped starter CSS**; contrast figures use the plugin's own generator maths. The plugin was not modified, and nothing here repeats the bug-fix report's tables.

## A. Issues

**SS-A1 · high · Law 7 (density) does nothing on a subtree, which is how every doc uses it.** Where: tokens.css:77-79, :487-489; spacing-system.md:536-546; layout.css:851-855 (`.region-compact`); layout-composition.md:43, :815; typography.md:426-434; pattern-invention.md:368.
- **Cause:** Tier-2 roles (`--gap-grouped: calc(var(--space-4) * var(--density))`) are declared on `:root`, resolved there, and inherited as finished values. A descendant `[data-density]` changes only `--density`.
- **Evidence (Chrome 153):** `.stack` row-gap is 16px at the root, in `compact`, in `spacious`, and in `.region-compact`. In the compact section `--density` is 0.875 but `--gap-grouped` is `calc(1rem * 1)`.
- **Same cause breaks subtree themes:** in `<section data-theme="dark">`, `--bg-canvas` flips, but `--elevation-card` keeps the light shadow (alpha .06 vs .36) and `--shadow-focus` keeps a light gap ring.
- **Sibling contradiction:** component-state-matrix/SKILL.md:178-180 documents this trap and says it "never surfaces" because density lives on `<html>`. The studio docs teach the opposite, and the layout-composition.md:815 check can never fail.
- **Fix:** re-declare density-derived roles on `:root, [data-density]` and theme-derived tokens on `:root, [data-theme]`, as two separate groups. Add a browser test (SS-C1). Confidence: high.

**SS-A2 · high · Native form fields become unreadable when the theme and `color-scheme` disagree.** Where: reset.css:110 (`color-scheme: light`); tokens.css:425-471 (the dark block never sets `color-scheme`); tokens.css:473-480 (the OS media query flips the scheme but no tokens).
- **OS dark, no `data-theme`** (the starter ships no script): the page is light, but `<input>` renders rgb(59,59,59) with `--fg-default` text, **1.63:1**.
- **OS light, `data-theme="dark"` chosen:** the scheme stays light, so fields are #fff with neutral-100 text, **1.12:1**. `<select>` behaves the same. style-architecture.md:456 mentions `color-scheme` only in prose.
- **Fix:** set `color-scheme` inside the `[data-theme]` blocks, drop the scheme-only media block, ship the no-flash script, or use `light-dark()` (SS-B3). Confidence: high.

**SS-A3 · high · The `hidden` attribute loses to every layout primitive.** Where: reset.css:405-423.
- `[hidden]{display:none}` sits in the weakest layer. Its comment (:411) says the authoritative copy is the last rule of `overrides.css`, which no skill ships.
- **Evidence (Chrome 153):** `<div class="stack" hidden>` and `.cluster[hidden]` compute `display: flex`.
- **Fix:** ship overrides.css (SS-C9), or allow one sanctioned `!important` for `[hidden]`. Confidence: high.

**SS-A4 · high · Shipped role pairs fail WCAG 2.2 AA, and no gate checks them.**
- **Dark error text:** dark `--fg-danger` (danger-500, tokens.css:462) is 4.38:1 on `--bg-canvas` and 4.24:1 on `--bg-surface`, failing 1.4.3.
- **`.inverse`:** base.css:626-631 ships the class. base.css:619-623 says to add re-points in tokens.css, but none exist. Headings are **1.10:1**, links 2.51:1, `small`/`figcaption` 2.74:1 (Chrome confirms these colours render).
- **Input borders:** `--border-default` is assigned to "card and input outlines" (tokens.css:287). It measures 1.51:1 on surface, 1.43:1 on canvas, 1.38:1 dark; even `--border-strong` is 2.53:1. Understanding 1.4.11 requires 3:1 for an input's complete border (w3.org/WAI/WCAG22/Understanding/non-text-contrast.html), and color-system.md:292/:633 says so too.
- **Fix:** add `--danger-400` for dark, an `.inverse` role block and a `--border-input` role at ≥3:1, then build SS-B1. Confidence: high.

**SS-A5 · medium · reset.css removes the browser safety net that keeps a modal on screen.** Where: reset.css:452-453 (`dialog { max-inline-size: none; max-block-size: none }`).
- **Evidence (Chrome 153):** `showModal()` with 3000px of content in a 704px viewport spans -1162 to 1866px. clientHeight equals scrollHeight, so it cannot scroll.
- **Control:** with `max-block-size: revert`, the browser default `calc(100% - 38px)` applies, the dialog is 666px tall and scrolls.
- This contradicts layout-composition.md:380. **Fix:** keep the browser defaults. Confidence: high.

**SS-A6 · medium · The references' own CSS examples fail the plugin's gate.** I ran `audit_design --strict` on 71 extracted css blocks, skipping blocks marked WRONG, token blocks and `@font-face`.
- **Focus rings:** pattern-invention.md:474/:611/:718 use `outline:none; box-shadow:var(--shadow-focus)`. That is an L6 error, and `outline:none` overrides reset's transparent outline, so there is **no focus ring in forced-colors mode**. This breaks token-contract.md:109 and the pattern gate's own H3.
- **Other failures:** pattern-invention.md:469/:501 (L2 margins); motion-system.md:480 (L6); color-system.md:491-511 (4× L6 + L1 `z-index:-1`); spacing-system.md:428-429 (L2); typography.md:251 and :372-373 (L6, see SS-A10).
- **Motion recipes:** motion-system.md:174, :244-247, :401, :424 and :452-528 split `--dur-*` from `--ease-*`. That raises `tier1-motion` warnings, which fail `--strict` (SKILL.md:97).
- **Fix:** correct the examples and add SS-C3. Confidence: high.

**SS-A7 · medium · The skill gives four incompatible prose rhythms and two `.center`s.**
- **Gap after a heading:** 8px (spacing-system.md:454), 12px (typography.md:170), 16px (base.css:414-416), 12px (layout.css:264 `.flow`). **Gap above an h3:** `--space-block`, `--gap-distinct`, `--space-block`, `--space-subsection`.
- **Heading after heading:** typography.md:172-173 gives it the larger gap, base.css:410-413 the smaller. base.css:361-366 allows only `.prose` as an owl, yet layout.css ships `.flow`.
- **`.center`:** spacing-system.md:518-526 uses `inline-size: min()` and argues against the max-width + padding approach that layout.css:679-686 uses.
- **"Quoted" code isn't:** layout-composition.md:5 claims its code is quoted from layout.css, but :403 reads an undeclared `--media-object-gap`, and :667 teaches an inline `style="background:…"` (a Law 4 violation).
- **Fix:** make base.css/layout.css the single source (SS-C4). Confidence: high.

**SS-A8 · medium · color-system.md §6 contradicts tokens.css.**
- **Role table (:280-295) vs tokens:** light `--bg-accent` 500 (tokens: 600); dark `--fg-muted` 400 (300), dark `--fg-subtle` 500 (400), dark `--border-focus` 400 (never re-pointed, so 600).
- **Lightness:** :30 gives `--neutral-500` L 0.580; the tokens use 0.535 ("Do not lighten it").
- **Stale audit section:** "Two live audit findings" (:320-333) still reports fg-subtle at 4.07:1 and prescribes 600. The tokens already fixed it another way (4.60:1 on sunken, 4.91:1 on canvas).
- **Comment mismatch:** "Verified 8.22:1" at tokens.css:439-441 is neutral-400's ratio, but the line maps neutral-300 (13.80:1).
- **Risk:** Claude "fixes" solved problems. **Fix:** generate the table from tokens.css (SS-C2). Confidence: high.

**SS-A9 · medium · The generators can't reproduce the starter, and SKILL.md's Phase-1 commands produce off-system output.**
- **Type:** generate_type_scale.py:26-30 says `--snap-px --fluid 380 1440 --fluid-steps 2` reproduces tokens.css "approximately". It prints 9/11/13/16/20/25/31/39/49, 49→61, 61→76.5; the starter ships 11/12/14/16/18/22/28/35/44, 44→72, 56→110.
- **SKILL.md:72** (no `--snap-px`) prints "warning: smallest step is 9.26px" plus 13.33/11.11px steps, breaking typography.md:44 and :478.
- **Colour:** SKILL.md:67 seeds the neutral from the accent, giving hue 36, which color-system.md:556-558 says "would read pink". `NEUTRAL_L[500]=0.580` (generate_color_ramp.py:120) regenerates the 4.08:1 fg-subtle failure that tokens.css:212-216 fixed by hand.
- **Brand hex lost:** `build_ramp` (:444) discards the seed's lightness, so `#e8440a` becomes `--accent-500: #f14d1a` and the brand hex appears nowhere, undocumented.
- **Fix:** SS-C5. Confidence: high.

**SS-A10 · medium · The weight axis of the hierarchy method is illegal under L6.** typography.md:251 ("Right": `.card { font-weight: var(--weight-semibold) }`) and :372-373 ("weight + colour, no size change") produce `tier1-leak` errors (verified; audit_design.py:147). The only legal carrier, a `--type-*` shorthand, also changes size, and the contract (token-contract.md:95) has no Tier-2 weight role. The starter also uses four weights against typography.md:413/:486 "at most 3". **Fix:** add weight roles or `--type-*-strong` variants.

**SS-A11 · medium · The container-query containment facts are out of date.** Where: layout-composition.md:414, :416; layout.css:806, :818-822.
- The CSS Working Group resolved on 2024-07-24 (csswg-drafts#10544) that `container-type` no longer applies layout containment. css-conditional-5 now says "Applies style containment and inline-size containment … and establishes an independent formatting context"; mdn/content#43405 says this shipped in Chrome, Firefox and Safari.
- **Evidence (Chrome 153):** a `position: fixed` child of an `inline-size` container lands at the viewport origin.
- **Fix:** delete the "portal fixed modals to `<body>`" advice. Add the missing gotcha: a container is a new formatting context, so margins stop collapsing through it. Confidence: high.

**SS-A12 · medium · The `@property` recipe is invalid, and would break parts if it worked.**
- style-architecture.md:361-366 uses `initial-value: 1.5rem`. The spec requires a computationally independent initial value, so the rule is dropped (css-properties-values-api-1).
- **Evidence (Chrome 153):** an invalid value stays the string "not-a-length" and a child inherits 10px; a `24px` control registers correctly.
- **Second problem:** `inherits:false` would starve parts that read root sockets (spacing-system.md:414 reads `--card-radius`/`--card-inset`).
- **Fix:** use px initial values and name the sockets that may be non-inheriting.

**SS-A13 · medium · The colour-blindness safety claim is false.** color-system.md:433-435 says success-500 and danger-500 are "33 L-points apart" and survive deuteranopia. The tokens put them at L 0.62 and 0.58, 4 points apart, 1.39:1 from each other. **Fix:** separate status steps by ≥0.20 L, or require an icon or text channel.

**SS-A14 · medium · SKILL.md never says where to run the scripts, and its default deliverable is a ZIP.**
- Every command is `python -m scripts.X` (SKILL.md:66-72, :159-173; :58 even omits the path). From the project root `scripts` can't be imported; from the skill root, `src/` points inside the plugin.
- **Fix:** add one line, `PYTHONPATH=<skill base dir> python -m scripts.audit_design <project>/src`.
- :206-208 makes a ZIP (with a copied audit script) the default deliverable. That is wrong inside a Claude Code repo session; make it opt-in.

**SS-A15 · low · The fluid spacing anchors aren't what the comments say, and typography's "sanity check" is stale.**
- Solving each clamp: `--space-fluid-sm/lg/xl` meet their bounds at ≈400 and 1460px (md: 394/1454), not the 380/1440 claimed at tokens.css:66-75 and :149-151. They run 1.5px low at xl.
- `--text-5xl/6xl` are exact for 380→1440, so typography.md:350 ("max at ~1015–1020px") is now wrong.
- `scripts/generate_space_scale.py` (tokens.css:69; client-presentation-builder deck-tokens.css:69) doesn't exist.

**SS-A16 · low · Factual slips (all verified).**
- **Subgrid:** layout-composition.md:529 says "Safari was last in, in 2023". Safari shipped in 16 (2022); Chrome 117 (Sept 2023) was last. :527 and layout.css:570-573 forbid a subgrid's own gap; it can set one (MDN).
- **Block-level gap:** layout-composition.md:132 and layout.css:247 call it "specified and shipping". `gap` applies only to multi-column, flex and grid containers (MDN).
- **Gradients:** color-system.md:515 says `in oklch` works wherever `oklch()` does. Interpolation arrived in Firefox 127 (oklch() in 113) and Safari 16.2 (vs 15.4).
- **APCA:** color-system.md:386 calls it "the candidate algorithm for WCAG 3". It was removed from the drafts in July 2023, and the algorithm is still undecided (Roselli, Apr 2026).
- **SC levels:** typography.md:383/:386 put 1.4.4 at Level A; it is AA. color-system.md:372 gives 2.4.13 an adjacent-background clause that belongs to 1.4.11. reset.css:341 cites 2.4.11 (Focus Not Obscured) for ring contrast.
- **Misc:** color-system.md:370 "18.66px/14px" should be 18pt / 14pt bold. :33 puts the sRGB chroma maximum at ~0.37; it is 0.322. :38 puts yellow at 90°; sRGB yellow is at ~110°.

**SS-A17 · low · Comments in tokens.css and the contract are contradicted by the files themselves.**
- tokens.css:9 says components never read Tier 1, but the contract allows some primitives (token-contract.md:95).
- tokens.css:26-27/:421 say themes re-point "Tier 2 ONLY", yet the dark block re-points Tier-1 `--shadow-*` (:464-470). style-architecture.md:433 re-points `--accent-500` alone, leaving a two-hued ramp.
- tokens.css:155-156 says "These four cover everything" above five leadings, and :8/:12 name `--gray-800` and `--btn-pad-x`, which don't exist.
- Law 3 counts "5 durations" (token-contract.md:13); there are six `--dur-*`.
- motion-system.md:76 puts spinners on `--dur-slower` (1ms under reduced motion, so a strobe) and never mentions `--dur-loop`.
- spacing-system.md:187-189 requires ≥1.5× between levels, but related→grouped is 1.33×.

**SS-A18 · low (confidence medium on impact) · reset.css scroll behaviour doesn't match its comments.** :374-384 says `html:has(:target)` limits smooth scrolling to anchor clicks. Once any fragment is targeted, including a shared `#section` link on load, html computes `scroll-behavior: smooth` (verified), so every later `scrollTo()`/`scrollIntoView()` animates. Separately, :153 uses `100dvh` on body, against layout-composition.md:716-720 (svh by default, dvh for fixed overlays only).

**SS-A19 · medium · Incidental, outside my assigned scripts: `audit_design` fails any CSS file that starts with a UTF-8 BOM.**
- **Cause:** audit_design.py:1040 reads `utf-8` rather than `utf-8-sig`, so `﻿@layer` counts as an unlayered rule.
- **Repro:** `python -m scripts.audit_design <dir> --strict` on a 3-line `@layer components{…}` file. No BOM: "design audit: clean", exit 0. With a BOM: `1 error L5 unlayered This stylesheet has rules outside any @layer.`, exit 1.
- **Impact:** PowerShell 5.1 `Set-Content -Encoding utf8` writes a BOM, so the pre-commit hook refuses clean commits. **Fix:** read as `utf-8-sig` and add a test.

## B. Gaps

**SS-B1 · There is no gate for role-pair contrast.** The generator checks ramp steps against one canvas. Nothing resolves Tier-2 roles per theme and checks the pairs components actually use, so every "Verified n:1" in tokens.css is a hand-written comment. That is how SS-A4 and SS-A8 shipped. Scope: `check_roles.py` resolves the light, dark and `.inverse` roles, checks a declared pair list (text 4.5:1, UI and focus 3:1), and runs in the hook and CI.

**SS-B2 · Tier-2 roles and starter files are missing.**
- No `--fg-on-success/-warning/-danger`: white on `--bg-warning` is 2.25:1 and on `--bg-success` 3.41:1, so a filled badge has no legal text colour.
- No weight roles (SS-A10), no instant/press motion pair (the catalogue's split tokens trip `--strict`), `--motion-travel-*` left as "add it yourself" (motion-system.md:78-85), and no `.inverse` block.
- Referenced but unshipped: overrides.css (SS-A3) and utilities.css. The visually-hidden class has two names: `.visually-hidden` (style-architecture.md:156) and `.u-visually-hidden` (pattern-invention.md:449/:688), which content-model-to-ui's scaffold emits (scaffold_ui.py:2138).

**SS-B3 · Theming without JavaScript.** The only options offered are "duplicate the block" or a blocking script. `light-dark()` plus `color-scheme` (Baseline 2024, widely available from Nov 2026 per web-features) keeps native controls and tokens in step, which fixes SS-A2. It also resolves per element, so colour themes work on subtrees. Teach it in color-system.md §6 and style-architecture.md §10, and keep `[data-theme]` as the override.

**SS-B4 · Modern CSS the systems references should teach:**
- `@starting-style` with `allow-discrete` for dialog and popover animation (only navigation-patterns.md:98 mentions it).
- The top layer versus the `--z-*` ladder: a `--z-toast` renders under a `showModal()` dialog.
- `cqi` units: typography.md:354 says "use container queries" but never names them.
- `font-size-adjust` for fallback x-height; `color-mix()` and relative colour for overlays and alpha variants.
- `:user-invalid` plus `:has()` for the error state; `interpolate-size` as a Chromium-only enhancement.

**SS-B5 · Fluid type and zoom (SC 1.4.4) is only half taught.** typography.md:348 treats a rem intercept as sufficient. Add the ≤2.5× max/min rule (Barvian, smashingmagazine.com/2023/11/addressing-accessibility-concerns-fluid-type) and a zoom test: at 1440px, `--text-6xl` grows only 1.33× at 200% zoom and first reaches 2× at 400% (computed). The current tokens pass at 1.64× and 1.96×; add both checks to typography.md §15.

**SS-B6 · The brand's exact colour isn't preserved.** The generator keeps the seed's chroma and hue but replaces its lightness. It has no option to anchor the seed at its nearest step, and no report of the distance between the seed and step 500.

**SS-B7 · Nothing tests docs, tokens and generators against each other.** The 72 tests cover script behaviour only. Most of section A lies in the gap between references, starter, generators and the numbers quoted in comments.

## C. Improvements

**SS-C1 · Fix token resolution and test it in a browser (effort S–M, P0).**
- Apply the SS-A1 re-declarations, re-point `--elevation-*` (not `--shadow-*`) in dark, put `color-scheme` in the theme blocks, and restore the dialog limits.
- Add a headless-Chrome test (the suite already locates local browsers) asserting: compact row-gap 14px; `hidden` computes `display:none`; fields readable in all four OS/theme combinations; a tall dialog scrolls. My fixtures are in the workdir.

**SS-C2 · A role-contrast gate, `check_roles.py` (M, P0).** As in SS-B1, wired into the audit and the pre-commit hook. Have it emit the table that color-system.md §6 quotes.

**SS-C3 · Make the docs part of the test suite (S–M, P1).**
- Extract every reference css block and run `--strict`, allowing blocks tagged `/* example: wrong */`.
- Assert each "Verified n:1" comment and each `clamp()`'s stated anchors, and check that the documented generator commands reproduce tokens.css.
- This would have caught SS-A6, A8, A9 and A15.

**SS-C4 · One source for shared CSS (M, P1).** Mark regions in base.css and layout.css, and have a script inject them into the references between `<!-- snippet -->` markers, with a `--check` mode. That makes "quoted from layout.css" true (SS-A7).

**SS-C5 · Generator upgrades (M, P1).**
- A type `--preset studio`: the 18px-rooted chain, whole-pixel snapping, fluid 44→72 and 56→110. Refuse steps under 11px unless forced.
- Colour: `--anchor-seed`, `NEUTRAL_L[500]=0.535`, and `--neutral-hue`. Emit fluid spacing too, or ship `generate_space_scale.py`.
- Then rewrite SKILL.md Phase 1 to use them.

**SS-C6 · Use Claude Code plugin features (M, P1).**
- A PostToolUse hook on Edit|Write for `*.css`/`*.scss`/`*.tsx`/`*.jsx` that runs `audit_design <file> --json` and returns the findings as context, catching drift at the edit rather than the commit.
- Commands `/wds:tokens` (generators plus role check, with the right flags and PYTHONPATH), `/wds:audit` and `/wds:contrast`; a read-only `design-auditor` subagent.

**SS-C7 · A `claude plugin eval` suite (M–L, P2).** Script-graded cases, run against a no-plugin baseline:
- compact dashboard section (computed gap shrinks);
- dark toggle plus a signup form (fields ≥4.5:1 in all four combinations);
- dark-mode error banner (`check_roles` passes);
- tall terms modal (scrolls);
- badge on a warning fill (text contrast passes);
- hero at 200% zoom (text still meets 1.4.4);
- `#e8440a` brand (the hex appears in the ramp).
Every case must also pass `audit_design --strict`.

**SS-C8 · Shrink SKILL.md and rework the description (S, P1).**
- **Size:** 17.7 KB / 2,616 words ≈ 4.4k tokens. Replace "The suite" table (:108-127, duplicated in token-contract.md and the README) with a pointer, fold the Scripts block (:155-179) into Phases 1 and 5, and move "Two things worth saying plainly" and "Deliverable shape" to handoff-conventions.md. That cuts about 30–35%.
- **Overlap:** the 949-character description triggers on almost any web task and shares exact nouns with siblings: "landing page / marketing site" (landing-page-conversion), "hands over a Figma file" (figma-variables-sync, which the chain runs first), "make this look better" (design-critique-gate), "dark mode" (component-state-matrix).
- **Fix:** add routing clauses and distinctive triggers: tokens.css, design tokens, spacing scale, type scale, OKLCH palette, cascade layers, layout primitives, density.

**SS-C9 · Ship what the starter refers to (S, P1).** overrides.css with the `[hidden]` rule, utilities.css with one visually-hidden class under one name, the no-flash theme script, and an `.inverse` block in tokens.css.

## Reviewed

- **Files read in full:** every assigned file, plus audit_design.py (the tier tables and the file reader), the bug-fix report, the README, component-state-matrix SKILL.md:170-185 and the sibling descriptions.
- **Commands** (on a copy in `...\scratchpad\review\studio-systems`, PYTHONDONTWRITEBYTECODE=1):
  - `contrast_check*.py`: every contrast claim, using the generator's maths.
  - `generate_color_ramp` with SKILL.md's seeds and color-system.md §12's; the §12 "verbatim" block matches exactly.
  - `generate_type_scale` with the docstring preset and SKILL.md's command.
  - `fluid_check.py` (real clamp anchors, zoom growth) and `extract_examples.py` (71 reference blocks through `audit_design --strict`).
  - The BOM repro, and headless Chrome 153 fixtures starter-test, theme-test (`--blink-settings=preferredColorScheme=0/1`), cq-test and property-test.
- **Sources:** WCAG 2.2; Understanding 1.4.11; css-conditional-5; mdn/content#43405; MDN gap, subgrid and container-type; the web-features explorer (gradient-interpolation, view transitions, cross-document view transitions, scroll-driven animations, light-dark, interpolate-size); the Properties & Values API spec; Barvian (Smashing 2023); Roselli (Apr 2026).
- **Confirmed correct:** motion-system's support lines for view transitions and scroll-driven animations; the `oklch()` browser versions; tokens.css's other contrast figures (4.60, 3.56, 4.92, 4.02, 5.84, 17.4, 18.5, 6.35, 7.91).
