# Handoff

**2026-09-30**, at the end of the session that answered PR #4's reviews, rescued the review's repro inputs and fixed SB-A9.

## State

- **3.2.1 is released** (`v3.2.1`, `63932cf`) and installed from it, in the local marketplace and in the cache that sessions load. 3.3.0 is in progress and unreleased.
- **PR #4, Python 3.9 (N6)**, merged as `8ccf8bb` after CodeRabbit's five points were answered and its threads resolved:
  - `check_pointers.py --write-register` and `sync_snippets.py` are tested writing a file, UTF-8 and LF byte for byte. The tests load the plugin under test's tools, so `WDS_PLUGIN_ROOT` at 3.2.1 errors twice on 3.9.
  - The plan and CLAUDE.md give `uv run --no-project --python <version> python -B -m unittest discover -s tests`, which runs the same in cmd, PowerShell and Git Bash.
  - CLAUDE.md's snapshot is dated 2026-09-30.
  - Codex did not review this PR.
- **PR #5, SB-A9 and N11**, merged with a merge commit at the user's request. It fixes the audit's three false cleans: `//` inside `url()`, a rule after a closed `@layer`, and a root-level `components/`. It also aligns the migration tool's file classes.
  - CodeRabbit's five points on it are answered in its last commit: the test counts, this file's `tar` warning, a plural-only token-file pattern (the spec's globs never matched `brand-token.css`), and `\)` inside an unquoted `url()`.
  - That commit was merged before CodeRabbit re-reviewed it.
  - 350 tests pass on 3.14.5 and 3.9.25; against 3.2.1 seven tests fail.
- **A decision made in PR #5:** a `@keyframes` block outside a layer is not unlayered CSS. The references and the scaffold write keyframes that way, and 3.2.1 flagged a keyframes-only file. If a reviewer disagrees, it is one condition in `audit_css`.
- **The review's repro inputs are rescued but not committed.** They are in `dev plans/web-design-suite-review/fixtures/`, untracked: 373 files, 3 MB, out of the 190 MB `%TEMP%` folder, which can now go.
  - Left out: plugin and skill copies, `.git`, `node_modules`, build output, a browser profile, binaries, files over 500 KB, and generated JSON naming this machine.
  - The scan found no secrets. Five probe scripts name local paths: `delivery/dark_all.cjs`, `dark_cta.cjs` and `ganga.cjs` load Playwright from `C:/DEV/audio-promptmonster/…`, and `persuasion/sizes.py` and `studio-build/snippet_audit.py` read the installed plugin.

## Next steps

1. **Read CodeRabbit's review of PR #5's last commit**, which arrives after the merge, and fold anything right into the next PR. No release until phase 3 is in.
2. **The fixtures**, once the user decides: commit as they are, drop or redact the five scripts first, or keep the folder local only. Stage them by path; never `git add -A`.
3. **Phase 3, as small PRs:**
   - N12: the migration tool's `extract_literals.blank_css_comments` has SB-A9's `//` bug.
   - SB-A24: in SCSS, a `@mixin`-only partial is flagged unlayered, and `$card-padding: 24px` passes. It changes what the gate accepts, so it starts in `design-rules.json`.
   - Then W1 (Supabase; the facts are in `dev plans/w1-supabase-facts.md`), the rest of W2, W3 and W4.
   - Release 3.3.0 when the phase is in.
4. **Fold the PR-by-PR sequencing into the plan**, as the user asked for a plan covering every open issue. CLAUDE.md's active-work line has the current order.

## Blockers

- The fixtures need the user's decision (step 2).

## Warnings

- **Cost.** The user caps a session at 500 thousand tokens. This one used about 350 thousand, counting only new context. Keep a session to one or two PRs, report token use as you go, and do not fan out to subagents or run max-effort reviews unless asked.
- **Fail-before from Git Bash.** `tar -x -C` with a Windows-form path (`C:\Users\…`) failed with "Cannot open", and a POSIX path from `cygpath -u` worked. `WDS_PLUGIN_ROOT` takes a Windows path (`cygpath -w`). In cmd, CLAUDE.md's commands apply as written.
- **Don't edit the plugin while the suite runs.** Every test spawns the scripts afresh, so a mid-run edit mixes versions. Stop the run and start again.
- **The installed plugin is a copy, and sessions load a cache of it.** Update both after every release.
- **Worktrees.** Never run `npm ci` in a worktree whose `tooling/*/node_modules` is a junction; remove junctions with `os.rmdir` before `git worktree remove`.
- **Don't trust the review's ✔ marks.** Use the inventory.
- **The repository is public** (since 2026-09-28, MIT). Commit nothing private: no secrets, and nothing from the user's other work. Its history already names paths on this machine and two other projects; the user chose to leave that as it is (decision 1).
