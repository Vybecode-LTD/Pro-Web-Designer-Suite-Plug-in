#!/usr/bin/env python3
"""scaffold_ui.py — step 4 of the content-model-to-ui workflow.

Take the `model.json` that `introspect_schema.py` produced, plus the answers to
the questions it asked, and write a React 19 (or, with --framework, a Vue 3.5
or a Svelte 5) + TypeScript scaffold: one folder per entity with a list view, a detail
view, a form, and the empty, loading and error states that generators normally
leave to default.

WHAT THIS IS AND IS NOT
-----------------------
It is a starting point a designer would not be embarrassed by: real layout
primitives, real role tokens, the five-part component shape, all seven
interactive states, and `audit_design.py --strict` clean.

It is NOT a finished product. Every state component carries a `TODO(copy)`
naming the sentence a human has to write, every control the scaffold cannot
honestly render is a marked stub rather than a guess. For the database it
writes a proposal, not a decision: `db/policies/` holds per table the RLS,
policies and column grants it guesses from the keys, each with a smoke
test, and `lib/supabase.ts` the browser's one client. Beyond that no data layer is
generated at all — the components take their rows as props so that the fetch,
the cache and the mutation stay yours.

Nothing it writes carries an `@generated` marker, on purpose: `audit_design.py`
skips generated files, and output that skips the gate proves nothing. Treat the
scaffold as code you now own.

STACKS
------
  css-modules   (default) one `.module.css` per component, wrapped in
                @layer components, Tier-3 sockets defaulting to Tier-2 roles.
  tailwind      the same components with utility classes from the suite's
                Tailwind theme. No arbitrary values — if a class does not
                exist, the token does not exist either, and that is the point.

USAGE
-----
    # Everything, into ./src
    python -m scripts.scaffold_ui model.json --out src

    # Look before you write
    python -m scripts.scaffold_ui model.json --out src --dry-run

    # One entity, with the interview answered
    python -m scripts.scaffold_ui model.json --out src \\
        --answers answers.json --entity products

    # Tailwind instead of CSS Modules
    python -m scripts.scaffold_ui model.json --out src --stack tailwind

    # Vue 3.5 single-file components, or Svelte 5 ones, instead of React
    python -m scripts.scaffold_ui model.json --out src --framework vue
    python -m scripts.scaffold_ui model.json --out src --framework svelte

Then, always:

    python -m scripts.audit_design src/ --strict

    # In CI: refuse when the schema has a blocking security finding
    python -m scripts.scaffold_ui model.json --out src --strict

Exit codes: 0 written (or dry-run printed) · 1 the model is unusable, or
--strict met a blocking security finding · 2 bad invocation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import keyword
import re
import sys
from pathlib import Path
from string import Template
from typing import Any

# A sibling import would otherwise leave __pycache__ inside the installed
# plugin. project_config.py is a copy of the plugin's shared/ master (P24).
sys.dont_write_bytecode = True
try:                                              # python -m scripts.scaffold_ui
    from .project_config import ConfigError, project_config
except ImportError:                               # python scripts/scaffold_ui.py, or loaded by path
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from project_config import ConfigError, project_config  # type: ignore[no-redef]

MODEL_SCHEMA = "content-model-to-ui/model/1"

# Controls the scaffold renders for real. Anything else becomes a marked stub
# with a TODO, because a plausible-looking wrong control is more expensive than
# an obviously missing one.
NATIVE_CONTROLS = {
    "text-input", "textarea", "email-input", "url-input", "tel-input",
    "password-input", "number-input", "currency-input", "percent-input",
    "stepper", "checkbox", "switch", "select", "radio-group", "multi-select",
    "date-picker", "datetime-picker", "time-picker", "slug-input",
    "color-picker", "readonly-text", "readonly-timestamp",
}

STUB_REASON = {
    "combobox": "needs a listbox with type-ahead, async options and full "
                "keyboard semantics — see field-mapping.md §6",
    "multi-combobox": "as combobox, plus chip removal and a live region that "
                      "announces each add and remove",
    "record-picker": "a modal with its own search, paging and empty state",
    "inline-subtable": "an editable child table with add/remove rows and its "
                       "own dirty tracking",
    "image-upload": "needs the Storage bucket, the signed-URL policy and a "
                    "crop — answer the .storage question first",
    "file-upload": "needs the Storage bucket and an accept list — answer the "
                   ".storage question first",
    "rich-text": "an editor is a dependency you cannot remove later; confirm "
                 "it is wanted before adding one",
    "geo-point": "needs a map provider",
    "date-range": "two coupled date inputs that validate against each other",
    "key-value-editor": "needs the key whitelist from the .shape question",
    # A text box bound to the array or the object corrupted it: `String()`
    # made tags comma text and JSON `[object Object]` (Codex on #176). Each
    # needs text of its own that is not yet a value.
    "tag-input": "the tag being typed is not a tag yet, so it needs its own text, an add and a "
                 "remove per tag, and a live region that announces each",
    "json-editor": "JSON is invalid while it is typed, so it needs its own text, a parse on blur "
                   "and the parse error shown; or fields, if the .shape question names the keys",
}

TS_KEYWORDS = {"default", "class", "function", "new", "delete", "case"}


# ---------------------------------------------------------------------------
# Naming
# ---------------------------------------------------------------------------

def pascal(s: str) -> str:
    return "".join(p.capitalize() for p in re.split(r"[_\-\s]+", s) if p)


def camel(s: str) -> str:
    p = pascal(s)
    return p[:1].lower() + p[1:]


def singular(name: str) -> str:
    for suffix, repl in (("ies", "y"), ("ses", "s"), ("xes", "x"),
                         ("ches", "ch"), ("shes", "sh")):
        if name.endswith(suffix):
            return name[: -len(suffix)] + repl
    if name.endswith("s") and not name.endswith("ss"):
        return name[:-1]
    return name


def prop_key(name: str) -> str:
    """A TS object key that does not need quoting, or one that does."""
    return name if re.fullmatch(r"[A-Za-z_$][\w$]*", name) else json.dumps(name, ensure_ascii=False)


def js_string(name: str) -> str:
    """`name` as a single-quoted JS string literal, escaped: a column called
    `it's` was an unterminated string (the audit's E3)."""
    return "'" + json.dumps(name, ensure_ascii=False)[1:-1].replace("'", "\\'") + "'"


def member(obj: str, name: str) -> str:
    """`obj.name`, or `obj['2fa']` for a name that is no identifier."""
    return f"{obj}.{name}" if prop_key(name) == name else f"{obj}[{js_string(name)}]"


# ---------------------------------------------------------------------------
# Type mapping
# ---------------------------------------------------------------------------

def ts_type(col: dict[str, Any], enum_names: dict[str, str]) -> str:
    t = col["type"]
    base = "string"
    if col.get("enum"):
        base = enum_names.get(col["enum"], "string")
    elif t in ("integer", "smallint", "bigint", "numeric", "real",
               "double precision", "money"):
        base = "number"
    elif t == "boolean":
        base = "boolean"
    elif t in ("jsonb", "json"):
        base = "Json"
    if col.get("is_array"):
        base = f"{base}[]"
    if col.get("nullable"):
        base = f"{base} | null"
    return base


# ---------------------------------------------------------------------------
# Answers
# ---------------------------------------------------------------------------

class Answers:
    """The human step, applied. Every lookup falls back to the model's own
    proposal, so a missing answers file degrades to 'the machine's best guess'
    rather than to a crash."""

    def __init__(self, data: dict[str, Any] | None):
        self.data = data or {}

    def get(self, qid: str, fallback: Any = None) -> Any:
        v = self.data.get(qid)
        return fallback if v is None else v

    def title(self, table: dict[str, Any]) -> str | None:
        return self.get(f"{table['name']}.title_column",
                        table["screens"].get("title_column"))

    def layout(self, table: dict[str, Any]) -> str:
        return self.get(f"{table['name']}.index_layout",
                        table["screens"].get("index_layout", "table"))

    def list_columns(self, table: dict[str, Any]) -> list[str]:
        proposed = [c["name"] for c in table["columns"]
                    if c["ui"].get("placement", {}).get("list")]
        return list(self.get(f"{table['name']}.list_columns", proposed))

    def groups(self, table: dict[str, Any], default: list) -> list:
        return list(self.get(f"{table['name']}.field_groups", default))

    def readonly(self, table: dict[str, Any]) -> set[str]:
        return set(self.get(f"{table['name']}.readonly_columns", []) or [])

    def in_form(self, table: dict[str, Any], col: dict[str, Any]) -> bool:
        """On the form when the model places it there — or when it carries
        authority and a human released it by removing it from the
        `authority_columns` answer (after protecting it in the database).
        A jsonb column the `.shape` answer calls machine-only is off it."""
        if self.machine_only(table, col):
            return False
        if col["ui"].get("placement", {}).get("form"):
            return True
        if col["ui"].get("authority") and not col["ui"].get("never_display"):
            kept = self.get(f"{table['name']}.authority_columns")
            return kept is not None and col["name"] not in kept
        return False

    def writable(self, table: dict[str, Any]) -> list[str]:
        """The columns a form submits: the Draft type, and the columns the
        policies file grants back to a signed-in user."""
        return [c["name"] for c in table["columns"]
                if self.in_form(table, c) and c["name"] not in self.readonly(table)]

    def empty(self, table: dict[str, Any]) -> dict[str, str]:
        d = {"headline": f"No {table['name'].replace('_', ' ')} yet",
             "body": "", "action": "Add one"}
        got = self.get(f"{table['name']}.empty_state", {})
        if isinstance(got, dict):
            d.update({k: v for k, v in got.items() if isinstance(v, str)})
        return d

    def density(self) -> str:
        return self.get("app.density", "compact")

    def rls(self, table: dict[str, Any] | None = None) -> bool:
        """What the DDL states for this table. The one answer for the whole
        application covers a source that cannot say, and never overrides a
        table's own fact: in a mixed schema it is "no" for every table."""
        stated = table.get("rls") if table else None
        return bool(self.get("app.rls_enabled", True) if stated is None else stated)

    # Per-column answers. Each is read where the output depends on it; the
    # ones the scaffold cannot act on (`.naive_timestamp`, `.storage`'s
    # bucket) are advisory, and SKILL.md says so.

    def column(self, table: dict[str, Any], col: dict[str, Any], key: str,
               fallback: Any = None) -> Any:
        return self.get(f"{table['name']}.{col['name']}.{key}", fallback)

    def money(self, table: dict[str, Any], col: dict[str, Any]) -> dict[str, Any]:
        """The currency and the storage unit of a money column. Without the
        answer the storage is the model's guess and the currency is unknown,
        which the output marks rather than silently writing USD."""
        proposed = dict(col["ui"].get("money") or {})
        got = self.column(table, col, "money")
        answered = isinstance(got, dict)
        if answered:
            proposed.update({k: v for k, v in got.items() if v is not None})
        storage = str(proposed.get("storage", "unknown"))
        if storage.startswith("minor"):
            storage = "minor-units"
        elif storage != "decimal":
            storage = "unknown"
        currency = proposed.get("currency") if answered else None
        return {"currency": str(currency).upper() if currency else None,
                "storage": storage, "answered": answered}

    def options(self, table: dict[str, Any], col: dict[str, Any]) -> list[str]:
        """The closed set: the schema's enum or CHECK, else the `.options`
        answer for a column that only reads as one."""
        if col["ui"].get("options"):
            return [str(o) for o in col["ui"]["options"]]
        got = self.column(table, col, "options", [])
        return [str(o) for o in got] if isinstance(got, list) else []

    def cardinality(self, table: dict[str, Any], col: dict[str, Any]) -> str | None:
        got = self.column(table, col, "cardinality")
        return got if got in ("under-20", "under-5000", "unbounded") else None

    def label_column(self, table: dict[str, Any], col: dict[str, Any]) -> str | None:
        got = self.column(table, col, "label_column")
        return str(got) if isinstance(got, str) and got else None

    def zone(self, table: dict[str, Any], col: dict[str, Any]) -> str:
        got = self.column(table, col, "zone", "viewer")
        return got if got in ("viewer", "record", "fixed-utc") else "viewer"

    def machine_only(self, table: dict[str, Any], col: dict[str, Any]) -> bool:
        """A jsonb column whose `.shape` answer says users do not edit it
        leaves the form and the Draft."""
        got = self.column(table, col, "shape")
        return isinstance(got, dict) and got.get("user_editable") is False \
            and col["ui"].get("control") == "json-editor"

    def default_sort(self, table: dict[str, Any]) -> dict[str, str]:
        proposed = table["screens"].get("default_sort") or {}
        got = self.get(f"{table['name']}.default_sort")
        column = proposed.get("column", "")
        direction = proposed.get("direction", "asc")
        if isinstance(got, dict):
            column = str(got.get("column", column))
            direction = str(got.get("direction", direction))
        elif isinstance(got, str) and got.strip():
            parts = got.split()
            column = parts[0]
            if len(parts) > 1:
                direction = parts[1]
        direction = direction.lower()
        if direction not in ("asc", "desc"):
            direction = "asc"
        return {"column": column, "direction": direction}


# ---------------------------------------------------------------------------
# Shared UI kit — emitted once, identical for every project
# ---------------------------------------------------------------------------

CN_TS = """\
/**
 * Three lines, no dependency. `className` from props goes LAST so a consumer
 * can always add a class without a specificity fight.
 */
export function cn(...parts: Array<string | false | null | undefined>): string {
  return parts.filter(Boolean).join(' ');
}
"""

BUTTON_TSX = """\
import { cn } from '../cn';
import styles from './Button.module.css';

/**
 * React 19: `ref` is an ordinary prop. No forwardRef, no generic dance — the
 * component signature says what it accepts and `React.ComponentProps` already
 * includes `ref` for an intrinsic element.
 */
export type ButtonProps = React.ComponentProps<'button'> & {
  variant?: 'default' | 'primary' | 'ghost' | 'danger';
  size?: 'default' | 'sm';
  /** Shows the busy affordance AND blocks the click. Both, or neither. */
  loading?: boolean;
};

export function Button({
  variant = 'default',
  size = 'default',
  loading = false,
  disabled,
  className,
  children,
  ...rest
}: ButtonProps) {
  return (
    <button
      type="button"
      className={cn(styles.root, className)}
      data-variant={variant === 'default' ? undefined : variant}
      data-size={size === 'default' ? undefined : size}
      data-state={loading ? 'loading' : undefined}
      aria-busy={loading || undefined}
      disabled={disabled || loading}
      {...rest}
    >
      <span className={styles.label}>{children}</span>
      {loading ? <span className={styles.spinner} aria-hidden="true" /> : null}
    </button>
  );
}
"""

BUTTON_CSS = """\
@layer components {
  /* ------------------------------------------------------------------
     1. SOCKETS — this component's Tier-3 API. Every adjustable value,
        declared once on the root, each defaulting to a Tier-2 role.
     ------------------------------------------------------------------ */
  .root {
    --button-pad-inline: var(--pad-inline-md);
    --button-pad-block:  var(--pad-block-md);
    --button-gap:        var(--gap-fused);
    --button-radius:     var(--radius-lg);
    --button-bg:         var(--bg-surface);
    --button-fg:         var(--fg-default);
    --button-border:     var(--border-default);
    --button-motion:     var(--motion-hover);
    /* Interaction paints as a translucent OVERLAY rather than replacing the
       fill, so one hover rule is correct for every variant — including the
       variants that do not exist yet. */
    --button-overlay:    transparent;

  /* ------------------------------------------------------------------
     2. STRUCTURE — what does not change between variants.
     ------------------------------------------------------------------ */
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: var(--button-gap);
    min-block-size: var(--tap-min);
    padding: var(--button-pad-block) var(--button-pad-inline);
    border: var(--stroke-default) solid var(--button-border);
    border-radius: var(--button-radius);
    background-color: var(--button-bg);
    background-image: linear-gradient(var(--button-overlay), var(--button-overlay));
    color: var(--button-fg);
    font: var(--type-ui);
    cursor: pointer;
    transition: background-color var(--button-motion),
                border-color var(--button-motion),
                color var(--button-motion);
  }

  /* ------------------------------------------------------------------
     3. VARIANTS — re-point sockets only. Never add structure here.
     ------------------------------------------------------------------ */
  .root[data-variant="primary"] {
    --button-bg:     var(--bg-accent);
    --button-fg:     var(--fg-on-accent);
    --button-border: transparent;
  }

  .root[data-variant="ghost"] {
    --button-bg:     transparent;
    --button-border: transparent;
  }

  .root[data-variant="danger"] {
    --button-bg:     var(--bg-danger);
    --button-fg:     var(--fg-on-danger);
    --button-border: transparent;
  }

  .root[data-size="sm"] {
    --button-pad-inline: var(--pad-inline-sm);
    --button-pad-block:  var(--pad-block-sm);
    --button-radius:     var(--radius-md);
  }

  /* ------------------------------------------------------------------
     4. STATES — all seven.

        focus-visible is deliberately NOT a ring here. The ring is one
        global decision, made once in reset.css, and a component that
        restates it both duplicates that decision and reads the Tier-1
        --shadow-focus from component code (Law 6). What a component DOES
        owe the focus state is making sure the ring is not clipped or
        overlapped by a neighbour, which is what this rule does.
     ------------------------------------------------------------------ */
  .root:hover:not(:disabled)  { --button-overlay: var(--bg-hover); }
  .root:active:not(:disabled) { --button-overlay: var(--bg-active); }

  .root:focus-visible {
    position: relative;
    z-index: var(--z-raised);
  }

  .root:disabled,
  .root[aria-disabled="true"] {
    --button-bg:     var(--bg-disabled);
    --button-fg:     var(--fg-disabled);
    --button-border: var(--border-subtle);
    cursor: not-allowed;
  }

  .root[data-state="loading"] { cursor: progress; }
  .root[data-state="error"]   { --button-border: var(--border-accent); }

  /* ------------------------------------------------------------------
     5. PARTS — addressed by class, never by element.
     ------------------------------------------------------------------ */
  .label { display: inline-flex; align-items: center; }

  .spinner {
    inline-size: 1em;
    block-size: 1em;
    flex: none;
    border: var(--stroke-thick) solid currentcolor;
    border-block-start-color: transparent;
    border-radius: var(--radius-full);
    /* A continuous spinner must be LINEAR or it visibly stutters once per
       turn, and every Tier-2 --motion-* pair is eased for a one-shot
       transition. There is no role for looping motion. That is a real gap in
       the token contract, so it is named here rather than papered over.
       (The pragma must be its own last line — the auditor attaches it to the
       line after the comment STARTS.) */
    animation: button-spin var(--motion-loop) infinite;
  }

  @media (prefers-reduced-motion: reduce) {
    /* Slowed, not removed: the spinner is the only signal that the button is
       still working, so stopping it reads as a hang. */
    /* design-audit-ignore-next-line: L6 -- reduced-motion fallback keeps the same loop, only slower; no --motion-* pair models "still looping, just calmer" */
    .spinner { animation-duration: var(--dur-slower); }
  }
}

@keyframes button-spin {
  to { rotate: 1turn; }
}
"""

FIELD_TSX = """\
import { cn } from '../cn';
import styles from './Field.module.css';

export type FieldProps = {
  id: string;
  label: string;
  /** Marked visually AND with the `required` attribute, or neither. */
  required?: boolean;
  /** Guidance shown before the user gets it wrong. */
  help?: string;
  /** Set only AFTER first blur, or the form scolds people as they type. */
  error?: string | null;
  disabled?: boolean;
  /**
   * A group of controls (radios, a date range): the label becomes a
   * `<legend>` with the id `${id}-label`, which the group's
   * `aria-labelledby` names, since a `<label htmlFor>` can name only one
   * control.
   */
  group?: boolean;
  children: React.ReactNode;
  className?: string;
};

/** The ids a control puts in its `aria-describedby`: help first, then the
 *  error, so a screen reader hears the guidance before the complaint. */
export function describedBy(id: string, help?: string, error?: string | null): string | undefined {
  const ids = [help ? `${id}-help` : null, error ? `${id}-error` : null].filter(Boolean);
  return ids.length > 0 ? ids.join(' ') : undefined;
}

/**
 * The label / control / help / error quartet, wired so the accessible name
 * and the visible name cannot drift apart.
 *
 * This component owns the structure and the ids: the help is `${id}-help`,
 * the error `${id}-error`. The CONTROL carries `aria-describedby` (from
 * `describedBy`) and `aria-invalid`, because assistive tech reads them on
 * the control and ignores them on a wrapper. The error is not a live region:
 * the form's summary announces a failed submit once and takes focus, and a
 * live region per field would announce every field a second time.
 */
export function Field({
  id,
  label,
  required = false,
  help,
  error,
  disabled = false,
  group = false,
  children,
  className,
}: FieldProps) {
  const helpId = help ? `${id}-help` : undefined;
  const errorId = error ? `${id}-error` : undefined;
  const Root = group ? 'fieldset' : 'div';
  const marker = required ? (
    <span className={styles.required} aria-hidden="true">
      *
    </span>
  ) : null;

  return (
    <Root
      className={cn(styles.root, 'stack', 'stack--tight', className)}
      data-state={error ? 'error' : undefined}
      data-disabled={disabled || undefined}
    >
      {group ? (
        <legend className={cn(styles.label, styles.groupLabel)} id={`${id}-label`}>
          {label}
          {marker}
        </legend>
      ) : (
        <label className={styles.label} htmlFor={id}>
          {label}
          {marker}
        </label>
      )}

      <div className={styles.control}>{children}</div>

      {help ? (
        <p className={styles.help} id={helpId}>
          {help}
        </p>
      ) : null}

      {error ? (
        <p className={styles.error} id={errorId}>
          {error}
        </p>
      ) : null}
    </Root>
  );
}
"""

FIELD_CSS = """\
@layer components {
  .root {
    --field-label-fg:    var(--fg-default);
    --field-help-fg:     var(--fg-muted);
    --field-error-fg:    var(--fg-danger);
    --field-required-fg: var(--fg-danger);
    --field-measure:     var(--measure-narrow);

    max-inline-size: var(--field-measure);
    /* A grouped field is a <fieldset>: drop the browser's box so it lays
       out like the plain one. */
    min-inline-size: 0;
    margin: 0;
    padding: 0;
    border: 0;
  }

  .root[data-disabled] { --field-label-fg: var(--fg-disabled); }

  /* A <legend> is drawn in the fieldset's border by the browser, outside the
     stack's flow. A floated legend gives that up and becomes an ordinary
     flex item, so it takes the gap like a label does. */
  .groupLabel {
    float: left;
    inline-size: 100%;
    padding: 0;
  }

  .label {
    font: var(--type-label);
    color: var(--field-label-fg);
  }

  .required { color: var(--field-required-fg); }

  .control { display: block; }

  .help {
    font: var(--type-label);
    color: var(--field-help-fg);
  }

  .error {
    font: var(--type-label);
    color: var(--field-error-fg);
  }
}
"""

CONTROL_CSS = """\
@layer components {
  /* ------------------------------------------------------------------
     The input surface, shared by every text-shaped control so that a
     text box, a select and a textarea agree on height, inset and border.
     They drift apart the moment each one owns its own numbers.
     ------------------------------------------------------------------ */
  .root {
    --control-pad-inline: var(--pad-inline-sm);
    --control-pad-block:  var(--pad-block-sm);
    --control-radius:     var(--radius-md);
    --control-bg:         var(--bg-surface);
    --control-fg:         var(--fg-default);
    --control-border:     var(--border-default);
    --control-motion:     var(--motion-hover);

    inline-size: 100%;
    min-block-size: var(--tap-min);
    padding: var(--control-pad-block) var(--control-pad-inline);
    border: var(--stroke-default) solid var(--control-border);
    border-radius: var(--control-radius);
    background-color: var(--control-bg);
    color: var(--control-fg);
    font: var(--type-body);
    transition: border-color var(--control-motion),
                background-color var(--control-motion);
  }

  .root::placeholder { color: var(--fg-subtle); }

  .root:hover:not(:disabled) { --control-border: var(--border-strong); }

  /* `:active` on a text input is almost invisible and that is correct — the
     press affordance belongs to things you press. It is written anyway,
     because the state is real on a <select> and on the toggle, and a state
     that is missing from the stylesheet is indistinguishable from a state
     nobody thought about. */
  .root:active:not(:disabled) { --control-bg: var(--bg-active); }

  .root:focus-visible {
    position: relative;
    z-index: var(--z-raised);
    --control-border: var(--border-focus);
  }

  .root:disabled {
    --control-bg: var(--bg-disabled);
    --control-fg: var(--fg-disabled);
    cursor: not-allowed;
  }

  .root[aria-invalid="true"] { --control-border: var(--border-invalid); }

  .root[data-state="loading"] { cursor: progress; }

  /* A textarea must not inherit the tap-target minimum as its whole height. */
  .textarea {
    min-block-size: var(--tap-min);
    block-size: auto;
    resize: vertical;
    field-sizing: content;
  }

  /* Numbers line up only when they are tabular. This is the difference
     between a column of prices you can compare and one you cannot. */
  .numeric {
    font-variant-numeric: tabular-nums;
    text-align: end;
  }

  .mono { font: var(--type-code); }

  /* A checkbox / switch is a control PLUS its label, so the pair is the
     tap target, not the 16px box. */
  .toggle {
    display: flex;
    align-items: center;
    gap: var(--gap-tight);
    min-block-size: var(--tap-min);
  }

  .toggleInput {
    inline-size: var(--space-block);
    block-size: var(--space-block);
    accent-color: var(--bg-accent);
    flex: none;
  }

  .toggleLabel { font: var(--type-body); color: var(--fg-default); }

  .options {
    display: flex;
    flex-direction: column;
    gap: var(--gap-tight);
  }

  .option {
    display: flex;
    align-items: center;
    gap: var(--gap-tight);
    min-block-size: var(--tap-min);
    font: var(--type-body);
    color: var(--fg-default);
  }

  /* A control the scaffold refused to guess at. Loud on purpose — a stub
     that looks finished is how a placeholder ships. */
  .stub {
    display: block;
    padding: var(--pad-well);
    border: var(--stroke-thick) dashed var(--border-strong);
    border-radius: var(--control-radius, var(--radius-md));
    background-color: var(--bg-sunken);
    color: var(--fg-muted);
    font: var(--type-code);
  }
}
"""

CONTROL_TSX = """\
import { cn } from '../cn';
import styles from './Control.module.css';

/**
 * The primitive input surfaces. Every one of them takes `ref` as a plain prop
 * (React 19) and forwards the rest, so a caller can attach whatever form
 * library it likes without this file knowing about it.
 */

export function TextInput({ className, ...rest }: React.ComponentProps<'input'>) {
  return <input className={cn(styles.root, className)} {...rest} />;
}

export function NumberInput({ className, ...rest }: React.ComponentProps<'input'>) {
  return (
    <input
      type="number"
      inputMode="decimal"
      className={cn(styles.root, styles.numeric, className)}
      {...rest}
    />
  );
}

export function TextArea({ className, ...rest }: React.ComponentProps<'textarea'>) {
  return <textarea rows={4} className={cn(styles.root, styles.textarea, className)} {...rest} />;
}

export function Select({ className, children, ...rest }: React.ComponentProps<'select'>) {
  return (
    <select className={cn(styles.root, className)} {...rest}>
      {children}
    </select>
  );
}

export type ToggleProps = React.ComponentProps<'input'> & { label: string };

export function Toggle({ label, id, className, ...rest }: ToggleProps) {
  return (
    <span className={cn(styles.toggle, className)}>
      <input id={id} type="checkbox" className={styles.toggleInput} {...rest} />
      <label className={styles.toggleLabel} htmlFor={id}>
        {label}
      </label>
    </span>
  );
}

export type RadioGroupProps = {
  name: string;
  value: string | null;
  options: readonly string[];
  disabled?: boolean;
  onValueChange?: (next: string) => void;
  /** The id of the group's name: a `<legend>`, from `<Field group>`. */
  labelledBy?: string;
  /** The ids of the help and the error, as `describedBy` builds them. */
  describedBy?: string;
  invalid?: boolean;
  /** The group says so (`aria-required`) and so does each radio. */
  required?: boolean;
};

export function RadioGroup({
  name,
  value,
  options,
  disabled,
  onValueChange,
  labelledBy,
  describedBy,
  invalid,
  required,
}: RadioGroupProps) {
  return (
    <div
      className={styles.options}
      role="radiogroup"
      aria-labelledby={labelledBy}
      aria-describedby={describedBy}
      aria-invalid={invalid || undefined}
      aria-required={required || undefined}
    >
      {options.map((option) => (
        <label className={styles.option} key={option}>
          <input
            type="radio"
            name={name}
            value={option}
            checked={value === option}
            disabled={disabled}
            required={required}
            className={styles.toggleInput}
            onChange={() => onValueChange?.(option)}
          />
          {option}
        </label>
      ))}
    </div>
  );
}

/**
 * A control this scaffold deliberately did not guess at. It renders as an
 * obvious placeholder so it cannot be mistaken for finished work.
 */
export function ControlStub({ control, reason }: { control: string; reason: string }) {
  return (
    <span className={styles.stub} data-state="error">
      TODO({control}): {reason}
    </span>
  );
}
"""

BADGE_TSX = """\
import { cn } from '../cn';
import styles from './Badge.module.css';

export type BadgeProps = React.ComponentProps<'span'> & {
  tone?: 'neutral' | 'accent' | 'success' | 'warning' | 'danger';
};

/**
 * A status pill. Tone is a PROP, not a lookup from the value — the mapping
 * from `status` to tone is product knowledge and belongs at the call site,
 * where someone can see it and argue with it.
 */
export function Badge({ tone = 'neutral', className, children, ...rest }: BadgeProps) {
  return (
    <span className={cn(styles.root, className)} data-tone={tone === 'neutral' ? undefined : tone} {...rest}>
      {children}
    </span>
  );
}
"""

BADGE_CSS = """\
@layer components {
  .root {
    --badge-pad-inline: var(--pad-inline-xs);
    --badge-pad-block:  var(--pad-block-xs);
    --badge-radius:     var(--radius-full);
    --badge-bg:         var(--bg-sunken);
    --badge-fg:         var(--fg-muted);

    display: inline-flex;
    align-items: center;
    gap: var(--gap-fused);
    padding: var(--badge-pad-block) var(--badge-pad-inline);
    border-radius: var(--badge-radius);
    background-color: var(--badge-bg);
    color: var(--badge-fg);
    font: var(--type-label);
    white-space: nowrap;
  }

  /* Tone re-points sockets. The text colour is the -fg role, never the fill,
     because the fill is tuned for a large area and fails contrast at 12px. */
  .root[data-tone="accent"]  { --badge-fg: var(--fg-accent); }
  .root[data-tone="success"] { --badge-fg: var(--fg-success); }
  .root[data-tone="warning"] { --badge-fg: var(--fg-warning); }
  .root[data-tone="danger"]  { --badge-fg: var(--fg-danger); }
}
"""

SKELETON_TSX = """\
import { cn } from '../cn';
import styles from './Skeleton.module.css';

export type SkeletonProps = React.ComponentProps<'span'> & {
  /** Width as a fraction of the container, 0-1. Passed in as a custom
   *  property: the one legal inline style (Law 4). */
  width?: number;
  lines?: number;
};

/**
 * A loading placeholder sized to the content it replaces. If the skeleton and
 * the real thing are different heights, the page jumps when data arrives and
 * the thing the user was about to click moves. That jump is the bug this
 * component exists to prevent, so always pass the real line count.
 */
export function Skeleton({ width = 1, lines = 1, className, ...rest }: SkeletonProps) {
  return (
    <span
      className={cn(styles.root, className)}
      style={{ '--skeleton-width': String(width), '--skeleton-lines': String(lines) } as React.CSSProperties}
      aria-hidden="true"
      {...rest}
    />
  );
}
"""

SKELETON_CSS = """\
@layer components {
  .root {
    --skeleton-width:  1;
    --skeleton-lines:  1;
    --skeleton-radius: var(--radius-sm);
    --skeleton-bg:     var(--bg-sunken);
    /* Derived sizes are geometry, so they live in sockets the sizes read.
       `1lh` is this element's OWN line box, so the placeholder is exactly as
       tall as the text it stands in for. Deriving it from a leading token
       instead would read Tier 1 from component code (Law 6) AND would drift
       the moment the type role changed. */
    --skeleton-inline: calc(100% * var(--skeleton-width));
    --skeleton-block:  calc(1lh * var(--skeleton-lines));

    display: block;
    inline-size: var(--skeleton-inline);
    font: var(--type-body);
    block-size: var(--skeleton-block);
    border-radius: var(--skeleton-radius);
    background-color: var(--skeleton-bg);
  }

  /* Deliberately not animated. A shimmer is decoration: it says nothing a
     static block does not, it is the first thing prefers-reduced-motion
     removes, and a loop that never resolves is the least useful place to
     spend the motion budget. */
}
"""

STATE_BLOCK_TSX = """\
import { cn } from '../cn';
import styles from './StateBlock.module.css';

export type StateBlockProps = {
  /** Drives the tone and the icon slot. These are DIFFERENT screens, not one
   *  screen with different words — see screen-patterns.md section 12. */
  kind: 'first-run' | 'filtered' | 'error' | 'forbidden' | 'stale';
  headline: string;
  body?: string;
  /** The single action this state offers. Two actions on an empty state is
   *  two people disagreeing about what the user should do next. */
  action?: React.ReactNode;
  className?: string;
};

export function StateBlock({ kind, headline, body, action, className }: StateBlockProps) {
  return (
    <div
      className={cn(styles.root, 'stack', 'stack--related', className)}
      data-kind={kind}
      role={kind === 'error' ? 'alert' : undefined}
    >
      <h2 className={styles.headline}>{headline}</h2>
      {body ? <p className={styles.body}>{body}</p> : null}
      {action ? <div className={styles.action}>{action}</div> : null}
    </div>
  );
}
"""

STATE_BLOCK_CSS = """\
@layer components {
  .root {
    --state-block-inset:  var(--pad-card-lg);
    --state-block-radius: var(--radius-xl);
    --state-block-bg:     var(--bg-surface);
    --state-block-border: var(--border-subtle);
    --state-block-fg:     var(--fg-muted);
    --state-block-measure: var(--measure-narrow);

    align-items: center;
    padding: var(--state-block-inset);
    border: var(--stroke-default) dashed var(--state-block-border);
    border-radius: var(--state-block-radius);
    background-color: var(--state-block-bg);
    color: var(--state-block-fg);
    text-align: center;
  }

  /* An error is not a decorative empty state. It gets a solid border and the
     danger role so it cannot be mistaken for "there is nothing here". */
  .root[data-kind="error"] {
    --state-block-border: var(--border-accent);
    border-style: solid;
  }

  .root[data-kind="forbidden"] { --state-block-border: var(--border-strong); }

  .root[data-kind="stale"] {
    --state-block-bg: var(--bg-sunken);
    --state-block-border: var(--border-default);
  }

  .headline {
    font: var(--type-h4);
    color: var(--fg-strong);
    max-inline-size: var(--state-block-measure);
  }

  .body {
    font: var(--type-body);
    max-inline-size: var(--state-block-measure);
  }

  .action { display: flex; gap: var(--gap-tight); }
}
"""

DATA_TABLE_CSS = """\
@layer components {
  /* ------------------------------------------------------------------
     A data table on a phone is the hard problem. This scaffold takes
     option 1 of the three in screen-patterns.md section 4: keep the table,
     scroll it honestly, and pin the identifying column so a scrolled row
     never becomes anonymous. Options 2 (collapse to cards) and 3 (a
     priority-ordered subset) are both correct in other situations and
     both need a human to say which columns matter.
     ------------------------------------------------------------------ */
  .scroller {
    --table-scroller-radius: var(--radius-lg);
    --table-scroller-border: var(--border-subtle);

    overflow-x: auto;
    overscroll-behavior-inline: contain;
    border: var(--stroke-default) solid var(--table-scroller-border);
    border-radius: var(--table-scroller-radius);
    background-color: var(--bg-surface);
  }

  /* A scroll container that cannot take focus traps keyboard users, so the
     markup carries tabindex="0" and an accessible name. This is the focus
     treatment that becomes mandatory the moment it does. */
  .scroller:focus-visible {
    position: relative;
    z-index: var(--z-raised);
  }

  .root {
    --table-cell-pad-inline: var(--pad-inline-md);
    --table-cell-pad-block:  var(--pad-block-sm);
    --table-rule:            var(--border-subtle);

    inline-size: 100%;
    border-collapse: collapse;
    font: var(--type-ui);
    color: var(--fg-default);
  }

  .head {
    position: sticky;
    inset-block-start: 0;
    z-index: var(--z-raised);
    background-color: var(--bg-surface);
  }

  .th {
    padding: var(--table-cell-pad-block) var(--table-cell-pad-inline);
    border-block-end: var(--stroke-default) solid var(--table-rule);
    color: var(--fg-muted);
    font: var(--type-label);
    text-align: start;
    white-space: nowrap;
  }

  .th[aria-sort] { color: var(--fg-default); }

  .td {
    padding: var(--table-cell-pad-block) var(--table-cell-pad-inline);
    border-block-end: var(--stroke-default) solid var(--table-rule);
    vertical-align: middle;
  }

  /* Numbers are comparable only when they are right-aligned and tabular. */
  .numeric {
    font-variant-numeric: tabular-nums;
    text-align: end;
  }

  .muted { color: var(--fg-muted); }

  .truncate {
    max-inline-size: var(--measure-narrow);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  /* The identifying column survives horizontal scroll. Without this, a row
     scrolled to its fifth column belongs to nobody. */
  .sticky {
    position: sticky;
    inset-inline-start: 0;
    background-color: var(--bg-surface);
  }

  .row { transition: background-color var(--motion-hover); }

  .row:hover  { background-color: var(--bg-hover); }
  .row:focus-within {
    position: relative;
    z-index: var(--z-raised);
    background-color: var(--bg-hover);
  }
  .row[aria-selected="true"] { background-color: var(--bg-selected); }
  .row[data-state="loading"] { color: var(--fg-muted); cursor: progress; }
  .row[data-state="error"]   { background-color: var(--bg-sunken); }
  .row[data-disabled]        { color: var(--fg-disabled); }

  .link {
    color: var(--fg-link);
    text-decoration-line: underline;
    text-decoration-thickness: var(--stroke-hairline);
  }

  .link:hover { color: var(--fg-accent); }
}
"""

CARD_GRID_CSS = """\
@layer components {
  .card {
    --record-card-inset:  var(--pad-card);
    --record-card-radius: var(--radius-xl);
    --record-card-bg:     var(--bg-surface);
    --record-card-border: var(--border-subtle);
    --record-card-shadow: var(--elevation-flat);
    --record-card-motion: var(--motion-hover);

    display: flex;
    flex-direction: column;
    gap: var(--gap-related);
    padding: var(--record-card-inset);
    border: var(--stroke-default) solid var(--record-card-border);
    border-radius: var(--record-card-radius);
    background-color: var(--record-card-bg);
    box-shadow: var(--record-card-shadow);
    transition: box-shadow var(--record-card-motion),
                border-color var(--record-card-motion);
  }

  .card:hover { --record-card-shadow: var(--elevation-card); }

  .card:focus-within {
    position: relative;
    z-index: var(--z-raised);
    --record-card-border: var(--border-focus);
  }

  .card[aria-selected="true"] { --record-card-bg: var(--bg-selected); }
  .card[data-state="loading"] { --record-card-shadow: var(--elevation-flat); }
  .card[data-state="error"]   { --record-card-border: var(--border-accent); }
  .card[data-disabled]        { --record-card-bg: var(--bg-disabled); }

  .cardMedia { border-radius: var(--radius-lg); overflow: hidden; }

  .cardTitle { font: var(--type-h4); color: var(--fg-strong); }

  .cardMeta { font: var(--type-label); color: var(--fg-muted); }

  /* The title is the link, so the whole card is not one enormous tab stop
     with an unreadable accessible name. */
  .cardLink {
    color: inherit;
    text-decoration-line: none;
  }

  .cardLink:hover { text-decoration-line: underline; }
}
"""

INDEX_TS_KIT = """\
export { Button } from './Button/Button';
export type { ButtonProps } from './Button/Button';
export { Field, describedBy } from './Field/Field';
export type { FieldProps } from './Field/Field';
export {
  TextInput,
  NumberInput,
  TextArea,
  Select,
  Toggle,
  RadioGroup,
  ControlStub,
} from './Control/Control';
export { Badge } from './Badge/Badge';
export { Skeleton } from './Skeleton/Skeleton';
export { StateBlock } from './StateBlock/StateBlock';
export type { StateBlockProps } from './StateBlock/StateBlock';
export { cn } from './cn';
"""


# ---------------------------------------------------------------------------
# Per-entity emitters
# ---------------------------------------------------------------------------

def emit_types(table: dict[str, Any], model: dict[str, Any],
               ans: Answers) -> str:
    name = table["name"]
    Entity = pascal(singular(name))
    enum_names: dict[str, str] = {}
    lines: list[str] = []
    used_enums = {c["enum"] for c in table["columns"] if c.get("enum")}
    for enum in sorted(e for e in used_enums if e):
        values = model["enums"].get(enum, [])
        tname = pascal(enum)
        enum_names[enum] = tname
        if values:
            union = " | ".join(f"'{v}'" for v in values)
            lines.append(f"export type {tname} = {union};")
        else:
            lines.append(f"/** TODO(model): `{enum}` had no values in the "
                         f"schema dump. */\nexport type {tname} = string;")
    if any(c["type"] in ("jsonb", "json") for c in table["columns"]):
        lines.append(
            "export type Json =\n"
            "  | string\n  | number\n  | boolean\n  | null\n"
            "  | { [key: string]: Json | undefined }\n  | Json[];")

    body = [f"export interface {Entity} {{"]
    for c in table["columns"]:
        if c["ui"].get("never_display"):
            body.append(f"  /* {c['name']}: write-only — deliberately absent "
                        f"from the read type so it cannot be rendered. */")
            continue
        body.append(f"  {prop_key(c['name'])}: {ts_type(c, enum_names)};")
    body.append("}")

    writable = ans.writable(table)
    draft = (f"/** What a form submits: the writable columns only. Omitting\n"
             f" *  the rest is what stops a form quietly PATCHing a column\n"
             f" *  the database owns. */\n"
             f"export type {Entity}Draft = Pick<\n  {Entity},\n"
             + "".join(f"  | {js_string(w)}\n" for w in writable) + ">;")

    state = Template("""
/**
 * The list's state, as a union rather than four booleans.
 *
 * `forbidden` is separate from an empty `ready` on purpose. Under RLS a row
 * the user may not see and a row that does not exist produce the SAME
 * response, so if the UI does not distinguish them deliberately it will tell
 * someone their data is gone. See supabase-integration.md section 2.
 */
export type $Entity${List}State =
  | { status: 'loading' }
  | { status: 'error'; error: Error; retry: () => void }
  | { status: 'forbidden' }
  | {
      status: 'ready';
      rows: $Entity[];
      /** True when a filter or search is active: drives which empty state. */
      filtered: boolean;
      /** True while revalidating behind already-rendered rows. */
      stale?: boolean;
    };
""").safe_substitute(Entity=Entity, List="List")

    return ("\n".join(lines) + ("\n\n" if lines else "")
            + "\n".join(body) + "\n\n" + draft + "\n" + state)


def field_spec(col: dict[str, Any], table: dict[str, Any], model: dict[str, Any],
               ans: Answers) -> dict[str, Any]:
    ui = col["ui"]
    spec: dict[str, Any] = {
        "name": col["name"],
        "label": ui.get("label") or col["name"],
        "control": ui["control"],
        "required": any(r["rule"] == "required" for r in ui.get("validation", [])),
    }
    for r in ui.get("validation", []):
        if r["rule"] in ("maxLength", "minLength", "min", "max",
                         "exclusiveMin", "exclusiveMax", "pattern"):
            spec[r["rule"]] = r["value"]
    options = ans.options(table, col)
    if options:
        spec["options"] = options
    if col.get("foreign_key"):
        # The `.cardinality` answer is the one input that decides between a
        # select, a combobox and a picker; the schema can never contain it.
        chosen = ans.cardinality(table, col)
        if chosen:
            spec["control"] = {"under-20": "select", "under-5000": "combobox",
                               "unbounded": "record-picker"}[chosen]
        label = ans.label_column(table, col)
        if label:
            spec["labelColumn"] = label
    if ui.get("control") == "currency-input":
        money = ans.money(table, col)
        spec["money"] = {"currency": money["currency"],
                         "storage": money["storage"]}
    if col["name"] in ans.readonly(table):
        spec["control"] = "readonly-text"
        spec["readOnly"] = True
    if ui.get("confidence") != "high":
        spec["review"] = ui.get("signal", "")
    return spec


def emit_fields(table: dict[str, Any], model: dict[str, Any],
                ans: Answers) -> str:
    name = table["name"]
    Entity = pascal(singular(name))
    specs = [field_spec(c, table, model, ans) for c in table["columns"]
             if ans.in_form(table, c)]

    default_groups = [{"legend": "Details",
                       "fields": [s["name"] for s in specs]}]
    groups = ans.groups(table, table["screens"].get("field_groups")
                        or default_groups)

    out: list[str] = [
        "/**",
        f" * Field metadata for {name}, derived from the schema and from the",
        " * answers to the interview. One source for the form, the list header",
        " * and the validation, so the three cannot drift apart.",
        " *",
        " * Every rule here MIRRORS a database constraint. A rule with no",
        " * constraint behind it is a second source of truth, and the two will",
        " * disagree — usually at 3am, in a background job, for one customer.",
        " */",
        f"import type {{ {Entity} }} from './{camel(name)}.types';",
        "",
        "export type FieldSpec = {",
        f"  name: keyof {Entity} & string;",
        "  label: string;",
        "  control: string;",
        "  required: boolean;",
        "  readOnly?: boolean;",
        "  options?: readonly string[];",
        "  maxLength?: number;",
        "  minLength?: number;",
        "  min?: number;",
        "  max?: number;",
        "  /** `CHECK (col > n)` / `< n`: the bound itself is out. HTML's `min`",
        "   *  is inclusive, so the control cannot say it; the schemas do. */",
        "  exclusiveMin?: number;",
        "  exclusiveMax?: number;",
        "  pattern?: string;",
        "  help?: string;",
        "  /** A money column: the `.money` answer. `currency` is null until it",
        "   *  is answered; `storage` says what the integer or decimal means. */",
        "  money?: { currency: string | null; storage: 'minor-units' | 'decimal' | 'unknown' };",
        "  /** A reference: the parent column a picker shows (`.label_column`). */",
        "  labelColumn?: string;",
        "  /** Present when the mapper was not certain. Read it, then delete it. */",
        "  review?: string;",
        "};",
        "",
        f"export const {camel(name)}Fields = [",
    ]
    for s in specs:
        entries = []
        for key in ("name", "label", "control", "required", "readOnly",
                    "options", "maxLength", "minLength", "min", "max",
                    "exclusiveMin", "exclusiveMax", "pattern", "money",
                    "labelColumn", "review"):
            if key not in s:
                continue
            entries.append(f"    {key}: {json.dumps(s[key])},")
        out.append("  {")
        out.extend(entries)
        out.append("  },")
    out.append("] as const satisfies readonly FieldSpec[];")
    out.append("")
    out.append("/** Form sections, in order. Grouping is the difference between")
    out.append(" *  a form and a questionnaire. */")
    out.append(f"export const {camel(name)}Groups = {json.dumps(groups, indent=2)} as const;")
    out.append("")
    list_cols = ans.list_columns(table)
    out.append("/** The scanning surface. Six is the working cap — past that")
    out.append(" *  people stop scanning and start reading. */")
    out.append(f"export const {camel(name)}ListColumns = "
               f"{json.dumps(list_cols)} as const;")
    out.append("")
    sort = ans.default_sort(table)
    out.append("/** The designed order (the `.default_sort` answer). The list takes")
    out.append(" *  its rows as props, so the query that fetches them applies this:")
    out.append(f" *  `.order('{sort['column']}', {{ ascending: "
               f"{'true' if sort['direction'] == 'asc' else 'false'} }})`. */")
    out.append(f"export const {camel(name)}DefaultSort = "
               f"{json.dumps(sort)} as const;")
    return "\n".join(out) + "\n"


def cell_render(col: dict[str, Any], row: str = "row",
                table: dict[str, Any] | None = None,
                ans: Answers | None = None) -> dict[str, Any]:
    """How one column renders in a list cell or a detail value.

    Returns the JSX, whether it is an element or an expression (they are
    wrapped differently), the modifier class, and which formatter it needs so
    the emitter can import exactly those and no more. The money, zone and
    label answers are read here, since this is where they change the output.
    """
    ui = col["ui"]
    ctrl = ui["control"]
    ans = ans or Answers(None)
    table = table or {"name": "", "screens": {}}
    acc = (f"{row}.{col['name']}"
           if re.fullmatch(r"[A-Za-z_$][\w$]*", col["name"])
           else f"{row}[{json.dumps(col['name'])}]")

    def out(jsx: str, *, element: bool = False, cls: str = "",
            helper: str | None = None) -> dict[str, Any]:
        return {"jsx": jsx, "element": element, "class": cls, "helper": helper, "acc": acc}

    if ctrl == "currency-input":
        money = ans.money(table, col)
        qid = f"{table['name']}.{col['name']}.money"
        currency = (json.dumps(money["currency"]) if money["currency"]
                    else f"'USD' /* TODO(answers): the currency, from `{qid}` */")
        if money["storage"] == "minor-units":
            # The scale is the currency's (JPY 1, KWD 1000), never a
            # hard-coded 100: formatMinorUnits divides by the right one. A
            # null stays null rather than becoming a type error.
            return out(f"formatMinorUnits({acc}, {currency})", cls="numeric",
                       helper="formatMinorUnits")
        amount = acc
        if money["storage"] == "unknown":
            amount = (f"{acc} /* TODO(money): minor units or a decimal? "
                      f"answer `{qid}` */")
        return out(f"formatMoney({amount}, {currency})", cls="numeric",
                   helper="formatMoney")
    if ctrl in ("number-input", "stepper", "percent-input"):
        return out(acc, cls="numeric")
    if ctrl in ("switch", "checkbox"):
        return out(f"{acc} ? 'Yes' : 'No'")
    if ctrl in ("select", "radio-group") and ans.options(table, col):
        return out(f"<Badge tone={{toneFor({acc})}}>{{{acc}}}</Badge>",
                   element=True, helper="toneFor")
    if ctrl in ("readonly-timestamp", "datetime-picker", "time-picker"):
        zone = ""
        if (ui.get("temporal") or {}).get("granularity") == "instant":
            answered = ans.zone(table, col)
            if answered == "fixed-utc":
                zone = ", 'UTC'"
            elif answered == "record":
                zone = (f", undefined /* TODO(zone): this record's own zone "
                        f"column, per `{table['name']}.{col['name']}.zone` */")
        return out(f"formatInstant({acc}{zone})", cls="muted",
                   helper="formatInstant")
    if ctrl == "date-picker":
        return out(f"formatDate({acc})", cls="muted", helper="formatDate")
    if ctrl == "image-upload":
        # A thumbnail needs the bucket and the signed-URL policy, which the
        # interview has to supply. Until it does, say so rather than render a
        # broken <img>.
        return out(f"{acc} === null ? '\u2014' : 'TODO(image): render the "
                   f"thumbnail once the bucket is known'", cls="muted")
    if col.get("foreign_key"):
        # The id is a placeholder for the parent's label, which needs a join
        # the scaffold has no data layer to perform. The `.label_column`
        # answer names the column that join selects.
        label = ans.label_column(table, col)
        parent = col["foreign_key"].get("table", "")
        note = (f" /* TODO(join): show `{parent}.{label}` */" if label
                else f" /* TODO(join): show the {parent} label; answer "
                     f"`{table['name']}.{col['name']}.label_column` */")
        return out(f"{acc}{note}", cls="truncate")
    if ctrl == "json-editor":                    # `String()` of an object is `[object Object]`
        return out(f"JSON.stringify({acc} ?? null)", cls="truncate")
    if ctrl in ("textarea", "rich-text"):
        return out(f"String({acc} ?? '')", cls="truncate")
    if ctrl == "tag-input":
        return out(f"({acc} ?? []).join(', ')", cls="truncate")
    return out(acc)


def cell_expr(cell: dict[str, Any]) -> str:
    """JSX elements interpolate bare; everything else needs braces."""
    return cell["jsx"] if cell["element"] else f"{{{cell['jsx']}}}"


FORMAT_TS = """\
/**
 * Display formatting. Deliberately tiny and deliberately explicit.
 *
 * MONEY. The currency is a parameter because it is a per-column answer from
 * the interview, not a global constant — the day this app sells in two
 * currencies, a hardcoded USD is 40 files of work. Integer minor units go
 * through `formatMinorUnits`, which divides by the currency's own scale
 * (100 for USD and EUR, 1 for JPY, 1000 for KWD) — `Intl` knows the
 * exponent, and a hard-coded `/ 100` is silently wrong for the rest of the
 * world. A decimal amount goes through `formatMoney` as it is.
 *
 * INSTANTS. `timestamptz` is a point in time; rendering it needs a zone, and
 * the browser's own zone is only the right answer when the interview said
 * `viewer`. Where it said `record`, pass that record's zone in.
 */

const MONEY_FORMATS = new Map<string, Intl.NumberFormat>();

function moneyFormat(currency: string): Intl.NumberFormat {
  let format = MONEY_FORMATS.get(currency);
  if (!format) {
    format = new Intl.NumberFormat(undefined, { style: 'currency', currency });
    MONEY_FORMATS.set(currency, format);
  }
  return format;
}

/** 10 to the currency's minor-unit exponent: 100 for USD, 1 for JPY, 1000 for KWD. */
export function minorUnitScale(currency: string): number {
  const digits = moneyFormat(currency).resolvedOptions().maximumFractionDigits ?? 2;
  return 10 ** digits;
}

/** A decimal amount (`numeric(p,2)`), already in major units. */
export function formatMoney(amount: number | string | null, currency: string): string {
  if (amount === null || amount === '') return '—';
  const value = typeof amount === 'string' ? Number(amount) : amount;
  if (!Number.isFinite(value)) return String(amount);
  return moneyFormat(currency).format(value);
}

/** An integer in minor units (`price_cents`), divided by the currency's scale. */
export function formatMinorUnits(minor: number | null, currency: string): string {
  if (minor === null) return '—';
  return moneyFormat(currency).format(minor / minorUnitScale(currency));
}

const INSTANT = new Intl.DateTimeFormat(undefined, {
  dateStyle: 'medium',
  timeStyle: 'short',
});

const DATE_ONLY = new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' });

export function formatInstant(value: string | null, timeZone?: string): string {
  if (!value) return '—';
  const formatter = timeZone
    ? new Intl.DateTimeFormat(undefined, {
        dateStyle: 'medium',
        timeStyle: 'short',
        timeZone,
      })
    : INSTANT;
  return formatter.format(new Date(value));
}

/**
 * A `date` column is a calendar day with no time and no zone. Parsing it as
 * an instant makes it midnight UTC, which renders as the PREVIOUS day for
 * everyone west of Greenwich. Splitting the string is not a shortcut here; it
 * is the correct handling.
 */
export function formatDate(value: string | null): string {
  if (!value) return '—';
  const parts = value.slice(0, 10).split('-');
  const year = Number(parts[0]);
  const month = Number(parts[1]);
  const day = Number(parts[2]);
  if (!Number.isFinite(year) || !Number.isFinite(month) || !Number.isFinite(day)) {
    return value;
  }
  return DATE_ONLY.format(new Date(year, month - 1, day));
}

/** TODO(product): map each status value to a tone. The mapping is product
 *  knowledge — "cancelled is danger" is a decision, not a derivation. */
export function toneFor(_value: string | null): 'neutral' | 'accent' | 'success' | 'warning' | 'danger' {
  return 'neutral';
}
"""


def _helper_imports(cells: list[dict[str, Any]], extra: set[str]) -> str:
    """Import exactly the formatters this file uses. An unused import is a
    compile error under `noUnusedLocals`, which is the setting every project
    that cares turns on."""
    used = {c["helper"] for c in cells if c.get("helper")} | extra
    if not used:
        return ""
    names = ", ".join(sorted(used))
    return f"import {{ {names} }} from '../../lib/format';\n"


def emit_list(table: dict[str, Any], model: dict[str, Any], ans: Answers) -> str:
    name = table["name"]
    Entity = pascal(singular(name))
    Entities = pascal(name)
    title = ans.title(table)
    layout = ans.layout(table)
    pk = table["primary_key"][0] if table["primary_key"] else "id"
    human = name.replace("_", " ")
    Title = human[:1].upper() + human[1:]

    listed = ans.list_columns(table)
    cols = [c for c in table["columns"] if c["name"] in listed]
    if not cols:
        cols = table["columns"][:1]
    cells = {c["name"]: cell_render(c, "row", table, ans) for c in cols}

    needs_badge = any(cells[c["name"]]["jsx"].startswith("<Badge") for c in cols)
    href = f"'/{name}/' + String(row.{pk})"

    if layout == "table":
        head = "\n".join(
            "              <th className={%s} scope=\"col\">\n"
            "                %s\n"
            "              </th>" % (
                "cn(styles.th, styles.sticky)" if c["name"] == title
                else "styles.th",
                c["ui"].get("label", c["name"]))
            for c in cols)
        body = []
        for c in cols:
            cell = cells[c["name"]]
            classes = ["styles.td"]
            if cell["class"]:
                classes.append(f"styles.{cell['class']}")
            if c["name"] == title:
                classes.append("styles.sticky")
            cls = classes[0] if len(classes) == 1 else f"cn({', '.join(classes)})"
            inner = (f"<a className={{styles.link}} href={{{href}}}>"
                     f"{cell_expr(cell)}</a>"
                     if c["name"] == title else cell_expr(cell))
            body.append(f"                  <td className={{{cls}}}>{inner}</td>")
        rows_markup = Template("""      <div
        className={styles.scroller}
        tabIndex={0}
        role="region"
        aria-label="$Title, scrollable table"
      >
        <table className={styles.root}>
          <thead className={styles.head}>
            <tr>
$head
            </tr>
          </thead>
          <tbody>
            {state.rows.map((row: $Entity) => (
              <tr className={styles.row} key={String(row.$pk)}>
$body
              </tr>
            ))}
          </tbody>
        </table>
      </div>""").safe_substitute(Title=Title, head=head,
                                 body="\n".join(body), Entity=Entity, pk=pk)
    else:
        grid_class = "grid grid--min-lg" if layout == "feed" else "grid grid--min-sm"
        meta = []
        for c in cols:
            if c["name"] == title:
                continue
            cell = cells[c["name"]]
            meta.append(
                f"                <div>\n"
                f"                  <dt className={{styles.cardMeta}}>"
                f"{c['ui'].get('label', c['name'])}</dt>\n"
                f"                  <dd>{cell_expr(cell)}</dd>\n"
                f"                </div>")
        rows_markup = Template("""      <ul className="$grid_class">
        {state.rows.map((row: $Entity) => (
          <li key={String(row.$pk)}>
            <article className={styles.card}>
              <h2 className={styles.cardTitle}>
                <a className={styles.cardLink} href={$href}>
                  $title_expr
                </a>
              </h2>
              <dl className="stack stack--fused">
$meta
              </dl>
            </article>
          </li>
        ))}
      </ul>""").safe_substitute(
            grid_class=grid_class, Entity=Entity, pk=pk, href=href,
            meta="\n".join(meta),
            title_expr=cell_expr(cells[title]) if title in cells
            else "{String(row." + pk + ")}")

    imports = _helper_imports(list(cells.values()), set())
    kit = ["Button"]
    if needs_badge:
        kit.insert(0, "Badge")
    if layout == "table":
        kit.insert(0, "cn")

    return Template("""\
import { $kit } from '../../ui';
${imports}import type { $Entity, ${Entity}ListState } from './$camel.types';
import {
  ${Entities}Empty,
  ${Entities}Error,
  ${Entities}FilteredEmpty,
  ${Entities}Forbidden,
  ${Entities}Loading,
} from './${Entities}States';
import styles from './${Entities}List.module.css';

export type ${Entities}ListProps = {
  state: ${Entity}ListState;
  /** The single primary action offered by the first-run empty state. */
  onCreate?: () => void;
  /** Clears whatever produced the filtered-empty state. */
  onClearFilters?: () => void;
};

/**
 * $human, as a $layout.
 *
 * $layout_why
 *
 * This component takes its rows as a prop and knows nothing about fetching.
 * That is deliberate: cache keys, realtime and optimistic writes are product
 * decisions, and a scaffold has no business guessing at them.
 */
export function ${Entities}List({ state, onCreate, onClearFilters }: ${Entities}ListProps) {
  if (state.status === 'loading') return <${Entities}Loading />;
  if (state.status === 'error') return <${Entities}Error error={state.error} onRetry={state.retry} />;
  if (state.status === 'forbidden') return <${Entities}Forbidden />;

  // Two different screens, not one screen with two strings. "Nothing here yet,
  // make the first one" and "your filter matched nothing, clear it" ask the
  // user to do opposite things.
  if (state.rows.length === 0) {
    return state.filtered ? (
      <${Entities}FilteredEmpty onClearFilters={onClearFilters} />
    ) : (
      <${Entities}Empty onCreate={onCreate} />
    );
  }

  return (
    <section className="stack stack--separate" aria-labelledby="$camel-heading">
      <header className="cluster cluster--between">
        <h1 className={styles.heading} id="$camel-heading">
          $Title
        </h1>
        <Button variant="primary" onClick={onCreate}>
          New $lower_entity
        </Button>
      </header>

      {state.stale ? (
        <p className={styles.stale} role="status">
          Showing the last known data while this refreshes.
        </p>
      ) : null}

$rows_markup
    </section>
  );
}
""").safe_substitute(
        kit=", ".join(kit), imports=imports, Entity=Entity, Entities=Entities,
        camel=camel(name), human=human, layout=layout, Title=Title,
        layout_why=table["screens"].get("index_layout_signal", ""),
        lower_entity=singular(human), rows_markup=rows_markup)


LIST_CSS = """\
@layer components {
  .heading {
    font: var(--type-h2);
    color: var(--fg-strong);
  }

  .stale {
    font: var(--type-label);
    color: var(--fg-warning);
  }
}
"""


def emit_detail(table: dict[str, Any], model: dict[str, Any],
                ans: Answers) -> str:
    name = table["name"]
    Entity = pascal(singular(name))
    Entities = pascal(name)
    title = ans.title(table)
    pk_detail = table["primary_key"][0] if table["primary_key"] else "id"
    rows, cells = [], []
    for c in table["columns"]:
        if not c["ui"].get("placement", {}).get("detail"):
            continue
        if c["name"] == title:
            continue
        cell = cell_render(c, "record", table, ans)
        cells.append(cell)
        rows.append(
            f"          <div className={{styles.pair}}>\n"
            f"            <dt className={{styles.term}}>"
            f"{c['ui'].get('label', c['name'])}</dt>\n"
            f"            <dd className={{styles.value}}>{cell_expr(cell)}</dd>\n"
            f"          </div>")
    related = []
    for r in table.get("relationships", []):
        if r["kind"] in ("one-to-many", "many-to-many"):
            related.append(
                f"        {{/* TODO({r['control']}): {r['kind']} to "
                f"`{r['to']}`"
                + (f" via `{r['via']}`" if r.get("via") else "") + ". "
                f"{r.get('signal', '')} */}}")

    placeholder_note = ""
    if table["screens"].get("title_is_placeholder"):
        placeholder_note = (
            "\n * TODO(title): nothing in this table looks like a title, so the\n"
            " * primary key is standing in. A uuid in an h1 is not a heading.\n"
            " * Answer the `.title_column` question and come back.")

    return Template("""\
import { $kit } from '../../ui';
${imports}import type { $Entity } from './$camel.types';
import { ${Entities}Error, ${Entities}Forbidden, ${Entities}Loading } from './${Entities}States';
import styles from './${Entity}Detail.module.css';

export type ${Entity}DetailState =
  | { status: 'loading' }
  | { status: 'error'; error: Error; retry: () => void }
  | { status: 'forbidden' }
  | { status: 'ready'; record: $Entity };

export type ${Entity}DetailProps = {
  state: ${Entity}DetailState;
  onEdit?: () => void;
  onDelete?: () => void;
};

/**
 * One $lower_entity.
 *
 * The layout is `.with-sidebar`: the record's own fields in the main pane, its
 * actions and metadata in the rail. The rail gives up and wraps underneath at
 * a CONTENT threshold rather than a viewport breakpoint, so this page is
 * correct inside a drawer and inside a 288px column without knowing it.$placeholder_note
 */
export function ${Entity}Detail({ state, onEdit, onDelete }: ${Entity}DetailProps) {
  if (state.status === 'loading') return <${Entities}Loading />;
  if (state.status === 'error') return <${Entities}Error error={state.error} onRetry={state.retry} />;
  if (state.status === 'forbidden') return <${Entities}Forbidden />;

  const record = state.record;

  return (
    <article className="with-sidebar" aria-labelledby="$camel-detail-heading">
      <div className="with-sidebar__main stack stack--separate">
        <h1 className={styles.title} id="$camel-detail-heading">
          $title_expr
        </h1>

        <dl className={styles.fields}>
$rows
        </dl>

$related
      </div>

      <aside className="with-sidebar__rail stack stack--related" aria-label="Actions">
        <Button variant="primary" onClick={onEdit}>
          Edit
        </Button>
        <Button variant="danger" onClick={onDelete}>
          Delete
        </Button>
        {/* TODO(copy): a delete confirmation must name the record and state
            what else disappears with it. "Are you sure?" is not that. See
            screen-patterns.md section 8. */}
      </aside>
    </article>
  );
}
""").safe_substitute(
        Entity=Entity, Entities=Entities, camel=camel(name),
        rows="\n".join(rows) or "          {/* no detail fields */}",
        related="\n".join(related),
        lower_entity=singular(name.replace("_", " ")),
        placeholder_note=placeholder_note,
        kit=", ".join(
            (["Badge"] if any(c["jsx"].startswith("<Badge") for c in cells) else [])
            + ["Button"]),
        imports=_helper_imports(cells, set()),
        title_expr=(f"{{record.{title}}}" if title and
                    re.fullmatch(r"[A-Za-z_$][\w$]*", title)
                    else f"{{String(record.{pk_detail})}}"))


DETAIL_CSS = """\
@layer components {
  .title {
    font: var(--type-h1);
    color: var(--fg-strong);
  }

  .fields {
    --detail-fields-gap: var(--gap-grouped);

    display: grid;
    gap: var(--detail-fields-gap);
    grid-template-columns: repeat(auto-fit, minmax(min(var(--measure-narrow), 100%), 1fr));
  }

  /* A definition pair is one thing, so its two halves sit at --gap-fused.
     Anything looser and the term stops reading as belonging to the value. */
  .pair {
    display: flex;
    flex-direction: column;
    gap: var(--gap-fused);
    min-inline-size: 0;
  }

  .term {
    font: var(--type-label);
    color: var(--fg-muted);
  }

  .value {
    font: var(--type-body);
    color: var(--fg-default);
    overflow-wrap: anywhere;
  }
}
"""


def control_jsx(spec: dict[str, Any], indent: str = "          ",
                named_toggle: bool = False) -> str:
    ctrl = spec["control"]
    name = spec["name"]
    key = prop_key(name)
    q, err = js_string(name), member("errors", name)        # E3: `2fa`, `it's`
    attr = f'"{name}"' if '"' not in name else "{" + q + "}"
    acc = f"values.{name}" if key == name else f"values[{json.dumps(name)}]"
    # The control itself carries the error's id and the invalid flag:
    # assistive tech reads `aria-describedby` and `aria-invalid` on the
    # control, not on a wrapper. The id is the one Field.tsx gives the error.
    common = (f'id={{fieldId({q})}}\n{indent}  name={attr}\n'
              f'{indent}  disabled={{disabled}}\n'
              f'{indent}  aria-invalid={{Boolean({err}) || undefined}}\n'
              f"{indent}  aria-describedby={{{err} ? fieldId({q}) + '-error' : undefined}}\n"
              f'{indent}  required={{{str(spec.get("required", False)).lower()}}}')
    if ctrl in STUB_REASON:
        reason = STUB_REASON[ctrl]
        if spec.get("labelColumn"):
            reason += f"; it shows `{spec['labelColumn']}`"
        return (f'{indent}<ControlStub control="{ctrl}" '
                f'reason="{reason}" />')
    if ctrl in ("textarea", "rich-text"):
        return (f"{indent}<TextArea\n{indent}  {common}\n"
                f"{indent}  value={{String({acc} ?? '')}}\n"
                f"{indent}  onChange={{(e) => onChange({q}, e.target.value)}}\n"
                f"{indent}/>")
    if ctrl in ("select", "multi-select"):
        multi = " multiple" if ctrl == "multi-select" else ""
        opts = spec.get("options") or []
        options = "\n".join(
            f"{indent}    <option key={{{json.dumps(o)}}} value={{{json.dumps(o)}}}>"
            f"{{{json.dumps(o)}}}</option>"
            for o in opts)
        blank = (f"{indent}    <option value=\"\">Choose one</option>\n"
                 if not spec.get("required") and not multi else "")
        if not opts and spec.get("labelColumn"):
            # A reference with under 20 parents: the rows come from the
            # parent table, and the option shows the answered label column.
            options = (f"{indent}    {{/* TODO(options): one <option> per "
                       f"parent row, showing `{spec['labelColumn']}` */}}")
        # A multiple select's value is the array, and so is what it sends
        # (Codex on #176): a string selected nothing and sent one option.
        value, read = ((f"{acc} ?? []", "Array.from(e.target.selectedOptions, (option) => option.value)")
                       if multi else (f"String({acc} ?? '')", "e.target.value"))
        return (f"{indent}<Select{multi}\n{indent}  {common}\n"
                f"{indent}  value={{{value}}}\n"
                f"{indent}  onChange={{(e) => onChange({q}, {read})}}\n"
                f"{indent}>\n{blank}{options}\n{indent}</Select>")
    if ctrl == "radio-group":
        opts = json.dumps(spec.get("options") or [])
        return (f"{indent}<RadioGroup\n{indent}  name={attr}\n"
                f"{indent}  value={{{acc} === null || {acc} === undefined ? null : String({acc})}}\n"
                f"{indent}  options={{{opts}}}\n"
                f"{indent}  disabled={{disabled}}\n"
                f"{indent}  labelledBy={{fieldId({q}) + '-label'}}\n"
                f"{indent}  describedBy={{{err} ? fieldId({q}) + '-error' : undefined}}\n"
                f"{indent}  invalid={{Boolean({err})}}\n"
                f"{indent}  required={{{str(spec.get('required', False)).lower()}}}\n"
                f"{indent}  onValueChange={{(next) => onChange({q}, next)}}\n"
                f"{indent}/>")
    if ctrl in ("switch", "checkbox"):
        # A posted form sends a checked box as `name=on`; it needs the name.
        named = f"{indent}  name={attr}\n" if named_toggle else ""
        return (f"{indent}<Toggle\n{indent}  id={{fieldId({q})}}\n{named}"
                f"{indent}  label=\"{spec['label']}\"\n"
                f"{indent}  checked={{Boolean({acc})}}\n"
                f"{indent}  disabled={{disabled}}\n"
                f"{indent}  aria-invalid={{Boolean({err}) || undefined}}\n"
                f"{indent}  aria-describedby={{{err} ? fieldId({q}) + '-error' : undefined}}\n"
                f"{indent}  onChange={{(e) => onChange({q}, e.target.checked)}}\n"
                f"{indent}/>")
    if ctrl in ("number-input", "stepper", "percent-input", "currency-input"):
        extra = ""
        if "min" in spec:
            extra += f"\n{indent}  min={{{spec['min']}}}"
        if "max" in spec:
            extra += f"\n{indent}  max={{{spec['max']}}}"
        note = ""
        if ctrl == "currency-input":
            money = spec.get("money") or {}
            cur = money.get("currency") or "the currency"
            if money.get("storage") == "minor-units":
                note = (f"\n{indent}  // TODO(money): stored in minor units of {cur}. "
                        f"Divide by\n{indent}  // minorUnitScale({json.dumps(cur) if money.get('currency') else 'currency'}) "
                        f"on read, multiply on write, and keep the\n{indent}  // float out of the middle.")
            elif money.get("storage") == "decimal":
                extra += f'\n{indent}  step="any"'
                note = (f"\n{indent}  // TODO(money): a decimal amount in {cur}; "
                        f"the database rounds to its\n{indent}  // scale. Parse "
                        f"permissively, format on blur, never while typing.")
            else:
                note = (f"\n{indent}  // TODO(money): minor units or a decimal? "
                        f"Answer the `.money` question;\n{indent}  // the two "
                        f"differ by the currency's scale on every read and write.")
        return (f"{indent}<NumberInput\n{indent}  {common}{extra}{note}\n"
                f"{indent}  value={{{acc} ?? ''}}\n"
                # An emptied input reads NaN; the draft holds null (Codex on #176).
                f"{indent}  onChange={{(e) => onChange({q}, Number.isNaN(e.target.valueAsNumber) "
                f"? null : e.target.valueAsNumber)}}\n"
                f"{indent}/>")
    if ctrl in ("readonly-text", "readonly-timestamp"):
        return (f"{indent}<TextInput\n{indent}  {common}\n"
                f"{indent}  readOnly\n"
                f"{indent}  value={{String({acc} ?? '')}}\n{indent}/>")
    input_type = {
        "email-input": "email", "url-input": "url", "tel-input": "tel",
        "password-input": "password", "date-picker": "date",
        "datetime-picker": "datetime-local", "time-picker": "time",
        "color-picker": "color",
    }.get(ctrl, "text")
    extra = ""
    if "maxLength" in spec:
        extra += f"\n{indent}  maxLength={{{spec['maxLength']}}}"
    if "pattern" in spec:
        extra += f"\n{indent}  pattern={{{json.dumps(spec['pattern'])}}}"
    if ctrl == "password-input":
        extra += f'\n{indent}  autoComplete="new-password"'
    if ctrl == "slug-input":
        extra += (f'\n{indent}  inputMode="url"'
                  f"\n{indent}  // TODO(slug): derive from the title until the "
                  f"user edits this\n{indent}  // field by hand, then stop — a "
                  f"slug that keeps changing breaks links.")
    return (f'{indent}<TextInput\n{indent}  type="{input_type}"\n'
            f"{indent}  {common}{extra}\n"
            f"{indent}  value={{String({acc} ?? '')}}\n"
            f"{indent}  onChange={{(e) => onChange({q}, e.target.value)}}\n"
            f"{indent}/>")


def _form_sections(table: dict[str, Any], model: dict[str, Any], ans: Answers,
                   posted: bool = False) -> tuple[str, set[str]]:
    """The form's fieldsets, and the kit components they use. A form that
    posts its FormData (`posted`) names every control, the toggles too."""
    specs = {s["name"]: s for s in
             (field_spec(c, table, model, ans) for c in table["columns"]
              if ans.in_form(table, c))}
    default_groups = [{"legend": "Details", "fields": list(specs)}]
    groups = ans.groups(table, table["screens"].get("field_groups")
                        or default_groups)

    sections: list[str] = []
    kit: set[str] = {"Button"}
    CONTROL_IMPORT = {
        "textarea": "TextArea", "rich-text": "TextArea",
        "select": "Select", "multi-select": "Select",
        "radio-group": "RadioGroup",
        "switch": "Toggle", "checkbox": "Toggle",
        "number-input": "NumberInput", "stepper": "NumberInput",
        "percent-input": "NumberInput", "currency-input": "NumberInput",
    }
    for g in groups:
        fields = [f for f in g.get("fields", []) if f in specs]
        if not fields:
            continue
        body = []
        for f in fields:
            s = specs[f]
            kit.add(CONTROL_IMPORT.get(s["control"], "TextInput")
                    if s["control"] not in STUB_REASON else "ControlStub")
            if s["control"] not in ("switch", "checkbox"):
                kit.add("Field")
            review = (f"\n        {{/* review: {s['review']} */}}"
                      if s.get("review") else "")
            if s["control"] in ("switch", "checkbox"):
                # A toggle is its own label; it gets the error below it, with
                # the id the control's aria-describedby names.
                err = member("errors", f)
                body.append(
                    f"{review}\n        <div className={{styles.field}} "
                    f"data-state={{{err} ? 'error' : undefined}}>\n"
                    f"{control_jsx(s, '          ', posted)}\n"
                    f"          {{{err} ? (\n"
                    f"            <p className={{styles.fieldError}} id={{fieldId({js_string(f)}) + '-error'}}>\n"
                    f"              {{{err}}}\n"
                    f"            </p>\n"
                    f"          ) : null}}\n"
                    f"        </div>")
                continue
            body.append(Template("""$review
        <Field
          id={fieldId($qname)}
          label="$label"
          required={$required}
          error={$err ?? null}
          disabled={disabled}$group
        >
$control
        </Field>""").safe_substitute(
                qname=js_string(f), err=member("errors", f), label=s["label"],
                required=str(s.get("required", False)).lower(),
                group="\n          group" if s["control"] == "radio-group" else "",
                control=control_jsx(s), review=review))
        sections.append(
            f"      <fieldset className={{styles.group}} disabled={{disabled}}>\n"
            f"        <legend className={{styles.legend}}>"
            f"{g.get('legend', 'Details')}</legend>\n"
            + "\n".join(body) + "\n      </fieldset>")
    return "\n\n".join(sections) or "      {/* no writable fields */}", kit


def emit_form(table: dict[str, Any], model: dict[str, Any], ans: Answers,
              action: bool = False) -> str:
    name = table["name"]
    Entity = pascal(singular(name))
    Entities = pascal(name)
    sections, kit = _form_sections(table, model, ans, posted=action)
    if action:
        return emit_posted_form(table, sections, kit)

    return Template("""\
import { useEffect, useRef, useState } from 'react';
import { $kit } from '../../ui';
import type { ${Entity}Draft } from './$camel.types';
import styles from './${Entity}Form.module.css';

export type ${Entity}FormProps = {
  values: Partial<${Entity}Draft>;
  errors: Partial<Record<keyof ${Entity}Draft, string>>;
  /** Blocks every control AND the submit button, together. */
  disabled?: boolean;
  submitting?: boolean;
  /** Set when the user has changed something and not saved it. */
  dirty?: boolean;
  /** A form-level failure: the save was rejected as a whole. */
  submitError?: string | null;
  onChange: (name: keyof ${Entity}Draft, value: unknown) => void;
  onSubmit: () => void;
  onCancel?: () => void;
};

const fieldId = (name: string) => '$camel-' + name;

/**
 * The $lower_entity form.
 *
 * Three UX rules this markup encodes, all of which generators skip:
 *
 * 1. VALIDATION TIMING. `errors` is rendered whenever it is set; it is the
 *    CALLER's job not to set it until a field has been blurred once. Validating
 *    on every keystroke tells someone their email is invalid while they are
 *    still typing the @.
 * 2. THE ERROR SUMMARY comes first in the DOM and moves focus, because on a
 *    long form the invalid field is usually off-screen. Each entry links to
 *    its field.
 * 3. REQUIRED IS MARKED BOTH WAYS. The asterisk is decorative and hidden from
 *    assistive tech; the `required` attribute is what actually announces it.
 *
 * Still yours to do: the unsaved-changes guard (block the route change while
 * `dirty`), and autosave if this form is long enough to deserve it. See
 * screen-patterns.md section 13.
 */
export function ${Entity}Form({
  values,
  errors,
  disabled = false,
  submitting = false,
  dirty = false,
  submitError = null,
  onChange,
  onSubmit,
  onCancel,
}: ${Entity}FormProps) {
  const invalid = Object.entries(errors).filter(([, message]) => Boolean(message));
  const summaryRef = useRef<HTMLDivElement>(null);
  const [attempt, setAttempt] = useState(0);
  const focusedFor = useRef(0);

  // After a submit attempt that failed validation, move focus to the
  // summary: once per attempt, whether or not the error count changed. The
  // caller sets `errors` in `onSubmit` (React renders them with the attempt)
  // or, validating asynchronously, sets `submitting` while it runs; fixing a
  // field afterwards does not move focus again.
  useEffect(() => {
    if (attempt > focusedFor.current && invalid.length > 0) {
      focusedFor.current = attempt;
      summaryRef.current?.focus();
    }
  }, [attempt, invalid.length]);
  // A save that ran and came back clean consumes the attempt, so an error
  // that appears later, from a blur, does not pull focus to the summary.
  useEffect(() => {
    if (!submitting && invalid.length === 0) focusedFor.current = attempt;
  }, [submitting, attempt, invalid.length]);

  return (
    <form
      className="stack stack--separate"
      noValidate
      onSubmit={(event) => {
        event.preventDefault();
        setAttempt((n) => n + 1);
        onSubmit();
      }}
    >
      {invalid.length > 0 ? (
        <div className={styles.summary} role="alert" tabIndex={-1} ref={summaryRef}>
          <p className={styles.summaryTitle}>
            {invalid.length === 1 ? 'One field needs attention' : String(invalid.length) + ' fields need attention'}
          </p>
          <ul className={styles.summaryList}>
            {invalid.map(([name, message]) => (
              <li key={name}>
                <a className={styles.summaryLink} href={'#' + fieldId(name)}>
                  {String(message)}
                </a>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {submitError ? (
        <p className={styles.submitError} role="alert">
          {submitError}
        </p>
      ) : null}

$sections

      <div className="cluster cluster--tight">
        <Button type="submit" variant="primary" loading={submitting} disabled={disabled}>
          Save
        </Button>
        <Button type="button" variant="ghost" onClick={onCancel} disabled={submitting}>
          {dirty ? 'Discard changes' : 'Cancel'}
        </Button>
      </div>
    </form>
  );
}
""").safe_substitute(
        Entity=Entity, Entities=Entities, camel=camel(name),
        kit=", ".join(sorted(kit)), sections=sections,
        lower_entity=singular(name.replace("_", " ")))


# ---------------------------------------------------------------------------
# Next.js server actions (--server-actions)
# ---------------------------------------------------------------------------
# The form posts its FormData to a 'use server' function through React 19's
# <form action>, useActionState holds the result, and useFormStatus gives the
# button its pending state (nextjs.org/docs/app/guides/forms).

def emit_posted_form(table: dict[str, Any], sections: str, kit: set[str]) -> str:
    name = table["name"]
    Entity = pascal(singular(name))
    return Template("""\
'use client';

import { useEffect, useRef } from 'react';
import { useFormStatus } from 'react-dom';
import { $kit } from '../../ui';
import type { ${Entity}Draft } from './$camel.types';
import styles from './${Entity}Form.module.css';

export type ${Entity}FormProps = {
  values: Partial<${Entity}Draft>;
  errors: Partial<Record<keyof ${Entity}Draft, string>>;
  /** The server action the form posts its FormData to (React 19's `<form action>`). */
  action: (formData: FormData) => void;
  /** Blocks every control AND the submit button, together. */
  disabled?: boolean;
  /** Set when the user has changed something and not saved it. */
  dirty?: boolean;
  /** A form-level failure: the save was rejected as a whole. */
  submitError?: string | null;
  onChange: (name: keyof ${Entity}Draft, value: unknown) => void;
  onCancel?: () => void;
};

const fieldId = (name: string) => '$camel-' + name;

/** The submit button reads the form it is rendered in: pending while the action runs. */
function SaveButton({ disabled }: { disabled: boolean }) {
  const { pending } = useFormStatus();
  return (
    <Button type="submit" variant="primary" loading={pending} disabled={disabled}>
      Save
    </Button>
  );
}

/**
 * The $lower_entity form, posted to a server action.
 *
 * The client-side form's markup and rules, with the save on the server: the
 * browser posts the FormData, the action validates it against the server's
 * schema and returns the errors, and the summary takes focus each time a
 * result comes back with errors. Every control has its `name`, since a control
 * without one is not posted. ${Entity}ActionForm.tsx wires it to the actions.
 */
export function ${Entity}Form({
  values,
  errors,
  action,
  disabled = false,
  dirty = false,
  submitError = null,
  onChange,
  onCancel,
}: ${Entity}FormProps) {
  const invalid = Object.entries(errors).filter(([, message]) => Boolean(message));
  const summaryRef = useRef<HTMLDivElement>(null);

  // The action returns a new errors object with each result, so focus moves to
  // the summary once per failed submit, and never while the user types.
  useEffect(() => {
    if (Object.values(errors).some(Boolean)) summaryRef.current?.focus();
  }, [errors]);

  return (
    <form className="stack stack--separate" noValidate action={action}>
      {invalid.length > 0 ? (
        <div className={styles.summary} role="alert" tabIndex={-1} ref={summaryRef}>
          <p className={styles.summaryTitle}>
            {invalid.length === 1 ? 'One field needs attention' : String(invalid.length) + ' fields need attention'}
          </p>
          <ul className={styles.summaryList}>
            {invalid.map(([name, message]) => (
              <li key={name}>
                <a className={styles.summaryLink} href={'#' + fieldId(name)}>
                  {String(message)}
                </a>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {submitError ? (
        <p className={styles.submitError} role="alert">
          {submitError}
        </p>
      ) : null}

$sections

      <div className="cluster cluster--tight">
        <SaveButton disabled={disabled} />
        <Button type="button" variant="ghost" onClick={onCancel}>
          {dirty ? 'Discard changes' : 'Cancel'}
        </Button>
      </div>
    </form>
  );
}
""").safe_substitute(
        Entity=Entity, camel=camel(name), kit=", ".join(sorted(kit)),
        sections=sections, lower_entity=singular(name.replace("_", " ")))


def emit_action_form(table: dict[str, Any]) -> str:
    name = table["name"]
    Entity = pascal(singular(name))
    pk = table["primary_key"][0] if table["primary_key"] else "id"
    return Template("""\
'use client';

import { useActionState, useEffect, useState } from 'react';
import { ${Entity}Form } from './${Entity}Form';
import type { $Entity, ${Entity}Draft } from './$camel.types';
import { create$Entity, update$Entity } from '../../server/$name.actions';
import type { ${Entity}ActionState } from '../../server/$name.actions';

export type ${Entity}ActionFormProps = {
  /** The row to edit; without one the form creates a row. */
  row?: $Entity;
  onCancel?: () => void;
};

/**
 * ${Entity}Form on the server's actions: useActionState holds what the last
 * submit returned (the values the server read, its errors, a form-level
 * failure), and the draft between submits is local state.
 */
export function ${Entity}ActionForm({ row, onCancel }: ${Entity}ActionFormProps) {
  const initial: ${Entity}ActionState = { values: row ?? {}, errors: {}, submitError: null };
  // The key travels outside the form's fields, bound to the action.
  const save = row ? update$Entity.bind(null, $key) : create$Entity;
  const [state, formAction] = useActionState(save, initial);
  const [values, setValues] = useState<Partial<${Entity}Draft>>(state.values);
  const [dirty, setDirty] = useState(false);

  // Each result replaces the draft with the values the server read.
  useEffect(() => {
    setValues(state.values);
    setDirty(false);
  }, [state]);

  return (
    <${Entity}Form
      values={values}
      errors={state.errors}
      submitError={state.submitError}
      action={formAction}
      dirty={dirty}
      onChange={(field, value) => {
        setValues((draft) => ({ ...draft, [field]: value }));
        setDirty(true);
      }}
      onCancel={onCancel}
    />
  );
}
""").safe_substitute(Entity=Entity, camel=camel(name), name=name, key=member("row", pk))


def _form_read(f: dict[str, Any]) -> str:
    """How the action reads one field from the FormData, by the schema's type."""
    key = js_string(f["name"])
    empty = " ?? null" if f["nullable"] else ""
    if f["array"]:
        each = "Number" if f["type"] in NUMBER_TYPES else "String"
        return f"form.getAll({key}).map({each})"
    if f["type"] == "boolean":
        return f"form.get({key}) === 'on'"
    if f["type"] in NUMBER_TYPES and not (f["enum"] or f["options"]):
        return f"number({key}){empty}"
    return f"text({key}){empty}"


def emit_actions(table: dict[str, Any], model: dict[str, Any], ans: Answers) -> str:
    name = table["name"]
    Entity = pascal(singular(name))
    pk = table["primary_key"][0] if table["primary_key"] else "id"
    fields = schema_fields(table, model, ans)
    reads = []
    for f in fields:
        note = ""
        if f["temporal"] == "instant" and f["aware"]:
            note = ("    // TODO(time zone): a datetime-local value has no offset, and the schema\n"
                    "    // wants one. Send the browser's with it (a hidden input), never the server's.\n")
        elif f["type"] in ("jsonb", "json"):
            note = "    // TODO(json): the field posts text; parse it into the value it stands for.\n"
        reads.append(f"{note}    {prop_key(f['name'])}: {_form_read(f)},")
    return Template("""\
'use server';

/**
 * The server actions for $lower: the form posts here, and this is the
 * control, as the form's own validation is a courtesy. Each action reads the
 * FormData by the column's type, validates it against the server's schema and
 * writes through the server's Supabase client, which carries the signed-in
 * user's session, so row-level security decides what it may write. Next.js
 * asks each action to check who is calling: the policies in db/policies/ are
 * that check, so apply them before this ships.
 */
import { revalidatePath } from 'next/cache';
import { createClient } from '../lib/supabase.server';
import { ${schema}DraftSchema } from './$name.schema';
import type { $Entity, ${Entity}Draft } from '../features/$name/$camel.types';

export type ${Entity}ActionState = {
  values: Partial<${Entity}Draft>;
  errors: Partial<Record<keyof ${Entity}Draft, string>>;
  submitError: string | null;
};

/** FormData holds strings. Each field is read as the schema's type; an empty
 *  one is left out, or null where the column takes null. */
function draftFrom(form: FormData): Partial<${Entity}Draft> {
  const text = (key: string) => {
    const value = form.get(key);
    return typeof value === 'string' && value !== '' ? value : undefined;
  };
  const number = (key: string) => {
    const value = text(key);
    return value === undefined ? undefined : Number(value);
  };
  return {
$reads
  } as Partial<${Entity}Draft>;
}

/** The schema's first message for each field, under the field's name. */
function errorsFrom(issues: { path: PropertyKey[]; message: string }[]) {
  const errors: Partial<Record<keyof ${Entity}Draft, string>> = {};
  for (const issue of issues) {
    const field = issue.path[0] as keyof ${Entity}Draft | undefined;
    if (field !== undefined && !errors[field]) errors[field] = issue.message;
  }
  return errors;
}

export async function create$Entity(
  _previous: ${Entity}ActionState,
  form: FormData,
): Promise<${Entity}ActionState> {
  const values = draftFrom(form);
  const parsed = ${schema}DraftSchema.safeParse(values);
  if (!parsed.success) {
    return { values, errors: errorsFrom(parsed.error.issues), submitError: null };
  }
  const supabase = await createClient();
  const { error } = await supabase.from($table).insert(parsed.data);
  if (error) return { values, errors: {}, submitError: 'The save failed: ' + error.message };
  revalidatePath('/$name'); // TODO(route): the path the list renders at.
  return { values: {}, errors: {}, submitError: null };
}

export async function update$Entity(
  key: $Entity[$pkq],
  _previous: ${Entity}ActionState,
  form: FormData,
): Promise<${Entity}ActionState> {
  const values = draftFrom(form);
  const parsed = ${schema}DraftSchema.safeParse(values);
  if (!parsed.success) {
    return { values, errors: errorsFrom(parsed.error.issues), submitError: null };
  }
  const supabase = await createClient();
  const { error } = await supabase.from($table).update(parsed.data).eq($pkq, key);
  if (error) return { values, errors: {}, submitError: 'The save failed: ' + error.message };
  revalidatePath('/$name'); // TODO(route): the path the list renders at.
  return { values: parsed.data, errors: {}, submitError: null };
}
""").safe_substitute(
        Entity=Entity, camel=camel(name), name=name, schema=camel(singular(name)),
        table=js_string(name), pkq=js_string(pk), reads="\n".join(reads),
        lower=name.replace("_", " "))


# The server's client: Supabase's own Next.js example
# (github.com/supabase/supabase, examples/auth/nextjs/lib/supabase/server.ts),
# typed with the generated Database.
SUPABASE_SERVER_TS = """\
// The server's Supabase client, for server actions, route handlers and Server
// Components (supabase-integration.md §9). It reads the signed-in user's
// session from the request's cookies, so row-level security applies to every
// query it makes. It holds the publishable key, never a secret one.
import { createServerClient } from '@supabase/ssr';
import { cookies } from 'next/headers';
import type { Database } from './database.types';

export async function createClient() {
  const cookieStore = await cookies();

  return createServerClient<Database>(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY!,
    {
      cookies: {
        getAll() {
          return cookieStore.getAll();
        },
        setAll(cookiesToSet) {
          try {
            cookiesToSet.forEach(({ name, value, options }) => cookieStore.set(name, value, options));
          } catch {
            // Called from a Server Component, which cannot set cookies: a proxy
            // that refreshes the session (Supabase's middleware) does it instead.
          }
        },
      },
    },
  );
}
"""

# The browser's client in a Next.js app: NEXT_PUBLIC_ variables, which Next.js
# writes into the bundle, in place of Vite's.
SUPABASE_NEXT_TS = """\
// The browser's only Supabase client (supabase-integration.md §9). It holds the
// publishable key, which is safe in a bundle because row-level security decides
// what it may do. Every NEXT_PUBLIC_ variable is public: a secret key never goes in one.
//
// database.types.ts comes from the database itself:
//   supabase gen types typescript --project-id <project-ref> > src/lib/database.types.ts
import { createBrowserClient } from '@supabase/ssr';
import type { Database } from './database.types';

const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
const publishableKey = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY;

if (!url || !publishableKey) {
  throw new Error('Set NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY (sb_publishable_…) in .env.local.');
}
if (publishableKey.startsWith('sb_secret_') || legacyRole(publishableKey) === 'service_role') {
  // That key bypasses row-level security, and this file ships to every browser.
  throw new Error('NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY holds a secret key. Keep it on the server.');
}

/** The role inside a legacy JWT key (`anon` or `service_role`), if it is one. */
function legacyRole(key: string): string | undefined {
  try {
    const payload = key.split('.')[1] ?? '';
    return JSON.parse(atob(payload.replace(/-/g, '+').replace(/_/g, '/'))).role;
  } catch {
    return undefined;
  }
}

export const supabase = createBrowserClient<Database>(url, publishableKey);
"""


FORM_CSS = """\
@layer components {
  .group {
    --form-group-gap:    var(--gap-grouped);
    --form-group-inset:  var(--pad-card);
    --form-group-border: var(--border-subtle);
    --form-group-radius: var(--radius-lg);

    display: flex;
    flex-direction: column;
    gap: var(--form-group-gap);
    padding: var(--form-group-inset);
    border: var(--stroke-default) solid var(--form-group-border);
    border-radius: var(--form-group-radius);
    background-color: var(--bg-surface);
    min-inline-size: 0;
  }

  .group:disabled { --form-group-border: var(--border-subtle); opacity: 0.6; }

  .legend {
    padding-inline: var(--pad-inline-xs);
    font: var(--type-h4);
    color: var(--fg-strong);
  }

  .field { display: block; }

  .fieldError {
    font: var(--type-label);
    color: var(--fg-danger);
  }

  .summary {
    --form-summary-inset:  var(--pad-well);
    --form-summary-border: var(--border-accent);
    --form-summary-radius: var(--radius-lg);

    display: flex;
    flex-direction: column;
    gap: var(--gap-tight);
    padding: var(--form-summary-inset);
    border: var(--stroke-thick) solid var(--form-summary-border);
    border-radius: var(--form-summary-radius);
    background-color: var(--bg-sunken);
  }

  .summaryTitle {
    font: var(--type-h4);
    color: var(--fg-danger);
  }

  .summaryList {
    display: flex;
    flex-direction: column;
    gap: var(--gap-fused);
    font: var(--type-body);
  }

  .summaryLink {
    color: var(--fg-link);
    text-decoration-line: underline;
    text-decoration-thickness: var(--stroke-hairline);
  }

  .submitError {
    font: var(--type-body);
    color: var(--fg-danger);
  }
}
"""


def emit_states(table: dict[str, Any], model: dict[str, Any],
                ans: Answers) -> str:
    name = table["name"]
    Entities = pascal(name)
    human = name.replace("_", " ")
    empty = ans.empty(table)
    cols = len(ans.list_columns(table)) or 3
    rls = ans.rls(table)

    forbidden_note = (
        "Row-level security is on for this table, so this is a real state: the\n"
        " * query succeeded and returned nothing because the policy filtered\n"
        " * everything out. Rendering that as 'no records' tells the user their\n"
        " * data is gone."
        if rls else
        "RLS was reported as off, so this should be unreachable today. It is\n"
        " * generated anyway, because 'we will add RLS later' is always true and\n"
        " * retrofitting this state means touching every list in the app.")

    return Template("""\
import { Button, Skeleton, StateBlock } from '../../ui';
import styles from './${Entities}States.module.css';

/**
 * The states a generator defaults and a finished product designs.
 *
 * Every TODO(copy) below is a sentence only someone who knows this product can
 * write. Leaving them as-is ships placeholder copy, which is worse than no
 * copy because it looks deliberate.
 */

/** No $human have ever existed. The most-seen screen in the app on day one. */
export function ${Entities}Empty({ onCreate }: { onCreate?: () => void }) {
  return (
    <StateBlock
      kind="first-run"
      headline="$headline"
      // TODO(copy): say what this screen will hold and why it is worth filling
      // in. One sentence. "No data" is the absence of copy, not copy.
      body="$body"
      action={
        <Button variant="primary" onClick={onCreate}>
          $action
        </Button>
      }
    />
  );
}

/**
 * A filter or a search matched nothing. A DIFFERENT screen from the one above:
 * the records exist, this query just missed them, so the action is "clear the
 * filter", never "create a record".
 */
export function ${Entities}FilteredEmpty({ onClearFilters }: { onClearFilters?: () => void }) {
  return (
    <StateBlock
      kind="filtered"
      headline="No $human match those filters"
      // TODO(copy): name the filters that are on, so the user can see what to
      // relax without hunting for it.
      body="Try a broader search, or clear the filters to see everything."
      action={
        <Button variant="ghost" onClick={onClearFilters}>
          Clear filters
        </Button>
      }
    />
  );
}

/**
 * A skeleton shaped like the real table: same column count, same row height.
 * A spinner would be less work and would also let the page jump when the data
 * lands, moving whatever the user was about to click.
 */
export function ${Entities}Loading({ rows = 5 }: { rows?: number }) {
  return (
    <div className={styles.loading} role="status" aria-live="polite">
      <span className="visually-hidden">Loading $human</span>
      {Array.from({ length: rows }, (_, index) => (
        <div className={styles.loadingRow} key={index}>
          {Array.from({ length: $cols }, (_, cell) => (
            <Skeleton key={cell} width={cell === 0 ? 0.8 : 0.5} />
          ))}
        </div>
      ))}
    </div>
  );
}

/** The request failed. Always offer the retry — an error with no way forward
 *  is a dead end, and users reload the whole app instead. */
export function ${Entities}Error({ error, onRetry }: { error?: Error; onRetry?: () => void }) {
  return (
    <StateBlock
      kind="error"
      // TODO(copy): say what failed in the user's terms, not the transport's.
      // "We could not load your $human" beats "Request failed".
      headline="Something went wrong loading $human"
      body={error?.message}
      action={
        <Button variant="primary" onClick={onRetry}>
          Try again
        </Button>
      }
    />
  );
}

/**
 * The user is not allowed to see these rows.
 *
 * $forbidden_note
 */
export function ${Entities}Forbidden() {
  return (
    <StateBlock
      kind="forbidden"
      headline="You do not have access to $human"
      // TODO(copy): say who to ask. A permission wall with no route onward is
      // a support ticket. Do NOT reveal whether any records exist.
      body="Ask an administrator if you think this is a mistake."
    />
  );
}

/**
 * Data on screen is known to be out of date — a realtime event arrived, or a
 * background revalidation failed. Shown ABOVE the stale rows rather than
 * replacing them: taking correct-a-moment-ago data away is worse than
 * labelling it.
 */
export function ${Entities}Stale({ onRefresh }: { onRefresh?: () => void }) {
  return (
    <StateBlock
      kind="stale"
      headline="This list has changed"
      body="Someone else updated these $human while you were reading."
      action={
        <Button variant="ghost" onClick={onRefresh}>
          Refresh
        </Button>
      }
    />
  );
}
""").safe_substitute(
        Entities=Entities, human=human, cols=cols,
        headline=empty["headline"],
        body=empty["body"] or f"TODO(copy): what {human} are for.",
        action=empty["action"], forbidden_note=forbidden_note)


STATES_CSS = """\
@layer components {
  .loading {
    display: flex;
    flex-direction: column;
    gap: var(--gap-related);
  }

  /* The skeleton row mirrors the real row's inset and rule, so the switch from
     loading to loaded changes the CONTENT and nothing else. */
  .loadingRow {
    display: flex;
    gap: var(--gap-grouped);
    align-items: center;
    padding: var(--pad-block-sm) var(--pad-inline-md);
    border-block-end: var(--stroke-default) solid var(--border-subtle);
    min-block-size: var(--tap-min);
  }

  .loadingRow > * { flex: 1 1 0; min-inline-size: 0; }
}
"""


def emit_index(table: dict[str, Any], ans: Answers) -> str:
    name = table["name"]
    Entity = pascal(singular(name))
    Entities = pascal(name)
    return Template("""\
export { ${Entities}List } from './${Entities}List';
export { ${Entity}Detail } from './${Entity}Detail';
export { ${Entity}Form } from './${Entity}Form';
export {
  ${Entities}Empty,
  ${Entities}FilteredEmpty,
  ${Entities}Loading,
  ${Entities}Error,
  ${Entities}Forbidden,
  ${Entities}Stale,
} from './${Entities}States';
export type { $Entity, ${Entity}Draft, ${Entity}ListState } from './$camel.types';
export { ${camel}Fields, ${camel}Groups, ${camel}ListColumns } from './$camel.fields';
""").safe_substitute(Entity=Entity, Entities=Entities, camel=camel(name))


# ---------------------------------------------------------------------------
# Tailwind variant
# ---------------------------------------------------------------------------

# Utility class names from the suite's Tailwind theme (assets/configs/
# tailwind.config.ts). There is not one arbitrary value here: if a utility does
# not exist, the token does not exist either, and writing `p-[13px]` re-opens
# the value space the closed scale is there to shut.
TW_UTILITIES = {
    # typography and colour
    "heading":      "text-h2 text-strong",
    "title":        "text-h1 text-strong",
    "headline":     "text-h4 text-strong max-w-narrow",
    "body":         "text-body max-w-narrow",
    "label":        "text-label text-default",
    "legend":       "px-inline-xs text-h4 text-strong",
    "groupLabel":   "float-left w-full p-0",
    "required":     "text-danger-fg",
    "help":         "text-label text-muted",
    "error":        "text-label text-danger-fg",
    "term":         "text-label text-muted",
    "value":        "text-body text-default break-words",
    "muted":        "text-muted",
    "stale":        "text-label text-warning-fg",
    "cardTitle":    "text-h4 text-strong",
    "cardMeta":     "text-label text-muted",
    "cardLink":     "text-inherit no-underline hover:underline",
    "link":         "text-link underline",
    "summaryLink":  "text-link underline",
    "summaryTitle": "text-h4 text-danger-fg",
    "submitError":  "text-body text-danger-fg",
    "toggleLabel":  "text-body text-default",
    "numeric":      "tabular-nums text-end",
    "mono":         "font-mono text-code",
    "truncate":     "max-w-narrow overflow-hidden text-ellipsis whitespace-nowrap",
    # structure
    "control":      "block",
    "field":        "block",
    "fieldError":   "text-label text-danger-fg",
    "action":       "flex gap-tight",
    "options":      "flex flex-col gap-tight",
    "option":       "flex items-center gap-tight min-h-tap text-body text-default",
    "toggle":       "flex items-center gap-tight min-h-tap",
    "pair":         "flex flex-col gap-fused min-w-0",
    "fields":       "grid gap-grouped",
    "group":        "flex flex-col gap-grouped p-card bg-surface border border-line-subtle rounded-card min-w-0",
    "summary":      "flex flex-col gap-tight p-well bg-sunken border-thick border-line-accent rounded-card",
    "summaryList":  "flex flex-col gap-fused text-body",
    "loading":      "flex flex-col gap-related",
    "loadingRow":   "flex items-center gap-grouped px-inline-md py-block-sm min-h-tap border-b border-line-subtle",
    "cardMedia":    "rounded-card overflow-hidden",
    "th":           "px-inline-md py-block-sm border-b text-label text-muted text-start whitespace-nowrap",
    "td":           "px-inline-md py-block-sm border-b align-middle",
    "head":         "sticky top-0 z-raised bg-surface",
}

# The handful of rules utilities genuinely cannot reach: variant and state
# tables driven by data attributes, a sticky table column, keyframes, and the
# two intrinsic-sizing tricks. They live in ONE global stylesheet in the
# components layer rather than being faked with arbitrary values.
#
# This is the honest boundary of the Tailwind stack, and it is stated rather
# than hidden: a utility system is excellent at layout, spacing, colour and
# type, and has nothing to say about a component's state machine.
TW_SCAFFOLD_CLASS = {
    "root": "scaffold-root",          # resolved per component by its parent class
    "spinner": "scaffold-spinner",
    "textarea": "scaffold-textarea",
    "toggleInput": "scaffold-toggle-input",
    "stub": "scaffold-stub",
    "scroller": "scaffold-scroller",
    "row": "scaffold-row",
    "sticky": "scaffold-sticky",
    "card": "scaffold-card",
}

SCAFFOLD_CSS = """\
/* =========================================================================
   scaffold.css — the part of the scaffold that utilities cannot express.

   Import it AFTER tokens.css and inside the components layer:

     @import url('./scaffold.css') layer(components);

   What lives here and why:
     - variant and state tables driven by data attributes and pseudo-classes
     - the sticky identifying column in a wide table
     - keyframes
     - two intrinsic-sizing rules (`1lh`, `field-sizing`)

   Everything else in the generated components is a utility class, because
   everything else is layout, spacing, colour or type — which is what a
   utility system is good at. A component's state machine is not.
   ========================================================================= */

@layer components {
  .scaffold-root {
    --scaffold-bg:      var(--bg-surface);
    --scaffold-fg:      var(--fg-default);
    --scaffold-border:  var(--border-default);
    --scaffold-overlay: transparent;
    --scaffold-motion:  var(--motion-hover);

    border: var(--stroke-default) solid var(--scaffold-border);
    background-color: var(--scaffold-bg);
    background-image: linear-gradient(var(--scaffold-overlay), var(--scaffold-overlay));
    color: var(--scaffold-fg);
    transition: background-color var(--scaffold-motion),
                border-color var(--scaffold-motion),
                color var(--scaffold-motion);
  }

  /* Interaction paints as a translucent overlay rather than replacing the
     fill, so one hover rule stays correct for every variant. */
  .scaffold-root:hover:not(:disabled)  { --scaffold-overlay: var(--bg-hover); }
  .scaffold-root:active:not(:disabled) { --scaffold-overlay: var(--bg-active); }

  /* The ring itself is one global decision made in reset.css. What a
     component owes the focus state is not being clipped by a neighbour. */
  .scaffold-root:focus-visible,
  .scaffold-row:focus-within,
  .scaffold-card:focus-within,
  .scaffold-scroller:focus-visible {
    position: relative;
    z-index: var(--z-raised);
  }

  .scaffold-root:disabled,
  .scaffold-root[aria-disabled="true"] {
    --scaffold-bg:     var(--bg-disabled);
    --scaffold-fg:     var(--fg-disabled);
    --scaffold-border: var(--border-subtle);
    cursor: not-allowed;
  }

  .scaffold-root[data-variant="primary"] {
    --scaffold-bg:     var(--bg-accent);
    --scaffold-fg:     var(--fg-on-accent);
    --scaffold-border: transparent;
  }

  .scaffold-root[data-variant="ghost"] {
    --scaffold-bg:     transparent;
    --scaffold-border: transparent;
  }

  .scaffold-root[data-variant="danger"] {
    --scaffold-bg:     var(--bg-danger);
    --scaffold-fg:     var(--fg-on-danger);
    --scaffold-border: transparent;
  }

  .scaffold-root[data-state="loading"] { cursor: progress; }
  .scaffold-root[data-state="error"],
  .scaffold-root[aria-invalid="true"]  { --scaffold-border: var(--border-invalid); }

  .scaffold-spinner {
    inline-size: 1em;
    block-size: 1em;
    flex: none;
    border: var(--stroke-thick) solid currentcolor;
    border-block-start-color: transparent;
    border-radius: var(--radius-full);
    animation: scaffold-spin var(--motion-loop) infinite;
  }

  /* `field-sizing` grows the box with the text, which is what every user
     expects a textarea to do and what none of them do by default. */
  .scaffold-textarea {
    block-size: auto;
    resize: vertical;
    field-sizing: content;
  }

  .scaffold-toggle-input {
    inline-size: var(--space-block);
    block-size: var(--space-block);
    accent-color: var(--bg-accent);
    flex: none;
  }

  /* A control the scaffold refused to guess at. Loud on purpose. */
  .scaffold-stub {
    display: block;
    padding: var(--pad-well);
    border: var(--stroke-thick) dashed var(--border-strong);
    border-radius: var(--radius-md);
    background-color: var(--bg-sunken);
    color: var(--fg-muted);
    font: var(--type-code);
  }

  .scaffold-scroller {
    overflow-x: auto;
    overscroll-behavior-inline: contain;
    border: var(--stroke-default) solid var(--border-subtle);
    border-radius: var(--radius-lg);
    background-color: var(--bg-surface);
  }

  .scaffold-row { transition: background-color var(--motion-hover); }
  .scaffold-row:hover { background-color: var(--bg-hover); }
  .scaffold-row[aria-selected="true"] { background-color: var(--bg-selected); }
  .scaffold-row[data-state="loading"] { color: var(--fg-muted); cursor: progress; }

  /* The identifying column survives horizontal scroll. Without it, a row
     scrolled to its fifth column belongs to nobody. */
  .scaffold-sticky {
    position: sticky;
    inset-inline-start: 0;
    background-color: var(--bg-surface);
  }

  .scaffold-card {
    --scaffold-card-shadow: var(--elevation-flat);

    display: flex;
    flex-direction: column;
    gap: var(--gap-related);
    padding: var(--pad-card);
    border: var(--stroke-default) solid var(--border-subtle);
    border-radius: var(--radius-xl);
    background-color: var(--bg-surface);
    box-shadow: var(--scaffold-card-shadow);
    transition: box-shadow var(--motion-hover);
  }

  .scaffold-card:hover { --scaffold-card-shadow: var(--elevation-card); }
}

@keyframes scaffold-spin {
  to { rotate: 1turn; }
}
"""

# Per-component utility strings for the classes that map to `scaffold-root`.
TW_ROOT_UTILITIES = {
    "Button":  "inline-flex items-center justify-center gap-fused min-h-tap "
               "px-inline-md py-block-md rounded-card text-ui cursor-pointer",
    "Control": "w-full min-h-tap px-inline-sm py-block-sm rounded-control text-body",
    "Badge":   "inline-flex items-center gap-fused px-inline-xs py-block-xs "
               "rounded-pill bg-sunken text-label text-muted whitespace-nowrap",
    "Skeleton": "block rounded-inner bg-sunken",
    "StateBlock": "flex flex-col gap-related items-center p-card-lg rounded-panel "
                  "bg-surface text-muted text-center border border-line-subtle",
    "Field":   "block max-w-narrow min-w-0 m-0 p-0 border-none",
    "List":    "w-full border-collapse text-ui text-default",
}


def tw_class(name: str, component: str) -> str:
    """One CSS Module class as the Tailwind stack writes it: its utilities,
    and the `styles/scaffold.css` class for a state they cannot express."""
    if name == "root":
        return f"{TW_SCAFFOLD_CLASS['root']} {TW_ROOT_UTILITIES.get(component, '')}".strip()
    parts = []
    if name in TW_SCAFFOLD_CLASS:
        parts.append(TW_SCAFFOLD_CLASS[name])
    if name in TW_UTILITIES:
        parts.append(TW_UTILITIES[name])
    return " ".join(parts)


def tailwindify(tsx: str, component: str) -> str:
    """Rewrite a CSS-Modules component as a Tailwind one.

    Layout, spacing, colour and type become utility classes. The state and
    variant tables become one plain class resolved by `styles/scaffold.css`,
    because a utility system has nothing to say about a state machine and
    faking one with arbitrary values would break Law 3.
    """
    out = re.sub(r"^import styles from '[^']*';\n", "", tsx, flags=re.M)
    # `styles.foo` becomes a string literal, leaving every cn() composition
    # intact so a caller's own `className` still reaches the element.
    out = re.sub(r"styles\.(\w+)", lambda m: f"'{tw_class(m.group(1), component)}'", out)
    # cn('x') with nothing to compose is just 'x'.
    out = re.sub(r"cn\('([^']*)'\)", lambda m: f"'{m.group(1)}'", out)
    # Having collapsed those, cn may now be unreferenced — and an unused
    # import is a compile error under noUnusedLocals.
    body = re.sub(r"^import [^;]*;\n", "", out, flags=re.M)
    # `className={'x'}` is just `className="x"`.
    out = re.sub(r"className=\{'([^']*)'\}",
                 lambda m: f'className="{m.group(1)}"', out)
    if "cn(" not in body:
        out = re.sub(r"^import \{ cn \} from '[^']*';\n", "", out, flags=re.M)
        out = re.sub(r"^(import \{ )cn, ", lambda m: m.group(1), out, flags=re.M)
        out = re.sub(r"^(import \{ [^}]*?), cn(,? )",
                     lambda m: m.group(1) + m.group(2), out, flags=re.M)
    return out


# ---------------------------------------------------------------------------
# Vue 3 (--framework vue)
# ---------------------------------------------------------------------------
# The same kit and the same screens as single-file components: `<script
# setup lang="ts">`, the React props as `defineProps`, its callbacks as
# `defineEmits`, `v-model` (`defineModel`) where the React control takes a
# value, `<slot />` where it takes children. Each CSS Module's rules go in a
# `<style scoped>` block inside `@layer components`, unchanged but for the
# root's class (stack-frameworks.md §1, §3). Vue 3.5 or newer: the form's
# summary is a `useTemplateRef`.

def vue_attr(expr: str) -> str:
    """An expression in a double-quoted directive. Vue decodes the entities
    before it parses the expression, so `row["2fa"]` survives the quotes."""
    return expr.replace("&", "&amp;").replace('"', "&quot;")


def vue_text(text: str) -> str:
    """Literal text in a template: markup, and a `{{`, stay text."""
    return (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace("{{", "&#123;&#123;"))


def vue_static(value: str) -> str:
    """A static attribute's value."""
    return vue_text(value).replace('"', "&quot;")


def vue_comment(text: str, indent: str) -> str:
    return f"{indent}<!-- {text.replace('-->', '-- >')} -->"


def kebab(name: str) -> str:
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "-", name).lower()


