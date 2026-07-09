import { useCallback, useEffect, useRef, useState } from "react";
import type { WSEvent } from "../types";

type WSStatus = "disconnected" | "connecting" | "connected" | "error";

export function useWebSocket(runId: string | null) {
  const [events, setEvents] = useState<WSEvent[]>([]);
  const [status, setStatus] = useState<WSStatus>("disconnected");
  const wsRef = useRef<WebSocket | null>(null);
  const retriesRef = useRef(0);
  const runIdRef = useRef(runId);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const lastProgressRef = useRef<string | null>(null);

  runIdRef.current = runId;

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const startPolling = useCallback((id: string) => {
    stopPolling();
    pollRef.current = setInterval(async () => {
      try {
        const res = await fetch(`/api/simulate/${id}`);
        if (!res.ok) return;
        const data = await res.json();

        // Emit progress as synthetic stage events
        if (data.progress && data.progress !== lastProgressRef.current) {
          lastProgressRef.current = data.progress;
          setEvents((prev) => [...prev, { type: "stage", stage: "running", progress: null, label: data.progress }]);
        }

        // Handle terminal states
        if (data.status === "completed" && data.result) {
          setEvents((prev) => [...prev, { type: "complete", result: data.result }]);
          stopPolling();
        } else if (data.status === "failed") {
          setEvents((prev) => [...prev, { type: "error", message: data.error || "Simulation failed" }]);
          stopPolling();
        }
      } catch {
        // Ignore fetch errors during polling
      }
    }, 3000);
  }, [stopPolling]);

  const connect = useCallback(() => {
    const id = runIdRef.current;
    if (!id) return;
    setStatus("connecting");

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host;
    const ws = new WebSocket(`${protocol}//${host}/api/ws/simulate/${id}`);
    wsRef.current = ws;

    ws.onopen = () => {
      setStatus("connected");
      retriesRef.current = 0;
      stopPolling(); // WS connected, no need for polling
    };

    ws.onmessage = (e) => {
      const event: WSEvent = JSON.parse(e.data);
      setEvents((prev) => [...prev, event]);
    };

    ws.onerror = () => {
      setStatus("error");
    };

    ws.onclose = () => {
      setStatus("disconnected");
      const delay = Math.min(1000 * 2 ** retriesRef.current, 10000);
      retriesRef.current++;
      if (retriesRef.current <= 5 && runIdRef.current) {
        setTimeout(connect, delay);
      } else if (runIdRef.current) {
        // WS exhausted retries — fall back to polling
        startPolling(runIdRef.current);
      }
    };
  }, [stopPolling, startPolling]);

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
  }, []);

  useEffect(() => {
    if (runId) {
      setEvents([]);
      retriesRef.current = 0;
      lastProgressRef.current = null;
      connect();
      // Start polling immediately as backup — will stop once WS connects
      startPolling(runId);
    }
    return () => {
      wsRef.current?.close();
      wsRef.current = null;
      stopPolling();
    };
  }, [runId, connect, startPolling, stopPolling]);

  return { events, status, connect, disconnect, reset };
}
