# Supabase Backend (Portal Demo)

Minimal Supabase backend for the MarketState portal with mock data.

## What This Creates

- `ms_profiles`
- `ms_portfolio_snapshots`
- `ms_holdings`
- `ms_watchlist`
- `ms_activity_log`
- `ms_get_portal_payload(p_email text)` RPC for one-call dashboard fetch

It also seeds one demo user:

- `demo@marketstate.ai`

## Quick Setup (Supabase Free Tier)

1. Open your Supabase project.
2. Go to **SQL Editor**.
3. Paste and run:
   - `backend/supabase/sql/bootstrap_portal_demo.sql`
   - `backend/supabase/sql/enable_demo_rest_writes.sql` (for PUT/POST tests)

## Quick Test

In SQL Editor:

```sql
select public.ms_get_portal_payload('demo@marketstate.ai');
```

From terminal:

```bash
cd /Users/gabrielzenkner/projects/marketstate/backend/supabase
cp .env.example .env
# Fill SUPABASE_URL and SUPABASE_ANON_KEY in .env, then:
set -a; source .env; set +a
./scripts/test_rpc.sh
```

## REST Method Tests (GET / PUT / POST)

Load environment first:

```bash
cd /Users/gabrielzenkner/projects/marketstate/backend/supabase
set -a; source .env; set +a
```

GET watchlist:

```bash
./scripts/test_get_watchlist.sh
```

PUT existing symbol (default updates `AMZN`):

```bash
./scripts/test_put_watchlist.sh
# or custom:
./scripts/test_put_watchlist.sh AMZN 201.10 1.88
```

POST upsert symbol (default upserts `PLTR`):

```bash
./scripts/test_post_watchlist_upsert.sh
# or custom:
./scripts/test_post_watchlist_upsert.sh NVDA 980.25 2.72
```

## Notes

- Current RLS policies allow public read for quick demo testing.
- `enable_demo_rest_writes.sql` opens write policies for watchlist demo tests.
- Tighten policies before production.
