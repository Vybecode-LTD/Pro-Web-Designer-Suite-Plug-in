"""The database side of the scaffold (DL-B2, DL-B1): per table a proposal of
row-level security, policies and column grants with a smoke test, and the
browser's one Supabase client.

Regressions covered:
- DL-B2: the scaffold decided which columns a form writes and emitted client
  validation, but nothing proposed policies or column grants, so its screens
  sat on tables that anyone holding the publishable key could write.
- DL-B1: no client file said which key the browser holds.

PoliciesRunOnPostgres runs the generated SQL on a scratch Postgres cluster
when `initdb`, `pg_ctl` and `psql` are on PATH, and skips otherwise.
"""
from __future__ import annotations

import json
import pathlib
import re
import shutil
import socket
import subprocess
import unittest

from wds_support import TempDirTest, class_temp_dir, env, load_script, output, run_py

FIXTURES = pathlib.Path(__file__).resolve().parent / "fixtures" / "supabase"
SHOP = (FIXTURES / "shop.sql").read_text(encoding="utf-8")
SHOP_TABLES = SHOP.split("\nalter table categories enable", 1)[0] + "\n"     # no RLS, no policies

SAAS = """\
create table organizations (id uuid primary key default gen_random_uuid(), name text not null,
  plan text not null default 'free');
create table profiles (id uuid primary key references auth.users (id) on delete cascade,
  display_name text not null, role text not null default 'member',
  is_admin boolean not null default false, credits integer not null default 0,
  org_id uuid references organizations (id), api_token text);
create table projects (id uuid primary key default gen_random_uuid(), name text not null,
  owner_id uuid not null references profiles (id));
create table documents (id uuid primary key default gen_random_uuid(),
  org_id uuid not null references organizations (id), title text not null);
"""

# The parts of Supabase the policies lean on, in a plain Postgres. auth.uid()
# reads the claims as Supabase's own does.
STUB = """\
create schema auth;
create table auth.users (id uuid primary key);
create function auth.uid() returns uuid language sql stable as $$
  select coalesce(nullif(current_setting('request.jwt.claim.sub', true), ''),
                  (nullif(current_setting('request.jwt.claims', true), '')::jsonb ->> 'sub'))::uuid
$$;
grant usage on schema public, auth to anon, authenticated, service_role;
grant execute on function auth.uid() to anon, authenticated;
alter default privileges in schema public grant all on tables to anon, authenticated, service_role;
"""

# Another user's order, so that a policy which shows every row has one to show.
SHOP_SEED = """\
insert into auth.users (id) values ('00000000-0000-4000-8000-000000000001'),
  ('00000000-0000-4000-8000-000000000002');
insert into public.customers (id, email, full_name)
  values ('00000000-0000-4000-8000-000000000002', 'b@example.com', 'B');
insert into public.products (title, slug, price_cents) values ('P', 'p', 100);
insert into public.orders (customer_id, total_cents) values ('00000000-0000-4000-8000-000000000002', 100);
insert into public.order_items (order_id, product_id, quantity, unit_price_cents)
  select o.id, p.id, 1, 100 from public.orders o, public.products p;
"""


# A schema of its own (N20), with the grants Supabase's docs give for one the
# API exposes; the parser passes over them.
APP = """\
create schema app;
grant usage on schema app to anon, authenticated, service_role;
alter default privileges in schema app grant all on tables to anon, authenticated, service_role;
create table app.profiles (id uuid primary key references auth.users (id), name text not null);
create table app.notes (id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references app.profiles (id), body text not null);
create table app.note_links (id uuid primary key default gen_random_uuid(),
  note_id uuid not null references app.notes (id), url text not null);
create table app.tags (id uuid primary key default gen_random_uuid(), label text not null);
"""

