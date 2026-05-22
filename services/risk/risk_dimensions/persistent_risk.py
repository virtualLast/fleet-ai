"""Deterministic persistent-risk evaluator for Behavioural Risk Engine v2."""

from __future__ import annotations

from services.risk.models import RiskFeatures


def evaluate_persistent_risk(features: RiskFeatures) -> dict:
    """Evaluate repeated cross-journey behavioural risk with severity weighting.

    Args:
        features: Extracted `RiskFeatures` payload. `journey_count` is treated as
            at least 1 for safe division; behaviours with zero journey presence
            are ignored for persistent contribution scoring.

    Returns:
        Dictionary with keys:
        - `level`: `low`/`medium`/`high`
        - `score`: deterministic persistent score
        - `contributors`: ranked behaviour contributors
        - `triggered`: whether persistent dimension should trigger intervention/escalation

    Side effects:
        None.

    Raises:
        Expects valid numeric fields in `features.behaviour_metrics`; malformed
        values may raise runtime exceptions.
    """

    journey_count = max(int(features.journey_count or 0), 1)
    weighted_ratio_sum = 0.0
    contributors = []

    for behaviour_key, metrics in features.behaviour_metrics.items():
        if metrics.journey_presence_count <= 0:
            continue

        ratio = float(metrics.journey_ratio)
        weighted_component = float(metrics.weighted_score / journey_count)
        weighted_ratio_sum += weighted_component

        contributors.append(
            {
                "behaviour": behaviour_key,
                "journey_ratio": ratio,
                "weighted_component": round(weighted_component, 4),
            }
        )

    score = round(weighted_ratio_sum, 4)

    if score >= 5.0:
        level = "high"
    elif score >= 2.0:
        level = "medium"
    else:
        level = "low"

    contributors.sort(key=lambda item: item["weighted_component"], reverse=True)

    return {
        "level": level,
        "score": score,
        "contributors": contributors[:5],
        "triggered": level in {"medium", "high"},
    }
