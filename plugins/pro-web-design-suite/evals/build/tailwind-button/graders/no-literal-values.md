---
type: regex
target: {source: file, path: src/components/Button.tsx}
pattern: '(?<![-\w])(?:duration|delay|-?z|border(?:-[xytrblse])?|ring|ring-offset|outline|outline-offset|underline-offset)-\d+(?:\.\d+)?(?![\w./-])'
match: not_contains
arm: both
---
