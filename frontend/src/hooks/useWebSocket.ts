import { useCallback, useEffect, useRef, useState } from "react";
import type { WSEvent } from "../types";
import { getRunToken, getShareToken } from "../lib/api";

type WSStatus = "disconnected" | "connecting" | "connected" | "error";

export function useWebSocket(runId: string | null) {
  const [events, setEvents] = useState<WSEvent[]>([]);
  const [status, setStatus] = useState<WSStatus>("disconnected");
  const wsRef = useRef<WebSocket | null>(null);
  const retriesRef = useRef(0);
  const runIdRef = useRef(runId);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const lastProgressRef = useRef<string | null>(null);
  const lastSeqRef = useRef(0);
  const terminalRef = useRef(false);
  const connectRef = useRef<() => void>(() => undefined);

  useEffect(() => {
    runIdRef.current = runId;
  }, [runId]);

  const appendEvent = useCallback((event: WSEvent) => {
    if (event.seq && event.seq <= lastSeqRef.current) return;
    if (event.seq) lastSeqRef.current = event.seq;
    if (terminalRef.current) return;
    if (event.type === "complete" || event.type === "error" || event.type === "cancelled") terminalRef.current = true;
    setEvents((previous) => [...previous, event]);
  }, []);

  const stopPolling = useCallback(() => {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = null;
  }, []);

  const startPolling = useCallback((id: string) => {
    stopPolling();
    pollRef.current = setInterval(async () => {
      if (terminalRef.current) return stopPolling();
      const token = getRunToken(id);
      const share = getShareToken();
      const url = `/api/simulate/${id}${share ? `?share=${encodeURIComponent(share)}` : ""}`;
      try {
        const res = await fetch(url, {
          headers: token ? { Authorization: `Bearer ${token}` } : undefined,
        });
        if (!res.ok) return;
        const data = await res.json();
        if (data.stage || data.progress_percent) {
          appendEvent({
            type: "stage",
            stage: data.stage || "schema",
            progress: data.progress_percent || 0,
            label: data.progress,
          });
        }
        if (data.status === "schema_pending") {
          appendEvent({ type: "schema_pending", schema: data.schema || null });
        } else if (data.status === "completed" && data.result) {
          appendEvent({ type: "complete", result: data.result });
          stopPolling();
        } else if (data.status === "failed" || data.status === "cancelled") {
          appendEvent({ type: "error", message: data.error || `Simulation ${data.status}` });
          stopPolling();
        }
        if (data.progress) lastProgressRef.current = data.progress;
      } catch {
        // Polling is a best-effort fallback while WebSocket reconnects.
      }
    }, 3000);
  }, [appendEvent, stopPolling]);

  const connect = useCallback(() => {
    const id = runIdRef.current;
    if (!id || terminalRef.current) return;
    setStatus("connecting");
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const params = new URLSearchParams({ since: String(lastSeqRef.current) });
    const token = getRunToken(id);
    const share = getShareToken();
    if (token) params.set("token", token);
    else if (share) params.set("share", share);
    const ws = new WebSocket(`${protocol}//${window.location.host}/api/ws/simulate/${id}?${params}`);
    wsRef.current = ws;

    ws.onopen = () => {
      setStatus("connected");
      retriesRef.current = 0;
      stopPolling();
    };
    ws.onmessage = (message) => {
      try { appendEvent(JSON.parse(message.data)); }
      catch { /* Ignore malformed transport messages. */ }
    };
    ws.onerror = () => setStatus("error");
    ws.onclose = () => {
      setStatus("disconnected");
      if (terminalRef.current || !runIdRef.current) return;
      const delay = Math.min(1000 * 2 ** retriesRef.current, 10000);
      retriesRef.current += 1;
      if (retriesRef.current <= 5) setTimeout(() => connectRef.current(), delay);
      else startPolling(runIdRef.current);
    };
  }, [appendEvent, startPolling, stopPolling]);

  useEffect(() => {
    connectRef.current = connect;
  }, [connect]);

  const disconnect = useCallback(() => {
    retriesRef.current = 99;
    wsRef.current?.close();
    wsRef.current = null;
    setStatus("disconnected");
    stopPolling();
  }, [stopPolling]);

  const reset = useCallback(() => {
    setEvents([]);
    retriesRef.current = 0;
    lastProgressRef.current = null;
    lastSeqRef.current = 0;
    terminalRef.current = false;
  }, []);

  useEffect(() => {
    if (runId) {
      reset();
      connect();
      startPolling(runId);
    }
    return () => {
      wsRef.current?.close();
      wsRef.current = null;
      stopPolling();
    };
  }, [runId, connect, reset, startPolling, stopPolling]);

  return { events, status, connect, disconnect, reset };
}
