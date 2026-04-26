# Supabase CLI Adapter

This directory exists because the Supabase CLI expects a repo-local `supabase/`
project directory with `config.toml`.

It is not the canonical home for backend service logic.

Source of truth:

- function code: `services/core/apis/currency-api/functions/exchange-rates`
- database migrations: `ops/platform/database/migrations`
- seed data: `ops/platform/database/seed.sql`
- provider helper scripts: `ops/providers/supabase`

Treat this directory as a thin adapter shell for local CLI workflows only.
