# The opening prompt for the next session

Written 2026-10-10, at the end of the third session that day, which closed P28 part 2 without `bin/` and merged P29 (#95). Paste the block below into a new session.

```
You're continuing work on web-design-suite, a Claude Code plugin, in C:\DEV\Pro-Web-Designer-Suite-Plug-in. Budget: this session may run up to 750 thousand tokens, with no compacting. Report usage after each PR (15,000,000 minus the counter, plus what was used before each reset), warn early, and write the handoff before the cap.
1. Run: git fetch && git worktree list && gh pr list --state open. Then, in the worktree that holds main (this checkout unless the list says otherwise): git checkout main && git pull
2. Read "dev plans/next-session-prompt.md" in full and follow it. Then read CLAUDE.md and docs/HANDOFF.md, as it says.
3.4.0 is released. P29 is merged (#95: the eval suite, 23 routing cases passing, the evals.yml CI job), bin/ was declined, then the session's docs, and no PR is open. This session: P30, the outcome evals against a no-plugin baseline, re-reading the sandboxing page and the evals page's fixtures section first; then prepare R3 (3.5.0). The CLI is signed in and the API key secret exists, but every eval run costs real money: ask me where the Bash-granting cases should run (WSL2 or CI only) and about the budget, after a one-case estimate, before any full run.
You merge PRs yourself once they're ready (CI green, review threads resolved, clean), never in a way that breaks other pending work.
```
