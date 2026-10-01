# W1 facts, re-read at source on 2026-09-25 and again on 2026-10-01 (for tests/fixtures/evidence.json)

Every quote below was found word for word on 2026-10-01, in the page's `.md` form (the same URL with `.md` appended). Added that day:

- https://supabase.com/docs/guides/api/api-keys
  - "Send publishable and secret keys on the `apikey` header, not on `Authorization: Bearer`."
  - Publishable key: "Safe to expose online: web page, mobile or desktop app, GitHub actions, CLIs, source code."
- https://supabase.com/docs/guides/database/postgres/row-level-security
  - A change to `app_metadata` "will not be reflected using `auth.jwt()` until the user's JWT is refreshed."
  - The template: `create function private.user_list_ids() … security definer set search_path = '' stable`, then `revoke execute on function private.user_list_ids() from public; grant usage on schema private to authenticated; grant execute … to authenticated`.
- https://www.postgresql.org/docs/current/sql-revoke.html
  - "if a role has been granted privileges on a table, then revoking the same privileges from individual columns will have no effect."
- https://www.postgresql.org/docs/current/sql-createpolicy.html
  - "If only a USING clause is specified, then that clause will be used for both USING and WITH CHECK cases."
- https://supabase.com/docs/guides/database/postgres/column-level-security
  - "By default, our table will have a table-level `UPDATE` privilege, which means that the `authenticated` role can update all the columns in the table."
- https://supabase.com/docs/guides/realtime/authorization
  - "By creating RLS policies on the `realtime.messages` table you can control the access users have to a Channel topic"
  - "To enforce private channels you need to disable the 'Allow public access' setting in Realtime Settings"
- https://supabase.com/docs/guides/storage/buckets/fundamentals
  - "When a bucket is designated as 'Public,' it effectively bypasses access controls for both retrieving and serving files within the bucket. This means that anyone who possesses the asset URL can readily access the file. Access control is still enforced for other types of operations including uploading, deleting, moving, and copying."

## Read on 2026-09-25

- https://supabase.com/docs/guides/getting-started/migrating-to-new-api-keys
  - "Supabase is deprecating the `anon` and `service_role` keys by the end of 2026."
  - Publishable key (`sb_publishable_xxx`): "Browsers, mobile and desktop apps, CLIs, public source"
  - Secret key (`sb_secret_xxx`): "Servers, Edge Functions, workers, other backend code"
  - "They return HTTP 401 if used in a browser (matched on the `User-Agent` header)"
  - "Secret keys bypass Row Level Security and have full access to your data."
- https://supabase.com/docs/guides/database/postgres/row-level-security
  - "A `security definer` function in an exposed schema is callable over the Data API with the creator's privileges. Never create one in a schema listed under "Exposed schemas" in your API settings."
  - "Set `search_path = ''` on every `security definer` function and schema-qualify the names inside it."
  - "`raw_user_meta_data` - can be updated by the authenticated user using the `supabase.auth.update()` function. It is not a good place to store authorization data."
  - "`raw_app_meta_data` - cannot be updated by the user, so it's a good place to store authorization data."
  - "To perform an `UPDATE` operation, a corresponding `SELECT` policy is required."
  - "A secret key authorizes access through the `service_role` Postgres role, which has the `bypassrls` attribute."
- https://www.postgresql.org/docs/current/ddl-rowsecurity.html (PostgreSQL 18)
  - "Referential integrity checks, such as unique or primary key constraints and foreign key references, always bypass row security to ensure that data integrity is maintained."
  - Example: "RLS silently prevents updating other rows" -> `UPDATE 0`
  - WITH CHECK violation -> `ERROR:  new row violates WITH CHECK OPTION for "passwd"`
- Still to re-read, for the parser work (DL-C2): the supabase CLI dump format (`--quote-all-identifiers`) and the `gen types` format.
- https://supabase.com/docs/guides/realtime/postgres-changes
  - "Caution: RLS policies are not applied to `DELETE` statements, because there is no way for Postgres to verify that a user has access to a deleted record."
  - "You can only filter Delete events when tracking Postgres Changes if the table has the `replica identity` set to `full`."
  - "If you expect more than ~3,000 concurrent subscribers on the same changes, use Broadcast to stream database changes instead. ..."
  - (The page does NOT say `old` holds only the PK under RLS; the review cited the troubleshooting page for that. Re-read it before writing the doc.)
- https://supabase.com/docs/guides/troubleshooting/realtime-postgres-changes-troubleshooting
  - "If the table has Row Level Security enabled, `replica identity full` isn't enough by itself: the `old` record still contains only the primary key."
