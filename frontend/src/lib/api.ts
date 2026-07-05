import type { SimulationConfig, RunSummaryItem } from "../types";

export async function startSimulation(config: SimulationConfig): Promise<{ id: string; status: string }> {
  const res = await fetch("/api/simulate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      stimulus: config.stimulus,
      agent_count: config.agent_count,
      depth: config.depth,
      provider: config.provider || undefined,
      crisis_override: config.crisis_override || undefined,
      concurrency: 2,
    }),
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function approveSchema(runId: string, approved: boolean = true): Promise<void> {
  const res = await fetch(`/api/simulate/${runId}/schema`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ approved }),
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
}

export async function getHistory(): Promise<{ runs: RunSummaryItem[]; total: number }> {
  const res = await fetch("/api/runs");
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function getRunDetail(id: string): Promise<any> {
  const res = await fetch(`/api/simulate/${id}`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}
