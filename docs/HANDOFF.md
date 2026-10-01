# Handoff

**2026-10-01**, in the session that merged PRs #7 to #10.

## State

- **3.2.1 is released** (`v3.2.1`, `63932cf`) and installed from it, in the local marketplace and in the cache that sessions load. 3.3.0 is in progress and unreleased.
- **Merged for 3.3.0:** PR #4 (Python 3.9, N6), #5 (SB-A9, N11), #6 (N12), #7 (SB-A24 and N13, the scripts on Sass) and #8 (W1's reference: DL-A5, DL-C4, and DL-B1 in `supabase-integration.md` §9).
- **Merged as PR #9: W1's security pass** (DL-A6, DL-C1, N14, N15).
  - `introspect_schema` reads `ENABLE ROW LEVEL SECURITY`, `CREATE POLICY` and column revokes, and opens `--summary` with a SECURITY block: `BLOCK` for a table with RLS off or a policy whose write condition is `true`; `warn` for RLS with no user policy, or authority columns a user can change.
  - The findings are in the model (`security`). The "Is RLS on?" question defaults from the DDL, and `scaffold_ui` repeats the blocking findings.
  - N14, found on the way: the skill's own command passed `supabase/migrations/*.sql`, which failed on two files. Several DDL files are now one schema.
  - N15, from the reviews: a column-level revoke does nothing while a table-level grant stands, which is Supabase's default. The reference's own advice was wrong and is corrected; the pass tracks `GRANT`, `REVOKE` and `DROP POLICY` in order, and treats a column as safe only when a policy pins it to the caller.
  - 377 tests pass on 3.14 and 3.9. The twelve new tests fail on `v3.2.1`.
- **Decisions the user has not made:**
  - stylelint reads no Sass, so the audit is the only Sass gate (`test_rules_spec` holds the statement). Teaching stylelint Sass means shipping `postcss-scss`.
- **Decided by the user on 2026-10-01:**
  - `scaffold_ui` warns about blocking findings and still writes the screens; `--strict` writes nothing and exits 1, for CI (merged as PR #10).
  - The `db pull` and `gen types` fixtures (DL-C2) come from the user's shelved Supabase project "Brewr". Read the files for anything private before committing them: the repository is public.
- **A fact that changed the review's advice:** an UPDATE policy with no `WITH CHECK` is not unchecked. Postgres uses the `USING` expression for the new row (postgresql.org, CREATE POLICY, read 2026-10-01). So the security pass does not flag it; it flags authority columns instead.
- **The review's repro inputs stay local** (the user's decision): `dev plans/web-design-suite-review/fixtures/` is ignored through `.git/info/exclude`, never committed.

## Next steps

1. **Pull the parser fixtures from Brewr** (DL-A7, DL-C2, DL-B8). The project is `ccsgoijoouggdepsweus`, in a second organisation, so `list_projects` does not show it; `get_project` does. It was restored on 2026-10-01 for this and has 25 tables, all with RLS on and no rows.
   - `gen types`: the Supabase connector's `generate_typescript_types`. About 25 tables of output, so do it at the start of a session.
   - The DDL: the local Supabase CLI is broken (no `supabase-go`) and there is no Docker, but `pg_dump` 18 is on PATH. The user runs it, because it needs the database password: `pg_dump --schema-only --quote-all-identifiers --no-owner -n public "<session pooler URI from the dashboard's Connect button>" > toolingrewr-schema.sql`.
   - Read both files for anything private before committing them, then pause the project again (`pause_project`) unless the user says otherwise.
2. **The rest of W1, in the scaffold:** `policies.todo.sql` per table with a smoke-test stub (DL-B2), and the generated `lib/supabase.ts` (the rest of DL-B1). Then the parser on real `db pull` and `gen types` files (DL-A7, DL-C2, DL-B8), which waits on the user's choice of project.
3. **The rest of W2:** N1 to N3, SB-A8, A11, A15, A23, A25, SB-C2 and C9. Then W3 and W4, and release 3.3.0.
4. **Fold the PR-by-PR sequencing into the plan**, as the user asked for a plan covering every open issue. CLAUDE.md's active-work line has the current order.

## Blockers

None.

## Warnings

- **Cost.** The user caps a session at 500 thousand tokens. Keep a session to one or two PRs, report token use as you go, and do not fan out to subagents or run max-effort reviews unless asked.
- **Fail-before from Git Bash.** `tar -x -C` needs a POSIX path (`cygpath -u`); `WDS_PLUGIN_ROOT` takes a Windows path (`cygpath -w`). In cmd, CLAUDE.md's commands apply as written.
- **Don't edit the plugin while the suite runs.** Every test spawns the scripts afresh, so a mid-run edit mixes versions. Stop the run and start again.
- **Heredocs in the Bash tool** lose backslashes: a Python edit script with `\)` or `C:\…` in it fails to parse. Use the Edit tool for those.
- **The installed plugin is a copy, and sessions load a cache of it.** Update both after every release.
- **Worktrees.** Never run `npm ci` in a worktree whose `tooling/*/node_modules` is a junction; remove junctions with `os.rmdir` before `git worktree remove`.
- **Don't trust the review's ✔ marks.** Use the inventory.
- **The repository is public** (since 2026-09-28, MIT). Commit nothing private: no secrets, and nothing from the user's other work. Its history already names paths on this machine and two other projects; the user chose to leave that as it is (decision 1).
