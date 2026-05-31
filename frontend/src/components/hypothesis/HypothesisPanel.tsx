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
import { Loader2, Sparkles } from "lucide-react";
import { useStore } from "../../stores/useStore";
import { api } from "../../lib/api";
import { Button } from "../ui/Button";
import { Badge, Card } from "../ui/Card";
import { cn, SOURCE_LABEL } from "../../lib/utils";
import type { EvidenceItem, Hypothesis } from "../../lib/types";

export function HypothesisPanel() {
  const hypotheses = useStore((s) => s.hypotheses);
  const selectedId = useStore((s) => s.selectedHypothesisId);
  const select = useStore((s) => s.selectHypothesis);
  const sessionId = useStore((s) => s.sessionId);
  const applyEvent = useStore((s) => s.applyEvent);
  const [busy, setBusy] = useState(false);

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

  return (
    <div className="flex h-full flex-col lg:flex-row">
      {/* Left: list + heatmap */}
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
                <p className="mt-2 text-sm leading-snug text-foreground">
                  {h.statement}
                </p>
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

      {/* Right: evidence stack */}
      <div className="flex-1 overflow-y-auto">
        {selected ? (
          <EvidenceView hypothesis={selected} />
        ) : (
          <div className="flex h-full items-center justify-center">
            <span className="label-mono">select a hypothesis</span>
          </div>
        )}
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
  // Merge each hypothesis's confidence history onto a shared time axis.
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
            <XAxis
              dataKey="t"
              tick={{ fill: "#737373", fontSize: 9, fontFamily: "JetBrains Mono" }}
              stroke="#262626"
            />
            <YAxis
              domain={[0, 100]}
              tick={{ fill: "#737373", fontSize: 9, fontFamily: "JetBrains Mono" }}
              stroke="#262626"
            />
            <Tooltip
              contentStyle={{
                background: "#0F0F0F",
                border: "1px solid #262626",
                borderRadius: 0,
                fontFamily: "JetBrains Mono",
                fontSize: 11,
              }}
            />
            {hypotheses.map((_, hi) => (
              <Area
                key={hi}
                type="monotone"
                dataKey={`h${hi}`}
                stroke={hi === 0 ? "#FF3D00" : "#737373"}
                strokeWidth={hi === 0 ? 2 : 1}
                fill={hi === 0 ? "url(#confGrad)" : "transparent"}
              />
            ))}
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function EvidenceView({ hypothesis }: { hypothesis: Hypothesis }) {
  const support = hypothesis.evidence.filter((e) => e.stance === "support");
  const contradict = hypothesis.evidence.filter((e) => e.stance === "contradict");
  return (
    <div className="p-6 md:p-8">
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

      <div className="mt-8 grid grid-cols-2 gap-4 border-y border-border py-4 sm:grid-cols-4">
        <Metric label="Confidence" value={`${hypothesis.confidence}%`} accent />
        <Metric label="Supporting" value={`${support.length}`} />
        <Metric label="Contradicting" value={`${contradict.length}`} />
        <Metric label="Status" value={hypothesis.status} />
      </div>

      <div className="mt-8 flex items-center gap-3">
        <span className="label-mono">Evidence stack</span>
      </div>
      <div className="mt-4 flex flex-col gap-3">
        {hypothesis.evidence.map((e) => (
          <EvidenceCard key={e.paperId + e.snippet.slice(0, 8)} item={e} />
        ))}
      </div>
    </div>
  );
}

function Metric({ label, value, accent }: { label: string; value: string; accent?: boolean }) {
  return (
    <div>
      <div className="label-mono">{label}</div>
      <div className={cn("mt-1 text-xl font-bold tracking-tight", accent && "text-accent")}>
        {value}
      </div>
    </div>
  );
}

function EvidenceCard({ item }: { item: EvidenceItem }) {
  const tone =
    item.stance === "support" ? "support" : item.stance === "contradict" ? "contradict" : "muted";
  return (
    <Card className="p-4 md:p-4">
      <div className="flex items-start justify-between gap-3">
        <p className="text-sm font-semibold leading-snug">{item.title}</p>
        <Badge tone={tone}>{item.stance}</Badge>
      </div>
      <p className="mt-2 text-sm leading-normal text-muted-foreground">
        “{item.snippet}”
      </p>
      <div className="mt-3 flex items-center gap-4 font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
        <span>{SOURCE_LABEL[item.source] ?? item.source}</span>
        {item.year && <span>{item.year}</span>}
        <span>relevance {(item.relevance * 100).toFixed(0)}</span>
        {item.url && (
          <a href={item.url} target="_blank" rel="noreferrer" className="text-accent">
            source
          </a>
        )}
      </div>
    </Card>
  );
}
