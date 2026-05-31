from __future__ import annotations

import httpx

from app.models.schemas import PaperRecord

_BASE = "https://api.semanticscholar.org/graph/v1/paper/search"
_FIELDS = "title,abstract,year,authors,citationCount,externalIds,url"


async def search(query: str, limit: int = 20) -> list[PaperRecord]:
    """Query the Semantic Scholar Academic Graph. Returns [] on any failure."""
    params = {"query": query, "fields": _FIELDS, "limit": str(min(limit, 100))}
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(_BASE, params=params)
            if resp.status_code != 200:
                return []
            data = resp.json()
    except Exception:
        return []

    records: list[PaperRecord] = []
    for p in data.get("data", []) or []:
        if not p.get("title"):
            continue
        pid = p.get("paperId") or p.get("externalIds", {}).get("DOI") or p["title"][:40]
        records.append(
            PaperRecord(
                id=f"s2_{pid}",
                title=p["title"],
                authors=[a.get("name", "") for a in (p.get("authors") or [])][:8],
                year=p.get("year"),
                abstract=p.get("abstract") or "",
                citation_count=p.get("citationCount") or 0,
                source="semantic_scholar",
                external_ids={k: str(v) for k, v in (p.get("externalIds") or {}).items()},
                url=p.get("url"),
            )
        )
    return records
