import type { SimulationConfig, RunSummaryItem } from "../types";
import { getStoredSettings } from "../components/layout/SettingsPanel";

// Always use relative paths — Vite dev server proxies /api to the backend.
// In production, backend serves the static dist so relative paths work too.
const API_BASE = "";

function buildHeaders(): Record<string, string> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const settings = getStoredSettings();
  if (settings?.apiKey) {
    headers["X-API-Key"] = settings.apiKey;
  }
  return headers;
}

export async function startSimulation(config: SimulationConfig): Promise<{ id: string; status: string }> {
  const settings = getStoredSettings();
  const res = await fetch(`${API_BASE}/api/simulate`, {
    method: "POST",
    headers: buildHeaders(),
    body: JSON.stringify({
      stimulus: config.stimulus,
      agent_count: config.agent_count,
      depth: config.depth,
      mode: config.mode || "collaborative",
      provider: settings?.provider || config.provider || undefined,
      model: settings?.model || undefined,
      crisis_override: config.crisis_override || undefined,
      custom_stakeholders: config.custom_stakeholders?.length ? config.custom_stakeholders : undefined,
      historical_precedents: config.historical_precedents?.length ? config.historical_precedents : undefined,
      concurrency: 2,
    }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => null);
    throw new Error(data?.detail || `API error: ${res.status}`);
  }
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

export async function cancelSimulation(id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/simulate/${id}/cancel`, { method: "POST" });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
}

export async function exportRun(id: string): Promise<any> {
  const res = await fetch(`${API_BASE}/api/runs/${id}/export`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function compareRuns(runA: string, runB: string): Promise<any> {
  const res = await fetch(`${API_BASE}/api/compare?run_a=${encodeURIComponent(runA)}&run_b=${encodeURIComponent(runB)}`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}
