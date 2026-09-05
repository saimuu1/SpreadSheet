# Sheetwave — Spreadsheet → API

### 🔗 **[Live demo → spread-sheet-fzur.vercel.app](https://spread-sheet-fzur.vercel.app)**

Upload a spreadsheet, get a live, queryable REST API in seconds — with auth, API keys, a
real query language, plan-based rate limits, and **Stripe subscription billing**. A
**FastAPI + Supabase** backend and a **React + Vite + Tailwind** frontend — with the rate
limiter rebuilt from scratch as a **lock-free token bucket in C++** (via pybind11).

> Frontend on Vercel · backend on Render (free tier — the first request after idle may take
> ~30s to wake up).

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

## Under the hood: a from-scratch rate limiter (C++)

The rate limiter isn't a library call or a `COUNT(*)` — it's a **lock-free token bucket
written in C++**, loaded via pybind11 (with a thread-safe pure-Python fallback). It replaced
the original per-request `SELECT count(*)` over a log table, which had a **TOCTOU race** and
grew unbounded.

- **Lock-free core** — each bucket's state (timestamp + fixed-point tokens) is packed into one
  `std::atomic<uint64_t>`; consuming a token is a single compare-and-swap, no lock.
- **Bounded & sharded** — a fixed-capacity table with striped locks and CLOCK eviction, so
  memory can't grow with the (unbounded) set of API keys.
- **Proven correct** — a stress test reproduces the original's race and shows this one grants
  exactly `burst` under 8 concurrent threads; **clean under ThreadSanitizer**.
- **Fast** — ~200M ops/s across 8 threads in C++; ~130 ns/call from Python, with **zero DB
  round-trips** (down from ~3 Supabase queries per request).
- **Live in production** — compiled in the Render build (non-fatal, with the Python fallback as
  a safety net) and running on the real request path. Verify it:
  [`/health`](https://sheetwave-backend.onrender.com/health) → `{"rate_limiter":"native (C++)"}`.

Design notes, tests, and benchmarks: **[backend/native/](backend/native/README.md)**.

## Who it's for

Anyone with structured data in a spreadsheet who needs it as an API — without building a backend:

- **No-code builders** — plug data straight into Webflow, Bubble, Retool, or Framer.
- **Non-technical teams** — own the sheet; the site reads the API, so data updates need no developer.
- **Developers & prototypers** — a real, queryable backend for a demo, portfolio, or hackathon in minutes.
- **Small businesses** — menus, listings, inventory, or pricing kept in a sheet and served live to a site.

They share one shape: structured data in a sheet, a need to consume it in software, and no
appetite to build a backend. The gap between "a file" and "an API" is the whole value — and
the users who outgrow the free tier (many datasets, heavy traffic, private APIs) are exactly
who **Pro billing** is for.

## Repository layout

```
SpreadSheet/
├── backend/          # FastAPI — auth, upload + inference, API keys, query language,
│   │                 # rate limiting & tiers, Stripe billing (see backend/README.md)
│   └── native/       # C++ lock-free rate limiter + pybind11 binding (see native/README.md)
└── frontend/         # React — landing, auth, dashboard, per-dataset API docs
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
| Performance | C++17 lock-free rate limiter via pybind11 (thread-safe Python fallback) |
| Deploy | Vercel (frontend) · Render (backend) |
