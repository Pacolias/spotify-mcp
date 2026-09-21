from spotify_mcp.mcp.prompts import (
    build_playlist,
    curate_from_liked,
    import_youtube_mix,
    listening_recap,
    start_listening,
)


def test_build_playlist_includes_theme_and_song_count() -> None:
    result = build_playlist("rainy day coding", num_songs=8, genre="ambient")

    assert '"rainy day coding"' in result
    assert "leaning ambient" in result
    assert "8 songs" in result
    assert "search_track" in result
    assert "create_user_playlist" in result
    assert "add_tracks" in result


def test_build_playlist_omits_genre_clause_when_not_given() -> None:
    result = build_playlist("focus", num_songs=5)

    assert "leaning" not in result


def test_listening_recap_mentions_dashboard_resource() -> None:
    result = listening_recap()

    assert "spotify://me/dashboard" in result


def test_import_youtube_mix_includes_url_and_playlist_name() -> None:
    result = import_youtube_mix("https://youtube.com/watch?v=abc", playlist_name="My Mix")

    assert "https://youtube.com/watch?v=abc" in result
    assert '"My Mix"' in result
    assert "import_youtube_playlist" in result


def test_import_youtube_mix_omits_name_clause_when_not_given() -> None:
    result = import_youtube_mix("https://youtube.com/watch?v=abc")

    assert "called" not in result


def test_start_listening_mentions_key_tools() -> None:
    result = start_listening()

    assert "now_playing" in result
    assert "list_devices" in result
    assert "activate_device" in result


def test_start_listening_includes_device_hint_when_given() -> None:
    result = start_listening(device_hint="fedora")

    assert '"fedora"' in result


def test_start_listening_omits_device_hint_when_not_given() -> None:
    result = start_listening()

    assert "probably mean" not in result


def test_curate_from_liked_includes_criteria_and_song_count() -> None:
    result = curate_from_liked("high energy workout songs", num_songs=12)

    assert '"high energy workout songs"' in result
    assert "12 tracks" in result
    assert "liked_songs" in result
    assert "create_user_playlist" in result


def test_curate_from_liked_uses_given_playlist_name() -> None:
    result = curate_from_liked("chill", playlist_name="Chill Vibes")

    assert '"Chill Vibes"' in result
