# Changelog

## 3.3.0 — unreleased

### Fixed

- **The audit passed three kinds of file as clean** (SB-A9):
  - It read `//` as a comment in plain CSS, so `url(https://cdn…/hero.svg)` hid every
    declaration after it, and a custom property holding an address (`--terms:
    https://…`) hid the rest of its line. `//` is now a comment only in Sass, Less,
    styled templates and single-file components, and never inside an unquoted address
    in `url()`, where an escaped `\)` does not end it. A Sass `url()` that holds an
    expression instead (`url($asset)`) is read as code, so its comments still count.
  - A rule after a closed `@layer` block was never reported as unlayered. The finding
    now points at the first unlayered rule. A `@keyframes` block outside a layer, as
    the references and the scaffold write it, is not unlayered CSS: a keyframe is not
    a style rule. 3.2.1 flagged a file that held only keyframes.
  - A root-level `components/` or `ui/` folder, the common Next.js layout, was not a
    component file, so Law 2 was skipped there. `mycomponents.css` no longer counts
    as `components.css`. The spec's file-class examples now include both cases.
- **The token migration tool's file classes** had drifted from the audit's (N11): it
  missed `brand-tokens.css`, `design.tokens.css`, files in `tokens/` and
  `dark-theme.css` as token files, so its inventory listed their literals and the
  codemod did not skip them, and it shared the `components/` bug above. It now uses
  the audit's patterns, and the spec test holds both copies.
- **The token migration tool had the same `//` bug** (N12). After `url(https://…)` in
  plain CSS its census filed every literal to the end of the file under `background`,
  so clustering saw the wrong property, and the codemod rewrote none of them. It now
  reads comments as the audit does.
- **A singular `token.css` or `brand-token.css` was a token file** to the audit, so it
  was never checked; the spec's globs and stylelint name only `tokens`. Both copies of
  the test now follow the spec, and its examples include the two names.
- **The audit misread Sass** (SB-A24). The rules are in `design-rules.json` under
  `sass`; the audit is the only gate that reads Sass.
  - A partial holding only mixins, such as the references' own `_mq.scss`, failed as
    unlayered, because a mixin holds rules. A `@mixin` or `@function` body emits
    nothing where it is written, so the layer is now checked where it is included.
    A mixin that holds a whole rule and is included at the root of its own file,
    directly or through another mixin, is unlayered there; a mixin defined in another
    file is not followed.
  - A Sass variable holding a literal passed (`$card-padding: 24px`, then
    `padding: $card-padding`). Outside a token file, a variable that holds a length,
    a hex or functional colour, a duration or an easing curve now fails as
    `sass-literal`, in a map as in a single value. A breakpoint (`$bp`, `$bp-*`,
    `$breakpoint*`) and a variable local to a `@function` are left alone, and a
    quoted string is text whatever it spells.
  - The braces of an interpolation closed the layer around them, so after
    `.card-#{$name} { … }` the next rule was unlayered, and a declaration whose value
    was an interpolation (`margin-inline: #{$gutter}`) was never read. A brace inside
    a string in an interpolation is text too.
  - Indented Sass (`.sass`) was reported clean whatever it held: the audit follows
    braces and that syntax has none. A `.sass` file is now listed as skipped, and a
    folder holding nothing else is the "0 files audited" error.
