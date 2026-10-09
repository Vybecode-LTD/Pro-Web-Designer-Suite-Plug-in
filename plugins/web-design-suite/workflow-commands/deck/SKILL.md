---
name: deck
description: Build the client deck from the evidence - audit, critique, defence sheet and deck in one run, stopping when a finding blocks the presentation.
disable-model-invocation: true
argument-hint: "DECISION_LOG.md --findings FILE [paths] [--audience client|team] [--dist DIR]"
allowed-tools:
  - Bash(python "${CLAUDE_SKILL_DIR}/scripts/deck.py" *)
  - Bash(python3 "${CLAUDE_SKILL_DIR}/scripts/deck.py" *)
---

# Deck

Run the persuasion chain on the user's project, from its root:

```bash
python "${CLAUDE_SKILL_DIR}/scripts/deck.py" $ARGUMENTS
```

Use `python3` where `python` is not Python 3 (macOS). It needs two inputs the user owns:
- **the decision log**, client-presentation-builder's `DECISION_LOG.md`: the decisions the deck argues. Without one, start from that skill's `assets/DECISION_LOG.md` with the user, before running this;
- **the critique's findings**, design-critique-gate's `findings.json` (`--findings`). Without one, run that skill's critique on the work first and save its findings, then run this.

The runner, in order:
1. **audit:** `audit_design.py --json` on the paths, or the project, and `perf_audit.py --json` on the build (`--dist`, else `dist/` or `build/`);
2. **critique:** `critique_report.py` on the findings, merged with the audit, `--fail-on blocking`. **A blocking finding stops it here**, exit 1, with no deck;
3. **defence:** the defence sheet, the open defects said out loud;
4. **deck:** `build_presentation.py` from the decision log, with the audits and the defence as evidence.

Everything goes in `design-reports/deck/`: `audit.json`, `perf.json`, `defence.md`, `deck.html` and `notes.md`.

Then tell the user:
- a stop: each blocking finding and its fix. It is fixed, or recorded in the decision log as a decision with its reason, before anyone presents it;
- a deck: where it and the notes are, and every warning `build_presentation.py` printed (a placeholder left, a decision with no evidence, no screenshots). Each is a slide that will not survive the room;
- what the deck may not say: a clean audit is the machine-checkable subset, never "accessible" or "compliant".

Exit 2 means a step could not run: report which, and why.
