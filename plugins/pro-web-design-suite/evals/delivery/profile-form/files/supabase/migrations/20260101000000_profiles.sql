create table public.profiles (
  id uuid primary key references auth.users (id) on delete cascade,
  email text not null,
  display_name text not null check (char_length(display_name) between 1 and 80),
  bio text check (char_length(bio) <= 500),
  avatar_url text,
  role text not null default 'member' check (role in ('member', 'editor', 'admin')),
  is_admin boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.profiles enable row level security;

create policy "owners read their profile" on public.profiles
  for select using (auth.uid() = id);

create policy "owners update their profile" on public.profiles
  for update using (auth.uid() = id);
