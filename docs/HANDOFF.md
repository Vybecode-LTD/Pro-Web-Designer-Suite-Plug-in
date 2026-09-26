# Handoff

**2026-09-26**, at the end of the session that reviewed and fixed PR #1 and started the CodeRabbit week.

## State

- **PR #1 (3.2.1)** is ready to merge, on `fix/3.2.1-distribution-readiness`.
  - Fixed, each with a fail-before: the ten-angle review's 30 findings, the gap sweep's 4, all five points of CodeRabbit's second review, and both of its third (report: `dev plans/web-design-suite-3.2.1-report.md`).
  - 339 tests pass on Python 3.10 to 3.14 on Windows, and on Linux (59 skipped: that WSL has no Node). `claude plugin validate --strict` passes on all three targets.
  - CodeRabbit has not reviewed the last push yet; its incremental review will be on the PR.
- **Python 3.9 (N6, decision 2)** is done on `feat/python-3.9-floor` (`644c528`), pushed, with no PR yet. It passed 335 tests on 3.9, 3.10 and 3.14. It is based on `00fb5f2`, so rebase it onto `main` once PR #1 merges. Expect conflicts in `tests/wds_support.py`, `tests/test_harness.py` and `tests/test_token_migration.py` (imports), `CLAUDE.md` and the plan (line 24, N6). Keep both sides; the floor becomes 3.9 everywhere, and the suite becomes 342 tests.
- **CodeRabbit** is on the Teams trial until about 2026-10-02: line-by-line reviews, 10 an hour, and each reply to a CodeRabbit thread costs one. Push fixes, let the incremental review mark threads addressed, and reply only where it does not.
- **Installed plugin:** 3.2.1 as first built (`8b27ff7`), without the review's fixes. Step 2 updates it.

## Next steps

1. **PR #1.** Read CodeRabbit's incremental review; fix what is right (with tests) and say why for anything declined. Merge with a merge commit, tag `v3.2.1` on `main`, push the tag.
2. **Release 3.2.1** (plan, release procedure, steps 4 and 6). Build the zip from the merge commit with `tooling/release/build_zip.py` into Downloads under a new name: the existing `web-design-suite-plugin-3.2.1.zip` was built from `8b27ff7`, and the builder never overwrites. Update the report's zip row. Mirror the extracted zip into the installed copy, `diff -r`, then `claude plugin update` and `details` with the bundled CLI.
3. **`.coderabbit.yaml`**, as a small PR merged early (CodeRabbit reads it from each PR's branch): `language: en-GB`, `reviews.profile: assertive`, `poem: false`, path filters for lockfiles and the review fixtures, and path instructions from CLAUDE.md's conventions (stdlib only, fail-before tests, `env()` for every test subprocess, one set of rules, size limits, cmd.exe commands).
4. **The 3.9 PR.** Rebase `feat/python-3.9-floor`, run 3.14 and 3.9, open the PR.
5. **Rescue the review's repro inputs** before Storage Sense deletes them: `%TEMP%/claude/C--DEV/5b1a5cc7-460d-4e95-848e-f823553c2172/scratchpad/review` (190 MB) into `dev plans/web-design-suite-review/fixtures/`. Without plugin copies, generated output, binaries and files over 500 KB it is 610 files, about 7 MB. Scan them for secrets first, and filter the folder out of CodeRabbit's review.
6. **Phase 3 as small PRs**, one item or a few each, so CodeRabbit reviews each: W2's audit false-clean (SB-A9, `//` inside `url()`) first, then W1 (Supabase; the facts are in `dev plans/w1-supabase-facts.md`), W3 and W4 (N4, N5, N7–N10, XC-A2, XC-A5, XC-B5, XC-C9). Release 3.3.0 when the phase is in.
7. **Plan the rest.** The user asked for a plan covering every open issue. The completion plan covers them all, but not the PR-by-PR sequencing above: fold that and the progress into the plan and the inventory.

## Blockers

None.

## Warnings

- **Cost.** The user is cost-sensitive, and this session ran past 4 million tokens. Keep a session to one or two PRs, and do not fan out to subagents or run max-effort reviews unless asked.
- **The installed plugin is a copy.** Update it after every release.
- **Worktrees.** Never run `npm ci` in a worktree whose `tooling/*/node_modules` is a junction; remove junctions with `os.rmdir` before `git worktree remove`.
- **Don't trust the review's ✔ marks.** Use the inventory.
- **Private material.** `dev plans/` names folders on this machine; settle decision 1 before the repository goes public.
