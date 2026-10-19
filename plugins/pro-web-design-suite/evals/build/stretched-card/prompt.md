---
description: 'SB-C6''s vanilla card whose title link stretches over the whole card.'
expected_outcome: 'One link, inside the heading, stretched over the card by a pseudo-element; the stylesheet keeps to the tokens and the audit passes it.'
tags: [outcome, build]
max_turns: 30
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill]
---

Build a blog post card for our index page: an image, the post's title as a link, a short excerpt and the date, where clicking anywhere on the card opens the post. Write `src/components/card.html` and `src/components/card.css`. Our design tokens are in `styles/tokens.css` and `styles/index.css` is the entry stylesheet. If you have a design audit available, run it on the stylesheet and fix what it finds before you finish.
