from __future__ import annotations

from app.agents.base import AgentContext, timer
from app.models.schemas import ConfidencePoint, EvidenceItem, Hypothesis

_CONTRADICT_CUES = (
    "no association", "not associated", "failed to", "no significant",
    "unrelated", "independent of", "no evidence", "does not", "contradict",
    "no link", "ruled out",
)


def _entity_overlap(entities: list[str], text: str) -> int:
    low = text.lower()
    return sum(1 for e in entities if e and e.lower() in low)


def _heuristic_stance(entities: list[str], text: str, relevance: float) -> tuple[str, float]:
    """Return (stance, blended_relevance) using the full paper text plus the
    vector relevance. Entity overlap drives a credible support signal even when
    the embedding backend is the hashing fallback."""
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

    def _score(self, evidence: list[EvidenceItem]) -> int:
        support = sum(1 for e in evidence if e.stance == "support")
        contradict = sum(1 for e in evidence if e.stance == "contradict")
        rel = sum(e.relevance for e in evidence) / max(1, len(evidence))
        raw = 50 + 12 * support - 18 * contradict + rel * 20
        return max(8, min(95, int(round(raw))))

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
            # Classify against the fuller paper text for a stronger signal.
            full_text = f"{rec.title} {rec.abstract}" if rec else hit["document"]
            stance = None
            if ctx.llm.enabled:
                stance = self._stance_llm(ctx, h.statement, snippet)
            if stance is None:
                stance, blended = _heuristic_stance(h.entities, full_text, hit["relevance"])
            else:
                blended = max(hit["relevance"], 0.4)
            evidence.append(
                EvidenceItem(
                    paperId=pid,
                    title=meta.get("title", rec.title if rec else pid),
                    source=meta.get("source", rec.source if rec else "derived"),
                    relevance=round(blended, 3),
                    stance=stance,  # type: ignore[arg-type]
                    snippet=snippet,
                    year=rec.year if rec else meta.get("year"),
                    url=rec.url if rec else None,
                )
            )
        # Ensure at least a little signal so the panel isn't empty.
        if not evidence:
            for rec in list(ctx.session.papers.values())[:3]:
                evidence.append(
                    EvidenceItem(
                        paperId=rec.id, title=rec.title, source=rec.source,
                        relevance=0.3, stance="neutral",
                        snippet=(rec.abstract or rec.title)[:240], year=rec.year, url=rec.url,
                    )
                )
        h.evidence = evidence
        h.confidence = self._score(evidence)
        h.history = self._history(ctx, evidence, h.confidence)
        support = sum(1 for e in evidence if e.stance == "support")
        contradict = sum(1 for e in evidence if e.stance == "contradict")
        h.status = "contested" if contradict >= support and contradict > 0 else (
            "supported" if h.confidence >= 70 else "emerging"
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
                        "support": sum(1 for e in h.evidence if e.stance == "support"),
                        "contradict": sum(1 for e in h.evidence if e.stance == "contradict"),
                        "confidence": h.confidence,
                    },
                )
        await ctx.session.emit({
            "type": "hypotheses",
            "payload": [h.model_dump() for h in hyps],
        })
        await ctx.audit(self.name, "Evidence tracking complete", detail=f"{len(hyps)} hypotheses", duration_ms=t.elapsed_ms)
        return hyps