# Reserved words as names (N21), and a name long enough that Postgres would
# cut the four policy names to one (N22).
LONG = "customer_subscription_renewal_reminder_preferences_by_region"
AWKWARD = f"""\
create table "select" (id uuid primary key default gen_random_uuid(),
  "where" text not null, owner_id uuid not null references auth.users (id));
create table "window" (id uuid primary key default gen_random_uuid(),
  select_id uuid not null references "select" (id), "for" text);
create table {LONG} (id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users (id), "limit" integer not null);
create table lookups (id uuid primary key default gen_random_uuid(), label text not null);
create table "it's" (id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users (id), body text);
create table "cash$$flow" (id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users (id), amount integer);
"""


class Scaffolded(TempDirTest):

    def scaffold(self, ddl, *args, schema=None):
        self.write("schema.sql", ddl)
        proc = run_py("content-model-to-ui", "introspect_schema", "schema.sql", "-o", "model.json",
                      *(["--schema", schema] if schema else []), cwd=self.tmp)
        self.assertEqual(proc.returncode, 0, output(proc))
        proc = run_py("content-model-to-ui", "scaffold_ui", "model.json", "--out", "src", *args,
                      cwd=self.tmp)
        self.assertEqual(proc.returncode, 0, output(proc))
        return self.tmp / "src"

    def policies(self, src, table):
        return (src / "db" / "policies" / f"{table}.policies.todo.sql").read_text(encoding="utf-8")


def owner_line(text):
    return re.search(r"^-- Whose a row is: (.*?)\.$", text, re.M).group(1)


def grants(text, verb):
    m = re.search(rf"^grant {verb} \(([^)]*)\) on ", text, re.M)
    return m.group(1).split(", ") if m else []


