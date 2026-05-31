export type NodeType = "paper" | "concept" | "author";
export type SourceType = "semantic_scholar" | "pubmed" | "arxiv" | "user_pdf" | "derived";

export interface GraphNode {
  id: string;
  label: string;
  type: NodeType;
  source?: SourceType;
  cluster?: number;
  clusterLabel?: string;
  centrality?: number;
  year?: number;
  citationCount?: number;
  summary?: string;
  authors?: string[];
  url?: string;
  paperCount?: number;
  // runtime fields populated by the force graph engine
  x?: number;
  y?: number;
}

export interface GraphLink {
  source: string;
  target: string;
  kind: "citation" | "conceptual" | "authored";
  weight?: number;
}

export interface GraphData {
  nodes: GraphNode[];
  links: GraphLink[];
  clusters: { id: number; label: string }[];
}

export interface EvidenceItem {
  paperId: string;
  title: string;
  source: SourceType;
  relevance: number;
  stance: "support" | "contradict" | "neutral";
  snippet: string;
  year?: number;
  url?: string;
}

export interface ConfidencePoint {
  t: string;
  confidence: number;
}

export interface Hypothesis {
  id: string;
  statement: string;
  rationale: string;
  confidence: number;
  status: "emerging" | "supported" | "contested";
  evidence: EvidenceItem[];
  history: ConfidencePoint[];
  entities: string[];
}

export interface Opportunity {
  id: string;
  hypothesisId: string;
  title: string;
  subgroup: string;
  patientPopulation: number;
  unmetNeed: number; // 0-100
  competition: number; // 0-100, lower = whitespace
  roiScore: number; // 0-100
  rationale: string;
}

export interface TrendPoint {
  year: number;
  [topic: string]: number;
}

export interface DashboardData {
  metrics: {
    opportunities: number;
    avgConfidence: number;
    patientPopulation: number;
    projectedRoi: number;
  };
  opportunities: Opportunity[];
  trends: TrendPoint[];
  trendTopics: string[];
  stratification: { subgroup: string; prevalence: number }[];
  crossDisease: { from: string; to: string; strength: number }[];
}

export interface AuditEntry {
  id: string;
  ts: string;
  agent: string;
  action: string;
  detail: string;
  params?: Record<string, unknown>;
  durationMs?: number;
  status: "ok" | "running" | "error";
}

export interface ChatCitation {
  paperId: string;
  title: string;
  source: SourceType;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  ts: string;
  citations?: ChatCitation[];
}

export interface SessionState {
  sessionId: string;
  query: string;
  graph: GraphData;
  hypotheses: Hypothesis[];
  dashboard: DashboardData;
  audit: AuditEntry[];
}

export interface WsEvent {
  type:
    | "audit"
    | "stage"
    | "graph"
    | "hypotheses"
    | "dashboard"
    | "node"
    | "done"
    | "error"
    | "ping";
  payload: any;
}
