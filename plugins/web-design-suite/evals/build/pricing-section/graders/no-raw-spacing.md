---
type: regex
target: {source: file, path: src/components/pricing.css}
pattern: '(?:^|[\s;{])(?:padding|margin|gap|row-gap|column-gap)[\w-]*\s*:[^;{}]*\d(?:px|rem|em)\b'
flags: im
match: not_contains
arm: both
---
