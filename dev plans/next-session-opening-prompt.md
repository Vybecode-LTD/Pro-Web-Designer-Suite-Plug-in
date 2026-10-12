# The opening prompt for the next session

Written 2026-10-12, at the end of the session that merged P38 part 2 (#115 `cqi`, `font-size-adjust`, alpha variants, `interpolate-size`), P39 (#116 the migration census and the rollout recipes) and P40 (#117 Prisma and Drizzle), which completes Phase 6a's code. Paste the block below into a new session.

```
You're continuing work on web-design-suite, a Claude Code plugin, in C:\DEV\Pro-Web-Designer-Suite-Plug-in. Budget: this session may run up to 750 thousand tokens, with no compacting. Report usage after each PR (15,000,000 minus the counter, plus what was used before each reset; it resets on every CI event and on my messages), warn early, and write the handoff before the cap.
1. Run: git fetch && git worktree list && gh pr list --state open. Then, in the worktree that holds main (this checkout unless the list says otherwise): git checkout main && git pull
2. Read "dev plans/next-session-prompt.md" in full and follow it. Then read CLAUDE.md and docs/HANDOFF.md, as it says.
Phase 6a's code is merged (P31, P32, P33, P38, P39, P40). This session: R3.6, the 3.6.0 release, as §4 of the prompt lays it out: a live check of what changed, the release PR, the eval dispatch on its merge, then the tag. Every eval run and every paid live session costs real money: ask me before any run, with its estimate. Keep each PR under 100 files, since CodeRabbit skips larger ones.
You merge PRs yourself once they're ready (CI green, review threads resolved, clean), never in a way that breaks other pending work. Ask me before pushing the v3.6.0 tag.
```
