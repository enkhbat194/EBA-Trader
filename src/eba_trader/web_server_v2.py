from __future__ import annotations

import json
import os
from http import HTTPStatus
from http.server import ThreadingHTTPServer
from typing import Any

from . import web_server as base
from .momentum_engine import MomentumPaperEngine
from .providers import CredentialEnvelope

MOMENTUM_ENGINE = MomentumPaperEngine()


def _server_demo_credentials() -> CredentialEnvelope | None:
    api_key = os.getenv("EBA_BINANCE_DEMO_API_KEY", "").strip()
    api_secret = os.getenv("EBA_BINANCE_DEMO_API_SECRET", "").strip()
    if not api_key or not api_secret:
        return None
    return CredentialEnvelope(api_key=api_key, api_secret=api_secret)


def run_server_autoconnect() -> dict[str, Any]:
    credentials = _server_demo_credentials()
    if credentials is None:
        return {
            "ok": False,
            "configured": False,
            "state": "not_configured",
            "message": "Render server Demo secret is not configured",
            "liveExecutionAllowed": False,
        }
    result = base.run_connection_test(
        {
            "provider": "binance",
            "environment": "demo",
            "credentials": {
                "apiKey": credentials.api_key,
                "apiSecret": credentials.api_secret,
            },
        },
        session_store=base.DEMO_SESSIONS,
    )
    result["configured"] = True
    result["credentialMode"] = "server_secret"
    return result


def _session_credentials(payload: dict[str, Any]) -> tuple[str, CredentialEnvelope]:
    token = str(payload.get("sessionToken", ""))
    credentials = base.DEMO_SESSIONS.get(token)
    if credentials is None:
        raise PermissionError("Demo session is missing or expired")
    return token, credentials


def run_momentum_step(payload: dict[str, Any]) -> dict[str, Any]:
    token, credentials = _session_credentials(payload)
    allow_entry = payload.get("allowEntry") is True
    return MOMENTUM_ENGINE.step(token, credentials, allow_entry=allow_entry)


def run_momentum_state(payload: dict[str, Any]) -> dict[str, Any]:
    token, _ = _session_credentials(payload)
    return MOMENTUM_ENGINE.state(token)


def run_momentum_close(payload: dict[str, Any]) -> dict[str, Any]:
    token, credentials = _session_credentials(payload)
    reason = str(payload.get("reason") or "MANUAL_MOMENTUM_CLOSE")[:80]
    return MOMENTUM_ENGINE.close(token, credentials, reason=reason)


class EBAExtendedRequestHandler(base.EBARequestHandler):
    """M18.3 demo server: persistent server-secret login + momentum paper APIs."""

    server_version = "EBA-UI/0.7"

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/api/demo/credential-status":
            configured = _server_demo_credentials() is not None
            self._json_response(
                HTTPStatus.OK,
                {
                    "ok": True,
                    "configured": configured,
                    "credentialMode": "server_secret" if configured else "manual_session",
                    "liveExecutionAllowed": False,
                },
            )
            return
        super().do_GET()

    def do_POST(self) -> None:  # noqa: N802
        extended_paths = {
            "/api/demo/autoconnect",
            "/api/momentum/step",
            "/api/momentum/state",
            "/api/momentum/close",
        }
        if self.path not in extended_paths:
            if self.path == "/api/demo/disconnect":
                self._disconnect_all_paper()
                return
            super().do_POST()
            return

        try:
            payload = self._read_json_payload()
            if self.path == "/api/demo/autoconnect":
                result = run_server_autoconnect()
            elif self.path == "/api/momentum/step":
                result = run_momentum_step(payload)
            elif self.path == "/api/momentum/state":
                result = run_momentum_state(payload)
            else:
                result = run_momentum_close(payload)
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
                    "message": f"Demo momentum request failed: {exc}",
                    "liveExecutionAllowed": False,
                },
            )
            return
        self._json_response(HTTPStatus.OK, result)

    def _read_json_payload(self) -> dict[str, Any]:
        content_length = int(self.headers.get("Content-Length", "0") or "0")
        if content_length <= 0 or content_length > 32_768:
            raise ValueError("invalid request size")
        payload = json.loads(self.rfile.read(content_length).decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("JSON object required")
        return payload

    def _disconnect_all_paper(self) -> None:
        try:
            payload = self._read_json_payload()
            token = str(payload.get("sessionToken", ""))
            if token:
                MOMENTUM_ENGINE.clear(token)
            result = base.run_demo_disconnect_request(
                payload,
                session_store=base.DEMO_SESSIONS,
                paper_engine=base.PAPER_ENGINE,
            )
        except (json.JSONDecodeError, ValueError) as exc:
            self._json_response(
                HTTPStatus.BAD_REQUEST,
                {"ok": False, "message": str(exc), "liveExecutionAllowed": False},
            )
            return
        self._json_response(HTTPStatus.OK, result)


def main() -> None:
    host = os.getenv("EBA_WEB_HOST", "0.0.0.0")
    port = int(os.getenv("PORT", os.getenv("EBA_WEB_PORT", "8000")))
    if not base.WEB_ROOT.exists():
        raise RuntimeError(f"web root missing: {base.WEB_ROOT}")
    server = ThreadingHTTPServer((host, port), EBAExtendedRequestHandler)
    print(
        f"EBA Trader UI serving on http://{host}:{port} "
        "(demo/paper momentum enabled, live locked)"
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
