import base64
import hashlib

from spotify_mcp.spotify.auth import _generate_code_challenge, _generate_code_verifier


def test_code_verifier_is_url_safe_and_long_enough() -> None:
    # PKCE requires 43-128 chars from [A-Za-z0-9-._~].
    verifier = _generate_code_verifier()
    assert 43 <= len(verifier) <= 128
    assert all(c.isalnum() or c in "-._~" for c in verifier)


def test_code_verifier_is_random() -> None:
    assert _generate_code_verifier() != _generate_code_verifier()


def test_code_challenge_matches_spec_derivation() -> None:
    # code_challenge = base64url(sha256(code_verifier)), no padding — verify
    # our helper matches that exact derivation, not just "some hash".
    verifier = "test-verifier-value"
    expected = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest())
    expected = expected.decode("ascii").rstrip("=")

    assert _generate_code_challenge(verifier) == expected
