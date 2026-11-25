"""The Colab notebook bridge, against a fake Colab page speaking MCP over the websocket."""

import asyncio
import json
from unittest import mock

import pytest
import websockets
from mcp.server.fastmcp import FastMCP

from gpu_bridge.connectors.colab_ui import COLAB, ColabUI
from gpu_bridge.tools import colab_ui as colab_ui_tools


async def fake_colab_page(port, token, origin=COLAB, cells=None):
    """Plays the Colab web page: connects to the bridge and serves one notebook tool."""
    cells = [] if cells is None else cells
    async with websockets.connect(f"ws://localhost:{port}/?access_token={token}",
                                  origin=origin, subprotocols=["mcp"]) as ws:
        async for raw in ws:
            msg = json.loads(raw)
            if "id" not in msg:
                continue  # notifications need no answer
            if msg["method"] == "initialize":
                result = {"protocolVersion": msg["params"]["protocolVersion"], "capabilities": {"tools": {}},
                          "serverInfo": {"name": "colab", "version": "0"}}
            elif msg["method"] == "tools/list":
                result = {"tools": [{"name": "add_code_cell", "description": "Add a code cell",
                                     "inputSchema": {"type": "object", "properties": {"code": {"type": "string"}}}}]}
            else:
                cells.append(msg["params"]["arguments"]["code"])
                result = {"content": [{"type": "text", "text": f"cell {len(cells)} added"}], "isError": False}
            await ws.send(json.dumps({"jsonrpc": "2.0", "id": msg["id"], "result": result}))


def call(mcp, name, args):
    return mcp.call_tool(name, args)


def test_cells_reach_the_page():
    async def scenario():
        ui, mcp, cells = ColabUI(), FastMCP("t"), []
        colab_ui_tools.register(mcp, ui)
        await ui.start()
        page = asyncio.create_task(fake_colab_page(ui.port, ui.token, cells=cells))
        with mock.patch("webbrowser.open_new_tab") as opened:
            listed = await call(mcp, "colab_ui_connect", {"wait_seconds": 5})
        assert f"mcpProxyToken={ui.token}&mcpProxyPort={ui.port}" in opened.call_args.args[0]
        assert "add_code_cell" in str(listed)
        out = await call(mcp, "colab_ui_call", {"tool": "add_code_cell", "arguments": {"code": "print(1)"}})
        assert "cell 1 added" in str(out) and cells == ["print(1)"]
        page.cancel()
        await ui.stop()
    asyncio.run(scenario())


@pytest.mark.parametrize("origin,good_token", [("https://evil.example", True), (COLAB, False)])
def test_other_sites_and_wrong_tokens_are_refused(origin, good_token):
    async def scenario():
        ui = ColabUI()
        await ui.start()
        with pytest.raises(websockets.InvalidStatus):
            await fake_colab_page(ui.port, ui.token if good_token else "wrong", origin=origin)
        assert ui.session is None
        await ui.stop()
    asyncio.run(scenario())


def test_call_without_a_page_says_what_to_do():
    mcp = FastMCP("t")
    colab_ui_tools.register(mcp, ColabUI())
    out = asyncio.run(call(mcp, "colab_ui_call", {"tool": "add_code_cell"}))
    assert "colab_ui_connect" in str(out)
