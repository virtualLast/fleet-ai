"""Rule-based deterministic classification for Behavioural Risk Engine v2."""

from __future__ import annotations

from services.risk.models import RiskAssessment, RiskFeatures


def classify_risk_assessment(
    *,
    model_version: str,
    features: RiskFeatures,
    persistent_risk: dict,
    acute_risk: dict,
    breadth_risk: dict,
) -> RiskAssessment:
    """Classify final deterministic risk using precedence and escalation rules.

    Decision order is fixed:
    1. Acute hard override (if present) dominates.
    2. Persistent risk provides base classification.
    3. Breadth risk can only escalate existing non-trivial signals.

    Args:
        model_version: Deterministic risk-model version string.
        features: Extracted `RiskFeatures` from normalized journey rows.
        persistent_risk: Persistent dimension output with `level`, `score`,
            `triggered`, and `contributors`.
        acute_risk: Acute dimension output with `level`, `score`, `triggered`,
            `hard_override`, and `contributors`.
        breadth_risk: Breadth dimension output with `level`, `score`,
            `triggered`, and `contributors`.

    Returns:
        `RiskAssessment` containing final level/score/confidence,
        first-class dimension outputs, explainability flags, and intervention
        metadata.

    Side effects:
        None.

    Raises:
        Expects dimension dictionaries to follow the evaluator schemas; malformed
        payloads may raise runtime exceptions.
    """

    acute_level = acute_risk.get("level", "low")
    persistent_level = persistent_risk.get("level", "low")
    breadth_level = breadth_risk.get("level", "low")

    acute_override = bool(acute_risk.get("hard_override", False))
    persistent_escalation = False
    breadth_escalation = False

    if acute_override:
        overall_level = "high"
        decision_driver = "acute_risk"
    else:
        overall_level = persistent_level
        decision_driver = "persistent_risk"

        if persistent_level == "low" and acute_level == "medium":
            overall_level = "medium"
            decision_driver = "acute_risk"

        if acute_level == "high":
            overall_level = "high"
            decision_driver = "acute_risk"

        if persistent_level == "high" and overall_level != "high":
            overall_level = "high"
            persistent_escalation = True
            decision_driver = "persistent_risk"

        if breadth_level in {"medium", "high"} and overall_level in {"medium", "high"}:
            breadth_escalation = True

    if overall_level == "high":
        confidence = "high"
    elif overall_level == "medium":
        confidence = "medium"
    else:
        confidence = "low"

    intervention_triggers = []
    if acute_risk.get("triggered"):
        intervention_triggers.append("acute_risk")
    if persistent_risk.get("triggered"):
        intervention_triggers.append("persistent_risk")
    if breadth_risk.get("triggered") and (acute_risk.get("triggered") or persistent_risk.get("triggered")):
        intervention_triggers.append("breadth_risk")

    if acute_risk.get("hard_override"):
        action = "immediate_intervention"
        action_priority = "high"
    elif persistent_risk.get("triggered"):
        action = "coaching_monitoring"
        action_priority = "medium"
    elif breadth_risk.get("triggered") and intervention_triggers:
        action = "escalated_monitoring"
        action_priority = "medium"
    else:
        action = "routine_monitoring"
        action_priority = "low"

    top_concerns = []
    for dimension in (acute_risk, persistent_risk, breadth_risk):
        for contributor in dimension.get("contributors", []):
            behaviour = contributor.get("behaviour")
            if behaviour and behaviour not in top_concerns:
                top_concerns.append(behaviour)
            if len(top_concerns) >= 3:
                break
        if len(top_concerns) >= 3:
            break

    score = max(float(acute_risk.get("score", 0.0)), float(persistent_risk.get("score", 0.0)))
    if breadth_escalation:
        score += float(breadth_risk.get("score", 0.0)) * 0.05

    return RiskAssessment(
        model_version=model_version,
        overall_risk_level=overall_level,
        overall_risk_score=round(score, 4),
        assessment_confidence=confidence,
        primary_concerns=top_concerns,
        requires_intervention=action != "routine_monitoring",
        dimensions={
            "persistent_risk": persistent_risk,
            "acute_risk": acute_risk,
            "breadth_risk": breadth_risk,
        },
        explainability={
            "decision_driver_dimension": decision_driver,
            "acute_override_applied": acute_override,
            "persistent_escalation_applied": persistent_escalation,
            "breadth_escalation_applied": breadth_escalation,
            "top_contributing_behaviours": top_concerns,
        },
        intervention={
            "triggered_by_dimensions": intervention_triggers,
            "selected_action": action,
            "action_priority": action_priority,
        },
    )
