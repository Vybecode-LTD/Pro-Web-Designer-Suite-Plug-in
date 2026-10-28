# JS-A: hooks, MCP server, shared JavaScript, Tailwind probe and the shipped lint configs

Audited 2026-10-28 at main 8441ff0. Files read in full: `plugins/pro-web-design-suite/hooks/hooks.json`, `hooks/design_hooks.mjs`, `shared/project_config.mjs`, `shared/browser_common.mjs`, `.mcp.json`, `mcp/design_gates.mjs`, `skills/web-design-studio/scripts/tw_probe.mjs`, `skills/web-design-studio/assets/configs/eslint.design.config.mjs`, `assets/configs/stylelint.config.mjs`, `assets/rules/design-rules.json`, `.claude-plugin/plugin.json`, README.md §"What it runs, sends and stores" and §"Install" (lines 95–230), SKILL.md line 222 (the configs). Tests consulted: `tests/test_hooks.py` (the list pins at 72–79, the router cases at 584–640, the UTF-16 reader case at 497), `tests/test_mcp.py` (220–291), `tests/test_real_tools.py` (119–136, 555–600), and the import lines of the six browser scripts. Commands run: the router hook on eight prompts; the MCP server driven over stdio from a scratchpad project (`tools/call` with `C:..\outside.css`, `..\outside.css`, `C:..\outside.html`); the guard and gate hooks on a UTF-8 and a UTF-16LE generated file and on malformed events; ESLint 10 (`tooling/main`) `--print-config` and a lint of two JSX fixtures through the shipped config; stylelint 17.15 `--print-config` and lints with the config in a subfolder and at the root; micromatch 4.0.8 probes; `tw_probe.mjs` against tailwindcss 4.3.3; `readUrls()` on a sitemap with `&#99999999;`. The scratchpad junction to `tooling/main/node_modules` was removed with `os.rmdir`; the toolchain is intact.

## Summary

11 findings: 2 high, 3 medium, 6 low. By class (counted from the headings): bug 6, gap 3, inconsistency 1, risk 1. No dead code beyond one unused loop variable. The three that matter: (1) the MCP server's "a path must be inside the project" guard is fooled by a Windows drive-relative path (`C:..\outside.css`), and the scripts then read and quote files outside the project, while `..\outside.css` is refused as promised; (2) stylelint resolves `overrides.files` relative to the config file's folder with basename matching, so with `stylelint.config.mjs` kept at `assets/configs/`, the only placement the references name, the component-file block never reaches `src/components/card.css` and Law 2 (`design/component-margins`), the whole-file Law 6 and `selector-max-type` silently do not run there, though the tests put the config at the root and pass; (3) the router sends ordinary programming prompts ("remove the magic numbers from this Python function", "the hardcoded values in config.py", "write a codemod", "a CRUD API in FastAPI", "a pitch deck for our seed round") to design skills, against the S3 rule the file states for itself.

## Findings

### JS-A-1 · high · risk (and bug)

