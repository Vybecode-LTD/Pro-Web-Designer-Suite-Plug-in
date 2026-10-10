# Handoff

**2026-10-10 (second session)**, after P27 part 2 (#91), P28 part 1 (#92), N38 (#93) and this docs PR. 3.4.0 is the latest release; Phase 5 (3.5.0, a full Claude Code plugin) is under way.

**The next session starts from `dev plans/next-session-prompt.md`**: orientation, then P28 part 2 (`bin/`, only with the owner's yes) and P29 (the eval framework) in detail. `dev plans/next-session-opening-prompt.md` is the message to paste in.

## State

- **Merged this session:** #91, #92 and #93, each with CI green on its head, every thread answered and resolved, CodeRabbit finished and GitHub clean. #91 merged as `500e02d`, #92 as `f75dd51` and #93 as `ac482c5`. CodeRabbit's free tier ran out mid-session: it reviewed #91, and #92 when asked after the limit reset, but never #93, which merged on green CI, Codex's clean review and CodeRabbit's finished (rate-limited) check.
- **What they did:**
  - **#91, P27 part 2: two more checks in the gate's hook.** `hooks.a11yGate` runs `a11y_static.py` on each file Claude edits that it reads, its findings beside the audit's under the shared cap. `hooks.emailBuild` lints an edited email template, builds it into a temporary folder and lints the build; Claude hears the errors. A new top-level `emails` key holds the templates' globs (`emails/**/*.html` by default), in both readers. GT-C9 closes; DL-C7's hook lands, and DL-C7 closes with its evals in P30.
  - **#92, P28 part 1: the gates as MCP tools.** `.mcp.json` runs `node mcp/design_gates.mjs`: five tools (`audit_design`, `a11y_static`, `perf_audit`, `check_roles`, `diff_system`), each returning the script's JSON, its exit code and a verdict, arguments checked, a path never an option, a long report cut to 60,000 characters at any depth. Claude Code 2.1.293 connects to it on Windows (`claude mcp list`). **The LSP spike is not shipped:** each file extension gets one language server, so ours would pre-empt the user's TypeScript server (`claude-code-capabilities.md` §9).
  - **#93, N38: baselines across platforms.** `a11y_static.py` and `perf_audit.py` keyed a baseline by the path with the platform's separator, so `/install-gate`'s Linux-recorded baselines failed its Windows job. Keys now use `/`, and old baselines keep matching.
- **The reviews found 3 real issues:** CodeRabbit on #91 (the email test scanned the shared temp folder), Codex on #92 (nested lists escaped the size cap), and the session's own N38. One CodeRabbit suggestion was declined with a reason, and it withdrew it.
- **The plan:** 40 open items, 40 scheduled (`check_execution_plan.py`). Tests: about 940. Fifteen workflow commands, six agents, one MCP server.

## Next steps

1. **Ask the owner about `bin/`** (P28 part 2). Without a yes, close XC-B1 in the docs: the plugin then has agents, hooks, commands and an MCP server.
2. **P29:** the eval framework and the routing cases. It needs a signed-in CLI: the desktop app's bundled one said "Not logged in" to `claude -p`.
3. Then P30 (outcome evals) and R3 (3.5.0).

## Warnings

- **Nothing new has run in a live session**, apart from `claude mcp list` connecting to the MCP server. The installed plugin is 3.4.0. Before R3, load the branch's plugin (`claude --plugin-dir plugins/web-design-suite`) on Windows and check the hooks (the gate, a11y and email checks, the token diff, the guard, the router), each of the fifteen commands, each agent, and one call to each MCP tool.
- **The CI template has not run on GitHub.** Before R3, install it in a scratch repository and push; N38 was found by reading it, not running it.
- **A flake on `main`:** `test_critique_snapshots` failed once on Linux 3.9 with Chromium's "Unable to capture screenshot" (run 38005281749); the re-run passed. If it recurs, look at it.
- **CodeRabbit's free tier runs out.** "Review limit reached" reports its check as passing without a review; ask again (`@coderabbitai review`) after the limit resets when the code is new.
- **Open question:** `perf_audit.py --src` reports the starter's own `index.css` `@import` lines as `css-import` LCP errors, so a project started with `/new-system` fails `/gate --src`'s performance gate. Decide whether the perf gate should skip an entry stylesheet a bundler inlines, or the starter should stop using `@import`.
- **A merge from below leaves copies behind.** Seven `project_config.mjs` copies and ten `project_config.py` copies: after every merge, copy both masters over them.
- **The token counter** reset on every review event again. This session used about 510 thousand.
- **Still open from earlier:** the hydration timing test flakes on Windows 3.14 runners; `--warning-700`, `--danger-100` and `--info-100` fall outside Display P3; `check_roles.py` clips a colour outside sRGB; the worked examples are tests; a local build never matches the release's checksums; don't grep `tooling/`; the repository is public.
