#!/usr/bin/env python3
"""introspect_schema.py — step 1 and step 2 of the content-model-to-ui workflow.

Read a Postgres/Supabase schema from whichever artefact the project actually
has, normalise it into one `model.json`, run the mapping rules from
`references/field-mapping.md` over every column, and emit the list of questions
only a human can answer.

WHY THIS IS TWO JOBS IN ONE SCRIPT
----------------------------------
The mapping rules are worthless without the structural facts they key off —
nullability, length constraints, CHECK expressions, unique indexes, foreign
keys, whether a column is generated. Separating "parse" from "propose" would
mean two passes over the same half-understood data and two places for the
signal to get lost. So the normalised model and the proposal travel together,
and every proposal carries the signal that produced it and a confidence level,
so a reviewer can audit the machine's reasoning instead of trusting it.

WHAT IT READS
-------------
  *.sql   A plain DDL file: CREATE TABLE / CREATE TYPE ... AS ENUM /
          ALTER TABLE ... ADD CONSTRAINT / CREATE UNIQUE INDEX /
          COMMENT ON COLUMN. The richest source — it is the only one that
          carries CHECK constraints, lengths, defaults and comments.
  *.ts    The output of `supabase gen types typescript`. Carries tables,
          columns, nullability, enums and foreign keys. Carries NO lengths,
          NO checks, NO defaults, NO unique indexes, and collapses uuid/text/
          citext to `string` and date/timestamptz to `string`. Expect lower
          confidence and more questions from this source; that is the source's
          fault, not the mapper's.
  *.json  A schema dump. Two shapes are accepted: the documented
          `{"tables":[{"name":…,"columns":[…]}]}` shape, and a flat
          information_schema dump `{"columns":[{"table_name":…}], …}`.

Every source is normalised to the same model, and `model.fidelity` records
exactly which facts the source could not carry so nobody mistakes an absent
constraint for a permissive one.

USAGE
-----
    # The common case — write model.json beside the schema
    python -m scripts.introspect_schema schema.sql --out model.json

    # From generated types, naming the schema you care about
    python -m scripts.introspect_schema database.types.ts --schema public -o model.json

    # Read the proposal without writing anything
    python -m scripts.introspect_schema schema.sql --summary

    # Just the human step: the interview, ready to answer
    python -m scripts.introspect_schema schema.sql --questions

    # Force a parser when the extension lies
    python -m scripts.introspect_schema dump.txt --format ddl -o model.json

Answer the questions by writing `{"<question id>": <value>}` into an answers
file and handing it to `scaffold_ui.py --answers`. Every question ships with a
pre-filled default, so the human step is a five-minute review, not a design
exercise.

Exit codes: 0 model written · 1 nothing usable found in the input · 2 bad
invocation or an unreadable path.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Iterable

MODEL_SCHEMA = "content-model-to-ui/model/1"

# ---------------------------------------------------------------------------
# Vocabulary — the closed set of controls the scaffolder knows how to render.
#
# Keep this closed for the same reason the spacing scale is closed: an open set
# means every schema invents a new control and the generated UI stops being one
# UI. Adding a control here means teaching scaffold_ui.py to render it.
# ---------------------------------------------------------------------------

CONTROLS = {
    "text-input":        "one line of free text",
    "textarea":          "several lines, no formatting",
    "rich-text":         "formatted long-form body — needs an editor dependency",
    "slug-input":        "URL segment: lowercased, validated, derived from the title",
    "email-input":       "type=email, one address",
    "url-input":         "type=url, absolute",
    "tel-input":         "type=tel, formatted on blur, never on keystroke",
    "password-input":    "write-only; never rendered back",
    "number-input":      "a quantity the user types",
    "currency-input":    "money — see field-mapping.md §7",
    "percent-input":     "a rate displayed as %, stored as a fraction or basis points",
    "stepper":           "a small integer the user nudges rather than types",
    "checkbox":          "a binary the user sets as part of a form",
    "switch":            "a binary that takes effect immediately",
    "select":            "a closed set under ~20 options",
    "radio-group":       "a closed set under ~5 options where all must be visible",
    "multi-select":      "several values from a closed set",
    "combobox":          "type-to-filter over a set too big to list, small enough to fetch",
    "multi-combobox":    "the same, keeping several — the many-to-many control",
    "record-picker":     "a modal with its own search and paging, for a large parent table",
    "inline-subtable":   "owned children edited in place inside the parent's form",
    "linked-list":       "children that own themselves — listed on the parent's "
                         "detail page, edited on their own screens",
    "date-picker":       "a calendar date with no time and no zone",
    "datetime-picker":   "an instant — always carries an explicit zone",
    "time-picker":       "a wall-clock time",
    "date-range":        "two dates that validate against each other",
    "file-upload":       "an arbitrary file in storage",
    "image-upload":      "an image in storage, with a preview and a crop",
    "color-picker":      "a colour value",
    "json-editor":       "raw JSON with a parse gate — the honest fallback",
    "key-value-editor":  "flat string→string maps that users actually edit",
    "tag-input":         "an open-ended array of short strings",
    "geo-point":         "a map picker",
    "readonly-text":     "displayed, never edited",
    "readonly-timestamp": "displayed as relative-with-absolute-on-hover, never edited",
    "hidden":            "present in the model, absent from every screen",
}

CONFIDENCE = ("high", "medium", "low")

# ---------------------------------------------------------------------------
# Postgres type normalisation
# ---------------------------------------------------------------------------

TYPE_ALIASES = {
    "int": "integer", "int4": "integer", "int2": "smallint", "int8": "bigint",
    "serial": "integer", "serial4": "integer", "bigserial": "bigint",
    "smallserial": "smallint",
    "bool": "boolean",
    "varchar": "character varying", "character varying": "character varying",
    "char": "character", "bpchar": "character",
    "float4": "real", "float8": "double precision",
    "decimal": "numeric",
    "timestamptz": "timestamp with time zone",
    "timestamp": "timestamp without time zone",
    "timetz": "time with time zone",
    "time": "time without time zone",
    "json": "json", "jsonb": "jsonb",
    "uuid": "uuid", "text": "text", "citext": "citext",
    "date": "date", "numeric": "numeric", "money": "money",
    "bytea": "bytea", "tsvector": "tsvector", "interval": "interval",
    "inet": "inet", "cidr": "cidr", "macaddr": "macaddr",
    "geography": "geography", "geometry": "geometry", "point": "point",
}

NUMERIC_TYPES = {"integer", "smallint", "bigint", "numeric", "real",
                 "double precision", "money"}
INTEGER_TYPES = {"integer", "smallint", "bigint"}
TEXTUAL_TYPES = {"text", "character varying", "character", "citext"}
TEMPORAL_TYPES = {"date", "timestamp with time zone",
                  "timestamp without time zone",
                  "time with time zone", "time without time zone"}

# ---------------------------------------------------------------------------
# Name signals — the semantic layer the type system cannot carry.
#
# Ordered: the FIRST match wins, so the most specific patterns come first.
# Each entry is (compiled pattern, control, confidence, signal text, extras).
# `extras` is merged into the column's ui block, which is how money gets its
# storage unit and timestamps get their zone policy.
# ---------------------------------------------------------------------------

def _p(rx: str) -> re.Pattern[str]:
    return re.compile(rx, re.I)


NAME_RULES: list[tuple[re.Pattern[str], str, str, str, dict[str, Any]]] = [
    # Credentials, by the PATTERNS field-mapping.md promises (`*_token`,
    # `*_hash`, `*_secret`, …), not a list of exact names: `api_token`,
    # `reset_token`, `webhook_secret` and `token_hash` were displayed and
    # editable. Hiding them here is the UI half only — the database must not
    # let anon/authenticated read them at all (see supabase-integration.md).
    (_p(r"^(password|passwd|pwd|secret|token|salt|otp|totp|api_?key|private_key)$"
        r"|_(password|passwd|pwd|secret|token|hash|salt|digest|otp)$"
        r"|(^|_)(api|private|secret|access|signing|encryption|client)_key$"
        r"|^encrypted_"),
     "password-input", "high",
     "name is a credential — never displayed and never edited here. The "
     "database must also stop the anon and authenticated roles reading it "
     "(revoke the column's SELECT, or keep it in a private schema): a "
     "`select('*')` would still send it to the browser",
     {"write_only": True, "never_display": True}),

    (_p(r"(^|_)(email|email_address|contact_email)$"),
     "email-input", "high", "name says email", {"format": "email"}),

    # Media BEFORE the generic URL rule. `avatar_url` is a storage object that
    # happens to be addressed by URL; treating it as a link gives the user a
    # text box where they needed an upload with a preview. Order is the fix,
    # and it is the kind of ordering bug that only shows up on a real schema.
    (_p(r"^(avatar|image|photo|picture|thumbnail|thumb|cover|banner|logo|"
        r"hero|profile_image|cover_image|hero_image|featured_image)"
        r"(_url|_path|_key|_id)?$"),
     "image-upload", "high",
     "name says image — a storage object, not a string the user types",
     {"storage_backed": True, "media": "image"}),

    (_p(r"^(file|attachment|document|asset|upload|resume|invoice_pdf)"
        r"(_url|_path|_key)?$"),
     "file-upload", "high", "name says file — a storage object",
     {"storage_backed": True, "media": "file"}),

    (_p(r"(^|_)(url|uri|href|link|website|homepage|permalink|webhook_url)$"),
     "url-input", "high", "name says URL", {"format": "uri"}),

    (_p(r"(^|_)slug$|^slug$|^handle$|^permalink_slug$"),
     "slug-input", "high",
     "name says slug — derived from the title, uniquely indexed, and the "
     "thing a URL breaks on if it changes",
     {"format": "slug", "derive_from_title": True}),

    (_p(r"(^|_)(phone|phone_number|mobile|telephone|tel|fax)$"),
     "tel-input", "high", "name says phone number", {"format": "tel"}),

    (_p(r"_(cents|minor|minor_units|in_cents|pennies|cent)$"),
     "currency-input", "high",
     "name declares minor units — the integer is NOT a quantity",
     {"money": {"storage": "minor-units", "scale": 100}}),

    (_p(r"(^|_)(price|amount|cost|total|subtotal|fee|balance|salary|revenue|"
        r"charge|refund|discount|tax|shipping|payout|budget|mrr|arr)"
        r"(_[a-z]+)?$"),
     "currency-input", "medium",
     "name is a money word — confirm the storage unit before trusting it",
     {"money": {"storage": "unknown", "scale": None}}),

    (_p(r"(^|_)(rate|percent|percentage|pct|ratio|margin|share)$"),
     "percent-input", "medium",
     "name is a rate — confirm whether 0.15 or 15 is stored",
     {"percent": {"storage": "unknown"}}),

    (_p(r"^(is|has|can|should|was|are|allow|enable|require)_"),
     "switch", "high",
     "is_/has_ prefix — a boolean the user flips, not a form checkbox",
     {}),

    (_p(r"_(enabled|disabled|active|visible|published|archived|verified|"
        r"deleted|featured|locked|approved)$"),
     "switch", "medium", "name reads as a state flag", {}),

    (_p(r"^(currency|currency_code|iso_currency)$"),
     "select", "medium",
     "a currency code is a closed set of about 180 values that nobody types "
     "by hand — and it is the other half of every money column",
     {"options_source": "iso-4217",
      "options": ["USD", "EUR", "GBP", "CAD", "AUD", "JPY", "CHF", "SEK"]}),

    (_p(r"^(country|country_code|locale|language|language_code|timezone|"
        r"time_zone|tz)$"),
     "combobox", "medium",
     "a standards list — long, closed, and searchable; never a text input",
     {"options_source": "standard-list"}),

    (_p(r"(^|_)(description|body|content|summary|excerpt|bio|about|notes?|"
        r"message|comment|abstract|caption|instructions)$"),
     "textarea", "high",
     "name is a long-form field — a single-line input truncates it visually "
     "and users stop writing",
     {"long_form": True}),

    (_p(r"(^|_)(status|state|stage|phase|kind|type|category|level|priority|"
        r"severity|visibility|role)$"),
     "select", "medium",
     "name is a state word — almost always a closed set even when the column "
     "is plain text",
     {"closed_set_suspected": True}),

    (_p(r"(^|_)(sort_order|position|rank|ordinal|weight|display_order|"
        r"sequence|index)$"),
     "hidden", "high",
     "an ordering column — users reorder by dragging rows, never by typing a "
     "number into a form field",
     {"ordering": True}),

    (_p(r"^(metadata|meta|settings|config|configuration|options|properties|"
        r"attributes|payload|extra|custom_fields|preferences)$"),
     "json-editor", "medium",
     "name is a bag — needs a human to say which keys are real before it can "
     "be anything better than a JSON box",
     {}),

    (_p(r"(^|_)(color|colour|brand_color|accent_color)$"),
     "color-picker", "medium", "name says colour", {}),

    (_p(r"(^|_)(tags|labels|keywords|categories|skills)$"),
     "tag-input", "medium", "name is a plural bag of short strings", {}),

    (_p(r"^(lat|latitude|lng|lon|longitude|coordinates|location|geom|geog)$"),
     "geo-point", "medium", "name is geographic", {}),
]

# Timestamp columns that the application writes, not the user.
SYSTEM_TIMESTAMPS = _p(
    r"^(created_at|updated_at|inserted_at|modified_at|deleted_at|"
    r"last_seen_at|last_sign_in_at|confirmed_at|email_confirmed_at)$")

TIMESTAMP_SUFFIX = _p(r"_at$|^(created|updated|deleted|published|expires|"
                      r"starts|ends|scheduled|completed|due)(_on|_date)?$")

TITLE_CANDIDATES = ("title", "name", "display_name", "full_name", "label",
                    "subject", "headline", "heading", "company_name",
                    "product_name", "username", "email", "slug")

# Columns that carry no information a person reading a list wants.
# Columns a scanning eye gets nothing from. `created_at` / `updated_at` are
# deliberately absent — they are the most useful default second column there
# is; the temporal cap in _assign_placement stops them crowding the row.
LIST_NEVER = _p(r"^(id|.*_id|deleted_at|search_vector|fts|tsv|password.*|"
                r".*_hash|metadata|settings|config)$")

# Columns that do not make a table a real entity — the join-table test.
JOIN_TABLE_NOISE = _p(r"^(id|created_at|updated_at|inserted_at|sort_order|"
                      r"position|rank|ordinal|display_order)$")

LOOKUP_TABLE_NAMES = _p(r"(status|state|type|kind|category|categories|role|"
                        r"roles|tag|tags|label|labels|currency|currencies|"
                        r"country|countries|plan|plans|tier|tiers)$")


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

@dataclass
class Column:
    name: str
    type: str = "text"                       # normalised Postgres type
    raw_type: str = ""                       # exactly as the source spelled it
    nullable: bool = True
    default: str | None = None
    generated: bool = False                  # identity / GENERATED ALWAYS AS
    comment: str | None = None
    max_length: int | None = None
    numeric_precision: int | None = None
    numeric_scale: int | None = None
    is_array: bool = False
    enum: str | None = None                  # enum type name
    primary_key: bool = False
    unique: bool = False                     # participates in a 1-col unique index
    checks: list[str] = field(default_factory=list)
    foreign_key: dict[str, Any] | None = None
    ui: dict[str, Any] = field(default_factory=dict)


@dataclass
class Relationship:
    kind: str                                # many-to-one | one-to-many | many-to-many
    to: str
    via: str | None = None                   # join table, for many-to-many
    local_column: str | None = None
    remote_column: str | None = None
    on_delete: str | None = None
    optional: bool = False                   # nullable FK: the row can stand alone
    control: str | None = None
    confidence: str | None = None
    signal: str | None = None


@dataclass
class Table:
    name: str
    kind: str = "entity"                     # entity | join
    comment: str | None = None
    primary_key: list[str] = field(default_factory=list)
    columns: list[Column] = field(default_factory=list)
    unique_indexes: list[list[str]] = field(default_factory=list)
    relationships: list[Relationship] = field(default_factory=list)
    screens: dict[str, Any] = field(default_factory=dict)
    # Row-level security, as the source states it. None: the source cannot
    # say (generated types, a JSON dump). False: DDL that never enables it.
    rls: bool | None = None
    policies: list[dict[str, Any]] = field(default_factory=list)
    # Columns a signed-in user may UPDATE. None: the table-level grant
    # stands (Supabase's default), so every column. A list: the table-level
    # grant was revoked and these columns were granted back.
    update_columns: list[str] | None = None
    ineffective_revokes: list[str] = field(default_factory=list)

    def col(self, name: str) -> Column | None:
        return next((c for c in self.columns if c.name == name), None)


@dataclass
class Model:
    source: dict[str, Any] = field(default_factory=dict)
    fidelity: dict[str, Any] = field(default_factory=dict)
    enums: dict[str, list[str]] = field(default_factory=dict)
    tables: list[Table] = field(default_factory=list)
    questions: list[dict[str, Any]] = field(default_factory=list)
    security: dict[str, Any] = field(default_factory=dict)

    def table(self, name: str) -> Table | None:
        return next((t for t in self.tables if t.name == name), None)


class SchemaError(Exception):
    """A parse failure the user can act on."""


# ---------------------------------------------------------------------------
# Shared parsing helpers
# ---------------------------------------------------------------------------

def strip_sql_comments(text: str) -> str:
    out: list[str] = []
    i, n = 0, len(text)
    while i < n:
        ch = text[i]
        if ch == "'":
            j = i + 1
            while j < n:
                if text[j] == "'" and (j + 1 >= n or text[j + 1] != "'"):
                    break
                if text[j] == "'" and text[j + 1] == "'":
                    j += 1
                j += 1
            out.append(text[i:j + 1])
            i = j + 1
            continue
        if ch == '"':
            j = text.find('"', i + 1)
            j = n if j == -1 else j
            out.append(text[i:j + 1])
            i = j + 1
            continue
        if ch == "-" and text[i:i + 2] == "--":
            j = text.find("\n", i)
            j = n if j == -1 else j
            out.append(" " * (j - i))
            i = j
            continue
        if ch == "/" and text[i:i + 2] == "/*":
            j = text.find("*/", i + 2)
            j = n if j == -1 else j + 2
            out.append(" " * (j - i))
            i = j
            continue
        out.append(ch)
        i += 1
    return "".join(out)


RE_DOLLAR_TAG = re.compile(r"\$(?:[A-Za-z_]\w*)?\$")


def dollar_quote_end(text: str, i: int) -> int | None:
    """The index just past a `$$ … $$` (or `$tag$ … $tag$`) body that opens
    at `i`, as pg_dump writes every function: the `;` inside end nothing."""
    m = RE_DOLLAR_TAG.match(text, i)
    if not m:
        return None
    close = text.find(m.group(0), m.end())
    return len(text) if close == -1 else close + len(m.group(0))


def split_top_level(text: str, sep: str) -> list[str]:
    """Split on `sep` at paren depth 0, respecting quotes."""
    parts: list[str] = []
    buf: list[str] = []
    depth = 0
    i, n = 0, len(text)
    while i < n:
        ch = text[i]
        end = dollar_quote_end(text, i) if ch == "$" else None
        if end is not None:
            buf.append(text[i:end])
            i = end
            continue
        if ch in "'\"":
            quote = ch
            buf.append(ch)
            i += 1
            while i < n:
                buf.append(text[i])
                if text[i] == quote:
                    if quote == "'" and i + 1 < n and text[i + 1] == "'":
                        buf.append(text[i + 1])
                        i += 2
                        continue
                    break
                i += 1
            i += 1
            continue
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        if ch == sep and depth == 0:
            parts.append("".join(buf))
            buf = []
            i += 1
            continue
        buf.append(ch)
        i += 1
    if "".join(buf).strip():
        parts.append("".join(buf))
    return parts


def unquote_ident(s: str) -> str:
    s = s.strip().rstrip(";").strip()
    if s.startswith('"') and s.endswith('"'):
        return s[1:-1]
    return s


# Words that stay quoted: Postgres's reserved keywords, plus those this
# parser reads as the start of a clause. Quoting is what makes them names.
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
# No `$`: Postgres allows it in a bare name, but this parser reads names as
# word characters, so `"amount$usd"` keeps its quotes (N16).
RE_SIMPLE_IDENT = re.compile(r"[a-z_][a-z0-9_]*")


def unquote_identifiers(text: str) -> str:
    """`"public"."products"` -> `public.products`, `"text"` -> `text`.

    `pg_dump --quote-all-identifiers`, which `supabase db pull` uses, quotes
    every name, types included (DL-A7). A name that needs its quotes (capitals,
    spaces, a reserved word) keeps them; strings and `$$` bodies are left as
    they are."""
    out: list[str] = []
    i, n = 0, len(text)
    while i < n:
        ch = text[i]
        end = dollar_quote_end(text, i) if ch == "$" else None
        if end is None and ch == "'":
            end = i + 1
            while end < n and (text[end] != "'" or text[end + 1:end + 2] == "'"):
                end += 2 if text[end] == "'" else 1
            end += 1
        if end is not None:
            out.append(text[i:end])
            i = end
            continue
        if ch == '"':
            close = text.find('"', i + 1)
            close = n if close == -1 else close
            name = text[i + 1:close]
            simple = RE_SIMPLE_IDENT.fullmatch(name) and name not in KEEP_QUOTED
            out.append(name if simple else text[i:close + 1])
            i = close + 1
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def bare_table_name(qualified: str) -> str:
    """`public.products` and `"public"."products"` both become `products`."""
    parts = [unquote_ident(p) for p in split_top_level(qualified.strip(), ".")]
    return parts[-1] if parts else qualified.strip()


def normalise_type(raw: str) -> tuple[str, int | None, int | None, int | None, bool]:
    """-> (normalised type, max_length, precision, scale, is_array)"""
    t = raw.strip().lower().replace('"', "")
    is_array = False
    while t.endswith("[]"):
        is_array = True
        t = t[:-2].strip()
    # `public.order_status`, `pg_catalog.text`, `extensions.citext` (DL-A7).
    t = re.sub(r"^(?:[a-z_][\w$]*\.)+(?=[a-z_])", "", t)
    if t.startswith("array<") or t.startswith("_"):
        is_array = True
        t = t[6:].rstrip(">") if t.startswith("array<") else t[1:]
    length = precision = scale = None
    m = re.match(r"^([a-z_][\w ]*?)\s*\(([^)]*)\)\s*(.*)$", t)
    if m:
        base, args = m.group(1).strip(), m.group(2)
        tail = m.group(3).strip()
        nums = [a.strip() for a in args.split(",") if a.strip().isdigit()]
        if base in ("numeric", "decimal"):
            precision = int(nums[0]) if nums else None
            scale = int(nums[1]) if len(nums) > 1 else None
        elif nums:
            length = int(nums[0])
        t = f"{base} {tail}".strip()
    t = re.sub(r"\s+", " ", t)
    return TYPE_ALIASES.get(t, t), length, precision, scale, is_array


# ---------------------------------------------------------------------------
# Parser 1 — plain DDL
# ---------------------------------------------------------------------------

COL_MODIFIER_SPLIT = _p(r"\s+")

RE_CREATE_TABLE = _p(r"^\s*create\s+(?:unlogged\s+|temp\s+|temporary\s+)?table"
                     r"(?:\s+if\s+not\s+exists)?\s+((?:\"[^\"]+\"|[\w.])+)\s*\(")
RE_CREATE_ENUM = _p(r"^\s*create\s+type\s+((?:\"[^\"]+\"|[\w.])+)\s+as\s+enum\s*\((.*)\)\s*$")
RE_CREATE_INDEX = _p(r"^\s*create\s+(unique\s+)?index(?:\s+concurrently)?"
                     r"(?:\s+if\s+not\s+exists)?\s+(?:\"[^\"]+\"|[\w.])+\s+on\s+((?:\"[^\"]+\"|[\w.])+)"
                     r"(?:\s+using\s+\w+)?\s*\((.*?)\)\s*(where\b.*)?$")
RE_ALTER_TABLE = _p(r"^\s*alter\s+table(?:\s+if\s+exists)?(?:\s+only)?\s+((?:\"[^\"]+\"|[\w.])+)\s+(.*)$")
RE_ADD_CONSTRAINT = _p(r"^add\s+(?:constraint\s+(?:\"[^\"]+\"|[\w$]+)\s+)?"
                       r"(?=(?:primary\s+key|foreign\s+key|unique|check|exclude|not\s+null)\b)")
RE_ADD_COLUMN = _p(r"^add\s+(?:column\s+)?(?:if\s+not\s+exists\s+)?(.*)$")
RE_DROP_COLUMN = _p(r"^drop\s+(?:column\s+)?(?:if\s+exists\s+)?(\"[^\"]+\"|\w+)")
RE_ALTER_COLUMN = _p(r"^alter\s+(?:column\s+)?(\"[^\"]+\"|\w+)\s+(.*)$")
RE_RENAME = _p(r"^rename\s+(?:(?:column\s+)?(?!to\b)(\"[^\"]+\"|\w+)\s+)?to\s+(\"[^\"]+\"|\w+)$")
RE_COMMENT_COL = _p(r"^\s*comment\s+on\s+column\s+((?:\"[^\"]+\"|[\w.])+)\s+is\s+'(.*)'\s*$")
RE_COMMENT_TABLE = _p(r"^\s*comment\s+on\s+table\s+((?:\"[^\"]+\"|[\w.])+)\s+is\s+'(.*)'\s*$")
RE_FK_CLAUSE = _p(r"foreign\s+key\s*\(([^)]*)\)\s*references\s+((?:\"[^\"]+\"|[\w.])+)"
                  r"\s*(?:\(([^)]*)\))?(.*)$")
RE_PK_CLAUSE = _p(r"^primary\s+key\s*\(([^)]*)\)")
RE_UNIQUE_CLAUSE = _p(r"^unique\s*(?:nulls\s+(?:not\s+)?distinct\s*)?\(([^)]*)\)")
RE_CHECK_CLAUSE = _p(r"^check\s*\((.*)\)\s*$")
# Postgres 18 names a not-null constraint: `constraint t_name_nn not null name` (N19).
RE_NOT_NULL_CLAUSE = _p(r"^not\s+null\s+(\"[^\"]+\"|\w+)")
RE_INLINE_REFS = _p(r"\breferences\s+((?:\"[^\"]+\"|[\w.])+)\s*(?:\(([^)]*)\))?(.*)$")
# Row-level security (DL-A6): the statements the parser used to skip.
RE_ALTER_RLS = _p(r"^\s*alter\s+table(?:\s+if\s+exists)?(?:\s+only)?\s+((?:\"[^\"]+\"|[\w.])+)\s+"
                  r"(enable|disable|force|no\s+force)\s+row\s+level\s+security\s*$")
RE_CREATE_POLICY = _p(r"^\s*create\s+policy\s+(\"[^\"]+\"|\w+)\s+on\s+((?:\"[^\"]+\"|[\w.])+)\s*(.*)$")
RE_REVOKE = _p(r"^\s*revoke\s+(.+?)\s+on\s+(?:table\s+)?((?:\"[^\"]+\"|[\w.])+)\s+from\s+(.+)$")
RE_GRANT = _p(r"^\s*grant\s+(.+?)\s+on\s+(?:table\s+)?((?:\"[^\"]+\"|[\w.])+)\s+to\s+(.+)$")
RE_DROP_POLICY = _p(r"^\s*drop\s+policy(?:\s+if\s+exists)?\s+(\"[^\"]+\"|\w+)\s+on\s+((?:\"[^\"]+\"|[\w.])+)")
RE_POLICY_AS = _p(r"\s*as\s+(permissive|restrictive)\b")
RE_POLICY_FOR = _p(r"\s*for\s+(all|select|insert|update|delete)\b")
RE_POLICY_TO = _p(r"\s*to\s+(.+?)(?=\s+using\s*\(|\s+with\s+check\s*\(|\s*$)")
RE_POLICY_USING = _p(r"\s*using\s*\(")
RE_POLICY_CHECK = _p(r"\s*with\s+check\s*\(")

# Roles a browser never holds: a policy written for them alone is not a way in.
SERVER_ROLES = {"service_role", "postgres", "supabase_admin", "supabase_auth_admin",
                "supabase_storage_admin", "dashboard_user"}


def _parse_policy(name: str, tail: str) -> dict[str, Any]:
    """`CREATE POLICY name ON table` and what follows it, in the order Postgres
    takes the clauses: AS, FOR, TO, USING, WITH CHECK."""
    policy: dict[str, Any] = {"name": name, "command": "all", "roles": ["public"],
                              "permissive": True, "using": None, "with_check": None}
    m = RE_POLICY_AS.match(tail)
    if m:
        policy["permissive"] = m.group(1).lower() == "permissive"
        tail = tail[m.end():]
    m = RE_POLICY_FOR.match(tail)
    if m:
        policy["command"] = m.group(1).lower()
        tail = tail[m.end():]
    m = RE_POLICY_TO.match(tail)
    if m:
        policy["roles"] = [unquote_ident(r.strip()).lower() for r in m.group(1).split(",") if r.strip()]
        tail = tail[m.end():]
    for key, rx in (("using", RE_POLICY_USING), ("with_check", RE_POLICY_CHECK)):
        m = rx.match(tail)
        if m:
            depth, i = 0, m.end() - 1
            while i < len(tail):
                depth += (tail[i] == "(") - (tail[i] == ")")
                if depth == 0:
                    break
                i += 1
            policy[key] = tail[m.end():i].strip()
            tail = tail[i + 1:]
    return policy


def _apply_privileges(table: Table, verb: str, privileges: str, grantees: str) -> None:
    """GRANT and REVOKE of UPDATE for a signed-in user, replayed in order.

    Postgres: "if a role has been granted privileges on a table, then revoking
    the same privileges from individual columns will have no effect". Supabase
    grants table-level UPDATE to `authenticated` by default, so a column is
    protected only by revoking UPDATE on the table and granting back the
    columns a user may change."""
    if not re.search(r"\bauthenticated\b", grantees, re.I):
        return
    whole_table = bool(re.match(r"\s*all\b", privileges, re.I))
    columns: list[str] = []
    for m in re.finditer(r"\bupdate\b\s*(?:\(([^)]*)\))?", privileges, re.I):
        if m.group(1) is None:
            whole_table = True
        else:
            columns += [unquote_ident(c.strip()) for c in m.group(1).split(",") if c.strip()]
    if verb == "revoke":
        if whole_table:
            table.update_columns = []
            table.ineffective_revokes = []
        elif table.update_columns is None:
            table.ineffective_revokes += [c for c in columns if c not in table.ineffective_revokes]
        else:
            table.update_columns = [c for c in table.update_columns if c not in columns]
    elif whole_table:
        table.update_columns = None
    elif table.update_columns is not None:
        table.update_columns += [c for c in columns if c not in table.update_columns]


def _pinned_to_caller(column: str, check: str) -> bool:
    """Whether a policy condition fixes `column` to who is calling:
    `owner_id = auth.uid()`, `org_id = (select … auth.uid() …)`. Naming the
    column is not enough: `role in ('member', 'admin')` lets a member choose."""
    col = re.escape(column)
    if re.search(rf"auth\.\w+\s*\(\s*\)[\s)]*=\s*{col}(?!\w)", check, re.I):
        return True
    for m in re.finditer(rf"(?<![\w.]){col}\s*=\s*", check, re.I):
        rest = check[m.end():]
        operand = "(" + _balanced_slice(rest, 0) + ")" if rest.startswith("(") else re.split(r"\s", rest, 1)[0]
        if re.search(r"\bauth\.\w+\s*\(", operand, re.I):
            return True
    return False


def _is_true(expr: str | None) -> bool:
    return expr is not None and re.sub(r"[\s()]", "", expr).lower() == "true"


def security_pass(model: Model) -> None:
    """What the source says about who may reach each table (DL-A6, DL-C1).

    `block` findings are holes: a table anyone holding the publishable key can
    read and write, or a policy that lets every signed-in user write every
    row. `warn` findings need a human to look. Nothing is reported for a
    source that cannot state row-level security."""
    findings: list[dict[str, Any]] = []

    def add(level: str, table: Table, code: str, message: str, policy: str | None = None) -> None:
        entry = {"level": level, "table": table.name, "code": code, "message": message}
        if policy:
            entry["policy"] = policy
        findings.append(entry)

    for t in model.tables:
        if t.rls is None:
            continue
        if not t.rls:
            add("block", t, "rls-off",
                "row-level security is off: with the publishable key, anyone can read and "
                "write every row" + (f" ({len(t.policies)} policy(ies) exist and do nothing "
                                     f"until it is enabled)" if t.policies else ""))
            continue
        for_users = [p for p in t.policies if not set(p["roles"]) <= SERVER_ROLES]
        # A restrictive policy grants nothing: it narrows what the permissive
        # ones allow, and Postgres ANDs it with them.
        open_to_users = [p for p in for_users if p["permissive"]]
        narrowing = [p for p in for_users if not p["permissive"]]

        def narrowed(command: str) -> bool:
            return any(r["command"] in (command, "all")
                       and not _is_true(r["with_check"] if r["with_check"] is not None else r["using"])
                       for r in narrowing)

        if not open_to_users:
            add("warn", t, "no-policy",
                "row-level security is on with no policy for a signed-in user: every query "
                "returns nothing, so these screens stay empty until a policy exists")
            continue
        for p in open_to_users:
            cmd = p["command"]
            row_check = p["using"] if cmd in ("all", "update", "delete") else None
            # Postgres: with no WITH CHECK, the USING expression checks the new row too.
            new_row_check = (p["with_check"] if p["with_check"] is not None else p["using"]) \
                if cmd in ("all", "insert", "update") else None
            if (cmd != "select" and (_is_true(row_check) or _is_true(new_row_check))
                    and not narrowed(cmd)):
                add("block", t, "open-write",
                    f"policy \"{p['name']}\" lets {', '.join(p['roles'])} "
                    f"{'write' if cmd == 'all' else cmd} every row: its condition is `true`",
                    policy=p["name"])
        writers = [p for p in open_to_users if p["command"] in ("all", "update")]
        if writers:
            exposed = []
            def check_of(p: dict[str, Any]) -> str:
                return p["with_check"] if p["with_check"] is not None else (p["using"] or "")

            for c in t.columns:
                if not c.ui.get("authority"):
                    continue
                if t.update_columns is not None and c.name not in t.update_columns:
                    continue                                  # no UPDATE privilege on it
                # Permissive policies are ORed, so each must pin the column;
                # a restrictive one is ANDed, so one is enough.
                pinned = (all(_pinned_to_caller(c.name, check_of(p)) for p in writers)
                          or any(_pinned_to_caller(c.name, check_of(r)) for r in narrowing
                                 if r["command"] in ("all", "update")))
                if not pinned:
                    exposed.append(c.name)
            if exposed:
                cols = ", ".join(exposed)
                safe = ", ".join(c.name for c in t.columns
                                 if c.ui.get("placement", {}).get("form") and not c.ui.get("authority"))
                dead = [c for c in t.ineffective_revokes if c in exposed]
                add("warn", t, "authority-writable",
                    f"a user who may update a row may change {cols}: the table-level UPDATE "
                    f"grant covers every column and no policy pins them to the caller. "
                    + (f"The column revoke on {', '.join(dead)} has no effect while the "
                       f"table-level grant stands. " if dead else "")
                    + f"If that is not intended: revoke update on {t.name} from authenticated; "
                    f"grant update ({safe or '…'}) on {t.name} to authenticated;")

    model.security = {**model.security,
                      "stated_by_source": any(t.rls is not None for t in model.tables),
                      "findings": findings}


def security_block(model: Model) -> list[str]:
    """The lines `--summary` prints before anything else."""
    if not model.security.get("stated_by_source"):
        return ["SECURITY    unknown: this source carries no row-level security or policies.",
                "            Introspect the DDL (migrations or `supabase db dump`) to check it.", ""]
    out = ["SECURITY    as this DDL states it"]
    if not model.security.get("rls_statements"):
        out.append("            The file has no row-level security statement at all. If the policies")
        out.append("            live in another migration, introspect the files together.")
    by_table: dict[str, list[dict[str, Any]]] = {}
    for f in model.security.get("findings", []):
        by_table.setdefault(f["table"], []).append(f)
    width = max((len(t.name) for t in model.tables), default=0)
    for t in model.tables:
        found = by_table.get(t.name, [])
        if not found:
            commands = sorted({p["command"] for p in t.policies})
            out.append(f"  ok     {t.name:<{width}}  RLS on · {len(t.policies)} policy(ies): "
                       f"{', '.join(commands)}")
        for f in found:
            out.append(f"  {f['level'].upper() if f['level'] == 'block' else 'warn':<6} "
                       f"{t.name:<{width}}  {f['message']}")
    blocks = sum(1 for f in model.security.get("findings", []) if f["level"] == "block")
    if blocks:
        out.append(f"            {blocks} blocking: fix these in the database before the screens ship "
                   f"(supabase-integration.md §2, §9).")
    out.append("")
    return out


def parse_ddl(text: str) -> Model:
    model = Model()
    rls_statements = 0
    clean = strip_sql_comments(text)
    clean = re.sub(r"(?m)^[ \t]*\\.*$", "", clean)      # psql meta-commands: pg_dump 18's \restrict
    clean = unquote_identifiers(clean)
    statements = [s.strip() for s in split_top_level(clean, ";") if s.strip()]

    for stmt in statements:
        one_line = re.sub(r"\s+", " ", stmt).strip()

        m = RE_CREATE_ENUM.match(one_line)
        if m:
            name = bare_table_name(m.group(1))
            values = [v.strip().strip("'") for v in split_top_level(m.group(2), ",")]
            model.enums[name] = [v for v in values if v]
            continue

        m = RE_CREATE_TABLE.match(one_line)
        if m:
            model.tables.append(_parse_create_table(stmt, model))
            continue

        m = RE_CREATE_INDEX.match(one_line)
        if m:
            is_unique = bool(m.group(1))
            tname = bare_table_name(m.group(2))
            cols = [unquote_ident(c.split()[0]) if c.split() else ""
                    for c in split_top_level(m.group(3), ",")]
            cols = [c for c in cols if c and "(" not in c]
            partial = bool(m.group(4))
            t = model.table(tname)
            if t and is_unique and cols and not partial:
                t.unique_indexes.append(cols)
            continue

        m = RE_ALTER_RLS.match(one_line)
        if m:
            rls_statements += 1
            t = model.table(bare_table_name(m.group(1)))
            verb = m.group(2).lower()
            if t and verb in ("enable", "disable"):
                t.rls = verb == "enable"
            continue

        m = RE_CREATE_POLICY.match(one_line)
        if m:
            rls_statements += 1
            t = model.table(bare_table_name(m.group(2)))
            if t:
                t.policies.append(_parse_policy(unquote_ident(m.group(1)), m.group(3)))
            continue

        m = RE_DROP_POLICY.match(one_line)
        if m:
            # Migrations are replayed in order: a dropped policy is gone.
            t = model.table(bare_table_name(m.group(2)))
            if t:
                name = unquote_ident(m.group(1))
                t.policies = [p for p in t.policies if p["name"] != name]
            continue

        m = RE_REVOKE.match(one_line)
        if m:
            t = model.table(bare_table_name(m.group(2)))
            if t:
                _apply_privileges(t, "revoke", m.group(1), m.group(3))
            continue

        m = RE_GRANT.match(one_line)
        if m:
            t = model.table(bare_table_name(m.group(2)))
            if t:
                _apply_privileges(t, "grant", m.group(1), m.group(3))
            continue

        m = RE_ALTER_TABLE.match(one_line)
        if m:
            t = model.table(bare_table_name(m.group(1)))
            if t:
                for action in split_top_level(m.group(2), ","):
                    _apply_alter_action(model, t, action.strip())
            continue

        m = RE_COMMENT_COL.match(one_line)
        if m:
            path = [unquote_ident(p) for p in split_top_level(m.group(1), ".")]
            if len(path) >= 2:
                t = model.table(path[-2])
                c = t.col(path[-1]) if t else None
                if c:
                    c.comment = m.group(2).replace("''", "'")
            continue

        m = RE_COMMENT_TABLE.match(one_line)
        if m:
            t = model.table(bare_table_name(m.group(1)))
            if t:
                t.comment = m.group(2).replace("''", "'")

    if not model.tables:
        raise SchemaError(
            "No CREATE TABLE statements found. If this really is DDL, check "
            "that statements are terminated with `;`. If it is a generated "
            "types file, pass --format ts.")

    # DDL is the one source that states row-level security. A table the file
    # never enables it on is, as far as this file shows, open (DL-A6).
    for t in model.tables:
        if t.rls is None:
            t.rls = False
    model.security = {"stated_by_source": True, "rls_statements": rls_statements}

    model.fidelity = {
        "source_format": "ddl",
        "carries": ["tables", "columns", "types", "lengths", "nullability",
                    "defaults", "generated", "checks", "primary keys",
                    "foreign keys", "unique indexes", "enums", "comments",
                    "row-level security", "policies", "column privileges"],
        "missing": ["row counts / cardinality",
                    "which column is the title", "display order",
                    "what users actually do with each field"],
    }
    return model


def _parse_create_table(stmt: str, model: Model) -> Table:
    head_end = stmt.index("(")
    m = RE_CREATE_TABLE.match(re.sub(r"\s+", " ", stmt))
    name = bare_table_name(m.group(1)) if m else "unknown"
    body_end = stmt.rindex(")")
    body = stmt[head_end + 1:body_end]
    table = Table(name=name)

    constraints = []
    for item in split_top_level(body, ","):
        item = re.sub(r"\s+", " ", item).strip()
        if not item:
            continue
        low = item.lower()
        if low.startswith("constraint "):
            item = re.sub(r"(?i)^constraint\s+[\w\"]+\s+", "", item)
            low = item.lower()
        if low.startswith("like "):                   # another table's columns: not read
            continue
        if low.startswith(("primary key", "foreign key", "unique", "check", "exclude", "not null ")):
            constraints.append(item)                  # a constraint may come before its column
            continue
        col = _parse_column_def(item, table, model)
        if col:
            table.columns.append(col)
    for item in constraints:
        _apply_constraint_to_table(model, table, item)

    return table


def _parse_column_def(item: str, table: Table, model: Model) -> Column | None:
    m = re.match(r'^("(?:[^"]+)"|[\w]+)\s+(.*)$', item)
    if not m:
        return None
    name = unquote_ident(m.group(1))
    rest = m.group(2).strip()

    # The type is everything up to the first modifier keyword at depth 0.
    modifier_start = len(rest)
    depth = 0
    for mm in re.finditer(
            r"(?i)\b(not\s+null|null|default|primary\s+key|unique|references|"
            r"check|generated|collate|constraint|deferrable)\b", rest):
        depth = (rest[:mm.start()].count("(") - rest[:mm.start()].count(")"))
        if depth == 0:
            modifier_start = mm.start()
            break
    raw_type = rest[:modifier_start].strip()
    mods = rest[modifier_start:].strip()

    ptype, length, precision, scale, is_array = normalise_type(raw_type)
    col = Column(name=name, type=ptype, raw_type=raw_type,
                 max_length=length, numeric_precision=precision,
                 numeric_scale=scale, is_array=is_array)

    col.enum = _enum_named(model, ptype)

    low = mods.lower()
    # A plain substring test over the whole modifier text also matches a
    # `NOT NULL` that only appears inside a CHECK (or other parenthesised)
    # expression — e.g. `CHECK (published_at IS NOT NULL OR status='draft')`
    # on an otherwise-nullable column. Only a top-level keyword, outside any
    # parentheses, actually makes the column NOT NULL.
    col.nullable = True
    for nn in re.finditer(r"(?i)\bnot\s+null\b", mods):
        if mods[:nn.start()].count("(") - mods[:nn.start()].count(")") == 0:
            col.nullable = False
            break
    if re.search(r"(?i)\b(serial|bigserial|smallserial)\b", raw_type):
        col.nullable = False
        col.default = "sequence"
        col.generated = True
    if re.search(r"(?i)generated\s+(always|by\s+default)\s+as\s+identity", low):
        col.generated = True
        col.nullable = False
    if re.search(r"(?i)generated\s+(always|by\s+default)\s+as\s+\(", low):
        col.generated = True
    if re.search(r"(?i)\bprimary\s+key\b", low):
        col.primary_key = True
        col.nullable = False
        table.primary_key.append(name)
    if re.search(r"(?i)\bunique\b", low):
        col.unique = True
        table.unique_indexes.append([name])

    dm = re.search(r"(?i)\bdefault\s+(.*?)(?=\s+(?:not\s+null|null|primary\s+key"
                   r"|unique|references|check|generated|collate|constraint)\b|$)",
                   mods)
    if dm:
        col.default = dm.group(1).strip()

    for cm in re.finditer(r"(?i)\bcheck\s*\(", mods):
        expr = _balanced_slice(mods, mods.index("(", cm.start()))
        if expr:
            col.checks.append(expr)

    rm = RE_INLINE_REFS.search(mods)
    if rm:
        ref_cols = [unquote_ident(c) for c in split_top_level(rm.group(2) or "id", ",")]
        col.foreign_key = {
            "table": bare_table_name(rm.group(1)),
            "column": ref_cols[0] if ref_cols else "id",
            "on_delete": _on_delete(rm.group(3) or ""),
        }
    return col


def _balanced_slice(text: str, open_idx: int) -> str:
    depth, i, n = 0, open_idx, len(text)
    while i < n:
        if text[i] == "(":
            depth += 1
        elif text[i] == ")":
            depth -= 1
            if depth == 0:
                return text[open_idx + 1:i].strip()
        i += 1
    return ""


def _on_delete(tail: str) -> str | None:
    m = _p(r"on\s+delete\s+(cascade|set\s+null|set\s+default|restrict|no\s+action)").search(tail)
    return re.sub(r"\s+", " ", m.group(1)).lower() if m else None


def _apply_constraint_to_table(model: Model, table: Table, clause: str) -> None:
    clause = clause.strip().rstrip(",")
    m = RE_PK_CLAUSE.match(clause.lower())
    if m:
        cols = [unquote_ident(c) for c in split_top_level(clause[m.start(1):m.end(1)], ",")]
        table.primary_key = cols
        for c in cols:
            cc = table.col(c)
            if cc:
                cc.primary_key = True
                cc.nullable = False
        return
    m = RE_UNIQUE_CLAUSE.match(clause.lower())
    if m:
        cols = [unquote_ident(c) for c in split_top_level(clause[m.start(1):m.end(1)], ",")]
        table.unique_indexes.append(cols)
        if len(cols) == 1 and table.col(cols[0]):
            table.col(cols[0]).unique = True
        return
    m = RE_FK_CLAUSE.search(clause)
    if m:
        local = [unquote_ident(c) for c in split_top_level(m.group(1), ",")]
        remote = [unquote_ident(c) for c in split_top_level(m.group(3) or "id", ",")]
        col = table.col(local[0]) if local else None
        if col:
            col.foreign_key = {
                "table": bare_table_name(m.group(2)),
                "column": remote[0] if remote else "id",
                "on_delete": _on_delete(m.group(4) or ""),
            }
        return
    m = RE_NOT_NULL_CLAUSE.match(clause)
    if m:
        col = table.col(unquote_ident(m.group(1)))
        if col:
            col.nullable = False
        return
    m = RE_CHECK_CLAUSE.match(clause)
    if m:
        expr = m.group(1).strip()
        target = _check_target(expr, table)
        if target:
            target.checks.append(expr)


# An expression as pieces: a dollar-quoted literal (tagged or not), a string
# literal, a quoted name, or a run of anything else. The closing quote is
# optional, so the pieces cover the text.
SQL_PIECES = re.compile(
    r"(?P<dollar>\$\$.*?(?:\$\$|\Z)|\$(?P<tag>[A-Za-z_]\w*)\$.*?(?:\$(?P=tag)\$|\Z))"
    r"|(?P<string>'(?:[^']|'')*'?)"
    r"|(?P<quoted>\"(?:[^\"]|\"\")*\"?)"
    r"|(?P<other>(?:[^'\"$]|\$(?!\$|[A-Za-z_]\w*\$))+)",
    re.S)


def _ident(name: str) -> str:
    """A column name as an expression writes it: bare when it can be."""
    if RE_SIMPLE_IDENT.fullmatch(name) and name not in KEEP_QUOTED:
        return name
    return '"' + name.replace('"', '""') + '"'


def _column_refs(expr: str, name: str):
    """Each piece of the expression, with whether it refers to the column, and
    the pattern of a bare reference inside it. A quoted name refers to the
    column when it is the whole name, so `"old.part"` is not `old`; a bare
    word only for a name that can be bare, and never when a call follows, so
    `lower(note)` is not a column `lower`."""
    bare = (re.compile(rf"(?<![\w$]){re.escape(name)}(?![\w$])(?!\s*\()")
            if _ident(name) == name else None)
    for m in SQL_PIECES.finditer(expr):
        piece = m.group(0)
        if m.group("dollar") or m.group("string"):
            yield piece, False, None
        elif m.group("quoted"):
            yield piece, piece[1:-1].replace('""', '"') == name, None
        else:
            yield piece, bool(bare and bare.search(piece)), bare


def _names(expr: str, name: str) -> bool:
    """Whether an expression refers to the column."""
    return any(refers for _, refers, _ in _column_refs(expr, name))


def _rename_in(expr: str, old: str, new: str) -> str:
    """The expression with its references to the column renamed, and every
    other piece as it was."""
    out = []
    for piece, refers, bare in _column_refs(expr, old):
        if not refers:
            out.append(piece)
        elif bare is None:
            out.append(_ident(new))
        else:
            out.append(bare.sub(lambda _: _ident(new), piece))
    return "".join(out)


def _drop_column(model: Model, table: Table, name: str) -> None:
    """What Postgres drops with a column: every index and constraint that
    uses it, the whole primary key included, and with CASCADE, which it needs
    for them, other tables' foreign keys into it (N17)."""
    table.columns = [c for c in table.columns if c.name != name]
    if name in table.primary_key:
        for c in table.columns:
            if c.name in table.primary_key:
                c.primary_key = False
        table.primary_key = []
    table.unique_indexes = [idx for idx in table.unique_indexes if name not in idx]
    for c in table.columns:
        c.checks = [expr for expr in c.checks if not _names(expr, name)]
    for t in model.tables:
        for c in t.columns:
            if c.foreign_key and (c.foreign_key["table"], c.foreign_key["column"]) == (table.name, name):
                c.foreign_key = None
    if table.update_columns is not None:
        table.update_columns = [c for c in table.update_columns if c != name]


