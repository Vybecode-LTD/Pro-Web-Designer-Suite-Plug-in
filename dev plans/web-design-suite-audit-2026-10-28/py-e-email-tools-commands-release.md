# PY-E: the email scripts, the maintainer tools, the workflow-command scripts and the release builder

Audited 2026-10-28 at main 8441ff0. Files read in full: `plugins/pro-web-design-suite/skills/email-template-system/scripts/build_email.py`, `export_email_theme.py`, `lint_email.py`, `sync_email_tokens.py`; `plugins/pro-web-design-suite/tools/check.py`, `check_pointers.py`, `fail_before.py`, `sync_caniemail.py`, `sync_rules.py`, `sync_snippets.py`; `plugins/pro-web-design-suite/workflow-commands/deck/scripts/deck.py`, `gate/scripts/run_gates.py`, `install-gate/scripts/install_gate.py`, `install-gate/templates/design-gates.yml`, `new-system/scripts/new_system.py`, `release-check/scripts/release_check.py`; `tooling/release/build.py`, `tooling/release/compare.py`; `dev plans/check_execution_plan.py`, `dev plans/readme-art/build_readme_art.py`; `skills/email-template-system/SKILL.md`; the five commands' `SKILL.md` and `workflow-commands/email-build/SKILL.md`; `project_config.py` only for `refuse_overwrite`, `read_text` and `decode_text`; `references/email-workflow.md` by grep for the flags it promises. Tests consulted: `tests/test_email.py` (the comment, minify and size tests), `test_email_frameworks.py`, `test_email_tokens.py`, `test_caniemail.py`, `test_tools.py`, `test_commands.py`, `test_release_build.py`, `test_pointers.py`, `test_doc_snippets.py`, `test_precommit_hook.py`, `test_agents.py`, `test_evals.py` (names and enumeration only). Commands run: `python -B tooling/release/build.py <empty scratch folder>`; `build_email.py` on a scratch template with `--text`, `--minify`, `--text-only` and a nested-paren `var()` fallback, and on `assets/templates/newsletter.html` for the byte count; `lint_email.py` on scratch files with `display: ;`, named and `hsl()` colours, `--source`; `export_email_theme.py` both formats on the stock tokens; `sync_email_tokens.py` from the starter `tokens.css` twice and `--check`; `tools/check.py`'s `affected()` imported and probed with 36 paths; greps of the ruff and pylint outputs and the pinned caniemail fixture's result codes. Nothing outside the scratchpad was written but this file.

## Summary

12 findings: 1 critical, 1 high, 6 medium, 4 low. By class (counted from the headings): bug 8, gap 2, inconsistency 1, risk 1. No dead code found (every function, constant and flag I suspected is reached; checked by grep). No Python 3.9 problem found (the `X | None` forms are all under `from __future__ import annotations`; `str.removeprefix` is 3.9). The release builder prints a clean build today: no refusal, no hold, no warning.

The three that matter most: (1) `build_email.py --text` is never passed to `refuse_overwrite`, so `--text emails/receipt.html` silently replaces the source template with its plain-text part and exits 0 (PY-E-1). (2) `--minify` strips every non-conditional comment, including the ESP directives the build's own comment filter deliberately keeps (`{{#if}}`, `htmlmin:ignore`), and `--keep-comments` does not stop it (PY-E-2). (3) The lint measures contrast only for hex, the 18 named colours it knows and `rgb()`; `hsl(0 0% 60%)` on white at 2.85:1 and `dimgray` pass both the contrast check and `--source`'s Law 1 check in silence (PY-E-7).

## Findings

### PY-E-1 · critical · risk

