---
name: install-gate
description: Put the design, accessibility and performance gates into this project and write the CI workflow that runs them on every push.
disable-model-invocation: true
argument-hint: "[--dest scripts] [--src src] [--dist dist] [--build \"npm run build\"]"
allowed-tools:
  - Bash(python "${CLAUDE_SKILL_DIR}/scripts/install_gate.py" *)
  - Bash(python3 "${CLAUDE_SKILL_DIR}/scripts/install_gate.py" *)
---

# Install the gates

Vendor the suite's gate scripts into the user's project and write the GitHub Actions workflow that runs them. Run it from the project's root. First show what it would write:

```bash
python "${CLAUDE_SKILL_DIR}/scripts/install_gate.py" --dry-run $ARGUMENTS
```

Use `python3` where `python` is not Python 3 (macOS). Ask the user before running it again without `--dry-run`. Then:

```bash
python "${CLAUDE_SKILL_DIR}/scripts/install_gate.py" $ARGUMENTS
```

What it writes:
- **`scripts/`** (`--dest`): the gate scripts, as every CI recipe and the pre-commit hook in the suite expect them (`python -m scripts.audit_design`). A clean checkout then has every script CI runs, with no plugin installed and no `PYTHONPATH`. `scripts/design-gates.json` lists each file with its SHA-256 and the plugin's version.
- **`.github/workflows/design-gates.yml`:** three jobs.
  - `gates`: the three gates on Linux, in the Playwright image built for the project's own `playwright`, so the browser is the one the lockfile expects. It builds, serves the build, waits for it, and uploads the browser gates' reports.
  - `windows`: the static gates on a Windows runner.
  - `baselines`: run by hand with `update-baselines` ticked. It records each gate's baseline where the gates run, and uploads them to review and commit.

It takes the baselines' paths from `.design-suite.json`. It never overwrites a file it did not write, or one changed since it wrote it, unless `--force`: tell the user which files are in the way and let them decide. It refuses a `playwright` version range in `package.json`, since the image's browsers fit one version.

It refuses a path with a space or a shell character, since the workflow runs each one unquoted. Then tell the user what was written, and the next steps the command printed: the exact `npm i -D -E` line for any package the browser gates need that `package.json` does not list (`playwright`, `axe-core`, `serve`, `wait-on`), committing both, and the first baseline run. Running it again upgrades the scripts and the workflow to this plugin's version.
