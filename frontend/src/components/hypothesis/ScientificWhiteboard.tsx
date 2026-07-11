import { useMemo, useState } from "react";
import type { EvidenceItem, Hypothesis } from "../../lib/types";

type DiagramId = "pathway" | "interaction" | "progression" | "cascade";

const DIAGRAMS: {
  id: DiagramId;
  label: string;
  subtitle: string;
  explains: string;
}[] = [
  {
    id: "pathway",
    label: "Pathway",
    subtitle: "Entity signaling route",
    explains:
      "A directed route A → B → C: how the hypothesis proposes one entity acts on the next in sequence. Arrows read as “influences / signals to”.",
  },
  {
    id: "interaction",
    label: "Interactions",
    subtitle: "Molecular binding map",
    explains:
      "Which entities interact around a shared bridge node. Dashed lines are putative links; green = a supporting paper exists, red = a conflicting one.",
  },
  {
    id: "progression",
    label: "Progression",
    subtitle: "Disease stage model",
    explains:
      "Left-to-right disease stages with the confidence trajectory overlaid — how belief in the hypothesis shifts as evidence accumulates (or decays under conflict).",
  },
  {
    id: "cascade",
    label: "Cascade",
    subtitle: "Protein activation chain",
    explains:
      "A top-down activation chain: each step switches on the next, like a signaling cascade triggered by the lead entity.",
  },
];

/** Deterministic Nature-style figures from hypothesis entities — zero API calls. */
export function ScientificWhiteboard({ hypothesis }: { hypothesis: Hypothesis }) {
  const [active, setActive] = useState<DiagramId>("pathway");
  const entities = useMemo(() => {
    const ents = hypothesis.entities.length >= 2 ? hypothesis.entities : ["Target A", "Pathway B", "Disease C"];
    return ents.slice(0, 4);
  }, [hypothesis.entities]);

  const contradictCount =
    hypothesis.confidenceBreakdown?.contradictCount ??
    hypothesis.evidence.filter((e) => e.stance === "contradict").length;

  const activeDiagram = DIAGRAMS.find((d) => d.id === active)!;

  return (
    <div className="border border-border bg-[#0F0F0F]">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border px-4 py-3">
        <div>
          <span className="label-mono">Scientific whiteboard</span>
          <p className="mt-1 text-xs text-muted-foreground">
            Illustrative schematics drawn from the hypothesis' gap entities — hand-drawn
            style, generated locally with no AI calls or patient data. Use them to
            picture the mechanism, not as a source of truth.
          </p>
        </div>
        <div className="flex flex-wrap gap-1">
          {DIAGRAMS.map((d) => (
            <button
              key={d.id}
              type="button"
              onClick={() => setActive(d.id)}
              className={`border px-2 py-1 font-mono text-[9px] uppercase tracking-widest transition-colors ${
                active === d.id
                  ? "border-accent text-accent"
                  : "border-border text-muted-foreground hover:text-foreground"
              }`}
            >
              {d.label}
            </button>
          ))}
        </div>
      </div>

      {/* Plain-language explanation of the selected diagram. */}
      <div className="border-b border-border px-4 py-2.5">
        <p className="text-xs leading-normal text-muted-foreground">
          <span className="font-mono uppercase tracking-widest text-accent">
            {activeDiagram.label}
          </span>{" "}
          — {activeDiagram.explains}
        </p>
      </div>

      <div className="relative bg-white p-4">
        <div className="pointer-events-none absolute left-4 top-3 font-mono text-[8px] uppercase tracking-widest text-neutral-400">
          Fig. 1 — {DIAGRAMS.find((d) => d.id === active)?.subtitle}
        </div>
        {active === "pathway" && <PathwayDiagram entities={entities} confidence={hypothesis.confidence} />}
        {active === "interaction" && (
          <InteractionDiagram entities={entities} evidence={hypothesis.evidence} />
        )}
        {active === "progression" && (
          <ProgressionDiagram
            entities={entities}
            history={hypothesis.history}
            contradictCount={contradictCount}
          />
        )}
        {active === "cascade" && <CascadeDiagram entities={entities} />}
      </div>
    </div>
  );
}

