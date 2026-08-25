from __future__ import annotations

from dataclasses import dataclass

from .m5_hypothesis import StrategyHypothesis


@dataclass(frozen=True, slots=True)
class SimilarityResult:
    left_fingerprint: str
    right_fingerprint: str
    score: float
    near_duplicate: bool


def hypothesis_similarity(
    left: StrategyHypothesis,
    right: StrategyHypothesis,
    *,
    threshold: float = 0.85,
) -> SimilarityResult:
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("threshold must be between 0 and 1")
    left.validate()
    right.validate()

    if (
        left.direction is not right.direction
        or left.timeframe != right.timeframe
        or left.family != right.family
    ):
        score = 0.0
    else:
        left_tokens = _tokens(left)
        right_tokens = _tokens(right)
        union = left_tokens | right_tokens
        score = len(left_tokens & right_tokens) / len(union) if union else 1.0

    return SimilarityResult(
        left_fingerprint=left.fingerprint,
        right_fingerprint=right.fingerprint,
        score=score,
        near_duplicate=score >= threshold,
    )


def remove_near_duplicates(
    hypotheses: tuple[StrategyHypothesis, ...],
    *,
    threshold: float = 0.85,
) -> tuple[StrategyHypothesis, ...]:
    kept: list[StrategyHypothesis] = []
    for hypothesis in hypotheses:
        hypothesis.validate()
        if any(
            hypothesis_similarity(hypothesis, existing, threshold=threshold).near_duplicate
            for existing in kept
        ):
            continue
        kept.append(hypothesis)
    return tuple(kept)


def _tokens(hypothesis: StrategyHypothesis) -> set[str]:
    tokens = {f"feature:{name}" for name in hypothesis.features}
    for prefix, conditions in (
        ("entry", hypothesis.entry_all),
        ("exit", hypothesis.exit_all),
    ):
        tokens.update(
            f"{prefix}:{condition.feature}:{condition.operator.value}"
            for condition in conditions
        )
    return tokens
