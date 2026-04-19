# MarketState Architecture Manifest

**Generated:** 2026-04-19  
**Scope:** `/Users/gabrielzenkner/projects/marketstate`  
**Business target:** 10,000 paid users at $10/month ($100,000 MRR)

## Executive Summary
This workspace is structured as a startup-grade, domain-oriented microservice platform for an investment SaaS product.

- `apps`: customer/operator clients.
- `services`: business microservices (accounts, portfolio, orders, billing, notifications).
- `platform-backend`: shared data and infrastructure backbone.
- `platform-frontend`: shared client runtime foundations.
- `packages`: shared contracts, types, UI, and policy libraries.
- `infra`: environment and infrastructure manifests.
- `docs`: architecture and runbooks.
- `business`: strategy and market context assets.

Current reality: `platform-backend/data-platform` and `services/api-services` are the most implemented repositories; many others are scaffold-level placeholders and should be activated in priority order.

## Workspace Inventory

### Top-Level Contents
- `apps/`
- `business/`
- `docs/`
- `infra/`
- `packages/`
- `platform-backend/`
- `platform-frontend/`
- `services/`

### Top-Level File/Directory Metrics
| Path | Files | Directories |
|---|---:|---:|
| `apps` | 4 | 4 |
| `business` | 6 | 1 |
| `docs` | 1 | 1 |
| `infra` | 1 | 1 |
| `packages` | 7 | 7 |
| `platform-backend` | 5124 | 652 |
| `platform-frontend` | 1 | 1 |
| `services` | 180 | 119 |

### Detected Nested Git Repositories
- `/Users/gabrielzenkner/projects/marketstate/platform-backend/data-platform`
- `/Users/gabrielzenkner/projects/marketstate/services/api-services`
- `/Users/gabrielzenkner/projects/marketstate/platform-backend/data-platform/dags/dbt/marketstate/dbt_packages/dbt_profiler`

## Directory Map (Level 2)
```text
marketstate/
├── apps/
│   ├── admin-web/
│   ├── mobile/
│   └── web/
├── business/
│   ├── Screenshot 2026-04-19 at 10.05.37.png
│   ├── archetctiure.txt
│   ├── business.md
│   ├── competitors.json
│   ├── mvp.txt
│   └── playbook.txt
├── docs/
│   └── README.md
├── infra/
│   └── README.md
├── packages/
│   ├── contracts-events/
│   ├── contracts-openapi/
│   ├── design-system/
│   ├── shared-authz-policies/
│   ├── shared-types/
│   └── shared-utils/
├── platform-backend/
│   ├── cache/
│   ├── ci-cd-release/
│   ├── config-feature-flags/
│   ├── data-ingestion/
│   ├── data-platform/
│   ├── data-processing-batch/
│   ├── data-processing-stream/
│   ├── data-warehouse/
│   ├── event-bus/
│   ├── infra-provisioning/
│   ├── observability-logging/
│   ├── observability-metrics/
│   ├── observability-tracing/
│   ├── operational-db-migrations/
│   ├── orchestration/
│   ├── search-index/
│   ├── secrets-kms/
│   └── security-scanning/
├── platform-frontend/
└── services/
    ├── admin-backoffice/
    ├── alerts-notifications/
    ├── analytics-risk/
    ├── api-gateway/
    ├── api-services/
    ├── audit-compliance/
    ├── billing-subscriptions/
    ├── documents-reports/
    ├── identity-auth/
    ├── market-data-api/
    ├── orders-execution/
    ├── portfolio/
    ├── pricing-valuation/
    ├── user-profile/
    └── watchlists/
```

## Domain Responsibilities and Product Impact

### Apps (`apps/*`)
- **`web`**: Main investor web experience.
  - Example: holdings dashboard, watchlists, order forms, subscription upgrade prompts.
- **`mobile`**: Fast trading and alerts on mobile.
  - Example: push-driven workflows for price triggers and order updates.
- **`admin-web`**: Operator and support console.
  - Example: account recovery, billing exception review, compliance escalations.

### Shared Packages (`packages/*`)
- **`contracts-openapi`**: API contract definitions.
  - Example: versioned schema for portfolio and order APIs.
