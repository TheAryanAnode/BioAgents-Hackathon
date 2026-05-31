from __future__ import annotations

import re
import xml.etree.ElementTree as ET

import httpx

from app.models.schemas import PaperRecord

_BASE = "http://export.arxiv.org/api/query"
_NS = {"a": "http://www.w3.org/2005/Atom"}


async def search(query: str, limit: int = 10) -> list[PaperRecord]:
    params = {
        "search_query": f"all:{query}",
        "start": "0",
        "max_results": str(limit),
        "sortBy": "relevance",
    }
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(_BASE, params=params)
            if resp.status_code != 200:
                return []
            root = ET.fromstring(resp.text)
    except Exception:
        return []

    records: list[PaperRecord] = []
    for entry in root.findall("a:entry", _NS):
        title_el = entry.find("a:title", _NS)
        summary_el = entry.find("a:summary", _NS)
        id_el = entry.find("a:id", _NS)
        published = entry.find("a:published", _NS)
        if title_el is None or id_el is None:
            continue
        title = re.sub(r"\s+", " ", (title_el.text or "")).strip()
        arxiv_id = (id_el.text or "").split("/")[-1]
        year = None
        if published is not None and published.text:
            year = int(published.text[:4])
        authors = [
            (a.find("a:name", _NS).text or "")
            for a in entry.findall("a:author", _NS)
            if a.find("a:name", _NS) is not None
        ]
        records.append(
            PaperRecord(
                id=f"arxiv_{arxiv_id}",
                title=title,
                authors=authors[:8],
                year=year,
                abstract=re.sub(r"\s+", " ", (summary_el.text or "")).strip() if summary_el is not None else "",
                source="arxiv",
                external_ids={"arXiv": arxiv_id},
                url=id_el.text,
            )
        )
    return records
