# Sheetwave — Spreadsheet → API

Upload a spreadsheet, get a live, queryable REST API in seconds. A full-stack portfolio
project: a **FastAPI + Supabase** backend and a **React + Vite + Tailwind** frontend.

## What this serves as

A complete, deployable SaaS base kept **in reserve**. It already has the hard parts of a
metered API product built and tested — multi-tenant auth, hashed API keys, a real query
language, and **plan-tiered rate limiting**. Payments are intentionally stubbed: upgrading
just flips a `plan` flag, and the entitlement logic reads that flag live.

The intent: if a company or client ever needs a **Stripe-billed / usage-metered API SaaS**,
this is the project to pull off the shelf. Wiring in real billing is a small, isolated
change — swap the "flip the flag" trigger from a button to a **Stripe Checkout + webhook**;
everything else (limits, tiers, enforcement) already works.

```
SpreadSheet/
├── backend/    # FastAPI service — auth, upload + schema inference, API keys,
│               # the URL query language, rate limiting & tiers (see backend/README.md)
└── frontend/   # React dashboard — landing page, auth, upload, API keys, per-dataset docs
```

## What it does

- **Builders** use the website: sign up, upload a CSV, copy an API key, read auto-generated docs.
- **Consumers** (programs) hit `GET /api/v1/datasets/{id}` with that key and get filtered,
  sorted, paginated JSON back.

Two auth systems, on purpose: the dashboard is guarded by **Supabase JWT + Postgres RLS**;
the public API is guarded by **hashed API keys** checked in the backend.

## Run it locally

**1. Backend** (needs a Supabase project + `backend/.env` — see [backend/README.md](backend/README.md)):

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

**2. Frontend** (`frontend/.env` holds the Supabase URL + anon key and `VITE_API_URL`):

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173
```

> Tip: for a smooth signup demo, disable email confirmation in Supabase
> (Authentication → Sign In / Providers → Email → turn off "Confirm email").

## Stack

| Layer | Tech |
|-------|------|
| Frontend | React, Vite, Tailwind CSS v4, React Router, supabase-js |
| Backend | FastAPI, asyncpg, supabase-py, PyJWT |
| Data / auth | Supabase (Postgres, Auth, Storage, RLS) |
