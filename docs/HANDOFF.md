# Handoff

**2026-10-15**, after P52 and P53 part 1 of Phase 6c, the owner's audit. **Next: P53 part 2, the JSON type guards (the audit's S1, V8, G3, G11, G15, E13, W6, S10).** The owner placed all of Phase 6c (P50 to P55) before Phase 6b's remaining workstreams.

**The next session starts from `dev plans/next-session-prompt.md`**: orientation, then the work in detail. `dev plans/next-session-opening-prompt.md` is the message to paste in.

## State

- **#135, P52 (N44, the audit's H11 to H15)**, merged as `a888fb5`:
  - The migration's reconciliation accounts for every census literal:
    - a colour the proposal cannot parse (`oklch()`, `lab()`, `lch()`, `hwb()`, `color()`, `hsl(turn)`) gets an unmapped row;
    - so does a `letter-spacing` in `px`;
    - and so does a project ramp step it cannot read.
  - What it calls mechanically replaceable is what `--apply` rewrites:
    - the codemod takes named colours;
    - a `color-mix()` with a colour written out is one colour function;
    - a duration counts at the one rule that rewrites it.
  - A width (never a height) meets the `--width-*` steps first. A width rule's class is `width`, which the codemod gives only `width`, `min-width` and `max-width`.
  - H14 did not reproduce: during a rebase `--ours` is HEAD, so the recipe's staged file is clean. A test now runs the recipe end to end.
  - H15:
    - the UTF-8 test reads every entry script's `__main__` block, with a positive control;
    - six scripts gained the reconfigure: `check_roles.py` and the five workflow commands' scripts;
    - CI runs the Pydantic test with `pydantic>=2,<3` and `WDS_REQUIRE_PYDANTIC`.
  - **Reviews:** 3 real findings, all fixed with tests failing on the head they reviewed: Codex 2 (a height took a width step, at the proposal and then at the codemod) and CodeRabbit 1 (a duration counted twice, the audit's F7).
- **#136, P53 part 1 (N45, the `--out` guard: V7, E9, G4, class 5)**, merged as `7e59f90`:
  - One helper decides: `refuse_overwrite()` in `shared/project_config.py`, and `refuseOverwrite()` in `shared/browser_common.mjs`, which reads a `file://` URL as its file.
  - Fifteen Python writers and two Node ones call it before writing, and exit 2 with the input untouched.
  - It compares against the files actually read: a glob's matches, a folder's files, every file of a snapshot (`Snapshot.sources`), the token files and budgets the config names, screenshots and their captions, the manifest's templates, `--prose`, and the deck's bundled tokens.
  - `critique_report.py` and `generate_matrix.py` carry the master's function verbatim, held equal by `test_out_guard`.
  - **Reviews:** Codex 12 real findings over two rounds, all fixed with tests failing on the head they reviewed. One more was declined with evidence: a Windows drive path never matches the URL-scheme pattern.
- **At the end:** `main` is this docs PR's merge; no other PR is open. The plan: 22 open items, 22 scheduled. About 1,198 tests.

## Next steps

1. **P53 part 2: the JSON type guards** (S1, V8, G3, G11, G15, E13, W6, S10). Validate at load, exit 2 naming the key, with a test per loader for `[]`, a string, and a list where an object is expected.
2. **Then P53's other classes**, one PR each:
   - the encoding readers (S8, W7);
   - the discarded diagnostics (S2, V11, V12, M9, and `diff_system`'s contrast check that skips a colour it cannot parse, found beside H11);
   - the cmd.exe placeholders (D4, G13, E14).
3. **Then the mediums (P54) and the lows (P55).** Then Phase 6b's workstreams, in the owner's order, then **R4**.

## Open owner decisions

- None new. The order within Phase 6b, once Phase 6c is done, is the owner's call.

## Warnings

- **Codex finds the next case of a class every round.** #136 took 12 findings over two rounds, all of the form "the guard compares the spelling, not the file read". For P53's other classes, list every way each script finds its inputs before writing the fix: globs, folders, the config's paths, defaults, bundled assets and URLs.
- **CodeRabbit is optional** (the owner): never wait for it, and fix its real findings when it posts them. It ran out of free reviews on #136.
- **A merge commit made with `-m` and then committed with `--no-edit` after conflicts** keeps git's `# Conflicts:` list after the `Co-Authored-By:` line (`97e5c31`). Harmless, but write the message with `git commit -F` after resolving instead.
- **The audit session's worktree is still registered:** `…\3985bfd1-…\scratchpad\wt`, detached at `9391774`. Its fixtures (`migration\fx1..fx7` and the others) are still there, and they were what showed H14 was a staged-against-HEAD case, not a rebase. Once P53 to P55 no longer need them, remove it with `git worktree remove "C:\Users\vybec\AppData\Local\Temp\claude\C--DEV-Pro-Web-Designer-Suite-Plug-in\3985bfd1-4280-462b-8333-0e682826a220\scratchpad\wt"`, which works in cmd.exe too.
- **Still open from earlier:**
  - Vue's `:style` binding is not read by the audit's `style=""` reader (P54);
  - the `VitalsUnderCsp` flake on Windows with Python 3.14, and the TBT flake on macOS;
  - `perf_audit.py` and an unbundled `@import` chain;
  - three tokens outside Display P3;
  - a local build never matches the release's checksums;
  - don't grep `tooling/`;
  - the repository is public;
  - `Vybecode-LTD/wds-gate-scratch` is the owner's to delete.
