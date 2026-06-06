from __future__ import annotations

import datetime as dt
import time
import uuid
from dataclasses import dataclass, field

from app.core.llm import LLM
from app.db.database import AuditRow, SessionLocal
from app.models.schemas import AuditEntry
from app.services.embeddings import VectorStore
from app.services.session_store import Session


def now_iso() -> str:
    return dt.datetime.utcnow().isoformat()


@dataclass
class AgentContext:
    session: Session
    llm: LLM
    vectors: VectorStore
    # Scratch space shared across pipeline stages (entity maps, relations, etc.).
    work: dict = field(default_factory=dict)

    @property
    def corpus_id(self) -> str:
        return self.session.state.sessionId

    @property
    def query(self) -> str:
        return self.session.state.query

    async def audit(
        self,
        agent: str,
        action: str,
        detail: str = "",
        params: dict | None = None,
        duration_ms: int | None = None,
        status: str = "ok",
    ) -> None:
        entry = AuditEntry(
            id=str(uuid.uuid4()),
            ts=now_iso(),
            agent=agent,
            action=action,
            detail=detail,
            params=params or {},
            durationMs=duration_ms,
            status=status,  # type: ignore[arg-type]
        )
        self.session.state.audit.append(entry)
        await self.session.emit({"type": "audit", "payload": entry.model_dump()})
        # Persist for regulatory traceability.
        try:
            with SessionLocal() as db:
                db.add(
                    AuditRow(
                        id=entry.id,
                        session_id=self.corpus_id,
                        ts=entry.ts,
                        agent=agent,
                        action=action,
                        data=entry.model_dump(),
                    )
                )
                db.commit()
        except Exception:
            pass

    async def stage(self, stage: str) -> None:
        self.session.state.stage = stage
        await self.session.emit({"type": "stage", "payload": {"stage": stage}})


class timer:
    def __enter__(self):
        self._t = time.perf_counter()
        return self

    def __exit__(self, *a):
        self.ms = int((time.perf_counter() - self._t) * 1000)

    @property
    def elapsed_ms(self) -> int:
        return int((time.perf_counter() - self._t) * 1000)
