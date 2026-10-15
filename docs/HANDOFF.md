# Handoff

**2026-10-14 (second session)**, after P50 part 2 and P51 of Phase 6c, the owner's audit. **Next: P52, the migration proposal's arithmetic and recipe, and two tests (the audit's H11 to H15).** The owner placed all of Phase 6c (P50 to P55) before Phase 6b's remaining workstreams.

**The next session starts from `dev plans/next-session-prompt.md`**: orientation, then the work in detail. `dev plans/next-session-opening-prompt.md` is the message to paste in.

## State

- **#132, P50 part 2 (N42, the audit's H4 to H8)**, merged as `6257623`:
  - `a11y_static` reads every CSS rule at any depth: `outline: none` inside `@layer`, `@media` or `@supports` is seen. A nested `&` rule resolves against its parent, and a condition nested in a rule keeps the rule's declarations. Comments keep their newlines, so line numbers and ignore pragmas hold after a multi-line comment.
  - `a11y_static` reads Vue's `:x` and `v-bind:x`, Angular's `[x]` and `[attr.x]`, and the event bindings (`@click`, `v-on:`, `on:`, `(click)`).
  - `generate_matrix` mirrors states inside `:is()` and `:where()` (an arm with no state becomes `arm:not(*)`) and nested rules; a forced state is covered only when a mirror was written.
  - The hook's `DESIGN_GATE_INDEX=1` scratch tree carries the config, its baselines and the default ones, and never writes through a staged symlink.
  - The audit takes a style object's keys from its depth-0 entries, with spreads' object literals and comments handled.
  - **Reviews:** 7 real findings, all fixed with tests failing on the head they reviewed: Codex 3 over two rounds, CodeRabbit 4.
- **#133, P51 (N43, the audit's H2, H3, H9, H10)**, merged as `f603b02`:
  - `--reverse` reports a theme's value it cannot carry, naming the mode, and exits 1.
  - `extract_system`, `build_docs` and `diff_system` read a BOM.
  - `introspect_schema` replays `ALTER TYPE … ADD VALUE` and `RENAME VALUE`, reads `''` in a label, and ends a `CREATE TABLE`'s column list at its own paren, past strings and `$$` bodies.
  - **Reviews:** 6 real findings, all fixed with tests failing on the head they reviewed: Codex 3 over two rounds, CodeRabbit 3.
- **At the end:** `main` is this docs PR's merge; no other PR is open. The plan: 23 open items, 23 scheduled. About 1,177 tests.

## Next steps

1. **P52:** the audit's H11 to H15 (`cluster_values.py`, `apply_codemod.py`, `migration-strategies.md`, `test_utf8_output.py`, `test_scaffold.py`), each with a fail-before test on `v3.6.0`, then a grep for the same construct (the audit's class 2).
2. **Then P53's cross-cutting classes**, one PR each (the `--out` guard, the JSON type guards, the encoding readers, the discarded diagnostics, the cmd.exe placeholders), then the mediums (P54) and the lows (P55).
3. **Then Phase 6b's workstreams** (P34, P35, P37, P41, P42 and P43), then **R4**: a live check, the release PR, the evals on its merge, then the tag.

## Open owner decisions

- None new. The order within Phase 6b, once Phase 6c is done, is the owner's call.

## Warnings

- **Codex re-reviews a PR when asked (`@codex review`) and finds more each round**: #132 took two rounds. Ask once after a round of fixes, then merge when the fixes are small and tested.
- **CodeRabbit is optional** (the owner, 2026-10-14 and 2026-10-12): never wait for it; fix its real findings when it posts them.
- **A symlink test skips on Windows** without the symlink right (`test_the_index_mode_never_writes_through_a_staged_symlink`); Linux and macOS CI run it.
- **Bash heredocs eat backslashes** (twice more this session). Write such code with the Write or Edit tool.
- **The audit session's worktree is still registered:** `…\3985bfd1-…\scratchpad\wt`, detached at `9391774`. It may hold the audit's fixtures, so it was left; `git worktree remove` it once P52 to P55 no longer need them.
- **Still open from earlier:**
  - Vue's `:style` binding is not read by the audit's `style=""` reader (a gap noted for P54);
  - the `VitalsUnderCsp` flake on Windows with Python 3.14, and the TBT flake on macOS;
  - `perf_audit.py` and an unbundled `@import` chain;
  - `test_critique_snapshots`;
  - three tokens outside Display P3, and `check_roles.py` clipping outside sRGB;
  - a local build never matches the release's checksums;
  - don't grep `tooling/`;
  - the repository is public;
  - `Vybecode-LTD/wds-gate-scratch` is the owner's to delete.
