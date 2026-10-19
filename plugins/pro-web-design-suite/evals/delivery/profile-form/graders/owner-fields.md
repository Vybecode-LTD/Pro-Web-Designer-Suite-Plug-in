---
type: llm
focus: {source: file, path: src/ProfileForm.tsx}
arm: both
---

PASS if the form offers inputs only for fields a user may edit about themselves (such as display_name, bio and avatar_url), and its update sends none of role, is_admin, id or created_at.
FAIL if it renders an input for role, is_admin, id or created_at, or includes any of them in the update payload.
