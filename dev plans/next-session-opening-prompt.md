# The opening prompt for the next session

Written 2026-10-13, at the end of the day's second session, which began Phase 6b with P36 (Tailwind v4): #125 moved Part 5 to eslint-plugin-better-tailwindcss (D4, 4.0.0's breaking change), #126 added `tw_probe.mjs` and `/tw-probe`, and #127 taught v4's variants after `--*: initial`. Paste the block below into a new session.

```
You're continuing work on web-design-suite, a Claude Code plugin, in C:\DEV\Pro-Web-Designer-Suite-Plug-in. Budget: this session may run up to 750 thousand tokens, with no compacting. Report usage after each PR (15,000,000 minus the counter, plus what was used before each reset; it resets on every CI event and on my messages), warn early, and write the handoff before the cap.
1. Run: git fetch && git worktree list && gh pr list --state open. Then, in the worktree that holds main (this checkout unless the list says otherwise): git checkout main && git pull
2. Read "dev plans/next-session-prompt.md" in full and follow it. Then read CLAUDE.md and docs/HANDOFF.md, as it says.
3.6.0 is released; 4.0.0 is in progress. This session: P36's last part (LC-B5's v4 --spacing census and N40, the colour match), as §4 of the prompt lays it out; then ask me which workstream follows (P34, P35, P37, P41, or P42 and P43). Every eval run and every paid live session costs real money: ask me before any run, with its estimate. Keep each PR under 100 files, since CodeRabbit skips larger ones.
You merge PRs yourself once they're ready (CI green, review threads resolved, clean), never in a way that breaks other pending work.
```
