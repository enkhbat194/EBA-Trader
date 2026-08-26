from __future__ import annotations

import stat
from pathlib import Path

import pytest
from cryptography.fernet import Fernet

from eba_trader.credential_vault import CredentialVaultError, DemoCredentialVault
from eba_trader.providers import CredentialEnvelope


def _vault(tmp_path: Path) -> DemoCredentialVault:
    key_path = tmp_path / "etc" / "demo-credential.key"
    key_path.parent.mkdir(parents=True)
    key_path.write_bytes(Fernet.generate_key() + b"\n")
    key_path.chmod(0o600)
    return DemoCredentialVault(
        key_path=key_path,
        vault_path=tmp_path / "state" / "credentials" / "binance-demo.fernet",
    )


def test_vault_encrypts_and_survives_fresh_instance(tmp_path: Path) -> None:
    vault = _vault(tmp_path)
    credentials = CredentialEnvelope(api_key="demo-key-ABC123", api_secret="demo-secret-XYZ789")

    status = vault.save(credentials)

    assert status.configured is True
    assert status.masked_api_key == "••••••••C123"
    ciphertext = vault.vault_path.read_bytes()
    assert b"demo-key-ABC123" not in ciphertext
    assert b"demo-secret-XYZ789" not in ciphertext
    assert stat.S_IMODE(vault.vault_path.stat().st_mode) == 0o600

    restarted = DemoCredentialVault(key_path=vault.key_path, vault_path=vault.vault_path)
    loaded = restarted.load()
    assert loaded is not None
    assert loaded.api_key == credentials.api_key
    assert loaded.api_secret == credentials.api_secret
    assert restarted.status().masked_api_key == "••••••••C123"


def test_vault_wrong_master_key_fails_closed(tmp_path: Path) -> None:
    vault = _vault(tmp_path)
    vault.save(CredentialEnvelope(api_key="demo-key", api_secret="demo-secret"))

    wrong_key = tmp_path / "wrong.key"
    wrong_key.write_bytes(Fernet.generate_key() + b"\n")
    restarted = DemoCredentialVault(key_path=wrong_key, vault_path=vault.vault_path)

    with pytest.raises(CredentialVaultError, match="failed authentication"):
        restarted.load()


def test_vault_missing_master_key_fails_closed(tmp_path: Path) -> None:
    vault = _vault(tmp_path)
    vault.save(CredentialEnvelope(api_key="demo-key", api_secret="demo-secret"))
    vault.key_path.unlink()

    with pytest.raises(CredentialVaultError, match="master key is not installed"):
        vault.load()


def test_vault_replace_and_delete_are_explicit(tmp_path: Path) -> None:
    vault = _vault(tmp_path)
    vault.save(CredentialEnvelope(api_key="old-key", api_secret="old-secret"))
    vault.save(CredentialEnvelope(api_key="new-key-1234", api_secret="new-secret"))

    loaded = vault.load()
    assert loaded is not None
    assert loaded.api_key == "new-key-1234"
    assert loaded.api_secret == "new-secret"
    assert vault.delete() is True
    assert vault.load() is None
    assert vault.delete() is False
