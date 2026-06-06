import { Card } from "../ui/Card";
import type { ConfidenceBreakdown, Hypothesis } from "../../lib/types";
import { cn } from "../../lib/utils";

export function ConfidenceExplainer({ hypothesis }: { hypothesis: Hypothesis }) {
  const bd = hypothesis.confidenceBreakdown;
  return (
    <Card className="p-5">
      <div className="mb-3 flex items-center gap-3">
        <span className="h-1 w-8 bg-accent" />
        <span className="label-mono">Confidence score</span>
        <span className="ml-auto font-mono text-2xl font-bold text-accent">
          {hypothesis.confidence}%
        </span>
      </div>
      <p className="text-sm leading-normal text-muted-foreground">
        {hypothesis.confidenceExplanation ||
          "Confidence reflects how strongly the ingested literature supports this hypothesis versus contradicting it, weighted by semantic relevance."}
      </p>
      {bd && (
        <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <BreakdownItem label="Baseline" value={`${bd.base}%`} />
          <BreakdownItem label="Support" value={`+${bd.supportBoost}`} tone="support" sub={`${bd.supportCount} papers`} />
          <BreakdownItem label="Contradict" value={`−${bd.contradictPenalty}`} tone="contradict" sub={`${bd.contradictCount} papers`} />
          <BreakdownItem label="Relevance" value={`+${bd.relevanceBoost}`} sub={`avg ${Math.round(bd.avgRelevance * 100)}%`} />
        </div>
      )}
      <p className="mt-4 font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
        Status: {hypothesis.status} · {bd?.neutralCount ?? 0} neutral source(s)
      </p>
    </Card>
  );
}

function BreakdownItem({
  label,
  value,
  sub,
  tone,
}: {
  label: string;
  value: string;
  sub?: string;
  tone?: "support" | "contradict";
}) {
  return (
    <div className="border border-border p-3">
      <div className="label-mono">{label}</div>
      <div
        className={cn(
          "mt-1 text-lg font-bold",
          tone === "support" && "text-support",
          tone === "contradict" && "text-contradict",
          !tone && "text-foreground",
        )}
      >
        {value}
      </div>
      {sub && <div className="mt-0.5 text-xs text-muted-foreground">{sub}</div>}
    </div>
  );
}
