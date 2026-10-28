# PY-A: content-model-to-ui scripts and the shared Python masters

Audited 2026-10-28 at main 8441ff0. Files read in full: `plugins/pro-web-design-suite/shared/project_config.py` (674 lines), `plugins/pro-web-design-suite/shared/dtcg.py` (1,684), `plugins/pro-web-design-suite/skills/content-model-to-ui/scripts/introspect_schema.py` (3,546), `plugins/pro-web-design-suite/skills/content-model-to-ui/scripts/scaffold_ui.py` (6,185), `plugins/pro-web-design-suite/skills/content-model-to-ui/SKILL.md`; `references/scripts.md` skimmed for the flags and the Prisma/Drizzle promises. Tests consulted: `tests/test_schema_sources.py` (34 tests), `tests/test_scaffold.py` (39), `tests/test_scaffold_frameworks.py` (23), `tests/test_project_config.py` (53), `tests/test_dtcg.py` (71), `tests/test_stacks.py` (17), `tests/test_policies.py` (20), by grep for the areas below. Commands run (all from the scratchpad `C:\Users\vybec\AppData\Local\Temp\claude\C--DEV-Pro-Web-Designer-Suite-Plug-in\d484deaf-54ec-437b-be40-bf3f426dae3e\scratchpad\py-a\`, fixtures `v1_columns.sql` … `v13.prisma`, `probe_shared.py`, `probe_dark.py` kept there): `python -B introspect_schema.py <fixture> -o <model>` for v1–v8 and v13, `python -B introspect_schema.py v1_columns.sql v7_other.txt -o v7.model.json`, `python -B scaffold_ui.py <model> --out <dir> --stack css-modules` for v3, v5, v6, v8, `python -B probe_shared.py` / `probe_dark.py` (load the two masters by path), `uv run --no-project --python 3.9 python -B …` for both scripts and the probe, `grep -rn` across the plugin for dead symbols and the documented flags. Nothing under `tooling/` was read; no file outside the report was written.

## Summary

18 findings: 1 critical, 6 high, 5 medium, 6 low. By class: 13 bugs, 2 gaps, 1 dead-code, 2 inconsistencies. No Python 3.9 problem (both scripts and both masters run under `uv --python 3.9`); the three B023 closures are harmless; every ARG001 is a signature kept uniform.

The three that matter most: (1) `_parse_create_table` tests `low.startswith("check")`/`"unique"`/`"exclude"` without a word boundary, so any column whose name begins with those words (`check_in`, `check_out`, `checksum`, `unique_code`, `exclude_from_search`) vanishes from `model.json` with no warning (PY-A-1, confirmed). (2) The DDL reader's CHECK handling fails on three realistic shapes — a `DROP CONSTRAINT` is never replayed so a re-created CHECK keeps the old option list, a table-level CHECK is discarded when one of its string literals happens to be another column's name, and `pg_dump`/`supabase db pull`'s `(price >= (0)::numeric)` yields no mirrored rule (PY-A-2, -3, -4, all confirmed). (3) `project_config._css_tokens` reads `html.dark`, `:root.dark`, `html[data-bs-theme="dark"]` and `html[data-mode="dark"]` as the default rule, and the cascade's "last wins" makes the dark theme's values the contract's defaults for every gate that reads tokens through it (PY-A-7, confirmed).

## Findings

### PY-A-1 · critical · bug
- **Where:** `plugins/pro-web-design-suite/skills/content-model-to-ui/scripts/introspect_schema.py:1142`
- **What:** Inside `CREATE TABLE`, an item is classed as a table constraint by `low.startswith(("primary key", "foreign key", "unique", "check", "exclude", "not null "))`. Three of the six have no trailing space or boundary, so a column whose name begins with `unique`, `check` or `exclude` is sent to `_apply_constraint_to_table`, matches none of its clause regexes, and is dropped silently.
- **Evidence:** `v1_columns.sql` declares `bookings(id, guest_name, check_in date not null, check_out date not null, checksum text, unique_code text, exclude_from_search boolean …, notes text)`; `introspect_schema.py v1_columns.sql -o v1.model.json` reports "1 entities, 3 columns" and the model's columns are `['id', 'guest_name', 'notes']`. No warning is printed.
- **Effect:** Every booking/reservation schema loses its check-in and check-out dates; a files table loses `checksum`; the screens, the Draft type, the zod/pydantic schemas and the column grants in `db/policies/` are all generated without them, and the user is told nothing.
- **Fix:** Match the clause keyword with a boundary: `re.match(r"(primary\s+key|foreign\s+key|unique|check|exclude|not\s+null)\b", low)` (or `KEEP_QUOTED`-style: a bare `check`/`unique` column name must be quoted anyway, so `\b` is safe). Regression test: the fixture above, asserting the eight columns, failing on `v4.0.1`.
- **Confidence:** confirmed

### PY-A-2 · high · bug
- **Where:** `plugins/pro-web-design-suite/skills/content-model-to-ui/scripts/introspect_schema.py:1406` (and `_apply_constraint_to_table`, which keeps no constraint names)
- **What:** `ALTER TABLE … DROP CONSTRAINT name` is swallowed by the "a constraint this parser does not know is still never a column" early return, so a CHECK or UNIQUE that a later migration drops and re-creates stays in the model beside its replacement. `_closed_set` returns the first CHECK that matches, i.e. the dropped one.
- **Evidence:** `v2_drop_constraint.sql` creates `orders_status_check check (status in ('pending','paid'))`, drops it, and adds it back with `('pending','paid','shipped','cancelled')`. The model's `status.checks` holds both expressions and `ui.options` is `['pending', 'paid']`.
- **Effect:** The form's select, the Badge cells, `z.enum([...])` and `Literal[...]` all refuse `shipped` and `cancelled`, which the database accepts: exactly the migration pattern Postgres forces on anyone changing a CHECK (CodeRabbit's "replayed in order" rule at line 1049 is honoured for policies but not for constraints).
- **Fix:** Record the constraint name with each CHECK/UNIQUE/FK it creates (from `CONSTRAINT name` inside CREATE TABLE and `ADD CONSTRAINT name`), and on `DROP CONSTRAINT` remove that entry (checks, unique_indexes, foreign_key, primary_key). Regression test with the fixture above, asserting the four options.
- **Confidence:** confirmed

### PY-A-3 · high · bug
- **Where:** `plugins/pro-web-design-suite/skills/content-model-to-ui/scripts/introspect_schema.py:1464` (`_check_target`)
- **What:** A table-level CHECK is attached to "the one column it mentions", found with a bare `\bname\b` search over the whole expression, string literals included. The masked matcher `_names()` (SQL_PIECES) exists forty lines above and is not used here.
- **Evidence:** `v3_check_target.sql`: `contact_methods(label, kind text not null, email text, phone text, constraint … check (kind in ('email', 'phone')))`. The model gives `kind.checks == []`, `control == "select"`, `options == []`, confidence low, plus a `.options` question — the closed set the schema states is gone.
- **Effect:** Any CHECK whose allowed values coincide with sibling column names (`kind in ('email','phone')`, `channel in ('email','sms')`, `type in ('image','file')`) is silently dropped; the scaffold then renders an empty `<Select>` (PY-A-14) and the server schemas lose the enum.
- **Fix:** `mentioned = [c for c in table.columns if _names(expr, c.name)]`. Regression test with the fixture, asserting two options on `kind`.
- **Confidence:** confirmed

### PY-A-4 · high · bug
- **Where:** `plugins/pro-web-design-suite/skills/content-model-to-ui/scripts/introspect_schema.py:2325` (also the `between` and `length()` regexes that follow)
- **What:** `_validate` reads a bound with `name\s*(>=|<=|>|<)\s*([\-\d.]+)`. Postgres deparses a CHECK on a `numeric` column as `(price >= (0)::numeric)` — the number is parenthesised and cast — so `pg_dump`, `supabase db pull` and `supabase db dump` output never match.
- **Evidence:** `v4_pgdump_cast.sql` (pg_dump's exact spelling). `price numeric(10,2)` with `CHECK ((price >= (0)::numeric))` gets only the mapper's invented `min 0` (`mirror: false`); `stock integer` with `CHECK ((stock >= 0))` gets the mirrored rule. A `CHECK (price > 0)` or `<= 1000000` on a numeric column yields nothing at all.
- **Effect:** SKILL.md promises "Migrations and a `pg_dump` or `supabase db pull` of them give the same model" and that every validation rule "names the constraint it mirrors"; for every numeric/decimal column read from a dump the rule is missing or marked invented, so the reviewer is told to drop it.
- **Fix:** Before the bound regexes, strip casts and the parentheses around a literal: `expr2 = SQL_CAST.sub("", expr)` then `re.sub(r"\(\s*(-?[\d.]+)\s*\)", r"\1", expr2)`; keep `source` as the original text. Regression test with the fixture, asserting `min 0, mirror true` on `price`.
- **Confidence:** confirmed

### PY-A-5 · high · bug
- **Where:** `plugins/pro-web-design-suite/skills/content-model-to-ui/scripts/introspect_schema.py:2397` and `:2400` (`_title_column`); `plugins/pro-web-design-suite/skills/content-model-to-ui/scripts/scaffold_ui.py:1977` (`emit_detail`)
- **What:** The title column is chosen before the name rules run and never excludes a credential: a `NOT NULL UNIQUE` text column wins the second rule even when it is `token`, `token_hash`, `api_key`, `secret`. The scaffold then writes `{record.token}` into the detail `<h1>` while `emit_types` deliberately leaves `token` out of the read type.
- **Evidence:** `v5_token_title.sql` (`sessions(id, user_id, token text not null unique, expires_at, created_at)`). Model: `title_column == "token"`, `title_is_placeholder == false`, the `.title_column` question defaults to `token`, while `token.ui` is `password-input`, `never_display: true`, placement all false. Scaffold: `SessionDetail.tsx:38` is `{record.token}`; `sessions.types.ts:4` says "token: write-only — deliberately absent from the read type so it cannot be rendered". `SessionsList.tsx` has no link cell (the title is not a list column; see PY-A-6).
- **Effect:** The generated detail page does not type-check (`Property 'token' does not exist on type 'Session'`), and the only fix a user is likely to make — adding `token` back to the interface — renders the credential in the h1 and the browser tab, the one thing the `password-input` rule says must never happen.
- **Fix:** In `_title_column`, skip a column the credential rule (`NAME_RULES[0]`) matches, and set `title_is_placeholder` when nothing else qualifies; in `emit_detail`/`emit_list`/the Vue and Svelte twins, fall back to the primary key when the title column is `never_display`. Regression test: the fixture, asserting the title is not `token` and the scaffold's detail uses the key.
- **Confidence:** confirmed

### PY-A-6 · high · bug
- **Where:** `plugins/pro-web-design-suite/skills/content-model-to-ui/scripts/scaffold_ui.py:1716` (`emit_list`, table layout; the Vue and Svelte lists at `:3951` and `:4995` are the same)
- **What:** In the table layout the only link to the detail page is placed on the cell whose column is the title. When the title is not among the list columns — always the case when the title is the placeholder primary key, because `_assign_placement` (`introspect_schema.py:2467`) skips a `hidden` column — no cell gets `<a>`, so the list has no way to reach the detail.
- **Evidence:** `v6_no_title.sql`: `readings(id, sensor_id, value numeric, taken_at, quality)` has no text column, so `title_column == "id"`, `title_is_placeholder == true`, `index_layout == "table"`, list columns `['sensor_id', 'value', 'taken_at', 'quality']`. `grep -E "href|styles.link|<a " v6_out/features/readings/ReadingsList.tsx` prints nothing. The card layout is not affected (its `href` is on the title expression, which falls back to the key).
- **Effect:** Every table without a textual column (readings, events, line items, measurements, log rows) gets an index with rows that cannot be opened; SKILL.md §3 says one entity implies "an index, a detail".
- **Fix:** When `title not in cells`, put the link on the first listed cell (or add a leading key cell), in all three frameworks. Regression test with the fixture, asserting an `href` in the table body.
- **Confidence:** confirmed

### PY-A-7 · high · bug
- **Where:** `plugins/pro-web-design-suite/shared/project_config.py:428`–`429` and `:537`–`540` (`_css_tokens`)
- **What:** A rule is a default when its selector *starts with* `:root`/`html`/`:where(:root)`/`*` and `THEME_OR_DENSITY` (`[data-theme=`/`[data-density=`) does not appear in it. A class-based or differently-named theme selector passes both tests, and "the cascade: the last one wins" then makes the theme's value the default.
- **Evidence:** `probe_dark.py` writes `:root { --bg: white; } <sel> { --bg: black; }` and reads it back: `html[data-bs-theme="dark"]`, `html[data-mode="dark"]`, `:root.dark`, `html.dark` and `:root:where(.dark)` all give `--bg = black`; only `:root[data-theme="dark"]` gives `white`. `probe_shared.py` on a two-rule sheet gives `{'--bg-page': 'black', '--fg-default': 'white', …}`.
- **Effect:** Tailwind's `darkMode: 'class'` (`html.dark`/`.dark` on the root), Bootstrap 5.3's `[data-bs-theme]`, and every `data-mode`/`data-color-scheme` convention feed the dark palette to `read_tokens()` as the defaults, so the contrast pairs, `diff_system`, the token diff hook and the Figma export all reason about the wrong values, with no problem reported. (`extract_system.py:1054` uses the same `data-theme`-only rule, so the two readers agree with each other and are wrong together; that file is outside this pass.)
- **Fix:** Accept a default rule only when every selector in the list is exactly one of the root forms, optionally followed by `, [data-theme]`-style bare attribute selectors; anything compound (`:root.x`, `html[…=…]`, `:root:where(…)`, `:root:has(…)`) is an override, as the docstring already intends ("no theme or density selector that names a value"). Keep `extract_system` and `project_config.mjs` in step (`test_project_config` holds the three together). Regression test: the probe's selectors, asserting `white`.
- **Confidence:** confirmed

### PY-A-8 · medium · gap
- **Where:** `plugins/pro-web-design-suite/skills/content-model-to-ui/scripts/introspect_schema.py:3079` (`parse_prisma`) and the `fidelity["missing"]` list at `:3148`
- **What:** A Prisma implicit many-to-many (`tags Tag[]` on one model, `posts Post[]` on the other, no `@relation(fields:)`) is skipped on both sides, so neither the `_PostToTag` join table nor a `many-to-many` edge reaches the model, and `fidelity.missing` does not say so.
- **Evidence:** `v13.prisma` (Post/Tag with implicit m:n): the model has two entities, zero relationships, and no entry in `missing` mentions many-to-many.
- **Effect:** The detail pages lose their `TODO(multi-combobox)` and the policies lose the join table, silently; `references/scripts.md` line 21 promises "keys with their `onDelete` from `@relation`" and lists what Prisma lacks, but not this.
- **Fix:** Pair the two list fields and synthesise Prisma's join table (`_AToB`, models sorted, columns `A`/`B` with cascade keys) as a `join` table, or at minimum append "implicit many-to-many relations" to `missing` and say so in scripts.md. Test either way.
- **Confidence:** confirmed

### PY-A-9 · medium · bug
- **Where:** `plugins/pro-web-design-suite/skills/content-model-to-ui/scripts/introspect_schema.py:3482` (`main`, the several-files check; the guarded call is at `:3491`)
- **What:** With more than one input, `detect_format()` is called for each file *outside* the `try … except SchemaError`, so a file it cannot classify raises straight through.
- **Evidence:** `introspect_schema.py v1_columns.sql v7_other.txt -o v7.model.json` prints a traceback ending in `SchemaError: Cannot tell what v7_other.txt is. Pass --format …` instead of the one-line message and exit 1 the docstring promises.
- **Effect:** A stray file in `supabase/migrations/*` (a README, a `.keep`) turns the documented glob invocation into a traceback.
- **Fix:** Wrap the per-file detection in the same `try`, or catch `SchemaError` there and print `introspect_schema: <file>: <message>`; return 1. Regression test with a two-file run.
- **Confidence:** confirmed

### PY-A-10 · medium · bug
- **Where:** `plugins/pro-web-design-suite/skills/content-model-to-ui/scripts/scaffold_ui.py:5766` (`emit_schema_zod`); pydantic's rule at `:5860`–`5863`
- **What:** Every instant column becomes `z.string().datetime({ offset: true })`, which accepts `Z` or an explicit offset but rejects a string with no zone. The scaffold's own form posts `datetime-local` values (`2026-10-28T09:00`, no offset), and a `timestamp without time zone` column (`temporal.timezone == "ambiguous"`, every Prisma `DateTime`) cannot carry one. The pydantic twin uses plain `datetime` for the naive case and `AwareDatetime` only when `aware` is true, so the two server schemas disagree.
- **Evidence:** Lines cited; `emit_actions` (`:2551`) already admits the gap with "a datetime-local value has no offset, and the schema wants one".
- **Effect:** A naive timestamp column's draft can never pass the zod schema; an aware column's draft fails until the user hand-writes the offset the TODO describes. The SKILL promises the server schema mirrors "the same constraints the form reads".
- **Fix:** For `aware == False` emit `.datetime({ offset: true, local: true })` (zod ≥3.23), and decide once whether the form appends the offset (then keep `offset: true`) or the schema accepts local time; make pydantic match. Test the emitted string for both column kinds.
- **Confidence:** likely (zod semantics from its docs; not executed)

### PY-A-11 · medium · bug
- **Where:** `plugins/pro-web-design-suite/skills/content-model-to-ui/scripts/scaffold_ui.py:2069` (`control_jsx`, radio-group), `:594` (`FIELD_TSX` root), `:2323` (the summary link); the Vue (`:3687`) and Svelte (`:4742`) controls are the same
- **What:** The error summary links each entry to `'#' + fieldId(name)`, "because on a long form the invalid field is usually off-screen". A radio group gets no element with that id: `RadioGroup` is rendered without `id`, `Field`'s `<fieldset>` root carries none, and only the `<legend>` gets `${id}-label`.
- **Evidence:** `v8_out/features/shows/ShowForm.tsx:93` `href={'#' + fieldId(name)}`; `:152` `id={fieldId('size')}` is the `Field` prop, `:159` `<RadioGroup` has no `id`, `:164` `labelledBy={fieldId('size') + '-label'}`; `v8_out/ui/Field/Field.tsx:64` `<Root` has no `id` attribute.
- **Effect:** For every radio group (any CHECK/enum of ≤3 values that is not a state word) the summary's link is a dead anchor: focus and scroll go nowhere, which defeats the stated purpose of the summary.
- **Fix:** Put `id={id}` on the fieldset root when `group`, or pass `id={fieldId(q)}` to `RadioGroup`'s container (keeping `-label` on the legend), in all three kits. Regression test: the form contains an element with `id="shows-size"`.
- **Confidence:** confirmed

### PY-A-12 · medium · bug
- **Where:** `plugins/pro-web-design-suite/shared/dtcg.py:1396` (`_shadow_layer`) and `:1465` (`_css_value`, the shadow branch runs before `_border` and the fallback)
- **What:** With no literal colour, `_shadow_layer` takes the last reference as the colour, so any value made of three or four references (and nothing else) is typed `shadow`, whatever the tokens are.
- **Evidence:** `probe_shared.py`: `document([("--space-1","4px"),("--space-2","8px"),("--space-3","16px"),("--inset-card","var(--space-1) var(--space-2) var(--space-3)")])` writes `inset.card` as `{"$type": "shadow", "$value": {"color": "{space.3}", "offsetX": "{space.1}", "offsetY": "{space.2}", "blur": 0px, "spread": 0px}}` with no problem reported.
- **Effect:** A padding/inset shorthand built from spacing tokens reaches Figma as a shadow whose colour is a dimension; a reader of the file (figma-variables-sync, a resolver) sees a typed composite that is wrong rather than a `notWritten` entry it could act on.
- **Fix:** Require at least one literal length or a literal colour in a layer before calling it a shadow, or require the colour reference to resolve to a `color`-typed token (the types are known in `document()`); otherwise report it as unsupported. Regression test with the probe's four tokens.
- **Confidence:** confirmed

### PY-A-13 · low · bug / dead-code
- **Where:** `plugins/pro-web-design-suite/skills/content-model-to-ui/scripts/introspect_schema.py:1984` (call) and `:2405` (`_subtitle_column`)
- **What:** `screens.subtitle_column` is computed before the mapping loop fills `col.ui`, so its first test (`c.ui.get("control") in ("textarea", "rich-text")`) can never fire; only the name regex works. And nothing reads the field: `grep -rn subtitle_column` finds the two lines in introspect and nothing in scaffold_ui, the references or the tests.
- **Evidence:** `v8_subtitle.sql` (`blurb varchar(1000)` → control `textarea`): `subtitle_column` is `None`.
- **Effect:** A dead key in `model.json`, misleading to a reviewer.
- **Fix:** Either move the assignment after the loop and have the card/feed layouts use it for the first meta line, or delete it. Test accordingly.
- **Confidence:** confirmed

### PY-A-14 · low · gap
- **Where:** `plugins/pro-web-design-suite/skills/content-model-to-ui/scripts/scaffold_ui.py:2054`–`2060` (`control_jsx`, select); the Vue and Svelte twins at `:3677` and `:4730`
- **What:** A `select` whose option list is empty (a state-word text column with no CHECK, no enum and no `.options` answer — the model sets `options: []` and confidence `low`) is rendered as a real `<Select>` with no options (not even the blank when the column is required), not as a `ControlStub`.
- **Evidence:** `v3_out/features/contact_methods/ContactMethodForm.tsx:139–150`: `<Select … required={true}>` … `</Select>` with no `<option>`.
- **Effect:** The one control shape the docstring says it refuses — "a plausible-looking wrong control" — ships for every unconstrained `status`/`type`/`kind` column until the `.options` question is answered.
- **Fix:** When `not opts and not spec.get("labelColumn")`, emit `ControlStub control="select" reason="the closed set is unknown; answer the .options question or add a CHECK"`. Test with the v3 fixture.
- **Confidence:** confirmed

### PY-A-15 · low · dead-code
- **Where:** `introspect_schema.py:95` (`CONTROLS`), `:345` (`TIMESTAMP_SUFFIX`), `:667` (`COL_MODIFIER_SPLIT`); `scaffold_ui.py:93` (`NATIVE_CONTROLS`), `:127` (`TS_KEYWORDS`)
- **What:** Five module constants have no reference anywhere in the plugin or its tests beyond their definition (`grep -rn -w` over `skills shared hooks mcp tools tests`). `CONTROLS` is described as "the closed set of controls the scaffolder knows how to render … keep this closed", but nothing checks an emitted control against it. Separately, the `password-input` branches of `control_jsx`, `vue_control` and `svelte_control` (`:2127`/`:2136`, `:3728`/`:3737`, `:4783`/`:4792`) are unreachable from a model the introspector writes: the only rule that assigns `password-input` also sets `never_display`, which makes `placement.form` false and `Answers.in_form` (`:227`) refuse it.
- **Evidence:** the grep counts (1 each) and the `in_form` logic cited.
- **Effect:** Maintenance noise; the "closed vocabulary" guarantee is a comment, not a check.
- **Fix:** Delete `TIMESTAMP_SUFFIX`, `COL_MODIFIER_SPLIT`, `NATIVE_CONTROLS`, `TS_KEYWORDS`; keep `CONTROLS` and assert in `map_columns` (or a test) that every `ui.control` is in it. Leave the password branches if a hand-edited model is meant to reach them, and say so in a comment.
- **Confidence:** confirmed

### PY-A-16 · low · inconsistency
- **Where:** `plugins/pro-web-design-suite/skills/content-model-to-ui/scripts/scaffold_ui.py:1694` (`href = f"'/{name}/' + String(row.{pk})"`), `:1732` (`key={String(row.$pk)}`), `:1979` (`String(record.{pk_detail})`)
- **What:** The React list and detail write the primary key with `row.<pk>` directly, while the Vue and Svelte emitters use `member('row', pk)` (which brackets a non-identifier). A key column named like `order-id` or `2fa` (the E3 case the audit fixed for form fields) produces invalid TSX in React only.
- **Evidence:** lines cited; `member()` at `:164` exists for this.
- **Effect:** One framework breaks on a key name the other two handle.
- **Fix:** Use `member("row", pk)` / `member("record", pk)` in the three places. Test with a quoted key name.
- **Confidence:** likely (by reading; not executed)

### PY-A-17 · low · bug
- **Where:** `plugins/pro-web-design-suite/skills/content-model-to-ui/scripts/scaffold_ui.py:2826`–`2834` (`emit_states`: `headline="$headline"` at `:2826`, `body="$body"` at `:2829`, the action label) and `:2202` (`_form_sections`: `label="$label"`); `:2085` (`control_jsx`, Toggle `label="…"`)
- **What:** Copy from the answers file and labels from `humanise()` are interpolated into JSX attribute strings without escaping, whereas the Vue and Svelte emitters route the same text through `vue_static`/`svelte_static`. A double quote in an `empty_state.headline` answer (`No "projects" yet`) ends the attribute early.
- **Evidence:** lines cited.
- **Effect:** One malformed React file per quoted answer; the other two frameworks are fine.
- **Fix:** Emit the attribute as an expression (`headline={json.dumps(text)}`) or escape with `html.escape(text, quote=True)`. Test with a quoted answer.
- **Confidence:** likely (by reading)

### PY-A-18 · low · inconsistency
- **Where:** `plugins/pro-web-design-suite/skills/content-model-to-ui/scripts/introspect_schema.py:3431` (argparse help for `schema`) and the module docstring "WHAT IT READS" (`:19`–`:34`)
- **What:** Both still list `.sql`, `.ts` and `.json` only; Prisma and Drizzle (3.6.0, documented in SKILL.md and `references/scripts.md`) are missing from the script's own `--help` and docstring, while `--format` already offers them.
- **Evidence:** lines cited; `grep` of scripts.md shows every flag documented, so this is the only drift found between the CLI and its documentation.
- **Effect:** `--help` understates what the script reads.
- **Fix:** Add the two formats to both texts. No test needed.
- **Confidence:** confirmed

## Static-analysis candidates, resolved

- `introspect_schema.py:885` B023 — harmless: `narrowed()` (`:882`) closes over `narrowing`, which is rebound per table, but it is only called inside the same `for t in model.tables` iteration.
- `introspect_schema.py:3319` B023 — harmless: `cols_of()` (`:3318`) closes over `keys` from `for _, table, keys, refs, extra in tables` and is called only within that iteration.
- `introspect_schema.py:3341` B023 — harmless: the `lambda x: keys.get(…)` inside `re.sub` runs immediately, in the same iteration.
- `introspect_schema.py:1260` ARG001 (`_apply_constraint_to_table(model, …)`: `model` unused) — fine-by-design, kept symmetrical with `_apply_alter_action(model, table, action)`.
- `introspect_schema.py:1941` ARG001 (`_relationship_control(…, col)`: `col` unused) — fine-by-design; the call sites pass the column or `None`, and the docstring says the real input (the parent's row count) is not in the schema. Not a wired-but-forgotten feature: the cardinality answer is applied in `scaffold_ui.field_spec`.
- `introspect_schema.py:2132` ARG001 (`_by_type(…, table, …)`) and `:2298` (`_validate(…, model)`) — fine-by-design, uniform with the other mapping helpers.
- `introspect_schema.py:3400` ARG001 (`build_model(path, …)`) — fine-by-design; `path` is used by `detect_format` beside it.
- `scaffold_ui.py:1358, 1677, 1869, 2790, 3925, 4054, 4148, 4970, 5113, 5202` ARG001 (`model` unused) and `:2968` (`emit_index(table, ans)`: `ans` unused) — fine-by-design: every emitter takes `(table, model, ans)` so `build_files` can call them uniformly; nothing is left unwired (the answers each emitter needs are read through `ans`).
- `introspect_schema.py:642` and `:3110` PIE810 — style only (`startswith` twice instead of a tuple); no behaviour difference.

## What is covered well

- `project_config.py`: the config validation (unknown keys, shapes, `schema` as a non-bool), `..`-relative paths, `find_config` stopping at `.git`, `refuse_overwrite`'s identity comparison, BOM/UTF-16/UTF-32 decoding in `decode_text`/`text_encoding`, `_css_blocks`' handling of quotes and brackets (a `;` in a data URL), `@layer`-only nesting, the `ramps`/`scales` merge rule in `read_tokens`, the deprecation record, and the by-path loading of `dtcg.py` that no stray module named `dtcg` can shadow. The `[data-theme]` default and theme override cases are tested (`test_project_config.py:147–157`); the hole is only the class/other-attribute selectors in PY-A-7.
- `dtcg.py`: colour conversion in both directions (hex, rgb legacy and modern, hsl, hwb, lab/lch, oklab/oklch, `none`, `color()` spaces, the sRGB `hex` fallback), `$extends` chains and cycles, property-level `$ref` inlining with a fan-out budget, depth and size guards, reference-cycle removal, Tokens Studio sets/themes/math with memoised lookups, the resolver's folder sandbox (`outside()`, `OutsideFolder`, URL refusal, pointer rules), the `$root` naming, the `notWritten` record, and deterministic output ordering. Python 3.9 clean.
- `introspect_schema.py`: `strip_sql_comments`/`split_top_level`/`_balanced_slice` respect `''` escapes, `"…"` names and `$$`/`$tag$` bodies; `unquote_identifiers` keeps reserved and mixed-case names quoted; `NOT NULL` inside a CHECK does not make a column NOT NULL; `normalise_type` handles schemas, arrays, `timestamp(6)`, `geography(Point, 4326)`; the policy parser and `security_pass` (restrictive vs permissive, `true` conditions, pinned authority columns, column-privilege replay) are careful and tested; gen-types (Prettier-wrapped unions, `Database["public"]["Enums"]`, `isOneToOne`), the JSON guards, the Drizzle reader and the camelCase name signals are all exercised by `test_schema_sources.py` and `test_policies.py`. CRLF and BOM input are fine (`json.detect_encoding`, `splitlines`).
- `scaffold_ui.py`: no write escapes `--out` (`unsafe_name` plus the resolved-parent check), existing files are skipped without `--force`, output is byte-deterministic (every set is sorted before it is joined; verified by reading each `kit`/`used`/`invented` site), `--strict` refuses on a blocking finding, `js_string`/`member`/`prop_key` cover the E3 names in forms and server schemas, SQL identifiers and literals in `db/policies/` are quoted, policy names are cut to 63 bytes with a hash, and the `$$` tag in the smoke test avoids a name that contains `$$`. Both scripts run under Python 3.9 (`uv run --python 3.9`).
