"""Client for Google's Colab API MCP server (https://colaboratory.googleapis.com/mcp).

It creates and lists Colab runtimes, runs code in them and reports the subscription. It
needs a Google Cloud project with the Colab API enabled and a bearer token for your
account; gcloud supplies both, or set GPU_BRIDGE_GOOGLE_TOKEN and GPU_BRIDGE_GOOGLE_PROJECT.
Each call opens its own short connection: the runtimes live on Google's side.
"""

import os
import subprocess

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

URL = "https://colaboratory.googleapis.com/mcp"

SETUP = """Google's Colab API is not set up. Once:
1. Install the Google Cloud CLI (https://cloud.google.com/sdk/docs/install) and run
   `gcloud auth application-default login`.
2. Pick the project: `gcloud config set project PROJECT_ID`.
3. Enable the API in it: `gcloud services enable colaboratory.googleapis.com`.
Tokens last about an hour; gpu-bridge asks gcloud for a fresh one on every call."""


def _gcloud(*args: str) -> str:
    try:
        done = subprocess.run(["gcloud", *args], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return done.stdout.strip() if done.returncode == 0 else ""


def headers() -> dict:
    token = os.environ.get("GPU_BRIDGE_GOOGLE_TOKEN") or _gcloud("auth", "application-default",
                                                                 "print-access-token")
    project = os.environ.get("GPU_BRIDGE_GOOGLE_PROJECT") or _gcloud("config", "get-value", "project")
    if not token or not project:
        raise RuntimeError(SETUP)
    return {"Authorization": f"Bearer {token}", "x-goog-user-project": project}


async def session_call(tool: str | None, arguments: dict | None = None):
    """List the server's tools (tool is None) or call one; returns the MCP result."""
    async with streamablehttp_client(URL, headers=headers()) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            if tool is None:
                return await session.list_tools()
            return await session.call_tool(tool, arguments or {})
