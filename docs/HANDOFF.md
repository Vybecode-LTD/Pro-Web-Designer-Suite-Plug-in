# Handoff

**2026-10-15 (second session)**, after P53 parts 2 to 4 of Phase 6c, the owner's audit. **Next: P53's last class, the cmd.exe placeholders (the audit's D4, G13, E14), then P54, the mediums.** The owner placed all of Phase 6c (P50 to P55) before Phase 6b's remaining workstreams.

**The next session starts from `dev plans/next-session-prompt.md`**: orientation, then the work in detail. `dev plans/next-session-opening-prompt.md` is the message to paste in.

## State

- **#138, P53 part 2 (the JSON type guards: S1, S10, V8, G3, G11, G15, E13, W6; §7 class 6)**, merged as `4701883`:
  - Every loader checks a JSON file's shape where it reads it, and exits 2 naming the file and the key. `introspect_schema` exits 1, its documented code. A baseline of the wrong shape is read as an unreadable one, as before.
  - The token readers leave out a non-string `$type`, in Python and in Node. A `$deprecated` that is neither a string nor a boolean is named.
  - `perf_audit`'s `budget_problem()` is ported to `measure_vitals.mjs`; both refuse a non-finite limit, and a `null` in `bytes` or `lab` still lifts a default.
  - `test_json_guards` has a row per loader, and fails on a script that reads JSON with no row.
  - **Reviews:** 9 real findings over three rounds (CodeRabbit 5, Codex 4). The class was a value that is present but falsy (`[]`, `0`, `false`), which `or {}` read as empty, plus fields the readers index without checking.
- **#139, P53 part 3 (the encoding readers: S8, W7; class 4)**, merged as `551d918`:
  - `project_config.read_text()` and `decode_text()` follow `json.detect_encoding()`, so a UTF-16 `tokens.css` reads in Python and in Node.
  - Every script's project reads go through them, or through a local `_read_text()` in the four scripts that run on their own.
  - The codemod and `deprecate add --source` write a file back in its own encoding (`text_encoding()`).
  - `test_encodings`. **Reviews:** none (Codex 👍).
- **#140, P53 part 4 (the discarded diagnostics: S2, V11, V12, M9, and `diff_system`'s contrast skip; class 7)**, merged as `7b28cbf`:
  - `ProjectTokens.problems` is printed by the five gates that read a project's tokens.
  - `--reverse` names a `clamped` colour, and "no variables" lists what the input held.
  - The codemod gives a generated file a skip row, and `diff_system` notes a pair a change reaches that it cannot measure.
  - `test_diagnostics`. **Reviews:** 3 real findings (Codex 1: `--quiet`; CodeRabbit 2: a translucent pair, and the two formats with no notes).
- **At the end:**
  - `main` is this docs PR's merge, and no other PR is open.
  - The plan: 22 open items, 22 scheduled. About 1,223 tests.
  - This session used about 570 thousand tokens.

## Next steps

1. **P53's last class: the cmd.exe placeholders** (D4, G13, E14):
   - `CLAUDE.md:44`'s `<ids>`;
   - the `<export>` in the prompt's live-check command;
   - `design-critique-gate/SKILL.md`'s `<path>`;
   - the email skill's bash-only quick start.

   Extend `test_docs.PasteableCommands` to every fenced block and inline command in `CLAUDE.md`, the SKILL.md files and the plans, with placeholders in capitals. Size the sweep first: the plans hold many Bash-tool blocks, which are bash on purpose.
2. **Then P54, the mediums**, one PR per §3 area, and **P55, the lows**. Then Phase 6b's workstreams in the owner's order, then **R4**.

## Open owner decisions

- None new. The order within Phase 6b, once Phase 6c is done, is the owner's call.

## Warnings

- **Found this session, not yet fixed (for P54):**
  - `diff_system`'s snapshot resolver reads an 8-digit hex alpha (`#2563eb80`) as opaque, so its contrast is measured as if solid. `oklch(… / 0.5)` is read as translucent.
  - `extract_system --tokens` reads a JSON file as CSS, so a DTCG token file gives zero tokens with exit 0.
- **A present but falsy value is the next case of class 6.** `x.get(k) or {}` reads `[]`, `0` and `false` as empty. Use `_given()` (`build_presentation`), or check `is None` first.
- **Bash heredocs ate `\n` twice this session** in test edits: a string written through a heredoc became real newlines. Use the Edit tool, or write a script file with the Write tool.
- **Don't edit a script while `check.py` runs.** This session did once (the perf budget) and reran the affected modules afterwards.
- **The audit session's worktree is still registered**: `…\3985bfd1-…\scratchpad\wt`, detached at `9391774`. Its fixtures may still help P54. Remove it once they don't, with `git worktree remove "C:\Users\vybec\AppData\Local\Temp\claude\C--DEV-Pro-Web-Designer-Suite-Plug-in\3985bfd1-4280-462b-8333-0e682826a220\scratchpad\wt"`.
- **Still open from earlier:**
  - Vue's `:style` binding is not read by the audit's `style=""` reader (P54);
  - the `VitalsUnderCsp` flake, now seen on macOS with Python 3.14 too (main's run of #137; its rerun passed), and the TBT flake on macOS;
  - `perf_audit.py` and an unbundled `@import` chain;
  - three tokens outside Display P3;
  - a local build never matches the release's checksums;
  - don't grep `tooling/`;
  - the repository is public;
  - `Vybecode-LTD/wds-gate-scratch` is the owner's to delete.
