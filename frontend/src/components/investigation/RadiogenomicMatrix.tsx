import { useState } from "react";
import { motion } from "framer-motion";
import { HelpCircle } from "lucide-react";
import type { PlotlyFigure, RadiogenomicArchetype } from "../../lib/types";
import { cn } from "../../lib/utils";

/** Short labels for inline chart explainability — one word or phrase each. */
const MATRIX_LEGEND = [
  { term: "Rows", hint: "DICOM modalities (CT, MR, PT…)" },
  { term: "Columns", hint: "Cancer types / molecular subtypes" },
  { term: "Cells", hint: "Imaging study count · IDC" },
  { term: "Blue strip", hint: "Mutation prevalence % · PanCancer" },
] as const;

/**
 * Radiogenomic correlation matrix — the biotech-challenge deliverable.
 *
 * Renders the CRAFT heatmap figure (modality × cancer-type imaging coverage) as
 * a lightweight SVG grid (no plotly.js bundle), with a mutation-prevalence strip
 * beneath each cancer column and the k-means "radiogenomic archetypes" the agent
 * discovered in the data. Dark theme, sharp corners — matches the design system.
 */
export function RadiogenomicMatrix({
  figure,
  archetypes = [],
}: {
  figure: PlotlyFigure;
  archetypes?: RadiogenomicArchetype[];
}) {
  const trace = figure.data?.[0] as
    | { z?: number[][]; x?: string[]; y?: string[] }
    | undefined;
  const z = trace?.z ?? [];
  const cancers = (trace?.x ?? []).map(String);
  const modalities = (trace?.y ?? []).map(String);
  const prevalence = figure.prevalence ?? [];
  const [showHelp, setShowHelp] = useState(false);
  if (!z.length || !cancers.length || !modalities.length) return null;

  const title = String((figure.layout as any)?.title ?? "");
  const max = Math.max(1, ...z.flat().map((v) => Number(v) || 0));
  const maxPrev = Math.max(1, ...prevalence.map((v) => Number(v) || 0));

  // Layout geometry.
  const cell = 46;
  const labelL = 108; // modality row labels + y-axis title
  const labelT = 128; // rotated cancer labels + x-axis title
  const prevH = 26;
  const gridW = cancers.length * cell;
  const gridH = modalities.length * cell;
  const W = labelL + gridW + 20;
  const H = labelT + gridH + prevH + 44;

  // Vermillion intensity ramp on dark (0 → near-background, 1 → accent).
  const fill = (v: number) => {
    const t = Math.max(0, Math.min(1, v / max));
    const r = Math.round(20 + t * (255 - 20));
    const g = Math.round(20 + t * (61 - 20));
    const b = Math.round(24 + t * (0 - 24));
    return `rgb(${r},${g},${b})`;
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, ease: [0.25, 0, 0, 1] }}
      className="border border-border bg-background p-4"
    >
      <div className="mb-1 flex flex-wrap items-center gap-3">
        <span className="h-1 w-8 bg-accent" />
        <span className="label-mono">Radiogenomic correlation matrix</span>
        <button
          type="button"
          onClick={() => setShowHelp((v) => !v)}
          className={cn(
            "flex items-center gap-1 font-mono text-[10px] uppercase tracking-widest transition-colors",
            showHelp ? "text-accent" : "text-muted-foreground hover:text-foreground",
          )}
        >
          <HelpCircle size={12} strokeWidth={1.5} /> What is this?
        </button>
      </div>

      <p className="mb-3 text-sm leading-normal text-muted-foreground">
        Does <span className="text-foreground">imaging coverage</span> track{" "}
        <span className="text-foreground">molecular subtype</span> across cancers? —
        the official biotech prompt. PanCancer prevalence joined to IDC modality counts
        per TCGA collection.
      </p>

      {showHelp && (
        <div className="mb-4 border border-border bg-card/70 p-4 backdrop-blur">
          <div className="label-mono mb-2">Reading the matrix</div>
          <ul className="grid gap-1.5 sm:grid-cols-2">
            {MATRIX_LEGEND.map((item) => (
              <li key={item.term} className="text-xs leading-normal text-muted-foreground">
                <span className="font-mono uppercase tracking-widest text-accent">
                  {item.term}
                </span>{" "}
                — {item.hint}
              </li>
            ))}
          </ul>
          <p className="mt-3 text-xs leading-normal text-muted-foreground">
            Brighter cells = more imaging studies for that modality in that cancer
            collection. Compare the heatmap pattern to the blue prevalence strip: when
            high mutation burden aligns with rich CT/MR coverage, radiogenomic trial
            design is feasible.
          </p>
        </div>
      )}

      {title && (
        <p className="mb-3 text-xs text-muted-foreground">{title}</p>
      )}

      <div className="overflow-x-auto">
        <svg
          viewBox={`0 0 ${W} ${H}`}
          width={W}
          className="max-w-full"
          role="img"
          aria-label="Radiogenomic correlation matrix"
        >
          {/* Axis titles — one-word / short phrases on the chart itself. */}
          <text
            x={labelL + gridW / 2}
            y={14}
            textAnchor="middle"
            fontSize={9}
            fontFamily="JetBrains Mono"
            fill="#737373"
            letterSpacing="0.08em"
          >
            CANCER TYPES
          </text>
          <text
            x={12}
            y={labelT + gridH / 2}
            textAnchor="middle"
            fontSize={9}
            fontFamily="JetBrains Mono"
            fill="#737373"
            letterSpacing="0.08em"
            transform={`rotate(-90 12 ${labelT + gridH / 2})`}
          >
            MODALITIES
          </text>
          <text
            x={labelL + gridW + 6}
            y={labelT + 12}
            textAnchor="start"
            fontSize={8}
            fontFamily="JetBrains Mono"
            fill="#FF3D00"
          >
            studies
          </text>

          {/* Cancer-type column labels (rotated). */}
          {cancers.map((c, j) => {
            const x = labelL + j * cell + cell / 2;
            return (
              <text
                key={`col-${j}`}
                x={x}
                y={labelT - 8}
                transform={`rotate(-40 ${x} ${labelT - 8})`}
                textAnchor="start"
                fontSize={10}
                fontFamily="JetBrains Mono"
                fill="#A3A3A3"
              >
                {c.length > 20 ? c.slice(0, 19) + "…" : c}
              </text>
            );
          })}

          {/* Rows: modality label + cells. */}
          {modalities.map((mod, i) => (
            <g key={`row-${i}`}>
              <text
                x={labelL - 10}
                y={labelT + i * cell + cell / 2 + 4}
                textAnchor="end"
                fontSize={11}
                fontFamily="JetBrains Mono"
                fill="#FAFAFA"
              >
                {mod}
              </text>
              {cancers.map((_, j) => {
                const v = Number(z[i]?.[j] ?? 0);
                const x = labelL + j * cell;
                const y = labelT + i * cell;
                const t = v / max;
                return (
                  <g key={`cell-${i}-${j}`}>
                    <rect
                      x={x + 1}
                      y={y + 1}
                      width={cell - 2}
                      height={cell - 2}
                      fill={fill(v)}
                      stroke="#0A0A0A"
                      strokeWidth={1}
                    />
                    <text
                      x={x + cell / 2}
                      y={y + cell / 2 + 3}
                      textAnchor="middle"
                      fontSize={9}
                      fontFamily="JetBrains Mono"
                      fill={t > 0.55 ? "#0A0A0A" : "#737373"}
                    >
                      {v > 0 ? v : ""}
                    </text>
                  </g>
                );
              })}
            </g>
          ))}

          {/* Mutation-prevalence strip under each cancer column. */}
          {prevalence.length > 0 && (
            <>
              <text
                x={labelL - 10}
                y={labelT + gridH + prevH / 2 + 10}
                textAnchor="end"
                fontSize={8}
                fontFamily="JetBrains Mono"
                fill="#00C8FF"
              >
                prev%
              </text>
              <text
                x={labelL - 10}
                y={labelT + gridH + prevH / 2 + 22}
                textAnchor="end"
                fontSize={7}
                fontFamily="JetBrains Mono"
                fill="#737373"
              >
                PanCancer
              </text>
              {cancers.map((_, j) => {
                const p = Number(prevalence[j] ?? 0);
                const h = (p / maxPrev) * prevH;
                const x = labelL + j * cell;
                const y = labelT + gridH + 8 + (prevH - h);
                return (
                  <g key={`prev-${j}`}>
                    <rect
                      x={x + cell * 0.2}
                      y={y}
                      width={cell * 0.6}
                      height={Math.max(1, h)}
                      fill="#00C8FF"
                    />
                    <text
                      x={x + cell / 2}
                      y={labelT + gridH + 8 + prevH + 12}
                      textAnchor="middle"
                      fontSize={8}
                      fontFamily="JetBrains Mono"
                      fill="#737373"
                    >
                      {p}
                    </text>
                  </g>
                );
              })}
            </>
          )}
        </svg>
      </div>

      <div className="mt-3 flex flex-wrap gap-2">
        {MATRIX_LEGEND.map((item) => (
          <span
            key={item.term}
            className="border border-border px-2 py-1 font-mono text-[9px] uppercase tracking-widest text-muted-foreground"
            title={item.hint}
          >
            <span className="text-foreground">{item.term}</span>
            <span className="mx-1 text-border">·</span>
            {item.hint.split(" · ")[0]}
          </span>
        ))}
      </div>

      {archetypes.length > 0 && (
        <div className="mt-4 border-t border-border pt-4">
          <div className="mb-1 flex flex-wrap items-center gap-2">
            <span className="label-mono">Radiogenomic archetypes</span>
            <span className="font-mono text-[10px] uppercase tracking-widest text-support">
              k-means · unsupervised
            </span>
          </div>
          <p className="mb-3 text-xs text-muted-foreground">
            Cancers grouped by shared imaging + mutation patterns — e.g. CT-dominant,
            mutation-high.
          </p>
          <div className="grid gap-3 sm:grid-cols-3">
            {archetypes.map((a, i) => (
              <div key={a.label + i} className="border border-border bg-muted/10 p-3">
                <div className="flex items-baseline justify-between">
                  <span className="font-mono text-[10px] uppercase tracking-widest text-accent">
                    Archetype {String.fromCharCode(65 + i)}
                  </span>
                  <span className="font-mono text-[10px] text-muted-foreground">
                    {a.avgPrevalencePct}% mut
                  </span>
                </div>
                <p className="mt-1 text-sm font-semibold text-foreground">{a.label}</p>
                <p className="mt-1 text-xs leading-snug text-muted-foreground">
                  {a.members.join(", ")}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}
    </motion.div>
  );
}
