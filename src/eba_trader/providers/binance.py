from __future__ import annotations

import hashlib
import hmac
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

from .base import (
    ConnectionState,
    ConnectionTestResult,
    ProviderAdapter,
    ProviderCapability,
    ProviderEnvironment,
)


@dataclass(frozen=True, slots=True)
class BinanceEndpointSet:
    spot_rest: str
    futures_rest: str


BINANCE_ENDPOINTS = {
    ProviderEnvironment.DEMO: BinanceEndpointSet(
        spot_rest="https://testnet.binance.vision",
        futures_rest="https://testnet.binancefuture.com",
    ),
    ProviderEnvironment.LIVE: BinanceEndpointSet(
        spot_rest="https://api.binance.com",
        futures_rest="https://fapi.binance.com",
    ),
}


def _parse_balances(payload: dict[str, object]) -> dict[str, float]:
    raw_balances = payload.get("balances")
    if not isinstance(raw_balances, list):
        return {}

    balances: dict[str, float] = {}
    for item in raw_balances:
        if not isinstance(item, dict):
            continue
        asset = str(item.get("asset", "")).strip()
        if not asset:
            continue
        try:
            free = float(item.get("free", 0.0))
            locked = float(item.get("locked", 0.0))
        except (TypeError, ValueError):
            continue
        total = free + locked
        if total < 0:
            continue
        balances[asset] = total
    return balances


class BinanceProviderAdapter(ProviderAdapter):
    """Read-only Binance connection adapter.

    Demo mode is the default product path. This class contains no order, cancel,
    transfer, withdrawal, or leverage-changing methods.
    """

    @property
    def capabilities(self) -> tuple[ProviderCapability, ...]:
        return (
            ProviderCapability.BALANCE,
            ProviderCapability.MARKET_DATA,
            ProviderCapability.FEES,
            ProviderCapability.POSITIONS,
            ProviderCapability.PAPER_EXECUTION,
        )

    def test_connection(self) -> ConnectionTestResult:
        if not self.credentials.api_key or not self.credentials.api_secret:
            return ConnectionTestResult(
                ok=False,
                state=ConnectionState.ERROR,
                message="API key and secret are required",
                capabilities=self.capabilities,
            )

        endpoints = BINANCE_ENDPOINTS[self.profile.environment]
        started = time.perf_counter()
        try:
            payload = self._signed_get(
                endpoints.spot_rest,
                "/api/v3/account",
                params={"omitZeroBalances": "true"},
            )
        except Exception as exc:  # network/API failures are returned to the UI, not raised
            return ConnectionTestResult(
                ok=False,
                state=ConnectionState.ERROR,
                message=f"Binance connection failed: {exc}",
                capabilities=self.capabilities,
            )

        latency_ms = int((time.perf_counter() - started) * 1000)
        account_label = str(payload.get("uid") or payload.get("accountType") or "Binance")
        return ConnectionTestResult(
            ok=True,
            state=ConnectionState.CONNECTED,
            message=f"{self.profile.environment.value.upper()} connection successful",
            latency_ms=latency_ms,
            account_label=account_label,
            capabilities=self.capabilities,
            balances=_parse_balances(payload),
        )

    def _signed_get(
        self,
        base_url: str,
        path: str,
        *,
        params: dict[str, str] | None = None,
    ) -> dict[str, object]:
        query = dict(params or {})
        query["timestamp"] = str(int(time.time() * 1000))
        query["recvWindow"] = "5000"
        encoded = urllib.parse.urlencode(query)
        signature = hmac.new(
            self.credentials.api_secret.encode("utf-8"),
            encoded.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        request = urllib.request.Request(
            f"{base_url}{path}?{encoded}&signature={signature}",
            headers={"X-MBX-APIKEY": self.credentials.api_key},
            method="GET",
        )
        try:
            with urllib.request.urlopen(request, timeout=10.0) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {exc.code}: {body[:240]}") from exc
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise RuntimeError("unexpected Binance response")
        return payload
