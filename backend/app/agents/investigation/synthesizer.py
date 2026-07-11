"""Synthesizer — turns genomic + imaging evidence into an actionable finding.

Produces the tri-modal validation scorecard (literature / genomics / imaging),
a revised confidence, an explicit literature-vs-data divergence note, and a
Plotly chart of modality coverage. Uses one interactive Gemini call for the
narrative when available, with a deterministic fallback.
"""

from __future__ import annotations

import datetime as dt
import uuid

from app.agents.investigation.runner import InvestigationContext
from app.models.schemas import (
    EvidenceItem,
    InvestigationResult,
    InvestigationScore,
)

AGENT = "craft_synthesizer"


def _clamp(v: float, lo: int = 5, hi: int = 98) -> int:
    return max(lo, min(hi, int(round(v))))


def _genomics_score(m: dict) -> int:
    freq = m.get("mutationFreqPct", 0.0)
    co = m.get("coRatePct", 0.0)
    os_gap = m.get("osGapDays", 0)
    score = 40 + min(30, freq) + min(18, co * 2) + (10 if os_gap > 120 else 0)
    return _clamp(score)


def _imaging_score(m: dict) -> int:
    total = m.get("totalStudies", 0)
    meas = m.get("measurements", 0)
    score = 30 + min(40, total / 40) + min(25, meas / 4)
    return _clamp(score)


async def run(ic: InvestigationContext) -> InvestigationResult:
    m = ic.metrics
    gene_a, gene_b, cancer = ic.gene_a, ic.gene_b, ic.cancer_name

    # 1) Chart — modality distribution (answers the biotech challenge visually).
    modality_rows = m.get("modalityRows", [])
    charts: list[dict] = []
    if modality_rows:
        chart = await ic.craft.generate_plotly_chart(
            modality_rows,
            "bar",
            {
                "title": f"Imaging modality coverage — {cancer}",
                "x": "modality",
                "y": "studies",
                "x_label": "DICOM modality",
                "y_label": "Studies",
            },
        )
        fig = chart.get("figure")
        if fig:
            charts.append(fig)
        await ic.record(
            phase="chart",
            agent=AGENT,
            question=f"Chart modality coverage for {cancer}",
            tool="generate_plotly_chart",
            tool_input={"chart_type": "bar", "rows": len(modality_rows)},
            tool_output={"hasFigure": bool(fig)},
            live=bool(chart.get("live")),
        )

    # 2) Tri-modal scorecard.
    literature = ic.h.confidence
    genomics = _genomics_score(m)
    imaging = _imaging_score(m)
    revised = _clamp(0.45 * literature + 0.35 * genomics + 0.20 * imaging)
    score = InvestigationScore(
        literature=literature, genomics=genomics, imaging=imaging, revised=revised
    )

    # 3) Divergence: where does patient data disagree with the literature?
    freq = m.get("mutationFreqPct", 0.0)
    co = m.get("coRatePct", 0.0)
    meas = m.get("measurements", 0)
    divergence = _divergence(gene_a, gene_b, cancer, freq, co, meas, literature, genomics)

    # 4) Finding narrative — Gemini (1 call) with deterministic fallback.
    finding = _fallback_finding(ic, genomics, imaging)
    if ic.ctx.llm.enabled and ic.ctx.llm.can_call():
        llm_finding = _llm_finding(ic, genomics, imaging, revised)
        if llm_finding:
            finding = llm_finding

    await ic.record(
        phase="synthesis",
        agent=AGENT,
        question="Synthesize actionable radiogenomics finding",
        tool="synthesis",
        tool_output={
            "genomics": genomics,
            "imaging": imaging,
            "revised": revised,
            "finding": finding[:400],
        },
    )

    data_evidence: list[EvidenceItem] = m.get("dataEvidence", [])
    result = InvestigationResult(
        id=uuid.uuid4().hex[:12],
        hypothesisId=ic.h.id,
        steps=ic.steps,
        finding=finding,
        findingConfidence=revised,
        divergence=divergence,
        charts=charts,
        matrixChart=m.get("matrixChart"),
        archetypes=m.get("archetypes", []),
        dataEvidence=data_evidence,
        score=score,
        revisedConfidence=revised,
        cohortSize=int(m.get("cohort", 0) or 0),
        live=ic.used_live,
        completedAt=dt.datetime.utcnow().isoformat(),
        geneA=gene_a,
        geneB=gene_b,
        study=ic.study,
        cancerName=cancer,
        mutationFreqPct=float(m.get("mutationFreqPct", 0.0)),
        coRatePct=float(m.get("coRatePct", 0.0)),
        topModality=str(m.get("topModality", "")),
        totalStudies=int(m.get("totalStudies", 0) or 0),
        measurements=int(m.get("measurements", 0) or 0),
    )
    return result


