from spotify_mcp.mcp.server import mcp_server


async def test_every_tool_has_a_non_empty_description() -> None:
    # Guards against a real bug we hit once: an f-string as a function's
    # first statement is NOT a docstring to Python (__doc__ comes back
    # None), so the tool silently loses its description for the model.
    tools = await mcp_server.list_tools()

    assert tools, "expected at least one registered tool"
    for tool in tools:
        assert tool.description, f"tool '{tool.name}' has no description"


async def test_every_resource_has_a_non_empty_description() -> None:
    resources = await mcp_server.list_resources()
    templates = await mcp_server.list_resource_templates()

    assert resources or templates, "expected at least one registered resource"
    for resource in [*resources, *templates]:
        assert resource.description, f"resource '{resource.name}' has no description"


async def test_every_prompt_has_a_non_empty_description() -> None:
    prompts = await mcp_server.list_prompts()

    assert prompts, "expected at least one registered prompt"
    for prompt in prompts:
        assert prompt.description, f"prompt '{prompt.name}' has no description"
