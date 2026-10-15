import logging

from spotify_mcp.log_redaction import StripQueryString


def _access_record(path: str) -> logging.LogRecord:
    return logging.LogRecord(
        "uvicorn.access",
        logging.INFO,
        __file__,
        1,
        '%s - "%s %s HTTP/%s" %d',
        ("127.0.0.1:1234", "GET", path, "1.1", 302),
        None,
    )


def test_query_string_is_dropped_from_access_log_lines() -> None:
    record = _access_record("/auth/callback?code=secret-code&state=secret-state")

    StripQueryString().filter(record)

    message = record.getMessage()
    assert "/auth/callback" in message
    assert "secret" not in message


def test_paths_without_a_query_are_untouched() -> None:
    record = _access_record("/health")

    StripQueryString().filter(record)

    assert record.getMessage() == '127.0.0.1:1234 - "GET /health HTTP/1.1" 302'
