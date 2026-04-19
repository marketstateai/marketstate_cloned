# MarketState Business Plan

**Version:** Draft v1  
**Date:** 2026-04-19  
**Prepared for:** Founder and early investors

## 1. Executive Summary
MarketState is a paid SaaS platform for self-directed investors who manage multiple accounts and need better decision support. The product consolidates portfolio visibility, ties it to long-term goals, and provides risk/performance context with actionable alert loops.

### Why now
- Category demand is already validated by portfolio tracking and financial operating tools.
- Existing solutions are often broad or brokerage-centric rather than decision-centric.
- Self-directed investors continue to increase and need higher quality workflow tools.

### 12-month objective
- Reach 2,000 paying users at $10/month = $20,000 MRR.

### Long-term objective
- Scale toward 100,000 paying users = $1,000,000 MRR.

---

## 2. Company Vision and Mission
### Vision
Become the default operating system for active long-term investors.

### Mission
Turn scattered investing into a goal-driven system that shows users whether they are on track, why, and what to change next.

### Product principle
We optimize for clear decisions and progress, not engagement through noise.

---

## 3. Problem Statement
Active retail investors commonly hold assets across multiple brokers, pensions, and crypto accounts. Their data, risk exposure, and performance are fragmented.

### User-level consequences
- weak confidence in whether strategy is working,
- reactive decisions driven by short-term noise,
- time lost reconciling multiple dashboards/spreadsheets,
- unclear link between current portfolio behavior and long-term outcomes.

### Market gap
Most incumbents either:
- provide broad personal finance aggregation, or
- focus on execution/brokerage workflows, or
- report passively rather than guiding action.

MarketState addresses this gap with a goal-centric investor decision layer.

---

## 4. Target Customer and ICP
### Primary ICP (MVP)
- Age: 25-40
- Profile: self-directed investors with 2+ accounts
- Behavior: already investing regularly, already paying for some financial tooling
- Motivation: wants control, clarity, and compounding progress

### Secondary segments (post-MVP)
- higher-balance households,
- semi-pro traders,
- advisors needing client-facing intelligence workflows.

### Initial launch market
- London-first (from existing strategy notes), with expansion to other major financial metros after repeatable acquisition and retention metrics are proven.

---

## 5. Product Strategy
### MVP (must-have)
1. Unified portfolio dashboard (positions, allocation, PnL, progress)
2. Watchlists and threshold alerts
3. Risk analytics (concentration, drawdown, volatility)
4. Monthly report export
5. Paid subscription + entitlement management

### Not in MVP
- Full AI advisor
- Brokerage replacement
- Social investing network
- Advanced tax optimization engine

### Product moat direction
- workflow depth and clarity for the target segment,
- trusted historical data and behavior loop,
- consistent execution speed with narrow scope discipline.

---

## 6. Competitive Positioning
Competitor research indicates clear demand across:
- net-worth aggregation,
- portfolio tracking,
- all-in-one money hubs,
- robo-advisory and automated investing platforms.

### Positioning statement
MarketState is not a broad budgeting app and not a brokerage replacement. It is a paid investor operating layer focused on high-signal decisions for active multi-account investors.

### Differentiation pillars
- goal-linked portfolio decision support,
- risk + performance context in one workflow,
- action-oriented alerts and review loops,
- focused user segment and faster iteration.

---

## 7. Business Model and Pricing
### Core model
- B2C SaaS subscription
- Starter plan: $10/month

### Optional launch mechanics
- Capped founder lifetime deal for early capital/testimonial generation
- No broad free-forever tier during MVP validation phase

### Revenue assumptions (base case)
- ARPU: $10/month
- Gross margin target: software-standard SaaS profile (to be finalized with infra model)
- Growth driven by paid conversion + retention, not top-of-funnel vanity volume

---

## 8. Go-To-Market Strategy
### Channel focus (first 90 days)
1. Reddit investing communities
2. X/Twitter finance creator ecosystem
3. SEO content around portfolio/risk workflows
4. Limited launch cohorts (paid beta, optional LTD)

### Weekly GTM cadence
- 2 long-form educational posts
- 3 proof or insight social posts
- 1 user interview
- 1 product demo/update clip

