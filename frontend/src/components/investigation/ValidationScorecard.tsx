import { motion } from "framer-motion";
import type { InvestigationResult } from "../../lib/types";
import { cn, formatNumber } from "../../lib/utils";
import { Card } from "../ui/Card";
import { RadiogenomicMatrix } from "./RadiogenomicMatrix";
import { RadiogenomicsChart } from "./RadiogenomicsChart";

/**
 * Tri-modal validation: literature vs genomics vs imaging, plus the revised
 * confidence and the actionable finding. Forked from ConfidenceExplainer's
 * BreakdownItem grid — same tokens, sharp corners, no count-up animation.
 */
export function ValidationScorecard({
  investigation,
}: {
  investigation: InvestigationResult;
}) {
  const s = investigation.score;
  const chart = investigation.charts?.[0];

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: [0.25, 0, 0, 1] }}
    >
      <Card accentTop className="p-6">
        <div className="mb-4 flex items-center gap-3">
          <span className="label-mono">Tri-modal validation</span>
          {investigation.live ? (
            <span className="font-mono text-[10px] uppercase tracking-widest text-support">
              live CRAFT
            </span>
          ) : (
            <span className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
              CRAFT demo data
            </span>
          )}
          <span className="ml-auto font-mono text-3xl font-bold text-accent">
            {s.revised}%
          </span>
        </div>

        <div className="grid grid-cols-3 gap-3">
          <ScoreItem label="Literature" value={s.literature} sub="papers" />
          <ScoreItem label="Genomics" value={s.genomics} sub="PanCancer" tone="support" />
          <ScoreItem label="Imaging" value={s.imaging} sub="IDC feasibility" tone="support" />
        </div>

        <p className="mt-4 font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
          Revised = 0.45 × literature + 0.35 × genomics + 0.20 × imaging
        </p>

        <div className="mt-6 grid grid-cols-2 gap-4 border-t border-border pt-4 sm:grid-cols-4">
          <Fact label="Cancer" value={investigation.cancerName || investigation.study || "—"} />
          <Fact
            label={`${investigation.geneA ?? ""} freq`}
            value={`${(investigation.mutationFreqPct ?? 0).toFixed(0)}%`}
          />
          <Fact
            label="Co-alteration"
            value={`${(investigation.coRatePct ?? 0).toFixed(1)}%`}
          />
          <Fact
            label="Top modality"
            value={`${investigation.topModality ?? "—"} · ${formatNumber(
              investigation.totalStudies ?? 0,
            )}`}
          />
        </div>

        {chart && (
          <div className="mt-6">
            <RadiogenomicsChart figure={chart} />
          </div>
        )}

        {investigation.matrixChart && (
          <div className="mt-6">
            <RadiogenomicMatrix
              figure={investigation.matrixChart}
              archetypes={investigation.archetypes ?? []}
            />
          </div>
        )}

        <div className="mt-6 border-l-2 border-accent bg-muted/20 p-4">
          <div className="label-mono mb-2">Actionable finding</div>
          <p className="text-base font-medium leading-normal text-foreground">
            {investigation.finding}
          </p>
        </div>

        {investigation.divergence && (
          <div className="mt-4 border border-border p-4">
            <div className="label-mono mb-2">Literature vs patient data</div>
            <p className="text-sm leading-normal text-muted-foreground">
              {investigation.divergence}
            </p>
          </div>
        )}
      </Card>
    </motion.div>
  );
}

function ScoreItem({
  label,
  value,
  sub,
  tone,
}: {
  label: string;
  value: number;
  sub?: string;
  tone?: "support" | "contradict";
}) {
  return (
    <div className="border border-border p-3">
      <div className="label-mono">{label}</div>
      <div
        className={cn(
          "mt-1 text-2xl font-bold tracking-tight",
          tone === "support" && "text-support",
          tone === "contradict" && "text-contradict",
          !tone && "text-foreground",
        )}
      >
        {value}%
      </div>
      {sub && <div className="mt-0.5 text-xs text-muted-foreground">{sub}</div>}
    </div>
  );
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="label-mono">{label}</div>
      <div className="mt-1 text-sm font-bold tracking-tight text-foreground">{value}</div>
    </div>
  );
}
