# Handoff

**2026-10-30 (its first session): stage 3 begun. P77 (#236) and P78 (#237) are merged, and the owner's GitHub settings are in place.**
- **P77, #236, `a11y_static.py` (PY-D-1 to PY-D-12).** These changes:
  - `//` comments in `.scss`, `.less`, `.pcss` and a `lang="scss|less"` style block are comments.
  - The mouse-only `:focus:not(:focus-visible)` reset passes.
  - Address and phone tokens must stand as words, and each attribute is read on its own.
  - The pragma covers the whole tag below it.
  - An inline `<svg>`'s title is not the page's.
  - A nav's `aria-labelledby` is judged by its text.
  - A link's name comes from its label, with a new `label-not-in-name` warning (2.5.3).
  - A document's dangling reference is reported, and so are `transition: all` on a ring and `autocomplete="off"`.
  - Review: Codex limited the mouse-only exemption to the reset's own compound. CodeRabbit had the renderer load Playwright by its path, and corrected the title rule's wording.
- **P78, #237, `audit_design.py`, `check_roles.py` and the generators (13 PY-B findings).** These changes:
  - z-index, the type family and `box-shadow` read the spec's allowlists, so the audit, stylelint and ESLint agree.
  - New `VAR_LIST` shape.
  - The gap ring carries `design-audit-ignore-next-line: L1` inside its `stylelint-disable` comment.
  - An unlayered `:root` fails.
  - Compound variants, Vue `:class` and zero utilities are handled.
  - A system colour in a fallback is not checked, in the audit and in stylelint.
  - Unreadable files are listed as skipped, and a crashed rule is an error.
  - Every CSS colour spelling is read.
  - Review: Codex (alpha in any number spelling) and CodeRabbit (the selector exemption is the query's own string; a unitless lightness is clamped). Each was fixed with a test that fails on `eaeec45`.
- **Also:**
  - The owner's §3 steps 1 to 4 and 8 were read back with `gh api`.
  - The social preview is drawn (`dev plans/readme-art/social/`).
  - The README hero's title is corrected.

## State

- **`main`** = this PR's merge, on #237's merge `ff628be` and #236's `aa1a7c0`.
- **Open:** none.
- **Released:** `v4.0.1`. P60 to P78 are on `main` for 4.1.0.
- **Tests:** 1,832.
- **Audit findings:** 125 of 281 closed (P66 to P78).
- **Plans:** `check_execution_plan.py` reads 11 open, 11 scheduled (N73 to N83). Next free ids: **N84, P90**. This PR is #238, so the next is #239.

## Next steps

1. **P79, `design-token-migration`** (N73; the runbook's §4 stage 3): PY-B-2, -3, -5, -6, -12, -15, -21, -23, -24, -25, -26. Its findings are in `dev plans/web-design-suite-audit-2026-10-28/py-b-studio-and-migration.md`.
2. **Carried from the last handoff, not done in P78:** ESLint's unused `m` at `web-design-studio/scripts/tw_probe.mjs:183` and `catch (e)` at `assets/starter/theme-init.js:14` (the starter is quoted, so `sync_snippets.py` follows). Then widen `test_real_tools.TheBrowserScriptsLeaveNothingUnused` to every shipped `.mjs` and `.js`. Do it in P79's PR or its own.
3. **P80 to P85:** the rest of stage 3.

## Open owner steps

- **Upload the social preview to both repositories.** `usesCustomOpenGraphImage` was still false on 2026-10-30.
- **Optional:** untick "Require branches to be up to date" in `main`'s ruleset. While it's on, a PR whose base moved needs updating and a CI rerun.
- **§3 steps 5, 7 and 9** stand as the runbook says.

## Warnings

- **`main`'s ruleset:** no direct push. A PR needs the seven checks and resolved threads, merges by merge commit, and must be up to date with `main`.
- **The gates are stricter:** say so in the 4.1.0 note. These now fail the default gate:
  - an unlayered `:root` file
  - a keyword weight, `normal` leading or a named font family
  - a token-built shadow
  - `calc()` on a z rung
  - a crashed rule
  - `autocomplete="off"` and `label-not-in-name` (warnings)
- **`check.py` prints only the suite's tail.** On a failure, rerun the modules it names for the full output.
- **A gate change touches the spec, `sync_rules.py`, both configs, the starter and the references' snippets** (`test_doc_snippets`). Run `audit_design.py skills --strict` before the full suite.
- **Budget:** this session reached its context limit and was compacted once, against the no-compacting rule: about 600K before, 160K after. Close by about 500K when a full-suite run and a review round are still ahead.