- **A zero with a unit hid the length after it.** The audit looked at the first
  length in a value only, so `padding: 0px 13px` passed, in CSS as in Sass. It now
  reads every length (CodeRabbit on PR #7).
- **Two more scripts passed indented Sass** (N13). On a `.sass` file full of literals
  the migration census reported "no hardcoded design values found", and
  `a11y_static` reported clean for `outline: none`. Both now say which `.sass` files
  they did not read. The census prints its notes when it finds nothing, too; they
  used to appear only beside a result.
- **The Supabase reference had no access boundary** (DL-B1, DL-A5, DL-C4), the first
  of the two high-severity gaps. `supabase-integration.md` now says which key each
  process holds (§9): the publishable key in the browser, and FastAPI either as the
  user, forwarding the caller's token so row-level security applies, or as the
  service, where no policy runs and the endpoint must do the policy's job. It says
  that every `VITE_` variable is public, and where validation and authorization are
  enforced. Three pieces of guidance were unsafe or wrong and are corrected:
  - The permission RPC was a `security definer` function in the exposed schema with
    no `search_path`. The template now keeps it in a private schema, pins
    `search_path = ''` and revokes `execute` from `public`.
  - "The JWT's claims" were trusted whole. Authorization data comes from
    `app_metadata` only, and a claim is as old as the token.
  - Realtime `DELETE` events are not policy-filtered, and `REPLICA IDENTITY FULL`
    does not return the old row on a table with RLS, so the fix the reference offered
    did not work in the case it was for.
  It also says that a public Storage bucket is world-readable whatever the policies
  say. Every Supabase fact was re-read at supabase.com on 2026-10-01.
- **The schema tool could not see row-level security** (DL-A6, DL-C1). It skipped
  `ENABLE ROW LEVEL SECURITY` and `CREATE POLICY`, listed "RLS policies" as missing
  from DDL that held them, and assumed RLS was on everywhere. `introspect_schema` now
  reads both statements and column revokes, records them per table, and opens
  `--summary` with a SECURITY block:
  - `BLOCK`: a table with RLS off, or a policy that lets a signed-in user write every
    row because its condition is `true`.
  - `warn`: RLS on with no policy for a signed-in user, or authority columns (`role`,
    `is_admin`, `org_id`) that a user who may update a row can change, with the
    revoke and grant that close it. A column counts as safe only when the user has no
    UPDATE privilege on it, or a policy pins it to the caller (`owner_id = auth.uid()`).
  Policies are replayed as the migrations state them: a dropped policy is gone, and a
  restrictive policy narrows the permissive ones and grants nothing.
  The findings are in the model (`security`), the "Is RLS on?" question defaults from
  the DDL, and `scaffold_ui` repeats the blocking findings and writes each table's
  forbidden-state notes from that table's own RLS. It still writes the screens by
  default; `scaffold_ui --strict` writes nothing and exits 1, for CI. From generated types or a JSON dump the block says "unknown".
- **The reference's column revoke did nothing** (N15, from CodeRabbit on PR #9). It
  told readers to protect `is_admin` with `revoke update (role, is_admin, …) on
  profiles from authenticated`, and secrets with a column-level `revoke select`.
  Postgres ignores a column-level revoke while a table-level grant stands, and
  Supabase grants table-level privileges by default. The reference and the security
  pass now give the form that works: revoke on the table, grant the columns back.
- **The skill's own command failed on two migration files** (N14).
  `introspect_schema supabase/migrations/*.sql` was an argparse error as soon as the
  folder held more than one file. Several DDL files are now read as one schema, in
  the order given, which is also how a later migration's policies reach the table.
  A pattern is expanded by the tool itself, because cmd.exe passes it as written.
- **The schema tool misread what Supabase writes** (DL-A7, DL-C2).
  - `supabase db pull` is `pg_dump --quote-all-identifier`, which quotes types too:
    `"text"` and `"date"` were unknown types, so a title fell back to the id and a
    date became a text input, and `"public"."order_status"` lost its values. An
    identity added by `ALTER TABLE … ADD GENERATED`, and a `serial` default set by
    `ALTER COLUMN`, were missed, so each id was a required number in the form.
  - A function's `$$` body was split at its own `;`, so an `alter table … disable
    row level security` inside a function turned RLS off for the table.
  - In generated types, prettier puts each member of a long union on its own line:
    an enum kept only its first value, and a Row column whose type wrapped was dropped.
  - Migrations: `generated by default as identity` read as an editable id,
    `ALTER TABLE … ADD COLUMN`, `DROP COLUMN`, `ALTER COLUMN` and `RENAME` were ignored, a quoted
    name with a space was not a name, and `CHECK (x between 1 and 99)` gave no bounds.
- **The worked example quoted a fixture nobody had** (DL-B8). It ships now, as
  `tests/fixtures/supabase/`, and the claims in supabase-integration.md §1 are
  measured on it. Two of them were wrong: generated types lose 12 rules across 9
  columns, not 14 across 13, and they lose a key into `auth.users`. The claim that a
  JSON dump gives the same model is gone: that depends on its query. The reference's
  `pg_dump` command keeps the privileges now, because the security pass reads them.

- **Vendor CSS beat every layer** (SB-A8). The canonical `index.css` in
  stack-vanilla-css §4 left `vendor` out of its statement and then imported into it,
  and a layer first named by its import is appended after `overrides`. Three references
  put `vendor` in three different places. The order is now in `design-rules.json`
  (`layers`): `reset, vendor, tokens, base, layout, components, utilities, overrides`,
  plus `theme` in a Tailwind entry. Every statement in the plugin names `vendor`, the
  contract's included. The audit and stylelint refuse a statement out of that order,
  and an `@import … layer(x)` whose `x` the statement does not name.
- **Self-wrapped files were imported with `layer()`** (SB-A23). Starter files open
  their own `@layer` block, so `layer(base)` around `base.css` made `base.base`, which
  stack-vanilla-css itself forbids. handoff-conventions and stack-tailwind did it, and
  style-architecture called it deliberate. handoff §7.1's pre-commit hook audited the
  whole tree on every commit; it takes the staged files now, as the hook does.
- **Two claims about a vendor's `!important` were wrong.** style-architecture §11 said
  a layer makes it lose to your components. stack-vanilla-css §5 said three `!important`s
  in `overrides` beat it. Important declarations reverse the layer order, so the
  vendor's win in both cases. The references now say to strip them at build time, or
  patch a vendored copy.
- **The schema parser misread four kinds of statement** (N16 to N19, from the reviews of #12):
  - A quoted name with a `$` (`"amount$usd"`, which every dump quotes) lost its quotes,
    and the column parser, which reads a bare name as word characters, then dropped the
    column without a word. Such a name keeps its quotes now.
  - `DROP COLUMN` left the column in the primary key, in unique indexes, and in other
    tables' foreign keys. Postgres drops every index and constraint that uses the
    column, the whole primary key with it, and needs `CASCADE` for the foreign keys
    into it, which it then drops. The model does the same, CHECKs included.
  - `RENAME COLUMN` left other tables' foreign keys and the CHECKs on the old name.
    Postgres retargets both, and so does the model; string literals stay as they are.
  - Postgres 18 names a not-null constraint: `add constraint t_name_nn not null name`.
    The parser read it as `ADD COLUMN` and made a column named `constraint`. It now
    makes the column not-null, in `ALTER TABLE` and `CREATE TABLE`, and an
    `ADD CONSTRAINT` it does not know is skipped, never read as a column.
- **The scaffold's policies failed on four kinds of schema** (N20 to N23, from the reviews of #13):
  - A model introspected with `--schema app` got every policy, grant and smoke test on
    `public`. They use the model's schema now.
  - `sql_ident` quoted nine reserved words, so a table named `select` or a column named
    `where` gave invalid SQL. It quotes every word Postgres reserves now, from a copy of
    the parser's list.
  - Postgres cuts a name at 63 bytes, so a table name of 55 bytes or more gave its four
    policies one name, and the second `CREATE POLICY` failed. A name that would be cut
    now shortens the table part, which ends in a hash of the whole name.
  - The smoke test's "no write policy" check counted a policy for `service_role`, which
    the browser never holds. It counts only policies for `public`, `anon` or
    `authenticated` now.
- **The layer statement** (N24 and N25 from the reviews of #14, and N29):
  - The canonical `index.css` stopped after `layout.css`, so a project that copied it
    never imported `utilities.css` or `overrides.css`. It names both now, imported last
    once the project has them, and the four references that quote it follow.
  - An `@import … layer(vendor)` above the `@layer` statement names `vendor` first,
    whatever the statement then says. The spec refuses it now, and so do the audit
    (`layer-statement-position`) and stylelint (`design/layer-order`).
  - stylelint never checked where the statement stands, so a rule above it passed,
    though the audit refused it. `design/layer-order` refuses it now, from a second
    refused example in the spec.
- **On Linux and macOS, `snapshot_matrix` missed a state with no style** (found by the
  first CI run). It called a hover, active or focus-visible cell unstyled only when it
  was pixel-identical to its default cell. The cells sit side by side at different
  subpixel offsets, and there text is antialiased by where it sits, so twin cells never
  matched and the check never fired. It now compares computed styles: a state is
  unstyled when every element of its cell, `::before` and `::after` included, computes
  the same style as in the default cell, leaving out what never changes a pixel (the
  cursor, pointer events, selection, motion timing).

### Added

- **One canonical entry stylesheet per stack** (SB-C9, SS-C9 in part). The starter
  ships `index.css`, and the configs ship `index.tailwind.css` for Tailwind v4. Five
  references quote them through `tools/sync_snippets.py` instead of writing their own.
- **The scaffold proposes each table's row-level security** (DL-B2). It used to
  decide which columns a form writes and emit client validation, with nothing on the
  database side. Now `db/policies/<table>.policies.todo.sql`, join tables included,
  turns RLS on and guesses whose a row is from the keys: the user's own row, an owner
  column, a child of an owned row, a tenant (a commented template) or nobody (read
  only). It revokes the table-level insert and update and grants back the form's
  columns, so the database and the `Draft` type agree. No write policy it proposes
  has a `true` condition, and the schema tool finds no hole in the result.
- **A smoke test per table**, `<table>.policies.test.sql`: plain SQL in a transaction
  that rolls back. It checks that RLS is on, that `anon` sees nothing, that a signed-in
  user sees only their rows, and that the columns outside the form refuse a write.
- **`lib/supabase.ts`** (the rest of DL-B1): the browser's one client, with the
  publishable key. It refuses to start on an `sb_secret_` key or a legacy
  `service_role` JWT.

### Changed

- **Python 3.9 or newer**, down from 3.10. The scripts already ran on 3.9, the Python
  macOS still ships; now the tests do too. The harness no longer uses
  `TemporaryDirectory(ignore_cleanup_errors=)`, `write_text(newline=)` or a slice of
  `Path.parents`, all 3.10+, and the README states the new floor.
- **CI** (XC-B3). `.github/workflows/ci.yml` runs the suite and the static checks on
  Windows, Linux and macOS, at Python 3.9 and 3.14, with the pinned Node tools, and
  `claude plugin validate --strict` on the marketplace, the plugin and `plugin.json`.
  Linux adds Playwright's headless shell and Postgres, so the browser and policy tests
  run there too.
- **The release build** (XC-C6). `tooling/release/build.py` replaces `build_zip.py`. It
  makes the plugin's zip, one `.skill` file per skill, packaged as Anthropic's
  skill-creator packages one and carrying the plugin's LICENSE, and `SHA256SUMS`, all
  from git and byte-identical on a rebuild. A pushed `v*` tag makes
  `.github/workflows/release.yml` build them and create the GitHub release, with the
  CHANGELOG's section as its notes; nothing else creates a release.
- **The 17 scripts with a shebang are executable** (N5), as the nine from 3.0.0 were.
- **Two tools for each PR.** `tools/fail_before.py` runs named tests against an earlier
  revision and this tree, and prints fixed, control, still failing or regression for
  each. `tools/check.py` runs the static checks and the tests a change affects.

### Tests

- SB-A9 and N11: six `AuditPrecision` tests and `test_rules_spec`'s file classes.
  Against 3.2.1 all seven fail; a quoted `url("https://…")` passes on both, as the
  control.
- N12: `test_token_migration.AddressesAreNotComments`, the census and the codemod.
  Against 3.2.1 both fail, in five subtests.
- SB-A24: seven `AuditPrecision` tests and `test_rules_spec.test_sass`, which runs the
  spec's Sass examples through the audit. Against 3.2.1 seven fail, `test_sass` in
  eleven subtests; the eighth, a brace in a string inside an interpolation, guards a bug
  that existed only while this fix was in review. Its example of an interpolation inside a layer passes there, because
  3.2.1 never reported a rule after a closed block; it fails on `5fd068e`, the commit
  before this fix. `test_sass_is_left_to_the_audit` holds the spec's statement that
  the stylelint config reads no Sass, and passes on both.
- N13: `test_token_migration` and `test_content_and_a11y` each hold a `.sass` file.
  Against 3.2.1 both fail; a `.scss` file with the same rule is the control.
- DL-B1, DL-A5 and DL-C4: `test_docs.SupabaseGuidance.test_the_access_boundary_is_stated`
  holds what the reference must say and must no longer say. Against 3.2.1 it fails
  in 16 subtests. The two dated figures it quotes are in the evidence register.
- DL-A6, DL-C1, N14 and N15: twelve tests in `test_content_and_a11y.SchemaSecurityPass`. Against
  3.2.1 all twelve fail. Controls inside them: a public read policy, a policy for the
  service role and an owner check are not findings.
- DL-A7, DL-C2 and DL-B8: `test_schema_sources`, fifteen tests on real output. The
  worked example in three forms: the migration, a `pg_dump` of it from Postgres 18,
  and the same schema as `gen types` writes it. Also `gen types` for a real 25-table
  project. Against 3.2.1, thirteen fail. The real project's types and the `db pull`
  form pass there, as controls: the parser already read both.
- DL-B2 and DL-B1: `test_policies`, eleven tests. Three run the generated SQL on a
  scratch Postgres when one is on PATH, and skip otherwise. Every proposal applies and
  every smoke test passes. Then four breakages each make their test fail with its
  reason: an open read policy, a re-granted owner column, RLS turned off, and a write
  policy on a read-only table. Against 3.2.1 all eleven fail.
- SB-A8, SB-A23 and SB-C9:
  - `test_rules_spec`: the spec's layer examples through the audit, the stylelint
    config's copy of the order, and every layer statement in the docs, configs and
    starter. Against 3.2.1 all three fail.
  - `test_real_tools.StylelintConfig` runs the examples through the real stylelint,
    and lints the two canonical entries. On 3.2.1 it cannot set up, because the
    entries do not exist there.
- `test_docs` runs `test_harness` on the floor interpreter, and `test_harness` checks
  the temporary folders and `TempDirTest.write` there. On 3.9, 3.2.1's harness errored
  in 181 tests.
- `tools/check_pointers.py --write-register` and `tools/sync_snippets.py` (without
  `--check`) are tested writing a file: UTF-8, LF, byte for byte. With 3.2.1's tools
  both tests error on 3.9, where `write_text` has no `newline`.
- The budget test passes `maxsplit` to `re.split` by keyword, as Python 3.13 asks.
- N16 to N25 and N29, against `8ed2e84`, the `main` before the fix, since none of this
  code is in 3.2.1. Fifteen tests fail there, in 26 failures and 2 errors:
  - `test_schema_sources`: one test per parser fix, four in all.
  - `test_policies`: eight tests. Four run on the scratch Postgres: a schema of its own,
    and reserved words with a 60-byte table name, each apply and pass their smoke tests;
    every word `pg_get_keywords()` reserves is on the list; and a write policy for
    `service_role` passes the smoke test while one for every role fails it.
  - `test_rules_spec`: the entry names a file for every layer (N24), and `test_layers`
    on the new refused example (N25).
  - `test_real_tools.StylelintConfig` on the two new refused examples (N25, N29).
  - The 20 tests in the same classes that pass on both are the controls. Among them is
    the N29 example through the audit, which refused it already.
- `load_script` moves into `wds_support`, for the test that holds the scaffold's copy
  of the reserved words equal to the parser's.
- What the reviews of #16 found, against its first commit (`0a0c249`): five tests fail
  there, and twelve controls pass on both.
  - A rename or a drop no longer reaches into a call (`lower(note)` is not a column
    `lower`) or into a quoted name (`"old.part"` is not `old`).
  - A table constraint listed before its column now applies.
  - The smoke test quotes every name it puts in a string (a table named `it's`).
  - The no-write check counts a role that `anon` or `authenticated` inherits.
- N5, the PR tools and the build, from `tools/fail_before.py` against 3.2.1: nine
  fixed and eleven controls.
  - `test_file_modes` reads git's modes (the index, or the commit `WDS_PLUGIN_REV`
    names) and fails on 3.2.1, where 17 scripts with a shebang were 100644.
  - `test_tools`, eight tests, all fixed. `fail_before.py` runs on a fake repository of
    two commits with a fix, a control, a test that still fails, a regression, failing
    subtests, a skip and a failing `setUpClass`. `check.py`'s choice of tests is checked
    on its own, and its list of changed files keeps a path with a space whole.
  - `test_release_build` ports the zip builder's seven tests to `build.py` and adds four:
    each `.skill` file, the sums, a skill the platform refuses, and a long description
    as a warning. The builder lives in `tooling/`, outside the plugin, so all eleven run
    the same builder in both runs: they are controls.
