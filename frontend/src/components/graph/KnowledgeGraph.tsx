import { useEffect, useMemo, useRef, useState } from "react";
import ForceGraph2D from "react-force-graph-2d";
import { useStore } from "../../stores/useStore";
import type { GraphLink, GraphNode } from "../../lib/types";
import {
  GRAPH_COLORS,
  drawNodeCore,
  drawNodeGlow,
  linkEndpointId,
} from "../../lib/graphEffects";

const TYPE_BASE_SIZE: Record<string, number> = {
  concept: 7,
  paper: 4.5,
  author: 3,
};

const ACCENT = GRAPH_COLORS.accent;
const FG = GRAPH_COLORS.fg;
const MUTED = GRAPH_COLORS.muted;
const SUPPORT = GRAPH_COLORS.support;

export function KnowledgeGraph({
  filter,
}: {
  filter: { types: Set<string>; source: "all" | "user_pdf" | "api"; yearMin: number; keyword: string };
}) {
  const graph = useStore((s) => s.graph);
  const stage = useStore((s) => s.stage);
  const running = useStore((s) => s.running);
  const selectNode = useStore((s) => s.selectNode);
  const selectedNode = useStore((s) => s.selectedNode);
  const fgRef = useRef<any>(null);
  const wrapRef = useRef<HTMLDivElement>(null);
  const [dims, setDims] = useState({ w: 800, h: 600 });
  const [hover, setHover] = useState<string | null>(null);

  useEffect(() => {
    const el = wrapRef.current;
    if (!el) return;
    const ro = new ResizeObserver(() => {
      setDims({ w: el.clientWidth, h: el.clientHeight });
    });
    ro.observe(el);
    setDims({ w: el.clientWidth, h: el.clientHeight });
    return () => ro.disconnect();
  }, []);

  const data = useMemo(() => {
    const nodes = graph.nodes.filter((n) => {
      if (!filter.types.has(n.type)) return false;
      if (filter.source === "user_pdf" && n.source !== "user_pdf") return false;
      if (filter.source === "api" && n.source === "user_pdf") return false;
      if (n.type === "paper" && n.year && filter.yearMin && n.year < filter.yearMin)
        return false;
      if (
        filter.keyword &&
        !n.label.toLowerCase().includes(filter.keyword.toLowerCase())
      )
        return false;
      return true;
    });
    const ids = new Set(nodes.map((n) => n.id));
    const links = graph.links.filter(
      (l) =>
        ids.has(typeof l.source === "string" ? l.source : (l.source as any).id) &&
        ids.has(typeof l.target === "string" ? l.target : (l.target as any).id),
    );
    // clone so the engine's mutations don't fight React state
    return {
      nodes: nodes.map((n) => ({ ...n })),
      links: links.map((l) => ({ ...l })),
    };
  }, [graph, filter]);

  const neighbors = useMemo(() => {
    const map = new Map<string, Set<string>>();
    for (const l of graph.links) {
      const s = typeof l.source === "string" ? l.source : (l.source as any).id;
      const t = typeof l.target === "string" ? l.target : (l.target as any).id;
      if (!map.has(s)) map.set(s, new Set());
      if (!map.has(t)) map.set(t, new Set());
      map.get(s)!.add(t);
      map.get(t)!.add(s);
    }
    return map;
  }, [graph]);

  const focusId = hover ?? selectedNode?.id ?? null;
  const focusSet = focusId
    ? new Set([focusId, ...(neighbors.get(focusId) ?? [])])
    : null;

  return (
    <div ref={wrapRef} className="relative h-full w-full">
      {data.nodes.length === 0 ? (
        <div className="flex h-full flex-col items-center justify-center gap-2">
          <span className="label-mono">
            {running || stage === "ingestion"
              ? "ingesting literature…"
              : "awaiting graph data…"}
          </span>
          {running && (
            <span className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
              stage: {stage}
            </span>
          )}
        </div>
      ) : (
        <ForceGraph2D
          ref={fgRef}
          width={dims.w}
          height={dims.h}
          graphData={data}
          backgroundColor="#0A0A0A"
          cooldownTicks={120}
          d3VelocityDecay={0.3}
          linkColor={(l: any) => {
            const s = typeof l.source === "object" ? l.source.id : l.source;
            const t = typeof l.target === "object" ? l.target.id : l.target;
            if (focusSet && (focusSet.has(s) || focusSet.has(t)))
              return "rgba(255,61,0,0.35)";
            return "rgba(115,115,115,0.12)";
          }}
          linkLineDash={(l: any) => (l.kind === "conceptual" ? [3, 3] : null)}
          linkWidth={(l: any) => {
            const s = linkEndpointId(l, "source");
            const t = linkEndpointId(l, "target");
            const focused = focusSet && (focusSet.has(s) || focusSet.has(t));
            if (l.kind === "conceptual") return focused ? 1.6 : 0.8;
            return focused ? 1.2 : 0.5;
          }}
          linkDirectionalParticles={(l: any) => {
            const s = linkEndpointId(l, "source");
            const t = linkEndpointId(l, "target");
            const focused = focusSet && (focusSet.has(s) || focusSet.has(t));
            if (l.kind === "conceptual") return focused ? 5 : 3;
            return focused ? 2 : 1;
          }}
          linkDirectionalParticleSpeed={0.004}
          linkDirectionalParticleWidth={2}
          linkDirectionalParticleColor={() => "rgba(255,61,0,0.9)"}
          onNodeClick={(n: any) => {
            selectNode(n as GraphNode);
            fgRef.current?.centerAt(n.x, n.y, 600);
            fgRef.current?.zoom(2.5, 600);
          }}
          onNodeHover={(n: any) => setHover(n ? n.id : null)}
          onBackgroundClick={() => selectNode(null)}
          nodeCanvasObject={(node: any, ctx, scale) => {
            const n = node as GraphNode & { x: number; y: number };
            const base = TYPE_BASE_SIZE[n.type] ?? 4;
            const r = base + (n.centrality ?? 0) * 8;
            const dim = focusSet ? !focusSet.has(n.id) : false;

            let color: string = MUTED;
            if (n.type === "concept") color = ACCENT;
            else if (n.type === "paper") color = n.source === "user_pdf" ? SUPPORT : FG;
            else color = MUTED;

            if (!dim) {
              const glowIntensity =
                n.type === "concept" ? "high" : n.source === "user_pdf" ? "medium" : "low";
              drawNodeGlow(ctx, n.x, n.y, r, color, scale, glowIntensity);
            }
            ctx.globalAlpha = dim ? 0.18 : 1;
            drawNodeCore(ctx, n.x, n.y, r, color, dim ? 0.18 : 1);

            // User-uploaded papers get a ring to signal provenance.
            if (n.source === "user_pdf") {
              ctx.lineWidth = 1.5 / scale;
              ctx.strokeStyle = SUPPORT;
              ctx.stroke();
            }
            if (selectedNode?.id === n.id) {
              ctx.lineWidth = 2 / scale;
              ctx.strokeStyle = ACCENT;
              ctx.beginPath();
              ctx.arc(n.x, n.y, r + 3, 0, 2 * Math.PI);
              ctx.stroke();
            }

            // Labels appear for concepts always, others when zoomed/focused.
            const showLabel =
              n.type === "concept" || scale > 2.2 || (focusSet && focusSet.has(n.id));
            if (showLabel && !dim) {
              const fontSize = Math.max(2.5, (n.type === "concept" ? 4 : 3));
              ctx.font = `${n.type === "concept" ? "600 " : ""}${fontSize}px "Inter Tight", sans-serif`;
              ctx.fillStyle = n.type === "concept" ? ACCENT : FG;
              ctx.textAlign = "center";
              ctx.textBaseline = "top";
              const text =
                n.label.length > 28 ? n.label.slice(0, 26) + "…" : n.label;
              ctx.fillText(text, n.x, n.y + r + 1);
            }
            ctx.globalAlpha = 1;
          }}
          nodePointerAreaPaint={(node: any, color, ctx) => {
            const n = node as GraphNode & { x: number; y: number };
            const base = TYPE_BASE_SIZE[n.type] ?? 4;
            const r = base + (n.centrality ?? 0) * 8 + 2;
            ctx.fillStyle = color;
            ctx.beginPath();
            ctx.arc(n.x, n.y, r, 0, 2 * Math.PI);
            ctx.fill();
          }}
        />
      )}

      <GraphControls fgRef={fgRef} />
      <Legend />
    </div>
  );
}

