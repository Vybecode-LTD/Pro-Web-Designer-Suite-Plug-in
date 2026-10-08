# The opening prompt for the next session

Written 2026-10-07, at the end of the session that merged P45 (#73), released 3.4.0 (R2, #74) and opened Phase 5 with P24 part 1 (#76). Paste the block below into a new session.

```
You're continuing work on web-design-suite, a Claude Code plugin, in C:\DEV\Pro-Web-Designer-Suite-Plug-in. Budget: this session may run up to 750 thousand tokens, with no compacting. Report usage after each PR, warn early, and write the handoff before the cap.
1. Run: git fetch && git checkout main && git pull && gh pr list --state open && git worktree list
2. Read "dev plans/next-session-prompt.md" in full and follow it. Then read CLAUDE.md and docs/HANDOFF.md, as it says.
3.4.0 is released and P24 part 1 is merged (#73 to #76, then the session's docs), and no PR is open. Remove any worktree left in the scratchpad from the last session. This session: P24 part 2 (the project contract in the other scripts, the Node reader included), then P25 (the hooks) if the budget allows.
You merge PRs yourself once they're ready (CI green, review threads resolved, clean), never in a way that breaks other pending work.
```