- **`contracts-events`**: Event contracts for async workflows.
  - Example: `OrderPlaced`, `OrderFilled`, `PriceAlertTriggered`.
- **`shared-types`**: Domain types used across repos.
  - Example: `Money`, `InstrumentId`, `SubscriptionTier`.
- **`shared-utils`**: Shared utility functions.
  - Example: date normalization, ID generation, resilient retries.
- **`shared-authz-policies`**: Reusable authorization policies.
  - Example: premium feature gates and admin-only policy checks.
- **`design-system`**: UI component primitives.
  - Example: data table, chart container, alert components.

### Business Microservices (`services/*`)
- **`api-gateway`**: Single secure ingress for clients.
  - Example: route authenticated requests to downstream services and enforce policy.
- **`identity-auth`**: Authentication and session lifecycle.
  - Example: sign-in, MFA, token refresh, session revocation.
- **`user-profile`**: User preferences and profile settings.
  - Example: timezone, currency, notifications preferences.
- **`billing-subscriptions`**: Revenue and entitlements.
  - Example: create/manage $10/month subscriptions and feature access.
- **`portfolio`**: Positions, balances, and PnL.
  - Example: compute holdings and performance for each user account.
- **`orders-execution`**: Order management and execution integration.
  - Example: validate orders, submit, and track fills/rejections.
- **`pricing-valuation`**: Instrument pricing and valuation logic.
  - Example: mark-to-market values feeding portfolio and risk views.
- **`market-data-api`**: Market and reference data APIs.
  - Example: quotes, candles, metadata.
- **`watchlists`**: User watchlist state and triggers.
  - Example: CRUD watchlists and bind symbol alerts.
- **`alerts-notifications`**: Delivery engine for outbound alerts.
  - Example: push/email notifications for order fills and thresholds.
- **`analytics-risk`**: Risk and analytics outputs.
  - Example: concentration risk, drawdown indicators, scenario analysis.
- **`documents-reports`**: Statements and downloadable reports.
  - Example: monthly statements and tax-ready export bundles.
- **`audit-compliance`**: Immutable compliance event trail.
  - Example: admin action logs and order decision audit history.
- **`admin-backoffice`**: Operational service workflows.
  - Example: support correction actions and manual review tooling.
- **`api-services`**: Existing implemented service bundle (active).
  - Example: currency API with token auth, rate limiting, CI workflows.

### Backend Platform (`platform-backend/*`)
- **`data-platform`**: Airflow/dbt orchestration and data backbone (active).
  - Example: ingest -> transform -> warehouse pipelines for portfolio analytics.
- **`data-ingestion`**: Source ingestion connectors.
  - Example: fetch and normalize external market datasets.
- **`data-processing-stream`**: Low-latency stream processing.
  - Example: process near-real-time market events for alerts.
- **`data-processing-batch`**: Scheduled heavy computation.
  - Example: nightly risk aggregates and precomputed analytics.
- **`data-warehouse`**: Curated analytical models.
  - Example: product, growth, and risk reporting marts.
- **`cache`**: Hot-path read optimization.
  - Example: quote and session caches.
- **`event-bus`**: Async communication substrate.
  - Example: publish order and pricing events to multiple consumers.
- **`orchestration`**: Multi-step workflow management.
  - Example: reconciliation and retries across service boundaries.
- **`search-index`**: Symbol/instrument search indexing.
  - Example: instant ticker autocomplete and lookup.
- **`config-feature-flags`**: Runtime feature control.
  - Example: gradual rollout for premium analytics features.
- **`infra-provisioning`**: Infrastructure as code.
  - Example: provision networks, compute, databases, and queues.
- **`ci-cd-release`**: CI/CD and release automation.
  - Example: build/test/deploy pipelines with quality gates.
- **`operational-db-migrations`**: Database schema evolution.
  - Example: controlled online migrations and rollback safety.
- **`observability-logging`**: Centralized log management.
  - Example: request-correlated logs across gateway and services.
- **`observability-metrics`**: Service metrics and SLO monitoring.
  - Example: latency/error dashboards and alert thresholds.
- **`observability-tracing`**: Distributed tracing.
  - Example: trace full request paths for performance debugging.
- **`security-scanning`**: Vulnerability and dependency scanning.
  - Example: CI enforcement on critical CVEs.
