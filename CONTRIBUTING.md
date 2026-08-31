# Contributing

## Setup

Use Python 3.11 and Node.js 22.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cd frontend && npm ci
```

Copy `.env.example` to `.env`; never commit credentials or private run data.

## Before opening a pull request

Run the same checks as CI:

```bash
ruff check config.py server.py src
pytest tests/unit -q
python -m compileall -q config.py server.py src tests

cd frontend
npm run lint
npm run test
npm run typecheck
npm run build
npm audit --audit-level=moderate
```

For packaging changes, also run `docker build -t simulateai:local .` and verify `/api/readiness` from the container.

## Design constraints

- Keep deterministic metrics authoritative; LLM narrative must not override the verdict.
- Keep API credentials out of persistence, URLs, logs, reports, and completed jobs.
- Preserve owner/share capability boundaries.
- New result fields belong in the versioned canonical serializer and must hydrate consistently for live, reload, history, export, and share paths.
- Portfolio v1 remains single-instance unless a change also replaces in-memory jobs/replay and SQLite assumptions.
- Add regression tests for behavioral fixes.

Use focused commits and do not commit generated run bundles, databases, `.env`, or `node_modules`.
