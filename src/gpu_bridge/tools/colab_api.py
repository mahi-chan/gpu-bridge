"""Google's Colab API: create Colab runtimes from code, with no pasted line."""

import json

from ..connectors import colab_api


def register(mcp):
    @mcp.tool()
    async def colab_api_tools() -> str:
        """List the tools of Google's Colab API (create_runtime, list_runtime_specs,
        list_runtimes, get_runtime, execute_code, create_session, get_subscription, ...)
        with their arguments. Call them with ``colab_api_call``. Needs the one-time Google
        Cloud setup that the error message describes."""
        try:
            listed = await colab_api.session_call(None)
        except RuntimeError as exc:
            return str(exc)
        return "\n".join(f"- {t.name}: {t.description or ''}\n  arguments: {json.dumps(t.inputSchema)}"
                         for t in listed.tools)

    @mcp.tool()
    async def colab_api_call(tool: str, arguments: dict | None = None) -> str:
        """Call one tool of Google's Colab API (see ``colab_api_tools``). Typical use:
        ``list_runtime_specs``, then ``create_runtime`` with a spec the user can use, then
        ``execute_code``. Runtimes bill the user's Colab quota: create only what is needed and
        ``delete_runtime`` only when the user asks."""
        try:
            result = await colab_api.session_call(tool, arguments)
        except RuntimeError as exc:
            return str(exc)
        text = "\n".join(c.text for c in result.content if c.type == "text") or "(no output)"
        return ("Colab API reported an error:\n" + text) if result.isError else text