- **`secrets-kms`**: Secret storage and key management.
  - Example: encrypted runtime secret retrieval and rotation.

### Frontend Platform (`platform-frontend`)
- Shared frontend runtime layer.
- Example: API client SDK, auth/session integration, telemetry wrappers used by `web`, `mobile`, and `admin-web`.

### Business Artifacts (`business`)
- Strategy and commercial context files.
- Example: competitor inputs (`competitors.json`) and launch notes (`mvp.txt`, `playbook.txt`).

## 100K User SaaS Operating Plan

### Target Economics
- **Users:** 100,000 paid
- **Price:** $10/month
- **MRR:** $1,000,000
- **ARR:** $12,000,000

### Reliability Targets
- API availability: **99.9%** monthly.
- p95 latency (read paths): **<300ms**.
- p95 latency (write/order paths): **<600ms**.
- Data freshness:
  - Market-sensitive paths: **sub-minute where feasible**.
  - Analytics/risk batches: **hourly/nightly** based on cost/accuracy trade-offs.

### Core Journeys to Harden First
- Signup -> payment -> entitlement activation.
- Login/MFA -> dashboard -> watchlist/portfolio load.
- Order submission -> execution status -> portfolio and notification updates.
- Monthly statement/report generation.

## Team Model (Maximum 4 Specialists)

1. **Frontend Product Engineer**
- Owns: `apps/*`, `platform-frontend`, `packages/design-system`.
- Mission: conversion UX, client performance, release speed.

2. **Backend Product Engineer**
- Owns: `services/api-gateway`, `identity-auth`, `user-profile`, `portfolio`, `orders-execution`, `watchlists`.
- Mission: secure APIs and transaction correctness.

3. **Data/Quant Engineer**
- Owns: `platform-backend/data-platform`, `data-ingestion`, `data-processing-*`, `data-warehouse`, `pricing-valuation`, `market-data-api`, `analytics-risk`.
- Mission: data quality, model quality, freshness.

4. **Platform/SRE/Security Engineer**
- Owns: `infra`, `infra-provisioning`, `ci-cd-release`, `observability-*`, `security-scanning`, `secrets-kms`, `operational-db-migrations`, `billing-subscriptions`, `audit-compliance`.
- Mission: uptime, safe deployments, security, billing reliability.

## Build Sequence for a Real Startup

### Phase 1 (Weeks 0-6): Revenue and Trust Foundation
- Harden `identity-auth`, `billing-subscriptions`, `api-gateway`, `portfolio`, `market-data-api`.
- Stabilize current active repos: `services/api-services` and `platform-backend/data-platform`.
- Stand up minimum observability and incident runbooks.

### Phase 2 (Weeks 6-12): Transaction and Retention Loop
- Build `orders-execution`, `watchlists`, `alerts-notifications`, `pricing-valuation`.
- Integrate `event-bus` for asynchronous fan-out.
- Expand `admin-backoffice` for support workflows.

### Phase 3 (Weeks 12-20): Compliance and Scale Controls
- Build `audit-compliance`, `documents-reports`, `analytics-risk`.
- Enforce migration discipline, security scanning gates, and key management.
- Introduce feature flags and staged releases.

### Phase 4 (Week 20+): Growth and Efficiency
- Deepen mobile/admin functionality.
- Optimize caching and search performance.
- Expand product analytics and experimentation.

## Current Gap Summary
- **Implemented cores:** `platform-backend/data-platform`, `services/api-services`.
- **Mostly scaffolded:** most other services/modules.
- **Recommendation:** execute strictly by phase priority instead of parallelizing every scaffold.

## Mandatory Cross-Cutting Standards
Every service should ship with:
- health/readiness endpoints,
- structured logs with request IDs,
- metrics instrumentation,
- authentication/authorization middleware,
- contract tests (OpenAPI/events),
- rollback-ready deployments,
- migration plans,
- dashboard + alert links,
- runbook references in `docs`.

## Architecture Decision
Keep the current root layout as the canonical structure:
- `apps`, `services`, `platform-backend`, `platform-frontend`, `packages`, `infra`, `docs`, `business`.

This structure is appropriate for a real investment SaaS and can scale to a 100k paid-user operating model with a focused 4-engineer team.
