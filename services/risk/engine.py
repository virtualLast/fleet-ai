"""Risk engine orchestration for Behavioural Risk Engine v2."""

from __future__ import annotations

from services.risk.classification import classify_risk_assessment
from services.risk.feature_extraction import extract_risk_features
from services.risk.risk_dimensions.acute_risk import evaluate_acute_risk
from services.risk.risk_dimensions.breadth_risk import evaluate_breadth_risk
from services.risk.risk_dimensions.persistent_risk import evaluate_persistent_risk


class RiskEngine:
    """Orchestrate feature extraction, risk dimensions, and final classification."""

    RISK_MODEL_VERSION = "v2"

    @classmethod
    def build_assessment(cls, normalized_data: list[dict]):
        """Build deterministic risk assessment from normalized journey rows.

        Args:
            normalized_data: List of normalized journey dictionaries. Each row is
                expected to provide behavior counters aligned with the registry
                source fields (for example `adasFcwCount`, `dsmFatigueCount`).

        Returns:
            `RiskAssessment` generated via deterministic orchestration:
            feature extraction -> persistent/acute/breadth dimensions ->
            rule-based classification.

        Side effects:
            None.

        Raises:
            Propagates exceptions from extraction/dimension/classification layers
            if malformed input causes downstream failures.
        """

        features = extract_risk_features(normalized_data)
        persistent_risk = evaluate_persistent_risk(features)
        acute_risk = evaluate_acute_risk(features)
        breadth_risk = evaluate_breadth_risk(features)

        return classify_risk_assessment(
            model_version=cls.RISK_MODEL_VERSION,
            features=features,
            persistent_risk=persistent_risk,
            acute_risk=acute_risk,
            breadth_risk=breadth_risk,
        )
