# Start here: the next session

**Written 2026-10-29.** It points at files; it restates nothing.

## 1. What this is

**pro-web-design-suite**, a Claude Code plugin of 13 skills, in `C:\DEV\Pro-Web-Designer-Suite-Plug-in` (public, MIT; the plugin at `plugins/pro-web-design-suite`; releases go to `Vybecode-LTD/pro-web-design-suite` through `release.yml` only). `CLAUDE.md` is the map and loads by itself; its Working rules and `docs/FACTS.md` hold the lessons.

## 2. Rules that override the defaults

`CLAUDE.md`'s Gotchas, Conventions and Working rules bind, and so does the runbook's §5 protocol. One session, in this checkout; up to 750K tokens, no compacting; report usage after each PR. **Never:** act in the directory portal; commit to the distribution repository by hand; grep `tooling/`; write into OneDrive; "fix" the four old ids; run a paid eval without the owner's OK; delete a repository.

## 3. The state, verified 2026-10-29

`docs/HANDOFF.md` has it. In short:

- `main` is the merge of #228 (this session's docs), on #226's merge `dbbe72a` (P71) and #225's `0a72ded` (P70).
- **#227 (P72) is open**, at head `3ac0ba9`, with its CI running at the end of the session.
- The owner's four GitHub settings are **not done**.
- `check_execution_plan.py`: 18 open. Next free ids: N84, P90, PR #229.

Check it:

```bash
cd /c/DEV/Pro-Web-Designer-Suite-Plug-in && git fetch -q && git status --short && git log --oneline -3 origin/main && gh pr list --state open && gh pr checks 227 && python -B "dev plans/check_execution_plan.py"
```

## 4. The work, in order

Read `dev plans/web-design-suite-completion-runbook.md` §4 (the packages) and §5 (the protocol); §7 has the ticks.

1. **#227:** bind it in the app (`get_status`, `bind_pr`), turn Auto-fix on, and read its CI. Read every CodeRabbit and Codex thread. Fix each real finding with a test that fails on the reviewed head (`fail_before.py --rev SHA`), answer and resolve each thread, and merge with `--match-head-commit`. Then tick P72 in §7, N66 in the completion plan and the P72 row in the execution plan (`P72, #227`).
2. **P73, the scaffold** (N67): the row in §4 stage 1. The findings are in `dev plans/web-design-suite-audit-2026-10-28/py-a-content-model-and-shared.md`. Also delete `NATIVE_CONTROLS` and `TS_KEYWORDS` from `scaffold_ui.py`, the half of PY-A-15 that P72 left. Branch from `main`.
3. Then stage 2 (P74 to P76), and on in the runbook's order.

## 5. Owner decisions still open

None of the runbook's twelve. Ask before: a paid eval run (P89, stage 5), the release tag (stage 5), a large download, anything in the portal.

## 6. Environment and tooling

- Python 3.14, with `uv` for 3.9; Node 26.
- `tooling/main` pins Playwright 1.64.1, whose Chromium is installed.
- The desktop app's CLI is 2.1.309 (`CLAUDE.md`'s Commands).

Traps:

- Use `python -B`.
- The Bash heredoc unescapes `\\`, which broke three edits last session: use the Edit tool for any Python with backslashes.
- A change under `shared/` runs the whole suite through `check.py`: 25 to 65 minutes, depending on what else the machine runs. Run it in the background, and never edit while it runs.
- Use `--base BRANCH` for a stacked PR.
- Two PRs that both add CHANGELOG entries conflict when the second merges: keep both.

## 7. Evidence, memory, promotion candidates

The audit's pass files (above); the memory index at `C:\Users\vybec\.claude\projects\C--DEV-Pro-Web-Designer-Suite-Plug-in\memory\MEMORY.md`. Candidates for `knowledge/`:

- An overwrite guard compares every key a path has, its identity and its resolved path: on POSIX, `stat("new/../x")` fails while `new` is missing.
- Never compare outputs pairwise: 400 outputs timed out.
- A test module's new module-level fixture can shadow an older test's global of the same name.

## 8. End of session

Rewrite `docs/HANDOFF.md` and this file. Update `CLAUDE.md`'s Current state, the runbook's §7 and `dev plans/README.md`, and run the checker. Commit the docs in their own PR and merge it. Give the owner the chip and the printed prompt.
