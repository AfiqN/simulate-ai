import type { SimulationConfig, RunSummaryItem } from "../types";

// When accessed via IP (WSL2 from Windows), call backend directly on port 8000.
// When accessed via localhost (same machine or proxy), use relative path.
const API_BASE = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1"
  ? ""
  : `http://${window.location.hostname}:8000`;

export async function startSimulation(config: SimulationConfig): Promise<{ id: string; status: string }> {
  const res = await fetch(`${API_BASE}/api/simulate`, {
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
  const res = await fetch(`${API_BASE}/api/simulate/${runId}/schema`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ approved }),
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
}

export async function getHistory(): Promise<{ runs: RunSummaryItem[]; total: number }> {
  const res = await fetch(`${API_BASE}/api/runs`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function getRunDetail(id: string): Promise<any> {
  const res = await fetch(`${API_BASE}/api/simulate/${id}`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}
