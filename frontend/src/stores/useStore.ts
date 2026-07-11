import { create } from "zustand";
import type {
  AuditEntry,
  ChatMessage,
  DashboardData,
  GraphData,
  GraphNode,
  Hypothesis,
  InvestigationStep,
  SessionState,
  WsEvent,
} from "../lib/types";

export type View = "home" | "auto" | "graph" | "hypotheses" | "chat";
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
  llmLive: boolean;
  llmQuotaExhausted: boolean;
  llmModel: string;

  graph: GraphData;
  hypotheses: Hypothesis[];
  selectedHypothesisId: string | null;
  dashboard: DashboardData | null;
  audit: AuditEntry[];
  chat: ChatMessage[];

  selectedNode: GraphNode | null;
  auditOpen: boolean;

  // Live CRAFT investigation streaming (one at a time, user-initiated).
  investigatingId: string | null;
  liveSteps: InvestigationStep[];
  startInvestigation: (hypothesisId: string) => void;
  endInvestigation: () => void;

  setView: (v: View) => void;
  setQuery: (q: string) => void;
  setSession: (id: string) => void;
  setLlm: (live: boolean, quotaExhausted?: boolean, model?: string) => void;
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
  view: "home",
  stage: "idle",
  running: false,
  llmLive: false,
  llmQuotaExhausted: false,
  llmModel: "",

  graph: emptyGraph,
  hypotheses: [],
  selectedHypothesisId: null,
  dashboard: null,
  audit: [],
  chat: [],

  selectedNode: null,
  auditOpen: false,

  investigatingId: null,
  liveSteps: [],
  startInvestigation: (hypothesisId) =>
    set({ investigatingId: hypothesisId, liveSteps: [] }),
  endInvestigation: () => set({ investigatingId: null }),

  setView: (v) => set({ view: v }),
  setQuery: (q) => set({ query: q }),
  setSession: (id) => set({ sessionId: id }),
  setLlm: (live: boolean, quotaExhausted?: boolean, model?: string) =>
    set({
      llmLive: live,
      llmQuotaExhausted: quotaExhausted ?? false,
      llmModel: model ?? get().llmModel,
    }),
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
      investigatingId: null,
      liveSteps: [],
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
      case "investigation_step":
        set((s) => ({ liveSteps: [...s.liveSteps, e.payload as InvestigationStep] }));
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
