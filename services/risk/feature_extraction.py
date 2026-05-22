"""Deterministic feature extraction for Behavioural Risk Engine v2."""

from __future__ import annotations

from services.risk.behaviour_registry import get_behaviour_definitions
from services.risk.models import BehaviourMetrics, RiskFeatures


HIGH_SEVERITY_EVENT_THRESHOLD = 5


def _safe_non_negative_int(value: object) -> int:
    """Safely coerce mixed input to non-negative int for risk feature extraction."""

    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def extract_risk_features(normalized_data: list[dict]) -> RiskFeatures:
    """Extract deterministic per-behaviour and global features from normalized journey rows.

    Args:
        normalized_data: Normalized journey rows used as deterministic engine input.

    Returns:
        Typed RiskFeatures payload with per-behaviour metrics and global counters.
    """

    definitions = get_behaviour_definitions()
    journey_count = 0
    high_severity_journey_count = 0
    interim = {
        key: {
            "raw_event_count": 0,
            "journey_presence_count": 0,
            "max_single_journey_events": 0,
            "weighted_score": 0.0,
        }
        for key in definitions
    }

    for row in normalized_data or []:
        if not isinstance(row, dict):
            continue

        journey_count += 1
        journey_severity_max = 0

        for behaviour_key, definition in definitions.items():
            source_field = definition["source_field"]
            severity_weight = float(definition["severity_weight"])
            event_count = _safe_non_negative_int(row.get(source_field, 0))

            bucket = interim[behaviour_key]
            bucket["raw_event_count"] += event_count
            bucket["weighted_score"] += float(event_count * severity_weight)

            if event_count > 0:
                bucket["journey_presence_count"] += 1

            if event_count > bucket["max_single_journey_events"]:
                bucket["max_single_journey_events"] = event_count

            if event_count > journey_severity_max:
                journey_severity_max = event_count

        if journey_severity_max >= HIGH_SEVERITY_EVENT_THRESHOLD:
            high_severity_journey_count += 1

    behaviour_metrics = {}
    active_behaviour_count = 0
    denominator = max(journey_count, 1)

    for behaviour_key, values in interim.items():
        journey_presence_count = int(values["journey_presence_count"])
        journey_ratio = float(journey_presence_count / denominator) if journey_count else 0.0

        if values["raw_event_count"] > 0:
            active_behaviour_count += 1

        behaviour_metrics[behaviour_key] = BehaviourMetrics(
            raw_event_count=int(values["raw_event_count"]),
            journey_presence_count=journey_presence_count,
            journey_ratio=journey_ratio,
            max_single_journey_events=int(values["max_single_journey_events"]),
            weighted_score=float(values["weighted_score"]),
        )

    return RiskFeatures(
        journey_count=journey_count,
        active_behaviour_count=active_behaviour_count,
        high_severity_journey_count=high_severity_journey_count,
        behaviour_metrics=behaviour_metrics,
    )
