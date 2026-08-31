import { describe, expect, it } from "vitest";
import { transformMetrics } from "./transformMetrics";
import type { SimulationResult } from "../types";

const decision = (id: string, action: string, utility: number) => ({
  id,
  archetype: id === "a1" ? "operator" : "regulator",
  action,
  utility,
  utility_dimensions: { feasibility: utility },
  reasoning_chain: [],
  new_state: "Alert",
});

describe("transformMetrics", () => {
  it("hydrates canonical results including Round 4 and config", () => {
    const raw: SimulationResult = {
      version: "1.0",
      id: "run-1",
      stimulus: "Launch the product",
      config: { depth: "deep", agent_count: 2, mode: "collaborative" },
      scenario_name: "Product launch",
      schema: {
        scenario_name: "Product launch",
        evaluation_dimensions: ["feasibility"],
        actions: [{ name: "ADOPT", is_terminal: false }],
        state_vocabulary: ["Alert"],
      },
      rounds: {
        r1: [decision("a1", "ADOPT", 0.4), decision("a2", "REJECT", -0.2)],
        r4: [decision("a1", "ADOPT", 0.8), decision("a2", "ADOPT", 0.3)],
      },
      resilience_metrics: {
        verdict: "Resilient",
        decision_stability: 1,
        utility_drift_mean: 0.2,
      },
    };

    const hydrated = transformMetrics(raw);
    expect(hydrated.result.stimulus).toBe("Launch the product");
    expect(hydrated.result.config?.depth).toBe("deep");
    expect(hydrated.rounds.map((round) => round.round)).toEqual([1, 4]);
    expect(hydrated.agentsByRound[4]).toHaveLength(2);
    expect(hydrated.rounds[1].vote_tally).toEqual({ ADOPT: 2 });
  });

  it("hydrates adversarial, faction, trigger, and historical data", () => {
    const raw: SimulationResult = {
      scenario_name: "Policy",
      rounds: { r1: [decision("a1", "HOLD", 0.1)] },
      adversarial_result: {
        claims: [],
        survival_rate: 0.5,
        surviving_count: 1,
        defeated_count: 1,
        key_defeats: ["Unsupported demand claim"],
      },
      faction_metrics: {
        faction_history: [{ round: 1, factions: { HOLD: 1 } }],
        swing_agents: [],
        alliance_events: [],
        majority_stability: 1,
        faction_count_trajectory: [1],
      },
      conditional_dynamics: [
        { rule_id: "budget", rule_name: "Budget pressure", round: 1, effect: "Delay", context: {} },
      ],
      historical_context: {
        precedents: [{ title: "Prior rollout", summary: "A phased launch reduced risk." }],
      },
    };

    const hydrated = transformMetrics(raw);
    expect(hydrated.adversarialResult?.key_defeats).toEqual(["Unsupported demand claim"]);
    expect(hydrated.factionUpdates[0].factions.HOLD.size).toBe(1);
    expect(hydrated.triggersEvents[0].triggers[0].rule).toBe("Budget pressure");
    expect(hydrated.historicalPrecedents[0].title).toBe("Prior rollout");
  });

  it("normalizes legacy top-level actions without a schema", () => {
    const hydrated = transformMetrics({
      scenario_name: "Legacy run",
      actions: ["ADOPT", { name: "REJECT", is_terminal: true }],
      rounds: { r1: [decision("a1", "ADOPT", 0.2)] },
    } as SimulationResult & { actions: Array<string | { name: string; is_terminal: boolean }> });

    expect(hydrated.schema?.scenario_name).toBe("Legacy run");
    expect(hydrated.schema?.actions).toEqual([
      { name: "ADOPT", is_terminal: false },
      { name: "REJECT", is_terminal: true },
    ]);
  });
});
