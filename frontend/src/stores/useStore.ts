import { create } from "zustand";
import type {
  AuditEntry,
  ChatMessage,
  DashboardData,
  GraphData,
  GraphNode,
  Hypothesis,
  SessionState,
  WsEvent,
} from "../lib/types";

export type View = "graph" | "hypotheses" | "chat";
export type Stage =
  | "idle"
  | "ingestion"
  | "analysis"
  | "graph"
  | "hypothesis"
  | "evidence"
  | "commercial"
  | "done";

interface Store {
  sessionId: string | null;
  query: string;
  view: View;
  stage: Stage;
  running: boolean;
  geminiLive: boolean;
  geminiQuotaExhausted: boolean;

  graph: GraphData;
  hypotheses: Hypothesis[];
  selectedHypothesisId: string | null;
  dashboard: DashboardData | null;
  audit: AuditEntry[];
  chat: ChatMessage[];

  selectedNode: GraphNode | null;
  auditOpen: boolean;

  setView: (v: View) => void;
  setQuery: (q: string) => void;
  setSession: (id: string) => void;
  setGemini: (live: boolean, quotaExhausted?: boolean) => void;
  setRunning: (r: boolean) => void;
  selectNode: (n: GraphNode | null) => void;
  selectHypothesis: (id: string | null) => void;
  toggleAudit: () => void;
  addChat: (m: ChatMessage) => void;
  reset: () => void;
  loadSession: (state: SessionState & { done?: boolean }) => void;
  applyEvent: (e: WsEvent) => void;
}

const emptyGraph: GraphData = { nodes: [], links: [], clusters: [] };

export const useStore = create<Store>((set, get) => ({
  sessionId: null,
  query: "",
  view: "graph",
  stage: "idle",
  running: false,
  geminiLive: false,
  geminiQuotaExhausted: false,

  graph: emptyGraph,
  hypotheses: [],
  selectedHypothesisId: null,
  dashboard: null,
  audit: [],
  chat: [],

  selectedNode: null,
  auditOpen: false,

  setView: (v) => set({ view: v }),
  setQuery: (q) => set({ query: q }),
  setSession: (id) => set({ sessionId: id }),
  setGemini: (live: boolean, quotaExhausted?: boolean) =>
    set({ geminiLive: live, geminiQuotaExhausted: quotaExhausted ?? false }),
  setRunning: (r) => set({ running: r }),
  selectNode: (n) => set({ selectedNode: n }),
  selectHypothesis: (id) => set({ selectedHypothesisId: id }),
  toggleAudit: () => set((s) => ({ auditOpen: !s.auditOpen })),
  addChat: (m) => set((s) => ({ chat: [...s.chat, m] })),

  reset: () =>
    set({
      graph: emptyGraph,
      hypotheses: [],
      selectedHypothesisId: null,
      dashboard: null,
      audit: [],
      chat: [],
      selectedNode: null,
      stage: "idle",
    }),

  loadSession: (state) =>
    set((s) => ({
      graph: state.graph ?? emptyGraph,
      hypotheses: state.hypotheses ?? [],
      selectedHypothesisId:
        s.selectedHypothesisId ?? state.hypotheses?.[0]?.id ?? null,
      dashboard: state.dashboard ?? null,
      audit: state.audit ?? [],
      stage: (state.stage as Stage) || s.stage,
      running: state.done ? false : s.running,
    })),

  applyEvent: (e) => {
    switch (e.type) {
      case "ping":
        break;
      case "snapshot":
        get().loadSession(e.payload as SessionState & { done?: boolean });
        break;
      case "audit":
        set((s) => ({ audit: [...s.audit, e.payload as AuditEntry] }));
        break;
      case "stage":
        set({ stage: e.payload.stage as Stage });
        break;
      case "node": {
        const node = e.payload as GraphNode;
        set((s) => {
          if (s.graph.nodes.some((n) => n.id === node.id)) return {};
          return { graph: { ...s.graph, nodes: [...s.graph.nodes, node] } };
        });
        break;
      }
      case "graph":
        set({ graph: e.payload as GraphData });
        break;
      case "hypotheses": {
        const hyps = e.payload as Hypothesis[];
        set((s) => ({
          hypotheses: hyps,
          selectedHypothesisId: s.selectedHypothesisId ?? hyps[0]?.id ?? null,
        }));
        break;
      }
      case "dashboard":
        set({ dashboard: e.payload as DashboardData });
        break;
      case "done":
        set({ stage: "done", running: false });
        break;
      case "error":
        set({ running: false });
        break;
    }
    void get;
  },
}));
