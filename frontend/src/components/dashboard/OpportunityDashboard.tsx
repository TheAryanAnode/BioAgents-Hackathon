import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useStore } from "../../stores/useStore";
import { Card } from "../ui/Card";
import { cn, formatNumber } from "../../lib/utils";
import type { Opportunity } from "../../lib/types";

const SERIES_COLORS = ["#FF3D00", "#FAFAFA", "#737373", "#34D399"];

export function OpportunityDashboard() {
  const dashboard = useStore((s) => s.dashboard);

  if (!dashboard) {
    return (
      <div className="flex h-full items-center justify-center">
        <span className="label-mono">commercial analysis pending…</span>
      </div>
    );
  }

  const { metrics, opportunities, trends, trendTopics, stratification } = dashboard;

  return (
    <div className="h-full overflow-y-auto px-6 py-8 md:px-10">
      <div className="mx-auto max-w-container">
        <div className="mb-2 flex items-center gap-3">
          <span className="h-1 w-10 bg-accent" />
          <span className="label-mono">Commercial Development Discovery</span>
        </div>
        <h1 className="text-balance text-4xl font-extrabold tracking-tighter md:text-5xl">
          Opportunity Dashboard
        </h1>

        <div className="mt-10 grid grid-cols-1 gap-px border border-border bg-border sm:grid-cols-2 lg:grid-cols-4">
          <MetricCard n="01" label="Opportunities" value={`${metrics.opportunities}`} />
          <MetricCard n="02" label="Avg Confidence" value={`${metrics.avgConfidence}%`} />
          <MetricCard
            n="03"
            label="Patient Population"
            value={formatNumber(metrics.patientPopulation)}
          />
          <MetricCard n="04" label="Projected ROI" value={`${metrics.projectedRoi}x`} accent />
        </div>

        <div className="mt-10 grid grid-cols-1 gap-6 lg:grid-cols-2">
          <Card>
            <span className="label-mono">Research activity vs time</span>
            <div className="mt-4 h-64">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={trends} margin={{ top: 5, right: 10, bottom: 0, left: -20 }}>
                  <CartesianGrid stroke="#262626" vertical={false} />
                  <XAxis dataKey="year" tick={axisTick} stroke="#262626" />
                  <YAxis tick={axisTick} stroke="#262626" />
                  <Tooltip contentStyle={tooltipStyle} />
                  {trendTopics.map((topic, i) => (
                    <Line
                      key={topic}
                      type="monotone"
                      dataKey={topic}
                      stroke={SERIES_COLORS[i % SERIES_COLORS.length]}
                      strokeWidth={i === 0 ? 2.5 : 1.5}
                      dot={false}
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </div>
            <div className="mt-3 flex flex-wrap gap-4">
              {trendTopics.map((t, i) => (
                <span key={t} className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
                  <span className="h-2 w-2" style={{ background: SERIES_COLORS[i % SERIES_COLORS.length] }} />
                  {t}
                </span>
              ))}
            </div>
          </Card>

          <Card>
            <span className="label-mono">Patient stratification</span>
            <div className="mt-4 h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={stratification}
                  layout="vertical"
                  margin={{ top: 5, right: 10, bottom: 0, left: 10 }}
                >
                  <CartesianGrid stroke="#262626" horizontal={false} />
                  <XAxis type="number" tick={axisTick} stroke="#262626" />
                  <YAxis
                    type="category"
                    dataKey="subgroup"
                    tick={{ ...axisTick, width: 120 }}
                    width={130}
                    stroke="#262626"
                  />
                  <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "#1A1A1A" }} />
                  <Bar dataKey="prevalence" fill="#FF3D00" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Card>
        </div>

        <div className="mt-10">
          <span className="label-mono">Opportunity ranking</span>
          <OpportunityTable opportunities={opportunities} />
        </div>
      </div>
    </div>
  );
}

const axisTick = { fill: "#737373", fontSize: 10, fontFamily: "JetBrains Mono" } as const;
const tooltipStyle = {
  background: "#0F0F0F",
  border: "1px solid #262626",
  borderRadius: 0,
  fontFamily: "JetBrains Mono",
  fontSize: 11,
} as const;

function MetricCard({
  n,
  label,
  value,
  accent,
}: {
  n: string;
  label: string;
  value: string;
  accent?: boolean;
}) {
  return (
    <div className="relative overflow-hidden bg-card p-6">
      <span className="pointer-events-none absolute -right-2 -top-6 select-none font-mono text-7xl text-muted opacity-50">
        {n}
      </span>
      <div className="relative">
        <div className="label-mono">{label}</div>
        <div className={cn("mt-3 text-4xl font-extrabold tracking-tight", accent && "text-accent")}>
          {value}
        </div>
      </div>
    </div>
  );
}

function OpportunityTable({ opportunities }: { opportunities: Opportunity[] }) {
  const ranked = [...opportunities].sort((a, b) => b.roiScore - a.roiScore);
  return (
    <div className="mt-4 overflow-x-auto border border-border">
      <table className="w-full min-w-[640px] border-collapse">
        <thead>
          <tr className="border-b border-border text-left font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
            <th className="px-4 py-3 font-normal">Opportunity</th>
            <th className="px-4 py-3 font-normal">Subgroup</th>
            <th className="px-4 py-3 font-normal text-right">Population</th>
            <th className="px-4 py-3 font-normal text-right">Unmet need</th>
            <th className="px-4 py-3 font-normal text-right">Whitespace</th>
            <th className="px-4 py-3 font-normal text-right">ROI score</th>
          </tr>
        </thead>
        <tbody>
          {ranked.map((o, i) => (
            <tr
              key={o.id}
              className={cn(
                "border-b border-border text-sm transition-colors hover:bg-muted",
                i === 0 && "bg-accent/5",
              )}
            >
              <td className="px-4 py-3">
                <span className="font-semibold">{o.title}</span>
              </td>
              <td className="px-4 py-3 text-muted-foreground">{o.subgroup}</td>
              <td className="px-4 py-3 text-right font-mono">{formatNumber(o.patientPopulation)}</td>
              <td className="px-4 py-3 text-right font-mono">{o.unmetNeed}</td>
              <td className="px-4 py-3 text-right font-mono">{100 - o.competition}</td>
              <td className="px-4 py-3 text-right">
                <span className={cn("font-mono font-bold", i === 0 ? "text-accent" : "text-foreground")}>
                  {o.roiScore}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
