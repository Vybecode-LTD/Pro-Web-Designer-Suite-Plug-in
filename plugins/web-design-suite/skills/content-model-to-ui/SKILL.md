---
name: content-model-to-ui
description: Turn a database schema into an on-system UI spec and a React scaffold, with CRUD screens, schema-derived forms, list and detail pages and admin panels. Use for Supabase or Postgres tables that need screens. Not for designing the content model itself, for charts and dashboards, or for marketing pages.
---

# Content Model to UI

> **Running the scripts** — by path, from the user's project root, so `src/`
> means the project's `src/` and every output lands in the project, never
> inside this plugin:
>
> ```bash
> python "${CLAUDE_SKILL_DIR}/scripts/introspect_schema.py" supabase/migrations/*.sql -o model.json --summary
> ```
>
> The commands below are written `python -m scripts.<name>`. That form is for a project that
> has copied the scripts into its own `scripts/` folder, as CI and git hooks
> do; when you run one here, use the path form.
> This skill's scripts are in `${CLAUDE_SKILL_DIR}/scripts/` (introspect_schema.py, scaffold_ui.py).
> From sibling skills: `${CLAUDE_PLUGIN_ROOT}/skills/web-design-studio/scripts/audit_design.py`.

A Postgres schema exists. Somebody now has to turn it into screens.

Done by hand that is a week of tedium and a guaranteed source of inconsistency: the third CRUD form is never shaped like the first, and by the eighth nobody can say which one is the house style. Done badly by a generator it produces the admin-panel look — every column a labelled text input, every list a grey table, every empty state the words "No data" — which no client accepts and which is faster to rebuild than to fix.

This skill closes the loop: **a schema in, an on-system UI spec and component scaffold out.** Composed from the suite's layout primitives, styled with role tokens in the five-part component shape, with all seven interactive states and with the empty, loading and error states *designed* rather than defaulted.

It produces a starting point a designer would not be embarrassed by. It does not produce a finished product, and §Scope says exactly where the line is.

---

## The mapping principle

> **A column type does not determine a control. The semantics do.**

`text` could be a single-line input, a textarea, a rich editor, a slug field, a read-only display, or nothing on any screen at all. The type is identical in all six cases. What separates them:

| Signal | Example | Decides |
|---|---|---|
| The column's **name** | `price_cents` vs `stock_count` | Money, not a quantity — and the label is "Price", not "Price Cents" |
| A **length constraint** | `varchar(140)` vs `text` | One line vs a paragraph, plus the input's own `maxLength` |
| Whether it is **editable** | `generated always as identity` | Whether the column is a field at all |
| **Distinct-value cardinality** | 5 vs 5,000 vs 5,000,000 | Radio group vs select vs combobox vs a picker with its own search |
| A **foreign key** | `category_id` | That the control is a function of the *parent's* size, not this column's type |
| An **enum or CHECK** | `status` | That the set is closed, and exactly what is in it |
| A **unique index** | `slug` | That validation needs a server round trip, and a `23505` race handled on submit |
| What the user is **doing** | reading a list vs filling a form | Read-only display vs an editable control |

Get that layer right and roughly three quarters of the columns map correctly on the first pass. The remaining quarter is where the product actually lives, and no amount of cleverness finds it — so the job of the mapper is to make that quarter **visible, small and answerable in one sitting**. That is what the `questions` block in `model.json` is for, and it is the reason step 2 of the workflow exists.

The full decision procedure, every signal, and the list of what only a human can answer: `references/field-mapping.md`.

---

## Workflow

### 1. Ingest the schema

```bash
python -m scripts.introspect_schema supabase/migrations/*.sql -o model.json --summary
```

Reads a `.sql` DDL file, a `supabase gen types typescript` `.ts` file, or a JSON schema dump, and normalises all three to one `model.json`: tables, columns with type/nullability/default/constraints/comment, primary and foreign keys, unique indexes, enums, and inferred relationships — including the join-table detection that turns two foreign keys in a table with no other meaningful column into a many-to-many edge rather than an entity with two screens nobody wants.

