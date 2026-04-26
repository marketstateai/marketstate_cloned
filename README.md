# MarketState

This repository is intentionally organized as one monolith with clear domain boundaries.

## Core Product Components (In Scope)

### Apps
- `apps/core/web`: Primary customer-facing web app for onboarding, portfolio view, trading, and billing.

### Core Services
- `services/core/api-gateway`: Single API entrypoint and routing layer.
- `services/core/auth`: Authentication, sessions, and access control.
- `services/core/user-profile`: User settings, preferences, account metadata.
- `services/core/portfolio`: Holdings, P&L, allocation, performance snapshots.
- `services/core/orders`: Order lifecycle and execution orchestration.
- `services/core/apis/currency-api`: Currency conversion API and rate ingestion surface.
- `services/core/apis/market-data-api`: Market quotes/candles/reference data API (scaffold).
- `services/core/apis/broker-data-api`: Broker/account/position synchronization API (scaffold).
- `services/core/watchlists`: User watchlists and saved instruments.
- `services/core/notifications`: Price/order/account notifications.
- `services/core/payments`: Subscription billing and payment workflows.
- `services/core/deployment`: Release orchestration, rollback, and environment promotion.

### Data Platform
- `data/`: Pipelines, transformations, orchestration, analytics datasets, and data quality checks.

### Shared Modules
- `shared/`: Shared contracts, types, utilities, policies, and design system.

### Platform Operations
- `.github/workflows/`: CI/CD workflows.
- `ops/`: Infra/docs assets used to deploy and operate the monolith.
- `ops/platform/database`: Shared database lifecycle assets such as migrations and seeds.
- `ops/providers`: Provider-specific adapters and local tooling. Vendor names belong here, not in service paths.

## Deferred (Backlog)

These are preserved but not in active MVP delivery scope:
- `services/backlog/admin-backoffice`
- `services/backlog/analytics-risk`
- `services/backlog/audit-compliance`
- `services/backlog/documents-reports`
- `services/backlog/pricing-valuation`
- `apps/backlog/admin-web`
- `apps/backlog/mobile`
- `apps/backlog/web`

## Scaling Model (while staying monolithic)

- Keep one deployable unit, but enforce domain boundaries by directory and API contracts.
- Scale reads with caching and replicas; scale writes with queue-backed async workers.
- Isolate heavy data workloads inside `data/` so user-facing APIs stay responsive.
- Use CI gates per domain path to reduce blast radius and keep quality high.
