# Supabase Integration

The stack-specific half: where the schema comes from, what RLS does to a UI, and the four data-layer decisions that change what the components have to render.

Everything here assumes FastAPI + Supabase + React 19/Vite. The mapping rules in `field-mapping.md` are stack-agnostic; this file is not.

**Read §9 before wiring anything.** It says which key each process holds, and every guarantee in §2 depends on it.

## Contents

1. [Getting the schema out](#1-getting-the-schema-out)
2. [RLS is a UI concern](#2-rls-is-a-ui-concern)
3. [Generated types](#3-generated-types)
4. [Realtime](#4-realtime)
5. [Pagination](#5-pagination)
6. [Optimistic updates](#6-optimistic-updates)
7. [Storage-backed fields](#7-storage-backed-fields)
8. [Search](#8-search)
9. [Who talks to the database](#9-who-talks-to-the-database)

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

1. **A capability the session already knows.** A `/me` endpoint that returns what this user can do, or a claim in the JWT's `app_metadata`. Reading permission from the session is the only approach that works before the first query. Two limits on the claim:
   - **Never `user_metadata`.** The signed-in user can write it through the auth API; `app_metadata` they cannot, which is why Supabase names it as the place for authorization data.
   - **A claim is as old as the token.** A change to `app_metadata` reaches `auth.jwt()` only when the token is refreshed. Where a stale answer matters, ask `/me`.
2. **An explicit RPC.** `select can_read_products()` — one round trip, unambiguous, and the function decides what to reveal. Write it as an ordinary function (security invoker, the default) that reads only what the user may already read, such as their own membership row. If it must read more than that, see the template below.
3. **A count against a table the user can always read.** "The tenant has 40 products, this query returned 0" distinguishes the cases. Only viable when such a table exists.

**A `security definer` function runs with its owner's rights, so it is a hole in RLS by design.** Three rules, all Supabase's own (its RLS guide): keep it out of every schema the API exposes, set `search_path = ''` and schema-qualify every name inside it, and take `execute` away from `public`:

```sql
create schema if not exists private;

create function private.readable_org_ids() returns setof uuid
  language sql security definer set search_path = '' stable
as $$
  select org_id from public.memberships where user_id = (select auth.uid())
$$;

revoke execute on function private.readable_org_ids() from public;
grant usage on schema private to authenticated;
grant execute on function private.readable_org_ids() to authenticated;
```

A policy, or an invoker function in `public`, may then call `private.readable_org_ids()`. The client cannot reach it directly, because `private` is not exposed.

What does **not** work: inspecting the error. A successful query returning zero rows is a success.

**Never surface the policy.** "You cannot see rows where `tenant_id != your_tenant`" tells an attacker your data model. "You do not have access to products. Ask an administrator if you think this is a mistake." tells the user what to do and reveals nothing — including whether any records exist at all.

### Writes fail differently — and often silently

A blocked read is silent. So is half of a blocked write:

- **An `INSERT` a policy rejects raises `42501`**, and so does an `UPDATE` whose new row fails the policy's `WITH CHECK`.
- **An `UPDATE` or `DELETE` on a row the policy's `USING` hides changes 0 rows and reports success.** Postgres's own docs show it: `UPDATE 0`. A successful response does not mean the write happened. Always `.select()` the written rows and treat an empty result as "not permitted, or gone".
- **Foreign-key and unique checks run outside row security** ("referential integrity checks … always bypass row security", postgresql.org/docs/current/ddl-rowsecurity.html). A parent the user cannot see does **not** raise `23503`: the insert succeeds, which is how a user attaches a row to another tenant's record. The policy's `WITH CHECK` must confirm the parent is one this user may use (`exists (select 1 from projects p where p.id = project_id and p.org_id = (select org_id from profiles where id = auth.uid()))`). And because these checks see hidden rows, a `23505` or `23503` can reveal that a hidden row exists — word the messages so they do not.

| Signal | Means | Show |
|---|---|---|
| `42501` | A policy rejected an insert, or an update's new row failed `WITH CHECK` | "You do not have permission to change this." |
| 0 rows from `.update()` / `.delete()` + `.select()` | The policy hid the row, or it no longer exists — Postgres said "success" | "You do not have permission to change this, or it no longer exists." |
| `23505` | Unique violation — checked against rows the user cannot see | The field-level message from the unique index, without echoing the other row |
| `23503` | Foreign key violation: the parent does not exist at all. A parent that exists but is hidden does **not** raise this | "That selection is no longer available." |
| `PGRST116` | Zero rows from a `.single()` | Not found **or** not permitted. Do not say "deleted" |

### Columns row-level security cannot protect

Row-level security decides *which rows*; it has no opinion about *which columns*. Two kinds of column need column-level privileges as well:

- **Secrets** — `*_token`, `*_secret`, `*_hash`, `api_key`, anything the browser must never receive. The generator leaves them out of every screen and type, but that is only the UI: a `select('*')` still sends them. Take them away from the API roles entirely — `revoke select (api_token, reset_token) on profiles from anon, authenticated;` — or keep them in a schema that is not exposed. A `password` column in an exposed schema is a schema bug: Supabase Auth owns passwords.
- **Authority** — `role`, `is_admin`, `owner_id`, `org_id`, `plan`, `credits`: columns that decide who may do what. The standard profile policy `using (id = auth.uid())` with no `WITH CHECK` lets a user `update` every column of their own row, including `is_admin`. Revoke the column: `revoke update (role, is_admin, credits, org_id) on profiles from authenticated;`, or enforce it in `WITH CHECK` or a trigger. The generated `Draft` type leaves these columns out, but a TypeScript type is not access control.

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

**Realtime respects RLS on `INSERT` and `UPDATE`, and not on `DELETE`.** Insert and update payloads are policy-filtered, so you only receive rows you can see. A delete is not: Postgres has no row left to check a policy against, so Supabase applies none (Realtime guide, Postgres Changes). Every subscriber to the table hears every delete, whoever owned the row.

What arrives is the primary key and nothing else. `REPLICA IDENTITY FULL` does not change that on a table with RLS: the `old` record still holds only the key (Supabase's Realtime troubleshooting guide). So:

- **Treat a `DELETE` event as "a row with this id is gone", and nothing more.** Remove the row only if that id is in the list you hold. Render nothing from `old`.
- **The id itself is what leaks.** With a sequential key, another tenant's subscriber can count your deletes. Use `uuid` keys on any table that is both multi-tenant and realtime.
- **Do not filter deletes.** A filter on delete events needs replica identity `full`, and under RLS the old row is still only the key.

**At scale, switch transport.** Supabase's guidance is to use Broadcast instead of Postgres Changes past about 3,000 concurrent subscribers on the same changes.

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
// Name the columns: select('*') also sends any column the screen does not show.
let q = supabase.from('products')
  .select('id, name, price_cents, status, created_at')
  .order('created_at', { ascending: false })
  .order('id', { ascending: false })   // tiebreak — see below
  .limit(20);

if (cursor) {
  // .or() takes its string as-is: validate what goes into it.
  if (!/^\d{4}-\d{2}-\d{2}T[\d:.]+(Z|[+-]\d{2}:\d{2})$/.test(cursor.created_at) ||
      !/^[0-9a-f-]{36}$/i.test(cursor.id)) throw new Error('bad cursor');
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
  // supabase-js returns errors instead of throwing — throwOnError() makes a
  // rejected write reach onError. .select() returns the rows actually written:
  // none means the policy hid the row, and Postgres still reported success.
  mutationFn: async (next) => {
    const { data } = await supabase.from('products').update(next).eq('id', next.id)
      .select().throwOnError();
    if (!data?.length) throw new Error('not permitted, or no longer exists');
    return data[0];
  },
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

**Under RLS, a rejected write is either `42501` or zero rows — never a network error.** Handle both as "you do not have permission" rather than "something went wrong": the retry the generic message invites will fail identically, forever. An update that returns zero rows is the one that fools people, because nothing looks wrong.

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

**A public bucket is world-readable, whatever the policies say.** Marking a bucket public switches off access control for reading and serving its files: anyone who has the URL has the file (Supabase's Storage guide, bucket fundamentals). Policies still govern uploading, deleting, moving and copying. A public bucket is for assets you would publish anyway: avatars, product images. Invoices, exports and anything per-tenant go in a private bucket behind signed URLs.

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

---

## 9. Who talks to the database

§2 holds for a request that reaches Postgres **as the user**. Which key a process holds decides whether it does.

| Key | Looks like | May live in | What Postgres sees |
|---|---|---|---|
| **Publishable** | `sb_publishable_…` | The browser bundle, a mobile app, public source | `anon`, or `authenticated` when the user's token comes with it. RLS applies |
| **Secret** | `sb_secret_…` | A server only: FastAPI, an Edge Function, a worker | `service_role`, which has `bypassrls`. No policy runs |

The older `anon` and `service_role` JWT keys are the same two authorities under their old names. Supabase is deprecating them by the end of 2026, so new code uses the two above.

### The browser holds the publishable key, and nothing else

```ts
// src/lib/supabase.ts — the only client the React code imports.
import { createClient } from '@supabase/supabase-js';
import type { Database } from './database.types';

export const supabase = createClient<Database>(
  import.meta.env.VITE_SUPABASE_URL,
  import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY,
);
```

**Every `VITE_` variable is public.** Vite writes it into the bundle, where anyone can read it. The project URL and the publishable key belong there. A secret key in a `VITE_` variable is a published secret, and so is one in any file the browser can fetch. Supabase rejects a secret key sent from a browser with a 401, but it tells a browser by its `User-Agent`: that is a safety net, not a control.

The publishable key is not a secret and gives no protection. With it, anyone can send any query the policies allow. The policies are the protection: a table in an exposed schema with RLS off answers to anyone who holds that key.

### FastAPI has two authorities, and must choose per request

**As the user (the default).** Forward the caller's access token. The publishable key goes on the `apikey` header and the user's token on `Authorization`, so PostgREST runs the query as that user and every policy applies:

```python
# One call, as the user: row-level security applies.
async def list_products(request: Request) -> list[dict]:
    token = request.headers["authorization"].removeprefix("Bearer ")
    async with httpx.AsyncClient(base_url=f"{SUPABASE_URL}/rest/v1") as db:
        response = await db.get(
            "/products",
            params={"select": "id,name,price"},
            headers={"apikey": SUPABASE_PUBLISHABLE_KEY, "Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()
        return response.json()
```

**As the service.** The secret key, for work that has no user: a webhook, a scheduled job, an admin task. Nothing in §2 applies, so the endpoint does the policy's job itself:

- Check who is calling, and what they may do, before the first query.
- Write every tenant filter by hand (`org_id = …`). There is no policy behind it to catch a missing one.
- Never send what comes back straight to a client. A `select *` as the service returns the columns §2 told you to revoke.

**The mistake that voids everything:** one module-level client built with the secret key and used for user requests. Every query succeeds, every test passes, and every user can read every tenant's rows through the API.

### Where validation and authorization live

The generated forms validate in the browser. That is a courtesy to the user, and nothing more: a request built by hand skips it.

| Concern | Enforced by | Not by |
|---|---|---|
| Which rows a user may read or change | RLS policies (`USING`, `WITH CHECK`) | A filter in the React query |
| Which columns a user may change | Column privileges, `WITH CHECK` or a trigger (§2) | The generated `Draft` type |
| What a valid value is | Constraints in the schema (`NOT NULL`, `CHECK`, unique indexes), and the FastAPI model for anything they cannot express | The form's validation |
| Who the user is | The token Supabase Auth signed; authorization data in `app_metadata` only | Anything the client sends in the body |

A table the scaffold builds screens for needs its policies written before it ships. The scaffold does not write them: it cannot know who owns a row.
