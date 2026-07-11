from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

SourceType = Literal[
    "semantic_scholar", "pubmed", "arxiv", "user_pdf", "derived",
    "craft_pancancer", "craft_idc",
]
NodeType = Literal["paper", "concept", "author", "dataset"]
Stance = Literal["support", "contradict", "neutral"]


class PaperRecord(BaseModel):
    """Unified representation for an API-fetched paper or a user upload."""

    id: str
    title: str
    authors: list[str] = Field(default_factory=list)
    year: Optional[int] = None
    abstract: str = ""
    full_text_excerpt: str = ""
    citation_count: int = 0
    source: SourceType = "semantic_scholar"
    external_ids: dict[str, str] = Field(default_factory=dict)
    url: Optional[str] = None


class GraphNode(BaseModel):
    id: str
    label: str
    type: NodeType
    source: Optional[SourceType] = None
    cluster: Optional[int] = None
    clusterLabel: Optional[str] = None
    centrality: float = 0.0
    year: Optional[int] = None
    citationCount: Optional[int] = None
    summary: Optional[str] = None
    authors: Optional[list[str]] = None
    url: Optional[str] = None
    paperCount: Optional[int] = None


class GraphLink(BaseModel):
    source: str
    target: str
    kind: Literal["citation", "conceptual", "authored"]
    weight: float = 1.0


class Cluster(BaseModel):
    id: int
    label: str


class GraphData(BaseModel):
    nodes: list[GraphNode] = Field(default_factory=list)
    links: list[GraphLink] = Field(default_factory=list)
    clusters: list[Cluster] = Field(default_factory=list)


class EvidenceItem(BaseModel):
    paperId: str
    title: str
    source: SourceType
    relevance: float
    stance: Stance
    snippet: str
    year: Optional[int] = None
    url: Optional[str] = None
    # Populated for CRAFT real-world-evidence rows (patient-data, not papers).
    rowCount: Optional[int] = None
    sql: Optional[str] = None
    connection: Optional[str] = None


class ConfidenceBreakdown(BaseModel):
    base: int = 50
    supportCount: int = 0
    contradictCount: int = 0
    neutralCount: int = 0
    supportBoost: int = 0
    contradictPenalty: int = 0
    relevanceBoost: int = 0
    avgRelevance: float = 0.0


class RoiBreakdown(BaseModel):
    confidenceComponent: int = 0
    unmetNeedComponent: int = 0
    whitespaceComponent: int = 0
    formula: str = "0.4×confidence + 0.3×unmetNeed + 0.3×whitespace"


class HypothesisOpportunity(BaseModel):
    id: str
    hypothesisId: str
    title: str
    subgroup: str
    patientPopulation: int
    unmetNeed: int
    competition: int
    roiScore: int
    rationale: str
    roiRationale: str = ""
    roiBreakdown: RoiBreakdown = Field(default_factory=RoiBreakdown)
    estimatedFundingUsd: int = 0
    whitespace: int = 0


class ConfidencePoint(BaseModel):
    t: str
    confidence: int


InvestigationPhase = Literal["plan", "schema", "term", "query", "chart", "synthesis"]


class InvestigationStep(BaseModel):
    """One CRAFT tool call in the investigation, captured for the live timeline."""

    id: str
    phase: InvestigationPhase
    agent: str            # craft_planner | craft_pancancer | craft_imaging | craft_synthesizer
    question: str         # why this step runs (human-readable)
    tool: str             # search_schema | resolve_term | generate_sql | execute_query | ...
    connection: str = ""  # CRAFT connection slug when applicable
    toolInput: dict = Field(default_factory=dict)
    toolOutput: dict = Field(default_factory=dict)
    sql: str = ""
    rowCount: Optional[int] = None
    live: bool = False     # True when a real MCP call served this step
    status: Literal["running", "ok", "error"] = "ok"
    durationMs: Optional[int] = None


class InvestigationScore(BaseModel):
    """Tri-modal validation scorecard shown alongside literature confidence."""

    literature: int = 0    # existing literature-derived confidence
    genomics: int = 0      # PanCancer evidence strength
    imaging: int = 0       # IDC imaging feasibility
    revised: int = 0       # blended, revised hypothesis confidence


