# Handoff

**2026-10-01**, in the session that opened the SB-A24 pull request (the audit on Sass).

## State

- **3.2.1 is released** (`v3.2.1`, `63932cf`) and installed from it, in the local marketplace and in the cache that sessions load. 3.3.0 is in progress and unreleased.
- **Merged for 3.3.0:** PR #4 (Python 3.9, N6), PR #5 (SB-A9 and N11) and PR #6 (N12). CodeRabbit left no review of the last commits of #5 and #6, so there was nothing to fold in.
- **Open: SB-A24, branch `fix/sb-a24-audit-scss`.** The rules are in `design-rules.json` under `sass`. The audit is the only gate that reads Sass: the stylelint config lints `.css` and ships no Sass syntax.
  - A rule inside a `@mixin` or `@function` is not unlayered CSS. The references' own `_mq.scss` failed.
  - A Sass variable holding a length, a hex or functional colour, a duration or an easing curve fails as `sass-literal` outside a token file.
  - **Found on the way (N13), and fixed in the audit:** the braces of an interpolation (`.card-#{$name}`) closed the layer around them, and indented Sass (`.sass`) passed as clean. A `.sass` file is now listed as skipped.
  - 359 tests pass on 3.14 and 3.9. The six new tests fail on `v3.2.1`.
- **Decisions in SB-A24** a reviewer may question; each is one condition in `audit_css`:
  - A breakpoint is known by its name: `$bp`, `$bp-*`, `$breakpoint*`.
  - A variable local to a `@function` is not checked (`$ratio * 1rem` is a unit conversion).
  - A named colour in a Sass variable is not checked, because a list of names (`$sides: top, right`) would be misread.
- **The review's repro inputs stay local** (the user's decision): `dev plans/web-design-suite-review/fixtures/` is ignored through `.git/info/exclude`, never committed.

## Next steps

1. **Answer CodeRabbit on the SB-A24 pull request**, then merge it when the user says so.
2. **W1**, the Supabase access boundary. The facts are in `dev plans/w1-supabase-facts.md`; re-read them at their source on the day.
3. **The rest of W2:** N13's open half (`extract_literals` and `a11y_static` report a `.sass` file clean), N1 to N3, SB-A8, A11, A15, A23, A25, SB-C2 and C9. Then W3 and W4, and release 3.3.0.
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
