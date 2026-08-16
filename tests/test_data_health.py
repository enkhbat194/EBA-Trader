import pytest

from eba_trader.data_health import DataHealthStatus, MarketDataHealth


def test_data_health_starts_without_data() -> None:
    health = MarketDataHealth(max_age_ms=1_000)
    snapshot = health.snapshot(now_ns=1_000_000_000)

    assert snapshot.status is DataHealthStatus.STARTING
    assert snapshot.events_seen == 0
    assert snapshot.age_ms is None


def test_data_health_becomes_healthy_after_event() -> None:
    health = MarketDataHealth(max_age_ms=1_000)
    health.mark_event(received_ns=1_000_000_000)

    snapshot = health.snapshot(now_ns=1_500_000_000)

    assert snapshot.status is DataHealthStatus.HEALTHY
    assert snapshot.events_seen == 1
    assert snapshot.age_ms == 500.0


def test_data_health_becomes_stale() -> None:
    health = MarketDataHealth(max_age_ms=1_000)
    health.mark_event(received_ns=1_000_000_000)

    snapshot = health.snapshot(now_ns=2_000_000_001)

    assert snapshot.status is DataHealthStatus.STALE
    assert snapshot.age_ms > 1_000


def test_data_health_stopped_is_terminal() -> None:
    health = MarketDataHealth()
    health.mark_event(received_ns=1_000_000_000)
    health.stop()

    assert health.snapshot(now_ns=2_000_000_000).status is DataHealthStatus.STOPPED
    with pytest.raises(RuntimeError):
        health.mark_event(received_ns=2_000_000_000)


def test_data_health_rejects_backwards_clock() -> None:
    health = MarketDataHealth()
    health.mark_event(received_ns=2_000_000_000)

    with pytest.raises(ValueError):
        health.mark_event(received_ns=1_000_000_000)
