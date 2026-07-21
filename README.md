# SimulateAI

Multi-agent LLM simulation platform for stress-testing ideas. Submit any concept — a product pitch, draft policy, research question, or strategic decision — and an LLM-generated swarm of personas evaluates it across three rounds of structured debate, then produces a resilience analysis report.

This repository is Phase 1 (Local PoC) of the broader product roadmap described in `project-brief.md`.

## How it works

Every simulation runs in five stages:

1. **Architect.** A single LLM call analyzes the stimulus and produces a `SimulationSchema` defining the entire vocabulary: action verbs (e.g. `INVEST/PASS/COUNTER_OFFER` for a pitch, `SUPPORT/OPPOSE/AMEND` for a policy debate), emotional states, resource model, linguistic clusters, macro-environmental anchors, and crisis dimensions. Nothing is hardcoded.
2. **Swarm generation.** A second LLM call designs N persona profiles aligned to the schema. A diversity heuristic rejects monoculture swarms and retries once.
3. **Round 1 — Initial perception.** Each agent independently evaluates the stimulus and commits to an action with a utility score.
4. **Round 2 — Directed debate.** Each agent is paired with an adversary via a ΔU-maximizing algorithm and must engage that opponent's stance directly.
5. **Round 3 — Crisis stress-test.** An external shock is synthesized from the dominant Round 2 concern (or injected manually), and the swarm re-evaluates.

An Executive Compiler then produces a Markdown diagnostic report with a deterministic resilience verdict (Fragile / Moderate / Resilient) computed from R2→R3 decision stability, utility drift, and terminal-action share.

## Requirements

- Python 3.11 or later
- Node.js 20+ (for frontend builds only)
- An LLM backend: a Google AI Studio API key, an OpenAI-compatible API key, or a running Ollama server with at least one chat-capable model pulled

## Quick Start

```bash
git clone <repo-url> SimulateAI
cd SimulateAI
cp .env.example .env        # Fill in your API keys
pip install -r requirements.txt
python server.py            # Backend + frontend on http://localhost:8000
```

Or with Docker:

```bash
cp .env.example .env        # Fill in your API keys
docker compose up --build   # Everything on http://localhost:8000
```

## Configuration

Copy `.env.example` to `.env` and set your values:

```bash
# LLM Provider: "ollama", "gemini", or "openai"
LLM_PROVIDER=openai

# Only the keys for your chosen provider are required:
GEMINI_API_KEY=             # for gemini
OPENAI_API_KEY=             # for openai
OPENAI_BASE_URL=https://api.openai.com/v1
OLLAMA_HOST=http://localhost:11434  # for ollama

# Optional
MAX_CONCURRENCY=5
RAG_ENABLED=true
BRAVE_API_KEY=              # Brave Search for RAG enrichment
```

`config.py` reads these via `os.getenv()` with sensible defaults. You can also set env vars directly without a `.env` file.

## Running the interactive CLI

```bash
source /mnt/g/WSL/venv/bin/activate && python main.py   # WSL
# or
python main.py
```

Two modes are available:

- **Sandbox chat** — 1:1 streaming chat with the configured LLM, useful for sanity-checking the connection.
- **Swarm simulation** — the full Architect → Swarm → 3-round pipeline. You will be prompted for the stimulus text, agent count, and concurrency limit.

## Running scenarios non-interactively

Pre-written stimuli live in `tests/scenarios/`. Run any one of them, or all in sequence:

```bash
# Run by prefix or name fragment
python tests/run_scenario.py 01
python tests/run_scenario.py fintech

# Run every scenario sequentially
python tests/run_scenario.py --all

# Override agent count and concurrency
python tests/run_scenario.py 02 --agents 5 --concurrency 3

# Run 2 scenarios concurrently
python tests/run_scenario.py --all --parallel 2

# Inject a custom crisis event for Round 3
python tests/run_scenario.py 04 --crisis "A massive data breach occurs"

# Override provider and model
python tests/run_scenario.py 01 --provider openai --model gpt-4o
python tests/run_scenario.py 01 --provider ollama --model qwen2.5:3b
```

### CLI flags

| Flag | Default | Description |
|---|---|---|
| `scenario` | — | Name fragment, numeric prefix, or path to a `.txt` file |
| `--all` | false | Run every scenario in `tests/scenarios/` |
| `--agents N` | 5 | Agent count per scenario |
| `--concurrency N` | 2 | Max simultaneous LLM calls |
| `--parallel N` | 1 | Run N scenarios concurrently (each gets its own client) |
| `--provider` | config default | `gemini`, `openai`, or `ollama` |
| `--model MODEL` | config default | Model name passed to the provider |
| `--crisis TEXT` | auto-generated | Custom crisis event injected into Round 3 |

### Run output

Each run is saved to `tests/runs/<timestamp>__<scenario>/`:

- `stimulus.txt` — the original prompt
- `report.md` — the Executive Diagnostic Report
- `metrics.json` — schema, decisions per round, adversary map, resilience metrics, timings
- `transcript.txt` / `transcript.html` — full Rich-rendered console output
- `bundle/` — self-contained shareable export (`manifest.json`, `simulation.json`, `report.md`)

When running multiple scenarios, a `summary_<timestamp>.json` is also written to `tests/runs/` aggregating verdicts and timings.