- **Where:** `plugins/pro-web-design-suite/skills/email-template-system/scripts/build_email.py:1392`, `:1438-1441`
- **What:** The overwrite guard covers `--out` but not `--text`. A `--text` that names the source template (or the token file, or `--out`) is written over without a word.
- **Evidence:** `clash = refuse_overwrite(args.out, source_path, tokens_path)` at 1392; `text_path.write_text(text, encoding="utf-8")` at 1441 with no check. Run: `build_email.py victim.html --out out.html --text victim.html -q` exited 0 and `victim.html` now begins `Caf&eacute; & cr&egrave;me…` (the plain text). `--out same.html --text same.html` leaves `same.html` holding the text, not the HTML.
- **Effect:** One wrong extension in the command SKILL.md and `/email-build` tell the user to run (`--text build/x.txt`) destroys the committed source template, silently. This is the E9 class the suite's `refuse_overwrite` exists for; the sibling flag is guarded.
- **Fix:** `refuse_overwrite(args.out, source_path, tokens_path, args.text)` and `refuse_overwrite(args.text, source_path, tokens_path, args.out)`. Regression test: `--text` naming the source exits 2 and the source is unchanged (fail-before on v4.0.1).
- **Confidence:** confirmed

### PY-E-2 · high · bug

- **Where:** `plugins/pro-web-design-suite/skills/email-template-system/scripts/build_email.py:1114` (`minify_html`), against `:112-115` (`COMMENT_KEEP_RE`) and `:1289-1295`
- **What:** `strip_comments` keeps conditional comments and ESP directives (DL-A20). `--minify` then runs a second, blunter filter that removes every comment that is not `[if`/`<![endif]`, so the directives it just kept are gone; `--keep-comments` (documented in `email-workflow.md` line 109 as the escape hatch "when your ESP parses comment markers") is ignored by the minifier too.
- **Evidence:** `html = re.sub(r"<!--(?!\[if|<!\[endif).*?-->", "", html, flags=re.S)` at 1114. Run on a template holding `<!-- {{#if vip}} -->…<!-- {{/if}} -->` and `<!-- htmlmin:ignore -->`: the plain build keeps both (`{{#if`: 1, `htmlmin`: 1); `--minify` keeps neither (0, 0), exit 0. `tests/test_email.py:233` tests the directives only on the unminified path.
- **Effect:** A near-threshold email (the documented reason to pass `--minify`) ships to Mailchimp or a Handlebars ESP with its conditional blocks unbalanced or missing, and the build reports success. SKILL.md promises only that "conditional comments are protected", which is true and incomplete.
- **Fix:** In `minify_html`, strip only comments that `COMMENT_KEEP_RE` does not match, and skip the strip entirely when `keep_comments` is set (pass it in from `build`). Regression test: the ESP-directive test run again with `--minify` and with `--keep-comments --minify`.
- **Confidence:** confirmed

### PY-E-3 · medium · bug

- **Where:** `plugins/pro-web-design-suite/skills/email-template-system/scripts/build_email.py:908-909` (`inject_mso`)
- **What:** The head's existing MSO block is recognised only when its comment opens with `[if mso`. The boilerplate most inherited emails carry (`<!--[if gte mso 9]>`, `[if (gte mso 9)|(IE)]`) is not seen, so the build adds a second `PixelsPerInch` block and a second font rule. `lint_email.py:126` already fixed the same test for the lint (`MSO_IF_RE`, "Codex on #196"); the build was not given it.
- **Evidence:** `re.match(r"\s*\[if\s+mso", node.data, re.I)` at 909. Run on a head holding `<!--[if gte mso 9]><xml>…<o:PixelsPerInch>96</o:PixelsPerInch>…<style>table, td { font-family: Arial… }</style><![endif]-->`: notes "added <o:PixelsPerInch>96</o:PixelsPerInch>" and "added the [if mso] font rule"; the output holds `PixelsPerInch` four times (two blocks).
- **Effect:** Duplicate `<o:OfficeDocumentSettings>` and `[if mso]` style in every build of a Litmus/Foundation/Campaign Monitor-style template: a few hundred bytes and a sloppy head the lint does not flag.
- **Fix:** Reuse the lint's `MSO_IF_RE` (move it to `build_email.py`, import it in the lint) at 909. Regression test: a `[if gte mso 9]` head gets no second block.
- **Confidence:** confirmed

