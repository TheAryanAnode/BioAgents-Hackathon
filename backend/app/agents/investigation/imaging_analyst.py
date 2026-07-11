"""Imaging analyst — imaging feasibility via IDC.

Answers the biotech-challenge question directly: which imaging modalities cover
the cancer cohort, and are quantitative measurements available to power a
radiology endpoint? Emits modality distribution used by the synthesizer chart.
"""

from __future__ import annotations

from app.agents.investigation.runner import InvestigationContext
from app.models.schemas import EvidenceItem

AGENT = "craft_imaging"


async def run(ic: InvestigationContext) -> None:
    cancer = ic.cancer_name
    evidence: list[EvidenceItem] = ic.metrics.setdefault("dataEvidence", [])

    # Q4 — imaging modality distribution for the cohort.
    rows, sql, _ = await ic.run_query(
        agent=AGENT,
        question=f"Imaging modality distribution for {cancer}",
        nl_question=(
            f"How many imaging studies exist per modality (CT, MR, PT) for the "
            f"{cancer} collection?"
        ),
        connection=ic.idc,
    )
    modality_rows = [
        {"modality": str(r.get("Modality", r.get("modality", "?"))),
         "studies": int(r.get("studies", 0) or 0)}
        for r in rows
        if r.get("Modality") or r.get("modality")
    ]
    total_studies = sum(m["studies"] for m in modality_rows)
    top_modality = modality_rows[0]["modality"] if modality_rows else "—"
    ic.metrics["modalityRows"] = modality_rows
    ic.metrics["totalStudies"] = total_studies
    ic.metrics["topModality"] = top_modality
    if modality_rows:
        evidence.append(
            EvidenceItem(
                paperId=f"craft_idc_modality_{ic.study}",
                title=f"IDC: {total_studies} imaging studies for {cancer}; {top_modality} dominant",
                source="craft_idc",
                relevance=min(1.0, total_studies / 2000 + 0.3),
                stance="support" if total_studies >= 200 else "neutral",
                snippet=(
                    f"DICOM_PIVOT reports {total_studies} studies across "
                    f"{len(modality_rows)} modalities; {top_modality} is most common."
                ),
                rowCount=len(rows),
                sql=sql,
                connection=ic.idc,
            )
        )

    # Q5 — quantitative measurement availability (radiomic feasibility).
    rows2, sql2, _ = await ic.run_query(
        agent=AGENT,
        question=f"Quantitative measurement availability for {cancer}",
        nl_question=(
            f"How many {cancer} patients have quantitative imaging measurements "
            f"available in the measurement groups table?"
        ),
        connection=ic.idc,
    )
    measurements = 0
    for r in rows2:
        if "patients_with_measurements" in r:
            measurements = int(r.get("patients_with_measurements", 0) or 0)
            break
    ic.metrics["measurements"] = measurements
    if rows2:
        evidence.append(
            EvidenceItem(
                paperId=f"craft_idc_meas_{ic.study}",
                title=f"IDC: {measurements} {cancer} patients have quantitative measurements",
                source="craft_idc",
                relevance=min(1.0, measurements / 200 + 0.25),
                stance="support" if measurements >= 40 else "contradict",
                snippet=(
                    f"MEASUREMENT_GROUPS covers {measurements} {cancer} patients — "
                    f"{'sufficient' if measurements >= 40 else 'limited'} for a radiology endpoint."
                ),
                rowCount=len(rows2),
                sql=sql2,
                connection=ic.idc,
            )
        )
