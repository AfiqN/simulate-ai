import { useCallback, useEffect, useRef, useState } from "react";
import type { WSEvent } from "../types";

type WSStatus = "disconnected" | "connecting" | "connected" | "error";

export function useWebSocket(runId: string | null) {
  const [events, setEvents] = useState<WSEvent[]>([]);
  const [status, setStatus] = useState<WSStatus>("disconnected");
  const wsRef = useRef<WebSocket | null>(null);
  const retriesRef = useRef(0);
  const runIdRef = useRef(runId);

  runIdRef.current = runId;

  const connect = useCallback(() => {
    const id = runIdRef.current;
    if (!id) return;
    setStatus("connecting");

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1"
      ? window.location.host
      : `${window.location.hostname}:8000`;
    const ws = new WebSocket(`${protocol}//${host}/api/ws/simulate/${id}`);
    wsRef.current = ws;

    ws.onopen = () => {
      setStatus("connected");
      retriesRef.current = 0;
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
      }
    };
  }, []);

  const disconnect = useCallback(() => {
    retriesRef.current = 99;
    wsRef.current?.close();
    wsRef.current = null;
    setStatus("disconnected");
  }, []);

  const reset = useCallback(() => {
    setEvents([]);
    retriesRef.current = 0;
  }, []);

  useEffect(() => {
    if (runId) {
      setEvents([]);
      retriesRef.current = 0;
      connect();
    }
    return () => {
      wsRef.current?.close();
      wsRef.current = null;
    };
  }, [runId, connect]);

  return { events, status, connect, disconnect, reset };
}
