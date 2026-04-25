# Core Web App

Main customer web application for onboarding, portfolio monitoring, watchlists, and order entry.

## Current Setup

This folder currently ships a static GitHub Pages portal:

- `index.html`: Login screen + dashboard shell
- `styles.css`: Styling and responsive layout
- `app.js`: Client-side login mock + mock financial data rendering
- `CNAME`: Custom domain for GitHub Pages (`app.marketstate.ai`)

## Local Preview

From this directory:

```bash
python3 -m http.server 4173
```

Then open `http://localhost:4173`.

## Supabase Integration (next step)

- Replace mock login submit logic in `app.js` with Supabase auth calls.
- Replace `mockData` in `app.js` with data from your backend tables/views.

## GitHub Pages Deployment

Deployment is configured by:

- `.github/workflows/core-web-pages.yml`

It publishes `apps/core/web` whenever files in this folder change on `main`.

One-time GitHub setup:

1. In repo Settings -> Pages, set **Source** to **GitHub Actions**.
2. In your DNS provider, add a CNAME record:
   - Host: `app`
   - Value: `<your-github-username>.github.io`
3. In Pages settings, confirm custom domain is `app.marketstate.ai` and enable HTTPS.
