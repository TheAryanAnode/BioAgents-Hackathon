import { useEffect, useRef, useState } from "react";
import * as pdfjs from "pdfjs-dist";
import pdfjsWorker from "pdfjs-dist/build/pdf.worker.min.mjs?url";

pdfjs.GlobalWorkerOptions.workerSrc = pdfjsWorker;

const PAGE_W_PT = 612;

type PagePreview = {
  pageNumber: number;
  dataUrl: string;
  cssWidth: number;
  cssHeight: number;
};

export function PdfCanvasPreview({
  blob,
  width,
}: {
  blob: Blob;
  width: number;
}) {
  const [pages, setPages] = useState<PagePreview[]>([]);
  const [error, setError] = useState<string | null>(null);
  const generationRef = useRef(0);
  const prevBlobRef = useRef<Blob | null>(null);

  useEffect(() => {
    if (blob === prevBlobRef.current && pages.length > 0) return;
    prevBlobRef.current = blob;

    const generation = ++generationRef.current;
    setError(null);

    (async () => {
      try {
        const data = await blob.arrayBuffer();
        const pdf = await pdfjs.getDocument({ data }).promise;
        const dpr = Math.min(window.devicePixelRatio || 1, 2.5);
        const displayScale = width / PAGE_W_PT;
        const rendered: PagePreview[] = [];

        for (let pageNumber = 1; pageNumber <= pdf.numPages; pageNumber++) {
          if (generation !== generationRef.current) return;

          const page = await pdf.getPage(pageNumber);
          const viewport = page.getViewport({ scale: displayScale });

          const canvas = document.createElement("canvas");
          const ctx = canvas.getContext("2d");
          if (!ctx) continue;

          canvas.width = Math.floor(viewport.width * dpr);
          canvas.height = Math.floor(viewport.height * dpr);

          ctx.imageSmoothingEnabled = true;
          ctx.imageSmoothingQuality = "high";

          await page.render({
            canvasContext: ctx,
            viewport,
            transform: dpr !== 1 ? [dpr, 0, 0, dpr, 0, 0] : undefined,
            canvas,
          }).promise;

          rendered.push({
            pageNumber,
            dataUrl: canvas.toDataURL("image/png"),
            cssWidth: Math.floor(viewport.width),
            cssHeight: Math.floor(viewport.height),
          });
        }

        if (generation !== generationRef.current) return;
        setPages(rendered);
      } catch (e: unknown) {
        if (generation !== generationRef.current) return;
        setError(e instanceof Error ? e.message : "Preview failed");
      }
    })();

    return () => {
      generationRef.current += 1;
    };
  }, [blob, width]);

  if (error) {
    return <p className="text-center text-sm text-muted-foreground">{error}</p>;
  }

  if (pages.length === 0) {
    return (
      <p className="py-8 text-center font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
        Rendering preview…
      </p>
    );
  }

  return (
    <div className="flex w-full flex-col items-center gap-4">
      {pages.map((p) => (
        <div key={p.pageNumber} className="flex flex-col items-center gap-1">
          <span className="font-mono text-[9px] uppercase tracking-widest text-muted-foreground/80">
            Page {p.pageNumber}
          </span>
          <img
            src={p.dataUrl}
            alt={`Report page ${p.pageNumber}`}
            className="border border-border bg-white shadow-lg"
            style={{
              width: p.cssWidth,
              height: p.cssHeight,
              display: "block",
            }}
          />
        </div>
      ))}
    </div>
  );
}