def vue_sfc(script: str, template: str, style: str = "") -> str:
    out = (f'<script setup lang="ts">\n{script.strip()}\n</script>\n\n'
           f"<template>\n{template.rstrip()}\n</template>\n")
    if style:
        out += f"\n<style scoped>\n{style.rstrip()}\n</style>\n"
    return out


def vue_root(sheet: str, root: str) -> str:
    """A CSS Module's sheet with `.root` renamed. Vue puts a parent's scope
    attribute on a child component's root element as well ("by design",
    stack-frameworks.md §3), so a parent's `.root` would style every child
    whose root is a `.root` too."""
    return re.sub(r"\.root(?![\w-])", "." + root, sheet)


def sfc_tailwind(sfc: str, component: str, root: str, sheet: str) -> str:
    """The Tailwind stack's single-file component (Vue or Svelte): each class
    from the component's sheet becomes its utilities (`tw_class`), the
    layout primitives stay, and the `<style>` block goes, as the CSS Module
    does. Svelte's `class={['a b', className]}` is read like `class="a b"`."""
    own = set(re.findall(r"\.([A-Za-z][\w-]*)", sheet)) | {root}

    def names(text: str) -> str:
        return " ".join(n for n in (tw_class("root" if c == root else c, component) if c in own else c
                                    for c in text.split()) if n)

    out = re.sub(r'(?<![\w:-])class="([^"]*)"', lambda m: f'class="{names(m.group(1))}"', sfc)
    out = re.sub(r"(?<![\w:-])class=\{\['([^']*)'", lambda m: "class={['" + names(m.group(1)) + "'", out)
    return re.sub(r'\n<style(?: scoped)?(?: src="[^"]*")?>[\s\S]*?</style>\n', "", out)


