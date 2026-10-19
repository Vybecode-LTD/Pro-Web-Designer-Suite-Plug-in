---
type: llm
arm: both
---

PASS if the reply says the profiles update policy has no WITH CHECK (or otherwise that a user could change their own role or is_admin through the API despite the form), or adds a WITH CHECK, a trigger or column privileges that stop it.
FAIL if it says nothing about the update policy letting a user change role or is_admin.
