# Start here: the next session

**Written 2026-10-28**, at the end of the audit session. It points at files; it restates nothing.

## 1. What this is

**pro-web-design-suite**, a Claude Code plugin of 13 skills, in `C:\DEV\Pro-Web-Designer-Suite-Plug-in` (public, MIT; the plugin at `plugins/pro-web-design-suite`; releases go to `Vybecode-LTD/pro-web-design-suite` through `release.yml` only). `CLAUDE.md` is the map and loads by itself.

## 2. Rules that override the defaults

`CLAUDE.md`'s Gotchas and Conventions bind. Beyond them: one session at a time, in this checkout, no subagents or worktrees unless the owner asks; up to 750K tokens with no compacting, usage reported after each PR, the handoff written well before the cap; Claude merges on CI green, threads resolved, GitHub clean, with a merge commit (CodeRabbit is not a gate); push once when the work is done; every fix gets a test seen failing on `v4.0.1` through `tools/fail_before.py`; a gate change goes into `design-rules.json` first. **Never:** act in the directory portal (only the owner submits, publishes, withdraws or presses a button there); commit to the distribution repository by hand; grep `tooling/`; write into OneDrive; "fix" the four old ids; run a paid eval without the owner's OK. The full rule list with its sources is in the runbook's §5 and in `next-session-prompt-2026-10-27-full.md` §0 (kept until P69 folds it into `CLAUDE.md` and `docs/FACTS.md`).

## 3. The state, verified 2026-10-28

`docs/HANDOFF.md` has it. In short: `main` at `8441ff0`, **red** on macOS 3.14 in `test_runtime_urls.EachPageHasItsTypesBudget`; PR #215 (this session's docs) open or merged; `v4.0.1` the latest tag, the distribution repository at `4809e3f`; 4.0.1 in the directory's review and installed at user scope on the owner's machine (3.6.0 removed); `check_execution_plan.py` 0 open, 0 scheduled; next free ids N60, P66, PR #216. Check it:

```bash
cd /c/DEV/Pro-Web-Designer-Suite-Plug-in && git fetch -q && git status --short && git log --oneline -3 origin/main && gh pr list --state open && gh run list --branch main --limit 1 && python -B "dev plans/check_execution_plan.py"
```

## 4. The work, in order

**Read `dev plans/web-design-suite-completion-runbook.md`: §1 (what done means), §2 (the decisions), §3 (the owner's steps), §4 (the packages).** Then:

1. Ask the owner the twelve decisions in §2 and record the answers in §7. Ask for the four GitHub settings in §3 (items 1 to 4).
2. Add the packages' rows: N60 to N83 in the completion plan, P66 to P89 in the execution plan; `check_execution_plan.py` must pass.
3. Do **P66** (`main` green, the timing tests honest), then **P67**, **P68**, **P69**, each by the runbook's §5 protocol, each its own PR. Stage 0 is first because nothing after it is trustworthy without the ruleset, the release gate and an honest fail-before table.
4. Then stage 1 (P70 to P73: the four critical findings and the theme-classification class). Stages 2 to 8 follow in the runbook's order.

The findings each package closes are in `dev plans/web-design-suite-audit-2026-10-28/` (one file per pass, with file, line, evidence and fix); the summary is `web-design-suite-audit-2026-10-28.md`.

## 5. Owner decisions still open

The runbook's Q1 to Q12. Ask; do not decide. Q1 (one release or two) and Q7 (split the full prompt) change the order.

## 6. Environment and tooling

Python 3.14 and `uv` for 3.9; Node 26; the pinned tools in `tooling/` (`npm ci --prefix tooling/main` once); the desktop app's CLI at `C:\Users\vybec\AppData\Local\Claude-Data\claude_pzs8sxrjxfjjc\claude-code\2.1.308\c17a819afb40\claude.exe`. Traps: `python -B`; the Bash tool unescapes `\\` in heredocs (write Python with the Edit tool); look at the CPU before a long `check.py`; stop a hung run with `TaskStop`; the four timing flakes in the handoff's Warnings until P66.

## 7. Evidence and memory

The audit's pass files (above); the static-analysis outputs were in the session scratchpad (regenerate with ruff 0.6.9, pylint 4.0.5, ESLint 10 if needed); the memory index at `C:\Users\vybec\.claude\projects\C--DEV-Pro-Web-Designer-Suite-Plug-in\memory\MEMORY.md`.

## 8. Promotion candidates for `knowledge/`

The runbook's Q11 names three memory notes to promote. From this session: (1) a parallel read-only audit by area, each pass writing its own findings file in `dev plans`, with a digest script to rank them; (2) `python -I` ignores `PYTHONIOENCODING`, so use `-X utf8` for non-ASCII output; (3) the desktop app's CLI moved to `AppData\Local\Claude-Data`.

## 9. End of session

Rewrite `docs/HANDOFF.md` and this file; update `CLAUDE.md`'s Current state, the runbook's §7 and `dev plans/README.md`; run the checker; commit the docs in their own PR and merge it; give the owner the chip and the printed prompt.
