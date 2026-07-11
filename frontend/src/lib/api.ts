import type { Hypothesis, HypothesisReport, SessionState } from "./types";

/**
 * API base URL.
 * - Local dev: empty → Vite proxy `/api`
 * - Vercel experimentalServices: `/_/backend` (same origin)
 * - Override: set VITE_API_URL in env
 */
function backendOrigin(): string {
  const env = import.meta.env.VITE_API_URL?.replace(/\/$/, "");
  if (env) return env;
  if (import.meta.env.PROD) return "/_/backend";
  return "";
}

const API_ROOT = backendOrigin();
const BASE = API_ROOT ? `${API_ROOT}/api` : "/api";

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  async health(): Promise<{
    status: string;
    llm: boolean;
    llmProvider?: string;
    llmModel?: string;
    llmPipeline?: boolean;
    llmQuotaExhausted?: boolean;
  }> {
    return json(await fetch(`${BASE}/health`));
  },

  async startResearch(query: string): Promise<{ sessionId: string }> {
    return json(
      await fetch(`${BASE}/research`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query }),
      }),
    );
  },

  async getSession(sessionId: string): Promise<SessionState> {
    return json(await fetch(`${BASE}/sessions/${sessionId}`));
  },

  async generateHypothesis(sessionId: string): Promise<Hypothesis> {
    return json(
      await fetch(`${BASE}/sessions/${sessionId}/hypotheses`, {
        method: "POST",
      }),
    );
  },

  /** One Nebius LLM call — only when user explicitly selects a hypothesis. */
  async enrichHypothesis(
    sessionId: string,
    hypothesisId: string,
  ): Promise<Hypothesis> {
    return json(
      await fetch(`${BASE}/sessions/${sessionId}/hypotheses/${hypothesisId}/enrich`, {
        method: "POST",
      }),
    );
  },

  /** User-initiated CRAFT real-world evidence investigation (IDC + PanCancer). */
  async investigateHypothesis(
    sessionId: string,
    hypothesisId: string,
    force = false,
  ): Promise<Hypothesis> {
    const qs = force ? "?force=true" : "";
    return json(
      await fetch(
        `${BASE}/sessions/${sessionId}/hypotheses/${hypothesisId}/investigate${qs}`,
        { method: "POST" },
      ),
    );
  },

  async chat(
    sessionId: string,
    message: string,
    focusNodeId?: string,
  ): Promise<{ content: string; citations: any[] }> {
    return json(
      await fetch(`${BASE}/sessions/${sessionId}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message, focusNodeId }),
      }),
    );
  },

  async uploadPaper(
    sessionId: string,
    file: File,
    meta: { title?: string; doi?: string },
  ): Promise<{ ok: boolean; paperId: string }> {
    const form = new FormData();
    form.append("file", file);
    if (meta.title) form.append("title", meta.title);
    if (meta.doi) form.append("doi", meta.doi);
    return json(
      await fetch(`${BASE}/sessions/${sessionId}/upload`, {
        method: "POST",
        body: form,
      }),
    );
  },

  async generateReport(
    sessionId: string,
    hypothesisId: string,
  ): Promise<HypothesisReport> {
    return json(
      await fetch(`${BASE}/sessions/${sessionId}/hypotheses/${hypothesisId}/report`, {
        method: "POST",
      }),
    );
  },

  wsUrl(sessionId: string): string {
    const wsEnv = import.meta.env.VITE_WS_URL?.replace(/\/$/, "");
    if (wsEnv) return `${wsEnv}/ws/${sessionId}`;
    if (import.meta.env.PROD) {
      const proto = location.protocol === "https:" ? "wss" : "ws";
      return `${proto}://${location.host}/_/backend/ws/${sessionId}`;
    }
    const proto = location.protocol === "https:" ? "wss" : "ws";
    return `${proto}://${location.host}/ws/${sessionId}`;
  },
};
