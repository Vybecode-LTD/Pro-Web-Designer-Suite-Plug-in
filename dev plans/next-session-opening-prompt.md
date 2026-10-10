# The opening prompt for the next session

Written 2026-10-10, at the end of the fourth session that day, which merged P30 (#97), N39 (#98) and R3 (#99), and released 3.5.0. Paste the block below into a new session.

```
You're continuing work on web-design-suite, a Claude Code plugin, in C:\DEV\Pro-Web-Designer-Suite-Plug-in. Budget: this session may run up to 750 thousand tokens, with no compacting. Report usage after each PR (15,000,000 minus the counter, plus what was used before each reset), warn early, and write the handoff before the cap.
1. Run: git fetch && git worktree list && gh pr list --state open. Then, in the worktree that holds main (this checkout unless the list says otherwise): git checkout main && git pull
2. Read "dev plans/next-session-prompt.md" in full and follow it. Then read CLAUDE.md and docs/HANDOFF.md, as it says.
3.5.0 is released (Phase 5 is done: P30's outcome evals, N39, and R3 with its live check). This session: Phase 6, starting with P31, the DTCG tokens (my choice), re-reading the DTCG 2025.10 format, Tokens Studio's themes and the Style Dictionary and Terrazzo docs first. Every eval run costs real money: ask me before any run, with its estimate. Keep each PR under 100 files, since CodeRabbit skips larger ones.
You merge PRs yourself once they're ready (CI green, review threads resolved, clean), never in a way that breaks other pending work.
```
