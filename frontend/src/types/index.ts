export interface CustomStakeholder {
  role: string;
  description: string;
  focus_areas?: string[];
  constraints?: string[];
}

export interface SimulationConfig {
  stimulus: string;
  agent_count: number;
  depth: "quick" | "standard" | "deep";
  mode?: "collaborative" | "adversarial";
  provider?: string;
  crisis_override?: string;
  custom_stakeholders?: CustomStakeholder[];
  historical_precedents?: HistoricalPrecedent[];
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
  faction_metrics?: FactionMetrics;
  conditional_dynamics?: { rule_id: string; rule_name: string; round: number; effect: string; context: Record<string, any> }[];
  historical_context?: { precedents: HistoricalPrecedent[] };
  adversarial_result?: AdversarialResult | null;
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

// --- Structured Output / Chart Data Types ---

export interface UtilityTrajectory {
  agent_id: string;
  archetype: string;
  is_custom: boolean;
  values: { round: number; utility: number; action: string }[];
}

export interface ChartData {
  utility_trajectories: UtilityTrajectory[];
  faction_pie: Record<string, Record<string, number>>;
  state_sankey: { from_round: string; to_round: string; from_state: string; to_state: string; count: number }[];
  dimension_heatmap: Record<string, { agent_id: string; archetype: string; dimensions: Record<string, number> }[]>;
}

export interface ComparisonResult {
  verdict: { run_a: string; run_b: string; changed: boolean };
  stability: {
    decision_stability: { run_a: number; run_b: number; delta: number };
    utility_drift_mean: { run_a: number; run_b: number; delta: number };
  };
  vote_tally: Record<string, Record<string, { run_a: number; run_b: number; delta: number }>>;
  dimension_stats: Record<string, Record<string, { run_a_mean: number; run_b_mean: number; delta: number }>>;
  timings: { run_a_total: number; run_b_total: number; delta: number };
  meta: { run_a_scenario: string; run_b_scenario: string; run_a_agents: number; run_b_agents: number };
}

export interface FactionSnapshot {
  size: number;
  cohesion: number;
}

export interface FactionUpdate {
  round: number;
  factions: Record<string, FactionSnapshot>;
}

export interface DefectionEvent {
  round: number;
  type: string;
  agent: string;
  from: string;
  to: string;
}

export interface FactionMetrics {
  faction_history: { round: number; factions: Record<string, number> }[];
  swing_agents: string[];
  alliance_events: DefectionEvent[];
  majority_stability: number;
  faction_count_trajectory: number[];
}

// --- Phase 3: Conditional Dynamics ---

export interface TriggerFired {
  rule: string;
  effect: string;
  context: Record<string, any>;
}

export interface TriggersEvent {
  round: number;
  triggers: TriggerFired[];
}

// --- Phase 3: Historical Context ---

export interface HistoricalPrecedent {
  title: string;
  year?: number | null;
  summary: string;
  outcome?: string;
  relevance?: string;
  domain?: string;
  source?: string;
}

// --- Phase 3: Webhooks ---

export interface Webhook {
  id: string;
  url: string;
  events: string[];
  secret?: string;
  active: boolean;
  created_at: string;
  failure_count: number;
}

// --- Adversarial Mode ---

export interface ArgumentClaimResult {
  agent_id: string;
  archetype: string;
  claim_text: string;
  evidence: string;
  status: "standing" | "defeated" | "amended";
  attack_text: string;
  attack_severity: string;
  defense_response: string;
  defense_text: string;
  amended_claim: string;
}

export interface AdversarialResult {
  claims: ArgumentClaimResult[];
  survival_rate: number;
  surviving_count: number;
  defeated_count: number;
  key_defeats: string[];
}
