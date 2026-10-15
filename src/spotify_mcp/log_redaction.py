"""Keep OAuth secrets out of the HTTP access log.

uvicorn logs each request's full URL. Several of ours carry secrets in the
query string: Spotify's authorization code on /auth/callback, and PKCE and
state values on /authorize. Logging the path alone keeps the log useful
without writing credentials to disk.
"""

import logging


class StripQueryString(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        # uvicorn.access records: (client, method, path, http_version, status).
        if isinstance(record.args, tuple) and len(record.args) == 5:
            client, method, path, http_version, status = record.args
            if isinstance(path, str):
                record.args = (client, method, path.split("?", 1)[0], http_version, status)
        return True


def install() -> None:
    """Call after uvicorn has configured logging (i.e. at app startup)."""
    logging.getLogger("uvicorn.access").addFilter(StripQueryString())
