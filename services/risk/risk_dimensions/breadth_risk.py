"""Deterministic breadth-risk evaluator for Behavioural Risk Engine v2."""

from __future__ import annotations

from services.risk.behaviour_registry import get_behaviour_definitions
from services.risk.models import RiskFeatures


def evaluate_breadth_risk(features: RiskFeatures) -> dict:
    """Evaluate weighted diversity of active risky behaviours.

    Breadth is an escalation signal only and must not be the primary classifier.

    Args:
        features: Extracted `RiskFeatures` payload used to determine which
            behaviours are active (`raw_event_count > 0`).

    Returns:
        Dictionary with keys:
        - `level`: `low`/`medium`/`high`
        - `score`: weighted active-behaviour diversity score
        - `contributors`: ranked active behaviour contributors
        - `triggered`: whether breadth should participate in escalation logic
        - `escalation_only`: always `True` by contract

    Side effects:
        None.

    Raises:
        Expects registry metadata to include `severity_weight` for behaviour
        keys; malformed structures may raise runtime exceptions.
    """

    definitions = get_behaviour_definitions()
    active_weight_sum = 0.0
    contributors = []

    for behaviour_key, metrics in features.behaviour_metrics.items():
        if metrics.raw_event_count <= 0:
            continue

        weight = float(definitions.get(behaviour_key, {}).get("severity_weight", 0.0))
        active_weight_sum += weight
        contributors.append(
            {
                "behaviour": behaviour_key,
                "weight": weight,
                "raw_event_count": int(metrics.raw_event_count),
            }
        )

    if active_weight_sum >= 18.0:
        level = "high"
    elif active_weight_sum >= 8.0:
        level = "medium"
    else:
        level = "low"

    contributors.sort(key=lambda item: item["weight"], reverse=True)

    return {
        "level": level,
        "score": round(active_weight_sum, 4),
        "contributors": contributors[:6],
        "triggered": level in {"medium", "high"},
        "escalation_only": True,
    }
