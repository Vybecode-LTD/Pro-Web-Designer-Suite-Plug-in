# Handoff

**2026-10-02**, at the end of the session that opened PR #16 (P0), PR #17 (P1) and PR #18 (P2 part 1).

**The next session starts from `dev plans/next-session-prompt.md`.** It has the orientation, then P2 part 2 and P3 in detail.

## State

- **3.2.1 is released** (`v3.2.1`, `63932cf`) and installed. 3.3.0 is in progress on `main`, unreleased.
- **Open, waiting for the user to merge (in this order):**
  - **#16, P0:** what the reviews of #12 to #15 found, N16 to N25, and N29, a gap found on the way. The schema parser (`$` names, `DROP` and `RENAME COLUMN`, Postgres 18's named not-null), the scaffold's policies (the model's schema, every reserved word, 63-byte policy names, write policies for server roles), and the layer statement (the entry names `utilities.css` and `overrides.css`; an import or a rule above the statement is refused by the spec, the audit and stylelint). Fail-before against `8ed2e84`: 15 tests fail, 20 controls. 419 tests passed on Python 3.14 and 3.9 locally. Its reviews (Codex, CodeRabbit) found five more edge cases, fixed in `81b50f9` with five tests that fail on its first commit; all eight threads are answered and resolved.
  - **#17, P1, stacked on #16:**
    - CI (`.github/workflows/ci.yml`): the suite and the static checks on Windows, Linux and macOS, at Python 3.9 and 3.14, with Node; and `claude plugin validate --strict`.
    - The release: `tooling/release/build.py` (the zip, 13 `.skill` files, `SHA256SUMS`) and `release.yml`, which a pushed `v*` tag runs. It is the only thing that creates a release.
    - The PR tools: `tools/fail_before.py` and `tools/check.py`.
    - N5: 17 scripts made executable, held by `test_file_modes`.
  - **CI on #17:**
    - The first run failed only on `setup-uv@v10`, a tag that does not exist (now `@v10.2.0`).
    - The second run found one real platform bug, fixed: `snapshot_matrix` missed an unstyled state on Linux and macOS. It also found two tests that assumed Windows.
    - The third run was green on Windows. On Linux and macOS the matrix check still missed the unstyled state, because twin cells never match pixel for pixel there. It now compares computed styles instead (`STYLE_SIGNATURE_FN`).
    - The fourth run was green on five of six jobs: the computed-style check works on Linux and macOS. macOS with 3.14 failed a timing-sensitive browser test (the mega-menu's safe triangle), whose real waits a loaded runner stretched; the scenario now runs on Playwright's fake clock.
    - The fifth run, with that change, was in progress at handoff. Auto-fix is on for #17, so the app reports a failure there; #18 needs it switched on too.
  - **#18, P2 part 1, stacked on #17:** `tools/sync_rules.py` writes the spec's layer order and statement, nesting depth and system colours into a `BEGIN design-rules` block in the audit and the stylelint config. `--check` runs in `check.py` and CI. Four new tests fail on 3.2.1; `check.py` (the whole suite) passed on 3.14.
- **Tests:** 435. **The plan:** 151 open items, all scheduled (`check_execution_plan.py`).
- **Decided by the user on 2026-10-02:** a session may run up to 750 thousand tokens, with no compacting.

## Next steps

1. **The user:** merge #16, #17 and #18 in that order, once CI is green. Each retargets to `main` when the branch below it is deleted.
2. **The next session:** if CI is not green, fix it first. Then P2 part 2 (the spec generates the value allowlists and ESLint's patterns, with conformance tests through all three tools) and P3 (the gates agree), as the prompt describes.

## Open questions for the user

- **Skill descriptions and claude.ai uploads.** All 13 descriptions are 301 to 368 characters. The platform's limit is 1024, but the claude.ai help center gives 200 for an uploaded skill. `build.py` warns and still builds the `.skill` files. Shortening them touches routing, so it is the user's call; it fits P27/P28.

## Warnings

- **Cost.** This session used about 650 thousand tokens. Long thinking is the largest cost: decide, then act.
- **Bash heredocs eat backslashes** (three times this session). Write anything with a backslash with the Write or Edit tool.
- **Don't edit, rename or delete a file the suite reads while it runs.** A rename mid-run gave ten false failures this session.
- **Never poll CI.** Read it with the app's `get_status` at natural points.
- **`pg_ctl start` from Python on Windows** must not capture output. See `tests/test_policies.py`.
- **pg_dump on Windows writes CRLF.** Convert a dump to LF before committing it.
- **Register any new `§` pointer** with `tools/check_pointers.py --write-register`, then read the register's diff.
- **The installed plugin is a copy, and sessions load a cache of it.** Update both after every release.
- **The repository is public.** Commit nothing private.