function PathwayDiagram({ entities, confidence }: { entities: string[]; confidence: number }) {
  const nodes = entities.slice(0, 3);
  const w = 480;
  const h = 200;
  const xs = [80, w / 2, w - 80];

  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="mx-auto mt-4 w-full max-w-xl" role="img">
      <defs>
        <marker id="arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
          <path d="M0,0 L6,3 L0,6 Z" fill="#FF3D00" />
        </marker>
        <filter id="glow">
          <feGaussianBlur stdDeviation="2" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>
      {nodes.slice(0, -1).map((_, i) => (
        <line
          key={i}
          x1={xs[i] + 36}
          y1={h / 2}
          x2={xs[i + 1] - 36}
          y2={h / 2}
          stroke="#FF3D00"
          strokeWidth="2"
          markerEnd="url(#arrow)"
          opacity={0.7}
        />
      ))}
      {nodes.map((label, i) => (
        <g key={label} transform={`translate(${xs[i]}, ${h / 2})`}>
          <circle r="32" fill="#FFF5F2" stroke="#FF3D00" strokeWidth="2" filter="url(#glow)" />
          <text
            textAnchor="middle"
            dominantBaseline="middle"
            fill="#171717"
            fontSize="9"
            fontFamily="Georgia, serif"
            fontWeight="600"
          >
            {truncate(label, 14)}
          </text>
        </g>
      ))}
      <text x={w / 2} y={h - 12} textAnchor="middle" fill="#737373" fontSize="8" fontFamily="monospace">
        Hypothesized pathway · confidence {confidence}%
      </text>
    </svg>
  );
}

function InteractionDiagram({
  entities,
  evidence,
}: {
  entities: string[];
  evidence: EvidenceItem[];
}) {
  const w = 480;
  const h = 220;
  const center = { x: w / 2, y: h / 2 - 10 };
  const orbit = entities.slice(0, 3).map((label, i) => {
    const angle = (i / 3) * Math.PI * 2 - Math.PI / 2;
    return {
      label,
      x: center.x + Math.cos(angle) * 90,
      y: center.y + Math.sin(angle) * 70,
      stance: evidence.find((e) =>
        e.title.toLowerCase().includes(label.toLowerCase().split(" ")[0]),
      )?.stance,
    };
  });

  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="mx-auto mt-4 w-full max-w-xl" role="img">
      {orbit.map((a, i) =>
        orbit.slice(i + 1).map((b) => (
          <line
            key={`${a.label}-${b.label}`}
            x1={a.x}
            y1={a.y}
            x2={b.x}
            y2={b.y}
            stroke="#D4D4D4"
            strokeWidth="1"
            strokeDasharray="4 3"
          />
        )),
      )}
      <ellipse cx={center.x} cy={center.y} rx="28" ry="20" fill="#FF3D00" fillOpacity="0.12" stroke="#FF3D00" strokeWidth="1.5" />
      <text x={center.x} y={center.y + 4} textAnchor="middle" fill="#FF3D00" fontSize="8" fontFamily="monospace">
        BRIDGE
      </text>
      {orbit.map((node) => {
        const color =
          node.stance === "contradict" ? "#F87171" : node.stance === "support" ? "#34D399" : "#262626";
        return (
          <g key={node.label}>
            <rect
              x={node.x - 42}
              y={node.y - 18}
              width="84"
              height="36"
              rx="4"
              fill="white"
              stroke={color}
              strokeWidth="2"
            />
            <text
              x={node.x}
              y={node.y + 4}
              textAnchor="middle"
              fill="#171717"
              fontSize="8"
              fontFamily="Georgia, serif"
            >
              {truncate(node.label, 16)}
            </text>
          </g>
        );
      })}
      <text x={w / 2} y={h - 8} textAnchor="middle" fill="#737373" fontSize="8" fontFamily="monospace">
        Dashed = putative · green = supporting evidence · red = conflicting
      </text>
    </svg>
  );
}

