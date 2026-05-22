from dataclasses import FrozenInstanceError

from services.risk.models import BehaviourMetrics, RiskAssessment, RiskFeatures


def test_behaviour_metrics_defaults_are_stable():
    """What: Verify default BehaviourMetrics values are deterministic.

    Why: Deterministic default metrics prevent inconsistent extraction fallbacks.
    How: Construct with defaults and assert expected primitive values.
    """
    metrics = BehaviourMetrics()

    assert metrics.raw_event_count == 0
    assert metrics.journey_presence_count == 0
    assert metrics.journey_ratio == 0.0
    assert metrics.max_single_journey_events == 0
    assert metrics.weighted_score == 0.0


def test_risk_features_accepts_typed_behaviour_metrics_mapping():
    """What: Verify RiskFeatures stores keyed BehaviourMetrics deterministically.

    Why: Feature extraction must pass typed behavior metrics to dimension evaluators.
    How: Construct with explicit mapping and assert content.
    """
    features = RiskFeatures(
        journey_count=12,
        active_behaviour_count=3,
        high_severity_journey_count=2,
        behaviour_metrics={"dsm_fatigue": BehaviourMetrics(raw_event_count=7, journey_presence_count=4)},
    )

    assert features.journey_count == 12
    assert features.active_behaviour_count == 3
    assert features.high_severity_journey_count == 2
    assert features.behaviour_metrics["dsm_fatigue"].raw_event_count == 7


def test_risk_assessment_contains_dimensions_explainability_and_intervention_fields():
    """What: Verify RiskAssessment keeps required semantic metadata sections.

    Why: v2 explainability/intervention contract requires explicit output metadata.
    How: Construct assessment with all sections and assert shape.
    """
    assessment = RiskAssessment(
        model_version="v2",
        overall_risk_level="high",
        overall_risk_score=6.2,
        assessment_confidence="high",
        primary_concerns=["fatigue", "distraction"],
        requires_intervention=True,
        dimensions={"acute_risk": {"level": "high"}},
        explainability={"acute_override_applied": True},
        intervention={"selected_action": "immediate_intervention"},
    )

    assert assessment.dimensions["acute_risk"]["level"] == "high"
    assert assessment.explainability["acute_override_applied"] is True
    assert assessment.intervention["selected_action"] == "immediate_intervention"


def test_risk_models_are_immutable_dataclasses():
    """What: Verify risk dataclasses are frozen/immutable.

    Why: Immutability protects deterministic results from mutation side effects.
    How: Attempt field mutation and assert FrozenInstanceError is raised.
    """
    metrics = BehaviourMetrics()

    try:
        setattr(metrics, "raw_event_count", 1)
    except FrozenInstanceError:
        pass
    else:
        raise AssertionError("Expected frozen dataclass mutation to fail")
