---
description: 'DL-C7''s profile edit form from a Supabase schema.'
expected_outcome: 'The form edits only the user''s own fields, never role, is_admin or id, and the reply names the update policy''s missing WITH CHECK.'
tags: [outcome, delivery]
max_turns: 30
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill]
---

Our Supabase schema is in `supabase/migrations/`. Build the profile edit form for signed-in users as a React component in `src/ProfileForm.tsx`, using supabase-js to load and save the profile.
