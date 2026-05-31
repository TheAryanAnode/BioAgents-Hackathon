import type { Hypothesis, SessionState } from "./types";

const BASE = "/api";

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  async health(): Promise<{ status: string; gemini: boolean }> {
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

  wsUrl(sessionId: string): string {
    const proto = location.protocol === "https:" ? "wss" : "ws";
    return `${proto}://${location.host}/ws/${sessionId}`;
  },
};