**Prefer the DDL.** All three sources produce the same structural model, but generated types carry no lengths, no CHECKs, no `ON DELETE` and no unique indexes — which is exactly the information the mapper wants most. `references/supabase-integration.md` §1 has the fidelity table and the measured difference.

`--summary` prints the proposal: every column, its control, the signal that chose it, and a confidence level. Read it. It is faster than reading the JSON and it is where you will spot the one column the machine got backwards.

### 2. Enrich it — the human step

This is the step that decides whether the output is worth keeping, and it is a **structured interview, not a blank page**. The script emits every question a schema cannot answer, phrased so it can be answered, with a defensible default already filled in:

```bash
python -m scripts.introspect_schema schema.sql --questions          # read them
python -m scripts.introspect_schema schema.sql --answers-template answers.json
```

`answers.json` arrives pre-filled with every default. Editing it is a five-minute review. What it asks, per entity:

- **Which column is the record's title?** Everything hangs off this — the list's first column, the detail `h1`, the delete confirmation, the browser tab, every toast. If nothing in the table looks like a title, the primary key stands in and is flagged loudly, because a uuid in an `h1` is not a heading.
- **What is the default order?** A list with no designed order changes its top row whenever anyone edits anything, and people read the top row first.
- **What is on the list view, versus only on the detail view?** Six columns is the working cap; past that people stop scanning and start reading.
- **Table, card grid or feed?**
- **How do the form's fields group?** Grouping is the difference between a form and a questionnaire.
- **Which columns are read-only in practice?** The database permits far more than the product should.
- **What does the empty state say, and what is the one action it offers?**

Plus, per column where it applies: the currency and whether the stored value is minor units; whether a `timestamptz` renders in the viewer's zone or the record's; which jsonb keys are real; which Storage bucket and whether it is public; how many rows a referenced parent will hold; which parent column labels a picker.

Skip this step and the scaffold still runs — every answer falls back to the machine's own proposal. It will be defensible and it will be wrong in about a quarter of places, and you will find them one at a time in review instead of all at once in a text editor.

### 3. Derive the screen set

Falls out of the model plus the answers, and is recorded in `model.json` under each table's `screens`. One entity implies an index, a detail, a create/edit form, a delete confirmation, and — once the list exceeds a screen — filter, search and pagination. Join tables get no screens; they are edges, and they appear as a control on both sides. Owned children (`ON DELETE CASCADE`, no title of their own) live inside the parent's form rather than getting their own CRUD.

Anatomy, primitive composition, spacing in real tokens, and the responsive behaviour of each: `references/screen-patterns.md`.

### 4. Generate

```bash
python -m scripts.scaffold_ui model.json --out src --answers answers.json --dry-run
python -m scripts.scaffold_ui model.json --out src --answers answers.json
```

One folder per entity: a list view, a detail view, a form, and the empty / filtered-empty / loading / error / forbidden / stale states as real components. A shared `ui/` kit underneath — Button, Field, the control primitives, Badge, Skeleton, StateBlock — each in the five-part component shape with Tier-3 sockets defaulting to Tier-2 roles.

React 19 conventions throughout: `ref` is an ordinary prop, no `forwardRef`. Components take their rows as props and know nothing about fetching, because cache keys, realtime and optimistic writes are product decisions and a scaffold has no business guessing at them.

**Nothing it writes carries an `@generated` marker, deliberately.** `audit_design.py` skips generated files, and output that skips the gate proves nothing. Treat the scaffold as code you now own.

### 5. Design the states the generator stubbed

Every `TODO(...)` is a decision the scaffold refused to make up. Fixing them is the work, and there are two kinds:

**`TODO(copy)`** — a sentence only somebody who knows the product can write. First-run empty is the most-seen screen in the app on day one, and it is the one generators always default. "No data" is the absence of copy, not copy.

**`TODO(<control>)`** — a control the scaffold would not guess at: a combobox, a record picker, an inline sub-table, an image upload. Each renders as an obviously unfinished placeholder rather than a plausible wrong control, because a stub that looks finished is how a placeholder ships.

