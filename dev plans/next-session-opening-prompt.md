# The opening prompt for the next session

Written 2026-10-10, at the end of the fifth session that day, which merged P31 part 1 (#101, `shared/dtcg.py`) and part 2 (#102, Tokens Studio). Paste the block below into a new session.

```
You're continuing work on web-design-suite, a Claude Code plugin, in C:\DEV\Pro-Web-Designer-Suite-Plug-in. Budget: this session may run up to 750 thousand tokens, with no compacting. Report usage after each PR (15,000,000 minus the counter, plus what was used before each reset), warn early, and write the handoff before the cap.
1. Run: git fetch && git worktree list && gh pr list --state open. Then, in the worktree that holds main (this checkout unless the list says otherwise): git checkout main && git pull
2. Read "dev plans/next-session-prompt.md" in full and follow it. Then read CLAUDE.md and docs/HANDOFF.md, as it says.
Phase 6 (4.0.0) is under way: P31 parts 1 and 2 are merged (the DTCG reader and writer, and Tokens Studio). This session: P31 part 3 (themes through the DTCG resolver module, $deprecated into the ledger, the Style Dictionary and Terrazzo name routes), re-reading the resolver module and the Style Dictionary and Terrazzo docs first, then the rest of Phase 6. Every eval run costs real money: ask me before any run, with its estimate. Keep each PR under 100 files, since CodeRabbit skips larger ones.
You merge PRs yourself once they're ready (CI green, review threads resolved, clean), never in a way that breaks other pending work.
```
