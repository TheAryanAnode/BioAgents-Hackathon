"""Planner agent — turns a hypothesis into an investigable CRAFT plan.

Deterministic (no LLM spend): it resolves domain terms, locates the relevant
tables in both connections, and frames the sub-questions the analysts answer.
"""

from __future__ import annotations

from app.agents.investigation.runner import InvestigationContext

AGENT = "craft_planner"


async def run(ic: InvestigationContext) -> None:
    ic.parse()
    gene_a, gene_b, cancer = ic.gene_a, ic.gene_b, ic.cancer_name

    # 1) Frame the investigation (no tool call — pure reasoning step).
    await ic.record(
        phase="plan",
        agent=AGENT,
        question=(
            f"Investigate whether the {gene_a}/{gene_b} axis in {cancer} is supported by "
            f"real patient genomics and is measurable in imaging."
        ),
        tool="plan",
        tool_output={
            "geneA": gene_a,
            "geneB": gene_b,
            "study": ic.study,
            "cancer": cancer,
            "subQuestions": [
                f"How prevalent is {gene_a} mutation in {ic.study}?",
                f"Do {gene_a} and {gene_b} co-alter in the same tumors?",
                f"Does {gene_a} mutation stratify survival?",
                f"What imaging modalities cover the {cancer} cohort?",
                f"Are quantitative imaging measurements available for {cancer}?",
            ],
        },
    )

    # 2) Resolve domain terminology via CRAFT (semantic-layer depth).
    for term in ("Hugo_Symbol", "TCGA ParticipantBarcode", "DICOM Modality"):
        res = await ic.craft.resolve_term(term)
        await ic.record(
            phase="term",
            agent=AGENT,
            question=f"Resolve domain term: {term}",
            tool="resolve_term",
            tool_input={"term": term},
            tool_output={"definition": res.get("definition", "")},
            live=bool(res.get("live")),
        )

    # 3) Locate the tables in each connection.
    pan = await ic.craft.search_schema(
        f"{gene_a} mutation clinical survival", ic.pancancer
    )
    await ic.record(
        phase="schema",
        agent=AGENT,
        question="Locate mutation + clinical tables in PanCancer Atlas",
        tool="search_schema",
        connection=ic.pancancer,
        tool_input={"query": f"{gene_a} mutation clinical survival"},
        tool_output={"tables": pan.get("tables", [])},
        live=bool(pan.get("live")),
    )

    idc = await ic.craft.search_schema(
        f"{cancer} DICOM imaging modality measurement", ic.idc
    )
    await ic.record(
        phase="schema",
        agent=AGENT,
        question="Locate imaging + measurement tables in IDC",
        tool="search_schema",
        connection=ic.idc,
        tool_input={"query": f"{cancer} DICOM imaging modality measurement"},
        tool_output={"tables": idc.get("tables", [])},
        live=bool(idc.get("live")),
    )
