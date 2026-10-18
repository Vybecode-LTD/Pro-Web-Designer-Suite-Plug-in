# The opening prompt for the next session

Written 2026-10-18, at the end of the 2026-10-17 session, which finished Phase 6b's P34 (#165, the runtime checks read through shadow roots; #166, several pages and viewports in one run). Paste the block below into a new session.

```
You're continuing work on web-design-suite, a Claude Code plugin, in C:\DEV\Pro-Web-Designer-Suite-Plug-in. Budget: this session may run up to 750 thousand tokens, with no compacting. Report usage after each PR (15,000,000 minus the counter, plus what was used before each reset; it resets on every CI event and on my messages), warn early, and write the handoff before the cap.
1. Run: git fetch && git worktree list && gh pr list --state open. Then, in the worktree that holds main (this checkout unless the list says otherwise): git checkout main && git pull
2. Read "dev plans/next-session-prompt.md" in full and follow it, starting with section 3. Then read CLAUDE.md and docs/HANDOFF.md, as it says.
3.6.0 is released; 4.0.0 is in progress. P34 is done. I put P37 next, with N48: do it in the four parts section 4 sets out (N48's bound inline styles, SCSS in stylelint, the Next.js, Vue, Svelte and Astro stacks, the scaffold's other outputs). Then ask me which of P35, P41, P42 and P43 comes next. Every eval run and every paid live session costs real money: ask me before any run, with its estimate. Keep each PR under 100 files, since CodeRabbit skips larger ones; CodeRabbit and Codex are optional, never a gate.
You merge PRs yourself once they're ready (CI green, review threads resolved, clean), never in a way that breaks other pending work.
```
