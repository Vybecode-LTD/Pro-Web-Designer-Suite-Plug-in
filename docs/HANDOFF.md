# Handoff

**2026-10-29: stage 1 of the completion runbook, three of its four packages, all merged.** P70 (#225), P71 (#226) and P72 (#227); P73 is not started.
- **P70, #225, one overwrite guard per script:** `guard_outputs(outputs, inputs)` in the shared master. Every Python writer calls it, and the three skills with no reader carry it verbatim. `test_out_guard.EveryWriteIsGuarded` ties each write in the shipped scripts to its function's guard call (`DECLARED` lists the rest with reasons; build_docs waits there for P82). It closes PY-B-1 and PY-E-1 (critical), PY-C-7 and PY-C-18, plus the same hole in nine scripts the audit did not name. Review: Codex's POSIX `new/../x` bypass (each path is now keyed by identity and by resolved path).
- **P71, #226, one answer to "default or theme":** `classify_rule()`, `class_themes()` and `nested()` in the shared master, and `classifyRule()` in `project_config.mjs`. The token reader, `figma_to_tokens`, `extract_system`, `diff_system` and `check_roles` all call it. It closes PY-C-1 (critical), PY-A-7, PY-C-4 and PY-B-7. Review fixes: `check_roles`' specificity, a root that leaves out dark, nested lists, and a gate that measured nothing exits 2.
- **P72, #227, the schema reader:** the ten PY-A findings, PY-A-1 critical. Review fixes: string literals kept as written, a call's parentheses kept across a space, inline constraint names, a dropped column's constraints, Prisma self-relations.

## State

- **`main` = this PR's merge**, on #227's merge `59096d8`.
- **No PR open.**
- **Released:** `v4.0.1`; P60 to P72 on `main` for 4.1.0.
- **The plans:** `check_execution_plan.py` 17 open, 17 scheduled. Next free ids: **N84, P90**; the next PR is #230 (this one is #229).

## Next steps

1. **P73, the scaffold** (N67: PY-A-6, PY-A-10, PY-A-11, PY-A-14, PY-A-16, PY-A-17), with the half of PY-A-15 P72 left in `scaffold_ui.py` (`NATIVE_CONTROLS`, `TS_KEYWORDS`). Branch from `main`.
2. Then stage 2 (P74 to P76).

## Open owner steps

- **The four GitHub settings** (the runbook's §3): **still not done on 2026-10-29**, checked with `gh api`. No ruleset on either repository; secret scanning, push protection and Dependabot security updates are off on both; private vulnerability reporting is off on the distribution one; neither has topics or a social preview; the development one has no description or homepage; Issues and Wiki are on in the distribution one.
- **Delete `Vybecode-LTD/wds-gate-scratch`** (Q12).

## Warnings

- **`check.py` is slow on a loaded machine.** A change under `shared/` runs the whole suite: 25 minutes alone, 65 with another project's dev server and mypy running. Look at the CPU first, and never edit a file the suite reads while it runs.
- **Codex and CodeRabbit review every push, and found real bugs in each PR:** budget a review round per PR. CodeRabbit's free tier ran out mid-session (one review an hour).
- **Two PRs that both add CHANGELOG entries conflict** when the second merges: keep both entries.
- **A test module's new global can shadow an older test's.** Grep the module before naming a fixture (`DARK_PAIR`, P71).
- **`guard_outputs` keys each path once, by identity and by resolved path.** Never compare outputs pairwise: a scaffold's 400 outputs timed out.
- **The Bash heredoc unescapes `\\`**, which broke three edits this session. Write Python with backslashes through the Edit tool.
- **Budget:** the session ran to about 750K by my own estimate (no counter was visible).
