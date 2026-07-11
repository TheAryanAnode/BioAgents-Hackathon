import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { HelpCircle, Loader2 } from "lucide-react";
import type { InvestigationPhase, InvestigationStep } from "../../lib/types";
import { CraftQueryCard } from "./CraftQueryCard";
import { cn } from "../../lib/utils";

const AGENT_LABEL: Record<string, string> = {
  craft_planner: "Planner",
  craft_pancancer: "PanCancer analyst",
  craft_imaging: "Imaging analyst",
  craft_radiogenomics: "Radiogenomics analyst",
  craft_synthesizer: "Synthesizer",
};

// Plain-language meaning of each CRAFT phase, shown in the explainer legend.
const PHASE_INFO: { id: InvestigationPhase; label: string; what: string }[] = [
  { id: "plan", label: "Plan", what: "The planner frames the sub-questions worth asking about this hypothesis." },
  { id: "term", label: "Resolve term", what: "Maps everyday wording to the exact database columns (e.g. gene symbol, DICOM modality)." },
  { id: "schema", label: "Search schema", what: "Finds which tables in PanCancer / IDC hold the answer — no hand-written SQL." },
  { id: "query", label: "Query", what: "Asks a question in plain English → CRAFT writes SQL → runs it on real patient data." },
  { id: "chart", label: "Chart", what: "Turns the returned rows into a figure (e.g. modality coverage)." },
  { id: "synthesis", label: "Synthesis", what: "Weighs genomics + imaging into one actionable, revised-confidence finding." },
];

const AGENT_PURPOSE: Record<string, string> = {
  craft_planner: "decides what to investigate",
  craft_pancancer: "checks the genomics (mutations, co-alteration, survival)",
  craft_imaging: "checks imaging feasibility (modalities, measurements)",
  craft_radiogenomics: "correlates imaging modalities with molecular subtypes across cancers, then clusters them into archetypes",
  craft_synthesizer: "combines everything into the finding",
};

/**
 * The investigation story: a numbered vertical timeline of every CRAFT tool
 * call, streamed live as the agents work. Steps fade up (Bold Typography motion:
 * fast, no bounce). Grouped by the agent that produced each step.
 */
export function InvestigationTimeline({
  steps,
  running,
}: {
  steps: InvestigationStep[];
  running: boolean;
}) {
  const [showHelp, setShowHelp] = useState(false);
  if (!steps.length && !running) return null;

  // Count steps per agent + queries run, so the header explains the "why" of N steps.
  const agentCounts = steps.reduce<Record<string, number>>((acc, s) => {
    acc[s.agent] = (acc[s.agent] ?? 0) + 1;
    return acc;
  }, {});
  const queryCount = steps.filter((s) => s.tool === "execute_query").length;
  const activeAgents = Object.keys(agentCounts);

  return (
    <div>
      <div className="mb-3 flex items-center gap-3">
        <span className="h-1 w-8 bg-accent" />
        <span className="label-mono">Investigation timeline</span>
        <span className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
          {steps.length} steps
        </span>
        <button
          onClick={() => setShowHelp((v) => !v)}
          className={cn(
            "flex items-center gap-1 font-mono text-[10px] uppercase tracking-widest transition-colors",
            showHelp ? "text-accent" : "text-muted-foreground hover:text-foreground",
          )}
        >
          <HelpCircle size={12} strokeWidth={1.5} /> What is this?
        </button>
        {running && (
          <span className="ml-auto flex items-center gap-1.5 text-accent">
            <Loader2 size={12} className="animate-spin" />
            <span className="font-mono text-[10px] uppercase tracking-widest">
              investigating
            </span>
          </span>
        )}
      </div>

      {/* Always-on one-liner so the trail is never a mystery. */}
      <p className="mb-3 text-sm leading-normal text-muted-foreground">
        This is the agent's reasoning trail — each entry is a single call to the
        CRAFT data layer. {activeAgents.length} specialist agent
        {activeAgents.length === 1 ? "" : "s"} ran{" "}
        <span className="text-foreground">{queryCount} live queries</span> against
        PanCancer genomics and IDC imaging to stress-test the hypothesis against real
        patient data (not just the literature).
      </p>

      {showHelp && (
        <div className="mb-4 border border-border bg-card/70 p-4 backdrop-blur">
          <div className="label-mono mb-2">The agents</div>
          <ul className="mb-4 space-y-1">
            {activeAgents.map((a) => (
              <li key={a} className="text-xs leading-normal text-muted-foreground">
                <span className="font-mono uppercase tracking-widest text-foreground">
                  {AGENT_LABEL[a] ?? a}
                </span>{" "}
                — {AGENT_PURPOSE[a] ?? "runs part of the investigation"} ({agentCounts[a]}{" "}
                step{agentCounts[a] === 1 ? "" : "s"})
              </li>
            ))}
          </ul>
          <div className="label-mono mb-2">What each phase means</div>
          <ul className="grid gap-1.5 sm:grid-cols-2">
            {PHASE_INFO.map((p) => (
              <li key={p.id} className="text-xs leading-normal text-muted-foreground">
                <span className="text-accent">{p.label}</span> — {p.what}
              </li>
            ))}
          </ul>
        </div>
      )}

      <ol className="relative flex flex-col gap-3 border-l border-border pl-6">
        <AnimatePresence initial={false}>
          {steps.map((step, i) => (
            <motion.li
              key={step.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, ease: [0.25, 0, 0, 1] }}
              className="relative"
            >
              <span className="absolute -left-[27px] top-3 h-1 w-4 bg-accent" />
              <div className="mb-1 flex items-center gap-2">
                <span className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
                  {String(i + 1).padStart(2, "0")}
                </span>
                <span className="font-mono text-[10px] uppercase tracking-widest text-foreground">
                  {AGENT_LABEL[step.agent] ?? step.agent}
                </span>
              </div>
              <CraftQueryCard step={step} />
            </motion.li>
          ))}
        </AnimatePresence>
        {running && (
          <li className="relative">
            <span className="absolute -left-[27px] top-3 h-1 w-4 animate-pulse bg-accent" />
            <div className="border border-dashed border-border p-3">
              <span className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
                Awaiting next CRAFT step…
              </span>
            </div>
          </li>
        )}
      </ol>
    </div>
  );
}
