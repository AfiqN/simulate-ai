# Architecture

## System overview

```text
React 19 SPA
  ├─ REST: create, snapshot, owner actions, share/export
  └─ WebSocket: sequenced progress + bounded replay
                 │
FastAPI single process / one worker
  ├─ capability access checks
  ├─ SQLite quota and run metadata
  ├─ in-memory active job registry and event buffers
  └─ async simulation pipeline
       ├─ schema architect
       ├─ optional RAG enrichment
       ├─ persona swarm
       ├─ structured rounds
       ├─ deterministic metric compiler
       └─ narrative report compiler
                 │
Filesystem canonical bundle + SQLite index
```

## Canonical result

`src/export/serialization.py` defines the versioned result boundary. Completion events, persisted `result.json`, reload/history responses, export, curated examples, and shared views use the same shape. Legacy `metrics.json` data is normalized as a compatibility fallback.

The snapshot includes stimulus and configuration, schema, rounds, resilience and quantitative metrics, faction/conditional dynamics, historical context, adversarial output, crisis event, report, and timings. Keeping a single contract prevents live UI and reloaded UI from presenting different evidence.

## Access control

Each new run receives a high-entropy owner capability token. The server persists only its SHA-256 hash and compares tokens in constant time. Owner access permits mutation and cost-bearing actions. The owner can create or revoke a distinct read-only share token.

REST tokens use headers. Browser WebSocket connections use a query parameter because the WebSocket API cannot set arbitrary headers. Deployment proxies must suppress query-string logging.

## Event recovery

The event bus assigns a monotonically increasing sequence per run and keeps a bounded replay window. A reconnecting browser sends its latest sequence, drops duplicates, and receives missed events. Periodic status polling supplies an authoritative snapshot if replay history is unavailable. Terminal states are `complete`, `error`, and `cancelled`.

## Persistence and lifecycle

SQLite stores run metadata, capability hashes, share state, and privacy-preserving usage events. Canonical result bundles are written below `tests/runs/`. Startup marks interrupted queued/running rows failed. Periodic maintenance removes expired terminal jobs, event buffers, quota events, safe filesystem bundles, and their database rows.

Shutdown order is deliberate: stop maintenance, cancel/wait for simulation jobs, finish webhook delivery, then close SQLite. Provider and RAG HTTP clients are closed on success, failure, cancellation, and early exit. Per-request API keys are removed from job memory at terminal state.

## Public-demo safeguards

The create endpoint uses a SQLite-backed daily quota. BYOK raises the quota but never bypasses abuse protection. Forwarded client IP headers are trusted only when explicitly enabled. Webhooks are disabled by default; when enabled, management is admin-only and targets must resolve to public HTTPS destinations without redirects.

## Deployment topology

Portfolio v1 intentionally runs one Uvicorn worker. Active jobs and replay buffers are process-local, while SQLite and filesystem persistence are local-volume oriented. Multiple workers or replicas would split job/event state and are unsupported. A scalable version requires a shared queue, distributed event stream, durable object storage, and a database designed for concurrent instances.
