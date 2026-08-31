import type {
  SimulationResult,
  RoundSummary,
  AgentDecision,
  FactionUpdate,
  TriggersEvent,
  HistoricalPrecedent,
  AdversarialResult,
  SchemaData,
} from "../types";

interface MetricsRaw extends SimulationResult {
  verdict_label?: string;
  agents?: any[];
  actions?: Array<string | { name: string; description?: string; is_terminal: boolean }>;
}

export interface ExampleData {
  result: SimulationResult;
  schema: SchemaData | null;
  rounds: RoundSummary[];
  agentsByRound: Record<number, AgentDecision[]>;
  factionUpdates: FactionUpdate[];
  triggersEvents: TriggersEvent[];
  historicalPrecedents: HistoricalPrecedent[];
  adversarialResult: AdversarialResult | null;
}

function normalizeDecision(d: any): AgentDecision {
  return {
    id: String(d.id || ""),
    archetype: String(d.archetype || "Unknown agent"),
    action: String(d.action || "UNKNOWN"),
    utility: Number(d.utility || 0),
    utility_dimensions: d.utility_dimensions || {},
    reasoning_chain: d.reasoning_chain || [],
    emotional_state: d.emotional_state,
    new_state: d.new_state,
    monologue: d.monologue,
    statement: d.statement,
    confidence: d.confidence,
    duration: d.duration,
  };
}

/** Normalize canonical and legacy backend payloads into one UI model. */
export function transformMetrics(raw: MetricsRaw): ExampleData {
  const result: SimulationResult = {
    ...raw,
    verdict: raw.resilience_metrics?.verdict || raw.verdict,
  };

  const schema: SchemaData | null = raw.schema
    ? {
        scenario_name: raw.schema.scenario_name || raw.scenario_name || "Simulation",
        evaluation_dimensions: raw.schema.evaluation_dimensions || [],
        actions: (raw.schema.actions || []).map((a: any) =>
          typeof a === "string" ? { name: a, is_terminal: false } : a
        ),
        state_vocabulary: raw.schema.state_vocabulary || [],
      }
    : raw.actions
    ? {
        scenario_name: raw.scenario_name || "Simulation",
        evaluation_dimensions: [],
        actions: (raw.actions as any[]).map((a: any) =>
          typeof a === "string" ? { name: a, is_terminal: false } : a
        ),
      }
    : null;

  const roundEntries = Object.entries(raw.rounds || {})
    .filter(([, values]) => Array.isArray(values) && values.length > 0)
    .sort(([a], [b]) => Number(a.replace(/\D/g, "")) - Number(b.replace(/\D/g, "")));
  const rounds: RoundSummary[] = [];
  const agentsByRound: Record<number, AgentDecision[]> = {};

  roundEntries.forEach(([key, values], index) => {
    const parsed = Number(key.replace(/\D/g, ""));
    const roundNum = Number.isFinite(parsed) && parsed > 0 ? parsed : index + 1;
    const decisions = (values as any[]).map(normalizeDecision);
    const voteTally: Record<string, number> = {};
    decisions.forEach((decision) => {
      voteTally[decision.action] = (voteTally[decision.action] || 0) + 1;
    });
    rounds.push({
      round: roundNum,
      decisions,
      vote_tally: voteTally,
      consensus_index: raw.quantitative_metrics?.consensus_index?.[`r${roundNum}`],
    });
    agentsByRound[roundNum] = decisions;
  });

  const factionUpdates: FactionUpdate[] = [];
  const factionHistory = raw.faction_metrics?.faction_history || [];
  for (const entry of factionHistory) {
    const snapshots: Record<string, { size: number; cohesion: number }> = {};
    for (const [action, value] of Object.entries(entry.factions || {})) {
      snapshots[action] = typeof value === "number"
        ? { size: value, cohesion: 0 }
        : (value as { size: number; cohesion: number });
    }
    factionUpdates.push({ round: Number(entry.round), factions: snapshots });
  }
  const legacySnapshots = (raw.faction_metrics as any)?.snapshots;
  if (factionUpdates.length === 0 && legacySnapshots) {
    for (const [round, factions] of Object.entries(legacySnapshots)) {
      factionUpdates.push({ round: Number(round), factions: factions as any });
    }
  }

  const triggersEvents: TriggersEvent[] = [];
  if (raw.conditional_dynamics?.length) {
    const byRound: Record<number, TriggersEvent["triggers"]> = {};
    for (const item of raw.conditional_dynamics) {
      const round = item.round ?? 0;
      if (!byRound[round]) byRound[round] = [];
      byRound[round].push({
        rule: item.rule_name || item.rule_id,
        effect: item.effect,
        context: item.context || {},
      });
    }
    for (const [round, triggers] of Object.entries(byRound)) {
      triggersEvents.push({ round: Number(round), triggers });
    }
  }

  return {
    result,
    schema,
    rounds,
    agentsByRound,
    factionUpdates,
    triggersEvents,
    historicalPrecedents: raw.historical_context?.precedents || [],
    adversarialResult: raw.adversarial_result || null,
  };
}
