import { jsPDF } from "jspdf";
import type { HypothesisReport } from "./types";

const MARGIN = 54;
const PAGE_W = 612; // letter width in pt
const PAGE_H = 792;
const CONTENT_W = PAGE_W - MARGIN * 2;
const FOOTER_Y = PAGE_H - 36;

/** Collapse odd whitespace / unicode that can confuse the PDF font engine. */
function cleanText(text: string): string {
  return text
    .replace(/\u00a0/g, " ")
    .replace(/[\u2018\u2019]/g, "'")
    .replace(/[\u201c\u201d]/g, '"')
    .replace(/[\u2013\u2014]/g, "-")
    .replace(/\s+/g, " ")
    .trim();
}

/**
 * Write wrapped text line-by-line. Passing a string[] to doc.text() can cause
 * horizontal stretching in some jsPDF builds — render one line at a time instead.
 */
function writeBlock(
  doc: jsPDF,
  text: string,
  x: number,
  y: number,
  maxW: number,
  lineH: number,
): number {
  const cleaned = cleanText(text);
  if (!cleaned) return y;

  const lines = doc.splitTextToSize(cleaned, maxW) as string[];
  for (const line of lines) {
    doc.text(line, x, y);
    y += lineH;
  }
  return y;
}

function ensureSpace(doc: jsPDF, y: number, need: number): number {
  if (y + need > FOOTER_Y) {
    doc.addPage();
    return MARGIN;
  }
  return y;
}

/** Build a print-ready PDF matching SynthesisOS report structure. */
export function buildReportPdf(report: HypothesisReport): jsPDF {
  const doc = new jsPDF({ unit: "pt", format: "letter", compress: true });
  let y = MARGIN;

  doc.setFont("helvetica", "bold");
  doc.setFontSize(15);
  y = writeBlock(doc, report.title, MARGIN, y, CONTENT_W, 18) + 10;

  doc.setFont("helvetica", "normal");
  doc.setFontSize(9);
  doc.setTextColor(80);
  const meta = [
    `Generated ${new Date(report.generatedAt).toLocaleDateString()}`,
    `Funding est. $${report.fundingEstimateUsd.toLocaleString()}`,
    `${report.patientPopulation.toLocaleString()} patients`,
    report.timelineMonths ? `${report.timelineMonths} month timeline` : "",
  ]
    .filter(Boolean)
    .join(" | ");
  y = writeBlock(doc, meta, MARGIN, y, CONTENT_W, 12) + 14;
  doc.setTextColor(0);

  if (report.keyMetrics && Object.keys(report.keyMetrics).length) {
    doc.setFont("helvetica", "bold");
    doc.setFontSize(8);
    const metricLine = Object.entries(report.keyMetrics)
      .map(([k, v]) => `${k.toUpperCase()}: ${v}`)
      .join("   ");
    y = writeBlock(doc, metricLine, MARGIN, y, CONTENT_W, 10) + 12;
  }

  for (const section of report.sections) {
    y = ensureSpace(doc, y, 56);
    doc.setFont("helvetica", "bold");
    doc.setFontSize(10.5);
    y = writeBlock(doc, section.title.toUpperCase(), MARGIN, y, CONTENT_W, 13) + 4;

    doc.setFont("helvetica", "normal");
    doc.setFontSize(10);
    y = writeBlock(doc, section.body, MARGIN, y, CONTENT_W, 13) + 6;

    if (section.bullets?.length) {
      doc.setFontSize(9.5);
      for (const b of section.bullets) {
        y = ensureSpace(doc, y, 18);
        y = writeBlock(doc, `- ${b}`, MARGIN + 10, y, CONTENT_W - 10, 12) + 2;
      }
    }

    if (section.highlight) {
      y = ensureSpace(doc, y, 14);
      doc.setFont("helvetica", "bold");
      doc.setFontSize(9);
      doc.setTextColor(180, 40, 0);
      y = writeBlock(doc, section.highlight, MARGIN, y, CONTENT_W, 12) + 4;
      doc.setTextColor(0);
    }
    y += 8;
  }

  if (report.references?.length) {
    y = ensureSpace(doc, y, 36);
    doc.setFont("helvetica", "bold");
    doc.setFontSize(10.5);
    y = writeBlock(doc, "REFERENCES", MARGIN, y, CONTENT_W, 13) + 4;
    doc.setFont("helvetica", "normal");
    doc.setFontSize(9);
    for (const ref of report.references) {
      y = ensureSpace(doc, y, 14);
      const line = `[${ref.stance ?? "neutral"}] ${ref.title}${ref.url ? ` - ${ref.url}` : ""}`;
      y = writeBlock(doc, line, MARGIN, y, CONTENT_W, 12) + 2;
    }
  }

  const pageCount = doc.getNumberOfPages();
  for (let p = 1; p <= pageCount; p++) {
    doc.setPage(p);
    doc.setFont("helvetica", "normal");
    doc.setFontSize(8);
    doc.setTextColor(120);
    doc.text("SynthesisOS - Autonomous Research Brief", MARGIN, FOOTER_Y);
    doc.text(`${p} / ${pageCount}`, PAGE_W - MARGIN, FOOTER_Y, { align: "right" });
  }
  doc.setTextColor(0);

  return doc;
}

export function reportPdfBlob(report: HypothesisReport): Blob {
  const doc = buildReportPdf(report);
  return doc.output("blob");
}

/** Letter-size preview dimensions (preserves 8.5:11 aspect ratio). */
export const REPORT_PDF_PREVIEW = {
  width: 480,
  height: Math.round(480 * (792 / 612)),
} as const;
