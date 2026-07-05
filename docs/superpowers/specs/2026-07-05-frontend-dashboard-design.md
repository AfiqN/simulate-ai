# SimulateAI Frontend Dashboard — Design Spec

## Overview

Full rebuild of the SimulateAI frontend as a professional, data-focused dashboard. Replaces the current minimal vanilla HTML with a React (Vite) single-page application that provides real-time simulation observability via WebSocket.

**Key decisions:**
- Framework: React 19 + Vite + TypeScript + Tailwind CSS 4
- Communication: WebSocket for real-time progress, REST for submit + history
- Visual direction: Minimalist, instrument-grade. No decorations without function.
- Interaction: View-only (observe simulation). Interactive controls reserved for Phase 2.
- Deployment: Monorepo — Vite builds to `static/dist/`, FastAPI serves it.

---

## Architecture

```
frontend/                    ← Vite + React + TypeScript
├── src/
│   ├── components/
│   │   ├── layout/          Header, PageShell
│   │   ├── simulation/      SimForm, PipelineProgress, AgentCard, RoundTimeline
│   │   ├── metrics/         VoteTally, ConsensusGauge, SwingTable, DimensionChart
│   │   └── common/          Badge, ProgressBar, Tooltip, Card
│   ├── hooks/
│   │   ├── useWebSocket.ts  WS connection + reconnect logic
│   │   └── useSimulation.ts Simulation state machine (useReducer)
│   ├── pages/
│   │   ├── Dashboard.tsx    New simulation + history
│   │   └── RunDetail.tsx    Full result view for completed run
│   ├── types/               TypeScript interfaces matching API models
│   ├── lib/                 API client, formatters, constants
│   └── App.tsx
├── index.html
├── vite.config.ts
├── tailwind.config.ts
├── tsconfig.json
└── package.json
```

### Data Flow

```
Browser  <--WebSocket-->  FastAPI  <-->  Simulation Pipeline
          (real-time)

Browser  --REST POST-->   /api/simulate     (start run)
Browser  --REST GET-->    /api/runs         (history)
Browser  --REST GET-->    /api/runs/{id}    (full result)
```

### Serving Strategy

- **Dev:** Vite dev server on `:5173`, proxy `/api` and `/ws` to FastAPI on `:8000`
- **Production:** `vite build` → `static/dist/` → FastAPI mounts as static + SPA fallback

---

## Page Layout

Single page, vertical scroll. Sections appear progressively as data arrives.

```
┌─────────────────────────────────────────────────────────────┐
│  SimulateAI                                    History →     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  STIMULUS INPUT                                             │
│  [textarea]                                                 │
│  Agents: [5]    Depth: [standard]    [Run Simulation]       │
│                                                             │
│  PIPELINE                                                   │
│  Schema ● ─── Swarm ● ─── R1 ◐ ─── R2 ○ ─── R3 ○ ─── Report ○  │
│  [████████████░░░░░░░░░░░░░░░░] 35%                        │
│                                                             │
│  AGENTS                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                  │
│  │ Agent 1  │  │ Agent 2  │  │ Agent 3  │                  │
│  │ INVEST   │  │ PASS     │  │ COUNTER  │                  │
│  │ u: 0.45  │  │ u:-0.30  │  │ u: 0.12  │                  │
│  └──────────┘  └──────────┘  └──────────┘                  │
│                                                             │
│  ROUNDS                                                     │
│  [R1] [R2] [R3]                                             │
│  Agent  │ Action  │ Utility │ State      │ Driver           │
│  ────────┼─────────┼─────────┼────────────┼──────────       │
│  VC      │ INVEST  │ +0.45   │ Optimistic │ financial       │
│  Analyst │ PASS  ↓ │ -0.30   │ Skeptical  │ regulatory      │
│                                                             │
│  METRICS                                                    │
│  Vote Tally    │ Consensus  │ Dimensions    │ Swings        │
│  [stacked bar] │ [number]   │ [grouped bar] │ [table]       │
│                                                             │
│  REPORT                                                     │
│  Verdict: RESILIENT                                         │
│  [rendered markdown]                                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### State Machine

1. **Idle** — Form active. History list visible at bottom.
2. **Running** — Form disabled. Pipeline animates. Cards stream in per-agent per-round.
3. **Complete** — Full result: agents, timeline, metrics, report all visible.

---

## Visual Design

### Typography

| Role | Font | Weight | Size |
|------|------|--------|------|
| Page title | Inter | 500 | 20px |
| Section titles | Inter | 500 | 15px |
| Body | Inter | 400 | 14px |
| Labels | Inter | 400 | 11px |
| Data/numbers | JetBrains Mono | 400 | 13px |

Letter-spacing: -0.02em on headings. Tabular figures enabled on all numbers.

### Color System

```
Background:     #FAFAFA (page), #FFFFFF (cards)
Text:           #0F0F0F (primary), #6B6B6B (secondary), #9B9B9B (tertiary)
Border:         #E5E5E5 (default), #D0D0D0 (active)
Accent:         #1A1A1A (buttons, active states)

