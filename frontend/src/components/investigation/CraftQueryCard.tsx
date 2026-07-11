import { useState } from "react";
import { ChevronDown } from "lucide-react";
import type { InvestigationStep } from "../../lib/types";
import { cn } from "../../lib/utils";

const PHASE_LABEL: Record<InvestigationStep["phase"], string> = {
  plan: "Plan",
  term: "Resolve term",
  schema: "Search schema",
  query: "Query",
  chart: "Chart",
  synthesis: "Synthesis",
};

/**
 * One investigation step: the natural-language question, the CRAFT tool used,
 * and (when present) the generated SQL + a compact row preview. Sharp corners,
 * mono labels — Bold Typography.
 */
export function CraftQueryCard({ step }: { step: InvestigationStep }) {
  const hasDetail = Boolean(step.sql) || rowPreview(step).length > 0;
  const [open, setOpen] = useState(false);

  return (
    <div className="border border-border bg-card">
      <button
        onClick={() => hasDetail && setOpen((v) => !v)}
        className={cn(
          "flex w-full items-start gap-3 p-3 text-left transition-colors",
          hasDetail && "hover:bg-muted",
        )}
      >
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="label-mono text-accent">{PHASE_LABEL[step.phase]}</span>
            <span className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
              {step.tool}
            </span>
            {step.connection && (
              <span className="font-mono text-[10px] text-muted-foreground">
                {step.connection}
              </span>
            )}
            {typeof step.rowCount === "number" && (
              <span className="border border-border px-1.5 py-0.5 font-mono text-[10px] text-foreground">
                {step.rowCount} rows
              </span>
            )}
            {step.live ? (
              <span className="font-mono text-[9px] uppercase tracking-widest text-support">
                live
              </span>
            ) : (
              <span className="font-mono text-[9px] uppercase tracking-widest text-muted-foreground">
                demo
              </span>
            )}
          </div>
          <p className="mt-1.5 text-sm leading-snug text-foreground">{step.question}</p>
        </div>
        {hasDetail && (
          <ChevronDown
            size={14}
            strokeWidth={1.5}
            className={cn(
              "mt-1 shrink-0 text-muted-foreground transition-transform",
              open && "rotate-180",
            )}
          />
        )}
      </button>

      {open && hasDetail && (
        <div className="border-t border-border">
          {step.sql && (
            <div className="p-3">
              <div className="label-mono mb-1.5">Generated SQL</div>
              <pre className="overflow-x-auto border border-border bg-background p-3 font-mono text-[11px] leading-relaxed text-muted-foreground">
                {step.sql}
              </pre>
            </div>
          )}
          {rowPreview(step).length > 0 && (
            <div className="p-3 pt-0">
              <div className="label-mono mb-1.5">Result</div>
              <pre className="overflow-x-auto border border-border bg-background p-3 font-mono text-[11px] leading-relaxed text-muted-foreground">
                {JSON.stringify(rowPreview(step), null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function rowPreview(step: InvestigationStep): unknown[] {
  const rows = (step.toolOutput as { rows?: unknown[] } | undefined)?.rows;
  return Array.isArray(rows) ? rows.slice(0, 6) : [];
}
