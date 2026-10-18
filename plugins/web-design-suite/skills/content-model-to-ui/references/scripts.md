# The two scripts, in full

Every argument of `introspect_schema.py` and `scaffold_ui.py`. `SKILL.md` has the workflow; this is the reference behind it.

## 1. `scripts/introspect_schema.py`

Normalise a schema, propose a UI for every column, and emit the interview.

| Flag | Does |
|---|---|
| `-o`, `--out FILE` | write `model.json` |
| `--format auto\|ddl\|ts\|json\|prisma\|drizzle` | override detection: `.prisma`, and a `.ts` or `.js` file with `pgTable(`, are found by themselves |
| `--schema NAME` | which schema to read from a generated types file (default `public`). The model records it, and the scaffold writes its policies, grants and smoke tests for that schema |
| `--summary` | the SECURITY block (from DDL), then the human-readable proposal: control, signal and confidence per column |
| `--questions` | the interview alone, as markdown |
| `--answers-template FILE` | every question pre-filled with its default, ready to edit |
| `--only TABLE` | restrict the model (repeatable or comma-separated) |

Exit `0` model produced · `1` nothing usable in the input · `2` bad invocation.

**Prisma and Drizzle (3.6.0).** A `schema.prisma` gives tables (`@@map`), columns (`@map`), native types (`@db.VarChar(80)`, `@db.Uuid`, `@db.Timestamptz`), defaults, `@id` and `@@id`, `@unique` and `@@unique`, enums, and keys with their `onDelete` from `@relation`. Prisma has no CHECK constraints, so the rules they give (a minimum, a maximum, a length) are missing, and a `DateTime` with no `@db.Timestamptz` is a timestamp without time zone, which the proposal flags as a question. A Drizzle schema (`drizzle-orm/pg-core`) gives each `pgTable`'s columns and their chained modifiers, `pgEnum`, `.references()` and `foreignKey()`, `primaryKey()`, `unique()` and `uniqueIndex()`, and a one-column `check()`. A key to `authUsers` from `drizzle-orm/supabase` is a key to `auth.users`. Neither file carries row-level security as the reader reads it, so the SECURITY block says unknown: introspect the migrations for that. Field names spelt the JavaScript way (`createdAt`, `authorId`) meet the same signals as their snake_case spelling, and the model keeps them as the source spells them.

The model's `fidelity` block records what the source could not carry, so an absent constraint is never mistaken for a permissive one. Confidence is `high` (the schema said so) · `medium` (a strong signal with a plausible alternative) · `low` (a default standing in for a decision nobody has made).

---

## 2. `scripts/scaffold_ui.py`

Turn a model plus answers into components.

| Flag | Does |
|---|---|
| `--out DIR` | output root (default `src`) |
| `--answers FILE` | the interview, answered; without it every question falls back to the proposal |
| `--entity TABLE` | one entity (repeatable or comma-separated) |
| `--stack css-modules\|tailwind` | default: the project's `.design-suite.json` `stack` (`tailwind-v3` and `tailwind-v4` scaffold Tailwind), else `css-modules` |
| `--framework react\|vue` | `react` (default): React 19 components, `.tsx`; `vue`: Vue 3.5 single-file components, `.vue` (below) |
| `--server-actions` | a Next.js App Router project: each form posts its FormData to a `'use server'` action, through React 19's `useActionState` and `useFormStatus` (supabase-integration.md §9) |
| `--dry-run` | print the tree, the sizes and the TODO count; write nothing |
| `--force` | overwrite files that already exist (the default is to skip them) |
| `--strict` | write nothing and exit `1` when the schema has a blocking security finding (RLS off, a policy that lets anyone write). For CI; the default prints the findings and still writes |

Exit `0` written · `1` the model is unusable, or `--strict` met a blocking security finding · `2` bad invocation.

It writes, per entity, `features/<table>/` (types, fields, list, detail, form, states), `db/policies/<table>.policies.todo.sql` with its `.test.sql`, and `server/<table>.schema.ts` and `server/<table>_schema.py`, the draft's constraints for the server (field-mapping.md §9); plus `ui/`, `lib/format.ts` and `lib/supabase.ts` once. With `--server-actions` it also writes `features/<table>/<Entity>ActionForm.tsx` and `server/<table>.actions.ts` per entity and `lib/supabase.server.ts` once, and `lib/supabase.ts` reads Next.js's `NEXT_PUBLIC_` variables instead of Vite's.

**On Vue (`--framework vue`).** The same kit and the same screens, one component per `.vue` file, with `<script setup lang="ts">` (Vue 3.5 or newer: the form's summary is a `useTemplateRef`). The React props are `defineProps`, its callbacks are `defineEmits` (the form emits `change`, `submit` and `cancel`; the list `create` and `clearFilters`; the detail `edit` and `delete`), each control's value is a `v-model`, and `<slot />` takes the place of `children` (the state block's action is the `action` slot). Each CSS Module's rules are the component's `<style scoped>` block, inside `@layer components` (stack-frameworks.md §1, §3); the seven controls are a file each and share `ui/Control/Control.css` through `<style scoped src>`. A root's class is the component's name (`.ui-button`, `.orders-list`), never `.root`, because Vue puts a parent's scope on a child component's root element too. A control is one element that every attribute the caller passes lands on (`v-bind="$attrs"`, with `inheritAttrs: false`), which `a11y_static` reads as JSX's `{...rest}`. The six states are a component each (`OrdersEmpty.vue` …), the detail's state type joins the types file, and every file that is not a component (types, fields, `lib/`, `server/`, `db/`) is the React scaffold's. On the Tailwind stack the classes become utilities and the `<style>` blocks go, as with React. `--server-actions` is React's alone: with `--framework vue` it exits `2`.

**On the Tailwind stack.** Layout, spacing, colour and type become utility classes from the suite's theme — with no arbitrary values, because if a utility does not exist then neither does the token. Variant and state tables cannot be expressed that way, so they live in one emitted `styles/scaffold.css` under `@layer components`. That boundary is real and is stated rather than hidden: a utility system is excellent at layout and has nothing to say about a component's state machine.
