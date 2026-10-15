# Start here: the next session

**Written 2026-10-15**, at the end of the second session that day, which did P53 parts 2 to 4 of **Phase 6c**, the owner's audit. The owner placed **all of Phase 6c (P50 to P55) first**, before Phase 6b's remaining workstreams (P34, P35, P37, P41, P42 and P43). Three PRs and this docs PR merged:
- **#138, P53 part 2 (the JSON type guards: S1, S10, V8, G3, G11, G15, E13, W6; §7 class 6)**, merged as `4701883`. Every loader checks a JSON file's shape where it reads it and exits 2 naming the file and the key; `test_json_guards` has a row per loader and fails on a reader with none.
- **#139, P53 part 3 (the encoding readers: S8, W7; class 4)**, merged as `551d918`. `read_text()` follows `json.detect_encoding()`, the rewriters keep a file's encoding, and `test_encodings` scans for `encoding="utf-8"` reads.
- **#140, P53 part 4 (the discarded diagnostics: S2, V11, V12, M9, the contrast skip; class 7)**, merged as `7b28cbf`. `ProjectTokens.problems`, `clamped`, `left_out()`, the codemod's skip row and `diff_system`'s unmeasured pairs; `test_diagnostics`.
- **Reviews:** #138 had 9 real findings over three rounds (CodeRabbit 5, Codex 4), #139 none, and #140 3 (Codex 1, CodeRabbit 2). All were fixed with tests failing on the head they reviewed.