- `test_policies` keeps the scratch cluster's socket in its own folder: Debian's and
  Ubuntu's Postgres put it in `/var/run/postgresql`, which only `postgres` may write.
- The first CI run, on Linux and macOS: `test_browser_runtime.MatrixSeesStateChanges`
  failed there and passes now, which holds the `snapshot_matrix` fix; on Windows it
  passes on both. Two tests assumed Windows: `test_harness` took a relative path across
  drives (the runner's checkout is on `D:`), and `test_release_build` set a mode git
  re-read from the disk on POSIX. On a loaded macOS runner, the mega-menu scenario in
  `test_recipes.NavigationCodeInABrowser` dwelt over a trigger past the recipe's
  switching delay, because it timed the pointer with real waits. Its page now runs on
  Playwright's fake clock, which only the scenario advances. Its diagonal also went two
  thirds of a pixel down per step, so some steps rounded to straight sideways, which
  is not heading into the panel; each step now goes a whole pixel down.

## 3.2.1 — 2026-09-25

Ready to distribute. The stylelint config and both Tailwind blocks of the ESLint config
now run through the real tools in the tests, and what that found is fixed. A review of
this release before it shipped found more, and that is fixed too. Every fix has a
regression test that fails on 3.2.0, or on the release candidate for what the review
found (`python -B -m unittest discover -s tests`: 339 tests).

### Upgrading

- **Tailwind v3 with Part 5 of the ESLint config:** give `settings.tailwindcss.config` an
  absolute path anchored at your project, not at the folder ESLint runs in. Copy the v3
  block as it stands now: it looks up from the config file (`import.meta.dirname`) to
  the nearest `package.json`. eslint-plugin-tailwindcss 3.18 stops ESLint with "Could
  not resolve tailwindcss" when the path is relative, and ESLint 10 loads a config from
  whichever folder it lints, so a path resolved from the working folder broke a run from
  a monorepo root.
- **Tailwind, both lines:** Part 5 now whitelists the starter's own classes (`stack`,
  `cluster--tight`, `u-*`) in `ownClasses`; add your components' blocks there before
  you make `no-custom-classname` an error, or it reports every one of them.
