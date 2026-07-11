"""PanCancer analyst — genomic validation of the hypothesis.

Runs three CRAFT query loops against the PanCancer Atlas connection:
prevalence, co-alteration, and survival stratification. Stores metrics on the
shared context for the synthesizer and emits data-evidence rows.
"""

from __future__ import annotations

from app.agents.investigation.runner import InvestigationContext
from app.models.schemas import EvidenceItem

AGENT = "craft_pancancer"


def _num(rows: list[dict], key: str, default: float = 0.0) -> float:
    for r in rows:
        if key in r and isinstance(r[key], (int, float)):
            return float(r[key])
    return default


async def run(ic: InvestigationContext) -> None:
    gene_a, gene_b, study = ic.gene_a, ic.gene_b, ic.study
    evidence: list[EvidenceItem] = ic.metrics.setdefault("dataEvidence", [])

    # Q1 — mutation prevalence.
    rows, sql, _ = await ic.run_query(
        agent=AGENT,
        question=f"Prevalence of {gene_a} mutation in {study}",
        nl_question=f"What fraction of {study} tumors carry a {gene_a} mutation?",
        connection=ic.pancancer,
    )
    freq_pct = _num(rows, "frequency_pct")
    mutated = int(_num(rows, "mutated"))
    cohort = int(_num(rows, "cohort", 0)) or int(_num(rows, "n", 0))
    ic.metrics["mutationFreqPct"] = freq_pct
    ic.metrics["mutated"] = mutated
    ic.metrics["cohort"] = cohort or ic.metrics.get("cohort", 0)
    if rows:
        evidence.append(
            EvidenceItem(
                paperId=f"craft_pan_prev_{gene_a}",
                title=f"PanCancer: {gene_a} altered in {freq_pct:.0f}% of {study} tumors (n={mutated})",
                source="craft_pancancer",
                relevance=min(1.0, freq_pct / 100 + 0.35),
                stance="support" if freq_pct >= 8 else "neutral",
                snippet=(
                    f"MC3 MAF shows {mutated} of {cohort or '—'} {study} patients carry a "
                    f"{gene_a} mutation ({freq_pct:.1f}%)."
                ),
                rowCount=len(rows),
                sql=sql,
                connection=ic.pancancer,
            )
        )

    # Q2 — co-alteration with the bridge/second gene.
    rows2, sql2, _ = await ic.run_query(
        agent=AGENT,
        question=f"Co-alteration of {gene_a} and {gene_b}",
        nl_question=(
            f"How many {study} tumors carry both a {gene_a} mutation and a {gene_b} "
            f"mutation (co-occurrence)?"
        ),
        connection=ic.pancancer,
    )
    co_rate = _num(rows2, "co_rate_pct")
    co_altered = int(_num(rows2, "co_altered"))
    ic.metrics["coRatePct"] = co_rate
    ic.metrics["coAltered"] = co_altered
    if rows2:
        evidence.append(
            EvidenceItem(
                paperId=f"craft_pan_co_{gene_a}_{gene_b}",
                title=f"PanCancer: {gene_a}+{gene_b} co-altered in {co_rate:.1f}% of {study}",
                source="craft_pancancer",
                relevance=min(1.0, co_rate / 50 + 0.4),
                stance="support" if co_rate >= 3 else "contradict",
                snippet=(
                    f"{co_altered} {study} tumors co-alter {gene_a} and {gene_b} "
                    f"({co_rate:.1f}% of the cohort)."
                ),
                rowCount=len(rows2),
                sql=sql2,
                connection=ic.pancancer,
            )
        )

    # Q3 — survival stratification.
    rows3, sql3, _ = await ic.run_query(
        agent=AGENT,
        question=f"Survival stratified by {gene_a} status",
        nl_question=(
            f"Compare mean overall survival time between {gene_a}-mutant and living "
            f"{study} patients."
        ),
        connection=ic.pancancer,
    )
    deceased_os = 0.0
    living_os = 0.0
    for r in rows3:
        status = str(r.get("OS_STATUS", "")).upper()
        if "DECEAS" in status:
            deceased_os = float(r.get("mean_os_days", 0) or 0)
        elif "LIV" in status:
            living_os = float(r.get("mean_os_days", 0) or 0)
    os_gap = int(living_os - deceased_os)
    ic.metrics["osGapDays"] = os_gap
    if rows3:
        evidence.append(
            EvidenceItem(
                paperId=f"craft_pan_os_{gene_a}",
                title=f"PanCancer: OS gap of {os_gap} days across {gene_a} outcome groups",
                source="craft_pancancer",
                relevance=0.6,
                stance="support" if os_gap > 120 else "neutral",
                snippet=(
                    f"Mean OS differs by ~{os_gap} days between living and deceased "
                    f"{gene_a}-associated {study} patients."
                ),
                rowCount=len(rows3),
                sql=sql3,
                connection=ic.pancancer,
            )
        )
