"""Investigation orchestrator — LangGraph sub-graph + result application.

Wires Planner -> PanCancer analyst -> Imaging analyst -> Synthesizer, then folds
the real-world evidence back into the hypothesis: appends data-evidence, revises
confidence with the tri-modal score, and grounds the commercial population in
the CRAFT-measured mutation frequency.
"""

from __future__ import annotations

from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from app.agents.base import AgentContext, timer
from app.agents.commercial import CommercialAgent
from app.agents.evidence import EvidenceAgent
from app.agents.investigation import (
    imaging_analyst,
    pancancer_analyst,
    planner,
    synthesizer,
)
from app.agents.investigation.runner import InvestigationContext
from app.models.schemas import (
    ConfidencePoint,
    GraphLink,
    GraphNode,
    Hypothesis,
    InvestigationResult,
)
from app.services.craft_mcp import get_craft


class _IState(TypedDict, total=False):
    step: str


def _build(ic: InvestigationContext):
    result_holder: dict[str, InvestigationResult] = {}

    async def n_plan(state: _IState) -> _IState:
        await planner.run(ic)
        return {"step": "plan"}

    async def n_pancancer(state: _IState) -> _IState:
        await pancancer_analyst.run(ic)
        return {"step": "pancancer"}

    async def n_imaging(state: _IState) -> _IState:
        await imaging_analyst.run(ic)
        return {"step": "imaging"}

    async def n_synth(state: _IState) -> _IState:
        result_holder["result"] = await synthesizer.run(ic)
        return {"step": "synthesis"}

    sg = StateGraph(_IState)
    sg.add_node("plan", n_plan)
    sg.add_node("pancancer", n_pancancer)
    sg.add_node("imaging", n_imaging)
    sg.add_node("synthesis", n_synth)
    sg.add_edge(START, "plan")
    sg.add_edge("plan", "pancancer")
    sg.add_edge("pancancer", "imaging")
    sg.add_edge("imaging", "synthesis")
    sg.add_edge("synthesis", END)
    return sg.compile(), result_holder


async def investigate(
    ctx: AgentContext, h: Hypothesis, *, force: bool = False
) -> Hypothesis:
    """Run the CRAFT investigation for a single hypothesis and apply results."""
    if h.craftInvestigated and not force:
        return h

    craft = get_craft()
    ic = InvestigationContext(ctx=ctx, craft=craft, h=h)

    await ctx.audit(
        "craft_planner",
        "Investigation started",
        detail=h.statement[:80],
        params={"hypothesisId": h.id, "mode": "live" if craft.live else "demo"},
    )

    with timer() as t:
        graph, holder = _build(ic)
        try:
            await graph.ainvoke({"step": "start"})
        finally:
            await craft.close()

    result = holder.get("result")
    if result is None:
        await ctx.audit(
            "craft_synthesizer", "Investigation produced no result",
            detail=h.statement[:60], status="error",
        )
        return h

    _apply_result(ctx, h, result)

    # Fold CRAFT findings into the knowledge graph as first-class dataset nodes,
    # then push the updated graph to the client. Reuses investigation data only.
    new_nodes = _craft_graph_nodes(ctx, h, result)
    if new_nodes:
        await ctx.session.emit(
            {"type": "graph", "payload": ctx.session.state.graph.model_dump()}
        )
        await ctx.audit(
            "craft_synthesizer",
            "Added CRAFT nodes to graph",
            detail=f"{len(new_nodes)} dataset node(s)",
            params={"nodes": [n.id for n in new_nodes]},
        )

    await ctx.audit(
        "craft_synthesizer",
        "Investigation complete",
        detail=result.finding[:90],
        params={
            "hypothesisId": h.id,
            "revisedConfidence": result.revisedConfidence,
            "genomics": result.score.genomics,
            "imaging": result.score.imaging,
            "queries": ic.queries_used,
            "live": result.live,
        },
        duration_ms=t.elapsed_ms,
    )
    return h