function ProgressionDiagram({
  entities,
  history,
  contradictCount,
}: {
  entities: string[];
  history: { t: string; confidence: number }[];
  contradictCount: number;
}) {
  const w = 480;
  const h = 200;
  const stages = entities.slice(0, 4);
  const pad = 50;
  const step = (w - pad * 2) / Math.max(1, stages.length - 1);

  const confLine = history.length >= 2 ? history : [{ t: "T0", confidence: 50 }, { t: "T1", confidence: 70 }];
  const maxConf = 100;

  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="mx-auto mt-4 w-full max-w-xl" role="img">
      {stages.map((label, i) => {
        const x = pad + i * step;
        return (
          <g key={label}>
            <rect x={x - 36} y={30} width="72" height="40" fill="#FAFAFA" stroke="#262626" strokeWidth="1" />
            <text x={x} y={55} textAnchor="middle" fill="#171717" fontSize="8" fontFamily="Georgia, serif">
              {truncate(label, 12)}
            </text>
            {i < stages.length - 1 && (
              <path d={`M ${x + 38} 50 L ${x + step - 38} 50`} stroke="#737373" strokeWidth="1.5" markerEnd="url(#prog-arrow)" />
            )}
          </g>
        );
      })}
      <defs>
        <marker id="prog-arrow" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">
          <path d="M0,0 L6,3 L0,6 Z" fill="#737373" />
        </marker>
      </defs>
      <polyline
        fill="none"
        stroke="#FF3D00"
        strokeWidth="2"
        points={confLine
          .map((p, i) => {
            const x = pad + (i / Math.max(1, confLine.length - 1)) * (w - pad * 2);
            const y = h - 20 - (p.confidence / maxConf) * 50;
            return `${x},${y}`;
          })
          .join(" ")}
      />
      {contradictCount > 0 && (
        <text x={w / 2} y={h - 4} textAnchor="middle" fill="#F87171" fontSize="8" fontFamily="monospace">
          ↓ confidence decay from {contradictCount} conflicting {contradictCount === 1 ? "study" : "studies"}
        </text>
      )}
    </svg>
  );
}

function CascadeDiagram({ entities }: { entities: string[] }) {
  const w = 280;
  const h = 240;
  const items = entities.slice(0, 4);
  const stepY = 48;

  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="mx-auto mt-4 w-full max-w-xs" role="img">
      <defs>
        <linearGradient id="cascade-grad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#FF3D00" stopOpacity="0.15" />
          <stop offset="100%" stopColor="#FF3D00" stopOpacity="0.02" />
        </linearGradient>
      </defs>
      <rect x="40" y="20" width="200" height={items.length * stepY + 20} fill="url(#cascade-grad)" stroke="#E5E5E5" />
      {items.map((label, i) => {
        const y = 40 + i * stepY;
        const active = i < items.length - 1;
        return (
          <g key={label}>
            <circle cx="140" cy={y} r="18" fill="white" stroke={active ? "#FF3D00" : "#737373"} strokeWidth="2" />
            <text x="140" y={y + 3} textAnchor="middle" fill="#171717" fontSize="7" fontFamily="Georgia, serif">
              {truncate(label, 10)}
            </text>
            {i < items.length - 1 && (
              <line x1="140" y1={y + 20} x2="140" y2={y + stepY - 20} stroke="#FF3D00" strokeWidth="1.5" opacity="0.6" />
            )}
          </g>
        );
      })}
      <text x="140" y={h - 6} textAnchor="middle" fill="#737373" fontSize="8" fontFamily="monospace">
        Proposed activation cascade
      </text>
    </svg>
  );
}

function truncate(s: string, max: number) {
  return s.length > max ? s.slice(0, max - 1) + "…" : s;
}
