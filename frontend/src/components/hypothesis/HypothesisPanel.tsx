import { useState } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { FileText, Loader2, Sparkles } from "lucide-react";
import { useStore } from "../../stores/useStore";
import { api } from "../../lib/api";
import { Button } from "../ui/Button";
import { Badge, Card } from "../ui/Card";
import { PaperLink } from "../ui/PaperLink";
import { cn, formatNumber, formatUsd, SOURCE_LABEL } from "../../lib/utils";
import type { EvidenceItem, Hypothesis, HypothesisReport } from "../../lib/types";
import { ConfidenceExplainer } from "./ConfidenceExplainer";
import { HypothesisMiniGraph } from "./HypothesisMiniGraph";
import { ReportModal } from "./ReportModal";

export function HypothesisPanel() {
  const hypotheses = useStore((s) => s.hypotheses);
  const selectedId = useStore((s) => s.selectedHypothesisId);
  const select = useStore((s) => s.selectHypothesis);
  const sessionId = useStore((s) => s.sessionId);
  const applyEvent = useStore((s) => s.applyEvent);
  const [busy, setBusy] = useState(false);
  const [reportBusy, setReportBusy] = useState(false);
  const [report, setReport] = useState<HypothesisReport | null>(null);

  const selected =
    hypotheses.find((h) => h.id === selectedId) ?? hypotheses[0] ?? null;

  const generate = async () => {
    if (!sessionId) return;
    setBusy(true);
    try {
      const h = await api.generateHypothesis(sessionId);
      applyEvent({ type: "hypotheses", payload: [...hypotheses, h] });
      select(h.id);
    } finally {
      setBusy(false);
    }
  };

  const generateReport = async () => {
    if (!sessionId || !selected) return;
    setReportBusy(true);
    try {
      const r = await api.generateReport(sessionId, selected.id);
      setReport(r);
    } finally {
      setReportBusy(false);
    }
  };

  return (
    <div className="flex h-full flex-col lg:flex-row">
      <div className="flex w-full flex-col border-b border-border lg:w-[44%] lg:border-b-0 lg:border-r">
        <div className="flex items-center justify-between border-b border-border px-6 py-4">
          <div className="flex items-center gap-3">
            <span className="h-1 w-10 bg-accent" />
            <span className="label-mono">Hypotheses {hypotheses.length}</span>
          </div>
          <Button size="sm" onClick={generate} disabled={busy || !sessionId}>
            {busy ? (
              <>
                <Loader2 size={14} strokeWidth={1.5} className="animate-spin" /> Generating
              </>
            ) : (
              <>
                <Sparkles size={14} strokeWidth={1.5} /> Generate
              </>
            )}
          </Button>
        </div>

        {hypotheses.length > 0 && (
          <div className="border-b border-border px-4 py-4">
            <ConfidenceChart hypotheses={hypotheses} />
          </div>
        )}

        <div className="flex-1 overflow-y-auto p-4">
          <div className="flex flex-col gap-3">
            {hypotheses.map((h, i) => (
              <button
                key={h.id}
                onClick={() => select(h.id)}
                className={cn(
                  "border p-4 text-left transition-colors",
                  selected?.id === h.id
                    ? "border-accent"
                    : "border-border hover:border-border-hover",
                )}
              >
                <div className="flex items-center justify-between">
                  <span className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
                    H{String(i + 1).padStart(2, "0")}
                  </span>
                  <StatusBadge status={h.status} />
                </div>
                <p className="mt-2 text-sm leading-snug text-foreground">{h.statement}</p>
                {h.opportunity && (
                  <p className="mt-2 font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
                    ROI {h.opportunity.roiScore} · {formatNumber(h.opportunity.patientPopulation)} patients
                  </p>
                )}
                <ConfidenceMeter value={h.confidence} />
              </button>
            ))}
            {hypotheses.length === 0 && (
              <p className="px-2 py-8 text-center text-sm text-muted-foreground">
                Hypotheses appear as the agent finds structural gaps in the graph.
              </p>
            )}
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        {selected ? (
          <HypothesisDetail
            hypothesis={selected}
            onGenerateReport={generateReport}
            reportBusy={reportBusy}
          />
        ) : (
          <div className="flex h-full items-center justify-center">
            <span className="label-mono">select a hypothesis</span>
          </div>
        )}
      </div>

      {report && <ReportModal report={report} onClose={() => setReport(null)} />}
    </div>
  );
}