### PY-E-4 · medium · bug

- **Where:** `plugins/pro-web-design-suite/skills/email-template-system/scripts/build_email.py:297` (`VAR_RE`), `:375-404`, `:1219-1223`
- **What:** The `var()` regex allows one level of parentheses in a fallback. A fallback with two (`var(--pad-card, max(4px, min(8px, 1vw)))`) matches nothing, so the token is not substituted even though `--pad-card` exists, nothing is reported missing, and the literal `var(…)` ships with exit 0. The docstring and SKILL.md promise exit 2 on an unresolved token.
- **Evidence:** `VAR_RE = re.compile(r"var\(\s*(--[A-Za-z0-9_-]+)\s*(?:,([^()]*|[^()]*\([^()]*\)[^()]*))?\)")`. Run: the built HTML holds `padding:var(--pad-card, max(4px, min(8px, 1vw)))`, exit 0. `lint_email.py` then reports "unresolved token --pad-card … add the token to assets/email-tokens.json", which is the wrong diagnosis: the token is there.
- **Effect:** A token-authored declaration reaches the inbox as `var()`, which no client resolves; the user sees the lint blame a token that exists.
- **Fix:** Replace the regex with a small scanner that finds `var(` and walks to its matching `)` (as `sync_email_tokens.resolve` at 131-151 already does), or after substitution fail the build on any `var(` left in a style, attribute or comment. Regression test: a two-level fallback resolves to the token's value.
- **Confidence:** confirmed

### PY-E-5 · medium · bug

- **Where:** `plugins/pro-web-design-suite/skills/email-template-system/scripts/build_email.py:1030-1056` (`ENTITIES`, `unescape_entities`)
- **What:** The plain-text part decodes 40 named entities by table. Every other named entity (`&eacute;`, `&egrave;`, `&ouml;`, `&aring;`, `&ntilde;`, `&szlig;`, `&euml;`…) is written to the text part as its source text. `html.unescape` is in the stdlib and knows all 2,231.
- **Evidence:** Run `--text-only` on `<p>Caf&eacute; &amp; cr&egrave;me, &ouml; &aring; &ntilde; &copy;</p>`: output `Caf&eacute; & cr&egrave;me, &ouml; &aring; &ntilde; ©`. SKILL.md: "Read the plain-text part … Somebody receives it."
- **Effect:** A French, German or Nordic email's text part, which the workflow calls "a deliverable, not an afterthought", shows raw entities to the reader of the text alternative.
- **Fix:** `html.unescape(text)` first, then the three the table maps differently (`&nbsp;` to a space, `&zwnj;`/`&zwj;`/`&shy;` to nothing); keep the numeric branch for the `0 < code` guard or drop it. Regression test: `&eacute;` in the text part.
- **Confidence:** confirmed

### PY-E-6 · medium · bug

- **Where:** `plugins/pro-web-design-suite/skills/email-template-system/scripts/build_email.py:1426`, `:1434`, `:1441`; `lint_email.py:1499`
- **What:** `Path.write_text` without `newline=""` lets Windows turn every `\n` into `\r\n`. The build's byte count and clipping percentage are computed from the LF string, so on Windows the file on disk is larger than the number reported, the lint (which reads the bytes through `decode_text`, no newline translation) measures the larger file, and a Windows build differs byte for byte from the Linux one. `export_email_theme.py:488` and `sync_email_tokens.py:850-854` write bytes for exactly this reason ("LF, as the file has it, on Windows too").
- **Evidence:** `out_path.write_text(html, encoding="utf-8")` at 1434. Run on `assets/templates/newsletter.html`: the report says `9,332 bytes — 9.1% of Gmail's 102,400-byte clipping threshold`; the file is 9,442 bytes with 110 `\r\n`; the text part has 49. `tests/test_email.py:594` already works round it (`.replace("\r\n", "\n")  # as the build counts it`).
- **Effect:** Near the threshold, a Windows build that reports 101,900 bytes can be over 102,400 on disk and in the lint; the same source yields different `build/` bytes per platform.
- **Fix:** `write_bytes(html.encode("utf-8"))` at all four sites (or `open(..., newline="\n")`). Regression test: a built file holds no `\r`.
- **Confidence:** confirmed

