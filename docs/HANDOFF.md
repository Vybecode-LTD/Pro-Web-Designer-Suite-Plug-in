# Handoff

**2026-09-26**, at the end of the session that released 3.2.1, configured CodeRabbit and rebased the Python 3.9 floor.

## State

- **3.2.1 is released.** PR #1 merged as `63932cf`, tagged `v3.2.1`; the release notes (PR #2) merged as `02f9955`.
  - The zip is `Downloads\web-design-suite-plugin-3.2.1-63932cf.zip` (227 entries, SHA-256 `592c985f…`), identical to `git archive v3.2.1` under `diff -r`. The `web-design-suite-plugin-3.2.1.zip` beside it is the pre-review build from `8b27ff7`; the user can delete it.
  - Installed from `63932cf`, in the local marketplace and in the cache that sessions load. `plugin update` refreshes the cache only when the version changes (plan, release procedure, step 6).
- **`.coderabbit.yaml` (PR #3)** sets en-GB, the assertive profile and no poem, filters the lockfiles and the review fixtures, and restates CLAUDE.md's conventions as path instructions. It validates against CodeRabbit's schema.v2.json. CodeRabbit said it reads a changed config only from the target branch for this PR's author, so the config takes effect from `main` once merged, not from a PR's branch.
- **Python 3.9 (N6)** is the 3.9 PR, on `feat/python-3.9-floor`, rebased onto `main` (conflicts resolved by keeping both sides). 342 tests pass on 3.9 and 3.14. It also lowers `.coderabbit.yaml`'s floor to 3.9.
- **Reviewers.** Codex (`chatgpt-codex-connector`) reviews each PR as well as CodeRabbit; every point either raised this session was right. CodeRabbit is on the Teams trial until about 2026-10-02: 10 reviews an hour, and each reply to one of its threads costs one. Push fixes and let the incremental review mark threads addressed.

## Next steps

1. **The 3.9 PR.** Read CodeRabbit's and Codex's reviews, fix what is right (with tests), then merge with a merge commit. No release: 3.3.0 ships when phase 3 is in.
2. **Rescue the review's repro inputs** before Storage Sense deletes them: `%TEMP%/claude/C--DEV/5b1a5cc7-460d-4e95-848e-f823553c2172/scratchpad/review` (190 MB) into `dev plans/web-design-suite-review/fixtures/`. Without plugin copies, generated output, binaries and files over 500 KB it is 610 files, about 7 MB. Scan them for secrets first; `.coderabbit.yaml` already filters the folder out of reviews.
3. **Phase 3 as small PRs**, one item or a few each: W2's audit false-clean (SB-A9, `//` inside `url()`) first, then W1 (Supabase; the facts are in `dev plans/w1-supabase-facts.md`), W3 and W4 (N4, N5, N7–N10, XC-A2, XC-A5, XC-B5, XC-C9). Release 3.3.0 when the phase is in.
4. **Plan the rest.** The user asked for a plan covering every open issue. The completion plan covers them all, but not the PR-by-PR sequencing above: fold that and the progress into the plan and the inventory.

## Blockers

None.

## Warnings

- **Cost.** The user caps a session at 500 thousand tokens; this one used about 300 thousand, and an earlier one ran past 4 million. Keep a session to one or two PRs, report token use as you go, and do not fan out to subagents or run max-effort reviews unless asked.
- **The installed plugin is a copy, and sessions load a cache of it.** Update both after every release.
- **Worktrees.** Never run `npm ci` in a worktree whose `tooling/*/node_modules` is a junction; remove junctions with `os.rmdir` before `git worktree remove`.
- **Don't trust the review's ✔ marks.** Use the inventory.
- **Private material.** This repository's own `dev plans/` names paths on this machine and two other projects (`audio-promptmonster`, `Basefra.me`). It matters only if the repository goes public; settle decision 1 first.