Semantic:
  Positive:     #16653A (non-terminal positive actions)
  Negative:     #8B1A1A (terminal actions)
  Neutral:      #6B5C1A (middle-ground actions)
  Shift:        #2563EB (agent flipped between rounds)

Verdict:
  Resilient:    text #16653A, background #ECFDF5
  Moderate:     text #6B5C1A, background #FEFCE8
  Fragile:      text #8B1A1A, background #FEF2F2
```

### Spacing

4px base unit. Component padding: 16px. Section gaps: 24px. Maximum content width: 960px centered.

### Surface Treatment

- Cards: 1px solid #E5E5E5 border, 6px border-radius, no shadow
- Active card: 2px left border in accent color
- No gradients, no glows, no blur effects

### Motion

- Pipeline stage activation: opacity transition 300ms
- Card arrival: opacity 0→1 + translateY 4px→0, 200ms ease-out
- Progress bar: width transition 300ms linear
- No spring physics, no stagger, no bounce

### Icons

Lucide React. Used for: expand/collapse (ChevronDown), status (Circle/CircleDot), trend (TrendingUp/TrendingDown/Minus). No decorative icons.

---

## Components

### PipelineProgress

Six stages as connected dots: Schema, Swarm, R1, R2, R3, Report.

- Completed: solid filled dot
- Active: pulsing dot (CSS animation, not JS)
- Pending: hollow ring
- Percentage bar beneath (each stage = ~16.6%)
- Stage labels below dots in 11px tertiary text

### AgentCard

Compact during run (action + utility only). Expands on click after completion.

**Compact state:**
- Archetype name (13px, bold)
- Cluster badge (11px, muted background pill)
- Action badge (color-coded by semantic category)
- Aggregate utility (monospace, signed number)

**Expanded state:**
- Utility dimensions: horizontal bars, each labeled with dimension name + score
- Reasoning chain: bulleted list — dimension, score, one-line reasoning
- Emotional state label
- Memory snippet (if present)

### RoundTimeline

Tab switcher: R1 | R2 | R3 (highlighted active tab with bottom border).

Table columns: Agent | Action | Utility | State | Key Reasoning (truncated)

Visual cues:
- Rows where action changed from previous round: left border in Shift blue (#2563EB)
- Utility shows delta arrow (up/down) from previous round
- State changes shown as "Previous → Current"

### VoteTally

Stacked horizontal bar chart, one bar per round. Each segment colored by action semantic category. Labels show count. Renders using Recharts `<BarChart>` with horizontal layout.

### ConsensusGauge

Single large number (HHI value, 0-1) with qualitative label:
- < 0.4: "Fragmented" (tertiary text)
- 0.4-0.7: "Converging" (neutral text)
- > 0.7: "Aligned" (positive text)

Shows per-round values: R1 → R2 → R3 with directional arrows.

### DimensionChart

Grouped bar chart (Recharts). X-axis: evaluation dimensions. Grouped by round (R1/R2/R3). Y-axis: mean score [-1, 1]. Error bars showing stdev.

### SwingTable

Table: Agent | Round | From → To | Driver Dimension | Delta

Sorted by round, then by magnitude of utility shift. Driver dimension highlighted.

### Report Section

- Verdict as large badge (background-tinted pill, semantic color)
- Stability + drift numbers beside verdict (monospace)
- Crisis event in single-line label below
- Rendered markdown body (react-markdown, no custom styling beyond base typography)
- Collapsible "Raw Metrics" section (pre-formatted JSON)

---

## WebSocket Protocol

### Connection

`ws://localhost:8000/ws/simulate/{run_id}`

Opened immediately after POST `/api/simulate` returns `run_id`.

### Server → Client Events

```typescript
// Pipeline stage changes
{ type: "stage", stage: "schema" | "swarm" | "round1" | "round2" | "round3" | "report", progress: number }

// Schema designed (provides context for upcoming agents)
{ type: "schema_ready", data: { scenario_name: string, evaluation_dimensions: string[], actions: {name: string, is_terminal: boolean}[] } }

// Swarm generated (agent roster before round starts)
{ type: "swarm_ready", agents: { id: string, archetype: string, cluster_id: string }[] }

// Individual agent completes a round
{ type: "agent_done", round: number, data: AgentDecision }

// All agents done for a round (includes computed summary)
{ type: "round_summary", round: number, data: RoundSummary }

// Crisis event generated (between R2 and R3)
{ type: "crisis", event: string }

// Simulation finished
{ type: "complete", result: SimulationResult }

// Error
{ type: "error", message: string }
```