### PY-E-7 · medium · bug

- **Where:** `plugins/pro-web-design-suite/skills/email-template-system/scripts/lint_email.py:276-282` (`NAMED_COLORS`), `:371-393` (`parse_color`), `:994-996`, `:1124-1126`, `:1296-1297`
- **What:** `parse_color` knows 18 named colours, 3/6/8-digit hex and comma- or space-separated `rgb()` with 0–255 channels. Any other notation (`hsl()`, `oklch()`, `rgb()` with percentages, the other 130 named colours) returns `None`, and `check_contrast`, `check_dark` and `resolve_background` `continue` without a finding. `check_source`'s "hand-written colour" check uses the same 18 names, so `color: dimgray` is not a Law 1 violation.
- **Evidence:** Run on `<p style="color:hsl(0 0% 60%)">` and `<p style="color:dimgray">` on `#ffffff` beside a `#999999` control: the only contrast finding is `#999999 on #ffffff is 2.85:1` (the `hsl()` is the same grey). `--source` on `.a { color: dimgray; } .b { color: red; }`: one error, for `red`.
- **Effect:** SKILL.md promises "measured contrast against the nearest resolvable background" and that `--source` catches "a hand-written colour"; an inherited email (the "when you are handed an existing email" workflow) keeps failing text and hand-written colours with a clean report.
- **Fix:** Reuse `sync_email_tokens.to_hex` (it already converts `hsl()`, `oklch()` and percentage `rgb()`) in `parse_color`, and a full CSS named-colour table (148 entries) shared by both checks; where a colour still cannot be parsed, add an `info` finding "colour not measured". Regression tests: `hsl()` under 4.5:1 fails; `dimgray` is a Law 1 error in `--source`.
- **Confidence:** confirmed

### PY-E-8 · low · bug

- **Where:** `plugins/pro-web-design-suite/skills/email-template-system/scripts/lint_email.py:609`
- **What:** The `<style>` sweep takes `value.split()[0]` without the empty guard its inline twin has at 589.
- **Evidence:** `if value.split()[0] not in entry:`; run on `<style>.x { display: ; }</style>`: `IndexError: list index out of range`.
- **Effect:** A traceback instead of a report on a malformed declaration.
- **Fix:** `first = value.split()[0] if value.split() else ""`, as at 589. Regression test: `display: ;` in a style block lints without a crash.
- **Confidence:** confirmed

### PY-E-9 · medium · gap

- **Where:** `plugins/pro-web-design-suite/tools/check.py:50`, `:58-62`
- **What:** A changed file outside `skills/` selects the test modules whose text contains its file name. A file a test reads by glob but never spells gets no module, so the quick pass runs nothing for it. The docstring describes this behaviour; the consequence is that `check.py` can report "pass" on a change the suite would fail.
- **Evidence:** `affected(["plugins/pro-web-design-suite/agents/gate-runner.md"], sources)` returns `[]`; `tests/test_agents.py:38` checks every agent through `AGENTS.glob("*.md")` and names `gate-runner` (line 19) but never `gate-runner.md`. `agents/design-critic.md` happens to select `test_agents` because another test spells it. Of 36 probed paths, three select nothing: that agent, `tooling/release/icon.svg` (no test reads it; fine) and `dev plans/check_execution_plan.py` (run as its own check; fine).
- **Effect:** An edit to an agent's frontmatter that breaks `test_agents` passes `check.py` locally and fails in CI, after the push the economy rules say to make once.
- **Fix:** Add the top folder as a second key for files under `agents/`, `hooks/`, `mcp/`, `evals/` and `workflow-commands/` (as `skills/<name>` already gets), or map those folders to their test modules outright. Regression test in `test_tools.py`: an agent file selects `test_agents`.
- **Confidence:** confirmed

