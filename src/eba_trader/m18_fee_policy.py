from __future__ import annotations

from dataclasses import dataclass

M18_POLICY_NAME = "m18_fee_aware_execution_economics_v1"
M18_STATUS = "ENGINEERING_VALIDATION_NO_LIVE_EXECUTION"

SPOT_SYMBOL = "BTCUSDT"
DEFAULT_QUANTITY_BTC = 0.001
DEFAULT_DEPTH_LIMIT = 100
MAX_QUOTE_AGE_MS = 1_500
EXIT_SLIPPAGE_RESERVE_BPS_PER_LEG = 2.0
SAFETY_BUFFER_BPS = 5.0
MIN_SCREENING_NET_EDGE_BPS = 5.0
RECV_WINDOW_MS = 5_000

SPOT_BASE_URL = "https://api.binance.com"
FUTURES_BASE_URL = "https://fapi.binance.com"
SPOT_COMMISSION_ENDPOINT = "/api/v3/account/commission"
FUTURES_COMMISSION_ENDPOINT = "/fapi/v1/commissionRate"
SPOT_DEPTH_ENDPOINT = "/api/v3/depth"
FUTURES_DEPTH_ENDPOINT = "/fapi/v1/depth"
FUTURES_EXCHANGE_INFO_ENDPOINT = "/fapi/v1/exchangeInfo"


@dataclass(frozen=True, slots=True)
class M18ExecutionPolicy:
    max_quote_age_ms: int = MAX_QUOTE_AGE_MS
    exit_slippage_reserve_bps_per_leg: float = EXIT_SLIPPAGE_RESERVE_BPS_PER_LEG
    safety_buffer_bps: float = SAFETY_BUFFER_BPS
    min_screening_net_edge_bps: float = MIN_SCREENING_NET_EDGE_BPS
    depth_limit: int = DEFAULT_DEPTH_LIMIT
    live_execution_allowed: bool = False
    ai_signal_authority: bool = False

    def __post_init__(self) -> None:
        if self.max_quote_age_ms <= 0:
            raise ValueError("max_quote_age_ms must be positive")
        if self.depth_limit <= 0:
            raise ValueError("depth_limit must be positive")
        for name, value in (
            ("exit_slippage_reserve_bps_per_leg", self.exit_slippage_reserve_bps_per_leg),
            ("safety_buffer_bps", self.safety_buffer_bps),
            ("min_screening_net_edge_bps", self.min_screening_net_edge_bps),
        ):
            if value < 0:
                raise ValueError(f"{name} must be non-negative")
        if self.live_execution_allowed:
            raise ValueError("M18 live execution is intentionally forbidden")
        if self.ai_signal_authority:
            raise ValueError("M18 AI signal authority is intentionally forbidden")
