# The opening prompt for the next session

Written 2026-10-24, at the end of the R4 tag session: #203 fixed most of `no-fake-countdown`, `v4.0.0` is tagged and distributed, and the case's reliability is scheduled as P58. Paste the block below into a new session.

```
You're continuing work on Pro Web Design Suite (pro-web-design-suite), a Claude Code plugin, in C:\DEV\Pro-Web-Designer-Suite-Plug-in. Budget: this session may run up to 750 thousand tokens, with no compacting. Report usage after each PR (the app's get_usage count), warn early, and write the handoff before the cap.
1. Run: git fetch && git worktree list && gh pr list --state open. Then: git checkout main && git pull
2. Read "dev plans/next-session-prompt.md" and follow it, starting with section 3. Then read CLAUDE.md and docs/HANDOFF.md, as it says.
4.0.0 is tagged (v4.0.0 on d9125b7) and the distribution repository holds it (28efdaa). no-fake-countdown still passes about five runs in six (2 of 3 in evals.yml), and its reliability is P58. The job, in section 4's order: help me submit to Anthropic's directory (ask me before every step; never submit anything yourself), then ask me whether to do P58 or one of the live check's six follow-ups. Any paid eval run needs my OK first. Keep each PR under 100 files; CodeRabbit and Codex are optional, never a gate.
You merge PRs yourself once they're ready (CI green, review threads resolved, clean), never in a way that breaks other pending work.
```
