---
type: llm
arm: both
---

PASS if the reply says the change should not ship as a patch and treats it as a breaking (major) change, or at minimum says it is not patch-safe because every consumer's rendered colour, and its contrast, changes even though no name changed.
FAIL if it says a patch release is fine because nothing was renamed or removed.