class PoliciesAreProposed(Scaffolded):

    def test_every_table_has_a_proposal_and_a_test(self):
        src = self.scaffold(SHOP_TABLES)
        tables = ["categories", "customers", "order_items", "orders", "product_tags", "products", "tags"]
        self.assertEqual(sorted(f"{t}.policies.{kind}.sql" for t in tables for kind in ("test", "todo")),
                         sorted(p.name for p in (src / "db" / "policies").iterdir()))
        for t in tables:
            with self.subTest(table=t):
                self.assertIn(f"alter table public.{t} enable row level security;", self.policies(src, t))
                self.assertIn("TODO(policy)", self.policies(src, t))

    def test_whose_a_row_is_read_from_the_keys(self):
        src = self.scaffold(SHOP_TABLES)
        self.assertEqual("id is the user's own id, a key into auth.users",
                         owner_line(self.policies(src, "customers")))
        self.assertEqual("customer_id is a key into customers, whose id is the user's",
                         owner_line(self.policies(src, "orders")))
        self.assertIn("order_id makes it part of a row of orders", owner_line(self.policies(src, "order_items")))
        self.assertIn("p1.customer_id = (select auth.uid())", self.policies(src, "order_items"))
        self.assertEqual("no column says who a row belongs to", owner_line(self.policies(src, "categories")))

    def test_no_policy_lets_the_browser_write_every_row(self):
        src = self.scaffold(SHOP_TABLES + SAAS.replace("profiles", "people"))
        writes = 0
        for path in (src / "db" / "policies").glob("*.todo.sql"):
            text = path.read_text(encoding="utf-8")
            for m in re.finditer(r"^create policy .*?;$", text, re.M | re.S):
                with self.subTest(policy=m.group(0).splitlines()[0]):
                    if re.search(r"\bfor (insert|update|delete|all)\b", m.group(0)):
                        writes += 1
                        self.assertNotRegex(m.group(0), r"(using|with check) \(true\)")
        # Insert, update and delete on customers, orders, order_items, people and projects.
        self.assertEqual(5 * 3, writes)

    def test_the_grants_are_the_forms_columns_and_never_authority(self):
        src = self.scaffold(SAAS)
        text = self.policies(src, "profiles")
        types = next(src.rglob("profiles.types.ts")).read_text(encoding="utf-8")
        draft = re.findall(r"\| '(\w+)'", types.split("export type ProfileDraft", 1)[1].split(">;", 1)[0])
        self.assertEqual(draft, grants(text, "update"))
        self.assertEqual(draft + ["id"], grants(text, "insert"))
        for column in ("role", "is_admin", "credits", "org_id", "api_token", "id"):
            self.assertNotIn(column, grants(text, "update"))
        self.assertIn("revoke insert, update on public.profiles from authenticated;", text)

    def test_a_tenant_table_gets_a_template_and_no_policy(self):
        src = self.scaffold(SAAS)
        text = self.policies(src, "documents")
        self.assertEqual("org_id names a tenant", owner_line(text))
        self.assertNotRegex(text, r"(?m)^create policy")
        self.assertIn("private.user_org_ids()", text)
        self.assertEqual("owner_id is a key into profiles, whose id is the user's",
                         owner_line(self.policies(src, "projects")))

    def test_the_proposal_closes_what_the_security_pass_finds(self):
        src = self.scaffold(SHOP_TABLES)
        files = [str(p.relative_to(self.tmp)) for p in sorted((src / "db" / "policies").glob("*.todo.sql"))]
        proc = run_py("content-model-to-ui", "introspect_schema", "schema.sql", *files, "-o", "after.json",
                      cwd=self.tmp)
        self.assertEqual(proc.returncode, 0, output(proc))
        after = json.loads((self.tmp / "after.json").read_text(encoding="utf-8"))
        before = json.loads((self.tmp / "model.json").read_text(encoding="utf-8"))
        self.assertEqual(7, len([f for f in before["security"]["findings"] if f["code"] == "rls-off"]))
        self.assertEqual([], after["security"]["findings"])

    def test_one_entity_brings_its_join_tables(self):
        src = self.scaffold(SHOP_TABLES, "--entity", "products")
        self.assertEqual(["product_tags", "products"],
                         sorted(p.name.split(".")[0] for p in (src / "db" / "policies").glob("*.todo.sql")))

    def test_the_schema_is_the_models(self):
        # N20: a model introspected with --schema app put every statement on public.
        src = self.scaffold(APP, schema="app")
        for path in sorted((src / "db" / "policies").iterdir()):
            with self.subTest(file=path.name):
                self.assertNotIn("public.", path.read_text(encoding="utf-8"))
        self.assertIn("alter table app.notes enable row level security;", self.policies(src, "notes"))
        self.assertIn("exists (select 1 from app.notes p1 ", self.policies(src, "note_links"))
        test = (src / "db" / "policies" / "tags.policies.test.sql").read_text(encoding="utf-8")
        self.assertIn("where schemaname = 'app'", test)

    def test_a_reserved_word_keeps_its_quotes(self):
        # N21: sql_ident quoted nine reserved words, so `select` and `where` were bare.
        src = self.scaffold(AWKWARD)
        text = self.policies(src, "select")
        self.assertIn('alter table public."select" enable row level security;', text)
        self.assertIn('create policy "select: owner reads" on public."select"', text)
        self.assertEqual(['"where"'], grants(text, "update"))
        self.assertIn('exists (select 1 from public."select" p1 where p1.id = "window".select_id',
                      self.policies(src, "window"))

    def test_the_scaffold_quotes_what_the_parser_keeps_quoted(self):
        # N21: the scripts stand alone, so each keeps its own copy of the list.
        self.assertEqual(load_script("content-model-to-ui", "introspect_schema").KEEP_QUOTED,
                         load_script("content-model-to-ui", "scaffold_ui").KEEP_QUOTED)

    def test_policy_names_fit_in_63_bytes(self):
        # N22: Postgres cuts a name at 63 bytes, which made a long table's four names one.
        src = self.scaffold(AWKWARD)
        names = re.findall(r'^create policy "([^"]+)"', self.policies(src, LONG), re.M)
        self.assertEqual(4, len(set(names)), names)
        for name in names:
            with self.subTest(name=name):
                self.assertLessEqual(len(name.encode("utf-8")), 63)
                self.assertTrue(name.startswith(LONG[:30]))

    def test_the_browser_client_holds_the_publishable_key_only(self):
        src = self.scaffold(SHOP_TABLES)
        client = (src / "lib" / "supabase.ts").read_text(encoding="utf-8")
        self.assertIn("import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY", client)
        self.assertEqual(2, len(re.findall(r"import\.meta\.env\.", client)))
        self.assertIn("startsWith('sb_secret_')", client)
        self.assertIn("=== 'service_role'", client)
        self.assertIn("createClient<Database>(url, publishableKey)", client)


