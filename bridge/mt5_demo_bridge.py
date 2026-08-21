from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from typing import Any

DEFAULT_SYMBOLS = ("XAUUSD", "XAGUSD", "USOIL")
TIMEFRAMES = ("1m", "5m", "15m", "1h")
TIMEFRAME_NAMES = {
    "1m": "TIMEFRAME_M1",
    "5m": "TIMEFRAME_M5",
    "15m": "TIMEFRAME_M15",
    "1h": "TIMEFRAME_H1",
}
ALIASES = {
    "XAUUSD": ("XAUUSD", "GOLD"),
    "XAGUSD": ("XAGUSD", "SILVER"),
    "USOIL": ("USOIL", "WTI", "XTIUSD", "OILUSD"),
}


def _post_json(url: str, payload: dict[str, Any], *, timeout: float = 15.0) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"EBA HTTP {exc.code}: {body[:300]}") from exc
    if not isinstance(result, dict):
        raise RuntimeError("unexpected EBA bridge response")
    return result


def _as_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if hasattr(value, "_asdict"):
        return dict(value._asdict())
    return {}


def _safe_number(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _discover_symbol(mt5: Any, requested: str) -> str | None:
    symbols = mt5.symbols_get()
    if symbols is None:
        return None
    names = [str(getattr(item, "name", "")) for item in symbols]
    upper_to_original = {name.upper(): name for name in names if name}
    for alias in ALIASES.get(requested, (requested,)):
        exact = upper_to_original.get(alias.upper())
        if exact:
            return exact
    for alias in ALIASES.get(requested, (requested,)):
        needle = alias.upper()
        for name in names:
            if needle in name.upper():
                return name
    return None


def _bars(mt5: Any, symbol: str, timeframe_name: str, count: int) -> list[dict[str, Any]]:
    timeframe = getattr(mt5, TIMEFRAME_NAMES[timeframe_name])
    rows = mt5.copy_rates_from_pos(symbol, timeframe, 0, count)
    if rows is None:
        return []
    bars: list[dict[str, Any]] = []
    for row in rows:
        bars.append(
            {
                "time": int(row["time"]),
                "open": _safe_number(row["open"]),
                "high": _safe_number(row["high"]),
                "low": _safe_number(row["low"]),
                "close": _safe_number(row["close"]),
                "volume": _safe_number(row["tick_volume"]),
            }
        )
    return bars


def build_snapshot(mt5: Any, requested_symbols: tuple[str, ...], *, bars: int) -> dict[str, Any]:
    account = _as_dict(mt5.account_info())
    terminal = _as_dict(mt5.terminal_info())
    resolved: dict[str, str] = {}
    ticks: dict[str, dict[str, Any]] = {}
    charts: dict[str, dict[str, list[dict[str, Any]]]] = {}

    for requested in requested_symbols:
        actual = _discover_symbol(mt5, requested)
        if actual is None:
            continue
        resolved[requested] = actual
        mt5.symbol_select(actual, True)
        tick = _as_dict(mt5.symbol_info_tick(actual))
        ticks[requested] = {
            "brokerSymbol": actual,
            "bid": _safe_number(tick.get("bid")),
            "ask": _safe_number(tick.get("ask")),
            "last": _safe_number(tick.get("last")),
            "timeMsc": int(tick.get("time_msc") or 0),
        }
        charts[requested] = {
            timeframe: _bars(mt5, actual, timeframe, bars) for timeframe in TIMEFRAMES
        }

    positions_raw = mt5.positions_get() or ()
    positions: list[dict[str, Any]] = []
    for position in positions_raw:
        item = _as_dict(position)
        positions.append(
            {
                "ticket": int(item.get("ticket") or 0),
                "symbol": str(item.get("symbol") or ""),
                "type": int(item.get("type") or 0),
                "volume": _safe_number(item.get("volume")),
                "priceOpen": _safe_number(item.get("price_open")),
                "priceCurrent": _safe_number(item.get("price_current")),
                "sl": _safe_number(item.get("sl")),
                "tp": _safe_number(item.get("tp")),
                "profit": _safe_number(item.get("profit")),
            }
        )

    return {
        "bridgeVersion": 1,
        "readOnly": True,
        "timestampMs": int(time.time() * 1000),
        "account": {
            "login": int(account.get("login") or 0),
            "server": str(account.get("server") or ""),
            "company": str(account.get("company") or ""),
            "currency": str(account.get("currency") or ""),
            "balance": _safe_number(account.get("balance")),
            "equity": _safe_number(account.get("equity")),
            "profit": _safe_number(account.get("profit")),
            "margin": _safe_number(account.get("margin")),
            "marginFree": _safe_number(account.get("margin_free")),
            "leverage": int(account.get("leverage") or 0),
            "tradeMode": int(account.get("trade_mode") or 0),
        },
        "terminal": {
            "connected": bool(terminal.get("connected", False)),
            "tradeAllowed": bool(terminal.get("trade_allowed", False)),
            "tradeApiDisabled": bool(terminal.get("tradeapi_disabled", False)),
        },
        "resolvedSymbols": resolved,
        "ticks": ticks,
        "charts": charts,
        "positions": positions,
        "markers": [],
    }


def run() -> None:
    parser = argparse.ArgumentParser(description="EBA Trader MT5 Demo read-only bridge")
    parser.add_argument("--eba-url", required=True, help="EBA Trader HTTPS base URL")
    parser.add_argument("--pair-token", required=True, help="Pair token generated inside EBA Trader")
    parser.add_argument("--symbols", default=",".join(DEFAULT_SYMBOLS))
    parser.add_argument("--interval", type=float, default=15.0)
    parser.add_argument("--bars", type=int, default=120)
    args = parser.parse_args()

    if not args.eba_url.lower().startswith("https://"):
        raise SystemExit("EBA URL must use HTTPS")
    if args.interval < 5:
        raise SystemExit("interval must be at least 5 seconds")
    if args.bars < 30 or args.bars > 240:
        raise SystemExit("bars must be between 30 and 240")

    try:
        import MetaTrader5 as mt5
    except ImportError as exc:
        raise SystemExit("Install the local package first: py -m pip install MetaTrader5") from exc

    if not mt5.initialize():
        raise SystemExit(f"MT5 initialize failed: {mt5.last_error()}")
    account = mt5.account_info()
    if account is None:
        mt5.shutdown()
        raise SystemExit(f"MT5 account unavailable: {mt5.last_error()}")

    symbols = tuple(item.strip().upper() for item in args.symbols.split(",") if item.strip())
    endpoint = args.eba_url.rstrip("/") + "/api/mt5/ingest"
    print(f"EBA MT5 Demo bridge connected to account {account.login} @ {account.server}")
    print("READ-ONLY bridge: this program contains no order_send call.")

    try:
        while True:
            snapshot = build_snapshot(mt5, symbols, bars=args.bars)
            result = _post_json(endpoint, {"pairToken": args.pair_token, "snapshot": snapshot})
            print(
                f"heartbeat={result.get('state')} symbols={len(snapshot['resolvedSymbols'])} "
                f"positions={len(snapshot['positions'])}"
            )
            time.sleep(args.interval)
    except KeyboardInterrupt:
        pass
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    run()
