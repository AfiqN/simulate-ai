# SimulateAI — Roadmap to Product-Market Fit

> Domain-agnostic multi-agent simulation for stress-testing any decision.
> Model: Open-core. Core engine open source, commercial layer on top.
> Goal: Validate that real people use this, then monetize.

---

## Current State (v0.9 — Feature-Complete PoC)

The simulation engine is mature. What's missing isn't features — it's **product packaging** for public consumption.

### ✅ Done (Engine)

- Schema-first architecture (domain-agnostic, no hardcoded vocabulary)
- 5-stage pipeline: Architect → Swarm → Perceive → Debate → Crisis
- Multi-dimensional utility (vector, not scalar)
- Structured reasoning chain per agent per dimension
- Quantitative metrics: vote tally, distributions, swing analysis, consensus index
- Adversary pairing with faction evolution
- Sensitivity analysis (multi-run variance)
- RAG perspective injection
- Conditional dynamics (triggers, game-theoretic payoffs)
- Historical context + precedent tracking
- Custom stakeholder injection

### ✅ Done (Infra)

- Web frontend (React/TS) with live progress
- REST API (FastAPI) with async job queue
- Docker + docker-compose
- Environment-based config (.env)
- Health endpoint
- PDF export, chart data, comparison view
- Webhooks
- Non-interactive CLI runner + batch mode
- SQLite persistence

### ❌ Not Done (Product)

