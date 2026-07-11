import { useMemo, useState } from "react";
import { useStore } from "../../stores/useStore";
import { KnowledgeGraph } from "./KnowledgeGraph";
import { NodeDetailPanel } from "./NodeDetailPanel";
import { UploadControl } from "../upload/UploadControl";
import { cn } from "../../lib/utils";

type SourceFilter = "all" | "api" | "user_pdf";
const TYPES = ["paper", "concept", "author", "dataset"] as const;

export function GraphView() {
  const graph = useStore((s) => s.graph);
  const [types, setTypes] = useState<Set<string>>(new Set(TYPES));
  const [source, setSource] = useState<SourceFilter>("all");
  const [keyword, setKeyword] = useState("");
  const [yearMin, setYearMin] = useState(0);

  const years = useMemo(
    () => graph.nodes.map((n) => n.year).filter(Boolean) as number[],
    [graph],
  );
  const minYear = years.length ? Math.min(...years) : 2000;
  const maxYear = years.length ? Math.max(...years) : 2025;

  const toggleType = (t: string) =>
    setTypes((prev) => {
      const next = new Set(prev);
      next.has(t) ? next.delete(t) : next.add(t);
      return next;
    });

  const counts = useMemo(() => {
    const c = { paper: 0, concept: 0, author: 0, dataset: 0, user: 0 };
    for (const n of graph.nodes) {
      c[n.type as "paper" | "concept" | "author" | "dataset"]++;
      if (n.source === "user_pdf") c.user++;
    }
    return c;
  }, [graph]);

  return (
    <div className="flex h-full flex-col">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2 border-b border-border px-4 py-2.5">
        <div className="flex items-center gap-1">
          {TYPES.map((t) => (
            <button
              key={t}
              onClick={() => toggleType(t)}
              className={cn(
                "border px-2.5 py-1 font-mono text-[10px] uppercase tracking-widest transition-colors",
                types.has(t)
                  ? "border-accent text-accent"
                  : "border-border text-muted-foreground hover:text-foreground",
              )}
            >
              {t}{" "}
              {t === "paper"
                ? counts.paper
                : t === "concept"
                  ? counts.concept
                  : t === "dataset"
                    ? counts.dataset
                    : counts.author}
            </button>
          ))}
        </div>

        <span className="h-4 w-px bg-border" />

        <div className="flex items-center gap-1">
          {(["all", "api", "user_pdf"] as SourceFilter[]).map((s) => (
            <button
              key={s}
              onClick={() => setSource(s)}
              className={cn(
                "border px-2.5 py-1 font-mono text-[10px] uppercase tracking-widest transition-colors",
                source === s
                  ? "border-accent text-accent"
                  : "border-border text-muted-foreground hover:text-foreground",
              )}
            >
              {s === "all" ? "All" : s === "api" ? "API" : `User ${counts.user}`}
            </button>
          ))}
        </div>

        <span className="hidden h-4 w-px bg-border sm:block" />

        <div className="hidden items-center gap-2 sm:flex">
          <span className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
            ≥ {yearMin || minYear}
          </span>
          <input
            type="range"
            min={minYear}
            max={maxYear}
            value={yearMin || minYear}
            onChange={(e) => setYearMin(Number(e.target.value))}
            className="accent-accent"
          />
        </div>

        <input
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
          placeholder="filter…"
          className="h-8 w-28 border border-border bg-input px-2 font-mono text-xs text-foreground outline-none focus:border-accent"
        />

        <div className="ml-auto">
          <UploadControl />
        </div>
      </div>

      <div className="relative flex-1">
        <KnowledgeGraph filter={{ types, source, yearMin, keyword }} />
        <NodeDetailPanel />
      </div>
    </div>
  );
}
