import { useStore, type Stage } from "../stores/useStore";
import { cn } from "../lib/utils";

const STAGES: { id: Stage; label: string }[] = [
  { id: "ingestion", label: "Ingest" },
  { id: "analysis", label: "Analyze" },
  { id: "graph", label: "Graph" },
  { id: "hypothesis", label: "Hypothesize" },
  { id: "evidence", label: "Evidence" },
  { id: "commercial", label: "Commercial" },
];

const ORDER: Stage[] = [
  "idle",
  "ingestion",
  "analysis",
  "graph",
  "hypothesis",
  "evidence",
  "commercial",
  "done",
];

export function StageBar() {
  const stage = useStore((s) => s.stage);
  const running = useStore((s) => s.running);
  const current = ORDER.indexOf(stage);

  if (stage === "idle") return null;

  return (
    <div className="flex items-center gap-1 overflow-x-auto border-b border-border bg-background px-4 py-2">
      {STAGES.map((s, i) => {
        const idx = ORDER.indexOf(s.id);
        const done = current > idx || stage === "done";
        const active = stage === s.id;
        return (
          <div key={s.id} className="flex items-center gap-1">
            <div
              className={cn(
                "flex items-center gap-2 px-2 py-1 font-mono text-[10px] uppercase tracking-widest transition-colors",
                done && "text-support",
                active && "text-accent",
                !done && !active && "text-muted-foreground",
              )}
            >
              <span
                className={cn(
                  "h-1.5 w-1.5",
                  done && "bg-support",
                  active && "animate-pulse bg-accent",
                  !done && !active && "bg-border",
                )}
              />
              {s.label}
            </div>
            {i < STAGES.length - 1 && (
              <span className="h-px w-4 bg-border" />
            )}
          </div>
        );
      })}
      {running && (
        <span className="ml-auto shrink-0 font-mono text-[10px] uppercase tracking-widest text-accent">
          ● live
        </span>
      )}
    </div>
  );
}