function HypothesisDetail({
  hypothesis,
  onGenerateReport,
  reportBusy,
}: {
  hypothesis: Hypothesis;
  onGenerateReport: () => void;
  reportBusy: boolean;
}) {
  const support = hypothesis.evidence.filter((e) => e.stance === "support");
  const contradict = hypothesis.evidence.filter((e) => e.stance === "contradict");
  const opp = hypothesis.opportunity;

  return (
    <div className="space-y-8 p-6 md:p-8">
      <div>
        <div className="mb-2 flex items-center gap-3">
          <span className="h-1 w-10 bg-accent" />
          <span className="label-mono">Hypothesis</span>
        </div>
        <h2 className="text-balance text-2xl font-bold leading-tight tracking-tight md:text-3xl">
          {hypothesis.statement}
        </h2>
        <p className="mt-5 max-w-2xl text-base leading-normal text-muted-foreground">
          {hypothesis.rationale}
        </p>
        <div className="mt-6 flex flex-wrap gap-2">
          {hypothesis.entities.map((e) => (
            <Badge key={e} tone="muted">
              {e}
            </Badge>
          ))}
        </div>
      </div>

      <ConfidenceExplainer hypothesis={hypothesis} />

      <div>
        <span className="label-mono">Structural gap (mini graph)</span>
        <p className="mt-2 mb-3 text-sm text-muted-foreground">
          Only the three gap concepts and papers that directly connect them (≥2 shared entities) — not the full corpus graph.
        </p>
        <HypothesisMiniGraph
          data={hypothesis.subgraph ?? { nodes: [], links: [], clusters: [] }}
          gapNodeIds={hypothesis.gapNodeIds}
          entities={hypothesis.entities}
        />
      </div>

      {opp && (
        <Card accentTop className="p-6">
          <div className="mb-4 flex items-center gap-3">
            <span className="label-mono">Commercial opportunity</span>
            <Badge tone="accent">ROI {opp.roiScore}</Badge>
          </div>
          <h3 className="text-xl font-bold tracking-tight">{opp.title}</h3>
          <p className="mt-3 text-sm leading-normal text-muted-foreground">{opp.rationale}</p>

          <div className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
            <Metric label="Patients" value={formatNumber(opp.patientPopulation)} />
            <Metric label="Unmet need" value={`${opp.unmetNeed}/100`} />
            <Metric label="Whitespace" value={`${opp.whitespace}/100`} />
            <Metric label="Est. funding" value={formatUsd(opp.estimatedFundingUsd)} accent />
          </div>

          <div className="mt-6 border-t border-border pt-4">
            <span className="label-mono">How ROI was calculated</span>
            <p className="mt-2 text-sm leading-normal text-muted-foreground">
              {opp.roiRationale || opp.rationale}
            </p>
            {opp.roiBreakdown && (
              <div className="mt-4 grid grid-cols-3 gap-3 font-mono text-xs">
                <div className="border border-border p-2">
                  <div className="text-muted-foreground">Confidence</div>
                  <div className="text-accent">+{opp.roiBreakdown.confidenceComponent}</div>
                </div>
                <div className="border border-border p-2">
                  <div className="text-muted-foreground">Unmet need</div>
                  <div>+{opp.roiBreakdown.unmetNeedComponent}</div>
                </div>
                <div className="border border-border p-2">
                  <div className="text-muted-foreground">Whitespace</div>
                  <div>+{opp.roiBreakdown.whitespaceComponent}</div>
                </div>
              </div>
            )}
            <p className="mt-3 font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
              {opp.roiBreakdown?.formula ?? "Weighted composite score"}
            </p>
          </div>
        </Card>
      )}

      <div className="flex flex-wrap items-center gap-6 border-y border-border py-4">
        <Metric label="Supporting" value={`${support.length}`} />
        <Metric label="Contradicting" value={`${contradict.length}`} />
        <Metric label="Status" value={hypothesis.status} />
        <div className="ml-auto">
          <Button size="sm" onClick={onGenerateReport} disabled={reportBusy}>
            {reportBusy ? (
              <>
                <Loader2 size={14} className="animate-spin" /> Generating report
              </>
            ) : (
              <>
                <FileText size={14} strokeWidth={1.5} /> Generate full report
              </>
            )}
          </Button>
        </div>
      </div>

      <div>
        <span className="label-mono">Evidence stack</span>
        <div className="mt-4 flex flex-col gap-3">
          {hypothesis.evidence.map((e) => (
            <EvidenceCard key={e.paperId + e.snippet.slice(0, 8)} item={e} />
          ))}
        </div>
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: Hypothesis["status"] }) {
  const map: Record<Hypothesis["status"], "support" | "accent" | "contradict"> = {
    supported: "support",
    emerging: "accent",
    contested: "contradict",
  };
  return <Badge tone={map[status]}>{status}</Badge>;
}