The eight states that decide whether a product feels finished — first-run empty, filtered empty, loading, partial, error, permission-denied, stale, optimistic-with-rollback — are in `references/screen-patterns.md` §12, with what each must and must not do. Two of them are worth naming here:

- **First-run empty and filtered empty are different screens**, not one screen with different words. "Nothing here yet, make the first one" and "your filter matched nothing, clear it" ask the user to do opposite things.
- **A row the user cannot see and a row that does not exist look identical to the client.** Under RLS that is not an edge case; it is what every mis-provisioned user sees. If the UI does not distinguish "empty" from "forbidden" deliberately, it will tell somebody their data is gone. `references/supabase-integration.md` §2.

### 6. Audit

```bash
python -m scripts.audit_design src/ --strict      # from web-design-studio
```

Law 9. The scaffold is built to exit clean on a fresh run and does; anything the audit finds after step 5 is something the edit introduced.

Then prove the result, not just the code: `component-state-matrix` renders every state × density × theme, which is the only way to see a state that was never written — an unwritten state produces no violation for a linter to object to.

---

## The model

`model.json` is the contract between the two scripts and the thing a human reviews. Its shape, abbreviated:

```jsonc
{
  "$schema": "content-model-to-ui/model/1",
  "source":   { "path": "schema.sql", "format": "ddl", "pg_schema": "public" },
  "fidelity": { "source_format": "ddl",
                "carries": ["lengths", "checks", "unique indexes", "…"],
                "missing": ["row counts / cardinality", "RLS policies", "…"] },
  "enums":    { "order_status": ["pending", "paid", "shipped", "cancelled"] },

  "tables": [{
    "name": "products",
    "kind": "entity",                  // entity | join
    "primary_key": ["id"],
    "unique_indexes": [["slug"]],

    "columns": [{
      "name": "price_cents",
      "type": "integer",               // normalised; `raw_type` keeps the source spelling
      "nullable": false,
      "default": "0",
      "generated": false,
      "checks": ["price_cents >= 0"],
      "foreign_key": null,
      "ui": {
        "control":    "currency-input",
        "label":      "Price",         // NOT "Price Cents"
        "confidence": "high",
        "signal":     "name declares minor units — the integer is NOT a quantity",
        "editable":   true,
        "money":      { "storage": "minor-units", "scale": 100, "currency": "unknown" },
        "validation": [
          { "rule": "required", "value": true,
            "source": "NOT NULL with no DEFAULT", "mirror": true, "message": "…" },
          { "rule": "min", "value": 0,
            "source": "CHECK (price_cents >= 0)", "mirror": true, "message": "…" }
        ],
        "placement":  { "list": true, "detail": true, "form": true }
      }
    }],

    "relationships": [
      { "kind": "many-to-one",  "to": "categories", "local_column": "category_id",
        "optional": true, "control": "select",  "confidence": "medium", "signal": "…" },
      { "kind": "many-to-many", "to": "tags", "via": "product_tags",
        "control": "multi-select", "confidence": "medium", "signal": "…" }
    ],

    "screens": {
      "title_column": "title", "title_is_placeholder": false,
      "index_layout": "table", "index_layout_signal": "…",
      "default_sort": { "column": "created_at", "direction": "desc",
                        "tiebreak": "id", "signal": "…" }
    }
  }],

  "questions": [{
    "id":       "products.title_column",
    "kind":     "choice",
    "table":    "products",
    "question": "Which column is a product's title …?",
    "options":  ["slug", "title", "description", "currency"],
    "default":  "title",
    "why":      "Everything downstream hangs off this: …"
  }],

  "stats": { "tables": 6, "join_tables": 1, "columns": 51, "questions": 64,
             "confidence": { "high": 38, "medium": 11, "low": 2 } }
}
```

Three things to notice, because they are the parts that make it reviewable rather than merely machine-readable:

- **Every `ui` block carries its `signal`.** A reviewer can audit the machine's reasoning instead of trusting its output, and disagree with a specific sentence rather than with a black box.
- **Every validation rule names the constraint it mirrors**, and `mirror: false` marks the ones invented for convenience. Those are the rules to either drop or promote into the schema — a client rule with no constraint behind it is a second source of truth, and the two will disagree.
- **`questions` is the deliverable of step 1**, not a footnote. Its length is the honest measure of how much the schema left unsaid.

