from spotify_mcp.youtube import _parse_description_tracklist, artist_plausibly_matches


def test_parses_leading_timestamp_tracklist() -> None:
    description = (
        "Tracklist:\n"
        "0:00 Nujabes - Aruarian Dance\n"
        "3:45 Emancipator - Soon It Will Be Cold Enough\n"
        "7:20 WYS - Snowman\n"
        "\n"
        "Follow us on Instagram!"
    )

    assert _parse_description_tracklist(description) == [
        "Nujabes - Aruarian Dance",
        "Emancipator - Soon It Will Be Cold Enough",
        "WYS - Snowman",
    ]


def test_parses_trailing_timestamp_tracklist() -> None:
    description = (
        "1. Aruarian Dance - Nujabes (0:00)\n"
        "2. Soon It Will Be Cold Enough - Emancipator (3:45)\n"
        "3. Snowman - WYS (7:20)\n"
        "\n"
        "Thanks for watching"
    )

    assert _parse_description_tracklist(description) == [
        "Aruarian Dance - Nujabes",
        "Soon It Will Be Cold Enough - Emancipator",
        "Snowman - WYS",
    ]


def test_no_false_positives_on_plain_description() -> None:
    description = "Just a normal video, check out my socials at 10:00am tomorrow"

    assert _parse_description_tracklist(description) == []


def test_artist_plausibly_matches_accepts_matching_artist() -> None:
    # Real case: "1aevne, baby.m - Crystals (slowed)" matching a Spotify
    # result credited to "1aevne, baby.murcielaga" (see journal).
    assert artist_plausibly_matches(
        "1aevne, baby.m - Crystals (slowed)", ["1aevne", "baby.murcielaga"]
    )


def test_artist_plausibly_matches_rejects_wrong_artist() -> None:
    # Real case: "1aevne - unreleased track" (not on Spotify at all) matched
    # a Spotify search result by a completely unrelated artist.
    assert not artist_plausibly_matches("1aevne - unreleased track", ["JøhnnyStørm"])


def test_artist_plausibly_matches_rejects_entry_with_no_artist() -> None:
    # A bare chapter marker like "LOOP" has no " - " separator, so there's
    # no artist to check against — must not be treated as a match.
    assert not artist_plausibly_matches("LOOP", ["Jerri"])
