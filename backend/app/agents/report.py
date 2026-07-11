"""Generate a structured investment / research report for funders and clinicians."""

from __future__ import annotations

import datetime as dt
import uuid

from app.agents.base import AgentContext
from app.models.schemas import (
    Hypothesis,
    HypothesisReport,
    ReportReference,
    ReportSection,
)


def _funding_estimate(h: Hypothesis) -> int:
    opp = h.opportunity
    base = 350_000
    if opp:
        base += min(opp.patientPopulation // 80, 3_500_000)
        base += opp.unmetNeed * 8_000
    return int(base)


def _support_summary(h: Hypothesis) -> str:
    support = [e for e in h.evidence if e.stance == "support"]
    contradict = [e for e in h.evidence if e.stance == "contradict"]
    return (
        f"{len(support)} supporting, {len(contradict)} contradicting, "
        f"{len(h.evidence) - len(support) - len(contradict)} neutral sources"
    )


def _references(h: Hypothesis) -> list[ReportReference]:
    refs: list[ReportReference] = []
    seen: set[str] = set()
    for e in h.evidence:
        if e.paperId in seen:
            continue
        seen.add(e.paperId)
        refs.append(ReportReference(title=e.title, url=e.url, stance=e.stance))
    return refs


def _lead_target(h: Hypothesis, ctx: AgentContext) -> str:
    entity_type: dict[str, str] = ctx.work.get("entity_type", {})
    for ent in h.entities:
        if _entity_kind(entity_type, ent) == "gene":
            return ent
    if len(h.entities) > 1:
        return h.entities[1]
    return h.entities[0] if h.entities else "lead target"


def _report_title(h: Hypothesis, ctx: AgentContext, query: str) -> str:
    """Descriptive fallback title — names the gap, target, and research domain."""
    entities = h.entities
    a, bridge, b = (entities + ["", "", ""])[:3]
    primary = _lead_target(h, ctx)
    opp = h.opportunity
    subgroup = opp.subgroup if opp else query
    status_note = f" ({h.status}, {h.confidence}% confidence)" if h.confidence else ""

    if len(entities) >= 3 and a and b and bridge:
        return (
            f"Investment Brief: Modulating {primary} to Link {a} and {b} "
            f"via {bridge} — {subgroup}{status_note}"
        )
    if h.statement:
        stmt = h.statement.strip()
        if len(stmt) > 100:
            stmt = stmt[:97].rsplit(" ", 1)[0] + "…"
        return f"Investment Brief: {stmt} — {query}"
    return f"Research & Investment Brief: {query} — Hypothesis {h.id}"


def _normalize_title(title: str, fallback: str) -> str:
    cleaned = " ".join(title.split()).strip()
    if len(cleaned) < 24 or cleaned.lower() in (
        "short report title",
        "investment brief",
        "research brief",
        "report",
    ):
        return fallback
    return cleaned[:220]


def _entity_kind(entity_type: dict[str, str], label: str) -> str:
    from app.agents.lexicon import ENTITY_TYPE

    return entity_type.get(label.lower(), ENTITY_TYPE.get(label.lower(), "concept"))


def _knowledge_gaps_section(h: Hypothesis, ctx: AgentContext, query: str) -> ReportSection:
    entity_type: dict[str, str] = ctx.work.get("entity_type", {})
    entities = h.entities
    a, bridge, b = (entities + ["?", "?", "?"])[:3]

    targets: list[str] = []
    for ent in entities:
        kind = _entity_kind(entity_type, ent)
        if kind in ("gene", "pathway"):
            targets.append(f"{ent} ({kind})")

    primary = next(
        (e for e in entities if _entity_kind(entity_type, e) == "gene"),
        bridge,
    )
    bridge_kind = _entity_kind(entity_type, bridge)
    modality = (
        "small-molecule or biologic pathway modulator"
        if bridge_kind == "pathway"
        else "gene-targeted therapy (ASO, siRNA, or biologic)"
        if _entity_kind(entity_type, primary) == "gene"
        else "phenotypic screen anchored to bridge biology"
    )

    return ReportSection(
        id="gaps",
        title="Knowledge Gaps & Drug Target Identification",
        body=(
            f'Literature synthesis on "{query}" exposes a structural knowledge gap: '
            f"{a} and {b} repeatedly co-occur with {bridge} in the corpus but are never "
            f"directly linked in primary papers—an open triangle indicative of unvalidated "
            f"mechanistic whitespace. {primary} is prioritized as the lead intervention "
            f"node because modulating this target may establish the missing {a}→{b} "
            f"connection and translate into a druggable hypothesis."
        ),
        bullets=[
            f"Gap type: open triangle — endpoints ({a}, {b}) lack direct citations despite shared bridge ({bridge}).",
            f"Candidate targets: {', '.join(targets) if targets else primary}.",
            f"Suggested modality: {modality}.",
            "Target validation: genetic/functional perturbation + co-occurrence in ≥2 independent cohorts.",
            "Whitespace signal: no approved therapy in corpus explicitly links this mechanistic axis.",
            f"Biomarker hook: stratify on {bridge} activity or {primary} expression for trial enrichment.",
        ],
        highlight=f"Lead target: {primary}",
    )


def _fallback_sections(h: Hypothesis, ctx: AgentContext, opp, funding: int, query: str) -> list[ReportSection]:
    support = [e for e in h.evidence if e.stance == "support"]
    contradict = [e for e in h.evidence if e.stance == "contradict"]
    entity_chain = " → ".join(h.entities) if h.entities else "N/A"
    pop = opp.patientPopulation if opp else 0
    unmet = opp.unmetNeed if opp else 0
    roi = opp.roiScore if opp else 0

    return [
        ReportSection(
            id="executive",
            title="Executive Summary",
            body=(
                f"This investment brief evaluates a novel mechanistic hypothesis derived from "
                f"literature synthesis on “{query}”: {h.statement} "
                f"Current corpus confidence is {h.confidence}% ({h.status}). "
                f"The opportunity targets an estimated {pop:,} patients with significant unmet need "
                f"({unmet}/100) and an ROI score of {roi}/100."
            ),
            highlight=f"${funding:,} validation budget · {pop:,} patients",
        ),
        _knowledge_gaps_section(h, ctx, query),
        ReportSection(
            id="mechanism",
            title="Scientific Hypothesis & Mechanistic Rationale",
            body=h.rationale,
            bullets=[
                f"Structural gap entities: {entity_chain}",
                h.confidenceExplanation or "Confidence derived from evidence stance weighting.",
                "Open triangle: endpoints co-occur with a shared bridge but lack direct linkage in corpus.",
            ],
        ),
        ReportSection(
            id="clinical",
            title="Clinical Significance & Healthcare Impact",
            body=(
                f"Clinicians should evaluate whether modulating the {entity_chain} axis could "
                f"change outcomes in {opp.subgroup if opp else 'the identified subgroup'}. "
                f"Early validation would inform biomarker-guided stratification and trial design."
            ),
            bullets=[
                "Potential to refine patient selection beyond syndromic diagnosis.",
                "Supports precision-medicine positioning if mechanistic link is confirmed.",
                "Addresses high-burden comorbidity patterns visible in the synthesized literature.",
            ],
        ),
        ReportSection(
            id="evidence",
            title="Evidence Assessment",
            body=_support_summary(h),
            bullets=[
                *(f"[{e.stance}] {e.title}" for e in support[:4]),
                *(f"[{e.stance}] {e.title}" for e in contradict[:2]),
            ] or ["No indexed evidence yet — expand corpus or upload primary papers."],
            highlight=f"{h.confidence}% confidence",
        ),
        ReportSection(
            id="population",
            title="Target Population & Stratification",
            body=(
                f"Primary subgroup: {opp.subgroup if opp else 'To be defined from entity overlap'}. "
                f"Estimated addressable population {pop:,} based on epidemiological heuristics "
                f"and corpus concept prevalence."
            ),
            bullets=[
                f"Unmet need index: {unmet}/100",
                f"Competitive whitespace: {opp.whitespace if opp else 'N/A'}/100",
                "Recommend genomic / pathway biomarker panel aligned to hypothesis entities.",
            ],
        ),
        ReportSection(
            id="commercial",
            title="Commercial Opportunity & ROI",
            body=opp.rationale if opp else "Commercial assessment pending opportunity scoring.",
            bullets=[
                opp.roiRationale if opp and opp.roiRationale else "ROI weighted by confidence, unmet need, and whitespace.",
                f"Estimated validation funding: ${funding:,}",
                f"Competition intensity: {opp.competition if opp else 'N/A'}/100 (lower = more whitespace)",
            ],
            highlight=f"ROI {roi}/100",
        ),
        ReportSection(
            id="validation",
            title="Recommended Validation Program",
            body="A staged 12–24 month program de-risks mechanism before larger clinical investment.",
            bullets=[
                f"Months 0–6: Retrospective EHR/chart review (n≈200) for {entity_chain} co-occurrence.",
                f"Months 4–12: Primary-cell or iPSC model perturbation of bridge pathway ({h.entities[1] if len(h.entities) > 1 else 'bridge'}).",
                f"Months 10–18: Biomarker assay development + small prospective observational cohort (n≈60).",
                f"Months 16–24: IND-enabling tox if small-molecule tractable; otherwise academic partnership.",
            ],
        ),
        ReportSection(
            id="budget",
            title="Budget & Funding Requirements",
            body=f"Total estimated validation spend: ${funding:,} over 18 months.",
            bullets=[
                f"Preclinical / model systems: ${funding // 3:,}",
                f"Clinical data & biobanking: ${funding // 3:,}",
                f"Biomarker assay + regulatory consulting: ${funding // 3:,}",
            ],
            highlight=f"${funding:,}",
        ),
        ReportSection(
            id="regulatory",
            title="Regulatory & Reimbursement Considerations",
            body=(
                "Initial work likely qualifies as observational / biomarker research (IRB). "
                "If therapeutic modality pursued, engage FDA INTERACT meeting by month 12. "
                "Payer value story hinges on stratified responder identification."
            ),
            bullets=[
                "Document diagnostic-therapeutic linkage for companion biomarker strategy.",
                "Map to existing CPT/ICD codes for baseline population; novel codes may require HEOR dossier.",
                "Rare-disease or subgroup pathway may qualify for orphan / breakthrough designation review.",
            ],
        ),
        ReportSection(
            id="risks",
            title="Risk Register & Mitigations",
            body="Key risks for funders and clinical partners to monitor.",
            bullets=[
                "Mechanistic gap may not translate to causal intervention → staged go/no-go gates.",
                "Corpus bias toward published positive findings → prioritize user-uploaded primary data.",
                "Competitive entry in whitespace → accelerate biomarker IP filing.",
                f"Evidence contested ({len(contradict)} contradicting sources) → pre-specify falsification criteria.",
            ],
        ),
        ReportSection(
            id="kpis",
            title="Key Performance Indicators for Funders",
            body="Milestone-based funding release recommended.",
            bullets=[
                "≥2 independent cohorts replicate entity co-occurrence pattern.",
                "Bridge-pathway perturbation shifts endpoint ≥30% vs control in model system.",
                "Prospective biomarker AUC ≥0.75 for subgroup assignment.",
                "Clear go/no-go decision memo by month 18 with updated ROI model.",
            ],
        ),
    ]


def _sections_to_plaintext(title: str, sections: list[ReportSection], refs: list[ReportReference]) -> str:
    lines = [title, ""]
    for s in sections:
        lines.append(s.title.upper())
        lines.append(s.body)
        for b in s.bullets:
            lines.append(f"  • {b}")
        if s.highlight:
            lines.append(f"  → {s.highlight}")
        lines.append("")
    if refs:
        lines.append("REFERENCES")
        for r in refs:
            url = f" ({r.url})" if r.url else ""
            lines.append(f"  • [{r.stance}] {r.title}{url}")
    return "\n".join(lines)


async def generate(ctx: AgentContext, h: Hypothesis) -> HypothesisReport:
    opp = h.opportunity
    funding = opp.estimatedFundingUsd if opp and opp.estimatedFundingUsd else _funding_estimate(h)
    pop = opp.patientPopulation if opp else 0
    roi = opp.roiBreakdown if opp else {}
    evidence_lines = "\n".join(
        f"- [{e.stance}] {e.title} ({e.url or 'no url'}): {e.snippet[:160]}"
        for e in h.evidence[:10]
    )
    title = _report_title(h, ctx, ctx.query)

    sections: list[ReportSection] | None = None
    key_metrics: dict[str, str] = {}
    timeline = 18
    if ctx.llm.enabled:
        prompt = f"""You are preparing a detailed investment & clinical research brief for funders, hospital R&D, and healthcare professionals.

Research session: {ctx.query}
HYPOTHESIS: {h.statement}
RATIONALE: {h.rationale}
ENTITIES: {', '.join(h.entities)}
CONFIDENCE: {h.confidence}% ({h.status}) — {h.confidenceExplanation or ''}

EVIDENCE:
{evidence_lines or 'None yet'}

COMMERCIAL:
- Subgroup: {opp.subgroup if opp else 'N/A'}
- Patients: {pop:,}
- Unmet need: {opp.unmetNeed if opp else 'N/A'}/100
- Competition: {opp.competition if opp else 'N/A'}/100
- ROI: {opp.roiScore if opp else 'N/A'}/100 — {opp.roiRationale if opp else ''}
- ROI breakdown: {roi}
- Funding estimate: ${funding:,}

Return JSON ONLY:
{{
  "title": "Specific descriptive title (12–22 words): name the mechanistic hypothesis, lead drug target or pathway, patient subgroup or disease context, and core investment thesis. Do NOT use generic labels like 'Investment Brief' alone.",
  "timelineMonths": 18,
  "keyMetrics": {{"confidence": "...", "patients": "...", "funding": "...", "roi": "...", "timeline": "..."}},
  "sections": [
    {{"id": "executive", "title": "Executive Summary", "body": "2-4 sentences", "bullets": [], "highlight": "key figure"}},
    {{"id": "gaps", "title": "Knowledge Gaps & Drug Target Identification", "body": "Describe the open-triangle knowledge gap and prioritize druggable targets (genes/pathways) with modality suggestions", "bullets": ["gap type", "lead target", "modality", "validation"], "highlight": "lead target name"}},
    {{"id": "mechanism", "title": "Scientific Hypothesis & Mechanistic Rationale", "body": "...", "bullets": ["..."], "highlight": ""}},
    {{"id": "clinical", "title": "Clinical Significance & Healthcare Impact", "body": "...", "bullets": ["..."], "highlight": ""}},
    {{"id": "evidence", "title": "Evidence Assessment", "body": "...", "bullets": ["..."], "highlight": ""}},
    {{"id": "population", "title": "Target Population & Stratification", "body": "...", "bullets": ["..."], "highlight": ""}},
    {{"id": "commercial", "title": "Commercial Opportunity & ROI", "body": "...", "bullets": ["..."], "highlight": ""}},
    {{"id": "validation", "title": "Recommended Validation Program", "body": "...", "bullets": ["month-by-month milestones"], "highlight": ""}},
    {{"id": "budget", "title": "Budget & Funding Requirements", "body": "...", "bullets": ["line items"], "highlight": "${funding:,}"}},
    {{"id": "regulatory", "title": "Regulatory & Reimbursement Considerations", "body": "...", "bullets": ["..."], "highlight": ""}},
    {{"id": "risks", "title": "Risk Register & Mitigations", "body": "...", "bullets": ["..."], "highlight": ""}},
    {{"id": "kpis", "title": "Key Performance Indicators for Funders", "body": "...", "bullets": ["measurable milestones"], "highlight": ""}}
  ]
}}

Be specific, quantitative where possible, and actionable. Note uncertainties explicitly."""
        data = ctx.llm.complete_json_interactive(prompt, deep=True)
        if isinstance(data, dict) and isinstance(data.get("sections"), list):
            sections = []
            for raw in data["sections"]:
                if not isinstance(raw, dict):
                    continue
                sections.append(
                    ReportSection(
                        id=str(raw.get("id", "section")),
                        title=str(raw.get("title", "Section")),
                        body=str(raw.get("body", "")),
                        bullets=[str(b) for b in raw.get("bullets", []) if b],
                        highlight=str(raw.get("highlight", "")),
                    )
                )
            if data.get("title"):
                title = _normalize_title(str(data["title"]), title)
            key_metrics = {str(k): str(v) for k, v in (data.get("keyMetrics") or {}).items()}
            timeline = int(data.get("timelineMonths", 18))

    if sections and not any(s.id == "gaps" for s in sections):
        idx = next((i for i, s in enumerate(sections) if s.id == "executive"), -1)
        sections.insert(idx + 1, _knowledge_gaps_section(h, ctx, ctx.query))

    if not sections:
        sections = _fallback_sections(h, ctx, opp, funding, ctx.query)
        key_metrics = {
            "confidence": f"{h.confidence}%",
            "patients": f"{pop:,}",
            "funding": f"${funding:,}",
            "roi": f"{opp.roiScore if opp else 0}/100",
            "timeline": f"{timeline} months",
        }

    refs = _references(h)
    plaintext = _sections_to_plaintext(title, sections, refs)

    return HypothesisReport(
        id=str(uuid.uuid4())[:12],
        hypothesisId=h.id,
        title=title,
        generatedAt=dt.datetime.utcnow().isoformat(),
        fundingEstimateUsd=funding,
        patientPopulation=pop,
        timelineMonths=timeline,
        sections=sections,
        references=refs,
        keyMetrics=key_metrics if key_metrics else {
            "confidence": f"{h.confidence}%",
            "patients": f"{pop:,}",
            "funding": f"${funding:,}",
            "roi": f"{opp.roiScore if opp else 0}/100",
            "timeline": f"{timeline} months",
        },
        markdown=plaintext,
    )