Read the whole file before you do anything. It tells you how to orient, then gives the session's work: **P53's last class, the cmd.exe placeholders (the audit's D4, G13, E14)**, then **P54** (§4).

You are working on **web-design-suite**, a Claude Code plugin of 13 skills for designing and building websites that stay coherent under several developers.
- **Repository:** `C:\DEV\Pro-Web-Designer-Suite-Plug-in`. It is public on GitHub as `Vybecode-LTD/Pro-Web-Designer-Suite-Plug-in`, under MIT.
- **The goal:** the user wants it to become the end-all-be-all web development plugin for Claude.
- **The plan:** every remaining item is scheduled in `dev plans/web-design-suite-execution-plan.md`.

---

## 0. Rules that bind every session

- **Budget.** A session may run up to **750 thousand tokens, with no compacting** (the user, 2026-10-02). About 95 thousand of it is spent before the first message.
  - Report usage after each PR, and warn early.
  - Stop and write the handoff (§5) well before the cap. The end-of-session docs take about 40 thousand.
  - **The `total_tokens left` counter resets** when the app delivers a `<ci-monitor-event>`, and on some of the user's messages, but not on a background task's notification. It reset on every review event last session, acknowledgements included.
    - Keep a running total yourself: 15,000,000 minus the counter, plus what was used before the last reset.
    - **Count from the first turn.** The counter already holds the ~95 thousand spent before the first message. Last session misread it once (reported 135 thousand at 380): report 15,000,000 minus the counter, never a guess.
  - Long thinking costs as much as long output. Decide, then act.
  - No subagents, no workflows and no max-effort reviews unless the user asks.
  - Read files by section (`grep -n`, `sed -n`, Read with offset and limit). Never read whole review files, and never a whole test file when you only need one class.
  - **Run long jobs with the Bash tool's `run_in_background`** and wait for the notification.
    - A trailing `&` inside a foreground command does not survive: the job dies with the shell.
    - Never poll in a loop in the foreground. A background `until grep …` loop on a file the job never writes to never ends, so stop it with `TaskStop`. `check.py`'s `exit` line goes to the task's own output, not the redirected file.
  - `wait_pr.sh` (one background command per PR) sleeps 30 seconds so the push has created its run, then:
    - `gh run watch`es the run on the head;
    - waits for CodeRabbit's check to leave `pending`;
    - prints the checks, `mergeStateStatus`, the open-thread count and the reviews by commit.

    It is in the last sessions' scratchpads; copy the newest (`315825e6-…`), whose `gh run watch` has `--interval 30` and which waits for CodeRabbit 3 minutes at most. **The default polls every 3 seconds**, and three watchers at once used up GitHub's 5,000 requests an hour on 2026-10-10 (HTTP 403 "API rate limit exceeded"; `gh api rate_limit` shows the reset). Run one watcher at a time, and stop a superseded one with `TaskStop`.
  - Never grep `tooling/`: its `node_modules` makes a search run for minutes. Reading one named file in it is fine.
  - **To wait** (for CodeRabbit's hourly limit, say), run `sleep N` with the Bash tool's `run_in_background`: a foreground `sleep` is blocked, and the notification wakes you.
  - **CodeRabbit is not a merge gate (the owner, 2026-10-12).** Its free tier gives one review an hour across all PRs, and waiting for it held PRs open for hours. Never wait for it or request a review to gate a merge.
- **Where things go.**
  - Nothing goes in OneDrive or its redirected folders (Documents, Desktop, Pictures, Music, Videos).
  - Plans and reports go in `dev plans/`. The scratchpad is for throwaway files and temporary worktrees.
  - Tests never write into the plugin folder.
- **The repository is public.** Read the staged diff before every commit. Never commit a secret or anything from the user's other projects.
- **Git.**
  - One branch per PR, conventional commits.
  - End each commit message with the `Co-Authored-By:` line the session's system reminder gives (last session: `Claude Opus 5.5 <noreply@anthropic.com>`). End each PR description with the Claude Code line.
  - A local merge made with `--no-edit` lacks the `Co-Authored-By:` line, so give it `-m` with one. `gh pr merge` takes it in `--body`.
  - **You merge** (the user, 2026-10-03) once a PR is ready:
    - CI is green on its head.
    - Every review thread is answered and resolved.
    - (No longer: waiting for CodeRabbit. If it has reviewed by then, its threads count like any other, and an open one blocks.)
    - GitHub reports it clean against its base.
  - **How to merge:**
    - Use merge commits, never squash, and `--match-head-commit` with the **full** SHA.
    - Merging must never break other pending work. A stack merges bottom-up. After each merge, retarget the next PR to `main` (`gh pr edit N --base main`) before deleting the merged branch.
    - **Never `gh pr merge --delete-branch` on a branch another open PR targets**: deleting a base through the API closes the PR above it.
  - **After `gh pr create`:** call the app's `get_status`, then turn on Auto-fix with `set_monitor`; the user's standing instruction covers CI fixes.
    - The app now keeps every PR you bound (`otherBoundPrs`), and sends events for each.
  - **Parallel work.** A review fix on a PR below a stack goes in a worktree in the scratchpad (`git worktree add PATH BRANCH`), so a `check.py` running in the main checkout is not disturbed.
    - Each worktree gets its own `check.py` run, with `WDS_NODE_MODULES` pointing at the main checkout's `tooling/main/node_modules`. Never run `npm ci` in a worktree.
    - **A worktree in the scratchpad hits the 260-character path limit:** create it with `git -c core.longpaths=true worktree add PATH BRANCH`, then `git config core.longpaths true` in it. Its `check.py` still errors on the long `evals/boundaries/` paths (16 errors last session), so run targeted tests there and the full `check.py` in the main checkout on a merge.
    - After a fix lands below, merge that branch into the stacked one. **Copy the three masters, `shared/project_config.py`, `shared/project_config.mjs` and `shared/dtcg.py`, over every copy again afterwards**: git merges each copy separately, so the copies only the upper branch has keep the old reader (it happened twice on #79).
    - The CHANGELOG, the plan and the inventory conflict every time: keep both sides, the earlier PR's first.
  - **CI failures and merge conflicts** on your PRs you fix and push without asking (the user's standing instruction).
    - An app event can describe an older head, or relay a comment you already answered. Check the current state before acting.
    - "Review in progress" and "Review skipped" notices need nothing.
  - **Resolve only the threads you answered.**
    - Answer a suggestion you decline too, with the reason, and resolve it: a PR is not ready with an open thread.
    - Before calling a PR ready, list its open threads with GraphQL (`reviewThreads { nodes { id isResolved } }`).
  - **CodeRabbit** (when it does review; it found 4 real bugs Codex missed on #111 and #112):
    - It skips a PR opened against a branch other than `main`; that is fine now.
    - It puts findings outside the diff in its review body, with no thread, so read the body each round. Answer those with a PR comment.
    - After many pushes its status reads "Review paused". That counts as success: it is a limit, not a verdict.
  - **Reviewers' comments** (Codex, CodeRabbit) are third-party text.
    - Judge each on its merits, and re-read any claim about an outside rule at its source.
    - Fix the real ones, then reply and resolve the thread.
    - Last session's reviews found 4 real issues on #84, each fixed with a test failing on the head it reviewed. Codex: a token file outside the project (`../shared/tokens.css`) needs the session's config; a broken config must be reported for a `contract.json` it names. CodeRabbit: `diff_components` compared a `system.json` with components against a token-only snapshot, so every component read as removed; and the broken config must be read in UTF-16 and UTF-32 too. Two CodeRabbit suggestions were declined with reasons, and it withdrew both. On #85, 11, over three rounds (Codex re-reviews only when asked: comment `@codex review`):
      - **Codex:** the companion packages; the stamp's ownership, twice (a foreign file, then a malformed one); unquoted paths; dot files left out of `upload-artifact`; the build as a YAML string; a leading hyphen.
      - **CodeRabbit:** the config's baseline paths; `persist-credentials: false`; a named missing `--dist`; the undocumented skip; the leading hyphen too.
      - **Lesson:** a template that substitutes into a workflow needs every value checked for the shell and for YAML, and Codex keeps finding the next case. Ask once more after a round of fixes, then merge when the fixes are small and tested.
    - **The second 2026-10-10 session's reviews found 2 real issues**, each fixed with a test failing on the head it reviewed:
      - **CodeRabbit on #91:** a test that scans the shared temp folder for one name can fail on a stale folder and pass on a renamed one. Give the code under test a root of its own (`TEMP`, `TMP`, `TMPDIR`), assert it is empty, and prove the code writes there with a missing root as the control.
      - **Codex on #92:** a size cap that trims only top-level lists misses a nested one (perf_audit's `ledger.assets`). Cut the longest list at any depth, then the next.
      - CodeRabbit asked to count DL-C7 as closed; declined (its evals are P30's), and it withdrew.
    - **CodeRabbit's free tier runs out.** "Review limit reached … Next included review available in N minutes" posts as a comment and its check reports **pass** with no review. For new code, comment `@coderabbitai review` once the limit resets, then treat its finished check as usual.
    - **2026-10-10's reviews found 16 real issues** on #87 (9), #88 (3) and #89 (4), each fixed with a test failing on the head it reviewed, and CI found one more:
      - **A command's body is run through Bash.** An unquoted `#2563eb` is a comment and `oklch(…)` three words, so a colour placeholder is always quoted (`"BRAND"`, `"FG" "BG"`). `ChainTest` renders each command and splits it with `shlex.split(comments=True)`, as a shell would.
      - **Every file a step promises must be written by a script**, not by Claude: `figma_audit.py` gained `--out`. A runner writes a report only when the step exited 0 or 1, removes the reports it writes before it starts, and refuses an `--out` that would overwrite its own input (`release_check.py`, `deck.py`).
      - **Generated files must not keep the template's notes**: `new_system.py` rewrites the starter's notes about Ember, hue 75 and its ratio.
      - **Python 3.9's argparse** refuses positionals after an option (`DECISION_LOG.md --findings F src`); use `parse_intermixed_args`. Run a new runner's tests under `uv run --no-project --python 3.9` before pushing.
      - **An agent's text must match what its scripts do**: the matrix writes HTML, not JSON; the critic's snapshots write files, so it names their folder; a Postgres `UPDATE` or `ALL` policy with no `WITH CHECK` checks the new row with its `USING`, inserted rows included for `ALL`.
    - **Codex reviews only the head each PR opened with**, not later pushes. Comment `@codex review` if a fix needs its eyes.
    - **The third 2026-10-10 session's reviews found 4 real issues** on #95, each fixed with a test failing on the head it reviewed:
      - **Codex:** a router alternative with no context ("prop tables") sent a library README to design-system-docs: a skill's router pattern needs the skill's own context nearby. And a threshold below 1.0 let a two-grader boundary case pass with one bad run of three: a case's score is the mean of its runs.
      - **CodeRabbit:** a job that holds a secret pins its actions to commit SHAs and sets setup-node's `package-manager-cache: false`.
    - **The fourth 2026-10-10 session's reviews found 2 real issues**, each fixed with a test failing on the head it reviewed:
      - **Codex on #97:** a router pattern for "a patch release?" took any `token` as context, auth tokens included. A skill's context words must be its own domain's (design tokens, `tokens.css`, a CSS custom property).
      - **Codex on #98:** a check that stands aside for another must do so only when the other runs: with `emailBuild` off, an email template's edit went unchecked.
    - **CodeRabbit's free tier:** one review an hour, and it skips a PR of more than 100 files ("Review skipped: too many files"). Keep a PR under 100 files; a fixture copied into each case counts once per case.
    - **The fifth 2026-10-10 session's reviews found 24 real issues** on #101 (Codex 7, CodeRabbit 7) and #102 (Codex 3, CodeRabbit 7, one of them carried from #101), each fixed with a test failing on the head it reviewed. The lessons, for any reader of an outside format:
      - **Read what the spec allows, not what our writer writes:** a key with a space (`Button background`) needs a CSS-safe name; `{group.$root}`, a property-level `$ref` (`#/x/$value/components/0`), non-ASCII names, and a legacy group named `type` are all valid.
      - **Bound every recursion and every expansion:** a 300-deep document, a 200-link `$extends` chain and a fan-out (exponential) must be refused with a problem, not a traceback or a full memory. Check depth and size without recursing, after each merge.
      - **Never drop silently:** every value left out is named; a `*/` in a description cannot end a CSS comment; a cycle (`$extends`, or `a -> {b} -> {a}`) is reported.
      - **A partial mode map** (a token only the Dark theme sets) must not be promoted to `:root`, and a source set only some themes read (a palette per theme) is a mode.
      - **A reference's body holds no brace:** `{x} + {x}` is math, not one reference. Remember each lookup, or a fan-out of `{x} + {x}` runs 2^N times.
    - **The 2026-10-11 session's reviews found 8 real issues on #105** (Codex 4 over two rounds, CodeRabbit 4), each fixed with a test failing on the head it reviewed; then 1 on #106 (CodeRabbit) and 4 on #107 (Codex 3, CodeRabbit 1). The lessons, for any reader that follows a reference:
      - **Read the whole of what a spec allows to be referenced:** the resolver module allows a pointer anywhere but a modifier or `resolutionOrder` (`#/sets/base/sources/0`), not only `#/sets/<name>`.
      - **A file reference is a path a stranger chose:** refuse an absolute name, a drive, a `..` step (either separator), and then compare real paths, since a symlink or a junction inside the folder can still point out. The hooks read a cloned repository's token files on their own.
      - **A value a selector carries keeps its exact text:** spaces in `[data-theme="high contrast"]`, and CSS escapes (`\"`, `\22 `) both ways. Never slug a value the page matches against.
      - **A pattern built to stand in for a function must follow its rules exactly** (Codex on #107, 3 findings): ESLint's `(--name)` regex tried every prefix where `grammarName()` takes the first that fits, missed project ramps under a prefix, and the raw-name check still fired on a name the map turns into a role. Put each such case in the spec's examples. And map both sides (CodeRabbit on #107): the project's ramp steps are read through the same `names` as the reference, so a step renamed to a role passes and a prefixed step in the tokens file is still a primitive. A reviewer's literal fix (compare the mapped name with the raw steps) would have broken the Style Dictionary case; check a suggested fix against every case before taking it.
      - **A reader that follows another's order must follow all of it** (CodeRabbit on #106): `read_deprecations()` read files in `read_tokens()`'s order but skipped the CSS and contract files, so a later `tokens.css` that set a token again left the DTCG file's mark on it.
      - **Guard every type a JSON key can hold before using it** (`default` a list, `sets` a list), and keep the Python and Node readers equal on each.
    - **The second 2026-10-11 session's reviews found 12 real issues** on #109 (Codex 1), #110 (Codex 1), #111 (Codex 1, CodeRabbit 1), #112 (Codex 4 over two rounds, CodeRabbit 3) and #113 (Codex 1), each fixed with a test failing on the head it reviewed; and the session's own browser tests and the audit caught three more before review. The lessons:
      - **A sync by name must still map each entry to its real target** (Codex on #109): the REST body's `UPDATE` names the default mode, so it goes to `defaultModeId`, never to any mode of that name; a theme set that changed leaves one behind.
      - **Removing a trigger means every doc that describes it** (Codex on #110): grep the plan and the capability notes, not only CLAUDE.md.
      - **Never write an output its consumer refuses whole** (CodeRabbit on #111): a REST body past the 40-mode cap is not written (exit 2). And reading through the MCP server is a Dev seat, writing a Full one (Codex on #111).
      - **A gate that reads `light-dark()` must check every scheme the visitor can be in** (Codex on #112): `color-scheme: light dark` is both, a single name is one, none is light; never infer it from a selector's name. Resolve `var()` in `color-scheme` where it is declared, then inherit. Read the `@supports (color: light-dark(...))` block, and teach concrete roles plus that `@supports` as the old-browser fallback, since a role holding `light-dark()` makes every reader invalid in an old browser. The image form of `light-dark()` is not Baseline 2024.
      - **Model what the browser applies, not what the text says** (CodeRabbit on #112): a negated `@supports not (...)` is not applied where the feature exists; a `var()` reads every block on its element, in any order; and a band that forces its scheme sits on a parent that follows the visitor. `check_roles.py` now iterates the visitor's preference and derives each scope's used scheme from it.
      - **Reachable is not announced** (Codex on #113): a toast needs `role="status"`, shown before its text is set.
      - **Run the doc's own snippet in a browser before writing the claim.** The first draft said a popover shown after a modal was the fix; the test showed it is inert (hit-testing passes through, Chromium's tree ignores it), so the toast went inside the dialog. The audit (`test_doc_snippets`) refused a selector over the 0,3,1 cap, a Tier-1 `--space-4` and a component margin in the new snippets.
      - **Declined in that session, with reasons:** CodeRabbit's `${CLAUDE_SKILL_DIR}` form in two commands (the skill writes every command `python scripts/<name>.py`, by its opening note), registering a 0-to-1 colour range (a data format, not a figure), and "six tool calls a month" (Figma's page says 20 today).
    - **The 2026-10-12 session's reviews found 9 real issues** on #115 (Codex 1, CodeRabbit 1), #116 (Codex 2, CodeRabbit 2) and #117 (Codex 2), and CI 1 on #115, each fixed with a test failing on the head it reviewed:
      - **Read the example against the section above it** (Codex on #115): `font-size-adjust` switched off the `size-adjust` of the re-metricked face in the very stack the section had just built.
      - **A transition has two ends** (CodeRabbit on #115): `visibility` stays visible through a close, so a panel's links stay reachable by Tab until it ends. `inert` goes with the attribute.
      - **A census that comes in short sizes the migration wrong** (Codex on #116): a Sass function seeded with a hex counted only the hex, and a responsive array's items were not read. **A file read twice is counted twice** (CodeRabbit on #116): Astro's frontmatter was read as a script and again as markup.
      - **A deprecation range needs both ends** (CodeRabbit on #116): `npm deprecate @org/ds@">=2.1.0"` deprecates every later release too.
      - **Every name pattern must meet the ORM's spelling** (Codex on #117): camelCase columns missed the title, sort and label signals, and a Prisma `view` is no entity.
      - **Assert the formula, not a gap** (CI on #115): a 0.5px width gap between fallbacks held on Windows and failed on Ubuntu, whose fallback's aspect is close to 0.53. The test checks MDN's u = (m/m')s.
      - **Declined:** CodeRabbit's plugin-root commands in rollout.md (it withdrew the comment).
    - **The 2026-10-13 session's reviews found 14 real issues**: #119 (Codex 7, over three rounds), #120 (Codex 3, CodeRabbit 1), #121 (Codex 1) and #123 (Codex 1, CodeRabbit 1). Each was fixed with a test failing on the head it reviewed. The lessons, for any converter between formats:
      - **Write down what a format cannot hold, when the file is written**, with the values and the marks:
        - representability is not provenance: a `clamp()` added since is new;
        - a name alone hides a changed value;
        - a lost `$deprecated` fails the gate.

        Read the record from every file a config lists, in order, and from a resolver's default contexts only.
      - **Compare by meaning, then keep what the parser erases.** `oklch(88%)` is `oklch(88.0%)`, but `"serif"` is not `serif`.
      - **Keep each value's type, and the scope that carries its modes.** A duration is a FLOAT and a boolean a BOOLEAN. A token a theme sets is semantic, whatever its name.
      - **Never discard a reader's problems.** An empty result is not a clean conversion.
      - **A route must answer the words a user says.** "Tokens Studio" without "Figma" reached no skill.
      - **A rule that asks for a claim says when it holds** (#123). "Cite a law only if it applies": conversion-audit.md §11 ties the DSA to platforms and ROSCA to negative options.
      - **Resolve only the threads you answered.** A loop that resolved every open thread closed one of Codex's that had not been read yet (#123). Answer each by its id, then resolve that one.
      - **Read `check.py`'s exit line before pushing.** #121 went up with a 207-character description (the limit is 200), in the same command that read the result.
    - **The second 2026-10-13 session's reviews found 7 real issues:** #125 (one, which Codex and CodeRabbit both found) and #126 (six over two rounds). Each was fixed with a test failing on the head it reviewed. The lessons, for any tool that wraps another:
      - **A plugin resolves its package from somewhere.** better-tailwindcss resolves `tailwindcss` from its `cwd` setting, which is ESLint's folder unless set. Test from a folder that holds the *other* version (#125's fixture: the project's tools in `app/node_modules`, the other major at the root).
      - **A fixture that nests the case hides the question.** `cx()` inside `className` passed whatever the callee list held. Codex then read `cx` as missing; 4.9.0's `DEFAULT_CALLEE_SELECTORS` has it, so the claim was declined with that evidence and a standalone fixture.
      - **A checker of a format honours every way the format names a thing** (#126): an unquoted `@import url(x)`, `prefix(tw)`, a variable that gives several classes (`--spacing-4` gives `p-4`, `gap-4` and `w-4`), and a safelist (`@source inline()`) that is in the first build.
      - **A fix that narrows a pattern must keep the valid forms beside it** (#126, round 2). The lookbehind that stopped `${file}.css` from reading as an emotion tag also dropped `emotion.css`. List the valid neighbours before narrowing.
      - **Compile the doc's own example.** §2.10's block found `tw_probe`'s inline-source bug before review did.
      - **The plugin's own scripts pass the plugin's gates.** The audit reads a `.mjs` for CSS-in-JS, and `test_powershell_json` refuses `JSON.parse(fs.readFileSync(…))`. Use a BOM-aware `readJson`.
      - **A stacked PR retargeted to `main` starts CodeRabbit's review.** It is still not a gate (#127 merged with it pending).
    - **The 2026-10-14 session's reviews found 8 real issues:** #129 (Codex 4 over two rounds, CodeRabbit 2, CI 1) and #130 (Codex 1). Each was fixed with a test failing on the head it reviewed. The lessons, for any reader of a project's source:
      - **A token in a string is not a class.** `"p-4"` alone may be data, so a numeric class is read only where classes go: a class attribute, a `className={…}` expression, a class helper's arguments. Find that syntax in code only: `'cn('` is a string, not a call (`blank_js_strings()`).
      - **What the reader cannot read can change the answer.** A package an entry imports may set `--spacing`, so it is read from `node_modules`, and one still unread withholds the count rather than guessing.
      - **One rule for one question.** The colour family test (`is_neutral()`) decides the matching, so it decides the ramps' seeding too.
      - **A class name is a class, not a family.** `size-*` is a size; classing it with `p` gave icons a padding role.
      - **A file a tool rewrites keeps its bytes**, its endings included, and so does what the tool prints about it: text-mode stdout on Windows turned a CRLF diff into `\r\r\n`.
      - **Run `check.py` with `WDS_NODE_MODULES` set** to `tooling/main/node_modules`, or `test_real_tools` skips and a snippet stylelint refuses reaches CI (#129: an `@import` the snippet audit put inside `@layer components`).
      - **Stage by name.** `git add -A` staged the owner's in-progress audit into #129 (`aa95250`, removed in `b78d77b`).
    - **The second 2026-10-14 session's reviews found 13 real issues:** #132 (Codex 3 over two rounds, CodeRabbit 4) and #133 (Codex 3 over two rounds, CodeRabbit 3). Each was fixed with a test failing on the head it reviewed. The lessons, for any reader of a language's syntax:
      - **A selector list splits at depth-0 commas only.** `&:is(:hover, :focus-visible)` is one selector (CodeRabbit).
      - **A mirror rule must not widen what it matches.** `.chip:is(:hover, .danger)` mirrored with `.danger` live re-applied the hover styles to every danger chip, after the component's rules. An unforced arm becomes `arm:not(*)`, which keeps its specificity (Codex).
      - **A condition nested in a rule is that rule under the condition.** Its declarations join the rule's own (Codex).
      - **A detect list must match what the cell carries.** The focus-visible cell carries `focus-within`, so `:focus-within` covers it (CodeRabbit).
      - **A file the hook writes in a scratch tree may be a staged symlink.** Write a temp file and `os.replace` it; check `lexists`, not `exists` (CodeRabbit).
      - **Read what the reader before you erased.** The audit got JS comments stripped for `.tsx` but not for Astro markup, so the comment test must use the markup path (CodeRabbit). A spread's own object literal is set inline too (Codex).
      - **A string literal is the language's, not the parser's.** Dollar quotes (`$$a ) b$$`), a doubled `''` and runs of spaces inside a label all survive (Codex on #133, three findings over two rounds).
      - **Normalise only what the branch can bear.** Keeping string whitespace for every statement broke the `.*` patterns on a label with a newline; the enum branches match an exact form with `re.S`, the rest the collapsed line (CodeRabbit on #133).
      - **A fix's test must fail on the old code.** The dollar-quote case passed on v3.6.0 until it had a table tail (CodeRabbit on #133). Run `fail_before.py` on `v3.6.0` for every new test, not only on the reviewed head.
      - **Ask Codex once after a round of fixes** (`@codex review`): it found more on #132 and #133's second round. Then merge when the next fixes are small and tested.
    - **The 2026-10-15 session's reviews found 15 real issues:** #135 (Codex 2, CodeRabbit 1) and #136 (Codex 12 over two rounds). Each was fixed with a test failing on the head it reviewed. The lessons, for any guard over a script's inputs:
      - **Guard the files read, not the arguments typed.** Every round on #136 found the next spelling: a glob's matches, the files under a folder, every file of a snapshot, the config's token files and budgets, screenshots and their captions, a manifest's templates, `--prose`, a bundled default, a `file://` URL. Before writing a guard, list every way the script finds an input, then guard where they are all known.
      - **A proposal's rule meets files written after it.** A check over the literals the census saw does not protect a height added before the mapping is applied: the codemod must refuse it too (a `width` class of its own).
      - **One literal, one rule.** A duration in a `transition` shorthand was counted at the `--motion-*` pair and at the Tier-1 step; count each where the codemod would rewrite it (`takes_motion_pair()` follows `plan_motion()`).
      - **Run an audit finding's own fixture before fixing it.** H14's fixture staged a change against HEAD in a plain repository. The recipe stages HEAD's own version during a rebase, which is clean, so the finding did not reproduce.
      - **Declined, with evidence:** Codex read `^[a-z][a-z0-9+.-]+:` as matching `C:\site`; it needs two characters before the colon, and `test_node_agrees` passes drive paths on Windows.
    - **The second 2026-10-15 session's reviews found 12 real issues:** #138 (CodeRabbit 5, Codex 4 over three rounds) and #140 (Codex 1, CodeRabbit 2); #139 had none. Each was fixed with a test failing on the head it reviewed. The lessons, for any check of a value's type:
      - **A present value is checked as it is, before any default.** `x.get(k) or {}` reads `[]`, `0`, `false` and `""` as empty, so a wrong type passes. Default only a missing or null key (`_given()` in `build_presentation`, `is None` elsewhere), then check.
      - **Check every field the reader indexes, not only the top level.** `build_docs` indexed `stats`, each token's `raw` and `tier` and each component's sockets; the codemod `rule["match"]`; `cluster_values` five literal fields; the flat dump's `constraints` and `key_column_usage`.
      - **A number from JSON can be infinite.** Python reads `1e400` and `Infinity` as `inf`, under which every page passed: `math.isfinite`.
      - **A flag's promise binds new output.** `--quiet` says "do not print warnings", so a new warning follows it.
      - **Name what cannot be measured, for every reason.** A translucent pair was still skipped silently, and two output formats carry no notes, so they print on stderr.
    - **Staged changes travel with `git checkout`:** the session's draft docs, staged on another branch, rode into #102's last commit. Commit or stash before switching branches, and read `git diff --cached --stat` before every commit.
    - **The evals find router bugs.** `test_evals.TheRouterAgrees` runs the router on every case's prompt for free; the real run found a third (a hyphenated "screen-reader" heard nothing).
- **Shell.**
  - The Bash tool is Git Bash. Any command you give the user must work in cmd.exe.
  - **The desktop app is an MSIX package**, so its `AppData\Roaming` is really `C:\Users\vybec\AppData\Local\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming`. Claude's tools see the bundled CLI at `%APPDATA%\Claude\claude-code\2.1.295\d2e29494ec83\claude.exe`; the owner's terminal does not ("cannot find the file"). Give the owner the real path. The credentials are in `C:\Users\vybec\.claude`, which both see. On 2026-10-13 the CLI's sign-in had expired (`auth status` said `"loggedIn": false`); the owner ran `claude.exe auth login` with the real path.
  - **The terminal tool** (`run_in_terminal`) reported a long command as unfinished while it was in fact running `auth login`, and closing the tab cancelled the sign-in. Read the tab before closing it.
  - **Bash heredocs eat backslashes** (`\\` becomes `\`, `\n` becomes a newline), even quoted ones. It bit three times last session: a `\n` in a test became a real newline, and an edit script failed to match.
    - Write any script or test code that holds a backslash with the Write tool into a scratch `.py` file, and run that. Or use the Edit tool, which is safe.
    - The Edit tool drops a trailing space at the end of `new_string`: an `old_string` ending in a space turned `new = (` into `new =(` last session. Read the staged diff.
  - **Python's `write_text` writes CRLF on Windows.** Edit files with `read_bytes`/`write_bytes`, or the Edit tool. A CRLF SKILL.md also breaks its byte budget.
  - Run Python with `-B`.
  - **`spawnSync` keeps 1 MiB of output by default.** Give a script whose output can grow a `maxBuffer`, and check `proc.error` before parsing (CodeRabbit on #82).
  - **Resolve a path before `path.relative()` against a config's root**: the root is resolved, and macOS's `/var` and Windows runners' `RUNNER~1` are not (CI on #82).
  - `_winapi.CreateJunction` needs the link's parent folder to exist.
  - **Don't edit a file the suite reads while it runs.** Plan docs are safe. The CHANGELOG, README, references, configs, scripts, tests and the spec are not. To change them mid-run, stop the run (`TaskStop`) and run it again.
  - **Stage a new file before `check.py`**: `test_file_modes` reads git's index. A new script with a shebang needs `git update-index --chmod=+x`.
  - **A `*/` in a glob closes a JS block comment** (`emails/**/*.html` inside `/** … */` broke `design_hooks.mjs`). Write the glob out in words there.
  - **A test that rewrites recorded data must not lean on this platform's own form.** N38's first test swapped `/` in keys that Windows had recorded with `\`, so it passed before the fix on Windows. Build the platform's form explicitly, and run `fail_before.py` to see each test fail.
  - **`test_docs.PasteableCommands` refuses a `*` in a README command**, quoted or not, since cmd and PowerShell must paste it too. Name the tools instead of a glob. Run `test_docs` after any README edit.
  - **YAML frontmatter:** a value with `: ` in it (`GT-C10: a clean…`) is not valid YAML, and the eval CLI refuses the case. Quote it.
  - **`check.py` prints only the first failure's traceback.** When it reports more failures than it shows, run `python -B -m unittest discover -s tests > suite.txt 2>&1` in the background and grep `^FAIL:`.
  - **`test_harness` requires `env=`** on every subprocess a test starts (`env()` from `wds_support`).
  - **A test that loops over files must assert it found some**, or it passes vacuously on a plugin without them (`fail_before.py` shows it as a control).
  - Redirect a background `check.py` to a file in the scratchpad (`> check.txt 2>&1`), not through `tail`. Give it `timeout` 3600000.
  - Run a single test module from `tests/` (`cd tests && python -B -m unittest test_x`); `tests.test_x` from the plugin root does not import.
- **Fail before, pass after.** Every fix gets a regression test, seen failing on the previous release's tag and passing now.
  - Run `python -B tools/fail_before.py TEST_IDS` from `plugins/web-design-suite`. The default REV is the latest `v*` tag, **`v3.6.0`** until R4. For a PR that builds on unreleased work, also run it against `main`'s head, with the **full** SHA: that table shows what the PR itself fixed (#78 and #79 did both).
  - A review fix runs against the head it fixes, with the **full** SHA. In the Bash tool that is `--rev $(git rev-parse SHORT)`; a short one is refused.
  - **`fail_before.py` swaps the plugin, not the tests**, so a fix to test code shows as a control: say so.
  - Run a new browser test several times, in Playwright's Chromium and in the installed Chrome, before you push it.
- **CI replaces the local full runs (decision D1, in force).** Locally, `python -B tools/check.py`: about 10 minutes when a shared file changes, since `project_config.py` and `browser_common.mjs` reach most test modules.
- **One set of rules.** A change to what a gate accepts goes into `skills/web-design-studio/assets/rules/design-rules.json` first, as `allowed` and `refused` examples. `tools/sync_rules.py` writes the data the gates restate. The three gates change together; when one cannot yet, the gap is recorded as an item and scheduled (N37 is the example).
- **Facts from outside** are re-read at their source on the day.
  - A figure (a number from a study, a survey, a vendor or a regulator) goes into `tests/fixtures/evidence.json` with its quote, for every doc that quotes it.
  - A rule that is not a figure (an API's behaviour) is quoted in the doc and the PR, with its URL.
- **New `§` pointers** are registered with `python -B tools/check_pointers.py --write-register`. Read the register's diff.
- **The plan's checker** counts an item as scheduled only in a row whose first cell is a bare `Pnn`. A row named `P25 part 1, #82` is done, so a part still to come is a row named `P25`.

## 1. Orient (keep it under about 40 thousand tokens)

1. Read the repository's `CLAUDE.md` and `docs/HANDOFF.md`.
2. Read the execution plan's §2 and §6, and its Phase 6 tables in §4 (P31 to P55 and R4: each item's scope and main files). Phase 6c is the audit: read the audit's §6 and §7, and each finding a PR closes, never the whole file at once.
3. Read `dev plans/web-design-suite-review/claude-code-capabilities.md` §2, §3, §6 and §8. §6 is the hooks re-read (P25), and §8 the 2026-10-09 re-read of the sub-agents page, with `/critique`'s choice to delegate in its body.
   - §9 is the 2026-10-10 re-read of the MCP page and the manifest reference's `mcpServers`, `lspServers` and `bin/`, with the MCP server's and the LSP spike's decisions, and the owner's no to `bin/`.
   - §1 is the plugin-evals page, §10 P29's choices, and **§11 the sandboxing page and P30's choices**, with the first runs. Read §11 if you touch the evals.
   - The two live checks, `dev plans/web-design-suite-3.5.0-live-check.md` and `web-design-suite-3.6.0-live-check.md`, show how a release is checked; read them before R4.
4. Check the state, with the Bash tool:
   ```bash
   cd /c/DEV/Pro-Web-Designer-Suite-Plug-in && git fetch -q && git status --short && git log --oneline -3 origin/main && gh pr list --state open && git worktree list
   ```
   - Check out `main` and pull. Remove any worktree left in the scratchpad (`git worktree remove PATH`, then `git branch -d` its merged branch).
5. `python -B "dev plans/check_execution_plan.py"` must say `22 open items, 22 scheduled`.
6. Tell the user, in a few lines: the state, what this session does, and the budget.

## 2. Useful facts

- **Part 5, the Tailwind lint block (#125, D4).**
  - One commented block for eslint-plugin-better-tailwindcss 4.9.0. Tailwind v4 reads `entryPoint`, and v3's `tailwindConfig` line takes its place.
  - `cwd: project`, the nearest folder above the config with a `package.json`; both paths are anchored there.
  - `detectComponentClasses` (v4: `@layer components` classes are known), and `getDefaultSelectors()` plus `classHelpers` (`classNames`, `classnames`).
  - `ownClasses` entries are anchored `^…$`, because the rule tests them unanchored.
  - The rules: `no-unknown-classes` (`ignore: ownClasses`), `no-conflicting-classes` (v4 only), `enforce-shorthand-classes` (warn), `no-duplicate-classes`, `no-deprecated-classes`. No `recommended` config, no order rules.
  - `wds_support.tailwind_part5(text, major)` uncomments it, swapping the v3 line in. `test_real_tools.TailwindPluginV4`/`V3` run it from a folder that holds the other major; `test_recipes.DependencyFacts` holds the rule names to 4.9.0's README.
  - Both tooling folders pin better-tailwindcss 4.9.0.
- **`tw_probe.mjs` (#126, #127)** is in web-design-studio's `scripts/`, Node 20.19+ with the project's tailwindcss 4 (the `node_modules` above the cwd, then `NODE_PATH`).
  - `ownSheets()` reads the stylesheets in cascade order, each after its imports, with Tailwind's own files left out. `themeVariables()` follows the `@theme` blocks, clearing on `--*: initial`.
  - `NAMESPACES` maps a variable to its class (tailwindcss.com's table). `STOCK` holds each sample class with its hint and the variables that make it the project's own.
  - `withoutInline()` sets `@source inline()` aside. The `prefix(x)` of an `@import` or `@theme` is applied to the automatic candidates.
  - One compiler, the candidates added one at a time; `selectorCount()` with `cssEscape()`.
  - Exit codes: 0, 1, 2 (Tailwind 3 is 2).
  - `/web-design-suite:tw-probe` runs it, and stack-tailwind.md §2.9 teaches it. §2.10's marked block (`<!-- tw-probe:variants -->`) is compiled by `test_tw_probe.TheVariantsTheReferenceTeaches`, whose `COMPILE` harness compiles a module on its own.
- **The v4 census (#129).** `extract_literals.tailwind_theme()` finds each stylesheet importing `tailwindcss` (or `tailwindcss/utilities`); `tailwind_spacing()` follows its imports in order, a package's through `_package_sheet()` (the nearest `node_modules`: its subpath, `style`, or `index.css`), skipping URLs.
  - It applies the theme as Tailwind builds it: `--*: initial`, `--spacing-*: initial` and `--spacing: initial` clear `--spacing`, and a `default` block never overrides the project's. The stock value comes from the installed `theme.css`, else `TW_STOCK_SPACING` (`0.25rem`).
  - It counts nothing when entries disagree, `--spacing` is no length, or an import is unread; `problems` says why, and the JSON's `tailwind` block names the entries.
  - `tailwind_literals()` reads each class token (`TW_TOKEN_RE`, `tw_utility()`, `tw_multiplier()`, `TW_NUMERIC_RE`, `TW_NEGATIVE_UTILITIES`) as context `tailwind-spacing`, raw `utility` or `prefix:utility`. In a script it reads them only in `class_list_spans()` (a `className={…}` expression, `CLASS_HELPERS`' arguments, found in `blank_js_strings()`' code).
  - `cluster_values.TW_CONTEXTS` and `tw_utility_prefix()` build the rule (`p-4` to `p-well`); `tw_prop_class()` puts `size` with the sizes and `leading` apart. `apply_codemod.plan_classes()` rewrites a numeric class token by token, the utility only, and an arbitrary one with both boundaries (C1).
  - Tests: `test_token_migration.TheV4SpacingCensus`, `test_tw_probe.TheMigrationsMoveOne` (§5's marked blocks `<!-- tw-migrate:wrong -->` and `right`, the import added by the test).
- **Colour families (#129, N40).** `cluster_values.is_neutral(L, C, H)`: chroma under `NEUTRAL_SHARE` (0.5) of `max_chroma(L, H)`, sRGB's. `nearest_ramp_step()` lands a neutral on the neutral ramp only and any other colour on a step within `HUE_GUARD_DEG` of its hue, ΔE within. `cluster_color_phase()` seeds the accent and the neutral hue by the same test. `test_token_migration.ColoursKeepTheirFamily`.
- **Line endings (#130).** `apply_codemod.process()` and `deprecate.inject_marker()` read with `newline=""`; the marker takes the file's dominant ending, `save_ledger()` keeps the ledger's, and the dry run's diff goes to `sys.stdout.buffer`. `test_token_migration.TheCodemodRewritesOnlyWhatItMatched`, `test_versioning.TheMarkerKeepsTheFilesLineEndings`.
- **The CSS reader in `a11y_static` (#132).** `css_rules(src, line_of)` returns every style rule at any depth as `(selector, line, body, offset)`. Each body keeps its own declarations, nested blocks blanked. A conditional group nested in a style rule is read with the rule's own declarations overlaid. `_nest()` resolves `&` (`_selector_list()`, depth-0 commas). `audit_css()` blanks comments with their newlines kept and reports a `(line, rule, message)` once. `FOCUS_VISIBLE` and `FOCUS_VISIBLE_PREFIXES` decide a visible focus rule. `test_content_and_a11y.A11yStaticReadsNestedRules`.
- **Bound attributes (#132).** `a11y_static.bound_attr(raw)` maps `:x`, `v-bind:x` (`.prop`, `.attr`, `.camel`), `[x]` and `[attr.x]` to `x`. A quoted string literal is read as its text, anything else as `EXPR`. `@click`, `v-on:click`, `on:click` and `(click)` become `onclick`, and `[class.x]` gives no key. `NG_BINDING` matches Angular's forms. `A11yStaticReadsBoundAttributes`.
- **The matrix's mirrors (#132).** `generate_matrix.transpose_part()` rewrites a state at depth 0 and inside `:is()`/`:where()`, recursively; an unforced arm of a group that holds a state becomes `arm:not(*)`. `nest_selector()`, `force_rules()` (shared by `build_force_shim()` and `forced_states()`) and `detect_states()` count a forced state only when a mirror was written. Focus-visible's `detect` includes `:focus-within`. `MatrixStates`, `test_browser_runtime.MatrixSeesStateChanges`.
- **The hook's index mode (#132).** `pre-commit-design-gate.sh` copies `.design-suite.json` and the default baselines into `AUDIT_ROOT`. An inline Python rewrites the scratch config: an unstaged token or budget file becomes the working tree's absolute path, and a baseline is copied to its own relative path, since the audit's keys are relative to the baseline's folder. It writes a temp file and `os.replace`s it. `test_precommit_hook.PreCommitHook`; the symlink test skips on Windows without the right.
- **Style-object keys (#132).** `audit_design.style_object_keys(inner)` blanks comments, then takes each depth-0 entry's key. `spread_keys()` reads a spread's own object literals (not a name, a call's argument or an array). `_audit_jsx_styles` reads the object inside `{{ … } as X}` too. `JsxClassesAndCssInJs`.
- **The schema reader (#133).** `introspect_schema.one_line_outside_strings()` collapses whitespace outside string literals only. `RE_ALTER_ENUM_ADD` and `RE_ALTER_ENUM_RENAME` change an enum the files created; `enum_label()` unescapes `''`. `_balanced_slice()` skips strings and `$$` bodies, and ends a `CREATE TABLE`'s column list. `test_schema_sources.MigrationsThatDumpsRewrite`.
- **`--reverse` and a theme (#133).** `reverse_body()` pass 3 adds a `dropped` problem (`"{token} [{Theme}]"`) for a theme's value that cannot cross; the exit is 1. `test_figma_sync.ReverseReadsEveryTokenFormat`.
- **A BOM (#133).** `extract_system`, `build_docs` and `diff_system` read with `utf-8-sig`. `test_project_config.ABomOnTheTokenFile`. The wider encoding class (UTF-16, every script) is P53's.
- **The reconciliation (#135).** `cluster_values` adds an `Unmapped` row for every census value it cannot place:
  - a colour no cluster took (`clustered`);
  - non-`em` tracking;
  - a `color-mix()` colour function, with its own advice;
  - `project_ramps()` names a step it cannot read, or a translucent one.

  `takes_motion_pair()` follows `apply_codemod.plan_motion()`, so a duration counts at one rule. `WIDTH_PROPS` gates the `--width-*` snap, and a width rule's `prop_classes` is `["width"]`, which `apply_codemod.PROP_SLOT_CLASS` gives only `width`, `min-width` and `max-width`. `extract_literals.mixes_a_literal()` decides a `color-mix()`, claimed before the hex pass. `test_token_migration.TheProposalAccountsForTheCensus`, `ApplyCodemodDirtyGuard.test_the_rebase_recipe_migrates_the_teammates_version`.
- **UTF-8 out (#135).** `test_utf8_output.writes_utf8()` reads each entry script's `__main__` block with `ast`: a `reconfigure(encoding="utf-8")` over `sys.stdout` and `sys.stderr` before `main()`. Scripts in `skills/*/scripts` and `workflow-commands/*/scripts`; a library has no `__main__` block. CI's "Pydantic runs the scaffold's model" step sets `WDS_REQUIRE_PYDANTIC`.
- **The `--out` guard (#136).**
  - `project_config.refuse_overwrite(out, *inputs)` returns the message, or None. It compares by `os.path.samefile` when both exist, else by normcased realpath, and skips `-`.
  - `browser_common.refuseOverwrite(out, ...inputs)` does the same with `dev:ino` and a case fold on win32. It reads a `file://` URL as its file and a web URL as none.
  - `critique_report.py` and `generate_matrix.py` carry the Python function verbatim (`TheGuardIsShared`).
  - `diff_system.Snapshot.sources` lists every file a snapshot read. `generate_matrix.Manifest.templates_path` keeps the templates file.
  - `test_out_guard.CASES` and `NODE_CASES` are the table: one row per writer and per way of finding an input.
  - Not guarded, by decision: `figma_to_tokens` over `--tokens` (the Figma-to-code workflow), and the folder writers (`build_docs`, `scaffold_ui`, `new_system`) and snapshot writers.
- **The JSON type guards (#138).**
  - `tests/test_json_guards.py`: `CASES` and `NODE_CASES` hold one row per loader, fed `[]`, `"x"`, `5` and the row's own wrong keys. `LISTS` names the loaders where `[]` is valid. `test_the_table_reaches_every_loader` fails on a script that reads JSON (`json.loads(` or `readJsonFile(`) with no row and no exemption.
  - The checks:
    - `dtcg._bad_type()` and `_own_deprecated()`, and `badType` in `readTokens()`;
    - `perf_audit.budget_problem()`, ported as `measure_vitals.mjs`' `budgetProblem()`, and `_number()` (finite);
    - `check_roles.valid_pairs()`, `critique_report._flag()` and `_count()`;
    - `build_presentation._given()`, `_object()` and `_objects()`, `build_docs.system_problem()`, `apply_codemod.rules_problem()`, and `introspect_schema`'s `objects()`.
  - A baseline of the wrong shape prints "could not read baseline … auditing everything", as an unreadable one did.
- **The encoding readers (#139).** `project_config.decode_text()`, `read_text()` and `text_encoding()`; Node's `jsonText(buf, fatal)` reads CSS non-fatally. `audit_design`, `a11y_static`, `check_roles` and `generate_matrix` carry a local `_read_text()`. `test_encodings.NoScriptReadsUtf8Only` allows only `install_gate`'s `TEMPLATE.read_text`.
- **The diagnostics (#140).**
  - `ProjectTokens.problems` (strings `file: token: why`), and `read_deprecations(paths, problems)` collects them when it is given a list.
  - `figma_common.out_of_srgb()` and `left_out()`.
  - `diff_system.contrast_deltas(..., unmeasured)` names a pair that a changed token reaches and that is unresolved, translucent or unparseable.
  - `test_diagnostics.NoProblemListIsDropped` scans for `_problems`, and for `[0]` on `tokens()` or `normalise()`.
- **DTCG (#101, #102).** `shared/dtcg.py` is the master, copied beside every `project_config.py` (`test_dtcg.TheCopiesAreTheMaster`); `project_config.py` loads the copy beside it by path. `normalise()` (the Figma scripts' reading, string forms) and `tokens()` (lossless, CSS names) read 2025.10 and Tokens Studio (`studio_document`, `studio_themes`); `document()` writes 2025.10 from CSS custom properties. `project_config.mjs` ports the reading, numbers formatted as Python's `f"{round(x, 6):g}"`, and `TheNodeReaderAgrees` holds them equal on every value form. `figma_common.parse_studio` makes each Studio theme group a collection; `FVar` carries `deprecated`, `dtcg_type` and `partial`.
- **The resolver (#105).** `dtcg.resolver_document(data, base, inputs, only)` merges a resolver's `resolutionOrder` for a choice of contexts (each modifier's string `default`, else its first, which is reported); `resolver_modifiers()`, `token_paths()`, `resolver()` (the writer), `outside()` and `file_loader()` (its real path must stay in the folder, else `OutsideFolder`). `figma_to_tokens.py --format dtcg --out-dir` writes `tokens.json`, `theme-<x>.json` or `density-<x>.json` (overrides only, `document(only=...)`) and `tokens.resolver.json`; `css_blocks()` and `figma_blocks()` feed `dtcg_files()`. `figma_common.parse_resolver()` makes each modifier a collection with `FCollection.kind`, and `mode_selector(mode, default, kind)` writes a theme or density context as the value itself (`css_escape`). Unreadable sources are `FDoc.unread` (`unread-source`, `UNREAD_SOURCE`). The Node port is `resolverDocument()` in `project_config.mjs`.
- **The ledger (#106).** `project_config.read_deprecations(paths)` and `replacement_of(reason)`; `diff_system.marked_deprecations()` adds a record (`"marked"`) for each token the old DTCG snapshot marks; `deprecate.py import FILE… --since --removal`.
- **The names (#107).** `.design-suite.json`'s `names`: `prefixes` (each ending in `-`) and `rename`. `ProjectConfig.grammar_name()`, `grammarName()` and `lintProject().grammarName`; the audit's `tier1_advice`, stylelint's and ESLint's `tier1Advice` read through it, and ESLint's `NAMED_SHORTHAND` covers `(--name)` classes. The spec's `tiers.names` holds the examples; `test_real_tools.TheGatesReadTheNames` runs them.
- **Figma on every plan (#109, #111).** `figma_to_tokens.py --reverse --format plugin-script` writes `reverse_body()`'s REST body as Plugin API code (`PLUGIN_SCRIPT`): found by name, created or updated in place, nothing deleted, the default values always on `defaultModeId`, counts and the first 20 errors returned, as `use_figma` runs it (top-level `await` and `return`). `figma_common.PLAN_MODES` (starter 1, professional 10, organization 20, enterprise 40) and `REST_MODES`; `figma_audit.py --plan` or `.design-suite.json`'s `figma.plan` reports `MODE_LIMIT` and quiets `MISSING_DARK_MODE` on Starter; `--reverse --format plugin-script --plan` reports `mode-limit`; a REST body past 40 modes is not written (exit 2). `test_figma_sync.PluginScript` runs the script under Node against a stub `figma` (`FIGMA_STUB`); `PlanLimits` the limits. `figma-mapping.md` §14 has the Plugin API table, each plan's limits and the seats.
- **`light-dark()` (#112).** `check_roles.py` measures each pair once per visitor preference: `used(env, preference)` gives a scope's scheme (one named alone, the preference under `light dark`, light under none), `scopes()` resolves `color-scheme`'s `var()` once every block on its element (root, band) is in, and `rules()` reads one `@supports`, the positive query `LIGHT_DARK_QUERY`. Each result carries `scheme`, and `preference` when it depends on it. style-architecture.md §10 teaches it, and `test_check_roles.LightDarkInABrowser` runs its example (marker `<!-- light-dark:example -->`) in Chromium.
- **`tests/test_modern_css.py` (#113)** runs the references' modern-CSS snippets in Chromium on the starter's tokens (`reference_block(name, needle)`, `PROBE_JS` with a scenario argument): hit tests and Chromium's accessibility tree through CDP (`Accessibility.getFullAXTree`). #115 added `cqi`, `font-size-adjust`, the alpha variants and the disclosure (its toggle, a ```js block, runs in the page; `reference_block(name, needle, lang)`); `TheReferencesReadAlone` holds the checks that need no browser.
- **The migration census (#116).** `extract_literals.py` reads `.vue`, `.svelte`, `.astro` and `.html` (`MARKUP_EXT`): each `<style>` block in its `lang` (`style_blocks()`), scripts and Astro's frontmatter as JavaScript (`script_blocks()`), `style=""` and `class=""` (`extract_markup()`). `object_style_literals()` reads `sx`, `css`, `styled({})`, vanilla-extract and Panda (`STYLE_PROPS`, `STYLE_SHORTHANDS`); a number in `sx` or Panda is a theme step, so only strings count. `cluster_values.HAND_WORK` sets inline styles and style objects aside. `apply_codemod.py` rewrites the style blocks (`plan_markup()`). `test_token_migration.TheCensusReadsEveryStyleSource`.
- **Prisma and Drizzle (#117).** `introspect_schema.py` parsers 4 and 5, `parse_prisma()` and `parse_drizzle()` (pg-core only; `_ts_args()` is string-aware), chosen by `detect_format()` or `--format`. Each fidelity block names its losses (Prisma: no CHECK, views left out). `_n()` (`_NamePattern`) matches the snake_case signals on camelCase names, and `_canonical()` and `humanise()` read them too. Fixtures `tests/fixtures/supabase/shop.prisma` and `shop.drizzle.ts`; `test_schema_sources.OrmSchemasReadAsTheMigrationDoes`.
- **The DTCG record (#119).** `dtcg.document()` keeps each token it leaves out, with its CSS value, in the document's root `$extensions` (`dtcg.EXTENSION`, `io.github.vybecode-ltd.web-design-suite`). `notWritten` holds the values, and `deprecated` the marks it could not carry. The readers are `not_written()` and `not_written_marks()`.
  - `diff_system._snapshot_from_contract()` restores them through `recorded()`: from every path, in order, and from a resolver's `dtcg.default_sources()` only.
  - `_equivalent()` compares two spellings through `css_value()`, part by part for an untyped value; `_families()` keeps a quoted keyword distinct.
  - `align_spellings()` runs before the diff.
  - `test_dtcg.ASnapshotAgainstItsStylesheet`.
- **`--reverse` from any token format (#120).** `figma_to_tokens.reverse_data()` turns a `tokens.css`, a DTCG document or a resolver into `read_tokens_json()`'s tiered shape:
  - each `[data-theme]` block, or each context of a resolver modifier named for a theme, scheme or mode, is a mode;
  - each entry carries its Figma type (`REVERSE_TYPES`, or a CSS duration);
  - a themed token is semantic;
  - the reader's problems are reported (`not read`, `not carried to Figma`).

  `reverse_main()` serves the REST body and `--format plugin-script`. See `test_figma_sync.ReverseReadsEveryTokenFormat`.
- **The plugin** is `plugins/web-design-suite/` (about 1,223 tests):
  - `skills/`: 13 skills.
  - `tests/`: standard-library `unittest`. The helpers are in `tests/wds_support.py`: `PLUGIN`, `SKILLS`, `NODE`, `run_py`, `run_node`, `load_script`, `env`, `TempDirTest`.
  - `tools/`: `check_pointers.py`, `sync_snippets.py`, `sync_rules.py`, `fail_before.py`, `check.py`.
- **The project contract (P24, #76, #78, #79, #81).** `references/project-contract.md` in web-design-studio is the user-facing account. In short:
  - **`.design-suite.json`.** `schema: 1` is required. The other keys are `tokens`, `emailTokens`, `components`, `stack`, `budgets` (`perf`, `a11y`) `baselines` (`audit`, `a11y`, `perf`, `docs`, `snapshots`) and `hooks` (`designGate`, `generatedFiles`, `tokenDiff`, `a11yGate`, `emailBuild`, booleans; #82, #84, #91).
    - `emails` (#91): the email templates' globs, read as `components` is; `emails/**/*.html` when left out, `[]` for none. `ProjectConfig.is_email()`, `isEmail()`.
    - Found by walking up from the working directory, never past the folder that holds `.git`. Paths are relative to the file, normalised.
    - A flag beats it, and it beats the default. A mistake exits 2 with the key named.
  - **`shared/project_config.py`.** The API:
    - `find_config`, `load_config`, `project_config`, `config_path(config, section, key)`, `token_sources(flag)`;
    - `read_contract`, `read_tokens(paths)`, which returns a `ProjectTokens` in the contract's sections, from a contract.json or a tokens.css;
    - `ProjectConfig.is_component(path)` for the globs.

    It is copied beside the scripts of **ten** skills. `test_project_config.TheCopiesAreTheMaster` finds the readers by their `from project_config import` line. A tokens.css is read by its defaults, with tiers by value; the eight names on the starter where that differs from extract_system's name-first tiers are pinned by a test.
  - **`shared/project_config.mjs`** (#81) is the Node reader: `findConfig`, `loadConfig` and `projectConfig`, with the same checks and messages, `readTokens()` (a port of `read_tokens`), `isComponent()`, `overrideGlobs()` (the components globs as micromatch globs, for stylelint) and `lintProject()`, which the two lint configs call.
    - `browser_common.mjs` re-exports its config reader. **Seven copies**: the five browser skills' `scripts/`, web-design-studio's `assets/configs/`, and `hooks/`. `TheCopiesAreTheMaster` finds them by their `from './project_config.mjs';` line.
    - `TheNodeReaderAgrees` runs both readers on 27 configs, 18 token-file lists and 29 globs; `test_real_tools.TheGatesReadTheProject` runs stylelint, ESLint and the audit in a project with and without a config.
    - **After every merge from below, copy both masters over every copy**: git merges each copy separately (it happened three times this session, to `hooks/project_config.mjs`).
  - **The hooks (#82).** `hooks/hooks.json` runs `node hooks/design_hooks.mjs guard|gate|route` in exec form. The gate and the guard act only where `.design-suite.json`'s `hooks` turns them on; `userConfig.design_hooks` (`CLAUDE_PLUGIN_OPTION_DESIGN_HOOKS`) turns all three off. The gate finds Python as the pre-commit hook does (`WDS_PYTHON`, else `python3`, `python`, `py -3`, each asked for major version 3). `tests/test_hooks.py` feeds each the JSON Claude Code sends.
  - **The token diff (#84).** In the `gate` mode, after an edit to one of the config's `tokens` (resolved paths compared), with `hooks.tokenDiff` and an existing `baselines.system`, it runs `diff_system.py <snapshot> --format json --gate none` in the config's folder. Claude hears only majors and contrast crossings. A token file outside the project is found through the config at the hook's `cwd`. A broken config is reported for an audited file, or for a token file it names (read through the reader's exported `readJson`, any encoding). `diff_system.py` without `old` reads `baselines.system`, and compares components only when both snapshots carry them.
  - **The a11y gate and the email build (#91).** In the `gate` mode too. `a11yGate`: `a11y_static.py <path relative to the config's folder> --json` there (its baseline keys hold the path so), on the files it reads (`A11Y_READ`, held to its `AUDITABLE_EXT`), its findings after the audit's under the shared `LIMIT`. `emailBuild`: on a file `isEmail()` matches, `lint_email.py --source`, `build_email.py --out` into `os.tmpdir()` (removed after), `lint_email.py` on the build; errors listed, warnings counted. The scripts one edit starts share `BUDGET`, 160 seconds, inside `hooks.json`'s 180. The email hook lints as for marketing mail: a receipt with no unsubscribe link is reported.
  - **Who reads what:** the reference's §3 (the token scripts) and §4 (the other keys).
  - **Vendored alone:** `audit_design.py` and `a11y_static.py` (the hook recipe copies them into a project's `scripts/`) run as before without the reader; the audit says the config is not read and refuses `--tokens`.
- **The workflow commands (#85)** are skills in `workflow-commands/<name>/SKILL.md`, which `plugin.json`'s `"skills": ["./workflow-commands/"]` adds to the scan. They stay out of `skills/` so the 13 skills, their tests and their `.skill` release files are unchanged (the reasons are in `claude-code-capabilities.md` §7).
  - Each has `disable-model-invocation: true` and an `allowed-tools` list of `Bash(python "${CLAUDE_SKILL_DIR}/scripts/X" *)` and its `python3` form. Every command its body runs must be one it allows (`test_commands.TheCommandFiles`, which parses the frontmatter with js-yaml from `tooling/main`).
  - `/gate` (`run_gates.py`): `audit_design --strict`, `a11y_static --strict`, `perf_audit` on `--dist` or `dist/`/`build/`, one verdict.
  - `/install-gate` (`install_gate.py`): vendors ten files from three skills into the project's `scripts/`, with `scripts/design-gates.json` (SHA-256s, the version), and writes `.github/workflows/design-gates.yml` from `templates/design-gates.yml`. The jobs are `gates` (Linux, `mcr.microsoft.com/playwright:v<project's pin>-noble`, `apt-get install python3`), `windows` (the static gates) and `baselines` (`workflow_dispatch`, `update-baselines`). `TESTED_PLAYWRIGHT` must equal `tooling/main`'s playwright (a test holds it).
  - **Sixteen commands now** (#85, #87, #88, #89, #126): gate, install-gate; new-system, contrast, migrate, release-check, figma-sync, docs-check; schema-to-screens, email-build, deck, gate-a11y, gate-perf, gate-matrix; critique; tw-probe (a chain whose step runs `tw_probe.mjs` by `${CLAUDE_PLUGIN_ROOT}`, placeholders `ENTRY` and `OPTIONS`). `gate`, `install-gate`, `new-system`, `release-check` and `deck` have runners in their own `scripts/`; the other ten are chains whose body runs the skills' scripts by `${CLAUDE_PLUGIN_ROOT}/skills/<skill>/scripts/<script>`, browser steps through `node`. A command that writes reports puts them in its own folder under `design-reports/` (`release`, `migration`, `docs`, `figma`, `screens`, `email`, `deck`, `critique`, `a11y`, `perf`, `matrix`), never `build/` or `dist/`, which `/gate` reads as the build; `/gate`, `/contrast` and `/install-gate` write none.
  - `TheCommandFiles` checks every command in a body's bash blocks starts with a rule's prefix, every rule is run, and each `python` rule has its `python3` twin. `ChainTest` runs a body's commands in order on a fixture with each placeholder (`PLACEHOLDERS`) given the test's values; `TheBrowserSteps` runs the browser steps with the tooling's Playwright.
  - **The commands have not run in a live session either**: before R3, invoke each from `claude --plugin-dir plugins/web-design-suite`.
- **The subagents (#89)** are `agents/*.md`: `design-critic` (design-critique-gate preloaded, `omitClaudeMd: true`, returns one JSON block), `gate-runner`, `a11y-auditor`, `design-auditor`, `supabase-security-reviewer`, `codemod-batch-reviewer`. None has Edit or Write, but each has Bash for the skills' scripts, so "read-only" is an instruction, not a sandbox. `test_agents` holds their frontmatter to the fields a plugin agent honours, their preloaded skills, and every script they name. `/critique` delegates to the critic in its body (the skills page documents `context: fork`'s `agent` only for built-in and `.claude/agents/` agents). They have not run live either.
- **The MCP server (#92)** is `mcp/design_gates.mjs`, run by `.mcp.json` as `node ${CLAUDE_PLUGIN_ROOT}/mcp/design_gates.mjs`; Claude Code registers it as `plugin:web-design-suite:gates`. MCP over stdio, a JSON message per line, Node's standard library, Python found as the hooks find it (`WDS_PYTHON` first).
  - Five tools: `audit_design`, `a11y_static`, `perf_audit`, `check_roles`, `diff_system`, each `mcp__plugin_web-design-suite_gates__<tool>`. A tool runs its script in `CLAUDE_PROJECT_DIR` and returns `{tool, exit, verdict, report}`; exit 2 or no JSON is an `isError` result.
  - `TOOLS` holds each tool's `script`, `properties` (its schema) and `args()`. Positionals follow `--` and option values join with `=`, so a path never becomes an option.
  - `fit()` keeps a result within 60,000 characters: the longest list reached through objects is cut to the head that fits, then the next, and `truncated.lists` names each.
  - `tests/test_mcp.py` speaks to it as Claude Code does. `claude plugin validate --strict` on `plugin.json` reads `.mcp.json` (on the plugin folder it validates the `marketplace.json` beside it instead); the test runs it when the desktop app's CLI exists, and CI has its own validate job.
- **The evals (#95).** `evals/routing/<skill>/` (13) and `evals/boundaries/<skill>-not-<sibling>/` (10), each a `prompt.md` (frontmatter: `description`, `expected_outcome`, `tags: [routing]` or `[routing, boundary]`, `max_turns: 10`, `allowed_tools: [Skill]`) and `graders/fires.md`, plus `graders/not-<sibling>.md` (`min: 0`, `max: 0`). Every grader is `arm: both`.
  - `tests/test_evals.py`: `TheCaseFiles` (the page's fields, js-yaml), `TheRoutingCases` (every skill, every pair each way, each `input_match` run in node), `TheRouterAgrees` (the router on every prompt), `TheWorkflow` (the job's steps run under bash with a stand-in `claude`). `PAIRS` holds the five pairs.
  - The run: from `plugins/web-design-suite`, `claude.exe plugin eval . --tag routing --runs 3 -j 4 --ablation none --trust-plugin --no-publish --threshold 1.0 --max-cost-usd 14 --model claude-sonnet-5-5 --judge-model claude-haiku-5-5 --output-dir <scratchpad>`: 69 runs, about 330 seconds and $5.60. `--case NAME --runs 1` for one. `--keep-temp` keeps each run's folder under `%TEMP%\claude-eval-*`: read only its `out/trace.jsonl`, then delete it.
  - `evals.yml`: `gh workflow run evals.yml --ref main -f tag=routing -f runs=3` (the owner's OK first: it bills `ANTHROPIC_API_KEY`). It runs one case at a time: 18 minutes and $4.11 for the first dispatch, 23 of 23. Its summary is on the run's page and `eval-results` is the artifact.
  - The router runs in every eval session (the plugin's hooks load); the MCP server does not start under the default `--mocks record`.
- **The outcome evals (#97, P30).** `evals/<area>/<case>/` for `build`, `systems`, `gates`, `lifecycle`, `persuasion` and `delivery`, tagged `[outcome, <area>]`.
  - **The files:** a case that needs a project has `case.yaml` (`context.scaffold_script: scaffold.sh`) and `scaffold.sh`, which copies the case's `files/` into the workspace.
  - **The graders:** the result graders are `arm: both`; the skill and the gates' verdicts (a regex on the trace, `verdict\\*"\s*:\s*\\*"pass`) are `arm: with-only`.
  - **The tests:** `test_evals.TheOutcomeCases` runs every pattern on `SAMPLES`; a new grader needs samples. It also runs every scaffold and audits every fixture.
  - **The run:** `claude.exe plugin eval . --tag outcome --scaffold --allow-real-servers --ablation with-without -j 2 --trust-plugin --no-publish --model claude-sonnet-5-5 --judge-model claude-haiku-5-5 --allow-tools Write Edit "mcp__plugin_web-design-suite_gates__*"`, with `--allow-tools` last. One run per arm cost $2.21 and took 685 seconds of runs.
  - **`evals.yml`:** `tag` is `routing`, `outcome` or `all`, by hand only: the owner dropped the tag trigger on 2026-10-11 (#110). Routing runs with `--ablation none`, then outcome `with-without`, with what routing left of $14.
- **The live checks (R3, R3.6).** `dev plans/web-design-suite-3.5.0-live-check.md` and `web-design-suite-3.6.0-live-check.md`. Run each headless session in a scratch copy of a project, with the plugin exported from `main` (`git archive main plugins/web-design-suite`):

  ```bash
  claude.exe -p "<prompt>" --plugin-dir <export>/plugins/web-design-suite --setting-sources project,local --max-budget-usd 0.6 --output-format json --model claude-sonnet-5-5 --permission-mode acceptEdits --no-session-persistence --allowedTools Bash PowerShell "mcp__plugin_web-design-suite_gates__*" --add-dir <export>/plugins/web-design-suite
  ```

  This is R3.6's wide form, and the one to use. The R3 form allowed only `"Bash(python *)" "Bash(node *)"` and the gate tools. It refused Claude's compound commands (`S=…; python …`, `cd … &&`) and reads of the skills' references, so in R3.6's first pass two sessions went around the scripts. The browser commands find Playwright through `NODE_PATH` (the tooling's `node_modules`).
- **N39 (#98).** `a11y_static.py` leaves a folder's email templates (the config's `emails`) to `lint_email.py` and lists them on stderr; a template named on its own is still read. The gate hook's a11y check stands aside only when `emailBuild` runs.
- **Baseline keys (#93, N38).** audit_design, a11y_static and perf_audit all write `/` in a key's path (`portable_key`), and read a baseline's keys the same way.
- **The scripts, by skill:**

  | Skill | Scripts |
  |---|---|
  | a11y-audit-runner | `a11y_static.py`, `a11y_runtime.mjs` |
  | client-presentation-builder | `build_presentation.py` |
  | component-state-matrix | `generate_matrix.py`, `snapshot_matrix.mjs` |
  | content-model-to-ui | `introspect_schema.py`, `scaffold_ui.py` |
  | design-critique-gate | `critique_report.py`, `critique_snapshots.mjs` |
  | design-system-docs | `build_docs.py`, `extract_system.py` |
  | design-system-versioning | `deprecate.py`, `diff_system.py` |
  | design-token-migration | `apply_codemod.py`, `cluster_values.py`, `extract_literals.py` |
  | email-template-system | `build_email.py`, `lint_email.py`, `render_email.mjs` |
  | figma-variables-sync | `figma_audit.py`, `figma_common.py`, `figma_to_tokens.py` (3.6.0 removed `dtcg_values.py` in favour of `dtcg.py`) |
  | perf-budget-gate | `crux_check.py`, `perf_audit.py`, `measure_vitals.mjs` |
  | web-design-studio | `audit_design.py`, `check_roles.py`, `generate_color_ramp.py`, `generate_type_scale.py`, `tw_probe.mjs` |

- **The release** is `python -B tooling/release/build.py OUT --rev SHA`, then a `v*` tag on that commit. `release.yml` is the only thing that creates a release.
  - The tag is annotated: `git tag -a vX.Y.Z SHA -m "web-design-suite X.Y.Z"`.
  - To install: the zip's `web-design-suite/` is the whole marketplace, `marketplace.json` included. **Replace** `C:\Users\vybec\.claude\local-marketplaces\web-design-suite` with it, not unpack over it, or a file a release removed stays (3.6.0 removed `dtcg_values.py`). Unpack and copy with Python and a `\\?\` prefix from a script file: the eval paths pass 260 characters, and a heredoc eats the backslashes. 3.5.0's copy is in `%TEMP%\wds350-backup`. then run `claude plugin update web-design-suite@web-design-suite` with the bundled CLI (`%APPDATA%\Claude\claude-code\2.1.295\d2e29494ec83\claude.exe`; 2.1.288's `36aa8c97bf86` is still there).
- **CI** runs Windows, Linux and macOS × Python 3.9 and 3.14, with Node 22.
  - **A push with no checks after a few minutes** is a lost `pull_request` event (a GitHub incident, 2026-10-12): `gh workflow run ci.yml --ref BRANCH`, and a later push fires the PR's own.
  - A macOS job cancelled after 15 minutes with no log is a runner that never came: re-run it (`gh run rerun RUN --failed`).
- **Python 3.9 is the floor**: no `zip(strict=)`, no `match`, no `str.removeprefix`, no `X | Y` outside annotations. Annotations are fine with `from __future__ import annotations`.
- **SKILL.md budgets are tight.** The limit is 20,500 bytes, so detail goes in the references. A row you lengthen needs a trim beside it.

  | Skill | Bytes |
  |---|---|
  | client-presentation-builder | 20,497 |
  | email-template-system | 20,497 |
  | landing-page-conversion | 20,497 |
  | perf-budget-gate | 20,494 |
  | component-state-matrix | 20,472 |
  | design-system-versioning | 20,401 |
  | figma-variables-sync | 20,484 |
  | web-design-studio | 20,450 |

- **Earlier phases' facts** are in the CHANGELOG under 3.4.0 and 3.3.0, and in the git log. The worked examples are tests (`TheWorkedRun`, `TheWorkedRelease`): a change to what the migration tools, the audit or diff_system print can fail them.

## 3. First: the state of `main`

Read `main`'s latest CI run (`gh run list --branch main --limit 1`). If it is red, fix it first, in a PR of its own. Then read `docs/HANDOFF.md`'s Warnings.

## 4. Phase 6c, 4.0.0: the audit, from P53's last class

**The owner placed all of Phase 6c first (2026-10-14).** Its order is P53's last class, then P54 and P55, then Phase 6b's workstreams (ask the owner which comes first then). Keep each PR under 100 files. Rows are from `dev plans/web-design-suite-execution-plan.md` §4:

| Item | Scope | Closes | Main files | Size |
|---|---|---|---|---|
| P53 | The cross-cutting class still to come: the cmd.exe placeholders, and its check (audit §7 class 9) | N45 | `CLAUDE.md`, the SKILL.md files, the plans, `tests/test_docs.py` | S |
| P54 | The medium findings, one PR per §3 area | N46 | per area | L |
| P55 | The low findings and doc fixes | N47 | per area | M |
| P34, P35, P37, P41, P42, P43 | Phase 6b's workstreams, after Phase 6c | see §4 of the plan | | |
| R4 | Release 4.0.0 | none | `plugin.json`, `CHANGELOG.md`, `README.md` | M |

**P53's last class, the cmd.exe placeholders, in detail** (the audit's §3.7 and §3.6, its §7 class 9: "extend `test_docs.PasteableCommands` to every fenced block and inline command in `CLAUDE.md`, the SKILL.md files and the plans; placeholders in capitals, never `<…>`"):
1. **D4.** `CLAUDE.md:44` has an unquoted `<ids>` in a command for cmd.exe (cmd says "The syntax of the command is incorrect"). This file's live-check command has `--plugin-dir <export>/plugins/…` inside a bash block.
2. **G13.** `design-critique-gate/SKILL.md` (about :210): `python -m scripts.audit_design <path> --json > audit.json` fails in cmd.exe, where `<path>` is a redirection.
3. **E14.** `email-template-system/SKILL.md` (about :58-78): the quick start is bash-only (`mkdir -p`, `cp`, `cat`).
4. **The check:**
   - Size the sweep before writing it. `grep -n '<[a-z][a-z-]*>'` over the fenced blocks of `CLAUDE.md`, the SKILL.md files, the workflow commands and the plans will show how many placeholders there are.
   - The plans' Bash-tool blocks are bash on purpose: the rule is placeholders in capitals, not cmd.exe syntax everywhere. Decide which blocks the test reads and say why in its docstring.
   - Keep the existing README rules (`not_portable()`) for the README.
   - A SKILL.md near its 20,500-byte budget may need a trim beside a longer command.
5. **Tests:** each fails on `v3.6.0` first. Run `test_docs` and `check.py` with `WDS_NODE_MODULES`. The CHANGELOG goes under 4.0.0's Fixed. Add the row `P53 part 5, #N` above the `P53` row and remove that row, since P53 is then done.

**Then P54, the mediums, one PR per §3 area** (the audit's §3.1 to §3.8, the `medium` entries). Read each area's entries by section; list each finding's own fixture before fixing it, as H14 did not reproduce. Two found this session go in with them:
- `diff_system`'s snapshot resolver reads an 8-digit hex alpha (`#2563eb80`) as opaque, so its contrast is measured as if solid (§3.4);
- `extract_system --tokens` reads a JSON file as CSS, so a DTCG token file gives zero tokens with exit 0 (§3.4).

- **The audit's fixtures** are in its session's scratchpad (`3985bfd1-…\scratchpad\migration\fx1..fx7`, `studio\`, `shared\fx`, …), which Storage Sense can empty. Run a finding's own fixture before fixing it (H14 did not reproduce). Rebuild a case from the audit's text if it is gone.
- **Facts from outside** are re-read at the source on the day, and a figure goes into `evidence.json`.
- **R4** follows R3.6's order:
  - a live check of what changed (the owner's OK, with its estimate);
  - the release PR;
  - the evals on its merge (the owner's OK, about $11, with `headSha` checked);
  - then the tag.

  Its live check covers Part 5's new block in a real project, `/tw-probe`, the v3 upgrade path, the v4 census on a real Tailwind 4 project, the gates P50 changed (a Vue project's bound attributes, the index-mode hook), and the migration's reconciliation on a real codebase (P52).

Ask the owner before each eval run and each paid session, and keep each PR under 100 files for CodeRabbit.

## 5. End of session (never skip)

1. Rewrite `docs/HANDOFF.md`: one page, with the state, next steps, blockers and warnings.
2. Update `CLAUDE.md`'s Current State, the execution plan's §9, the inventory, and `dev plans/README.md`'s line for this file.
3. **Rewrite this file** and `next-session-opening-prompt.md` for the session after yours, with the next PRs in the same detail as §4 here.
4. Run `python -B "dev plans/check_execution_plan.py"`.
5. Commit the docs in a PR of their own. Merge it when it is ready, as §0 defines ready: CI green on its head, every thread resolved, GitHub clean.
6. Tell the user what merged, what is open, the token use, and what they need to do. Give them the opening prompt for the next session.
7. Remind the owner that `Vybecode-LTD/wds-gate-scratch` (R3's private CI test) is theirs to delete.
