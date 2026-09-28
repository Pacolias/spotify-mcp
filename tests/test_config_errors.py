import os
import subprocess
import sys


def test_missing_client_id_prints_friendly_error_and_exits_1(tmp_path) -> None:
    # sys.exit() happens at import time in config.py, so this has to run in a
    # subprocess — importing it in-process would kill the test runner.
    clean_env = {k: v for k, v in os.environ.items() if not k.startswith("SPOTIFY_")}

    result = subprocess.run(
        [sys.executable, "-c", "import spotify_mcp.config"],
        cwd=tmp_path,  # no .env file here, so nothing to pick up spotify_client_id from
        env=clean_env,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Missing required configuration: spotify_client_id" in result.stderr
    assert "cp .env.example .env" in result.stderr


def _import_config(tmp_path, **env: str) -> subprocess.CompletedProcess[str]:
    base = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith("SPOTIFY_") and k != "JWT_SIGNING_KEY"
    }
    return subprocess.run(
        [sys.executable, "-c", "import spotify_mcp.config"],
        cwd=tmp_path,
        env={**base, **env},
        capture_output=True,
        text=True,
    )


def test_missing_jwt_signing_key_is_reported(tmp_path) -> None:
    result = _import_config(tmp_path, SPOTIFY_CLIENT_ID="x")

    assert result.returncode == 1
    assert "Missing required configuration: jwt_signing_key" in result.stderr


def test_short_jwt_signing_key_is_rejected(tmp_path) -> None:
    result = _import_config(tmp_path, SPOTIFY_CLIENT_ID="x", JWT_SIGNING_KEY="too-short")

    assert result.returncode == 1
    assert "at least 32 bytes" in result.stderr


def test_32_byte_jwt_signing_key_is_accepted(tmp_path) -> None:
    result = _import_config(tmp_path, SPOTIFY_CLIENT_ID="x", JWT_SIGNING_KEY="k" * 32)

    assert result.returncode == 0, result.stderr
