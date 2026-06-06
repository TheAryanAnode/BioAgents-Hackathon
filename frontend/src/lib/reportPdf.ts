import html2canvas from "html2canvas";
import { jsPDF } from "jspdf";

const PAGE_W_PT = 612;
const PAGE_H_PT = 792;

function captureScale(): number {
  const dpr = window.devicePixelRatio || 1;
  return Math.min(4, Math.max(3, dpr * 2));
}

/** Slice a tall canvas into letter-sized pages (top-to-bottom order). */
function canvasToPdf(canvas: HTMLCanvasElement): jsPDF {
  const pdf = new jsPDF({ unit: "pt", format: "letter", compress: false });
  const pageHeightPx = Math.floor((PAGE_H_PT / PAGE_W_PT) * canvas.width);
  let yPx = 0;
  let pageIndex = 0;

  while (yPx < canvas.height) {
    const sliceH = Math.min(pageHeightPx, canvas.height - yPx);
    const slice = document.createElement("canvas");
    slice.width = canvas.width;
    slice.height = sliceH;
    const sctx = slice.getContext("2d");
    if (!sctx) break;
    sctx.fillStyle = "#ffffff";
    sctx.fillRect(0, 0, slice.width, slice.height);
    sctx.drawImage(canvas, 0, yPx, canvas.width, sliceH, 0, 0, canvas.width, sliceH);

    const sliceHPt = (sliceH / canvas.width) * PAGE_W_PT;
    if (pageIndex > 0) pdf.addPage();
    pdf.addImage(
      slice.toDataURL("image/png"),
      "PNG",
      0,
      0,
      PAGE_W_PT,
      sliceHPt,
      undefined,
      "NONE",
    );
    yPx += pageHeightPx;
    pageIndex += 1;
  }

  return pdf;
}

/** Render a fixed-width HTML sheet to a multi-page letter PDF. */
export async function htmlElementToPdfBlob(element: HTMLElement): Promise<Blob> {
  const scale = captureScale();
  const canvas = await html2canvas(element, {
    scale,
    backgroundColor: "#ffffff",
    useCORS: true,
    logging: false,
    width: element.scrollWidth,
    height: element.scrollHeight,
    windowWidth: element.scrollWidth,
    imageTimeout: 0,
    removeContainer: true,
  });

  return canvasToPdf(canvas).output("blob");
}

export const REPORT_PRINT_WIDTH_PX = 816;
export const REPORT_PDF_PREVIEW_MIN_WIDTH = 420;
export const REPORT_PDF_PREVIEW_MAX_WIDTH = 560;

/** Preferred section order in PDF / print layout. */
export const REPORT_SECTION_ORDER = [
  "executive",
  "gaps",
  "mechanism",
  "clinical",
  "evidence",
  "population",
  "commercial",
  "validation",
  "budget",
  "regulatory",
  "risks",
  "kpis",
] as const;

export function sortReportSections<T extends { id: string }>(sections: T[]): T[] {
  const rank = new Map(REPORT_SECTION_ORDER.map((id, i) => [id, i]));
  return [...sections].sort(
    (a, b) => (rank.get(a.id as typeof REPORT_SECTION_ORDER[number]) ?? 99)
      - (rank.get(b.id as typeof REPORT_SECTION_ORDER[number]) ?? 99),
  );
}
