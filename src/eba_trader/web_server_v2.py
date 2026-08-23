from __future__ import annotations

import json
import os
from http import HTTPStatus
from http.server import ThreadingHTTPServer
from typing import Any

from . import web_server as base
from .autonomous_runner import AutonomousDemoRunner
from .momentum_engine import MomentumPaperEngine
from .providers import CredentialEnvelope

MOMENTUM_ENGINE = MomentumPaperEngine()
APP_VERSION = "0.9.0"
APP_RELEASE = "M18.5"
PWA_CACHE_VERSION = "eba-trader-ui-v9"
APP_RELEASED_AT = "2026-08-23"
APP_CHANGES = [
    "Cash-and-carry and Fast Momentum scanners now run on the Render server",
    "Closing or backgrounding the PWA no longer stops the server scan loop",
    "PWA buttons now control the server runner instead of browser timers",
    "Settings shows server-runner health and last scan timestamps",
    "Live execution remains locked; all autonomous execution is paper-only",
]


def _server_demo_credentials() -> CredentialEnvelope | None:
    api_key = os.getenv("EBA_BINANCE_DEMO_API_KEY", "").strip()
    api_secret = os.getenv("EBA_BINANCE_DEMO_API_SECRET", "").strip()
    if not api_key or not api_secret:
        return None
    return CredentialEnvelope(api_key=api_key, api_secret=api_secret)


RUNNER = AutonomousDemoRunner(
    credentials_loader=_server_demo_credentials,
    snapshot_loader=base.run_demo_fee_snapshot,
    paper_engine=base.PAPER_ENGINE,
    momentum_engine=MOMENTUM_ENGINE,
    interval_seconds=15.0,
    auto_start_carry=True,
    auto_start_fast=True,
)


def _app_info() -> dict[str, Any]:
    build_sha = (
        os.getenv("RENDER_GIT_COMMIT", "").strip()
        or os.getenv("SOURCE_VERSION", "").strip()
        or "unknown"
    )
    return {
        "ok": True,
        "appVersion": APP_VERSION,
        "release": APP_RELEASE,
        "pwaCache": PWA_CACHE_VERSION,
        "buildSha": build_sha,
        "releasedAt": APP_RELEASED_AT,
        "changes": list(APP_CHANGES),
        "serverRunner": True,
        "liveExecutionAllowed": False,
    }


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


def run_runner_start(payload: dict[str, Any]) -> dict[str, Any]:
    carry = payload.get("carry") if "carry" in payload else None
    fast = payload.get("fast") if "fast" in payload else None
    if carry is None and fast is None:
        carry = True
        fast = True
    return RUNNER.set_enabled(
        carry=bool(carry) if carry is not None else None,
        fast=bool(fast) if fast is not None else None,
    )


def run_runner_stop(payload: dict[str, Any]) -> dict[str, Any]:
    carry_requested = payload.get("carry") is True
    fast_requested = payload.get("fast") is True
    if not carry_requested and not fast_requested:
        carry_requested = True
        fast_requested = True
    RUNNER.set_enabled(
        carry=False if carry_requested else None,
        fast=False if fast_requested else None,
    )
    if carry_requested and payload.get("closeCarry") is True:
        RUNNER.close_carry(reason="SERVER_RUNNER_STOP_CLOSE")
    return RUNNER.status()


def run_runner_close(payload: dict[str, Any]) -> dict[str, Any]:
    target = str(payload.get("target") or "").strip().lower()
    if target == "carry":
        RUNNER.close_carry(reason="SERVER_RUNNER_MANUAL_CARRY_CLOSE")
    elif target == "fast":
        RUNNER.close_fast(reason="SERVER_RUNNER_MANUAL_FAST_CLOSE")
    else:
        raise ValueError("target must be carry or fast")
    return RUNNER.status()


class EBAExtendedRequestHandler(base.EBARequestHandler):
    """M18.5 demo server: server-autonomous paper scanners; live remains locked."""

    server_version = "EBA-UI/0.9"

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/api/app-info":
            self._json_response(HTTPStatus.OK, _app_info())
            return
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
        if self.path == "/api/runner/status":
            self._json_response(HTTPStatus.OK, RUNNER.status())
            return
        super().do_GET()

    def do_POST(self) -> None:  # noqa: N802
        extended_paths = {
            "/api/demo/autoconnect",
            "/api/momentum/step",
            "/api/momentum/state",
            "/api/momentum/close",
            "/api/runner/start",
            "/api/runner/stop",
            "/api/runner/close",
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
            elif self.path == "/api/momentum/close":
                result = run_momentum_close(payload)
            elif self.path == "/api/runner/start":
                result = run_runner_start(payload)
            elif self.path == "/api/runner/stop":
                result = run_runner_stop(payload)
            else:
                result = run_runner_close(payload)
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
                    "message": f"Demo server-runner request failed: {exc}",
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
    RUNNER.ensure_started()
    server = ThreadingHTTPServer((host, port), EBAExtendedRequestHandler)
    print(
        f"EBA Trader UI serving on http://{host}:{port} "
        "(server-autonomous demo/paper scanners enabled, live locked)"
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        RUNNER.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
