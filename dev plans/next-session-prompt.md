# Start here: the next session

**Written 2026-10-30, at the close of 2026-10-29's third session.** It points at files; it restates nothing.

## 1. What this is

**pro-web-design-suite**, a Claude Code plugin of 13 skills, in `C:\DEV\Pro-Web-Designer-Suite-Plug-in` (public, MIT; the plugin at `plugins/pro-web-design-suite`; releases go to `Vybecode-LTD/pro-web-design-suite` through `release.yml` only). `CLAUDE.md` is the map and loads by itself; its Working rules and `docs/FACTS.md` hold the lessons.

## 2. Rules that override the defaults

`CLAUDE.md`'s Gotchas, Conventions and Working rules bind, and so does the runbook's §5 protocol. One session, in this checkout; up to 750K tokens, no compacting; report usage after each PR. **Never:** act in the directory portal; commit to the distribution repository by hand; grep `tooling/`; write into OneDrive; "fix" the four old ids; run a paid eval without the owner's OK; delete a repository.

## 3. The state, verified at the close

`docs/HANDOFF.md` has it. In short:

- `main` is the merge of #235 (this session's docs), on #234 (P76, `1bc2481`) and #232 (P75, `4453fa6`).
- **Open: none.** Stages 0 to 2 are done (P66 to P76); 1,804 tests.
- The owner's four GitHub settings are **not done**.
- `check_execution_plan.py`: 13 open, 13 scheduled. Next free ids: N84, P90, PR #236.

Check it:

```bash
cd /c/DEV/Pro-Web-Designer-Suite-Plug-in && git fetch -q && git status --short && git log --oneline -3 origin/main && gh pr list --state open && python -B "dev plans/check_execution_plan.py"
```

## 4. The work, in order

Read `dev plans/web-design-suite-completion-runbook.md` §4 (the packages) and §5 (the protocol); §7 has the ticks. Stages 0 to 2 are done (P66 to P76).

1. **Stage 3, P77 `a11y_static.py`** (N71): the row in §4 stage 3; the findings (PY-D-1 to PY-D-12) are in `dev plans/web-design-suite-audit-2026-10-28/py-d-gates-critique-deck-landing.md`. Branch from `main`; after `gh pr create`, bind it (`get_status`), turn Auto-fix on, expect Codex and CodeRabbit (`@coderabbitai review` if its limit skipped it), merge with `--match-head-commit`.
2. **P78** (N72), with `tw_probe.mjs:183` and `theme-init.js:14` (`docs/HANDOFF.md`), then **P79** (N73).

## 5. Owner decisions still open

None of the runbook's twelve. Ask before: a paid eval run (P89, stage 5), the release tag (stage 5), a large download (Firefox's pinned build, about 90 MB, to run the engine tests here), anything in the portal.

## 6. Environment and tooling

- Python 3.14, `uv` for 3.9; Node 26; Playwright 1.64.1's Chromium is installed, not its Firefox or WebKit (their tests run on CI's Linux leg); the desktop app's CLI is 2.1.309.

Traps:

- Use `python -B`. The Bash heredoc unescapes `\\` and trips on quotes: write patch scripts with the Write tool, run them from a file.
- A `tools/` or `shared/` change makes `check.py` run most of the suite (27 minutes): in the background, no edits meanwhile, then `check.py --base SHA`.
- A SKILL.md near 20,500 bytes: `docs/FACTS.md`'s byte table must be updated with it.
- A reviewer's claim about a library: read the pinned copy's code (one named file in `tooling/`, never a grep of it) before fixing.

## 7. Evidence, memory, promotion candidates

The audit's pass files (above); the memory index at `C:\Users\vybec\.claude\projects\C--DEV-Pro-Web-Designer-Suite-Plug-in\memory\MEMORY.md`. Candidates for `knowledge/`:

- Chromium with `isMobile` lays a page with no viewport meta out 980 px wide whatever the window: measure CSS-pixel criteria (WCAG 1.4.10) in a desktop context.
- Playwright's Firefox takes `isMobile` (1.64.1); "not supported in Firefox" is old documentation.
- A piped Node CLI exits through `process.stdout.write('', cb)`, not `process.exit()`, which drops a macOS pipe's queued writes.
- A browser stops reporting LCP at the first input: a run that clicks during load has no page LCP.

## 8. End of session

Rewrite `docs/HANDOFF.md` and this file. Update `CLAUDE.md`'s Current state, the runbook's §7 and `dev plans/README.md`, and run the checker. Commit the docs in their own PR and merge it. Give the owner the chip and the printed prompt.
