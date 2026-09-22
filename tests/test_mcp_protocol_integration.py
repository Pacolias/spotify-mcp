"""Exercises the MCP server through a real client/server protocol session
(in-memory transport, real JSON-RPC-style serialization) instead of calling
the registered handler functions directly in-process. Closes the gap noted
in journal entry 11: everything else tests the underlying Python functions,
or `mcp_server.list_tools()` called directly — neither proves a tool still
works once its arguments/results actually cross the protocol boundary.
"""

import httpx
import respx
from mcp.client._memory import InMemoryTransport
from mcp.client.session import ClientSession

from spotify_mcp.mcp.server import mcp_server
from spotify_mcp.spotify.client import SPOTIFY_API_BASE


async def test_ping_round_trips_over_a_real_protocol_session() -> None:
    async with InMemoryTransport(mcp_server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("ping", {})

    assert not result.is_error
    assert [c.text for c in result.content if c.type == "text"] == ["pong"]


async def test_list_tools_over_a_real_protocol_session_matches_registration() -> None:
    async with InMemoryTransport(mcp_server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()

    names = {t.name for t in tools.tools}
    assert "search_track" in names
    assert "import_youtube_playlist" in names
    for tool in tools.tools:
        assert tool.description, f"tool '{tool.name}' lost its description over the wire"


@respx.mock
async def test_search_track_with_arguments_over_a_real_protocol_session(logged_in) -> None:
    respx.get(f"{SPOTIFY_API_BASE}/search").mock(
        return_value=httpx.Response(
            200,
            json={
                "tracks": {
                    "items": [
                        {
                            "id": "abc123",
                            "name": "Bohemian Rhapsody",
                            "artists": [{"name": "Queen"}],
                            "album": {"name": "A Night at the Opera"},
                            "external_urls": {"spotify": "https://open.spotify.com/track/abc123"},
                        }
                    ]
                }
            },
        )
    )

    async with InMemoryTransport(mcp_server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("search_track", {"query": "Bohemian Rhapsody"})

    assert not result.is_error
    text = "\n".join(c.text for c in result.content if c.type == "text")
    assert "Bohemian Rhapsody — Queen (A Night at the Opera) — id: abc123" in text