def _apply_result(ctx: AgentContext, h: Hypothesis, result: InvestigationResult) -> None:
    """Fold real-world evidence into the hypothesis (confidence, evidence, N)."""
    h.investigation = result
    h.craftInvestigated = True

    # Append CRAFT data-evidence to the evidence stack (dedup by paperId).
    existing = {e.paperId for e in h.evidence}
    for item in result.dataEvidence:
        if item.paperId not in existing:
            h.evidence.append(item)
            existing.add(item.paperId)

    # Recompute the breakdown so the explainer reflects genomics + imaging rows,
    # but let the tri-modal score be the headline confidence.
    agent = EvidenceAgent()
    _, breakdown = agent._score_detail(h.evidence)
    revised = result.revisedConfidence or h.confidence
    h.confidence = revised
    h.confidenceBreakdown = breakdown
    h.confidenceExplanation = (
        f"Revised to {revised}% after CRAFT investigation: literature "
        f"{result.score.literature}%, genomics {result.score.genomics}%, imaging "
        f"feasibility {result.score.imaging}% (weighted 0.45/0.35/0.20). "
        f"{breakdown.supportCount} supporting and {breakdown.contradictCount} "
        f"contradicting sources across papers and patient data."
    )
    # Extend the trajectory with the revised point.
    h.history = list(h.history) + [ConfidencePoint(t="RWE", confidence=revised)]
    support = breakdown.supportCount
    contradict = breakdown.contradictCount
    h.status = (
        "contested"
        if contradict >= support and contradict > 0
        else ("supported" if revised >= 70 else "emerging")
    )

    # Ground the commercial population in the CRAFT-measured mutation frequency.
    CommercialAgent().apply_investigation(ctx, h, result)


def _craft_graph_nodes(
    ctx: AgentContext, h: Hypothesis, result: InvestigationResult
) -> list[GraphNode]:
    """Add PanCancer + IDC dataset nodes to the graph, linked to topic concepts.

    Built entirely from the investigation result (no extra CRAFT calls). Idempotent
    per hypothesis: prior CRAFT nodes for this hypothesis are replaced on re-run.
    """
    graph = ctx.session.state.graph
    pan_id = f"craftpan_{h.id}"
    idc_id = f"craftidc_{h.id}"
    craft_ids = {pan_id, idc_id}

    def _endpoint(v: object) -> str:
        return v if isinstance(v, str) else getattr(v, "id", str(v))

    graph.nodes = [n for n in graph.nodes if n.id not in craft_ids]
    graph.links = [
        l for l in graph.links
        if _endpoint(l.source) not in craft_ids and _endpoint(l.target) not in craft_ids
    ]

    study = result.study or "PANCAN"
    cancer = result.cancerName or study
    pan = GraphNode(
        id=pan_id,
        label=f"PanCancer · {study}",
        type="dataset",
        source="craft_pancancer",
        centrality=0.6,
        summary=(
            f"CRAFT genomics cohort. {result.geneA} mutated in "
            f"{result.mutationFreqPct:.0f}% of {study}; {result.geneA}+{result.geneB} "
            f"co-altered in {result.coRatePct:.1f}%. Derived via text-to-SQL over the "
            f"PanCancer Atlas MC3 MAF + clinical tables."
        ),
    )
    idc = GraphNode(
        id=idc_id,
        label=f"IDC · {cancer}",
        type="dataset",
        source="craft_idc",
        centrality=0.6,
        summary=(
            f"CRAFT imaging cohort. {result.totalStudies} studies; top modality "
            f"{result.topModality}; {result.measurements} patients with quantitative "
            f"measurements. Derived via text-to-SQL over IDC DICOM_PIVOT + "
            f"MEASUREMENT_GROUPS."
        ),
    )
    new_nodes = [pan, idc]

    # TCGA-barcode bridge between the two modalities.
    new_links = [GraphLink(source=pan_id, target=idc_id, kind="conceptual", weight=1.0)]

    concept_by_label: dict[str, str] = {}
    for n in graph.nodes:
        if n.type == "concept":
            concept_by_label.setdefault(n.label.lower(), n.id)

    linked = False
    for ent in h.entities:
        nid = concept_by_label.get(ent.lower())
        if nid:
            new_links.append(GraphLink(source=pan_id, target=nid, kind="conceptual", weight=0.7))
            linked = True
    # Anchor imaging node to the lead entity as the radiogenomics bridge.
    if h.entities:
        lead = concept_by_label.get(h.entities[0].lower())
        if lead:
            new_links.append(GraphLink(source=idc_id, target=lead, kind="conceptual", weight=0.5))
    # Fallback: attach to the most central concept so the pair isn't orphaned.
    if not linked:
        concepts = [n for n in graph.nodes if n.type == "concept"]
        if concepts:
            top = max(concepts, key=lambda n: n.centrality or 0)
            new_links.append(GraphLink(source=pan_id, target=top.id, kind="conceptual", weight=0.5))

    graph.nodes.extend(new_nodes)
    graph.links.extend(new_links)
    return new_nodes
