import os
import stat
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from backend.app.core.config import settings


class CredentialVault:
    """
    Encrypts and decrypts API credentials at rest using Fernet (AES-128-CBC + HMAC-SHA256).
    Never logs or exposes raw secrets.
    """

    def __init__(self, key_override: str | None = None) -> None:
        self._fernet = Fernet(self._resolve_key(key_override))

    def _resolve_key(self, key_override: str | None = None) -> bytes:
        raw_key = key_override or settings.secret_key
        if raw_key:
            return raw_key.encode("utf-8")

        key_file: Path = settings.data_dir / ".secret.key"
        if key_file.exists():
            return key_file.read_bytes().strip()

        generated_key = Fernet.generate_key()
        key_file.write_bytes(generated_key)
        try:
            os.chmod(key_file, stat.S_IRUSR | stat.S_IWUSR)
        except OSError:
            pass
        return generated_key

    def encrypt(self, plaintext: str) -> str:
        if not plaintext:
            raise ValueError("Cannot encrypt empty credential")
        token = self._fernet.encrypt(plaintext.encode("utf-8"))
        return token.decode("utf-8")

    def decrypt(self, ciphertext: str) -> str:
        if not ciphertext:
            raise ValueError("Cannot decrypt empty ciphertext")
        try:
            plaintext = self._fernet.decrypt(ciphertext.encode("utf-8"))
            return plaintext.decode("utf-8")
        except InvalidToken as exc:
            raise ValueError("Failed to decrypt credential: invalid encryption key or corrupted data") from exc

    @staticmethod
    def mask_key(api_key: str) -> str:
        """Returns a safe masked hint such as 'sk-proj...9a2f'."""
        cleaned = api_key.strip()
        if len(cleaned) <= 8:
            return "****"
        return f"{cleaned[:6]}...{cleaned[-4:]}"


vault = CredentialVault()
