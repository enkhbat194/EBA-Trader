from __future__ import annotations

from pathlib import Path

import pytest
from cryptography.fernet import Fernet

from eba_trader import web_server_v2


def _configure_vault(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    key_path = tmp_path / "demo-credential.key"
    key_path.write_bytes(Fernet.generate_key() + b"\n")
    vault_path = tmp_path / "credentials" / "binance-demo.fernet"
    monkeypatch.setenv("EBA_DEMO_CREDENTIAL_KEY_FILE", str(key_path))
    monkeypatch.setenv("EBA_DEMO_CREDENTIAL_VAULT_FILE", str(vault_path))
    monkeypatch.delenv("EBA_BINANCE_DEMO_API_KEY", raising=False)
    monkeypatch.delenv("EBA_BINANCE_DEMO_API_SECRET", raising=False)
    monkeypatch.delenv("BINANCE_DEMO_API_KEY", raising=False)
    monkeypatch.delenv("BINANCE_DEMO_API_SECRET", raising=False)
    return vault_path


def _success_connection_test(payload: dict, session_store=None) -> dict:
    assert payload["provider"] == "binance"
    assert payload["environment"] == "demo"
    return {
        "ok": True,
        "message": "Binance Demo authenticated",
        "latencyMs": 7,
        "balances": {"USDT": "1000"},
        "liveExecutionAllowed": False,
    }


def test_save_tests_then_persists_without_returning_secret(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    vault_path = _configure_vault(monkeypatch, tmp_path)
    monkeypatch.setattr(web_server_v2.base, "run_connection_test", _success_connection_test)

    result = web_server_v2.run_save_demo_credentials(
        {
            "provider": "binance",
            "environment": "demo",
            "credentials": {"apiKey": "demo-key-ABCD", "apiSecret": "super-secret"},
        }
    )

    assert result["ok"] is True
    assert result["saved"] is True
    assert result["configured"] is True
    assert result["credentialMode"] == "encrypted_server_vault"
    assert result["maskedApiKey"] == "••••••••ABCD"
    assert result["sessionToken"]
    assert "super-secret" not in repr(result)
    assert "demo-key-ABCD" not in vault_path.read_text(encoding="utf-8")
    status = web_server_v2._credential_status()
    assert status["configured"] is True
    assert status["maskedApiKey"] == "••••••••ABCD"
    assert "apiSecret" not in status


def test_failed_connection_test_is_never_persisted(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    vault_path = _configure_vault(monkeypatch, tmp_path)

    def failed(payload: dict, session_store=None) -> dict:
        return {"ok": False, "message": "invalid Demo key", "liveExecutionAllowed": False}

    monkeypatch.setattr(web_server_v2.base, "run_connection_test", failed)
    result = web_server_v2.run_save_demo_credentials(
        {
            "provider": "binance",
            "environment": "demo",
            "credentials": {"apiKey": "bad", "apiSecret": "bad-secret"},
        }
    )

    assert result["saved"] is False
    assert not vault_path.exists()


def test_live_or_non_binance_credentials_cannot_be_saved(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _configure_vault(monkeypatch, tmp_path)

    with pytest.raises(ValueError, match="live credentials cannot be saved"):
        web_server_v2.run_save_demo_credentials(
            {
                "provider": "binance",
                "environment": "live",
                "credentials": {"apiKey": "x", "apiSecret": "y"},
            }
        )
    with pytest.raises(ValueError, match="only Binance Demo"):
        web_server_v2.run_save_demo_credentials(
            {
                "provider": "metatrader5",
                "environment": "demo",
                "credentials": {"apiKey": "x", "apiSecret": "y"},
            }
        )


def test_delete_requires_explicit_confirmation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    vault_path = _configure_vault(monkeypatch, tmp_path)
    monkeypatch.setattr(web_server_v2.base, "run_connection_test", _success_connection_test)
    web_server_v2.run_save_demo_credentials(
        {
            "provider": "binance",
            "environment": "demo",
            "credentials": {"apiKey": "demo-key", "apiSecret": "demo-secret"},
        }
    )
    assert vault_path.exists()

    with pytest.raises(ValueError, match="confirm=true"):
        web_server_v2.run_delete_demo_credentials({})

    result = web_server_v2.run_delete_demo_credentials({"confirm": True})
    assert result["deleted"] is True
    assert result["configured"] is False
    assert not vault_path.exists()