The answers file is a flat `{ "<question id>": <value> }` map. `--answers-template` writes it pre-filled.

---

## Worked example

One schema taken from introspection to generated screens: `references/worked-example.md`.

---

## Scope — what the generator does and does not decide

Stated plainly, because a generator that overstates its reach is worse than one that does less.

**It decides**, and will usually be right:

- Which control each column gets, with the signal and a confidence level attached to every choice
- Labels, with the storage details stripped out (`price_cents` → "Price", `category_id` → "Category")
- Validation rules derived from database constraints, each tagged with the constraint it mirrors
- Which columns belong on a list versus a detail versus a form
- Which tables are entities, which are join-table edges, and which are owned children
- Layout composition, spacing, states and token usage — the parts that make it *on-system*

**It proposes, and expects to be corrected:**

- The title column, the default order, the list columns, the field groups, the index layout
- The control for every reference, because the deciding input is the parent's row count and no schema carries it

**It does not decide, and does not pretend to:**

- Any copy at all. Every string that a user reads and that is not a column label is a `TODO(copy)`
- Information architecture — which screens a person needs to get their job done, and in what order
- Navigation, permissions, roles, or who can do what
- The data layer: fetching, caching, realtime, optimistic writes, error taxonomy
- Whether the schema is any good. A float money column, a naive `timestamp`, a `status text` with no constraint — it flags all three and fixes none of them, because they are schema bugs and fixing them in the UI is how they become permanent

The honest summary: **this gets you to the end of the tedium, not to the end of the work.** What it buys is that the eighth CRUD screen is shaped like the first, every state exists before anyone asks for it, and the design decisions left over are a list you can read in one sitting rather than a backlog you discover in review.

---

## Scripts

Both are stdlib-only Python 3. Run them by path from the project root (see *Running the scripts* at the top).

Every argument of `introspect_schema.py` and `scaffold_ui.py` is in `references/scripts.md`.

---

## Routing

| Situation | Go to |
|---|---|
| Building or restyling the system itself | `web-design-studio` |
| An inherited codebase not yet on tokens | `design-token-migration` |
| Design file and code have drifted apart | `figma-variables-sync` |
| **A schema exists and the screens do not** | **here** |
| Proving every state × density × theme renders | `component-state-matrix` |
| Copy, offer and persuasion on a landing page | `landing-page-conversion` |
| Adversarial review before a client sees it | `design-critique-gate` |

Within this skill:

| You want | Read |
|---|---|
| the token vocabulary | `references/token-contract.md` |
| why a column became that control | `references/field-mapping.md` |
| money, or dates and timezones | `references/field-mapping.md` §7, §8 |
| relationship controls and the cardinality ladder | `references/field-mapping.md` §6 |
| what a schema can never tell you | `references/field-mapping.md` §10 |
| how each screen is composed from primitives | `references/screen-patterns.md` |
| the wide-table-on-a-phone problem | `references/screen-patterns.md` §4 |
| the states that decide whether it feels finished | `references/screen-patterns.md` §12 |
| form UX — order, timing, guarding, autosave | `references/screen-patterns.md` §13 |
| RLS as a UI concern | `references/supabase-integration.md` §2 |
| pagination, realtime, optimistic writes, search | `references/supabase-integration.md` §4–§8 |

---

## The three sentences to remember

1. **A column type does not determine a control — the semantics do**, and the mapper's real job is not to be right about all of them but to make the ones it cannot know *visible, small and answerable in one sitting*.
2. **The states nobody generates are the ones that decide whether it feels finished** — first-run empty, filtered empty, permission-denied and optimistic rollback are four different screens, and defaulting them is what makes a product read as a demo.
3. **The output is a starting point, not a product**, and every `TODO` in it is a decision a human still owes the scaffold — which is why the scaffold refuses to guess rather than shipping a plausible wrong answer.
