# The opening prompt for the next session

Written 2026-10-07, at the end of the seventh Phase 4 session (P22 in two parts and P23: #69 to #71). Paste the block below into a new session.

```
You're continuing work on web-design-suite, a Claude Code plugin, in C:\DEV\Pro-Web-Designer-Suite-Plug-in. Budget: this session may run up to 750 thousand tokens, with no compacting. Report usage after each PR, warn early, and write the handoff before the cap.
1. Run: git fetch && git checkout main && git pull && gh pr list --state open && git worktree list
2. Read "dev plans/next-session-prompt.md" in full and follow it. Then read CLAUDE.md and docs/HANDOFF.md, as it says.
#69 to #72 are merged (P22 in two parts, P23, and the session's docs) and no PR is open. Remove any worktree left in the scratchpad from the last session. This session: P45 (Law 6 in stylelint and the ESLint config, from the spec's tiers), then R2 (the 3.4.0 release: the version, the build, the v3.4.0 tag), and into Phase 5 if the budget allows.
You merge PRs yourself once they're ready (CI green, review threads resolved, clean), never in a way that breaks other pending work.
```
