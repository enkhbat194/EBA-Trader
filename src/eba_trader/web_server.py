from __future__ import annotations

import json
import os
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from .demo_sessions import DemoSessionStore
from .m18_demo_snapshot import run_demo_fee_snapshot
from .market_chart import fetch_binance_demo_chart, normalize_mt5_chart
from .mt5_bridge_store import MT5BridgeStore
from .paper_engine import PaperExecutionEngine
from .providers import (
    BinanceProviderAdapter,
    ConnectionManager,
    ConnectionProfile,
    CredentialEnvelope,
    MetaTrader4ProviderAdapter,
    MetaTrader5ProviderAdapter,
    ProviderEnvironment,
    ProviderKind,
)

WEB_ROOT = Path(__file__).resolve().parents[2] / "web"
DEMO_SESSIONS = DemoSessionStore()
MT5_BRIDGES = MT5BridgeStore()
PAPER_ENGINE = PaperExecutionEngine()


def build_default_manager() -> ConnectionManager:
    manager = ConnectionManager()
    manager.register(ProviderKind.BINANCE, BinanceProviderAdapter)
    manager.register(ProviderKind.METATRADER5, MetaTrader5ProviderAdapter)
    manager.register(ProviderKind.METATRADER4, MetaTrader4ProviderAdapter)
    return manager


def _provider_kind(raw: Any) -> ProviderKind:
    try:
        return ProviderKind(str(raw))
    except ValueError as exc:
        raise ValueError("unsupported provider") from exc


def parse_connection_request(
    payload: dict[str, Any],
) -> tuple[ConnectionProfile, CredentialEnvelope]:
    provider = _provider_kind(payload.get("provider"))
    environment_raw = str(payload.get("environment", "demo"))
    try:
        environment = ProviderEnvironment(environment_raw)
    except ValueError as exc:
        raise ValueError("environment must be demo or live") from exc
    if environment is ProviderEnvironment.LIVE:
        raise ValueError("live connections are locked in M18.2")

    credentials_raw = payload.get("credentials")
    if not isinstance(credentials_raw, dict):
        raise ValueError("credentials object is required")

    profile = ConnectionProfile(
        connection_id=f"{provider.value}-{environment.value}",
        provider=provider,
        environment=environment,
        label=f"{provider.value} {environment.value}",
    )
    credentials = CredentialEnvelope(
        api_key=str(credentials_raw.get("apiKey", "")),
        api_secret=str(credentials_raw.get("apiSecret", "")),
        login=str(credentials_raw.get("login", "")),
        password=str(credentials_raw.get("password", "")),
        server=str(credentials_raw.get("server", "")),
    )
    return profile, credentials


def run_connection_test(
    payload: dict[str, Any],
    *,
    session_store: DemoSessionStore | None = None,
) -> dict[str, Any]:
    profile, credentials = parse_connection_request(payload)
    manager = build_default_manager()
    manager.upsert_profile(profile)
    result = manager.test_connection(profile.connection_id, credentials)
    response = {
        "ok": result.ok,
        "state": result.state.value,
        "message": result.message,
        "latencyMs": result.latency_ms,
        "accountLabel": result.account_label,
        "balances": result.balances,
        "capabilities": [capability.value for capability in result.capabilities],
        "environment": profile.environment.value,
        "provider": profile.provider.value,
        "liveExecutionAllowed": False,
    }
    if (
        result.ok
        and profile.provider is ProviderKind.BINANCE
        and profile.environment is ProviderEnvironment.DEMO
        and session_store is not None
    ):
        response["sessionToken"] = session_store.create(credentials)
    return response


def _session_credentials(payload: dict[str, Any], session_store: DemoSessionStore) -> tuple[str, CredentialEnvelope]:
    token = str(payload.get("sessionToken", ""))
    credentials = session_store.get(token)
    if credentials is None:
        raise PermissionError("Demo session is missing or expired")
    return token, credentials


def run_demo_snapshot_request(
    payload: dict[str, Any],
    *,
    session_store: DemoSessionStore,
) -> dict[str, Any]:
    _, credentials = _session_credentials(payload, session_store)
    return run_demo_fee_snapshot(credentials)


def run_demo_disconnect_request(
    payload: dict[str, Any],
    *,
    session_store: DemoSessionStore,
    paper_engine: PaperExecutionEngine | None = None,
) -> dict[str, Any]:
    token = str(payload.get("sessionToken", ""))
    if not token:
        raise ValueError("sessionToken is required")
    if paper_engine is not None:
        paper_engine.clear(token)
    session_store.revoke(token)
    return {"ok": True, "state": "disconnected", "liveExecutionAllowed": False}


