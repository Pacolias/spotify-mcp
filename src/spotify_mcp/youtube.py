import re

import yt_dlp

_TIMESTAMP = r"\d{1,2}:\d{2}(?::\d{2})?"

# Two shapes cover most community-written tracklists:
#   "0:00 Artist - Title"        (timestamp first — same shape as YouTube's
#                                  own auto-detected chapters)
#   "Artist - Title (0:00)"      (timestamp last)
_LEADING_TIMESTAMP_RE = re.compile(
    rf"^\s*(?:\d+[.)]\s*)?\[?({_TIMESTAMP})\]?\s*[-–—:]?\s*(.+?)\s*$"
)
_TRAILING_TIMESTAMP_RE = re.compile(
    rf"^\s*(?:\d+[.)]\s*)?(.+?)\s*[-–—(\[]\s*{_TIMESTAMP}\)?\]?\s*$"
)


def _parse_description_tracklist(description: str) -> list[str]:
    leading_matches = []
    trailing_matches = []

    for raw_line in description.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        match = _LEADING_TIMESTAMP_RE.match(line)
        if match:
            leading_matches.append(match.group(2).strip())
            continue

        match = _TRAILING_TIMESTAMP_RE.match(line)
        if match:
            trailing_matches.append(match.group(1).strip())

    # A real tracklist has many consecutive matching lines; a promo link
    # with a stray time-like substring is a one-off. Prefer whichever
    # pattern actually matched more of the description.
    return leading_matches if len(leading_matches) >= len(trailing_matches) else trailing_matches


def _artist_tokens(entry: str) -> list[str]:
    if " - " not in entry:
        return []
    artist_part = entry.split(" - ", 1)[0]
    return [a.strip().lower() for a in re.split(r"[,&]", artist_part) if a.strip()]


def artist_plausibly_matches(entry: str, result_artists: list[str]) -> bool:
    """Sanity check that a Spotify search result is actually by the artist
    the tracklist entry names, not just a text-similarity fluke. Tracklists
    often name unreleased/"coming soon" tracks that aren't on Spotify at
    all — search still returns *a* result for those, just the wrong song by
    an unrelated artist, unless this is checked. Found by testing against a
    real video with several unreleased tracks listed (see journal)."""
    entry_artists = _artist_tokens(entry)
    if not entry_artists:
        # No artist parsed (bare title, or a non-track chapter marker like
        # "LOOP") — nothing to check against, so don't claim a match.
        return False

    result_lower = [a.lower() for a in result_artists]
    return any(
        entry_artist in r or r in entry_artist
        for entry_artist in entry_artists
        for r in result_lower
    )


def extract_tracklist(url: str) -> list[str]:
    """Best-effort: returns song titles from a YouTube video's chapters (if
    the uploader added any) or, failing that, parsed out of the video
    description. Only works for videos that actually list their tracks —
    there's no audio recognition here."""
    ydl_opts = {"quiet": True, "no_warnings": True, "skip_download": True, "noplaylist": True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    chapters = info.get("chapters") or []
    if chapters:
        return [c["title"].strip() for c in chapters if c.get("title")]

    return _parse_description_tracklist(info.get("description") or "")
