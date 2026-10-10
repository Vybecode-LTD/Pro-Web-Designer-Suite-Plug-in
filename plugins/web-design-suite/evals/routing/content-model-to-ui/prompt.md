---
description: A request content-model-to-ui handles, phrased as a user would.
expected_outcome: Claude loads web-design-suite:content-model-to-ui.
tags: [routing]
max_turns: 10
allowed_tools: [Skill]
---

I have a Supabase table `projects` (id uuid, name text, status enum draft/active/archived, owner_id uuid references auth.users, due_date date). I need its list page, detail page and create/edit form in React. Can you spec and scaffold those screens?