### Comparing batch runs

```bash
python tests/compare_runs.py tests/runs/summary_A.json tests/runs/summary_B.json
```

Prints a side-by-side table of resilience verdicts, stability scores, and elapsed time — useful for tracking regressions after code changes.

`tests/runs/` is gitignored.

## API server

The REST API lets you run simulations programmatically and query historical results. It persists run metadata to a SQLite database at `data/simulate.db`.

```bash
python server.py                   # Start on port 8000
python server.py --port 9000       # Custom port
python server.py --reload          # Auto-reload for development
```

### Endpoints

**GET /api/health** — Health check. Returns provider and model info.

**POST /api/simulate** — Start a new simulation. Returns immediately with a run ID.

```json
{
  "stimulus": "A fintech startup pitching micro-investment accounts to Indonesian regulators",
  "agent_count": 5,
  "concurrency": 2,
  "provider": "gemini",
  "model": "gemma-4-26b-a4b-it",
  "crisis_override": "A sudden regulatory freeze on all new fintech licenses"
}
```

All fields except `stimulus` are optional.

**GET /api/simulate/{id}** — Poll run status. Returns `status` (`queued` | `running` | `completed` | `failed`), `verdict`, `elapsed_s`, and the full result payload once complete.

**GET /api/runs** — List historical runs from the database, newest first.

Query params: `limit` (default 50), `offset` (default 0), `verdict` (filter by Fragile / Moderate / Resilient).

**GET /api/runs/{id}** — Full metrics JSON for a specific historical run (reads from `metrics.json` on disk).

## Running the unit tests

```bash
python -m pytest tests/unit/ -v
```

Covers deterministic helpers — JSON parsing, resilience metrics, adversary mapping, and swarm diversity. The LLM-driven path is verified by running scenarios and inspecting generated reports.

## Repository layout

```
main.py                     entry point (delegates to src.cli.menu)
server.py                   API server entry point (FastAPI + uvicorn)
config.py                   LLM provider configuration (gitignored)
requirements.txt
pytest.ini
project-brief.md            product vision and roadmap
CLAUDE.md                   architecture notes for AI assistants
data/
  simulate.db               SQLite run index (auto-created by server)
src/
  agent/
    agent.py                single-agent LLM rounds (perceive, debate, crisis)
    adversary.py            ΔU pairing algorithm
    profile.py              AgentProfile, AgentAttributes, ResourceBalance
    swarm.py                LLM-driven persona generator
  api/
    app.py                  FastAPI app factory and lifespan (DB init)
    routes.py               /api/simulate and /api/runs route handlers
    models.py               Pydantic request/response models
    queue.py                In-memory job queue for async simulation runs
  cli/
    menu.py                 main menu and sandbox chat
    rendering.py            Rich panel and table helpers
    simulation.py           3-round orchestrator
  export/
    bundle.py               Self-contained run bundle writer (manifest + full data)
  llm/
    client.py               UnifiedLLMClient (Gemini, OpenAI, Ollama)
    json_parse.py           Robust JSON extraction and thought-tag stripping
  persistence/
    db.py                   SQLite async helpers (aiosqlite)
  report/
    compiler.py             Crisis synthesis and diagnostic report
  schema/
    architect.py            Schema design LLM call
    simulation_schema.py    SimulationSchema dataclasses
tests/
  scenarios/                .txt stimuli for non-interactive runs
  run_scenario.py           Non-interactive runner (writes bundle + batch summary)
  compare_runs.py           Side-by-side diff of two batch summaries
  unit/                     Deterministic helper tests
```

## Supported providers

| Provider | How to configure |
|---|---|
| **Gemini** (Google AI Studio) | Set `LLM_PROVIDER=gemini` and `GEMINI_API_KEY` in `.env`. Uses the OpenAI-compatible endpoint at `generativelanguage.googleapis.com`. |
| **OpenAI** | Set `LLM_PROVIDER=openai` and provide `OPENAI_API_KEY` + `OPENAI_BASE_URL` in `.env`. |
| **Ollama** (local) | Set `LLM_PROVIDER=ollama` and `OLLAMA_HOST` in `.env`. Default model: `qwen2.5:3b`. |

Provider and model can also be overridden per-run via `--provider` / `--model` on the CLI, or via the `provider` / `model` fields in the API request body.

## Operational notes

- **Concurrency.** Agent rounds run behind an `asyncio.Semaphore`. Worker tasks stagger start times (`idx * 2`s for Round 1, `4 + idx * 3`s for Rounds 2–3) to stay within the Gemini free-tier per-minute quota.
- **Retry layer.** The LLM client retries on 429, 500, 502, 503, and 504 with exponential backoff (up to 5 attempts).
- **Failure modes.** If the Architect or swarm generator fails twice, the run aborts with a clear error. Per-agent round failures are tolerated — the agent is marked Failed in the live monitor and the pipeline continues with a synthesized fallback entry.

## Scope

This project has reached the end of Phase 1 (Local PoC with Web UI). The following are possible extensions:

- Persistent agent state across sessions
- Backtesting against historical scenarios
- Scale beyond ~20 agents per run
- Prompt caching to reduce input token costs

See `project-brief.md` for the full roadmap.
