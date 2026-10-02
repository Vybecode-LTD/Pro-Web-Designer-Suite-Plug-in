# Handoff

**2026-10-01**, in the session that opened PRs #12, #13 and #14.

## State

- **3.2.1 is released** (`v3.2.1`, `63932cf`) and installed. 3.3.0 is in progress and unreleased.
- **Merged for 3.3.0:** PRs #4 to #10.
- **Open, stacked, to merge in this order:**
  1. **#12** `fix/w1-schema-sources` → `main`. The parser on real output: DL-A7, DL-C2, DL-B8. It reads `pg_dump --quote-all-identifiers` (what `supabase db pull` runs), `ALTER TABLE` replays, `$$` bodies and wrapped `gen types` unions. Fixtures are in `tests/fixtures/supabase/`.
  2. **#13** `feat/w1-policies` → #12. DL-B2 and DL-B1:
     - `db/policies/<table>.policies.todo.sql`: RLS, policies guessed from the keys, and column grants equal to the form's `Draft`;
     - a plain-SQL smoke test per table;
     - `lib/supabase.ts`.
     - `test_policies` runs the SQL on a scratch Postgres when `initdb` is on PATH.
  3. **#14** `fix/w2-canonical-index` → #13. SB-A8, SB-A23, SB-C9:
     - `layers` in `design-rules.json`, with `vendor` after `reset`;
     - the audit and stylelint refuse an import into an unstated layer;
     - the canonical `starter/styles/index.css` and `configs/index.tailwind.css`, quoted by five references;
     - two wrong claims about a vendor's `!important`, corrected.
  - GitHub retargets each when the one below merges. If it doesn't, rebase onto `main`. Each branch carries the previous one's commits.
- **Tests:** 406 on #14's branch, passing on 3.14 and 3.9 (392 on #12, 403 on #13).
- **Brewr's dump is dropped** (2026-10-01): the user has no database password for it, and `shop.dump.sql` already covers real `pg_dump` output. Brewr (`ccsgoijoouggdepsweus`) is still active, waiting on the user's word to pause it (`pause_project`).
- **Decisions the user has not made:**
  - stylelint reads no Sass (it would need `postcss-scss`).
  - Scope: I recommended finishing phases 3 to 5 and moving phase 6 to a backlog. No answer yet.
- **Left open in this work:**
  - DL-B2's server-side schema (pydantic or zod mirroring the constraints);
  - SB-C9's Tailwind v3 entry, which is still inline in stack-tailwind.

## Next steps

1. **After the merges:** check that `main` has all three, then delete the branches.
2. **Pause Brewr** if the user agreed.
3. **The rest of W2:**
   - **N1:** decide each row of the gates-disagree table in the plan, spec first, and make all three gates follow it.
   - **N2:** `tools/sync_rules.py --check`, and conformance fixtures through the real tools.
   - **N3:** a stylelint snippet test, then fix the 56 failing reference snippets or the config.
   - **SB-A11, A15, A25,** and the rest of **SB-C2**.
4. **Then W3** (generators, roles, starter files) and **W4** (hygiene, N4 to N10). Then release 3.3.0 by the plan's release procedure.

## Blockers

None.

## Warnings

- **Cost.** The usual cap is 500 thousand tokens a session; the user allowed 750 thousand for this one, which stopped at about 580 thousand. Report usage as you go, and don't fan out to subagents.
- **Heredocs in the Bash tool** turn `\\b` into a backspace byte and drop other backslashes. Write edit scripts with the Write tool, then run them.
- **`pg_ctl start` from Python on Windows** must not capture output: the server inherits the pipes and the call never returns. `test_policies` uses DEVNULL and a log file.
- **Local Postgres 18** is installed. The scratch cluster from this session is at `<scratchpad>/pgdata`, on port 54329; stop it with `pg_ctl -D … stop`.
- **pg_dump on Windows writes CRLF.** Convert a dump to LF before committing it.
- **A new `§` pointer in any file** must be registered: `python tools/check_pointers.py --write-register`, then read the diff.
- **Don't edit a script while the suite runs.** A test file edited mid-run is loaded by the next interpreter's run.
- **The installed plugin is a copy, and sessions load a cache of it.** Update both after every release.
- **The repository is public.** Commit nothing private.
