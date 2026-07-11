import { useState } from "react";
import { motion } from "framer-motion";
import { ArrowRight } from "lucide-react";
import { Input } from "../components/ui/Input";
import { Button } from "../components/ui/Button";
import { SynthesisLogo } from "../components/ui/SynthesisLogo";

const EXAMPLES = [
  "KRAS G12C lung cancer resistance",
  "CDH1 breast cancer invasion",
  "GLP-1 and neuroinflammation",
  "tau propagation in Alzheimer's",
];

export function Landing({
  onStart,
  llmLive,
}: {
  onStart: (q: string) => void;
  llmLive: boolean;
}) {
  const [value, setValue] = useState("");

  const submit = (q: string) => {
    const trimmed = q.trim();
    if (trimmed) onStart(trimmed);
  };

  return (
    <div className="relative flex h-full min-h-0 flex-col justify-start overflow-y-auto px-6 pb-20 pt-10 md:px-12 md:pt-14 lg:px-16">
      <div className="pointer-events-none absolute right-4 top-32 -z-10 select-none font-mono text-[18vw] leading-none text-muted opacity-30 md:text-[14vw]">
        01
      </div>

      <div className="mx-auto w-full max-w-container">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: [0.25, 0, 0, 1] }}
        >
          <div className="mb-10">
            <SynthesisLogo size="hero" />
          </div>

          <div className="mb-6 flex items-center gap-3">
            <span className="h-1 w-16 bg-accent" />
            <span className="label-mono">Emergence Hackathon — Autonomous Investigation</span>
          </div>

          <h1 className="max-w-5xl text-balance font-sans text-4xl font-extrabold leading-tight tracking-tighter sm:text-5xl md:text-6xl lg:text-7xl">
            You tell us topics.
            <br />
            We find <span className="text-accent">insights</span>.
          </h1>

          <p className="mt-8 max-w-2xl text-lg leading-normal text-muted-foreground md:text-xl">
            Literature finds the hypothesis. CRAFT investigates the patients. An
            autonomous agent maps the literature into a knowledge graph, finds a
            structural gap, then interrogates PanCancer genomics and IDC imaging to
            deliver an actionable radiogenomics finding — with full SQL provenance.
          </p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.12, ease: [0.25, 0, 0, 1] }}
          className="mt-12 max-w-3xl"
        >
          <form
            onSubmit={(e) => {
              e.preventDefault();
              submit(value);
            }}
            className="flex flex-col gap-4 sm:flex-row"
          >
            <Input
              autoFocus
              placeholder="Enter a research domain — e.g. autism genomics"
              value={value}
              onChange={(e) => setValue(e.target.value)}
              aria-label="Research query"
            />
            <Button type="submit" size="lg" className="shrink-0">
              Synthesize <ArrowRight size={16} strokeWidth={1.5} />
            </Button>
          </form>

          <div className="mt-8 flex flex-wrap items-center gap-x-2 gap-y-3">
            <span className="label-mono mr-2">Try</span>
            {EXAMPLES.map((ex) => (
              <Button
                key={ex}
                variant="ghost"
                size="sm"
                type="button"
                onClick={() => {
                  setValue(ex);
                  submit(ex);
                }}
              >
                {ex}
              </Button>
            ))}
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.5, delay: 0.3 }}
          className="mt-20 flex items-center gap-2 border-t border-border pt-6"
        >
          <span
            className={`h-2 w-2 ${llmLive ? "bg-support" : "bg-muted-foreground"}`}
          />
          <span className="label-mono">
            {llmLive
              ? "Nebius Token Factory — chat, hypothesis click, & reports"
              : "Demo mode — deterministic synthesis (no API key)"}
          </span>
        </motion.div>
      </div>
    </div>
  );
}
