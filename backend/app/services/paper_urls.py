"""Resolve a canonical public URL for a paper record."""

from __future__ import annotations

import re

from app.models.schemas import PaperRecord

_DOI_PREFIX = re.compile(r"^https?://(dx\.)?doi\.org/", re.I)


def resolve_paper_url(record: PaperRecord) -> str | None:
    if record.url and record.url.startswith("http"):
        return record.url

    ids = record.external_ids or {}
    doi = ids.get("DOI") or ids.get("doi")
    if doi:
        doi = _DOI_PREFIX.sub("", doi.strip())
        return f"https://doi.org/{doi}"

    pmid = ids.get("PMID") or ids.get("PubMed") or ids.get("pmid")
    if pmid:
        return f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"

    arxiv = ids.get("arXiv") or ids.get("arxiv")
    if arxiv:
        arxiv = arxiv.replace("arxiv:", "").strip()
        return f"https://arxiv.org/abs/{arxiv}"

    if record.id.startswith("s2_"):
        pid = record.id[3:]
        return f"https://www.semanticscholar.org/paper/{pid}"

    if record.source == "pubmed" and record.id.startswith("pubmed_"):
        return f"https://pubmed.ncbi.nlm.nih.gov/{record.id[7:]}/"

    if record.source == "arxiv" and record.id.startswith("arxiv_"):
        return f"https://arxiv.org/abs/{record.id[6:]}"

    return None
