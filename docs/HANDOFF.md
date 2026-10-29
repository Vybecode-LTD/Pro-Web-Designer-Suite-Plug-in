# Handoff

**2026-10-28 (second session): stage 0 of the completion runbook is done.** P68 (#222) and P69 (#223) merged; this PR, #224, is the session's docs.
- **P68, #222, the maintainer tools:** `check.py` selects by a folder map (every plugin file now selects a test; 93 selected none); `fail_before.py` counts errors apart (an errors column, each failure's first line, `fixed?`); the evidence register fails an entry past 90 days and holds the pinned Playwright and axe-core; three weak tests strengthened, four `__main__` guards; the pins bumped with Dependabot's #218 to #220, less jsdom 30 and TypeScript 7, which `dependabot.yml` now ignores. **Shipped:** the install gate pins Playwright 1.64.1; a11y-audit-runner's scripts lock axe-core 4.14.0, which runs `label-content-name-mismatch` (2.5.3) by default. CodeRabbit's five findings fixed or answered.
- **P69, #223, the plans and the CLI path:** the 125 KB prompt split into `CLAUDE.md`'s Working rules and `docs/FACTS.md`; `test_mcp.find_claude()` finds the desktop app's CLI again (the strict validation runs locally on 2.1.309); the 19 stale plan statements; the plan checker reads an escaped pipe (265 rows).

## State

- **`main` = #224's merge** once it lands, on #223's merge `e8a46a6` (#222's: `eafa224`). CI passed on all seven legs of #222's and #223's heads; `main`'s run on `e8a46a6` was in progress at the end.
- **No PR open** but this one. Dependabot's #218 and #220 closed themselves once `main` held their updates; #219 was closed by hand, pointing at #222.
- **Released:** `v4.0.1` on `84f4a4f`; the distribution repository at `4809e3f`. On `main`, unreleased, for 4.1.0: P60 to P69.
- **The directory:** 4.0.1 submitted 2026-10-26; no reviewer's answer at the last read (not read this session).
- **The owner's install:** 4.0.1, user scope.
- **The plans:** `check_execution_plan.py` 20 open, 20 scheduled. Next free ids: **N84, P90, PR #225**.

## Next steps

1. **Stage 1, P70 to P73** (the runbook's §4): P70, one overwrite guard per script (two critical findings, PY-B-1 and PY-E-1), then P71 (default or theme), P72 (the schema reader), P73 (the scaffold).
2. Then stage 2 (P74 to P76), and on in the runbook's order.

## Open owner steps

- **The four GitHub settings** (the runbook's §3, items 1 to 4), **still not done on 2026-10-28** (checked with `gh api`): no ruleset on either repository; secret scanning, push protection and Dependabot security updates off on both; private vulnerability reporting off on the distribution one; no topics on either; the development repository has no description or homepage; Issues and Wiki on in the distribution one (Q4: off).
- **Delete `Vybecode-LTD/wds-gate-scratch`** (Q12), the owner's own step.

## Warnings

- **An evidence entry older than 90 days fails `test_evidence`** from 2026-12-25 (the twelve checked 2026-09-25 go first): re-read each at its URL, then move its quote and date.
- **A Playwright or axe-core bump in `tooling/main`** fails until `evidence.json` registers the new version and `automation-coverage.md`'s axe sentence is re-read (`test_facts.AxeTagAdvice` names the minor version).
- **`check.py` now runs more per change** (the folder map adds the directory's checks to every shipped file); a change under `tooling/` still runs the whole suite (23 minutes here).
- **A tag needs CI green on its commit** (`release.yml`'s gate); a skip over a leg's ceiling fails it (`tools/skip_ceiling.py`).
- **Budget:** this session used roughly 520K by its own estimate of its 750K (no counter was visible to the agent).
- **Standing:** never grep `tooling/`; the repository is public; nobody commits to the distribution repository by hand; nobody but the owner acts in the directory portal; the four old ids stay; `python -B`.
