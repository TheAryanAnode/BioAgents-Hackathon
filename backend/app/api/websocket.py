from __future__ import annotations

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.session_store import store

router = APIRouter()


@router.websocket("/ws/{session_id}")
async def ws_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    session = store.get(session_id)
    if not session:
        await websocket.send_json({"type": "error", "payload": {"message": "unknown session"}})
        await websocket.close()
        return

    # Full state snapshot so clients that connect late (or miss events) still hydrate.
    await websocket.send_json(
        {
            "type": "snapshot",
            "payload": {
                **session.state.model_dump(),
                "done": session.done,
            },
        }
    )

    queue = session.subscribe()
    try:
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=30.0)
                await websocket.send_json(event)
            except asyncio.TimeoutError:
                # keep-alive ping so idle connections survive proxies (ignored by client)
                await websocket.send_json({"type": "ping", "payload": {}})
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        session.unsubscribe(queue)
