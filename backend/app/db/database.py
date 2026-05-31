from __future__ import annotations

import datetime as dt
from pathlib import Path

from sqlalchemy import (
    JSON,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    sessionmaker,
)

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


class SessionRow(Base):
    __tablename__ = "sessions"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    query: Mapped[str] = mapped_column(String)
    created_at: Mapped[str] = mapped_column(String, default=lambda: dt.datetime.utcnow().isoformat())


class PaperRow(Base):
    __tablename__ = "papers"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    session_id: Mapped[str] = mapped_column(String, ForeignKey("sessions.id"))
    title: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String)
    year: Mapped[int] = mapped_column(Integer, nullable=True)
    data: Mapped[dict] = mapped_column(JSON)


class UploadRow(Base):
    """Provenance for user-uploaded documents (regulatory traceability)."""

    __tablename__ = "uploads"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    session_id: Mapped[str] = mapped_column(String, ForeignKey("sessions.id"))
    paper_id: Mapped[str] = mapped_column(String)
    filename: Mapped[str] = mapped_column(String)
    checksum: Mapped[str] = mapped_column(String)
    pages: Mapped[int] = mapped_column(Integer, default=0)
    chars: Mapped[int] = mapped_column(Integer, default=0)
    stored_path: Mapped[str] = mapped_column(String, nullable=True)
    created_at: Mapped[str] = mapped_column(String, default=lambda: dt.datetime.utcnow().isoformat())


class HypothesisRow(Base):
    __tablename__ = "hypotheses"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    session_id: Mapped[str] = mapped_column(String, ForeignKey("sessions.id"))
    statement: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float)
    data: Mapped[dict] = mapped_column(JSON)


class AuditRow(Base):
    __tablename__ = "audit"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    session_id: Mapped[str] = mapped_column(String, ForeignKey("sessions.id"))
    ts: Mapped[str] = mapped_column(String)
    agent: Mapped[str] = mapped_column(String)
    action: Mapped[str] = mapped_column(String)
    data: Mapped[dict] = mapped_column(JSON)


_settings = get_settings()
_db_path = Path(_settings.data_dir) / "synthesisos.db"
engine = create_engine(f"sqlite:///{_db_path}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db() -> None:
    Base.metadata.create_all(engine)