VUE_BUTTON = vue_sfc("""\
/**
 * Every attribute the caller passes (`type`, `@click`, an aria attribute)
 * falls through to the <button> and wins over the defaults written here, as
 * React's `...rest` did; a `class` is merged.
 */
withDefaults(
  defineProps<{
    variant?: 'default' | 'primary' | 'ghost' | 'danger';
    size?: 'default' | 'sm';
    /** Shows the busy affordance AND blocks the click. Both, or neither. */
    loading?: boolean;
    disabled?: boolean;
  }>(),
  { variant: 'default', size: 'default', loading: false, disabled: false },
);
""", """\
  <button
    type="button"
    class="ui-button"
    :data-variant="variant === 'default' ? undefined : variant"
    :data-size="size === 'default' ? undefined : size"
    :data-state="loading ? 'loading' : undefined"
    :aria-busy="loading || undefined"
    :disabled="disabled || loading"
  >
    <span class="label"><slot /></span>
    <span v-if="loading" class="spinner" aria-hidden="true" />
  </button>
""", vue_root(BUTTON_CSS, "ui-button"))

VUE_FIELD = vue_sfc("""\
/**
 * The label / control / help / error quartet, wired so the accessible name
 * and the visible name cannot drift apart.
 *
 * This component owns the structure and the ids: the help is `${id}-help`,
 * the error `${id}-error`. The CONTROL in the slot carries `aria-describedby`
 * (from `describedBy`) and `aria-invalid`, because assistive tech reads them
 * on the control, not on a wrapper. The error is not a live region: the
 * form's summary announces a failed submit once and takes focus.
 */
withDefaults(
  defineProps<{
    id: string;
    label: string;
    /** Marked visually AND with the `required` attribute, or neither. */
    required?: boolean;
    /** Guidance shown before the user gets it wrong. */
    help?: string;
    /** Set only AFTER first blur, or the form scolds people as they type. */
    error?: string | null;
    disabled?: boolean;
    /**
     * A group of controls (radios, a date range): the label becomes a
     * `<legend>` with the id `${id}-label`, which the group's
     * `aria-labelledby` names, since a `<label for>` can name only one
     * control.
     */
    group?: boolean;
  }>(),
  { required: false, error: null, disabled: false, group: false },
);
""", """\
  <component
    :is="group ? 'fieldset' : 'div'"
    class="ui-field stack stack--tight"
    :data-state="error ? 'error' : undefined"
    :data-disabled="disabled || undefined"
  >
    <legend v-if="group" :id="id + '-label'" class="label groupLabel">
      {{ label }}<span v-if="required" class="required" aria-hidden="true">*</span>
    </legend>
    <label v-else :for="id" class="label">
      {{ label }}<span v-if="required" class="required" aria-hidden="true">*</span>
    </label>

    <div class="control"><slot /></div>

    <p v-if="help" :id="id + '-help'" class="help">{{ help }}</p>

    <p v-if="error" :id="id + '-error'" class="error">{{ error }}</p>
  </component>
""", vue_root(FIELD_CSS, "ui-field"))

