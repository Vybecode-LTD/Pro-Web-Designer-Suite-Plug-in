---
name: schema-to-screens
description: Turn a database schema into screens - introspect it, ask the questions only a person can answer, scaffold the UI, audit it, and check the security the screens depend on.
disable-model-invocation: true
argument-hint: "SCHEMA (supabase/migrations/*.sql, a dump or generated types)"
allowed-tools:
  - Bash(python "${CLAUDE_PLUGIN_ROOT}/skills/content-model-to-ui/scripts/introspect_schema.py" *)
  - Bash(python3 "${CLAUDE_PLUGIN_ROOT}/skills/content-model-to-ui/scripts/introspect_schema.py" *)
  - Bash(python "${CLAUDE_PLUGIN_ROOT}/skills/content-model-to-ui/scripts/scaffold_ui.py" *)
  - Bash(python3 "${CLAUDE_PLUGIN_ROOT}/skills/content-model-to-ui/scripts/scaffold_ui.py" *)
  - Bash(python "${CLAUDE_PLUGIN_ROOT}/skills/web-design-studio/scripts/audit_design.py" *)
  - Bash(python3 "${CLAUDE_PLUGIN_ROOT}/skills/web-design-studio/scripts/audit_design.py" *)
---

# Schema to screens

Run content-model-to-ui's workflow on the user's schema, from the project's root. SCHEMA is `$ARGUMENTS`: the migration files in order (`supabase/migrations/*.sql`), a structure-only dump, or generated types. Without one, ask. Use `python3` where `python` is not Python 3 (macOS).

1. **Introspect**, and read the proposal and the security pass:
   ```bash
   python "${CLAUDE_PLUGIN_ROOT}/skills/content-model-to-ui/scripts/introspect_schema.py" SCHEMA -o design-reports/screens/model.json --summary
   ```
2. **Ask** the questions only a person can answer (who edits a field, what is sensitive, what a status means). Put them to the user, grouped, and wait:
   ```bash
   python "${CLAUDE_PLUGIN_ROOT}/skills/content-model-to-ui/scripts/introspect_schema.py" SCHEMA --questions
   python "${CLAUDE_PLUGIN_ROOT}/skills/content-model-to-ui/scripts/introspect_schema.py" SCHEMA --answers-template design-reports/screens/answers.json
   ```
   Write the user's answers into `design-reports/screens/answers.json`. An unanswered question keeps the machine's proposal; say which ones.
3. **Scaffold**, first as a dry run. `--strict` stops on a blocking security finding (row-level security off, a privilege the publishable key should not have), and **a stop ends the command**: the database is fixed first.
   ```bash
   python "${CLAUDE_PLUGIN_ROOT}/skills/content-model-to-ui/scripts/scaffold_ui.py" design-reports/screens/model.json --answers design-reports/screens/answers.json --strict --dry-run
   python "${CLAUDE_PLUGIN_ROOT}/skills/content-model-to-ui/scripts/scaffold_ui.py" design-reports/screens/model.json --answers design-reports/screens/answers.json --strict
   ```
   It never overwrites a file; `--force` only when the user asks. `--out DIR` when the source is not `src`.
4. **Audit** what it wrote:
   ```bash
   python "${CLAUDE_PLUGIN_ROOT}/skills/web-design-studio/scripts/audit_design.py" src --strict
   ```
5. **The security checklist.** Read content-model-to-ui's `references/supabase-integration.md` §2 and §9, and check the scaffold against them: the proposed policies and their smoke test, which columns row-level security cannot protect, `WITH CHECK` on every write, and that the browser holds the publishable key and nothing else.

Then tell the user:
- the security pass: each blocking finding and warning, by table, and, when the scaffold stopped, the fix in the database;
- what was written, and the TODO markers left: each is a decision a person still owes;
- the audit's verdict, and the checklist, item by item, with what still needs a person. The proposed policies are a guess from the keys until someone corrects them.
