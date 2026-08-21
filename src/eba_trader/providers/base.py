from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum


class ProviderKind(StrEnum):
    BINANCE = "binance"
    METATRADER5 = "metatrader5"
    METATRADER4 = "metatrader4"


class ProviderEnvironment(StrEnum):
    DEMO = "demo"
    LIVE = "live"


class ConnectionState(StrEnum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


class ProviderCapability(StrEnum):
    BALANCE = "balance"
    MARKET_DATA = "market_data"
    POSITIONS = "positions"
    FEES = "fees"
    PAPER_EXECUTION = "paper_execution"
    LIVE_EXECUTION = "live_execution"


@dataclass(frozen=True, slots=True)
class CredentialEnvelope:
    api_key: str = ""
    api_secret: str = ""
    login: str = ""
    password: str = ""
    server: str = ""

    def redacted(self) -> dict[str, str]:
        return {
            "api_key": "••••••••" if self.api_key else "",
            "api_secret": "••••••••" if self.api_secret else "",
            "login": self.login,
            "password": "••••••••" if self.password else "",
            "server": self.server,
        }


@dataclass(frozen=True, slots=True)
class ConnectionProfile:
    connection_id: str
    provider: ProviderKind
    environment: ProviderEnvironment
    label: str
    enabled: bool = True
    metadata: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.connection_id.strip():
            raise ValueError("connection_id is required")
        if not self.label.strip():
            raise ValueError("label is required")


@dataclass(frozen=True, slots=True)
class ConnectionTestResult:
    ok: bool
    state: ConnectionState
    message: str
    latency_ms: int | None = None
    account_label: str | None = None
    capabilities: tuple[ProviderCapability, ...] = ()
    balances: dict[str, float] = field(default_factory=dict)


class ProviderAdapter(ABC):
    """Provider-neutral exchange/broker boundary.

    M18.1 deliberately exposes no order-placement contract. Live execution remains
    outside this interface until a later separately validated release.
    """

    def __init__(self, profile: ConnectionProfile, credentials: CredentialEnvelope) -> None:
        self.profile = profile
        self.credentials = credentials

    @property
    @abstractmethod
    def capabilities(self) -> tuple[ProviderCapability, ...]:
        raise NotImplementedError

    @abstractmethod
    def test_connection(self) -> ConnectionTestResult:
        raise NotImplementedError