- **Where:** `plugins/pro-web-design-suite/mcp/design_gates.mjs:246-250` (`inProject`), with `real()` at 222–239.
- **What:** A drive-relative Windows path (`C:..\x`, a drive letter with no separator after the colon) is not `path.isAbsolute`, so it is joined to the project (`<project>\C:..\x`); `real()` splits on separators and keeps `C:..` as one literal part, so nothing climbs out; `path.relative` then yields `C:..\x`, which starts with neither `..` nor a root, and the path passes. The script receives `C:..\x` as written, and Windows resolves it against the drive's current directory, the project, so `..` escapes.
- **Evidence:** Driving the server from a scratchpad project with `CLAUDE_PROJECT_DIR` set: `tools/call audit_design {paths:["C:..\\outside.css"]}` returned `verdict fail, exit 1` with a finding whose `file` is `C:..\outside.css` and whose message quotes its line (`padding: 13px`); `a11y_static {paths:["C:..\\outside.html"]}` returned `<img> has no alt attribute (src=secret-chart.png)`, text from the outside file. The control `{paths:["..\\outside.css"]}` was refused: `'paths' must be inside the project (…)`. `checked()`'s own `path.resolve(project(), v)` at line 310 does resolve the spelling correctly (Node resolves a drive-relative path against the matching drive's cwd), so only `inProject` is fooled. `tests/test_mcp.py:240-256` cover `../`, `deep/../` and absolute paths, no drive-relative one.
- **Effect:** README.md:216–218 promises "A path Claude passes must be inside the project, through any link"; on Windows a prompt-injected or mistaken `C:..\..\…` path reads any file on the drive and returns its lines in finding messages (the audit's S9, which this guard exists for).
- **Fix:** In `inProject`, refuse (or first `path.resolve`) a value matching `/^[A-Za-z]:(?![\\/])/`, and apply the same to the `folders` list; keep the string join for the `link/../secret` case. Regression test in `test_mcp.py`, Windows-only, with `C:..\leak.css` and `c:..\leak.css`, seen failing at v4.0.1.
- **Confidence:** confirmed

### JS-A-2 · high · bug

- **Where:** `plugins/pro-web-design-suite/skills/web-design-studio/assets/configs/stylelint.config.mjs:1132-1142` (block 1), `1169-1172` (block 2, the `**/tokens/*.css` entries), `1250` (block 4); the header's `lint:css` line at 30 and "Copy project_config.mjs with this file" at 32–33.
- **What:** stylelint matches `overrides.files` against the path relative to the config file's folder, with basename matching. A glob whose only directory part is a leading `**/` (`**/*.scss`, `**/theme.css`, `**/*.module.css`, `**/tokens.css`) still matches a file outside that folder by its basename; a glob with a literal directory segment (`**/components/**/*.css`, `**/ui/**/*.css`, `**/tokens/*.css`, `**/styles/legacy-bridge.css`) cannot, because `**` never crosses `..`. So when the config is not at the project root, those entries are dead for every file above it. The references name the file only as `assets/configs/stylelint.config.mjs` (stack-tailwind.md:7, stack-vanilla-css.md:999 "run the shipped `assets/configs/stylelint.config.mjs`", stack-css-modules.md:429) and never say to move it; `PROJECT.componentGlobs` and `tokenGlobs` from `.design-suite.json` are already built absolute (project_config.mjs `overrideGlobs`, `rootSpellings`), which is why they keep working. The tests write the config at the temp project's root (`test_real_tools.py:563`, run with `--config stylelint.config.mjs` at 593), so they cannot see it.
- **Evidence:** Scratchpad project, config copied to `configs/`, `src/components/card.css` holding `margin-block-start: 16px` in `@layer components`: `stylelint --config configs/stylelint.config.mjs "src/**/*.{css,scss}"` reported `declaration-property-value-allowed-list` ×3 and `design/color-no-hex`, and no `design/component-margins`; `--print-config src/components/card.css` listed `design/component-margins` once (in `overrides`), against twice with the same config at the root, where the lint also reported `design/component-margins` on line 2. From `configs/`, `src/components/x.module.css` (glob `**/*.module.css`) and `configs/components/inside.css` (relative path `components/inside.css`) did get `design/component-margins`; `src/styles/theme.css` got block 3's `BINDING_ALLOWLIST` (`--spacing-card: 28px` refused). micromatch 4.0.8: `isMatch('../src/components/card.css', '**/components/**/*.css', {dot:true, matchBase:true})` is false; `isMatch('../src/components/_card.scss', '**/*.scss', …)` is true.
- **Effect:** In the documented layout a component file under `src/` gets no Law 2 (`design/component-margins`), no whole-file Law 6 (`tier1-primitive {componentFile}`), no `selector-max-type: 0` or `selector-max-universal`; `src/tokens/*.css` keeps every literal rule on; the `@apply` bridge file is never exempted. Nothing warns.
- **Fix:** Anchor the fixed globs as the project's own are: find the project as Part 5 of the ESLint config does (the nearest folder above `import.meta.dirname` with a package.json) and run each glob through `overrideGlobs(rootSpellings(project, process.cwd()), glob)`, exported from project_config.mjs; or, at least, state in the header that the file must sit at the project root and be found without `--config`. Regression test in `test_real_tools.py`: the config written at `assets/configs/stylelint.config.mjs`, run with `--config`, a `src/components/card.css` margin expected refused, seen failing at v4.0.1. Cross-platform (the `..` rule is picomatch's, not Windows').
- **Confidence:** confirmed

### JS-A-3 · medium · bug

- **Where:** `plugins/pro-web-design-suite/hooks/design_hooks.mjs:85-87` (`design-token-migration`: `hard-?coded|magic (values|colours|numbers|pixels)`, `codemods?`), `100` (`content-model-to-ui`: `CRUD`), `108` (`client-presentation-builder`: `pitch decks?`).
- **What:** Lines 60–63 state the rule: "A word another domain shares is heard only beside one of the skill's own" (Codex on #97, S3), and the migration's `migrat…tokens` pattern is gated by `about(DESIGN_TOKEN, …)`. The patterns above are not gated, and each is a common phrase of ordinary programming or business work.
- **Evidence:** `node design_hooks.mjs route` with `{"prompt": …}`: "Remove the magic numbers from this Python function and name them as constants." → `design-token-migration`; "The hardcoded values in config.py should come from environment variables." → `design-token-migration`; "Write a codemod that renames useQuery to useSuspenseQuery." → `design-token-migration`; "Write a CRUD API in FastAPI for the orders table." → `content-model-to-ui`; "Write a pitch deck outline for our seed round." → `client-presentation-builder`. Controls: "Add a Redis cache in front of the Postgres database." and "Fix the race condition in the job scheduler." → silent. `tests/test_hooks.py:596-612` (`elsewhere`) has no case for these words.
- **Effect:** A system reminder naming a design skill is injected into unrelated prompts; the wording is soft ("If it fits"), but it is the plugin's only output on those prompts and it costs context and attention.
- **Fix:** Gate them as the siblings are: `about(DESIGN_WORK, /\b(?:hard-?coded|magic) (?:values?|…)\b/i)` or require `colou?rs?|pixels?` beside `hard-coded`; `about(DESIGN_TOKEN, /\bcodemods?\b/i)`; `about(/\b(?:screens?|forms?|UI|admin)\b/, /\bCRUD\b/)`; `about(DESIGN_WORK, /\bpitch decks?\b/i)`. Add the five prompts to `elsewhere` in test_hooks.py.
- **Confidence:** confirmed

### JS-A-4 · medium · bug

- **Where:** `plugins/pro-web-design-suite/hooks/design_hooks.mjs:165-171` (`guard`: `buf.subarray(0, read).toString('utf8')`), against the docstring at 5–8 ("as audit_design.py reads it").
- **What:** The guard decodes the file's head as UTF-8 only. `audit_design.py` reads a file through `decode_text()` (UTF-16 too, S8) and skips a generated one; the guard sees NUL-interleaved bytes, finds no marker and allows the edit.
- **Evidence:** `.design-suite.json` with `"hooks": {"generatedFiles": true, "designGate": true}`; `gen8.css` (UTF-8) and `gen16.css` (UTF-16LE with BOM, as PowerShell 5.1's `>` and `Set-Content -Encoding Unicode` write), both starting `/* DO NOT EDIT: generated by build.py */`. `guard` on gen8.css printed `permissionDecision: "deny"`; on gen16.css printed nothing (exit 0). `gate` on gen16.css was silent too: the audit recognises the marker and returns `[]`, so the edit is neither refused nor audited. `test_hooks.py:497` covers a UTF-16 config, not a UTF-16 guarded file.
- **Effect:** A generated file written by a PowerShell build step on Windows is editable by Claude, and the edit is overwritten by the next build, which is the case LC-C8 was written for.
- **Fix:** Decode the head with project_config.mjs's `jsonText(buf, false)` (exported; it already applies Python's `detect_encoding` heuristics, BOM and BOM-less UTF-16/32) before slicing 800 code points. Regression test beside the UTF-8 case, seen failing at v4.0.1.
- **Confidence:** confirmed

### JS-A-5 · medium · gap

- **Where:** `plugins/pro-web-design-suite/skills/web-design-studio/assets/configs/eslint.design.config.mjs:137-138` (`NUMERIC_SPACING`), `176` (`SPACE_BETWEEN`), `127-128` (`STOCK_PALETTE`).
- **What:** The lookbehind `(?<![-\w])` that stops `md:p-4` from matching inside a longer class also stops Tailwind's negative utilities (`-mt-2`, `-mx-4`, `-space-x-2`, `-m-4`), which `OUTER_MARGIN` (line 161) handles with `-?m`. `STOCK_PALETTE` lists the colour ramps and `\d{2,3}` steps, so `bg-white`, `text-black`, `bg-black/50` pass, although `--color-*: initial` removes them with the rest and `tw_probe`'s STOCK (tw_probe.mjs:81) checks `text-white` for exactly that reason. The audit's `TW_SPACE_XY` (`audit_design.py:447`) shares the lookbehind; it has no numeric-spacing or palette rule, so nothing else catches these.
- **Evidence:** ESLint 10.11 through the shipped config on `src/pages/Home.jsx`: line 5 `className="mx-4 space-x-2 bg-gray-100"` → three reports (stock palette, numeric spacing, space-between); line 4 `className="-mx-4 -mt-2 -space-x-2 bg-white text-black"` → no report. (In `src/components/Card.jsx`, `-mx-4` was caught by `OUTER_MARGIN` only.)
- **Effect:** The classes the comment at 134–136 says "this rule mainly fires on", pasted negative margins and `text-white`, ship through the gate; with the theme loaded they generate nothing, which is the silent failure the rule describes.
- **Fix:** Use `(?<![\w])-?` for `NUMERIC_SPACING` and `SPACE_BETWEEN` (as `OUTER_MARGIN` does, keeping `(?<![-\w])` semantics for the `md:` case via the `:`), and add `(?:bg|text|…)-(?:white|black)\b` to `STOCK_PALETTE`. Fixture lines in the ESLint real-tool test, seen failing at v4.0.1.
- **Confidence:** confirmed

### JS-A-6 · low · bug

- **Where:** `plugins/pro-web-design-suite/skills/web-design-studio/assets/configs/eslint.design.config.mjs:617-619`.
- **What:** `name: 'design-laws/a11y'` is written before `...jsxA11y.flatConfigs.recommended`, and that object carries `name: 'jsx-a11y/recommended'` (its keys: `languageOptions, name, plugins, rules`), so the spread overwrites the name.
- **Evidence:** `import('./eslint.config.mjs')` → `map(c => c.name)` prints `jsx-a11y/recommended | design-laws/core | design-laws/components`.
- **Effect:** The config inspector and error messages show the plugin's name for the block, not the suite's; nothing else changes.
- **Fix:** Put `name` after the spread.
- **Confidence:** confirmed

### JS-A-7 · low · bug

- **Where:** `plugins/pro-web-design-suite/skills/web-design-studio/assets/configs/eslint.design.config.mjs:116` (`IMPORTANT_MODIFIER`), scoped by `CLASS_TABLE` at 332–333.
- **What:** The suffix alternative `[\w\])]!(?=\s|$)` matches any string literal ending in `!`. Inside a `VariableDeclarator` named `*Styles`, `*Variants`, `*Classes` or `*ClassNames` every string literal is read, so a message table named `errorStyles` or `toastVariants` reports Law 5.
- **Evidence:** `src/components/Card.jsx:2`, `const errorStyles = { msg: 'Oops!' };` → `` `!important` is banned in both spellings ``. The audit's `TW_IMPORTANT_SUFFIX` (`audit_design.py:468`) requires a class-shaped token before the `!`.
- **Effect:** A false error in a heuristic scope the file calls "costs nothing when it misses"; here it costs a disable comment.
- **Fix:** Require a class shape before the `!`, as the audit does: `(?<![\w!\[:-])[a-z][\w:./\[\]()-]*[\w\])]!(?=\s|$)`. Fixture in the ESLint real-tool test.
- **Confidence:** confirmed

### JS-A-8 · low · bug

- **Where:** `plugins/pro-web-design-suite/shared/browser_common.mjs:657-661` (`xmlText`), called by `readUrls` at 700–701.
- **What:** `String.fromCodePoint(Number(e.slice(1)))` throws `RangeError` for a numeric entity past U+10FFFF; `readUrls` catches file and JSON errors but not this one.
- **Evidence:** `readUrls('sitemap.xml')` on `<urlset><url><loc>https://example.com/a&#99999999;</loc></url></urlset>` → `readUrls threw: RangeError: Invalid code point 99999999`.
- **Effect:** A malformed or hostile sitemap given to `--urls` ends a gate run with a stack trace instead of the `--urls FILE: …` problem every other bad input gets (exit 2 with the reason).
- **Fix:** Wrap the entity decode in try/catch and leave the entity as written, or `return fail('…is not XML text')`. Unit case in `test_browser_scripts.py`.
- **Confidence:** confirmed

