---
name: critique
description: Get an adversarial design critique from the design critic, a subagent with no stake in the build, then the ranked report and the tickets.
disable-model-invocation: true
argument-hint: "[paths | URL | built page] [the page's goal]"
allowed-tools:
  - Bash(python "${CLAUDE_PLUGIN_ROOT}/skills/design-critique-gate/scripts/critique_report.py" *)
  - Bash(python3 "${CLAUDE_PLUGIN_ROOT}/skills/design-critique-gate/scripts/critique_report.py" *)
---

# Critique

Have the work critiqued by someone who did not make it, from the project's root.

1. **Delegate** to the `web-design-suite:design-critic` agent. Its task is the target in `$ARGUMENTS` (paths, a URL or a built page; without one, ask) and, when the user gave them, the page's goal and audience. **Pass nothing else**: not your view of the work, not what was built in this session or why. The critic works in a fresh context so that the builder's familiarity does not come with it.
2. **Save** the JSON block it returns, exactly as it is, to `design-reports/critique/findings.json`. Do not edit, drop, soften or re-rank a finding. If it returned no JSON block, say so and stop.
3. **Report** it: the ranked critique, then one line per finding for a tracker.
   ```bash
   python "${CLAUDE_PLUGIN_ROOT}/skills/design-critique-gate/scripts/critique_report.py" design-reports/critique/findings.json
   python "${CLAUDE_PLUGIN_ROOT}/skills/design-critique-gate/scripts/critique_report.py" design-reports/critique/findings.json --format triage
   ```
   Use `python3` where `python` is not Python 3 (macOS).

Then tell the user:
- the top three, and every blocking finding, with its evidence and fix;
- which findings are taste, labelled as taste: the user decides those, not the critic;
- that `/web-design-suite:deck` takes this file (`--findings design-reports/critique/findings.json`) and stops on a blocking finding.

Fix nothing unless the user asks. A finding the user disagrees with is answered in the decision log, not deleted from the findings.
