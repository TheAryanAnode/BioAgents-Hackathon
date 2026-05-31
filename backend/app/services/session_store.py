from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from app.models.schemas import PaperRecord, SessionState


@dataclass
class Session:
    state: SessionState
    papers: dict[str, PaperRecord] = field(default_factory=dict)
    # Per-session pub/sub queues for WebSocket subscribers.
    subscribers: list[asyncio.Queue] = field(default_factory=list)
    # Buffer of events emitted before any subscriber connected (replayed on connect).
    backlog: list[dict] = field(default_factory=list)
    done: bool = False

    def add_papers(self, records: list[PaperRecord]) -> None:
        for r in records:
            self.papers[r.id] = r

    async def emit(self, event: dict) -> None:
        self.backlog.append(event)
        for q in list(self.subscribers):
            await q.put(event)

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        # Replay backlog so a late-connecting client catches up.
        for ev in self.backlog:
            q.put_nowait(ev)
        self.subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        if q in self.subscribers:
            self.subscribers.remove(q)


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}

    def create(self, session_id: str, query: str) -> Session:
        sess = Session(state=SessionState(sessionId=session_id, query=query))
        self._sessions[session_id] = sess
        return sess

    def get(self, session_id: str) -> Session | None:
        return self._sessions.get(session_id)


store = SessionStore()
