"""Bridge to the notebook open in the user's Colab browser tab.

Colab's web page has an MCP server built in. When a notebook is opened with
``#mcpProxyToken=<token>&mcpProxyPort=<port>`` at the end of its address, the page
connects to a websocket on this computer and offers tools that add, edit and run cells in
that notebook, so the user watches the work happen cell by cell on whatever runtime the
notebook uses. This module runs that websocket and an MCP client over it. It speaks the
same protocol as Google's colab-mcp (Apache-2.0).

The websocket listens on localhost only, accepts only Colab's origins, and needs a random
token that travels in the address fragment (browsers never send fragments to servers).
"""

import asyncio
import secrets
from typing import Optional

import anyio
import mcp.types as types
import websockets
from mcp import ClientSession
from mcp.shared.message import SessionMessage

COLAB = "https://colab.research.google.com"
ORIGINS = [COLAB, "https://colab.google.com"]
SCRATCH_NOTEBOOK = COLAB + "/notebooks/empty.ipynb"


class ColabUI:
    def __init__(self) -> None:
        self.token = secrets.token_urlsafe(16)
        self.port = 0
        self.session: Optional[ClientSession] = None
        self.ready = asyncio.Event()
        self._server = None

    async def start(self) -> None:
        if self._server is None:
            self._server = await websockets.serve(
                self._handle, "localhost", 0, subprotocols=["mcp"], origins=ORIGINS,
                process_request=self._check_token)
            self.port = self._server.sockets[0].getsockname()[1]

    async def stop(self) -> None:
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

    def url(self, notebook_url: str = "") -> str:
        base = (notebook_url or SCRATCH_NOTEBOOK).split("#")[0]
        return f"{base}#mcpProxyToken={self.token}&mcpProxyPort={self.port}"

    def _check_token(self, connection, request):
        if (f"access_token={self.token}" in request.path
                or request.headers.get("Authorization") == f"Bearer {self.token}"):
            return None
        return connection.respond(403, "Bad or missing token\n")

    async def _handle(self, ws) -> None:
        if self.session is not None:
            await ws.close(1013, "Another Colab tab is already connected")
            return
        to_client, from_ws = anyio.create_memory_object_stream(0)
        to_ws, from_client = anyio.create_memory_object_stream(0)

        async def pump_in():
            try:
                async for raw in ws:
                    try:
                        msg = SessionMessage(types.JSONRPCMessage.model_validate_json(raw))
                    except Exception as exc:  # a bad frame is reported to the session, not fatal
                        msg = exc
                    await to_client.send(msg)
            except websockets.ConnectionClosed:
                pass

        async def pump_out():
            try:
                async for msg in from_client:
                    await ws.send(msg.message.model_dump_json(by_alias=True, exclude_none=True))
            except websockets.ConnectionClosed:
                pass

        try:
            async with anyio.create_task_group() as tg:
                tg.start_soon(pump_in)
                tg.start_soon(pump_out)
                async with ClientSession(from_ws, to_ws) as session:
                    await session.initialize()
                    self.session = session
                    self.ready.set()
                    await ws.wait_closed()
                tg.cancel_scope.cancel()
        finally:
            self.session = None
            self.ready.clear()
