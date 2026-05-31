from __future__ import annotations

import xml.etree.ElementTree as ET

import httpx

from app.core.config import get_settings
from app.models.schemas import PaperRecord

_ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
_EFETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"


async def search(query: str, limit: int = 12) -> list[PaperRecord]:
    settings = get_settings()
    common = {"db": "pubmed", "retmode": "xml"}
    if settings.entrez_email:
        common["email"] = settings.entrez_email
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            es = await client.get(
                _ESEARCH,
                params={**common, "term": query, "retmax": str(limit), "sort": "relevance"},
            )
            if es.status_code != 200:
                return []
            ids = [i.text for i in ET.fromstring(es.text).findall(".//Id") if i.text]
            if not ids:
                return []
            ef = await client.get(
                _EFETCH, params={**common, "id": ",".join(ids)}
            )
            if ef.status_code != 200:
                return []
            root = ET.fromstring(ef.text)
    except Exception:
        return []

    records: list[PaperRecord] = []
    for art in root.findall(".//PubmedArticle"):
        pmid_el = art.find(".//PMID")
        title_el = art.find(".//ArticleTitle")
        if pmid_el is None or title_el is None:
            continue
        pmid = pmid_el.text or ""
        abstract = " ".join(
            (t.text or "") for t in art.findall(".//AbstractText")
        ).strip()
        year_el = art.find(".//PubDate/Year")
        year = int(year_el.text) if year_el is not None and (year_el.text or "").isdigit() else None
        authors = []
        for a in art.findall(".//Author"):
            last = a.find("LastName")
            fore = a.find("ForeName")
            if last is not None:
                authors.append(" ".join(filter(None, [fore.text if fore is not None else None, last.text])))
        records.append(
            PaperRecord(
                id=f"pubmed_{pmid}",
                title="".join(title_el.itertext()).strip(),
                authors=authors[:8],
                year=year,
                abstract=abstract,
                source="pubmed",
                external_ids={"PMID": pmid},
                url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            )
        )
    return records