- **stylelint:** the config now accepts the starter as shipped; it used to refuse it 32
  times. If you copied the starter, take its new comments with it: the
  `stylelint-disable` comments in reset.css, base.css, tokens.css and layout.css, and
  layout.css's sockets (`--center-box`, `--imposter-max`, `--reel-bleed-pad`) and
  `.imposter--bottom` shorthand.
- **Node:** the lint configs need a Node both stylelint 17 and ESLint 10 support: 20.19+,
  22.13+ or 24+.

### Fixed

- The stylelint config, run on stylelint 17.15 with stylelint-config-standard 40.0:
  - The CSS system colours (`Canvas`, `ButtonText`, `Highlight`…) are allowed only inside
    `@media (forced-colors: active)`, in any case; a new rule,
    `design/system-colors-in-forced-colors`, refuses them anywhere else, shorthands
    included.
  - `100svb`, `100svh` and `100dvb` are allowed for `min-block-size`.
  - `import-notation` is off. The references spell imports both ways, and the
    standard config's `url()` notation refused the documented Tailwind entry.
  - The single-line-declarations rule is off: formatting is Prettier's job, as the
    config already said.
  - The file-class overrides are still the documented four. A fifth, for layout
    primitives, was tried and removed: placed after the component block, it took Law 2
    from any component in a `layout/` folder, and its regex hung on a long number.
