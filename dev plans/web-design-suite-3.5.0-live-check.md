# 3.5.0: the live check (R3, 2026-10-10)

Before the release, everything Phase 5 added ran in a real Claude Code session for the first time: each hook, each of the fifteen commands, each of the six agents and each MCP tool. The owner chose headless sessions on their Max plan.

## How

- **The sessions.** One `claude -p` session per component, 22 in all, with Claude Code 2.1.293 and `claude-sonnet-5-5`. Each loaded the plugin from `main` at `922cf5a` (`--plugin-dir`), and each ran in a fresh copy of a scratch project.
  - `--setting-sources project,local` kept the user's settings out, so their installed 3.4.0 and other plugins did not load.
  - `--max-budget-usd` capped each session at $0.60 ($0.80 for the hooks), and the run stopped at $6 in all.
  - `--permission-mode acceptEdits` was used, with `Bash(python *)`, `Bash(node *)` and the gate tools allowed.
- **The project.** The starter's styles, a clean card component and a generated file, with every hook switched on. It held the inputs the commands need:
  - a published token snapshot;
  - the receipt email template;
  - a small build;
  - the Supabase fixture schema;
  - a Figma export;
  - the deck's decision log and findings;
  - a matrix manifest.
- **The CI template.** `/install-gate`'s workflow ran in a private scratch repository, `Vybecode-LTD/wds-gate-scratch`, which the owner may delete.

## What ran

All 22 sessions finished, for **$3.01** at list price.

| Component | Result |
|---|---|
| **Hooks** | All five acted on their edit, and the router named web-design-studio for the prompt. |
| ↳ design gate | Caught `padding: 13px` (raw-spacing). |
| ↳ a11y gate | Caught an empty link (WCAG 4.1.2). |
| ↳ token diff | A re-pointed `--bg-accent` is major, and `--fg-on-accent` falls from 4.92 to 3.56:1. |
| ↳ email build | Caught `#999999` text at 2.71:1. |
| ↳ generated-file guard | Blocked the edit to `@generated` `client.ts`. |
| **MCP tools** | All five passed on the clean project. |
| `/gate` | Failed on the receipt template's a11y findings: **N39**, below. |
| `/install-gate` | Did a dry run, listed the files and the packages to add, then stopped for confirmation. |
| `/new-system "#e8440a"` | Wrote `brand/`; the brand is exact at `--accent-500`, and 100 of 100 pairs pass. |
| `/contrast` | 100 of 100 pairs pass. It could not read the exit code: `$?` is not in its allowed tools. |
| `/migrate src` | Found nothing to migrate, but ran the clustering step its body says to stop before. |
| `/release-check` | Patch, nothing changed. It asks for `--from-version` when the project has no tags. |
| `/figma-sync` | The audit is clean. The generated tokens would be a major change against the project's 218, and it did not copy them over. |
| `/docs-check` | No drift. It said it compared nothing: the project has no docs baseline and no `docs/`. |
| `/schema-to-screens` | 108 files, a clean audit and the security pass. Its 63 questions went unasked (headless). |
| `/email-build --transactional` | 0 errors; 12.5 KB, 12% of Gmail's clipping limit. |
| `/deck` | 12 slides. It reported the open major finding and the gaps in the decision log. |
| `/gate-a11y --file` | axe in Chromium. The two errors (no title, no lang) are because the card is a fragment. |
| `/gate-perf` | Both layers passed. My runner gave a Git Bash `file://` path; Claude retried with a Windows one. |
| `/gate-matrix` | A proof sheet of 4 cells; exit 1 because there were no baselines yet, as designed. |
| `/critique` | The design critic returned six findings, the top three major (the card's link target first). |
| design-auditor | Pass. It noted the card stylesheet is not imported by `index.css`. |
| gate-runner | Ran the runtime a11y gate on `dist/index.html`. It needs a URL for the perf gate and a manifest for the matrix. |
| a11y-auditor | Static pass. It made no conformance claim. |
| supabase-security-reviewer | Fail: the `customers` policy pins only `id`, and order inserts can set `status` and the total. |
| codemod-batch-reviewer | "Fix first": no baseline commit or reconciliation to verify against. |

**The CI template on GitHub:**
- **The push run:** `gates` (Linux, `mcr.microsoft.com/playwright:v1.63.0-noble`: the three static gates, then axe and the vitals on the served build) and `windows` (the static gates) both passed.
- **A run by hand** with `update-baselines`: `baselines` passed and uploaded `design-gate-baselines`.
- **The project:** it needed its CSS bundled. The starter's unbundled `@import` chain (8 requests) fails the default performance budget, which is the open question in the HANDOFF.

## What it found

- **N39, fixed in #98.** `a11y_static.py` read email templates as pages, so `/gate` failed on the plugin's own receipt template. The a11y hook did the same after each edit to a template. A folder's templates (the config's `emails`) are now the email lint's. The hook stands aside only when the email build runs (Codex on #98).
- **Notes, not defects:**
  - `/contrast` asked for `$?`, which its allowed tools refuse.
  - `/migrate` chained the cluster step onto the census.
  - A headless session was refused a read of a skill's reference file. Interactive sessions ask.