VUE_DESCRIBED_BY = """\
/** The ids a control puts in its `aria-describedby`: help first, then the
 *  error, so a screen reader hears the guidance before the complaint. They
 *  are the ids Field.vue gives the two. */
export function describedBy(id: string, help?: string, error?: string | null): string | undefined {
  const ids = [help ? `${id}-help` : null, error ? `${id}-error` : null].filter(Boolean);
  return ids.length > 0 ? ids.join(' ') : undefined;
}
"""

# Each control is one element that every attribute the caller passes lands
# on (`v-bind="$attrs"`, last, so the caller's win), with `inheritAttrs: false`
# so they land there once. The seven share Control.css, scoped in each.
VUE_CONTROL_DOC = """\
/**
 * The primitive input surfaces: one element each, which every attribute the
 * caller passes lands on, so a caller can attach whatever form library it
 * likes. `v-model` is the value.
 */
defineOptions({ inheritAttrs: false });
"""
VUE_CONTROL_STYLE = '\n<style scoped src="./Control.css"></style>\n'


def _vue_control(script: str, template: str) -> str:
    return vue_sfc(VUE_CONTROL_DOC + script, template) + VUE_CONTROL_STYLE


VUE_CONTROLS = {
    "TextInput": _vue_control("""\
const model = defineModel<string>();
""", """\
  <input v-model="model" class="ui-control" v-bind="$attrs">
"""),
    "NumberInput": _vue_control("""\
/** The number the input reads (`valueAsNumber`), or null once it is emptied. */
const model = defineModel<number | null>();

function read(event: Event) {
  const value = (event.target as HTMLInputElement).valueAsNumber;
  model.value = Number.isNaN(value) ? null : value;
}
""", """\
  <input
    type="number"
    inputmode="decimal"
    class="ui-control numeric"
    :value="model ?? ''"
    v-bind="$attrs"
    @input="read"
  >
"""),
    "TextArea": _vue_control("""\
const model = defineModel<string>();
""", """\
  <textarea v-model="model" rows="4" class="ui-control textarea" v-bind="$attrs" />
"""),
    "Select": _vue_control("""\
const model = defineModel<string | string[]>();
""", """\
  <select v-model="model" class="ui-control" v-bind="$attrs">
    <slot />
  </select>
"""),
    "Toggle": _vue_control("""\
defineProps<{ id: string; label: string }>();
const model = defineModel<boolean>();
""", """\
  <span class="toggle">
    <input :id="id" v-model="model" type="checkbox" class="toggleInput" v-bind="$attrs">
    <label class="toggleLabel" :for="id">{{ label }}</label>
  </span>
"""),
    "RadioGroup": _vue_control("""\
withDefaults(
  defineProps<{
    name: string;
    options: readonly string[];
    disabled?: boolean;
    /** The id of the group's name: a `<legend>`, from `<Field group>`. */
    labelledBy?: string;
    /** The ids of the help and the error, as `describedBy` builds them. */
    describedBy?: string;
    invalid?: boolean;
    /** The group says so (`aria-required`) and so does each radio. */
    required?: boolean;
  }>(),
  { disabled: false, labelledBy: undefined, describedBy: undefined, invalid: false, required: false },
);
const model = defineModel<string | null>({ default: null });
""", """\
  <div
    class="options"
    role="radiogroup"
    :aria-labelledby="labelledBy"
    :aria-describedby="describedBy"
    :aria-invalid="invalid || undefined"
    :aria-required="required || undefined"
    v-bind="$attrs"
  >
    <label v-for="option in options" :key="option" class="option">
      <input
        v-model="model"
        type="radio"
        :name="name"
        :value="option"
        :disabled="disabled"
        :required="required"
        class="toggleInput"
      >
      {{ option }}
    </label>
  </div>
"""),
    "ControlStub": _vue_control("""\
/** A control this scaffold deliberately did not guess at. It renders as an
 *  obvious placeholder so it cannot be mistaken for finished work. */
defineProps<{ control: string; reason: string }>();
""", """\
  <span class="stub" data-state="error" v-bind="$attrs">TODO({{ control }}): {{ reason }}</span>
"""),
}

