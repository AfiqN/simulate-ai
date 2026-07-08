import { useReducer, useEffect } from "react";
import type {
  AgentDecision,
  FactionUpdate,
  PipelineStage,
  RoundSummary,
  SchemaData,
  SimStatus,
  SimulationResult,
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

    case "LOAD_RESULT":
      return { ...initialState, status: "complete", result: action.result };

    case "RESET":
      return initialState;

    default:
      return state;
  }
}

export function useSimulation() {
  const [state, dispatch] = useReducer(reducer, initialState);
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
