from __future__ import annotations

import json
import os
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from .demo_sessions import DemoSessionStore
from .m18_demo_snapshot import run_demo_fee_snapshot
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
        raise ValueError("live connections are locked in M18.1")

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


def run_demo_snapshot_request(
    payload: dict[str, Any],
    *,
    session_store: DemoSessionStore,
) -> dict[str, Any]:
    token = str(payload.get("sessionToken", ""))
    credentials = session_store.get(token)
    if credentials is None:
        raise PermissionError("Demo session is missing or expired")
    return run_demo_fee_snapshot(credentials)


class EBARequestHandler(SimpleHTTPRequestHandler):
    """Static PWA + Demo-only read API.

    Connection credentials are accepted only during the connection-test request.
    On successful Binance Demo validation they move into a short-lived process-memory
    session. Secrets are never written to disk, logs, browser storage, or API replies.
    """

    server_version = "EBA-UI/0.3"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, directory=str(WEB_ROOT), **kwargs)

    def log_message(self, format: str, *args: Any) -> None:
        # SimpleHTTPRequestHandler logs request metadata only; request bodies are never logged.
        super().log_message(format, *args)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/api/health":
            self._json_response(
                HTTPStatus.OK,
                {
                    "ok": True,
                    "mode": "demo-first",
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
                        {"id": "metatrader5", "name": "MetaTrader 5", "status": "scaffolded"},
                        {"id": "metatrader4", "name": "MetaTrader 4", "status": "scaffolded"},
                    ],
                    "environment": "demo",
                    "liveExecutionAllowed": False,
                },
            )
            return
        super().do_GET()

    def do_POST(self) -> None:  # noqa: N802
        if self.path not in {"/api/connections/test", "/api/demo/snapshot"}:
            self._json_response(HTTPStatus.NOT_FOUND, {"ok": False, "message": "not found"})
            return

        content_length = int(self.headers.get("Content-Length", "0") or "0")
        if content_length <= 0 or content_length > 32_768:
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
            else:
                result = run_demo_snapshot_request(payload, session_store=DEMO_SESSIONS)
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
                    "message": f"Demo read-only request failed: {exc}",
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
    print(f"EBA Trader UI serving on http://{host}:{port} (demo-first, live locked)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
