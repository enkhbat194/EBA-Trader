from __future__ import annotations

import hashlib
import hmac
import json
import time
import urllib.parse
import urllib.request
from dataclasses import asdict
from typing import Any

from .m18_fee_aware import (
    BookSnapshot,
    FeeAwarePairEstimate,
    FuturesCommissionSnapshot,
    SpotCommissionSnapshot,
    evaluate_cash_carry_snapshot,
    parse_book,
    parse_futures_commission,
    parse_spot_commission,
    select_nearest_btcusdt_delivery_symbol,
)
from .m18_fee_policy import DEFAULT_QUANTITY_BTC, SPOT_SYMBOL, M18ExecutionPolicy
from .providers import CredentialEnvelope
from .providers.base import ProviderEnvironment
from .providers.binance import BINANCE_ENDPOINTS

SPOT_COMMISSION_ENDPOINT = "/api/v3/account/commission"
SPOT_DEPTH_ENDPOINT = "/api/v3/depth"
FUTURES_COMMISSION_ENDPOINT = "/fapi/v1/commissionRate"
FUTURES_DEPTH_ENDPOINT = "/fapi/v1/depth"
FUTURES_EXCHANGE_INFO_ENDPOINT = "/fapi/v1/exchangeInfo"
RECV_WINDOW_MS = 5_000


class BinanceDemoReadOnlyClient:
    """Read-only Binance Spot + USD-M Testnet client.

    This client intentionally exposes no order, cancel, transfer, withdrawal,
    leverage, or live-environment methods.
    """

    def __init__(self, credentials: CredentialEnvelope, *, timeout_seconds: float = 10.0) -> None:
        if not credentials.api_key or not credentials.api_secret:
            raise ValueError("Spot Testnet API key and secret are required")
        if not credentials.futures_api_key or not credentials.futures_api_secret:
            raise ValueError("USD-M Futures Testnet API key and secret are required")
        self._credentials = credentials
        self._timeout_seconds = timeout_seconds
        endpoints = BINANCE_ENDPOINTS[ProviderEnvironment.DEMO]
        self._spot_base_url = endpoints.spot_rest
        self._futures_base_url = endpoints.futures_rest

    def _get_json(self, url: str, *, api_key: str | None = None) -> dict[str, Any]:
        headers = {"Accept": "application/json"}
        if api_key:
            headers["X-MBX-APIKEY"] = api_key
        request = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(request, timeout=self._timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if not isinstance(payload, dict):
            raise RuntimeError("unexpected Binance Testnet JSON response")
        return payload

    def _public_get(self, base_url: str, endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
        query = urllib.parse.urlencode(params)
        url = f"{base_url}{endpoint}"
        if query:
            url = f"{url}?{query}"
        return self._get_json(url)

    def _signed_get(
        self,
        base_url: str,
        endpoint: str,
        params: dict[str, Any],
        *,
        api_key: str,
        api_secret: str,
    ) -> dict[str, Any]:
        signed = dict(params)
        signed.setdefault("recvWindow", RECV_WINDOW_MS)
        signed.setdefault("timestamp", int(time.time() * 1000))
        query = urllib.parse.urlencode(signed)
        signature = hmac.new(
            api_secret.encode("utf-8"),
            query.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return self._get_json(
            f"{base_url}{endpoint}?{query}&signature={signature}",
            api_key=api_key,
        )

    def spot_commission(self) -> SpotCommissionSnapshot:
        payload = self._signed_get(
            self._spot_base_url,
            SPOT_COMMISSION_ENDPOINT,
            {"symbol": SPOT_SYMBOL},
            api_key=self._credentials.api_key,
            api_secret=self._credentials.api_secret,
        )
        return parse_spot_commission(payload)

    def futures_commission(self, symbol: str) -> FuturesCommissionSnapshot:
        payload = self._signed_get(
            self._futures_base_url,
            FUTURES_COMMISSION_ENDPOINT,
            {"symbol": symbol},
            api_key=self._credentials.futures_api_key,
            api_secret=self._credentials.futures_api_secret,
        )
        return parse_futures_commission(payload)

    def spot_book(self, *, limit: int) -> BookSnapshot:
        payload = self._public_get(
            self._spot_base_url,
            SPOT_DEPTH_ENDPOINT,
            {"symbol": SPOT_SYMBOL, "limit": limit},
        )
        return parse_book(payload, symbol=SPOT_SYMBOL, received_at_ms=int(time.time() * 1000))

    def futures_book(self, symbol: str, *, limit: int) -> BookSnapshot:
        payload = self._public_get(
            self._futures_base_url,
            FUTURES_DEPTH_ENDPOINT,
            {"symbol": symbol, "limit": limit},
        )
        return parse_book(payload, symbol=symbol, received_at_ms=int(time.time() * 1000))

    def futures_exchange_info(self) -> dict[str, Any]:
        return self._public_get(self._futures_base_url, FUTURES_EXCHANGE_INFO_ENDPOINT, {})


def _estimate_payload(estimate: FeeAwarePairEstimate) -> dict[str, Any]:
    payload = asdict(estimate)
    payload["decision"] = estimate.decision.value
    payload["reason_codes"] = list(estimate.reason_codes)
    return payload


def run_demo_fee_snapshot(
    credentials: CredentialEnvelope,
    *,
    quantity_btc: float = DEFAULT_QUANTITY_BTC,
    client: BinanceDemoReadOnlyClient | None = None,
) -> dict[str, Any]:
    """Return one immutable-in-memory Demo screening snapshot.

    Missing Testnet quarterly contracts fail closed instead of falling back to a
    live market or a different strategy.
    """

    demo_client = client or BinanceDemoReadOnlyClient(credentials)
    now_ms = int(time.time() * 1000)
    policy = M18ExecutionPolicy()
    try:
        futures_symbol = select_nearest_btcusdt_delivery_symbol(
            demo_client.futures_exchange_info(),
            now_ms=now_ms,
        )
    except RuntimeError:
        return {
            "mode": "DEMO_READ_ONLY",
            "decision": "NO_TRADE",
            "reasonCodes": ["NO_ACTIVE_TESTNET_DELIVERY_CONTRACT"],
            "environment": "demo",
            "liveExecutionAllowed": False,
            "snapshotTimeMs": now_ms,
        }

    spot_commission = demo_client.spot_commission()
    futures_commission = demo_client.futures_commission(futures_symbol)
    spot_book = demo_client.spot_book(limit=policy.depth_limit)
    futures_book = demo_client.futures_book(futures_symbol, limit=policy.depth_limit)
    evaluation_time_ms = int(time.time() * 1000)
    estimate = evaluate_cash_carry_snapshot(
        spot_book=spot_book,
        futures_book=futures_book,
        spot_commission=spot_commission,
        futures_commission=futures_commission,
        quantity_btc=quantity_btc,
        now_ms=evaluation_time_ms,
        policy=policy,
    )
    return {
        "mode": "DEMO_READ_ONLY",
        "decision": estimate.decision.value,
        "reasonCodes": list(estimate.reason_codes),
        "estimate": _estimate_payload(estimate),
        "policy": asdict(policy),
        "futuresSymbol": futures_symbol,
        "environment": "demo",
        "snapshotTimeMs": evaluation_time_ms,
        "liveExecutionAllowed": False,
    }
