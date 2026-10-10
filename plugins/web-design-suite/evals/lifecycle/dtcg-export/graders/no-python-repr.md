---
type: regex
target: {source: file, path: tokens.json}
pattern: '\{'''
match: not_contains
arm: both
---
