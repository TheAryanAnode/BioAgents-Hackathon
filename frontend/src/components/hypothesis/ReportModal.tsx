import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Download, Loader2, X } from "lucide-react";
import type { Hypothesis, HypothesisReport } from "../../lib/types";
import {
  htmlElementToPdfBlob,
  REPORT_PDF_PREVIEW_MAX_WIDTH,
  REPORT_PDF_PREVIEW_MIN_WIDTH,
  sortReportSections,
} from "../../lib/reportPdf";
import { formatNumber, formatUsd } from "../../lib/utils";
import { Button } from "../ui/Button";
import { Badge, Card } from "../ui/Card";
import { PdfCanvasPreview } from "./PdfCanvasPreview";
import { ReportPrintSheet } from "./ReportPrintSheet";
import { ScientificWhiteboard } from "./ScientificWhiteboard";

export function ReportModal({
  report,
  hypothesis,
  onClose,
}: {
  report: HypothesisReport;
  hypothesis?: Hypothesis;
  onClose: () => void;
}) {
  const printRef = useRef<HTMLDivElement>(null);
  const previewPaneRef = useRef<HTMLDivElement>(null);
  const [pdfBlob, setPdfBlob] = useState<Blob | null>(null);
  const [pdfBusy, setPdfBusy] = useState(true);
  const [previewWidth, setPreviewWidth] = useState(500);

  // Measure preview pane once on mount — avoid ResizeObserver loops.
  useEffect(() => {
    const pane = previewPaneRef.current;
    if (!pane) return;
    const w = pane.clientWidth - 32;
    setPreviewWidth(
      Math.min(REPORT_PDF_PREVIEW_MAX_WIDTH, Math.max(REPORT_PDF_PREVIEW_MIN_WIDTH, w)),
    );
  }, []);

  // Generate PDF blob once from the off-screen print sheet.
  useEffect(() => {
    const el = printRef.current;
    if (!el) return;

    let cancelled = false;
    setPdfBusy(true);

    const timer = window.setTimeout(() => {
      htmlElementToPdfBlob(el)
        .then((blob) => {
          if (!cancelled) {
            setPdfBlob(blob);
            setPdfBusy(false);
          }
        })
        .catch(() => {
          if (!cancelled) setPdfBusy(false);
        });
    }, 80);

    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [report]);

  const download = () => {
    if (!pdfBlob) return;
    const url = URL.createObjectURL(pdfBlob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `synthesisos-brief-${report.hypothesisId}.pdf`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const metrics = report.keyMetrics ?? {};
  const sections = sortReportSections(report.sections);

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 flex items-center justify-center bg-background/95 p-4 backdrop-blur"
        onClick={onClose}
      >
        {/* Off-screen print source for PDF generation */}
        <div
          aria-hidden
          style={{
            position: "fixed",
            left: -10000,
            top: 0,
            pointerEvents: "none",
            opacity: 0,
          }}
        >
          <div ref={printRef}>
            <ReportPrintSheet report={report} />
          </div>
        </div>

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
              <Button size="sm" onClick={download} disabled={!pdfBlob || pdfBusy}>
                {pdfBusy ? (
                  <>
                    <Loader2 size={14} className="animate-spin" /> Building PDF
                  </>
                ) : (
                  <>
                    <Download size={14} strokeWidth={1.5} /> Download PDF
                  </>
                )}
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

          <div className="grid min-h-0 flex-1 grid-cols-1 overflow-hidden lg:grid-cols-2">
            <div className="overflow-y-auto border-b border-border p-6 lg:border-b-0 lg:border-r">
              <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-3">
                <MetricCard label="Funding" value={formatUsd(report.fundingEstimateUsd)} accent />
                <MetricCard label="Patients" value={formatNumber(report.patientPopulation)} />
                <MetricCard label="Confidence" value={metrics.confidence ?? "—"} />
                <MetricCard label="ROI" value={metrics.roi ?? "—"} />
                <MetricCard label="Timeline" value={metrics.timeline ?? `${report.timelineMonths ?? 18} mo`} />
              </div>

              {hypothesis && (
                <div className="mb-6">
                  <ScientificWhiteboard hypothesis={hypothesis} />
                </div>
              )}

              <div className="flex flex-col gap-6">
                {sections.map((section) => (
                  <Card
                    key={section.id}
                    className={`p-5 ${section.id === "gaps" ? "border-accent bg-accent/5" : ""}`}
                    accentTop={section.id === "gaps"}
                  >
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
              </div>
              <div ref={previewPaneRef} className="relative flex-1 overflow-auto bg-[#525659] p-4">
                {pdfBusy && (
                  <div className="flex h-full min-h-[280px] items-center justify-center gap-2">
                    <Loader2 size={16} className="animate-spin text-muted-foreground" />
                    <span className="label-mono text-muted-foreground">Rendering PDF…</span>
                  </div>
                )}
                {!pdfBusy && pdfBlob && (
                  <PdfCanvasPreview blob={pdfBlob} width={previewWidth} />
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
