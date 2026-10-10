---
description: 'SB-C6''s vendor stylesheet, loaded into the low vendor layer so the project''s styles win.'
expected_outcome: 'The entry stylesheet imports the vendor file with layer(vendor) after the layer statement, and the vendor file is left alone.'
tags: [outcome, build]
max_turns: 30
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill]
---

We're adding a third-party datepicker to the booking form. Its stylesheet is `vendor/datepicker.css`, and we never edit vendor files. Load it through our entry stylesheet, `styles/index.css`, so the datepicker works but our own component styles still win wherever they overlap with it.
