# Frontend Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the minimal vanilla HTML frontend with a professional React dashboard providing real-time simulation observability via WebSocket, metric visualizations, and run history.

**Architecture:** Monorepo — Vite builds to `static/dist/`, FastAPI serves it. Dev mode proxies `/api` and `/ws` to FastAPI on `:8000`. WebSocket event bus in backend pushes structured events as each pipeline stage completes.

**Tech Stack:** React 19, TypeScript 5.7, Vite 6, Tailwind CSS 4, Recharts 2.15, react-markdown 9, Lucide React 0.460

## Global Constraints

- No custom CSS files — Tailwind utility classes only
- No state management library — `useReducer` + context
- No router library — conditional rendering based on view state
- Font stack: Inter (Google Fonts CDN) for UI, JetBrains Mono for data/numbers
- 6px border-radius, 1px borders, no shadows
- Lucide icons only where functionally needed
- All number displays use `font-mono` with tabular figures
- Maximum content width: 960px centered
- 4px base spacing unit, 16px component padding, 24px section gaps
- Colors: bg #FAFAFA, cards #FFFFFF, borders #E5E5E5, text #0F0F0F/#6B6B6B/#9B9B9B
- Semantic: positive #16653A, negative #8B1A1A, neutral #6B5C1A, shift #2563EB
- Verdict: resilient #16653A/#ECFDF5, moderate #6B5C1A/#FEFCE8, fragile #8B1A1A/#FEF2F2

---

## Task 1: Frontend Scaffold

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tsconfig.json`
- Create: `frontend/index.html`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/index.css`

**Interfaces:**
- Consumes: nothing (standalone scaffold)
- Produces: working Vite dev server at `:5173` proxying to FastAPI at `:8000`

**Steps:**

- [ ] Create `frontend/package.json`
- [ ] Create `frontend/vite.config.ts` (proxy /api and /ws to :8000, build to ../static/dist)
- [ ] Create `frontend/tsconfig.json`
- [ ] Create `frontend/index.html` (Inter + JetBrains Mono via Google Fonts)
- [ ] Create `frontend/src/index.css` (Tailwind import)
- [ ] Create `frontend/src/main.tsx` (React root)
- [ ] Create `frontend/src/App.tsx` (header + placeholder)
- [ ] Run `cd frontend && npm install && npm run dev` — verify renders at localhost:5173

---

## Task 2: WebSocket Backend

**Files:**
- Create: `src/api/websocket.py`
- Modify: `src/api/routes.py` (add WS route)
- Modify: `src/api/queue.py` (emit events via bus)
- Modify: `src/cli/simulation.py` (add `event_callback` param)

**Interfaces:**
- Consumes: `run_simulation_pipeline()` stage events
- Produces: WebSocket endpoint at `/ws/simulate/{run_id}` sending JSON event stream

**Steps:**

- [ ] Create `src/api/websocket.py` with `SimulationEventBus` class (emit, subscribe, unsubscribe)
- [ ] Add WebSocket route to `src/api/routes.py`: accept connection, subscribe to event bus, send events as JSON, close on complete/error
- [ ] Add `event_callback: Optional[Callable]` parameter to `run_simulation_pipeline()` in `src/cli/simulation.py`
- [ ] Insert `_emit()` calls at each stage: schema start/ready, swarm start/ready, round1/2/3 start, agent_done per agent, round_summary, crisis, report start, complete
- [ ] Modify `src/api/queue.py` `_execute_simulation()` to pass event_callback that calls `event_bus.emit(run_id, event)`, emit complete/error at end
- [ ] Verify: start FastAPI, connect wscat to ws://localhost:8000/ws/simulate/{id}, trigger simulation, confirm events stream

---

## Task 3: Types + Hooks + SimForm + PipelineProgress

**Files:**
- Create: `frontend/src/types/index.ts`
- Create: `frontend/src/lib/api.ts`
- Create: `frontend/src/hooks/useWebSocket.ts`
- Create: `frontend/src/hooks/useSimulation.ts`
- Create: `frontend/src/components/simulation/SimForm.tsx`
- Create: `frontend/src/components/simulation/PipelineProgress.tsx`
- Modify: `frontend/src/App.tsx`

**Interfaces:**
- Consumes: REST POST `/api/simulate`, WebSocket `/ws/simulate/{run_id}`
- Produces: `SimulationState` via useSimulation hook; rendered form and pipeline progress

**Steps:**

- [ ] Create `frontend/src/types/index.ts` — SimulationConfig, AgentDecision, RoundSummary, SwingEntry, SchemaData, SimulationResult, PipelineStage, SimStatus, WSEvent, RunSummaryItem
- [ ] Create `frontend/src/lib/api.ts` — startSimulation(), getHistory(), getRunDetail()
- [ ] Create `frontend/src/hooks/useWebSocket.ts` — connect to WS, auto-reconnect with backoff, return {events, status}
- [ ] Create `frontend/src/hooks/useSimulation.ts` — useReducer state machine: idle→running→complete/error. Process WS events into structured state (schema, agents, rounds, agentsByRound, crisisEvent, result)
- [ ] Create `frontend/src/components/simulation/SimForm.tsx` — textarea + agents input + depth select + submit button
- [ ] Create `frontend/src/components/simulation/PipelineProgress.tsx` — 6 connected dots (Schema/Swarm/R1/R2/R3/Report), active=pulsing, complete=solid, pending=hollow. Progress bar below.
- [ ] Wire into App.tsx: submit triggers startSimulation → connect WS → pipeline animates
- [ ] Verify: submit form, see pipeline progress update in real-time as simulation runs

