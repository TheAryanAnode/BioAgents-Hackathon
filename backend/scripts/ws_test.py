import asyncio
import json
from collections import Counter

import httpx
import websockets


async def main():
    async with httpx.AsyncClient() as c:
        r = await c.post("http://localhost:8000/api/research", json={"query": "autism genomics"})
        sid = r.json()["sessionId"]
    print("session", sid)

    counts = Counter()
    stages = []
    async with websockets.connect(f"ws://localhost:8000/ws/{sid}") as ws:
        try:
            while True:
                msg = await asyncio.wait_for(ws.recv(), timeout=15)
                ev = json.loads(msg)
                counts[ev["type"]] += 1
                if ev["type"] == "stage":
                    stages.append(ev["payload"]["stage"])
                if ev["type"] == "done":
                    break
        except asyncio.TimeoutError:
            print("timeout waiting for events")

    print("event counts:", dict(counts))
    print("stages:", stages)


asyncio.run(main())
