# The opening prompt for the next session

Written 2026-10-11, at the end of the session that merged P31 parts 3 to 5 (#105 the DTCG resolver module, #106 `$deprecated` into the release gate, #107 Style Dictionary's and Terrazzo's names), which completes P31. Paste the block below into a new session.

```
You're continuing work on web-design-suite, a Claude Code plugin, in C:\DEV\Pro-Web-Designer-Suite-Plug-in. Budget: this session may run up to 750 thousand tokens, with no compacting. Report usage after each PR (15,000,000 minus the counter, plus what was used before each reset; it resets on every CI event), warn early, and write the handoff before the cap.
1. Run: git fetch && git worktree list && gh pr list --state open. Then, in the worktree that holds main (this checkout unless the list says otherwise): git checkout main && git pull
2. Read "dev plans/next-session-prompt.md" in full and follow it. Then read CLAUDE.md and docs/HANDOFF.md, as it says.
Phase 6a is under way toward the 3.6.0 release: P31 is done (the DTCG reader and writer, Tokens Studio, the resolver module, $deprecated into the ledger, the name routes). This session: P32 (Figma on every plan: a plugin-script route for use_figma, reading through the Figma MCP server, each plan's mode limits), re-reading the Plugin API's variables pages, the MCP server's tools and Figma's plan limits first, then P33, P38, P39 and P40 toward 3.6.0. Every eval run costs real money: ask me before any run, with its estimate. Keep each PR under 100 files, since CodeRabbit skips larger ones.
You merge PRs yourself once they're ready (CI green, review threads resolved, clean), never in a way that breaks other pending work.
```
