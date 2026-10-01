# Handoff

**2026-10-01**, in the session that opened PR #7 (SB-A24 and N13, the scripts on Sass) and the first W1 pull request, stacked on it.

## State

- **3.2.1 is released** (`v3.2.1`, `63932cf`) and installed from it, in the local marketplace and in the cache that sessions load. 3.3.0 is in progress and unreleased.
- **Merged for 3.3.0:** PR #4 (Python 3.9, N6), PR #5 (SB-A9 and N11) and PR #6 (N12). CodeRabbit left no review of the last commits of #5 and #6, so there was nothing to fold in.
- **Open: PR #7, SB-A24 and N13, branch `fix/sb-a24-audit-scss`.** The rules are in `design-rules.json` under `sass`. The audit is the only gate that reads Sass: the stylelint config lints `.css` and ships no Sass syntax.
  - A rule inside a `@mixin` or `@function` is not unlayered CSS. The references' own `_mq.scss` failed.
  - A Sass variable holding a length, a hex or functional colour, a duration or an easing curve fails as `sass-literal` outside a token file.
  - **Found on the way (N13):** the braces of an interpolation (`.card-#{$name}`) closed the layer around them, and indented Sass (`.sass`), which has no braces, passed as clean in the audit, the migration census and `a11y_static`. All three now list a `.sass` file as not read.
  - **From the reviews of PR #7** (CodeRabbit and Codex): a mixin that holds a whole rule is unlayered when included at the root of its own file; `0px 13px` no longer hides the `13px` (older than Sass: the audit read only the first length); a quoted string in a Sass variable or an interpolation is text; `$breakpointSmall` is a breakpoint.
  - **Not done, and the user's call:** CodeRabbit asked for stylelint and ESLint to follow the Sass rules. Neither reads Sass today, and `test_rules_spec` now holds that statement. Teaching stylelint Sass means shipping `postcss-scss` in the config, a new dependency for every project that uses it.
  - 364 tests pass on 3.14 and 3.9. Nine of the eleven new tests fail on `v3.2.1`. The other two pass on both: one holds the stylelint statement, and one guards a bug that existed only inside the PR.
- **Open: W1's reference, branch `feat/w1-supabase-boundary`, stacked on PR #7.** DL-A5 and DL-C4 are done, and DL-B1 in the reference: `supabase-integration.md` §9 says which key goes where, and §2, §4 and §7 are corrected. Every Supabase fact was re-read on 2026-10-01 (`dev plans/w1-supabase-facts.md`). 365 tests pass; the new one fails on `v3.2.1` in 16 subtests.
- **Decisions in SB-A24** a reviewer may question; each is one condition in `audit_css`:
  - A breakpoint is known by its name: `$bp`, `$bp-*`, `$breakpoint*`.
  - A variable local to a `@function` is not checked (`$ratio * 1rem` is a unit conversion).
  - A named colour in a Sass variable is not checked, because a list of names (`$sides: top, right`) would be misread.
  - A mixin defined in another file is not followed to its include.
- **The review's repro inputs stay local** (the user's decision): `dev plans/web-design-suite-review/fixtures/` is ignored through `.git/info/exclude`, never committed.

## Next steps

1. **Merge PR #7, then the W1 reference PR**, when the user says so. Reply to the review threads on #7 only if the user asks: the fixes are in `88b3cfc`.
2. **The rest of W1:** the security pass in `introspect_schema` (DL-A6, DL-C1), `policies.todo.sql` with a smoke-test stub (DL-B2), the generated `lib/supabase.ts` (the rest of DL-B1), and real `db pull` and `gen types` files as fixtures (DL-A7, DL-C2, DL-B8). The fixtures need a real Supabase project to pull from: ask the user which one.
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
