from __future__ import annotations

from dataclasses import dataclass

from .domain import ExecutionMode


@dataclass(frozen=True, slots=True)
class AppConfig:
    symbol: str = "BTCUSDT"
    execution_mode: ExecutionMode = ExecutionMode.PAPER
    primary_venue: str = "BINANCE"
    live_execution_enabled: bool = False

    def validate(self) -> None:
        if (
            self.execution_mode in {ExecutionMode.MICRO_LIVE, ExecutionMode.LIVE}
            and not self.live_execution_enabled
        ):
            raise RuntimeError("Live execution is locked in V1")

        if self.symbol != "BTCUSDT":
            raise RuntimeError("V1 scope is frozen to BTCUSDT")

        if self.primary_venue != "BINANCE":
            raise RuntimeError("V1 primary venue is frozen to BINANCE")
