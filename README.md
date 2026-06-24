# SimulateAI

A domain-agnostic multi-agent swarm simulator. The user submits any concept — a product pitch, draft policy, hackathon idea, research question, or strategic decision — and an LLM-generated swarm of personas evaluates it across three rounds of debate, culminating in a diagnostic report.

This repository is Phase 1 (Local PoC) of the broader product roadmap described in `project-brief.md`.

## How it works

Every simulation runs in five stages:

1. **Architect.** A single LLM call analyzes the stimulus and produces a `SimulationSchema` that defines the entire vocabulary of the simulation: action verbs (e.g. `INVEST/PASS/COUNTER_OFFER` for a pitch review, `SUPPORT/OPPOSE/AMEND` for a policy debate), emotional states, resource model, linguistic clusters, macro-environmental anchors, and crisis dimensions. Nothing is hardcoded; vocabularies are derived per stimulus.
2. **Swarm generation.** A second LLM call designs N persona profiles aligned to the schema. A diversity heuristic rejects monoculture swarms and retries once.
3. **Round 1 — Initial perception.** Each agent independently evaluates the stimulus and commits to an action with a utility calculation.
4. **Round 2 — Directed debate.** Each agent is paired with an adversary via a ΔU-maximizing algorithm and must engage that opponent's stance directly.
5. **Round 3 — Crisis stress-test.** An external event (either stress-flavored or validation-flavored) is synthesized from the dominant Round 2 concern, and the swarm re-evaluates.

Finally, an Executive Compiler agent produces a Markdown diagnostic report with a deterministic resilience verdict (Fragile / Moderate / Resilient) computed from R2 → R3 decision stability, utility drift, and terminal-action share.

## Requirements

- Python 3.12 or later
- An LLM backend: either a Google AI Studio API key, or a running Ollama server with at least one chat-capable model pulled

## Installation

```bash
git clone <repo-url> SimulateAI
cd SimulateAI
python -m venv venv
source venv/bin/activate          # Linux/WSL
# .\venv\Scripts\Activate.ps1     # Windows PowerShell
pip install -r requirements.txt
```

## Configuration

Create `config.py` in the repository root:

```python
LLM_PROVIDER = "gemini"           # or "ollama"
OLLAMA_HOST = "http://localhost:11434"
GEMINI_API_KEY = "<your-key>"
GEMINI_MODEL = "gemma-4-26b-a4b-it"
DEFAULT_MODEL = GEMINI_MODEL if LLM_PROVIDER == "gemini" else "qwen2.5:3b"
REQUEST_TIMEOUT = 120.0
```

`config.py` is gitignored. Never commit your API key.

## Running the CLI

```bash
python main.py
```

The interactive cockpit offers two modes:

- **Sandbox chat** — a 1:1 streaming chat with the configured LLM, useful for sanity-checking the connection.
- **Swarm simulation** — the full Architect → Swarm → 3-round pipeline. You will be prompted for the stimulus text, the agent count, and the concurrency limit.

## Running scenarios non-interactively

Five pre-written stimuli covering different domains live in `tests/scenarios/`. Run any one of them, or all in sequence:

```bash
python tests/run_scenario.py 01                       # by prefix
python tests/run_scenario.py fintech                  # by name fragment
python tests/run_scenario.py --all                    # every scenario
python tests/run_scenario.py 02 --agents 5 --concurrency 3
```

Each run is saved to `tests/runs/<timestamp>__<scenario>/` with:

- `stimulus.txt` — the original prompt
- `report.md` — the Executive Diagnostic Report
- `metrics.json` — schema, decisions per round, adversary map, resilience metrics, timings
- `transcript.txt` and `transcript.html` — full Rich-rendered console output

When running multiple scenarios (`--all` or multiple matches), a `summary_<timestamp>.json` is also written to `tests/runs/` aggregating resilience verdicts and timings.

### Comparing batch runs

```bash
python tests/compare_runs.py tests/runs/summary_A.json tests/runs/summary_B.json
```

Prints a side-by-side table of resilience verdicts, stability scores, and total elapsed time — useful for tracking regressions after code changes.

`tests/runs/` is gitignored.

## Running the unit tests

```bash
python -m pytest tests/unit/
```

The test suite covers the deterministic helpers — JSON parsing, resilience metrics, adversary mapping, and swarm diversity — but does not exercise the LLM-driven path. End-to-end verification is done by running the scenarios above and inspecting the generated reports.

## Repository layout

```
main.py                     entry point (delegates to src.cli.menu)
config.py                   LLM provider configuration (gitignored)
requirements.txt
pytest.ini
project-brief.md            product vision and roadmap
CLAUDE.md                   architecture notes for AI assistants
src/
  agent/
    agent.py                single-agent LLM rounds (perceive, debate, crisis)
    adversary.py            ΔU pairing algorithm
    profile.py              AgentProfile, AgentAttributes, ResourceBalance
    swarm.py                LLM-driven persona generator
  cli/
    menu.py                 main menu and sandbox chat
    rendering.py            Rich panel and table helpers
    simulation.py           3-round orchestrator
  llm/
    client.py               UnifiedLLMClient (Gemini and Ollama)
    json_parse.py           robust JSON extraction and thought-tag stripping
  report/
    compiler.py             crisis synthesis and diagnostic report
  schema/
    architect.py            schema design LLM call
    simulation_schema.py    SimulationSchema dataclasses
tests/
  scenarios/                five .txt stimuli for non-interactive runs
  run_scenario.py           non-interactive scenario runner (writes batch summary JSON)
  compare_runs.py           side-by-side diff of two batch summaries
  unit/                     deterministic helper tests
```

## Operational notes

- **Concurrency.** Agent rounds run behind an `asyncio.Semaphore`. Worker tasks stagger their start times (`idx * 2`s for Round 1, `4 + idx * 3`s for Rounds 2 and 3) to keep the Gemini free tier within its per-minute quota.
- **Retry layer.** The LLM client retries on 429, 500, 502, 503, and 504 with exponential backoff (up to 5 attempts).
- **Failure modes.** If the Architect or swarm generator fails twice, the run aborts with a clear error. Per-agent round failures are tolerated; the agent is marked Failed in the live monitor and the pipeline continues with a synthesized fallback entry for that agent.

## Scope and limitations

This repository implements Phase 1 of the roadmap in `project-brief.md`. The following items are explicitly out of scope here:

- Persistent agent state across sessions (planned for Phase 2)
- Backtesting against historical scenarios (planned for Phase 2)
- Web-based Simulation Cockpit (planned for Phase 2)
- Scale beyond ~20 agents per run (planned for Phase 3)
- Prompt caching to reduce input token costs (planned for Phase 2)

See `project-brief.md` for the full roadmap.
