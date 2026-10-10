# Handoff

**2026-10-10 (third session)**, after P29 (#95) and this docs PR. 3.4.0 is the latest release; Phase 5 (3.5.0, a full Claude Code plugin) is under way.

**The next session starts from `dev plans/next-session-prompt.md`**: orientation, then P30 (the outcome evals) in detail. `dev plans/next-session-opening-prompt.md` is the message to paste in.

## State

- **Merged this session:** #95 as `c84ec10`, with CI green on its head (`be94f1c`), every thread answered and resolved, CodeRabbit finished and GitHub clean.
- **What it did:**
  - **P28 part 2 is closed without `bin/`** (the owner, 2026-10-10). A plugin with `bin/` is not installed by claude.ai or Cowork, and the commands and MCP tools reach the runners already. XC-B1 closes.
  - **P29: the eval suite.** `evals/` has 23 cases: a routing case per skill and a "must not fire" case each way between five sibling pairs. Every grader is `arm: both`, and every case lists `allowed_tools: [Skill]` alone, since the route is decided before any other tool runs ($0.09 a run against $0.21 with Read, Glob and Grep). `test_evals` checks the cases, runs each pattern in node, runs the router on every prompt and runs the CI job's steps under bash. XC-C1 and XC-B2 close.
  - **The first real run** (the owner's Max plan, 2.1.293, `claude-sonnet-5-5`): 22 of 23 passed in 69 runs for $5.59, then 23 of 23 after a router fix. The whole session's eval spend was $6.11 on the plan and $4.11 on the API key, at list price.
  - **The router, corrected three times** by the cases: "looks professional" for the critique, docs or prop tables beside a design system for the docs, and "screen-reader" with a hyphen.
  - **`evals.yml`**, the CI job. It runs on `workflow_dispatch` and `v*` tags, never on a pull request, billed to the `ANTHROPIC_API_KEY` secret, which the owner added. It pins the CLI (2.1.293) and the models, and its actions to commit SHAs. The threshold is 1.0 and the ceiling $14. Its first dispatch on `main` (run 38055988575): 23 of 23 at 1.00, $4.11, 18 minutes.
- **The reviews found 4 real issues**, each fixed with a test that failed on the head it reviewed:
  - Codex, twice: prop tables routed for a library README, and the 0.8 threshold let a boundary case pass with one bad run.
  - CodeRabbit: actions not pinned to commits, and setup-node's cache.
- **The plan:** 37 open items, 37 scheduled (`check_execution_plan.py`). About 955 tests.

## Next steps

1. **P30: the outcome evals**, against a no-plugin baseline (SS-C7, SB-C6, GT-C10, LC-C10, PS-C7, DL-C7). Estimate one case first: these grant tools, run two arms and may use judges.
2. Then R3 (3.5.0), after a live check of the new components.

## Warnings

- **The desktop app's bundled CLI lives in a packaged folder.** The app is an MSIX package, so its `AppData\Roaming` is `C:\Users\vybec\AppData\Local\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming`. Claude's tools see the usual path; the owner's own terminal does not. Give the owner the real path. The credentials are in `C:\Users\vybec\.claude`, which both share, and the CLI is signed in now (claude.ai, Max).
- **Granting Bash to an eval needs an OS sandbox.** Native Windows has none (WSL2 is needed), and Linux needs bubblewrap and socat. The sandbox makes the home folder unreadable, and a GitHub checkout is under `/home/runner`, so check that a run can read the plugin's scripts before building on it. The plugin's MCP server runs outside the sandbox: with `--allow-real-servers` and a tool grant, it can run the gates with no Bash.
- **Nothing new has run in a live session**: the hooks, the fifteen commands, the six agents and the MCP tools. Before R3, load the branch's plugin (`claude --plugin-dir plugins/web-design-suite`) and check each one. The evals ran the router hook 69 times without a problem.
- **The CI templates have not run on GitHub**: `/install-gate`'s, nor `evals.yml` on a tag.
- **Flakes:** the hydration timing test on Windows 3.14 (again on #95, passed on re-run), and `test_critique_snapshots` on Linux 3.9.
- **Open question:** `perf_audit.py --src` reports the starter's `@import` lines as LCP errors, so a `/new-system` project fails `/gate --src`'s performance gate.
- **The token counter** reset on review events and some user messages. This session used about 360 thousand.
- **Still open from earlier:** `--warning-700`, `--danger-100` and `--info-100` fall outside Display P3; `check_roles.py` clips a colour outside sRGB; the worked examples are tests; a local build never matches the release's checksums; don't grep `tooling/`; the repository is public.