VUE_BADGE = vue_sfc("""\
/**
 * A status pill. Tone is a PROP, not a lookup from the value — the mapping
 * from `status` to tone is product knowledge and belongs at the call site,
 * where someone can see it and argue with it.
 */
withDefaults(
  defineProps<{ tone?: 'neutral' | 'accent' | 'success' | 'warning' | 'danger' }>(),
  { tone: 'neutral' },
);
""", """\
  <span class="ui-badge" :data-tone="tone === 'neutral' ? undefined : tone"><slot /></span>
""", vue_root(BADGE_CSS, "ui-badge"))

VUE_SKELETON = vue_sfc("""\
/**
 * A loading placeholder sized to the content it replaces: always pass the
 * real line count, or the page jumps when the data arrives. The width and
 * the lines are custom properties, the one legal inline style (Law 4).
 */
withDefaults(
  defineProps<{
    /** Width as a fraction of the container, 0-1. */
    width?: number;
    lines?: number;
  }>(),
  { width: 1, lines: 1 },
);
""", """\
  <span
    class="ui-skeleton"
    :style="{ '--skeleton-width': String(width), '--skeleton-lines': String(lines) }"
    aria-hidden="true"
  />
""", vue_root(SKELETON_CSS, "ui-skeleton"))

VUE_STATE_BLOCK = vue_sfc("""\
/**
 * `kind` drives the tone. These are DIFFERENT screens, not one screen with
 * different words — see screen-patterns.md section 12. The `action` slot is
 * the single action this state offers: two actions on an empty state is two
 * people disagreeing about what the user should do next.
 */
defineProps<{
  kind: 'first-run' | 'filtered' | 'error' | 'forbidden' | 'stale';
  headline: string;
  body?: string;
}>();
""", """\
  <div
    class="ui-state-block stack stack--related"
    :data-kind="kind"
    :role="kind === 'error' ? 'alert' : undefined"
  >
    <h2 class="headline">{{ headline }}</h2>
    <p v-if="body" class="body">{{ body }}</p>
    <div v-if="$slots.action" class="action"><slot name="action" /></div>
  </div>
""", vue_root(STATE_BLOCK_CSS, "ui-state-block"))

VUE_INDEX_KIT = """\
export { default as Button } from './Button/Button.vue';
export { default as Field } from './Field/Field.vue';
export { describedBy } from './Field/describedBy';
export { default as TextInput } from './Control/TextInput.vue';
export { default as NumberInput } from './Control/NumberInput.vue';
export { default as TextArea } from './Control/TextArea.vue';
export { default as Select } from './Control/Select.vue';
export { default as Toggle } from './Control/Toggle.vue';
export { default as RadioGroup } from './Control/RadioGroup.vue';
export { default as ControlStub } from './Control/ControlStub.vue';
export { default as Badge } from './Badge/Badge.vue';
export { default as Skeleton } from './Skeleton/Skeleton.vue';
export { default as StateBlock } from './StateBlock/StateBlock.vue';
"""


def vue_tag(tag: str, attrs: list[str], indent: str, body: str | None = None) -> str:
    inner = "".join(f"\n{indent}  {a}" for a in attrs)
    if body is None:
        return f"{indent}<{tag}{inner}\n{indent}/>"
    return f"{indent}<{tag}{inner}\n{indent}>\n{body}\n{indent}</{tag}>"


def vue_cell(cell: dict[str, Any]) -> str:
    """A list cell or a detail value: the Badge, or an interpolation."""
    if cell["element"]:
        tone = vue_attr(f"toneFor({cell['acc']})")
        return f'<Badge :tone="{tone}">{{{{ {cell["acc"]} }}}}</Badge>'
    return "{{ " + cell["jsx"] + " }}"


def vue_control(spec: dict[str, Any], indent: str = "        ") -> str:
    """One form control, as control_jsx writes it for React: the same ids,
    the same aria wiring, the same TODOs, in Vue's attribute syntax."""
    ctrl = spec["control"]
    name = spec["name"]
    q, err = js_string(name), member("errors", name)
    acc = member("values", name)
    fid = f"fieldId({q})"
    error_id = f"{err} ? {fid} + '-error' : undefined"
    common = [f':id="{vue_attr(fid)}"', f'name="{vue_static(name)}"', ':disabled="disabled"',
              f':aria-invalid="{vue_attr(f"Boolean({err}) || undefined")}"',
              f':aria-describedby="{vue_attr(error_id)}"',
              f':required="{str(spec.get("required", False)).lower()}"']

    def update(value: str = "value") -> str:
        return f'@update:model-value="{vue_attr(f"({value}) => emit({chr(39)}change{chr(39)}, {q}, {value})")}"'

    if ctrl in STUB_REASON:
        reason = STUB_REASON[ctrl]
        if spec.get("labelColumn"):
            reason += f"; it shows `{spec['labelColumn']}`"
        return f'{indent}<ControlStub control="{ctrl}" reason="{vue_static(reason)}" />'
    text_model = f':model-value="{vue_attr(f"String({acc} ?? {chr(39)}{chr(39)})")}"'
    if ctrl in ("textarea", "rich-text"):
        return vue_tag("TextArea", common + [text_model, update()], indent)
    if ctrl in ("select", "multi-select"):
        multi = ["multiple"] if ctrl == "multi-select" else []
        opts = spec.get("options") or []
        lines = []
        if not spec.get("required") and not multi:
            lines.append(f'{indent}  <option value="">Choose one</option>')
        lines += [f'{indent}  <option value="{vue_static(o)}">{vue_text(o)}</option>' for o in opts]
        if not opts and spec.get("labelColumn"):
            lines.append(vue_comment(f"TODO(options): one <option> per parent row, showing "
                                     f"`{spec['labelColumn']}`", indent + "  "))
        # A multiple select's v-model is the array (Codex on #176).
        model_value = f':model-value="{vue_attr(f"{acc} ?? []")}"' if multi else text_model
        return vue_tag("Select", multi + common + [model_value, update()], indent,
                       "\n".join(lines) or vue_comment("TODO(options): the closed set", indent + "  "))
    if ctrl == "radio-group":
        opts = "[" + ", ".join(js_string(o) for o in spec.get("options") or []) + "]"
        value = f"{acc} === null || {acc} === undefined ? null : String({acc})"
        return vue_tag("RadioGroup", [
            f'name="{vue_static(name)}"', f':model-value="{vue_attr(value)}"',
            f':options="{vue_attr(opts)}"', ':disabled="disabled"',
            f':labelled-by="{vue_attr(fid + " + " + chr(39) + "-label" + chr(39))}"',
            f':described-by="{vue_attr(error_id)}"',
            f':invalid="{vue_attr(f"Boolean({err})")}"',
            f':required="{str(spec.get("required", False)).lower()}"', update("next")], indent)
    if ctrl in ("switch", "checkbox"):
        return vue_tag("Toggle", [
            f':id="{vue_attr(fid)}"', f'label="{vue_static(spec["label"])}"',
            f':model-value="{vue_attr(f"Boolean({acc})")}"', ':disabled="disabled"',
            f':aria-invalid="{vue_attr(f"Boolean({err}) || undefined")}"',
            f':aria-describedby="{vue_attr(error_id)}"', update()], indent)
    if ctrl in ("number-input", "stepper", "percent-input", "currency-input"):
        extra = [f':{k}="{spec[k]}"' for k in ("min", "max") if k in spec]
        note = ""
        if ctrl == "currency-input":
            money = spec.get("money") or {}
            cur = money.get("currency") or "the currency"
            if money.get("storage") == "minor-units":
                scale = json.dumps(cur) if money.get("currency") else "currency"
                note = (f"TODO(money): stored in minor units of {cur}. Divide by "
                        f"minorUnitScale({scale}) on read, multiply on write, and keep the "
                        f"float out of the middle.")
            elif money.get("storage") == "decimal":
                extra.append('step="any"')
                note = (f"TODO(money): a decimal amount in {cur}; the database rounds to its "
                        f"scale. Parse permissively, format on blur, never while typing.")
            else:
                note = ("TODO(money): minor units or a decimal? Answer the `.money` question; "
                        "the two differ by the currency's scale on every read and write.")
        tag = vue_tag("NumberInput", common + extra + [
            f':model-value="{vue_attr(f"{acc} ?? null")}"', update()], indent)
        return (vue_comment(note, indent) + "\n" + tag) if note else tag
    if ctrl in ("readonly-text", "readonly-timestamp"):
        return vue_tag("TextInput", common + ["readonly", text_model], indent)
    input_type = {
        "email-input": "email", "url-input": "url", "tel-input": "tel",
        "password-input": "password", "date-picker": "date",
        "datetime-picker": "datetime-local", "time-picker": "time",
        "color-picker": "color",
    }.get(ctrl, "text")
    extra = []
    if "maxLength" in spec:
        extra.append(f':maxlength="{spec["maxLength"]}"')
    if "pattern" in spec:
        extra.append(f'pattern="{vue_static(spec["pattern"])}"')
    if ctrl == "password-input":
        extra.append('autocomplete="new-password"')
    note = ""
    if ctrl == "slug-input":
        extra.append('inputmode="url"')
        note = vue_comment("TODO(slug): derive from the title until the user edits this field "
                           "by hand, then stop — a slug that keeps changing breaks links.", indent) + "\n"
    return note + vue_tag("TextInput", [f'type="{input_type}"'] + common + extra
                          + [text_model, update()], indent)


VUE_CONTROL_IMPORT = {
    "textarea": "TextArea", "rich-text": "TextArea",
    "select": "Select", "multi-select": "Select",
    "radio-group": "RadioGroup",
    "switch": "Toggle", "checkbox": "Toggle",
    "number-input": "NumberInput", "stepper": "NumberInput",
    "percent-input": "NumberInput", "currency-input": "NumberInput",
}


def _vue_form_sections(table: dict[str, Any], model: dict[str, Any],
                       ans: Answers) -> tuple[str, set[str]]:
    """The form's fieldsets, as _form_sections writes React's."""
    specs = {s["name"]: s for s in
             (field_spec(c, table, model, ans) for c in table["columns"]
              if ans.in_form(table, c))}
    groups = ans.groups(table, table["screens"].get("field_groups")
                        or [{"legend": "Details", "fields": list(specs)}])
    sections: list[str] = []
    kit: set[str] = {"Button"}
    for g in groups:
        fields = [f for f in g.get("fields", []) if f in specs]
        if not fields:
            continue
        body = []
        for f in fields:
            s = specs[f]
            kit.add(VUE_CONTROL_IMPORT.get(s["control"], "TextInput")
                    if s["control"] not in STUB_REASON else "ControlStub")
            review = (vue_comment(f"review: {s['review']}", "        ") + "\n"
                      if s.get("review") else "")
            err = member("errors", f)
            if s["control"] in ("switch", "checkbox"):
                # A toggle is its own label; it gets the error below it, with
                # the id the control's aria-describedby names.
                error_id = vue_attr(f"fieldId({js_string(f)}) + '-error'")
                body.append(
                    f'{review}        <div class="field" :data-state="{vue_attr(f"{err} ? {chr(39)}error{chr(39)} : undefined")}">\n'
                    f"{vue_control(s, '          ')}\n"
                    f'          <p v-if="{vue_attr(err)}" :id="{error_id}" class="fieldError">\n'
                    f"            {{{{ {err} }}}}\n"
                    f"          </p>\n"
                    f"        </div>")
                continue
            kit.add("Field")
            attrs = [f':id="{vue_attr(f"fieldId({js_string(f)})")}"',
                     f'label="{vue_static(s["label"])}"',
                     f':required="{str(s.get("required", False)).lower()}"',
                     f':error="{vue_attr(f"{err} ?? null")}"', ':disabled="disabled"']
            if s["control"] == "radio-group":
                attrs.append("group")
            body.append(review + vue_tag("Field", attrs, "        ", vue_control(s, "          ")))
        sections.append(
            f'      <fieldset class="group" :disabled="disabled">\n'
            f'        <legend class="legend">{vue_text(g.get("legend", "Details"))}</legend>\n'
            + "\n".join(body) + "\n      </fieldset>")
    return "\n\n".join(sections) or "      <!-- no writable fields -->", kit


def emit_vue_form(table: dict[str, Any], model: dict[str, Any], ans: Answers) -> str:
    name = table["name"]
    Entity = pascal(singular(name))
    sections, kit = _vue_form_sections(table, model, ans)
    script = Template("""\
import { computed, ref, useTemplateRef, watch } from 'vue';
import { $kit } from '../../ui';
import type { ${Entity}Draft } from './$camel.types';

/**
 * The $lower_entity form.
 *
 * Three UX rules this markup encodes, all of which generators skip:
 *
 * 1. VALIDATION TIMING. `errors` is rendered whenever it is set; it is the
 *    CALLER's job not to set it until a field has been blurred once.
 * 2. THE ERROR SUMMARY comes first in the DOM and takes focus, once per
 *    submit attempt, because on a long form the invalid field is usually
 *    off-screen. Each entry links to its field.
 * 3. REQUIRED IS MARKED BOTH WAYS. The asterisk is decorative and hidden from
 *    assistive tech; the `required` attribute is what actually announces it.
 *
 * Still yours to do: the unsaved-changes guard (block the route change while
 * `dirty`), and autosave if this form is long enough to deserve it. See
 * screen-patterns.md section 13.
 */
const props = withDefaults(
  defineProps<{
    values: Partial<${Entity}Draft>;
    errors: Partial<Record<keyof ${Entity}Draft, string>>;
    /** Blocks every control AND the submit button, together. */
    disabled?: boolean;
    submitting?: boolean;
    /** Set when the user has changed something and not saved it. */
    dirty?: boolean;
    /** A form-level failure: the save was rejected as a whole. */
    submitError?: string | null;
  }>(),
  { disabled: false, submitting: false, dirty: false, submitError: null },
);

const emit = defineEmits<{
  change: [name: keyof ${Entity}Draft, value: unknown];
  submit: [];
  cancel: [];
}>();

const fieldId = (name: string) => '$camel-' + name;

const invalid = computed(() => Object.entries(props.errors).filter(([, message]) => Boolean(message)));
const summary = useTemplateRef<HTMLDivElement>('summary');
const attempt = ref(0);
let focusedFor = 0;

// After a submit attempt that failed validation, move focus to the summary:
// once per attempt, whether or not the error count changed. The caller sets
// `errors` in its `submit` handler or, validating asynchronously, sets
// `submitting` while it runs. `flush: 'post'` runs this after the update that
// renders them, so the summary exists. A save that came back clean consumes
// the attempt, so an error that appears later, from a blur, does not pull
// focus to the summary.
watch(
  [attempt, () => invalid.value.length, () => props.submitting],
  ([tries, count, busy]) => {
    if (tries > focusedFor && count > 0) {
      focusedFor = tries;
      summary.value?.focus();
    } else if (!busy && count === 0) {
      focusedFor = tries;
    }
  },
  { flush: 'post' },
);

function submit() {
  attempt.value += 1;
  emit('submit');
}
""").safe_substitute(Entity=Entity, camel=camel(name), kit=", ".join(sorted(kit)),
                     lower_entity=singular(name.replace("_", " ")))
    template = """\
  <form class="stack stack--separate" novalidate @submit.prevent="submit">
    <div v-if="invalid.length > 0" ref="summary" class="summary" role="alert" tabindex="-1">
      <p class="summaryTitle">
        {{ invalid.length === 1 ? 'One field needs attention' : String(invalid.length) + ' fields need attention' }}
      </p>
      <ul class="summaryList">
        <li v-for="[name, message] in invalid" :key="name">
          <a class="summaryLink" :href="'#' + fieldId(name)">{{ String(message) }}</a>
        </li>
      </ul>
    </div>

    <p v-if="submitError" class="submitError" role="alert">
      {{ submitError }}
    </p>

""" + "\n".join(line[2:] for line in sections.split("\n")) + """

    <div class="cluster cluster--tight">
      <Button type="submit" variant="primary" :loading="submitting" :disabled="disabled">
        Save
      </Button>
      <Button type="button" variant="ghost" :disabled="submitting" @click="emit('cancel')">
        {{ dirty ? 'Discard changes' : 'Cancel' }}
      </Button>
    </div>
  </form>
"""
    return vue_sfc(script, template, vue_root(FORM_CSS, kebab(f"{Entity}Form")))


def _vue_imports(cells: list[dict[str, Any]], kit: list[str], Entities: str,
                 states: tuple[str, ...]) -> str:
    out = f"import {{ {', '.join(kit)} }} from '../../ui';\n" + _helper_imports(cells, set())
    return out + "".join(f"import {Entities}{s} from './{Entities}{s}.vue';\n" for s in states)


def emit_vue_list(table: dict[str, Any], model: dict[str, Any], ans: Answers) -> str:
    name = table["name"]
    Entity = pascal(singular(name))
    Entities = pascal(name)
    title = ans.title(table)
    layout = ans.layout(table)
    pk = table["primary_key"][0] if table["primary_key"] else "id"
    human = name.replace("_", " ")
    Title = human[:1].upper() + human[1:]
    root = kebab(f"{Entities}List")
    cols = [c for c in table["columns"] if c["name"] in ans.list_columns(table)] or table["columns"][:1]
    cells = {c["name"]: cell_render(c, "row", table, ans) for c in cols}
    href = vue_attr(f"{js_string('/' + name + '/')} + String({member('row', pk)})")
    key = vue_attr(f"String({member('row', pk)})")

    if layout == "table":
        head = "\n".join(
            f'            <th class="{"th sticky" if c["name"] == title else "th"}" scope="col">\n'
            f"              {vue_text(c['ui'].get('label', c['name']))}\n"
            f"            </th>" for c in cols)
        body = []
        for c in cols:
            cell = cells[c["name"]]
            cls = " ".join(["td"] + ([cell["class"]] if cell["class"] else [])
                           + (["sticky"] if c["name"] == title else []))
            inner = (f'<a class="link" :href="{href}">{vue_cell(cell)}</a>'
                     if c["name"] == title else vue_cell(cell))
            body.append(f'            <td class="{cls}">{inner}</td>')
        rows = Template("""\
    <div class="scroller" tabindex="0" role="region" aria-label="$Title, scrollable table">
      <table class="$root">
        <thead class="head">
          <tr>
$head
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in state.rows" :key="$key" class="row">
$body
          </tr>
        </tbody>
      </table>
    </div>""").safe_substitute(Title=vue_static(Title), root=root, head=head, key=key,
                               body="\n".join(body))
    else:
        grid = "grid grid--min-lg" if layout == "feed" else "grid grid--min-sm"
        meta = "\n".join(
            f"            <div>\n"
            f'              <dt class="cardMeta">{vue_text(c["ui"].get("label", c["name"]))}</dt>\n'
            f"              <dd>{vue_cell(cells[c['name']])}</dd>\n"
            f"            </div>" for c in cols if c["name"] != title)
        title_expr = (vue_cell(cells[title]) if title in cells
                      else "{{ String(" + member("row", pk) + ") }}")
        rows = Template("""\
    <ul class="$grid">
      <li v-for="row in state.rows" :key="$key">
        <article class="card">
          <h2 class="cardTitle">
            <a class="cardLink" :href="$href">
              $title_expr
            </a>
          </h2>
          <dl class="stack stack--fused">
$meta
          </dl>
        </article>
      </li>
    </ul>""").safe_substitute(grid=grid, key=key, href=href, title_expr=title_expr, meta=meta)

    kit = (["Badge"] if any(c["element"] for c in cells.values()) else []) + ["Button"]
    script = Template("""\
${imports}import type { ${Entity}ListState } from './$camel.types';

/**
 * $human, as a $layout.
 *
 * $layout_why
 *
 * This component takes its rows as a prop and knows nothing about fetching.
 * That is deliberate: cache keys, realtime and optimistic writes are product
 * decisions, and a scaffold has no business guessing at them.
 */
defineProps<{ state: ${Entity}ListState }>();

const emit = defineEmits<{
  /** The single primary action offered by the first-run empty state. */
  create: [];
  /** Clears whatever produced the filtered-empty state. */
  clearFilters: [];
}>();
""").safe_substitute(
        imports=_vue_imports(list(cells.values()), kit, Entities,
                             ("Empty", "Error", "FilteredEmpty", "Forbidden", "Loading")),
        Entity=Entity, camel=camel(name), human=human, layout=layout,
        layout_why=table["screens"].get("index_layout_signal", ""))
    template = Template("""\
  <${Entities}Loading v-if="state.status === 'loading'" />
  <${Entities}Error v-else-if="state.status === 'error'" :error="state.error" @retry="state.retry()" />
  <${Entities}Forbidden v-else-if="state.status === 'forbidden'" />
  <!-- Two different screens, not one screen with two strings. "Nothing here
       yet, make the first one" and "your filter matched nothing, clear it"
       ask the user to do opposite things. -->
  <${Entities}FilteredEmpty
    v-else-if="state.rows.length === 0 && state.filtered"
    @clear-filters="emit('clearFilters')"
  />
  <${Entities}Empty v-else-if="state.rows.length === 0" @create="emit('create')" />
  <section v-else class="stack stack--separate" aria-labelledby="$camel-heading">
    <header class="cluster cluster--between">
      <h1 id="$camel-heading" class="heading">
        $Title
      </h1>
      <Button variant="primary" @click="emit('create')">
        New $lower_entity
      </Button>
    </header>

    <p v-if="state.stale" class="stale" role="status">
      Showing the last known data while this refreshes.
    </p>

$rows
  </section>
""").safe_substitute(Entities=Entities, camel=camel(name), Title=vue_text(Title),
                     lower_entity=vue_text(singular(human)), rows=rows)
    sheet = LIST_CSS + (DATA_TABLE_CSS if layout == "table" else CARD_GRID_CSS)
    return vue_sfc(script, template, vue_root(sheet, root))


def emit_vue_detail(table: dict[str, Any], model: dict[str, Any], ans: Answers) -> str:
    name = table["name"]
    Entity = pascal(singular(name))
    Entities = pascal(name)
    title = ans.title(table)
    pk = table["primary_key"][0] if table["primary_key"] else "id"
    rows, cells = [], []
    for c in table["columns"]:
        if not c["ui"].get("placement", {}).get("detail") or c["name"] == title:
            continue
        cell = cell_render(c, "state.record", table, ans)
        cells.append(cell)
        rows.append(
            f'        <div class="pair">\n'
            f'          <dt class="term">{vue_text(c["ui"].get("label", c["name"]))}</dt>\n'
            f'          <dd class="value">{vue_cell(cell)}</dd>\n'
            f"        </div>")
    related = [vue_comment(f"TODO({r['control']}): {r['kind']} to `{r['to']}`"
                           + (f" via `{r['via']}`" if r.get("via") else "")
                           + f". {r.get('signal', '')}", "      ")
               for r in table.get("relationships", [])
               if r["kind"] in ("one-to-many", "many-to-many")]
    placeholder_note = ""
    if table["screens"].get("title_is_placeholder"):
        placeholder_note = (
            "\n *\n * TODO(title): nothing in this table looks like a title, so the\n"
            " * primary key is standing in. A uuid in an h1 is not a heading.\n"
            " * Answer the `.title_column` question and come back.")
    title_expr = ("{{ state.record." + title + " }}"
                  if title and re.fullmatch(r"[A-Za-z_$][\w$]*", title)
                  else "{{ String(" + member("state.record", pk) + ") }}")
    kit = (["Badge"] if any(c["element"] for c in cells) else []) + ["Button"]
    script = Template("""\
${imports}import type { ${Entity}DetailState } from './$camel.types';

/**
 * One $lower_entity.
 *
 * The layout is `.with-sidebar`: the record's own fields in the main pane, its
 * actions and metadata in the rail. The rail wraps underneath at a CONTENT
 * threshold rather than a viewport breakpoint, so this page is correct inside
 * a drawer and inside a 288px column without knowing it.$placeholder_note
 */
defineProps<{ state: ${Entity}DetailState }>();

const emit = defineEmits<{ edit: []; delete: [] }>();
""").safe_substitute(
        imports=_vue_imports(cells, kit, Entities, ("Error", "Forbidden", "Loading")),
        Entity=Entity, camel=camel(name), placeholder_note=placeholder_note,
        lower_entity=singular(name.replace("_", " ")))
    template = Template("""\
  <${Entities}Loading v-if="state.status === 'loading'" />
  <${Entities}Error v-else-if="state.status === 'error'" :error="state.error" @retry="state.retry()" />
  <${Entities}Forbidden v-else-if="state.status === 'forbidden'" />
  <article v-else class="with-sidebar" aria-labelledby="$camel-detail-heading">
    <div class="with-sidebar__main stack stack--separate">
      <h1 id="$camel-detail-heading" class="title">
        $title_expr
      </h1>

      <dl class="fields">
$rows
      </dl>
$related
    </div>

    <aside class="with-sidebar__rail stack stack--related" aria-label="Actions">
      <Button variant="primary" @click="emit('edit')">
        Edit
      </Button>
      <Button variant="danger" @click="emit('delete')">
        Delete
      </Button>
      <!-- TODO(copy): a delete confirmation must name the record and state
           what else disappears with it. "Are you sure?" is not that. See
           screen-patterns.md section 8. -->
    </aside>
  </article>
""").safe_substitute(Entities=Entities, camel=camel(name), title_expr=title_expr,
                     rows="\n".join(rows) or "        <!-- no detail fields -->",
                     related=("\n" + "\n".join(related)) if related else "")
    return vue_sfc(script, template, vue_root(DETAIL_CSS, kebab(f"{Entity}Detail")))


