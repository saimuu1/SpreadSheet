-- Row Level Security policies.
-- Run this AFTER schema.sql, in the Supabase SQL editor.
--
-- These guard the Builder/dashboard path: the backend talks to Postgres using the
-- caller's Supabase access token, so auth.uid() resolves to the logged-in user and the
-- database itself refuses to return another user's rows.
--
-- The public Consumer API uses the service-role key, which BYPASSES RLS by design — that
-- path authenticates via hashed API keys and authorizes ownership in application code.

alter table public.profiles      enable row level security;
alter table public.datasets      enable row level security;
alter table public.columns       enable row level security;
alter table public.rows          enable row level security;
alter table public.api_keys      enable row level security;
alter table public.request_logs  enable row level security;

-- ----- profiles -----------------------------------------------------------------
drop policy if exists "profiles self read" on public.profiles;
create policy "profiles self read" on public.profiles
    for select using (id = auth.uid());

drop policy if exists "profiles self update" on public.profiles;
create policy "profiles self update" on public.profiles
    for update using (id = auth.uid()) with check (id = auth.uid());

-- ----- datasets -----------------------------------------------------------------
drop policy if exists "datasets owner all" on public.datasets;
create policy "datasets owner all" on public.datasets
    for all using (owner_id = auth.uid()) with check (owner_id = auth.uid());

-- ----- columns (ownership via parent dataset) -----------------------------------
drop policy if exists "columns owner all" on public.columns;
create policy "columns owner all" on public.columns
    for all
    using (
        dataset_id in (select id from public.datasets where owner_id = auth.uid())
    )
    with check (
        dataset_id in (select id from public.datasets where owner_id = auth.uid())
    );

-- ----- rows (ownership via parent dataset) --------------------------------------
drop policy if exists "rows owner all" on public.rows;
create policy "rows owner all" on public.rows
    for all
    using (
        dataset_id in (select id from public.datasets where owner_id = auth.uid())
    )
    with check (
        dataset_id in (select id from public.datasets where owner_id = auth.uid())
    );

-- ----- api_keys -----------------------------------------------------------------
drop policy if exists "api_keys owner all" on public.api_keys;
create policy "api_keys owner all" on public.api_keys
    for all using (owner_id = auth.uid()) with check (owner_id = auth.uid());

-- ----- request_logs (read-only for the owner, via their keys) --------------------
drop policy if exists "request_logs owner read" on public.request_logs;
create policy "request_logs owner read" on public.request_logs
    for select using (
        api_key_id in (select id from public.api_keys where owner_id = auth.uid())
    );
