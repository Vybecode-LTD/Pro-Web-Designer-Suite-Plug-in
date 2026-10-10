---
description: 'SB-C6''s Tailwind button with a loading state, on the project''s theme.'
expected_outcome: 'The button keeps a visible focus outline, announces its busy state, and uses the theme''s classes, not arbitrary or literal values.'
tags: [outcome, build]
max_turns: 30
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill]
---

Write a reusable Button component for our React app in `src/components/Button.tsx`, styled with Tailwind on our theme (`src/styles/app.css`). It needs primary and secondary variants and a loading state that shows a spinner and stops double submits. If you have a design audit available, run it on the component and fix what it finds before you finish.