def _rename_column(model: Model, table: Table, old: str, new: str) -> None:
    """Postgres keeps a column's keys, indexes, CHECKs and grants through a
    rename, and retargets other tables' foreign keys into it (N18)."""
    table.col(old).name = new
    table.primary_key = [new if n == old else n for n in table.primary_key]
    table.unique_indexes = [[new if n == old else n for n in idx] for idx in table.unique_indexes]
    for c in table.columns:
        c.checks = [_rename_in(expr, old, new) for expr in c.checks]
    for t in model.tables:
        for c in t.columns:
            if c.foreign_key and (c.foreign_key["table"], c.foreign_key["column"]) == (table.name, old):
                c.foreign_key["column"] = new
    if table.update_columns is not None:
        table.update_columns = [new if c == old else c for c in table.update_columns]


def _apply_alter_action(model: Model, table: Table, action: str) -> None:
    """One action of `ALTER TABLE`, replayed in order: migrations add and
    change columns after the CREATE, and a dump adds every key and identity
    that way."""
    m = RE_ADD_CONSTRAINT.match(action)
    if m:
        _apply_constraint_to_table(model, table, action[m.end():])
        return
    # A constraint this parser does not know is still never a column (N19).
    if re.match(r"(?i)(?:add|drop)\s+constraint\b", action):
        return
    m = RE_ADD_COLUMN.match(action)
    if m:
        col = _parse_column_def(m.group(1).strip(), table, model)
        if col and not table.col(col.name):
            table.columns.append(col)
        return
    m = RE_DROP_COLUMN.match(action)
    if m:
        _drop_column(model, table, unquote_ident(m.group(1)))
        return
    m = RE_RENAME.match(action)
    if m:
        old, new = (unquote_ident(g) if g else None for g in m.groups())
        if old is None:                               # the table itself
            for t in model.tables:
                for c in t.columns:
                    if c.foreign_key and c.foreign_key["table"] == table.name:
                        c.foreign_key["table"] = new
            table.name = new
        elif table.col(old):
            _rename_column(model, table, old, new)
        return
    m = RE_ALTER_COLUMN.match(action)
    col = table.col(unquote_ident(m.group(1))) if m else None
    if not col:
        return
    change = m.group(2).strip()
    if re.match(r"(?i)add\s+generated\s+(always|by\s+default)\s+as\s+identity\b", change):
        col.generated, col.nullable = True, False
    elif re.match(r"(?i)set\s+default\s+nextval\s*\(", change):
        col.generated, col.nullable, col.default = True, False, "sequence"
    elif re.match(r"(?i)set\s+default\s", change):
        col.default = change[len("set default"):].strip()
    elif re.match(r"(?i)drop\s+default\b", change):
        col.default = None
    elif re.match(r"(?i)(set|drop)\s+not\s+null\b", change):
        col.nullable = change.lower().startswith("drop")
    else:
        tm = re.match(r"(?i)(?:set\s+data\s+)?type\s+(.+?)(?:\s+(?:using|collate)\s.*)?$", change)
        if tm:
            raw = tm.group(1).strip()
            col.type, col.max_length, col.numeric_precision, col.numeric_scale, col.is_array = \
                normalise_type(raw)
            col.raw_type, col.enum = raw, _enum_named(model, col.type)


