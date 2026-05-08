"""Deterministic risk engine for driver behaviour scoring and classification."""


class DriverRiskEngine:
    """Build deterministic risk outputs from normalized journey behaviour rows.

    The risk engine is the single source of truth for:
    - behaviour breakdown computation
    - weighted risk scoring
    - risk level classification
    - confidence scoring
    - primary concern derivation
    - risk profile construction
    """

    RISK_MODEL_VERSION = "v1"

    BEHAVIOUR_WEIGHTS = {
        "dsm_fatigue": 5,
        "dsm_distraction": 4,
        "dsm_handheld_device": 4,
        "adas_events": 3,
        "dsm_seatbelt": 2,
        "dsm_smoking": 2,
    }

    _NORMALIZED_BEHAVIOUR_FIELDS = {
        "dsm_fatigue": "dsmFatigueCount",
        "dsm_distraction": "dsmDistractionCount",
        "dsm_handheld_device": "dsmHandheldDevicesCount",
        "adas_events": "adasEventsCount",
        "dsm_seatbelt": "dsmSeatbeltCount",
        "dsm_smoking": "dsmSmokingCount",
    }

    _PRIMARY_CONCERN_LABELS = {
        "dsm_fatigue": "fatigue",
        "dsm_distraction": "distraction",
        "dsm_handheld_device": "handheld_device",
        "adas_events": "adas",
        "dsm_seatbelt": "seatbelt",
        "dsm_smoking": "smoking",
    }

    @staticmethod
    def _safe_non_negative_int(value) -> int:
        """Return non-negative integer from mixed numeric inputs."""

        try:
            return max(0, int(value or 0))
        except (TypeError, ValueError):
            return 0

    @classmethod
    def compute_behaviour_breakdown(cls, normalized_data: list[dict]) -> dict:
        """Return behavior breakdown with raw counts and journey presence counts.

        `journey_presence_count` is computed as the number of journeys where the
        per-journey event counter for the behavior is strictly greater than zero.
        """

        breakdown = {
            behavior_key: {
                "raw_event_count": 0,
                "journey_presence_count": 0,
            }
            for behavior_key in cls.BEHAVIOUR_WEIGHTS
        }

        for row in normalized_data:
            if not isinstance(row, dict):
                continue

            for behavior_key, field_name in cls._NORMALIZED_BEHAVIOUR_FIELDS.items():
                event_count = cls._safe_non_negative_int(row.get(field_name, 0))
                breakdown_entry = breakdown[behavior_key]
                breakdown_entry["raw_event_count"] += event_count

                if event_count > 0:
                    breakdown_entry["journey_presence_count"] += 1

        return breakdown

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
            behavior_metrics = behaviour_breakdown.get(behavior_key, {}) if isinstance(behaviour_breakdown, dict) else {}
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
            behavior_metrics = behaviour_breakdown.get(behavior_key, {}) if isinstance(behaviour_breakdown, dict) else {}
            raw_event_count = cls._safe_non_negative_int(behavior_metrics.get("raw_event_count", 0))
            contributions[behavior_key] = float(raw_event_count * weight)

        return contributions

    @classmethod
    def compute_confidence(cls, journey_count: int, behaviour_breakdown: dict) -> str:
        """Return deterministic confidence from signal diversity and concentration.

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
            (
                (behavior_key, contribution)
                for behavior_key, contribution in contributions.items()
                if contribution > 0
            ),
            key=lambda item: (-item[1], item[0]),
        )

        return [cls._PRIMARY_CONCERN_LABELS.get(behavior_key, behavior_key) for behavior_key, _ in ranked[:3]]

    @classmethod
    def build_risk_profile(cls, normalized_data: list[dict]) -> dict:
        """Return deterministic risk profile from normalized journey rows."""

        journey_count = len(normalized_data) if isinstance(normalized_data, list) else 0
        behaviour_breakdown = cls.compute_behaviour_breakdown(normalized_data if isinstance(normalized_data, list) else [])
        risk_score = cls.calculate_weighted_risk_score(behaviour_breakdown, journey_count)
        risk_level = cls.classify_risk_level(risk_score)
        confidence = cls.compute_confidence(journey_count, behaviour_breakdown)
        primary_concerns = cls.derive_primary_concerns(behaviour_breakdown)

        return {
            "model_version": cls.RISK_MODEL_VERSION,
            "risk_level": risk_level,
            "risk_score": risk_score,
            "confidence": confidence,
            "primary_concerns": primary_concerns,
            "requires_intervention": risk_level == "high",
        }