/** Shared canvas helpers for force-graph node glow and link styling. */

export const GRAPH_COLORS = {
  accent: "#FF3D00",
  fg: "#FAFAFA",
  support: "#34D399",
  contradict: "#F87171",
  muted: "#737373",
} as const;

export function drawNodeGlow(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  r: number,
  color: string,
  scale: number,
  intensity: "low" | "medium" | "high" = "medium",
) {
  const blur = { low: 8, medium: 14, high: 22 }[intensity] / scale;
  ctx.save();
  ctx.shadowBlur = blur;
  ctx.shadowColor = color;
  ctx.globalAlpha = 0.55;
  ctx.beginPath();
  ctx.arc(x, y, r + 1.5, 0, 2 * Math.PI);
  ctx.fillStyle = color;
  ctx.fill();
  ctx.restore();
}

export function drawNodeCore(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  r: number,
  color: string,
  alpha = 1,
) {
  ctx.save();
  ctx.globalAlpha = alpha;
  ctx.beginPath();
  ctx.arc(x, y, r, 0, 2 * Math.PI);
  ctx.fillStyle = color;
  ctx.fill();
  ctx.restore();
}

export function linkEndpointId(link: { source: unknown; target: unknown }, end: "source" | "target") {
  const node = end === "source" ? link.source : link.target;
  return typeof node === "object" && node !== null && "id" in node
    ? (node as { id: string }).id
    : String(node);
}