### JS-A-9 · low · gap

- **Where:** `plugins/pro-web-design-suite/skills/web-design-studio/assets/configs/stylelint.config.mjs:787` (`SASS_LENGTH`, units `px|rem|em|pt|pc|in|cm|mm|q`); the same list in `audit_design.py:425` (`LENGTH_LITERAL`).
- **What:** `design-rules.json` `sass.variables.rule` refuses "a Sass variable that holds a length"; both gates know the absolute and font-relative units only, so viewport, container, `ch`/`ex` and percentage lengths pass, and so does the one the sizing family singles out, `65ch`.
- **Evidence:** `_card.scss` with `$card-width: 50vw; $card-measure: 65ch; $card-pad: 24px;` → one report, `design/sass-variable-literal` for `24px` only. The spec's examples (`design-rules.json:198-206`) use `px` only, so `test_rules_spec` cannot see it.
- **Effect:** `$measure: 65ch` in a partial is the "line length is a spacing decision" case `values.families.sizing.why` argues against, uncaught in SCSS.
- **Fix:** Extend both unit lists with the units `audit_design.py:423` already knows for values (`%|ch|ex|vh|vw|dvh|svh|…|cq*`), add `$measure: 65ch` and `$w: 50vw` to the spec's `refused`, rerun the conformance tests.
- **Confidence:** confirmed

