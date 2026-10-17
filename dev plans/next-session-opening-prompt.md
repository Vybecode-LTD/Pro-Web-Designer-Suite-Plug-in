# The opening prompt for the next session

Written 2026-10-16, at the end of the fourth session that day, which finished Phase 6c (#162, D6's Baseline browser versions, registered) and began Phase 6b's P34 (#163, part 1: reaching a client-rendered or signed-in page). Paste the block below into a new session.

```
You're continuing work on web-design-suite, a Claude Code plugin, in C:\DEV\Pro-Web-Designer-Suite-Plug-in. Budget: this session may run up to 750 thousand tokens, with no compacting. Report usage after each PR (15,000,000 minus the counter, plus what was used before each reset; it resets on every CI event and on my messages), warn early, and write the handoff before the cap.
1. Run: git fetch && git worktree list && gh pr list --state open. Then, in the worktree that holds main (this checkout unless the list says otherwise): git checkout main && git pull
2. Read "dev plans/next-session-prompt.md" in full and follow it, starting with section 3. Then read CLAUDE.md and docs/HANDOFF.md, as it says.
3.6.0 is released; 4.0.0 is in progress. My audit (Phase 6c) is done. I put P34 first in Phase 6b: part 1 is merged, so do part 2 (shadow DOM, GT-B3), then part 3 (several URLs and viewports, GT-B4). Then ask me which of P35, P37 (with N48), P41, P42 and P43 comes next. Every eval run and every paid live session costs real money: ask me before any run, with its estimate. Keep each PR under 100 files, since CodeRabbit skips larger ones; CodeRabbit and Codex are optional, never a gate.
You merge PRs yourself once they're ready (CI green, review threads resolved, clean), never in a way that breaks other pending work.
```
