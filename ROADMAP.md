# SimulateAI Roadmap

## Portfolio v1 — implemented

- Canonical, versioned simulation result across live completion, reload, history, export, and share.
- Private-by-default owner capabilities and revocable read-only sharing.
- Sequenced WebSocket replay, polling snapshot recovery, and explicit schema-approval modes.
- Durable SQLite quota with separate demo/BYOK limits.
- Webhook feature flag, admin management, HMAC signing, HTTPS/public-network validation, and tracked shutdown.
- Credential/resource cleanup, retention maintenance, readiness/liveness endpoints, and sanitized provider failures.
- React 19 frontend quality gates, backend unit suite, Ruff runtime lint, GitHub Actions, and multi-stage non-root Docker image.
- Architecture, methodology, security, and limitations documentation.

## Next: public-demo validation

- Run the clean container smoke test in CI and on the target hosting platform.
- Exercise run → reload → history → share → revoke in a real browser/incognito session.
- Add Playwright smoke coverage with a fake provider so end-to-end tests never spend API quota.
- Add structured request/run logging and basic uptime/error monitoring without logging capabilities or user stimuli.
- Collect user feedback; improve onboarding only after observing real friction.
- Clean React Hooks warnings and expand frontend reducer/API tests.
- Migrate or remove pre-v1 legacy runs that have no capability hashes.

## Later: multi-tenant product

These are deliberately outside Portfolio v1:

- OAuth/accounts, organizations, RBAC, account recovery, and audit logs.
- PostgreSQL, object storage, Redis/durable queue, and distributed event delivery.
- Multi-replica deployment, resumable jobs, idempotent workers, and durable webhook retries/dead letters.
- Billing, tier enforcement, API-key management, team workspaces, and product analytics.
- Backup/restore automation, SLOs, alerting, load/chaos testing, and formal security review.
- Stronger reproducibility experiments and confidence intervals from repeated independent runs.

## Release principle

Do not add large simulation features before the current decision-support flow is validated with real users. Correctness, evidence quality, recovery, privacy, and honest limitations take priority over agent count or feature breadth.
