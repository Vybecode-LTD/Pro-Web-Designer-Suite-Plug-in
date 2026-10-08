# Handoff

**2026-10-08**, after P24 part 2 (#78), P24 part 3 (#79) and this docs PR. 3.4.0 is the latest release; Phase 5 (3.5.0, a full Claude Code plugin) is under way.

**The next session starts from `dev plans/next-session-prompt.md`**: orientation, then P24 part 4 (N37) and P25 in detail. `dev plans/next-session-opening-prompt.md` is the message to paste in.

## State

- **Merged this session:** #78 and #79, each with CI green on its head, every thread answered and resolved, CodeRabbit finished and GitHub clean. This handoff PR follows. No other PR is open.
- **What they did:**
  - **#78, P24 part 2: the project's tokens in every script that compared against the starter's** (closes LC-C1 and LC-B3).
    - `read_tokens()` in `shared/project_config.py` reads a project's tokens.css or contract.json into the contract's sections.
    - audit_design: the config's token files, component globs, ramps and baseline.
    - figma_audit: the project's scales.
    - figma_to_tokens: the project's names.
    - diff_system: a contract as a snapshot, and the project's tokens as the default candidate.
    - cluster_values: lands on the project's ramps.
    - web-design-studio has a new `references/project-contract.md`.
  - **#79, P24 part 3: every key of `.design-suite.json` has its readers.** XC-C8 stays open: its scope also names the hook (P25) and the commands (P26), where it closes.
    - Budgets, the other baselines, `emailTokens`, the deck's CSS tokens and `stack` reach their scripts.
    - `browser_common.mjs` gains `projectConfig()`, held to the Python reader by `TheNodeReaderAgrees`.
    - The reader is copied beside ten skills' scripts.
- **The reviews found 9 real issues**, 7 on #78 and 2 on #79:
  - **Codex:** a name moved between sections across files; mixed CSS and contract lists in diff_system; a11y_static vendored alone raising `NameError`.
  - **CodeRabbit:**
    - `--tokens` not repeatable in figma_audit;
    - non-numeric and non-ASCII ramp steps;
    - project steps outside the contract in cluster_values, and a ramp with none reported as taken;
    - build_docs naming `--baseline` for a baseline the config named.

  CodeRabbit also kept XC-C8 open, rightly.

  Each is fixed with a test that fails on the head it reviewed. One suggestion was declined with the reason, and CodeRabbit withdrew it: a reader fallback for scripts that are never vendored alone.
- **N37 is new** (CodeRabbit on #78). The project's config reaches the audit but not stylelint or the ESLint config, so for a project with a config the three gates can disagree. It is recorded in the completion plan and scheduled as P24 part 4.
- **The plan:** 53 open items, 53 scheduled (`check_execution_plan.py`). Tests: 799.

## Next steps

1. **P24 part 4 (N37):** the project's config in the stylelint and ESLint configs, through a copy of the Node reader, with real-tool tests. The prompt's §4 has the decisions to make.
2. **P25**, the hooks: the opt-in design gate, the generated-file block, `diff_system` after a tokens edit, and the prompt router. Re-read the hooks page and the mods reference first.
3. Then P26 to P30, and R3 (3.5.0).

## Warnings

- **The hydration timing test flakes on Windows 3.14 runners.** `test_browser_runtime.VitalsMeasures.test_interact_at_clicks_while_the_page_hydrates` measured the click at 5,729 ms against 2,800 ms on #79. The re-run passed. If it recurs, look at the runner's load before the code.
- **A merge into a stacked branch leaves the reader's copies behind.** Git merges each `project_config.py` copy separately, so the copies only the upper branch has keep the old reader. After every merge from below, copy `shared/project_config.py` over all ten.
- **SKILL.md budgets:**
  - client-presentation-builder: 20,497 bytes of 20,500
  - email-template-system: 20,497
  - landing-page-conversion: 20,497
  - perf-budget-gate: 20,494
  - component-state-matrix: 20,493
- **The token counter reset at each app event** (nine times this session, and once on a message from the user). Keep a running total. This session used about 640 thousand tokens: two PRs with three review rounds each, and the docs PR.
- **Bash heredocs eat backslashes**, twice again this session. Write such scripts with the Write tool.
- **Codex reviewed only the head each PR opened with.**
- **Still open from earlier:**
  - `--warning-700`, `--danger-100` and `--info-100` fall outside Display P3.
  - `check_roles.py` measures a colour outside sRGB with its channels clipped.
  - The worked examples are tests (`TheWorkedRun`, `TheWorkedRelease`).
  - A local build never matches the release's checksums.
  - Don't grep `tooling/`.
  - The repository is public.