def _enum_named(model: Model, type_name: str) -> str | None:
    """The enum a normalised (lower-case, unqualified) type names, if any."""
    return next((name for name in model.enums if name.lower() == type_name), None)


def _check_target(expr: str, table: Table) -> Column | None:
    """Attach a CHECK to the one column it mentions. A multi-column check is
    a cross-field rule and belongs on the form, not on a field — we drop it
    rather than pin it to an arbitrary column and generate a wrong message."""
    mentioned = [c for c in table.columns
                 if re.search(rf"\b{re.escape(c.name)}\b", expr)]
    return mentioned[0] if len(mentioned) == 1 else None


# ---------------------------------------------------------------------------
# Parser 2 — `supabase gen types typescript`
# ---------------------------------------------------------------------------

def parse_gen_types(text: str, schema: str = "public") -> Model:
    model = Model()
    block = _ts_block(text, rf"\b{re.escape(schema)}\s*:\s*\{{")
    if block is None:
        block = _ts_block(text, r"\bpublic\s*:\s*\{")
    if block is None:
        raise SchemaError(
            f"Could not find a `{schema}: {{ … }}` block. `supabase gen types "
            f"typescript` nests everything under a schema key; pass --schema "
            f"with the one you want.")
    # Prettier wraps a union that does not fit on its line: the name ends the
    # line and each member starts one of its own with `|` (DL-A7).
    block = re.sub(r"\n[ \t]*\|", " |", block)
    block = re.sub(r":[ \t]*\|", ":", block)

    enums_block = _ts_block(block, r"\bEnums\s*:\s*\{")
    if enums_block:
        for m in re.finditer(r"(\w+)\s*:\s*([^\n]+)", enums_block):
            vals = re.findall(r'"([^"]*)"', m.group(2))
            if vals:
                model.enums[m.group(1)] = vals

    tables_block = _ts_block(block, r"\bTables\s*:\s*\{")
    if tables_block is None:
        raise SchemaError("No `Tables: { … }` block in the generated types file.")

    for tname, tbody in _ts_entries(tables_block):
        table = Table(name=tname)
        row = _ts_block(tbody, r"\bRow\s*:\s*\{")
        if row is None:
            continue
        for line in row.splitlines():
            line = line.strip().rstrip(",").rstrip(";")
            m = re.match(r'^"?([\w]+)"?\s*\??\s*:\s*(.+)$', line)
            if not m:
                continue
            cname, ctype = m.group(1), m.group(2).strip()
            nullable = "null" in [p.strip() for p in ctype.split("|")]
            base = " | ".join(p.strip() for p in ctype.split("|")
                              if p.strip() != "null").strip()
            is_array = base.endswith("[]")
            # Suffix removal, NOT rstrip: `rstrip("[]")` strips every trailing
            # bracket character, which quietly eats the closing `]` of
            # `Database["public"]["Enums"]["order_status"]` and turns a
            # perfectly detectable enum into an untyped string.
            base = (base[:-2] if is_array else base).strip()
            enum_name = None
            em = re.match(r'Database\[["\'](\w+)["\']\]\[["\']Enums["\']\]'
                          r'\[["\'](\w+)["\']\]', base)
            if em:
                enum_name = em.group(2)
            elif base in model.enums:
                enum_name = base
            elif '"' in base and "|" in base:
                # An inline union of string literals is an enum without a name.
                vals = re.findall(r'"([^"]*)"', base)
                if vals:
                    enum_name = f"{tname}_{cname}"
                    model.enums[enum_name] = vals

            ptype = _ts_to_pg(base, cname, enum_name)
            table.columns.append(Column(
                name=cname, type=ptype, raw_type=ctype, nullable=nullable,
                is_array=is_array, enum=enum_name))

        # Relationships carry the foreign keys, which is the one structural
        # fact this format keeps that a bare TypeScript type could not.
        rel = _ts_block(tbody, r"\bRelationships\s*:\s*\[")
        if rel:
            for entry in re.finditer(
                    r"\{(.*?)\}", rel, re.S):
                body = entry.group(1)
                cols = re.search(r'columns\s*:\s*\[(.*?)\]', body, re.S)
                ref_t = re.search(r'referencedRelation\s*:\s*"([^"]+)"', body)
                ref_c = re.search(r'referencedColumns\s*:\s*\[(.*?)\]', body, re.S)
                one = re.search(r'isOneToOne\s*:\s*(true|false)', body)
                if not (cols and ref_t):
                    continue
                local = re.findall(r'"([^"]+)"', cols.group(1))
                remote = re.findall(r'"([^"]+)"', ref_c.group(1)) if ref_c else ["id"]
                c = table.col(local[0]) if local else None
                if c:
                    c.foreign_key = {
                        "table": ref_t.group(1),
                        "column": remote[0] if remote else "id",
                        "on_delete": None,
                    }
                    if one and one.group(1) == "true":
                        c.unique = True
                        table.unique_indexes.append([c.name])

        # Insert tells us which columns have a default: they are optional
        # there. That is the only default information this format carries,
        # and it is enough to distinguish "the app supplies it" from
        # "the database supplies it".
        ins = _ts_block(tbody, r"\bInsert\s*:\s*\{")
        if ins:
            for line in ins.splitlines():
                m = re.match(r'^\s*"?([\w]+)"?\s*(\??)\s*:', line)
                if m and m.group(2) == "?":
                    c = table.col(m.group(1))
                    if c and not c.nullable:
                        c.default = "database-supplied"

        model.tables.append(table)

    if not model.tables:
        raise SchemaError("The `Tables` block parsed to zero tables.")

    for t in model.tables:
        pk = [c.name for c in t.columns if c.name == "id"]
        if pk:
            t.primary_key = pk
            t.col("id").primary_key = True
            t.col("id").generated = True
            t.col("id").nullable = False
        elif t.columns:
            # Composite keys on a join table show up as two non-null FKs.
            fks = [c.name for c in t.columns if c.foreign_key and not c.nullable]
            if len(fks) == 2:
                t.primary_key = fks
                for n in fks:
                    t.col(n).primary_key = True

    model.fidelity = {
        "source_format": "gen-types",
        "carries": ["tables", "columns", "nullability", "foreign keys",
                    "enums", "has-a-default (from the Insert type)"],
        "missing": ["exact Postgres types (uuid/text/citext all read as "
                    "`string`; date/timestamptz both read as `string`)",
                    "length constraints", "CHECK constraints",
                    "default expressions", "unique indexes beyond 1:1 FKs",
                    "column comments", "row counts / cardinality",
                    "RLS policies"],
        "consequence": "Name signals do proportionally more of the work here, "
                       "so more columns land at medium confidence and the "
                       "questions list is longer. If the DDL is available, "
                       "prefer it.",
    }
    return model