VUE_DETAIL_STATE = Template("""
/** The detail view's state: the list's, with one record. */
export type ${Entity}DetailState =
  | { status: 'loading' }
  | { status: 'error'; error: Error; retry: () => void }
  | { status: 'forbidden' }
  | { status: 'ready'; record: $Entity };
""")


def emit_vue_states(table: dict[str, Any], model: dict[str, Any],
                    ans: Answers) -> dict[str, str]:
    """The six states, one component each: Vue's is one per file."""
    name = table["name"]
    human = name.replace("_", " ")
    empty = ans.empty(table)
    cols = len(ans.list_columns(table)) or 3
    forbidden_note = (
        "Row-level security is on for this table, so this is a real state: the\n"
        " * query succeeded and returned nothing because the policy filtered\n"
        " * everything out. Rendering that as 'no records' tells the user their\n"
        " * data is gone."
        if ans.rls(table) else
        "RLS was reported as off, so this should be unreachable today. It is\n"
        " * generated anyway, because 'we will add RLS later' is always true and\n"
        " * retrofitting this state means touching every list in the app.")

    def block(doc: str, emits: str, kind: str, headline: str, body: str, note: str | None,
              action: tuple[str, str, str] | None, props: str = "", bound: str | None = None) -> str:
        """`action` is (variant, event, label). `body` is copy, the answers'
        among it, so it is always text; `bound` is an expression instead
        (CodeRabbit on #176: copy that began with `:` became a directive)."""
        script = "import { Button, StateBlock } from '../../ui';\n" if action else \
                 "import { StateBlock } from '../../ui';\n"
        script += f"\n/**\n * {doc}\n */\n" + props + emits
        body_attr = f':body="{vue_attr(bound)}"' if bound else f'body="{vue_static(body)}"'
        tag = (f'  <StateBlock\n    kind="{kind}"\n    headline="{vue_static(headline)}"\n'
               f"    {body_attr}\n  >\n")
        if action:
            variant, event, label = action
            tag += (f"    <template #action>\n"
                    f'      <Button variant="{variant}" @click="emit({js_string(event)})">\n'
                    f"        {vue_text(label)}\n      </Button>\n    </template>\n")
        tag += "  </StateBlock>\n"
        return vue_sfc(script, (vue_comment(note, "  ") + "\n" if note else "") + tag)

    return {
        "Empty": block(f"No {human} have ever existed. The most-seen screen in the app on day one.",
                       "const emit = defineEmits<{ create: [] }>();\n", "first-run",
                       empty["headline"], empty["body"] or f"TODO(copy): what {human} are for.",
                       "TODO(copy): say what this screen will hold and why it is worth filling "
                       "in. One sentence. \"No data\" is the absence of copy, not copy.",
                       ("primary", "create", empty["action"])),
        "FilteredEmpty": block(
            "A filter or a search matched nothing. A DIFFERENT screen from the empty one:\n"
            " * the records exist, this query just missed them, so the action is \"clear the\n"
            " * filter\", never \"create a record\".",
            "const emit = defineEmits<{ clearFilters: [] }>();\n", "filtered",
            f"No {human} match those filters",
            "Try a broader search, or clear the filters to see everything.",
            "TODO(copy): name the filters that are on, so the user can see what to "
            "relax without hunting for it.", ("ghost", "clearFilters", "Clear filters")),
        "Error": block(
            "The request failed. Always offer the retry — an error with no way forward\n"
            " * is a dead end, and users reload the whole app instead.",
            "const emit = defineEmits<{ retry: [] }>();\n", "error",
            f"Something went wrong loading {human}", "",
            f"TODO(copy): say what failed in the user's terms, not the transport's. "
            f"\"We could not load your {human}\" beats \"Request failed\".",
            ("primary", "retry", "Try again"), "defineProps<{ error?: Error }>();\n\n",
            bound="error?.message"),
        "Forbidden": block(
            f"The user is not allowed to see these rows.\n *\n * {forbidden_note}",
            "", "forbidden", f"You do not have access to {human}",
            "Ask an administrator if you think this is a mistake.",
            "TODO(copy): say who to ask. A permission wall with no route onward is a "
            "support ticket. Do NOT reveal whether any records exist.", None),
        "Stale": block(
            "Data on screen is known to be out of date — a realtime event arrived, or a\n"
            " * background revalidation failed. Shown ABOVE the stale rows rather than\n"
            " * replacing them: taking correct-a-moment-ago data away is worse than\n"
            " * labelling it.",
            "const emit = defineEmits<{ refresh: [] }>();\n", "stale", "This list has changed",
            f"Someone else updated these {human} while you were reading.", None,
            ("ghost", "refresh", "Refresh")),
        "Loading": vue_sfc("""\
import { Skeleton } from '../../ui';

/**
 * A skeleton shaped like the real table: same column count, same row height.
 * A spinner would be less work and would also let the page jump when the data
 * lands, moving whatever the user was about to click.
 */
withDefaults(defineProps<{ rows?: number }>(), { rows: 5 });
""", Template("""\
  <div class="loading" role="status" aria-live="polite">
    <span class="visually-hidden">Loading $human</span>
    <div v-for="index in rows" :key="index" class="loadingRow">
      <Skeleton v-for="cell in $cols" :key="cell" :width="cell === 1 ? 0.8 : 0.5" />
    </div>
  </div>
""").safe_substitute(human=vue_text(human), cols=cols), STATES_CSS),
    }


def emit_vue_index(table: dict[str, Any]) -> str:
    name = table["name"]
    Entity = pascal(singular(name))
    Entities = pascal(name)
    parts = [f"{Entities}List", f"{Entity}Detail", f"{Entity}Form"] + [
        f"{Entities}{s}" for s in ("Empty", "FilteredEmpty", "Loading", "Error", "Forbidden", "Stale")]
    return ("".join(f"export {{ default as {p} }} from './{p}.vue';\n" for p in parts)
            + f"export type {{ {Entity}, {Entity}Draft, {Entity}ListState, {Entity}DetailState }} "
              f"from './{camel(name)}.types';\n"
            + f"export {{ {camel(name)}Fields, {camel(name)}Groups, {camel(name)}ListColumns }} "
              f"from './{camel(name)}.fields';\n")


def build_vue_files(model: dict[str, Any], ans: Answers, stack: str,
                    entities: set[str] | None) -> dict[str, str]:
    """The kit and the screens as Vue single-file components; everything
    that is not a component (types, fields, format, the server's schemas)
    is the React scaffold's own file."""
    css = stack == "css-modules"

    def sfc(path: str, text: str, component: str, root: str, sheet: str) -> None:
        files[path] = text if css else sfc_tailwind(text, component, root, sheet)

    files: dict[str, str] = {"lib/format.ts": FORMAT_TS, "ui/index.ts": VUE_INDEX_KIT,
                             "ui/Field/describedBy.ts": VUE_DESCRIBED_BY}
    if not css:
        files["styles/scaffold.css"] = SCAFFOLD_CSS
    for comp, text, sheet in (("Button", VUE_BUTTON, BUTTON_CSS), ("Field", VUE_FIELD, FIELD_CSS),
                              ("Badge", VUE_BADGE, BADGE_CSS), ("Skeleton", VUE_SKELETON, SKELETON_CSS),
                              ("StateBlock", VUE_STATE_BLOCK, STATE_BLOCK_CSS)):
        sfc(f"ui/{comp}/{comp}.vue", text, comp, f"ui-{kebab(comp)}", sheet)
    if css:
        files["ui/Control/Control.css"] = vue_root(CONTROL_CSS, "ui-control")
    for comp, text in VUE_CONTROLS.items():
        sfc(f"ui/Control/{comp}.vue", text, "Control", "ui-control", CONTROL_CSS)

    for table in model["tables"]:
        if table["kind"] == "join" or (entities and table["name"] not in entities):
            continue
        name = table["name"]
        Entity = pascal(singular(name))
        Entities = pascal(name)
        base = f"features/{name}"
        files[f"{base}/{camel(name)}.types.ts"] = (emit_types(table, model, ans)
                                                   + VUE_DETAIL_STATE.substitute(Entity=Entity))
        files[f"{base}/{camel(name)}.fields.ts"] = emit_fields(table, model, ans)
        list_sheet = LIST_CSS + (DATA_TABLE_CSS if ans.layout(table) == "table" else CARD_GRID_CSS)
        sfc(f"{base}/{Entities}List.vue", emit_vue_list(table, model, ans), "List",
            kebab(f"{Entities}List"), list_sheet)
        sfc(f"{base}/{Entity}Detail.vue", emit_vue_detail(table, model, ans), "Detail",
            kebab(f"{Entity}Detail"), DETAIL_CSS)
        sfc(f"{base}/{Entity}Form.vue", emit_vue_form(table, model, ans), "Form",
            kebab(f"{Entity}Form"), FORM_CSS)
        for state, text in emit_vue_states(table, model, ans).items():
            sfc(f"{base}/{Entities}{state}.vue", text, "States", "", STATES_CSS)
        files[f"{base}/index.ts"] = emit_vue_index(table)
        files[f"server/{name}.schema.ts"] = emit_schema_zod(table, model, ans)
        files[f"server/{name}_schema.py"] = emit_schema_pydantic(table, model, ans)
    return files


# ---------------------------------------------------------------------------
# Svelte 5 (--framework svelte)
# ---------------------------------------------------------------------------
# The same kit and the same screens as Svelte 5 components: runes (`$props()`,
# `$state`, `$derived`, `$effect`), snippets for children (`{@render
# children()}`), callbacks as props, as React's are, and each CSS Module's
# rules in the component's `<style>` inside `@layer components`
# (stack-frameworks.md §1, §4). Svelte scopes a style to the component's own
# elements only, so the sheets keep `.root`; a rule that reaches a child
# component's element says so with `:global(...)`. `style:` sets only the
# skeleton's custom properties.

def svelte_text(text: str) -> str:
    """Literal text, or a quoted attribute's value: Svelte reads `{` in
    either as an expression."""
    return (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace("{", "&#123;").replace("}", "&#125;"))


def svelte_static(value: str) -> str:
    return svelte_text(value).replace('"', "&quot;")


def svelte_sfc(script: str, markup: str, style: str = "") -> str:
    body = "\n".join(("  " + line) if line else "" for line in script.strip().split("\n"))
    out = f'<script lang="ts">\n{body}\n</script>\n\n{markup.rstrip()}\n'
    if style:
        out += f"\n<style>\n{style.rstrip()}\n</style>\n"
    return out


def css_rules(sheet: str, keep: set[str]) -> str:
    """The rules of a sheet's `@layer components` block whose classes are all
    in `keep`, each with the comments before it: Svelte drops, and warns
    about, a selector nothing in the component can match."""
    start = sheet.index("@layer components {") + len("@layer components {")
    body = sheet[start:sheet.rindex("}")]
    kept, pending, i = [], "", 0
    while i < len(body):
        if body.startswith("/*", i):
            j = body.index("*/", i) + 2
            pending, i = pending + body[i:j], j
            continue
        if body[i].isspace():
            pending, i = pending + body[i], i + 1
            continue
        j = k = body.index("{", i)
        depth = 0
        while True:
            depth += {"{": 1, "}": -1}.get(body[k], 0)
            if depth == 0:
                break
            k += 1
        classes = set(re.findall(r"\.([A-Za-z][\w-]*)", body[i:j]))
        if classes and classes <= keep:
            kept.append(pending + body[i:k + 1])
        pending, i = "", k + 1
    return "@layer components {" + "".join(kept) + "\n}\n"


def svelte_sheet(markup: str, *sheets: str) -> str:
    """The rules of the sheets whose classes the screen's markup uses:
    Svelte drops, and warns about, the rest."""
    used: set[str] = set()
    for m in re.finditer(r"""class=(?:"([^"]*)"|\{\['([^']*)')""", markup):
        used.update((m.group(1) or m.group(2)).split())
    return "".join(css_rules(sheet, used) for sheet in sheets)


# The list's rows and headers have rules for states its markup does not
# render yet; Svelte compiles each in once the markup sets the attribute.
SVELTE_STATE_RULES = """\
<!-- The rules for a sorted column and a selected, loading, failed or disabled
     row wait for the markup to set aria-sort, aria-selected, data-state or
     data-disabled; Svelte compiles each one in when it does. -->
<!-- svelte-ignore css_unused_selector -->
"""


SVELTE_BUTTON = svelte_sfc("""\
import type { Snippet } from 'svelte';
import type { HTMLButtonAttributes } from 'svelte/elements';

/**
 * Every attribute the caller passes (`type`, `onclick`, an aria attribute)
 * comes after the defaults written here, so it wins, as React's `...rest`
 * did; a `class` joins the component's own.
 */
type Props = HTMLButtonAttributes & {
  variant?: 'default' | 'primary' | 'ghost' | 'danger';
  size?: 'default' | 'sm';
  /** Shows the busy affordance AND blocks the click. Both, or neither. */
  loading?: boolean;
  children?: Snippet;
};

let {
  variant = 'default',
  size = 'default',
  loading = false,
  disabled = false,
  class: className = '',
  children,
  ...rest
}: Props = $props();
""", """\
<button
  type="button"
  class={['root', className]}
  data-variant={variant === 'default' ? undefined : variant}
  data-size={size === 'default' ? undefined : size}
  data-state={loading ? 'loading' : undefined}
  aria-busy={loading || undefined}
  disabled={disabled || loading}
  {...rest}
>
  <span class="label">{@render children?.()}</span>
  {#if loading}
    <span class="spinner" aria-hidden="true"></span>
  {/if}
</button>
""", BUTTON_CSS)

SVELTE_FIELD = svelte_sfc("""\
import type { Snippet } from 'svelte';

/**
 * The label / control / help / error quartet, wired so the accessible name
 * and the visible name cannot drift apart.
 *
 * This component owns the structure and the ids: the help is `${id}-help`,
 * the error `${id}-error`. The CONTROL in `children` carries
 * `aria-describedby` (from `describedBy`) and `aria-invalid`, because
 * assistive tech reads them on the control, not on a wrapper. The error is
 * not a live region: the form's summary announces a failed submit once and
 * takes focus.
 */
type Props = {
  id: string;
  label: string;
  /** Marked visually AND with the `required` attribute, or neither. */
  required?: boolean;
  /** Guidance shown before the user gets it wrong. */
  help?: string;
  /** Set only AFTER first blur, or the form scolds people as they type. */
  error?: string | null;
  disabled?: boolean;
  /**
   * A group of controls (radios, a date range): the label becomes a
   * `<legend>` with the id `${id}-label`, which the group's
   * `aria-labelledby` names, since a `<label for>` can name only one
   * control.
   */
  group?: boolean;
  class?: string;
  children: Snippet;
};

let {
  id,
  label,
  required = false,
  help,
  error = null,
  disabled = false,
  group = false,
  class: className = '',
  children,
}: Props = $props();
""", """\
<svelte:element
  this={group ? 'fieldset' : 'div'}
  class={['root stack stack--tight', className]}
  data-state={error ? 'error' : undefined}
  data-disabled={disabled || undefined}
>
  {#if group}
    <legend class="label groupLabel" id={id + '-label'}>
      {label}{#if required}<span class="required" aria-hidden="true">*</span>{/if}
    </legend>
  {:else}
    <label class="label" for={id}>
      {label}{#if required}<span class="required" aria-hidden="true">*</span>{/if}
    </label>
  {/if}

  <div class="control">{@render children()}</div>

  {#if help}
    <p class="help" id={id + '-help'}>{help}</p>
  {/if}

  {#if error}
    <p class="error" id={id + '-error'}>{error}</p>
  {/if}
</svelte:element>
""", FIELD_CSS)

SVELTE_CONTROL_DOC = """\
/**
 * One of the primitive input surfaces: one element, which every attribute
 * the caller passes lands on, so a caller can attach whatever form library
 * it likes. The value and its callback are the caller's, as in React.
 */
"""

SVELTE_CONTROLS = {
    "TextInput": svelte_sfc("""\
import type { HTMLInputAttributes } from 'svelte/elements';

""" + SVELTE_CONTROL_DOC + """\
let { class: className = '', ...rest }: HTMLInputAttributes = $props();
""", """\
<input class={['root', className]} {...rest} />
""", css_rules(CONTROL_CSS, {"root"})),
    "NumberInput": svelte_sfc("""\
import type { HTMLInputAttributes } from 'svelte/elements';

""" + SVELTE_CONTROL_DOC + """\
let { class: className = '', ...rest }: HTMLInputAttributes = $props();
""", """\
<input type="number" inputmode="decimal" class={['root numeric', className]} {...rest} />
""", css_rules(CONTROL_CSS, {"root", "numeric"})),
    "TextArea": svelte_sfc("""\
import type { HTMLTextareaAttributes } from 'svelte/elements';

""" + SVELTE_CONTROL_DOC + """\
let { class: className = '', ...rest }: HTMLTextareaAttributes = $props();
""", """\
<textarea rows={4} class={['root textarea', className]} {...rest}></textarea>
""", css_rules(CONTROL_CSS, {"root", "textarea"})),
    "Select": svelte_sfc("""\
import type { HTMLSelectAttributes } from 'svelte/elements';

""" + SVELTE_CONTROL_DOC + """\
let { class: className = '', children, ...rest }: HTMLSelectAttributes = $props();
""", """\
<select class={['root', className]} {...rest}>
  {@render children?.()}
</select>
""", css_rules(CONTROL_CSS, {"root"})),
    "Toggle": svelte_sfc("""\
import type { HTMLInputAttributes } from 'svelte/elements';

""" + SVELTE_CONTROL_DOC + """\
type Props = HTMLInputAttributes & { id: string; label: string };

let { id, label, class: className = '', ...rest }: Props = $props();
""", """\
<span class={['toggle', className]}>
  <input {id} type="checkbox" class="toggleInput" {...rest} />
  <label class="toggleLabel" for={id}>{label}</label>
</span>
""", css_rules(CONTROL_CSS, {"toggle", "toggleInput", "toggleLabel"})),
    "RadioGroup": svelte_sfc("""\
type Props = {
  name: string;
  value: string | null;
  options: readonly string[];
  disabled?: boolean;
  onValueChange?: (next: string) => void;
  /** The id of the group's name: a `<legend>`, from `<Field group>`. */
  labelledBy?: string;
  /** The ids of the help and the error, as `describedBy` builds them. */
  describedBy?: string;
  invalid?: boolean;
  /** The group says so (`aria-required`) and so does each radio. */
  required?: boolean;
};

let { name, value, options, disabled, onValueChange, labelledBy, describedBy, invalid, required }: Props =
  $props();
""", """\
<div
  class="options"
  role="radiogroup"
  aria-labelledby={labelledBy}
  aria-describedby={describedBy}
  aria-invalid={invalid || undefined}
  aria-required={required || undefined}
>
  {#each options as option (option)}
    <label class="option">
      <input
        type="radio"
        {name}
        value={option}
        checked={value === option}
        {disabled}
        {required}
        class="toggleInput"
        onchange={() => onValueChange?.(option)}
      />
      {option}
    </label>
  {/each}
</div>
""", css_rules(CONTROL_CSS, {"options", "option", "toggleInput"})),
    "ControlStub": svelte_sfc("""\
/** A control this scaffold deliberately did not guess at. It renders as an
 *  obvious placeholder so it cannot be mistaken for finished work. */
let { control, reason }: { control: string; reason: string } = $props();
""", """\
<span class="stub" data-state="error">TODO({control}): {reason}</span>
""", css_rules(CONTROL_CSS, {"stub"})),
}

SVELTE_BADGE = svelte_sfc("""\
import type { Snippet } from 'svelte';
import type { HTMLAttributes } from 'svelte/elements';

/**
 * A status pill. Tone is a PROP, not a lookup from the value — the mapping
 * from `status` to tone is product knowledge and belongs at the call site,
 * where someone can see it and argue with it.
 */
type Props = HTMLAttributes<HTMLSpanElement> & {
  tone?: 'neutral' | 'accent' | 'success' | 'warning' | 'danger';
  children?: Snippet;
};

let { tone = 'neutral', class: className = '', children, ...rest }: Props = $props();
""", """\
<span class={['root', className]} data-tone={tone === 'neutral' ? undefined : tone} {...rest}>
  {@render children?.()}
</span>
""", BADGE_CSS)

SVELTE_SKELETON = svelte_sfc("""\
import type { HTMLAttributes } from 'svelte/elements';

/**
 * A loading placeholder sized to the content it replaces: always pass the
 * real line count, or the page jumps when the data arrives. The width and
 * the lines are custom properties (`style:`), the one legal inline style
 * (Law 4).
 */
type Props = HTMLAttributes<HTMLSpanElement> & {
  /** Width as a fraction of the container, 0-1. */
  width?: number;
  lines?: number;
};

let { width = 1, lines = 1, class: className = '', ...rest }: Props = $props();
""", """\
<span
  class={['root', className]}
  style:--skeleton-width={String(width)}
  style:--skeleton-lines={String(lines)}
  aria-hidden="true"
  {...rest}
></span>
""", SKELETON_CSS)

SVELTE_STATE_BLOCK = svelte_sfc("""\
import type { Snippet } from 'svelte';

/**
 * `kind` drives the tone. These are DIFFERENT screens, not one screen with
 * different words — see screen-patterns.md section 12. `action` is the
 * single action this state offers: two actions on an empty state is two
 * people disagreeing about what the user should do next.
 */
type Props = {
  kind: 'first-run' | 'filtered' | 'error' | 'forbidden' | 'stale';
  headline: string;
  body?: string;
  action?: Snippet;
  class?: string;
};

let { kind, headline, body, action, class: className = '' }: Props = $props();
""", """\
<div
  class={['root stack stack--related', className]}
  data-kind={kind}
  role={kind === 'error' ? 'alert' : undefined}
>
  <h2 class="headline">{headline}</h2>
  {#if body}
    <p class="body">{body}</p>
  {/if}
  {#if action}
    <div class="action">{@render action()}</div>
  {/if}
</div>
""", STATE_BLOCK_CSS)

SVELTE_INDEX_KIT = VUE_INDEX_KIT.replace(".vue';", ".svelte';")


def svelte_tag(tag: str, attrs: list[str], indent: str, body: str | None = None) -> str:
    inner = "".join(f"\n{indent}  {a}" for a in attrs)
    if body is None:
        return f"{indent}<{tag}{inner}\n{indent}/>"
    return f"{indent}<{tag}{inner}\n{indent}>\n{body}\n{indent}</{tag}>"


def svelte_control(spec: dict[str, Any], indent: str = "      ") -> str:
    """One form control, as control_jsx writes it for React; Svelte's
    expressions are JSX's, its attribute names HTML's."""
    ctrl = spec["control"]
    name = spec["name"]
    q, err = js_string(name), member("errors", name)
    acc = member("values", name)
    fid = f"fieldId({q})"
    error_id = f"{err} ? {fid} + '-error' : undefined"
    common = [f"id={{{fid}}}", f'name="{svelte_static(name)}"', "disabled={disabled}",
              f"aria-invalid={{Boolean({err}) || undefined}}", f"aria-describedby={{{error_id}}}",
              f"required={{{str(spec.get('required', False)).lower()}}}"]
    text_value = f"value={{String({acc} ?? '')}}"

    def on(event: str, read: str = "e.currentTarget.value") -> str:
        return f"on{event}={{(e) => onChange({q}, {read})}}"

    if ctrl in STUB_REASON:
        reason = STUB_REASON[ctrl]
        if spec.get("labelColumn"):
            reason += f"; it shows `{spec['labelColumn']}`"
        return f'{indent}<ControlStub control="{ctrl}" reason="{svelte_static(reason)}" />'
    if ctrl in ("textarea", "rich-text"):
        return svelte_tag("TextArea", common + [text_value, on("input")], indent)
    if ctrl in ("select", "multi-select"):
        multi = ["multiple"] if ctrl == "multi-select" else []
        opts = spec.get("options") or []
        lines = []
        if not spec.get("required") and not multi:
            lines.append(f'{indent}  <option value="">Choose one</option>')
        lines += [f"{indent}  <option value={{{json.dumps(o)}}}>{{{json.dumps(o)}}}</option>" for o in opts]
        if not opts and spec.get("labelColumn"):
            lines.append(vue_comment(f"TODO(options): one <option> per parent row, showing "
                                     f"`{spec['labelColumn']}`", indent + "  "))
        # A multiple select's value is the array, and so is what it sends (#176).
        value = ([f"value={{{acc} ?? []}}",
                  on("change", "Array.from(e.currentTarget.selectedOptions, (option) => option.value)")]
                 if multi else [text_value, on("change")])
        return svelte_tag("Select", multi + common + value, indent,
                          "\n".join(lines) or vue_comment("TODO(options): the closed set", indent + "  "))
    if ctrl == "radio-group":
        return svelte_tag("RadioGroup", [
            f'name="{svelte_static(name)}"',
            f"value={{{acc} === null || {acc} === undefined ? null : String({acc})}}",
            f"options={{{json.dumps(spec.get('options') or [])}}}", "disabled={disabled}",
            f"labelledBy={{{fid} + '-label'}}", f"describedBy={{{error_id}}}",
            f"invalid={{Boolean({err})}}", f"required={{{str(spec.get('required', False)).lower()}}}",
            f"onValueChange={{(next) => onChange({q}, next)}}"], indent)
    if ctrl in ("switch", "checkbox"):
        return svelte_tag("Toggle", [
            f"id={{{fid}}}", f'label="{svelte_static(spec["label"])}"',
            f"checked={{Boolean({acc})}}", "disabled={disabled}",
            f"aria-invalid={{Boolean({err}) || undefined}}", f"aria-describedby={{{error_id}}}",
            on("change", "e.currentTarget.checked")], indent)
    if ctrl in ("number-input", "stepper", "percent-input", "currency-input"):
        extra = [f"{k}={{{spec[k]}}}" for k in ("min", "max") if k in spec]
        note = ""
        if ctrl == "currency-input":
            money = spec.get("money") or {}
            cur = money.get("currency") or "the currency"
            if money.get("storage") == "minor-units":
                scale = json.dumps(cur) if money.get("currency") else "currency"
                note = (f"TODO(money): stored in minor units of {cur}. Divide by "
                        f"minorUnitScale({scale}) on read, multiply on write, and keep the "
                        f"float out of the middle.")
            elif money.get("storage") == "decimal":
                extra.append('step="any"')
                note = (f"TODO(money): a decimal amount in {cur}; the database rounds to its "
                        f"scale. Parse permissively, format on blur, never while typing.")
            else:
                note = ("TODO(money): minor units or a decimal? Answer the `.money` question; "
                        "the two differ by the currency's scale on every read and write.")
        tag = svelte_tag("NumberInput", common + extra + [
            f"value={{{acc} ?? ''}}",
            on("input", "Number.isNaN(e.currentTarget.valueAsNumber) ? null : e.currentTarget.valueAsNumber")],
            indent)
        return (vue_comment(note, indent) + "\n" + tag) if note else tag
    if ctrl in ("readonly-text", "readonly-timestamp"):
        return svelte_tag("TextInput", common + ["readonly", text_value], indent)
    input_type = {
        "email-input": "email", "url-input": "url", "tel-input": "tel",
        "password-input": "password", "date-picker": "date",
        "datetime-picker": "datetime-local", "time-picker": "time",
        "color-picker": "color",
    }.get(ctrl, "text")
    extra = []
    if "maxLength" in spec:
        extra.append(f"maxlength={{{spec['maxLength']}}}")
    if "pattern" in spec:
        extra.append(f"pattern={{{json.dumps(spec['pattern'])}}}")
    if ctrl == "password-input":
        extra.append('autocomplete="new-password"')
    note = ""
    if ctrl == "slug-input":
        extra.append('inputmode="url"')
        note = vue_comment("TODO(slug): derive from the title until the user edits this field "
                           "by hand, then stop — a slug that keeps changing breaks links.", indent) + "\n"
    return note + svelte_tag("TextInput", [f'type="{input_type}"'] + common + extra
                             + [text_value, on("input")], indent)


def _svelte_form_sections(table: dict[str, Any], model: dict[str, Any],
                          ans: Answers) -> tuple[str, set[str]]:
    """The form's fieldsets, as _form_sections writes React's."""
    specs = {s["name"]: s for s in
             (field_spec(c, table, model, ans) for c in table["columns"]
              if ans.in_form(table, c))}
    groups = ans.groups(table, table["screens"].get("field_groups")
                        or [{"legend": "Details", "fields": list(specs)}])
    sections: list[str] = []
    kit: set[str] = {"Button"}
    for g in groups:
        fields = [f for f in g.get("fields", []) if f in specs]
        if not fields:
            continue
        body = []
        for f in fields:
            s = specs[f]
            kit.add(VUE_CONTROL_IMPORT.get(s["control"], "TextInput")
                    if s["control"] not in STUB_REASON else "ControlStub")
            review = (vue_comment(f"review: {s['review']}", "    ") + "\n" if s.get("review") else "")
            err = member("errors", f)
            if s["control"] in ("switch", "checkbox"):
                # A toggle is its own label; it gets the error below it, with
                # the id the control's aria-describedby names.
                body.append(
                    f"{review}    <div class=\"field\" data-state={{{err} ? 'error' : undefined}}>\n"
                    f"{svelte_control(s, '      ')}\n"
                    f"      {{#if {err}}}\n"
                    f"        <p class=\"fieldError\" id={{fieldId({js_string(f)}) + '-error'}}>{{{err}}}</p>\n"
                    f"      {{/if}}\n"
                    f"    </div>")
                continue
            kit.add("Field")
            attrs = [f"id={{fieldId({js_string(f)})}}", f'label="{svelte_static(s["label"])}"',
                     f"required={{{str(s.get('required', False)).lower()}}}",
                     f"error={{{err} ?? null}}", "disabled={disabled}"]
            if s["control"] == "radio-group":
                attrs.append("group")
            body.append(review + svelte_tag("Field", attrs, "    ", svelte_control(s, "      ")))
        sections.append(
            "  <fieldset class=\"group\" {disabled}>\n"
            f"    <legend class=\"legend\">{svelte_text(g.get('legend', 'Details'))}</legend>\n"
            + "\n".join(body) + "\n  </fieldset>")
    return "\n\n".join(sections) or "  <!-- no writable fields -->", kit


