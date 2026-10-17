# Handoff

**2026-10-16**, the fourth session that day: Phase 6c's last piece and the first PR of Phase 6b. **Phase 6c, the owner's audit, is done.** **Next: P34 part 2 (shadow DOM), then P34 part 3 (several URLs and viewports), then the rest of Phase 6b in the order the owner chooses, then R4.**

**The next session starts from `dev plans/next-session-prompt.md`**: orientation, then the work in detail. `dev plans/next-session-opening-prompt.md` is the message to paste in.

## State

- **The owner's decisions (2026-10-16):** register D6's Baseline browser versions (not waive them); give Vue's `:style` an item (N48, scheduled with P37); P34 comes first in Phase 6b.
- **#162, P55 part 6 (D6's rest)**, merged as `7b1126a`. Twenty Baseline support lines in eight web-design-studio references are registered in `evidence.json`, each quote the status block of web-features' file for the feature (`97c5a95`, 2026-10-16).
  - The re-read corrected the Popover API (Chrome 116, not 114) and `@scope` (Firefox 146, Baseline since 2026-03-24, not "Firefox from 128").
  - `test_evidence.test_every_browser_version_is_registered` holds every quoted browser version, with each later version beside it (Codex on #162), to a registered figure or a `not_statistics` row.
  - N47 is done; N48 is new.
- **#163, P34 part 1 (GT-B1, GT-B2)**, merged as `8505aa1`. `browser_common.mjs` gives the URL gates `--wait-for`, `--steps`, `--storage-state` and `--header` (the page's own origin only). `measure_vitals` takes the wait and the session and refuses the rest, and an HTTP error status exits 2 in all three. Tests: `test_runtime_reach`.
- **Reviews:** Codex found 1 real issue on #162: the version pattern stopped at a browser's first version, so "Safari 17.5 and 17.4" hid the 17.4. It was fixed with controls the old pattern fails. On #163 Codex hit its usage limit and CodeRabbit its hourly limit, so it merged unreviewed; its Windows 3.9 cell failed once on the known `test_interact_at_clicks_while_the_page_hydrates` flake and passed on a re-run.
- **At the end:** the plan has 18 open items, all 18 scheduled; about 1,320 tests. This session used about 510 thousand tokens.

## Next steps

1. **P34 part 2, shadow DOM (GT-B3):** a deep query through open shadow roots for `a11y_runtime`'s in-page code (the focusables, document order, `activeElement`, the names, the contrast walker, reflow, the keymap), and a `cssPath()` that crosses a shadow boundary and resolves back. The prompt's §4 lists the call sites.
2. **P34 part 3 (GT-B4):** `--urls FILE` or a sitemap, a list of viewports, a URL-to-page-type map for perf.
3. **Ask the owner which Phase 6b workstream follows P34**: P35, P37 (now with N48), P41, P42, P43.
4. Then **R4**, release 4.0.0, in R3.6's order: a live check (the owner's OK and its estimate), the release PR, the evals (the owner's OK, about $11), the tag.

## Open owner decisions

- The order of Phase 6b's workstreams after P34.

## Warnings

- **`check.py` takes 20 to 25 minutes now** when a shared file changes (`browser_common.mjs` reaches 41 test modules), and longer while another project's suite runs on the machine.
- **Never edit a file the suite reads while `check.py` runs.** This session set an edited `browser_common.mjs` aside in the scratchpad for the run.
- **A fix in a test pattern is shown by a control** the old pattern fails (`fail_before.py` swaps the plugin, not the tests): `scratchpad/old_regex.py` did it for #162.
- **Inline `python -c` through the Bash tool breaks on quotes and parentheses**: write the script with the Write tool.
- **The byte table in `next-session-prompt.md` is held to the disk** (`test_docs.TheAuditsDocsLows`): update a row whenever a SKILL.md changes size. perf-budget-gate's is 20,493 now, 7 bytes from the limit.
- **Codex reviews again; CodeRabbit runs one review an hour.** Neither is a gate.
- **Still open from earlier:** the `VitalsUnderCsp` macOS flake; `test_interact_at_clicks_while_the_page_hydrates` failed once in 11 local runs; `perf_audit.py` and an unbundled `@import` chain; three tokens outside Display P3; don't grep `tooling/`; the repository is public; `Vybecode-LTD/wds-gate-scratch` is the owner's to delete.
