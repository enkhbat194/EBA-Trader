from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .research_evidence import canonical_json, sha256_text
from .strategy_discovery_v2 import DISCOVERY_AUTHORITY, DiscoveryTrialLedger

CONFIRMATION_ZONE = "D1"
FROZEN_OOS_ZONE = "D3"


@dataclass(frozen=True, slots=True)
class HiddenConfirmationFreeze:
    freeze_id: str
    campaign_id: str
    selection_id: str
    candidate_ids: tuple[str, ...]
    discovery_dataset_sha256s: tuple[str, ...]
    definition_sha256: str
    definition: Mapping[str, Any]


class HiddenConfirmationFreezeStore:
    """Persist the one-way D0-survivor freeze without granting authority to open D1."""

    def __init__(self, ledger: DiscoveryTrialLedger) -> None:
        self.ledger = ledger
        self.store = ledger.store
        self._initialize()

    def _initialize(self) -> None:
        with self.store._connection() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS discovery_confirmation_freezes_v2 (
                    freeze_id TEXT PRIMARY KEY,
                    campaign_id TEXT NOT NULL UNIQUE,
                    selection_id TEXT NOT NULL,
                    definition_sha256 TEXT NOT NULL,
                    definition_json TEXT NOT NULL,
                    state TEXT NOT NULL CHECK(state = 'SEALED'),
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(campaign_id) REFERENCES discovery_campaigns_v2(campaign_id)
                        ON DELETE RESTRICT,
                    FOREIGN KEY(selection_id)
                        REFERENCES discovery_survivor_selections_v2(selection_id)
                        ON DELETE RESTRICT
                );
                """
            )

    def freeze(
        self,
        *,
        campaign_id: str,
        execution_contract: Mapping[str, object],
        universe_contract: Mapping[str, object],
        feature_contract: Mapping[str, object],
    ) -> HiddenConfirmationFreeze:
        selection = self.ledger.get_survivor_selection(campaign_id)
        if selection is None:
            raise RuntimeError("hidden confirmation cannot be frozen before survivor selection")
        candidate_ids = tuple(selection["candidate_ids"])
        candidates = {
            row["candidate_id"]: row for row in self.ledger.list_candidates(campaign_id)
        }
        missing = sorted(set(candidate_ids) - set(candidates))
        if missing:
            raise RuntimeError("survivor selection references missing discovery candidates")
        trials = self.ledger.list_trials(campaign_id)
        discovery_datasets = tuple(sorted({str(row["dataset_sha256"]) for row in trials}))
        if not discovery_datasets:
            raise RuntimeError("hidden confirmation freeze requires recorded D0 evaluation data")

        candidate_contract = [
            {
                "candidate_id": candidate_id,
                "candidate_spec_sha256": candidates[candidate_id]["candidate_spec_sha256"],
                "source_code_sha": candidates[candidate_id]["source_code_sha"],
            }
            for candidate_id in candidate_ids
        ]
        definition: dict[str, object] = {
            "authority": DISCOVERY_AUTHORITY,
            "campaign_id": campaign_id,
            "candidate_contract": candidate_contract,
            "candidate_ids": list(candidate_ids),
            "confirmation_zone": CONFIRMATION_ZONE,
            "d1_opened": False,
            "discovery_dataset_sha256s": list(discovery_datasets),
            "execution_contract": dict(execution_contract),
            "feature_contract": dict(feature_contract),
            "frozen_oos_allowed": False,
            "frozen_oos_zone": FROZEN_OOS_ZONE,
            "selection_definition_sha256": selection["definition_sha256"],
            "selection_id": selection["selection_id"],
            "universe_contract": dict(universe_contract),
        }
        definition_json = canonical_json(definition)
        definition_sha256 = sha256_text(definition_json)
        freeze_id = f"dfreeze_{definition_sha256[:24]}"

        with self.store._connection() as connection:
            existing = connection.execute(
                """
                SELECT * FROM discovery_confirmation_freezes_v2
                WHERE campaign_id = ?
                """,
                (campaign_id,),
            ).fetchone()
            if existing is not None:
                if existing["definition_sha256"] != definition_sha256:
                    raise RuntimeError("hidden confirmation freeze is immutable")
                return self._row(existing)
            connection.execute(
                """
                INSERT INTO discovery_confirmation_freezes_v2(
                    freeze_id, campaign_id, selection_id,
                    definition_sha256, definition_json, state
                ) VALUES (?, ?, ?, ?, ?, 'SEALED')
                """,
                (
                    freeze_id,
                    campaign_id,
                    selection["selection_id"],
                    definition_sha256,
                    definition_json,
                ),
            )

        stored = self.get(campaign_id)
        if stored is None:  # pragma: no cover - defensive invariant
            raise RuntimeError("hidden confirmation freeze could not be reloaded")
        return stored

    def get(self, campaign_id: str) -> HiddenConfirmationFreeze | None:
        with self.store._connection() as connection:
            row = connection.execute(
                """
                SELECT * FROM discovery_confirmation_freezes_v2
                WHERE campaign_id = ?
                """,
                (campaign_id,),
            ).fetchone()
        return self._row(row) if row is not None else None

    @staticmethod
    def assert_unseen_confirmation_dataset(
        freeze: HiddenConfirmationFreeze,
        dataset_sha256: str,
    ) -> None:
        dataset_sha256 = dataset_sha256.strip()
        if not dataset_sha256:
            raise ValueError("confirmation dataset SHA is required")
        if dataset_sha256 in set(freeze.discovery_dataset_sha256s):
            raise ValueError("D1 confirmation dataset was already consumed by D0 discovery")

    @staticmethod
    def _row(row: Mapping[str, Any]) -> HiddenConfirmationFreeze:
        definition = json.loads(str(row["definition_json"]))
        if definition.get("d1_opened") is not False:
            raise RuntimeError("stored hidden confirmation freeze must remain sealed")
        if definition.get("frozen_oos_allowed") is not False:
            raise RuntimeError("stored hidden confirmation freeze cannot authorize Frozen OOS")
        return HiddenConfirmationFreeze(
            freeze_id=str(row["freeze_id"]),
            campaign_id=str(row["campaign_id"]),
            selection_id=str(row["selection_id"]),
            candidate_ids=tuple(str(item) for item in definition["candidate_ids"]),
            discovery_dataset_sha256s=tuple(
                str(item) for item in definition["discovery_dataset_sha256s"]
            ),
            definition_sha256=str(row["definition_sha256"]),
            definition=definition,
        )
