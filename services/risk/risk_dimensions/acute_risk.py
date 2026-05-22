"""Deterministic acute-risk evaluator for Behavioural Risk Engine v2."""

from __future__ import annotations

from services.risk.models import RiskFeatures


def evaluate_acute_risk(features: RiskFeatures) -> dict:
    """Evaluate single-journey and intra-journey severity risk signals.

    Args:
        features: Extracted `RiskFeatures` payload containing behaviour metrics
            with `max_single_journey_events` and `weighted_score`.

    Returns:
        Dictionary with keys:
        - `level`: `low`/`medium`/`high`
        - `score`: deterministic acute score
        - `contributors`: ranked acute behaviour contributors
        - `triggered`: whether acute dimension triggers intervention/escalation
        - `hard_override`: whether acute dimension should hard-override final class

    Side effects:
        None.

    Raises:
        Expects valid numeric fields in behaviour metrics; malformed values may
        raise runtime exceptions.
    """

    score = 0.0
    contributors = []

    for behaviour_key, metrics in features.behaviour_metrics.items():
        peak = int(metrics.max_single_journey_events)
        if peak <= 0:
            continue

        component = float(peak * 0.6) + float(metrics.weighted_score / max(features.journey_count or 1, 1) * 0.2)
        score += component

        contributors.append(
            {
                "behaviour": behaviour_key,
                "max_single_journey_events": peak,
                "acute_component": round(component, 4),
            }
        )

    score = round(score, 4)

    if score >= 10.0:
        level = "high"
    elif score >= 4.0:
        level = "medium"
    else:
        level = "low"

    contributors.sort(key=lambda item: item["acute_component"], reverse=True)

    return {
        "level": level,
        "score": score,
        "contributors": contributors[:5],
        "triggered": level in {"medium", "high"},
        "hard_override": level == "high",
    }