def emit_svelte_form(table: dict[str, Any], model: dict[str, Any], ans: Answers) -> str:
    name = table["name"]
    Entity = pascal(singular(name))
    sections, kit = _svelte_form_sections(table, model, ans)
    script = Template("""\
import { $kit } from '../../ui';
import type { ${Entity}Draft } from './$camel.types';

/**
 * The $lower_entity form.
 *
 * Three UX rules this markup encodes, all of which generators skip:
 *
 * 1. VALIDATION TIMING. `errors` is rendered whenever it is set; it is the
 *    CALLER's job not to set it until a field has been blurred once.
 * 2. THE ERROR SUMMARY comes first in the DOM and takes focus, once per
 *    submit attempt, because on a long form the invalid field is usually
 *    off-screen. Each entry links to its field.
 * 3. REQUIRED IS MARKED BOTH WAYS. The asterisk is decorative and hidden from
 *    assistive tech; the `required` attribute is what actually announces it.
 *
 * Still yours to do: the unsaved-changes guard (block the route change while
 * `dirty`), and autosave if this form is long enough to deserve it. See
 * screen-patterns.md section 13.
 */
type Props = {
  values: Partial<${Entity}Draft>;
  errors: Partial<Record<keyof ${Entity}Draft, string>>;
  /** Blocks every control AND the submit button, together. */
  disabled?: boolean;
  submitting?: boolean;
  /** Set when the user has changed something and not saved it. */
  dirty?: boolean;
  /** A form-level failure: the save was rejected as a whole. */
  submitError?: string | null;
  onChange: (name: keyof ${Entity}Draft, value: unknown) => void;
  onSubmit: () => void;
  onCancel?: () => void;
};

let {
  values,
  errors,
  disabled = false,
  submitting = false,
  dirty = false,
  submitError = null,
  onChange,
  onSubmit,
  onCancel,
}: Props = $props();

const fieldId = (name: string) => '$camel-' + name;

const invalid = $derived(Object.entries(errors).filter(([, message]) => Boolean(message)));
let summary = $state<HTMLDivElement>();
let attempt = $state(0);
let focusedFor = 0;

// After a submit attempt that failed validation, move focus to the summary:
// once per attempt, whether or not the error count changed. The caller sets
// `errors` in `onSubmit` or, validating asynchronously, sets `submitting`
// while it runs. An effect runs after the DOM updates, with the summary bound.
// A save that came back clean consumes the attempt, so an error that appears
// later, from a blur, does not pull focus to the summary.
$effect(() => {
  if (attempt > focusedFor && invalid.length > 0) {
    focusedFor = attempt;
    summary?.focus();
  } else if (!submitting && invalid.length === 0) {
    focusedFor = attempt;
  }
});

function submit(event: SubmitEvent) {
  event.preventDefault();
  attempt += 1;
  onSubmit();
}
""").safe_substitute(Entity=Entity, camel=camel(name), kit=", ".join(sorted(kit)),
                     lower_entity=singular(name.replace("_", " ")))
    markup = """\
<form class="stack stack--separate" novalidate onsubmit={submit}>
  {#if invalid.length > 0}
    <div class="summary" role="alert" tabindex="-1" bind:this={summary}>
      <p class="summaryTitle">
        {invalid.length === 1 ? 'One field needs attention' : String(invalid.length) + ' fields need attention'}
      </p>
      <ul class="summaryList">
        {#each invalid as [name, message] (name)}
          <li>
            <a class="summaryLink" href={'#' + fieldId(name)}>{String(message)}</a>
          </li>
        {/each}
      </ul>
    </div>
  {/if}

  {#if submitError}
    <p class="submitError" role="alert">{submitError}</p>
  {/if}

""" + sections + """

  <div class="cluster cluster--tight">
    <Button type="submit" variant="primary" loading={submitting} {disabled}>Save</Button>
    <Button type="button" variant="ghost" onclick={onCancel} disabled={submitting}>
      {dirty ? 'Discard changes' : 'Cancel'}
    </Button>
  </div>
</form>
"""
    return svelte_sfc(script, markup, svelte_sheet(markup, FORM_CSS))


def _svelte_imports(cells: list[dict[str, Any]], kit: list[str], Entities: str,
                    states: tuple[str, ...]) -> str:
    out = f"import {{ {', '.join(kit)} }} from '../../ui';\n" + _helper_imports(cells, set())
    return out + "".join(f"import {Entities}{s} from './{Entities}{s}.svelte';\n" for s in states)


def emit_svelte_list(table: dict[str, Any], model: dict[str, Any], ans: Answers) -> str:
    name = table["name"]
    Entity = pascal(singular(name))
    Entities = pascal(name)
    title = ans.title(table)
    layout = ans.layout(table)
    pk = table["primary_key"][0] if table["primary_key"] else "id"
    human = name.replace("_", " ")
    Title = human[:1].upper() + human[1:]
    cols = [c for c in table["columns"] if c["name"] in ans.list_columns(table)] or table["columns"][:1]
    cells = {c["name"]: cell_render(c, "row", table, ans) for c in cols}
    href = f"{{{js_string('/' + name + '/')} + String({member('row', pk)})}}"
    key = f"String({member('row', pk)})"

    if layout == "table":
        head = "\n".join(
            f'          <th class="{"th sticky" if c["name"] == title else "th"}" scope="col">\n'
            f"            {svelte_text(c['ui'].get('label', c['name']))}\n"
            f"          </th>" for c in cols)
        body = []
        for c in cols:
            cell = cells[c["name"]]
            cls = " ".join(["td"] + ([cell["class"]] if cell["class"] else [])
                           + (["sticky"] if c["name"] == title else []))
            inner = (f'<a class="link" href={href}>{cell_expr(cell)}</a>'
                     if c["name"] == title else cell_expr(cell))
            body.append(f'            <td class="{cls}">{inner}</td>')
        rows = Template("""\
    <!-- A scrollable region must take focus, or a keyboard cannot scroll it
         (WCAG 2.1.1): the tabindex is the point, not an accident. -->
    <!-- svelte-ignore a11y_no_noninteractive_tabindex -->
    <div class="scroller" tabindex="0" role="region" aria-label="$Title, scrollable table">
      <table class="root">
        <thead class="head">
          <tr>
$head
          </tr>
        </thead>
        <tbody>
          {#each state.rows as row ($key)}
            <tr class="row">
$body
            </tr>
          {/each}
        </tbody>
      </table>
    </div>""").safe_substitute(Title=svelte_static(Title), head=head, key=key,
                               body="\n".join("  " + b for b in body))
    else:
        grid = "grid grid--min-lg" if layout == "feed" else "grid grid--min-sm"
        meta = "\n".join(
            f"              <div>\n"
            f'                <dt class="cardMeta">{svelte_text(c["ui"].get("label", c["name"]))}</dt>\n'
            f"                <dd>{cell_expr(cells[c['name']])}</dd>\n"
            f"              </div>" for c in cols if c["name"] != title)
        title_expr = (cell_expr(cells[title]) if title in cells
                      else "{String(" + member("row", pk) + ")}")
        rows = Template("""\
    <ul class="$grid">
      {#each state.rows as row ($key)}
        <li>
          <article class="card">
            <h2 class="cardTitle">
              <a class="cardLink" href=$href>
                $title_expr
              </a>
            </h2>
            <dl class="stack stack--fused">
$meta
            </dl>
          </article>
        </li>
      {/each}
    </ul>""").safe_substitute(grid=grid, key=key, href=href, title_expr=title_expr, meta=meta)

    kit = (["Badge"] if any(c["element"] for c in cells.values()) else []) + ["Button"]
    script = Template("""\
${imports}import type { ${Entity}ListState } from './$camel.types';

/**
 * $human, as a $layout.
 *
 * $layout_why
 *
 * This component takes its rows as a prop and knows nothing about fetching.
 * That is deliberate: cache keys, realtime and optimistic writes are product
 * decisions, and a scaffold has no business guessing at them.
 */
type Props = {
  state: ${Entity}ListState;
  /** The single primary action offered by the first-run empty state. */
  onCreate?: () => void;
  /** Clears whatever produced the filtered-empty state. */
  onClearFilters?: () => void;
};

let { state, onCreate, onClearFilters }: Props = $props();
""").safe_substitute(
        imports=_svelte_imports(list(cells.values()), kit, Entities,
                                ("Empty", "Error", "FilteredEmpty", "Forbidden", "Loading")),
        Entity=Entity, camel=camel(name), human=human, layout=layout,
        layout_why=table["screens"].get("index_layout_signal", ""))
    markup = Template("""\
{#if state.status === 'loading'}
  <${Entities}Loading />
{:else if state.status === 'error'}
  <${Entities}Error error={state.error} onRetry={state.retry} />
{:else if state.status === 'forbidden'}
  <${Entities}Forbidden />
{:else if state.rows.length === 0}
  <!-- Two different screens, not one screen with two strings. "Nothing here
       yet, make the first one" and "your filter matched nothing, clear it"
       ask the user to do opposite things. -->
  {#if state.filtered}
    <${Entities}FilteredEmpty {onClearFilters} />
  {:else}
    <${Entities}Empty {onCreate} />
  {/if}
{:else}
  <section class="stack stack--separate" aria-labelledby="$camel-heading">
    <header class="cluster cluster--between">
      <h1 class="heading" id="$camel-heading">
        $Title
      </h1>
      <Button variant="primary" onclick={onCreate}>
        New $lower_entity
      </Button>
    </header>

    {#if state.stale}
      <p class="stale" role="status">Showing the last known data while this refreshes.</p>
    {/if}

$rows
  </section>
{/if}
""").safe_substitute(Entities=Entities, camel=camel(name), Title=svelte_text(Title),
                     lower_entity=svelte_text(singular(human)), rows=rows)
    sfc = svelte_sfc(script, markup, svelte_sheet(
        markup, LIST_CSS, DATA_TABLE_CSS if layout == "table" else CARD_GRID_CSS))
    return sfc.replace("\n<style>\n", "\n" + SVELTE_STATE_RULES + "<style>\n", 1)


def emit_svelte_detail(table: dict[str, Any], model: dict[str, Any], ans: Answers) -> str:
    name = table["name"]
    Entity = pascal(singular(name))
    Entities = pascal(name)
    title = ans.title(table)
    pk = table["primary_key"][0] if table["primary_key"] else "id"
    rows, cells = [], []
    for c in table["columns"]:
        if not c["ui"].get("placement", {}).get("detail") or c["name"] == title:
            continue
        cell = cell_render(c, "state.record", table, ans)
        cells.append(cell)
        rows.append(
            f'        <div class="pair">\n'
            f'          <dt class="term">{svelte_text(c["ui"].get("label", c["name"]))}</dt>\n'
            f'          <dd class="value">{cell_expr(cell)}</dd>\n'
            f"        </div>")
    related = [vue_comment(f"TODO({r['control']}): {r['kind']} to `{r['to']}`"
                           + (f" via `{r['via']}`" if r.get("via") else "")
                           + f". {r.get('signal', '')}", "      ")
               for r in table.get("relationships", [])
               if r["kind"] in ("one-to-many", "many-to-many")]
    placeholder_note = ""
    if table["screens"].get("title_is_placeholder"):
        placeholder_note = (
            "\n *\n * TODO(title): nothing in this table looks like a title, so the\n"
            " * primary key is standing in. A uuid in an h1 is not a heading.\n"
            " * Answer the `.title_column` question and come back.")
    title_expr = ("{state.record." + title + "}"
                  if title and re.fullmatch(r"[A-Za-z_$][\w$]*", title)
                  else "{String(" + member("state.record", pk) + ")}")
    kit = (["Badge"] if any(c["element"] for c in cells) else []) + ["Button"]
    script = Template("""\
${imports}import type { ${Entity}DetailState } from './$camel.types';

/**
 * One $lower_entity.
 *
 * The layout is `.with-sidebar`: the record's own fields in the main pane, its
 * actions and metadata in the rail. The rail wraps underneath at a CONTENT
 * threshold rather than a viewport breakpoint, so this page is correct inside
 * a drawer and inside a 288px column without knowing it.$placeholder_note
 */
type Props = {
  state: ${Entity}DetailState;
  onEdit?: () => void;
  onDelete?: () => void;
};

let { state, onEdit, onDelete }: Props = $props();
""").safe_substitute(
        imports=_svelte_imports(cells, kit, Entities, ("Error", "Forbidden", "Loading")),
        Entity=Entity, camel=camel(name), placeholder_note=placeholder_note,
        lower_entity=singular(name.replace("_", " ")))
    markup = Template("""\
{#if state.status === 'loading'}
  <${Entities}Loading />
{:else if state.status === 'error'}
  <${Entities}Error error={state.error} onRetry={state.retry} />
{:else if state.status === 'forbidden'}
  <${Entities}Forbidden />
{:else}
  <article class="with-sidebar" aria-labelledby="$camel-detail-heading">
    <div class="with-sidebar__main stack stack--separate">
      <h1 class="title" id="$camel-detail-heading">
        $title_expr
      </h1>

      <dl class="fields">
$rows
      </dl>
$related
    </div>

    <aside class="with-sidebar__rail stack stack--related" aria-label="Actions">
      <Button variant="primary" onclick={onEdit}>Edit</Button>
      <Button variant="danger" onclick={onDelete}>Delete</Button>
      <!-- TODO(copy): a delete confirmation must name the record and state
           what else disappears with it. "Are you sure?" is not that. See
           screen-patterns.md section 8. -->
    </aside>
  </article>
{/if}
""").safe_substitute(Entities=Entities, camel=camel(name), title_expr=title_expr,
                     rows="\n".join(rows) or "        <!-- no detail fields -->",
                     related=("\n" + "\n".join(related)) if related else "")
    return svelte_sfc(script, markup, svelte_sheet(markup, DETAIL_CSS))


def emit_svelte_states(table: dict[str, Any], model: dict[str, Any],
                       ans: Answers) -> dict[str, str]:
    """The six states, one component each."""
    name = table["name"]
    human = name.replace("_", " ")
    empty = ans.empty(table)
    cols = len(ans.list_columns(table)) or 3
    forbidden_note = (
        "Row-level security is on for this table, so this is a real state: the\n"
        " * query succeeded and returned nothing because the policy filtered\n"
        " * everything out. Rendering that as 'no records' tells the user their\n"
        " * data is gone."
        if ans.rls(table) else
        "RLS was reported as off, so this should be unreachable today. It is\n"
        " * generated anyway, because 'we will add RLS later' is always true and\n"
        " * retrofitting this state means touching every list in the app.")

    def block(doc: str, props: str, kind: str, headline: str, body: str, note: str | None,
              action: tuple[str, str, str] | None, bound: str | None = None) -> str:
        """`action` is (variant, callback, label). `body` is copy, so always
        text; `bound` is an expression instead (as the Vue one, #176)."""
        script = ("import { Button, StateBlock } from '../../ui';\n" if action
                  else "import { StateBlock } from '../../ui';\n")
        script += f"\n/**\n * {doc}\n */\n" + props
        body_attr = f"body={{{bound}}}" if bound else f'body="{svelte_static(body)}"'
        tag = f'<StateBlock kind="{kind}" headline="{svelte_static(headline)}" {body_attr}>\n'
        if action:
            variant, callback, label = action
            tag += (f"  {{#snippet action()}}\n"
                    f'    <Button variant="{variant}" onclick={{{callback}}}>{svelte_text(label)}</Button>\n'
                    f"  {{/snippet}}\n")
        tag += "</StateBlock>\n"
        return svelte_sfc(script, (vue_comment(note, "") + "\n" if note else "") + tag)

    return {
        "Empty": block(f"No {human} have ever existed. The most-seen screen in the app on day one.",
                       "let { onCreate }: { onCreate?: () => void } = $props();\n", "first-run",
                       empty["headline"], empty["body"] or f"TODO(copy): what {human} are for.",
                       "TODO(copy): say what this screen will hold and why it is worth filling "
                       "in. One sentence. \"No data\" is the absence of copy, not copy.",
                       ("primary", "onCreate", empty["action"])),
        "FilteredEmpty": block(
            "A filter or a search matched nothing. A DIFFERENT screen from the empty one:\n"
            " * the records exist, this query just missed them, so the action is \"clear the\n"
            " * filter\", never \"create a record\".",
            "let { onClearFilters }: { onClearFilters?: () => void } = $props();\n", "filtered",
            f"No {human} match those filters",
            "Try a broader search, or clear the filters to see everything.",
            "TODO(copy): name the filters that are on, so the user can see what to "
            "relax without hunting for it.", ("ghost", "onClearFilters", "Clear filters")),
        "Error": block(
            "The request failed. Always offer the retry — an error with no way forward\n"
            " * is a dead end, and users reload the whole app instead.",
            "let { error, onRetry }: { error?: Error; onRetry?: () => void } = $props();\n", "error",
            f"Something went wrong loading {human}", "",
            f"TODO(copy): say what failed in the user's terms, not the transport's. "
            f"\"We could not load your {human}\" beats \"Request failed\".",
            ("primary", "onRetry", "Try again"), bound="error?.message"),
        "Forbidden": block(
            f"The user is not allowed to see these rows.\n *\n * {forbidden_note}",
            "", "forbidden", f"You do not have access to {human}",
            "Ask an administrator if you think this is a mistake.",
            "TODO(copy): say who to ask. A permission wall with no route onward is a "
            "support ticket. Do NOT reveal whether any records exist.", None),
        "Stale": block(
            "Data on screen is known to be out of date — a realtime event arrived, or a\n"
            " * background revalidation failed. Shown ABOVE the stale rows rather than\n"
            " * replacing them: taking correct-a-moment-ago data away is worse than\n"
            " * labelling it.",
            "let { onRefresh }: { onRefresh?: () => void } = $props();\n", "stale",
            "This list has changed", f"Someone else updated these {human} while you were reading.",
            None, ("ghost", "onRefresh", "Refresh")),
        "Loading": svelte_sfc("""\
import { Skeleton } from '../../ui';

/**
 * A skeleton shaped like the real table: same column count, same row height.
 * A spinner would be less work and would also let the page jump when the data
 * lands, moving whatever the user was about to click.
 */
let { rows = 5 }: { rows?: number } = $props();
""", Template("""\
<div class="loading" role="status" aria-live="polite">
  <span class="visually-hidden">Loading $human</span>
  {#each Array.from({ length: rows }, (_, index) => index) as index (index)}
    <div class="loadingRow">
      {#each Array.from({ length: $cols }, (_, cell) => cell) as cell (cell)}
        <Skeleton width={cell === 0 ? 0.8 : 0.5} />
      {/each}
    </div>
  {/each}
</div>
""").safe_substitute(human=svelte_text(human), cols=cols),
            # The skeletons are Skeleton's elements, which this component's
            # scope does not reach.
            STATES_CSS.replace(".loadingRow > *", ".loadingRow > :global(*)")),
    }


def emit_svelte_index(table: dict[str, Any]) -> str:
    return emit_vue_index(table).replace(".vue';", ".svelte';")


def build_svelte_files(model: dict[str, Any], ans: Answers, stack: str,
                       entities: set[str] | None) -> dict[str, str]:
    """The kit and the screens as Svelte 5 components; everything that is not
    a component is the React scaffold's own file."""
    css = stack == "css-modules"

    def comp(path: str, text: str, component: str, sheet: str) -> None:
        files[path] = text if css else sfc_tailwind(text, component, "root", sheet)

    files: dict[str, str] = {"lib/format.ts": FORMAT_TS, "ui/index.ts": SVELTE_INDEX_KIT,
                             "ui/Field/describedBy.ts": VUE_DESCRIBED_BY.replace("Field.vue", "Field.svelte")}
    if not css:
        files["styles/scaffold.css"] = SCAFFOLD_CSS
    for name, text, sheet in (("Button", SVELTE_BUTTON, BUTTON_CSS), ("Field", SVELTE_FIELD, FIELD_CSS),
                              ("Badge", SVELTE_BADGE, BADGE_CSS), ("Skeleton", SVELTE_SKELETON, SKELETON_CSS),
                              ("StateBlock", SVELTE_STATE_BLOCK, STATE_BLOCK_CSS)):
        comp(f"ui/{name}/{name}.svelte", text, name, sheet)
    for name, text in SVELTE_CONTROLS.items():
        comp(f"ui/Control/{name}.svelte", text, "Control", CONTROL_CSS)

    for table in model["tables"]:
        if table["kind"] == "join" or (entities and table["name"] not in entities):
            continue
        name = table["name"]
        Entity = pascal(singular(name))
        Entities = pascal(name)
        base = f"features/{name}"
        files[f"{base}/{camel(name)}.types.ts"] = (emit_types(table, model, ans)
                                                   + VUE_DETAIL_STATE.substitute(Entity=Entity))
        files[f"{base}/{camel(name)}.fields.ts"] = emit_fields(table, model, ans)
        list_sheet = LIST_CSS + (DATA_TABLE_CSS if ans.layout(table) == "table" else CARD_GRID_CSS)
        comp(f"{base}/{Entities}List.svelte", emit_svelte_list(table, model, ans), "List", list_sheet)
        comp(f"{base}/{Entity}Detail.svelte", emit_svelte_detail(table, model, ans), "Detail", DETAIL_CSS)
        comp(f"{base}/{Entity}Form.svelte", emit_svelte_form(table, model, ans), "Form", FORM_CSS)
        for state, text in emit_svelte_states(table, model, ans).items():
            comp(f"{base}/{Entities}{state}.svelte", text, "States", STATES_CSS)
        files[f"{base}/index.ts"] = emit_svelte_index(table)
        files[f"server/{name}.schema.ts"] = emit_schema_zod(table, model, ans)
        files[f"server/{name}_schema.py"] = emit_schema_pydantic(table, model, ans)
    return files


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# The database side (supabase-integration.md §9): the browser's one client
# (DL-B1), and per table a policies proposal with its smoke test (DL-B2).
# ---------------------------------------------------------------------------

SUPABASE_TS = """\
// The browser's only Supabase client (supabase-integration.md §9). It holds the
// publishable key, which is safe in a bundle because row-level security decides
// what it may do. Every VITE_ variable is public: a secret key never goes in one.
//
// database.types.ts comes from the database itself:
//   supabase gen types typescript --project-id <project-ref> > src/lib/database.types.ts
import { createClient } from '@supabase/supabase-js';
import type { Database } from './database.types';

const url = import.meta.env.VITE_SUPABASE_URL;
const publishableKey = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY;

if (!url || !publishableKey) {
  throw new Error('Set VITE_SUPABASE_URL and VITE_SUPABASE_PUBLISHABLE_KEY (sb_publishable_…) in .env.local.');
}
if (publishableKey.startsWith('sb_secret_') || legacyRole(publishableKey) === 'service_role') {
  // That key bypasses row-level security, and this file ships to every browser.
  throw new Error('VITE_SUPABASE_PUBLISHABLE_KEY holds a secret key. Keep it on the server.');
}

/** The role inside a legacy JWT key (`anon` or `service_role`), if it is one. */
function legacyRole(key: string): string | undefined {
  try {
    const payload = key.split('.')[1] ?? '';
    return JSON.parse(atob(payload.replace(/-/g, '+').replace(/_/g, '/'))).role;
  } catch {
    return undefined;
  }
}

export const supabase = createClient<Database>(url, publishableKey);
"""

OWNER_NAMES = ("owner_id", "user_id", "author_id", "created_by", "profile_id")
TENANT_COLUMN = re.compile(r"^(org|organization|tenant|workspace|team|account)_id$")
UID = "(select auth.uid())"
TEST_USER = "00000000-0000-4000-8000-000000000001"


# Words that stay quoted: Postgres's reserved keywords, plus those
# introspect_schema reads as the start of a clause. The scripts stand alone, so
# this is a copy of introspect_schema.KEEP_QUOTED, and a test holds them equal (N21).
KEEP_QUOTED = set("""
    all analyse analyze and any array as asc asymmetric authorization binary both case cast check
    collate collation column concurrently constraint create cross current_catalog current_date
    current_role current_schema current_time current_timestamp current_user default deferrable
    desc distinct do else end except exclude false fetch for foreign freeze from full generated
    grant group having ilike in initially inner intersect into is isnull join lateral leading
    left like limit localtime localtimestamp natural not notnull null offset on only or order
    outer overlaps placing primary references returning right select session_user similar some
    symmetric system_user table tablesample then to trailing true union unique user using
    variadic verbose when where window with""".split())
# Postgres cuts a longer name to this many bytes (NAMEDATALEN - 1).
NAME_BYTES = 63


def sql_ident(name: str) -> str:
    """A name as SQL writes it: bare only when Postgres reads it back as the same name."""
    if re.fullmatch(r"[a-z_][a-z0-9_]*", name) and name not in KEEP_QUOTED:
        return name
    return '"' + name.replace('"', '""') + '"'


def sql_text(value: str) -> str:
    """A string literal."""
    return "'" + value.replace("'", "''") + "'"


def raise_text(value: str) -> str:
    """A RAISE message: a string literal in which `%` is a placeholder."""
    return sql_text(value.replace("%", "%%"))


def pg_schema(model: dict[str, Any]) -> str:
    """The schema introspect_schema read (`--schema`), where the policies go (N20)."""
    return (model.get("source") or {}).get("pg_schema") or "public"


def policy_name(table: str, label: str) -> str:
    """`<table>: <label>`, kept to 63 bytes. Postgres cuts a longer name, so a
    long table's four names became one and the second CREATE POLICY failed
    (N22). A shortened table part ends in a hash of the whole name."""
    name = f"{table}: {label}"
    if len(name.encode("utf-8")) <= NAME_BYTES:
        return name
    tail = f"~{hashlib.sha256(table.encode('utf-8')).hexdigest()[:8]}: {label}"
    head = table.encode("utf-8")[:NAME_BYTES - len(tail.encode("utf-8"))].decode("utf-8", "ignore")
    return head + tail


def _key_into_auth(model: dict[str, Any], col: dict[str, Any]) -> bool:
    """A foreign key to `users` that is not a table of this schema: auth.users."""
    fk = col.get("foreign_key")
    return bool(fk) and fk["table"] == "users" and not any(
        t["name"] == "users" for t in model["tables"])


def ownership(table: dict[str, Any], model: dict[str, Any],
              seen: frozenset[str] = frozenset()) -> dict[str, Any]:
    """Whose a row is, as far as the schema says: `self` (the row is the user),
    `owner` (a column holds the user), `tenant`, `child` (its parent's owner),
    or `none`. A guess from keys and names, which is why the file is a TODO."""
    seen = seen | {table["name"]}
    tables = {t["name"]: t for t in model["tables"]}
    cols = table["columns"]

    def parent(c: dict[str, Any]) -> dict[str, Any] | None:
        fk = c.get("foreign_key")
        p = tables.get(fk["table"]) if fk else None
        return p if p and p["name"] not in seen else None

    for c in cols:
        if c["primary_key"] and len(table["primary_key"]) == 1 and _key_into_auth(model, c):
            return {"kind": "self", "column": c["name"],
                    "why": f"{c['name']} is the user's own id, a key into auth.users"}
    owners = []
    for c in cols:
        if c["primary_key"] and len(table["primary_key"]) == 1:
            continue
        p = parent(c)
        if _key_into_auth(model, c):
            owners.append((0, c, f"{c['name']} is a key into auth.users"))
        elif p and ownership(p, model, seen)["kind"] == "self":
            owners.append((0, c, f"{c['name']} is a key into {p['name']}, whose id is the user's"))
        elif c["name"] in OWNER_NAMES and c["type"] == "uuid":
            owners.append((1, c, f"{c['name']} is named for an owner"))
    if owners:
        _, c, why = min(owners, key=lambda o: (o[0], o[1]["nullable"]))
        return {"kind": "owner", "column": c["name"], "why": why}
    for c in cols:
        if TENANT_COLUMN.match(c["name"]):
            return {"kind": "tenant", "column": c["name"], "why": f"{c['name']} names a tenant"}
    for c in cols:
        p = parent(c) if not c["nullable"] else None
        up = ownership(p, model, seen) if p else None
        if up and up["kind"] in ("self", "owner", "child"):
            return {"kind": "child", "column": c["name"], "parent": p["name"],
                    "parent_column": c["foreign_key"]["column"], "up": up,
                    "why": f"{c['name']} makes it part of a row of {p['name']}, where {up['why']}"}
    return {"kind": "none", "column": None, "why": "no column says who a row belongs to"}


def owner_check(own: dict[str, Any], table: str, schema: str, ref: str = "", depth: int = 1) -> str:
    """The condition that holds when the row is the caller's. `ref` names the
    row's table inside a parent's subquery, where each level has its alias."""
    qual = f"{ref}." if ref else ""
    if own["kind"] in ("self", "owner"):
        return f"{qual}{sql_ident(own['column'])} = {UID}"
    alias = f"p{depth}"
    return (f"exists (select 1 from {sql_ident(schema)}.{sql_ident(own['parent'])} {alias} "
            f"where {alias}.{sql_ident(own['parent_column'])} = "
            f"{ref or sql_ident(table)}.{sql_ident(own['column'])} "
            f"and {owner_check(own['up'], own['parent'], schema, alias, depth + 1)})")


def _protected(table: dict[str, Any], own: dict[str, Any], writable: list[str]) -> list[str]:
    """Columns a user must not set: authority, credentials, and the owner."""
    return [c["name"] for c in table["columns"]
            if c["name"] not in writable and not c["generated"]
            and (c["ui"].get("authority") or c["ui"].get("never_display")
                 or c["name"] == own.get("column"))]


