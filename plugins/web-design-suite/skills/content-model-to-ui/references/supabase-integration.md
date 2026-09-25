# Supabase Integration

The stack-specific half: where the schema comes from, what RLS does to a UI, and the four data-layer decisions that change what the components have to render.

Everything here assumes FastAPI + Supabase + React 19/Vite. The mapping rules in `field-mapping.md` are stack-agnostic; this file is not.

## Contents

1. [Getting the schema out](#1-getting-the-schema-out)
2. [RLS is a UI concern](#2-rls-is-a-ui-concern)
3. [Generated types](#3-generated-types)
4. [Realtime](#4-realtime)
5. [Pagination](#5-pagination)
6. [Optimistic updates](#6-optimistic-updates)
7. [Storage-backed fields](#7-storage-backed-fields)
8. [Search](#8-search)

---

## 1. Getting the schema out

Three sources, three fidelities. `introspect_schema.py` reads all three and records what each one could not carry, so nobody mistakes an absent constraint for a permissive one.

| Fact | DDL (`.sql`) | `gen types` (`.ts`) | `information_schema` (`.json`) |
|---|---|---|---|
| Tables, columns | yes | yes | yes |
| Nullability | yes | yes (`\| null`) | yes |
| Exact Postgres type | yes | **no** — `uuid`, `text`, `citext`, `date` and `timestamptz` all read as `string` | yes |
| Length constraints | yes | **no** | yes |
| CHECK constraints | yes | **no** | with a join to `check_constraints` |
| Defaults | yes | only "has one", via optionality in `Insert` | yes |
| Generated / identity | yes | no | yes |
| Primary keys | yes | inferred | with a join to `key_column_usage` |
| Foreign keys | yes | yes, in `Relationships` | with a join |
| `ON DELETE` | yes | **no** | with a join to `referential_constraints` |
| Unique indexes | yes | only 1:1 FKs (`isOneToOne`) | with a join |
| Enums | yes | yes | with a join to `pg_enum` |
| Column comments | yes | no | yes |
| Row counts | **no** | **no** | **no** |
| RLS policies | if the dump includes them | no | separate (`pg_policies`) |

**Prefer the DDL.** Measured on the fixture in this skill's verification: the DDL and a full `information_schema` dump produce byte-identical models. The generated-types source produces an identical *structural* model — same tables, columns, nullability, foreign keys, enums, join-table detection, many-to-many edges, controls and list placement — but loses **14 validation rules across 13 columns** (every `maxLength`, every `unique`, every CHECK-derived `min`/`max`), loses ownership (no `ON DELETE`, so every one-to-many degrades from `inline-subtable` to `linked-list`), and cannot see that a `timestamp` column is missing its time zone.

That last one is worth stating plainly: **the generated-types file loses exactly the information the mapper wants most.** It is the easiest source to obtain and the weakest one. Use it when the DDL is genuinely unavailable, and expect a longer questions list.

```bash
# Best: the migration files you already have
cat supabase/migrations/*.sql > /tmp/schema.sql
python -m scripts.introspect_schema /tmp/schema.sql -o model.json --summary

# Or a live dump, structure only
pg_dump --schema-only --no-owner --no-privileges -n public "$DATABASE_URL" > /tmp/schema.sql

# Weakest, but always available
supabase gen types typescript --project-id "$PROJECT_ID" > database.types.ts
python -m scripts.introspect_schema database.types.ts -o model.json
```

If you are building the JSON dump yourself, join the constraint tables. A dump of `information_schema.columns` alone is the generated-types source with extra steps.

---

## 2. RLS is a UI concern

The single most important thing in this file.

> **Under row-level security, a row the user may not see and a row that does not exist produce the same response: an empty result and no error.**

PostgREST does not distinguish them, and it is right not to — telling a client "this row exists but you cannot have it" is an information leak. But it means a UI that checks `rows.length === 0` and renders "No records yet" will, for a user whose policy filters everything out, **tell them their data is gone.**

This is not a rare edge. It is what every new user in a multi-tenant product sees if their tenant assignment has not landed, what every user sees when a role changes mid-session, and what a support engineer sees when they impersonate.

### What the UI must do

**Model the list's state as a union, not as booleans.** The scaffold generates exactly this:

```ts
export type ProductListState =
  | { status: 'loading' }
  | { status: 'error'; error: Error; retry: () => void }
  | { status: 'forbidden' }
  | { status: 'ready'; rows: Product[]; filtered: boolean; stale?: boolean };
```

`forbidden` is an arm, not a flag, so it cannot be confused with an empty `ready`.

**Decide `forbidden` from something other than the row count**, because the row count cannot tell you. In order of preference:

1. **A capability the session already knows.** The JWT's claims, or a `/me` endpoint that returns what this user can do. Reading permission from the session is the only approach that works before the first query.
2. **An explicit RPC.** `create function can_read_products() returns boolean security definer` — one round trip, unambiguous, and the function decides what to reveal.
3. **A count against a table the user can always read.** "The tenant has 40 products, this query returned 0" distinguishes the cases. Only viable when such a table exists.

What does **not** work: inspecting the error. A successful query returning zero rows is a success.

**Never surface the policy.** "You cannot see rows where `tenant_id != your_tenant`" tells an attacker your data model. "You do not have access to products. Ask an administrator if you think this is a mistake." tells the user what to do and reveals nothing — including whether any records exist at all.

### Writes fail differently

A blocked read is silent; a blocked write is loud, and its error code is not obvious:

| Code | Means | Show |
|---|---|---|
| `42501` | Insufficient privilege — a policy rejected the write | "You do not have permission to change this." |
| `23505` | Unique violation | The field-level message from the unique index |
| `23503` | Foreign key violation — often a parent the user cannot see | "That selection is no longer available." |
| `PGRST116` | Zero rows from a `.single()` | Not found **or** not permitted. Do not say "deleted" |

`PGRST116` is the one that bites. `.single()` on a row the policy hides returns the same error as `.single()` on a row that was deleted, and a detail page that renders "This record was deleted" for a permissions problem sends the user to the wrong support queue.

### The generated code must never assume the table is fully visible

Three concrete consequences:

- **A foreign-key picker shows only permitted parents.** If a user can see an order but not its customer, the customer combobox is empty and the form looks broken. Either the policy should permit reading the label, or the picker needs to say "you cannot change this".
- **A client-side "does this id exist" check rejects valid input.** The id may be perfectly valid and simply invisible. Existence is a server check, always.
- **A client-side count is a count of what you can see.** Never present it as a total. `{ count: 'exact' }` on a PostgREST query is also policy-filtered, which is correct and is not the number a dashboard usually wants.

---

## 3. Generated types

```bash
supabase gen types typescript --project-id "$PROJECT_ID" --schema public > src/database.types.ts
```

Regenerate in CI on every migration and fail the build on a diff. A types file that drifts from the schema is worse than no types file: it is confidently wrong, and TypeScript will defend the wrong shape.

```ts
import type { Database } from './database.types';

type Tables<T extends keyof Database['public']['Tables']> =
  Database['public']['Tables'][T]['Row'];
type Enums<T extends keyof Database['public']['Enums']> =
  Database['public']['Enums'][T];

export type Product = Tables<'products'>;
export type ProductStatus = Enums<'product_status'>;
```

The scaffold emits its own hand-shaped interfaces rather than importing these, for one reason: **the write type is not the read type.** The generated `Row` includes `id`, `created_at` and every column a database default fills in. A form typed as `Row` invites a `PATCH` that sets `created_at`, and the scaffold's `ProductDraft` is a `Pick` of the writable columns precisely so that cannot compile.

Once the scaffold is yours, wire the two together: keep `Draft` hand-shaped, and derive the read type from the generated `Row` so a migration that drops a column breaks the build.

**Three known rough edges:**

- `jsonb` becomes `Json`, which is a union you cannot index. Cast it at the boundary, with a runtime check — the generated type is a promise the database does not keep.
- Views are typed with every column nullable, because Postgres cannot prove otherwise. Use a table type when you know better.
- Enum values come through as a string union, which is exactly right and is the one place the generated types beat hand-written ones.

---

## 4. Realtime

```ts
supabase.channel('products')
  .on('postgres_changes', { event: '*', schema: 'public', table: 'products' }, handle)
  .subscribe();
```

Realtime is a list-state problem before it is a transport problem.

**Realtime respects RLS, and that is a trap on `DELETE`.** `INSERT` and `UPDATE` payloads are policy-filtered, so you only receive rows you can see. But the `DELETE` payload contains only the primary key unless the table's replica identity is `FULL` — so you cannot evaluate a policy against it, and you cannot tell whether the deleted row was one of yours. `ALTER TABLE products REPLICA IDENTITY FULL` gives you the old row, at the cost of a larger WAL.

**An arriving row that fails the current filter must not be inserted.** The subscription is on the table; the list is a filtered, sorted, paginated view of it. Re-apply the filter and the sort client-side, or the user's carefully filtered list starts growing rows that do not match.

**Do not reorder or remove rows under a reading user.** A row that vanishes mid-read — or worse, mid-click — is the most disorienting thing realtime can do. Mark the list stale, render the banner above it, and let the user pull the change in:

```
┌──────────────────────────────────────────┐
│ This list has changed.        [Refresh]  │   ← the `stale` state
├──────────────────────────────────────────┤
│ …the rows the user was already reading…  │
```

**Exceptions where live insertion is right:** a chat log, an activity feed, a monitoring view. The distinguishing property is that the user is watching *for* change rather than working *on* a record.

**Reconnection needs a refetch.** Events during a disconnect are gone. On `SUBSCRIBED` after a drop, refetch rather than assuming continuity — otherwise the list silently diverges and never recovers.

---

## 5. Pagination

| Method | Query | Use for |
|---|---|---|
| **Offset** | `.range(40, 59)` | Numbered pages over data that does not change under the user |
| **Keyset** | `.gt('created_at', cursor).limit(20)` | Everything else |

**Keyset is right for anything that changes under the user**, and the reason is not performance. With offset pagination, if a row is inserted above the user's window between page 1 and page 2, every subsequent row shifts down by one — so the last row of page 1 becomes the first row of page 2, the user sees it twice, and a different row is skipped entirely and never seen at all. On an infinite-scroll list this produces duplicate keys in React and a warning nobody can explain.

Keyset asks "give me the rows after *this one*", which is stable regardless of what was inserted above it.

```ts
// The sort column must be part of the cursor, and the cursor must be unique.
let q = supabase.from('products')
  .select('*')
  .order('created_at', { ascending: false })
  .order('id', { ascending: false })   // tiebreak — see below
  .limit(20);

if (cursor) {
  q = q.or(
    `created_at.lt.${cursor.created_at},` +
    `and(created_at.eq.${cursor.created_at},id.lt.${cursor.id})`
  );
}
```

**The tiebreak is not optional.** Two rows with the same `created_at` — which happens constantly with `default now()` in a batch insert — make the cursor ambiguous, and rows at the boundary are skipped or repeated. Always add the primary key as the final sort key. This is also why the `default_sort` answer in the model carries a `tiebreak` field.

**Offset's other cost:** `count: 'exact'` scans the table. On anything large use `count: 'estimated'` (from `reltuples`), or `'planned'`, and render "about 40,000" rather than a precise number you paid for and then rounded in the UI anyway.

**Keyset cannot jump to page 7.** That is a real limitation and the right trade for a list that changes. If numbered pages are a hard requirement, the data is probably a report, and a report can be offset-paginated over a stable snapshot.

---

## 6. Optimistic updates

Worth it when the write is small, the failure is rare, and the latency is visible: toggles, inline edits, status changes, reordering. Not worth it for a create with server-generated fields the UI cannot predict.

The sequence, all five steps:

1. **Cancel in-flight refetches** for this key, or one lands after your optimistic write and clobbers it.
2. **Snapshot** the previous value.
3. **Apply** the change, marked pending (`data-state="loading"` on the row, not a disabled row — disabled removes it from the tab order).
4. **On error, restore the snapshot** *and tell the user*, with their input still recoverable. A silent rollback is worse than no optimism: the user believes the change was saved and finds out later.
5. **Settle**: invalidate and refetch, so the server's version — including anything it computed — becomes the truth.

```ts
useMutation({
  mutationFn: (next) =>
    supabase.from('products').update(next).eq('id', next.id).select().single(),
  onMutate: async (next) => {
    await qc.cancelQueries({ queryKey: ['products'] });
    const previous = qc.getQueryData(['products']);
    qc.setQueryData(['products'], (rows) =>
      rows.map((r) => (r.id === next.id ? { ...r, ...next, _pending: true } : r)));
    return { previous };
  },
  onError: (_e, _next, ctx) => {
    qc.setQueryData(['products'], ctx.previous);
    toast.error('That change did not save. Try again.');   // never silent
  },
  onSettled: () => qc.invalidateQueries({ queryKey: ['products'] }),
});
```

**Under RLS, a rejected write returns `42501`, not a network error.** Handle it as "you do not have permission" rather than "something went wrong" — the retry the generic message invites will fail identically, forever.

**`.select()` after the write is not optional** if the row has triggers, generated columns or an `updated_at`. Without it you keep your optimistic guess instead of the row the database actually holds.

---

## 7. Storage-backed fields

A column named `avatar_url`, `cover_image` or `attachment` is a pointer into Storage, not a string a user types. Which component it needs depends on one answer the schema does not carry: **is the bucket public?**

| Bucket | Read | Component implication |
|---|---|---|
| **Public** | A stable URL | `<img src={row.avatar_url}>`. Cache normally |
| **Private** | `createSignedUrl(path, ttl)` | The URL **expires**, possibly while the page is open. The component must be able to re-mint it |

The private case is the one that surprises people. A signed URL minted at page load with a 60-second TTL is dead before a user finishes reading a long list, and the images turn into broken-image icons with no error anywhere. Either mint with a TTL longer than any plausible session, or re-mint on `error` — and make the second one the default, because "longer than any plausible session" is a guess.

**Store the path, not the URL.** A row holding `https://xyz.supabase.co/storage/v1/object/public/avatars/u/1.png` breaks when the project moves, when the bucket flips to private, and when a CDN goes in front. Store `avatars/u/1.png` and build the URL at render.

**Uploads need their own state machine**, and it is not the form's:

```
idle → selected (local preview, revoke the object URL on unmount)
     → uploading (real progress, cancellable)
     → uploaded  (the path, not the URL)
     → error     (with the file still selected, so retry costs nothing)
```

**Validate before uploading, not after.** Size and type, client-side, so a user on a phone does not spend 40 seconds of their data allowance discovering the file was too big. Then validate again server-side, because the client check is a courtesy and not a control.

**RLS applies to Storage too**, via policies on `storage.objects`. A working upload and a broken read is a missing `SELECT` policy, and it is the commonest Storage bug.

---

## 8. Search

| Method | Query | Good for | Cost |
|---|---|---|---|
| `ilike` | `.ilike('title', '%' + q + '%')` | One column, small tables, substring matching | Leading `%` cannot use a b-tree index. Fine at thousands, a sequential scan at millions |
| `ilike` + `pg_trgm` | same, with a GIN trigram index | Fuzzy and typo-tolerant substring search | Index size; still one column at a time |
| `tsvector` | `.textSearch('fts', q, { type: 'websearch' })` | Several columns, stemming, ranking, real scale | A generated column plus a GIN index, and it stops being substring search |

**The UI consequences differ, and they are what the user notices:**

| | `ilike` | `tsvector` |
|---|---|---|
| "prod" finds "product" | yes (substring) | **no** — stemming matches words, not prefixes |
| "running" finds "run" | no | yes |
| Results are ranked | no — arbitrary order | yes, `ts_rank` |
| Highlighting | client-side, exact | `ts_headline`, server-side |
| Typos | only with `pg_trgm` | no |

The prefix row is the one that generates support tickets. Users type three letters and expect results; full-text search gives them nothing until they finish a word. If the search box is a type-ahead, either add `:*` to the query terms for prefix matching, or use trigram, or accept that the box only works on whole words and say so in the placeholder.

```sql
alter table products add column fts tsvector
  generated always as (
    to_tsvector('english', coalesce(title,'') || ' ' || coalesce(description,''))
  ) stored;
create index products_fts_idx on products using gin (fts);
```

A generated column keeps the index in step with the data with no trigger to forget. `introspect_schema.py` maps `tsvector` to `hidden` — it powers the search box and is never a field.

**Search must respect RLS** and, with PostgREST, it does automatically. The consequence is that a search returning nothing can mean "no matches" or "no permitted matches", which is §2 again: the filtered-empty state and the forbidden state are different screens.

---

Related: `field-mapping.md` (types and controls), `screen-patterns.md` §12 (the states RLS and realtime make reachable), `token-contract.md`.
