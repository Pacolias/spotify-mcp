import pytest
from cryptography.fernet import Fernet, InvalidToken

from spotify_mcp.db.encryption import decrypt, encrypt


def test_round_trip() -> None:
    assert decrypt(encrypt("spotify-refresh-token")) == "spotify-refresh-token"


def test_ciphertext_does_not_contain_the_plaintext() -> None:
    assert "spotify-refresh-token" not in encrypt("spotify-refresh-token")


def test_same_plaintext_encrypts_differently_each_time() -> None:
    # Fernet uses a random IV, so equal tokens don't produce equal ciphertexts.
    assert encrypt("x") != encrypt("x")


def test_ciphertext_from_another_key_is_rejected() -> None:
    foreign = Fernet(Fernet.generate_key()).encrypt(b"secret").decode()

    with pytest.raises(InvalidToken):
        decrypt(foreign)


def test_tampered_ciphertext_is_rejected() -> None:
    ciphertext = encrypt("secret")
    tampered = ciphertext[:-5] + ("A" if ciphertext[-5] != "A" else "B") + ciphertext[-4:]

    with pytest.raises(InvalidToken):
        decrypt(tampered)
