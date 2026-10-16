# Handoff

**2026-10-16**, after P55 parts 4 and 5, the last of Phase 6c, the owner's audit. **Phase 6c is done (P50 to P55, N41 to N47).** **Next: Phase 6b's workstreams (P34, P35, P37, P41, P42, P43), in the order the owner chooses, then R4.**

**The next session starts from `dev plans/next-session-prompt.md`**: orientation, then the work in detail. `dev plans/next-session-opening-prompt.md` is the message to paste in.

## State

- **#159, P55 part 4 (§3.5 and §3.6: E11, E12, G8 to G10, G12, G14, G16)**, merged as `1401c4f`.
  - `lint_email` reports each `<style>` rule on its own line.
  - Prisma's `Unsupported("…")` reads as the type it names, and neither schema reader takes a PostGIS SRID for a length.
  - `perf_audit` names the report pages it leaves out, `--write-baseline` included.
  - `a11y_static` quotes a bound value as `{…}`. Only a job title asks for `organization-title`, and a number input asks only for a number's purposes.
  - The outline's colour may transition, and axe's two-digit criteria are named.
- **#160, P55 part 5 (§3.7 and §3.8: D5 to D9, T3 to T10)**, merged as `2aa5fb4`.
  - The Core Web Vitals thresholds and the evals' Claude Code floor are registered.
  - `check_pointers` reads the agents and the workflow commands.
  - Unused imports, empty f-strings, `raise` without `from` and unread locals are gone, and the new `test_static_checks` keeps them out without ruff.
  - 81 assertion loops are on `subTest`, the 2025.10 fixtures use the colour object, and the suite's guards are widened.
  - N47 is done.
- **Reviews:** 8 real findings (Codex 3, CodeRabbit 5), and the local `check.py` caught 2 more. Each was fixed with a test failing on the head it reviewed, or, for test code, a control the old code fails. The next prompt's §0 has the lessons.
- **At the end:** the plan has 19 open items, all 19 scheduled; about 1,310 tests. This session used about 600 thousand tokens.

## Next steps

1. If this docs PR, #161, is still open, merge it once green.
2. **Ask the owner which Phase 6b workstream comes first**: P34 (runtime coverage: SPAs, logged-in pages, shadow DOM, several URLs and viewports), P35 (the cheap automatable checks, other engines), P37 (SCSS in stylelint; Next.js App Router, Vue, Svelte, Astro), P41 (email: MJML or React Email, RTL, caniemail's matrix), P42 (persuasion: UK and EU consumer law, consent, price experiments), P43 (more page types, a claims layer). The next prompt's §4 has each one's scope and files.
3. Then **R4**, release 4.0.0, in R3.6's order: a live check (the owner's OK and its estimate), the release PR, the evals (the owner's OK, about $11), the tag.

## Open owner decisions

- The order of Phase 6b's workstreams.
- **The Baseline browser versions** (the rest of the audit's D6): about a dozen references quote versions such as "Chrome 111, Firefox 113, Safari 16.2", many linked to web-features. Registering each in `evidence.json` is a research task of its own: schedule it as an item, or leave the web-features links as the record?

## Warnings

- **Codex reviews again** (it found 2 real issues on #159). CodeRabbit still runs one review an hour. Neither is a gate.
- **A gate's source that names a criterion counts as covering it**: `TheAuditsRuntimeMediums.test_the_coverage_table_says_what_this_suite_runs` greps `a11y_static.py` and `a11y_runtime.mjs` for each criterion the coverage table marks "Not in this suite". A comment naming "1.4.12" failed it.
- **The byte table in `next-session-prompt.md` is held to the disk** (`test_docs.TheAuditsDocsLows`): update a row whenever a SKILL.md changes size.
- **`test_static_checks`** refuses an unused import, an empty f-string, an unread local, `raise` in an `except` without `from`, `open(…).read()`, and an assertion loop in a test method without `subTest`. `# noqa: CODE` on the line waives one.
- **Heredocs ate backslashes three times this session** (a NUL byte in the CHANGELOG once): write any text with a backslash through a script file or the Edit tool.
- **`gh run watch` lost its connection twice** (`ci exit 1`, "error connecting to api.github.com"): read `gh pr checks N` and restart the watcher.
- **Still open from earlier:** Vue's `:style` binding is not read by the audit's `style=""` reader (no audit finding covers it, so P55 did not; it needs an item); the `VitalsUnderCsp` macOS flake; `test_interact_at_clicks_while_the_page_hydrates` failed once in 11 local runs; `perf_audit.py` and an unbundled `@import` chain; three tokens outside Display P3; don't grep `tooling/`; the repository is public; `Vybecode-LTD/wds-gate-scratch` is the owner's to delete.
