<div align="center">

<img src="frontend/public/logo-mark.svg" alt="SimulateAI" width="64" />

# SimulateAI

**Stress-test decisions with structured multi-agent debate.**

[![CI](https://github.com/AfiqN/simulate-ai/actions/workflows/ci.yml/badge.svg)](https://github.com/AfiqN/simulate-ai/actions/workflows/ci.yml)
[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.11](https://img.shields.io/badge/python-3.11-3776AB.svg)](https://python.org)
[![React 19](https://img.shields.io/badge/react-19-61DAFB.svg)](https://react.dev)

[Live Demo](https://simulate-ai-production.up.railway.app) · [Methodology](docs/methodology.md) · [Architecture](docs/architecture.md) · [Limitations](docs/limitations.md)

</div>

![SimulateAI landing page](docs/screenshot-landing.png)

## What it does

SimulateAI turns a decision, proposal, or policy into a schema-first simulation. Diverse AI personas independently assess it, debate opposing positions, react to a generated crisis, and—at deep depth—attempt reconciliation. The application then presents coalition changes, utility drift, failure modes, and a resilience verdict.

The verdict is **not chosen freely by an LLM**. It is computed from deterministic thresholds over simulation outputs; the LLM writes the accompanying narrative. Results are decision-support artifacts, not forecasts or professional advice.

## Pipeline

```text
Stimulus → Dynamic schema → Persona swarm → Structured rounds
         → Deterministic metrics → Narrative report → Canonical snapshot
```

- **Quick:** initial assessment plus crisis stress test.
- **Standard:** perception, debate, and crisis.
- **Deep:** Standard plus reconciliation and minority analysis.
- **Adversarial mode:** extracts claims, challenges evidence, and records which claims survive.

See [Methodology](docs/methodology.md) for metric definitions and [Architecture](docs/architecture.md) for component boundaries.

## Portfolio v1 capabilities

- React 19 + TypeScript SPA with live WebSocket progress.
- FastAPI async orchestration with Gemini, OpenAI-compatible, and Ollama providers.
- Canonical, versioned result used by live completion, reload, history, export, and shared views.
- Private-by-default runs using hashed owner capability tokens.
- Revocable read-only share links; shared viewers cannot cancel, approve, ask follow-ups, or create new shares.
- Sequenced WebSocket replay with polling/snapshot recovery.
- SQLite-backed daily quota: 3 demo runs or 30 BYOK runs per identity by default.
- API keys retained only while a job is active; browser BYOK settings use tab-scoped `sessionStorage`.
- Webhooks disabled by default and protected by admin authentication, HTTPS/public-network validation, HMAC signing, and redirect blocking when enabled.
- Retention cleanup, readiness/liveness checks, graceful shutdown, CI, and reproducible multi-stage Docker build.

## Quick start

### Docker (recommended)

```bash
git clone https://github.com/AfiqN/simulate-ai.git
cd simulate-ai
cp .env.example .env
# Set one provider and its key in .env, or use Ollama.
docker compose up --build
```

Open <http://localhost:8000>. Docker builds the frontend from source and runs one non-root API worker. The one-worker constraint is intentional: active jobs and WebSocket replay buffers are in memory in Portfolio v1.

### Local development

Requirements: Python 3.11+, Node.js 22+, and one supported LLM provider.

```bash
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows: .venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env
python server.py --reload
```

In a second terminal:

```bash
cd frontend
npm ci
npm run dev
```

The Vite development server runs at <http://localhost:5173> and proxies API/WebSocket traffic to port 8000.

## Configuration

| Variable | Default | Purpose |
|---|---:|---|
| `LLM_PROVIDER` | `openai` | `openai`, `gemini`, or `ollama` |
| `OPENAI_MODEL` | `gpt-4o` | OpenAI-compatible model |
| `OPENAI_BASE_URL` | OpenAI API | Optional compatible gateway |
| `GEMINI_MODEL` | `gemma-4-26b-a4b-it` | Gemini model |
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama endpoint |
| `REQUEST_TIMEOUT` | `120` | Provider request timeout in seconds |
| `MAX_CONCURRENCY` | `5` | Per-run LLM concurrency ceiling |
| `RAG_ENABLED` | `true` | Enable web-search enrichment when configured |
| `ADMIN_API_KEY` | empty | Required for administrative run index/webhook management |
| `RATE_LIMIT_SALT` | local-dev value | Set a random secret in public deployments |
| `TRUST_PROXY_HEADERS` | `false` | Trust forwarded client IP only behind a controlled proxy |
| `WEBHOOKS_ENABLED` | `false` | Enable webhook management and delivery |
| `RUN_RETENTION_DAYS` | `7` | Terminal run retention |
| `JOB_RETENTION_SECONDS` | `900` | In-memory terminal job retention |

Never commit `.env`. Set a strong `RATE_LIMIT_SALT` and `ADMIN_API_KEY` for a public deployment.

## Access model

`POST /api/simulate` returns a run ID and a random owner token. Only the token hash is stored server-side. Owner operations accept `Authorization: Bearer <token>` or `X-Run-Token`; read-only shared views use a separately generated `share` token.

Browser WebSockets cannot send custom headers, so the capability is sent in the WebSocket query string. Configure reverse proxies not to log query strings. This model is appropriate for a portfolio demo, but it is not a replacement for accounts, sessions, and RBAC in a multi-tenant product.

Useful endpoints:

| Endpoint | Access |
|---|---|
| `POST /api/simulate` | Public, quota-limited |
| `GET /api/simulate/{id}` | Owner or active share token |
| `POST /api/simulate/{id}/cancel` | Owner |
| `POST /api/simulate/{id}/schema` | Owner |
| `POST/DELETE /api/runs/{id}/share` | Owner |
| `POST /api/runs/{id}/ask` | Owner |
| `GET /api/runs/{id}/export` | Owner or active share token |
| `GET /api/runs` | Admin |
| `GET /api/health` | Public liveness |
| `GET /api/readiness` | Public local-dependency readiness |

Interactive OpenAPI documentation is available at `/docs`.

## Quality gates

```bash
# Backend
ruff check config.py server.py src
pytest tests/unit -q
python -m compileall -q config.py server.py src tests

# Frontend
cd frontend
npm run lint
npm run test
npm run typecheck
npm run build
npm audit --audit-level=moderate
```

Current local checkpoint: **355 backend tests** and **3 frontend regression tests** passing. GitHub Actions repeats backend, frontend, and container-readiness checks from a clean checkout.

## Deployment scope

Portfolio v1 is designed for a **single application instance with one worker**, SQLite, and local persistent storage. It is suitable for a portfolio/public demo with documented constraints. It is not yet a horizontally scalable or multi-tenant SaaS. Read [Limitations](docs/limitations.md) before exposing it to real workloads.

## Security and contributing

Report vulnerabilities using [SECURITY.md](SECURITY.md). Development workflow is in [CONTRIBUTING.md](CONTRIBUTING.md). Planned work is tracked in [ROADMAP.md](ROADMAP.md).

## License

[MIT](LICENSE) © AfiqN
