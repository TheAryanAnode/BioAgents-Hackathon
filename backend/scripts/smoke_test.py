"""Offline end-to-end smoke test of the agent pipeline (no server, demo mode)."""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agents.orchestrator import get_context, run_pipeline  # noqa: E402
from app.db.database import init_db  # noqa: E402
from app.services.session_store import store  # noqa: E402


async def main(query: str):
    init_db()
    session = store.create("smoke123", query)
    await run_pipeline(session)
    st = session.state

    print(f"\n=== QUERY: {query} ===")
    print(f"papers ingested : {len(session.papers)}")
    print(f"graph nodes     : {len(st.graph.nodes)}  edges: {len(st.graph.links)}")
    print(f"clusters        : {[c.label for c in st.graph.clusters][:6]}")
    concepts = [n.label for n in st.graph.nodes if n.type == 'concept']
    print(f"concepts ({len(concepts)}) : {concepts[:12]}")

    print(f"\nhypotheses ({len(st.hypotheses)}):")
    for h in st.hypotheses:
        sup = sum(1 for e in h.evidence if e.stance == 'support')
        con = sum(1 for e in h.evidence if e.stance == 'contradict')
        print(f"  [{h.confidence}% {h.status}] {h.statement}")
        print(f"      evidence: {len(h.evidence)} (support {sup} / contradict {con}); history pts {len(h.history)}")

    if st.dashboard:
        m = st.dashboard.metrics
        print(f"\ndashboard: opps={m.opportunities} avgConf={m.avgConfidence}% "
              f"pop={m.patientPopulation:,} roi={m.projectedRoi}x")
        print(f"  trend topics: {st.dashboard.trendTopics}")
        print(f"  trend rows: {len(st.dashboard.trends)}  stratification: {len(st.dashboard.stratification)}")
        for o in sorted(st.dashboard.opportunities, key=lambda x: x.roiScore, reverse=True)[:3]:
            print(f"    OPP {o.roiScore} | {o.title} | {o.subgroup} | pop {o.patientPopulation:,}")

    print(f"\naudit entries: {len(st.audit)}")
    ctx = get_context("smoke123")
    print(f"vector backend: {ctx.vectors.backend} | embedding: {ctx.vectors.embedder.mode}")


if __name__ == "__main__":
    q = sys.argv[1] if len(sys.argv) > 1 else "autism genomics"
    asyncio.run(main(q))
