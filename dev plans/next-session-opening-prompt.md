# The opening prompt for the next session

Written 2026-10-26, at the end of the directory session: `v4.0.1` (the listing icon) is tagged and distributed, the owner submitted it to Anthropic's directory, P58 closed with no change, and #207 (P60) cleared the icon's directory hold for 4.0.2. Paste the block below into a new session.

```
You're continuing work on Pro Web Design Suite (pro-web-design-suite), a Claude Code plugin, in C:\DEV\Pro-Web-Designer-Suite-Plug-in. Budget: this session may run up to 750 thousand tokens, with no compacting. Report usage after each PR (the app's get_usage count), warn early, and write the handoff before the cap.
1. Run: git fetch && git worktree list && gh pr list --state open. Then: git checkout main && git pull
2. Read "dev plans/next-session-prompt.md" and follow it, starting with section 3. Then read CLAUDE.md and docs/HANDOFF.md, as it says.
4.0.1 is tagged (v4.0.1 on 84f4a4f), the distribution repository holds it (4809e3f), and I submitted it to Anthropic's directory on 2026-10-26; it waits for a reviewer. The job, in section 4's order: ask me what the portal shows and help me answer the review (ask me before every step in the portal; never submit, publish or withdraw anything yourself), then ask me whether to release 4.0.2 (P60, the icon's directory hold, is on main), do P61 (CI's slow browser install), do one of the live check's six follow-ups, or start Part B of the distribution plan. Any paid eval run needs my OK first. Keep each PR under 100 files; CodeRabbit and Codex are optional, never a gate.
You merge PRs yourself once they're ready (CI green, review threads resolved, clean), never in a way that breaks other pending work.
```
