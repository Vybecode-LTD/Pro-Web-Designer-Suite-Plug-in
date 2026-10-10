---
type: regex
target: {source: file, path: src/components/card.css}
pattern: 'var\(\s*--(?:neutral|blue|space)-\d+\s*\)'
match: not_contains
arm: both
---
