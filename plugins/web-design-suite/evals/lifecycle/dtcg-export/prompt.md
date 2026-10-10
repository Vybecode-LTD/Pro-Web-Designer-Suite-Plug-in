---
description: 'LC-C10''s DTCG export of the project''s tokens, in the 2025.10 format.'
expected_outcome: 'tokens.json holds $type and $value, colours as 2025.10 colour objects, and the roles as aliases to the palette.'
tags: [outcome, lifecycle]
max_turns: 30
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill]
---

Our Figma plugin imports design tokens in the Design Tokens Community Group format. Export the tokens in `styles/tokens.css` to `tokens.json` in that format, so the designers get the same palette and the same semantic colours.
