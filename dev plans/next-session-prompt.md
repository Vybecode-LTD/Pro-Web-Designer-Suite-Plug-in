# Start here: the next session

**Written 2026-10-28.** It points at files; it restates nothing.

## 1. What this is

**pro-web-design-suite**, a Claude Code plugin of 13 skills, in `C:\DEV\Pro-Web-Designer-Suite-Plug-in` (public, MIT; the plugin at `plugins/pro-web-design-suite`; releases go to `Vybecode-LTD/pro-web-design-suite` through `release.yml` only). `CLAUDE.md` is the map and loads by itself; its Working rules and `docs/FACTS.md` hold what the old long prompt held.

## 2. Rules that override the defaults

`CLAUDE.md`'s Gotchas, Conventions and Working rules bind, and the runbook's §5 protocol. One session, this checkout; up to 750K tokens, no compacting, usage reported after each PR. **Never:** act in the directory portal; commit to the distribution repository by hand; grep `tooling/`; write into OneDrive; "fix" the four old ids; run a paid eval without the owner's OK; delete a repository.

## 3. The state, verified 2026-10-28

`docs/HANDOFF.md` has it. In short: `main` = #224's merge (the session's docs) on `e8a46a6` (#223, P69); stage 0 done (P66 to P69); no PR open but #224 until it merges; Dependabot's #218 to #220 folded into #222; the owner's four GitHub settings **not done**; `check_execution_plan.py` 20 open; next free ids N84, P90, PR #225. Check it:

```bash
cd /c/DEV/Pro-Web-Designer-Suite-Plug-in && git fetch -q && git status --short && git log --oneline -3 origin/main && gh pr list --state open && gh run list --branch main --limit 2 && python -B "dev plans/check_execution_plan.py"
```

## 4. The work, in order

Read `dev plans/web-design-suite-completion-runbook.md` §4 (the packages) and §5 (the protocol); §7 has the ticks.

1. Check the owner's GitHub settings with the runbook's §6 ruleset command and `gh api repos/Vybecode-LTD/REPO` (`security_and_analysis`, `topics`, `has_issues`), REPO being each of `Pro-Web-Designer-Suite-Plug-in` and `pro-web-design-suite`; if not done, give the owner the steps (`docs/HANDOFF.md`, Open owner steps) and go on.
2. **P70, one overwrite guard per script** (N64; PY-B-1 and PY-E-1 are critical): the row in the runbook's §4 stage 1; the findings in `dev plans/web-design-suite-audit-2026-10-28/py-b-studio-and-migration.md` and `py-e-email-tools-commands-release.md`. Copy the shared master over its ten copies before the push.
3. **P71** (default or theme, N65), **P72** (the schema reader, N66), **P73** (the scaffold, N67), each its own PR; stack only where files are shared.
4. Then stage 2 (P74 to P76), and on in the runbook's order.

## 5. Owner decisions still open

None of the runbook's twelve. Ask before: a paid eval run (P89, stage 5), the release tag (stage 5), a large download, anything in the portal.

## 6. Environment and tooling

Python 3.14 and `uv` for 3.9; Node 26; `tooling/main` pins Playwright 1.64.1, whose Chromium 156.0.8078.4 (`chromium_headless_shell-1248`) is installed; the desktop app's CLI is 2.1.309 (`CLAUDE.md`'s Commands). Traps: `python -B`; the Bash tool unescapes `\\` in heredocs (write Python with backslashes with the Edit or Write tool); run tests from `tests/`; a change under `tooling/` makes `check.py` run the whole suite (23 minutes); `--base BRANCH` for a stacked PR; `TaskStop` a hung run.

## 7. Evidence, memory, promotion candidates

The audit's pass files (above); the memory index at `C:\Users\vybec\.claude\projects\C--DEV-Pro-Web-Designer-Suite-Plug-in\memory\MEMORY.md`. For `knowledge/`: a test that reads its own module's source contaminates a substring selector (`CheckCoversEveryFile` leaves `test_tools` out); `x or ["all"]` reads an empty list as everything, so tell `None` from `[]`.

## 8. End of session

Rewrite `docs/HANDOFF.md` and this file; update `CLAUDE.md`'s Current state, the runbook's §7 and `dev plans/README.md`; run the checker; commit the docs in their own PR and merge it; give the owner the chip and the printed prompt.
