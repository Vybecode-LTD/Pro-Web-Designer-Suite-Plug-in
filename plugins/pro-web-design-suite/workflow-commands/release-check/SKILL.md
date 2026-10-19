---
name: release-check
description: Check a design-system release - extract the system, diff it against the published snapshot, gate unannounced removals, and write the changelog and the migration guide.
disable-model-invocation: true
argument-hint: "[paths] [--from-version X.Y.Z] [--published FILE] [--deprecations FILE] [--project NAME]"
allowed-tools:
  - Bash(python "${CLAUDE_SKILL_DIR}/scripts/release_check.py" *)
  - Bash(python3 "${CLAUDE_SKILL_DIR}/scripts/release_check.py" *)
---

# Release check

Run design-system-versioning's release flow on the user's project, from its root:

```bash
python "${CLAUDE_SKILL_DIR}/scripts/release_check.py" $ARGUMENTS
```

Use `python3` where `python` is not Python 3 (macOS). When the user has not given `--from-version`, read the version the published snapshot shipped as from the project (its `package.json`, or the last release tag) and pass it, so the bump becomes a real version. The runner, in order:

1. **extract:** `extract_system.py` on the paths, else `src/`, to `design-reports/release/system.json`;
2. **diff:** `diff_system.py` from the published snapshot (`--published`, else `.design-suite.json`'s `baselines.system`) to that candidate: every change, its severity, and the bump;
3. **gate:** with a deprecation ledger (`--deprecations`, else `deprecations.json`), a name that vanished with no record stops the run here, exit 1. Without one the gate is advisory;
4. **changelog:** `design-reports/release/CHANGELOG.part.md`;
5. **guide:** `design-reports/release/UPGRADE.md`, only when a change is breaking.

It edits nothing in the project.

Then tell the user:
- the bump and the version, with the reason the diff gives, and each breaking change;
- a failed gate: each vanished name, and the fix, a deprecation before the removal (design-system-versioning's `deprecate.py add`) and a shim for one minor version. Nothing was written past the gate;
- an advisory gate: the names a ledger would have refused;
- where the changelog and the guide are. Offer to merge the changelog entry into the project's CHANGELOG; never edit it unasked.

Exit 2 means a step could not run. The common one is a project with no published snapshot: at its first release, snapshot the system (`extract_system.py src --out published/system.json`), commit it, and name it as `baselines.system` in `.design-suite.json`.
