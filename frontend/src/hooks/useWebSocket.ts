import { useEffect, useRef } from "react";
import { api } from "../lib/api";
import { useStore } from "../stores/useStore";
import type { WsEvent } from "../lib/types";

/**
 * Subscribes to the agent event stream for a session. Each message is a
 * discrete agent action (audit line, stage change, node added, etc.) which is
 * applied to the global store, driving the live "watch the agents work" demo.
 */
export function useWebSocket(sessionId: string | null) {
  const applyEvent = useStore((s) => s.applyEvent);
  const ref = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!sessionId) return;
    const ws = new WebSocket(api.wsUrl(sessionId));
    ref.current = ws;

    ws.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data) as WsEvent;
        applyEvent(data);
      } catch {
        /* ignore malformed frames */
      }
    };

    return () => {
      ws.close();
      ref.current = null;
    };
  }, [sessionId, applyEvent]);

  return ref;
}
