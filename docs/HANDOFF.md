# Handoff

**2026-10-08**, after P24 part 4 (#81), P25 part 1 (#82) and this docs PR. 3.4.0 is the latest release; Phase 5 (3.5.0, a full Claude Code plugin) is under way.

**The next session starts from `dev plans/next-session-prompt.md`**: orientation, then P25 part 2 and P26 in detail. `dev plans/next-session-opening-prompt.md` is the message to paste in.

## State

- **Merged this session:** #81 (`20c0da1`) and #82 (`c93b235`), each with CI green on its head, every thread answered and resolved, CodeRabbit finished and GitHub clean. This docs PR follows. No other PR is open.
- **What they did:**
  - **#81, P24 part 4 (N37): the lint configs read the project's config.** stylelint now treats the config's token files as token files and adds its `components` globs to the component files. ESLint treats a JSX or TSX file the globs match as a component file. In both, a step of the project's own ramps is a Tier-1 colour with a role.
    - `shared/project_config.mjs` is the Node reader. It moved out of `browser_common.mjs`, which re-exports it, and gained `readTokens()`, a port of `read_tokens()`.
    - The ramp advice is in the spec (`tiers.project_ramps`), written into all three gates by `sync_rules.py`.
    - stylelint's overrides need micromatch globs, so `overrideGlobs()` translates each config glob, for every spelling of the project's folder.
  - **#82, P25 part 1: the plugin's first hooks.** `hooks/hooks.json` runs `node hooks/design_hooks.mjs` in exec form, in three modes:
    - **gate:** `audit_design.py` on each edited file, with the findings returned to Claude.
    - **guard:** refuses an edit to a generated file.
    - **route:** names the skill a prompt needs.

    The gate and the guard are opt-in, through `.design-suite.json`'s new `hooks` key. The `design_hooks` option turns all three off. The re-read docs and the choice of command hooks over a mod are in `claude-code-capabilities.md` §6.
- **The reviews and CI found 7 real issues.** Each is fixed, and the six in code each have a test that fails on the head it reviewed:
  - **CodeRabbit on #81:** the globs must name a linked or lower-case-drive folder, and a token file reached through a link.
  - **Codex on #81:** JSON in every encoding Python's `json` reads.
  - **Codex on #82:** the guard's window counted in code points.
  - **CI on #82:** a path named from the unresolved file on macOS (`/var`) and Windows (an 8.3 TEMP name).
  - **CodeRabbit on #82:** a report past 1 MiB cut short, and a spawn failure left silent; and the README called the router opt-in.
- **The plan:** 51 open items, 51 scheduled (`check_execution_plan.py`). Tests: 828.

## Next steps

1. **P25 part 2 (LC-C8):** after a token-file edit, `diff_system` against the published snapshot, with the bump and any contrast crossings returned as context. The prompt's §4 recommends `baselines.system` and `hooks.tokenDiff`.
2. **P26:** the workflow commands and the CI bootstrap. Re-read the skills page first, and split it in two (the prompt's §5).
3. Then P27 to P30, and R3 (3.5.0).

## Warnings

- **The hooks have not run in a live session.** The installed plugin is 3.4.0. Before R3, load the branch's plugin (`claude --plugin-dir plugins/web-design-suite`) on Windows and check three things: the gate on a real edit, the guard's refusal, and how often the router speaks.
- **Worth the owner's look:** the router runs in every project unless `design_hooks` is off; the gate and the guard are opt-in per project. If the router proves noisy, it could become opt-in too.
- **A merge from below leaves copies behind.** There are seven `project_config.mjs` copies (five skills, `assets/configs/`, `hooks/`) and ten `project_config.py` copies. After every merge, copy both masters over them. `hooks/project_config.mjs` kept the old reader three times this session.
- **Resolve a path before taking it relative to a config's root.** The root is resolved, and macOS's `/var` and Windows runners' short TEMP names are not.
- **The token counter:** count 15,000,000 minus the counter, plus the totals before each reset. One report this session was wrong (135 thousand, at 380). This session used about 590 thousand.
- **The bundled CLI** is now 2.1.293 (`%APPDATA%\Claude\claude-code\2.1.293\83cb0bd7fed4\claude.exe`).
- **SKILL.md budgets:** client-presentation-builder, email-template-system and landing-page-conversion 20,497 bytes of 20,500; perf-budget-gate 20,494; component-state-matrix 20,493.
- **Still open from earlier:**
  - The hydration timing test flakes on Windows 3.14 runners (re-run it).
  - `--warning-700`, `--danger-100` and `--info-100` fall outside Display P3.
  - `check_roles.py` clips a colour outside sRGB.
  - The worked examples are tests.
  - A local build never matches the release's checksums.
  - Don't grep `tooling/`.
  - The repository is public.
