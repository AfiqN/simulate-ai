import { useReducer, useEffect } from "react";
import type {
  AdversarialResult,
  AgentDecision,
  FactionUpdate,
  HistoricalPrecedent,
  PipelineStage,
  RoundSummary,
  SchemaData,
  SimStatus,
  SimulationResult,
  TriggersEvent,
  WSEvent,
} from "../types";

export interface SimState {
  status: SimStatus;
  runId: string | null;
  currentStage: PipelineStage | null;
  progress: number;
  schema: SchemaData | null;
  schemaPending: boolean;
  agents: { id: string; archetype: string; cluster_id: string }[];
  rounds: RoundSummary[];
  agentsByRound: Record<number, AgentDecision[]>;
  factionUpdates: FactionUpdate[];
  triggersEvents: TriggersEvent[];
  historicalPrecedents: HistoricalPrecedent[];
  adversarialResult: AdversarialResult | null;
  stressEvent: string | null;
  validationEvent: string | null;
  result: SimulationResult | null;
  error: string | null;
}

export type SimAction =
  | { type: "START"; runId: string }
  | { type: "WS_EVENT"; event: WSEvent }
  | { type: "SCHEMA_APPROVED" }
  | { type: "LOAD_RESULT"; result: SimulationResult }
  | { type: "RESET" };

const initialState: SimState = {
  status: "idle",
  runId: null,
  currentStage: null,
  progress: 0,
  schema: null,
  schemaPending: false,
  agents: [],
  rounds: [],
  agentsByRound: {},
  factionUpdates: [],
  triggersEvents: [],
  historicalPrecedents: [],
  adversarialResult: null,
  stressEvent: null,
  validationEvent: null,
  result: null,
  error: null,
};

function reducer(state: SimState, action: SimAction): SimState {
  switch (action.type) {
    case "START":
      return { ...initialState, status: "running", runId: action.runId };

    case "WS_EVENT": {
      const ev = action.event;
      switch (ev.type) {
        case "stage":
          return { ...state, currentStage: ev.stage, progress: ev.progress ?? state.progress };
        case "schema_ready":
          return { ...state, schema: ev.data };
        case "schema_pending":
          return { ...state, status: "schema_pending", schema: ev.schema, schemaPending: true };
        case "schema_approved":
          return { ...state, status: "running", schemaPending: false };
        case "swarm_ready":
          return { ...state, agents: ev.agents };
        case "agent_done": {
          const round = ev.round as number;
          const prev = state.agentsByRound[round] || [];
          return {
            ...state,
            agentsByRound: { ...state.agentsByRound, [round]: [...prev, ev.data] },
          };
        }
        case "round_summary": {
          const rs: RoundSummary = { ...ev.data, round: ev.round };
          return { ...state, rounds: [...state.rounds, rs] };
        }
        case "crisis":
          return { ...state, stressEvent: ev.stress_event ?? ev.event ?? null, validationEvent: ev.validation_event ?? null };
        case "faction_update": {
          const fu: FactionUpdate = { round: ev.round, factions: ev.data };
          return { ...state, factionUpdates: [...state.factionUpdates, fu] };
        }
        case "triggers_fired": {
          const te: TriggersEvent = { round: ev.round, triggers: ev.triggers };
          return { ...state, triggersEvents: [...state.triggersEvents, te] };
        }
        case "historical_context":
          return { ...state, historicalPrecedents: ev.precedents || [] };
        case "adversarial_result":
          return {
            ...state,
            adversarialResult: {
              claims: ev.claims || [],
              survival_rate: ev.survival_rate ?? 0,
              surviving_count: ev.surviving_count ?? 0,
              defeated_count: ev.defeated_count ?? 0,
              key_defeats: ev.key_defeats || [],
            },
          };
        case "complete":
          return { ...state, status: "complete", result: ev.result, progress: 100 };
        case "error":
          return { ...state, status: "error", error: ev.message };
        default:
          return state;
      }
    }

    case "SCHEMA_APPROVED":
      return { ...state, schemaPending: false, status: "running" };

    case "LOAD_RESULT": {
      // Hydrate dynamics data from persisted result
      const triggersEvents: TriggersEvent[] = [];
      if (action.result.conditional_dynamics) {
        const byRound: Record<number, TriggersEvent["triggers"]> = {};
        for (const d of action.result.conditional_dynamics) {
          const r = d.round ?? 0;
          if (!byRound[r]) byRound[r] = [];
          byRound[r].push({ rule: d.rule_name, effect: d.effect, context: d.context });
        }
        for (const [round, triggers] of Object.entries(byRound)) {
          triggersEvents.push({ round: Number(round), triggers });
        }
      }
      const historicalPrecedents: HistoricalPrecedent[] =
        action.result.historical_context?.precedents ?? [];
      // Hydrate adversarial result if present
      const adversarialResult: AdversarialResult | null =
        action.result.adversarial_result
          ? {
              claims: action.result.adversarial_result.claims,
              survival_rate: action.result.adversarial_result.survival_rate,
              surviving_count: action.result.adversarial_result.surviving_count,
              defeated_count: action.result.adversarial_result.defeated_count,
              key_defeats: action.result.adversarial_result.key_defeats,
            }
          : null;
      return { ...initialState, status: "complete", result: action.result, triggersEvents, historicalPrecedents, adversarialResult };
    }

    case "RESET":
      return initialState;

    default:
      return state;
  }
}

const STORAGE_KEY = "simulate-ai-active-run";

interface PersistedRun {
  runId: string;
  startedAt: number;
  depth?: string;
}

function persistRun(run: PersistedRun) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(run));
  } catch {}
}

function clearPersistedRun() {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch {}
}

export function getPersistedRun(): PersistedRun | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    // Expire after 15 minutes (simulation can't take longer)
    if (Date.now() - parsed.startedAt > 15 * 60 * 1000) {
      clearPersistedRun();
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
}

export function useSimulation() {
  const [state, dispatch] = useReducer(reducer, initialState);

  // Persist run to localStorage on start, clear on completion/error/reset
  useEffect(() => {
    if (state.status === "running" && state.runId) {
      persistRun({ runId: state.runId, startedAt: Date.now() });
    } else if (state.status === "complete" || state.status === "error" || state.status === "idle") {
      clearPersistedRun();
    }
  }, [state.status, state.runId]);

  return { state, dispatch };
}

export function useSimulationEvents(
  dispatch: React.Dispatch<SimAction>,
  events: WSEvent[]
) {
  useEffect(() => {
    if (events.length === 0) return;
    const latest = events[events.length - 1];
    dispatch({ type: "WS_EVENT", event: latest });
  }, [events, dispatch]);
}
