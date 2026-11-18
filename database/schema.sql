-- MOTIONFORGE optional Supabase schema.
-- Apply only when Phase 6 begins. Local Room storage is the MVP baseline.
-- Enable RLS on every user-owned table.

create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  display_name text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.sessions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  programme_id text,
  session_type text not null check (session_type in ('fitness', 'fighting_fundamentals')),
  started_at timestamptz not null,
  completed_at timestamptz,
  duration_seconds integer not null default 0 check (duration_seconds >= 0),
  perceived_effort smallint check (perceived_effort between 1 and 10),
  created_at timestamptz not null default now()
);

create table if not exists public.session_exercises (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references public.sessions(id) on delete cascade,
  exercise_id text not null,
  sequence_number integer not null,
  duration_seconds integer not null default 0 check (duration_seconds >= 0),
  repetition_count integer check (repetition_count is null or repetition_count >= 0),
  tracking_quality text check (tracking_quality in ('good', 'partial', 'unavailable', 'not_used')),
  created_at timestamptz not null default now()
);

create table if not exists public.user_programmes (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  programme_id text not null,
  started_at timestamptz not null default now(),
  completed_at timestamptz,
  unique(user_id, programme_id)
);

alter table public.profiles enable row level security;
alter table public.sessions enable row level security;
alter table public.session_exercises enable row level security;
alter table public.user_programmes enable row level security;

create policy "Users can read own profile"
on public.profiles for select
using (auth.uid() = id);

create policy "Users can insert own profile"
on public.profiles for insert
with check (auth.uid() = id);

create policy "Users can update own profile"
on public.profiles for update
using (auth.uid() = id)
with check (auth.uid() = id);

create policy "Users can manage own sessions"
on public.sessions for all
using (auth.uid() = user_id)
with check (auth.uid() = user_id);

create policy "Users can manage exercises in own sessions"
on public.session_exercises for all
using (
  exists (
    select 1 from public.sessions s
    where s.id = session_id and s.user_id = auth.uid()
  )
)
with check (
  exists (
    select 1 from public.sessions s
    where s.id = session_id and s.user_id = auth.uid()
  )
);

create policy "Users can manage own programmes"
on public.user_programmes for all
using (auth.uid() = user_id)
with check (auth.uid() = user_id);
