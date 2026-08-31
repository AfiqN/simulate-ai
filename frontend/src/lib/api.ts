import type { SimulationConfig, RunSummaryItem, SimulationResult } from "../types";
import { getStoredSettings } from "../components/layout/SettingsPanel";

const TOKEN_STORAGE_KEY = "simulateai_run_tokens";

function tokenMap(): Record<string, string> {
  try { return JSON.parse(localStorage.getItem(TOKEN_STORAGE_KEY) || "{}"); }
  catch { return {}; }
}

export function saveRunToken(runId: string, token: string): void {
  const tokens = tokenMap();
  tokens[runId] = token;
  localStorage.setItem(TOKEN_STORAGE_KEY, JSON.stringify(tokens));
}

export function getRunToken(runId: string): string | null {
  return tokenMap()[runId] || null;
}

export function removeRunToken(runId: string): void {
  const tokens = tokenMap();
  delete tokens[runId];
  localStorage.setItem(TOKEN_STORAGE_KEY, JSON.stringify(tokens));
}

export function getShareToken(): string | null {
  return new URLSearchParams(window.location.search).get("share");
}

function requestHeaders(runId?: string, includeApiKey = false): Record<string, string> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (runId) {
    const token = getRunToken(runId);
    if (token) headers.Authorization = `Bearer ${token}`;
  }
  if (includeApiKey) {
    const apiKey = getStoredSettings()?.apiKey;
    if (apiKey) headers["X-API-Key"] = apiKey;
  }
  return headers;
}

function withShare(url: string): string {
  const share = getShareToken();
  if (!share) return url;
  const separator = url.includes("?") ? "&" : "?";
  return `${url}${separator}share=${encodeURIComponent(share)}`;
}

async function parseError(res: Response): Promise<never> {
  const data = await res.json().catch(() => null);
  throw new Error(data?.message || data?.detail || `API error: ${res.status}`);
}

export async function startSimulation(config: SimulationConfig): Promise<{ id: string; status: string; access_token: string }> {
  const settings = getStoredSettings();
  const res = await fetch("/api/simulate", {
    method: "POST",
    headers: requestHeaders(undefined, true),
    body: JSON.stringify({
      stimulus: config.stimulus,
      agent_count: config.agent_count,
      depth: config.depth,
      mode: config.mode || "collaborative",
      schema_approval: "auto",
      provider: settings?.provider || config.provider || undefined,
      model: settings?.model || undefined,
      crisis_override: config.crisis_override || undefined,
      custom_stakeholders: config.custom_stakeholders?.length ? config.custom_stakeholders : undefined,
      historical_precedents: config.historical_precedents?.length ? config.historical_precedents : undefined,
      concurrency: 2,
    }),
  });
  if (!res.ok) return parseError(res);
  const data = await res.json();
  saveRunToken(data.id, data.access_token);
  return data;
}

export async function approveSchema(runId: string, approved = true): Promise<void> {
  const res = await fetch(`/api/simulate/${runId}/schema`, {
    method: "POST", headers: requestHeaders(runId), body: JSON.stringify({ approved }),
  });
  if (!res.ok) return parseError(res);
}

export async function getHistory(): Promise<{ runs: RunSummaryItem[]; total: number }> {
  // Server history is administrative; browser-owned history lives in lib/history.
  return { runs: [], total: 0 };
}

export async function getRunDetail(id: string): Promise<any> {
  const res = await fetch(withShare(`/api/simulate/${id}`), { headers: requestHeaders(id) });
  if (!res.ok) return parseError(res);
  return res.json();
}

export async function getCanonicalRun(id: string): Promise<SimulationResult> {
  const res = await fetch(withShare(`/api/runs/${id}`), { headers: requestHeaders(id) });
  if (!res.ok) return parseError(res);
  return res.json();
}

export async function cancelSimulation(id: string): Promise<void> {
  const res = await fetch(`/api/simulate/${id}/cancel`, { method: "POST", headers: requestHeaders(id) });
  if (!res.ok) return parseError(res);
}

export async function createShare(id: string): Promise<string> {
  const res = await fetch(`/api/runs/${id}/share`, { method: "POST", headers: requestHeaders(id) });
  if (!res.ok) return parseError(res);
  const data = await res.json();
  return `${window.location.origin}/run/${id}?share=${encodeURIComponent(data.share_token)}`;
}

export async function revokeShare(id: string): Promise<void> {
  const res = await fetch(`/api/runs/${id}/share`, { method: "DELETE", headers: requestHeaders(id) });
  if (!res.ok) return parseError(res);
}

export async function exportRun(id: string): Promise<any> {
  const res = await fetch(withShare(`/api/runs/${id}/export`), { headers: requestHeaders(id) });
  if (!res.ok) return parseError(res);
  return res.json();
}

export async function compareRuns(runA: string, runB: string): Promise<any> {
  const res = await fetch(`/api/compare?run_a=${encodeURIComponent(runA)}&run_b=${encodeURIComponent(runB)}`, {
    headers: {
      "X-Run-A-Token": getRunToken(runA) || "",
      "X-Run-B-Token": getRunToken(runB) || "",
    },
  });
  if (!res.ok) return parseError(res);
  return res.json();
}

export async function askRun(id: string, question: string, contextMd: string): Promise<string> {
  const res = await fetch(`/api/runs/${id}/ask`, {
    method: "POST",
    headers: requestHeaders(id, true),
    body: JSON.stringify({ question, context_md: contextMd }),
  });
  if (!res.ok) return parseError(res);
  return (await res.json()).answer;
}
