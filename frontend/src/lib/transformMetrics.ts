/**
 * Transforms raw metrics.json (backend format) into props for ResultsView.
 */
import type { SimulationResult, RoundSummary, AgentDecision, FactionUpdate, TriggersEvent, HistoricalPrecedent, AdversarialResult } from "../types";

interface MetricsRaw {
  scenario_name: string;
  verdict_label?: string;
  resilience_metrics?: any;
  crisis_event?: any;
  quantitative_metrics?: any;
  faction_metrics?: any;
  conditional_dynamics?: any;
  historical_context?: any;
  adversarial_result?: any;
  agents?: any[];
  rounds?: Record<string, any[]>;
  report_md?: string;
  timings?: any;
}

export interface ExampleData {
  result: SimulationResult;
  rounds: RoundSummary[];
  agentsByRound: Record<number, AgentDecision[]>;
  factionUpdates: FactionUpdate[];
  triggersEvents: TriggersEvent[];
  historicalPrecedents: HistoricalPrecedent[];
  adversarialResult: AdversarialResult | null;
}

export function transformMetrics(raw: MetricsRaw): ExampleData {
  // Build result object
  const result: SimulationResult = {
    scenario_name: raw.scenario_name,
    verdict: raw.resilience_metrics?.verdict,
    resilience_metrics: raw.resilience_metrics,
    crisis_event: raw.crisis_event,
    timings: raw.timings,
    report_md: raw.report_md,
    quantitative_metrics: raw.quantitative_metrics,
    faction_metrics: raw.faction_metrics,
    conditional_dynamics: raw.conditional_dynamics,
    historical_context: raw.historical_context,
    adversarial_result: raw.adversarial_result,
  };

  // Transform rounds: { r1: [...], r2: [...], r3: [...] } → RoundSummary[]
  const roundKeys = Object.keys(raw.rounds || {}).sort();
  const rounds: RoundSummary[] = [];
  const agentsByRound: Record<number, AgentDecision[]> = {};

  roundKeys.forEach((key, idx) => {
    const roundNum = idx + 1;
    const decisions: AgentDecision[] = (raw.rounds?.[key] || []).map((d: any) => ({
      id: d.id,
      archetype: d.archetype,
      action: d.action,
      utility: d.utility,
      utility_dimensions: d.utility_dimensions || {},
      reasoning_chain: d.reasoning_chain || [],
      emotional_state: d.emotional_state,
      new_state: d.new_state,
      monologue: d.monologue,
      statement: d.statement,
      confidence: d.confidence,
      duration: d.duration,
    }));

    // Compute vote tally
    const voteTally: Record<string, number> = {};
    decisions.forEach((d) => {
      voteTally[d.action] = (voteTally[d.action] || 0) + 1;
    });

    rounds.push({ round: roundNum, decisions, vote_tally: voteTally });
    agentsByRound[roundNum] = decisions;
  });

  // Faction updates from faction_metrics
  const factionUpdates: FactionUpdate[] = [];
  if (raw.faction_metrics?.snapshots) {
    for (const [roundStr, factions] of Object.entries(raw.faction_metrics.snapshots as Record<string, any>)) {
      factionUpdates.push({ round: parseInt(roundStr), factions: factions as any });
    }
  }

  // Triggers events — group by round
  const triggersEvents: TriggersEvent[] = [];
  if (raw.conditional_dynamics?.length) {
    const byRound: Record<number, { rule: string; effect: string; context: Record<string, any> }[]> = {};
    for (const d of raw.conditional_dynamics) {
      const r = d.round ?? 0;
      if (!byRound[r]) byRound[r] = [];
      byRound[r].push({ rule: d.rule_name || d.rule_id, effect: d.effect, context: d.context || {} });
    }
    for (const [round, triggers] of Object.entries(byRound)) {
      triggersEvents.push({ round: Number(round), triggers });
    }
  }

  // Historical precedents
  const historicalPrecedents: HistoricalPrecedent[] = raw.historical_context?.precedents || [];

  // Adversarial result
  const adversarialResult: AdversarialResult | null = raw.adversarial_result || null;

  return { result, rounds, agentsByRound, factionUpdates, triggersEvents, historicalPrecedents, adversarialResult };
}
