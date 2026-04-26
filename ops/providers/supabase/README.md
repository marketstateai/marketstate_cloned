# Supabase Adapter

Provider-specific tooling and helper assets for the current Supabase-backed
runtime.

Canonical responsibilities here:

- local/test helper scripts under `scripts/`
- provider env template in `.env.example`
- provider-specific operational notes

Canonical responsibilities elsewhere:

- database migrations and seed data: `ops/platform/database`
- exchange-rates function source: `services/core/apis/currency-api/functions/exchange-rates`
- portfolio bootstrap SQL: `services/core/portfolio/sql`
- watchlist demo write-policy SQL: `services/core/watchlists/scripts`

## Quick Test

```bash
cd /Users/gabrielzenkner/projects/marketstate/ops/providers/supabase
cp .env.example .env
set -a; source .env; set +a
./scripts/test_rpc.sh
```

## Watchlist REST Tests

```bash
cd /Users/gabrielzenkner/projects/marketstate/ops/providers/supabase
set -a; source .env; set +a
./scripts/test_get_watchlist.sh
./scripts/test_put_watchlist.sh
./scripts/test_post_watchlist_upsert.sh
```