def run_paper_step_request(
    payload: dict[str, Any],
    *,
    session_store: DemoSessionStore,
    paper_engine: PaperExecutionEngine,
) -> dict[str, Any]:
    token, credentials = _session_credentials(payload, session_store)
    snapshot = run_demo_fee_snapshot(credentials)
    paper = paper_engine.step(token, snapshot)
    return {
        "ok": True,
        "snapshot": snapshot,
        "paper": paper,
        "liveExecutionAllowed": False,
    }


def run_paper_state_request(
    payload: dict[str, Any],
    *,
    session_store: DemoSessionStore,
    paper_engine: PaperExecutionEngine,
) -> dict[str, Any]:
    token, _ = _session_credentials(payload, session_store)
    return paper_engine.state(token)


def run_paper_close_request(
    payload: dict[str, Any],
    *,
    session_store: DemoSessionStore,
    paper_engine: PaperExecutionEngine,
) -> dict[str, Any]:
    token, credentials = _session_credentials(payload, session_store)
    snapshot = run_demo_fee_snapshot(credentials)
    paper = paper_engine.close(token, snapshot)
    return {
        "ok": True,
        "snapshot": snapshot,
        "paper": paper,
        "liveExecutionAllowed": False,
    }


def run_mt5_pair_request(*, bridge_store: MT5BridgeStore) -> dict[str, Any]:
    result = bridge_store.create_pair()
    result.update(
        {
            "ok": True,
            "provider": "metatrader5",
            "environment": "demo",
            "liveExecutionAllowed": False,
        }
    )
    return result


def run_mt5_ingest_request(
    payload: dict[str, Any],
    *,
    bridge_store: MT5BridgeStore,
) -> dict[str, Any]:
    token = str(payload.get("pairToken", ""))
    snapshot = payload.get("snapshot")
    if not token:
        raise ValueError("pairToken is required")
    if not isinstance(snapshot, dict):
        raise ValueError("snapshot object is required")
    if snapshot.get("readOnly") is not True:
        raise ValueError("MT5 bridge must declare readOnly=true")
    if not isinstance(snapshot.get("account"), dict):
        raise ValueError("MT5 account snapshot is required")
    if not isinstance(snapshot.get("charts"), dict):
        raise ValueError("MT5 chart snapshot is required")
    result = bridge_store.ingest(token, snapshot)
    result["liveExecutionAllowed"] = False
    return result


def run_mt5_state_request(
    payload: dict[str, Any],
    *,
    bridge_store: MT5BridgeStore,
) -> dict[str, Any]:
    token = str(payload.get("pairToken", ""))
    if not token:
        raise ValueError("pairToken is required")
    return bridge_store.state(token)


def run_mt5_disconnect_request(
    payload: dict[str, Any],
    *,
    bridge_store: MT5BridgeStore,
) -> dict[str, Any]:
    token = str(payload.get("pairToken", ""))
    if not token:
        raise ValueError("pairToken is required")
    bridge_store.revoke(token)
    return {"ok": True, "state": "disconnected", "liveExecutionAllowed": False}


def run_chart_request(
    payload: dict[str, Any],
    *,
    bridge_store: MT5BridgeStore,
    session_store: DemoSessionStore | None = None,
    paper_engine: PaperExecutionEngine | None = None,
) -> dict[str, Any]:
    provider = str(payload.get("provider", "")).lower()
    symbol = str(payload.get("symbol", "")).upper().strip()
    timeframe = str(payload.get("timeframe", "15m"))
    limit = int(payload.get("limit", 120))
    if provider == "binance":
        result = fetch_binance_demo_chart(symbol, timeframe, limit)
        token = str(payload.get("sessionToken", ""))
        if token and session_store is not None and session_store.get(token) is not None:
            if paper_engine is not None:
                result["markers"] = paper_engine.markers(token)
                result["paper"] = paper_engine.state(token)
        return result
    if provider == "metatrader5":
        token = str(payload.get("pairToken", ""))
        state = bridge_store.state(token)
        if not state.get("connected"):
            raise PermissionError("MT5 Demo bridge is not connected")
        snapshot = state.get("snapshot")
        if not isinstance(snapshot, dict):
            raise PermissionError("MT5 Demo bridge has no snapshot")
        result = normalize_mt5_chart(snapshot, symbol, timeframe)
        result["bridgeHeartbeatAgeSeconds"] = state.get("heartbeatAgeSeconds")
        return result
    raise ValueError("unsupported chart provider")


