# Handoff

**2026-10-16**, after P54 part 9 and P55 parts 1 to 3 of Phase 6c, the owner's audit. **Next: P55 part 4 (§3.5 and §3.6's lows), then part 5 (§3.7 and §3.8's lows).** The owner placed all of Phase 6c (P50 to P55) before Phase 6b's remaining workstreams.

**The next session starts from `dev plans/next-session-prompt.md`**: orientation, then the work in detail. `dev plans/next-session-opening-prompt.md` is the message to paste in.

## State

- **#154, P54 part 9 (§3.8: T1, T2)**, merged as `15e40d6`. The evidence register's entries live on the figure itself or a spelling of it, never a companion number, and the register is read beside the docs it describes; the TBT tests read the fixture's own task (`measure_vitals`' new `perRun[].tasks`) against TTI. P54 and N46 are done.
- **#155, P55 part 1 (§3.1: S5, S6, S7, S9)**, merged as `add2ced`. The Python and Node token readers agree on a spaced reference, non-ASCII digits and `components` given as an object; the MCP server refuses a path outside the project, through any link, and a folder holding a link that leads out.
- **#156, P55 part 2 (§3.2: W8 to W13)**, merged as `91b43cb`. `check_roles` reads a rule with a nested block; the audit's `!important` is the flag; `tw_probe` reads an extensionless import; the hook's role stage takes every one-file token set that declares a role; two config comments corrected.
- **#157, P55 part 3 (§3.3 and §3.4: M7, M8, V13 to V16)**, merged as `5fbb615`. The census reads `@apply` and markup class expressions; the codemod keeps a file's mode; a duration by its type resolves; `diff_system` reads one docs schema; `--format all` needs its folder; the references name every flag, kind and shape, held by tests; classes in `@apply` and class expressions are hand work.
- **Reviews:** 12 real findings (Codex 6, CodeRabbit 6, two of them the same issue), each fixed with a test failing on the head it reviewed. Four corrections to the audit: W14's `noqa` are used under ruff's defaults, T2's third site holds a ratio only, and S8, S10, M9 and V12 were already closed by P53.
- **At the end:** the plan has 20 open items, all 20 scheduled; about 1,270 tests. This session used about 680 thousand tokens.

## Next steps

1. If this docs PR, #158, is still open, merge it once green.
2. **P55 part 4, §3.5 and §3.6:** E11, E12; G8, G9, G10, G12, G14, G16 (E13, G11, G15 closed by #138; E14, G13 by #142).
3. **P55 part 5, §3.7 and §3.8:** D5 to D9; T3 to T10. Then remove the `P55` row and mark N47 done.
4. Then Phase 6b in the owner's order, then **R4**.

## Open owner decisions

- None new. The order within Phase 6b, once Phase 6c is done, is the owner's call.

## Warnings

- **Codex reached its review usage limit** on #157 ("You have reached your Codex usage limits for code reviews"). Until it resets or the owner adds credit, PRs merge on CI green, threads resolved and clean, as they do when CodeRabbit is rate-limited.
- **`git ls-files '*dtcg.py'` matches `tests/test_dtcg.py`**: copying the masters over every copy overwrote it once (restored). Leave `tests/` out.
- **ruff writes a `.ruff_cache`** with machine paths, which `test_docs.NoMachinePaths` refuses: run it with `--no-cache`.
- **`gh run watch` can lose its connection** ("error connecting to api.github.com"), and `wait_pr.sh` then reports `ci exit 1`. Read the run (`gh pr checks N`) before acting on it.
- **The MCP server walks each folder a gate reads** for a link out of the project. A large tree without `node_modules` makes a call slower; a project with a link out is refused (`-32602` names it), and the CLI scripts are unchanged.
- **Still open from earlier:** Vue's `:style` (P55); the `VitalsUnderCsp` macOS flake; `test_interact_at_clicks_while_the_page_hydrates` failed once in 11 local runs; `perf_audit.py` and an unbundled `@import` chain; three tokens outside Display P3; don't grep `tooling/`; the repository is public; `Vybecode-LTD/wds-gate-scratch` is the owner's to delete.
