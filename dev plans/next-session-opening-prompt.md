# The opening prompt for the next session

Written 2026-10-16, at the end of the third session that day, which did P55 parts 4 and 5 (#159 §3.5 and §3.6, #160 §3.7 and §3.8) of Phase 6c, the owner's audit; one piece of D6 is left (P55). Paste the block below into a new session.

```
You're continuing work on web-design-suite, a Claude Code plugin, in C:\DEV\Pro-Web-Designer-Suite-Plug-in. Budget: this session may run up to 750 thousand tokens, with no compacting. Report usage after each PR (15,000,000 minus the counter, plus what was used before each reset; it resets on every CI event and on my messages), warn early, and write the handoff before the cap.
1. Run: git fetch && git worktree list && gh pr list --state open. Then, in the worktree that holds main (this checkout unless the list says otherwise): git checkout main && git pull
2. Read "dev plans/next-session-prompt.md" in full and follow it, starting with section 3. Then read CLAUDE.md and docs/HANDOFF.md, as it says.
3.6.0 is released; 4.0.0 is in progress. My audit of 2026-10-14 (Phase 6c) is done but one piece: D6's Baseline browser versions (P55). Ask me whether to register them or waive them, and do that first. Then Phase 6b's remaining workstreams (P34, P35, P37, P41, P42, P43): ask me which comes first, and whether Vue's :style gets an item. Every eval run and every paid live session costs real money: ask me before any run, with its estimate. Keep each PR under 100 files, since CodeRabbit skips larger ones; CodeRabbit and Codex are optional, never a gate.
You merge PRs yourself once they're ready (CI green, review threads resolved, clean), never in a way that breaks other pending work.
```
