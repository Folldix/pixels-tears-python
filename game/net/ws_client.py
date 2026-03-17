from __future__ import annotations

import asyncio
import json
import threading
from dataclasses import dataclass
from queue import Queue
from typing import Any

import websockets


@dataclass
class WsClient:
    url: str
    incoming: "Queue[dict[str, Any]]"
    outgoing: "Queue[dict[str, Any]]"

    _thread: threading.Thread | None = None
    _stop: threading.Event = threading.Event()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name="ws-client", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def send(self, payload: dict[str, Any]) -> None:
        self.outgoing.put(payload)

    def _run(self) -> None:
        asyncio.run(self._main())

    async def _main(self) -> None:
        while not self._stop.is_set():
            try:
                async with websockets.connect(self.url) as ws:
                    await self._pump(ws)
            except Exception:
                await asyncio.sleep(1.0)

    async def _pump(self, ws: websockets.WebSocketClientProtocol) -> None:
        async def sender() -> None:
            while not self._stop.is_set():
                payload = await asyncio.to_thread(self.outgoing.get)
                try:
                    await ws.send(json.dumps(payload, ensure_ascii=False))
                except Exception:
                    return

        async def receiver() -> None:
            while not self._stop.is_set():
                try:
                    msg = await ws.recv()
                except Exception:
                    return
                try:
                    data = json.loads(msg)
                except Exception:
                    continue
                self.incoming.put(data)

        await asyncio.gather(sender(), receiver())