class InvestigationResult(BaseModel):
    id: str
    hypothesisId: str
    steps: list[InvestigationStep] = Field(default_factory=list)
    finding: str = ""                  # actionable radiogenomics insight
    findingConfidence: int = 0
    divergence: str = ""               # where literature and patient data disagree
    charts: list[dict] = Field(default_factory=list)  # Plotly figure specs
    dataEvidence: list["EvidenceItem"] = Field(default_factory=list)
    score: InvestigationScore = Field(default_factory=InvestigationScore)
    revisedConfidence: Optional[int] = None
    cohortSize: int = 0
    live: bool = False
    completedAt: str = ""
    # Investigation subject + key measured figures (for commercial + report).
    geneA: str = ""
    geneB: str = ""
    study: str = ""
    cancerName: str = ""
    mutationFreqPct: float = 0.0
    coRatePct: float = 0.0
    topModality: str = ""
    totalStudies: int = 0
    measurements: int = 0


class Hypothesis(BaseModel):
    id: str
    statement: str
    rationale: str
    confidence: int
    status: Literal["emerging", "supported", "contested"]
    evidence: list[EvidenceItem] = Field(default_factory=list)
    history: list[ConfidencePoint] = Field(default_factory=list)
    entities: list[str] = Field(default_factory=list)
    subgraph: GraphData = Field(default_factory=GraphData)
    gapNodeIds: list[str] = Field(default_factory=list)
    confidenceExplanation: str = ""
    confidenceBreakdown: Optional[ConfidenceBreakdown] = None
    opportunity: Optional[HypothesisOpportunity] = None
    geminiEnriched: bool = False
    craftInvestigated: bool = False
    investigation: Optional[InvestigationResult] = None


class ReportSection(BaseModel):
    id: str
    title: str
    body: str
    bullets: list[str] = Field(default_factory=list)
    highlight: str = ""


class ReportReference(BaseModel):
    title: str
    url: Optional[str] = None
    stance: str = "neutral"


class HypothesisReport(BaseModel):
    id: str
    hypothesisId: str
    title: str
    generatedAt: str
    fundingEstimateUsd: int = 0
    patientPopulation: int = 0
    timelineMonths: int = 18
    sections: list[ReportSection] = Field(default_factory=list)
    references: list[ReportReference] = Field(default_factory=list)
    keyMetrics: dict[str, str] = Field(default_factory=dict)
    markdown: str = ""  # plain-text export fallback


class Opportunity(BaseModel):
    id: str
    hypothesisId: str
    title: str
    subgroup: str
    patientPopulation: int
    unmetNeed: int
    competition: int
    roiScore: int
    rationale: str


class DashboardMetrics(BaseModel):
    opportunities: int
    avgConfidence: int
    patientPopulation: int
    projectedRoi: float


class DashboardData(BaseModel):
    metrics: DashboardMetrics
    opportunities: list[Opportunity] = Field(default_factory=list)
    trends: list[dict] = Field(default_factory=list)
    trendTopics: list[str] = Field(default_factory=list)
    stratification: list[dict] = Field(default_factory=list)
    crossDisease: list[dict] = Field(default_factory=list)


class AuditEntry(BaseModel):
    id: str
    ts: str
    agent: str
    action: str
    detail: str = ""
    params: dict = Field(default_factory=dict)
    durationMs: Optional[int] = None
    status: Literal["ok", "running", "error"] = "ok"


class SessionState(BaseModel):
    sessionId: str
    query: str
    stage: str = "idle"
    graph: GraphData = Field(default_factory=GraphData)
    hypotheses: list[Hypothesis] = Field(default_factory=list)
    dashboard: Optional[DashboardData] = None
    audit: list[AuditEntry] = Field(default_factory=list)


# Request bodies
class ResearchRequest(BaseModel):
    query: str


class ChatCitation(BaseModel):
    paperId: str
    title: str
    source: SourceType
    url: Optional[str] = None


class ChatRequest(BaseModel):
    message: str
    focusNodeId: Optional[str] = None
