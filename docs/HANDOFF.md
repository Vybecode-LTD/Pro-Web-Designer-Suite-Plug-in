# Handoff

**2026-10-09**, after P25 part 2 (#84), P26 part 1 (#85) and this docs PR. 3.4.0 is the latest release; Phase 5 (3.5.0, a full Claude Code plugin) is under way.

**The next session starts from `dev plans/next-session-prompt.md`**: orientation, then P26 parts 2 and 3 and P27 in detail. `dev plans/next-session-opening-prompt.md` is the message to paste in.

## State

- **Merged this session:** #84 (`6a1f28d`) and #85 (`fd7032f`). Each had CI green on its head, every thread answered and resolved, CodeRabbit finished and GitHub clean. This docs PR follows. No other PR is open.
- **What they did:**
  - **#84, P25 part 2 (LC-C8): the token diff.** After Claude edits one of the project's token files, the gate's hook runs `diff_system.py` against the published snapshot. Claude hears the release that makes, each breaking change and each contrast pair that crossed a WCAG floor. An additive edit is silent.
    - It is opt-in: `hooks.tokenDiff`, with `tokens` and the new `baselines.system`. Both readers check the keys.
    - `diff_system.py` without `old` reads `baselines.system`.
    - P25 is complete.
  - **#85, P26 part 1 (GT-C12, LC-B4, XC-C8; XC-C3 in part): the first workflow commands.** They are skills only the user invokes, in `workflow-commands/`, added by `plugin.json`'s `skills` key.
    - **`/gate`** runs the three static gates, with one verdict.
    - **`/install-gate`** vendors the gate scripts into the project's `scripts/`, where every recipe expects them, and writes `.github/workflows/design-gates.yml`. The workflow runs the gates in the Playwright image pinned to the project's playwright, the static gates on Windows, and a baseline job by hand.
    - The three gates now create a baseline's missing folder.
    - XC-C8 closes.
- **The reviews found 15 real issues** (4 on #84, 11 on #85), each fixed with a test that fails on the head it reviewed. Two suggestions on #84 were declined with reasons, and CodeRabbit withdrew both.
  - **#84:**
    - a token file outside the project;
    - a broken config unreported for a `contract.json`, and in UTF-16 or UTF-32;
    - `diff_components` reading every component as removed against a token-only snapshot.
  - **#85:**
    - the stamp's ownership, a foreign file and then a malformed one;
    - unquoted paths from the flags, from the config's baselines, and with a leading hyphen;
    - the browser gates' missing packages;
    - `persist-credentials`;
    - dot-file baselines left out of the artifact;
    - the build command read as a YAML boolean;
    - a named `--dist` that is missing;
    - the skip, undocumented.
- **The plan:** 47 open items, 47 scheduled (`check_execution_plan.py`). Tests: 863.

## Next steps

1. **P26 parts 2 and 3:** the other workflow commands (the prompt's §4). Name them first.
2. **P27:** the subagents, and the two hooks P25 closed without: GT-C9's `a11y_static` on edit and DL-C7's email-template build and lint. Re-read the sub-agents page first.
3. Then P28 to P30, and R3 (3.5.0).

## Warnings

- **Neither the hooks nor the commands have run in a live session.** The installed plugin is 3.4.0. Before R3, load the branch's plugin (`claude --plugin-dir plugins/web-design-suite`) on Windows and check:
  - the gate on a real edit;
  - the token diff;
  - the guard's refusal;
  - how often the router speaks;
  - `/web-design-suite:gate` and `/web-design-suite:install-gate`, including that their `allowed-tools` spare the prompt.
- **The CI template has not run on GitHub.** The tests run its Windows and baseline jobs' commands on a fixture, and parse the whole workflow. Before R3, install it in a scratch repository and push.
- **Worth the owner's look:** the router runs in every project unless `design_hooks` is off; the gate, the token diff and the guard are opt-in.
- **A merge from below leaves copies behind.** There are seven `project_config.mjs` copies and ten `project_config.py` copies. After every merge, copy both masters over them.
- **`check.py` prints only the first failure.** When it reports more, run the suite directly and grep `^FAIL:`.
- **The token counter** reset about 15 times this session, on every review event. This session used about 550 thousand.
- **SKILL.md budgets:** client-presentation-builder, email-template-system and landing-page-conversion 20,497 bytes of 20,500; perf-budget-gate 20,494; component-state-matrix 20,493.
- **Still open from earlier:**
  - The hydration timing test flakes on Windows 3.14 runners (re-run it).
  - `--warning-700`, `--danger-100` and `--info-100` fall outside Display P3.
  - `check_roles.py` clips a colour outside sRGB.
  - The worked examples are tests.
  - A local build never matches the release's checksums.
  - Don't grep `tooling/`.
  - The repository is public.
