from services.risk.models import BehaviourMetrics, RiskFeatures
from services.risk.risk_dimensions.persistent_risk import evaluate_persistent_risk


def test_evaluate_persistent_risk_returns_low_for_sparse_repetition():
    """What: Verify sparse recurring behaviour yields low persistent risk.

    Why: Persistent dimension should capture habitual repetition, not isolated weak signals.
    How: Provide low weighted recurrence and assert low level without trigger.
    """
    features = RiskFeatures(
        journey_count=10,
        behaviour_metrics={
            "dsm_fatigue": BehaviourMetrics(raw_event_count=1, journey_presence_count=1, journey_ratio=0.1, weighted_score=5.0),
        },
    )

    result = evaluate_persistent_risk(features)

    assert result["level"] == "low"
    assert result["triggered"] is False


def test_evaluate_persistent_risk_returns_medium_for_repeated_patterns():
    """What: Verify repeated moderate behaviour patterns produce medium persistent risk.

    Why: Persistent recurrence should elevate long-term behavioural concern levels.
    How: Provide medium weighted recurrence and assert medium classification.
    """
    features = RiskFeatures(
        journey_count=10,
        behaviour_metrics={
            "dsm_distraction": BehaviourMetrics(raw_event_count=8, journey_presence_count=5, journey_ratio=0.5, weighted_score=24.0),
        },
    )

    result = evaluate_persistent_risk(features)

    assert result["level"] == "medium"
    assert result["triggered"] is True


def test_evaluate_persistent_risk_returns_high_for_strong_repeated_patterns():
    """What: Verify strong repeated patterns yield high persistent risk.

    Why: High recurrence with severity should be represented as strong behavioural habit risk.
    How: Provide high weighted recurrence across behaviours and assert high output.
    """
    features = RiskFeatures(
        journey_count=8,
        behaviour_metrics={
            "dsm_fatigue": BehaviourMetrics(raw_event_count=16, journey_presence_count=6, journey_ratio=0.75, weighted_score=48.0),
            "dsm_distraction": BehaviourMetrics(raw_event_count=10, journey_presence_count=5, journey_ratio=0.625, weighted_score=30.0),
        },
    )

    result = evaluate_persistent_risk(features)

    assert result["level"] == "high"
    assert result["triggered"] is True
    assert result["contributors"][0]["behaviour"] == "dsm_fatigue"
