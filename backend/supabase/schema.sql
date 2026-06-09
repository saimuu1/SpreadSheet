-- Spreadsheet-to-API schema.
-- Run this in the Supabase SQL editor (SQL Editor → New query → paste → Run).
-- Then run rls.sql.

-- Needed for gen_random_uuid()
create extension if not exists pgcrypto;

-- ---------------------------------------------------------------------------
-- profiles: extends Supabase auth.users with app fields. plan drives tier gating.
-- ---------------------------------------------------------------------------
create table if not exists public.profiles (
    id          uuid primary key references auth.users (id) on delete cascade,
    email       text,
    plan        text not null default 'free' check (plan in ('free', 'pro')),
    created_at  timestamptz not null default now()
);

-- Auto-create a profile row whenever a new auth user signs up.
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
    insert into public.profiles (id, email)
    values (new.id, new.email)
    on conflict (id) do nothing;
    return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
    after insert on auth.users
    for each row execute function public.handle_new_user();

-- ---------------------------------------------------------------------------
-- datasets: one row per uploaded spreadsheet. id appears in the public API URL.
-- ---------------------------------------------------------------------------
create table if not exists public.datasets (
    id          uuid primary key default gen_random_uuid(),
    owner_id    uuid not null references public.profiles (id) on delete cascade,
    name        text not null,
    row_count   int not null default 0,
    created_at  timestamptz not null default now()
);
create index if not exists datasets_owner_idx on public.datasets (owner_id);

-- ---------------------------------------------------------------------------
-- columns: the inferred schema (the "menu"). One row per spreadsheet column.
-- ---------------------------------------------------------------------------
create table if not exists public.columns (
    id          uuid primary key default gen_random_uuid(),
    dataset_id  uuid not null references public.datasets (id) on delete cascade,
    name        text not null,
    data_type   text not null check (data_type in ('text', 'number', 'boolean', 'date')),
    position    int not null
);
create index if not exists columns_dataset_idx on public.columns (dataset_id);

-- ---------------------------------------------------------------------------
-- rows: the actual data, one JSON object per spreadsheet row (jsonb).
-- ---------------------------------------------------------------------------
create table if not exists public.rows (
    id          uuid primary key default gen_random_uuid(),
    dataset_id  uuid not null references public.datasets (id) on delete cascade,
    data        jsonb not null
);
create index if not exists rows_dataset_idx on public.rows (dataset_id);
-- GIN index supports filtering inside the jsonb document.
create index if not exists rows_data_gin on public.rows using gin (data);

-- ---------------------------------------------------------------------------
-- api_keys: the Consumer's credential. Store only a hash, never the raw key.
-- ---------------------------------------------------------------------------
create table if not exists public.api_keys (
    id            uuid primary key default gen_random_uuid(),
    owner_id      uuid not null references public.profiles (id) on delete cascade,
    key_hash      text not null unique,
    key_prefix    text not null,
    created_at    timestamptz not null default now(),
    last_used_at  timestamptz
);
create index if not exists api_keys_owner_idx on public.api_keys (owner_id);
create index if not exists api_keys_hash_idx on public.api_keys (key_hash);

-- ---------------------------------------------------------------------------
-- request_logs: one row per public API request, for rate limiting + analytics.
-- ---------------------------------------------------------------------------
create table if not exists public.request_logs (
    id           uuid primary key default gen_random_uuid(),
    api_key_id   uuid not null references public.api_keys (id) on delete cascade,
    created_at   timestamptz not null default now()
);
-- Composite index makes "count this key's requests since T" fast.
create index if not exists request_logs_key_time_idx
    on public.request_logs (api_key_id, created_at);
