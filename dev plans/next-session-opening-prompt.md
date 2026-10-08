# The opening prompt for the next session

Written 2026-10-08, at the end of the session that merged P24 part 4 (#81) and P25 part 1 (#82). Paste the block below into a new session.

```
You're continuing work on web-design-suite, a Claude Code plugin, in C:\DEV\Pro-Web-Designer-Suite-Plug-in. Budget: this session may run up to 750 thousand tokens, with no compacting. Report usage after each PR (15,000,000 minus the counter, plus what was used before each reset), warn early, and write the handoff before the cap.
1. Run: git fetch && git checkout main && git pull && gh pr list --state open && git worktree list
2. Read "dev plans/next-session-prompt.md" in full and follow it. Then read CLAUDE.md and docs/HANDOFF.md, as it says.
3.4.0 is released, P24 is complete (#76, #78, #79, #81), P25 part 1 is merged (#82, the hooks), then the session's docs, and no PR is open. This session: P25 part 2 (the token diff after a token-file edit, LC-C8), then P26 (the workflow commands and the CI bootstrap), re-reading the skills page first.
You merge PRs yourself once they're ready (CI green, review threads resolved, clean), never in a way that breaks other pending work.
```