- The starter:
  - It marks its documented one-offs with a `stylelint-disable` comment and a reason: the
    `[hidden]` override, iOS text-size-adjust, the second `html` rule, the sub/sup
    ratio, the focus ring's gap, the two repeated `:root` blocks in tokens.css, and in
    layout.css the switcher's quantity queries and the file's `> *` child rules.
  - layout.css derives its three computed boxes through sockets, as it already did
    elsewhere, and `.imposter--bottom` uses the `inset-block` shorthand. Nothing renders
    differently.
- The ESLint config's Part 5:
  - The v3 block anchors its config path at the project.
  - Both blocks whitelist the starter's own classes; the v3 block no longer whitelists
    the utilities the plugin already learns from the config, which hid their typos.
  - Both blocks and the header give `p-card p-card-lg` as the contradiction.
    `p-card px-inline-md` is not one: the longhand always follows the shorthand, in
    v4 and in v3.
- The 3.0.1 entry below named a report by a path on the maintainer's machine.
- The README states the floors: Python 3.10 or newer (the suite runs on 3.10 to 3.14),
  and Node 20.19+, 22.13+ or 24+ for the lint configs.
- The rule spec, `design-rules.json`, records the system-colour rule, and that a
  component in a `layout/` folder is a component.

### Tests

- `test_real_tools` runs stylelint over the starter, the documented entries and fixtures
  for each law and for everything the review found. It runs both Part 5 blocks through
  the real plugin (4.4 with Tailwind 4.3, 3.18 with Tailwind 3.4) from the folder above
  the project, over role classes, the starter's own classes and typos of both; the
  contradiction fixtures are the examples the blocks' own comments give.
