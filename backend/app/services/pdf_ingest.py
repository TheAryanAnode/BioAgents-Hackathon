from __future__ import annotations

import hashlib
import io
import re

from app.core.config import get_settings
from app.models.schemas import PaperRecord

_DOI_RE = re.compile(r"10\.\d{4,9}/[-._;()/:a-z0-9]+", re.IGNORECASE)
_ARXIV_RE = re.compile(r"arXiv:\s*(\d{4}\.\d{4,5})", re.IGNORECASE)


def extract_pdf(data: bytes) -> tuple[str, int]:
    """Return (text, page_count). Caps pages/chars for safety."""
    settings = get_settings()
    try:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(data))
        pages = reader.pages[: settings.max_pdf_pages]
        text = "\n".join((p.extract_text() or "") for p in pages)
        return text[: settings.max_pdf_chars], len(reader.pages)
    except Exception:
        return "", 0


def guess_title(text: str, fallback: str) -> str:
    for line in text.splitlines():
        line = line.strip()
        if 15 <= len(line) <= 180 and not line.lower().startswith(("abstract", "doi", "http")):
            return line
    return fallback


def find_external_ids(text: str) -> dict[str, str]:
    ids: dict[str, str] = {}
    doi = _DOI_RE.search(text[:4000])
    if doi:
        ids["DOI"] = doi.group(0).rstrip(".")
    arxiv = _ARXIV_RE.search(text[:4000])
    if arxiv:
        ids["arXiv"] = arxiv.group(1)
    return ids


def build_record(
    text: str,
    filename: str,
    title_override: str | None,
    doi_override: str | None,
) -> tuple[PaperRecord, str]:
    """Normalize extracted PDF text into a PaperRecord. Returns (record, checksum)."""
    checksum = hashlib.sha256(text.encode("utf-8", "ignore")).hexdigest()[:16]
    paper_id = f"user_{checksum}"
    external_ids = find_external_ids(text)
    if doi_override:
        key = "arXiv" if re.match(r"^\d{4}\.\d{4,5}$", doi_override.strip()) else "DOI"
        external_ids[key] = doi_override.strip()

    title = title_override or guess_title(text, filename.rsplit(".", 1)[0])
    # Abstract heuristic: text following an "Abstract" header, else the head.
    abstract = ""
    m = re.search(r"abstract[\s:]*", text, re.IGNORECASE)
    if m:
        abstract = text[m.end() : m.end() + 900].strip()
    if not abstract:
        abstract = text[:900].strip()

    year_m = re.search(r"\b(19|20)\d{2}\b", text[:2000])
    year = int(year_m.group(0)) if year_m else None

    record = PaperRecord(
        id=paper_id,
        title=title,
        authors=[],
        year=year,
        abstract=abstract,
        full_text_excerpt=text[:6000],
        citation_count=0,
        source="user_pdf",
        external_ids=external_ids,
        url=None,
    )
    return record, checksum
