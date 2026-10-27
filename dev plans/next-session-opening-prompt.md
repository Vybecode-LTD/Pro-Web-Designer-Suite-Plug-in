# The opening prompt for the next session

Written 2026-10-27, at the end of the follow-ups session. P61 (#208), P62 (#209, `sync_email_tokens.py`) and P63 (#210, the scaffold's default sort) merged for 4.0.2, and 4.0.1 is still in Anthropic's directory review. Paste the block below into a new session.

```
You're continuing work on Pro Web Design Suite (pro-web-design-suite), a Claude Code plugin, in C:\DEV\Pro-Web-Designer-Suite-Plug-in. Budget: this session may run up to 750 thousand tokens, with no compacting. Report usage after each PR (the app's get_usage count), warn early, and write the handoff before the cap.
1. Run: git fetch && git worktree list && gh pr list --state open. Then: git checkout main && git pull
2. Read "dev plans/next-session-prompt.md" and follow it, starting with section 3. Then read CLAUDE.md and docs/HANDOFF.md, as it says.
4.0.1 (v4.0.1 on 84f4a4f) is in Anthropic's directory review, and I hold 4.0.2 until the reviewer decides. main carries P60 to P63 for 4.0.2. The job, in section 4's order: ask me what the portal shows and help me answer the review (ask me before every step in the portal; never submit, publish or withdraw anything yourself), then ask me whether to release 4.0.2, do one of the live check's four remaining follow-ups, or start Part B of the distribution plan. Any paid eval run needs my OK first. Keep each PR under 100 files; CodeRabbit and Codex are optional, never a gate.
You merge PRs yourself once they're ready (CI green, review threads resolved, clean), never in a way that breaks other pending work.
```
