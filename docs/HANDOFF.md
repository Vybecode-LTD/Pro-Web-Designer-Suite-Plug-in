# Handoff

**2026-10-28: the owner's twelve decisions, the packages' rows, and stage 0's first two packages.**
- The owner answered the runbook's Q1 to Q12 (asked in its §2, the answers recorded in its §7): **one release, 4.1.0, absorbing 4.0.2**; Phase 7 after done; issues in the development repository; Q10's two 3.5.0 command notes itemised into P88; Q11's notes promoted to `C:\DEV\knowledge` (`e2899aa`).
- The 24 packages have their rows: N60 to N83 in the completion plan, P66 to P89 in the execution plan.
- **P66, #216:** `measure_vitals.mjs` waits up to 5 s past its settle for a first LCP; the timing tests judge each run against its own page clock; CI keeps the measured numbers from a red leg. **The audit misread the macOS failure:** it was a missing LCP, not a breach (N60 has the evidence: eight macOS reds, one cause).
- **P67, #217:** a `v*` tag releases only a commit CI passed on (`tooling/release/ci_gate.py`); `main`'s runs are never cancelled or replaced; every action is pinned and Dependabot moves the pins; the CLI is pinned at 2.1.312; every leg tests Playwright's Chromium (153.0.8010.12) and fails a test that finds no browser; a skip ceiling per leg.

## State

- **`main` at `e6c214c`** (#217's merge); its CI was running at the end. #216's merge (`9c1a528`) passed on all seven legs, and so did #217's head (`6c1031f`).
- **Dependabot's first PRs, opened on #217's merge:** #218 (`tooling/tailwind-v3`, 2 updates), #219 (`setup-uv` 10.2.0 to 10.3.2), #220 (`tooling/main`, 8 updates). P68 bumps those pins anyway: fold them into it (with the test pins that name the versions), and Dependabot closes each once `main` has them.
- **This PR, #221,** `docs/handoff-2026-10-28-p66-p67`: this handoff, the starting prompts, `CLAUDE.md`'s Current state, the runbook's §7 ticks, `dev plans/README.md`.
- **Released:** `v4.0.1` on `84f4a4f`; the distribution repository at `4809e3f`. On `main`, unreleased, for 4.1.0: P60 to P67.
- **The directory:** 4.0.1 submitted 2026-10-26; no reviewer's answer at the last read.
- **The owner's install:** 4.0.1, user scope.
- **The plans:** `check_execution_plan.py` 22 open, 22 scheduled. Next free ids: **N84, P90, PR #222**.

## Next steps

1. **P68, the maintainer tools** (the runbook's §4 stage 0): `check.py`'s folder map (Q8: yes), `fail_before.py`'s errors column, `evidence.json`'s age test, the three weak tests, the `__main__` guards, the pin bumps.
2. **P69, the plans and the CLI path:** the full prompt split per Q7 (`docs/FACTS.md`), one state, `find_claude()`.
3. Then stage 1 (P70 to P73, the four critical findings), and on in the runbook's order.

## Open owner steps

- **The four GitHub settings** (the runbook's §3, items 1 to 4): the ruleset on `main` (a PR and the seven checks required, no force-push or deletion), secret scanning, Dependabot security updates and private vulnerability reporting on both repositories, the distribution repository's Issues and Wiki off and its deploy-key-only ruleset, the topics and About. Not done at the end of this session; verify with the runbook's §6 commands before asking again.
- **Delete `Vybecode-LTD/wds-gate-scratch`** (Q12): the owner asked the agent to; the agent declined, since a permanent deletion is the owner's.

## Warnings

- **A tag now needs CI green on its commit.** Pushed before CI finishes, `release.yml` fails at "CI passed on the tagged commit"; rerun that job once CI is green.
- **A new skip in CI can cross a ceiling** (`tools/skip_ceiling.py`; Linux 7, Windows 20, macOS 16): raise the ceiling in `ci.yml` on purpose, with the reason.
- **A test that needs a browser calls `wds_support.no_browser(self, why)`**, never `self.skipTest`: `test_harness.NoBrowser` fails on a bare skip after a no-browser check.
- **Dependabot opens PRs** (actions weekly, `tooling/` monthly). Fold them into a feature PR, never merge one alone; a bump that breaks a test pin is fixed there. They take PR numbers: predict the next one from `gh pr list --state all --limit 1`.
- **Eight SKILL.md files are within 20 bytes of the 20,500-byte cap** (P86 and P87 name the cuts).
- **Budget:** this session used about 560K tokens of its 750K. Before a long `check.py`, look at the CPU; stop a hung run with `TaskStop`.
- **Standing:** never grep `tooling/`; the repository is public; nobody commits to the distribution repository by hand; nobody but the owner acts in the directory portal; the four old ids stay; `python -B`.
