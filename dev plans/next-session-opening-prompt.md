# The opening prompt for the next session

Written 2026-10-07, at the end of the sixth Phase 4 session (P20, P21 in two parts, P44: #64 to #67). Paste the block below into a new session.

```
You're continuing work on web-design-suite, a Claude Code plugin, in C:\DEV\Pro-Web-Designer-Suite-Plug-in. Budget: this session may run up to 750 thousand tokens, with no compacting. Report usage after each PR, warn early, and write the handoff before the cap.
1. Run: git fetch && git checkout main && git pull && gh pr list --state open && git worktree list
2. Read "dev plans/next-session-prompt.md" in full and follow it. Then read CLAUDE.md and docs/HANDOFF.md, as it says.
#64 to #67 are merged (P20, P21 in two parts, P44) and no PR is open. Remove any worktree left in the scratchpad from the last session. This session: P22 (the critique: merges with covers, notes and status, the counts, and critique_snapshots.mjs), then P23 (the persuasion references and facts), and further into Phase 4 if the budget allows.
You merge PRs yourself once they're ready (CI green, review threads resolved, clean), never in a way that breaks other pending work.
```
