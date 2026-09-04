from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .sfv2_next_d0_service_state import read_sfv2_next_d0_service_state
from .strategy_factory_v2_next_materialization import (
    AUTHORITY,
    CAMPAIGN_ID,
    EXPECTED_CATALOG_SHA256,
    EXPECTED_PLAN_SHA256,
    EXPECTED_WINDOW_COUNT,
    REQUEST_ID,
    STATUS_SCHEMA,
)

DEFAULT_STATUS_PATH = Path(
    "/var/lib/eba-trader/research/sfv2-next-d0-materialization-status.json"
)


def _unavailable(reason: str) -> dict[str, Any]:
    return {
        "available": False,
        "reason": reason,
        "authority": AUTHORITY,
        "campaignId": CAMPAIGN_ID,
        "expectedWindowCount": EXPECTED_WINDOW_COUNT,
        "serviceState": read_sfv2_next_d0_service_state(),
        "performanceEvaluationAllowed": False,
        "freshConfirmationEvidence": False,
        "verificationAuthority": False,
        "d1Opened": False,
        "frozenOosOpened": False,
        "sf4DataAccessAllowed": False,
        "liveExecutionAllowed": False,
        "realExecutionAllowed": False,
    }


def read_sfv2_next_d0_materialization_summary(
    path: str | Path | None = None,
) -> dict[str, Any]:
    selected = Path(
        path
        or os.getenv("EBA_SFV2_NEXT_D0_STATUS", "").strip()
        or DEFAULT_STATUS_PATH
    )
    if not selected.is_file():
        return _unavailable("status_unavailable")
    try:
        payload = json.loads(selected.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _unavailable("status_invalid")
    if not isinstance(payload, dict):
        return _unavailable("status_invalid")
    safety = (
        payload.get("schema") == STATUS_SCHEMA
        and payload.get("requestId") == REQUEST_ID
        and payload.get("authority") == AUTHORITY
        and payload.get("campaignId") == CAMPAIGN_ID
        and payload.get("datasetPlanSha256") == EXPECTED_PLAN_SHA256
        and payload.get("catalogSha256") == EXPECTED_CATALOG_SHA256
        and payload.get("expectedWindowCount") == EXPECTED_WINDOW_COUNT
        and payload.get("performanceEvaluationAllowed") is False
        and payload.get("freshConfirmationEvidence") is False
        and payload.get("verificationAuthority") is False
        and payload.get("d1Opened") is False
        and payload.get("frozenOosOpened") is False
        and payload.get("sf4DataAccessAllowed") is False
        and payload.get("demoPromotionAllowed") is False
        and payload.get("liveExecutionAllowed") is False
        and payload.get("realExecutionAllowed") is False
    )
    if not safety:
        return _unavailable("status_safety_rejected")
    receipts = payload.get("receipts")
    if not isinstance(receipts, list):
        return _unavailable("receipts_invalid")
    completed = payload.get("completedWindowCount")
    if isinstance(completed, bool) or not isinstance(completed, int):
        return _unavailable("completed_count_invalid")
    if completed != len(receipts) or not 0 <= completed <= EXPECTED_WINDOW_COUNT:
        return _unavailable("completed_count_mismatch")
    complete = payload.get("phase") == "COMPLETE"
    bundle_sha = payload.get("datasetBundleSha256")
    if complete and (not isinstance(bundle_sha, str) or len(bundle_sha) != 64):
        return _unavailable("complete_bundle_sha_invalid")
    return {
        "available": True,
        "phase": "COMPLETE" if complete else "IN_PROGRESS",
        "authority": AUTHORITY,
        "campaignId": CAMPAIGN_ID,
        "sourceCodeSha": payload.get("sourceCodeSha"),
        "datasetPlanSha256": EXPECTED_PLAN_SHA256,
        "catalogSha256": EXPECTED_CATALOG_SHA256,
        "expectedWindowCount": EXPECTED_WINDOW_COUNT,
        "completedWindowCount": completed,
        "nextWindowName": payload.get("nextWindowName"),
        "datasetBundleSha256": bundle_sha if complete else None,
        "serviceState": read_sfv2_next_d0_service_state(),
        "performanceEvaluationAllowed": False,
        "freshConfirmationEvidence": False,
        "verificationAuthority": False,
        "d1Opened": False,
        "frozenOosOpened": False,
        "sf4DataAccessAllowed": False,
        "liveExecutionAllowed": False,
        "realExecutionAllowed": False,
    }