- `test_docs` checks that no shipped file names a folder on the author's machine
  (including as JSON escapes it and WSL paths), that the README states the Python
  floor, and that every script compiles, and every shipped script's `--help` runs, on
  the floor interpreter itself (`WDS_FLOOR_PYTHON`, else uv's).
- Inside the plugin's repository, `npm ci` in `tooling/main` and `tooling/tailwind-v3`
  installs every tool the tests use but the browser, at pinned versions, and the tests
  find them without any variable set; `off` switches a group of tests off.
- Every subprocess the tests start gets the harness's environment, without the variables
  that tie git to one repository (`GIT_DIR`, `GIT_INDEX_FILE` and the rest), and a test
  holds every call to it. Run from a git hook, the hook tests staged their fixtures into
  the hook's repository.

## 3.2.0 — 2026-09-25

Phase 2 of the 3.0.1 review: the docs are tied to the code. Tests now read the
commands, configs, code blocks, figures and pointers out of the docs and check them
against the scripts, a real browser and the real tools, and the fixes followed from
what they found. Every fix has a regression test that fails on 3.1.0 and passes here
(`python -m unittest discover -s tests`: 296 tests).

### Upgrading

- **The pre-commit hook fails when a stage cannot run.** A missing stylelint config,
  audit script or Python used to print SKIPPED and let the commit through. Set
  `DESIGN_GATE_ALLOW_SKIP=1` while a stage is being adopted. Configs are now found at
  the repo root first (`stylelint.config.*`, `.stylelintrc*`, a `stylelint` object in
  package.json), then in `assets/configs/`.
- **Install the hook twice**, as `pre-commit` and as `commit-msg`: a bypass
  (`DESIGN_GATE_BYPASS=1 DESIGN_GATE_BYPASS_REASON="why"`) now leaves a
  `Design-Gate-Bypass:` trailer in the commit as well as a line in the log.
- **Re-baseline the design audit.** It now reads class strings inside `cn()`, `clsx()`,
  `cva()` and the other class helpers, refuses every Tailwind arbitrary value except
  arbitrary variants, image URLs and pseudo-element content, flags arbitrary properties
  (`[padding:13px]`) and the v4 `!` suffix, and audits styled-components and emotion
  template bodies as CSS.
- **Renames and moves.** Tailwind's width utility `border-default` is now
  `border-stroke` (it also painted the border colour). `.prose` moved from base.css to
  layout.css. The navigation code moved from `navigation-patterns.md` §6 to
  `navigation-code.md`.
- **New roles** in all 14 contracts, the starter, both Tailwind configs, the migration
  template, the Figma importer and the email map: `--motion-instant` (press, toggle,
  check) and `--bg-scrim`. Components may read `--weight-*` directly.
- **design-system-docs.** The drift baseline is `docs/system.json`, extracted from
  `styles/ src/components/` in every step. `build_docs --check --baseline FILE` exits 2
  when FILE does not exist; it used to check prose only and pass.
- **Versions.** stylelint `^17` with stylelint-config-standard `^40`; ESLint `^10` with
  a package.json `overrides` entry for eslint-plugin-jsx-a11y; eslint-plugin-tailwindcss
  4.x for Tailwind v4 (`cssConfigPath`), pinned to 3.x on v3. CI actions on their
  Node 24 majors (checkout@v5, setup-node@v5, setup-python@v6, cache@v5,
  upload-artifact@v6).

### Tests on the gap between docs and code

- Every CSS, TSX and JSX block in the references passes the audit; deliberate bad
  examples say so with `example: wrong | before | illustration`.
- Quoted starter code is kept identical to its region in the starter
  (`tools/sync_snippets.py --check`).
- Every "Verified n:1" is recomputed and every `clamp()` anchor solved.
- Every documented flag is one the script's own parser accepts.
- Every § pointer resolves, and each cross-file pointer lands on the heading it was
  checked against (`tools/check_pointers.py`, 300 registered).
- Real tools where they are installed: ESLint (on 9 and 10), a Tailwind v4 compile of
  theme.css, tailwind-merge with the documented config, and Chromium for the focus-ring
  caveat, the navigation code, container queries, subgrid, layer order and more.
- `check_roles.py` checks role pairs in light, dark, `.inverse` and dark `.inverse`, as
  an opt-in hook stage, and generates color-system.md §6.
- One rule spec, `assets/rules/design-rules.json`, that the audit, the stylelint config
  and the docs are tested against.

### Recipes that run as written

- The drift gate: one baseline, one set of inputs.
- Performance budgets are JSONC, and `measure_vitals` reads the budget before it starts
  a browser.
- The CI workflows: `shell: bash`, the server waited for in the step that uses it, the
  lockfile's Chromium installed and cached, nothing installed ad hoc, a readable report
  in the log (`--report FILE`, new in `measure_vitals` and `a11y_runtime`), and a PR
  comment with its number, token and permission.
- Navigation code: the safe triangle holds, a click keeps a hovered panel open, the
  drawer's light dismiss ignores its own padding, and `--nav-offset` is registered as a
  `<length>`.
- The `@property` recipe uses a px initial value and a socket only the root reads.

### Docs that are true

- The accessibility skill's runtime promises (keys, reduced motion, budget keys, 200%
  zoom as a warning), its coverage figures (a tool fully decides 7 of the 55 A and AA
  criteria and part of 31 more), and "Not Evaluated" for AAA only.