function ConfidenceMeter({ value }: { value: number }) {
  return (
    <div className="mt-3 flex items-center gap-3">
      <div className="h-1 flex-1 bg-muted">
        <div className="h-full bg-accent" style={{ width: `${value}%` }} />
      </div>
      <span className="font-mono text-xs text-foreground">{value}%</span>
    </div>
  );
}

function ConfidenceChart({ hypotheses }: { hypotheses: Hypothesis[] }) {
  const points = hypotheses[0]?.history ?? [];
  const data = points.map((p, idx) => {
    const row: Record<string, number | string> = { t: p.t };
    hypotheses.forEach((h, hi) => {
      row[`h${hi}`] = h.history[idx]?.confidence ?? h.confidence;
    });
    return row;
  });

  return (
    <div>
      <span className="label-mono">Confidence over time</span>
      <div className="mt-3 h-28">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 5, right: 5, bottom: 0, left: -28 }}>
            <defs>
              <linearGradient id="confGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#FF3D00" stopOpacity={0.4} />
                <stop offset="100%" stopColor="#FF3D00" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid stroke="#262626" vertical={false} />
            <XAxis dataKey="t" tick={{ fill: "#737373", fontSize: 9, fontFamily: "JetBrains Mono" }} stroke="#262626" />
            <YAxis domain={[0, 100]} tick={{ fill: "#737373", fontSize: 9, fontFamily: "JetBrains Mono" }} stroke="#262626" />
            <Tooltip contentStyle={{ background: "#0F0F0F", border: "1px solid #262626", borderRadius: 0, fontFamily: "JetBrains Mono", fontSize: 11 }} />
            {hypotheses.map((_, hi) => (
              <Area key={hi} type="monotone" dataKey={`h${hi}`} stroke={hi === 0 ? "#FF3D00" : "#737373"} strokeWidth={hi === 0 ? 2 : 1} fill={hi === 0 ? "url(#confGrad)" : "transparent"} />
            ))}
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function Metric({ label, value, accent }: { label: string; value: string; accent?: boolean }) {
  return (
    <div>
      <div className="label-mono">{label}</div>
      <div className={cn("mt-1 text-xl font-bold tracking-tight", accent && "text-accent")}>{value}</div>
    </div>
  );
}

function EvidenceCard({ item }: { item: EvidenceItem }) {
  const tone = item.stance === "support" ? "support" : item.stance === "contradict" ? "contradict" : "muted";
  return (
    <Card className="p-4">
      <div className="flex items-start justify-between gap-3">
        <PaperLink title={item.title} url={item.url} className="text-sm font-semibold leading-snug" />
        <Badge tone={tone}>{item.stance}</Badge>
      </div>
      <p className="mt-2 text-sm leading-normal text-muted-foreground">“{item.snippet}”</p>
      <div className="mt-3 flex flex-wrap items-center gap-4 font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
        <span>{SOURCE_LABEL[item.source] ?? item.source}</span>
        {item.year && <span>{item.year}</span>}
        <span>relevance {(item.relevance * 100).toFixed(0)}</span>
        {item.url && (
          <a href={item.url} target="_blank" rel="noopener noreferrer" className="text-accent underline">
            Open paper ↗
          </a>
        )}
      </div>
    </Card>
  );
}
