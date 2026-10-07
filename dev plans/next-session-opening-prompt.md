# The opening prompt for the next session

Written 2026-10-07, at the end of the session that merged P45 (#73) and released 3.4.0 (R2, #74). Paste the block below into a new session.

```
You're continuing work on web-design-suite, a Claude Code plugin, in C:\DEV\Pro-Web-Designer-Suite-Plug-in. Budget: this session may run up to 750 thousand tokens, with no compacting. Report usage after each PR, warn early, and write the handoff before the cap.
1. Run: git fetch && git checkout main && git pull && gh pr list --state open && git worktree list
2. Read "dev plans/next-session-prompt.md" in full and follow it. Then read CLAUDE.md and docs/HANDOFF.md, as it says.
3.4.0 is released (#73 and #74, then the session's docs), which completes Phase 4, and no PR is open. Remove any worktree left in the scratchpad from the last session. This session opens Phase 5: P24 (the project contract, .design-suite.json and contract.json, in two parts), then P25 (the hooks) if the budget allows.
You merge PRs yourself once they're ready (CI green, review threads resolved, clean), never in a way that breaks other pending work.
```