### JS-A-10 · low · gap

- **Where:** `plugins/pro-web-design-suite/skills/web-design-studio/assets/configs/stylelint.config.mjs:1203-1211` (block 3), comment at 1199–1201.
- **What:** Block 3 replaces `declaration-property-value-allowed-list` with `BINDING_ALLOWLIST`, whose keys are custom-property regexes only, so in a theme file every ordinary declaration (an `@utility` block's `min-block-size: 44px; padding: 13px`) has no value allowlist at all. The comment says those "answer to the gates' other rules"; the ones left are `color-no-hex`, `no-literal-colour-function` and `color-named`, so lengths, durations and sizes pass. The audit treats a theme file as a token file (`design-rules.json` `file_classes.binding_files`), so neither gate sees them.
- **Evidence:** `src/styles/theme.css` with `@theme { --spacing-card: 28px }` and `@utility tap-target { min-block-size: 44px; padding: 13px; }` → one report, `--spacing-card`.
- **Effect:** A literal in theme.css's `@utility` blocks is checked nowhere; `theme.css §0` says the file "decides nothing".
- **Fix:** Merge `VALUE_ALLOWLIST` and `BINDING_ALLOWLIST` for block 3 (`{...VALUE_ALLOWLIST, ...BINDING_ALLOWLIST}`), so `@utility` declarations keep the families' allowlists; or state the exemption in the spec. Spec example and real-tool case either way.
- **Confidence:** confirmed (the behaviour); possible (whether it is meant)

### JS-A-11 · low · inconsistency

- **Where:** `plugins/pro-web-design-suite/mcp/design_gates.mjs:98-113` (`findPython`, `if (python !== undefined) return python;`).
- **What:** The first probe's result is cached for the server's lifetime, `null` included; the hooks (`design_hooks.mjs:186-195`) probe on every run. A user who installs Python, or sets `WDS_PYTHON`, after the first tool call keeps getting "the gates need Python 3 … and none was found" until the session restarts, and the message does not say so.
- **Evidence:** Lines 103 and 111: `python = candidates.find(…) ?? null; return python;` with the guard `python !== undefined`.
- **Effect:** One confusing session after installing Python mid-task.
- **Fix:** Cache only a found interpreter (`if (python) return python;`), or say "restart the MCP server after installing" in the message.
- **Confidence:** possible

## Static-analysis candidates, resolved

- `eslint.design.config.mjs:552` `no-template-curly-in-string`: intentional. The string is the rule's message and quotes the `${…}` syntax it reports; it is not a template literal and nothing is interpolated. No change, or an inline `// eslint-disable-next-line no-template-curly-in-string -- the message quotes the syntax`.
- `tw_probe.mjs:183` `'m' is assigned a value but never used`: a nit, not a bug. `m` is only the `while` test; `while (opener.exec(text))` reads the same and drops the variable. No behaviour change.

## What is covered well

The hook contract is right and defensive: `PreToolUse` deny with `permissionDecision`/`permissionDecisionReason`, `PostToolUse` and `UserPromptSubmit` `additionalContext`, exit 0 always, silence on a missing `file_path`, non-JSON stdin or a hook's own throw (all confirmed by running them), config errors told to Claude only for a file that config would have governed, and the 9,000-character cap below Claude Code's documented 10,000. The extension and marker lists are pinned to the Python constants by `test_hooks.py:72-79`, so they cannot drift. The MCP server keeps stdout for JSON-RPC alone, answers `initialize`/`ping`/`tools/list`/`tools/call`, validates argument types and unknown keys, refuses `..`, `deep/..` and links that lead out (except JS-A-1), kills a script at the timeout, and `fit()` trims the longest nested list first with an honest `truncated` note. `project_config.mjs` is a faithful port held to the Python reader by `test_project_config.py` and `test_dtcg.py` (encodings, DTCG, Tokens Studio math, resolvers, the `names` map), and its project globs are already anchored to every spelling of the root. Both shipped configs load cleanly under ESLint 10.11 (`--print-config`: 38 rules, exit 0) and stylelint 17.15 (`--print-config` exit 0, no stderr), with rule options the current majors accept; the refused examples of the spec are caught where the tests exercise them. `tw_probe.mjs` detects v3 and refuses it with a pointer to Part 5, finds the project's own Tailwind and ran clean against 4.3.3 (3 roles generate, 0 of 22 stock classes, `md:block` from `--breakpoint-md`). The browser helpers quote the install hint per shell (`shellArgument`), never download a browser, send `--header` values to the page's origin only, and refuse to overwrite an input. No export of either shared master is dead: every one is imported by a script or exercised by a test (`test_browser_scripts.py`, `test_project_config.py`, `test_check_roles.py`, `test_real_tools.py`).
