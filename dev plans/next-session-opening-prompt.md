# The opening prompt for the next session

Written 2026-10-19, at the end of the session that finished P35 (#179, the drivable a11y checks; #183, Firefox and WebKit). The plugin is now Pro Web Design Suite (#180). Paste the block below into a new session.

```
You're continuing work on Pro Web Design Suite (pro-web-design-suite), a Claude Code plugin, in C:\DEV\Pro-Web-Designer-Suite-Plug-in. Budget: this session may run up to 750 thousand tokens, with no compacting. Report usage after each PR (15,000,000 minus the counter, plus what was used before each reset; it resets on every CI or review event and on my messages), warn early, and write the handoff before the cap.
1. Run: git fetch && git worktree list && gh pr list --state open. Then, in the worktree that holds main (this checkout unless the list says otherwise): git checkout main && git pull
2. Read "dev plans/next-session-prompt.md" in full and follow it, starting with section 3. Then read CLAUDE.md and docs/HANDOFF.md, as it says.
3.6.0 is released; 4.0.0 is in progress. P35 and P56 (the webdesignersuite.com findings, #185 to #187) are done; P57 (a small check_roles fix) is open and, like P41 to P43, must land before R4. Ask me in what order to do P41 (email), P42 (persuasion law, consent, price tests, WCAG), P43 (page types, claims layer, routing) and P57, then do them as section 4 sets out; then R4. The plugin was renamed and given a distribution repository in my other session (#180 to #182): read docs/HANDOFF.md's section on it. Every eval run and every paid live session costs real money: ask me before any run, with its estimate. Keep each PR under 100 files, since CodeRabbit skips larger ones; CodeRabbit and Codex are optional, never a gate.
You merge PRs yourself once they're ready (CI green, review threads resolved, clean), never in a way that breaks other pending work.
```
