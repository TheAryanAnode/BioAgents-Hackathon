import { useEffect, useRef } from "react";
import { api } from "../lib/api";
import { useStore } from "../stores/useStore";
import type { WsEvent } from "../lib/types";

/**
 * Subscribes to the agent event stream for a session. Each message is a
 * discrete agent action (audit line, stage change, node added, etc.) which is
 * applied to the global store, driving the live "watch the agents work" demo.
 *
 * Also polls REST while the pipeline is running so the UI hydrates even if
 * the WebSocket connects late or drops (common in React Strict Mode dev).
 */
export function useWebSocket(sessionId: string | null) {
  const applyEvent = useStore((s) => s.applyEvent);
  const loadSession = useStore((s) => s.loadSession);
  const ref = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!sessionId) return;

    let cancelled = false;

    const hydrate = async () => {
      try {
        const state = await api.getSession(sessionId);
        if (!cancelled) loadSession(state);
      } catch {
        /* session may not exist yet */
      }
    };

    void hydrate();

    const poll = window.setInterval(() => {
      if (useStore.getState().running) void hydrate();
    }, 2500);

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
      cancelled = true;
      window.clearInterval(poll);
      ws.close();
      ref.current = null;
    };
  }, [sessionId, applyEvent, loadSession]);

  return ref;
}
