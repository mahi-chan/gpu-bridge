"""Colab notebook tools: work shown cell by cell in the notebook open in the user's browser."""

import asyncio
import base64
import json
import webbrowser

from mcp.server.fastmcp import Image

from ..connectors.colab_ui import ColabUI


def register(mcp, ui: ColabUI | None = None):
    ui = ui or ColabUI()

    @mcp.tool()
    async def colab_ui_connect(notebook_url: str = "", wait_seconds: int = 60) -> str:
        """Connect to a Colab notebook in the user's browser, so work appears there as cells.

        Opens the notebook in the browser on this computer (``notebook_url``, or a new
        scratch notebook when empty) and waits for the page to connect. The code runs on
        whatever runtime that notebook uses, so the user picks the GPU there
        (Runtime > Change runtime type). Returns the notebook tools Colab offers, with
        their arguments; call them with ``colab_ui_call``.
        """
        await ui.start()
        if ui.session is None:
            url = ui.url(notebook_url)
            webbrowser.open_new_tab(url)
            try:
                await asyncio.wait_for(ui.ready.wait(), wait_seconds)
            except asyncio.TimeoutError:
                return ("The Colab page did not connect. Ask the user to open this address in "
                        f"their browser on this computer, then call colab_ui_connect again:\n{url}")
        listed = await ui.session.list_tools()
        lines = ["Connected to the Colab notebook. Its tools (call them with colab_ui_call):"]
        for tool in listed.tools:
            lines.append(f"- {tool.name}: {tool.description or ''}\n"
                         f"  arguments: {json.dumps(tool.inputSchema)}")
        return "\n".join(lines)

    @mcp.tool()
    async def colab_ui_call(tool: str, arguments: dict | None = None) -> list:
        """Call one of the Colab notebook's tools (listed by colab_ui_connect), e.g. to add
        a code cell and run it. The user sees the cell and its output in their browser."""
        if ui.session is None:
            return ["No Colab notebook is connected. Call colab_ui_connect first."]
        result = await ui.session.call_tool(tool, arguments or {})
        parts: list = ["Colab reported an error:"] if result.isError else []
        for item in result.content:
            if item.type == "text":
                parts.append(item.text)
            elif item.type == "image":
                parts.append(Image(data=base64.b64decode(item.data),
                                   format=item.mimeType.split("/")[-1]))
        return parts or ["(no output)"]