### Trust-building assets
- changelog,
- roadmap,
- security/privacy page,
- review collection and testimonials.

### Conversion funnel (MVP)
1. Traffic -> waitlist
2. Waitlist -> paid beta
3. Paid beta -> retained paid users
4. Retained users -> referrals and social proof

---

## 9. Operations and Team Plan
### Team model (max 4 engineers)
1. Frontend Product Engineer
- Owns apps, UX, onboarding, activation metrics

2. Backend Product Engineer
- Owns auth, APIs, portfolio/order workflows, reliability at service layer

3. Data/Quant Engineer
- Owns ingestion quality, pricing/valuation logic, risk analytics

4. Platform/SRE/Security Engineer
- Owns infra, CI/CD, observability, billing stability, security controls

### Non-engineering support (minimum)
- part-time growth/marketing lead,
- part-time design support,
- legal/compliance advisor on demand.

---

## 10. Technical and Delivery Plan
### Existing strengths
- Substantial implementation already in data-platform and api-services foundations.
- Domain-oriented architecture prepared for modular scale.

### 16-week MVP timeline
**Weeks 1-4:** auth, billing, base portfolio model, initial ingestion  
**Weeks 5-8:** dashboard v1, watchlists, alerts, risk v1  
**Weeks 9-12:** reporting, observability, security and reliability baseline  
**Weeks 13-16:** paid beta onboarding, funnel instrumentation, launch assets

### Reliability targets
- 99.9% API availability target
- p95 read latency <300ms
- p95 write latency <600ms

---

## 11. Financial Plan (Draft)

### Revenue projection (example base case)
| Period | Paid users | ARPU | MRR | ARR run-rate |
|---|---:|---:|---:|---:|
| Month 12 | 2,000 | $10 | $20,000 | $240,000 |
| Month 24 | 8,000 | $10 | $80,000 | $960,000 |
| Month 36 | 20,000 | $10 | $200,000 | $2,400,000 |

### Performance metrics to manage weekly
- Activation rate
- Paid conversion rate
- Monthly churn / retention
- CAC and CAC payback
- Net revenue retention (if expansion pricing introduced later)

### Funding use framework (for raise)
- Product engineering and infra reliability
- Data quality and pipeline hardening
- GTM testing and customer acquisition
- Security/compliance baseline

---

## 12. Risks and Mitigation
### Risk: weak acquisition velocity
Mitigation:
- strict channel focus,
- weekly experimentation cadence,
- message/ICP refinement based on paid behavior.

### Risk: low retention after initial conversion
Mitigation:
- instrument weekly usage loop,
- prioritize insight/action value over feature breadth,
- systematic onboarding and first-value optimization.

### Risk: data quality trust issues
Mitigation:
- source transparency,
- reconciliation checks,
- clear confidence and freshness indicators.

### Risk: overbuilding
Mitigation:
- hard MVP scope guardrails,
- milestone-based roadmap,
- defer non-core features until retention targets are met.

### Risk: compliance/security incidents
Mitigation:
- logging/audit foundations,
- secrets and key hygiene,
- dependency scanning and incident runbooks.

---

## 13. Milestones and Success Criteria
### 0-3 months
- paid beta live
- first 20-50 paying users
- activation baseline established

### 3-6 months
- stable retention trend
- repeatable paid acquisition channel identified
- month-6 revenue target reached (to be finalized)

### 6-12 months
- 2,000 paying users target
- clear path to multi-channel growth
- investor-ready data room and KPI history

---

## 14. Immediate Decisions Required
1. Confirm exact beta launch date.
2. Confirm month-6 and month-12 paid user targets.
3. Confirm CAC ceiling and payback threshold.
4. Confirm run-rate budget and hiring plan.
5. Confirm LTD decision (yes/no, cap, price).

---

## 15. Conclusion
MarketState is a practical, execution-ready startup concept in a validated category. The plan intentionally starts narrow, monetizes early, and focuses on measurable outcomes: paid conversion, retention, and decision-quality value for a specific investor segment.

The next step is operational: lock assumptions, commit launch dates, and execute weekly against the milestone plan.