def _divergence(
    gene_a: str, gene_b: str, cancer: str, freq: float, co: float,
    meas: int, literature: int, genomics: int,
) -> str:
    notes: list[str] = []
    if literature >= 65 and co < 3:
        notes.append(
            f"Literature is confident in the {gene_a}/{gene_b} link, but patient genomics "
            f"show only {co:.1f}% co-alteration in {cancer} — the mechanism may be rarer than papers imply."
        )
    if genomics >= 70 and meas < 40:
        notes.append(
            f"Genomics support is strong, yet only {meas} {cancer} patients have quantitative "
            f"imaging — an imaging endpoint would be underpowered without more cases."
        )
    if not notes:
        notes.append(
            f"Literature and patient data agree: {gene_a} is prevalent ({freq:.0f}%) and "
            f"imaging coverage supports stratification in {cancer}."
        )
    return " ".join(notes)


def _fallback_finding(ic: InvestigationContext, genomics: int, imaging: int) -> str:
    m = ic.metrics
    gene_a, gene_b, cancer = ic.gene_a, ic.gene_b, ic.cancer_name
    freq = m.get("mutationFreqPct", 0.0)
    co = m.get("coRatePct", 0.0)
    top = m.get("topModality", "CT")
    total = m.get("totalStudies", 0)
    meas = m.get("measurements", 0)
    verdict = "supports" if genomics >= 60 else "only partially supports"
    feasible = "feasible" if imaging >= 55 else "constrained"
    return (
        f"Patient data {verdict} the hypothesis: {gene_a} is mutated in {freq:.0f}% of {cancer} "
        f"tumors and co-alters with {gene_b} in {co:.1f}% of cases. Imaging is {feasible} — "
        f"{top} dominates {total} studies with {meas} patients carrying quantitative measurements. "
        f"Recommended next step: prioritise a {top}-based endpoint for the {gene_a}+{gene_b} "
        f"{cancer} subgroup and confirm measurability before trial design."
    )


def _llm_finding(ic: InvestigationContext, genomics: int, imaging: int, revised: int) -> str | None:
    m = ic.metrics
    prompt = f"""You are a translational oncology analyst. Write ONE actionable finding (3-4 sentences)
that a real trialist would act on, based on CRAFT queries against PanCancer + IDC.

Hypothesis: {ic.h.statement}
Cancer: {ic.cancer_name} ({ic.study})
Lead gene: {ic.gene_a}; secondary gene: {ic.gene_b}
{ic.gene_a} mutation frequency: {m.get('mutationFreqPct', 0):.1f}%
{ic.gene_a}+{ic.gene_b} co-alteration: {m.get('coRatePct', 0):.1f}%
Survival gap (days): {m.get('osGapDays', 0)}
Imaging studies: {m.get('totalStudies', 0)} (top modality {m.get('topModality', 'CT')})
Patients with quantitative measurements: {m.get('measurements', 0)}
Genomics score: {genomics}/100; Imaging feasibility: {imaging}/100; Revised confidence: {revised}%

Return JSON ONLY: {{"finding": "..."}}. Be specific, quantitative, and recommend a concrete next step."""
    data = ic.ctx.llm.complete_json_interactive(prompt)
    if isinstance(data, dict) and data.get("finding"):
        return str(data["finding"]).strip()[:800]
    return None