def _postgres() -> str | None:
    tools = [shutil.which(t) for t in ("initdb", "pg_ctl", "psql")]
    return None if all(tools) else "Postgres (initdb, pg_ctl, psql) is not on PATH"


@unittest.skipIf(_postgres(), _postgres())
class PoliciesRunOnPostgres(Scaffolded):
    """The proposal applies, and its smoke test passes, on a real Postgres;
    and the smoke test fails when a policy, a grant or RLS is wrong."""

    @classmethod
    def setUpClass(cls):
        cls.root = class_temp_dir(cls, "wds-pg-")
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            cls.port = str(s.getsockname()[1])
        data = cls.root / "data"
        subprocess.run(["initdb", "-D", str(data), "-U", "postgres", "-A", "trust", "-E", "UTF8",
                        "--locale=C"], check=True, capture_output=True, env=env())
        # No pipes: the server pg_ctl starts would inherit them, and on Windows
        # the call would wait for the server to exit. Its output goes to `log`.
        cls.data = data
        subprocess.run(["pg_ctl", "-D", str(data), "-o", f"-p {cls.port} -c listen_addresses=127.0.0.1",
                        "-l", str(cls.root / "log"), "-w", "-t", "60", "start"], check=True,
                       stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       timeout=90, env=env())
        cls.psql_ok("postgres", "create role anon nologin; create role authenticated nologin;"
                                "create role service_role nologin bypassrls;")

    @classmethod
    def tearDownClass(cls):
        subprocess.run(["pg_ctl", "-D", str(cls.data), "-m", "fast", "-w", "stop"],
                       stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       timeout=90, env=env())

    @classmethod
    def psql(cls, db, sql=None, file=None):
        args = ["psql", "-X", "-q", "-v", "ON_ERROR_STOP=1", "-h", "127.0.0.1", "-p", cls.port,
                "-U", "postgres", "-d", db]
        args += ["-f", str(file)] if file else ["-c", sql]
        return subprocess.run(args, capture_output=True, stdin=subprocess.DEVNULL, timeout=60, env=env())

    @classmethod
    def psql_ok(cls, db, sql):
        proc = cls.psql(db, sql)
        if proc.returncode:
            raise AssertionError(output(proc))

    def database(self, ddl, seed="", schema=None):
        db = f"t{self.id().rsplit('.', 1)[-1][-40:]}".lower()
        self.psql_ok("postgres", f"drop database if exists {db}")
        self.psql_ok("postgres", f"create database {db}")
        self.psql_ok(db, STUB + ddl + seed)
        src = self.scaffold(ddl, schema=schema)
        proposals = sorted((src / "db" / "policies").glob("*.todo.sql"))
        self.assertGreaterEqual(len(proposals), 4)
        for path in proposals:
            proc = self.psql(db, file=path)
            self.assertEqual(0, proc.returncode, f"{path.name}: {output(proc)}")
        return db, src

    def smoke(self, db, src, table):
        return self.psql(db, file=src / "db" / "policies" / f"{table}.policies.test.sql")

    def test_the_shop_proposal_applies_and_passes_its_tests(self):
        db, src = self.database(SHOP_TABLES, SHOP_SEED)
        for path in sorted((src / "db" / "policies").glob("*.test.sql")):
            with self.subTest(test=path.name):
                proc = self.psql(db, file=path)
                self.assertEqual(0, proc.returncode, output(proc))

    def test_the_saas_proposal_applies_and_passes_its_tests(self):
        db, src = self.database(SAAS)
        for path in sorted((src / "db" / "policies").glob("*.test.sql")):
            with self.subTest(test=path.name):
                proc = self.psql(db, file=path)
                self.assertEqual(0, proc.returncode, output(proc))

    def test_the_smoke_test_fails_when_the_database_is_wrong(self):
        db, src = self.database(SHOP_TABLES, SHOP_SEED)
        for table, breakage, message in (
                ("orders", 'drop policy "orders: owner reads" on public.orders; '
                           'create policy "orders: owner reads" on public.orders '
                           "for select to authenticated using (true);",
                 "a signed-in user can read orders rows that are not theirs"),
                ("customers", "grant update (id) on public.customers to authenticated;",
                 "a signed-in user can change customers.id"),
                ("tags", "alter table public.tags disable row level security;",
                 "row-level security is off on public.tags"),
                ("categories", 'create policy "anyone writes" on public.categories '
                               "for insert to authenticated with check (true);",
                 "a policy lets the browser write public.categories")):
            with self.subTest(table=table):
                self.psql_ok(db, breakage)
                proc = self.smoke(db, src, table)
                self.assertNotEqual(0, proc.returncode)
                self.assertIn(message, output(proc))

    def test_a_schema_of_its_own_applies_and_passes_its_tests(self):
        # N20.
        db, src = self.database(APP, schema="app")
        for path in sorted((src / "db" / "policies").glob("*.test.sql")):
            with self.subTest(test=path.name):
                proc = self.psql(db, file=path)
                self.assertEqual(0, proc.returncode, output(proc))

    def test_reserved_words_and_long_names_apply_and_pass_their_tests(self):
        # N21 and N22.
        db, src = self.database(AWKWARD)
        for path in sorted((src / "db" / "policies").glob("*.test.sql")):
            with self.subTest(test=path.name):
                proc = self.psql(db, file=path)
                self.assertEqual(0, proc.returncode, output(proc))

    def test_every_reserved_word_is_on_the_list(self):
        # N21: Postgres's own list, the words it reserves outright or for
        # functions and types. Neither can name a table or column unquoted.
        proc = self.psql("postgres", "copy (select word from pg_get_keywords() "
                                     "where catcode in ('R', 'T')) to stdout")
        self.assertEqual(0, proc.returncode, output(proc))
        words = set(proc.stdout.decode("utf-8").split())
        self.assertGreater(len(words), 90)
        self.assertEqual(set(), words - load_script("content-model-to-ui", "scaffold_ui").KEEP_QUOTED)

    def test_a_write_policy_for_the_server_is_not_the_browsers(self):
        # N23: the smoke test counted a service_role policy as one the browser holds.
        db, src = self.database(SHOP_TABLES, SHOP_SEED)
        self.psql_ok(db, 'create policy "the server writes" on public.categories '
                         "for insert to service_role with check (true);")
        proc = self.smoke(db, src, "categories")
        self.assertEqual(0, proc.returncode, output(proc))
        self.psql_ok(db, 'create policy "anyone writes" on public.categories for all using (true);')
        proc = self.smoke(db, src, "categories")
        self.assertNotEqual(0, proc.returncode)
        self.assertIn("a policy lets the browser write public.categories", output(proc))

    def test_a_write_policy_for_a_role_the_browser_inherits_is_the_browsers(self):
        # The review of #16: authenticated, a member of an editor role, holds
        # the editor's policies too.
        db, src = self.database(SHOP_TABLES, SHOP_SEED)
        # The control: a membership WITH INHERIT FALSE gives the browser none of
        # the role's policies without SET ROLE, so its write policy passes.
        self.psql_ok(db, "do $$ begin create role wds_reader nologin; "
                         "exception when duplicate_object then null; end $$;")
        self.psql_ok(db, "grant wds_reader to authenticated with inherit false; "
                         'create policy "readers write" on public.categories for insert to wds_reader '
                         "with check (true);")
        proc = self.smoke(db, src, "categories")
        self.assertEqual(0, proc.returncode, output(proc))
        self.psql_ok(db, "do $$ begin create role wds_editor nologin; "
                         "exception when duplicate_object then null; end $$;")
        self.psql_ok(db, "grant wds_editor to authenticated; "
                         'create policy "editors write" on public.categories for insert to wds_editor '
                         "with check (true);")
        proc = self.smoke(db, src, "categories")
        self.assertNotEqual(0, proc.returncode)
        self.assertIn("a policy lets the browser write public.categories", output(proc))


if __name__ == "__main__":
    unittest.main()
