# Start here: the next session

**Written 2026-10-29, at the second session's close.** It points at files; it restates nothing.

## 1. What this is

**pro-web-design-suite**, a Claude Code plugin of 13 skills, in `C:\DEV\Pro-Web-Designer-Suite-Plug-in` (public, MIT; the plugin at `plugins/pro-web-design-suite`; releases go to `Vybecode-LTD/pro-web-design-suite` through `release.yml` only). `CLAUDE.md` is the map and loads by itself; its Working rules and `docs/FACTS.md` hold the lessons.

## 2. Rules that override the defaults

`CLAUDE.md`'s Gotchas, Conventions and Working rules bind, and so does the runbook's §5 protocol. One session, in this checkout; up to 750K tokens, no compacting; report usage after each PR. **Never:** act in the directory portal; commit to the distribution repository by hand; grep `tooling/`; write into OneDrive; "fix" the four old ids; run a paid eval without the owner's OK; delete a repository.

## 3. The state, verified 2026-10-29

`docs/HANDOFF.md` has it. In short:

- `main` is the merge of #233 (this session's docs), on #231 (P74, `455d085`) and #230 (P73, `001de97`).
- **Open: #232 (P75)**, head `075a783`, with six CodeRabbit threads unanswered.
- The owner's four GitHub settings are **not done**.
- `check_execution_plan.py`: 15 open. Next free ids: N84, P90, PR #234.

Check it:

```bash
cd /c/DEV/Pro-Web-Designer-Suite-Plug-in && git fetch -q && git status --short && git log --oneline -3 origin/main && gh pr list --state open && python -B "dev plans/check_execution_plan.py"
```

## 4. The work, in order

Read `dev plans/web-design-suite-completion-runbook.md` §4 (the packages) and §5 (the protocol); §7 has the ticks.

1. **Finish #232 (P75):** `docs/HANDOFF.md` lists its six open CodeRabbit threads, each real. Fix each with a test failing on `d8a2414` (`fail_before.py --rev SHA`), reply, resolve, merge; tick P75 in the plans.
2. **P76, vitals, the matrix and the critique capture** (N70): the row in §4 stage 2; the findings are in `dev plans/web-design-suite-audit-2026-10-28/js-b-browser-scripts.md`. Branch from `main`; after `gh pr create`, bind the PR and turn Auto-fix on. Expect a Codex and CodeRabbit round; merge with `--match-head-commit`.
3. Then stage 3 (P77 to P79), in the runbook's order.

## 5. Owner decisions still open

None of the runbook's twelve. Ask before: a paid eval run (P89, stage 5), the release tag (stage 5), a large download, anything in the portal.

## 6. Environment and tooling

- Python 3.14, with `uv` for 3.9; Node 26; `tooling/main` pins Playwright 1.64.1, whose Chromium is installed; the desktop app's CLI is 2.1.309.

Traps:

- Use `python -B`. The Bash heredoc unescapes `\\`: use the Edit tool for anything with backslashes.
- A change to `tools/` or `shared/` runs the whole suite through `check.py` (about 32 minutes). Run it in the background, never edit while it runs, and after it passes use `check.py --base SHA` for later changes.
- A browser test of a wait gives the run 60 s (`TheGatesBoundTheirWaits.bounded`): a hang on the old tree is a FAIL.
- `scaffold_ui.py` is 1,239 bytes under the directory's 262,144-byte hold.
- A stacked PR: `--base BRANCH`, retarget to `main` after the lower one merges; CodeRabbit skips a PR whose base is not `main`.

## 7. Evidence, memory, promotion candidates

The audit's pass files (above); the 4.0.0 live check (L8's cause); the memory index at `C:\Users\vybec\.claude\projects\C--DEV-Pro-Web-Designer-Suite-Plug-in\memory\MEMORY.md`. Candidates for `knowledge/`:

- Playwright's `frame.addScriptTag` waits for ever in a lazy iframe that has no document yet: bound every per-frame call.
- `check.py`-style test selection must also run the tests that read every test module by glob.
- A JS wrapper around a page's timer callbacks must call them with `window` as `this`.

## 8. End of session

Rewrite `docs/HANDOFF.md` and this file. Update `CLAUDE.md`'s Current state, the runbook's §7 and `dev plans/README.md`, and run the checker. Commit the docs in their own PR and merge it. Give the owner the chip and the printed prompt.
