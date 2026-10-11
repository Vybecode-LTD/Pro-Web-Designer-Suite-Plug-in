# Handoff

**2026-10-11 (one session)**, after P31 parts 3 to 5 (#105, #106, #107) and this docs PR. **P31 is complete**: LC-C2 and LC-B2 are closed. Phase 6a continues with P32, toward the 3.6.0 release; the owner reordered Phase 6 on 2026-10-11 so the non-breaking half (P31, P32, P33, P38, P39, P40) ships first as 3.6.0, then 4.0.0.

**The next session starts from `dev plans/next-session-prompt.md`**: orientation, then P32 in detail. `dev plans/next-session-opening-prompt.md` is the message to paste in.

## State

- **Merged this session**, each with CI green on its head, every thread resolved, CodeRabbit finished and GitHub clean:
  - **#105 (P31 part 3): the DTCG resolver module**, merged as `ed3667c`. `figma_to_tokens.py --format dtcg --out-dir DIR` writes `tokens.json`, each theme's or density's overrides and `tokens.resolver.json`, from a Figma export, a Tokens Studio export or a `tokens.css`. Both Figma scripts read a resolver as modes; `read_tokens()` and the Node reader read its default. Review found 8 real issues (Codex 4, CodeRabbit 4), each fixed with a test: a pointer to one source, a context's spaces and escaped quotes, sources outside the resolver's folder (by name and through a link), and odd shapes that raised.
  - **#106 (P31 part 4): `$deprecated` into the release gate**, merged as `9fd1fec`. A token the old DTCG snapshot marks counts as recorded in `diff_system.py`; `deprecate.py import` writes the marks into the ledger. Closes LC-C2. CodeRabbit found 1 real issue: a later tokens.css or contract.json that set a token again did not take its mark off.
  - **#107 (P31 part 5): Style Dictionary's and Terrazzo's names**, merged as `28c73da`. `.design-suite.json`'s `names` (`prefixes`, `rename`); the spec's `tiers.names` first, then the audit, stylelint and ESLint read Law 6 through it. Closes LC-B2. Codex found 3 real issues, all in ESLint's `(--name)` pattern, which did not follow the map's order, and CodeRabbit 1: the gates matched a renamed ramp step by its old name. The project's ramp steps are now read through the map too, and the spec's `tiers.names.overlaps` holds every case.
- **At the end:** `main` is this docs PR's merge (#108), on top of #107's `28c73da`, with CI green on each code PR's head. No other PR is open, and the checkout at `C:\DEV\Pro-Web-Designer-Suite-Plug-in` is on `main` with no other worktree.
- **The plan:** 29 open items, 29 scheduled. About 1,036 tests.
- **No eval was run** this session (none was asked for).

## Next steps

1. **P32: Figma on every plan** (LC-B1, LC-B6, LC-C7): a `--reverse --format plugin-script` route for `use_figma`, a routing row for the Figma MCP server's `get_variable_defs`, and each plan's mode limits in the audit.
2. Then P33, P38, P39 and P40, and R3.6 releases 3.6.0. Phase 6b (4.0.0) follows.

## Open owner decisions

- **`evals.yml` on a tag** (asked again at this session's start, no answer yet): a release runs the suite twice. Drop the tag trigger, or keep cancelling the tag's run?
- **The `dtcg-export` eval** (`evals/lifecycle/dtcg-export`, about $0.30) can be graded against the script route, now with themes: run it when the owner says so.

## Warnings

- **The masters and their copies.** After every merge from a branch below, copy `shared/dtcg.py`, `shared/project_config.py` and `shared/project_config.mjs` over every copy (ten, ten and seven), then run `TheCopiesAreTheMaster`. Git merges each copy on its own.
- **A worktree in the scratchpad hits Windows' 260-character path limit** (`evals/boundaries/...`): create it with `git -c core.longpaths=true worktree add`, run targeted tests there, and the full `check.py` in the main checkout. This session fixed #105's review findings in a worktree while `check.py` ran in the main one.
- **Bash heredocs eat backslashes**, quoted or not, and a heredoc holding `'''` breaks the shell's parse. Write edit scripts with the Write tool; fix a backslash in one with the Edit tool.
- **The token counter resets on every `<ci-monitor-event>`**, acknowledgements included. Keep a running total.
- **The scratch repository** `Vybecode-LTD/wds-gate-scratch` is private and the owner's to delete.
- **CodeRabbit's free tier:** one review an hour; it skips a stacked PR until it targets `main` (comment `@coderabbitai review` after retargeting).
- **Still open from earlier:** `perf_audit.py` and an unbundled `@import` chain; headless sessions refused a skill's reference files; the hydration and `test_critique_snapshots` flakes; three tokens outside Display P3; `check_roles.py` clips outside sRGB; the worked examples are tests; a local build never matches the release's checksums; don't grep `tooling/`; the repository is public.
