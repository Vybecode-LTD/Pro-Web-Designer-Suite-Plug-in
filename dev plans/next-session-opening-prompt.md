# The opening prompt for the next session

Written 2026-10-06, at the end of the fifth Phase 4 session (the flake fix, P18 and P19). Paste the block below into a new session.

```
You're continuing work on web-design-suite, a Claude Code plugin, in C:\DEV\Pro-Web-Designer-Suite-Plug-in. Budget: this session may run up to 750 thousand tokens, with no compacting. Report usage after each PR, warn early, and write the handoff before the cap.
1. Run: git fetch && git checkout main && git pull && gh pr list --state open && git worktree list
2. Read "dev plans/next-session-prompt.md" in full and follow it. Then read CLAUDE.md and docs/HANDOFF.md, as it says.
#56 (the hydration flake), P18 (#57, #58) and P19 (#59) are merged and no PR is open. Remove any worktree left in the scratchpad from the last session. This session: schedule the three follow-ups in the handoff, then P20 (the scaffold's answers, accessible forms and a server schema), then P21 (the deck, honest by construction), and further into Phase 4 if the budget allows.
You merge PRs yourself once they're ready (CI green, review threads resolved, clean), never in a way that breaks other pending work.
```
