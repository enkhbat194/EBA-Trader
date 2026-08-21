from __future__ import annotations

from .base import (
    ConnectionState,
    ConnectionTestResult,
    ProviderAdapter,
    ProviderCapability,
)


class MetaTrader5ProviderAdapter(ProviderAdapter):
    """MT5 provider boundary.

    The connection bridge is intentionally not activated in M18.1. The adapter is
    present now so UI/data models are not coupled to Binance.
    """

    @property
    def capabilities(self) -> tuple[ProviderCapability, ...]:
        return (
            ProviderCapability.BALANCE,
            ProviderCapability.MARKET_DATA,
            ProviderCapability.POSITIONS,
            ProviderCapability.PAPER_EXECUTION,
        )

    def test_connection(self) -> ConnectionTestResult:
        if not self.credentials.login or not self.credentials.password or not self.credentials.server:
            return ConnectionTestResult(
                ok=False,
                state=ConnectionState.ERROR,
                message="MT5 requires broker server, login and password",
                capabilities=self.capabilities,
            )
        return ConnectionTestResult(
            ok=False,
            state=ConnectionState.DISCONNECTED,
            message="MT5 bridge is scaffolded but not activated yet",
            capabilities=self.capabilities,
        )


class MetaTrader4ProviderAdapter(ProviderAdapter):
    """MT4 bridge boundary; implementation will use a dedicated EA/bridge service."""

    @property
    def capabilities(self) -> tuple[ProviderCapability, ...]:
        return (
            ProviderCapability.BALANCE,
            ProviderCapability.MARKET_DATA,
            ProviderCapability.POSITIONS,
            ProviderCapability.PAPER_EXECUTION,
        )

    def test_connection(self) -> ConnectionTestResult:
        if not self.credentials.login or not self.credentials.password or not self.credentials.server:
            return ConnectionTestResult(
                ok=False,
                state=ConnectionState.ERROR,
                message="MT4 requires broker server, login and password",
                capabilities=self.capabilities,
            )
        return ConnectionTestResult(
            ok=False,
            state=ConnectionState.DISCONNECTED,
            message="MT4 EA/bridge is scaffolded but not activated yet",
            capabilities=self.capabilities,
        )
