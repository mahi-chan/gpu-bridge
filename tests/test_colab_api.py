"""Google's Colab API client, against a local fake of its MCP endpoint."""

import asyncio
import socket
import threading
import time
from unittest import mock

import pytest
import uvicorn
from mcp.server.fastmcp import FastMCP

from gpu_bridge.connectors import colab_api
from gpu_bridge.tools import colab_api as colab_api_tools


class HeaderEcho:
    """Records the headers of every request so the test can check what was sent."""

    def __init__(self, app):
        self.app, self.seen = app, []

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            self.seen.append(dict(scope["headers"]))
        await self.app(scope, receive, send)


@pytest.fixture
def fake_colab():
    fake = FastMCP("fake-colab", host="127.0.0.1")

    @fake.tool()
    def list_runtime_specs() -> str:
        return "T4 eligible"

    @fake.tool()
    def create_runtime(requestId: str) -> str:
        return f"created for {requestId}"

    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    echo = HeaderEcho(fake.streamable_http_app())
    server = uvicorn.Server(uvicorn.Config(echo, host="127.0.0.1", port=port, log_level="error"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    while not server.started:
        time.sleep(0.05)
    with mock.patch.object(colab_api, "URL", f"http://127.0.0.1:{port}/mcp"), \
            mock.patch.dict("os.environ", {"GPU_BRIDGE_GOOGLE_TOKEN": "tok", "GPU_BRIDGE_GOOGLE_PROJECT": "proj"}):
        yield echo
    server.should_exit = True
    thread.join(5)


def test_tools_are_listed_and_called_with_credentials(fake_colab):
    mcp = FastMCP("t")
    colab_api_tools.register(mcp)
    listed = asyncio.run(mcp.call_tool("colab_api_tools", {}))
    assert "create_runtime" in str(listed)
    out = asyncio.run(mcp.call_tool("colab_api_call", {"tool": "create_runtime",
                                                       "arguments": {"requestId": "r1"}}))
    assert "created for r1" in str(out)
    sent = fake_colab.seen[0]
    assert sent[b"authorization"] == b"Bearer tok" and sent[b"x-goog-user-project"] == b"proj"


def test_missing_setup_says_what_to_do():
    mcp = FastMCP("t")
    colab_api_tools.register(mcp)
    with mock.patch.dict("os.environ", {}, clear=True), mock.patch.object(colab_api, "_gcloud", return_value=""):
        out = asyncio.run(mcp.call_tool("colab_api_call", {"tool": "list_runtimes"}))
    assert "gcloud services enable colaboratory.googleapis.com" in str(out)