- Container queries, subgrid, SC levels, legal baselines (EU EN 301 549 v3.2.1, ADA
  Title II WCAG 2.1 AA, Section 508), colour-science numbers, email-client support per
  caniemail, Gmail's style ceiling (and the build now splits retained CSS over it),
  classic Outlook's support dates, Figma plans and styles, Bootstrap's !important
  utilities, MUI native colour, and the README's standalone claim.
- An evidence register, `tests/fixtures/evidence.json`: each quoted figure with its
  source, date checked and the source's own words. Baymard's checkout figures were
  corrected on the way.

### Leaner skills

- Every SKILL.md fits in what Claude Code keeps after compaction (about 5,000 tokens);
  large sections moved verbatim into references. Landing-page-conversion's ethics and
  evidence rules come first.
- Descriptions are 301–368 characters, lead with a sentence that stands alone, and say
  what each skill is not for.

### Not verified by execution

stylelint 17 and eslint-plugin-tailwindcss 4.x are not installed here, so their config
text is checked against the registry and their READMEs, not run.

## 3.1.0 — 2026-09-24

Phase 1 of the 3.0.1 review: the gates stop passing things they never checked, the
unsafe defaults go, and every documented command runs as written. Each fix has a
regression test that fails on 3.0.1 and passes here (`python -m unittest discover -s tests`).

### Upgrading: re-baseline

The design audit now finds things it used to miss, so a gate that was green may go red
on code that was always wrong:

- a literal beside a `var()` (`padding: var(--pad-sm) 13px`);
- spacing inside `@media` / `@container` / `@supports`;
- HTML, Vue, Svelte and Astro files: `<style>` blocks, `style=""`, class lists;
- literal Tailwind utilities (`duration-300`, `z-50`, `border-2`, `bg-accent/37`,
  `p-(--space-6)`, `space-y-related`).

Existing debt: `audit_design.py src/ --write-baseline .design-baseline.json`, as before.
Baseline keys are now relative to the baseline file, so a 3.0.1 baseline written from
the folder that holds it keeps matching.

### The gates

