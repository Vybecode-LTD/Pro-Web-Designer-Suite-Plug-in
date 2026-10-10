# Handoff

**2026-10-10 (fourth session)**, after P30 (#97), N39 (#98), R3 (#99) and this docs PR. **3.5.0 is released**, which completes Phase 5 (a full Claude Code plugin). Phase 6 (4.0.0, broader coverage) is next, starting with P31 (the owner's choice).

**The next session starts from `dev plans/next-session-prompt.md`**: orientation, then P31 (DTCG tokens) in detail. `dev plans/next-session-opening-prompt.md` is the message to paste in.

## State

- **Merged this session**, each with CI green on its head, every thread resolved and GitHub clean:
  - **#97 (P30): the outcome evals**, merged as `922cf5a`. There are eleven cases in six areas under `evals/<area>/`. Each grades what the run wrote in both arms, and the skill and the gates' verdicts with the plugin only. The gates run through the plugin's MCP server, so no case grants Bash and none needs WSL2 (the owner). `evals.yml` runs routing in one arm, then outcome in both, under one $14 ceiling (the owner's shared $15). One router fix. SS-C7, SB-C6, GT-C10, LC-C10, PS-C7 and DL-C7 close; SB-C6 has three of its four cases, with the mega menu left out for the budget.
  - **#98 (N39)**, merged as `29b0504`. `a11y_static.py` read email templates as pages, so `/gate` failed on the plugin's own receipt template. A folder's templates are now the email lint's, and the hook stands aside only when the email build runs (Codex).
  - **#99 (R3): release 3.5.0**, merged as `44637c1`. The version is bumped, the CHANGELOG dated, and the live check recorded (`dev plans/web-design-suite-3.5.0-live-check.md`).
- **Evals:**
  - **The local check of the outcome set** (the owner's Max plan, one run per arm): 11 of 11, mean Δ 0.22, $2.21.
  - **The release dispatch** of `evals.yml` (`tag=all`) on `44637c1`: routing 23 of 23 ($4.18) and outcome 11 of 11 (mean Δ 0.15, $5.21), $9.39 in all, in 46 minutes (run 38075960885).
- **The live check:** 22 headless sessions, $3.01. Every hook, all fifteen commands, the six agents and the five MCP tools ran; the one defect was N39. `/install-gate`'s CI template passed all three jobs on GitHub, in the private scratch repository `Vybecode-LTD/wds-gate-scratch`.
- **The release:** `v3.5.0` (annotated, on `44637c1`) was pushed, and `release.yml` published it with the zip, the 13 `.skill` files and `SHA256SUMS`. The installed plugin was updated from the release zip, its checksum verified (3.4.0 to 3.5.0). The tag's own `evals.yml` run was cancelled at its start: it would have re-run the commit the dispatch had just passed, for about $9 more.
- **The plan:** 31 open items, 31 scheduled. About 980 tests.

## Next steps

1. **P31:** `shared/dtcg.py` (DTCG 2025.10 read and write, Tokens Studio sets and themes, `$deprecated`, and the Style Dictionary and Terrazzo routes), building on `figma-variables-sync/scripts/dtcg_values.py`.
2. Then the rest of Phase 6, in the plan's order unless the owner says otherwise.

## Open owner decision

- **`evals.yml` on a tag.** A release now runs the suite twice: the dispatch before the tag, which holds the release back, and the tag's own run. Drop the tag trigger, or keep it and cancel it each time as this session did?

## Warnings

- **The scratch repository** `Vybecode-LTD/wds-gate-scratch` is private and the owner's to delete.
- **CodeRabbit's free tier** allows one review an hour. It skipped #97 (107 files, over its 100-file limit) and was rate-limited on #99. Keep PRs under 100 files.
- **Outcome evals vary run to run.** In five cases the plugin's arm did the work without loading the skill, so their skill graders are indicators only, in both arms (§11 of `claude-code-capabilities.md`).
- **Open question:** `perf_audit.py` fails a starter project whose CSS is not bundled. The `@import` chain makes 8 requests, which is over the default budget, and `--src` reads the `@import` lines as errors. The CI template's test had to bundle.
- **Headless sessions are refused reads of a skill's reference files** (the live check's `/schema-to-screens`). Interactive sessions ask.
- **Flakes:** the hydration timing test on Windows 3.14, and `test_critique_snapshots` on Linux 3.9.
- **Still open from earlier:**
  - `--warning-700`, `--danger-100` and `--info-100` fall outside Display P3.
  - `check_roles.py` clips a colour outside sRGB.
  - The worked examples are tests.
  - A local build never matches the release's checksums.
  - Don't grep `tooling/`.
  - The repository is public.
