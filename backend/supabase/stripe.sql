-- Stripe billing columns on profiles.
-- Run this in the Supabase SQL editor after schema.sql (safe to run anytime; idempotent).

alter table public.profiles
    add column if not exists stripe_customer_id     text,
    add column if not exists stripe_subscription_id text;

-- Look up a profile by its Stripe customer quickly (used by webhook fallbacks).
create index if not exists profiles_stripe_customer_idx
    on public.profiles (stripe_customer_id);