function GraphControls({ fgRef }: { fgRef: React.MutableRefObject<any> }) {
  return (
    <div className="absolute bottom-4 right-4 flex flex-col gap-1">
      {[
        { label: "+", fn: () => fgRef.current?.zoom((fgRef.current?.zoom() ?? 1) * 1.4, 300) },
        { label: "−", fn: () => fgRef.current?.zoom((fgRef.current?.zoom() ?? 1) / 1.4, 300) },
        { label: "⊡", fn: () => fgRef.current?.zoomToFit(500, 40) },
      ].map((b) => (
        <button
          key={b.label}
          onClick={b.fn}
          className="h-9 w-9 border border-border bg-background/80 font-mono text-sm text-muted-foreground backdrop-blur transition-colors hover:border-accent hover:text-accent"
        >
          {b.label}
        </button>
      ))}
    </div>
  );
}

function Legend() {
  const items = [
    { c: "#FF3D00", t: "Concept" },
    { c: "#FAFAFA", t: "Paper" },
    { c: "#34D399", t: "Your upload" },
    { c: "#737373", t: "Author" },
  ];
  return (
    <div className="absolute bottom-4 left-4 flex flex-col gap-1.5 border border-border bg-background/80 p-3 backdrop-blur">
      {items.map((i) => (
        <div key={i.t} className="flex items-center gap-2">
          <span className="h-2.5 w-2.5 rounded-full" style={{ background: i.c }} />
          <span className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
            {i.t}
          </span>
        </div>
      ))}
    </div>
  );
}

export type { GraphNode, GraphLink };
