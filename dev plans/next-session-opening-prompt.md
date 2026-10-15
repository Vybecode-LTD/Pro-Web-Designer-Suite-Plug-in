# The opening prompt for the next session

Written 2026-10-15, at the end of the session that did P52 (#135, the audit's H11 to H15, the migration's reconciliation) and P53 part 1 (#136, the `--out` guard). The owner placed all of Phase 6c before Phase 6b's remaining workstreams. Paste the block below into a new session.

```
You're continuing work on web-design-suite, a Claude Code plugin, in C:\DEV\Pro-Web-Designer-Suite-Plug-in. Budget: this session may run up to 750 thousand tokens, with no compacting. Report usage after each PR (15,000,000 minus the counter, plus what was used before each reset; it resets on every CI event and on my messages), warn early, and write the handoff before the cap.
1. Run: git fetch && git worktree list && gh pr list --state open. Then, in the worktree that holds main (this checkout unless the list says otherwise): git checkout main && git pull
2. Read "dev plans/next-session-prompt.md" in full and follow it. Then read CLAUDE.md and docs/HANDOFF.md, as it says.
3.6.0 is released; 4.0.0 is in progress. This session: my audit of 2026-10-14 ("dev plans/web-design-suite-audit-2026-10-14.md", Phase 6c), from P53 part 2 (the JSON type guards: S1, V8, G3, G11, G15, E13, W6, S10), then P53's other classes, one PR each, as §4 of the prompt lays it out. All of Phase 6c comes before Phase 6b's other workstreams. Every eval run and every paid live session costs real money: ask me before any run, with its estimate. Keep each PR under 100 files, since CodeRabbit skips larger ones; CodeRabbit is optional, never a gate.
You merge PRs yourself once they're ready (CI green, review threads resolved, clean), never in a way that breaks other pending work.
```
