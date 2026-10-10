---
type: regex
target: {source: file, path: src/components/Button.tsx}
pattern: '(?<![\w-])(?!(?:data|aria|group|peer|has|not|in|supports|nth|nth-last)-\[)[a-z][\w-]*?-\[[^\]\s]+\]'
match: not_contains
arm: both
---
