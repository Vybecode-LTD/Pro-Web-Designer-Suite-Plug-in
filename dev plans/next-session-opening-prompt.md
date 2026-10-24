# The opening prompt for the next session

Written 2026-10-24, at the end of the R4 session: the live check ran, its fixes merged (#201), and the evals passed all but `no-fake-countdown`. The `v4.0.0` tag waits on that case. Paste the block below into a new session.

```
You're continuing work on Pro Web Design Suite (pro-web-design-suite), a Claude Code plugin, in C:\DEV\Pro-Web-Designer-Suite-Plug-in. Budget: this session may run up to 750 thousand tokens, with no compacting. Report usage after each PR (the app's get_usage count), warn early, and write the handoff before the cap.
1. Run: git fetch && git worktree list && gh pr list --state open. Then: git checkout main && git pull
2. Read "dev plans/next-session-prompt.md" and follow it, starting with section 3. Then read CLAUDE.md and docs/HANDOFF.md, as it says.
4.0.0 is merged (#201, 5e30a70) but not tagged. The evals passed routing 23 of 23 and outcome 10 of 11: no-fake-countdown scored 2 of 3, and again 2 of 3 on my rerun, because the landing-page skill never loads on its prompt. The job, in section 4's order: fix that case, rerun it (ask me first, about $0.17), re-date the CHANGELOG, tag v4.0.0, then the distribution repository's checks. Ask me before anything is submitted to Anthropic's directory. Keep each PR under 100 files; CodeRabbit and Codex are optional, never a gate.
You merge PRs yourself once they're ready (CI green, review threads resolved, clean), never in a way that breaks other pending work.
```
