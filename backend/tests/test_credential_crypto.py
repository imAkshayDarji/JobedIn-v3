import pytest
from cryptography.fernet import Fernet

from app.config import settings
from app.services.credential_crypto import decrypt_value, encrypt_value, generate_key


class TestGenerateKey:
    def test_returns_valid_fernet_key(self) -> None:
        key = generate_key()
        assert isinstance(key, str)
        assert len(key) > 0

    def test_generated_key_is_usable(self, monkeypatch: pytest.MonkeyPatch) -> None:
        key = generate_key()
        monkeypatch.setattr(settings, "ENCRYPTION_KEY", key)
        plaintext = "test-password-123"
        ciphertext = encrypt_value(plaintext)
        assert decrypt_value(ciphertext) == plaintext


class TestEncryptDecrypt:
    def test_roundtrip(self, monkeypatch: pytest.MonkeyPatch) -> None:
        key = Fernet.generate_key().decode()
        monkeypatch.setattr(settings, "ENCRYPTION_KEY", key)

        plaintext = "my-secret-password"
        ciphertext = encrypt_value(plaintext)
        assert ciphertext != plaintext
        assert decrypt_value(ciphertext) == plaintext

    def test_different_encryptions_produce_different_ciphertext(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        key = Fernet.generate_key().decode()
        monkeypatch.setattr(settings, "ENCRYPTION_KEY", key)

        plaintext = "same-password"
        ct1 = encrypt_value(plaintext)
        ct2 = encrypt_value(plaintext)
        assert ct1 != ct2

    def test_missing_key_raises_value_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(settings, "ENCRYPTION_KEY", "")
        with pytest.raises(ValueError, match="ENCRYPTION_KEY is not configured"):
            encrypt_value("test")

    def test_invalid_key_raises_value_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(settings, "ENCRYPTION_KEY", "not-a-valid-key")
        with pytest.raises(ValueError, match="Invalid ENCRYPTION_KEY"):
            encrypt_value("test")

    def test_tampered_ciphertext_returns_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        key = Fernet.generate_key().decode()
        monkeypatch.setattr(settings, "ENCRYPTION_KEY", key)

        ciphertext = encrypt_value("secret")
        tampered = ciphertext[:-5] + "XXXXX"
        assert decrypt_value(tampered) is None

    def test_decrypt_invalid_base64_returns_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        key = Fernet.generate_key().decode()
        monkeypatch.setattr(settings, "ENCRYPTION_KEY", key)

        assert decrypt_value("not-valid-ciphertext!!!") is None

    def test_decrypt_with_wrong_key_returns_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        key1 = Fernet.generate_key().decode()
        key2 = Fernet.generate_key().decode()

        monkeypatch.setattr(settings, "ENCRYPTION_KEY", key1)
        ciphertext = encrypt_value("secret")

        monkeypatch.setattr(settings, "ENCRYPTION_KEY", key2)
        assert decrypt_value(ciphertext) is None
