---
description: 'XC-C1''s pricing section, built on the project''s tokens and left clean by the design audit.'
expected_outcome: 'The section''s stylesheet uses the project''s role tokens, sits in a cascade layer, and the audit passes it.'
tags: [outcome, build]
max_turns: 30
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill]
---

Our SaaS landing page needs a pricing section: three plans (Starter at $9 a month, Team at $29, Enterprise with "Contact sales"), the Team plan highlighted as the most popular, each with a short feature list and a call-to-action button. Write the markup to `src/components/pricing.html` and its styles to `src/components/pricing.css`. Our design tokens are in `styles/tokens.css` and `styles/index.css` is the entry stylesheet. If you have a design audit available, run it on the stylesheet and fix what it finds before you finish.
