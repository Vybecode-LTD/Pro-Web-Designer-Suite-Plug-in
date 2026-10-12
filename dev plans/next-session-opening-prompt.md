# The opening prompt for the next session

Written 2026-10-12, at the end of the session that merged P32 (#109 the Plugin API route into Figma, #111 each plan's mode limits), #110 (evals by hand only), P33 (#112 `light-dark()`) and P38 part 1 (#113 the top layer, `@starting-style`, `:user-invalid`). Paste the block below into a new session.

```
You're continuing work on web-design-suite, a Claude Code plugin, in C:\DEV\Pro-Web-Designer-Suite-Plug-in. Budget: this session may run up to 750 thousand tokens, with no compacting. Report usage after each PR (15,000,000 minus the counter, plus what was used before each reset; it resets on every CI event), warn early, and write the handoff before the cap.
1. Run: git fetch && git worktree list && gh pr list --state open. Then, in the worktree that holds main (this checkout unless the list says otherwise): git checkout main && git pull
2. Read "dev plans/next-session-prompt.md" in full and follow it. Then read CLAUDE.md and docs/HANDOFF.md, as it says.
Phase 6a is under way toward the 3.6.0 release: P31, P32 and P33 are done, and P38 part 1. This session: P38 part 2 (cqi, font-size-adjust, color-mix() and relative colour, interpolate-size, each run in Chromium), re-reading web-features' records and MDN first, then P39 and P40 toward 3.6.0. Every eval run costs real money: ask me before any run, with its estimate. Keep each PR under 100 files, since CodeRabbit skips larger ones.
You merge PRs yourself once they're ready (CI green, review threads resolved, clean), never in a way that breaks other pending work.
```