def _ts_to_pg(ts_type: str, col_name: str, enum_name: str | None) -> str:
    """TypeScript throws away the distinctions the mapper cares about most.
    Recover what the column NAME makes near-certain and be honest about the
    rest — a guess recorded as a fact is worse than a known unknown."""
    if enum_name:
        return "enum"
    t = ts_type.strip()
    if t == "number":
        return "numeric" if re.search(r"(price|amount|rate|total|cost|lat|lng|"
                                      r"weight|score)", col_name, re.I) \
            and not re.search(r"_cents$|_minor$", col_name, re.I) else "integer"
    if t == "boolean":
        return "boolean"
    if t == "Json" or t.startswith("Json"):
        return "jsonb"
    if t == "string":
        if re.search(r"^id$|_id$", col_name, re.I):
            return "uuid"
        if SYSTEM_TIMESTAMPS.match(col_name) or re.search(r"_at$", col_name, re.I):
            return "timestamp with time zone"
        if re.search(r"_date$|^date$|_on$", col_name, re.I):
            return "date"
        return "text"
    return "text"


def _ts_block(text: str, head_rx: str) -> str | None:
    """Return the balanced body that follows the first match of `head_rx`."""
    m = re.search(head_rx, text)
    if not m:
        return None
    opener = text[m.end() - 1]
    closer = {"{": "}", "[": "]"}[opener]
    depth, i, n = 0, m.end() - 1, len(text)
    start = i + 1
    while i < n:
        ch = text[i]
        if ch in "\"'":
            q = ch
            i += 1
            while i < n and text[i] != q:
                i += 2 if text[i] == "\\" else 1
        elif ch == opener:
            depth += 1
        elif ch == closer:
            depth -= 1
            if depth == 0:
                return text[start:i]
        i += 1
    return None


