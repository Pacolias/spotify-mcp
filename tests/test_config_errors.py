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
