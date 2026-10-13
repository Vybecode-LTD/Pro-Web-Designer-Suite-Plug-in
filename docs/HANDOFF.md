# Handoff

**2026-10-13**, after the 3.6.0 release (Phase 6a) and this docs PR. **Phase 6b, 4.0.0, is next**: ask the owner which workstream comes first.

**The next session starts from `dev plans/next-session-prompt.md`**: orientation, then Phase 6b in detail. `dev plans/next-session-opening-prompt.md` is the message to paste in.

## State

- **3.6.0 is released**: `v3.6.0` on `d91a146`, #123's merge, the commit after the release PR (#122). `release.yml` created the release, and it is installed: `claude plugin update` took the user scope from 3.5.0 to 3.6.0. The evals: routing 23 of 23 and outcome 10 of 11 on `d2c1f9b` ($9.35 of the $14 ceiling). The miss was `no-fake-countdown`: one of three runs never said why the resetting timer deceives. #123 fixed the persuasion skill, and the case then passed 3 of 3 on `d91a146` ($0.32), with a +1.00 difference over no plugin.
- **The live check** (`dev plans/web-design-suite-3.6.0-live-check.md`) ran each route 3.6.0 changed in 8 headless sessions and 3 reruns, for $2.92 on the owner's plan. It found three defects, each merged with CI green on its head, every thread resolved and GitHub clean:
  - **#119, `diff_system.py`:** a published DTCG file against the stylesheet it was written from was a major release for an unchanged system. Values are now compared by meaning. The DTCG writer keeps the tokens it cannot hold, with their values and `$deprecated` marks, in its `$extensions`, and the snapshot reads them back: from every listed file, and from a resolver's default contexts only. Codex found 7 real issues over three rounds.
  - **#120, `figma_to_tokens.py --reverse`:** it had no route from a `tokens.css`, and it made variables of a DTCG file's groups. It now reads a `tokens.css`, a DTCG file and a resolver, each theme a Figma mode, with types kept and problems reported. Codex found 3, CodeRabbit 1.
  - **#121, the router:** a Tokens Studio prompt without "Figma" reached no skill. Codex found 1, the description's length.
  - **#123, landing-page-conversion** (the evals): its ethics boundary now asks the reply to name a declined pattern and say it deceives, citing a law only if it applies. CodeRabbit and Codex found 1 each.
- **At the end:** `main` is this docs PR's merge. No other PR is open, and the checkout is on `main` with no other worktree.
- **The plan:** 23 open items, 23 scheduled, all in Phase 6b. 1,096 tests.

## Next steps

1. **Ask the owner which Phase 6b workstream comes first:** P34 runtime coverage, P35 the cheap checks and other engines, P36 Tailwind v4 (D4, the breaking change), P37 SCSS and frameworks, P41 email, or P42 and P43 persuasion.
2. The first Phase 6b PR opens `## 4.0.0 — unreleased` in the CHANGELOG.
3. R4 follows R3.6's order: a live check, the release PR, the evals on its merge, then the tag.

## Open owner decisions

- Which Phase 6b workstream comes first.
- Whether the migration's colour-to-role matching (ΔE alone mapped a grey to `--fg-warning`) becomes an item, with P36's `cluster_values.py` work.

## Warnings

- **Read `check.py`'s exit line before pushing.** #121 went up with a failing test, because one command read the result and pushed.
- **Headless live sessions:** a narrow allow-list sends Claude around the scripts. Allow every shell command and `--add-dir` the plugin (the 3.6.0 runner's `--wide`), in a scratch copy.
- **The bundled CLI** is 2.1.295 (`d2e29494ec83`). Its sign-in expired once this session; `claude.exe auth status` shows it.
- **Flakes seen on Windows CI:** `test_a_minified_stylesheet_is_extracted_in_roughly_linear_time` (a timing ratio) and the hydration test's `ERR_NO_BUFFER_SPACE`. Re-run the failed jobs.
- **The masters and their copies.** After every merge from a branch below, copy `shared/dtcg.py`, `shared/project_config.py` and `shared/project_config.mjs` over every copy, then run `TheCopiesAreTheMaster`.
- **Bash heredocs eat backslashes**, even quoted ones: it joined a continued line this session. Write such code with the Write or Edit tool.
- **CodeRabbit is not a merge gate**; its free tier ran out twice this session.
- **The scratch repository** `Vybecode-LTD/wds-gate-scratch` is private and the owner's to delete.
- **Still open from earlier:**
  - `perf_audit.py` and an unbundled `@import` chain;
  - the TBT flake on macOS;
  - `test_critique_snapshots`;
  - three tokens outside Display P3, and `check_roles.py` clipping outside sRGB;
  - the worked examples are tests;
  - a local build never matches the release's checksums;
  - don't grep `tooling/`;
  - the repository is public.
