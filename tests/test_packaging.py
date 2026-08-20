from __future__ import annotations

import tomllib
from pathlib import Path


def test_public_commands_expose_only_the_authoritative_oos_workflow() -> None:
    project = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))["project"]
    scripts = project["scripts"]

    assert scripts["eba-development-verdict"] == "eba_trader.verdict:development_verdict_cli"
    assert scripts["eba-risk-execution-study"] == "eba_trader.risk_evidence:main"
    assert scripts["eba-risk-execution-verdict"] == "eba_trader.risk_verdict:main"
    assert scripts["eba-final-freeze"] == "eba_trader.final_freeze:main"
    assert scripts["eba-final-oos"] == "eba_trader.final_oos:main"
    assert scripts["eba-final-oos-verdict"] == "eba_trader.final_oos_verdict:main"

    assert "eba-freeze-oos-candidate" not in scripts
    assert "eba-oos-study" not in scripts
