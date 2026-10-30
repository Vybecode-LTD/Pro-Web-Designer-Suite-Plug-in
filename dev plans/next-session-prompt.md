# Start here: the next session

**Written 2026-10-30, at the close of its first session.** It points at files; it restates nothing.

## 1. What this is

**pro-web-design-suite**, a Claude Code plugin of 13 skills, in `C:\DEV\Pro-Web-Designer-Suite-Plug-in`.
- **Repository:** public, MIT. The plugin is at `plugins/pro-web-design-suite`.
- **Releases:** they reach `Vybecode-LTD/pro-web-design-suite` only through `release.yml`.
- **Where the rules live:** `CLAUDE.md` is the map and loads by itself. Its Working rules and `docs/FACTS.md` hold the lessons.

## 2. Rules that override the defaults

`CLAUDE.md` and the runbook's §5 protocol bind.
- **One session**, in this checkout, up to 750K tokens, with no compacting. Report usage after each PR.
- **`main`'s ruleset:** PRs only, the seven checks, threads resolved, up to date with `main`.
- **Never:**
  - act in the directory portal
  - commit to the distribution repository
  - grep `tooling/`
  - write into OneDrive
  - "fix" the four old ids
  - run a paid eval without the owner's OK
  - delete a repository

## 3. The state, verified at the close

`docs/HANDOFF.md` has it. In short:
- **`main`** is #238's merge, on #237 (P78, `ff628be`) and #236 (P77, `aa1a7c0`).
- **Open: none.** Stages 0 to 2 and P77 and P78 are done. 1,832 tests.
- **Audit:** 125 of 281 findings closed.
- **Plans:** `check_execution_plan.py` reads 11 open, 11 scheduled. Next free ids N84 and P90; the next PR is #239.

Check it:

```bash
cd /c/DEV/Pro-Web-Designer-Suite-Plug-in && git fetch -q && git status --short && git log --oneline -3 origin/main && gh pr list --state open && python -B "dev plans/check_execution_plan.py"
```

## 4. The work, in order

The runbook (`dev plans/web-design-suite-completion-runbook.md`) has the plan: §4 the packages, §5 the protocol, §7 the ticks.

1. **P79, `design-token-migration`** (N73): the §4 stage 3 row. Its findings are in `dev plans/web-design-suite-audit-2026-10-28/py-b-studio-and-migration.md`.
   - Add the two unused names and the widened ESLint test from `docs/HANDOFF.md`'s Next steps.
   - Branch from `main`. After `gh pr create`, bind the PR (`get_status`) and turn Auto-fix on.
   - Answer Codex and CodeRabbit, each fix with a test that fails on the head they read. Merge with `--match-head-commit`.
2. **Then P80 to P85,** in order.

## 5. Owner decisions still open

None of the runbook's twelve. Ask before any of these:
- a paid eval run (P89)
- the release tag
- a large download
- anything in the portal

## 6. Environment and traps

**Environment:** Python 3.14 (`uv` for 3.9), Node 26. Playwright 1.64.1's Chromium is installed. The CLI is 2.1.309.

**Traps:**
- **Run Python with `python -B`.** Write patch scripts with the Write tool, since the Bash heredoc unescapes `\\`.
- **A `tools/`, `shared/` or spec change** makes `check.py` run the whole suite (about 30 minutes). Run it in the background and edit nothing meanwhile. It shows only the tail, so rerun the failing modules to see each failure.
- **A gate change** goes in the spec first, then `sync_rules.py`. Run `audit_design.py skills --strict` and `test_doc_snippets` early.

## 7. Evidence, memory, promotion candidates

- **Evidence:** the audit's pass files, named above.
- **Memory:** `C:\Users\vybec\.claude\projects\C--DEV-Pro-Web-Designer-Suite-Plug-in\memory\MEMORY.md`.

Candidates for `knowledge/`:
- CSS clamps an out-of-range channel. A parser that guesses (a unitless `64.5` read as a percentage) measures what no browser draws.
- An exemption keyed on a whole line hides a real finding beside it. Key it to the token itself.
- A stylelint-disable comment can carry the audit's pragma after `--`, so one comment silences both gates with one reason.

## 8. End of session

1. Rewrite `docs/HANDOFF.md` and this file.
2. Update `CLAUDE.md`'s Current state and the runbook's §7, and run the checker.
3. Commit the docs in their own PR and merge it.
4. Give the owner the chip and the printed prompt.