### Client → Server Events (Phase 2, reserved)

```typescript
{ type: "pause" }
{ type: "resume" }
{ type: "inject_crisis", event: string }
```

### Reconnection

Exponential backoff: 1s, 2s, 4s, max 10s. On reconnect, server replays a state snapshot so the client can rebuild current progress without re-running the simulation.

---

## Data Types

```typescript
interface SimulationConfig {
  stimulus: string;
  agent_count: number;
  depth: "quick" | "standard" | "deep";
  provider?: string;
  crisis_override?: string;
}

interface AgentDecision {
  id: string;
  archetype: string;
  cluster_id: string;
  action: string;
  utility: number;
  utility_dimensions: Record<string, number>;
  reasoning_chain: { dimension: string; score: number; reasoning: string }[];
  emotional_state: string;
  confidence?: number;
}

interface RoundSummary {
  round: number;
  decisions: AgentDecision[];
  vote_tally: Record<string, number>;
  consensus_index: number;
}

interface SwingEntry {
  id: string;
  archetype: string;
  from_action: string;
  to_action: string;
  driver_dimension: string;
}

interface SimulationResult {
  schema: {
    scenario_name: string;
    evaluation_dimensions: string[];
    actions: { name: string; is_terminal: boolean }[];
    state_vocabulary: string[];
  };
  rounds: RoundSummary[];
  crisis_event: string;
  metrics: {
    vote_tally: Record<string, Record<string, number>>;
    dimension_stats: Record<string, Record<string, { mean: number; stdev: number; min: number; max: number }>>;
    state_transitions: Record<string, { shifted_count: number; total: number; top_shifts: any[] }>;
    swing_analysis: Record<string, SwingEntry[]>;
    consensus_index: Record<string, number>;
    net_confidence: Record<string, number>;
  };
  resilience: {
    verdict: "Resilient" | "Moderate" | "Fragile" | "Indeterminate";
    decision_stability: number;
    utility_drift_mean: number;
  };
  report_md: string;
  elapsed_s: number;
}
```

---

## Dependencies

```json
{
  "dependencies": {
    "react": "^19.0",
    "react-dom": "^19.0",
    "recharts": "^2.15",
    "react-markdown": "^9.0",
    "lucide-react": "^0.460"
  },
  "devDependencies": {
    "vite": "^6.0",
    "@vitejs/plugin-react": "^4.4",
    "typescript": "^5.7",
    "tailwindcss": "^4.0",
    "@tailwindcss/vite": "^4.0",
    "@types/react": "^19.0",
    "@types/react-dom": "^19.0"
  }
}
```

No state management library. `useReducer` + context for simulation state.
No router library. Conditional rendering based on view state (dashboard vs detail).

---

## Backend Changes Required

1. **WebSocket endpoint** — `ws://localhost:8000/ws/simulate/{run_id}`
   - FastAPI WebSocket route that subscribes to simulation progress events
   - Simulation pipeline emits events to an in-memory channel (asyncio.Queue per run)
   - WebSocket handler reads from channel and sends JSON to client

2. **Simulation pipeline instrumentation**
   - Add event emission at each stage boundary and per-agent completion
   - Wrap existing pipeline functions to emit progress without changing their logic

3. **Static file serving update**
   - Mount `static/dist/` for built frontend assets
   - SPA fallback: serve `index.html` for any non-API, non-static route

4. **CORS (dev only)** — allow `:5173` during Vite dev server usage

---

## Implementation Phases

**Phase A: Scaffold + Pipeline Progress**
- Vite project setup, Tailwind, TypeScript config
- FastAPI WebSocket endpoint (basic stage events)
- PipelineProgress component connected to real WS
- SimForm submitting to existing REST API

**Phase B: Agent Cards + Rounds**
- WebSocket emitting per-agent results
- AgentCard component (compact + expanded)
- RoundTimeline with tab switching
- Flip highlighting

**Phase C: Metrics Dashboard**
- VoteTally (Recharts stacked bar)
- ConsensusGauge
- DimensionChart (grouped bar with error bars)
- SwingTable

**Phase D: Report + Polish**
- Verdict badge, rendered markdown report
- History list with click-to-view
- RunDetail page loading from REST
- Responsive layout adjustments
- Production build integration

---

## Non-Goals

- Dark mode (future consideration)
- Authentication / multi-user
- Mobile-optimized layout (responsive but desktop-primary)
- Mid-simulation interaction (Phase 2 scope)
- PDF export
- Animated chart transitions beyond basic fade
