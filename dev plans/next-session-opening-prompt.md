# The opening prompt for the next session

Written 2026-10-10, at the end of the second session that day, which merged P27 part 2 (#91), P28 part 1 (#92) and N38 (#93). Paste the block below into a new session.

```
You're continuing work on web-design-suite, a Claude Code plugin, in C:\DEV\Pro-Web-Designer-Suite-Plug-in. Budget: this session may run up to 750 thousand tokens, with no compacting. Report usage after each PR (15,000,000 minus the counter, plus what was used before each reset), warn early, and write the handoff before the cap.
1. Run: git fetch && git worktree list && gh pr list --state open. Then, in the worktree that holds main (this checkout unless the list says otherwise): git checkout main && git pull
2. Read "dev plans/next-session-prompt.md" in full and follow it. Then read CLAUDE.md and docs/HANDOFF.md, as it says.
3.4.0 is released. P27 is complete (#89, #91: subagents, /critique, the a11y and email checks in the gate's hook) and P28 part 1 is merged (#92: the MCP server for the gates; the LSP spike not shipped), with N38 (#93), then the session's docs, and no PR is open. This session: P28 part 2 (bin/: ask me first; without my yes, close XC-B1 in the docs), then P29 (the eval framework and the routing cases), re-reading the plugin-evals page first. Evals cost real model calls: ask me about the signed-in CLI and the CI secret before any run.
You merge PRs yourself once they're ready (CI green, review threads resolved, clean), never in a way that breaks other pending work.
```