- **audit_design**:
  - A `var()` no longer hides a literal written beside it.
  - Spacing inside media, container and supports queries is checked.
  - HTML and single-file components are audited; HTML email is skipped and routed to `lint_email`.
  - A file named explicitly that is not CSS, JS or HTML is skipped and listed, not read as JavaScript.
  - A folder with nothing auditable in it exits 2 instead of reporting "clean".
  - Files saved with a UTF-8 BOM no longer fail as "unlayered".
  - The baseline matches however the path is spelled.
  - The clean message names the laws it checks (L1–L6).
- **a11y_runtime**:
  - Contrast is measured for colours in any syntax, including the suite's own OKLCH.
  - A modal `<dialog>` is no longer a "keyboard trap", and what sits behind it is not "unreachable" or "unnamed".
  - Focus inside a same-origin iframe is followed.
  - axe runs in every frame.
- **snapshot_matrix**:
  - The default per-pixel tolerance is 0.03 (was 0.10, coarser than the suite's own hover and pressed overlays).
  - Every hover, active and focus-visible cell must differ from its default cell, with no baseline needed.
- **a11y_static**:
  - Linear time on large pages: 4,000 rows took 46 s and now take 0.7 s.
  - Files it cannot audit are skipped, not parsed.
- **The pre-commit hook** runs `a11y_static` on staged files when `scripts/a11y_static.py` is vendored. The inline hook snippets in the docs are replaced by the shipped hook.

### Unsafe defaults

- **content-model-to-ui**:
  - Credential columns are matched by the documented patterns (`*_token`, `*_hash`, `*_secret`, `*_key`, …) and never displayed or editable.
  - Columns that carry authority (`role`, `is_admin`, `owner_id`, `org_id`, `plan`, `credits`, a profile id that references `auth.users`, …) are read-only by default, with their own question.
  - The Supabase guidance now describes how writes really fail under row-level security, and how to protect columns.
- **Starter CSS**:
  - Density and theme work on a subtree, not only on `<html>`.
  - Themes set `color-scheme`, so native fields stay readable.
  - `[hidden]` beats every layer.
  - Dark error text, `.inverse` sections and control borders meet WCAG AA.
  - Dialogs keep their viewport limit.
  - The focus ring is an outline, which no component `box-shadow` can remove. The same applies to the Tailwind `focus-ring` utility, which had `outline: none`.

### Honest output

- **The client deck**:
  - Claims "passes" only when the accessibility results say so, and "keyboard-tested" only when the decision log records it (`## Tested by hand`).
  - The performance slide's title follows the budget.
  - The audit is credited with the laws it checks.
- **The critique report**:
  - The defence sheet carries open confirmed defects and labels suspicions.
  - An audit rule is folded into a hand finding only when the finding claims it (`covers`, or the id in backticks).
  - Every merge is reported.

### Pipelines

- **Figma sync**:
  - Reads DTCG 2025.10: colour objects, `{value, unit}`, `$ref`, `$extends`, `$root` and group `$type`. Values it cannot express are reported, never written as Python.
  - Composed-colour opacity is a percentage.
  - `figma_audit --tokens` checks against the project's own ramps.
  - Output carries no clock time (`SOURCE_DATE_EPOCH` to stamp one).
- **Token migration**:
  - Focus rings map to `--elevation-focus` at review confidence.
  - `src/lib` is no longer treated as vendor code.
  - The codemod has `--include-vendor` and rewrites files named explicitly.
  - Minified CSS is extracted in linear time.

### Docs

- Every SKILL.md says how its scripts are run: by path, from the project root, via `${CLAUDE_SKILL_DIR}` and `${CLAUDE_PLUGIN_ROOT}`.
- The README quick start runs as written.
- The rebase recipe keeps the teammate's change; the before/after audit strands nothing in the stash.
- The handoff guide no longer describes a `build-tokens.mjs` that does not ship.
- The Tailwind v3 layer guidance matches what v3 emits.
- The Tailwind v4 "build error" claims are corrected.

### Also fixed

- **The migration's proposed `tokens.css`** now includes the starter's fixes: roles are declared where density and theme are set, the dark theme sets `color-scheme`, and there are `.inverse` roles, dark error text and control borders that meet AA.
- **The Supabase samples**:
  - The optimistic update throws on a rejected write (`throwOnError()`, and zero rows written), so the rollback and the message run.
  - The keyset sample validates the cursor before it goes into `.or()`.
- **The audit**: `url(icons.svg#add)` is no longer reported as a hardcoded colour.
- **Scripts run by path** no longer write `__pycache__` into the plugin.
- **The email quick start** copies a template into the project, not into the plugin.
- **The studio** writes into the repository when there is one, and makes a ZIP only when there is not.
- **The pattern examples** draw focus with an outline, not with `outline: none` and a box-shadow.

## 3.0.1 — 2026-09-21

38 bug fixes and the first regression suite (72 tests). The report is
`dev plans/web-design-suite-bugfix-report.md` in the project repository.
