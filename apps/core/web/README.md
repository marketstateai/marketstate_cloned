# Core Web App

Main customer web application for onboarding, portfolio monitoring, watchlists, and order entry.

## Current Setup

This folder currently ships a static GitHub Pages portal:

- `index.html`: Login screen + dashboard shell
- `styles.css`: Styling and responsive layout
- `app.js`: Client-side login mock, Supabase RPC dashboard fetch, watchlist upsert form
- `supabase-config.js`: Supabase public config values (URL + anon key)
- `supabase-client.js`: Supabase client initialization
- `CNAME`: Custom domain for GitHub Pages (`portal.marketstate.ai`)

## Local Preview

From this directory:

```bash
python3 -m http.server 4173
```

Then open `http://localhost:4173`.

## Supabase Integration (active)

- `app.js` calls `rpc('ms_get_portal_payload', { p_email })` to load dashboard data.
- If email profile is missing, it falls back to `demo@marketstate.ai`.
- Watchlist save form upserts into `public.ms_watchlist` with `onConflict: user_id,symbol`.
- If Supabase is unavailable, UI falls back to local mock data and shows a badge.
- Backend SQL bootstrap for this flow is under `services/core/portfolio/sql` and `services/core/watchlists/scripts`.

## GitHub Pages Deployment

Deployment is configured by:

- `.github/workflows/core-web-pages.yml`

It publishes `apps/core/web` whenever files in this folder change on `main`.

One-time GitHub setup:

1. In repo Settings -> Pages, set **Source** to **GitHub Actions**.
2. In your DNS provider, add a CNAME record:
   - Host: `portal`
   - Value: `<your-github-username>.github.io`
3. In Pages settings, confirm custom domain is `portal.marketstate.ai` and enable HTTPS.