class EBARequestHandler(SimpleHTTPRequestHandler):
    """Static PWA + Demo-only Binance/MT5/paper APIs. Live execution is absent."""

    server_version = "EBA-UI/0.6"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, directory=str(WEB_ROOT), **kwargs)

    def end_headers(self) -> None:
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        self.send_header("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
            "connect-src 'self'; manifest-src 'self'; worker-src 'self'; object-src 'none'; "
            "base-uri 'self'; frame-ancestors 'none'; form-action 'self'",
        )
        super().end_headers()

    def log_message(self, format: str, *args: Any) -> None:
        super().log_message(format, *args)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/api/health":
            self._json_response(
                HTTPStatus.OK,
                {
                    "ok": True,
                    "mode": "demo-first",
                    "providers": ["binance", "metatrader5"],
                    "paperExecution": True,
                    "liveExecutionAllowed": False,
                },
            )
            return
        if self.path == "/api/providers":
            self._json_response(
                HTTPStatus.OK,
                {
                    "providers": [
                        {"id": "binance", "name": "Binance", "status": "ready"},
                        {"id": "metatrader5", "name": "MetaTrader 5", "status": "bridge-ready"},
                    ],
                    "environment": "demo",
                    "liveExecutionAllowed": False,
                },
            )
            return
        super().do_GET()

    def do_POST(self) -> None:  # noqa: N802
        allowed_paths = {
            "/api/connections/test",
            "/api/demo/snapshot",
            "/api/demo/disconnect",
            "/api/paper/step",
            "/api/paper/state",
            "/api/paper/close",
            "/api/mt5/pair",
            "/api/mt5/ingest",
            "/api/mt5/state",
            "/api/mt5/disconnect",
            "/api/chart",
        }
        if self.path not in allowed_paths:
            self._json_response(HTTPStatus.NOT_FOUND, {"ok": False, "message": "not found"})
            return

        content_length = int(self.headers.get("Content-Length", "0") or "0")
        max_size = 524_288 if self.path == "/api/mt5/ingest" else 32_768
        if content_length <= 0 or content_length > max_size:
            self._json_response(
                HTTPStatus.BAD_REQUEST,
                {"ok": False, "message": "invalid request size"},
            )
            return

        try:
            payload = json.loads(self.rfile.read(content_length).decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("JSON object required")
            if self.path == "/api/connections/test":
                result = run_connection_test(payload, session_store=DEMO_SESSIONS)
            elif self.path == "/api/demo/snapshot":
                result = run_demo_snapshot_request(payload, session_store=DEMO_SESSIONS)
            elif self.path == "/api/demo/disconnect":
                result = run_demo_disconnect_request(
                    payload,
                    session_store=DEMO_SESSIONS,
                    paper_engine=PAPER_ENGINE,
                )
            elif self.path == "/api/paper/step":
                result = run_paper_step_request(
                    payload,
                    session_store=DEMO_SESSIONS,
                    paper_engine=PAPER_ENGINE,
                )
            elif self.path == "/api/paper/state":
                result = run_paper_state_request(
                    payload,
                    session_store=DEMO_SESSIONS,
                    paper_engine=PAPER_ENGINE,
                )
            elif self.path == "/api/paper/close":
                result = run_paper_close_request(
                    payload,
                    session_store=DEMO_SESSIONS,
                    paper_engine=PAPER_ENGINE,
                )
            elif self.path == "/api/mt5/pair":
                result = run_mt5_pair_request(bridge_store=MT5_BRIDGES)
            elif self.path == "/api/mt5/ingest":
                result = run_mt5_ingest_request(payload, bridge_store=MT5_BRIDGES)
            elif self.path == "/api/mt5/state":
                result = run_mt5_state_request(payload, bridge_store=MT5_BRIDGES)
            elif self.path == "/api/mt5/disconnect":
                result = run_mt5_disconnect_request(payload, bridge_store=MT5_BRIDGES)
            else:
                result = run_chart_request(
                    payload,
                    bridge_store=MT5_BRIDGES,
                    session_store=DEMO_SESSIONS,
                    paper_engine=PAPER_ENGINE,
                )
        except PermissionError as exc:
            self._json_response(
                HTTPStatus.UNAUTHORIZED,
                {"ok": False, "message": str(exc), "liveExecutionAllowed": False},
            )
            return
        except (json.JSONDecodeError, ValueError) as exc:
            self._json_response(
                HTTPStatus.BAD_REQUEST,
                {"ok": False, "message": str(exc), "liveExecutionAllowed": False},
            )
            return
        except Exception as exc:
            self._json_response(
                HTTPStatus.BAD_GATEWAY,
                {
                    "ok": False,
                    "message": f"Demo read-only/paper request failed: {exc}",
                    "liveExecutionAllowed": False,
                },
            )
            return

        self._json_response(HTTPStatus.OK, result)

    def _json_response(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    host = os.getenv("EBA_WEB_HOST", "0.0.0.0")
    port = int(os.getenv("PORT", os.getenv("EBA_WEB_PORT", "8000")))
    if not WEB_ROOT.exists():
        raise RuntimeError(f"web root missing: {WEB_ROOT}")
    server = ThreadingHTTPServer((host, port), EBARequestHandler)
    print(f"EBA Trader UI serving on http://{host}:{port} (demo/paper only, live locked)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
