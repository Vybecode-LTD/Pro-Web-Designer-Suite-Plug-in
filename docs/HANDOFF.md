# Handoff

**2026-10-04**, after PR #26 (P5) and this docs PR, #27, were merged into `main`.

**The next session starts from `dev plans/next-session-prompt.md`.** It has the orientation, then P6 in two parts: type in detail, then colour.

## State

- **3.2.1 is released** (`v3.2.1`, `63932cf`) and installed. 3.3.0 is in progress on `main`, unreleased.
- **Merged this session:** #26, P5 (N3, SB-C9, N32), as a merge commit, with CI green on its head, every review thread resolved, and GitHub reporting it clean.
  - **N3.** The references' CSS now passes the real stylelint, not only the audit: `StylelintConfig.test_the_references_css_snippets_pass_the_config`. 28 of 159 blocks failed after P3.
    - The references changed where the spec refuses what they showed.
    - Escape hatches now name both tools.
    - The config now accepts sub-layers inside a canonical layer (a new spec example) and CSS Modules' `composes` and `:global`.
  - **SB-C9.** `assets/configs/index.tailwind-v3.css` is the canonical v3 entry, quoted by stack-tailwind §11.6. Preflight goes in `reset`, as in v4.
  - **N32.** `design-rules.json: selectors` holds the specificity cap, 0,3,1, and three compound selectors, written into both gates by `sync_rules.py`. The audit weighs selectors as stylelint's library does.
    - `compound-specificity` is an error now, and `compound-selectors` is new.
    - `:where(.a .b .c .d)` is refused, which departs from the session prompt: stylelint already refused it, and `:where()` removes weight, not DOM knowledge.
    - The strict audit then found one shipped selector over the cap, in landing-page `page-sections.css`.
- **The reviews of #26 found five real bugs in three rounds, all fixed with tests that fail on the head they reviewed:**
  - a `:hover` rule's parent was found by nesting depth, which pseudo-only rules do not add;
  - `::slotted()` lost its argument's weight;
  - a quoted `)` ended a `:where()` early;
  - a quoted `&` read as nesting;
  - the completion plan's W2 row still said SB-C9 was partly done.
- **Tests:** 460. **The plan:** 142 open items, all scheduled (`check_execution_plan.py`).

## Next steps

1. **The next session:** P6 part 1, the type generator's `--preset studio`, the fluid-type zoom rule (SS-B5) and the tests that hold docs, tokens and generator together. Then part 2, colour (SS-B6 and the rest), as the prompt describes.
2. **3.3.0** ships after P8 (release R1).

## Warnings

- **Decide P6's default first.** SS-C5 says to refuse type steps under 11px, but the generator's default run produces 9.26px. The prompt recommends making the studio preset the default.
- **stylelint 17's compound counter** walks into every functional pseudo-class, and reads an An+B's `+` as a combinator. A quantity query (`:nth-last-child(n + 5) ~ *`) keeps its disable comment, in the starter and in layout-composition.md.
- **The theme files are token files to the audit**, which checks only their custom properties (`bindings`). stylelint's theme override checks the same set, and nothing else in them.
- **A stricter gate reaches the references, the starter, the scaffold, the deck and every shipped stylesheet.** `test_doc_snippets`, the stylelint snippet test, the starter's own runs, `ScaffoldAuditsClean`, `test_presentation` and the strict audit of the skills all read them.
- **Bash heredocs eat backslashes.** Write anything with a backslash through the Write or Edit tool, or a script file.
- **Don't grep `tooling/`**: its `node_modules` makes the search run for minutes. Reading one named file there is fine.
- **The token counter resets** when the user sends a message: keep a running total.
- **The repository is public.** Commit nothing private.
