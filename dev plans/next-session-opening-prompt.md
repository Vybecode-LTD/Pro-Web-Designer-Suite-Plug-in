# The opening prompt for the next session

Written 2026-10-18, at the end of the session that did P37 parts 1 and 2 (#168, the audit and the census read a bound inline style, N48; #169, stylelint reads SCSS, D3). Paste the block below into a new session.

```
You're continuing work on web-design-suite, a Claude Code plugin, in C:\DEV\Pro-Web-Designer-Suite-Plug-in. Budget: this session may run up to 750 thousand tokens, with no compacting. Report usage after each PR (15,000,000 minus the counter, plus what was used before each reset; it resets on every CI or review event and on my messages), warn early, and write the handoff before the cap.
1. Run: git fetch && git worktree list && gh pr list --state open. Then, in the worktree that holds main (this checkout unless the list says otherwise): git checkout main && git pull
2. Read "dev plans/next-session-prompt.md" in full and follow it, starting with section 3. Then read CLAUDE.md and docs/HANDOFF.md, as it says.
3.6.0 is released; 4.0.0 is in progress. P37 parts 1 and 2 are done. Do part 3 (Next.js App Router, Vue, Svelte and Astro in the stack references, with a fixture project per stack, and N49: ESLint and the templates), then part 4 (content-model-to-ui's server-action form and Vue and Svelte output), as section 4 sets out. Then ask me which of P35, P41, P42 and P43 comes next. Every eval run and every paid live session costs real money: ask me before any run, with its estimate. Keep each PR under 100 files, since CodeRabbit skips larger ones; CodeRabbit and Codex are optional, never a gate.
You merge PRs yourself once they're ready (CI green, review threads resolved, clean), never in a way that breaks other pending work.
```
