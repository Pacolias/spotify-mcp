from spotify_mcp.mcp.server import mcp_server


@mcp_server.prompt()
def build_playlist(theme: str, num_songs: int = 10, genre: str = "") -> str:
    """Build a Spotify playlist around a theme, using the model's own music
    knowledge instead of generic search phrases."""
    genre_clause = f", leaning {genre}" if genre else ""
    return (
        f'Build me a Spotify playlist for "{theme}"{genre_clause}, with about {num_songs} songs.\n\n'
        "Pick specific real songs and artists from your own knowledge that fit — searching Spotify "
        'with generic mood/genre phrases (e.g. "lofi coding beats") tends to return poor, off-topic '
        "matches. For each song: use search_track to find it, and check the result's artist actually "
        "matches what you intended. Then use create_user_playlist to make the playlist, and add_tracks "
        "to add the matches. Tell me the final tracklist and the playlist link when you're done."
    )


@mcp_server.prompt()
def listening_recap() -> str:
    """Summarize the user's current Spotify listening: now playing, top
    tracks, and recently played."""
    return (
        "Give me a quick, friendly recap of my Spotify listening right now: what's playing, my top "
        "tracks, and what I've played recently. The spotify://me/dashboard resource has all of this "
        "in a single read. Summarize it conversationally — don't just dump raw data."
    )


@mcp_server.prompt()
def import_youtube_mix(youtube_url: str, playlist_name: str = "") -> str:
    """Import a YouTube mix/compilation video's tracklist into a new Spotify
    playlist."""
    name_clause = f' called "{playlist_name}"' if playlist_name else ""
    return (
        f"Import the tracklist from this YouTube video into a new Spotify playlist{name_clause}: "
        f"{youtube_url}\n\nUse the import_youtube_playlist tool, and tell me which tracks matched "
        "and which didn't."
    )


@mcp_server.prompt()
def start_listening(device_hint: str = "") -> str:
    """Get music playing: check what's already active, or help pick a
    device if nothing is."""
    device_clause = f' (I probably mean a device with "{device_hint}" in its name)' if device_hint else ""
    return (
        "Get some music playing for me. First check now_playing — if something's already playing, "
        "just tell me what it is and leave it alone. If nothing's playing, use list_devices to see "
        f"what's available{device_clause}; if there's an obvious choice, activate it with "
        "activate_device (this also resumes playback there) and tell me what you picked. If there's "
        "more than one reasonable option, ask me which device before activating one. If list_devices "
        "comes back empty, tell me — the MCP server can't launch Spotify itself, I'll need to open it "
        "somewhere first."
    )


@mcp_server.prompt()
def curate_from_liked(criteria: str, num_songs: int = 15, playlist_name: str = "") -> str:
    """Build a new playlist from a subset of the user's Liked Songs that
    fits some criteria (mood, era, genre feel, ...)."""
    name_clause = f' called "{playlist_name}"' if playlist_name else ' with a name that fits the theme'
    return (
        f'Build me a new Spotify playlist{name_clause}, made from songs already in my Liked Songs '
        f'that fit: "{criteria}". Aim for about {num_songs} tracks.\n\n'
        "Use liked_songs to look through my library — I may have hundreds or thousands of saved "
        "tracks, so call it more than once with an increasing offset (50 at a time) to see a good "
        "range before picking. There's no audio analysis available, so judge fit from what you know "
        "about each song/artist/album, not audio features. Once you've picked the tracks, use "
        "create_user_playlist and add_tracks to build the playlist, and tell me which songs you "
        "picked and why they fit."
    )