- No hosted demo (strangers can't try without setup)
- No onboarding flow (first-time user sees raw form)
- No example gallery (user doesn't know what good input looks like)
- No usage analytics (we don't know what people do)
- No rate limiting / abuse protection
- No auth (anyone with URL has full access)
- No pricing/tier enforcement
- No community presence (GitHub, Discord, etc.)

---

## Phase 0 — Launch-Ready (4-6 weeks)

**Goal:** A stranger can try SimulateAI in under 2 minutes, without local setup, and understand what it does.

### 0.1 Hosted Demo

- [ ] Deploy to Railway/Fly.io/Render (one-click deploy button in README)
- [ ] Free tier: 3 simulations/day, max 5 agents, standard depth only
- [ ] Rate limiting per IP (no auth required for demo)
- [ ] Auto-cleanup: runs older than 7 days deleted

### 0.2 Onboarding & Example Gallery

- [ ] First-visit guided tour (3 steps: pick example → watch it run → read report)
- [ ] 5-7 curated example stimuli across domains:
  - Startup pitch (fintech, SaaS, marketplace)
  - Policy debate (regulation, public health)
  - Personal decision (career move, relocation)
  - Technical architecture (monolith vs micro, build vs buy)
  - Strategy (market entry, pricing change)
- [ ] "Try this example" one-click buttons on landing page
- [ ] Show example output/report inline (so user sees value before signing up)

### 0.3 Landing Page & Positioning

- [ ] Clear value prop: "Stress-test your idea before you build it"
- [ ] Before/after comparison: "asking ChatGPT" vs "structured simulation"
- [ ] 3 use case sections with example outputs
- [ ] Social proof placeholder (testimonials, logos — fill when available)
- [ ] Email capture for waitlist / updates
- [ ] Open source badge + GitHub link (builds trust)

### 0.4 Core UX Polish

- [ ] Reduce time-to-first-result: "Quick" mode runs in <90 seconds
- [ ] Progress bar with ETA (not just spinner)
- [ ] Mobile-responsive (people will try from phone after seeing a link)
- [ ] Error states that guide recovery (not stack traces)
- [ ] Share link per simulation result (public URL for the report)

### 0.5 Analytics & Feedback

- [ ] PostHog/Plausible (privacy-respecting analytics)
- [ ] Track: stimuli submitted, completion rate, time-on-report, share clicks
- [ ] In-app feedback widget ("Was this useful? What would you change?")
- [ ] Funnel: landing → start sim → complete → share/return

---

## Phase 1 — Validate (weeks 5-10)

**Goal:** Get 50+ real users. Learn what they actually want. Identify who would pay.

### 1.1 Launch & Distribution

- [ ] Product Hunt launch
- [ ] Hacker News "Show HN" post
- [ ] Reddit posts: r/startup, r/ProductManagement, r/ArtificialIntelligence
- [ ] Twitter/X thread with example simulation GIF
- [ ] Dev.to / Hashnode technical writeup ("How I built a multi-agent debate simulator")
- [ ] GitHub: proper README, contributing guide, issue templates, discussions enabled

### 1.2 Open Source Packaging

- [ ] LICENSE file (Apache 2.0 or MIT for core)
- [ ] CONTRIBUTING.md with setup guide
- [ ] GitHub Actions: CI (pytest + lint), auto-release
- [ ] PyPI package for CLI-only usage (`pip install simulate-ai`)
- [ ] Separate `simulate-ai-server` package or just `docker compose up`

### 1.3 User Interview Pipeline

- [ ] In-app "Want to chat about your use case?" CTA
- [ ] Schedule 10 user interviews (find through launch channels)
- [ ] Key questions:
  - What did you simulate? Why?
  - Was the output useful? Would you share it with your team?
  - What's missing that would make you come back?
  - Would you pay for this? How much? What would justify it?
- [ ] Document patterns → update roadmap based on findings

### 1.4 Depth Tiers (User-Facing)

- [ ] Expose quick/standard/deep as first-class UI choice
- [ ] Quick: 2 rounds, 3-5 agents, <90s — free forever
- [ ] Standard: 3 rounds, 5-10 agents, 3-8 min — free tier limited
- [ ] Deep: 3+ rounds, 10-20 agents, multi-run CI, 15-40 min — paid only

### 1.5 Retention Hooks

- [ ] Email report delivery (run finishes → PDF in inbox)
- [ ] "Re-run with different assumptions" one-click
- [ ] Simulation history per user (requires basic auth)
- [ ] Weekly digest: "People also simulated..." (inspiration)

---

## Phase 2 — Monetize (weeks 10-20)

**Goal:** Convert validated demand into revenue. $1K MRR milestone.

### 2.1 Auth & User Accounts

- [ ] OAuth (Google, GitHub) — no email/password maintenance
- [ ] User dashboard: my simulations, usage quota, billing
- [ ] Team workspace (shared history, shared custom personas)

### 2.2 Pricing Model

- [ ] Freemium:
  - Free: 5 quick sims/month, 2 standard/month, no deep
  - Pro ($29/mo): unlimited quick/standard, 10 deep/month, API access, PDF export
  - Team ($99/mo): 5 seats, shared workspace, custom personas, priority queue
  - Enterprise (custom): SSO, SLA, dedicated infra, bulk API, webhooks
- [ ] Stripe integration
- [ ] Usage metering (track runs per user per tier)

### 2.3 API Productization

- [ ] API key management (generate, revoke, rotate)
- [ ] Rate limiting per tier
- [ ] API docs (OpenAPI/Swagger auto-generated from FastAPI)
- [ ] SDKs: Python, TypeScript (auto-generated from spec)
- [ ] Webhook delivery with retry + dead letter queue

### 2.4 Pro Features (Differentiators)

- [ ] Custom persona library (save and reuse personas across sims)
- [ ] Branded reports (company logo, custom colors, custom footer)
- [ ] Comparison mode: run same stimulus with different parameters side-by-side
- [ ] Batch API: submit N stimuli, get N reports (consulting use case)
- [ ] Export: Notion, Google Docs, Confluence integration

### 2.5 Trust & Quality

- [ ] Reproducibility mode: same seed → same result (fix temperature, order)
- [ ] Confidence intervals on verdicts (from multi-run sensitivity)
- [ ] Citation sources in agent reasoning (when RAG is active)
- [ ] "Methodology" section auto-appended to reports (for sharing with stakeholders)

---

## Phase 3 — Scale (months 5-12)

**Goal:** Grow to $10K+ MRR. Identify if this is a venture-scale opportunity or a sustainable indie product.

### 3.1 B2B Features

- [ ] SSO (SAML, OIDC)
- [ ] Audit log (who ran what, when)
- [ ] Role-based access (admin, analyst, viewer)
- [ ] Custom LLM backend (customer's own API key or private deployment)
- [ ] On-premise deployment option
- [ ] SOC 2 compliance checklist

### 3.2 Platform Expansion

- [ ] Plugin system: custom round types, custom metrics, custom report sections
- [ ] Template marketplace: pre-built simulation templates per industry
- [ ] Community personas: share/discover persona libraries
- [ ] Integration hub: Slack bot, Notion widget, Linear/Jira integration

### 3.3 Intelligence Layer

- [ ] Cross-simulation insights: "Based on 500 fintech simulations, regulatory risk is the #1 failure mode"
- [ ] Industry benchmarks: "Your idea scored in the top 20% for market fit"
- [ ] Trend detection: what are people simulating most? (aggregated, anonymized)

### 3.4 Venture vs. Indie Decision Point

At this stage, evaluate:
- Is growth rate venture-scale (>20% MoM)?
- Is the market large enough ($100M+ TAM)?
- Does the product have network effects or moats?
- Would funding accelerate meaningfully, or is organic growth fine?

If venture: raise seed, hire, go fast.
If indie: stay lean, optimize margins, enjoy the lifestyle business.

---

## Decision Log

| Date | Decision | Reasoning |
|------|----------|-----------|
| 2025-07-22 | Open-core model | Builds trust, gets feedback, differentiates from "AI wrapper" crowd |
| 2025-07-22 | Validate before monetize | No evidence yet that strangers will pay; find PMF first |
| 2025-07-22 | Hosted demo as #1 priority | Remove all friction; if people won't try it free, they won't pay |

---

## Anti-Goals (things we deliberately won't do)

- ❌ Build more engine features before validating demand
- ❌ Raise money before proving people use this
- ❌ Build mobile app (web-responsive is enough)
- ❌ Compete on "number of agents" or "rounds" — compete on insight quality
- ❌ Build everything — ship the minimum that validates the next assumption
- ❌ Enterprise sales before self-serve revenue proves the value prop

---

## Success Metrics

| Phase | Metric | Target |
|-------|--------|--------|
| 0 | Demo live, e2e works without local setup | ✓/✗ |
| 1 | Users who complete a simulation | 50+ |
| 1 | Users who return within 7 days | 10+ |
| 1 | Users who say "I'd pay for this" in interview | 5+ |
| 2 | Monthly Recurring Revenue | $1,000 |
| 2 | Paying customers | 20+ |
| 3 | MRR | $10,000 |
| 3 | B2B contracts signed | 3+ |
