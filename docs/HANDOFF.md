# Handoff

**2026-10-02**, at the end of the session that opened and merged PRs #12 to #15.

**The next session starts from `dev plans/next-session-prompt.md`.** It has the orientation, and P0 and P1 in detail.

## State

- **3.2.1 is released** (`v3.2.1`, `63932cf`) and installed. 3.3.0 is in progress on `main`, unreleased.
- **Merged on 2026-10-02:**
  - **#12:** the schema parser reads real `pg_dump` and `gen types` output (DL-A7, DL-C2, DL-B8).
  - **#13:** the scaffold proposes each table's policies, with a smoke test, and writes `lib/supabase.ts` (DL-B2 in part, DL-B1).
  - **#14:** the canonical entry stylesheets, and `vendor` in the layer order (SB-A8, SB-A23, SB-C9 in part).
  - **#15:** the execution plan.
- **Tests:** 406, passing on Python 3.14 and 3.9 on Windows. macOS has never run, and Linux has never run the Node tests; P1's CI fixes both.
- **The plan:** `dev plans/web-design-suite-execution-plan.md` schedules all 164 open items in 44 PRs, P0 to P43, and `check_execution_plan.py` holds it at 164 of 164.
  - **P0** is new: what the reviews of #12 to #15 found, N16 to N25, ten small real bugs.
  - CodeRabbit's note on `--quote-all-identifier` is not taken: that line quotes the Supabase CLI's script, which spells it that way.
- **Decided by the user on 2026-10-02:** keep phase 6, and yes to every decision in the plan's §2:
  - CI replaces the two local full runs, from P1 on;
  - N1's five rows are decided;
  - SCSS goes into stylelint (P37);
  - a spike picks the Tailwind lint plugin (P36);
  - phase 6 ships as 4.0.0;
  - PRs stack;
  - evals are capped at **$15 per full run**.
- **Brewr** (`ccsgoijoouggdepsweus`) is paused, and its dump is dropped: the user has no database password, and `shop.dump.sql` covers real `pg_dump` output.

## Next steps

1. **P0**, then **P1**, as `dev plans/next-session-prompt.md` describes them.
2. **Then P2 to P8** and release 3.3.0 (R1), by the execution plan.

## Blockers

None.

## Warnings

- **Cost.** The cap is 500 thousand tokens a session unless the user says otherwise; this one was allowed 750 thousand and used about 720 thousand. Report usage as you go, and don't fan out to subagents.
- **Heredocs in the Bash tool** drop backslashes and turn `\b` into a backspace byte. Write scripts that contain backslashes with the Write tool.
- **`pg_ctl start` from Python on Windows** must not capture output. See `tests/test_policies.py`.
- **pg_dump on Windows writes CRLF.** Convert a dump to LF before committing it.
- **Register any new `§` pointer** with `tools/check_pointers.py --write-register`, then read the register's diff.
- **Don't edit a script while the suite runs.**
- **The installed plugin is a copy, and sessions load a cache of it.** Update both after every release.
- **The repository is public.** Commit nothing private.
