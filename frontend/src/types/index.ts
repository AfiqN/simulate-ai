export interface SimulationConfig {
  stimulus: string;
  agent_count: number;
  depth: "quick" | "standard" | "deep";
  provider?: string;
  crisis_override?: string;
}

export interface AgentDecision {
  id: string;
  archetype: string;
  cluster_id?: string;
  action: string;
  utility: number;
  utility_dimensions: Record<string, number>;
  reasoning_chain: { dimension: string; score: number; reasoning: string }[];
  emotional_state?: string;
  new_state?: string;
  monologue?: string;
  statement?: string;
  confidence?: number;
  duration?: number;
}

export interface RoundSummary {
  round: number;
  decisions: AgentDecision[];
  vote_tally: Record<string, number>;
  consensus_index?: number;
}

export interface SwingEntry {
  id: string;
  archetype: string;
  from_action: string;
  to_action: string;
  driver_dimension: string;
  utility_delta?: number;
}

export interface SchemaData {
  scenario_name: string;
  evaluation_dimensions: string[];
  actions: { name: string; description?: string; is_terminal: boolean }[];
  state_vocabulary?: string[];
}

export interface SimulationResult {
  scenario_name?: string;
  verdict?: string;
  resilience_metrics?: {
    verdict: "Resilient" | "Moderate" | "Fragile" | "Indeterminate";
    decision_stability: number;
    utility_drift_mean: number;
    rationale?: string;
  };
  crisis_event?: { stress: string; validation: string | null } | string;
  timings?: { r1: number; r2: number; r3: number; total: number };
  report_md?: string;
  quantitative_metrics?: {
    vote_tally: Record<string, Record<string, number>>;
    dimension_stats: Record<string, Record<string, { mean: number; stdev: number; min: number; max: number }>>;
    state_transitions: Record<string, { shifted_count: number; total: number; top_shifts: any[] }>;
    swing_analysis: Record<string, SwingEntry[]>;
    consensus_index: Record<string, number>;
  };
}

export type PipelineStage = "schema" | "swarm" | "round1" | "round2" | "round3" | "round4" | "report";

export type SimStatus = "idle" | "running" | "schema_pending" | "complete" | "error";

export interface WSEvent {
  type: string;
  [key: string]: any;
}

export interface RunSummaryItem {
  id: string;
  scenario_name: string;
  status: string;
  verdict?: string;
  agent_count?: number;
  elapsed_s?: number;
  created_at: string;
}
