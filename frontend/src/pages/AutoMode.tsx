import { useMemo, useState } from "react";
import { motion } from "framer-motion";
import { ArrowRight, RefreshCw, Sparkles } from "lucide-react";
import { Button } from "../components/ui/Button";

/**
 * Auto mode — surfaces "hot" research fronts without spending any API credits.
 * Topics are drawn from a curated, locally-scored pool (deterministic), so this
 * screen is free to browse and reshuffle. Selecting one launches the normal
 * research pipeline (which is where CRAFT + Gemini spend happens, on demand).
 */

interface HotTopic {
  title: string;
  angle: string;
  tags: string[];
  heat: number; // 0-100 synthetic "momentum" score
}

const POOL: HotTopic[] = [
  { title: "KRAS G12C resistance in lung adenocarcinoma", angle: "Adaptive bypass signaling after covalent inhibitors — CT-measurable?", tags: ["oncology", "LUAD", "radiogenomics"], heat: 94 },
  { title: "CDH1 loss and lobular breast cancer invasion", angle: "E-cadherin dysfunction vs MRI-detectable growth patterns", tags: ["oncology", "BRCA", "imaging"], heat: 88 },
  { title: "GLP-1 agonists and neuroinflammation", angle: "Metabolic-neuro crosstalk beyond weight loss", tags: ["neuro", "metabolism"], heat: 91 },
  { title: "Tau propagation networks in Alzheimer's", angle: "Prion-like spread mapped to connectomics", tags: ["neuro", "imaging"], heat: 85 },
  { title: "STK11/KEAP1 co-mutation and immunotherapy escape", angle: "Cold-tumor phenotype across TCGA cohorts", tags: ["oncology", "immuno"], heat: 90 },
  { title: "Gut microbiome modulation of checkpoint response", angle: "Strain-level signatures predicting responders", tags: ["immuno", "microbiome"], heat: 83 },
  { title: "Senescence clearance as an anti-fibrotic strategy", angle: "Senolytics repurposed for organ fibrosis", tags: ["aging", "fibrosis"], heat: 79 },
  { title: "IDH1 mutant glioma metabolic dependencies", angle: "2-HG oncometabolite vulnerabilities + MR spectroscopy", tags: ["neuro-onc", "GBM"], heat: 82 },
  { title: "Radiogenomic links between imaging phenotype and subtype", angle: "Does modality coverage track molecular class?", tags: ["radiogenomics", "pan-cancer"], heat: 96 },
  { title: "PIK3CA signaling in HR+ breast cancer", angle: "Resistance to endocrine therapy and co-alterations", tags: ["oncology", "BRCA"], heat: 80 },
  { title: "Ferroptosis induction in therapy-resistant tumors", angle: "Lipid peroxidation as a synthetic-lethal axis", tags: ["oncology", "cell death"], heat: 78 },
  { title: "Circadian disruption and metabolic disease", angle: "Clock-gene control of insulin sensitivity", tags: ["metabolism", "chronobiology"], heat: 74 },
];

export function AutoMode({
  onStart,
  geminiLive,
}: {
  onStart: (q: string) => void;
  geminiLive: boolean;
}) {
  const [seed, setSeed] = useState(0);

  const topics = useMemo(() => {
    // Deterministic rotation: sort by heat, then rotate the window by `seed`.
    const sorted = [...POOL].sort((a, b) => b.heat - a.heat);
    const n = sorted.length;
    const start = (seed * 2) % n;
    return Array.from({ length: 6 }, (_, i) => sorted[(start + i) % n]);
  }, [seed]);

  return (
    <div className="relative h-full overflow-y-auto px-6 py-12 md:px-12 lg:px-16">
      <div className="pointer-events-none absolute right-6 top-16 -z-10 select-none font-mono text-[16vw] leading-none text-muted opacity-25 md:text-[11vw]">
        AUTO
      </div>

      <div className="mx-auto w-full max-w-container">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: [0.25, 0, 0, 1] }}
        >
          <div className="mb-4 flex items-center gap-3">
            <span className="h-1 w-16 bg-accent" />
            <span className="label-mono">Auto — Hot Research Fronts</span>
          </div>
          <h1 className="max-w-4xl text-balance font-sans text-4xl font-extrabold leading-none tracking-tighter md:text-6xl">
            WHAT'S <span className="text-accent">HOT</span> RIGHT NOW
          </h1>
          <p className="mt-6 max-w-2xl text-base leading-normal text-muted-foreground md:text-lg">
            Auto-surfaced research fronts, scored by momentum. Pick one to launch the
            full pipeline — ingestion, knowledge graph, hypotheses, then CRAFT
            investigation on demand. Browsing here is free; no API credits are spent
            until you start a run.
          </p>

          <div className="mt-6 flex items-center gap-4">
            <Button size="sm" variant="ghost" onClick={() => setSeed((s) => s + 1)}>
              <RefreshCw size={14} strokeWidth={1.5} /> Reshuffle
            </Button>
            <span className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
              {geminiLive ? "Gemini on demand" : "Demo mode"} · locally generated
            </span>
          </div>
        </motion.div>

        <div className="mt-10 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {topics.map((t, i) => (
            <motion.button
              key={t.title}
              onClick={() => onStart(t.title)}
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: i * 0.05, ease: [0.25, 0, 0, 1] }}
              whileTap={{ y: 1 }}
              className="group relative flex flex-col border border-border bg-card/70 p-5 text-left backdrop-blur transition-colors hover:border-accent"
            >
              <span className="absolute -top-px left-0 h-1 w-12 bg-accent opacity-0 transition-opacity group-hover:opacity-100" />
              <div className="flex items-center justify-between">
                <span className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
                  #{String(i + 1).padStart(2, "0")}
                </span>
                <HeatMeter value={t.heat} />
              </div>
              <h3 className="mt-3 text-lg font-bold leading-snug tracking-tight text-foreground">
                {t.title}
              </h3>
              <p className="mt-2 flex-1 text-sm leading-normal text-muted-foreground">
                {t.angle}
              </p>
              <div className="mt-4 flex flex-wrap items-center gap-2">
                {t.tags.map((tag) => (
                  <span
                    key={tag}
                    className="border border-border px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-widest text-muted-foreground"
                  >
                    {tag}
                  </span>
                ))}
                <span className="ml-auto flex items-center gap-1 font-mono text-[10px] uppercase tracking-widest text-accent opacity-0 transition-opacity group-hover:opacity-100">
                  Investigate <ArrowRight size={12} strokeWidth={1.5} />
                </span>
              </div>
            </motion.button>
          ))}
        </div>

        <div className="mt-10 flex items-center gap-2 border-t border-border pt-6">
          <Sparkles size={14} strokeWidth={1.5} className="text-accent" />
          <span className="label-mono">
            Momentum scores are heuristic — a starting point, not a ranking of truth
          </span>
        </div>
      </div>
    </div>
  );
}

function HeatMeter({ value }: { value: number }) {
  return (
    <div className="flex items-center gap-2">
      <div className="h-1 w-16 bg-muted">
        <div className="h-full bg-accent" style={{ width: `${value}%` }} />
      </div>
      <span className="font-mono text-[10px] text-foreground">{value}</span>
    </div>
  );
}
