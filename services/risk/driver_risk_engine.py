"""Compatibility facade over Behavioural Risk Engine v2 deterministic modules."""

from typing import Any

from services.risk.behaviour_registry import get_behaviour_definitions
from services.risk.engine import RiskEngine
from services.risk.feature_extraction import extract_risk_features


class DriverRiskEngine:
    """Expose legacy driver-risk API while delegating deterministic truth to v2 engine."""

    RISK_MODEL_VERSION = RiskEngine.RISK_MODEL_VERSION

    BEHAVIOUR_WEIGHTS = {key: definition["severity_weight"] for key, definition in get_behaviour_definitions().items()}

    _NORMALIZED_BEHAVIOUR_FIELDS = {
        key: definition["source_field"] for key, definition in get_behaviour_definitions().items()
    }

    _PRIMARY_CONCERN_LABELS = {
        "dsm_fatigue": "fatigue",
        "dsm_distraction": "distraction",
        "dsm_handheld_devices": "handheld_device",
        "dsm_seatbelt": "seatbelt",
        "dsm_smoking": "smoking",
        "dsm_no_driver": "no_driver",
        "dsm_yawning": "yawning",
        "adas_fcw": "adas_fcw",
        "adas_hmw": "adas_hmw",
        "adas_pcw": "adas_pcw",
    }

    @staticmethod
    def _safe_non_negative_int(value: Any) -> int:
        """Return non-negative integer from mixed numeric inputs."""

        try:
            return max(0, int(value or 0))
        except (TypeError, ValueError):
            return 0

    @classmethod
    def compute_behaviour_breakdown(cls, normalized_data: list[dict]) -> dict:
        """Return legacy-compatible behaviour breakdown derived from deterministic v2 features.

        Args:
            normalized_data: Normalized journey rows used to compute behaviour metrics.

        Returns:
            Mapping of behaviour key to metric dictionary containing:
            - `raw_event_count`: total observed events for the behaviour.
            - `journey_presence_count`: count of journeys where behaviour appeared.
        """

        features = extract_risk_features(normalized_data if isinstance(normalized_data, list) else [])
        return {
            behavior_key: {
                "raw_event_count": metrics.raw_event_count,
                "journey_presence_count": metrics.journey_presence_count,
            }
            for behavior_key, metrics in features.behaviour_metrics.items()
        }

    @classmethod
    def calculate_weighted_risk_score(cls, behaviour_breakdown: dict, journey_count: int) -> float:
        """Return repetition-safe weighted risk score.

        Formula:
        weighted_event_sum = Σ(min(event_count_per_journey, 1) * weight)
        risk_score = weighted_event_sum / max(journey_count, 1)

        Given pre-aggregated inputs, `journey_presence_count` represents
        Σ(min(event_count_per_journey, 1)) for each behavior.
        """

        denominator = max(cls._safe_non_negative_int(journey_count), 1)
        weighted_event_sum = 0.0

        for behavior_key, weight in cls.BEHAVIOUR_WEIGHTS.items():
            behavior_metrics = (
                behaviour_breakdown.get(behavior_key, {}) if isinstance(behaviour_breakdown, dict) else {}
            )
            journey_presence_count = cls._safe_non_negative_int(behavior_metrics.get("journey_presence_count", 0))
            weighted_event_sum += float(journey_presence_count * weight)

        return float(weighted_event_sum / denominator)

    @staticmethod
    def classify_risk_level(risk_score: float) -> str:
        """Map weighted risk score to fixed deterministic risk bands."""

        try:
            score = float(risk_score)
        except (TypeError, ValueError):
            score = 0.0

        if score < 1.0:
            return "low"
        if score < 3.0:
            return "medium"

        return "high"

    @classmethod
    def _weighted_contributions(cls, behaviour_breakdown: dict) -> dict:
        """Return per-behavior weighted contributions using raw event counts.

        Raw event counts are reporting-only and must never be used for risk score;
        they are used here solely for contribution distribution and concern ranking.
        """

        contributions = {}

        for behavior_key, weight in cls.BEHAVIOUR_WEIGHTS.items():
            behavior_metrics = (
                behaviour_breakdown.get(behavior_key, {}) if isinstance(behaviour_breakdown, dict) else {}
            )
            raw_event_count = cls._safe_non_negative_int(behavior_metrics.get("raw_event_count", 0))
            contributions[behavior_key] = float(raw_event_count * weight)

        return contributions

    @classmethod
    def compute_assessment_confidence(cls, journey_count: int, behaviour_breakdown: dict) -> str:
        """Return deterministic assessment confidence from signal diversity and concentration.

        Dominance rule:
        A category is dominant when
        `weighted_contribution >= 0.9 * total_weighted_contribution`.
        """

        _ = cls._safe_non_negative_int(journey_count)  # kept for explicit signature usage.
        contributions = cls._weighted_contributions(behaviour_breakdown)
        non_zero_contributions = [value for value in contributions.values() if value > 0]

        if len(non_zero_contributions) <= 1:
            return "low"

        total_weighted_contribution = sum(non_zero_contributions)

        if total_weighted_contribution <= 0:
            return "low"

        is_dominant = any(value >= 0.9 * total_weighted_contribution for value in non_zero_contributions)

        if is_dominant:
            return "low"

        category_count = len(non_zero_contributions)

        if 2 <= category_count <= 3:
            return "medium"

        return "high"

    @classmethod
    def derive_primary_concerns(cls, behaviour_breakdown: dict) -> list[str]:
        """Return top deterministic concern labels ranked by weighted impact.

        Concern ranking uses weighted contribution (`raw_event_count * weight`) and
        returns at most three concerns in deterministic order.
        """

        contributions = cls._weighted_contributions(behaviour_breakdown)
        ranked = sorted(
            ((behavior_key, contribution) for behavior_key, contribution in contributions.items() if contribution > 0),
            key=lambda item: (-item[1], item[0]),
        )

        return [cls._PRIMARY_CONCERN_LABELS.get(behavior_key, behavior_key) for behavior_key, _ in ranked[:3]]

    @classmethod
    def build_risk_profile(cls, normalized_data: list[dict]) -> dict:
        """Return legacy-compatible risk profile from v2 deterministic assessment."""

        assessment = RiskEngine.build_assessment(normalized_data if isinstance(normalized_data, list) else [])
        primary_concerns = [
            cls._PRIMARY_CONCERN_LABELS.get(concern, concern) for concern in (assessment.primary_concerns or [])
        ]
        return {
            "model_version": assessment.model_version,
            "risk_level": assessment.overall_risk_level,
            "risk_score": assessment.overall_risk_score,
            "assessment_confidence": assessment.assessment_confidence,
            "primary_concerns": primary_concerns,
            "requires_intervention": assessment.requires_intervention,
            "dimensions": assessment.dimensions,
            "explainability": assessment.explainability,
            "intervention": assessment.intervention,
        }
