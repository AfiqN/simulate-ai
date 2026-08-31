# Limitations

## Product scope

Portfolio v1 is a public-demo/single-instance release, not a production multi-tenant SaaS. It has no accounts, password recovery, OAuth, RBAC, billing, organization workspaces, or formal audit log. Access is capability-based: possession of an owner or share token grants its corresponding rights.

## Infrastructure

- Active jobs, cancellation state, webhook subscriptions, and WebSocket replay buffers are in memory.
- SQLite and filesystem bundles are local to one instance.
- Run exactly one Uvicorn worker and one replica.
- Restarted active runs are marked failed; they are not resumed.
- Horizontal scaling requires Redis or another durable queue/event stream, shared object storage, and a multi-instance database.
- Webhook delivery is bounded and tracked but is not a durable enterprise delivery queue or dead-letter system.

## Security and privacy

- WebSocket tokens appear in query strings due to browser API constraints; proxy logs must omit query strings.
- Browser BYOK keys use `sessionStorage`, which limits persistence but does not protect against XSS or a compromised browser extension.
- Legacy runs without capability hashes remain readable for backward compatibility. Remove or migrate them before storing sensitive scenarios.
- Default retention deletes application-managed terminal bundles after seven days, but cannot erase external backups, logs, exports, or copies.
- SSRF validation resolves webhook DNS before delivery, but a dedicated egress proxy/network policy provides stronger protection against DNS rebinding and infrastructure mistakes.
- The project has not received an independent security assessment.

## Simulation validity

Personas are generated abstractions, not real stakeholder samples. Outputs can inherit hallucinations, bias, missing context, and provider-specific behavior. RAG sources may be incomplete or incorrect. Deterministic metrics make classification logic inspectable; they do not make the underlying generated evidence factual or predictive.

Do not use SimulateAI as the sole basis for medical, legal, financial, safety-critical, employment, or public-policy decisions.

## Operational gaps before commercial production

A commercial deployment should add identity and authorization, centralized secrets, distributed workers, durable webhook delivery, PostgreSQL/object storage, backups and restore drills, observability and alerting, load/chaos tests, data governance, incident response, and independent security review.