def _ts_entries(block: str) -> list[tuple[str, str]]:
    """Top-level `key: { … }` pairs inside an object body."""
    out: list[tuple[str, str]] = []
    i, n = 0, len(block)
    while i < n:
        m = re.compile(r'"?([\w]+)"?\s*:\s*\{').search(block, i)
        if not m:
            break
        depth, j = 0, m.end() - 1
        start = j + 1
        while j < n:
            ch = block[j]
            if ch in "\"'":
                q = ch
                j += 1
                while j < n and block[j] != q:
                    j += 2 if block[j] == "\\" else 1
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        out.append((m.group(1), block[start:j]))
        i = j + 1
    return out


# ---------------------------------------------------------------------------
# Parser 3 — JSON dumps
# ---------------------------------------------------------------------------

def parse_json_schema(text: str) -> Model:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise SchemaError(f"Not valid JSON: {exc}") from exc

    model = Model()
    if isinstance(data, list):
        data = {"tables": data}
    if not isinstance(data, dict):
        raise SchemaError("Expected a JSON object or a list of tables.")

    for name, values in (data.get("enums") or {}).items():
        model.enums[name] = list(values)

    tables_in = data.get("tables")
    if tables_in is None and "columns" in data:
        tables_in = _group_flat_columns(data)
    if not tables_in:
        raise SchemaError(
            'No tables found. Expected {"tables":[{"name":…,"columns":[…]}]} '
            'or a flat information_schema dump {"columns":[{"table_name":…}]}.')

    if isinstance(tables_in, dict):
        tables_in = [{"name": k, **v} for k, v in tables_in.items()]

    for t in tables_in:
        table = Table(name=t.get("name") or t.get("table_name") or "unknown",
                      comment=t.get("comment"))
        table.primary_key = list(t.get("primary_key") or t.get("primary_keys") or [])
        for u in (t.get("unique_indexes") or t.get("unique") or []):
            table.unique_indexes.append(list(u) if isinstance(u, (list, tuple)) else [u])

        for c in (t.get("columns") or []):
            raw = (c.get("data_type") or c.get("type") or c.get("udt_name")
                   or "text")
            ptype, length, precision, scale, is_array = normalise_type(str(raw))
            nullable = c.get("is_nullable", c.get("nullable", True))
            if isinstance(nullable, str):
                nullable = nullable.strip().upper() != "NO"
            col = Column(
                name=c.get("name") or c.get("column_name") or "unknown",
                type=ptype, raw_type=str(raw), nullable=bool(nullable),
                default=c.get("column_default", c.get("default")),
                comment=c.get("comment") or c.get("description"),
                max_length=c.get("character_maximum_length", length),
                numeric_precision=c.get("numeric_precision", precision),
                numeric_scale=c.get("numeric_scale", scale),
                is_array=bool(c.get("is_array", is_array)),
                enum=c.get("enum") or (ptype if ptype in model.enums else None),
                checks=list(c.get("checks") or []),
            )
            if col.enum:
                col.type = "enum"
            gen = c.get("is_generated") or c.get("generated")
            col.generated = bool(gen) and str(gen).upper() not in ("NEVER", "NO", "FALSE")
            if c.get("identity_generation"):
                col.generated = True
            table.columns.append(col)

        for fk in (t.get("foreign_keys") or []):
            col = table.col(fk.get("column") or fk.get("column_name") or "")
            if col:
                col.foreign_key = {
                    "table": bare_table_name(str(
                        fk.get("references_table") or fk.get("foreign_table_name")
                        or fk.get("table") or "")),
                    "column": fk.get("references_column")
                    or fk.get("foreign_column_name") or fk.get("to") or "id",
                    "on_delete": fk.get("on_delete"),
                }
        for ck in (t.get("checks") or []):
            col = table.col(ck.get("column", ""))
            if col:
                col.checks.append(ck.get("expression") or ck.get("check") or "")

        for name in table.primary_key:
            c = table.col(name)
            if c:
                c.primary_key = True
                c.nullable = False
        for idx in table.unique_indexes:
            if len(idx) == 1 and table.col(idx[0]):
                table.col(idx[0]).unique = True

        model.tables.append(table)

    model.fidelity = {
        "source_format": "json",
        "carries": ["whatever the dump query selected — check `missing` "
                    "against your own query before trusting an absence"],
        "missing": ["row counts / cardinality", "RLS policies",
                    "which column is the title", "display order"],
    }
    return model


