# Security Policy

## Supported version

Security fixes target the current `master` branch and the latest Portfolio v1 release.

## Reporting a vulnerability

Do not open a public issue containing an exploit, credential, private run token, or user data. Use GitHub's private vulnerability reporting feature for this repository. Include the affected endpoint/component, impact, reproduction steps, and a minimal proof of concept. Please allow reasonable time for triage before public disclosure.

## Deployment responsibilities

Before public deployment:

- Use HTTPS end to end.
- Set strong, unique values for `ADMIN_API_KEY` and `RATE_LIMIT_SALT`.
- Keep `TRUST_PROXY_HEADERS=false` unless requests pass through a controlled proxy that overwrites forwarding headers.
- Keep `WEBHOOKS_ENABLED=false` unless webhook delivery is required.
- Configure proxy/access logs to omit query strings because browser WebSocket capability tokens are passed in the URL.
- Protect `.env`, SQLite data, run bundles, backups, and logs.
- Run exactly one application worker for Portfolio v1.
- Keep dependencies and the base container image patched.

## Security model

New runs are private by default. A random owner capability token is returned once and only its SHA-256 hash is persisted. A separate revocable token grants read-only sharing. Capability possession grants access; there is no account recovery, user identity, RBAC, or audit trail in v1.

Provider API keys submitted through the UI are stored in tab-scoped browser `sessionStorage`, sent per request over HTTPS, held in memory only while the job is active, and cleared at terminal state. Browser storage still depends on the page remaining free from XSS. Server operators may configure provider keys through environment variables.

Webhook targets are restricted to HTTPS hosts resolving to public addresses, redirects are disabled, and management requires the admin key. DNS validation reduces SSRF risk but does not provide the network isolation of a dedicated egress proxy.

## Known boundaries

- SQLite, filesystem bundles, job state, and replay buffers are designed for one instance.
- Legacy database rows created before capability tokens may remain readable for compatibility; migrate or delete them before handling sensitive material.
- Simulation output can contain sensitive text supplied by users. Retention defaults to seven days but operators remain responsible for backups and copies outside the application.
- This project has not undergone an independent penetration test or compliance audit.
