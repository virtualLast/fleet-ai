from services.risk.models import BehaviourMetrics, RiskFeatures
from services.risk.risk_dimensions.acute_risk import evaluate_acute_risk


def test_evaluate_acute_risk_returns_low_for_non_severe_inputs():
    """What: Verify low-severity single-journey patterns produce low acute risk.

    Why: Acute dimension should avoid over-triggering on non-dangerous journey peaks.
    How: Provide low peak/max values and assert low level without hard override.
    """
    features = RiskFeatures(
        journey_count=6,
        behaviour_metrics={
            "dsm_fatigue": BehaviourMetrics(max_single_journey_events=1, weighted_score=6.0),
        },
    )

    result = evaluate_acute_risk(features)

    assert result["level"] == "low"
    assert result["hard_override"] is False


def test_evaluate_acute_risk_returns_medium_for_repeated_intra_journey_spikes():
    """What: Verify repeated medium spikes yield medium acute risk.

    Why: Acute model treats repeated same-journey bursts as meaningful danger.
    How: Provide medium peaks and assert medium risk without hard override.
    """
    features = RiskFeatures(
        journey_count=4,
        behaviour_metrics={
            "adas_fcw": BehaviourMetrics(max_single_journey_events=4, weighted_score=20.0),
            "dsm_distraction": BehaviourMetrics(max_single_journey_events=3, weighted_score=12.0),
        },
    )

    result = evaluate_acute_risk(features)

    assert result["level"] == "medium"
    assert result["triggered"] is True
    assert result["hard_override"] is False


def test_evaluate_acute_risk_returns_high_and_sets_hard_override_for_severe_peaks():
    """What: Verify severe journey peaks trigger high acute risk and override flag.

    Why: Acute severe conditions must support hard-priority final classification logic.
    How: Provide very high peak values and assert high level + hard override true.
    """
    features = RiskFeatures(
        journey_count=3,
        behaviour_metrics={
            "adas_fcw": BehaviourMetrics(max_single_journey_events=9, weighted_score=45.0),
            "dsm_fatigue": BehaviourMetrics(max_single_journey_events=7, weighted_score=35.0),
        },
    )

    result = evaluate_acute_risk(features)

    assert result["level"] == "high"
    assert result["triggered"] is True
    assert result["hard_override"] is True
    assert result["contributors"][0]["behaviour"] == "adas_fcw"
