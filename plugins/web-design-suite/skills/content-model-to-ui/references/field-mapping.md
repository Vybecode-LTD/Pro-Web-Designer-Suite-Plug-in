# Field Mapping

A column type does not determine a control. This file is the decision procedure that does.

`text` could be a single-line input, a textarea, a rich editor, a slug field, a read-only display or nothing at all. The type is the same in all six cases. What separates them is *semantics* — what the column is called, how long it is allowed to be, whether a human writes it, how many distinct values it holds, and what the user is trying to do when they touch it. Most of that is in the schema. The rest is in someone's head, and §10 is the list of what has to be asked.

Ground truth for the vocabulary is `references/token-contract.md`. The implementation is `scripts/introspect_schema.py`; every rule below is a rule in that file, and every `signal` string it emits is quoted from here.

## Contents

1. [The mapping order](#1-the-mapping-order)
2. [The signals](#2-the-signals)
3. [Type → candidate controls](#3-type--candidate-controls)
4. [Semantic overrides by name](#4-semantic-overrides-by-name)
5. [Closed sets: enums, CHECKs and cardinality](#5-closed-sets-enums-checks-and-cardinality)
6. [Relationships](#6-relationships)
7. [Money](#7-money)
8. [Dates, times and zones](#8-dates-times-and-zones)
9. [Validation](#9-validation)
10. [What the schema cannot tell you](#10-what-the-schema-cannot-tell-you)

---

## 1. The mapping order

Rules are evaluated in this order and **the first match wins**. Order is the whole design: an image column called `avatar_url` matches both the URL rule and the image rule, and which one fires decides whether the user gets an upload with a preview or a text box to paste a link into.

| # | Gate | Beats everything below because |
|---|---|---|
| 1 | **Not editable by anyone** — generated, identity, surrogate PK | A beautiful control on a column the database owns is a lie. It cannot be saved. |
| 2 | **Search/index columns** (`tsvector`) | Machinery. It powers the search box; it is never a field. |
| 3 | **Foreign key** | The control is a function of the *parent's size*, not of this column's type (§6). |
| 4 | **Closed set** — enum type, or a `CHECK … IN (…)` | A closed set is a closed set however it was spelled (§5). |
| 5 | **Name signal** | The layer the type system cannot carry (§4). |
| 6 | **Temporal type** | The one place the type is authoritative and a wrong guess is invisible until a user in another zone complains (§8). |
| 7 | **Type plus weak signals** | The fallback. Most `low` confidence lands here. |

A name signal that contradicts its type loses. `is_active text` is a bad schema, but rendering a switch over a free-text column is worse — the switch can write `true` into a column whose other 40,000 rows say `yes`.

Every proposal carries a confidence:

| Level | Means | What to do |
|---|---|---|
| `high` | The schema said so | Skim it |
| `medium` | A strong signal with a plausible alternative | Read the signal, agree or override |
| `low` | A default standing in for a decision nobody made | Answer the question it generated |

---

## 2. The signals

Nine facts, in rough order of how much they tell you.

| Signal | Reads on | What it settles |
|---|---|---|
| **Column name** | everything | The single strongest signal. `price_cents`, `is_active`, `slug`, `created_at` each determine a control outright |
| **Generated / identity / default** | every type | Whether a human supplies the value at all. Decides `editable`, which decides whether the column appears on the form |
| **Foreign key** | scalar types | That the value is a *reference*; the parent's row count then picks the control |
| **Enum type or CHECK … IN** | any | That the set is closed, and exactly what is in it |
| **Length constraint** | textual | Single line vs paragraph vs document, and the input's own `maxLength` |
| **Unique index** | any | That the value is an identifier a person reads and types — and that validation needs a server round trip |
| **Nullability** | any | `required`, and whether an "event that may not have happened" needs an empty rendering |
| **CHECK with a comparison** | numeric, textual | `min` / `max` / `pattern`, and whether a small integer is a stepper or a typed number |
| **Distinct-value cardinality** | any | Select vs combobox vs picker. **Not in the schema.** Ask, or measure with `SELECT count(DISTINCT …)` |

Cardinality is the one signal worth going to the database for. One query answers it for every reference column at once:

```sql
select c.table_name, c.column_name,
       (select reltuples::bigint from pg_class
         where oid = (quote_ident(ccu.table_name))::regclass) as approx_parent_rows
from information_schema.table_constraints tc
join information_schema.constraint_column_usage ccu using (constraint_name)
join information_schema.columns c
  on c.table_name = tc.table_name
join information_schema.key_column_usage kcu
  on kcu.constraint_name = tc.constraint_name and kcu.column_name = c.column_name
where tc.constraint_type = 'FOREIGN KEY';
```

`reltuples` is an estimate and that is fine — the thresholds in §6 are an order of magnitude apart.

---

## 3. Type → candidate controls

The default is in **bold**. Everything else in the row is reachable by a signal.

| Postgres type | Candidates | The signal that picks |
|---|---|---|
| `text` | **text-input** · textarea · rich-text · slug-input · readonly-text · json-editor | Name (§4). Unbounded `text` with no name signal is the most ambiguous shape there is — that is a `low` and a question |
| `varchar(n)` n ≤ 255 | **text-input** | The bound. An author who meant "a paragraph" writes `text`; `varchar(140)` is someone being careful about a line |
| `varchar(n)` 256–2000 | **textarea** | Past a line, short of a document |
| `varchar(n)` n > 2000 | **rich-text** | Long enough that users want formatting — confirm before taking an editor dependency you cannot remove |
| `char(n)` | **text-input** | Almost always a code (`char(3)` = ISO currency). Check the name for a standards list |
| `citext` | as `text` | Case-insensitive means it is an identifier people type: email, handle, slug |
| `integer` / `smallint` | **number-input** · stepper · currency-input · select | `_cents` suffix → money. `CHECK … <= n` with small n, or a count-ish name → stepper. FK → §6 |
| `bigint` | **number-input** · currency-input | Same rules. A `bigint` money column is minor units of something that got big |
| `numeric(p,s)` | **number-input** · currency-input · percent-input | `s = 2` is usually money, but say so before formatting it as money. Exact decimal — safe to display directly |
| `real` / `double precision` | **number-input** | Never money. If a money column is a float, that is a schema bug worth raising before a UI bug |
| `boolean` | **switch** · checkbox | `is_` / `has_` prefix → switch (acts immediately). Otherwise checkbox (part of a form submission) |
| `date` | **date-picker** | Hard rule: a date is a calendar day. It must never become a datetime (§8) |
| `timestamptz` | **datetime-picker** · readonly-timestamp | A system timestamp name (`created_at`, `updated_at`) → read-only |
| `timestamp` (no tz) | **datetime-picker** + a warning | Cannot answer "when" for anyone outside the server's zone. Treat as a schema bug and ask |
| `time` / `timetz` | **time-picker** | Wall-clock |
| `interval` | **number-input** + unit select | No good native control. Usually should be two columns or an integer of minutes |
| `uuid` | **hidden** · readonly-text · reference control | PK with a default → hidden. FK → §6. A bare non-key uuid is an external id — read-only |
| `jsonb` / `json` | **json-editor** · key-value-editor · real fields | Nothing but the name. A JSON textarea in a product UI is an admission nobody knew what the column was for — §10 |
| `enum` | **select** · radio-group · multi-select | Option count and whether it is a state word (§5) |
| `T[]` | **tag-input** · multi-select · multi-combobox | Text array → tags. Array of ids → it should have been a join table; say so |
| `bytea` | **file-upload** | Bytes in a column. Move it to Storage — the row gets read on every list query |
| `tsvector` | **hidden** | Powers the search box, never appears |
| `inet` / `cidr` / `macaddr` | **text-input** with a pattern | Read-only in almost every product UI |
| `geography` / `geometry` / `point` | **geo-point** | A map picker, never two number boxes. Two number boxes is how you get a store in the Atlantic |
| `money` | **currency-input** | And raise it: Postgres `money` carries no currency and rounds by a session setting. `bigint` cents is the fix |

---

## 4. Semantic overrides by name

The layer that makes this skill worth running. Each of these beats the type default, subject to the contradiction rule in §1.

| Name pattern | Control | Why the type was not enough |
|---|---|---|
| `password`, `*_hash`, `api_key`, `*_token`, `secret` | **password-input**, write-only | The value must never be rendered back. It is absent from the read type entirely, so it *cannot* be |
| `email`, `*_email` | **email-input** | `type="email"` gets the right mobile keyboard and the right autofill. Both matter more than the validation |
| `url`, `uri`, `link`, `website`, `webhook_url` | **url-input** | Same: keyboard, autofill, and a scheme check |
| `slug`, `handle`, `permalink` | **slug-input** | Derived from the title, uniquely indexed, lowercased — and the thing a URL breaks on when it changes. Derive until the user edits it by hand, then **stop** |
| `phone`, `mobile`, `tel`, `fax` | **tel-input** | Format on blur, never on keystroke — reformatting mid-entry moves the caret and people lose their place |
| `*_cents`, `*_minor`, `*_pennies` | **currency-input**, minor units | The integer is NOT a quantity. See §7 |
| `price`, `amount`, `cost`, `total`, `fee`, `balance`, `salary` | **currency-input**, unit unknown | A money word. Confirm the storage unit before formatting it |
| `rate`, `percent`, `pct`, `ratio`, `margin` | **percent-input** | Confirm whether `0.15` or `15` is stored. Getting it wrong is a 100× error that looks plausible |
| `is_*`, `has_*`, `can_*`, `should_*`, `allow_*` | **switch** | The prefix says "a thing that is either on or off right now", which is a switch. A checkbox says "part of what I am submitting" |
| `*_enabled`, `*_active`, `*_published`, `*_archived` | **switch** | Same shape, suffix form |
| `avatar`, `image`, `photo`, `cover`, `banner`, `logo`, `thumbnail` (± `_url`/`_path`/`_key`) | **image-upload** | A storage object, not a string the user types. **This rule must be evaluated before the URL rule** — `avatar_url` matches both, and a text box where an upload belongs is the single most common generator failure |
| `file`, `attachment`, `document`, `asset` (± suffix) | **file-upload** | Same |
| `description`, `body`, `content`, `summary`, `excerpt`, `bio`, `notes`, `message` | **textarea** | A single-line input truncates long-form visually, and users write less because the box looks small. The box is the brief |
| `status`, `state`, `stage`, `kind`, `type`, `category`, `role`, `visibility` | **select** | Almost always a closed set even when the column is plain text. If nothing constrains it, that is a schema gap worth naming, not a UI problem to route around |
| `sort_order`, `position`, `rank`, `display_order` | **hidden** | Users reorder by dragging rows. Nobody has ever wanted to type `70` into a "sort order" box |
| `metadata`, `settings`, `config`, `options`, `payload`, `custom_fields` | **json-editor** | A bag. It needs a human to name the real keys before it can be anything better |
| `currency`, `currency_code` | **select**, ISO 4217 | 180 closed values nobody types — and the other half of every money column |
| `country`, `locale`, `language`, `timezone` | **combobox**, standards list | Long, closed, searchable. Never a text input |
| `color`, `brand_color` | **color-picker** | |
| `tags`, `labels`, `keywords`, `skills` | **tag-input** | A plural bag of short strings |
| `lat`, `lng`, `coordinates`, `geom` | **geo-point** | |
| `*_at`, `*_on`, `*_date` | temporal, per §8 | |
| `*_id` with a FK | reference, per §6 | |

**The label is not the column name.** `price_cents` labels as "Price" — the minor-unit suffix is a storage detail, and a user who reads "Price Cents" on a form has been shown the database. `category_id` labels as "Category". Strip the suffix; keep the meaning.

---

## 5. Closed sets: enums, CHECKs and cardinality

An enum type and a `CHECK (col IN ('a','b','c'))` are the same fact. Treat them identically.

| Options | Control | Why |
|---|---|---|
| 2, and it is a state | **switch** | If the enum is `active`/`inactive`, it is a boolean wearing a costume |
| 2–3, and the choice is the point of the screen | **radio-group** | Every option visible, one tab stop, no click-to-discover |
| 2–3 on a **state word** (`status`, `role`, `type`) | **select** | A status is one field among twenty. Three stacked radios cost more vertical space than they buy, and people *change* a status from a list rather than surveying it |
| 4–20 | **select** | Everything visible in one open, no fetch |
| 20–200 | **combobox** | Type-to-filter. A 60-item select is a scroll, and people do not scroll a select |
| 200+ | **combobox** with async options | Fetch on keystroke, debounced |
| Any count, multi-valued | **multi-select** / **multi-combobox** | An array or a join table |

**A "status" column with no constraint is a bug in the schema, not a problem for the UI.** If the set is genuinely closed, it belongs in the database as an enum or a CHECK, or the UI and the data will disagree within a month — someone will write `Shipped` where every other row says `shipped`, and the filter will silently drop their rows. Say this out loud rather than quietly rendering a select over values the database will happily contradict.

---

## 6. Relationships

Three shapes. Each has a control set that changes with cardinality, and the cardinality is the thing no schema carries.

### 6.1 Many-to-one (this row points at one parent)

The control is a function of **how many rows the parent holds**, not of anything about this column.

| Parent rows | Control | Why it stops working past the threshold |
|---|---|---|
| < ~20 | **select** | Every option visible in one open, zero round trips. Past 20, people stop reading and start scrolling |
| ~20 – ~5,000 | **combobox** | Type-to-filter over a set you can fetch once and keep. Past a few thousand, the payload and the client-side filter both start to hurt |
| > ~5,000 | **record-picker** — a modal with its own search, paging and empty state | At this size the picker is a small search product. Trying to make a combobox do it produces a control that is slow, unfilterable and impossible to keyboard |
| Unknown | **combobox** | It degrades acceptably in both directions, which no other choice does |

The thresholds are an order of magnitude apart on purpose: you do not need a precise row count, only the right decade.

Two properties belong to the relationship, not the control:

- **Which parent column is the label.** A picker showing uuids is a picker nobody can use. Usually the parent's title, but not always — an invoice picker wants the number, not the customer name.
- **Whether the FK is nullable.** A nullable FK means the row can stand alone, so the control needs an explicit "none" option with real words ("No category"), not a blank first entry. A blank entry is indistinguishable from "I have not chosen yet".

### 6.2 One-to-many (children point at this row)

`ON DELETE` is the signal, but it is not the whole test. A child is **owned**
only when it ALSO has no title of its own — `CASCADE` alone says the rows
cannot outlive the parent, not that they are anonymous details of it:

| `ON DELETE` | Has a title of its own? | Meaning | Control |
|---|---|---|---|
| `CASCADE` | no | The children do not outlive the parent and are not named things in their own right — they are **owned** | **inline-subtable** inside the parent's form: add, edit and remove rows in place, saved in one transaction with the parent. Order lines, survey options, image variants |
| `CASCADE` | yes | The children do not outlive the parent, but each is still a record someone looks up by name (e.g. `users` under `organizations`) | **linked-list**, same as independent — full CRUD screens of its own, linked from the parent |
| `RESTRICT` / `NO ACTION` / `SET NULL` | — | The children survive — they are **independent** | **linked-list** on the parent's detail page: a few rows, a count, and a link to their own screens. Never an editor |

Getting this backwards is expensive in both directions. Editing independent records inline means two screens can write the same row and neither knows about the other. Giving owned children their own CRUD screens means a user can create an order line with no order.

Generated types from `supabase gen types typescript` **do not carry `ON DELETE`**, so from that source every one-to-many falls back to `linked-list`. That is one of the concrete reasons to prefer the DDL (see `supabase-integration.md` §1).

### 6.3 Many-to-many (via a join table)

**Join-table detection:** a table with exactly two foreign keys and no other meaningful column. "Meaningful" excludes a surrogate `id`, `created_at`/`updated_at`, and an ordering column — those are plumbing. A composite primary key on exactly the two FK columns confirms it.

A join table is an **edge, not an entity**. It gets no screens of its own. It shows up as a control on both sides, and the two sides are usually different controls because the two parents are usually different sizes:

```
products ←→ tags     from a product:  multi-select over ~30 tags
                     from a tag:      multi-combobox over thousands of products
```

**The negative case matters as much.** `order_items` has two foreign keys *and* `quantity` and `unit_price_cents`. Those columns belong to the line item itself, so it is an entity with two references — not an edge. Collapsing it into a many-to-many would delete the two facts that make an order line an order line.

Sorted many-to-many (a join table with `sort_order`) cannot use a plain multi-select, because a multi-select has no order. It needs a two-pane picker or a reorderable chip list, and that is a real component, not a prop.

---

## 7. Money

Where generated UIs are wrong most often, and where being wrong is a 100× error that looks completely plausible.

### The storage question

| Storage | Looks like | Display | Danger |
|---|---|---|---|
| **Integer minor units** (`price_cents integer`) | `1999` | ÷ 100 → `$19.99` | Rendering raw shows `$1,999`. Nobody notices until a customer does |
| **`numeric(p,2)`** | `19.99` | direct | Safe to display. Not safe to do arithmetic on in JS — it arrives as a string from some drivers and as a float from others |
| **`float` / `double`** | `19.989999999999998` | — | A bug. Raise it before writing UI over it |
| **Postgres `money`** | `$19.99` | — | Carries no currency and rounds by a session setting. Also a bug |

**Integer minor units is the right storage and the scaffold assumes it when the name says so.** The rules that follow from it:

- Divide on read, multiply on save. Never store the divided value.
- A float must not exist in the middle. `Math.round(parseFloat(input) * 100)` is correct; accumulating `0.1 + 0.2` is not.
- `null / 100` is a type error, not zero. Nullable money needs an explicit guard, and the scaffold emits one.

### Currency display vs currency input

These are different problems and the same component cannot do both.

**Display** is `Intl.NumberFormat` with `style: 'currency'`: it places the symbol correctly for the locale, uses the right group separators, and knows that JPY has no minor unit while KWD has three. Never build the string by hand.

**Input** must not be locale-formatted while the user is typing. Reformatting on every keystroke moves the caret and people lose their place mid-number — this is the single most hated behaviour in money forms. Parse permissively (accept `1,299.00`, `1299`, `$1,299`), format on blur, and show the currency as a static adornment rather than inside the editable text.

**The currency is a column, not a constant.** `Intl.NumberFormat(locale, { currency: 'USD' })` hardcoded in a formatter is 40 files of work the day the product sells in euros. If there is a `currency` column, thread it through. If there is not, ask whether there should be.

**Minor-unit scale is not always 100.** JPY is 1, KWD and BHD are 1000. `Intl.NumberFormat().resolvedOptions().maximumFractionDigits` gives the right exponent per currency; a hardcoded `/ 100` is correct for most of the world and silently wrong for the rest. The scaffold's `formatMinorUnits(minor, currency)` divides by `minorUnitScale(currency)`, and the currency in every cell is the `.money` answer's; unanswered, the cell carries `'USD'` with a `TODO(answers)` naming the question, so the assumption is visible rather than silent.

---

## 8. Dates, times and zones

The other place generated UIs are reliably wrong, and the errors are invisible to whoever built it because they are in the server's timezone.

### The three kinds, and why conflating them breaks

| Column | Is | Render with | Break if you get it wrong |
|---|---|---|---|
| `date` | A **calendar day**. No time, no zone | Split the string, construct a *local* date | `new Date('2026-03-14')` is midnight **UTC**, which renders as 13 March for everyone west of Greenwich. A birthday shifts by a day for half your users |
| `timestamptz` | An **instant**. Stored UTC, rendered in some zone | `Intl.DateTimeFormat` with an explicit `timeZone` | Two users read two different times from one value and both think they are right |
| `timestamp` | Neither | — | Cannot answer "when" for anyone outside the server's zone. This is a schema bug; fix it in the schema |

The date-only case deserves the emphasis. `formatDate` in the generated scaffold splits `2026-03-14` into `(2026, 3, 14)` and builds a local date. That is not a shortcut around the date parser; it is the only correct handling, because the value never described an instant in the first place.

### Viewer zone vs record zone

An instant needs a zone to render, and there are exactly three defensible answers:

| Policy | Right when | Example |
|---|---|---|
| **Viewer** (`Intl` default) | The event is global and the reader's relationship to it is "when, for me" | A comment was posted. An order was placed |
| **Record** (a zone stored on the row) | The event is local to a place, and rendering it in the viewer's zone makes it wrong | A shift starts at 09:00 at the Denver site. A restaurant booking |
| **Fixed UTC** | The reader is an operator reasoning about a system | Log timestamps, audit trails |

A booking at 9am in Berlin is not a 9am event for the person in Denver reading the list — but "the shift starts at 09:00" *is* local to the site and must render as 09:00 everywhere. Only a human knows which of these a given column is, which is why `introspect_schema.py` asks per column rather than guessing globally.

**Record-zone display needs a zone column.** If the policy is "record" and there is no `timezone` column, that is a missing column, not a UI problem. Storing the zone name (`Europe/Berlin`), never the offset — offsets change twice a year.

### Display conventions

- **Relative with absolute on hover.** "3 hours ago" is what people want to read; the exact timestamp is what they need when it matters. `<time dateTime={iso} title={absolute}>` gives both and stays machine-readable.
- **Relative stops being useful past about a week.** "47 days ago" is worse than "12 March".
- **Never relative in a sortable table column.** Two rows both reading "2 days ago" cannot be ordered by eye, which defeats the sort.

---

## 9. Validation

> **Every client rule mirrors a database constraint. A client rule with no constraint behind it is a second, divergent source of truth.**

This is the rule that keeps forms honest. Invent a client rule and one of two things happens: the form rejects what the database would have accepted (a user is blocked for no reason and cannot find out why), or the form accepts what the database will reject (the save fails at submit, or worse, succeeds in one path and fails in a background job at 3am for one customer).

| Constraint | Client rule | Checked |
|---|---|---|
| `NOT NULL` with no `DEFAULT` | `required` | Locally |
| `varchar(n)` | `maxLength: n` | Locally, plus the input's own `maxlength` |
| `CHECK (col >= n)` | `min: n` | Locally |
| `CHECK (col <= n)` | `max: n` | Locally |
| `CHECK (length(col) <= n)` | `maxLength: n` | Locally |
| `CHECK (col ~ '…')` | `pattern` | Locally |
| `CHECK (col IN (…))` | the option set | By construction — the control has no other values |
| `UNIQUE` index | `unique` | **Server.** Debounce on blur, and still handle the `23505` race on submit |
| `FOREIGN KEY` | `exists` | **Server only.** A client cannot see rows RLS hides from it, so a local "does this id exist" check rejects valid input. The database checks the key *outside* RLS, so it accepts a hidden parent too: the policy's `WITH CHECK` must confirm the parent is one this user may use |
| Enum type | the option set | By construction |

`introspect_schema.py` marks each rule `mirror: true` or `mirror: false`. The `false` ones — email format, URL scheme, slug pattern, "money is non-negative" — are conveniences the database does not enforce, and each is an argument for adding the constraint. A reviewer should read that list and decide, per rule, whether to tighten the schema or accept the divergence knowingly.

**The server gets the same rules.** The form's check is a courtesy; the control runs where the browser cannot edit it. `scaffold_ui.py` writes `server/<table>.schema.ts` (zod, `.strict()`) and `server/<table>_schema.py` (pydantic 2, `extra='forbid'`) for each entity: the draft's columns only, with the same `required`, lengths, bounds, patterns and option sets the form reads, a uuid as a uuid, a `timestamptz` as a datetime with its offset, and minor units as an integer. A rule with no constraint behind it is marked `invented` in both files, so the reviewer's list above is the same list on the server. Delete the language the project does not use.

**Two constraints the client cannot mirror at all:**

- **Uniqueness has a race.** Between the blur check and the submit there is a window. Handle `23505` on submit and map it back to the field, or two users will create the same slug forty milliseconds apart and one gets a stack trace.
- **Multi-column CHECKs are form rules, not field rules.** `CHECK (ends_at > starts_at)` belongs on the form's submit path with the error placed on the *later* field. Attaching it to one column produces a message that blames the wrong input.

---

## 10. What the schema cannot tell you

The interview. `introspect_schema.py` emits every one of these as an answerable question with a defensible default pre-filled, so step 2 of the workflow is a five-minute review rather than a design exercise.

| Question | Why no schema has it | Default the script proposes |
|---|---|---|
| **Which column is the record's title?** | A schema has no concept of "the important one". This drives the list's first column, the detail `h1`, the delete confirmation, the browser tab and every toast | First match among `title`, `name`, `display_name`, `full_name`, `label`, …; else the first non-null unique text column. **If nothing matches, the primary key stands in and is flagged — a uuid in an `h1` is not a heading** |
| **What is the default order?** | `ORDER BY` is not in the DDL. A list with no designed order changes its top row whenever anyone edits anything, and people read the top row first | `sort_order asc` if one exists, else `created_at desc` |
| **What is on the list view?** | The schema knows every column and nothing about what this team scans for | Ranked by kind: title, image, references, status, money, flags, dates. Capped at six |
| **Table, card grid or feed?** | A presentation decision. An image column suggests cards, five numeric columns suggest a table, and a phone in the field overrides both | Per the rule in `screen-patterns.md` §2 |
| **How do the form's fields group?** | Grouping is the difference between a form and a questionnaire, and it is semantic | Grouped by control shape: Identity, Content, Classification, Relationships, Scheduling, Media, Advanced. Correlates with meaning only by accident |
| **Which columns are read-only in practice?** | The database permits far more than the product should: externally-synced fields, values only a job should write, columns an admin may change and a user may not | Only the ones the database itself forbids |
| **What does the empty state say?** | The most-seen screen on day one, and it is pure product knowledge | A `TODO(copy)` with the headline scaffolded and the body blank, on purpose |
| **Currency, and minor units or decimal?** | `integer` does not say "cents" | From the name suffix; `unknown` when only a money *word* matched |
| **Which jsonb keys are real?** | `jsonb` is a shrug in schema form | Empty. A JSON textarea is the honest placeholder, and it should embarrass someone into answering |
| **Which storage bucket, public or signed?** | Not in the schema at all. A public bucket renders a URL; a private one mints a signed URL with an expiry that can go stale while the page is open | The table name, private |
| **Viewer zone or record zone?** | §8 | Viewer |
| **How many rows will this parent hold?** | The only input that decides select vs combobox vs picker | Inferred from the parent's shape, at `medium` confidence at best |
| **Which parent column labels a reference?** | Usually the title. Not always | The parent's own title answer |
| **Is RLS on?** | Sets what the generated forbidden state's notes say; the state is generated either way — see `supabase-integration.md` §2 | What the DDL states per table; "yes" from a source that cannot say |

The honest summary: **the schema gets you to a defensible default for every column, and to the right answer for about three quarters of them.** The remaining quarter is where the product actually lives, and no amount of cleverness in the mapper will find it. What the mapper can do — and does — is make that quarter visible, small, and answerable in one sitting.

---

Related: `screen-patterns.md` (what the mapped fields get assembled into), `supabase-integration.md` (what each schema source carries, and RLS), `token-contract.md` (the vocabulary every generated component speaks).
