# The opening prompt for the next session

Written 2026-10-10, at the end of the session that merged P26 parts 2 and 3 (#87, #88) and P27 part 1 (#89). Paste the block below into a new session.

```
You're continuing work on web-design-suite, a Claude Code plugin, in C:\DEV\Pro-Web-Designer-Suite-Plug-in. Budget: this session may run up to 750 thousand tokens, with no compacting. Report usage after each PR (15,000,000 minus the counter, plus what was used before each reset), warn early, and write the handoff before the cap.
1. Run: git fetch && git worktree list && gh pr list --state open. Then, in the worktree that holds main (this checkout unless the list says otherwise): git checkout main && git pull
2. Read "dev plans/next-session-prompt.md" in full and follow it. Then read CLAUDE.md and docs/HANDOFF.md, as it says.
3.4.0 is released. P26 is complete (#85, #87, #88: fifteen workflow commands) and P27 part 1 is merged (#89: six subagents and /critique), then the session's docs, and no PR is open. This session: P27 part 2 (the two hooks P25 left: a11y_static on edit, the email build and lint), then P28 (an MCP server for the gates; bin/ only with my yes; an LSP spike), re-reading the MCP page first.
You merge PRs yourself once they're ready (CI green, review threads resolved, clean), never in a way that breaks other pending work.
```
