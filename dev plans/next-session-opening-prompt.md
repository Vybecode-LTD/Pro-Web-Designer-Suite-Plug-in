# The opening prompt for the next session

Written 2026-10-05, at the end of the third Phase 4 session (P14 and P15). Paste the block below into a new session. It complements `next-session-prompt.md`, which still says #52 is open: #51 and #52 were merged after it was written.

```
You're continuing work on web-design-suite, a Claude Code plugin, in C:\DEV\Pro-Web-Designer-Suite-Plug-in. Budget: this session may run up to 750 thousand tokens, with no compacting. Report usage after each PR, warn early, and write the handoff before the cap.
1. Run: git fetch && git checkout main && git pull && gh pr list --state open
2. Read "dev plans/next-session-prompt.md" in full and follow it. Then read CLAUDE.md and docs/HANDOFF.md, as it says.
Since the handoff was written, #51 (the docs) and #52 (the audit's test-path fix) were merged, so main is at 73ad8c5. #49 and #50 (P15) are still open. Both now need main merged in first: #52 added a CHANGELOG entry in the same place (keep both). Then fix #49's two open CodeRabbit threads as §3 says: pair a negative cancel only when the parent's padding on that side is unambiguous. Merge #49, retarget #50 to main, and merge it.
You merge PRs yourself once they're ready (CI green, review threads resolved, clean), never in a way that breaks other pending work. Then P16 (the Figma scripts) and P17 (the lifecycle instructions), and further into Phase 4 if the budget allows.
```

This file was saved without a commit. The next session should commit it with its first docs change, together with the `README.md` line for it.
