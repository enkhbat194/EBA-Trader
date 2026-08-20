from __future__ import annotations

import os
from dataclasses import dataclass
from enum import StrEnum


class BinanceDataEnvironment(StrEnum):
    LIVE_PUBLIC = "live_public"
    DEMO = "demo"


@dataclass(frozen=True, slots=True)
class BinanceProbeSettings:
    environment: BinanceDataEnvironment = BinanceDataEnvironment.LIVE_PUBLIC
    instrument_id: str = "BTCUSDT.BINANCE"
    bar_type: str = "BTCUSDT.BINANCE-1-MINUTE-LAST-EXTERNAL"

    @classmethod
    def from_env(cls) -> BinanceProbeSettings:
        raw = os.getenv("EBA_BINANCE_DATA_ENV", BinanceDataEnvironment.LIVE_PUBLIC.value)
        try:
            environment = BinanceDataEnvironment(raw.lower())
        except ValueError as exc:
            raise RuntimeError(
                "EBA_BINANCE_DATA_ENV must be 'live_public' or 'demo'"
            ) from exc
        return cls(environment=environment)

    def validate_demo_credentials(self) -> tuple[str | None, str | None]:
        if self.environment is BinanceDataEnvironment.LIVE_PUBLIC:
            return None, None

        api_key = os.getenv("BINANCE_DEMO_API_KEY")
        api_secret = os.getenv("BINANCE_DEMO_API_SECRET")
        if not api_key or not api_secret:
            raise RuntimeError(
                "Demo mode requires BINANCE_DEMO_API_KEY and BINANCE_DEMO_API_SECRET "
                "from environment variables"
            )
        return api_key, api_secret


def build_data_only_node(settings: BinanceProbeSettings | None = None):
    """Build a Binance market-data node with no execution client registered.

    Imports are local so the EBA Trader deterministic core remains usable without
    installing the optional trading dependency.
    """

    settings = settings or BinanceProbeSettings.from_env()
    api_key, api_secret = settings.validate_demo_credentials()

    from nautilus_trader.adapters.binance import (
        BINANCE,
        BinanceAccountType,
        BinanceDataClientConfig,
        BinanceLiveDataClientFactory,
    )
    from nautilus_trader.adapters.binance.common.enums import BinanceEnvironment
    from nautilus_trader.config import InstrumentProviderConfig, LoggingConfig, TradingNodeConfig
    from nautilus_trader.live.node import TradingNode
    from nautilus_trader.model.data import BarType
    from nautilus_trader.model.identifiers import InstrumentId, TraderId
    from nautilus_trader.test_kit.strategies.tester_data import DataTester, DataTesterConfig

    instrument_id = InstrumentId.from_str(settings.instrument_id)
    bar_type = BarType.from_str(settings.bar_type)
    environment = (
        BinanceEnvironment.DEMO
        if settings.environment is BinanceDataEnvironment.DEMO
        else BinanceEnvironment.LIVE
    )

    node_config = TradingNodeConfig(
        trader_id=TraderId("EBA-DATA-001"),
        logging=LoggingConfig(log_level="INFO", use_pyo3=True),
        data_clients={
            BINANCE: BinanceDataClientConfig(
                api_key=api_key,
                api_secret=api_secret,
                environment=environment,
                account_type=BinanceAccountType.SPOT,
                instrument_provider=InstrumentProviderConfig(
                    load_ids=frozenset([instrument_id]),
                ),
            ),
        },
        # SAFETY: no exec_clients are configured in M1.
        timeout_connection=20.0,
        timeout_disconnection=10.0,
        timeout_post_stop=1.0,
    )

    node = TradingNode(config=node_config)
    tester = DataTester(
        config=DataTesterConfig(
            instrument_ids=[instrument_id],
            bar_types=[bar_type],
            subscribe_instrument=True,
            subscribe_quotes=True,
            subscribe_trades=True,
            subscribe_bars=True,
            log_data=True,
        )
    )
    node.trader.add_actor(tester)
    node.add_data_client_factory(BINANCE, BinanceLiveDataClientFactory)
    node.build()
    return node


def run_data_only_probe() -> None:
    node = build_data_only_node()
    try:
        node.run()
    finally:
        node.dispose()
