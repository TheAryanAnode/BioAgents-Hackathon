import { useEffect, useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Download, X } from "lucide-react";
import type { HypothesisReport } from "../../lib/types";
import { reportPdfBlob, REPORT_PDF_PREVIEW } from "../../lib/reportPdf";
import { formatNumber, formatUsd } from "../../lib/utils";
import { Button } from "../ui/Button";
import { Badge, Card } from "../ui/Card";

export function ReportModal({
  report,
  onClose,
}: {
  report: HypothesisReport;
  onClose: () => void;
}) {
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);

  const pdfBlob = useMemo(() => reportPdfBlob(report), [report]);

  useEffect(() => {
    const url = URL.createObjectURL(pdfBlob);
    setPdfUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [pdfBlob]);

  const download = () => {
    const url = URL.createObjectURL(pdfBlob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `synthesisos-brief-${report.hypothesisId}.pdf`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const metrics = report.keyMetrics ?? {};

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 flex items-center justify-center bg-background/95 p-4 backdrop-blur"
        onClick={onClose}
      >
        <motion.div
          initial={{ y: 16, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: 16, opacity: 0 }}
          className="flex max-h-[94vh] w-full max-w-6xl flex-col border border-border bg-card"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="flex flex-wrap items-start justify-between gap-4 border-b border-border px-6 py-4">
            <div>
              <div className="mb-2 flex items-center gap-3">
                <span className="h-1 w-10 bg-accent" />
                <span className="label-mono">Investment brief</span>
              </div>
              <h2 className="max-w-2xl text-balance text-xl font-bold tracking-tight md:text-2xl">
                {report.title}
              </h2>
              <p className="mt-2 font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
                {new Date(report.generatedAt).toLocaleString()} ·{" "}
                {report.timelineMonths ?? 18} month program
              </p>
            </div>
            <div className="flex items-center gap-3">
              <Button size="sm" onClick={download}>
                <Download size={14} strokeWidth={1.5} /> Download PDF
              </Button>
              <button
                onClick={onClose}
                className="text-muted-foreground hover:text-foreground"
                aria-label="Close"
              >
                <X size={20} strokeWidth={1.5} />
              </button>
            </div>
          </div>

          <div className="grid flex-1 min-h-0 grid-cols-1 overflow-hidden lg:grid-cols-2">
            <div className="overflow-y-auto border-b border-border p-6 lg:border-b-0 lg:border-r">
              <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-3">
                <MetricCard label="Funding" value={formatUsd(report.fundingEstimateUsd)} accent />
                <MetricCard label="Patients" value={formatNumber(report.patientPopulation)} />
                <MetricCard label="Confidence" value={metrics.confidence ?? "—"} />
                <MetricCard label="ROI" value={metrics.roi ?? "—"} />
                <MetricCard label="Timeline" value={metrics.timeline ?? `${report.timelineMonths ?? 18} mo`} />
              </div>

              <div className="flex flex-col gap-6">
                {report.sections.map((section) => (
                  <Card key={section.id} className="p-5">
                    <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                      <span className="label-mono">{section.title}</span>
                      {section.highlight && (
                        <Badge tone="accent">{section.highlight}</Badge>
                      )}
                    </div>
                    <p className="text-sm leading-relaxed text-foreground/90">{section.body}</p>
                    {section.bullets && section.bullets.length > 0 && (
                      <ul className="mt-4 flex flex-col gap-2 border-t border-border pt-4">
                        {section.bullets.map((b, i) => (
                          <li
                            key={i}
                            className="flex gap-2 text-sm leading-snug text-muted-foreground"
                          >
                            <span className="mt-1.5 h-1 w-1 shrink-0 bg-accent" />
                            <span>{b}</span>
                          </li>
                        ))}
                      </ul>
                    )}
                  </Card>
                ))}

                {report.references && report.references.length > 0 && (
                  <div>
                    <span className="label-mono">References</span>
                    <ul className="mt-3 flex flex-col gap-2">
                      {report.references.map((ref, i) => (
                        <li key={i} className="border border-border p-3 text-sm">
                          <span className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
                            {ref.stance ?? "neutral"}
                          </span>
                          <p className="mt-1 font-medium">{ref.title}</p>
                          {ref.url && (
                            <a
                              href={ref.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="mt-1 inline-block font-mono text-[10px] text-accent underline"
                            >
                              Open source ↗
                            </a>
                          )}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>

            <div className="flex min-h-[320px] flex-col bg-muted/20 lg:min-h-0">
              <div className="border-b border-border px-4 py-3">
                <span className="label-mono">PDF preview</span>
                <p className="mt-1 text-xs text-muted-foreground">
                  This is the document that will download when you click Download PDF.
                </p>
              </div>
              <div className="relative flex-1 overflow-auto bg-[#525659] p-4">
                {pdfUrl ? (
                  <div className="mx-auto" style={{ width: REPORT_PDF_PREVIEW.width }}>
                    <iframe
                      title="Report PDF preview"
                      src={`${pdfUrl}#toolbar=0&navpanes=0`}
                      className="border border-border bg-white shadow-lg"
                      style={{
                        width: REPORT_PDF_PREVIEW.width,
                        height: REPORT_PDF_PREVIEW.height,
                        display: "block",
                      }}
                    />
                  </div>
                ) : (
                  <div className="flex h-full items-center justify-center">
                    <span className="label-mono text-muted-foreground">Preparing preview…</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}

function MetricCard({
  label,
  value,
  accent,
}: {
  label: string;
  value: string;
  accent?: boolean;
}) {
  return (
    <div className="border border-border p-3">
      <div className="label-mono">{label}</div>
      <div className={`mt-1 text-lg font-bold tracking-tight ${accent ? "text-accent" : ""}`}>
        {value}
      </div>
    </div>
  );
}
