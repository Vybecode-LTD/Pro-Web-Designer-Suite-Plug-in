# The opening prompt for the next session

Written 2026-10-05, at the end of the fourth Phase 4 session (P15 to P17). Paste the block below into a new session.

```
You're continuing work on web-design-suite, a Claude Code plugin, in C:\DEV\Pro-Web-Designer-Suite-Plug-in. Budget: this session may run up to 750 thousand tokens, with no compacting. Report usage after each PR, warn early, and write the handoff before the cap.
1. Run: git fetch && git checkout main && git pull && gh pr list --state open && git worktree list
2. Read "dev plans/next-session-prompt.md" in full and follow it. Then read CLAUDE.md and docs/HANDOFF.md, as it says.
P15 (#49, #50), P16 (#53) and P17 (#54) are merged and no PR is open. Remove any worktree left in the scratchpad from the last session. This session: P18 (the email templates and lint, with DL-A13 moved in from P19), then P19 (the email build and its facts), and further into Phase 4 if the budget allows.
You merge PRs yourself once they're ready (CI green, review threads resolved, clean), never in a way that breaks other pending work.
```
