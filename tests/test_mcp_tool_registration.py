from spotify_mcp.mcp.server import mcp_server


async def test_every_tool_has_a_non_empty_description() -> None:
    # Guards against a real bug we hit once: an f-string as a function's
    # first statement is NOT a docstring to Python (__doc__ comes back
    # None), so the tool silently loses its description for the model.
    tools = await mcp_server.list_tools()

    assert tools, "expected at least one registered tool"
    for tool in tools:
        assert tool.description, f"tool '{tool.name}' has no description"
