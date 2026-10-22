# The opening prompt for the next session

Written 2026-10-22, at the end of the second session that day, which did P41 part 3 (#198, the email tokens as an MJML head or a React Email theme). Phase 6b is done and no item is open. Paste the block below into a new session.

```
You're continuing work on Pro Web Design Suite (pro-web-design-suite), a Claude Code plugin, in C:\DEV\Pro-Web-Designer-Suite-Plug-in. Budget: this session may run up to 750 thousand tokens, with no compacting. Report usage after each PR (the app's get_usage count, or 15,000,000 minus the counter where it shows), warn early, and write the handoff before the cap.
1. Run: git fetch && git worktree list && gh pr list --state open. Then: git checkout main && git pull
2. Read "dev plans/next-session-prompt.md" and follow it, starting with section 3. Then read CLAUDE.md and docs/HANDOFF.md, as it says.
3.6.0 is released; 4.0.0 is ready to release: Phase 6b ended with P41 part 3 (#198), and nothing is open. The job is R4, the 4.0.0 release, in section 4's order: the live check of what changed, the release PR, the evals on its merge, the tag, then the distribution repository's checks. Ask me before the live check and before the eval run, each with its estimate: both cost real money. Ask me before anything is submitted to Anthropic's directory. Keep each PR under 100 files; CodeRabbit and Codex are optional, never a gate.
You merge PRs yourself once they're ready (CI green, review threads resolved, clean), never in a way that breaks other pending work.
```
