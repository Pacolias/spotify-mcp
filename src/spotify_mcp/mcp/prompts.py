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
