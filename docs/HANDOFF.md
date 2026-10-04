# Handoff

**2026-10-04**, after PRs #23 (2026-10-03) and #24 (2026-10-04) were merged into `main`.

**The next session starts from `dev plans/next-session-prompt.md`.** It has the orientation, then P5 (N3, the rest of SB-C9, and N32) in detail.

## State

- **3.2.1 is released** (`v3.2.1`, `63932cf`) and installed. 3.3.0 is in progress on `main`, unreleased.
- **Merged this session,** each as a merge commit, with CI green on its head, every review thread resolved, and GitHub reporting it clean:
  - #23, P3 part 2 (SB-A15, N31). Every hole in the stylelint allowlist is now examples in the spec, run through the audit and the real stylelint:
    - `design/no-literal-colour-function`;
    - the `stroke` family;
    - margins outside components;
    - the full sizing family;
    - the motion shorthands (`MOTION_LIST`);
    - theme bindings (`bindings`, `binding-literal`);
    - the audit-only `geometry`;
    - N31's zeros, shares and margins.

    The audit's spacing, stroke, motion and sizing checks read the spec's allowlists.
  - #24, P4 (SB-A11, SB-A25, SB-C10). It added the breakpoint diff (`breakpoint-drift`), `--files-from` and `--sarif`, and stopped `:where()` warning. Every other promise the docs made about the gates is corrected.
- **The reviews of #23 found six real issues in seven comments, all fixed.** The five bugs each have a test that fails on the head before the fix:
  - From Codex: a Sass value skipped the allowlists, so `padding: $space 13px` passed; and `EASE-IN` passed as a name.
  - From CodeRabbit:
    - `padding: $space 5%` passed;
    - `#{5%}` passed as a token;
    - `--aspect-video: currentColor` passed through the generic binding key;
    - N31's bullets read as pending (a docs fix).
  - Found while writing P4's tests: Tailwind's `--breakpoint-*: initial` was refused.
- **The reviews of #24 found eleven more, all fixed with tests:**
  - the breakpoint diff ran one way only;
  - a theme's ignore pragmas did not reach it;
  - a NUL-separated `--files-from` list was split on newlines too;
  - the SARIF run lacked `originalUriBaseIds`;
  - SARIF carried a fingerprint code scanning does not read. It now sets none, and `upload-sarif` computes one;
  - the diff read only the first declaration of each name, though the cascade keeps the last;
  - a generated theme was not skipped;
  - a Tailwind theme with no copies, or tokens with no breakpoints, dropped out of the diff. Counting them showed that themes split across files each lacked the other's names, so the themes paired with one token file now mirror it together;
  - a theme whose project had no token file in the run was paired with another project's;
  - a nested package's tokens were paired with its parent project's theme. A theme now pairs only with token files whose nearest `package.json` folder is its own;
  - `--files-from` read its list as UTF-8, so on Linux a file name that is not UTF-8 lost its bytes, and the file went unaudited. Its test runs on Linux only, since Windows and macOS file names are always Unicode.

  Two more comments came outside the diff:
  - the completion plan's W12 list still named SARIF as future work. It is now marked done.
  - the spec holds no selector-specificity limit. That predates #24, so it is N32, scheduled in P5.
- **Tests:** 458. **The plan:** 145 open items, all scheduled (`check_execution_plan.py`).

## Next steps

1. **The next session:** P5, the references' CSS through the real stylelint (N3), the Tailwind v3 entry (the rest of SB-C9), and the specificity limits in the spec (N32), as the prompt describes. Then P6.
2. **3.3.0** ships after P8 (release R1).

## Warnings

- **Stacked PRs.** #24 was stacked on #23. Merge bottom-up, retarget the next PR to `main`, then delete the merged branch. Never use `gh pr merge --delete-branch` on a branch another PR targets.
- **A review fix on a lower PR goes into that PR**, then merge its branch into the PR above it. Don't rewrite a pushed branch.
- **The theme files are token files to the audit**, which checks only their custom properties (`bindings`). stylelint's theme override checks the same set, and nothing else in them.
- **A stricter gate reaches the references, the starter, the scaffold and the deck.** `test_doc_snippets`, the starter's own runs, `ScaffoldAuditsClean` and `test_presentation` all audit generated or quoted CSS.
- **Bash heredocs eat backslashes.** Write anything with a backslash through the Write or Edit tool, or a script file.
- **Don't grep `tooling/`**: its `node_modules` makes the search run for minutes.
- **A Linux-only test runs under WSL** (Ubuntu, Python 3.14), with `WDS_PLUGIN_ROOT` set to an unpacked revision for the before run:
  - in cmd.exe, double-quote the script: `wsl -d Ubuntu --exec sh -c "cd /mnt/c/DEV && …"`;
  - in the Bash tool, single-quote it, or Git Bash expands each `$` first: `wsl.exe -d Ubuntu --exec sh -c 'cd /mnt/c/DEV && …'`.

  Use `--exec` either way. Without it, WSL's own shell expands each `$` before `sh` sees the script.
- **The repository is public.** Commit nothing private.
