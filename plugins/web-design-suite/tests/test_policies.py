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

from wds_support import TempDirTest, class_temp_dir, env, output, run_py

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


class Scaffolded(TempDirTest):

    def scaffold(self, ddl, *args):
        self.write("schema.sql", ddl)
        proc = run_py("content-model-to-ui", "introspect_schema", "schema.sql", "-o", "model.json",
                      cwd=self.tmp)
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

    def database(self, ddl, seed=""):
        db = f"t{self.id().rsplit('.', 1)[-1][-40:]}".lower()
        self.psql_ok("postgres", f"drop database if exists {db}")
        self.psql_ok("postgres", f"create database {db}")
        self.psql_ok(db, STUB + ddl + seed)
        src = self.scaffold(ddl)
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


if __name__ == "__main__":
    unittest.main()
