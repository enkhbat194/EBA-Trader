from __future__ import annotations

import json
import os
import tempfile
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from .providers import CredentialEnvelope

VAULT_SCHEMA = "eba_binance_demo_credentials_v1"
DEFAULT_KEY_PATH = Path("/etc/eba-trader/demo-credential.key")
DEFAULT_VAULT_PATH = Path("/var/lib/eba-trader/credentials/binance-demo.fernet")


class CredentialVaultError(RuntimeError):
    """Raised when encrypted credential state cannot be trusted or decrypted."""


@dataclass(frozen=True, slots=True)
class CredentialVaultStatus:
    configured: bool
    masked_api_key: str | None = None


class DemoCredentialVault:
    """Encrypted-at-rest store for one Binance Demo API credential pair.

    The encryption key is intentionally stored separately from the ciphertext. The
    browser never reads this file or the decrypted secret; only the Linode backend does.
    """

    def __init__(
        self,
        *,
        key_path: str | Path = DEFAULT_KEY_PATH,
        vault_path: str | Path = DEFAULT_VAULT_PATH,
    ) -> None:
        self.key_path = Path(key_path)
        self.vault_path = Path(vault_path)

    def exists(self) -> bool:
        return self.vault_path.is_file()

    def status(self) -> CredentialVaultStatus:
        if not self.exists():
            return CredentialVaultStatus(configured=False)
        credentials = self.load()
        return CredentialVaultStatus(
            configured=True,
            masked_api_key=_mask_api_key(credentials.api_key),
        )

    def load(self) -> CredentialEnvelope | None:
        if not self.exists():
            return None
        fernet = self._fernet()
        try:
            token = self.vault_path.read_bytes().strip()
        except OSError as exc:
            raise CredentialVaultError("could not read encrypted Demo credential vault") from exc
        if not token:
            raise CredentialVaultError("encrypted Demo credential vault is empty")
        try:
            plaintext = fernet.decrypt(token)
        except InvalidToken as exc:
            raise CredentialVaultError(
                "encrypted Demo credential vault failed authentication"
            ) from exc
        try:
            payload = json.loads(plaintext.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise CredentialVaultError("encrypted Demo credential payload is invalid") from exc
        if not isinstance(payload, dict):
            raise CredentialVaultError("encrypted Demo credential payload must be an object")
        required = {"schema", "provider", "environment", "apiKey", "apiSecret"}
        if set(payload) != required:
            raise CredentialVaultError("encrypted Demo credential payload fields are invalid")
        if payload["schema"] != VAULT_SCHEMA:
            raise CredentialVaultError("unsupported Demo credential vault schema")
        if payload["provider"] != "binance" or payload["environment"] != "demo":
            raise CredentialVaultError("credential vault is not Binance Demo")
        api_key = str(payload["apiKey"]).strip()
        api_secret = str(payload["apiSecret"]).strip()
        if not api_key or not api_secret:
            raise CredentialVaultError("stored Binance Demo credential is incomplete")
        return CredentialEnvelope(api_key=api_key, api_secret=api_secret)

    def save(self, credentials: CredentialEnvelope) -> CredentialVaultStatus:
        api_key = credentials.api_key.strip()
        api_secret = credentials.api_secret.strip()
        if not api_key or not api_secret:
            raise ValueError("Binance Demo API key and secret are required")
        payload = {
            "schema": VAULT_SCHEMA,
            "provider": "binance",
            "environment": "demo",
            "apiKey": api_key,
            "apiSecret": api_secret,
        }
        plaintext = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        encrypted = self._fernet().encrypt(plaintext)
        self.vault_path.parent.mkdir(parents=True, exist_ok=True)
        _atomic_private_write(self.vault_path, encrypted + b"\n")
        return CredentialVaultStatus(configured=True, masked_api_key=_mask_api_key(api_key))

    def delete(self) -> bool:
        try:
            self.vault_path.unlink()
        except FileNotFoundError:
            return False
        except OSError as exc:
            raise CredentialVaultError("could not delete encrypted Demo credential vault") from exc
        return True

    def _fernet(self) -> Fernet:
        try:
            key = self.key_path.read_bytes().strip()
        except FileNotFoundError as exc:
            raise CredentialVaultError("Demo credential master key is not installed") from exc
        except OSError as exc:
            raise CredentialVaultError("could not read Demo credential master key") from exc
        try:
            return Fernet(key)
        except (TypeError, ValueError) as exc:
            raise CredentialVaultError("Demo credential master key is invalid") from exc


def _mask_api_key(api_key: str) -> str:
    text = api_key.strip()
    if not text:
        return ""
    suffix = text[-4:] if len(text) >= 4 else text
    return f"••••••••{suffix}"


def _atomic_private_write(path: Path, content: bytes) -> None:
    fd: int | None = None
    temp_name: str | None = None
    try:
        fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb") as handle:
            fd = None
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
        temp_name = None
        os.chmod(path, 0o600)
    finally:
        if fd is not None:
            os.close(fd)
        if temp_name is not None:
            with suppress(FileNotFoundError):
                os.unlink(temp_name)
