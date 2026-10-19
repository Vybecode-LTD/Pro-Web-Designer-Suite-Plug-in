---
description: 'DL-C7''s receipt email for Outlook and dark mode.'
expected_outcome: 'The email has Outlook conditional code, a dark-mode scheme, and presentation tables.'
tags: [outcome, delivery]
max_turns: 30
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill]
---

Write the HTML for our order receipt email: the order number, the items with their prices, the total and a "View your order" button. It has to work in Outlook on Windows and look right in dark mode. Save it as `emails/receipt.html`.
