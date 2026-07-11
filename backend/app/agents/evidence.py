from __future__ import annotations

from app.agents.base import AgentContext, timer
from app.agents.subgraph import build_hypothesis_subgraph
from app.models.schemas import ConfidenceBreakdown, ConfidencePoint, EvidenceItem, Hypothesis
from app.services.paper_urls import resolve_paper_url

_CONTRADICT_CUES = (
    "no association", "not associated", "failed to", "no significant",
    "unrelated", "independent of", "no evidence", "does not", "contradict",
    "no link", "ruled out",
)


def _entity_overlap(entities: list[str], text: str) -> int:
    low = text.lower()
    return sum(1 for e in entities if e and e.lower() in low)


def _heuristic_stance(entities: list[str], text: str, relevance: float) -> tuple[str, float]:
    low = text.lower()
    overlap = _entity_overlap(entities, text)
    blended = max(relevance, min(1.0, 0.3 + 0.22 * overlap))
    if any(cue in low for cue in _CONTRADICT_CUES) and overlap >= 1:
        return "contradict", blended
    if overlap >= 2:
        return "support", blended
    if overlap == 1 and relevance > 0.3:
        return "support", blended
    if blended < 0.2:
        return "neutral", blended
    return "neutral", blended


def _paper_url(ctx: AgentContext, pid: str, rec) -> str | None:
    if rec:
        url = resolve_paper_url(rec)
        if url:
            return url
    node = next((n for n in ctx.session.state.graph.nodes if n.id == pid), None)
    if node and node.url:
        return node.url
    return None


