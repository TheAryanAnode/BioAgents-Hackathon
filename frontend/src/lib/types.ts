export type NodeType = "paper" | "concept" | "author" | "dataset";
export type SourceType =
  | "semantic_scholar"
  | "pubmed"
  | "arxiv"
  | "user_pdf"
  | "derived"
  | "craft_pancancer"
  | "craft_idc";

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
  rowCount?: number;
  sql?: string;
  connection?: string;
}

export interface ConfidencePoint {
  t: string;
  confidence: number;
}

export interface ConfidenceBreakdown {
  base: number;
  supportCount: number;
  contradictCount: number;
  neutralCount: number;
  supportBoost: number;
  contradictPenalty: number;
  relevanceBoost: number;
  avgRelevance: number;
}

export interface RoiBreakdown {
  confidenceComponent: number;
  unmetNeedComponent: number;
  whitespaceComponent: number;
  formula: string;
}

export interface HypothesisOpportunity {
  id: string;
  hypothesisId: string;
  title: string;
  subgroup: string;
  patientPopulation: number;
  unmetNeed: number;
  competition: number;
  roiScore: number;
  rationale: string;
  roiRationale: string;
  roiBreakdown: RoiBreakdown;
  estimatedFundingUsd: number;
  whitespace: number;
}

export type InvestigationPhase =
  | "plan"
  | "schema"
  | "term"
  | "query"
  | "chart"
  | "synthesis";

export interface InvestigationStep {
  id: string;
  phase: InvestigationPhase;
  agent: string;
  question: string;
  tool: string;
  connection?: string;
  toolInput?: Record<string, unknown>;
  toolOutput?: Record<string, unknown>;
  sql?: string;
  rowCount?: number | null;
  live?: boolean;
  status: "running" | "ok" | "error";
  durationMs?: number | null;
}

export interface InvestigationScore {
  literature: number;
  genomics: number;
  imaging: number;
  revised: number;
}

export interface PlotlyFigure {
  data: Array<Record<string, unknown>>;
  layout?: Record<string, unknown>;
}

export interface InvestigationResult {
  id: string;
  hypothesisId: string;
  steps: InvestigationStep[];
  finding: string;
  findingConfidence: number;
  divergence?: string;
  charts: PlotlyFigure[];
  dataEvidence: EvidenceItem[];
  score: InvestigationScore;
  revisedConfidence?: number | null;
  cohortSize?: number;
  live?: boolean;
  completedAt?: string;
  geneA?: string;
  geneB?: string;
  study?: string;
  cancerName?: string;
  mutationFreqPct?: number;
  coRatePct?: number;
  topModality?: string;
  totalStudies?: number;
  measurements?: number;
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
  subgraph?: GraphData;
  gapNodeIds?: string[];
  confidenceExplanation?: string;
  confidenceBreakdown?: ConfidenceBreakdown;
  opportunity?: HypothesisOpportunity;
  llmEnriched?: boolean;
  craftInvestigated?: boolean;
  investigation?: InvestigationResult | null;
}

export interface ReportSection {
  id: string;
  title: string;
  body: string;
  bullets?: string[];
  highlight?: string;
}

export interface ReportReference {
  title: string;
  url?: string | null;
  stance?: string;
}

export interface HypothesisReport {
  id: string;
  hypothesisId: string;
  title: string;
  generatedAt: string;
  fundingEstimateUsd: number;
  patientPopulation: number;
  timelineMonths?: number;
  sections: ReportSection[];
  references?: ReportReference[];
  keyMetrics?: Record<string, string>;
  markdown?: string;
}

export interface Opportunity {
  id: string;
  hypothesisId: string;
  title: string;
  subgroup: string;
  patientPopulation: number;
  unmetNeed: number;
  competition: number;
  roiScore: number;
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
  url?: string;
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
  stage?: string;
  graph: GraphData;
  hypotheses: Hypothesis[];
  dashboard: DashboardData | null;
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
    | "ping"
    | "snapshot"
    | "investigation_step";
  payload: any;
}