def emit_policies(table: dict[str, Any], model: dict[str, Any], ans: Answers) -> str:
    name = table["name"]
    schema = pg_schema(model)
    q = f"{sql_ident(schema)}.{sql_ident(name)}"
    own = ownership(table, model)
    kind = own["kind"]
    out = [f"-- TODO(policy): {name}. Proposed from the schema, which cannot say who may do",
           "-- what. Read each statement and fix what is wrong, then move the file into a",
           "-- migration: nothing here runs until you do. Then run",
           f"-- {name}.policies.test.sql against the database (supabase-integration.md §9).",
           f"-- Whose a row is: {own['why']}."]
    if table.get("policies"):
        out.append(f"-- The schema already has {len(table['policies'])} policy(ies) on {name}: "
                   f"compare them before you replace anything.")
    out += ["", f"alter table {q} enable row level security;", ""]

    if kind in ("self", "owner", "child"):
        check = owner_check(own, name, schema)
        for verb, cmd, clauses in (
                ("reads", "select", (("using", check),)),
                ("inserts", "insert", (("with check", check),)),
                ("updates", "update", (("using", check), ("with check", check))),
                ("deletes", "delete", (("using", check),))):
            out.append(f"create policy {sql_ident(policy_name(name, f'owner {verb}'))} on {q}\n"
                       f"  for {cmd} to authenticated\n"
                       + "\n".join(f"  {kw} ({cond})" for kw, cond in clauses) + ";")
            out.append("")
    elif kind == "tenant":
        col = sql_ident(own["column"])
        out += ["-- TODO(policy): a policy needs the caller's tenants, which this schema does",
                "-- not show. The usual shape is a security-definer helper in a schema the API",
                "-- does not expose. Until then RLS is on with no policy: nobody can read or write.",
                f"--   create function private.user_{own['column']}s() returns setof uuid",
                "--     language sql security definer set search_path = '' stable",
                f"--     as $$ select {col} from {sql_ident(schema)}.memberships where user_id = {UID} $$;",
                f"--   revoke execute on function private.user_{own['column']}s() from public;",
                "--   grant usage on schema private to authenticated;",
                f"--   grant execute on function private.user_{own['column']}s() to authenticated;",
                f"--   create policy {sql_ident(policy_name(name, 'members read'))} on {q}",
                f"--     for select to authenticated using ({col} in (select private.user_{own['column']}s()));",
                ""]
    else:
        out += [f"create policy {sql_ident(policy_name(name, 'signed-in users read'))} on {q}",
                "  for select to authenticated", "  using (true);", "",
                "-- No write policy: the browser cannot change these rows. Writes go through the",
                "-- server, with the secret key. If users should write here, the table needs an",
                "-- owner column first.", ""]

    if kind != "none":
        writable = ans.writable(table)
        inserted = writable + [c for c in (own["column"],) if c and c not in writable]
        out += ["-- Columns. Supabase grants every column to signed-in users, and a column revoke",
                "-- does nothing while that table-level grant stands. So take the table back, and",
                f"-- grant the columns the form writes ({pascal(singular(name))}Draft) and the owner.",
                "-- TODO(policy): a user may set each of these on their own rows. Strike any",
                "-- the server should own, such as a status or a total.",
                f"revoke insert, update on {q} from authenticated;"]
        if inserted:
            out.append(f"grant insert ({', '.join(map(sql_ident, inserted))}) on {q} to authenticated;")
        if writable:
            out.append(f"grant update ({', '.join(map(sql_ident, writable))}) on {q} to authenticated;")
    return "\n".join(out).rstrip() + "\n"


def emit_policy_test(table: dict[str, Any], model: dict[str, Any], ans: Answers) -> str:
    name = table["name"]
    schema = pg_schema(model)
    q = f"{sql_ident(schema)}.{sql_ident(name)}"
    own = ownership(table, model)
    kind = own["kind"]
    out = [f"-- Smoke test for {name}.policies.todo.sql, once those statements have run.",
           "-- It changes nothing: everything happens in a transaction that rolls back.",
           "-- Run it as the database owner, and read silence as a pass:",
           f'--   psql "<connection string>" -v ON_ERROR_STOP=1 -f {name}.policies.test.sql',
           "begin;", "",
           "do $$ begin",
           f"  assert (select relrowsecurity from pg_class where oid = {sql_text(q)}::regclass),",
           f"    {sql_text(f'row-level security is off on {q}')};",
           "end $$;", "",
           "-- A visitor with the publishable key and no session. TODO(test): if the table is",
           "-- public on purpose, delete this check.",
           "set local role anon;",
           "do $$ begin",
           f"  assert not exists (select 1 from {q}), {sql_text(f'anon can read {q}')};",
           "end $$;",
           "reset role;", "",
           "-- A signed-in user. TODO(test): put an id from your seed here to test real rows.",
           "set local role authenticated;",
           f"""set local request.jwt.claims = '{{"sub": "{TEST_USER}", "role": "authenticated"}}';""",
           ""]
    if kind in ("self", "owner", "child"):
        out += ["do $$ begin",
                f"  assert not exists (select 1 from {q} where ({owner_check(own, name, schema)}) is not true),",
                f"    {sql_text(f'a signed-in user can read {name} rows that are not theirs')};",
                "end $$;", ""]
    elif kind == "none":
        # Only a policy the browser's roles hold: one for service_role is the
        # server's (N23). `public` is every role, and the default; any other
        # role counts when anon or authenticated has its privileges, directly or
        # through roles they inherit (USAGE: a grant WITH INHERIT FALSE does not
        # count, since its policies do not apply without SET ROLE).
        out += ["do $$ begin",
                f"  assert not exists (select 1 from pg_policies where schemaname = {sql_text(schema)}",
                f"    and tablename = {sql_text(name)} and cmd <> 'SELECT'",
                "    and exists (select 1 from unnest(roles) as r(role) where case when r.role = 'public' then true",
                "      else pg_has_role('anon', r.role, 'USAGE') or pg_has_role('authenticated', r.role, 'USAGE') end)),",
                f"    {sql_text(f'a policy lets the browser write {q}')};",
                "end $$;", ""]
    writable = ans.writable(table)
    protected = _protected(table, own, writable) if kind != "none" else []
    if protected or (writable and kind != "none"):
        out += ["-- Columns. Postgres checks a column privilege before it touches a row, so",
                "-- `where false` is enough to prove each one.",
                "do $$ begin"]
        for c in map(sql_ident, protected):
            out += ["  begin",
                    f"    update {q} set {c} = {c} where false;",
                    f"    raise exception {raise_text(f'a signed-in user can change {name}.{c}')};",
                    "  exception when insufficient_privilege then null;",
                    "  end;"]
            if c != sql_ident(own.get("column") or ""):
                out += ["  begin",
                        f"    insert into {q} ({c}) select {c} from {q} where false;",
                        f"    raise exception {raise_text(f'a signed-in user can set {name}.{c} on insert')};",
                        "  exception when insufficient_privilege then null;",
                        "  end;"]
        if writable and kind != "none":
            w = sql_ident(writable[0])
            out.append(f"  update {q} set {w} = {w} where false;  -- the form's columns stay writable")
        out += ["end $$;", ""]
    out.append("rollback;")
    text = "\n".join(out) + "\n"
    # A name may hold `$$`, which would end a `do $$` body early: use a
    # delimiter the body does not contain.
    body = text.replace("do $$ begin", "").replace("end $$;", "")
    tag, n = "$$", 0
    while tag in body:
        n += 1
        tag = f"$wds{n}$"
    return text.replace("do $$ begin", f"do {tag} begin").replace("end $$;", f"end {tag};")


# ---------------------------------------------------------------------------
# The server schema: the same constraints the form mirrors, for the side that
# is a control rather than a courtesy
# ---------------------------------------------------------------------------

INTEGER_TYPES = ("integer", "smallint", "bigint")
NUMBER_TYPES = INTEGER_TYPES + ("numeric", "real", "double precision", "money")


def schema_fields(table: dict[str, Any], model: dict[str, Any],
                  ans: Answers) -> list[dict[str, Any]]:
    """One entry per writable column: what the Draft type submits, with the
    rules the database holds. A rule invented by the mapper (`mirror: false`)
    is kept and marked, so a reviewer can add the constraint or drop the
    rule, but never find the two silently disagreeing."""
    writable = ans.writable(table)
    cols = {c["name"]: c for c in table["columns"]}
    out = []
    for name in writable:
        col = cols[name]
        spec = field_spec(col, table, model, ans)
        rules = col["ui"].get("validation", [])
        # A rule is invented only when no constraint states it: a CHECK and
        # the mapper's "money is non-negative" both say `min`, and the CHECK
        # makes it a mirror.
        mirrored = {r["rule"] for r in rules if r.get("mirror") is not False}
        invented = sorted({r["rule"] for r in rules
                           if r.get("mirror") is False} - mirrored)
        fmt = next((r["value"] for r in rules if r["rule"] == "format"), None)
        entry = {
            "name": name,
            "type": col["type"],
            "nullable": bool(col.get("nullable", True)),
            "required": bool(spec.get("required")),
            "array": bool(col.get("is_array")),
            "enum": model["enums"].get(col["enum"], []) if col.get("enum") else [],
            "options": spec.get("options") or [],
            "integer": col["type"] in INTEGER_TYPES
                       or (spec.get("money") or {}).get("storage") == "minor-units",
            "format": fmt,
            "temporal": (col["ui"].get("temporal") or {}).get("granularity"),
            # A `timestamp` without time zone cannot carry an offset; every
            # other instant must, or a wall time is read in the server's zone.
            "aware": (col["ui"].get("temporal") or {}).get("timezone") != "ambiguous",
            "invented": invented,
        }
        for key in ("maxLength", "minLength", "min", "max", "exclusiveMin",
                    "exclusiveMax", "pattern"):
            if key in spec:
                entry[key] = spec[key]
        # A strict bound that is at least as tight as an inclusive one makes
        # the inclusive one redundant: `CHECK (discount > 0)` beside the
        # mapper's "money is non-negative" is one rule, `gt=0`.
        for loose, strict in (("min", "exclusiveMin"), ("max", "exclusiveMax")):
            if loose in entry and strict in entry and (
                    entry[strict] >= entry[loose] if loose == "min"
                    else entry[strict] <= entry[loose]):
                del entry[loose]
                entry["invented"] = [r for r in entry["invented"] if r != loose]
        out.append(entry)
    return out


def emit_schema_zod(table: dict[str, Any], model: dict[str, Any],
                    ans: Answers) -> str:
    name = table["name"]
    Entity = pascal(singular(name))
    fields = schema_fields(table, model, ans)
    lines = [
        "/**",
        f" * The server's schema for a {singular(name.replace('_', ' '))} draft.",
        " *",
        " * The form's validation is a courtesy; this is the control. Every rule",
        " * here mirrors a database constraint, the same ones the form reads from",
        " * the model, so the two cannot drift apart. A rule marked `invented`",
        " * came from the mapper, not the schema: add the constraint or drop the",
        " * rule. Run it in whatever answers the browser: an Edge Function, a",
        " * route handler, a server action.",
        " */",
        "import { z } from 'zod';",
        "",
        f"export const {camel(singular(name))}DraftSchema = z.object({{",
    ]
    for f in fields:
        values = f["enum"] or f["options"]
        if values:
            expr = f"z.enum({json.dumps(values)})"
        elif f["type"] in NUMBER_TYPES:
            expr = "z.number()"
            if f["integer"]:
                expr += ".int()"
            if "min" in f:
                expr += f".min({f['min']})"
            if "max" in f:
                expr += f".max({f['max']})"
            if "exclusiveMin" in f:
                expr += f".gt({f['exclusiveMin']})"
            if "exclusiveMax" in f:
                expr += f".lt({f['exclusiveMax']})"
        elif f["type"] == "boolean":
            expr = "z.boolean()"
        elif f["type"] in ("jsonb", "json"):
            expr = "z.unknown()"
        elif f["temporal"] == "instant":
            expr = "z.string().datetime({ offset: true })"
        elif f["temporal"] == "date":
            expr = "z.string().date()"
        elif f["temporal"] == "time":
            expr = "z.string().time()"
        elif f["type"] == "uuid":
            expr = "z.string().uuid()"
        else:
            expr = "z.string()"
            if f["format"] == "email":
                expr += ".email()"
            elif f["format"] == "uri":
                expr += ".url()"
            if "minLength" in f:
                expr += f".min({f['minLength']})"
            elif f["required"]:
                expr += ".trim().min(1)"
            if "maxLength" in f:
                expr += f".max({f['maxLength']})"
            if "pattern" in f:
                expr += f".regex(new RegExp({json.dumps(f['pattern'])}))"
        if f["array"]:
            expr = f"z.array({expr})"
        if f["nullable"]:
            expr += ".nullable()"
        if not f["required"]:
            expr += ".optional()"
        note = (f" // invented: {', '.join(f['invented'])}"
                if f["invented"] else "")
        lines.append(f"  {prop_key(f['name'])}: {expr},{note}")
    lines += [
        "}).strict();",
        "",
        f"export type {Entity}DraftInput = z.infer<typeof "
        f"{camel(singular(name))}DraftSchema>;",
    ]
    return "\n".join(lines) + "\n"


def emit_schema_pydantic(table: dict[str, Any], model: dict[str, Any],
                         ans: Answers) -> str:
    name = table["name"]
    Entity = pascal(singular(name))
    fields = schema_fields(table, model, ans)
    uses_literal = any(f["enum"] or f["options"] for f in fields)
    uses_decimal = any(f["type"] in NUMBER_TYPES and not f["integer"] for f in fields)
    uses_any = any(f["type"] in ("jsonb", "json") for f in fields)
    temporal = sorted({{"instant": "datetime", "date": "date", "time": "time"}[f["temporal"]]
                       for f in fields if f["temporal"]
                       and not (f["temporal"] == "instant" and f["aware"])})
    aware = any(f["temporal"] == "instant" and f["aware"] for f in fields)
    typing = ["Optional"] + (["Literal"] if uses_literal else []) + (["Any"] if uses_any else [])
    lines = [
        f'"""The server\'s schema for a {singular(name.replace("_", " "))} draft.',
        "",
        "The form's validation is a courtesy; this is the control. Every rule here",
        "mirrors a database constraint, the same ones the form reads from the model,",
        "so the two cannot drift apart. A rule marked `invented` came from the mapper,",
        "not the schema: add the constraint or drop the rule. Pydantic 2.",
        '"""',
        "",
        "from __future__ import annotations",
        "",
    ]
    if temporal:
        lines.append(f"from datetime import {', '.join(temporal)}")
    if uses_decimal:
        lines.append("from decimal import Decimal")
    lines += [f"from typing import {', '.join(sorted(typing))}"]
    if any(f["type"] == "uuid" for f in fields):
        lines.append("from uuid import UUID")
    lines += ["", "from pydantic import " + ("AwareDatetime, " if aware else "")
              + "BaseModel, ConfigDict, Field", "", "",
              f"class {Entity}Draft(BaseModel):",
              "    model_config = ConfigDict(extra='forbid')", ""]
    for f in fields:
        values = f["enum"] or f["options"]
        args: list[str] = []
        if values:
            typ = "Literal[" + ", ".join(repr(v) for v in values) + "]"
        elif f["type"] in NUMBER_TYPES:
            typ = "int" if f["integer"] else "Decimal"
            if "min" in f:
                args.append(f"ge={f['min']}")
            if "max" in f:
                args.append(f"le={f['max']}")
            if "exclusiveMin" in f:
                args.append(f"gt={f['exclusiveMin']}")
            if "exclusiveMax" in f:
                args.append(f"lt={f['exclusiveMax']}")
        elif f["type"] == "boolean":
            typ = "bool"
        elif f["type"] in ("jsonb", "json"):
            typ = "Any"
        elif f["temporal"] == "instant" and f["aware"]:
            typ = "AwareDatetime"
        elif f["temporal"]:
            typ = {"instant": "datetime", "date": "date", "time": "time"}[f["temporal"]]
        elif f["type"] == "uuid":
            typ = "UUID"
        else:
            typ = "str"
            if f["format"] == "email":
                # pydantic's EmailStr needs the email-validator package;
                # the same pattern the form shows, until that is installed.
                args.append("pattern=r'^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$'")
            elif f["format"] == "uri":
                args.append("pattern=r'^https?://'")
            if "minLength" in f:
                args.append(f"min_length={f['minLength']}")
            elif f["required"]:
                args.append("min_length=1")
            if "maxLength" in f:
                args.append(f"max_length={f['maxLength']}")
            if "pattern" in f:
                args.append(f"pattern={f['pattern']!r}")
        if f["array"]:
            typ = f"list[{typ}]"
        if f["nullable"]:
            typ = f"Optional[{typ}]"
        # An omittable NOT NULL column (it has a default) keeps its bare type
        # with `None` as the default: pydantic does not validate a default, so
        # omitting the field passes and an explicit null is refused, as the
        # zod schema's `.optional()` without `.nullable()` refuses it.
        default = "..." if f["required"] else "None"
        attr = f["name"]
        if not attr.isidentifier() or keyword.iskeyword(attr):
            # `class`, `from`, `order-id`: the attribute is renamed and the
            # alias keeps the column's own name on the wire.
            attr = re.sub(r"\W", "_", attr) + "_"
            if attr[0].isdigit():                       # `2fa` (E3); `_2fa` would be private
                attr = "col_" + attr
            args.append(f"alias={f['name']!r}")
        note = (f"  # invented: {', '.join(f['invented'])}"
                if f["invented"] else "")
        lines.append(f"    {attr}: {typ} = Field({', '.join([default] + args)}){note}")
    if not fields:
        lines.append("    pass")
    return "\n".join(lines) + "\n"


def unsafe_name(name: Any) -> str:
    """Why a table's name cannot be a folder or file name under `--out`, or
    "": it goes into `features/<name>/`, `server/<name>.schema.ts` and
    `db/policies/<name>…`, so `../evil` wrote above `features/` and
    `../../evil` left `--out` (the audit's E2)."""
    if not isinstance(name, str) or not name:
        return "it is not a name"
    if any(ch in name for ch in "/\\\x00") or ".." in name or name == ".":
        return "a path separator, `..` or NUL would take the files outside --out"
    return ""


def build_files(model: dict[str, Any], ans: Answers, stack: str,
                entities: set[str] | None, server_actions: bool = False,
                framework: str = "react") -> dict[str, str]:
    if framework in ("vue", "svelte"):
        files = (build_vue_files if framework == "vue" else build_svelte_files)(model, ans, stack, entities)
        files.update(build_database_files(model, ans, entities, server_actions))
        return files
    files = {}
    css = stack == "css-modules"

    files["lib/format.ts"] = FORMAT_TS
    files["ui/cn.ts"] = CN_TS
    files["ui/index.ts"] = INDEX_TS_KIT
    kit = [
        ("Button", BUTTON_TSX, BUTTON_CSS),
        ("Field", FIELD_TSX, FIELD_CSS),
        ("Control", CONTROL_TSX, CONTROL_CSS),
        ("Badge", BADGE_TSX, BADGE_CSS),
        ("Skeleton", SKELETON_TSX, SKELETON_CSS),
        ("StateBlock", STATE_BLOCK_TSX, STATE_BLOCK_CSS),
    ]
    if not css:
        files["styles/scaffold.css"] = SCAFFOLD_CSS
    for comp, tsx, sheet in kit:
        files[f"ui/{comp}/{comp}.tsx"] = tsx if css else tailwindify(tsx, comp)
        if css:
            files[f"ui/{comp}/{comp}.module.css"] = sheet

    for table in model["tables"]:
        if table["kind"] == "join":
            continue
        if entities and table["name"] not in entities:
            continue
        name = table["name"]
        Entity = pascal(singular(name))
        Entities = pascal(name)
        base = f"features/{name}"

        files[f"{base}/{camel(name)}.types.ts"] = emit_types(table, model, ans)
        files[f"{base}/{camel(name)}.fields.ts"] = emit_fields(table, model, ans)
        pairs = [
            (f"{Entities}List", emit_list(table, model, ans),
             LIST_CSS + DATA_TABLE_CSS if ans.layout(table) == "table"
             else LIST_CSS + CARD_GRID_CSS),
            (f"{Entity}Detail", emit_detail(table, model, ans), DETAIL_CSS),
            (f"{Entity}Form", emit_form(table, model, ans, action=server_actions), FORM_CSS),
            (f"{Entities}States", emit_states(table, model, ans), STATES_CSS),
        ]
        for comp, tsx, sheet in pairs:
            kind = ("List" if comp.endswith("List")
                    else "Detail" if comp.endswith("Detail")
                    else "Form" if comp.endswith("Form") else "States")
            files[f"{base}/{comp}.tsx"] = (tsx if css
                                           else tailwindify(tsx, kind))
            if css:
                files[f"{base}/{comp}.module.css"] = sheet
        index = emit_index(table, ans)
        if server_actions:
            files[f"{base}/{Entity}ActionForm.tsx"] = emit_action_form(table)
            files[f"server/{name}.actions.ts"] = emit_actions(table, model, ans)
            form_line = f"export {{ {Entity}Form }} from './{Entity}Form';\n"
            index = index.replace(form_line, form_line + f"export {{ {Entity}ActionForm }} "
                                                         f"from './{Entity}ActionForm';\n")
        files[f"{base}/index.ts"] = index
        # The server's copy of the constraints, in both languages a Supabase
        # server is written in; delete the one the project does not use.
        files[f"server/{name}.schema.ts"] = emit_schema_zod(table, model, ans)
        files[f"server/{name}_schema.py"] = emit_schema_pydantic(table, model, ans)

    files.update(build_database_files(model, ans, entities, server_actions))
    return files


def build_database_files(model: dict[str, Any], ans: Answers, entities: set[str] | None,
                         server_actions: bool) -> dict[str, str]:
    """The database side, whatever renders the screens. A join table needs
    its policies too: the many-to-many control reads and writes it."""
    files = {"lib/supabase.ts": SUPABASE_NEXT_TS if server_actions else SUPABASE_TS}
    if server_actions:
        files["lib/supabase.server.ts"] = SUPABASE_SERVER_TS
    for table in model["tables"]:
        linked = {c["foreign_key"]["table"] for c in table["columns"] if c.get("foreign_key")}
        if entities and table["name"] not in entities and not (
                table["kind"] == "join" and linked & entities):
            continue
        files[f"db/policies/{table['name']}.policies.todo.sql"] = emit_policies(table, model, ans)
        files[f"db/policies/{table['name']}.policies.test.sql"] = emit_policy_test(table, model, ans)

    return files


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="python -m scripts.scaffold_ui",
        description="Generate a React 19, Vue 3.5 or Svelte 5 + TypeScript CRUD scaffold from a "
                    "model.json, composed from the suite's layout primitives "
                    "and role tokens.",
        epilog="The output is a starting point, not a product. Every TODO in "
               "it names a decision a human still has to make.",
    )
    ap.add_argument("model", help="model.json from introspect_schema.py")
    ap.add_argument("--out", metavar="DIR", default="src",
                    help="output root (default: src)")
    ap.add_argument("--answers", metavar="FILE",
                    help="JSON answers to the interview; without it every "
                         "question falls back to the machine's own proposal")
    ap.add_argument("--entity", action="append", metavar="TABLE",
                    help="only this entity (repeatable or comma-separated)")
    ap.add_argument("--stack", choices=("css-modules", "tailwind"), default=None,
                    help="default: the project's .design-suite.json stack (tailwind-v3 and "
                         "tailwind-v4 scaffold Tailwind; css-modules scaffolds CSS Modules), "
                         "else css-modules")
    ap.add_argument("--framework", choices=("react", "vue", "svelte"), default="react",
                    help="react (default): React 19 components (.tsx); vue: Vue 3.5 single-file "
                         "components (.vue, <script setup lang=\"ts\">, <style scoped>); svelte: "
                         "Svelte 5 components (.svelte, runes and snippets)")
    ap.add_argument("--server-actions", action="store_true",
                    help="a Next.js App Router project: each form posts to a server action "
                         "(React 19's useActionState and useFormStatus), with the server's "
                         "Supabase client")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the tree and sizes, write nothing")
    ap.add_argument("--force", action="store_true",
                    help="overwrite files that already exist")
    ap.add_argument("--strict", action="store_true",
                    help="write nothing and exit 1 when the schema has a blocking "
                         "security finding (for CI)")
    args = ap.parse_args(argv)
    if args.server_actions and args.framework != "react":
        print("scaffold_ui: --server-actions is Next.js's (React 19's useActionState); "
              f"--framework {args.framework} has no server actions.", file=sys.stderr)
        return 2
    # A flag beats the project's .design-suite.json, which beats the default (P24).
    # The scaffold writes CSS Modules or Tailwind; a vanilla-css project gets
    # CSS Modules, the nearer of the two.
    if args.stack is None:
        try:
            config = project_config()
        except ConfigError as exc:
            print(f"scaffold_ui: {exc}", file=sys.stderr)
            return 2
        args.stack = "tailwind" if config and (config.stack or "").startswith("tailwind") else "css-modules"

    mp = Path(args.model)
    if not mp.exists():
        print(f"scaffold_ui: no such file: {mp}", file=sys.stderr)
        return 2
    try:
        model = json.loads(mp.read_bytes())
    except json.JSONDecodeError as exc:
        print(f"scaffold_ui: {mp} is not valid JSON: {exc}", file=sys.stderr)
        return 2
    if not isinstance(model, dict) or model.get("$schema") != MODEL_SCHEMA:   # `[]` was a traceback
        print(f"scaffold_ui: {mp} is not a {MODEL_SCHEMA} document. Run "
              f"introspect_schema.py first.", file=sys.stderr)
        return 2
    tables = model.get("tables", [])                 # `{}` is no empty list (CodeRabbit on #138)
    if not isinstance(tables, list) or not all(isinstance(t, dict) and isinstance(t.get("name"), str)
                                               for t in tables):
        print(f"scaffold_ui: {mp}: `tables` must be a list of named objects.", file=sys.stderr)
        return 2
    if not model.get("tables"):
        print("scaffold_ui: the model has no tables.", file=sys.stderr)
        return 1

    answers_data = None
    if args.answers:
        apath = Path(args.answers)
        if not apath.exists():
            print(f"scaffold_ui: no such answers file: {apath}", file=sys.stderr)
            return 2
        try:
            answers_data = json.loads(apath.read_bytes())
        except json.JSONDecodeError as exc:
            print(f"scaffold_ui: {apath} is not valid JSON: {exc}",
                  file=sys.stderr)
            return 2
        if not isinstance(answers_data, dict):
            print(f"scaffold_ui: {apath} must be an object of answers, not "
                  f"{json.dumps(answers_data)[:40]}.", file=sys.stderr)
            return 2
    ans = Answers(answers_data)

    entities = None
    if args.entity:
        entities = {e.strip() for spec in args.entity for e in spec.split(",")
                    if e.strip()}
        known = {t["name"] for t in model["tables"]}
        unknown = entities - known
        if unknown:
            print(f"scaffold_ui: no such table(s): {', '.join(sorted(unknown))}. "
                  f"Known: {', '.join(sorted(known))}", file=sys.stderr)
            return 2

    for table in model["tables"]:
        why = unsafe_name(table.get("name"))
        if why:
            print(f"scaffold_ui: table {table.get('name')!r} cannot name a file: {why}. "
                  f"Rename it in the model, or leave it out with --entity.", file=sys.stderr)
            return 2

    files = build_files(model, ans, args.stack, entities, args.server_actions, args.framework)
    root = Path(args.out)

    # The screens are only as safe as the tables behind them: say so here,
    # where the code is about to be written (DL-A6).
    blocking = [f for f in model.get("security", {}).get("findings", [])
                if f["level"] == "block" and (entities is None or f["table"] in entities)]
    for f in blocking:
        print(f"scaffold_ui: SECURITY {f['table']}: {f['message']}", file=sys.stderr)
    if blocking and args.strict:
        print(f"scaffold_ui: {len(blocking)} blocking security finding(s) in the schema, and "
              f"--strict is set: nothing written. Fix the database, or introspect the "
              f"migrations that hold the policies (supabase-integration.md §2, §9).",
              file=sys.stderr)
        return 1
    if blocking:
        print(f"scaffold_ui: {len(blocking)} blocking security finding(s) in the schema. "
              f"The screens are generated, but fix the database before they ship "
              f"(supabase-integration.md §2, §9). --strict refuses instead.", file=sys.stderr)

    if args.dry_run:
        total = 0
        print(f"scaffold_ui: {len(files)} file(s) into {root}/ "
              f"[{args.stack}] — dry run, nothing written\n")
        for rel in sorted(files):
            size = len(files[rel].encode("utf-8"))
            total += size
            print(f"  {size:>7}  {root / rel}")
        print(f"\n  {total:>7}  total bytes")
        todos = sum(f.count("TODO(") for f in files.values())
        print(f"\n  {todos} TODO(...) marker(s) — each one is a decision a "
              f"human still owes this scaffold.")
        return 0

    written, skipped = 0, 0
    inside = root.resolve()
    for rel, content in sorted(files.items()):
        dest = root / rel
        if inside not in dest.resolve().parents:            # never past --out, whatever names it
            print(f"scaffold_ui: refusing {rel}: it resolves outside {root}", file=sys.stderr)
            return 2
        if dest.exists() and not args.force:
            skipped += 1
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")
        written += 1

    todos = sum(f.count("TODO(") for f in files.values())
    print(f"scaffold_ui: wrote {written} file(s) to {root}/"
          + (f", skipped {skipped} that already existed (use --force)"
             if skipped else "") + ".", file=sys.stderr)
    print(f"scaffold_ui: {todos} TODO(...) marker(s) left for a human. "
          f"Now run: python -m scripts.audit_design {root}/ --strict",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    # A Windows pipe (git hook, CI, `> file`) defaults to the ANSI code page,
    # where printing →, Δ or ✓ raises UnicodeEncodeError. Consoles and
    # Claude Code already use UTF-8 and are left alone.
    for _stream in (sys.stdout, sys.stderr):
        if getattr(_stream, "encoding", "utf-8").lower() not in ("utf-8", "utf8"):
            _stream.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
