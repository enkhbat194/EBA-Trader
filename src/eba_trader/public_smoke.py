from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

DEFAULT_PUBLIC_URL = "https://eba-trader-172-236-150-62.sslip.io"


class ProductionSmokeError(RuntimeError):
    """Raised when the externally visible production contract is not satisfied."""


@dataclass(frozen=True, slots=True)
class SmokeSummary:
    build_sha: str
    research_ok: bool
    demo_vault_ok: bool
    demo_autoconnect_ok: bool
    fast_positions_ok: bool
    chart_ok: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "buildSha": self.build_sha,
            "researchOk": self.research_ok,
            "demoVaultOk": self.demo_vault_ok,
            "demoAutoconnectOk": self.demo_autoconnect_ok,
            "fastPositionsOk": self.fast_positions_ok,
            "chartOk": self.chart_ok,
        }


def _url(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}{path}"


def _request_json(
    base_url: str,
    path: str,
    *,
    payload: dict[str, Any] | None = None,
    timeout: float = 15.0,
) -> dict[str, Any]:
    body = None
    method = "GET"
    headers = {"Accept": "application/json", "User-Agent": "EBA-Production-Smoke/1"}
    if payload is not None:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        method = "POST"
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(
        _url(base_url, path),
        data=body,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        raise ProductionSmokeError(f"{path} returned HTTP {exc.code}: {raw[:160]}") from exc
    except urllib.error.URLError as exc:
        raise ProductionSmokeError(f"{path} request failed: {exc.reason}") from exc
    try:
        result = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ProductionSmokeError(f"{path} returned non-JSON data") from exc
    if not isinstance(result, dict):
        raise ProductionSmokeError(f"{path} did not return a JSON object")
    return result


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ProductionSmokeError(message)


def wait_for_build(
    base_url: str,
    expected_build: str | None,
    *,
    timeout_seconds: float,
    poll_seconds: float = 15.0,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    last_build = "unknown"
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            info = _request_json(base_url, "/api/app-info")
            last_build = str(info.get("buildSha") or "unknown")
            if expected_build is None or last_build == expected_build:
                _require(info.get("ok") is True, "app-info ok flag is not true")
                _require(info.get("runtime") == "linode", "production runtime is not Linode")
                _require(info.get("httpsReady") is True, "public HTTPS is not ready")
                _require(
                    info.get("liveExecutionAllowed") is False,
                    "public production unexpectedly allows live execution",
                )
                return info
        except ProductionSmokeError as exc:
            last_error = exc
        time.sleep(poll_seconds)

    detail = f"last visible build={last_build}"
    if last_error is not None:
        detail += f"; last error={last_error}"
    if expected_build:
        raise ProductionSmokeError(
            f"production did not deploy expected build {expected_build} before timeout; {detail}"
        )
    raise ProductionSmokeError(f"production app-info did not become healthy; {detail}")


def verify_research(base_url: str, *, expected_build: str) -> None:
    status = _request_json(base_url, "/api/research/status")
    _require(status.get("ok") is True, "research status is not healthy")
    _require(status.get("runtime") == "linode", "research status is not from Linode")
    _require(status.get("buildSha") == expected_build, "research endpoint build is stale")
    _require(status.get("liveExecutionAllowed") is False, "research endpoint allows live execution")
    locks = status.get("locks")
    _require(isinstance(locks, dict), "research locks are missing")
    _require(locks.get("frozenOos") is True, "frozen OOS lock is not engaged")
    _require(locks.get("realExecution") is True, "real-execution lock is not engaged")
    store = status.get("researchStore")
    _require(isinstance(store, dict), "research store status is missing")


def verify_demo_vault(base_url: str) -> None:
    status = _request_json(base_url, "/api/demo/credential-status")
    _require(status.get("ok") is True, "Demo credential vault is unhealthy")
    _require(status.get("configured") is True, "Demo credential is not configured")
    _require(
        status.get("credentialMode") == "encrypted_server_vault",
        "Demo credential is not using the encrypted server vault",
    )
    _require(status.get("liveExecutionAllowed") is False, "Demo vault allows live execution")
    _require(bool(status.get("maskedApiKey")), "Demo vault does not expose masked-key metadata")


def verify_demo_autoconnect(base_url: str, *, attempts: int = 3) -> None:
    last_message = "unknown"
    for attempt in range(attempts):
        try:
            result = _request_json(base_url, "/api/demo/autoconnect", payload={})
            last_message = str(result.get("message") or result.get("state") or "unknown")
            if result.get("ok") is True:
                _require(
                    result.get("configured") is True,
                    "autoconnect lost saved Demo configuration",
                )
                _require(
                    result.get("credentialMode") == "encrypted_server_vault",
                    "autoconnect did not load the encrypted Demo vault",
                )
                _require(
                    result.get("liveExecutionAllowed") is False,
                    "Demo autoconnect unexpectedly allows live execution",
                )
                return
        except ProductionSmokeError as exc:
            last_message = str(exc)
        if attempt + 1 < attempts:
            time.sleep(5.0)
    raise ProductionSmokeError(f"saved Demo no-paste autoconnect failed: {last_message}")


def verify_fast_positions(base_url: str) -> None:
    status = _request_json(base_url, "/api/runner/status")
    _require(status.get("ok") is True, "server runner is not healthy")
    _require(status.get("serverSide") is True, "Fast runner is not server-side")
    _require(status.get("pwaRequired") is False, "Fast runner incorrectly requires the PWA")
    _require(status.get("fastThreadAlive") is True, "Fast runner thread is not alive")
    _require(status.get("fastRunning") is True, "Fast scanner is not enabled")
    _require(
        status.get("demoCredentialsConfigured") is True,
        "server runner did not reload the saved Demo credential",
    )
    _require(status.get("liveExecutionAllowed") is False, "runner allows live execution")
    fast_state = status.get("fastState")
    _require(isinstance(fast_state, dict), "Fast position state is missing")
    _require("openPosition" in fast_state, "Fast position state lacks openPosition")
    _require(isinstance(fast_state.get("history"), list), "Fast position history is invalid")
    _require(fast_state.get("liveExecutionAllowed") is False, "Fast state allows live execution")


def verify_chart(base_url: str) -> None:
    chart = _request_json(
        base_url,
        "/api/chart",
        payload={
            "provider": "binance",
            "symbol": "BTCUSDT",
            "timeframe": "15m",
            "limit": 20,
        },
    )
    _require(chart.get("provider") == "binance", "chart provider is not Binance")
    _require(chart.get("symbol") == "BTCUSDT", "chart symbol is not BTCUSDT")
    _require(chart.get("timeframe") == "15m", "chart timeframe is not 15m")
    _require(chart.get("environment") == "demo", "chart is not using Demo environment")
    _require(chart.get("liveExecutionAllowed") is False, "chart path allows live execution")
    candles = chart.get("candles")
    _require(isinstance(candles, list) and len(candles) >= 10, "chart returned too few candles")
    times = [int(item["time"]) for item in candles if isinstance(item, dict) and "time" in item]
    _require(len(times) == len(candles), "chart candle timestamps are incomplete")
    ordered = all(left < right for left, right in zip(times, times[1:], strict=False))
    _require(ordered, "chart candles are not strictly ordered")


def run_public_production_smoke(
    *,
    base_url: str,
    expected_build: str | None,
    timeout_seconds: float,
) -> SmokeSummary:
    app = wait_for_build(
        base_url,
        expected_build,
        timeout_seconds=timeout_seconds,
    )
    build_sha = str(app.get("buildSha") or "unknown")
    verify_research(base_url, expected_build=build_sha)
    verify_demo_vault(base_url)
    verify_demo_autoconnect(base_url)
    verify_fast_positions(base_url)
    verify_chart(base_url)
    return SmokeSummary(
        build_sha=build_sha,
        research_ok=True,
        demo_vault_ok=True,
        demo_autoconnect_ok=True,
        fast_positions_ok=True,
        chart_ok=True,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify the external EBA Trader Linode production PWA and read-only/paper APIs."
    )
    parser.add_argument(
        "--base-url",
        default=os.getenv("EBA_PUBLIC_PWA_URL", DEFAULT_PUBLIC_URL),
    )
    parser.add_argument(
        "--expected-build",
        default=os.getenv("EBA_EXPECTED_BUILD_SHA", "").strip() or None,
    )
    parser.add_argument("--timeout-seconds", type=float, default=720.0)
    return parser


def main() -> None:
    args = _parser().parse_args()
    summary = run_public_production_smoke(
        base_url=args.base_url,
        expected_build=args.expected_build,
        timeout_seconds=args.timeout_seconds,
    )
    print(json.dumps(summary.as_dict(), sort_keys=True))


if __name__ == "__main__":
    main()
