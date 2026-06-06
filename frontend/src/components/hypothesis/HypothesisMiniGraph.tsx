import { useEffect, useMemo, useRef, useState } from "react";
import ForceGraph2D from "react-force-graph-2d";
import type { GraphData } from "../../lib/types";

const ACCENT = "#FF3D00";
const FG = "#FAFAFA";
const SUPPORT = "#34D399";
const MUTED = "#737373";

/** Mini force graph scoped to one hypothesis — gap concepts + connecting papers only. */
export function HypothesisMiniGraph({
  data,
  gapNodeIds = [],
  entities = [],
}: {
  data: GraphData;
  gapNodeIds?: string[];
  entities?: string[];
}) {
  const ref = useRef<any>(null);
  const wrapRef = useRef<HTMLDivElement>(null);
  const [w, setW] = useState(320);

  const gapSet = useMemo(() => new Set(gapNodeIds), [gapNodeIds]);
  const entityLabels = useMemo(
    () => new Set(entities.map((e) => e.toLowerCase())),
    [entities],
  );

  useEffect(() => {
    const el = wrapRef.current;
    if (!el) return;
    const ro = new ResizeObserver(() => setW(el.clientWidth));
    ro.observe(el);
    setW(el.clientWidth);
    return () => ro.disconnect();
  }, []);

  const graph = useMemo(
    () => ({
      nodes: data.nodes.map((n) => ({ ...n })),
      links: data.links.map((l) => ({ ...l })),
    }),
    [data],
  );

  if (!graph.nodes.length) {
    return (
      <div className="flex h-48 items-center justify-center border border-border bg-muted/30">
        <span className="label-mono">No connected nodes yet</span>
      </div>
    );
  }

  return (
    <div ref={wrapRef} className="h-52 border border-border bg-background">
      <ForceGraph2D
        ref={ref}
        width={w}
        height={208}
        graphData={graph}
        backgroundColor="#0A0A0A"
        cooldownTicks={80}
        enableNodeDrag={false}
        linkColor={() => "rgba(255,61,0,0.25)"}
        linkWidth={0.9}
        nodeCanvasObject={(node: any, ctx) => {
          const n = node;
          const isGapConcept =
            n.type === "concept" &&
            (gapSet.has(n.id) || entityLabels.has(String(n.label).toLowerCase()));
          const r = isGapConcept ? 7 : n.type === "concept" ? 5 : 4;
          ctx.beginPath();
          ctx.arc(n.x, n.y, r, 0, 2 * Math.PI);
          if (isGapConcept) ctx.fillStyle = ACCENT;
          else if (n.type === "paper" && n.source === "user_pdf") ctx.fillStyle = SUPPORT;
          else if (n.type === "paper") ctx.fillStyle = FG;
          else ctx.fillStyle = MUTED;
          ctx.fill();
          if (isGapConcept) {
            ctx.lineWidth = 1.5;
            ctx.strokeStyle = ACCENT;
            ctx.stroke();
          }
          ctx.font = '9px "JetBrains Mono", monospace';
          ctx.fillStyle = isGapConcept ? ACCENT : FG;
          ctx.textAlign = "center";
          ctx.textBaseline = "top";
          const label = n.label.length > 16 ? n.label.slice(0, 14) + "…" : n.label;
          ctx.fillText(label, n.x, n.y + r + 2);
        }}
        onEngineStop={() => ref.current?.zoomToFit(400, 24)}
      />
    </div>
  );
}
