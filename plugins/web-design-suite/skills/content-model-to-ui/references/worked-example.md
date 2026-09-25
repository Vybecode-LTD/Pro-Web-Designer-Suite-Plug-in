# Worked example

One schema taken from introspection to generated screens.

## 1. Worked example

The fixture this skill is verified against: seven tables, a join table, two enums, integer cents, a nullable foreign key, a jsonb bag, a slug behind a unique index, a storage-backed image, and one naive `timestamp`. What `--summary` says about `products`:

```
     products   title=title  layout=table
     LDF   title             character varying  -> text-input
            the record's title — one line, always, regardless of how much room the column allows
     ·DF   slug              text               -> slug-input
            name says slug — derived from the title, uniquely indexed, and the thing a URL
            breaks on if it changes
     LDF   price_cents       integer            -> currency-input
            name declares minor units — the integer is NOT a quantity
     ·DF ? currency          character          -> select
            a currency code is a closed set of about 180 values that nobody types by hand
     LDF   status            product_status     -> select
            a closed set of 3 values (enum type) on a state column, which people change from
            a list rather than survey
     LDF ? category_id       uuid               -> select
            `categories` reads as a lookup table, which is almost always under 20 rows
     LDF   cover_image_url   text               -> image-upload
            name says image — a storage object, not a string the user types
     ·DF ? metadata          jsonb              -> json-editor
            name is a bag — needs a human to say which keys are real
     LDF   is_featured       boolean            -> switch
            is_/has_ prefix — a boolean the user flips, not a form checkbox
     ·DF   available_on      date               -> date-picker
            `date` — a calendar day with no time and no zone. Rendering it as a datetime
            shifts it by a day for half the planet.
     LD·   created_at        timestamptz        -> readonly-timestamp
            a system timestamp — the database writes it, so it is displayed and never edited
       rel  many-to-one   -> categories            [select]
       rel  many-to-many  -> tags via product_tags [multi-select]

L=list D=detail F=form   ? medium confidence   ! low, needs a human
```

Read what that is doing. `cover_image_url` became an upload rather than a URL text box, which only happens because the image rule is evaluated *before* the URL rule — both patterns match. `price_cents` became money with a "Price" label rather than an integer spinner reading "Price Cents". `available_on` stayed a calendar day. `created_at` left the form entirely. `product_tags` produced no screens at all, because two foreign keys and an ordering column is an edge, not an entity — while `order_items`, which has the same two-foreign-key shape *plus* `quantity` and `unit_price_cents`, stayed an entity, because those two columns are what make a line item a line item.

And the two `?` marks are the point: the mapper is telling you it guessed at the currency list and at how many categories there will be, and both of those are now questions with defaults sitting in `answers.json`.
