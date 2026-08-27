import json
import sqlite3
from pathlib import Path

import pytest

from eba_trader.lifecycle import (
    CURRENT_LIFECYCLE_POLICY_VERSION,
    LEGACY_LIFECYCLE_POLICY_VERSION,
    StrategyLifecycle,
)
from eba_trader.research_store import ResearchStore


def _write_legacy_db(path: Path, *, state: StrategyLifecycle) -> None:
    connection = sqlite3.connect(path)
    connection.executescript(
        """
        CREATE TABLE strategies (
            strategy_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            family TEXT,
            active_version INTEGER,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE strategy_versions (
            strategy_id TEXT NOT NULL,
            version INTEGER NOT NULL CHECK (version > 0),
            lifecycle_state TEXT NOT NULL,
            spec_json TEXT NOT NULL,
            spec_sha256 TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY(strategy_id, version)
        );

        CREATE TABLE lifecycle_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            strategy_id TEXT NOT NULL,
            strategy_version INTEGER NOT NULL,
            previous_state TEXT NOT NULL,
            current_state TEXT NOT NULL,
            reason TEXT NOT NULL,
            evidence_ref TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    spec_json = json.dumps(
        {"adapter": "ema_trend_v1", "fixed": {}, "dataset": {}},
        sort_keys=True,
        separators=(",", ":"),
    )
    connection.execute(
        """
        INSERT INTO strategies(strategy_id, name, active_version)
        VALUES ('LEGACY', 'Legacy Strategy', 1)
        """
    )
    connection.execute(
        """
        INSERT INTO strategy_versions(
            strategy_id, version, lifecycle_state, spec_json, spec_sha256
        ) VALUES ('LEGACY', 1, ?, ?, 'legacy-sha')
        """,
        (state.value, spec_json),
    )
    connection.execute(
        """
        INSERT INTO lifecycle_history(
            strategy_id, strategy_version, previous_state, current_state,
            reason, evidence_ref
        ) VALUES ('LEGACY', 1, 'generated', ?, 'legacy transition', 'legacy:evidence')
        """,
        (state.value,),
    )
    connection.commit()
    connection.close()


def test_legacy_pre_oos_backtested_row_is_safely_migrated_to_v2(tmp_path: Path) -> None:
    path = tmp_path / "legacy-pre-oos.db"
    _write_legacy_db(path, state=StrategyLifecycle.BACKTESTED)

    store = ResearchStore(path)
    strategy = store.get_strategy_version("LEGACY", 1)

    assert strategy is not None
    assert strategy["lifecycle_state"] is StrategyLifecycle.BACKTESTED
    assert strategy["lifecycle_policy_version"] == CURRENT_LIFECYCLE_POLICY_VERSION
    with store._connection() as connection:
        old_history = connection.execute(
            "SELECT policy_version FROM lifecycle_history WHERE strategy_id = 'LEGACY'"
        ).fetchone()
        migration = connection.execute(
            """
            SELECT previous_version, current_version
            FROM lifecycle_policy_history
            WHERE strategy_id = 'LEGACY'
            """
        ).fetchone()
    assert old_history is not None
    assert old_history["policy_version"] == LEGACY_LIFECYCLE_POLICY_VERSION
    assert migration is not None
    assert migration["previous_version"] == LEGACY_LIFECYCLE_POLICY_VERSION
    assert migration["current_version"] == CURRENT_LIFECYCLE_POLICY_VERSION


def test_legacy_post_oos_row_is_frozen_until_explicit_retest(tmp_path: Path) -> None:
    path = tmp_path / "legacy-post-oos.db"
    _write_legacy_db(path, state=StrategyLifecycle.OOS_VERIFIED)

    store = ResearchStore(path)
    legacy = store.get_strategy_version("LEGACY", 1)
    assert legacy is not None
    assert legacy["lifecycle_policy_version"] == LEGACY_LIFECYCLE_POLICY_VERSION
    assert legacy["lifecycle_state"] is StrategyLifecycle.OOS_VERIFIED

    with pytest.raises(ValueError, match="not allowed under policy v1"):
        store.record_transition(
            strategy_id="LEGACY",
            strategy_version=1,
            current=StrategyLifecycle.ROBUSTNESS_VERIFIED,
            reason="Legacy path must not silently continue",
            evidence_ref="robustness:legacy",
        )

    store.record_transition(
        strategy_id="LEGACY",
        strategy_version=1,
        current=StrategyLifecycle.RETEST_REQUIRED,
        reason="Re-enter validation under lifecycle v2",
    )
    upgraded = store.upgrade_lifecycle_policy_v2(
        strategy_id="LEGACY",
        strategy_version=1,
        reason="Explicit retest migration after legacy OOS semantics",
    )
    assert upgraded["lifecycle_policy_version"] == CURRENT_LIFECYCLE_POLICY_VERSION
    assert upgraded["lifecycle_state"] is StrategyLifecycle.RETEST_REQUIRED

    store.record_transition(
        strategy_id="LEGACY",
        strategy_version=1,
        current=StrategyLifecycle.BACKTESTED,
        reason="Development evidence refreshed under v2",
        evidence_ref="development:v2",
    )
    refreshed = store.get_strategy_version("LEGACY", 1)
    assert refreshed is not None
    assert refreshed["lifecycle_state"] is StrategyLifecycle.BACKTESTED


def test_post_oos_legacy_row_cannot_upgrade_policy_in_place(tmp_path: Path) -> None:
    path = tmp_path / "legacy-no-retest.db"
    _write_legacy_db(path, state=StrategyLifecycle.ROBUSTNESS_VERIFIED)

    store = ResearchStore(path)
    with pytest.raises(RuntimeError, match="must enter RETEST_REQUIRED"):
        store.upgrade_lifecycle_policy_v2(
            strategy_id="LEGACY",
            strategy_version=1,
            reason="Unsafe direct migration",
        )
