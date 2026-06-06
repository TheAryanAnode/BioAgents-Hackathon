import type { HypothesisReport } from "../../lib/types";
import { formatNumber, formatUsd } from "../../lib/utils";
import { sortReportSections } from "../../lib/reportPdf";

/** Off-screen print layout — source for html2canvas PDF generation. */
export function ReportPrintSheet({
  report,
}: {
  report: HypothesisReport;
}) {
  const metrics = report.keyMetrics ?? {};
  const sections = sortReportSections(report.sections);

  return (
    <div
      className="report-print-sheet"
      style={{
        width: 816,
        padding: "48px 54px",
        background: "#ffffff",
        color: "#0a0a0a",
        fontFamily: '"Helvetica Neue", Helvetica, Arial, sans-serif',
        fontSize: 11,
        lineHeight: 1.45,
        letterSpacing: "normal",
        wordSpacing: "normal",
      }}
    >
      <header style={{ marginBottom: 20, borderBottom: "2px solid #FF3D00", paddingBottom: 16 }}>
        <p
          style={{
            margin: 0,
            fontSize: 9,
            letterSpacing: "0.12em",
            textTransform: "uppercase",
            color: "#737373",
          }}
        >
          SynthesisOS Investment Brief
        </p>
        <h1 style={{ margin: "8px 0 0", fontSize: 20, fontWeight: 700, lineHeight: 1.25 }}>
          {report.title}
        </h1>
        <p style={{ margin: "10px 0 0", fontSize: 10, color: "#525252" }}>
          Generated {new Date(report.generatedAt).toLocaleString()} ·{" "}
          {report.timelineMonths ?? 18} month program · Funding{" "}
          {formatUsd(report.fundingEstimateUsd)} · {formatNumber(report.patientPopulation)} patients
        </p>
      </header>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(3, 1fr)",
          gap: 8,
          marginBottom: 24,
        }}
      >
        {[
          ["Funding", formatUsd(report.fundingEstimateUsd)],
          ["Patients", formatNumber(report.patientPopulation)],
          ["Confidence", metrics.confidence ?? "—"],
          ["ROI", metrics.roi ?? "—"],
          ["Timeline", metrics.timeline ?? `${report.timelineMonths ?? 18} mo`],
        ].map(([label, value]) => (
          <div
            key={label}
            style={{ border: "1px solid #e5e5e5", padding: "8px 10px" }}
          >
            <div style={{ fontSize: 8, textTransform: "uppercase", letterSpacing: "0.1em", color: "#737373" }}>
              {label}
            </div>
            <div style={{ marginTop: 4, fontSize: 13, fontWeight: 700 }}>{value}</div>
          </div>
        ))}
      </div>

      {sections.map((section) => {
        const isGaps = section.id === "gaps";
        return (
          <section
            key={section.id}
            style={{
              marginBottom: 18,
              pageBreakInside: "avoid",
              ...(isGaps
                ? {
                    border: "1px solid #FF3D00",
                    padding: "12px 14px",
                    background: "#FFF8F6",
                  }
                : {}),
            }}
          >
            <h2
              style={{
                margin: "0 0 6px",
                fontSize: 11,
                fontWeight: 700,
                textTransform: "uppercase",
                letterSpacing: "0.08em",
                color: "#FF3D00",
              }}
            >
              {section.title}
            </h2>
            {section.highlight && (
              <p style={{ margin: "0 0 6px", fontSize: 10, fontWeight: 600, color: "#FF3D00" }}>
                {section.highlight}
              </p>
            )}
            <p style={{ margin: "0 0 8px", fontSize: 11, color: "#171717" }}>{section.body}</p>
            {section.bullets && section.bullets.length > 0 && (
              <ul style={{ margin: 0, paddingLeft: 18, fontSize: 10, color: "#404040" }}>
                {section.bullets.map((b, i) => (
                  <li key={i} style={{ marginBottom: 4 }}>
                    {b}
                  </li>
                ))}
              </ul>
            )}
          </section>
        );
      })}

      {report.references && report.references.length > 0 && (
        <section style={{ marginTop: 20 }}>
          <h2
            style={{
              margin: "0 0 8px",
              fontSize: 11,
              fontWeight: 700,
              textTransform: "uppercase",
              letterSpacing: "0.08em",
            }}
          >
            References
          </h2>
          <ul style={{ margin: 0, paddingLeft: 18, fontSize: 9, color: "#404040" }}>
            {report.references.map((ref, i) => (
              <li key={i} style={{ marginBottom: 6 }}>
                <strong>[{ref.stance ?? "neutral"}]</strong> {ref.title}
                {ref.url ? ` — ${ref.url}` : ""}
              </li>
            ))}
          </ul>
        </section>
      )}

      <footer
        style={{
          marginTop: 28,
          paddingTop: 12,
          borderTop: "1px solid #e5e5e5",
          fontSize: 8,
          color: "#737373",
        }}
      >
        SynthesisOS — Autonomous Research Brief · Confidential draft for funders & clinical partners
      </footer>
    </div>
  );
}