class EvidenceAgent:
    name = "evidence"

    def _stance_llm(self, ctx: AgentContext, statement: str, snippet: str) -> str | None:
        prompt = (
            f"Hypothesis: {statement}\n\nEvidence snippet: {snippet}\n\n"
            "Does the snippet SUPPORT, CONTRADICT, or stay NEUTRAL toward the "
            'hypothesis? Return JSON: {"stance": "support|contradict|neutral"}.'
        )
        data = ctx.llm.complete_json(prompt)
        if isinstance(data, dict) and data.get("stance") in ("support", "contradict", "neutral"):
            return data["stance"]
        return None

    def _score_detail(self, evidence: list[EvidenceItem]) -> tuple[int, ConfidenceBreakdown]:
        support = sum(1 for e in evidence if e.stance == "support")
        contradict = sum(1 for e in evidence if e.stance == "contradict")
        neutral = sum(1 for e in evidence if e.stance == "neutral")
        rel = sum(e.relevance for e in evidence) / max(1, len(evidence))
        support_boost = 12 * support
        contradict_penalty = 18 * contradict
        relevance_boost = int(round(rel * 20))
        raw = 50 + support_boost - contradict_penalty + relevance_boost
        score = max(8, min(95, int(round(raw))))
        return score, ConfidenceBreakdown(
            base=50,
            supportCount=support,
            contradictCount=contradict,
            neutralCount=neutral,
            supportBoost=support_boost,
            contradictPenalty=contradict_penalty,
            relevanceBoost=relevance_boost,
            avgRelevance=round(rel, 3),
        )

    def _confidence_explanation(self, h: Hypothesis, bd: ConfidenceBreakdown, score: int) -> str:
        return (
            f"Confidence {score}% starts from a {bd.base}% baseline, adds +{bd.supportBoost} "
            f"from {bd.supportCount} supporting paper(s), subtracts {bd.contradictPenalty} "
            f"from {bd.contradictCount} contradicting paper(s), and adds +{bd.relevanceBoost} "
            f"from average semantic relevance ({int(bd.avgRelevance * 100)}%). "
            f"{bd.neutralCount} neutral source(s) did not move the score."
        )

    def _history(self, ctx: AgentContext, evidence: list[EvidenceItem], final: int) -> list[ConfidencePoint]:
        years = sorted({e.year for e in evidence if e.year} | {2018, 2020, 2022, 2024})
        years = years[-5:] if len(years) > 5 else years
        if not years:
            years = [2020, 2021, 2022, 2023, 2024]
        pts: list[ConfidencePoint] = []
        start = max(20, final - 30)
        step = (final - start) / max(1, len(years) - 1)
        for i, y in enumerate(years):
            pts.append(ConfidencePoint(t=str(y), confidence=int(round(start + step * i))))
        return pts

    async def evaluate(self, ctx: AgentContext, h: Hypothesis) -> Hypothesis:
        query = f"{h.statement} {' '.join(h.entities)}"
        hits = ctx.vectors.search(ctx.corpus_id, query, k=8)
        evidence: list[EvidenceItem] = []
        seen_papers: set[str] = set()
        for hit in hits:
            meta = hit["meta"]
            pid = meta.get("paper_id")
            if not pid or pid in seen_papers:
                continue
            seen_papers.add(pid)
            rec = ctx.session.papers.get(pid)
            snippet = hit["document"][:240]
            full_text = f"{rec.title} {rec.abstract}" if rec else hit["document"]
            stance = None
            # Stance LLM only via on-demand enrich endpoint — pipeline uses heuristics.
            if stance is None:
                stance, blended = _heuristic_stance(h.entities, full_text, hit["relevance"])
            else:
                blended = max(hit["relevance"], 0.4)
            title = meta.get("title", rec.title if rec else pid)
            evidence.append(
                EvidenceItem(
                    paperId=pid,
                    title=title,
                    source=meta.get("source", rec.source if rec else "derived"),
                    relevance=round(blended, 3),
                    stance=stance,  # type: ignore[arg-type]
                    snippet=snippet,
                    year=rec.year if rec else meta.get("year"),
                    url=_paper_url(ctx, pid, rec),
                )
            )

        # User uploads with entity overlap must be eligible even if vector rank is low.
        for rec in ctx.session.papers.values():
            if rec.source != "user_pdf" or rec.id in seen_papers:
                continue
            body = f"{rec.title}. {rec.abstract}. {rec.full_text_excerpt or ''}"
            overlap = _entity_overlap(h.entities, body)
            if overlap < 1:
                continue
            seen_papers.add(rec.id)
            snippet = (rec.abstract or rec.title)[:240]
            stance, blended = _heuristic_stance(h.entities, body, min(1.0, 0.45 + 0.15 * overlap))
            evidence.append(
                EvidenceItem(
                    paperId=rec.id,
                    title=rec.title,
                    source=rec.source,
                    relevance=round(blended, 3),
                    stance=stance,  # type: ignore[arg-type]
                    snippet=snippet,
                    year=rec.year,
                    url=resolve_paper_url(rec),
                )
            )
        if not evidence:
            for rec in list(ctx.session.papers.values())[:3]:
                evidence.append(
                    EvidenceItem(
                        paperId=rec.id, title=rec.title, source=rec.source,
                        relevance=0.3, stance="neutral",
                        snippet=(rec.abstract or rec.title)[:240], year=rec.year,
                        url=resolve_paper_url(rec),
                    )
                )
        h.evidence = evidence
        score, breakdown = self._score_detail(evidence)
        h.confidence = score
        h.confidenceBreakdown = breakdown
        h.confidenceExplanation = self._confidence_explanation(h, breakdown, score)
        h.history = self._history(ctx, evidence, h.confidence)
        support = breakdown.supportCount
        contradict = breakdown.contradictCount
        h.status = "contested" if contradict >= support and contradict > 0 else (
            "supported" if h.confidence >= 70 else "emerging"
        )
        h.subgraph = build_hypothesis_subgraph(
            ctx, h.entities, evidence_paper_ids=[e.paperId for e in h.evidence]
        )
        return h

    async def run(self, ctx: AgentContext) -> list[Hypothesis]:
        await ctx.stage("evidence")
        hyps = ctx.session.state.hypotheses
        with timer() as t:
            for h in hyps:
                await self.evaluate(ctx, h)
                await ctx.audit(
                    self.name, "Evidence scored",
                    detail=f"{h.statement[:60]} → {h.confidence}% ({h.status})",
                    params={
                        "hypothesis": h.id,
                        "support": h.confidenceBreakdown.supportCount if h.confidenceBreakdown else 0,
                        "contradict": h.confidenceBreakdown.contradictCount if h.confidenceBreakdown else 0,
                        "confidence": h.confidence,
                    },
                )
        await ctx.session.emit({
            "type": "hypotheses",
            "payload": [h.model_dump() for h in hyps],
        })
        await ctx.audit(self.name, "Evidence tracking complete", detail=f"{len(hyps)} hypotheses", duration_ms=t.elapsed_ms)
        return hyps
