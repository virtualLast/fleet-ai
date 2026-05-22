from services.risk.classification import classify_risk_assessment
from services.risk.models import RiskFeatures


def test_classification_applies_acute_hard_override_first():
    """What: Verify acute hard override dominates final classification.

    Why: Contract requires acute severe conditions to take highest classification precedence.
    How: Provide conflicting dimensions and assert final high risk + acute decision driver.
    """
    assessment = classify_risk_assessment(
        model_version="v2",
        features=RiskFeatures(journey_count=6),
        persistent_risk={"level": "low", "score": 1.0, "triggered": False, "contributors": []},
        acute_risk={"level": "high", "score": 12.0, "triggered": True, "hard_override": True, "contributors": []},
        breadth_risk={"level": "high", "score": 20.0, "triggered": True, "contributors": []},
    )

    assert assessment.overall_risk_level == "high"
    assert assessment.explainability["decision_driver_dimension"] == "acute_risk"
    assert assessment.explainability["acute_override_applied"] is True
    assert assessment.intervention["selected_action"] == "immediate_intervention"


def test_classification_uses_persistent_as_base_when_acute_not_dominant():
    """What: Verify persistent risk drives classification when acute is not overriding.

    Why: Contract places persistent as the base classifier when acute is not dominant.
    How: Provide medium persistent and low acute/breadth signals and assert medium result.
    """
    assessment = classify_risk_assessment(
        model_version="v2",
        features=RiskFeatures(journey_count=10),
        persistent_risk={"level": "medium", "score": 3.1, "triggered": True, "contributors": []},
        acute_risk={"level": "low", "score": 1.3, "triggered": False, "hard_override": False, "contributors": []},
        breadth_risk={"level": "low", "score": 2.0, "triggered": False, "contributors": []},
    )

    assert assessment.overall_risk_level == "medium"
    assert assessment.explainability["decision_driver_dimension"] == "persistent_risk"
    assert assessment.intervention["selected_action"] == "coaching_monitoring"


def test_classification_marks_breadth_as_escalation_only_signal():
    """What: Verify breadth cannot independently create high risk classification.

    Why: Contract forbids breadth as standalone primary classifier.
    How: Provide high breadth with low acute/persistent and assert low final level.
    """
    assessment = classify_risk_assessment(
        model_version="v2",
        features=RiskFeatures(journey_count=8),
        persistent_risk={"level": "low", "score": 0.8, "triggered": False, "contributors": []},
        acute_risk={"level": "low", "score": 0.9, "triggered": False, "hard_override": False, "contributors": []},
        breadth_risk={"level": "high", "score": 21.0, "triggered": True, "contributors": []},
    )

    assert assessment.overall_risk_level == "low"
    assert assessment.explainability["breadth_escalation_applied"] is False
    assert assessment.intervention["selected_action"] == "routine_monitoring"
