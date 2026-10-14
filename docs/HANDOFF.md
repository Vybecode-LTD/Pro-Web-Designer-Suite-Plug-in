# Handoff

**2026-10-14**, after P36's last part (Phase 6b), the owner's audit, and the audit's first fix (Phase 6c). **Next: P44, the audit's gates (H4 to H8)**, unless the owner places Phase 6c elsewhere among Phase 6b's workstreams.

**The next session starts from `dev plans/next-session-prompt.md`**: orientation, then the work in detail. `dev plans/next-session-opening-prompt.md` is the message to paste in.

## State

- **P36 is done.** #129, its part 4, merged on 2026-10-14 (LC-B5's rest and N40):
  - **The census** counts Tailwind v4's numeric classes (`p-4` at N × `--spacing`), reading `--spacing` through each entry's imports as Tailwind builds the theme. In a script it reads them only where classes go: a class attribute, a `className={…}` expression, a class helper's arguments.
  - **The proposal** maps them, and **the codemod** rewrites only the utility, matched whole.
  - **framework-migrations.md §5** gives Move 1 in v4's form, compiled by a test.
  - **Colours** are matched by family first: a neutral (under half of sRGB's chroma at its lightness and hue) only to the neutral ramp, any other colour within 30° of its hue. ΔE then ranks within the family, and the ramps are seeded by the same test.
  - **Reviews:** 7 real findings, all fixed with tests: Codex 4 over two rounds, CodeRabbit 2 (one a stale plan line), and CI 1 (stylelint on the doc's own `@import`).
- **The owner's audit**, `dev plans/web-design-suite-audit-2026-10-14.md`, covers `main` at `9391774`: 114 findings (2 critical, 15 high, 49 medium, 48 low). It is scheduled as N41 to N47 in the completion plan and as Phase 6c, P44 to P49, in the execution plan, all before R4.
- **#130 (P44 part 1)** closed the audit's C1, C2 and H1: the codemod's arbitrary-class match is bound on both ends, and the codemod, `deprecate`'s marker and its ledger keep a file's line endings.
- **At the end:** `main` is this docs PR's merge; no other PR is open. The plan: 25 open items, 25 scheduled. About 1,147 tests.

## Next steps

1. **P44:** the audit's H4 to H8, the gates that pass what they should fail. Each fix gets a fail-before test on `v3.6.0`, then a grep for the same construct across the plugin (the audit's class 2).
2. **Then P45 and P46** (H2, H3, H9, H10; H11 to H15), then P47's cross-cutting classes, then the mediums (P48) and the lows (P49).
3. **Phase 6b's other workstreams** (P34, P35, P37, P41, P42 and P43) come where the owner places them.
4. **R4** follows R3.6's order: a live check, the release PR, the evals on its merge, then the tag.

## Open owner decisions

- Where Phase 6c goes among P34, P35, P37, P41, P42 and P43, or whether it all goes first.

## Warnings

- **Stage by name, never `git add -A`, while a file the owner is writing sits untracked in the checkout.** It put the audit on #129's branch (added in `aa95250`, removed in `b78d77b`; the owner chose to keep that history).
- **`check.py` skips `test_real_tools` without the tools' modules.** Run it with `WDS_NODE_MODULES` pointing at `tooling/main/node_modules`, or a snippet stylelint refuses reaches CI (it did on #129).
- **A doc's CSS block is filed by the snippet audit**: its `@theme` goes to the theme file, and the rest to a component inside `@layer components`, where an `@import` is invalid. Show the theme alone.
- **Bash heredocs eat backslashes** (twice more this session). Write such code with the Edit tool.
- **The `VitalsUnderCsp` positive control flaked once on Windows with Python 3.14** (main's CI on 2026-10-14, green on a re-run): the shift went unmeasured. Watch for a repeat.
- **Still open from earlier:**
  - `perf_audit.py` and an unbundled `@import` chain;
  - the TBT flake on macOS;
  - `test_critique_snapshots`;
  - three tokens outside Display P3, and `check_roles.py` clipping outside sRGB;
  - the worked examples are tests;
  - a local build never matches the release's checksums;
  - don't grep `tooling/`;
  - the repository is public;
  - `Vybecode-LTD/wds-gate-scratch` is the owner's to delete.
