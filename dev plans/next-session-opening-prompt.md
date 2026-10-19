# The opening prompt for the next session

Written 2026-10-18, at the end of the day's third session, which finished P37 (#176, the scaffold writes Vue 3.5 components; #177, Svelte 5). The owner chose P35 next. Paste the block below into a new session.

```
You're continuing work on pro-web-design-suite, a Claude Code plugin, in C:\DEV\Pro-Web-Designer-Suite-Plug-in. Budget: this session may run up to 750 thousand tokens, with no compacting. Report usage after each PR (15,000,000 minus the counter, plus what was used before each reset; it resets on every CI or review event and on my messages), warn early, and write the handoff before the cap.
1. Run: git fetch && git worktree list && gh pr list --state open. Then, in the worktree that holds main (this checkout unless the list says otherwise): git checkout main && git pull
2. Read "dev plans/next-session-prompt.md" in full and follow it, starting with section 3. Then read CLAUDE.md and docs/HANDOFF.md, as it says.
3.6.0 is released; 4.0.0 is in progress. P37 is done. Do P35 (I chose it on 2026-10-18), in two PRs, as section 4 sets out: the cheap automatable a11y checks, then engines other than Chromium. Ask me before CI downloads Firefox or WebKit. Then ask me which of P41, P42 and P43 comes next. Every eval run and every paid live session costs real money: ask me before any run, with its estimate. Keep each PR under 100 files, since CodeRabbit skips larger ones; CodeRabbit and Codex are optional, never a gate.
You merge PRs yourself once they're ready (CI green, review threads resolved, clean), never in a way that breaks other pending work.
```
