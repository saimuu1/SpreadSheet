# Spreadsheet-to-API — Backend

Upload a CSV, get a live, queryable REST API for it. FastAPI + Supabase (Postgres, Auth,
Storage, RLS).

Two audiences, two auth systems:

| Path | Who | Auth | DB access |
|------|-----|------|-----------|
| Dashboard (`/api/account`, `/api/datasets`, `/api/keys`) | the **Builder** (a human, via the website) | Supabase JWT | RLS-scoped Supabase client — Postgres enforces per-user isolation |
| Public API (`/api/v1/datasets/{id}`) | the **Consumer** (a program) | hashed API key | direct asyncpg pool + parameterized SQL over `jsonb` |

## Setup

1. **Install deps** (uses [uv](https://docs.astral.sh/uv/)):
   ```bash
   uv sync
   ```

2. **Configure `.env`** — copy the template and fill from your Supabase project:
   ```bash
   cp .env.example .env
   ```
   Values live in the Supabase dashboard:
   - `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY` → Settings → API
   - `SUPABASE_JWT_SECRET` → Settings → API → JWT Settings
   - `DATABASE_URL` → Settings → Database → Connection string (URI)

3. **Create the schema** — in the Supabase SQL editor, run in order:
   - `supabase/schema.sql` (tables, indexes, profile trigger)
   - `supabase/rls.sql` (row-level security policies)

4. **Create the Storage bucket** named to match `STORAGE_BUCKET` (default `raw-uploads`),
   Supabase dashboard → Storage → New bucket.

## Stripe billing (test mode, optional)

The Pro plan upgrades through Stripe. Without these env vars the app still runs — the
billing endpoints just return `503` until configured.

1. Run `supabase/stripe.sql` in the SQL editor (adds `stripe_customer_id` /
   `stripe_subscription_id` to `profiles`).
2. In the **Stripe dashboard (test mode)**:
   - Create a **Product** "Pro" with a **recurring** price (e.g. $7/mo) → copy the **Price ID**
     (`price_…`) into `STRIPE_PRICE_ID`.
   - Developers → API keys → copy the **Secret key** (`sk_test_…`) into `STRIPE_SECRET_KEY`.
3. **Webhook** — forward Stripe events to the local server with the Stripe CLI:
   ```bash
   stripe listen --forward-to localhost:8000/api/webhooks/stripe
   ```
   It prints a signing secret (`whsec_…`) → put it in `STRIPE_WEBHOOK_SECRET`.
   (In production, add a webhook endpoint in the dashboard pointing at your deployed URL and
   subscribe to `checkout.session.completed` + `customer.subscription.*`.)
4. Set `FRONTEND_URL` to where Stripe should return the user (default `http://localhost:5173`).

Flow: dashboard **Upgrade to Pro** → Stripe Checkout → on success a webhook flips
`profiles.plan` to `pro`. **Manage billing** opens the Stripe Customer Portal; cancelling
there flips the plan back to `free`. Use test card `4242 4242 4242 4242`, any future expiry/CVC.

## Run

```bash
uv run uvicorn app.main:app --reload
```

- Health check: http://localhost:8000/health
- Interactive API docs (OpenAPI): http://localhost:8000/docs

## Tests

Pure-logic tests (schema inference + query parser) need no credentials:

```bash
uv run pytest tests/test_inference.py tests/test_query_parser.py -q
```

## End-to-end with curl

The dashboard routes need a **Supabase access token** (`TOKEN`). The quickest way to get one
for testing: create a user in Supabase → Authentication, then sign them in via the
auth REST endpoint, or copy a session token from a logged-in frontend.

```bash
BASE=http://localhost:8000
TOKEN=<supabase access token>

# Who am I (profile)
curl -s $BASE/api/account/me -H "Authorization: Bearer $TOKEN"

# Upload a CSV -> returns the inferred schema
curl -s -X POST $BASE/api/datasets \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@tests/sample.csv"

# List datasets, get one dataset's schema, get its docs
curl -s $BASE/api/datasets -H "Authorization: Bearer $TOKEN"
curl -s $BASE/api/datasets/<DATASET_ID> -H "Authorization: Bearer $TOKEN"
curl -s $BASE/api/datasets/<DATASET_ID>/docs -H "Authorization: Bearer $TOKEN"

# Create an API key (raw key shown ONCE)
curl -s -X POST $BASE/api/keys -H "Authorization: Bearer $TOKEN"

# Upgrade / downgrade plan (stubbed payment)
curl -s -X POST $BASE/api/account/upgrade -H "Authorization: Bearer $TOKEN"
```

Then hit the **public API** as a Consumer with the API key:

```bash
KEY=<raw api key from create-key>
DS=<dataset id>

# All rows
curl -s "$BASE/api/v1/datasets/$DS" -H "Authorization: Bearer $KEY"

# Filter + sort + paginate
curl -s "$BASE/api/v1/datasets/$DS?category=protein&price__gt=20&sort=-rating&page=1&limit=25" \
  -H "Authorization: Bearer $KEY"
```

Expected error behaviors:
- no/invalid key → `401`
- key's owner doesn't own the dataset → `403`
- unknown field or bad value type → `400`
- over the plan's rate limit → `429` (with `Retry-After`)

## The query language

`?field=value` filters with optional operator suffixes:

| Param | Meaning |
|-------|---------|
| `category=protein` | equals |
| `price__gt=20` / `__lt` / `__gte` / `__lte` | numeric/date comparisons |
| `name__contains=oil` | text search (ILIKE) |
| `sort=-rating` | sort descending (no `-` = ascending) |
| `page=2&limit=25` | pagination (limit capped at 100) |

Field names are whitelisted against the dataset's inferred schema, and both field names and
values are bound as SQL parameters — so user input can never alter the query structure.

## Project layout

```
app/
  main.py            # app, CORS, request-id middleware, DB lifespan
  config.py          # env settings
  db.py              # asyncpg pool (public API path; jsonb codec)
  supabase_client.py # service + RLS-scoped user clients (dashboard path)
  dependencies.py    # get_current_user (JWT) ; resolve_api_key (key->owner)
  models/schemas.py  # Pydantic models
  services/          # inference, keys, query_parser, query_builder, rate_limit, plans
  routers/           # account, datasets, api_keys, public_api
supabase/            # schema.sql, rls.sql
tests/               # inference + query-parser unit tests, sample.csv
```

## Scaling notes (deliberate scope calls)

- **jsonb over a table-per-dataset.** One `rows` table holds any shape; Postgres still filters
  and sorts inside the JSON. Dynamic tables are the scaling path.
- **Rate limiting in Postgres.** Counting `request_logs` rows works now; Redis (sliding
  window / token bucket) is the production path.
- **Payments are stubbed.** `upgrade` flips `profiles.plan`; the real work is that the rate
  limiter and upload cap read that flag live.
