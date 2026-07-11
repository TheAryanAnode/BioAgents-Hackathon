import { useEffect, useMemo, useRef, useState } from "react";
import ForceGraph2D from "react-force-graph-2d";
import type { EvidenceItem, GraphData } from "../../lib/types";
import {
  GRAPH_COLORS,
  drawNodeCore,
  drawNodeGlow,
  linkEndpointId,
} from "../../lib/graphEffects";

/** Mini force graph scoped to one hypothesis — gap concepts + connecting papers only. */
export function HypothesisMiniGraph({
  data,
  gapNodeIds = [],
  entities = [],
  evidence = [],
}: {
  data: GraphData;
  gapNodeIds?: string[];
  entities?: string[];
  evidence?: EvidenceItem[];
}) {
  const ref = useRef<any>(null);
  const wrapRef = useRef<HTMLDivElement>(null);
  const [w, setW] = useState(320);

  const gapSet = useMemo(() => new Set(gapNodeIds), [gapNodeIds]);
  const entityLabels = useMemo(
    () => new Set(entities.map((e) => e.toLowerCase())),
    [entities],
  );
  const stanceByPaper = useMemo(() => {
    const m = new Map<string, EvidenceItem["stance"]>();
    for (const e of evidence) m.set(e.paperId, e.stance);
    return m;
  }, [evidence]);

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

  const linkStyle = (l: { source: unknown; target: unknown; kind?: string }) => {
    const sId = linkEndpointId(l, "source");
    const tId = linkEndpointId(l, "target");
    for (const id of [sId, tId]) {
      const stance = stanceByPaper.get(id);
      if (stance === "contradict") {
        return { color: "rgba(248,113,113,0.9)", width: 2.2, dash: [4, 3] as number[] | null, particles: 3, particleColor: "#F87171" };
      }
      if (stance === "support") {
        return { color: "rgba(52,211,153,0.7)", width: 1.6, dash: null, particles: 2, particleColor: "#34D399" };
      }
    }
    if (l.kind === "conceptual") {
      return { color: "rgba(255,61,0,0.45)", width: 1.4, dash: [3, 3] as number[] | null, particles: 4, particleColor: "#FF3D00" };
    }
    return { color: "rgba(255,61,0,0.25)", width: 0.9, dash: null, particles: 1, particleColor: "#FF3D00" };
  };

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
        linkColor={(l) => linkStyle(l).color}
        linkWidth={(l) => linkStyle(l).width}
        linkLineDash={(l) => linkStyle(l).dash}
        linkDirectionalParticles={(l) => linkStyle(l).particles}
        linkDirectionalParticleSpeed={0.005}
        linkDirectionalParticleWidth={2}
        linkDirectionalParticleColor={(l) => linkStyle(l).particleColor}
        nodeCanvasObject={(node: any, ctx, scale) => {
          const n = node;
          const isGapConcept =
            n.type === "concept" &&
            (gapSet.has(n.id) || entityLabels.has(String(n.label).toLowerCase()));
          const stance = n.type === "paper" ? stanceByPaper.get(n.id) : undefined;
          const r = isGapConcept ? 7 : n.type === "concept" ? 5 : 4;

          let color: string = GRAPH_COLORS.muted;
          let glow: "low" | "medium" | "high" = "low";
          if (isGapConcept) {
            color = GRAPH_COLORS.accent;
            glow = "high";
          } else if (stance === "contradict") {
            color = GRAPH_COLORS.contradict;
            glow = "medium";
          } else if (stance === "support") {
            color = GRAPH_COLORS.support;
            glow = "medium";
          } else if (n.type === "paper" && n.source === "user_pdf") {
            color = GRAPH_COLORS.support;
          } else if (n.type === "paper") {
            color = GRAPH_COLORS.fg;
          }

          drawNodeGlow(ctx, n.x, n.y, r, color, scale, glow);
          drawNodeCore(ctx, n.x, n.y, r, color);

          if (stance === "contradict") {
            ctx.save();
            ctx.lineWidth = 1.5 / scale;
            ctx.strokeStyle = GRAPH_COLORS.contradict;
            ctx.setLineDash([2, 2]);
            ctx.beginPath();
            ctx.arc(n.x, n.y, r + 3, 0, 2 * Math.PI);
            ctx.stroke();
            ctx.restore();
          }

          ctx.font = '9px "JetBrains Mono", monospace';
          ctx.fillStyle = isGapConcept ? GRAPH_COLORS.accent : GRAPH_COLORS.fg;
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
