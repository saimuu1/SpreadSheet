# Sheetwave — Spreadsheet → API

Upload a spreadsheet, get a live, queryable REST API in seconds — with auth, API keys, a
real query language, plan-based rate limits, and **Stripe subscription billing**. A
**FastAPI + Supabase** backend and a **React + Vite + Tailwind** frontend.

## What this is

A complete, deployable SaaS product — and a reusable base for metered API businesses. The
hard parts are built and tested end to end: multi-tenant auth, hashed API keys, schema
inference, a URL query language, plan-tiered rate limiting, and **real Stripe billing**
(Checkout → webhook → Customer Portal). If a project ever needs a Stripe-billed API SaaS,
this is the foundation to build on.

## What it does

- **Builders** use the website: sign up, upload a CSV, copy an API key, read auto-generated
  docs, and subscribe to Pro through Stripe.
- **Consumers** (programs) call `GET /api/v1/datasets/{id}` with that key and get filtered,
  sorted, paginated JSON back.

Two authentication systems, on purpose: the dashboard is guarded by **Supabase JWT +
Postgres Row-Level Security**; the public API is guarded by **hashed API keys** checked in
the backend.

## Features

- **Schema inference** — every uploaded CSV column is auto-typed as number, boolean, date, or text.
- **A real query language** — `?price__gt=20&name__contains=oil&sort=-rating&page=2&limit=25`,
  parsed against the inferred schema.
- **Injection-safe** — field names are schema-whitelisted and all values are bound as
  parameters in `jsonb` queries.
- **Multi-tenancy** — Postgres RLS isolates dashboard data; hashed API keys scope the public API.
- **Plan tiers + rate limiting** — Free vs Pro caps (datasets, requests/day, requests/min)
  enforced in the backend, not the UI.
- **Stripe subscription billing** — Checkout for upgrades, a webhook that syncs subscription
  status to the `plan` flag, and the Customer Portal for self-serve manage/cancel.
- **Auto-generated docs** — each dataset gets an endpoint reference with fields, operators,
  a cURL sample, and a live "try it" panel.

## Repository layout

```
SpreadSheet/
├── backend/    # FastAPI — auth, upload + inference, API keys, query language,
│               # rate limiting & tiers, Stripe billing (see backend/README.md)
└── frontend/   # React — landing, auth, dashboard, per-dataset API docs
```

## Run it locally

**1. Backend** (needs a Supabase project + `backend/.env` — full setup in [backend/README.md](backend/README.md)):

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

**2. Frontend** (`frontend/.env` holds `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, `VITE_API_URL`):

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173
```

**3. Stripe billing** (optional — the app runs without it; billing endpoints return `503`
until configured). Create a recurring Pro price, add the test keys to `backend/.env`, and
forward webhooks locally:

```bash
stripe listen --forward-to localhost:8000/api/webhooks/stripe
```

Details and the exact env vars are in [backend/README.md](backend/README.md).

> Tip: for instant signup, disable email confirmation in Supabase
> (Authentication → Sign In / Providers → Email → turn off "Confirm email").

## Stack

| Layer | Tech |
|-------|------|
| Frontend | React, Vite, Tailwind CSS v4, React Router, supabase-js |
| Backend | FastAPI, asyncpg, supabase-py, PyJWT, Stripe |
| Data / auth | Supabase (Postgres, Auth, Storage, RLS) |
| Billing | Stripe (Checkout, webhooks, Customer Portal) |
