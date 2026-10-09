# The opening prompt for the next session

Written 2026-10-09, at the end of the session that merged P25 part 2 (#84) and P26 part 1 (#85). Paste the block below into a new session.

```
You're continuing work on web-design-suite, a Claude Code plugin, in C:\DEV\Pro-Web-Designer-Suite-Plug-in. Budget: this session may run up to 750 thousand tokens, with no compacting. Report usage after each PR (15,000,000 minus the counter, plus what was used before each reset), warn early, and write the handoff before the cap.
1. Run: git fetch && git worktree list && gh pr list --state open. Then, in the worktree that holds main (this checkout unless the list says otherwise): git checkout main && git pull
2. Read "dev plans/next-session-prompt.md" in full and follow it. Then read CLAUDE.md and docs/HANDOFF.md, as it says.
3.4.0 is released. P25 is complete (#82, #84: the hooks and the token diff), P26 part 1 is merged (#85: /gate and /install-gate, with the CI template), then the session's docs, and no PR is open. This session: P26 parts 2 and 3 (the other workflow commands), then P27 (the subagents, and the two hooks P25 left), re-reading the sub-agents page first.
You merge PRs yourself once they're ready (CI green, review threads resolved, clean), never in a way that breaks other pending work.
```
