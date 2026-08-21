from eba_trader.demo_sessions import DemoSessionStore
from eba_trader.providers import CredentialEnvelope


def test_demo_session_round_trip_is_memory_only_token_lookup() -> None:
    store = DemoSessionStore(ttl_seconds=60)
    credentials = CredentialEnvelope(
        api_key="spot-key",
        api_secret="spot-secret",
        futures_api_key="futures-key",
        futures_api_secret="futures-secret",
    )
    token = store.create(credentials)
    assert token
    assert "spot-key" not in token
    assert "futures-key" not in token
    assert store.get(token) == credentials


def test_demo_session_revoke_fails_closed() -> None:
    store = DemoSessionStore(ttl_seconds=60)
    token = store.create(CredentialEnvelope(api_key="x"))
    store.revoke(token)
    assert store.get(token) is None


def test_demo_session_expiry_fails_closed(monkeypatch) -> None:
    clock = {"value": 100.0}
    monkeypatch.setattr("eba_trader.demo_sessions.time.monotonic", lambda: clock["value"])
    store = DemoSessionStore(ttl_seconds=10)
    token = store.create(CredentialEnvelope(api_key="x"))
    assert store.get(token) is not None
    clock["value"] = 111.0
    assert store.get(token) is None
