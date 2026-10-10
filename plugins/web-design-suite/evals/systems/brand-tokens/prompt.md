---
description: 'SS-C7''s #e8440a brand: a palette and two themes of roles, the brand kept exactly.'
expected_outcome: 'The token file keeps the brand colour exactly, aliases its roles to the palette, has a dark theme, and its role pairs pass the contrast check.'
tags: [outcome, systems]
max_turns: 30
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill]
---

We're starting a new web app and our brand colour is #e8440a. Set up our colour tokens in `styles/tokens.css`: a palette built from the brand colour, and the semantic colours our components will use (text, surfaces, borders, the accent, and success, warning and danger), for a light and a dark theme. If you have a contrast check available, run it on the file and fix what fails.
