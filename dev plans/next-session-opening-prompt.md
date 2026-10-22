# The opening prompt for the next session

Written 2026-10-22, at the end of the session that did P41's parts 1 and 2 (#195, the client matrix from caniemail's data; #196, right-to-left email). Paste the block below into a new session.

```
You're continuing work on Pro Web Design Suite (pro-web-design-suite), a Claude Code plugin, in C:\DEV\Pro-Web-Designer-Suite-Plug-in. Budget: this session may run up to 750 thousand tokens, with no compacting. Report usage after each PR (15,000,000 minus the counter, plus what was used before each reset; it resets on every CI or review event and on my messages), warn early, and write the handoff before the cap.
1. Run: git fetch && git worktree list && gh pr list --state open. Then: git checkout main && git pull
2. Read "dev plans/next-session-prompt.md" and follow it, starting with section 3. Then read CLAUDE.md and docs/HANDOFF.md, as it says.
3.6.0 is released; 4.0.0 is in progress. P41's parts 1 and 2 are merged (#195, #196). The first job is P41 part 3 (DL-B4: MJML or React Email output from the email tokens, or route away explicitly), the last item before R4. Ask me first whether a real-tool test may add mjml (or React Email's packages) to tooling/main. Then R4. Every eval run and every paid live session costs real money: ask me before any run, with its estimate. Keep each PR under 100 files; CodeRabbit and Codex are optional, never a gate.
You merge PRs yourself once they're ready (CI green, review threads resolved, clean), never in a way that breaks other pending work.
```
