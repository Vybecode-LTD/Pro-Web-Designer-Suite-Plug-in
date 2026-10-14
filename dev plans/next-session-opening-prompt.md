# The opening prompt for the next session

Written 2026-10-14, at the end of the session that finished P36 (#129: the v4 `--spacing` census, N40's colour families) and took in the owner's audit (114 findings, scheduled as Phase 6c; #130 closed its C1, C2 and H1). Paste the block below into a new session.

```
You're continuing work on web-design-suite, a Claude Code plugin, in C:\DEV\Pro-Web-Designer-Suite-Plug-in. Budget: this session may run up to 750 thousand tokens, with no compacting. Report usage after each PR (15,000,000 minus the counter, plus what was used before each reset; it resets on every CI event and on my messages), warn early, and write the handoff before the cap.
1. Run: git fetch && git worktree list && gh pr list --state open. Then, in the worktree that holds main (this checkout unless the list says otherwise): git checkout main && git pull
2. Read "dev plans/next-session-prompt.md" in full and follow it. Then read CLAUDE.md and docs/HANDOFF.md, as it says.
3.6.0 is released; 4.0.0 is in progress. This session: my audit of 2026-10-14 ("dev plans/web-design-suite-audit-2026-10-14.md", Phase 6c), from P44 (its gates, H4 to H8), as §4 of the prompt lays it out. First ask me where Phase 6c goes among P34, P35, P37, P41, P42 and P43. Every eval run and every paid live session costs real money: ask me before any run, with its estimate. Keep each PR under 100 files, since CodeRabbit skips larger ones.
You merge PRs yourself once they're ready (CI green, review threads resolved, clean), never in a way that breaks other pending work.
```
