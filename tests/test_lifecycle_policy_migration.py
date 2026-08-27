from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from eba_trader.lifecycle import (
    CURRENT_LIFECYCLE_POLICY_VERSION,
    LEGACY_LIFECYCLE_POLICY_VERSION,
    StrategyLifecycle,
)
from eba_trader.research_store import ResearchStore


def _legacy_db(path: Path) -> None:
    connection = sqlite3.connect(path)
    try:
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
                PRIMARY KEY(strategy_id, version),
                FOREIGN KEY(strategy_id) REFERENCES strategies(strategy_id)
                    ON DELETE CASCADE
            );

            CREATE TABLE lifecycle_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_id TEXT NOT NULL,
                strategy_version INTEGER NOT NULL,
                previous_state TEXT NOT NULL,
                current_state TEXT NOT NULL,
                reason TEXT NOT NULL,
                evidence_ref TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(strategy_id, strategy_version)
                    REFERENCES strategy_versions(strategy_id, version)
                    ON DELETE CASCADE
            );
            """
        )
        rows = (
            ("LEGACY-BT", "Legacy Backtested", "backtested"),
            ("LEGACY-OOS", "Legacy OOS", "oos_verified"),
        )
        for strategy_id, name, state in rows:
            connection.execute(
                "INSERT INTO strategies(strategy_id, name, active_version) VALUES (?, ?, 1)",
                (strategy_id, name),
            )
            connection.execute(
                """
                INSERT INTO strategy_versions(
                    strategy_id, version, lifecycle_state, spec_json, spec_sha256
                ) VALUES (?, 1, ?, '{}', ?)
                """,
                (strategy_id, state, f"sha-{strategy_id}"),
            )
        connection.execute(
            """
            INSERT INTO lifecycle_history(
                strategy_id, strategy_version, previous_state,
                current_state, reason, evidence_ref
            ) VALUES ('LEGACY-OOS', 1, 'backtested', 'oos_verified', 'legacy OOS', 'oos:legacy')
            """
        )
        connection.commit()
    finally:
        connection.close()


def test_pre_oos_legacy_row_migrates_safely_to_policy_v2(tmp_path: Path) -> None:
    path = tmp_path / "legacy.db"
    _legacy_db(path)

    store = ResearchStore(path)
    strategy = store.get_strategy_version("LEGACY-BT", 1)

    assert strategy is not None
    assert strategy["lifecycle_state"] is StrategyLifecycle.BACKTESTED
    assert strategy["lifecycle_policy_version"] == CURRENT_LIFECYCLE_POLICY_VERSION

    with pytest.raises(ValueError, match="not allowed under policy v2"):
        store.record_transition(
            strategy_id="LEGACY-BT",
            strategy_version=1,
            current=StrategyLifecycle.OOS_VERIFIED,
            reason="Trying to skip robustness after migration",
            evidence_ref="oos:too-early",
        )


def test_post_oos_legacy_row_remains_v1_and_promotion_is_frozen(tmp_path: Path) -> None:
    path = tmp_path / "legacy.db"
    _legacy_db(path)

    store = ResearchStore(path)
    strategy = store.get_strategy_version("LEGACY-OOS", 1)

    assert strategy is not None
    assert strategy["lifecycle_state"] is StrategyLifecycle.OOS_VERIFIED
    assert strategy["lifecycle_policy_version"] == LEGACY_LIFECYCLE_POLICY_VERSION

    with pytest.raises(ValueError, match="not allowed under policy v1"):
        store.record_transition(
            strategy_id="LEGACY-OOS",
            strategy_version=1,
            current=StrategyLifecycle.ROBUSTNESS_VERIFIED,
            reason="Legacy path must not keep promoting",
            evidence_ref="robustness:legacy",
        )


def test_legacy_post_oos_requires_retest_before_v2_reentry(tmp_path: Path) -> None:
    path = tmp_path / "legacy.db"
    _legacy_db(path)
    store = ResearchStore(path)

    with pytest.raises(RuntimeError, match="must enter RETEST_REQUIRED"):
        store.upgrade_lifecycle_policy_v2(
            strategy_id="LEGACY-OOS",
            strategy_version=1,
            reason="unsafe direct upgrade",
        )

    store.record_transition(
        strategy_id="LEGACY-OOS",
        strategy_version=1,
        current=StrategyLifecycle.RETEST_REQUIRED,
        reason="Legacy OOS evidence predates robustness-first policy",
        evidence_ref="migration:retest-required",
    )
    migrated = store.upgrade_lifecycle_policy_v2(
        strategy_id="LEGACY-OOS",
        strategy_version=1,
        reason="Re-enter under robustness-first lifecycle",
    )
    assert migrated["lifecycle_state"] is StrategyLifecycle.RETEST_REQUIRED
    assert migrated["lifecycle_policy_version"] == CURRENT_LIFECYCLE_POLICY_VERSION

    store.record_transition(
        strategy_id="LEGACY-OOS",
        strategy_version=1,
        current=StrategyLifecycle.BACKTESTED,
        reason="Fresh development evidence passed",
        evidence_ref="development:retest-pass",
    )
    strategy = store.get_strategy_version("LEGACY-OOS", 1)
    assert strategy is not None
    assert strategy["lifecycle_state"] is StrategyLifecycle.BACKTESTED

    with pytest.raises(ValueError, match="not allowed under policy v2"):
        store.record_transition(
            strategy_id="LEGACY-OOS",
            strategy_version=1,
            current=StrategyLifecycle.OOS_VERIFIED,
            reason="OOS still cannot open before fresh robustness",
            evidence_ref="oos:still-too-early",
        )


def test_existing_legacy_history_rows_are_marked_policy_v1(tmp_path: Path) -> None:
    path = tmp_path / "legacy.db"
    _legacy_db(path)
    ResearchStore(path)

    connection = sqlite3.connect(path)
    try:
        row = connection.execute(
            """
            SELECT policy_version
            FROM lifecycle_history
            WHERE strategy_id = 'LEGACY-OOS'
            ORDER BY id
            LIMIT 1
            """
        ).fetchone()
    finally:
        connection.close()

    assert row is not None
    assert row[0] == LEGACY_LIFECYCLE_POLICY_VERSION
