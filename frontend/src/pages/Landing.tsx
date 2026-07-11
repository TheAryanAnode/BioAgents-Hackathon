import { useState } from "react";
import { motion } from "framer-motion";
import { ArrowRight } from "lucide-react";
import { Input } from "../components/ui/Input";
import { Button } from "../components/ui/Button";
import { SynthesisLogo } from "../components/ui/SynthesisLogo";

const EXAMPLES = [
  "autism genomics",
  "GLP-1 and neuroinflammation",
  "tau propagation in Alzheimer's",
  "KRAS G12C resistance",
];

export function Landing({
  onStart,
  geminiLive,
}: {
  onStart: (q: string) => void;
  geminiLive: boolean;
}) {
  const [value, setValue] = useState("");

  const submit = (q: string) => {
    const trimmed = q.trim();
    if (trimmed) onStart(trimmed);
  };

  return (
    <div className="relative flex min-h-screen flex-col justify-center px-6 py-20 md:px-12 lg:px-16">
      <div className="pointer-events-none absolute right-4 top-24 -z-10 select-none font-mono text-[18vw] leading-none text-muted opacity-40 md:text-[14vw]">
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
            <span className="label-mono">Track 02 — Autonomous Research</span>
          </div>

          <h1 className="max-w-5xl text-balance font-sans text-5xl font-extrabold leading-none tracking-tighter md:text-7xl lg:text-8xl">
            SYNTHESIZE
            <br />
            THE <span className="text-accent">UNKNOWN</span>
          </h1>

          <p className="mt-8 max-w-2xl text-lg leading-normal text-muted-foreground md:text-xl">
            An autonomous agent that ingests scientific literature, maps it into a
            living knowledge graph, generates novel hypotheses, and surfaces the
            commercial opportunities experts are structurally unable to see.
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
            className={`h-2 w-2 ${geminiLive ? "bg-support" : "bg-muted-foreground"}`}
          />
          <span className="label-mono">
            {geminiLive
              ? "Gemini on demand — chat, hypothesis click, & reports only"
              : "Demo mode — deterministic synthesis (no API key)"}
          </span>
        </motion.div>
      </div>
    </div>
  );
}
