# Handoff

**2026-10-03**, after PRs #16 to #21 were merged into `main`. Nothing is open.

**The next session starts from `dev plans/next-session-prompt.md`.** It has the orientation, then P3 part 2 (SB-A15 and N31) in detail.

## State

- **3.2.1 is released** (`v3.2.1`, `63932cf`) and installed. 3.3.0 is in progress on `main`, unreleased.
- **Merged on 2026-10-03,** in order, each as a merge commit with CI green on its head, every review thread resolved, and GitHub reporting it clean:
  - #16, P0: what the reviews of #12 to #15 found (N16 to N25, N29);
  - #17, P1: CI on three platforms, the release build, `fail_before.py`, `check.py`, N5;
  - #18 and #19, P2: the spec writes its data into the gates, value allowlists included, and every example in it runs through the audit, stylelint and ESLint (N2, SB-C2);
  - #20, P3 part 1: the three gates agree on every example (N1, N30), and the mega-menu flake is fixed;
  - #21: every skill description is 200 characters or fewer (the user's call).
- **The last reviews** found six more real bugs, all fixed; five have a test that fails before, and the sixth was the header recipe's missing rule, a docs fix:
  - From Codex on #20: the factor check read `var()` fallbacks; half an owl (`.card + *`) was the owl; stylelint missed the owl inside `@media`; and the header recipe lost the page's reservation.
  - From Codex on #19: `sync_rules.py` emitted a new shape by name but never declared it. Both gates' blocks now write every shape.
  - From CodeRabbit on #20: an inline literal's baseline key could hide a new literal further along the line.
- **Tests:** 438. **The plan:** 149 open items, all scheduled (`check_execution_plan.py`).
- **The user's rule since 2026-10-03:** Claude merges, without asking, once a PR is ready, and never in a way that breaks other pending work (the prompt's §0 has the procedure).

## Next steps

1. **The next session:** read `main`'s latest CI run, then P3 part 2: SB-A15 (the stylelint allowlist's holes) and N31, as the prompt describes. Then P4.
2. **3.3.0** ships after P8 (release R1).

## Warnings

- **Never `gh pr merge --delete-branch` on a branch another PR targets.** It closed #17 during these merges; #17 was restored by pushing its base back, `gh pr reopen` and `gh pr edit --base main`. Merge, retarget the next PR, then delete the branch.
- **Another session acted on the same PRs.** While the stack was being merged, a commit from another Claude session (`88ca21f`, retries for the mega-menu test) landed on #17's branch, most likely through Auto-fix. CI covered it, and it fits #20's fix, but one session per set of PRs is safer: turn Auto-fix off in a session that is done.
- **Browser tests and the fake clock.** `page.clock.install()` lets time flow in real time until `pauseAt()`. Pause after load, and wait until the page has seen an event before advancing the clock.
- **A stricter audit reaches the references.** `test_doc_snippets` audits every CSS block in them; a new check needs the references fixed in the same PR, or the block placed in its layer.
- **Bash heredocs eat backslashes.** Write anything with a backslash with the Write or Edit tool, or put it in a script file.
- **The repository is public.** Commit nothing private.
