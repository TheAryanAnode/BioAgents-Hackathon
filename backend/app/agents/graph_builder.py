from __future__ import annotations

import networkx as nx

from app.agents.base import AgentContext, timer
from app.models.schemas import Cluster, GraphData, GraphLink, GraphNode


class GraphBuilderAgent:
    name = "graph_builder"

    async def run(self, ctx: AgentContext) -> GraphData:
        await ctx.stage("graph")
        papers = ctx.session.papers
        paper_entities: dict[str, list[str]] = ctx.work.get("paper_entities", {})
        entity_papers: dict[str, list[str]] = ctx.work.get("entity_papers", {})
        entity_type: dict[str, str] = ctx.work.get("entity_type", {})
        cooc: dict[tuple[str, str], int] = ctx.work.get("cooc", {})

        g = nx.Graph()

        # Concept nodes (keep concepts that appear in >=1 paper).
        concept_ids: dict[str, str] = {}
        for ent, pids in entity_papers.items():
            cid = f"concept::{ent}"
            concept_ids[ent] = cid
            g.add_node(cid, label=ent, type="concept", paperCount=len(pids))

        # Paper nodes + paper->concept edges.
        for pid, rec in papers.items():
            g.add_node(pid, label=rec.title, type="paper")
            for ent in paper_entities.get(pid, []):
                cid = concept_ids.get(ent)
                if cid:
                    g.add_edge(pid, cid, kind="conceptual", weight=1.0)

        # Concept<->concept edges from co-occurrence.
        for (a, b), w in cooc.items():
            ca, cb = concept_ids.get(a), concept_ids.get(b)
            if ca and cb and w >= 1:
                g.add_edge(ca, cb, kind="conceptual", weight=float(w))

        # Paper<->paper "citation-like" links when papers share >=2 concepts.
        plist = list(papers.keys())
        for i in range(len(plist)):
            for j in range(i + 1, len(plist)):
                shared = set(paper_entities.get(plist[i], [])) & set(
                    paper_entities.get(plist[j], [])
                )
                if len(shared) >= 2:
                    g.add_edge(plist[i], plist[j], kind="citation", weight=float(len(shared)))

        with timer() as t:
            centrality = nx.degree_centrality(g) if g.number_of_nodes() else {}
            # Community detection over the concept-rich graph.
            try:
                comms = list(nx.community.greedy_modularity_communities(g))
            except Exception:
                comms = [set(g.nodes())]

        node_cluster: dict[str, int] = {}
        cluster_objs: list[Cluster] = []
        for idx, comm in enumerate(comms):
            # Label cluster by its highest-degree concept.
            concepts = [
                (n, g.degree(n)) for n in comm if g.nodes[n].get("type") == "concept"
            ]
            label = "Cluster"
            if concepts:
                label = g.nodes[max(concepts, key=lambda x: x[1])[0]]["label"]
            cluster_objs.append(Cluster(id=idx, label=label))
            for n in comm:
                node_cluster[n] = idx
                g.nodes[n]["cluster"] = idx

        nodes: list[GraphNode] = []
        for n, attrs in g.nodes(data=True):
            cl = node_cluster.get(n, 0)
            if attrs.get("type") == "paper":
                rec = papers[n]
                nodes.append(
                    GraphNode(
                        id=n, label=rec.title, type="paper", source=rec.source,
                        cluster=cl, clusterLabel=cluster_objs[cl].label if cluster_objs else None,
                        centrality=round(centrality.get(n, 0), 4),
                        year=rec.year, citationCount=rec.citation_count,
                        authors=rec.authors, summary=rec.abstract[:400] or None, url=rec.url,
                    )
                )
            else:
                ent = attrs["label"]
                nodes.append(
                    GraphNode(
                        id=n, label=ent, type="concept", source="derived",
                        cluster=cl, clusterLabel=cluster_objs[cl].label if cluster_objs else None,
                        centrality=round(centrality.get(n, 0), 4),
                        paperCount=attrs.get("paperCount"),
                        summary=f"{entity_type.get(ent, 'concept').capitalize()} appearing in "
                        f"{attrs.get('paperCount', 0)} papers in this corpus.",
                    )
                )

        links: list[GraphLink] = [
            GraphLink(source=u, target=v, kind=d.get("kind", "conceptual"), weight=d.get("weight", 1.0))
            for u, v, d in g.edges(data=True)
        ]

        graph = GraphData(nodes=nodes, links=links, clusters=cluster_objs)
        ctx.session.state.graph = graph
        ctx.work["nx_graph"] = g
        ctx.work["centrality"] = centrality
        ctx.work["concept_ids"] = concept_ids
        ctx.work["node_cluster"] = node_cluster

        await ctx.session.emit({"type": "graph", "payload": graph.model_dump()})
        await ctx.audit(
            self.name, "Knowledge graph built",
            detail=f"{len(nodes)} nodes · {len(links)} edges · {len(cluster_objs)} clusters",
            params={"nodes": len(nodes), "edges": len(links), "clusters": len(cluster_objs)},
            duration_ms=t.elapsed_ms,
        )
        return graph
