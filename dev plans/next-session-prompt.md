# Start here: the next session

**Written 2026-10-28.** It points at files; it restates nothing.

## 1. What this is

**pro-web-design-suite**, a Claude Code plugin of 13 skills, in `C:\DEV\Pro-Web-Designer-Suite-Plug-in` (public, MIT; the plugin at `plugins/pro-web-design-suite`; releases go to `Vybecode-LTD/pro-web-design-suite` through `release.yml` only). `CLAUDE.md` is the map and loads by itself.

## 2. Rules that override the defaults

`CLAUDE.md`'s Gotchas and Conventions bind, and the runbook's §5 protocol. One session, this checkout, no subagents or worktrees unless asked; up to 750K tokens, no compacting, usage reported after each PR; Claude merges on CI green, threads resolved, GitHub clean, with a merge commit (CodeRabbit is not a gate); push once; every fix gets a test seen failing on `v4.0.1` (`tools/fail_before.py`); a test that needs a browser skips through `wds_support.no_browser`. **Never:** act in the directory portal; commit to the distribution repository by hand; grep `tooling/`; write into OneDrive; "fix" the four old ids; run a paid eval without the owner's OK; delete a repository.

## 3. The state, verified 2026-10-28

`docs/HANDOFF.md` has it. In short: `main` at `e6c214c` (#217); #221 (this session's docs) open or merged; P66 (#216) and P67 (#217) done; Dependabot's #218 to #220 open, to fold into P68; the owner's twelve decisions in the runbook's §7 (one release, 4.1.0); the owner's four GitHub settings **not yet done**; `check_execution_plan.py` 22 open; next free ids N84, P90, PR #222. Check it:

```bash
cd /c/DEV/Pro-Web-Designer-Suite-Plug-in && git fetch -q && git status --short && git log --oneline -3 origin/main && gh pr list --state open && gh run list --branch main --limit 2 && python -B "dev plans/check_execution_plan.py"
```

## 4. The work, in order

Read `dev plans/web-design-suite-completion-runbook.md` §4 (the packages) and §5 (the protocol); §7 has the answers and the ticks.

1. Check the owner's GitHub settings with the runbook's §6 ruleset command and `gh api repos/Vybecode-LTD/REPO` (`security_and_analysis`, `topics`); if not done, give the owner the steps (`docs/HANDOFF.md`, Open owner steps) and go on.
2. **P68, the maintainer tools**: the row in the runbook's §4 and N62 in the completion plan; the findings are in `dev plans/web-design-suite-audit-2026-10-28/test-suite.md` (TEST-2 to TEST-4, TEST-13 to TEST-19) and `ops-ci-release-evals-distribution.md` (OPS-7, OPS-8). Its own PR.
3. **P69, the plans and the CLI path** (N63; the PLAN findings in `plan-what-is-left.md`), splitting the 125 KB prompt per Q7.
4. Then stage 1 (P70 to P73), and on in the runbook's order.

## 5. Owner decisions still open

None of the runbook's twelve. Ask before: a paid eval run (P89, stage 5), the release tag (stage 5), a large download, anything in the portal.

## 6. Environment and tooling

Python 3.14 and `uv` for 3.9; Node 26; `tooling/main` has Playwright's Chromium 153.0.8010.12; the desktop app's CLI path is in `CLAUDE.md`. Traps: `python -B`; the Bash tool unescapes `\\` in heredocs and `sed` mangles backslashes (write Python and regexes with the Edit tool); `python -X utf8` for non-ASCII output; run tests from `tests/`; look at the CPU before a long `check.py`; `TaskStop` a hung run; `rm` only on literal paths.

## 7. Evidence, memory, promotion candidates

The audit's pass files (above); the memory index at `C:\Users\vybec\.claude\projects\C--DEV-Pro-Web-Designer-Suite-Plug-in\memory\MEMORY.md`. For `knowledge/`: CI job names that include a matrix make `step()` needles ambiguous once a second step shares a word, so a CI test anchors on an `id:` or a unique command; a GitHub concurrency group holds one pending run, so a group per commit is the only way never to drop a push run.

## 8. End of session

Rewrite `docs/HANDOFF.md` and this file; update `CLAUDE.md`'s Current state, the runbook's §7 and `dev plans/README.md`; run the checker; commit the docs in their own PR and merge it; give the owner the chip and the printed prompt.
