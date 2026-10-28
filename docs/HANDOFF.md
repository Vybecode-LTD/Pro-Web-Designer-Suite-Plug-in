# Handoff

**2026-10-28: the full audit of `main` and the completion runbook. No code changed.**
- `dev plans/web-design-suite-audit-2026-10-28.md` records 281 findings (4 critical, 44 high, 109 medium, 124 low) and 23 open items over every script, browser script, hook, the MCP server, the lint configs, the suite, CI and release, the evals, the distribution repository, every shipped document and the plans; the thirteen pass files with every finding's evidence and fix are in `dev plans/web-design-suite-audit-2026-10-28/`.
- `dev plans/web-design-suite-completion-runbook.md` defines "100% done" (nine conditions), lists twelve decisions for the owner (§2) and the owner's own steps (§3), and schedules 24 packages, P66 to P89, in eight stages (§4) that close every finding and open item.

The next session starts from `dev plans/next-session-prompt.md`, which sends it to the runbook's §2 (the decisions) and §4 (the packages, in order).

## State

- **`main` at `8441ff0`** (#214, the previous session's docs). **Its CI is red:** run 40681521613 failed on `macos-latest · Python 3.14` only, in `test_runtime_urls.EachPageHasItsTypesBudget` (a timing test the flake list called a Windows flake; it has now failed on a third platform). The code merge before it (`e59d6b3`, #213) was green on all seven legs. The first package, P66, makes the timing tests honest instead of rerunning.
- **This PR, #215**, `docs/audit-2026-10-28-runbook`: the audit, the runbook, this handoff, the starting prompts, `CLAUDE.md`'s Current state and CLI path, and `dev plans/README.md`. The old 125 KB starting prompt is kept as `dev plans/next-session-prompt-2026-10-27-full.md` until P69 folds its rules and facts into `CLAUDE.md` and `docs/FACTS.md`.
- **Released:** `v4.0.1` on `84f4a4f`; the distribution repository's `main` and `v4.0.1` at `4809e3f`, verified today: each of the release zip's 230 files has the same SHA-256 as the distribution tree's file at `v4.0.1`. 4.0.2 is unreleased on `main` (P60 to P65); the runbook's Q1 asks whether it ships alone or folds into the audit release, 4.1.0.
- **The directory:** 4.0.1 submitted 2026-10-26, still waiting for a reviewer at the last read (2026-10-27).
- **The owner's install is 4.0.1** (2026-10-28, user scope, from the distribution marketplace); the 3.6.0 `web-design-suite` install and its local marketplace are gone. The runbook's L4 and §3 item 6 are done for this release; the next release repeats `claude plugin update`.
- **The execution plan:** `check_execution_plan.py` 0 open, 0 scheduled; the runbook's packages get their rows (N60 to N83, P66 to P89) in stage 0. Next free ids: N60, P66, PR #216.
- **The desktop app's CLI** is at `C:\Users\vybec\AppData\Local\Claude-Data\claude_pzs8sxrjxfjjc\claude-code\2.1.308\c17a819afb40\claude.exe` (2.1.308); both paths the docs gave before are gone. `claude plugin validate --strict` passes on the plugin, the marketplace root and the built tree.

## Next steps

1. **Ask the owner the runbook's twelve decisions (§2)** and record the answers in its §7. Q1 (one release or two), Q2 (4.1.0), Q3 (Phase 7 out of done) and Q7 (split the starting prompt) shape the order.
2. **Ask the owner for the four GitHub settings (§3, items 1 to 4):** the ruleset on `main`, security settings on both repositories, the distribution repository's settings, topics and the social preview.
3. **Stage 0, in order:** P66 (`main` green, the timing tests honest), P67 (the process gates), P68 (the maintainer tools), P69 (the plans and the CLI path). Each gets its N-item and P-row first; each follows the runbook's §5 protocol.
4. Then stages 1 to 4 by the runbook's order; stage 5 is the release.

## Open owner decisions

All twelve are in the runbook's §2 with a recommendation each; none is decided. The four from before (where issues live, a terms-of-service link, `check.py` and the snippet tests, splitting the prompt) are Q4, Q5, Q8 and Q7 there. The live check's three remaining follow-ups are Q9; the 3.5.0 notes are Q10; the memory notes are Q11; `wds-gate-scratch` is Q12.

## Warnings

- **`main` is red** (above). The workspace rule puts a red suite before anything else; P66 is first for that reason.
- **The four critical findings** are user-file hazards in shipped scripts (`cluster_values.py` overwrites `tokens.json`, `build_email.py --text` is unguarded, the schema reader drops `check_*`/`unique_*`/`exclude_*` columns, the extractor and the diff misread theme-scoped rules). They are P70 to P72, after stage 0.
- **The 390 px hang is explained** (JS-B-1: `await document.fonts.ready` with no bound, in three browser scripts) and is P74. Until then a run on such a page prints `browser:` and never returns; stop it with `TaskStop`, never `Stop-Process`.
- **Budget:** this session spent about 140K tokens in the main context and about 5.3M in the thirteen audit passes. A session may run up to 750K with no compacting; report usage after each PR.
- **Before a long `check.py`, look at the CPU.** Known timing flakes until P66: `EachPageHasItsTypesBudget`, `test_tbt_stops_at_tti`, `VitalsUnderCsp`, `test_interact_at_clicks_while_the_page_hydrates`.
- **Eight SKILL.md files are within 20 bytes of the 20,500-byte cap** (the runbook's P86 and P87 name the cuts); an addition needs a cut first.
- **Standing:** never grep `tooling/`; the repository is public; nobody commits to the distribution repository by hand; nobody but the owner acts in the directory portal; the four old ids stay; `python -B`.
