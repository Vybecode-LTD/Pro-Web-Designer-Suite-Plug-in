# Handoff

**2026-10-16**, after P54 parts 5 to 8 of Phase 6c, the owner's audit. **Next: P54 part 9, §3.8 (T1, T2), then P55, the lows.** The owner placed all of Phase 6c (P50 to P55) before Phase 6b's remaining workstreams.

**The next session starts from `dev plans/next-session-prompt.md`**: orientation, then the work in detail. `dev plans/next-session-opening-prompt.md` is the message to paste in.

## State

- **#149, P54 part 5 (§3.4's second half: V2, V3, V10, `extract_system --tokens` on JSON)**, merged as `6b0900e`. `dtcg.recorded()` reads a document's or a resolver's record of the tokens it left out, in source order (a later source that writes a token ends its record); `read_deprecations` reads its marks; `extract_system` reads a contract.json or DTCG file through `read_tokens`, with the file's roles at Tier 2; every SKILL.md's copy note names its helpers.
- **#150, P54 part 6 (§3.5: E1 to E8, E10)**, merged as `c236246`. Naive system timestamps read-only; table names refused in the scaffold's paths; odd column names escaped; casts, JWT claims and quoted names pin a column; `pgTable.withRLS(`; the email minifier's word spaces; the style bytes; the templates lint clean (seven `--email-*` tokens); the deck's header placeholders.
- **#151, P54 part 7 (§3.6: G1, G2, G5, G6, G7)**: `aria-hidden` reads the subtree's real tab stops, a control's name is read at any depth (a component is "cannot tell", a silent subtree names nothing), the forced-colours survey is anchored, the TBT control clicks a button the task reveals, the coverage table marks what this suite does not run. **Merged as the last step of this session, or still open: check (§3 of the prompt).**
- **#152, P54 part 8 (§3.7: D1, D2, D3)**, merged as `cd4d1fe`. `release.yml` pins its actions to SHAs and keeps no credential; the tooling README explains zlib-ng; the README counts six `.mjs` scripts.
- **Reviews:** 11 real findings (Codex 7, CodeRabbit 4, two of them the same issue), and CI 3, each fixed with a test failing on the head it reviewed. One correction to the audit: 3.3.8's missing `autocomplete` is checked.
- **At the end:** the plan has 21 open items, all 21 scheduled; about 1,253 tests. This session used about 640 thousand tokens.

## Next steps

1. If #151 or this docs PR is still open, merge each once green.
2. **P54 part 9, §3.8:** T1 (`test_evidence.test_no_entry_outlives_its_figure` passes on an `also` substring; require the figure itself, word-bound the `also` values, then fix the register, re-reading each figure at its source), T2 (wall-clock thresholds: keep the ratio bounds, drop the absolute ones). After part 9, remove the `P54` row and mark N46 done.
3. **Then P55, the lows** (the audit's "low" findings and doc fixes, per area), then Phase 6b in the owner's order, then **R4**.

## Open owner decisions

- None new. The order within Phase 6b, once Phase 6c is done, is the owner's call.

## Warnings

- **A reader that merges two kinds of entry from ordered sources** (written tokens and a record of the left-out ones) must walk them in one pass, inline sources included (Codex on #149, twice).
- **A written boolean attribute is on by presence** (`hidden="false"` hides); only a bound value (`EXPR`) is unknown (CodeRabbit and Codex on #151).
- **`test_facts` holds every "N of the 55" to the table's Full count**: qualify a count, never change it.
- **`fail_before.py` swaps the plugin only**: a test of `release.yml` or `tooling/` reads as a control. Test it against `main`'s copies by hand, with `MSYS_NO_PATHCONV=1` before `git show origin/main:PATH` in Git Bash (without it the path is mangled and the `>` truncates the target).
- **Parallel PRs off `main` conflict on the CHANGELOG and both plans after every merge.** `keep_both.py` in this session's scratchpad resolves them (completion notes compared by part).
- **`test_interact_at_clicks_while_the_page_hydrates` failed once in 11 local runs**, with no output kept. Watch it on CI.
- **Still open from earlier:** Vue's `:style` (P55); the `VitalsUnderCsp` macOS flake; `perf_audit.py` and an unbundled `@import` chain; three tokens outside Display P3; don't grep `tooling/`; the repository is public; `Vybecode-LTD/wds-gate-scratch` is the owner's to delete.
