import type { PlotlyFigure } from "../../lib/types";

/**
 * Renders a CRAFT `generate_plotly_chart` figure as a lightweight SVG bar chart.
 * Reads the Plotly spec (data[0].x / data[0].y) so it stays compatible with the
 * live MCP output without pulling in the full plotly.js bundle. Dark theme only.
 */
export function RadiogenomicsChart({ figure }: { figure: PlotlyFigure }) {
  const trace = figure.data?.[0] as
    | { x?: (string | number)[]; y?: number[] }
    | undefined;
  const layout = (figure.layout ?? {}) as Record<string, any>;
  const xs = (trace?.x ?? []).map((v) => String(v));
  const ys = (trace?.y ?? []).map((v) => Number(v) || 0);
  if (!xs.length || !ys.length) return null;

  const title = String(layout.title ?? "");
  const yLabel = String(layout.yaxis?.title ?? "");
  const max = Math.max(...ys, 1);

  const W = 520;
  const H = 220;
  const padL = 44;
  const padB = 34;
  const padT = 12;
  const plotW = W - padL - 12;
  const plotH = H - padB - padT;
  const bw = plotW / xs.length;

  return (
    <div className="border border-border bg-background p-4">
      {title && (
        <div className="mb-2 font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
          {title}
        </div>
      )}
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="w-full"
        role="img"
        aria-label={title || "Radiogenomics chart"}
      >
        {[0, 0.5, 1].map((f) => {
          const y = padT + plotH * (1 - f);
          return (
            <g key={f}>
              <line x1={padL} y1={y} x2={W - 12} y2={y} stroke="#262626" strokeWidth={1} />
              <text
                x={padL - 6}
                y={y + 3}
                textAnchor="end"
                fontSize={9}
                fontFamily="JetBrains Mono"
                fill="#737373"
              >
                {Math.round(max * f)}
              </text>
            </g>
          );
        })}
        {xs.map((label, i) => {
          const h = (ys[i] / max) * plotH;
          const x = padL + i * bw + bw * 0.18;
          const y = padT + (plotH - h);
          return (
            <g key={label + i}>
              <rect
                x={x}
                y={y}
                width={bw * 0.64}
                height={Math.max(1, h)}
                fill="#FF3D00"
              />
              <text
                x={x + bw * 0.32}
                y={y - 4}
                textAnchor="middle"
                fontSize={9}
                fontFamily="JetBrains Mono"
                fill="#FAFAFA"
              >
                {ys[i]}
              </text>
              <text
                x={x + bw * 0.32}
                y={H - padB + 14}
                textAnchor="middle"
                fontSize={9}
                fontFamily="JetBrains Mono"
                fill="#737373"
              >
                {label}
              </text>
            </g>
          );
        })}
      </svg>
      {yLabel && (
        <div className="mt-1 text-right font-mono text-[9px] uppercase tracking-widest text-muted-foreground">
          {yLabel}
        </div>
      )}
    </div>
  );
}