### PY-E-10 · low · inconsistency

- **Where:** `plugins/pro-web-design-suite/skills/email-template-system/scripts/lint_email.py:900`, against `build_email.py:113`
- **What:** The build's comment filter treats ERB `<%` as an ESP directive; the lint's relative-URL check accepts `{{`, `{%`, `*|`, `%%` and `#` as merge-tag prefixes but not `<%` (nor Mailjet's `{$`).
- **Evidence:** `re.match(r"^(https?:|mailto:|tel:|sms:|\{\{|\{%|\*\||%%|#)", href, re.I)` at 900; `COMMENT_KEEP_RE` includes `<%` at 113.
- **Effect:** `href="<%= unsubscribe_url %>"` is an error, "relative URL", on a build whose comments the same tag passed.
- **Fix:** Add `<%` and `\{\$` to the prefix list. Regression test: the ERB href is not a relative URL.
- **Confidence:** confirmed

### PY-E-11 · low · bug

- **Where:** `plugins/pro-web-design-suite/skills/email-template-system/scripts/build_email.py:1313-1315`, `:1448-1449`
- **What:** The "bytes of `<style>` survived" figure counts every `<style>` in the output, including the one inside the `[if mso]` conditional comment that the build itself adds (`MSO_FONT_STYLE`, about 110 bytes). Gmail drops comments whole, so that CSS never counts against its 16,384-byte ceiling.
- **Evidence:** `for match in re.finditer(r"<style[^>]*>(.*?)</style>", html, flags=re.S | re.I)` at 1313 runs on the serialised document, comments included; `email-client-matrix.md` quotes the resulting 751–919 bytes as what the templates "keep" (`tests/test_email.py:598`).
- **Effect:** The reported figure and the documented range overstate the retained CSS by the MSO rule's size; harmless at today's sizes, misleading next to the ceiling.
- **Fix:** Count `<style>` elements in the DOM, skipping comment nodes, before serialising; or strip conditional comments from `html` before the count. Update the matrix's range with the test. No regression test beyond the existing E7 test's number.
- **Confidence:** likely

### PY-E-12 · low · gap

- **Where:** `plugins/pro-web-design-suite/skills/email-template-system/SKILL.md:233-241`, against `lint_email.py:1416`
- **What:** The lint's flag table omits `--tokens`, the flag `--source` needs in a project with no `.design-suite.json` `emailTokens`; nothing in SKILL.md or `email-workflow.md` says `lint_email.py --source` takes it (the grep found no `lint_email … --tokens`). `build_email.py`'s `--quiet`/`-q` is likewise undocumented, harmlessly.
- **Evidence:** `parser.add_argument("--tokens", help="token file for --source …")` at 1416; the SKILL table lists `--format`, `--source`, `--transactional`, `--strict`, `--ignore`, `--verbose`, `-o`.
- **Effect:** A user linting a source template against a project's own token file does not learn from the skill that they can.
- **Fix:** One row in the lint table. No test.
- **Confidence:** confirmed

## Static-analysis candidates, resolved

- `lint_email.py:910` B005 / E1310: `strip(" .!:>»→»")` is an intentional character set (trailing space, punctuation, `>`, `»`, `→`) stripped from both ends of link text before the weak-text match; it eats nothing a real label needs (a leading `.` in `.NET` is the only casualty, and `net` is not in `WEAK_LINK_TEXT`). Harmless; `»` is listed twice, a nit.
- `sync_email_tokens.py:635`, `:639` B023: `figure` closes over the loop's `name`, and `pair.sub(figure, note)` consumes it at 647 inside the same iteration. Harmless.
- `check.py:70` PLW1510: the nested `git()` returns `None` unless `returncode == 0` (line 71); callers test for `None`. Handled. `check.py:132` PLW1510: `ok = proc.returncode == 0` at 134 drives the verdict. Handled.
- `fail_before.py:141` PLW1510: the exit code is deliberately not read; the runner never calls `sys.exit`, and a crash is detected by the missing results file at 143-145 with the output's tail. Handled.
- `deck.py:54` PLW1510: `capture` returns the code; both callers test it against `(0, 1)` at 87 and 95. Handled.
- `install_gate.py:258` PLW1510: branched on `returncode` at 260-265. Handled. Note: `timeout=120` with no `except subprocess.TimeoutExpired`, so a hung `check_roles.py` is a traceback rather than "unreadable" (low; not a finding on its own).
- `new_system.py:55` PLW1510: `generate` tests `proc.returncode != 0` at 71. Handled.
- `check_pointers.py:109`, `:113`, `:115`, `:116`, `:117` B023: `line` and `add` close over `text`, `path`, `used`, `src`, and are called only from the `finditer` loops at 119-126 inside the same iteration. Harmless.
- `sync_rules.py:298` B023: the lambda is consumed by `BLOCK.sub` on the same line. Harmless.
- `sync_snippets.py:78` B023: `fresh` is consumed by `QUOTE.sub` at 81 in the same iteration. Harmless.
- `new_system.py:125` ARG005 / B023: `lambda m: note` is consumed by `re.subn` on the same line; it exists so a backslash in `note` is literal. Harmless; `_m` would silence ARG005.

## What build.py prints today

```
$ python -B tooling/release/build.py <empty scratch folder>
wrote <folder> from 8441ff057158: pro-web-design-suite-4.0.1.zip (313 entries, 231 files, 37 executable), 13 .skill files, SHA256SUMS; testzip: OK
exit=0
```

No refusal, no directory hold, no warning. (`main` is one file ahead of the 230 the CLAUDE.md records for the 4.0.1 tree; the version in `plugin.json` is still 4.0.1, as expected before the 4.0.2 release.)

## What is covered well

- The release builder: `test_release_build.py` proves two builds of one commit are byte-identical, that `tests/`, `evals/` and `tools/` never ship, that a link, an `export-ignore` file, a platform-refused skill, a bad or missing icon and each directory block are refused, that holds are warnings, and that `compare.py` sees a damaged payload under an intact directory. `unpack` in `fail_before.py` guards path traversal (127-128) and the builder reads modes from `ls-tree`, not the tar (383). The REV default in `fail_before.py` is the nearest reachable `v*` tag from HEAD; a fix committed on the tag itself would show as "control", which is the right answer.
- The sync tools are idempotent and `--check` is honest: `sync_email_tokens.py` from the starter's `tokens.css` wrote 181 entries, `--check` said "up to date", and a second write was byte-identical; `sync_rules.py`, `sync_snippets.py` and `sync_caniemail.py` each have a "rewrite of a tree in step changes nothing" or "stale is rewritten byte for byte" test. `sync_caniemail.py` maps `y`/`n`/`a`/`u` and rejects any other code (a `p`) loudly with a `DataError` rather than mapping it wrongly; the pinned data holds only `a`, `n`, `u`, `y`.
- `install_gate.py` refuses paths the workflow runs unquoted, a `playwright` range, a configured token file that is missing and files it did not write; the template's eleven placeholders are all replaced and `@` is barred from `--build` so no later placeholder can be smuggled in. `release_check.py` refuses an `--out` that holds the published snapshot. `new_system.py` writes nothing on a refused generator and never overwrites without `--force`. `deck.py` leaves no stale evidence from an earlier run.
- `export_email_theme.py` refuses a token value that could end its markup, both formats run clean on the stock tokens with no missing role, and the JavaScript-name clash check prevents a silent collision.
- The email scripts' encoding story holds: sources read through `decode_text` (BOM, UTF-16), JSON through `json.loads(bytes)` (BOM-aware), and every `__main__` reconfigures a cp1252 pipe to UTF-8.
