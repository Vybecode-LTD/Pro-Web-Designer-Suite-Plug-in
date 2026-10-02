# Schema fixtures

What `introspect_schema` is tested on (`tests/test_schema_sources.py`). Each file is either real output or the same schema in another real format, so the parser is tested on what Postgres and Supabase write.

| File | What it is | How it was made |
|---|---|---|
| `shop.sql` | The worked example's seven tables, written as a migration, with row-level security and policies | By hand |
| `shop.dump.sql` | `shop.sql` after a round trip through Postgres | Loaded into Postgres 18 after the stub below, then `pg_dump --schema-only --quote-all-identifiers --no-owner -n public` (pg_dump 18.4) |
| `shop.types.ts` | `shop.sql` as `supabase gen types typescript` writes it | By hand, in the exact layout of `brewr.types.ts`: sorted tables and columns, `?: never` for a `GENERATED ALWAYS` identity, no relationship into `auth`, and prettier's wrapping of a union too long for its line. The helper types at the end are copied from `brewr.types.ts` |
| `brewr.types.ts` | `gen types` for a real 25-table Supabase project, unedited | The Supabase connector's `generate_typescript_types`, 2026-10-01. The project has no rows; the file holds table and column names only |

`supabase db pull` and `db dump` run the same `pg_dump --schema-only --quote-all-identifier`, then comment out the `\restrict` lines and add `IF NOT EXISTS` to each `CREATE TABLE` (supabase/cli `apps/cli-go/pkg/migration/scripts/dump_schema.sh`, read 2026-10-01). The parser reads both forms.

## The stub that makes a plain Postgres look like Supabase

```sql
create role anon nologin;
create role authenticated nologin;
create role service_role nologin bypassrls;
create schema auth;
create table auth.users (id uuid primary key);
create function auth.uid() returns uuid language sql stable as $$ select null::uuid $$;
grant usage on schema public to anon, authenticated, service_role;
alter default privileges in schema public grant all on tables to anon, authenticated, service_role;
```

The last line is Supabase's default, which is why the dump grants every table to `authenticated`.

To remake `shop.dump.sql`: `initdb` a scratch cluster, create a database, run the stub and then `shop.sql` with `psql -v ON_ERROR_STOP=1`, and dump it with the command above. The `\restrict` key changes on every dump.
