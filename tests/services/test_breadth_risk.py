from services.risk.models import BehaviourMetrics, RiskFeatures
from services.risk.risk_dimensions.breadth_risk import evaluate_breadth_risk


def test_evaluate_breadth_risk_uses_weighted_diversity_not_simple_count():
    """What: Verify breadth score uses behaviour weights, not plain active-count.

    Why: Breadth semantics require weighted diversity and independent ADAS signal handling.
    How: Activate mixed behaviours and assert weighted score/level and contributors.
    """
    features = RiskFeatures(
        behaviour_metrics={
            "adas_fcw": BehaviourMetrics(raw_event_count=1),
            "adas_hmw": BehaviourMetrics(raw_event_count=1),
            "dsm_smoking": BehaviourMetrics(raw_event_count=1),
        }
    )

    result = evaluate_breadth_risk(features)

    assert result["score"] == 11.0
    assert result["level"] == "medium"
    assert result["escalation_only"] is True


def test_evaluate_breadth_risk_keeps_independent_adas_behaviours():
    """What: Verify FCW/HMW/PCW are treated as separate breadth contributors.

    Why: Semantic contract forbids category-collapsing breadth simplification.
    How: Activate each ADAS behaviour and assert all appear independently.
    """
    features = RiskFeatures(
        behaviour_metrics={
            "adas_fcw": BehaviourMetrics(raw_event_count=1),
            "adas_hmw": BehaviourMetrics(raw_event_count=1),
            "adas_pcw": BehaviourMetrics(raw_event_count=1),
        }
    )

    result = evaluate_breadth_risk(features)
    keys = {entry["behaviour"] for entry in result["contributors"]}

    assert {"adas_fcw", "adas_hmw", "adas_pcw"}.issubset(keys)


def test_evaluate_breadth_risk_low_when_no_active_behaviours():
    """What: Verify breadth is low when there are no active risky behaviours.

    Why: Breadth should not trigger escalation without active behaviour diversity.
    How: Provide empty feature metrics and assert low/no-trigger output.
    """
    features = RiskFeatures(behaviour_metrics={})

    result = evaluate_breadth_risk(features)

    assert result["level"] == "low"
    assert result["triggered"] is False
    assert result["escalation_only"] is True
