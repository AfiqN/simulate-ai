const STORAGE_KEY = "simulate-ai-history";
const MAX_ENTRIES = 20;

export interface HistoryEntry {
  runId: string;
  scenarioName: string;
  verdict: string;
  agents: number;
  depth: string;
  duration?: number;
  timestamp: number;
}

export function getHistory(): HistoryEntry[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    return JSON.parse(raw);
  } catch {
    return [];
  }
}

export function saveToHistory(entry: HistoryEntry) {
  try {
    const history = getHistory();
    // Don't duplicate
    if (history.some((h) => h.runId === entry.runId)) return;
    // Prepend (newest first), cap at MAX_ENTRIES
    const updated = [entry, ...history].slice(0, MAX_ENTRIES);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
  } catch {}
}

export function removeFromHistory(runId: string) {
  try {
    const history = getHistory().filter((h) => h.runId !== runId);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(history));
  } catch {}
}

export function clearAllHistory() {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch {}
}
