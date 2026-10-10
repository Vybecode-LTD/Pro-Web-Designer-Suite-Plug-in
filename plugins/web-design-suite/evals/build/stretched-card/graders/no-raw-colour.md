---
type: regex
target: {source: file, path: src/components/card.css}
pattern: '#[0-9a-f]{3,8}\b|\b(?:rgba?|hsla?|hwb|lab|lch|oklab|oklch)\('
flags: i
match: not_contains
arm: both
---
