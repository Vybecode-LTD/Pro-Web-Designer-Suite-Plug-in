# Handoff

**2026-10-01**, in the session that opened PR #12.

## State

- **3.2.1 is released** (`v3.2.1`, `63932cf`) and installed. 3.3.0 is in progress and unreleased.
- **Merged for 3.3.0:** PRs #4 to #10. Those are N6, SB-A9 with N11, N12, SB-A24 with N13, W1's reference, W1's security pass and `scaffold_ui --strict`.
- **Open: PR #12, the parser on real output** (DL-A7, DL-C2, DL-B8). Branch `fix/w1-schema-sources`. It has no CI checks; it waits for review and the user's merge.
  - `introspect_schema` now reads `pg_dump --quote-all-identifiers` (what `supabase db pull` runs) and `ALTER TABLE` replays (identity, add, drop, alter and rename). It also handles `$$` bodies, pg_dump 18's `\restrict`, prettier's wrapped unions in `gen types`, and `BETWEEN`.
  - The fixtures are in `tests/fixtures/supabase/` (README there):
    - the worked example as a migration;
    - a real `pg_dump` of it from local Postgres 18;
    - its generated types;
    - Brewr's real `gen types`.
  - §1 of `supabase-integration.md` is now measured on those fixtures. Two of its claims were wrong.
  - 392 tests pass on 3.14 and 3.9. Of the 15 new ones, 13 fail on `v3.2.1`; the other 2 are controls.
- **Brewr** (`ccsgoijoouggdepsweus`) is **still active**, waiting for the user's `pg_dump`. The command is under Next steps. Pause it (`pause_project`) once the dump is in, or when the user says so.
- **Decisions the user has not made:**
  - stylelint reads no Sass. Teaching it means shipping `postcss-scss`.
  - Scope: I recommended finishing phases 3 to 5, releasing, and moving phase 6 (broader coverage) to a backlog. No answer yet.

## Next steps

1. **PR #13: the rest of W1 in the scaffold** (DL-B2, the rest of DL-B1). Base it on main once #12 is merged, because it uses #12's fixtures. The design below was proven on Postgres 18 on 2026-10-01.
   - **`features/<t>/<t>.policies.todo.sql`, one per entity.** Each file enables RLS. It then proposes policies from the first of these that matches:
     - a primary key that references `auth.users` gets `id = (select auth.uid())`;
     - an owner column gets the same check on that column. An owner column is a foreign key to `users`, or to a table whose key is `auth.users`, or a column named `user_id`, `owner_id`, `author_id`, `created_by` or `customer_id`;
     - a child of an owned parent gets an `exists (…)` check;
     - a tenant column (`org_id` and the like) gets a TODO with the security-definer helper template from `w1-supabase-facts.md`;
     - anything else gets select for `authenticated` and no writes.
   - **Grants in the same file:** `revoke insert, update … from authenticated`, then grant insert on the writable columns plus the owner column, and update on the writable columns only. "Writable" means `emit_types`' `Draft` list (`ans.in_form`, not readonly), so the database and the form agree.
   - **`<t>.policies.test.sql`:** plain SQL in a transaction that rolls back. It asserts:
     - `relrowsecurity` is on;
     - `anon` sees 0 rows;
     - as `authenticated` (`set local role`, plus `set_config('request.jwt.claims', …)`), no foreign rows are visible;
     - `update … set <authority column> = <itself> where false` raises `insufficient_privilege`, and the same update on a writable column passes. The privilege check runs even with `where false`.
   - **A real-Postgres test**, skipped when `initdb` is not on PATH:
     - its stub's `auth.uid()` reads `request.jwt.claims`, as Supabase's does;
     - it applies every policies file and runs every test file;
     - re-introspecting the DDL plus the policies must give no findings;
     - a `using (true)` variant must make the smoke test fail.
   - **`lib/supabase.ts`** is the §9 snippet, plus a throw when the key starts with `sb_secret_`.
   - **Docs:** update §9's "The scaffold does not write them" and SKILL.md's "does not decide: … permissions".
2. **Brewr's real dump**, when the user has run this in cmd (Session pooler URI from the dashboard's Connect button):
   `pg_dump --schema-only --quote-all-identifiers --no-owner -n public "<URI>" > "%USERPROFILE%\Downloads\brewr-schema.sql"`
   Read it for anything private. Add it as `tests/fixtures/supabase/brewr.dump.sql`, with a test that it agrees with `brewr.types.ts`, then pause Brewr.
3. **The rest of W2:** N1 to N3, SB-A8, A11, A15, A23, A25, SB-C2 and C9. Then W3 and W4, and release 3.3.0.

## Blockers

None.

## Warnings

- **Cost.** The cap is 500 thousand tokens a session; this one stopped at about 350 thousand. Keep a session to one or two PRs and report usage as you go. Don't fan out to subagents.
- **Local Postgres 18** is installed (`initdb`, `pg_ctl`, `psql` on PATH). For a scratch cluster: `initdb -D <scratch>/pgdata -U postgres -A trust`, then `pg_ctl -D … -o "-p 54329" start`. Roles are per cluster, so create them once. Stop the cluster when done.
- **pg_dump on Windows writes CRLF.** Convert a dump to LF before committing it.
- **Fail-before from Git Bash.** `tar -x -C` needs a POSIX path (`cygpath -u`), and `WDS_PLUGIN_ROOT` a Windows one (`cygpath -w`).
- **Don't edit a script while the suite runs.** Every test spawns the scripts afresh, and a test edited mid-run is loaded by the next interpreter's run.
- **Heredocs in the Bash tool lose backslashes.** For regex edits, write a small Python file with the Write tool.
- **The installed plugin is a copy, and sessions load a cache of it.** Update both after every release.
- **Never run `npm ci` in a worktree** whose `tooling/*/node_modules` is a junction.
- **The repository is public.** Commit nothing private.