---

## Task 4: AgentCard + RoundTimeline

**Files:**
- Create: `frontend/src/components/common/Badge.tsx`
- Create: `frontend/src/components/simulation/AgentCard.tsx`
- Create: `frontend/src/components/simulation/RoundTimeline.tsx`
- Modify: `frontend/src/App.tsx`

**Interfaces:**
- Consumes: `agentsByRound` and `rounds` from useSimulation state
- Produces: agent cards grid, round timeline table

**Steps:**

- [ ] Create `frontend/src/components/common/Badge.tsx` — colored pill component (variant: positive/negative/neutral/shift)
- [ ] Create `frontend/src/components/simulation/AgentCard.tsx`:
  - Compact: archetype name, cluster badge, action Badge (color by semantic), utility number (mono)
  - Expanded (click): dimension horizontal bars, reasoning chain bullets, emotional state
  - Animate in: opacity 0→1 + translateY 4px→0, 200ms
- [ ] Create `frontend/src/components/simulation/RoundTimeline.tsx`:
  - Tab switcher: R1 | R2 | R3
  - Table: Agent | Action | Utility | State | Key Reasoning
  - Rows highlighted with left border (#2563EB) if action flipped from prev round
  - Delta arrows on utility
- [ ] Wire into App.tsx below PipelineProgress
- [ ] Verify: run simulation, cards appear as agent_done events arrive, tabs switch between rounds

---

## Task 5: Metrics Dashboard

**Files:**
- Create: `frontend/src/components/metrics/VoteTally.tsx`
- Create: `frontend/src/components/metrics/ConsensusGauge.tsx`
- Create: `frontend/src/components/metrics/DimensionChart.tsx`
- Create: `frontend/src/components/metrics/SwingTable.tsx`
- Modify: `frontend/src/App.tsx`

**Interfaces:**
- Consumes: `result.metrics` from useSimulation state (after complete)
- Produces: 4-panel metrics grid

**Steps:**

- [ ] Create `VoteTally.tsx` — Recharts stacked horizontal BarChart, one bar per round, segments colored by action semantic category
- [ ] Create `ConsensusGauge.tsx` — large HHI number + label (Fragmented < 0.4, Converging 0.4-0.7, Aligned > 0.7). Show R1→R2→R3 with arrows.
- [ ] Create `DimensionChart.tsx` — Recharts grouped vertical BarChart. X=dimensions, grouped by round. Y=mean [-1,1].
- [ ] Create `SwingTable.tsx` — table: Agent | Round | From→To | Driver Dimension. Sorted by round, then magnitude.
- [ ] Wire all 4 into a 2x2 grid section below RoundTimeline
- [ ] Verify: after simulation completes, all 4 panels render with correct data

---

## Task 6: Report + History + Production Build

**Files:**
- Create: `frontend/src/components/simulation/ReportSection.tsx`
- Create: `frontend/src/components/layout/Header.tsx`
- Create: `frontend/src/components/layout/HistoryList.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `src/api/app.py` (serve static/dist + SPA fallback)

**Interfaces:**
- Consumes: `result` from useSimulation, GET `/api/runs`, GET `/api/runs/{id}`
- Produces: complete rendered report, history navigation, production-ready build

**Steps:**

- [ ] Create `ReportSection.tsx` — verdict badge (big colored pill), stability + drift (mono), crisis event line, rendered markdown (react-markdown), collapsible raw JSON
- [ ] Create `Header.tsx` — "SimulateAI" title left, "History" toggle right
- [ ] Create `HistoryList.tsx` — fetch /api/runs, list past runs (scenario, verdict badge, elapsed). Click → dispatch LOAD_RESULT with full detail from /api/runs/{id}
- [ ] Update `frontend/src/App.tsx` — conditional view: idle/running shows sim view, history toggle shows history list, LOAD_RESULT shows completed result view
- [ ] Modify `src/api/app.py`:
  - Mount `static/dist` if directory exists
  - SPA fallback: serve `static/dist/index.html` for non-API, non-static routes
- [ ] Run `cd frontend && npm run build` — verify output in static/dist/
- [ ] Start FastAPI only (no Vite), open localhost:8000 — full app works from static build
- [ ] Commit

---

## Execution Order

Tasks 1 and 2 can run in parallel (frontend scaffold + backend WS are independent).
Tasks 3-6 are sequential — each builds on the previous.

```
Task 1 (Frontend Scaffold) ─┐
                             ├─→ Task 3 → Task 4 → Task 5 → Task 6
Task 2 (WebSocket Backend) ─┘
```
