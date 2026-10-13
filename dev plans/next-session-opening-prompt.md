# The opening prompt for the next session

Written 2026-10-13, at the end of the session that released 3.6.0 (Phase 6a). Its live check found three defects, fixed in #119 (diff_system against a DTCG file), #120 (`--reverse` from any token format) and #121 (Tokens Studio's route), before the release PR (#122). The evals missed one case, which #123 fixed in the persuasion skill, before the `v3.6.0` tag. Paste the block below into a new session.

```
You're continuing work on web-design-suite, a Claude Code plugin, in C:\DEV\Pro-Web-Designer-Suite-Plug-in. Budget: this session may run up to 750 thousand tokens, with no compacting. Report usage after each PR (15,000,000 minus the counter, plus what was used before each reset; it resets on every CI event and on my messages), warn early, and write the handoff before the cap.
1. Run: git fetch && git worktree list && gh pr list --state open. Then, in the worktree that holds main (this checkout unless the list says otherwise): git checkout main && git pull
2. Read "dev plans/next-session-prompt.md" in full and follow it. Then read CLAUDE.md and docs/HANDOFF.md, as it says.
3.6.0 is released. This session: Phase 6b, 4.0.0, as §4 of the prompt lays it out. Ask me first which workstream to start with (P34, P35, P36, P37, P41, or P42 and P43). Every eval run and every paid live session costs real money: ask me before any run, with its estimate. Keep each PR under 100 files, since CodeRabbit skips larger ones.
You merge PRs yourself once they're ready (CI green, review threads resolved, clean), never in a way that breaks other pending work.
```
