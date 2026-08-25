from __future__ import annotations

import json
import os
import subprocess
from http import HTTPStatus
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any

from . import web_server as base
from .autonomous_runner import AutonomousDemoRunner
from .persistent_momentum import PersistentMomentumPaperEngine, ledger_from_env
from .providers import CredentialEnvelope
from .research_dashboard import build_research_status

MOMENTUM_ENGINE = PersistentMomentumPaperEngine(ledger=ledger_from_env())
APP_VERSION = "0.12.1"
APP_RELEASE = "LINODE-M6"
PWA_CACHE_VERSION = "eba-trader-ui-v14"
APP_RELEASED_AT = "2026-08-26"
APP_CHANGES = [
    "Home separates carry opportunity from Fast Momentum scanner heartbeat state",
    "Fast Momentum shows last server scan, next expected scan and stale/live heartbeat",
    "Research / AI Lab shows the current M5 frontier and experiment-store state",
    "Order-flow ablation adapters compare candle-only and candle-plus-footprint arms",
    "Linode bootstraps a public HTTPS PWA automatically with an IP-backed hostname",
    "Fast Momentum paper runs from public Binance Demo market data even without account secrets",
    "Fast Momentum OPEN, MARK and CLOSE state remains restart-safe in SQLite",
    "LONG and SHORT remain symmetric paper directions; real execution remains locked",
]


def _server_demo_credentials() -> CredentialEnvelope | None:
    api_key = (
        os.getenv("EBA_BINANCE_DEMO_API_KEY", "").strip()
        or os.getenv("BINANCE_DEMO_API_KEY", "").strip()
    )
    api_secret = (
        os.getenv("EBA_BINANCE_DEMO_API_SECRET", "").strip()
        or os.getenv("BINANCE_DEMO_API_SECRET", "").strip()
    )
    if not api_key or not api_secret:
        return None
    return CredentialEnvelope(api_key=api_key, api_secret=api_secret)


def _build_sha() -> str:
    configured = os.getenv("EBA_BUILD_SHA", "").strip()
    if configured:
        return configured
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=os.getcwd(),
            capture_output=True,
            check=True,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    return result.stdout.strip() or "unknown"


def _public_endpoint() -> tuple[str | None, str | None]:
    host_path = Path("/etc/eba-trader/public-host")
    url_path = Path("/etc/eba-trader/public-url")
    try:
        host = host_path.read_text(encoding="utf-8").strip() if host_path.exists() else ""
        url = url_path.read_text(encoding="utf-8").strip() if url_path.exists() else ""
    except OSError:
        return None, None
    if host and not url:
        url = f"https://{host}/"
    return host or None, url or None


RUNNER = AutonomousDemoRunner(
    credentials_loader=_server_demo_credentials,
    snapshot_loader=base.run_demo_fee_snapshot,
    paper_engine=base.PAPER_ENGINE,
    momentum_engine=MOMENTUM_ENGINE,
    interval_seconds=15.0,
    auto_start_carry=False,
    auto_start_fast=True,
)


def _credential_status() -> dict[str, Any]:
    configured = _server_demo_credentials() is not None
    return {
        "ok": True,
        "configured": configured,
        "credentialMode": "server_secret" if configured else "optional_for_fast_paper",
        "fastPaperAvailable": True,
        "fastMarketDataMode": "authenticated_demo" if configured else "public_demo",
        "fastFeeMode": (
            "account_commission_with_fallback" if configured else "conservative_fallback"
        ),
        "runtime": "linode",
        "liveExecutionAllowed": False,
    }


def _app_info() -> dict[str, Any]:
    public_host, public_url = _public_endpoint()
    return {
        "ok": True,
        "appVersion": APP_VERSION,
        "release": APP_RELEASE,
        "pwaCache": PWA_CACHE_VERSION,
        "buildSha": _build_sha(),
        "releasedAt": APP_RELEASED_AT,
        "changes": list(APP_CHANGES),
        "runtime": "linode",
        "serverRunner": True,
        "persistentLedger": True,
        "publicHost": public_host,
        "publicUrl": public_url,
        "httpsReady": bool(public_url),
        "liveExecutionAllowed": False,
    }


def _research_status() -> dict[str, Any]:
    result = build_research_status()
    result["buildSha"] = _build_sha()
    result["runtime"] = "linode"
    result["liveExecutionAllowed"] = False
    return result


def run_server_autoconnect() -> dict[str, Any]:
    credentials = _server_demo_credentials()
    if credentials is None:
        return {
            "ok": False,
            "configured": False,
            "state": "not_configured",
            "message": (
                "Binance Demo account secret is not configured; "
                "Fast paper still runs from public Demo market data"
            ),
            "fastPaperAvailable": True,
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
    result["runtime"] = "linode"
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
        fast = True
    return RUNNER.set_enabled(
        carry=bool(carry) if carry is not None else None,
        fast=bool(fast) if fast is not None else None,
    )


def run_runner_stop(payload: dict[str, Any]) -> dict[str, Any]:
    carry_requested = payload.get("carry") is True
    fast_requested = payload.get("fast") is True
    if not carry_requested and not fast_requested:
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
    """Linode PWA server with autonomous paper scanners; real execution locked."""

    server_version = "EBA-UI/0.12.1"

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/api/app-info":
            self._json_response(HTTPStatus.OK, _app_info())
            return
        if self.path == "/api/research/status":
            self._json_response(HTTPStatus.OK, _research_status())
            return
        if self.path == "/api/demo/credential-status":
            self._json_response(HTTPStatus.OK, _credential_status())
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
                    "message": f"Linode server-runner request failed: {exc}",
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
    host = os.getenv("EBA_WEB_HOST", "127.0.0.1")
    port = int(os.getenv("EBA_WEB_PORT", "8000"))
    if not base.WEB_ROOT.exists():
        raise RuntimeError(f"web root missing: {base.WEB_ROOT}")
    RUNNER.ensure_started()
    server = ThreadingHTTPServer((host, port), EBAExtendedRequestHandler)
    print(
        f"EBA Trader Linode UI serving on http://{host}:{port} "
        "(server-autonomous paper scanner enabled, real execution locked)",
        flush=True,
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