def _group_flat_columns(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Turn `select * from information_schema.columns` into table groups."""
    groups: dict[str, dict[str, Any]] = {}
    for row in data.get("columns", []):
        tname = row.get("table_name") or row.get("table") or "unknown"
        groups.setdefault(tname, {"name": tname, "columns": []})
        groups[tname]["columns"].append(row)
    for row in data.get("constraints", []) + data.get("key_column_usage", []):
        tname = row.get("table_name")
        if tname not in groups:
            continue
        ctype = (row.get("constraint_type") or "").upper()
        if ctype == "PRIMARY KEY":
            groups[tname].setdefault("primary_key", []).append(row.get("column_name"))
        elif ctype == "UNIQUE":
            groups[tname].setdefault("unique_indexes", []).append([row.get("column_name")])
        elif ctype == "FOREIGN KEY":
            groups[tname].setdefault("foreign_keys", []).append(row)
    return list(groups.values())


# ---------------------------------------------------------------------------
# Structural inference — join tables and relationships
# ---------------------------------------------------------------------------

def _has_own_title(table: Table) -> bool:
    """Whether `table` has a textual, non-FK column that could stand as a
    human-readable title. Used to decide whether a cascade-deleted child is
    truly an owned, nameless detail of its parent, or an independent record
    that merely cannot outlive it."""
    return any(c.type in TEXTUAL_TYPES and not c.foreign_key for c in table.columns)


def infer_structure(model: Model) -> None:
    for t in model.tables:
        fks = [c for c in t.columns if c.foreign_key]
        others = [c for c in t.columns
                  if not c.foreign_key and not JOIN_TABLE_NOISE.match(c.name)]
        composite_pk_on_fks = (
            len(t.primary_key) == 2
            and set(t.primary_key) == {c.name for c in fks})
        if len(fks) == 2 and not others:
            t.kind = "join"
            t.screens["reason"] = (
                "two foreign keys and no column of its own"
                + (" plus a composite primary key on exactly those two columns"
                   if composite_pk_on_fks else "")
                + " — this is an edge, not an entity, so it gets no screens of "
                  "its own and shows up as a picker on both sides")

    for t in model.tables:
        for c in t.columns:
            if not c.foreign_key:
                continue
            parent = c.foreign_key["table"]
            control, conf, signal = _relationship_control(model, parent, c)
            t.relationships.append(Relationship(
                kind="many-to-one", to=parent, local_column=c.name,
                remote_column=c.foreign_key.get("column", "id"),
                on_delete=c.foreign_key.get("on_delete"),
                optional=c.nullable, control=control,
                confidence=conf, signal=signal))

            p = model.table(parent)
            if p is None or t.kind == "join":
                continue
            cascade = c.foreign_key.get("on_delete") == "cascade"
            if cascade:
                t.screens["owned_by"] = parent
            # Owned means BOTH cascade AND no title of its own — the same
            # test used below for screens.primary_home. A cascade-deleted
            # child that still has a name of its own (`full_name`, `email`,
            # ...) is not a nameless detail of the parent; it keeps its own
            # CRUD screens and is only linked from the parent's.
            owned = cascade and not _has_own_title(t)
            p.relationships.append(Relationship(
                kind="one-to-many", to=t.name, local_column=c.foreign_key.get("column", "id"),
                remote_column=c.name, on_delete=c.foreign_key.get("on_delete"),
                control="inline-subtable" if owned else "linked-list",
                confidence="medium" if owned else "low",
                signal=("ON DELETE CASCADE and no title of its own — the "
                        "children do not outlive the parent and are not "
                        "named things in their own right, so they belong "
                        "inside the parent's own form"
                        if owned else
                        "the children survive the parent's deletion, or have "
                        "a title of their own, so they are independent "
                        "records and get their own screens with a link "
                        "back")))

    # An owned child with no title of its own is a detail of its parent, not a
    # thing in the product's vocabulary. It still gets screens — somebody has
    # to fix a bad line item — but its primary home is the parent's form.
    for t in model.tables:
        if t.screens.get("owned_by") and not _has_own_title(t):
            t.screens["primary_home"] = "inline in " + t.screens["owned_by"]

    # Many-to-many: collapse each join table into one edge per side, and mark
    # the one-to-many edges that point AT the join table as plumbing.
    for j in [t for t in model.tables if t.kind == "join"]:
        fks = [c for c in j.columns if c.foreign_key]
        if len(fks) != 2:
            continue
        a_name, b_name = fks[0].foreign_key["table"], fks[1].foreign_key["table"]
        for side, other, own_col, other_col in (
                (a_name, b_name, fks[0].name, fks[1].name),
                (b_name, a_name, fks[1].name, fks[0].name)):
            parent = model.table(side)
            if parent is None:
                continue
            parent.relationships = [r for r in parent.relationships
                                    if not (r.kind == "one-to-many" and r.to == j.name)]
            control, conf, signal = _relationship_control(model, other, None)
            # A many-to-many control must be multi-valued. Falling through to
            # the single-valued form here is how a "tags" field silently
            # becomes a "tag" field and nobody notices until QA.
            multi = {"select": "multi-select", "combobox": "multi-combobox",
                     "record-picker": "record-picker"}[control]
            parent.relationships.append(Relationship(
                kind="many-to-many", to=other, via=j.name,
                local_column=own_col, remote_column=other_col,
                control=multi, confidence=conf,
                signal=f"{j.name} is a join table; {signal}"))


def _relationship_control(model: Model, parent_name: str,
                          col: Column | None) -> tuple[str, str, str]:
    """Pick the control for a reference by the only proxy the schema offers.

    The real input is the parent table's ROW COUNT, which no schema carries, so
    this is a defensible default plus a question — never a silent guess. See
    field-mapping.md §6 for the cardinality ladder this approximates.
    """
    parent = model.table(parent_name)
    if parent is None:
        return ("combobox", "low",
                f"`{parent_name}` is not in this schema — the control is a "
                f"guess until someone says how big it is")
    if LOOKUP_TABLE_NAMES.search(parent.name):
        return ("select", "medium",
                f"`{parent.name}` reads as a lookup table, which is almost "
                f"always under 20 rows — a select shows every option without "
                f"a round trip")
    meaningful = [c for c in parent.columns if not JOIN_TABLE_NOISE.match(c.name)]
    if len(meaningful) <= 3:
        return ("select", "low",
                f"`{parent.name}` has {len(meaningful)} columns of its own, "
                f"which usually means a small reference table — confirm the "
                f"row count")
    return ("combobox", "medium",
            f"`{parent.name}` looks like a real entity, so assume it grows "
            f"past what a select can hold; a combobox degrades gracefully "
            f"either way")


# ---------------------------------------------------------------------------
# The mapping layer — a column type does NOT determine a control
# ---------------------------------------------------------------------------

def map_columns(model: Model) -> None:
    for table in model.tables:
        title = _title_column(table)
        table.screens["title_column"] = title
        # A uuid is not a title. Saying so out loud matters: a generator that
        # quietly puts a primary key in an h1 produces screens that look
        # finished and are unusable.
        tcol = table.col(title) if title else None
        table.screens["title_is_placeholder"] = bool(
            tcol is None or tcol.primary_key or tcol.type == "uuid")
        table.screens["subtitle_column"] = _subtitle_column(table, title)
        for col in table.columns:
            col.ui = _guard_authority(col, _map_column(model, table, col, title))
        _assign_placement(table, title)
        table.screens["index_layout"], table.screens["index_layout_signal"] = \
            _index_layout(table)
        table.screens["default_sort"] = _default_sort(table)


# Columns that decide who may do what: ownership, tenancy, role, billing and
# verification. A user who can edit one can promote themselves — the standard
# Supabase profile policy (`USING (id = auth.uid())`, no WITH CHECK) lets
# `.update(draft)` write any column the draft carries. A TypeScript type is
# not access control, so these start read-only and get their own question.
AUTHORITY = _p(
    r"^(role|roles|user_role|permissions?|scopes?|admin|is_admin|is_staff|is_superuser"
    r"|is_owner|is_verified|is_approved|is_banned|is_suspended|verified|approved"
    r"|email_verified|owner_id|user_id|author_id|created_by|updated_by|org_id"
    r"|organization_id|tenant_id|workspace_id|team_id|account_id|plan|plan_id|tier"
    r"|credits|balance|quota|subscription_status|subscription_id|customer_id)$"
    r"|_role$|^stripe_|^billing_")


def _guard_authority(col: Column, ui: dict[str, Any]) -> dict[str, Any]:
    """Make authority-bearing columns read-only by default (see AUTHORITY).
    A primary key that is also a foreign key (profiles.id → auth.users) is the
    row's identity borrowed from another table: never a user's choice."""
    borrowed_identity = col.primary_key and bool(col.foreign_key)
    if not (borrowed_identity or AUTHORITY.search(col.name)) or ui.get("never_display"):
        return ui
    ui["editable"] = False
    ui["authority"] = True
    ui["signal"] = (ui.get("signal", "") + " · carries authority (ownership, tenant, "
                    "role, billing or identity) — read-only here by default. If users "
                    "may change it, protect it in the database first: a policy WITH "
                    "CHECK, a column grant, or a trigger").lstrip(" ·")
    return ui


def _map_column(model: Model, table: Table, col: Column,
                title: str | None) -> dict[str, Any]:
    ui: dict[str, Any] = {
        "control": "text-input",
        "label": humanise(col.name),
        "confidence": "low",
        "signal": "no signal beyond the type — this is a default, not a decision",
        "editable": True,
        "validation": [],
    }

    # --- 1. Not editable by anybody. These beat every other signal, because a
    #        beautiful control on a column the database owns is a lie.
    if col.generated or (col.primary_key and col.default):
        ui.update(control="hidden", editable=False, confidence="high",
                  signal="generated by the database — the user never supplies it")
        if col.primary_key:
            ui["signal"] = ("surrogate primary key with a database default — "
                            "it identifies the row, it is not a field")
        _validate(ui, col, table, model)
        return ui

    if col.type == "tsvector":
        ui.update(control="hidden", editable=False, confidence="high",
                  signal="a search index column — it powers the search box, "
                         "it is never shown or edited")
        return ui

    # --- 2. Foreign keys. The control is a function of the PARENT's size.
    if col.foreign_key:
        control, conf, signal = _relationship_control(
            model, col.foreign_key["table"], col)
        ui.update(control=control, confidence=conf, signal=signal,
                  label=humanise(re.sub(r"_id$", "", col.name)),
                  references={"table": col.foreign_key["table"],
                              "column": col.foreign_key["column"],
                              "label_column": None})
        _validate(ui, col, table, model)
        return ui

    # --- 3. Enum and CHECK-constrained sets: a closed set is a closed set
    #        however it was spelled.
    options = _closed_set(model, col)
    if options is not None:
        n = len(options)
        # A state word gets a select even at three options. A radio group is
        # right when the choice is the point of the screen and every option
        # must be visible; `status` is a field among twenty others, and three
        # stacked radios there cost more vertical space than they buy.
        state_word = bool(_p(r"(^|_)(status|state|stage|phase|visibility|"
                             r"role|type|kind|category)$").search(col.name))
        control = ("multi-select" if col.is_array else
                   "radio-group" if n <= 3 and not state_word else
                   "select" if n <= 20 else "combobox")
        ui.update(control=control, confidence="high",
                  signal=(f"a closed set of {n} values "
                          f"({'enum type' if col.enum else 'CHECK constraint'})"
                          + (" on a state column, which people change from a "
                             "list rather than survey" if state_word else "")
                          + f" — {control} is what that wants"),
                  options=options)
        _validate(ui, col, table, model)
        return ui

    # --- 4. Name signals. The whole reason this skill exists: `text` could be
    #        six different controls and the name is what picks.
    for pattern, control, conf, signal, extras in NAME_RULES:
        if not pattern.search(col.name):
            continue
        # A name signal that contradicts the type loses — `is_active text` is
        # bad schema, but rendering a switch over a free-text column is worse.
        if control in ("switch", "checkbox") and col.type != "boolean":
            continue
        if control in ("currency-input", "percent-input", "stepper") \
                and col.type not in NUMERIC_TYPES:
            continue
        if control == "geo-point" and col.type in TEXTUAL_TYPES:
            continue
        ui.update(control=control, confidence=conf, signal=signal, **extras)
        if control == "currency-input":
            ui["money"] = _money_policy(col, ui.get("money", {}))
            # "Price Cents" is a storage detail wearing a label. The user sees
            # a formatted amount; the minor-unit suffix is the developer's
            # business and belongs nowhere near the screen.
            ui["label"] = humanise(re.sub(
                r"_(cents|minor|minor_units|in_cents|pennies|cent)$", "",
                col.name, flags=re.I))
        if control == "select" and extras.get("closed_set_suspected"):
            ui["confidence"] = "low"
            ui["signal"] += (" — but nothing in the schema constrains it, so "
                             "the option list has to come from a human")
            ui["options"] = []
        _validate(ui, col, table, model)
        return ui

    # --- 5. Temporal. Split by TYPE, not by name, because this is the one
    #        place the type is authoritative and getting it wrong is a bug
    #        that only shows up for users in another zone.
    if col.type in TEMPORAL_TYPES:
        ui.update(**_temporal(col))
        _validate(ui, col, table, model)
        return ui

    # --- 6. Everything else: type plus whatever weak signal exists.
    ui.update(**_by_type(col, table, title))
    _validate(ui, col, table, model)
    return ui


def _by_type(col: Column, table: Table, title: str | None) -> dict[str, Any]:
    t, n = col.type, col.name
    if t == "boolean":
        return {"control": "checkbox", "confidence": "medium",
                "signal": "boolean with no is_/has_ prefix — a checkbox inside "
                          "a form rather than a switch that acts immediately"}
    if t == "uuid":
        return {"control": "readonly-text", "editable": False,
                "confidence": "medium",
                "signal": "a uuid nobody types by hand"}
    if t in ("jsonb", "json"):
        return {"control": "json-editor", "confidence": "low",
                "signal": "jsonb with no name signal — a JSON box is the honest "
                          "placeholder until somebody says what keys live in it"}
    if t in ("bytea",):
        return {"control": "file-upload", "confidence": "medium",
                "signal": "bytes in a column — move it to storage"}
    if t in ("geography", "geometry", "point"):
        return {"control": "geo-point", "confidence": "high",
                "signal": "a PostGIS type — a map picker, never two number boxes"}
    if t in INTEGER_TYPES:
        small = any(re.search(r"<=?\s*(\d+)", c) for c in col.checks)
        if col.is_array:
            return {"control": "multi-select", "confidence": "low",
                    "signal": "an integer array — almost always a set of ids "
                              "that should be a join table"}
        if re.search(r"(count|qty|quantity|stock|seats|units|copies)", n, re.I) or small:
            return {"control": "stepper", "confidence": "medium",
                    "signal": "a small bounded count — users nudge these, they "
                              "do not type them"}
        return {"control": "number-input", "confidence": "medium",
                "signal": "an integer with no other signal"}
    if t in NUMERIC_TYPES:
        if col.numeric_scale == 2:
            return {"control": "currency-input", "confidence": "low",
                    "signal": "numeric(p,2) — two decimal places is usually "
                              "money, but confirm it before formatting it as "
                              "money",
                    "money": {"storage": "decimal", "scale": 1}}
        return {"control": "number-input", "confidence": "medium",
                "signal": "a decimal quantity"}
    if col.is_array and t in TEXTUAL_TYPES:
        return {"control": "tag-input", "confidence": "medium",
                "signal": "a text array — an open-ended bag of short strings"}
    if t in TEXTUAL_TYPES:
        # The title is one line whatever its declared length. A 140-character
        # cap is a tweet-length limit, not an instruction to grow a textarea.
        if col.name == title:
            return {"control": "text-input", "confidence": "high",
                    "signal": "the record's title — one line, always, "
                              "regardless of how much room the column allows"}
        if col.max_length is not None:
            decl = col.raw_type or f"{t}({col.max_length})"
            # A bounded length is evidence of a SHORT field. The threshold is
            # high on purpose: authors who mean "a paragraph" write `text`,
            # and a varchar(255) is almost always a line someone was being
            # careful about. Only the name promotes a column to long-form,
            # and the name rules above already ran.
            if col.max_length <= 255:
                return {"control": "text-input", "confidence": "high",
                        "signal": f"`{decl}` — a bounded length is a single "
                                  f"line, and it hands the input its own "
                                  f"maxLength for free"}
            if col.max_length <= 2000:
                return {"control": "textarea", "confidence": "medium",
                        "signal": f"`{decl}` — past a line, short of a document"}
            return {"control": "rich-text", "confidence": "low",
                    "signal": f"`{decl}` — long enough that users will want "
                              f"formatting; confirm before taking on an editor "
                              f"dependency you cannot remove later"}
        if col.unique:
            return {"control": "text-input", "confidence": "medium",
                    "signal": "uniquely indexed, so it is an identifier a "
                              "person reads and types — one line"}
        return {"control": "text-input", "confidence": "low",
                "signal": "unbounded `text` with no name signal and no length "
                          "constraint — the single most ambiguous column shape "
                          "there is. Ask."}
    return {"control": "text-input", "confidence": "low",
            "signal": f"unrecognised type `{col.raw_type or col.type}`"}


def _temporal(col: Column) -> dict[str, Any]:
    system = bool(SYSTEM_TIMESTAMPS.match(col.name))
    if col.type == "date":
        return {"control": "date-picker", "confidence": "high",
                "editable": not system,
                "signal": "`date` — a calendar day with no time and no zone. "
                          "Rendering it as a datetime shifts it by a day for "
                          "half the planet.",
                "temporal": {"granularity": "date", "timezone": "none"}}
    if col.type in ("time with time zone", "time without time zone"):
        return {"control": "time-picker", "confidence": "high",
                "signal": "a wall-clock time",
                "temporal": {"granularity": "time",
                             "timezone": "offset" if "with" in col.type else "none"}}
    if col.type == "timestamp with time zone":
        if system:
            return {"control": "readonly-timestamp", "editable": False,
                    "confidence": "high",
                    "signal": "a system timestamp — the database writes it, so "
                              "it is displayed and never edited",
                    "temporal": {"granularity": "instant", "timezone": "viewer",
                                 "display": "relative, absolute on hover"}}
        return {"control": "datetime-picker", "confidence": "high",
                "signal": "`timestamptz` — an instant. It must be displayed "
                          "with an explicit zone or two users will read two "
                          "different times from one value.",
                "temporal": {"granularity": "instant", "timezone": "viewer"}}
    return {"control": "datetime-picker", "confidence": "low",
            "signal": "`timestamp` WITHOUT time zone — this column cannot "
                      "answer 'when' for anyone outside the server's zone. "
                      "Treat as a schema bug and ask.",
            "temporal": {"granularity": "instant", "timezone": "ambiguous",
                         "warning": "naive timestamp"}}


def _money_policy(col: Column, existing: dict[str, Any]) -> dict[str, Any]:
    policy = dict(existing)
    if re.search(r"_(cents|minor|minor_units|in_cents|pennies|cent)$", col.name, re.I):
        policy.update(storage="minor-units", scale=100,
                      note="integer minor units — divide by 100 for display, "
                           "multiply on save, and never let a float touch it")
    elif col.type in INTEGER_TYPES:
        policy.update(storage="minor-units-suspected", scale=100,
                      note="a money-named INTEGER column is minor units "
                           "roughly every time — confirm, because rendering "
                           "it raw shows the user a 100x price")
    elif col.numeric_scale is not None:
        policy.update(storage="decimal", scale=1,
                      note=f"numeric with scale {col.numeric_scale} — exact "
                           f"decimal, safe to display directly")
    else:
        policy.update(storage="unknown", scale=None,
                      note="storage unit unknown; do not format as money until "
                           "someone confirms it")
    policy.setdefault("currency", "unknown")
    return policy


def _closed_set(model: Model, col: Column) -> list[str] | None:
    if col.enum and col.enum in model.enums:
        return list(model.enums[col.enum])
    if col.enum:
        return []
    for expr in col.checks:
        m = re.search(rf"{re.escape(col.name)}\s*(?:=\s*any\s*\(\s*array\s*)?"
                      r"\[?\s*(?:in\s*)?\(?([^)\]]*)\)?\]?", expr, re.I)
        if m and "'" in m.group(1):
            vals = re.findall(r"'([^']*)'", m.group(1))
            if len(vals) >= 2:
                return vals
    return None


def _validate(ui: dict[str, Any], col: Column, table: Table, model: Model) -> None:
    """Every client rule MIRRORS a database constraint and names it.

    A client rule with no database constraint behind it is a second, divergent
    source of truth: the form rejects what the database would have accepted, or
    accepts what it will reject at 3am in a background job. Rules invented here
    are marked `mirror: false` so a reviewer can see the ones that need a
    matching constraint added.
    """
    rules: list[dict[str, Any]] = ui.setdefault("validation", [])

    def rule(kind: str, value: Any, source: str, mirror: bool = True,
             message: str | None = None) -> None:
        rules.append({"rule": kind, "value": value, "source": source,
                      "mirror": mirror,
                      "message": message or _default_message(kind, value, ui)})

    if not col.nullable and col.default is None and ui.get("editable", True):
        rule("required", True, "NOT NULL with no DEFAULT")
    if col.max_length is not None:
        rule("maxLength", col.max_length, f"{col.raw_type or col.type}")
    if col.unique or any(idx == [col.name] for idx in table.unique_indexes):
        rule("unique", True, "UNIQUE index",
             message=f"That {humanise(col.name).lower()} is already taken.")
        ui["unique_check"] = "server — debounce on blur, and handle the 23505 "\
                             "race on submit anyway"
    for expr in col.checks:
        for m in re.finditer(rf"{re.escape(col.name)}\s*(>=|<=|>|<)\s*"
                             r"([\-\d.]+)", expr):
            op, val = m.group(1), m.group(2)
            num = float(val) if "." in val else int(val)
            rule({"<=": "max", "<": "exclusiveMax",
                  ">=": "min", ">": "exclusiveMin"}[op], num,
                 f"CHECK ({expr})")
        bm = re.search(rf"(?<![\w.]){re.escape(col.name)}\s+between\s+(-?[\d.]+)\s+and\s+(-?[\d.]+)",
                       expr, re.I)
        if bm:
            for kind, val in (("min", bm.group(1)), ("max", bm.group(2))):
                rule(kind, float(val) if "." in val else int(val), f"CHECK ({expr})")
        lm = re.search(r"(?:char_)?length\s*\(\s*" + re.escape(col.name) +
                       r"\s*\)\s*(<=|<|>=|>)\s*(\d+)", expr, re.I)
        if lm:
            rule("maxLength" if lm.group(1).startswith("<") else "minLength",
                 int(lm.group(2)), f"CHECK ({expr})")
        rx = re.search(re.escape(col.name) + r"\s*~\*?\s*'([^']*)'", expr)
        if rx:
            rule("pattern", rx.group(1), f"CHECK ({expr})")
    if ui.get("format") == "email":
        rule("format", "email", "column name", mirror=False,
             message="Enter an email address, like name@example.com.")
    if ui.get("format") == "uri":
        rule("format", "uri", "column name", mirror=False,
             message="Enter a full address starting with https://")
    if ui.get("format") == "slug":
        rule("pattern", "^[a-z0-9]+(?:-[a-z0-9]+)*$", "column name",
             mirror=False,
             message="Lowercase letters, numbers and hyphens only.")
    if ui.get("control") == "currency-input":
        rule("min", 0, "money fields are non-negative unless the schema says "
                       "otherwise", mirror=False)
    if col.foreign_key:
        rule("exists", True, "FOREIGN KEY",
             message="Pick one from the list.")
        ui["exists_check"] = ("server only — a client cannot see rows RLS "
                              "hides from it, so a local 'does this id exist' "
                              "check will reject valid input")


def _default_message(kind: str, value: Any, ui: dict[str, Any]) -> str:
    label = ui.get("label", "This field")
    return {
        "required": f"{label} is required.",
        "maxLength": f"Keep {label.lower()} to {value} characters or fewer.",
        "minLength": f"{label} needs at least {value} characters.",
        "min": f"{label} cannot be less than {value}.",
        "max": f"{label} cannot be more than {value}.",
        "exclusiveMin": f"{label} must be greater than {value}.",
        "exclusiveMax": f"{label} must be less than {value}.",
    }.get(kind, f"{label} is not valid.")


# ---------------------------------------------------------------------------
# Screens: which column is the title, what goes on the list, how it lays out
# ---------------------------------------------------------------------------

def _title_column(table: Table) -> str | None:
    names = {c.name for c in table.columns}
    for cand in TITLE_CANDIDATES:
        if cand in names:
            col = table.col(cand)
            if col and col.type in TEXTUAL_TYPES | {"citext"}:
                return cand
    for c in table.columns:
        if c.type in TEXTUAL_TYPES and not c.nullable and c.unique:
            return c.name
    for c in table.columns:
        if c.type in TEXTUAL_TYPES and not c.nullable and not c.foreign_key:
            return c.name
    return table.primary_key[0] if table.primary_key else None


def _subtitle_column(table: Table, title: str | None) -> str | None:
    for c in table.columns:
        if c.name == title:
            continue
        if c.ui.get("control") in ("textarea", "rich-text"):
            return c.name
        if re.search(r"(description|summary|excerpt|subtitle|tagline)", c.name, re.I):
            return c.name
    return None


def _assign_placement(table: Table, title: str | None) -> None:
    """The list view is a scanning surface, not a dump of the row.

    Six columns is the working cap: past that a person stops scanning and
    starts reading, which is what the detail view is for. The ranking below is
    by what someone scanning a list is actually looking for.
    """
    def score(c: Column) -> int:
        if c.name == title:
            return 100
        ctrl = c.ui.get("control")
        if ctrl in ("image-upload",):
            return 90
        # A foreign key first, whatever control it landed on — "which customer"
        # is a question people scan a list to answer, and the control it uses
        # on the FORM has nothing to do with that.
        if c.foreign_key:
            return 75
        # A status is the second thing anyone looks at. A currency code or a
        # locale is a UNIT — it belongs beside its value, not in a column of
        # its own repeating "USD" four hundred times.
        if ctrl in ("select", "radio-group") and c.ui.get("options") \
                and not c.ui.get("options_source"):
            return 80
        if ctrl == "currency-input":
            return 70
        if ctrl in ("switch", "checkbox"):
            return 60
        # Dates rank by what they mean, not alphabetically. A NOT NULL
        # timestamp is when the record happened; a nullable one is an event
        # that may never have occurred; anything named for a migration is
        # plumbing that escaped into the schema.
        if c.type in TEMPORAL_TYPES or c.ui.get("temporal"):
            if _p(r"(legacy|import|sync|migrat|raw|backfill)").search(c.name):
                return 5
            if c.name in ("created_at", "updated_at"):
                return 40
            return 45 if not c.nullable else 35
        if ctrl in ("text-input", "email-input", "url-input", "tel-input",
                    "number-input", "stepper", "slug-input"):
            return 30
        return 0

    ranked = sorted(table.columns, key=lambda c: (-score(c), c.name))
    chosen: list[str] = []
    temporal_used = 0
    for c in ranked:
        if len(chosen) >= 6:
            break
        if score(c) == 0:
            continue
        if c.ui.get("never_display") or c.ui.get("control") == "hidden":
            continue
        # A foreign key IS a good list column — it renders as the parent's
        # label, not as the uuid. Only a bare `*_id` with nothing behind it is
        # noise, and that is a schema smell worth seeing.
        if LIST_NEVER.match(c.name) and not c.foreign_key:
            continue
        # Two dates is the most a scanning eye can use. Three is a log file.
        if (c.ui.get("temporal") or c.type in TEMPORAL_TYPES):
            if temporal_used >= 2:
                continue
            temporal_used += 1
        chosen.append(c.name)

    for c in table.columns:
        never = bool(c.ui.get("never_display"))
        hidden = c.ui.get("control") == "hidden"
        c.ui["placement"] = {
            "list": c.name in chosen,
            "detail": not never and not hidden,
            "form": bool(c.ui.get("editable", True)) and not hidden and not never,
        }


def _index_layout(table: Table) -> tuple[str, str]:
    """Table vs card grid vs feed. The decision rule is in
    screen-patterns.md §2; this is its mechanical half."""
    listed = [c for c in table.columns if c.ui.get("placement", {}).get("list")]
    has_image = any(c.ui.get("control") == "image-upload" for c in table.columns)
    # `description` accompanies a thing. `body` / `content` / `message` IS the
    # thing. Only the second kind makes a feed: a feed shows the text because
    # the text is the record, and a feed of descriptions is a table with its
    # columns knocked out.
    is_the_text = any(
        _p(r"^(body|content|message|post|text|comment|excerpt|transcript)$")
        .match(c.name) for c in table.columns)
    numeric = sum(1 for c in listed
                  if c.ui.get("control") in ("number-input", "stepper",
                                             "currency-input", "percent-input"))
    if has_image and len(listed) <= 5:
        return ("card-grid",
                "an image column plus few scannable fields — people recognise "
                "records here by looking, and a thumbnail in a table cell is a "
                "thumbnail nobody can see")
    if numeric >= 2 or len(listed) >= 5:
        return ("table",
                f"{len(listed)} scannable columns, {numeric} of them numeric — "
                f"values need to line up vertically to be comparable, which is "
                f"the one thing only a table does")
    if is_the_text and len(listed) <= 3:
        return ("feed",
                "few fields and a body column — the record IS its text, so "
                "show some of it rather than a row that says nothing")
    return ("table", "the default: a list of records with a handful of fields "
                     "scans fastest as rows, and a table is never the WRONG "
                     "answer, only sometimes the dull one")


def _default_sort(table: Table) -> dict[str, Any]:
    names = {c.name for c in table.columns}
    for cand, direction, why in (
            ("sort_order", "asc", "an explicit ordering column exists, so the "
                                  "product already has an opinion"),
            ("position", "asc", "an explicit ordering column exists"),
            ("created_at", "desc", "newest first is right until someone says "
                                   "otherwise, and it is stable under inserts"),
            ("updated_at", "desc", "most-recently-touched first")):
        if cand in names:
            return {"column": cand, "direction": direction, "signal": why,
                    "tiebreak": table.primary_key[0] if table.primary_key else None}
    return {"column": table.primary_key[0] if table.primary_key else None,
            "direction": "asc",
            "signal": "no temporal or ordering column — falling back to the "
                      "primary key, which is stable but meaningless to a user",
            "tiebreak": None}


# ---------------------------------------------------------------------------
# The interview — exactly what a schema cannot tell you
# ---------------------------------------------------------------------------

def build_questions(model: Model) -> None:
    q = model.questions

    def ask(qid: str, kind: str, question: str, default: Any, why: str,
            table: str | None = None, options: list[Any] | None = None,
            column: str | None = None) -> None:
        entry: dict[str, Any] = {
            "id": qid, "kind": kind, "question": question,
            "default": default, "why": why,
        }
        if table:
            entry["table"] = table
        if column:
            entry["column"] = column
        if options:
            entry["options"] = options
        q.append(entry)

    for t in model.tables:
        if t.kind == "join":
            continue
        text_cols = [c.name for c in t.columns
                     if c.type in TEXTUAL_TYPES and not c.ui.get("never_display")]
        placeholder = t.screens.get("title_is_placeholder")
        ask(f"{t.name}.title_column", "choice",
            f"Which column is a {singular(t.name)}'s title — the words a "
            f"person uses to refer to one out loud?"
            + (f"  NOTHING IN `{t.name}` LOOKS LIKE A TITLE, so the primary "
               f"key is standing in. If a {singular(t.name)} is really "
               f"identified by a combination of fields, say so here as a "
               f"template, e.g. \"{{product}} × {{quantity}}\"."
               if placeholder else ""),
            t.screens.get("title_column"),
            "Everything downstream hangs off this: the list's first column, "
            "the detail page's h1, the delete confirmation, the browser tab, "
            "every toast. A schema has no concept of 'the important one'.",
            table=t.name, options=text_cols or None)

        ask(f"{t.name}.default_sort", "choice",
            f"What order should {t.name} appear in by default?",
            f"{t.screens['default_sort']['column']} "
            f"{t.screens['default_sort']['direction']}",
            "A list with no designed order is a list whose top row changes "
            "every time anyone edits anything, and users read the top row "
            "first. " + t.screens["default_sort"]["signal"],
            table=t.name)

        ask(f"{t.name}.list_columns", "list",
            f"Which columns belong on the {t.name} list view?",
            [c.name for c in t.columns if c.ui.get("placement", {}).get("list")],
            "Proposed by ranking; the ranking does not know what this team "
            "looks for when scanning. Six is the working cap — past that "
            "people stop scanning and start reading.",
            table=t.name,
            options=[c.name for c in t.columns
                     if c.ui.get("placement", {}).get("detail")])

        ask(f"{t.name}.index_layout", "choice",
            f"Should {t.name} be a table, a card grid, or a feed?",
            t.screens["index_layout"],
            t.screens["index_layout_signal"] +
            " Override it if people will use this on a phone in the field, "
            "where a wide table is the wrong shape whatever the field count.",
            table=t.name, options=["table", "card-grid", "feed"])

        groups = _propose_groups(t)
        ask(f"{t.name}.field_groups", "groups",
            f"How should the {singular(t.name)} form be grouped into sections?",
            groups,
            "Grouping is the difference between a form and a questionnaire. "
            "The proposal below is by column ORDER and name, which correlates "
            "with meaning only by accident.",
            table=t.name)

        authority = [c.name for c in t.columns if c.ui.get("authority")]
        if authority:
            ask(f"{t.name}.authority_columns", "list",
                f"These {t.name} columns carry authority. Which must stay read-only "
                f"in this UI?",
                authority,
                "They decide ownership, tenancy, role or billing, so a user who can "
                "edit one can promote themselves. They start read-only. Remove a "
                "column from this list only after the database protects it — a "
                "policy WITH CHECK, a column-level grant, or a trigger — because the "
                "form's Draft type is not access control.",
                table=t.name, options=authority)

        readonly_guess = [c.name for c in t.columns
                          if not c.ui.get("editable", True)]
        ask(f"{t.name}.readonly_columns", "list",
            f"Which {t.name} columns are writable in the database but should "
            f"NOT be editable in this UI?",
            readonly_guess,
            "The database permits far more than the product should. An "
            "externally-synced field, a value only a background job should "
            "write, a column an admin may change and a user may not — none of "
            "that is expressible in DDL.",
            table=t.name,
            options=[c.name for c in t.columns
                     if c.ui.get("placement", {}).get("form")])

        ask(f"{t.name}.empty_state", "text",
            f"What should the {t.name} screen say when there are no records "
            f"at all, and what is the one action offered?",
            {"headline": f"No {humanise(t.name).lower()} yet",
             "body": "TODO: say what this screen will hold and why it is "
                     "worth filling in.",
             "action": f"Add {singular(humanise(t.name).lower())}"},
            "First-run empty is the screen most users see first and the one "
            "generators always default. 'No results' is not copy; it is the "
            "absence of copy.",
            table=t.name)

        for c in t.columns:
            ui = c.ui
            if ui.get("control") == "currency-input":
                ask(f"{t.name}.{c.name}.money", "money",
                    f"`{t.name}.{c.name}`: what currency, and is the stored "
                    f"value minor units (cents) or a decimal amount?",
                    {"currency": "USD",
                     "storage": ui.get("money", {}).get("storage", "unknown")},
                    "Get this wrong in either direction and every price on the "
                    "site is out by 100x. " + ui.get("money", {}).get("note", ""),
                    table=t.name, column=c.name,
                    options=["minor-units", "decimal"])
            if ui.get("control") in ("select", "combobox", "radio-group",
                                     "multi-select") and not ui.get("options") \
                    and not ui.get("options_source") and not c.foreign_key:
                ask(f"{t.name}.{c.name}.options", "list",
                    f"`{t.name}.{c.name}` reads as a closed set but nothing in "
                    f"the schema constrains it. What are the allowed values?",
                    [],
                    "If there is a real closed set, it belongs in the database "
                    "as an enum or a CHECK — otherwise the UI and the data "
                    "will disagree within a month. If there is not, this is a "
                    "text input.",
                    table=t.name, column=c.name)
            if ui.get("control") == "json-editor":
                ask(f"{t.name}.{c.name}.shape", "text",
                    f"`{t.name}.{c.name}` is jsonb. Which keys does it really "
                    f"hold, and do users edit them?",
                    {"keys": [], "user_editable": False},
                    "A JSON textarea in a product UI is an admission that "
                    "nobody knew what the column was for. Name the keys and it "
                    "becomes real fields; say it is machine-only and it "
                    "disappears from the form entirely.",
                    table=t.name, column=c.name)
            if ui.get("storage_backed"):
                ask(f"{t.name}.{c.name}.storage", "text",
                    f"`{t.name}.{c.name}`: which Supabase Storage bucket, and "
                    f"is it public or signed-URL only?",
                    {"bucket": t.name, "public": False,
                     "max_bytes": 5_000_000,
                     "accept": "image/png,image/jpeg,image/webp"
                     if ui.get("media") == "image" else "*/*"},
                    "A public bucket and a private one produce different "
                    "components: one renders a URL, the other has to mint a "
                    "signed URL with an expiry and handle it going stale "
                    "while the page is open.",
                    table=t.name, column=c.name)
            if (ui.get("temporal") or {}).get("granularity") == "instant" \
                    and ui.get("editable", True):
                ask(f"{t.name}.{c.name}.zone", "choice",
                    f"`{t.name}.{c.name}`: display in the viewer's timezone, or "
                    f"in a zone stored on the record?",
                    "viewer",
                    "A booking at 9am in Berlin is not a 9am event for the "
                    "person in Denver reading the list — but a 'shift starts "
                    "at 09:00' IS local to the site. Only you know which this "
                    "is, and the two render differently.",
                    table=t.name, column=c.name,
                    options=["viewer", "record", "fixed-utc"])
            if (ui.get("temporal") or {}).get("timezone") == "ambiguous":
                ask(f"{t.name}.{c.name}.naive_timestamp", "choice",
                    f"`{t.name}.{c.name}` is `timestamp` WITHOUT time zone. Is "
                    f"that deliberate?",
                    "migrate-to-timestamptz",
                    "A naive timestamp cannot answer 'when' for anyone outside "
                    "the server's zone. It is nearly always a mistake, and it "
                    "is much cheaper to fix in the schema than to paper over "
                    "in six components.",
                    table=t.name, column=c.name,
                    options=["migrate-to-timestamptz", "deliberate-wall-clock"])

        for r in t.relationships:
            if r.kind == "many-to-one":
                parent = model.table(r.to)
                guess = parent.screens.get("title_column") if parent else None
                ask(f"{t.name}.{r.local_column}.label_column", "choice",
                    f"When picking a {singular(r.to)} for a {singular(t.name)}, "
                    f"which {r.to} column is shown in the list?",
                    guess,
                    "A picker showing uuids is a picker nobody can use. This "
                    "is usually the parent's title column, but not always — an "
                    "invoice picker wants the number, not the customer name.",
                    table=t.name, column=r.local_column,
                    options=[c.name for c in parent.columns] if parent else None)
                ask(f"{t.name}.{r.local_column}.cardinality", "choice",
                    f"Roughly how many rows will `{r.to}` hold in production?",
                    _cardinality_default(r.control),
                    "This is the only input that decides between a select, a "
                    "combobox and a modal picker, and it is the one thing a "
                    "schema can never contain. Under ~20: select. Up to a few "
                    "thousand: combobox. Beyond: a picker with its own search "
                    "and paging.",
                    table=t.name, column=r.local_column,
                    options=["under-20", "under-5000", "unbounded"])

    if not model.tables:
        return
    # The DDL states it; any other source cannot, and the answer stays a guess.
    stated = [t for t in model.tables if t.rls is not None]
    off = [t.name for t in stated if not t.rls]
    ask("app.rls_enabled", "choice",
        "Is RLS on for every table listed here?",
        not off,
        ("The DDL says no: it is off on " + ", ".join(off) + ". " if off else
         "The DDL enables it on every table. " if stated else
         "This source cannot say, so check the database. ")
        + "Under RLS a row you cannot see and a row that does not exist are the "
        "same response, so 'empty' and 'forbidden' have to be told apart "
        "deliberately or the UI tells users their data is gone. The forbidden "
        "state is generated either way. Where the DDL states RLS for a table, "
        "that table's notes follow the DDL; this answer covers a source that "
        "cannot say. See supabase-integration.md §2.")
    ask("app.density", "choice",
        "Which density should the generated screens run at?",
        "compact",
        "Data-dense admin work is the one place --density: 0.875 is right by "
        "default; a marketing-weight 1.125 in a 40-row table wastes a screen "
        "of vertical space. Law 7 makes this one attribute, not a second set "
        "of styles.",
        options=["compact", "comfortable", "spacious"])


def _cardinality_default(control: str | None) -> str:
    return {"select": "under-20", "combobox": "under-5000",
            "record-picker": "unbounded"}.get(control or "", "under-5000")


def _propose_groups(table: Table) -> list[dict[str, Any]]:
    """Grouping by shape, which is a stand-in for grouping by meaning.

    Identity first (what the thing is called), then content, then the closed
    sets that classify it, then the relationships, then everything with a date
    on it, then the machinery. It is a defensible order and it is not the
    right one for any particular product.
    """
    buckets: dict[str, list[str]] = {
        "Identity": [], "Content": [], "Classification": [],
        "Relationships": [], "Scheduling": [], "Media": [], "Advanced": [],
    }
    title = table.screens.get("title_column")
    for c in table.columns:
        if not c.ui.get("placement", {}).get("form"):
            continue
        ctrl = c.ui.get("control")
        if c.name == title or ctrl in ("slug-input", "email-input", "tel-input",
                                       "url-input"):
            buckets["Identity"].append(c.name)
        elif ctrl in ("textarea", "rich-text"):
            buckets["Content"].append(c.name)
        elif ctrl in ("select", "radio-group", "multi-select", "switch",
                      "checkbox", "tag-input") and not c.foreign_key:
            buckets["Classification"].append(c.name)
        elif c.foreign_key or ctrl in ("combobox", "record-picker",
                                       "inline-subtable"):
            buckets["Relationships"].append(c.name)
        elif ctrl in ("date-picker", "datetime-picker", "time-picker",
                      "date-range"):
            buckets["Scheduling"].append(c.name)
        elif ctrl in ("image-upload", "file-upload"):
            buckets["Media"].append(c.name)
        else:
            buckets["Advanced"].append(c.name)
    return [{"legend": k, "fields": v} for k, v in buckets.items() if v]


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------

def humanise(name: str) -> str:
    s = re.sub(r"_id$", "", name)
    s = s.replace("_", " ").strip()
    words = s.split()
    acronyms = {"id", "url", "uri", "api", "sku", "utm", "ip", "seo", "css",
                "html", "pdf", "vat", "iso"}
    out = [w.upper() if w.lower() in acronyms else w.capitalize() for w in words]
    return " ".join(out) or name


def singular(name: str) -> str:
    n = name.rstrip()
    for suffix, repl in (("ies", "y"), ("ses", "s"), ("xes", "x"),
                         ("ches", "ch"), ("shes", "sh")):
        if n.endswith(suffix):
            return n[: -len(suffix)] + repl
    if n.endswith("s") and not n.endswith("ss"):
        return n[:-1]
    return n


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def model_to_dict(model: Model, source: dict[str, Any]) -> dict[str, Any]:
    d = {
        "$schema": MODEL_SCHEMA,
        "source": source,
        "fidelity": model.fidelity,
        "enums": model.enums,
        "security": model.security,
        "tables": [_table_dict(t) for t in model.tables],
        "questions": model.questions,
        "stats": {
            "tables": len([t for t in model.tables if t.kind == "entity"]),
            "join_tables": len([t for t in model.tables if t.kind == "join"]),
            "columns": sum(len(t.columns) for t in model.tables),
            "questions": len(model.questions),
            "confidence": _confidence_counts(model),
        },
    }
    return d


def _table_dict(t: Table) -> dict[str, Any]:
    d = asdict(t)
    d["relationships"] = [asdict(r) for r in t.relationships]
    return d


def _confidence_counts(model: Model) -> dict[str, int]:
    counts = {c: 0 for c in CONFIDENCE}
    for t in model.tables:
        for c in t.columns:
            lvl = c.ui.get("confidence")
            if lvl in counts:
                counts[lvl] += 1
    return counts


def summary(model: Model, doc: dict[str, Any]) -> str:
    out: list[str] = security_block(model)
    st = doc["stats"]
    out.append(f"source      {doc['source']['path']} "
               f"({doc['fidelity'].get('source_format')})")
    out.append(f"model       {st['tables']} entities · {st['join_tables']} join "
               f"table(s) · {st['columns']} columns · {len(model.enums)} enum(s)")
    conf = st["confidence"]
    out.append(f"confidence  {conf['high']} high · {conf['medium']} medium · "
               f"{conf['low']} low")
    out.append(f"questions   {st['questions']} for a human\n")

    for t in model.tables:
        tag = "JOIN" if t.kind == "join" else "    "
        title = t.screens.get("title_column")
        head = f"{tag} {t.name}"
        if t.kind == "entity":
            head += f"   title={title or '?'}  layout={t.screens.get('index_layout')}"
        out.append(head)
        if t.kind == "join":
            out.append(f"       {t.screens.get('reason', '')}")
            continue
        for c in t.columns:
            ui = c.ui
            flags = "".join([
                "L" if ui.get("placement", {}).get("list") else "·",
                "D" if ui.get("placement", {}).get("detail") else "·",
                "F" if ui.get("placement", {}).get("form") else "·",
            ])
            mark = {"high": "  ", "medium": " ?", "low": " !"}[ui.get("confidence", "low")]
            shown = f"{c.type}[]" if c.is_array else c.type
            out.append(f"     {flags}{mark} {c.name:<22} {shown:<26} "
                       f"-> {ui.get('control')}")
            out.append(f"            {ui.get('signal', '')}")
        for r in t.relationships:
            via = f" via {r.via}" if r.via else ""
            out.append(f"       rel  {r.kind:<13} -> {r.to}{via}  "
                       f"[{r.control}]")
        out.append("")
    out.append("L=list D=detail F=form   ? medium confidence   ! low, needs a human")
    return "\n".join(out)


def render_questions(model: Model) -> str:
    out: list[str] = [
        "# The interview",
        "",
        "Answer these into a JSON file as {\"<id>\": <value>} and pass it to",
        "`scaffold_ui.py --answers`. Every default is pre-filled and defensible;",
        "the ones that are wrong are wrong in ways only you can see.",
        "",
    ]
    by_table: dict[str, list[dict[str, Any]]] = {}
    for q in model.questions:
        by_table.setdefault(q.get("table", "(application)"), []).append(q)
    for table, qs in by_table.items():
        out.append(f"## {table}")
        out.append("")
        for q in qs:
            out.append(f"### {q['id']}")
            out.append(f"{q['question']}")
            if q.get("options"):
                out.append(f"  options: {', '.join(str(o) for o in q['options'])}")
            out.append(f"  default: {json.dumps(q['default'])}")
            out.append(f"  why:     {q['why']}")
            out.append("")
    return "\n".join(out)


def answers_template(model: Model) -> dict[str, Any]:
    return {q["id"]: q["default"] for q in model.questions}


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def detect_format(path: Path, text: str) -> str:
    ext = path.suffix.lower()
    if ext in (".sql", ".ddl", ".pgsql"):
        return "ddl"
    if ext in (".ts", ".tsx", ".d.ts"):
        return "ts"
    if ext == ".json":
        return "json"
    head = text.lstrip()[:400].lower()
    if head.startswith(("{", "[")):
        return "json"
    if "create table" in text.lower():
        return "ddl"
    if "Database" in text and "Tables:" in text:
        return "ts"
    raise SchemaError(
        f"Cannot tell what {path.name} is. Pass --format ddl|ts|json.")


def build_model(path: Path, text: str, fmt: str, schema: str) -> Model:
    if fmt == "ddl":
        model = parse_ddl(text)
    elif fmt == "ts":
        model = parse_gen_types(text, schema)
    elif fmt == "json":
        model = parse_json_schema(text)
    else:
        raise SchemaError(f"Unknown format `{fmt}`.")
    infer_structure(model)
    map_columns(model)
    security_pass(model)
    build_questions(model)
    return model


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="python -m scripts.introspect_schema",
        description="Normalise a Postgres/Supabase schema into model.json and "
                    "propose a control, label, validation and placement for "
                    "every column.",
        epilog="Confidence levels: high = the schema said so · medium = a "
               "strong signal with a plausible alternative · low = a default "
               "standing in for a decision nobody has made yet.",
    )
    ap.add_argument("schema", nargs="+",
                    help="a .sql DDL file, a `supabase gen types typescript` .ts "
                         "file, or a .json dump. Several .sql files are read as one, "
                         "in the order given (supabase/migrations/*.sql)")
    ap.add_argument("-o", "--out", metavar="FILE",
                    help="write model.json here (default: stdout as JSON, "
                         "unless --summary or --questions is given)")
    ap.add_argument("--format", choices=("auto", "ddl", "ts", "json"),
                    default="auto", help="override extension detection")
    ap.add_argument("--schema", dest="pg_schema", default="public",
                    metavar="NAME",
                    help="which schema to read from a generated types file "
                         "(default: public)")
    ap.add_argument("--summary", action="store_true",
                    help="print the human-readable proposal instead of JSON")
    ap.add_argument("--questions", action="store_true",
                    help="print only the interview, as markdown")
    ap.add_argument("--answers-template", metavar="FILE",
                    help="write a JSON file of every question pre-filled with "
                         "its default, ready to edit")
    ap.add_argument("--only", action="append", metavar="TABLE",
                    help="restrict the model to these tables (repeatable)")
    args = ap.parse_args(argv)

    # cmd.exe hands `supabase/migrations/*.sql` over as written, so expand a
    # pattern here; sorted, which is the order migrations are applied in.
    paths = []
    for given in args.schema:
        matched = sorted(glob.glob(given)) if any(ch in given for ch in "*?[") else []
        paths += [Path(p) for p in matched] or [Path(given)]
    path = paths[0]
    texts: list[str] = []
    for each in paths:
        if not each.exists():
            print(f"introspect_schema: no such file: {each}", file=sys.stderr)
            return 2
        try:
            raw = each.read_bytes()
            # A dump saved with `>` in PowerShell is UTF-16 or starts with a BOM.
            texts.append(raw.decode(json.detect_encoding(raw), errors="replace"))
        except OSError as exc:
            print(f"introspect_schema: cannot read {each}: {exc}", file=sys.stderr)
            return 2
    # Migrations build on each other, so several DDL files are one schema.
    if len(paths) > 1:
        other = [str(each) for each, body in zip(paths, texts)
                 if (args.format if args.format != "auto" else detect_format(each, body)) != "ddl"]
        if other:
            print(f"introspect_schema: several files are read together only when all are "
                  f"DDL; pass {', '.join(other)} alone.", file=sys.stderr)
            return 2
    # The `;` ends a last statement its file left open.
    text = "\n;\n".join(texts) if len(texts) > 1 else texts[0]

    try:
        fmt = args.format if args.format != "auto" else detect_format(path, text)
        model = build_model(path, text, fmt, args.pg_schema)
    except SchemaError as exc:
        print(f"introspect_schema: {exc}", file=sys.stderr)
        return 1

    if args.only:
        wanted = {n for spec in args.only for n in spec.split(",")}
        model.tables = [t for t in model.tables if t.name in wanted]
        model.questions = [q for q in model.questions
                           if q.get("table", "(application)") in wanted
                           or "table" not in q]
        security_pass(model)
        if not model.tables:
            print(f"introspect_schema: --only matched no tables.", file=sys.stderr)
            return 1

    doc = model_to_dict(model, {"path": ", ".join(str(each) for each in paths), "format": fmt,
                                "pg_schema": args.pg_schema})

    if args.answers_template:
        Path(args.answers_template).parent.mkdir(parents=True, exist_ok=True)   # a new folder too (P26)
        Path(args.answers_template).write_text(
            json.dumps(answers_template(model), indent=2) + "\n", encoding="utf-8")
        print(f"introspect_schema: wrote {len(model.questions)} pre-filled "
              f"answer(s) to {args.answers_template}.", file=sys.stderr)

    # --out is independent of what gets printed, so `--out model.json --summary`
    # writes the model AND shows you the proposal, which is the combination you
    # actually want the first time you run this on a schema.
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(doc, indent=2) + "\n",
                                  encoding="utf-8")
        st = doc["stats"]
        print(f"introspect_schema: wrote {args.out} — {st['tables']} entities, "
              f"{st['columns']} columns, {st['questions']} questions. "
              f"Review them before scaffolding.", file=sys.stderr)

    if args.questions:
        print(render_questions(model))
    elif args.summary:
        print(summary(model, doc))
    elif not args.out:
        print(json.dumps(doc, indent=2))
    return 0


if __name__ == "__main__":
    # A Windows pipe (git hook, CI, `> file`) defaults to the ANSI code page,
    # where printing →, Δ or ✓ raises UnicodeEncodeError. Consoles and
    # Claude Code already use UTF-8 and are left alone.
    for _stream in (sys.stdout, sys.stderr):
        if getattr(_stream, "encoding", "utf-8").lower() not in ("utf-8", "utf8"):
            _stream.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
